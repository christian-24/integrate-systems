"""Asystent na danych w skali produkcji (zlecenie 2026-11-24 „Asystent na prawdziwych danych”).

Zestaw: dashboard/przyklad-duzy/zbuduj.py (10 projektów, 44 sprawy dla Ciebie, 30 po terminie, długie tytuły, nazwy
z nawiasami, 12 publikacji w tygodniu). Sprawdza: liczby spraw z jednego źródła (projekt.owner_counts = pm.py = /api/data
= menu = karta = listy panelu), karty domyślne bez duplikatów, start scen bez listy, brak poziomego przewijania
390–1920 px i brak błędów JS. Zmiana zestawu = zmiana liczb w EXPECTED.
"""
import importlib.util
import json
import os
import re
import subprocess
import sys
import unittest

from test_serwer import Serwer
from wspolne import projekt, server  # noqa: F401
import karty  # noqa: E402  (ścieżka dashboard/ z wspolne)

HERE = os.path.dirname(os.path.abspath(__file__))
DASH = os.path.dirname(HERE)
PW = next((p for p in ("/home/agent/narzedzia/pw/bin/python",) if os.path.isfile(p)), "")
EXPECTED = {"youToday": 37, "youLate": 30, "youWeek": 4, "youLater": 3}


def build(root):
    spec = importlib.util.spec_from_file_location("zbuduj_duzy", os.path.join(DASH, "przyklad-duzy", "zbuduj.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.build(root)


class Duzy(Serwer):
    def setUp(self):
        super().setUp()
        self.big = build(os.path.join(self.tmp, "duzy"))
        projekt.REGISTRY = os.path.join(self.big, "projekty.json")
        server.data_invalidate()


class JednoZrodlo(Duzy):
    def test_liczby_serwer_i_pm(self):
        data = self.data()
        self.assertEqual(data["projectsSource"], "registry")
        self.assertEqual(len(data["projects"]), 10)
        self.assertEqual({k: data[k] for k in EXPECTED}, EXPECTED)
        sys.path.insert(0, os.path.join(os.path.dirname(DASH), "standard"))
        import pm
        counts = pm.facts()["counts"]
        self.assertEqual({k: counts[k] for k in EXPECTED}, EXPECTED)          # raport PM = panel
        self.assertEqual(counts["late"], data["late"])
        facts = self.manager.assistant_facts(*self._loaded(), {k: data[k] for k in projekt.OWNER_COUNT_KEYS})
        self.assertIn("sprawy dla Ciebie na dziś: 37, w tym po terminie: 30", facts)   # rozmowa = panel
        self.assertIn("sprawy dla Ciebie na dziś: 37, w tym po terminie: 30",
                      self.manager.assistant_facts(*self._loaded()))                   # bez /api/data: to samo
        pubs = [t for t in data["tasks"] if t["kind"] == "publikacja" and t["state"] != "done"]
        self.assertEqual(len(pubs), 12)
        self.assertTrue(any(len(t["title"]) >= 100 for t in data["tasks"]))
        self.assertTrue(all("(" in p["name"] for p in data["projects"]))

    def _loaded(self):
        import datetime
        data, _ = server.load_projects()
        return data, datetime.date.today()


class KartyDomyslne(unittest.TestCase):
    def test_bez_duplikatow(self):
        ids = [c["id"] for c in karty.STARTERS]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(karty.START, ("sprawy-dzis", "publikacje-tygodnia", "postep-projektow", "raport-pm"))
        self.assertFalse(set(karty.ALIASES) & set(karty.START))
        for old in ("dzis-dla-ciebie", "po-terminie"):
            self.assertNotIn(old, ids)
            self.assertEqual(karty.ALIASES[old], "sprawy-dzis")
        titles = [c["tytul"] for c in karty.STARTERS]
        self.assertEqual(len(titles), len(set(titles)))
        # jedna karta publikacji (tydzień) i jedna spraw na starcie
        pubs = [c for c in karty.STARTERS if (c.get("zapytanie") or {}).get("zrodlo") == "publikacje"]
        self.assertEqual([c["id"] for c in pubs], ["publikacje-tygodnia"])


PAGE = r"""
import json, sys
from playwright.sync_api import sync_playwright
U = sys.argv[1]
out, errs = {}, []
with sync_playwright() as p:
    b = p.chromium.launch()
    for w in (390, 768, 1024, 1440, 1920):
        for theme in ("dark", "light"):
            ctx = b.new_context(viewport={"width": w, "height": 900}, color_scheme=theme, reduced_motion="reduce")
            pg = ctx.new_page()
            pg.on("pageerror", lambda e: errs.append("%d %s: %s" % (w, theme, e)))
            r = out["%d-%s" % (w, theme)] = {}
            pg.goto(U + "#asystent"); pg.wait_for_selector(".as-today"); pg.wait_for_timeout(400)
            r["start"] = pg.locator(".as-start").inner_text()
            r["startLists"] = pg.locator(".as-home ul, .as-home .ap-card, .as-home .rows").count()
            r["chips"] = pg.locator(".as-chips .as-sug").count()
            r["chipTops"] = pg.evaluate("[...new Set([...document.querySelectorAll('.as-chips .as-sug')].map(e=>Math.round(e.getBoundingClientRect().top)))].length")
            r["sw0"] = pg.evaluate("document.documentElement.scrollWidth")
            r["badge"] = pg.evaluate("(document.querySelector('#nav a[href=\"#asystent\"] .count')||document.querySelector('#bnav a[href=\"#asystent\"] .count')||{}).textContent||''")
            r["badgeTitle"] = pg.evaluate("(document.querySelector('#nav a[href=\"#asystent\"] .count')||{title:''}).title||''")
            r["pjd"] = pg.locator(".pjd-btn").count()
            pg.locator(".as-today").click(); pg.wait_for_timeout(900)
            r["todayScene"] = pg.locator(".as-scene").count()
            r["sw1"] = pg.evaluate("document.documentElement.scrollWidth")
            pg.locator('[data-asmode="karty"]').first.click(); pg.wait_for_timeout(800)
            r["cards"] = pg.locator(".ap-cv .ap-card h2").all_inner_texts()
            r["sum"] = pg.locator(".ap-card[data-cid='sprawy-dzis'] .ap-sum").inner_text()
            r["youState"] = [int(x) for x in pg.locator(".ap-card[data-cid='sprawy-dzis'] .ap-sum").get_attribute("data-lists").split(",")]
            r["rows"] = pg.locator(".ap-card[data-cid='sprawy-dzis'] .ap-today>li").count()
            r["src"] = pg.locator(".ap-cv .ap-src").count()
            r["quick"] = pg.locator(".ap-quick").count()
            r["sw2"] = pg.evaluate("document.documentElement.scrollWidth")
            r["holes"] = pg.evaluate('''(()=>{const c=[...document.querySelectorAll('.ap-cv>.ap-card')];const rows={};
              c.forEach(e=>{const t=Math.round(e.getBoundingClientRect().top);rows[t]=(rows[t]||0)+e.getBoundingClientRect().width});
              const W=document.querySelector('.ap-cv').getBoundingClientRect().width;return Object.values(rows).filter(v=>v<W-40).length})()''')
            pg.locator(".ap-card[data-cid='sprawy-dzis'] [data-apfull]").first.click(); pg.wait_for_timeout(500)
            r["drawer"] = pg.locator("#drawer .ap-full").count()
            ctx.close()
    b.close()
print(json.dumps({"out": out, "errs": errs}, ensure_ascii=False))
"""


@unittest.skipUnless(PW and not os.environ.get("PANEL_TESTY_BEZ_RENDERU"), "brak Playwright albo PANEL_TESTY_BEZ_RENDERU")
class Przegladarka(Duzy):
    """Chromium na dużym zestawie: 390–1920 px, oba motywy."""

    def test_wyglad_i_liczby(self):
        data = self.data()
        env = dict(os.environ)
        if not env.get("PLAYWRIGHT_BROWSERS_PATH") and os.path.isdir("/opt/ms-playwright"):
            env["PLAYWRIGHT_BROWSERS_PATH"] = "/opt/ms-playwright"
        r = subprocess.run([PW, "-c", PAGE, "http://127.0.0.1:%d/" % self.port], capture_output=True, text=True,
                           timeout=600, env=env)
        self.assertEqual(r.returncode, 0, r.stderr[-3000:])
        res = json.loads(r.stdout.strip().split("\n")[-1])
        self.assertEqual(res["errs"], [])
        for k, o in res["out"].items():
            w = int(k.split("-")[0])
            for sw in ("sw0", "sw1", "sw2"):
                self.assertLessEqual(o[sw], w, (k, sw))                          # bez poziomego przewijania
            self.assertEqual(o["youState"], [37, 30, 4, 3], k)                   # listy panelu = fakty
            self.assertEqual(re.search(r"\d+", o["badge"]).group(0), str(data["youToday"]), k)   # menu = fakty
            self.assertIn("37", o["start"]); self.assertIn("30 po terminie", o["start"])
            self.assertEqual(o["startLists"], 0, k)                              # start scen bez listy
            self.assertLessEqual(o["chips"], 4, k)
            if w >= 1440:
                self.assertEqual(o["chipTops"], 1, k)                            # podpowiedzi w jednym rzędzie
                self.assertIn("w tym po terminie: 30", o["badgeTitle"])
            self.assertEqual(o["pjd"], 0, k)                                     # bez drugiego czatu
            self.assertEqual(o["todayScene"], 1, k)
            self.assertEqual(len(o["cards"]), len(set(o["cards"])), k)           # bez duplikatów kart
            self.assertEqual(o["cards"][:3], ["Sprawy dla Ciebie", "Publikacje w tym tygodniu", "Postęp projektów"], k)
            self.assertTrue(o["sum"].startswith("Dziś 37"), o["sum"])            # karta = fakty
            self.assertIn("w tym 30 po terminie", o["sum"])
            self.assertEqual(o["rows"], 5, k)                                    # najwyżej 5 + „i N więcej”
            self.assertEqual((o["quick"], o["holes"], o["drawer"]), (0, 0, 1), k)


if __name__ == "__main__":
    unittest.main()
