"""Mniej widoków (zlecenie 2026-11-24): zostają Asystent, Marketing, Media, Agenci i Serwer. Dawne Start, Dla Ciebie,
Przegląd, Wskaźniki, Tablica, Terminy, Blokady i Projekty pokazuje Asystent kartami; stare adresy prowadzą do Asystenta."""
import datetime
import json
import os
import re
import subprocess
import sys
import unittest

from test_blokady import NODE, PANEL
from test_instagram import panel_parts
from test_serwer import Serwer
from wspolne import agents, server  # noqa: F401
import karty  # noqa: E402  (ścieżka dashboard/ z wspolne)

PW = next((p for p in ("/home/agent/narzedzia/pw/bin/python",) if os.path.isfile(p)), "")
REMOVED = ("start", "przeglad", "wskazniki", "ty", "tablica", "terminy", "blokady", "projekty")


def html():
    with open(PANEL, encoding="utf-8") as f:
        return f.read()


class Menu(unittest.TestCase):
    """Menu ma tylko pozostałe widoki; kod usuniętych widoków zniknął; brak odnośników do starych adresów."""

    @classmethod
    def setUpClass(cls):
        cls.html = html()

    def test_tylko_pozostale_widoki(self):
        views = re.search(r"^const VIEWS=\[(.*?)\];", self.html, re.M).group(1)
        self.assertEqual(re.findall(r"'(\w+)'", views), ["asystent", "marketing", "media", "agenci", "koszty"])
        self.assertIn("const MAINV=VIEWS;", self.html)
        self.assertIn("const BNAV=['asystent','marketing','media','agenci'];", self.html)
        self.assertNotIn("nav-more", self.html)                       # bez grupy „Więcej” w menu bocznym
        names = re.search(r"^const VNAME=\{(.*?)\};", self.html, re.M).group(1)
        self.assertEqual(re.findall(r"(\w+):'", names), ["asystent", "marketing", "media", "agenci", "koszty", "odbior"])
        # licznik spraw dla Ciebie stoi przy Asystencie
        self.assertIn("C={asystent:[you],agenci:[ag,'blue']}", self.html)

    def test_kod_widokow_usuniety(self):
        for fn in ("vStart", "vPrzeglad", "vWskazniki", "vTy", "vTablica", "vTerminy", "vBlokady", "vProjekty",
                   "riskRows", "todayPanel", "pvToday", "pvSys", "statusLine", "projCard", "qPanel", "pvWeek"):
            self.assertIsNone(re.search(r"function %s\(" % fn, self.html), fn)
        for cls in ("pv-head", "pv-today", "tb-head", "tm-jumps", "nav-more", "ptable", "pcards"):
            self.assertNotIn("." + cls + "{", self.html, cls)

    def test_bez_odnosnikow_do_starych_widokow(self):
        js = self.html[self.html.index("<script>"):]
        old = "|".join(REMOVED)
        self.assertEqual(re.findall(r"href=\\?[\"']#(?:%s)\b" % old, js), [])
        self.assertEqual(re.findall(r"[\"']#(?:%s)(?:\?|[\"'])" % old, js), [])
        self.assertFalse("na Tablicy" in js)
        self.assertFalse("z Tablicy" in js)

    def test_skroty_klawiszowe(self):
        m = re.search(r"const m=\{(s:'asystent'[^}]*)\}\[k\]", self.html)
        self.assertTrue(m)
        self.assertEqual(re.findall(r":'(\w+)'", m.group(1)), ["asystent", "marketing", "media", "agenci", "koszty"])


@unittest.skipUnless(NODE, "brak node")
class Adresy(unittest.TestCase):
    """route(): stare adresy (z parametrami) → Asystent z kartą; #koszty?k= → sekcja Serwera; oldRoute zostawia ?z=."""

    def run_js(self, body):
        code = panel_parts(html(), ["OLDV", "VIEWS", "route", "oldRoute"])
        js = """let location={hash:'',pathname:'/',search:''};const replaced=[],shown=[];
const history={replaceState:(a,b,u)=>replaced.push(u)};
const D={},PF={bp:'all',bk:'',ms:'all',apZ:{p:'all',s:'otwarte'}};
const P=id=>id==='x'?{id:'x'}:null,odRouteId=()=>'',apShowCard=id=>shown.push(id);
%s
const go=h=>{location.hash=h;return route()};
const out={};
%s
console.log(JSON.stringify(out));""" % (code, body)
        r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_stare_adresy(self):
        o = self.run_js("""for(const h of ['#start','#przeglad','#ty','#wskazniki','#tablica','#terminy','#blokady','#projekty',
  '#ty?z=a|b','#terminy?p=x','#tablica?p=x','#blokady?p=x','#wskazniki?p=all','','#nieznany','#asystent','#asystent?k=raport-pm',
  '#koszty?k=projekty','#agenci'])out[h]=go(h);out.pf=PF;""")
        want = {"#start": "", "#przeglad": "", "#ty": "sprawy", "#wskazniki": "wskazniki", "#tablica": "zadania",
                "#terminy": "terminy", "#blokady": "blokady", "#projekty": ""}
        for h, k in want.items():
            self.assertEqual((o[h]["v"], o[h]["k"]), ("asystent", k), h)
        self.assertEqual(o["#ty?z=a|b"]["qs"], "z=a|b")
        self.assertEqual((o["#terminy?p=x"]["v"], o["pf"]["bp"], o["pf"]["apZ"]["p"], o["pf"]["bk"]), ("asystent", "x", "x", "x"))
        self.assertEqual(o[""], {"v": "asystent"})
        self.assertEqual(o["#nieznany"], {"v": "asystent"})
        self.assertEqual(o["#asystent"], {"v": "asystent"})
        self.assertEqual(o["#asystent?k=raport-pm"]["k"], "raport-pm")
        self.assertEqual(o["#koszty?k=projekty"], {"v": "koszty", "go": "projekty"})
        self.assertEqual(o["#agenci"], {"v": "agenci"})

    def test_stary_adres_zostawia_parametr_powiadomienia(self):
        o = self.run_js("""oldRoute(go('#ty?z=t1&p=x'));oldRoute(go('#przeglad'));oldRoute(go('#asystent?k=blokady'));
out.r=replaced;out.s=shown;""")
        self.assertEqual(o["r"], ["/#asystent?z=t1", "/#asystent", "/#asystent"])
        self.assertEqual(o["s"], ["sprawy", "blokady"])


class Karty(unittest.TestCase):
    """Karty wbudowane typu „panel” (dawne widoki), opis dla modelu i linki powiadomień."""

    def test_karty_panelu(self):
        ids = [c["id"] for c in karty.STARTERS]
        for i in ("sprawy-dzis", "raport-pm", "sprawy", "terminy", "blokady", "wskazniki", "zadania"):
            self.assertIn(i, ids)
        self.assertEqual(karty.START, ("sprawy-dzis", "raport-pm"))
        self.assertEqual(set(karty.PANEL_VIEWS), {"sprawy-dzis", "sprawy", "terminy", "blokady", "wskazniki", "zadania", "raport"})
        ok = karty.card({"id": "t", "typ": "panel", "widok": "terminy", "tytul": "Terminy"})
        self.assertEqual(ok["widok"], "terminy")
        for bad in ({"id": "t", "typ": "panel", "tytul": "T"}, {"id": "t", "typ": "panel", "widok": "pulpit", "tytul": "T"},
                    {"id": "t", "typ": "panel", "widok": "terminy", "tytul": "T", "zapytanie": {"zrodlo": "zadania"}}):
            with self.assertRaises(karty.Bad):
                karty.card(bad)
        _, ops = karty.extract('```karty\n{"pokaz": [{"id": "sprawy"}, {"id": "x", "typ": "panel", "widok": "blokady", "tytul": "B"}]}\n```')
        self.assertEqual((ops["pokaz"], ops["bledy"]), ([{"id": "sprawy"}, {"id": "x", "typ": "panel", "widok": "blokady", "tytul": "B"}], []))

    def test_model_wie_ze_to_jego_dane(self):
        for part in ("Widoków Start, Dla Ciebie, Przegląd, Wskaźniki, Tablica, Terminy, Blokady i Projekty",
                     '{"id": "sprawy"}', '{"id": "terminy"}', '{"id": "blokady"}', '{"id": "wskazniki"}', '{"id": "zadania"}',
                     '{"id": "raport-pm"}', "- panel: fragment panelu z przyciskami"):
            self.assertIn(part, karty.PROMPT)
        views = [v for v, _ in agents.Manager.ASSIST_VIEWS]
        self.assertEqual(views, ["#asystent", "#marketing", "#media", "#agenci", "#koszty"])

    def test_linki_powiadomien(self):
        self.assertEqual(agents.notify_link({"kind": "task", "taskId": "p|ZADANIA.md|3", "id": "r"}), "#asystent?z=p|ZADANIA.md|3")
        self.assertEqual(agents.notify_link({"kind": "pm", "id": "r1"}), "#asystent")
        self.assertEqual(agents.notify_link({"kind": "plan", "id": "r1"}), "#agenci")
        self.assertEqual(agents.notify_link({"kind": "check", "id": "r1"}), "#agenci?u=r1")


ZADANIA_DOD = """
## Etap: Drugi
termin: %(today)s

- [~] Sprawdź wynik agenta | kto: claude | wymaga: odbiór | kiedy: %(today)s
- [ ] Krok po D | kto: claude | kiedy: %(today)s | po: Zadanie D
- [ ] Czeka na brak | kto: claude | po: Nie ma takiego zadania
"""
PYTANIE = "\n## Pytania do właściciela\n1. Czy wysłać ofertę teraz?\n"
NOTATKA = "## Najważniejsze\n- Punkt testowy\n\n## Proponuję\n- **Krok z notatki PM**\n"

PAGE = r"""
import json, sys
from playwright.sync_api import sync_playwright
U = sys.argv[1]
out, errs = {}, []
with sync_playwright() as p:
    b = p.chromium.launch()
    for w in (1440, 390):
        pg = b.new_page(viewport={"width": w, "height": 900})
        pg.on("pageerror", lambda e: errs.append(str(e)))
        r = out[str(w)] = {}
        pg.goto(U + "#asystent"); pg.wait_for_selector(".as-start .as-st1")
        r["start"] = pg.locator(".as-start").inner_text()
        r["nav"] = pg.evaluate("[...document.querySelectorAll('#nav a')].map(a=>a.getAttribute('href'))")
        r["badge"] = pg.locator("#nav a[href='#asystent'] .count").inner_text() if w > 900 else ""
        cards = {}
        for k in ("ty", "terminy", "blokady", "wskazniki", "tablica"):
            pg.goto(U + "#" + k); pg.wait_for_selector(".as-anc .ap-card"); pg.wait_for_timeout(300)
            cards[k] = [pg.evaluate("location.hash"), pg.locator(".as-anc .ap-card").first.inner_text()]
        r["cards"] = cards
        pg.goto(U + "#asystent?k=raport-pm"); pg.wait_for_selector(".as-anc .ap-card"); pg.wait_for_timeout(300)
        r["raport"] = pg.locator(".as-anc .ap-card").first.inner_text()
        pg.close()
    # działania w karcie „Sprawy dla Ciebie” (komputer): zgoda, odpowiedź na pytanie, odbiór
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(U + "#ty"); pg.wait_for_selector(".as-anc .ap-card"); pg.wait_for_timeout(300)
    row = pg.locator(".as-anc li", has_text="Zadanie E").first
    row.locator("button", has_text="Zatwierdź").click(); pg.wait_for_timeout(1500)
    pg.locator(".as-anc button[data-qans]").first.click(); pg.wait_for_selector("form[data-qa] textarea")
    pg.fill("form[data-qa] textarea", "Tak, wysłać"); pg.keyboard.press("Enter"); pg.wait_for_timeout(1500)
    for _ in range(3):
        if pg.locator("#drawer").count():
            pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
    out["drawer_closed"] = pg.locator("#drawer").count() == 0
    row = pg.locator(".as-anc li", has_text="Sprawdź wynik agenta").first
    btn = row.locator("[data-act], [data-od], a[href^='#odbior'], button").last
    out["odbior_btn"] = btn.inner_text()
    btn.click(); pg.wait_for_timeout(800)
    out["odbior_hash"] = pg.evaluate("location.hash")
    # szczegóły zadania z brakującym poprzednikiem: naprawa z dawnych Blokad
    pg.goto(U + "#asystent?k=zadania"); pg.wait_for_selector(".as-anc .ap-card"); pg.wait_for_timeout(300)
    pg.locator(".as-anc button[data-aptask]", has_text="Czeka na brak").first.click(); pg.wait_for_timeout(500)
    out["fix"] = pg.locator("#drawerHost [data-bkdrop], #drawerHost [data-bkadd]").all_inner_texts()
    pg.close()
    b.close()
print(json.dumps({"out": out, "errs": errs}, ensure_ascii=False))
"""


@unittest.skipUnless(PW and not os.environ.get("PANEL_TESTY_BEZ_RENDERU"), "brak Playwright albo PANEL_TESTY_BEZ_RENDERU")
class Przegladarka(Serwer):
    """Cała strona w Chromium na projekcie testowym: start Asystenta, karty z dawnych widoków liczone z danych,
    działania (zgoda, odpowiedź na pytanie, odbiór) z karty, bez błędów JS."""

    def setUp(self):
        super().setUp()
        today = datetime.date.today().isoformat()
        with open(os.path.join(self.folder, "ZADANIA.md"), "a", encoding="utf-8") as f:
            f.write(ZADANIA_DOD % {"today": today})
        with open(os.path.join(self.folder, "KARTA.md"), "a", encoding="utf-8") as f:
            f.write(PYTANIE)
        with open(os.path.join(self.notes, today + ".md"), "w", encoding="utf-8") as f:
            f.write(NOTATKA)

    def test_karty_i_dzialania(self):
        data = self.data()
        open_tasks = sum(1 for t in data["tasks"] if t.get("kind") != "publikacja" and t["state"] != "done")
        env = dict(os.environ)
        if not env.get("PLAYWRIGHT_BROWSERS_PATH") and os.path.isdir("/opt/ms-playwright"):
            env["PLAYWRIGHT_BROWSERS_PATH"] = "/opt/ms-playwright"
        r = subprocess.run([PW, "-c", PAGE, "http://127.0.0.1:%d/" % self.port], capture_output=True, text=True,
                           timeout=240, env=env)
        self.assertEqual(r.returncode, 0, r.stderr[-3000:])
        res = json.loads(r.stdout.strip().split("\n")[-1])
        self.assertEqual(res["errs"], [])
        for w, o in res["out"].items():
            if w not in ("1440", "390"):
                continue
            self.assertIn("Dziś dla Ciebie", o["start"])
            self.assertIn("Krok z notatki PM", o["start"])                    # notatka PM na starcie (część „Proponuję”)
            self.assertNotIn("Punkt testowy", o["start"])
            if w == "1440":
                self.assertEqual(o["nav"][:5], ["#asystent", "#marketing", "#media", "#agenci", "#koszty"])
                self.assertRegex(o["badge"], r"\d+\s+spraw")
            c = o["cards"]
            for k in c:
                self.assertEqual(c[k][0], "#asystent", k)                    # stary adres → Asystent
            self.assertIn("Sprawy dla Ciebie", c["ty"][1])
            self.assertIn("Zadanie E", c["ty"][1])
            self.assertIn("Czy wysłać ofertę teraz?", c["ty"][1])
            self.assertIn("Terminy", c["terminy"][1])
            self.assertIn("Auto dziś", c["terminy"][1])
            self.assertIn("Blokady", c["blokady"][1])
            self.assertIn("Zadanie D", c["blokady"][1])                      # Twoje zadanie wstrzymuje „Krok po D”
            self.assertIn("Wskaźniki", c["wskazniki"][1])
            self.assertIn("%d zada" % open_tasks, c["tablica"][1])          # Zadania: otwarte ze wszystkich projektów
            self.assertIn("Krok z notatki PM", o["raport"])
            self.assertIn("Najważniejsze", o["raport"])                      # pełna notatka: „Najważniejsze” zwinięte
        out = res["out"]
        self.assertNotIn("wymaga: zgoda", self.row("Zadanie E"))             # zgoda z karty zapisana w pliku
        with open(os.path.join(self.folder, "KARTA.md"), encoding="utf-8") as f:
            self.assertIn("Tak, wysłać", f.read())                           # odpowiedź na pytanie zapisana
        self.assertTrue(out["odbior_hash"].startswith("#odbior"), out)      # odbiór: strona Odbiór pracy
        self.assertEqual(len(out["fix"]), 2, out)                           # Usuń warunek / Dodaj zadanie


if __name__ == "__main__":
    unittest.main()
