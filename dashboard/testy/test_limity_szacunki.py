"""Wspólny stan limitów, szacunki i wybór wykonawcy w panelu."""
import datetime
import json
from pathlib import Path
import subprocess
import time
import unittest
from unittest.mock import patch

from test_agenci_widok import event_tool
from wspolne import Baza, TODAY, agents, projekt, server
import agent_progress


class Limity(Baza):
    def test_log_i_sesja_zasilaja_stan_po_restarcie(self):
        root = Path(self.tmp)
        home = root / "codex"
        orders = root / "zlecenia"
        orders.mkdir()
        (orders / "ZLECENIE-proba.md").write_text("# Próba", encoding="utf-8")
        now = time.time()
        stamp = datetime.datetime.fromtimestamp(now, datetime.timezone.utc).isoformat()
        log = [
            {"type": "rate_limit_event", "timestamp": stamp, "rate_limit_info": {"unifiedWindows": {
                "five_hour": {"utilization": .23, "resetsAt": now + 60},
                "seven_day": {"utilization": .56, "resetsAt": now + 600}}}},
            event_tool("Bash", {"description": "Uruchamia testy", "command": "python3 -m unittest"}),
            event_tool("Edit", {"file_path": "panel.html"}),
        ]
        (orders / "ZLECENIE-proba.log").write_text("\n".join(map(json.dumps, log)), encoding="utf-8")
        folder = home / "sessions" / "2026" / "11" / "24"
        folder.mkdir(parents=True)
        session = folder / "rollout-proba.jsonl"
        session.write_text("\n".join(map(json.dumps, [
            {"type": "event_msg", "payload": {"type": "user_message", "message": "Treść prywatna"}},
            {"type": "event_msg", "timestamp": stamp, "payload": {"type": "token_count", "rate_limits": {
                "primary": {"window_minutes": 300, "used_percent": 12, "resets_at": now + 60},
                "secondary": {"window_minutes": 10080, "used_percent": 41, "resets_at": now + 600}}}},
        ])), encoding="utf-8")
        manager = self.new_manager(PANEL_ROZWOJ_DIR=str(orders), PANEL_CODEX_HOME=str(home))
        snapshot = manager.snapshot()
        usage = snapshot["usage"]
        self.assertEqual([usage[k] for k in ("five", "seven", "codexFive", "codexSeven")], [.23, .56, .12, .41])
        self.assertEqual(snapshot["development"][0]["recent"], ["Bash: Uruchamia testy", "Edit: panel.html"])
        self.assertNotIn("Treść prywatna", json.dumps(snapshot))
        restarted = self.new_manager()
        self.assertEqual(restarted.usage_state(), usage)
        with patch("agents.time.time", return_value=now + 90):
            expired = restarted.usage_state()
        self.assertTrue(expired["fiveNew"])
        self.assertEqual((expired["five"], expired["seven"]), (0, .56))

    def test_limit_codex_z_logu_rozwoju(self):
        root = Path(self.tmp)
        (root / "ZLECENIE-codex.md").write_text("# Codex", encoding="utf-8")
        event = {"type": "event_msg", "payload": {"type": "token_count", "rate_limits": {
            "primary": {"window_minutes": 300, "used_percent": 33}}}}
        (root / "ZLECENIE-codex.log").write_text(json.dumps(event), encoding="utf-8")
        manager = self.new_manager(PANEL_ROZWOJ_DIR=str(root))
        self.assertEqual(manager.snapshot()["usage"]["codexFive"], .33)


class Szacunki(unittest.TestCase):
    def test_mediana_postep_i_kolejka(self):
        rows = [dict(tool="codex", kind="task", category="repo", state="done",
                     durationMs=seconds * 1000, limitStart=.1, limitNow=.1 + used, tokensIn=tokens)
                for seconds, used, tokens in [(40, .02, 100), (60, .06, 400), (150, .04, 250)]]
        self.assertEqual(agent_progress.estimate(rows[:2], "codex", "repo"), {"examples": 2})
        self.assertEqual(agent_progress.estimate(rows, "claude", "repo"), {"examples": 0})
        typical = agent_progress.estimate(rows, "codex", "repo")
        self.assertEqual((typical["seconds"], typical["tokens"]), (60, 250))
        self.assertAlmostEqual(typical["limit"], .04)
        start = datetime.datetime.fromtimestamp(100).isoformat()
        row = {"startedAt": start, "plan": [{"text": text, "done": done} for text, done in
                (("po pierwsze", True), ("po drugie", False), ("po trzecie", False))]}
        running = agent_progress.estimate_running(typical, row, 130)
        # 2026-11-25 (kamienie milowe): pozostałe kamienie z tempa (30 s na kamień → 60 s) ważone z historią
        # (60 s × 2/3 = 40 s) wagą 1/2 po jednym kamieniu → zostało 50 s, razem 80 s (dawniej 30 s × 3/1 = 90 s)
        self.assertEqual(running["seconds"], 80)
        self.assertEqual(running["basis"], "milestones")
        queued = [{"estimate": dict(typical)}, {"estimate": dict(typical)}]
        total = agent_progress.estimate_queue([{"estimate": running}], queued, 1, 130)
        self.assertEqual([r["estimate"]["start"] for r in queued], [180, 240])
        self.assertEqual([r["estimate"]["end"] for r in queued], [240, 300])
        self.assertEqual((total["seconds"], total["tokens"]), (120, 500))


class Wykonawca(Baza):
    def _choose(self, task):
        return self.manager.choose_task_tool(task, {}, self.folder, decide=True)

    def test_decyzja_claude_i_pamiec_dnia(self):
        self.set_mode("decyzja-codex")
        task = self.task("Zadanie A")
        self.assertEqual(self._choose(task), ("codex", "Wybrał Claude: Zmiana kodu i wolny limit"))
        decision = self.manager._state["decisions"][projekt.task_key(task)]
        self.assertEqual(decision["cost"]["decisionTokensIn"], 42)
        with patch.object(self.manager, "_ask_executor") as ask:
            self.assertEqual(self._choose(task)[0], "codex")
            ask.assert_not_called()
        restarted = self.new_manager()
        with patch.object(restarted, "_ask_executor") as ask:
            self.assertEqual(restarted.choose_task_tool(task, {}, self.folder, decide=True)[0], "codex")
            ask.assert_not_called()

    def test_przypiecie_i_twarde_reguly(self):
        task = self.task("Zadanie A")
        for tool in ("claude", "codex"):
            detail = projekt.parse_detail(["  wykonawca: tylko " + tool])
            with patch.object(self.manager, "_ask_executor") as ask:
                self.assertEqual(self._choose(dict(task, detail=detail)), (tool, "Przypięcie wykonawcy"))
                ask.assert_not_called()
        now = time.time()
        self.manager._record_limits("codex", {"seven": (.9, now, now + 60)})
        with patch.object(self.manager, "_ask_executor") as ask:
            self.assertEqual(self._choose(task)[0], "claude")
            ask.assert_not_called()
        self.manager._tools["claude"].update(found=True, loggedIn=False)
        self.assertEqual(self._choose(task)[0], "")

    def test_decyzja_z_regul_po_przekroczeniu_czasu(self):
        task = dict(self.task("Zadanie C"), executor="agent", title="Napisz tekst")
        self.manager.refresh_tools(wait=True)
        with patch("agents.subprocess.run", side_effect=subprocess.TimeoutExpired("claude", 60)):
            tool, reason = self._choose(task)
        self.assertEqual(tool, "claude")
        self.assertIn("Decyzja z reguł", reason)

    def test_pm_uruchamia_gotowe_i_odmawia_zgody(self):
        original = self.task("Zadanie A")
        project = original["project"]
        tasks = [dict(original, date=TODAY), dict(original, title="Zgoda", date=TODAY, needs=["zgoda"]),
                 dict(original, title="Właściciel", date=TODAY, executor="ty"),
                 dict(original, title="Po poprzedniku", date=TODAY, waitingFor=[{"done": False}])]
        data = {"tasks": tasks}
        ready, waiting = self.manager._pm_tasks(data)
        self.assertEqual([t["title"] for t in ready], [original["title"]])
        self.assertEqual(waiting, {"czeka na zgodę": 1, "czeka na poprzedniki z po:": 1})
        answer = f"Raport\nUruchom: {project} | Zadanie A\nUruchom: {project} | Zgoda"
        with patch.object(self.manager, "load_projects", return_value=(data, {})), \
                patch.object(self.manager, "launch_task", return_value={"text": "W kolejce: Zadanie A"}) as launch:
            result = self.manager._pm_launches(answer, {(project, "Zadanie A"), (project, "Zgoda")})
        launch.assert_called_once_with(ready[0], data, pm=True)
        self.assertIn("W kolejce: Zadanie A", result)
        self.assertIn("Nie uruchomiono „Zgoda”", result)

    def test_format_zadania_z_czatow(self):
        data, index = server.load_projects()
        project = data["projects"][0]
        folder = index[project["id"]]
        self.assertIn("kto: agent", "\n".join(self.manager.run_rules("", datetime.date.today())))
        prompt = self.manager.assistant_prompt(data, index, "Zrób zadanie", "#asystent")
        self.assertIn("kto: agent", prompt)
        self.assertIn("kto: agent", self.manager.project_chat_prompt(project, folder, folder, "Zrób zadanie"))
