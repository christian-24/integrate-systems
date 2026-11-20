"""Blokady: model zależności bkGraph z panel.html (czysta funkcja JS), uruchamiany przez JavaScriptCore (osascript na Macu).

Bez osascript (np. serwer z Linuksem) przez node; bez obu testy są pomijane. Sprawdzają: korzenie, liczby zależnych (bezpośrednie i razem),
cykle bez korzenia i pod korzeniem, po: bez pasującego zadania, wspólnych następników, zablokowane korzenie i kolejność.
"""
import json
import os
import re
import shutil
import subprocess
import unittest

PANEL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "panel.html")
OSA = shutil.which("osascript")
NODE = shutil.which("node") or shutil.which("nodejs")
JS = OSA or NODE


def run_js(js):
    """JavaScriptCore przez osascript (Mac) albo node (np. serwer z Linuksem): wynik ostatniego wyrażenia jako tekst."""
    if OSA:
        return subprocess.run([OSA, "-l", "JavaScript", "-e", js], capture_output=True, text=True, timeout=60)
    lines = js.rstrip().split("\n")
    lines[-1] = "console.log(" + lines[-1].rstrip().rstrip(";") + ");"
    return subprocess.run([NODE, "-e", "\n".join(lines)], capture_output=True, text=True, timeout=60)

HARNESS = r"""
%(src)s
function build(spec){
  const L=spec.map(s=>({id:s.id,title:s.id,state:s.state||'todo',executor:s.ex||'claude',you:!!s.you,date:s.date||'',prio:s.prio||3,cost:s.cost||1,
    waits:(s.after||[]),miss:(s.miss||[]),kids:[]}));
  const ix={};L.forEach(t=>{ix[t.id]=t});
  L.forEach(t=>{t.waits.forEach(w=>{if(ix[w])ix[w].kids.push(t.id)})});
  L.forEach(t=>{t.waits=t.waits.concat(t.miss)});
  return L;
}
const cases=%(cases)s,out={};
Object.keys(cases).forEach(k=>{const t0=Date.now(),m=bkGraph(build(cases[k]),'2026-11-19'),I={};
  cases[k].filter(s=>k!=='dlugi'||s.id==='c0').forEach(s=>{const t=m.byId(s.id),i=m.info(t);I[s.id]={count:i.count,direct:i.direct,next:i.next,late:i.late,chain:m.chain(t),cycle:i.cycle.map(x=>x.id),
    tight:(x=>x?{steps:x.steps,days:x.days,id:x.id}:null)(m.tight(t)),early:m.early(t).map(x=>x.id),
    crit:Object.keys(m.crit(t,50)).sort()}});
  out[k]={roots:m.roots.map(t=>t.id),blocked:m.blocked.map(t=>t.id),fix:m.fix.map(x=>[x.t.id,x.why.map(w=>w.kind)]),
    via:m.fix.map(x=>[x.t.id,x.why.map(w=>w.via||'')]),info:I,ms:Date.now()-t0,
    kids:m.roots.length?m.kids(m.roots[0]).map(t=>t.id):[]}});
JSON.stringify(out);
"""

CASES = {
    "lancuch": [{"id": "A"}, {"id": "B", "after": ["A"]}, {"id": "C", "after": ["B"]}],
    "cykl_bez_korzenia": [{"id": "X", "after": ["Y"]}, {"id": "Y", "after": ["X"]}, {"id": "O", "after": ["X"]}],
    "cykl_pod_korzeniem": [{"id": "R"}, {"id": "P", "after": ["R", "Q"]}, {"id": "Q", "after": ["P"]}],
    "brak_poprzednika": [{"id": "M", "miss": ["nie ma takiego"]}, {"id": "N", "after": ["M"]}],
    "diament": [{"id": "R"}, {"id": "A", "after": ["R"]}, {"id": "B", "after": ["R"]}, {"id": "D", "after": ["A", "B"]}],
    "zablokowany": [{"id": "Z", "state": "blocked"}, {"id": "W", "after": ["Z"]}, {"id": "V", "after": ["W"]}],
    "kolejnosc": [
        {"id": "duzo"}, {"id": "d1", "after": ["duzo"], "date": "2026-12-20"}, {"id": "d2", "after": ["duzo"]},
        {"id": "d3", "after": ["duzo"]},
        {"id": "pilne"}, {"id": "p1", "after": ["pilne"], "date": "2026-11-18"},
        {"id": "moje", "ex": "ty"}, {"id": "m1", "after": ["moje"]},
        {"id": "maly"}, {"id": "s1", "after": ["maly"]},
    ],
    "zgoda_to_twoje": [{"id": "agent"}, {"id": "a1", "after": ["agent"]}, {"id": "a2", "after": ["agent"]},
                       {"id": "odbior", "you": True}, {"id": "o1", "after": ["odbior"]}],
    "zapas_i_kolejnosc": [{"id": "R"}, {"id": "B", "after": ["R"], "date": "2026-11-25"},
                          {"id": "C", "after": ["B"], "date": "2026-11-20"}, {"id": "D", "after": ["C"]}],
    "zablokowany_z_brakiem": [{"id": "Z", "state": "blocked", "miss": ["literówka"]}],
    "cykl_wyzej": [{"id": "X", "after": ["Y"]}, {"id": "Y", "after": ["X"]}, {"id": "O", "after": ["X"]}],
}
# gęste cykle: dawniej czas rósł wykładniczo (wszystkie ścieżki proste), teraz składowe spójne i jeden przebieg
CASES["gesty_cykl"] = [{"id": "g%d" % i, "after": ["g%d" % j for j in range(10) if j != i]} for i in range(10)]
CASES["pierscien"] = [{"id": "r%d" % i, "after": ["r%d" % ((i + 1) % 60), "r%d" % ((i + 2) % 60)]} for i in range(60)]
CASES["pierscien"].append({"id": "start"})
CASES["pierscien"][0]["after"].append("start")
# fałszywy alarm z rundy 3: krótka gałąź z bliskim terminem i długa z dalekim — każda ścieżka liczona osobno
CASES["zapas_na_sciezke"] = [{"id": "R"}, {"id": "A", "after": ["R"], "date": "2026-11-20"},
                             {"id": "B", "after": ["R"]}, {"id": "C", "after": ["B"]}, {"id": "D", "after": ["C"]},
                             {"id": "E", "after": ["D"], "date": "2027-01-20"}]
# ścieżka krytyczna: krótka gałąź, która jutro przekroczy termin, wygrywa z długą bez terminów
CASES["krytyczna"] = [{"id": "R"}, {"id": "A", "after": ["R"]}, {"id": "A2", "after": ["A"], "date": "2026-11-20"},
                      {"id": "B", "after": ["R"]}, {"id": "C", "after": ["B"]}, {"id": "D", "after": ["C"]}, {"id": "F", "after": ["D"]}]
# czas: Twojego zadania: 3 dni pracy na jednym kroku
CASES["koszt"] = [{"id": "R"}, {"id": "K", "after": ["R"], "cost": 3, "date": "2026-11-21"}]
CASES["koszt_korzenia"] = [{"id": "R", "cost": 3}, {"id": "K", "after": ["R"], "date": "2026-11-21"}]
CASES["krotkie"] = [{"id": "R", "cost": 0.25}] + [{"id": "k%d" % i, "after": ["R" if i == 0 else "k%d" % (i - 1)],
                                                   "cost": 0.0625} for i in range(5)]
CASES["krotkie"][-1]["date"] = "2026-11-19"
CASES["wlasny_termin"] = [{"id": "R", "cost": 2, "date": "2026-11-19"}, {"id": "X", "after": ["R"]}]
CASES["pilnosc"] = [
    {"id": "duzo"}] + [{"id": "d%d" % i, "after": ["duzo"], "date": "2026-12-20"} for i in range(5)] + [
    {"id": "ciasny"}, {"id": "c1", "after": ["ciasny"], "cost": 2, "date": "2026-11-20"},
    {"id": "moje", "ex": "ty"}, {"id": "m1", "after": ["moje"]}, {"id": "m2", "after": ["moje"]},
    {"id": "dzis", "date": "2026-11-19"}, {"id": "z1", "after": ["dzis"]},
    {"id": "zb_pozno", "state": "blocked"}, {"id": "zb1", "after": ["zb_pozno"]}, {"id": "zb2", "after": ["zb_pozno"]},
    {"id": "zb_sam_po_terminie", "state": "blocked", "date": "2026-11-10"},
]
# długi łańcuch: bez rekurencji (dawniej Tarjan rekurencyjny mógł dać RangeError)
CASES["dlugi"] = [{"id": "c0"}] + [{"id": "c%d" % i, "after": ["c%d" % (i - 1)]} for i in range(1, 5000)]


@unittest.skipUnless(JS, "brak silnika JS (osascript albo node)")
class Graf(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(PANEL, encoding="utf-8") as f:
            html = f.read()
        src = re.search(r"/\*bkGraph:start\*/(.*?)/\*bkGraph:end\*/", html, re.S).group(1)
        js = HARNESS % {"src": src, "cases": json.dumps(CASES)}
        r = run_js(js)
        if r.returncode != 0:
            raise AssertionError("JS: " + r.stderr.strip())
        cls.out = json.loads(r.stdout)

    def test_lancuch(self):
        o = self.out["lancuch"]
        self.assertEqual(o["roots"], ["A"])
        self.assertEqual((o["info"]["A"]["count"], o["info"]["A"]["direct"], o["info"]["A"]["chain"]), (2, 1, 2))
        self.assertEqual(o["fix"], [])

    def test_cykl_bez_korzenia_widoczny(self):
        o = self.out["cykl_bez_korzenia"]
        self.assertEqual(o["roots"], [])
        fix = dict((k, v) for k, v in o["fix"])
        self.assertEqual(fix["X"], ["cycle"])
        self.assertEqual(fix["Y"], ["cycle"])
        self.assertEqual(fix["O"], ["orphan"])          # czeka na zadanie z cyklu: też do poprawy

    def test_cykl_pod_korzeniem(self):
        o = self.out["cykl_pod_korzeniem"]
        self.assertEqual(o["roots"], ["R"])
        self.assertEqual(o["info"]["R"]["count"], 2)    # P i Q, każde raz
        self.assertEqual(sorted(k for k, _ in o["fix"]), ["P", "Q"])

    def test_brak_poprzednika(self):
        o = self.out["brak_poprzednika"]
        self.assertEqual(o["roots"], [])                # M czeka na fragment bez zadania: nie jest „do zrobienia najpierw”
        self.assertIn(["M", ["missing"]], o["fix"])
        self.assertIn(["N", ["orphan"]], o["fix"])

    def test_diament_liczony_raz(self):
        o = self.out["diament"]
        self.assertEqual((o["info"]["R"]["count"], o["info"]["R"]["direct"]), (3, 2))
        self.assertEqual(o["info"]["R"]["chain"], 2)

    def test_zablokowany_nie_jest_korzeniem(self):
        o = self.out["zablokowany"]
        self.assertEqual(o["roots"], [])
        self.assertEqual(o["blocked"], ["Z"])
        self.assertEqual(o["fix"], [])                  # W i V są pod zablokowanym, nie „do poprawy”

    def test_kolejnosc_zapas_liczba_twoje(self):
        o = self.out["kolejnosc"]
        # pilność z zapasu (po terminie najpierw), potem najwięcej zależnych; bez terminów: Twoje przed agentem
        self.assertEqual(o["roots"], ["pilne", "duzo", "moje", "maly"])
        self.assertEqual((o["info"]["pilne"]["late"], o["info"]["pilne"]["next"]), (1, "2026-11-18"))
        self.assertEqual(o["info"]["duzo"]["next"], "2026-12-20")

    def test_zgoda_i_odbior_to_twoje(self):
        o = self.out["zgoda_to_twoje"]
        # bez terminów: więcej zależnych wyżej, także gdy to zadanie agenta (runda 1: agent nie spada pod Twoje)
        self.assertEqual(o["roots"], ["agent", "odbior"])

    def test_bez_zapasu_i_zla_kolejnosc(self):
        o = self.out["zapas_i_kolejnosc"]
        self.assertEqual(o["info"]["R"]["chain"], 3)
        # do C (jutro) 3 dni pracy (R, B, C), a są 2 dni (dziś i jutro): zapas -1
        self.assertEqual(o["info"]["R"]["tight"], {"steps": 3, "days": 2, "id": "C"})
        self.assertEqual(o["info"]["C"]["early"], ["B"])            # C ma termin przed poprzednikiem B
        self.assertEqual(o["info"]["B"]["early"], [])
        self.assertIsNone(self.out["lancuch"]["info"]["A"]["tight"])

    def test_zablokowany_tylko_w_zablokowanych(self):
        o = self.out["zablokowany_z_brakiem"]
        self.assertEqual(o["blocked"], ["Z"])
        self.assertEqual(o["fix"], [])

    def test_powod_wyzej_w_lancuchu(self):
        via = dict((k, v) for k, v in self.out["cykl_wyzej"]["via"])
        self.assertEqual(via["O"], ["cycle"])
        via = dict((k, v) for k, v in self.out["brak_poprzednika"]["via"])
        self.assertEqual(via["N"], ["missing"])

    def test_gesty_cykl_szybko(self):
        for k in ("gesty_cykl", "pierscien"):
            self.assertLess(self.out[k]["ms"], 2000, k)
        o = self.out["pierscien"]
        self.assertEqual(o["roots"], ["start"])
        self.assertEqual(o["info"]["start"]["count"], 60)
        self.assertEqual(o["info"]["start"]["chain"], 60)            # cykl jako jeden węzeł: 59 kroków w środku + 1

    def test_zapas_liczony_na_sciezke(self):
        o = self.out["zapas_na_sciezke"]
        self.assertEqual(o["info"]["R"]["chain"], 4)
        self.assertIsNone(o["info"]["R"]["tight"])                 # A jest o krok od R i ma dzień: bez alarmu

    def test_sciezka_krytyczna_po_zapasie(self):
        o = self.out["krytyczna"]
        self.assertEqual(o["info"]["R"]["crit"], ["A", "A2", "R"])  # nie najdłuższa gałąź B-C-D-F
        self.assertEqual(o["info"]["R"]["tight"], {"steps": 3, "days": 2, "id": "A2"})
        # bez terminów: najdłuższy łańcuch
        self.assertEqual(self.out["lancuch"]["info"]["A"]["crit"], ["A", "B", "C"])

    def test_czas_zadania_w_dniach(self):
        self.assertEqual(self.out["koszt"]["info"]["R"]["tight"], {"steps": 4, "days": 3, "id": "K"})
        # praca nad samym korzeniem się liczy: korzeń 3 dni, zależny pojutrze (3 dni z dzisiejszym, razem 4 dni pracy)
        self.assertEqual(self.out["koszt_korzenia"]["info"]["R"]["tight"], {"steps": 4, "days": 3, "id": "K"})
        # krótkie zadania (ułamek dnia z czas:) nie dają fałszywego „ciasno”
        self.assertIsNone(self.out["krotkie"]["info"]["R"]["tight"])
        # własny termin korzenia też: 2 dni pracy na dziś
        self.assertEqual(self.out["wlasny_termin"]["info"]["R"]["tight"], {"steps": 2, "days": 1, "id": "R"})

    def test_ciasne_i_dzisiejsze_na_gorze(self):
        o = self.out["pilnosc"]
        # „ciasno” (1 zależny) przed korzeniem z 5 zależnymi za miesiąc; Twoje bez terminu pod agentem z terminem dziś
        self.assertEqual(o["roots"], ["ciasny", "dzis", "duzo", "moje"])
        self.assertEqual(o["blocked"], ["zb_pozno", "zb_sam_po_terminie"][::-1])

    def test_dlugi_lancuch_bez_rekurencji(self):
        o = self.out["dlugi"]
        self.assertEqual(o["roots"], ["c0"])
        self.assertEqual((o["info"]["c0"]["count"], o["info"]["c0"]["chain"]), (4999, 4999))
        self.assertLess(o["ms"], 3000)


MODEL = r"""
const D={todayKey:'2026-11-19',projects:[{id:'p',state:'active',priority:2},{id:'q',state:'paused',priority:1}],tasks:%(tasks)s};
const P=id=>D.projects.find(p=>p.id===id)||null,isDay=k=>/^\d{4}-\d\d-\d\d$/.test(k||'');
const needsMe=t=>t.state!=='done'&&(t.executor==='ty'||!!t.needsYou);
const pl=(n,a,b,c)=>n===1?a:(n%%10>=2&&n%%10<=4&&(n%%100<10||n%%100>=20))?b:c;
let FX=null;const facts=()=>FX||(FX={open:D.tasks.filter(t=>t.state!=='done')});
%(graph)s
%(model)s
const m=bkModel(),y=bkYouL();
const RES=JSON.stringify({roots:m.roots.map(n=>n.id),fix:m.fix.map(x=>[x.t.id,x.why.map(w=>w.kind)]),you:y.map(n=>n.id),
  kids:Object.fromEntries(D.tasks.filter(t=>m.byId(t.id)).map(t=>[t.id,m.kids(m.byId(t.id)).map(n=>n.id)])),
  n:bkYouN(),txt:bkYouTxt(bkYouN()),pf:bkYouL('q').map(n=>n.id)});
RES;
"""


def task(id, title, **kw):
    t = {"id": id, "title": title, "project": "p", "file": "ZADANIA.md", "state": "todo", "executor": "claude",
         "needsYou": "", "date": "", "waits": [], "unlocksL": []}
    t.update(kw)
    return t


@unittest.skipUnless(JS, "brak silnika JS (osascript albo node)")
class Model(unittest.TestCase):
    """bkModel: dane panelu (unlocksL z serwera, waits z frontu) → graf; duplikat tytułu, brakujące po:, Twoje."""

    def test_model_z_danych_panelu(self):
        tasks = [
            task("t1", "Domena", executor="ty", unlocksL=[{"id": "t2", "title": "Strona", "done": False},
                                                          {"id": "", "title": "Wpis", "done": False}]),
            task("t2", "Strona", waits=["Domena"]),
            task("t3", "Wpis", waits=["Domena"]),
            task("t4", "Wpis", file="INNY.md"),                     # ten sam tytuł w innym pliku: nie jest dzieckiem t1
            task("t5", "Odbiór projektu", needsYou="odbiór", unlocksL=[{"id": "t6", "title": "Faktura", "done": False}]),
            task("t6", "Faktura", waits=["Odbiór projektu"]),
            task("t7", "Kampania", state="blocked", waits=["literówka"], missing=["literówka"]),
            task("t8", "Post", waits=["nie ma takiego"], missing=["nie ma takiego"]),
            task("t9", "Wstrzymany", project="q", executor="ty", unlocksL=[{"id": "t10", "title": "X", "done": False}]),
            task("t10", "X", project="q", waits=["Wstrzymany"]),
        ]
        with open(PANEL, encoding="utf-8") as f:
            html = f.read()
        graph = re.search(r"/\*bkGraph:start\*/(.*?)/\*bkGraph:end\*/", html, re.S).group(1)
        model = re.search(r"/\*bkModel:start\*/(.*?)/\*bkModel:end\*/", html, re.S).group(1)
        js = MODEL % {"tasks": json.dumps(tasks), "graph": graph, "model": model}
        r = run_js(js)
        self.assertEqual(r.returncode, 0, r.stderr)
        o = json.loads(r.stdout)
        self.assertEqual(sorted(o["kids"]["t1"]), ["t2", "t3"])     # „Wpis” bez id: po tytule w tym samym pliku
        self.assertEqual(o["you"], ["t1", "t5"])                     # kto: ty i odbiór; projekt wstrzymany pominięty
        # model ma wszystkie projekty (filtr aktywnych jest w widoku); Twoje na górze
        self.assertEqual([x for x in o["roots"] if x != "t9"][:2], ["t1", "t5"])
        self.assertIn(["t8", ["missing"]], o["fix"])
        self.assertNotIn("t7", [k for k, _ in o["fix"]])             # [!] tylko w Zablokowanych
        self.assertEqual(o["n"], {"tasks": 2, "n": 3, "all": 3})
        self.assertEqual(o["txt"], "Twoje zadania wstrzymują 3 inne zadania")
        self.assertEqual(o["pf"], ["t9"])                            # filtr na projekt wstrzymany: jego Twoje zadania


if __name__ == "__main__":
    unittest.main()
