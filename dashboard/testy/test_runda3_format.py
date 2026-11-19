"""Runda 3, format i raport PM: priorytet projektu, propozycja pod pytaniem, wyniki publikacji, cel liczbowy kampanii,
nowe braki w ZADANIA.md, ryzyka „bez zapasu” i „ponad pojemność”, kolejność po priorytecie.

Testy pracują wyłącznie w katalogu tymczasowym (rejestr, zbieracz, uruchomienia).
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
ENV_KEYS = ("STAN_DIR", "LOKALNE_DIR", "PANEL_RUNS_DIR", "PANEL_DZIEN_MIN")


def day(n):
    return (DAY + datetime.timedelta(days=n)).isoformat()


def quiet(fn, *args, **kw):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*args, **kw)


class Baza(unittest.TestCase):
    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp(prefix="runda3-"))
        self._registry = projekt.REGISTRY
        projekt.REGISTRY = os.path.join(self.tmp, "projekty.json")
        self._environ = {k: os.environ.get(k) for k in ENV_KEYS}
        self.runs = os.path.join(self.tmp, "uruchomienia")
        os.environ.update({"STAN_DIR": os.path.join(self.tmp, "stan"), "LOKALNE_DIR": os.path.join(self.tmp, "lok"),
                           "PANEL_RUNS_DIR": self.runs})
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

    def read(self, folder=None):
        return projekt.read_project(folder or self.folder)

    def book_gaps(self, folder=None):
        doc = next(d for d in self.read(folder)["project"]["book"] if d["key"] == "zadania")
        return doc["gaps"]


class Priorytet(Baza):
    def test_priorytet_z_karty(self):
        self.card("- priorytet: 1\n")
        self.assertEqual(self.read()["project"]["priority"], 1)
        self.card()
        self.assertEqual(self.read()["project"]["priority"], 3)          # brak wiersza = 3
        self.card("- priorytet: 7\n")
        p = self.read()["project"]
        karta = next(d for d in p["book"] if d["key"] == "karta")
        self.assertEqual(p["priority"], 3)
        self.assertIn("priorytet: 7 (dozwolone: 1–5, 1 najważniejszy)", karta["gaps"])

    def test_szablon_karty_ma_priorytet(self):
        self.assertIn("- priorytet: 3", self.text("KARTA.md"))
        self.assertEqual(self.read()["project"]["priority"], 3)

    def test_zapis_priorytetu(self):
        self.card("- priorytet: 2\n")
        projekt.set_card_fields(self.folder, {"priority": 5})
        self.assertIn("- priorytet: 5\n", self.text("KARTA.md"))
        self.assertEqual(self.read()["project"]["priority"], 5)
        for bad in (0, 6, "1", True):
            with self.assertRaises(ValueError):
                projekt.set_card_fields(self.folder, {"priority": bad})

    def test_pojemnosc_dnia(self):
        self.assertEqual(projekt.day_minutes({}), 120)
        self.assertEqual(projekt.day_minutes({"PANEL_DZIEN_MIN": "90"}), 90)
        for bad in ("0", "-5", "dużo", ""):
            self.assertEqual(projekt.day_minutes({"PANEL_DZIEN_MIN": bad}), 120)


class Propozycja(Baza):
    QUESTIONS = ("\n## Pytania do właściciela\n1. Który kolor logo?\n   termin: %s\n   propozycja: niebieski,\n"
                 "   propozycja: jak strona\n2. Bez propozycji?\n" % day(-1))

    def test_propozycja_pod_pytaniem(self):
        self.card(questions=self.QUESTIONS)
        q = self.read()["project"]["questions"]
        self.assertEqual([(x["text"], x["proposal"], x["date"]) for x in q],
                         [("Który kolor logo?", "niebieski, jak strona", day(-1)), ("Bez propozycji?", "", "")])

    def test_odpowiedz_pod_propozycja(self):
        self.card(questions=self.QUESTIONS)
        projekt.set_answer(self.folder, 1, "zielony")
        q = self.read()["project"]["questions"][0]
        self.assertEqual((q["answer"], q["proposal"]), ("zielony", "niebieski, jak strona"))
        self.assertIn("   propozycja: jak strona\n   Odpowiedź: zielony\n2. Bez propozycji?", self.text("KARTA.md"))

    def test_raport_pokazuje_propozycje(self):
        self.card(questions=self.QUESTIONS)
        f = pm.facts(DAY, self.runs)
        q = next(x for x in f["decisions"] if x["kind"] == "pytanie" and x["title"] == "Który kolor logo?")
        self.assertEqual(q["proposal"], "niebieski, jak strona")
        text = pm.text(f)
        self.assertIn("Który kolor logo? (wczoraj, 2 min) · propozycja: niebieski, jak strona", text)
        self.assertIn("pytanie po terminie: Alfa · Który kolor logo? (termin wczoraj, propozycja: niebieski, jak strona)",
                      text)


CAMPAIGN = """# Kampania: Jesień

- stan: w toku
- cel: konta
- miernik: konta
- cel liczbowy: %(target)s
- wynik: %(result)s
- kanały: LinkedIn
- start: %(start)s
- koniec: %(end)s

## Grupa docelowa
firmy

## Przekaz
krótko

## Harmonogram
- [x] Post o ofercie | kanał: LinkedIn | kiedy: %(start)s | kto: ty | czas: 15
  materiał: posty/oferta.md
  wyświetlenia: 1 200
  kliknięcia: 34
  konta: 2
  link: https://example.com/post/1
- [ ] Drugi post | kanał: LinkedIn | kiedy: %(end)s
  kliknięcia: dużo
  link: nie-adres

## Wyniki i wnioski
"""


class Publikacje(Baza):
    def campaign(self, target="40 kont", result="12", state="w toku"):
        self.write("kampanie/jesien.md", (CAMPAIGN % {"target": target, "result": result, "start": day(-2),
                                                      "end": day(5)}).replace("- stan: w toku", "- stan: " + state))

    def pubs(self):
        return [t for t in self.read()["tasks"] if t["kind"] == "publikacja"]

    def test_wyniki_publikacji(self):
        self.campaign()
        first, second = self.pubs()
        d = first["detail"]
        self.assertEqual((d["views"], d["clicks"], d["accounts"], d["link"]), (1200, 34, 2, "https://example.com/post/1"))
        self.assertEqual(d["refs"], [{"path": "posty/oferta.md", "anchor": ""}])
        d = second["detail"]
        self.assertEqual((d["views"], d["clicks"], d["accounts"], d["link"]), (None, None, None, ""))
        self.assertEqual(d["notes"], ["kliknięcia: dużo", "link: nie-adres"])      # zła wartość zostaje notatką

    def test_zadanie_bez_wynikow_nie_ma_nowych_kluczy(self):
        t = self.read()["tasks"][0]
        self.assertEqual(set(t["detail"]), set(projekt.blank_detail()))
        self.assertNotIn("views", t["detail"])

    def test_cel_liczbowy_i_wynik_jako_liczby(self):
        self.campaign()
        c = self.read()["campaigns"][0]
        self.assertEqual((c["target"], c["result"]), (40, 12))
        self.assertIsInstance(c["target"], int)
        self.campaign(target="1 200 wyświetleń", result="2,5")
        c = self.read()["campaigns"][0]
        self.assertEqual((c["target"], c["result"]), (1200, 2.5))
        self.campaign(target="", result="")
        c = self.read()["campaigns"][0]
        self.assertEqual((c["target"], c["result"]), (None, None))

    def test_zapis_wynikow(self):
        self.campaign()
        second = self.pubs()[1]
        rel, line = second["file"], second["line"]
        self.assertTrue(projekt.set_detail(self.folder, rel, line, "Drugi post", "wyświetlenia", "3 400"))
        self.assertTrue(projekt.set_detail(self.folder, rel, line, "Drugi post", "konta", "1"))
        self.assertTrue(projekt.set_detail(self.folder, rel, line, "Drugi post", "link", "https://example.com/2"))
        d = self.pubs()[1]["detail"]
        self.assertEqual((d["views"], d["accounts"], d["link"]), (3400, 1, "https://example.com/2"))
        text = self.text("kampanie/jesien.md")
        self.assertIn("- [ ] Drugi post | kanał: LinkedIn | kiedy: %s\n  wyświetlenia: 3400\n  kliknięcia: dużo\n"
                      "  konta: 1\n  link: https://example.com/2\n" % day(5), text)
        for key, bad in (("wyświetlenia", "dużo"), ("kliknięcia", "-3"), ("link", "ftp://x"), ("link", "http://a b")):
            with self.assertRaises(ValueError):
                projekt.set_detail(self.folder, rel, line, "Drugi post", key, bad)
        self.assertTrue(projekt.set_detail(self.folder, rel, line, "Drugi post", "wyświetlenia", ""))
        self.assertIsNone(self.pubs()[1]["detail"]["views"])

    def test_raport_kampanii(self):
        self.campaign()
        c = pm.facts(DAY, self.runs)["campaigns"][0]
        self.assertEqual((c["target"], c["result"], c["progress"]), (40, 12, 30))


class Braki(Baza):
    def zadania(self, rows, extra=""):
        self.write("ZADANIA.md", "# Zadania: X\n\n## Etap: A\ntermin: %s\n\n%s\n\n## Do rozplanowania\n%s"
                   % (day(30), rows, extra))

    def gap(self, prefix):
        return next((g for g in self.book_gaps() if g.startswith(prefix)), None)

    def test_szablon_bez_brakow_w_zadaniach(self):
        self.assertEqual(self.book_gaps(), [])
        titles = [t["title"] for t in self.read()["tasks"]]
        self.assertEqual(titles, ["Uzupełnij Kartę projektu", "Uzupełnij README i docs/"])
        t = self.read()["tasks"][0]
        self.assertTrue(t["detail"]["steps"] and t["detail"]["refs"] and t["detail"]["doneWhen"])

    def test_zadanie_wlasciciela_bez_krokow_i_materialu(self):
        self.zadania("- [ ] Wyślij ofertę | kto: ty | kiedy: %s | czas: 10\n  gotowe gdy: wysłana\n"
                     "- [ ] Zadzwoń | kto: ty | kiedy: %s | czas: 5\n  gotowe gdy: g\n  materiał: plan.md\n"
                     "- [ ] Sprawdź listę | kto: ty | kiedy: %s | czas: 5\n  gotowe gdy: g\n  - [ ] krok\n"
                     "- [ ] Zaplanuj wyjazd | kto: ty | kiedy: %s | czas: 5\n  gotowe gdy: g\n"
                     "- [ ] Opłać fakturę | kto: ty | kiedy: %s | czas: 5\n  gotowe gdy: g\n"
                     % (day(3), day(2), day(1), day(20), day(-1)))
        self.assertEqual(self.gap("Twoje zadania na 7 dni"),
                         "Twoje zadania na 7 dni bez kroków i materiału: 2 („Wyślij ofertę”, „Opłać fakturę”)")

    def test_zadanie_wlasciciela_bez_czasu(self):
        self.zadania("- [ ] Wyślij ofertę | kto: ty | kiedy: %s\n  gotowe gdy: g\n  materiał: a.md\n"
                     "- [x] Zrobione | kto: ty\n" % day(20))
        self.assertEqual(self.gap("Twoje zadania bez"), "Twoje zadania bez „czas”: 1 („Wyślij ofertę”)")

    def test_zadanie_agenta_bez_kiedy(self):
        self.zadania("- [ ] Napisz test | kto: claude\n  gotowe gdy: g\n- [ ] Popraw błąd | kto: codex | kiedy: %s\n"
                     "  gotowe gdy: g\n- [ ] Przejrzyj kod\n  gotowe gdy: g\n" % day(1),
                     "- [ ] Zbadaj pomysł | kto: claude\n")
        self.assertEqual(self.gap("zadania agenta"), "zadania agenta bez „kiedy”: 1 („Napisz test”)")
        text = self.text("KARTA.md").replace("- stan: aktywny", "- stan: wstrzymany")
        self.write("KARTA.md", text)
        self.assertIsNone(self.gap("zadania agenta"))                    # tylko aktywne projekty

    def test_tytul_od_rzeczownika(self):
        self.zadania("- [ ] Przygotowanie oferty | kto: claude | kiedy: %s\n  gotowe gdy: g\n"
                     "- [ ] Przygotuj ofertę | kto: claude | kiedy: %s\n  gotowe gdy: g\n" % (day(1), day(1)))
        self.assertEqual(self.gap("tytuł nie"), "tytuł nie zaczyna się od czasownika: 1 („Przygotowanie oferty”)")

    def test_wynik_bez_odbioru(self):
        self.zadania("- [ ] Napisz raport | kto: claude | kiedy: %(d)s\n  gotowe gdy: g\n  wynik: raport w docs/\n"
                     "- [~] Napisz plan | kto: claude | kiedy: %(d)s\n  gotowe gdy: g\n  wynik: plan\n"
                     "- [ ] Napisz notę | kto: claude | kiedy: %(d)s | wymaga: odbiór\n  gotowe gdy: g\n  wynik: nota\n"
                     "- [!] Napisz umowę | kto: claude | kiedy: %(d)s | blokada: brak danych\n  gotowe gdy: g\n"
                     "  wynik: szkic\n" % {"d": day(1)})
        self.assertEqual(self.gap("otwarte zadania z"),
                         "otwarte zadania z „wynik:” bez odbioru i nie w toku: 1 („Napisz raport”)")

    def test_kampania_w_toku_bez_celu_liczbowego(self):
        self.write("kampanie/jesien.md", CAMPAIGN % {"target": "", "result": "", "start": day(-2), "end": day(5)})
        self.assertEqual(self.gap("kampania"), "kampania w toku bez „cel liczbowy”: 1 („Jesień”)")
        self.write("kampanie/jesien.md", CAMPAIGN % {"target": "40", "result": "", "start": day(-2), "end": day(5)})
        self.assertIsNone(self.gap("kampania"))
        self.write("kampanie/jesien.md", (CAMPAIGN % {"target": "", "result": "", "start": day(-2), "end": day(5)})
                   .replace("- stan: w toku", "- stan: plan"))
        self.assertIsNone(self.gap("kampania"))

    def test_najwyzej_piec_przykladow(self):
        self.zadania("\n".join("- [ ] Zrób rzecz %d | kto: ty | kiedy: %s\n  gotowe gdy: g\n  materiał: a.md"
                               % (i, day(20)) for i in range(7)))
        self.assertEqual(self.gap("Twoje zadania bez"),
                         "Twoje zadania bez „czas”: 7 („Zrób rzecz 0”, „Zrób rzecz 1”, „Zrób rzecz 2”, "
                         "„Zrób rzecz 3”, „Zrób rzecz 4” i 2 inne)")

    def test_sprawdz_zglasza_braki(self):
        self.zadania("- [ ] Wyślij ofertę | kto: ty | kiedy: %s\n" % day(1))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = projekt.cmd_sprawdz([self.folder])
        self.assertEqual(code, 1)
        self.assertIn("Twoje zadania bez „czas”: 1", out.getvalue())


class RaportPM(Baza):
    def setUp(self):
        super().setUp()
        self.beta = self.new_project("beta", "Beta")
        self.card("- priorytet: 4\n")
        self.card("- priorytet: 1\n", folder=self.beta)

    def zadania(self, rows, folder=None, stage_date=None):
        self.write("ZADANIA.md", "# Zadania: X\n\n## Etap: A\ntermin: %s\n\n%s\n\n## Do rozplanowania\n"
                   % (stage_date or day(30), rows), folder)

    def test_kolejnosc_po_priorytecie(self):
        self.zadania("- [ ] Wyślij ofertę alfa | kto: ty | kiedy: %s | czas: 10\n"
                     "- [ ] Zadzwoń alfa | kto: ty | kiedy: %s | czas: 10\n" % (day(0), day(1)))
        self.zadania("- [ ] Wyślij ofertę beta | kto: ty | kiedy: %s | czas: 10\n"
                     "- [ ] Zadzwoń beta | kto: ty | kiedy: %s | czas: 10\n" % (day(1), day(0)), self.beta)
        f = pm.facts(DAY, self.runs)
        self.assertEqual([t["title"] for t in f["decisions"]],
                         ["Zadzwoń beta", "Wyślij ofertę beta", "Wyślij ofertę alfa", "Zadzwoń alfa"])
        self.assertEqual([t["priority"] for t in f["decisions"]], [1, 1, 4, 4])
        self.assertEqual([t["title"] for t in f["today_tasks"]], ["Zadzwoń beta", "Wyślij ofertę alfa"])
        self.assertEqual([t["title"] for t in f["top"]], ["Zadzwoń beta", "Wyślij ofertę beta", "Wyślij ofertę alfa"])
        self.assertEqual({p["name"]: p["priority"] for p in f["projects"]}, {"Alfa": 4, "Beta": 1})

    def test_etap_bez_zapasu(self):
        self.zadania("- [ ] Uruchom test zamknięty 14 dni | kto: ty | kiedy: %s | czas: 5\n" % day(10),
                     stage_date=day(20))
        self.zadania("- [ ] Zbierz opinie | kto: claude | kiedy: %s\n  trwa: 3 dni\n"
                     "- [ ] Napisz podsumowanie | kto: claude | kiedy: %s\n" % (day(5), day(6)),
                     self.beta, stage_date=day(9))
        f = pm.facts(DAY, self.runs)
        self.assertEqual([(s["project"], s["end"], s["task"], s["days"]) for s in f["stagesNoSlack"]],
                         [("Alfa", day(24), "Uruchom test zamknięty 14 dni", 14)])
        self.zadania("- [ ] Zbierz opinie | kto: claude | kiedy: %s\n  trwa: 4 dni\n" % day(5), self.beta,
                     stage_date=day(9))
        f = pm.facts(DAY, self.runs)
        self.assertEqual(sorted((s["project"], s["end"]) for s in f["stagesNoSlack"]),
                         [("Alfa", day(24)), ("Beta", day(9))])
        self.assertEqual(f["counts"]["noSlack"], 2)
        self.assertIn("▲ bez zapasu: Beta · etap A (termin %s), ostatnie zadanie „Zbierz opinie” kończy się %s"
                      % (day(9), day(9)), pm.text(f))

    def test_etap_po_terminie_nie_jest_bez_zapasu(self):
        self.zadania("- [ ] Zrób | kto: claude | kiedy: %s\n" % day(-1), stage_date=day(-2))
        self.assertEqual(pm.facts(DAY, self.runs)["stagesNoSlack"], [])

    def test_ponad_pojemnosc(self):
        self.zadania("- [ ] Napisz ofertę | kto: ty | kiedy: %s | czas: 60\n"
                     "- [ ] Sprawdź umowę | kto: ty | kiedy: %s | czas: 30\n" % (day(0), day(-1)))
        self.zadania("- [ ] Zadzwoń do klienta | kto: ty | kiedy: %s | czas: 45\n"
                     "- [ ] Przejrzyj szkic | kto: claude | kiedy: %s | wymaga: odbiór\n" % (day(0), day(0)), self.beta)
        f = pm.facts(DAY, self.runs)
        self.assertEqual((f["dayMinutes"], f["capacity"]["minutes"], f["capacity"]["over"]), (120, 135, True))
        self.assertEqual([t["title"] for t in f["capacity"]["move"]], ["Napisz ofertę"])     # priorytet 4, później
        self.assertEqual(f["counts"]["overCapacity"], 1)
        self.assertIn("▲ ponad pojemność: Twoje sprawy na dziś 135 min, limit 120 min; do przesunięcia: "
                      "Alfa · Napisz ofertę (priorytet 4, 60 min)", pm.text(f))
        os.environ["PANEL_DZIEN_MIN"] = "200"
        f = pm.facts(DAY, self.runs)
        self.assertEqual((f["dayMinutes"], f["capacity"]["over"], f["capacity"]["move"]), (200, False, []))
        self.assertNotIn("ponad pojemność", pm.text(f))
        os.environ["PANEL_DZIEN_MIN"] = "20"
        move = [t["title"] for t in pm.facts(DAY, self.runs)["capacity"]["move"]]
        self.assertEqual(move, ["Napisz ofertę", "Sprawdź umowę", "Zadzwoń do klienta"])


if __name__ == "__main__":
    unittest.main()
