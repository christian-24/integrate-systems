#!/usr/bin/env python3
"""Standard projektu: zakładanie, sprawdzanie i odczyt projektów prowadzonych w jednym układzie.

Polecenia:
  python3 projekt.py nowy <folder> [--nazwa "Nazwa"] [--rejestruj]   zakłada brakujące pliki standardu
  python3 projekt.py kampania <folder> "Nazwa kampanii"            zakłada kampanie/<nazwa>.md
  python3 projekt.py sprawdz [<folder> ...]                        raport zgodności ze standardem
  python3 projekt.py dodaj <folder> | usun <folder> | lista        rejestr projektów widocznych w panelu

Ten sam plik jest modułem, z którego panel (dashboard/server.py) czyta projekty.
Tylko biblioteka standardowa Pythona. Istniejących plików nigdy nie nadpisuje.
"""
import datetime
import glob
import json
import os
import re
import sys
import tempfile
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TEMPLATE = os.path.join(HERE, "szablon")
CAMPAIGN_TEMPLATE = os.path.join(HERE, "szablon-kampanii.md")
REGISTRY = os.path.join(ROOT, "projekty.json")
PLACEHOLDER = "_Do uzupełnienia"
INBOX = "Do rozplanowania"
BLOCK = ("<!-- standard-projektu:start -->", "<!-- standard-projektu:end -->")

# Dokumenty wymagane w każdym projekcie: (klucz, etykieta, plik, do czego służy, stałe sekcje)
DOCS = [
    ("karta", "Karta", "KARTA.md", "Umowa z agentami: po co jest projekt, co obejmuje i na jakich zasadach wolno w nim pracować.",
     ["Cel", "Zakres", "Poza zakresem", "Definicja ukończenia", "Zasady pracy agentów"]),
    ("zadania", "Zadania", "ZADANIA.md", "Jedyna lista zadań: etapy z terminami i zadania w jednym formacie wiersza.",
     ["Etap: nazwa (z wierszem termin:)", INBOX]),
    ("decyzje", "Decyzje", "DECYZJE.md", "Dziennik decyzji, żeby nie wracać do rozstrzygniętych spraw.",
     ["RRRR-MM-DD: tytuł (jeden nagłówek na decyzję)"]),
    ("readme", "README", "README.md", "Wejście do projektu dla człowieka i agenta.",
     ["Co to jest", "Jak uruchomić", "Struktura", "Dokumentacja"]),
    ("arch", "Architektura", "docs/ARCHITEKTURA.md", "Jak system jest zbudowany.",
     ["Przegląd", "Komponenty", "Dane", "Integracje"]),
    ("run", "Uruchomienie", "docs/URUCHOMIENIE.md", "Jak uruchomić, przetestować i wdrożyć.",
     ["Wymagania", "Uruchomienie lokalne", "Testy", "Wdrożenie"]),
    ("agenci", "Instrukcje agentów", "CLAUDE.md, AGENTS.md", "Te same zasady dla Claude Code i Codex: czytaj Kartę, prowadź ZADANIA.md.",
     ["Standard projektu"]),
]
CAMPAIGN_DOC = ("kampania", "Kampania", "kampanie/<nazwa>.md", "Jedna kampania w jednym pliku: cel, miernik, kanały, harmonogram publikacji, wyniki.",
                ["Grupa docelowa", "Przekaz", "Harmonogram", "Wyniki i wnioski"])
CAMPAIGN_META = ["stan", "cel", "kanały", "start", "koniec"]

STATE = {" ": "todo", "~": "doing", "!": "blocked", "x": "done", "X": "done"}
CHAR = {"todo": " ", "doing": "~", "blocked": "!", "done": "x"}
WHO = {"claude": "claude", "claude code": "claude", "codex": "codex", "ty": "ty", "ja": "ty"}
WHERE = {"pc": "pc", "windows": "pc", "mac": "mac", "chmura": "cloud", "cloud": "cloud"}
SLOT = {"dzień": "dzień", "dzien": "dzień", "noc": "noc"}
NEEDS = {"zgoda": "zgoda", "odbiór": "odbiór", "odbior": "odbiór"}
PROJECT_STATE = {"aktywny": "active", "wstrzymany": "paused", "zakończony": "done", "zakonczony": "done",
                 "backlog": "backlog"}
# Fazy projektu (pole „- faza:” w KARTA.md); zapis z polskimi znakami, odczyt także bez nich.
PHASES = ["pomysl", "ksiega", "budowa", "wdrozenie", "marketing", "utrzymanie"]
PHASE_OUT = {"pomysl": "pomysł", "ksiega": "księga", "budowa": "budowa", "wdrozenie": "wdrożenie",
             "marketing": "marketing", "utrzymanie": "utrzymanie"}
THRESHOLDS = {"lekka": "lekka", "pelna": "pelna"}
THRESHOLD_OUT = {"lekka": "lekka", "pelna": "pełna"}
YES_NO = {"tak": True, "nie": False}
# Decyzje zbieracza (system/KONTRAKT.md): stany, w których folder jest projektem w panelu.
COLLECTOR_STATE = {"w realizacji": "active", "w przygotowaniu": "active", "wstrzymany": "paused", "backlog": "backlog"}
DESCRIPTION_MAX = 300
CAMPAIGN_STATE = {"plan": "plan", "w toku": "active", "zakończona": "done", "zakonczona": "done", "wstrzymana": "paused"}
PRIORITY_DEFAULT = 3                      # „- priorytet: 1–5” w KARTA.md; 1 najważniejszy, brak wiersza = 3
PRIORITIES = range(1, 6)
DAY_MINUTES = 120                         # dzienna pojemność właściciela w minutach (PANEL_DZIEN_MIN)
OWNER_SOON_DAYS = 7                       # zadanie właściciela z kiedy w tylu dniach potrzebuje kroków albo materiału
# Pole „sprawdza:”: klucze kontroli serwera (uruchom/serwer/zdrowie.sh, „server.checks” w /api/data) albo „plik <ścieżka>”.
SERVER_CHECKS = ("kopia", "kopia-poza", "claude", "claude-agent", "zapis-kart", "panel", "useme", "dysk")
CHECK_FILE = "plik"
HEALTH_FILE = "/home/panel/.zdrowie-stan"  # PANEL_ZDROWIE_STAN
HEALTH_VALUES = ("ok", "zle", "brak")
# Pole „licznik:”: nazwa liczby, którą właściciel podaje przy zamknięciu zadania (trafia do kampanii).
COUNTERS = {"zaproszenia": "zaproszenia", "przyjęte": "przyjęte", "przyjete": "przyjęte", "rozmowy": "rozmowy",
            "linki": "linki", "konta": "konta", "oferty": "oferty", "odpowiedzi": "odpowiedzi"}
RESULTS_TITLE = "Wyniki i wnioski"
CAMPAIGN_FILE = re.compile(r"^kampanie/[^/\\]+\.md$")

TASK = re.compile(r"^\s*[-*]\s+\[([ xX~!])\]\s+(.*\S)\s*$")
DATE = re.compile(r"^(\d{4}-\d\d-\d\d|[+-]\d+)$")  # data albo liczba dni od dziś (tylko dane przykładowe)
META = re.compile(r"^\s*-\s*([^:|\[\]`]{1,30}?)\s*:\s*(.*?)\s*$")


def slug(text):
    t = unicodedata.normalize("NFKD", str(text).replace("ł", "l").replace("Ł", "L")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-") or "projekt"


def read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except (OSError, UnicodeDecodeError):
        return None


def write_atomic(path, text):
    # Plik standardu może być dowiązaniem (repozytorium projektu → karta w IntegrateSystems/szkice):
    # zapis trafia do pliku docelowego, a dowiązanie zostaje.
    path = os.path.realpath(path)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".tmp-")
    with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    os.replace(tmp, path)


def strip_comments(text):
    """Usuwa komentarze HTML, zachowując numerację wierszy."""
    return re.sub(r"<!--.*?-->", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)


def parse_doc(text):
    """Zwraca (tytuł H1, wiersze przed pierwszą sekcją, sekcje H2). Wiersz to para (numer, tekst)."""
    h1, head, sections, cur, fence = "", [], [], None, False
    for no, line in enumerate(strip_comments(text).split("\n"), 1):
        line = line.rstrip("\r")
        if line.lstrip().startswith("```"):
            fence = not fence
        elif not fence and line.startswith("# ") and not h1 and cur is None:
            h1 = line[2:].strip()
            continue
        elif not fence and line.startswith("## "):
            cur = {"title": line[3:].strip(), "line": no, "body": []}
            sections.append(cur)
            continue
        (cur["body"] if cur else head).append((no, line))
    return h1, head, sections


def meta_of(lines):
    out = {}
    for _, line in lines:
        m = META.match(line)
        if m:
            out[m.group(1).strip().lower()] = m.group(2)
    return out


def is_filled(body):
    for _, line in body:
        s = line.strip()
        if s and PLACEHOLDER not in s and not s.startswith(">"):
            return True
    return False


def section(sections, title):
    for s in sections:
        if s["title"].lower() == title.lower():
            return s
    return None


def minutes_of(value):
    m = re.match(r"^(?:(\d+)\s*h)?\s*(?:(\d+)\s*(?:min)?)?$", value.strip().lower())
    if not m or not (m.group(1) or m.group(2)):
        return None
    return int(m.group(1) or 0) * 60 + int(m.group(2) or 0)


def number_of(value):
    """Pierwsza liczba w tekście („40 rozmów” -> 40, „1 200” -> 1200, „2,5” -> 2.5); None bez liczby."""
    m = re.search(r"\d+(?:[.,]\d+)?", str(value or "").replace(" ", "").replace("\u00a0", ""))
    if not m:
        return None
    n = float(m.group(0).replace(",", "."))
    return int(n) if n.is_integer() else n


def day_minutes(env=None):
    """Dzienna pojemność właściciela w minutach: PANEL_DZIEN_MIN (liczba całkowita > 0), inaczej DAY_MINUTES."""
    raw = str((os.environ if env is None else env).get("PANEL_DZIEN_MIN", "") or "").strip()
    return int(raw) if raw.isdigit() and int(raw) > 0 else DAY_MINUTES


def parse_task(line):
    """Wiersz '- [ ] Tytuł | kto: claude | kiedy: 2026-11-12' -> słownik albo None."""
    m = TASK.match(line)
    if not m:
        return None
    parts = re.split(r"\s*\|\s*", m.group(2))
    t = {"title": parts[0], "state": STATE[m.group(1)], "executor": "", "machine": "", "date": "", "slot": "",
         "minutes": 0, "needsYou": "", "needs": [], "blocked": "", "channel": "", "after": [], "check": None,
         "counter": "", "campaignFile": "", "errors": []}
    for p in parts[1:]:
        k, sep, v = p.partition(":")
        k, v = k.strip().lower(), v.strip()
        bad = None
        if not p:
            continue
        if not sep:
            bad = "pole „%s” bez wartości" % p
        elif k == "kto":
            t["executor"] = WHO.get(v.lower(), "")
            bad = None if t["executor"] else "kto: %s (dozwolone: claude, codex, ty)" % v
        elif k == "gdzie":
            t["machine"] = WHERE.get(v.lower(), "")
            bad = None if t["machine"] else "gdzie: %s (dozwolone: pc, mac, chmura)" % v
        elif k == "kiedy":
            t["date"] = v if DATE.match(v) else ""
            bad = None if t["date"] else "kiedy: %s (format RRRR-MM-DD)" % v
        elif k == "pora":
            t["slot"] = SLOT.get(v.lower(), "")
            bad = None if t["slot"] else "pora: %s (dozwolone: dzień, noc)" % v
        elif k == "czas":
            mins = minutes_of(v)
            t["minutes"] = mins or 0
            bad = None if mins else "czas: %s (podaj minuty)" % v
        elif k == "wymaga":
            vals = [x.strip() for x in re.split(r"\s*[,/;]\s*|\s+i\s+", v) if x.strip()]
            wrong = [x for x in vals if x.lower() not in NEEDS]
            for x in vals:
                if x.lower() in NEEDS and NEEDS[x.lower()] not in t["needs"]:
                    t["needs"].append(NEEDS[x.lower()])
            t["needsYou"] = t["needs"][0] if t["needs"] else ""
            bad = "wymaga: %s (dozwolone: zgoda, odbiór)" % ", ".join(wrong) if wrong or not vals else None
        elif k == "blokada":
            t["blocked"] = v
        elif k in ("kanał", "kanal"):
            t["channel"] = v
        elif k == "po":
            t["after"] = [x.strip() for x in v.split(",") if x.strip()]
            bad = None if t["after"] else "po: podaj fragment tytułu zadania"
        elif k == "sprawdza":
            t["check"] = check_of(v)
            bad = None if t["check"] else "sprawdza: podaj klucz kontroli serwera albo plik <ścieżka>"
        elif k == "licznik":
            t["counter"] = COUNTERS.get(v.lower(), "")
            bad = None if t["counter"] else "licznik: %s (dozwolone: %s)" % (v, ", ".join(sorted(set(COUNTERS.values()))))
        elif k == "kampania":
            t["campaignFile"] = campaign_rel(v)
            bad = None if t["campaignFile"] else "kampania: %s (plik kampanii, np. kampanie/nazwa.md)" % v
        else:
            bad = "nieznane pole „%s”" % k
        if bad:
            t["errors"].append(bad)
    return t


def check_of(value):
    """Wartość pola „sprawdza:” -> {"key", "ok": None, "at": ""} albo None przy pustej wartości.
    Klucz kontroli serwera małymi literami; plik jako „plik <ścieżka>” (ścieżka względem folderu projektu)."""
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    head, _, rest = text.partition(" ")
    if head.lower() == CHECK_FILE:
        path = rest.strip().strip("`").strip()
        return {"key": "%s %s" % (CHECK_FILE, path), "ok": None, "at": ""} if path else None
    return {"key": text.lower(), "ok": None, "at": ""} if text else None


def campaign_rel(value):
    """Pole „kampania:” -> "kampanie/<plik>.md" albo "" przy złej wartości („nazwa”, „nazwa.md”, „kampanie/nazwa.md”)."""
    v = str(value or "").strip().strip("`").replace("\\", "/")
    if not v:
        return ""
    if not v.startswith("kampanie/"):
        v = "kampanie/" + v
    if not v.endswith(".md"):
        v += ".md"
    return v if CAMPAIGN_FILE.match(v) and ".." not in v else ""


def known_check(key):
    """Czy klucz pola „sprawdza:” jest znany: klucz kontroli serwera albo „plik <ścieżka>”."""
    key = str(key or "")
    return key in SERVER_CHECKS or (key.startswith(CHECK_FILE + " ") and bool(key[len(CHECK_FILE) + 1:].strip()))


# ---------- szczegóły zadania: wcięte wiersze bezpośrednio pod wierszem zadania ----------
DETAIL_KEYS = {"cel": "goal", "gotowe gdy": "doneWhen", "materiał": "refs", "material": "refs", "materiały": "refs",
               "materialy": "refs", "wynik": "result", "decyzja": "decision", "zostało": "left", "zostalo": "left",
               "poprawka": "fix", "następne": "next", "nastepne": "next",
               "wyświetlenia": "views", "wyswietlenia": "views", "kliknięcia": "clicks", "klikniecia": "clicks",
               "konta": "accounts", "link": "link"}
DETAIL_OUT = {"goal": "cel", "doneWhen": "gotowe gdy", "refs": "materiał", "result": "wynik", "decision": "decyzja",
              "left": "zostało", "fix": "poprawka", "next": "następne", "views": "wyświetlenia",
              "clicks": "kliknięcia", "accounts": "konta", "link": "link"}
DETAIL_ORDER = ["goal", "doneWhen", "refs", "steps", "views", "clicks", "accounts", "link", "result", "decision",
                "left", "fix", "next"]   # kroki i notatki: "steps"
# Wyniki publikacji (wiersze kampanii): liczby całkowite i adres. W szczegółach publikacji zawsze obecne
# (None / ""), w zadaniach ZADANIA.md tylko wtedy, gdy wiersz jest zapisany.
PUB_COUNTS = ("views", "clicks", "accounts")
PUB_KEYS = PUB_COUNTS + ("link",)
LINK = re.compile(r"^https?://\S+$")
STEP_KEY = "krok"           # set_detail: {"index": n, "done": bool} zmienia n-ty krok (od 0)
DETAIL_INDENT = "  "
DETAIL_LINE = re.compile(r"^(?:[-*]\s+)?([^:|\[\]`]{2,20}?)\s*:\s*(.*?)\s*$")
STEP = re.compile(r"^[-*]\s+\[([ xX~!])\]\s+(.*\S)\s*$")
TITLE_MAX = 120
NOUN_START = re.compile(r"^\w{3,}(anie|enie|ęcie|ycie)$")   # „Wdrożenie”, „Przygotowanie”: rzeczownik zamiast czasownika
DONE_LOOSE = re.compile(r"\balbo\s+w\s+[„\"]?zostało", re.I)    # „gotowe gdy: … albo w zostało: …” to nie warunek
DONE_TABLE = re.compile(r"\btabel", re.I)
DONE_ENTRY = re.compile(r"\bwpis", re.I)
DONE_AND = re.compile(r"\b(i|oraz|a)\b|;", re.I)


def weak_done(text):
    """„gotowe gdy” niesprawdzalne: z wyjątkiem „albo w zostało” albo będące jedynie wpisem do tabeli."""
    s = str(text or "")
    return bool(DONE_LOOSE.search(s)) or bool(DONE_TABLE.search(s) and DONE_ENTRY.search(s) and not DONE_AND.search(s))


def blank_detail():
    return {"goal": "", "doneWhen": "", "refs": [], "steps": [], "result": "", "decision": "", "left": "", "fix": "",
            "next": "", "notes": []}


def ref_of(value):
    """„marketing/plan.md#5” -> {"path": "marketing/plan.md", "anchor": "5"}."""
    path, _, anchor = value.strip().strip("`").partition("#")
    return {"path": path.strip(), "anchor": anchor.strip()}


def detail_key(line):
    """Wiersz szczegółów -> (pole, wartość) dla znanego klucza, inaczej (None, None)."""
    m = DETAIL_LINE.match(line.strip())
    if m and m.group(1).strip().lower() in DETAIL_KEYS:
        return DETAIL_KEYS[m.group(1).strip().lower()], m.group(2)
    return None, None


def is_detail(line):
    """Wiersz wcięty i niepusty: należy do szczegółów zadania, pod którym stoi."""
    return bool(line.strip()) and line[:1] in (" ", "\t")


def count_of(value):
    """Liczba całkowita nieujemna z tekstu wyniku publikacji („1 200”, „1200”) albo None."""
    text = re.sub(r"[\s\u00a0.]", "", str(value or ""))
    return int(text) if text.isdigit() else None


def parse_detail(lines):
    """Wcięte wiersze pod zadaniem -> {"goal", "doneWhen", "refs", "steps", "result", "decision", "left", "fix", "next",
    "notes"}. „następne” to jeden wiersz (pierwszy wygrywa); pozostałe klucze łączą kolejne wiersze spacją.
    Wyniki publikacji („wyświetlenia”, „kliknięcia”, „konta”: liczby, „link”: adres http) trafiają do "views",
    "clicks", "accounts", "link" tylko wtedy, gdy są zapisane; zła wartość zostaje notatką."""
    d = blank_detail()
    for line in lines:
        s = line.strip()
        step = STEP.match(s)
        if step:
            d["steps"].append({"done": step.group(1) in "xX", "text": step.group(2)})
            continue
        key, value = detail_key(line)
        if key in PUB_COUNTS:
            n = count_of(value)
            if n is None:
                d["notes"].append(s)
            else:
                d[key] = n
        elif key == "link":
            if LINK.match(value.strip()):
                d["link"] = value.strip()
            else:
                d["notes"].append(s)
        elif key == "refs":
            d["refs"] += [ref_of(v) for v in re.split(r",\s+", value) if v.strip()]
        elif key == "next":
            d["next"] = d["next"] or value
        elif key:
            d[key] = (d[key] + " " + value).strip() if d[key] else value
        else:
            d["notes"].append(s)
    return d


def task_rows(body):
    """Zadania sekcji: [(numer wiersza, zadanie)], z polem "detail". Wcięte wiersze bezpośrednio pod zadaniem
    (także kroki „- [ ] …”) to jego szczegóły, nie osobne zadania; kończą się na pierwszym wierszu bez wcięcia."""
    out, cur = [], None
    for no, line in body:
        if cur is not None and is_detail(line):
            cur.append(line)
            continue
        cur = None
        t = parse_task(line)
        if t:
            cur = []
            out.append((no, t, cur))
    for no, t, lines in out:
        t["detail"] = parse_detail(lines)
    return [(no, t) for no, t, _ in out]


def _examples(items, limit=5):
    shown = ["„%s”" % (x if len(x) <= 40 else x[:39].rstrip() + "…") for x in items[:limit]]
    return ", ".join(shown) + (" i %d inne" % (len(items) - limit) if len(items) > limit else "")


def task_gaps(stages, tasks, today=None, active=True, campaigns=()):
    """Braki w opisie otwartych zadań ZADANIA.md (do braków dokumentu, najwyżej 5 przykładów w wierszu).

    today: date do reguły 7 dni (domyślnie dziś), active: czy projekt jest aktywny (reguła „agent bez kiedy”),
    campaigns: kampanie projektu (reguła „kampania w toku bez celu liczbowego”)."""
    today = today or datetime.date.today()
    soon = (today + datetime.timedelta(days=OWNER_SOON_DAYS)).isoformat()
    dated = {s["id"] for s in stages if s["date"] and not s["closed"]}
    open_ = [t for t in tasks if t["state"] != "done" and t.get("kind", "zadanie") == "zadanie"]
    no_done = [t["title"] for t in open_ if t["stage"] in dated and not t["detail"]["doneWhen"]]
    long_ = [t["title"] for t in open_ if len(t["title"]) > TITLE_MAX]
    nouns = [t["title"] for t in open_ if NOUN_START.match((t["title"].split() or [""])[0].lower())]
    owner = [t for t in open_ if t["executor"] == "ty"]
    bare = [t["title"] for t in owner if date_key(t["date"], today) and date_key(t["date"], today) <= soon
            and not t["detail"]["steps"] and not t["detail"]["refs"]]
    no_time = [t["title"] for t in owner if not t["minutes"]]
    agent_no_date = [t["title"] for t in open_ if active and t["executor"] in ("claude", "codex")
                     and not t["date"] and t.get("group") != INBOX]
    left_result = [t["title"] for t in open_ if t["state"] == "todo" and t["detail"]["result"]
                   and not t.get("needs") and not t.get("needsYou")]
    no_target = [c["name"] for c in campaigns if c.get("state") == "active" and c.get("target") is None]
    bad_check = ["%s (%s)" % (t["title"], t["check"]["key"]) for t in open_
                 if isinstance(t.get("check"), dict) and not known_check(t["check"].get("key"))]
    weak = [t["title"] for t in open_ if t["detail"]["doneWhen"] and weak_done(t["detail"]["doneWhen"])]
    gaps = []
    if no_done:
        gaps.append("zadania bez „gotowe gdy” w etapie z terminem: %d (%s)" % (len(no_done), _examples(no_done)))
    if long_:
        gaps.append("tytuł dłuższy niż %d znaków: %d (%s)" % (TITLE_MAX, len(long_), _examples(long_)))
    if nouns:
        gaps.append("tytuł nie zaczyna się od czasownika: %d (%s)" % (len(nouns), _examples(nouns)))
    if bare:
        gaps.append("Twoje zadania na %d dni bez kroków i materiału: %d (%s)" % (OWNER_SOON_DAYS, len(bare), _examples(bare)))
    if no_time:
        gaps.append("Twoje zadania bez „czas”: %d (%s)" % (len(no_time), _examples(no_time)))
    if agent_no_date:
        gaps.append("zadania agenta bez „kiedy”: %d (%s)" % (len(agent_no_date), _examples(agent_no_date)))
    if left_result:
        gaps.append("otwarte zadania z „wynik:” bez odbioru i nie w toku: %d (%s)"
                    % (len(left_result), _examples(left_result)))
    if no_target:
        gaps.append("kampania w toku bez „cel liczbowy”: %d (%s)" % (len(no_target), _examples(no_target)))
    if bad_check:
        gaps.append("„sprawdza:” z nieznanym kluczem (dozwolone: %s, plik <ścieżka>): %d (%s)"
                    % (", ".join(SERVER_CHECKS), len(bad_check), _examples(bad_check)))
    if weak:
        gaps.append("„gotowe gdy” z „albo w zostało” albo tylko z wpisem do tabeli: %d (%s)" % (len(weak), _examples(weak)))
    return gaps


def _task(t, pid, file_rel, no, kind, **extra):
    errors = t.pop("errors")
    t.update({"id": "%s|%s|%d" % (pid, file_rel, no), "project": pid, "file": file_rel, "line": no, "kind": kind,
              "stage": "", "group": "", "campaign": ""})
    t.setdefault("detail", blank_detail())
    t.setdefault("waitingFor", [])
    t.setdefault("unlocks", [])
    t.setdefault("unlockCount", 0)
    t.update(extra)
    return ["wiersz %d: %s" % (no, e) for e in errors]


def link_after(tasks):
    """Pole „po:”: dla każdego zadania lista poprzedników "waitingFor" [{"title", "done", "id"}].

    Poprzednik to pierwszy wiersz tego samego pliku (poza samym zadaniem), którego tytuł zawiera fragment,
    bez wielkości liter. Fragment bez pasującego wiersza: {"title": fragment, "done": False, "id": ""}.
    W drugą stronę: "unlocks" [{"id", "title", "executor", "date"}] to otwarte zadania, które mają „po:” na tym
    zadaniu (w kolejności wierszy), "unlockCount" ich liczba.
    """
    by_file = {}
    for t in tasks:
        by_file.setdefault((t["project"], t["file"]), []).append(t)
    for rows in by_file.values():
        rows.sort(key=lambda t: t["line"])
        for t in rows:
            out = []
            for frag in t.get("after") or []:
                low = frag.lower()
                hit = next((x for x in rows if x is not t and low in x["title"].lower()), None)
                out.append({"title": hit["title"], "done": hit["state"] == "done", "id": hit["id"]} if hit
                           else {"title": frag, "done": False, "id": ""})
            t["waitingFor"] = out
    by_id = {t["id"]: t for t in tasks}
    for t in tasks:
        t["unlocks"] = []
    for t in sorted(tasks, key=lambda x: (x["project"], x["file"], x["line"])):
        if t["state"] == "done":
            continue
        for w in t["waitingFor"]:
            pred = by_id.get(w.get("id"))
            if pred is not None and pred is not t and all(u["id"] != t["id"] for u in pred["unlocks"]):
                pred["unlocks"].append({"id": t["id"], "title": t["title"], "executor": t["executor"], "date": t["date"]})
    for t in tasks:
        t["unlockCount"] = len(t["unlocks"])
    return tasks


def waiting_titles(task):
    """Tytuły poprzedników z „po:”, które nie są zrobione."""
    return [w["title"] for w in task.get("waitingFor") or [] if not w.get("done")]


def parse_tasks(text, pid, file_rel="ZADANIA.md"):
    """ZADANIA.md -> (etapy, zadania, uwagi do formatu)."""
    _, _, sections = parse_doc(text)
    stages, tasks, problems, seen = [], [], [], set()
    for sec in sections:
        m = re.match(r"^Etap\s*:\s*(.+)$", sec["title"], re.I)
        stage = None
        if m:
            sid = "%s/%s" % (pid, slug(m.group(1)))
            while sid in seen:
                sid += "-2"
            seen.add(sid)
            stage = {"id": sid, "project": pid, "title": m.group(1).strip(), "date": "", "closed": False,
                     "line": sec["line"]}
            for _, line in sec["body"]:
                if TASK.match(line):
                    break
                mm = re.match(r"^\s*-?\s*(termin|stan)\s*:\s*(.*?)\s*$", line, re.I)
                if mm and mm.group(1).lower() == "termin":
                    if DATE.match(mm.group(2)):
                        stage["date"] = mm.group(2)
                    else:
                        problems.append("etap „%s”: termin „%s” nie jest datą RRRR-MM-DD" % (stage["title"], mm.group(2)))
                elif mm:
                    stage["closed"] = mm.group(2).lower().startswith(("zamkni", "zako"))
            if not stage["date"]:
                problems.append("etap „%s” bez terminu" % stage["title"])
            stages.append(stage)
        for no, t in task_rows(sec["body"]):
            problems += _task(t, pid, file_rel, no, "zadanie", stage=stage["id"] if stage else "",
                              group=stage["title"] if stage else sec["title"])
            tasks.append(t)
    return stages, tasks, problems


def parse_campaign(text, pid, file_rel):
    """kampanie/<nazwa>.md -> (kampania, publikacje)."""
    h1, head, sections = parse_doc(text)
    base = os.path.splitext(os.path.basename(file_rel))[0]
    meta = meta_of(head)
    gaps = ["brak pola „%s”" % k for k in CAMPAIGN_META if not meta.get(k)]
    state = CAMPAIGN_STATE.get(meta.get("stan", "").lower())
    if meta.get("stan") and not state:
        gaps.append("stan: %s (dozwolone: plan, w toku, zakończona, wstrzymana)" % meta["stan"])
    dates = {}
    for k in ("start", "koniec"):
        dates[k] = meta.get(k, "") if DATE.match(meta.get(k, "")) else ""
        if meta.get(k) and not dates[k]:
            gaps.append("%s: %s nie jest datą RRRR-MM-DD" % (k, meta[k]))
    cid = "%s/k/%s" % (pid, slug(base))
    name = re.sub(r"^Kampania\s*:\s*", "", h1, flags=re.I).strip() or base
    tasks = []
    for title in CAMPAIGN_DOC[4]:
        sec = section(sections, title)
        if not sec:
            gaps.append("brak sekcji „%s”" % title)
        elif title == "Harmonogram":
            for no, t in task_rows(sec["body"]):
                gaps += _task(t, pid, file_rel, no, "publikacja", campaign=cid, group=name)
                for k in PUB_KEYS:
                    t["detail"].setdefault(k, "" if k == "link" else None)
                tasks.append(t)
            if not tasks:
                gaps.append("harmonogram bez publikacji")
        elif not is_filled(sec["body"]) and (title != "Wyniki i wnioski" or state == "done"):
            gaps.append("sekcja „%s” do uzupełnienia" % title)
    counters = campaign_counters(section(sections, RESULTS_TITLE))
    metric = re.sub(r"^licznik\s*:?\s*", "", meta.get("miernik", "").strip().lower())
    counter_metric = COUNTERS.get(metric, "")
    manual = number_of(meta.get("wynik"))
    result = manual
    if counter_metric in counters:            # wynik = większa z liczb: ręczny „wynik:” albo suma licznika miernika
        total = counters[counter_metric]
        result = total if manual is None else max(manual, total)
    camp = {"id": cid, "project": pid, "name": name, "state": state or "plan", "goal": meta.get("cel", ""),
            "metric": meta.get("miernik", ""), "target": number_of(meta.get("cel liczbowy")),
            "result": result, "resultManual": manual, "counters": counters, "counterMetric": counter_metric,
            "start": dates["start"], "end": dates["koniec"],
            "channels": [c.strip() for c in meta.get("kanały", "").split(",") if c.strip()],
            "budget": meta.get("budżet", ""), "file": file_rel, "gaps": gaps}
    return camp, tasks


COUNT_ROW = re.compile(r"^\s*[-*]\s+(\d{4}-\d\d-\d\d)\s*·\s*(\S+)\s+(\d+)\s*·\s*(.*?)\s*$")


def campaign_counters(sec):
    """Sekcja „Wyniki i wnioski” -> {licznik: suma} z wierszy „- RRRR-MM-DD · <licznik> <n> · <tytuł zadania>”.
    Liczą się tylko znane liczniki (COUNTERS); inne wiersze sekcji to wnioski."""
    out = {}
    for _, line in (sec["body"] if sec else []):
        m = COUNT_ROW.match(line)
        name = COUNTERS.get(m.group(2).lower()) if m else None
        if name:
            out[name] = out.get(name, 0) + int(m.group(3))
    return out


def _doc(key, label, file, status, gaps=()):
    return {"key": key, "label": label, "file": file, "status": status, "gaps": list(gaps)}


def _check_sections(key, label, rel, text, titles):
    if text is None:
        return _doc(key, label, rel, "missing", ["brak pliku %s" % rel])
    _, _, sections = parse_doc(text)
    gaps = []
    for title in titles:
        sec = section(sections, title)
        if not sec:
            gaps.append("brak sekcji „%s”" % title)
        elif not is_filled(sec["body"]):
            gaps.append("sekcja „%s” do uzupełnienia" % title)
    return _doc(key, label, rel, "gaps" if gaps else "ok", gaps)


def read_project(path, pid=None, decision=None):
    """Czyta folder projektu. Zwraca {"project", "stages", "tasks", "campaigns"}; brakujące pliki to braki, nie błędy.

    decision: ostatnia decyzja zbieracza dla folderu (stan, klient, alias), gdy projekt pochodzi ze zbieracza.
    """
    path = os.path.abspath(os.path.expanduser(path))
    pid = pid or slug(os.path.basename(path))
    texts = {d[2]: read(os.path.join(path, d[2])) for d in DOCS[:6]}
    docs = []

    karta = texts["KARTA.md"]
    name, meta, goal, description, sections = os.path.basename(path), {}, "", "", []
    if karta is not None:
        h1, head, sections = parse_doc(karta)
        name = re.sub(r"^Karta projektu\s*:\s*", "", h1, flags=re.I).strip() or name
        meta = meta_of(head)
        cel = section(sections, "Cel")
        if cel and is_filled(cel["body"]):
            goal = next(l.strip().lstrip("- ").strip() for _, l in cel["body"] if l.strip() and PLACEHOLDER not in l)
            description = first_paragraph(cel["body"])
    karta_doc = _check_sections("karta", "Karta", "KARTA.md", karta, DOCS[0][4])
    fields = card_fields(meta, decision)
    questions = parse_questions(sections) if karta is not None else []
    q_gaps = question_gaps(questions)
    if karta is not None and (fields["errors"] or q_gaps):
        karta_doc["gaps"] += fields["errors"] + q_gaps
        karta_doc["status"] = "gaps"
    docs.append(karta_doc)

    stages, tasks, campaigns, pubs = [], [], [], []
    for f in sorted(glob.glob(os.path.join(glob.escape(path), "kampanie", "*.md"))):
        text = read(f)
        if text is not None:
            camp, rows = parse_campaign(text, pid, "kampanie/" + os.path.basename(f))
            campaigns.append(camp)
            pubs += rows
    if texts["ZADANIA.md"] is None:
        docs.append(_doc("zadania", "Zadania", "ZADANIA.md", "missing", ["brak pliku ZADANIA.md"]))
    else:
        stages, tasks, problems = parse_tasks(texts["ZADANIA.md"], pid)
        if not stages:
            problems.insert(0, "brak etapów (nagłówek „## Etap: nazwa”)")
        problems += task_gaps(stages, tasks, active=fields["state"] == "active", campaigns=campaigns)
        docs.append(_doc("zadania", "Zadania", "ZADANIA.md", "gaps" if problems else "ok", problems))

    decisions = []
    if texts["DECYZJE.md"] is None:
        docs.append(_doc("decyzje", "Decyzje", "DECYZJE.md", "missing", ["brak pliku DECYZJE.md"]))
    else:
        gaps = []
        for sec in parse_doc(texts["DECYZJE.md"])[2]:
            m = re.match(r"^(\d{4}-\d\d-\d\d|[+-]\d+)\s*:\s*(.+)$", sec["title"])
            if m:
                decisions.append({"date": m.group(1), "title": m.group(2).strip()})
            else:
                gaps.append("wpis „%s” bez daty w nagłówku" % sec["title"])
        docs.append(_doc("decyzje", "Decyzje", "DECYZJE.md", "gaps" if gaps else "ok", gaps))

    for d in DOCS[3:6]:
        docs.append(_check_sections(d[0], d[1], d[2], texts[d[2]], d[4]))

    claude, agents = read(os.path.join(path, "CLAUDE.md")), read(os.path.join(path, "AGENTS.md"))
    gaps = []
    if claude is None:
        gaps.append("brak pliku CLAUDE.md")
    else:
        gaps += ["CLAUDE.md nie importuje @%s" % f for f in ("KARTA.md", "ZADANIA.md")
                 if not re.search(r"^@%s\s*$" % re.escape(f), claude, re.M)]
    if agents is None:
        gaps.append("brak pliku AGENTS.md")
    else:
        gaps += ["AGENTS.md nie wskazuje %s" % f for f in ("KARTA.md", "ZADANIA.md") if f not in agents]
    docs.append(_doc("agenci", "Instrukcje agentów", "CLAUDE.md, AGENTS.md",
                     "missing" if claude is None and agents is None else "gaps" if gaps else "ok", gaps))

    tasks += pubs

    docs_ok = sum(1 for d in docs if d["status"] == "ok")
    project = {"id": pid, "name": name, "goal": goal, "description": description, "state": fields["state"],
               "machine": WHERE.get(meta.get("maszyna", "").lower(), ""), "repo": meta.get("repozytorium", ""),
               "decisions": len(decisions), "lastDecision": decisions[0] if decisions else None,
               "docs": docs, "docsOk": docs_ok, "docsTotal": len(docs),
               "book": [dict(d, gaps=list(d["gaps"])) for d in docs], "bookOk": docs_ok, "bookTotal": len(docs),
               "client": fields["client"], "threshold": fields["threshold"], "alias": fields["alias"],
               "priority": fields["priority"],
               "questions": questions}
    link_after(tasks)
    project["nextStep"] = next_step(tasks)
    if fields["phase"]:
        project["phase"], project["phaseSource"] = fields["phase"], "karta"
    else:
        project["phase"] = compute_phase(project["state"], karta_doc, stages, tasks, campaigns)
        project["phaseSource"] = "wyliczona"
    return {"project": project, "stages": stages, "tasks": tasks, "campaigns": campaigns}


def date_key(value, today=None):
    """Data zadania do porównań: RRRR-MM-DD, także z zapisu względnego („+3”); '' gdy brak daty."""
    value = str(value or "")
    if re.match(r"^\d{4}-\d\d-\d\d", value):
        return value[:10]
    m = re.match(r"^([+-]\d+)", value)
    if m:
        return ((today or datetime.date.today()) + datetime.timedelta(days=int(m.group(1)))).isoformat()
    return ""


def next_step(tasks, today=None):
    """Następny krok projektu: otwarte zadanie z najwcześniejszą datą, inaczej pierwsze otwarte z polem kto.
    {"title", "taskId", "executor", "date"} albo None."""
    open_ = [(i, t) for i, t in enumerate(tasks) if t["state"] != "done"]
    dated = sorted(((date_key(t["date"], today), i, t) for i, t in open_ if date_key(t["date"], today)),
                   key=lambda x: x[:2])
    pick = dated[0][2] if dated else next((t for _, t in open_ if t["executor"]), None)
    if not pick:
        return None
    return {"title": pick["title"], "taskId": pick["id"], "executor": pick["executor"], "date": pick["date"]}


def first_paragraph(body, limit=DESCRIPTION_MAX):
    """Pierwszy akapit sekcji jako jeden wiersz tekstu; dłuższy skracany do pełnych zdań (najwyżej limit znaków)."""
    lines = []
    for _, line in body:
        s = line.strip()
        if not s:
            if lines:
                break
            continue
        if PLACEHOLDER in s or s.startswith(">"):
            continue
        lines.append(re.sub(r"^[-*]\s+", "", s))
    text = re.sub(r"\s+", " ", " ".join(lines)).strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    if end > 0:
        return cut[:end + 1]
    return cut[:limit - 1].rsplit(" ", 1)[0].rstrip(" ,;:") + "…"


def card_fields(meta, decision=None):
    """Pola karty: stan, faza, klient, próg, alias, priorytet (1–5, brak = 3). Karta wygrywa z decyzją zbieracza.

    decision: ostatnia decyzja zbieracza dla tego folderu ({"stan", "klient", "alias"}) albo None.
    Zwraca też listę błędów w wartościach pól (trafiają do braków karty).
    """
    decision = decision if isinstance(decision, dict) else {}
    errors = []
    state = PROJECT_STATE.get(meta.get("stan", "").strip().lower()) or COLLECTOR_STATE.get(str(decision.get("stan", "")).strip().lower()) or "active"

    raw = meta.get("faza", "").strip()
    phase = slug(raw) if raw else ""
    if raw and phase not in PHASES:
        errors.append("faza: %s (dozwolone: %s)" % (raw, ", ".join(PHASE_OUT[p] for p in PHASES)))
        phase = ""

    raw = meta.get("klient", "").strip().lower()
    if raw in YES_NO:
        client = YES_NO[raw]
    else:
        if raw:
            errors.append("klient: %s (dozwolone: tak, nie)" % meta["klient"])
        client = decision["klient"] if isinstance(decision.get("klient"), bool) else True

    raw = meta.get("próg", meta.get("prog", "")).strip()
    threshold = THRESHOLDS.get(slug(raw)) if raw else None
    if raw and not threshold:
        errors.append("próg: %s (dozwolone: lekka, pełna)" % raw)
    threshold = threshold or ("pelna" if client else "lekka")

    alias = decision.get("alias")
    alias = alias.strip() if isinstance(alias, str) and alias.strip() else None

    raw = meta.get("priorytet", "").strip()
    priority = int(raw) if raw.isdigit() and int(raw) in PRIORITIES else PRIORITY_DEFAULT
    if raw and not (raw.isdigit() and int(raw) in PRIORITIES):
        errors.append("priorytet: %s (dozwolone: 1–5, 1 najważniejszy)" % raw)
    return {"state": state, "phase": phase, "client": client, "threshold": threshold, "alias": alias,
            "priority": priority, "errors": errors}


def stage_done(stage, tasks):
    mine = [t for t in tasks if t["stage"] == stage["id"]]
    return stage["closed"] or bool(mine and all(t["state"] == "done" for t in mine))


def compute_phase(state, karta_doc, stages, tasks, campaigns):
    """Faza bez wiersza „- faza:” w karcie; pierwsza pasująca reguła z dashboard/PULPIT.md."""
    if state == "backlog":
        return "pomysl"
    if karta_doc["status"] != "ok":
        return "ksiega"
    if any(c["state"] == "active" for c in campaigns):
        return "marketing"
    if stages and all(stage_done(s, tasks) for s in stages):
        return "utrzymanie"
    return "budowa"


# ---------- sprawy właściciela: wspólne reguły dla pm.py i panelu (STANDARD.md, „Raport PM”) ----------
QUIET_STATES = ("paused", "backlog")      # projekty wstrzymane i w backlogu nie liczą się do spraw właściciela
STALLED_DAYS = 3                          # [~] bez agenta dłużej niż tyle dni: ryzyko „zawieszone”
REVIEW_DAYS = 2                           # odbiór czekający dłużej niż tyle dni: ryzyko


def owner_needs(task):
    """Wartości „wymaga”, które są sprawą właściciela. Na zadaniu kto: ty „zgoda” nie jest decyzją."""
    needs = task.get("needs")
    needs = list(needs) if isinstance(needs, list) else ([task["needsYou"]] if task.get("needsYou") else [])
    return [n for n in needs if n != "zgoda"] if task.get("executor") == "ty" else needs


def for_owner(task):
    """Otwarte zadanie, które czeka na właściciela: kto: ty albo pole wymaga (po regule owner_needs)."""
    return task.get("state") != "done" and (task.get("executor") == "ty" or bool(owner_needs(task)))


def task_key(task):
    return "%s|%s|%s" % (task.get("project", ""), task.get("file", ""), task.get("title", ""))


def task_status(task):
    """"doing" ([~] bez odbioru), "review" (otwarte z wymaga: odbiór) albo ""."""
    if task.get("state") == "done":
        return ""
    if "odbiór" in (task.get("needs") or ([task["needsYou"]] if task.get("needsYou") else [])):
        return "review"
    return "doing" if task.get("state") == "doing" else ""


def state_flags(task, since, live, today):
    """(stalled, reviewOverdue) zadania. since: dzień wejścia w obecny stan ("RRRR-MM-DD" albo ""),
    live: czy agent pracuje nad zadaniem, today: date."""
    try:
        age = (today - datetime.date.fromisoformat(str(since)[:10])).days
    except ValueError:
        return False, False
    status = task_status(task)
    return (status == "doing" and not live and age > STALLED_DAYS), (status == "review" and age > REVIEW_DAYS)


def owner_counts(projects, stages, tasks, today):
    """Liczniki spraw właściciela w projektach poza QUIET_STATES: zadania for_owner i pytania bez odpowiedzi.
    youToday: z datą najpóźniej dziś albo w etapie po terminie; youWeek: w ciągu 7 dni; youLater: później albo bez daty."""
    key = today.isoformat()
    week = (today + datetime.timedelta(days=7)).isoformat()
    quiet = {p["id"] for p in projects if p.get("state") in QUIET_STATES}
    late_stages = {s["id"] for s in stages if re.match(r"^\d{4}-\d\d-\d\d$", s.get("date") or "")
                   and s["date"] < key and not stage_done(s, tasks)}
    items = [(date_key(t.get("date"), today), t.get("stage") in late_stages) for t in tasks
             if t.get("project") not in quiet and for_owner(t)]
    items += [(date_key(q.get("date"), today), False) for p in projects if p["id"] not in quiet
              for q in p.get("questions") or [] if not q.get("answer")]
    out = {"youToday": 0, "youWeek": 0, "youLater": 0}
    for day, late in items:
        out["youToday" if late or (day and day <= key) else "youWeek" if day and day <= week else "youLater"] += 1
    return out


def describe():
    """Opis standardu do pokazania w panelu."""
    return [{"key": d[0], "label": d[1], "file": d[2], "purpose": d[3], "sections": d[4]} for d in DOCS + [CAMPAIGN_DOC]]


# ---------- zapis: wiersz zadania, nowe zadanie, termin etapu, pola kampanii ----------
CARDS = os.path.join(ROOT, "szkice")


def _linked_card(path):
    """Plik standardu z dowiązania do kart w IntegrateSystems/szkice (repozytorium projektu na serwerze)."""
    cards = os.path.realpath(CARDS)
    return os.path.commonpath([cards, path]) == cards


def _task_file(root, file_rel):
    if file_rel != "ZADANIA.md" and not re.match(r"^kampanie/[^/\\]+\.md$", file_rel):
        raise ValueError("niedozwolony plik")
    root = os.path.realpath(os.path.expanduser(root))
    path = os.path.realpath(os.path.join(root, file_rel))
    if os.path.commonpath([root, path]) != root and not _linked_card(path):
        raise ValueError("plik poza projektem")
    return path


def set_state(root, file_rel, line_no, title, state):
    """Zmienia znacznik [ ] w jednym wierszu. False, gdy wiersz zmienił się od odczytu."""
    if state not in CHAR:
        raise ValueError("nieznany stan")
    path = _task_file(root, file_rel)
    with open(path, encoding="utf-8", newline="") as f:
        lines = f.read().split("\n")
    i = int(line_no) - 1
    if i < 0 or i >= len(lines):
        return False
    t = parse_task(lines[i].rstrip("\r"))
    if not t or t["title"] != title:
        return False
    lines[i] = re.sub(r"\[[ xX~!]\]", "[%s]" % CHAR[state], lines[i], count=1)
    write_atomic(path, "\n".join(lines))
    return True


WHERE_OUT = {"pc": "pc", "mac": "mac", "cloud": "chmura"}
CAMPAIGN_STATE_OUT = {"plan": "plan", "active": "w toku", "done": "zakończona", "paused": "wstrzymana"}
KNOWN = {"kto", "gdzie", "kiedy", "pora", "czas", "wymaga", "blokada", "kanał", "kanal", "po"}
ALLOWED = {"state": set(CHAR), "executor": {"", "claude", "codex", "ty"}, "machine": {"", "pc", "mac", "cloud"},
           "slot": {"", "dzień", "noc"}, "needsYou": {"", "zgoda", "odbiór"}}


def _clean(value, limit):
    return re.sub(r"\s+", " ", str(value).replace("|", "/")).strip()[:limit]


def _day(value):
    """Data RRRR-MM-DD istniejąca w kalendarzu albo ValueError."""
    value = str(value)
    if not re.match(r"^\d{4}-\d\d-\d\d$", value):
        raise ValueError("data w formacie RRRR-MM-DD")
    datetime.date.fromisoformat(value)
    return value


def format_task(t, extra=()):
    """Słownik zadania -> wiersz w jednym, stałym układzie pól."""
    parts = [t["title"]]
    for label, value in (("kto", t["executor"]), ("gdzie", WHERE_OUT.get(t["machine"], "")), ("kiedy", t["date"]),
                         ("pora", t["slot"]), ("czas", str(t["minutes"]) if t["minutes"] else ""),
                         ("wymaga", ", ".join(t.get("needs") or ([t["needsYou"]] if t["needsYou"] else []))),
                         ("blokada", t["blocked"]), ("kanał", t["channel"]), ("po", ", ".join(t.get("after") or []))):
        if value:
            parts.append("%s: %s" % (label, value))
    return "- [%s] %s" % (CHAR[t["state"]], " | ".join(parts + list(extra)))


def _lines(path):
    with open(path, encoding="utf-8", newline="") as f:
        return f.read().split("\n")


def update_task(root, file_rel, line_no, title, changes):
    """Zmienia pola jednego wiersza zadania. False, gdy wiersz zmienił się od odczytu."""
    path = _task_file(root, file_rel)
    lines = _lines(path)
    i = int(line_no) - 1
    if i < 0 or i >= len(lines):
        return False
    raw = lines[i]
    t = parse_task(raw.rstrip("\r"))
    if not t or t["title"] != title:
        return False
    if not isinstance(changes, dict) or not changes:
        raise ValueError("brak zmian")
    for k, v in changes.items():
        if k == "title":
            v = _clean(v, 160)
            if not v:
                raise ValueError("pusty tytuł")
        elif k in ALLOWED:
            if v not in ALLOWED[k]:
                raise ValueError("niedozwolona wartość pola %s" % k)
            if k == "needsYou":
                # needsYou to pierwsza wartość pola „wymaga”; pusta usuwa całe pole
                t["needs"] = [v] + [n for n in t["needs"][1:] if n != v] if v else []
        elif k == "needs":
            if not isinstance(v, list) or any(n not in ("zgoda", "odbiór") for n in v):
                raise ValueError("wymaga: lista z wartościami zgoda, odbiór")
            v = list(dict.fromkeys(v))
            t["needsYou"] = v[0] if v else ""
        elif k == "date":
            v = _day(v) if v else ""
        elif k == "minutes":
            if isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= 1440:
                raise ValueError("czas w minutach, od 0 do 1440")
        elif k in ("blocked", "channel"):
            v = _clean(v, 120)
        elif k == "after":
            if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
                raise ValueError("po: lista fragmentów tytułów")
            v = [x for x in (_clean(x, 120).replace(",", " ").strip() for x in v) if x][:10]
        else:
            raise ValueError("nieznane pole")
        t[k] = v
    body = TASK.match(raw.rstrip("\r")).group(2)
    extra = [p for p in re.split(r"\s*\|\s*", body)[1:]
             if p and p.partition(":")[0].strip().lower() not in KNOWN]
    indent = re.match(r"^\s*", raw).group(0)
    lines[i] = indent + format_task(t, extra) + ("\r" if raw.endswith("\r") else "")
    write_atomic(path, "\n".join(lines))
    return True


def add_task(root, title, file_rel="ZADANIA.md", section_line=None):
    """Dopisuje zadanie: do etapu (numer wiersza nagłówka), do „Do rozplanowania” albo do harmonogramu kampanii."""
    title = _clean(title, 160)
    if not title:
        raise ValueError("pusty tytuł")
    path = _task_file(root, file_rel)
    with open(path, encoding="utf-8", newline="") as f:
        text = f.read()
    lines = text.split("\n")
    sections = parse_doc(text)[2]
    fallback = INBOX if file_rel == "ZADANIA.md" else "Harmonogram"
    if section_line and file_rel == "ZADANIA.md":
        sec = next((s for s in sections if s["line"] == int(section_line)), None)
        if not sec:
            raise ValueError("nie ma takiego etapu")
    else:
        sec = section(sections, fallback)
    row = "- [ ] " + title
    if sec:
        nums = [no for no, l in sec["body"] if l.strip()]
        at = nums[-1] if nums else sec["line"]
        lines.insert(at, row)
    else:
        while lines and not lines[-1].strip():
            lines.pop()
        lines += ["", "## " + fallback, row, ""]
    write_atomic(path, "\n".join(lines))
    return True


def next_value(value):
    """Propozycja następnego zadania „Tytuł | kto: … | kiedy: …” -> znormalizowany tekst; ValueError przy błędzie."""
    text = re.sub(r"\s+", " ", str(value)).strip()
    if len(text) > 300:
        raise ValueError("następne: najwyżej 300 znaków")
    t = parse_task("- [ ] " + text)
    if not t or not t["title"].strip():
        raise ValueError("następne: podaj tytuł zadania")
    if t["errors"]:
        raise ValueError("następne: %s" % t["errors"][0])
    return text


def set_detail(root, file_rel, line_no, title, key, value):
    """Dopisuje, zmienia albo (pusta wartość) usuwa jeden klucz szczegółów pod wierszem zadania.

    key: cel, gotowe gdy, materiał, wynik, decyzja, zostało, poprawka, następne, wyświetlenia, kliknięcia, konta,
    link albo krok. Wyświetlenia, kliknięcia i konta to liczby całkowite nieujemne, link to adres http(s). Materiał może mieć kilka
    wartości (lista albo wartości w osobnych wierszach tekstu); zapis zastępuje wszystkie dotychczasowe wiersze
    materiału. „następne” to wiersz zadania bez stanu („Tytuł | kto: … | kiedy: …”), sprawdzany jak wiersz zadania.
    „krok” przyjmuje {"index": n, "done": bool} i zmienia znacznik n-tego wciętego kroku (liczone od 0).
    False, gdy wiersz zadania zmienił się od odczytu; ValueError przy złym kluczu albo wartości.
    """
    name = str(key or "").strip().lower()
    if name == STEP_KEY:
        return _set_step(root, file_rel, line_no, title, value)
    field = DETAIL_KEYS.get(name)
    if not field:
        raise ValueError("nieznany klucz szczegółów (dozwolone: %s, %s)" % (", ".join(DETAIL_OUT.values()), STEP_KEY))
    if isinstance(value, list):
        raw = [str(v) for v in value]
    elif isinstance(value, str):
        raw = value.split("\n") if field == "refs" else [value]
    else:
        raise ValueError("wartość to tekst")
    if sum(len(v) for v in raw) > 2000:
        raise ValueError("wartość: najwyżej 2000 znaków")
    if field == "next":
        values = [next_value(v) for v in raw[:1] if v.strip()]
    elif field in PUB_COUNTS:
        values = [v.strip() for v in raw[:1] if v.strip()]
        if values and count_of(values[0]) is None:
            raise ValueError("%s: liczba całkowita nieujemna" % DETAIL_OUT[field])
        values = [str(count_of(v)) for v in values]
    elif field == "link":
        values = [v.strip() for v in raw[:1] if v.strip()]
        if values and (len(values[0]) > 500 or not LINK.match(values[0])):
            raise ValueError("link: adres http:// albo https:// bez spacji")
    else:
        values = [v for v in (_clean(v, 300 if field == "refs" else 1000) for v in raw) if v]
    if field != "refs":
        values = values[:1]
    path = _task_file(root, file_rel)
    lines = _lines(path)
    i = int(line_no) - 1
    if i < 0 or i >= len(lines):
        return False
    t = parse_task(lines[i].rstrip("\r"))
    if not t or t["title"] != title:
        return False
    end = i + 1
    while end < len(lines) and is_detail(lines[end].rstrip("\r")):
        end += 1
    cr = "\r" if lines[i].endswith("\r") else ""
    kinds = {k: detail_key(lines[k])[0] for k in range(i + 1, end)}
    kinds = {k: (f if f and not STEP.match(lines[k].strip()) else "steps") for k, f in kinds.items()}
    existing = [k for k, f in kinds.items() if f == field]
    if existing:
        at = existing[0]
        for k in reversed(existing):
            del lines[k]
    else:
        rank, at = DETAIL_ORDER.index(field), i + 1
        for k, f in kinds.items():
            if DETAIL_ORDER.index(f) <= rank:
                at = k + 1
    lines[at:at] = ["%s%s: %s%s" % (DETAIL_INDENT, DETAIL_OUT[field], v, cr) for v in values]
    write_atomic(path, "\n".join(lines))
    return True


def _set_step(root, file_rel, line_no, title, value):
    """Znacznik n-tego kroku („  - [ ] krok”) pod zadaniem. value: {"index": n, "done": bool}."""
    if not isinstance(value, dict):
        raise ValueError("krok: {index, done}")
    index, done = value.get("index"), value.get("done")
    if isinstance(index, bool) or not isinstance(index, int) or index < 0 or not isinstance(done, bool):
        raise ValueError("krok: index to liczba od 0, done to true albo false")
    path = _task_file(root, file_rel)
    lines = _lines(path)
    i = int(line_no) - 1
    if i < 0 or i >= len(lines):
        return False
    t = parse_task(lines[i].rstrip("\r"))
    if not t or t["title"] != title:
        return False
    steps = []
    k = i + 1
    while k < len(lines) and is_detail(lines[k].rstrip("\r")):
        if STEP.match(lines[k].strip()):
            steps.append(k)
        k += 1
    if index >= len(steps):
        raise ValueError("nie ma takiego kroku")
    k = steps[index]
    lines[k] = re.sub(r"\[[ xX~!]\]", "[x]" if done else "[ ]", lines[k], count=1)
    write_atomic(path, "\n".join(lines))
    return True


def set_stage_date(root, section_line, title, date):
    """Ustawia wiersz „termin:” etapu. False, gdy nagłówek etapu zmienił się od odczytu."""
    date = _day(date)
    path = _task_file(root, "ZADANIA.md")
    with open(path, encoding="utf-8", newline="") as f:
        text = f.read()
    lines = text.split("\n")
    sec = next((s for s in parse_doc(text)[2] if s["line"] == int(section_line)), None)
    m = re.match(r"^Etap\s*:\s*(.+)$", sec["title"], re.I) if sec else None
    if not m or m.group(1).strip() != title:
        return False
    for no, line in sec["body"]:
        if TASK.match(line):
            break
        mm = re.match(r"^(\s*-?\s*termin\s*:\s*)", line, re.I)
        if mm:
            lines[no - 1] = mm.group(1) + date + ("\r" if lines[no - 1].endswith("\r") else "")
            break
    else:
        no = None
    if no is None or not re.match(r"^\s*-?\s*termin\s*:", lines[no - 1], re.I):
        lines.insert(sec["line"], "termin: " + date)
    write_atomic(path, "\n".join(lines))
    return True


def set_campaign(root, file_rel, name, changes):
    """Zmienia pola „wynik” i „stan” pod tytułem pliku kampanii. False, gdy to już inna kampania."""
    if not re.match(r"^kampanie/[^/\\]+\.md$", file_rel):
        raise ValueError("niedozwolony plik")
    path = _task_file(root, file_rel)
    with open(path, encoding="utf-8", newline="") as f:
        text = f.read()
    camp, _ = parse_campaign(text, "x", file_rel)
    if camp["name"] != name:
        return False
    values = {}
    for k, v in (changes or {}).items():
        if k == "result":
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not 0 <= v <= 1e9:
                raise ValueError("wynik to liczba nieujemna")
            values["wynik"] = ("%g" % v).replace(".", ",")
        elif k == "state":
            if v not in CAMPAIGN_STATE_OUT:
                raise ValueError("niedozwolony stan kampanii")
            values["stan"] = CAMPAIGN_STATE_OUT[v]
        else:
            raise ValueError("nieznane pole")
    if not values:
        raise ValueError("brak zmian")
    lines = text.split("\n")
    _, head, _ = parse_doc(text)
    last = 1
    for no, line in head:
        m = META.match(line)
        if not m:
            continue
        last = no
        key = m.group(1).strip().lower()
        if key in values:
            cr = "\r" if lines[no - 1].endswith("\r") else ""
            lines[no - 1] = "- %s: %s%s" % (key, values.pop(key), cr)
    for key, value in values.items():
        lines.insert(last, "- %s: %s" % (key, value))
        last += 1
    write_atomic(path, "\n".join(lines))
    return True


QUESTIONS_TITLE = "Pytania do właściciela"
QUESTION = re.compile(r"^(?:(\d+)\.|[-*])\s+(.+)$")
ANSWER = re.compile(r"^\s+Odpowiedź\s*:\s*(.*)$", re.I)
QUESTION_DUE = re.compile(r"^\s+termin\s*:\s*(\d{4}-\d\d-\d\d|[+-]\d+)\s*$", re.I)
QUESTION_DUE_TEXT = re.compile(r"\bdo\s+(\d{4}-\d\d-\d\d)\b")
PROPOSAL = re.compile(r"^\s+propozycja\s*:\s*(.*?)\s*$", re.I)
EFFECT = re.compile(r"^\s+skutek\s*:\s*(.*?)\s*$", re.I)
EFFECT_ARROW = re.compile(r"\s*(?:→|->)\s*")
EFFECT_STATE = {"zrobione": "done", "zrobiony": "done", "wstrzymane": "blocked", "wstrzymany": "blocked"}
# Propozycja, która zmienia zadania (heurystyka): bez „skutek:” panel nie wykona jej po przyjęciu.
PROPOSAL_CHANGES = re.compile(r"\b(wstrzyma[ćjnł]|przesu[nń]|zamkn|doda[ćjn])", re.I)


def parse_questions(sections):
    """Pytania z sekcji „Pytania do właściciela” w KARTA.md: wiersz „1. pytanie” albo „- pytanie”,
    pod nim opcjonalnie wcięte wiersze „termin: RRRR-MM-DD”, „propozycja: …” (rekomendacja agenta), „skutek: …”
    (operacja na ZADANIA.md wykonywana po przyjęciu propozycji, apply_effects) i „Odpowiedź: …”.
    Termin może też stać w treści („… do RRRR-MM-DD”). Zwraca [{n, text, answer, date, proposal, effects, line}];
    date to "RRRR-MM-DD" albo "", proposal to tekst albo "", effects lista tekstów operacji.
    """
    sec = section(sections, QUESTIONS_TITLE)
    out = []
    for no, line in (sec["body"] if sec else []):
        m = QUESTION.match(line)
        a = ANSWER.match(line)
        due = QUESTION_DUE.match(line)
        prop = PROPOSAL.match(line)
        eff = EFFECT.match(line)
        if a and out:
            out[-1]["answer"] = a.group(1).strip()
        elif eff and out:
            if eff.group(1):
                out[-1]["effects"].append(eff.group(1))
        elif due and out:
            out[-1]["date"] = due.group(1)
        elif prop and out:
            out[-1]["proposal"] = (out[-1]["proposal"] + " " + prop.group(1)).strip()
        elif m and PLACEHOLDER not in line:
            out.append({"n": len(out) + 1, "text": m.group(2).strip(), "answer": "", "date": "", "proposal": "",
                        "effects": [], "line": no})
        elif line.startswith((" ", "\t")) and line.strip() and out and not out[-1]["answer"]:
            out[-1]["text"] += " " + line.strip()
    for q in out:
        if not q["date"]:
            hit = QUESTION_DUE_TEXT.search(q["text"])
            q["date"] = hit.group(1) if hit else ""
    return out


def set_answer(root, n, answer):
    """Zapisuje albo zmienia wiersz „   Odpowiedź: …” pod pytaniem n w KARTA.md. Pusta odpowiedź usuwa wiersz.
    ValueError przy złych danych, OSError bez pliku karty."""
    if not isinstance(n, int) or isinstance(n, bool) or n < 1:
        raise ValueError("zły numer pytania")
    if not isinstance(answer, str) or len(answer) > 2000:
        raise ValueError("odpowiedź: tekst do 2000 znaków")
    answer = " ".join(answer.split())
    root = os.path.realpath(os.path.expanduser(root))
    path = os.path.join(root, "KARTA.md")
    with open(path, encoding="utf-8", newline="") as f:
        text = f.read()
    nl = "\r\n" if "\r\n" in text else "\n"
    qs = parse_questions(parse_doc(text)[2])
    if n > len(qs):
        raise ValueError("nie ma takiego pytania")
    lines = text.split(nl)
    i = qs[n - 1]["line"]                       # indeks wiersza po pytaniu (numery od 1)
    while i < len(lines) and lines[i].startswith((" ", "\t")) and lines[i].strip() and not ANSWER.match(lines[i]):
        i += 1                                  # dalszy ciąg pytania
    has = i < len(lines) and ANSWER.match(lines[i])
    if answer:
        row = "   Odpowiedź: " + answer
        if has:
            lines[i] = row
        else:
            lines.insert(i, row)
    elif has:
        del lines[i]
    write_atomic(path, nl.join(lines))


def parse_effect(text):
    """Wiersz „skutek:” -> (operacja, argumenty) albo ValueError. Operacje:
    „po: <fragment poprzednika> → <fragment tytułu>”, „kiedy: RRRR-MM-DD → <fragment tytułu>”,
    „stan: zrobione|wstrzymane → <fragment tytułu>”, „nowe: <wiersz zadania>”. Strzałka: → albo ->."""
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    op, sep, rest = text.partition(":")
    op, rest = op.strip().lower(), rest.strip()
    if not sep or op not in ("po", "kiedy", "stan", "nowe"):
        raise ValueError("nieznana operacja (dozwolone: po, kiedy, stan, nowe)")
    if op == "nowe":
        row = re.sub(r"^[-*]\s+\[[ xX~!]\]\s+", "", rest)
        t = parse_task("- [ ] " + row) if row else None
        if not t or not t["title"].strip():
            raise ValueError("nowe: podaj wiersz zadania")
        if t["errors"]:
            raise ValueError("nowe: %s" % t["errors"][0])
        if len(t["title"]) > TITLE_MAX:
            raise ValueError("nowe: tytuł dłuższy niż %d znaków" % TITLE_MAX)
        return op, (row,)
    parts = EFFECT_ARROW.split(rest, maxsplit=1)
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        raise ValueError("%s: zapis „%s: … → fragment tytułu zadania”" % (op, op))
    value, frag = parts[0].strip(), parts[1].strip()
    if op == "kiedy":
        try:
            _day(value)
        except ValueError:
            raise ValueError("kiedy: data RRRR-MM-DD")
    elif op == "stan" and value.lower() not in EFFECT_STATE:
        raise ValueError("stan: zrobione albo wstrzymane")
    return op, (value, frag)


def question_gaps(questions):
    """Braki karty z pytań bez odpowiedzi: zły wiersz „skutek:”, propozycja zmieniająca zadania bez „skutek:”."""
    bad, missing = [], []
    for q in questions:
        if q.get("answer"):
            continue
        for e in q.get("effects") or []:
            try:
                parse_effect(e)
            except ValueError as err:
                bad.append("pytanie %d: %s" % (q["n"], err))
        if q.get("proposal") and not q.get("effects") and PROPOSAL_CHANGES.search(q["proposal"]):
            missing.append("pytanie %d" % q["n"])
    gaps = []
    if bad:
        gaps.append("zły wiersz „skutek:”: %d (%s)" % (len(bad), _examples(bad)))
    if missing:
        gaps.append("propozycja zmienia zadania, a nie ma „skutek:”: %d (%s)" % (len(missing), _examples(missing)))
    return gaps


def _match_task(tasks, frag, exclude=None, open_first=True):
    """Jedno zadanie, którego tytuł zawiera fragment (bez wielkości liter); najpierw wśród otwartych.
    ValueError, gdy nie pasuje żadne albo pasuje kilka."""
    low = frag.lower()
    hits = [t for t in tasks if t is not exclude and low in t["title"].lower()]
    if open_first:
        open_ = [t for t in hits if t["state"] != "done"]
        if len(open_) == 1:
            return open_[0]
        if len(open_) > 1:
            raise ValueError("„%s” pasuje do %d otwartych zadań" % (frag, len(open_)))
    if len(hits) == 1 or (hits and not open_first):
        return hits[0]
    raise ValueError("„%s” nie pasuje do żadnego zadania" % frag if not hits
                     else "„%s” pasuje do %d zadań" % (frag, len(hits)))


def _add_note(path, line_no, title, note):
    """Wcięty wiersz notatki na końcu szczegółów zadania (bez powtórzeń). False, gdy wiersz zadania się zmienił."""
    lines = _lines(path)
    i = int(line_no) - 1
    if i < 0 or i >= len(lines):
        return False
    t = parse_task(lines[i].rstrip("\r"))
    if not t or t["title"] != title:
        return False
    end = i + 1
    while end < len(lines) and is_detail(lines[end].rstrip("\r")):
        if lines[end].strip() == note:
            return True
        end += 1
    lines.insert(end, DETAIL_INDENT + note + ("\r" if lines[i].endswith("\r") else ""))
    write_atomic(path, "\n".join(lines))
    return True


def _insert_inbox(path, rows):
    """Dopisuje wiersze na końcu sekcji „Do rozplanowania” (zakłada ją, gdy jej nie ma)."""
    text = "\n".join(_lines(path))
    lines = text.split("\n")
    sec = section(parse_doc(text)[2], INBOX)
    if sec:
        nums = [no for no, l in sec["body"] if l.strip()]
        at = nums[-1] if nums else sec["line"]
        lines[at:at] = rows
    else:
        while lines and not lines[-1].strip():
            lines.pop()
        lines += ["", "## " + INBOX] + rows + [""]
    write_atomic(path, "\n".join(lines))


def _apply_effect(root, effect, note):
    """Jedna operacja „skutek:” na ZADANIA.md projektu. Zwraca tytuł zmienionego zadania; ValueError przy błędzie."""
    op, args = parse_effect(effect)
    path = _task_file(root, "ZADANIA.md")
    _, tasks, _ = parse_tasks("\n".join(_lines(path)), "x")
    if op == "nowe":
        t = parse_task("- [ ] " + args[0])
        if any(x["title"].lower() == t["title"].lower() and x["state"] != "done" for x in tasks):
            raise ValueError("otwarte zadanie „%s” już jest" % t["title"])
        _insert_inbox(path, ["- [ ] " + args[0], DETAIL_INDENT + note])
        return t["title"]
    value, frag = args
    target = _match_task(tasks, frag)
    if op == "po":
        _match_task(tasks, value, exclude=target, open_first=False)      # poprzednik musi istnieć w pliku
        after = list(target["after"])
        if not any(value.lower() == a.lower() for a in after):
            changes = {"after": after + [value]}
        else:
            changes = None
    elif op == "kiedy":
        changes = {"date": value}
    else:
        state = EFFECT_STATE[value.lower()]
        changes = {"state": state}
        if state == "blocked" and not target["blocked"]:
            changes["blocked"] = "wstrzymane: %s" % note
    if changes and not update_task(root, "ZADANIA.md", target["line"], target["title"], changes):
        raise ValueError("wiersz „%s” zmienił się w trakcie" % target["title"])
    if not _add_note(path, target["line"], target["title"], note):
        raise ValueError("wiersz „%s” zmienił się w trakcie" % target["title"])
    return target["title"]


def apply_effects(root, effects, qn, day):
    """Wykonuje skutki pytania qn („skutek:”) na ZADANIA.md tego projektu, po kolei; pod zmienionym (albo nowym)
    zadaniem dopisuje notatkę „z pytania N, RRRR-MM-DD”. Zadanie dopasowane po fragmencie tytułu bez wielkości liter:
    jedno otwarte zadanie, a bez otwartych jedno dowolne; fragment pasujący do kilku zadań to błąd.

    day: "RRRR-MM-DD" albo date. Zwraca (applied, failed): listy tekstów, applied „<skutek> (zadanie „<tytuł>”)”,
    failed „<skutek>: <powód>”. Operacja z błędem nie zatrzymuje kolejnych."""
    day = day.isoformat() if isinstance(day, datetime.date) else _day(day)
    note = "z pytania %d, %s" % (int(qn), day)
    applied, failed = [], []
    for raw in effects or []:
        effect = re.sub(r"\s+", " ", str(raw)).strip()
        if not effect:
            continue
        try:
            title = _apply_effect(root, effect, note)
        except (ValueError, OSError) as e:
            failed.append("%s: %s" % (effect, e))
        else:
            applied.append("%s (zadanie „%s”)" % (effect, title))
    return applied, failed


# ---------- liczniki zadań i kampanie (pole „licznik:”, sekcja „Wyniki i wnioski”) ----------
def active_campaign(root):
    """Plik pierwszej kampanii w toku ("kampanie/<plik>.md", kolejność nazw plików) albo ""."""
    root = os.path.realpath(os.path.expanduser(root))
    for f in sorted(glob.glob(os.path.join(glob.escape(root), "kampanie", "*.md"))):
        text = read(f)
        rel = "kampanie/" + os.path.basename(f)
        if text is not None and parse_campaign(text, "x", rel)[0]["state"] == "active":
            return rel
    return ""


def append_campaign_count(root, campaign_file, name, n, title, day):
    """Dopisuje w sekcji „Wyniki i wnioski” kampanii wiersz „- RRRR-MM-DD · <licznik> <n> · <tytuł zadania>”
    (sekcję zakłada, gdy jej brak; wiersz szablonu „_Do uzupełnienia…_” usuwa). campaign_file: „kampanie/x.md”
    (albo „x”, „x.md”); puste = pierwsza kampania w toku. name: licznik z COUNTERS, n: liczba całkowita od 0.
    Zwraca True; ValueError przy złych danych albo bez kampanii."""
    name = COUNTERS.get(str(name or "").strip().lower())
    if not name:
        raise ValueError("licznik: %s" % ", ".join(sorted(set(COUNTERS.values()))))
    if isinstance(n, bool) or not isinstance(n, int) or not 0 <= n <= 10 ** 6:
        raise ValueError("liczba całkowita od 0")
    day = day.isoformat() if isinstance(day, datetime.date) else _day(day)
    title = _clean(title, 160)
    rel = campaign_rel(campaign_file) if campaign_file else active_campaign(root)
    if not rel:
        raise ValueError("brak kampanii w toku" if not campaign_file else "zły plik kampanii")
    path = _task_file(root, rel)
    lines = _lines(path)
    text = "\n".join(lines)
    cr = "\r" if lines and lines[0].endswith("\r") else ""
    row = "- %s · %s %d · %s%s" % (day, name, n, title, cr)
    sec = section(parse_doc(text)[2], RESULTS_TITLE)
    if not sec:
        while lines and not lines[-1].strip():
            lines.pop()
        lines += [cr, "## " + RESULTS_TITLE + cr, row, ""]
    else:
        drop = {no - 1 for no, l in sec["body"] if PLACEHOLDER in l}
        keep = [no for no, l in sec["body"] if l.strip() and PLACEHOLDER not in l]
        at = (keep[-1] if keep else sec["line"]) - 1
        out = []
        for i, line in enumerate(lines):
            if i not in drop:
                out.append(line)
            if i == at:
                out.append(row)
        lines = out
    write_atomic(path, "\n".join(lines))
    return True


# ---------- kontrole przy zadaniu (pole „sprawdza:”) ----------
def read_health(path=None):
    """Plik kontroli zdrowia serwera (PANEL_ZDROWIE_STAN, domyślnie /home/panel/.zdrowie-stan), wiersze
    nazwa=ok|zle|brak -> {"checks": {nazwa: stan}, "at": czas zmiany pliku ISO} albo None bez pliku."""
    path = path or os.environ.get("PANEL_ZDROWIE_STAN", "").strip() or HEALTH_FILE
    text = read(path)
    if text is None:
        return None
    checks = {}
    for line in text.splitlines():
        name, sep, value = line.strip().partition("=")
        if sep and re.match(r"^[\w.-]{1,40}$", name) and value.strip() in HEALTH_VALUES:
            checks[name] = value.strip()
    try:
        at = datetime.datetime.fromtimestamp(os.path.getmtime(path)).isoformat(timespec="seconds")
    except OSError:
        at = ""
    return {"checks": checks, "at": at}


def _check_file(root, rel):
    """Plik z „sprawdza: plik <ścieżka>” w folderze projektu albo folderze jego karty (KARTA.md jako dowiązanie)
    -> pełna ścieżka istniejącego pliku albo None. Ścieżki wychodzące poza te foldery nie liczą się."""
    rel = str(rel or "").strip().strip("`").replace("\\", "/")
    if not rel or rel.startswith("/") or re.match(r"^[A-Za-z]:", rel):
        return None
    base = os.path.realpath(os.path.expanduser(root))
    bases = [base]
    card = os.path.join(base, "KARTA.md")
    if os.path.islink(card):
        bases.append(os.path.dirname(os.path.realpath(card)))
    for b in bases:
        path = os.path.realpath(os.path.join(b, rel))
        if os.path.commonpath([b, path]) == b and os.path.exists(path):
            return path
    return None


def check_task(task, server_checks=None, root=None):
    """Kontrola zadania z polem „sprawdza:” -> {"key", "ok", "at"} albo None bez pola.

    server_checks: "checks" ze stanu serwera ({nazwa: "ok"|"zle"|"brak"}) albo cały blok {"checks", "at"}
    (wtedy "at" pochodzi z bloku); None, gdy stanu serwera nie ma. ok: True przy stanie „ok”, False przy
    „zle”/„brak”, None bez danych (brak stanu serwera, kontroli w pliku albo nieznany klucz).
    „plik <ścieżka>”: ok True, gdy plik istnieje w folderze projektu albo karty (at: czas zmiany pliku), inaczej False;
    None bez root."""
    c = task.get("check") if isinstance(task, dict) else None
    key = str(c.get("key") if isinstance(c, dict) else c or "").strip()
    if not key:
        return None
    if key.startswith(CHECK_FILE + " "):
        if not root:
            return {"key": key, "ok": None, "at": ""}
        path = _check_file(root, key[len(CHECK_FILE) + 1:])
        if not path:
            return {"key": key, "ok": False, "at": ""}
        at = datetime.datetime.fromtimestamp(os.path.getmtime(path)).isoformat(timespec="seconds")
        return {"key": key, "ok": True, "at": at}
    at = ""
    checks = server_checks
    if isinstance(checks, dict) and isinstance(checks.get("checks"), dict):
        at = str(checks.get("at") or "")
        checks = checks["checks"]
    state = checks.get(key) if isinstance(checks, dict) and key in SERVER_CHECKS else None
    return {"key": key, "ok": True if state == "ok" else False if state in ("zle", "brak") else None,
            "at": at if state else ""}


def set_card_fields(root, changes):
    """Zmienia albo dopisuje wiersze „- faza:”, „- klient:”, „- próg:”, „- priorytet:” pod tytułem KARTA.md.

    changes: {"phase"?, "client"?, "threshold"?, "priority"? (1–5)}. ValueError przy złej wartości, OSError bez pliku karty.
    """
    values = {}
    if not isinstance(changes, dict):
        raise ValueError("brak zmian")
    for k, v in changes.items():
        if k == "phase":
            v = slug(v) if isinstance(v, str) else ""
            if v not in PHASES:
                raise ValueError("niedozwolona faza")
            values["faza"] = PHASE_OUT[v]
        elif k == "client":
            if not isinstance(v, bool):
                raise ValueError("klient: true albo false")
            values["klient"] = "tak" if v else "nie"
        elif k == "threshold":
            v = slug(v) if isinstance(v, str) else ""
            if v not in THRESHOLDS:
                raise ValueError("próg: lekka albo pełna")
            values["próg"] = THRESHOLD_OUT[v]
        elif k == "priority":
            if isinstance(v, bool) or not isinstance(v, int) or v not in PRIORITIES:
                raise ValueError("priorytet: liczba od 1 do 5")
            values["priorytet"] = str(v)
        else:
            raise ValueError("nieznane pole")
    if not values:
        raise ValueError("brak zmian")
    root = os.path.realpath(os.path.expanduser(root))
    path = os.path.join(root, "KARTA.md")
    with open(path, encoding="utf-8", newline="") as f:
        text = f.read()
    lines = text.split("\n")
    _, head, _ = parse_doc(text)
    aliases = {"prog": "próg"}
    last = None
    for no, line in head:
        m = META.match(line)
        if not m:
            continue
        last = no
        key = m.group(1).strip().lower()
        key = aliases.get(key, key)
        if key in values:
            cr = "\r" if lines[no - 1].endswith("\r") else ""
            lines[no - 1] = "- %s: %s%s" % (key, values.pop(key), cr)
    new = ["- %s: %s" % (k, v) for k, v in values.items()]
    if new:
        if last is None:
            # bez wierszy pól: wstawiamy blok zaraz pod tytułem, oddzielony pustym wierszem
            fence, title = False, 0
            for i, line in enumerate(strip_comments(text).split("\n"), 1):
                if line.lstrip().startswith("```"):
                    fence = not fence
                elif not fence and line.startswith("# "):
                    title = i
                    break
                elif not fence and line.startswith("## "):
                    break
            new = [""] + new if title else new + [""]
            last = title
        lines[last:last] = new
    write_atomic(path, "\n".join(lines))
    return True


# ---------- projekty ze zbieracza (system/zbieracz.py, kontrakt system/KONTRAKT.md) ----------
_system_settings = None


def system_settings():
    """Ustawienia systemu z system/wspolne.ustawienia(); bez tego pliku ścieżki domyślne z kontraktu."""
    global _system_settings
    if _system_settings is None:
        path = os.path.join(ROOT, "system", "wspolne.py")
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("integrate_system_wspolne", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            _system_settings = module.ustawienia
        except (OSError, ImportError, AttributeError, SyntaxError):
            def _system_settings():
                return {k: os.path.abspath(os.path.expanduser(os.environ.get(k) or v))
                        for k, v in (("STAN_DIR", "~/stan-systemu"), ("LOKALNE_DIR", "~/.integrate-lokalne"))}
    return _system_settings()


def collector_projects():
    """[(folder, decyzja)] dla projektów zakwalifikowanych zbieraczem na tym komputerze.

    Folder z LOKALNE_DIR/aliasy.json, decyzja: ostatni wiersz dla tożsamości w STAN_DIR/mac/decyzje.jsonl.
    Brak plików albo nieczytelne wiersze nie są błędem. Pomija foldery, których nie ma na dysku.
    """
    try:
        u = system_settings()
    except Exception:  # noqa: BLE001  (uszkodzony system.env nie może zatrzymać panelu)
        return []
    try:
        with open(os.path.join(u["LOKALNE_DIR"], "aliasy.json"), encoding="utf-8") as f:
            aliases = json.load(f)
    except (OSError, ValueError):
        return []
    if not isinstance(aliases, dict):
        return []
    last = {}
    try:
        with open(os.path.join(u["STAN_DIR"], "mac", "decyzje.jsonl"), encoding="utf-8") as f:
            for line in f:
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                if isinstance(d, dict) and isinstance(d.get("tozsamosc"), str):
                    last[d["tozsamosc"]] = d
    except (OSError, UnicodeDecodeError):
        return []
    out = []
    for ident in sorted(last, key=lambda k: str(last[k].get("czas", ""))):
        d = last[ident]
        entry = aliases.get(ident)
        if str(d.get("stan", "")).strip().lower() not in COLLECTOR_STATE or not isinstance(entry, dict):
            continue
        folder = entry.get("sciezka")
        if not isinstance(folder, str) or not folder.strip():
            continue
        folder = os.path.abspath(os.path.expanduser(folder))
        if os.path.isdir(folder):
            out.append((folder, d))
    return out


def all_folders():
    """[(folder, źródło, decyzja)]: rejestr, potem zbieracz; bez powtórzeń po realpath.

    Gdy folder jest w obu źródłach, zostaje wpis z rejestru z decyzją zbieracza (alias, klient, stan).
    """
    out, seen = [], {}
    for folder in registry():
        real = os.path.realpath(folder)
        if real not in seen:
            seen[real] = len(out)
            out.append([folder, "registry", None])
    for folder, decision in collector_projects():
        real = os.path.realpath(folder)
        if real in seen:
            out[seen[real]][2] = decision
        else:
            seen[real] = len(out)
            out.append([folder, "collector", decision])
    return [tuple(x) for x in out]


# ---------- rejestr projektów ----------
def registry_raw():
    try:
        with open(REGISTRY, encoding="utf-8") as f:
            data = json.load(f)
        return [str(p) for p in data.get("projekty", [])]
    except (OSError, ValueError, AttributeError):
        return []


def registry():
    """Foldery z rejestru, które istnieją."""
    out = []
    for p in registry_raw():
        full = os.path.abspath(os.path.expanduser(p))
        if os.path.isdir(full) and full not in out:
            out.append(full)
    return out


def registry_save(paths):
    home = os.path.expanduser("~")
    short = [("~" + p[len(home):]) if p.startswith(home + os.sep) else p for p in paths]
    write_atomic(REGISTRY, json.dumps({"projekty": short}, ensure_ascii=False, indent=2) + "\n")


# ---------- polecenia ----------
def _fill(text, name, today):
    def date(m):
        return (today + datetime.timedelta(days=int(m.group(1) or 0))).isoformat()
    return re.sub(r"\{\{DATA([+-]\d+)?\}\}", date, text.replace("{{NAZWA}}", name))


def cmd_nowy(folder, name=None, register=False):
    folder = os.path.abspath(os.path.expanduser(folder))
    name = name or os.path.basename(folder)
    today = datetime.date.today()
    os.makedirs(folder, exist_ok=True)
    for base, _, files in os.walk(TEMPLATE):
        for fn in sorted(files):
            src = os.path.join(base, fn)
            rel = os.path.relpath(src, TEMPLATE)
            dst = os.path.join(folder, rel)
            body = _fill(read(src), name, today)
            if not os.path.exists(dst):
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                with open(dst, "w", encoding="utf-8") as f:
                    f.write(body)
                print("  utworzono  ", rel)
            elif rel in ("CLAUDE.md", "AGENTS.md") and BLOCK[0] not in (read(dst) or ""):
                # Istniejące instrukcje zostają; dopisujemy tylko importy i blok standardu.
                block = body[body.index(BLOCK[0]):body.index(BLOCK[1]) + len(BLOCK[1])]
                lead = "@KARTA.md\n@ZADANIA.md\n\n" if rel == "CLAUDE.md" else "Na początku sesji przeczytaj KARTA.md i ZADANIA.md.\n\n"
                with open(dst, "a", encoding="utf-8") as f:
                    f.write("\n\n" + lead + block + "\n")
                print("  uzupełniono", rel, "(dopisany blok standardu)")
            else:
                print("  pominięto  ", rel, "(już istnieje)")
    if register:
        cmd_dodaj(folder)
    print("Gotowe. Sprawdź braki: python3 %s sprawdz %s" % (os.path.relpath(__file__), folder))


def cmd_kampania(folder, name):
    folder = os.path.abspath(os.path.expanduser(folder))
    dst = os.path.join(folder, "kampanie", slug(name) + ".md")
    if os.path.exists(dst):
        print("Już istnieje:", dst)
        return 1
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "w", encoding="utf-8") as f:
        f.write(_fill(read(CAMPAIGN_TEMPLATE), name, datetime.date.today()))
    print("Utworzono", dst)
    return 0


def cmd_sprawdz(folders):
    folders = folders or registry()
    if not folders:
        print("Brak projektów. Podaj folder albo dodaj projekt: python3 projekt.py dodaj <folder>")
        return 2
    mark = {"ok": "ok   ", "gaps": "braki", "missing": "BRAK "}
    worst = 0
    for folder in folders:
        d = read_project(folder)
        p = d["project"]
        open_tasks = sum(1 for t in d["tasks"] if t["state"] != "done")
        print("%s  (%s)" % (p["name"], os.path.abspath(os.path.expanduser(folder))))
        print("  standard: %d z %d dokumentów kompletnych · zadania otwarte: %d · etapy: %d · kampanie: %d"
              % (p["docsOk"], p["docsTotal"], open_tasks, len(d["stages"]), len(d["campaigns"])))
        for doc in p["docs"]:
            print("  [%s] %-22s %s" % (mark[doc["status"]], doc["file"], "; ".join(doc["gaps"])))
        for c in d["campaigns"]:
            print("  [%s] %-22s %s" % (mark["gaps" if c["gaps"] else "ok"], c["file"], "; ".join(c["gaps"])))
        if p["docsOk"] < p["docsTotal"] or any(c["gaps"] for c in d["campaigns"]):
            worst = 1
        print()
    return worst


def cmd_dodaj(folder):
    full = os.path.abspath(os.path.expanduser(folder))
    if not os.path.isdir(full):
        print("Nie ma takiego folderu:", full)
        return 1
    paths = registry()
    if full not in paths:
        paths.append(full)
        registry_save(paths)
    print("W rejestrze panelu:", full)
    return 0


def cmd_usun(folder):
    full = os.path.abspath(os.path.expanduser(folder))
    registry_save([p for p in registry() if p != full])
    print("Usunięto z rejestru (pliki projektu bez zmian):", full)
    return 0


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help", "pomoc"):
        print(__doc__)
        return 0
    cmd, args = argv[1], argv[2:]
    flags = [a for a in args if a.startswith("--")]
    pos, name, skip = [], None, False
    for i, a in enumerate(args):
        if skip:
            skip = False
        elif a == "--nazwa" and i + 1 < len(args):
            name, skip = args[i + 1], True
        elif not a.startswith("--"):
            pos.append(a)
    if cmd == "nowy" and pos:
        cmd_nowy(pos[0], name, "--rejestruj" in flags)
        return 0
    if cmd == "kampania" and len(pos) >= 2:
        return cmd_kampania(pos[0], pos[1])
    if cmd == "sprawdz":
        return cmd_sprawdz(pos)
    if cmd == "dodaj" and pos:
        return cmd_dodaj(pos[0])
    if cmd == "usun" and pos:
        return cmd_usun(pos[0])
    if cmd == "lista":
        print("\n".join(registry()) or "Rejestr jest pusty. Panel pokazuje projekty przykładowe.")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
