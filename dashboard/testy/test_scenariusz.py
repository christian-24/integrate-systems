"""Scenariusz nagrania (scenariusz.md w folderze posta): format i odczyt, pole karty `nagrywa: ty`, trasy panelu
(przygotowanie przez agenta na atrapie, poprawka, edycja tekstu, przejścia stanów z zadaniem nagrania, sesja),
zadanie Automatu dla filmów na 7 dni i wiersze „Do nagrania” ze stanem w Chrome (pomijane bez Chrome albo
z PANEL_TESTY_BEZ_RENDERU)."""
import datetime
import json
import os
import re
import subprocess
import tempfile
import unittest

from test_instagram import CHROME, PANEL, panel_parts, read
from test_serwer import REMOTE, Serwer

import projekt  # noqa: E402  (ścieżki ustawia wspolne.py)
import scenariusz  # noqa: E402
import server  # noqa: E402

TODAY = datetime.date.today()
DAY = (TODAY + datetime.timedelta(days=3)).isoformat()
REC = (TODAY + datetime.timedelta(days=2)).isoformat()
FILM = "Opublikuj film „Miernik w akcji”"
TEXT = "Opublikuj post „Oferta”"


class Format(unittest.TestCase):
    def test_wzor_bez_bledow(self):
        p = scenariusz.parse(scenariusz.skeleton("Miernik", DAY, REC))
        self.assertEqual((p["title"], p["state"], p["publication"], p["recording"]), ("Miernik", "propozycja", DAY, REC))
        self.assertEqual([s["seconds"] for s in p["shots"]], [5, 10])
        self.assertEqual((p["seconds"], p["errors"]), (15, []))
        self.assertEqual(list(p["sections"])[:6], list(scenariusz.SECTIONS))

    def test_bledy_i_ujecia(self):
        p = scenariusz.parse("# Scenariusz nagrania: X\n\n- stan: gotowe\n\n## Po co\nCel\n\n## Co nagrać\n"
                             "- [x] Ujęcie A | 7 sek\n- [ ] Ujęcie B bez czasu\n- [ ] C | znak | 3 s\n")
        self.assertEqual(p["shots"], [{"text": "Ujęcie A", "seconds": 7, "done": True},
                                      {"text": "Ujęcie B bez czasu", "seconds": 0, "done": False},
                                      {"text": "C | znak", "seconds": 3, "done": False}])
        joined = "; ".join(p["errors"])
        for part in ("stan: gotowe", "brak sekcji: Jak, Co powiedzieć, Na koniec, Gotowe gdy", "ujęcie bez czasu"):
            self.assertIn(part, joined)
        self.assertIn("bez ujęć", "; ".join(scenariusz.parse("# Scenariusz nagrania: X\n## Co nagrać\nnic\n")["errors"]))

    def test_stan_i_wersja(self):
        text = scenariusz.skeleton("X", DAY, REC)
        out = scenariusz.set_state(text, "do realizacji")
        self.assertEqual(scenariusz.parse(out)["state"], "do realizacji")
        self.assertEqual(out.count("- stan:"), 1)
        bare = scenariusz.set_state("# Scenariusz nagrania: X\n\n## Po co\nx\n", "nagrane")
        self.assertEqual(scenariusz.parse(bare)["state"], "nagrane")
        with self.assertRaises(ValueError):
            scenariusz.set_state(text, "gotowe")
        self.assertNotEqual(scenariusz.version(text), scenariusz.version(out))

    def test_pomocnicze(self):
        self.assertEqual(scenariusz.pub_title({"title": FILM}), "Film „Miernik w akcji”")
        self.assertEqual(scenariusz.rec_day(DAY, TODAY), REC)
        self.assertEqual(scenariusz.rec_day(TODAY.isoformat(), TODAY), TODAY.isoformat())   # najwcześniej dziś
        self.assertTrue(scenariusz.is_film({"title": "Opublikuj post", "channel": "Reels"}))
        self.assertTrue(scenariusz.is_film({"title": FILM}))
        self.assertFalse(scenariusz.is_film({"title": TEXT, "channel": "LinkedIn"}))
        with tempfile.TemporaryDirectory() as d:
            path = scenariusz.new_post_dir(d, DAY, "Film „Łódź i żółw”")
            self.assertEqual(os.path.basename(path), DAY + "-film-lodz-i-zolw")
            self.assertIsNone(scenariusz.post_dir(d, DAY))              # folder zakłada agent
            os.makedirs(path)
            self.assertEqual(scenariusz.post_dir(d, DAY), path)

    def test_pole_karty(self):
        self.assertTrue(projekt.card_fields({"nagrywa": "ty"})["filmOwner"])
        self.assertFalse(projekt.card_fields({"nagrywa": "panel"})["filmOwner"])
        self.assertFalse(projekt.card_fields({})["filmOwner"])
        self.assertEqual(projekt.card_fields({"nagrywa": "ktoś"})["errors"],
                         ["nagrywa: ktoś (ty, ai, panel albo podział, np. „panel 50, ai 40, ty 10”)"])
        f = projekt.card_fields({"nagrywa": "panel 50, ai 40, ty 10"})
        self.assertEqual((f["filmOwner"], f["filmMix"]), (True, {"panel": 50, "ai": 40, "ty": 10}))
        self.assertTrue(projekt.card_fields({"nagrywa": "ai"})["filmOwner"])
        self.assertEqual(projekt.card_fields({"nagrywa": "ty"})["filmMix"], {"ty": 100})

    def test_podzial_sposobow(self):
        mix, used, seq = {"panel": 50, "ai": 40, "ty": 10}, {}, []
        for _ in range(10):
            w = scenariusz.pick_way(mix, used)
            seq.append(w)
            used[w] = used.get(w, 0) + 1
        self.assertEqual((seq.count("panel"), seq.count("ai"), seq.count("ty")), (5, 4, 1))
        self.assertEqual(scenariusz.pick_way({}, {}), "ty")
        self.assertEqual(scenariusz.parse("# Scenariusz nagrania: x\n\n- stan: propozycja\n- sposób: AI\n")["way"], "ai")
        self.assertEqual(scenariusz.parse("# Scenariusz nagrania: x\n\n- sposób: kto\n")["way"], "")


class Trasy(Serwer):
    owner = True

    def setUp(self):
        super().setUp()
        if self.owner:
            path = os.path.join(self.folder, "KARTA.md")
            with open(path, encoding="utf-8") as f:
                text = f.read()
            first, rest = text.split("\n", 1)
            with open(path, "w", encoding="utf-8") as f:
                f.write(first + "\n\n- nagrywa: ty\n" + rest)
        os.makedirs(os.path.join(self.folder, "kampanie"), exist_ok=True)
        with open(os.path.join(self.folder, "kampanie", "filmy.md"), "w", encoding="utf-8") as f:
            f.write("# Kampania: Filmy\n\n- stan: w toku\n- kanały: reels\n\n## Grupa docelowa\nx\n\n## Przekaz\nx\n\n"
                    "## Harmonogram\n- [ ] %s | kto: ty | kanał: Reels | kiedy: %s\n"
                    "- [ ] %s | kto: ty | kanał: LinkedIn | kiedy: %s\n\n## Wyniki i wnioski\n" % (FILM, DAY, TEXT, DAY))
        self.pid = self.data()["projects"][0]["id"]
        self.set_mode("scenariusz")

    def pub(self, title=FILM):
        return next(t for t in self.data()["tasks"] if t["title"] == title)

    def info(self):
        return json.loads(self.request("GET", "/api/scenariusz?project=%s&date=%s" % (self.pid, DAY))[2])

    def tasks(self, prefix):
        return [t for t in self.data()["tasks"] if t["title"].startswith(prefix + DAY)]

    def prepare(self, **extra):
        code, ans = self.post("/api/scenariusz/przygotuj", dict({"project": self.pid, "date": DAY}, **extra))
        self.assertEqual(code, 200, ans)
        self.assertTrue(ans["started"], ans)
        self.wait_for(lambda: all(t["state"] == "done" for t in self.tasks(scenariusz.PREP_TASK)), timeout=15)
        self.wait_for(lambda: not server.get_agents().has_live(self.pid), timeout=15)   # koniec uruchomienia
        return ans

    def test_dane_i_przygotowanie(self):
        self.assertEqual(self.pub()["script"], {"state": "", "shots": 0, "seconds": 0, "errors": 0, "owner": True})
        self.assertNotIn("script", self.pub(TEXT))                        # post bez filmu: bez scenariusza
        self.assertFalse(self.info()["exists"])
        ans = self.prepare()
        self.assertEqual(ans["title"], "Przygotuj scenariusz nagrania na %s: Film „Miernik w akcji”" % DAY)
        info = self.info()
        self.assertTrue(info["exists"], info)
        self.assertEqual((info["script"]["state"], info["script"]["errors"], info["recDay"]), ("propozycja", [], REC))
        self.assertEqual(info["post"], DAY + "-film-miernik-w-akcji")
        self.assertFalse(info["postReady"])
        self.assertEqual(self.pub()["script"]["state"], "propozycja")
        self.assertEqual(self.pub()["script"]["shots"], 4)
        self.assertNotIn("script", self.pub(TEXT))                        # ten sam dzień i folder: scenariusz należy do filmu
        call = [c for c in self.calls() if "Przygotuj scenariusz nagrania" in c.get("prompt", "")][-1]
        for part in ("posty/%s-film-miernik-w-akcji/scenariusz.md" % DAY, "## Co nagrać", "kampanie/filmy.md",
                     "„- nagranie: %s”" % REC):
            self.assertIn(part, call["prompt"])
        # drugi raz bez „od nowa”: odmowa; od nowa: to samo zadanie jeszcze raz, z poprawką
        code, ans = self.post("/api/scenariusz/przygotuj", {"project": self.pid, "date": DAY})
        self.assertEqual(code, 409, ans)
        self.prepare(od_nowa=True)
        self.assertEqual(len(self.tasks(scenariusz.PREP_TASK)), 1)
        self.assertIn("od nowa", self.tasks(scenariusz.PREP_TASK)[0]["detail"]["fix"])

    def test_poprawka_tekst_i_stany(self):
        self.prepare()
        code, ans = self.post("/api/scenariusz/popraw", {"project": self.pid, "date": DAY, "uwaga": "Dodaj ujęcie miernika z bliska"})
        self.assertEqual(code, 200, ans)
        self.wait_for(lambda: all(t["state"] == "done" for t in self.tasks(scenariusz.FIX_TASK)), timeout=15)
        info = self.info()
        self.assertEqual(info["script"]["shots"][-1]["text"], "Dodaj ujęcie miernika z bliska")
        self.assertEqual(self.post("/api/scenariusz/popraw", {"project": self.pid, "date": DAY, "uwaga": "x"})[0], 400)
        # edycja tekstu: stara wersja -> 409; stan w tekście nie zmienia stanu
        body = {"project": self.pid, "date": DAY, "text": info["text"].replace("| 4 s", "| 3 s"), "old": "zla"}
        self.assertEqual(self.post("/api/scenariusz/tekst", body)[0], 409)
        body.update(old=info["version"], text=body["text"].replace("- stan: propozycja", "- stan: nagrane"))
        code, ans = self.post("/api/scenariusz/tekst", body)
        self.assertEqual((code, ans["errors"]), (200, []), ans)
        info = self.info()
        self.assertEqual((info["script"]["state"], info["script"]["shots"][0]["seconds"]), ("propozycja", 3))
        # przejścia stanów
        st = lambda stan, old=None: self.post("/api/scenariusz/stan", {"project": self.pid, "date": DAY, "stan": stan,
                                                                       "old": old or self.info()["version"]})
        self.assertEqual(st("nagrane")[0], 409)                         # najpierw do realizacji
        self.assertEqual(st("do realizacji", "zla")[0], 409)            # cudza zmiana w tym czasie
        self.assertEqual(st("gotowe")[0], 400)
        code, ans = st("do realizacji")
        self.assertEqual((code, ans["state"]), (200, "do realizacji"), ans)
        rec = self.tasks(scenariusz.REC_TASK)
        self.assertEqual(len(rec), 1)
        self.assertEqual((rec[0]["executor"], rec[0]["date"], rec[0]["state"], rec[0]["minutes"]),
                         ("ty", REC, "todo", scenariusz.REC_MINUTES))
        self.assertEqual([r["path"] for r in rec[0]["detail"]["refs"]],
                         ["posty/%s-film-miernik-w-akcji/scenariusz.md" % DAY])
        self.assertEqual(self.pub()["script"]["state"], "do realizacji")
        self.assertEqual(st("do realizacji")[0], 409)
        self.assertEqual(st("nagrane")[0], 200)
        self.assertEqual(self.tasks(scenariusz.REC_TASK)[0]["state"], "done")
        self.assertEqual(self.pub()["script"]["state"], "nagrane")
        self.assertEqual(st("propozycja")[0], 200)                       # cofnięcie
        self.assertEqual(st("do realizacji")[0], 200)                    # to samo zadanie nagrania, znowu otwarte
        rec = self.tasks(scenariusz.REC_TASK)
        self.assertEqual((len(rec), rec[0]["state"]), (1, "todo"))

    def test_bez_publikacji_i_bez_pliku(self):
        other = (TODAY + datetime.timedelta(days=9)).isoformat()
        self.assertEqual(self.post("/api/scenariusz/przygotuj", {"project": self.pid, "date": other})[0], 404)
        self.assertEqual(self.post("/api/scenariusz/przygotuj", {"project": "nie-ma", "date": DAY})[0], 404)
        self.assertEqual(self.post("/api/scenariusz/przygotuj", {"project": self.pid, "date": "jutro"})[0], 400)
        self.assertEqual(self.post("/api/scenariusz/popraw", {"project": self.pid, "date": DAY, "uwaga": "krócej"})[0], 404)
        self.assertEqual(self.post("/api/scenariusz/stan", {"project": self.pid, "date": DAY, "stan": "nagrane"})[0], 404)

    def test_sesja(self):
        server.TOKEN = "haslo-do-testow"
        body = {"project": self.pid, "date": DAY}
        status, _, text = self.request("POST", "/api/scenariusz/przygotuj", body=body, headers=REMOTE)
        self.assertEqual((status, json.loads(text)["error"]), (401, "Wymagane hasło."))
        status, _, _ = self.request("GET", "/api/scenariusz?project=%s&date=%s" % (self.pid, DAY), headers=REMOTE)
        self.assertEqual(status, 401)
        self.assertEqual(self.tasks(scenariusz.PREP_TASK), [])
        cookie = self.login("haslo-do-testow")[1]["Set-Cookie"].split(";")[0]
        status, _, text = self.request("GET", "/api/scenariusz?project=%s&date=%s" % (self.pid, DAY),
                                       headers=dict(REMOTE, Cookie=cookie))
        self.assertEqual((status, json.loads(text)["exists"]), (200, False))

    def test_automat_raz_dla_filmu_wlasciciela(self):
        data, index = server.load_projects()
        self.assertTrue(self.manager._plan_scripts(data, index, TODAY))
        prep = self.tasks(scenariusz.PREP_TASK)
        self.assertEqual(len(prep), 1)
        self.assertEqual((prep[0]["executor"], prep[0]["date"]), ("claude", TODAY.isoformat()))
        self.assertIn("posty/%s-film-miernik-w-akcji/scenariusz.md" % DAY, prep[0]["detail"]["doneWhen"])
        self.assertFalse(os.path.isdir(os.path.join(self.folder, "posty")))     # pusty folder posta nie powstaje
        data, index = server.load_projects()
        self.assertFalse(self.manager._plan_scripts(data, index, TODAY))            # drugi raz nic
        far = TODAY - datetime.timedelta(days=8)                                   # publikacja poza 7 dniami
        self.assertFalse(self.manager._plan_scripts(data, index, far))
        self.assertEqual(self.manager._state["filmWays"]["%s|%s" % (self.pid, DAY)], "ty")
        self.assertIn("„- sposób: ty”", prep[0]["detail"]["doneWhen"])
        self.assertEqual(self.info()["way"], "ty")

    def test_automat_film_ai_i_panel(self):
        """Podział karty: film „panel” nie dostaje scenariusza, film „ai” dostaje scenariusz z poleceniami dla AI."""
        data, index = server.load_projects()
        for p in data["projects"]:
            p["filmOwner"], p["filmMix"] = True, {"panel": 100}
        self.assertFalse(self.manager._plan_scripts(data, index, TODAY))
        self.assertEqual(self.tasks(scenariusz.PREP_TASK), [])
        self.assertEqual(self.manager._state["filmWays"]["%s|%s" % (self.pid, DAY)], "panel")
        self.manager._state["filmWays"] = {}
        for p in data["projects"]:
            p["filmMix"] = {"ai": 100}
        self.assertTrue(self.manager._plan_scripts(data, index, TODAY))
        prep = self.tasks(scenariusz.PREP_TASK)
        self.assertIn("narzędziu AI", prep[0]["detail"]["goal"])
        self.assertIn("„- sposób: ai”", prep[0]["detail"]["doneWhen"])


class TrasyBezNagraniaWlasciciela(Trasy):
    owner = False

    def test_dane_i_przygotowanie(self):
        self.assertNotIn("script", self.pub())                            # film robi panel: bez scenariusza nagrania
        data, index = server.load_projects()
        self.assertFalse(self.manager._plan_scripts(data, index, TODAY))
        self.prepare()                                                    # na prośbę: plik i wiersz w danych
        self.assertEqual(self.pub()["script"]["owner"], False)
        code, ans = self.post("/api/scenariusz/stan", {"project": self.pid, "date": DAY, "stan": "do realizacji",
                                                       "old": self.info()["version"]})
        self.assertEqual(code, 200, ans)
        self.assertTrue(ans["task"].startswith(scenariusz.AGENT_TASK + DAY), ans)
        self.assertEqual(self.tasks(scenariusz.REC_TASK), [])

    test_poprawka_tekst_i_stany = test_automat_raz_dla_filmu_wlasciciela = None


@unittest.skipUnless(CHROME and not os.environ.get("PANEL_TESTY_BEZ_RENDERU"),
                     "brak Chrome albo PANEL_TESTY_BEZ_RENDERU: test wierszy „Do nagrania” w przeglądarce pominięty")
class DoNagraniaWChrome(unittest.TestCase):
    def test_wiersze_ze_stanem_i_akcja(self):
        code = panel_parts(read(PANEL).decode("utf-8"),
                           ["esc", "pl", "SC", "SCST", "SCPRE", "scOwn", "scLz", "scTasks", "scBusy", "scPrimary", "recPanel"])
        page = """<!doctype html><meta charset="utf-8"><body><pre id="w"></pre><script>
const T0='2026-11-20',PD={},PF={};
const addK=(k,n)=>{const d=new Date(k+'T12:00:00');d.setDate(d.getDate()+n);return d.toISOString().slice(0,10)};
const isDay=v=>/^\\d{4}-\\d\\d-\\d\\d/.test(v||''),cap=s=>s.charAt(0).toUpperCase()+s.slice(1),ddl=k=>k,mkTitle=t=>t.title.replace(/^Opublikuj\\s+/,'');
const projName=id=>id,mkIsFilm=t=>/film/i.test(t.title),filmState=()=>['grey','x'];
const S=(st)=>({state:st,shots:0,seconds:0,errors:0,owner:true});
const D={todayKey:T0,tasks:[
 {id:'a',project:'ss',kind:'publikacja',state:'todo',date:'2026-11-22',title:'Opublikuj film A',script:S('')},
 {id:'b',project:'ss',kind:'publikacja',state:'todo',date:'2026-11-23',title:'Opublikuj film B',script:S('propozycja')},
 {id:'c',project:'ss',kind:'publikacja',state:'todo',date:'2026-11-24',title:'Opublikuj film C',script:S('nagrane')},
 {id:'d',project:'op',kind:'publikacja',state:'todo',date:'2026-11-22',title:'Opublikuj film D'},
 {id:'p',project:'ss',state:'doing',title:'Przygotuj scenariusz nagrania na 2026-11-22: A'}]};
%s
const h=recPanel(''),r={};
r.scopen=(h.match(/data-scopen="[^"]+"/g)||[]).map(x=>x.split('|')[2].replace('"',''));
r.medit=(h.match(/data-medit="[^"]+"/g)||[]).length;
r.stany=(h.match(/<span class="lz [a-z]+">[^<]+/g)||[]).map(x=>x.replace(/.*>/,''));
r.hint=/nagrywasz Ty/.test(h)&&/Pozostałe nagrywa panel/.test(h);
const ok={ok:true,exists:true,script:{state:'propozycja'}};
r.akcje=[scPrimary({ok:true,exists:false},''),scPrimary(ok,''),scPrimary({ok:true,exists:true,script:{state:'do realizacji'}},''),
 scPrimary({ok:true,exists:true,script:{state:'nagrane'}},''),scPrimary(ok,'prep'),scPrimary(ok,'fix')].map(x=>x?x.n:null);
r.busy=[scBusy('ss','2026-11-22'),scBusy('ss','2026-11-23')];
document.getElementById('w').textContent=JSON.stringify(r);
</script>""" % code
        with tempfile.TemporaryDirectory(prefix="panel-sc-") as tmp:
            path = os.path.join(tmp, "nagrania.html")
            with open(path, "w", encoding="utf-8") as f:
                f.write(page)
            out = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
                                  "--user-data-dir=" + os.path.join(tmp, "profil"), "--virtual-time-budget=3000",
                                  "--dump-dom", "file://" + path], capture_output=True, text=True, timeout=60)
        import html as H
        m = re.search(r'<pre id="w">(.*?)</pre>', out.stdout, re.S)
        self.assertTrue(m and m.group(1), out.stderr[-500:])
        r = json.loads(H.unescape(m.group(1)))
        self.assertEqual(r["scopen"], ["a", "b"])                      # nagrane znika; film panelu otwiera post
        self.assertEqual(r["medit"], 1)
        self.assertEqual(r["stany"], ["bez scenariusza", "propozycja"])
        self.assertTrue(r["hint"])
        self.assertEqual(r["akcje"], ["Przygotuj scenariusz", "Wyślij do realizacji", "Nagrane", None,
                                      "Agent pisze scenariusz…", "Wyślij do realizacji"])
        self.assertEqual(r["busy"], ["prep", ""])


if __name__ == "__main__":
    unittest.main()
