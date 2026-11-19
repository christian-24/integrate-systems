"""Wspólne przygotowanie testów: projekt w katalogu tymczasowym, tymczasowy rejestr, zarządca na atrapach.

Testy niczego nie zapisują w folderze IntegrateSystems: rejestr, uruchomienia i notatki są w katalogu tymczasowym.
"""
import contextlib
import datetime
import io
import json
import os
import shutil
import sys
import tempfile
import time
import unittest

TESTY = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(TESTY))
import server  # noqa: E402
import agents  # noqa: E402
import projekt  # noqa: E402

ATRAPA_CLAUDE = os.path.join(TESTY, "atrapa_claude.py")
ATRAPA_CODEX = os.path.join(TESTY, "atrapa_codex.py")
ENV_KEYS = ("STAN_DIR", "LOKALNE_DIR", "PANEL_HISTORY_DIR", "PANEL_ZDROWIE_STAN", "PANEL_KOPIA_STAN", "PANEL_RUNS_DIR",
            "PANEL_AGENT_USER", "PANEL_DZIEN_MIN")
# Ustawienia z panel.env tego komputera, które zmieniają dostęp i polecenia: w testach wyłączone.
CLEARED = ("PANEL_AGENT_USER", "PANEL_DZIEN_MIN")
TODAY = datetime.date.today().isoformat()
TOMORROW = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()

ZADANIA = """# Zadania: Projekt testowy

## Etap: Pierwszy
termin: %(tomorrow)s

- [ ] Zadanie A | kto: claude
- [ ] Zadanie B
- [ ] Zadanie C | kto: codex
- [ ] Zadanie D | kto: ty
- [ ] Zadanie E | wymaga: zgoda
- [x] Zadanie F
- [ ] Auto dziś | kto: claude | gdzie: mac | kiedy: %(today)s
- [ ] Auto inny węzeł | kto: claude | gdzie: pc | kiedy: %(today)s
- [ ] Auto jutro | kto: claude | gdzie: mac | kiedy: %(tomorrow)s
- [ ] Auto noc | kto: claude | gdzie: mac | kiedy: %(today)s | pora: noc
- [ ] Auto bez daty | kto: claude | gdzie: mac

## Do rozplanowania
""" % {"today": TODAY, "tomorrow": TOMORROW}


def quiet(fn, *args, **kw):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*args, **kw)


class Baza(unittest.TestCase):
    """Katalog tymczasowy z jednym projektem w rejestrze i zarządcą uruchomień na atrapach."""
    registered = True

    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp(prefix="panel-test-"))
        self.root = os.path.join(self.tmp, "korzen")            # zastępuje folder IntegrateSystems
        self.runs = os.path.join(self.tmp, "uruchomienia")
        self.notes = os.path.join(self.root, "raporty")
        self.folder = os.path.join(self.tmp, "projekt-testowy")
        os.makedirs(self.notes)
        self._registry = projekt.REGISTRY
        projekt.REGISTRY = os.path.join(self.tmp, "projekty.json")
        # Zbieracz i historia tylko w katalogu tymczasowym (nigdy ~/stan-systemu ani ../historia).
        self.stan = os.path.join(self.tmp, "stan")
        self.lokalne = os.path.join(self.tmp, "lokalne")
        self.history_dir = os.path.join(self.tmp, "historia")
        self._environ = {k: os.environ.get(k) for k in ENV_KEYS}
        # Stan serwera (zdrowie, kopia) i uruchomienia czytane przez pm.py też tylko z katalogu tymczasowego.
        self.health_file = os.path.join(self.tmp, "zdrowie-stan")
        self.backup_file = os.path.join(self.tmp, "kopie", "ostatnia.json")
        os.environ.update({"STAN_DIR": self.stan, "LOKALNE_DIR": self.lokalne, "PANEL_HISTORY_DIR": self.history_dir,
                           "PANEL_ZDROWIE_STAN": self.health_file, "PANEL_KOPIA_STAN": self.backup_file,
                           "PANEL_RUNS_DIR": self.runs})
        for k in CLEARED:
            os.environ.pop(k, None)
        quiet(projekt.cmd_nowy, self.folder, "Projekt testowy", register=self.registered)
        with open(os.path.join(self.folder, "ZADANIA.md"), "w", encoding="utf-8") as f:
            f.write(ZADANIA)
        self.mode_file = os.path.join(self.tmp, "tryb")
        self.journal = os.path.join(self.tmp, "dziennik.jsonl")
        self.pid_file = os.path.join(self.tmp, "pid")
        self.managers = []
        self._server_state = (server._agents, server.TOKEN, server.LOCAL_KEY_FILE)
        server.LOCAL_KEY_FILE = ""          # zapis z loopback bez klucza (Mac); testy klucza ustawiają go same
        self.manager = self.new_manager()
        server._agents = self.manager
        # /api/data bez pamięci podręcznej: testy zmieniają pliki i od razu czytają dane (test pamięci: test_teraz)
        self._data_ttl = server.DATA_TTL
        server.DATA_TTL = 0
        server.data_invalidate()

    def tearDown(self):
        for m in self.managers:
            m.shutdown()
        server._agents, server.TOKEN, server.LOCAL_KEY_FILE = self._server_state
        server.DATA_TTL = self._data_ttl
        server.data_invalidate()
        projekt.REGISTRY = self._registry
        for k, v in self._environ.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.tmp, ignore_errors=True)

    def env(self, **extra):
        env = dict(os.environ)
        env.update({"PANEL_CLAUDE": ATRAPA_CLAUDE, "PANEL_CODEX": ATRAPA_CODEX, "PANEL_MACHINE": "mac",
                    "PANEL_AGENTS_MAX": "2", "PANEL_AGENT_TIMEOUT": "30", "PANEL_PM_HOUR": "7", "PANEL_GIT_PULL": "0",
                    "PANEL_NTFY_URL": "", "PANEL_AGENT_MODEL": "", "PANEL_PM_MODEL": "", "PANEL_RUNS_DIR": "",
                    "ATRAPA_TRYB_PLIK": self.mode_file, "ATRAPA_DZIENNIK": self.journal, "ATRAPA_PID_PLIK": self.pid_file,
                    "ANTHROPIC_API_KEY": "klucz-testowy", "OPENAI_API_KEY": "klucz-testowy",
                    "PANEL_TOKEN": "haslo-testowe", "CLAUDECODE": "1", "CLAUDE_CODE_OAUTH_TOKEN": "token-testowy",
                    "PANEL_AGENT_USER": "", "PANEL_AGENT_WORKTREE": "1"})
        env.update(extra)
        return env

    def new_manager(self, **extra):
        m = agents.Manager(server.load_projects, server._write_lock, projekt, env=self.env(**extra),
                           runs_dir=self.runs, root=self.root, notes_dir=self.notes)
        self.managers.append(m)
        return m

    # ---------- pomocnicze ----------
    def set_mode(self, mode):
        with open(self.mode_file, "w", encoding="utf-8") as f:
            f.write(mode)

    def task(self, title):
        data, _ = server.load_projects()
        return next(t for t in data["tasks"] if t["title"] == title)

    def row(self, title):
        with open(os.path.join(self.folder, "ZADANIA.md"), encoding="utf-8") as f:
            return next(line for line in f.read().split("\n") if title in line)

    def run_task(self, title, manager=None):
        t = self.task(title)
        return (manager or self.manager).run_task(t["id"], t["title"])

    def wait(self, rid, states=("done", "error", "login", "limit", "stopped", "timeout"), timeout=15, manager=None):
        end = time.time() + timeout
        while time.time() < end:
            rec = (manager or self.manager).get(rid)
            if rec and rec["state"] in states:
                return rec
            time.sleep(0.03)
        self.fail("Uruchomienie %s nie doszło do stanu %s: %s" % (rid, states, (manager or self.manager).get(rid)))

    def wait_for(self, check, timeout=10):
        end = time.time() + timeout
        while time.time() < end:
            if check():
                return True
            time.sleep(0.03)
        self.fail("Warunek nie został spełniony w czasie %s s" % timeout)

    def collector(self, folders):
        """Pliki zbieracza: {folder: decyzja bez czasu i tożsamości} -> aliasy.json i mac/decyzje.jsonl."""
        os.makedirs(os.path.join(self.stan, "mac"), exist_ok=True)
        os.makedirs(self.lokalne, exist_ok=True)
        aliases, rows = {}, []
        for i, (folder, decision) in enumerate(folders.items()):
            ident = "%012x" % (i + 1)
            aliases[ident] = {"nazwa": os.path.basename(folder), "sciezka": folder, "zdalne": None}
            for j, d in enumerate(decision if isinstance(decision, list) else [decision]):
                row = {"czas": "2026-11-0%dT10:00:00+01:00" % (j + 1), "tozsamosc": ident, "alias": "K-%04d" % i,
                       "klient": True, "scalony_z": None}
                row.update(d)
                rows.append(row)
        with open(os.path.join(self.lokalne, "aliasy.json"), "w", encoding="utf-8") as f:
            json.dump(aliases, f)
        with open(os.path.join(self.stan, "mac", "decyzje.jsonl"), "w", encoding="utf-8") as f:
            f.write("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))

    def calls(self):
        if not os.path.exists(self.journal):
            return []
        with open(self.journal, encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]
