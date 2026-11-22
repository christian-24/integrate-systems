"""Asystent: fakty dla modelu (Twoje sprawy, po terminie, postęp) bez czytania plików."""
import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import agents  # noqa: E402


class Fakty(unittest.TestCase):
    def test_fakty(self):
        today = datetime.date(2026, 11, 22)
        data = {"projects": [{"id": "a", "name": "Alfa", "state": "active"}, {"id": "b", "name": "Beta", "state": "paused"}],
                "tasks": [
                    {"project": "a", "title": "Nagraj film", "executor": "ty", "state": "todo", "date": "2026-11-23", "kind": "zadanie"},
                    {"project": "a", "title": "Stare", "executor": "claude", "state": "todo", "date": "2026-11-20", "kind": "zadanie"},
                    {"project": "a", "title": "Zrobione", "executor": "ty", "state": "done", "date": "2026-11-21", "kind": "zadanie"},
                    {"project": "a", "title": "Daleko", "executor": "ty", "state": "todo", "date": "2027-01-10", "kind": "zadanie"},
                    {"project": "b", "title": "Wstrzymany", "executor": "ty", "state": "todo", "date": "2026-11-23", "kind": "zadanie"}]}
        f = agents.Manager.assistant_facts(data, today)
        self.assertIn("Alfa: 25% (1 z 4 zadań)", f)
        self.assertIn("Alfa | Nagraj film | 2026-11-23", f)
        self.assertIn("Alfa | Stare | 2026-11-20", f.split("Po terminie:")[1])
        self.assertNotIn("Daleko", f)
        self.assertNotIn("Wstrzymany", f)


if __name__ == "__main__":
    unittest.main()
