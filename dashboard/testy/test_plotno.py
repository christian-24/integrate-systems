"""Strona Asystent: karty z katalogu (sprawdzenie bloku ```karty```, bez HTML), silnik zapytań w przeglądarce
(JS przez osascript albo node), biblioteka kart (trasy z sesją, zapis, limity), atrapa Claude z blokiem kart,
internet dla asystenta (PANEL_ASYSTENT_INTERNET)."""
import json
import os
import re
import sys
import tempfile
import unittest

from wspolne import Baza
from test_blokady import JS, PANEL, run_js
from test_serwer import REMOTE, Serwer

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import karty  # noqa: E402
import server  # noqa: E402

Q = {"zrodlo": "zadania", "filtr": {"stan": "otwarte"}}


def block(obj):
    return "Tekst.\n```karty\n" + json.dumps(obj, ensure_ascii=False) + "\n```\nOtwórz: a|ZADANIA.md|3"


class Walidacja(unittest.TestCase):
    def test_dobre_karty(self):
        cards = [{"id": "a", "typ": "liczba", "tytul": "A", "zapytanie": Q,
                  "porownaj": {"etykieta": "Twoje", "zapytanie": {"zrodlo": "zadania", "filtr": {"kto": "dla-ciebie"}}}},
                 {"id": "b", "typ": "wykres", "rodzaj": "linia", "tytul": "B",
                  "zapytanie": {"zrodlo": "zadania", "filtr": {"od": "-7", "do": "dziś"}, "grupuj": "dzien", "miara": "minuty"}},
                 {"id": "c", "typ": "news", "tytul": "C", "dane": {"pozycje": [
                     {"tytul": "N", "zrodlo": "s", "data": "2026-11-20", "link": "https://example.com/x?a=1"}]}},
                 {"id": "d", "typ": "tabela", "tytul": "D", "kolumny": ["tytul", "data"], "zapytanie": dict(Q, limit=5)},
                 {"id": "e", "typ": "postep", "tytul": "E"},
                 {"id": "dzis-dla-ciebie"}]
        text, ops = karty.extract(block({"pokaz": cards, "usun": ["x", "x", "Zły id"]}))
        self.assertEqual(ops["bledy"], [])
        self.assertEqual([c["id"] for c in ops["pokaz"]], ["a", "b", "c", "d", "e", "dzis-dla-ciebie"])
        self.assertEqual(ops["usun"], ["x"])
        self.assertEqual(text, "Tekst.\n\nOtwórz: a|ZADANIA.md|3")
        self.assertEqual(ops["pokaz"][5], {"id": "dzis-dla-ciebie"})            # odwołanie do gotowej karty

    def test_odrzucone(self):
        bad = [
            ("nieznany typ", {"id": "a", "typ": "iframe", "tytul": "A", "dane": {}}),
            ("nieznane pole html", {"id": "a", "typ": "liczba", "tytul": "A", "zapytanie": Q, "html": "x"}),
            ("dane.tekst: bez HTML", {"id": "a", "typ": "notatka", "tytul": "A", "dane": {"tekst": "<script>alert(1)</script>"}}),
            ("tytul: bez HTML", {"id": "a", "typ": "liczba", "tytul": "<img src=x onerror=1>", "zapytanie": Q}),
            ("link: bez HTML", {"id": "a", "typ": "news", "tytul": "A", "dane": {"pozycje": [
                {"tytul": "N", "zrodlo": "s", "link": "javascript:alert(1)"}]}}),
            ("tylko adres http", {"id": "a", "typ": "news", "tytul": "A", "dane": {"pozycje": [
                {"tytul": "N", "zrodlo": "s", "link": "ftp://example.com/x"}]}}),
            ("link: wymagany", {"id": "a", "typ": "news", "tytul": "A", "dane": {"pozycje": [{"tytul": "N", "zrodlo": "s"}]}}),
            ("zapytanie.zrodlo", {"id": "a", "typ": "liczba", "tytul": "A", "zapytanie": {"zrodlo": "pliki"}}),
            ("filtr: nieznane pole xx", {"id": "a", "typ": "liczba", "tytul": "A", "zapytanie": {"zrodlo": "zadania", "filtr": {"xx": 1}}}),
            ("RRRR-MM-DD", {"id": "a", "typ": "liczba", "tytul": "A", "zapytanie": {"zrodlo": "zadania", "filtr": {"od": "kiedyś"}}}),
            ("zapytanie.limit", {"id": "a", "typ": "lista", "tytul": "A", "zapytanie": {"zrodlo": "zadania", "limit": 500}}),
            ("wymaga grupuj", {"id": "a", "typ": "wykres", "tytul": "A", "zapytanie": Q}),
            ("wymagane zapytanie albo dane", {"id": "a", "typ": "lista", "tytul": "A"}),
            ("nie oba", {"id": "a", "typ": "liczba", "tytul": "A", "zapytanie": Q, "dane": {"wartosc": 1}}),
            ("id:", {"id": "A B", "typ": "liczba", "tytul": "A", "zapytanie": Q}),
            ("nieznane pole dane", {"id": "a", "typ": "postep", "tytul": "A", "dane": {}}),
            ("tytul: wymagany", {"id": "a", "typ": "postep", "tytul": " "}),
        ]
        for why, c in bad:
            with self.subTest(why):
                _, ops = karty.extract(block({"pokaz": [c]}))
                self.assertEqual(ops["pokaz"], [])
                self.assertEqual(len(ops["bledy"]), 1)
                self.assertIn(why, ops["bledy"][0])

    def test_blok_i_limity(self):
        _, ops = karty.extract("```karty\n{nie json\n```")
        self.assertEqual(ops["bledy"], ["blok kart: nieprawidłowy JSON"])
        _, ops = karty.extract("```karty\n{\"pokaz\": [], \"skrypt\": 1}\n```")
        self.assertIn("dozwolone tylko pokaz i usun", ops["bledy"][0])
        many = [{"id": "k%d" % i, "typ": "postep", "tytul": "K"} for i in range(karty.MAX_CARDS + 3)]
        _, ops = karty.extract(block(many))                                    # sama lista = pokaz
        self.assertEqual(len(ops["pokaz"]), karty.MAX_CARDS)
        # niedomknięty blok na końcu (odpowiedź ucięta) i dwa bloki
        text, ops = karty.extract("A\n```karty\n[{\"id\": \"a\", \"typ\": \"postep\", \"tytul\": \"A\"}]\n```\nB\n"
                                  "```karty\n[{\"id\": \"b\", \"typ\": \"postep\", \"tytul\": \"B\"}]")
        self.assertEqual((text, [c["id"] for c in ops["pokaz"]]), ("A\n\nB", ["a", "b"]))


class Biblioteka(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.lib = karty.Library(os.path.join(self.dir.name, "czat", "karty.json"))

    def tearDown(self):
        self.dir.cleanup()

    def test_zapis_uklad_i_usuwanie(self):
        q = {"id": "q", "typ": "liczba", "tytul": "Q", "zapytanie": Q, "zapisz": True}
        news = {"id": "n", "typ": "notatka", "tytul": "N", "dane": {"tekst": "x"}}
        self.assertEqual(self.lib.save([q, news, {"id": "ref"}]), (200, "", ["q"]))  # dane wprost się nie zapisują
        lib = self.lib.read()
        self.assertEqual(list(lib["karty"]), ["q"])
        self.assertNotIn("zapisz", lib["karty"]["q"])
        self.assertIn("- q (liczba): Q", self.lib.summary())
        self.assertIn("- dzis-dla-ciebie (lista, wbudowana): Dziś dla Ciebie · Twoje otwarte sprawy na dziś i po terminie",
                      self.lib.summary())
        with self.assertRaises(karty.Bad):
            self.lib.save([{"id": "postep-projektow", "typ": "postep", "tytul": "X"}])  # id karty wbudowanej
        self.lib.layout(pins=["q", "postep-projektow", "q"])
        self.assertEqual(self.lib.read()["przypiete"], ["q", "postep-projektow"])
        self.lib.layout(hide="q", at="2026-11-22T10:00:00")
        self.assertEqual((self.lib.read()["przypiete"], self.lib.read()["ukryte"]), (["postep-projektow"], {"q": "2026-11-22T10:00:00"}))
        self.lib.layout(clear_hidden=True)
        self.assertEqual(self.lib.read()["ukryte"], {})
        self.assertEqual(self.lib.remove("q"), (200, ""))
        self.assertEqual(self.lib.remove("q")[0], 404)
        # plik zmieniony ręcznie: zła karta odpada przy odczycie
        with open(self.lib.path, "w", encoding="utf-8") as f:
            json.dump({"karty": {"z": {"id": "z", "typ": "notatka", "tytul": "<b>", "dane": {"tekst": "x"}}}}, f)
        self.assertEqual(self.lib.read()["karty"], {})

    def test_limity(self):
        self.lib.MAX_CARDS = 3
        for i in range(3):
            self.assertEqual(self.lib.save([{"id": "k%d" % i, "typ": "postep", "tytul": "K"}])[0], 200)
        self.assertEqual(self.lib.save([{"id": "k9", "typ": "postep", "tytul": "K"}])[0], 409)
        self.assertEqual(self.lib.save([{"id": "k1", "typ": "postep", "tytul": "Nowy"}])[0], 200)   # podmiana mieści się
        self.lib.MAX_BYTES = 450
        code, err, _ = self.lib.save([{"id": "k2", "typ": "postep", "tytul": "x" * 80, "opis": "y" * 200}])
        self.assertEqual(code, 413, err)


ENGINE_DATA = {
    "projects": [{"id": "a", "name": "Alfa", "state": "active", "tasksDone": 1, "tasksTotal": 4},
                 {"id": "b", "name": "Beta", "state": "paused", "tasksDone": 0, "tasksTotal": 1}],
    "stages": [{"id": "s1", "project": "a", "title": "Start", "date": "2026-11-30", "done": False, "total": 2, "open": 1}],
    "tasks": [
        {"id": "1", "project": "a", "title": "Nagraj", "executor": "ty", "state": "todo", "date": "2026-11-22", "minutes": 30, "kind": "zadanie", "stage": "s1"},
        {"id": "2", "project": "a", "title": "Stare", "executor": "claude", "state": "todo", "date": "2026-11-20", "kind": "zadanie", "needsYou": "zgoda"},
        {"id": "3", "project": "a", "title": "Zrobione", "executor": "ty", "state": "done", "date": "2026-11-21", "minutes": 15, "kind": "zadanie"},
        {"id": "4", "project": "a", "title": "Bez daty", "executor": "codex", "state": "doing", "kind": "zadanie"},
        {"id": "5", "project": "a", "title": "Post", "executor": "ty", "state": "todo", "date": "2026-11-24", "kind": "publikacja", "channel": "instagram, facebook", "minutes": 10},
        {"id": "6", "project": "b", "title": "Wstrzymany", "executor": "ty", "state": "todo", "date": "2026-11-22", "kind": "zadanie"}]}


@unittest.skipUnless(JS, "brak silnika JS (osascript albo node)")
class Silnik(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(PANEL, encoding="utf-8") as f:
            cls.html = f.read()
        cls.src = re.search(r"/\*karty:start\*/(.*?)/\*karty:end\*/", cls.html, re.S).group(1)

    def run_q(self, queries):
        js = self.src + "\nconst DATA=%s;\nJSON.stringify(%s.map(q=>kqRun(q,DATA,'2026-11-22')))" % (
            json.dumps(ENGINE_DATA), json.dumps(queries))
        r = run_js(js)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_zapytania(self):
        out = self.run_q([
            {"zrodlo": "zadania"},                                                        # 0: aktywne projekty, bez publikacji
            {"zrodlo": "zadania", "filtr": {"stan": "otwarte", "kto": "dla-ciebie"}, "sortuj": "data"},
            {"zrodlo": "zadania", "filtr": {"stan": "po terminie"}},
            {"zrodlo": "zadania", "filtr": {"od": "-2", "do": "dziś"}, "grupuj": "dzien", "miara": "minuty"},
            {"zrodlo": "publikacje", "grupuj": "kanal"},
            {"zrodlo": "zadania", "filtr": {"projekt": "beta"}},                         # wprost: także wstrzymany
            {"zrodlo": "zadania", "filtr": {"stan": "w toku", "kto": "agenci"}},
            {"zrodlo": "projekty"},
            {"zrodlo": "zadania", "sortuj": "-data", "limit": 2},
            {"zrodlo": "etapy", "filtr": {"szukaj": "sta"}},
            {"zrodlo": "zadania", "filtr": {"czeka": "dowolne"}, "grupuj": "projekt"},
            {"zrodlo": "projekty", "filtr": {"stan": "wstrzymane"}},
        ])
        self.assertEqual(out[0]["value"], 4)
        self.assertEqual([r["tytul"] for r in out[1]["rows"]], ["Stare", "Nagraj"])          # z datą rosnąco
        self.assertEqual([r["tytul"] for r in out[2]["rows"]], ["Stare"])
        self.assertEqual(out[3]["groups"], [{"klucz": "2026-11-20", "wartosc": 0}, {"klucz": "2026-11-21", "wartosc": 15},
                                            {"klucz": "2026-11-22", "wartosc": 30}])          # dni bez dziur
        self.assertEqual(sorted((g["klucz"], g["wartosc"]) for g in out[4]["groups"]), [("facebook", 1), ("instagram", 1)])
        self.assertEqual([r["tytul"] for r in out[5]["rows"]], ["Wstrzymany"])
        self.assertEqual([r["tytul"] for r in out[6]["rows"]], ["Bez daty"])
        self.assertEqual([(r["tytul"], r["postep"]) for r in out[7]["rows"]], [("Alfa", 25)])  # domyślnie aktywne
        self.assertEqual(([r["tytul"] for r in out[8]["rows"]], out[8]["total"]), (["Nagraj", "Zrobione"], 4))
        self.assertEqual([(r["tytul"], r["wartosc"]) for r in out[9]["rows"]], [("Start", 50)])
        self.assertEqual(out[10]["groups"], [{"klucz": "Alfa", "wartosc": 1}])
        self.assertEqual([r["tytul"] for r in out[11]["rows"]], ["Beta"])

    def test_karty_wbudowane_jak_w_pythonie(self):
        js = re.search(r"/\*apStart:start\*/\s*const AP_START=(.*?);\s*/\*apStart:end\*/", self.html, re.S).group(1)
        self.assertEqual(json.loads(js), karty.STARTERS)
        for c in karty.STARTERS:
            self.assertEqual(karty.card(c), c)


class Trasy(Serwer):
    def test_biblioteka_przez_panel(self):
        card = {"id": "moje", "typ": "liczba", "tytul": "Moje", "zapytanie": Q}
        self.assertEqual(self.post("/api/asystent/karty", {"zapisz": card})[0], 200)
        status, _, text = self.request("GET", "/api/asystent/karty")
        lib = json.loads(text)
        self.assertEqual((status, [c["id"] for c in lib["karty"]]), (200, ["moje"]))
        self.assertEqual(lib["wbudowane"], karty.STARTERS)
        self.assertEqual(self.post("/api/asystent/karty", {"przypiete": ["moje", "postep-projektow"]})[0], 200)
        self.assertEqual(self.post("/api/asystent/karty", {"ukryj": "postep-projektow"})[0], 200)
        lib = json.loads(self.request("GET", "/api/asystent/karty")[2])
        self.assertEqual((lib["przypiete"], list(lib["ukryte"])), (["moje"], ["postep-projektow"]))
        self.assertEqual(self.post("/api/asystent/karty", {"pokaz": "postep-projektow"})[0], 200)
        self.assertEqual(self.post("/api/asystent/karty", {"usun": "moje"})[0], 200)
        lib = json.loads(self.request("GET", "/api/asystent/karty")[2])
        self.assertEqual((lib["karty"], lib["przypiete"], lib["ukryte"]), ([], [], {}))
        # odmowy: zła karta, dane wprost, dwa działania naraz, za duże ciało
        status, ans = self.post("/api/asystent/karty", {"zapisz": dict(card, typ="skrypt")})
        self.assertEqual(status, 400)
        self.assertIn("nieznany typ", ans["error"])
        self.assertEqual(self.post("/api/asystent/karty", {"zapisz": {"id": "n", "typ": "notatka", "tytul": "N",
                                                                       "dane": {"tekst": "x"}}})[0], 400)
        self.assertEqual(self.post("/api/asystent/karty", {"usun": "a", "ukryj": "b"})[0], 400)
        self.assertEqual(self.post("/api/asystent/karty", {"przypiete": "moje"})[0], 400)
        self.assertEqual(self.post("/api/asystent/karty", {"zapisz": dict(card, opis="x" * 40000)})[0], 400)
        # bez sesji (zdalnie z hasłem): odczyt i zapis odmówione
        server.TOKEN = "haslo-do-testow"
        try:
            self.assertEqual(self.request("GET", "/api/asystent/karty", headers=REMOTE)[0], 401)
            self.assertEqual(self.request("POST", "/api/asystent/karty", body={"zapisz": card}, headers=REMOTE)[0], 401)
        finally:
            server.TOKEN = ""
        self.assertEqual(json.loads(self.request("GET", "/api/asystent/karty")[2])["karty"], [])


class AtrapaZKartami(Baza):
    def ask(self, text, manager=None):
        m = manager or self.manager
        self.assertEqual(m.assistant_send(text, "#asystent"), (202, "", {"pending": True}))
        self.wait_for(lambda: not m.assistant_get()[2]["pending"], timeout=15)
        return m.assistant_get()[2]

    def prompts(self):
        return [c["prompt"] for c in self.calls() if c.get("stream")]

    def test_blok_kart_i_biblioteka(self):
        a = self.ask("Pokaż karty")
        last = a["messages"][-1]
        self.assertEqual(last["text"], "Odpowiedź atrapy 1: karty.")                 # bez bloku w tekście
        self.assertEqual(last["cards"]["bledy"], [])
        self.assertEqual(len(last["cards"]["pokaz"]), 7)
        first = self.prompts()[0]
        for part in ("```karty", "Karty gotowe", "- dzis-dla-ciebie (lista, wbudowana)", "Na tej stronie nie używaj „Pokaż:”",
                     "[ekran: #asystent]"):
            self.assertIn(part, first)
        lib = self.manager.cards.read()["karty"]
        self.assertEqual(list(lib), ["otwarte-wg-projektu"])                          # tylko karta z "zapisz": true
        b = self.ask("Jeszcze raz zła karta")
        self.assertEqual([c["id"] for c in b["messages"][-1]["cards"]["pokaz"]], ["dobra"])
        self.assertEqual(len(b["messages"][-1]["cards"]["bledy"]), 2)
        self.assertIn("Karty gotowe", self.prompts()[1])                              # biblioteka się zmieniła
        self.assertIn("- otwarte-wg-projektu (wykres)", self.prompts()[1])
        self.ask("Dalej")
        self.assertNotIn("Karty gotowe", self.prompts()[2])                           # bez zmian: bez listy
        # nowa rozmowa zdejmuje ukryte karty, biblioteka zostaje
        self.manager.cards.layout(hide="notatka", at="2026-11-22T10:00:00")
        self.assertEqual(self.manager.assistant_reset()[0], 200)
        self.assertEqual(self.manager.cards.read()["ukryte"], {})
        self.assertIn("otwarte-wg-projektu", self.manager.cards.read()["karty"])

    def test_internet(self):
        self.ask("Cześć")
        argv = [c for c in self.calls() if c.get("stream")][0]["argv"]
        allow = argv[argv.index("--allowedTools") + 1].split(",")
        deny = argv[argv.index("--disallowedTools") + 1].split(",")
        self.assertIn("WebSearch", allow)
        self.assertIn("WebFetch", allow)
        self.assertNotIn("WebSearch", deny)
        self.assertIn("Bash", deny)
        self.assertIn("bez nazw klientów", self.prompts()[0])
        off = self.new_manager(PANEL_ASYSTENT_INTERNET="0")
        self.assertEqual(off.assistant_reset()[0], 200)                              # pełny prompt w nowej rozmowie
        self.ask("Bez internetu", manager=off)
        argv = [c for c in self.calls() if c.get("stream")][-1]["argv"]
        self.assertNotIn("WebSearch", argv[argv.index("--allowedTools") + 1].split(","))
        self.assertIn("WebSearch", argv[argv.index("--disallowedTools") + 1].split(","))
        self.assertNotIn("Internet (WebSearch", self.prompts()[-1])


if __name__ == "__main__":
    unittest.main()
