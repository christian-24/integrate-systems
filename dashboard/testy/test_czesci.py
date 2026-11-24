"""Projekt z częściami (pole karty „część projektu:”), rozmowa w prawym dolnym rogu i sekcja „Kod i pliki”.

Dane i raport PM: zawsze. Funkcje widoku z panel.html: w node (bez przeglądarki). Cała strona w Chromium (Playwright):
bez PANEL_TESTY_BEZ_RENDERU.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer

from test_blokady import NODE
from test_czat_uruchamia import PW
from test_instagram import PANEL, panel_parts, read
from wspolne import TODAY, Baza, projekt, quiet, server

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "standard"))
import pm  # noqa: E402


def project(pid, name, part_of=""):
    return {"id": pid, "name": name, "partOfRaw": part_of,
            "docs": [{"key": "karta", "status": "ok", "gaps": []}], "book": [{"key": "karta", "status": "ok", "gaps": []}],
            "docsOk": 1, "bookOk": 1}


class Pole(unittest.TestCase):
    def test_parser_pola(self):
        f = projekt.card_fields({"część projektu": " company-audits "})
        self.assertEqual(f["partOf"], "company-audits")
        self.assertEqual(f["errors"], [])
        self.assertEqual(projekt.card_fields({"czesc projektu": "`Company-Audits`"})["partOf"], "company-audits")
        self.assertEqual(projekt.card_fields({})["partOf"], "")
        f = projekt.card_fields({"część projektu": "!!!"})
        self.assertEqual(f["partOf"], "")
        self.assertTrue(any(e.startswith("część projektu:") for e in f["errors"]))

    def test_nazwy_czesci(self):
        L = [project("company-audits", "Oprogramowani (integracje ERP ↔ sprzedaż)"),
             project("oprogramowani-onepager", "Oprogramowani – strona WWW", "company-audits"),
             project("inny", "Inny projekt")]
        self.assertEqual(projekt.link_parts(L), {"oprogramowani-onepager": "company-audits"})
        head, part, other = L
        self.assertEqual(head["name"], "Oprogramowani")
        self.assertEqual(head["partLabel"], "Integracje ERP ↔ sprzedaż")
        self.assertEqual(head["parts"], [{"id": "oprogramowani-onepager", "label": "Strona WWW"}])
        self.assertEqual(head["cardName"], "Oprogramowani (integracje ERP ↔ sprzedaż)")
        self.assertEqual((part["partOf"], part["partLabel"], part["name"]),
                         ("company-audits", "Strona WWW", "Oprogramowani · Strona WWW"))
        self.assertEqual((other["name"], other["partOf"], other["parts"]), ("Inny projekt", "", []))
        self.assertNotIn("partOfRaw", part)

    def test_tytul_karty_to_nazwa_czesci(self):
        L = [project("a", "Marka"), project("b", "Strona WWW", "a")]
        projekt.link_parts(L)
        self.assertEqual((L[0]["name"], L[0]["partLabel"]), ("Marka", "Główna część"))
        self.assertEqual(L[1]["name"], "Marka · Strona WWW")

    def test_wskazanie_po_folderze_karty(self):
        with tempfile.TemporaryDirectory() as tmp:
            cards = os.path.join(tmp, "szkice", "company-audits")
            os.makedirs(cards)
            folder = os.path.join(tmp, "repo-firmy")
            os.makedirs(folder)
            open(os.path.join(cards, "KARTA.md"), "w").close()
            os.symlink(os.path.join(cards, "KARTA.md"), os.path.join(folder, "KARTA.md"))
            L = [project("repo-firmy", "Firma"), project("strona", "Strona", "company-audits")]
            projekt.link_parts(L, {"repo-firmy": folder, "strona": tmp})
            self.assertEqual(L[1]["partOf"], "repo-firmy")

    def test_bledne_wskazania(self):
        L = [project("a", "A", "nie-ma"), project("b", "B", "b"), project("c", "C", "d"), project("d", "D", "a")]
        projekt.link_parts(L)
        gaps = {p["id"]: p["docs"][0]["gaps"] for p in L}
        self.assertIn("nie ma takiego projektu", gaps["a"][0])
        self.assertIn("ten sam projekt", gaps["b"][0])
        self.assertIn("jest częścią innego projektu", gaps["c"][0])   # bez zagnieżdżania części
        self.assertEqual(L[0]["docsOk"], 0)
        self.assertEqual([p["partOf"] for p in L], ["", "", "", "a"])  # a bez głównego zostaje zwykłym projektem


class ZCzesciami(Baza):
    """Projekt główny (projekt-testowy) i część „Strona WWW” w rejestrze."""

    def setUp(self):
        super().setUp()
        path = os.path.join(self.folder, "KARTA.md")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        with open(path, "w", encoding="utf-8") as f:
            f.write(re.sub(r"^# .*$", "# Oprogramowani (integracje ERP)", text, count=1, flags=re.M))
        self.part = os.path.join(self.tmp, "oprogramowani-onepager")
        quiet(projekt.cmd_nowy, self.part, "Strona WWW", register=True)
        projekt.set_card_fields(self.part, {"priority": 2})
        with open(os.path.join(self.part, "KARTA.md"), encoding="utf-8") as f:
            text = f.read()
        with open(os.path.join(self.part, "KARTA.md"), "w", encoding="utf-8") as f:
            f.write(text.replace("- priorytet: 2", "- priorytet: 2\n- część projektu: projekt-testowy\n- strona: site", 1))
        with open(os.path.join(self.part, "ZADANIA.md"), "w", encoding="utf-8") as f:
            f.write("# Zadania: Strona WWW\n\n## Etap: Strona\ntermin: %s\n\n"
                    "- [ ] Oceń stronę | kto: ty | kiedy: %s | czas: 15\n- [ ] Podgląd strony | kto: claude\n" % (TODAY, TODAY))
        server.data_invalidate()


class Dane(ZCzesciami):
    def test_dane_panelu(self):
        d = server.build_data()
        by = {p["id"]: p for p in d["projects"]}
        self.assertEqual(set(by), {"projekt-testowy", "oprogramowani-onepager"})   # oba foldery dalej osobno
        self.assertEqual(by["projekt-testowy"]["name"], "Oprogramowani")
        self.assertEqual(by["projekt-testowy"]["parts"], [{"id": "oprogramowani-onepager", "label": "Strona WWW"}])
        part = by["oprogramowani-onepager"]
        self.assertEqual((part["partOf"], part["partLabel"]), ("projekt-testowy", "Strona WWW"))
        self.assertEqual([p for p in d["projects"] if not p["partOf"]], [by["projekt-testowy"]])  # na listach jeden
        self.assertTrue(part["site"])                                    # Strona części działa jak dziś
        t = next(t for t in d["tasks"] if t["title"] == "Oceń stronę")
        self.assertEqual(t["project"], "oprogramowani-onepager")          # zadania zostają w pliku części
        self.assertIn("branch", by["projekt-testowy"]["git"])
        karta = next(x for x in part["docs"] if x["key"] == "karta")
        self.assertFalse(any("część" in g for g in karta["gaps"]))

    def test_pm_bez_dublowania(self):
        f = pm.facts()
        self.assertEqual([p["name"] for p in f["projects"]], ["Oprogramowani"])
        self.assertEqual(f["projects"][0]["parts"], ["Strona WWW"])
        mine = [t for t in d_all(f) if t["title"] == "Oceń stronę"]
        self.assertEqual({t["project"] for t in mine}, {"Oprogramowani · Strona WWW"})
        self.assertEqual(len([t for t in f["decisions"] if t["title"] == "Oceń stronę"]), 1)
        titles = [t["title"] for t in f["decisions"]]
        self.assertEqual(len(titles), len(set(titles)))
        self.assertEqual(f["noNextStep"], [])
        text = pm.text(f)
        self.assertIn("Oprogramowani · Strona WWW · Oceń stronę", text)
        self.assertEqual(len(re.findall(r"^\s*\S+ Oprogramowani\s+\d+/\d+", text, re.M)), 1)   # PROJEKTY: jeden wiersz

    def test_rozmowa_o_calosci_zna_czesci(self):
        data, index = server.load_projects()
        p = next(x for x in data["projects"] if x["id"] == "projekt-testowy")
        prompt = self.manager.project_chat_prompt(p, self.folder, self.folder, "Co dalej?",
                                                  [("Strona WWW", self.part)])
        self.assertIn("„Oprogramowani”", prompt)
        self.assertIn("- Strona WWW: %s" % os.path.join(self.part, "ZADANIA.md"), prompt)


def d_all(f):
    return f["decisions"] + f["today_tasks"] + f["tomorrow_tasks"]


@unittest.skipUnless(NODE, "brak node")
class Widok(unittest.TestCase):
    """Funkcje strony projektu z panel.html w node: adresy części, przełącznik, „Kod i pliki”, okno rozmowy."""

    def run_view(self, body):
        code = panel_parts(read(PANEL).decode("utf-8"), ["esc", "pl", "pid2", "phref", "inP", "topP", "ptag", "partSw", "kpN",
                                                         "ghLine", "driveLine", "codeBox", "pjChatOf", "dockHtml"])
        js = """let LIVE=true;const PF={more:{}},GHS={},DRV={x:{connected:true,mounted:true,files:3,folder:'1AbCdEfGhIjK'}},A={busy:{}};
const D={projectsSource:'registry'},loaded=[];
const ghLoad=id=>loaded.push(id),loadDrive=()=>{},loadPChat=id=>loaded.push('chat:'+id);
const ghBody=p=>'<div class="gh">GH:'+p.id+'</div>',driveBody=p=>'<div class="dv">DRV:'+p.id+'</div>';
const chatMsg=m=>'<div class="cm">'+m.text+'</div>';
let PJC={};
%s
const top={id:'x',name:'Oprogramowani',partOf:'',partLabel:'Integracje',github:'f/x',git:{repo:true,remote:'github',branch:'main',unpushed:0}};
const part={id:'s',name:'Oprogramowani · Strona WWW',partOf:'x',partLabel:'Strona WWW',site:{dir:'site'},github:'',git:{repo:true,remote:'github',branch:'nowa',unpushed:2},mem:new Set(['s']),partsL:[]};
top.partsL=[part];top.mem=new Set(['x','s']);top.own=Object.assign({},top,{isOwn:true,mem:new Set(['x']),partsL:[],name:'Oprogramowani · Integracje'});
const by={x:top,s:part};const P=id=>by[id]||null;
const out={};
%s
JSON.stringify(out);
""" % (code, body)
        lines = js.rstrip().split("\n")
        lines[-1] = "console.log(" + lines[-1].rstrip(";") + ");"
        r = subprocess.run([NODE, "-"], input="\n".join(lines), capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_adresy_i_przelacznik(self):
        o = self.run_view("""out.top=phref(top,'tablica');out.part=phref(part,'strona');out.own=phref(top.own);
const sw=partSw(part,'strona');out.sw=[...sw.matchAll(/<a href="([^"]+)"[^>]*>([^<]+)</g)].map(m=>[m[1],m[2]]);
out.cur=(sw.match(/aria-current="page">([^<]+)/)||[])[1];out.none=partSw(by.s&&{id:'z',partsL:[]},'plan');
out.tag=ptag(top,'s');out.tagOwn=ptag(top,'x');out.tagPart=ptag(part,'s');""")
        self.assertEqual(o["top"], "#p-x-tablica")
        self.assertEqual(o["part"], "#p-x-strona?cz=s")                 # część: adres projektu głównego
        self.assertEqual(o["own"], "#p-x?cz=x")
        self.assertEqual(o["sw"], [["#p-x", "Całość"], ["#p-x?cz=x", "Integracje"], ["#p-x-strona?cz=s", "Strona WWW"]])
        self.assertEqual(o["cur"], "Strona WWW")
        self.assertEqual(o["none"], "")
        self.assertIn("Strona WWW", o["tag"])
        self.assertEqual((o["tagOwn"], o["tagPart"]), ("", ""))

    def test_kod_i_pliki_zwiniety_i_rozwiniety(self):
        o = self.run_view("""out.zw=codeBox(top);out.ld=loaded.slice();PF.more['pj-code']=true;out.rw=codeBox(top);out.ld2=loaded.slice();
out.cz=codeBox(part);LIVE=false;out.off=codeBox(part);""")
        zw, rw = o["zw"], o["rw"]
        self.assertIn('aria-expanded="false"', zw)
        self.assertIn(">Szczegóły<", zw)
        self.assertIn('id="pcode-det" hidden', zw)
        self.assertNotIn("GH:", zw)
        self.assertEqual(o["ld"], [])                                     # zwinięte: bez zapytań o stan kopii
        self.assertEqual(zw.count("<dt>GitHub"), 2)                       # wiersz na każde repozytorium części
        self.assertIn("zgodne z GitHubem", zw)
        self.assertIn("2 commity do wysłania", zw)
        self.assertIn("brak pola github:", zw)
        self.assertIn("połączony: <a href=\"https://drive.google.com/drive/folders/1AbCdEfGhIjK\"", zw)
        self.assertIn("3 pozycje", zw)
        self.assertIn('aria-expanded="true"', rw)
        self.assertIn(">Zwiń<", rw)
        self.assertIn("GH:x", rw)
        self.assertIn("GH:s", rw)
        self.assertIn("DRV:x", rw)
        self.assertEqual(o["ld2"], ["x", "s"])
        self.assertEqual(o["cz"].count("<dt>GitHub"), 1)                  # wybrana część: tylko jej repozytorium
        self.assertIn("GH:s", o["cz"])
        self.assertNotIn("GH:", o["off"])                                 # poza serwerem bez działań na kopii

    def test_rozmowa_w_rogu(self):
        o = self.run_view("""const r={v:'projekt',p:top};out.zam=dockHtml(r);out.ld=loaded.slice();
PJC.x.loading=false;PJC.x.messages=[{role:'ty',text:'Pytanie'}];PJC.x.pending=true;out.czeka=dockHtml(r);
PJC.x.pending=false;PJC.x.messages.push({role:'claude',text:'Odpowiedź'});out.nowa=dockHtml(r);
PF.more['pj-chat']=true;out.otw=dockHtml(r);PF.more['pj-chat']=false;out.po=dockHtml(r);
PF.more['pj-chat']=true;out.czesc=dockHtml({v:'projekt',p:part});out.wlasna=dockHtml({v:'projekt',p:top.own});
out.inny=dockHtml({v:'start'});""")
        self.assertIn('data-pjd="open"', o["zam"])
        self.assertIn('aria-expanded="false"', o["zam"])
        self.assertIn(">Rozmowa<", o["zam"])
        self.assertEqual(o["ld"], ["chat:x"])
        self.assertIn("czeka na odpowiedź", o["czeka"])
        self.assertIn("nowa odpowiedź", o["nowa"])
        otw = o["otw"]
        self.assertIn('role="dialog"', otw)
        self.assertIn("Oprogramowani · całość", otw)
        self.assertIn('data-pchat="x"', otw)                              # wysyłka jak dotąd: /api/project/chat
        self.assertIn('data-pjd="close"', otw)
        self.assertIn("Odpowiedź", otw)
        self.assertNotIn("nowa odpowiedź", o["po"])                       # po otwarciu odpowiedź przeczytana
        self.assertIn('data-pchat="s"', o["czesc"])                       # część: własna rozmowa
        self.assertIn("Oprogramowani · Strona WWW", o["czesc"])
        self.assertIn("Oprogramowani · Integracje", o["wlasna"])
        self.assertEqual(o["inny"], "")                                   # tylko na stronie projektu


class Kod(unittest.TestCase):
    """Strona projektu bez sekcji rozmowy i osobnej sekcji Google Drive; Esc zwija rozmowę; Serwer bez działań."""

    @classmethod
    def setUpClass(cls):
        cls.html = read(PANEL).decode("utf-8")

    def test_bez_starych_sekcji(self):
        v = panel_parts(self.html, ["vProjekt"])
        self.assertIn("codeBox(p)", v)
        self.assertNotIn("projChatBox", self.html)
        self.assertNotIn("pjFold('pj-drive'", self.html)
        self.assertIn('<div id="pjdock" class="pjd"></div>', self.html)
        gh = panel_parts(self.html, ["ghPanel"])
        self.assertNotIn("ghBody", gh)
        self.assertIn('data-pjgo="pcode"', gh)

    def test_esc_i_odstep(self):
        self.assertRegex(self.html, r"ev\.key!=='Escape'\|\|!PF\.more\['pj-chat'\]")
        self.assertIn("body.pjd-on #view{padding-bottom:", self.html)


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
        pg.goto(U + "#p-oprogramowani-onepager-strona"); pg.wait_for_selector(".pj-parts")
        r["redirect"] = pg.evaluate("location.hash")
        r["cur"] = pg.locator(".pj-parts a[aria-current]").inner_text()
        r["tabs"] = pg.locator(".ptabs > a").all_inner_texts()
        pg.goto(U + "#p-projekt-testowy"); pg.wait_for_selector(".pj-parts"); pg.wait_for_timeout(500)
        r["list"] = pg.locator("#plist a .nm").all_inner_texts()
        r["tag"] = pg.locator("#pplan .ptag").all_inner_texts()
        pg.click("[data-pjcode]"); pg.wait_for_timeout(300)
        r["det"] = pg.locator("#pcode-det").is_visible()
        pg.click("[data-pjcode]"); pg.wait_for_timeout(300)
        r["det2"] = pg.locator("#pcode-det").is_visible()
        pg.click("[data-pjd=open]"); pg.wait_for_selector("#pjdock .pjd-win")
        box = pg.locator("#pjdock .pjd-win").bounding_box()
        r["box"] = [round(box["width"]), round(box["height"]), round(box["x"] + box["width"])]
        r["focus"] = pg.evaluate("document.activeElement.tagName")
        pg.fill("#pjdock textarea", "Co dalej?"); pg.keyboard.press("Enter")
        pg.wait_for_selector("#pjdock .cm >> nth=1", timeout=20000)
        r["msgs"] = pg.locator("#pjdock .cm").count()
        pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
        r["esc"] = [pg.locator("#pjdock .pjd-win").count(), pg.evaluate("document.activeElement.dataset.pjd||''")]
        pg.close()
    b.close()
print(json.dumps({"out": out, "errs": errs}))
"""


@unittest.skipUnless(PW and not os.environ.get("PANEL_TESTY_BEZ_RENDERU"), "brak Playwright albo PANEL_TESTY_BEZ_RENDERU")
class Strona(ZCzesciami):
    """Cała strona w Chromium: stary adres części, jeden projekt na liście, „Kod i pliki”, rozmowa (Enter, Esc)."""

    def test_strona_projektu(self):
        self.set_mode("ok")
        log = server.Handler.log_message
        server.Handler.log_message = lambda *a: None
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        try:
            env = dict(os.environ)
            if not env.get("PLAYWRIGHT_BROWSERS_PATH") and os.path.isdir("/opt/ms-playwright"):
                env["PLAYWRIGHT_BROWSERS_PATH"] = "/opt/ms-playwright"
            r = subprocess.run([PW, "-c", PAGE, "http://127.0.0.1:%d/" % httpd.server_address[1]], capture_output=True,
                               text=True, timeout=180, env=env)
        finally:
            httpd.shutdown()
            httpd.server_close()
            server.Handler.log_message = log
        self.assertEqual(r.returncode, 0, r.stderr[-2000:])
        res = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(res["errs"], [])
        for w, o in res["out"].items():
            with self.subTest(szerokosc=w):
                self.assertEqual(o["redirect"], "#p-projekt-testowy-strona?cz=oprogramowani-onepager")
                self.assertEqual(o["cur"], "Strona WWW")
                self.assertIn("Strona", o["tabs"])
                self.assertEqual(o["list"], ["Oprogramowani"])
                self.assertIn("Strona WWW", o["tag"])
                self.assertEqual((o["det"], o["det2"]), (True, False))
                self.assertEqual(o["focus"], "TEXTAREA")
                self.assertGreaterEqual(o["msgs"], 2)
                self.assertEqual(o["esc"], [0, "open"])
                if w == "1440":
                    self.assertEqual(o["box"][:2], [380, 520])
                else:
                    self.assertEqual(o["box"][0], 390)                    # telefon: arkusz na całą szerokość


if __name__ == "__main__":
    unittest.main()
