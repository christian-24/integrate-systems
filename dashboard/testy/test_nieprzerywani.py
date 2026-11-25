"""Zlecenie „agenci nieprzerywani” (2026-11-25): uruchomienie przeżywa restart panelu (pośrednik przebieg.py),
dokończenie przerwanego zadania (z commitem i bez), zadanie projektu z częściami we własnym katalogu roboczym części,
zatwierdzenie i odłożenie zmian niezatwierdzonych, praca równoległa (różne projekty tak, ten sam nie), budowa strony
na żywo w zakładce Strona, przeglądarka MCP w poleceniu zadania strony, jednorazowa naprawa i czekanie na wdrożenie.
"""
import datetime
import json
import os
import signal
import subprocess
import time
import unittest
import urllib.request
from unittest import mock

from test_strona import GIT, IDENT, Strona
from wspolne import Baza, agents, projekt, quiet, server

import naprawy  # noqa: E402  (ścieżki ustawia wspolne.py)


def git(cwd, *args):
    return subprocess.run(["git"] + IDENT + list(args), cwd=cwd, check=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, encoding="utf-8").stdout.strip()


def repo(folder):
    git(folder, "init", "-q", "-b", "main")
    git(folder, "add", "-A")
    git(folder, "commit", "-q", "-m", "start")


class Restart(Baza):
    def setUp(self):
        super().setUp()
        self.waiting = os.path.join(self.tmp, "czeka")
        self.go = os.path.join(self.tmp, "dalej")

    def manager2(self, **kw):
        return self.new_manager(ATRAPA_CZEKA_PLIK=self.waiting, ATRAPA_DALEJ_PLIK=self.go, **kw)

    def start_waiting(self, mode="czekaj"):
        self.set_mode(mode)
        m = self.manager2()
        code, err, extra = self.run_task("Zadanie A", m)
        self.assertEqual(code, 200, err)
        self.wait_for(lambda: os.path.exists(self.waiting), timeout=15)
        return m, extra["id"]

    def test_przezywa_restart_panelu(self):
        m1, rid = self.start_waiting()
        runner = m1.get(rid)["runner"]["pid"]
        m1.shutdown(keep=True)                       # panel kończy pracę (SIGTERM usługi z KillMode=process)
        self.assertTrue(agents.pid_alive(runner, rid))
        with open(os.path.join(self.runs, rid + ".json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["state"], "running")
        m2 = self.manager2()                          # nowy panel podejmuje śledzenie
        m2.start()
        self.assertEqual(m2.get(rid)["state"], "running")
        open(self.go, "w").close()
        rec = self.wait(rid, manager=m2, timeout=20)
        self.assertEqual(rec["state"], "done", rec.get("error"))
        self.assertTrue(self.row("Zadanie A").startswith("- [x] Zadanie A"))
        texts = [x["text"] for x in rec.get("log") or []]
        self.assertIn("Panel uruchomił się ponownie; agent pracował dalej.", texts)
        self.assertEqual(sum(1 for t in texts if t.startswith("Write:")), 1)   # zdarzenia bez powtórzeń
        self.assertFalse(agents.pid_alive(runner, rid))

    def test_bez_posrednika_jak_dotad(self):
        self.set_mode("ok")
        m = self.new_manager(PANEL_PRZEBIEG="0")
        rec = self.wait(self.run_task("Zadanie A", m)[2]["id"], manager=m)
        self.assertEqual(rec["state"], "done")
        self.assertNotIn("runner", rec)

    def kill_hard(self, m, rid):
        """Panel i agent zabici (dawna usługa bez KillMode=process): bez zapisu końca."""
        runner = m.get(rid)["runner"]["pid"]
        m.shutdown(keep=True)
        os.killpg(runner, signal.SIGKILL)
        self.wait_for(lambda: not agents.pid_alive(runner, rid), timeout=10)

    @unittest.skipUnless(GIT, "brak polecenia git")
    def test_przerwane_z_commitem_konczy_zadanie(self):
        repo(self.folder)
        m1, rid = self.start_waiting("czekaj-commit")
        self.kill_hard(m1, rid)
        m2 = self.manager2()
        m2.start()
        rec = self.wait(rid, manager=m2)
        self.assertEqual((rec["state"], rec.get("recovered")), ("done", "commit"))
        self.assertIn("wymaga: odbiór", self.row("Zadanie A"))       # jak po zwykłym końcu
        self.assertEqual(git(self.folder, "log", "-1", "--format=%s", rec["branch"]), "Praca agenta")
        self.assertFalse(os.path.exists(os.path.join(self.folder, ".agent", rid)))

    @unittest.skipUnless(GIT, "brak polecenia git")
    def test_przerwane_bez_commita_wznawia_od_galezi(self):
        repo(self.folder)
        m1, rid = self.start_waiting("czekaj")
        self.kill_hard(m1, rid)
        self.set_mode("ok")
        m2 = self.manager2()
        m2.start()
        rec = self.wait(rid, manager=m2)
        self.assertEqual((rec["state"], rec.get("recovered")), ("stopped", "restart"))
        self.assertIn("uruchomi się ponownie", rec["error"])
        self.wait_for(lambda: any(r.get("recoveredFrom") == rid for r in m2._runs.values()), timeout=15)
        new = next(r for r in m2._runs.values() if r.get("recoveredFrom") == rid)
        new = self.wait(new["id"], manager=m2)
        self.assertEqual(new["state"], "done")
        self.assertTrue(new.get("resumed"))                         # dalej na gałęzi przerwanej pracy
        self.assertEqual(new["branch"], rec["branch"])
        prompt = [c for c in self.calls() if "Zadanie A" in (c.get("prompt") or "")][-1]["prompt"]
        self.assertIn("przerwał restart panelu", prompt)
        task = self.task("Zadanie A")
        self.assertIn("przerwał restart panelu", task["detail"]["fix"])


@unittest.skipUnless(GIT, "brak polecenia git")
class Czesci(Baza):
    def setUp(self):
        super().setUp()
        self.part = os.path.join(self.tmp, "strona-czesc")
        quiet(projekt.cmd_nowy, self.part, "Projekt testowy · Strona", register=True)
        main_id = next(p["id"] for p in server.load_projects()[0]["projects"] if p["name"] == "Projekt testowy")
        path = os.path.join(self.part, "KARTA.md")
        with open(path, encoding="utf-8") as f:
            head, _, rest = f.read().partition("\n")
        with open(path, "w", encoding="utf-8") as f:
            f.write(head + "\n\n- część projektu: %s\n" % main_id + rest)
        repo(self.part)
        server.data_invalidate()

    def test_zadanie_glowne_pisze_w_katalogu_czesci(self):
        self.set_mode("czesc")
        m = self.new_manager()
        rec = self.wait(self.run_task("Zadanie A", m)[2]["id"], manager=m)
        self.assertEqual(rec["state"], "done", rec.get("error"))
        call = [c for c in self.calls() if "Zadanie A" in (c.get("prompt") or "")][-1]
        wt = os.path.join(self.part, ".agent", rec["id"])
        args = call["argv"]
        self.assertIn(wt, [args[i + 1] for i, a in enumerate(args) if a == "--add-dir"])
        deny = args[args.index("--disallowedTools") + 1]
        self.assertIn("Edit(/%s)" % os.path.join(self.part, "KARTA.md"), deny)          # Edit(//ścieżka)
        self.assertNotIn(".agent", deny)
        self.assertIn("katalog roboczy %s (gałąź" % wt, call["prompt"])
        # folder części bez zmian, praca na gałęzi części, katalog roboczy usunięty
        self.assertFalse(os.path.exists(os.path.join(self.part, "z-czesci.txt")))
        self.assertEqual(git(self.part, "status", "--porcelain", "--untracked-files=all"), "")
        self.assertFalse(os.path.exists(wt))
        part = rec["parts"][0]
        self.assertTrue(part["branch"].startswith("agent/"))
        self.assertEqual(part["commits"], 1)
        self.assertIn("z-czesci.txt", git(self.part, "show", "--name-only", "--format=", part["branch"]))
        # scalenie gałęzi części tym samym przyciskiem co gałąź z pola gałąź:
        code, err, _ = m.merge("", part["project"], part["branch"])
        self.assertEqual(code, 200, err)
        self.assertTrue(os.path.exists(os.path.join(self.part, "z-czesci.txt")))

    def test_bez_zmian_w_czesci_galaz_znika(self):
        self.set_mode("ok")
        m = self.new_manager()
        rec = self.wait(self.run_task("Zadanie A", m)[2]["id"], manager=m)
        self.assertEqual(rec.get("parts"), [])
        self.assertNotIn("agent/", git(self.part, "branch", "--list", "agent/*"))


@unittest.skipUnless(GIT, "brak polecenia git")
class ZmianyNiezatwierdzone(Baza):
    def setUp(self):
        super().setUp()
        repo(self.folder)
        self.pid = server.load_projects()[0]["projects"][0]["id"]
        self.file = os.path.join(self.folder, "strona.js")
        with open(self.file, "w", encoding="utf-8") as f:
            f.write("zmiana agenta\n")
        # przebieg innego zadania, które zapisało plik w głównym katalogu repozytorium
        os.makedirs(self.runs, exist_ok=True)
        rid = "%s-abcd" % datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        rec = dict(self.manager._new("task", "claude", "Dodaj miejsce na film", project="inny",
                                     project_name="Inny projekt"), id=rid, state="done", startedAt=agents.now_iso())
        with open(os.path.join(self.runs, rid + ".json"), "w", encoding="utf-8") as f:
            json.dump(rec, f)
        ev = {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Edit",
                                                            "input": {"file_path": self.file}}]}}
        with open(os.path.join(self.runs, rid + ".log"), "w", encoding="utf-8") as f:
            # zdarzenia z innym kształtem (message jako tekst, lista, napis) jak w przebiegach z produkcji
            for odd in ({"type": "user", "message": "tool_use %s" % self.file}, ["tool_use", self.file],
                        "tool_use " + self.file):
                f.write(json.dumps(odd) + "\n")
            f.write(json.dumps(ev) + "\n")
        self.m = self.new_manager()
        server._agents = self.m
        self.rid = rid

    def test_stan_zrodlo_i_blokada_scalania(self):
        code, _, extra = server.github_state({"project": self.pid})
        st = extra["state"]
        self.assertEqual(st["dirtyCount"], 1)
        self.assertEqual(st["sources"][0]["runId"], self.rid)
        self.assertEqual(st["stashes"], [])
        block = self.m.site.repo_block(self.pid, self.folder)
        self.assertIn("Zatwierdź jako zmiany agenta", block["text"])

    def test_zatwierdz_jako_zmiany_agenta(self):
        code, msg, extra = server.repo_change({"project": self.pid}, "commit")
        self.assertEqual(code, 200, msg)
        self.assertEqual(extra["state"]["dirtyCount"], 0)
        body = git(self.folder, "log", "-1", "--format=%B")
        self.assertIn("Dodaj miejsce na film", body)
        self.assertIn(self.rid, body)
        self.assertEqual(git(self.folder, "log", "-1", "--format=%an"), "Panel projektów")

    def test_odloz_i_przywroc(self):
        code, msg, extra = server.repo_change({"project": self.pid}, "stash")
        self.assertEqual(code, 200, msg)
        self.assertFalse(os.path.exists(self.file))
        st = extra["state"]["stashes"]
        self.assertEqual(len(st), 1)
        self.assertIn("Dodaj miejsce na film", st[0]["message"])
        self.assertEqual(st[0]["files"], ["strona.js"])
        code, msg, extra = server.repo_change({"project": self.pid, "ref": st[0]["ref"]}, "restore")
        self.assertEqual(code, 200, msg)
        self.assertTrue(os.path.exists(self.file))
        self.assertEqual(extra["state"]["stashes"], [])
        self.assertEqual(server.repo_change({"project": self.pid, "ref": "zly"}, "restore")[0], 409)


class Rownolegle(Baza):
    def setUp(self):
        super().setUp()
        self.other = os.path.join(self.tmp, "drugi")
        quiet(projekt.cmd_nowy, self.other, "Drugi projekt", register=True)
        with open(os.path.join(self.other, "ZADANIA.md"), "w", encoding="utf-8") as f:
            f.write("# Zadania: Drugi\n\n## Do rozplanowania\n\n- [ ] Zadanie Z | kto: claude\n")
        server.data_invalidate()
        self.go = os.path.join(self.tmp, "dalej")
        self.set_mode("czekaj")

    def test_dwa_projekty_naraz_jeden_projekt_po_kolei(self):
        m = self.new_manager(ATRAPA_DALEJ_PLIK=self.go, PANEL_AGENTS_MAX="")
        self.assertEqual(m.max_parallel, 2)                          # domyślnie 2
        a = self.run_task("Zadanie A", m)[2]["id"]
        b = self.run_task("Zadanie B", m)[2]["id"]
        z = self.run_task("Zadanie Z", m)[2]["id"]
        self.wait(a, states=("running",), manager=m)
        self.wait(z, states=("running",), manager=m)
        time.sleep(0.3)
        self.assertEqual(m.get(b)["state"], "queued")                 # ten sam projekt: czeka
        open(self.go, "w").close()
        for rid in (a, z, b):
            self.assertEqual(self.wait(rid, manager=m, timeout=20)["state"], "done")
        self.assertGreaterEqual(m.get(b)["startedAt"], m.get(a)["endedAt"])

    def test_ustawienie_w_panelu(self):
        m = self.new_manager()
        self.assertEqual(m.set_parallel(5)[0], 400)
        self.assertEqual(m.set_parallel(1)[0], 200)
        self.assertEqual(m.snapshot()["maxParallel"], 1)
        m2 = self.new_manager(PANEL_AGENTS_MAX="3", ATRAPA_DALEJ_PLIK=self.go)
        self.assertEqual(m2.max_parallel, 1)                          # ustawienie z panelu wygrywa ze zmienną
        a = self.run_task("Zadanie A", m2)[2]["id"]
        z = self.run_task("Zadanie Z", m2)[2]["id"]
        self.wait(a, states=("running",), manager=m2)
        time.sleep(0.3)
        self.assertEqual(m2.get(z)["state"], "queued")
        open(self.go, "w").close()
        self.assertEqual(self.wait(z, manager=m2, timeout=20)["state"], "done")

    def test_wdrozenie_czeka_nowe_zadania_tez(self):
        deploy = os.path.join(self.tmp, "wdrozenie")
        os.makedirs(deploy)
        path = os.path.join(deploy, "stan.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"state": "waiting", "at": datetime.datetime.now().isoformat(timespec="seconds")}, f)
        m = self.new_manager(PANEL_WDROZENIE_DIR=deploy, ATRAPA_DALEJ_PLIK=self.go)
        open(self.go, "w").close()
        a = self.run_task("Zadanie A", m)[2]["id"]
        time.sleep(0.4)
        self.assertEqual(m.get(a)["state"], "queued")
        self.assertTrue(m.snapshot()["deployHold"])
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"state": "running", "at": datetime.datetime.now().isoformat(timespec="seconds")}, f)
        m._hold = (0.0, False)
        m.tick(datetime.datetime.now())
        self.assertEqual(self.wait(a, manager=m)["state"], "done")

    def test_bezpiecznik_liczy_sume(self):
        m = self.new_manager()
        recs = []
        for n, start in ((1, 0.10), (2, 0.15)):
            r = dict(m._new("task", "claude", "R%d" % n), state="running", limitStart=start, limitNow=start)
            m._runs[r["id"] + str(n)] = r
            r["id"] = r["id"] + str(n)
            recs.append(r)
        stopped = []
        m.stop = lambda rid: stopped.append(rid) or (200, "", {})
        m._record_limits = lambda *a, **k: None
        with mock.patch.object(agents.agent_progress, "limit_windows", lambda *a: {"five": (0.4, 1, None)}):
            recs[1]["limitNow"] = 0.40                # razem 30 pkt: poniżej 2 × 20
            m._watch_budget(recs[1], {})
            self.assertEqual(stopped, [])
            recs[1]["limitNow"] = 0.55                # 45 pkt od startu pierwszego: zatrzymane to najdłuższe
            m._watch_budget(recs[1], {})
        self.assertEqual(stopped, [recs[0]["id"]])
        self.assertIn("razem", m._priv[recs[0]["id"]]["budget"])


class StronaNaZywo(Strona):
    card_lines = "- strona: site\n- strona build: npm run build:panel\n- strona wynik: dist\n"

    def setUp(self):
        super().setUp()
        self.waiting = os.path.join(self.tmp, "czeka")
        self.go = os.path.join(self.tmp, "dalej")
        self.cli = os.path.join(self.tmp, "cli.js")
        open(self.cli, "w").close()
        self.m = self.new_manager(ATRAPA_CZEKA_PLIK=self.waiting, ATRAPA_DALEJ_PLIK=self.go,
                                  PANEL_PRZEGLADARKA_MCP=self.cli, PANEL_PRZEGLADARKA_CHROME="/opt/chrome")
        server._agents = self.m
        with open(os.path.join(self.folder, "ZADANIA.md"), "a", encoding="utf-8") as f:
            f.write("- [ ] Strona: większy nagłówek | kto: claude\n")
        os.makedirs(os.path.join(self.folder, "site", "dist"))
        with open(os.path.join(self.folder, "site", "dist", "index.html"), "w", encoding="utf-8") as f:
            f.write("<html><head></head><body>W budowie</body></html>")
        server.data_invalidate()

    def test_postep_wersja_w_budowie_i_przegladarka(self):
        self.set_mode("czekaj")
        t = self.task("Strona: większy nagłówek")
        code, err, extra = self.m.run_task(t["id"], t["title"])
        self.assertEqual(code, 200, err)
        rid = extra["id"]
        self.wait_for(lambda: os.path.exists(self.waiting), timeout=15)
        self.wait_for(lambda: self.m.site.info(self.pid)[2]["live"]["steps"], timeout=5)
        code, _, info = self.m.site.info(self.pid)
        live = info["live"]
        self.assertEqual((live["runId"], live["state"]), (rid, "running"))
        self.assertTrue(live["steps"])
        self.assertTrue(live["browser"])
        self.assertTrue(live["url"].endswith("/~budowa/"))
        code, body, ctype, _ = self.m.site.serve(live["url"] + "index.html")
        self.assertEqual(code, 200)
        self.assertIn(b"W budowie", body)
        # polecenie: przeglądarka MCP tylko dla adresu podglądu, bez narzędzi wykonujących kod
        call = [c for c in self.calls() if "Strona: większy nagłówek" in (c.get("prompt") or "")][-1]
        args = call["argv"]
        cfg = json.loads(args[args.index("--mcp-config") + 1])["mcpServers"]["przegladarka"]
        port = self.m._priv[rid]["preview"]["port"]
        self.assertIn("http://127.0.0.1:%d" % port, cfg["args"])
        self.assertIn("--executable-path", cfg["args"])
        self.assertIn("mcp__przegladarka__browser_navigate", args[args.index("--allowedTools") + 1])
        self.assertIn("mcp__przegladarka__browser_run_code_unsafe", args[args.index("--disallowedTools") + 1])
        self.assertIn("--strict-mcp-config", args)
        self.assertIn("http://127.0.0.1:%d/" % port, call["prompt"])
        with urllib.request.urlopen("http://127.0.0.1:%d/" % port, timeout=5) as r:   # podgląd dla przeglądarki agenta
            self.assertIn(b"W budowie", r.read())
        open(self.go, "w").close()
        self.wait(rid, manager=self.m, timeout=20)
        self.assertEqual(self.m.site.serve(live["url"] + "index.html")[0], 404)        # po końcu pracy nie ma

        def closed():
            try:
                urllib.request.urlopen("http://127.0.0.1:%d/" % port, timeout=1).close()
                return False
            except OSError:
                return True
        self.wait_for(closed, timeout=5)                             # serwer podglądu w budowie zamknięty

    def test_bez_mcp_bez_przegladarki(self):
        m = self.new_manager(PANEL_PRZEGLADARKA_MCP=os.path.join(self.tmp, "nie-ma.js"))
        self.set_mode("ok")
        t = self.task("Strona: większy nagłówek")
        rid = m.run_task(t["id"], t["title"])[2]["id"]
        self.wait(rid, manager=m)
        call = [c for c in self.calls() if "Strona: większy nagłówek" in (c.get("prompt") or "")][-1]
        self.assertNotIn("--mcp-config", call["argv"])
        self.assertNotIn("mcp__przegladarka", call["prompt"])


@unittest.skipUnless(GIT, "brak polecenia git")
class Naprawa(Baza):
    def test_zatwierdza_scala_i_zamyka(self):
        with open(os.path.join(self.folder, "ZADANIA.md"), "a", encoding="utf-8") as f:
            f.write("- [ ] Strona: poprawki | kto: agent\n")
        with open(os.path.join(self.folder, "strona.js"), "w", encoding="utf-8") as f:
            f.write("a\nb\nc\n")
        repo(self.folder)
        git(self.folder, "checkout", "-q", "-b", "agent/poprawki")
        with open(os.path.join(self.folder, "strona.js"), "w", encoding="utf-8") as f:
            f.write("A\nb\nc\n")
        git(self.folder, "commit", "-qam", "Poprawki\n\nUruchomienie panelu 20261125-172031-0002 (claude).")
        git(self.folder, "checkout", "-q", "main")
        with open(os.path.join(self.folder, "film.js"), "w", encoding="utf-8") as f:
            f.write("film\n")
        pid = server.load_projects()[0]["projects"][0]["id"]
        base = git(self.folder, "rev-parse", "main")
        runs = {"r-przerwane": dict(self.manager._new("task", "claude", "Strona: poprawki", project=pid,
                                                      file="ZADANIA.md"), state="error", branch="agent/poprawki",
                                    base="main", baseCommit=base, error="Polecenie zakończyło się kodem 143.",
                                    changes=[{"path": "strona.js", "added": 1, "removed": 1}]),
                "r-zrodlo": dict(self.manager._new("task", "claude", "Dodaj miejsce na film", project="inny"),
                                 state="done", startedAt=agents.now_iso())}
        os.makedirs(self.runs, exist_ok=True)
        for rid, rec in runs.items():
            rec["id"] = "20261125-0000%02d-%s" % (len(rid), rid[2:6])
            runs[rid] = rec
            with open(os.path.join(self.runs, rec["id"] + ".json"), "w", encoding="utf-8") as f:
                json.dump(rec, f)
        ev = {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Write",
                                                            "input": {"file_path": os.path.join(self.folder, "film.js")}}]}}
        with open(os.path.join(self.runs, runs["r-zrodlo"]["id"] + ".log"), "w", encoding="utf-8") as f:
            f.write(json.dumps(ev) + "\n")
        m = self.new_manager()
        spec = dict(naprawy.OPRO, run=runs["r-przerwane"]["id"], source=runs["r-zrodlo"]["id"])
        naprawy.run(m, [("proba", lambda mm: naprawy.opro_fix(mm, spec))])
        log = git(self.folder, "log", "--format=%s", "-3")
        self.assertIn("Scalenie agent/poprawki", log)
        self.assertIn("Zmiany agenta z zadania „Dodaj miejsce na film”", log)
        with open(os.path.join(self.folder, "strona.js"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "A\nb\nc\n")
        self.assertTrue(os.path.exists(os.path.join(self.folder, "film.js")))
        self.assertTrue(self.row("Strona: poprawki").startswith("- [x] Strona: poprawki"))
        task = self.task("Strona: poprawki")
        self.assertIn("scalone do main", task["detail"]["result"])
        self.assertIn("proba", json.load(open(os.path.join(self.runs, "stan.json")))["naprawy"])
        self.assertEqual(m.get(runs["r-przerwane"]["id"])["recovered"], "naprawa")


class Wdrozenie(unittest.TestCase):
    def test_skrypt_czeka_na_agentow(self):
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                            "uruchom", "serwer", "wdroz-panel.sh")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        self.assertLess(text.index("pracujacy()"), text.index('stan running "Scalam z produkcją"'))
        self.assertIn("WDROZ_CZEKAJ_AGENCI:-1800", text)
        self.assertIn("stan waiting", text)
        conf = os.path.join(os.path.dirname(path), "panel-agenci.conf")
        with open(conf, encoding="utf-8") as f:
            self.assertIn("KillMode=process", f.read())


if __name__ == "__main__":
    unittest.main()
