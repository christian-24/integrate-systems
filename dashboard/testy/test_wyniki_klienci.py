"""Etap 1 wyników: dziennik klientów (klienci.py) poza repozytorium, import CSV, podsumowania, licznik kampanii."""
import datetime
import json
import os
import stat
import unittest

from test_serwer import Serwer
from wspolne import TESTY, server

import klienci  # noqa: E402

TODAY = datetime.date.today()
KAMPANIA = """# Kampania: Reklamy listopad

- stan: w toku
- cel: zapytania z reklam
- miernik: zapytania z reklam
- cel liczbowy: 10
- wynik: 1
- kanały: facebook
- start: %s
- koniec: %s
- budżet: 300 zł

## Grupa docelowa
Kierowcy.

## Przekaz
Cisza w aucie.

## Harmonogram
- [ ] Opublikuj post S1 „Drzwi” | kto: ty | kanał: facebook | kiedy: %s

## Wyniki i wnioski
""" % ((TODAY - datetime.timedelta(days=10)).isoformat(), (TODAY + datetime.timedelta(days=10)).isoformat(),
       TODAY.isoformat())


class Dziennik(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.dir = tempfile.mkdtemp()
        self.k = klienci.Klienci(self.dir, now=lambda: datetime.datetime(2026, 11, 25, 10, 0))

    def test_zapis_0600_poza_repo(self):
        code, err, extra = self.k.add("shield", {"data": "2026-11-24", "auto": "Skoda Octavia", "zrodlo": "Meta – reklama",
                                                 "kod": "S1", "usluga": "Drzwi", "wycena": "1 590 zł"})
        self.assertEqual(code, 200, err)
        path = os.path.join(self.dir, "shield.json")
        self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)
        self.assertEqual(extra["entry"]["wycena"], 1590)
        self.assertIsNone(extra["entry"]["umowiony"])
        repo = os.path.realpath(os.path.join(TESTY, "..", ".."))
        self.assertFalse(os.path.realpath(path).startswith(repo))

    def test_bez_telefonu_i_ze_zrodlem_z_listy(self):
        self.assertEqual(self.k.add("p", {"auto": "Audi 600 100 200", "zrodlo": "Inne"})[0], 400)
        self.assertEqual(self.k.add("p", {"auto": "Audi", "zrodlo": "Gazeta"})[0], 400)
        self.assertEqual(self.k.add("p", {"auto": "Audi", "zrodlo": "Inne", "wycena": "dużo"})[0], 400)

    def test_zmiana_wykonane_i_usuniecie(self):
        eid = self.k.add("p", {"auto": "BMW", "zrodlo": "Google Ads"})[2]["entry"]["id"]
        self.assertEqual(self.k.update("p", {"id": eid, "wykonane": "4200,50"})[0], 200)
        e = self.k.entries("p")[0]
        self.assertEqual((e["wykonane"], e["umowiony"], e["auto"]), (4200.5, True, "BMW"))
        self.assertEqual(self.k.update("p", {"id": eid, "umowiony": "nie"})[0], 200)
        self.assertFalse(self.k.entries("p")[0]["umowiony"])
        self.assertEqual(self.k.update("p", {"id": eid, "usun": True})[0], 200)
        self.assertEqual(self.k.entries("p"), [])
        self.assertEqual(self.k.update("p", {"id": eid})[0], 404)

    def test_import_przykladowego_csv(self):
        with open(os.path.join(TESTY, "klienci-przyklad.csv"), encoding="utf-8") as f:
            text = f.read()
        code, err, extra = self.k.import_csv("p", text)
        self.assertEqual(code, 200, err)
        self.assertEqual(extra["dodane"], 4)
        self.assertEqual(extra["pominiete"], 2)              # powtórzony wiersz i zła data
        self.assertTrue(extra["bledy"][0].startswith("wiersz 7"))
        L = self.k.entries("p")
        self.assertEqual([e["zrodlo"] for e in L], ["Meta – reklama", "Google Ads", "Polecenie", "Instagram"])
        self.assertEqual(L[1]["wycena"], 4200)
        self.assertEqual(L[2]["wycena"], 1290)
        self.assertFalse(any("telefon" in e or "—" in json.dumps(e, ensure_ascii=False) for e in L))
        # drugi import tego samego pliku nie dubluje wpisów
        self.assertEqual(self.k.import_csv("p", text)[2]["dodane"], 0)

    def test_podsumowanie_tydzien_start_zrodla(self):
        for d, src, kod, done in (("2026-11-24", "Meta – reklama", "S1", 1590), ("2026-11-23", "Instagram", "", None),
                                  ("2026-11-10", "Google Ads", "", 4200), ("2026-10-01", "Polecenie", "", 900)):
            self.k.add("p", {"data": d, "auto": "X", "zrodlo": src, "kod": kod, "wykonane": done})
        s = klienci.summarize(self.k.entries("p"), "2026-11-25", "2026-11-01")
        self.assertEqual(s["tydzien"], {"zapytania": 2, "umowieni": 1, "wykonane": 1, "przychod": 1590, "wycena": 0})
        self.assertEqual((s["odStartu"]["zapytania"], s["odStartu"]["wykonane"], s["odStartu"]["przychod"]), (3, 2, 5790))
        self.assertEqual({z["zrodlo"]: z["zapytania"] for z in s["zrodla"]},
                         {"Meta – reklama": 1, "Instagram": 1, "Google Ads": 1})
        self.assertEqual(klienci.ad_inquiries(self.k.entries("p"), "2026-11-01", "2026-11-30"), 2)


class Api(Serwer):
    def setUp(self):
        super().setUp()
        self._env_k = os.environ.get("PANEL_KLIENCI_DIR")
        os.environ["PANEL_KLIENCI_DIR"] = os.path.join(self.tmp, "klienci")
        server._wyniki["obj"] = None
        os.makedirs(os.path.join(self.folder, "kampanie"), exist_ok=True)
        with open(os.path.join(self.folder, "kampanie", "reklamy.md"), "w", encoding="utf-8") as f:
            f.write(KAMPANIA)
        self.pid = next(p["id"] for p in self.data()["projects"])

    def tearDown(self):
        server._wyniki["obj"] = None
        if self._env_k is None:
            os.environ.pop("PANEL_KLIENCI_DIR", None)
        else:
            os.environ["PANEL_KLIENCI_DIR"] = self._env_k
        super().tearDown()

    def test_wpis_z_telefonu_i_licznik_kampanii(self):
        camp = lambda: next(c for c in self.data()["campaigns"] if c["name"] == "Reklamy listopad")
        self.assertEqual(camp()["result"], 1)                      # ręczny wynik, brak wpisów
        for body in ({"auto": "Skoda", "zrodlo": "Meta – reklama", "kod": "S1"},
                     {"auto": "Audi", "zrodlo": "Google Ads"},
                     {"auto": "VW", "zrodlo": "Instagram", "kod": "post 20.11"},
                     {"auto": "Opel", "zrodlo": "Polecenie"}):
            status, ans = self.post("/api/klienci/dodaj", dict(body, project=self.pid))
            self.assertEqual(status, 200, ans)
        c = camp()
        self.assertEqual((c["result"], c["counters"]["zapytania z reklam"]), (3, 3))
        status, _, text = self.request("GET", "/api/klienci?project=" + self.pid)
        view = json.loads(text)
        self.assertEqual(view["summary"]["odStartu"]["zapytania"], 4)
        self.assertIn("S1", [c["kod"] for c in view["codes"]])
        # dane klientów nie są w /api/data
        self.assertNotIn("Skoda", json.dumps(self.data(), ensure_ascii=False))
        self.assertEqual(self.post("/api/klienci/dodaj", {"project": "nie-ma", "zrodlo": "Inne"})[0], 404)

    def test_import_przez_api(self):
        with open(os.path.join(TESTY, "klienci-przyklad.csv"), encoding="utf-8") as f:
            status, ans = self.post("/api/klienci/import", {"project": self.pid, "csv": f.read()})
        self.assertEqual((status, ans["dodane"]), (200, 4))


if __name__ == "__main__":
    unittest.main()
