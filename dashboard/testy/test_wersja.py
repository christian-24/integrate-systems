"""Wersja panelu w /api/data: otwarta aplikacja przeładowuje się po wdrożeniu."""
import os
import tempfile
import unittest

from wspolne import server


class Wersja(unittest.TestCase):
    def test_zmienia_sie_z_plikiem(self):
        old = server.PAGE
        with tempfile.TemporaryDirectory() as d:
            server.PAGE = os.path.join(d, "panel.html")
            try:
                self.assertEqual(server.panel_version(), "")
                with open(server.PAGE, "w", encoding="utf-8") as f:
                    f.write("a")
                v1 = server.panel_version()
                self.assertRegex(v1, r"^[0-9a-f]{12}$")
                with open(server.PAGE, "w", encoding="utf-8") as f:
                    f.write("bb")
                self.assertNotEqual(server.panel_version(), v1)
            finally:
                server.PAGE = old


class Panel(unittest.TestCase):
    def test_bez_zdublowanych_funkcji(self):
        """Dwie funkcje o tej samej nazwie w panel.html: późniejsza po cichu zastępuje wcześniejszą."""
        import collections
        import re
        with open(server.PAGE, encoding="utf-8") as f:
            names = re.findall(r"^(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(", f.read(), re.M)
        self.assertEqual([n for n, c in collections.Counter(names).items() if c > 1], [])


if __name__ == "__main__":
    unittest.main()
