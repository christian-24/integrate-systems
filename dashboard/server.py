#!/usr/bin/env python3
"""Panel projektów: raport PM, monitor zadań, agenci, kampanie, kalendarz, standard.

Mały serwer, tylko biblioteka standardowa Pythona:
  GET  /                      strona panelu (panel.html)
  GET  /podglad               ta sama strona z samymi danymi przykładowymi
  GET  /wejscie               strona hasła dla połączeń spoza tego komputera (POST: pole haslo)
  GET  /api/data              projekty, etapy, zadania, kampanie, kalendarz i blok agents
  POST /api/task/update       zmienia pola zadania w ZADANIA.md albo w pliku kampanii
  POST /api/task/state        zmienia sam stan zadania (z "count": wynik licznika do kampanii)
  POST /api/task/count        dopisuje wynik licznika zadania do kampanii projektu („Wyniki i wnioski”)
  POST /api/task/close-checked  zamyka zadanie potwierdzone kontrolą serwera (pole sprawdza:)
  POST /api/task/detail      jeden klucz szczegółów zadania (cel, gotowe gdy, materiał, wynik…, poprawka, następne, krok)
  POST /api/task/add          dopisuje zadanie do etapu, do „Do rozplanowania” albo do harmonogramu kampanii
  POST /api/stage/update      zmienia termin etapu
  POST /api/campaign/update   zmienia wynik i stan kampanii
  POST /api/calendar/connect  prosi macOS o zgodę na odczyt kalendarza
  POST /api/agent/run         uruchamia agenta dla jednego zadania
  POST /api/agent/pm          uruchamia raport PM
  POST /api/agent/check       test połączenia z Claude Code albo Codex
  POST /api/agent/stop        zatrzymuje uruchomienie albo zdejmuje je z kolejki
  POST /api/agent/merge       scala gałąź uruchomienia do bazy (git merge --no-ff, bez push)
  GET  /api/agent/diff        diff gałęzi uruchomienia względem bazy (?id=, najwyżej 200 KB)
  POST /api/agent/automat     włącza i wyłącza Automat
  POST /api/project/add       dopisuje folder do rejestru projektów (opcjonalnie zakłada pliki standardu)
  POST /api/project/remove    usuwa projekt z rejestru; pliki zostają
  POST /api/project/meta      zmienia pola karty projektu: faza, klient, próg (KARTA.md)
  POST /api/session/logout-all  unieważnia wszystkie sesje (nowy klucz sesji w ../uruchomienia/stan.json)
  GET  /api/plik              tekst pliku .md/.txt z folderu projektu albo jego karty (?project=&path=&anchor=)
  GET  /terminy.ics           terminy etapów i publikacje jako kalendarz do subskrypcji (?k=klucz spoza komputera)

Projekty pochodzą z rejestru ../projekty.json (python3 ../standard/projekt.py dodaj <folder>)
i z decyzji zbieracza na tym komputerze (system/zbieracz.py). Gdy obu brak, panel pokazuje projekty
przykładowe z folderu przyklad/. Dzienny stan zadań zapisuje historia.py (../historia/).
Uruchamianie agentów, ustawienia (panel.env) i dostęp z innych urządzeń opisuje AGENCI.md.

Uruchomienie:  python3 server.py
Podgląd bez serwera (dane przykładowe):  python3 server.py --export podglad.html
"""
import collections
import contextlib
import datetime
import glob
import errno
import hashlib
import hmac
import io
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from http.cookies import CookieError, SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
for _stream in ("stdout", "stderr"):            # pythonw na Windows: brak konsoli, strumienie to None
    if getattr(sys, _stream) is None:
        setattr(sys, _stream, open(os.devnull, "w", encoding="utf-8"))
    elif hasattr(getattr(sys, _stream), "reconfigure"):
        try:                                     # konsola bez polskich znaków nie może przerwać komunikatu
            getattr(sys, _stream).reconfigure(errors="replace")
        except (OSError, ValueError):
            pass


def load_env_file(path):
    """panel.env: wiersze NAZWA=wartość, # to komentarz. Zmienna środowiska wygrywa z plikiem; pusty wpis to brak wartości."""
    try:
        with open(path, encoding="utf-8-sig") as f:
            lines = f.read().splitlines()
    except OSError:
        return
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name, value = name.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if value and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name) and not os.environ.get(name):
            os.environ[name] = value


load_env_file(os.path.join(HERE, "panel.env"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "standard"))
sys.path.insert(0, HERE)
import projekt  # noqa: E402  (standard projektu: odczyt, kontrola zgodności, zapis stanu zadań)
import historia  # noqa: E402  (dzienny stan zadań projektów, PULPIT.md sekcja 3)
import agents  # noqa: E402  (uruchamianie Claude Code i Codex, kontrakt w AGENCI.md)
import koszty  # noqa: E402  (koszty Hetznera z API Hetzner Cloud)
import publikacja  # noqa: E402  (publikacja postów: Facebook, LinkedIn)
COSTS = koszty.Costs()
HOST = os.environ.get("PANEL_HOST", "").strip() or "127.0.0.1"
PORT = int(os.environ.get("PANEL_PORT", "").strip() or "4801")
# Dodatkowe nazwy hosta, pod którymi panel może być otwierany (np. adres Tailscale).
EXTRA_HOSTS = [h.strip() for h in os.environ.get("PANEL_ALLOWED_HOSTS", "").split(",") if h.strip()]
# Hasło panelu dla połączeń spoza tego komputera. Bez hasła takie połączenia są odrzucane.
TOKEN = os.environ.get("PANEL_TOKEN", "").strip()
# Klucz zapisu dla żądań z tego komputera bez sesji (nagłówek X-Panel-Klucz). Plik czytelny tylko dla użytkownika
# panelu i root; agent (PANEL_AGENT_USER) nie może go przeczytać.
LOCAL_KEY_FILE = os.path.expanduser(os.environ.get("PANEL_LOKALNY_KLUCZ_PLIK", "").strip())
LOCAL_KEY_HEADER = "X-Panel-Klucz"
DAY_MINUTES_DEFAULT = 120
# Inne położenie rejestru projektów (testy, osobny zestaw projektów). Domyślnie ../projekty.json.
if os.environ.get("PANEL_REGISTRY", "").strip():
    projekt.REGISTRY = os.path.abspath(os.path.expanduser(os.environ["PANEL_REGISTRY"].strip()))

PAGE = os.path.join(HERE, "panel.html")
SAMPLES = os.path.join(HERE, "przyklad")
SAMPLE_CAL = os.path.join(HERE, "kalendarz-przyklad.json")
SAMPLE_AGENTS = os.path.join(HERE, "agenci-przyklad.json")
SAMPLE_NOTE = os.path.join(SAMPLES, "raport.md")
SAMPLE_HISTORY = os.path.join(HERE, "historia-przyklad.json")
NOTES = os.path.join(os.path.dirname(HERE), "raporty")
APP = os.path.join(HERE, "build", "PanelKalendarz.app")
CACHE = os.path.join(HERE, "build", "kalendarz.json")
DAYS_BACK, DAYS_AHEAD = 7, 45
CAL_TTL = 60  # sekundy między odczytami kalendarza

REL = re.compile(r"^([+-]\d+)(T\d\d:\d\d)?$")


def resolve_date(value, today=None):
    """'+3' -> '2026-11-12', '+0T09:30' -> '2026-11-09T09:30'. Daty bezwzględne bez zmian."""
    m = REL.match(value) if isinstance(value, str) else None
    if not m:
        return value
    day = (today or datetime.date.today()) + datetime.timedelta(days=int(m.group(1)))
    return day.isoformat() + (m.group(2) or "")


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def sample_folders():
    return sorted(p for p in glob.glob(os.path.join(SAMPLES, "*")) if os.path.isdir(p))


def project_folders():
    """Foldery projektów: rejestr i zbieracz [(folder, źródło, decyzja)], a gdy oba puste, projekty przykładowe."""
    folders = projekt.all_folders()
    if folders:
        return "registry", folders
    return "sample", [(p, "sample", None) for p in sample_folders()]


def short_path(path):
    home = os.path.expanduser("~")
    if path.startswith(HERE + os.sep):
        return os.path.relpath(path, os.path.dirname(HERE))
    return "~" + path[len(home):] if path.startswith(home + os.sep) else path


def load_projects(resolve=True):
    """Czyta wszystkie projekty w standardzie. Zwraca (dane dla strony, {id projektu: folder})."""
    source, folders = project_folders()
    out = {"projects": [], "stages": [], "tasks": [], "campaigns": [], "projectsSource": source}
    index = {}
    for folder, origin, decision in folders:
        base = pid = projekt.slug(os.path.basename(folder))
        n = 2
        while pid in index:
            pid, n = "%s-%d" % (base, n), n + 1
        index[pid] = folder
        d = projekt.read_project(folder, pid, decision)
        d["project"]["origin"] = origin
        out["projects"].append(d["project"])
        for k in ("stages", "tasks", "campaigns"):
            out[k] += d[k]
    if resolve:
        for item in out["stages"] + out["tasks"]:
            item["date"] = resolve_date(item["date"])
        for t in out["tasks"]:
            for u in t.get("unlocks") or []:
                if isinstance(u, dict):
                    u["date"] = resolve_date(u.get("date", ""))
        for c in out["campaigns"]:
            c["start"], c["end"] = resolve_date(c["start"]), resolve_date(c["end"])
        for p in out["projects"]:
            if p["lastDecision"]:
                p["lastDecision"]["date"] = resolve_date(p["lastDecision"]["date"])
            if p.get("nextStep"):
                p["nextStep"]["date"] = resolve_date(p["nextStep"]["date"])
            for q in p.get("questions") or []:
                q["date"] = resolve_date(q.get("date", ""))
    return out, index


_write_lock = threading.Lock()


def change_task(body):
    """{"id", "title", "state", "count"?}: zadanie odszukujemy po stronie serwera, nigdy po ścieżce od klienta.
    "count" (tylko ze stanem done): liczba dla pola licznik: zadania, dopisana do kampanii (count_task)."""
    if "count" in body and body.get("count") is not None:
        if body.get("state") != "done":
            return 400, "Nie zapisano: licznik tylko przy stanie zrobione."
        return count_task(body, state="done")
    parts = str(body.get("id", "")).split("|")
    if len(parts) != 3 or not parts[2].isdigit():
        return 400, "Nieznane zadanie."
    _, index = load_projects(resolve=False)
    folder = index.get(parts[0])
    if not folder:
        return 404, "Nie ma takiego projektu."
    try:
        with _write_lock:
            ok = projekt.set_state(folder, parts[1], int(parts[2]), str(body.get("title", "")), str(body.get("state", "")))
    except (ValueError, OSError):
        return 400, "Nie udało się zapisać zmiany."
    return (200, "") if ok else (409, "Plik zmienił się od ostatniego odczytu. Odświeżam listę.")


COUNT_MAX = 1000000


def _find_task(task_id, title):
    """(zadanie, dane, folder) z bieżącego odczytu albo (None, None, (kod, komunikat)). Tytuł musi się zgadzać."""
    where, error = _locate(task_id)
    if error:
        return None, None, error
    data, _ = load_projects(resolve=False)
    t = next((x for x in data["tasks"] if x["id"] == str(task_id)), None)
    if not t or t["title"] != str(title or ""):
        return None, None, CONFLICT
    return t, data, where[0]


def task_counter(task):
    """Nazwa licznika zadania (pole licznik:) albo ""."""
    value = task.get("counter")
    if isinstance(value, dict):
        value = value.get("name")
    return str(value or "").strip()


def counter_campaign(task, campaigns):
    """Kampania, do której trafia wynik licznika: wskazana polem kampania: zadania, kampania, w której stoi
    publikacja, a bez tego pierwsza kampania projektu w toku. None, gdy żadna nie pasuje."""
    own = [c for c in campaigns if c["project"] == task["project"]]
    want = str(task.get("campaignFile") or "").strip().replace("\\", "/")
    if want:
        names = {want, want if want.startswith("kampanie/") else "kampanie/" + want}
        names |= {n + ".md" for n in list(names) if not n.endswith(".md")}
        return next((c for c in own if c["file"] in names or c["id"] == want), None)
    if task.get("file", "").startswith("kampanie/"):
        hit = next((c for c in own if c["file"] == task["file"]), None)
        if hit:
            return hit
    return next((c for c in own if c.get("state") == "active"), None)


def count_task(body, state=None):
    """POST /api/task/count {id, title, count} (i /api/task/state z count): wiersz
    „- RRRR-MM-DD · <licznik> <n> · <tytuł>” w sekcji „Wyniki i wnioski” kampanii projektu
    (projekt.append_campaign_count). state="done" najpierw zamyka zadanie; gdy dopisanie się nie uda, stan wraca."""
    n = body.get("count")
    if isinstance(n, bool) or not isinstance(n, int) or not 0 <= n <= COUNT_MAX:
        return 400, "Nie zapisano: licznik to liczba całkowita od 0 do %d." % COUNT_MAX
    title = str(body.get("title", ""))
    t, data, folder = _find_task(body.get("id", ""), title)
    if t is None:
        return folder
    name = task_counter(t)
    if not name:
        return 400, "Nie zapisano: zadanie nie ma pola licznik."
    camp = counter_campaign(t, data["campaigns"])
    if not camp:
        return 409, "Nie zapisano: projekt nie ma kampanii w toku (albo kampanii z pola kampania:)."
    day = datetime.date.today().isoformat()
    try:
        with _write_lock:
            if state and t["state"] != state:
                if not projekt.set_state(folder, t["file"], t["line"], title, state):
                    return CONFLICT
            try:
                ok = projekt.append_campaign_count(folder, camp["file"], name, n, title, day)
            except (ValueError, OSError):
                if state and t["state"] != state:
                    projekt.set_state(folder, t["file"], t["line"], title, t["state"])
                raise
            if ok is False and state and t["state"] != state:
                projekt.set_state(folder, t["file"], t["line"], title, t["state"])
    except ValueError as e:
        return 400, "Nie zapisano: %s." % e
    except OSError:
        return 400, "Nie udało się zapisać zmiany."
    if ok is False:
        return CONFLICT
    return 200, "", {"campaign": camp["id"], "counter": name, "count": n}


def _locate(task_id):
    """Identyfikator zadania -> (folder, plik, wiersz) albo (kod, komunikat)."""
    parts = str(task_id).split("|")
    if len(parts) != 3 or not parts[2].isdigit():
        return None, (400, "Nieznane zadanie.")
    _, index = load_projects(resolve=False)
    folder = index.get(parts[0])
    if not folder:
        return None, (404, "Nie ma takiego projektu.")
    return (folder, parts[1], int(parts[2])), None


CONFLICT = (409, "Plik zmienił się od ostatniego odczytu. Odświeżam listę.")


def update_task(body):
    """{"id", "title", "changes": {...}}: zmienia pola jednego wiersza."""
    where, error = _locate(body.get("id", ""))
    if error:
        return error
    try:
        with _write_lock:
            ok = projekt.update_task(where[0], where[1], where[2], str(body.get("title", "")), body.get("changes"))
    except ValueError as e:
        return 400, "Nie zapisano: %s." % e
    except OSError:
        return 400, "Nie udało się zapisać zmiany."
    return (200, "") if ok else CONFLICT


DETAIL_KEYS = ("cel", "gotowe gdy", "materiał", "wynik", "decyzja", "zostało", "poprawka", "następne", "krok",
               "wyświetlenia", "kliknięcia", "konta", "link", "gałąź", "pyta", "odpowiedź")
DETAIL_ALIASES = {"nastepne": "następne", "wyswietlenia": "wyświetlenia", "klikniecia": "kliknięcia",
                  "material": "materiał", "zostalo": "zostało", "galaz": "gałąź", "odpowiedz": "odpowiedź"}


def update_detail(body):
    """{"id", "title", "key", "value"}: jeden klucz szczegółów pod wierszem zadania (projekt.set_detail).
    "krok": value {"index": n, "done": bool}; "następne": „Tytuł | kto: … | kiedy: …”."""
    where, error = _locate(body.get("id", ""))
    if error:
        return error
    key = str(body.get("key", "")).strip().lower()
    key = DETAIL_ALIASES.get(key, key)
    if key not in DETAIL_KEYS:
        return 400, "Nie zapisano: klucz %s." % ", ".join(DETAIL_KEYS)
    try:
        with _write_lock:
            ok = projekt.set_detail(where[0], where[1], where[2], str(body.get("title", "")), key, body.get("value", ""))
    except ValueError as e:
        return 400, "Nie zapisano: %s." % e
    except OSError:
        return 400, "Nie udało się zapisać zmiany."
    return (200, "") if ok else CONFLICT


# ---------- kontrola serwera przy zadaniu (pole sprawdza:) ----------
def task_check(task, srv, folder):
    """"check" zadania: {"key", "ok", "at"} z projekt.check_task (stan serwera albo plik w folderze projektu
    lub karty) albo None, gdy zadanie nie ma pola sprawdza:."""
    if not task.get("check"):
        return None
    try:
        out = projekt.check_task(task, srv, folder or None)
    except (OSError, ValueError, TypeError) as e:
        agents.log("sprawdza: %s (%s)" % (task.get("title", ""), e))
        return None
    return dict(out, at=out.get("at") or "") if isinstance(out, dict) else None


def add_checks(tasks, index, srv):
    """"check" każdego zadania z polem sprawdza: (stan serwera z server_state, pliki w folderze projektu)."""
    for t in tasks:
        t["check"] = task_check(t, srv, index.get(t["project"], ""))


def check_stamp(at):
    """Czas kontroli „RRRR-MM-DD HH:MM” z ISO; bez czasu: teraz."""
    dt = _iso(at) if at else None
    return (dt or datetime.datetime.now()).strftime("%Y-%m-%d %H:%M")


def close_checked(body):
    """POST /api/task/close-checked {id, title}: otwarte zadanie, które kontrola serwera potwierdza (check.ok),
    dostaje stan zrobione i notatkę „zamknięte na podstawie kontroli serwera z RRRR-MM-DD HH:MM”."""
    title = str(body.get("title", ""))
    t, _, folder = _find_task(body.get("id", ""), title)
    if t is None:
        return folder
    if t["state"] == "done":
        return 409, "Zadanie jest już zrobione."
    check = task_check(t, server_state(), folder)
    if not check or check.get("ok") is not True:
        return 409, "Kontrola serwera nie potwierdza tego zadania."
    stamp = check_stamp(check.get("at"))
    try:
        with _write_lock:
            if not projekt.set_state(folder, t["file"], t["line"], title, "done"):
                return CONFLICT
            projekt._add_note(projekt._task_file(folder, t["file"]), t["line"], title,
                              "zamknięte na podstawie kontroli serwera z %s" % stamp)
    except (ValueError, OSError):
        return 400, "Nie udało się zapisać zmiany."
    return 200, "", {"check": check, "at": stamp}


# ---------- odczyt materiałów zadania (GET /api/plik) ----------
FILE_MAX = 200 * 1024
FILE_TYPES = (".md", ".txt")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")


def _inside(base, path):
    try:
        return os.path.commonpath([base, path]) == base
    except ValueError:
        return False


def project_file(pid, rel):
    """Ścieżka pliku materiału albo (None, komunikat). Tylko .md i .txt wewnątrz folderu projektu albo folderu
    jego karty (KARTA.md może być dowiązaniem do szkice/); porównanie po realpath."""
    rel = str(rel or "").strip().replace("\\", "/")
    if not rel or "\x00" in rel or os.path.isabs(rel) or rel.startswith("~"):
        return None, "Nie ma takiego pliku."
    _, index = load_projects(resolve=False)
    folder = index.get(pid)
    if not folder:
        return None, "Nie ma takiego projektu."
    root = os.path.realpath(folder)
    bases = [root]
    card = os.path.dirname(os.path.realpath(os.path.join(folder, "KARTA.md")))
    if card not in bases:
        bases.append(card)
    for base in bases:
        path = os.path.realpath(os.path.join(base, rel))
        if not any(_inside(b, path) for b in bases):
            continue
        if os.path.isfile(path):
            if not path.lower().endswith(FILE_TYPES):
                return None, "Panel pokazuje tylko pliki .md i .txt."
            if os.path.getsize(path) > FILE_MAX:
                return None, "Plik jest większy niż 200 KB."
            return path, ""
    return None, "Nie ma takiego pliku."


def file_section(text, anchor):
    """(tytuł, tekst) sekcji: nagłówek ## z numerem („5.”) albo z tekstem; najpierw poziom ##, potem każdy inny.
    None, gdy takiej sekcji nie ma."""
    want = str(anchor).strip().lstrip("#").strip()
    num = re.match(r"^(\d+(?:\.\d+)*)\.?$", want)
    lines, fence, heads = text.split("\n"), False, []
    for i, line in enumerate(lines):
        if line.lstrip().startswith("```"):
            fence = not fence
            continue
        m = None if fence else HEADING.match(line.rstrip("\r"))
        if m:
            heads.append((i, len(m.group(1)), m.group(2)))

    def match(title):
        if num:
            return re.match(r"^%s(?:\.(?!\d)|\)|\s|$)" % re.escape(num.group(1)), title) is not None
        return title.lower() == want.lower() or projekt.slug(title) == projekt.slug(want)

    for level in (2, None):
        for n, (i, depth, title) in enumerate(heads):
            if (level is None or depth == level) and match(title):
                end = next((j for j, d, _ in heads[n + 1:] if d <= depth), len(lines))
                return title, "\n".join(lines[i:end]).strip()
    return None


def read_project_file(query):
    """GET /api/plik: (kod, odpowiedź)."""
    q = parse_qs(query)
    pid, rel, anchor = ((q.get(k) or [""])[0] for k in ("project", "path", "anchor"))
    path, error = project_file(pid, rel)
    if not path:
        return 404, {"ok": False, "error": error}
    text = projekt.read(path)
    if text is None:
        return 404, {"ok": False, "error": "Nie udało się odczytać pliku."}
    h1 = next((m.group(2) for m in map(HEADING.match, text.split("\n")) if m and len(m.group(1)) == 1), "")
    title = h1 or os.path.basename(path)
    if anchor.strip():
        found = file_section(text, anchor)
        if not found:
            return 404, {"ok": False, "error": "Nie ma takiej sekcji w pliku."}
        title, text = found
    return 200, {"ok": True, "path": rel.strip().replace("\\", "/"), "title": title, "text": text}


def add_task(body):
    """{"project", "title", "stage"?, "campaign"?}: nowe zadanie w etapie, w kampanii albo w „Do rozplanowania”."""
    data, index = load_projects(resolve=False)
    pid = str(body.get("project", ""))
    folder = index.get(pid)
    if not folder:
        return 404, "Nie ma takiego projektu."
    file_rel, line = "ZADANIA.md", None
    if body.get("campaign"):
        camp = next((c for c in data["campaigns"] if c["id"] == body["campaign"] and c["project"] == pid), None)
        if not camp:
            return 404, "Nie ma takiej kampanii."
        file_rel = camp["file"]
    elif body.get("stage"):
        stage = next((x for x in data["stages"] if x["id"] == body["stage"] and x["project"] == pid), None)
        if not stage:
            return 404, "Nie ma takiego etapu."
        line = stage["line"]
    try:
        with _write_lock:
            projekt.add_task(folder, body.get("title", ""), file_rel, line)
    except ValueError:
        return 400, "Podaj tytuł zadania."
    except OSError:
        return 400, "Projekt nie ma pliku ZADANIA.md. Załóż go: python3 standard/projekt.py nowy <folder>"
    return 200, ""


def update_stage(body):
    """{"id", "title", "date"}: nowy termin etapu."""
    data, index = load_projects(resolve=False)
    stage = next((x for x in data["stages"] if x["id"] == body.get("id")), None)
    if not stage:
        return 404, "Nie ma takiego etapu."
    try:
        with _write_lock:
            ok = projekt.set_stage_date(index[stage["project"]], stage["line"], str(body.get("title", "")),
                                        body.get("date", ""))
    except ValueError:
        return 400, "Podaj termin jako datę."
    except OSError:
        return 400, "Nie udało się zapisać zmiany."
    return (200, "") if ok else CONFLICT


def update_campaign(body):
    """{"id", "name", "changes": {"result", "state"}}."""
    data, index = load_projects(resolve=False)
    camp = next((c for c in data["campaigns"] if c["id"] == body.get("id")), None)
    if not camp:
        return 404, "Nie ma takiej kampanii."
    try:
        with _write_lock:
            ok = projekt.set_campaign(index[camp["project"]], camp["file"], str(body.get("name", "")),
                                      body.get("changes"))
    except ValueError as e:
        return 400, "Nie zapisano: %s." % e
    except OSError:
        return 400, "Nie udało się zapisać zmiany."
    return (200, "") if ok else CONFLICT


def add_project(body):
    """{"path", "name"?, "files": bool}: dopisuje istniejący folder do rejestru; files zakłada brakujące pliki standardu."""
    raw, name, files = body.get("path"), body.get("name"), body.get("files", False)
    if not isinstance(raw, str) or not raw.strip():
        return 400, "Podaj ścieżkę folderu."
    if not isinstance(files, bool):
        return 400, "Podaj files: true albo false."
    if name is not None and not isinstance(name, str):
        return 400, "Nazwa musi być tekstem."
    raw = raw.strip()
    if not (raw.startswith("~") or os.path.isabs(raw)):
        return 400, "Podaj pełną ścieżkę folderu albo ścieżkę od ~."
    folder = os.path.abspath(os.path.expanduser(raw))
    if not os.path.isdir(folder):
        return 404, "Nie ma takiego folderu."
    real = os.path.realpath(folder)
    samples = os.path.realpath(SAMPLES)
    if real == samples or real.startswith(samples + os.sep):
        return 400, "Projekty przykładowe służą tylko do podglądu."
    if real in (os.path.realpath(os.path.expanduser("~")), os.path.dirname(real)):
        return 400, "Wskaż folder projektu, nie folder domowy ani cały dysk."
    try:
        with _write_lock, contextlib.redirect_stdout(io.StringIO()):
            if folder in projekt.registry():
                return 409, "Ten folder jest już w panelu."
            if files:
                projekt.cmd_nowy(folder, (name or "").strip() or None, register=True)
            elif projekt.cmd_dodaj(folder) != 0:
                return 404, "Nie ma takiego folderu."
    except (OSError, ValueError):
        return 400, "Nie udało się dodać projektu."
    return 200, ""


def remove_project(body):
    """{"id"}: usuwa projekt z rejestru. Pliki projektu zostają."""
    data, index = load_projects(resolve=False)
    pid = body.get("id")
    if data["projectsSource"] != "registry" or not isinstance(pid, str) or pid not in index:
        return 404, "Nie ma takiego projektu."
    if os.path.abspath(index[pid]) not in projekt.registry():
        return 409, "Projekt pochodzi z decyzji zbieracza. Zmień jego stan w zbieraczu (kwalifikuj)."
    if get_agents().has_live(pid):
        return 409, "Projekt ma uruchomienie w toku. Najpierw je zatrzymaj."
    try:
        with _write_lock, contextlib.redirect_stdout(io.StringIO()):
            projekt.cmd_usun(index[pid])
    except OSError:
        return 400, "Nie udało się zapisać zmiany."
    return 200, ""


def update_meta(body):
    """{"id", "phase"?, "client"?, "threshold"?}: pola pod tytułem KARTA.md projektu z rejestru albo ze zbieracza."""
    data, index = load_projects(resolve=False)
    pid = body.get("id")
    if data["projectsSource"] != "registry" or not isinstance(pid, str) or pid not in index:
        return 404, "Nie ma takiego projektu."
    changes = {k: body[k] for k in ("phase", "client", "threshold") if k in body}
    if not changes:
        return 400, "Nie zapisano: brak zmian."
    try:
        with _write_lock:
            projekt.set_card_fields(index[pid], changes)
    except ValueError as e:
        return 400, "Nie zapisano: %s." % e
    except OSError:
        return 400, "Projekt nie ma pliku KARTA.md. Załóż go: python3 standard/projekt.py nowy <folder>"
    return 200, ""


def _words(text):
    return " ".join(str(text or "").split())


APPLY_TITLE = "Zastosuj odpowiedź na pytanie %d"
APPLY_REF = "KARTA.md#Pytania do właściciela"


def apply_answer_task(folder, pid, n, today):
    """Zadanie agenta „Zastosuj odpowiedź na pytanie N” w „Do rozplanowania” (kto: claude, kiedy: dziś,
    materiał: sekcja pytań karty); gdy otwarte zadanie o tym tytule już jest, nowego nie zakłada.
    Wywołujący trzyma _write_lock. Zwraca tytuł zadania."""
    title = APPLY_TITLE % n

    def rows():
        return [t for t in projekt.read_project(folder, pid)["tasks"]
                if t["file"] == "ZADANIA.md" and t["title"] == title]

    if any(t["state"] != "done" for t in rows()):
        return title
    projekt.add_task(folder, title)
    t = rows()[-1]
    projekt.update_task(folder, t["file"], t["line"], title, {"executor": "claude", "date": today})
    projekt.set_detail(folder, t["file"], t["line"], title, "cel",
                       "zmiany w ZADANIA.md według odpowiedzi właściciela na pytanie %d w KARTA.md" % n)
    projekt.set_detail(folder, t["file"], t["line"], title, "materiał", APPLY_REF)
    return title


def answer_question(body):
    """{"id", "n", "answer"} albo {"id", "n", "accept": true}: odpowiedź na pytanie z sekcji „Pytania do właściciela”
    w KARTA.md. Przyjęcie propozycji (accept, albo pierwsza odpowiedź równa propozycji) zapisuje odpowiedź = propozycja
    i wykonuje skutki pytania (skutek:) na ZADANIA.md (projekt.apply_effects). Inna odpowiedź na pytanie ze skutkami
    zakłada zadanie agenta „Zastosuj odpowiedź na pytanie N”. Odpowiedź: "applied", "failed", "task"."""
    data, index = load_projects(resolve=False)
    pid = body.get("id")
    if data["projectsSource"] != "registry" or not isinstance(pid, str) or pid not in index:
        return 404, "Nie ma takiego projektu."
    folder = index[pid]
    project = next(p for p in data["projects"] if p["id"] == pid)
    n = body.get("n")
    qs = project.get("questions") or []
    q = qs[n - 1] if isinstance(n, int) and not isinstance(n, bool) and 1 <= n <= len(qs) else None
    accept = body.get("accept") is True
    if "accept" in body and not isinstance(body.get("accept"), bool):
        return 400, "Nie zapisano: accept to true albo false."
    if accept:
        if not q:
            return 400, "Nie zapisano: nie ma takiego pytania."
        if not _words(q.get("proposal")):
            return 400, "Nie zapisano: pytanie nie ma propozycji."
        if _words(q.get("answer")):
            return 409, "Pytanie ma już odpowiedź."
        answer = _words(q["proposal"])
    else:
        answer = body.get("answer", "")
    effects = [e for e in (q or {}).get("effects") or [] if str(e).strip()]
    words, before = _words(answer) if isinstance(answer, str) else "", _words((q or {}).get("answer"))
    applied, failed, task = [], [], ""
    today = datetime.date.today().isoformat()
    try:
        with _write_lock:
            projekt.set_answer(folder, n, answer)
            if q and effects and words and words != before:
                if accept or (not before and words == _words(q.get("proposal"))):
                    try:
                        applied, failed = projekt.apply_effects(folder, effects, n, today)
                    except (ValueError, OSError) as e:
                        failed = ["%s (%s)" % (e, "skutki pytania %d" % n)]
                else:
                    try:
                        task = apply_answer_task(folder, pid, n, today)
                    except (ValueError, OSError, StopIteration, IndexError) as e:
                        failed = ["nie powstało zadanie „%s” (%s)" % (APPLY_TITLE % n, e or "brak ZADANIA.md")]
    except ValueError as e:
        return 400, "Nie zapisano: %s." % e
    except OSError:
        return 400, "Projekt nie ma pliku KARTA.md."
    if not (accept or effects):
        return 200, ""
    return 200, "", {"applied": list(applied), "failed": list(failed), "task": task}


# ---------- agenci (agents.py) ----------
_agents = None
_agents_lock = threading.Lock()


_publisher = None


def get_publisher():
    """Publikacja postów (publikacja.py); jedna na proces."""
    global _publisher
    with _agents_lock:
        if _publisher is None:
            _publisher = publikacja.Publisher(load_projects, _write_lock, projekt, post_folder, post_info, post_image,
                                              notify=lambda text: get_agents()._send_ntfy(text))
        return _publisher


def get_agents():
    """Jeden zarządca uruchomień na proces; powstaje przy pierwszym użyciu (eksport podglądu go nie potrzebuje)."""
    global _agents
    with _agents_lock:
        if _agents is None:
            _agents = agents.Manager(load_projects, _write_lock, projekt)
        return _agents


WRITES = {"/api/task/state": lambda b: change_task(b), "/api/task/update": lambda b: update_task(b),
          "/api/task/count": lambda b: count_task(b),
          "/api/task/close-checked": lambda b: close_checked(b),
          "/api/task/detail": lambda b: update_detail(b),
          "/api/task/add": lambda b: add_task(b), "/api/stage/update": lambda b: update_stage(b),
          "/api/campaign/update": lambda b: update_campaign(b),
          "/api/project/add": lambda b: add_project(b), "/api/project/remove": lambda b: remove_project(b),
          "/api/project/meta": lambda b: update_meta(b),
          "/api/agent/run": lambda b: get_agents().run_task(b.get("id", ""), b.get("title", "")),
          "/api/agent/pm": lambda b: get_agents().run_pm(),
          "/api/agent/check": lambda b: get_agents().run_check(b.get("tool", "claude")),
          "/api/agent/stop": lambda b: get_agents().stop(b.get("id", "")),
          "/api/publikacja/facebook": lambda b: get_publisher().connect_facebook(b),
          "/api/publikacja/linkedin": lambda b: get_publisher().connect_linkedin(b),
          "/api/publikacja/strona": lambda b: get_publisher().map_page(b),
          "/api/publikacja/odlacz": lambda b: get_publisher().disconnect(b),
          "/api/publikacja/plan": lambda b: get_publisher().plan(b),
          "/api/publikacja/anuluj": lambda b: get_publisher().cancel(b),
          "/api/agent/merge": lambda b: get_agents().merge(b.get("id", ""), b.get("project", ""), b.get("branch", "")),
          "/api/agent/automat": lambda b: get_agents().set_automat(b.get("enabled")),
          "/api/agent/login": lambda b: get_agents().open_login(b.get("tool", "claude")),
          "/api/agent/recheck": lambda b: get_agents().recheck_login(),
          "/api/agent/login-code": lambda b: get_agents().submit_login_code(b.get("code", "")),
          "/api/question/answer": lambda b: answer_question(b),
          "/api/session/logout-all": lambda b: logout_all(b),
          "/api/plan/ask": lambda b: get_agents().run_plan(b.get("text", "")),
          "/api/plan/accept": lambda b: get_agents().accept_plan(b.get("id", ""), b.get("ids"))}


def pm_note(sample):
    """Najnowsza notatka PM z ../raporty/RRRR-MM-DD.md; przy danych przykładowych notatka przykładowa."""
    if not sample:
        files = sorted(f for f in glob.glob(os.path.join(NOTES, "*.md"))
                       if re.match(r"^\d{4}-\d\d-\d\d\.md$", os.path.basename(f)))
        if files:
            text = projekt.read(files[-1])
            if text and text.strip():
                return {"date": os.path.basename(files[-1])[:10], "text": text.strip()[:4000]}
    else:
        text = projekt.read(SAMPLE_NOTE)
        if text and text.strip():
            return {"date": "+0", "text": text.strip()[:4000]}
    return None


def sample_calendar():
    d = load_json(SAMPLE_CAL, {"calendars": [], "events": []})
    cals = {c["id"]: c for c in d.get("calendars", [])}
    events = []
    for i, e in enumerate(d.get("events", [])):
        c = cals.get(e.get("calendarId"), {})
        events.append({**e, "id": "przyklad-%d" % i, "allDay": bool(e.get("allDay")),
                       "start": resolve_date(e["start"]), "end": resolve_date(e["end"]),
                       "calendar": c.get("title", ""), "color": c.get("color", "#888888")})
    return {"calendars": d.get("calendars", []), "events": events}


# ---------- kalendarz macOS (EventKit przez pomocnik w build/PanelKalendarz.app) ----------
_cal_lock = threading.Lock()
_cal = {"at": 0.0, "data": {"status": "not_checked"}, "connecting": False}


def _run_helper(prompt):
    """Uruchamia pomocnik przez 'open', bo tylko tak macOS przypisuje zgodę do tej aplikacji."""
    if sys.platform != "darwin":
        return {"status": "unsupported", "error": "Odczyt przez EventKit działa tylko na macOS."}
    if not os.path.isdir(APP):
        return {"status": "no_helper", "error": "Brak pomocnika. Uruchom ./zbuduj-kalendarz.sh"}
    try:
        os.remove(CACHE)
    except OSError:
        pass
    args = ["open", "-W", "-n", "-g", APP, "--args", "--out", CACHE,
            "--back", str(DAYS_BACK), "--ahead", str(DAYS_AHEAD)]
    if not prompt:
        args.append("--no-prompt")
    try:
        subprocess.run(args, timeout=150 if prompt else 25, check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "error": "Pomocnik kalendarza nie odpowiedział."}
    data = load_json(CACHE, None)
    if data is None:
        return {"status": "error", "error": "Pomocnik nie zwrócił danych."}
    data["readAt"] = datetime.datetime.now().isoformat(timespec="seconds")
    return data


def read_calendar():
    """Zwraca ostatni odczyt, odświeżany najwyżej raz na CAL_TTL sekund. Nigdy nie pyta o zgodę."""
    if _cal["connecting"] or time.time() - _cal["at"] < CAL_TTL:
        return _cal["data"]
    if _cal_lock.acquire(blocking=False):
        try:
            _cal["data"] = _run_helper(prompt=False)
            _cal["at"] = time.time()
        finally:
            _cal_lock.release()
    return _cal["data"]


def connect_calendar():
    """Prosi macOS o zgodę. Okno systemowe czeka na użytkownika do 2 minut."""
    def work():
        with _cal_lock:
            try:
                _cal["data"] = _run_helper(prompt=True)
                _cal["at"] = time.time()
            finally:
                _cal["connecting"] = False
    if not _cal["connecting"]:
        _cal["connecting"] = True
        threading.Thread(target=work, daemon=True).start()


def build_data():
    out, index = load_projects()
    for p in out["projects"]:
        p["folder"] = short_path(index[p["id"]])
    out["standard"] = projekt.describe()
    out["pmNote"] = pm_note(False) or (pm_note(True) if out["projectsSource"] == "sample" else None)
    if out["pmNote"]:
        out["pmNote"]["date"] = resolve_date(out["pmNote"]["date"])
    cal = read_calendar()
    status = cal.get("status", "error")
    if status == "ok":
        calendar = {"status": "ok", "source": "macos", "readAt": cal.get("readAt"),
                    "calendars": cal.get("calendars", []), "events": cal.get("events", [])}
    elif out["projectsSource"] == "sample":
        calendar = {"status": status, "source": "sample", "error": cal.get("error", ""), **sample_calendar()}
    else:       # prawdziwe projekty: bez wydarzeń przykładowych
        calendar = {"status": status, "source": "none", "error": cal.get("error", ""), "calendars": [], "events": []}
    calendar["connecting"] = _cal["connecting"]
    out["calendar"] = calendar
    out["today"] = datetime.date.today().isoformat()
    out["generatedAt"] = datetime.datetime.now().isoformat(timespec="seconds")
    out["mode"] = "live"
    out["icsPath"] = "/terminy.ics" + ("?k=" + ics_key() if TOKEN else "")
    out["dayMinutes"] = day_minutes()
    today = datetime.date.fromisoformat(out["today"])
    manager = get_agents()
    manager.annotate(out["tasks"], out["projectsSource"], today)
    for t in out["tasks"]:
        t["ownerNeeds"] = projekt.owner_needs(t)
    out.update(projekt.owner_counts(out["projects"], out["stages"], out["tasks"], today))
    out["agents"] = manager.snapshot()
    out["agents"]["canRunTasks"] = out["projectsSource"] == "registry"
    out["history"] = project_history(out)
    out["server"] = server_state()
    out["costs"] = COSTS.state()
    out["panelVersion"] = panel_version()
    out["publish"] = get_publisher().status()
    add_checks(out["tasks"], index, out["server"])
    return out


_VERSION = {"key": None, "value": ""}


def panel_version():
    """Skrót panel.html: otwarta aplikacja porównuje go ze swoim i po wdrożeniu przeładowuje się sama."""
    try:
        st = os.stat(PAGE)
    except OSError:
        return ""
    key = (st.st_mtime_ns, st.st_size)
    if _VERSION["key"] != key:
        with open(PAGE, "rb") as f:
            _VERSION.update(key=key, value=hashlib.sha256(f.read()).hexdigest()[:12])
    return _VERSION["value"]


def day_minutes():
    """PANEL_DZIEN_MIN: dzienna pojemność właściciela w minutach (domyślnie 120)."""
    try:
        value = int(os.environ.get("PANEL_DZIEN_MIN", "").strip())
    except ValueError:
        return DAY_MINUTES_DEFAULT
    return value if value > 0 else DAY_MINUTES_DEFAULT


# ---------- stan serwera: kontrola zdrowia i kopie (uruchom/serwer/zdrowie.sh, kopia.sh) ----------
HEALTH_FILE = "/home/panel/.zdrowie-stan"
BACKUP_FILE = "/home/panel/kopie/ostatnia.json"
BACKUP_OFF_HOURS = 26
HEALTH_VALUES = ("ok", "zle", "brak")


def _iso(value):
    """Tekst ISO (data albo data z czasem) -> datetime bez strefy, w czasie lokalnym; None, gdy to nie data."""
    if not isinstance(value, str) or not re.match(r"^\d{4}-\d\d-\d\d", value):
        return None
    try:
        dt = datetime.datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt.astimezone().replace(tzinfo=None) if dt.tzinfo else dt


def server_state(now=None):
    """Blok "server" w /api/data albo None, gdy nie ma ani pliku zdrowia, ani pliku kopii.

    Zdrowie: wiersze nazwa=ok|zle|brak (PANEL_ZDROWIE_STAN, domyślnie /home/panel/.zdrowie-stan).
    Kopia: JSON (PANEL_KOPIA_STAN, domyślnie /home/panel/kopie/ostatnia.json) z polami "at" (czas kopii)
    i "offsiteAt" (czas wysyłki poza serwer, null bez wysyłki); "at" to czas odczytu zdrowia."""
    now = now or datetime.datetime.now()
    health = os.environ.get("PANEL_ZDROWIE_STAN", "").strip() or HEALTH_FILE
    backup = os.environ.get("PANEL_KOPIA_STAN", "").strip() or BACKUP_FILE
    text = projekt.read(health)
    info = load_json(backup, None) if os.path.isfile(backup) else None
    if text is None and info is None:
        return None
    checks = {}
    for line in (text or "").splitlines():
        name, sep, value = line.strip().partition("=")
        if sep and re.match(r"^[\w.-]{1,40}$", name) and value.strip() in HEALTH_VALUES:
            checks[name] = value.strip()
    info = info if isinstance(info, dict) else {}
    at = _iso(info.get("at"))
    off = _iso(info.get("offsiteAt"))
    if off is None and info.get("offsite") is True:
        off = at
    stamp = health if text is not None else backup
    try:
        read_at = datetime.datetime.fromtimestamp(os.path.getmtime(stamp))
    except OSError:
        read_at = now
    return {"checks": checks, "backupAt": at.isoformat(timespec="seconds") if at else None,
            "backupOff": bool(off and datetime.timedelta(0) <= now - off <= datetime.timedelta(hours=BACKUP_OFF_HOURS)),
            "at": read_at.isoformat(timespec="seconds")}


def project_history(out):
    """Projekty z rejestru: zapis dzisiejszego stanu i 63 dni wstecz; przykładowe: historia przykładowa."""
    today = datetime.date.fromisoformat(out["today"])
    if out["projectsSource"] != "registry":
        return historia.sample(SAMPLE_HISTORY, today)
    try:
        historia.save(historia.snapshot(out["tasks"], [p["id"] for p in out["projects"]], today))
    except OSError as e:
        agents.log("historia: nie zapisano stanu (%s)" % e)
    return historia.load(today)


# ---------- dostęp spoza tego komputera (PANEL_TOKEN) ----------
SESSION_COOKIE = "panel_sesja"
LOGIN_TRIES, LOGIN_WINDOW, LOGIN_DELAY = 10, 60, 1.0
_fails = collections.deque()
_fails_lock = threading.Lock()


def _derive(label):
    return hmac.new(TOKEN.encode("utf-8"), label.encode("utf-8"), hashlib.sha256).hexdigest()


SESSION_DAYS = 30


def _session_sig(stamp):
    """Podpis sesji: HMAC z hasła, losowego klucza sesji (stan panelu) i chwili logowania."""
    return _derive("panel-sesja|%s|%d" % (get_agents().session_key(), stamp))


def session_value(now=None):
    """Wartość ciasteczka „chwila.podpis”: bez hasła; ważna SESSION_DAYS dni albo do „Wyloguj wszędzie”."""
    stamp = int(now if now is not None else time.time())
    return "%d.%s" % (stamp, _session_sig(stamp))


def session_ok(value, now=None):
    stamp, _, sig = str(value or "").partition(".")
    if not stamp.isdigit() or len(stamp) > 12 or not sig:
        return False
    age = (now if now is not None else time.time()) - int(stamp)
    if age > SESSION_DAYS * 86400 or age < -300:
        return False
    return hmac.compare_digest(sig.encode("utf-8"), _session_sig(int(stamp)).encode("ascii"))


def logout_all(body):
    """POST /api/session/logout-all: nowy klucz sesji, wszystkie ciasteczka tracą ważność."""
    return get_agents().reset_sessions()


_key_warned = []


def local_guard():
    """Czy zapis z tego komputera wymaga sesji albo klucza: przy pliku klucza, przy agentach jako osobny użytkownik
    i na serwerze (PANEL_MACHINE=cloud). Na Macu i PC bez tych ustawień jak dotąd (agent i tak działa jako właściciel)."""
    if LOCAL_KEY_FILE or os.environ.get("PANEL_AGENT_USER", "").strip():
        return True
    try:
        return get_agents().machine == "cloud"
    except Exception:
        return True


def key_file_exposed(st, agent_user=""):
    """Czy plik klucza mógłby przeczytać ktoś poza właścicielem pliku, grupą panelu i root: prawa dla innych
    albo prawa dla grupy, do której należy użytkownik agenta (PANEL_AGENT_USER)."""
    if st.st_mode & 0o007:
        return True
    if not st.st_mode & 0o070:
        return False
    if not agent_user:
        return False
    try:
        import grp
        import pwd
        user = pwd.getpwnam(agent_user)
        group = grp.getgrgid(st.st_gid)
    except (ImportError, KeyError):
        return True                     # nie da się sprawdzić grupy: bezpieczniej odrzucić
    return user.pw_gid == st.st_gid or agent_user in group.gr_mem or user.pw_uid == st.st_uid


def local_key_ok(given):
    """Nagłówek X-Panel-Klucz równy zawartości PANEL_LOKALNY_KLUCZ_PLIK. Plik, który mógłby przeczytać agent
    (prawa dla innych albo dla grupy agenta, key_file_exposed), jest odrzucany; klucz krótszy niż 16 znaków też."""
    given = str(given or "").strip()
    if not LOCAL_KEY_FILE or not given:
        return False
    try:
        if os.name != "nt" and key_file_exposed(os.stat(LOCAL_KEY_FILE),
                                                os.environ.get("PANEL_AGENT_USER", "").strip()):
            if not _key_warned:
                _key_warned.append(1)
                agents.log("Plik klucza lokalnego może przeczytać agent albo inni użytkownicy: chmod 640, "
                           "grupa bez użytkownika agenta (%s)" % LOCAL_KEY_FILE)
            return False
        with open(LOCAL_KEY_FILE, encoding="utf-8") as f:
            key = f.read().strip()
    except (OSError, UnicodeDecodeError):
        return False
    return len(key) >= 16 and hmac.compare_digest(given.encode("utf-8"), key.encode("utf-8"))


def ics_key():
    """Klucz subskrypcji kalendarza: inna pochodna hasła niż ciasteczko."""
    return _derive("panel-ics")[:32]


def login_blocked(add=False):
    """Czy wyczerpano limit błędnych prób w ostatniej minucie; add dopisuje błędną próbę."""
    now = time.time()
    with _fails_lock:
        while _fails and now - _fails[0] > LOGIN_WINDOW:
            _fails.popleft()
        if add:
            _fails.append(now)
            return False
        return len(_fails) >= LOGIN_TRIES


LOGIN_PAGE = """<!doctype html><html lang="pl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Panel projektów</title>
@@APP@@
<link href="https://fonts.googleapis.com/css2?family=Alegreya+Sans:wght@400;500;700&display=swap" rel="stylesheet">
<style>
html,body{height:100%%;margin:0}
body{background:#0b1020;color:#e9e4d4;font:16px/1.4 "Alegreya Sans",system-ui,sans-serif;display:flex;align-items:center;justify-content:center}
form{width:min(320px,calc(100vw - 48px));padding:24px;border:1px solid rgba(226,179,71,.35);border-radius:10px;background:rgba(255,255,255,.04)}
h1{margin:0 0 4px;font-size:20px;font-weight:700;color:#e2b347}
p{margin:0 0 16px;color:#a9a48f;font-size:14px}
p.blad{color:#f08a7a;margin:12px 0 0}
input,button{width:100%%;box-sizing:border-box;font:inherit;border-radius:6px;padding:10px 12px}
input{background:#0b1020;color:inherit;border:1px solid rgba(226,179,71,.45)}
input:focus,button:focus{outline:2px solid #e2b347;outline-offset:1px}
button{margin-top:12px;background:#e2b347;color:#0b1020;border:0;font-weight:700;cursor:pointer}
</style></head><body><form method="post" action="/wejscie">
<h1>Panel projektów</h1><p>Hasło panelu</p>
<input type="password" name="haslo" aria-label="Hasło panelu" autocomplete="current-password" autofocus required>
<button type="submit">Wejdź</button>%s</form></body></html>"""


def login_page(error=""):
    return (LOGIN_PAGE % ('<p class="blad" role="alert">%s</p>' % error if error else "")).replace("@@APP@@", APP_HEAD, 1)


# ---------- eksport terminów do kalendarza (ICS) ----------
def ics_escape(text):
    return str(text).replace("\\", "\\\\").replace(";", "\;").replace(",", "\\,").replace("\n", "\\n")


def ics_fold(line):
    raw = line.encode("utf-8")
    if len(raw) <= 75:
        return line
    parts, cur = [], b""
    for ch in line:
        b = ch.encode("utf-8")
        if len(cur) + len(b) > (75 if not parts else 74):
            parts.append(cur.decode("utf-8"))
            cur = b
        else:
            cur += b
    parts.append(cur.decode("utf-8"))
    return "\r\n ".join(parts)


def ics_event(uid, day, summary, desc, alarm, stamp):
    nxt = day + datetime.timedelta(days=1)
    return ["BEGIN:VEVENT", "UID:%s@panel-agentow" % re.sub(r"[^A-Za-z0-9.-]+", "-", uid), "DTSTAMP:" + stamp,
            "DTSTART;VALUE=DATE:" + day.strftime("%Y%m%d"), "DTEND;VALUE=DATE:" + nxt.strftime("%Y%m%d"),
            "SUMMARY:" + ics_escape(summary), "DESCRIPTION:" + ics_escape(desc), "TRANSP:TRANSPARENT",
            "BEGIN:VALARM", "ACTION:DISPLAY", "DESCRIPTION:" + ics_escape(alarm),
            "TRIGGER:-PT15H", "END:VALARM", "END:VEVENT"]


def as_day(value):
    try:
        return datetime.date.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def build_ics():
    d, _ = load_projects()
    names = {p["id"]: p["name"] for p in d["projects"]}
    camps = {c["id"]: c["name"] for c in d["campaigns"]}
    stamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Panel agentow//Terminy POC//PL",
             "CALSCALE:GREGORIAN", "METHOD:PUBLISH", "X-WR-CALNAME:Terminy projektów",
             "REFRESH-INTERVAL;VALUE=DURATION:PT1H", "X-PUBLISHED-TTL:PT1H"]
    for st in d["stages"]:
        tasks = [t for t in d["tasks"] if t["stage"] == st["id"]]
        done = sum(1 for t in tasks if t["state"] == "done")
        day = as_day(st["date"])
        if not day or st["closed"] or (tasks and done == len(tasks)):
            continue
        name = names.get(st["project"], st["project"])
        lines += ics_event(st["id"], day, "Termin: %s (%s)" % (st["title"], name),
                           "Projekt: %s. Zadania: %d z %d." % (name, done, len(tasks)),
                           "Jutro termin: " + st["title"], stamp)
    for t in d["tasks"]:
        day = as_day(t["date"])
        if t["kind"] != "publikacja" or t["state"] == "done" or not day:
            continue
        where = " (%s)" % t["channel"] if t["channel"] else ""
        lines += ics_event("pub-" + t["id"], day, "Publikacja: %s%s" % (t["title"], where),
                           "Kampania: %s. Projekt: %s." % (camps.get(t["campaign"], ""), names.get(t["project"], "")),
                           "Jutro publikacja: " + t["title"], stamp)
    lines.append("END:VCALENDAR")
    return "\r\n".join(ics_fold(l) for l in lines) + "\r\n"


# ---------- posty (stały rytm marketingu) ----------
POST_DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def post_folder(pid, day):
    """Folder posta: <karta projektu>/posty/<dzień>-<nazwa>/. None, gdy go nie ma albo dane są niepoprawne."""
    if not POST_DAY.match(day or ""):
        return None
    _, index = load_projects(resolve=False)
    folder = index.get(pid)
    if not folder:
        return None
    cards = os.path.dirname(os.path.realpath(os.path.join(folder, "KARTA.md")))
    base = os.path.join(cards, "posty")
    try:
        names = sorted(n for n in os.listdir(base) if n.startswith(day + "-") or n == day)
    except OSError:
        return None
    for n in names:
        path = os.path.realpath(os.path.join(base, n))
        if os.path.commonpath([os.path.realpath(base), path]) == os.path.realpath(base) and os.path.isdir(path):
            return path
    return None


def post_info(folder):
    """Tytuł i teksty z post.md: sekcje „## Facebook”, „## LinkedIn”, „## Alt” (pozostałe sekcje też, pod swoją nazwą)."""
    out = {"title": "", "sections": {}, "image": False, "folder": os.path.basename(folder)}
    try:
        with open(os.path.join(folder, "post.md"), encoding="utf-8") as f:
            text = f.read()
    except OSError:
        text = ""
    name = None
    for line in text.split("\n"):
        if line.startswith("# ") and not out["title"]:
            out["title"] = line[2:].strip()
        elif line.startswith("## "):
            name = line[3:].strip()
            out["sections"][name] = ""
        elif name is not None:
            out["sections"][name] += line + "\n"
    out["sections"] = {k: v.strip() for k, v in out["sections"].items()}
    out["image"] = bool(os.path.exists(os.path.join(folder, "grafika.png")) or os.path.exists(os.path.join(folder, "grafika.svg")))
    film = publikacja.Publisher.film(folder)
    out["film"] = {"name": os.path.basename(film), "size": os.path.getsize(film)} if film else None
    return out


def post_image(folder):
    """grafika.png posta; gdy brak albo starsza od grafika.svg, tworzy ją rsvg-convert. None, gdy nie da się."""
    png, svg = os.path.join(folder, "grafika.png"), os.path.join(folder, "grafika.svg")
    fresh = os.path.exists(png) and (not os.path.exists(svg) or os.path.getmtime(png) >= os.path.getmtime(svg))
    if not fresh and os.path.exists(svg) and shutil.which("rsvg-convert"):
        try:
            subprocess.run(["rsvg-convert", "-w", "1080", svg, "-o", png + ".tmp"], check=True, timeout=30,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            os.replace(png + ".tmp", png)
        except (OSError, subprocess.SubprocessError):
            pass
    return png if os.path.exists(png) else None


# ---------- strona ----------
APP_HEAD = ('<link rel="manifest" href="/app/manifest.webmanifest"><meta name="theme-color" content="#0b1020">'
            '<link rel="icon" href="/app/ikona.svg" type="image/svg+xml"><link rel="apple-touch-icon" href="/app/ikona-180.png">'
            '<meta name="apple-mobile-web-app-capable" content="yes"><meta name="mobile-web-app-capable" content="yes">'
            '<meta name="apple-mobile-web-app-title" content="Projekty"><meta name="apple-mobile-web-app-status-bar-style" content="black">')
# Pliki aplikacji (ikona, manifest): bez danych, dostępne bez logowania, żeby system mógł dodać panel jako aplikację.
APP_DIR = os.path.join(HERE, "app")
APP_FILES = {"manifest.webmanifest": "application/manifest+json", "ikona.svg": "image/svg+xml",
             "ikona-180.png": "image/png", "ikona-192.png": "image/png", "ikona-512.png": "image/png"}


SHELL = ('<!doctype html><html lang="pl"><head><meta charset="utf-8">'
         '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>Panel projektów</title>' + APP_HEAD +
         '</head><body>%s</body></html>')


def page_html(preview=None):
    with open(PAGE, encoding="utf-8") as f:
        html = f.read()
    if preview is not None:
        html = html.replace("/*PREVIEW*/null", json.dumps(preview, ensure_ascii=False, separators=(",", ":")), 1)
    return html


def preview_data():
    """Same dane przykładowe, z datami względnymi (strona przelicza je przy otwarciu) i bez ścieżek."""
    out = {"projects": [], "stages": [], "tasks": [], "campaigns": []}
    for folder in sample_folders():
        d = projekt.read_project(folder)
        d["project"]["origin"] = "sample"
        out["projects"].append(d["project"])
        for k in ("stages", "tasks", "campaigns"):
            out[k] += d[k]
    cal = load_json(SAMPLE_CAL, {"calendars": [], "events": []})
    out["projectsSource"] = "sample"
    out["standard"] = projekt.describe()
    out["dayMinutes"] = day_minutes()
    out["pmNote"] = pm_note(True)
    out["history"] = historia.sample(SAMPLE_HISTORY)      # daty względne, jak w zadaniach i etapach
    out["calendar"] = {"calendars": cal.get("calendars", []), "events": cal.get("events", [])}
    block = load_json(SAMPLE_AGENTS, None)
    block = block if isinstance(block, dict) else {}
    # podgląd bez serwera: tylko kontrola plików
    add_checks(out["tasks"], {projekt.slug(os.path.basename(f)): f for f in sample_folders()}, None)
    agents.annotate_sample(out["tasks"], block)    # w podglądzie zadania przykładowe wyglądają jak prawdziwe
    if block:
        out["agents"] = block
    return out


def export_preview(path):
    """Zapisuje stronę z wbudowanymi danymi przykładowymi, bez żadnych danych z kalendarza."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(page_html(preview_data()))
    print("Zapisano", path, os.path.getsize(path), "bajtów")


class Handler(BaseHTTPRequestHandler):
    server_version = "PanelProjektow/1.0"

    def log_message(self, fmt, *args):
        agents.log(fmt % args)

    def _host_ok(self):
        # Kalendarz to dane prywatne: odrzucamy żądania z obcą nazwą hosta (ochrona przed DNS rebinding).
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0].strip("[]").lower()
        return host in {"localhost", "127.0.0.1", "::1", HOST.lower(), *[h.lower() for h in EXTRA_HOSTS]}

    def _client_local(self):
        """Połączenie z tego komputera: adres loopback, lokalna nazwa hosta i brak nagłówków pośrednika.

        Pośrednik (np. `tailscale serve`) łączy się z adresu loopback, ale w imieniu innego urządzenia,
        więc takie żądanie traktujemy jak zdalne i wymagamy hasła.
        """
        ip = self.client_address[0]
        ip = ip[7:] if ip.startswith("::ffff:") else ip
        if not (ip == "::1" or ip.startswith("127.")):
            return False
        if any(self.headers.get(h) for h in ("X-Forwarded-For", "Forwarded", "X-Real-IP", "Tailscale-User-Login")):
            return False
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0].strip("[]").lower()
        return host in ("localhost", "127.0.0.1", "::1")

    def _has_session(self):
        if not TOKEN:
            return False
        try:
            morsel = SimpleCookie(self.headers.get("Cookie") or "").get(SESSION_COOKIE)
        except CookieError:
            return False
        return morsel is not None and session_ok(morsel.value)

    def _allowed(self, path, query=""):
        """Dostęp według AGENCI.md. Gdy żądanie nie przechodzi, wysyła odmowę i zwraca False."""
        if self._client_local():
            if self.command != "POST" or path == "/wejscie" or not local_guard() or self._has_session() \
                    or local_key_ok(self.headers.get(LOCAL_KEY_HEADER)):
                return True
            self._send(401, json.dumps({"ok": False, "error": "Zapis z tego komputera wymaga zalogowania albo klucza "
                                        "lokalnego."}, ensure_ascii=False), "application/json; charset=utf-8")
            return False
        if not TOKEN:
            self._send(403, "Dostęp z innego urządzenia wymaga hasła: ustaw PANEL_TOKEN na serwerze.",
                       "text/plain; charset=utf-8")
            return False
        if path == "/wejscie" or self._has_session() or self._app_file(path):
            return True
        if self.command == "GET" and path.startswith("/media/"):     # plik dla Instagrama: jednorazowy token w ścieżce
            return True
        if path == "/terminy.ics":
            key = (parse_qs(query).get("k") or [""])[0]
            if self.command == "GET" and hmac.compare_digest(key.encode("utf-8"), ics_key().encode("ascii")):
                return True
            self._send(401, "Wymagany klucz.", "text/plain; charset=utf-8")
        elif path.startswith("/api/"):
            self._send(401, json.dumps({"ok": False, "error": "Wymagane hasło."}, ensure_ascii=False),
                       "application/json; charset=utf-8")
        else:
            self._redirect("/wejscie")
        return False

    @staticmethod
    def _app_file(path):
        return path.startswith("/app/") and path[5:] in APP_FILES

    def _send(self, code, body, ctype, headers=()):
        raw = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        if not any(name.lower() == "cache-control" for name, _ in headers):
            self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for name, value in headers:
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(raw)

    def _redirect(self, where, headers=()):
        self._send(303, "", "text/plain; charset=utf-8", [("Location", where)] + list(headers))

    def _https(self):
        """Żądanie przyszło przez HTTPS: pośrednik (Caddy) ustawia X-Forwarded-Proto: https."""
        proto = (self.headers.get("X-Forwarded-Proto") or "").split(",")[0].strip().lower()
        return proto == "https"

    def _login(self):
        """POST /wejscie: formularz z polem haslo. Błędna próba: odpowiedź po 1 s, najwyżej 10 na minutę."""
        if self._client_local() and not (local_guard() and TOKEN):
            return self._redirect("/")
        if login_blocked():
            return self._send(429, login_page("Za dużo prób. Spróbuj za minutę."), "text/html; charset=utf-8")
        given = ""
        try:
            size = int(self.headers.get("Content-Length") or 0)
            if 0 < size <= 1024:
                given = (parse_qs(self.rfile.read(size).decode("utf-8")).get("haslo") or [""])[0].strip()
        except (ValueError, UnicodeDecodeError):
            given = ""
        if given and hmac.compare_digest(given.encode("utf-8"), TOKEN.encode("utf-8")):
            cookie = "%s=%s; HttpOnly; SameSite=Strict; Path=/; Max-Age=%d" % (SESSION_COOKIE, session_value(),
                                                                               SESSION_DAYS * 86400)
            if self._https():
                cookie += "; Secure"
            return self._redirect("/", [("Set-Cookie", cookie)])
        login_blocked(add=True)
        time.sleep(LOGIN_DELAY)
        return self._send(401, login_page("Błędne hasło."), "text/html; charset=utf-8")

    def do_GET(self):
        if not self._host_ok():
            return self._send(403, "Niedozwolony host", "text/plain; charset=utf-8")
        url = urlparse(self.path)
        path = url.path
        if not self._allowed(path, url.query):
            return
        if path.startswith("/media/"):
            parts = path.split("/")
            f = get_publisher().media_file(parts[2]) if len(parts) == 4 and re.match(r"^[0-9a-f]{32}$", parts[2]) else None
            if not f or os.path.basename(f) != parts[3]:
                return self._send(404, "Nie znaleziono", "text/plain; charset=utf-8")
            ctype = {".jpg": "image/jpeg", ".mp4": "video/mp4", ".mov": "video/quicktime"}.get(os.path.splitext(f)[1], "application/octet-stream")
            with open(f, "rb") as fh:
                return self._send(200, fh.read(), ctype, [("Cache-Control", "no-store")])
        if path == "/wejscie":
            if self._has_session() or (self._client_local() and not (local_guard() and TOKEN)):
                return self._redirect("/")
            return self._send(200, login_page(), "text/html; charset=utf-8")
        if path in ("/", "/index.html"):
            return self._send(200, SHELL % page_html(), "text/html; charset=utf-8")
        if path == "/podglad":
            return self._send(200, SHELL % page_html(preview_data()), "text/html; charset=utf-8")
        if path == "/api/data":
            return self._send(200, json.dumps(build_data(), ensure_ascii=False), "application/json; charset=utf-8")
        if path == "/terminy.ics":
            return self._send(200, build_ics(), "text/calendar; charset=utf-8")
        if path == "/api/agent/diff":
            qs = parse_qs(url.query)
            code, text = get_agents().diff((qs.get("id") or [""])[0], (qs.get("project") or [""])[0],
                                           (qs.get("branch") or [""])[0])
            if code == 200:
                return self._send(200, text, "text/plain; charset=utf-8")
            return self._send(code, json.dumps({"ok": False, "error": text}, ensure_ascii=False),
                              "application/json; charset=utf-8")
        if path == "/api/plik":
            code, answer = read_project_file(url.query)
            return self._send(code, json.dumps(answer, ensure_ascii=False), "application/json; charset=utf-8")
        if path in ("/api/post", "/api/post/grafika"):
            q = parse_qs(url.query)
            folder = post_folder((q.get("project") or [""])[0], (q.get("date") or [""])[0])
            if not folder:
                return self._send(404, json.dumps({"ok": False, "error": "Nie ma posta na ten dzień."}, ensure_ascii=False),
                                  "application/json; charset=utf-8")
            if path == "/api/post":
                return self._send(200, json.dumps(dict(post_info(folder), ok=True), ensure_ascii=False),
                                  "application/json; charset=utf-8")
            png = post_image(folder)
            if not png:
                return self._send(404, "Brak grafiki", "text/plain; charset=utf-8")
            with open(png, "rb") as f:
                return self._send(200, f.read(), "image/png", [("Content-Disposition", 'inline; filename="%s.png"'
                                                                 % os.path.basename(folder))])
        if self._app_file(path):
            with open(os.path.join(APP_DIR, path[5:]), "rb") as f:
                return self._send(200, f.read(), APP_FILES[path[5:]], [("Cache-Control", "max-age=86400")])
        if path == "/favicon.ico":
            return self._send(204, b"", "image/x-icon")       # bez ikony; przeglądarka nie zgłasza błędu 404
        return self._send(404, "Nie znaleziono", "text/plain; charset=utf-8")

    def do_POST(self):
        if not self._host_ok():
            return self._send(403, "Niedozwolony host", "text/plain; charset=utf-8")
        origin = self.headers.get("Origin")
        if origin and urlparse(origin).netloc != self.headers.get("Host"):
            return self._send(403, "Niedozwolone źródło", "text/plain; charset=utf-8")
        path = urlparse(self.path).path
        if not self._allowed(path):
            return
        if path == "/wejscie":
            return self._login()
        if path == "/api/calendar/connect":
            connect_calendar()
            return self._send(202, json.dumps({"connecting": True}), "application/json; charset=utf-8")
        if path == "/api/post/film":
            return self._film_upload(urlparse(self.path).query)
        if path in WRITES:
            body = self._json_body()
            if body is None:
                return self._send(400, json.dumps({"ok": False, "error": "Nieprawidłowe żądanie."}),
                                  "application/json; charset=utf-8")
            result = WRITES[path](body)
            code, answer = result[0], {"ok": result[0] == 200, "error": result[1]}
            if len(result) > 2:
                answer.update(result[2])            # np. id nowego uruchomienia
            return self._send(code, json.dumps(answer, ensure_ascii=False), "application/json; charset=utf-8")
        return self._send(404, "Nie znaleziono", "text/plain; charset=utf-8")

    def _film_upload(self, query):
        """POST /api/post/film?project=&date=: surowy plik MP4 albo MOV (najwyżej 300 MB) jako film.mp4|mov posta."""
        q = parse_qs(query)
        ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        ext = {"video/mp4": ".mp4", "video/quicktime": ".mov"}.get(ctype)
        folder = post_folder((q.get("project") or [""])[0], (q.get("date") or [""])[0])
        try:
            size = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            size = 0
        err = ("Nie ma posta na ten dzień." if not folder else "Film: MP4 albo MOV." if not ext
               else "Film: najwyżej 300 MB." if not 0 < size <= publikacja.FILM_MAX else "")
        if err:
            self.close_connection = True
            return self._send(400, json.dumps({"ok": False, "error": err}, ensure_ascii=False), "application/json; charset=utf-8")
        tmp = os.path.join(folder, ".film-wysylka")
        left = size
        with open(tmp, "wb") as f:
            while left > 0:
                chunk = self.rfile.read(min(left, 1 << 20))
                if not chunk:
                    break
                f.write(chunk)
                left -= len(chunk)
        if left:
            os.remove(tmp)
            return self._send(400, json.dumps({"ok": False, "error": "Wysyłka przerwana."}, ensure_ascii=False),
                              "application/json; charset=utf-8")
        for name in publikacja.FILM_NAMES:
            with contextlib.suppress(OSError):
                os.remove(os.path.join(folder, name))
        os.replace(tmp, os.path.join(folder, "film" + ext))
        return self._send(200, json.dumps({"ok": True, "error": "", "size": size}), "application/json; charset=utf-8")

    def _json_body(self):
        """Mały obiekt JSON. Wymagany typ application/json, więc obca strona nie wyśle go bez zgody CORS."""
        if (self.headers.get("Content-Type") or "").split(";")[0].strip().lower() != "application/json":
            return None
        try:
            size = int(self.headers.get("Content-Length") or 0)
            if not 0 < size <= 4096:
                return None
            body = json.loads(self.rfile.read(size).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return None
        return body if isinstance(body, dict) else None


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--export":
        export_preview(sys.argv[2])
        sys.exit(0)
    address = "http://%s:%d/" % ("localhost" if HOST == "127.0.0.1" else HOST, PORT)
    try:
        httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    except OSError as err:
        if err.errno != errno.EADDRINUSE:
            raise
        print("Port %d jest zajęty: panel prawdopodobnie już działa. Otwórz %s" % (PORT, address))
        print("Inny port: PANEL_PORT=4802 python3 dashboard/server.py")
        sys.exit(1)
    print("Panel: " + address)
    if HOST not in ("127.0.0.1", "localhost", "::1") and not TOKEN:
        print("Brak PANEL_TOKEN: połączenia z innych urządzeń będą odrzucane.")

    def _stop(signum, frame):
        raise KeyboardInterrupt

    for name in ("SIGTERM", "SIGBREAK"):       # zatrzymanie usługi ma zakończyć także procesy agentów
        if hasattr(signal, name):
            signal.signal(getattr(signal, name), _stop)
    get_agents().start()                        # dopiero po zajęciu portu: drugi egzemplarz nie rusza rekordów
    get_publisher().start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        get_agents().shutdown()
