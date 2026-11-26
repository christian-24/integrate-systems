"""Grupa agenci (2026-11-25): kamienie milowe w poleceniu zadania, szacunek zawężany kamieniami (atrapa strumienia),
sekcja Użycie (usage_stats) i brak Planu dnia w widoku Agenci."""
import datetime
import json
import math
import os
from pathlib import Path
import re
import tempfile
import time
import unittest

from wspolne import Baza, server
import agent_progress

HERE = os.path.dirname(os.path.abspath(__file__))
PANEL = os.path.join(os.path.dirname(HERE), "panel.html")
MILESTONES = ["Przejrzyj kod", "Dodaj sekcję", "Napisz testy", "Sprawdź widok", "Zapisz wynik"]


def todo(done, active=None):
    """Zdarzenie TodoWrite strumienia Claude: pierwsze `done` kamieni ukończone, `active` w toku."""
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "TodoWrite", "id": "t", "input": {
        "todos": [{"content": text, "status": "completed" if i < done else "in_progress" if i == active else "pending"}
                  for i, text in enumerate(MILESTONES)]}}]}}


def codex_plan(done):
    return {"type": "item.updated", "item": {"type": "todo_list", "items": [
        {"text": text, "completed": i < done} for i, text in enumerate(MILESTONES)]}}


class Polecenie(Baza):
    def test_regula_kamieni_claude_i_codex(self):
        claude = self.manager.task_prompt("claude", "P", "ZADANIA.md", 4, "Tytuł", "")
        codex = self.manager.task_prompt("codex", "P", "ZADANIA.md", 4, "Tytuł", "")
        for prompt in (claude, codex):
            self.assertIn("3–7 kamieni milowych", prompt)
            self.assertIn("odhaczaj je po kolei", prompt)
        self.assertIn("TodoWrite", claude)
        self.assertNotIn("update_plan", claude)
        self.assertIn("update_plan", codex)
        self.assertNotIn("TodoWrite", codex)

    def test_snapshot_ma_uzycie(self):
        stats = self.manager.snapshot()["stats"]
        self.assertEqual(set(stats), {"claude", "codex"})
        self.assertEqual(stats["claude"]["runs7"], 0)
        self.assertIsNone(stats["codex"]["successRate"])


class Szacunek(unittest.TestCase):
    TYPICAL = {"examples": 5, "seconds": 600, "low": 400, "high": 900}
    START = 1000

    def run_at(self, plan):
        return {"startedAt": datetime.datetime.fromtimestamp(self.START).isoformat(), "plan": plan}

    def test_strumien_claude_zaweza_szacunek(self):
        plan = []
        agent_progress.update_plan(plan, todo(0, 0), self.START + 20)
        before = agent_progress.estimate_running(self.TYPICAL, self.run_at(plan), self.START + 100)
        self.assertEqual(before["basis"], "history")                  # przed kamieniem: mediana, jedna liczba
        self.assertEqual((before["typical"], before["seconds"], before["remaining"]), (600, 600, 500))
        self.assertEqual(before["milestones"], {"done": 0, "total": 5})
        agent_progress.update_plan(plan, todo(1, 1), self.START + 120)
        first = agent_progress.estimate_running(self.TYPICAL, self.run_at(plan), self.START + 130)
        # tempo 120 s na kamień: bieżący 110 s + 3 × 120 s = 470 s; historia 600 × 4/5 = 480 s; waga 1/2 → 475 s
        self.assertEqual(first["basis"], "milestones")
        self.assertEqual((first["pace"], first["remaining"]), (120, 475))
        self.assertAlmostEqual(first["margin"], 475 * .5)
        agent_progress.update_plan(plan, todo(2, 2), self.START + 240)
        self.assertEqual([s.get("doneAt") for s in plan], [self.START + 120, self.START + 240, None, None, None])
        second = agent_progress.estimate_running(self.TYPICAL, self.run_at(plan), self.START + 240)
        self.assertEqual(second["remaining"], 360)                    # 3 × 120 s, historia 600 × 3/5, waga 2/3
        self.assertAlmostEqual(second["margin"], 360 * .5 / math.sqrt(2))
        self.assertLess(second["margin"], first["margin"])             # po każdym kamieniu dokładniej
        self.assertLess(second["margin"] / second["remaining"], first["margin"] / first["remaining"])
        agent_progress.update_plan(plan, todo(5), self.START + 600)
        last = agent_progress.estimate_running(self.TYPICAL, self.run_at(plan), self.START + 610)
        self.assertEqual((last["remaining"], last["seconds"]), (0, 610))

    def test_bez_historii_szacunek_z_tempa(self):
        plan = []
        agent_progress.update_plan(plan, codex_plan(0), self.START)
        self.assertNotIn("seconds", agent_progress.estimate_running({"examples": 1}, self.run_at(plan), self.START + 50))
        agent_progress.update_plan(plan, codex_plan(1), self.START + 60)
        est = agent_progress.estimate_running({"examples": 1}, self.run_at(plan), self.START + 60)
        self.assertEqual((est["basis"], est["remaining"]), ("milestones", 240))

    def test_doneat_ze_strumienia_zlecenia(self):
        start = datetime.datetime(2026, 11, 25, 10, 0, tzinfo=datetime.timezone.utc)
        events = [dict(todo(0, 0), timestamp=start.isoformat()),
                  dict(todo(1, 1), timestamp=(start + datetime.timedelta(minutes=3)).isoformat()),
                  dict(todo(2, 2), timestamp=(start + datetime.timedelta(minutes=7)).isoformat()),
                  todo(3, 3)]                                          # zdarzenie bez czasu: bez doneAt
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder) / "ZLECENIE-kamienie"
            base.with_suffix(".md").write_text("# Kamienie", encoding="utf-8")
            base.with_suffix(".log").write_text("\n".join(map(json.dumps, events)) + "\n", encoding="utf-8")
            plan = agent_progress.Orders(folder).snapshot()[0]["plan"]
        stamps = [s.get("doneAt") for s in plan]
        self.assertEqual(stamps[:2], [(start + datetime.timedelta(minutes=m)).timestamp() for m in (3, 7)])
        self.assertEqual(stamps[2:], [None, None, None])

    def test_mediana_z_zakresem(self):
        rows = [dict(tool="claude", kind="task", state="done", durationMs=s * 1000) for s in (60, 120, 180, 240, 900)]
        est = agent_progress.estimate(rows, "claude", "text")
        self.assertEqual((est["seconds"], est["low"], est["high"]), (180, 120, 240))


class Uzycie(unittest.TestCase):
    def test_statystyki_z_zapisow(self):
        now = time.time()
        iso = lambda hours: datetime.datetime.fromtimestamp(now - hours * 3600).isoformat()  # noqa: E731
        rows = [
            dict(id="a", tool="claude", state="done", startedAt=iso(.5), durationMs=600000, tokensIn=1000, tokensOut=500,
                 costUsd=.2, title="Mały", limitStart=.1, limitNow=.15),
            dict(id="b", tool="claude", state="done", outcome="blocked", startedAt=iso(30), durationMs=1200000,
                 tokensIn=90000, tokensOut=1000, title="Duży"),
            dict(id="c", tool="claude", state="error", startedAt=iso(50), tokensIn=10, title="Błąd"),
            dict(id="d", tool="claude", state="stopped", startedAt=iso(60), tokensIn=5, title="Zatrzymany"),
            dict(id="e", tool="claude", state="done", startedAt=iso(8 * 24), durationMs=1, tokensIn=10 ** 7, title="Stary"),
            dict(id="f", tool="codex", state="running", startedAt=iso(.1), tokensIn=300, title="W toku"),
        ]
        stats = agent_progress.usage_stats(rows, now)
        c, x = stats["claude"], stats["codex"]
        self.assertEqual((c["runs7"], c["tokens7"]), (4, 1500 + 91000 + 15))
        self.assertEqual(c["avgMs"], 900000)
        self.assertEqual((c["ok7"], c["finished7"]), (1, 3))          # blokada i błąd nieudane, zatrzymane poza
        self.assertAlmostEqual(c["successRate"], 1 / 3)
        self.assertEqual([r["id"] for r in c["top"]], ["b", "a", "c", "d"])
        self.assertAlmostEqual(c["top"][1]["limit"], .05)
        self.assertEqual((x["runs7"], x["tokens7"], x["top"], x["successRate"]), (1, 300, [], None))

    def test_dane_przykladowe(self):
        stats = server.preview_data()["agents"]["stats"]["claude"]
        self.assertEqual((stats["runs7"], stats["finished7"], stats["ok7"]), (5, 3, 2))
        self.assertTrue(stats["top"])


class Widok(unittest.TestCase):
    def test_bez_planu_dnia_w_agentach(self):
        html = Path(PANEL).read_text(encoding="utf-8")
        body = html[html.index("function vAgenci(){"):]
        body = body[:body.index("\n}\n")]
        self.assertNotIn("planBox", html)
        self.assertNotIn("/api/plan/ask", html)
        self.assertNotIn("Ułóż plan", html)
        self.assertNotIn("plan dnia", body.replace("plan dnia jest w Asystencie", ""))
        self.assertIn("ppSec('ag-runs','ag-runs','Uruchomienia'", body)   # zwinięte domyślnie (open0 false)
        self.assertRegex(body, r"ppSec\('ag-runs','ag-runs','Uruchomienia',[^;]*,false,")
        self.assertIn("agUseHtml(a)", body)
        self.assertTrue(re.search(r"'Kamień '\+\(i\+1\)\+' z '", html))


if __name__ == "__main__":
    unittest.main()
