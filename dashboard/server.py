#!/usr/bin/env python3
"""Panel projektów: raport PM, monitor zadań, agenci, kampanie, kalendarz, standard.

Mały serwer, tylko biblioteka standardowa Pythona:
  GET  /                      strona panelu (panel.html)
  GET  /podglad               ta sama strona z samymi danymi przykładowymi
  GET  /wejscie               strona hasła dla połączeń spoza tego komputera (POST: pole haslo)
  GET  /api/data              projekty, etapy, zadania, kampanie, kalendarz i blok agents
  POST /api/task/update       zmienia pola zadania w ZADANIA.md albo w pliku kampanii
  POST /api/task/state        zmienia sam stan zadania
  POST /api/task/add          dopisuje zadanie do etapu, do „Do rozplanowania” albo do harmonogramu kampanii
  POST /api/stage/update      zmienia termin etapu
  POST /api/campaign/update   zmienia wynik i stan kampanii
  POST /api/calendar/connect  prosi macOS o zgodę na odczyt kalendarza
  POST /api/agent/run         uruchamia agenta dla jednego zadania
  POST /api/agent/pm          uruchamia raport PM
  POST /api/agent/check       test połączenia z Claude Code albo Codex
  POST /api/agent/stop        zatrzymuje uruchomienie albo zdejmuje je z kolejki
  POST /api/agent/automat     włącza i wyłącza Automat
  POST /api/project/add       dopisuje folder do rejestru projektów (opcjonalnie zakłada pliki standardu)
  POST /api/project/remove    usuwa projekt z rejestru; pliki zostają
  POST /api/project/meta      zmienia pola karty projektu: faza, klient, próg (KARTA.md)
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
HOST = os.environ.get("PANEL_HOST", "").strip() or "127.0.0.1"
PORT = int(os.environ.get("PANEL_PORT", "").strip() or "4801")
# Dodatkowe nazwy hosta, pod którymi panel może być otwierany (np. adres Tailscale).
EXTRA_HOSTS = [h.strip() for h in os.environ.get("PANEL_ALLOWED_HOSTS", "").split(",") if h.strip()]
# Hasło panelu dla połączeń spoza tego komputera. Bez hasła takie połączenia są odrzucane.
TOKEN = os.environ.get("PANEL_TOKEN", "").strip()
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
        for c in out["campaigns"]:
            c["start"], c["end"] = resolve_date(c["start"]), resolve_date(c["end"])
        for p in out["projects"]:
            if p["lastDecision"]:
                p["lastDecision"]["date"] = resolve_date(p["lastDecision"]["date"])
    return out, index


_write_lock = threading.Lock()


def change_task(body):
    """{"id", "title", "state"}: zadanie odszukujemy po stronie serwera, nigdy po ścieżce od klienta."""
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


def answer_question(body):
    """{"id", "n", "answer"}: odpowiedź na pytanie z sekcji „Pytania do właściciela” w KARTA.md."""
    data, index = load_projects(resolve=False)
    pid = body.get("id")
    if data["projectsSource"] != "registry" or not isinstance(pid, str) or pid not in index:
        return 404, "Nie ma takiego projektu."
    try:
        with _write_lock:
            projekt.set_answer(index[pid], body.get("n"), body.get("answer", ""))
    except ValueError as e:
        return 400, "Nie zapisano: %s." % e
    except OSError:
        return 400, "Projekt nie ma pliku KARTA.md."
    return 200, ""


# ---------- agenci (agents.py) ----------
_agents = None
_agents_lock = threading.Lock()


def get_agents():
    """Jeden zarządca uruchomień na proces; powstaje przy pierwszym użyciu (eksport podglądu go nie potrzebuje)."""
    global _agents
    with _agents_lock:
        if _agents is None:
            _agents = agents.Manager(load_projects, _write_lock, projekt)
        return _agents


WRITES = {"/api/task/state": change_task, "/api/task/update": lambda b: update_task(b),
          "/api/task/add": lambda b: add_task(b), "/api/stage/update": lambda b: update_stage(b),
          "/api/campaign/update": lambda b: update_campaign(b),
          "/api/project/add": lambda b: add_project(b), "/api/project/remove": lambda b: remove_project(b),
          "/api/project/meta": lambda b: update_meta(b),
          "/api/agent/run": lambda b: get_agents().run_task(b.get("id", ""), b.get("title", "")),
          "/api/agent/pm": lambda b: get_agents().run_pm(),
          "/api/agent/check": lambda b: get_agents().run_check(b.get("tool", "claude")),
          "/api/agent/stop": lambda b: get_agents().stop(b.get("id", "")),
          "/api/agent/automat": lambda b: get_agents().set_automat(b.get("enabled")),
          "/api/agent/login": lambda b: get_agents().open_login(b.get("tool", "claude")),
          "/api/agent/recheck": lambda b: get_agents().recheck_login(),
          "/api/question/answer": lambda b: answer_question(b),
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
    else:
        calendar = {"status": status, "source": "sample", "error": cal.get("error", ""), **sample_calendar()}
    calendar["connecting"] = _cal["connecting"]
    out["calendar"] = calendar
    out["today"] = datetime.date.today().isoformat()
    out["generatedAt"] = datetime.datetime.now().isoformat(timespec="seconds")
    out["mode"] = "live"
    out["icsPath"] = "/terminy.ics" + ("?k=" + ics_key() if TOKEN else "")
    manager = get_agents()
    manager.annotate(out["tasks"], out["projectsSource"])
    out["agents"] = manager.snapshot()
    out["agents"]["canRunTasks"] = out["projectsSource"] == "registry"
    out["history"] = project_history(out)
    return out


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


def session_value():
    """Wartość ciasteczka: pochodna hasła, nie samo hasło."""
    return _derive("panel-sesja")


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
    return LOGIN_PAGE % ('<p class="blad" role="alert">%s</p>' % error if error else "")


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


# ---------- strona ----------
SHELL = ('<!doctype html><html lang="pl"><head><meta charset="utf-8">'
         '<meta name="viewport" content="width=device-width,initial-scale=1"></head><body>%s</body></html>')


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
    out["pmNote"] = pm_note(True)
    out["history"] = historia.sample(SAMPLE_HISTORY)      # daty względne, jak w zadaniach i etapach
    out["calendar"] = {"calendars": cal.get("calendars", []), "events": cal.get("events", [])}
    block = load_json(SAMPLE_AGENTS, None)
    block = block if isinstance(block, dict) else {}
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
        return morsel is not None and hmac.compare_digest(morsel.value.encode("utf-8"), session_value().encode("ascii"))

    def _allowed(self, path, query=""):
        """Dostęp według AGENCI.md. Gdy żądanie nie przechodzi, wysyła odmowę i zwraca False."""
        if self._client_local():
            return True
        if not TOKEN:
            self._send(403, "Dostęp z innego urządzenia wymaga hasła: ustaw PANEL_TOKEN na serwerze.",
                       "text/plain; charset=utf-8")
            return False
        if path == "/wejscie" or self._has_session():
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

    def _send(self, code, body, ctype, headers=()):
        raw = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for name, value in headers:
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(raw)

    def _redirect(self, where, headers=()):
        self._send(303, "", "text/plain; charset=utf-8", [("Location", where)] + list(headers))

    def _login(self):
        """POST /wejscie: formularz z polem haslo. Błędna próba: odpowiedź po 1 s, najwyżej 10 na minutę."""
        if self._client_local():
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
            cookie = "%s=%s; HttpOnly; SameSite=Strict; Path=/; Max-Age=2592000" % (SESSION_COOKIE, session_value())
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
        if path == "/wejscie":
            if self._client_local() or self._has_session():
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
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        get_agents().shutdown()
