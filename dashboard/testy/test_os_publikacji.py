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
        srv = open(os.path.join(HERE, "..", "server.py"), encoding="utf-8").read()
        self.assertIn('"/api/reklama/tekst"', srv)
        self.assertIn('"/api/reklama/podglad"', srv)

    def test_kopiuj_obraz(self):
        self.assertIn("data-oscopy", HTML)
        self.assertIn("ClipboardItem", HTML)

    def test_obraz_trzech_podgladow(self):
        import sys
        sys.path.insert(0, os.path.join(HERE, ".."))
        import podglad
        if podglad.Image is None:
            self.skipTest("brak Pillow")
        import tempfile
        from PIL import Image
        d = tempfile.mkdtemp()
        Image.new("RGB", (1080, 1350), (200, 200, 200)).save(os.path.join(d, "grafika.png"))
        Image.new("RGB", (1080, 1920), (90, 90, 90)).save(os.path.join(d, "grafika-story.png"))
        with open(os.path.join(d, "post.md"), "w", encoding="utf-8") as f:
            f.write("# S1\n\n**Tekst główny:** Mata na blasze. Napisz model auta.\n\n**Nagłówek:** Wygłuszanie drzwi od 1 590 zł\n")
        png = podglad.render(d, "Shield & Silent Studio", "S1: Drzwi", True, "czw. 26.11")
        im = Image.open(__import__("io").BytesIO(png))
        self.assertGreater(im.width, 1500)
        self.assertEqual(podglad.parse(open(os.path.join(d, "post.md"), encoding="utf-8").read())["head"], "Wygłuszanie drzwi od 1 590 zł")


if __name__ == "__main__":
    unittest.main()
