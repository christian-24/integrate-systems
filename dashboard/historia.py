"""Historia stanów projektów: jeden plik JSON na dzień, kontrakt w PULPIT.md (sekcja 3).

Plik HISTORIA_DIR/RRRR-MM-DD.json (domyślnie ../historia/, zmienna PANEL_HISTORY_DIR):
  {"date": "RRRR-MM-DD", "projects": {"<pid>": {"todo", "wip", "rev", "blocked", "done", "total"}}}
Liczone są tylko zadania (kind = zadanie); publikacje kampanii nie wchodzą do historii.
Tylko biblioteka standardowa Pythona.
"""
import datetime
import glob
import json
import os
import re
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DIR = os.path.join(os.path.dirname(HERE), "historia")
DAYS = 63
KEYS = ("todo", "wip", "rev", "blocked", "done", "total")
FILE = re.compile(r"^(\d{4}-\d\d-\d\d)\.json$")
REL = re.compile(r"^([+-]?\d+)$")


def directory():
    """Katalog historii; PANEL_HISTORY_DIR czytana przy każdym użyciu (testy, osobny zestaw danych)."""
    raw = os.environ.get("PANEL_HISTORY_DIR", "").strip()
    return os.path.abspath(os.path.expanduser(raw)) if raw else DEFAULT_DIR


def counts(tasks):
    """Liczby stanów jednej listy zadań. Kolejność reguł: zrobione, do odbioru, zablokowane, w toku, reszta."""
    c = dict.fromkeys(KEYS, 0)
    for t in tasks:
        if t.get("kind", "zadanie") != "zadanie" or t["state"] == "cancelled":
            continue
        c["total"] += 1
        if t["state"] == "done":
            c["done"] += 1
        elif t.get("needsYou") == "odbiór":
            c["rev"] += 1
        elif t["state"] == "blocked":
            c["blocked"] += 1
        elif t["state"] == "doing":
            c["wip"] += 1
        else:
            c["todo"] += 1
    return c


def snapshot(tasks, project_ids, today=None):
    """Wpis historii na dziś dla podanych projektów (także tych bez zadań)."""
    day = (today or datetime.date.today()).isoformat()
    by = {pid: [] for pid in project_ids}
    for t in tasks:
        if t.get("project") in by:
            by[t["project"]].append(t)
    return {"date": day, "projects": {pid: counts(ts) for pid, ts in by.items()}}


def _write_atomic(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".tmp-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def _valid(entry):
    if not isinstance(entry, dict) or not isinstance(entry.get("projects"), dict):
        return False
    if not isinstance(entry.get("date"), str):
        return False
    for c in entry["projects"].values():
        if not isinstance(c, dict) or any(not isinstance(c.get(k), int) or isinstance(c.get(k), bool) for k in KEYS):
            return False
    return True


def save(entry, folder=None):
    """Zapisuje wpis dnia (nadpisuje plik z tego dnia). Bez zmian w treści pliku nie rusza."""
    folder = folder or directory()
    path = os.path.join(folder, entry["date"] + ".json")
    text = json.dumps(entry, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    try:
        with open(path, encoding="utf-8") as f:
            if f.read() == text:
                return False
    except (OSError, UnicodeDecodeError):
        pass
    _write_atomic(path, text)
    return True


def load(today=None, days=DAYS, folder=None):
    """Wpisy z ostatnich `days` dni (dziś włącznie), rosnąco po dacie. Uszkodzone pliki są pomijane."""
    today = today or datetime.date.today()
    first = (today - datetime.timedelta(days=days - 1)).isoformat()
    out = []
    for path in sorted(glob.glob(os.path.join(glob.escape(folder or directory()), "*.json"))):
        m = FILE.match(os.path.basename(path))
        if not m or not first <= m.group(1) <= today.isoformat():
            continue
        try:
            with open(path, encoding="utf-8") as f:
                entry = json.load(f)
        except (OSError, ValueError):
            continue
        if _valid(entry) and entry["date"] == m.group(1):
            out.append({"date": entry["date"], "projects": entry["projects"]})
    return out


def sample(path, today=None):
    """Historia przykładowa z pliku z datami względnymi (-56 … 0).

    Z today daty są zamieniane na RRRR-MM-DD; bez today zostają względne ("-56", "+0"),
    tak jak inne daty w podglądzie (/podglad, --export), które przelicza strona.
    """
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, ValueError):
        return []
    entries = raw.get("history", []) if isinstance(raw, dict) else []
    out = []
    for e in entries:
        if not _valid(e) or not REL.match(e["date"]):
            continue
        n = int(e["date"])
        date = (today + datetime.timedelta(days=n)).isoformat() if today else "%+d" % n
        out.append((n, {"date": date, "projects": e["projects"]}))
    return [e for _, e in sorted(out, key=lambda x: x[0])]
