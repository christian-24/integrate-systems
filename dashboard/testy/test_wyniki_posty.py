"""Etap 2 wyników: automatyczny odczyt postów Facebooka i Instagrama na nagranych odpowiedziach Graph API (bez sieci)."""
import datetime
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
import urllib.parse

TESTY = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(TESTY, ".."))
sys.path.insert(0, os.path.join(TESTY, "..", "..", "standard"))
import projekt  # noqa: E402
import publikacja  # noqa: E402
import wyniki  # noqa: E402

with open(os.path.join(TESTY, "meta-posty.json"), encoding="utf-8") as f:
    REC = json.load(f)
DAY = "2026-11-21"
KAMPANIA = """# Kampania: Stały rytm

- stan: w toku
- kanały: facebook, instagram

## Grupa docelowa
Kierowcy.

## Przekaz
Cisza.

## Harmonogram
- [x] Opublikuj post S1 „Drzwi” | kto: ty | kanał: facebook, instagram | kiedy: %s

## Wyniki i wnioski
""" % DAY


class Graph:
    """Atrapa Graph API z nagranych odpowiedzi; zapisuje wywołania (bez sieci)."""

    def __init__(self):
        self.calls = []
        self.expired = False

    def __call__(self, method, url, headers=None, body=None, timeout=120):
        assert method == "GET", "odczyt wyników nie może nic zmieniać w Meta"
        self.calls.append(url)
        ok = lambda d: (200, {}, json.dumps(d).encode("utf-8"))
        if self.expired:
            return 400, {}, json.dumps(REC["token_wygasl"]).encode("utf-8")
        q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        metric = (q.get("metric") or [""])[0].split(",")
        if "/111_9/insights" in url:
            if any(m in ("post_impressions", "post_impressions_unique") for m in metric):
                return 400, {}, json.dumps(REC["fb_bledna_metryka"]).encode("utf-8")
            return ok({"data": [r for r in REC["fb_insights"]["data"] if r["name"] in metric]})
        if "/111_9?" in url:
            return ok(REC["fb_pola"])
        if "/555/media?" in url:
            return ok(REC["ig_media"])
        if "/m1/insights" in url:
            return ok({"data": [r for r in REC["ig_insights"]["data"] if r["name"] in metric]})
        raise AssertionError(url)


class Posty(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.folder = os.path.join(self.tmp, "projekt")
        self.post = os.path.join(self.folder, "posty", DAY + "-drzwi")
        os.makedirs(os.path.join(self.folder, "kampanie"))
        os.makedirs(self.post)
        with open(os.path.join(self.folder, "kampanie", "staly-rytm.md"), "w", encoding="utf-8") as f:
            f.write(KAMPANIA)
        self.clock = [datetime.datetime(2026, 11, 21, 15, 0)]
        now = lambda: self.clock[0]
        self.api = Graph()
        self.notes = []
        dane = os.path.join(self.tmp, "publikacja")
        self.pub = publikacja.Publisher(self.load, threading.Lock(), projekt, None, None, None, data_dir=dane, now=now)
        self.pub._write("facebook.json", {"appId": "1", "at": "2026-11-20T10:00:00", "pages": [
            {"id": "111", "name": "Shield", "token": "TOKEN-STRONY", "project": "shield",
             "ig": {"id": "555", "username": "shield"}}]})
        self.pub._write("stan.json", {"shield|kampanie/staly-rytm.md|Opublikuj post S1 „Drzwi”": {
            "facebook": {"ok": True, "link": "https://www.facebook.com/111_9", "at": "2026-11-21T09:00:00"},
            "instagram": {"ok": True, "link": "https://www.instagram.com/p/abc/", "at": "2026-11-21T09:01:00"}}})
        self.w = wyniki.Wyniki(self.load, threading.Lock(), projekt, self.post_folder,
                               notify=lambda text, link="": self.notes.append(text), publisher=self.pub,
                               klienci_dir=os.path.join(self.tmp, "klienci"), ads_dir=os.path.join(self.tmp, "reklamy"),
                               http_call=self.api, now=now)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def load(self, resolve=True):
        with open(os.path.join(self.folder, "kampanie", "staly-rytm.md"), encoding="utf-8") as f:
            camp, tasks = projekt.parse_campaign(f.read(), "shield", "kampanie/staly-rytm.md")
        return {"tasks": tasks, "projects": [{"id": "shield", "name": "Shield"}], "campaigns": [camp]}, {"shield": self.folder}

    def post_folder(self, pid, day, index=None, tid=""):
        return self.post if day == DAY else None

    def tick(self):
        self.w.tick()
        return self.load()[0]["tasks"][0]

    def test_liczby_w_wierszu_i_wyniki_json_bez_recznego_wpisu(self):
        t = self.tick()
        self.assertEqual(t["detail"]["views"], 1840 + 910)
        self.assertEqual(t["detail"]["clicks"], 37)
        with open(os.path.join(self.post, "wyniki.json"), encoding="utf-8") as f:
            rec = json.load(f)["kanaly"]
        self.assertEqual(rec["facebook"]["liczby"], {"wyswietlenia": 1840, "zasieg": 1210, "klikniecia": 37,
                                                      "reakcje": 12, "komentarze": 3, "udostepnienia": 2, "interakcje": 17})
        self.assertEqual(rec["instagram"]["liczby"]["zasieg"], 640)
        self.assertEqual(len(rec["facebook"]["odczyty"]), 1)
        self.assertNotIn("TOKEN-STRONY", json.dumps(rec))
        # metryki, których v26 nie zwraca, panel zapamiętuje i pomija
        self.assertEqual(self.w.state()["badMetrics"], ["post_impressions", "post_impressions_unique"])
        # /api/data: znacznik odczytu przy publikacji
        data = self.load()[0]
        self.w.annotate(data)
        self.assertEqual(set(data["tasks"][0]["auto"]), {"facebook", "instagram"})

    def test_rytm_co_6_h_przez_3_dni_potem_raz_dziennie_do_30(self):
        self.tick()
        n = len(self.api.calls)
        self.clock[0] += datetime.timedelta(hours=3)
        self.tick()
        self.assertEqual(len(self.api.calls), n)                 # za wcześnie
        self.clock[0] += datetime.timedelta(hours=4)
        self.tick()
        self.assertGreater(len(self.api.calls), n)               # po 7 h od odczytu
        self.clock[0] = datetime.datetime(2026, 11, 25, 12, 0)    # 4. dzień: raz dziennie
        self.tick()
        n = len(self.api.calls)
        self.clock[0] += datetime.timedelta(hours=7)
        self.tick()
        self.assertEqual(len(self.api.calls), n)
        self.clock[0] += datetime.timedelta(hours=18)
        self.tick()
        self.assertGreater(len(self.api.calls), n)
        self.clock[0] = datetime.datetime(2026, 12, 22, 12, 0)    # po 30 dniach: koniec
        n = len(self.api.calls)
        self.tick()
        self.assertEqual(len(self.api.calls), n)

    def test_blad_jedno_powiadomienie_bez_ponawiania_do_ponownego_polaczenia(self):
        self.api.expired = True
        t = self.tick()
        self.assertEqual(len(self.notes), 2)                     # po jednym na kanał
        self.assertIn("token wygasł", self.notes[0])
        self.assertIsNone(t["detail"]["views"])
        n = len(self.api.calls)
        self.clock[0] += datetime.timedelta(hours=7)
        self.tick()
        self.assertEqual((len(self.api.calls), len(self.notes)), (n, 2))
        self.assertEqual(set(self.w.state()["perm"]), {"facebook", "instagram"})
        # właściciel łączy Facebook ponownie: odczyt rusza
        self.api.expired = False
        fb = self.pub._read("facebook.json", {})
        fb["at"] = "2026-11-21T23:00:00"
        self.pub._write("facebook.json", fb)
        t = self.tick()
        self.assertEqual(t["detail"]["views"], 2750)
        self.assertEqual(self.w.state()["perm"], {})

    def test_link_reczny_z_pfbid_szuka_posta_na_stronie(self):
        kind, oid = wyniki.meta.fb_target("https://www.facebook.com/shield/posts/pfbid02abc")
        self.assertEqual(kind, "szukaj")
        self.assertEqual(wyniki.meta.fb_target("https://www.facebook.com/111/videos/77"), ("video", "77"))
        self.assertEqual(wyniki.meta.fb_target("https://www.facebook.com/reel/88"), ("video", "88"))
        self.assertEqual(wyniki.meta.fb_target("https://www.facebook.com/111_9"), ("post", "111_9"))


from wspolne import Baza, agents as _agents  # noqa: E402

RYTM = """# Kampania: Stały rytm

- stan: w toku
- kanały: facebook

## Grupa docelowa
Kierowcy.

## Przekaz
Cisza.

## Harmonogram
- [x] Post ręczny | kanał: facebook | kiedy: %(d2)s
- [x] Post z odczytem | kanał: facebook | kiedy: %(d)s

## Wyniki i wnioski
"""


class Rytm(Baza):
    """Rytm marketingu nie zakłada „Wpisz wynik publikacji…” dla posta z automatycznymi wynikami (wyniki.json)."""

    def test_bez_zadania_wpisz_wynik(self):
        d = (datetime.date.today() - datetime.timedelta(days=3)).isoformat()
        os.makedirs(os.path.join(self.folder, "kampanie"), exist_ok=True)
        with open(os.path.join(self.folder, "kampanie", "staly-rytm.md"), "w", encoding="utf-8") as f:
            f.write(RYTM % {"d": d, "d2": (datetime.date.today() - datetime.timedelta(days=4)).isoformat()})
        os.makedirs(os.path.join(self.folder, "posty", d + "-odczyt"))
        with open(os.path.join(self.folder, "posty", d + "-odczyt", "wyniki.json"), "w", encoding="utf-8") as f:
            f.write('{"kanaly": {}}')
        m = self.new_manager(PANEL_MACHINE="chmura")
        data, index = m.load_projects()
        m._plan_rhythm(data, index, datetime.date.today())
        titles = [t["title"] for t in m.load_projects()[0]["tasks"] if t["title"].startswith(_agents.RESULT_TASK)]
        self.assertEqual(titles, ["Wpisz wynik publikacji Post ręczny"])


if __name__ == "__main__":
    unittest.main()
