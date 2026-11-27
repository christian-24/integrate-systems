"""Praca agenta na żywo (AGENCI.md, „Wiadomość w trakcie pracy”, „Podgląd pracy na żywo”): wiadomość właściciela na
stdin pracującego Claude (stream-json), zamknięcie stdin po result, wiadomość po result jako poprawka i ponowne
uruchomienie, Zatrzymaj, Codex z poprawką i „Zatrzymaj i uruchom z poprawką”, przebieg w rekordzie, zrzuty strony
(bez wychodzenia poza .zrzuty/), uwaga z zakładki Strona do pracującego agenta, reguły z `strona build:`, start od
gałęzi poprzedniego uruchomienia. Atrapy: atrapa_claude.py, atrapa_codex.py (bez prawdziwego Claude i sieci)."""
import http.client
import json
import os
import re
import shutil
import subprocess
import time
import unittest

from test_serwer import Serwer
from test_strona import IDENT, Strona
from wspolne import agents, server

import strona

GIT = shutil.which("git")


def matches(rules, command):
    """Uproszczone sprawdzenie uprawnień jak w Claude Code: każdy człon `&&` musi pasować do reguły dokładnej
    `Bash(polecenie)` albo z prefiksem `Bash(polecenie:*)` (polecenie, potem spacja albo koniec)."""
    exact = {r[5:-1] for r in rules if r.startswith("Bash(") and not r.endswith(":*)")}
    prefix = [r[5:-3] for r in rules if r.startswith("Bash(") and r.endswith(":*)")]
    for part in command.split("&&"):
        part = " ".join(part.split())
        if part not in exact and not any(part == p or part.startswith(p + " ") for p in prefix):
            return False
    return True


class Wspolne(Serwer):
    def setUp(self):
        super().setUp()
        self.wait_file = os.path.join(self.tmp, "czeka")
        self.eof_file = os.path.join(self.tmp, "eof")
        os.environ["ATRAPA_CZEKA_PLIK"] = self.wait_file
        os.environ["ATRAPA_EOF_PLIK"] = self.eof_file
        self.manager.shutdown()
        self.manager = self.new_manager(ATRAPA_CZEKA_PLIK=self.wait_file, ATRAPA_EOF_PLIK=self.eof_file)
        server._agents = self.manager

    def tearDown(self):
        os.environ.pop("ATRAPA_CZEKA_PLIK", None)
        os.environ.pop("ATRAPA_EOF_PLIK", None)
        super().tearDown()

    def say(self, title, text):
        """„Wyślij do agenta” z Rozmowy w projekcie z odnośnikiem do zadania (POST /api/project/chat, task, execute)."""
        t = self.task(title)
        status, answer = self.post("/api/project/chat", {"project": t["project"], "task": t["id"], "message": text,
                                                         "execute": True})
        self.assertEqual(status, 200, answer)
        return answer["status"]

    def start(self, title, mode):
        self.set_mode(mode)
        code, err, extra = self.run_task(title)
        self.assertEqual(code, 200, err)
        return extra["id"]

    def runs_of(self, title):
        with self.manager._lock:
            return [dict(r) for r in self.manager._runs.values() if r.get("title") == title]

    def log(self, rid):
        status, _, text = self.request("GET", "/api/agent/przebieg?id=%s&od=0" % rid)
        self.assertEqual(status, 200, text)
        return json.loads(text)

    def eofs(self):
        if not os.path.exists(self.eof_file):
            return []
        with open(self.eof_file, encoding="utf-8") as f:
            return f.read().split()


class Wiadomosc(Wspolne):
    def test_wiadomosc_trafia_na_stdin_i_zostaje_przy_zadaniu(self):
        rid = self.start("Zadanie A", "na-zywo")
        self.wait_for(lambda: os.path.exists(self.wait_file))
        self.assertTrue(self.log(rid)["takesMsg"])
        status = self.say("Zadanie A", "Nagłówek ma być granatowy")
        self.assertEqual(status["text"], "Przekazano agentowi.")
        self.assertTrue(status["delivered"])
        self.assertEqual(status["runId"], rid)
        rec = self.wait(rid)
        self.assertEqual(rec["state"], "done", rec)
        self.assertIn({"live": "Nagłówek ma być granatowy"}, [{k: c[k] for k in c if k == "live"} for c in self.calls()])
        self.assertEqual(self.eofs(), ["eof"])                          # stdin zamknięty po result
        with open(os.path.join(self.folder, "ZADANIA.md"), encoding="utf-8") as f:
            text = f.read()
        self.assertIn("  poprawka: Nagłówek ma być granatowy", text)   # następne uruchomienie też zna polecenie
        self.assertEqual(rec["fix"], "Nagłówek ma być granatowy")       # Automat nie powtarza tego uruchomienia
        log = self.log(rid)
        kinds = [(x["k"], x["text"]) for x in log["items"]]
        self.assertIn(("ty", "Nagłówek ma być granatowy"), kinds)
        self.assertIn(("agent", "Uwzględniam wiadomość: Nagłówek ma być granatowy"), kinds)
        self.assertIn(("narzedzie", "Read: ZADANIA.md"), kinds)
        self.assertTrue(all(re.match(r"^\d\d:\d\d:\d\d$", x["t"]) for x in log["items"]))
        self.assertFalse(log["takesMsg"])
        with open(os.path.join(self.runs, rid + ".json"), encoding="utf-8") as f:
            saved = json.load(f)
        self.assertEqual(saved["logN"], log["next"])                    # przebieg w zapisie uruchomienia
        # przyrostowo: od ostatniego numeru nic nowego
        status, _, text = self.request("GET", "/api/agent/przebieg?id=%s&od=%d" % (rid, log["next"]))
        self.assertEqual(json.loads(text)["items"], [])
        # /api/data bez pełnego przebiegu
        run = next(r for r in self.manager.snapshot()["runs"] if r["id"] == rid)
        self.assertNotIn("log", run)
        self.assertEqual(run["logN"], log["next"])
        # rozmowa: wiadomość właściciela i odpowiedź panelu zostają
        status, _, text = self.request("GET", "/api/project/chat?project=" + self.task("Zadanie A")["project"])
        msgs = json.loads(text)["messages"]
        self.assertEqual([m.get("text") for m in msgs][-2:], ["Nagłówek ma być granatowy", "Przekazano agentowi."])

    def test_stdin_zamkniety_po_result(self):
        rid = self.start("Zadanie A", "ok")
        rec = self.wait(rid, timeout=10)                 # atrapa czeka na koniec wejścia: bez zamknięcia nie kończy
        self.assertEqual(rec["state"], "done")
        self.assertEqual(self.eofs(), ["eof"])
        call = next(c for c in self.calls() if c.get("prompt"))
        self.assertIn("--input-format", call["argv"])
        self.assertIn("z pliku ZADANIA.md, wiersz", call["prompt"])

    def test_wiadomosc_po_result_zapisana_i_uruchomiona_ponownie(self):
        rid = self.start("Zadanie A", "po-wyniku")
        self.wait_for(lambda: (self.manager._priv.get(rid) or {}).get("ended"))
        self.set_mode("ok")
        status = self.say("Zadanie A", "Dopisz jeszcze stopkę")
        self.assertTrue(status["text"].startswith("Agent skończył, polecenie zapisane jako poprawka"), status)
        self.assertEqual(self.wait(rid)["state"], "done")
        self.wait_for(lambda: len(self.runs_of("Zadanie A")) == 2, timeout=10)
        again = next(r for r in self.runs_of("Zadanie A") if r["id"] != rid)
        self.assertEqual(self.wait(again["id"])["state"], "done")
        call = [c for c in self.calls() if c.get("prompt")][-1]
        self.assertIn("Poprawka od właściciela (wiersz poprawka:): Dopisz jeszcze stopkę", call["prompt"])
        status, _, text = self.request("GET", "/api/project/chat?project=" + self.task("Zadanie A")["project"])
        texts = [m.get("text") for m in json.loads(text)["messages"]]
        self.assertIn("Uruchomiono: Zadanie A", texts)

    def test_nieodczytana_wiadomosc_po_result(self):
        self.manager.GRACE = 0.3
        rid = self.start("Zadanie A", "ignoruje")
        self.wait_for(lambda: os.path.exists(self.wait_file))
        self.assertEqual(self.say("Zadanie A", "Zmień kolor")["text"], "Przekazano agentowi.")
        self.set_mode("ok")
        self.assertEqual(self.wait(rid)["state"], "done")
        texts = [x["text"] for x in self.log(rid)["items"]]
        self.assertTrue(any(t.startswith("Agent skończył przed odczytaniem wiadomości") for t in texts), texts)
        self.wait_for(lambda: len(self.runs_of("Zadanie A")) == 2, timeout=10)

    def test_zatrzymaj_dziala(self):
        rid = self.start("Zadanie A", "wolno")
        self.wait_for(lambda: (self.manager._priv.get(rid) or {}).get("open"))
        self.assertEqual(self.say("Zadanie A", "Jeszcze to")["text"], "Przekazano agentowi.")
        status, answer = self.post("/api/agent/stop", {"id": rid})
        self.assertEqual(status, 200, answer)
        rec = self.wait(rid)
        self.assertEqual(rec["state"], "stopped")
        time.sleep(0.3)
        self.assertEqual(len(self.runs_of("Zadanie A")), 1)            # zatrzymane: bez ponownego uruchomienia

    def test_bezpiecznik_przy_wejsciu_stream(self):
        rid = self.start("Zadanie A", "wolno")
        self.wait_for(lambda: (self.manager._priv.get(rid) or {}).get("open"))
        rec = self.manager._runs[rid]
        ev = lambda u: {"type": "rate_limit_event", "rate_limit_info": {"status": "allowed", "rateLimitType": "five_hour",  # noqa: E731
                        "unifiedWindows": {"five_hour": {"utilization": u}}}}
        self.manager._on_claude(rec, ev(0.10), {"rate": None, "limit": False}, self.folder)
        self.manager._on_claude(rec, ev(0.40), {"rate": None, "limit": False}, self.folder)
        done = self.wait(rid)
        self.assertEqual(done["state"], "stopped")
        self.assertIn("limitu 5 godzin", done["error"])

    def test_wiadomosc_do_zadania_w_kolejce(self):
        self.manager.max_parallel = 0
        rid = self.start("Zadanie A", "ok")
        self.assertEqual(self.manager.get(rid)["state"], "queued")
        status = self.say("Zadanie A", "Najpierw sprawdź kartę")
        self.assertIn("polecenie dołączone do zadania", status["text"])
        self.assertIn("Poprawka od właściciela (wiersz poprawka:): Najpierw sprawdź kartę",
                      self.manager._priv[rid]["prompt"])
        self.manager.max_parallel = 2
        self.manager._pump()
        self.assertEqual(self.wait(rid)["state"], "done")

    def test_przebieg_odmowy_dlugi_tekst_limit(self):
        rid = self.start("Zadanie A", "odmowa-w-trakcie")
        self.wait(rid)
        items = self.log(rid)["items"]
        self.assertIn(("odmowa", "Bash: npm publish"), [(x["k"], x["text"]) for x in items])
        rid = self.start("Auto dziś", "dlugi-tekst")
        self.wait(rid)
        long = next(x for x in self.log(rid)["items"] if x["k"] == "agent" and x["text"].startswith("Początek."))
        self.assertEqual(len(long["text"]), agents.LOG_TEXT + 1)       # przycięta wypowiedź z „…”
        rec = {"id": "x", "log": [], "logN": 0}
        for i in range(agents.LOG_KEEP + 50):
            self.manager._log(rec, "agent", "wiersz %d" % i)
        self.assertEqual(len(rec["log"]), agents.LOG_KEEP)
        self.assertEqual(rec["log"][0]["n"], 51)
        self.manager._log(rec, "agent", "y" * 9000)
        self.assertEqual(len(rec["log"][-1]["text"]), agents.LOG_TEXT + 1)

    def test_nieznane_uruchomienie(self):
        status, _, text = self.request("GET", "/api/agent/przebieg?id=brak")
        self.assertEqual(status, 404)
        status, _, _ = self.request("GET", "/api/agent/zrzut?id=brak&plik=telefon.png")
        self.assertEqual(status, 404)


class Codex(Wspolne):
    def test_codex_dostaje_poprawke_i_restart(self):
        rid = self.start("Zadanie C", "wolno")
        self.wait_for(lambda: (self.manager._priv.get(rid) or {}).get("proc") is not None)
        status = self.say("Zadanie C", "Użyj krótszych zdań")
        self.assertIn("Codex nie przyjmuje wiadomości", status["text"])
        self.assertEqual(status["restart"], rid)
        with open(os.path.join(self.folder, "ZADANIA.md"), encoding="utf-8") as f:
            self.assertIn("  poprawka: Użyj krótszych zdań", f.read())
        self.assertFalse((self.manager._priv.get(rid) or {}).get("stream"))
        self.set_mode("ok")
        st, answer = self.post("/api/agent/restart", {"id": rid})
        self.assertEqual(st, 200, answer)
        self.assertEqual(self.wait(rid)["state"], "stopped")
        self.wait_for(lambda: len(self.runs_of("Zadanie C")) == 2, timeout=30)
        again = next(r for r in self.runs_of("Zadanie C") if r["id"] != rid)
        self.assertEqual(self.wait(again["id"])["state"], "done")
        call = [c for c in self.calls() if c.get("prompt")][-1]
        self.assertIn("Użyj krótszych zdań", call["prompt"])


class Reguly(unittest.TestCase):
    def test_reguly_z_karty(self):
        rules, cmds, skipped = strona.build_rules("npm ci && npm run build:panel")
        self.assertEqual(cmds, ["npm ci", "npm run build:panel"])
        self.assertEqual(skipped, [])
        self.assertEqual(rules, ["Bash(npm ci)", "Bash(npm ci:*)", "Bash(npm run build:panel)",
                                 "Bash(npm run build:panel:*)"])
        self.assertNotIn("Bash", rules)
        for cmd in ("npm ci && npm run build:panel", "npm ci --prefix /p/site && npm run build:panel --prefix /p/site",
                    "npm run build:panel -- --base=./"):
            self.assertTrue(matches(rules, cmd), cmd)
        self.assertFalse(matches(["Bash(npm run build:*)"], "npm run build:panel"))   # stara reguła nie przepuszczała
        for cmd in ("npm run build", "npm ci && rm -rf /", "npm publish"):
            self.assertFalse(matches(rules, cmd), cmd)

    def test_inne_czlony_pominiete(self):
        rules, cmds, skipped = strona.build_rules(
            "cd web && npm --prefix web install && npm run build -- --base=./ && npx vite build ; npm run x | tee log && "
            "npm run $(whoami) && npm install left-pad")
        self.assertEqual(cmds, ["npm install", "npm run build"])
        self.assertEqual(skipped, ["cd web", "npx vite build", "npm run x | tee log", "npm run $(whoami)",
                                   "npm install left-pad"])
        self.assertFalse([r for r in rules if r in ("Bash", "Bash(*)") or "npx" in r or "cd " in r])

    def test_polecenie_dla_agenta_podaje_te_polecenia(self):
        site = {"dir": "site", "build": "npm ci && npm run build:panel", "out": "dist", "customBuild": True,
                "shot": "python3 zrzut.py"}
        text = "\n".join(strona.Site.rules(site, "/r"))
        self.assertIn("`npm ci && npm run build:panel`", text)
        self.assertIn("`npm ci`, `npm run build:panel`", text)
        tools = strona.Site.tools(None, site)
        self.assertEqual(tools, ["Bash(npm ci)", "Bash(npm ci:*)", "Bash(npm run build:panel)",
                                 "Bash(npm run build:panel:*)", "Bash(python3 zrzut.py:*)",
                                 "Bash(git merge:*)"])
        site.update(build="make all && npm ci")
        text = "\n".join(strona.Site.rules(site, "/r"))
        self.assertIn("nie uruchamiaj (brak uprawnienia): `make all`", text)
        site.update(build="npm run build", customBuild=False)
        self.assertIn("Bash(npm run build:*)", strona.Site.tools(None, site))

    def test_codex_zaleznosci_instaluje_panel(self):
        """Piaskownica Codexa bez sieci blokuje spawnSync z potokami (npm ci → esbuild EPERM): npm ci robi panel."""
        import tempfile, types
        site = {"dir": "site", "build": "npm ci && npm run build:panel", "out": "dist", "customBuild": True,
                "shot": "python3 zrzut.py"}
        self.assertIn("Nie uruchamiaj `npm ci`", "\n".join(strona.Site.rules(site, "/r", "codex")))
        self.assertNotIn("Nie uruchamiaj `npm ci`", "\n".join(strona.Site.rules(site, "/r")))
        with tempfile.TemporaryDirectory() as d:
            sdir = os.path.join(d, "site")
            os.makedirs(sdir)
            fake = types.SimpleNamespace(m=types.SimpleNamespace(env={}), build_timeout=30,
                                         _build_args=lambda folder, cmd: ["/bin/sh", "-c", "echo %s > ran.txt" % cmd])
            self.assertEqual(strona.Site.install_deps(fake, d, site), (None, ""))       # bez package.json
            open(os.path.join(sdir, "package.json"), "w").write("{}")
            open(os.path.join(sdir, "package-lock.json"), "w").write("{}")
            self.assertEqual(strona.Site.install_deps(fake, d, site), (True, "npm ci"))
            self.assertEqual(open(os.path.join(sdir, "ran.txt")).read().strip(), "npm ci")
            os.makedirs(os.path.join(sdir, "node_modules"))
            self.assertEqual(strona.Site.install_deps(fake, d, site), (None, ""))       # już zainstalowane
            fake._build_args = lambda folder, cmd: ["/bin/sh", "-c", "echo blad; exit 3"]
            os.rmdir(os.path.join(sdir, "node_modules"))
            self.assertEqual(strona.Site.install_deps(fake, d, site), (False, "npm ci: kod 3: blad"))


@unittest.skipUnless(GIT, "brak git")
class Galaz(Wspolne):
    def setUp(self):
        super().setUp()
        self.git("init", "-q")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "start")

    def git(self, *args):
        return subprocess.run(["git"] + IDENT + list(args), cwd=self.folder, check=True, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, encoding="utf-8").stdout.strip()

    def reopen(self, title, extra=""):
        path = os.path.join(self.folder, "ZADANIA.md")
        with open(path, encoding="utf-8") as f:
            lines = f.read().split("\n")
        i = next(n for n, line in enumerate(lines) if title in line)
        lines[i] = re.sub(r"^- \[.\]", "- [ ]", lines[i])
        lines.insert(i + 1, "  poprawka: Dokończ" + extra)
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        server.data_invalidate()

    def test_start_od_galezi_poprzedniego_uruchomienia(self):
        first = self.wait(self.start("Zadanie A", "commit"))
        self.assertEqual(first["state"], "done", first)
        self.assertGreaterEqual(first["commits"], 1)
        self.reopen("Zadanie A")
        second = self.wait(self.start("Zadanie A", "ok"))
        self.assertEqual(second["branch"], first["branch"])
        self.assertTrue(second.get("resumed"))
        self.assertTrue(any("Dalej na gałęzi" in s["text"] for s in second["steps"]), second["steps"])
        prompt = [c for c in self.calls() if c.get("prompt")][-1]["prompt"]
        self.assertIn("ma już commity z poprzedniej pracy", prompt)
        self.assertEqual(second["baseCommit"], self.git("rev-parse", "HEAD"))
        self.assertGreaterEqual(len(second["changes"]), 1)              # zmiany całej gałęzi agenta

    def test_start_od_galezi_z_pola(self):
        self.git("switch", "-q", "-c", "agent/2026-11-23-reczna")
        with open(os.path.join(self.folder, "plik.txt"), "w") as f:
            f.write("x")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "praca")
        self.git("switch", "-q", "-")
        self.reopen("Zadanie A", "\n  gałąź: agent/2026-11-23-reczna")
        rec = self.wait(self.start("Zadanie A", "ok"))
        self.assertEqual(rec["branch"], "agent/2026-11-23-reczna")

    def test_scalona_galaz_nowy_start(self):
        first = self.wait(self.start("Zadanie A", "commit"))
        self.git("merge", "-q", "--no-ff", "-m", "scalenie", first["branch"])
        self.reopen("Zadanie A")
        second = self.wait(self.start("Zadanie A", "ok"))
        self.assertNotEqual(second["branch"], first["branch"])
        self.assertFalse(second.get("resumed"))


class StronaNaZywo(Strona):
    def raw(self, path):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=15)
        try:
            conn.request("GET", path)
            resp = conn.getresponse()
            return resp.status, dict(resp.getheaders()), resp.read()
        finally:
            conn.close()

    def setUp(self):
        super().setUp()
        self.wait_file = os.path.join(self.tmp, "czeka")
        self.manager.shutdown()
        self.manager = self.new_manager(ATRAPA_CZEKA_PLIK=self.wait_file)
        server._agents = self.manager
        self.site = self.manager.site

    def test_zrzuty_i_uwaga_do_pracujacego_agenta(self):
        self.set_mode("zrzuty")
        status, answer = self.post("/api/strona/uwaga", {"project": self.pid, "text": "Większy nagłówek",
                                                         "view": "telefon"})
        self.assertEqual(status, 200, answer)
        rid, title = answer["runId"], answer["note"]["title"]
        self.wait_for(lambda: os.path.exists(self.wait_file))
        status, _, text = self.request("GET", "/api/agent/przebieg?id=%s" % rid)
        shots = json.loads(text)["shots"]
        self.assertEqual(sorted(s["name"] for s in shots), ["komputer.png", "telefon.png"])
        status, headers, body = self.raw("/api/agent/zrzut?id=%s&plik=telefon.png" % rid)
        self.assertEqual((status, headers["Content-Type"]), (200, "image/png"))
        self.assertTrue(body.startswith(b"\x89PNG"))
        shot_dir = os.path.join(self.folder, ".zrzuty")
        os.symlink(os.path.join(self.folder, "KARTA.md"), os.path.join(shot_dir, "zly.png"))
        for name in ("../KARTA.md", "..%2FKARTA.md", "notatka.txt", "zly.png", "brak.png", "%2Fetc%2Fpasswd"):
            status, _, _ = self.raw("/api/agent/zrzut?id=%s&plik=%s" % (rid, name))
            self.assertEqual(status, 404, name)
        # druga uwaga przy pracującym agencie strony idzie do niego, bez nowego zadania
        status, second = self.post("/api/strona/uwaga", {"project": self.pid, "text": "Krótszy tekst",
                                                         "view": "komputer", "selector": "#tytul"})
        self.assertEqual(status, 200, second)
        self.assertEqual(second["runId"], rid)
        self.assertEqual(second["note"]["title"], title)
        self.assertEqual(second["forwarded"], "Przekazano agentowi.")
        rec = self.wait(rid, timeout=30)
        self.assertEqual(rec["state"], "done", rec)
        self.assertIn(("ty", "Uwaga do strony: Krótszy tekst (Podstrona /, widok komputer (1440 px). Element: #tytul)"),
                      [(x["k"], x["text"]) for x in rec["log"]])
        with open(os.path.join(self.folder, "ZADANIA.md"), encoding="utf-8") as f:
            text = f.read()
        self.assertIn("poprawka: Uwaga do strony: Krótszy tekst", text)
        self.assertEqual(sum(1 for line in text.split("\n") if line.startswith("- [") and "Strona:" in line), 1)


if __name__ == "__main__":
    unittest.main()
