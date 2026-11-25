"""Przebudowa układu panelu według dashboard/WYGLAD.md (zlecenie 2026-11-25 „UI: przebudowa”).

Duży zestaw (dashboard/przyklad-duzy) plus część projektu ze stroną (Portal klienta · Strona WWW). Sprawdza w Chromium:
brak poziomego przewijania 393–1920 px na stronie projektu (Plan, Zadania, Strona), w szczegółach zadania i w Agentach;
zakładki i przełącznik części w jednym wierszu; przycisk Rozmowy nie zasłania treści (bounding box, także nad szufladą
na telefonie); sekcje Planu rozwijane (Dla Ciebie dziś otwarta, reszta zwinięta, stan zapamiętany); „Po terminie” w Planie
= grupa „Po terminie” w Zadaniach = pm.py dla każdego projektu; brak błędów JS.
"""
import json
import os
import subprocess
import sys
import unittest

from test_asystent_duzy import PW, Duzy
from wspolne import projekt, server  # noqa: F401

HERE = os.path.dirname(os.path.abspath(__file__))
DASH = os.path.dirname(HERE)

PART_CARD = """# Karta projektu: Portal klienta – strona WWW

- stan: aktywny
- faza: budowa
- priorytet: 3
- klient: nie
- próg: lekka
- maszyna: chmura
- założono: 2026-09-26
- część projektu: portal
- strona: www

## Cel
Strona informacyjna portalu.
"""
PART_TASKS = """# Zadania: Strona WWW

## Etap: Strona
termin: 2099-12-10

- [ ] Strona: popraw nagłówek na telefonie | kto: claude | kiedy: %s
- [ ] Obejrzyj nową stronę główną | kto: ty | kiedy: %s | czas: 10
"""


def add_part(big):
    import datetime
    d = os.path.join(big, "portal-www")
    os.makedirs(os.path.join(d, "www"))
    today = datetime.date.today().isoformat()
    tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
    with open(os.path.join(d, "KARTA.md"), "w") as f:
        f.write(PART_CARD)
    with open(os.path.join(d, "ZADANIA.md"), "w") as f:
        f.write(PART_TASKS % (tomorrow, today))
    with open(os.path.join(d, "www", "index.html"), "w") as f:
        f.write("<!doctype html><title>Portal</title><h1>Portal</h1>")
    reg = os.path.join(big, "projekty.json")
    with open(reg) as f:
        j = json.load(f)
    j["projekty"].append(d)
    with open(reg, "w") as f:
        json.dump(j, f)


PAGE = r"""
import json, sys
from playwright.sync_api import sync_playwright
U = sys.argv[1]; PIDS = json.loads(sys.argv[2]); TASK = sys.argv[3]
out, errs = {"w": {}, "late": {}}, []
# elementy treści, których przycisk Rozmowy nie może przykrywać (poza samym przyciskiem i otwartym oknem rozmowy)
COVER = '''(() => {
  // przycisk przykryty szufladą (nie na wierzchu w swoim środku) niczego nie zasłania
  const top = b => { const r = b.getBoundingClientRect(), e = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2); return !!e && (e === b || b.contains(e)); };
  const btns = [...document.querySelectorAll('[data-pjd="open"]')].filter(b => b.checkVisibility() && b.getBoundingClientRect().width > 0 && top(b));
  const sel = 'button,a,input,select,textarea,summary,h1,h2,h3,p,li,.lk,.lz,time';
  const els = [...document.querySelectorAll(sel)].filter(e => e.checkVisibility() && !e.closest('#pjdock') && e.getBoundingClientRect().width > 0);
  const hits = [];
  for (const b of btns) { const r = b.getBoundingClientRect();
    for (const e of els) { if (e === b || e.contains(b) || b.contains(e)) continue;
      const q = e.getBoundingClientRect();
      const w = Math.min(r.right, q.right) - Math.max(r.left, q.left), h = Math.min(r.bottom, q.bottom) - Math.max(r.top, q.top);
      if (w > 2 && h > 2) hits.push((e.textContent || e.tagName).trim().slice(0, 40)); } }
  return {n: btns.length, floating: btns.filter(b => b.closest('#pjdock')).length, hits: hits.slice(0, 5)};
})()'''
ONE_ROW = "(s => { const a = [...document.querySelectorAll(s)]; return a.length ? new Set(a.map(e => Math.round(e.getBoundingClientRect().top))).size : 0 })"
with sync_playwright() as p:
    b = p.chromium.launch()
    for w in (393, 768, 1024, 1440, 1920):
        ctx = b.new_context(viewport={"width": w, "height": 852 if w < 500 else 900}, color_scheme="dark", reduced_motion="reduce",
                            is_mobile=w < 500, has_touch=w < 500)
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errs.append("%d: %s" % (w, e)))
        r = out["w"][w] = {}
        def sw(k):
            r[k] = pg.evaluate("document.documentElement.scrollWidth")
        for name, h in (("plan", "#p-portal"), ("tablica", "#p-portal-tablica"), ("strona", "#p-portal-strona?cz=portal-www"),
                        ("agenci", "#agenci"), ("plan2", "#p-shield")):
            pg.goto(U + h); pg.wait_for_timeout(700)
            sw("sw-" + name)
            pg.evaluate("scrollTo(0, 0)"); r["cov0-" + name] = pg.evaluate(COVER)
            pg.evaluate("scrollTo(0, document.documentElement.scrollHeight)"); pg.wait_for_timeout(150)
            r["cov1-" + name] = pg.evaluate(COVER)
            if name != "agenci":
                r["tabRows-" + name] = pg.evaluate(ONE_ROW + "('.ptabs a')")
                r["partRows-" + name] = pg.evaluate(ONE_ROW + "('.pj-parts a')")
        # sekcje Planu: domyślnie Dla Ciebie dziś otwarta, Po terminie / Agenci / Później zwinięte; stan zapamiętany
        pg.goto(U + "#p-shield"); pg.wait_for_timeout(600)
        r["open0"] = pg.evaluate("Object.fromEntries([...document.querySelectorAll('details.psec')].map(d => [d.id, d.open]))")
        pg.locator("#plate > summary").click(); pg.wait_for_timeout(200)
        pg.reload(); pg.wait_for_timeout(700)
        r["lateAfterReload"] = pg.evaluate("document.querySelector('#plate').open")
        r["lateRows"] = pg.locator("#plate .prow > li").count()
        r["lateActs"] = pg.locator("#plate .prow > li .pr-a .btn").count()
        r["lateDue"] = pg.locator("#plate .prow > li .due.late").count()
        r["lateBadges"] = pg.locator("#plate .prow .lz.red").count()
        pg.locator("#plate > summary").click(); pg.wait_for_timeout(200)
        # szczegóły zadania: bez poziomego przewijania, pływający przycisk Rozmowy nie zasłania „Zamknij”
        pg.goto(U + "#p-shield-tablica?z=" + TASK); pg.wait_for_timeout(800)
        r["drawer"] = pg.locator("#drawer .dttl").count()
        sw("sw-drawer"); r["cov-drawer"] = pg.evaluate(COVER)
        ctx.close()
    # liczby: „Po terminie” w Planie = grupa „Po terminie” w Zadaniach, dla każdego projektu
    ctx = b.new_context(viewport={"width": 1440, "height": 900}, color_scheme="dark"); pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append("liczby: %s" % e))
    for pid in PIDS:
        pg.goto(U + "#p-" + pid); pg.wait_for_timeout(500)
        plan = pg.evaluate("(document.querySelector('#plate .cnt')||{textContent:'0'}).textContent")
        today = [pg.evaluate("(document.querySelector('#pplan .cnt')||{textContent:'-1'}).textContent"), pg.locator("#pplan .prow > li").count()]
        pg.goto(U + "#p-" + pid + "-tablica"); pg.wait_for_timeout(500)
        board = pg.evaluate("(document.querySelector('.col.todo .tb-gh.late .tb-gn')||{textContent:'0'}).textContent")
        out["late"][pid] = {"plan": int(plan), "board": int(board), "today": [int(today[0]), today[1]]}
    ctx.close()
    b.close()
print(json.dumps({"out": out, "errs": errs}, ensure_ascii=False))
"""


@unittest.skipUnless(PW and not os.environ.get("PANEL_TESTY_BEZ_RENDERU"), "brak Playwright albo PANEL_TESTY_BEZ_RENDERU")
class Przebudowa(Duzy):
    def setUp(self):
        super().setUp()
        add_part(self.big)
        server.data_invalidate()

    def test_uklad_i_liczby(self):
        data = self.data()
        pids = [p["id"] for p in data["projects"] if not p.get("partOf")]
        task = next(t for t in data["tasks"] if t["project"] == "shield" and t["state"] != "done" and t.get("executor") == "ty")
        env = dict(os.environ)
        if not env.get("PLAYWRIGHT_BROWSERS_PATH") and os.path.isdir("/opt/ms-playwright"):
            env["PLAYWRIGHT_BROWSERS_PATH"] = "/opt/ms-playwright"
        from urllib.parse import quote
        r = subprocess.run([PW, "-c", PAGE, "http://127.0.0.1:%d/" % self.port, json.dumps(pids), quote(task["id"], safe="")],
                           capture_output=True, text=True, timeout=900, env=env)
        self.assertEqual(r.returncode, 0, r.stderr[-3000:])
        res = json.loads(r.stdout.strip().split("\n")[-1])
        self.assertEqual(res["errs"], [])
        for w, o in res["out"]["w"].items():
            w = int(w)
            for k, v in o.items():
                if k.startswith("sw-"):
                    self.assertLessEqual(v, w, (w, k))                                    # bez poziomego przewijania
                if k.startswith("cov"):
                    self.assertEqual(v["hits"], [], (w, k))                               # Rozmowa nie zasłania treści
                if k.startswith("tabRows-") or k.startswith("partRows-"):
                    self.assertLessEqual(v, 1, (w, k))                                    # jeden wiersz, bez zawijania
            for k in ("cov0-plan", "cov0-tablica", "cov0-strona"):
                self.assertEqual((o[k]["n"], o[k]["floating"]), (1, 0), (w, k))         # Rozmowa w nagłówku projektu
            self.assertEqual(o["cov-drawer"]["floating"], 0, w)                           # nad szufladą bez pływającego
            self.assertEqual(o["drawer"], 1, w)
            self.assertEqual(o["open0"].get("pplan"), True, w)
            for sec in ("plate", "pag", "plater"):
                if sec in o["open0"]:
                    self.assertFalse(o["open0"][sec], (w, sec))
            self.assertTrue(o["lateAfterReload"], w)                                      # stan zwinięcia zapamiętany
            self.assertEqual(o["lateRows"], 3, w)
            self.assertEqual((o["lateActs"], o["lateDue"], o["lateBadges"]), (3, 3, 0), w)   # przycisk i jeden znacznik
        # jedno źródło: Plan = Zadania = pm.py (Twoje zadania po terminie, bez publikacji)
        sys.path.insert(0, os.path.join(os.path.dirname(DASH), "standard"))
        import pm
        names = {p["id"]: p["name"] for p in data["projects"]}
        late = pm.facts()["late"]
        tasks = {(t["project"], t["title"]): t for t in data["tasks"]}
        for pid, v in res["out"]["late"].items():
            mine = [x for x in late if x["project"] == names[pid] and x["kind"] != "publikacja"
                    and (x["executor"] == "ty" or x["needsYou"])]
            mine = [x for x in mine if not tasks.get((pid, x["title"]), {}).get("waits")]
            self.assertEqual(v["plan"], v["board"], pid)
            self.assertEqual(v["plan"], len(mine), pid)
            self.assertEqual(v["today"][0], v["today"][1], pid)                           # licznik = wiersze


if __name__ == "__main__":
    unittest.main()
