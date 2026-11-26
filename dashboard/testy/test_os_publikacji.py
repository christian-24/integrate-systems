"""Marketing: jedna oś publikacji (decyzja właściciela 26.11) zamiast Kampanii, Wyników i Klientów."""
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
HTML = open(os.path.join(HERE, "..", "panel.html"), encoding="utf-8").read()


def fn(name):
    m = re.search(r"\nfunction " + name + r"\(.*?\n}\n", HTML, re.S)
    return m.group(0) if m else ""


class Os(unittest.TestCase):
    def test_zakladka_projektu_to_os(self):
        body = fn("wyTab")
        self.assertIn("osView(", body)
        for gone in ("wyKlienci", "wyWyniki", "mktView", "data-wysub"):
            self.assertNotIn(gone, body)

    def test_widok_marketing_to_os(self):
        body = fn("vMarketing")
        self.assertIn("osView(", body)
        self.assertNotIn("mkCampList", body)
        self.assertIn("Kanały i studio", body)

    def test_rodzaje_i_podglad(self):
        for txt in ("'Film'", "'Post'", "'Reklama Meta'", "'Reklama Google'", "data-ospick", "data-ostab", "Sponsorowane"):
            self.assertIn(txt, HTML)

    def test_endpointy(self):
        src = open(os.path.join(HERE, "..", "wyniki.py"), encoding="utf-8").read()
        self.assertIn('"/api/wyniki/os"', src)
        self.assertIn('"/api/wyniki/posty-api"', src)
        self.assertIn('"/api/reklama/tekst"', open(os.path.join(HERE, "..", "server.py"), encoding="utf-8").read())


if __name__ == "__main__":
    unittest.main()
