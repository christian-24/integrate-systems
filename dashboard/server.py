#!/usr/bin/env python3
"""Panel projektów: raport PM, monitor zadań, agenci, kampanie, kalendarz, standard.

Mały serwer, tylko biblioteka standardowa Pythona:
  GET  /                      strona panelu (panel.html)
  GET  /podglad               ta sama strona z samymi danymi przykładowymi
  GET  /wejscie               strona hasła dla połączeń spoza tego komputera (POST: pole haslo)
  GET  /api/data              projekty, etapy, zadania, kampanie, kalendarz i blok agents
                              (projekt z częściami, pole karty „część projektu:”: partOf, partLabel, parts;
                              git: repo, remote, url, host, unpushed, branch)
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
  POST /api/agent/restart     „Zatrzymaj i uruchom z poprawką”: zatrzymuje zadanie i uruchamia je ponownie
  GET  /api/agent/przebieg    przebieg uruchomienia na żywo (?id=&od=numer ostatniego wiersza) i zrzuty strony
  GET  /api/agent/zrzut       zrzut PNG z .zrzuty/ katalogu roboczego uruchomienia (?id=&plik=telefon.png)
  GET  /api/task/chat         historia dawnej rozmowy o zadaniu (?id=), tylko do odczytu; nowe wiadomości o zadaniu idą
                              przez POST /api/project/chat z "task"
  GET  /api/odbior            strona „Odbiór pracy” (?id=): zadanie, wersje wyniku, uruchomienie, odebrane warianty
  GET  /api/odbior/plik       plik wersji wyniku (?id=&v=&path=), z Range
  POST /api/odbior/popraw     poprawka ze znacznikami pod zadaniem i od razu uruchomienie agenta
  POST /api/odbior/akceptuj   odbiór całości albo wybranych wariantów (zadanie zrobione)
  POST /api/project/chat      wiadomość w Rozmowie w projekcie (Claude czyta, zmienia ZADANIA/DECYZJE/kampanie na prośbę,
                              uruchamia zadania przez run_task); "task": id zadania („Zapytaj o to zadanie”, kontekst
                              zadania), "execute": true (polecenie pod zadaniem i uruchomienie agenta, bez modelu),
                              "attach": {"kind": "strona", …} (uwaga do strony z zakładki Strona, bez modelu)
  GET  /api/project/chat      historia Rozmowy w projekcie (?project=)
  POST /api/asystent          wiadomość do asystenta (wszystkie projekty, może przełączyć widok: „Pokaż: #adres”)
  GET  /api/asystent          historia rozmowy z asystentem (z odpowiedzią w trakcie pisania); POST /api/asystent/nowa
                               czyści rozmowę
  GET  /api/asystent/karty     biblioteka kart asystenta (zapisane, wbudowane, przypięte, ukryte);
  POST /api/asystent/karty     {"zapisz": karta} | {"usun": id} | {"przypiete": [id]} | {"ukryj": id} | {"pokaz": id}
  POST /api/asystent/glos      nagranie (audio/webm, audio/mp4) -> rozpoznany tekst -> wiadomość do asystenta;
                               POST /api/asystent/glos/start wczytuje model mowy w tle
  GET  /api/drive             Google Drive projektu: połączony, zamontowany, logowanie w toku (?project=)
  POST /api/drive/start|finish|montuj|anuluj|odlacz   podłączenie Drive tylko do odczytu (drive.py)
  GET  /api/drive/konta       połączone konta Google (jedno logowanie na konto), logowanie w toku
  GET  /api/drive/foldery     foldery konta (?account=, odswiez=1) do wyboru folderu projektu
  GET  /api/drive/powrot      powrót z Google przy własnym kliencie OAuth (bez sesji, chroni jednorazowy state)
  POST /api/drive/konto/start|finish|anuluj|usun   łączenie konta Google; /api/drive/wybierz: folder dla projektu
  POST /api/agent/merge       scala gałąź uruchomienia do bazy (git merge --no-ff, bez push)
  POST /api/repo/zatwierdz    zatwierdza niezatwierdzone zmiany w repozytorium projektu jako zmiany agenta
  POST /api/repo/odloz        odkłada niezatwierdzone zmiany do schowka git (z opisem); /api/repo/przywroc przywraca
  POST /api/agent/rownolegle  ile uruchomień agentów naraz (1–4), zapis w stan.json
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
import html
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
from urllib.parse import parse_qs, quote, urlparse

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
import film  # noqa: E402  (nagrywanie filmów ze scenariusza)
import scenariusz  # noqa: E402  (scenariusz nagrania filmu właściciela: scenariusz.md w folderze posta)
import pola  # noqa: E402  (pola formularza zadań właściciela: propozycja modelu, przejście)
import zasoby  # noqa: E402  (pamięć, dysk i rozmiary folderów serwera)
import drive  # noqa: E402  (Google Drive projektu tylko do odczytu, rclone)
import glos  # noqa: E402  (rozpoznawanie mowy dla asystenta, pracownik glos_stt.py)
import udostepnij  # noqa: E402  (ręczne udostępnienie posta przez rozszerzenie Chrome: IG, FB, LinkedIn, TikTok)
import grafiki  # noqa: E402  (grafiki do postów przez Codex: warianty w folderze posta)
import kopie  # noqa: E402  (kopia projektu a GitHub: stan, wysłanie, klon, kosz)
SHARES = udostepnij.Shares()
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
    """Czyta wszystkie projekty w standardzie. Zwraca (dane dla strony, {id projektu: folder}).
    Części projektu (pole karty „część projektu:”) zostają osobnymi projektami z partOf (projekt.link_parts)."""
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
    projekt.link_parts(out["projects"], index)
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
    if ok and body.get("state") == "done":
        note_closed(parts[0], parts[1], str(body.get("title", "")))
    return (200, "") if ok else (409, "Plik zmienił się od ostatniego odczytu. Odświeżam listę.")


def finish_task(body):
    """POST /api/task/finish {id, title, values, steps?, count?}: „Zrobione” w formularzu zadania właściciela.
    values: odpowiedzi w kolejności pól `pyta:` (tak/nie jako true/false), sprawdzane według typu
    (projekt.answer_lines); steps: stan kroków [true, false, …]. Zapisuje `odpowiedź:` i kroki, potem stan [x]
    (zadania z `po:` na tym zadaniu przestają czekać); z count przez count_task, jak /api/task/state."""
    t, data, where = _find_task(body.get("id", ""), body.get("title", ""))
    if t is None:
        return where
    if t["state"] == "done":
        return CONFLICT
    folder, file, line = where, t["file"], t["line"]
    try:
        lines = projekt.answer_lines(t["detail"].get("fields") or [], body.get("values"))
    except ValueError as e:
        return 400, "Nie zapisano: %s." % e
    steps = body.get("steps") if isinstance(body.get("steps"), list) else []
    if any(not isinstance(x, bool) for x in steps):
        return 400, "Nie zapisano: kroki to true albo false."
    have = t["detail"].get("steps") or []
    try:
        with _write_lock:
            ok = True
            if lines:
                ok = projekt.set_detail(folder, file, line, t["title"], "odpowiedź", lines)
            for i, done in enumerate(steps[:len(have)]):
                if ok and done != have[i]["done"]:
                    ok = projekt.set_detail(folder, file, line, t["title"], projekt.STEP_KEY, {"index": i, "done": done})
            if ok and body.get("count") is None:
                ok = projekt.set_state(folder, file, line, t["title"], "done")
    except (ValueError, OSError):
        return 400, "Nie udało się zapisać zmiany."
    if not ok:
        return CONFLICT
    if body.get("count") is not None:
        return count_task(body, state="done")
    note_closed(t["project"], file, t["title"])
    return 200, ""


def task_fields(body):
    """POST /api/task/pola {id, title}: pola formularza dla zadania właściciela bez `pyta:` (pola.Fields.for_task)."""
    return get_fields().for_task(body.get("id", ""), body.get("title", ""))


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


DETAIL_KEYS = ("wykonawca", "cel", "gotowe gdy", "materiał", "wynik", "decyzja", "zostało", "poprawka", "następne", "krok",
               "wyświetlenia", "kliknięcia", "konta", "link", "gałąź", "pyta", "odpowiedź", "zmiany")
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
    note_closed(t["project"], t["file"], title)
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


# wynik pracy agenta do obejrzenia w zadaniu (GET /api/plik/surowy): obrazy i PDF, bez SVG i HTML (skrypty)
ASSET_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp",
               ".pdf": "application/pdf"}
ASSET_MAX = 15 * 1024 * 1024


def project_file(pid, rel, types=FILE_TYPES, max_size=FILE_MAX):
    """Ścieżka pliku materiału albo (None, komunikat). Tylko pliki o rozszerzeniach z types (domyślnie .md i .txt)
    wewnątrz folderu projektu albo folderu jego karty (KARTA.md może być dowiązaniem do szkice/); porównanie po realpath."""
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
            if not path.lower().endswith(tuple(types)):
                return None, ("Panel pokazuje tylko pliki .md i .txt." if types == FILE_TYPES
                              else "Panel pokazuje tylko obrazy PNG, JPG, WEBP i pliki PDF.")
            if os.path.getsize(path) > max_size:
                return None, "Plik jest większy niż %d %s." % ((200, "KB") if max_size == FILE_MAX else (max_size >> 20, "MB"))
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


def read_project_asset(query):
    """GET /api/plik/surowy: (kod, bajty | komunikat, typ). Obraz albo PDF z folderu projektu (karty), a gdy go tam
    nie ma i podano branch=agent/…, z nie scalonej gałęzi agenta."""
    q = parse_qs(query)
    pid, rel, branch = ((q.get(k) or [""])[0] for k in ("project", "path", "branch"))
    ctype = ASSET_TYPES.get(os.path.splitext(str(rel).lower())[1])
    if not ctype:
        return 404, "Panel pokazuje tylko obrazy PNG, JPG, WEBP i pliki PDF.", ""
    path, error = project_file(pid, rel, ASSET_TYPES, ASSET_MAX)
    if path:
        try:
            with open(path, "rb") as f:
                return 200, f.read(), ctype
        except OSError:
            return 404, "Nie udało się odczytać pliku.", ""
    if branch and error == "Nie ma takiego pliku.":
        data, error = get_agents().branch_blob(pid, branch, rel, tuple(ASSET_TYPES), ASSET_MAX)
        if data is not None:
            return 200, data, ctype
    return 404, error, ""


def read_project_file(query):
    """GET /api/plik: (kod, odpowiedź)."""
    q = parse_qs(query)
    pid, rel, anchor, branch = ((q.get(k) or [""])[0] for k in ("project", "path", "anchor", "branch"))
    path, error = project_file(pid, rel)
    if path:
        text = projekt.read(path)
    elif branch and error == "Nie ma takiego pliku.":
        # plik dopisany na gałęzi agenta, jeszcze nie scalony: treść z gałęzi (git show)
        text, error = get_agents().branch_file(pid, branch, rel)
        if text is None:
            return 404, {"ok": False, "error": error}
    else:
        return 404, {"ok": False, "error": error}
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
_recorder = None


def get_recorder():
    """Nagrywanie filmów (film.py); jedno na proces."""
    global _recorder
    with _agents_lock:
        if _recorder is None:
            _recorder = film.Recorder(notify=lambda text: get_agents()._send_ntfy(text, "#marketing"))
        return _recorder


def record_film(body):
    """POST /api/film/nagraj {project, date}: nagranie filmu posta w tle (widok Teraz widzi je od razu)."""
    res = get_recorder().start(post_folder(str(body.get("project") or ""), str(body.get("date") or "")),
                               str(body.get("title") or ""))
    with _films_lock:
        _films_cache["at"] = 0.0
    return res


def film_account(body):
    """POST /api/film/konto {email, haslo}: konto demo do nagrań (plik 0600, hasło nie wraca do panelu)."""
    email, password = str(body.get("email") or "").strip(), str(body.get("haslo") or "")
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email) or not 6 <= len(password) <= 200:
        return 400, "Podaj e-mail i hasło konta demo (co najmniej 6 znaków)."
    film.save_account(email, password)
    return 200, ""


def fix_post(body):
    """POST /api/post/popraw {project, date, uwaga}: zadanie dla agenta „Popraw post na …” z uwagą właściciela."""
    pid, day, note = str(body.get("project") or ""), str(body.get("date") or ""), str(body.get("uwaga") or "").strip()
    folder = post_folder(pid, day)
    if not folder:
        return 404, "Nie ma posta na ten dzień."
    if not 3 <= len(note) <= 1000:
        return 400, "Napisz, co poprawić (do 1000 znaków)."
    try:                                        # miejsce w filmie z edytora: sekunda i napis sceny
        at = float(body.get("czas")) if body.get("czas") not in (None, "") else None
    except (TypeError, ValueError):
        at = None
    scene = projekt._clean(str(body.get("napis") or ""), 120)
    if at is not None and 0 <= at < 3600:
        note = "[film %d:%02d%s] %s" % (int(at) // 60, int(at) % 60, (", scena „%s”" % scene) if scene else "", note)
    _, index = load_projects(resolve=False)
    proj = index.get(pid)
    rel = "posty/" + os.path.basename(folder)
    title = projekt._clean("Popraw post na %s: %s" % (day, note), 120)
    detail = {"cel": "post %s poprawiony według uwagi właściciela" % rel,
              "gotowe gdy": "w %s/post.md (i scenariusz.json przy filmie) uwzględniona uwaga z wiersza poprawka:" % rel,
              "poprawka": note, "materiał": [rel + "/post.md"] + film_refs(folder)}
    try:
        with _write_lock:
            get_agents()._add_task(proj, pid, title, {"executor": "claude", "machine": "cloud",
                                                      "date": datetime.date.today().isoformat()}, detail)
    except (ValueError, OSError, StopIteration) as e:
        return 409, "Nie dodano zadania: %s" % e
    started = False
    try:                                        # agent od razu, bez czekania na Automat (gdy nie może, zrobi to Automat)
        data, _ = load_projects()
        t = next((x for x in data["tasks"] if x["project"] == pid and x["title"] == title and x["state"] != "done"), None)
        if t:
            started = get_agents().run_task(t["id"], t["title"])[0] == 200
    except Exception:  # noqa: BLE001
        pass
    return 200, "", {"title": title, "started": started}


# ---------- scenariusz nagrania (scenariusz.py; STANDARD.md „Scenariusz nagrania”) ----------
def _script_ctx(body):
    """(dane, folder projektu, projekt, publikacja, dzień) albo (kod, komunikat). Publikacja: id z body, inaczej
    pierwsza z filmem tego dnia, inaczej pierwsza tego dnia."""
    pid, day, tid = str(body.get("project") or ""), str(body.get("date") or ""), str(body.get("id") or "")
    if not POST_DAY.match(day):
        return 400, "Podaj dzień publikacji (RRRR-MM-DD)."
    data, index = load_projects()
    proj = next((p for p in data["projects"] if p["id"] == pid), None)
    if not proj or pid not in index:
        return 404, "Nie ma takiego projektu."
    pubs = [t for t in data["tasks"] if t["project"] == pid and t.get("kind") == "publikacja"
            and str(t.get("date") or "")[:10] == day]
    pub = next((t for t in pubs if t["id"] == tid), None) or next((t for t in pubs if scenariusz.is_film(t)), None) \
        or (pubs[0] if pubs else None)
    if not pub:
        return 404, "Nie ma publikacji na ten dzień."
    return data, index[pid], proj, pub, day


def publication_material(pub, post, film_owner=False):
    """Brakujący materiał i miejsce zapisu zgodne z edytorem posta."""
    day = str(pub.get("date") or "")[:10]
    rel = "posty/" + (os.path.basename(post) if post else day + "-publikacja")
    if scenariusz.is_film(pub):
        if post and (scenariusz.read(post) or os.path.isfile(os.path.join(post, film.SCENARIO))
                     or publikacja.Publisher.film(post)):
            return None
        filename = scenariusz.FILE if film_owner else film.SCENARIO
        return "scenariusz filmu", rel + "/" + filename
    if re.search(r"\b(?:grafik\w*|infografik\w*|ilustracj\w*|karuzel\w*)\b", pub["title"], re.I):
        if post and any(os.path.isfile(os.path.join(post, name)) for name in ("grafika.png", "grafika.svg")):
            return None
        return "plik grafiki", rel + "/grafika.png"
    if post and any(v for k, v in post_text(post)[1].items() if k.casefold() != "alt"):
        return None
    return "tekst posta", rel + "/post.md"


def publication_job(pub, jobs):
    """Zadanie z przycisku lub istniejące otwarte zadanie przygotowania tego materiału."""
    pid, day = pub["project"], str(pub["date"])[:10]
    job = jobs.get((pid, agents.publication_task_title(pub, projekt)))
    if job:
        return job
    title = projekt._clean("%s%s: %s" % (agents.POST_TASK, day, pub["title"]), 160)
    if scenariusz.is_film(pub):
        title = projekt._clean("%s%s: %s" % (scenariusz.PREP_TASK, day, scenariusz.pub_title(pub)), 120)
    job = jobs.get((pid, title))
    return job if job and job["state"] != "done" else None


def publication_jobs(data, index):
    owners = {p["id"] for p in data["projects"] if p.get("filmOwner")}
    posts = {}
    jobs = {(t["project"], t["title"]): t for t in data["tasks"] if t["file"] == "ZADANIA.md"
            and t["title"].startswith(("Przygotuj publikację na ", agents.POST_TASK, scenariusz.PREP_TASK))}
    for pub in data["tasks"]:
        day = str(pub.get("date") or "")[:10]
        if pub.get("kind") != "publikacja" or pub["state"] == "done" or not POST_DAY.fullmatch(day):
            continue
        job = publication_job(pub, jobs)
        pid = pub["project"]
        if (pid, day) not in posts:
            posts[pid, day] = post_folder(pid, day, index)
        material = publication_material(pub, posts[pid, day], pid in owners)
        if material:
            pub["missingMaterial"] = material[0]
        if job:
            pub["materialTask"] = job["id"]


def assign_publication(body):
    tid, title = body.get("id"), body.get("title")
    manager = get_agents()
    with _write_lock:
        data, index = load_projects()
        pub = next((t for t in data["tasks"] if t["id"] == tid and t["title"] == title
                    and t.get("kind") == "publikacja" and t["state"] != "done"), None)
        if not pub:
            return 409, "Publikacja się zmieniła. Odśwież Marketing.", {}
        pid, day = pub["project"], str(pub.get("date") or "")[:10]
        if not POST_DAY.fullmatch(day):
            return 400, "Publikacja musi mieć termin.", {}
        if data["projectsSource"] != "registry":
            return 409, "Wybierz projekt z rejestru.", {}
        name = agents.publication_task_title(pub, projekt)
        folder = index[pid]

        job = publication_job(pub, {(pid, t["title"]): t for t in data["tasks"]
                                    if t["project"] == pid and t["file"] == "ZADANIA.md"})
        if job:
            return 200, "", {"task": job["id"]}
        owner = next((p.get("filmOwner") for p in data["projects"] if p["id"] == pid), False)
        material = publication_material(pub, post_folder(pid, day, index), owner)
        if not material:
            return 409, "Materiał do tej publikacji jest już gotowy.", {}
        kind, destination = material
        goal = "Przygotuj %s do publikacji „%s” (%s), termin %s. Pozostaw publikację właścicielowi." % (
            kind, pub["title"], pub.get("channel") or "kanał z kampanii", day)
        done_when = "%s jest w %s, zgodny z wpisem w %s i gotowy do odbioru przed publikacją %s." % (
            kind.capitalize(), destination, pub["file"], day)
        today = datetime.date.today().isoformat()
        rows = ["- [ ] %s | kto: agent | kiedy: %s" % (name, today)]
        rows.extend(projekt.DETAIL_INDENT + "%s: %s" % (field, projekt._clean(value, 1000))
                    for field, value in (("cel", goal), ("gotowe gdy", done_when), ("materiał", pub["file"])))
        try:
            projekt._insert_inbox(projekt._task_file(folder, "ZADANIA.md"), rows)
        except (ValueError, OSError):
            return 409, "Nie udało się zapisać zadania publikacji.", {}
        job = next((t for t in projekt.read_project(folder, pid)["tasks"]
                    if t["file"] == "ZADANIA.md" and t["title"] == name), None)
    if not job:
        return 409, "Nie udało się odczytać zapisanego zadania.", {}
    code, error, run = manager.run_task(job["id"], job["title"])
    record = manager.get(run.get("id", "")) if code == 200 else None
    state = (record or {}).get("state", "running" if code == 200 else "")
    return 200, "", {"task": job["id"], "state": state, "reason": error}


def _script_tasks(data, pid, day, prefix):
    return [t for t in data["tasks"] if t["project"] == pid and t["title"].startswith(prefix + day)]


def script_info(pid, day):
    """GET /api/scenariusz?project=&date=: tekst i odczyt scenariusz.md posta, kto nagrywa, dzień nagrania."""
    ctx = _script_ctx({"project": pid, "date": day})
    if len(ctx) == 2:
        return ctx[0], ctx[1], {}
    _, _, proj, pub, day = ctx
    folder = post_folder(pid, day)
    text = scenariusz.read(folder) if folder else None
    return 200, "", {"exists": text is not None, "text": text or "", "version": scenariusz.version(text) if text else "",
                     "script": scenariusz.parse(text) if text is not None else None,
                     "post": os.path.basename(folder) if folder else "",
                     "postReady": bool(folder) and os.path.isfile(os.path.join(folder, "post.md")),
                     "filmOwner": bool(proj.get("filmOwner")), "title": scenariusz.pub_title(pub),
                     "way": film_way(proj, day, scenariusz.parse(text) if text is not None else None),
                     "task": pub["id"], "recDay": scenariusz.rec_day(day)}


def film_way(proj, day, script=None):
    """Kto robi film: ty (nagrywasz), ai (robisz w AI), panel (studio). Z pliku scenariusza, z podziału karty
    zapisanego przez Automat (stan.json filmWays) albo z karty."""
    if script and script.get("way"):
        return script["way"]
    try:
        way = (get_agents()._state.get("filmWays") or {}).get("%s|%s" % (proj["id"], day))
    except Exception:
        way = None
    if way in scenariusz.WAYS:
        return way
    mix = proj.get("filmMix") or {}
    return "ty" if proj.get("filmOwner") and (len(mix) <= 1 or "ty" in mix) and not mix.get("ai") else \
        (max(mix, key=mix.get) if mix else "panel")


def _script_run(title, pid):
    """Uruchamia agenta dla zadania o tym tytule od razu (gdy nie może, zrobi to Automat). True, gdy ruszył."""
    try:
        data, _ = load_projects()
        t = next((x for x in data["tasks"] if x["project"] == pid and x["title"] == title and x["state"] != "done"), None)
        return bool(t) and get_agents().run_task(t["id"], t["title"])[0] == 200
    except Exception:  # noqa: BLE001
        return False


def script_prepare(body):
    """POST /api/scenariusz/przygotuj {project, date, id?, od_nowa?}: zadanie agenta „Przygotuj scenariusz nagrania
    na <dzień>: <tytuł>” i od razu uruchomienie. Bez folderu posta agent zakłada posty/<dzień>-<nazwa>/ (ścieżka
    w zadaniu). Istniejący scenariusz tylko
    z od_nowa (wtedy zadanie otwiera się ponownie z poprawką „napisz od nowa”)."""
    ctx = _script_ctx(body)
    if len(ctx) == 2:
        return ctx
    data, folder, proj, pub, day = ctx
    again = body.get("od_nowa") is True
    if any(t["state"] != "done" for t in _script_tasks(data, proj["id"], day, scenariusz.PREP_TASK)):
        return 409, "Agent już przygotowuje ten scenariusz."
    post = post_folder(proj["id"], day)
    if post and os.path.isfile(os.path.join(post, scenariusz.FILE)) and not again:
        return 409, "Scenariusz już jest. Nowy przygotujesz w menu ⋯ (Przygotuj od nowa)."
    cards = os.path.dirname(os.path.realpath(os.path.join(folder, "KARTA.md")))
    title = projekt._clean("%s%s: %s" % (scenariusz.PREP_TASK, day, scenariusz.pub_title(pub)), 120)
    try:
        with _write_lock:
            name = agents.publication_task_title(pub, projekt)
            if any(t["title"] == name and t["state"] != "done"
                   for t in projekt.read_project(folder, proj["id"])["tasks"]):
                return 409, "Agent już przygotowuje ten scenariusz."
            post = post or scenariusz.new_post_dir(cards, day, scenariusz.pub_title(pub))
            detail = get_agents().script_detail(folder, pub, "posty/" + os.path.basename(post),
                                                scenariusz.rec_day(day))
            old = next((t for t in _script_tasks(data, proj["id"], day, scenariusz.PREP_TASK) if t["title"] == title),
                       None)
            if old:                     # od nowa: to samo zadanie jeszcze raz, z poprawką
                if not projekt.set_state(folder, old["file"], old["line"], title, "todo"):
                    raise ValueError("wiersz zadania zmienił się w tym czasie")
                projekt.set_detail(folder, old["file"], old["line"], title, "wynik", "")
                projekt.set_detail(folder, old["file"], old["line"], title, "poprawka",
                                   "napisz scenariusz od nowa (poprzednia wersja do zastąpienia)" if again else "")
            else:
                get_agents()._add_task(folder, proj["id"], title, {"executor": "claude", "machine": "cloud",
                                                                   "date": datetime.date.today().isoformat()}, detail)
    except (ValueError, OSError, StopIteration) as e:
        return 409, "Nie dodano zadania: %s" % e
    return 200, "", {"title": title, "started": _script_run(title, proj["id"])}


def script_fix(body):
    """POST /api/scenariusz/popraw {project, date, uwaga}: zadanie agenta „Popraw scenariusz nagrania na <dzień>:
    <uwaga>” (rozmowa o scenariuszu w panelu) i od razu uruchomienie."""
    ctx = _script_ctx(body)
    if len(ctx) == 2:
        return ctx
    data, folder, proj, pub, day = ctx
    note = str(body.get("uwaga") or "").strip()
    if not 3 <= len(note) <= 1000:
        return 400, "Napisz, co zmienić (do 1000 znaków)."
    post = post_folder(proj["id"], day)
    if not post or not os.path.isfile(os.path.join(post, scenariusz.FILE)):
        return 404, "Scenariusza jeszcze nie ma. Najpierw go przygotuj."
    title = projekt._clean("%s%s: %s" % (scenariusz.FIX_TASK, day, note), 120)
    if any(t["title"] == title and t["state"] != "done" for t in data["tasks"] if t["project"] == proj["id"]):
        return 409, "Ta uwaga już czeka na agenta."
    rel = "posty/%s/%s" % (os.path.basename(post), scenariusz.FILE)
    detail = {"cel": "scenariusz nagrania %s poprawiony według uwagi właściciela" % rel,
              "gotowe gdy": "w %s uwzględniona uwaga z wiersza poprawka:; układ sekcji i wiersz - stan: bez zmian; "
                            "post.md bez zmian" % rel,
              "poprawka": note, "materiał": [rel] + ([pub["file"]] if pub.get("file") else [])}
    try:
        with _write_lock:
            get_agents()._add_task(folder, proj["id"], title, {"executor": "claude", "machine": "cloud",
                                                               "date": datetime.date.today().isoformat()}, detail)
    except (ValueError, OSError, StopIteration) as e:
        return 409, "Nie dodano zadania: %s" % e
    return 200, "", {"title": title, "started": _script_run(title, proj["id"])}


def _script_file(body):
    """(kontekst, ścieżka scenariusz.md, tekst) albo (kod, komunikat)."""
    ctx = _script_ctx(body)
    if len(ctx) == 2:
        return ctx
    post = post_folder(ctx[2]["id"], ctx[4])
    text = scenariusz.read(post) if post else None
    if text is None:
        return 404, "Scenariusza jeszcze nie ma. Najpierw go przygotuj."
    if str(body.get("old") or "") != scenariusz.version(text):
        return 409, "Scenariusz zmienił się w tym czasie (np. poprawił go agent). Odśwież i zmień jeszcze raz."
    return ctx, os.path.join(post, scenariusz.FILE), text


def script_text(body):
    """POST /api/scenariusz/tekst {project, date, text, old}: tekst scenariusza wprost z panelu. Stan zostaje ten sam
    (zmieniają go przyciski); old: wersja (scenariusz.version) z odczytu, inna wersja na dysku to 409."""
    got = _script_file(body)
    if len(got) == 2:
        return got
    _, path, text = got
    new = str(body.get("text") or "").replace("\r\n", "\n").strip()
    if not 20 <= len(new) <= scenariusz.MAX_TEXT:
        return 400, "Scenariusz: od 20 do %d znaków." % scenariusz.MAX_TEXT
    state = scenariusz.parse(text)["state"]
    new = scenariusz.set_state(new, state if state in scenariusz.STATES else "propozycja") + "\n"
    with _write_lock:
        projekt.write_atomic(path, new)
    return 200, "", {"version": scenariusz.version(new), "errors": scenariusz.parse(new)["errors"]}


def script_state(body):
    """POST /api/scenariusz/stan {project, date, stan, old}: propozycja → do realizacji (zadanie nagrania dla
    właściciela na dzień nagrania z materiałem scenariusza; film bez nagrania właściciela: zadanie agenta),
    do realizacji → nagrane (zamyka zadanie nagrania), do realizacji|nagrane → propozycja (cofnięcie)."""
    got = _script_file(body)
    if len(got) == 2:
        return got
    (data, folder, proj, pub, day), path, text = got
    want, now = str(body.get("stan") or ""), scenariusz.parse(text)["state"]
    now = now if now in scenariusz.STATES else "propozycja"
    if want not in scenariusz.STATES:
        return 400, "Stan: %s." % ", ".join(scenariusz.STATES)
    if (now, want) not in SCRIPT_MOVES:
        return 409, ("Scenariusz już ma stan „%s”." % want if now == want else
                     "Najpierw wyślij scenariusz do realizacji." if want == "nagrane" else
                     "Ze stanu „%s” nie można przejść do „%s”." % (now, want))
    rel = "posty/%s/%s" % (os.path.basename(os.path.dirname(path)), scenariusz.FILE)
    rec, title, owner = scenariusz.rec_day(day), scenariusz.pub_title(pub), bool(proj.get("filmOwner"))
    task_title = ""
    try:
        with _write_lock:
            if want == "do realizacji" and owner:
                task_title = projekt._clean("%s%s: %s" % (scenariusz.REC_TASK, day, title), 120)
                old = next((t for t in _script_tasks(data, proj["id"], day, scenariusz.REC_TASK)
                            if t["title"] == task_title), None)
                if old:                 # już jest: nowy dzień nagrania i znowu otwarte
                    projekt.update_task(folder, old["file"], old["line"], task_title, {"date": rec, "state": "todo"})
                else:
                    get_agents()._add_task(folder, proj["id"], task_title,
                                           {"executor": "ty", "date": rec, "minutes": scenariusz.REC_MINUTES},
                                           {"cel": "nagranie filmu do publikacji „%s” z %s według scenariusza"
                                                   % (title, day),
                                            "gotowe gdy": "ujęcia z sekcji Co nagrać nagrane; w panelu scenariusz "
                                                          "ma stan nagrane",
                                            "materiał": [rel]})
            elif want == "do realizacji":
                task_title = projekt._clean("%s%s: %s" % (scenariusz.AGENT_TASK, day, title), 120)
                if not any(t["title"] == task_title and t["state"] != "done" for t in data["tasks"]
                           if t["project"] == proj["id"]):
                    get_agents()._add_task(folder, proj["id"], task_title,
                                           {"executor": "claude", "machine": "cloud",
                                            "date": datetime.date.today().isoformat()},
                                           {"cel": "film do publikacji „%s” z %s według scenariusza nagrania %s"
                                                   % (title, day, rel),
                                            "gotowe gdy": "w folderze posta jest scenariusz.json filmu zgodny ze "
                                                          "scenariuszem nagrania (film nagra panel)",
                                            "materiał": [rel]})
            elif want == "nagrane":
                for t in _script_tasks(data, proj["id"], day, scenariusz.REC_TASK):
                    if t["state"] != "done":
                        projekt.set_state(folder, t["file"], t["line"], t["title"], "done")
            projekt.write_atomic(path, scenariusz.set_state(text, want))
    except (ValueError, OSError, StopIteration) as e:
        return 409, "Nie zapisano: %s" % e
    started = _script_run(task_title, proj["id"]) if want == "do realizacji" and not owner else False
    return 200, "", {"state": want, "task": task_title, "started": started}


SCRIPT_MOVES = {("propozycja", "do realizacji"), ("do realizacji", "nagrane"), ("do realizacji", "propozycja"),
                ("nagrane", "propozycja")}


def script_links(tasks, projects, index):
    """Publikacje z filmem w projektach z `nagrywa: ty` (i każda publikacja z plikiem scenariusz.md):
    t["script"] = {"state": "" | propozycja | do realizacji | nagrane, "shots", "seconds", "errors", "owner"}."""
    owners = {p["id"] for p in projects if p.get("filmOwner")}
    film_days = {(t["project"], str(t.get("date") or "")[:10]) for t in tasks
                 if t.get("kind") == "publikacja" and scenariusz.is_film(t)}
    cards = {}
    for t in tasks:
        day = str(t.get("date") or "")[:10]
        if t.get("kind") != "publikacja" or not POST_DAY.match(day) or t["project"] not in index:
            continue
        pid = t["project"]
        if pid not in cards:
            cards[pid] = os.path.dirname(os.path.realpath(os.path.join(index[pid], "KARTA.md")))
        if not scenariusz.is_film(t) and (pid, day) in film_days:
            continue                    # folder posta jest jeden na dzień: scenariusz należy do filmu tego dnia
        post = scenariusz.post_dir(cards[pid], day)
        info = scenariusz.summary(post) if post else None
        if info is None and not (pid in owners and scenariusz.is_film(t)):
            continue
        t["script"] = dict(info or {"state": "", "shots": 0, "seconds": 0, "errors": 0}, owner=pid in owners)


def film_change(body):
    """POST /api/film/zmien {project, date, params: {nazwa: wartość}} albo {…, slides: [{n, tekst, podpis}]}: zmiana
    treści filmu wprost w panelu (bez agenta). Zapis w scenariusz.json po tych samych kontrolach co nagranie
    (film.apply_changes), potem nagranie od nowa: od razu, gdy nagrywarka jest wolna; gdy nagrywa (ten albo inny
    film), w kolejce nagrywarki zaraz po bieżącym nagraniu (Recorder.start). Panel bez nagrywarki: nagra Automat
    nagrań na serwerze (wersja scenariusza jest nowsza niż film)."""
    pid, day = str(body.get("project") or ""), str(body.get("date") or "")
    folder = post_folder(pid, day)
    if not folder:
        return 404, "Nie ma posta na ten dzień."
    params, slides, music = body.get("params"), body.get("slides"), body.get("music", film.UNSET)
    if not params and not slides and music is film.UNSET:
        return 400, "Podaj, co zmienić."
    if music is not film.UNSET and not (music is False or (isinstance(music, str) and len(music) <= 100)):
        return 400, "Podkład: nazwa pliku z listy marki, false (bez muzyki) albo pusty (na zmianę)."
    if params is not None and not (isinstance(params, dict) and len(params) <= 40
                                   and all(isinstance(k, str) and len(str(v)) <= 300 for k, v in params.items())):
        return 400, "Zmiany: najwyżej 40 pól po 300 znaków."
    if slides is not None and not (isinstance(slides, list) and len(slides) <= film.MAX_CARDS):
        return 400, "Zmiany plansz: lista najwyżej %d plansz." % film.MAX_CARDS
    try:
        with _write_lock:
            info = film.apply_changes(folder, params=params or None, slides=slides or None, music=music)
    except film.ScenarioChanged:
        return 409, "Scenariusz filmu zmienił się w tym czasie (np. zapisał go agent). Odśwież i zmień jeszcze raz."
    except ValueError as e:
        return 400, "Nie zapisano: %s." % e
    except OSError as e:
        return 409, "Nie zapisano scenariusza (%s)." % e
    if info.get("missing"):              # zapisane, ale brakuje jeszcze pliku w innym polu obrazu: bez nagrania
        with _films_lock:
            _films_cache["at"] = 0.0
        return 200, "", {"recording": False, "queued": False, "seconds": 0,
                         "note": "Brakuje jeszcze pliku w polu „%s”; film nagra się po jego wgraniu." % info["missing"]}
    code, msg, data = get_recorder().start(folder, str(body.get("title") or ""))
    with _films_lock:
        _films_cache["at"] = 0.0
    recording = code == 202 and data.get("state") == "running"
    note = "" if recording else data.get("note") or (msg if code >= 400 else "")
    return 200, "", {"recording": recording, "queued": data.get("state") == "queued", "note": note,
                     "seconds": info.get("seconds", 0)}


STUDIO_KINDS = {"marka": "plansze i wygląd marki", "szablon": "nowy szablon filmu"}


def studio_request(body):
    """POST /api/studio/popros {project, rodzaj: marka|szablon, uwaga}: zadanie dla agenta „Zmień studio filmów …”
    (zmiana dla wszystkich filmów projektu: marka.json albo nowy szablon)."""
    pid, kind, note = (str(body.get("project") or ""), str(body.get("rodzaj") or ""),
                       str(body.get("uwaga") or "").strip())
    data, index = load_projects(resolve=False)
    folder = index.get(pid)
    if not folder:
        return 404, "Nie ma takiego projektu."
    if kind not in STUDIO_KINDS:
        return 400, "Rodzaj: marka albo szablon."
    if not 3 <= len(note) <= 1000:
        return 400, "Napisz, co zmienić (do 1000 znaków)."
    title = projekt._clean("%s%s: %s" % (agents.STUDIO_TASK, STUDIO_KINDS[kind], note), 120)
    _templates, refs = agents.Manager.studio_refs(folder)
    detail = {"cel": "studio filmów projektu zmienione według uwagi właściciela (%s), dla wszystkich filmów"
                     % STUDIO_KINDS[kind],
              "gotowe gdy": ("studio/marka.json zmienione według uwagi; python3 film.py sprawdz przechodzi dla postów "
                             "z dniem od dziś" if kind == "marka" else
                             "nowy plik studio/szablony/<nazwa>.json z polami tytul, opis, dla_wlasciciela, wymagane; "
                             "python3 film.py sprawdz przechodzi dla posta z tym szablonem i dla wszystkich postów od "
                             "dziś, które używają zmienionego szablonu; nazw parametrów szablonu używanego w postach "
                             "nie zmieniasz i takiego szablonu nie usuwasz"),
              "poprawka": note, "materiał": refs or ["studio/"]}
    try:
        with _write_lock:
            get_agents()._add_task(folder, pid, title, {"executor": "claude", "machine": "cloud",
                                                        "date": datetime.date.today().isoformat()}, detail)
    except (ValueError, OSError, StopIteration) as e:
        return 409, "Nie dodano zadania: %s" % e
    return 200, "", {"title": title, "started": _script_run(title, pid)}    # od razu, jak inne przyciski (run_task)


STUDIO_TYPES = {"muzyka": {"audio/mpeg": "mp3", "audio/mp3": "mp3", "audio/mp4": "m4a", "audio/x-m4a": "m4a",
                           "audio/aac": "aac", "audio/wav": "wav", "audio/x-wav": "wav", "audio/wave": "wav",
                           "audio/ogg": "ogg"},
                "logo": {"image/png": "png", "image/jpeg": "jpg"}}


def _studio_of(pid):
    """(folder studio/ karty projektu, błąd). Studio nie może być dowiązaniem poza kartę projektu."""
    _data, index = load_projects(resolve=False)
    card = index.get(pid)
    if not card:
        return None, "Nie ma takiego projektu."
    card = os.path.dirname(os.path.realpath(os.path.join(card, "KARTA.md")))
    studio = os.path.join(card, film.STUDIO)
    if os.path.lexists(studio) and not film._inside(studio, studio):
        return None, "Folder studio/ wskazuje poza kartę projektu."
    return studio, ""


def _brand_edit(studio, change):
    """Zmiana marka.json z panelu: odczyt, change(raw) (zwraca błąd albo ""), kontrola validate_brand i zapis
    atomowy; pod _write_lock i z kontrolą czasu modyfikacji (zmiana agenta w międzyczasie nie zostanie nadpisana).
    Brak pliku: marka zaczyna się od kolorów domyślnych (DEFAULT_BRAND), żeby wgrany podkład nie psuł filmów
    projektu. (kod, błąd)."""
    bpath = os.path.join(studio, film.BRAND)
    with _write_lock:
        try:
            stamp = os.stat(bpath).st_mtime_ns if os.path.isfile(bpath) else None
            raw = film._load_json(bpath) if stamp is not None else {
                "nazwa": "", "kolory": dict(film.DEFAULT_BRAND["kolory"])}
        except (OSError, ValueError) as e:
            return 409, "marka.json jest uszkodzona (%s); popraw ją najpierw." % str(e)[:80]
        if not isinstance(raw, dict):
            return 409, "marka.json jest uszkodzona; popraw ją najpierw."
        err = change(raw)
        if err:
            return 409, err
        errors = film.validate_brand(raw)
        if errors:
            return 409, "Nie zapisano marki: %s." % errors[0]
        now = os.stat(bpath).st_mtime_ns if os.path.isfile(bpath) else None
        if now != stamp:
            return 409, "marka.json zmieniła się w tym czasie (np. zapisał ją agent). Odśwież i spróbuj jeszcze raz."
        tmp = bpath + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False, indent=1)
            f.write("\n")
        os.replace(tmp, bpath)
    with _films_lock:
        _films_cache["at"] = 0.0
    return 200, ""


def studio_add_file(pid, kind, ctype, data, licence, corner=None):
    """Podkład albo logo wgrane w panelu: plik w studio/ projektu (kontrola treści jak przy nagraniu: media_error)
    i wpis w marka.json: podkład dopisany do listy "muzyka" (filmy dostają podkłady na zmianę), logo w "logo"
    (corner: True/False ustawia "logo_w_rogu", czyli logo w rogu przez cały film); licencja (skąd plik i na jakich
    warunkach) dopisana do "zrodlo". Zmiana marki nagra od nowa filmy postów od dziś. (kod, błąd, dane)."""
    if kind not in STUDIO_TYPES:
        return 400, "Rodzaj: muzyka albo logo.", {}
    studio, err = _studio_of(pid)
    if not studio:
        return (404 if err.startswith("Nie ma") else 409), err, {}
    ext = STUDIO_TYPES[kind].get(ctype)
    if not ext:
        return 400, ("Podkład: plik mp3, m4a, wav albo ogg." if kind == "muzyka" else "Logo: plik png albo jpg."), {}
    licence = re.sub(r"\s+", " ", str(licence or "")).strip()
    if not 3 <= len(licence) <= 200:
        return 400, "Napisz, skąd jest plik i na jakiej licencji (3–200 znaków).", {}
    if kind == "muzyka":                 # limit podkładów przed zapisem pliku (bez osieroconych plików w studio/)
        try:
            cur = film._load_json(os.path.join(studio, film.BRAND)) if os.path.isfile(
                os.path.join(studio, film.BRAND)) else {}
        except (OSError, ValueError):
            cur = {}
        if isinstance(cur, dict) and len(film.music_list(cur.get("muzyka"))) >= film.MUSIC_MAX:
            return 409, ("Marka ma już %d podkładów. Usuń któryś z listy podkładów w Studiu filmów "
                         "(przycisk „Usuń z listy”)." % film.MUSIC_MAX), {}
    os.makedirs(studio, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    base = "muzyka-%s" % stamp if kind == "muzyka" else "logo-%s" % stamp
    name = "%s.%s" % (base, ext)
    n = 2
    while os.path.lexists(os.path.join(studio, name)):      # dwa wgrania w tej samej sekundzie: osobne pliki
        name, n = "%s-%d.%s" % (base, n, ext), n + 1
    path = os.path.join(studio, name)
    tmp = os.path.join(studio, ".%s.tmp" % name)
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, path)
    bad = film.media_error(path, "audio" if kind == "muzyka" else "image")
    if bad:
        os.remove(path)
        return 400, "Plik odrzucony: %s." % bad, {}

    def change(raw):
        if kind == "muzyka":
            songs = film.music_list(raw.get("muzyka"))
            if len(songs) >= film.MUSIC_MAX:
                return "Marka ma już %d podkładów; usuń któryś z listy." % film.MUSIC_MAX
            raw["muzyka"] = songs + [name] if songs else name
        else:
            raw["logo"] = name
            if corner is not None:
                raw["logo_w_rogu"] = bool(corner)
        raw["zrodlo"] = ("%s; %s %s: %s" % (str(raw.get("zrodlo") or "").rstrip("; "), kind, name,
                                           licence)).lstrip("; ")
        return ""
    code, err = _brand_edit(studio, change)
    if code != 200:
        os.remove(path)
        return code, err, {}
    return 200, "", {"name": name}


def studio_settings(body):
    """POST /api/studio/ustaw {project, logo_w_rogu: true|false}: logo marki w rogu przez cały film (bez prośby do
    agenta). Nagra od nowa filmy nadchodzących postów projektu."""
    studio, err = _studio_of(str(body.get("project") or ""))
    if not studio:
        return 404, err
    corner = body.get("logo_w_rogu")
    if not isinstance(corner, bool):
        return 400, "logo_w_rogu: true albo false."

    def change(raw):
        if corner and not raw.get("logo"):
            return "Najpierw dodaj logo."
        raw["logo_w_rogu"] = corner
        return ""
    return _brand_edit(studio, change)


def studio_remove_music(body):
    """POST /api/studio/usun {project, plik}: podkład znika z listy marki (plik zostaje w studio/, a w "zrodlo"
    licencja). Nie usuwa podkładu, który wybrał scenariusz nadchodzącego posta."""
    pid, name = str(body.get("project") or ""), str(body.get("plik") or "")
    studio, err = _studio_of(pid)
    if not studio:
        return 404, err
    if not film.AUDIO_RE.match(name):
        return 400, "Podaj plik podkładu."
    card = os.path.dirname(studio)
    today = datetime.date.today().isoformat()
    try:
        posts = sorted(os.listdir(os.path.join(card, "posty")))
    except OSError:
        posts = []
    for n in posts:
        if n[:10] < today:
            continue
        try:
            raw = film._load_json(os.path.join(card, "posty", n, film.SCENARIO))
        except (OSError, ValueError):
            continue
        if isinstance(raw, dict) and raw.get("muzyka") == name:
            return 409, "Ten podkład wybrał film posta z %s. Zmień tam podkład, potem usuń go z listy." % n[:10]

    def change(raw):
        songs = film.music_list(raw.get("muzyka"))
        if name not in songs:
            return "Tego podkładu nie ma na liście marki."
        rest = [x for x in songs if x != name]
        raw["muzyka"] = rest if len(rest) > 1 else (rest[0] if rest else "")
        return ""
    return _brand_edit(studio, change)


def studio_music_file(pid, name):
    """Plik podkładu z listy marki do odsłuchu w panelu: ścieżka albo None."""
    studio, _err = _studio_of(pid)
    if not studio or not film.AUDIO_RE.match(name or ""):
        return None
    brand, errors, _exists = film.load_brand(studio)
    if errors or name not in film.music_list(brand.get("muzyka")):
        return None
    path = os.path.join(studio, name)
    return path if os.path.isfile(path) and film._inside(path, studio) else None


AUDIO_TYPES = {"mp3": "audio/mpeg", "m4a": "audio/mp4", "aac": "audio/aac", "wav": "audio/wav", "ogg": "audio/ogg"}


def post_add_image(pid, day, param, ctype, data):
    """Zrzut ekranu albo zdjęcie do filmu posta (POST /api/post/obraz): plik w folderze posta i od razu w parametrze
    szablonu, który jest obrazem planszy (np. „Zrzut 1”), potem nagranie od nowa. (kod, błąd, dane)."""
    folder = post_folder(pid, day)
    if not folder:
        return 404, "Nie ma posta na ten dzień.", {}
    ext = STUDIO_TYPES["logo"].get(ctype)
    if not ext:
        return 400, "Zrzut: plik png albo jpg.", {}
    info = film.describe(folder)
    images = ((info.get("fields") or {}).get("images") or []) if isinstance(info.get("fields"), dict) else []
    if param not in images:
        return 400, "Ten film nie ma takiego pola z obrazem.", {}
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    name = "%s-%s.%s" % (param.replace("_", "-"), stamp, ext)
    n = 2
    while os.path.lexists(os.path.join(folder, name)):
        name, n = "%s-%s-%d.%s" % (param.replace("_", "-"), stamp, n, ext), n + 1
    path = os.path.join(folder, name)
    tmp = os.path.join(folder, ".%s.tmp" % name)
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, path)
    bad = film.media_error(path, "image")
    if bad:
        os.remove(path)
        return 400, "Plik odrzucony: %s." % bad, {}
    old = next((str(p.get("value") or "") for p in info.get("params") or [] if p.get("name") == param), "")
    code, err, extra = _film_change3({"project": pid, "date": day, "params": {param: name}})
    if code != 200:
        os.remove(path)
        return code, err, {}
    _drop_old_image(folder, param, old, name)
    return 200, "", dict(extra, name=name)


POST_SECTIONS = ("Instagram", "Facebook", "LinkedIn", "TikTok", "Reels", "Alt")
POST_TEXT_MAX = 5000


def _section_span(lines, name):
    """(początek, koniec) treści sekcji „## name” w wierszach post.md albo None, gdy jej nie ma."""
    head = next((i for i, x in enumerate(lines) if x.startswith("## ") and x[3:].strip() == name), None)
    if head is None:
        return None
    end = next((j for j in range(head + 1, len(lines)) if lines[j].startswith("## ")), len(lines))
    return head + 1, end


def post_set_text(body):
    """POST /api/post/tekst {project, date, section, text, old}: opis jednej platformy w post.md (sekcja „## Nazwa”,
    ten sam podział, który czytają post_info, publikacja.py i udostepnij.caption). Brakującą sekcję dopisuje na końcu.
    old: tekst sekcji, od którego właściciel zaczął edycję; gdy plik zmienił się w międzyczasie (np. poprawił go
    agent), nic nie zapisuje i zwraca 409. (kod, błąd)."""
    folder = post_folder(str(body.get("project") or ""), str(body.get("date") or ""))
    if not folder:
        return 404, "Nie ma posta na ten dzień."
    name = str(body.get("section") or "")
    text = str(body.get("text") or "").replace("\r\n", "\n").strip()
    if name not in POST_SECTIONS:
        return 400, "Nieznana sekcja posta."
    if len(text) > POST_TEXT_MAX:
        return 400, "Opis: najwyżej %d znaków." % POST_TEXT_MAX
    if re.search(r"^## ", text, re.M):          # wiersz „## …” rozbiłby post.md na nowe sekcje
        return 400, "Wiersz opisu nie może zaczynać się od „## ”."
    path = os.path.join(folder, "post.md")
    with _write_lock:
        try:
            with open(path, encoding="utf-8") as f:
                lines = f.read().replace("\r\n", "\n").split("\n")
        except FileNotFoundError:
            lines = []
        except OSError:
            return 400, "Nie udało się odczytać post.md."
        span = _section_span(lines, name)
        cur = "\n".join(lines[span[0]:span[1]]).strip() if span else ""
        if "old" in body and cur != str(body.get("old") or "").replace("\r\n", "\n").strip():
            return 409, "Opis zmienił się w międzyczasie. Wczytuję nową wersję."
        new = text.split("\n") if text else []
        if span:
            lines[span[0]:span[1]] = new + [""]
        else:
            while lines and not lines[-1].strip():
                lines.pop()
            lines += ([""] if lines else []) + ["## " + name] + new + [""]
        try:
            projekt.write_atomic(path, "\n".join(lines))
        except OSError:
            return 400, "Nie udało się zapisać post.md."
    return 200, ""


def post_set_image(pid, day, ctype, data):
    """POST /api/post/grafika?project=&date=: nowa grafika posta (PNG albo JPG) jako grafika.png. Poprzednia zostaje
    w ukrytym .grafika-poprzednia.png. grafika.svg zostaje, ale jest starsza, więc post_image jej nie nadpisze.
    JPG zamienia na PNG ffmpeg (jest na serwerze z nagrywarką). (kod, błąd)."""
    folder = post_folder(pid, day)
    if not folder:
        return 404, "Nie ma posta na ten dzień."
    ext = STUDIO_TYPES["logo"].get(ctype)
    if not ext:
        return 400, "Grafika: plik PNG albo JPG."
    tmp = os.path.join(folder, ".grafika-wysylka." + ext)
    with open(tmp, "wb") as f:
        f.write(data)
    bad = film.media_error(tmp, "image")
    if bad:
        os.remove(tmp)
        return 400, "Plik odrzucony: %s." % bad
    out = tmp
    if ext != "png":
        out = os.path.join(folder, ".grafika-wysylka-png.png")
        ff = shutil.which("ffmpeg")
        try:
            if not ff:
                raise OSError("brak ffmpeg")
            subprocess.run([ff, "-y", "-loglevel", "error", "-i", tmp, "-frames:v", "1", out], check=True, timeout=60,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except (OSError, subprocess.SubprocessError):
            with contextlib.suppress(OSError):
                os.remove(out)
            return 400, "Nie udało się zamienić JPG na PNG. Wgraj grafikę PNG."
        finally:
            with contextlib.suppress(OSError):
                os.remove(tmp)
    png = os.path.join(folder, "grafika.png")
    with _write_lock:
        if os.path.isfile(png) and not os.path.islink(png):
            os.replace(png, os.path.join(folder, ".grafika-poprzednia.png"))
        os.replace(out, png)
    return 200, ""


def _drop_old_image(folder, param, old, new):
    """Poprzedni zrzut tego pola wgrany w panelu (<pole>-RRRRMMDD-HHMMSS[-n].png|jpg w folderze posta) znika po
    wgraniu nowego, jeśli scenariusz już go nie używa w innym polu (folder posta nie rośnie przy każdej poprawce)."""
    if not old or old == new or not re.match(r"^%s-\d{8}-\d{6}(?:-\d+)?\.(?:png|jpe?g)$"
                                              % re.escape(param.replace("_", "-")), old):
        return
    try:
        raw = film._load_json(os.path.join(folder, film.SCENARIO))
    except (OSError, ValueError):
        return
    used = (raw.get("parametry") or {}).values() if isinstance(raw, dict) and isinstance(raw.get("parametry"), dict) \
        else ()
    if old in [str(v) for v in used]:
        return
    path = os.path.join(folder, old)
    if os.path.isfile(path) and not os.path.islink(path):
        try:
            os.remove(path)
        except OSError:
            pass


def _film_change3(body):
    """film_change zawsze jako (kod, błąd, dane)."""
    res = film_change(body)
    return res[0], res[1], (res[2] if len(res) > 2 else {})


FILM_TASK = re.compile(r"^(?:nagra[jć]|obejrzyj)\s+film", re.I)    # „Obejrzyj film A”: film nagrywa panel


def film_link(task, tasks, index):
    """Folder posta, którego film robi zadanie „Nagraj film …” (jedno źródło dla panelu: sprawy dla Ciebie, Blokady, szuflada):
    materiał: w posty/<post>/ albo publikacja z kanałem, która czeka na to zadanie (po:), z postem na swój dzień.
    None: zadanie nie jest powiązane z postem."""
    if not FILM_TASK.match(task.get("title") or "") or task.get("channel"):
        return None
    card = index.get(task.get("project"))
    if not card:
        return None
    base = os.path.join(os.path.dirname(os.path.realpath(os.path.join(card, "KARTA.md"))), "posty")
    for r in (task.get("detail") or {}).get("refs") or []:
        m = re.match(r"^posty/([^/#]+)", str((r or {}).get("path") or "") if isinstance(r, dict) else str(r))
        if m and os.path.isdir(os.path.join(base, m.group(1))):
            return os.path.join(base, m.group(1))
    title = (task.get("title") or "").lower()
    for y in tasks:
        if y is task or y.get("project") != task.get("project") or y.get("kind") != "publikacja" \
                or not y.get("channel"):
            continue
        if any(str(a).strip() and title.startswith(str(a).strip().lower()) for a in y.get("after") or []):
            folder = post_folder(task["project"], str(resolve_date(y.get("date") or "") or "")[:10])
            if folder:
                return folder
    return None


def film_links(tasks, index):
    """Zadania „Nagraj film …” powiązane z postem: t["filmPost"] = {"day", "post", "scenario", "film", "state"}.
    film: film nagrany i nie starszy niż scenariusz posta (właściciel tylko go ogląda); do tego czasu film robi panel."""
    for t in tasks:
        folder = film_link(t, tasks, index)
        if not folder:
            continue
        fpath = publikacja.Publisher.film(folder)
        sv = film.scenario_version(folder) if fpath else None
        t["filmPost"] = {"day": post_day(folder), "post": os.path.basename(folder),
                         "scenario": os.path.isfile(os.path.join(folder, film.SCENARIO)),
                         "film": bool(fpath) and not (sv is not None and sv > os.path.getmtime(fpath)),
                         "state": film.read_state(folder).get("state", "")}


def film_refs(folder):
    """Materiał filmu posta dla agenta: scenariusz, użyty szablon studia i marka (ścieżki względem karty)."""
    if not os.path.isfile(os.path.join(folder, film.SCENARIO)):
        return []
    out = ["posty/%s/%s" % (os.path.basename(folder), film.SCENARIO)]
    studio = film.studio_dir(folder)
    name = film.describe(folder).get("template")
    if name and film.NAME_RE.match(name) and os.path.isfile(os.path.join(studio, film.TEMPLATES, name + ".json")):
        out.append("%s/%s/%s.json" % (film.STUDIO, film.TEMPLATES, name))
    if os.path.isfile(os.path.join(studio, film.BRAND)):
        out.append("%s/%s" % (film.STUDIO, film.BRAND))
    return out


def studio_summary(index):
    """Studio filmów projektów (folder studio/ obok KARTA.md): {projekt: {"templates": [{"name", "kind", "kindLabel",
    "desc", "params", "labels", "error", "uses"}], "brand": {"name", "errors", "colors", "intro", "outro", "sites"}
    albo None}}. "uses": dni postów (posty/<dzień>-…/scenariusz.json) z tym szablonem. Projekty bez studia pominięte."""
    out = {}
    for pid, folder in sorted(index.items()):
        card = os.path.dirname(os.path.realpath(os.path.join(folder, "KARTA.md")))
        studio = os.path.join(card, film.STUDIO)
        if not os.path.isdir(studio):
            continue
        brand, errors, exists = film.load_brand(studio)
        uses = {}
        try:
            posts = sorted(os.listdir(os.path.join(card, "posty")))
        except OSError:
            posts = []
        for n in posts:
            try:
                with open(os.path.join(card, "posty", n, film.SCENARIO), encoding="utf-8") as f:
                    raw = json.load(f)
            except (OSError, ValueError):
                continue
            name = raw.get("szablon") if isinstance(raw, dict) else None
            if isinstance(name, str) and POST_DAY.match(n[:10]):
                uses.setdefault(name, []).append(n[:10])
        templates = film.list_templates(studio)
        today = datetime.date.today().isoformat()
        names = {t["name"] for t in templates}
        for name, days in uses.items():          # posty ze scenariuszem wskazującym szablon, którego już nie ma
            if name not in names and any(d >= today for d in days):
                templates.append({"name": name, "title": name, "kind": "pokaz", "kindLabel": film.KINDS["pokaz"],
                                  "desc": "", "forOwner": "", "params": [], "labels": {}, "required": [],
                                  "error": "brak pliku studio/szablony/%s.json" % name})
        for t in templates:
            t["uses"] = uses.get(t["name"], [])
            # nadchodzące posty z tym szablonem, których scenariusz się nie nagra (np. po zmianie szablonu)
            t["broken"] = [n[:10] for n in posts if n[:10] in t["uses"] and n[:10] >= today
                           and film.describe(os.path.join(card, "posty", n))["error"]]
            t["sample"] = ""                    # ostatni post z nagranym filmem z tego szablonu (przykład w studiu)
            for n in reversed(posts):
                if n[:10] in t["uses"] and publikacja.Publisher.film(os.path.join(card, "posty", n)):
                    t["sample"] = n[:10]
                    break

        def card_of(key):
            c = brand.get(key) or None
            return {"title": c.get("tytul", ""), "subtitle": c.get("podtytul", ""), "address": c.get("adres", ""),
                    "seconds": film.brand_time(c, key)[0], "bg": c.get("tlo") or brand["kolory"]["tekst"],
                    "fg": c.get("kolor") or brand["kolory"]["tlo"]} if c else None
        out[pid] = {"templates": templates,
                    "brand": {"name": brand.get("nazwa") or "", "errors": errors[:3],
                              "colors": dict(brand["kolory"]) if not errors else {},
                              "intro": card_of("plansza_startowa") if not errors else None,
                              "outro": card_of("plansza_koncowa") if not errors else None,
                              "sites": list(brand.get("strony") or []),
                              "music": bool(brand.get("muzyka")) and not errors,
                              "musicCount": len(film.music_list(brand.get("muzyka"))) if not errors else 0,
                              "songs": [{"name": m, "source": _song_source(brand.get("zrodlo"), m)}
                                        for m in film.music_list(brand.get("muzyka"))] if not errors else [],
                              "logo": bool(brand.get("logo")) and not errors,
                              "logoCorner": bool(brand.get("logo_w_rogu")) and bool(brand.get("logo")) and not errors,
                              "caption": {"color": (brand.get("napisy") or {}).get("kolor", ""),
                                          "bg": (brand.get("napisy") or {}).get("tlo", "")} if not errors else None,
                              # kroje z marki (nazwy, bez grubości po „:”): podgląd plansz w panelu tymi krojami
                              "fonts": {k: str(v).partition(":")[0] for k, v in (brand.get("czcionki") or {}).items()
                                        if v} if not errors else {},
                              "gaps": [str(x) for x in brand.get("braki") or []] if not errors else [],
                              "pending": [{"card": film.CARD_NAMES.get(k, k), "what": str(v)}
                                          for k, v in (brand.get("do_potwierdzenia") or {}).items()]
                              if not errors else [],
                              "hidden": len(brand.get("ukryj") or []) if not errors else 0,
                              "warnings": _brand_warnings(studio)}
                    if exists else None}
    return out


def _brand_warnings(studio):
    """Ostrzeżenia marka.json (nieznane klucze: pomijane, filmy się nagrywają)."""
    try:
        return film.brand_warnings(film._load_json(os.path.join(studio, film.BRAND)))[:3]
    except (OSError, ValueError):
        return []


def _song_source(zrodlo, name):
    """Licencja podkładu z „zrodlo” marki (wpis panelu: „muzyka <plik>: <skąd i licencja>”) albo ""."""
    m = re.search(r"muzyka %s: ([^;]{1,200})" % re.escape(name), str(zrodlo or ""))
    return m.group(1).strip() if m else ""


def auto_record():
    """Co minutę: post ze scenariuszem bez filmu albo ze scenariuszem nowszym niż film → nagranie (raz na wersję).
    Jedno nagranie naraz: gdy coś się nagrywa, reszta czeka w kolejce (od najstarszego scenariusza)."""
    rec = get_recorder()
    pokaz = rec.available()
    if not (pokaz or rec.available("objasnienie")):      # objaśnienia nagrywa się z samym ffmpeg
        return
    with rec.lock:
        if rec.busy:
            return
    data, index = load_projects(resolve=False)
    published = published_days(data["tasks"])
    with rec.lock:
        busy = set(os.path.realpath(b) for b in rec.busy)
    now = datetime.datetime.now()
    for _pid, _n, pf in _post_dirs(index):
        st = film.read_state(pf)
        if os.path.realpath(pf) in busy:
            continue
        # za długo albo osierocone na tym hoście (proces nie żyje, po FILM_GRACE s): od razu błąd, żeby kolejka
        # nie stała do film.TIMEOUT + 60 s, a stan w panelu („przerwane”) zgadzał się z kolejką
        err = FILM_STALE if film_stale(st, now) else FILM_ORPHAN if film_orphan(st, now) else ""
        if err:
            keep = {"scenario": st["scenario"]} if "scenario" in st else {}
            try:
                film.write_state(pf, state="error", error=err, **keep)
            except OSError:
                pass
    for _pid, n, pf, mt in film_queue(index, published=published):
        try:
            if not pokaz and film.describe(pf)["kind"] == "pokaz":     # pokaz czeka na maszynę z Playwright
                continue
            film.write_state(pf, state="queued", scenario=mt)
            res = rec.start(pf, n)
        except Exception as e:  # noqa: BLE001
            res = (500, "%s: %s" % (type(e).__name__, e))
        # start nie ruszył (np. wyścig z dostępnością nagrywarki): stan „queued” ze scenario tej wersji zniknąłby
        # z panelu bez śladu; zapisujemy błąd (scenario zostaje: tej wersji Automat nie powtarza w kółko,
        # „Nagraj ponownie” w panelu tak)
        if res and res[0] >= 400:
            st = film.read_state(pf)
            if st.get("state") == "queued":
                try:
                    film.write_state(pf, state="error", error="nagranie nie ruszyło: %s" % str(res[1])[:200],
                                     scenario=mt)
                except OSError:
                    pass
        with _films_lock:
            _films_cache["at"] = 0.0
        return


def film_orphan(st, now=None):
    """„running” tego hosta, którego nie nagrywa żywy proces (nie inny żywy PID; wołający sprawdza, że ten proces
    go nie nagrywa), starsze niż FILM_GRACE s: nagranie przerwane."""
    if st.get("state") != "running" or not st.get("host") or film_elsewhere(st):
        return False          # bez host (stan sprzed tej wersji) nie wiadomo, czyj to proces: zostaje film_stale
    at = _iso(st.get("at"))
    now = now or datetime.datetime.now()
    return at is not None and now - at > datetime.timedelta(seconds=FILM_GRACE)


_auto_rec = {"error": "", "logged": None}


def auto_record_loop():
    """Automat nagrań co minutę. Błąd jest logowany (raz na zmianę treści) i widoczny w Teraz (activity.error),
    a nie połykany po cichu."""
    while True:
        time.sleep(60)
        try:
            auto_record()
            _auto_rec["error"] = ""
        except Exception as e:  # noqa: BLE001
            msg = "%s: %s" % (type(e).__name__, e)
            _auto_rec["error"] = msg[:200]
            if msg != _auto_rec["logged"]:
                _auto_rec["logged"] = msg
                import traceback
                print("auto_record:", file=sys.stderr)
                traceback.print_exception(type(e), e, e.__traceback__)


def get_publisher():
    """Publikacja postów (publikacja.py); jedna na proces."""
    global _publisher
    with _agents_lock:
        if _publisher is None:
            _publisher = publikacja.Publisher(load_projects, _write_lock, projekt, post_folder, post_info, post_image,
                                              notify=lambda text, link="#marketing": get_agents()._send_ntfy(text, link))
        return _publisher


# kanał zadania (pole kanał) → platforma pakietu udostępnienia; skróty jak CHAL w panel.html
SHARE_CHANNELS = {"instagram": r"instagram|insta|\big\b", "facebook": r"facebook|\bfb\b|reels|rolki",
                  "linkedin": r"linkedin|\bli\b", "tiktok": r"tiktok|\btt\b"}


def post_share(body):
    """POST /api/udostepnij {id, title, platforma}: pakiet posta dla rozszerzenia Chrome (udostepnij.py).
    (kod, błąd, {path, token, url, platform, handle, files, warning}). Publikuje właściciel na stronie platformy."""
    platform = str(body.get("platforma") or "instagram").lower()
    if platform not in udostepnij.PLATFORMS:
        return 400, "Nieznana platforma: %s." % platform[:30]
    name = udostepnij.PLATFORMS[platform]["name"]
    t, data, folder = _find_task(body.get("id", ""), body.get("title", ""))
    if t is None:
        return folder
    channel = str(t.get("channel") or "").lower()
    if t.get("kind") != "publikacja" or not re.search(SHARE_CHANNELS[platform], channel):
        return 400, "To nie jest publikacja z kanałem %s." % name
    pf = post_folder(t["project"], str(t.get("date") or "")[:10])
    if not pf:
        return 404, "Nie ma przygotowanego posta na dzień publikacji."
    info = post_info(pf)
    film = publikacja.Publisher.film(pf)
    files = udostepnij.media(pf, film, post_image(pf) if info.get("image") else None, platform)
    if not files and udostepnij.PLATFORMS[platform]["media"]:
        return 409, ("Post nie ma filmu. TikTok wymaga filmu." if platform == "tiktok" else
                     "Post nie ma grafiki, zdjęć ani filmu. %s wymaga zdjęcia albo filmu." % name)
    proj = next((p for p in data.get("projects") or [] if p.get("id") == t["project"]), {})
    handle = str(proj.get(platform) or "")
    text = udostepnij.caption(info, platform)
    token = SHARES.create(t["title"], text, files, handle, platform)
    warning = "" if handle else ("Karta projektu nie ma pola %s: (profil albo strona), więc rozszerzenie nie "
                                 "sprawdzi, czy wybrane jest właściwe konto." % platform)
    url = udostepnij.compose_url(platform, bool(film), bool(re.search(r"reels|rolki", channel)), text)
    return 200, "", {"path": "/udostepnij/" + token, "token": token, "url": url, "platform": platform,
                     "handle": handle, "files": len(files), "warning": warning}


def instagram_share(body):
    """POST /api/instagram/udostepnij {id, title}: dawna trasa, to samo co /api/udostepnij z platformą instagram."""
    return post_share(dict(body, platforma="instagram"))


def _post_project_name(pid):
    data, _ = load_projects(resolve=False)
    p = next((x for x in data["projects"] if x["id"] == pid), {})
    return p.get("alias") or p.get("name") or pid


def graphic_state(pid, day):
    """GET /api/post/warianty: warianty, obrazy do wyboru, zlecenia Codex i stan Codexa dla edytora posta."""
    folder = post_folder(pid, day)
    if not folder:
        return 404, "Nie ma posta na ten dzień.", {}
    names = grafiki.variants(folder)
    out = {"folder": os.path.basename(folder), "variants": [{"name": n, "at": int(os.path.getmtime(os.path.join(folder, n)))}
                                                             for n in names],
           "inputs": [{"name": n, "at": int(os.path.getmtime(os.path.join(folder, n)))} for n in grafiki.inputs(folder)],
           "image": os.path.isfile(os.path.join(folder, "grafika.png")),
           "photos": udostepnij.photos(folder), "max": grafiki.INPUTS_MAX}
    m = get_agents()
    m.refresh_tools()
    try:
        grafiki.chat_settle(folder, m.graphic_live)
    except OSError as e:
        print("rozmowa o grafice: %s" % e, file=sys.stderr)
    out.update(tool=m.graphic_tool(), runs=m.graphic_runs(pid, day), chat=grafiki.chat_public(folder))
    return 200, "", out


def graphic_order(body):
    """POST /api/post/grafika-codex {project, date, polecenie, tryb: zachowaj | nowa, zrodlo: grafika.png | zdjęcie}:
    polecenie w rozmowie o grafice. Przy oczekującej wersji Codex poprawia ją (zrodlo bez znaczenia)."""
    pid, day = str(body.get("project") or ""), str(body.get("date") or "")
    folder = post_folder(pid, day)
    if not folder:
        return 404, "Nie ma posta na ten dzień."
    post_image(folder)                       # grafika.svg → grafika.png, żeby było co poprawiać
    return get_agents().run_graphic(pid, day, folder, body.get("polecenie", ""), str(body.get("tryb") or "zachowaj"),
                                    str(body.get("zrodlo") or ""), _post_project_name(pid))


def graphic_variant(body):
    """POST /api/post/wariant {project, date, name, akcja}: oczekująca wersja z rozmowy: akceptuj | odrzuc | karuzela;
    dowolny wariant: grafika | usun."""
    folder = post_folder(str(body.get("project") or ""), str(body.get("date") or ""))
    if not folder:
        return 404, "Nie ma posta na ten dzień."
    do = {"akceptuj": grafiki.accept, "odrzuc": grafiki.reject, "karuzela": grafiki.to_carousel,
          "grafika": grafiki.use_as_graphic, "usun": grafiki.remove}.get(str(body.get("akcja") or ""))
    if not do:
        return 400, "Nieznana akcja."
    with _write_lock:
        try:
            return do(folder, str(body.get("name") or ""))
        except OSError as e:
            return 500, "Nie zapisano zmiany: %s." % (e.strerror or e)


def get_agents():
    """Jeden zarządca uruchomień na proces; powstaje przy pierwszym użyciu (eksport podglądu go nie potrzebuje)."""
    global _agents
    with _agents_lock:
        if _agents is None:
            _agents = agents.Manager(load_projects, _write_lock, projekt)
            _agents.site.secret = _derive("panel-podglad").encode("ascii")   # adresy podglądu trwają po restarcie
            _agents.counts_hook = cached_counts
            _agents.answer_hook = answer_question    # „Odpowiedź na pytanie:” z rozmów: ta sama droga co przycisk
        return _agents


_fields = None
_fields_lock = threading.Lock()


def get_fields():
    """Propozycje pól formularza zadań właściciela (pola.py); model przez zarządcę agentów."""
    global _fields
    with _fields_lock:
        if _fields is None:
            m = get_agents()
            _fields = pola.Fields(m.runs_dir, lambda: load_projects(resolve=False),
                                  lambda pid: load_projects(resolve=False)[1].get(pid), m.ask_fields, _write_lock)
        return _fields


def cached_counts():
    """Liczby spraw z ostatniej odpowiedzi /api/data (te same, które widzi panel) albo None, gdy jeszcze jej nie ma."""
    with _data_lock:
        body = _data_cache["body"]
    try:
        d = json.loads(body) if body else None
    except ValueError:
        d = None
    return {k: d[k] for k in projekt.OWNER_COUNT_KEYS if k in d} if isinstance(d, dict) else None


# Wiadomość w rozmowie: 2000 znaków w JSON z \uXXXX (np. polskie litery, emoji) przekracza 4 KB.
CHAT_BODY = 32 * 1024
WRITES = {"/api/task/state": lambda b: change_task(b), "/api/task/update": lambda b: update_task(b),
          "/api/task/count": lambda b: count_task(b),
          "/api/task/close-checked": lambda b: close_checked(b),
          "/api/task/detail": lambda b: update_detail(b),
          "/api/task/finish": lambda b: finish_task(b), "/api/task/pola": lambda b: task_fields(b),
          "/api/task/add": lambda b: add_task(b), "/api/stage/update": lambda b: update_stage(b),
          "/api/campaign/update": lambda b: update_campaign(b),
          "/api/project/add": lambda b: add_project(b), "/api/project/remove": lambda b: remove_project(b),
          "/api/project/meta": lambda b: update_meta(b),
          "/api/github/stan": lambda b: github_state(b), "/api/github/wyslij": lambda b: github_push(b),
          "/api/github/usun-kopie": lambda b: github_remove(b),
          "/api/repo/zatwierdz": lambda b: repo_change(b, "commit"),
          "/api/repo/odloz": lambda b: repo_change(b, "stash"),
          "/api/repo/przywroc": lambda b: repo_change(b, "restore"),
          "/api/agent/rownolegle": lambda b: get_agents().set_parallel(b.get("value")),
          "/api/agent/run": lambda b: get_agents().run_task(b.get("id", ""), b.get("title", "")),
          "/api/strona/zbuduj": lambda b: get_agents().site.build_api(b.get("project", "")),
          "/api/strona/uwaga": lambda b: get_agents().site.add_note(b),
          "/api/strona/koncepcja": lambda b: get_agents().site.concept(b),
          "/api/odbior/popraw": lambda b: get_agents().review_fix(b.get("id", ""), b.get("title", ""), b.get("text", ""),
                                                                  b.get("pins")),
          "/api/odbior/akceptuj": lambda b: get_agents().review_accept(b.get("id", ""), b.get("title", ""),
                                                                       b.get("variants")),
          "/api/drive/start": lambda b: get_drive().start(b.get("project", ""), b.get("link", "")),
          "/api/drive/finish": lambda b: get_drive().finish(b.get("project", ""), b.get("url", "")),
          "/api/drive/montuj": lambda b: get_drive().mount(b.get("project", "")),
          "/api/drive/anuluj": lambda b: get_drive().cancel(b.get("project", "")),
          "/api/drive/odlacz": lambda b: get_drive().disconnect(b.get("project", "")),
          "/api/post/zlec": lambda b: assign_publication(b),
          "/api/drive/klient": lambda b: get_drive().save_client(b),
          "/api/drive/konto/start": lambda b: get_drive().start_account(b.get("label", ""),
                                                                         b.get("account", ""), b.get("returnTo", "")),
          "/api/drive/konto/finish": lambda b: get_drive().finish_account(b.get("url", "")),
          "/api/drive/konto/anuluj": lambda b: get_drive().cancel_account(),
          "/api/drive/konto/usun": lambda b: get_drive().remove_account(b.get("account", "")),
          "/api/drive/wybierz": lambda b: get_drive().choose(b.get("project", ""), b.get("account", ""),
                                                             b.get("folder", ""), b.get("path", "")),
          "/api/project/chat": lambda b: get_agents().project_chat_send(
              b.get("project", ""), b.get("message", ""), str(b.get("task") or ""), b.get("execute") is True,
              b.get("attach") if isinstance(b.get("attach"), dict) else None),
          "/api/asystent": lambda b: get_agents().assistant_send(b.get("message", ""), b.get("view", ""),
                                                                 b.get("open", "")),
          "/api/asystent/nowa": lambda b: get_agents().assistant_reset(),
          "/api/asystent/karty": lambda b: get_agents().assistant_cards_post(b),
          "/api/asystent/glos/start": lambda b: get_agents().voice_warm(),
          "/api/agent/pm": lambda b: get_agents().run_pm(),
          "/api/wdroz": lambda b: start_deploy(b),
          "/api/agent/limity": lambda b: get_agents().run_limits(),
          "/api/agent/check": lambda b: get_agents().run_check(b.get("tool", "claude")),
          "/api/agent/stop": lambda b: get_agents().stop(b.get("id", "")),
          "/api/agent/restart": lambda b: get_agents().restart_run(b.get("id", "")),
          "/api/film/nagraj": record_film,
          "/api/film/konto": film_account,
          "/api/post/popraw": fix_post,
          "/api/scenariusz/przygotuj": script_prepare,
          "/api/scenariusz/popraw": script_fix,
          "/api/scenariusz/tekst": script_text,
          "/api/scenariusz/stan": script_state,
          "/api/post/tekst": post_set_text,
          "/api/film/zmien": film_change,
          "/api/studio/popros": studio_request,
          "/api/studio/ustaw": studio_settings,
          "/api/studio/usun": studio_remove_music,
          "/api/publikacja/facebook": lambda b: get_publisher().connect_facebook(b),
          "/api/publikacja/linkedin": lambda b: get_publisher().connect_linkedin(b),
          "/api/publikacja/strona": lambda b: get_publisher().map_page(b),
          "/api/publikacja/odlacz": lambda b: get_publisher().disconnect(b),
          "/api/publikacja/plan": lambda b: get_publisher().plan(b),
          "/api/publikacja/anuluj": lambda b: get_publisher().cancel(b),
          "/api/instagram/udostepnij": instagram_share,
          "/api/udostepnij": post_share,
          "/api/post/grafika-codex": graphic_order,
          "/api/post/wariant": graphic_variant,
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
                try:
                    at = datetime.datetime.fromtimestamp(os.path.getmtime(files[-1])).isoformat(timespec="seconds")
                except OSError:
                    at = None
                return {"date": os.path.basename(files[-1])[:10], "text": text.strip()[:4000], "at": at}
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


# ---------- „Teraz” w Agentach: filmy, rozmowy o zadaniach, zamknięte zadania, zakończone uruchomienia ----------
ACTIVITY_TTL = 5                      # s: foldery postów czytane najwyżej co tyle (panel pyta co 3 s, gdy coś trwa)
RECENT_HOURS = 24                     # „Ostatnio zrobione”
CLOSED_KEEP = 100
# w podkatalogu katalogu uruchomień: Manager._load bierze *.json z katalogu głównego za rekordy uruchomień
CLOSED_FILE = os.path.join("teraz", "zamkniete.json")
CLOSED_OLD = "zamkniete.json"         # dawne miejsce pliku; przenoszony przy pierwszym odczycie
FILM_INTERRUPTED = "nagrywanie przerwane przy restarcie panelu"
FILM_STALE = "nagrywanie nie skończyło się w limicie czasu (proces przerwany)"
FILM_ORPHAN = "nagrywanie przerwane: proces nagrywarki nie działa"
FILM_GRACE = 60                       # s: świeże „running” bez procesu to zwykle chwila przed wpisaniem do busy
_films_cache = {"at": 0.0, "key": None, "value": [], "error": None}
_films_lock = threading.Lock()
_closed_lock = threading.Lock()
_closed_mem = {}                      # ścieżka pliku -> stan track_closed (readAt: ostatni odczyt, bez zapisu na dysk)


def _recent(at, now, hours=RECENT_HOURS):
    return at is not None and datetime.timedelta(0) <= now - at <= datetime.timedelta(hours=hours)


def _post_dirs(index, need=(film.STATE,)):
    """(projekt, nazwa folderu, ścieżka) folderów posty/<nazwa>/ z co najmniej jednym z plików `need`."""
    for pid, folder in sorted(index.items()):
        base = os.path.join(os.path.dirname(os.path.realpath(os.path.join(folder, "KARTA.md"))), "posty")
        try:
            names = sorted(os.listdir(base))
        except OSError:
            continue
        for n in names:
            pf = os.path.join(base, n)
            if any(os.path.isfile(os.path.join(pf, x)) for x in need):
                yield pid, n, pf


def _pid_alive(pid):
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except (PermissionError, OSError):
        return True
    return True


def film_elsewhere(st):
    """Nagranie „running” prowadzone przez inny proces: inny host albo inny żywy proces na tym hoście.
    Stan bez host/pid (sprzed tej wersji) traktujemy jak własny."""
    host, pid = st.get("host"), st.get("pid")
    if not host:
        return False
    if host != film.HOST:
        return True
    return pid != os.getpid() and _pid_alive(pid)


def film_stale(st, now=None):
    """„running” starszy niż film.TIMEOUT + 60 s: nagranie na pewno się skończyło (proces padł, PID przejął
    inny proces albo host nie odpowiada). Traktujemy jak przerwane, żeby nie wstrzymywało kolejki na zawsze."""
    if st.get("state") != "running":
        return False
    at = _iso(st.get("at"))
    now = now or datetime.datetime.now()
    return at is None or now - at > datetime.timedelta(seconds=film.TIMEOUT + 60)


def film_pending(pf, st=None, today=None, published=False):
    """Wersja filmu (film.version: najnowszy mtime scenariusza, szablonu, marki, muzyki, obrazów), gdy post czeka na
    automatyczne nagranie; None, gdy nie czeka. Te same warunki co w auto_record: film starszy niż ta wersja albo
    brak filmu, ta wersja jeszcze nie nagrywana. „running” starszy niż limit nagrania (film_stale) nie wstrzymuje
    kolejki.
    Zmiana samego studia (szablon, marka, muzyka, logo; scenariusz posta starszy niż film) nagrywa od nowa tylko
    posty z dniem od dziś, nieopublikowane i bez filmu wgranego ręcznie: archiwum ma zostać takie, jakie poszło do
    ludzi (studio_stale pokazuje w poście, że film jest starszy niż studio)."""
    mt = film.version(pf)
    if mt is None:
        return None
    fm = publikacja.Publisher.film(pf)
    st = film.read_state(pf) if st is None else st
    if (fm and os.path.getmtime(fm) >= mt) or (st.get("state") == "running" and not film_stale(st)) \
            or st.get("scenario") == mt:
        return None
    if fm and studio_stale(pf, fm) and (published or post_day(pf) < (today or datetime.date.today().isoformat())
                                        or os.path.exists(os.path.join(pf, film.MANUAL))):
        return None
    return mt


def post_day(pf):
    """Dzień posta z nazwy folderu posty/<RRRR-MM-DD>-…; "" gdy nazwa go nie ma."""
    n = os.path.basename(os.path.normpath(pf))[:10]
    return n if POST_DAY.match(n) else ""


def studio_stale(pf, fm=None):
    """Film starszy tylko przez studio: scenariusz i obrazy posta są starsze niż film, a szablon, marka, muzyka albo
    logo nowsze."""
    fm = fm or publikacja.Publisher.film(pf)
    if not fm:
        return False
    sv, v = film.scenario_version(pf), film.version(pf)
    t = os.path.getmtime(fm)
    return sv is not None and v is not None and sv <= t < v


def published_days(tasks):
    """{(projekt, dzień)} postów opublikowanych: publikacja z kampanii w stanie zrobione."""
    out = set()
    for t in tasks or []:
        if t.get("kind") == "publikacja" and t.get("state") == "done":
            day = str(resolve_date(t.get("date") or "") or "")[:10]
            if POST_DAY.match(day):
                out.add((t.get("project"), day))
    return out


def film_queue(index, today=None, published=None):
    """Posty czekające na automatyczne nagranie, najstarszy scenariusz najpierw: [(projekt, folder, ścieżka, mtime)].
    published: {(projekt, dzień)} opublikowanych postów (zmiana studia ich nie nagrywa)."""
    out = []
    published = published or set()
    for pid, n, pf in _post_dirs(index, (film.SCENARIO,)):
        try:
            mt = film_pending(pf, today=today, published=(pid, n[:10]) in published)
        except Exception as e:  # noqa: BLE001  (jeden uszkodzony post nie zatrzymuje kolejki pozostałych)
            _film_skip(pf, e)
            continue
        if mt is not None:
            out.append((pid, n, pf, mt))
    out.sort(key=lambda x: (x[3], x[2]))
    return out


_film_bad = {}


def _film_skip(pf, e):
    """Błąd jednego folderu posta: zapamiętany (film_activity pokazuje go jako pozycję „film: błąd”), w logu raz."""
    msg = "%s: %s" % (type(e).__name__, e)
    if _film_bad.get(pf) != msg:
        print("film (%s): %s" % (pf, msg), file=sys.stderr)
    _film_bad[pf] = msg


def _post_title(pf, n):
    text = projekt.read(os.path.join(pf, "post.md")) or ""
    for line in text.split("\n"):
        if line.startswith("# "):
            return projekt._clean(line[2:].strip() or n, 160)
    return projekt._clean(n, 160)


def film_activity(index, now=None, busy=(), queue=False, published=None):
    """Filmy z .film-stan.json folderów posty/: nagrywane teraz, czekające w kolejce Automatu nagrań oraz nagrane
    albo z błędem w ostatnich 24 h.

    „running” jest pokazywane, gdy nagrywa ten proces (busy) albo inny proces według host/pid w stanie
    (film_elsewhere, najwyżej film.TIMEOUT od startu). Osierocone „running” tego hosta (proces nie żyje, starsze niż
    FILM_GRACE s, z 24 h) pokazujemy jako błąd FILM_ORPHAN, żeby nie znikało bez śladu (stanu nie zmieniamy:
    zrobi to auto_record albo mark_interrupted_films).
    queue=True (nagrywarka dostępna): posty ze scenariuszem do nagrania jako „queued”, z pozycją w kolejce
    (auto_record nagrywa je po jednym, od najstarszego scenariusza).
    [{"project", "post", "day", "title", "state", "at", "error", "pos"}], najnowsze najpierw."""
    now = now or datetime.datetime.now()
    busy = set(os.path.realpath(b) for b in busy or ())
    out, seen = [], set()

    def bad(pid, n, pf, e):
        """Jeden folder z błędem odczytu: pozycja „film: błąd” zamiast pustej listy dla wszystkich projektów."""
        out.append({"project": pid, "post": n, "day": n[:10] if POST_DAY.match(n[:10]) else "", "title": n,
                    "state": "error", "at": now.isoformat(timespec="seconds"),
                    "error": ("nie odczytano stanu filmu (%s: %s)" % (type(e).__name__, e))[:200], "pos": 0})

    for pid, n, pf in _post_dirs(index):
        try:
            st = film.read_state(pf)
            state, at = st.get("state"), _iso(st.get("at"))
            err = str(st.get("error") or "")
            if state == "running":
                if os.path.realpath(pf) not in busy and not (
                        film_elsewhere(st) and at is not None
                        and now - at <= datetime.timedelta(seconds=film.TIMEOUT + 60)):
                    if film_elsewhere(st) or at is None or not _recent(at, now) or \
                            now - at <= datetime.timedelta(seconds=FILM_GRACE):
                        continue
                    state, err = "error", FILM_ORPHAN
            elif state not in ("done", "error") or not _recent(at, now):
                continue
            item = {"project": pid, "post": n, "day": n[:10] if POST_DAY.match(n[:10]) else "",
                    "title": _post_title(pf, n), "state": state,
                    "at": at.isoformat(timespec="seconds") if at else "",
                    "error": err[:200], "pos": 0}
        except Exception as e:  # noqa: BLE001
            bad(pid, n, pf, e)
            continue
        seen.add(pf)
        out.append(item)
    if queue:
        for i, (pid, n, pf, mt) in enumerate(film_queue(index, published=published)):
            try:
                at = datetime.datetime.fromtimestamp(mt).replace(microsecond=0).isoformat()
                out.append({"project": pid, "post": n, "day": n[:10] if POST_DAY.match(n[:10]) else "",
                            "title": _post_title(pf, n), "state": "queued", "at": at, "error": "", "pos": i + 1})
            except Exception as e:  # noqa: BLE001
                bad(pid, n, pf, e)
        # posty ze scenariuszem, których kolejka nie odczytała (film_pending rzucił wyjątek)
        names = {pf: (pid, n) for pid, n, pf in _post_dirs(index, (film.SCENARIO,))}
        for pf, msg in list(_film_bad.items()):
            if pf in names and pf not in seen:
                pid, n = names[pf]
                out.append({"project": pid, "post": n, "day": n[:10] if POST_DAY.match(n[:10]) else "", "title": n,
                            "state": "error", "at": now.isoformat(timespec="seconds"),
                            "error": ("nie odczytano scenariusza (%s)" % msg)[:200], "pos": 0})
    out.sort(key=lambda f: f["at"], reverse=True)
    return out


def mark_interrupted_films(index):
    """Przy starcie panelu: „running” i „queued” z poprzedniego procesu na tym hoście to przerwane nagrania
    (stan błędu, raz). Nagrań innego hosta albo żywego procesu (drugi panel, ręczne film.py) nie rusza.
    Pole scenario zostaje, więc auto_record nie nagrywa tej wersji scenariusza sam drugi raz."""
    n = 0
    for _pid, _n, pf in _post_dirs(index):
        st = film.read_state(pf)
        if st.get("state") in ("running", "queued") and not film_elsewhere(st):
            keep = {"scenario": st["scenario"]} if "scenario" in st else {}
            try:
                film.write_state(pf, state="error", error=FILM_INTERRUPTED, **keep)
                n += 1
            except OSError:
                pass
    return n


def films_cached(index, busy=(), queue=False, published=None):
    """film_activity najwyżej co ACTIVITY_TTL s; zmiana rejestru albo nagrywanych folderów odświeża od razu."""
    key = (tuple(sorted(index.items())), tuple(sorted(busy)), bool(queue), tuple(sorted(published or ())))
    with _films_lock:
        if _films_cache["key"] != key or time.time() - _films_cache["at"] >= ACTIVITY_TTL:
            _film_bad.clear()
            try:
                value, err = film_activity(index, busy=busy, queue=queue, published=published), None
            except Exception as e:  # noqa: BLE001  (np. rejestr projektów zmienił się w trakcie skanu)
                value, err = [], "%s: %s" % (type(e).__name__, e)
            _films_cache.update(value=value, key=key, at=time.time(), error=err)
        if _films_cache.get("error") is not None:
            # nowy wyjątek z zapamiętanego tekstu (ponowne podnoszenie tego samego obiektu wydłuża jego ślad)
            raise RuntimeError(_films_cache["error"])
        return _films_cache["value"]


def track_closed(tasks, prev, now=None, when=None):
    """Zadania zamknięte między odczytami: otwarte w poprzednim odczycie, teraz [x].

    prev: {"open": [klucz projekt|plik|tytuł], "closed": [{"project", "file", "title", "at", "how"}], "readAt"}
    z poprzedniego odczytu (pierwsze wywołanie bez "open" niczego nie uznaje za zamknięte).
    Zadania o tym samym kluczu (ten sam tytuł w jednym pliku) liczą się osobno: zamknięcie jednego z dwóch
    jest wykryte, gdy otwartych z tym kluczem jest mniej niż poprzednio.
    Czas zamknięcia: when(zadanie) -> [(czas, źródło)] kandydatów (koniec uruchomienia agenta "run", zmiana
    pliku zadań "file"); pierwszy, który mieści się między poprzednim odczytem (readAt) a teraz. Bez takiego
    czasu: chwila wykrycia, "how": "seen" (panel pisze wtedy „zauważone”, nie „zamknięte o”).
    Zadanie otwarte ponownie (jest otwarte i żadne o tym kluczu nie jest [x]) znika z "closed".
    Zamknięcie razem ze zmianą tytułu w jednym zapisie nie jest wykrywane (inny klucz).
    Zwraca nowy stan; "closed" z 48 h, najwyżej CLOSED_KEEP, jedno na zadanie (ostatnie zamknięcie)."""
    now = now or datetime.datetime.now()
    prev = prev if isinstance(prev, dict) else {}
    closed = [c for c in prev.get("closed") or [] if isinstance(c, dict) and all(isinstance(c.get(k), str)
              for k in ("project", "file", "title", "at")) and _recent(_iso(c["at"]), now, 48)]
    open_now = collections.Counter(projekt.task_key(t) for t in tasks if t.get("state") != "done")
    done_now = set(projekt.task_key(t) for t in tasks if t.get("state") == "done")
    closed = [c for c in closed if not (open_now[projekt.task_key(c)] and projekt.task_key(c) not in done_now)]
    if isinstance(prev.get("open"), list):
        was = collections.Counter(k for k in prev["open"] if isinstance(k, str))
        low = _iso(prev.get("readAt")) if isinstance(prev.get("readAt"), str) else None
        seen = set()
        for t in tasks:
            k = projekt.task_key(t)
            if t.get("state") != "done" or k in seen or open_now[k] >= was[k]:
                continue
            seen.add(k)
            at, how = now, "seen"
            for cand, src in (when(t) if when else []):
                if cand is not None and cand <= now and (low is None or cand >= low):
                    at, how = cand, src
                    break
            closed = [c for c in closed if projekt.task_key(c) != k]
            closed.append({"project": t["project"], "file": t["file"], "title": t["title"],
                           "at": at.isoformat(timespec="seconds"), "how": how})
        closed.sort(key=lambda c: c["at"])
    return {"open": sorted(open_now.elements()), "closed": closed[-CLOSED_KEEP:],
            "readAt": now.isoformat(timespec="seconds")}


def closed_recent(tasks, runs_dir, now=None, when=None):
    """track_closed ze stanem w pamięci procesu i w <katalog uruchomień>/teraz/zamkniete.json; zwraca zamknięte
    w ostatnich 24 h. readAt (dolna granica czasu zamknięcia) to ostatni odczyt w tym procesie; plik zapisuje się
    tylko wtedy, gdy zmienił się zbiór otwartych albo zamkniętych (po restarcie readAt to ostatni zapis pliku).
    Zapis z wnętrza GET /api/data jest bezpieczny w jednym procesie (budowę szereguje _data_build_lock, najwyżej raz
    na DATA_TTL). Dwa panele na jednym katalogu uruchomień (np. Mac i serwer ze wspólnym szkice/) nie mają blokady
    między procesami: ostatni zapis wygrywa, więc każdy host powinien mieć własny PANEL_RUNS_DIR. Lista nie jest
    pełnym dziennikiem: zamknięcie ze zmianą tytułu w jednym zapisie nie jest wykrywane."""
    now = now or datetime.datetime.now()
    path = os.path.join(runs_dir, CLOSED_FILE)
    with _closed_lock:
        prev = _closed_mem.get(path)
        if prev is None:
            old = os.path.join(runs_dir, CLOSED_OLD)
            if not os.path.exists(path) and os.path.isfile(old):
                try:
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    os.replace(old, path)
                except OSError:
                    pass
            prev = load_json(path, {})
        new = track_closed(tasks, prev, now, when)
        _closed_mem[path] = new
        if {k: v for k, v in new.items() if k != "readAt"} != {k: v for k, v in prev.items() if k != "readAt"}:
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path + ".tmp", "w", encoding="utf-8") as f:
                    json.dump(new, f, ensure_ascii=False)
                os.replace(path + ".tmp", path)
            except OSError:
                pass
    return [c for c in reversed(new["closed"]) if _recent(_iso(c["at"]), now)]


def close_times(index, runs):
    """Kandydaci na czas zamknięcia zadania dla track_closed: koniec ostatniego uruchomienia agenta dla tego
    zadania, potem czas zmiany pliku zadań."""
    ended = {}
    for r in runs:
        if r.get("kind") == "task" and r.get("endedAt") and r.get("state") == "done":
            k = "%s|%s|%s" % (r.get("project", ""), r.get("file", ""), r.get("title", ""))
            ended[k] = max(ended.get(k, ""), str(r["endedAt"]))

    def when(t):
        out = []
        e = _iso(ended.get(projekt.task_key(t)))
        if e is not None:
            out.append((e, "run"))
        folder = index.get(t.get("project"))
        if folder:
            try:
                out.append((datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(folder, t["file"])))
                            .replace(microsecond=0), "file"))
            except (OSError, KeyError, ValueError):
                pass
        return out
    return when


def note_closed(project, file, title, runs_dir=None, now=None):
    """Zamknięcie zapisane w chwili zmiany stanu przez panel (zmiana stanu, zamknięcie po kontroli): dokładny czas,
    "how": "set". Klucz znika z "open", więc następny odczyt (track_closed) nie doda go drugi raz z gorszym czasem.
    Edycje ręczne w pliku nadal wykrywa track_closed z różnicy odczytów."""
    now = now or datetime.datetime.now()
    try:
        runs_dir = runs_dir or get_agents().runs_dir
    except Exception:  # noqa: BLE001
        return
    path = os.path.join(runs_dir, CLOSED_FILE)
    key = "%s|%s|%s" % (project, file, title)
    with _closed_lock:
        prev = _closed_mem.get(path)
        if prev is None:
            prev = load_json(path, {})
        prev = dict(prev) if isinstance(prev, dict) else {}
        closed = [c for c in prev.get("closed") or [] if isinstance(c, dict) and projekt.task_key(c) != key]
        closed.append({"project": project, "file": file, "title": title,
                       "at": now.isoformat(timespec="seconds"), "how": "set"})
        prev["closed"] = sorted(closed, key=lambda c: str(c.get("at", "")))[-CLOSED_KEEP:]
        if isinstance(prev.get("open"), list) and key in prev["open"]:
            o = list(prev["open"])
            o.remove(key)
            prev["open"] = o
        _closed_mem[path] = prev
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path + ".tmp", "w", encoding="utf-8") as f:
                json.dump(prev, f, ensure_ascii=False)
            os.replace(path + ".tmp", path)
        except OSError:
            pass


_activity_log = {"last": None}


def activity(out, index, manager):
    """Blok "activity" w /api/data: to, czego panel nie ma w innych polach (uruchomienia w toku, publikacje
    i Automat są). "runs": zakończone uruchomienia z 24 h, których nie ma w agents.runs (tam tylko ostatnie 40).
    Kolejka nagrań jest liczona zawsze (szkice/ mogą być wspólne z serwerem); "recorder": czy ten host ma nagrywarkę
    (bez niej panel pisze „nagra serwer”). Każde źródło osobno: błąd w jednym (np. skan filmów) zostawia pozostałe,
    "error" nazywa źródła z błędem. Ślad błędu w logu raz na zmianę treści (panel pyta co 3 s)."""
    empty = {"films": [], "chats": [], "chatsDone": [], "closed": [], "runs": [], "recorder": False}
    if out["projectsSource"] != "registry":
        return empty
    res, errs = dict(empty), []

    def part(label, fn, default=None):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            errs.append((label, e))
            return default

    recent = part("uruchomienia", lambda: manager.recent_runs(RECENT_HOURS), [])
    rec = part("nagrywarka", get_recorder)
    busy = set()
    if rec is not None:
        with rec.lock:
            busy = set(rec.busy)
        res["recorder"] = bool(part("nagrywarka", rec.available, False))
    res["films"] = part("filmy", lambda: films_cached(index, busy, queue=True,
                                                      published=published_days(out["tasks"])), [])
    res["chats"] = part("rozmowy", manager.chat_pending, [])
    done = getattr(manager, "chat_recent", None)
    res["chatsDone"] = part("rozmowy", lambda: done(RECENT_HOURS), []) if done else []
    res["closed"] = part("zamknięte zadania", lambda: closed_recent(out["tasks"], manager.runs_dir,
                                                                    when=close_times(index, recent)), [])
    shown = set(r.get("id") for r in ((out.get("agents") or {}).get("runs") or []) if isinstance(r, dict))
    res["runs"] = [r for r in recent if isinstance(r, dict) and r.get("id") not in shown]
    sig = "; ".join("%s: %s %s" % (lab, type(e).__name__, e) for lab, e in errs) or None
    if sig != _activity_log["last"]:
        _activity_log["last"] = sig
        if errs:
            import traceback
            for lab, e in errs:
                print("activity (%s):" % lab, file=sys.stderr)
                traceback.print_exception(type(e), e, e.__traceback__)
    if errs:
        res["error"] = "Nie odczytano: %s (%s)." % (", ".join(lab for lab, _ in errs),
                                                    ", ".join(sorted(set(type(e).__name__ for _, e in errs))))
    if _auto_rec["error"]:
        res["error"] = ((res.get("error") or "") + " Automat nagrań: błąd (%s)." % _auto_rec["error"]).strip()
    return res


DATA_TTL = 1.5                        # s: /api/data z pamięci (panel pyta co 3 s z kilku urządzeń, gdy coś trwa)
_data_lock = threading.Lock()
_data_cache = {"at": 0.0, "body": None, "gen": 0}
_data_build_lock = threading.Lock()


def data_cached(ttl=None):
    """/api/data jako tekst JSON; ta sama odpowiedź najwyżej przez DATA_TTL s. Każdy zapis (POST) unieważnia ją
    (data_invalidate), więc po zmianie panel dostaje świeże dane od razu."""
    ttl = DATA_TTL if ttl is None else ttl
    with _data_lock:
        if _data_cache["body"] is not None and time.time() - _data_cache["at"] < ttl:
            return _data_cache["body"]
    # kilka urządzeń naraz po wygaśnięciu: buduje jedno żądanie, reszta czeka i bierze jego wynik
    with _data_build_lock:
        with _data_lock:
            if _data_cache["body"] is not None and time.time() - _data_cache["at"] < ttl:
                return _data_cache["body"]
            gen = _data_cache.get("gen", 0)
        try:
            body = json.dumps(build_data(), ensure_ascii=False)
        except Exception as e:  # noqa: BLE001
            # błąd budowy: ostatnia dobra odpowiedź (przez ttl, żeby czekające żądania nie budowały od nowa po kolei)
            # ze znacznikiem "stale" (panel ostrzega, że dane są sprzed błędu); bez niej błąd idzie dalej (500)
            log_once("data", "build_data", e)
            with _data_lock:
                last = _data_cache.get("last")
                if last is None:
                    raise
                body = stale_body(last, e)
                _data_cache.update(at=time.time(), body=body)
            return body
        with _data_lock:
            if _data_cache.get("gen", 0) == gen:          # zapis w trakcie budowy: nie zapamiętuj starszego stanu
                _data_cache.update(at=time.time(), body=body)
            _data_cache["last"] = body
    return body


def stale_body(last, e):
    """Ostatnia dobra odpowiedź ze znacznikiem "stale" {"since": generatedAt tej odpowiedzi, "error": rodzaj błędu}
    i zdaniem w activity.error (Teraz)."""
    try:
        d = json.loads(last)
    except ValueError:
        return last
    since = d.get("generatedAt") or ""
    d["stale"] = {"since": since, "error": type(e).__name__}
    a = d.get("activity") if isinstance(d.get("activity"), dict) else {}
    hm = since[11:16] if len(since) >= 16 else ""
    a["error"] = "Dane sprzed %s: błąd odczytu na serwerze (%s)." % (hm or "błędu", type(e).__name__)
    d["activity"] = a
    return json.dumps(d, ensure_ascii=False)


_log_last = {}


def log_once(key, label, e):
    """Ślad wyjątku w logu raz na zmianę treści (panel pyta co 3 s z kilku urządzeń: stały błąd nie zalewa stderr)."""
    sig = (label, type(e).__name__, str(e))
    if _log_last.get(key) == sig:
        return False
    _log_last[key] = sig
    import traceback
    print("%s:" % label, file=sys.stderr)
    traceback.print_exception(type(e), e, e.__traceback__)
    return True


def data_invalidate():
    with _data_lock:
        _data_cache.update(at=0.0, body=None, gen=_data_cache.get("gen", 0) + 1)


def git_link(raw):
    """Adres zdalnego repozytorium → (rodzaj, link, host). Rodzaj: "github", "inny" albo "" (brak adresu).
    Link https bez danych logowania (user:token@) i bez .git; dla ssh poza GitHubem tylko host, bez linku."""
    raw = (raw or "").strip()
    if not raw:
        return "", "", ""
    if "://" in raw:
        u = urlparse(raw)
        host, path, scheme = (u.hostname or "").lower(), u.path, u.scheme.lower()
        port = ":%d" % u.port if u.port and scheme in ("http", "https") else ""
    elif re.match(r"^(?:[^@/\s]+@)?[^:/\s]+:", raw) and not re.match(r"^[A-Za-z]:[\\/]", raw):
        host, _, path = raw.partition(":")
        host, scheme, port = host.rpartition("@")[2].lower(), "ssh", ""
    else:                                              # ścieżka lokalna
        return "inny", "", ""
    path = "/" + path.strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    if host in ("github.com", "www.github.com", "ssh.github.com"):
        parts = [x for x in path.split("/") if x][:2]
        return "github", ("https://github.com/" + "/".join(parts)) if len(parts) == 2 else "", "github.com"
    if not host:
        return "inny", "", ""
    if scheme in ("http", "https"):
        return "inny", "https://%s%s%s" % (host, port, path if path != "/" else ""), host
    return "inny", "", host


def _git_dirs(folder):
    """(katalog .git kopii, wspólny katalog .git) bez wołania gita; worktree i submoduł mają plik .git z „gitdir:”."""
    gitdir = os.path.join(folder, ".git")
    if os.path.isfile(gitdir):
        line = (projekt.read(gitdir) or "").strip()
        if not line.startswith("gitdir:"):
            return "", ""
        gitdir = os.path.normpath(os.path.join(folder, line[7:].strip()))
        common = (projekt.read(os.path.join(gitdir, "commondir")) or "").strip()
        return gitdir, os.path.normpath(os.path.join(gitdir, common)) if common else gitdir
    return gitdir, gitdir


def _head_branch(folder):
    """Bieżąca gałąź z .git/HEAD (bez wołania gita); "" przy odłączonym HEAD albo bez repozytorium."""
    head = (projekt.read(os.path.join(_git_dirs(folder)[0], "HEAD")) or "").strip() if _git_dirs(folder)[0] else ""
    return head[16:] if head.startswith("ref: refs/heads/") else ""


def _origin_url(folder):
    """remote.origin.url z .git/config bez wołania gita (działa też przy innym właścicielu folderu)."""
    gitdir = _git_dirs(folder)[1]
    if not gitdir:
        return ""
    section = False
    for line in (projekt.read(os.path.join(gitdir, "config")) or "").splitlines():
        s = line.strip()
        if s.startswith("["):
            section = re.match(r'^\[\s*remote\s+"origin"\s*\]$', s) is not None
        elif section:
            k, sep, v = s.partition("=")
            if sep and k.strip().lower() == "url":
                return v.strip().strip('"')
    return ""


def project_git(folder):
    """{repo, remote, url, host, unpushed}: folder projektu jako repozytorium git (własne .git, nie folder
    nadrzędny). unpushed: commity gałęzi lokalnych, których nie ma w żadnej gałęzi zdalnej (bez git fetch)."""
    if not os.path.exists(os.path.join(folder, ".git")):
        return {"repo": False, "remote": "", "url": "", "host": "", "unpushed": 0, "branch": ""}
    remote, url, host = git_link(_origin_url(folder))
    unpushed = 0
    if remote:
        code, n = _git_out(folder, "rev-list", "--count", "--branches", "--not", "--remotes", timeout=3)
        unpushed = int(n) if code == 0 and n.isdigit() else 0
    return {"repo": True, "remote": remote, "url": url, "host": host, "unpushed": unpushed,
            "branch": _head_branch(folder)}


GIT_TTL = 120                         # s: stan git projektów odświeżany w tle, /api/data bierze ostatni wynik
_git_state = {"value": {}, "at": {}, "busy": False, "lock": threading.Lock()}


def git_states(folders):
    """{folder: project_git} z pamięci. Nowy folder liczony od razu (kilka ms), przeterminowane w tle;
    po odświeżeniu ze zmianą /api/data jest unieważniane."""
    st, now = _git_state, time.time()
    with st["lock"]:
        missing = [f for f in folders if f not in st["value"]]
        stale = [f for f in folders if f in st["value"] and now - st["at"].get(f, 0) >= GIT_TTL]
    for f in missing:
        v = project_git(f)
        with st["lock"]:
            st["value"][f], st["at"][f] = v, time.time()
    if stale:
        with st["lock"]:
            start, st["busy"] = not st["busy"], True
        if start:
            def work():
                changed = False
                try:
                    for f in stale:
                        v = project_git(f)
                        with st["lock"]:
                            changed = changed or st["value"].get(f) != v
                            st["value"][f], st["at"][f] = v, time.time()
                finally:
                    with st["lock"]:
                        st["busy"] = False
                if changed:
                    data_invalidate()
            threading.Thread(target=work, daemon=True).start()
    with st["lock"]:
        return {f: dict(st["value"][f]) for f in folders if f in st["value"]}


# ---------- kopia projektu a GitHub (kopie.py; AGENCI.md „Kopia projektu i GitHub”) ----------
def _gh_project(body):
    """(projekt, folder, None) albo (None, None, (kod, błąd)) dla {"project": id}."""
    pid = str(body.get("project") or "")
    data, index = load_projects(resolve=False)
    p = next((x for x in data["projects"] if x["id"] == pid), None)
    if not p or pid not in index:
        return None, None, (404, "Nie ma takiego projektu.")
    if data["projectsSource"] != "registry":
        return None, None, (409, "Projekty przykładowe: bez kopii na serwerze.")
    return p, index[pid], None


def _gh_view(p, folder):
    """Stan kopii z blokadami usunięcia (z pracą agenta i budowaniem podglądu) i polem removable."""
    st = kopie.state(folder, p.get("github") or "", p.get("githubBranch") or "", projekt.CARDS)
    m = get_agents()
    live = m.has_live(p["id"])
    with m.site._lock:
        building = p["id"] in m.site._busy
    if st["repo"]:
        if building:
            st["blocks"].insert(0, "Trwa budowanie podglądu strony")
        if live:
            st["blocks"].insert(0, "Agent pracuje w projekcie")
        if p.get("origin") != "registry":
            st["blocks"].append("Projekt ze zbieracza: kopię usuwasz na komputerze, z którego pochodzi")
    st.update(agentLive=live, removable=st["repo"] and not st["blocks"], folder=short_path(folder),
              project=p["id"])
    if st["repo"]:
        st["stashes"] = kopie.stash_list(folder)
        st["sources"] = m.dirty_sources(folder, [d["path"] for d in st["dirty"]]) if st["dirtyCount"] else []
    if st["removed"].get("trash"):
        st["removed"]["trash"] = short_path(st["removed"]["trash"])
    return st


def _gh_forget(folder):
    with _git_state["lock"]:
        _git_state["value"].pop(folder, None)


def github_state(body):
    """POST /api/github/stan {"project", "fetch"?: bool}: stan kopii; fetch tylko na żądanie („Sprawdź”)."""
    p, folder, err = _gh_project(body)
    if err:
        return err
    msg = ""
    if body.get("fetch") is True:
        if not kopie.has_repo(folder):
            msg = "Kopii nie ma na serwerze: nie ma czego sprawdzać."
        else:
            with kopie.folder_lock(folder):
                ok, why = kopie.fetch(folder, p.get("github") or "")
            msg = "Sprawdzono na GitHubie." if ok else why
            if not ok:
                return 502, msg, {"state": _gh_view(p, folder)}
    _gh_forget(folder)
    return 200, "", {"state": _gh_view(p, folder), "message": msg}


PUSH_ORDER = ("access", "missing", "timeout", "rejected", "error", "sent", "nothing")


def github_push(body):
    """POST /api/github/wyslij {"project", "branches"?: [nazwy]}: push gałęzi bazowej (wybranej w kopii) i wybranych
    innych, bez --force; potem stan od nowa. 200 wysłano / nic do wysłania, 409 odrzucone, 502 brak dostępu."""
    p, folder, err = _gh_project(body)
    if err:
        return err
    st = kopie.state(folder, p.get("github") or "", p.get("githubBranch") or "")
    if not st["repo"]:
        return 409, "Kopii nie ma na serwerze: nie ma czego wysłać."
    if not st["origin"]:
        return 409, "Repozytorium projektu nie ma origin."
    if st["github"] and not st["originOk"]:
        return 409, "origin wskazuje inne repozytorium niż pole github: w karcie (%s)." % st["github"]
    known = {b["name"] for b in st["branches"]}
    extra = body.get("branches") if isinstance(body.get("branches"), list) else []
    names = ([st["branch"]] if st["branch"] else []) + [str(b) for b in extra if isinstance(b, str)]
    names = list(dict.fromkeys(n for n in names if n))
    if not names:
        return 409, "W kopii nie jest wybrana żadna gałąź (odłączony HEAD). Wybierz gałęzie do wysłania."
    bad = [n for n in names if n not in known]
    if bad:
        return 400, "Nie ma gałęzi: %s." % ", ".join(bad[:3])
    with kopie.folder_lock(folder):
        results = kopie.push(folder, names, p.get("github") or "")
    _gh_forget(folder)
    kinds = {r["result"] for r in results}
    worst = next(k for k in PUSH_ORDER if k in kinds)
    msg = " ".join(r["message"] for r in results)
    extra = {"state": _gh_view(p, folder), "results": results, "result": worst, "message": msg}
    if worst in ("sent", "nothing"):
        return 200, "", extra
    return (409 if worst in ("rejected", "error") else 502), msg, extra


def github_remove(body):
    """POST /api/github/usun-kopie {"project", "confirm": true}: przeniesienie kopii do kosza, gdy nic lokalnego nie
    zginie (najpierw git fetch; blokady jak w _gh_view). Folder zostaje z dowiązaniami karty."""
    if body.get("confirm") is not True:
        return 400, "Potwierdź usunięcie kopii."
    p, folder, err = _gh_project(body)
    if err:
        return err
    m = get_agents()
    with m._start_lock, kopie.folder_lock(folder):
        if not kopie.has_repo(folder):
            return 409, "Kopii nie ma na serwerze."
        st = _gh_view(p, folder)
        if st["blocks"]:
            return 409, "Nie usunięto: %s." % "; ".join(st["blocks"]), {"state": st}
        ok, why = kopie.fetch(folder, p.get("github") or "")
        if not ok:
            return 502, "Nie sprawdzono GitHuba, kopia zostaje. %s" % why, {"state": _gh_view(p, folder)}
        st = _gh_view(p, folder)
        if st["blocks"]:
            return 409, "Nie usunięto: %s." % "; ".join(st["blocks"]), {"state": st}
        ok, dest = kopie.move_to_trash(folder, p.get("github") or "")
    _gh_forget(folder)
    if not ok:
        return 500, dest, {"state": _gh_view(p, folder)}
    return 200, "", {"trash": short_path(dest), "state": _gh_view(p, folder),
                     "message": "Kopia w koszu: %s. Projekt zostaje; kopia sklonuje się z GitHuba przy następnym zadaniu."
                     % short_path(dest)}


def repo_change(body, action):
    """POST /api/repo/zatwierdz | odloz | przywroc {"project", "ref"?}: zmiany niezatwierdzone w kopii projektu
    (zatwierdzenie jako zmiany agenta, odłożenie do schowka, przywrócenie); potem stan kopii od nowa."""
    p, folder, err = _gh_project(body)
    if err:
        return err
    code, msg, extra = get_agents().repo_action(p["id"], action, str(body.get("ref") or ""))
    _gh_forget(folder)
    data_invalidate()
    extra = dict(extra or {}, state=_gh_view(p, folder))
    return (code, msg, extra) if code != 200 else (200, "", extra)


def build_data():
    out, index = load_projects()
    for p in out["projects"]:
        p["folder"] = short_path(index[p["id"]])
    gits = git_states(sorted(set(index.values())))
    for p in out["projects"]:
        p["git"] = gits.get(index[p["id"]])
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
    publication_jobs(out, index)
    for t in out["tasks"]:
        t["ownerNeeds"] = projekt.owner_needs(t)
    out.update(projekt.owner_counts(out["projects"], out["stages"], out["tasks"], today))
    out["agents"] = manager.snapshot(out, index)
    out["agents"]["canRunTasks"] = out["projectsSource"] == "registry"
    out["history"] = project_history(out)
    out["server"] = server_state()
    out["costs"] = COSTS.state()
    out["panelVersion"] = panel_version()
    # części poza rdzeniem (zadania, projekty): błąd w jednej nie daje 500 na całym /api/data; nazwa części trafia
    # do activity.error (Teraz: „Nie odczytano: …”), ślad do logu
    errs = []

    def part(label, fn, default):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            errs.append(label)
            log_once("build_data:" + label, "build_data (%s)" % label, e)
            return default

    out["publish"] = part("publikacje", lambda: get_publisher().status(), None)
    out["resources"] = part("zasoby", resources_state, None)
    out["deploy"] = part("wdrożenie", deploy_state, None)
    out["fieldsMigration"] = part("pola zadań", lambda: get_fields().summary(), {})
    out["film"] = part("nagrywarka", lambda: {"available": get_recorder().available(), "account": film.account_email(),
                                              "explainer": get_recorder().available("objasnienie")},
                       {"available": False, "account": "", "explainer": False})
    out["studio"] = part("studio", lambda: studio_summary(index), {}) if out["projectsSource"] == "registry" else {}
    if out["projectsSource"] == "registry":
        part("filmy zadań", lambda: film_links(out["tasks"], index) or True, False)
        part("scenariusze nagrań", lambda: script_links(out["tasks"], out["projects"], index) or True, False)
    out["activity"] = part("aktywność", lambda: activity(out, index, manager),
                           {"films": [], "chats": [], "chatsDone": [], "closed": [], "runs": [], "recorder": False})
    if part("kontrole zadań", lambda: add_checks(out["tasks"], index, out["server"]) or True, False) is False:
        for t in out["tasks"]:
            t.setdefault("check", None)
    if errs:
        a = out["activity"]
        a["error"] = ("Nie odczytano: %s. " % ", ".join(errs) + (a.get("error") or "")).strip()
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


# ---------- rozwój panelu na serwerze (ROZWOJ.md): gałąź rozwoj kopii roboczej agenta, przycisk „Wdróż” ----------
DEV_REPO = os.environ.get("PANEL_ROZWOJ_REPO", "").strip() or "/home/agent/rozwoj/IntegrateSystems"
DEV_BRANCH = "rozwoj"
DEPLOY_DIR = os.environ.get("PANEL_WDROZENIE_DIR", "").strip() or os.path.expanduser("~/dane/wdrozenie")
TEST_ENV = os.environ.get("PANEL_TEST_ENV", "").strip() or "/etc/integrate/panel-testowy.env"
TEST_URL = os.environ.get("PANEL_TEST_URL", "").strip() or "https://test.2-29-181-133.sslip.io"
DEPLOY_CMD = ["sudo", "-n", "/usr/bin/systemctl", "start", "--no-block", "wdroz-panel.service"]
DEPLOY_TTL = 30
AUTO_UNIT = "/etc/systemd/system/multi-user.target.wants/wdroz-panel-auto.path"
PROD_REPO = os.path.dirname(HERE)
_deploy = {"at": 0.0, "value": None, "lock": threading.Lock()}


def _git_out(repo, *args, timeout=20):
    try:
        r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return 1, ""
    return r.returncode, r.stdout.strip()


def _deploy_branch():
    """Commity gałęzi rozwoj, których nie ma na produkcji (pobrane do refs/rozwoj/kandydat), co DEPLOY_TTL s."""
    # --no-write-fetch-head: FETCH_HEAD należy do git pull zapisu kart (zapis-kart.sh); wspólny plik dawał
    # „Cannot rebase onto multiple branches”, gdy oba pobierania zbiegły się w czasie
    with _deploy["lock"]:
        if _deploy["value"] is not None and time.time() - _deploy["at"] < DEPLOY_TTL:
            return _deploy["value"]
        repo = PROD_REPO
        code, _ = _git_out(repo, "fetch", "-q", "--no-tags", "--no-write-fetch-head", DEV_REPO, "+%s:refs/rozwoj/kandydat" % DEV_BRANCH)
        if code:
            value = {"error": "Nie odczytano gałęzi %s z kopii roboczej." % DEV_BRANCH}
        else:
            _, log = _git_out(repo, "log", "--format=%h%x09%cI%x09%s", "-n", "30", "HEAD..refs/rozwoj/kandydat")
            _, ahead = _git_out(repo, "rev-list", "--count", "HEAD..refs/rozwoj/kandydat")
            _, behind = _git_out(repo, "rev-list", "--count", "refs/rozwoj/kandydat..HEAD", "--", ".",
                                 ":(exclude)szkice", ":(exclude)raporty")
            _, stat = _git_out(repo, "diff", "--shortstat", "HEAD...refs/rozwoj/kandydat")
            commits = []
            for line in log.splitlines():
                sha, _, rest = line.partition("\t")
                at, _, subject = rest.partition("\t")
                commits.append({"sha": sha, "at": at, "subject": subject})
            value = {"ahead": int(ahead or 0), "behind": int(behind or 0), "stat": stat, "commits": commits}
        _deploy.update(at=time.time(), value=value)
        return value


def _test_password():
    try:
        with open(TEST_ENV, encoding="utf-8") as f:
            for line in f:
                name, sep, value = line.strip().partition("=")
                if sep and name == "PANEL_TOKEN":
                    return value.strip().strip("\"'")
    except OSError:
        pass
    return ""


def deploy_state():
    """Blok "deploy" w /api/data albo None, gdy na tej maszynie nie ma kopii roboczej rozwoju."""
    if not os.path.isdir(os.path.join(DEV_REPO, ".git")):
        return None
    out = dict(_deploy_branch())
    last = load_json(os.path.join(DEPLOY_DIR, "stan.json"), None)
    out["last"] = last if isinstance(last, dict) else None
    if out["last"] and out["last"].get("state") in ("error", "rolledback"):
        text = projekt.read(os.path.join(DEPLOY_DIR, "ostatnie.log")) or ""
        out["log"] = "\n".join(text.splitlines()[-40:])
    out.update(branch=DEV_BRANCH, repo=DEV_REPO, testUrl=TEST_URL, testPassword=_test_password(),
               auto=os.path.exists(AUTO_UNIT))
    return out


def start_deploy(body):
    """POST /api/wdroz: uruchamia wdroz-panel.service (testy, scalenie, restart, kontrola, powrót przy błędzie)."""
    st = deploy_state()
    if st is None:
        return 400, "Rozwój na serwerze nie jest zainstalowany (uruchom/serwer/zainstaluj-rozwoj.sh)."
    last = st.get("last") or {}
    if last.get("state") in ("queued", "running"):
        started = _iso(last.get("at"))
        if started and datetime.datetime.now() - started < datetime.timedelta(minutes=30):
            return 409, "Wdrożenie już trwa."
    if not st.get("ahead"):
        return 400, "Na gałęzi %s nie ma nowych zmian." % DEV_BRANCH
    try:
        r = subprocess.run(DEPLOY_CMD, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError) as e:
        return 500, "Nie uruchomiono wdrożenia: %s" % e
    if r.returncode:
        return 500, "Nie uruchomiono wdrożenia: %s" % ((r.stderr or r.stdout).strip()[:200] or "błąd sudo")
    os.makedirs(DEPLOY_DIR, exist_ok=True)
    now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    projekt.write_atomic(os.path.join(DEPLOY_DIR, "stan.json"),
                         json.dumps({"state": "queued", "text": "W kolejce", "at": now, "startedAt": now}, ensure_ascii=False))
    _deploy["at"] = 0.0
    return 200, ""


DRIVE_BACK_PAGE = ('<!doctype html><html lang="pl"><head><meta charset="utf-8"><meta name="viewport" '
                   'content="width=device-width,initial-scale=1"><title>Google Drive</title></head><body '
                   'style="font:16px system-ui,sans-serif;padding:24px"><p>%s</p><p><a href="/#koszty?k=drive">Panel</a></p>'
                   '</body></html>')
DRIVE_BACK_REDIRECT = ('<!doctype html><html lang="pl"><meta charset="utf-8"><title>Google Drive</title>'
                       '<meta http-equiv="refresh" content="0;url=%s">'
                       '<p>Google Drive połączony. <a href="%s">Wróć do panelu</a>.</p></html>')
_drive = {"obj": None}


def get_drive():
    """Połączenia Google Drive projektów (drive.py); jedno na proces."""
    if _drive["obj"] is None:
        env = os.environ.get       # PANEL_RCLONE*, PANEL_DRIVE_*: atrapa i osobne pliki (testy, zrzuty)
        helper = env("PANEL_DRIVE_HELPER")
        _drive["obj"] = drive.Drive(card_dir, rclone=env("PANEL_RCLONE"), conf=env("PANEL_RCLONE_CONF"),
                                    data_dir=env("PANEL_DRIVE_DIR"), helper=helper.split() if helper else None)
    return _drive["obj"]


_resources = {"obj": None}


def _resource_projects():
    """{id: (nazwa, [repozytorium, folder karty])} z rejestru dla rozmiarów projektów."""
    data, index = load_projects(resolve=False)
    names = {p["id"]: p["name"] for p in data["projects"]}
    return {pid: (names.get(pid, pid), [folder, card_dir(pid) or ""]) for pid, folder in index.items()}


def resources_state():
    """Blok "resources" w /api/data: tylko na serwerze z Linuksem (na Macu None)."""
    if not sys.platform.startswith("linux") and not os.environ.get("PANEL_ZASOBY"):
        return None
    if _resources["obj"] is None:
        home = os.path.expanduser("~")
        folders = [("Repozytoria projektów", os.path.join(home, "projekty")),
                   ("Karty, posty i media", os.path.join(os.path.dirname(HERE), "szkice")),
                   ("Kopie zapasowe", os.path.join(home, "kopie")),
                   ("Dane panelu", os.path.join(home, "dane")),
                   ("Narzędzia (nagrywanie)", os.path.join(home, "narzedzia"))]
        _resources["obj"] = zasoby.Resources(folders, _resource_projects)
    return _resources["obj"].state()


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
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Projekty · logowanie</title>
@@APP@@
<style>
:root{--bg:#f6f7f9;--surface:#fff;--line:#dde1e7;--ink:#1d2433;--ink-3:#5a6577;--accent:#2563c9;--accent-ink:#fff;--ctl-line:#7d8696;--bad:#a8281a;
  --font:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue","Noto Sans",Arial,sans-serif;color-scheme:light dark}
@media (prefers-color-scheme:dark){:root{--bg:#15171c;--surface:#1d2027;--line:#30353f;--ink:#e7e9ee;--ink-3:#8d95a3;--accent:#6b9ef0;--accent-ink:#0f1420;--ctl-line:#6b7382;--bad:#ffaaa0}}
html,body{height:100%%;margin:0}
body{background:var(--bg);color:var(--ink);font:15px/1.5 var(--font);display:flex;align-items:center;justify-content:center}
@media (max-width:620px){body{align-items:flex-start;padding-top:12vh;box-sizing:border-box}}
form{width:min(340px,calc(100vw - 32px));box-sizing:border-box;padding:24px;border:1px solid var(--line);border-radius:8px;background:var(--surface);display:grid;grid-template-columns:minmax(0,1fr);gap:12px}
.brand{display:flex;align-items:center;gap:10px}
.mark{width:32px;height:32px;border-radius:6px;background:var(--accent);color:var(--accent-ink);display:grid;place-items:center;font-weight:700;font-size:13px}
h1{margin:0;font-size:18px;line-height:1.2}
.brand small{display:block;font-size:13px;color:var(--ink-3)}
label{font-weight:600;font-size:14px}
.pw{display:flex;gap:8px}
input,button{box-sizing:border-box;font:inherit;border-radius:6px;min-height:44px}
input{flex:1 1 0;width:0;min-width:0;padding:8px 12px;background:var(--surface);color:var(--ink);border:1px solid var(--ctl-line)}
button:focus-visible{outline:2px solid var(--accent);outline-offset:1px}
input:focus-visible{outline:none;border-color:var(--accent);box-shadow:0 0 0 1px var(--accent)}
button{padding:8px 14px;font-weight:600;cursor:pointer}
.pokaz{background:var(--surface);color:var(--ink);border:1px solid var(--ctl-line)}
.wejdz{width:100%%;background:var(--accent);color:var(--accent-ink);border:0}
p.blad{margin:0;color:var(--bad)}
</style></head><body><form method="post" action="/wejscie">
<div class="brand"><div class="mark" aria-hidden="true">IS</div><div><h1>Projekty</h1><small>IntegrateSystems</small></div></div>
<label for="haslo">Hasło</label>
<div class="pw"><input type="password" id="haslo" name="haslo" autocomplete="current-password" autofocus required>
<button type="button" class="pokaz" aria-pressed="false" aria-controls="haslo" onclick="var i=document.getElementById('haslo'),on=i.type==='password';i.type=on?'text':'password';this.setAttribute('aria-pressed',on);this.textContent=on?'Ukryj':'Pokaż'">Pokaż</button></div>
<button type="submit" class="wejdz">Zaloguj</button>%s</form></body></html>"""


def login_page(error=""):
    return (LOGIN_PAGE % ('<p class="blad" role="alert">%s</p>' % error if error else "")).replace("@@APP@@", APP_HEAD, 1)


# ---------- eksport terminów do kalendarza (ICS) ----------
def ics_escape(text):
    return str(text).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


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


MEDIA_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp",
               ".gif": "image/gif", ".mp4": "video/mp4", ".mov": "video/quicktime"}
MEDIA_MAX = 300 * 1024 * 1024
MEDIA_DIRS = ("posty", "media", "studio")      # w folderze karty: posty, Twoje wgrane pliki, studio filmów


def card_dir(pid):
    """Folder karty projektu (tam, gdzie leży KARTA.md) albo None."""
    _, index = load_projects(resolve=False)
    folder = index.get(str(pid or ""))
    return os.path.dirname(os.path.realpath(os.path.join(folder, "KARTA.md"))) if folder else None


def media_list():
    """Zdjęcia i filmy ze wszystkich projektów: posty/, media/ (wgrane), studio/. Najnowsze najpierw."""
    _, index = load_projects(resolve=False)
    out = []
    for pid, folder in index.items():
        cards = os.path.dirname(os.path.realpath(os.path.join(folder, "KARTA.md")))
        for sub in MEDIA_DIRS:
            for root, dirs, files in os.walk(os.path.join(cards, sub)):
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    if f.startswith(".") or ext not in MEDIA_TYPES:
                        continue
                    path = os.path.join(root, f)
                    try:
                        st = os.stat(path)
                    except OSError:
                        continue
                    rel = os.path.relpath(path, cards).replace(os.sep, "/")
                    item = {"project": pid, "path": rel, "name": f, "kind": "video" if ext in (".mp4", ".mov") else "image",
                            "size": st.st_size, "at": int(st.st_mtime), "source": sub}
                    m = re.match(r"^posty/(\d{4}-\d\d-\d\d)", rel)
                    if m:
                        item["day"] = m.group(1)
                    out.append(item)
    out.sort(key=lambda x: -x["at"])
    return out[:3000]


def media_file(pid, rel):
    """Ścieżka pliku z media_list (tylko w posty/, media/, studio/ karty, tylko znane rozszerzenia) albo None."""
    cards = card_dir(pid)
    rel = str(rel or "")
    parts = rel.split("/")
    if not cards or not rel or rel.startswith("/") or parts[0] not in MEDIA_DIRS or any(x.startswith(".") or not x for x in parts):
        return None
    path = os.path.realpath(os.path.join(cards, rel))
    if os.path.commonpath([cards, path]) != cards or os.path.splitext(path)[1].lower() not in MEDIA_TYPES \
            or not os.path.isfile(path) or os.path.basename(path).startswith("."):
        return None
    return path


def post_folder(pid, day, index=None):
    """Folder posta: <karta projektu>/posty/<dzień>-<nazwa>/. None, gdy go nie ma albo dane są niepoprawne."""
    if not POST_DAY.match(day or ""):
        return None
    if index is None:
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


def post_text(folder):
    """Tytuł i teksty kanałów z post.md."""
    out = {"title": "", "sections": {}}
    try:
        with open(os.path.join(folder, "post.md"), encoding="utf-8") as f:
            text = f.read()
    except (OSError, UnicodeDecodeError):
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
    return out["title"], out["sections"]


def post_info(folder):
    """Treści i pliki, które można otworzyć w edytorze posta."""
    title, sections = post_text(folder)
    out = {"title": title, "sections": sections, "folder": os.path.basename(folder),
           "image": any(os.path.exists(os.path.join(folder, name)) for name in ("grafika.png", "grafika.svg"))}
    # imageAt: wersja grafiki (najnowszy z grafika.png i grafika.svg) do odświeżenia podglądu po zmianie
    out["imageAt"] = max([int(os.path.getmtime(os.path.join(folder, n))) for n in ("grafika.png", "grafika.svg")
                          if os.path.exists(os.path.join(folder, n))] or [0])
    fpath = publikacja.Publisher.film(folder)
    # at: zmiana pliku (ctime) do odświeżenia odtwarzacza; czas modyfikacji filmu to wersja scenariusza (Recorder)
    out["film"] = {"name": os.path.basename(fpath), "size": os.path.getsize(fpath),
                   "at": int(os.stat(fpath).st_ctime)} if fpath else None
    out["scenario"] = os.path.isfile(os.path.join(folder, film.SCENARIO))
    out["filmInfo"] = film.describe(folder) if out["scenario"] else None     # rodzaj filmu, szablon, błąd scenariusza
    st = film.read_state(folder)
    out["rec"] = {"state": st.get("state", ""), "error": st.get("error", ""), "at": st.get("at", ""),
                  "hint": film.record_hint(st.get("error", "")) if st.get("state") == "error" else "",
                  "shot": st.get("state") == "error" and os.path.isfile(os.path.join(folder, film.ERROR_SHOT))}
    out["filmManual"] = bool(fpath) and os.path.exists(os.path.join(folder, film.MANUAL))
    out["filmStale"] = bool(out["scenario"] and fpath) and studio_stale(folder, fpath)   # starszy niż szablon/marka
    # film starszy niż treść posta (scenariusz albo obrazy posta zmienione po nagraniu): nagra się od nowa
    sv = film.scenario_version(folder) if out["scenario"] and fpath else None
    out["filmOld"] = bool(sv is not None and sv > os.path.getmtime(fpath) and not out["filmManual"])
    out["srt"] = bool(fpath) and os.path.isfile(os.path.join(folder, film.SRT))
    out["photos"] = udostepnij.photos(folder)        # dodatkowe zdjęcia (karuzela na Instagramie)
    out["film4x5"] = bool(fpath) and os.path.isfile(os.path.join(folder, film.FEED))
    prev = os.path.join(folder, film.PREVIOUS)      # poprzednia wersja filmu (porównanie w panelu)
    out["filmPrev"] = {"at": int(os.stat(prev).st_ctime)} if fpath and os.path.isfile(prev) else None
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

    def log_request(self, code="-", size="-"):
        if urlparse(getattr(self, "path", "")).path == "/api/drive/powrot":
            return
        super().log_request(code, size)

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
        if path.startswith("/podglad/"):        # podgląd strony w ramce bez ciasteczka: klucz projektu w ścieżce
            if self.command == "GET" and get_agents().site.key_ok(path):
                return True
            self._send(401, "Wymagane hasło.", "text/plain; charset=utf-8")
            return False
        if self.command == "GET" and path == "/api/drive/powrot":    # powrót z Google: jednorazowy state logowania
            return True
        if self.command in ("GET", "OPTIONS") and path.startswith("/udostepnij/"):   # pakiet: token w ścieżce
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

    def _send_range(self, body, ctype, disposition="inline", extra=()):
        """Bajty pliku z obsługą nagłówka Range (film w Safari wymaga odpowiedzi 206)."""
        size = len(body)
        head = [("Cache-Control", "no-store"), ("Content-Disposition", disposition), ("Accept-Ranges", "bytes"), *extra]
        m = re.match(r"^bytes=(\d*)-(\d*)$", (self.headers.get("Range") or "").strip())
        if not m or not (m.group(1) or m.group(2)):
            return self._send(200, body, ctype, head)
        if m.group(1):
            start = int(m.group(1))
            end = min(int(m.group(2)), size - 1) if m.group(2) else size - 1
        else:
            start, end = max(0, size - int(m.group(2))), size - 1
        if start >= size or start > end:
            return self._send(416, b"", ctype, head + [("Content-Range", "bytes */%d" % size)])
        return self._send(206, body[start:end + 1], ctype, head + [("Content-Range", "bytes %d-%d/%d" % (start, end, size))])

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
        if path.startswith("/udostepnij/"):
            return self._share_get(path, parse_qs(url.query))
        if path.startswith("/podglad/"):
            code, body, ctype, headers = get_agents().site.serve(path)
            return self._send(code, body, ctype, headers)
        if path == "/api/strona":
            code, err, extra = get_agents().site.info((parse_qs(url.query).get("project") or [""])[0])
            return self._send(code, json.dumps(dict(extra, ok=code == 200, error=err), ensure_ascii=False),
                              "application/json; charset=utf-8")
        if path in ("/api/udostepnij", "/api/instagram/udostepnij"):       # czy rozszerzenie pobrało pakiet
            st = SHARES.status((parse_qs(url.query).get("t") or [""])[0])
            return self._send(200 if st else 404, json.dumps(dict(st or {}, ok=bool(st)), ensure_ascii=False),
                              "application/json; charset=utf-8")
        if path == "/wejscie":
            if self._has_session() or (self._client_local() and not (local_guard() and TOKEN)):
                return self._redirect("/")
            return self._send(200, login_page(), "text/html; charset=utf-8")
        if path in ("/", "/index.html"):
            return self._send(200, SHELL % page_html(), "text/html; charset=utf-8")
        if path == "/podglad":
            return self._send(200, SHELL % page_html(preview_data()), "text/html; charset=utf-8")
        if path == "/api/data":
            return self._send(200, data_cached(), "application/json; charset=utf-8")
        if path == "/terminy.ics":
            return self._send(200, build_ics(), "text/calendar; charset=utf-8")
        if path == "/api/agent/zlecenie-wynik":
            name = (parse_qs(url.query).get("id") or [""])[0]
            body = get_agents().orders.result(name)
            return self._send(200 if body is not None else 404, body if body is not None else "Nie znaleziono wyniku.",
                              "text/plain; charset=utf-8", [("Cache-Control", "no-store"), ("X-Content-Type-Options", "nosniff")])
        if path == "/api/agent/przebieg":          # przebieg uruchomienia na żywo (wiersze po numerze od=)
            qs = parse_qs(url.query)
            code, err, extra = get_agents().run_log((qs.get("id") or [""])[0], (qs.get("od") or ["0"])[0])
            return self._send(code, json.dumps(dict(extra, ok=code == 200, error=err), ensure_ascii=False),
                              "application/json; charset=utf-8", [("Cache-Control", "no-store")])
        if path == "/api/agent/zrzut":             # zrzut PNG z .zrzuty/ katalogu roboczego uruchomienia strony
            qs = parse_qs(url.query)
            code, body = get_agents().shot_file((qs.get("id") or [""])[0], (qs.get("plik") or [""])[0])
            if code != 200:
                return self._send(404, "Nie znaleziono", "text/plain; charset=utf-8")
            return self._send(200, body, "image/png", [("Cache-Control", "no-store"), ("X-Content-Type-Options", "nosniff"),
                                                       ("Content-Disposition", "inline")])
        if path == "/api/agent/diff":
            qs = parse_qs(url.query)
            code, text = get_agents().diff((qs.get("id") or [""])[0], (qs.get("project") or [""])[0],
                                           (qs.get("branch") or [""])[0])
            if code == 200:
                return self._send(200, text, "text/plain; charset=utf-8")
            return self._send(code, json.dumps({"ok": False, "error": text}, ensure_ascii=False),
                              "application/json; charset=utf-8")
        if path == "/api/drive":
            code, err, extra = get_drive().status((parse_qs(url.query).get("project") or [""])[0])
            return self._send(code, json.dumps(dict(extra, ok=code == 200, error=err), ensure_ascii=False),
                              "application/json; charset=utf-8")
        if path in ("/api/drive/konta", "/api/drive/foldery"):
            q = parse_qs(url.query)
            code, err, extra = get_drive().accounts() if path == "/api/drive/konta" else \
                get_drive().folders((q.get("account") or [""])[0], (q.get("odswiez") or [""])[0] == "1")
            return self._send(code, json.dumps(dict(extra, ok=code == 200, error=err), ensure_ascii=False),
                              "application/json; charset=utf-8")
        if path == "/api/drive/powrot":         # powrót z Google (własny klient OAuth); bez sesji: chroni state
            code, text = get_drive().oauth_back(url.query, redirect=True)
            if code == 303:
                # Nowy dokument panelu kończy przekierowanie z obcej domeny. Kolejne żądanie
                # do własnej witryny dostanie ciasteczko sesji SameSite=Strict.
                target = html.escape(text, quote=True)
                return self._send(200, DRIVE_BACK_REDIRECT % (target, target), "text/html; charset=utf-8",
                                  [("Referrer-Policy", "no-referrer")])
            return self._send(code, DRIVE_BACK_PAGE % (html.escape(text)), "text/html; charset=utf-8",
                              [("Referrer-Policy", "no-referrer")])
        if path == "/api/asystent/karty":
            code, err, extra = get_agents().assistant_cards_get()
            return self._send(code, json.dumps(dict(extra, ok=code == 200, error=err), ensure_ascii=False),
                              "application/json; charset=utf-8")
        if path == "/api/asystent":
            code, err, extra = get_agents().assistant_get()
            return self._send(code, json.dumps(dict(extra, ok=code == 200, error=err), ensure_ascii=False),
                              "application/json; charset=utf-8")
        if path == "/api/project/chat":
            code, err, extra = get_agents().project_chat_get((parse_qs(url.query).get("project") or [""])[0])
            return self._send(code, json.dumps(dict(extra, ok=code == 200, error=err), ensure_ascii=False),
                              "application/json; charset=utf-8")
        if path == "/api/task/chat":
            code, err, extra = get_agents().chat_get((parse_qs(url.query).get("id") or [""])[0])
            return self._send(code, json.dumps(dict(extra, ok=code == 200, error=err), ensure_ascii=False),
                              "application/json; charset=utf-8")
        if path == "/api/odbior":                 # strona „Odbiór pracy”: zadanie, wersje wyniku, uruchomienie
            code, err, extra = get_agents().review((parse_qs(url.query).get("id") or [""])[0])
            return self._send(code, json.dumps(dict(extra, ok=code == 200, error=err), ensure_ascii=False),
                              "application/json; charset=utf-8")
        if path in ("/api/odbior/plik", "/api/odbior/zip"):
            qs = parse_qs(url.query)
            task_id, version, rel = ((qs.get(k) or [""])[0] for k in ("id", "v", "path"))
            full = path.endswith("/zip")
            if full:
                code, body, ctype = get_agents().review_zip(task_id, version)
            else:
                code, body, ctype = get_agents().review_file(task_id, version, rel)
            if code != 200:
                return self._send(code, body, "text/plain; charset=utf-8")
            if qs.get("miniatura") == ["1"]:
                if ctype != "application/pdf":
                    return self._send(404, "Brak miniatury.", "text/plain; charset=utf-8")
                preview = agents.review_pdf_thumbnail(body)
                if not preview:
                    return self._send(404, "Brak miniatury PDF.", "text/plain; charset=utf-8")
                return self._send(200, preview, "image/png", [("Cache-Control", "private, max-age=60")])
            name = "pliki-wyniku.zip" if full else rel.rsplit("/", 1)[-1]
            disposition = "attachment; filename*=UTF-8''" + quote(name, safe="") if full or qs.get("pobierz") == ["1"] else "inline"
            if ctype == "image/svg+xml":
                return self._send_range(body, ctype, disposition, [("Content-Security-Policy", "sandbox; default-src 'none'; style-src 'unsafe-inline'")])
            return self._send_range(body, ctype, disposition)
        if path == "/api/plik/surowy":            # obraz albo PDF z wyniku zadania (podgląd w szufladzie)
            code, body, ctype = read_project_asset(url.query)
            if code != 200:
                return self._send(code, body, "text/plain; charset=utf-8")
            return self._send(200, body, ctype, [("Cache-Control", "no-store"), ("X-Content-Type-Options", "nosniff"),
                                                 ("Content-Disposition", "inline")])
        if path == "/api/plik":
            code, answer = read_project_file(url.query)
            return self._send(code, json.dumps(answer, ensure_ascii=False), "application/json; charset=utf-8")
        if path == "/api/studio/podklad":            # odsłuch podkładu z listy marki
            qs = parse_qs(url.query)
            fpath = studio_music_file((qs.get("project") or [""])[0], (qs.get("plik") or [""])[0])
            if not fpath:
                return self._send(404, "Brak podkładu", "text/plain; charset=utf-8")
            with open(fpath, "rb") as f:
                return self._send(200, f.read(), AUDIO_TYPES.get(os.path.splitext(fpath)[1][1:].lower(),
                                                                 "application/octet-stream"),
                                  [("Cache-Control", "no-store")])
        if path == "/api/media":
            return self._send(200, json.dumps({"ok": True, "items": media_list()}, ensure_ascii=False),
                              "application/json; charset=utf-8")
        if path == "/api/media/plik":
            q = parse_qs(url.query)
            fpath = media_file((q.get("project") or [""])[0], (q.get("path") or [""])[0])
            if not fpath:
                return self._send(404, "Nie znaleziono", "text/plain; charset=utf-8")
            return self._send_file(fpath, MEDIA_TYPES[os.path.splitext(fpath)[1].lower()], bool((q.get("pobierz") or [""])[0]))
        if path == "/api/scenariusz":
            q = parse_qs(url.query)
            code, err, extra = script_info((q.get("project") or [""])[0], (q.get("date") or [""])[0])
            return self._send(code, json.dumps(dict(extra, ok=code == 200, error=err), ensure_ascii=False),
                              "application/json; charset=utf-8", [("Cache-Control", "no-store")])
        if path == "/api/post/warianty":
            q = parse_qs(url.query)
            code, err, extra = graphic_state((q.get("project") or [""])[0], (q.get("date") or [""])[0])
            return self._send(code, json.dumps(dict(extra, ok=code == 200, error=err), ensure_ascii=False),
                              "application/json; charset=utf-8", [("Cache-Control", "no-store")])
        if path in ("/api/post", "/api/post/grafika", "/api/post/film", "/api/post/bladfilmu", "/api/post/napisy"):
            q = parse_qs(url.query)
            folder = post_folder((q.get("project") or [""])[0], (q.get("date") or [""])[0])
            if folder and not agents.has_post(folder):     # sam scenariusz nagrania: posta jeszcze nie ma
                folder = None
            if not folder:
                return self._send(404, json.dumps({"ok": False, "error": "Nie ma posta na ten dzień."}, ensure_ascii=False),
                                  "application/json; charset=utf-8")
            if path == "/api/post":
                return self._send(200, json.dumps(dict(post_info(folder), ok=True), ensure_ascii=False),
                                  "application/json; charset=utf-8")
            if path in ("/api/post/bladfilmu", "/api/post/napisy"):   # zrzut z błędu nagrania, napisy .srt filmu
                name = film.ERROR_SHOT if path == "/api/post/bladfilmu" else film.SRT
                fpath = os.path.join(folder, name)
                if not os.path.isfile(fpath):
                    return self._send(404, "Brak pliku", "text/plain; charset=utf-8")
                with open(fpath, "rb") as f:
                    return self._send(200, f.read(), "image/png" if name.endswith(".png") else
                                      "application/x-subrip; charset=utf-8",
                                      [("Content-Disposition", ('inline; filename="blad-filmu.png"'
                                                                if name.endswith(".png") else
                                                                'attachment; filename="%s.srt"'
                                                                % os.path.basename(folder))),
                                       ("Cache-Control", "no-store")])
            if path == "/api/post/film":                 # plik filmu do udostępnienia z telefonu
                fpath = publikacja.Publisher.film(folder)
                if (q.get("wariant") or [""])[0] == "4x5":   # wersja 4:5 do feedu (film.py: FEED)
                    fpath = os.path.join(folder, film.FEED) if os.path.isfile(os.path.join(folder, film.FEED)) else None
                elif (q.get("wariant") or [""])[0] == "poprzedni":   # poprzednia wersja (film.py: PREVIOUS)
                    prev = os.path.join(folder, film.PREVIOUS)
                    fpath = prev if os.path.isfile(prev) and not os.path.islink(prev) else None
                if not fpath:
                    return self._send(404, "Brak filmu", "text/plain; charset=utf-8")
                return self._send_file(fpath, "video/quicktime" if fpath.endswith(".mov") else "video/mp4")
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
        data_invalidate()
        if path == "/wejscie":
            return self._login()
        if path == "/api/calendar/connect":
            connect_calendar()
            return self._send(202, json.dumps({"connecting": True}), "application/json; charset=utf-8")
        if path == "/api/post/film":
            return self._film_upload(urlparse(self.path).query)
        if path == "/api/media/wgraj":
            return self._media_upload(urlparse(self.path).query)
        if path == "/api/studio/plik":
            return self._studio_upload(urlparse(self.path).query)
        if path == "/api/post/obraz":
            return self._post_image_upload(urlparse(self.path).query)
        if path == "/api/post/grafika":
            return self._post_graphic_upload(urlparse(self.path).query)
        if path == "/api/asystent/glos":
            return self._voice_upload(urlparse(self.path).query)
        if path in WRITES:
            body = self._json_body(CHAT_BODY if path in ("/api/odbior/popraw", "/api/odbior/akceptuj", "/api/project/chat", "/api/asystent", "/api/asystent/karty",
                                                         "/api/film/zmien", "/api/post/tekst", "/api/strona/uwaga", "/api/strona/koncepcja",
                                                         "/api/scenariusz/tekst", "/api/drive/klient", "/api/task/finish") else 4096)
            if body is None:
                return self._send(400, json.dumps({"ok": False, "error": "Nieprawidłowe żądanie."}),
                                  "application/json; charset=utf-8")
            try:
                result = WRITES[path](body)
            except Exception as e:  # noqa: BLE001  (błąd w obsłudze: odpowiedź z opisem zamiast zerwanego połączenia)
                import traceback
                traceback.print_exc()
                result = (500, "Błąd serwera panelu (%s). Szczegóły w dzienniku usługi." % type(e).__name__)
            data_invalidate()
            code, answer = result[0], {"ok": 200 <= result[0] < 300, "error": result[1]}
            if len(result) > 2:
                answer.update(result[2])            # np. id nowego uruchomienia
            return self._send(code, json.dumps(answer, ensure_ascii=False), "application/json; charset=utf-8")
        return self._send(404, "Nie znaleziono", "text/plain; charset=utf-8")

    def _raw_body(self, limit):
        """(bajty, błąd): surowe ciało żądania do limit bajtów (wgranie pliku)."""
        size = 0
        with contextlib.suppress(ValueError):
            size = int(self.headers.get("Content-Length") or 0)
        if not 0 < size <= limit:
            self.close_connection = True
            return None, "Plik do %d MB." % (limit // (1 << 20))
        data, left = [], size
        while left > 0:
            chunk = self.rfile.read(min(left, 1 << 20))
            if not chunk:
                break
            data.append(chunk)
            left -= len(chunk)
        if left:
            return None, "Wysyłka przerwana."
        return b"".join(data), ""

    def _voice_upload(self, query):
        """POST /api/asystent/glos?view=&open=: nagranie z mikrofonu (audio/webm z Chrome, audio/mp4 z Safari, do
        4 MB) -> rozpoznany tekst -> wiadomość do asystenta. Odpowiedź: {"text"} i stan jak POST /api/asystent."""
        q = parse_qs(query)
        ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if not (ctype.startswith("audio/") or ctype in ("video/webm", "video/mp4")):
            self.close_connection = True
            return self._send(400, json.dumps({"ok": False, "error": "Nieobsługiwany format nagrania."},
                                              ensure_ascii=False), "application/json; charset=utf-8")
        data, err = self._raw_body(glos.AUDIO_MAX)
        if data is None:
            return self._send(400, json.dumps({"ok": False, "error": err.replace("Plik", "Nagranie")},
                                              ensure_ascii=False), "application/json; charset=utf-8")
        code, err, extra = get_agents().assistant_voice(ctype, data, (q.get("view") or [""])[0],
                                                        (q.get("open") or [""])[0])
        return self._send(code, json.dumps(dict(extra, ok=200 <= code < 300, error=err), ensure_ascii=False),
                          "application/json; charset=utf-8")

    def _studio_upload(self, query):
        """POST /api/studio/plik?project=&rodzaj=muzyka|logo&licencja=[&rog=1|0]: surowy plik podkładu (mp3, m4a,
        wav, ogg) albo logo (png, jpg) do studio/ projektu i wpis w marka.json (studio_add_file; rog: logo w rogu
        przez cały film)."""
        q = parse_qs(query)
        ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        limit = film.AUDIO_MAX if (q.get("rodzaj") or [""])[0] == "muzyka" else film.IMAGE_MAX
        data, err = self._raw_body(limit)
        if data is None:
            return self._send(400, json.dumps({"ok": False, "error": err}, ensure_ascii=False),
                              "application/json; charset=utf-8")
        rog = (q.get("rog") or [""])[0]
        code, err, extra = studio_add_file((q.get("project") or [""])[0], (q.get("rodzaj") or [""])[0], ctype,
                                           data, (q.get("licencja") or [""])[0],
                                           corner={"1": True, "0": False}.get(rog))
        data_invalidate()
        return self._send(code, json.dumps(dict(extra, ok=code == 200, error=err), ensure_ascii=False),
                          "application/json; charset=utf-8")

    def _post_image_upload(self, query):
        """POST /api/post/obraz?project=&date=&param=: zrzut ekranu (png, jpg) do folderu posta, wpisany w pole
        obrazu szablonu filmu (post_add_image)."""
        q = parse_qs(query)
        ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        data, err = self._raw_body(film.IMAGE_MAX)
        if data is None:
            return self._send(400, json.dumps({"ok": False, "error": err}, ensure_ascii=False),
                              "application/json; charset=utf-8")
        code, err, extra = post_add_image((q.get("project") or [""])[0], (q.get("date") or [""])[0],
                                          (q.get("param") or [""])[0], ctype, data)
        data_invalidate()
        return self._send(code, json.dumps(dict(extra, ok=code == 200, error=err), ensure_ascii=False),
                          "application/json; charset=utf-8")

    def _post_graphic_upload(self, query):
        """POST /api/post/grafika?project=&date=: nowa grafika posta (post_set_image)."""
        q = parse_qs(query)
        ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        data, err = self._raw_body(film.IMAGE_MAX)
        if data is None:
            return self._send(400, json.dumps({"ok": False, "error": err}, ensure_ascii=False),
                              "application/json; charset=utf-8")
        code, err = post_set_image((q.get("project") or [""])[0], (q.get("date") or [""])[0], ctype, data)
        return self._send(code, json.dumps({"ok": code == 200, "error": err}, ensure_ascii=False),
                          "application/json; charset=utf-8")

    def _cors(self, path=""):
        """Nagłówki CORS pakietu udostępnienia: tylko dokładny adres strony platformy pakietu (rozszerzenie działa
        na niej); pakiet nieznany albo wygasły: dowolnej obsługiwanej platformy (komunikat o wygaśnięciu)."""
        origin = self.headers.get("Origin") or ""
        parts = path.split("/")
        platform = SHARES.platform(parts[2]) if len(parts) > 2 else None
        if not udostepnij.origin_ok(origin, platform):
            return [("Vary", "Origin")]
        return [("Access-Control-Allow-Origin", origin), ("Vary", "Origin")]

    def do_OPTIONS(self):
        """Zapytanie wstępne przeglądarki (sieć lokalna: Access-Control-Request-Private-Network) do pakietu."""
        path = urlparse(self.path).path
        if not self._host_ok() or not path.startswith("/udostepnij/") or not self._allowed(path):
            return self._send(404, "Nie znaleziono", "text/plain; charset=utf-8")
        hdr = self._cors(path)
        if len(hdr) > 1:
            hdr += [("Access-Control-Allow-Methods", "GET"), ("Access-Control-Max-Age", "600")]
            if self.headers.get("Access-Control-Request-Private-Network"):
                hdr.append(("Access-Control-Allow-Private-Network", "true"))
        return self._send(204, b"", "text/plain; charset=utf-8", hdr)

    def _share_get(self, path, q):
        """GET /udostepnij/<token>: pakiet (JSON); /udostepnij/<token>/<n>[?pobierz=1]: plik n pakietu."""
        parts = path.split("/")
        cors = self._cors(path)
        if len(parts) == 3:
            pkg = SHARES.package(parts[2])
            if pkg:
                return self._send(200, json.dumps(pkg, ensure_ascii=False), "application/json; charset=utf-8", cors)
        elif len(parts) == 4:
            hit = SHARES.file(parts[2], parts[3])
            if hit:
                return self._send_file(hit[0], hit[1], bool((q.get("pobierz") or [""])[0]), cors)
        return self._send(404, json.dumps({"ok": False, "error": "Pakiet wygasł albo nie istnieje. Udostępnij post "
                                           "z panelu jeszcze raz."}, ensure_ascii=False),
                          "application/json; charset=utf-8", cors)

    def _send_file(self, fpath, ctype, download=False, extra=()):
        """Plik z obsługą Range (Safari na iPhonie odtwarza wideo tylko z odpowiedzi 206)."""
        size = os.path.getsize(fpath)
        hdr = [("Content-Disposition", '%s; filename="%s"' % ("attachment" if download else "inline",
                                                             os.path.basename(fpath).replace('"', ""))),
               ("Accept-Ranges", "bytes")] + list(extra)
        m = re.match(r"^bytes=(\d*)-(\d*)$", (self.headers.get("Range") or "").strip())
        with open(fpath, "rb") as f:
            if m and (m.group(1) or m.group(2)):
                a, b = m.group(1), m.group(2)
                start = int(a) if a else max(0, size - int(b))
                end = min(size - 1, int(b)) if a and b else size - 1
                if start > end or start >= size:
                    return self._send(416, b"", ctype, [("Content-Range", "bytes */%d" % size)])
                f.seek(start)
                return self._send(206, f.read(end - start + 1), ctype,
                                  hdr + [("Content-Range", "bytes %d-%d/%d" % (start, end, size))])
            return self._send(200, f.read(), ctype, hdr)

    def _media_upload(self, query):
        """POST /api/media/wgraj?project=&name=: zdjęcie albo film (najwyżej 300 MB) do <karta>/media/."""
        q = parse_qs(query)
        pid, name = (q.get("project") or [""])[0], (q.get("name") or [""])[0]
        cards = card_dir(pid)
        ext = os.path.splitext(name)[1].lower()
        try:
            size = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            size = 0
        err = ("Wybierz projekt." if not cards else "Plik: zdjęcie (JPG, PNG, WEBP, GIF) albo film (MP4, MOV)."
               if ext not in MEDIA_TYPES else "Plik: najwyżej 300 MB." if not 0 < size <= MEDIA_MAX else "")
        if err:
            self.close_connection = True
            return self._send(400, json.dumps({"ok": False, "error": err}, ensure_ascii=False), "application/json; charset=utf-8")
        base = re.sub(r"[^\w.-]+", "-", os.path.splitext(os.path.basename(name))[0]).strip("-.")[:60] or "plik"
        folder = os.path.join(cards, "media")
        os.makedirs(folder, exist_ok=True)
        stem = "%s-%s" % (datetime.date.today().isoformat(), base)
        target, n = os.path.join(folder, stem + ext), 2
        while os.path.exists(target):
            target, n = os.path.join(folder, "%s-%d%s" % (stem, n, ext)), n + 1
        tmp, left = os.path.join(folder, ".wysylka-" + os.path.basename(target)), size
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
        os.replace(tmp, target)
        return self._send(200, json.dumps({"ok": True, "error": "", "path": os.path.relpath(target, cards)}, ensure_ascii=False),
                          "application/json; charset=utf-8")

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
        for name in publikacja.FILM_NAMES + (film.FEED, film.SRT):   # wersja 4:5 i napisy były z poprzedniego filmu
            with contextlib.suppress(OSError):
                os.remove(os.path.join(folder, name))
        os.replace(tmp, os.path.join(folder, "film" + ext))
        with contextlib.suppress(OSError):          # film wgrany ręcznie: zmiana studia nie nagra go sama od nowa
            with open(os.path.join(folder, film.MANUAL), "w", encoding="utf-8") as f:
                f.write(datetime.datetime.now().isoformat(timespec="seconds") + "\n")
        return self._send(200, json.dumps({"ok": True, "error": "", "size": size}), "application/json; charset=utf-8")

    def _json_body(self, limit=4096):
        """Mały obiekt JSON (najwyżej limit bajtów). Wymagany typ application/json, więc obca strona nie wyśle go
        bez zgody CORS."""
        if (self.headers.get("Content-Type") or "").split(";")[0].strip().lower() != "application/json":
            return None
        try:
            size = int(self.headers.get("Content-Length") or 0)
            if not 0 < size <= limit:
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
        get_agents()._closing = True            # uruchomienia za pośrednikiem pracują dalej (AGENCI.md)
        raise KeyboardInterrupt

    for name in ("SIGTERM", "SIGBREAK"):       # zatrzymanie usługi ma zakończyć także procesy agentów
        if hasattr(signal, name):
            signal.signal(getattr(signal, name), _stop)
    get_agents().start()                        # dopiero po zajęciu portu: drugi egzemplarz nie rusza rekordów
    get_publisher().start()
    try:
        mark_interrupted_films(load_projects(resolve=False)[1])
    except Exception:  # noqa: BLE001  (stan filmów nie może zatrzymać startu panelu)
        pass
    threading.Thread(target=auto_record_loop, daemon=True).start()
    threading.Thread(target=get_fields().migration_loop, args=(get_agents().claude_free, time.sleep), daemon=True).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        get_agents().shutdown(keep=True)
