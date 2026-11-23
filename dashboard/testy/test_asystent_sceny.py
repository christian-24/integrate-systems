"""Asystent w formie scen, serwer: daty stanu zadań (doneAt, blockedSince) i opcje pytań (opcja:)."""
import datetime
import json
import os
import unittest

from test_serwer import Serwer
from wspolne import server

TODAY = datetime.date.today()
KEY = "p|ZADANIA.md|%s"


def day(n):
    return (TODAY + datetime.timedelta(days=n)).isoformat()


def task(title, state="todo", blocked=""):
    return {"project": "p", "file": "ZADANIA.md", "title": title, "state": state, "blocked": blocked}


class DatyStanu(Serwer):
    def marks(self, tasks, today=TODAY, manager=None):
        return (manager or self.manager).track_marks(tasks, today)

    def ended_run(self, title, n):
        rid = "r-" + title
        self.manager._runs[rid] = {"id": rid, "kind": "task", "project": "p", "file": "ZADANIA.md", "title": title,
                                   "state": "done", "endedAt": day(n) + "T10:00:00"}

    def test_przejscia_stanow(self):
        self.assertEqual(self.marks([task("A")]), {})                       # otwarte: bez daty
        self.assertEqual(self.marks([task("A", "done")]), {KEY % "A": ("done", day(0))})
        self.assertEqual(self.manager._state["marks"][KEY % "A"], {"s": "done", "d": day(0)})
        # dzień później data zostaje
        self.assertEqual(self.marks([task("A", "done")], TODAY + datetime.timedelta(days=1))[KEY % "A"],
                         ("done", day(0)))
        # zablokowane: [!] albo samo pole blokada:
        self.assertEqual(self.marks([task("A", "todo", "czeka na dane")])[KEY % "A"], ("blocked", day(0)))
        self.assertEqual(self.marks([task("B")]), {})
        self.assertEqual(self.marks([task("B", "blocked")])[KEY % "B"], ("blocked", day(0)))
        self.assertEqual(self.marks([task("B")]), {})
        self.assertEqual(self.manager._state["marks"], {})                  # ponowne otwarcie usuwa wpis
        with open(os.path.join(self.runs, "stan.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["marks"], {})

    def test_zastane_zadanie(self):
        self.ended_run("Z uruchomieniem", -4)
        got = self.marks([task("Bez uruchomienia", "done"), task("Z uruchomieniem", "done"),
                          task("Zablokowane", "blocked")])
        self.assertEqual(got, {KEY % "Bez uruchomienia": ("done", ""), KEY % "Z uruchomieniem": ("done", day(-4)),
                               KEY % "Zablokowane": ("blocked", "")})
        self.assertEqual(set(self.manager._state["marks"]), {KEY % "Z uruchomieniem"})   # nieznanych dat nie zapisuje
        self.assertEqual(self.marks([task("Bez uruchomienia", "done")])[KEY % "Bez uruchomienia"], ("done", ""))

    def test_po_restarcie(self):
        self.marks([task("A"), task("B")])
        self.marks([task("A", "blocked"), task("B", "done")])
        fresh = self.new_manager()
        self.assertEqual(fresh._state["marks"][KEY % "A"], {"s": "blocked", "d": day(0)})
        # zmiana zapisana w stan.json widziana po restarcie: od dziś
        got = self.marks([task("A", "done"), task("B", "done")], TODAY + datetime.timedelta(days=2), fresh)
        self.assertEqual(got, {KEY % "A": ("done", day(2)), KEY % "B": ("done", day(0))})

    def test_czyszczenie_po_90_dniach(self):
        self.manager._state["marks"] = {KEY % "Stare": {"s": "done", "d": day(-91)},
                                        KEY % "Granica": {"s": "done", "d": day(-90)},
                                        KEY % "Blokada": {"s": "blocked", "d": day(-200)}}
        got = self.marks([task("Stare", "done"), task("Granica", "done"), task("Blokada", "blocked")])
        self.assertEqual(got[KEY % "Stare"], ("done", day(-91)))            # w danych zostaje
        self.assertEqual(set(self.manager._state["marks"]), {KEY % "Granica", KEY % "Blokada"})
        self.marks([])                                                        # zadanie zniknęło z pliku
        self.assertEqual(self.manager._state["marks"], {})

    def test_pola_w_danych(self):
        data = self.data()
        self.assertTrue(all({"stateSince", "doneAt", "blockedSince"} <= set(t) for t in data["tasks"]))
        t = data["tasks"][0]
        server.projekt.set_state(self.folder, "ZADANIA.md", t["line"], t["title"], "done")
        t = next(x for x in self.data()["tasks"] if x["title"] == t["title"])
        self.assertEqual((t["doneAt"], t["blockedSince"]), (day(0), ""))

    def test_podglad(self):
        preview = server.preview_data()
        self.assertTrue(all(t["doneAt"] == "" and t["blockedSince"] == "" for t in preview["tasks"]))
        qs = [q for p in preview["projects"] for q in p["questions"]]
        self.assertTrue(all(isinstance(q["options"], list) for q in qs))
        self.assertTrue(any(len(q["options"]) >= 2 for q in qs))


PYTANIA = """
## Pytania do właściciela
1. Jaki kolor tła?
   opcja: granatowy
   opcja:  biały
   opcja: szary
   propozycja: granatowy
2. Czy wysłać ofertę?
   termin: +2
3. Jedna opcja?
   opcja: tak
"""


class OpcjePytan(Serwer):
    def setUp(self):
        super().setUp()
        with open(os.path.join(self.folder, "KARTA.md"), "a", encoding="utf-8") as f:
            f.write(PYTANIA)

    def test_parsowanie_i_odpowiedz(self):
        p = self.data()["projects"][0]
        qs = p["questions"]
        self.assertEqual([q["options"] for q in qs], [["granatowy", "biały", "szary"], [], ["tak"]])
        self.assertEqual((qs[0]["text"], qs[0]["proposal"]), ("Jaki kolor tła?", "granatowy"))
        gaps = [g for d in p["docs"] for g in d["gaps"]]
        self.assertTrue(any("jedną opcją" in g and "pytanie 3" in g for g in gaps), gaps)
        self.assertEqual(self.post("/api/question/answer", {"id": "projekt-testowy", "n": 1, "answer": "biały"})[0],
                         200)
        q = self.data()["projects"][0]["questions"][0]
        self.assertEqual((q["answer"], q["options"]), ("biały", ["granatowy", "biały", "szary"]))

    def test_bez_opcji(self):
        q = server.projekt.parse_questions(server.projekt.parse_doc("# K\n\n## Pytania do właściciela\n1. Pyt?\n")[2])
        self.assertEqual(q[0]["options"], [])

    def test_prompt(self):
        p = self.manager.task_prompt("claude", "P", "ZADANIA.md", 4, "Tytuł", "", server.projekt.blank_detail())
        self.assertIn("2–3 wcięte wiersze `   opcja: …`", p)
        self.assertIn("`propozycja:` wskazuje wtedy jedną z opcji", p)


if __name__ == "__main__":
    unittest.main()
