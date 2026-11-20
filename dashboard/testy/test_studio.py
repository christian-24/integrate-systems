"""Studio filmów (film.py): szablony z parametrami, rodzaj filmu (pokaz, objaśnienie), marka.json, panel i agent.

Renderowanie objaśnienia wymaga ffmpeg: test jest pomijany, gdy go nie ma (Mac bez ffmpeg). Na serwerze:
testy/render_na_serwerze.sh (kopiuje dashboard/ do /tmp, uruchamia ten plik, sprząta)."""
import json
import os
import shutil
import tempfile
import unittest

from wspolne import Baza, agents, server

film = server.film
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SZKICE = os.path.join(REPO, "szkice")

BRAND = {"nazwa": "Marka", "zrodlo": "test", "strony": ["example.org"],
         "kolory": {"tlo": "#fbf7f1", "tekst": "#2b1d12", "akcent": "#9e5f18", "akcent2": "#c79a3e"},
         "czcionki": {"tytul": "Fraunces", "tekst": "Inter", "napisy": "Inter"},
         "napisy": {"rozmiar": 50, "kolor": "#ffffff", "tlo": "#2b1d12", "krycie": 0.85},
         "plansza_startowa": {"tytul": "Marka", "podtytul": "Podtytuł", "czas": 2},
         "plansza_koncowa": {"tytul": "Koniec", "adres": "example.org", "czas": 2}}
_THREAD = film.threading.Thread
PNG16 = b"\x89PNG\r\n\x1a\n\x00\x00\x00\x0dIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x06\x00\x00\x00" + b"\x00" * 32


class _Inline:
    """Wątek uruchamiany od razu (test bez czekania)."""

    def __init__(self, target, args=(), daemon=None):
        self.target, self.args = target, args

    def start(self):
        self.target(*self.args)


POKAZ = {"opis": "Pokaz", "typ": "pokaz", "parametry": {"mebel": "Komoda", "szer": "80", "napis": "Wpisujesz mebel"},
         "url": "https://example.org/generator",
         "kroki": [{"napis": "{{napis}}", "wpisz": ["#nazwa", "{{mebel}}"]}, {"wpisz": ["#w", "{{szer}}"]},
                   {"napis": "{{mebel}} ({{szer}} cm)", "pauza": 2}]}
OBJ = {"opis": "Objaśnienie", "typ": "objasnienie", "parametry": {"problem": "Problem", "czas": 3},
       "plansze": [{"tekst": "{{problem}}", "podpis": "Podpis", "czas": "{{czas}}"}, {"tekst": "{{rozwiazanie}}"}]}


class Studio(unittest.TestCase):
    """Karta w katalogu tymczasowym: studio/ z marką i szablonami, posty/<dzień>-<nazwa>/scenariusz.json."""

    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp(prefix="studio-test-"))
        self.studio = os.path.join(self.tmp, "studio")
        os.makedirs(os.path.join(self.studio, "szablony"))
        self.write("studio/szablony/pokaz-a.json", POKAZ)
        self.write("studio/szablony/obj-a.json", OBJ)
        self.post = os.path.join(self.tmp, "posty", "2026-11-25-test")
        os.makedirs(self.post)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, rel, data):
        with open(os.path.join(self.tmp, rel), "w", encoding="utf-8") as f:
            f.write(data if isinstance(data, str) else json.dumps(data, ensure_ascii=False))

    def scenario(self, sc):
        self.write("posty/2026-11-25-test/scenariusz.json", sc)

    # ---------- podstawianie parametrów ----------
    def test_podstawienie_parametrow(self):
        self.assertEqual(film.fill({"a": ["x {{p}} y", "{{ p }}"], "n": "{{n}}", "s": "{{n}} s"}, {"p": "P", "n": 3}),
                         {"a": ["x P y", "P"], "n": 3, "s": "3 s"})          # sam znacznik zachowuje typ (liczba)
        with self.assertRaisesRegex(ValueError, "brak parametru „q”"):
            film.fill("{{q}}", {"p": 1})

    def test_szablon_z_wartosciami_domyslnymi(self):
        sc, name = film.expand({"szablon": "pokaz-a", "parametry": {"mebel": "Sofa"}}, self.studio)
        self.assertEqual(name, "pokaz-a")
        self.assertEqual(sc["kroki"][0], {"napis": "Wpisujesz mebel", "wpisz": ["#nazwa", "Sofa"]})
        self.assertEqual(sc["kroki"][2]["napis"], "Sofa (80 cm)")
        self.assertNotIn("parametry", sc)
        self.assertNotIn("opis", sc)
        self.assertEqual(sc["url"], "https://example.org/generator")

    def test_bledy_szablonu(self):
        with self.assertRaisesRegex(ValueError, "nie ma parametru „kolor”"):
            film.expand({"szablon": "pokaz-a", "parametry": {"kolor": "biały"}}, self.studio)
        with self.assertRaisesRegex(ValueError, "brak szablonu"):
            film.expand({"szablon": "inny"}, self.studio)
        for bad in ("../pokaz-a", "Pokaz", "a/b", ""):
            with self.assertRaisesRegex(ValueError, "nazwa szablonu"):
                film.expand({"szablon": bad}, self.studio)
        with self.assertRaisesRegex(ValueError, "brak parametru „rozwiazanie”"):   # bez wartości domyślnej: wymagany
            film.expand({"szablon": "obj-a"}, self.studio)
        with self.assertRaisesRegex(ValueError, "parametry"):
            film.expand({"szablon": "pokaz-a", "parametry": ["x"]}, self.studio)

    def test_pelny_scenariusz_bez_zmian(self):
        sc = {"url": "https://example.org", "kroki": [{"napis": "{{nie-parametr}}"}]}
        self.assertEqual(film.expand(sc, self.studio), (sc, ""))       # zgodność wstecz: bez podstawiania

    # ---------- rodzaj filmu ----------
    def test_wybor_rodzaju(self):
        self.assertEqual(film.kind_of({"url": "x"}), "pokaz")
        self.assertEqual(film.kind_of({"typ": "objasnienie", "plansze": []}), "objasnienie")
        self.scenario({"szablon": "obj-a", "parametry": {"rozwiazanie": "Rozwiązanie", "czas": 4}})
        info = film.describe(self.post)
        self.assertEqual((info["kind"], info["template"], info["error"], info["cards"]), ("objasnienie", "obj-a", "", 2))
        sc, _brand, _ = film.prepare(self.post)
        self.assertEqual(sc["plansze"][0], {"tekst": "Problem", "podpis": "Podpis", "czas": 4})
        self.write("studio/marka.json", BRAND)                              # pokaz: strony z marki
        self.scenario({"szablon": "pokaz-a"})
        info = film.describe(self.post)
        self.assertEqual((info["kind"], info["kindLabel"], info["steps"]), ("pokaz", film.KINDS["pokaz"], 3))

    def test_walidacja_objasnienia(self):
        ok = {"typ": "objasnienie", "plansze": [{"tekst": "A", "podpis": "B", "czas": 3}]}
        self.assertEqual(film.validate_scenario(ok), [])
        self.assertTrue(film.validate_scenario({"typ": "film"}))
        self.assertTrue(film.validate_scenario({"typ": "objasnienie", "plansze": []}))
        self.assertTrue(film.validate_scenario({"typ": "objasnienie", "plansze": [{"tekst": ""}]}))
        self.assertTrue(film.validate_scenario({"typ": "objasnienie", "plansze": [{"tekst": "A", "czas": 40}]}))
        self.assertTrue(film.validate_scenario({"typ": "objasnienie", "plansze": [{"tekst": "A"}] * 21}))
        self.assertTrue(film.validate_scenario({"url": "x", "plansza_startowa": "tak"}))
        self.scenario({"typ": "objasnienie", "plansze": [{"tekst": "A", "czas": 99}]})
        info = film.describe(self.post)
        self.assertEqual(info["kind"], "objasnienie")
        self.assertIn("plansza 1: czas", info["error"])

    def test_plansze_marki_domyslnie_wlaczone(self):
        self.scenario({"typ": "objasnienie", "plansze": [{"tekst": "A"}]})
        self.assertEqual((film.describe(self.post)["intro"], film.describe(self.post)["outro"]), (False, False))
        self.write("studio/marka.json", BRAND)
        info = film.describe(self.post)
        self.assertEqual((info["intro"], info["outro"]), (True, True))
        self.scenario({"typ": "objasnienie", "plansze": [{"tekst": "A"}], "plansza_koncowa": False})
        info = film.describe(self.post)
        self.assertEqual((info["intro"], info["outro"]), (True, False))
        self.scenario({"szablon": "pokaz-a", "plansza_startowa": False})        # wyłączenie przy szablonie
        info = film.describe(self.post)
        self.assertEqual((info["intro"], info["outro"]), (False, True))

    # ---------- marka.json ----------
    def test_walidacja_marki(self):
        self.assertEqual(film.validate_brand(BRAND), [])
        self.assertEqual(film.validate_brand({"kolory": {"tlo": "#fff", "tekst": "#000", "akcent": "#123456"}}), [])
        bad = json.loads(json.dumps(BRAND))
        bad["kolory"]["tlo"] = "beżowy"
        bad["kolory"]["inny"] = "#000000"
        bad["napisy"]["rozmiar"] = 300
        bad["napisy"]["krycie"] = 2
        bad["plansza_startowa"] = {"podtytul": "bez tytułu", "czas": 0}
        bad["plansza_koncowa"]["tlo"] = "red"
        errors = film.validate_brand(bad)
        for part in ("kolory.tlo", "napisy.rozmiar", "napisy.krycie", "plansza_startowa.tytul",
                     "plansza_startowa.czas", "plansza_koncowa.tlo"):
            self.assertTrue(any(e.startswith(part) for e in errors), (part, errors))
        # nieznany kolor nie blokuje filmów projektu: ostrzeżenie (runda 3 recenzji)
        self.assertFalse(any("kolory.inny" in e for e in errors))
        self.assertIn("marka.json: nieznany klucz „kolory.inny” (pomijany)", film.brand_warnings(bad))
        self.assertTrue(film.validate_brand([]))
        self.assertIn("kolory.akcent: brak", film.validate_brand({"kolory": {"tlo": "#fff", "tekst": "#000"}}))

    def test_wczytanie_marki(self):
        brand, errors, exists = film.load_brand(self.studio)
        self.assertEqual((errors, exists), ([], False))
        self.assertEqual(brand["napisy"], film.DEFAULT_BRAND["napisy"])       # bez marki: napisy jak dotąd
        self.write("studio/marka.json", {"kolory": {"tlo": "#fff", "tekst": "#000", "akcent": "#123456"},
                                         "napisy": {"rozmiar": 60}})
        brand, errors, exists = film.load_brand(self.studio)
        self.assertEqual((errors, exists), ([], True))
        self.assertEqual((brand["napisy"]["rozmiar"], brand["napisy"]["krycie"], brand["kolory"]["akcent2"]),
                         (60, 0.85, "#123456"))
        self.write("studio/marka.json", "{zły json")
        self.assertIn("niepoprawny JSON", film.load_brand(self.studio)[1][0])
        self.scenario({"url": "https://example.org", "kroki": [{"pauza": 1}]})
        self.assertIn("studio/marka.json", film.describe(self.post)["error"])

    def test_kontrast_napisow(self):
        self.assertGreater(film.contrast("#ffffff", "#000000"), 20)
        self.assertEqual(film.readable("#161310", "#7d5526", "#d93425"), "#d93425")   # za słaby kontrast: następny
        self.assertEqual(film.readable("#000000", "#111111", "#121212"), "#121212")   # żaden: ostatni

    def test_lista_szablonow(self):
        self.write("studio/szablony/zly.json", "[]")
        got = {t["name"]: t for t in film.list_templates(self.studio)}
        self.assertEqual(sorted(got), ["obj-a", "pokaz-a", "zly"])
        self.assertEqual((got["obj-a"]["kind"], got["obj-a"]["params"]), ("objasnienie", ["problem", "czas", "rozwiazanie"]))
        self.assertEqual(got["obj-a"]["kindLabel"], film.KINDS["objasnienie"])
        self.assertEqual(got["pokaz-a"]["kind"], "pokaz")
        self.assertTrue(got["zly"]["error"])
        self.assertEqual(film.list_templates(os.path.join(self.tmp, "brak")), [])


    # ---------- runda 1: walidacja szablonów i scenariuszy ----------
    def test_zle_znaczniki_w_szablonie(self):
        for bad in ("{{Kolor}}", "{{typ-mebla}}"):
            self.write("studio/szablony/zly.json", {"typ": "pokaz", "url": "https://example.org",
                                                    "kroki": [{"napis": bad}]})
            with self.assertRaisesRegex(ValueError, "zły znacznik"):
                film.load_template(self.studio, "zly")
        self.write("studio/szablony/zly.json", {"typ": "pokaz", "parametry": {"Kolor": "x"}, "url": "https://e.org",
                                                "kroki": [{"pauza": 1}]})
        with self.assertRaisesRegex(ValueError, "nazwa parametru „Kolor”"):
            film.load_template(self.studio, "zly")
        # niedomknięty znacznik: błąd zamiast dosłownego tekstu w filmie
        self.write("studio/szablony/zly.json", {"typ": "pokaz", "parametry": {"kolor": "x"}, "url": "https://e.org",
                                                "kroki": [{"napis": "{{ kolor} i {{kolor}}"}]})
        with self.assertRaisesRegex(ValueError, "zły znacznik"):
            film.expand({"szablon": "zly"}, self.studio)
        # znacznik w wartości parametru zostałby w filmie
        with self.assertRaisesRegex(ValueError, "parametr „mebel”: wartość nie może zawierać"):
            film.expand({"szablon": "pokaz-a", "parametry": {"mebel": "{{Kolor}}"}}, self.studio)
        # scenariusz pisany ręcznie: „{{” to zwykły tekst (zgodność wstecz); z szablonu: niepodstawiony znacznik
        self.assertFalse(film.validate_scenario({"url": "https://e.org", "kroki": [{"napis": "{{x}}"}]}))
        self.assertTrue(film.validate_scenario({"url": "https://e.org", "kroki": [{"napis": "{{x}}"}]}, template=True))

    def test_typy_parametrow(self):
        for value, word in ((None, "null"), ([1, 2], "lista"), ({"a": 1}, "obiekt"), (True, "bool")):
            with self.assertRaisesRegex(ValueError, "parametr „mebel”: tekst albo liczba"):
                film.expand({"szablon": "pokaz-a", "parametry": {"mebel": value}}, self.studio)
        sc, _ = film.expand({"szablon": "pokaz-a", "parametry": {"szer": 120}}, self.studio)
        self.assertEqual(sc["kroki"][1]["wpisz"], ["#w", 120])                # sam znacznik: typ wartości
        self.write("studio/szablony/zly.json", {"typ": "pokaz", "parametry": {"x": None}, "url": "https://e.org",
                                                "kroki": [{"napis": "{{x}}"}]})
        self.assertIn("parametr „x”", {t["name"]: t for t in film.list_templates(self.studio)}["zly"]["error"])

    def test_nieznane_klucze_obok_szablonu(self):
        for key in ("url", "kroki", "typ", "plansze", "logowanie"):
            with self.assertRaisesRegex(ValueError, "obok „szablon” dozwolone tylko"):
                film.expand({"szablon": "pokaz-a", key: "x"}, self.studio)
        self.assertIn("nieznany klucz „tytul”", film.validate_scenario({"url": "https://e.org", "kroki": [{}],
                                                                        "tytul": "x"})[0])

    def test_walidacja_krokow_pokazu(self):
        ok = {"url": "https://example.org", "kroki": [{"napis": "A", "wpisz": ["#a", "b"], "pauza": 1}]}
        self.assertEqual(film.validate_scenario(ok), [])
        cases = ({"kroki": [{"pauza": 1}]}, "url"), \
            ({"url": "https://e.org", "kroki": [{"kilknij": "#a"}]}, "nieznany klucz „kilknij”"), \
            ({"url": "https://e.org", "kroki": [{"wpisz": "#a"}]}, "wpisz to [selektor, tekst]"), \
            ({"url": "https://e.org", "kroki": [{"wybierz": ["#a"]}]}, "wybierz to [selektor, tekst]"), \
            ({"url": "https://e.org", "kroki": [{"pauza": "2"}]}, "pauza 0–30"), \
            ({"url": "https://e.org", "kroki": [{"czekaj_na": "#a", "limit": 500}]}, "limit 1–120"), \
            ({"url": "https://e.org", "kroki": [{"kliknij": ""}]}, "kliknij to selektor"), \
            ({"url": "https://e.org", "kroki": []}, "kroki: lista"), \
            ({"url": "https://e.org", "kroki": [{"napis": "x" * 81}]}, "napis do 80")
        for sc, part in cases:
            errors = film.validate_scenario(sc)
            self.assertTrue(any(part in e for e in errors), (sc, errors))
        self.scenario({"url": "https://example.org", "kroki": [{"kilknij": "#a"}]})
        info = film.describe(self.post)
        self.assertIn("kilknij", info["error"])
        self.assertEqual(info["errorHint"], "Błąd w scenariuszu filmu.")

    def test_dozwolone_adresy_pokazu(self):
        base = {"kroki": [{"pauza": 1}]}
        brand = dict(film.DEFAULT_BRAND)
        for url in ("http://example.org", "file:///home/panel/x", "https://user:pw@example.org", "javascript:alert(1)"):
            self.assertIn("url: tylko adres https://", film.site_errors(dict(base, url=url), brand))
        self.assertIn("pole strony", film.site_errors(dict(base, url="https://example.org/a"), brand)[0])
        self.assertEqual(film.site_errors(dict(base, url="https://example.org/a"), dict(brand, strony=["example.org"])),
                         [])
        # konto demo tylko na stronie z marki
        self.assertIn("pole strony", film.site_errors(dict(base, url="https://example.org",
                                                            logowanie="https://example.org/logowanie"), brand)[0])
        brand = dict(brand, strony=["example.org"])
        self.assertEqual(film.site_errors(dict(base, url="https://app.example.org/g",
                                                logowanie="https://app.example.org/logowanie"), brand), [])
        self.assertIn("spoza stron marki", film.site_errors(dict(base, url="https://inny.pl"), brand)[0])
        self.assertIn("pole strony", film.site_errors(dict(base, url="https://example.org",
                                                            logowanie="https://evil.example.com/x"), brand)[0])
        self.assertIn("inny host", film.site_errors(dict(base, url="https://example.org",
                                                          logowanie="https://app.example.org/x"), brand)[0])
        self.assertIn("evil-example.org", film.site_errors(dict(base, url="https://evil-example.org"), brand)[0])
        self.write("studio/marka.json", dict(BRAND, strony=["example.org"]))
        self.scenario({"url": "https://inny.pl", "kroki": [{"pauza": 1}]})
        info = film.describe(self.post)
        self.assertIn("spoza stron marki", info["error"])
        self.assertEqual(info["errorHint"], "Adres strony w filmie jest niedozwolony.")

    def test_plik_studia_poza_karta(self):
        outside = os.path.realpath(tempfile.mkdtemp(prefix="poza-"))
        self.addCleanup(shutil.rmtree, outside, True)
        with open(os.path.join(outside, "obcy.json"), "w", encoding="utf-8") as f:
            json.dump(POKAZ, f)
        with open(os.path.join(outside, "marka.json"), "w", encoding="utf-8") as f:
            json.dump(BRAND, f)
        os.symlink(os.path.join(outside, "obcy.json"), os.path.join(self.studio, "szablony", "obcy.json"))
        with self.assertRaisesRegex(ValueError, "poza kartą"):
            film.load_template(self.studio, "obcy")
        os.symlink(os.path.join(outside, "marka.json"), os.path.join(self.studio, "marka.json"))
        self.assertIn("poza kartą", film.load_brand(self.studio)[1][0])

    def test_walidacja_czcionek_marki(self):
        for ok in ("Inter", "Inter:Bold", "Fraunces:Black", "Archivo Black", ""):
            self.assertEqual(film.validate_brand(dict(BRAND, czcionki={"tytul": ok})), [], ok)
        for bad in ("---", "/usr/share/fonts/a,b.ttf", "Inter:Heavy", "../x", "a" * 50):
            self.assertTrue(film.validate_brand(dict(BRAND, czcionki={"tytul": bad})), bad)
        self.assertEqual(film.font_spec("---", "/x.ttf"), ("/x.ttf", 0.0))       # pusty klucz: nie pierwsza lepsza
        self.assertEqual(film.validate_brand(dict(BRAND, inne=1)), [])                # literówka w kluczu marki:
        self.assertEqual(film.brand_warnings(dict(BRAND, inne=1)),                    # ostrzeżenie, nie błąd
                         ["marka.json: nieznany klucz „inne” (pomijany)"])
        self.assertTrue(film.validate_brand(dict(BRAND, strony=["https://x.pl"])))
        self.assertTrue(film.validate_brand(dict(BRAND, muzyka="../a.mp3")))
        self.write("studio/marka.json", dict(BRAND, muzyka="podklad.mp3"))
        self.assertIn("brak pliku", film.load_brand(self.studio)[1][0])

    def test_ucieczka_sciezek_w_filtrze(self):
        self.assertEqual(film._ff("/a/b.ttf"), "/a/b.ttf")
        got = film._ff("/f,o:n'[t].ttf")
        for ch in ",[]":
            self.assertIn("\\" + ch, got)
        self.assertNotIn(":", got.replace("\\\\:", ""))

    # ---------- typografia ----------
    def test_lamanie_po_polsku(self):
        f = film.Font(film.FONT, 88)
        for text in ("Zamówienie z Allegro przepisujesz ręcznie do ERP", "Papierowy dziennik moknie i ginie",
                     "Opis mebla w dwóch językach w 10 sekund", "Porozmawiajmy o Twoim procesie", "Kup a potem u nas"):
            lines = film.wrap(text, f, 900)
            self.assertEqual(" ".join(lines), text)
            for ln in lines[:-1]:
                self.assertNotIn(ln.split()[-1].lower(), film.GLUE, (text, lines))   # spójnik nie zostaje na końcu
        self.assertEqual(film.wrap("Kowal – kuźnia", f, 500), ["Kowal – kuźnia"][:1] if f.width("Kowal – kuźnia") <= 500
                         else ["Kowal –", "kuźnia"])
        # długie słowo: mniejsza czcionka zamiast cięcia w środku
        fit_f, lines = film.fit("Produktbeschreibungen für Möbel", f, 900, list(range(92, 59, -4)), 5)
        self.assertIn("Produktbeschreibungen", lines)
        self.assertLess(fit_f.size, 92)
        # słowo za długie nawet przy najmniejszej: podział z łącznikiem
        _f, lines = film.fit("x" * 60, f, 900, [64], 5)
        self.assertTrue(lines[0].endswith("-"))
        # wiersze podobnej długości (nie zachłannie)
        lines = film.wrap("aaaa bbbb cccc dddd eeee ffff gggg", f.at(60), 700)
        widths = [f.at(60).width(x) for x in lines]
        self.assertLess(max(widths) - min(widths), 260)

    def test_uklad_najdluzszego_tekstu(self):
        f = film.Font(film.FONT, 92)
        text = "Słowo " * 15
        self.assertLessEqual(len(text.strip()), film.TEXT_MAX)
        fit_f, lines = film.fit(text.strip(), f, film.TEXT_W, list(range(92, 59, -4)), 5)
        self.assertLessEqual(len(lines), 5)
        self.assertLessEqual(len(lines) * int(fit_f.size * 1.18), 1440 - 430 - 230)    # mieści się nad podpisem
        texts = film._Texts(self.tmp)
        st = film.caption_style(film.DEFAULT_BRAND)
        filters = film.caption_filters(texts, [(0, "Podpis " * 9)], 3, st)
        boxes = [x for x in filters if x.startswith("drawbox")]
        # jedno pudełko na cały napis (wejście w krokach krycia: te same wymiary, kolejne odcinki czasu)
        self.assertEqual(len({x.split(":color=")[0] for x in boxes}), 1)
        y, h = [int(v) for v in boxes[0].split(":y=")[1].split(":w=")[0:1] + [boxes[0].split(":h=")[1].split(":")[0]]]
        self.assertLessEqual(y + h, film.SIZE[1] - film.SAFE_BOTTOM)          # nad strefą interfejsu Reels
        self.assertTrue(all("max_glyph_a" in x for x in filters if x.startswith("drawtext")))  # linia bazowa

    def test_czas_czytania_planszy(self):
        self.assertEqual(film.card_time({"tekst": "Krótko"})[0], film.CARD_SHORT)            # bez podpisu: krócej
        self.assertEqual(film.card_time({"tekst": "Krótko", "podpis": "Pod"})[0], film.CARD_DEFAULT)
        sec, need = film.card_time({"tekst": "x" * 47, "podpis": "y" * 45, "czas": 3}, hook=True)   # 1. plansza: hak
        self.assertGreaterEqual(sec, film.HOOK_BASE + 92 / 15 - 0.01)
        self.assertGreaterEqual(film.card_time({"tekst": "x" * 47, "podpis": "y" * 45})[0], 1.2 + 92 / film.CARD_CPS - 0.01)
        self.scenario({"typ": "objasnienie", "plansze": [{"tekst": "x" * 47, "podpis": "y" * 45, "czas": 3},
                                                         {"tekst": "*Jedno* słowo"}]})
        info = film.describe(self.post)
        self.assertEqual(info["error"], "")
        self.assertEqual(info["warnings"][0], "Plansza 1 trwa 3 s, za krótko na przeczytanie; panel wydłuży ją do %s."
                         % film.sec_text(sec))                              # pełne zdanie, przecinek w liczbie
        self.assertIn(",", film.sec_text(sec))
        self.assertEqual(info["slides"][1], {"text": "Jedno słowo", "caption": "", "seconds": film.CARD_SHORT,
                                             "image": "", "markup": "*Jedno* słowo", "hook": False})
        self.assertAlmostEqual(info["seconds"], sec + film.CARD_SHORT - film.XFADE, places=1)
        self.assertTrue(film.validate_scenario({"typ": "objasnienie", "plansze": [{"tekst": "*bez pary"}]}))
        self.assertTrue(film.validate_scenario({"typ": "objasnienie", "plansze": [{"tekst": "x" * 91}]}))

    def test_obraz_na_planszy(self):
        self.scenario({"typ": "objasnienie", "plansze": [{"tekst": "Ekran", "obraz": "ekran.png"}]})
        self.assertIn("brak obrazu ekran.png", film.describe(self.post)["error"])
        os.makedirs(os.path.join(self.studio, "obrazy"))
        self.write("studio/obrazy/ekran.png", "png")
        self.assertIn("błąd obrazu ekran.png", film.describe(self.post)["error"])     # treść nie jest PNG
        with open(os.path.join(self.studio, "obrazy", "ekran.png"), "wb") as f:
            f.write(PNG16)
        self.assertEqual(film.describe(self.post)["error"], "")
        self.assertEqual(film.image_path(self.post, "ekran.png"), os.path.join(self.studio, "obrazy", "ekran.png"))
        with open(os.path.join(self.post, "ekran.png"), "wb") as f:           # najpierw folder posta
            f.write(PNG16)
        self.assertEqual(film.image_path(self.post, "ekran.png"), os.path.join(self.post, "ekran.png"))
        self.assertTrue(film.validate_scenario({"typ": "objasnienie", "plansze": [{"tekst": "A", "obraz": "../x.png"}]}))

    def test_plansza_startowa_z_hakiem(self):
        self.write("studio/marka.json", BRAND)
        self.scenario({"szablon": "obj-a", "parametry": {"rozwiazanie": "R"},
                       "plansza_startowa": {"tytul": "Hak posta", "czas": 1}})
        info = film.describe(self.post)
        self.assertEqual(info["error"], "")
        # hak nie dziedziczy podtytułu marki; czas wydłużony do czytania (0,6 s + 9 znaków / 15 + pół przejścia): hak
        # stoi od pierwszej klatki
        self.assertEqual(info["introCard"], {"title": "Hak posta", "subtitle": "", "address": "", "seconds": 1.38,
                                             "hook": True})
        self.assertIn("Plansza startowa trwa 1 s, za krótko na przeczytanie", info["warnings"][0])
        self.assertEqual(info["outroCard"]["address"], "example.org")
        self.scenario({"typ": "objasnienie", "plansze": [{"tekst": "A"}], "plansza_startowa": {"tytul": "x" * 61}})
        self.assertIn("plansza_startowa.tytul", film.describe(self.post)["error"])

    def test_tresc_filmu_dla_panelu(self):
        self.write("studio/marka.json", BRAND)
        self.write("studio/szablony/pokaz-a.json", dict(POKAZ, etykiety={"mebel": "Mebel"}))
        self.scenario({"szablon": "pokaz-a", "parametry": {"mebel": "Sofa"}})
        info = film.describe(self.post)
        self.assertEqual(info["templateDesc"], "Pokaz")
        # kolejność jak w filmie: napis 1, potem dane wpisywane na stronie
        sub = lambda p: {k: p[k] for k in ("name", "label", "value", "changed", "group")}  # noqa: E731
        self.assertEqual(sub(info["params"][0]), {"name": "napis", "label": "napis", "value": "Wpisujesz mebel",
                                                  "changed": False, "group": "napisy"})
        self.assertEqual(sub(info["params"][1]), {"name": "mebel", "label": "Mebel", "value": "Sofa", "changed": True,
                                                  "group": "napisy"})          # w napisie 2 i w formularzu
        self.assertEqual(sub(info["params"][2]), {"name": "szer", "label": "szer", "value": "80", "changed": False,
                                                  "group": "napisy"})
        self.assertEqual(info["fields"]["captions"], [["napis"], ["mebel", "szer"]])
        self.assertEqual(info["fields"]["form"], ["mebel", "szer"])
        self.assertEqual(info["captions"], ["Wpisujesz mebel", "Sofa (80 cm)"])
        self.assertEqual([x["kind"] for x in info["sequence"]], ["napis", "wpisz", "wpisz", "napis"])
        self.assertEqual((info["kindLabel"], info["kindHelp"]), (film.KINDS["pokaz"], film.KIND_HELP["pokaz"]))
        self.scenario({"szablon": "obj-a"})
        info = film.describe(self.post)
        self.assertEqual((info["errorHint"], info["kind"]), ("W scenariuszu brakuje danych do szablonu.", "objasnienie"))

    def test_kursor_w_kolorach_marki(self):
        brand = film.load_brand(self.studio)[0]
        brand["kolory"].update(akcent="#d93425", akcent2="#7d5526")
        js = film.cursor_js(brand)
        self.assertIn("rgba(125,85,38,.85)", js)
        self.assertIn("#d93425", js)
        self.assertNotIn("199,154,62", js)

    def test_wersja_filmu_z_szablonu_i_marki(self):
        self.write("studio/marka.json", BRAND)
        self.scenario({"szablon": "pokaz-a"})
        paths = [os.path.join(self.post, film.SCENARIO), os.path.join(self.studio, "szablony", "pokaz-a.json"),
                 os.path.join(self.studio, "marka.json")]
        for p in paths:
            os.utime(p, (100, 100))
        self.assertEqual(film.version(self.post), 100)
        os.utime(paths[1], (300, 300))
        self.assertEqual(film.version(self.post), 300)
        os.utime(paths[2], (400, 400))
        self.assertEqual(film.version(self.post), 400)
        os.utime(os.path.join(self.studio, "szablony", "obj-a.json"), (900, 900))   # inny szablon: bez wpływu
        self.assertEqual(film.version(self.post), 400)

    def test_rodzaj_przekazany_do_nagrania(self):
        rec = film.Recorder(python="/bin/false")
        rec.available = lambda kind="pokaz": True
        seen = []
        rec._run = lambda folder, title: seen.append(rec.kinds.get(folder))
        self.scenario({"typ": "objasnienie", "plansze": [{"tekst": "A"}]})
        film.threading.Thread = _Inline
        try:
            self.assertEqual(rec.start(self.post)[0], 202)
        finally:
            film.threading.Thread = _THREAD
        self.assertEqual(seen, ["objasnienie"])
        self.assertEqual(rec.interpreter("objasnienie"), film.sys.executable)

    # ---------- nagrywarka ----------
    def test_nagrywarka_bez_playwright_nagrywa_objasnienie(self):
        rec = film.Recorder(python=os.path.join(self.tmp, "brak-pythona"))
        which = film.shutil.which
        try:
            film.shutil.which = lambda name: "/usr/bin/ffmpeg"
            self.assertFalse(rec.available())
            self.assertTrue(rec.available("objasnienie"))
            self.assertEqual(rec.interpreter("objasnienie"), film.sys.executable)
            self.assertEqual(rec.interpreter("pokaz"), rec.python)
            self.scenario({"url": "https://example.org"})
            self.assertEqual(rec.start(self.post)[0], 409)                      # pokaz bez Playwright
            self.scenario({"typ": "objasnienie", "plansze": [{"tekst": "A"}]})
            rec._run = lambda folder, title: None
            self.assertEqual(rec.start(self.post)[0], 202)
            film.shutil.which = lambda name: None
            rec.busy.clear()
            code, msg, _ = rec.start(self.post)
            self.assertEqual(code, 409)
            self.assertIn("ffmpeg", msg)
        finally:
            film.shutil.which = which

    def test_blad_scenariusza_od_razu_w_stanie(self):
        rec = film.Recorder(python="/bin/false")
        rec.available = lambda kind="pokaz": True
        rec._run = lambda folder, title: self.fail("bez nagrania przy błędnym scenariuszu")
        self.scenario({"szablon": "nie-ma"})
        code, msg, _ = rec.start(self.post)
        self.assertEqual(code, 409)
        self.assertIn("brak szablonu", msg)
        st = film.read_state(self.post)
        self.assertEqual(st["state"], "error")
        self.assertIn("brak szablonu", st["error"])

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "brak ffmpeg (renderowanie na serwerze)")
    def test_render_objasnienia(self):
        self.write("studio/marka.json", BRAND)
        self.scenario({"szablon": "obj-a", "parametry": {"rozwiazanie": "Rozwiązanie: 100% gotowe", "czas": 1.5}})
        out = film.record(self.post)
        import subprocess
        probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height:format=duration",
                                "-of", "json", out], capture_output=True, text=True)
        meta = json.loads(probe.stdout)
        self.assertEqual((meta["streams"][0]["width"], meta["streams"][0]["height"]), (1080, 1920))
        self.assertAlmostEqual(float(meta["format"]["duration"]), film.describe(self.post)["seconds"], delta=0.3)
        self.assertIn("audio", [s["codec_type"] for s in meta["streams"]])           # cicha ścieżka AAC
        # najdłuższy dopuszczalny tekst z wyróżnieniem, obraz nad tekstem, hak zamiast planszy startowej
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=s=600x900:d=1", "-frames:v", "1",
                        os.path.join(self.post, "ekran.png")], check=True)
        self.scenario({"typ": "objasnienie", "plansza_startowa": {"tytul": "Hak"}, "plansze": [
            {"tekst": ("Przedsiębiorstwami zarządzamy przez *WMS, ERP, CRM, WWW* i Produktbeschreibungen")[:90],
             "podpis": "p" * 70, "obraz": "ekran.png"}, {"tekst": "x " * 45}]})
        self.assertEqual(film.describe(self.post)["error"], "")
        out = film.record(self.post, "objasnienie")
        probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", out],
                               capture_output=True, text=True)
        self.assertAlmostEqual(float(probe.stdout), film.describe(self.post)["seconds"], delta=0.3)


class StudioProjektow(unittest.TestCase):
    """Studio w kartach projektów (szkice/): marki poprawne, szablony się rozwijają, film A z szablonu."""

    def test_marki_i_szablony_w_kartach(self):
        for pid in ("generator-opisow-mebli", "company-audits", "naulikapp"):
            studio = os.path.join(SZKICE, pid, "studio")
            if not os.path.isdir(studio):
                self.skipTest("brak szkice/ (kopia bez kart)")
            brand, errors, exists = film.load_brand(studio)
            self.assertEqual((errors, exists), ([], True), pid)
            self.assertTrue(brand["zrodlo"], pid)                            # skąd kolory
            templates = film.list_templates(studio)
            self.assertTrue(templates, pid)
            self.assertGreaterEqual(len(templates), 2, pid)                 # więcej niż jeden układ filmu
            for t in templates:
                self.assertEqual(t["error"], "", (pid, t))
                self.assertNotEqual(t["title"], t["name"], (pid, t["name"]))  # czytelna nazwa dla właściciela
                with open(os.path.join(studio, "szablony", t["name"] + ".json"), encoding="utf-8") as f:
                    tpl = json.load(f)
                if t["required"]:                                          # bez treści posta szablon nie przejdzie
                    with self.assertRaisesRegex(ValueError, "wymagany"):
                        film.expand({"szablon": t["name"]}, studio)
                given = {k: tpl["parametry"][k] for k in t["required"]}
                sc, _ = film.expand({"szablon": t["name"], "parametry": given}, studio)
                self.assertEqual(film.validate_scenario(sc, template=True), [], (pid, t["name"]))
                self.assertEqual(film.site_errors(sc, brand), [], (pid, t["name"]))
                for key in ("plansza_startowa", "plansza_koncowa"):
                    card = film._card(brand, sc, key)
                    if card and not isinstance(sc.get(key), dict):     # plansza marki bez nadpisania: bez ostrzeżeń
                        self.assertNotIn("czas", card, (pid, key))
        nb = film.load_brand(os.path.join(SZKICE, "naulikapp", "studio"))[0]
        self.assertNotEqual(nb["plansza_koncowa"]["tytul"], nb["plansza_startowa"]["tytul"])   # koniec z wezwaniem
        kinds = {t["kind"] for pid in ("company-audits", "naulikapp")
                 for t in film.list_templates(os.path.join(SZKICE, pid, "studio"))}
        self.assertEqual(kinds, {"objasnienie"})
        opis = {t["kind"] for t in film.list_templates(os.path.join(SZKICE, "generator-opisow-mebli", "studio"))}
        self.assertEqual(opis, {"pokaz", "objasnienie"})                    # Opisarnia: pokaz i objaśnienie

    def test_film_a_z_szablonu(self):
        post = os.path.join(SZKICE, "generator-opisow-mebli", "posty", "2026-11-20-film-a-opis-pl-de")
        if not os.path.isfile(os.path.join(post, film.SCENARIO)):
            self.skipTest("brak posta filmu A")
        with open(os.path.join(post, film.SCENARIO), encoding="utf-8") as f:
            raw = json.load(f)
        self.assertEqual(raw["szablon"], "pokaz-generatora")
        sc, _brand, info = film.prepare(post)
        self.assertEqual((info["kind"], info["template"], info["intro"], info["outro"]),
                         ("pokaz", "pokaz-generatora", True, True))
        self.assertEqual(sc["url"], "https://opisarnia.pl/generator")
        self.assertIn({"napis": "Wpisujesz typ mebla", "wpisz": ["#g-nazwa", "Komoda Nordic, 4 szuflady"]}, sc["kroki"])
        self.assertIn(["#g-w", "80"], [k.get("wpisz") for k in sc["kroki"]])
        self.assertFalse(film.placeholders(sc))                              # wszystko podstawione
        brand = film.load_brand(film.studio_dir(post))[0]
        outro = brand["plansza_koncowa"]
        last = [k["napis"] for k in sc["kroki"] if k.get("napis")][-1]
        for part in (outro["tytul"], outro.get("adres", "")):
            self.assertNotIn(part, last)                                     # koniec pokazu nie dubluje planszy marki
        self.assertEqual(info["introCard"]["title"], raw["parametry"]["hak"])  # hak w pierwszej sekundzie
        self.assertEqual(info["introCard"]["subtitle"], "")                   # hak bez podtytułu marki
        self.assertGreaterEqual(info["introCard"]["seconds"],
                                film.HOOK_BASE + len(raw["parametry"]["hak"]) / 15 + film.XFADE / 2 - 0.01)   # da się przeczytać
        self.assertLessEqual(info["introCard"]["seconds"], film.HOOK_MAX + film.XFADE / 2)   # strona przed 3,5 s
        self.assertFalse([w for w in info["warnings"] if "za krótko" in w])
        self.assertEqual(film.site_errors(sc, brand), [])


class StudioWPanelu(Baza):
    """Serwer: studio w /api/data, rodzaj filmu w poście, materiał dla agenta; reguły agenta dla postów."""

    def setUp(self):
        super().setUp()
        self.studio = os.path.join(self.folder, "studio")
        os.makedirs(os.path.join(self.studio, "szablony"))
        for name, data in (("szablony/pokaz-a.json", POKAZ), ("szablony/obj-a.json", OBJ), ("marka.json", BRAND)):
            with open(os.path.join(self.studio, name), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        self.post = os.path.join(self.folder, "posty", "2026-11-25-film")
        os.makedirs(self.post)
        with open(os.path.join(self.post, film.SCENARIO), "w", encoding="utf-8") as f:
            json.dump({"szablon": "pokaz-a", "parametry": {"mebel": "Sofa"}}, f)

    def test_podsumowanie_studia(self):
        _, index = server.load_projects(resolve=False)
        got = server.studio_summary(index)
        self.assertEqual(list(got), ["projekt-testowy"])
        s = got["projekt-testowy"]
        self.assertEqual([(t["name"], t["kind"]) for t in s["templates"]], [("obj-a", "objasnienie"), ("pokaz-a", "pokaz")])
        self.assertEqual((s["brand"]["name"], s["brand"]["errors"], s["brand"]["colors"]["akcent"]), ("Marka", [], "#9e5f18"))
        self.assertEqual(s["brand"]["outro"], {"title": "Koniec", "subtitle": "", "address": "example.org",
                                             "seconds": film.brand_time(BRAND["plansza_koncowa"], "plansza_koncowa")[0],
                                             "bg": "#2b1d12", "fg": "#fbf7f1"})       # kolory do podglądu planszy
        self.assertEqual(s["brand"]["caption"], {"color": "#ffffff", "bg": "#2b1d12"})
        self.assertEqual([t["uses"] for t in s["templates"]], [[], ["2026-11-25"]])   # post z pokaz-a
        data = server.build_data()
        self.assertIn("projekt-testowy", data["studio"])
        self.assertIn("explainer", data["film"])

    def test_bez_studia_pusto(self):
        shutil.rmtree(self.studio)
        _, index = server.load_projects(resolve=False)
        self.assertEqual(server.studio_summary(index), {})

    def test_rodzaj_filmu_w_poscie(self):
        info = server.post_info(self.post)
        self.assertTrue(info["scenario"])
        self.assertEqual((info["filmInfo"]["kind"], info["filmInfo"]["template"], info["filmInfo"]["error"]),
                         ("pokaz", "pokaz-a", ""))
        os.remove(os.path.join(self.post, film.SCENARIO))
        self.assertIsNone(server.post_info(self.post)["filmInfo"])

    def test_material_poprawki_ze_studiem(self):
        self.assertEqual(server.film_refs(self.post), ["posty/2026-11-25-film/scenariusz.json",
                                                       "studio/szablony/pokaz-a.json", "studio/marka.json"])
        with open(os.path.join(self.post, film.SCENARIO), "w", encoding="utf-8") as f:
            json.dump({"typ": "objasnienie", "plansze": [{"tekst": "A"}]}, f)
        self.assertEqual(server.film_refs(self.post), ["posty/2026-11-25-film/scenariusz.json", "studio/marka.json"])

    def test_agent_przygotowuje_post_z_szablonu(self):
        d = self.manager.post_detail(self.folder, "2026-11-25", "facebook", "Post")
        self.assertIn('{"szablon": "<nazwa>", "parametry"', d["gotowe gdy"])
        self.assertIn("obj-a (objasnienie; parametry: problem, czas, rozwiazanie); pokaz-a (pokaz; parametry: napis, "
                      "mebel, szer)", d["gotowe gdy"])
        self.assertIn("film.py sprawdz", d["gotowe gdy"])
        self.assertEqual(d["materiał"][-3:], ["studio/szablony/obj-a.json", "studio/szablony/pokaz-a.json",
                                              "studio/marka.json"])
        shutil.rmtree(self.studio)
        d = self.manager.post_detail(self.folder, "2026-11-25", "", "Post")
        self.assertIn("objasnienie", d["gotowe gdy"])
        self.assertFalse([r for r in d["materiał"] if r.startswith("studio/")])

    def test_poprawka_szablonu_nagrywa_film_od_nowa(self):
        film_path = os.path.join(self.post, "film.mp4")
        with open(film_path, "wb") as f:
            f.write(b"x")
        files = [os.path.join(self.post, film.SCENARIO), os.path.join(self.studio, "szablony", "pokaz-a.json"),
                 os.path.join(self.studio, "marka.json")]
        for p in files:
            os.utime(p, (100, 100))
        os.utime(film_path, (200, 200))
        today = "2026-11-19"                                             # post 2026-11-25: nadchodzący
        self.assertIsNone(server.film_pending(self.post, today=today))
        for p, t in ((files[1], 300), (files[2], 400)):                 # agent poprawił szablon, potem markę
            os.utime(p, (t, t))
            self.assertEqual(server.film_pending(self.post, today=today), t)
            film.write_state(self.post, state="error", scenario=t)       # ta wersja już raz nagrywana
            self.assertIsNone(server.film_pending(self.post, today=today))

    def test_automat_nagrywa_objasnienie_bez_playwright(self):
        obj = os.path.join(self.folder, "posty", "2026-11-26-obj")
        os.makedirs(obj)
        with open(os.path.join(obj, film.SCENARIO), "w", encoding="utf-8") as f:
            json.dump({"typ": "objasnienie", "plansze": [{"tekst": "A"}]}, f)
        rec = film.Recorder(python="/brak")
        rec.available = lambda kind="pokaz": kind == "objasnienie"
        started = []
        rec.start = lambda folder, title="": started.append(os.path.basename(folder)) or (202, "")
        saved = server._recorder
        server._recorder = rec
        try:
            server.auto_record()
        finally:
            server._recorder = saved
        self.assertEqual(started, ["2026-11-26-obj"])                   # pokaz (2026-11-25-film) czeka na Playwright

    def test_agent_widzi_bledny_szablon(self):
        with open(os.path.join(self.studio, "szablony", "Pokaz.json"), "w", encoding="utf-8") as f:
            json.dump(POKAZ, f)
        templates, refs = self.manager.studio_refs(self.folder)
        bad = {t["name"]: t for t in templates}["Pokaz"]
        self.assertIn("nazwa szablonu", bad["error"])
        d = self.manager.post_detail(self.folder, "2026-11-25", "", "Post")
        self.assertIn("Pokaz (błąd: nazwa szablonu", d["gotowe gdy"])

    def test_regula_filmu_tylko_dla_postow(self):
        post = self.manager.task_prompt("claude", "P", "ZADANIA.md", 4, agents.POST_TASK + "2026-11-25: Post", "")
        fix = self.manager.task_prompt("claude", "P", "ZADANIA.md", 4, agents.FIX_POST_TASK + "2026-11-25: krótszy", "")
        other = self.manager.task_prompt("claude", "P", "ZADANIA.md", 4, "Zadanie", "")
        for p in (post, fix):
            self.assertIn("studio/szablony/*.json", p)
            self.assertIn('"typ": "objasnienie"', p)
        self.assertNotIn("studio/szablony", other)


if __name__ == "__main__":
    unittest.main()
