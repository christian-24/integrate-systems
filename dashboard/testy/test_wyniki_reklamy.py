"""Etap 3 wyników: reklamy Meta (Marketing API, tylko odczyt) na nagranej odpowiedzi insights, sumy i alerty."""
import datetime
import json
import os
import stat
import threading
import unittest
import urllib.parse

from wspolne import Baza, TESTY, projekt, server

import publikacja  # noqa: E402
import wyniki  # noqa: E402

with open(os.path.join(TESTY, "meta-reklamy.json"), encoding="utf-8") as f:
    REC = json.load(f)
NOW = datetime.datetime(2026, 11, 25, 7, 0)
TOKEN = "TOKEN-SYSTEMOWY-" + "x" * 30
KAMPANIA = """# Kampania: Rozmowy listopad

- stan: w toku
- cel: rozmowy
- miernik: zapytania z reklam
- cel liczbowy: 20
- start: 2026-11-10
- koniec: 2026-12-10

## Grupa docelowa
Kierowcy.

## Przekaz
Cisza.

## Harmonogram
- [ ] Opublikuj post S1 „Drzwi” | kto: ty | kanał: facebook | kiedy: 2026-11-28

## Wyniki i wnioski
"""


class Marketing:
    """Atrapa Marketing API z nagranych odpowiedzi; tylko GET."""

    def __init__(self):
        self.calls = []

    def __call__(self, method, url, headers=None, body=None, timeout=120):
        assert method == "GET", "panel nie może zmieniać reklam"
        self.calls.append(url)
        ok = lambda d: (200, {}, json.dumps(d).encode("utf-8"))
        q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        if "/me/adaccounts" in url:
            return ok(REC["konta"])
        if "/act_123456/insights" in url:
            if "after" in q:
                return ok(REC["strona2"])
            if "time_increment" not in q:
                return ok(REC["ostatnie7"])
            return ok(REC["strona1"])
        raise AssertionError(url)


class Reklamy(Baza):
    def setUp(self):
        super().setUp()
        os.makedirs(os.path.join(self.folder, "kampanie"), exist_ok=True)
        with open(os.path.join(self.folder, "kampanie", "rozmowy.md"), "w", encoding="utf-8") as f:
            f.write(KAMPANIA)
        self.api = Marketing()
        self.notes = []
        self.pub = publikacja.Publisher(server.load_projects, server._write_lock, projekt, None, None, None,
                                        data_dir=os.path.join(self.tmp, "publikacja"), now=lambda: NOW)
        self.w = wyniki.Wyniki(server.load_projects, server._write_lock, projekt, None,
                               notify=lambda text, link="": self.notes.append(text), publisher=self.pub,
                               klienci_dir=os.path.join(self.tmp, "klienci"), ads_dir=os.path.join(self.tmp, "reklamy"),
                               http_call=self.api, now=lambda: NOW)
        self.pid = server.load_projects()[0]["projects"][0]["id"]

    def connect(self):
        code, err, extra = self.w.connect_meta({"token": TOKEN, "rodzaj": "system"})
        self.assertEqual(code, 200, err)
        self.assertEqual([a["id"] for a in extra["accounts"]], ["act_123456", "act_777888"])
        self.assertEqual(self.w.meta_assign({"project": self.pid, "act": "act_123456"})[0], 200)

    def sync(self):
        data, index = server.load_projects()
        self.w.meta_tick(data, index)

    def test_sumy_z_dwoch_stron_i_zapis_poza_repo(self):
        self.connect()
        self.sync()
        path = os.path.join(self.tmp, "reklamy", self.pid + ".json")
        self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)
        rows = self.w.ads(self.pid)["meta"]["rows"]
        self.assertEqual(len(rows), 18)
        # zapytanie od startu kampanii (2026-11-10) do wczoraj
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.api.calls[1]).query)
        self.assertEqual(json.loads(q["time_range"][0]), {"since": "2026-11-10", "until": "2026-11-24"})
        by = {}
        for r in rows:
            b = by.setdefault(r["kod"] or "bez kodu", [0, 0])
            b[0] += r["wydano"]
            b[1] += r["rozmowy"]
        self.assertEqual(by, {"S1": [75.0, 0], "F2": [90.0, 1], "B1": [62.5, 10], "bez kodu": [5.0, 0]})
        self.assertEqual(wyniki.meta.ad_code("B1 - Bagażnik cicho"), "B1")
        self.assertEqual(wyniki.meta.ad_code("Reklama testowa listopad"), "")
        # token nie trafia do zapisu reklam ani do /api/data
        with open(path, encoding="utf-8") as f:
            self.assertNotIn(TOKEN, f.read())
        out = server.load_projects()[0]
        self.w.annotate(out)
        self.assertNotIn(TOKEN, json.dumps(out, ensure_ascii=False))
        self.assertEqual(out["wyniki"]["projects"][self.pid]["metaAct"], "act_123456")
        # drugi odczyt tego samego dnia: nic (raz dziennie)
        n = len(self.api.calls)
        self.sync()
        self.assertEqual(len(self.api.calls), n)

    def test_alerty_jako_zadania_wlasciciela_raz_na_tydzien(self):
        self.connect()
        self.sync()
        tasks = {t["title"]: t for t in server.load_projects()[0]["tasks"] if t["project"] == self.pid}
        made = sorted(t for t in tasks if t.startswith(("Wyłącz", "Wymień", "Odśwież")))
        self.assertEqual(made, ["Odśwież grafikę B1", "Wymień reklamę F2", "Wyłącz reklamę S1: 0 rozmów za 60 zł"])
        t = tasks["Wymień reklamę F2"]
        self.assertEqual((t["executor"], t["date"], t["minutes"], t["campaignFile"]),
                         ("ty", "2026-11-25", 5, "kampanie/rozmowy.md"))
        self.assertIn("koszt rozmowy 70 zł", t["detail"]["goal"])
        with open(os.path.join(self.folder, "ZADANIA.md"), encoding="utf-8") as f:
            self.assertIn("- [ ] Wymień reklamę F2 | kto: ty | kiedy: 2026-11-25 | czas: 5 | kampania: kampanie/rozmowy.md\n"
                          "  cel: koszt rozmowy 70 zł", f.read())
        # ponownie w tym tygodniu (nawet po zamknięciu zadania): bez nowych zadań
        data, index = server.load_projects()
        self.assertEqual(self.w.meta_alerts(self.pid, index[self.pid], data), [])

    def test_progi_z_karty(self):
        with open(os.path.join(self.folder, "KARTA.md"), encoding="utf-8") as f:
            text = f.read()
        lines = text.split("\n")
        at = next(i for i, l in enumerate(lines) if l.startswith("- "))
        lines.insert(at, "- meta progi: 80; 100; 4")
        with open(os.path.join(self.folder, "KARTA.md"), "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        self.connect()
        self.sync()
        titles = [t["title"] for t in server.load_projects()[0]["tasks"] if t["title"].startswith(("Wyłącz", "Wymień", "Odśwież"))]
        self.assertEqual(titles, [])

    def test_widok_wyniki_sumy_i_wskazniki(self):
        self.connect()
        self.sync()
        for body in ({"data": "2026-11-23", "auto": "Skoda", "zrodlo": "Meta – reklama", "kod": "S1", "wykonane": 1590},
                     {"data": "2026-11-24", "auto": "Audi", "zrodlo": "Meta – reklama", "kod": "f2", "umowiony": "tak", "wykonane": 900},
                     {"data": "2026-11-24", "auto": "VW", "zrodlo": "Meta – reklama", "kod": "F2"},
                     {"data": "2026-11-24", "auto": "Opel", "zrodlo": "Polecenie", "wykonane": 500}):
            self.assertEqual(self.w.klienci.add(self.pid, body)[0], 200)
        rep = self.w.report(self.pid, "30")
        by = {r["kod"]: r for r in rep["rows"]}
        self.assertEqual([r["kod"] for r in rep["rows"]][:2], ["S1", "F2"])          # po przychodzie
        s1 = by["S1"]
        self.assertEqual((s1["wydano"], s1["rozmowy"], s1["wykonane"], s1["przychod"], s1["kosztKlienta"], s1["zwrot"],
                          s1["kosztRozmowy"]), (75.0, 0, 1, 1590.0, 75.0, 21.2, None))
        f2 = by["F2"]
        self.assertEqual((f2["wydano"], f2["rozmowy"], f2["kosztRozmowy"], f2["zapytania"], f2["umowieni"], f2["wykonane"]),
                         (90.0, 1, 90.0, 2, 1, 1))
        self.assertEqual(rep["bezKodu"], [{"nazwa": "Reklama testowa listopad", "wydano": 5.0}])
        self.assertEqual(rep["sum"]["wydano"], 232.5)
        self.assertEqual(rep["sum"]["przychod"], 2990.0)                            # z klientem bez kodu
        self.assertEqual(rep["bezKoduKlienci"]["przychod"], 500.0)
        # 7 dni: od 2026-11-19
        self.assertEqual(self.w.report(self.pid, "7")["rows"][0]["wydano"], 75.0)
        self.assertEqual(by["F2"]["kanal"], "Meta")
        hist = self.w.history(self.pid, "F2")
        self.assertEqual((len(hist), hist[-2]), (9, {"data": "2026-11-23", "wydano": 10.0, "rozmowy": 1, "wyswietlenia": 500}))  # wyświetlenia do osi publikacji
        self.assertEqual(self.w.month(self.pid), {"przychod": 2990.0, "wydatek": 232.5})
        # raport PM: te same liczby kampanii (klienci.marketing_numbers, pm.py --json)
        import klienci
        m = klienci.marketing_numbers(self.pid, "2026-11-10", "2026-12-10", os.path.join(self.tmp, "klienci"),
                                      os.path.join(self.tmp, "reklamy"))
        self.assertEqual(m, {"inquiries": 4, "adInquiries": 3, "done": 3, "revenue": 2990.0, "adSpend": 232.5,
                             "revenuePerZl": 12.86})
        self.assertIsNone(klienci.marketing_numbers("brak", klienci_dir=os.path.join(self.tmp, "klienci"),
                                                    ads_dir=os.path.join(self.tmp, "reklamy")))

    def test_konto_jednego_projektu_i_token_tymczasowy(self):
        self.assertEqual(self.w.connect_meta({"token": "krótki"})[0], 400)
        code, _, extra = self.w.connect_meta({"token": TOKEN, "rodzaj": "tymczasowy"})
        self.assertEqual(extra["expiresAt"][:10], "2027-01-24")
        self.assertEqual(self.w.meta_assign({"project": self.pid, "act": "act_999"})[0], 409)
        conns = {"inny": {"metaAct": "act_123456"}}
        self.pub._write("polaczenia.json", conns)
        self.assertEqual(self.w.meta_assign({"project": self.pid, "act": "act_123456"})[0], 409)


if __name__ == "__main__":
    unittest.main()
