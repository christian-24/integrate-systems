"""Zadania właściciela bez kroków technicznych: pole `gałąź:` (zmiany agenta i scalenie w panelu)
oraz `pyta:` / `odpowiedź:` (krótki formularz; dane trafiają do zadania agenta z `po:`)."""
import os
import unittest

from test_runda3_agenci import GIT, Repo
from wspolne import agents, projekt


class Format(unittest.TestCase):
    def test_odczyt(self):
        d = projekt.parse_detail(["  gałąź: agent/2026-11-19-sec", "  pyta: Imię w commitach; E-mail w commitach",
                                  "  odpowiedź: Imię w commitach = Jan K", "  odpowiedź: E-mail = a@b.pl = x",
                                  "  gałąź: zla/galaz"])
        self.assertEqual(d["branch"], "agent/2026-11-19-sec")
        self.assertEqual(d["asks"], ["Imię w commitach", "E-mail w commitach"])
        self.assertEqual(d["answers"], [{"label": "Imię w commitach", "value": "Jan K"},
                                        {"label": "E-mail", "value": "a@b.pl = x"}])
        self.assertIn("gałąź: zla/galaz", d["notes"])

    def test_poprzednicy_daja_odpowiedzi(self):
        tasks = [{"id": "a", "detail": {"answers": [{"label": "E-mail", "value": "a@b.pl"}]}},
                 {"id": "b", "detail": {"answers": [{"label": "Inne", "value": "x"}]}}]
        task = {"detail": {"goal": "cel"}, "waitingFor": [{"id": "a", "done": True}, {"id": "b", "done": False}]}
        d = agents.with_answers(task, tasks)
        self.assertEqual(d["answers"], [{"label": "E-mail", "value": "a@b.pl"}])
        self.assertNotIn("answers", task["detail"])
        lines = agents.Manager.detail_lines(d)
        self.assertIn("- E-mail: a@b.pl", lines)


@unittest.skipUnless(GIT, "brak polecenia git")
class Galaz(Repo):
    def setUp(self):
        super().setUp()
        self.git("switch", "-q", "-c", "agent/2026-11-19-reczna")
        with open(os.path.join(self.folder, "plik.txt"), "w", encoding="utf-8") as f:
            f.write("zmiana\n")
        self.git("add", "plik.txt")
        self.git("commit", "-q", "-m", "zmiana agenta")
        self.git("switch", "-q", self.main)
        self.pid = self.task("Zadanie A")["project"]

    def test_zapis_pol(self):
        t = self.task("Zadanie A")
        self.assertTrue(projekt.set_detail(self.folder, "ZADANIA.md", t["line"], t["title"], "gałąź", "agent/x-1"))
        with self.assertRaises(ValueError):
            projekt.set_detail(self.folder, "ZADANIA.md", t["line"], t["title"], "gałąź", "master")
        self.assertTrue(projekt.set_detail(self.folder, "ZADANIA.md", t["line"], t["title"], "odpowiedź",
                                           ["Imię = Jan", "E-mail = a@b.pl"]))
        with self.assertRaises(ValueError):
            projekt.set_detail(self.folder, "ZADANIA.md", t["line"], t["title"], "odpowiedź", ["bez znaku"])
        d = self.task("Zadanie A")["detail"]
        self.assertEqual((d["branch"], [a["value"] for a in d["answers"]]), ("agent/x-1", ["Jan", "a@b.pl"]))

    def test_diff_i_scalenie_galezi_z_pola(self):
        m, b = self.manager, "agent/2026-11-19-reczna"
        code, text = m.diff("", self.pid, b)
        self.assertEqual(code, 200, text)
        self.assertIn("+zmiana", text)
        self.assertEqual(m.diff("", self.pid, "master")[0], 400)                      # tylko gałęzie agenta
        self.assertEqual(m.diff("", self.pid, "agent/nie-ma")[0], 409)
        code, err, extra = m.merge("", self.pid, b)
        self.assertEqual(code, 200, err)
        self.assertEqual(self.git("rev-parse", "HEAD"), extra["commit"])
        self.assertTrue(os.path.exists(os.path.join(self.folder, "plik.txt")))
        self.assertIn("nie ma zmian", m.merge("", self.pid, b)[1])                     # drugi raz nie


if __name__ == "__main__":
    unittest.main()
