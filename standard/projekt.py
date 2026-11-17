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
    m = re.search(r"\d+(?:[.,]\d+)?", str(value or "").replace(" ", ""))
    return float(m.group(0).replace(",", ".")) if m else None


def parse_task(line):
    """Wiersz '- [ ] Tytuł | kto: claude | kiedy: 2026-11-12' -> słownik albo None."""
    m = TASK.match(line)
    if not m:
        return None
    parts = re.split(r"\s*\|\s*", m.group(2))
    t = {"title": parts[0], "state": STATE[m.group(1)], "executor": "", "machine": "", "date": "", "slot": "",
         "minutes": 0, "needsYou": "", "blocked": "", "channel": "", "errors": []}
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
            t["needsYou"] = NEEDS.get(v.lower(), "")
            bad = None if t["needsYou"] else "wymaga: %s (dozwolone: zgoda, odbiór)" % v
        elif k == "blokada":
            t["blocked"] = v
        elif k in ("kanał", "kanal"):
            t["channel"] = v
        else:
            bad = "nieznane pole „%s”" % k
        if bad:
            t["errors"].append(bad)
    return t


def _task(t, pid, file_rel, no, kind, **extra):
    errors = t.pop("errors")
    t.update({"id": "%s|%s|%d" % (pid, file_rel, no), "project": pid, "file": file_rel, "line": no, "kind": kind,
              "stage": "", "group": "", "campaign": ""})
    t.update(extra)
    return ["wiersz %d: %s" % (no, e) for e in errors]


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
        for no, line in sec["body"]:
            t = parse_task(line)
            if t:
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
            for no, line in sec["body"]:
                t = parse_task(line)
                if t:
                    gaps += _task(t, pid, file_rel, no, "publikacja", campaign=cid, group=name)
                    tasks.append(t)
            if not tasks:
                gaps.append("harmonogram bez publikacji")
        elif not is_filled(sec["body"]) and (title != "Wyniki i wnioski" or state == "done"):
            gaps.append("sekcja „%s” do uzupełnienia" % title)
    camp = {"id": cid, "project": pid, "name": name, "state": state or "plan", "goal": meta.get("cel", ""),
            "metric": meta.get("miernik", ""), "target": number_of(meta.get("cel liczbowy")),
            "result": number_of(meta.get("wynik")), "start": dates["start"], "end": dates["koniec"],
            "channels": [c.strip() for c in meta.get("kanały", "").split(",") if c.strip()],
            "budget": meta.get("budżet", ""), "file": file_rel, "gaps": gaps}
    return camp, tasks


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
    if karta is not None and fields["errors"]:
        karta_doc["gaps"] += fields["errors"]
        karta_doc["status"] = "gaps"
    docs.append(karta_doc)

    stages, tasks, campaigns = [], [], []
    if texts["ZADANIA.md"] is None:
        docs.append(_doc("zadania", "Zadania", "ZADANIA.md", "missing", ["brak pliku ZADANIA.md"]))
    else:
        stages, tasks, problems = parse_tasks(texts["ZADANIA.md"], pid)
        if not stages:
            problems.insert(0, "brak etapów (nagłówek „## Etap: nazwa”)")
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

    for f in sorted(glob.glob(os.path.join(glob.escape(path), "kampanie", "*.md"))):
        text = read(f)
        if text is not None:
            camp, pubs = parse_campaign(text, pid, "kampanie/" + os.path.basename(f))
            campaigns.append(camp)
            tasks += pubs

    docs_ok = sum(1 for d in docs if d["status"] == "ok")
    project = {"id": pid, "name": name, "goal": goal, "description": description, "state": fields["state"],
               "machine": WHERE.get(meta.get("maszyna", "").lower(), ""), "repo": meta.get("repozytorium", ""),
               "decisions": len(decisions), "lastDecision": decisions[0] if decisions else None,
               "docs": docs, "docsOk": docs_ok, "docsTotal": len(docs),
               "book": [dict(d, gaps=list(d["gaps"])) for d in docs], "bookOk": docs_ok, "bookTotal": len(docs),
               "client": fields["client"], "threshold": fields["threshold"], "alias": fields["alias"],
               "questions": parse_questions(sections) if karta is not None else []}
    if fields["phase"]:
        project["phase"], project["phaseSource"] = fields["phase"], "karta"
    else:
        project["phase"] = compute_phase(project["state"], karta_doc, stages, tasks, campaigns)
        project["phaseSource"] = "wyliczona"
    return {"project": project, "stages": stages, "tasks": tasks, "campaigns": campaigns}


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
    """Pola karty: stan, faza, klient, próg, alias. Karta wygrywa z decyzją zbieracza.

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
    return {"state": state, "phase": phase, "client": client, "threshold": threshold, "alias": alias, "errors": errors}


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
KNOWN = {"kto", "gdzie", "kiedy", "pora", "czas", "wymaga", "blokada", "kanał", "kanal"}
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
                         ("wymaga", t["needsYou"]), ("blokada", t["blocked"]), ("kanał", t["channel"])):
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
        elif k == "date":
            v = _day(v) if v else ""
        elif k == "minutes":
            if isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= 1440:
                raise ValueError("czas w minutach, od 0 do 1440")
        elif k in ("blocked", "channel"):
            v = _clean(v, 120)
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


def parse_questions(sections):
    """Pytania z sekcji „Pytania do właściciela” w KARTA.md: wiersz „1. pytanie” albo „- pytanie”,
    pod nim opcjonalnie wcięty wiersz „Odpowiedź: …”. Zwraca [{n, text, answer, line}]."""
    sec = section(sections, QUESTIONS_TITLE)
    out = []
    for no, line in (sec["body"] if sec else []):
        m = QUESTION.match(line)
        a = ANSWER.match(line)
        if a and out:
            out[-1]["answer"] = a.group(1).strip()
        elif m and PLACEHOLDER not in line:
            out.append({"n": len(out) + 1, "text": m.group(2).strip(), "answer": "", "line": no})
        elif line.startswith((" ", "\t")) and line.strip() and out and not out[-1]["answer"]:
            out[-1]["text"] += " " + line.strip()
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


def set_card_fields(root, changes):
    """Zmienia albo dopisuje wiersze „- faza:”, „- klient:”, „- próg:” pod tytułem KARTA.md.

    changes: {"phase"?, "client"?, "threshold"?}. ValueError przy złej wartości, OSError bez pliku karty.
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
