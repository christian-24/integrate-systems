"""Studio filmów, runda 5: błędne pole posta do poprawy w panelu (brak treści, limit, brak zrzutu), szablon sprawdzany
z wartościami przykładowymi, wgranie podkładu bez marka.json, podkład zapisany przy poście, rotacja szablonów A-B-A-B,
przyspieszenie czekania w pokazie zamiast cięcia, napisy w chwili akcji, łamanie liczb i wyróżnień, panel (Co poprawić
na wierzchu, pola [wpisz tekst], „Obejrzyj film”)."""
import json
import os
import re
import shutil
import tempfile
import unittest

from test_studio_r2 import BRAND, PNG, POKAZ, Karta, _Capture
from test_studio_r3 import OBJ, png
from wspolne import server

film = server.film
PANEL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "panel.html")
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class PoleDoPoprawy(Karta):
    def test_brak_wymaganej_tresci_to_pole_w_panelu(self):
        self.scenario({"szablon": "pokaz-a", "parametry": {}})
        info = film.describe(self.post)
        self.assertEqual(info["errorParam"], "mebel")
        self.assertEqual(info["editable"], ["params"])
        self.assertIn("mebel", [p["name"] for p in info["params"]])
        self.assertIn("uzupełnij pole", info["errorHint"])

    def test_limit_znakow_to_pole_z_wpisana_wartoscia(self):
        self.scenario({"szablon": "pokaz-a", "parametry": {"mebel": "x" * 25}})
        info = film.describe(self.post)
        self.assertEqual(info["errorParam"], "mebel")
        value = next(p["value"] for p in info["params"] if p["name"] == "mebel")
        self.assertEqual(value, "x" * 25)                       # w polu do poprawy wartość właściciela, nie przykład
        self.assertTrue(info["errorHint"].startswith("Popraw pole „Mebel"), info["errorHint"])

    def test_brak_zrzutu_to_pole_do_wgrania(self):
        tpl = {"tytul": "Zrzuty", "typ": "objasnienie", "plansza_startowa": False,
               "parametry": {"hak": "Hak", "zrzut": "zrzut.png", "tekst": "Tekst"}, "wymagane": ["zrzut"],
               "plansze": [{"tekst": "{{hak}}"}, {"tekst": "{{tekst}}", "obraz": "{{zrzut}}", "uklad": "zrzut"}]}
        self.write("studio/szablony/zrzuty.json", tpl)
        self.scenario({"szablon": "zrzuty", "parametry": {"zrzut": "moj-zrzut.png"}})
        info = film.describe(self.post)
        self.assertEqual(info["errorParam"], "zrzut")
        self.assertTrue(next(p for p in info["params"] if p["name"] == "zrzut").get("image"))
        self.assertIn("wgraj", info["errorHint"])
        self.write("posty/2026-11-25-test/moj-zrzut.png", png(400, 800))
        self.assertEqual(film.describe(self.post)["error"], "")

    def test_komunikat_obok_szablonu_wymienia_wszystkie_pola(self):
        with self.assertRaises(ValueError) as e:
            film.expand({"szablon": "pokaz-a", "typ": "objasnienie", "parametry": {"mebel": "Sofa"}}, self.studio)
        for key in ("muzyka", "opis", "komentarz"):
            self.assertIn(key, str(e.exception))
        self.assertNotEqual(film.error_hint(str(e.exception)), "Błąd w scenariuszu filmu.")


class SzablonZPrzykladem(Karta):
    def test_przyklad_ponad_limit_to_blad_szablonu(self):
        self.write("studio/szablony/zly.json", dict(POKAZ, limity={"hak": {"max": 5}}))
        item = next(t for t in film.list_templates(self.studio) if t["name"] == "zly")
        self.assertIn("przykład parametru „hak”", item["error"])

    def test_nieznany_klucz_planszy_widoczny_w_studiu(self):
        bad = dict(OBJ, plansze=[{"tekst": "{{hak}}", "zle": 1}])
        self.write("studio/szablony/obj-zly.json", bad)
        item = next(t for t in film.list_templates(self.studio) if t["name"] == "obj-zly")
        self.assertIn("nieznany klucz „zle”", item["error"])

    def test_parametr_bez_przykladu_nie_jest_bledem_szablonu(self):
        tpl = {"tytul": "Lista", "typ": "objasnienie", "plansza_startowa": False, "parametry": {"hak": "Hak"},
               "wymagane": ["punkty", "czas"],
               "plansze": [{"tekst": "{{hak}}"}, {"tekst": "{{punkty}}", "uklad": "lista", "czas": "{{czas}}"}]}
        self.write("studio/szablony/lista.json", tpl)
        item = next(t for t in film.list_templates(self.studio) if t["name"] == "lista")
        self.assertEqual(item["error"], "")
        self.assertTrue(item["needsData"] is False)

    def test_pole_czasu_bez_przykladu_przyjmuje_liczbe_z_formularza(self):
        tpl = {"tytul": "Czas", "typ": "objasnienie", "plansza_startowa": False, "parametry": {"hak": "Hak"},
               "plansze": [{"tekst": "{{hak}}", "czas": "{{c}}"}]}
        self.assertEqual(film.coerce_params(tpl, {"c": "5"}), {"c": 5})
        self.write("studio/szablony/czas.json", tpl)
        self.scenario({"szablon": "czas", "parametry": {"c": "50"}})
        info = film.describe(self.post)
        self.assertEqual(info["errorParam"], "c")             # winne pole posta, nie „błąd w szablonie”

    def test_prawdziwe_szablony_bez_bledow_i_bez_zmyslonych_danych(self):
        for pid in ("company-audits", "generator-opisow-mebli", "naulikapp"):
            studio = os.path.join(REPO, "szkice", pid, "studio")
            if not os.path.isdir(studio):
                self.skipTest("brak kart")
            for t in film.list_templates(studio):
                self.assertEqual(t["error"], "", (pid, t["name"]))
                for label in t["labels"].values():
                    self.assertNotIn("gwiazd", label, (pid, t["name"]))
                    self.assertNotIn("średnik", label, (pid, t["name"]))
        tpl = film.load_template(os.path.join(REPO, "szkice", "generator-opisow-mebli", "studio"), "opinia-klienta")
        self.assertTrue(tpl["parametry"]["cytat"].startswith("["))       # przykład jawnie zastępczy
        brand = film.load_brand(os.path.join(REPO, "szkice", "generator-opisow-mebli", "studio"))[0]
        for name in ("opinia-klienta", "lista-kontrolna"):
            tpl = film.load_template(os.path.join(REPO, "szkice", "generator-opisow-mebli", "studio"), name)
            last = film._plain(tpl["plansze"][-1]["tekst"])
            last = film.fill(last, tpl["parametry"])
            self.assertNotIn(film._plain(brand["plansza_koncowa"]["tytul"]), film._plain(last), name)


class WgranieBezMarki(unittest.TestCase):
    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp(prefix="studio-r5-"))
        with open(os.path.join(self.tmp, "KARTA.md"), "w", encoding="utf-8") as f:
            f.write("# Karta\n")
        self.real = server.load_projects
        server.load_projects = lambda resolve=False: ({}, {"p": self.tmp})

    def tearDown(self):
        server.load_projects = self.real
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_podklad_bez_marki_nie_psuje_filmow(self):
        mp3 = b"ID3" + b"\x00" * 64
        code, err, data = server.studio_add_file("p", "muzyka", "audio/mpeg", mp3, "YouTube Audio Library")
        self.assertEqual((code, err), (200, ""))
        studio = os.path.join(self.tmp, "studio")
        self.assertEqual(film.load_brand(studio)[1], [])                        # marka poprawna, kolory domyślne
        code, err, data2 = server.studio_add_file("p", "muzyka", "audio/mpeg", mp3, "Pixabay Music")
        self.assertEqual(code, 200)
        self.assertNotEqual(data["name"], data2["name"])                          # ta sama sekunda: dwa pliki
        self.assertEqual(server.studio_music_file("p", data["name"]), os.path.join(studio, data["name"]))
        self.assertIsNone(server.studio_music_file("p", "../marka.json"))
        brand = film.load_brand(studio)[0]
        self.assertEqual(film.music_list(brand["muzyka"]), [data["name"], data2["name"]])
        self.assertEqual(server.studio_remove_music({"project": "p", "plik": data["name"]})[0], 200)
        self.assertEqual(film.music_list(film.load_brand(studio)[0]["muzyka"]), [data2["name"]])
        self.assertTrue(os.path.isfile(os.path.join(studio, data["name"])))       # plik zostaje (licencja w zrodlo)

    def test_logo_w_rogu(self):
        code, _err, _data = server.studio_add_file("p", "logo", "image/png", png(64, 64), "logo własne", corner=True)
        self.assertEqual(code, 200)
        studio = os.path.join(self.tmp, "studio")
        self.assertTrue(film.load_brand(studio)[0]["logo_w_rogu"])
        self.assertEqual(server.studio_settings({"project": "p", "logo_w_rogu": False})[0], 200)
        self.assertFalse(film.load_brand(studio)[0]["logo_w_rogu"])
        self.assertEqual(server.studio_settings({"project": "p", "logo_w_rogu": "tak"})[0], 400)

    def test_limit_podkladow_przed_zapisem_pliku(self):
        studio = os.path.join(self.tmp, "studio")
        os.makedirs(studio)
        with open(os.path.join(studio, "marka.json"), "w", encoding="utf-8") as f:
            json.dump(dict(BRAND, muzyka=["m%d.mp3" % i for i in range(film.MUSIC_MAX)]), f)
        before = set(os.listdir(studio))
        code, err, _ = server.studio_add_file("p", "muzyka", "audio/mpeg", b"ID3" + b"\x00" * 64, "licencja x")
        self.assertEqual(code, 409)
        self.assertIn("Usuń z listy", err)
        self.assertEqual(set(os.listdir(studio)), before)                          # bez osieroconego pliku


class Podklad(Karta):
    def test_podklad_zapisany_przy_poscie(self):
        brand = {"muzyka": ["a.mp3", "b.mp3"]}
        base = os.path.join(self.tmp, "posty")
        p = os.path.join(base, "2026-11-27-c")
        os.makedirs(p)
        with open(os.path.join(p, film.SCENARIO), "w", encoding="utf-8") as f:
            f.write("{}")
        first = film.music_name(p, brand, {})
        film.pin_music(p, first)
        os.makedirs(os.path.join(base, "2026-11-21-wczesniej"))                  # nowy wcześniejszy post
        with open(os.path.join(base, "2026-11-21-wczesniej", film.SCENARIO), "w", encoding="utf-8") as f:
            f.write("{}")
        self.assertEqual(film.music_name(p, brand, {}), first)                     # bez przesunięcia podkładów
        self.assertEqual(film.music_name(p, {"muzyka": ["c.mp3", "d.mp3"]}, {}) in ("c.mp3", "d.mp3"), True)

    def test_wybor_podkladu_dla_filmu(self):
        self.write("studio/marka.json", dict(BRAND, muzyka=["a.mp3", "b.mp3"]))
        for n in ("a.mp3", "b.mp3"):
            self.write("studio/" + n, b"ID3" + b"\x00" * 64)
        self.scenario({"szablon": "pokaz-a", "parametry": {"mebel": "Sofa"}})
        info = film.apply_changes(self.post, music="b.mp3")
        self.assertEqual((info["musicName"], info["musicChoice"]), ("b.mp3", "b.mp3"))
        self.assertEqual(film.apply_changes(self.post, music=False)["musicChoice"], "off")
        self.assertEqual(film.apply_changes(self.post, music="")["musicChoice"], "")
        with self.assertRaises(ValueError):
            film.apply_changes(self.post, music="../marka.json")


class Rotacja(Karta):
    def test_a_b_a_b_ostrzega(self):
        self.write("studio/szablony/obj-b.json", OBJ)
        base = os.path.join(self.tmp, "posty")
        for day, name in (("2026-11-17", "pokaz-a"), ("2026-11-19", "obj-b"), ("2026-11-21", "pokaz-a"),
                          ("2026-11-23", "obj-b")):
            os.makedirs(os.path.join(base, day + "-x"))
            with open(os.path.join(base, day + "-x", film.SCENARIO), "w", encoding="utf-8") as f:
                json.dump({"szablon": name, "parametry": {"mebel": "Sofa %s" % day}}, f)
        self.scenario({"szablon": "pokaz-a", "parametry": {"mebel": "Inna"}})
        warns = film.describe(self.post)["warnings"]
        self.assertTrue([w for w in warns if "2 z 4 ostatnich" in w], warns)


class Pokaz(unittest.TestCase):
    def test_czekanie_przyspieszone_nie_wyciete(self):
        cuts = film.cuts_for([(2.0, 12.0)])
        a, b = cuts[0]
        self.assertAlmostEqual(film.shift_time(20.0, cuts), 20.0 - (b - a) + film.FAST_LEN)
        self.assertGreater(film.speed_of(a, b), 4)
        self.assertAlmostEqual(film.shift_time(a, cuts), a)

    def test_filtry_renderu(self):
        calls = []
        saved = (film._encode, film._duration)
        film._encode = lambda args, out, final=False, seconds=None: calls.append(args) or out
        film._duration = lambda path: 0.0
        try:
            tmp = tempfile.mkdtemp()
            film.render("/tmp/x.webm", os.path.join(tmp, "o.mp4"), [(1.0, "Napis")], 20.0, tmp,
                        waits=[(2.0, 12.0)], lead_hint=3.0)
        finally:
            film._encode, film._duration = saved
            shutil.rmtree(tmp, ignore_errors=True)
        args = calls[0]
        self.assertEqual(args[args.index("-ss") + 1], "2.80")                      # bez ffprobe: czas otwarcia strony
        vf = args[args.index("-vf") + 1]
        self.assertIn("setpts='(T-(clip(T-", vf)                                   # przyspieszenie, nie select
        self.assertNotIn("select=", vf)
        self.assertIn("-protocol_whitelist", args)
        caps = re.findall(r"enable='between\(t,([0-9.]+),", vf)
        self.assertIn("%.2f" % (1.0 + film.LEAD_PAD), caps)                        # napis w chwili akcji

    def test_hak_pokazu_w_limicie(self):
        sec = film.brand_time({"tytul": "x" * film.HOOK_CHARS}, "plansza_startowa", hook=True)[0]
        self.assertLessEqual(sec - film.XFADE, film.HOOK_MAX)                     # strona widoczna przed 3,5 s


class Montaz(Karta):
    def setUp(self):
        super().setUp()
        self.cap = _Capture()
        self.saved = film._clip
        film._clip = self.cap

    def tearDown(self):
        film._clip = self.saved
        super().tearDown()

    def test_ostatnia_plansza_gasnie_cala_przed_plansza_koncowa(self):
        work = tempfile.mkdtemp(dir=self.tmp)
        brand = film.load_brand(self.studio)[0]
        film.explainer_clips([{"tekst": "A"}, {"tekst": "B"}], brand, work, film._Texts(work), self.post,
                             fade_last=True)
        self.assertEqual(self.cap.calls[0]["fade_from"], film.BAR_Y + 14)
        self.assertIsNone(self.cap.calls[1]["fade_from"])                        # nagłówek i pasek też gasną

    def test_cudzyslow_gorny_po_przejsciu(self):
        work = tempfile.mkdtemp(dir=self.tmp)
        brand = film.load_brand(self.studio)[0]
        film.explainer_clips([{"tekst": "A"}, {"tekst": "Cytat", "podpis": "Autor", "uklad": "cytat"}], brand, work,
                             film._Texts(work), self.post)
        quote = [d for d in self.cap.calls[1]["draws"] if "fontsize=260" in d][0]
        path = re.search(r"textfile=([^:]+)", quote).group(1).replace("\\", "")
        with open(path, encoding="utf-8") as f:
            self.assertEqual(f.read(), "“")
        self.assertIn("clip((t-%.2f)" % film.XFADE, quote)

    def test_koniec_wchodzi_po_przejsciu(self):
        work = tempfile.mkdtemp(dir=self.tmp)
        film.brand_card(film.load_brand(self.studio)[0], BRAND["plansza_koncowa"], "plansza_koncowa", work,
                        film._Texts(work), "k.mp4", delay=0.25)
        first = [d for d in self.cap.calls[0]["draws"] if d.startswith("drawtext")][0]
        self.assertIn("clip((t-0.30)", first)


class Lamanie(unittest.TestCase):
    def test_liczba_z_nastepnym_slowem(self):
        toks = film._tokens("Wpis do dziennika w *3 dotknięciach*")
        self.assertIn("w *3 dotknięciach*", toks)

    def test_bez_przerwy_w_wyroznieniu(self):
        class F:                                   # stała szerokość znaku: wynik niezależny od czcionek komputera
            def width(self, text):
                return len(text.replace("*", "").replace(film.NBSP, " ")) * 10
        lines = film.wrap("Każdy opis ma *wymiary i materiał* w treści", F(), 200)
        self.assertEqual(len(lines), 3, lines)
        for ln in lines:
            self.assertEqual(ln.count("*") % 2, 0, lines)


class Panel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(PANEL, encoding="utf-8") as f:
            cls.html = f.read()

    def test_obejrzyj_film_to_zadanie_filmu(self):
        self.assertIn("const FILM_RE=/^(nagra[jć]|obejrzyj)\\s+film/i", self.html)
        self.assertTrue(server.FILM_TASK.match("Obejrzyj film A nagrany przez panel"))
        self.assertTrue(server.agents.FILM_TASK[1] == "Obejrzyj film")

    def test_co_poprawic_zawsze_na_wierzchu(self):
        self.assertIn("const full=!!fday&&!shown.post;", self.html)

    def test_pola_do_uzupelnienia_i_lista_szablonow(self):
        body = self.html[self.html.index("function fixBox("):]
        body = body[:body.index("\nfunction ")]
        self.assertIn("FIX_GAP", body)
        self.assertIn("data-fixtpl", body)                                       # szablony w liście, nie w przyciskach
        self.assertIn("needsData", body)
        self.assertNotIn("'Zrób z filmu objaśnienie na planszach'", body)

    def test_bez_tekstu_zastepczego_w_miniaturach(self):
        self.assertNotIn("Tekst planszy z *wyróżnieniem*", self.html)

    def test_bez_zdublowanych_funkcji(self):
        names = re.findall(r"\bfunction\s+([A-Za-z0-9_]+)\s*\(", self.html)
        self.assertEqual(len(names), len(set(names)))


if __name__ == "__main__":
    unittest.main()
