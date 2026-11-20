"""Studio filmów, runda 3: błąd wartości przypisany do parametru (nie do szablonu), liczby z formularza panelu,
mapa pól szablonu dla panelu, limity w formularzu (max, opcje, cyfry), znaki sterujące, obrazy plansz jak logo,
pokaz tylko ze stronami z marki, zapis z panelu bez nadpisania zmiany agenta, ostrzeżenia o powtórkach i długości,
czas haka, dzielenie słów po polsku, przejścia bez podwójnej ekspozycji, studio w panelu (posty z błędem)."""
import json
import os
import shutil
import unittest

from test_studio_r2 import BRAND, PNG, Karta, _Capture
from wspolne import Baza, agents, server

film = server.film
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SZKICE = os.path.join(REPO, "szkice")
OBJ = {"tytul": "Objaśnienie", "typ": "objasnienie", "plansza_startowa": False,
       "parametry": {"hak": "Hak *przykładowy*", "a": "Pierwszy", "b": "Drugi", "c": 3,
                     "p1": "Plansza jeden", "p2": "Plansza dwa", "p3": "Plansza trzy"},
       "wymagane": ["hak"], "limity": {"hak": {"max": 60}},
       "etykiety": {"hak": "Plansza 1: hak", "a": "Słowo A", "b": "Słowo B"},
       "plansze": [{"tekst": "{{hak}}"}, {"tekst": "{{a}} i {{b}}", "podpis": "Stały podpis", "czas": "{{c}}"},
                   {"tekst": "{{p1}}"}, {"tekst": "{{p2}}"}, {"tekst": "{{p3}}"}]}


def png(w, h):
    return PNG[:16] + w.to_bytes(4, "big") + h.to_bytes(4, "big") + PNG[24:]


class Parametry(Karta):
    def setUp(self):
        super().setUp()
        self.write("studio/szablony/obj-b.json", OBJ)

    def test_blad_wartosci_przypisany_do_parametru(self):
        self.scenario({"szablon": "obj-b", "parametry": {"hak": "Hak *bez pary"}})
        info = film.describe(self.post)
        self.assertTrue(info["error"].startswith("parametr „hak”, pole „Plansza 1: hak”: "), info["error"])
        self.assertNotIn("szablon obj-b", info["error"])
        self.assertTrue(info["errorHint"].startswith("Popraw pole „Plansza 1: hak”"), info["errorHint"])
        self.assertEqual(info["errorParam"], "hak")                         # panel pokazuje pole do poprawy
        self.assertEqual(info["editable"], ["params"])
        self.assertIn("hak", [p["name"] for p in info["params"]])
        # błąd w samym szablonie (wartości przykładowe też go dają): zgłoszony jako błąd szablonu
        self.write("studio/szablony/obj-b.json", dict(OBJ, parametry=dict(OBJ["parametry"], p1="x" * 95)))
        self.scenario({"szablon": "obj-b", "parametry": {"hak": "Hak"}})
        self.assertTrue(film.describe(self.post)["error"].startswith("szablon obj-b: "))

    def test_liczba_z_formularza_zostaje_liczba(self):
        self.scenario({"szablon": "obj-b", "parametry": {"hak": "Hak"}})
        info = film.apply_changes(self.post, params={"c": "5"})
        self.assertEqual(self.read_scenario()["parametry"]["c"], 5)
        self.assertEqual(info["slides"][1]["seconds"], 5.0)
        self.assertEqual(film.coerce_params(OBJ, {"c": "4,5", "a": "7"}), {"c": 4.5, "a": "7"})   # tekst zostaje
        with self.assertRaises(ValueError):
            film.apply_changes(self.post, params={"c": "dużo"})

    def test_mapa_pol_dla_panelu(self):
        self.scenario({"szablon": "obj-b", "parametry": {"hak": "Hak"}})
        info = film.describe(self.post)
        slides = info["fields"]["slides"]
        self.assertEqual(slides[0], {"params": ["hak"], "text": "hak", "caption": ""})
        self.assertEqual(slides[1], {"params": ["a", "b"], "text": "", "caption": ""})   # dwa parametry w jednym tekście
        self.assertIn("a", info["fields"]["markup"])
        by = {p["name"]: p for p in info["params"]}
        self.assertEqual((by["a"]["group"], by["hak"]["max"], by["a"]["max"]), ("plansze", 60, film.TEXT_MAX))
        self.assertTrue(by["hak"]["required"])

    def test_limity_w_formularzu(self):
        self.scenario({"szablon": "pokaz-a", "parametry": {"mebel": "Sofa"}})
        info = film.describe(self.post)
        by = {p["name"]: p for p in info["params"]}
        self.assertEqual(by["kat"]["options"], ["komoda", "stół"])
        self.assertEqual((by["mebel"]["max"], by["mebel"]["group"], by["kat"]["group"]), (20, "formularz", "formularz"))
        self.assertEqual(info["fields"]["form"], ["mebel", "kat"])
        self.assertEqual(info["fields"]["intro"], {"params": ["hak"], "fields": {"tytul": "hak"}})

    def test_cyfry_i_opcje(self):
        tpl = dict(POKAZ_W, limity={"szer": {"max": 4, "cyfry": True}, "kat": {"opcje": ["komoda"]}})
        self.write("studio/szablony/pokaz-w.json", tpl)
        with self.assertRaisesRegex(ValueError, "same cyfry"):
            film.expand({"szablon": "pokaz-w", "parametry": {"szer": "8O"}}, self.studio)
        with self.assertRaisesRegex(ValueError, "jedna z wartości"):
            film.expand({"szablon": "pokaz-w", "parametry": {"kat": "szafa"}}, self.studio)
        film.expand({"szablon": "pokaz-w", "parametry": {"szer": "120"}}, self.studio)
        self.write("studio/szablony/pokaz-w.json", dict(tpl, limity={"szer": {"cyfry": "tak"}}))
        with self.assertRaises(ValueError):
            film.load_template(self.studio, "pokaz-w")

    def test_znaki_sterujace_odrzucone(self):
        for value in ("Sofa\n", "So\rfa", "Sofa\x00", "a\tb"):
            with self.assertRaisesRegex(ValueError, "znaków sterujących"):
                film.expand({"szablon": "pokaz-a", "parametry": {"mebel": value}}, self.studio)
        self.assertTrue(film.validate_scenario({"typ": "objasnienie", "plansze": [{"tekst": "A\nB"}]}))
        self.assertIn("nowy wiersz", film.error_hint("tekst „A B”: bez znaków sterujących (nowy wiersz, tabulator)"))


POKAZ_W = {"typ": "pokaz", "parametry": {"szer": "80", "kat": "komoda"}, "url": "https://example.org/g",
           "kroki": [{"wpisz": ["#w", "{{szer}}"]}, {"wybierz": ["#k", "{{kat}}"]}]}


class Bezpieczenstwo(Karta):
    def test_obraz_planszy_sprawdzany_jak_logo(self):
        os.makedirs(os.path.join(self.studio, "obrazy"))
        self.write("studio/obrazy/a.png", "#EXTM3U\nfile:///etc/passwd\n")
        self.scenario({"typ": "objasnienie", "plansze": [{"tekst": "A", "obraz": "a.png"}]})
        err = film.describe(self.post)["error"]
        self.assertIn("błąd obrazu a.png", err)
        self.assertIn("nie zgadza się", err)
        self.write("studio/obrazy/a.png", png(40000, 40000))                # mały plik, ogromne wymiary
        self.assertIn("obraz do", film.describe(self.post)["error"])
        self.assertIsNone(film.image_path(self.post, "a.png"))
        self.write("studio/obrazy/a.png", png(1080, 900))
        self.assertEqual(film.describe(self.post)["error"], "")
        jpg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00" + \
            b"\xff\xc0\x00\x11\x08\x03\x84\x04\x38\x03\x01\x22\x00\x02\x11\x01\x03\x11\x01"
        self.write("studio/obrazy/b.jpg", jpg)
        self.assertEqual(film._image_size(os.path.join(self.studio, "obrazy", "b.jpg"), "jpg"), (1080, 900))

    def test_pokaz_bez_stron_w_marce_sie_nie_nagra(self):
        self.write("studio/marka.json", dict(BRAND, strony=[]))
        self.scenario({"szablon": "pokaz-a", "parametry": {"mebel": "Sofa"}})
        info = film.describe(self.post)
        self.assertIn("pole strony", info["error"])
        self.assertEqual(info["errorHint"], "Adres strony w filmie jest niedozwolony.")
        self.scenario({"typ": "objasnienie", "plansze": [{"tekst": "A"}]})      # objaśnienie: bez stron
        self.assertEqual(film.describe(self.post)["error"], "")

    def test_zapis_z_panelu_nie_nadpisuje_zmiany_agenta(self):
        self.scenario({"szablon": "pokaz-a", "parametry": {"mebel": "Komoda"}})
        real = film.prepare_raw

        def agent_writes(raw, folder):
            out = real(raw, folder)
            with open(os.path.join(folder, film.SCENARIO), "w", encoding="utf-8") as f:
                json.dump({"szablon": "pokaz-a", "parametry": {"mebel": "Od agenta"}}, f)
            os.utime(os.path.join(folder, film.SCENARIO), ns=(1, 1))      # inny mtime niż przy odczycie
            return out
        film.prepare_raw = agent_writes
        try:
            with self.assertRaises(film.ScenarioChanged):
                film.apply_changes(self.post, params={"mebel": "Sofa"})
        finally:
            film.prepare_raw = real
        self.assertEqual(self.read_scenario()["parametry"]["mebel"], "Od agenta")
        self.assertEqual([n for n in os.listdir(self.post) if n.endswith(".tmp")], [])   # bez plików tymczasowych


class Ostrzezenia(Karta):
    def setUp(self):
        super().setUp()
        self.write("studio/szablony/obj-b.json", OBJ)

    def test_wiekszosc_plansz_z_przykladu(self):
        self.scenario({"szablon": "obj-b", "parametry": {"hak": "Mój hak"}})
        w = film.describe(self.post)["warnings"]
        self.assertTrue([x for x in w if x.startswith("4 z 5 plansz ma przykładowy tekst")], w)
        self.scenario({"szablon": "obj-b", "parametry": {"hak": "Mój hak", "a": "X", "p1": "Y", "p2": "Z"}})
        self.assertFalse([x for x in film.describe(self.post)["warnings"] if "przykładowy tekst" in x])

    def test_powtorka_wzgledem_poprzednich_postow(self):
        prev = os.path.join(self.tmp, "posty", "2026-11-20-wczesniej")
        os.makedirs(prev)
        with open(os.path.join(prev, film.SCENARIO), "w", encoding="utf-8") as f:
            json.dump({"szablon": "pokaz-a", "parametry": {"mebel": "Sofa"}}, f)
        self.scenario({"szablon": "pokaz-a", "parametry": {"mebel": "sofa "}})
        w = film.describe(self.post)["warnings"]
        self.assertTrue([x for x in w if x.startswith("Poprzedni film (20.11) ma ten sam szablon")], w)
        self.assertTrue([x for x in w if "taki sam jak w filmie z 20.11" in x], w)
        self.scenario({"szablon": "pokaz-a", "parametry": {"mebel": "Szafa"}})
        w = film.describe(self.post)["warnings"]
        self.assertFalse([x for x in w if "taki sam" in x])
        later = os.path.join(self.tmp, "posty", "2026-11-30-pozniej")     # późniejsze posty się nie liczą
        os.makedirs(later)
        with open(os.path.join(later, film.SCENARIO), "w", encoding="utf-8") as f:
            json.dump({"szablon": "pokaz-a", "parametry": {"mebel": "Szafa"}}, f)
        self.assertFalse([x for x in film.describe(self.post)["warnings"] if "taki sam" in x])

    def test_dlugie_objasnienie_i_cisza(self):
        self.scenario({"typ": "objasnienie", "plansze": [{"tekst": "x" * 80, "podpis": "y" * 60}] * 4})
        info = film.describe(self.post)
        self.assertGreater(info["seconds"], film.OBJ_MAX)
        self.assertTrue([x for x in info["warnings"] if x.startswith("Objaśnienie potrwa ok.")])
        self.assertTrue([x for x in info["warnings"] if x.startswith("Film bez muzyki")])   # widoczne, nie szare

    def test_brak_pil_nie_trafia_do_opisu_filmu(self):
        saved = film._PILFont
        film._PILFont = None
        try:
            self.scenario({"typ": "objasnienie", "plansze": [{"tekst": "*Słowo* w kolorze"}]})
            self.assertFalse([x for x in film.describe(self.post)["warnings"] if "PIL" in x or "pillow" in x])
        finally:
            film._PILFont = saved

    def test_hak_krotki_i_ostrzezenie_przy_dlugim(self):
        short = film.card_time({"tekst": "3 błędy w opisie mebla na Allegro"}, hook=True)[0]
        self.assertLessEqual(short, 3.0)                                    # hak bez podpisu: ok. 3 s
        self.assertLess(short, film.card_time({"tekst": "3 błędy w opisie mebla na Allegro"})[0] + 0.01)
        self.scenario({"typ": "objasnienie", "plansze": [{"tekst": "x" * 50, "podpis": "y" * 40}, {"tekst": "A"}],
                       "plansza_startowa": False})                         # pierwsza plansza to hak
        info = film.describe(self.post)
        self.assertTrue(info["slides"][0]["hook"])
        self.assertTrue([x for x in info["warnings"] if x.startswith("Pierwsza plansza (hak) trwa")])

    def test_napisy_pokazu_maja_czas_czytania(self):
        sc = {"kroki": [{"napis": "Profil Allegro i „Generuj opis”", "kliknij": "#a"}, {"kliknij": "#b"},
                        {"napis": "Dalej", "pauza": 3}]}
        total, paused = film._pokaz_timeline(sc)
        self.assertEqual(paused, 1)                                         # pierwszy napis wydłużony
        self.assertGreaterEqual(total, 0.8 + film.caption_need("Profil Allegro i „Generuj opis”") + 3)


class Montaz(Karta):
    def setUp(self):
        super().setUp()
        self.cap = _Capture()
        self.saved = film._clip
        film._clip = self.cap

    def tearDown(self):
        film._clip = self.saved
        super().tearDown()

    def brand(self):
        return film.load_brand(self.studio)[0]

    def test_tresc_gasnie_przed_przejsciem_ostatni_klip_bez_tego(self):
        work = os.path.join(self.tmp, "w")
        os.makedirs(work)
        texts = film._Texts(work)
        film.explainer_clips([{"tekst": "A"}, {"tekst": "B"}], self.brand(), work, texts, self.post)
        film.brand_card(self.brand(), BRAND["plansza_koncowa"], "plansza_koncowa", work, texts, "k.mp4")
        film.brand_card(self.brand(), BRAND["plansza_startowa"], "plansza_startowa", work, texts, "s.mp4", first=True)
        self.assertEqual([c["fade_out"] for c in self.cap.calls], [True, True, False, True])
        self.assertEqual(film.transition("#fbf7f1", "#2b1d12"), "slideup")  # do planszy końcowej bez czerni i szarości

    def test_naglowek_i_pasek_pod_nakladka_reels(self):
        work = os.path.join(self.tmp, "w")
        os.makedirs(work)
        film.explainer_clips([{"tekst": "A"}, {"tekst": "B"}], self.brand(), work, film._Texts(work), self.post)
        c = self.cap.calls[0]
        self.assertGreaterEqual(c["bar"][1], 0.18 * film.SIZE[1])
        heads = [d for d in c["draws"] if d.startswith("drawtext") and "-max_glyph_a'" in d and "fontsize=40" in d]
        self.assertTrue(heads)
        self.assertTrue(all(":y='%d-max_glyph_a'" % film.HEAD_Y in d for d in heads))
        self.assertGreaterEqual(film.HEAD_Y, 0.18 * film.SIZE[1])

    def test_pytanie_na_srodku_i_podpis_haka_wczesniej(self):
        work = os.path.join(self.tmp, "w")
        os.makedirs(work)
        film.explainer_clips([{"tekst": "Ile razy dziennie przepisujesz?"}, {"tekst": "Tekst", "podpis": "Pod"}],
                             self.brand(), work, film._Texts(work), self.post, first=True)
        one, two = self.cap.calls
        self.assertTrue([d for d in one["draws"] if d.startswith("drawbox=x=(iw-120)/2")])   # kreska na środku
        self.assertFalse([d for d in two["draws"] if d.startswith("drawbox=x=(iw-120)/2")])

    def test_podtytul_planszy_startowej_duzy_w_kolorze_tekstu(self):
        work = os.path.join(self.tmp, "w")
        os.makedirs(work)
        film.brand_card(self.brand(), {"tytul": "Marka", "podtytul": "Dziennik pokładowy w telefonie"},
                        "plansza_startowa", work, film._Texts(work), "s.mp4")
        draws = self.cap.calls[0]["draws"]
        texts = [d for d in draws if d.startswith("drawtext")]
        sizes = [int(d.split("fontsize=")[1].split(":")[0]) for d in texts]
        self.assertGreaterEqual(min(sizes), 52)
        fg = film._col(BRAND["kolory"]["tlo"])
        self.assertTrue(all(d.split("fontcolor=")[1].split(":")[0] == fg for d in texts))
        self.assertTrue([d for d in draws if d.startswith("drawbox=x=(iw-120)/2")])         # akcent na kresce

    def test_pudelko_podpisu_wchodzi_plynnie(self):
        out = film._box_fade("90", 100, 200, 80, "#000000", 0.9, 1.0, 4.0)
        self.assertGreaterEqual(len(out), 10)


class Dzielenie(unittest.TestCase):
    def test_bez_czesci_od_n_s_c_z_i_bez_rozdzielania_dwuznakow(self):
        font = film.Font(film.FONT, 92)
        for word in ("Konstantynopolitańczykowianeczka", "Przeszczepienieszczęśliwców", "Najważniejszychrzeczywistości"):
            for maxw in (500, 600, 700):
                parts = film._split_long(word, font, maxw)
                self.assertEqual("".join(p.rstrip("-") for p in parts), word)
                for a, b in zip(parts, parts[1:]):
                    self.assertNotIn(b[0], "ńśćź", parts)
                    self.assertNotIn((a.rstrip("-")[-1] + b[0]).lower(), film.DIGRAPHS, parts)


class StudioRealne(unittest.TestCase):
    def test_szablony_maja_opis_dla_wlasciciela_i_limit_haka(self):
        for pid in ("generator-opisow-mebli", "company-audits", "naulikapp"):
            for t in film.list_templates(os.path.join(SZKICE, pid, "studio")):
                self.assertEqual(t["error"], "", (pid, t["name"]))
                self.assertTrue(t["forOwner"], (pid, t["name"]))
                if t["kind"] == "objasnienie":
                    tpl = film.load_template(os.path.join(SZKICE, pid, "studio"), t["name"])
                    hook = film._uses(tpl["plansze"][0]["tekst"])[0][0]
                    # limit haka = tyle znaków, ile da się przeczytać w HOOK_MAX (bez ostrzeżenia „hak za długi”)
                    self.assertEqual(tpl["limity"][hook]["max"], film.HOOK_CHARS, (pid, t["name"]))
                    self.assertLessEqual(len(str(tpl["parametry"].get(hook, ""))), film.HOOK_CHARS)
                    self.assertNotIn("podpis", tpl["plansze"][0], (pid, t["name"]))   # hak bez podpisu: ok. 3 s
                    self.assertGreater(len(tpl["wymagane"]), 1, (pid, t["name"]))   # treść posta, nie przykład

    def test_kategoria_z_listy_generatora_i_wymiary_cyfry(self):
        studio = os.path.join(SZKICE, "generator-opisow-mebli", "studio")
        for name in ("pokaz-generatora", "pokaz-problem-de"):
            lim = film.load_template(studio, name)["limity"]
            self.assertIn("komoda", lim["kategoria"]["opcje"])
            self.assertTrue(all(lim[k].get("cyfry") for k in ("szerokosc", "wysokosc", "glebokosc")))


class Panel(Baza):
    def setUp(self):
        super().setUp()
        self.studio = os.path.join(self.folder, "studio")
        os.makedirs(os.path.join(self.studio, "szablony"))
        for name, data in (("szablony/obj-b.json", OBJ), ("marka.json", BRAND)):
            with open(os.path.join(self.studio, name), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        self.day = server.datetime.date.today() + server.datetime.timedelta(days=2)
        self.post = os.path.join(self.folder, "posty", "%s-film" % self.day.isoformat())
        os.makedirs(self.post)
        with open(os.path.join(self.post, film.SCENARIO), "w", encoding="utf-8") as f:
            json.dump({"szablon": "obj-b", "parametry": {"hak": "Hak"}}, f)

    def test_zmiana_liczby_przez_panel(self):
        server.get_recorder().start = lambda folder, title="": (409, "zajęte", {})
        code, _msg, *rest = server.film_change({"project": "projekt-testowy", "date": self.day.isoformat(),
                                                "params": {"c": "6"}})
        self.assertEqual(code, 200)
        with open(os.path.join(self.post, film.SCENARIO), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["parametry"]["c"], 6)

    def test_konflikt_zapisu_to_409(self):
        real = film.apply_changes

        def changed(*a, **k):
            raise film.ScenarioChanged("x")
        film.apply_changes = changed
        try:
            code, msg = server.film_change({"project": "projekt-testowy", "date": self.day.isoformat(),
                                            "params": {"a": "X"}})[:2]
        finally:
            film.apply_changes = real
        self.assertEqual(code, 409)
        self.assertIn("Odśwież", msg)

    def test_studio_pokazuje_posty_z_bledem_po_zmianie_szablonu(self):
        _, index = server.load_projects(resolve=False)
        t = server.studio_summary(index)["projekt-testowy"]["templates"][0]
        self.assertEqual((t["name"], t["broken"], t["forOwner"]), ("obj-b", [], ""))
        renamed = dict(OBJ, parametry={k if k != "hak" else "haczyk": v for k, v in OBJ["parametry"].items()},
                       wymagane=["haczyk"], limity={}, etykiety={})
        renamed["plansze"] = [{"tekst": "{{haczyk}}"}] + OBJ["plansze"][1:]
        with open(os.path.join(self.studio, "szablony", "obj-b.json"), "w", encoding="utf-8") as f:
            json.dump(renamed, f, ensure_ascii=False)
        t = server.studio_summary(index)["projekt-testowy"]["templates"][0]
        self.assertEqual(t["broken"], [self.day.isoformat()])
        os.remove(os.path.join(self.studio, "szablony", "obj-b.json"))     # usunięty szablon, którego używa post
        got = server.studio_summary(index)["projekt-testowy"]["templates"]
        self.assertEqual([(x["name"], x["uses"]) for x in got], [("obj-b", [self.day.isoformat()])])
        self.assertIn("brak pliku", got[0]["error"])

    def test_zadanie_studia_pilnuje_postow_z_szablonem(self):
        code, _msg, data = server.studio_request({"project": "projekt-testowy", "rodzaj": "szablon",
                                                  "uwaga": "Nowy szablon porównania"})
        self.assertEqual(code, 200)
        rules = " ".join(agents.film_rules(agents.STUDIO_TASK + "x"))
        self.assertIn("nie zmieniasz w nim nazw parametrów", rules)
        self.assertIn("dla_wlasciciela", rules)
        self.assertIn("{\"typ\": \"objasnienie\", \"plansze\": [...]}", " ".join(agents.film_rules(agents.POST_TASK)))


if __name__ == "__main__":
    unittest.main()
