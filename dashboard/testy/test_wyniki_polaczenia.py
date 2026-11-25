"""Etap 5 wyników: połączenia projektu (Meta, LinkedIn, Google Ads), skrypt Google Ads z kluczem projektu, izolacja projektów."""
import datetime
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest

from test_serwer import Serwer
from wspolne import TESTY, projekt, quiet, server

import wyniki  # noqa: E402

NODE = shutil.which("node")
ADS = os.path.join(TESTY, "google-ads-przyklad.json")
ENV = ("PANEL_PUBLIKACJA_DIR", "PANEL_REKLAMY_DIR", "PANEL_KLIENCI_DIR", "PANEL_PUBLIC_URL")


class Polaczenia(Serwer):
    def setUp(self):
        super().setUp()
        self._env = {k: os.environ.get(k) for k in ENV}
        os.environ.update({"PANEL_PUBLIKACJA_DIR": os.path.join(self.tmp, "publikacja"),
                           "PANEL_REKLAMY_DIR": os.path.join(self.tmp, "reklamy"),
                           "PANEL_KLIENCI_DIR": os.path.join(self.tmp, "klienci"),
                           "PANEL_PUBLIC_URL": "https://panel.example"})
        self._pub, self._wy = server._publisher, dict(server._wyniki)
        server._publisher = None
        server._wyniki["obj"] = None
        self.folder2 = os.path.join(self.tmp, "drugi-projekt")
        quiet(projekt.cmd_nowy, self.folder2, "Drugi projekt", register=True)
        ids = [p["id"] for p in self.data()["projects"]]
        self.a, self.b = ids[0], ids[1]

    def tearDown(self):
        server._publisher = self._pub
        server._wyniki.clear()
        server._wyniki.update(self._wy)
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        super().tearDown()

    def key_for(self, pid, customer):
        self.assertEqual(self.post("/api/wyniki/polaczenie", {"project": pid, "googleKlient": customer})[0], 200)
        status, ans = self.post("/api/wyniki/google/klucz", {"project": pid})
        self.assertEqual(status, 200, ans)
        script = ans["skrypt"]
        key = re.search(r"var KLUCZ = '([^']+)'", script).group(1)
        self.assertIn("var PANEL = 'https://panel.example/api/wyniki/google-ads'", script)
        return key, script

    def ingest(self, key, body):
        return self.request("POST", "/api/wyniki/google-ads", body=body,
                            headers={"X-Klucz-Projektu": key, "X-Forwarded-For": "203.0.113.9"})

    def payload(self, script):
        """Skrypt z panelu uruchomiony w node na atrapie AdsApp: ciało, które wysłałby do panelu."""
        path = os.path.join(self.tmp, "skrypt.js")
        with open(path, "w", encoding="utf-8") as f:
            f.write(script)
        out = json.loads(subprocess.run([NODE, os.path.join(TESTY, "atrapa_google_ads.js"), path, ADS], check=True,
                                        capture_output=True, text=True, timeout=30).stdout)
        self.assertEqual(out["mutating"], [])                    # skrypt tylko czyta (same SELECT)
        self.assertEqual(len(out["sent"]), 1)
        return out["sent"][0]

    @unittest.skipUnless(NODE, "brak node")
    def test_skrypt_z_panelu_daje_poprawne_sumy(self):
        key, script = self.key_for(self.a, "434-771-1860")
        sent = self.payload(script)
        self.assertEqual((sent["headers"]["X-Klucz-Projektu"], sent["contentType"]), (key, "application/json"))
        body = sent["body"]
        drzwi = next(r for r in body["wiersze"] if r["grupa"] == "Drzwi")
        self.assertEqual((drzwi["koszt"], drzwi["konwersje"], drzwi["telefony"]), (96.5, 3, 2))
        status, _, text = self.ingest(key, body)
        self.assertEqual(status, 200, text)
        rep = self.request("GET", "/api/wyniki?project=%s&okres=30" % self.a)[2]
        rows = {r["kod"]: r for r in json.loads(rep)["rows"]}
        self.assertEqual((rows["G · Wygłuszanie"]["wydano"], rows["G · Wygłuszanie"]["rozmowy"],
                          rows["G · Wygłuszanie"]["wyswietlenia"], rows["G · Wygłuszanie"]["interakcje"]), (127.7, 3, 1800, 63))
        self.assertEqual(rows["G · Marka"]["wydano"], 6.0)
        # klient z kodem kampanii Google łączy się z wydatkiem
        day = body["dzien"]
        self.post("/api/klienci/dodaj", {"project": self.a, "data": day, "auto": "BMW", "zrodlo": "Google Ads",
                                         "kod": "G · Wygłuszanie", "wykonane": "4200"})
        r = {x["kod"]: x for x in json.loads(self.request("GET", "/api/wyniki?project=%s" % self.a)[2])["rows"]}["G · Wygłuszanie"]
        self.assertEqual((r["przychod"], r["kosztKlienta"], r["zwrot"]), (4200.0, 127.7, 32.89))
        # ponowne wysłanie tego samego dnia nie dubluje
        self.ingest(key, body)
        r = {x["kod"]: x for x in json.loads(self.request("GET", "/api/wyniki?project=%s" % self.a)[2])["rows"]}["G · Wygłuszanie"]
        self.assertEqual(r["wydano"], 127.7)
        # alert hasła: 23,50 zł bez konwersji > 20 zł
        titles = [t["title"] for t in self.data()["tasks"] if t["project"] == self.a]
        self.assertIn("Wyklucz hasło „mata wygłuszająca allegro” w G · Wygłuszanie", titles)
        self.assertIn("Google Ads: wklej skrypt z panelu i ustaw „codziennie”", titles)

    def test_zly_klucz_403_bez_szczegolow(self):
        key, _ = self.key_for(self.a, "434-771-1860")
        body = {"konto": "434-771-1860", "dzien": "2026-11-24", "wiersze": [], "hasla": []}
        for bad in ("", "gk_" + "x" * 32, key[:-1] + ("A" if key[-1] != "A" else "B")):
            status, _, text = self.ingest(bad, body)
            self.assertEqual((status, text), (403, "Odmowa."))
        self.assertEqual(self.ingest(key, body)[0], 200)
        # konto z innego projektu niż klucz: odrzucone
        self.assertEqual(self.ingest(key, dict(body, konto="111-222-3333"))[0], 400)
        # za duże ciało
        big = dict(body, hasla=[{"haslo": "x" * 100, "koszt": 1}] * 6000)
        try:
            self.assertIn(self.ingest(key, big)[0], (400, 413))
        except (BrokenPipeError, ConnectionResetError):
            pass                                                 # serwer zrywa połączenie przed końcem wysyłki
        # unieważnienie
        self.assertEqual(self.post("/api/wyniki/google/uniewaznij", {"project": self.a})[0], 200)
        self.assertEqual(self.ingest(key, body)[0], 403)
        # klucz nie jest zapisany jawnie ani w /api/data
        with open(os.path.join(self.tmp, "publikacja", "polaczenia.json"), encoding="utf-8") as f:
            self.assertNotIn(key, f.read())
        self.assertNotIn(key, json.dumps(self.data()))

    def test_dwa_projekty_nie_widza_swoich_danych(self):
        ka, _ = self.key_for(self.a, "434-771-1860")
        kb, _ = self.key_for(self.b, "555-666-7777")
        self.assertNotEqual(ka, kb)
        row = lambda c: {"kampania": c, "grupa": "g", "wyswietlenia": 10, "klikniecia": 1, "koszt": 5, "konwersje": 0}
        self.assertEqual(self.ingest(ka, {"konto": "434-771-1860", "dzien": "2026-11-24", "wiersze": [row("Tylko A")]})[0], 200)
        self.assertEqual(self.ingest(kb, {"konto": "555-666-7777", "dzien": "2026-11-24", "wiersze": [row("Tylko B")]})[0], 200)
        self.post("/api/klienci/dodaj", {"project": self.a, "auto": "Skoda", "zrodlo": "Polecenie", "wykonane": 100})
        ra = json.loads(self.request("GET", "/api/wyniki?project=%s&okres=start" % self.a)[2])
        rb = json.loads(self.request("GET", "/api/wyniki?project=%s&okres=start" % self.b)[2])
        self.assertEqual([r["kod"] for r in ra["rows"]], ["G · Tylko A"])
        self.assertEqual([r["kod"] for r in rb["rows"]], ["G · Tylko B"])
        self.assertEqual((ra["sum"]["przychod"], rb["sum"]["przychod"]), (100.0, 0.0))
        self.assertEqual(json.loads(self.request("GET", "/api/klienci?project=%s" % self.b)[2])["entries"], [])
        # projekt bez połączenia: „brak połączenia”, bez błędu
        os.environ["PANEL_REKLAMY_DIR"] = os.path.join(self.tmp, "pusto")
        server._wyniki["obj"] = None
        rep = json.loads(self.request("GET", "/api/wyniki?project=%s" % self.b)[2])
        self.assertEqual((rep["rows"], rep["polaczenia"]["meta"]), ([], False))

    def test_linkedin_bez_api_stan_wniosku_i_wpis_reczny(self):
        body = {"project": self.a, "linkedin": {"rodzaj": "organizacja", "organizacja": "12345678", "wniosek": "złożony"}}
        self.assertEqual(self.post("/api/wyniki/polaczenie", body)[0], 200)
        st = self.data()["wyniki"]["projects"][self.a]["linkedin"]
        self.assertEqual((st["rodzaj"], st["wniosek"]), ("organizacja", "złożony"))
        titles = [t["title"] for t in self.data()["tasks"] if t["project"] == self.a]
        self.assertIn("LinkedIn: wniosek o Community Management API", titles)
        self.assertEqual(self.post("/api/wyniki/polaczenie", {"project": self.a, "linkedin": {"rodzaj": "organizacja"}})[0], 400)
        self.assertEqual(self.post("/api/wyniki/polaczenie", {"project": self.a, "googleKlient": "123"})[0], 400)


class LinkedIn(unittest.TestCase):
    """Odczyt statystyk strony firmowej po zgodzie LinkedIn i przypomnienie o tokenie (atrapa API, bez sieci)."""

    def setUp(self):
        import threading
        import publikacja
        self.tmp = tempfile.mkdtemp()
        self.folder = os.path.join(self.tmp, "projekt")
        os.makedirs(os.path.join(self.folder, "kampanie"))
        with open(os.path.join(self.folder, "ZADANIA.md"), "w", encoding="utf-8") as f:
            f.write("# Zadania: P\n\n## Etap: Jeden\n\n- [ ] A\n\n## Do rozplanowania\n")
        with open(os.path.join(self.folder, "kampanie", "li.md"), "w", encoding="utf-8") as f:
            f.write("# Kampania: LI\n\n- stan: w toku\n\n## Harmonogram\n- [x] Opublikuj post L1 „Firma” | kanał: linkedin"
                    " | kiedy: 2026-11-24\n  link: https://www.linkedin.com/feed/update/urn:li:share:7001/\n")
        self.now = datetime.datetime(2026, 11, 25, 12, 0)
        self.calls = []
        pub = publikacja.Publisher(self.load, threading.Lock(), projekt, None, None, None,
                                   data_dir=os.path.join(self.tmp, "pub"), now=lambda: self.now)
        pub._write("linkedin.json", {"token": "LI" * 20, "sub": "x", "expiresAt": "2026-11-30T10:00:00"})
        pub._write("polaczenia.json", {"p": {"linkedin": {"rodzaj": "organizacja", "organizacja": "999",
                                                          "wniosek": "przyznany"}}})
        self.w = wyniki.Wyniki(self.load, threading.Lock(), projekt, None, publisher=pub,
                               klienci_dir=os.path.join(self.tmp, "k"), ads_dir=os.path.join(self.tmp, "r"),
                               http_call=self.api, now=lambda: self.now)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def api(self, method, url, headers=None, body=None, timeout=120):
        self.calls.append(url)
        assert method == "GET" and "organizationalEntityShareStatistics" in url and "shares=List(urn%3Ali%3Ashare%3A7001)" in url
        return 200, {}, json.dumps({"elements": [{"totalShareStatistics": {
            "impressionCount": 830, "uniqueImpressionsCount": 512, "clickCount": 22, "likeCount": 14, "commentCount": 2,
            "shareCount": 1, "engagement": 0.047}}]}).encode("utf-8")

    def load(self, resolve=True):
        d = projekt.read_project(self.folder, "p")
        return {"tasks": d["tasks"], "projects": [d["project"]], "campaigns": d["campaigns"]}, {"p": self.folder}

    def test_statystyki_strony_i_przypomnienie(self):
        self.w.tick()
        t = next(x for x in self.load()[0]["tasks"] if x["kind"] == "publikacja")
        self.assertEqual((t["detail"]["views"], t["detail"]["clicks"]), (830, 22))
        titles = [x["title"] for x in self.load()[0]["tasks"]]
        self.assertIn("Odnów token LinkedIn (wygasa 30.11)", titles)
        self.w.tick()
        self.assertEqual(sum(1 for x in self.load()[0]["tasks"] if x["title"].startswith("Odnów token")), 1)


if __name__ == "__main__":
    unittest.main()
