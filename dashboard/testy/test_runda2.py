"""Runda 2: kolejność zadań (po:), kroki, poprawka i następne w /api/task/detail, terminy pytań, mniej szumu
w raporcie PM i w danych, Automat (zadania bez gdzie:, rytm marketingu), prompt agenta, stan serwera, sesje."""
import datetime
import json
import os
import sys
import time
import unittest

from test_serwer import REMOTE, Serwer
from wspolne import Baza, agents, projekt, server

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "standard"))
import pm  # noqa: E402

DAY = datetime.date.today()


def day(n):
    return (DAY + datetime.timedelta(days=n)).isoformat()


def at(hour, n=0):
    return datetime.datetime.combine(DAY + datetime.timedelta(days=n), datetime.time(hour, 0))


ZADANIA = """# Zadania: Projekt testowy

## Etap: Pierwszy
termin: %(t5)s

- [ ] Przygotuj makietę | kto: claude | gdzie: mac | kiedy: %(t0)s
- [ ] Zbuduj stronę | kto: claude | gdzie: mac | kiedy: %(t0)s | po: makietę
- [ ] Zatwierdź teksty | kto: ty | kiedy: %(t2)s
- [ ] Opublikuj stronę | kto: claude | kiedy: %(t1)s | po: zatwierdź teksty, nie ma takiego
- [ ] Wyślij ofertę | kto: ty | kiedy: %(t3)s | wymaga: zgoda
- [ ] Sprawdź formularz | kto: claude | kiedy: %(t1)s
  cel: formularz wysyła wiadomość
  - [ ] pole e-mail
  - [x] pole treść
  notatka bez klucza

## Do rozplanowania
""" % {"t0": day(0), "t1": day(1), "t2": day(2), "t3": day(3), "t5": day(5)}

PYTANIA = """
## Pytania do właściciela
1. Który kolor logo?
   termin: %s
2. Czy wysyłamy newsletter do %s?
3. Bez terminu?
   Odpowiedź: tak
""" % (day(-1), day(4))


class Wspolne(Baza):
    def setUp(self):
        super().setUp()
        self.write("ZADANIA.md", ZADANIA)

    def write(self, rel, text, mode="w"):
        path = os.path.join(self.folder, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, mode, encoding="utf-8") as f:
            f.write(text)

    def text(self, rel="ZADANIA.md"):
        with open(os.path.join(self.folder, rel), encoding="utf-8") as f:
            return f.read()

    def get(self, title):
        return next(t for t in projekt.read_project(self.folder, "projekt-testowy")["tasks"] if t["title"] == title)

    def set_card_state(self, state):
        card = self.text("KARTA.md")
        self.write("KARTA.md", card.replace("- stan: aktywny", "- stan: " + state))


class Kolejnosc(Wspolne):
    def test_parser_i_poprzednicy(self):
        t = self.get("Zbuduj stronę")
        self.assertEqual(t["after"], ["makietę"])
        self.assertEqual([(w["title"], w["done"]) for w in t["waitingFor"]], [("Przygotuj makietę", False)])
        self.assertTrue(t["waitingFor"][0]["id"].endswith("|ZADANIA.md|6"))
        t = self.get("Opublikuj stronę")
        self.assertEqual(t["after"], ["zatwierdź teksty", "nie ma takiego"])          # bez wielkości liter
        self.assertEqual([(w["title"], w["done"], w["id"]) for w in t["waitingFor"]][1], ("nie ma takiego", False, ""))
        self.assertEqual(self.get("Przygotuj makietę")["waitingFor"], [])
        self.assertEqual(projekt.parse_task("- [ ] A | po: ,")["errors"], ["po: podaj fragment tytułu zadania"])
        self.assertEqual(projekt.parse_task("- [ ] A | po: x")["errors"], [])

    def test_zapis_zachowuje_po(self):
        t = self.get("Zbuduj stronę")
        self.assertTrue(projekt.update_task(self.folder, "ZADANIA.md", t["line"], t["title"], {"date": day(2)}))
        self.assertIn("- [ ] Zbuduj stronę | kto: claude | gdzie: mac | kiedy: %s | po: makietę" % day(2), self.text())
        self.assertTrue(projekt.update_task(self.folder, "ZADANIA.md", t["line"], t["title"],
                                            {"after": ["makietę", "Zatwierdź"]}))
        self.assertEqual(self.get("Zbuduj stronę")["after"], ["makietę", "Zatwierdź"])
        with self.assertRaises(ValueError):
            projekt.update_task(self.folder, "ZADANIA.md", t["line"], t["title"], {"after": "makietę"})

    def test_run_block_i_automat(self):
        self.assertEqual(self.run_task("Zbuduj stronę")[:2], (409, "Czeka na: Przygotuj makietę"))
        self.assertEqual(agents.run_block(self.task("Opublikuj stronę"), "registry", {}, {"claude": True}),
                         "Czeka na: Zatwierdź teksty, nie ma takiego")
        open(os.path.join(self.notes, day(0) + ".md"), "w").close()
        self.manager.set_automat(True)
        self.set_mode("ok")
        started = self.manager.tick(at(10))
        self.assertEqual([self.manager.get(r)["title"] for r in started], ["Przygotuj makietę"])
        self.wait(started[0])
        self.assertTrue(self.row("Przygotuj makietę").startswith("- [x]"))
        started = self.manager.tick(at(11))                     # poprzednik zrobiony: następne zadanie rusza
        self.assertEqual([self.manager.get(r)["title"] for r in started], ["Zbuduj stronę"])
        self.wait(started[0])


class Szczegoly(Wspolne):
    def test_krok_poprawka_nastepne(self):
        t = self.get("Sprawdź formularz")
        args = (self.folder, "ZADANIA.md", t["line"], t["title"])
        self.assertTrue(projekt.set_detail(*args, "krok", {"index": 0, "done": True}))
        self.assertTrue(projekt.set_detail(*args, "krok", {"index": 1, "done": False}))
        self.assertEqual([s["done"] for s in self.get("Sprawdź formularz")["detail"]["steps"]], [True, False])
        for bad in ({"index": 2, "done": True}, {"index": -1, "done": True}, {"index": 0, "done": "tak"}, "0",
                    {"index": True, "done": True}):
            with self.assertRaises(ValueError):
                projekt.set_detail(*args, "krok", bad)
        self.assertTrue(projekt.set_detail(*args, "poprawka", "Dodaj walidację adresu"))
        self.assertTrue(projekt.set_detail(*args, "następne", "Wyślij  test | kto: ty | kiedy: %s" % day(2)))
        d = self.get("Sprawdź formularz")["detail"]
        self.assertEqual((d["fix"], d["next"]), ("Dodaj walidację adresu", "Wyślij test | kto: ty | kiedy: %s" % day(2)))
        self.assertEqual(d["notes"], ["notatka bez klucza"])
        self.assertIn("  - [x] pole e-mail\n  - [ ] pole treść\n  notatka bez klucza\n  poprawka: Dodaj walidację adresu\n"
                      "  następne: Wyślij test | kto: ty | kiedy: %s\n" % day(2), self.text())
        self.assertEqual(len([x for x in projekt.read_project(self.folder)["tasks"] if x["title"].startswith("Wyślij test")]), 0)
        for bad in ("| kto: ty", "Tytuł | kto: nikt", "x" * 301):
            with self.assertRaises(ValueError):
                projekt.set_detail(*args, "następne", bad)
        self.assertTrue(projekt.set_detail(*args, "nastepne", ""))
        self.assertEqual(self.get("Sprawdź formularz")["detail"]["next"], "")

    def test_prompt_agenta(self):
        detail = dict(projekt.blank_detail(), doneWhen="w", fix="popraw nagłówek", next="X | kto: ty")
        p = self.manager.task_prompt("claude", "P", "ZADANIA.md", 4, "Tytuł", "", detail)
        for part in ("Poprawka od właściciela (wiersz poprawka:): popraw nagłówek", "wiersz `poprawka:`",
                     "`  następne: Tytuł | kto: … | kiedy: RRRR-MM-DD`", "agent/%s-krotka-nazwa" % day(0),
                     "bez push", "W wierszu `wynik:` podaj gałąź i skrót commita",
                     "Gdy warunek „gotowe gdy” nie jest spełniony, zakończ stanem `[!]` z polem `blokada: powód` "
                     "(bez `wymaga: odbiór`)", "`   termin: RRRR-MM-DD`"):
            self.assertIn(part, p)


class Pytania(Wspolne):
    def setUp(self):
        super().setUp()
        self.write("KARTA.md", PYTANIA, "a")

    def test_termin_pytania(self):
        qs = projekt.read_project(self.folder)["project"]["questions"]
        self.assertEqual([(q["n"], q["text"], q["date"], q["answer"]) for q in qs],
                         [(1, "Który kolor logo?", day(-1), ""), (2, "Czy wysyłamy newsletter do %s?" % day(4), day(4), ""),
                          (3, "Bez terminu?", "", "tak")])
        projekt.set_answer(self.folder, 1, "niebieski")
        self.assertIn("1. Który kolor logo?\n   termin: %s\n   Odpowiedź: niebieski\n" % day(-1), self.text("KARTA.md"))
        self.assertEqual(projekt.read_project(self.folder)["project"]["questions"][0]["date"], day(-1))

    def test_pytania_w_raporcie(self):
        f = pm.facts(DAY, self.runs)
        qs = [t for t in f["decisions"] if t["kind"] == "pytanie"]
        self.assertEqual([(t["title"], t["minutes"], t["date"]) for t in qs],
                         [("Który kolor logo?", 2, day(-1)), ("Czy wysyłamy newsletter do %s?" % day(4), 2, day(4))])
        self.assertEqual(f["top"][0]["title"], "Który kolor logo?")                   # po terminie najpierw
        self.assertEqual([t["title"] for t in f["questionsLate"]], ["Który kolor logo?"])
        text = pm.text(f)
        self.assertIn("◆ pytanie Projekt testowy · Który kolor logo? (wczoraj, 2 min)", text)
        self.assertIn("■ pytanie po terminie: Projekt testowy · Który kolor logo?", text)


class RaportPM(Wspolne):
    def facts(self):
        return pm.facts(DAY, self.runs)

    def test_zgoda_na_zadaniu_wlasciciela_i_liczniki(self):
        f = self.facts()
        titles = [t["title"] for t in f["decisions"]]
        self.assertNotIn("Wyślij ofertę", titles)                     # kto: ty + zgoda, termin za 3 dni: zwykłe zadanie
        self.assertNotIn("Zatwierdź teksty", titles)
        self.assertEqual(projekt.owner_needs(self.get("Wyślij ofertę")), [])
        c = f["counts"]
        self.assertEqual((c["you"], c["youToday"], c["youWeek"], c["youLater"]), (2, 0, 2, 0))
        self.write("ZADANIA.md", "- [ ] Zgoda dziś | kto: ty | kiedy: %s | wymaga: zgoda\n" % day(0), "a")
        f = self.facts()
        [t] = [t for t in f["decisions"] if t["title"] == "Zgoda dziś"]
        self.assertEqual(t["needsYou"], "")
        self.assertIn("◆ Twoje   Projekt testowy · Zgoda dziś", pm.text(f))
        self.assertEqual(f["counts"]["youToday"], 1)

    def test_wstrzymany_projekt_bez_spraw(self):
        self.write("KARTA.md", PYTANIA, "a")
        self.set_card_state("wstrzymany")
        f = self.facts()
        self.assertEqual((f["decisions"], f["top"], f["counts"]["you"], f["counts"]["youWeek"]), ([], [], 0, 0))
        self.assertEqual((f["questionsLate"], f["order"], f["waitingOnYou"]), ([], [], []))
        self.set_card_state("backlog")
        self.assertEqual(self.facts()["counts"]["you"], 0)

    def test_kolejnosc_i_czeka_na_ciebie(self):
        f = self.facts()
        self.assertEqual([(t["title"], t["after"]) for t in f["order"]], [("Opublikuj stronę", "Zatwierdź teksty")])
        self.assertEqual([(t["title"], t["after"]) for t in f["waitingOnYou"]], [("Opublikuj stronę", "Zatwierdź teksty")])
        text = pm.text(f)
        self.assertIn("◆ czeka na Ciebie: Projekt testowy · Opublikuj stronę · po Twoim zadaniu „Zatwierdź teksty”", text)
        self.assertIn("▲ kolejność: Projekt testowy · Opublikuj stronę (jutro) przed poprzednikiem „Zatwierdź teksty”"
                      " (za 2 dni)", text)
        self.write("ZADANIA.md", ZADANIA.replace("- [ ] Zatwierdź teksty | kto: ty | kiedy: %s" % day(2),
                                                 "- [ ] Zatwierdź teksty | kto: claude"))
        f = self.facts()
        self.assertEqual([t["afterDate"] for t in f["order"]], [""])                 # poprzednik bez daty
        self.assertEqual(f["waitingOnYou"], [])

    def test_zawieszone_i_odbior(self):
        self.write("ZADANIA.md", ZADANIA.replace("- [ ] Przygotuj makietę", "- [~] Przygotuj makietę")
                   .replace("- [ ] Sprawdź formularz | kto: claude", "- [~] Sprawdź formularz | kto: claude | wymaga: odbiór"))
        os.makedirs(self.runs, exist_ok=True)
        since = {"projekt-testowy|ZADANIA.md|Przygotuj makietę": {"s": "doing", "d": day(-4)},
                 "projekt-testowy|ZADANIA.md|Sprawdź formularz": {"s": "review", "d": day(-3)}}
        with open(os.path.join(self.runs, "stan.json"), "w", encoding="utf-8") as f:
            json.dump({"automat": False, "since": since}, f)
        f = self.facts()
        self.assertEqual([(t["title"], t["since"]) for t in f["stalled"]], [("Przygotuj makietę", day(-4))])
        self.assertEqual([t["title"] for t in f["reviewWaiting"]], ["Sprawdź formularz"])
        text = pm.text(f)
        self.assertIn("▲ zawieszone: Projekt testowy · Przygotuj makietę (w toku 4 dni, bez agenta)", text)
        self.assertIn("◆ odbiór czeka 3 dni: Projekt testowy · Sprawdź formularz", text)
        with open(os.path.join(self.runs, "20990101-000000-abcd.json"), "w", encoding="utf-8") as fh:
            json.dump({"id": "20990101-000000-abcd", "kind": "task", "state": "running", "project": "projekt-testowy",
                       "file": "ZADANIA.md", "title": "Przygotuj makietę"}, fh)
        self.assertEqual(self.facts()["stalled"], [])                                 # agent pracuje: nie zawieszone
        since["projekt-testowy|ZADANIA.md|Sprawdź formularz"]["d"] = day(-2)
        with open(os.path.join(self.runs, "stan.json"), "w", encoding="utf-8") as fh:
            json.dump({"since": since}, fh)
        self.assertEqual(self.facts()["reviewWaiting"], [])                           # 2 dni to jeszcze nie ryzyko


class Dane(Serwer):
    def setUp(self):
        super().setUp()
        with open(os.path.join(self.folder, "ZADANIA.md"), "w", encoding="utf-8") as f:
            f.write(ZADANIA)
        with open(os.path.join(self.folder, "KARTA.md"), "a", encoding="utf-8") as f:
            f.write(PYTANIA)

    def test_pola_w_danych(self):
        data = self.data()
        t = next(x for x in data["tasks"] if x["title"] == "Zbuduj stronę")
        self.assertEqual((t["after"], t["waitingFor"][0]["title"], t["waitingFor"][0]["done"]),
                         (["makietę"], "Przygotuj makietę", False))
        self.assertEqual(t["runBlock"], "Czeka na: Przygotuj makietę")
        self.assertTrue(all({"after", "waitingFor", "stateSince", "stalled", "reviewOverdue", "ownerNeeds"} <= set(x)
                            for x in data["tasks"]))
        self.assertEqual(next(x for x in data["tasks"] if x["title"] == "Wyślij ofertę")["ownerNeeds"], [])
        self.assertEqual([q["date"] for q in data["projects"][0]["questions"]], [day(-1), day(4), ""])
        # Zatwierdź teksty (2 dni), Wyślij ofertę (3 dni), pytanie po terminie (dziś), pytanie za 4 dni
        self.assertEqual((data["youToday"], data["youWeek"], data["youLater"]), (1, 3, 0))
        self.assertEqual((data["calendar"]["source"], data["calendar"]["events"]), ("none", []))
        self.assertIsNone(data["server"])

    def test_zawieszone_w_danych(self):
        t = self.task("Przygotuj makietę")
        projekt.set_state(self.folder, "ZADANIA.md", t["line"], t["title"], "doing")
        data = self.data()
        t = next(x for x in data["tasks"] if x["title"] == "Przygotuj makietę")
        self.assertEqual((t["stateSince"], t["stalled"]), (day(0), False))
        key = "projekt-testowy|ZADANIA.md|Przygotuj makietę"
        self.assertEqual(self.manager._state["since"][key], {"s": "doing", "d": day(0)})
        with open(os.path.join(self.runs, "stan.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["since"][key]["d"], day(0))              # stan zapisany dla pm.py
        self.manager._state["since"][key]["d"] = day(-5)
        t = next(x for x in self.data()["tasks"] if x["title"] == "Przygotuj makietę")
        self.assertEqual((t["stateSince"], t["stalled"], t["reviewOverdue"]), (day(-5), True, False))
        t = self.task("Przygotuj makietę")
        projekt.update_task(self.folder, "ZADANIA.md", t["line"], t["title"], {"needsYou": "odbiór"})
        t = next(x for x in self.data()["tasks"] if x["title"] == "Przygotuj makietę")
        self.assertEqual((t["stateSince"], t["stalled"]), (day(0), False))         # nowy stan: odbiór od dziś

    def test_api_szczegolow(self):
        t = self.task("Sprawdź formularz")
        post = lambda key, value, title=t["title"]: self.post("/api/task/detail", {"id": t["id"], "title": title,
                                                                                   "key": key, "value": value})
        self.assertEqual(post("krok", {"index": 1, "done": False}), (200, {"ok": True, "error": ""}))
        self.assertEqual(post("krok", {"index": 5, "done": True})[0], 400)
        self.assertEqual(post("krok", "1")[0], 400)
        self.assertEqual(post("poprawka", "Popraw nagłówek")[0], 200)
        self.assertEqual(post("następne", "Wyślij link | kto: ty | kiedy: %s" % day(2))[0], 200)
        self.assertEqual(post("nastepne", "| kto: ty")[0], 400)
        self.assertEqual(post("krok", {"index": 0, "done": True}, title="Inny")[0], 409)
        d = next(x for x in self.data()["tasks"] if x["title"] == "Sprawdź formularz")["detail"]
        self.assertEqual(([s["done"] for s in d["steps"]], d["fix"], d["next"]),
                         ([False, False], "Popraw nagłówek", "Wyślij link | kto: ty | kiedy: %s" % day(2)))

    def test_stan_serwera(self):
        with open(self.health_file, "w", encoding="utf-8") as f:
            f.write("panel=ok\nkopia=zle\nuseme=brak\nzly wiersz\nx=cos\n")
        self.assertEqual(self.data()["server"]["backupAt"], None)
        now = datetime.datetime.now().replace(microsecond=0)
        os.makedirs(os.path.dirname(self.backup_file))
        with open(self.backup_file, "w", encoding="utf-8") as f:
            json.dump({"at": (now - datetime.timedelta(hours=3)).isoformat(), "offsiteAt": (now - datetime.timedelta(hours=2)).isoformat()}, f)
        s = self.data()["server"]
        self.assertEqual(s["checks"], {"panel": "ok", "kopia": "zle", "useme": "brak"})
        self.assertEqual((s["backupAt"], s["backupOff"]), ((now - datetime.timedelta(hours=3)).isoformat(), True))
        self.assertRegex(s["at"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d$")
        with open(self.backup_file, "w", encoding="utf-8") as f:
            json.dump({"at": (now - datetime.timedelta(hours=30)).isoformat(), "offsiteAt": None}, f)
        self.assertFalse(self.data()["server"]["backupOff"])
        with open(self.backup_file, "w", encoding="utf-8") as f:
            json.dump({"at": (now - datetime.timedelta(hours=30)).isoformat() + "+00:00", "offsite": True}, f)
        self.assertFalse(self.data()["server"]["backupOff"])                         # poza serwerem 30 h temu
        os.remove(self.health_file)
        s = self.data()["server"]
        self.assertEqual(s["checks"], {})
        os.remove(self.backup_file)
        self.assertIsNone(self.data()["server"])

    def test_wyloguj_wszedzie_i_wygasanie(self):
        server.TOKEN = "haslo-do-testow"
        _, headers, _ = self.login("haslo-do-testow")
        cookie = headers["Set-Cookie"].split(";")[0]
        self.assertIn("Max-Age=2592000", headers["Set-Cookie"])
        session = dict(REMOTE, Cookie=cookie)
        self.assertEqual(self.request("GET", "/api/data", headers=session)[0], 200)
        self.assertEqual(self.post("/api/session/logout-all", {}, headers=session), (200, {"ok": True, "error": ""}))
        self.assertEqual(self.request("GET", "/api/data", headers=session)[0], 401)
        self.assertEqual(self.new_manager()._state["sessionKey"], self.manager._state["sessionKey"])  # klucz w stan.json
        _, headers, _ = self.login("haslo-do-testow")
        session = dict(REMOTE, Cookie=headers["Set-Cookie"].split(";")[0])
        self.assertEqual(self.request("GET", "/api/data", headers=session)[0], 200)
        old = int(time.time()) - 31 * 86400
        self.assertFalse(server.session_ok(server.session_value(old)))
        self.assertTrue(server.session_ok(server.session_value(int(time.time()) - 29 * 86400)))
        expired = dict(REMOTE, Cookie="panel_sesja=" + server.session_value(old))
        self.assertEqual(self.request("GET", "/api/data", headers=expired)[0], 401)
        for bad in ("", "abc", "123.", ".abc", "1" * 20 + ".x"):
            self.assertFalse(server.session_ok(bad), bad)


class KalendarzPrzykladowy(Serwer):
    registered = False

    def test_przyklady_tylko_przy_projektach_przykladowych(self):
        data = self.data()
        self.assertEqual(data["projectsSource"], "sample")
        self.assertEqual(data["calendar"]["source"], "sample")
        self.assertTrue(data["calendar"]["events"])
        self.assertTrue(all(t["stateSince"] == "" and t["stalled"] is False for t in data["tasks"]))


class Automat(Wspolne):
    def setUp(self):
        super().setUp()
        open(os.path.join(self.notes, day(0) + ".md"), "w").close()
        self.write("ZADANIA.md", "- [ ] Bez gdzie wczoraj | kto: claude | kiedy: %s\n"
                                 "- [ ] Bez gdzie jutro | kto: claude | kiedy: %s\n" % (day(-1), day(1)), "a")

    def started(self, m, hour=10):
        m.set_automat(True)
        ids = m.tick(at(hour))
        for r in ids:
            self.wait(r, manager=m)
        return [m.get(r)["title"] for r in ids]

    def test_bez_gdzie_na_serwerze(self):
        m = self.new_manager(PANEL_MACHINE="chmura", PANEL_AGENTS_MAX="3")
        self.assertTrue(m.default_node)
        self.assertEqual(self.started(m), ["Bez gdzie wczoraj"])            # przeszła data też startuje, gdzie: mac nie
        self.assertIn("| gdzie: chmura |", self.row("Bez gdzie wczoraj"))

    def test_mac_nie_bierze_zadan_bez_gdzie(self):
        self.assertFalse(self.manager.default_node)
        self.assertEqual(self.started(self.manager, 10), ["Przygotuj makietę"])
        m = self.new_manager(PANEL_DEFAULT_NODE="1")
        self.assertTrue(m.default_node)


RYTM = """# Kampania: Stały rytm

- stan: w toku
- kanały: facebook

## Harmonogram

- [ ] Post jutro | kanał: facebook | kiedy: %(t1)s
- [ ] Post z folderem | kanał: facebook | kiedy: %(t2)s
- [ ] Post za tydzień | kanał: facebook | kiedy: %(t7)s
- [x] Post stary | kanał: facebook | kiedy: %(m3)s
- [x] Post stary z wynikiem | kanał: facebook | kiedy: %(m3)s
  wynik: 120 wyświetleń
- [x] Post przedwczoraj | kanał: facebook | kiedy: %(m2)s
""" % {"t1": day(1), "t2": day(2), "t7": day(7), "m3": day(-3), "m2": day(-2)}


class RytmMarketingu(Wspolne):
    def setUp(self):
        super().setUp()
        self.write("kampanie/staly-rytm.md", RYTM)
        os.makedirs(os.path.join(self.folder, "posty", day(2) + "-gotowy"))
        self.m = self.new_manager(PANEL_MACHINE="chmura")

    def plan(self):
        data, index = self.m.load_projects()
        return self.m._plan_rhythm(data, index, DAY)

    def titles(self):
        return [t for t in self.m.load_projects()[0]["tasks"]
                if t["title"].startswith((agents.POST_TASK, agents.RESULT_TASK))]

    def test_posty_i_wyniki(self):
        self.assertTrue(self.plan())
        tasks = {t["title"]: t for t in self.titles()}
        self.assertEqual(sorted(tasks), ["Przygotować post na %s: Post jutro" % day(1), "Wpisz wynik publikacji Post stary"])
        post = tasks["Przygotować post na %s: Post jutro" % day(1)]
        self.assertEqual((post["executor"], post["machine"], post["date"]), ("claude", "cloud", day(0)))
        self.assertEqual(post["detail"]["refs"], [{"path": "kampanie/staly-rytm.md", "anchor": ""}])
        res = tasks["Wpisz wynik publikacji Post stary"]
        self.assertEqual((res["executor"], res["date"], res["minutes"]), ("ty", day(0), 3))
        self.assertFalse(self.plan())                                          # nic drugi raz
        row = self.row("Wpisz wynik publikacji Post stary")                   # właściciel usuwa zadanie: nie wraca
        self.write("ZADANIA.md", self.text().replace(row + "\n", ""))
        self.assertFalse(self.plan())
        self.assertNotIn("Wpisz wynik publikacji Post stary", [x["title"] for x in self.titles()])
        self.assertIn("projekt-testowy|%s|Post stary" % day(-3), self.new_manager()._state["rytmDone"])

    def test_wstrzymany_projekt_bez_rytmu(self):
        self.set_card_state("wstrzymany")
        self.assertFalse(self.plan())


class Podglad(unittest.TestCase):
    def test_podglad_ma_nowe_pola(self):
        preview = server.preview_data()
        self.assertTrue(all({"after", "waitingFor", "stateSince", "stalled", "reviewOverdue"} <= set(t)
                            for t in preview["tasks"]))
        self.assertTrue(any(t["after"] for t in preview["tasks"]))                  # przykład pola po:
        self.assertTrue(any(q["date"] for p in preview["projects"] for q in p["questions"]))


if __name__ == "__main__":
    unittest.main()
