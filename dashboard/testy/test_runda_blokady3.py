"""Teraz i Blokady, runda 3 recenzji: po: między plikami projektu (kampania czeka na zadanie z ZADANIA.md),
kolejność korzeni = wyświetlany zapas, własna data zadania jako termin, „ruszy od razu” osobno od „odblokowuje”,
koszt cyklu jako suma, znacznik „stale” w /api/data po błędzie budowy, log błędu raz na zmianę treści
oraz pilnowanie zmian w panelu (zerowanie FX w applyAgents, film przypisany tylko jawnie)."""
import contextlib
import io
import json
import re
import unittest

import os

from wspolne import Baza, server, projekt
from test_blokady import JS, PANEL, run_js
from test_runda_blokady2 import src


def t(title, file="ZADANIA.md", line=1, state="todo", after=(), project="p", **kw):
    d = {"id": "%s|%s|%d" % (project, file, line), "project": project, "file": file, "line": line, "title": title,
         "state": state, "after": list(after), "executor": "ty", "date": ""}
    d.update(kw)
    return d


class PoMiedzyPlikami(unittest.TestCase):
    def test_kampania_czeka_na_zadanie_z_zadania_md(self):
        dpa = t("Potwierdź DPA z dostawcami LLM", line=97, state="done")
        pub = t("Opublikuj post 1", file="kampanie/rytm.md", line=26, after=["Potwierdź DPA"])
        projekt.link_after([dpa, pub])
        self.assertEqual(pub["waitingFor"], [{"title": dpa["title"], "done": True, "id": dpa["id"]}])
        self.assertEqual(projekt.waiting_titles(pub), [])               # publikator wypuści post

    def test_najpierw_ten_sam_plik(self):
        a = t("Nagraj film A", line=5)
        b = t("Nagraj film A (kampania)", file="kampanie/rytm.md", line=3)
        c = t("Opublikuj film A", file="kampanie/rytm.md", line=9, after=["nagraj film a"])
        projekt.link_after([a, b, c])
        self.assertEqual(c["waitingFor"][0]["id"], b["id"])
        self.assertEqual(b["unlocks"][0]["id"], c["id"])
        self.assertEqual(a["unlocks"], [])

    def test_zadania_md_przed_innymi_kampaniami_i_brak(self):
        z = t("Domena", line=4)
        k = t("Domena (inna kampania)", file="kampanie/a.md", line=2)
        x = t("Post", file="kampanie/b.md", line=2, after=["domena", "nie ma takiego"])
        y = t("Domena", line=2, project="q")                            # inny projekt: nie pasuje
        projekt.link_after([z, k, x, y])
        self.assertEqual(x["waitingFor"][0]["id"], z["id"])
        self.assertEqual(x["waitingFor"][1], {"title": "nie ma takiego", "done": False, "id": ""})
        self.assertEqual([u["id"] for u in z["unlocks"]], [x["id"]])
        self.assertEqual(y["unlocks"], [])


HARNESS = r"""
%(src)s
function build(spec){
  const L=spec.map(s=>({id:s.id,title:s.id,state:s.state||'todo',executor:s.ex||'claude',you:!!s.you,date:s.date||'',prio:s.prio||3,
    cost:('cost' in s)?s.cost:1,est:!!s.est,waits:(s.after||[]).concat(s.miss||[]),miss:(s.miss||[]),kids:[]}));
  const ix={};L.forEach(t=>{ix[t.id]=t});
  L.forEach(t=>{(t.waits||[]).forEach(w=>{if(ix[w])ix[w].kids.push(t.id)})});
  return L;
}
const cases=%(cases)s,out={};
Object.keys(cases).forEach(k=>{const m=bkGraph(build(cases[k]),'2026-11-19');
  out[k]={roots:m.roots.map(t=>t.id),grp:Object.fromEntries(m.roots.map(t=>[t.id,m.grp(t)])),
    urg:Object.fromEntries(m.roots.map(t=>[t.id,m.urgX(t)])),
    info:Object.fromEntries(m.roots.map(t=>{const i=m.info(t);return [t.id,{direct:i.direct,ready:i.ready,other:i.other}]})),
    tight:Object.fromEntries(m.roots.map(t=>[t.id,m.tight(t)]))}});
JSON.stringify(out);
"""

CASES = {
    # kolejność po wyświetlanym zapasie (właściciel: „zapas 0 dni” pod „zapas 0,9 dnia” wyglądało na błąd)
    "zapas": [{"id": "duzy", "cost": 0.1}, {"id": "d1", "after": ["duzy"], "date": "2026-11-19", "cost": 0},
              {"id": "zero"}, {"id": "z1", "after": ["zero"], "date": "2026-11-21", "cost": 2}],
    # własna data korzenia to termin także w kolejności (PM: A z datą dziś nad B z zależnym 22.11 — teraz spójnie)
    "wlasna_data": [{"id": "A", "date": "2026-11-19", "cost": 0.5}, {"id": "a1", "after": ["A"], "date": "2026-11-30"},
                    {"id": "B", "cost": 0.5}, {"id": "b1", "after": ["B"], "date": "2026-11-22"}],
    # po terminie osobno i najstarszy najpierw, przed „ciasno”
    "po_terminie": [{"id": "L", "date": "2026-11-10"}, {"id": "l1", "after": ["L"], "date": "2026-12-20"},
                    {"id": "U"}, {"id": "u1", "after": ["U"], "date": "2026-11-19", "cost": 2}],
    # wspólny następnik: X→Z, Y→Y1→Z; Z ruszy dopiero po obu — X „odblokowuje 1”, ale od razu nie ruszy nic
    "wspolny": [{"id": "X"}, {"id": "Y"}, {"id": "Y1", "after": ["Y"]},
                {"id": "Z", "after": ["X", "Y1"], "date": "2026-11-22"}],
    # zależny czeka też na brakujące zadanie: „dalej i tak czeka na”
    "dalej_stoi": [{"id": "N"}, {"id": "P", "after": ["N"], "miss": ["Potwierdź DPA"], "date": "2026-11-20"}],
    # cykl: zadania robi się po kolei (suma), więc pod korzeniem 1 + 2 dni pracy do jutra = ciasno
    "cykl": [{"id": "R", "cost": 1}, {"id": "C1", "after": ["R", "C2"]}, {"id": "C2", "after": ["C1"], "date": "2026-11-20"}],
}


@unittest.skipUnless(JS, "brak silnika JS (osascript albo node)")
class Graf(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        r = run_js(HARNESS % {"src": src("bkGraph"), "cases": json.dumps(CASES)})
        if r.returncode != 0:
            raise AssertionError("JS: " + r.stderr.strip())
        cls.out = json.loads(r.stdout)

    def test_kolejnosc_po_wyswietlanym_zapasie(self):
        o = self.out["zapas"]
        self.assertEqual(o["roots"], ["zero", "duzy"])
        self.assertLess(o["urg"]["zero"], o["urg"]["duzy"])
        self.assertEqual(o["grp"], {"zero": "today", "duzy": "today"})

    def test_wlasna_data_to_termin(self):
        o = self.out["wlasna_data"]
        self.assertEqual(o["roots"], ["A", "B"])                      # A ma termin dziś (zapas 0,5), B zapas 2,5
        self.assertEqual(o["grp"], {"A": "today", "B": "soon"})

    def test_po_terminie_osobno(self):
        o = self.out["po_terminie"]
        self.assertEqual(o["roots"], ["L", "U"])
        self.assertEqual(o["grp"], {"L": "late", "U": "tight"})

    def test_ruszy_od_razu(self):
        i = self.out["wspolny"]["info"]
        self.assertEqual((i["X"]["direct"], i["X"]["ready"], i["X"]["other"]), (1, 0, ["Y1"]))
        self.assertEqual((i["Y"]["direct"], i["Y"]["ready"]), (1, 1))

    def test_dalej_i_tak_stoi(self):
        i = self.out["dalej_stoi"]["info"]["N"]
        self.assertEqual((i["ready"], i["other"]), (0, ["Potwierdź DPA"]))

    def test_cykl_suma(self):
        tg = self.out["cykl"]["tight"]["R"]
        self.assertEqual((tg["steps"], tg["days"]), (3, 2))


class DaneZPamieci(unittest.TestCase):
    def test_stale_body(self):
        last = json.dumps({"generatedAt": "2026-11-20T09:15:00", "tasks": [1], "activity": {"films": []}})
        d = json.loads(server.stale_body(last, RuntimeError("x")))
        self.assertEqual(d["stale"], {"since": "2026-11-20T09:15:00", "error": "RuntimeError"})
        self.assertEqual(d["activity"]["error"], "Dane sprzed 09:15: błąd odczytu na serwerze (RuntimeError).")
        self.assertEqual(d["tasks"], [1])

    def test_log_raz_na_zmiane(self):
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            self.assertTrue(server.log_once("t", "test", ValueError("a")))
            self.assertFalse(server.log_once("t", "test", ValueError("a")))
            self.assertTrue(server.log_once("t", "test", ValueError("b")))
        self.assertEqual(buf.getvalue().count("ValueError"), 2)


class RozmowyPoRestarcie(Baza):
    def test_przerwana_i_zakonczona_zostaja(self):
        m = self.manager
        for f, live in (("a.json", False), ("b.json", True)):
            path = os.path.join(self.tmp, f)
            with m._chat_lock:
                m._chat_live.add(path)
                m._chat_meta[path] = {"taskId": f, "project": "p", "file": "ZADANIA.md", "title": "Rozmowa " + f,
                                      "since": "2026-11-19T10:00:00"}
                m._chat_save()
            if not live:
                m._chat_end(path, "odpowiedź", "", "")
        m2 = self.new_manager()                                         # restart panelu w trakcie rozmowy b
        got = {c["title"]: c for c in m2.chat_recent()}
        self.assertTrue(got["Rozmowa a.json"]["ok"])
        self.assertFalse(got["Rozmowa b.json"]["ok"])
        self.assertIn("ponownie", got["Rozmowa b.json"]["error"])
        self.assertEqual(m2.chat_pending(), [])
        m3 = self.new_manager()                                         # drugi restart: bez powtórzeń
        self.assertEqual(len(m3.chat_recent()), 2)


class Panel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(PANEL, encoding="utf-8") as f:
            cls.html = f.read()

    def body(self, name):
        m = re.search(r"function %s\(.*?\n}\n" % name, self.html, re.S)
        self.assertIsNotNone(m, name)
        return m.group(0)

    def test_apply_agents_zeruje_fakty(self):
        self.assertIn("FX=null;", self.body("applyAgents"))

    def test_film_tylko_jawnie(self):
        w = self.body("bkWork")
        self.assertNotIn("/film|nagra/", w)
        self.assertIn("refs", w)

    def test_derive_po_miedzy_plikami(self):
        d = self.body("derive")
        self.assertIn("filesOf", d)
        self.assertIn("'ZADANIA.md'", d)

    def test_uruchom_przy_logowaniu(self):
        self.assertIn("bkClaudeWait(t)", self.body("bkAct"))


if __name__ == "__main__":
    unittest.main()
