"""Studio filmów, runda 6 (recenzja rundy 3): błąd w polu nadpisanym przez post nie jest błędem szablonu, parametr
usunięty z szablonu nie blokuje nagrania, nieznany klucz marki to ostrzeżenie, podpowiedzi błędów po polsku, limit
znaków bez gwiazdek, stary zrzut błędu znika na starcie nagrania, ukrywanie elementów strony w pokazie, przejście
jasne↔ciemne bez szarości, kadr 4:5 nagrania strony, braki marki i dane właściciela w Studiu, wgrywanie (aac, stare
zrzuty), poprzednia wersja filmu, panel (filmWho bez przycisku, którego nie ma, skrót filmu w publikacji)."""
import json
import os
import re
import unittest

from test_studio_r2 import BRAND, Karta
from test_studio_r3 import OBJ, png
from test_studio_r4 import _Inline
from wspolne import server

film = server.film
PANEL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "panel.html")


class BledyPosta(Karta):
    def setUp(self):
        super().setUp()
        self.write("studio/szablony/obj-b.json", OBJ)

    def test_plansza_koncowa_posta_to_blad_posta_nie_szablonu(self):
        self.scenario({"szablon": "obj-b", "parametry": {"hak": "Hak posta"}, "plansza_koncowa": {"tytul": "x" * 70}})
        info = film.describe(self.post)
        self.assertTrue(info["error"].startswith("scenariusz posta: plansza_koncowa.tytul"), info["error"])
        self.assertNotIn("Błąd w szablonie", info["errorHint"])
        self.assertIn("nie w szablonie", info["errorHint"])

    def test_muzyka_posta_to_blad_posta(self):
        self.scenario({"szablon": "obj-b", "parametry": {"hak": "Hak posta"}, "muzyka": "../x.mp3"})
        info = film.describe(self.post)
        self.assertTrue(info["error"].startswith("scenariusz posta: muzyka"), info["error"])

    def test_blad_w_szablonie_nadal_przypisany_szablonowi(self):
        bad = dict(OBJ, plansza_koncowa={"tytul": "y" * 70})
        self.write("studio/szablony/obj-b.json", bad)
        self.scenario({"szablon": "obj-b", "parametry": {"hak": "Hak posta"}})
        self.assertTrue(film.describe(self.post)["error"].startswith("szablon obj-b:"))

    def test_usuniety_parametr_szablonu_to_ostrzezenie(self):
        self.scenario({"szablon": "obj-b", "parametry": {"hak": "Hak posta", "stary": "x"}})
        info = film.describe(self.post)
        self.assertEqual(info["error"], "")
        self.assertTrue(any("„stary”" in w for w in info["warnings"]), info["warnings"])
        with self.assertRaisesRegex(ValueError, "nie ma parametru „obcy”"):   # zmiana z panelu: nadal błąd
            film.apply_changes(self.post, params={"obcy": "x"})
        info = film.apply_changes(self.post, params={"hak": "Nowy hak"})     # inne pole: zapis mimo starego
        self.assertEqual(self.read_scenario()["parametry"]["hak"], "Nowy hak")

    def test_nieznany_klucz_marki_nie_blokuje_filmow(self):
        self.write("studio/marka.json", dict(BRAND, literowka=1))
        self.scenario({"szablon": "obj-b", "parametry": {"hak": "Hak posta"}})
        info = film.describe(self.post)
        self.assertEqual(info["error"], "")
        self.assertTrue(any("„literowka”" in w for w in info["warnings"]), info["warnings"])

    def test_podpowiedzi_i_typy_po_polsku(self):
        self.assertNotEqual(film.error_hint("muzyka: brak pliku studio/nie.mp3"), "Błąd w scenariuszu filmu.")
        self.assertNotEqual(film.error_hint("parametry: obiekt {nazwa: wartość}"), "Błąd w scenariuszu filmu.")
        for value, word in ((True, "prawda/fałsz"), (None, "puste pole"), ({}, "obiekt"), ([], "lista")):
            with self.assertRaises(ValueError) as e:
                film._param_value("x", value)
            self.assertIn(word, str(e.exception))
            self.assertNotRegex(str(e.exception), r"\((jest )?(bool|NoneType|dict|list|str)\)")

    def test_limit_bez_gwiazdek(self):
        limits = {"hak": {"max": film.HOOK_CHARS}}
        film._check_value("hak", "*12* " + "x" * (film.HOOK_CHARS - 3), limits)      # 43 widoczne znaki
        with self.assertRaisesRegex(ValueError, "najwyżej"):
            film._check_value("hak", "*12* " + "x" * (film.HOOK_CHARS - 2), limits)


class Marka(Karta):
    def test_braki_do_potwierdzenia_i_ukryj(self):
        ok = dict(BRAND, braki=["Krój strony niedostępny"], do_potwierdzenia={"plansza_koncowa": "tekst testu"},
                  ukryj=["#baner", "[class*=\"zd-baner\"]"])
        self.assertEqual(film.validate_brand(ok), [])
        for bad in ({"ukryj": ["a{display:block}"]}, {"ukryj": "x"}, {"braki": [""]},
                    {"do_potwierdzenia": {"inne": "x"}}):
            self.assertTrue(film.validate_brand(dict(BRAND, **bad)), bad)
        self.write("studio/marka.json", ok)
        self.write("studio/szablony/obj-b.json", OBJ)
        self.scenario({"szablon": "obj-b", "parametry": {"hak": "Hak posta"}})
        info = film.describe(self.post)
        self.assertEqual(info["outroCard"]["pending"], "tekst testu")
        self.assertTrue(any("tymczasowa" in w for w in info["warnings"]))
        # własne wezwanie posta: bez ostrzeżenia o tekście tymczasowym marki
        self.scenario({"szablon": "obj-b", "parametry": {"hak": "Hak posta"}, "plansza_koncowa": {"tytul": "Inne"}})
        self.assertFalse(any("tymczasowa" in w for w in film.describe(self.post)["warnings"]))

    def test_ukrywanie_elementow_w_pokazie(self):
        brand = dict(film.DEFAULT_BRAND, ukryj=[".fb-fab", "#baner"])
        self.assertEqual(film.hide_list(brand, {"ukryj": ["#baner", ".czat"]}), [".fb-fab", "#baner", ".czat"])
        js = film.hide_js([".fb-fab", "[class*=\"zd-baner\"]"])
        self.assertIn('"[class*=\\"zd-baner\\"]"', js)              # selektory jako JSON, nie wklejone w kod
        self.assertIn("display:none!important", js)
        self.assertEqual(film.validate_scenario({"url": "https://e.org", "kroki": [{"napis": "a"}], "ukryj": ["#a"]}),
                         [])
        self.assertTrue(film.validate_scenario({"url": "https://e.org", "kroki": [{"napis": "a"}], "ukryj": ["<b>"]}))

    def test_szablony_z_danymi_wlasciciela(self):
        tpl = dict(OBJ, parametry=dict(OBJ["parametry"], hak="[cytat klienta]"),
                   etykiety=dict(OBJ["etykiety"], hak="Cytat klienta"))
        self.write("studio/szablony/cytat.json", tpl)
        self.write("studio/szablony/obj-b.json", OBJ)
        items = {t["name"]: t for t in film.list_templates(self.studio)}
        self.assertEqual(items["cytat"]["needs"], [{"label": "Cytat klienta", "image": False}])
        self.assertEqual(items["obj-b"]["needs"], [])
        self.assertEqual(items["obj-b"]["kindHelp"], film.KIND_HELP["objasnienie"])


class Montaz(unittest.TestCase):
    def test_przejscie_jasne_ciemne_przesuniecie(self):
        self.assertEqual(film.transition("#f7fbfd", "#002b4f"), "slideup")
        self.assertEqual(film.transition("#fbf7f1", "#f4efe6"), "fade")
        self.assertEqual(film.transition(None, "#002b4f"), "fadeblack")
        self.assertFalse(film.far_bg("zly", "#000000"))

    def test_kadr_4x5_nagrania_strony(self):
        self.assertEqual(film.feed_crop(), "[0:v]crop=1080:1350:0:300[v]")
        graph = film.feed_crop((3.2, 20.5), "#fbf7f1")
        self.assertIn("between(t,3.200,20.500)", graph)
        self.assertIn("scale=758:1350", graph)                # cały kadr strony: pasek z logo i napis zostają
        self.assertIn("color=0xfbf7f1", graph)

    def test_ffprobe_tylko_pliki_lokalne_z_limitem(self):
        calls = []

        class R:
            stdout = "12.5\n"

        real = film.subprocess.run
        film.subprocess.run = lambda args, **kw: calls.append((args, kw)) or R()
        try:
            self.assertEqual(film._duration("/tmp/x.mp3"), 12.5)
        finally:
            film.subprocess.run = real
        args, kw = calls[0]
        self.assertIn("-protocol_whitelist", args)
        self.assertEqual(args[args.index("-f") + 1], "mp3")
        self.assertTrue(kw.get("timeout"))

    def test_napis_strony_prawie_nieprzezroczysty(self):
        self.assertGreaterEqual(film.PAGE_CAPTION_ALPHA, 0.95)


class Nagrywarka(Karta):
    def test_stary_zrzut_bledu_znika_na_starcie(self):
        self.write("studio/szablony/obj-b.json", OBJ)
        self.scenario({"szablon": "obj-b", "parametry": {"hak": "Hak posta"}})
        with open(os.path.join(self.post, film.ERROR_SHOT), "wb") as f:
            f.write(b"x")
        rec = film.Recorder(python="/bin/false", script=os.path.join(self.tmp, "zle.py"))
        rec.available = lambda kind="pokaz": True
        with open(rec.script, "w", encoding="utf-8") as f:
            f.write("import sys\nprint('montaż: ffmpeg', file=sys.stderr)\nsys.exit(1)\n")
        rec.interpreter = lambda kind: film.sys.executable
        old = film.threading.Thread
        film.threading.Thread = _Inline
        try:
            rec.start(self.post)
        finally:
            film.threading.Thread = old
        self.assertEqual(film.read_state(self.post)["state"], "error")
        self.assertFalse(os.path.exists(os.path.join(self.post, film.ERROR_SHOT)))   # inny błąd: bez starego zrzutu


class Serwer(Karta):
    def test_aac_to_aac(self):
        self.assertEqual(server.STUDIO_TYPES["muzyka"]["audio/aac"], "aac")

    def test_stary_zrzut_pola_usuwany(self):
        old = "zrzut-1-20261120-101010.png"
        self.write("posty/2026-11-25-test/" + old, png(400, 800))
        self.write("posty/2026-11-25-test/inny.png", png(400, 800))
        self.scenario({"szablon": "x", "parametry": {"zrzut_1": "zrzut-1-20261121-090000.png"}})
        server._drop_old_image(self.post, "zrzut_1", old, "zrzut-1-20261121-090000.png")
        self.assertFalse(os.path.exists(os.path.join(self.post, old)))
        server._drop_old_image(self.post, "zrzut_1", "inny.png", "zrzut-1-20261121-090000.png")
        self.assertTrue(os.path.exists(os.path.join(self.post, "inny.png")))        # nie plik panelu: zostaje
        self.write("posty/2026-11-25-test/" + old, png(400, 800))
        self.scenario({"szablon": "x", "parametry": {"zrzut_1": "n.png", "zrzut_2": old}})
        server._drop_old_image(self.post, "zrzut_1", old, "n.png")
        self.assertTrue(os.path.exists(os.path.join(self.post, old)))              # używany w innym polu

    def test_poprzednia_wersja_filmu(self):
        self.write("studio/szablony/obj-b.json", OBJ)
        self.scenario({"szablon": "obj-b", "parametry": {"hak": "Hak posta"}})
        self.write("posty/2026-11-25-test/film.mp4", b"x")
        self.assertIsNone(server.post_info(self.post)["filmPrev"])
        self.write("posty/2026-11-25-test/" + film.PREVIOUS, b"y")
        self.assertTrue(server.post_info(self.post)["filmPrev"])


class Panel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(PANEL, encoding="utf-8") as f:
            cls.src = f.read()

    def fn(self, name):
        i = self.src.index("function %s(" % name)
        return self.src[i:self.src.index("\n}\n", i) + 2]

    def test_nagraj_ponownie_tylko_gdy_przycisk_jest(self):
        who = self.fn("filmWho")
        for m in re.finditer(r"'[^']*„Nagraj (ponownie|film)”[^']*'", who):
            before = who[max(0, m.start() - 60):m.start()]
            self.assertTrue("can?" in before or "can?" in who[m.start() - 200:m.start()], m.group(0))
        self.assertIn("filmCanRec(fi,d)", self.fn("filmBox"))
        self.assertNotIn("scenariusz", who.split("\n", 1)[1].replace("scenario", ""))

    def test_bez_martwej_galezi_i_ze_skrotem_w_publikacji(self):
        top = self.fn("filmTop")
        self.assertNotIn("!full", top)
        self.assertIn("kindHelp", top)
        self.assertIn("filmTop(t,day,false,true)", self.fn("postBox"))
        self.assertNotIn("DR.more=true", self.src[self.src.index("qq('[data-filmgo]')"):][:200])

    def test_studio_braki_i_odnosnik(self):
        self.assertIn("Czego potrzebuję od Ciebie", self.src)
        self.assertIn("data-stugo", self.fn("filmBox"))
        self.assertIn("stuFont(b,'tytul')", self.fn("stuMock"))
        self.assertIn("wariant=poprzedni", self.fn("filmBox"))


if __name__ == "__main__":
    unittest.main()
