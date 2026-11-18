"""Zarządca uruchomień (agents.py) na atrapach poleceń claude i codex."""
import datetime
import http.server
import json
import os
import re
import shutil
import subprocess
import threading
import time
import unittest

from wspolne import ATRAPA_CLAUDE, TODAY, Baza, agents, projekt, server

ISO = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d$")


def at(hour):
    return datetime.datetime.combine(datetime.date.today(), datetime.time(hour, 0))


def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


class Zadanie(Baza):
    def test_sukces(self):
        code, error, extra = self.run_task("Zadanie A")
        self.assertEqual((code, error), (200, ""))
        self.assertRegex(extra["id"], r"^\d{8}-\d{6}-[0-9a-f]{4}$")
        rec = self.wait(extra["id"])
        self.assertEqual(rec["state"], "done", rec)
        self.assertEqual((rec["kind"], rec["tool"], rec["auto"], rec["machine"]), ("task", "claude", False, "mac"))
        self.assertEqual((rec["project"], rec["projectName"], rec["file"], rec["title"]),
                         ("projekt-testowy", "Projekt testowy", "ZADANIA.md", "Zadanie A"))
        self.assertEqual(rec["taskId"].split("|")[:2], ["projekt-testowy", "ZADANIA.md"])
        for key in ("queuedAt", "startedAt", "endedAt"):
            self.assertRegex(rec[key], ISO)
        self.assertIsInstance(rec["durationMs"], int)
        self.assertEqual(rec["activity"], "")
        texts = [s["text"] for s in rec["steps"]]
        self.assertEqual(texts[:2], ["Read: ZADANIA.md", "Edit: ZADANIA.md"])
        self.assertRegex(rec["steps"][0]["t"], r"^\d\d:\d\d:\d\d$")
        self.assertTrue(rec["result"].startswith("Zrobione: zmiana gotowa."))
        self.assertEqual((rec["error"], rec["turns"], rec["tokensIn"], rec["tokensOut"]), ("", 3, 3112, 240))
        self.assertEqual((rec["costUsd"], rec["model"], rec["keySource"], rec["denials"]),
                         (0.0421, "claude-atrapa-1", "none", []))
        self.assertTrue(self.row("Zadanie A").startswith("- [x] Zadanie A | kto: claude | gdzie: mac"))
        self.assertTrue(os.path.exists(os.path.join(self.runs, rec["id"] + ".json")))
        with open(os.path.join(self.runs, rec["id"] + ".log"), encoding="utf-8") as f:
            self.assertIn('"type": "result"', f.read())
        with open(os.path.join(self.runs, rec["id"] + ".json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["state"], "done")

    def test_polecenie_i_srodowisko(self):
        rec = self.wait(self.run_task("Zadanie A")[2]["id"])
        self.assertEqual(rec["state"], "done")
        call = self.calls()[-1]
        self.assertEqual(call["argv"], ["-p", "--output-format", "stream-json", "--verbose",
                                        "--permission-mode", "acceptEdits"])
        self.assertEqual(os.path.realpath(call["cwd"]), self.folder)
        self.assertIn("z pliku ZADANIA.md, wiersz", call["prompt"])
        self.assertIn("„Zadanie A”", call["prompt"])
        self.assertIn("Etap: Pierwszy.", call["prompt"])
        self.assertIn("KARTA.md", call["prompt"])
        self.assertEqual(call["env"], ["CLAUDE_CODE_OAUTH_TOKEN"])     # klucze API i zmienne sesji usunięte

    def test_model_z_ustawien(self):
        m = self.new_manager(PANEL_AGENT_MODEL="sonnet")
        self.wait(self.run_task("Zadanie A", m)[2]["id"], manager=m)
        self.assertEqual(self.calls()[-1]["argv"][-2:], ["--model", "sonnet"])

    def test_wiersz_zostaje_w_toku_dostaje_odbior(self):
        self.set_mode("zostaw")
        rec = self.wait(self.run_task("Zadanie B")[2]["id"])
        self.assertEqual(rec["state"], "done")
        self.assertEqual(self.row("Zadanie B"), "- [~] Zadanie B | kto: claude | gdzie: mac | wymaga: odbiór")

    def test_odmowy(self):
        self.set_mode("odmowy")
        rec = self.wait(self.run_task("Zadanie A")[2]["id"])
        self.assertEqual((rec["state"], rec["denials"]), ("done", ["Bash: npm publish"]))

    def test_blad_polecenia(self):
        self.set_mode("smieci")
        rec = self.wait(self.run_task("Zadanie A")[2]["id"])
        self.assertEqual(rec["state"], "error")
        self.assertIn("Segmentation fault", rec["error"])
        self.assertEqual(rec["result"], "")
        self.assertTrue(self.row("Zadanie A").startswith("- [ ] Zadanie A"))
        self.assertFalse(self.manager.snapshot()["needsLogin"])

    def test_logowanie(self):
        self.set_mode("login")
        rec = self.wait(self.run_task("Zadanie A")[2]["id"])
        self.assertEqual(rec["state"], "login")
        self.assertIn("claude auth login", rec["error"])
        self.assertIn("Ponawiam połączenie (1/10)", [s["text"] for s in rec["steps"]])
        self.assertTrue(self.row("Zadanie A").startswith("- [ ] Zadanie A"))
        self.assertTrue(self.manager.snapshot()["needsLogin"])
        with open(os.path.join(self.runs, "stan.json"), encoding="utf-8") as f:
            self.assertTrue(json.load(f)["needsLogin"])
        self.assertTrue(self.new_manager().snapshot()["needsLogin"])      # znacznik przeżywa restart
        self.manager.set_automat(True)
        self.assertEqual(self.manager.tick(at(10)), [])                    # Automat czeka na logowanie
        self.set_mode("ok")
        code, _, extra = self.manager.run_check("claude")
        self.assertEqual(code, 200)
        self.assertEqual(self.wait(extra["id"])["state"], "done")
        self.assertFalse(self.manager.snapshot()["needsLogin"])           # pierwsze udane uruchomienie zdejmuje znacznik

    def test_limit_z_czasem_odnowienia(self):
        self.set_mode("limit")
        rec = self.wait(self.run_task("Zadanie A")[2]["id"])
        self.assertEqual(rec["state"], "limit")
        until = datetime.datetime.fromisoformat(self.manager.snapshot()["limitUntil"])
        minutes = (until - datetime.datetime.now()).total_seconds() / 60
        self.assertTrue(115 < minutes < 121, minutes)
        self.assertTrue(self.row("Zadanie A").startswith("- [ ] Zadanie A"))
        self.manager.set_automat(True)
        self.assertEqual(self.manager.tick(at(10)), [])                    # Automat czeka do odnowienia

    def test_limit_ze_zdarzenia(self):
        self.set_mode("limit-zdarzenie")
        rec = self.wait(self.run_task("Zadanie A")[2]["id"])
        self.assertEqual(rec["state"], "limit")
        until = datetime.datetime.fromisoformat(self.manager.snapshot()["limitUntil"])
        minutes = (until - datetime.datetime.now()).total_seconds() / 60
        self.assertTrue(25 < minutes < 31, minutes)

    def test_miniony_limit_znika(self):
        self.manager._state["limitUntil"] = "2020-01-01T00:00:00"
        self.assertIsNone(self.manager.snapshot()["limitUntil"])

    def test_zatrzymanie_w_toku(self):
        self.set_mode("wolno")
        rid = self.run_task("Zadanie A")[2]["id"]
        self.wait_for(lambda: os.path.exists(self.pid_file) and self.manager.get(rid)["activity"].startswith("Bash"))
        rec = self.manager.get(rid)
        self.assertEqual((rec["state"], rec["activity"]), ("running", "Bash: sleep 120"))
        self.assertEqual(self.row("Zadanie A"), "- [~] Zadanie A | kto: claude | gdzie: mac")
        task = self.task("Zadanie A")
        self.manager.annotate([task], "registry")
        self.assertEqual((task["runId"], task["runBlock"]), (rid, "W toku"))
        self.assertEqual(self.run_task("Zadanie A")[:2], (409, "W toku"))
        with open(self.pid_file, encoding="utf-8") as f:
            grandchild = int(f.read())
        self.assertEqual(self.manager.stop(rid)[0], 200)
        rec = self.wait(rid)
        self.assertEqual((rec["state"], rec["error"]), ("stopped", ""))
        self.assertTrue(self.row("Zadanie A").startswith("- [ ] Zadanie A"))
        if os.name != "nt":
            self.wait_for(lambda: not alive(grandchild))                  # zatrzymana cała grupa procesów
        self.assertEqual(self.manager.stop(rid)[0], 409)
        self.assertEqual(self.manager.stop("nie-ma")[0], 404)

    def test_kolejka_i_zdjecie_z_kolejki(self):
        m = self.new_manager(PANEL_AGENTS_MAX="1")
        self.set_mode("wolno")
        first = self.run_task("Zadanie A", m)[2]["id"]
        second = self.run_task("Zadanie B", m)[2]["id"]
        self.wait(first, ("running",), manager=m)
        self.assertEqual(m.get(second)["state"], "queued")
        self.assertTrue(self.row("Zadanie B").startswith("- [~] Zadanie B"))
        snap = m.snapshot()
        self.assertEqual([r["id"] for r in snap["runs"]], [second, first])          # najnowsze pierwsze
        self.assertEqual((snap["maxParallel"], snap["today"]["runs"]), (1, 2))
        self.assertEqual(m.stop(second)[0], 200)
        self.assertEqual(m.get(second)["state"], "stopped")
        self.assertIsNone(m.get(second)["startedAt"])
        self.assertTrue(self.row("Zadanie B").startswith("- [ ] Zadanie B"))
        self.assertEqual(m.get(first)["state"], "running")
        self.set_mode("ok")
        third = self.run_task("Zadanie B", m)[2]["id"]
        self.assertEqual(m.get(third)["state"], "queued")
        m.stop(first)
        self.assertEqual(self.wait(third, manager=m)["state"], "done")              # kolejka rusza po zwolnieniu miejsca

    def test_limit_czasu(self):
        m = self.new_manager(PANEL_AGENT_TIMEOUT="1")
        self.set_mode("wolno")
        rec = self.wait(self.run_task("Zadanie A", m)[2]["id"], manager=m)
        self.assertEqual(rec["state"], "timeout")
        self.assertIn("Przekroczony czas", rec["error"])
        self.assertTrue(self.row("Zadanie A").startswith("- [ ] Zadanie A"))

    def test_codex(self):
        rec = self.wait(self.run_task("Zadanie C")[2]["id"])
        self.assertEqual((rec["state"], rec["tool"]), ("done", "codex"), rec)
        self.assertEqual((rec["turns"], rec["tokensIn"], rec["tokensOut"]), (1, 1200, 300))
        self.assertTrue(rec["result"].startswith("Zrobione"))
        self.assertIn("Bash: ls", [s["text"] for s in rec["steps"]])
        self.assertIn("Edit: ZADANIA.md", [s["text"] for s in rec["steps"]])
        call = self.calls()[-1]
        self.assertEqual(call["argv"], ["exec", "--json", "--sandbox", "workspace-write", "--skip-git-repo-check",
                                        "-C", self.folder, "-"])
        self.assertEqual(call["env"], [])
        self.assertIn("AGENTS.md", call["prompt"])
        self.assertTrue(self.row("Zadanie C").startswith("- [x] Zadanie C | kto: codex | gdzie: mac"))

    def test_codex_blad_i_logowanie(self):
        self.set_mode("blad")
        rec = self.wait(self.run_task("Zadanie C")[2]["id"])
        self.assertEqual((rec["state"], rec["error"]), ("error", "Nie udało się wykonać polecenia."))
        self.set_mode("login")
        rec = self.wait(self.run_task("Zadanie C")[2]["id"])
        self.assertEqual(rec["state"], "login")
        self.assertIn("codex login", rec["error"])
        self.assertFalse(self.manager.snapshot()["needsLogin"])           # znacznik dotyczy logowania Claude


class Reguly(Baza):
    def test_odmowy_uruchomienia(self):
        self.assertEqual(self.run_task("Zadanie D")[:2], (409, "Zadanie po Twojej stronie"))
        self.assertEqual(self.run_task("Zadanie E")[:2], (409, "Czeka na Twoją zgodę"))
        self.assertEqual(self.run_task("Zadanie F")[:2], (409, "Zrobione"))
        t = self.task("Zadanie A")
        self.assertEqual(self.manager.run_task(t["id"], "Inny tytuł")[:2], (409, agents.CONFLICT))
        self.assertEqual(self.manager.run_task("zly-identyfikator", "x")[0], 400)
        self.assertEqual(self.manager.run_task("nie-ma|ZADANIA.md|3", "x")[0], 404)
        self.assertEqual(self.calls(), [])
        self.assertTrue(self.row("Zadanie A").startswith("- [ ] Zadanie A"))

    def test_brak_polecenia(self):
        m = self.new_manager(PANEL_CODEX=os.path.join(self.tmp, "nie-ma-codex"),
                             PANEL_CLAUDE=os.path.join(self.tmp, "nie-ma-claude"))
        self.assertEqual(self.run_task("Zadanie C", m)[:2], (409, "Brak polecenia codex"))
        self.assertEqual(self.run_task("Zadanie B", m)[:2], (409, "Brak polecenia claude"))
        self.assertEqual(m.run_pm()[:2], (409, "Brak polecenia claude"))
        self.assertEqual(m.run_check("codex")[:2], (409, "Brak polecenia codex"))
        self.assertEqual(m.run_check("inne")[0], 400)

    def test_kolejnosc_regul(self):
        tools = {"claude": True, "codex": False}
        base = {"project": "p", "file": "ZADANIA.md", "title": "T", "kind": "zadanie", "state": "todo",
                "executor": "", "needsYou": ""}
        block = lambda live=(), source="registry", **kw: agents.run_block(dict(base, **kw), source, live, tools)
        self.assertEqual(block(), "")
        self.assertEqual(block(source="sample", state="done"), "Projekty przykładowe")
        self.assertEqual(block(kind="publikacja", state="done"), "Publikację wykonujesz samodzielnie")
        self.assertEqual(block(state="done", executor="ty"), "Zrobione")
        self.assertEqual(block(executor="ty", needsYou="zgoda"), "Zadanie po Twojej stronie")
        self.assertEqual(block(needsYou="zgoda", executor="codex"), "Czeka na Twoją zgodę")
        self.assertEqual(block(executor="codex", live={("p", "ZADANIA.md", "T")}), "Brak polecenia codex")
        self.assertEqual(block(live={("p", "ZADANIA.md", "T")}), "W toku")
        self.assertEqual(block(state="doing", needsYou="odbiór"), "")

    def test_srodowisko_procesu(self):
        env = agents.child_env({"PATH": "/bin", "ANTHROPIC_API_KEY": "a", "ANTHROPIC_BASE_URL": "b", "OPENAI_API_KEY": "c",
                                "PANEL_TOKEN": "d", "PANEL_NTFY_URL": "e", "CLAUDECODE": "1", "CLAUDE_CODE_ENTRYPOINT": "x",
                                "CLAUDE_CODE_OAUTH_TOKEN": "t", "CLAUDE_CONFIG_DIR": "/k", "PANEL_MACHINE": "mac"})
        self.assertEqual(sorted(env), ["CLAUDE_CODE_OAUTH_TOKEN", "CLAUDE_CONFIG_DIR", "PANEL_MACHINE", "PATH"])

    def test_stan_narzedzi(self):
        self.manager.refresh_tools(force=True, wait=True)
        tools = self.manager.snapshot()["tools"]
        self.assertEqual(tools["claude"], {"found": True, "version": "2.1.156", "loggedIn": True, "subscription": "max",
                                           "loginCmd": "claude auth login"})
        self.assertEqual(tools["codex"], {"found": True, "version": "0.50.0", "loggedIn": True, "subscription": "chatgpt",
                                          "loginCmd": "codex login"})
        m = self.new_manager(PANEL_CODEX=os.path.join(self.tmp, "nie-ma"))
        m.refresh_tools(force=True, wait=True)
        self.assertEqual(m.snapshot()["tools"]["codex"],
                         {"found": False, "version": "", "loggedIn": False, "subscription": "",
                          "loginCmd": "codex login"})

    @unittest.skipIf(agents.WINDOWS, "ścieżki POSIX")
    def test_polecenie_logowania(self):
        cmd = agents.Manager.login_cmd
        home = os.path.expanduser("~")
        self.assertEqual(cmd("claude", ""), "claude auth login")
        self.assertEqual(cmd("codex", ""), "codex login")
        self.assertEqual(cmd("claude", os.path.join(home, ".local", "bin", "claude")), "~/.local/bin/claude auth login")
        self.assertEqual(cmd("codex", "/opt/homebrew/bin/codex"), "/opt/homebrew/bin/codex login")
        self.assertEqual(cmd("claude", "/Applications/Moje narzędzia/claude"),
                         "'/Applications/Moje narzędzia/claude' auth login")
        self.assertEqual(cmd("claude", ATRAPA_CLAUDE), "claude auth login")      # atrapa: bez ścieżki


class Automat(Baza):
    def test_wybor_zadan(self):
        open(os.path.join(self.notes, TODAY + ".md"), "w").close()         # raport PM z dziś już jest
        self.assertEqual(self.manager.tick(at(10)), [])                    # Automat wyłączony domyślnie
        self.assertEqual(self.manager.set_automat("tak")[0], 400)
        self.assertEqual(self.manager.set_automat(True)[0], 200)
        self.assertTrue(self.new_manager().snapshot()["automat"])          # stan zapisany w stan.json
        started = self.manager.tick(at(10))
        self.assertEqual(len(started), 1)
        rec = self.wait(started[0])
        self.assertEqual((rec["title"], rec["auto"], rec["state"]), ("Auto dziś", True, "done"))
        self.assertEqual(self.manager.tick(at(11)), [])                    # nic więcej w dzień
        self.set_mode("zostaw")
        night = self.manager.tick(at(23))
        self.assertEqual([self.manager.get(r)["title"] for r in night], ["Auto noc"])
        self.wait(night[0])
        self.assertEqual(self.manager.tick(at(23)), [])                    # to samo zadanie nie rusza drugi raz dziś
        self.assertTrue(self.row("Auto jutro").startswith("- [ ]"))
        self.assertTrue(self.row("Auto inny węzeł").startswith("- [ ]"))
        self.assertTrue(self.row("Auto bez daty").startswith("- [ ]"))
        self.assertTrue(self.row("Zadanie A").startswith("- [ ]"))

    def test_raport_pm_raz_dziennie(self):
        self.manager.set_automat(True)
        with open(os.path.join(self.folder, "ZADANIA.md"), "w", encoding="utf-8") as f:
            f.write("# Zadania\n\n## Etap: Pusty\ntermin: %s\n\n- [x] Gotowe\n" % TODAY)
        self.assertEqual(self.manager.tick(at(6)), [])                     # przed PANEL_PM_HOUR
        started = self.manager.tick(at(8))
        self.assertEqual(len(started), 1)
        rec = self.wait(started[0])
        self.assertEqual((rec["kind"], rec["title"], rec["auto"], rec["state"], rec["project"]),
                         ("pm", "Raport PM", True, "done", ""))
        call = self.calls()[-1]
        self.assertEqual(os.path.realpath(call["cwd"]), os.path.realpath(self.root))
        self.assertEqual(call["argv"], ["-p", "--output-format", "stream-json", "--verbose", "--permission-mode",
                                        "acceptEdits", "--agent", "pm", "--allowedTools", agents.PM_TOOLS])
        self.assertIn("raporty/%s.md" % TODAY, call["prompt"])
        self.assertEqual(self.manager.tick(at(9)), [])                     # drugi raz tego dnia nie rusza

    def test_raport_pm_tylko_jeden_naraz(self):
        self.set_mode("wolno")
        code, _, extra = self.manager.run_pm()
        self.assertEqual(code, 200)
        self.assertEqual(self.manager.run_pm()[:2], (409, "Raport PM już trwa."))
        self.manager.stop(extra["id"])
        self.assertEqual(self.wait(extra["id"])["state"], "stopped")
        self.manager.set_automat(True)
        self.set_mode("ok")
        started = self.manager.tick(at(8))                                 # ręczny, zatrzymany raport nie zużywa dziennej próby
        self.assertEqual([self.manager.get(r)["kind"] for r in started][:1], ["pm"])
        self.wait(started[0])
        self.assertNotIn("pm", [self.manager.get(r)["kind"] for r in self.manager.tick(at(9))])

    def test_miejsca_w_kolejce(self):
        m = self.new_manager(PANEL_AGENTS_MAX="1")
        open(os.path.join(self.notes, TODAY + ".md"), "w").close()
        with open(os.path.join(self.folder, "ZADANIA.md"), "a", encoding="utf-8") as f:
            f.write("- [ ] Auto drugie | kto: claude | gdzie: mac | kiedy: %s\n" % TODAY)
        m.set_automat(True)
        self.set_mode("wolno")
        started = m.tick(at(10))
        self.assertEqual(len(started), 1)                                  # tyle, ile wolnych miejsc
        self.assertEqual(m.tick(at(10)), [])
        m.stop(started[0])


class Trwalosc(Baza):
    def record(self, rid, state="done", **extra):
        rec = self.manager._new("task", "claude", "Zadanie A", project="projekt-testowy",
                                project_name="Projekt testowy", file="ZADANIA.md")
        rec.update(id=rid, state=state, **extra)
        os.makedirs(self.runs, exist_ok=True)
        for ext, body in ((".json", json.dumps(rec)), (".log", "")):
            with open(os.path.join(self.runs, rid + ext), "w", encoding="utf-8") as f:
                f.write(body)
        return rec

    def test_restart_serwera(self):
        t = self.task("Zadanie A")
        projekt.update_task(self.folder, "ZADANIA.md", t["line"], "Zadanie A", {"state": "doing", "executor": "claude"})
        self.record("20261110-100000-aaaa", "running", taskId=t["id"], startedAt="2026-11-10T10:00:00")
        self.record("20261110-100500-bbbb", "queued", title="Zadanie B")
        m = self.new_manager()
        for rid in ("20261110-100000-aaaa", "20261110-100500-bbbb"):
            rec = m.get(rid)
            self.assertEqual((rec["state"], rec["error"]), ("stopped", "Serwer został zatrzymany."))
            with open(os.path.join(self.runs, rid + ".json"), encoding="utf-8") as f:
                self.assertEqual(json.load(f)["state"], "stopped")
        m.tick_seconds = 0.05
        m.start()
        self.assertTrue(self.row("Zadanie A").startswith("- [ ] Zadanie A"))
        self.assertEqual(m.run_task(t["id"], "Zadanie A")[0], 200)         # zadanie znów można uruchomić

    def test_zostaje_200_rekordow(self):
        for i in range(205):
            self.record("20261109-%06d-abcd" % i)
        m = self.new_manager()
        snap = m.snapshot()
        self.assertEqual(len(snap["runs"]), 40)
        self.assertEqual(snap["runs"][0]["id"], "20261109-000204-abcd")
        names = sorted(n for n in os.listdir(self.runs) if n.endswith(".json") and n != "stan.json")
        self.assertEqual((len(names), names[0]), (200, "20261109-000005-abcd.json"))
        self.assertFalse(os.path.exists(os.path.join(self.runs, "20261109-000004-abcd.log")))
        rec = self.wait(self.run_task("Zadanie A", m)[2]["id"], manager=m)
        self.assertEqual(rec["state"], "done")
        self.assertEqual(len([n for n in os.listdir(self.runs) if n.endswith(".json") and n != "stan.json"]), 200)

    def test_uszkodzone_pliki_nie_przerywaja(self):
        os.makedirs(self.runs, exist_ok=True)
        for name, body in (("20261109-000001-abcd.json", "{nie json"), ("stan.json", "[1, 2]")):
            with open(os.path.join(self.runs, name), "w", encoding="utf-8") as f:
                f.write(body)
        m = self.new_manager()
        self.assertEqual((m.snapshot()["runs"], m.snapshot()["automat"]), ([], False))


class Dodatki(Baza):
    @unittest.skipUnless(shutil.which("git"), "brak polecenia git")
    def test_git_pull_nie_blokuje(self):
        def git(*args):
            subprocess.run(["git", "-c", "user.name=test", "-c", "user.email=test@example.invalid"] + list(args),
                           cwd=self.folder, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        git("init")
        git("add", "-A")
        git("commit", "-m", "start")
        m = self.new_manager(PANEL_GIT_PULL="1")
        rec = self.wait(self.run_task("Zadanie A", m)[2]["id"], manager=m)
        self.assertEqual(rec["state"], "done")
        self.assertEqual(rec["steps"][0]["text"], "git pull: nie udało się")        # brak zdalnego repozytorium
        rec = self.wait(self.run_task("Zadanie B", m)[2]["id"], manager=m)          # po zmianie wiersza repozytorium nie jest czyste
        self.assertEqual(rec["steps"][0]["text"], "git pull pominięty: niezapisane zmiany w repozytorium")
        self.assertEqual(rec["state"], "done")

    def test_powiadomienie(self):
        got = []

        class Odbiornik(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                got.append(self.rfile.read(int(self.headers.get("Content-Length") or 0)).decode("utf-8"))
                self.send_response(200)
                self.end_headers()

            def log_message(self, *args):
                pass

        httpd = http.server.HTTPServer(("127.0.0.1", 0), Odbiornik)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        try:
            m = self.new_manager(PANEL_NTFY_URL="http://127.0.0.1:%d/temat" % httpd.server_address[1])
            self.wait(self.run_task("Zadanie A", m)[2]["id"], manager=m)
            self.wait_for(lambda: got)
            # projekt bez pola „klient” jest kliencki: powiadomienie bez tytułu zadania
            self.assertEqual(got, ["Zadanie w projekcie Projekt testowy: zakończone"])
            self.wait(m.run_check("claude")[2]["id"], manager=m)                    # test połączenia nie powiadamia
            time.sleep(0.3)
            self.assertEqual(len(got), 1)
            projekt.set_card_fields(self.folder, {"client": False})
            self.wait(self.run_task("Zadanie B", m)[2]["id"], manager=m)
            self.wait_for(lambda: len(got) == 2)
            self.assertEqual(got[1], "Zadanie B (Projekt testowy): zakończone")
        finally:
            httpd.shutdown()
            httpd.server_close()

    def test_test_polaczenia(self):
        code, _, extra = self.manager.run_check("claude")
        rec = self.wait(extra["id"])
        self.assertEqual((rec["kind"], rec["title"], rec["state"]), ("check", "Test połączenia", "done"))
        call = self.calls()[-1]
        self.assertEqual(call["argv"], ["-p", "--output-format", "stream-json", "--verbose", "--model", "haiku"])
        self.assertEqual(call["prompt"].strip(), "Odpowiedz jednym słowem: ok")
        self.assertEqual(os.path.realpath(call["cwd"]), os.path.realpath(self.runs))


class ProjektyPrzykladowe(Baza):
    registered = False

    def test_zadan_przykladowych_nie_uruchamiamy(self):
        data, _ = server.load_projects()
        self.assertEqual(data["projectsSource"], "sample")
        self.manager.annotate(data["tasks"], data["projectsSource"])
        self.assertEqual({t["runBlock"] for t in data["tasks"]}, {"Projekty przykładowe"})
        t = data["tasks"][0]
        self.assertEqual(self.manager.run_task(t["id"], t["title"])[:2], (409, "Projekty przykładowe"))
        self.manager.set_automat(True)
        open(os.path.join(self.notes, TODAY + ".md"), "w").close()
        self.assertEqual(self.manager.tick(at(10)), [])
        self.assertEqual(self.manager.run_check("claude")[0], 200)                  # test połączenia działa zawsze


if __name__ == "__main__":
    unittest.main()
