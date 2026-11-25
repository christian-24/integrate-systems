"""Projekt z częściami (pole karty „część projektu:”), rozmowa w prawym dolnym rogu i zakładka Połączenia (dawniej „Kod i pliki”).

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
                                                  [("Strona WWW", self.part, "oprogramowani-onepager")])
        self.assertIn("„Oprogramowani”", prompt)
        self.assertIn("- Strona WWW (id oprogramowani-onepager): %s" % os.path.join(self.part, "ZADANIA.md"), prompt)
        self.assertNotIn("[Otwórz podgląd]", prompt)                     # bez stron: bez zasady o podglądzie

    def test_rozmowy_podaja_adres_podgladu(self):
        """Rozmowa o projekcie i Asystent dostają adres zakładki Strona części, nie opis drogi w panelu."""
        data, index = server.load_projects()
        links = self.manager.site_links(data)
        self.assertEqual(links, [("Oprogramowani · Strona WWW", "#p-projekt-testowy-strona?cz=oprogramowani-onepager")])
        p = next(x for x in data["projects"] if x["id"] == "projekt-testowy")
        prompt = self.manager.project_chat_prompt(p, self.folder, self.folder, "Gdzie zobaczę stronę?",
                                                  [("Strona WWW", self.part, "oprogramowani-onepager")], links)
        self.assertIn("[Otwórz podgląd](adres)", prompt)
        self.assertIn("#p-projekt-testowy-strona?cz=oprogramowani-onepager", prompt)
        self.assertIn("#p-projekt-testowy-strona?cz=oprogramowani-onepager",
                      self.manager.assistant_prompt(data, index, "Gdzie zobaczę stronę?", "#asystent"))
        self.assertEqual(self.manager.site_links(data, {"projekt-testowy"}), [])     # inny projekt: bez adresu


def d_all(f):
    return f["decisions"] + f["today_tasks"] + f["tomorrow_tasks"]


@unittest.skipUnless(NODE, "brak node")
class Widok(unittest.TestCase):
    """Funkcje strony projektu z panel.html w node: adresy części, wybór części, Połączenia, okno rozmowy."""

    def run_view(self, body):
        code = panel_parts(read(PANEL).decode("utf-8"), ["esc", "pl", "pid2", "phref", "inP", "topP", "ptag", "wwSites", "partSw", "kpN",
                                                         "ghLine", "drWhere", "driveLine", "projName", "pjxRepos", "pjxCard",
                                                         "pjxRows", "pjxGh", "pjxDrive", "pjxPages", "pjxMembers", "pjxMetaHas",
                                                         "pjxIg", "pjxMeta", "pjxConView", "shortT", "PJD", "pjChatOf",
                                                         "taskChatOf", "dockTarget", "pjdRef", "pjdAtt", "attLabel", "AS_MICI",
                                                         "voiceButton", "dockHtml"])
        js = """let LIVE=true;const PF={more:{}},GHS={},DRV={x:{connected:true,mounted:true,files:3,folder:'1AbCdEfGhIjK'}},A={busy:{}};
const D={projectsSource:'registry',campaigns:[],tasks:[],publish:null},loaded=[];
const ghLoad=id=>loaded.push(id),loadDrive=()=>{},loadPChat=id=>loaded.push('chat:'+id);
const ghBody=p=>'<div class="gh">GH:'+p.id+'</div>',driveBody=p=>'<div class="dv">DRV:'+p.id+'</div>';
const chatMsg=m=>'<div class="cm">'+m.text+'</div>';
let PJC={},DR=null,VOICE=null;const runOf=()=>null,isAct=()=>false;
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
const sw=partSw(part,'strona');out.sw=[...sw.matchAll(/<option value="([^"]+)"[^>]*>([^<]+)</g)].map(m=>[m[1],m[2]]);
out.cur=(sw.match(/ selected>([^<]+)/)||[])[1];out.none=partSw(by.s&&{id:'z',partsL:[]},'tablica');out.sel=sw;
out.tag=ptag(top,'s');out.tagOwn=ptag(top,'x');out.tagPart=ptag(part,'s');""")
        self.assertEqual(o["top"], "#p-x-tablica")
        self.assertEqual(o["part"], "#p-x-strona?cz=s")                 # część: adres projektu głównego
        self.assertEqual(o["own"], "#p-x?cz=x")
        # „Całość” ma zakładkę Strona (strona części), część bez strony przechodzi na Zadania (zakładki Plan już nie ma);
        # wybór części to mała lista przy nazwie, nie osobne zakładki
        self.assertEqual(o["sw"], [["#p-x-strona", "Całość"], ["#p-x-tablica?cz=x", "Integracje"], ["#p-x-strona?cz=s", "Strona WWW"]])
        self.assertIn('<label class="pjx-cz">', o["sel"])
        self.assertIn('data-pjxcz="1"', o["sel"])
        self.assertNotIn("<a ", o["sel"])
        self.assertEqual(o["cur"], "Strona WWW")
        self.assertEqual(o["none"], "")
        self.assertIn("Strona WWW", o["tag"])
        self.assertEqual((o["tagOwn"], o["tagPart"]), ("", ""))

    def test_polaczenia_zwiniete_i_rozwiniete(self):
        o = self.run_view("""out.zw=pjxConView(top);out.ld=loaded.slice();PF.more['pj-con-gh']=true;PF.more['pj-con-dr']=true;out.rw=pjxConView(top);
out.ld2=loaded.slice();out.cz=pjxConView(part);LIVE=false;out.off=pjxConView(part);""")
        zw, rw = o["zw"], o["rw"]
        # jedna karta na usługę; bez kanałów (kampanie, publikacje, profile w karcie, strona Facebook) bez karty Meta
        self.assertEqual(re.findall(r'<h2 id="pcon-[a-z]+-h">([^<]+)', zw), ["GitHub", "Google Drive"])
        self.assertEqual(zw.count('aria-expanded="false"'), 2)
        self.assertIn(">Szczegóły<", zw)
        self.assertIn('id="pcon-gh-det" hidden', zw)
        self.assertNotIn("GH:", zw)
        self.assertEqual(o["ld"], [])                                     # zwinięte: bez zapytań o stan kopii
        # wiersz na każdą część (WYGLAD.md), zwykłe słowa zamiast „commit”, „origin”, „pole github:”
        self.assertEqual(zw.count("<dt>Integracje</dt>"), 2)
        self.assertEqual(zw.count("<dt>Strona WWW</dt>"), 2)
        self.assertIn("zgodne z GitHubem", zw)
        self.assertIn("2 zmiany do wysłania", zw)
        self.assertNotIn("brak pola github:", zw)
        self.assertNotIn("commit", zw)
        self.assertIn("<a href=\"https://drive.google.com/drive/folders/1AbCdEfGhIjK\"", zw)
        self.assertIn("3 pozycje", zw)
        self.assertIn('aria-expanded="true"', rw)
        self.assertIn(">Zwiń<", rw)
        for k in ("GH:x", "GH:s", "DRV:x", "DRV:s"):
            self.assertIn(k, rw)
        self.assertEqual(o["ld2"], ["x", "s"])
        self.assertNotIn("<dt>", o["cz"])                                 # wybrana część: tylko jej repozytorium
        self.assertIn("GH:s", o["cz"])
        self.assertNotIn("GH:x", o["cz"])
        self.assertNotIn("GH:", o["off"])                                 # poza serwerem bez działań na kopii

    def test_polaczenia_meta(self):
        o = self.run_view("""PF.more['pj-con-meta']=true;
D.campaigns=[{project:'s'}];out.bez=pjxConView(top);out.inny=pjxConView(top.own);
D.campaigns=[];part.instagram='marka';out.karta=pjxConView(top);part.instagram='';out.nic=pjxConView(top);
D.publish={fb:{connected:true,pages:[{id:'1',name:'Strona Marki',project:'s',instagram:'marka'},{id:'2',name:'Inna',project:'',instagram:''}]}};
out.pol=pjxConView(part);top.facebook='Marka';out.wolne=pjxConView(top.own);""")
        bez = o["bez"]
        self.assertIn("Meta Business", bez)                               # kampania w części: karta w „Całość”
        self.assertIn("Niepołączone", bez)
        self.assertIn('data-nwchan="1"', bez)                             # ta sama droga co Kanały publikacji
        self.assertNotIn("Meta Business", o["inny"])                      # część główna bez kanałów: bez karty
        self.assertIn("Instagram @marka", o["karta"])                     # profil z karty projektu
        self.assertNotIn("Meta Business", o["nic"])
        self.assertIn("połączone", o["pol"])
        self.assertIn("Strona Marki", o["pol"])
        self.assertIn("Instagram @marka", o["pol"])
        self.assertNotIn("Niepołączone", o["pol"])
        self.assertIn('data-pjxfb="x"', o["wolne"])                       # wybór strony dla projektu bez strony
        self.assertIn("Facebook „Marka”", o["wolne"])                     # profil z karty (pole facebook:)
        self.assertIn(">Inna<", o["wolne"])

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
        self.assertIn('data-voice="x"', otw)
        self.assertIn("Mów</button>", otw)
        self.assertNotIn("nowa odpowiedź", o["po"])                       # po otwarciu odpowiedź przeczytana
        self.assertIn('data-pchat="s"', o["czesc"])                       # część: własna rozmowa
        self.assertIn("Oprogramowani · Strona WWW", o["czesc"])
        self.assertIn("Oprogramowani · Integracje", o["wlasna"])
        self.assertEqual(o["inny"], "")                                   # poza projektem i zadaniem bez rozmowy


@unittest.skipUnless(NODE, "brak node")
class Podglad(unittest.TestCase):
    """Zakładka Strona w „Całość”, przycisk „Otwórz podgląd” przy zadaniu oceny strony i link w odpowiedzi czatu (node)."""

    def run_js(self, body):
        code = panel_parts(read(PANEL).decode("utf-8"), ["esc", "pid2", "phref", "topP", "PTABS", "PTMAIN", "wwSites", "ptabsOf",
                                                         "ptMain", "WWC", "wwCur", "wwHref", "wwView", "partSw", "WWT", "wwTask",
                                                         "wwBtn", "wwHrefFor", "wwLinks", "chatText", "shortT", "attLabel",
                                                         "chatRef", "chatMsg"])
        js = """let LIVE=true;const pnMsg=()=>'',document={addEventListener(){}};
const top={id:'x',name:'Oprogramowani',partOf:'',partLabel:'Integracje'};
const part={id:'s',name:'Oprogramowani · Strona WWW',partOf:'x',partLabel:'Strona WWW',site:{dir:'site'},partsL:[]};
const inny={id:'y',name:'Sklep',partOf:'',partsL:[],site:{dir:'www'}};
top.partsL=[part];top.own=Object.assign({},top,{isOwn:true,partsL:[],own:null,name:'Oprogramowani · Integracje'});
const by={x:top,s:part,y:inny};const P=id=>by[id]||null;
const D={projects:[top]};
const out={};
%s
%s
JSON.stringify(out);
""" % (code, body)
        lines = js.rstrip().split("\n")
        lines[-1] = "console.log(" + lines[-1].rstrip(";") + ");"
        r = subprocess.run([NODE, "-"], input="\n".join(lines), capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_zakladka_strona_w_calosci(self):
        o = self.run_js("""const T=p=>ptabsOf(p).map(x=>x[0]);out.top=T(top);out.own=T(top.own);out.part=T(part);out.main=ptMain(top);out.n=T(top).length;
out.view=wwView(top);out.sw=partSw(top,'strona');
const s2={id:'s2',name:'Oprogramowani · Sklep',partOf:'x',partLabel:'Sklep',site:{dir:'sklep'},partsL:[]};by.s2=s2;top.partsL=[part,s2];
out.two=wwView(top);WWC.x='s2';out.two2=wwView(top);LIVE=false;out.off=wwView(top);""")
        # grupa projekt: bez Planu, Zadania pierwsze, Strona druga, Połączenia na końcu; wszystkie zakładki główne (bez „Więcej”)
        self.assertEqual(o["top"], ["tablica", "strona", "marketing", "etapy", "wskazniki", "ksiega", "polaczenia"])
        self.assertEqual(o["main"], o["n"])
        self.assertNotIn("strona", o["own"])                                     # część bez strony: bez zakładki
        self.assertIn("strona", o["part"])
        self.assertIn('data-ww="s"', o["view"])                                  # podgląd części ze stroną
        self.assertIn('href="#p-x-strona?cz=s"', o["view"])
        self.assertIn('class="pjx-cz"', o["sw"])                                 # wybór części przy nazwie (WYGLAD.md)
        self.assertIn('value="#p-x-strona"', o["sw"])                            # „Całość” zostaje na zakładce Strona
        self.assertIn('value="#p-x-tablica?cz=x"', o["sw"])                      # część bez strony: Zadania
        self.assertEqual(o["two"].count("data-wwpart="), 2)                      # dwie części ze stroną: wybór
        self.assertIn('data-ww="s"', o["two"])
        self.assertIn('data-ww="s2"', o["two2"])
        self.assertIn('data-wwpart="s2" data-wwtop="x" data-k="wwp:s2" aria-pressed="true"', o["two2"])
        self.assertNotIn("data-ww=", o["off"])

    def test_przycisk_otworz_podglad(self):
        o = self.run_js("""const t=(id,project,title,executor,refs)=>({id:id,project:project,title:title,executor:executor||'ty',detail:{refs:refs||[]}});
out.tytul=wwBtn(t('a','s','Oceń nową stronę w zakładce Strona'));
out.calosc=wwBtn(t('b','x','Obejrzyj podgląd strony i daj uwagi'));
out.mat=wwBtn(t('c','s','Przejrzyj i zatwierdź',null,[{path:'./site/'}]));
out.matIn=wwBtn(t('d','s','Przejrzyj',null,[{path:'site/src/App.tsx'}]));
out.inny=wwBtn(t('e','s','Zapłać fakturę',null,[{path:'docs/site.md'}]));
out.agent=wwBtn(t('f','s','Popraw stronę w zakładce Strona','claude'));
out.zgoda=wwBtn(Object.assign(t('g','s','Zatwierdź podgląd strony','claude'),{needsYou:'zgoda'}));
out.bez=wwBtn(t('h','y','Oceń stronę w zakładce Strona'));by.y.site=null;out.bez2=wwBtn(t('i','y','Oceń stronę w zakładce Strona'));""")
        for k in ("tytul", "calosc", "mat", "matIn", "zgoda"):
            with self.subTest(k):
                self.assertIn('href="#p-x-strona?cz=s"', o[k])
                self.assertIn(">Otwórz podgląd</a>", o[k])
        self.assertEqual((o["inny"], o["agent"]), ("", ""))                      # inne zadania i zadania agentów: bez
        self.assertIn('href="#p-y-strona"', o["bez"])                            # projekt bez części
        self.assertEqual(o["bez2"], "")

    def test_link_w_odpowiedzi_czatu(self):
        o = self.run_js("""const txt='Nową stronę zobaczysz w zakładce Strona przy części Strona WWW.';
out.pj=chatMsg({role:'claude',text:txt},'',top);out.cz=chatMsg({role:'claude',text:txt},'',part);
out.as=chatText(txt,{p:null});out.ty=chatMsg({role:'ty',text:txt},'',top);
out.md=chatText('Gotowe: [Otwórz podgląd](#p-x-strona?cz=s).',{p:null});
out.xss=chatText('[a](javascript:alert(1)) [b](#p-x" onclick="x)',{p:null});
D.projects=[top,inny];out.dwa=chatText('Podgląd jest w zakładce Strona.',{p:null});
out.sklep=chatText('Stronę Sklep zobaczysz w zakładce Strona.',{p:null});out.wiele=chatText(txt,{p:null});""")
        link = '<a href="#p-x-strona?cz=s" data-k="wwlink">zakładce Strona</a>'
        for k in ("pj", "cz", "as", "wiele"):
            with self.subTest(k):
                self.assertIn(link, o[k])
        self.assertNotIn("<a ", o["ty"])                                         # wiadomość właściciela bez linków
        self.assertIn('<a href="#p-x-strona?cz=s">Otwórz podgląd</a>', o["md"])
        self.assertNotIn("<a ", o["xss"])                                        # tylko adresy panelu (#…)
        self.assertNotIn("<a ", o["dwa"])                                        # nie wiadomo, która strona: bez linku
        self.assertIn('<a href="#p-y-strona" data-k="wwlink">zakładce Strona</a>', o["sklep"])


@unittest.skipUnless(NODE, "brak node")
class Kod(unittest.TestCase):
    """Strona projektu bez sekcji rozmowy, „Kod i pliki” i zakładki Plan; Esc zwija rozmowę; Serwer bez działań."""

    @classmethod
    def setUpClass(cls):
        cls.html = read(PANEL).decode("utf-8")

    def test_bez_starych_sekcji(self):
        v = panel_parts(self.html, ["vProjekt"])
        self.assertIn("pjxConView(p)", v)                                 # „Kod i pliki” → zakładka Połączenia
        self.assertIn("pjxDecyzje(p)+projBoard(p)", v)                    # Decyzje na górze Zadań
        self.assertNotIn("codeBox", self.html)
        self.assertNotIn("planView", self.html)
        self.assertNotIn("['plan','Plan']", self.html)
        # stary adres zakładki Plan prowadzi do Zadań; domyślna zakładka to Zadania
        self.assertIn("let p=P(rest),tab='tablica';", self.html)
        self.assertIn("if(tab==='plan'){tab='tablica';", self.html)
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
        SEL = "document.querySelector('[data-pjxcz]').selectedOptions[0].textContent"
        pg.goto(U + "#p-oprogramowani-onepager-strona"); pg.wait_for_selector("[data-pjxcz]")
        r["redirect"] = pg.evaluate("location.hash")
        r["cur"] = pg.evaluate(SEL)
        r["tabs"] = pg.locator(".ptabs > a").all_inner_texts()
        pg.goto(U + "#p-projekt-testowy-strona"); pg.wait_for_selector(".ww-root")
        r["calosc"] = [pg.evaluate("location.hash"), pg.locator(".ptabs > a[aria-current]").inner_text(),
                       pg.evaluate(SEL), pg.locator(".ww-root").get_attribute("data-ww")]
        pg.goto(U + "#p-projekt-testowy"); pg.wait_for_selector("[data-pjxcz]"); pg.wait_for_timeout(500)
        r["list"] = pg.locator("#plist a .nm").all_inner_texts()
        r["tabCur"] = pg.locator(".ptabs > a[aria-current]").inner_text()
        r["tag"] = pg.locator("#view").inner_text()
        pg.goto(U + "#p-projekt-testowy-polaczenia"); pg.wait_for_selector("#pcon-gh")
        pg.click("#pcon-gh [data-pjcon]"); pg.wait_for_timeout(300)
        r["det"] = pg.locator("#pcon-gh-det").is_visible()
        pg.click("#pcon-gh [data-pjcon]"); pg.wait_for_timeout(300)
        r["det2"] = pg.locator("#pcon-gh-det").is_visible()
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
    """Cała strona w Chromium: stary adres części, jeden projekt na liście, Połączenia, rozmowa (Enter, Esc)."""

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
                self.assertEqual(o["calosc"], ["#p-projekt-testowy-strona", "Strona", "Całość", "oprogramowani-onepager"])
                self.assertEqual(o["list"], ["Oprogramowani"])
                self.assertEqual(o["tabCur"], "Zadania")                  # domyślna zakładka
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
