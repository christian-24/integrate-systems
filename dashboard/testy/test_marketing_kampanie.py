"""Marketing: kampanie czytelne, reklamy statyczne, nowa kampania z panelu (zlecenie 2026-11-25).

Rodzaje wierszy kampanii (pole „rodzaj:” i rozpoznanie, zgodność wstecz), stan reklam w przeglądzie, „Brak …” i „Zleć”
tylko przy reklamach i publikacjach (dane i /api/post/zlec), brak automatu dla kroków właściciela, nowa kampania
(szkic + zadanie agenta, „grafiki: tylko zdjęcia”), miniatura reklamy oraz w Chromium: przegląd kampanii, zwinięty
harmonogram, widok Marketing z kampaniami, formularz nowej kampanii, brak poziomego przewijania i błędów JS.
"""
import datetime
import glob
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from test_asystent_duzy import PW, Duzy
from test_serwer import Serwer
from wspolne import projekt, server

HERE = os.path.dirname(os.path.abspath(__file__))
DASH = os.path.dirname(HERE)
TODAY = datetime.date.today()


def day(n):
    return (TODAY + datetime.timedelta(days=n)).isoformat()


CAMPAIGN = """# Kampania: Meta – reklamy statyczne

- stan: w toku
- cel: rozmowy z reklam
- miernik: rozmowy
- cel liczbowy: 40
- kanały: meta ads
- start: {d0}
- koniec: {d60}
- budżet: 12 zł/dzień

## Grupa docelowa
Kierowcy.

## Przekaz
Cena na wierzchu.

## Harmonogram
- [x] Przygotuj reklamę S1: Drzwi od 1 590 zł | kto: codex | kiedy: {d0} | czas: 15
- [ ] Przygotuj reklamę S4: Lepsze audio | kto: codex | kiedy: {d0} | czas: 15
- [ ] Przygotuj reklamę S5: Cennik | kto: codex | kiedy: {d0} | czas: 15
  cel: plansza cennika od 890 zł
- [x] Zatwierdź grafiki i teksty S1, S4 | kto: ty | kiedy: {d0} | czas: 10
- [x] Wgraj S1 do kampanii „Wiadomości – Cisza” | kto: ty | kanał: meta ads | kiedy: {d0} | czas: 20
- [ ] Wgraj B1 do kampanii „Wiadomości – Bon” | kto: ty | kanał: meta ads | kiedy: {d1} | czas: 10
- [ ] Dopisz ceny wygłuszania na stronie | kto: ty | kiedy: {d1} | czas: 15
- [ ] Przegląd Meta za tydzień | kto: ty | kiedy: {d2} | czas: 10 | licznik: rozmowy
- [-] Przygotuj reklamę S2: Zimowe opony | kto: codex | anulowano: {d0} | powód: brak zdjęcia
- [ ] Reklama film F1: Puk w drzwi | kto: ty | kiedy: {d3}
- [ ] Opublikuj post „Drzwi od środka” | kto: ty | kanał: facebook, instagram | kiedy: {d1} | czas: 10
- [ ] Spot o ciszy w aucie | rodzaj: reklama film | kto: ty | kanał: meta ads | kiedy: {d3}
- [ ] Wyślij oferty z Useme | kto: ty | kanał: Useme | kiedy: {d2} | licznik: oferty
- [ ] Notatka dla zespołu | rodzaj: publikacja | kto: ty | kanał: meta ads | kiedy: {d2}

## Wyniki i wnioski
""".format(d0=day(0), d1=day(1), d2=day(2), d3=day(3), d60=day(60))


def rows(text=CAMPAIGN):
    camp, tasks = projekt.parse_campaign(text, "p", "kampanie/meta.md")
    return camp, {t["title"]: t for t in tasks}


class RodzajeWierszy(unittest.TestCase):
    def test_rozpoznanie_i_pole(self):
        camp, T = rows()
        kinds = {k: (t["row"], t["adFormat"], t["adCode"]) for k, t in T.items()}
        self.assertEqual(kinds["Przygotuj reklamę S1: Drzwi od 1 590 zł"], ("reklama", "grafika", "S1"))
        self.assertEqual(kinds["Reklama film F1: Puk w drzwi"], ("reklama", "film", "F1"))
        self.assertEqual(kinds["Spot o ciszy w aucie"], ("reklama", "film", ""))                       # pole rodzaj:
        self.assertEqual(kinds["Notatka dla zespołu"][0], "publikacja")                                 # pole wygrywa
        for title in ("Zatwierdź grafiki i teksty S1, S4", "Wgraj S1 do kampanii „Wiadomości – Cisza”",
                      "Wgraj B1 do kampanii „Wiadomości – Bon”", "Dopisz ceny wygłuszania na stronie",
                      "Wyślij oferty z Useme"):
            self.assertEqual(kinds[title][0], "zadanie", title)
        self.assertEqual(kinds["Przegląd Meta za tydzień"][0], "przegląd")
        self.assertEqual(kinds["Opublikuj post „Drzwi od środka”"][0], "publikacja")
        self.assertEqual(T["Wgraj B1 do kampanii „Wiadomości – Bon”"]["codes"], ["B1"])
        self.assertEqual(T["Zatwierdź grafiki i teksty S1, S4"]["codes"], ["S1", "S4"])
        self.assertFalse(any("wiersz" in g for g in camp["gaps"]), camp["gaps"])

    def test_zly_rodzaj_to_blad_wiersza(self):
        camp, T = rows(CAMPAIGN.replace("rodzaj: publikacja", "rodzaj: ulotka"))
        self.assertTrue(any("rodzaj: ulotka" in g for g in camp["gaps"]), camp["gaps"])
        self.assertEqual(T["Notatka dla zespołu"]["row"], "zadanie")             # bez poprawnego pola: rozpoznanie

    def test_zgodnosc_wstecz_przyklady(self):
        """Dawne kampanie bez pola: wiersze z kanałem zostają publikacjami."""
        files = glob.glob(os.path.join(DASH, "przyklad", "*", "kampanie", "*.md"))
        self.assertTrue(files)
        for f in files:
            with open(f, encoding="utf-8") as fh:
                _, tasks = projekt.parse_campaign(fh.read(), "x", "kampanie/" + os.path.basename(f))
            for t in tasks:
                self.assertEqual(t["row"], "publikacja", (f, t["title"]))
        # zapis pola zostawia „rodzaj:” w wierszu (pole spoza znanych przechodzi bez zmian)
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "kampanie"))
            p = os.path.join(d, "kampanie", "k.md")
            Path(p).write_text("# Kampania: K\n\n## Harmonogram\n- [ ] Spot | rodzaj: reklama film | kto: ty | kiedy: %s\n" % day(1),
                               encoding="utf-8")
            self.assertTrue(projekt.update_task(d, "kampanie/k.md", 4, "Spot", {"date": day(2)}))
            self.assertIn("rodzaj: reklama film", Path(p).read_text(encoding="utf-8"))

    def test_stan_reklam(self):
        camp, T = rows()
        ads = {a["code"] or a["title"]: a for a in camp["ads"]}
        self.assertEqual(ads["S1"]["state"], "w reklamie")            # wgrana
        self.assertEqual(ads["S1"]["price"], "1 590 zł")
        self.assertEqual(ads["S1"]["title"], "Drzwi od 1 590 zł")
        self.assertEqual(ads["S4"]["state"], "zatwierdzona")
        self.assertEqual(ads["S5"]["state"], "do zrobienia")
        self.assertEqual(ads["S5"]["price"], "890 zł")                # z cel:
        self.assertEqual(ads["S2"]["state"], "wyłączona")             # anulowana
        self.assertEqual(ads["F1"]["format"], "film")
        s5 = T["Przygotuj reklamę S5: Cennik"]
        ads2 = projekt.ad_states(list(T.values()), {s5["id"]: True})
        self.assertEqual(next(a for a in ads2 if a["code"] == "S5")["state"], "grafika gotowa")
        done = CAMPAIGN.replace("- [ ] Wgraj B1", "- [x] Wyłącz S1 w Menedżerze | kto: ty | kiedy: %s\n- [ ] Wgraj B1" % day(0))
        self.assertEqual(next(a for a in rows(done)[0]["ads"] if a["code"] == "S1")["state"], "wyłączona")


class NowaKampania(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        Path(self.d, "ZADANIA.md").write_text("# Zadania\n\n## Do rozplanowania\n", encoding="utf-8")
        os.makedirs(os.path.join(self.d, "meta-ads"))
        Path(self.d, "meta-ads", "Styl-reklam-i-zasady.md").write_text("# Styl\n", encoding="utf-8")
        self.body = {"name": "Wygłuszanie samochodu Wrocław", "channels": ["Facebook", "Instagram"], "format": "grafiki",
                     "budget": 15, "start": day(1), "end": day(31), "target": 40, "metric": "rozmowy"}

    def tearDown(self):
        import shutil
        shutil.rmtree(self.d, ignore_errors=True)

    def test_szkic_i_zadanie_agenta(self):
        rel, title = projekt.new_campaign(self.d, self.body, photos_only=True)
        self.assertEqual(rel, "kampanie/wygluszanie-samochodu-wroclaw.md")
        camp, _ = projekt.parse_campaign(Path(self.d, rel).read_text(encoding="utf-8"), "p", rel)
        self.assertEqual((camp["state"], camp["target"], camp["channels"], camp["budget"], camp["format"]),
                         ("plan", 40, ["Facebook", "Instagram"], "15 zł/dzień", "grafiki statyczne"))
        self.assertEqual((camp["start"], camp["end"]), (day(1), day(31)))
        d = projekt.read_project(self.d, "p")
        job = next(t for t in d["tasks"] if t["title"] == title)
        self.assertEqual(title, "Przygotuj plan kampanii „Wygłuszanie samochodu Wrocław”")
        self.assertEqual((job["executor"], job["date"], job["needsYou"], job["file"]), ("agent", TODAY.isoformat(), "odbiór", "ZADANIA.md"))
        self.assertIn("bez $imagegen", job["detail"]["goal"])                       # grafiki: tylko zdjęcia
        self.assertIn("Nie publikuj", job["detail"]["goal"])
        self.assertEqual([r["path"] for r in job["detail"]["refs"]], [rel, "meta-ads/Styl-reklam-i-zasady.md"])
        import agents
        self.assertTrue(agents.photos_only("", job["detail"]["goal"]))
        with self.assertRaises(ValueError):                                          # druga taka sama: odmowa
            projekt.new_campaign(self.d, self.body)

    def test_zle_dane(self):
        for k, v in (("name", "x"), ("channels", []), ("format", "ulotki"), ("budget", 0), ("budget", True),
                     ("end", day(0)), ("target", -1), ("start", "jutro")):
            with self.assertRaises(ValueError, msg=k):
                projekt.new_campaign(self.d, dict(self.body, **{k: v}))
        self.assertFalse(os.path.isdir(os.path.join(self.d, "kampanie")) and os.listdir(os.path.join(self.d, "kampanie")))
        rel, title = projekt.new_campaign(self.d, dict(self.body, target=None, format="oba"))
        self.assertNotIn("bez $imagegen", next(t for t in projekt.read_project(self.d, "p")["tasks"] if t["title"] == title)["detail"]["goal"])


class Serwerowe(Serwer):
    def setUp(self):
        super().setUp()
        Path(self.folder, "kampanie").mkdir(exist_ok=True)
        Path(self.folder, "kampanie", "meta.md").write_text(CAMPAIGN, encoding="utf-8")
        server.data_invalidate()

    def test_zlec_tylko_przy_reklamach_i_publikacjach(self):
        data = self.data()
        T = {t["title"]: t for t in data["tasks"] if t["file"] == "kampanie/meta.md"}
        for title, t in T.items():
            if t["row"] in ("zadanie", "przegląd"):
                self.assertNotIn("missingMaterial", t, title)
        self.assertEqual(T["Przygotuj reklamę S4: Lepsze audio"]["missingMaterial"], "plik grafiki")
        self.assertEqual(T["Opublikuj post „Drzwi od środka”"]["missingMaterial"], "tekst posta")
        self.assertEqual(T["Spot o ciszy w aucie"]["missingMaterial"], "scenariusz filmu")
        with mock.patch.object(self.manager, "run_task", return_value=(200, "", {"id": "x"})) as run:
            step = T["Wgraj B1 do kampanii „Wiadomości – Bon”"]
            code, ans = self.post("/api/post/zlec", {"id": step["id"], "title": step["title"]})
            self.assertEqual(code, 409, ans)
            self.assertIn("po Twojej stronie", ans["error"])
            run.assert_not_called()
            ad = T["Przygotuj reklamę S4: Lepsze audio"]
            code, ans = self.post("/api/post/zlec", {"id": ad["id"], "title": ad["title"]})
            self.assertEqual(code, 200, ans)
            job = next(t for t in self.data()["tasks"] if t["id"] == ans["task"])
            self.assertIn("reklama-s4/grafika.png", job["detail"]["doneWhen"])
        self.assertNotIn("Wgraj B1", Path(self.folder, "ZADANIA.md").read_text(encoding="utf-8"))

    def test_miniatura_reklamy(self):
        post = Path(self.folder, "posty", "%s-reklama-s4" % day(0))
        post.mkdir(parents=True)
        Path(self.folder, "posty", "%s-reklama-s5" % day(0)).mkdir()
        png = b"\x89PNG\r\n\x1a\n" + b"0" * 20
        (post / "grafika.png").write_bytes(png)
        data = self.data()
        camp = next(c for c in data["campaigns"] if c["file"] == "kampanie/meta.md")
        ads = {a["code"]: a for a in camp["ads"]}
        self.assertEqual((ads["S4"]["state"], ads["S4"]["image"]), ("zatwierdzona", True))   # krok „Zatwierdź” ważniejszy
        self.assertEqual((ads["S5"]["state"], ads["S5"]["image"]), ("do zrobienia", False))   # kod rozróżnia foldery
        s4 = next(t for t in data["tasks"] if t["title"].startswith("Przygotuj reklamę S4"))
        self.assertNotIn("missingMaterial", s4)
        import http.client
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=15)
        conn.request("GET", "/api/reklama/grafika?project=%s&date=%s&kod=S4" % (s4["project"], day(0)))
        resp = conn.getresponse()
        self.assertEqual((resp.status, resp.read()), (200, png))
        conn.close()
        self.assertEqual(self.request("GET", "/api/reklama/grafika?project=%s&date=%s&kod=S5" % (s4["project"], day(0)))[0], 404)

    def test_nowa_kampania_przez_api(self):
        Path(self.folder, "KARTA.md").write_text(Path(self.folder, "KARTA.md").read_text(encoding="utf-8")
                                                 .replace("\n## ", "\n- grafiki: tylko zdjęcia\n\n## ", 1), encoding="utf-8")
        pid = self.data()["projects"][0]["id"]
        body = {"project": pid, "name": "Wygłuszanie samochodu Wrocław", "channels": ["Facebook", "Instagram"],
                "format": "oba", "budget": 20, "start": day(1), "end": day(30), "target": 30}
        code, ans = self.post("/api/campaign/new", body)
        self.assertEqual(code, 200, ans)
        data = self.data()
        camp = next(c for c in data["campaigns"] if c["file"] == ans["file"])
        self.assertEqual((camp["state"], camp["target"]), ("plan", 30))
        job = next(t for t in data["tasks"] if t["title"] == ans["task"])
        self.assertEqual((job["executor"], job["needsYou"]), ("agent", "odbiór"))
        self.assertIn("bez $imagegen", job["detail"]["goal"])
        self.assertEqual(self.post("/api/campaign/new", body)[0], 400)                 # ta sama nazwa
        self.assertEqual(self.post("/api/campaign/new", dict(body, project="nie-ma"))[0], 404)


class Automat(Serwer):
    def test_rytm_pomija_kroki_wlasciciela(self):
        import agents
        Path(self.folder, "kampanie").mkdir(exist_ok=True)
        Path(self.folder, "kampanie", "staly-rytm.md").write_text(
            "# Kampania: Stały rytm\n\n- stan: w toku\n\n## Harmonogram\n"
            "- [ ] Wgraj B1 do kampanii „Bon” | kto: ty | kanał: meta ads | kiedy: %s\n"
            "- [ ] Przegląd Meta za tydzień | kto: ty | kanał: facebook | kiedy: %s | licznik: rozmowy\n"
            "- [ ] Opublikuj post „Drzwi” | kto: ty | kanał: facebook | kiedy: %s\n" % (day(1), day(1), day(1)),
            encoding="utf-8")
        data, index = server.load_projects()
        self.assertTrue(self.manager._plan_rhythm(data, index, TODAY))
        titles = [t["title"] for t in projekt.read_project(self.folder, data["projects"][0]["id"])["tasks"]
                  if t["file"] == "ZADANIA.md" and t["title"].startswith(agents.POST_TASK)]
        self.assertEqual(len(titles), 1, titles)
        self.assertIn("Opublikuj post „Drzwi”", titles[0])
        self.assertFalse(agents.material_row({"row": "zadanie"}))
        self.assertTrue(agents.material_row({}))                         # wiersz bez rozpoznania (stare dane)


PAGE = r"""
import json, sys
from playwright.sync_api import sync_playwright
U = sys.argv[1]; out = {}; errs = []
with sync_playwright() as p:
    b = p.chromium.launch()
    for w in (393, 1440):
        ctx = b.new_context(viewport={"width": w, "height": 900}, color_scheme="dark", is_mobile=w < 500, has_touch=w < 500)
        pg = ctx.new_page(); pg.on("pageerror", lambda e: errs.append("%d: %s" % (w, e)))
        r = out[w] = {}
        pg.goto(U + "#p-firmowa-marketing"); pg.wait_for_timeout(900)
        card = pg.locator("section.mk-cc", has_text="Meta – reklamy")
        r["ads"] = card.locator(".mk-ads li:not(.mk-adh) .mk-code").all_inner_texts()
        r["states"] = card.locator(".mk-ads li:not(.mk-adh) .lz").all_inner_texts()
        r["facts"] = card.locator(".mk-facts dt").all_inner_texts()
        r["films"] = card.locator(".mk-fl li").count()
        r["harmOpen"] = card.locator("details.mk-harm").evaluate("e => e.open")
        r["sw1"] = pg.evaluate("document.documentElement.scrollWidth")
        card.locator("details.mk-harm > summary").click(); pg.wait_for_timeout(200)
        lis = card.locator("details.mk-harm > ul.mk-prow > li")
        r["rows"] = [[li.locator(".lk.t").inner_text(), li.locator("[data-mkassign]").count(),
                      li.locator("[data-act=done]").count(), li.locator("form.mk-rev").count()] for li in lis.all()]
        r["sw2"] = pg.evaluate("document.documentElement.scrollWidth")
        pg.locator("[data-mknew]").first.click(); pg.wait_for_timeout(200)
        r["form"] = pg.locator("form.mk-new [data-mknch]").count()
        r["sw3"] = pg.evaluate("document.documentElement.scrollWidth")
        pg.goto(U + "#marketing"); pg.wait_for_timeout(900)
        r["cards"] = pg.locator("#mk-camp .mk-card .t").all_inner_texts()
        r["campFirst"] = pg.evaluate("[...document.querySelectorAll('#view section.panel')].findIndex(s => s.id === 'mk-camp') < [...document.querySelectorAll('#view section.panel')].findIndex(s => s.querySelector('#mk-wkh'))")
        r["weekSteps"] = pg.locator("#view .tl-card", has_text="Wgraj").count()
        pg.locator("#mk-camp [data-mknew]").click(); pg.wait_for_timeout(200)
        r["formV"] = pg.locator("#mk-camp form.mk-new select").count()
        r["sw4"] = pg.evaluate("document.documentElement.scrollWidth")
        ctx.close()
    b.close()
print(json.dumps({"out": out, "errs": errs}, ensure_ascii=False))
"""


@unittest.skipUnless(PW and not os.environ.get("PANEL_TESTY_BEZ_RENDERU"), "brak Playwright albo PANEL_TESTY_BEZ_RENDERU")
class Widok(Duzy):
    def setUp(self):
        super().setUp()
        Path(self.big, "firmowa", "kampanie", "meta.md").write_text(CAMPAIGN, encoding="utf-8")
        server.data_invalidate()

    def test_przeglad_harmonogram_i_marketing(self):
        env = dict(os.environ)
        if not env.get("PLAYWRIGHT_BROWSERS_PATH") and os.path.isdir("/opt/ms-playwright"):
            env["PLAYWRIGHT_BROWSERS_PATH"] = "/opt/ms-playwright"
        r = subprocess.run([PW, "-c", PAGE, "http://127.0.0.1:%d/" % self.port], capture_output=True, text=True,
                           timeout=600, env=env)
        self.assertEqual(r.returncode, 0, r.stderr[-3000:])
        res = json.loads(r.stdout.strip().split("\n")[-1])
        self.assertEqual(res["errs"], [])
        for w, o in res["out"].items():
            w = int(w)
            for k in ("sw1", "sw2", "sw3", "sw4"):
                self.assertLessEqual(o[k], w, (w, k))
            self.assertEqual(o["ads"], ["S1", "S4", "S5", "S2", "F1", "—"], w)        # „Spot”: rodzaj: reklama film, bez kodu
            self.assertEqual(o["states"][:3], ["w reklamie", "zatwierdzona", "do zrobienia"], w)
            self.assertEqual(o["facts"][:3], ["Okres", "Budżet", "Kanały"], w)
            self.assertGreaterEqual(o["films"], 1, w)
            self.assertFalse(o["harmOpen"], w)                                    # harmonogram zwinięty
            R = {t: (zl, done, form) for t, zl, done, form in o["rows"]}
            self.assertEqual(R["Wgraj B1 do kampanii „Wiadomości – Bon”"], (0, 1, 0), w)   # krok: Zrobione, bez Zleć
            self.assertEqual(R["Dopisz ceny wygłuszania na stronie"], (0, 1, 0), w)
            self.assertEqual(R["Przegląd Meta za tydzień"], (0, 0, 1), w)              # przegląd: formularz z liczbą
            self.assertEqual(R["Przygotuj reklamę S4: Lepsze audio"][0], 1, w)         # reklama: Zleć
            self.assertEqual(sum(v[0] for k, v in R.items() if k.startswith(("Wgraj", "Dopisz", "Przegląd", "Wyślij"))), 0, w)
            self.assertEqual(o["form"], 7, w)
            self.assertIn("Meta – reklamy statyczne", o["cards"], w)
            self.assertTrue(o["campFirst"], w)                                    # kampanie nad tygodniem publikacji
            self.assertEqual(o["weekSteps"], 0, w)                                # kroki właściciela poza osią publikacji
            self.assertEqual(o["formV"], 1, w)                                    # w widoku Marketing: wybór projektu


if __name__ == "__main__":
    unittest.main()
