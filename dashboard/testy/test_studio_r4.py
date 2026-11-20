"""Studio filmów, runda 4: liczby z formularza bez NaN i nieskończoności, kontrola zmian z panelu (plansze, puste pole
przywraca przykład), kolejka nagrywarki (jedno nagranie naraz) i wersja filmu z chwili startu, podkłady na zmianę,
logowanie z selektorami, układy plansz w serii, hak i plansza końcowa w limitach, napisy SRT, zadanie „Nagraj film”
powiązane z postem po stronie serwera, panel bez zwiniętego filmu."""
import json
import math
import os
import re
import unittest

from test_studio_r2 import BRAND, Karta, _Capture
from test_studio_r3 import OBJ
from wspolne import server

film = server.film
PANEL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "panel.html")


class _Inline:
    """Zamiast threading.Thread: wywołanie od razu (bez wątku)."""

    def __init__(self, target, args=(), daemon=None):
        self.target, self.args = target, args

    def start(self):
        self.target(*self.args)


class Wartosci(Karta):
    def setUp(self):
        super().setUp()
        self.write("studio/szablony/obj-b.json", OBJ)

    def test_liczba_tylko_z_cyfr(self):
        for bad in ("nan", "inf", "-inf", "1e400", "1_0", "Infinity"):
            self.assertEqual(film.coerce_params(OBJ, {"c": bad}), {"c": bad}, bad)    # zostaje tekstem
        self.assertEqual(film.coerce_params(OBJ, {"c": "4,5"}), {"c": 4.5})
        self.assertFalse(film._num(float("nan")))
        self.assertFalse(film._num(float("inf")))

    def test_zapis_bez_nan_w_scenariuszu(self):
        self.scenario({"szablon": "obj-b", "parametry": {"hak": "Hak"}})
        with self.assertRaises(ValueError):
            film.apply_changes(self.post, params={"c": "nan"})
        with open(os.path.join(self.post, film.SCENARIO), encoding="utf-8") as f:
            raw = f.read()
        self.assertNotIn("NaN", raw)
        self.assertNotIn("Infinity", raw)

    def test_puste_pole_przywraca_przyklad(self):
        self.scenario({"szablon": "obj-b", "parametry": {"hak": "Hak", "a": "Moje"}})
        film.apply_changes(self.post, params={"a": ""})
        with open(os.path.join(self.post, film.SCENARIO), encoding="utf-8") as f:
            self.assertNotIn("a", json.load(f)["parametry"])                     # wartość przykładowa szablonu
        with self.assertRaises(ValueError):
            film.apply_changes(self.post, params={"hak": ""})                    # wymagane: puste to błąd

    def test_zmiany_plansz_lista_i_numer(self):
        self.scenario({"typ": "objasnienie", "plansze": [{"tekst": "A"}, {"tekst": "B"}]})
        for bad, text in (({"n": 1}, "lista"), ([{"tekst": "X"}], "bez numeru"), ([{"n": True, "tekst": "X"}], "nie ma"),
                          ([{"n": 3, "tekst": "X"}], "nie ma takiej")):
            with self.assertRaises(ValueError) as e:
                film.apply_changes(self.post, slides=bad)
            self.assertIn(text, str(e.exception))

    def test_aliasy_parametrow(self):
        self.write("studio/szablony/obj-b.json", dict(OBJ, aliasy={"stary_hak": "hak"}))
        self.scenario({"szablon": "obj-b", "parametry": {"stary_hak": "Hak ze starego posta"}})
        info = film.describe(self.post)
        self.assertEqual(info["error"], "")
        self.assertEqual(info["slides"][0]["text"], "Hak ze starego posta")

    def test_komentarz_w_scenariuszu(self):
        self.scenario({"typ": "objasnienie", "komentarz": "notatka", "plansze": [{"tekst": "A"}]})
        self.assertEqual(film.describe(self.post)["error"], "")


class Nagrywarka(Karta):
    def setUp(self):
        super().setUp()
        self.post2 = os.path.join(self.tmp, "posty", "2026-11-27-drugi")
        os.makedirs(self.post2)
        for p in (self.post, self.post2):
            with open(os.path.join(p, film.SCENARIO), "w", encoding="utf-8") as f:
                json.dump({"typ": "objasnienie", "plansze": [{"tekst": "A"}]}, f)
        self.thread = film.threading.Thread

    def tearDown(self):
        film.threading.Thread = self.thread
        super().tearDown()

    def test_jedno_nagranie_naraz_drugie_w_kolejce(self):
        rec = film.Recorder(python="/bin/false")
        rec.available = lambda kind="pokaz": True
        started = []
        rec._run = lambda folder, title: started.append(folder)
        self.assertEqual(rec.start(self.post)[0], 202)
        code, msg, data = rec.start(self.post2)
        self.assertEqual((code, data["state"]), (202, "queued"))
        self.assertEqual(film.read_state(self.post2)["state"], "queued")
        self.assertEqual(started, [self.post])                                   # bez drugiego Chromium/ffmpeg
        code, _msg, data = rec.start(self.post)                                  # ten sam film w trakcie: po nim
        self.assertEqual(data["state"], "queued")
        self.assertEqual(film.read_state(self.post)["state"], "running")
        rec.busy.discard(self.post)
        rec._next()
        self.assertEqual(started, [self.post, self.post2])
        self.assertEqual(film.read_state(self.post2)["state"], "running")

    def test_film_ma_wersje_z_chwili_startu(self):
        """Zmiana scenariusza w trakcie nagrania: film jest starszy niż ta zmiana, więc nagra się jeszcze raz."""
        sc = os.path.join(self.post, film.SCENARIO)
        for path in (sc, os.path.join(self.studio, film.BRAND)):
            os.utime(path, (1000, 1000))
        rec = film.Recorder(python="/bin/false", script=os.path.join(self.tmp, "nagraj.py"))
        rec.available = lambda kind="pokaz": True
        with open(rec.script, "w", encoding="utf-8") as f:     # „nagranie”: zapis filmu, potem zmiana scenariusza
            f.write("import os,sys\nopen(os.path.join(sys.argv[2],'film.mp4'),'wb').write(b'x')\n"
                    "os.utime(os.path.join(sys.argv[2],'scenariusz.json'),(5000,5000))\n")
        rec.interpreter = lambda kind: film.sys.executable
        film.threading.Thread = _Inline
        self.assertEqual(rec.start(self.post)[0], 202)
        fm = os.path.join(self.post, "film.mp4")
        self.assertEqual(os.path.getmtime(fm), 1000)
        self.assertLess(os.path.getmtime(fm), film.version(self.post))           # film starszy niż poprawka
        self.assertEqual(film.read_state(self.post)["state"], "done")

    def test_zrzut_bledu_znika_po_udanym_nagraniu(self):
        with open(os.path.join(self.post, film.ERROR_SHOT), "wb") as f:
            f.write(b"x")
        rec = film.Recorder(python="/bin/false", script=os.path.join(self.tmp, "ok.py"))
        rec.available = lambda kind="pokaz": True
        with open(rec.script, "w", encoding="utf-8") as f:
            f.write("print('ok')\n")
        rec.interpreter = lambda kind: film.sys.executable
        film.threading.Thread = _Inline
        rec.start(self.post)
        self.assertFalse(os.path.exists(os.path.join(self.post, film.ERROR_SHOT)))

    def test_bledy_nagrania_po_polsku(self):
        self.assertIn("konto demo", film.record_hint("Błąd nagrania: brak konta demo do nagrań"))
        self.assertIn("zrzut", film.record_hint("krok 3 (kliknięcie): element strony nie pojawił się na czas"))
        self.assertIn("ffmpeg", film.record_hint("montaż: Invalid argument"))
        self.assertEqual(film.step_label({"wpisz": ["#typ", "Komoda"], "napis": "Wpisujesz mebel"}),
                         "wpisanie „Komoda”, napis „Wpisujesz mebel”")
        self.assertNotIn("[", film.step_label({"wybierz": ["#kat", "komoda"]}))
        self.assertIn("na czas", film.step_error(Exception("Timeout 10000ms exceeded.\nCall log")))


class Muzyka(Karta):
    def test_podklady_na_zmiane_i_wlasny_w_scenariuszu(self):
        brand = {"muzyka": ["a.mp3", "b.mp3"]}
        posts = []
        for n in ("2026-11-21-a", "2026-11-23-b", "2026-11-25-c"):
            p = os.path.join(self.tmp, "posty", n)
            os.makedirs(p, exist_ok=True)
            with open(os.path.join(p, film.SCENARIO), "w", encoding="utf-8") as f:
                f.write("{}")
            posts.append(p)
        names = [film.music_name(p, brand, {}) for p in posts]
        self.assertEqual(names, ["a.mp3", "b.mp3", "a.mp3"])                   # kolejne filmy: inny podkład
        self.assertEqual(film.music_name(posts[0], brand, {"muzyka": "c.mp3"}), "c.mp3")
        self.assertEqual(film.music_name(posts[0], brand, {"muzyka": False}), "")
        self.assertEqual(film.validate_brand(dict(BRAND, muzyka=["a.mp3", "b.mp3"])), [])
        self.assertTrue(film.validate_brand(dict(BRAND, muzyka=["../a.mp3"])))

    def test_film_bez_muzyki_swiadomie_bez_ostrzezenia(self):
        self.scenario({"typ": "objasnienie", "muzyka": False, "plansze": [{"tekst": "A"}]})
        info = film.describe(self.post)
        self.assertEqual(info["error"], "")
        self.assertFalse([w for w in info["warnings"] if "muzyki" in w])
        self.scenario({"typ": "objasnienie", "muzyka": "brak.mp3", "plansze": [{"tekst": "A"}]})
        self.assertIn("muzyka", film.describe(self.post)["error"])


class Logowanie(unittest.TestCase):
    def test_selektory_z_scenariusza(self):
        self.assertEqual(film.login_spec("https://x.org/logowanie")["email"], "#lg-email")
        spec = film.login_spec({"url": "https://x.org/login", "email": "#mail", "haslo": "#pw", "wyslij": "#go"})
        self.assertEqual((spec["url"], spec["email"], spec["wyslij"]), ("https://x.org/login", "#mail", "#go"))
        self.assertEqual(film.login_errors({"url": "https://x.org/login", "email": "#m"}), [])
        self.assertTrue(film.login_errors({"url": "https://x.org/login", "pole": "#m"}))
        self.assertTrue(film.login_errors({"email": "#m"}))
        self.assertTrue(film.login_errors(5))


class Uklady(Karta):
    def test_seria_krokow_w_jednym_ukladzie(self):
        cards = [{"tekst": "Gdzie to zapisać?"}, {"tekst": "*1.* Otwierasz dziennik bieżącego rejsu"},
                 {"tekst": "*2.* Wybierasz usterkę"}, {"tekst": "*3.* Zapis ma godzinę"}]
        self.assertEqual(film.layouts(cards), ["srodek", "tekst", "tekst", "tekst"])   # krok 3 nie na środku
        short = [{"tekst": "Hak?"}, {"tekst": "Raz"}, {"tekst": "Dwa"}]
        self.assertEqual(film.layouts(short), ["srodek", "srodek", "srodek"])
        self.assertEqual(film.layouts([{"tekst": "A", "uklad": "liczba"}]), ["liczba"])

    def test_walidacja_ukladu(self):
        self.assertTrue(film._slides_errors([{"tekst": "A", "uklad": "inny"}], "plansze", 5))
        self.assertTrue(film._slides_errors([{"tekst": "A", "uklad": "zrzut"}], "plansze", 5))
        self.assertTrue(film._slides_errors([{"tekst": "Jeden", "uklad": "lista"}], "plansze", 5))
        self.assertEqual(film._slides_errors([{"tekst": "A; B", "uklad": "lista"}], "plansze", 5), [])

    def test_naglowek_stoi_tresc_gasnie_pasek_serii(self):
        cap = _Capture()
        real = film._clip
        film._clip = cap
        try:
            work = os.path.join(self.tmp, "w")
            os.makedirs(work)
            film.explainer_clips([{"tekst": "A"}, {"tekst": "B", "uklad": "liczba"}, {"tekst": "C; D", "uklad": "lista"},
                                  {"tekst": "Cytat", "podpis": "Autor", "uklad": "cytat"}],
                                 self.brand(), work, film._Texts(work), self.post)
        finally:
            film._clip = real
        self.assertTrue(all(c["fade_from"] == film.BAR_Y + 14 for c in cap.calls))
        bars = [c["bar"] for c in cap.calls]
        self.assertEqual(bars[0][2], 0.0)
        self.assertAlmostEqual(bars[-1][3], 1.0)
        self.assertTrue(all(abs(a[3] - b[2]) < 1e-9 for a, b in zip(bars, bars[1:])))   # postęp całej serii
        swap = [d for d in cap.calls[1]["draws"] if "enable='lt(t," in d]
        self.assertEqual(len(swap), 1)                                   # w przenikaniu jeszcze poprzedni numer

    def brand(self):
        return film.load_brand(self.studio)[0]


class Czasy(unittest.TestCase):
    def test_plansza_koncowa_najwyzej_end_max(self):
        card = {"tytul": "10 opisów miesięcznie za darmo", "podtytul": "Konto Free, bez karty", "adres": "opisarnia.pl"}
        self.assertEqual(film.brand_time(card, "plansza_koncowa")[0], film.END_MAX)
        self.assertGreater(film.brand_time(dict(card, czas=6), "plansza_koncowa")[0], film.END_MAX)   # podany czas

    def test_limit_haka_zgodny_z_czasem(self):
        self.assertEqual(film.HOOK_CHARS, 43)
        sec = film.card_time({"tekst": "x" * film.HOOK_CHARS}, hook=True)[0]
        self.assertLessEqual(sec, film.HOOK_MAX)

    def test_srt(self):
        text = film.srt_text([(0, 2.5, "Hak"), (2.35, 3661.2, "Dwa\nwiersze")])
        self.assertIn("1\n00:00:00,000 --> 00:00:02,500\nHak\n", text)
        self.assertIn("00:00:02,350 --> 01:01:01,200\nDwa\nwiersze", text)

    def test_wiersze_wyrownane(self):
        f = film.Font(film.FONT, 62)
        lines = film.wrap("Napisz w komentarzu, wyślemy zaproszenie do testu", f, film.TEXT_W)
        self.assertTrue(all(len(x.split()) > 1 for x in lines[:-1]), lines)          # bez samotnego słowa w środku


class ZadanieFilmu(unittest.TestCase):
    def test_powiazanie_po_materiale_i_po(self):
        import tempfile
        tmp = os.path.realpath(tempfile.mkdtemp(prefix="film-link-"))
        try:
            os.makedirs(os.path.join(tmp, "posty", "2026-11-20-film-a"))
            with open(os.path.join(tmp, "KARTA.md"), "w", encoding="utf-8") as f:
                f.write("# Karta\n")
            index = {"p": tmp}
            rec = {"project": "p", "title": "Nagraj film A: test", "channel": "", "kind": "publikacja",
                   "detail": {"refs": [{"path": "posty/2026-11-20-film-a/scenariusz.json"}]}}
            self.assertEqual(server.film_link(rec, [rec], index), os.path.join(tmp, "posty", "2026-11-20-film-a"))
            other = dict(rec, title="Opublikuj film A")
            self.assertIsNone(server.film_link(other, [other], index))
            server.film_links([rec], index)
            self.assertEqual(rec["filmPost"]["day"], "2026-11-20")
            self.assertFalse(rec["filmPost"]["film"])
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)

    def test_kampania_mowi_ze_film_nagrywa_panel(self):
        path = os.path.join(os.path.dirname(PANEL), "..", "szkice", "generator-opisow-mebli", "kampanie", "staly-rytm.md")
        if not os.path.isfile(path):
            self.skipTest("brak karty")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        row = next(x for x in text.splitlines() if x.startswith("- [") and "Obejrzyj film A" in x)
        self.assertIn("czas: 5", row)
        self.assertIn("nagrany przez panel", row)                                # tytuł: ogląda, nie nagrywa
        self.assertNotIn("60 sekund", row)                                       # zgodny z hakiem „w 10 s”
        self.assertIn("po: Obejrzyj film A", text)
        self.assertNotIn("scenariusza zastępczego", text)
        self.assertIn("materiał: posty/2026-11-20-film-a-opis-pl-de/", text)


class Panel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(PANEL, encoding="utf-8") as f:
            cls.html = f.read()

    def test_film_nie_w_zwinietych_szczegolach(self):
        self.assertNotIn("flm-watch", self.html)                                 # odtwarzacz nie w <details>
        self.assertIn("postBox(t,fday,false,'film')", self.html)                 # film i „Co poprawić” na wierzchu
        self.assertIn("if(ftask)h+=postBox(t,fday,false,'text')", self.html)     # w szczegółach sam tekst posta

    def test_jeden_stan_filmu(self):
        body = self.html[self.html.index("function mCard("):]
        body = body[:body.index("\nfunction ")]
        self.assertIn("filmState(d,t,day)", body)
        self.assertNotIn("'błąd nagrania'", body)
        st = self.html[self.html.index("function filmState("):]
        st = st[:st.index("\n}")]
        self.assertIn("filmQueued", st)                                          # ta sama kolejka co w Teraz
        self.assertNotIn("&&!d.film)return ['red'", st)                          # błąd także przy starym filmie

    def test_bez_zdublowanych_funkcji(self):
        names = re.findall(r"\bfunction\s+([A-Za-z0-9_]+)\s*\(", self.html)
        self.assertEqual(len(names), len(set(names)))



class WgranieDoStudia(unittest.TestCase):
    def test_podklad_i_logo_do_marki(self):
        import shutil
        import tempfile
        tmp = os.path.realpath(tempfile.mkdtemp(prefix="studio-plik-"))
        real = server.load_projects
        server.load_projects = lambda resolve=False: ({}, {"p": tmp})
        try:
            with open(os.path.join(tmp, "KARTA.md"), "w", encoding="utf-8") as f:
                f.write("# Karta\n")
            os.makedirs(os.path.join(tmp, "studio"))
            with open(os.path.join(tmp, "studio", "marka.json"), "w", encoding="utf-8") as f:
                json.dump(BRAND, f)
            mp3 = b"ID3" + b"\x00" * 64
            code, err, data = server.studio_add_file("p", "muzyka", "audio/mpeg", mp3, "")
            self.assertEqual(code, 400)                                           # licencja wymagana
            code, err, data = server.studio_add_file("p", "muzyka", "audio/mpeg", mp3, "YouTube Audio Library")
            self.assertEqual((code, err), (200, ""))
            code, err, data2 = server.studio_add_file("p", "logo", "image/gif", b"GIF89a", "własne")
            self.assertEqual(code, 400)
            with open(os.path.join(tmp, "studio", "marka.json"), encoding="utf-8") as f:
                brand = json.load(f)
            self.assertEqual(brand["muzyka"], data["name"])
            self.assertIn("YouTube Audio Library", brand["zrodlo"])
            self.assertEqual(film.load_brand(os.path.join(tmp, "studio"))[1], [])
            code, err, _ = server.studio_add_file("p", "muzyka", "audio/mpeg", b"nie mp3", "x" * 5)
            self.assertEqual(code, 400)                                           # treść niezgodna z rozszerzeniem
        finally:
            server.load_projects = real
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
