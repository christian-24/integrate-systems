"""Pole karty „- grafiki: tylko zdjęcia” i zapis „bez $imagegen” w zadaniu: Codex dostaje zasady bez generowania obrazów."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "standard"))
import agents  # noqa: E402


class TylkoZdjecia(unittest.TestCase):
    def test_pole_karty(self):
        self.assertTrue(agents.photos_only("# K\n- grafiki: tylko zdjęcia\n"))
        self.assertTrue(agents.photos_only("- Grafiki: tylko prawdziwe zdjęcia"))
        self.assertFalse(agents.photos_only("- grafiki: dowolne"))
        self.assertFalse(agents.photos_only(""))

    def test_zapis_w_zadaniu(self):
        self.assertTrue(agents.photos_only("", "cel: tryb „Zachowaj zdjęcie” (Pillow, bez $imagegen)"))
        self.assertFalse(agents.photos_only("", "Przygotuj grafikę do posta"))

    def test_zasady_w_poleceniu_codexa(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "KARTA.md"), "w", encoding="utf-8") as f:
                f.write("# Karta\n- grafiki: tylko zdjęcia\n")
            zad = os.path.join(d, "ZADANIA.md")
            open(zad, "w", encoding="utf-8").close()
            rules = agents.Manager._image_rules(agents.Manager.__new__(agents.Manager), zad, "Przygotuj reklamę S1", None)
            self.assertIs(rules, agents.CODEX_PHOTO_RULES)
            os.remove(os.path.join(d, "KARTA.md"))
            rules = agents.Manager._image_rules(agents.Manager.__new__(agents.Manager), zad, "Przygotuj grafikę", None)
            self.assertIs(rules, agents.CODEX_IMAGE_RULES)


if __name__ == "__main__":
    unittest.main()
