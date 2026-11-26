import datetime
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from wspolne import Baza, server
from test_czat_uruchamia import PW
import agent_progress
from agents import pick_agent, task_outcome


def event_tool(name, args, tool_id="t"):
    return {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "name": name, "input": args, "id": tool_id}]}}


class Postep(unittest.TestCase):
    def test_claude_todo(self):
        plan = []
        agent_progress.update_plan(plan, event_tool("TodoWrite", {"todos": [
            {"content": "Odczytaj kartę", "status": "completed"},
            {"content": "Zapisz wynik", "status": "in_progress"}]}))
        self.assertEqual([(s["text"], s["done"], s["active"]) for s in plan],
                         [("Odczytaj kartę", True, False), ("Zapisz wynik", False, True)])

    def test_claude_task(self):
        plan, pending = [], {}
        agent_progress.task_creates(pending, plan, event_tool("TaskCreate", {"subject": "Sprawdź dane"}))
        agent_progress.task_creates(pending, plan, {"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "t", "content": "Task #2 created successfully"}]}})
        agent_progress.update_plan(plan, event_tool("TaskUpdate", {"taskId": "2", "status": "completed"}))
        self.assertEqual(plan, [{"id": "2", "text": "Sprawdź dane", "done": True, "active": False}])

    def test_codex_todo(self):
        plan = []
        agent_progress.update_plan(plan, {"type": "item.updated", "item": {"type": "todo_list", "items": [
            {"text": "Dodaj widok", "completed": True}, {"text": "Uruchom testy", "completed": False}]}})
        self.assertEqual([(s["text"], s["done"]) for s in plan], [("Dodaj widok", True), ("Uruchom testy", False)])
        self.assertEqual(agent_progress.codex_limit({"msg": {"rate_limits": {"primary": {
            "window_minutes": 300, "used_percent": 85, "resets_at": 123}}}}), (0.85, 123))

    def test_codex_limit_z_sesji(self):
        at = datetime.datetime(2026, 11, 24, 12, tzinfo=datetime.timezone.utc).timestamp()
        thread = "12345678-abcd-1234-abcd-abcdef123456"
        with tempfile.TemporaryDirectory() as folder:
            day = Path(folder) / "sessions" / "2026" / "11" / "24"
            day.mkdir(parents=True)
            target = day / ("rollout-2026-11-24T12-00-00-" + thread + ".jsonl")
            target.write_text(json.dumps({"type": "event_msg", "payload": {"type": "token_count",
                "rate_limits": {"primary": {"window_minutes": 300, "used_percent": 76}}}}) + "\n", encoding="utf-8")
            self.assertEqual(agent_progress.codex_session_limit(folder, thread, at), (.76, None))
            self.assertIsNone(agent_progress.codex_session_limit(folder, "../../sekret", at))

    def test_stany_zlecenia(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder) / "ZLECENIE-proba"
            base.with_suffix(".md").write_text("# Próba\nWiersz poza tytułem", encoding="utf-8")
            orders = agent_progress.Orders(folder)
            self.assertEqual(orders.snapshot()[0]["state"], "queued")
            log = base.with_suffix(".log")
            log.write_text('{"type":"turn.started"}\n{"type":"item.completed","item":{"type":"agent_message","text":"Działa"}}\n',
                           encoding="utf-8")
            self.assertEqual(orders.snapshot()[0]["state"], "running")
            self.assertEqual(orders.live_log(base.name, 0)["items"][0]["text"], "Działa")
            with log.open("a") as stream:
                stream.write('{"type":"turn.completed"}\n')
            self.assertEqual(orders.snapshot()[0]["state"], "done")
            self.assertIsNone(orders.result(base.name))
            Path(str(base) + ".wynik.md").write_text("Gotowe", encoding="utf-8")
            self.assertTrue(orders.snapshot()[0]["hasResult"])
            self.assertEqual(orders.result(base.name), "Gotowe")
            self.assertIsNone(orders.result("../" + base.name))

    def test_wybor(self):
        tools = {"claude": True, "codex": True}
        code = {"executor": "agent", "title": "Dodaj stronę ustawień", "machine": "cloud"}
        writing = {"executor": "agent", "title": "Napisz raport", "machine": "cloud"}
        self.assertEqual(pick_agent(code, True, {}, .8, tools), ("codex", "zmiana kodu"))
        self.assertEqual(pick_agent(writing, True, {}, .8, tools)[0], "claude")
        self.assertEqual(pick_agent(dict(code, title="Napisz testy"), True, {}, .8, tools)[0], "codex")
        self.assertEqual(pick_agent(code, True, {"codex": .85}, .8, tools), ("claude", "limit Codex 85%"))
        self.assertEqual(pick_agent(writing, True, {"claude": .8}, .8, tools)[0], "codex")
        self.assertEqual(pick_agent(dict(code, executor="codex"), True, {"codex": .85}, .8, tools),
                         ("codex", ""))

    def test_wyniki(self):
        self.assertEqual(task_outcome({"state": "done"}), "done")
        self.assertEqual(task_outcome({"state": "blocked"}), "blocked")
        self.assertEqual(task_outcome({"state": "doing", "needsYou": "odbiór"}), "review")
        self.assertEqual(task_outcome({"state": "todo"}), "unknown")


class Routing(Baza):
    def test_start_zachowuje_kto_agent(self):
        path = Path(self.folder) / "ZADANIA.md"
        text = path.read_text(encoding="utf-8").replace("Zadanie C | kto: codex", "Strona: popraw menu | kto: agent")
        path.write_text(text, encoding="utf-8")
        self.manager.refresh_tools(force=True, wait=True)
        code, msg, extra = self.run_task("Strona: popraw menu")
        self.assertEqual(code, 200, msg)
        run = self.wait(extra["id"])
        self.assertEqual((run["tool"], run["choiceReason"]), ("codex", "Decyzja z reguł: zmiana kodu"))
        self.assertIn("kto: agent", self.row("Strona: popraw menu"))


BROWSER = """
import json, os, sys
from playwright.sync_api import sync_playwright
url, fixture, dest = sys.argv[1:]
with open(fixture, encoding='utf-8') as f:
    agents = json.load(f)
with sync_playwright() as p:
    browser = p.chromium.launch()
    for width in (390, 1440, 1920):
        page = browser.new_page(viewport={'width':width,'height':950}, color_scheme='dark')
        errors, requests = [], []
        page.on('pageerror', lambda e: errors.append(str(e)))
        def data(route):
            requests.append(1)
            res = route.fetch()
            body = res.json()
            body['agents'].update(agents)
            if len(requests) > 1:
                body['agents']['runs'][0]['recent'] = ['Nowy wpis z następnego odczytu']
            route.fulfill(response=res, json=body)
        page.route('**/api/data', data)
        page.goto(url + '#agenci')
        page.get_by_role('heading', name='Teraz', exact=True).wait_for()
        # grupa agenci (2026-11-25): kamienie milowe i zawężony szacunek, brak Planu dnia, Użycie, zwinięte Uruchomienia
        assert page.get_by_text('Kamień 2 z 3', exact=False).is_visible()
        assert page.get_by_text('Zostało ok. 8 min', exact=False).is_visible()
        assert page.locator('#ag-view').get_by_text('Plan dnia').count() == 0
        assert page.locator('#plan').count() == 0
        use = page.locator('#ag-use')
        assert use.get_by_role('heading', name='Claude', exact=False).is_visible()
        assert use.get_by_role('heading', name='Codex', exact=False).is_visible()
        assert use.get_by_text('Uruchomienia', exact=True).count() == 2
        assert use.get_by_text('Udane (7 dni)', exact=True).count() == 2
        runs = page.locator('#ag-runs')
        assert runs.evaluate('el => el.tagName === "DETAILS" && !el.open')
        assert not runs.locator('.wh').first.is_visible()
        assert 'dziś' in runs.locator('summary').inner_text()
        runs.locator('summary').click()
        runs.locator('.wh').first.wait_for()
        assert page.get_by_text('Przygotuj zmianę w kolejce', exact=False).is_visible()
        for state in ['zrobione', 'do odbioru', 'blokada', 'zatrzymane', 'błąd']:
            assert page.locator('#ag-runs .wh').get_by_text(state, exact=True).is_visible(), state
        assert page.evaluate('document.documentElement.scrollWidth === innerWidth'), width
        assert page.locator('#ag-view').evaluate('el => el.scrollWidth <= el.clientWidth'), width
        assert not errors, errors
        if dest and width in (390, 1440):
            page.screenshot(path=os.path.join(dest, f'agenci-{width}.png'), full_page=True)
        page.locator('#ag-runs .ag-rm .t').first.evaluate("el => el.textContent = 'DługiTytuł'.repeat(60)")
        assert page.evaluate('document.documentElement.scrollWidth === innerWidth'), width
        if width == 390:
            page.get_by_text('Nowy wpis z następnego odczytu', exact=True).wait_for(timeout=7000)
            assert not errors, errors
        page.close()
"""


@unittest.skipUnless(PW and not os.environ.get("PANEL_TESTY_BEZ_RENDERU"), "brak Playwright albo PANEL_TESTY_BEZ_RENDERU")
class Widok(unittest.TestCase):
    def test_agenci_bez_przewijania(self):
        now = datetime.datetime.now().isoformat(timespec="seconds")
        base = {"tool": "codex", "kind": "task", "machine": "cloud", "projectName": "Projekt przykładowy",
                "queuedAt": now, "startedAt": now}
        fixture = {
            "tools": {
                "claude": {"found": True, "loggedIn": True, "subscription": "Max"},
                "codex": {"found": True, "loggedIn": True, "subscription": "ChatGPT"},
            },
            "usage": {"five": .64, "codexFive": .21, "budget": .2, "reserve": .8},
            "today": {"runs": 6, "tokens": 24250, "costUsd": .37},
            "development": [{"id": "ZLECENIE-przyklad", "kind": "development", "state": "queued",
                             "title": "Przygotuj zmianę w kolejce", "queuedAt": now, "projectName": "Rozwój panelu"}],
            "nextTasks": [{"title": "Sprawdź kartę projektu", "projectName": "Projekt przykładowy", "taskId": "p|f|1"}],
            "runs": [dict(base, id="live", state="running", title="Rozbuduj widok projektu",
                          plan=[{"text": "Przejrzyj kod", "done": True}, {"text": "Piszę testy", "active": True},
                                {"text": "Sprawdź widok"}],
                          estimate={"basis": "milestones", "remaining": 480, "margin": 240, "pace": 300,
                                    "milestones": {"done": 1, "total": 3}, "elapsed": 300, "seconds": 780,
                                    "examples": 4, "typical": 600},
                          limitStart=.18, limitNow=.21, recent=["Sprawdzono układ widoku", "Zapisano zmiany",
                                                               "Uruchomiono testy"])]
        }
        for n, (title, state, outcome) in enumerate([
            ("Dodaj filtr na liście projektów", "done", "done"),
            ("Raport o stanie przykładowych zadań", "done", "review"),
            ("Przygotuj podgląd strony przed publikacją", "done", "blocked"),
            ("Sprawdź kolejność działań", "stopped", ""),
            ("Porównaj dane z karty", "error", ""),
        ]):
            fixture["runs"].append(dict(base, id=str(n), state=state, outcome=outcome, title=title, endedAt=now,
                                        choiceReason="zmiana kodu", result="Przykładowy wynik pracy agenta"))
        httpd = None
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "agenci.json"
            path.write_text(json.dumps(fixture), encoding="utf-8")
            url = os.environ.get("PANEL_AGENCI_TEST_URL")
            if not url:
                from http.server import ThreadingHTTPServer
                import threading
                from unittest.mock import patch
                patcher = patch.object(server, "data_cached", lambda: json.dumps(server.preview_data()))
                patcher.start()
                self.addCleanup(patcher.stop)
                httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
                threading.Thread(target=httpd.serve_forever, daemon=True).start()
                url = "http://127.0.0.1:%d/" % httpd.server_address[1]
            env = dict(os.environ)
            if Path("/opt/ms-playwright").is_dir():
                env.setdefault("PLAYWRIGHT_BROWSERS_PATH", "/opt/ms-playwright")
            try:
                proc = subprocess.run([PW, "-c", BROWSER, url, str(path), env.get("PANEL_AGENCI_ZRZUTY", "")],
                                      env=env, text=True, capture_output=True, timeout=90)
                self.assertEqual(proc.returncode, 0, proc.stderr)
            finally:
                if httpd:
                    httpd.shutdown()
                    httpd.server_close()
