"""Stały rytm postów: zadanie przygotowania posta z wyprzedzeniem i podgląd posta w panelu."""
import datetime
import http.client
import json
import os
import unittest

import agents
from test_serwer import Serwer
from wspolne import Baza, projekt

KAMPANIA = """# Kampania: Stały rytm

- stan: w toku
- kanały: facebook, linkedin

## Harmonogram

%s
"""


class Rytm(Baza):
    def setUp(self):
        super().setUp()
        self.pid = os.path.basename(self.folder)
        self.m = self.new_manager(PANEL_RYTM="%s=2,nie-ma=3,zly=x" % self.pid, PANEL_MACHINE="cloud")

    def kampania(self, rows=""):
        os.makedirs(os.path.join(self.folder, "kampanie"), exist_ok=True)
        with open(os.path.join(self.folder, "kampanie", "staly-rytm.md"), "w", encoding="utf-8") as f:
            f.write(KAMPANIA % rows)

    def plan(self, today):
        data, index = self.m.load_projects()
        return self.m._plan_posts(data, index, today)

    def posts(self):
        return [t for t in self.m.load_projects()[0]["tasks"] if t["title"].startswith(agents.POST_TASK)]

    def test_termin_kolejnego_posta(self):
        d = datetime.date(2026, 11, 18)
        self.assertEqual(agents.next_post_slot([], 2, d), datetime.date(2026, 11, 19))
        self.assertEqual(agents.next_post_slot([datetime.date(2026, 11, 18)], 2, d), datetime.date(2026, 11, 20))
        self.assertEqual(agents.next_post_slot([datetime.date(2026, 11, 1)], 3, d), datetime.date(2026, 11, 19))
        self.assertEqual(self.m.rytm, {self.pid: 2, "nie-ma": 3})

    def test_zadanie_raz_i_z_wyprzedzeniem(self):
        self.kampania("- [ ] Post A | kanał: facebook | kiedy: 2026-11-18 | wymaga: zgoda")
        self.assertTrue(self.plan(datetime.date(2026, 11, 18)))
        [t] = self.posts()
        self.assertEqual(t["title"], agents.POST_TASK + "2026-11-20 (stały rytm)")
        self.assertEqual((t["executor"], t["machine"], t["date"]), ("claude", "cloud", "2026-11-18"))
        self.assertFalse(self.plan(datetime.date(2026, 11, 18)))           # nie dubluje otwartego zadania
        self.assertEqual(len(self.posts()), 1)

    def test_za_wczesnie_i_bez_kampanii(self):
        self.assertFalse(self.plan(datetime.date(2026, 11, 18)))           # brak pliku kampanii
        self.kampania("- [ ] Post A | kanał: facebook | kiedy: 2026-11-25")
        self.assertFalse(self.plan(datetime.date(2026, 11, 18)))           # kolejny termin 27.11, za daleko
        self.assertEqual(self.posts(), [])


class Podglad(Serwer):
    def setUp(self):
        super().setUp()
        self.pid = os.path.basename(self.folder)
        d = os.path.join(self.folder, "posty", "2026-11-20-generator-dziala")
        os.makedirs(d)
        with open(os.path.join(d, "post.md"), "w", encoding="utf-8") as f:
            f.write("# Generator działa\n\n## Facebook\nTekst FB\n\n## LinkedIn\nTekst LI\ndrugi wiersz\n\n## Alt\nOpis grafiki\n")
        with open(os.path.join(d, "grafika.png"), "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\nkoniec")

    def test_tekst_i_grafika(self):
        status, _, text = self.request("GET", "/api/post?project=%s&date=2026-11-20" % self.pid)
        self.assertEqual(status, 200)
        d = json.loads(text)
        self.assertEqual(d["title"], "Generator działa")
        self.assertEqual(d["sections"]["LinkedIn"], "Tekst LI\ndrugi wiersz")
        self.assertTrue(d["image"])
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=15)
        conn.request("GET", "/api/post/grafika?project=%s&date=2026-11-20" % self.pid)
        resp = conn.getresponse()
        self.assertEqual((resp.status, resp.getheader("Content-Type"), resp.read()[:4]), (200, "image/png", b"\x89PNG"))
        conn.close()

    def test_odmowy(self):
        for q in ("project=%s&date=2026-11-21" % self.pid, "project=nie-ma&date=2026-11-20",
                  "project=%s&date=../../x" % self.pid, "project=%s&date=" % self.pid):
            self.assertEqual(self.request("GET", "/api/post?" + q)[0], 404, q)


if __name__ == "__main__":
    unittest.main()
