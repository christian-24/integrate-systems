"""Uruchamianie agentów (Claude Code, Codex) z panelu, na logowaniu subskrypcji. Kontrakt: AGENCI.md.

Sama biblioteka standardowa, Python 3.9+, macOS i Windows. Moduł nie importuje serwera:
dostaje od niego funkcję load_projects, wspólny zamek zapisu i moduł projekt.
"""
import collections
import contextlib
import datetime
import glob
import hashlib
import io
import json
import os
import posixpath
import re
import shlex
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import urllib.request
import uuid
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import agent_progress
import asystent  # noqa: E402  (stała sesja asystenta)
import glos  # noqa: E402  (rozpoznawanie mowy)
import grafiki  # noqa: E402  (grafiki do postów przez Codex)
import karty  # noqa: E402  (karty asystenta: katalog, sprawdzenie, biblioteka)
import kopie  # noqa: E402  (kopia projektu a GitHub: klon na start)
import naprawy  # noqa: E402  (jednorazowe naprawy po starcie panelu)
import pola  # noqa: E402  (pola formularza zadań właściciela: propozycja modelu)
import scenariusz  # noqa: E402  (scenariusz nagrania filmu właściciela)
import strona  # noqa: E402  (podgląd strony WWW projektu)
ROOT = os.path.dirname(HERE)
WINDOWS = os.name == "nt"
# Windows: serwer działa pod pythonw (bez konsoli), więc żaden proces potomny nie może otwierać okna.
NO_WINDOW = {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)} if WINDOWS else {}
LIVE = ("queued", "running")
KEEP = 200          # tyle rekordów zostaje na dysku
NOT_RUNS = ("stan.json", "zamkniete.json")   # pliki w katalogu uruchomień, które nie są rekordami (dawny zamkniete.json)
SHOWN = 40          # tyle rekordów trafia do /api/data
TOOLS_TTL = 300     # sekundy między odczytami stanu narzędzi
CONFLICT = "Plik zmienił się od ostatniego odczytu. Odświeżam listę."
PM_TOOLS = "Bash(python3 standard/pm.py:*),Bash(python standard/pm.py:*),Read,Write,Edit,Glob,Grep"
# Zadania Claude: bezpieczna lista narzędzi (git lokalnie, testy, pliki); bez push i bez sieci.
TASK_TOOLS = ",".join([
    "Bash(git status:*)", "Bash(git diff:*)", "Bash(git log:*)", "Bash(git switch -c:*)", "Bash(git checkout -b:*)",
    "Bash(git add:*)", "Bash(git commit:*)", "Bash(python3 -m pytest:*)", "Bash(pytest:*)",
    "Bash(python3 -m unittest:*)", "Read", "Edit", "Write", "Glob", "Grep",
    "TodoWrite", "TaskCreate", "TaskUpdate", "TaskList", "TaskGet"])
CHECK_PROMPT = "Odpowiedz jednym słowem: ok"
# Agent uruchomiony z panelu nie zakłada własnych pomocników ani przepływów (2026-11-23: zadanie „wizytówki” uruchomiło
# 33 pomocników i zużyło cały limit 5 godzin) i nie dostaje konektorów konta (--strict-mcp-config).
RUN_DENY = "Agent,Task,Workflow,SendMessage,TaskStop,Monitor,CronCreate,CronDelete,ScheduleWakeup,RemoteTrigger,PushNotification"
# Rozmowy z agentem (Asystent i Rozmowa w projekcie, AGENCI.md „Rozmowy”): jedna lista zabronionych narzędzi dla obu;
# internet (WebSearch, WebFetch) zdejmuje z niej Manager przy PANEL_ASYSTENT_INTERNET różnym od 0.
CHAT_DENY = "Bash,MultiEdit,Write,NotebookEdit,WebFetch,WebSearch,Task," + RUN_DENY
PL_DAYS = ("poniedziałek", "wtorek", "środa", "czwartek", "piątek", "sobota", "niedziela")
CHAT_MAX = 2000             # znaków w jednej wiadomości właściciela
CHAT_KEEP = 100             # tyle wiadomości zostaje w historii zadania
CHAT_ANSWER = 8000          # najwyżej tyle znaków odpowiedzi
AS_ANSWER = 16000           # odpowiedź asystenta: tekst i blok kart
CHAT_PARALLEL = 3           # tyle rozmów naraz czeka na odpowiedź
CHAT_EXPIRED = "Rozmowa wygasła. Wyślij pytanie jeszcze raz."
LOGIN_TTL = 600           # s: tyle czeka logowanie przez panel na kod
PLAN_MAX = 6
STATE_LABEL = {"done": "zakończone", "error": "błąd", "login": "wymaga logowania", "limit": "limit subskrypcji",
               "stopped": "zatrzymane", "timeout": "przekroczony czas"}
LOGIN_RE = re.compile(r"authenticat|oauth|/login|not logged in|invalid api key|\b401\b", re.I)
LIMIT_RE = re.compile(r"usage limit|limit reached|rate.?limit|hit your limit|\b429\b", re.I)
DENIED = {"rejected", "denied", "blocked", "exceeded"}
AGENT_DIR = ".agent"        # katalogi robocze uruchomień: <repozytorium>/.agent/<id uruchomienia>
DIFF_MAX = 200 * 1024       # GET /api/agent/diff: najwyżej tyle bajtów tekstu
CHANGES_MAX = 200           # tyle plików trafia do pola changes rekordu
# Przebieg uruchomienia na żywo (pole log rekordu, GET /api/agent/przebieg): bez osobnych plików na serwerze.
LOG_KEEP = 200              # wierszy przebiegu w rekordzie
LOG_TEXT = 4000             # znaków jednej wypowiedzi agenta albo wiadomości właściciela
LOG_SAVE = 10               # s: najrzadziej tyle między zapisami rekordu w trakcie pracy
FIX_MAX = 1500              # znaków wiersza poprawka: po dopisaniu wiadomości z pracy agenta
SHOT_NAME = re.compile(r"^[\w.-]{1,80}\.png$")
SHOT_MAX = 15 * 1024 * 1024
SHOTS_SHOWN = 6
DENY_RE = re.compile(r"requires approval|permission|haven't granted|not allowed|denied", re.I)
GIT_NAME, GIT_EMAIL = "Panel projektów", "panel@localhost"     # gdy repozytorium nie ma user.email
# Ścieżki plików w wierszu wynik: (materiał dla następników z po:).
RESULT_PATH = re.compile(r"(?<![\w./-])(/?(?:[\w.-]+/)*[\w-][\w.-]*\.(?:md|txt|csv|json|html|svg|png|jpe?g|pdf|ya?ml))"
                         r"(?![\w/])", re.I)
RESULT_PATHS_MAX = 10
# Render HTML → PDF/PNG dla agenta zadania (AGENCI.md, „Render HTML do PDF i PNG”): jeden skrypt panelu,
# w narzędziach Claude tylko jako Bash(<python> <skrypt>:*). Skrypt leży w repozytorium panelu (na serwerze
# /home/panel/…, agent go nie zmieni).
RENDER_SCRIPT = os.path.join(HERE, "html-do-pdf.py")
# Uruchamianie z rozmów (AGENCI.md, „Rozmowa o projekcie” i „Asystent”): wiersz działania w odpowiedzi modelu.
# Model tylko prosi; uruchamia serwer przez run_task po sprawdzeniu tych samych reguł co przycisk „Uruchom”.
# Wersje wyniku zadania (strona „Odbiór pracy”): <runs_dir>/wersje/<sha1(projekt|plik|tytuł)[:16]>/<n>/meta.json
# i kopie plików z wyniku. Ścieżki jak resFiles w panelu (wynik:, zostało:), także film.
VERSION_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp",
                 ".gif": "image/gif", ".avif": "image/avif", ".svg": "image/svg+xml", ".pdf": "application/pdf",
                 ".md": "text/plain; charset=utf-8", ".txt": "text/plain; charset=utf-8",
                 ".mp4": "video/mp4", ".mov": "video/quicktime", ".webm": "video/webm",
                 ".zip": "application/zip", ".csv": "text/csv", ".json": "application/json", ".docx": "application/octet-stream",
                 ".xlsx": "application/octet-stream", ".pptx": "application/octet-stream",
                 ".odt": "application/octet-stream", ".tiff": "application/octet-stream", ".mp3": "audio/mpeg", ".wav": "audio/wav"}
VERSION_KINDS = {ext: (mime.split("/")[0] if mime.startswith(("image/", "video/")) else "other")
                 for ext, mime in VERSION_TYPES.items()}
VERSION_KINDS.update({".pdf": "pdf", ".md": "text", ".txt": "text"})
VERSION_EXTENSIONS = "|".join(re.escape(ext) for ext in VERSION_TYPES)
VERSION_PATH = re.compile(r"(?:^|(?<=[\s(„\"'`:]))((?:[\w.-]+/)*[\w-][\w.-]*(?:" + VERSION_EXTENSIONS +
                          r"))(?:#[\w-]+)?(?=$|[\s),.;:\"'`”])", re.I)
VERSION_FILE_MAX = 15 * 1024 * 1024     # jeden plik w kopii wersji (i odczyt z folderu albo gałęzi)
REVIEW_FILE_MAX = 128 * 1024 * 1024  # pojedyncze pobranie, także bez kopii wersji
VERSION_TOTAL_MAX = 60 * 1024 * 1024    # razem na wersję
VERSION_FILES = 12
VERSIONS_KEEP = 20
VARIANTS_LABEL = "odebrane warianty"    # odpowiedź: odebrane warianty = a, b (odbiór części wariantów)
REVIEW_FIX_DEFAULT = "Popraw według znaczników poniżej."


def publication_task_title(pub, projekt):
    """Stały tytuł zadania z Marketingu, niezależny od numeru wiersza w kampanii."""
    day = str(pub["date"])[:10]
    key = hashlib.sha256((projekt.task_key(pub) + "|" + day).encode()).hexdigest()[:16]
    return projekt._clean("Przygotuj publikację na %s (%s): %s" % (day, key, pub["title"]), 120)


def version_paths(text, refs=()):
    """Ścieżki plików z tekstu wyniku jak resFiles w panelu: bez .., bez ZADANIA.md i materiałów zadania, do 12."""
    skip = {r.get("path") for r in refs if isinstance(r, dict) and not r.get("anchor")}
    out = []
    for m in VERSION_PATH.finditer(str(text or "")):
        path = m.group(1)
        path = path[2:] if path.startswith("./") else path
        if re.search(r"(^|/)\.\.(/|$)", path) or path.lower() == "zadania.md" or path in skip or path in out:
            continue
        out.append(path)
    return out[:VERSION_FILES]


def review_pdf_thumbnail(blob):
    """Pierwsza strona jako mały PNG. Renderer nie zapisuje podglądu na dysku."""
    renderer = shutil.which("pdftoppm")
    if not renderer or len(blob) > VERSION_FILE_MAX:
        return None
    try:
        proc = subprocess.run([renderer, "-f", "1", "-l", "1", "-scale-to", "192", "-png", "-singlefile", "-"],
                              input=blob, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=5, **NO_WINDOW)
    except (OSError, subprocess.SubprocessError):
        return None
    return proc.stdout if proc.returncode == 0 and proc.stdout.startswith(b"\x89PNG\r\n\x1a\n") else None


def variant_name(path):
    """Nazwa wariantu z pliku obrazu: „wizytowki/podglad.png” -> „podglad”."""
    return os.path.splitext(posixpath.basename(path))[0]


RUN_LINE = re.compile(r"^[ \t>*`-]*Uruchom\s*:\s*(.+?)\s*$", re.I)
# wiersze działań rozmów (Asystent i Rozmowa w projekcie); panel wykonuje je i usuwa z odpowiedzi
ACTION_LINE = re.compile(r"^[ \t>*`-]*(Uruchom|Polecenie|Odpowiedź na pytanie|Odpowiedz na pytanie)\s*:\s*(.+?)\s*$", re.I)
RUN_MAX = 3                 # najwyżej tyle uruchomień (Uruchom: i Polecenie:) z jednej odpowiedzi
ANSWER_MAX = 3              # najwyżej tyle odpowiedzi na pytania z jednej odpowiedzi
# „zrób to” / „wykonaj” na końcu wiadomości o zadaniu (Rozmowa w projekcie z odnośnikiem do zadania) = „Wyślij i wykonaj”
EXEC_END = re.compile(r"(?:^|[\s,.;:!?—–-])(?:zrób to|zrob to|wykonaj(?: to)?)[\s.!]*$", re.I)
# wersja zasad w promptach rozmów: inna wersja w pliku rozmowy = nowa sesja z pełnym promptem
CHAT_RULES_V = "6"
PANEL_ROLE = "panel"        # wiadomość panelu w historii rozmowy (stan uruchomienia), nie od modelu


def _unq(text):
    return str(text or "").strip().strip("`").strip().strip("„”\"'`«»").strip()


def take_actions(answer):
    """Wiersze działań z odpowiedzi rozmowy: (odpowiedź bez nich, [(rodzaj, pola)]). Rodzaje:
    ("run", (projekt, tytuł)) z „Uruchom: <projekt> | <tytuł>” (albo „Uruchom: <tytuł>”),
    ("order", (projekt, tytuł, polecenie)) z „Polecenie: <projekt> | <tytuł> | <polecenie>”,
    ("answer", (projekt, numer, odpowiedź)) z „Odpowiedź na pytanie: <projekt> | <numer> | <odpowiedź>”.
    Najwyżej RUN_MAX uruchomień i poleceń razem oraz ANSWER_MAX odpowiedzi; powtórzenia raz."""
    keep, found = [], []
    runs = answers = 0
    for line in str(answer or "").split("\n"):
        m = ACTION_LINE.match(line)
        if not m:
            keep.append(line)
            continue
        word, value = m.group(1).lower(), m.group(2).strip().strip("`")
        if word == "uruchom":
            pid, _, title = value.rpartition("|") if "|" in value else ("", "", value)
            item = ("run", (pid.strip(), _unq(title)))
            ok = bool(item[1][1])
        else:
            bits = [x.strip() for x in value.split("|", 2)]
            if len(bits) < 3:
                continue
            kind = "order" if word == "polecenie" else "answer"
            item = (kind, (bits[0], _unq(bits[1]), bits[2].strip()))
            ok = all(item[1])
        if not ok or item in found:
            continue
        if item[0] == "answer":
            if answers >= ANSWER_MAX:
                continue
            answers += 1
        else:
            if runs >= RUN_MAX:
                continue
            runs += 1
        found.append(item)
    return "\n".join(keep).rstrip(), found


def take_run_lines(answer):
    """Odpowiedź bez wierszy działań i lista (projekt, tytuł) samych „Uruchom:”."""
    text, found = take_actions(answer)
    return text, [v for k, v in found if k == "run"]


def _norm_title(text):
    return re.sub(r"\s+", " ", str(text or "")).strip().rstrip(".").lower()


def _inside(base, path):
    try:
        return os.path.commonpath([base, path]) == base
    except ValueError:
        return False


def git_run(cwd, args, timeout=60):
    """git bez haków i fsmonitora (repozytorium mógł zmienić agent), z komunikatami po angielsku do rozpoznania
    konfliktów. Zwraca (kod, stdout, stderr); -1 przy braku polecenia albo przekroczonym czasie."""
    env = dict(os.environ, LC_ALL="C", LANG="C", GIT_TERMINAL_PROMPT="0")
    base = ["git", "-c", "core.hooksPath=" + os.devnull, "-c", "core.fsmonitor=false", "-c", "core.quotePath=false"]
    try:
        p = subprocess.run(base + list(args), cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, encoding="utf-8", errors="replace", timeout=timeout, env=env,
                           **NO_WINDOW)
        return p.returncode, p.stdout or "", p.stderr or ""
    except (OSError, subprocess.SubprocessError) as e:
        return -1, "", str(e)


def git_ident(cwd):
    """-c user.name/user.email, gdy repozytorium (ani konfiguracja globalna) nie ma autora."""
    code, out, _ = git_run(cwd, ["config", "user.email"], timeout=15)
    return [] if code == 0 and out.strip() else ["-c", "user.name=" + GIT_NAME, "-c", "user.email=" + GIT_EMAIL]


def git_numstat(top, base, branch):
    """[{"path", "added", "removed"}] dla base...branch; plik binarny: 0, 0 i "binary": true."""
    code, out, _ = git_run(top, ["diff", "--numstat", "--no-renames", "--no-ext-diff", "%s...%s" % (base, branch)])
    if code != 0:
        return []
    changes = []
    for line in out.splitlines():
        parts = line.split("\t", 2)
        if len(parts) != 3:
            continue
        item = {"path": parts[2], "added": int(parts[0]) if parts[0].isdigit() else 0,
                "removed": int(parts[1]) if parts[1].isdigit() else 0}
        if not parts[0].isdigit():
            item["binary"] = True
        changes.append(item)
    return changes[:CHANGES_MAX]


# Mniej spraw do właściciela (decyzja 2026-11-21): pytania tylko o to, czego nikt poza nim nie rozstrzygnie,
# Zadanie Codexa o grafice (AGENCI.md „Grafiki (Codex)”): obrazy wbudowanym narzędziem na subskrypcji ChatGPT.
CODEX_IMAGE_RULES = [
    "- Grafiki i zdjęcia twórz i poprawiaj wbudowanym narzędziem obrazów ($imagegen), bez klucza API. Wynik zapisz "
    "jako PNG w folderze posta (posty/<dzień>-<nazwa>/) pod nazwą wariant-<n>.png z kolejnym wolnym numerem; "
    "nie nadpisuj grafika.png ani zdjęć (właściciel wybiera wariant w edytorze posta).",
]
# Projekt z polem karty „- grafiki: tylko zdjęcia” (albo zadanie z „bez $imagegen” / „Zachowaj zdjęcie”): Codex
# nie generuje obrazów, tylko obrabia prawdziwe zdjęcia (decyzja właściciela 2026-11-25, reklamy Shield & Silent).
CODEX_PHOTO_RULES = [
    "- Nie generuj ani nie przerabiaj obrazów narzędziem $imagegen. Pracuj tylko na prawdziwych zdjęciach z materiałów "
    "zadania albo folderu posta: kadrowanie, tekst, gradient, ramka i logo (Pillow albo HTML i dashboard/html-do-pdf.py). "
    "Auto, ludzie i tło zostają takie jak na zdjęciu. Wynik zapisz jako PNG w folderze posta (posty/<dzień>-<nazwa>/); "
    "nie nadpisuj grafika.png ani zdjęć.",
]
PHOTO_ONLY_RE = re.compile(r"bez\s+\$imagegen|zachowaj\s+zdj", re.I)


def photos_only(card_text, detail_text=""):
    """Czy Codex ma pracować tylko na prawdziwych zdjęciach: pole karty „- grafiki: tylko zdjęcia” albo zapis w zadaniu."""
    for line in str(card_text or "").splitlines():
        m = re.match(r"^\s*-\s*grafiki\s*:\s*(.+?)\s*$", line, re.I)
        if m and re.search(r"tylko\s+(prawdziwe\s+)?zdj", m.group(1), re.I):
            return True
    return bool(PHOTO_ONLY_RE.search(str(detail_text or "")))


# najwyżej jedno otwarte pytanie na projekt, odbiór tylko dla pracy wychodzącej na zewnątrz albo z decyzją.
FIELDS_RULE = ("- Zadanie `kto: ty`, które wymaga danych od właściciela (identyfikatory, liczby, wybór, data, adres), "
               "zakładasz od razu z wciętym wierszem `  pyta: Etykieta [typ]; Etykieta [typ]` (typy: `[tekst, np. …]`, "
               "`[tak/nie]`, `[liczba]`, `[wybór: A | B]`, `[data]`, `[link]`; najwyżej 3 pola; format w STANDARD.md). "
               "Bez pól na hasła, klucze i tokeny: zamiast nich `Hasło do X [hasło: gdzie je wpisać]`. Zadanie bez "
               "potrzebnych danych zostaje bez `pyta:` (właściciel kliknie tylko „Zrobione”).")


OWNER_RULES = [
    "- Właściciela angażuj tylko w sprawy, których nikt poza nim nie rozstrzygnie: pieniądze i koszty, dane prawne "
    "i firmowe, działania nieodwracalne albo wychodzące na zewnątrz, zakres i terminy projektu, rzeczy fizyczne "
    "(nagranie, urządzenie, dysk) i fakty znane tylko jemu. Resztę (definicje, nazwy, kolejność, sprawy techniczne, "
    "to, co sprawdzisz sam w plikach, repozytorium albo w sieci) rozstrzygnij sam: wybierz rozsądną, odwracalną "
    "opcję i dopisz ją na górze DECYZJE.md obok karty (`## RRRR-MM-DD: tytuł`, Kontekst, Decyzja, Skutki, "
    "`- Kto: agent`).",
    "- Najwyżej jedno otwarte pytanie do właściciela na projekt: gdy w sekcji „Pytania do właściciela” w KARTA.md "
    "jest już pytanie bez odpowiedzi, nie dodawaj nowego; przyjmij domyślną opcję i zapisz ją w DECYZJE.md.",
    "- `wymaga: odbiór` tylko wtedy, gdy praca wyjdzie na zewnątrz (post, wiadomość, materiał dla klienta), ma "
    "wiersz `decyzja:` albo zmienia kod do scalenia. Notatki, plany i analizy wewnętrzne kończ stanem `[x]`.",
]


def log(text):
    """Wpis do dziennika serwera. Pod pythonw stderr nie istnieje, więc zapis nie może przerwać pracy."""
    try:
        sys.stderr.write("%s %s\n" % (time.strftime("%H:%M:%S"), text))
        sys.stderr.flush()
    except (AttributeError, OSError, ValueError):
        pass


def now_iso(when=None):
    return (when or datetime.datetime.now()).isoformat(timespec="seconds")


def _int(value, default, low=1):
    try:
        return max(low, int(str(value).strip()))
    except (TypeError, ValueError):
        return default


def _short(text, limit):
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"


def child_env(base=None):
    """Środowisko procesu agenta: bez kluczy API i bez zmiennych sesji nadrzędnej, więc praca idzie na subskrypcję."""
    env = {}
    for key, value in (os.environ if base is None else base).items():
        up = key.upper()
        if up in ("CLAUDE_CODE_OAUTH_TOKEN", "CLAUDE_CONFIG_DIR"):
            env[key] = value
        elif up.startswith("ANTHROPIC_") or up.startswith("CLAUDE") or up in ("OPENAI_API_KEY", "PANEL_TOKEN", "PANEL_NTFY_URL"):
            continue
        else:
            env[key] = value
    return env


def stat_regular(st):
    return stat.S_ISREG(st.st_mode)


def _command(path):
    """Atrapy testowe to skrypty .py: uruchamiamy je bieżącym interpreterem (działa także na Windows)."""
    return [sys.executable, path] if path.lower().endswith(".py") else [path]


def describe_tool(name, data, cwd=""):
    """Czynność agenta w jednym wierszu: 'Edit: src/api.py', 'Bash: npm test'."""
    if name in ("TodoWrite", "TaskCreate", "TaskUpdate"):
        return {"TodoWrite": "Aktualizuje listę kroków", "TaskCreate": "Dodaje krok", "TaskUpdate": "Aktualizuje krok"}[name]
    detail = ""
    if isinstance(data, dict):
        for key in ("file_path", "path", "notebook_path"):
            if data.get(key):
                detail = str(data[key])
                if cwd and os.path.isabs(detail):
                    try:
                        rel = os.path.relpath(detail, cwd)
                        detail = rel if not rel.startswith("..") else os.path.basename(detail)
                    except ValueError:
                        detail = os.path.basename(detail)
                break
        else:
            for key in ("description", "command", "pattern", "url", "query", "prompt"):
                if data.get(key):
                    detail = str(data[key]).strip().split("\n")[0]
                    break
    return _short("%s: %s" % (name, detail) if detail else str(name), 120)


STANDARD_LINKS = ("KARTA.md", "ZADANIA.md", "DECYZJE.md")


def _card_dirs(folder):
    """--add-dir dla kart podpiętych dowiązaniem spoza folderu projektu (inaczej agent bez okna ich nie przeczyta)."""
    root = os.path.realpath(folder)
    dirs = []
    for name in STANDARD_LINKS:
        target = os.path.realpath(os.path.join(folder, name))
        where = os.path.dirname(target)
        if os.path.exists(target) and os.path.commonpath([root, target]) != root and where not in dirs:
            dirs.append(where)
    return [x for d in dirs for x in ("--add-dir", d)]


def drive_dir(folder):
    """Zamontowany Google Drive projektu (szkice/<karta>/media/drive, tylko do odczytu) albo ''."""
    try:
        cards = os.path.dirname(os.path.realpath(os.path.join(folder, "KARTA.md")))
    except (OSError, TypeError, ValueError):
        return ""
    mnt = os.path.join(cards, "media", "drive")
    return mnt if os.path.ismount(mnt) else ""


def drive_rules(mnt):
    """Zasada zadania z folderem Google Drive projektu."""
    if not mnt:
        return []
    return ["- Pliki projektu z Google Drive są w %s (tylko do odczytu, kopia folderu z Drive). Czytaj z nich i kopiuj "
            "potrzebne pliki do folderu projektu; nic tam nie zapisuj ani nie usuwaj." % mnt]


def notify_link(rec):
    """Adres w panelu dla powiadomienia o uruchomieniu: zadanie otwiera szczegóły zadania na stronie Asystent,
    raport PM stronę Asystent (notatka PM na starcie), plan dnia Agentów, reszta szczegóły uruchomienia w Agentach."""
    if rec.get("kind") == "task" and rec.get("taskId"):
        return "#asystent?z=" + str(rec["taskId"])
    if rec.get("kind") == "pm":
        return "#asystent"
    if rec.get("kind") == "plan":
        return "#agenci"
    return "#agenci?u=" + str(rec.get("id") or "") if rec.get("id") else "#agenci"


def click_url(link):
    """Pełny adres dla nagłówka Click: PANEL_PUBLIC_URL + link, tylko znaki ASCII; bez adresu publicznego pusty."""
    base = (os.environ.get("PANEL_PUBLIC_URL") or "").strip().rstrip("/")
    if not base or not link:
        return ""
    view, sep, query = link.partition("?")
    if sep:
        query = "&".join(k + "=" + urllib.parse.quote(v, safe="") for k, _, v in (x.partition("=") for x in query.split("&")))
    return base + "/" + urllib.parse.quote(view, safe="#") + (("?" + query) if sep else "")

AGENT_EXECUTORS = ("agent", "claude", "codex")


def projekt_counts(data, today):
    """Liczby spraw właściciela (projekt.owner_counts) z danych load_projects, gdy nie ma odpowiedzi /api/data."""
    std = os.path.join(ROOT, "standard")
    if std not in sys.path:
        sys.path.insert(0, std)
    import projekt  # noqa: E402  (ten sam moduł, którego używa serwer)
    return projekt.owner_counts(data["projects"], data.get("stages") or [], data["tasks"], today)


def pick_agent(task, code_repo, usage, reserve, available):
    """Wybór wykonawcy i powodu zapisywanego przy uruchomieniu."""
    executor = task.get("executor")
    if executor != "agent":
        return ("codex" if executor == "codex" else "claude"), ""
    title = task.get("title", "")
    writing = re.match(r"(?i)^(przeanalizuj|opisz|spisz|raport|analiza|przygotuj post)\b", title) or re.match(
        r"(?i)^(napisz|przygotuj|uzupełnij|zaktualizuj)\s+(raport|notatkę|opis|dokumentację|instrukcję|tekst|post)\b",
        title)
    code_words = re.search(r"(?i)\b(kod|testy|skrypt|repozytorium|implementac\w*|zaimplementuj|refaktoryzac\w*)\b", title)
    coding = title.startswith((strona.SITE_TASK, strona.CONCEPT_TASK)) or (
        code_repo and not writing and (task.get("machine") or code_words))
    primary, other = ("codex", "claude") if coding else ("claude", "codex")
    percent = usage.get(primary)
    if percent is not None and percent >= reserve and available.get(other) and (usage.get(other) or 0) < reserve:
        return other, "limit %s %d%%" % (primary.capitalize(), round(percent * 100))
    if not available.get(primary) and available.get(other):
        return other, "%s niedostępny" % primary.capitalize()
    return primary, "zmiana kodu" if coding else "pisanie, analiza lub raport"


def task_outcome(task):
    if not task:
        return "unknown"
    if task.get("state") == "done":
        return "done"
    if task.get("state") == "blocked" or task.get("blocked"):
        return "blocked"
    if "odbiór" in needs_of(task):
        return "review"
    return "unknown"


RUNNER = os.path.join(HERE, "przebieg.py")
RUN_PRIVATE = ("log", "runner", "logPos", "family", "startCommit")    # pola rekordu poza /api/data
RUNNER_FILES = (".log", ".wej", ".koniec", ".przebieg")      # pliki uruchomienia obok rekordu <id>.json
KILLED_CODES = (-15, -9, -1, 143, 137, 129, -1001)            # koniec sygnałem (restart, zatrzymanie usługi)
PARALLEL_MAX = 4            # najwięcej uruchomień naraz w ustawieniu panelu
PARTS_MAX = 4               # tyle części projektu dostaje katalog roboczy w jednym uruchomieniu
RECOVER_MAX = 2             # tyle razy z rzędu panel wznawia zadanie przerwane restartem


def pid_alive(pid, rid=""):
    """Czy proces o tym pid żyje (i, gdy podano rid, jest pośrednikiem tego uruchomienia)."""
    try:
        pid = int(pid)
        os.kill(pid, 0)
    except (TypeError, ValueError, OSError):
        return False
    if not rid:
        return True
    try:
        with open("/proc/%d/cmdline" % pid, "rb") as f:
            args = f.read().split(b"\0")
    except OSError:
        return sys.platform == "darwin"     # bez /proc (macOS): sam pid
    try:
        with open("/proc/%d/stat" % pid, "rb") as f:
            if f.read().rsplit(b")", 1)[-1].split()[0] == b"Z":
                return False                # zombie: proces już się skończył
    except (OSError, IndexError):
        pass
    return any(a.endswith(b"przebieg.py") for a in args) and rid.encode() in args


class _Inbox:
    """stdin agenta za pośrednikiem: dopisywanie do <id>.wej (wiersze JSON)."""

    def __init__(self, path):
        self.path = path
        self.closed = False

    def _put(self, msg):
        if self.closed:
            raise ValueError("wejście zamknięte")
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(msg, ensure_ascii=False) + "\n")

    def write(self, text):
        self._put({"d": text})

    def flush(self):
        pass

    def close(self):
        if not self.closed:
            try:
                self._put({"zamknij": True})
            except OSError:
                pass
            self.closed = True


class Detached:
    """Uruchomienie za pośrednikiem (przebieg.py) z interfejsem Popen: pid (grupa procesów), stdin, stdout (wiersze
    z <id>.log od miejsca `pos`), poll(), wait(). Działa też po restarcie panelu (proc=None: pośrednik nie jest
    dzieckiem tego procesu)."""

    def __init__(self, runs_dir, rid, pid, proc=None, pos=0):
        self.base = os.path.join(runs_dir, rid)
        self.rid, self.pid, self.proc, self.pos = rid, int(pid), proc, int(pos or 0)
        self.abandoned = False          # panel kończy pracę: przestaje czytać, uruchomienie pracuje dalej
        self.stdin = _Inbox(self.base + ".wej")
        self.stdout = self._lines()
        self.returncode = None

    def _end(self):
        try:
            with open(self.base + ".koniec", encoding="utf-8") as f:
                data = json.load(f)
            return int(data.get("code"))
        except (OSError, ValueError, TypeError, AttributeError):
            return None

    def poll(self):
        if self.returncode is not None:
            return self.returncode
        if self.proc is not None and self.proc.poll() is None:
            return None
        code = self._end()
        if code is None and self.proc is None and pid_alive(self.pid, self.rid):
            return None
        if code is None:
            code = self._end()          # pośrednik zapisał koniec między odczytami
        self.returncode = -1001 if code is None else code     # pośrednik zniknął bez zapisu końca
        return self.returncode

    def wait(self, timeout=None):
        end = None if timeout is None else time.time() + timeout
        while self.poll() is None:
            if end is not None and time.time() > end:
                raise subprocess.TimeoutExpired("przebieg", timeout)
            time.sleep(0.2)
        return self.returncode

    def _lines(self):
        buf = b""
        f = None
        try:
            while not self.abandoned:
                if f is None:
                    try:
                        f = open(self.base + ".log", "rb")
                        f.seek(self.pos)
                    except OSError:
                        f = None
                chunk = f.read(65536) if f else b""
                if chunk:
                    buf += chunk
                    while b"\n" in buf:
                        line, buf = buf.split(b"\n", 1)
                        self.pos += len(line) + 1
                        yield line.decode("utf-8", "replace") + "\n"
                    continue
                if self.poll() is not None:
                    rest = f.read() if f else b""
                    buf += rest
                    for line in buf.split(b"\n"):
                        if line:
                            self.pos += len(line)
                            yield line.decode("utf-8", "replace") + "\n"
                    return
                time.sleep(0.2)
        finally:
            if f:
                f.close()

    def abandon(self):
        self.abandoned = True

    def kill(self):
        try:
            os.killpg(self.pid, signal.SIGKILL)
        except OSError:
            pass

    def close(self):
        self.stdout.close()


class Manager:
    """Kolejka i przebieg uruchomień jednego węzła."""

    def __init__(self, load_projects, write_lock, projekt, env=None, runs_dir=None, root=None, notes_dir=None):
        self.load_projects = load_projects
        self.write_lock = write_lock
        self.projekt = projekt
        self.env = dict(os.environ if env is None else env)
        get = self.env.get
        self.root = root or ROOT
        self.runs_dir = runs_dir or get("PANEL_RUNS_DIR") or os.path.join(self.root, "uruchomienia")
        self.notes_dir = notes_dir or os.path.join(self.root, "raporty")
        machine = (get("PANEL_MACHINE") or ("mac" if sys.platform == "darwin" else "pc")).strip().lower()
        self.machine = projekt.WHERE.get(machine, machine)
        # Zadania bez „gdzie:” bierze Automat węzła domyślnego (po D13 serwer). Mac domyślnie nie.
        default = (get("PANEL_DEFAULT_NODE") or "").strip()
        self.default_node = default == "1" if default in ("0", "1") else self.machine != "mac"
        self.max_parallel = _int(get("PANEL_AGENTS_MAX"), 2)     # bez ustawienia w panelu (stan.json parallel)
        self.deploy_file = (get("PANEL_WDROZENIE_DIR") or "").strip() or os.path.expanduser("~/dane/wdrozenie")
        self.deploy_file = os.path.join(self.deploy_file, "stan.json")
        self._hold = (0.0, False)
        self.timeout = _int(get("PANEL_AGENT_TIMEOUT"), 3600)
        # bezpiecznik zużycia: limit 5 godzin subskrypcji (rate_limit_event w strumieniu claude, ułamek 0–1)
        self.run_budget = max(0.02, min(1.0, _int(get("PANEL_RUN_BUDGET_PROC"), 20) / 100.0))   # jedno uruchomienie
        self.auto_reserve = max(0.1, min(1.0, _int(get("PANEL_AUTOMAT_DO_PROC"), 80) / 100.0))  # Automat do tylu %
        self._usage = {"five": None, "seven": None, "at": 0.0, "resetsAt": None}
        self._codex_usage = {"five": None, "seven": None, "at": 0, "resetsAt": None}
        self._session_limits_at = 0
        self._limit_reader_lock = threading.Lock()
        development_dir = get("PANEL_ROZWOJ_DIR", "/home/agent/rozwoj" if self.machine == "cloud" else "")
        self.orders = agent_progress.Orders(development_dir.strip(), describe_tool)
        self.model = (get("PANEL_AGENT_MODEL") or "").strip()
        self.pm_model = (get("PANEL_PM_MODEL") or "").strip()
        # Stały rytm postów: "projekt=dni,projekt=dni". Automat zakłada zadanie „Przygotować post na …”.
        self.rytm = {}
        for part in (get("PANEL_RYTM") or "").split(","):
            pid, _, days = part.partition("=")
            if pid.strip() and days.strip().isdigit() and int(days) > 0:
                self.rytm[pid.strip()] = int(days)
        self.pm_hour = _int(get("PANEL_PM_HOUR"), 7, low=0)
        self.git_pull = (get("PANEL_GIT_PULL") or "").strip() == "1"
        # Zadanie w repozytorium git: katalog roboczy i gałąź zakłada panel (AGENCI.md, „Gałąź uruchomienia”).
        self.worktrees = (get("PANEL_AGENT_WORKTREE") or "1").strip() != "0"
        # Agenci jako osobny użytkownik systemu: sudo -n -u <użytkownik> -- polecenie.
        self.agent_user = (get("PANEL_AGENT_USER") or "").strip()
        self.ntfy_url = (get("PANEL_NTFY_URL") or "").strip()
        self.tick_seconds = 60

        self._lock = threading.RLock()        # rekordy, kolejka, procesy, stan
        self._start_lock = threading.Lock()   # jedno przyjmowanie zadania naraz (może potrwać: git pull)
        self._runs = collections.OrderedDict()
        self._queue = []
        self._priv = {}                       # id -> dane robocze, których nie pokazujemy (folder, prompt, proces)
        self._state = {"automat": False, "needsLogin": False, "limitUntil": None, "since": {}, "marks": {},
                       "sessionKey": "", "rytmDone": [], "decisions": {}}
        self._shot_dirs = {}                  # id uruchomienia zadania strony -> katalog .zrzuty/ (GET /api/agent/zrzut)
        self._seen_marks = {}                 # klucz zadania -> stan z ostatniego track_marks (zmiany widziane na żywo)
        self._tools = {"claude": self._tool_blank(), "codex": self._tool_blank()}
        self._tools_at = 0.0
        self._tools_read = False              # stan narzędzi odczytany choć raz (grafiki: „Codex niezalogowany”)
        self._tools_busy = False
        self._tools_ready = threading.Event()
        self._login = None          # logowanie przez panel (serwer bez okna): proces, adres, stan
        self._cx_login = None       # logowanie Codex kodem urządzenia (serwer bez okna): proces, adres, kod
        self.login_web = (get("PANEL_LOGIN_WEB") or "").strip() == "1" or not (sys.platform == "darwin" or WINDOWS)
        self.launcher = lambda args, **kw: subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                                            stderr=subprocess.DEVNULL, **kw)
        self._stop_event = threading.Event()
        self._thread = None
        self._closing = False                 # panel kończy pracę: uruchomienia za pośrednikiem zostają
        self._git_lock = threading.Lock()     # operacje panelu na repozytoriach projektów (worktree, commit, merge)
        self._ver_lock = threading.Lock()     # zapis i porządki wersji wyniku (strona odbioru)
        self.chat_timeout = 180               # s: odpowiedź w rozmowie (Rozmowa w projekcie)
        self.assist_model = (get("PANEL_ASYSTENT_MODEL") or "sonnet").strip()  # tańszy model dla asystenta
        self._chat_lock = threading.Lock()    # pliki rozmów i _chat_live
        self._chat_live = set()               # pliki rozmów, które czekają na odpowiedź w tym procesie
        self._chat_meta = {}                  # plik rozmowy -> zadanie i czas pytania (widok Teraz w panelu)
        self._chat_done = []                  # zakończone rozmowy (Teraz → Ostatnie 24 h), najnowsze na końcu
        self._as = asystent.Session(idle=_int(get("PANEL_ASYSTENT_BEZCZYNNOSC"), asystent.IDLE),
                                    on_rate=self._claude_limit_event)
        self._as_live = {"partial": "", "activity": ""}   # odpowiedź asystenta w trakcie pisania
        self._as_facts = ""                   # skrót faktów wysłanych w tej sesji (nowe fakty tylko po zmianie danych)
        self._as_lib = ""                     # skrót listy kart wysłanej w tej sesji
        # internet dla asystenta (karty news): WebSearch i WebFetch tylko do odczytu; PANEL_ASYSTENT_INTERNET=0 wyłącza
        self.assist_web = (get("PANEL_ASYSTENT_INTERNET") or "1").strip() != "0"
        if self.assist_web:
            self.ASSIST_DENY = ",".join(x for x in self.ASSIST_DENY.split(",") if x not in self.ASSIST_WEB)
        self.cards = karty.Library((get("PANEL_ASYSTENT_KARTY") or "").strip() or
                                   os.path.join(self.runs_dir, "czat", "asystent-karty.json"))
        self.voice = glos.Recognizer(self.env, idle=_int(get("PANEL_GLOS_BEZCZYNNOSC"), glos.GLOS_IDLE))
        self.site = strona.Site(self)         # podgląd strony WWW projektów z polem karty strona:
        self._load()
        self._chat_restore()
        self._login_sent = self._state["needsLogin"]     # stan sprzed restartu nie wysyła powiadomienia drugi raz

    # ---------- narzędzia (claude, codex) ----------
    @staticmethod
    def _tool_blank():
        return {"found": False, "version": "", "loggedIn": False, "subscription": "", "loginCmd": ""}

    @staticmethod
    def login_cmd(tool, path):
        """Polecenie logowania do wklejenia w terminalu. Pełna ścieżka, bo powłoka właściciela nie zawsze ma
        narzędzie w PATH (instalator Claude Code kładzie je w ~/.local/bin)."""
        args = "login" if tool == "codex" else "auth login"
        if not path or path.lower().endswith(".py"):
            return "%s %s" % (tool, args)
        if WINDOWS:
            return '& "%s" %s' % (path, args)                # PowerShell
        home = os.path.expanduser("~")
        shown = "~" + path[len(home):] if path.startswith(home + os.sep) else path
        if re.search(r"[^\w@%+=:,./~-]", shown):
            shown = shlex.quote(path)                        # w cudzysłowie ~ się nie rozwija: pełna ścieżka
        return "%s %s" % (shown, args)

    def tool_path(self, tool):
        """Ścieżka polecenia albo ''. PANEL_CLAUDE / PANEL_CODEX, potem PATH, dla Claude także ~/.local/bin."""
        explicit = (self.env.get("PANEL_CLAUDE" if tool == "claude" else "PANEL_CODEX") or "").strip()
        if explicit:
            explicit = os.path.expanduser(explicit)
            return explicit if os.path.isfile(explicit) else (shutil.which(explicit, path=self.env.get("PATH")) or "")
        found = shutil.which(tool, path=self.env.get("PATH"))
        if found:
            return found
        if tool == "claude":
            for name in (("claude.exe", "claude.cmd") if WINDOWS else ("claude",)):
                guess = os.path.join(os.path.expanduser("~"), ".local", "bin", name)
                if os.path.isfile(guess):
                    return guess
        return ""

    def as_agent(self, args):
        """Polecenie agenta: przy PANEL_AGENT_USER przez sudo -n -u <użytkownik> -- (bez hasła; brak zgody w sudoers
        kończy się błędem, nie pytaniem)."""
        if self.agent_user and not WINDOWS:
            return ["sudo", "-n", "-u", self.agent_user, "--"] + list(args)
        return list(args)

    def _probe(self, args, timeout=20):
        args = self.as_agent(args)          # stan logowania tego użytkownika, który uruchamia agentów
        try:
            p = subprocess.run(args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               env=child_env(self.env), timeout=timeout, encoding="utf-8", errors="replace",
                               **NO_WINDOW)
            return p.returncode, p.stdout or ""
        except (OSError, subprocess.SubprocessError):
            return -1, ""

    def _read_tools(self):
        out = {}
        for tool in ("claude", "codex"):
            info = self._tool_blank()
            path = self.tool_path(tool)
            info["loginCmd"] = self.login_cmd(tool, path)
            if path:
                info["found"] = True
                _, text = self._probe(_command(path) + ["--version"])
                m = re.search(r"\d+\.\d+\.\d+", text)
                info["version"] = m.group(0) if m else ""
                if tool == "claude":
                    _, text = self._probe(_command(path) + ["auth", "status"])
                    try:
                        data = json.loads(text[text.index("{"):text.rindex("}") + 1])
                        info["loggedIn"] = bool(data.get("loggedIn"))
                        info["subscription"] = str(data.get("subscriptionType") or "")
                    except (ValueError, AttributeError):
                        pass
                else:
                    code, text = self._probe(_command(path) + ["login", "status"])
                    low = text.lower()
                    info["loggedIn"] = code == 0 and "logged in" in low and "not logged in" not in low
                    info["subscription"] = "chatgpt" if info["loggedIn"] and "chatgpt" in low else ""
            out[tool] = info
        return out

    def refresh_tools(self, force=False, wait=False):
        """Odczyt stanu narzędzi w tle, najwyżej raz na TOOLS_TTL sekund. Nigdy nie blokuje (poza wait=True w testach)."""
        with self._lock:
            reading = self._tools_busy
            if not reading and not force and time.time() - self._tools_at < TOOLS_TTL:
                return
            if not reading:
                self._tools_busy = True
                self._tools_ready.clear()
        if reading:
            if wait:
                self._tools_ready.wait()
            return

        def work():
            try:
                tools = self._read_tools()
                with self._lock:
                    self._tools, self._tools_at, self._tools_read = tools, time.time(), True
                self._login_alert()
            finally:
                with self._lock:
                    self._tools_busy = False
                    self._tools_ready.set()

        if wait:
            work()
        else:
            threading.Thread(target=work, daemon=True).start()

    def tool_found(self, tool):
        """Szybkie sprawdzenie bez uruchamiania procesu (do reguł runBlock)."""
        return bool(self.tool_path(tool))

    # ---------- zapis na dysk ----------
    def _write_json(self, path, data):
        os.makedirs(self.runs_dir, exist_ok=True)
        tmp = "%s.tmp-%s" % (path, uuid.uuid4().hex[:6])
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        os.replace(tmp, path)

    def _save(self, rec):
        try:
            self._write_json(os.path.join(self.runs_dir, rec["id"] + ".json"), rec)
        except OSError:
            pass

    def _save_state(self):
        try:
            with self._lock:
                self._write_json(os.path.join(self.runs_dir, "stan.json"),
                                 dict(self._state, limits={"claude": self._usage, "codex": self._codex_usage}))
        except OSError:
            pass

    def _load(self):
        """Wczytuje ostatnie rekordy; starsze niż KEEP usuwa; przerwane restartem oznacza jako zatrzymane."""
        try:
            names = sorted(n for n in os.listdir(self.runs_dir) if n.endswith(".json") and n not in NOT_RUNS)
        except OSError:
            names = []
        for name in names[:-KEEP] if len(names) > KEEP else []:
            self._remove_files(name[:-5])
        self._interrupted = []
        for name in names[-KEEP:]:
            try:
                with open(os.path.join(self.runs_dir, name), encoding="utf-8") as f:
                    rec = json.load(f)
            except (OSError, ValueError):
                continue
            if not isinstance(rec, dict) or rec.get("id") != name[:-5]:
                continue
            if rec.get("state") == "running" and rec.get("kind") == "task" or \
                    rec.get("state") == "running" and (rec.get("runner") or {}).get("pid"):
                self._interrupted.append(rec)          # start(): podjęcie śledzenia albo dokończenie
            elif rec.get("state") in LIVE:
                rec.update(state="stopped", error="Serwer został zatrzymany.", endedAt=now_iso(), activity="")
                self._save(rec)
                self._interrupted.append(rec)
            self._runs[rec["id"]] = rec
            read_at, amount, reset = rec.get("limitReadAt"), rec.get("limitNow"), rec.get("limitReset")
            if rec.get("tool") == "codex" and isinstance(read_at, (int, float)) and isinstance(amount, (int, float)) \
                    and read_at > self._codex_usage["at"]:
                self._codex_usage.update(five=amount, at=read_at,
                                         resetsAt=reset if isinstance(reset, (int, float)) else None)
        try:
            with open(os.path.join(self.runs_dir, "stan.json"), encoding="utf-8") as f:
                saved = json.load(f)
            for tool, target in (("claude", self._usage), ("codex", self._codex_usage)):
                windows = (saved.get("limits") or {}).get(tool) or {}
                for key, at, reset in (("five", "at", "resetsAt"), ("seven", "sevenAt", "sevenReset")):
                    value, stamp = windows.get(key), windows.get(at)
                    if isinstance(value, (int, float)) and 0 <= value <= 1 and isinstance(stamp, (int, float)) \
                            and stamp > target.get(at, 0):
                        target.update({key: value, at: stamp, reset: agent_progress.reset_time(windows.get(reset))})
            decisions = saved.get("decisions")
            if isinstance(decisions, dict):
                self._state["decisions"] = {key: v for key, v in decisions.items()
                                            if isinstance(v, dict) and v.get("day") == now_iso()[:10]}
            self._state["automat"] = saved.get("automat") is True
            if isinstance(saved.get("naprawy"), list):
                self._state["naprawy"] = [x for x in saved["naprawy"] if isinstance(x, str)][-50:]
            if isinstance(saved.get("parallel"), int) and 1 <= saved["parallel"] <= PARALLEL_MAX:
                self._state["parallel"] = saved["parallel"]
                self.max_parallel = saved["parallel"]
            self._state["needsLogin"] = saved.get("needsLogin") is True
            self._state["limitUntil"] = saved.get("limitUntil") if isinstance(saved.get("limitUntil"), str) else None
            since = saved.get("since")
            self._state["since"] = {k: v for k, v in since.items() if isinstance(k, str) and isinstance(v, dict)
                                    and isinstance(v.get("s"), str) and isinstance(v.get("d"), str)} \
                if isinstance(since, dict) else {}
            marks = saved.get("marks")
            self._state["marks"] = {k: v for k, v in marks.items() if isinstance(k, str) and isinstance(v, dict)
                                    and v.get("s") in ("done", "blocked") and isinstance(v.get("d"), str)} \
                if isinstance(marks, dict) else {}
            key = saved.get("sessionKey")
            self._state["sessionKey"] = key if isinstance(key, str) and re.match(r"^[0-9a-f]{32,128}$", key) else ""
            done = saved.get("rytmDone")
            self._state["rytmDone"] = [x for x in done if isinstance(x, str)][-RYTM_KEEP:] if isinstance(done, list) else []
            ways = saved.get("filmWays")
            self._state["filmWays"] = {k: v for k, v in list(ways.items())[-400:] if isinstance(k, str)
                                       and v in scenariusz.WAYS} if isinstance(ways, dict) else {}
        except (OSError, ValueError, AttributeError):
            pass

    def _remove_files(self, rid):
        for ext in (".json",) + RUNNER_FILES:
            try:
                os.remove(os.path.join(self.runs_dir, rid + ext))
            except OSError:
                pass

    def _trim(self):
        with self._lock:
            extra = len(self._runs) - KEEP
            for rid in [r for r, rec in self._runs.items() if rec["state"] not in LIVE][:max(0, extra)]:
                del self._runs[rid]
                self._shot_dirs.pop(rid, None)
                self._remove_files(rid)

    # ---------- wątek Automatu ----------
    def start(self):
        """Uruchamia wątek Automatu i porządkuje zadania po uruchomieniach przerwanych restartem."""
        for rec in self._interrupted:
            if rec.get("state") == "running":
                try:
                    self._resume_after_restart(rec)
                except Exception as e:
                    log("Uruchomienie %s po restarcie: %s" % (rec["id"], e))
                continue
            if rec.get("kind") == "task":
                self._settle_task(rec, rec["state"])
                try:
                    git = self._worktree_info(rec)
                    if git:
                        self._worktree_close(rec, git)
                except Exception as e:
                    log("Gałąź uruchomienia %s: %s" % (rec["id"], e))
        self._interrupted = []
        if self.machine == "cloud" and (self.env.get("PANEL_NAPRAWY") or "1").strip() != "0":
            naprawy.start(self)                 # jednorazowe naprawy (dashboard/naprawy.py) w tle
        if self._thread is None:
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()
        self.refresh_tools()

    def _loop(self):
        while not self._stop_event.wait(self.tick_seconds):
            try:
                self.tick()
            except Exception as e:  # wątek ma przeżyć błąd jednego obiegu
                log("Automat: %s" % e)

    def shutdown(self, wait=8, keep=False):
        """Zatrzymuje wątek i wszystkie procesy (koniec pracy serwera, testy). Czeka, aż rekordy zostaną zamknięte.
        keep (koniec pracy serwera): uruchomienia za pośrednikiem pracują dalej; panel po starcie je podejmie."""
        if getattr(self, "_shut", False):
            return
        if keep:
            self._closing = True
            self._shut = True
        if self._login:
            self._login_stop(self._login)
        self._stop_event.set()
        self._as.stop()
        self.voice.stop()
        with self._lock:
            kept = {rid for rid, p in self._priv.items() if keep and isinstance(p.get("proc"), Detached)}
            ids = [rid for rid, rec in self._runs.items() if rec["state"] in LIVE and rid not in kept]
            procs = [p["proc"] for rid, p in self._priv.items() if p.get("proc") is not None and rid not in kept]
            for rid in kept:
                self._priv[rid]["proc"].abandon()
                self._save(self._runs[rid])     # miejsce w przebiegu (logPos) dla podjęcia po starcie
        for rid in ids:
            self.stop(rid)
        end = time.time() + wait
        while time.time() < end:
            with self._lock:
                if not any(rec["state"] in LIVE for rid, rec in self._runs.items() if rid not in kept):
                    break
            time.sleep(0.05)
        for proc in procs:                      # proces, który nie zareagował na SIGTERM
            if proc.poll() is None:
                try:
                    if WINDOWS:
                        proc.kill()
                    else:
                        os.killpg(proc.pid, signal.SIGKILL)
                except OSError:
                    pass

    def has_live(self, project):
        """Czy projekt ma uruchomienie w kolejce albo w toku."""
        with self._lock:
            return any(r["project"] == project and r["state"] in LIVE for r in self._runs.values())

    # ---------- reguły ----------
    def _task_category(self, task, project, folder):
        if task.get("title", "").startswith((strona.SITE_TASK, strona.CONCEPT_TASK)):
            return "site"
        repo = bool(project.get("github") or (folder and self._git_top(folder)))
        tool, _ = pick_agent(dict(task, executor="agent"), repo, {}, self.auto_reserve, {})
        return "repo" if repo and tool == "codex" else "text"

    def _eligible_tools(self, task, usage):
        pin = (task.get("detail") or {}).get("executorPin")
        available = {}
        with self._lock:
            for tool, prefix in (("claude", ""), ("codex", "codex")):
                info = self._tools.get(tool) or {}
                keys = (prefix + "Five", prefix + "Seven") if prefix else ("five", "seven")
                available[tool] = (self.tool_found(tool)
                                   and pin in (None, "", "tylko " + tool)
                                   and not (info.get("found") and not info.get("loggedIn"))
                                   and not (tool == "claude" and (self._state["needsLogin"] or self.limit_until()))
                                   and all((usage.get(key) or 0) < self.auto_reserve for key in keys))
        return [tool for tool, allowed in available.items() if allowed]

    def choose_task_tool(self, task, project, folder, decide=False):
        usage = self.usage_state()
        if decide:
            self.refresh_tools(wait=True)
        eligible = self._eligible_tools(task, usage)
        if not eligible:
            return "", "Żaden dozwolony wykonawca nie ma dostępu lub wolnego limitu."
        cost = {}
        day = now_iso()[:10]
        pin = (task.get("detail") or {}).get("executorPin")
        key = self.projekt.task_key(task)
        with self._lock:
            saved = self._state["decisions"].get(key) or {}
        if (saved.get("day") == day and saved.get("pin") == pin
                and saved.get("tool") in eligible and saved.get("reason")):
            return saved["tool"], saved["reason"]
        hint = task.get("executor")
        repo = bool(project.get("github") or (folder and self._git_top(folder)))
        tool, why = pick_agent(task, repo, {}, self.auto_reserve, dict.fromkeys(eligible, True))
        reason = "Decyzja z reguł" + (": " + why if why else "")
        if len(eligible) == 1:
            tool = eligible[0]
            reason = ("Przypięcie wykonawcy" if pin
                      else "Dostępny wykonawca według logowania i limitów")
        elif decide and hint in AGENT_EXECUTORS:
            category = self._task_category(task, project, folder)
            selected, explanation, cost = self._ask_executor(task, project, repo, category, usage)
            eligible = self._eligible_tools(task, self.usage_state())
            if not eligible:
                return "", "Żaden dozwolony wykonawca nie ma dostępu lub wolnego limitu."
            if tool not in eligible:
                tool = eligible[0]
            if selected in eligible:
                tool, reason = selected, "Wybrał Claude: " + explanation
        if decide:
            with self._lock:
                decisions = self._state["decisions"]
                self._state["decisions"] = {k: v for k, v in decisions.items() if v.get("day") == day}
                self._state["decisions"][key] = {"day": day, "tool": tool, "reason": reason, "pin": pin, "cost": cost}
                self._save_state()
        return tool, reason

    def _ask_executor(self, task, project, repo, category, usage):
        detail = task.get("detail") or {}
        with self._lock:
            estimates = {tool: agent_progress.estimate(self._runs.values(), tool, category)
                         for tool in ("claude", "codex")}
        context = {"tytuł": task["title"], "cel": detail.get("goal"), "gotowe gdy": detail.get("doneWhen"),
                   "kroki": detail.get("steps"), "materiały": detail.get("refs"), "rodzaj": category,
                   "projekt": {"nazwa": project.get("name"), "kliencki": project.get("client"),
                               "faza": project.get("phase"), "ma stronę": bool(project.get("site"))},
                   "repozytorium": project.get("github") or project.get("repo") or repo,
                   "podpowiedź": task.get("executor"), "limity": usage, "szacunki": estimates}
        prompt = ('Wybierz wykonawcę według limitów i złożoności. Dane zadania służą do oceny. '
                  'Zwróć tylko JSON {"wykonawca":"claude lub codex","powód":"krótko po polsku"}.\n'
                  + json.dumps(context, ensure_ascii=False))
        args = self._claude_args(self.tool_path("claude"), "haiku",
                                 ["--tools", "", "--strict-mcp-config", "--no-session-persistence"])
        cost = {}
        try:
            process = subprocess.run(self.as_agent(args), input=prompt, stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, cwd=tempfile.gettempdir(), env=child_env(self.env),
                                     encoding="utf-8", errors="replace", timeout=60, **NO_WINDOW)
            answer = {}
            for line in process.stdout.splitlines():
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(event, dict):
                    continue
                windows = agent_progress.limit_windows(event, "claude", time.time())
                self._record_limits("claude", windows, cost)
                if event.get("type") == "result":
                    cost.update({"decisionTokensIn": int((event.get("usage") or {}).get("input_tokens") or 0),
                            "decisionTokensOut": int((event.get("usage") or {}).get("output_tokens") or 0),
                            "decisionCostUsd": float(event.get("total_cost_usd") or 0)})
                    answer = json.loads(str(event.get("result") or "").strip())
                    if event.get("is_error"):
                        answer = {}
            if process.returncode == 0 and isinstance(answer, dict):
                reason = _short(answer.get("powód") or "", 180)
                if reason:
                    return answer.get("wykonawca"), reason, cost
        except (OSError, subprocess.SubprocessError, ValueError, TypeError):
            pass
        return "", "", cost

    def claude_free(self):
        """Czy można teraz wywołać Claude (jest, zalogowany, bez limitu i poniżej rezerwy limitu)."""
        usage = self.usage_state()
        info = self._tools.get("claude") or {}
        return (self.tool_found("claude") and not (info.get("found") and not info.get("loggedIn"))
                and not self._state["needsLogin"] and not self.limit_until()
                and all((usage.get(k) or 0) < self.auto_reserve for k in ("five", "seven")))

    def ask_fields(self, items):
        """Pola formularza dla zadań właściciela (pola.PROMPT, Claude Haiku, jedno wywołanie):
        {n: "Etykieta [typ]; …" albo ""} albo None, gdy model jest niedostępny albo odpowiedź jest zła."""
        if not items or not self.claude_free():
            return None
        prompt = pola.PROMPT + json.dumps(items, ensure_ascii=False)
        args = self._claude_args(self.tool_path("claude"), "haiku",
                                 ["--tools", "", "--strict-mcp-config", "--no-session-persistence"])
        try:
            process = subprocess.run(self.as_agent(args), input=prompt, stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, cwd=tempfile.gettempdir(), env=child_env(self.env),
                                     encoding="utf-8", errors="replace", timeout=90, **NO_WINDOW)
        except (OSError, subprocess.SubprocessError):
            return None
        answer = None
        for line in process.stdout.splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if not isinstance(event, dict):
                continue
            self._record_limits("claude", agent_progress.limit_windows(event, "claude", time.time()), {})
            if event.get("type") == "result" and not event.get("is_error"):
                text = str(event.get("result") or "").strip()
                text = text[text.find("{"):text.rfind("}") + 1] if "{" in text else ""
                try:
                    answer = json.loads(text)
                except ValueError:
                    answer = None
        if process.returncode != 0 or not isinstance(answer, dict) or not isinstance(answer.get("zadania"), list):
            return None
        out = {}
        for z in answer["zadania"]:
            if isinstance(z, dict) and isinstance(z.get("n"), int) and isinstance(z.get("pyta", ""), str):
                out[z["n"]] = z.get("pyta", "")
        return out

    def auto_task_ready(self, task, project, folder, claude_paused):
        tool, _ = self.choose_task_tool(task, project, folder)
        return bool(tool) and (tool != "claude" or not claude_paused)

    def limit_until(self):
        """Aktywny limit jako tekst ISO albo None (miniony limit jest zdejmowany)."""
        with self._lock:
            value = self._state["limitUntil"]
            if value and value <= now_iso():
                self._state["limitUntil"] = value = None
                self._save_state()
            return value

    def _live_keys(self):
        with self._lock:
            return {(r["project"], r["file"], r["title"]): r["id"] for r in self._runs.values()
                    if r["kind"] == "task" and r["state"] in LIVE}

    def run_block(self, task, source, live=None, tools=None):
        """Powód, dla którego zadania nie da się uruchomić; '' gdy można. Kolejność jak w AGENCI.md."""
        return run_block(task, source, self._live_keys() if live is None else live,
                         tools or {"claude": self.tool_found("claude"), "codex": self.tool_found("codex")})

    def annotate(self, tasks, source, today=None):
        """Dopisuje do zadań runId, runBlock, stateSince, stalled i reviewOverdue (projekt.state_flags)."""
        live = self._live_keys()
        tools = {"claude": self.tool_found("claude"), "codex": self.tool_found("codex")}
        today = today or datetime.date.today()
        since = self.track_states(tasks, today) if source == "registry" else {}
        marks = self.track_marks(tasks, today) if source == "registry" else {}
        for t in tasks:
            t["runId"] = live.get((t["project"], t["file"], t["title"]), "")
            t["runBlock"] = run_block(t, source, live, tools)
            k = self.projekt.task_key(t)
            t["stateSince"] = since.get(k, "")
            mark = marks.get(k) or ("", "")
            t["doneAt"] = mark[1] if mark[0] == "done" else ""
            t["blockedSince"] = mark[1] if mark[0] == "blocked" else ""
            t["stalled"], t["reviewOverdue"] = self.projekt.state_flags(t, t["stateSince"], bool(t["runId"]), today)

    def track_states(self, tasks, today):
        """Od kiedy zadanie jest w toku ([~] bez odbioru) albo czeka na odbiór: {klucz: "RRRR-MM-DD"}.

        Zapis w stan.json (pole since). Nowe zadanie w takim stanie dostaje dzień zakończenia ostatniego
        uruchomienia agenta dla tego zadania, a bez uruchomienia dzisiejszy dzień. Zadania w innym stanie znikają."""
        with self._lock:
            old = self._state.get("since") or {}
            ended = {}
            for r in self._runs.values():
                if r.get("kind") == "task" and r.get("endedAt"):
                    k = "%s|%s|%s" % (r["project"], r["file"], r["title"])
                    ended[k] = max(ended.get(k, ""), str(r["endedAt"])[:10])
            new = {}
            for t in tasks:
                status = self.projekt.task_status(t)
                if not status:
                    continue
                k = self.projekt.task_key(t)
                prev = old.get(k)
                if isinstance(prev, dict) and prev.get("s") == status:
                    new[k] = prev
                else:
                    new[k] = {"s": status, "d": min(ended.get(k) or today.isoformat(), today.isoformat())}
            if new != old:
                self._state["since"] = new
                self._save_state()
            return {k: v["d"] for k, v in new.items()}

    def track_marks(self, tasks, today):
        """Od kiedy zadanie jest zrobione ([x]) albo zablokowane ([!] / blokada:): {klucz: (stan, "RRRR-MM-DD")}.

        Zapis w stan.json (pole marks, tylko znane daty). Zmianę stanu widzianą przez panel (poprzednio inny stan
        w tym procesie albo w stan.json) liczy od dziś. Zadanie zastane w tym stanie dostaje dzień zakończenia
        ostatniego uruchomienia agenta dla zadania, a bez uruchomienia "" (nieznana). Wpisy zrobionych starsze
        niż MARKS_KEEP_DAYS dni nie są przechowywane."""
        with self._lock:
            old = self._state.get("marks") or {}
            since = self._state.get("since") or {}
            seen = self._seen_marks
            ended = {}
            for r in self._runs.values():
                if r.get("kind") == "task" and r.get("endedAt"):
                    k = "%s|%s|%s" % (r["project"], r["file"], r["title"])
                    ended[k] = max(ended.get(k, ""), str(r["endedAt"])[:10])
            cutoff = (today - datetime.timedelta(days=MARKS_KEEP_DAYS)).isoformat()
            day = today.isoformat()
            new, out, now_seen = {}, {}, {}
            for t in tasks:
                k = self.projekt.task_key(t)
                status = mark_status(t)
                now_seen[k] = status
                if status == "open":
                    continue
                prev = old.get(k)
                if isinstance(prev, dict) and prev.get("s") == status:
                    d = prev["d"]
                else:
                    before = seen.get(k) or (prev.get("s") if isinstance(prev, dict) else "") or \
                        ("open" if k in since else None)
                    if before is not None and before != status:
                        d = day                                        # zmiana widziana przez panel
                    else:
                        d = min(ended.get(k) or "", day)               # zastane: koniec uruchomienia albo ""
                out[k] = (status, d)
                if d and not (status == "done" and d < cutoff):
                    new[k] = {"s": status, "d": d}
            self._seen_marks = now_seen
            if new != old:
                self._state["marks"] = new
                self._save_state()
            return out

    # ---------- sesje panelu (server.py) ----------
    def session_key(self):
        """Losowy klucz sesji z stan.json; powstaje przy pierwszym użyciu."""
        with self._lock:
            if not self._state.get("sessionKey"):
                self._state["sessionKey"] = uuid.uuid4().hex + uuid.uuid4().hex
                self._save_state()
            return self._state["sessionKey"]

    def reset_sessions(self):
        """Nowy klucz sesji: wszystkie dotychczasowe ciasteczka przestają działać."""
        with self._lock:
            self._state["sessionKey"] = uuid.uuid4().hex + uuid.uuid4().hex
            self._save_state()
        return 200, "", {}

    # ---------- dane dla /api/data ----------
    def snapshot(self, data=None, index=None):
        self.refresh_tools()
        today = datetime.date.today().isoformat()
        limit = self.limit_until()
        orders = self._read_external_limits()
        tasks = {(t["project"], t["file"], t["title"]): t for t in (data or {}).get("tasks", [])}
        upcoming = self.next_tasks(data, index) if data and index else []
        with self._lock:
            # przebieg (log) idzie osobno: GET /api/agent/przebieg; w /api/data tylko liczba wierszy
            runs = [dict({k: v for k, v in r.items() if k not in RUN_PRIVATE}, steps=list(r.get("steps") or []),
                         denials=list(r.get("denials") or []), logN=int(r.get("logN") or 0),
                         takesMsg=bool(r["state"] == "running" and (self._priv.get(r["id"]) or {}).get("stream")
                                   and not (self._priv.get(r["id"]) or {}).get("ended")))
                    for r in reversed(list(self._runs.values()))]
            seen = set()
            for r in runs:
                key = (r.get("project"), r.get("file"), r.get("title"))
                task = tasks.get(key)
                if r["state"] == "running":
                    log = self._runs[r["id"]].get("log") or []
                    r["recent"] = [entry["text"][:300] for entry in log if entry.get("k") in
                                   ("agent", "narzedzie", "panel", "odmowa")][-3:]
                    r["plan"] = [dict(step) for step in r.get("plan") or [] if step.get("text")] or (
                        (task or {}).get("detail") or {}).get("steps", [])
                if r["kind"] == "task" and r["state"] == "done":
                    if not r.get("outcome"):
                        r["outcome"] = task_outcome(task) if key not in seen else "unknown"
                    elif r.get("outcome") == "review" and key not in seen and task and task["state"] == "done":
                        r["outcome"] = "done"
                if r["kind"] == "task":
                    seen.add(key)
            history = runs + orders
            now = time.time()
            estimates = {}
            for row in history + upcoming:
                if row.get("state") not in LIVE:
                    continue
                key = (row.get("tool"), agent_progress.category(row))
                if key not in estimates:
                    estimates[key] = agent_progress.estimate(history, *key)
                row["estimate"] = (agent_progress.estimate_running(estimates[key], row, now)
                                   if row["state"] == "running" else dict(estimates[key]))
            panel_queue = [r for r in reversed(runs) if r["state"] == "queued"] + upcoming
            development_queue = [r for r in reversed(orders) if r["state"] == "queued"]
            queue_estimate = agent_progress.estimate_queue([r for r in runs if r["state"] == "running"],
                                                          panel_queue, self.max_parallel, now)
            development_estimate = agent_progress.estimate_queue([r for r in orders if r["state"] == "running"],
                                                                 development_queue, 1, now)
            if development_queue and panel_queue:
                queue_estimate = {k: value + development_estimate[k] for k, value in queue_estimate.items()
                                  if k in development_estimate}
            elif development_queue:
                queue_estimate = development_estimate
            todays = [r for r in runs if (r.get("queuedAt") or "")[:10] == today]
            return {"machine": self.machine,
                    "tools": {k: dict(v) for k, v in self._tools.items()},
                    "needsLogin": self._state["needsLogin"], "limitUntil": limit,
                    "automat": self._state["automat"], "maxParallel": self.max_parallel, "canRunTasks": True,
                    "parallelMax": PARALLEL_MAX, "deployHold": self.deploy_hold(),
                    "usage": self.usage_state(),
                    "loginWeb": self.login_web,
                    "login": ({"active": True, "url": self._login["url"]}
                              if self._login and self._login["proc"].poll() is None and self._login["url"] else {"active": False}),
                    "today": {"runs": len(todays),
                              "tokens": sum((r.get("tokensIn") or 0) + (r.get("tokensOut") or 0) +
                                            (r.get("decisionTokensIn") or 0) + (r.get("decisionTokensOut") or 0) for r in todays),
                              "costUsd": round(sum((r.get("costUsd") or 0) + (r.get("decisionCostUsd") or 0) for r in todays), 2)},
                    "runs": list({r["id"]: r for r in runs[:SHOWN] + [r for r in runs if r["state"] in LIVE]}.values()),
                    "development": orders, "queueEstimate": queue_estimate,
                    "nextTasks": upcoming}

    def get(self, rid):
        with self._lock:
            rec = self._runs.get(rid)
            return dict(rec) if rec else None

    # ---------- przyjmowanie uruchomień ----------
    def _new(self, kind, tool, title, auto=False, project="", project_name="", task_id="", file=""):
        return {"id": "%s-%s" % (time.strftime("%Y%m%d-%H%M%S"), uuid.uuid4().hex[:4]), "kind": kind, "tool": tool,
                "state": "queued", "auto": bool(auto), "machine": self.machine, "project": project,
                "projectName": project_name, "taskId": task_id, "file": file, "title": title,
                "queuedAt": now_iso(), "startedAt": None, "endedAt": None, "durationMs": None, "activity": "",
                "steps": [], "result": "", "error": "", "turns": 0, "tokensIn": 0, "tokensOut": 0, "costUsd": 0,
                "model": "", "keySource": "", "denials": [], "limitStart": None, "limitNow": None}

    def _enqueue(self, rec, priv):
        with self._lock:
            self._runs[rec["id"]] = rec
            self._priv[rec["id"]] = priv
            self._queue.append(rec["id"])
            self._save(rec)
        self._trim()
        self._pump()

    def _claude_args(self, path, model="", extra=()):
        args = _command(path) + ["-p", "--output-format", "stream-json", "--verbose", "--permission-mode", "acceptEdits"]
        if model:
            args += ["--model", model]
        return args + list(extra)

    @staticmethod
    def detail_lines(detail):
        """Szczegóły zadania (projekt.parse_detail) jako wiersze promptu."""
        d = detail if isinstance(detail, dict) else {}
        out = []
        if d.get("goal"):
            out.append("Cel: %s" % d["goal"])
        if d.get("doneWhen"):
            out.append("Gotowe gdy: %s" % d["doneWhen"])
        refs = [r for r in d.get("refs") or [] if isinstance(r, dict) and r.get("path")]
        if refs:
            out.append("Materiały (ścieżki względem folderu projektu; po # numer albo nazwa sekcji):")
            out += ["- %s%s" % (r["path"], "#" + r["anchor"] if r.get("anchor") else "") for r in refs]
        steps = [x for x in d.get("steps") or [] if isinstance(x, dict) and x.get("text")]
        if steps:
            out.append("Kroki (wcięte wiersze pod zadaniem; to nie są osobne zadania):")
            out += ["- [%s] %s" % ("x" if x.get("done") else " ", x["text"]) for x in steps]
        for key, label in (("notes", "Notatki"),):
            if d.get(key):
                out.append("%s: %s" % (label, " / ".join(d[key])))
        answers = [a for a in d.get("answers") or [] if isinstance(a, dict) and a.get("label")]
        if answers:
            out.append("Dane od właściciela (formularz w panelu):")
            out += ["- %s: %s" % (a["label"], a.get("value", "")) for a in answers]
        for key, label in (("result", "Wynik poprzedniej pracy"), ("decision", "Decyzja do zatwierdzenia"),
                           ("left", "Zostało z poprzedniej pracy"), ("fix", "Poprawka od właściciela (wiersz poprawka:)"),
                           ("next", "Zaproponowane następne zadanie")):
            if d.get(key):
                out.append("%s: %s" % (label, d[key]))
        pins = [p for p in d.get("pins") or [] if isinstance(p, dict) and p.get("file")]
        if pins:
            out.append("Znaczniki właściciela do poprawki (wiersze pod poprawka:; plik względem folderu projektu, "
                       "położenie w %% od lewej i od góry obrazu, przy filmie chwila m:ss; obejrzyj ten plik przed poprawką):")
            out += ["  " + projekt_pin_line(p) for p in pins]
        return out

    def _image_rules(self, file, title, detail):
        """Zasady obrazów dla Codexa: generowanie ($imagegen) albo tylko prawdziwe zdjęcia (pole karty, zapis w zadaniu)."""
        card = ""
        try:
            with open(os.path.join(os.path.dirname(os.path.realpath(file)), "KARTA.md"), encoding="utf-8") as f:
                card = f.read()
        except (OSError, TypeError, ValueError):
            pass
        text = " ".join([str(title or "")] + [str(x) for x in (self.detail_lines(detail) or [])])
        return CODEX_PHOTO_RULES if photos_only(card, text) else CODEX_IMAGE_RULES

    def task_prompt(self, tool, name, file, line, title, stage, detail=None, git=None, site_rules=(), drive="",
                    parts=()):
        """git: {"branch", "cwd", "file", "card", "cards"} przy pracy w katalogu roboczym gałęzi uruchomienia.
        site_rules: zasady zadania strony WWW (strona.Site.rules)."""
        rules = "AGENTS.md" if tool == "codex" else "CLAUDE.md"
        head = ["Pracujesz w projekcie „%s” według %s i KARTA.md." % (name, rules),
                "Wykonaj jedno zadanie z pliku %s, wiersz %d: „%s”." % (git["file"] if git else file, line, title)]
        if stage:
            head.append("Etap: %s." % stage)
        more = self.detail_lines(detail)
        if more:
            head += ["", "Szczegóły zadania:"] + more
        if git:
            git_rules = [
                "- Pracujesz w osobnym katalogu roboczym git (%s) na gałęzi `%s`, którą założył panel. Pracę zapisz "
                "w tym katalogu i zatwierdź lokalnym commitem na tej gałęzi: bez zmiany gałęzi, bez push, bez plików "
                "KARTA.md, ZADANIA.md, DECYZJE.md. Niezatwierdzone zmiany panel zatwierdzi sam po zakończeniu."
                % (git["cwd"], git["branch"]),
                "- Plik zadania i kartę zmieniaj wyłącznie pod tymi ścieżkami (kopii w katalogu roboczym nie zmieniaj): "
                "zadanie %s, karta %s. Folder posty/ leży obok karty: %s." % (git["file"], git["card"], git["cards"]),
                "- W wierszu `wynik:` podaj ścieżki powstałych plików względem folderu projektu."]
            if git.get("resumed"):
                git_rules.append("- Ta gałąź ma już commity z poprzedniej pracy nad tym zadaniem: zacznij od nich "
                                 "(`git log`), nie rób tej pracy od nowa.")
        else:
            git_rules = [
                "- Pracę w repozytorium git zapisz na nowej gałęzi `agent/%s-krotka-nazwa` (`git switch -c`) jednym "
                "lokalnym commitem, bez push i bez plików KARTA.md, ZADANIA.md, DECYZJE.md. W wierszu `wynik:` podaj "
                "gałąź i skrót commita. Folder bez repozytorium: bez gałęzi i commita." % datetime.date.today().isoformat()]
        return "\n".join(head + [
            "",
            "Zasady:",
            "- Rób tylko to zadanie. Nie zmieniaj innych zadań ani terminów. W KARTA.md możesz tylko dopisać pytanie. "
            "Wyjątek: zadanie, którego tytuł zaczyna się od „Porządki spraw właściciela”, robi to, co opisuje jego cel.",
            "- Nigdy nie zmieniaj tytułu zadania (tekstu wiersza przed pierwszym „|”) i nie dopisuj do niego raportu.",
            "- Nie wykonuj działań nieodwracalnych ani wychodzących na zewnątrz (wysyłka, publikacja, wdrożenie, płatność). "
            "Gdy zadanie tego wymaga, przygotuj wszystko i dopisz w wierszu zadania `wymaga: zgoda`.",
            "- Polecenia, na które nie masz uprawnień, pomiń i opisz w wierszu `zostało:`.",
            "- Nie zlecaj właścicielowi kroków technicznych (git, commit, scalanie, konfiguracja, polecenia w terminalu): "
            "panel sam zatwierdza i scala gałęzie agenta. Gdy do dokończenia potrzebujesz od właściciela danych "
            "(nazwa, adres, wybór), zadaj pytanie w KARTA.md z propozycją; techniczną resztę zrobi kolejne zadanie agenta.",
            "- Wykonane kroki odhacz w ich wierszach (`  - [x] krok`).",
            "- Gdy pod zadaniem jest wiersz `poprawka:`, to polecenie albo uwagi właściciela (po odbiorze albo "
            "z rozmowy w panelu): wykonaj je, a istniejącą pracę popraw według nich. Wiersze `- znacznik N (plik, "
            "położenie): uwaga` pod poprawką to uwagi do miejsca na obrazie (albo chwili filmu); nie zmieniaj ich.",
            "- Na koniec dopisz pod wierszem zadania wcięte o 2 spacje wiersze (istniejące wiersze z tym kluczem zastąp): "
            "`  wynik: …` (krótko, co powstało i gdzie); `  decyzja: …`, gdy właściciel ma coś zatwierdzić przy odbiorze; "
            "`  zostało: …`, gdy coś nie zostało zrobione (tylko to, co ważne dla właściciela, np. czego nie sprawdzono; "
            "bez spraw technicznych: gdzie leży plik, commit, gałąź, git); po pracy z wierszem `poprawka:` także "
            "`  zmiany: …`: 2–3 krótkie zmiany rozdzielone „; ”, a przy każdej uwadze i znaczniku „zrobione” albo "
            "powód (np. `  zmiany: tło granatowe; logo większe; znacznik 1: zrobione; znacznik 2: bez zmian, bo …`).",
            "- W nowym zadaniu użyj `kto: agent`, gdy wybór narzędzia ma należeć do panelu. Nie zmieniaj pola kto "
            "bieżącego zadania. Nie uruchamiaj innych agentów ani nie używaj ogólnego Bash.",
            "- Możesz dopisać pod zadaniem jeden wiersz `  następne: Tytuł | kto: … | kiedy: RRRR-MM-DD` z propozycją "
            "kolejnego zadania. Nowych zadań nie zakładaj.",
            FIELDS_RULE,
        ] + git_rules + self.part_rules(parts) + drive_rules(drive) + film_rules(title) + list(site_rules) + (self._image_rules(file, title, detail) if tool == "codex" else []) + OWNER_RULES
            + self.render_rules() + [
            "- Pytania do właściciela dopisz jako kolejny punkt „1. pytanie” w sekcji „## Pytania do właściciela” "
            "w KARTA.md (załóż sekcję na końcu pliku, gdy jej nie ma); termin odpowiedzi jako wcięty wiersz "
            "`   termin: RRRR-MM-DD` pod pytaniem.",
            "- Gdy pytanie jest wyborem, dopisz pod nim 2–3 wcięte wiersze `   opcja: …` (krótko, wzajemnie "
            "wykluczające się odpowiedzi); `propozycja:` wskazuje wtedy jedną z opcji, tym samym tekstem.",
            "- Gdy masz rekomendację, dopisz pod pytaniem wcięty wiersz `   propozycja: …`. Gdy przyjęcie propozycji "
            "zmienia zadania w ZADANIA.md, pod propozycją zawsze dopisz każdą zmianę jako wcięty wiersz "
            "`   skutek: <operacja>`, jedna operacja w wierszu: `po: <fragment poprzednika> → <fragment tytułu "
            "zadania>`, `kiedy: RRRR-MM-DD → <fragment tytułu>`, `stan: zrobione|wstrzymane → <fragment tytułu>` "
            "albo `nowe: <wiersz zadania>`. Panel wykona skutki dopiero po przyjęciu propozycji przez właściciela.",
            "- Wiersza `gotowe gdy:` nie zmieniaj i nie łagodź (nie dopisuj „albo w zostało:” ani innych wyjątków). "
            "Gdy warunku nie da się spełnić, opisz to w `zostało:` i zakończ stanem `[!]`.",
            "- Stan zmień w %s wyłącznie w wierszu tego zadania: gotowe to `[x]`; potrzebny przegląd właściciela to `[~]` "
            "i pole `wymaga: odbiór`. Gdy warunek „gotowe gdy” nie jest spełniony, zakończ stanem `[!]` z polem "
            "`blokada: powód` (bez `wymaga: odbiór`)." % (git["file"] if git else file),
            "- Zakończ odpowiedź trzema krótkimi punktami: Zrobione, Sprawdzone, Zostało.",
        ]) + "\n"

    def render_command(self):
        """Polecenie renderu HTML → PDF/PNG (prefiks dla agenta) albo '' (Windows, brak Pythona z Playwright).
        PANEL_RENDER: całe polecenie; PANEL_RENDER_PYTHON: Python z Playwright; inaczej Python zrzutów strony
        na serwerze albo ~/narzedzia/pw, ~/narzedzia/film na Macu i PC."""
        given = (self.env.get("PANEL_RENDER") or "").strip()
        if given:
            return given
        if WINDOWS:
            return ""
        py = os.path.expanduser((self.env.get("PANEL_RENDER_PYTHON") or "").strip())
        if not py:
            for cand in (strona.SHOT_PYTHON, "~/narzedzia/pw/bin/python",
                         self.env.get("PANEL_FILM_PYTHON") or "~/narzedzia/film/bin/python"):
                cand = os.path.expanduser(cand)
                if os.path.isfile(cand):
                    py = cand
                    break
        if not py or not os.path.isfile(py):
            return ""
        return "%s %s" % (shlex.quote(py), shlex.quote(RENDER_SCRIPT))

    def render_rules(self):
        cmd = self.render_command()
        if not cmd:
            return ["- Zamiana HTML na PDF albo PNG jest na tym komputerze niedostępna (brak Playwright): przygotuj "
                    "plik HTML i wpisz to w `zostało:`."]
        return ["- PDF albo PNG z pliku HTML (np. wizytówka, ulotka, grafika): `%s <plik.html> <wynik.pdf> "
                "<wynik.png>` (opcje: `--strona 90x50mm` albo `--strona A4`, `--szerokosc 1080`, `--ekran`). Tylko "
                "pliki lokalne, zasoby z sieci są blokowane (fonty i obrazy trzymaj obok HTML). PNG obejrzyj "
                "narzędziem Read (to obraz)." % cmd]

    def _find_task(self, task_id=None, key=None):
        """Zadanie po id albo po (projekt, plik, tytuł). Zwraca (zadanie, dane, indeks folderów)."""
        data, index = self.load_projects()
        for t in data["tasks"]:
            if (task_id is not None and t["id"] == task_id) or \
                    (key is not None and (t["project"], t["file"], t["title"]) == key):
                return t, data, index
        return None, data, index

    def run_task(self, task_id, title, auto=False, pm=False):
        """Przyjmuje zadanie do uruchomienia. Zwraca (kod, błąd, dodatki)."""
        parts = str(task_id).split("|")
        if len(parts) != 3 or not parts[2].isdigit():
            return 400, "Nieznane zadanie.", {}
        title = str(title)
        with self._start_lock:
            task, data, index = self._find_task(task_id=str(task_id))
            if parts[0] not in index:
                return 404, "Nie ma takiego projektu.", {}
            if not task or task["title"] != title:
                return 409, CONFLICT, {}
            block = self.run_block(task, data["projectsSource"])
            if block:
                return 409, block, {}
            folder = index[task["project"]]
            first_steps = []
            ok, note = self.ensure_copy(next((p for p in data["projects"] if p["id"] == task["project"]), {}), folder)
            if not ok:
                return 409, note, {}
            if note:
                first_steps.append({"t": time.strftime("%H:%M:%S"), "text": note})
            if self.git_pull:
                note, pulled = self._git_pull(folder)
                if note:
                    first_steps.append({"t": time.strftime("%H:%M:%S"), "text": note})
                if pulled:
                    task, data, index = self._find_task(key=(task["project"], task["file"], title))
                    if not task or self.run_block(task, data["projectsSource"]):
                        return 409, CONFLICT, {}
            project = next((p for p in data["projects"] if p["id"] == task["project"]), {})
            self._read_external_limits()
            tool, reason = self.choose_task_tool(task, project, folder, decide=True)
            if not tool:
                return 409, reason, {}
            if auto:
                used = self.usage_state()["codexFive" if tool == "codex" else "five"]
                if used is not None and used >= self.auto_reserve:
                    return 409, "Wykonawca osiągnął próg limitu Automatu.", {}
            path = self.tool_path(tool)
            if not path:
                return 409, "Brak polecenia %s" % tool, {}
            changes = {"state": "doing"}
            if not task.get("executor"):
                changes["executor"] = tool
            if self.machine in ("pc", "mac", "cloud"):
                changes["machine"] = self.machine
            try:
                with self.write_lock:
                    current, data, current_index = self._find_task(task_id=task["id"])
                    if (not current or current["title"] != title or current_index.get(task["project"]) != folder
                            or current.get("executor") != task.get("executor")
                            or (current.get("detail") or {}).get("executorPin") !=
                               (task.get("detail") or {}).get("executorPin")):
                        return 409, CONFLICT, {}
                    block = self.run_block(current, data["projectsSource"])
                    if pm and not block:
                        block = self._pm_wait(current, now_iso()[:10])
                    if block:
                        return 409, block, {}
                    task = current
                    ok = self.projekt.update_task(folder, task["file"], task["line"], title, changes)
            except ValueError as e:
                return 400, "Nie zapisano: %s." % e, {}
            except OSError:
                return 400, "Nie udało się zapisać zmiany.", {}
            if not ok:
                return 409, CONFLICT, {}
            stage = next((s["title"] for s in data["stages"] if s["id"] == task.get("stage")), "")
            rec = self._new("task", tool, title, auto, task["project"], project.get("name", task["project"]),
                            task["id"], task["file"])
            rec["steps"] = first_steps
            rec["family"] = project.get("partOf") or task["project"]
            rec["choiceReason"] = reason
            rec["category"] = self._task_category(task, project, folder)
            with self._lock:
                decision = self._state["decisions"].get(self.projekt.task_key(task)) or {}
                cost = decision.pop("cost", {})
                rec.update({key: value for key, value in cost.items() if key.startswith("decision")})
                if (used := agent_progress.consumed(cost)) is not None:
                    rec["decisionLimit"] = used
                self._save_state()
            rec["fix"] = str((task.get("detail") or {}).get("fix") or "")[:1000]   # Automat: nowa poprawka = nowe uruchomienie
            rec["pins"] = [dict(p) for p in (task.get("detail") or {}).get("pins") or [] if isinstance(p, dict)]
            priv = {"folder": folder, "client": project.get("client") is True,
                    "label": project.get("alias") or project.get("name") or task["project"],
                    "task": {"tool": tool, "path": path, "name": rec["projectName"], "file": task["file"],
                             "line": task["line"], "title": title, "stage": stage,
                             "detail": with_answers(task, data["tasks"]),
                             "site": self.site.task_site(project, title)},
                    "resume": self._resume_branches(task),
                    "parts": [{"project": x["id"], "label": x.get("partLabel") or x.get("name") or x["id"],
                               "folder": index[x["id"]]} for x in data["projects"]
                              if x.get("partOf") == task["project"] and x["id"] in index][:PARTS_MAX]}
            self._task_command(priv)
            self._enqueue(rec, priv)
            return 200, "", {"id": rec["id"]}

    @staticmethod
    def ensure_copy(project, folder):
        """Klon na start: karta z polem github:, a folder projektu bez repozytorium (kopia usunięta albo jej brak)
        → klon z GitHuba przed zadaniem albo budowaniem podglądu. (True, notatka albo "") / (False, powód blokady)."""
        github = (project or {}).get("github") or ""
        if not github or not folder or kopie.has_repo(folder):
            return True, ""
        return kopie.clone(folder, github, project.get("githubBranch") or "")

    def _task_command(self, priv, git=None):
        """Polecenie, katalog i prompt zadania. git (z _worktree_open): praca w katalogu roboczym gałęzi
        uruchomienia, pliki standardu w folderze projektu przez --add-dir i ścieżki bezwzględne."""
        t, folder = priv["task"], priv["folder"]
        if git:
            cwd = git["worktree"] if git["rel"] == "." else os.path.join(git["worktree"], git["rel"])
            extra = [x for d in self._standard_dirs(folder, t["file"]) for x in ("--add-dir", d)]
            info = {"branch": git["branch"], "cwd": cwd, "file": os.path.join(folder, t["file"]),
                    "card": os.path.join(folder, "KARTA.md"),
                    "cards": os.path.dirname(os.path.realpath(os.path.join(folder, "KARTA.md"))),
                    "resumed": bool(git.get("resumed"))}
        else:
            cwd, extra, info = folder, _card_dirs(folder), None
        site = t.get("site")
        mnt = drive_dir(folder)
        if mnt and mnt not in extra:
            extra = extra + ["--add-dir", mnt]       # odczyt plików z Drive (Claude czyta tylko w podanych folderach)
        parts = [x for x in priv.get("parts") or [] if x.get("worktree")]
        for x in parts:
            extra = extra + ["--add-dir", x["worktree"]]
        mcp = self.site.mcp_args(priv, cwd) if site and t["tool"] == "claude" else []
        prompt = self.task_prompt(t["tool"], t["name"], t["file"], t["line"], t["title"], t["stage"], t["detail"],
                                  git=info, site_rules=(self.site.rules(site, cwd) + self.site.mcp_rules(priv))
                                  if site else (), drive=mnt, parts=parts)
        if t["tool"] == "codex":
            args = _command(t["path"]) + ["exec", "--json", "--sandbox", "workspace-write", "--skip-git-repo-check",
                                          "-c", "sandbox_workspace_write.network_access=false",
                                          "-c", "features.multi_agent=false", "-c", "features.multi_agent_v2=false",
                                          "-C", cwd] + (extra if git or parts else []) + ["-"]
        else:
            render = self.render_command()
            tools = ",".join([TASK_TOOLS] + (["Bash(%s:*)" % render] if render else []) +
                             (self.site.tools(site) + self.site.mcp_tools(priv) if site else []))
            # wejście stream-json: stdin zostaje otwarty do zdarzenia result, więc właściciel może pisać do agenta
            # w trakcie pracy (live_order); po result panel zamyka stdin i CLI kończy pracę
            deny = ",".join([RUN_DENY] + [r for x in parts for r in x.get("deny") or []] + self.site.mcp_deny(priv))
            args = self._claude_args(t["path"], self.model, ["--input-format", "stream-json"] + extra +
                                     ["--allowedTools", tools, "--disallowedTools", deny, "--strict-mcp-config"]
                                     + mcp)
            priv["stream"] = True
        priv.update(args=args, cwd=cwd, prompt=prompt)

    # ---------- dawna rozmowa o zadaniu (tylko odczyt historii; rozmowy: Asystent i Rozmowa w projekcie) ----------
    def _chat_file(self, task):
        key = "%s|%s|%s" % (task["project"], task["file"], task["title"])
        return os.path.join(self.runs_dir, "czat", hashlib.sha1(key.encode("utf-8")).hexdigest() + ".json")

    @staticmethod
    def _chat_read(path):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            data = {}
        data = data if isinstance(data, dict) else {}
        msgs = [m for m in data.get("messages") or [] if isinstance(m, dict) and m.get("role") in ("ty", "claude", PANEL_ROLE)]
        return {"session": str(data.get("session") or ""), "messages": msgs[-CHAT_KEEP:],
                "pending": data.get("pending") is True, "error": str(data.get("error") or ""), "v": str(data.get("v") or "")}

    @staticmethod
    def _chat_session(chat):
        """Sesja do wznowienia: '' przy złym id albo zasadach z innej wersji promptu (CHAT_RULES_V)."""
        ok = re.fullmatch(r"[\w-]{1,100}", chat["session"]) and chat.get("v") == CHAT_RULES_V
        return chat["session"] if ok else ""

    def _chat_write(self, path, chat):
        chat["messages"] = chat["messages"][-CHAT_KEEP:]
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._write_json(path, chat)

    def chat_get(self, task_id):
        """Historia dawnej rozmowy o zadaniu, tylko do odczytu (szczegóły zadania, „Dawna rozmowa o zadaniu”).
        Nowe wiadomości o zadaniu idą do Rozmowy w projekcie. Zwraca (kod, błąd, {"messages", "pending", "error"})."""
        task, _, _ = self._find_task(task_id=str(task_id))
        if not task:
            return 404, "Nie ma tego zadania.", {}
        path = self._chat_file(task)
        with self._chat_lock:
            chat = self._chat_read(path)
            live = path in self._chat_live
        if chat["pending"] and not live:            # odpowiedź przerwana restartem panelu
            chat["error"] = chat["error"] or "Odpowiedź przerwana. Wyślij pytanie jeszcze raz."
        return 200, "", {"messages": self.panel_view(chat["messages"]), "pending": live, "error": chat["error"]}

    RECENT_FIELDS = ("id", "kind", "tool", "state", "auto", "machine", "project", "projectName", "taskId", "file",
                     "title", "queuedAt", "startedAt", "endedAt", "durationMs")

    def recent_runs(self, hours=24, limit=100):
        """Zakończone uruchomienia z ostatnich `hours` godzin, najnowsze najpierw, pola skrócone (widok Teraz).
        snapshot() oddaje tylko SHOWN ostatnich, więc przy aktywnym Automacie część dnia by wypadła."""
        low = (datetime.datetime.now() - datetime.timedelta(hours=hours)).isoformat(timespec="seconds")
        with self._lock:
            done = [r for r in self._runs.values()
                    if r.get("endedAt") and str(r["endedAt"]) >= low and r.get("state") not in ("queued", "running")]
            done.sort(key=lambda r: str(r["endedAt"]), reverse=True)
            return [dict({k: r.get(k) for k in self.RECENT_FIELDS}, error=str(r.get("error") or "")[:200])
                    for r in done[:limit]]

    def chat_pending(self):
        """Rozmowy, które czekają na odpowiedź Claude: [{"taskId", "project", "file", "title", "since"}]."""
        with self._chat_lock:
            return sorted((dict(m) for f, m in self._chat_meta.items() if f in self._chat_live),
                          key=lambda m: m["since"])

    CHAT_DONE_MAX = 50
    CHAT_FILE = os.path.join("teraz", "rozmowy.json")
    CHAT_CUT = "przerwana: panel uruchomiono ponownie w trakcie odpowiedzi"

    def _chat_save(self):
        """Rozmowy w toku i zakończone w <katalog uruchomień>/teraz/rozmowy.json (wywołanie pod _chat_lock): po restarcie
        panelu „Ostatnie 24 h” ma nadal rozmowy, a przerwane dostają błąd z „Zapytaj ponownie”."""
        path = os.path.join(self.runs_dir, self.CHAT_FILE)
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            self._write_json(path, {"live": [self._chat_meta[f] for f in self._chat_live if f in self._chat_meta],
                                    "done": self._chat_done[-self.CHAT_DONE_MAX:]})
        except OSError:
            pass

    def _chat_restore(self):
        """Przy starcie: zakończone rozmowy z pliku, a rozmowy w toku poprzedniego procesu jako przerwane (błąd)."""
        try:
            with open(os.path.join(self.runs_dir, self.CHAT_FILE), encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            return
        if not isinstance(data, dict):
            return
        ok = lambda m: isinstance(m, dict) and isinstance(m.get("title"), str) and m.get("title")  # noqa: E731
        done = [m for m in data.get("done") or [] if ok(m) and m.get("at")]
        cut = [dict(m, at=now_iso(), ok=False, error=self.CHAT_CUT) for m in data.get("live") or [] if ok(m)]
        with self._chat_lock:
            self._chat_done = (done + cut)[-self.CHAT_DONE_MAX:]
            if cut:
                self._chat_save()

    def chat_recent(self, hours=24):
        """Zakończone rozmowy z ostatnich `hours` godzin (od startu tego procesu), najnowsze najpierw:
        [{"taskId", "project", "file", "title", "since", "at", "ok", "error"}]."""
        low = (datetime.datetime.now() - datetime.timedelta(hours=hours)).isoformat(timespec="seconds")
        with self._chat_lock:
            return [dict(m) for m in reversed(self._chat_done) if str(m.get("at", "")) >= low]

    # ---------- uruchamianie z rozmów (AGENCI.md, „Uruchamianie z rozmów”) ----------
    def _chat_append(self, file, msgs):
        """Dopisuje wiadomości do pliku rozmowy (pod _chat_lock). False przy błędzie zapisu."""
        with self._chat_lock:
            chat = self._chat_read(file)
            chat["messages"] += list(msgs)
            try:
                self._chat_write(file, chat)
            except OSError:
                return False
        return True

    def task_chat_file(self, task):
        """Rozmowa w projekcie, do której trafiają wiadomości o zadaniu: rozmowa projektu (albo części) zadania."""
        return self._project_chat_file(task["project"])

    def chat_execute(self, task, index, text, pins=None, ref=True, spoken=False):
        """„Wyślij i wykonaj” (Rozmowa w projekcie z odnośnikiem do zadania, „Do poprawy”, odbiór): wiadomość trafia
        pod zadanie jako `poprawka:` (polecenie dla agenta), zadanie wraca do [ ] (zrobione, w toku, do odbioru,
        blokada), potem launch_task albo wiadomość do pracującego agenta. Bez modelu. Wiadomość i stan zapisują się
        w Rozmowie w projekcie zadania. Zwraca (200, "", {"status": wiadomość panelu}) albo błąd zapisu rozmowy."""
        file = self.task_chat_file(task)
        mine = {"role": "ty", "text": text, "at": now_iso(), "exec": True}
        if spoken:
            mine["spoken"] = True
        if ref:
            mine["task"] = {"id": task["id"], "title": task["title"], "project": task["project"]}
        if pins:
            mine["pins"] = pins
        if not self._chat_append(file, [mine]):
            return 500, "Nie udało się zapisać rozmowy.", {}
        msg = self._execute_order(task, index, text, pins)
        self._chat_append(file, [msg])
        return 200, "", {"status": self.panel_view([msg])[0]}

    def _execute_order(self, task, index, text, pins=None):
        msg = self._panel_msg(task)
        key = (task["project"], task["file"], task["title"])
        why = ""
        if task.get("kind") == "publikacja":
            why = "publikację wykonujesz samodzielnie."
        elif task.get("executor") not in AGENT_EXECUTORS:
            why = "to zadanie nie jest dla agenta (kto: %s). Zmień wykonawcę w szczegółach." % (task.get("executor") or "brak")
        elif key in self._live_keys():
            code, err, live = self.live_message(self._live_keys()[key], text, pins)
            if code == 200:
                return live
            if code != 409:                         # 409: uruchomienie właśnie się skończyło, zwykła droga niżej
                msg["text"] = "Nie przekazano polecenia: %s" % err
                return msg
        if why:
            msg["text"] = "Nie uruchomiono „%s”: %s" % (task["title"], why)
            return msg
        changes = {}
        needs = needs_of(task)
        if task.get("state") in ("done", "doing", "blocked"):     # zrobione wraca do [ ] tylko z poprawką
            changes["state"] = "todo"
        if task.get("state") == "blocked" or task.get("blocked"):
            changes["blocked"] = ""
        if "odbiór" in needs:
            changes["needs"] = [n for n in needs if n != "odbiór"]
        folder = index[task["project"]]
        try:
            with self.write_lock:
                ok = self.projekt.set_detail(folder, task["file"], task["line"], task["title"], "poprawka", text[:1000],
                                             pins=pins)
                if ok and changes:
                    ok = self.projekt.update_task(folder, task["file"], task["line"], task["title"], changes)
        except (ValueError, OSError):
            ok = False
        if not ok:
            msg["text"] = "Nie zapisano polecenia: zadanie zmieniło się w pliku. Odśwież i wyślij jeszcze raz."
            return msg
        fresh, data, _ = self._find_task(key=key)
        if not fresh:
            msg["text"] = "Nie zapisano polecenia: nie ma już tego zadania."
            return msg
        return self.launch_task(fresh, data)

    @staticmethod
    def _panel_msg(task):
        return {"role": PANEL_ROLE, "at": now_iso(), "project": task.get("project", ""), "file": task.get("file", ""),
                "title": task.get("title", ""), "runId": "", "text": ""}

    # ---------- wiadomość do pracującego agenta (AGENCI.md, „Wiadomość w trakcie pracy”) ----------
    def _append_fix(self, task, folder, text, pins=None):
        """Dopisuje polecenie do wiersza `poprawka:` zadania (następne uruchomienie też je zna). Zwraca nową
        treść poprawki albo '' (wiersz zmienił się w pliku)."""
        d = task.get("detail") or {}
        old = str(d.get("fix") or "").strip()
        new = text if not old or old == text or old.endswith(" / " + text) else "%s / %s" % (old, text)
        if len(new) > FIX_MAX:
            new = "…" + new[-(FIX_MAX - 1):]
        keep = pins or [dict(p) for p in d.get("pins") or [] if isinstance(p, dict)] or None
        try:
            with self.write_lock:
                try:
                    ok = self.projekt.set_detail(folder, task["file"], task["line"], task["title"], "poprawka", new,
                                                 pins=keep)
                except ValueError:
                    ok = self.projekt.set_detail(folder, task["file"], task["line"], task["title"], "poprawka", new)
        except (ValueError, OSError):
            ok = False
        return new if ok else ""

    def _stdin_send(self, priv, text):
        """Wiadomość użytkownika na otwarte wejście stream-json procesu. False, gdy wejście jest już zamknięte."""
        line = json.dumps({"type": "user", "message": {"role": "user", "content": text}}, ensure_ascii=False)
        with priv.setdefault("stdinLock", threading.Lock()):
            proc = priv.get("proc")
            if priv.get("closed") or proc is None or proc.stdin is None or proc.poll() is not None:
                return False
            try:
                proc.stdin.write(line + "\n")
                proc.stdin.flush()
                return True
            except (OSError, ValueError):
                return False

    def _stdin_close(self, priv):
        with priv.setdefault("stdinLock", threading.Lock()):
            priv["closed"] = True
            proc = priv.get("proc")
            if proc is not None and proc.stdin is not None:
                try:
                    proc.stdin.close()
                except (OSError, ValueError):
                    pass

    def live_message(self, rid, text, pins=None):
        """Polecenie właściciela dla uruchomienia zadania w kolejce albo w toku. Zawsze dopisuje je do `poprawka:`
        zadania; Claude w toku dostaje je na stdin (agent uwzględnia je przy następnym kroku), zadanie w kolejce ma je
        w poleceniu startowym, Codex (bez wejścia w trakcie) i Claude po zdarzeniu result dostają je po zakończeniu
        (Codex: przycisk „Zatrzymaj i uruchom z poprawką”, Claude: ponowne uruchomienie jak „Wyślij i wykonaj”).
        Zwraca (200, "", wiadomość panelu) albo (404|409, błąd, {})."""
        text = str(text or "").strip()[:CHAT_MAX]
        if not text:
            return 400, "Napisz polecenie.", {}
        with self._lock:
            rec = self._runs.get(str(rid))
            if not rec or rec.get("kind") != "task":
                return 404, "Nie ma takiego uruchomienia.", {}
            if rec["state"] not in LIVE:
                return 409, "Uruchomienie już się zakończyło.", {}
        key = (rec["project"], rec["file"], rec["title"])
        task, _, index = self._find_task(key=key)
        msg = self._panel_msg(task or {"project": key[0], "file": key[1], "title": key[2]})
        msg["runId"] = rec["id"]
        if not task or task["project"] not in index:
            msg["text"] = "Nie zapisano polecenia: nie ma już tego zadania."
            return 200, "", msg
        saved = self._append_fix(task, index[task["project"]], text, pins)
        with self._lock:
            priv = self._priv.get(rec["id"])
            if rec["state"] not in LIVE or priv is None:
                mode = "gone"
            elif rec["state"] == "queued":
                mode = "queued"
            elif rec["tool"] != "claude" or not priv.get("stream"):
                mode = "codex"
            elif priv.get("ended") or priv.get("closed"):
                mode = "after"
            elif not priv.get("open"):
                mode = "early"
                priv.setdefault("early", []).append(text)
            else:
                mode = "send"
            if saved:
                rec["fix"] = saved[:1000]       # Automat: ta poprawka jest już w tym uruchomieniu
            if mode == "queued" and saved:
                t = priv["task"]
                t["detail"] = dict(t.get("detail") or {}, fix=saved)
                self._task_command(priv)
        if mode == "send" and not self._stdin_send(priv, text):
            mode = "after"
        if mode == "after":
            with self._lock:
                if rec["state"] in LIVE and self._priv.get(rec["id"]) is priv:
                    priv.setdefault("after", []).append({"text": text, "pins": pins})
                else:
                    mode = "gone"
        if mode == "gone":
            return 409, "Uruchomienie już się zakończyło.", {}
        if mode in ("send", "early"):
            with self._lock:
                priv.setdefault("msgs", []).append({"text": text, "seen": False, "tr": False})
            self._log(rec, "ty", text, save=True)
            self._step(rec, "Ty: " + text, log=False)
            msg["text"] = "Przekazano agentowi."
            msg["delivered"] = True
        elif mode == "after":
            self._log(rec, "ty", text, save=True)
            self._log(rec, "panel", "Agent skończył, polecenie zapisane jako poprawka: uruchomię zadanie ponownie.")
            msg["text"] = "Agent skończył, polecenie zapisane jako poprawka. Zadanie uruchomi się ponownie z tym poleceniem."
        elif mode == "queued":
            msg["text"] = "Zadanie czeka w kolejce: polecenie dołączone do zadania (poprawka)."
        else:
            msg["text"] = ("Codex nie przyjmuje wiadomości w trakcie pracy. Polecenie zapisane jako poprawka: "
                           "zatrzymaj i uruchom z poprawką albo poczekaj na koniec pracy.")
            msg["restart"] = rec["id"]
        if not saved:
            msg["text"] += " Nie zapisano go pod zadaniem (wiersz zmienił się w pliku)."
        return 200, "", msg

    def _relaunch(self, rec, after, restart):
        """Po zakończeniu uruchomienia: polecenia, które przyszły po zdarzeniu result (ponowne uruchomienie jak
        „Wyślij i wykonaj”), albo „Zatrzymaj i uruchom z poprawką” (Codex). Wynik trafia do Rozmowy w projekcie."""
        title = rec["title"]
        end = time.time() + 1800
        while title in getattr(self.site, "_finishing", ()) and time.time() < end:
            time.sleep(1)                     # zadanie strony: najpierw scalenie i podgląd po tamtym uruchomieniu
        task, data, index = self._find_task(key=(rec["project"], rec["file"], title))
        if not task:
            return
        if after:
            text = " / ".join(a["text"] for a in after)[:1000]
            pins = next((a["pins"] for a in reversed(after) if a.get("pins")), None)
            msg = self._execute_order(task, index, text, pins)
        else:
            msg = self.launch_task(task, data)
        self._chat_append(self.task_chat_file(task), [msg])

    def restart_run(self, rid):
        """„Zatrzymaj i uruchom z poprawką”: zatrzymuje uruchomienie zadania, po zakończeniu uruchamia je ponownie
        (poprawka jest już pod zadaniem)."""
        with self._lock:
            rec = self._runs.get(str(rid))
            if not rec or rec.get("kind") != "task":
                return 404, "Nie ma takiego uruchomienia.", {}
            if rec["state"] not in LIVE:
                return 409, "Uruchomienie już się zakończyło.", {}
            self._priv.setdefault(rec["id"], {})["restart"] = True
        return self.stop(rid)

    def run_log(self, rid, since=0):
        """GET /api/agent/przebieg: wiersze przebiegu po numerze `since`, stan i najnowsze zrzuty strony."""
        try:
            since = max(0, int(since or 0))
        except (TypeError, ValueError):
            since = 0
        if agent_progress.ORDER.fullmatch(str(rid)):
            result = self.orders.live_log(str(rid), since)
            return (200, "", result) if result else (404, "Nie ma takiego zlecenia.", {})
        with self._lock:
            rec = self._runs.get(str(rid))
            if not rec:
                return 404, "Nie ma takiego uruchomienia.", {}
            priv = self._priv.get(rec["id"]) or {}
            items = [dict(x) for x in rec.get("log") or [] if int(x.get("n") or 0) > since]
            out = {"items": items, "next": int(rec.get("logN") or 0), "state": rec["state"],
                   "activity": rec.get("activity") or "", "tool": rec.get("tool") or "",
                   "takesMsg": bool(rec["state"] == "running" and priv.get("stream") and not priv.get("ended"))}
        out["shots"] = self.shots(rid)
        return 200, "", out

    def _shot_dir(self, rid):
        with self._lock:
            return self._shot_dirs.get(str(rid)) or ""

    def shots(self, rid):
        """Najnowsze zrzuty PNG z katalogu .zrzuty/ uruchomienia zadania strony: [{"name", "at", "v"}]."""
        base = self._shot_dir(rid)
        if not base or os.path.islink(base) or not os.path.isdir(base):
            return []
        out = []
        try:
            names = os.listdir(base)
        except OSError:
            return []
        for name in names:
            if not SHOT_NAME.match(name):
                continue
            path = os.path.join(base, name)
            try:
                st = os.lstat(path)
            except OSError:
                continue
            if not stat_regular(st):
                continue
            out.append({"name": name, "at": now_iso(datetime.datetime.fromtimestamp(st.st_mtime)),
                        "v": int(st.st_mtime)})
        out.sort(key=lambda x: x["v"], reverse=True)
        return out[:SHOTS_SHOWN]

    def shot_file(self, rid, name):
        """(200, bajty) zrzutu PNG z .zrzuty/ uruchomienia albo (404, ''). Bez dowiązań i wyjścia poza katalog."""
        base = self._shot_dir(rid)
        name = str(name or "")
        if not base or not SHOT_NAME.match(name) or os.path.islink(base):
            return 404, b""
        path = os.path.join(base, name)
        real = os.path.realpath(path)
        if os.path.dirname(real) != os.path.realpath(base):
            return 404, b""
        try:
            st = os.lstat(path)
            if not stat_regular(st) or st.st_size > SHOT_MAX:
                return 404, b""
            with open(path, "rb") as f:
                data = f.read(SHOT_MAX + 1)
        except OSError:
            return 404, b""
        if not data.startswith(b"\x89PNG\r\n\x1a\n"):
            return 404, b""
        return 200, data

    def chat_launches(self, answer, pid=""):
        """Wiersze działań z odpowiedzi rozmowy (take_actions): (odpowiedź bez nich, [wiadomość panelu na każde]).
        Uruchom: launch_task; Polecenie: _execute_order (poprawka i uruchomienie albo wiadomość do pracującego
        agenta); Odpowiedź na pytanie: ta sama droga co przycisk przy pytaniu (answer_hook = server.answer_question).
        pid: Rozmowa w projekcie (tylko ten projekt i jego części); '' Asystent (projekt z wiersza albo dowolny)."""
        text, wanted = take_actions(answer)
        if not wanted:
            return answer, []
        out = []
        for kind, val in wanted:
            data, index = self.load_projects()
            allowed = self.family(data, pid) if pid else None
            if kind == "answer":
                out.append(self._chat_answer(data, allowed, *val))
                continue
            want_pid, title = val[0], val[1]
            task = self._match_task(data, want_pid if not pid or want_pid in (allowed or ()) else pid, title,
                                    allowed=allowed)
            if not task:
                out.append(dict(self._panel_msg({"project": pid, "title": title}),
                                text="Nie uruchomiono „%s”: nie ma takiego zadania w ZADANIA.md." % title))
            elif kind == "run":
                out.append(self.launch_task(task, data))
            else:
                out.append(self._execute_order(task, index, val[2][:1000]))
        return text, out

    @staticmethod
    def family(data, pid):
        """Projekt rozmowy i jego części (pole karty część projektu:): {id}. Część: tylko ona sama."""
        pid = str(pid or "")
        return {pid} | {p["id"] for p in data["projects"] if p.get("partOf") == pid}

    def _chat_answer(self, data, allowed, want, n, text):
        """„Odpowiedź na pytanie: <projekt> | <numer> | <odpowiedź>” z rozmowy: zapis jak przycisk przy pytaniu."""
        pid = self._project_id(data, want) if want else ""
        if allowed is not None and pid not in allowed:
            pid = next(iter(allowed)) if len(allowed) == 1 else pid
        msg = dict(self._panel_msg({"project": pid, "title": ""}), text="")
        num = re.sub(r"\D", "", str(n))[:3]
        hook = getattr(self, "answer_hook", None)
        if not pid or (allowed is not None and pid not in allowed) or not num:
            msg["text"] = "Nie zapisano odpowiedzi: nie ma takiego projektu albo pytania."
            return msg
        if not hook:
            msg["text"] = "Nie zapisano odpowiedzi: panel nie obsługuje tu pytań."
            return msg
        try:
            res = hook({"id": pid, "n": int(num), "answer": str(text)[:1000]})
        except Exception as e:  # noqa: BLE001  (odpowiedź rozmowy musi trafić do historii)
            res = (500, "błąd panelu (%s)" % type(e).__name__)
        code, err = res[0], res[1]
        name = next((p.get("name") or pid for p in data["projects"] if p["id"] == pid), pid)
        msg["text"] = ("Zapisano odpowiedź na pytanie %s (%s)." % (num, name) if 200 <= code < 300 else
                       "Nie zapisano odpowiedzi na pytanie %s: %s" % (num, str(err or "błąd").rstrip(".") + "."))
        return msg

    @staticmethod
    def _project_id(data, want):
        """Id projektu z id, nazwy albo aliasu; '' gdy nie ma."""
        if any(p["id"] == want for p in data["projects"]):
            return want
        low = str(want or "").strip().lower()
        return next((p["id"] for p in data["projects"] if low in ((p.get("name") or "").lower(),
                                                                (p.get("alias") or "").lower())), "")

    @classmethod
    def _match_task(cls, data, pid, title, only=False, allowed=None):
        """Zadanie do uruchomienia po tytule: najpierw otwarte, potem zrobione. pid: id, nazwa albo alias projektu;
        only: szukaj tylko w tym projekcie; allowed: szukaj tylko w tych projektach (Rozmowa w projekcie)."""
        if pid and not any(p["id"] == pid for p in data["projects"]):
            pid = cls._project_id(data, pid) or (pid if only else "")
        want = _norm_title(title)
        cands = [t for t in data["tasks"] if t.get("kind") != "publikacja" and (not pid or t["project"] == pid)
                 and (allowed is None or t["project"] in allowed) and _norm_title(t["title"]) == want]
        if not cands and allowed is not None and pid:      # tytuł z innej części tego samego projektu
            cands = [t for t in data["tasks"] if t.get("kind") != "publikacja" and t["project"] in allowed
                     and _norm_title(t["title"]) == want]
        order = {"todo": 0, "blocked": 1, "doing": 2, "done": 3}
        cands.sort(key=lambda t: order.get(t.get("state"), 2))
        return cands[0] if cands else None

    def launch_task(self, task, data, pm=False):
        """Uruchomienie z rozmowy przez run_task, z tymi samymi regułami co przycisk „Uruchom”. Zwraca wiadomość
        panelu: „Uruchomiono: …”, „W kolejce: …” albo „Nie uruchomiono „…”: powód.”"""
        msg = self._panel_msg(task)
        title = task["title"]
        live = self._live_keys()
        key = (task["project"], task["file"], title)
        if key in live:
            msg.update(runId=live[key], text="Już w toku: %s" % title)
            return msg

        def no(why):
            msg["text"] = "Nie uruchomiono „%s”: %s" % (title, why)
            return msg
        block = self.run_block(task, data["projectsSource"], live)
        if block:
            return no(block[0].lower() + block[1:].rstrip(".") + ".")
        if task.get("executor") not in AGENT_EXECUTORS:
            return no("zadanie nie ma wykonawcy agenta (kto: agent, claude albo codex).")
        code, err, extra = self.run_task(task["id"], title, pm=pm)
        if code != 200:
            return no((err or "błąd").rstrip(".") + ".")
        rec = self.get(extra["id"]) or {}
        msg["runId"] = extra["id"]
        if rec.get("state") == "queued":
            with self._lock:
                busy = [r["title"] for r in self._runs.values() if r["state"] == "running" and r["id"] != extra["id"]]
            msg["text"] = ("W kolejce: agent pracuje nad „%s”, to zadanie ruszy po nim." % _short(busy[0], 120)
                           if busy else "W kolejce: %s" % title)
        else:
            msg["text"] = "Uruchomiono: %s" % title
        return msg

    def panel_view(self, msgs):
        """Wiadomości rozmowy; przy wiadomościach panelu bieżący stan uruchomienia: taskId (obecne id zadania, link do
        szczegółów), live (stan rekordu: queued, running, done, error…) i label (krótko: w kolejce, w toku, do odbioru,
        zrobione, blokada…). Stan liczony przy odczycie, więc aktualizuje się sam."""
        if not any(m.get("role") == PANEL_ROLE for m in msgs):
            return list(msgs)
        data, _ = self.load_projects(resolve=False)
        tasks = {(t["project"], t["file"], t["title"]): t for t in data["tasks"]}
        out = []
        for m in msgs:
            if m.get("role") == PANEL_ROLE:
                t = tasks.get((m.get("project"), m.get("file"), m.get("title")))
                with self._lock:
                    rec = dict(self._runs.get(m.get("runId") or "") or {})
                live, label = rec.get("state", ""), ""
                if live == "queued":
                    label = "w kolejce"
                elif live == "running":
                    label = "w toku"
                elif t and t.get("state") == "blocked":
                    label = "blokada" + (": " + _short(t["blocked"], 80) if t.get("blocked") else "")
                elif live == "done":
                    label = ("do odbioru" if t and "odbiór" in needs_of(t) else
                             "zrobione" if t and t.get("state") == "done" else "skończone")
                elif live:
                    label = STATE_LABEL.get(live, live)
                m = dict(m, taskId=t["id"] if t else "", live=live, label=label)
            out.append(m)
        return out

    # ---------- rozmowa o projekcie: postęp, zadania, anulowanie ----------
    def _project_chat_file(self, pid):
        return os.path.join(self.runs_dir, "czat", "projekt-" + hashlib.sha1(str(pid).encode("utf-8")).hexdigest() + ".json")

    def project_chat_get(self, pid):
        """Historia rozmowy o projekcie: (kod, błąd, {"messages", "pending", "error"})."""
        _, index = self.load_projects(resolve=False)
        if str(pid) not in index:
            return 404, "Nie ma tego projektu.", {}
        path = self._project_chat_file(pid)
        with self._chat_lock:
            chat = self._chat_read(path)
            live = path in self._chat_live
        if chat["pending"] and not live:
            chat["error"] = chat["error"] or "Odpowiedź przerwana. Wyślij wiadomość jeszcze raz."
        return 200, "", {"messages": self.panel_view(chat["messages"]), "pending": live, "error": chat["error"]}

    @staticmethod
    def project_chat_tools(folder):
        """Uprawnienia do plików jednego projektu w rozmowach: odczyt oraz edycja tylko ZADANIA.md, DECYZJE.md
        i kampanie/ (karta i dowiązania w folderze projektu). (allow, deny, folder karty)."""
        cards = os.path.dirname(os.path.realpath(os.path.join(folder, "KARTA.md")))
        allow = ["Read", "Grep", "Glob", "LS"]
        for base in dict.fromkeys([cards, folder]):
            b = base.rstrip("/")                    # ścieżka bezwzględna: reguła Edit(//…)
            allow += ["Edit(/%s/ZADANIA.md)" % b, "Edit(/%s/DECYZJE.md)" % b, "Edit(/%s/kampanie/**)" % b]
        return ",".join(allow), CHAT_DENY, cards

    def chat_tools(self, folders):
        """Narzędzia obu rozmów (Asystent i Rozmowa w projekcie), te same reguły: odczyt, internet do odczytu
        (PANEL_ASYSTENT_INTERNET), edycja tylko ZADANIA.md, DECYZJE.md i kampanie/ podanych projektów; zabronione
        wprost: powłoka, zapis innych plików, pomocnicy i przepływy (ASSIST_DENY). (allow, deny, katalogi --add-dir)."""
        allow, dirs = ["Read", "Grep", "Glob", "LS"] + (list(self.ASSIST_WEB) if self.assist_web else []), []
        for folder in folders:
            a, _, cards = self.project_chat_tools(folder)
            allow += [x for x in a.split(",")[4:] if x not in allow]
            dirs += [d for d in (cards, folder) if d not in dirs]
        return allow, self.ASSIST_DENY, dirs

    def chat_args(self, folders, stream=False):
        """Wywołanie claude dla rozmowy: ten sam model (PANEL_ASYSTENT_MODEL), tryb uprawnień default (bez pytań
        w -p: wszystko poza listą jest odrzucane), te same narzędzia i katalogi, bez MCP."""
        allow, deny, dirs = self.chat_tools(folders)
        args = _command(self.tool_path("claude")) + ["-p"]
        args += (["--input-format", "stream-json", "--output-format", "stream-json", "--verbose",
                  "--include-partial-messages"] if stream else ["--output-format", "json"])
        args += ["--permission-mode", "default", "--model", self.assist_model]
        for d in dirs:
            args += ["--add-dir", d]
        return args + ["--allowedTools", ",".join(allow), "--disallowedTools", deny, "--strict-mcp-config"]

    @staticmethod
    def run_rules(prefix, today):
        """Zasady rozmów o pracy agentów: prośba o pracę = zadanie agenta i wiersz „Uruchom:”; polecenie do
        istniejącego zadania albo pracującego agenta = „Polecenie:”."""
        return [
            "- Gdy właściciel prosi o wykonanie pracy (zrób, przygotuj, napisz, napraw, sprawdź…), nie robisz jej sam: "
            "dopisz w ZADANIA.md projektu zadanie agenta `- [ ] <Tytuł od czasownika> | kto: agent | kiedy: %s` "
            "(w etapie, którego dotyczy, inaczej w „## Do rozplanowania”) z wciętymi o 2 spacje wierszami "
            "`  cel: …` i `  gotowe gdy: …` z prośby. Pasujące otwarte zadanie agenta wykorzystaj zamiast "
            "zakładać nowe. Potem na samym końcu odpowiedzi dodaj wiersz `Uruchom: %s<dokładny tytuł zadania>`; "
            "panel uruchomi agenta i sam pokaże stan, więc nie piszesz, że praca ruszyła." % (today.isoformat(), prefix),
            "- Gdy właściciel daje polecenie albo uwagi do istniejącego zadania agenta (popraw, zmień, dodaj w tym "
            "zadaniu; także gdy agent nad nim właśnie pracuje), nie zakładaj nowego zadania: na końcu odpowiedzi dodaj "
            "wiersz `Polecenie: %s<dokładny tytuł zadania> | <polecenie dla agenta jednym zdaniem>`. Panel zapisze je "
            "pod zadaniem (poprawka:) i uruchomi agenta albo przekaże je pracującemu agentowi." % prefix,
            "- Pytanie o stan, termin czy plan to nie prośba o pracę: wtedy bez nowego zadania, bez „Uruchom:” "
            "i bez „Polecenie:”. „wymaga: zgoda” dopisujesz tylko, gdy praca wysyła coś na zewnątrz (publikacja, "
            "wysyłka, płatność); takie zadanie czeka na zgodę właściciela w panelu.",
            "- Zadań `kto: ty` nie uruchamiasz i nie dajesz im poleceń: to praca właściciela.",
            FIELDS_RULE,
        ]

    @staticmethod
    def chat_rules(prefix, today, sites=()):
        """Zasady wspólne obu rozmów (Asystent i Rozmowa w projekcie): pliki, działania, twarde granice."""
        return [
            "- Pliki zmieniasz tylko na prośbę albo zgodę właściciela (np. zamknij, anuluj, przesuń, zmień termin, "
            "dodaj zadanie) i tylko ZADANIA.md, DECYZJE.md oraz pliki w kampanie/, w formacie ze STANDARD.md. "
            "Gdy prośba jest niejasna, dopytaj zamiast zgadywać.",
            "- Anulowanie: stan [x] i wcięty wiersz `wynik: anulowane %s na prośbę właściciela: <powód>`. "
            "Wierszy nie usuwasz. Decyzję, która zmienia plan, dopisz krótko do DECYZJE.md." % today.strftime("%d.%m"),
            "- Po każdej zmianie pliku napisz przed wierszami działań wiersz zaczynający się od „Zmieniono:” "
            "z projektem, plikiem i zadaniem.",
            "- Odpowiedź właściciela na pytanie z sekcji „Pytania do właściciela” karty zapisuje panel: dodaj na końcu "
            "wiersz `Odpowiedź na pytanie: %s<numer pytania> | <odpowiedź właściciela>`. Propozycję przyjmujesz tylko "
            "na wyraźne „tak” właściciela. Sam nie odpowiadasz za właściciela." % prefix,
            ] + Manager.site_rule(list(sites)) + Manager.run_rules(prefix, today) + [
            "- Wiersze `Uruchom:`, `Polecenie:` i `Odpowiedź na pytanie:` są zawsze na samym końcu, każdy w osobnym "
            "wierszu; panel wykonuje je i nie pokazuje ich właścicielowi.",
            "- Nie zmieniasz kart (KARTA.md), kodu ani innych plików, nie uruchamiasz poleceń, nic nie publikujesz "
            "i nie wysyłasz. Nigdy nie proś o hasła, klucze ani tokeny.",
        ]

    @staticmethod
    def site_links(data, ids=None):
        """[(nazwa, adres zakładki Strona w panelu)] projektów z polem karty strona: (ids: tylko te projekty).
        Część: #p-<główny>-strona?cz=<część>; projekt główny z częściami: ?cz=<jego id>; bez części: #p-<id>-strona."""
        projects = data.get("projects") or []
        heads = {x.get("partOf") for x in projects if x.get("partOf")}
        out = []
        for p in projects:
            if not p.get("site") or (ids is not None and p["id"] not in ids):
                continue
            pid, top = p["id"], p.get("partOf") or ""
            href = ("#p-%s-strona?cz=%s" % (top, pid) if top else
                    "#p-%s-strona?cz=%s" % (pid, pid) if pid in heads else "#p-%s-strona" % pid)
            out.append((p.get("name") or pid, href))
        return out

    @staticmethod
    def site_rule(links):
        """Zasada o podglądzie strony: link do zakładki zamiast opisu drogi w panelu."""
        if not links:
            return []
        return ["- Podgląd strony (zakładka Strona w panelu): nie opisuj drogi do niego. Podaj link w postaci "
                "[Otwórz podgląd](adres), adres z listy: " + "; ".join("%s: %s" % x for x in links) + "."]

    def project_chat_prompt(self, project, folder, cards, text, parts=(), sites=()):
        """parts: [(nazwa części, folder karty części)] projektu z częściami (pole karty „część projektu:”);
        sites: site_links projektu i jego części."""
        name = project.get("name") or project.get("id")
        today = datetime.date.today()
        lines = ["Rozmawiasz z właścicielem o projekcie „%s” (id %s) w Rozmowie w projekcie panelu. Dziś jest %s (%s)."
                 % (name, project.get("id"), today.isoformat(), PL_DAYS[today.weekday()]),
                 "", "Pliki projektu (czytaj je przed odpowiedzią):",
                 "- karta: %s" % os.path.join(cards, "KARTA.md"),
                 "- zadania: %s" % os.path.join(cards, "ZADANIA.md"),
                 "- kampanie: %s (pliki .md, sekcja Harmonogram)" % os.path.join(cards, "kampanie"),
                 "- decyzje: %s" % os.path.join(cards, "DECYZJE.md"),
                 "- format wierszy: %s" % os.path.join(self.root, "standard", "STANDARD.md"),
                 "- dokumenty projektu: %s" % folder,
                 ] + ([
                 "", "Projekt ma części z osobnymi plikami (czytasz i zmieniasz je tak samo; w wierszach działań "
                 "podaj id części):"] + ["- %s (id %s): %s" % (n, i, os.path.join(c, "ZADANIA.md")) for n, c, i in parts]
                 if parts else []) + [
                 "", "Zasady:",
                 "- Rozmawiacie o zadaniach, postępie, terminach i o tym, co właściciel ma zrobić w najbliższych dniach "
                 "(zadania z „kto: ty”, filmy do nagrania dzień przed publikacją, publikacje). Krótko, prostym językiem "
                 "po polsku, bez żargonu technicznego.",
                 "- Wiadomość może zaczynać się od [zadanie: …] z kontekstem zadania, o które pyta właściciel "
                 "(szczegóły, ostatnie uruchomienie). Odpowiadasz wtedy o tym zadaniu i działasz na nim. Gdy zadanie "
                 "wygląda na zbędne, błędne albo niejasne, powiedz to wprost i zaproponuj jedną zmianę w zdaniu "
                 "zaczynającym się od „Propozycja:”.",
                 ] + self.chat_rules("%s | " % project.get("id"), today, sites) + [
                 "", "Wiadomość właściciela:", text]
        return "\n".join(lines) + "\n"

    def task_context(self, task, data, index):
        """Kontekst zadania dla wiadomości z „Zapytaj o to zadanie”: tytuł, plik, stan, szczegóły, ostatnie
        uruchomienie. Dodawany przed każdą wiadomością z odnośnikiem (także w trwającej sesji)."""
        name = next((p.get("name") or p["id"] for p in data["projects"] if p["id"] == task["project"]), task["project"])
        stage = next((s["title"] for s in data.get("stages") or [] if s["id"] == task.get("stage")), "")
        head = "[zadanie: „%s” | projekt %s (id %s) | plik %s, wiersz %s | stan: %s | kto: %s%s%s]" % (
            task["title"], name, task["project"], task["file"], task.get("line"), task.get("state") or "todo",
            task.get("executor") or "brak", " | termin: %s" % task["date"] if task.get("date") else "",
            " | etap: %s" % stage if stage else "")
        lines = [head]
        more = self.detail_lines(with_answers(task, data["tasks"]))
        if more:
            lines += ["Szczegóły zadania:"] + more
        with self._lock:
            runs = [r for r in self._runs.values() if r.get("kind") == "task" and r.get("project") == task["project"]
                    and r.get("title") == task["title"]]
        if runs:
            r = max(runs, key=lambda x: str(x.get("queuedAt") or ""))
            bits = [STATE_LABEL.get(r.get("state"), r.get("state") or ""), "narzędzie %s" % (r.get("tool") or "?")]
            if r.get("endedAt"):
                bits.append("koniec %s" % str(r["endedAt"])[:16].replace("T", " "))
            if r.get("error"):
                bits.append("błąd: %s" % _short(r["error"], 300))
            if r.get("result"):
                bits.append("wynik: %s" % _short(r["result"], 600))
            if r.get("branch"):
                bits.append("gałąź %s" % r["branch"])
            lines.append("Ostatnie uruchomienie agenta: %s." % "; ".join(b for b in bits if b))
        else:
            lines.append("Ostatnie uruchomienie agenta: brak.")
        return "\n".join(lines)

    def project_chat_send(self, pid, message, task_id="", execute=False, attach=None, spoken=False):
        """Wiadomość właściciela w Rozmowie w projekcie; odpowiedź w tle (project_chat_get). (kod, błąd, dodatki).
        task_id: odnośnik do zadania („Zapytaj o to zadanie”): kontekst zadania przed wiadomością; execute (albo
        „zrób to” na końcu) przy zadaniu agenta: polecenie dla agenta bez modelu (chat_execute). attach: załącznik
        ze Strony {"kind": "strona", "project", "page", "view", "selector", "elementText"}: uwaga do strony
        (site.add_note: zadanie agenta strony i run_task albo wiadomość do pracującego agenta), bez modelu."""
        text = str(message or "").strip()
        if not text:
            return 400, "Napisz wiadomość.", {}
        if len(text) > CHAT_MAX:
            return 400, "Najwyżej %d znaków." % CHAT_MAX, {}
        data, index = self.load_projects()
        pid = str(pid)
        if pid not in index:
            return 404, "Nie ma tego projektu.", {}
        if data["projectsSource"] != "registry":
            return 409, "Projekty przykładowe", {}
        fam = self.family(data, pid)
        task = None
        if task_id:
            task = next((t for t in data["tasks"] if t["id"] == str(task_id)), None)
            if not task or task["project"] not in fam:
                return 404, "Nie ma tego zadania w tym projekcie.", {}
        if isinstance(attach, dict) and attach.get("kind") == "strona":
            return self._site_note(pid, fam, text, attach, spoken)
        if task and (execute is True or EXEC_END.search(text)):
            if task.get("executor") in AGENT_EXECUTORS and task.get("kind") != "publikacja":
                return self.chat_execute(task, index, text, spoken=spoken)
        path = self.tool_path("claude")
        if not path:
            return 409, "Brak polecenia claude", {}
        with self._lock:
            login = self._state["needsLogin"]
        if login:
            return 409, "Wymaga logowania: %s" % self.login_cmd("claude", path), {}
        limit = self.limit_until()
        if limit:
            return 409, "Limit subskrypcji. Odnowienie o %s." % limit[11:16], {}
        folder = index[pid]
        project = next((p for p in data["projects"] if p["id"] == pid), {"id": pid})
        file = self._project_chat_file(pid)
        with self._chat_lock:
            if file in self._chat_live:
                return 409, "Czekam jeszcze na odpowiedź.", {}
            if len(self._chat_live) >= CHAT_PARALLEL:
                return 409, "Za dużo rozmów naraz. Spróbuj za chwilę.", {}
            chat = self._chat_read(file)
            session = self._chat_session(chat)
            mine = {"role": "ty", "text": text, "at": now_iso()}
            if spoken:
                mine["spoken"] = True
            if task:
                mine["task"] = {"id": task["id"], "title": task["title"], "project": task["project"]}
            chat["messages"].append(mine)
            chat.update(pending=True, error="")
            try:
                self._chat_write(file, chat)
            except OSError:
                return 500, "Nie udało się zapisać rozmowy.", {}
            self._chat_live.add(file)
            self._chat_meta[file] = {"taskId": task["id"] if task else "", "project": pid,
                                     "file": task["file"] if task else "", "since": now_iso(),
                                     "title": ("Rozmowa w projekcie %s: %s" % (project.get("name") or pid, task["title"])
                                               if task else "Rozmowa w projekcie %s" % (project.get("name") or pid))}
            self._chat_save()
        try:
            folders = [index[i] for i in sorted(fam) if i in index and i != pid]
            cards = os.path.dirname(os.path.realpath(os.path.join(folder, "KARTA.md")))
            parts = [(x.get("partLabel") or x["id"],
                      os.path.dirname(os.path.realpath(os.path.join(index[x["id"]], "KARTA.md"))), x["id"])
                     for x in data["projects"] if x.get("partOf") == pid and x["id"] in index]
            sites = self.site_links(data, fam)
            body = (self.task_context(task, data, index) + "\n\n" + text) if task else text
            prompt = body + "\n" if session else self.project_chat_prompt(project, folder, cards, body, parts, sites)
            args = self.chat_args([folder] + folders)
            if session:
                args[args.index("-p") + 1:args.index("-p") + 1] = ["--resume", session]
            threading.Thread(target=self._chat_run, args=(file, args, folder, prompt, bool(session), pid),
                             daemon=True).start()
        except Exception:
            self._chat_end(file, "", "", "Nie udało się uruchomić rozmowy.")
            return 500, "Nie udało się uruchomić rozmowy.", {}
        return 202, "", {"pending": True}

    def _site_note(self, pid, fam, text, attach, spoken=False):
        """Uwaga ze Strony wysłana z Rozmowy w projekcie (załącznik: podstrona, widok, wskazany element): ta sama
        droga co dawny formularz Strony (site.add_note). Wiadomość i stan zostają w rozmowie."""
        site_pid = str(attach.get("project") or pid)
        if site_pid not in fam:
            return 404, "Strona nie należy do tego projektu.", {}
        body = {"project": site_pid, "text": text, "view": attach.get("view"), "page": attach.get("page"),
                "selector": attach.get("selector"), "elementText": attach.get("elementText")}
        code, err, extra = self.site.add_note(body)
        if code != 200:
            return code, err, extra
        att = {k: str(attach.get(k) or "")[:300] for k in ("project", "page", "view", "selector", "elementText")}
        att["kind"] = "strona"
        note = extra.get("note") or {}
        msg = self._panel_msg({"project": site_pid, "file": "ZADANIA.md", "title": note.get("title", "")})
        msg["runId"] = extra.get("runId", "")
        if extra.get("forwarded"):
            msg["text"] = "Agent strony już pracuje: %s" % extra["forwarded"]
        elif note.get("state") == "czeka" and note.get("error"):
            msg["text"] = note["error"]
        else:
            msg["text"] = "Uwaga do strony: zadanie „%s” dla agenta." % note.get("title", "")
        mine = {"role": "ty", "text": text, "at": now_iso(), "attach": att}
        if spoken:
            mine["spoken"] = True
        self._chat_append(self._project_chat_file(pid), [mine, msg])
        return 200, "", dict(extra, status=self.panel_view([msg])[0])

    # ---------- asystent: rozmowa o wszystkich projektach (Start i przycisk w każdym widoku) ----------
    ASSIST = "*asystent"
    ASSIST_DENY = CHAT_DENY     # obie rozmowy; bez WebSearch i WebFetch przy PANEL_ASYSTENT_INTERNET (w __init__)
    ASSIST_WEB = ("WebSearch", "WebFetch")
    ASSIST_TABS = ("plan", "tablica", "marketing", "etapy", "wskazniki", "ksiega")
    ASSIST_VIEWS = (("#asystent", "Asystent: ta strona, karty"), ("#marketing", "Marketing: publikacje i nagrania"),
                    ("#media", "Media"), ("#agenci", "Agenci: Teraz, plan dnia, uruchomienia"),
                    ("#koszty", "Serwer: stan, kalendarz, projekty i Księga, koszty"))

    def assistant_get(self):
        """Historia rozmowy z asystentem: (kod, błąd, {"messages", "pending", "error", "partial", "activity", "voice"}).
        partial: tekst odpowiedzi w trakcie pisania (stała sesja), activity: co asystent teraz robi."""
        path = self._project_chat_file(self.ASSIST)
        with self._chat_lock:
            chat = self._chat_read(path)
            live = path in self._chat_live
            cur = dict(self._as_live) if live else {}
        if chat["pending"] and not live:
            chat["error"] = chat["error"] or "Odpowiedź przerwana. Wyślij wiadomość jeszcze raz."
        msgs = []
        for m in self.panel_view(chat["messages"][-40:]):
            if m.get("role") == "claude":
                text, ops = karty.extract(m.get("text", ""))
                m = dict(m, text=text, cards=ops)
            msgs.append(m)
        return 200, "", {"messages": msgs, "pending": live, "error": chat["error"],
                         "partial": cur.get("partial", ""), "activity": cur.get("activity", ""),
                         "voice": self.voice.available()}

    def _assistant_keep_cards(self, answer):
        """Karty z "zapisz": true trafiają do biblioteki (następnym razem model poda samo id)."""
        _, ops = karty.extract(answer)
        try:
            self.cards.save([c for c in ops["pokaz"] if c.get("zapisz")])
        except (karty.Bad, OSError):
            pass

    def assistant_cards_get(self):
        """GET /api/asystent/karty: biblioteka, karty wbudowane i układ płótna."""
        lib = self.cards.read()
        return 200, "", {"karty": sorted(lib["karty"].values(), key=lambda c: c["id"]), "wbudowane": karty.STARTERS,
                         "start": list(karty.START), "przypiete": lib["przypiete"], "ukryte": lib["ukryte"]}

    def assistant_cards_post(self, body):
        """POST /api/asystent/karty: {"zapisz": karta} | {"usun": id} | {"przypiete": [id]} | {"ukryj": id} |
        {"pokaz": id}. Zmiany tylko z sesją (jak każdy zapis panelu)."""
        ops = [k for k in ("zapisz", "usun", "przypiete", "ukryj", "pokaz") if k in body]
        if len(ops) != 1:
            return 400, "Jedno działanie: zapisz, usun, przypiete, ukryj albo pokaz.", {}
        op, val = ops[0], body[ops[0]]
        try:
            if op == "zapisz":
                if not isinstance(val, dict) or "dane" in val:
                    return 400, "Zapisać można kartę z zapytaniem.", {}
                code, err, ids = self.cards.save([val])
                if code == 200 and not ids:
                    return 400, "Zapisać można kartę z zapytaniem.", {}
                return code, err, {"zapisane": ids}
            if op == "przypiete":
                if not isinstance(val, list) or len(val) > 60 or not all(isinstance(x, str) and karty.ID_RE.match(x) for x in val):
                    return 400, "Lista id kart (najwyżej 60).", {}
                return self.cards.layout(pins=val) + ({},)
            if not isinstance(val, str) or not karty.ID_RE.match(val):
                return 400, "Nieprawidłowe id karty.", {}
            if op == "usun":
                return self.cards.remove(val) + ({},)
            if op == "ukryj":
                return self.cards.layout(hide=val, at=now_iso()) + ({},)
            return self.cards.layout(show=val) + ({},)
        except karty.Bad as e:
            return 400, str(e)[:300], {}
        except OSError:
            return 500, "Nie udało się zapisać biblioteki kart.", {}

    @staticmethod
    def assistant_facts(data, today, counts=None):
        """Krótkie fakty dla asystenta (bez czytania plików przy pytaniu „co mam zrobić”): Twoje sprawy na 7 dni,
        publikacje na 7 dni, po terminie, postęp projektów. Przy sprawach id zadania (działanie „Otwórz:”)."""
        names = {p["id"]: p.get("name") or p["id"] for p in data["projects"]}
        active = {p["id"] for p in data["projects"] if p.get("state") not in ("backlog", "paused", "done")}
        week = (today + datetime.timedelta(days=7)).isoformat()
        tk = today.isoformat()
        mine, late, pubs = [], [], []
        for t in data["tasks"]:
            if t.get("state") == "done" or t.get("project") not in active:
                continue
            d = t.get("date") or ""
            line = "- %s | %s | %s%s%s" % (names[t["project"]], t.get("title", ""), d or "bez daty",
                                          " | czeka na: " + t["needsYou"] if t.get("needsYou") else "",
                                          " | id: " + t["id"] if t.get("id") else "")
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d[:10]) and d[:10] < tk:
                late.append(line)
            elif t.get("kind") == "publikacja":
                if d and d[:10] <= week:
                    pubs.append(line)
            elif (t.get("executor") == "ty" or t.get("needsYou")) and (not d or d <= week):
                mine.append(line)
        prog = []
        for pid in active:
            ts = [t for t in data["tasks"] if t.get("project") == pid and t.get("kind") != "publikacja"]
            if ts:
                done = sum(1 for t in ts if t.get("state") == "done")
                prog.append("- %s: %d%% (%d z %d zadań)" % (names[pid], round(100 * done / len(ts)), done, len(ts)))
        by_date = lambda x: x.split(" | ")[2]  # noqa: E731
        c = counts or projekt_counts(data, today)
        out = ["Liczby spraw (te same co w panelu; podawaj tylko je, z tymi podpisami, nie licz sam):",
               "- sprawy dla Ciebie na dziś: %d, w tym po terminie: %d" % (c["youToday"], c["youLate"]),
               "- sprawy dla Ciebie w ciągu 7 dni: %d, później: %d" % (c["youWeek"], c["youLater"]),
               "- wszystkie zadania po terminie (także agentów): %d" % c["late"], ""]
        out += ["Postęp projektów:"] + (sorted(prog) or ["- brak"])
        out += ["", "Twoje sprawy (kto: ty albo czeka na Ciebie) do %s, bez po terminie:" % week] + (sorted(mine, key=by_date)[:40] or ["- brak"])
        out += ["", "Publikacje do %s:" % week] + (sorted(pubs, key=by_date)[:20] or ["- brak"])
        out += ["", "Po terminie (wszystkie, także agentów; pokazano %d z %d):" % (min(len(late), 30), len(late))] + (late[:30] or ["- brak"])
        return "\n".join(out)

    @staticmethod
    def _assistant_open(data, opened):
        """Opis zadania otwartego w panelu (szuflada) albo ''."""
        opened = str(opened or "")[:300]
        t = next((x for x in data["tasks"] if opened and x.get("id") == opened), None)
        if not t:
            return ""
        kind = "publikacja" if t.get("kind") == "publikacja" else "zadanie"
        return "%s „%s” (id: %s)" % (kind, re.sub(r"\s+", " ", t.get("title", ""))[:160], t["id"])

    def _assistant_screen(self, data, view, opened):
        shown = self._assistant_open(data, opened)
        return "[ekran: %s%s]" % (view or "#asystent", "; otwarte: " + shown if shown else "")

    def assistant_prompt(self, data, index, text, view, opened=""):
        today = datetime.date.today()
        lines = ["Jesteś asystentem właściciela w panelu projektów. Dziś jest %s (%s)." % (today.isoformat(), PL_DAYS[today.weekday()]),
                 "Właściciel często mówi głosem; tekst pochodzi wtedy z rozpoznawania mowy i może przekręcać nazwy: "
                 "dopasuj je do nazw projektów i zadań. Odpowiedź czyta na ekranie: najpierw jedno zdanie odpowiedzi, "
                 "potem najwyżej 5 krótkich punktów („- …”), bez tabel, nagłówków i akapitów. Najwyżej jedna liczba "
                 "w zdaniu; listy i zestawienia liczb pokazujesz jako karty, nie w tekście.",
                 "", self.assistant_facts(data, today, self._counts()), "", "Projekty (pliki kart):"]
        for p in data["projects"]:
            folder = index.get(p["id"])
            if folder:
                cards = os.path.dirname(os.path.realpath(os.path.join(folder, "KARTA.md")))
                lines.append("- %s (id %s): %s/ZADANIA.md, kampanie: %s/kampanie" % (p.get("name") or p["id"], p["id"], cards, cards))
        lines += ["Format wierszy zadań: %s" % os.path.join(self.root, "standard", "STANDARD.md"),
                  "", "Sterowanie panelem: na samym końcu odpowiedzi możesz dodać wiersze działań, każdy w osobnym "
                  "wierszu. Panel wykonuje je po kolei i nie pokazuje ich właścicielowi:",
                  "  Pokaż: #adres            przełącza widok",
                  "  Otwórz: <id zadania>     otwiera szczegóły zadania albo publikacji (id z faktów; bez id: dokładny tytuł)",
                  "  Przewiń: <nagłówek>      przewija bieżący widok do sekcji o tym nagłówku",
                  "  Zamknij: szczegóły       zamyka otwarte zadanie",
                  "  Uruchom: <id projektu> | <dokładny tytuł>   uruchamia agenta dla zadania (zasady niżej)",
                  "  Polecenie: <id projektu> | <dokładny tytuł> | <polecenie>   polecenie do zadania agenta (zasady niżej)",
                  "  Odpowiedź na pytanie: <id projektu> | <numer> | <odpowiedź>   zapis odpowiedzi właściciela",
                  "Otwórz używaj, gdy właściciel prosi „otwórz” albo gdy szczegóły zadania pomagają. Pokaż tylko poza "
                  "stroną Asystent (ekran inny niż #asystent). Nie zapowiadaj działań w treści.",
                  "Adresy widoków: " + "; ".join("%s (%s)" % v for v in self.ASSIST_VIEWS) + ".",
                  "Projekt: #p-<id projektu> (plan), zakładki: " + ", ".join("#p-<id>-%s" % t for t in self.ASSIST_TABS) + ".",
                  "", "Zasady:",
                  "- Gdy właściciel pyta, co ma zrobić: wymień sprawy po kolei, najpierw po terminie, potem dziś. Przy sprawie, "
                  "która wymaga zgody lub odbioru, opisz ją jednym zdaniem i zapytaj „Zatwierdzasz?”. Na „tak” zamknij ją w pliku, "
                  "na poprawki wprowadź poprawki. Jedna sprawa naraz.",
                  ] + self.chat_rules("<id projektu> | ", today, self.site_links(data)) + [
                  "- Każda kolejna wiadomość zaczyna się od [ekran: …] (co właściciel ma teraz przed sobą); gdy dane się "
                  "zmienią, dostaniesz też nowe fakty.",
                  "", karty.PROMPT] + ([karty.PROMPT_WEB] if self.assist_web else []) + [
                  "", self._assistant_library(), "",
                  self._assistant_screen(data, view, opened), "", "Wiadomość właściciela:", text]
        return "\n".join(lines) + "\n"

    def _counts(self):
        """Liczby spraw z ostatniej odpowiedzi /api/data (serwer ustawia counts_hook); bez niej None (liczy facts)."""
        hook = getattr(self, "counts_hook", None)
        try:
            c = hook() if hook else None
        except Exception:  # noqa: BLE001  (fakty rozmowy nie mogą jej przerwać)
            c = None
        return c if isinstance(c, dict) and all(k in c for k in self.projekt.OWNER_COUNT_KEYS) else None

    def _assistant_library(self):
        return "Karty gotowe (id, typ, tytuł):\n" + "\n".join(self.cards.summary())

    def _assistant_tools(self, index):
        """Narzędzia Asystenta: chat_tools wszystkich projektów (te same reguły co Rozmowa w projekcie)."""
        allow, _, dirs = self.chat_tools(list(index.values()))
        return allow, dirs

    def assistant_send(self, message, view="", opened=""):
        text = str(message or "").strip()
        view = re.sub(r"[^\w#?=&.-]", "", str(view or ""))[:80]
        if not text:
            return 400, "Napisz albo powiedz wiadomość.", {}
        if len(text) > CHAT_MAX:
            return 400, "Najwyżej %d znaków." % CHAT_MAX, {}
        data, index = self.load_projects()
        if data["projectsSource"] != "registry":
            return 409, "Projekty przykładowe", {}
        path = self.tool_path("claude")
        if not path:
            return 409, "Brak polecenia claude", {}
        with self._lock:
            login = self._state["needsLogin"]
        if login:
            return 409, "Wymaga logowania: %s" % self.login_cmd("claude", path), {}
        limit = self.limit_until()
        if limit:
            return 409, "Limit subskrypcji. Odnowienie o %s." % limit[11:16], {}
        file = self._project_chat_file(self.ASSIST)
        with self._chat_lock:
            if file in self._chat_live:
                return 409, "Czekam jeszcze na odpowiedź.", {}
            if len(self._chat_live) >= CHAT_PARALLEL:
                return 409, "Za dużo rozmów naraz. Spróbuj za chwilę.", {}
            chat = self._chat_read(file)
            session = self._chat_session(chat)
            chat["messages"].append({"role": "ty", "text": text, "at": now_iso()})
            del chat["messages"][:-60]
            chat.update(pending=True, error="")
            try:
                self._chat_write(file, chat)
            except OSError:
                return 500, "Nie udało się zapisać rozmowy.", {}
            self._chat_live.add(file)
            self._as_live = {"partial": "", "activity": ""}
            self._chat_meta[file] = {"taskId": "", "project": "", "file": "", "since": now_iso(), "title": "Asystent"}
            self._chat_save()
        try:
            args = self.chat_args(list(index.values()), stream=True)
            threading.Thread(target=self._assistant_turn, args=(file, args, session, data, index, text, view, opened),
                             daemon=True).start()
        except Exception:
            self._chat_end(file, "", "", "Nie udało się uruchomić rozmowy.")
            return 500, "Nie udało się uruchomić rozmowy.", {}
        return 202, "", {"pending": True}

    def _as_update(self, **kw):
        with self._chat_lock:
            self._as_live.update(kw)

    def _assistant_turn(self, file, args, session, data, index, text, view, opened):
        """Wątek jednej wiadomości: stała sesja (start albo wznowienie przy potrzebie), odpowiedź z kawałkami tekstu."""
        answer, error, dropped = "", "", False
        try:
            facts = self.assistant_facts(data, datetime.date.today(), self._counts())
            stamp = hashlib.sha1(facts.encode("utf-8")).hexdigest()
            lib = self._assistant_library()
            lib_stamp = hashlib.sha1(lib.encode("utf-8")).hexdigest()
            key = hashlib.sha1(json.dumps(args).encode("utf-8")).hexdigest()
            for attempt in (0, 1):
                fresh = not session
                if fresh:
                    prompt = self.assistant_prompt(data, index, text, view, opened)
                else:
                    head = self._assistant_screen(data, view, opened)
                    if stamp != self._as_facts:
                        head += "\nAktualne fakty (dane się zmieniły):\n" + facts
                    if lib_stamp != self._as_lib:
                        head += "\n" + lib
                    prompt = head + "\n" + text
                if not self._as.alive(key):
                    self._as.start(self.as_agent(args + (["--resume", session] if session else [])), cwd=self.root,
                                   env=child_env(self.env), key=key, resumed=bool(session))
                resumed = self._as.resumed
                res = self._as.turn(prompt, on_text=lambda t: self._as_update(partial=t[:AS_ANSWER], activity=""),
                                    on_tool=lambda a: self._as_update(activity=a), timeout=self.chat_timeout)
                if res["ok"]:
                    answer, session = res["text"][:AS_ANSWER], res["session"] or session
                    self._as_facts, self._as_lib = stamp, lib_stamp
                    self._assistant_keep_cards(answer)
                    break
                if res["error"] == "czas":
                    error = "Brak odpowiedzi w ciągu %d s. Spróbuj ponownie." % self.chat_timeout
                    break
                blob = res["blob"]
                if LOGIN_RE.search(blob):
                    error = "Wymaga logowania: %s" % self.login_cmd("claude", self.tool_path("claude"))
                elif LIMIT_RE.search(blob):
                    error = "Limit subskrypcji. Spróbuj później."
                elif resumed and attempt == 0 and (res["error"] == "proces" or
                                                    re.search(r"no conversation found|session.{0,40}not found", blob, re.I)):
                    session, dropped = "", True     # sesja wygasła albo jej nie ma: nowa rozmowa z pełnymi faktami
                    self._as.stop(keep_watch=True)
                    self._as_update(partial="", activity="")
                    continue
                else:
                    error = "Nie udało się uzyskać odpowiedzi (kod %s)." % res["code"]
                self._as.stop(keep_watch=True)
                break
        except OSError:
            error = "Nie udało się uruchomić polecenia claude."
        except Exception:  # rozmowa nie może zostać w stanie oczekiwania
            error = "Nie udało się uzyskać odpowiedzi."
        finally:
            if not answer and not error:
                error = "Nie udało się uzyskać odpowiedzi."
            answer, extra = self._after_answer(answer, "*")
            self._chat_end(file, answer, session if answer else "", error, extra)
            if dropped and not answer:
                self._as_clear_session(file)

    def _as_clear_session(self, file):
        """Po nieudanym wznowieniu: następna wiadomość zaczyna nową rozmowę (pełny prompt z faktami)."""
        with self._chat_lock:
            try:
                chat = self._chat_read(file)
                if chat["session"]:
                    chat["session"] = ""
                    self._chat_write(file, chat)
            except OSError:
                pass

    def voice_warm(self):
        """POST /api/asystent/glos/start: model mowy wczytuje się, gdy właściciel mówi."""
        if not self.voice.available():
            return 409, "Rozpoznawanie mowy nie jest zainstalowane na serwerze.", {"voice": False}
        self.voice.warm()
        return 200, "", {}

    def voice_prompt(self, data):
        """initial_prompt dla Whisper: nazwy projektów (rozpoznawanie myli je bez podpowiedzi)."""
        names = [p.get("name") or p["id"] for p in data["projects"] if p.get("state") not in ("done",)]
        return ("Panel projektów. Projekty: %s. Zadania, etapy, marketing, publikacje, zgoda, odbiór." %
                ", ".join(names[:30]))[:600]

    def assistant_voice(self, ctype, blob, view="", opened="", draft=False):
        """Rozpoznaje nagranie; przy draft zwraca tekst do edycji, inaczej wysyła go do asystenta."""
        if not self.voice.available():
            return 409, "Rozpoznawanie mowy nie jest zainstalowane na serwerze.", {"voice": False}
        ext, err = glos.check_audio(ctype, blob)
        if err:
            return 400, err, {}
        data, _ = self.load_projects(resolve=False)
        code, err, text = self.voice.transcribe(blob, ext, self.voice_prompt(data))
        if code != 200:
            return code, err, {"voice": self.voice.available()}
        if not text:
            return 422, "Nie rozpoznano mowy. Powiedz jeszcze raz, bliżej mikrofonu.", {}
        if draft:
            return 200, "", {"text": text[:CHAT_MAX]}
        code, err, extra = self.assistant_send(text, view, opened)
        return code, err, dict(extra, text=text[:CHAT_MAX])

    def assistant_reset(self):
        file = self._project_chat_file(self.ASSIST)
        with self._chat_lock:
            if file in self._chat_live:
                return 409, "Czekam jeszcze na odpowiedź.", {}
            try:
                self._chat_write(file, {"messages": [], "pending": False, "error": "", "session": ""})
            except OSError:
                return 500, "Nie udało się wyczyścić rozmowy.", {}
        self._as.stop(keep_watch=True)          # nowa rozmowa: następna wiadomość z pełnym promptem
        self._as_facts = self._as_lib = ""
        with contextlib.suppress(OSError):
            self.cards.layout(clear_hidden=True)  # karty z poprzedniej rozmowy znikają razem z nią
        return 200, "", {}

    def _chat_run(self, file, args, cwd, prompt, resumed, launch=None):
        answer, session, error = "", "", ""
        if WINDOWS:
            kw = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | NO_WINDOW["creationflags"]}
        else:
            kw = {"start_new_session": True}
        try:
            proc = subprocess.Popen(self.as_agent(args), cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, env=child_env(self.env), encoding="utf-8",
                                    errors="replace", **kw)
            try:
                out, err = proc.communicate(prompt, timeout=self.chat_timeout)
                answer, session, error = self._chat_parse(out or "", err or "", proc.returncode, resumed)
            except subprocess.TimeoutExpired:
                self._kill(proc)
                try:
                    proc.communicate(timeout=10)
                except (OSError, ValueError, subprocess.SubprocessError):
                    pass
                error = "Brak odpowiedzi w ciągu %d s. Spróbuj ponownie." % self.chat_timeout
        except OSError:
            error = "Nie udało się uruchomić polecenia claude."
        except Exception:  # rozmowa nie może zostać w stanie oczekiwania
            error = "Nie udało się uzyskać odpowiedzi."
        finally:
            answer, extra = self._after_answer(answer, launch)
            self._chat_end(file, answer, session, error, extra)

    def _after_answer(self, answer, launch):
        """Wiersze „Uruchom:” z odpowiedzi: (odpowiedź bez nich, wiadomości panelu). launch: id projektu rozmowy
        o projekcie, "*" dla asystenta (wszystkie projekty), None bez uruchamiania (rozmowa o zadaniu)."""
        if not answer or launch is None:
            return answer, []
        try:
            return self.chat_launches(answer, "" if launch == "*" else launch)
        except Exception as e:  # odpowiedź musi trafić do rozmowy mimo błędu uruchomienia
            log("Uruchomienie z rozmowy: %s" % e)
            text, wanted = take_run_lines(answer)
            return text, [{"role": PANEL_ROLE, "at": now_iso(), "project": "", "file": "", "title": t, "runId": "",
                           "text": "Nie uruchomiono „%s”: błąd panelu." % t} for _, t in wanted]

    def _chat_end(self, file, answer, session, error, extra=()):
        with self._chat_lock:
            try:
                chat = self._chat_read(file)
                if session:
                    chat["session"], chat["v"] = session, CHAT_RULES_V
                elif error == CHAT_EXPIRED:
                    chat["session"] = ""            # następna wiadomość zaczyna rozmowę od nowa, z kontekstem
                if answer:
                    chat["messages"].append({"role": "claude", "text": answer, "at": now_iso()})
                chat["messages"] += list(extra)
                chat.update(pending=False, error=error)
                self._chat_write(file, chat)
            except OSError:
                pass
            finally:
                self._chat_live.discard(file)
                meta = self._chat_meta.pop(file, None)
                if meta:
                    self._chat_done.append(dict(meta, at=now_iso(), ok=not error, error=str(error or "")[:200]))
                    del self._chat_done[:-self.CHAT_DONE_MAX]
                self._chat_save()

    def _chat_parse(self, out, err, code, resumed):
        """Wynik `claude -p --output-format json`: (odpowiedź, sesja, błąd). Błąd krótko, bez śladu stosu."""
        try:
            res = json.loads(out)
        except ValueError:
            res = None
        if isinstance(res, list):
            for event in res:
                if isinstance(event, dict) and event.get("type") == "rate_limit_event":
                    self._claude_limit_event(event)
            res = next((x for x in reversed(res) if isinstance(x, dict) and x.get("type") == "result"), None)
        res = res if isinstance(res, dict) else None
        text = str(res.get("result") or "").strip() if res else ""
        if res and not res.get("is_error") and code == 0 and text:
            return text[:CHAT_ANSWER], str(res.get("session_id") or ""), ""
        blob = " ".join([text, out[-2000:] if res is None else "", err[-2000:]])
        if LOGIN_RE.search(blob):
            return "", "", "Wymaga logowania: %s" % self.login_cmd("claude", self.tool_path("claude"))
        if LIMIT_RE.search(blob):
            return "", "", "Limit subskrypcji. Spróbuj później."
        if resumed and re.search(r"no conversation found|session.{0,40}not found", blob, re.I):
            return "", "", CHAT_EXPIRED
        return "", "", "Nie udało się uzyskać odpowiedzi (kod %s)." % code

    @staticmethod
    def _standard_dirs(folder, file_rel):
        """Foldery plików, które agent zmienia poza katalogiem roboczym: KARTA.md, ZADANIA.md, DECYZJE.md, plik zadania."""
        dirs = []
        for name in STANDARD_LINKS + (file_rel,):
            target = os.path.realpath(os.path.join(folder, name))
            where = os.path.dirname(target)
            if os.path.exists(target) and where not in dirs:
                dirs.append(where)
        return dirs

    # ---------- gałąź uruchomienia (git worktree) ----------
    def _git_top(self, folder):
        """Katalog główny repozytorium git projektu albo ''. Folder IntegrateSystems (karty w szkice/) to nie
        repozytorium projektu: tam praca idzie jak dotąd."""
        code, out, _ = git_run(folder, ["rev-parse", "--show-toplevel"], timeout=15)
        if code != 0 or not out.strip():
            return ""
        top = os.path.realpath(out.strip())
        return "" if top == os.path.realpath(self.root) else top

    def _branch_name(self, top, title, day=None):
        short = re.sub(r"-+", "-", self.projekt.slug(title)[:40]).strip("-") or "zadanie"
        base = "agent/%s-%s" % ((day or datetime.date.today()).isoformat(), short)
        name, n = base, 2
        while git_run(top, ["rev-parse", "--verify", "-q", "refs/heads/" + name], timeout=15)[0] == 0:
            name, n = "%s-%d" % (base, n), n + 1
        return name

    @staticmethod
    def _exclude_agent_dir(top, extra=()):
        """/.agent/ (i extra: zrzuty, zależności i wynik budowania strony) w .git/info/exclude: katalogi robocze
        nie brudzą stanu repozytorium (lokalnie, bez commita)."""
        code, out, _ = git_run(top, ["rev-parse", "--git-common-dir"], timeout=15)
        if code != 0:
            return
        common = out.strip()
        path = os.path.join(common if os.path.isabs(common) else os.path.join(top, common), "info", "exclude")
        try:
            text = ""
            if os.path.exists(path):
                with open(path, encoding="utf-8", errors="replace") as f:
                    text = f.read()
            want = [x for x in ("/%s/" % AGENT_DIR,) + tuple(extra) if x not in text.split("\n")]
            if want:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "a", encoding="utf-8") as f:
                    f.write(("" if not text or text.endswith("\n") else "\n") + "\n".join(want) + "\n")
        except OSError:
            pass

    def _resume_branches(self, task):
        """Gałęzie, od których może zacząć ponowne uruchomienie zadania (np. po blokadzie z `poprawka:`): pole
        `gałąź:` zadania, potem gałęzie poprzednich uruchomień tego zadania, najnowsze najpierw. Sprawdza je
        _worktree_open (gałąź musi istnieć i mieć commity spoza bieżącej gałęzi projektu)."""
        out = []
        b = str((task.get("detail") or {}).get("branch") or "").strip()
        if b:
            out.append(b)
        key = (task["project"], task["file"], task["title"])
        with self._lock:
            for r in reversed(list(self._runs.values())):
                if r.get("kind") == "task" and (r.get("project"), r.get("file"), r.get("title")) == key \
                        and r.get("branch") and r["branch"] not in out and r.get("state") not in LIVE:
                    out.append(r["branch"])
        return [x for x in out if re.match(r"^agent/[\w./-]{1,150}$", x) and ".." not in x][:5]

    def _resume_pick(self, top, head, cands):
        """(gałąź, baza) pierwszej gałęzi z listy, która istnieje i ma commity spoza HEAD; albo ("", "")."""
        for name in cands:
            if git_run(top, ["rev-parse", "--verify", "-q", "refs/heads/%s^{commit}" % name], timeout=15)[0] != 0:
                continue
            code, out, _ = git_run(top, ["rev-list", "--count", "%s..%s" % (head, name)], timeout=15)
            if code != 0 or not out.strip().isdigit() or int(out.strip()) == 0:
                continue                         # już scalona albo pusta: zwykły start od HEAD
            code, base, _ = git_run(top, ["merge-base", head, name], timeout=15)
            if code == 0 and base.strip():
                return name, base.strip()
        return "", ""

    def _worktree_open(self, rec, priv):
        """Przed startem zadania w repozytorium git: nowa gałąź agent/RRRR-MM-DD-nazwa od bieżącego HEAD w katalogu
        <repozytorium>/.agent/<id>. Bez repozytorium (albo przy błędzie git) praca w folderze projektu jak dotąd.
        Ponowne uruchomienie zadania, którego poprzednia gałąź ma niescalone commity (pole `gałąź:` albo gałąź
        poprzedniego uruchomienia), pracuje dalej na tamtej gałęzi."""
        folder = priv["folder"]
        top = self._git_top(folder)
        if not top:
            return
        rel = os.path.relpath(os.path.realpath(folder), top)
        with self._git_lock:
            code, head, _ = git_run(top, ["rev-parse", "--verify", "-q", "HEAD^{commit}"], timeout=15)
            if code != 0:
                return self._step(rec, "git: repozytorium bez commita, praca w folderze projektu")
            head = head.strip()
            if rel != "." and not git_run(top, ["ls-tree", "-d", "HEAD", rel.replace(os.sep, "/")], timeout=15)[1].strip():
                return self._step(rec, "git: folder projektu poza repozytorium, praca w folderze projektu")
            code, cur, _ = git_run(top, ["symbolic-ref", "--short", "-q", "HEAD"], timeout=15)
            base = cur.strip() if code == 0 and cur.strip() else head
            wt = os.path.join(top, AGENT_DIR, rec["id"])
            try:
                os.makedirs(os.path.join(top, AGENT_DIR), exist_ok=True)
            except OSError:
                return self._step(rec, "git: nie utworzono katalogu %s, praca w folderze projektu" % AGENT_DIR)
            self._exclude_agent_dir(top)
            resumed, fork = self._resume_pick(top, head, priv.get("resume") or [])
            if resumed:
                code, _, err = git_run(top, ["worktree", "add", "-q", wt, resumed], timeout=300)
                if code == 0:
                    branch, start = resumed, fork
                else:
                    self._step(rec, "git: nie otwarto gałęzi %s (%s), zaczynam od %s" % (resumed, _short(err, 60), base))
                    resumed = ""
            if not resumed:
                branch, start = self._branch_name(top, rec["title"]), head
                code, _, err = git_run(top, ["worktree", "add", "-q", "-b", branch, wt, head], timeout=300)
                if code != 0:
                    return self._step(rec, "git: nie utworzono katalogu roboczego (%s), praca w folderze projektu"
                                      % _short(err, 80))
        # baseCommit: punkt rozejścia z bieżącą gałęzią projektu (przy wznowieniu zmiany całej gałęzi agenta)
        tip = git_run(top, ["rev-parse", "refs/heads/" + branch], timeout=15)[1].strip() or start
        git = {"top": top, "rel": rel, "worktree": wt, "branch": branch, "base": base, "baseCommit": start,
               "resumed": bool(resumed), "startCommit": tip}
        priv["git"] = git
        with self._lock:
            rec.update(branch=branch, base=base, baseCommit=start, startCommit=tip, changes=[], commits=0)
            if resumed:
                rec["resumed"] = True
            self._save(rec)
        if resumed:
            self._step(rec, "Dalej na gałęzi %s (poprzednia praca nad tym zadaniem)" % branch)
        else:
            self._step(rec, "Gałąź %s od %s" % (branch, base if base != head else head[:8]))
        self._task_command(priv, git)

    # ---------- części projektu: własny katalog roboczy i gałąź w repozytorium części ----------
    @staticmethod
    def part_rules(parts):
        if not parts:
            return []
        out = ["- Projekt ma części z własnym repozytorium. Zmiany w części rób wyłącznie w jej katalogu roboczym "
               "(panel założył go na osobnej gałęzi); folder części jest tylko do odczytu. Niezatwierdzone zmiany "
               "w katalogu roboczym części panel zatwierdzi na tej gałęzi po zakończeniu:"]
        out += ["  - %s: katalog roboczy %s (gałąź `%s`), folder części %s"
                % (x["label"], x["cwd"], x["branch"], x["folder"]) for x in parts]
        return out

    def _parts_open(self, rec, priv):
        """Zadanie projektu z częściami: dla każdej części z repozytorium git (innym niż repozytorium zadania)
        gałąź agent/RRRR-MM-DD-nazwa i katalog roboczy <repozytorium części>/.agent/<id>. Agent dostaje do nich
        --add-dir, a folder części (poza .agent/ i .git/) ma odmowę zapisu (Edit(//…))."""
        parts = priv.get("parts") or []
        if not parts:
            return
        own = (priv.get("git") or {}).get("top") or self._git_top(priv["folder"])
        opened = []
        for x in parts:
            if x.get("worktree"):
                opened.append(x)
                continue
            top = self._git_top(x["folder"])
            if not top or top == own:
                continue
            rel = os.path.relpath(os.path.realpath(x["folder"]), top)
            wt = os.path.join(top, AGENT_DIR, rec["id"])
            with self._git_lock:
                code, head, _ = git_run(top, ["rev-parse", "--verify", "-q", "HEAD^{commit}"], timeout=15)
                if code != 0:
                    continue
                head = head.strip()
                code, cur, _ = git_run(top, ["symbolic-ref", "--short", "-q", "HEAD"], timeout=15)
                base = cur.strip() if code == 0 and cur.strip() else head
                try:
                    os.makedirs(os.path.join(top, AGENT_DIR), exist_ok=True)
                except OSError:
                    continue
                self._exclude_agent_dir(top, (".zrzuty/", "node_modules/"))
                branch = self._branch_name(top, rec["title"])
                code, _, err = git_run(top, ["worktree", "add", "-q", "-b", branch, wt, head], timeout=300)
            if code != 0:
                self._step(rec, "git: nie utworzono katalogu roboczego części %s (%s)" % (x["label"], _short(err, 60)))
                continue
            cwd = wt if rel == "." else os.path.join(wt, rel)
            deny = []
            try:
                names = sorted(os.listdir(top))
            except OSError:
                names = []
            for name in names:
                if name in (AGENT_DIR, ".git"):
                    continue
                path = "/" + os.path.join(top, name).lstrip("/")
                deny.append("Edit(/%s)" % path)
                if os.path.isdir(os.path.join(top, name)) and not os.path.islink(os.path.join(top, name)):
                    deny.append("Edit(/%s/**)" % path)
            x.update(top=top, rel=rel, worktree=wt, cwd=cwd, branch=branch, base=base, baseCommit=head, deny=deny)
            opened.append(x)
            self._step(rec, "Część %s: gałąź %s w osobnym katalogu roboczym" % (x["label"], branch))
        if opened:
            with self._lock:
                rec["parts"] = [{"project": x["project"], "label": x["label"], "branch": x["branch"],
                                 "base": x["base"], "baseCommit": x["baseCommit"], "changes": [], "commits": 0}
                                for x in opened]
                self._save(rec)
            self._task_command(priv, priv.get("git"))

    def _parts_close(self, rec, parts):
        """Po zakończeniu: commit zmian w katalogach roboczych części, changes i commits, usunięcie katalogu;
        gałąź bez commitów znika (nic na niej nie ma)."""
        parts = [x for x in parts or [] if x.get("worktree")]
        if not parts and rec.get("parts"):
            parts = self._parts_info(rec)
        out = []
        for x in parts:
            git = {"top": x["top"], "rel": x.get("rel") or ".", "worktree": x["worktree"], "branch": x["branch"],
                   "baseCommit": x["baseCommit"]}
            probe = {"id": rec["id"], "title": rec["title"], "tool": rec.get("tool"), "file": "",
                     "branch": x["branch"]}
            self._worktree_close(probe, git, record=False)
            item = {"project": x["project"], "label": x["label"], "branch": probe["branch"], "base": x["base"],
                    "baseCommit": x["baseCommit"], "changes": probe.get("changes") or [],
                    "commits": probe.get("commits") or 0}
            if not item["commits"] and probe["branch"] == x["branch"]:
                with self._git_lock:
                    git_run(x["top"], ["branch", "-D", x["branch"]], timeout=30)
                item["branch"] = ""
            elif item["commits"]:
                self._step(rec, "Część %s: %d commit(ów) na gałęzi %s do scalenia"
                           % (x["label"], item["commits"], item["branch"]))
            out.append(item)
        if out:
            with self._lock:
                rec["parts"] = [i for i in out if i["branch"]]
                self._save(rec)

    def _parts_info(self, rec):
        """Katalogi robocze części z rekordu (uruchomienie przerwane restartem panelu)."""
        _, index = self.load_projects(resolve=False)
        out = []
        for p in rec.get("parts") or []:
            folder = index.get(p.get("project"))
            top = self._git_top(folder) if folder else ""
            if top and p.get("branch") and p.get("baseCommit"):
                out.append(dict(p, top=top, rel=os.path.relpath(os.path.realpath(folder), top),
                                worktree=os.path.join(top, AGENT_DIR, rec["id"])))
        return out

    def _worktree_info(self, rec):
        """Dane katalogu roboczego z rekordu (uruchomienie przerwane restartem serwera) albo None."""
        if not rec.get("branch") or not rec.get("baseCommit"):
            return None
        _, index = self.load_projects(resolve=False)
        folder = index.get(rec["project"])
        top = self._git_top(folder) if folder else ""
        if not top:
            return None
        return {"top": top, "rel": os.path.relpath(os.path.realpath(folder), top), "branch": rec["branch"],
                "worktree": os.path.join(top, AGENT_DIR, rec["id"]), "base": rec.get("base") or "",
                "baseCommit": rec["baseCommit"]}

    def _worktree_close(self, rec, git, record=True):
        """Po zakończeniu: commit niezatwierdzonych zmian agenta na gałęzi (bez plików standardu), changes i commits
        w rekordzie, usunięcie katalogu roboczego. Gałąź zostaje. record=False: tylko pola w `rec` (część projektu),
        bez zapisu rekordu."""
        wt, top = git["worktree"], git["top"]
        branch, note = rec.get("branch") or git["branch"], ""
        with self._git_lock:
            if os.path.isdir(wt):
                code, cur, _ = git_run(wt, ["symbolic-ref", "--short", "-q", "HEAD"], timeout=15)
                if code == 0 and cur.strip():
                    branch = cur.strip()                # agent założył własną gałąź: liczy się ta
                code, status, _ = git_run(wt, ["status", "--porcelain", "--untracked-files=all"])
                if code == 0 and status.strip():
                    prefix = "" if git["rel"] == "." else git["rel"].replace(os.sep, "/") + "/"
                    skip = [":(top,exclude)%s%s" % (prefix, n) for n in STANDARD_LINKS + (rec.get("file") or "",) if n]
                    git_run(wt, ["add", "-A", "--", ":/"] + skip, timeout=300)
                    if git_run(wt, ["diff", "--cached", "--quiet"])[0] == 1:
                        msg = "%s\n\nUruchomienie panelu %s (%s)." % (rec["title"], rec["id"], rec["tool"])
                        code, _, err = git_run(wt, git_ident(wt) + ["-c", "commit.gpgsign=false", "commit", "-q",
                                                                    "--no-verify", "-m", msg], timeout=300)
                        note = "git: zatwierdzono zmiany agenta na gałęzi %s" % branch if code == 0 \
                            else "git: nie zatwierdzono zmian (%s)" % _short(err, 80)
            changes = git_numstat(top, git["baseCommit"], branch)
            code, out, _ = git_run(top, ["rev-list", "--count", "%s..%s" % (git["baseCommit"], branch)], timeout=15)
            commits = int(out.strip()) if code == 0 and out.strip().isdigit() else 0
            if os.path.isdir(wt):
                if git_run(top, ["worktree", "remove", "--force", wt], timeout=300)[0] != 0:
                    shutil.rmtree(wt, ignore_errors=True)
            git_run(top, ["worktree", "prune"], timeout=30)
        if not record:
            rec.update(branch=branch, changes=changes, commits=commits, note=note)
            return
        if note:
            self._step(rec, note)
        with self._lock:
            rec.update(branch=branch, changes=changes, commits=commits)
            self._save(rec)

    def _run_repo(self, rid, project="", branch=""):
        """(rekord, repozytorium) dla merge i diff albo (None, (kod, błąd)). Bez id: gałąź agenta z pola
        `gałąź:` zadania (project, branch), z bazą w gałęzi wybranej teraz w repozytorium."""
        if not rid and (project or branch):
            return self._branch_repo(str(project), str(branch))
        rec = self.get(str(rid))
        if not rec or rec.get("kind") != "task" or not rec.get("branch"):
            return None, (404, "Nie ma gałęzi tego uruchomienia.")
        if rec["state"] in LIVE:
            return None, (409, "Uruchomienie jeszcze trwa.")
        _, index = self.load_projects(resolve=False)
        folder = index.get(rec["project"])
        top = self._git_top(folder) if folder else ""
        if not top:
            return None, (404, "Nie ma repozytorium projektu.")
        if git_run(top, ["rev-parse", "--verify", "-q", "refs/heads/" + rec["branch"]], timeout=15)[0] != 0:
            return None, (409, "Nie ma gałęzi %s." % rec["branch"])
        return (rec, top), None

    def _branch_spec(self, project, branch, rel):
        """(repozytorium, "refs/heads/<gałąź>:<ścieżka>", rozmiar) pliku z gałęzi agent/… w folderze projektu
        albo (None, błąd, None)."""
        branch, rel = str(branch), str(rel or "").strip().replace("\\", "/")
        if not self.projekt.BRANCH.match(branch) or ".." in branch:
            return None, "Gałąź agenta ma postać agent/nazwa.", None
        _, index = self.load_projects(resolve=False)
        folder = index.get(project)
        top = self._git_top(folder) if folder else ""
        if not top:
            return None, "Nie ma takiego pliku.", None
        base = os.path.relpath(os.path.realpath(folder), top).replace(os.sep, "/")
        path = posixpath.normpath(posixpath.join("" if base == "." else base, rel))
        if rel.startswith("/") or path == ".." or path.startswith("../") or "\x00" in rel:
            return None, "Nie ma takiego pliku.", None
        spec = "refs/heads/%s:%s" % (branch, path)
        code, size, _ = git_run(top, ["cat-file", "-s", spec], timeout=15)
        if code != 0 or not size.strip().isdigit():
            return None, "Nie ma takiego pliku w folderze ani na gałęzi %s." % branch, None
        return top, spec, int(size.strip())

    def branch_blob(self, project, branch, rel, types, max_size):
        """GET /api/plik/surowy z branch=: (bajty | None, błąd) obrazu albo PDF z gałęzi agent/… w folderze projektu."""
        if not self.projekt.BRANCH.match(str(branch)) or ".." in str(branch):
            return None, "Gałąź agenta ma postać agent/nazwa."
        if not str(rel or "").strip().lower().endswith(tuple(types)):
            return None, "Panel pokazuje tylko obrazy PNG, JPG, WEBP i pliki PDF."
        top, spec, size = self._branch_spec(project, branch, rel)
        if not top:
            return None, spec
        if size > max_size:
            return None, "Plik jest większy niż %d MB." % (max_size >> 20)
        return self._branch_read(top, spec, branch)

    @staticmethod
    def _branch_read(top, spec, branch):
        env = dict(os.environ, LC_ALL="C", LANG="C", GIT_TERMINAL_PROMPT="0")
        try:
            p = subprocess.run(["git", "-c", "core.hooksPath=" + os.devnull, "cat-file", "blob", spec], cwd=top,
                               stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                               timeout=60, env=env, **NO_WINDOW)
        except (OSError, subprocess.SubprocessError):
            return None, "Nie udało się odczytać pliku z gałęzi %s." % branch
        if p.returncode != 0:
            return None, "Nie udało się odczytać pliku z gałęzi %s." % branch
        return p.stdout, ""

    def branch_file(self, project, branch, rel):
        """GET /api/plik z branch=: (tekst | None, błąd) pliku .md/.txt z gałęzi agent/… w folderze projektu."""
        branch, rel = str(branch), str(rel or "").strip().replace("\\", "/")
        if not self.projekt.BRANCH.match(branch) or ".." in branch:
            return None, "Gałąź agenta ma postać agent/nazwa."
        if not rel.lower().endswith((".md", ".txt")):
            return None, "Panel pokazuje tylko pliki .md i .txt."
        _, index = self.load_projects(resolve=False)
        folder = index.get(project)
        top = self._git_top(folder) if folder else ""
        if not top:
            return None, "Nie ma takiego pliku."
        base = os.path.relpath(os.path.realpath(folder), top).replace(os.sep, "/")
        path = posixpath.normpath(posixpath.join("" if base == "." else base, rel))
        if rel.startswith("/") or path == ".." or path.startswith("../") or "\x00" in rel:
            return None, "Nie ma takiego pliku."
        spec = "refs/heads/%s:%s" % (branch, path)
        code, size, _ = git_run(top, ["cat-file", "-s", spec], timeout=15)
        if code != 0 or not size.strip().isdigit():
            return None, "Nie ma takiego pliku w folderze ani na gałęzi %s." % branch
        if int(size.strip()) > DIFF_MAX:
            return None, "Plik jest większy niż 200 KB."
        code, out, _ = git_run(top, ["show", "--no-textconv", spec], timeout=30)
        if code != 0:
            return None, "Nie udało się odczytać pliku z gałęzi %s." % branch
        return out, ""

    def _branch_repo(self, project, branch):
        if not self.projekt.BRANCH.match(branch) or ".." in branch:
            return None, (400, "Gałąź agenta ma postać agent/nazwa.")
        _, index = self.load_projects(resolve=False)
        folder = index.get(project)
        top = self._git_top(folder) if folder else ""
        if not top:
            return None, (404, "Nie ma repozytorium projektu.")
        if git_run(top, ["rev-parse", "--verify", "-q", "refs/heads/" + branch], timeout=15)[0] != 0:
            return None, (409, "Nie ma gałęzi %s." % branch)
        code, cur, _ = git_run(top, ["symbolic-ref", "--short", "-q", "HEAD"], timeout=15)
        base = cur.strip() if code == 0 else ""
        if not base or base == branch:
            return None, (409, "W repozytorium wybrana jest gałąź %s; wybierz gałąź bazową." % (base or "(brak)"))
        code, mb, _ = git_run(top, ["merge-base", base, branch], timeout=15)
        rec = {"id": "", "kind": "task", "state": "done", "project": project, "branch": branch, "base": base,
               "baseCommit": mb.strip() if code == 0 else base, "title": branch}
        return (rec, top), None

    def diff(self, rid, project="", branch=""):
        """GET /api/agent/diff: (kod, tekst diffu gałęzi względem bazy, najwyżej DIFF_MAX bajtów | błąd)."""
        found, error = self._run_repo(rid, project, branch)
        if error:
            return error[0], error[1]
        rec, top = found
        code, out, err = git_run(top, ["diff", "--no-color", "--no-ext-diff", "--no-textconv",
                                       "%s...%s" % (rec.get("baseCommit") or rec.get("base"), rec["branch"])])
        if code != 0:
            return 409, "Nie udało się odczytać zmian: %s" % _short(err, 200)
        raw = out.encode("utf-8")
        if len(raw) > DIFF_MAX:
            out = raw[:DIFF_MAX].decode("utf-8", "ignore") + "\n… (diff obcięty do 200 KB)\n"
        return 200, out

    def merge(self, rid, project="", branch=""):
        """POST /api/agent/merge: git merge --no-ff gałęzi uruchomienia (albo gałęzi z pola `gałąź:`) do bazy,
        bez push. Tylko na gałęzi bazowej, bez niezatwierdzonych zmian (poza plikami standardu, które zmienia panel)
        i bez konfliktów; inaczej 409."""
        found, error = self._run_repo(rid, project, branch)
        if error:
            return error[0], error[1], {}
        rec, top = found
        if rec.get("merged"):
            return 409, "Gałąź %s jest już scalona." % rec["branch"], {}
        base = rec.get("base") or ""
        with self._git_lock:
            code, cur, _ = git_run(top, ["symbolic-ref", "--short", "-q", "HEAD"], timeout=15)
            cur = cur.strip() if code == 0 else ""
            if not base or base == rec.get("baseCommit"):
                return 409, "Baza gałęzi to commit bez nazwy gałęzi. Scal ręcznie.", {}
            if cur != base:
                return 409, "W repozytorium wybrana jest gałąź %s, a baza to %s." % (cur or "(brak)", base), {}
            if git_run(top, ["rev-parse", "-q", "--verify", "MERGE_HEAD"], timeout=15)[0] == 0:
                return 409, "W repozytorium trwa inne scalanie.", {}
            code, status, _ = git_run(top, ["status", "--porcelain", "--untracked-files=no"])
            if code != 0:
                return 409, "Nie udało się odczytać stanu repozytorium.", {}
            dirty = [line[3:].strip() for line in status.splitlines() if len(line) > 3]
            dirty = [p for p in dirty if os.path.basename(p.split(" -> ")[-1].strip('"')) not in STANDARD_LINKS]
            if dirty:
                return 409, _short("Scalenie blokują niezatwierdzone zmiany w repozytorium (%d: %s). W Kod i pliki: "
                                   "„Zatwierdź jako zmiany agenta” albo „Odłóż na bok”."
                                   % (len(dirty), ", ".join(dirty[:4])), 300), {"blocked": "dirty"}
            code, out, _ = git_run(top, ["rev-list", "--count", "%s..%s" % (base, rec["branch"])], timeout=15)
            if code == 0 and out.strip() == "0":
                return 409, "Gałąź %s nie ma zmian do scalenia." % rec["branch"], {}
            code, names, _ = git_run(top, ["diff", "--name-only", "--no-renames", "--diff-filter=d", "-z",
                                           "%s...%s" % (base, rec["branch"])])
            if code != 0:
                return 409, "Nie udało się odczytać zmian gałęzi %s." % rec["branch"], {}
            secret = [p for p in names.split("\0") if p and secret_file(p)]
            if secret:
                return 409, _short("Gałąź zawiera pliki z sekretami: %s. Usuń je z gałęzi i scal ponownie."
                                   % ", ".join(secret[:5]), 300), {}
            msg = "Scalenie %s: %s" % (rec["branch"], rec["title"])
            code, out, err = git_run(top, git_ident(top) + ["-c", "commit.gpgsign=false", "merge", "--no-ff",
                                                            "--no-edit", "-m", msg, rec["branch"]], timeout=300)
            if code != 0:
                text = out + "\n" + err
                files = re.findall(r"CONFLICT \([^)]*\): .*? in (.+)$", text, re.M)
                if git_run(top, ["rev-parse", "-q", "--verify", "MERGE_HEAD"], timeout=15)[0] == 0:
                    git_run(top, ["merge", "--abort"])
                if files:
                    return 409, _short("Konflikt w: %s. Repozytorium bez zmian." % ", ".join(files[:5]), 300), {}
                local = re.findall(r"^\s+(\S.*)$", err, re.M) if "would be overwritten" in err else []
                if local:
                    return 409, _short("Scalenie zmieniłoby niezatwierdzone pliki: %s." % ", ".join(local[:5]), 300), {}
                return 409, _short("Scalenie nie powiodło się: %s" % (err.strip() or out.strip()), 300), {}
            sha = git_run(top, ["rev-parse", "HEAD"], timeout=15)[1].strip()
        with self._lock:
            live = self._runs.get(rec["id"])
            if live is not None:
                live.update(merged=now_iso(), mergeCommit=sha)
                self._save(live)
        try:
            self.site.after_merge(rec)
        except Exception as e:
            log("Podgląd strony po scaleniu: %s" % e)
        return 200, "", {"commit": sha}

    # ---------- zmiany niezatwierdzone w repozytorium projektu (Kod i pliki) ----------
    SOURCES_DAYS = 3            # tyle dni wstecz panel szuka uruchomień, które zmieniały pliki repozytorium

    def dirty_sources(self, folder, paths):
        """Uruchomienia agentów, które zmieniały te pliki w folderze (a nie w swoim katalogu roboczym):
        [{"runId", "title", "project", "at", "files"}], najnowsze pierwsze. Z przebiegów (Edit, Write) z ostatnich dni."""
        top = os.path.realpath(folder)
        want = {os.path.normpath(os.path.join(top, p)) for p in paths}
        if not want:
            return []
        since = (datetime.datetime.now() - datetime.timedelta(days=self.SOURCES_DAYS)).isoformat()[:19]
        with self._lock:
            runs = [dict(r) for r in self._runs.values() if r.get("kind") == "task"
                    and (r.get("startedAt") or "") >= since]
        out, needle = [], top.encode("utf-8")
        for r in reversed(runs):
            hit = set()
            try:
                with open(os.path.join(self.runs_dir, r["id"] + ".log"), "rb") as f:
                    for raw in f:
                        if needle not in raw or b"tool_use" not in raw:
                            continue
                        try:
                            ev = json.loads(raw.decode("utf-8", "replace"))
                        except ValueError:
                            continue
                        msg = ev.get("message") if isinstance(ev, dict) else None
                        body = msg.get("content") if isinstance(msg, dict) else None
                        for b in body if isinstance(body, list) else []:
                            if isinstance(b, dict) and b.get("type") == "tool_use" and \
                                    b.get("name") in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
                                fp = str((b.get("input") or {}).get("file_path") or "")
                                if fp and os.path.normpath(fp) in want:
                                    hit.add(os.path.relpath(os.path.normpath(fp), top))
            except OSError:
                continue
            if hit:
                out.append({"runId": r["id"], "title": r.get("title") or "", "project": r.get("project") or "",
                            "projectName": r.get("projectName") or "", "at": r.get("startedAt") or "",
                            "files": sorted(hit)[:20]})
        return out[:5]

    def repo_message(self, folder, dirty, kind="commit"):
        """Opis commita albo schowka: z jakiego zadania pochodzą zmiany (dirty_sources) albo ogólny."""
        src = self.dirty_sources(folder, [p for _, p in dirty])
        day = now_iso()[:16].replace("T", " ")
        if src:
            first = src[0]
            what = "Zmiany agenta z zadania „%s” (%s, uruchomienie %s)" % (
                first["title"], first["projectName"] or first["project"], first["runId"])
            if len(src) > 1:
                what += " i %d innych uruchomień" % (len(src) - 1)
        else:
            what = "Zmiany niezatwierdzone w repozytorium"
        if kind == "commit":
            return "%s\n\nAgent pisał w głównym katalogu repozytorium zamiast na swojej gałęzi; zatwierdzono w panelu " \
                   "%s (Kod i pliki)." % (what, day), src
        return "%s, odłożone w panelu %s" % (what, day), src

    def repo_action(self, pid, action, ref="", note=""):
        """POST /api/repo/zatwierdz | odloz | przywroc: zmiany niezatwierdzone w repozytorium projektu (konto panelu)."""
        _, index = self.load_projects(resolve=False)
        folder = index.get(str(pid))
        if not folder:
            return 404, "Nie ma takiego projektu.", {}
        if not kopie.has_repo(folder):
            return 409, "Folder projektu nie jest repozytorium git.", {}
        if self.has_live(pid) and not self.worktrees:
            return 409, "Agent pracuje w folderze projektu. Poczekaj na koniec jego pracy.", {}
        with self._git_lock, kopie.folder_lock(folder):
            dirty = kopie._dirty(folder) or []
            if action == "commit":
                msg, src = self.repo_message(folder, dirty, "commit")
                if note:
                    msg = "%s\n\n%s" % (msg, _short(note, 500))
                ok, out = kopie.commit_dirty(folder, msg)
                text = "Zatwierdzono %d %s jako commit %s." % (len(dirty), "plik" if len(dirty) == 1 else "pliki", out) \
                    if ok else out
            elif action == "stash":
                msg, src = self.repo_message(folder, dirty, "stash")
                ok, out = kopie.stash_save(folder, msg)
                text = "Zmiany odłożone na bok (%d). Przywrócisz je w Kod i pliki." % len(dirty) if ok else out
            elif action == "restore":
                ok, out = kopie.stash_restore(folder, ref)
                text = "Przywrócono odłożone zmiany." if ok else out
            else:
                return 400, "Nieznane działanie.", {}
        if not ok:
            return 409, text, {}
        return 200, "", {"message": text}

    # ---------- materiał z wyniku dla następników (po:) ----------
    def result_paths(self, text, folder, git=None):
        """Ścieżki plików z wiersza wynik:, które istnieją w folderze projektu, w folderze kart albo na gałęzi
        uruchomienia; względem folderu projektu, ukośniki /."""
        root = os.path.realpath(folder)
        cards = os.path.dirname(os.path.realpath(os.path.join(folder, "KARTA.md")))
        bases = [root] + ([cards] if cards != root else [])
        work = ""
        if git:
            work = git["worktree"] if git["rel"] == "." else os.path.join(git["worktree"], git["rel"])
        out = []
        for raw in RESULT_PATH.findall(str(text or "")):
            path = raw.replace("\\", "/")
            if os.path.isabs(path):
                for base in [work] + bases if work else bases:
                    if base and _inside(base, os.path.normpath(path)):
                        path = os.path.relpath(os.path.normpath(path), base).replace(os.sep, "/")
                        break
                else:
                    continue
            path = os.path.normpath(path).replace(os.sep, "/")
            if path.startswith("../") or path == ".." or os.path.isabs(path) or path in out:
                continue
            exists = any(_inside(b, os.path.realpath(os.path.join(b, path))) and
                         os.path.isfile(os.path.join(b, path)) for b in bases)
            if not exists and git:
                prefix = "" if git["rel"] == "." else git["rel"].replace(os.sep, "/") + "/"
                exists = git_run(git["top"], ["cat-file", "-e", "%s:%s%s" % (git["branch"], prefix, path)],
                                 timeout=15)[0] == 0
            if exists:
                out.append(path)
            if len(out) >= RESULT_PATHS_MAX:
                break
        return out

    def _pass_materials(self, rec, git=None):
        """Ścieżki z wynik: zadania trafiają jako materiał: do otwartych zadań z po: na tym zadaniu (bez duplikatów)."""
        data, index = self.load_projects(resolve=False)
        folder = index.get(rec["project"])
        if not folder:
            return
        tasks = [t for t in data["tasks"] if t["project"] == rec["project"] and t["file"] == rec["file"]]
        me = next((t for t in tasks if t["title"] == rec["title"]), None)
        result = ((me or {}).get("detail") or {}).get("result") or ""
        paths = self.result_paths(result, folder, git) if result else []
        if not paths:
            return
        added = 0
        for t in tasks:
            if t.get("state") == "done" or t is me or \
                    not any(isinstance(w, dict) and w.get("title") == rec["title"] for w in t.get("waitingFor") or []):
                continue
            refs = [r for r in (t.get("detail") or {}).get("refs") or [] if isinstance(r, dict) and r.get("path")]
            have = {r["path"] for r in refs}
            new = [p for p in paths if p not in have]
            if not new:
                continue
            values = ["%s%s" % (r["path"], "#" + r["anchor"] if r.get("anchor") else "") for r in refs] + new
            try:
                with self.write_lock:
                    if self.projekt.set_detail(folder, t["file"], t["line"], t["title"], "materiał", values):
                        added += 1
            except (ValueError, OSError) as e:
                log("Materiał dla %s: %s" % (t["title"], e))
        if added:
            self._step(rec, "Materiał z wyniku dopisany do %d zadań z po:" % added)

    # ---------- wersje wyniku i strona „Odbiór pracy” ----------
    def _versions_dir(self, project, file, title):
        key = "%s|%s|%s" % (project, file, title)
        return os.path.join(self.runs_dir, "wersje", hashlib.sha1(key.encode("utf-8")).hexdigest()[:16])

    def versions(self, project, file, title):
        """Zapisane wersje wyniku zadania (meta.json), od najstarszej."""
        base = self._versions_dir(project, file, title)
        try:
            names = [n for n in os.listdir(base) if n.isdigit()]
        except OSError:
            return []
        out = []
        for name in names:
            try:
                with open(os.path.join(base, name, "meta.json"), encoding="utf-8") as f:
                    meta = json.load(f)
            except (OSError, ValueError):
                continue
            if isinstance(meta, dict) and meta.get("n") == int(name):
                out.append(meta)
        return sorted(out, key=lambda m: m["n"])

    @staticmethod
    def _review_path(path):
        return (path and not any(c in path for c in ("\\", ":", "\x00", "\ufffd"))
                and all(part and not part.startswith(".") for part in path.split("/"))
                and posixpath.basename(path).lower() not in {"karta.md", "zadania.md", "decyzje.md", "kampania.md"}
                and os.path.splitext(path.lower())[1] in VERSION_TYPES)

    def _review_sources(self, task, folder, rec=None):
        """Pliki z różnicy zadania albo jawne ścieżki wyniku dla pracy bez gałęzi."""
        if not folder:
            return {}
        detail = task.get("detail") or {}
        refs = version_paths("%s\n%s" % (detail.get("result") or "", detail.get("left") or ""),
                             detail.get("refs") or [])
        refs = [path for path in refs if path != task["file"]]
        branch = (rec or {}).get("branch") or detail.get("branch") or ""
        if not branch:
            return {rel: where for rel in refs if (where := self._result_locate(folder, rel))}
        if not self.projekt.BRANCH.fullmatch(branch) or ".." in branch:
            return {}
        top = self._git_top(folder)
        if not top:
            return {}
        code, head, _ = git_run(top, ["rev-parse", "--verify", "refs/heads/" + branch + "^{commit}"], timeout=10)
        if code != 0:
            return {}
        head = head.strip()
        base = (rec or {}).get("baseCommit") or ""
        if not base:
            code, base, _ = git_run(top, ["merge-base", "HEAD", head], timeout=10)
            if code != 0:
                return {}
            base = base.strip()
        if not re.fullmatch(r"[0-9a-f]{40,64}", base):
            return {}
        scope = os.path.relpath(os.path.realpath(folder), top).replace(os.sep, "/")
        prefix = scope + "/" if scope != "." else ""
        code, diff, _ = git_run(top, ["--literal-pathspecs", "diff", "--name-only", "-z", "--no-renames",
                                     "--no-ext-diff", base, head, "--", scope], timeout=15)
        if code != 0:
            return {}
        paths = {path for path in diff.split("\0") if path.startswith(prefix)
                 and path[len(prefix):] != task["file"] and self._review_path(path[len(prefix):])}
        if not paths:
            return {}
        code, tree, _ = git_run(top, ["--literal-pathspecs", "ls-tree", "-rlz", head, "--", scope], timeout=15)
        sources = {}
        if code == 0:
            for line in tree.split("\0"):
                meta, _, path = line.partition("\t")
                if path not in paths:
                    continue
                mode, kind, oid, size = meta.split()
                if mode in ("100644", "100755") and kind == "blob":
                    sources[path[len(prefix):]] = ("gałąź", (top, oid), int(size))
        return {rel: sources[rel] for rel in dict.fromkeys(refs + sorted(sources)) if rel in sources}

    def _result_locate(self, folder, rel):
        if not self._review_path(rel):
            return None
        base = os.path.realpath(folder)
        path = os.path.join(base, *rel.split("/"))
        try:
            if os.path.realpath(path) == path and stat.S_ISREG(os.lstat(path).st_mode):
                return "dysk", (base, rel), os.path.getsize(path)
        except OSError:
            pass
        return None

    @staticmethod
    def _review_disk(base, rel):
        """Otwórz zwykły plik bez podążania za dowiązaniami, także przy zmianie katalogu podczas odczytu."""
        with contextlib.ExitStack() as stack:
            if os.open in os.supports_dir_fd and hasattr(os, "O_NOFOLLOW"):
                flags = os.O_RDONLY | os.O_NOFOLLOW
                fd = os.open(os.path.sep, flags | os.O_DIRECTORY)
                stack.callback(os.close, fd)
                parts = base.strip(os.path.sep).split(os.path.sep) + rel.split("/")
                for part in parts[:-1]:
                    fd = os.open(part, flags | os.O_DIRECTORY, dir_fd=fd)
                    stack.callback(os.close, fd)
                fd = os.open(parts[-1], flags | os.O_NONBLOCK, dir_fd=fd)
            else:
                path = os.path.join(base, *rel.split("/"))
                if os.path.realpath(path) != path:
                    return None
                fd = os.open(path, os.O_RDONLY | getattr(os, "O_BINARY", 0))
            with os.fdopen(fd, "rb") as f:
                if stat.S_ISREG(os.fstat(f.fileno()).st_mode):
                    blob = f.read(REVIEW_FILE_MAX + 1)
                    return blob if len(blob) <= REVIEW_FILE_MAX else None
        return None

    def _result_read(self, where):
        kind, src, size = where
        if size > REVIEW_FILE_MAX:
            return None
        if kind == "dysk":
            try:
                return self._review_disk(*src)
            except OSError:
                return None
        return self._branch_read(src[0], src[1], "")[0]

    def _task_run(self, key):
        """Bieżące (w kolejce albo w toku) albo ostatnie uruchomienie zadania: kopia rekordu i miejsce w kolejce."""
        with self._lock:
            recs = [r for r in self._runs.values()
                    if r.get("kind") == "task" and (r.get("project"), r.get("file"), r.get("title")) == key]
            live = [r for r in recs if r["state"] in LIVE]
            rec = live[0] if live else (max(recs, key=lambda r: r.get("queuedAt") or "") if recs else None)
            if not rec:
                return None, None
            pos = self._queue.index(rec["id"]) + 1 if rec["state"] == "queued" and rec["id"] in self._queue else None
            return dict(rec, steps=list(rec.get("steps") or [])), pos

    def _save_version(self, rec):
        """Po udanym uruchomieniu zadania: nowa wersja wyniku (wynik:, zostało:, decyzja:, zmiany:, poprawka
        z rekordu i kopie plików z wyniku). Bez nadpisywania; najwyżej VERSIONS_KEEP wersji na zadanie."""
        key = (rec["project"], rec["file"], rec["title"])
        data, index = self.load_projects(resolve=False)
        folder = index.get(rec["project"])
        task = next((t for t in data["tasks"] if (t["project"], t["file"], t["title"]) == key), None)
        if not folder or not task:
            return None
        d = task.get("detail") or {}
        result, left, decision = (str(d.get(k) or "") for k in ("result", "left", "decision"))
        sources = self._review_sources(task, folder, rec)
        if not (result or left or decision or sources):
            return None
        base = self._versions_dir(*key)
        with self._ver_lock:
            old = self.versions(*key)
            n = (old[-1]["n"] if old else 0) + 1
            os.makedirs(base, exist_ok=True)
            while True:
                try:
                    os.mkdir(os.path.join(base, str(n)))
                    break
                except FileExistsError:
                    n += 1
            here = os.path.join(base, str(n))
            changes = [str(c) for c in d.get("changes") or []]
            if old and old[-1].get("changes") == changes:
                changes = []                    # wiersz zmiany: z poprzedniej pracy, agent go nie odnowił
            fixes = []
            if rec.get("fix") or rec.get("pins"):
                fixes.append({"text": str(rec.get("fix") or ""), "pins": list(rec.get("pins") or [])})
            files, total = [], 0
            for i, (rel, where) in enumerate(sources.items()):
                ext = os.path.splitext(rel.lower())[1]
                entry = {"path": rel, "kind": VERSION_KINDS[ext], "size": where[2]}
                if where[2] > VERSION_FILE_MAX:
                    entry["skipped"] = "większy niż %d MB" % (VERSION_FILE_MAX >> 20)
                elif total + where[2] > VERSION_TOTAL_MAX:
                    entry["skipped"] = "razem ponad %d MB" % (VERSION_TOTAL_MAX >> 20)
                else:
                    blob = self._result_read(where)
                    if blob is None:
                        continue
                    copy = "plik-%d%s" % (i + 1, ext)
                    with open(os.path.join(here, copy), "wb") as f:
                        f.write(blob)
                    entry.update(size=len(blob), copy=copy)
                    total += len(blob)
                files.append(entry)
            meta = {"n": n, "at": now_iso(), "runId": rec["id"], "result": result, "left": left,
                    "decision": decision, "changes": changes, "fixes": fixes, "files": files}
            tmp = os.path.join(here, "meta.json.tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=1)
            os.replace(tmp, os.path.join(here, "meta.json"))
            for m in (old + [meta])[:-VERSIONS_KEEP]:
                shutil.rmtree(os.path.join(base, str(m["n"])), ignore_errors=True)
        return meta

    @staticmethod
    def _file_url(task_id, n, path):
        return "/api/odbior/plik?" + urllib.parse.urlencode({"id": task_id, "v": n, "path": path})

    def _current_version(self, task, folder):
        """Wersja „bieżąca” (saved=false) z pól zadania, gdy wersji zapisanych nie ma."""
        d = task.get("detail") or {}
        rec, _ = self._task_run((task["project"], task["file"], task["title"]))
        sources = self._review_sources(task, folder, rec)
        files = [{"path": rel, "kind": VERSION_KINDS[os.path.splitext(rel.lower())[1]], "size": where[2]}
                 for rel, where in sources.items()]
        fixes = [{"text": d["fix"], "pins": list(d.get("pins") or [])}] if d.get("fix") else []
        return {"n": 1, "at": (rec or {}).get("endedAt") or "", "saved": False, "runId": (rec or {}).get("id", ""),
                "result": d.get("result") or "", "left": d.get("left") or "", "decision": d.get("decision") or "",
                "changes": list(d.get("changes") or []), "fixes": fixes, "files": files}

    def review(self, task_id):
        """GET /api/odbior?id=: zadanie, wersje wyniku (od najstarszej), bieżące albo ostatnie uruchomienie,
        odebrane warianty. (kod, błąd, dane)."""
        task, data, index = self._find_task(task_id=str(task_id))
        if not task:
            return 404, "Nie ma tego zadania.", {}
        d = task.get("detail") or {}
        key = (task["project"], task["file"], task["title"])
        project = next((p for p in data["projects"] if p["id"] == task["project"]), {})
        stage = next((s["title"] for s in data["stages"] if s["id"] == task.get("stage")), "")
        info = {"id": task["id"], "title": task["title"], "project": task["project"],
                "projectName": project.get("name") or task["project"], "stage": stage, "state": task.get("state", ""),
                "needsYou": task.get("needsYou", ""), "executor": task.get("executor", ""),
                "goal": d.get("goal") or "", "doneWhen": d.get("doneWhen") or "", "decision": d.get("decision") or "",
                "left": d.get("left") or "", "fix": d.get("fix") or "", "pins": list(d.get("pins") or [])}
        saved = self.versions(*key)
        if saved:
            versions = [{"n": m["n"], "at": m.get("at", ""), "saved": True, "runId": m.get("runId", ""),
                         "result": m.get("result", ""), "decision": m.get("decision", ""), "left": m.get("left", ""),
                         "changes": list(m.get("changes") or []), "fixes": list(m.get("fixes") or []),
                         "files": [dict(f) for f in m.get("files") or []]} for m in saved]
            live = self._review_latest_sources(task, index.get(task["project"]), saved[-1])
            latest = versions[-1]["files"]
            known = {f["path"] for f in latest}
            latest.extend({"path": path, "kind": VERSION_KINDS[os.path.splitext(path.lower())[1]], "size": where[2]}
                          for path, where in live.items() if path not in known)
        else:
            versions = [self._current_version(task, index.get(task["project"]))]
        for v in versions:
            for f in v["files"]:
                f.pop("copy", None)
                f.update(name=posixpath.basename(f["path"]), url=self._file_url(task["id"], v["n"], f["path"]))
                if f.get("size", 0) > REVIEW_FILE_MAX:
                    f["skipped"] = "większy niż %d MB" % (REVIEW_FILE_MAX >> 20)
                elif v is versions[-1] and saved and f["path"] in live:
                    f.pop("skipped", None)
            v["zip"] = "/api/odbior/zip?" + urllib.parse.urlencode({"id": task["id"], "v": v["n"]})
        rec, pos = self._task_run(key)
        run = None
        if rec:
            run = {"id": rec["id"], "state": rec["state"], "queuedAt": rec.get("queuedAt"),
                   "startedAt": rec.get("startedAt"), "endedAt": rec.get("endedAt"), "steps": rec["steps"],
                   "activity": rec.get("activity", ""), "error": rec.get("error", ""), "position": pos}
        accepted = next((a.get("value", "") for a in d.get("answers") or []
                         if isinstance(a, dict) and a.get("label", "").lower() == VARIANTS_LABEL), "")
        return 200, "", {"task": info, "versions": versions, "run": run,
                         "accepted": [x.strip() for x in accepted.split(",") if x.strip()]}

    def _review_latest_sources(self, task, folder, meta):
        with self._lock:
            rec = self._runs.get(meta.get("runId"))
        if not rec:
            return {}
        live = self._review_sources(task, folder, rec)
        if rec.get("branch"):
            return live
        saved_paths = {f["path"] for f in meta.get("files") or []}
        return {path: where for path, where in live.items() if path in saved_paths}

    def _review_downloads(self, task_id, n):
        task, _, index = self._find_task(task_id=str(task_id))
        if not task:
            return {}
        try:
            n = int(n)
        except (TypeError, ValueError):
            return {}
        key = (task["project"], task["file"], task["title"])
        saved = self.versions(*key)
        folder = index.get(task["project"])
        if not saved:
            if n != 1:
                return {}
            live = self._review_sources(task, folder, self._task_run(key)[0])
            return {path: where for path, where in live.items() if where[2] <= REVIEW_FILE_MAX}
        meta = next((m for m in saved if m["n"] == n), None)
        if not meta:
            return {}
        live = self._review_latest_sources(task, folder, meta) if meta is saved[-1] else {}
        here = os.path.join(self._versions_dir(*key), str(n))
        sources = {}
        for f in meta.get("files") or []:
            path, copy = f.get("path", ""), f.get("copy", "")
            if not self._review_path(path):
                continue
            if re.fullmatch(r"plik-\d+\.[a-z0-9]+", copy):
                sources[path] = ("dysk", (here, copy), f["size"])
        sources.update({path: where for path, where in live.items()
                        if path not in sources and where[2] <= REVIEW_FILE_MAX})
        return sources

    def review_file(self, task_id, n, path):
        where = self._review_downloads(task_id, n).get(path)
        blob = self._result_read(where) if where else None
        if blob is None:
            return 404, "Nie ma takiego pliku do pobrania.", ""
        return 200, blob, VERSION_TYPES[os.path.splitext(path.lower())[1]]

    def review_zip(self, task_id, n):
        sources = self._review_downloads(task_id, n)
        if not sources:
            return 404, "Nie ma plików do pobrania.", ""
        if sum(where[2] for where in sources.values()) > REVIEW_FILE_MAX:
            return 413, "Pliki przekraczają limit ZIP (128 MB). Pobierz je pojedynczo.", ""
        out = io.BytesIO()
        total = 0
        with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=1) as archive:
            for path, where in sources.items():
                blob = self._result_read(where)
                if blob is None:
                    return 404, "Jeden z plików wyniku jest niedostępny.", ""
                total += len(blob)
                if total > REVIEW_FILE_MAX:
                    return 413, "Pliki przekraczają limit ZIP (128 MB). Pobierz je pojedynczo.", ""
                archive.writestr(path, blob)
        return 200, out.getvalue(), "application/zip"

    def review_fix(self, task_id, title, text, pins):
        """POST /api/odbior/popraw: poprawka ze znacznikami pod zadaniem i od razu uruchomienie (jak „Wyślij
        i wykonaj”). (kod, błąd, {"status"})."""
        text = str(text or "").strip()
        if not isinstance(pins, list):
            pins = [] if pins in (None, "") else None
        if pins is None:
            return 400, "Znaczniki to lista.", {}
        if not text and not pins:
            return 400, "Napisz, co zmienić, albo wskaż miejsce na projekcie.", {}
        if len(text) > 1000:
            return 400, "Najwyżej 1000 znaków.", {}
        if len(pins) > self.projekt.PIN_MAX:
            return 400, "Najwyżej %d znaczników." % self.projekt.PIN_MAX, {}
        try:
            pins = [self.projekt.pin_check(p) for p in pins]
        except ValueError as e:
            return 400, "Nie zapisano: %s." % e, {}
        task, data, index = self._find_task(task_id=str(task_id))
        if not task or task["project"] not in index:
            return 404, "Nie ma tego zadania.", {}
        if task["title"] != str(title):
            return 409, CONFLICT, {}
        if data["projectsSource"] != "registry":
            return 409, "Projekty przykładowe", {}
        return self.chat_execute(task, index, text or REVIEW_FIX_DEFAULT, pins or None)

    def review_accept(self, task_id, title, variants=None):
        """POST /api/odbior/akceptuj: zadanie zrobione (bez wymaga: odbiór). Odbiór części wariantów: pod zadaniem
        „odpowiedź: odebrane warianty = a, b”. (kod, błąd, {})."""
        task, data, index = self._find_task(task_id=str(task_id))
        if not task or task["project"] not in index:
            return 404, "Nie ma tego zadania.", {}
        if task["title"] != str(title):
            return 409, CONFLICT, {}
        key = (task["project"], task["file"], task["title"])
        if key in self._live_keys():
            return 409, "Agent jeszcze pracuje nad tym zadaniem.", {}
        part = []
        if variants is not None:
            if not isinstance(variants, list) or not all(isinstance(v, str) for v in variants):
                return 400, "Warianty to lista nazw.", {}
            wanted = list(dict.fromkeys(v.strip() for v in variants if v.strip()))
            if not wanted:
                return 400, "Wybierz co najmniej jeden wariant.", {}
            _, _, extra = self.review(task["id"])
            last = (extra.get("versions") or [{}])[-1]
            names = list(dict.fromkeys(variant_name(f["path"]) for f in last.get("files") or []
                                       if f.get("kind") == "image"))
            unknown = [v for v in wanted if v not in names]
            if unknown:
                return 400, "Nie ma wariantu %s." % ", ".join(unknown), {}
            if len(wanted) < len(names):
                part = [n for n in names if n in wanted]
        folder = index[task["project"]]
        d = task.get("detail") or {}
        try:
            with self.write_lock:
                ok = True
                if part:
                    answers = ["%s = %s" % (a.get("label", ""), a.get("value", "")) for a in d.get("answers") or []
                               if isinstance(a, dict) and a.get("label", "").lower() != VARIANTS_LABEL]
                    ok = self.projekt.set_detail(folder, task["file"], task["line"], task["title"], "odpowiedź",
                                                 answers + ["%s = %s" % (VARIANTS_LABEL, ", ".join(part))])
                if ok:
                    ok = self.projekt.update_task(folder, task["file"], task["line"], task["title"],
                                                  {"state": "done", "needsYou": ""})
        except ValueError as e:
            return 400, "Nie zapisano: %s." % e, {}
        except OSError:
            return 400, "Nie udało się zapisać zmiany.", {}
        return (200, "", {"accepted": part}) if ok else (409, CONFLICT, {})

    @staticmethod
    def _pm_wait(task, today):
        if "zgoda" in needs_of(task):
            return "czeka na zgodę"
        if any(not p.get("done") for p in task.get("waitingFor") or []):
            return "czeka na poprzedniki z po:"
        if "odbiór" in needs_of(task):
            return "czeka na odbiór"
        if task.get("state") != "todo" or task.get("blocked"):
            return "w toku lub zablokowane"
        if not task.get("date") or task["date"][:10] > today:
            return "czeka na termin"
        return ""

    def _pm_tasks(self, data):
        today = now_iso()[:10]
        ready, waiting = [], collections.Counter()
        by_id = {t.get("id"): t for t in data["tasks"] if t.get("id")}
        for task in data["tasks"]:
            if (task.get("executor") not in AGENT_EXECUTORS or task.get("state") == "done"
                    or task.get("kind") == "publikacja"):
                continue
            reason = self._pm_wait(task, today)
            if reason == "czeka na poprzedniki z po:" and any(
                    not p.get("done") and (by_id.get(p.get("id")) or {}).get("executor") == "ty"
                    for p in task.get("waitingFor") or []):
                reason = "czeka na Twoje zadania z po:"
            if reason:
                waiting[reason] += 1
            else:
                ready.append(task)
        return ready, waiting

    def _pm_launches(self, answer, allowed):
        text, wanted = take_run_lines(answer)
        statuses = []
        for pid, title in wanted:
            data, _ = self.load_projects()
            ready, _ = self._pm_tasks(data)
            matches = [t for t in ready if t["project"] == pid and t["title"] == title]
            if (pid, title) not in allowed or len(matches) != 1:
                statuses.append("Nie uruchomiono „%s”. Zadanie nie jest gotowe lub wymaga zgody." % title)
                continue
            statuses.append(self.launch_task(matches[0], data, pm=True)["text"])
        return "\n".join(filter(None, [text, *statuses]))

    def run_pm(self, auto=False):
        path = self.tool_path("claude")
        if not path:
            return 409, "Brak polecenia claude", {}
        data, _ = self.load_projects()
        if data["projectsSource"] != "registry":
            return 409, "Raport PM wymaga projektów z rejestru lub zbieracza.", {}
        registry = (self.env.get("PANEL_REGISTRY") or "").strip()
        command = "python3 standard/pm.py --tylko-rejestr"
        if registry:
            command += " --rejestr " + shlex.quote(os.path.abspath(os.path.expanduser(registry)))
        with self._lock:
            if any(r["kind"] == "pm" and r["state"] in LIVE for r in self._runs.values()):
                return 409, "Raport PM już trwa.", {}
            rec = self._new("pm", "claude", "Raport PM", auto)
            prompt = ("Przygotuj raport według standard/PM.md: uruchom `%s`. Jeżeli polecenie zgłosi błąd, podaj jego "
                      "przyczynę. Po udanym odczycie zapisz notatkę do raporty/%s.md (nadpisz wcześniejszą z tego dnia). "
                      "Odpowiedz raportem.\n" % (command, datetime.date.today().isoformat()))
            ready, waiting = self._pm_tasks(data)
            allowed = {(t["project"], t["title"]) for t in ready}
            prompt += ("\nGotowe zadania agentów (projekt | dokładny tytuł):\n" +
                       ("\n".join("%s | %s" % item for item in sorted(allowed)) or "Brak") +
                       "\nZadania oczekujące: " + json.dumps(waiting, ensure_ascii=False) +
                       "\nMożesz zwrócić osobne wiersze Uruchom: <id projektu> | <dokładny tytuł> wyłącznie "
                       "dla gotowych zadań. Gdy lista jest pusta, podaj powody oczekiwania.")
            args = self._claude_args(path, self.pm_model, ["--agent", "pm", "--allowedTools", PM_TOOLS,
                                                           "--disallowedTools", RUN_DENY, "--strict-mcp-config"])
            self._enqueue(rec, {"args": args, "cwd": self.root, "prompt": prompt, "pmAllowed": allowed})
        return 200, "", {"id": rec["id"]}

    # ---------- stały rytm postów ----------
    def _plan_posts(self, data, index, today):
        """Zakłada zadanie przygotowania posta, gdy w kampanii „stały rytm” zbliża się kolejny termin. True, gdy coś dodano."""
        added = False
        for pid, days in self.rytm.items():
            folder = index.get(pid)
            if not folder or not os.path.isfile(os.path.join(folder, RYTM_FILE)):
                continue
            tasks = [t for t in data["tasks"] if t["project"] == pid]
            if any(t["title"].startswith(POST_TASK) and t["title"].endswith(RYTM_SUFFIX) and t["state"] != "done"
                   for t in tasks):
                continue
            dates = []
            for t in tasks:
                if t.get("kind") == "publikacja" and t.get("file") == RYTM_FILE and t.get("date"):
                    try:
                        dates.append(datetime.date.fromisoformat(t["date"][:10]))
                    except ValueError:
                        pass
            slot = next_post_slot(dates, days, today)
            if (slot - today).days > RYTM_AHEAD:
                continue
            title = "%s%s%s" % (POST_TASK, slot.isoformat(), RYTM_SUFFIX)
            try:
                with self.write_lock:
                    self._add_task(folder, pid, title, {"executor": "claude", "machine": self.machine,
                                                        "date": today.isoformat(), "minutes": POST_REVIEW_MINUTES},
                                   self.post_detail(folder, slot.isoformat(), "", "post w stałym rytmie"))
                added = True
            except (ValueError, OSError, StopIteration) as e:
                log("Rytm postów (%s): %s" % (pid, e))
        return added

    def marketing_refs(self, folder):
        """Istniejące materiały marketingu projektu: STYL.md i plan (folder projektu albo folder karty)."""
        bases = [folder]
        cards = os.path.dirname(os.path.realpath(os.path.join(folder, "KARTA.md")))
        if cards != os.path.realpath(folder):
            bases.append(cards)
        out = []
        for patterns in (STYLE_FILES, PLAN_FILES):
            for pattern in patterns:
                hit = next((os.path.relpath(p, b).replace(os.sep, "/") for b in bases
                            for p in sorted(glob.glob(os.path.join(b, pattern))) if os.path.isfile(p)), None)
                if hit:
                    out.append(hit)
                    break
        return out

    @staticmethod
    def studio_refs(folder):
        """Studio filmów projektu (studio/ obok KARTA.md) według film.list_templates (te same zasady co nagrywarka):
        (szablony [{"name", "kind", "params", "error", …}], ścieżki do materiału). Szablon z błędem zostaje na liście
        z opisem błędu, żeby agent mógł go poprawić albo pominąć."""
        import film  # noqa: E402  (ten sam katalog; bez Playwright)
        cards = os.path.dirname(os.path.realpath(os.path.join(folder, "KARTA.md")))
        studio = os.path.join(cards, STUDIO_DIR)
        templates = film.list_templates(studio)
        refs = ["%s/szablony/%s.json" % (STUDIO_DIR, t["name"]) for t in templates]
        if os.path.isfile(os.path.join(studio, "marka.json")):
            refs.append(STUDIO_DIR + "/marka.json")
        return templates, refs

    @staticmethod
    def _template_line(t):
        if t.get("error"):
            return "%s (błąd: %s)" % (t["name"], t["error"][:120])
        return "%s (%s; parametry: %s)%s" % (t["name"], t["kind"], ", ".join(t.get("params") or []) or "brak",
                                             " wymagane: %s" % ", ".join(t["required"]) if t.get("required") else "")

    def post_detail(self, folder, day, channel, title):
        """Szczegóły zadania „Przygotować post na …”: cel, gotowe gdy, materiał (rytm, STYL.md, plan, studio filmów)."""
        templates, studio = self.studio_refs(folder)
        if templates:
            film = ("przy filmie także scenariusz.json z szablonu studia: {\"szablon\": \"<nazwa>\", \"parametry\": "
                    "{…}} (szablony: %s; wartości przykładowe w szablonie, wymagane podaj zawsze; szablon dobierz "
                    "według sekcji Filmy w STYL.md, inny niż w poprzednim filmie projektu) albo objaśnienie "
                    "{\"typ\": \"objasnienie\", \"plansze\": [{\"tekst\", \"podpis\", \"czas\", \"obraz\", "
                    "\"uklad\": tekst|srodek|liczba|cytat|lista|zrzut}]}; cytat tylko prawdziwy, liczby tylko "
                    "z materiałów projektu; sprawdź: python3 %s sprawdz <folder posta> (bez ostrzeżeń o haku i długości); "
                    "film nagrywa panel sam"
                    % ("; ".join(self._template_line(t) for t in templates), FILM_PY))
        else:
            film = ("przy filmie także scenariusz.json (wzór: posty/2026-11-20-film-a-opis-pl-de/scenariusz.json "
                    "albo objaśnienie {\"typ\": \"objasnienie\", \"plansze\": [{\"tekst\", \"podpis\", \"czas\"}]}), "
                    "film nagrywa panel sam")
        return {"cel": "post na %s%s: %s, do zatwierdzenia przez właściciela"
                       % (day, " (%s)" % channel if channel else "", title),
                "gotowe gdy": "obok KARTA.md jest folder posty/%s-<krótka-nazwa>/ z post.md (sekcje ## Facebook, "
                              "## LinkedIn, ## Alt) i grafika.svg albo grafika.png; %s" % (day, film),
                "materiał": [RYTM_FILE] + self.marketing_refs(folder) + studio}

    def result_detail(self, folder, day, channel, title):
        """Szczegóły zadania „Wpisz wynik publikacji …”: cel, gotowe gdy, materiał (rytm, plan)."""
        refs = [r for r in self.marketing_refs(folder) if not r.endswith("STYL.md")]
        return {"cel": "wynik publikacji „%s” z %s%s w %s (szczegóły pod publikacją)"
                       % (title, day, " (%s)" % channel if channel else "", RYTM_FILE),
                "gotowe gdy": "pod publikacją są wiersze wyświetlenia:, kliknięcia: i konta: (albo wynik:)",
                "materiał": [RYTM_FILE] + refs}

    # ---------- scenariusz nagrania (scenariusz.py, STANDARD.md „Scenariusz nagrania”) ----------
    def script_detail(self, folder, pub, rel, rec_day, way="ty"):
        """Szczegóły zadania „Przygotuj scenariusz nagrania na …”: cel, gotowe gdy (układ pliku), materiał.
        pub: publikacja z kampanii, rel: posty/<folder posta> względem karty, rec_day: dzień nagrania,
        way: ty (nagrywasz telefonem) albo ai (robisz w narzędziu AI według gotowych poleceń)."""
        day = str(pub.get("date") or "")[:10]
        title = scenariusz.pub_title(pub)
        channel = pub.get("channel") or ""
        refs = [pub["file"]] if pub.get("file") else []
        refs += [r for r in self.marketing_refs(folder) + self.film_plan_refs(folder) if r not in refs]
        where = " (%s)" % channel if channel else ""
        if way == "ai":
            goal = ("scenariusz filmu do publikacji „%s” z %s%s, który właściciel zrobi %s w narzędziu AI do wideo "
                    "(np. CapCut, Runway, Kling): dla każdej sceny gotowe polecenie do skopiowania (co widać, ruch "
                    "kamery, styl, długość), tekst lektora i napisy, muzyka; bez prawdziwych ludzi i bez udawania "
                    "prawdziwego produktu — ujęcia, które muszą pokazać prawdziwy produkt albo ekran, oznacz "
                    "„nagraj telefonem” albo „zrzut ekranu” (przeczytaj kampanię, plan filmów i dokumenty projektu)"
                    % (title, day, where, rec_day))
            shots, how = "„- [ ] polecenie dla AI | 5 s”", "narzędzie, format pionowy albo poziomy, styl i spójność scen"
        else:
            goal = ("scenariusz nagrania filmu do publikacji „%s” z %s%s: co nagrać, jak i po co; właściciel "
                    "nagrywa sam telefonem %s, więc pisz praktycznie i konkretnie (przeczytaj kampanię, plan "
                    "filmów i dokumenty projektu)" % (title, day, where, rec_day))
            shots, how = "„- [ ] opis ujęcia | 5 s”", "miejsce, światło, kadr, telefon pionowo albo poziomo, rekwizyty"
        return {"cel": goal,
                "gotowe gdy": "obok KARTA.md jest plik %s/%s w układzie: „# Scenariusz nagrania: <tytuł>”, pola "
                              "„- stan: propozycja”, „- publikacja: %s”, „- nagranie: %s”, „- sposób: %s”, sekcje "
                              "## Po co (cel, dla kogo), ## Co nagrać (wiersze %s), ## Jak (%s), ## Co powiedzieć "
                              "(tekst albo punkty), ## Na koniec (wezwanie do działania), ## Gotowe gdy; każda sekcja "
                              "wypełniona; post.md i zadania nagrania bez zmian"
                              % (rel, scenariusz.FILE, day, rec_day, way, shots, how),
                "materiał": refs}

    @staticmethod
    def film_plan_refs(folder):
        """Dokumenty z planem filmów projektu (nazwa z „film”, folder projektu albo docs/, marketing/), najwyżej 3."""
        out = []
        for sub in ("", "docs", "marketing", "kampanie"):
            base = os.path.join(folder, sub) if sub else folder
            try:
                names = sorted(os.listdir(base))
            except OSError:
                continue
            for n in names:
                if n.lower().endswith(".md") and "film" in n.lower() and os.path.isfile(os.path.join(base, n)):
                    out.append((sub + "/" if sub else "") + n)
        return out[:3]

    def _plan_scripts(self, data, index, today):
        """Filmy właściciela (karta `nagrywa: ty`) z publikacją w ciągu SCRIPT_AHEAD dni bez scenariusz.md: zadanie
        agenta „Przygotuj scenariusz nagrania na <dzień>: <tytuł>” (raz; bez folderu posta agent go zakłada).
        True, gdy coś dodano."""
        added = False
        horizon = (today + datetime.timedelta(days=SCRIPT_AHEAD)).isoformat()
        owners = {p["id"]: p.get("filmMix") or {"ty": 100} for p in data["projects"]
                  if p.get("filmOwner") and p.get("state") not in self.projekt.QUIET_STATES}
        with self._lock:
            ways = self._state.setdefault("filmWays", {})      # „projekt|dzień” -> ty | ai | panel (podział karty)
        for pid in sorted(owners):
            folder = index.get(pid)
            if not folder:
                continue
            tasks = [t for t in data["tasks"] if t["project"] == pid]
            titles = {t["title"] for t in tasks}
            cards = os.path.dirname(os.path.realpath(os.path.join(folder, "KARTA.md")))
            for t in tasks:
                day = str(t.get("date") or "")[:10]
                if t.get("kind") != "publikacja" or t["state"] == "done" or not scenariusz.is_film(t) \
                        or not (today.isoformat() <= day <= horizon):
                    continue
                if publication_task_title(t, self.projekt) in titles or any(
                        x.startswith(scenariusz.PREP_TASK + day) for x in titles):
                    continue                    # zadanie już jest (także zrobione: agent nie zostawił pliku)
                post = scenariusz.post_dir(cards, day)
                if post and os.path.isfile(os.path.join(post, scenariusz.FILE)):
                    continue
                key = "%s|%s" % (pid, day)
                with self._lock:
                    way = ways.get(key)
                    if way not in scenariusz.WAYS:
                        used = {}
                        for k, w in ways.items():
                            if k.startswith(pid + "|"):
                                used[w] = used.get(w, 0) + 1
                        way = ways[key] = scenariusz.pick_way(owners[pid], used)
                        self._save_state()
                if way == "panel":
                    continue                    # ten film nagrywa panel (studio), bez scenariusza dla właściciela
                try:
                    with self.write_lock:
                        if self._has_publication_task(folder, pid, t):
                            continue
                        post = post or scenariusz.new_post_dir(cards, day, scenariusz.pub_title(t))
                        title = self.projekt._clean("%s%s: %s" % (scenariusz.PREP_TASK, day,
                                                                   scenariusz.pub_title(t)), 120)
                        self._add_task(folder, pid, title,
                                       {"executor": "claude", "machine": self.machine, "date": today.isoformat()},
                                       self.script_detail(folder, t, "posty/" + os.path.basename(post),
                                                          scenariusz.rec_day(day, today), way))
                    titles.add(title)
                    added = True
                except (ValueError, OSError, StopIteration) as e:
                    log("Scenariusz nagrania (%s): %s" % (pid, e))
        return added

    def _add_task(self, folder, pid, title, changes, detail=None):
        """Nowe zadanie w „Do rozplanowania” z polami; wywołujący trzyma write_lock."""
        self.projekt.add_task(folder, title)
        task = next(t for t in self.projekt.read_project(folder, pid)["tasks"] if t["title"] == title)
        self.projekt.update_task(folder, task["file"], task["line"], title, changes)
        for key, value in (detail or {}).items():
            self.projekt.set_detail(folder, task["file"], task["line"], title, key, value)

    def _has_publication_task(self, folder, pid, pub):
        name = publication_task_title(pub, self.projekt)
        return any(t["file"] == "ZADANIA.md" and t["title"] == name
                   for t in self.projekt.read_project(folder, pid)["tasks"])

    def _plan_rhythm(self, data, index, today):
        """Rytm marketingu z kampanie/staly-rytm.md (każdy projekt z tym plikiem):
        - publikacja z kiedy w ciągu RYTM_AHEAD dni bez folderu posty/<kiedy>-*: zadanie „Przygotować post na <kiedy>: <tytuł>”;
        - publikacja zrobiona ponad 48 h temu bez wynik:: zadanie właściciela „Wpisz wynik publikacji <tytuł>” (raz).
        True, gdy coś dodano."""
        added = False
        changed = False
        horizon = (today + datetime.timedelta(days=RYTM_AHEAD)).isoformat()
        old = (today - datetime.timedelta(days=RYTM_RESULT_DAYS)).isoformat()
        with self._lock:
            done_keys = set(self._state.get("rytmDone") or [])
        quiet = {p["id"] for p in data["projects"] if p.get("state") in self.projekt.QUIET_STATES}
        for pid, folder in index.items():
            if pid in quiet or not os.path.isfile(os.path.join(folder, RYTM_FILE)):
                continue
            tasks = [t for t in data["tasks"] if t["project"] == pid]
            titles = {t["title"] for t in tasks}
            posts = os.path.join(os.path.dirname(os.path.realpath(os.path.join(folder, "KARTA.md"))), "posty")
            try:
                folders = os.listdir(posts)
            except OSError:
                folders = []
            for t in tasks:
                if t.get("kind") != "publikacja" or t.get("file") != RYTM_FILE:
                    continue
                day = str(t.get("date") or "")[:10]
                if not re.match(r"^\d{4}-\d\d-\d\d$", day):
                    continue
                new = None
                detail = t.get("detail") or {}
                # nagranie to nie publikacja; opis pod film dopiero po nagraniu
                film = t["title"].startswith(FILM_TASK) or any(w.startswith(FILM_TASK) for w in self.projekt.waiting_titles(t))
                if t["state"] != "done" and today.isoformat() <= day <= horizon and not detail.get("refs") and not film \
                        and not any((n == day or n.startswith(day + "-")) and has_post(os.path.join(posts, n))
                                    for n in folders):
                    title = self.projekt._clean("%s%s: %s" % (POST_TASK, day, t["title"]), 160)
                    if title not in titles and publication_task_title(t, self.projekt) not in titles:
                        new = (title, {"executor": "claude", "machine": self.machine, "date": today.isoformat(),
                                       "minutes": POST_REVIEW_MINUTES},
                               self.post_detail(folder, day, t.get("channel") or "", t["title"]))
                elif t["state"] == "done" and day < old and not has_result(detail):
                    key = "%s|%s|%s" % (pid, day, t["title"])
                    title = self.projekt._clean("%s%s" % (RESULT_TASK, t["title"]), 160)
                    if key not in done_keys:
                        done_keys.add(key)
                        changed = True
                        if title not in titles:
                            new = (title, {"executor": "ty", "date": today.isoformat(), "minutes": RESULT_MINUTES},
                                   self.result_detail(folder, day, t.get("channel") or "", t["title"]))
                if not new:
                    continue
                try:
                    with self.write_lock:
                        if new[0].startswith(POST_TASK) and self._has_publication_task(folder, pid, t):
                            continue
                        self._add_task(folder, pid, *new)
                    titles.add(new[0])
                    added = True
                except (ValueError, OSError, StopIteration) as e:
                    log("Rytm marketingu (%s): %s" % (pid, e))
        if changed:
            with self._lock:
                self._state["rytmDone"] = sorted(done_keys)[-RYTM_KEEP:]
                self._save_state()
        return added

    # ---------- plan dnia ----------
    def plan_candidates(self):
        """Otwarte zadania wszystkich projektów w skrócie dla PM: id, projekt, etap z terminem, wykonawca, czy agent może."""
        data, _ = self.load_projects()
        live = self._live_keys()
        tools = {"claude": self.tool_found("claude"), "codex": self.tool_found("codex")}
        names = {p["id"]: p.get("name", p["id"]) for p in data["projects"]}
        stages = {s["id"]: s for s in data["stages"]}
        out = []
        for t in data["tasks"]:
            if t.get("state") == "done":
                continue
            pub = t.get("kind") == "publikacja"
            if pub and "zgoda" not in needs_of(t):
                continue                    # publikacje tylko te, które czekają na zgodę właściciela
            if not pub and t.get("kind") != "zadanie":
                continue
            st = stages.get(t.get("stage")) or {}
            block = run_block(t, data["projectsSource"], live, tools)
            out.append({"id": t["id"], "project": names.get(t["project"], t["project"]), "title": t["title"],
                        "kind": t.get("kind", ""), "goal": (t.get("detail") or {}).get("goal", ""),
                        "minutes": t.get("minutes") or 0,
                        "stage": st.get("title", "") or (t.get("group", "") if pub else ""),
                        "stageDue": st.get("date") or "", "date": t.get("date") or "",
                        "executor": t.get("executor") or "", "state": t.get("state", ""),
                        "needsYou": t.get("needsYou") or "", "agent": not block, "why": block})
        return out

    def plan_prompt(self, text, cands, today):
        rows = json.dumps([{k: c[k] for k in ("id", "project", "kind", "title", "goal", "minutes", "stage", "stageDue",
                                              "date", "executor", "state", "needsYou", "agent")} for c in cands],
                          ensure_ascii=False)
        return "\n".join([
            "Jesteś kierownikiem projektów właściciela. Dziś jest %s." % today,
            "Właściciel napisał, co chce dziś robić:",
            "<<<", text, ">>>",
            "",
            "Poniżej wszystkie otwarte zadania jego projektów (JSON). Pole agent=true oznacza, że zadanie może wykonać agent;",
            "agent=false to zadania właściciela albo czekające na jego zgodę. kind=publikacja to publikacja z kampanii",
            "czekająca na zgodę właściciela. goal to cel zadania, minutes to czas pracy właściciela w minutach (0: nie podano).",
            rows,
            "",
            "Ułóż plan na dziś:",
            "- „agenci”: najwyżej %d zadań z agent=true, najważniejsze najpierw (terminy etapów, prośba właściciela);" % PLAN_MAX,
            "- „ty”: najwyżej 5 zadań z agent=false, które właściciel powinien dziś zrobić albo rozstrzygnąć "
            "(zgody na publikacje też); w podsumowaniu podaj łączny czas z pola minutes, gdy jest znany;",
            "- nie wymyślaj zadań spoza listy; jeśli prośba nie pasuje do żadnego zadania, napisz to w „uwagi”.",
            "Odpowiedz po polsku: 2–4 krótkie zdania podsumowania, a na końcu jeden blok:",
            "```json",
            '{"agenci": ["id", ...], "ty": ["id", ...], "uwagi": "tekst albo pusty"}',
            "```",
            "Nie używaj narzędzi i niczego nie zmieniaj.",
        ]) + "\n"

    def run_plan(self, text):
        text = re.sub(r"\s+", " ", str(text or "")).strip()
        if not text:
            return 400, "Napisz, co chcesz dziś robić.", {}
        if len(text) > 1500:
            return 400, "Najwyżej 1500 znaków.", {}
        path = self.tool_path("claude")
        if not path:
            return 409, "Brak polecenia claude", {}
        cands = self.plan_candidates()
        with self._lock:
            if any(r["kind"] == "plan" and r["state"] in LIVE for r in self._runs.values()):
                return 409, "Plan dnia już się układa.", {}
            rec = self._new("plan", "claude", "Plan dnia")
            rec["ask"] = text
            rec["plan"] = None
            prompt = self.plan_prompt(text, cands, datetime.date.today().isoformat())
            args = _command(path) + ["-p", "--output-format", "stream-json", "--verbose", "--permission-mode", "default",
                                     "--allowedTools", "Read"]
            if self.pm_model:
                args += ["--model", self.pm_model]
            os.makedirs(self.runs_dir, exist_ok=True)
            cmap = {c["id"]: {"id": c["id"], "title": c["title"], "project": c["project"], "agent": c["agent"],
                              "why": c["why"], "needsYou": c["needsYou"]} for c in cands}
            self._enqueue(rec, {"args": args, "cwd": self.runs_dir, "prompt": prompt, "cands": cmap})
        return 200, "", {"id": rec["id"]}

    @staticmethod
    def parse_plan(text, cmap):
        """Z odpowiedzi PM: (tekst bez bloku JSON, {"agents": [...], "you": [...], "note": str}) albo (tekst, None)."""
        text = str(text or "")
        blocks = list(re.finditer(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S))
        raw, body = None, text
        if blocks:
            raw, body = blocks[-1].group(1), text[:blocks[-1].start()] + text[blocks[-1].end():]
        else:
            m = re.search(r"\{[^{}]*\"agenci\"[^{}]*\}", text, re.S)
            if m:
                raw, body = m.group(0), text[:m.start()] + text[m.end():]
        try:
            obj = json.loads(raw) if raw else None
        except ValueError:
            obj = None
        if not isinstance(obj, dict):
            return text.strip(), None

        def pick(key, agent, limit):
            seen, out = set(), []
            for i in obj.get(key) or []:
                c = cmap.get(str(i))
                if c and c["id"] not in seen and c["agent"] == agent:
                    seen.add(c["id"])
                    out.append({"id": c["id"], "title": c["title"], "project": c["project"],
                                "why": c["why"], "needsYou": c["needsYou"]})
            return out[:limit]
        return body.strip(), {"agents": pick("agenci", True, PLAN_MAX), "you": pick("ty", False, 5),
                              "note": _short(str(obj.get("uwagi") or "").strip(), 400)}

    def accept_plan(self, rid, ids):
        """Uruchamia wybrane zadania z planu. Zwraca (kod, błąd, {"started": [...], "failed": [...]})."""
        rec = self.get(str(rid))
        if not rec or rec["kind"] != "plan" or not rec.get("plan"):
            return 404, "Nie ma takiego planu.", {}
        allowed = {a["id"]: a["title"] for a in rec["plan"].get("agents") or []}
        if not isinstance(ids, list) or not ids:
            return 400, "Zaznacz zadania do uruchomienia.", {}
        started, failed = [], []
        for i in ids[:PLAN_MAX]:
            i = str(i)
            if i not in allowed:
                failed.append({"id": i, "error": "Spoza planu."})
                continue
            code, err, extra = self.run_task(i, allowed[i])
            if code == 200:
                started.append({"id": i, "runId": extra.get("id", "")})
            else:
                failed.append({"id": i, "error": err})
        with self._lock:
            live = self._runs.get(rec["id"])
            if live is not None:
                live["accepted"] = sorted(set((live.get("accepted") or []) + [s["id"] for s in started]))
                self._save(live)
        if not started:
            return 409, failed[0]["error"] if failed else "Nic nie uruchomiono.", {"started": [], "failed": failed}
        return 200, "", {"started": started, "failed": failed}

    def run_limits(self):
        results = {tool: self.run_check(tool, limits=True) for tool in ("claude", "codex")}
        ids = [extra["id"] for code, _, extra in results.values() if code == 200]
        errors = [error for code, error, _ in results.values() if code != 200]
        return (200, "", {"ids": ids, "errors": errors}) if ids else (409, " ".join(errors), {})

    def run_check(self, tool="claude", limits=False):
        if tool not in ("claude", "codex"):
            return 400, "Nieznane narzędzie.", {}
        path = self.tool_path(tool)
        if not path:
            return 409, "Brak polecenia %s" % tool, {}
        with self._lock:
            if any(r["kind"] == "check" and r["tool"] == tool and r["state"] in LIVE for r in self._runs.values()):
                return 409, "Test już trwa.", {}
            rec = self._new("check", tool, "Odczyt limitu" if limits else "Test połączenia")
            os.makedirs(self.runs_dir, exist_ok=True)
            if tool == "codex":
                args = _command(path) + ["exec", "--json", "--sandbox", "read-only", "--skip-git-repo-check", "-"]
            else:
                args = _command(path) + ["-p", "--output-format", "stream-json", "--verbose", "--model", "haiku"]
                if limits:
                    args += ["--tools", "", "--strict-mcp-config"]
            self._enqueue(rec, {"args": args, "cwd": self.runs_dir, "prompt": CHECK_PROMPT + "\n"})
        return 200, "", {"id": rec["id"]}

    # ---------- grafiki do postów (Codex, AGENCI.md: „Grafiki (Codex)”) ----------
    def graphic_tool(self):
        """Stan Codexa dla edytora posta: need = "" (gotowy) | "off" | "install" | "login"."""
        mode = grafiki.mode(self.env)
        path = self.tool_path("codex")
        with self._lock:
            info = dict(self._tools.get("codex") or self._tool_blank())
            known = self._tools_read
            cx = self._cx_login
            login = {"active": True, "url": cx["url"], "code": cx["code"]} \
                if cx and cx["proc"].poll() is None and cx["url"] else {"active": False}
        need = "off" if mode == "wylaczone" else "install" if not path else \
            "login" if known and not info.get("loggedIn") else ""
        return {"mode": mode, "need": need, "found": bool(path), "loggedIn": bool(info.get("loggedIn")),
                "checked": known, "loginCmd": self.login_cmd("codex", path), "loginWeb": self.login_web,
                "agentUser": self.agent_user, "login": login}

    def graphic_runs(self, pid, day):
        """Zlecenia grafiki tego posta, najnowsze najpierw (najwyżej 5)."""
        with self._lock:
            runs = [r for r in reversed(list(self._runs.values()))
                    if r["kind"] == "grafika" and r.get("project") == pid and r.get("post") == day]
            return [{k: r.get(k) for k in ("id", "state", "error", "result", "ask", "variants", "queuedAt", "endedAt",
                                           "activity")} for r in runs[:5]]

    def run_graphic(self, pid, day, folder, text, mode="zachowaj", wanted="", project_name=""):
        """Polecenie w rozmowie o grafice posta: `codex exec` w folderze posta z obrazem wejściowym (--image).
        mode: „zachowaj” (obróbka zdjęcia Pillow, bez generowania) albo „nowa” ($imagegen). Obraz wejściowy: oczekująca
        wersja z rozmowy (iteracja), inaczej wanted (grafika.png albo zdjęcie karuzeli). (kod, błąd, dane)."""
        text = re.sub(r"\s+", " ", str(text or "")).strip()
        if len(text) < grafiki.TEXT_MIN:
            return 400, "Napisz, co zrobić z grafiką.", {}
        if len(text) > grafiki.TEXT_MAX:
            return 400, "Najwyżej %d znaków." % grafiki.TEXT_MAX, {}
        if mode not in grafiki.TRYBY:
            return 400, "Nieznany tryb.", {}
        name, source = grafiki.chat_base(folder, str(wanted or ""))
        if mode == "zachowaj" and not name:
            return 409, "Post nie ma zdjęcia do poprawy. Wyłącz „Zachowaj zdjęcie”, aby zrobić nową grafikę.", {}
        tool = self.graphic_tool()
        if tool["need"] == "off":
            return 409, "Grafiki przez Codex są wyłączone w ustawieniach panelu (PANEL_GRAFIKA).", {"need": "off"}
        if tool["need"] == "install":
            return 409, "Codex nie jest zainstalowany na tym komputerze.", {"need": "install"}
        if tool["need"] == "login":
            return 409, "Codex nie jest zalogowany. Zaloguj się kontem ChatGPT.", {"need": "login"}
        path = self.tool_path("codex")
        with self._lock:
            if any(r["kind"] == "grafika" and r["state"] in LIVE and r.get("project") == pid and r.get("post") == day
                   for r in self._runs.values()):
                return 409, "Codex już pracuje nad grafiką tego posta.", {}
            start = grafiki.next_number(folder)
            rec = self._new("grafika", "codex", "Grafika do posta %s" % day, project=pid,
                            project_name=project_name or pid)
            rec.update(post=day, ask=_short(text, 300), inputs=[name] if name else [], variants=[], mode=mode)
            args = _command(path) + ["exec", "--json", "--sandbox", "workspace-write", "--skip-git-repo-check",
                                     "-C", folder]
            if name:        # jeden argument z „=”: --image przyjmuje kilka wartości i nie może połknąć „-”
                args.append("--image=" + os.path.join(folder, name))
            args.append("-")
            prompt = grafiki.prompt_keep(text, name, start, folder) if mode == "zachowaj" else \
                grafiki.prompt(text, [name] if name else [], start, folder)
            try:
                grafiki.chat_start(folder, rec["id"], text, mode, name, source)
            except OSError as e:
                return 500, "Nie zapisano rozmowy o grafice: %s." % (e.strerror or e), {}
            self._enqueue(rec, {"args": args, "cwd": folder, "prompt": prompt, "limit": grafiki.timeout(self.env),
                                "graphic": {"folder": folder, "start": start, "since": time.time(), "mode": mode}})
        return 200, "", {"id": rec["id"]}

    def graphic_live(self, run_id):
        """True, gdy uruchomienie grafiki o tym id czeka albo trwa."""
        with self._lock:
            r = self._runs.get(run_id)
            return bool(r) and r["state"] in LIVE

    def _graphic_done(self, rec, priv, state, error, result):
        """Po poleceniu grafiki: wynik z folderu posta (w trybie „nowa” także z katalogu sesji Codex, gdy sam go nie
        skopiował), sprawdzenie i wpis w rozmowie (grafiki.chat_finish). (stan, błąd, wynik)."""
        g = priv.get("graphic") or {}
        if not g.get("folder"):
            return state, error, result
        home = grafiki.codex_home(self.env, self.agent_user)
        session = os.path.join(home, "generated_images", priv["thread"]) if home and priv.get("thread") else ""
        keep = g.get("mode") == "zachowaj"
        out = ""
        try:
            made = grafiki.collect(g["folder"], g["start"], g["since"], "" if keep else session) \
                if state != "stopped" else []
            state, error, result, out = grafiki.chat_finish(g["folder"], rec["id"], made, state, error, result,
                                                            session if keep else "", g["since"])
        except Exception as e:      # błąd zbierania nie może zatrzymać zamknięcia uruchomienia
            log("Grafika %s: %s" % (rec["id"], e))
            if state == "done":
                state, error = "error", "Nie udało się zapisać wyniku."
        with self._lock:
            rec["variants"] = [out] if out else []
        return state, error, result

    def _codex_device_login(self, args):
        """`codex login --device-auth` w tle: adres strony i jednorazowy kod dla właściciela. Proces sam kończy się
        po potwierdzeniu kodu na stronie OpenAI; panel niczego nie wpisuje."""
        with self._lock:
            cur = self._cx_login
            if cur and cur["proc"].poll() is None and cur["url"] and cur["code"]:
                return 200, "", {"url": cur["url"], "code": cur["code"]}
            if cur and cur["proc"].poll() is None:
                try:
                    cur["proc"].kill()
                except OSError:
                    pass
            try:
                proc = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        env=child_env(self.env), cwd=tempfile.gettempdir(), encoding="utf-8",
                                        errors="replace", bufsize=1, start_new_session=not WINDOWS)
            except OSError as e:
                return 500, "Nie udało się uruchomić logowania Codex: %s" % e, {}
            rec = {"proc": proc, "url": "", "code": "", "lines": collections.deque(maxlen=20)}
            self._cx_login = rec
        read_done = threading.Event()

        def read():
            for line in proc.stdout:
                line = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", line).strip()
                if not line:
                    continue
                rec["lines"].append(_short(line, 300))
                m = re.search(r"https://\S+", line)
                if m and not rec["url"]:
                    rec["url"] = m.group(0).rstrip(".,)")
                elif re.match(r"^[A-Z0-9]{4,}-[A-Z0-9]{4,}$", line) and not rec["code"]:
                    rec["code"] = line
            read_done.set()
            with self._lock:
                self._tools_at = 0.0
        threading.Thread(target=read, daemon=True).start()

        def expire():
            if proc.poll() is None:
                try:
                    proc.kill()
                except OSError:
                    pass
        timer = threading.Timer(LOGIN_TTL + 300, expire)     # kod urządzenia ważny 15 min
        timer.daemon = True
        timer.start()
        end = time.time() + 15
        while time.time() < end and not (rec["url"] and rec["code"]) and not read_done.is_set():
            time.sleep(0.05)
        if not (rec["url"] and rec["code"]):
            expire()
            text = " ".join(rec["lines"]) or "brak odpowiedzi"
            if re.search(r"device code|enable", text, re.I):
                return 409, "Włącz logowanie kodem urządzenia w ustawieniach bezpieczeństwa ChatGPT i spróbuj " \
                            "jeszcze raz (%s)." % _short(text, 160), {}
            return 500, "Logowanie Codex nie podało adresu: %s" % _short(text, 200), {}
        return 200, "", {"url": rec["url"], "code": rec["code"]}

    def open_login(self, tool="claude"):
        """Otwiera okno terminala z poleceniem logowania; właściciel loguje się w przeglądarce.
        Panel niczego nie wpisuje i nie widzi danych logowania."""
        if tool not in ("claude", "codex"):
            return 400, "Nieznane narzędzie.", {}
        path = self.tool_path(tool)
        if not path:
            return 409, "Brak polecenia %s. Instalacja: INSTALACJA.md." % tool, {}
        args = _command(path) + (["login"] if tool == "codex" else ["auth", "login"])
        if self.login_web:
            if tool != "claude":            # serwer bez okna: kod urządzenia (właściciel potwierdza go na stronie OpenAI)
                return self._codex_device_login(self.as_agent(args + ["--device-auth"]))
            return self._login_web_start(self.as_agent(args))
        try:
            if sys.platform == "darwin":
                line = " ".join(shlex.quote(a) for a in args)
                line = line.replace("\\", "\\\\").replace('"', '\\"')
                script = 'tell application "Terminal"\nactivate\ndo script "%s"\nend tell' % line
                self.launcher(["osascript", "-e", script])
            elif WINDOWS:
                cmd = "& " + " ".join('"%s"' % a for a in args)
                self.launcher(["powershell", "-NoExit", "-Command", cmd],
                              creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0))
            else:
                return 409, "Otwórz terminal i wpisz: %s" % self.login_cmd(tool, path), {}
        except OSError as e:
            return 500, "Nie udało się otworzyć terminala: %s" % e, {}
        with self._lock:
            self._tools_at = 0.0
        return 200, "", {"opened": True}

    # ---------- logowanie przez panel (serwer bez okna) ----------
    def _login_web_start(self, args):
        """Uruchamia `claude auth login` w tle i zwraca adres strony logowania. Kod wpisuje właściciel w panelu."""
        with self._lock:
            cur = self._login
            if cur and cur["proc"].poll() is None and cur["url"]:
                return 200, "", {"url": cur["url"]}
            if cur:
                self._login_stop(cur)
            try:
                proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        env=child_env(self.env), cwd=self.runs_dir if os.path.isdir(self.runs_dir) else None,
                                        encoding="utf-8", errors="replace", bufsize=1, start_new_session=not WINDOWS)
            except OSError as e:
                return 500, "Nie udało się uruchomić logowania: %s" % e, {}
            rec = {"proc": proc, "url": "", "lines": collections.deque(maxlen=20), "at": time.time()}
            self._login = rec

        def read():
            for line in proc.stdout:
                line = line.strip()
                if not line:
                    continue
                rec["lines"].append(_short(line, 300))
                m = re.search(r"https://\S+", line)
                if m and not rec["url"]:
                    rec["url"] = m.group(0)
        threading.Thread(target=read, daemon=True).start()
        timer = threading.Timer(LOGIN_TTL, lambda: self._login_expire(rec))
        timer.daemon = True
        timer.start()
        end = time.time() + 15
        while time.time() < end and not rec["url"] and proc.poll() is None:
            time.sleep(0.05)
        if not rec["url"]:
            with self._lock:
                self._login_stop(rec)
            return 500, "Logowanie nie podało adresu: %s" % (" ".join(rec["lines"]) or "brak odpowiedzi"), {}
        return 200, "", {"url": rec["url"]}

    def _login_stop(self, rec):
        if rec["proc"].poll() is None:
            try:
                rec["proc"].kill()
            except OSError:
                pass
        if self._login is rec:
            self._login = None

    def _login_expire(self, rec):
        with self._lock:
            if self._login is rec:
                self._login_stop(rec)

    def submit_login_code(self, code):
        """Przekazuje kod ze strony logowania do `claude auth login`. Kodu nie zapisuje ani nie loguje."""
        code = str(code or "").strip()
        if not code or len(code) > 1000 or any(c.isspace() for c in code):
            return 400, "Wklej cały kod ze strony logowania (bez spacji).", {}
        with self._lock:
            rec = self._login
        if not rec or rec["proc"].poll() is not None:
            return 409, "Logowanie nie trwa. Kliknij „Zaloguj” jeszcze raz.", {}
        seen = len(rec["lines"])
        try:
            rec["proc"].stdin.write(code + "\n")
            rec["proc"].stdin.flush()
        except (OSError, ValueError):
            return 409, "Logowanie się zakończyło. Kliknij „Zaloguj” jeszcze raz.", {}
        end = time.time() + 45
        while time.time() < end and rec["proc"].poll() is None and len(rec["lines"]) == seen:
            time.sleep(0.05)
        time.sleep(0.3)
        while time.time() < end and rec["proc"].poll() is None and \
                not any("code" in l.lower() for l in list(rec["lines"])[seen:]):
            time.sleep(0.1)
        done = rec["proc"].poll()
        news = [re.sub(r"^(Paste code here if prompted >\s*)+", "", l).strip() for l in list(rec["lines"])[seen:]]
        news = [l for l in news if l]
        if done == 0:
            with self._lock:
                if self._login is rec:
                    self._login = None
            code_, _, extra = self.recheck_login()
            if extra["loggedIn"]["claude"]:
                return 200, "", {"loggedIn": True}
            return 409, "Logowanie zakończone, ale Claude nadal niezalogowany.", {}
        if done is None:
            return 400, "Kod nie został przyjęty: %s" % (_short(" ".join(news), 200) or "spróbuj jeszcze raz"), {}
        with self._lock:
            if self._login is rec:
                self._login = None
        return 400, "Logowanie nie powiodło się: %s" % (_short(" ".join(news), 200) or "kod %s" % done), {}

    def recheck_login(self):
        """Ponowny odczyt stanu narzędzi; po udanym logowaniu zdejmuje blokadę needsLogin."""
        self.refresh_tools(force=True, wait=True)
        with self._lock:
            tools = dict(self._tools or {})
            if (tools.get("claude") or {}).get("loggedIn") and self._state["needsLogin"]:
                self._state["needsLogin"] = False
                self._save_state()
        return 200, "", {"loggedIn": {t: bool((tools.get(t) or {}).get("loggedIn")) for t in ("claude", "codex")}}

    def set_parallel(self, value):
        """POST /api/agent/rownolegle {"value": 1–4}: ile uruchomień naraz (różne projekty; projekt: jedno)."""
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= PARALLEL_MAX:
            return 400, "Podaj liczbę od 1 do %d." % PARALLEL_MAX, {}
        with self._lock:
            self._state["parallel"] = value
            self.max_parallel = value
            self._save_state()
        self._pump()
        return 200, "", {"maxParallel": value}

    def deploy_hold(self):
        """Wdrożenie panelu czeka, aż agenci skończą (wdroz-panel, stan „waiting”): nowe uruchomienia czekają
        w kolejce. Odczyt najwyżej co 5 s; stan starszy niż 40 min się nie liczy."""
        at, value = self._hold
        if time.time() - at < 5:
            return value
        value = False
        try:
            with open(self.deploy_file, encoding="utf-8") as f:
                st = json.load(f)
            if isinstance(st, dict) and st.get("state") == "waiting":
                when = datetime.datetime.fromisoformat(str(st.get("at") or "")[:19])
                value = (datetime.datetime.now() - when).total_seconds() < 2400
        except (OSError, ValueError, TypeError):
            value = False
        self._hold = (time.time(), value)
        return value

    @staticmethod
    def _family(rec):
        """Klucz projektu dla limitu „jedno uruchomienie na projekt” (części liczą się z projektem głównym)."""
        return rec.get("family") or rec.get("project") or ""

    def set_automat(self, enabled):
        if not isinstance(enabled, bool):
            return 400, "Podaj enabled: true albo false.", {}
        with self._lock:
            self._state["automat"] = enabled
            self._save_state()
        return 200, "", {}

    def stop(self, rid):
        """Zdejmuje z kolejki albo kończy proces razem z jego grupą."""
        with self._lock:
            rec = self._runs.get(str(rid))
            if not rec:
                return 404, "Nie ma takiego uruchomienia.", {}
            if rec["state"] not in LIVE:
                return 409, "Uruchomienie już się zakończyło.", {}
            priv = self._priv.setdefault(rec["id"], {})
            priv["stop"] = True
            queued = rec["id"] in self._queue
            if queued:
                self._queue.remove(rec["id"])
            proc = priv.get("proc")
        if queued:
            self._finish(rec, "stopped", "")
        elif proc is not None:
            self._kill(proc)
        return 200, "", {}

    # ---------- przebieg ----------
    def _git_pull(self, folder):
        """(wpis do kroków, czy coś pobrano). Tylko przy czystym repozytorium; błąd nie blokuje uruchomienia."""
        def git(*args, **kw):
            return subprocess.run(["git"] + list(args), cwd=folder, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, encoding="utf-8", errors="replace", **NO_WINDOW, **kw)
        try:
            if git("rev-parse", "--is-inside-work-tree", timeout=15).returncode != 0:
                return "", False
            status = git("status", "--porcelain", timeout=30)
            if status.returncode != 0:
                return "git pull: nie udało się odczytać stanu repozytorium", False
            if status.stdout.strip():
                return "git pull pominięty: niezapisane zmiany w repozytorium", False
            before = git("rev-parse", "HEAD", timeout=15).stdout.strip()
            pull = git("pull", "--ff-only", timeout=60)
            if pull.returncode != 0:
                return "git pull: nie udało się", False
            after = git("rev-parse", "HEAD", timeout=15).stdout.strip()
            return ("git pull: pobrano zmiany" if after != before else "git pull: bez zmian"), after != before
        except (OSError, subprocess.SubprocessError):
            return "git pull: nie udało się", False

    def _pump(self):
        """Start uruchomień z kolejki: najwyżej max_parallel naraz, zadania najwyżej jedno na projekt; w czasie
        oczekiwania wdrożenia na koniec pracy agentów nowe zadania czekają (raport PM i test połączenia nie)."""
        hold = self.deploy_hold() if self._queue else False
        with self._lock:
            running = [r for r in self._runs.values() if r["state"] == "running"]
            busy = {self._family(r) for r in running if r.get("kind") == "task"}
            for rid in list(self._queue):
                if len(running) >= self.max_parallel:
                    break
                rec = self._runs[rid]
                fam = self._family(rec) if rec.get("kind") == "task" else ""
                if fam and fam in busy or hold and rec.get("kind") == "task":
                    continue
                self._queue.remove(rid)
                rec["state"], rec["startedAt"] = "running", now_iso()
                self._priv[rec["id"]]["t0"] = time.time()
                self._save(rec)
                running.append(rec)
                if fam:
                    busy.add(fam)
                threading.Thread(target=self._execute, args=(rec,), daemon=True).start()

    def _step(self, rec, text, log=True):
        """Krok uruchomienia (activity i ostatnie 30 kroków). log: także wiersz przebiegu („panel”)."""
        text = _short(text, 120)
        if not text:
            return
        with self._lock:
            rec["activity"] = text
            rec["steps"] = (rec["steps"] + [{"t": time.strftime("%H:%M:%S"), "text": text}])[-30:]
        if log:
            self._log(rec, "panel", text)

    def _log(self, rec, kind, text, save=False):
        """Wiersz przebiegu na żywo w rekordzie (pole log, ostatnie LOG_KEEP): agent (wypowiedź), narzędzie, odmowa,
        ty (wiadomość właściciela), panel. Rekord zapisuje się najrzadziej co LOG_SAVE s (bez osobnych plików)."""
        text = str(text or "").strip()
        if not text:
            return
        if len(text) > LOG_TEXT:
            text = text[:LOG_TEXT].rstrip() + "…"
        with self._lock:
            n = int(rec.get("logN") or 0) + 1
            rec["logN"] = n
            rec["log"] = (list(rec.get("log") or []) + [{"n": n, "t": time.strftime("%H:%M:%S"), "k": kind,
                                                         "text": text}])[-LOG_KEEP:]
            priv = self._priv.get(rec["id"])
            now = time.time()
            if priv is not None and (save or now - priv.get("logSaved", 0) >= LOG_SAVE):
                priv["logSaved"] = now
                self._save(rec)

    def _kill(self, proc):
        if proc.poll() is not None:
            return
        try:
            if WINDOWS:
                subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], stdin=subprocess.DEVNULL,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20, **NO_WINDOW)
            else:
                os.killpg(proc.pid, signal.SIGTERM)

                def hard():
                    if proc.poll() is None:
                        try:
                            os.killpg(proc.pid, signal.SIGKILL)
                        except OSError:
                            pass
                timer = threading.Timer(5, hard)
                timer.daemon = True
                timer.start()
        except (OSError, subprocess.SubprocessError):
            try:
                proc.kill()
            except OSError:
                pass

    def _on_timeout(self, rec):
        with self._lock:
            priv = self._priv.get(rec["id"]) or {}
            if rec["state"] != "running":
                return
            priv["timeout"] = True
            proc = priv.get("proc")
        if proc is not None:
            self._kill(proc)

    def _detachable(self, rec):
        """Zadanie i raport PM idą przez pośrednika (przebieg.py): przeżywają restart panelu. PANEL_PRZEBIEG=0
        wyłącza (proces jak dotąd, potok do panelu). Windows: bez pośrednika."""
        return not WINDOWS and rec.get("kind") in ("task", "pm") and \
            (self.env.get("PANEL_PRZEBIEG") or "1").strip() != "0"

    PRIV_KEEP = ("folder", "cwd", "client", "label", "stream", "limit", "task", "git", "resume", "preview", "parts")

    def _site_live_open(self, rec, priv):
        """Zadanie strony: zrzuty z .zrzuty/ (podgląd na żywo) i serwer wersji w budowie dla przeglądarki agenta."""
        with self._lock:
            self._shot_dirs[rec["id"]] = os.path.join(priv["cwd"], ".zrzuty")
        try:
            self.site.live_open(rec["id"], priv)
        except Exception as e:
            log("Podgląd w budowie %s: %s" % (rec["id"], e))

    def _priv_save(self, rec, priv):
        """Dane robocze uruchomienia za pośrednikiem (<id>.przebieg): po restarcie panel podejmuje śledzenie."""
        data = {k: priv[k] for k in self.PRIV_KEEP if k in priv}
        data["t0"] = priv.get("t0") or time.time()
        try:
            self._write_json(os.path.join(self.runs_dir, rec["id"] + ".przebieg"), data)
        except (OSError, TypeError, ValueError) as e:
            log("Dane uruchomienia %s: %s" % (rec["id"], e))

    def _spawn_detached(self, rec, priv, cwd):
        base = os.path.join(self.runs_dir, rec["id"])
        for ext in (".koniec", ".wej"):
            try:
                os.remove(base + ext)
            except OSError:
                pass
        open(base + ".log", "w").close()
        open(base + ".wej", "w").close()
        self._priv_save(rec, priv)
        args = [sys.executable or "python3", RUNNER, self.runs_dir, rec["id"], "--"] + self.as_agent(priv["args"])
        p = subprocess.Popen(args, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, env=child_env(self.env), start_new_session=True)
        with self._lock:
            rec["runner"] = {"pid": p.pid}
            rec["logPos"] = 0
            self._save(rec)
        return Detached(self.runs_dir, rec["id"], p.pid, proc=p)

    def _execute(self, rec):
        priv = self._priv[rec["id"]]
        st = {"result": None, "tail": collections.deque(maxlen=8), "limit": False, "rate": None, "status": None,
              "last": "", "failed": ""}
        out, proc = None, None
        try:
            if priv.get("stop"):
                return self._finish(rec, "stopped", "")
            os.makedirs(self.runs_dir, exist_ok=True)
            detached = self._detachable(rec)
            if not detached:
                out = open(os.path.join(self.runs_dir, rec["id"] + ".log"), "w", encoding="utf-8")
            if WINDOWS:     # własna grupa (zatrzymanie całego drzewa) i brak okna konsoli
                kw = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | NO_WINDOW["creationflags"]}
            else:
                kw = {"start_new_session": True}
            if priv.get("task") and self.worktrees:
                self._worktree_open(rec, priv)
            if priv.get("task"):
                self._parts_open(rec, priv)
            cwd = priv["cwd"]
            if self.agent_user and rec["kind"] in ("check", "plan"):
                cwd = tempfile.gettempdir()     # agent nie musi mieć dostępu do katalogu uruchomień
            if (priv.get("task") or {}).get("site"):
                self._site_live_open(rec, priv)
            try:
                if detached:
                    proc = self._spawn_detached(rec, priv, cwd)
                else:
                    proc = subprocess.Popen(self.as_agent(priv["args"]), cwd=cwd, stdin=subprocess.PIPE,
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.STDOUT, env=child_env(self.env), encoding="utf-8",
                                            errors="replace", bufsize=1, **kw)
            except OSError as e:
                st["tail"].append("Nie udało się uruchomić polecenia %s: %s" % (rec["tool"], e.strerror or e))
                return self._conclude(rec, st, -1)
            with self._lock:
                priv["proc"] = proc
                stop_now = priv.get("stop")
            if stop_now:
                self._kill(proc)
            if priv.get("stream"):
                # zadanie Claude: polecenie jako pierwsza wiadomość stream-json, stdin otwarty do zdarzenia result
                # (live_message); wiadomości wysłane przed startem procesu idą zaraz po poleceniu
                self._stdin_send(priv, priv["prompt"])
                with self._lock:
                    priv["open"] = True
                    early = priv.pop("early", [])
                for text in early:
                    self._stdin_send(priv, text)
            else:
                try:
                    proc.stdin.write(priv["prompt"])
                except (OSError, ValueError):      # proces skończył się, zanim przeczytał polecenie
                    pass
                try:
                    proc.stdin.close()
                except (OSError, ValueError):
                    pass
        except Exception as e:
            st["tail"].append(str(e))
            if proc is None:
                if out:
                    out.close()
                return self._conclude(rec, st, -1)
        self._follow(rec, priv, proc, st, out)

    def _follow(self, rec, priv, proc, st, out=None, limit=None):
        """Czytanie zdarzeń agenta do końca procesu i klasyfikacja końca (także po ponownym podpięciu)."""
        code, timer = None, None
        try:
            timer = threading.Timer(limit or priv.get("limit") or self.timeout, self._on_timeout, [rec])
            timer.daemon = True
            timer.start()
            parse = self._on_codex if rec["tool"] == "codex" else self._on_claude
            for line in proc.stdout:
                if out:
                    out.write(line)
                    out.flush()
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except ValueError:
                    ev = None
                if not isinstance(ev, dict):
                    st["tail"].append(_short(line, 200))
                else:
                    try:
                        with self._lock:
                            plan = list(rec.get("plan") or [])
                            agent_progress.update_plan(plan, ev)
                            agent_progress.task_creates(priv.setdefault("planCreates", {}), plan, ev)
                            if plan or "plan" in rec:
                                rec["plan"] = plan
                        parse(rec, ev, st, priv["cwd"])
                    except Exception:  # nieznany kształt zdarzenia nie może przerwać uruchomienia
                        pass
                if isinstance(proc, Detached):
                    with self._lock:
                        rec["logPos"] = proc.pos
            if self._closing and isinstance(proc, Detached):
                return          # panel kończy pracę: uruchomienie podejmie panel po starcie
            code = proc.wait()
            if self._closing and isinstance(proc, Detached):
                return          # panel kończy pracę: uruchomienie dokończy (albo podejmie) panel po starcie
            if isinstance(proc, Detached) and code in KILLED_CODES and st["result"] is None \
                    and not priv.get("stop") and not priv.get("timeout") and rec.get("kind") == "task":
                return self._recover(rec, priv, "Agent przerwany (kod %s)." % code)
            self._conclude(rec, st, code)
        except Exception as e:
            st["tail"].append(str(e))
            self._conclude(rec, st, -1 if code is None else code)
        finally:
            if timer:
                timer.cancel()
            grace = priv.get("grace")
            if grace:
                grace.cancel()
            with self._lock:
                priv["closed"] = True
            for stream in (out, proc.stdout if proc else None,
                           proc.stdin if proc and not isinstance(proc, Detached) else None):
                if stream:
                    try:
                        stream.close()
                    except (OSError, ValueError):
                        pass

    # ---------- restart panelu: podjęcie śledzenia albo dokończenie (AGENCI.md, „Restart panelu”) ----------
    def _priv_load(self, rid):
        try:
            with open(os.path.join(self.runs_dir, rid + ".przebieg"), encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def _resume_after_restart(self, rec):
        """Rekord w stanie running z poprzedniego życia panelu: pośrednik żyje albo zapisał koniec → panel czyta
        dalej jego przebieg; inaczej zadanie jest przerwane → _recover."""
        rid = rec["id"]
        runner = rec.get("runner") or {}
        priv = self._priv_load(rid) if runner.get("pid") else {}
        base = os.path.join(self.runs_dir, rid)
        alive = bool(runner.get("pid")) and pid_alive(runner["pid"], rid)
        if priv.get("cwd") and (alive or os.path.exists(base + ".koniec")):
            return self._reattach(rec, priv, runner["pid"])
        if rec.get("kind") != "task":
            rec.update(state="stopped", error="Serwer został zatrzymany.", endedAt=now_iso(), activity="")
            self._save(rec)
            return
        priv.setdefault("folder", None)
        with self._lock:
            self._priv[rid] = priv
        self._recover(rec, priv, "Panel uruchomił się ponownie w trakcie pracy agenta.")

    def _replay(self, rec, upto):
        """Stan końca (zdarzenie result, limit) z przebiegu przeczytanego przed restartem panelu."""
        st = {"result": None, "tail": collections.deque(maxlen=8), "limit": False, "rate": None, "status": None,
              "last": "", "failed": ""}
        try:
            with open(os.path.join(self.runs_dir, rec["id"] + ".log"), "rb") as f:
                head = f.read(max(0, int(upto or 0)))
        except OSError:
            return st
        for raw in head.split(b"\n"):
            try:
                ev = json.loads(raw.decode("utf-8", "replace"))
            except ValueError:
                continue
            if not isinstance(ev, dict):
                continue
            kind = ev.get("type")
            if kind == "result":
                st["result"], st["status"] = ev, ev.get("api_error_status") or st["status"]
            elif kind == "rate_limit_event":
                info = ev.get("rate_limit_info") or {}
                st["rate"] = info
                st["limit"] = st["limit"] or str(info.get("status") or "").lower() in DENIED
            elif kind in ("turn.completed",):
                st["result"] = {"is_error": False}
            elif kind == "item.completed" and (ev.get("item") or {}).get("type") in ("agent_message",):
                st["last"] = str((ev.get("item") or {}).get("text") or "")
        return st

    def _reattach(self, rec, priv, pid):
        rid = rec["id"]
        pos = int(rec.get("logPos") or 0)
        st = self._replay(rec, pos)
        proc = Detached(self.runs_dir, rid, pid, pos=pos)
        priv.update(proc=proc, reattached=True)
        if priv.get("stream"):
            priv["open"] = st["result"] is None
            priv["ended"] = st["result"] is not None
        with self._lock:
            self._priv[rid] = priv
            rec["activity"] = "Panel uruchomił się ponownie: śledzę pracę agenta dalej"
            self._save(rec)
        if (priv.get("task") or {}).get("site"):
            self._site_live_open(rec, priv)
        self._log(rec, "panel", "Panel uruchomił się ponownie; agent pracował dalej.")
        left = self.timeout
        if priv.get("t0"):
            left = max(30, int((priv.get("limit") or self.timeout) - (time.time() - float(priv["t0"]))))
        threading.Thread(target=self._follow, args=(rec, priv, proc, st, None, left), daemon=True).start()

    def _agent_commits(self, rec, git):
        """Commity tej pracy na gałęzi (od startCommit, bez commita panelu z końca tego uruchomienia)."""
        start = rec.get("startCommit") or git.get("startCommit") or git["baseCommit"]
        branch = rec.get("branch") or git["branch"]
        code, out, _ = git_run(git["top"], ["log", "--format=%H%x00%B%x01", "%s..%s" % (start, branch)], timeout=30)
        if code != 0:
            return 0
        mark = "Uruchomienie panelu %s " % rec["id"]
        return sum(1 for item in out.split("\x01") if item.strip() and mark not in item)

    def _recover(self, rec, priv, reason):
        """Zadanie przerwane (restart panelu, zabity proces): zatwierdzona praca na gałęzi → koniec jak zwykle
        (stan done); bez commita → zatrzymanie i ponowne uruchomienie od gałęzi z dopiskiem w `poprawka:`."""
        git = priv.get("git") or self._worktree_info(rec)
        if git and not git.get("startCommit") and rec.get("startCommit"):
            git["startCommit"] = rec["startCommit"]
        wt = git and os.path.isdir(git["worktree"])
        if wt:
            code, cur, _ = git_run(git["worktree"], ["symbolic-ref", "--short", "-q", "HEAD"], timeout=15)
            if code == 0 and cur.strip():
                rec["branch"] = cur.strip()
        commits = self._agent_commits(rec, git) if git else 0
        with self._lock:
            priv["git"] = git
            self._priv[rec["id"]] = priv
            rec["state"] = "running"
        if commits:
            rec["recovered"] = "commit"
            self._step(rec, "%s Na gałęzi %s jest zatwierdzona praca (%d): kończę zadanie jak po zwykłym końcu."
                       % (reason, rec.get("branch") or git["branch"], commits))
            said = next((x["text"] for x in reversed(rec.get("log") or []) if x.get("k") == "agent"), "")
            return self._finish(rec, "done", "", result=_short(said, 4000))
        rec["recovered"] = "restart"
        n = int(rec.get("recoverN") or 0)
        again = n < RECOVER_MAX
        self._finish(rec, "stopped", _short(reason + (" Bez zatwierdzonej pracy: zadanie uruchomi się ponownie od "
                                                      "swojej gałęzi." if again else
                                                      " Wznowienia się powtarzają: uruchom zadanie ręcznie."), 300))
        if again:
            threading.Thread(target=self._relaunch_recovered, args=(dict(rec), n + 1), daemon=True).start()

    RECOVER_NOTE = ("Poprzednie uruchomienie przerwał restart panelu (%s). Twoja dotychczasowa praca jest na gałęzi "
                    "%s: sprawdź ją (git log, git diff) i dokończ zadanie.")

    def _relaunch_recovered(self, rec, n, wait=3):
        """Ponowne uruchomienie zadania przerwanego bez commita: dopisek w `poprawka:`, start od gałęzi zadania."""
        time.sleep(wait)
        task, data, index = self._find_task(key=(rec["project"], rec["file"], rec["title"]))
        if not task or task["state"] != "todo" or task["project"] not in index:
            return
        note = self.RECOVER_NOTE % ((rec.get("endedAt") or now_iso())[:16].replace("T", " "),
                                     rec.get("branch") or "zadania")
        if self._append_fix(task, index[task["project"]], note):
            task, data, index = self._find_task(key=(rec["project"], rec["file"], rec["title"]))
        if not task:
            return
        code, err, extra = self.run_task(task["id"], task["title"], auto=bool(rec.get("auto")))
        if code == 200:
            with self._lock:
                new = self._runs.get(extra["id"])
                if new is not None:
                    new["recoverN"] = n
                    new["recoveredFrom"] = rec["id"]
                    self._save(new)
        else:
            log("Wznowienie %s: %s" % (rec["id"], err))

    def _grace_end(self, rec, priv):
        """Po zdarzeniu result: wiadomości, których agent nie zdążył odczytać (brak nowej tury w GRACE s), zostają
        poleceniem na ponowne uruchomienie; wejście się zamyka i CLI kończy pracę."""
        with self._lock:
            if not priv.get("ended"):
                return
            unseen = [m for m in priv.get("msgs") or [] if not m["seen"]]
            for m in unseen:
                m["seen"] = True
            if unseen:
                priv.setdefault("after", []).extend({"text": m["text"], "pins": None} for m in unseen)
        if unseen:
            self._log(rec, "panel", "Agent skończył przed odczytaniem wiadomości: zapisana jako poprawka, "
                                    "zadanie uruchomi się ponownie.")
        self._stdin_close(priv)

    GRACE = 20                  # s: tyle panel czeka po result na nową turę z nieodczytaną wiadomością

    def _on_claude(self, rec, ev, st, cwd):
        kind = ev.get("type")
        priv = self._priv.get(rec["id"]) or {}
        if priv.get("ended") and kind in ("assistant", "user", "stream_event"):
            with self._lock:                    # nowa tura po result: agent czyta wiadomość wysłaną pod koniec
                priv["ended"] = False
                grace = priv.pop("grace", None)
            if grace:
                grace.cancel()
        if kind == "system":
            if ev.get("subtype") == "init":
                with self._lock:
                    rec["model"] = str(ev.get("model") or "")
                    rec["keySource"] = str(ev.get("apiKeySource") or "")
            elif ev.get("subtype") == "api_retry":
                st["status"] = ev.get("error_status") or st["status"]
                self._step(rec, "Ponawiam połączenie (%s/%s)" % (ev.get("attempt", "?"), ev.get("max_retries", "?")))
        elif kind == "assistant":
            msg = ev.get("message") or {}
            for block in msg.get("content") or []:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_use":
                    desc = describe_tool(block.get("name", "?"), block.get("input"), cwd)
                    self._step(rec, desc, log=False)
                    self._log(rec, "narzedzie", desc)
                    with self._lock:
                        tools = priv.setdefault("tools", {})
                        if len(tools) < 500:
                            tools[str(block.get("id") or "")] = desc
                elif block.get("type") == "text" and str(block.get("text") or "").strip():
                    self._step(rec, str(block["text"]).strip().split("\n")[0], log=False)
                    self._log(rec, "agent", block["text"])
            usage = msg.get("usage") or {}
            with self._lock:
                rec["tokensOut"] += int(usage.get("output_tokens") or 0)
                for m in priv.get("msgs") or []:    # odpowiedź po wyniku narzędzia: agent widział wiadomość
                    if m["tr"]:
                        m["seen"] = True
        elif kind == "user":
            msg = ev.get("message") or {}
            blocks = msg.get("content") if isinstance(msg.get("content"), list) else []
            for block in blocks:
                if not isinstance(block, dict) or block.get("type") != "tool_result":
                    continue
                with self._lock:
                    for m in priv.get("msgs") or []:
                        m["tr"] = True
                body = block.get("content")
                if isinstance(body, list):
                    body = " ".join(str(x.get("text") or "") for x in body if isinstance(x, dict))
                body = str(body or "")
                if block.get("is_error") and DENY_RE.search(body):
                    with self._lock:
                        desc = (priv.get("tools") or {}).get(str(block.get("tool_use_id") or ""), "")
                        priv.setdefault("denied", set()).add(desc)
                    self._log(rec, "odmowa", desc or _short(body, 200))
        elif kind == "rate_limit_event":
            info = ev.get("rate_limit_info") or {}
            st["rate"] = info
            if str(info.get("status") or "").lower() in DENIED:
                st["limit"] = True
            self._watch_budget(rec, info)
        elif kind == "result":
            st["result"] = ev
            usage = ev.get("usage") or {}
            denials = []
            for d in ev.get("permission_denials") or []:
                if isinstance(d, dict):
                    denials.append(describe_tool(d.get("tool_name", "?"), d.get("tool_input"), cwd))
            with self._lock:
                rec["turns"] = int(ev.get("num_turns") or 0)
                rec["costUsd"] = round(float(ev.get("total_cost_usd") or 0), 4)
                rec["tokensIn"] = int(usage.get("input_tokens") or 0) + int(usage.get("cache_creation_input_tokens") or 0)
                rec["tokensOut"] = int(usage.get("output_tokens") or 0)
                rec["denials"] = denials[:10]
                fresh = [d for d in denials if d not in (priv.get("denied") or set())]
            for d in fresh[:10]:
                self._log(rec, "odmowa", d)
            st["status"] = ev.get("api_error_status") or st["status"]
            if priv.get("stream"):
                # koniec tury: panel zamyka wejście (CLI kończy pracę); nieodczytana wiadomość dostaje GRACE s
                with self._lock:
                    priv["ended"] = True
                    unseen = any(not m["seen"] for m in priv.get("msgs") or [])
                    if unseen:
                        timer = threading.Timer(self.GRACE, self._grace_end, [rec, priv])
                        timer.daemon = True
                        priv["grace"] = timer
                if unseen:
                    timer.start()
                else:
                    self._stdin_close(priv)

    def _say(self, rec, text):
        """Wypowiedź agenta: pierwszy wiersz jako krok, pełny tekst w przebiegu."""
        self._step(rec, str(text or "").strip().split("\n")[0], log=False)
        self._log(rec, "agent", text)

    def _did(self, rec, desc):
        """Wywołanie narzędzia: krok i wiersz przebiegu (krótki argument)."""
        self._step(rec, desc, log=False)
        self._log(rec, "narzedzie", _short(desc, 120))

    def _on_codex(self, rec, ev, st, cwd):
        """Strumień `codex exec --json`: nowy układ (item.*, turn.*) i starszy (msg)."""
        kind = ev.get("type")
        now = time.time()
        windows = agent_progress.limit_windows(ev, "codex", agent_progress.read_time(ev.get("timestamp"), now))
        priv = self._priv.get(rec["id"]) or {}
        thread = priv.get("thread")
        if not windows and thread and (kind in ("turn.completed", "turn.failed") or
                                       now - priv.get("limitCheckedAt", 0) >= 5):
            priv["limitCheckedAt"] = now
            windows = agent_progress.codex_session_windows(grafiki.codex_home(self.env, self.agent_user), thread,
                                                           priv.get("t0") or now)
        self._record_limits("codex", windows, rec)
        msg = ev.get("msg") if isinstance(ev.get("msg"), dict) else None
        if msg:                                             # starszy układ
            kind, ev = msg.get("type"), msg
            if kind == "agent_message":
                st["last"] = str(ev.get("message") or "")
                self._say(rec, st["last"])
            elif kind == "exec_command_begin":
                cmd = ev.get("command")
                self._did(rec, "Bash: %s" % (" ".join(cmd) if isinstance(cmd, list) else cmd))
            elif kind == "task_complete":
                st["last"] = str(ev.get("last_agent_message") or st["last"])
                st["result"] = {"is_error": False}
            elif kind == "token_count":
                info = (ev.get("info") or {}).get("total_token_usage") or ev
                with self._lock:
                    rec["tokensIn"] = int(info.get("input_tokens") or 0)
                    rec["tokensOut"] = int(info.get("output_tokens") or 0)
            elif kind == "error":
                st["failed"] = str(ev.get("message") or "")
            return
        if kind in ("item.started", "item.completed"):
            item = ev.get("item") or {}
            what = item.get("type")
            if what == "agent_message" and kind == "item.completed":
                st["last"] = str(item.get("text") or "")
                self._say(rec, st["last"])
            elif what == "command_execution" and kind == "item.started":
                self._did(rec, "Bash: %s" % item.get("command", ""))
            elif what == "file_change" and kind == "item.completed":
                for ch in item.get("changes") or []:
                    if isinstance(ch, dict) and ch.get("path"):
                        self._did(rec, describe_tool("Edit", {"file_path": ch["path"]}, cwd))
            elif what == "error":
                st["failed"] = str(item.get("message") or item.get("text") or "")
        elif kind == "turn.completed":
            usage = ev.get("usage") or {}
            with self._lock:
                rec["turns"] += 1
                rec["tokensIn"] += int(usage.get("input_tokens") or 0)
                rec["tokensOut"] += int(usage.get("output_tokens") or 0)
            st["result"] = {"is_error": False}
        elif kind == "turn.failed":
            st["failed"] = str((ev.get("error") or {}).get("message") or "Tura nie powiodła się.")
        elif kind == "error":
            st["failed"] = str(ev.get("message") or "")
        elif kind == "thread.started" or kind == "session.created":
            with self._lock:
                rec["model"] = str(ev.get("model") or rec["model"])
                thread = str(ev.get("thread_id") or ev.get("session_id") or "")
                if thread and re.match(r"^[\w.-]{1,100}$", thread):
                    (self._priv.get(rec["id"]) or {})["thread"] = thread

    def _record_limits(self, tool, windows, rec=None):
        if not windows:
            return
        target = self._usage if tool == "claude" else self._codex_usage
        changed = False
        with self._lock:
            for key, at, reset in (("five", "at", "resetsAt"), ("seven", "sevenAt", "sevenReset")):
                if key not in windows:
                    continue
                amount, stamp, renewal = windows[key]
                if stamp >= target.get(at, 0) and (amount, stamp, renewal) != (
                        target.get(key), target.get(at), target.get(reset)):
                    target.update({key: amount, at: stamp, reset: renewal})
                    changed = True
                if key == "five" and rec is not None and stamp >= (rec.get("limitReadAt") or 0):
                    if rec.get("limitStart") is None or amount < rec["limitStart"] or (
                            renewal and rec.get("limitReset") != renewal):
                        rec["limitStart"] = amount
                    rec.update(limitNow=amount, limitReset=renewal, limitReadAt=stamp)
            if changed:
                self._save_state()

    def _read_external_limits(self):
        with self._limit_reader_lock:
            orders = self.orders.snapshot()
            for _, data, _ in self.orders.cache.values():
                for tool, windows in (data.get("limits") or {}).items():
                    self._record_limits(tool, windows)
            now = time.monotonic()
            if now >= self._session_limits_at:
                self._session_limits_at = now + 15
                home = grafiki.codex_home(self.env, "agent" if self.machine == "cloud" else self.agent_user)
                if home:
                    self._record_limits("codex", agent_progress.latest_session_windows(home))
        return orders

    def _claude_limit_event(self, event):
        self._record_limits("claude", agent_progress.limit_windows(event, "claude", time.time()))

    def _watch_budget(self, rec, info):
        """Zapis limitu i bezpiecznik pojedynczego uruchomienia Claude."""
        windows = agent_progress.limit_windows({"rate_limit_info": info}, "claude", time.time())
        self._record_limits("claude", windows, rec)
        if "five" not in windows:
            return
        with self._lock:
            # kilka uruchomień naraz: zużycie okna to suma ich pracy; próg rośnie z liczbą pracujących,
            # a zatrzymanie dostaje uruchomienie pracujące najdłużej (największy przyrost od startu)
            now = rec["limitNow"]
            running = [r for r in self._runs.values() if r["state"] == "running" and r.get("tool") == "claude"
                       and isinstance(r.get("limitStart"), (int, float))]
            if rec not in running:
                running.append(rec)
            deltas = {r["id"]: now - r["limitStart"] for r in running}
            victim = max(running, key=lambda r: deltas[r["id"]])
            used = deltas[victim["id"]]
            budget = self.run_budget * len(running)
            priv = self._priv.setdefault(victim["id"], {})
            if used < budget or priv.get("stop"):
                return
            if len(running) > 1:
                priv["budget"] = ("Zatrzymano: %d uruchomienia naraz zużyły razem %d%% limitu 5 godzin (próg %d%%); "
                                  "to pracowało najdłużej." % (len(running), round(used * 100), round(budget * 100)))
            else:
                priv["budget"] = ("Zatrzymano: to uruchomienie zużyło już %d%% limitu 5 godzin (próg %d%%). "
                                  "Zwykłe zadanie zużywa kilka procent; sprawdź, czym agent się zajmował."
                                  % (round(used * 100), round(self.run_budget * 100)))
        self._step(victim, "Bezpiecznik: zużyto %d%% limitu 5 godzin, zatrzymuję" % round(used * 100))
        self.stop(victim["id"])

    def usage_state(self):
        now = time.time()
        data = {"budget": self.run_budget, "reserve": self.auto_reserve}
        with self._lock:
            for windows, prefix in ((self._usage, ""), (self._codex_usage, "codex")):
                for key, at, reset, age in (("five", "at", "resetsAt", 5), ("seven", "sevenAt", "sevenReset", 168)):
                    name = prefix + key.capitalize() if prefix else key
                    stamp, renewal = windows.get(at, 0), windows.get(reset)
                    expired = bool(renewal and renewal <= now)
                    data[name] = 0 if expired else windows.get(key) if stamp and (renewal or now < stamp + age * 3600) else None
                    data[name + "New"] = expired
                    data[name + "At"] = now_iso(datetime.datetime.fromtimestamp(stamp)) if stamp else ""
        data["at"] = data["fiveAt"]
        return data

    def _conclude(self, rec, st, code):
        """Klasyfikacja końca: stopped → timeout → login → limit → error → done."""
        priv = self._priv.get(rec["id"]) or {}
        res = st["result"] if isinstance(st["result"], dict) else None
        text = str(res.get("result") or "") if res and rec["tool"] == "claude" else st["last"]
        failed = bool(st["failed"]) or res is None or bool(res.get("is_error")) or code not in (0, None)
        blob = " ".join([text, st["failed"]] + list(st["tail"]))
        status = str(st["status"] or "")
        if priv.get("stop"):
            return self._finish(rec, "stopped", priv.get("budget") or "")
        if priv.get("timeout"):
            return self._finish(rec, "timeout", "Przekroczony czas: %d min." % max(1, (priv.get("limit") or self.timeout) // 60))
        if failed and (status == "401" or LOGIN_RE.search(blob)):
            hint = self.login_cmd(rec["tool"], self.tool_path(rec["tool"]))
            return self._finish(rec, "login", "Wymaga logowania: %s" % hint)
        if failed and (status == "429" or st["limit"] or LIMIT_RE.search(blob)):
            until = self._limit_until(blob, st["rate"])
            return self._finish(rec, "limit", "Limit subskrypcji. Odnowienie o %s." % until[11:16], limit_until=until)
        if failed:
            detail = st["failed"] or (text if res and res.get("is_error") else "") or " ".join(st["tail"]) \
                or "Polecenie zakończyło się kodem %s." % code
            return self._finish(rec, "error", _short(detail, 300))
        return self._finish(rec, "done", "", result=text.strip() if rec["kind"] == "pm" else text.strip()[:4000])

    @staticmethod
    def _limit_until(blob, rate):
        now = time.time()
        when = None
        m = re.search(r"\|(\d{10})\b", blob)
        if m:
            when = int(m.group(1))
        elif isinstance(rate, dict):
            try:
                when = float(rate.get("resetsAt"))
                when = when / 1000 if when > 1e12 else when
            except (TypeError, ValueError):
                when = None
        if not when or when <= now:
            when = now + 3600
        return now_iso(datetime.datetime.fromtimestamp(when))

    def _finish(self, rec, state, error, result="", limit_until=None):
        with self._lock:
            priv = self._priv.setdefault(rec["id"], {})
            if rec["state"] not in LIVE or priv.get("finishing"):
                return
            priv["finishing"] = True
        if rec["kind"] == "task":                      # wiersz zadania przed ogłoszeniem stanu końcowego
            self._close_task(rec, state, priv.get("git"), priv.get("parts"))
        if rec["kind"] == "task" and state == "done":
            try:
                task, _, _ = self._find_task(key=(rec["project"], rec["file"], rec["title"]))
                rec["outcome"] = task_outcome(task)
            except (OSError, ValueError):
                rec["outcome"] = "unknown"
        if rec["kind"] == "grafika":
            state, error, result = self._graphic_done(rec, priv, state, error, result)
        if rec["kind"] == "pm" and state == "done":
            result = self._pm_launches(result, priv.get("pmAllowed") or set())[:6000]
        if rec["kind"] == "plan" and state == "done":
            body, plan = self.parse_plan(result, (self._priv.get(rec["id"]) or {}).get("cands") or {})
            result = body[:4000]
            with self._lock:
                rec["plan"] = plan
                if plan is None:
                    state, error = "error", "PM nie zwrócił planu w oczekiwanym formacie."
        with self._lock:
            priv = self._priv.pop(rec["id"], {})
            t0 = priv.get("t0")
            rec.update(state=state, error=error, result=result, endedAt=now_iso(), activity="",
                       durationMs=int((time.time() - t0) * 1000) if t0 else None)
            if rec["tool"] == "claude":
                if state == "login":
                    self._state["needsLogin"] = True
                elif state == "done":
                    self._state["needsLogin"] = False
            if state == "limit" and rec["tool"] == "claude":
                self._state["limitUntil"] = limit_until
            elif state == "done" and rec["tool"] == "claude":
                self._state["limitUntil"] = None
            self._save_state()
            self._save(rec)
        after = list(priv.get("after") or [])
        if priv.get("grace"):                 # koniec w czasie oczekiwania na nową turę: nieodczytane wiadomości
            priv["grace"].cancel()
            after += [{"text": m["text"], "pins": None} for m in priv.get("msgs") or [] if not m["seen"]]
        restart = bool(priv.get("restart")) and state == "stopped"
        if state != "stopped" and rec["kind"] != "check":
            self._notify(rec, priv)
        self.site.live_close(rec["id"])
        try:
            self.site.after_run(dict(rec))
        except Exception as e:
            log("Podgląd strony po uruchomieniu: %s" % e)
        if rec["kind"] == "task" and (restart or (after and state != "stopped")):     # po after_run (_finishing)
            threading.Thread(target=self._relaunch, args=(dict(rec), after, restart), daemon=True).start()
        self._login_alert()
        self.refresh_tools(force=True)
        self._pump()

    def _close_task(self, rec, state, git=None, parts=None):
        """Koniec zadania: wiersz zadania, gałąź uruchomienia (commit, changes, katalog roboczy), materiał dla
        następników. Błąd jednego kroku nie zatrzymuje pozostałych."""
        try:
            self._settle_task(rec, state)
        except Exception as e:
            log("Zadanie po uruchomieniu: %s" % e)
        try:
            if git:
                self._worktree_close(rec, git)
        except Exception as e:
            log("Gałąź uruchomienia %s: %s" % (rec["id"], e))
        try:
            self._parts_close(rec, parts)
        except Exception as e:
            log("Części projektu %s: %s" % (rec["id"], e))
        if state == "done":
            try:
                self._pass_materials(rec, dict(git, branch=rec.get("branch") or git["branch"]) if git else None)
            except Exception as e:
                log("Materiał z wyniku: %s" % e)
            try:
                self._save_version(rec)
            except Exception:       # wersja to dodatek: błąd nie zmienia zakończenia uruchomienia
                pass

    def _settle_task(self, rec, state):
        """Po zakończeniu: wiersz dalej [~] → przy niepowodzeniu wraca [ ], przy sukcesie dostaje wymaga: odbiór."""
        _, index = self.load_projects(resolve=False)
        folder = index.get(rec["project"])
        if not folder:
            return
        parse = self.projekt.parse_task
        with self.write_lock:
            text = self.projekt.read(os.path.join(folder, rec["file"]))
            if text is None:
                return
            lines = text.split("\n")
            rows = [(i + 1, parse(line.rstrip("\r"))) for i, line in enumerate(lines)]
            rows = [(no, t) for no, t in rows if t and t["title"] == rec["title"] and t["state"] == "doing"]
            if not rows:
                return
            try:
                want = int(str(rec.get("taskId", "")).split("|")[2])
            except (IndexError, ValueError):
                want = 0
            no, t = next((r for r in rows if r[0] == want), rows[0])
            if state != "done":
                changes = {"state": "todo"}
            elif not t["needsYou"]:
                changes = {"needsYou": "odbiór"}
            else:
                return
            try:
                self.projekt.update_task(folder, rec["file"], no, rec["title"], changes)
            except (ValueError, OSError):
                pass

    def _notify(self, rec, priv=None):
        """Powiadomienie ntfy po zakończeniu. W projektach klienckich bez tytułu zadania."""
        if not self.ntfy_url:
            return
        priv = priv or {}
        state = STATE_LABEL.get(rec["state"], rec["state"])
        if rec["kind"] == "task" and priv.get("client"):
            body = "Zadanie w projekcie %s: %s" % (priv.get("label") or rec["projectName"] or rec["project"], state)
        else:
            where = " (%s)" % rec["projectName"] if rec["projectName"] else ""
            body = "%s%s: %s" % (rec["title"], where, state)
        self._send_ntfy(body, notify_link(rec))

    def _send_ntfy(self, body, link=""):
        """Powiadomienie ntfy; link (np. "#asystent?z=<id zadania>") otwiera się po stuknięciu (nagłówek Click),
        gdy PANEL_PUBLIC_URL jest ustawiony."""
        if not self.ntfy_url:
            return
        data = body.encode("utf-8")
        headers = {"Content-Type": "text/plain; charset=utf-8"}
        click = click_url(link)
        if click:
            headers["Click"] = click

        def send():
            try:
                req = urllib.request.Request(self.ntfy_url, data=data, method="POST", headers=headers)
                urllib.request.urlopen(req, timeout=5).close()
            except Exception:
                pass
        threading.Thread(target=send, daemon=True).start()

    def _login_alert(self):
        """Powiadomienie, gdy Claude zaczyna wymagać logowania: raz na zmianę stanu.

        Wymaga logowania: needsLogin po uruchomieniu albo odczyt narzędzi (claude jest, ale niezalogowany)."""
        with self._lock:
            claude = self._tools.get("claude") or {}
            needs = bool(self._state["needsLogin"]) or (self._tools_at > 0 and claude.get("found") is True
                                                        and not claude.get("loggedIn"))
            send = needs and not self._login_sent
            self._login_sent = needs
        if send:
            self._send_ntfy("Claude wymaga logowania. Zaloguj się w panelu: Agenci, Zaloguj.", "#agenci")

    # ---------- Automat ----------
    def _auto_candidates(self, data, index, now):
        if data["projectsSource"] != "registry":
            return
        today = now.date().isoformat()
        night = now.hour >= 22 or now.hour < 6
        live = self._live_keys()
        tools = {tool: self.tool_found(tool) for tool in ("claude", "codex")}
        projects = {p["id"]: p for p in data["projects"]}
        five = self.usage_state()["five"]
        with self._lock:
            login = self._state["needsLogin"]
            done_today = {(r["project"], r["file"], r["title"], r.get("fix") or "") for r in self._runs.values()
                          if r["kind"] == "task" and (r.get("queuedAt") or "")[:10] == today}
        paused = login or self.limit_until() or (five is not None and five >= self.auto_reserve)
        for t in data["tasks"]:
            if t["state"] != "todo" or t["executor"] not in AGENT_EXECUTORS:
                continue
            if t["machine"] != self.machine and not (not t["machine"] and self.default_node):
                continue
            if not t["date"] or t["date"][:10] > today:
                continue
            if (t["slot"] == "noc" and not night) or (t["slot"] == "dzień" and night):
                continue
            key = (t["project"], t["file"], t["title"], str((t.get("detail") or {}).get("fix") or "")[:1000])
            project = projects.get(t["project"], {})
            if key not in done_today and not run_block(t, "registry", live, tools) and self.auto_task_ready(
                    t, project, index.get(t["project"]), paused):
                yield t, project

    def next_tasks(self, data, index):
        with self._lock:
            if not self._state["automat"]:
                return []
        return [{"title": t["title"], "taskId": t["id"], "projectName": p.get("name", t["project"]),
                 "state": "queued", "kind": "task", "category": self._task_category(t, p, index.get(t["project"])),
                 "tool": self.choose_task_tool(t, p, index.get(t["project"]))[0]}
                for t, p in self._auto_candidates(data, index, datetime.datetime.now())][:20]

    def tick(self, now=None):
        """Jeden obieg Automatu. Zwraca listę id nowych uruchomień."""
        started = []
        self._pump()                            # kolejka po końcu oczekiwania wdrożenia
        now = now or datetime.datetime.now()
        today = now.date().isoformat()
        with self._lock:
            if not self._state["automat"]:
                return started
            login = self._state["needsLogin"]
            pm_today = any(r["kind"] == "pm" and (r["auto"] or r["state"] in LIVE or r["state"] == "done")
                           and (r.get("queuedAt") or "")[:10] == today for r in self._runs.values())
            free = self.max_parallel - sum(1 for r in self._runs.values() if r["state"] in LIVE)
        self._read_external_limits()
        five = self.usage_state()["five"]
        paused = login or self.limit_until() or (five is not None and five >= self.auto_reserve)
        if free <= 0:
            return started
        if not paused and now.hour >= self.pm_hour and not pm_today and not os.path.exists(
                os.path.join(self.notes_dir, today + ".md")):
            code, _, extra = self.run_pm(auto=True)
            if code == 200:
                started.append(extra["id"])
                free -= 1
        if free <= 0:
            return started
        data, index = self.load_projects()
        if data["projectsSource"] != "registry":
            return started
        if not paused:
            added = self._plan_posts(data, index, now.date())
            added = self._plan_rhythm(data, index, now.date()) or added
            added = self._plan_scripts(data, index, now.date()) or added
            if added:
                data, index = self.load_projects()
        projects = {p["id"]: p for p in data["projects"]}
        for t, _ in self._auto_candidates(data, index, now):
            fam = (projects.get(t["project"]) or {}).get("partOf") or t["project"]
            with self._lock:
                if any(self._family(r) == fam and r["state"] in LIVE and r.get("kind") == "task"
                       for r in self._runs.values()):
                    continue                    # jedno uruchomienie na projekt: następne zadanie w kolejnym obiegu
            code, _, extra = self.run_task(t["id"], t["title"], auto=True)
            if code == 200:
                started.append(extra["id"])
                free -= 1
                if free <= 0:
                    break
        return started


def projekt_pin_line(pin):
    """Wiersz znacznika jak w ZADANIA.md (bez importu modułu projekt w funkcji statycznej)."""
    parts = [pin["file"]]
    if pin.get("t") is not None:
        parts.append("%d:%02d" % divmod(int(pin["t"]), 60))
    if pin.get("x") is not None and pin.get("y") is not None:
        pct = lambda v: ("%.1f" % float(v)).rstrip("0").rstrip(".")     # noqa: E731
        parts += ["%s%% od lewej" % pct(pin["x"]), "%s%% od góry" % pct(pin["y"])]
    return ("- znacznik %s (%s): %s" % (pin.get("n") or "", ", ".join(parts), pin.get("note") or "")).rstrip()


def with_answers(task, tasks):
    """Szczegóły zadania z odpowiedziami właściciela z formularzy poprzedników (`po:`, pole `pyta:`)."""
    d = dict(task.get("detail") or {})
    ids = {w.get("id") for w in task.get("waitingFor") or [] if isinstance(w, dict) and w.get("done") and w.get("id")}
    extra = [a for t in tasks if t.get("id") in ids for a in (t.get("detail") or {}).get("answers") or []]
    if extra:
        d["answers"] = list(d.get("answers") or []) + extra
    return d


POST_TASK = "Przygotować post na "
FIX_POST_TASK = "Popraw post na "   # zadanie z „Co poprawić” w poście (server.fix_post)
FILM_PY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "film.py")   # sprawdzanie scenariusza
STUDIO_DIR = "studio"               # studio filmów obok KARTA.md (film.py): marka.json i szablony/
STUDIO_TASK = "Zmień studio filmów: "   # zadanie z „Studio filmów” w Marketingu (server.studio_request)
# Reguły filmu dla zadań postów: scenariusz z szablonu studia, nie od zera.
FILM_RULES = [
    "- Film do posta: najpierw sprawdź studio/ obok KARTA.md (studio/szablony/*.json i studio/marka.json). Gdy jest "
    "pasujący szablon, zapisz scenariusz.json jako {\"szablon\": \"<nazwa>\", \"parametry\": {…}}: podaj parametry "
    "z \"wymagane\" w szablonie (treść tego posta) i te, które zmieniasz (tekst albo liczba, w \"limity\" szablonu); "
    "kroków nie przepisuj i nie dodawaj innych kluczy obok \"szablon\" (wolno tylko plansza_startowa i "
    "plansza_koncowa). Film bez strony (problem, rozwiązanie, korzyść) to objaśnienie: {\"typ\": \"objasnienie\", "
    "\"plansze\": [{\"tekst\": …, \"podpis\": …}]} albo szablon objaśnienia: 1–12 plansz, tekst do 90 znaków "
    "(jedno słowo kluczowe w *gwiazdkach* dostaje kolor akcentu), podpis do 70 znaków, czas 1–12 s (bez czasu "
    "panel liczy go sam: 1,2 s + 1 s na 15 znaków), opcjonalnie \"obraz\": plik .png/.jpg z folderu posta albo "
    "studio/obrazy/. Pokaz może mieć przed i po nagraniu strony plansze objaśnienia: \"plansze_przed\" i "
    "\"plansze_po\" (po 1–4 plansze), np. 2 plansze z problemem, potem pokaz.",
    "- Dobór filmu: według sekcji „Filmy” w STYL.md projektu; gdy jej nie ma: post z kanałem reels zawsze z filmem, "
    "na zmianę pokaz i objaśnienie, nie ten sam szablon dwa razy z rzędu (sprawdź scenariusz.json poprzednich "
    "postów w posty/). W każdym filmie własna treść: plansze objaśnienia piszesz pod ten post (nie zostawiasz "
    "przykładowych tekstów szablonu), w pokazie inny mebel niż w poprzednich filmach. film.py sprawdz ostrzega "
    "o powtórkach; ostrzeżenia poprawiasz przed oddaniem.",
    "- Dodatkowa plansza w filmie z szablonu objaśnienia (uwaga „Dodaj planszę”): szablon nie przyjmuje nowych "
    "plansz, więc zapisz scenariusz.json jako {\"typ\": \"objasnienie\", \"plansze\": [...]} z planszami "
    "z szablonu (treść tego posta, po podstawieniu parametrów) i nową planszą w podanym miejscu; "
    "plansza_startowa i plansza_koncowa jak w szablonie. Tak samo przy innych zmianach układu, których nie da się "
    "zrobić parametrem.",
    "- Pierwsza sekunda to hak posta: najlepiej do ok. 40 znaków (widz czyta go w 3 s), pierwsza plansza "
    "objaśnienia bez podpisu, objaśnienie do 30 s. W szablonie z planszą startową podaj hak w parametrze szablonu; w scenariuszu "
    "bez szablonu daj \"plansza_startowa\": {\"tytul\": \"<hak>\"} (hak nie dostaje podtytułu ani adresu marki, "
    "czas liczy panel) albo false, gdy pierwsza plansza objaśnienia jest hakiem. Plansze marki (start i koniec, "
    "z wezwaniem do działania) dokleja panel; nie powtarzaj ich treści w planszach ani w ostatnim napisie pokazu. "
    "Pokaz nagrywa tylko strony https z marka.json (pole strony). Przed oddaniem sprawdź scenariusz: python3 %s "
    "sprawdz <folder posta> (błędy i ostrzeżenia, długość filmu)." % FILM_PY,
    "- Poprawka jednego posta zmienia tylko scenariusz.json tego posta: parametry albo plansza_startowa / "
    "plansza_koncowa jako obiekt (np. inne wezwanie na końcu tylko w tym filmie: \"plansza_koncowa\": "
    "{\"podtytul\": \"…\"}). Szablonu (studio/szablony/) i marki (studio/marka.json) nie zmieniasz: zmiana nagrywa "
    "od nowa filmy wszystkich nadchodzących postów projektu. Zmieniasz je tylko w zadaniu „%s…” albo gdy uwaga "
    "właściciela mówi wprost „zmień dla wszystkich filmów”." % STUDIO_TASK,
]
STUDIO_RULES = [
    "- To zadanie zmienia studio filmów projektu (wszystkie filmy): studio/marka.json albo nowy szablon "
    "studio/szablony/<nazwa>.json. Szablon ma pola \"tytul\" (czytelna nazwa po polsku), \"opis\" (jedno zdanie: "
    "kiedy go użyć), \"parametry\" (wartości przykładowe), \"etykiety\", \"wymagane\" (treść posta, której nie wolno "
    "wziąć z przykładu) i opcjonalnie \"limity\" ({parametr: {\"max\": znaki, \"opcje\": [...]}}). Nowy szablon ma "
    "mieć inny układ niż istniejące, \"dla_wlasciciela\" (jedno zdanie dla właściciela: co widz zobaczy i do jakich "
    "postów) i limit haka 60 znaków. Szablonu, którego używają nadchodzące posty (scenariusz.json z tym "
    "\"szablon\"), nie usuwasz i nie zmieniasz w nim nazw parametrów; po zmianie python3 film.py sprawdz musi "
    "przejść dla każdego z tych postów. Muzykę i logo dodajesz tylko jako plik w studio/ z licencją i źródłem "
    "zapisanym w polu \"zrodlo\" marki. Filmy opublikowanych i minionych postów panel zostawia bez zmian.",
]


def film_rules(title):
    """Reguły filmu w poleceniu dla agenta: zadania postów i poprawek oraz zmiany studia."""
    if title.startswith(STUDIO_TASK):
        return FILM_RULES + STUDIO_RULES
    if title.startswith((POST_TASK, FIX_POST_TASK)):
        return FILM_RULES
    return []


SCRIPT_AHEAD = 7            # dni: scenariusz nagrania dla filmów właściciela z publikacją w tym czasie
RYTM_SUFFIX = " (stały rytm)"
RYTM_FILE = "kampanie/staly-rytm.md"
RYTM_AHEAD = 2      # dni: z takim wyprzedzeniem powstaje zadanie na kolejny post
RYTM_RESULT_DAYS = 2        # publikacja zrobiona dawniej niż tyle dni (48 h) bez wynik: → zadanie właściciela
MARKS_KEEP_DAYS = 90        # wpisy zrobionych (doneAt) starsze niż tyle dni znikają ze stan.json
RYTM_KEEP = 500             # tyle kluczy publikacji z założonym zadaniem wyniku zostaje w stan.json
RESULT_TASK = "Wpisz wynik publikacji "
FILM_TASK = ("Nagraj film", "Obejrzyj film")   # publikacja z „po: Nagraj/Obejrzyj film…”: post powstaje po nagraniu
RESULT_MINUTES = 3
POST_REVIEW_MINUTES = 5     # czas właściciela na przejrzenie i zatwierdzenie posta
STYLE_FILES = ("STYL.md", "marketing/STYL.md", "kampanie/STYL.md")
PLAN_FILES = ("marketing/plan*.md", "kampanie/plan*.md", "PLAN.md", "plan*.md")
RESULT_KEYS = ("result", "views", "clicks", "accounts", "wyswietlenia", "klikniecia", "konta")
RESULT_NOTES = re.compile(r"^(wynik|wyświetlenia|wyswietlenia|kliknięcia|klikniecia|konta)\s*:\s*\S", re.I)


def secret_file(path):
    """Plik, którego panel nie scala: nazwa .env* albo rozszerzenie .key, .pem (bez wielkości liter)."""
    name = os.path.basename(str(path).replace("\\", "/").rstrip("/")).lower()
    return name.startswith(".env") or name.endswith((".key", ".pem"))


def has_post(folder):
    """Folder posty/<dzień>-… to post, chyba że leży w nim tylko scenariusz nagrania (to jeszcze nie post)."""
    try:
        return os.listdir(folder) != [scenariusz.FILE]
    except OSError:
        return True


def has_result(detail):
    """Publikacja ma wynik: wiersz wynik: albo liczby wyświetlenia:, kliknięcia:, konta: (pola parsera albo notatki)."""
    d = detail if isinstance(detail, dict) else {}
    if any(d.get(k) not in (None, "", 0, [], {}) for k in RESULT_KEYS):
        return True
    for key in ("stats", "metrics"):
        if isinstance(d.get(key), dict) and any(v not in (None, "") for v in d[key].values()):
            return True
    return any(RESULT_NOTES.match(str(n)) for n in d.get("notes") or [])


def next_post_slot(dates, days, today):
    """Data kolejnego posta w rytmie co `days` dni: po ostatniej publikacji, nie wcześniej niż jutro."""
    tomorrow = today + datetime.timedelta(days=1)
    if not dates:
        return tomorrow
    return max(tomorrow, max(dates) + datetime.timedelta(days=days))


def needs_of(task):
    """Wszystkie wartości pola „wymaga” zadania (needs), dla starszych danych samo needsYou."""
    needs = task.get("needs")
    if isinstance(needs, list):
        return needs
    return [task["needsYou"]] if task.get("needsYou") else []


def run_block(task, source, live, tools, sample_ok=False):
    """Pierwszy pasujący powód z AGENCI.md; '' oznacza, że zadanie można uruchomić.

    live: {(projekt, plik, tytuł): id uruchomienia w kolejce albo w toku}; tools: {"claude": bool, "codex": bool}.
    sample_ok pomija regułę projektów przykładowych (podgląd).
    """
    if source != "registry" and not sample_ok:
        return "Projekty przykładowe"
    if task.get("kind") == "publikacja":
        return "Publikację wykonujesz samodzielnie"
    if task.get("state") == "done":
        return "Zrobione"
    if task.get("executor") == "ty":
        return "Zadanie po Twojej stronie"
    if "zgoda" in needs_of(task):
        return "Czeka na Twoją zgodę"
    waiting = [w.get("title", "") for w in task.get("waitingFor") or [] if isinstance(w, dict) and not w.get("done")]
    if waiting:
        return _short("Czeka na: " + ", ".join(waiting), 200)
    tool = "codex" if task.get("executor") == "codex" else "claude"
    if task.get("executor") in AGENT_EXECUTORS:
        if not any(tools.values()):
            return "Brak polecenia Claude i Codex"
    elif not tools.get(tool):
        return "Brak polecenia %s" % tool
    if (task.get("project"), task.get("file"), task.get("title")) in live:
        return "W toku"
    return ""


def mark_status(task):
    """"done" ([x]), "blocked" ([!] albo pole blokada:), "open" (pozostałe) — dla doneAt i blockedSince."""
    if task.get("state") == "done":
        return "done"
    if task.get("state") == "blocked" or (task.get("blocked") or "").strip():
        return "blocked"
    return "open"


def annotate_sample(tasks, block):
    """runId i runBlock dla zadań przykładowych, na podstawie bloku z agenci-przyklad.json."""
    runs = [r for r in block.get("runs") or [] if isinstance(r, dict) and r.get("state") in LIVE]
    by_title = {(r.get("project"), r.get("title")): r.get("id", "") for r in runs}
    tools = {k: bool((v or {}).get("found")) for k, v in (block.get("tools") or {}).items()}
    for t in tasks:
        t["runId"] = by_title.get((t["project"], t["title"]), "")
        live = {(t["project"], t["file"], t["title"])} if t["runId"] else ()
        t["runBlock"] = run_block(t, "sample", live, tools, sample_ok=True)
        t["stateSince"], t["stalled"], t["reviewOverdue"] = "", False, False
        t["doneAt"], t["blockedSince"] = "", ""
