"""Runda 5, serwer i agenci: kontrola serwera przy zadaniu (sprawdza:, /api/task/close-checked), licznik wyników
do kampanii (licznik:, /api/task/state z count, /api/task/count), skutki pytań (skutek:, /api/question/answer
z accept), unlocks w /api/data, prompt agenta i odmowa scalenia gałęzi z plikami sekretów."""
import json
import os
import unittest

from test_runda3_agenci import GIT, Repo
from test_serwer import Serwer
from wspolne import TODAY, TOMORROW, agents, projekt, server

PID = "projekt-testowy"
LATER = "2030-01-15"

ZADANIA5 = """# Zadania: Projekt testowy

## Etap: Pierwszy
termin: %(tomorrow)s

- [ ] Sprawdź kopię nocną | kto: ty | sprawdza: kopia
- [ ] Sprawdź panel | kto: ty | sprawdza: panel
- [ ] Opisz wdrożenie | kto: claude | sprawdza: plik notatki/wdrozenie.md
- [ ] Bez kontroli | kto: claude
- [ ] Wyślij zaproszenia | kto: ty | licznik: zaproszenia
- [ ] Zapisz rozmowy | kto: ty | licznik: rozmowy
- [ ] Przygotuj makietę | kto: ty
- [ ] Zbuduj stronę | kto: claude | po: makietę
- [ ] Opublikuj stronę | kto: claude | po: makietę
- [ ] Popraw teksty | kto: claude

## Do rozplanowania
""" % {"tomorrow": TOMORROW}

KAMPANIA = """# Kampania: Zaproszenia

- stan: w toku
- cel: rozmowy z firmami
- miernik: zaproszenia
- cel liczbowy: 40
- wynik: 2
- kanały: LinkedIn
- start: %(today)s
- koniec: %(later)s
- budżet: 0

## Grupa docelowa
Firmy z partii 1.

## Przekaz
Oferta.

## Harmonogram
- [ ] Post o ofercie | kanał: LinkedIn | kiedy: %(later)s | kto: ty

## Wyniki i wnioski
""" % {"today": TODAY, "later": LATER}

PYTANIA5 = """
## Pytania do właściciela
1. Czy przesunąć stronę na później?
   propozycja: tak, strona po makiecie i teksty zamknięte
   skutek: kiedy: %(later)s → Zbuduj stronę
   skutek: po: Popraw teksty → Opublikuj stronę
   skutek: stan: zrobione → Popraw teksty
   skutek: kiedy: %(later)s → Nie ma takiego zadania
2. Pytanie bez propozycji?
3. Kolor logo?
   propozycja: niebieski
""" % {"later": LATER}


class Runda5(Serwer):
    def setUp(self):
        super().setUp()
        self.write("ZADANIA.md", ZADANIA5)
        self.write("kampanie/zaproszenia.md", KAMPANIA)
        with open(os.path.join(self.folder, "KARTA.md"), "a", encoding="utf-8") as f:
            f.write(PYTANIA5)

    def write(self, rel, text):
        path = os.path.join(self.folder, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    def text(self, rel):
        with open(os.path.join(self.folder, rel), encoding="utf-8") as f:
            return f.read()

    def health(self, text):
        with open(self.health_file, "w", encoding="utf-8") as f:
            f.write(text)

    def t(self, title, data=None):
        return next(x for x in (data or self.data())["tasks"] if x["title"] == title)

    def lines_after(self, title, rel="ZADANIA.md"):
        """Wiersz zadania i wcięte wiersze pod nim."""
        lines = self.text(rel).split("\n")
        i = next(k for k, line in enumerate(lines) if line.startswith("- [") and line[6:].startswith(title))
        out = [lines[i]]
        for line in lines[i + 1:]:
            if not projekt.is_detail(line):
                break
            out.append(line)
        return out


class Kontrola(Runda5):
    def test_check_w_danych(self):
        self.health("kopia=ok\npanel=zle\n")
        data = self.data()
        at = data["server"]["at"]
        self.assertEqual(self.t("Sprawdź kopię nocną", data)["check"], {"key": "kopia", "ok": True, "at": at})
        self.assertEqual(self.t("Sprawdź panel", data)["check"]["ok"], False)
        self.assertIs(self.t("Opisz wdrożenie", data)["check"]["ok"], False)
        self.assertIsNone(self.t("Bez kontroli", data).get("check"))
        self.write("notatki/wdrozenie.md", "# Wdrożenie\n")
        check = self.t("Opisz wdrożenie")["check"]
        self.assertTrue(check["ok"])
        self.assertIn("notatki/wdrozenie.md", check["key"])

    def test_check_bez_serwera(self):
        data = self.data()
        self.assertIsNone(data["server"])
        self.assertIsNot(self.t("Sprawdź kopię nocną", data)["check"]["ok"], True)

    def test_zamknij_na_podstawie_kontroli(self):
        self.health("kopia=ok\npanel=zle\n")
        os.utime(self.health_file, (1795075200, 1795075200))
        t = self.t("Sprawdź kopię nocną")
        stamp = server.check_stamp(t["check"]["at"])
        code, body = self.post("/api/task/close-checked", {"id": t["id"], "title": t["title"]})
        self.assertEqual(code, 200, body)
        rows = self.lines_after("Sprawdź kopię nocną")
        self.assertTrue(rows[0].startswith("- [x] Sprawdź kopię nocną"))
        self.assertEqual(rows[1:], ["  zamknięte na podstawie kontroli serwera z %s" % stamp])
        self.assertRegex(stamp, r"^\d{4}-\d\d-\d\d \d\d:\d\d$")
        self.assertEqual(self.t("Sprawdź kopię nocną")["state"], "done")
        # ponownie: już zrobione
        self.assertEqual(self.post("/api/task/close-checked", {"id": t["id"], "title": t["title"]})[0], 409)

    def test_zamknij_odmowy(self):
        self.health("kopia=ok\npanel=zle\n")
        before = self.text("ZADANIA.md")
        for title in ("Sprawdź panel", "Bez kontroli", "Opisz wdrożenie"):
            t = self.t(title)
            code, body = self.post("/api/task/close-checked", {"id": t["id"], "title": t["title"]})
            self.assertEqual(code, 409, title)
            self.assertIn("nie potwierdza", body["error"])
        t = self.t("Sprawdź kopię nocną")
        self.assertEqual(self.post("/api/task/close-checked", {"id": t["id"], "title": "Inny tytuł"})[0], 409)
        self.assertEqual(self.post("/api/task/close-checked", {"id": "nie-ma|ZADANIA.md|1", "title": "x"})[0], 404)
        self.assertEqual(self.post("/api/task/close-checked", {"id": "zly", "title": "x"})[0], 400)
        self.assertEqual(self.text("ZADANIA.md"), before)


class Odblokowuje(Runda5):
    def test_unlocks(self):
        data = self.data()
        mak = self.t("Przygotuj makietę", data)
        self.assertEqual(mak["unlockCount"], 2)
        self.assertEqual([(u["id"], u["title"], u["executor"]) for u in mak["unlocks"]],
                         [(self.t("Zbuduj stronę", data)["id"], "Zbuduj stronę", "claude"),
                          (self.t("Opublikuj stronę", data)["id"], "Opublikuj stronę", "claude")])
        self.assertEqual(set(mak["unlocks"][0]), {"id", "title", "executor", "date"})
        self.assertEqual((self.t("Bez kontroli", data)["unlocks"], self.t("Bez kontroli", data)["unlockCount"]),
                         ([], 0))


class Licznik(Runda5):
    def campaign(self, data=None):
        return next(c for c in (data or self.data())["campaigns"] if c["file"] == "kampanie/zaproszenia.md")

    def test_stan_z_licznikiem(self):
        t = self.t("Wyślij zaproszenia")
        code, body = self.post("/api/task/state", {"id": t["id"], "title": t["title"], "state": "done", "count": 8})
        self.assertEqual(code, 200, body)
        self.assertEqual((body["counter"], body["count"]), ("zaproszenia", 8))
        self.assertTrue(self.lines_after("Wyślij zaproszenia")[0].startswith("- [x] "))
        text = self.text("kampanie/zaproszenia.md")
        section = text.split("## Wyniki i wnioski", 1)[1]
        self.assertIn("- %s · zaproszenia 8 · Wyślij zaproszenia" % TODAY, section)
        camp = self.campaign()
        self.assertEqual(camp["counters"], {"zaproszenia": 8})
        self.assertEqual(camp["result"], 8)                     # max(ręczny wynik 2, suma licznika miernika)
        # osobne dopisanie, bez zmiany stanu
        t = self.t("Wyślij zaproszenia")
        code, body = self.post("/api/task/count", {"id": t["id"], "title": t["title"], "count": 3})
        self.assertEqual(code, 200, body)
        camp = self.campaign()
        self.assertEqual(camp["counters"], {"zaproszenia": 11})
        self.assertEqual(camp["result"], 11)
        # licznik spoza miernika nie zmienia wyniku
        t = self.t("Zapisz rozmowy")
        self.assertEqual(self.post("/api/task/count", {"id": t["id"], "title": t["title"], "count": 5})[0], 200)
        camp = self.campaign()
        self.assertEqual(camp["counters"], {"zaproszenia": 11, "rozmowy": 5})
        self.assertEqual(camp["result"], 11)

    def test_licznik_odmowy(self):
        before = (self.text("ZADANIA.md"), self.text("kampanie/zaproszenia.md"))
        t = self.t("Wyślij zaproszenia")
        post = lambda path, **kw: self.post(path, dict({"id": t["id"], "title": t["title"]}, **kw))[0]
        self.assertEqual(post("/api/task/state", state="todo", count=3), 400)
        for bad in (-1, 1.5, "8", True, 10 ** 7):
            self.assertEqual(post("/api/task/count", count=bad), 400, bad)
        self.assertEqual(self.post("/api/task/count", {"id": t["id"], "title": "Inny", "count": 1})[0], 409)
        other = self.t("Bez kontroli")
        self.assertEqual(self.post("/api/task/count", {"id": other["id"], "title": other["title"], "count": 1})[0], 400)
        self.assertEqual((self.text("ZADANIA.md"), self.text("kampanie/zaproszenia.md")), before)
        # bez kampanii w toku: odmowa i stan zadania bez zmian
        self.write("kampanie/zaproszenia.md", KAMPANIA.replace("- stan: w toku", "- stan: plan"))
        self.assertEqual(post("/api/task/state", state="done", count=3), 409)
        self.assertTrue(self.lines_after("Wyślij zaproszenia")[0].startswith("- [ ] "))

    def test_kampania_wskazana_polem(self):
        self.write("kampanie/druga.md", KAMPANIA.replace("Zaproszenia", "Druga").replace("- stan: w toku",
                                                                                         "- stan: plan"))
        text = self.text("ZADANIA.md").replace("licznik: rozmowy", "licznik: rozmowy | kampania: kampanie/druga.md")
        self.write("ZADANIA.md", text)
        t = self.t("Zapisz rozmowy")
        code, body = self.post("/api/task/state", {"id": t["id"], "title": t["title"], "state": "done", "count": 2})
        self.assertEqual(code, 200, body)
        self.assertIn("· rozmowy 2 · Zapisz rozmowy", self.text("kampanie/druga.md"))
        self.assertNotIn("rozmowy 2", self.text("kampanie/zaproszenia.md"))

    def test_stan_bez_licznika_jak_dotad(self):
        t = self.t("Bez kontroli")
        self.assertEqual(self.post("/api/task/state", {"id": t["id"], "title": t["title"], "state": "done"}),
                         (200, {"ok": True, "error": ""}))


class Skutki(Runda5):
    def answer(self, n, **kw):
        return self.post("/api/question/answer", dict({"id": PID, "n": n}, **kw))

    def q(self, n):
        return self.data()["projects"][0]["questions"][n - 1]

    def test_effects_w_danych(self):
        q = self.q(1)
        self.assertEqual(len(q["effects"]), 4)
        self.assertTrue(q["effects"][0].startswith("kiedy: %s" % LATER))
        self.assertEqual(q["text"], "Czy przesunąć stronę na później?")
        self.assertEqual(self.q(2).get("effects") or [], [])

    def test_przyjecie_propozycji(self):
        code, body = self.answer(1, accept=True)
        self.assertEqual(code, 200, body)
        self.assertEqual((len(body["applied"]), len(body["failed"])), (3, 1))
        self.assertIn("Nie ma takiego zadania", json.dumps(body["failed"], ensure_ascii=False))
        self.assertEqual(body["task"], "")
        self.assertEqual(self.q(1)["answer"], "tak, strona po makiecie i teksty zamknięte")
        data = self.data()
        self.assertEqual(self.t("Zbuduj stronę", data)["date"], LATER)
        self.assertIn("Popraw teksty", self.t("Opublikuj stronę", data)["after"])
        self.assertEqual(self.t("Popraw teksty", data)["state"], "done")
        note = "z pytania 1, %s" % TODAY
        for title in ("Zbuduj stronę", "Opublikuj stronę", "Popraw teksty"):
            self.assertTrue(any(note in line for line in self.lines_after(title)[1:]), title)
        self.assertFalse([t for t in data["tasks"] if t["title"].startswith("Zastosuj odpowiedź")])
        # drugie przyjęcie: pytanie ma już odpowiedź
        self.assertEqual(self.answer(1, accept=True)[0], 409)

    def test_inna_odpowiedz_zaklada_zadanie_agenta(self):
        before = self.text("ZADANIA.md")
        code, body = self.answer(1, answer="Nie, zostaw jak jest, tylko teksty zamknij")
        self.assertEqual(code, 200, body)
        self.assertEqual((body["applied"], body["task"]), ([], "Zastosuj odpowiedź na pytanie 1"))
        self.assertIn(before.split("## Do rozplanowania")[0], self.text("ZADANIA.md"))   # zadania bez zmian
        t = self.t("Zastosuj odpowiedź na pytanie 1")
        self.assertEqual((t["executor"], t["date"], t["state"]), ("claude", TODAY, "todo"))
        self.assertEqual(t["detail"]["refs"], [{"path": "KARTA.md", "anchor": "Pytania do właściciela"}])
        self.assertEqual(t["group"], "Do rozplanowania")
        # zmiana odpowiedzi nie dubluje zadania
        self.assertEqual(self.answer(1, answer="Nie, jednak inaczej")[0], 200)
        titles = [x["title"] for x in self.data()["tasks"]]
        self.assertEqual(titles.count("Zastosuj odpowiedź na pytanie 1"), 1)
        # materiał wskazuje sekcję pytań w karcie
        status, _, text = self.request("GET", "/api/plik?project=%s&path=KARTA.md&anchor=Pytania%%20do%%20w%%C5%%82a"
                                              "%%C5%%9Bciciela" % PID)
        self.assertEqual(status, 200, text)

    def test_odpowiedz_rowna_propozycji(self):
        code, body = self.answer(1, answer="tak, strona po makiecie i  teksty zamknięte")
        self.assertEqual(code, 200, body)
        self.assertEqual(len(body["applied"]), 3)
        self.assertEqual(self.t("Zbuduj stronę")["date"], LATER)

    def test_odmowy_i_pytania_bez_skutkow(self):
        self.assertEqual(self.answer(2, accept=True)[0], 400)                  # bez propozycji
        self.assertEqual(self.answer(9, accept=True)[0], 400)
        self.assertEqual(self.answer(1, accept="tak")[0], 400)
        self.assertEqual(self.answer(2, answer="Tak"), (200, {"ok": True, "error": ""}))
        code, body = self.answer(3, accept=True)                                 # propozycja bez skutków
        self.assertEqual((code, body["applied"], body["failed"], body["task"]), (200, [], [], ""))
        self.assertEqual(self.q(3)["answer"], "niebieski")


class Prompt(Runda5):
    def test_prompt_skutki_i_gotowe_gdy(self):
        text = self.manager.task_prompt("claude", "Projekt", "ZADANIA.md", 5, "Zadanie", "")
        self.assertIn("`   skutek: <operacja>`", text)
        for op in ("po: <fragment poprzednika> → <fragment tytułu", "kiedy: RRRR-MM-DD →",
                   "stan: zrobione|wstrzymane →", "nowe: <wiersz zadania>"):
            self.assertIn(op, text)
        self.assertIn("Wiersza `gotowe gdy:` nie zmieniaj", text)
        self.assertIn("nie dopisuj „albo w zostało:”", text)


class Sekrety(unittest.TestCase):
    def test_secret_file(self):
        for path in (".env", ".env.local", "app/.env.production", "certs/serwer.pem", "klucz.KEY", "a\\b\\.env"):
            self.assertTrue(agents.secret_file(path), path)
        for path in ("env.md", "notatki/klucze.md", "pem.txt", "src/environment.py", "keys/README"):
            self.assertFalse(agents.secret_file(path), path)


@unittest.skipUnless(GIT, "brak polecenia git")
class ScalenieSekretow(Repo):
    def test_merge_odmawia_przy_sekretach(self):
        rec = self.run_done("Zadanie A", mode="sekret")
        paths = {c["path"] for c in rec["changes"]}
        self.assertTrue({".env.local", "certyfikat/serwer.pem", "notatki/analiza.md"} <= paths, paths)
        head = self.git("rev-parse", "HEAD")
        code, err, _ = self.manager.merge(rec["id"])
        self.assertEqual(code, 409)
        self.assertIn("pliki z sekretami", err)
        self.assertIn(".env.local", err)
        self.assertIn("certyfikat/serwer.pem", err)
        self.assertEqual(self.git("rev-parse", "HEAD"), head)                    # repozytorium bez zmian
        self.assertFalse(self.manager.get(rec["id"]).get("merged"))
        # po usunięciu sekretów z gałęzi scalenie przechodzi
        wt = os.path.join(self.tmp, "wt")
        self.git("worktree", "add", "-q", wt, rec["branch"])
        self.git("rm", "-q", ".env.local", "certyfikat/serwer.pem", cwd=wt)
        self.git("commit", "-q", "-m", "bez sekretów", cwd=wt)
        self.git("worktree", "remove", "--force", wt)
        code, err, extra = self.manager.merge(rec["id"])
        self.assertEqual(code, 200, err)
        self.assertTrue(extra["commit"])


if __name__ == "__main__":
    unittest.main()
