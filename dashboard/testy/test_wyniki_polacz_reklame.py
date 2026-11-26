"""Oś publikacji: połączenie pozycji „reklama Meta” z istniejącą reklamą konta (GET /api/wyniki/reklamy-api, pole link:)."""
import datetime
import json
import os
import re
import unittest
import urllib.parse

from wspolne import Baza, TESTY, projekt, server

import publikacja  # noqa: E402
import wyniki  # noqa: E402

with open(os.path.join(TESTY, "meta-reklamy.json"), encoding="utf-8") as f:
    REC = json.load(f)
NOW = datetime.datetime(2026, 11, 25, 7, 0)
TOKEN = "TOKEN-SYSTEMOWY-" + "x" * 30
HTML = open(os.path.join(TESTY, "..", "panel.html"), encoding="utf-8").read()
KAMPANIA = """# Kampania: Rozmowy listopad

- stan: w toku
- cel: rozmowy
- start: 2026-11-10
- koniec: 2026-12-10

## Harmonogram
- [x] Przygotuj reklamę K1 „Podłoga” | kto: ty | kanał: meta | kiedy: 2026-11-16
- [ ] Przygotuj reklamę K2 „Bagażnik” | kto: ty | kanał: meta | kiedy: 2026-11-20

## Wyniki i wnioski
"""
ADS = {"data": [
    {"id": "602", "name": "F2 · Wygłuszenie podłogi", "effective_status": "ACTIVE", "created_time": "2026-11-15T10:00:00+0100",
     "campaign": {"name": "Rozmowy listopad"}, "creative": {"thumbnail_url": "https://scontent.example/602.jpg", "title": "Cisza", "body": "Mata"}},
    {"id": "603", "name": "B1 - Bagażnik cicho", "effective_status": "CAMPAIGN_PAUSED", "created_time": "2026-11-19T10:00:00+0100",
     "creative": {"thumbnail_url": "javascript:alert(1)"}},
    {"id": "999", "name": "Stara reklama", "effective_status": "PAUSED", "created_time": "2026-09-01T10:00:00+0100"}]}
OLD = {"id": "999", "name": "Stara reklama", "effective_status": "PAUSED",
       "insights": {"data": [{"spend": "40.50", "impressions": "3000", "reach": "2100", "clicks": "33",
                              "actions": [{"action_type": wyniki.meta.CONVERSATION, "value": "2"}]}]}}


class Marketing:
    """Atrapa Marketing API: tylko GET."""

    def __init__(self):
        self.calls, self.deny = [], False

    def __call__(self, method, url, headers=None, body=None, timeout=120):
        assert method == "GET", "panel nie może zmieniać reklam"
        self.calls.append(url)
        ok = lambda d: (200, {}, json.dumps(d).encode("utf-8"))
        u = urllib.parse.urlparse(url)
        q = urllib.parse.parse_qs(u.query)
        if "/me/adaccounts" in url:
            return ok(REC["konta"])
        if u.path.endswith("/act_123456/ads"):
            if self.deny:
                return 400, {}, json.dumps({"error": {"code": 200, "message": "Requires ads_read permission"}}).encode()
            self.ads_q = q
            return ok(ADS)
        if "/act_123456/insights" in url:
            if "after" in q:
                return ok(REC["strona2"])
            if "time_increment" not in q:
                return ok(REC["ostatnie7"])
            return ok(REC["strona1"])
        if u.path.endswith("/999"):
            return ok(OLD)
        raise AssertionError(url)


class PolaczReklame(Baza):
    def setUp(self):
        super().setUp()
        os.makedirs(os.path.join(self.folder, "kampanie"), exist_ok=True)
        with open(os.path.join(self.folder, "kampanie", "rozmowy.md"), "w", encoding="utf-8") as f:
            f.write(KAMPANIA)
        self.api = Marketing()
        self.pub = publikacja.Publisher(server.load_projects, server._write_lock, projekt, None, None, None,
                                        data_dir=os.path.join(self.tmp, "publikacja"), now=lambda: NOW)
        self.w = wyniki.Wyniki(server.load_projects, server._write_lock, projekt, None, publisher=self.pub,
                               klienci_dir=os.path.join(self.tmp, "klienci"), ads_dir=os.path.join(self.tmp, "reklamy"),
                               http_call=self.api, now=lambda: NOW)
        self.pid = server.load_projects()[0]["projects"][0]["id"]

    def connect(self, sync=True):
        self.assertEqual(self.w.connect_meta({"token": TOKEN, "rodzaj": "system"})[0], 200)
        self.assertEqual(self.w.meta_assign({"project": self.pid, "act": "act_123456"})[0], 200)
        if sync:
            data, index = server.load_projects()
            self.w.meta_tick(data, index)

    def task(self, start):
        return next(t for t in server.load_projects()[0]["tasks"] if t["title"].startswith(start))

    def link(self, start, value):
        t = self.task(start)
        return server.update_detail({"id": t["id"], "title": t["title"], "key": "link", "value": value})

    def get(self, path):
        return self.w.api_get(path, {"project": [self.pid]})

    def test_lista_reklam_bez_konta_i_z_kontem(self):
        code, out = self.get("/api/wyniki/reklamy-api")
        self.assertEqual(code, 409)
        self.assertIn("konta reklamowego Meta", out["error"])
        self.assertEqual(self.w.api_get("/api/wyniki/reklamy-api", {"project": ["brak"]})[0], 404)
        self.connect(sync=False)
        code, out = self.get("/api/wyniki/reklamy-api")
        self.assertEqual(code, 200, out)
        self.assertEqual(out["konto"], "act_123456")
        self.assertEqual([x["id"] for x in out["reklamy"]], ["603", "602", "999"])          # najnowsze pierwsze
        a = out["reklamy"][1]
        self.assertEqual((a["nazwa"], a["stan"], a["data"], a["kampania"], a["miniatura"]),
                         ("F2 · Wygłuszenie podłogi", "aktywna", "2026-11-15", "Rozmowy listopad", "https://scontent.example/602.jpg"))
        self.assertEqual(out["reklamy"][0]["stan"], "kampania wstrzymana")
        self.assertEqual(out["reklamy"][0]["miniatura"], "")                               # tylko https
        self.assertEqual(wyniki.meta.ad_link_id(a["link"]), "602")
        self.assertTrue(a["link"].startswith("https://adsmanager.facebook.com/adsmanager/manage/ads?act=123456&"))
        self.assertEqual(self.api.ads_q["limit"], ["50"])
        self.assertIn("creative{thumbnail_url,title,body}", self.api.ads_q["fields"][0])
        self.assertNotIn(TOKEN, json.dumps(out))

    def test_brak_uprawnienia(self):
        self.connect(sync=False)
        self.api.deny = True
        code, out = self.get("/api/wyniki/reklamy-api")
        self.assertEqual(code, 409)
        self.assertIn("ads_read", out["error"])
        self.assertNotIn(TOKEN, out["error"])

    def test_polacz_wyniki_i_odlacz(self):
        self.connect()
        _, ads = self.get("/api/wyniki/reklamy-api")
        f2 = next(x for x in ads["reklamy"] if x["id"] == "602")
        self.assertEqual(self.link("Przygotuj reklamę K1", f2["link"]), (200, ""))
        with open(os.path.join(self.folder, "kampanie", "rozmowy.md"), encoding="utf-8") as f:
            self.assertIn("  link: https://adsmanager.facebook.com/adsmanager/manage/ads?act=123456&selected_ad_ids=602", f.read())
        t = self.task("Przygotuj reklamę K1")
        self.assertEqual(wyniki.meta.ad_link_id(t["detail"]["link"]), "602")
        # oś: wyniki reklamy 602 po id (dzienne wiersze odczytu, bez nowego zapytania do Meta)
        n = len(self.api.calls)
        code, os_ = self.get("/api/wyniki/os")
        self.assertEqual(code, 200)
        a = os_["reklamyId"]["602"]
        self.assertEqual((a["nazwa"], a["wydano"], a["rozmowy"], len(a["dni"])), ("F2 · Wygłuszenie podłogi", 90.0, 1, 9))
        self.assertEqual(a["wyswietlenia"], sum(d["wyswietlenia"] for d in a["dni"]))
        self.assertGreater(a["klikniecia"], 0)
        self.assertEqual(len(self.api.calls), n)
        # lista pokazuje, z czym reklama jest już połączona
        _, ads = self.get("/api/wyniki/reklamy-api")
        self.assertTrue(next(x for x in ads["reklamy"] if x["id"] == "602")["polaczona"].startswith("Przygotuj reklamę K1"))
        # Statystyki: wiersz reklamy pod kodem pozycji, nie pod kodem z nazwy i nie jako post
        rep = self.w.report(self.pid, "30")
        by = {r["kod"]: r for r in rep["rows"]}
        self.assertNotIn("F2", by)
        self.assertEqual((by["K1"]["rodzaj"], by["K1"]["kanal"], by["K1"]["wydano"], by["K1"]["tytul"]),
                         ("reklama", "Meta", 90.0, "F2 · Wygłuszenie podłogi"))
        self.assertEqual(rep["sum"]["wydano"], 232.5)
        # link reklamy to nie post: bez odczytu organicznego
        self.assertFalse([x for x in self.w.organic_targets(server.load_projects()[0]) if x[0]["title"].startswith("Przygotuj reklamę")])
        # odłącz: pusty link usuwa pole
        self.assertEqual(self.link("Przygotuj reklamę K1", ""), (200, ""))
        self.assertEqual(self.task("Przygotuj reklamę K1")["detail"].get("link") or "", "")
        self.assertEqual(self.get("/api/wyniki/os")[1]["reklamyId"], {})
        self.assertIn("F2", {r["kod"] for r in self.w.report(self.pid, "30")["rows"]})

    def test_reklama_bez_wierszy_odczyt_z_api_raz_na_6_godzin(self):
        self.connect()
        self.assertEqual(self.link("Przygotuj reklamę K2", wyniki.meta.ad_link("act_123456", "999")), (200, ""))
        a = self.get("/api/wyniki/os")[1]["reklamyId"]["999"]
        self.assertEqual((a["nazwa"], a["stan"], a["wydano"], a["wyswietlenia"], a["klikniecia"], a["rozmowy"]),
                         ("Stara reklama", "wstrzymana", 40.5, 3000, 33, 2))
        calls = [c for c in self.api.calls if urllib.parse.urlparse(c).path.endswith("/999")]
        self.assertEqual(len(calls), 1)
        self.assertIn("insights.date_preset(maximum)", urllib.parse.unquote(calls[0]))
        self.get("/api/wyniki/os")
        self.assertEqual(len([c for c in self.api.calls if urllib.parse.urlparse(c).path.endswith("/999")]), 1)
        with open(os.path.join(self.tmp, "reklamy", "reklamy-polaczone.json"), encoding="utf-8") as f:
            self.assertNotIn(TOKEN, f.read())

    def test_link_reklamy(self):
        self.assertEqual(wyniki.meta.ad_link_id("https://adsmanager.facebook.com/adsmanager/manage/ads?act=1&selected_ad_ids=120200001"), "120200001")
        self.assertEqual(wyniki.meta.ad_link_id("https://www.facebook.com/123/posts/456"), "")
        self.assertEqual(wyniki.meta.ad_link_id("https://adsmanager.facebook.com.zly.pl/adsmanager/manage/ads?selected_ad_ids=1"), "")


class Interfejs(unittest.TestCase):
    def fn(self, name):
        m = re.search(r"\nfunction " + name + r"\(.*?\n}\n", HTML, re.S)
        return m.group(0) if m else ""

    def test_przyciski_i_wybor(self):
        self.assertIn("osAdPicker()", self.fn("osView"))
        body = self.fn("osModal")
        for txt in ("Połącz z reklamą", "Odłącz", "data-osadpick", "data-osadunlink", "Połączona reklama", "Otwórz w Menedżerze reklam"):
            self.assertIn(txt, body)
        pick = self.fn("osAdPicker")
        self.assertIn("/api/wyniki/reklamy-api", pick)
        for k in ("x.miniatura", "x.nazwa", "x.stan", "x.data"):
            self.assertIn(k, pick)
        self.assertIn("reklamyId", self.fn("osStats"))
        self.assertIn('"/api/wyniki/reklamy-api"', open(os.path.join(TESTY, "..", "wyniki.py"), encoding="utf-8").read())


if __name__ == "__main__":
    unittest.main()
