"""Uruchamianie agentów (Claude Code, Codex) z panelu, na logowaniu subskrypcji. Kontrakt: AGENCI.md.

Sama biblioteka standardowa, Python 3.9+, macOS i Windows. Moduł nie importuje serwera:
dostaje od niego funkcję load_projects, wspólny zamek zapisu i moduł projekt.
"""
import collections
import datetime
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
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
CHECK_PROMPT = "Odpowiedz jednym słowem: ok"
PLAN_MAX = 6
STATE_LABEL = {"done": "zakończone", "error": "błąd", "login": "wymaga logowania", "limit": "limit subskrypcji",
               "stopped": "zatrzymane", "timeout": "przekroczony czas"}
LOGIN_RE = re.compile(r"authenticat|oauth|/login|not logged in|invalid api key|\b401\b", re.I)
LIMIT_RE = re.compile(r"usage limit|limit reached|rate.?limit|hit your limit|\b429\b", re.I)
DENIED = {"rejected", "denied", "blocked", "exceeded"}


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
        self.max_parallel = _int(get("PANEL_AGENTS_MAX"), 2)
        self.timeout = _int(get("PANEL_AGENT_TIMEOUT"), 3600)
        self.model = (get("PANEL_AGENT_MODEL") or "").strip()
        self.pm_model = (get("PANEL_PM_MODEL") or "").strip()
        self.pm_hour = _int(get("PANEL_PM_HOUR"), 7, low=0)
        self.git_pull = (get("PANEL_GIT_PULL") or "").strip() == "1"
        self.ntfy_url = (get("PANEL_NTFY_URL") or "").strip()
        self.tick_seconds = 60

        self._lock = threading.RLock()        # rekordy, kolejka, procesy, stan
        self._start_lock = threading.Lock()   # jedno przyjmowanie zadania naraz (może potrwać: git pull)
        self._runs = collections.OrderedDict()
        self._queue = []
        self._priv = {}                       # id -> dane robocze, których nie pokazujemy (folder, prompt, proces)
        self._state = {"automat": False, "needsLogin": False, "limitUntil": None}
        self._tools = {"claude": self._tool_blank(), "codex": self._tool_blank()}
        self._tools_at = 0.0
        self._tools_busy = False
        self.launcher = lambda args, **kw: subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                                            stderr=subprocess.DEVNULL, **kw)
        self._stop_event = threading.Event()
        self._thread = None
        self._load()

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

    def _probe(self, args, timeout=20):
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

    def annotate(self, tasks, source):
        """Dopisuje do zadań runId i runBlock."""
        live = self._live_keys()
        tools = {"claude": self.tool_found("claude"), "codex": self.tool_found("codex")}
        for t in tasks:
            t["runId"] = live.get((t["project"], t["file"], t["title"]), "")
            t["runBlock"] = run_block(t, source, live, tools)

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

    def task_prompt(self, tool, name, file, line, title, stage):
        rules = "AGENTS.md" if tool == "codex" else "CLAUDE.md"
        head = ["Pracujesz w projekcie „%s” według %s i KARTA.md." % (name, rules),
                "Wykonaj jedno zadanie z pliku %s, wiersz %d: „%s”." % (file, line, title)]
        if stage:
            head.append("Etap: %s." % stage)
        return "\n".join(head + [
            "",
            "Zasady:",
            "- Rób tylko to zadanie. Nie zmieniaj innych zadań, terminów ani pliku KARTA.md.",
            "- Nie wykonuj działań nieodwracalnych ani wychodzących na zewnątrz (wysyłka, publikacja, wdrożenie, płatność). "
            "Gdy zadanie tego wymaga, przygotuj wszystko i dopisz w wierszu zadania `wymaga: zgoda`.",
            "- Polecenia, na które nie masz uprawnień, pomiń i opisz w punkcie „Zostało”.",
            "- Na koniec zmień w %s wyłącznie wiersz tego zadania: gotowe to `[x]`; nie da się dokończyć to `[!]` "
            "i pole `blokada: powód`; potrzebny przegląd właściciela to `[~]` i pole `wymaga: odbiór`." % file,
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
            prompt = self.task_prompt(tool, rec["projectName"], task["file"], task["line"], title, stage)
            if tool == "codex":
                args = _command(path) + ["exec", "--json", "--sandbox", "workspace-write", "--skip-git-repo-check",
                                         "-C", folder, "-"]
            else:
                args = self._claude_args(path, self.model, _card_dirs(folder))
            self._enqueue(rec, {"args": args, "cwd": folder, "prompt": prompt, "folder": folder})
            return 200, "", {"id": rec["id"]}

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
            if t.get("kind") != "zadanie" or t.get("state") == "done":
                continue
            st = stages.get(t.get("stage")) or {}
            block = run_block(t, data["projectsSource"], live, tools)
            out.append({"id": t["id"], "project": names.get(t["project"], t["project"]), "title": t["title"],
                        "stage": st.get("title", ""), "stageDue": st.get("date") or "", "date": t.get("date") or "",
                        "executor": t.get("executor") or "", "state": t.get("state", ""),
                        "needsYou": t.get("needsYou") or "", "agent": not block, "why": block})
        return out

    def plan_prompt(self, text, cands, today):
        rows = json.dumps([{k: c[k] for k in ("id", "project", "title", "stage", "stageDue", "date", "executor",
                                              "state", "needsYou", "agent")} for c in cands], ensure_ascii=False)
        return "\n".join([
            "Jesteś kierownikiem projektów właściciela. Dziś jest %s." % today,
            "Właściciel napisał, co chce dziś robić:",
            "<<<", text, ">>>",
            "",
            "Poniżej wszystkie otwarte zadania jego projektów (JSON). Pole agent=true oznacza, że zadanie może wykonać agent;",
            "agent=false to zadania właściciela albo czekające na jego zgodę.",
            rows,
            "",
            "Ułóż plan na dziś:",
            "- „agenci”: najwyżej %d zadań z agent=true, najważniejsze najpierw (terminy etapów, prośba właściciela);" % PLAN_MAX,
            "- „ty”: najwyżej 5 zadań z agent=false, które właściciel powinien dziś zrobić albo rozstrzygnąć;",
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
            try:
                proc = subprocess.Popen(priv["args"], cwd=priv["cwd"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
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
            try:
                self._settle_task(rec, state)
            except Exception as e:
                log("Zadanie po uruchomieniu: %s" % e)
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
            self._notify(rec)
        self.refresh_tools(force=True)
        self._pump()

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

    def _notify(self, rec):
        if not self.ntfy_url:
            return
        where = " (%s)" % rec["projectName"] if rec["projectName"] else ""
        body = ("%s%s: %s" % (rec["title"], where, STATE_LABEL.get(rec["state"], rec["state"]))).encode("utf-8")

        def send():
            try:
                req = urllib.request.Request(self.ntfy_url, data=body, method="POST",
                                             headers={"Content-Type": "text/plain; charset=utf-8"})
                urllib.request.urlopen(req, timeout=5).close()
            except Exception:
                pass
        threading.Thread(target=send, daemon=True).start()

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
        data, _ = self.load_projects()
        if data["projectsSource"] != "registry":
            return started
        night = now.hour >= 22 or now.hour < 6
        live = self._live_keys()
        tools = {"claude": self.tool_found("claude"), "codex": self.tool_found("codex")}
        for t in data["tasks"]:
            if free <= 0:
                break
            if t["state"] != "todo" or t["executor"] not in ("claude", "codex") or t["machine"] != self.machine:
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
    if task.get("needsYou") == "zgoda":
        return "Czeka na Twoją zgodę"
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
