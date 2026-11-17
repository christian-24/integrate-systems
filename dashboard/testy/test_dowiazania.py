"""Pliki standardu jako dowiązania: zapis z panelu trafia do pliku docelowego, dowiązanie zostaje."""
import os
import unittest

from wspolne import Baza, projekt


class Dowiazania(Baza):
    def setUp(self):
        super().setUp()
        self._cards = projekt.CARDS
        projekt.CARDS = os.path.join(self.tmp, "karty")
        self.addCleanup(setattr, projekt, "CARDS", self._cards)

    def link(self, cel):
        os.makedirs(cel, exist_ok=True)
        zad = os.path.join(self.folder, "ZADANIA.md")
        os.replace(zad, os.path.join(cel, "ZADANIA.md"))
        os.symlink(os.path.join(cel, "ZADANIA.md"), zad)
        return zad

    def test_dowiazanie_poza_kartami_odrzucone(self):
        self.link(os.path.join(self.tmp, "gdzie-indziej"))
        t = self.task("Zadanie B")
        with self.assertRaises(ValueError):
            projekt.update_task(self.folder, "ZADANIA.md", t["line"], "Zadanie B", {"state": "doing"})

    def test_zapis_przez_dowiazanie(self):
        cel = projekt.CARDS
        zad = self.link(cel)
        t = self.task("Zadanie B")
        ok = projekt.update_task(self.folder, "ZADANIA.md", t["line"], "Zadanie B", {"state": "doing"})
        self.assertTrue(ok)
        self.assertTrue(os.path.islink(zad))
        with open(os.path.join(cel, "ZADANIA.md"), encoding="utf-8") as f:
            self.assertIn("- [~] Zadanie B", f.read())
        self.assertEqual(self.task("Zadanie B")["state"], "doing")

    def test_agent_dostaje_folder_karty(self):
        cel = projekt.CARDS
        self.link(cel)
        self.set_mode("zostaw")
        code, err, extra = self.run_task("Zadanie A")
        self.assertEqual(code, 200, err)
        self.wait(extra["id"])
        argv = self.calls()[-1]["argv"]
        self.assertIn("--add-dir", argv)
        self.assertEqual(argv[argv.index("--add-dir") + 1], os.path.realpath(cel))

    def test_bez_dowiazan_bez_add_dir(self):
        self.set_mode("zostaw")
        code, err, extra = self.run_task("Zadanie A")
        self.assertEqual(code, 200, err)
        self.wait(extra["id"])
        self.assertNotIn("--add-dir", self.calls()[-1]["argv"])


if __name__ == "__main__":
    unittest.main()
