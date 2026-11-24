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


def post_dir(cards, day):
    """Istniejący folder posta posty/<dzień>-…/ (albo posty/<dzień>/) w folderze karty; None, gdy go nie ma."""
    base = os.path.join(cards, "posty")
    try:
        names = sorted(n for n in os.listdir(base) if n == day or n.startswith(day + "-"))
    except OSError:
        return None
    for n in names:
        path = os.path.join(base, n)
        if os.path.isdir(path):
            return path
    return None


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
