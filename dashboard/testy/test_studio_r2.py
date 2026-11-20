"""Studio filmów, runda 2: czas plansz marki i hak, łączenie plansz przy szablonie, wymagane parametry i limity,
plansze przed i po pokazie, bezpieczeństwo (hosty, pliki dla ffmpeg), odporność nagrywarki, montaż (kolejność filtrów
bez ffmpeg), zmiana treści filmu w panelu, zmiana studia nie nagrywa minionych i opublikowanych postów."""
import json
import os
import shutil
import tempfile
import unittest

from wspolne import Baza, agents, server

film = server.film
PNG = b"\x89PNG\r\n\x1a\n\x00\x00\x00\x0dIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x06\x00\x00\x00" + b"\x00" * 48

BRAND = {"nazwa": "Marka", "zrodlo": "test", "strony": ["example.org"],
         "kolory": {"tlo": "#fbf7f1", "tekst": "#2b1d12", "akcent": "#9e5f18", "akcent2": "#c79a3e"},
         "plansza_startowa": {"tytul": "Marka", "podtytul": "Podtytuł marki", "adres": "example.org"},
         "plansza_koncowa": {"tytul": "Koniec", "podtytul": "Wezwanie do działania", "adres": "example.org"}}
POKAZ = {"tytul": "Pokaz formularza", "opis": "Pokaz {{nie_parametr}}", "typ": "pokaz",
         "parametry": {"hak": "Hak przykładowy", "mebel": "Komoda", "kat": "komoda", "napis": "Wpisujesz mebel"},
         "wymagane": ["mebel"], "limity": {"mebel": {"max": 20}, "kat": {"opcje": ["komoda", "stół"]}},
         "etykiety": {"mebel": "Mebel {{tez_nie}}"},
         "plansza_startowa": {"tytul": "{{hak}}"},
         "url": "https://example.org/generator",
         "kroki": [{"napis": "{{napis}}", "wpisz": ["#nazwa", "{{mebel}}"]}, {"wybierz": ["#kat", "{{kat}}"]}]}


class _Capture:
    """Zamiast _clip (ffmpeg): zapamiętuje filtry, pasek i flagę pierwszego klipu."""

    def __init__(self):
        self.calls = []

    def __call__(self, out, bg, dur, draws, image=None, bar=None, logo=None, first=False, fade_out=True,
                 fade_from=None, zoom=False):
        self.calls.append({"out": out, "bg": bg, "dur": dur, "draws": draws, "bar": bar, "logo": logo, "first": first,
                           "fade_out": fade_out, "image": image, "fade_from": fade_from, "zoom": zoom})
        return out, dur


class Karta(unittest.TestCase):
    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp(prefix="studio-r2-"))
        self.studio = os.path.join(self.tmp, "studio")
        os.makedirs(os.path.join(self.studio, "szablony"))
        self.write("studio/marka.json", BRAND)
        self.write("studio/szablony/pokaz-a.json", POKAZ)
        self.post = os.path.join(self.tmp, "posty", "2026-11-25-test")
        os.makedirs(self.post)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, rel, data):
        mode = "wb" if isinstance(data, bytes) else "w"
        with open(os.path.join(self.tmp, rel), mode, **({} if mode == "wb" else {"encoding": "utf-8"})) as f:
            f.write(data if isinstance(data, (str, bytes)) else json.dumps(data, ensure_ascii=False))

    def scenario(self, sc):
        self.write("posty/2026-11-25-test/scenariusz.json", sc)

    def read_scenario(self):
        with open(os.path.join(self.post, film.SCENARIO), encoding="utf-8") as f:
            return json.load(f)


class Plansze(Karta):
    def test_hak_bez_podtytulu_marki_i_z_czasem_czytania(self):
        self.scenario({"szablon": "pokaz-a", "parametry": {"mebel": "Sofa", "hak": "Opis mebla w 10 sekund na Allegro"}})
        info = film.describe(self.post)
        self.assertEqual(info["error"], "")
        card = info["introCard"]
        self.assertEqual((card["subtitle"], card["address"]), ("", ""))             # tylko hak
        # hak stoi od pierwszej klatki: bez czasu na wejście tekstu (HOOK_BASE zamiast READ_BASE)
        self.assertGreaterEqual(card["seconds"], film.HOOK_BASE + len(card["title"]) / 15 + film.XFADE / 2 - 0.01)
        self.assertTrue(card["hook"])
        self.assertEqual([w for w in info["warnings"] if "muzyki" not in w], [])   # czas liczy panel: bez ostrzeżeń
        # plansza końcowa: tytuł, podtytuł i adres wchodzą po kolei, plansza stoi najwyżej END_MAX (wezwanie nie stoi
        # długo nieruchomo), ale co najmniej domyślny czas planszy końcowej
        out = info["outroCard"]
        chars = len("Koniec") + len("Wezwanie do działania") + len("example.org")
        self.assertEqual(out["seconds"], min(film.END_MAX, max(film.CARD_TIMES["plansza_koncowa"],
                                                               1.2 + chars / 15 + film.XFADE)))

    def test_za_krotka_plansza_marki_daje_ostrzezenie(self):
        self.scenario({"typ": "objasnienie", "plansze": [{"tekst": "A"}],
                       "plansza_koncowa": {"czas": 1.5}})                           # bez tytułu: uzupełnia markę
        info = film.describe(self.post)
        self.assertEqual(info["outroCard"]["title"], "Koniec")
        self.assertTrue(info["warnings"][0].startswith("Plansza końcowa trwa 1,5 s, za krótko na przeczytanie; "
                                                       "panel wydłuży ją do "))
        self.assertTrue(info["warnings"][0].endswith(" s."))

    def test_nadpisanie_planszy_laczy_sie_z_szablonem(self):
        sc, _ = film.expand({"szablon": "pokaz-a", "parametry": {"mebel": "Sofa"}, "plansza_startowa": {"czas": 6}},
                            self.studio)
        self.assertEqual(sc["plansza_startowa"], {"tytul": "Hak przykładowy", "czas": 6})   # hak został
        sc, _ = film.expand({"szablon": "pokaz-a", "parametry": {"mebel": "Sofa"}, "plansza_startowa": False},
                            self.studio)
        self.assertIs(sc["plansza_startowa"], False)

    def test_pogrubione_tylko_zmienione_wartosci(self):
        self.scenario({"szablon": "pokaz-a", "parametry": {"mebel": "Komoda", "napis": "Inny napis"}})
        params = {p["name"]: p["changed"] for p in film.describe(self.post)["params"]}
        self.assertEqual(params, {"hak": False, "napis": True, "mebel": False, "kat": False})

    def test_kolejnosc_parametrow_jak_w_filmie_bez_widm(self):
        tpl = film.load_template(self.studio, "pokaz-a")
        self.assertEqual(film.template_params(tpl), ["hak", "napis", "mebel", "kat"])  # bez {{…}} z opisu i etykiet
        with self.assertRaisesRegex(ValueError, "nie ma parametru „nie_parametr”"):
            film.expand({"szablon": "pokaz-a", "parametry": {"mebel": "Sofa", "nie_parametr": "x"}}, self.studio)
        item = film.list_templates(self.studio)[0]
        self.assertEqual((item["title"], item["required"]), ("Pokaz formularza", ["mebel"]))

    def test_wymagane_limity_i_czytelne_bledy(self):
        self.scenario({"szablon": "pokaz-a"})
        info = film.describe(self.post)
        self.assertIn("brak parametru „mebel” (wymagany", info["error"])
        self.assertTrue(info["errorHint"].startswith("Brakuje treści tego posta: uzupełnij pole „Mebel"), info["errorHint"])
        self.assertEqual(info["errorParam"], "mebel")                                # pole do poprawy w panelu
        self.assertEqual(info["editable"], ["params"])
        self.assertEqual(info["templateTitle"], "Pokaz formularza")
        cases = (({"mebel": "  "}, "parametr „mebel”: same spacje"), ({"mebel": "Sofa", "napis": "   "}, "parametr „napis”: same spacje"),
                 ({"mebel": "x" * 21}, "parametr „mebel”: najwyżej 20 znaków"),
                 ({"mebel": "Sofa", "kat": "szafa"}, "parametr „kat”: jedna z wartości komoda, stół"),
                 ({"mebel": "{{hak}}"}, "parametr „mebel”: wartość nie może zawierać"))
        for params, msg in cases:
            with self.assertRaisesRegex(ValueError, msg):
                film.expand({"szablon": "pokaz-a", "parametry": params}, self.studio)
        sc, _ = film.expand({"szablon": "pokaz-a", "parametry": {"mebel": "Sofa", "napis": 5}}, self.studio)
        self.assertEqual(sc["kroki"][0]["napis"], "5")                             # liczba w napisie to tekst
        self.assertEqual(film.validate_scenario(sc, template=True), [])

    def test_ostrzezenie_gdy_same_wartosci_przykladu(self):
        tpl = dict(POKAZ)
        tpl.pop("wymagane")
        self.write("studio/szablony/pokaz-a.json", tpl)
        self.scenario({"szablon": "pokaz-a"})
        self.assertIn("same wartości z szablonu", film.describe(self.post)["warnings"][0])

    def test_zgodnosc_wstecz_scenariusz_reczny(self):
        self.scenario({"opis": "komentarz autora", "url": "https://example.org/a",
                       "kroki": [{"napis": "Klamry {{ }} w napisie"}]})
        self.assertEqual(film.describe(self.post)["error"], "")

    def test_plansze_przed_i_po_pokazie(self):
        self.scenario({"url": "https://example.org/a", "kroki": [{"pauza": 1}], "plansza_startowa": False,
                       "plansze_przed": [{"tekst": "Problem *jeden*"}, {"tekst": "Problem dwa", "podpis": "P"}],
                       "plansze_po": [{"tekst": "Wynik"}]})
        info = film.describe(self.post)
        self.assertEqual(info["error"], "")
        self.assertEqual(([s["text"] for s in info["before"]], [s["text"] for s in info["after"]]),
                         (["Problem jeden", "Problem dwa"], ["Wynik"]))
        parts = [s["seconds"] for s in info["before"] + info["after"]] + [info["outroCard"]["seconds"],
                                                                          film._pokaz_estimate({"kroki": [{"pauza": 1}]})]
        self.assertAlmostEqual(info["seconds"], sum(parts) - film.XFADE * 4, places=1)
        bad = film.validate_scenario({"url": "https://e.org", "kroki": [{"pauza": 1}],
                                      "plansze_przed": [{"tekst": "x"}] * 5})
        self.assertIn("plansze_przed: lista 1–4 plansz", bad)
        self.assertTrue(film.validate_scenario({"typ": "objasnienie", "plansze": [{"tekst": "A"}],
                                                "plansze_przed": [{"tekst": "x"}]}))   # tylko w pokazie


class Bezpieczenstwo(Karta):
    def test_bez_stron_w_marce_pokaz_sie_nie_nagra(self):
        for url in ("https://127.0.0.1/x", "https://localhost/x", "https://10.0.0.5/", "https://router.lan/",
                    "https://serwer.internal/", "https://[::1]/", "https://127.0.0.1.nip.io/", "https://example.org/x"):
            self.assertTrue(film.site_errors({"url": url, "kroki": []}, {"strony": []}), url)
        self.assertIn("pole strony", film.site_errors({"url": "https://example.org/x", "kroki": []}, {"strony": []})[0])
        self.assertEqual(film.site_errors({"url": "https://example.org/x", "kroki": []}, {"strony": ["example.org"]}),
                         [])
        self.assertFalse(film.public_host("127.0.0.1"))
        self.assertTrue(film.host_allowed("app.example.org", ["example.org"]))
        self.assertFalse(film.host_allowed("example.org.evil.com", ["example.org"]))
        self.assertFalse(film.host_allowed("127.0.0.1", []))

    def test_pliki_dla_ffmpeg_sprawdzane_po_tresci(self):
        os.makedirs(os.path.join(self.studio, "obrazy"))
        self.write("studio/obrazy/ok.png", PNG)
        self.write("studio/obrazy/zly.png", "#EXTM3U\n#EXT-X-MEDIA-SEQUENCE:0\nfile:///etc/passwd\n")
        self.assertEqual(film.media_error(os.path.join(self.studio, "obrazy", "ok.png"), "image"), "")
        self.assertIn("nie zgadza się", film.media_error(os.path.join(self.studio, "obrazy", "zly.png"), "image"))
        args = film.media_input(os.path.join(self.studio, "obrazy", "ok.png"), 3)
        self.assertEqual(args[:2], ["-protocol_whitelist", "file"])
        self.assertIn("image2", args)
        self.assertEqual(film.media_input("/x/muzyka.mp3")[:6], ["-protocol_whitelist", "file", "-stream_loop", "-1",
                                                                "-f", "mp3"])

    def test_logo_i_muzyka_w_marce(self):
        self.write("studio/marka.json", dict(BRAND, logo="logo.png", logo_w_rogu=True))
        self.assertIn("logo: brak pliku studio/logo.png", film.load_brand(self.studio)[1])
        self.write("studio/logo.png", "nie png")
        self.assertIn("treść pliku nie zgadza się", film.load_brand(self.studio)[1][0])
        self.write("studio/logo.png", PNG)
        brand, errors, _ = film.load_brand(self.studio)
        self.assertEqual(errors, [])
        self.assertEqual(film.logo_path(brand, self.studio), os.path.join(self.studio, "logo.png"))
        self.write("studio/marka.json", dict(BRAND, logo_w_rogu="tak"))
        self.assertIn("logo_w_rogu: true albo false", film.load_brand(self.studio)[1])

    def test_nagrywarka_zwalnia_folder_po_wyjatku(self):
        rec = film.Recorder(python="/nie/ma/takiego/pythona")
        rec.busy.add(self.post)
        rec.kinds[self.post] = "pokaz"
        msgs = []
        rec.notify = msgs.append
        rec._run(self.post, "Post")                                  # FileNotFoundError przy uruchomieniu
        self.assertEqual(rec.busy, set())
        st = film.read_state(self.post)
        self.assertEqual(st["state"], "error")
        self.assertIn("nie uruchomiono nagrania", st["error"])
        self.assertIn("Nie nagrano filmu", msgs[0])

    def test_nagrywarka_po_sukcesie_usuwa_znacznik_recznego_filmu(self):
        self.write("posty/2026-11-25-test/" + film.MANUAL, "x")
        rec = film.Recorder(python="/usr/bin/true", script="")
        rec.interpreter = lambda kind: "/usr/bin/true"
        rec.kinds[self.post] = "pokaz"
        rec._run(self.post, "Post")
        self.assertEqual(film.read_state(self.post)["state"], "done")
        self.assertFalse(os.path.exists(os.path.join(self.post, film.MANUAL)))


class Montaz(Karta):
    """Filtry ffmpeg bez uruchamiania ffmpeg (_clip podmieniony)."""

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

    def test_pierwsza_plansza_widoczna_od_pierwszej_klatki(self):
        work = tempfile.mkdtemp(dir=self.tmp)
        texts = film._Texts(work)
        film.brand_card(self.brand(), {"tytul": "Hak"}, "plansza_startowa", work, texts, "s.mp4", first=True)
        film.brand_card(self.brand(), {"tytul": "Hak"}, "plansza_startowa", work, texts, "t.mp4")
        first, later = self.cap.calls
        self.assertTrue(first["first"])
        self.assertFalse([d for d in first["draws"] if "alpha=" in d])       # bez wejścia: tekst od t=0
        self.assertTrue([d for d in later["draws"] if "alpha=" in d])
        cards = [{"tekst": "Pierwsza *plansza*", "podpis": "Podpis"}, {"tekst": "Druga"}]
        self.cap.calls.clear()
        film.explainer_clips(cards, self.brand(), work, texts, self.post, first=True)
        one, two = self.cap.calls
        text_one = [d for d in one["draws"] if d.startswith("drawtext") and "enable=" not in d]
        self.assertFalse([d for d in text_one if "alpha=" in d])
        self.assertTrue([d for d in two["draws"] if d.startswith("drawtext") and "alpha=" in d])
        for c in (one, two):
            self.assertGreaterEqual(c["bar"][1], film.SAFE_TOP)                # pasek pod strefą interfejsu

    def test_podpis_przy_lewym_marginesie_i_z_wejsciem(self):
        work = tempfile.mkdtemp(dir=self.tmp)
        film.explainer_clips([{"tekst": "Tekst planszy", "podpis": "Podpis planszy"}], self.brand(), work,
                             film._Texts(work), self.post)
        boxes = [d for d in self.cap.calls[0]["draws"] if d.startswith("drawbox") and ":w=120:" not in d]
        self.assertGreater(len(boxes), 2)                                    # krycie rośnie w krokach
        self.assertTrue(all(d.startswith("drawbox=x=%d:" % film.MARGIN) for d in boxes))
        alphas = [float(d.split("@")[1].split(":")[0]) for d in boxes]
        self.assertEqual(alphas, sorted(alphas))
        cap = [d for d in self.cap.calls[0]["draws"] if d.startswith("drawtext") and "enable=" in d]
        self.assertTrue(all(":x=%d:" % (film.MARGIN + int(56 * 0.6)) in d or ":x=" in d for d in cap))
        self.assertFalse([d for d in cap if "(w-text_w)/2" in d])            # tekst podpisu też do lewej

    def test_wezwanie_na_planszy_koncowej_duze_i_w_kolorze_tekstu(self):
        work = tempfile.mkdtemp(dir=self.tmp)
        film.brand_card(self.brand(), BRAND["plansza_koncowa"], "plansza_koncowa", work, film._Texts(work), "k.mp4")
        draws = self.cap.calls[0]["draws"]
        fg = film._col(BRAND["kolory"]["tlo"])
        sizes = [int(d.split("fontsize=")[1].split(":")[0]) for d in draws if d.startswith("drawtext")]
        cols = [d.split("fontcolor=")[1].split(":")[0] for d in draws if d.startswith("drawtext")]
        self.assertTrue(all(s >= 58 for s in sizes), sizes)
        self.assertTrue(all(c == fg for c in cols), cols)                     # akcent tylko na kresce

    def test_przejscie_bez_podwojnej_ekspozycji(self):
        # między planszami przenikanie (treść gaśnie do tła przed przejściem), bez czerni przed planszą końcową
        self.assertEqual(film.transition("#2b1d12", "#fbf7f1"), "slideup")   # jasne ↔ ciemne: bez szarości
        self.assertEqual(film.transition("#fbf7f1", "#f0e6d8"), "fade")
        self.assertEqual(film.transition("#fbf7f1", "#fbf7f1"), "fade")
        self.assertEqual(film.transition("#2b1d12", None), "fadeblack")       # nagranie strony: przez czerń

    def test_dlugie_slowo_dzielone_po_sylabie(self):
        font = film.Font(film.FONT, 92)
        parts = film._split_long("Konstantynopolitańczykowianeczka", font, 700)
        self.assertGreater(len(parts), 1)
        self.assertTrue(all(len(p.rstrip("-")) >= 3 for p in parts))
        self.assertTrue(all(p.endswith("-") for p in parts[:-1]))
        f, lines = film.fit("Konstantynopolitańczykowianeczka", font, 700, list(range(92, 59, -4)), 3)
        self.assertGreater(f.size, 60)                                       # nie od razu najmniejszy rozmiar


class ZmianaWPanelu(Karta):
    def test_zmiana_parametru_z_kontrola(self):
        self.scenario({"szablon": "pokaz-a", "parametry": {"mebel": "Komoda"}})
        info = film.apply_changes(self.post, params={"mebel": " Sofa "})
        self.assertEqual(self.read_scenario()["parametry"]["mebel"], "Sofa")
        self.assertEqual(info["error"] if "error" in info else "", "")
        with self.assertRaisesRegex(ValueError, "najwyżej 20 znaków"):
            film.apply_changes(self.post, params={"mebel": "x" * 30})
        self.assertEqual(self.read_scenario()["parametry"]["mebel"], "Sofa")   # błąd: plik bez zmian
        with self.assertRaisesRegex(ValueError, "nie ma parametru"):
            film.apply_changes(self.post, params={"obcy": "x"})

    def test_zmiana_planszy_objasnienia(self):
        self.scenario({"typ": "objasnienie", "plansze": [{"tekst": "A", "podpis": "B"}, {"tekst": "C"}]})
        self.assertEqual(film.describe(self.post)["editable"], ["slides"])
        film.apply_changes(self.post, slides=[{"n": 2, "tekst": "Nowy", "podpis": "Pod"}, {"n": 1, "podpis": ""}])
        self.assertEqual(self.read_scenario()["plansze"], [{"tekst": "A"}, {"tekst": "Nowy", "podpis": "Pod"}])
        with self.assertRaisesRegex(ValueError, "tekst 1–90"):
            film.apply_changes(self.post, slides=[{"n": 1, "tekst": "x" * 91}])
        with self.assertRaisesRegex(ValueError, "nie ma takiej planszy"):
            film.apply_changes(self.post, slides=[{"n": 3, "tekst": "x"}])


class StudioSerwer(Baza):
    def setUp(self):
        super().setUp()
        self.studio = os.path.join(self.folder, "studio")
        os.makedirs(os.path.join(self.studio, "szablony"))
        for name, data in (("szablony/pokaz-a.json", POKAZ), ("marka.json", BRAND)):
            with open(os.path.join(self.studio, name), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)

    def post(self, day, params=None):
        pf = os.path.join(self.folder, "posty", "%s-film" % day)
        os.makedirs(pf, exist_ok=True)
        with open(os.path.join(pf, film.SCENARIO), "w", encoding="utf-8") as f:
            json.dump({"szablon": "pokaz-a", "parametry": params or {"mebel": "Sofa"}}, f)
        return pf

    def stamp(self, pf, scenario, film_at, studio_at):
        os.utime(os.path.join(pf, film.SCENARIO), (scenario, scenario))
        with open(os.path.join(pf, "film.mp4"), "wb") as f:
            f.write(b"x")
        os.utime(os.path.join(pf, "film.mp4"), (film_at, film_at))
        for p in (os.path.join(self.studio, "marka.json"), os.path.join(self.studio, "szablony", "pokaz-a.json")):
            os.utime(p, (studio_at, studio_at))

    def test_zmiana_studia_nagrywa_tylko_nadchodzace_posty(self):
        past, future = self.post("2026-11-10"), self.post("2026-11-25")
        for pf in (past, future):
            self.stamp(pf, 100, 200, 300)                          # studio zmienione po nagraniu
        today = "2026-11-19"
        self.assertIsNone(server.film_pending(past, today=today))          # miniony post: film zostaje
        self.assertEqual(server.film_pending(future, today=today), 300)
        self.assertIsNone(server.film_pending(future, today=today, published=True))   # opublikowany
        with open(os.path.join(future, film.MANUAL), "w") as f:
            f.write("x")
        self.assertIsNone(server.film_pending(future, today=today))        # film wgrany ręcznie
        self.assertTrue(server.post_info(past)["filmStale"])               # w poście: film starszy niż studio
        self.assertTrue(server.post_info(future)["filmManual"])
        os.utime(os.path.join(past, film.SCENARIO), (400, 400))            # poprawka tego posta: nagrywa od nowa
        self.assertEqual(server.film_pending(past, today=today), 400)
        self.assertFalse(server.post_info(past)["filmStale"])

    def test_opublikowane_dni_z_kampanii(self):
        tasks = [{"kind": "publikacja", "state": "done", "project": "p", "date": "2026-11-20"},
                 {"kind": "publikacja", "state": "todo", "project": "p", "date": "2026-11-21"},
                 {"kind": "zadanie", "state": "done", "project": "p", "date": "2026-11-22"}]
        self.assertEqual(server.published_days(tasks), {("p", "2026-11-20")})

    def test_trasa_zmiany_tresci_filmu(self):
        pf = self.post("2026-11-25")
        started = []

        class Rec:
            def start(self, folder, title=""):
                started.append(os.path.basename(folder))
                return 202, "", {"state": "running"}
        saved = server._recorder
        server._recorder = Rec()
        try:
            code, err, extra = server.WRITES["/api/film/zmien"](
                {"project": "projekt-testowy", "date": "2026-11-25", "params": {"mebel": "Stół"}})
            self.assertEqual((code, err, extra["recording"]), (200, "", True))
            self.assertEqual(started, ["2026-11-25-film"])
            with open(os.path.join(pf, film.SCENARIO), encoding="utf-8") as f:
                self.assertEqual(json.load(f)["parametry"]["mebel"], "Stół")
            code, err = server.film_change({"project": "projekt-testowy", "date": "2026-11-25",
                                            "params": {"mebel": "x" * 25}})[:2]
            self.assertEqual(code, 400)
            self.assertIn("najwyżej 20 znaków", err)
            self.assertEqual(server.film_change({"project": "projekt-testowy", "date": "2026-11-26",
                                                 "params": {"mebel": "x"}})[0], 404)
            self.assertEqual(server.film_change({"project": "projekt-testowy", "date": "2026-11-25"})[0], 400)
        finally:
            server._recorder = saved

    def test_prosba_o_zmiane_studia_dla_agenta(self):
        code, err, extra = server.WRITES["/api/studio/popros"](
            {"project": "projekt-testowy", "rodzaj": "marka", "uwaga": "Na końcu adres większy"})
        self.assertEqual((code, err), (200, ""))
        self.assertTrue(extra["title"].startswith(agents.STUDIO_TASK))
        data, _ = server.load_projects()
        task = next(t for t in data["tasks"] if t["title"] == extra["title"])
        self.assertIn("Na końcu adres większy", json.dumps(task["detail"], ensure_ascii=False))
        self.assertEqual(server.studio_request({"project": "projekt-testowy", "rodzaj": "x", "uwaga": "abc"})[0], 400)
        prompt = self.manager.task_prompt("claude", "P", "ZADANIA.md", 4, extra["title"], "")
        self.assertIn("To zadanie zmienia studio filmów projektu", prompt)
        post = self.manager.task_prompt("claude", "P", "ZADANIA.md", 4, agents.FIX_POST_TASK + "2026-11-25: x", "")
        self.assertIn("Poprawka jednego posta zmienia tylko scenariusz.json tego posta", post)
        self.assertNotIn("To zadanie zmienia studio filmów projektu", post)

    def test_studio_w_danych_panelu(self):
        pf = self.post("2026-11-25")
        with open(os.path.join(pf, "film.mp4"), "wb") as f:
            f.write(b"x")
        _, index = server.load_projects(resolve=False)
        s = server.studio_summary(index)["projekt-testowy"]
        t = s["templates"][0]
        self.assertEqual((t["title"], t["required"], t["sample"]), ("Pokaz formularza", ["mebel"], "2026-11-25"))
        self.assertEqual((s["brand"]["music"], s["brand"]["logo"]), (False, False))


REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HAS_FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


@unittest.skipUnless(HAS_FFMPEG, "brak ffmpeg (renderowanie na serwerze: testy/render_na_serwerze.sh)")
class RenderSerwer(unittest.TestCase):
    """Render prawdziwych studiów projektów (czcionki z marki, pierwsza klatka z tekstem, długość jak w opisie),
    logo i muzyka marki. Klatki do obejrzenia: FILM_KLATKI=<katalog>."""

    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp(prefix="render-r2-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_ff(self, *args):
        import subprocess
        return subprocess.run(["ffmpeg", "-v", "error", "-y"] + list(args), check=True, capture_output=True)

    def probe(self, path):
        import subprocess
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height:format=duration",
                            "-of", "json", path], capture_output=True, text=True)
        return json.loads(r.stdout)

    def frame(self, video, t, name):
        out = os.path.join(self.tmp, name)
        self.run_ff("-ss", "%.2f" % t, "-i", video, "-frames:v", "1", out)
        keep = os.environ.get("FILM_KLATKI")
        if keep:
            os.makedirs(keep, exist_ok=True)
            shutil.copy(out, os.path.join(keep, name))
        return out

    def colors(self, png):
        """Liczba różnych kolorów w klatce (samo tło: 1–2)."""
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("brak PIL")
        with Image.open(png) as im:
            return len(im.convert("RGB").getcolors(maxcolors=1 << 20) or [])

    def card(self, pid):
        card = os.path.join(self.tmp, pid)
        shutil.copytree(os.path.join(REPO, "szkice", pid, "studio"), os.path.join(card, "studio"))
        return card

    def test_czcionki_marek_znalezione(self):
        for name in ("Fraunces", "Inter:Medium", "Inter:SemiBold", "Inter:Black", "Inter:Bold"):
            path, _bold = film.font_spec(name)
            self.assertNotIn("DejaVu", path, name)

    def test_objasnienia_projektow(self):
        for pid in ("generator-opisow-mebli", "company-audits", "naulikapp"):
            card = self.card(pid)
            for t in film.list_templates(os.path.join(card, "studio")):
                if t["kind"] != "objasnienie":
                    continue
                post = os.path.join(card, "posty", "2026-12-01-%s" % t["name"])
                os.makedirs(post)
                with open(os.path.join(card, "studio", "szablony", t["name"] + ".json"), encoding="utf-8") as f:
                    tpl = json.load(f)
                with open(os.path.join(post, film.SCENARIO), "w", encoding="utf-8") as f:
                    json.dump({"szablon": t["name"], "parametry": {k: tpl["parametry"][k] for k in t["required"]}}, f)
                for v in tpl["parametry"].values():       # zrzut telefonu (pionowy) albo zdjęcie (poziome) do planszy
                    if isinstance(v, str) and film.IMAGE_RE.match(v):
                        size = "1170x2532" if v.startswith("zrzut") else "1600x1200"
                        self.run_ff("-f", "lavfi", "-i", "testsrc2=s=%s" % size, "-frames:v", "1",
                                    os.path.join(post, v))
                info = film.describe(post)
                self.assertEqual(info["error"], "", (pid, t["name"]))
                out = film.record(post, "objasnienie")
                meta = self.probe(out)
                self.assertEqual((meta["streams"][0]["width"], meta["streams"][0]["height"]), (1080, 1920))
                self.assertAlmostEqual(float(meta["format"]["duration"]), info["seconds"], delta=0.3)
                first = self.frame(out, 0, "%s-%s-0.png" % (pid, t["name"]))
                self.assertGreater(self.colors(first), 20, (pid, t["name"]))   # hak widoczny w pierwszej klatce
                self.frame(out, info["slides"][0]["seconds"] + 0.6, "%s-%s-2.png" % (pid, t["name"]))
                self.frame(out, info["seconds"] - 0.3, "%s-%s-koniec.png" % (pid, t["name"]))

    def test_logo_muzyka_i_hak_na_planszy_startowej(self):
        card = self.card("generator-opisow-mebli")
        studio = os.path.join(card, "studio")
        self.run_ff("-f", "lavfi", "-i", "color=c=0x9e5f18@1:s=400x160", "-frames:v", "1", os.path.join(studio, "logo.png"))
        self.run_ff("-f", "lavfi", "-i", "sine=frequency=440:duration=3", os.path.join(studio, "podklad.wav"))
        with open(os.path.join(studio, "marka.json"), encoding="utf-8") as f:
            brand = json.load(f)
        brand.update(logo="logo.png", logo_w_rogu=True, muzyka="podklad.wav")
        with open(os.path.join(studio, "marka.json"), "w", encoding="utf-8") as f:
            json.dump(brand, f, ensure_ascii=False)
        post = os.path.join(card, "posty", "2026-12-02-hak")
        os.makedirs(post)
        with open(os.path.join(post, film.SCENARIO), "w", encoding="utf-8") as f:
            json.dump({"typ": "objasnienie", "plansza_startowa": {"tytul": "Opis mebla na Allegro w 10 sekund"},
                       "plansze": [{"tekst": "Plansza *pierwsza*", "podpis": "Podpis planszy"}]}, f, ensure_ascii=False)
        info = film.describe(post)
        self.assertEqual((info["error"], info["music"]), ("", True))
        out = film.record(post)
        meta = self.probe(out)
        self.assertAlmostEqual(float(meta["format"]["duration"]), info["seconds"], delta=0.3)
        self.assertIn("audio", [s["codec_type"] for s in meta["streams"]])
        self.assertGreater(self.colors(self.frame(out, 0, "hak-0.png")), 20)
        self.frame(out, info["introCard"]["seconds"] + 1.5, "hak-plansza.png")
        self.frame(out, info["seconds"] - 0.3, "hak-koniec.png")


if __name__ == "__main__":
    unittest.main()
