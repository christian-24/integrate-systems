"""Runda 5, format i raport PM: pola sprawdza:, licznik:, kampania:, skutek: pod pytaniami, liczniki kampanii
(„Wyniki i wnioski”), unlocks/unlockCount, nowe braki, „do zamknięcia”, grupowanie „czeka na Ciebie”, kolejność Dziś.

Testy pracują wyłącznie w katalogu tymczasowym (rejestr, zbieracz, uruchomienia, stan serwera).
"""
import contextlib
import datetime
import io
import os
import shutil
import sys
import tempfile
import unittest

TESTY = os.path.dirname(os.path.abspath(__file__))
STANDARD = os.path.join(os.path.dirname(os.path.dirname(TESTY)), "standard")
sys.path.insert(0, STANDARD)
import projekt  # noqa: E402
import pm  # noqa: E402

DAY = datetime.date.today()
ENV_KEYS = ("STAN_DIR", "LOKALNE_DIR", "PANEL_RUNS_DIR", "PANEL_DZIEN_MIN", "PANEL_ZDROWIE_STAN")


def day(n):
    return (DAY + datetime.timedelta(days=n)).isoformat()


def quiet(fn, *args, **kw):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*args, **kw)


CAMPAIGN = """# Kampania: Partia 1

- stan: %(state)s
- cel: konta
- miernik: %(metric)s
- cel liczbowy: 40
- wynik: %(result)s
- kanały: LinkedIn
- start: %(start)s
- koniec: %(end)s

## Grupa docelowa
firmy

## Przekaz
krótko

## Harmonogram
- [ ] Post o ofercie | kanał: LinkedIn | kiedy: %(start)s | kto: ty | czas: 15
%(results)s"""

PLACEHOLDER_RESULTS = "\n## Wyniki i wnioski\n_Do uzupełnienia po zakończeniu: wynik wobec celu._\n"


class Baza(unittest.TestCase):
    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp(prefix="runda5-"))
        self._registry = projekt.REGISTRY
        projekt.REGISTRY = os.path.join(self.tmp, "projekty.json")
        self._environ = {k: os.environ.get(k) for k in ENV_KEYS}
        self.runs = os.path.join(self.tmp, "uruchomienia")
        self.health = os.path.join(self.tmp, "zdrowie-stan")
        os.environ.update({"STAN_DIR": os.path.join(self.tmp, "stan"), "LOKALNE_DIR": os.path.join(self.tmp, "lok"),
                           "PANEL_RUNS_DIR": self.runs, "PANEL_ZDROWIE_STAN": self.health})
        os.environ.pop("PANEL_DZIEN_MIN", None)
        self.folder = self.new_project("alfa", "Alfa")

    def tearDown(self):
        projekt.REGISTRY = self._registry
        for k, v in self._environ.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.tmp, ignore_errors=True)

    def new_project(self, name, title, register=True):
        folder = os.path.join(self.tmp, name)
        quiet(projekt.cmd_nowy, folder, title, register=register)
        return folder

    def write(self, rel, text, folder=None):
        path = os.path.join(folder or self.folder, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    def text(self, rel, folder=None):
        with open(os.path.join(folder or self.folder, rel), encoding="utf-8") as f:
            return f.read()

    def card(self, extra_head="", questions="", folder=None):
        name = os.path.basename(folder or self.folder).capitalize()
        self.write("KARTA.md", "# Karta projektu: " + name + "\n\n- stan: aktywny\n%s\n## Cel\nCel.\n\n## Zakres\nZ.\n\n"
                   "## Poza zakresem\nP.\n\n## Definicja ukończenia\nD.\n\n## Zasady pracy agentów\nZ.\n%s"
                   % (extra_head, questions), folder)

    def zadania(self, rows, folder=None, stage_date=None):
        self.write("ZADANIA.md", "# Zadania: X\n\n## Etap: A\ntermin: %s\n\n%s\n\n## Do rozplanowania\n"
                   % (stage_date or day(30), rows), folder)

    def campaign(self, name="partia-1", state="w toku", metric="konta", result="", results=PLACEHOLDER_RESULTS,
                 folder=None):
        self.write("kampanie/%s.md" % name, CAMPAIGN % {"state": state, "metric": metric, "result": result,
                                                        "start": day(-2), "end": day(20), "results": results}, folder)

    def read(self, folder=None):
        return projekt.read_project(folder or self.folder)

    def tasks(self, folder=None):
        return [t for t in self.read(folder)["tasks"] if t["kind"] == "zadanie"]

    def gaps(self, key, folder=None):
        return next(d for d in self.read(folder)["project"]["book"] if d["key"] == key)["gaps"]


class Pola(Baza):
    def test_sprawdza_licznik_kampania(self):
        self.zadania("- [ ] Skonfiguruj kopię | kto: claude | kiedy: %s | sprawdza: kopia-poza\n"
                     "- [ ] Opisz wdrożenie | kto: claude | kiedy: %s | sprawdza: plik docs/WDROZENIE.md\n"
                     "- [ ] Wyślij zaproszenia | kto: ty | kiedy: %s | czas: 20 | licznik: Przyjete | kampania: partia-1\n"
                     "- [ ] Zrób coś | kto: claude | kiedy: %s\n" % (day(1), day(1), day(1), day(1)))
        a, b, c, d = self.tasks()
        self.assertEqual(a["check"], {"key": "kopia-poza", "ok": None, "at": ""})
        self.assertEqual(b["check"]["key"], "plik docs/WDROZENIE.md")
        self.assertEqual((c["counter"], c["campaignFile"]), ("przyjęte", "kampanie/partia-1.md"))
        self.assertEqual((d["check"], d["counter"], d["campaignFile"]), (None, "", ""))
        self.assertEqual(self.read()["project"]["book"][1]["key"], "zadania")
        self.assertFalse([g for g in self.gaps("zadania") if g.startswith("wiersz")])

    def test_zle_wartosci_pol(self):
        self.zadania("- [ ] Zrób | kto: claude | kiedy: %s | licznik: polubienia | kampania: ../x | sprawdza:\n" % day(1))
        gaps = self.gaps("zadania")
        self.assertTrue(any("licznik: polubienia" in g for g in gaps), gaps)
        self.assertTrue(any("kampania: ../x" in g for g in gaps), gaps)
        self.assertTrue(any("sprawdza: podaj klucz" in g for g in gaps), gaps)

    def test_nieznany_klucz_sprawdza(self):
        self.zadania("- [ ] Zrób kopię | kto: claude | kiedy: %s | sprawdza: backup\n" % day(1))
        self.assertTrue(any(g.startswith("„sprawdza:” z nieznanym kluczem") and "Zrób kopię (backup)" in g
                            for g in self.gaps("zadania")))

    def test_update_task_zachowuje_nowe_pola(self):
        self.zadania("- [ ] Wyślij zaproszenia | kto: ty | czas: 20 | licznik: zaproszenia | sprawdza: plik a.md\n")
        t = self.tasks()[0]
        self.assertTrue(projekt.update_task(self.folder, "ZADANIA.md", t["line"], t["title"], {"date": day(2)}))
        t = self.tasks()[0]
        self.assertEqual((t["date"], t["counter"], t["check"]["key"]), (day(2), "zaproszenia", "plik a.md"))

    def test_slabe_gotowe_gdy(self):
        self.zadania("- [ ] Wyślij zaproszenia | kto: claude | kiedy: %s\n"
                     "  gotowe gdy: w tabeli z punktu 8 planu wpisane „Zaproszenia wysłane: 8”\n"
                     "- [ ] Przygotuj post | kto: claude | kiedy: %s\n"
                     "  gotowe gdy: post.md gotowy albo w zostało: powód\n"
                     "- [ ] Napisz testy | kto: claude | kiedy: %s\n"
                     "  gotowe gdy: testy przechodzą i wynik wpisany do tabeli\n" % (day(1), day(1), day(1)))
        [gap] = [g for g in self.gaps("zadania") if g.startswith("„gotowe gdy” z")]
        self.assertIn(": 2 (", gap)
        self.assertNotIn("Napisz testy", gap)


class Kontrole(Baza):
    def test_check_task_serwer(self):
        t = {"check": {"key": "kopia", "ok": None, "at": ""}}
        self.assertEqual(projekt.check_task(t, {"kopia": "ok"}, self.folder), {"key": "kopia", "ok": True, "at": ""})
        self.assertFalse(projekt.check_task(t, {"kopia": "zle"}, self.folder)["ok"])
        self.assertIsNone(projekt.check_task(t, {}, self.folder)["ok"])
        self.assertIsNone(projekt.check_task(t, None, self.folder)["ok"])
        block = {"checks": {"kopia": "ok"}, "at": "2026-11-19T09:10:00"}
        self.assertEqual(projekt.check_task(t, block, self.folder)["at"], "2026-11-19T09:10:00")
        self.assertIsNone(projekt.check_task({"check": {"key": "backup"}}, {"backup": "ok"}, self.folder)["ok"])
        self.assertIsNone(projekt.check_task({"check": None}, {"kopia": "ok"}, self.folder))

    def test_check_task_plik(self):
        t = {"check": {"key": "plik docs/WDROZENIE.md"}}
        self.assertFalse(projekt.check_task(t, None, self.folder)["ok"])
        self.write("docs/WDROZENIE.md", "# W\n")
        c = projekt.check_task(t, None, self.folder)
        self.assertTrue(c["ok"])
        self.assertRegex(c["at"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d$")
        self.write("poza.md", "x", self.tmp)
        self.assertFalse(projekt.check_task({"check": {"key": "plik ../poza.md"}}, None, self.folder)["ok"])
        self.assertIsNone(projekt.check_task(t, None, None)["ok"])

    def test_check_task_plik_w_folderze_karty(self):
        cards = os.path.join(self.tmp, "karty")
        os.makedirs(cards)
        shutil.move(os.path.join(self.folder, "KARTA.md"), os.path.join(cards, "KARTA.md"))
        os.symlink(os.path.join(cards, "KARTA.md"), os.path.join(self.folder, "KARTA.md"))
        self.write("notatka.md", "x", cards)
        self.assertTrue(projekt.check_task({"check": {"key": "plik notatka.md"}}, None, self.folder)["ok"])

    def test_read_health(self):
        self.assertIsNone(projekt.read_health())
        self.write("zdrowie-stan", "kopia=ok\ndysk=zle\nśmieci\npanel=dziwne\n", self.tmp)
        h = projekt.read_health()
        self.assertEqual(h["checks"], {"kopia": "ok", "dysk": "zle"})
        self.assertTrue(h["at"])

    def test_pm_do_zamkniecia(self):
        self.zadania("- [ ] Skonfiguruj kopię | kto: ty | kiedy: %s | czas: 10 | sprawdza: kopia\n"
                     "- [ ] Opisz wdrożenie | kto: ty | kiedy: %s | czas: 10 | sprawdza: plik docs/W.md\n"
                     "- [ ] Sprawdź dysk | kto: ty | kiedy: %s | czas: 10 | sprawdza: dysk\n" % (day(0), day(0), day(0)))
        f = pm.facts(DAY, self.runs)                     # bez pliku stanu serwera: kontrole serwera pominięte
        self.assertEqual(f["toClose"], [])
        self.assertEqual(len(f["today_tasks"]), 3)
        self.write("zdrowie-stan", "kopia=ok\ndysk=zle\n", self.tmp)
        self.write("docs/W.md", "x")
        f = pm.facts(DAY, self.runs)
        self.assertEqual([t["title"] for t in f["toClose"]], ["Skonfiguruj kopię", "Opisz wdrożenie"])
        self.assertEqual(f["toClose"][0]["check"]["key"], "kopia")
        self.assertEqual(f["counts"]["toClose"], 2)
        self.assertEqual([t["title"] for t in f["today_tasks"]], ["Sprawdź dysk"])
        text = pm.text(f)
        self.assertIn("✓ wygląda na zrobione: Alfa · Skonfiguruj kopię (kontrola kopia, ", text)
        self.assertIn("· Do zamknięcia 2", text)


class Liczniki(Baza):
    def test_dopisanie_do_kampanii_w_toku(self):
        self.campaign("a-plan", state="plan")
        self.campaign("b-partia")
        self.assertEqual(projekt.active_campaign(self.folder), "kampanie/b-partia.md")
        self.assertTrue(projekt.append_campaign_count(self.folder, None, "konta", 3, "Wyślij | zaproszenia", day(0)))
        text = self.text("kampanie/b-partia.md")
        self.assertIn("## Wyniki i wnioski\n- %s · konta 3 · Wyślij / zaproszenia\n" % day(0), text)
        self.assertNotIn("_Do uzupełnienia", text)
        projekt.append_campaign_count(self.folder, "b-partia", "Przyjete", 2, "Sprawdź przyjęte", DAY)
        projekt.append_campaign_count(self.folder, "kampanie/b-partia.md", "konta", 4, "Zadzwoń", day(1))
        c = next(c for c in self.read()["campaigns"] if c["file"] == "kampanie/b-partia.md")
        self.assertEqual(c["counters"], {"konta": 7, "przyjęte": 2})
        self.assertEqual((c["counterMetric"], c["result"], c["resultManual"]), ("konta", 7, None))
        rows = [l for l in self.text("kampanie/b-partia.md").split("\n") if l.startswith("- %s" % day(0)[:4])]
        self.assertEqual([r.split(" · ")[1] for r in rows], ["konta 3", "przyjęte 2", "konta 4"])

    def test_wynik_wiekszy_z_recznego_i_licznika(self):
        self.campaign(result="10", results="\n## Wyniki i wnioski\n- %s · konta 4 · A\nWniosek: działa.\n" % day(0))
        c = self.read()["campaigns"][0]
        self.assertEqual((c["result"], c["resultManual"], c["counters"]), (10, 10, {"konta": 4}))
        self.campaign(result="2", results="\n## Wyniki i wnioski\n- %s · konta 4 · A\n" % day(0))
        self.assertEqual(self.read()["campaigns"][0]["result"], 4)
        self.campaign(metric="liczba kont", result="2", results="\n## Wyniki i wnioski\n- %s · konta 4 · A\n" % day(0))
        c = self.read()["campaigns"][0]
        self.assertEqual((c["result"], c["counterMetric"]), (2, ""))

    def test_sekcja_zakladana_gdy_brak(self):
        self.campaign(results="")
        projekt.append_campaign_count(self.folder, "partia-1", "rozmowy", 1, "Zadzwoń", day(0))
        text = self.text("kampanie/partia-1.md")
        self.assertTrue(text.rstrip("\n").endswith("## Wyniki i wnioski\n- %s · rozmowy 1 · Zadzwoń" % day(0)), text)
        self.assertEqual(self.read()["campaigns"][0]["counters"], {"rozmowy": 1})

    def test_bledy(self):
        with self.assertRaises(ValueError):
            projekt.append_campaign_count(self.folder, None, "konta", 1, "X", day(0))      # brak kampanii w toku
        self.campaign()
        for args in (("polubienia", 1), ("konta", -1), ("konta", True), ("konta", "3")):
            with self.assertRaises(ValueError):
                projekt.append_campaign_count(self.folder, None, args[0], args[1], "X", day(0))
        with self.assertRaises(ValueError):
            projekt.append_campaign_count(self.folder, "../x", "konta", 1, "X", day(0))


QUESTIONS = """
## Pytania do właściciela
1. Czy wstrzymać post 2 do potwierdzenia DPA?
   propozycja: wstrzymać post 2 do potwierdzenia DPA
   skutek: po: potwierdź DPA → opublikuj post 2
   skutek: kiedy: %(d)s -> opublikuj post 2
2. Czy zamknąć stary wątek?
   propozycja: zamknąć zadanie z wątkiem
"""

ZADANIA = """- [ ] Potwierdź DPA | kto: ty | kiedy: %(d0)s | czas: 15
- [ ] Opublikuj post 2 | kto: ty | kiedy: %(d1)s | czas: 15
  materiał: posty/2.md
- [ ] Opublikuj post 3 | kto: ty | kiedy: %(d2)s | czas: 15
- [x] Napisz post 1 | kto: claude | kiedy: %(d0)s
"""


class Skutki(Baza):
    def setUp(self):
        super().setUp()
        self.card(questions=QUESTIONS % {"d": day(3)})
        self.zadania(ZADANIA % {"d0": day(0), "d1": day(1), "d2": day(2)})

    def task(self, title):
        return next(t for t in self.tasks() if t["title"] == title)

    def test_effects_w_danych_i_braki_karty(self):
        q1, q2 = self.read()["project"]["questions"]
        self.assertEqual(q1["effects"], ["po: potwierdź DPA → opublikuj post 2", "kiedy: %s -> opublikuj post 2" % day(3)])
        self.assertEqual(q1["proposal"], "wstrzymać post 2 do potwierdzenia DPA")
        self.assertEqual(q2["effects"], [])
        gaps = self.gaps("karta")
        self.assertIn("propozycja zmienia zadania, a nie ma „skutek:”: 1 („pytanie 2”)", gaps)
        self.assertFalse([g for g in gaps if g.startswith("zły wiersz")])

    def test_zly_skutek(self):
        self.card(questions="\n## Pytania do właściciela\n1. Co?\n   propozycja: nic\n   skutek: usuń: X\n"
                            "   skutek: kiedy: jutro → X\n   skutek: stan: gotowe → X\n   skutek: po: X\n")
        [gap] = [g for g in self.gaps("karta") if g.startswith("zły wiersz")]
        self.assertIn(": 4 (", gap)

    def test_apply_effects(self):
        effects = self.read()["project"]["questions"][0]["effects"]
        applied, failed = projekt.apply_effects(self.folder, effects, 1, day(0))
        self.assertEqual(failed, [])
        self.assertEqual(len(applied), 2)
        self.assertIn("(zadanie „Opublikuj post 2”)", applied[0])
        t = self.task("Opublikuj post 2")
        self.assertEqual((t["after"], t["date"]), (["potwierdź DPA"], day(3)))
        self.assertEqual(t["detail"]["notes"], ["z pytania 1, %s" % day(0)])          # jedna notatka mimo 2 skutków
        self.assertEqual(t["detail"]["refs"], [{"path": "posty/2.md", "anchor": ""}])
        self.assertEqual(t["waitingFor"][0]["title"], "Potwierdź DPA")
        again, failed = projekt.apply_effects(self.folder, effects, 1, day(0))      # powtórzenie niczego nie dubluje
        self.assertEqual((len(again), failed), (2, []))
        self.assertEqual(self.text("ZADANIA.md").count("z pytania 1"), 1)
        self.assertEqual(self.task("Opublikuj post 2")["after"], ["potwierdź DPA"])

    def test_stan_i_nowe(self):
        applied, failed = projekt.apply_effects(self.folder, [
            "stan: wstrzymane → post 3", "stan: zrobione → potwierdź dpa",
            "nowe: Wyślij przypomnienie | kto: ty | kiedy: %s | czas: 5" % day(4)], 2, DAY)
        self.assertEqual((len(applied), failed), (3, []))
        t = self.task("Opublikuj post 3")
        self.assertEqual((t["state"], t["blocked"]), ("blocked", "wstrzymane: z pytania 2, %s" % day(0)))
        self.assertEqual(self.task("Potwierdź DPA")["state"], "done")
        t = self.task("Wyślij przypomnienie")
        self.assertEqual((t["group"], t["date"], t["executor"], t["detail"]["notes"]),
                         ("Do rozplanowania", day(4), "ty", ["z pytania 2, %s" % day(0)]))
        _, failed = projekt.apply_effects(self.folder, ["nowe: Wyślij przypomnienie | kto: ty"], 2, DAY)
        self.assertEqual(len(failed), 1)

    def test_bledy_nie_zatrzymuja_kolejnych(self):
        applied, failed = projekt.apply_effects(self.folder, [
            "kiedy: %s → opublikuj post" % day(5),           # pasuje do 2 otwartych zadań
            "kiedy: %s → nie ma takiego" % day(5),
            "po: nie ma takiego → post 3",
            "usuń: post 3",
            "kiedy: %s → napisz post 1" % day(5)], 3, day(0))   # zrobione, ale jedyne pasujące
        self.assertEqual(len(failed), 4)
        self.assertIn("pasuje do 2 otwartych zadań", failed[0])
        self.assertIn("nie pasuje do żadnego zadania", failed[1])
        self.assertEqual(len(applied), 1)
        self.assertEqual(self.task("Napisz post 1")["date"], day(5))
        self.assertEqual(self.task("Opublikuj post 2")["date"], day(1))
        with self.assertRaises(ValueError):
            projekt.apply_effects(self.folder, [], 1, "jutro")


class Odblokowania(Baza):
    def test_unlocks(self):
        self.zadania("- [ ] Zatwierdź teksty | kto: ty | kiedy: %s | czas: 10\n"
                     "- [ ] Opublikuj stronę | kto: claude | kiedy: %s | po: teksty\n"
                     "- [ ] Wyślij newsletter | kto: claude | kiedy: %s | po: zatwierdź teksty, opublikuj\n"
                     "- [x] Zrobione wcześniej | kto: claude | po: teksty\n" % (day(1), day(3), day(2)))
        t = {x["title"]: x for x in self.tasks()}
        self.assertEqual([u["title"] for u in t["Zatwierdź teksty"]["unlocks"]], ["Opublikuj stronę", "Wyślij newsletter"])
        self.assertEqual(t["Zatwierdź teksty"]["unlockCount"], 2)
        self.assertEqual(t["Opublikuj stronę"]["unlocks"],
                         [{"id": t["Wyślij newsletter"]["id"], "title": "Wyślij newsletter", "executor": "claude",
                           "date": day(2)}])
        self.assertEqual((t["Wyślij newsletter"]["unlockCount"], t["Zrobione wcześniej"]["unlocks"]), (0, []))

    def test_czeka_na_ciebie_pogrupowane(self):
        self.zadania("- [ ] Zatwierdź teksty | kto: ty | kiedy: %s | czas: 10\n"
                     "- [ ] Opublikuj stronę | kto: claude | kiedy: %s | po: teksty\n"
                     "- [ ] Wyślij newsletter | kto: claude | kiedy: %s | po: teksty\n"
                     "- [ ] Podpisz umowę | kto: ty | kiedy: %s | czas: 5\n"
                     "- [ ] Wystaw fakturę | kto: claude | kiedy: %s | po: umowę\n"
                     % (day(1), day(3), day(2), day(1), day(4)))
        f = pm.facts(DAY, self.runs)
        self.assertEqual(len(f["waitingOnYou"]), 3)
        g = f["waitingOnYouBy"]
        self.assertEqual([(x["title"], x["count"]) for x in g], [("Zatwierdź teksty", 2), ("Podpisz umowę", 1)])
        self.assertEqual(g[0]["nearest"], {"title": "Wyślij newsletter", "date": day(2)})
        text = pm.text(f)
        self.assertIn("◆ czeka na Ciebie: Alfa · Zatwierdź teksty wstrzymuje 2 zadań (najbliższe: Wyślij newsletter, "
                      "za 2 dni)", text)
        self.assertIn("◆ czeka na Ciebie: Alfa · Wystaw fakturę · po Twoim zadaniu „Podpisz umowę”", text)
        self.assertNotIn("Opublikuj stronę · po Twoim", text)

    def test_kolejnosc_dzis_i_top(self):
        beta = self.new_project("beta", "Beta")
        self.card("- priorytet: 4\n")
        self.card("- priorytet: 1\n", folder=beta)
        self.zadania("- [ ] Zatwierdź teksty | kto: ty | kiedy: %s | czas: 10\n"
                     "- [ ] Opublikuj stronę | kto: claude | kiedy: %s | po: teksty\n"
                     "- [ ] Zaległe alfa | kto: ty | kiedy: %s | czas: 10\n" % (day(0), day(3), day(-2)))
        self.zadania("- [ ] Zadzwoń beta | kto: ty | kiedy: %s | czas: 10\n"
                     "- [ ] Zaległe beta | kto: ty | kiedy: %s | czas: 10\n" % (day(0), day(-1)), beta)
        f = pm.facts(DAY, self.runs)
        self.assertEqual([t["title"] for t in f["today_tasks"]], ["Zatwierdź teksty", "Zadzwoń beta"])
        self.assertEqual(f["today_tasks"][0]["unlockCount"], 1)
        self.assertEqual([t["title"] for t in f["top"]], ["Zaległe alfa", "Zaległe beta", "Zatwierdź teksty"])


class Szablon(Baza):
    def test_instrukcje_agentow(self):
        for name in ("CLAUDE.md", "AGENTS.md"):
            text = self.text(name)
            self.assertIn("`   skutek: …`", text)
            self.assertIn("albo w zostało", text)

    def test_szablon_bez_nowych_brakow(self):
        gaps = self.gaps("zadania")
        self.assertFalse([g for g in gaps if "sprawdza" in g or "„gotowe gdy” z" in g], gaps)


if __name__ == "__main__":
    unittest.main()
