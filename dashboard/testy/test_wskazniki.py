"""Wskaźniki pracy agentów (grupa „wskazniki”, 2026-11-25).

Duży zestaw (dashboard/przyklad-duzy) z częścią ze stroną (Portal klienta · Strona WWW) i atrapą pracujących agentów
podstawioną w odpowiedzi /api/data (route w Playwright). Sprawdza w Chromium: kropkę i „pracuje” / „2 agentów” przy
projekcie w menu (także w arkuszu „Więcej” na telefonie), licznik pracujących przy Agentach, wiersz „… pracuje: zadanie ·
krok · Pokaż” pod nazwą projektu, kropkę na właściwej zakładce (Strona / Marketing / Zadania), brak wskaźników bez pracy
i po jej końcu (odświeżanie na żywo), brak pulsowania przy prefers-reduced-motion, brak poziomego przewijania 393–1440 px
i brak błędów JS.
"""
import json
import os
import subprocess
import unittest

from test_asystent_duzy import PW, Duzy
from test_ui_przebudowa import add_part
from wspolne import server

PAGE = r"""
import datetime, json, sys
from playwright.sync_api import sync_playwright
U = sys.argv[1]
now = datetime.datetime.now().astimezone()
iso = lambda m: (now - datetime.timedelta(minutes=m)).isoformat(timespec="seconds")
# kolejność jak w agents.runs: najnowsze najpierw (pierwsze w Shield: Claude z planem)
RUNS = [
    ("r-ws-1", "claude", "running", "shield|ZADANIA.md|18", 25, "Edytuje raport-testow.md",
     [{"text": "Zebrać wyniki testów", "done": True}, {"text": "Opisać wyniki w raporcie", "active": True}, {"text": "Sprawdzić odnośniki"}]),
    ("r-ws-2", "codex", "running", "shield|ZADANIA.md|19", 30, "Uruchamia testy: npm test", []),
    ("r-ws-3", "claude", "running", "portal-www|ZADANIA.md|6", 3, "Czyta www/index.html", []),
    ("r-ws-4", "claude", "running", "jesien|kampanie/publikacje-testowe.md|12", 12, "Pisze tekst posta", []),
    ("r-ws-5", "codex", "queued", "czesci|ZADANIA.md|26", 2, "", []),
]
S = {"work": True}
def inject(route):
    resp = route.fetch(); j = resp.json()
    if S["work"]:
        tasks = {t["id"]: t for t in j["tasks"]}
        for rid, tool, state, tid, ago, act, plan in RUNS:
            t = tasks[tid]; t["runId"] = rid
            j["agents"]["runs"].append({"id": rid, "kind": "task", "tool": tool, "state": state, "title": t["title"],
                "project": t["project"], "projectName": "", "taskId": t["id"], "file": t["file"], "queuedAt": iso(ago + 1),
                "startedAt": iso(ago) if state == "running" else None, "endedAt": None, "activity": act, "plan": plan, "steps": []})
    route.fulfill(response=resp, json=j)
TABS = "[...document.querySelectorAll('.ptabs a')].filter(a => a.querySelector('.ws-dot')).map(a => a.getAttribute('href').split('?')[0])"
SIDE = "Object.fromEntries([...document.querySelectorAll('#plist a')].filter(a => a.querySelector('.ws-b')).map(a => [a.getAttribute('href').split('?')[0], [...a.querySelector('.ws-b').childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join('')]))"
out, errs = {"w": {}}, []
with sync_playwright() as p:
    b = p.chromium.launch()
    for w in (393, 768, 1024, 1440):
        ctx = b.new_context(viewport={"width": w, "height": 852 if w < 500 else 900}, color_scheme="dark",
                            is_mobile=w < 500, has_touch=w < 500)
        pg = ctx.new_page(); pg.route("**/api/data", inject)
        pg.on("pageerror", lambda e: errs.append("%d: %s" % (w, e)))
        r = out["w"][w] = {}
        for name, h in (("shield", "#p-shield"), ("jesien", "#p-jesien"), ("portal", "#p-portal"),
                        ("www", "#p-portal-strona?cz=portal-www"), ("mobilna", "#p-mobilna")):
            pg.goto(U + h); pg.wait_for_timeout(700)
            r["sw-" + name] = pg.evaluate("document.documentElement.scrollWidth")
            r["tabs-" + name] = pg.evaluate(TABS)
            r["row-" + name] = pg.evaluate("(document.querySelector('#view .ws-row')||{innerText:''}).innerText")
        if w == 1440:
            r["side"] = pg.evaluate(SIDE)
            r["sideTitle"] = pg.evaluate("document.querySelector('#plist a[href=\"#p-shield\"]').title")
            r["ag"] = pg.evaluate("(a => a ? [(a.querySelector('[aria-hidden]') || a).textContent, a.className, a.title] : null)(document.querySelector('#nav a[href=\"#agenci\"] .count'))")
            r["anim"] = pg.evaluate("getComputedStyle(document.querySelector('#plist .ws-dot')).animationName")
            pg.goto(U + "#p-shield"); pg.wait_for_timeout(600)
            r["show"] = pg.evaluate("(document.querySelector('#view .ws-row [data-run]')||{dataset:{}}).dataset.run||''")
            pg.click("#view .ws-row [data-run]"); pg.wait_for_timeout(500)
            r["drawer"] = pg.evaluate("(d => !!d && d.checkVisibility() && d.getBoundingClientRect().width > 0)(document.querySelector('#drawer'))")
            # koniec pracy: następne odpytanie (co 3 s, gdy coś trwa) zdejmuje wskaźniki bez przeładowania strony
            pg.keyboard.press("Escape"); pg.goto(U + "#p-shield"); pg.wait_for_timeout(500)
            S["work"] = False; pg.wait_for_timeout(4500)
            r["after"] = {"dots": pg.locator(".ws-dot").count(), "row": pg.locator(".ws-row").count(),
                          "ag": pg.locator("#nav a[href='#agenci'] .count").count(), "side": pg.evaluate(SIDE)}
            S["work"] = True
        if w == 393:
            pg.goto(U + "#asystent"); pg.wait_for_timeout(600)
            r["bnag"] = pg.evaluate("(document.querySelector('#bnav a[href=\"#agenci\"] .count')||{textContent:''}).textContent")
            pg.click("[data-bnmore]"); pg.wait_for_timeout(300)
            r["sheet"] = pg.evaluate("[...document.querySelectorAll('#bnsheet a')].filter(a => a.querySelector('.ws-b')).map(a => a.getAttribute('href').split('?')[0])")
            r["sw-sheet"] = pg.evaluate("document.documentElement.scrollWidth")
        ctx.close()
    # prefers-reduced-motion: kropka bez pulsowania
    ctx = b.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="reduce"); pg = ctx.new_page(); pg.route("**/api/data", inject)
    pg.goto(U + "#p-shield"); pg.wait_for_timeout(700)
    out["reduced"] = pg.evaluate("[...document.querySelectorAll('.ws-dot')].map(d => getComputedStyle(d).animationName)")
    out["reducedCnt"] = pg.evaluate("getComputedStyle(document.querySelector('#nav .count.ws-live'), '::before').animationName")
    ctx.close()
    b.close()
print(json.dumps({"out": out, "errs": errs}, ensure_ascii=False))
"""


@unittest.skipUnless(PW and not os.environ.get("PANEL_TESTY_BEZ_RENDERU"), "brak Playwright albo PANEL_TESTY_BEZ_RENDERU")
class Wskazniki(Duzy):
    def setUp(self):
        super().setUp()
        add_part(self.big)
        server.data_invalidate()

    def test_wskazniki_pracy(self):
        data = self.data()
        ids = {t["id"] for t in data["tasks"]}
        for tid in ("shield|ZADANIA.md|18", "shield|ZADANIA.md|19", "portal-www|ZADANIA.md|6",
                    "jesien|kampanie/publikacje-testowe.md|12", "czesci|ZADANIA.md|26"):
            self.assertIn(tid, ids)                                                       # atrapa trafia w zadania zestawu
        env = dict(os.environ)
        if not env.get("PLAYWRIGHT_BROWSERS_PATH") and os.path.isdir("/opt/ms-playwright"):
            env["PLAYWRIGHT_BROWSERS_PATH"] = "/opt/ms-playwright"
        r = subprocess.run([PW, "-c", PAGE, "http://127.0.0.1:%d/" % self.port], capture_output=True, text=True,
                           timeout=600, env=env)
        self.assertEqual(r.returncode, 0, r.stderr[-3000:])
        res = json.loads(r.stdout.strip().split("\n")[-1])
        self.assertEqual(res["errs"], [])
        for w, o in res["out"]["w"].items():
            w = int(w)
            for k, v in o.items():
                if k.startswith("sw-"):
                    self.assertLessEqual(v, w, (w, k))                                    # bez poziomego przewijania
            # kropka na zakładce z pracą: zadanie → Zadania, publikacja z kampanii → Marketing, „Strona: …” → Strona
            self.assertEqual(o["tabs-shield"], ["#p-shield-tablica"], w)
            self.assertEqual(o["tabs-jesien"], ["#p-jesien-marketing"], w)
            self.assertEqual(o["tabs-portal"], ["#p-portal-strona"], w)                   # Całość zbiera pracę części
            self.assertEqual(o["tabs-www"], ["#p-portal-strona"], w)
            self.assertEqual((o["tabs-mobilna"], o["row-mobilna"]), ([], ""), w)          # bez pracy: nic
            # wiersz pod nazwą: kto, zadanie, kamień milowy albo ostatnia czynność, Pokaż; reszta „i jeszcze n”
            self.assertIn("Claude pracuje:", o["row-shield"], w)
            self.assertIn("krok 2 z 3: Opisać wyniki w raporcie", o["row-shield"], w)
            self.assertIn("Pokaż", o["row-shield"], w)
            self.assertIn("i jeszcze 1", o["row-shield"], w)
            self.assertIn("Pisze tekst posta", o["row-jesien"], w)
            self.assertIn("Strona: popraw nagłówek", o["row-www"], w)
        big = res["out"]["w"]["1440"]
        self.assertEqual(big["side"], {"#p-shield": "2 agentów", "#p-portal": "pracuje", "#p-jesien": "pracuje"})
        self.assertIn("Codex pracuje: Napraw testy formularza", big["sideTitle"])        # podpowiedź: kto i nad czym
        self.assertEqual(big["ag"][0], "4")                                               # pracujący, bez kolejki
        self.assertIn("ws-live", big["ag"][1])
        self.assertEqual(big["ag"][2], "Pracuje: 4, w kolejce: 1")
        self.assertEqual(big["anim"], "ws-pulse")
        self.assertEqual(big["show"], "r-ws-1")
        self.assertTrue(big["drawer"])                                                    # Pokaż otwiera przebieg
        self.assertEqual(big["after"], {"dots": 0, "row": 0, "ag": 0, "side": {}})       # koniec pracy: na żywo znika
        small = res["out"]["w"]["393"]
        self.assertEqual(small["bnag"], "4")
        self.assertEqual(sorted(small["sheet"]), ["#p-jesien", "#p-portal", "#p-shield"])
        self.assertTrue(res["out"]["reduced"])
        self.assertEqual(set(res["out"]["reduced"]), {"none"})                           # reduced motion: bez pulsowania
        self.assertEqual(res["out"]["reducedCnt"], "none")


if __name__ == "__main__":
    unittest.main()
