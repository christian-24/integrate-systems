"""Pytania do właściciela w KARTA.md (/api/question/answer) i logowanie narzędzi z panelu (/api/agent/login)."""
import os
import sys
import unittest

from test_serwer import Serwer
from wspolne import projekt

PYTANIA = """
## Pytania do właściciela
1. Pierwsze pytanie?
2. Drugie pytanie,
   z dalszym ciągiem?
- Trzecie jako punktor?
"""


class Pytania(Serwer):
    def setUp(self):
        super().setUp()
        self.karta = os.path.join(self.folder, "KARTA.md")
        with open(self.karta, "a", encoding="utf-8") as f:
            f.write(PYTANIA)

    def text(self):
        with open(self.karta, encoding="utf-8") as f:
            return f.read()

    def qs(self):
        return self.data()["projects"][0]["questions"]

    def test_odczyt(self):
        q = self.qs()
        self.assertEqual([(x["n"], x["text"], x["answer"]) for x in q],
                         [(1, "Pierwsze pytanie?", ""), (2, "Drugie pytanie, z dalszym ciągiem?", ""),
                          (3, "Trzecie jako punktor?", "")])

    def test_odpowiedz_zapis_zmiana_usuniecie(self):
        ans = lambda n, a: self.post("/api/question/answer", {"id": "projekt-testowy", "n": n, "answer": a})
        before = self.text()
        self.assertEqual(ans(2, "Tak,\n  na PC."), (200, {"ok": True, "error": ""}))
        self.assertIn("   z dalszym ciągiem?\n   Odpowiedź: Tak, na PC.\n- Trzecie", self.text())
        self.assertEqual(self.qs()[1]["answer"], "Tak, na PC.")
        self.assertEqual(self.qs()[1]["text"], "Drugie pytanie, z dalszym ciągiem?")
        self.assertEqual(ans(2, "Nie.")[0], 200)
        self.assertEqual(self.text().count("Odpowiedź:"), 1)
        self.assertEqual(ans(1, "Raz")[0], 200)
        self.assertEqual([x["answer"] for x in self.qs()], ["Raz", "Nie.", ""])
        self.assertEqual(ans(1, "")[0], 200)
        self.assertEqual(ans(2, " ")[0], 200)
        self.assertEqual(self.text(), before)                       # usunięcie odpowiedzi przywraca plik
        self.assertFalse([f for f in os.listdir(self.folder) if f.startswith(".tmp")])

    def test_odmowy(self):
        ans = lambda body: self.post("/api/question/answer", body)[0]
        self.assertEqual(ans({"id": "nie-ma", "n": 1, "answer": "x"}), 404)
        self.assertEqual(ans({"id": "projekt-testowy", "n": 9, "answer": "x"}), 400)
        self.assertEqual(ans({"id": "projekt-testowy", "n": "1", "answer": "x"}), 400)
        self.assertEqual(ans({"id": "projekt-testowy", "n": 1, "answer": "x" * 2001}), 400)
        self.assertEqual(ans({"id": "projekt-testowy", "n": 1, "answer": 5}), 400)

    def test_karta_bez_sekcji(self):
        self.assertEqual(projekt.parse_questions(projekt.parse_doc("# K\n\n## Cel\nX\n")[2]), [])


class Logowanie(Serwer):
    def test_otwiera_terminal(self):
        calls = []
        self.manager.launcher = lambda args, **kw: calls.append(args)
        status, body = self.post("/api/agent/login", {"tool": "claude"})
        if sys.platform == "darwin" or os.name == "nt":
            self.assertEqual((status, body.get("opened")), (200, True))
            self.assertEqual(len(calls), 1)
            joined = " ".join(calls[0])
            self.assertIn("auth login", joined)
            if sys.platform == "darwin":
                self.assertEqual(calls[0][:2], ["osascript", "-e"])
                self.assertIn('tell application "Terminal"', calls[0][2])
        else:                                      # serwer bez okna: logowanie przez panel (adres strony logowania)
            self.assertEqual(status, 200)
            self.assertTrue(body.get("url", "").startswith("https://"))
            self.assertEqual(calls, [])
        self.assertEqual(self.post("/api/agent/login", {"tool": "inne"})[0], 400)

    def test_ponowne_sprawdzenie(self):
        status, body = self.post("/api/agent/recheck", {})
        self.assertEqual(status, 200)
        self.assertEqual(set(body["loggedIn"]), {"claude", "codex"})


if __name__ == "__main__":
    unittest.main()
