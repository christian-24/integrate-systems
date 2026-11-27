"""Scenariusz nagrania: plik scenariusz.md w folderze posta (posty/<dzień>-<nazwa>/), opis w standard/STANDARD.md.

Film, który nagrywa właściciel (pole karty `- nagrywa: ty`), dostaje scenariusz: co nagrać, jak, po co. Agent pisze
propozycję, właściciel ją poprawia (rozmowa albo edycja tekstu), wysyła do realizacji i oznacza jako nagraną.

Układ pliku:

    # Scenariusz nagrania: <tytuł>

    - stan: propozycja | do realizacji | nagrane
    - publikacja: RRRR-MM-DD
    - nagranie: RRRR-MM-DD
    - sposób: ty | ai | panel     (kto robi film: nagrywasz telefonem, robisz w narzędziu AI, nagrywa panel)

    ## Po co
    ## Co nagrać          (wiersze `- [ ] opis ujęcia | 5 s`)
    ## Jak
    ## Co powiedzieć
    ## Na koniec
    ## Gotowe gdy
"""
import datetime
import hashlib
import os
import re

FILE = "scenariusz.md"
SECTIONS = ("Po co", "Co nagrać", "Jak", "Co powiedzieć", "Na koniec", "Gotowe gdy")
STATES = ("propozycja", "do realizacji", "nagrane")
MAX_TEXT = 12000                    # znaków; treść idzie w JSON do 32 KB (CHAT_BODY)
TITLE_PREFIX = "Scenariusz nagrania:"
PLACEHOLDER = "_Do uzupełnienia"

# zadania w ZADANIA.md (tytuł zaczyna się od tych słów, potem dzień publikacji)
PREP_TASK = "Przygotuj scenariusz nagrania na "
FIX_TASK = "Popraw scenariusz nagrania na "
REC_TASK = "Nagraj według scenariusza na "        # nie „Nagraj film …”: to nazwa filmów, które nagrywa panel
AGENT_TASK = "Zrób film według scenariusza na "
REC_MINUTES = 30                                    # czas właściciela na nagranie, gdy scenariusz nie podaje długości
WAYS = {"ty": "nagrywasz sam", "ai": "robisz w AI", "panel": "nagrywa panel"}


def pick_way(mix, used):
    """Sposób dla następnego filmu wg podziału karty (mix: {sposób: %}) i dotychczasowych scenariuszy (used: {sposób: ile}):
    ten, któremu najwięcej brakuje do swojego udziału; remis: kolejność ty, ai, panel."""
    if not mix:
        return "ty"
    total = sum(used.get(k, 0) for k in mix) + 1
    return max(mix, key=lambda k: (mix[k] / 100.0 - used.get(k, 0) / total, -list(WAYS).index(k)))

SHOT = re.compile(r"^\s*[-*]\s+\[( |x|X)\]\s+(.+?)\s*$")
SECONDS = re.compile(r"^(\d{1,4})\s*(s|sek\.?|sekund[ay]?)$", re.I)
META = re.compile(r"^\s*-\s+([^:]{1,30}):\s*(.*?)\s*$")
DAY = re.compile(r"^\d{4}-\d\d-\d\d$")
FILM_WORDS = re.compile(r"film|wideo|video|reel", re.I)
FILM_CHANNELS = re.compile(r"reels|tiktok|youtube|shorts", re.I)


def is_film(task):
    """Publikacja z filmem: słowo „film” (wideo, reel) w tytule albo kanał filmowy (Reels, TikTok, YouTube)."""
    return bool(FILM_WORDS.search(task.get("title") or "") or FILM_CHANNELS.search(task.get("channel") or ""))


def shot_of(text):
    """„Ujęcie miernika z bliska | 5 s” -> {"text", "seconds"} (seconds 0, gdy brak czasu)."""
    head, sep, tail = text.rpartition("|")
    m = SECONDS.match(tail.strip()) if sep else None
    if m:
        return {"text": head.strip(), "seconds": int(m.group(1))}
    return {"text": text.strip(), "seconds": 0}


def parse(text):
    """Tekst scenariusza -> {"title", "state", "publication", "recording", "sections": {nazwa: tekst},
    "shots": [{"text", "seconds", "done"}], "seconds", "errors": [...]}. Błędy nie przerywają odczytu."""
    out = {"title": "", "state": "", "publication": "", "recording": "", "way": "", "sections": {}, "shots": [],
           "seconds": 0, "errors": []}
    name, head = None, True
    for raw in (text or "").replace("\r\n", "\n").split("\n"):
        line = raw.rstrip()
        if line.startswith("# ") and not out["title"] and name is None:
            out["title"] = re.sub(r"^%s\s*" % re.escape(TITLE_PREFIX), "", line[2:].strip(), flags=re.I).strip()
            continue
        if line.startswith("## "):
            name, head = line[3:].strip(), False
            out["sections"].setdefault(name, "")
            continue
        if head:
            m = META.match(line)
            if m:
                key, value = m.group(1).strip().lower(), m.group(2)
                if key == "stan":
                    out["state"] = value.lower()
                elif key == "publikacja":
                    out["publication"] = value
                elif key == "nagranie":
                    out["recording"] = value
                elif key in ("sposób", "sposob"):
                    out["way"] = value.strip().lower() if value.strip().lower() in WAYS else ""
            continue
        if name is None:
            continue
        out["sections"][name] += line + "\n"
        if name == "Co nagrać":
            m = SHOT.match(line)
            if m:
                shot = shot_of(m.group(2))
                shot["done"] = m.group(1).lower() == "x"
                out["shots"].append(shot)
    out["sections"] = {k: v.strip() for k, v in out["sections"].items()}
    out["seconds"] = sum(s["seconds"] for s in out["shots"])
    if not out["title"]:
        out["errors"].append("brak tytułu (# %s …)" % TITLE_PREFIX)
    if out["state"] not in STATES:
        out["errors"].append("stan: %s (dozwolone: %s)" % (out["state"] or "brak", ", ".join(STATES)))
    for key in ("publication", "recording"):
        if out[key] and not DAY.match(out[key]):
            out["errors"].append("%s: %s (format RRRR-MM-DD)" % ("publikacja" if key == "publication" else "nagranie",
                                                                out[key]))
    missing = [s for s in SECTIONS if not out["sections"].get(s) or PLACEHOLDER in out["sections"][s]]
    if missing:
        out["errors"].append("brak sekcji: %s" % ", ".join(missing))
    if not out["shots"]:
        out["errors"].append("„Co nagrać” bez ujęć (wiersze - [ ] opis | 5 s)")
    elif any(not s["seconds"] for s in out["shots"]):
        out["errors"].append("ujęcie bez czasu trwania (na końcu wiersza | 5 s)")
    return out


def skeleton(title, publication, recording):
    """Wzór pliku (opis w poleceniu dla agenta i w testach)."""
    return "\n".join([
        "# %s %s" % (TITLE_PREFIX, title), "",
        "- stan: propozycja", "- publikacja: %s" % publication, "- nagranie: %s" % recording, "",
        "## Po co", "Cel filmu i dla kogo jest, jedno-dwa zdania.", "",
        "## Co nagrać", "- [ ] Ujęcie 1: co widać w kadrze | 5 s", "- [ ] Ujęcie 2: … | 10 s", "",
        "## Jak", "- Miejsce: …", "- Światło: …", "- Kadr: telefon pionowo, …", "- Rekwizyty: …", "",
        "## Co powiedzieć", "Tekst do powiedzenia albo punkty.", "",
        "## Na koniec", "Wezwanie do działania.", "",
        "## Gotowe gdy", "Sprawdzalny warunek: np. 3 ujęcia, razem do 30 s, dźwięk bez szumu.", ""])


def set_state(text, state):
    """Zmienia (albo dopisuje pod tytułem) wiersz `- stan:`. ValueError przy nieznanym stanie."""
    if state not in STATES:
        raise ValueError("stan: %s" % ", ".join(STATES))
    lines = (text or "").replace("\r\n", "\n").split("\n")
    for i, line in enumerate(lines):
        if line.startswith("## "):
            break
        m = META.match(line)
        if m and m.group(1).strip().lower() == "stan":
            lines[i] = "- stan: %s" % state
            return "\n".join(lines)
    at = next((i + 1 for i, line in enumerate(lines) if line.startswith("# ")), 0)
    lines[at:at] = ["", "- stan: %s" % state] if at else ["- stan: %s" % state, ""]
    return "\n".join(lines)


def version(text):
    """Skrót treści do zapisu bez nadpisania cudzej zmiany (pole old w trasach panelu)."""
    return hashlib.sha1((text or "").encode("utf-8")).hexdigest()[:16]


def read(folder):
    """Tekst scenariusz.md folderu posta albo None."""
    try:
        with open(os.path.join(folder, FILE), encoding="utf-8") as f:
            return f.read()
    except (OSError, UnicodeDecodeError):
        return None


def summary(folder):
    """Krótki stan scenariusza do danych panelu: {"state", "shots", "seconds", "errors"} albo None (brak pliku)."""
    text = read(folder) if folder else None
    if text is None:
        return None
    p = parse(text)
    return {"state": p["state"] if p["state"] in STATES else "propozycja", "shots": len(p["shots"]),
            "seconds": p["seconds"], "errors": len(p["errors"])}


def post_dir(cards, day, skip=()):
    """Istniejący folder posta posty/<dzień>-…/ (albo posty/<dzień>/) w folderze karty; None, gdy go nie ma.
    skip: foldery przypisane innym publikacjom (assign), pomijane."""
    base = os.path.join(cards, "posty")
    try:
        names = sorted(n for n in os.listdir(base) if n == day or n.startswith(day + "-"))
    except OSError:
        return None
    for n in names:
        path = os.path.join(base, n)
        if os.path.isdir(path) and path not in skip:
            return path
    return None


# ---------- folder posta filmu niezależnie od daty publikacji (STANDARD.md „Scenariusz nagrania”) ----------
QUOTES = re.compile(r"[\"'`„”“‟«»‚‘’‛]")
REF_POST = re.compile(r"^posty/([^/#\s]+)")
FILM_FILES = ("scenariusz.json", "film.mp4", "film.mov")     # film robiony przez panel (film.SCENARIO, FILM_NAMES)
_heads = {}                                                  # ścieżka scenariusz.md -> ((mtime, rozmiar), tytuł, publikacja)


def norm_title(text):
    """Tytuł do porównań: bez cudzysłowów, wielkości liter, nadmiaru spacji, „Opublikuj”/„Film” na początku
    i kropki na końcu. „Film Wygłuszanie: „Ten sam puk.”” -> „wygłuszanie: ten sam puk”."""
    t = re.sub(r"\s+", " ", QUOTES.sub("", str(text or ""))).strip().casefold()
    t = re.sub(r"^%s\s*" % re.escape(TITLE_PREFIX.casefold()), "", t)
    t = re.sub(r"^opublikuj\s+", "", t)
    t = re.sub(r"^film\s+", "", t)
    return t.rstrip(" .…!?").strip()


def same_title(a, b):
    """Ten sam tytuł po norm_title. Ucięty dłuższy tytuł (zadanie do 120 znaków, pub_title do 100) też pasuje,
    gdy krótszy ma co najmniej 40 znaków."""
    a, b = norm_title(a), norm_title(b)
    if not a or not b:
        return False
    short, other = sorted((a, b), key=len)
    return a == b or (len(short) >= 40 and other.startswith(short))


def ref_posts(pub):
    """Nazwy folderów z wierszy `materiał: posty/<folder>/…` publikacji, w kolejności wierszy."""
    out = []
    for r in (pub.get("detail") or {}).get("refs") or []:
        m = REF_POST.match(str((r.get("path") if isinstance(r, dict) else r) or "").strip().strip("`"))
        if m and m.group(1) not in (".", "..") and m.group(1) not in out:
            out.append(m.group(1))
    return out


def _head(folder):
    """(tytuł, pole publikacja) scenariusz.md folderu albo None, gdy pliku nie ma. Pamięć po czasie zmiany pliku."""
    path = os.path.join(folder, FILE)
    try:
        st = os.stat(path)
    except OSError:
        return None
    key = (st.st_mtime_ns, st.st_size)
    hit = _heads.get(path)
    if not hit or hit[0] != key:
        text = read(folder) or ""
        p = parse(text)
        head = next((ln for ln in text.split("\n") if ln.startswith("# ")), "")
        titled = head[2:].strip().casefold().startswith(TITLE_PREFIX.casefold())   # tylko pełny nagłówek wiąże
        hit = _heads[path] = (key, p["title"] if titled else "", p["publication"])
    return hit[1], hit[2]


def _entries(base):
    """Foldery posty/*/: nazwa, ścieżka, dzień z nazwy, scenariusz (tytuł, pole publikacja), film panelu."""
    try:
        names = sorted(os.listdir(base))
    except OSError:
        return []
    out = []
    for n in names:
        path = os.path.join(base, n)
        if n.startswith(".") or not os.path.isdir(path):
            continue
        head = _head(path)
        try:
            files = os.listdir(path)
        except OSError:
            files = []
        out.append({"name": n, "path": path, "day": n[:10] if DAY.match(n[:10]) and n[10:11] in ("", "-") else "",
                    "script": head is not None, "title": head[0] if head else "", "pubday": head[1] if head else "",
                    "film": any(f in FILM_FILES for f in files)})
    return out


def _gap(a, b):
    try:
        return abs((datetime.date.fromisoformat(a) - datetime.date.fromisoformat(b)).days)
    except ValueError:
        return 10 ** 6


def _named(entry, slug, day):
    """Nazwa folderu z tytułu publikacji (new_post_dir), także ucięta."""
    rest, want = entry["name"][len(day) + 1:], slug[len(day) + 1:]
    return bool(rest) and (rest == want or (len(rest) >= 12 and (want.startswith(rest) or rest.startswith(want))))


def assign(cards, pubs):
    """Foldery posta publikacji z filmem jednego projektu: {id publikacji: ścieżka folderu}. pubs: publikacje
    projektu (wszystkie rodzaje, z detail.refs). Kolejność rozpoznania, folder raz przypisany nie trafia do drugiej:
    a) wiersz `materiał: posty/<folder>/…` pod publikacją (istniejący folder);
    b) folder, którego scenariusz.md ma tytuł publikacji (same_title z pub_title); przy kilku: dzień w nazwie równy
       dniowi publikacji, potem pole `- publikacja:`, potem najbliższy dzień;
    c) folder dnia publikacji, bez scenariusza z innym tytułem: z nazwą z tytułu (new_post_dir), z filmem panelu,
       gdy to jedyny film tego dnia, albo dowolny, gdy to jedyna publikacja tego dnia.
    Post innej publikacji z tą samą datą (np. post ze zdjęciami) nie przechodzi do filmu."""
    day_of = lambda p: str(p.get("date") or "")[:10]
    films = sorted((p for p in pubs if is_film(p) and p.get("row") != "reklama"), key=lambda p: (day_of(p), str(p.get("id") or "")))
    if not films:
        return {}
    base = os.path.join(cards, "posty")
    entries = _entries(base)
    by_name = {e["name"]: e for e in entries}
    out, taken = {}, set()

    def give(p, e):
        out[p["id"]] = e["path"]
        taken.add(e["path"])

    for p in films:                                          # a) materiał
        e = next((by_name[n] for n in ref_posts(p) if n in by_name and by_name[n]["path"] not in taken), None)
        if e:
            give(p, e)
    for rule in ("dzień", "pole", "najbliższy"):            # b) tytuł w scenariusz.md
        for p in films:
            if p["id"] in out:
                continue
            title, day = pub_title(p), day_of(p)
            c = [e for e in entries if e["path"] not in taken and e["title"] and same_title(e["title"], title)]
            if rule == "dzień":
                c = [e for e in c if e["day"] == day]
            elif rule == "pole":
                c = [e for e in c if e["pubday"] == day]
            else:
                c.sort(key=lambda e: (_gap(e["day"] or e["pubday"], day), e["name"]))
            if c:
                give(p, c[0])
    per_day, films_day = {}, {}
    for p in pubs:
        if p.get("row", "publikacja") in ("publikacja", ""):
            per_day[day_of(p)] = per_day.get(day_of(p), 0) + 1
            if is_film(p):
                films_day[day_of(p)] = films_day.get(day_of(p), 0) + 1
    for p in films:                                          # c) data, tylko bez wątpliwości
        day = day_of(p)
        if p["id"] in out or not DAY.match(day):
            continue
        title = pub_title(p)
        slug = os.path.basename(new_post_dir(cards, day, title))
        c = [e for e in entries if e["path"] not in taken and e["day"] == day
             and not (e["title"] and not same_title(e["title"], title))]
        pick = [e for e in c if _named(e, slug, day)]
        if not pick and films_day.get(day) == 1:
            pick = [e for e in c if e["film"]]
        if not pick and per_day.get(day) == 1:
            pick = [e for e in c if "-reklama-" not in e["name"]]
        if pick:
            give(p, pick[0])
    return out


BACKUP = ".scenariusz-poprzedni.md"          # poprzednia wersja po zapisie dużo krótszej treści z panelu
SHRINK = 0.6                                 # nowy tekst krótszy niż 60% starego wymaga potwierdzenia


def shrink(old, new):
    """Opis utraty treści przy zapisie new w miejsce old („jest dużo krótszy …”, „nie ma sekcji …”) albo ""."""
    old, new = (old or "").strip(), (new or "").strip()
    if not old:
        return ""
    if len(new) < len(old) * SHRINK:
        return "jest dużo krótszy od zapisanego (%d z %d znaków)" % (len(new), len(old))
    was, now = parse(old)["sections"], parse(new)["sections"]
    gone = [n for n, v in was.items() if v and PLACEHOLDER not in v and not now.get(n)]
    if gone:
        return "nie ma treści sekcji: %s" % ", ".join(gone)
    return ""


def prep_of(task_title, pub):
    """Zadanie „Przygotuj scenariusz nagrania na <dzień>: <tytuł>” tej publikacji (po tytule; dzień dowolny, bo
    publikacja mogła zmienić kiedy:)."""
    t = str(task_title or "")
    if not t.startswith(PREP_TASK):
        return False
    rest = t[len(PREP_TASK):]
    return DAY.match(rest[:10]) is not None and rest[10:12] == ": " and same_title(rest[12:], pub_title(pub))


def link(projekt, folder, pid, pub, post):
    """Dopisuje pod publikacją `materiał: posty/<folder posta>/scenariusz.md`, gdy go nie ma: film zostaje powiązany
    ze scenariuszem niezależnie od kiedy:. Wiersz publikacji czytany od nowa (wcześniejsze dopisania przesuwają
    wiersze). Wywołujący trzyma blokadę zapisu. True, gdy dopisano."""
    name = os.path.basename(post)
    try:
        fresh = next((t for t in projekt.read_project(folder, pid)["tasks"] if t["file"] == pub.get("file")
                      and t["title"] == pub.get("title") and str(t.get("date") or "") == str(pub.get("date") or "")),
                     None)
    except (OSError, ValueError):
        fresh = None
    pub = fresh or pub
    if name in ref_posts(pub) or not pub.get("file") or not pub.get("line"):
        return False
    refs = [(r.get("path", "") + ("#" + r["anchor"] if r.get("anchor") else "")) if isinstance(r, dict) else str(r)
            for r in (pub.get("detail") or {}).get("refs") or []]
    try:
        return projekt.set_detail(folder, pub["file"], pub["line"], pub["title"], "materiał",
                                  refs + ["posty/%s/%s" % (name, FILE)]) is True
    except (ValueError, OSError):
        return False


def new_post_dir(cards, day, title):
    """Ścieżka nowego folderu posta posty/<dzień>-<nazwa z tytułu>/ w folderze karty (ta sama konwencja co posty
    agenta). Folderu nie zakłada: zakłada go agent razem z plikiem (pusty folder posta wstrzymałby przygotowanie
    posta w stałym rytmie)."""
    name = re.sub(r"[^a-z0-9]+", "-", _ascii(title).lower()).strip("-")[:40].strip("-") or "film"
    return os.path.join(cards, "posty", "%s-%s" % (day, name))


def _ascii(text):
    import unicodedata
    text = str(text or "").replace("ł", "l").replace("Ł", "L")
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


def pub_title(task):
    """Tytuł publikacji bez „Opublikuj” i cudzysłowów na brzegach: „Film o mierniku”."""
    t = re.sub(r"^Opublikuj\s+", "", str(task.get("title") or "")).strip()
    t = t[:1].upper() + t[1:]
    return re.sub(r"\s+", " ", t)[:100] or "Film"


def rec_day(day, today=None):
    """Dzień nagrania: dzień przed publikacją, najwcześniej dziś (RRRR-MM-DD)."""
    today = today or datetime.date.today()
    try:
        d = datetime.date.fromisoformat(day) - datetime.timedelta(days=1)
    except ValueError:
        return today.isoformat()
    return max(d, today).isoformat()
