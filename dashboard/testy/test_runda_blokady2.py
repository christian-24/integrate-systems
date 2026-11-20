"""Teraz i Blokady, runda 2 recenzji: kolejność korzeni (dzień, termin, dokładny zapas, bezpośrednie), zapas z czas:
(publikacja 0, szacunki policzone), zadania robione przez panel poza „Twoje”, odporność /api/data i skanu filmów,
Automat nagrań bez znikających pozycji, zakończone rozmowy w Teraz."""
import contextlib
import datetime
import io
import json
import os
import re
import unittest

from wspolne import Baza, server
from test_blokady import JS, PANEL, run_js

film = server.film

HARNESS = r"""
%(src)s
function build(spec){
  const L=spec.map(s=>({id:s.id,title:s.id,state:s.state||'todo',executor:s.ex||'claude',you:!!s.you,date:s.date||'',prio:s.prio||3,
    cost:('cost' in s)?s.cost:1,est:!!s.est,waits:(s.after||[]),miss:[],kids:[]}));
  const ix={};L.forEach(t=>{ix[t.id]=t});
  L.forEach(t=>{t.waits.forEach(w=>{if(ix[w])ix[w].kids.push(t.id)})});
  return L;
}
const cases=%(cases)s,out={};
Object.keys(cases).forEach(k=>{const m=bkGraph(build(cases[k]),'2026-11-19');
  out[k]={roots:m.roots.map(t=>t.id),blocked:m.blocked.map(t=>t.id),
    tight:Object.fromEntries(m.roots.map(t=>[t.id,m.tight(t)])),worst:Object.fromEntries(m.roots.map(t=>[t.id,m.slack(t).worst]))}});
JSON.stringify(out);
"""

CASES = {
    # oba trzeba zacząć dziś; agent z 3 zależnymi i terminem 21.11, Twoje z 1 zależnym i terminem dziś: najpierw dziś
    "w_dniu_termin": [
        {"id": "agent"}, {"id": "a1", "after": ["agent"], "cost": 2, "date": "2026-11-21"},
        {"id": "a2", "after": ["agent"]}, {"id": "a3", "after": ["agent"]},
        {"id": "film", "ex": "ty", "cost": 0.25}, {"id": "pub", "after": ["film"], "cost": 0.25, "date": "2026-11-19"},
    ],
    # spóźniony o 10 dni (1 zależny) przed „ciasno” z 5 zależnymi (jak pm.py: po terminie, najstarsze najpierw)
    "spoznione_najpierw": [
        {"id": "ciasny"}] + [{"id": "c%d" % i, "after": ["ciasny"], "cost": 2, "date": "2026-11-20"} for i in range(5)] + [
        {"id": "stary"}, {"id": "s1", "after": ["stary"], "date": "2026-11-09"},
    ],
    # bez terminów: liczy się liczba odblokowanych bezpośrednio (unlockCount), nie wszystkich dalej
    "bezposrednie": [
        {"id": "szeroki"}, {"id": "x1", "after": ["szeroki"]}, {"id": "x2", "after": ["szeroki"]},
        {"id": "dlugi"}, {"id": "y1", "after": ["dlugi"]}, {"id": "y2", "after": ["y1"]}, {"id": "y3", "after": ["y2"]},
    ],
    # publikacja (koszt 0) nie daje fałszywego „ciasno”; zadania bez czas: policzone w szacunku
    "publikacja_zero": [{"id": "R", "cost": 0.25}, {"id": "P", "after": ["R"], "cost": 0, "date": "2026-11-19"}],
    "szacunek": [{"id": "R", "est": True}, {"id": "S", "after": ["R"], "est": True},
                 {"id": "T", "after": ["S"], "est": True, "date": "2026-11-20"}],
}

MODEL = r"""
const D={todayKey:'2026-11-19',dayMinutes:120,projects:[{id:'p',state:'active',priority:2}],tasks:%(tasks)s};
const P=id=>D.projects.find(p=>p.id===id)||null,isDay=k=>/^\d{4}-\d\d-\d\d$/.test(k||'');
const needsMe=t=>t.state!=='done'&&(t.executor==='ty'||!!t.needsYou);
const pl=(n,a,b,c)=>n===1?a:(n%%10>=2&&n%%10<=4&&(n%%100<10||n%%100>=20))?b:c;
let FX=null;const facts=()=>FX||(FX={open:D.tasks.filter(t=>t.state!=='done')});
const bkPanelDoes=t=>/^Nagraj film/.test(t.title);
%(graph)s
%(model)s
const m=bkModel();
const RES=JSON.stringify({you:bkYouL().map(n=>n.id),cost:Object.fromEntries(D.tasks.map(t=>[t.id,[m.byId(t.id).cost,m.byId(t.id).est]]))});
RES;
"""


def task(id, title, **kw):
    t = {"id": id, "title": title, "project": "p", "file": "ZADANIA.md", "state": "todo", "executor": "claude",
         "needsYou": "", "date": "", "waits": [], "unlocksL": [], "minutes": 0, "kind": "zadanie"}
    t.update(kw)
    return t


def src(name):
    with open(PANEL, encoding="utf-8") as f:
        html = f.read()
    return re.search(r"/\*%s:start\*/(.*?)/\*%s:end\*/" % (name, name), html, re.S).group(1)


@unittest.skipUnless(JS, "brak silnika JS (osascript albo node)")
class Kolejnosc(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        r = run_js(HARNESS % {"src": src("bkGraph"), "cases": json.dumps(CASES)})
        if r.returncode != 0:
            raise AssertionError("JS: " + r.stderr.strip())
        cls.out = json.loads(r.stdout)

    def test_w_tym_samym_dniu_najblizszy_termin(self):
        # runda 3: kolejność = wyświetlany zapas; agent ma zapas 0 (2 dni pracy do 21.11), film 0,5 dnia
        self.assertEqual(self.out["w_dniu_termin"]["roots"], ["agent", "film"])

    def test_spoznione_najstarsze_przed_ciasnym(self):
        self.assertEqual(self.out["spoznione_najpierw"]["roots"], ["stary", "ciasny"])

    def test_liczba_bezposrednich_jak_raport_pm(self):
        self.assertEqual(self.out["bezposrednie"]["roots"], ["szeroki", "dlugi"])

    def test_publikacja_bez_kosztu(self):
        o = self.out["publikacja_zero"]
        self.assertIsNone(o["tight"]["R"])
        self.assertEqual(o["worst"]["R"]["slack"], 0.74)          # 0,25 + 0,01 (publikacja): zapas < 1 dnia, „zacznij dziś”

    def test_szacunek_policzony(self):
        t = self.out["szacunek"]["tight"]["R"]
        self.assertEqual((t["steps"], t["days"], t["unk"], t["n"]), (3, 2, 3, 3))


@unittest.skipUnless(JS, "brak silnika JS (osascript albo node)")
class ModelPanelu(unittest.TestCase):
    def test_film_robi_panel_publikacja_zero(self):
        tasks = [
            task("f", "Nagraj film A", executor="ty", unlocksL=[{"id": "p1", "title": "Opublikuj film A", "done": False}]),
            task("p1", "Opublikuj film A", kind="publikacja", waits=["Nagraj film A"]),
            task("d", "Domena", executor="ty", minutes=60, unlocksL=[{"id": "s", "title": "Strona", "done": False}]),
            task("s", "Strona", waits=["Domena"]),
        ]
        r = run_js(MODEL % {"tasks": json.dumps(tasks), "graph": src("bkGraph"), "model": src("bkModel")})
        self.assertEqual(r.returncode, 0, r.stderr)
        o = json.loads(r.stdout)
        self.assertEqual(o["you"], ["d"])                          # „Nagraj film” robi panel: nie Twoje na teraz
        self.assertEqual(o["cost"]["p1"], [0, False])              # publikację wysyła publikator
        self.assertEqual(o["cost"]["d"], [0.5, False])             # 60 min z 120 min dnia
        self.assertEqual(o["cost"]["s"], [0.5, True])              # bez czas: szacunek (agent pół dnia, runda 3)


class Odpornosc(Baza):
    def post(self, name, state=None, scenario=False):
        pf = os.path.join(self.folder, "posty", name)
        os.makedirs(pf, exist_ok=True)
        if state is not None:
            with open(os.path.join(pf, film.STATE), "w", encoding="utf-8") as f:
                json.dump(state, f)
        if scenario:
            with open(os.path.join(pf, film.SCENARIO), "w", encoding="utf-8") as f:
                f.write("{}")
        return pf

    def test_blad_czesci_nie_daje_500(self):
        orig_s, orig_p = server.studio_summary, server.get_publisher

        def boom(*a, **kw):
            raise KeyError("x")
        server.studio_summary, server.get_publisher = boom, boom
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                data = server.build_data()
        finally:
            server.studio_summary, server.get_publisher = orig_s, orig_p
        self.assertTrue(data["tasks"])
        self.assertIsNone(data["publish"])
        self.assertEqual(data["studio"], {})
        self.assertIn("studio", data["activity"]["error"])
        self.assertIn("publikacje", data["activity"]["error"])

    def test_ostatnia_dobra_odpowiedz(self):
        server.data_invalidate()
        good = server.data_cached(ttl=0)
        orig = server.build_data

        def boom():
            raise RuntimeError("x")
        server.build_data = boom
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                got = json.loads(server.data_cached(ttl=0))
            # ostatnia dobra odpowiedź ze znacznikiem: panel ostrzega, że dane są sprzed błędu (runda 3)
            ok = json.loads(good)
            self.assertEqual(got["generatedAt"], ok["generatedAt"])
            self.assertEqual(got["stale"], {"since": ok["generatedAt"], "error": "RuntimeError"})
            self.assertIn("błąd odczytu", got["activity"]["error"])
            self.assertEqual(got["tasks"], ok["tasks"])
        finally:
            server.build_data = orig

    def test_jeden_zly_folder_nie_wymazuje_filmow(self):
        now = datetime.datetime.now().replace(microsecond=0)
        self.post("2026-11-20-dobry", {"state": "done", "at": now.isoformat()})
        bad = self.post("2026-11-21-zly", {"state": "done", "at": now.isoformat()})
        orig = film.read_state

        def read(pf):
            if os.path.basename(pf) == os.path.basename(bad):
                raise TypeError("uszkodzony")
            return orig(pf)
        film.read_state = read
        try:
            _, index = server.load_projects(resolve=False)
            got = {f["post"]: f for f in server.film_activity(index, now)}
        finally:
            film.read_state = orig
        self.assertEqual(got["2026-11-20-dobry"]["state"], "done")
        self.assertEqual(got["2026-11-21-zly"]["state"], "error")
        self.assertIn("TypeError", got["2026-11-21-zly"]["error"])

    def test_pamiec_filmow_nowy_wyjatek(self):
        orig = server.film_activity

        def boom(*a, **kw):
            raise OSError("zniknął")
        server.film_activity = boom
        server._films_cache.update(at=0.0, key=None)
        try:
            _, index = server.load_projects(resolve=False)
            errs = []
            for _ in range(2):
                try:
                    server.films_cached(index)
                except RuntimeError as e:
                    errs.append(e)
        finally:
            server.film_activity = orig
            server._films_cache.update(at=0.0, key=None, error=None)
        self.assertEqual(len(errs), 2)
        self.assertIsNot(errs[0], errs[1])
        self.assertIn("zniknął", str(errs[1]))

    def _auto(self, start):
        rec = film.Recorder(python="/bin/false")
        rec.available = lambda kind=None: True
        rec.start = start
        saved = server._recorder
        server._recorder = rec
        try:
            server.auto_record()
        finally:
            server._recorder = saved

    def test_start_nie_ruszyl_zostaje_blad(self):
        pf = self.post("2026-11-20-q", None, scenario=True)
        orig = film.describe
        film.describe = lambda folder: {"kind": "pokaz", "error": ""}
        try:
            self._auto(lambda folder, title="": (409, "Film już się nagrywa."))
        finally:
            film.describe = orig
        st = film.read_state(pf)
        self.assertEqual(st["state"], "error")
        self.assertIn("nie ruszyło", st["error"])
        self.assertIsNone(server.film_pending(pf))                  # ta wersja nie wraca w kółko

    def test_osierocone_od_razu_bledem(self):
        at = (datetime.datetime.now() - datetime.timedelta(seconds=server.FILM_GRACE + 30)).isoformat(timespec="seconds")
        pf = self.post("2026-11-20-o", {"state": "running", "at": at, "host": film.HOST, "pid": 999999, "scenario": 3.0})
        self._auto(lambda folder, title="": (202, ""))
        st = film.read_state(pf)
        self.assertEqual((st["state"], st["error"], st["scenario"]), ("error", server.FILM_ORPHAN, 3.0))

    def test_blad_automatu_widoczny(self):
        server._auto_rec["error"] = "OSError: dysk"
        try:
            _, index = server.load_projects(resolve=False)
            a = server.activity({"projectsSource": "registry", "tasks": [], "agents": {}}, index, self.manager)
        finally:
            server._auto_rec["error"] = ""
        self.assertIn("Automat nagrań", a["error"])

    def test_zakonczone_rozmowy(self):
        m = self.manager
        for f, err in (("a.json", ""), ("b.json", "Odpowiedź przerwana.")):
            path = os.path.join(self.tmp, f)
            m._chat_live.add(path)
            m._chat_meta[path] = {"taskId": f, "project": "p", "file": "ZADANIA.md", "title": "Rozmowa " + f,
                                  "since": "2026-11-19T10:00:00"}
            m._chat_end(path, "" if err else "odpowiedź", "", err)
        got = m.chat_recent()
        self.assertEqual([(c["title"], c["ok"]) for c in got], [("Rozmowa b.json", False), ("Rozmowa a.json", True)])
        self.assertEqual(got[0]["error"], "Odpowiedź przerwana.")
        self.assertEqual(m.chat_pending(), [])


if __name__ == "__main__":
    unittest.main()
