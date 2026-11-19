"""Uruchamianie agentów (Claude Code, Codex) z panelu, na logowaniu subskrypcji. Kontrakt: AGENCI.md.

Sama biblioteka standardowa, Python 3.9+, macOS i Windows. Moduł nie importuje serwera:
dostaje od niego funkcję load_projects, wspólny zamek zapisu i moduł projekt.
"""
import collections
import datetime
import glob
import hashlib
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WINDOWS = os.name == "nt"
# Windows: serwer działa pod pythonw (bez konsoli), więc żaden proces potomny nie może otwierać okna.
NO_WINDOW = {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)} if WINDOWS else {}
LIVE = ("queued", "running")
KEEP = 200          # tyle rekordów zostaje na dysku
SHOWN = 40          # tyle rekordów trafia do /api/data
TOOLS_TTL = 300     # sekundy między odczytami stanu narzędzi
CONFLICT = "Plik zmienił się od ostatniego odczytu. Odświeżam listę."
PM_TOOLS = "Bash(python3 standard/pm.py:*),Bash(python standard/pm.py:*),Read,Write,Edit,Glob,Grep"
# Zadania Claude: bezpieczna lista narzędzi (git lokalnie, testy, pliki); bez push i bez sieci.
TASK_TOOLS = ",".join([
    "Bash(git status:*)", "Bash(git diff:*)", "Bash(git log:*)", "Bash(git switch -c:*)", "Bash(git checkout -b:*)",
    "Bash(git add:*)", "Bash(git commit:*)", "Bash(python3 -m pytest:*)", "Bash(pytest:*)",
    "Bash(python3 -m unittest:*)", "Read", "Edit", "Write", "Glob", "Grep"])
CHECK_PROMPT = "Odpowiedz jednym słowem: ok"
# Rozmowa o zadaniu (AGENCI.md, „Rozmowa o zadaniu”): tylko odczyt plików, bez powłoki, zapisu i sieci.
CHAT_TOOLS = "Read,Grep,Glob,LS"
CHAT_DENY = "Bash,Edit,MultiEdit,Write,NotebookEdit,WebFetch,WebSearch,Task"
CHAT_MAX = 2000             # znaków w jednej wiadomości właściciela
CHAT_KEEP = 100             # tyle wiadomości zostaje w historii zadania
CHAT_ANSWER = 8000          # najwyżej tyle znaków odpowiedzi
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
GIT_NAME, GIT_EMAIL = "Panel projektów", "panel@localhost"     # gdy repozytorium nie ma user.email
# Ścieżki plików w wierszu wynik: (materiał dla następników z po:).
RESULT_PATH = re.compile(r"(?<![\w./-])(/?(?:[\w.-]+/)*[\w-][\w.-]*\.(?:md|txt|csv|json|html|svg|png|jpe?g|pdf|ya?ml))"
                         r"(?![\w/])", re.I)
RESULT_PATHS_MAX = 10


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


def _command(path):
    """Atrapy testowe to skrypty .py: uruchamiamy je bieżącym interpreterem (działa także na Windows)."""
    return [sys.executable, path] if path.lower().endswith(".py") else [path]


def describe_tool(name, data, cwd=""):
    """Czynność agenta w jednym wierszu: 'Edit: src/api.py', 'Bash: npm test'."""
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
            for key in ("command", "pattern", "url", "query", "description", "prompt"):
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
        self.max_parallel = _int(get("PANEL_AGENTS_MAX"), 2)
        self.timeout = _int(get("PANEL_AGENT_TIMEOUT"), 3600)
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
        self._state = {"automat": False, "needsLogin": False, "limitUntil": None, "since": {}, "sessionKey": "",
                       "rytmDone": []}
        self._tools = {"claude": self._tool_blank(), "codex": self._tool_blank()}
        self._tools_at = 0.0
        self._tools_busy = False
        self._login = None          # logowanie przez panel (serwer bez okna): proces, adres, stan
        self.login_web = (get("PANEL_LOGIN_WEB") or "").strip() == "1" or not (sys.platform == "darwin" or WINDOWS)
        self.launcher = lambda args, **kw: subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                                            stderr=subprocess.DEVNULL, **kw)
        self._stop_event = threading.Event()
        self._thread = None
        self._git_lock = threading.Lock()     # operacje panelu na repozytoriach projektów (worktree, commit, merge)
        self.chat_timeout = 180               # s: odpowiedź w rozmowie o zadaniu
        self._chat_lock = threading.Lock()    # pliki rozmów i _chat_live
        self._chat_live = set()               # pliki rozmów, które czekają na odpowiedź w tym procesie
        self._load()
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
            if self._tools_busy or (not force and time.time() - self._tools_at < TOOLS_TTL):
                return
            self._tools_busy = True

        def work():
            try:
                tools = self._read_tools()
                with self._lock:
                    self._tools, self._tools_at = tools, time.time()
                self._login_alert()
            finally:
                self._tools_busy = False

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
            self._write_json(os.path.join(self.runs_dir, "stan.json"), self._state)
        except OSError:
            pass

    def _load(self):
        """Wczytuje ostatnie rekordy; starsze niż KEEP usuwa; przerwane restartem oznacza jako zatrzymane."""
        try:
            names = sorted(n for n in os.listdir(self.runs_dir) if n.endswith(".json") and n != "stan.json")
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
            if rec.get("state") in LIVE:
                rec.update(state="stopped", error="Serwer został zatrzymany.", endedAt=now_iso(), activity="")
                self._save(rec)
                self._interrupted.append(rec)
            self._runs[rec["id"]] = rec
        try:
            with open(os.path.join(self.runs_dir, "stan.json"), encoding="utf-8") as f:
                saved = json.load(f)
            self._state["automat"] = saved.get("automat") is True
            self._state["needsLogin"] = saved.get("needsLogin") is True
            self._state["limitUntil"] = saved.get("limitUntil") if isinstance(saved.get("limitUntil"), str) else None
            since = saved.get("since")
            self._state["since"] = {k: v for k, v in since.items() if isinstance(k, str) and isinstance(v, dict)
                                    and isinstance(v.get("s"), str) and isinstance(v.get("d"), str)} \
                if isinstance(since, dict) else {}
            key = saved.get("sessionKey")
            self._state["sessionKey"] = key if isinstance(key, str) and re.match(r"^[0-9a-f]{32,128}$", key) else ""
            done = saved.get("rytmDone")
            self._state["rytmDone"] = [x for x in done if isinstance(x, str)][-RYTM_KEEP:] if isinstance(done, list) else []
        except (OSError, ValueError, AttributeError):
            pass

    def _remove_files(self, rid):
        for ext in (".json", ".log"):
            try:
                os.remove(os.path.join(self.runs_dir, rid + ext))
            except OSError:
                pass

    def _trim(self):
        with self._lock:
            extra = len(self._runs) - KEEP
            for rid in [r for r, rec in self._runs.items() if rec["state"] not in LIVE][:max(0, extra)]:
                del self._runs[rid]
                self._remove_files(rid)

    # ---------- wątek Automatu ----------
    def start(self):
        """Uruchamia wątek Automatu i porządkuje zadania po uruchomieniach przerwanych restartem."""
        for rec in self._interrupted:
            if rec.get("kind") == "task":
                self._settle_task(rec, rec["state"])
                try:
                    git = self._worktree_info(rec)
                    if git:
                        self._worktree_close(rec, git)
                except Exception as e:
                    log("Gałąź uruchomienia %s: %s" % (rec["id"], e))
        self._interrupted = []
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

    def shutdown(self, wait=8):
        """Zatrzymuje wątek i wszystkie procesy (koniec pracy serwera, testy). Czeka, aż rekordy zostaną zamknięte."""
        if self._login:
            self._login_stop(self._login)
        self._stop_event.set()
        with self._lock:
            ids = [rid for rid, rec in self._runs.items() if rec["state"] in LIVE]
            procs = [p["proc"] for p in self._priv.values() if p.get("proc") is not None]
        for rid in ids:
            self.stop(rid)
        end = time.time() + wait
        while time.time() < end:
            with self._lock:
                if not any(rec["state"] in LIVE for rec in self._runs.values()):
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
        for t in tasks:
            t["runId"] = live.get((t["project"], t["file"], t["title"]), "")
            t["runBlock"] = run_block(t, source, live, tools)
            t["stateSince"] = since.get(self.projekt.task_key(t), "")
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
    def snapshot(self):
        self.refresh_tools()
        today = datetime.date.today().isoformat()
        limit = self.limit_until()
        with self._lock:
            runs = [dict(r, steps=list(r.get("steps") or []), denials=list(r.get("denials") or []))
                    for r in reversed(list(self._runs.values()))]
            todays = [r for r in runs if (r.get("queuedAt") or "")[:10] == today]
            return {"machine": self.machine,
                    "tools": {k: dict(v) for k, v in self._tools.items()},
                    "needsLogin": self._state["needsLogin"], "limitUntil": limit,
                    "automat": self._state["automat"], "maxParallel": self.max_parallel, "canRunTasks": True,
                    "loginWeb": self.login_web,
                    "login": ({"active": True, "url": self._login["url"]}
                              if self._login and self._login["proc"].poll() is None and self._login["url"] else {"active": False}),
                    "today": {"runs": len(todays),
                              "tokens": sum((r.get("tokensIn") or 0) + (r.get("tokensOut") or 0) for r in todays),
                              "costUsd": round(sum(r.get("costUsd") or 0 for r in todays), 2)},
                    "runs": runs[:SHOWN]}

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
                "model": "", "keySource": "", "denials": []}

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
        return out

    def task_prompt(self, tool, name, file, line, title, stage, detail=None, git=None):
        """git: {"branch", "cwd", "file", "card", "cards"} przy pracy w katalogu roboczym gałęzi uruchomienia."""
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
        else:
            git_rules = [
                "- Pracę w repozytorium git zapisz na nowej gałęzi `agent/%s-krotka-nazwa` (`git switch -c`) jednym "
                "lokalnym commitem, bez push i bez plików KARTA.md, ZADANIA.md, DECYZJE.md. W wierszu `wynik:` podaj "
                "gałąź i skrót commita. Folder bez repozytorium: bez gałęzi i commita." % datetime.date.today().isoformat()]
        return "\n".join(head + [
            "",
            "Zasady:",
            "- Rób tylko to zadanie. Nie zmieniaj innych zadań ani terminów. W KARTA.md możesz tylko dopisać pytanie.",
            "- Nigdy nie zmieniaj tytułu zadania (tekstu wiersza przed pierwszym „|”) i nie dopisuj do niego raportu.",
            "- Nie wykonuj działań nieodwracalnych ani wychodzących na zewnątrz (wysyłka, publikacja, wdrożenie, płatność). "
            "Gdy zadanie tego wymaga, przygotuj wszystko i dopisz w wierszu zadania `wymaga: zgoda`.",
            "- Polecenia, na które nie masz uprawnień, pomiń i opisz w wierszu `zostało:`.",
            "- Nie zlecaj właścicielowi kroków technicznych (git, commit, scalanie, konfiguracja, polecenia w terminalu): "
            "panel sam zatwierdza i scala gałęzie agenta. Gdy do dokończenia potrzebujesz od właściciela danych "
            "(nazwa, adres, wybór), zadaj pytanie w KARTA.md z propozycją; techniczną resztę zrobi kolejne zadanie agenta.",
            "- Wykonane kroki odhacz w ich wierszach (`  - [x] krok`).",
            "- Gdy pod zadaniem jest wiersz `poprawka:`, to uwagi właściciela po odbiorze: popraw pracę według nich.",
            "- Na koniec dopisz pod wierszem zadania wcięte o 2 spacje wiersze (istniejące wiersze z tym kluczem zastąp): "
            "`  wynik: …` (krótko, co powstało i gdzie); `  decyzja: …`, gdy właściciel ma coś zatwierdzić przy odbiorze; "
            "`  zostało: …`, gdy coś nie zostało zrobione.",
            "- Możesz dopisać pod zadaniem jeden wiersz `  następne: Tytuł | kto: … | kiedy: RRRR-MM-DD` z propozycją "
            "kolejnego zadania. Nowych zadań nie zakładaj.",
        ] + git_rules + [
            "- Pytania do właściciela dopisz jako kolejny punkt „1. pytanie” w sekcji „## Pytania do właściciela” "
            "w KARTA.md (załóż sekcję na końcu pliku, gdy jej nie ma); termin odpowiedzi jako wcięty wiersz "
            "`   termin: RRRR-MM-DD` pod pytaniem.",
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

    def _find_task(self, task_id=None, key=None):
        """Zadanie po id albo po (projekt, plik, tytuł). Zwraca (zadanie, dane, indeks folderów)."""
        data, index = self.load_projects()
        for t in data["tasks"]:
            if (task_id is not None and t["id"] == task_id) or \
                    (key is not None and (t["project"], t["file"], t["title"]) == key):
                return t, data, index
        return None, data, index

    def run_task(self, task_id, title, auto=False):
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
            tool = "codex" if task["executor"] == "codex" else "claude"
            path = self.tool_path(tool)
            first_steps = []
            if self.git_pull:
                note, pulled = self._git_pull(folder)
                if note:
                    first_steps.append({"t": time.strftime("%H:%M:%S"), "text": note})
                if pulled:
                    task, data, index = self._find_task(key=(task["project"], task["file"], title))
                    if not task or self.run_block(task, data["projectsSource"]):
                        return 409, CONFLICT, {}
            changes = {"state": "doing", "executor": tool}
            if self.machine in ("pc", "mac", "cloud"):
                changes["machine"] = self.machine
            try:
                with self.write_lock:
                    ok = self.projekt.update_task(folder, task["file"], task["line"], title, changes)
            except ValueError as e:
                return 400, "Nie zapisano: %s." % e, {}
            except OSError:
                return 400, "Nie udało się zapisać zmiany.", {}
            if not ok:
                return 409, CONFLICT, {}
            project = next((p for p in data["projects"] if p["id"] == task["project"]), {})
            stage = next((s["title"] for s in data["stages"] if s["id"] == task.get("stage")), "")
            rec = self._new("task", tool, title, auto, task["project"], project.get("name", task["project"]),
                            task["id"], task["file"])
            rec["steps"] = first_steps
            priv = {"folder": folder, "client": project.get("client") is True,
                    "label": project.get("alias") or project.get("name") or task["project"],
                    "task": {"tool": tool, "path": path, "name": rec["projectName"], "file": task["file"],
                             "line": task["line"], "title": title, "stage": stage,
                             "detail": with_answers(task, data["tasks"])}}
            self._task_command(priv)
            self._enqueue(rec, priv)
            return 200, "", {"id": rec["id"]}

    def _task_command(self, priv, git=None):
        """Polecenie, katalog i prompt zadania. git (z _worktree_open): praca w katalogu roboczym gałęzi
        uruchomienia, pliki standardu w folderze projektu przez --add-dir i ścieżki bezwzględne."""
        t, folder = priv["task"], priv["folder"]
        if git:
            cwd = git["worktree"] if git["rel"] == "." else os.path.join(git["worktree"], git["rel"])
            extra = [x for d in self._standard_dirs(folder, t["file"]) for x in ("--add-dir", d)]
            info = {"branch": git["branch"], "cwd": cwd, "file": os.path.join(folder, t["file"]),
                    "card": os.path.join(folder, "KARTA.md"),
                    "cards": os.path.dirname(os.path.realpath(os.path.join(folder, "KARTA.md")))}
        else:
            cwd, extra, info = folder, _card_dirs(folder), None
        prompt = self.task_prompt(t["tool"], t["name"], t["file"], t["line"], t["title"], t["stage"], t["detail"],
                                  git=info)
        if t["tool"] == "codex":
            args = _command(t["path"]) + ["exec", "--json", "--sandbox", "workspace-write", "--skip-git-repo-check",
                                          "-C", cwd] + (extra if git else []) + ["-"]
        else:
            args = self._claude_args(t["path"], self.model, extra + ["--allowedTools", TASK_TOOLS])
        priv.update(args=args, cwd=cwd, prompt=prompt)

    # ---------- rozmowa o zadaniu ----------
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
        msgs = [m for m in data.get("messages") or [] if isinstance(m, dict) and m.get("role") in ("ty", "claude")]
        return {"session": str(data.get("session") or ""), "messages": msgs[-CHAT_KEEP:],
                "pending": data.get("pending") is True, "error": str(data.get("error") or "")}

    def _chat_write(self, path, chat):
        chat["messages"] = chat["messages"][-CHAT_KEEP:]
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._write_json(path, chat)

    def chat_get(self, task_id):
        """Historia rozmowy o zadaniu. Zwraca (kod, błąd, {"messages", "pending", "error"})."""
        task, _, _ = self._find_task(task_id=str(task_id))
        if not task:
            return 404, "Nie ma tego zadania.", {}
        path = self._chat_file(task)
        with self._chat_lock:
            chat = self._chat_read(path)
            live = path in self._chat_live
        if chat["pending"] and not live:            # odpowiedź przerwana restartem panelu
            chat["error"] = chat["error"] or "Odpowiedź przerwana. Wyślij pytanie jeszcze raz."
        return 200, "", {"messages": chat["messages"], "pending": live, "error": chat["error"]}

    def chat_prompt(self, name, task, stage, detail, folder, text):
        """Pierwsza wiadomość rozmowy: kontekst zadania, zasady i pytanie właściciela (ostatnie wiersze)."""
        lines = ["Rozmawiasz z właścicielem projektu „%s” o jednym zadaniu z pliku %s, wiersz %d: „%s”."
                 % (name, task["file"], task["line"], task["title"])]
        if stage:
            lines.append("Etap: %s." % stage)
        more = self.detail_lines(detail)
        if more:
            lines += ["", "Szczegóły zadania:"] + more
        files = [os.path.join(folder, n) for n in ("KARTA.md", "ZADANIA.md", task["file"])]
        lines += ["", "Pliki projektu: karta %s, zadania %s%s." % (files[0], files[1], "" if files[2] == files[1]
                                                                  else ", plik zadania %s" % files[2]),
                  "", "Zasady:",
                  "- Odpowiadasz na pytanie właściciela o to jedno zadanie.",
                  "- Krótko i konkretnie, prostym językiem po polsku. Bez żargonu technicznego, chyba że właściciel o niego prosi.",
                  "- Możesz czytać pliki projektu, ale niczego nie zmieniasz i nie uruchamiasz poleceń.",
                  "- Gdy zadanie wygląda na zbędne, błędne albo niejasne, powiedz to wprost i zaproponuj jedną konkretną "
                  "zmianę (np. zamknąć je, zmienić termin, zastąpić je innym zadaniem) w jednym zdaniu zaczynającym się "
                  "od „Propozycja:”.",
                  "- Nigdy nie proś właściciela o hasła, klucze ani tokeny.",
                  "", "Pytanie właściciela:", text]
        return "\n".join(lines) + "\n"

    def chat_send(self, task_id, title, message):
        """Wiadomość właściciela w rozmowie o zadaniu; odpowiedź Claude przychodzi w tle (chat_get).
        Zwraca (kod, błąd, dodatki): 202 z {"pending": True} albo błąd 400, 404, 409, 500."""
        text = str(message or "").strip()
        if not text:
            return 400, "Napisz pytanie.", {}
        if len(text) > CHAT_MAX:
            return 400, "Najwyżej %d znaków." % CHAT_MAX, {}
        task, data, index = self._find_task(task_id=str(task_id))
        if not task or task["project"] not in index:
            return 404, "Nie ma tego zadania.", {}
        if task["title"] != str(title):
            return 409, CONFLICT, {}
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
        folder = index[task["project"]]
        file = self._chat_file(task)
        with self._chat_lock:
            if file in self._chat_live:
                return 409, "Czekam jeszcze na odpowiedź.", {}
            if len(self._chat_live) >= CHAT_PARALLEL:
                return 409, "Za dużo rozmów naraz. Spróbuj za chwilę.", {}
            chat = self._chat_read(file)
            session = chat["session"] if re.fullmatch(r"[\w-]{1,100}", chat["session"]) else ""
            chat["messages"].append({"role": "ty", "text": text, "at": now_iso()})
            chat.update(pending=True, error="")
            try:
                self._chat_write(file, chat)
            except OSError:
                return 500, "Nie udało się zapisać rozmowy.", {}
            self._chat_live.add(file)
        try:
            if session:
                prompt = text + "\n"
            else:
                project = next((p for p in data["projects"] if p["id"] == task["project"]), {})
                stage = next((s["title"] for s in data["stages"] if s["id"] == task.get("stage")), "")
                prompt = self.chat_prompt(project.get("name", task["project"]), task, stage,
                                          with_answers(task, data["tasks"]), folder, text)
            # Tylko odczyt: tryb uprawnień default (bez acceptEdits i bypass), lista narzędzi do odczytu, reszta
            # zabroniona wprost (zabronione wygrywa z regułami allow z .claude/settings.json projektu), bez MCP.
            args = _command(path) + ["-p", "--output-format", "json", "--permission-mode", "default"]
            if self.model:
                args += ["--model", self.model]
            if session:
                args += ["--resume", session]
            args += _card_dirs(folder) + ["--allowedTools", CHAT_TOOLS, "--disallowedTools", CHAT_DENY,
                                          "--strict-mcp-config"]
            threading.Thread(target=self._chat_run, args=(file, args, folder, prompt, bool(session)),
                             daemon=True).start()
        except Exception:
            self._chat_end(file, "", "", "Nie udało się uruchomić rozmowy.")
            return 500, "Nie udało się uruchomić rozmowy.", {}
        return 202, "", {"pending": True}

    def _chat_run(self, file, args, cwd, prompt, resumed):
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
            self._chat_end(file, answer, session, error)

    def _chat_end(self, file, answer, session, error):
        with self._chat_lock:
            try:
                chat = self._chat_read(file)
                if session:
                    chat["session"] = session
                elif error == CHAT_EXPIRED:
                    chat["session"] = ""            # następna wiadomość zaczyna rozmowę od nowa, z kontekstem
                if answer:
                    chat["messages"].append({"role": "claude", "text": answer, "at": now_iso()})
                chat.update(pending=False, error=error)
                self._chat_write(file, chat)
            except OSError:
                pass
            finally:
                self._chat_live.discard(file)

    def _chat_parse(self, out, err, code, resumed):
        """Wynik `claude -p --output-format json`: (odpowiedź, sesja, błąd). Błąd krótko, bez śladu stosu."""
        try:
            res = json.loads(out)
        except ValueError:
            res = None
        if isinstance(res, list):
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
    def _exclude_agent_dir(top):
        """/.agent/ w .git/info/exclude: katalogi robocze nie brudzą stanu repozytorium (lokalnie, bez commita)."""
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
            if "/%s/" % AGENT_DIR not in text.split("\n"):
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "a", encoding="utf-8") as f:
                    f.write(("" if not text or text.endswith("\n") else "\n") + "/%s/\n" % AGENT_DIR)
        except OSError:
            pass

    def _worktree_open(self, rec, priv):
        """Przed startem zadania w repozytorium git: nowa gałąź agent/RRRR-MM-DD-nazwa od bieżącego HEAD w katalogu
        <repozytorium>/.agent/<id>. Bez repozytorium (albo przy błędzie git) praca w folderze projektu jak dotąd."""
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
            branch = self._branch_name(top, rec["title"])
            wt = os.path.join(top, AGENT_DIR, rec["id"])
            try:
                os.makedirs(os.path.join(top, AGENT_DIR), exist_ok=True)
            except OSError:
                return self._step(rec, "git: nie utworzono katalogu %s, praca w folderze projektu" % AGENT_DIR)
            self._exclude_agent_dir(top)
            code, _, err = git_run(top, ["worktree", "add", "-q", "-b", branch, wt, head], timeout=300)
            if code != 0:
                return self._step(rec, "git: nie utworzono katalogu roboczego (%s), praca w folderze projektu"
                                  % _short(err, 80))
        git = {"top": top, "rel": rel, "worktree": wt, "branch": branch, "base": base, "baseCommit": head}
        priv["git"] = git
        with self._lock:
            rec.update(branch=branch, base=base, baseCommit=head, changes=[], commits=0)
            self._save(rec)
        self._step(rec, "Gałąź %s od %s" % (branch, base if base != head else head[:8]))
        self._task_command(priv, git)

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

    def _worktree_close(self, rec, git):
        """Po zakończeniu: commit niezatwierdzonych zmian agenta na gałęzi (bez plików standardu), changes i commits
        w rekordzie, usunięcie katalogu roboczego. Gałąź zostaje."""
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
                return 409, _short("Niezatwierdzone zmiany w repozytorium: %s." % ", ".join(dirty[:5]), 300), {}
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
        return 200, "", {"commit": sha}

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

    def run_pm(self, auto=False):
        path = self.tool_path("claude")
        if not path:
            return 409, "Brak polecenia claude", {}
        with self._lock:
            if any(r["kind"] == "pm" and r["state"] in LIVE for r in self._runs.values()):
                return 409, "Raport PM już trwa.", {}
            rec = self._new("pm", "claude", "Raport PM", auto)
            prompt = ("Przygotuj raport według standard/PM.md: uruchom `python3 standard/pm.py` i zapisz notatkę do "
                      "raporty/%s.md (nadpisz wcześniejszą z tego dnia). Odpowiedz raportem.\n"
                      % datetime.date.today().isoformat())
            args = self._claude_args(path, self.pm_model, ["--agent", "pm", "--allowedTools", PM_TOOLS])
            self._enqueue(rec, {"args": args, "cwd": self.root, "prompt": prompt})
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

    def post_detail(self, folder, day, channel, title):
        """Szczegóły zadania „Przygotować post na …”: cel, gotowe gdy, materiał (rytm, STYL.md, plan)."""
        return {"cel": "post na %s%s: %s, do zatwierdzenia przez właściciela"
                       % (day, " (%s)" % channel if channel else "", title),
                "gotowe gdy": "obok KARTA.md jest folder posty/%s-<krótka-nazwa>/ z post.md (sekcje ## Facebook, "
                              "## LinkedIn, ## Alt) i grafika.svg albo grafika.png; przy filmie także scenariusz.json "
                              "(wzór: posty/2026-11-20-film-a-opis-pl-de/scenariusz.json), film nagrywa panel sam" % day,
                "materiał": [RYTM_FILE] + self.marketing_refs(folder)}

    def result_detail(self, folder, day, channel, title):
        """Szczegóły zadania „Wpisz wynik publikacji …”: cel, gotowe gdy, materiał (rytm, plan)."""
        refs = [r for r in self.marketing_refs(folder) if not r.endswith("STYL.md")]
        return {"cel": "wynik publikacji „%s” z %s%s w %s (szczegóły pod publikacją)"
                       % (title, day, " (%s)" % channel if channel else "", RYTM_FILE),
                "gotowe gdy": "pod publikacją są wiersze wyświetlenia:, kliknięcia: i konta: (albo wynik:)",
                "materiał": [RYTM_FILE] + refs}

    def _add_task(self, folder, pid, title, changes, detail=None):
        """Nowe zadanie w „Do rozplanowania” z polami; wywołujący trzyma write_lock."""
        self.projekt.add_task(folder, title)
        task = next(t for t in self.projekt.read_project(folder, pid)["tasks"] if t["title"] == title)
        self.projekt.update_task(folder, task["file"], task["line"], title, changes)
        for key, value in (detail or {}).items():
            self.projekt.set_detail(folder, task["file"], task["line"], title, key, value)

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
                        and not any(n == day or n.startswith(day + "-") for n in folders):
                    title = self.projekt._clean("%s%s: %s" % (POST_TASK, day, t["title"]), 160)
                    if title not in titles:
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

    def run_check(self, tool="claude"):
        if tool not in ("claude", "codex"):
            return 400, "Nieznane narzędzie.", {}
        path = self.tool_path(tool)
        if not path:
            return 409, "Brak polecenia %s" % tool, {}
        with self._lock:
            if any(r["kind"] == "check" and r["tool"] == tool and r["state"] in LIVE for r in self._runs.values()):
                return 409, "Test już trwa.", {}
            rec = self._new("check", tool, "Test połączenia")
            os.makedirs(self.runs_dir, exist_ok=True)
            if tool == "codex":
                args = _command(path) + ["exec", "--json", "--sandbox", "read-only", "--skip-git-repo-check", "-"]
            else:
                args = _command(path) + ["-p", "--output-format", "stream-json", "--verbose", "--model", "haiku"]
            self._enqueue(rec, {"args": args, "cwd": self.runs_dir, "prompt": CHECK_PROMPT + "\n"})
        return 200, "", {"id": rec["id"]}

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
            if tool != "claude":
                return 409, "Logowanie Codex przez panel nie jest obsługiwane: %s" % self.login_cmd(tool, path), {}
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
        with self._lock:
            while self._queue and sum(1 for r in self._runs.values() if r["state"] == "running") < self.max_parallel:
                rec = self._runs[self._queue.pop(0)]
                rec["state"], rec["startedAt"] = "running", now_iso()
                self._priv[rec["id"]]["t0"] = time.time()
                self._save(rec)
                threading.Thread(target=self._execute, args=(rec,), daemon=True).start()

    def _step(self, rec, text):
        text = _short(text, 120)
        if not text:
            return
        with self._lock:
            rec["activity"] = text
            rec["steps"] = (rec["steps"] + [{"t": time.strftime("%H:%M:%S"), "text": text}])[-30:]

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

    def _execute(self, rec):
        priv = self._priv[rec["id"]]
        st = {"result": None, "tail": collections.deque(maxlen=8), "limit": False, "rate": None, "status": None,
              "last": "", "failed": ""}
        code, timer, out, proc = None, None, None, None
        try:
            if priv.get("stop"):
                return self._finish(rec, "stopped", "")
            os.makedirs(self.runs_dir, exist_ok=True)
            out = open(os.path.join(self.runs_dir, rec["id"] + ".log"), "w", encoding="utf-8")
            if WINDOWS:     # własna grupa (zatrzymanie całego drzewa) i brak okna konsoli
                kw = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | NO_WINDOW["creationflags"]}
            else:
                kw = {"start_new_session": True}
            if priv.get("task") and self.worktrees:
                self._worktree_open(rec, priv)
            cwd = priv["cwd"]
            if self.agent_user and rec["kind"] in ("check", "plan"):
                cwd = tempfile.gettempdir()     # agent nie musi mieć dostępu do katalogu uruchomień
            try:
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
            timer = threading.Timer(self.timeout, self._on_timeout, [rec])
            timer.daemon = True
            timer.start()
            try:
                proc.stdin.write(priv["prompt"])
            except (OSError, ValueError):      # proces skończył się, zanim przeczytał polecenie
                pass
            try:
                proc.stdin.close()
            except (OSError, ValueError):
                pass
            parse = self._on_codex if rec["tool"] == "codex" else self._on_claude
            for line in proc.stdout:
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
                    continue
                try:
                    parse(rec, ev, st, priv["cwd"])
                except Exception:  # nieznany kształt zdarzenia nie może przerwać uruchomienia
                    pass
            code = proc.wait()
            self._conclude(rec, st, code)
        except Exception as e:
            st["tail"].append(str(e))
            self._conclude(rec, st, -1 if code is None else code)
        finally:
            if timer:
                timer.cancel()
            for stream in (out, proc.stdout if proc else None, proc.stdin if proc else None):
                if stream:
                    try:
                        stream.close()
                    except OSError:
                        pass

    def _on_claude(self, rec, ev, st, cwd):
        kind = ev.get("type")
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
                    self._step(rec, describe_tool(block.get("name", "?"), block.get("input"), cwd))
                elif block.get("type") == "text" and str(block.get("text") or "").strip():
                    self._step(rec, str(block["text"]).strip().split("\n")[0])
            usage = msg.get("usage") or {}
            with self._lock:
                rec["tokensOut"] += int(usage.get("output_tokens") or 0)
        elif kind == "rate_limit_event":
            info = ev.get("rate_limit_info") or {}
            st["rate"] = info
            if str(info.get("status") or "").lower() in DENIED:
                st["limit"] = True
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
            st["status"] = ev.get("api_error_status") or st["status"]

    def _on_codex(self, rec, ev, st, cwd):
        """Strumień `codex exec --json`: nowy układ (item.*, turn.*) i starszy (msg)."""
        kind = ev.get("type")
        msg = ev.get("msg") if isinstance(ev.get("msg"), dict) else None
        if msg:                                             # starszy układ
            kind, ev = msg.get("type"), msg
            if kind == "agent_message":
                st["last"] = str(ev.get("message") or "")
                self._step(rec, st["last"].strip().split("\n")[0])
            elif kind == "exec_command_begin":
                cmd = ev.get("command")
                self._step(rec, "Bash: %s" % (" ".join(cmd) if isinstance(cmd, list) else cmd))
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
                self._step(rec, st["last"].strip().split("\n")[0])
            elif what == "command_execution" and kind == "item.started":
                self._step(rec, "Bash: %s" % item.get("command", ""))
            elif what == "file_change" and kind == "item.completed":
                for ch in item.get("changes") or []:
                    if isinstance(ch, dict) and ch.get("path"):
                        self._step(rec, describe_tool("Edit", {"file_path": ch["path"]}, cwd))
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

    def _conclude(self, rec, st, code):
        """Klasyfikacja końca: stopped → timeout → login → limit → error → done."""
        priv = self._priv.get(rec["id"]) or {}
        res = st["result"] if isinstance(st["result"], dict) else None
        text = str(res.get("result") or "") if res and rec["tool"] == "claude" else st["last"]
        failed = bool(st["failed"]) or res is None or bool(res.get("is_error")) or code not in (0, None)
        blob = " ".join([text, st["failed"]] + list(st["tail"]))
        status = str(st["status"] or "")
        if priv.get("stop"):
            return self._finish(rec, "stopped", "")
        if priv.get("timeout"):
            return self._finish(rec, "timeout", "Przekroczony czas: %d min." % max(1, self.timeout // 60))
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
        return self._finish(rec, "done", "", result=text.strip()[:4000])

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
            self._close_task(rec, state, priv.get("git"))
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
            if state == "limit":
                self._state["limitUntil"] = limit_until
            elif state == "done" and rec["tool"] == "claude":
                self._state["limitUntil"] = None
            self._save_state()
            self._save(rec)
        if state != "stopped" and rec["kind"] != "check":
            self._notify(rec, priv)
        self._login_alert()
        self.refresh_tools(force=True)
        self._pump()

    def _close_task(self, rec, state, git=None):
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
        if state == "done":
            try:
                self._pass_materials(rec, dict(git, branch=rec.get("branch") or git["branch"]) if git else None)
            except Exception as e:
                log("Materiał z wyniku: %s" % e)

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
        self._send_ntfy(body)

    def _send_ntfy(self, body):
        if not self.ntfy_url:
            return
        data = body.encode("utf-8")

        def send():
            try:
                req = urllib.request.Request(self.ntfy_url, data=data, method="POST",
                                             headers={"Content-Type": "text/plain; charset=utf-8"})
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
            self._send_ntfy("Claude wymaga logowania. Zaloguj się w panelu: Agenci, Zaloguj.")

    # ---------- Automat ----------
    def tick(self, now=None):
        """Jeden obieg Automatu. Zwraca listę id nowych uruchomień."""
        started = []
        with self._lock:
            if not self._state["automat"] or self._state["needsLogin"]:
                return started
        if self.limit_until():
            return started
        now = now or datetime.datetime.now()
        today = now.date().isoformat()
        with self._lock:
            todays = [r for r in self._runs.values() if (r.get("queuedAt") or "")[:10] == today]
            # raz dziennie: liczy się próba Automatu albo raport udany lub trwający; ręczny, przerwany nie blokuje
            pm_today = any(r["kind"] == "pm" and (r["auto"] or r["state"] in LIVE or r["state"] == "done")
                           for r in todays)
            done_today = {(r["project"], r["file"], r["title"]) for r in todays if r["kind"] == "task"}
            free = self.max_parallel - sum(1 for r in self._runs.values() if r["state"] in LIVE)
        if now.hour >= self.pm_hour and not pm_today and \
                not os.path.exists(os.path.join(self.notes_dir, today + ".md")):
            code, _, extra = self.run_pm(auto=True)
            if code == 200:
                started.append(extra["id"])
                free -= 1
        if free <= 0:
            return started
        data, index = self.load_projects()
        if data["projectsSource"] != "registry":
            return started
        added = self._plan_posts(data, index, now.date())
        added = self._plan_rhythm(data, index, now.date()) or added
        if added:
            data, index = self.load_projects()
        night = now.hour >= 22 or now.hour < 6
        live = self._live_keys()
        tools = {"claude": self.tool_found("claude"), "codex": self.tool_found("codex")}
        for t in data["tasks"]:
            if free <= 0:
                break
            if t["state"] != "todo" or t["executor"] not in ("claude", "codex"):
                continue
            if t["machine"] != self.machine and not (not t["machine"] and self.default_node):
                continue
            if not t["date"] or t["date"][:10] > today:
                continue
            if (t["slot"] == "noc" and not night) or (t["slot"] == "dzień" and night):
                continue
            if (t["project"], t["file"], t["title"]) in done_today or run_block(t, "registry", live, tools):
                continue
            code, _, extra = self.run_task(t["id"], t["title"], auto=True)
            if code == 200:
                started.append(extra["id"])
                free -= 1
        return started


def with_answers(task, tasks):
    """Szczegóły zadania z odpowiedziami właściciela z formularzy poprzedników (`po:`, pole `pyta:`)."""
    d = dict(task.get("detail") or {})
    ids = {w.get("id") for w in task.get("waitingFor") or [] if isinstance(w, dict) and w.get("done") and w.get("id")}
    extra = [a for t in tasks if t.get("id") in ids for a in (t.get("detail") or {}).get("answers") or []]
    if extra:
        d["answers"] = list(d.get("answers") or []) + extra
    return d


POST_TASK = "Przygotować post na "
RYTM_SUFFIX = " (stały rytm)"
RYTM_FILE = "kampanie/staly-rytm.md"
RYTM_AHEAD = 2      # dni: z takim wyprzedzeniem powstaje zadanie na kolejny post
RYTM_RESULT_DAYS = 2        # publikacja zrobiona dawniej niż tyle dni (48 h) bez wynik: → zadanie właściciela
RYTM_KEEP = 500             # tyle kluczy publikacji z założonym zadaniem wyniku zostaje w stan.json
RESULT_TASK = "Wpisz wynik publikacji "
FILM_TASK = "Nagraj film"   # publikacja z „po: Nagraj film…”: post powstaje po nagraniu
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
    if not tools.get(tool):
        return "Brak polecenia %s" % tool
    if (task.get("project"), task.get("file"), task.get("title")) in live:
        return "W toku"
    return ""


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
