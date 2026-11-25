"""dirty_sources: dziennik uruchomienia z wpisami, w których „message” jest tekstem, nie wywraca stanu kopii (AttributeError)."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "standard"))
import agents  # noqa: E402


class ZrodlaZmian(unittest.TestCase):
    def test_wpis_tekstowy_w_dzienniku(self):
        with tempfile.TemporaryDirectory() as d:
            repo = os.path.join(d, "repo")
            os.makedirs(repo)
            runs = os.path.join(d, "runs")
            os.makedirs(runs)
            target = os.path.join(repo, "a.txt")
            lines = [
                {"type": "system", "message": "tekst %s tool_use" % repo},
                {"type": "assistant", "message": {"content": [
                    {"type": "tool_use", "name": "Edit", "input": {"file_path": target}}]}},
                {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Write", "input": "x %s" % repo}]}},
            ]
            with open(os.path.join(runs, "r1.log"), "w", encoding="utf-8") as f:
                f.write("\n".join(json.dumps(x) for x in lines) + "\n")
            m = agents.Manager.__new__(agents.Manager)
            import threading
            m._lock = threading.RLock()
            m.runs_dir = runs
            m._runs = {"r1": {"id": "r1", "kind": "task", "startedAt": "2099-01-01T00:00:00", "title": "T", "project": "p"}}
            out = m.dirty_sources(repo, ["a.txt"])
            self.assertEqual(len(out), 1)
            self.assertIn("a.txt", out[0]["files"])


if __name__ == "__main__":
    unittest.main()
