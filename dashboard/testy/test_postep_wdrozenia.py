"""Postęp wdrożenia w panelu: etap z stan.json i dziennika wdroz-panel.sh (server.deploy_progress), testy z błędem
z dziennika bez sekretów, pasek na górze każdego widoku (wdModel, wdBar) i testy z błędem w Serwer → Rozwój panelu."""
import datetime
import json
import os
import subprocess
import unittest

from test_blokady import NODE, PANEL
from test_instagram import panel_parts
from test_serwer import Serwer
import test_wdrozenie as tw
from wspolne import server

PW = next((p for p in ("/home/agent/narzedzia/pw/bin/python",) if os.path.isfile(p)), "")
START = "2026-11-26T21:09:40+01:00"
LOG_BLAD = """21:09:41 Gałąź rozwoj w /home/agent/rozwoj/IntegrateSystems (automat)
21:10:01 Testy na abc1234
======================================================================
FAIL: test_pasek (test_postep.Pasek.test_pasek)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/tmp/wdrozenie-x/dashboard/testy/test_postep.py", line 10, in test_pasek
    self.assertEqual(a, b)
AssertionError: 1 != 2 PANEL_TOKEN=tajne123

======================================================================
ERROR: test_dane (test_serwer.Serwer.test_dane)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "x.py", line 3, in test_dane
KeyError: 'deploy'

----------------------------------------------------------------------
Ran 812 tests in 300.123s

FAILED (failures=1, errors=2, skipped=4)
21:16:40 BŁĄD: testy nie przeszły (dziennik wdrożenia)
"""
LOG_AGENCI = """21:09:41 Gałąź rozwoj w /home/agent/rozwoj/IntegrateSystems (automat)
21:10:01 Testy na abc1234
----------------------------------------------------------------------
Ran 812 tests in 300.1s

OK (skipped=4)
21:15:05 Agenci pracują (2): czekam najwyżej 30 min
"""


def stan(state, text, at, sha="abc1234def567890"):
    return {"state": state, "text": text, "startedAt": START, "at": at, "sha": sha, "prev": "", "new": "", "commits": 0}


class Etapy(unittest.TestCase):
    """deploy_progress: etap, od kiedy, agenci, wynik testów; przerwane, czekające na start, nieudane na głowie gałęzi."""
    NOW = datetime.datetime(2026, 11, 26, 21, 20)

    def p(self, last, ahead=1, head="abc1234", log=""):
        return server.deploy_progress(last, ahead, head, log, now=self.NOW)

    def test_etapy_z_tekstu_stanu(self):
        at = "2026-11-26T21:10:01+01:00"
        for text, stage in (("Sprawdzam gałąź rozwoj", "check"), ("Testy", "tests"), ("Scalam z produkcją", "merge"),
                            ("Restart i kontrola", "restart"), ("Coś nowego", "running")):
            p = self.p(stan("running", text, at))
            self.assertEqual((p["stage"], p["since"]), (stage, at), text)
        self.assertEqual(self.p(stan("queued", "W kolejce", at))["stage"], "queued")
        self.assertIsNone(self.p(stan("running", "Testy", at))["tests"])           # w trakcie testów bez wyniku

    def test_czeka_na_agentow(self):
        p = self.p(stan("waiting", "Czekam, aż agenci skończą pracę (2)", "2026-11-26T21:19:45"), log=LOG_AGENCI)
        self.assertEqual((p["stage"], p["agents"], p["agentsMax"]), ("agents", 2, 30))
        self.assertEqual(p["since"], "2026-11-26T21:15:05+01:00")                   # z dziennika, nie z ostatniego zapisu
        self.assertEqual((p["tests"]["ran"], p["tests"]["ok"], p["tests"]["failed"]), (812, True, 0))

    def test_nieudane_testy(self):
        p = self.p(stan("error", "testy nie przeszły (dziennik wdrożenia)", "2026-11-26T21:16:40+01:00"), log=LOG_BLAD)
        self.assertEqual(p["stage"], "error")                                       # głowa gałęzi = nieudany commit
        t = p["tests"]
        self.assertEqual((t["ran"], t["ok"], t["failed"], t["named"]), (812, False, 3, 2))
        self.assertEqual([(i["name"], i["test"]) for i in t["items"]],
                         [("test_pasek", "test_postep.Pasek.test_pasek"), ("test_dane", "test_serwer.Serwer.test_dane")])
        self.assertEqual(t["items"][0]["lines"], ["AssertionError: 1 != 2 PANEL_TOKEN=***"])
        self.assertEqual(t["items"][1]["lines"], ["KeyError: 'deploy'"])
        self.assertNotIn("tajne123", json.dumps(p))

    def test_stary_format_i_ucieta_naglowka(self):
        log = "  File \"a.py\", line 1\nValueError: x\n\n" + "-" * 70 + "\nRan 5 tests in 1s\n\nFAILED (errors=2)\n"
        t = server.deploy_tests(log.splitlines())
        self.assertEqual((t["ran"], t["failed"], t["named"], t["items"]), (5, 2, 0, []))
        t = server.deploy_tests(["ERROR: setUpClass (test_a.Klasa)", "-" * 70, "Traceback (most recent call last):",
                                 "  File \"a.py\"", "OSError: brak"])
        self.assertEqual((t["items"][0]["test"], t["items"][0]["lines"], t["failed"]), ("test_a.Klasa.setUpClass", ["OSError: brak"], 1))
        self.assertIsNone(server.deploy_tests(["21:00:00 Testy na abc"]))

    def test_czeka_na_start_i_przerwane(self):
        ok = stan("ok", "Wdrożono 2 commity", "2026-11-26T21:00:00+01:00")
        self.assertEqual(self.p(ok, ahead=0)["stage"], "ok")
        p = self.p(ok, ahead=2)
        self.assertEqual((p["stage"], p["previous"]), ("pending", "ok"))
        old = stan("error", "konflikt przy scalaniu", "2026-11-26T21:00:00+01:00", sha="0000000aaaa")
        self.assertEqual(self.p(old, ahead=1)["previous"], "error")                 # nowy commit: automat spróbuje
        self.assertEqual(self.p(None, ahead=3)["stage"], "pending")
        self.assertEqual(self.p(None, ahead=0)["stage"], "")
        dead = stan("running", "Testy", "2026-11-26T20:30:00")
        self.assertEqual(self.p(dead, ahead=0)["stage"], "stalled")
        self.assertEqual(self.p(dead, ahead=1)["previous"], "stalled")
        wait = stan("waiting", "Czekam, aż agenci skończą pracę (1)", "2026-11-26T21:10:00")   # nie odświeżany od 10 min
        p = self.p(wait, ahead=0, log=LOG_AGENCI)
        self.assertEqual((p["stage"], p["since"]), ("stalled", "2026-11-26T21:10:00"))

    def test_sekrety(self):
        s = server._redact("Authorization: Bearer abcdefghijklmnop x api_key=\"q1w2e3\" ghp_abcdefghijklmn "
                           "0123456789abcdef0123456789abcdef01234567 KeyError: 'token'")
        for bad in ("abcdefghijklmnop", "q1w2e3", "ghp_", "0123456789abcdef0123"):
            self.assertNotIn(bad, s)
        self.assertIn("KeyError: 'token'", s)
        self.assertEqual(server._redact("File \"/home/agent/rozwoj/wt-postep/dashboard/testy/test_x.py\""),
                         "File \"/home/agent/rozwoj/wt-postep/dashboard/testy/test_x.py\"")


class StanWdrozenia(unittest.TestCase):
    """deploy_state niesie progress (pole w /api/data, bez nowego odpytywania); dziennik bez sekretów;
    przycisk „Wdróż” nie startuje drugiego wdrożenia, gdy pierwsze czeka na agentów. Repozytoria jak w test_wdrozenie."""
    setUp, tearDown, commit, state = tw.Wdrozenie.setUp, tw.Wdrozenie.tearDown, tw.Wdrozenie.commit, tw.Wdrozenie.state

    def write(self, st, log):
        os.makedirs(server.DEPLOY_DIR, exist_ok=True)
        with open(os.path.join(server.DEPLOY_DIR, "stan.json"), "w") as f:
            json.dump(st, f)
        with open(os.path.join(server.DEPLOY_DIR, "ostatnie.log"), "w") as f:
            f.write(log)

    def test_progress_w_stanie(self):
        self.assertEqual(self.state()["progress"]["stage"], "")
        self.commit(self.dev, "b.py", "2", "Nowy widok")
        st = self.state()
        self.assertEqual((st["progress"]["stage"], st["progress"]["head"]), ("pending", st["commits"][0]["sha"]))
        head = subprocess.run(["git", "-C", self.dev, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        self.write(stan("error", "testy nie przeszły (dziennik wdrożenia)", "2026-11-26T21:16:40+01:00", sha=head), LOG_BLAD)
        st = self.state()
        self.assertEqual(st["progress"]["stage"], "error")
        self.assertEqual(st["progress"]["tests"]["items"][0]["name"], "test_pasek")
        self.assertNotIn("tajne123", st["log"])
        self.assertIn("PANEL_TOKEN=***", st["log"])
        now = datetime.datetime.now().isoformat(timespec="seconds")
        self.write(stan("waiting", "Czekam, aż agenci skończą pracę (1)", now, sha=head), LOG_AGENCI)
        self.assertEqual(self.state()["progress"]["stage"], "agents")
        self.assertEqual(server.start_deploy({})[0], 409)                          # czeka na agentów: już trwa


JS_STUB = r"""
const pad=n=>String(n).padStart(2,'0'),tOf=iso=>{const d=iso?new Date(iso):null;return d&&!isNaN(d)?d:null};
const hhmm=d=>pad(d.getHours())+':'+pad(d.getMinutes());
const pl=(n,a,b,c)=>n===1?a:(n%10>=2&&n%10<=4&&(n%100<12||n%100>14))?b:c;
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[c]);
"""


@unittest.skipUnless(NODE, "brak node")
class Pasek(unittest.TestCase):
    """wdModel: teksty paska dla każdego etapu; „gotowe” znika po 2 minutach; nieudane z liczbą i nazwą testu."""

    @classmethod
    def setUpClass(cls):
        with open(PANEL, encoding="utf-8") as f:
            cls.html = f.read()

    def models(self, cases):
        code = JS_STUB + panel_parts(self.html, ["WD_OK_MS", "wdFailT", "wdModel", "wdFails"])
        js = code + "\nconst C=%s,N=Date.parse('2026-11-26T21:20:00');\n" % json.dumps(cases, ensure_ascii=False) + \
            "process.stdout.write(JSON.stringify(C.map(c=>{const m=wdModel(c,N);return m?{t:m.t,cls:m.cls,x:!!m.x,on:!!m.on}:null}).concat([wdFails(C[C.length-1])])))"
        r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_teksty(self):
        T = lambda h, m: "2026-11-26T%02d:%02d:00" % (h, m)  # noqa: E731
        fail = {"ran": 812, "ok": False, "failed": 3, "named": 2, "items": [
            {"name": "test_pasek", "test": "test_postep.Pasek.test_pasek", "lines": ["AssertionError: 1 != 2"]},
            {"name": "test_dane", "test": "test_serwer.Serwer.test_dane", "lines": ["KeyError: 'deploy'"]}]}
        cases = [
            {"ahead": 2, "auto": True, "progress": {"stage": "pending", "since": ""}},
            {"ahead": 1, "auto": False, "progress": {"stage": "pending", "previous": "error", "since": ""}},
            {"ahead": 1, "progress": {"stage": "queued", "since": T(21, 9)}},
            {"ahead": 1, "progress": {"stage": "tests", "since": T(21, 10)}},
            {"ahead": 1, "progress": {"stage": "agents", "since": T(21, 15), "agents": 2, "agentsMax": 30}},
            {"ahead": 1, "progress": {"stage": "restart", "since": T(21, 17)}},
            {"ahead": 0, "progress": {"stage": "ok", "since": T(21, 19)}},
            {"ahead": 0, "progress": {"stage": "ok", "since": T(21, 17)}},                       # ponad 2 min temu
            {"ahead": 1, "last": {"text": "konflikt przy scalaniu"}, "progress": {"stage": "error", "since": T(21, 16)}},
            {"ahead": 0, "progress": {"stage": "error", "since": T(21, 16)}},                     # nic do wdrożenia
            {"ahead": 0, "progress": {"stage": "stalled", "since": T(20, 30)}},
            {"ahead": 0, "progress": {"stage": "", "since": ""}},
            {"ahead": 1, "progress": {"stage": "error", "since": T(21, 16), "tests": fail}},
        ]
        r = self.models(cases)
        t = [m and m["t"] for m in r[:-1]]
        self.assertEqual(t[0], "2 zmiany czekają na start")
        self.assertEqual(t[1], "1 zmiana czeka na wdrożenie · poprzednie nieudane")
        self.assertEqual(t[2], "w kolejce")
        self.assertEqual(t[3], "testy w toku od 21:10")
        self.assertEqual(t[4], "czeka na agentów (2 w toku), najdłużej do 21:45")
        self.assertEqual(t[5], "scalanie i restart")
        self.assertEqual((t[6], r[6]["x"], r[6]["cls"]), ("gotowe 21:19", True, "ok"))
        self.assertIsNone(t[7])
        self.assertEqual((t[8], r[8]["cls"]), ("nieudane: konflikt przy scalaniu", "bad"))
        self.assertIsNone(t[9])
        self.assertEqual(t[10], "brak postępu od 20:30 (wdrożenie przerwane?)")
        self.assertIsNone(t[11])
        self.assertEqual(t[12], "nieudane: 3 testy (test_pasek)")
        self.assertTrue(all(r[i]["on"] for i in (2, 3, 4, 5)))
        box = r[-1]
        for s in ("3 testy nie przeszły", "z 812", "test_pasek", "AssertionError: 1 != 2", "KeyError:", "Nazw pozostałych (1)"):
            self.assertIn(s, box)

    def test_miejsca_w_panelu(self):
        h = self.html
        self.assertIn("if(LIVE&&D){const w=wdBar();if(w)b.push(w)}", h)          # renderTop: każdy widok
        self.assertIn("+wdFails(d)}", h)                                           # Serwer: nieudane, bez rozwijania
        self.assertIn('id="srv-rozwoj" tabindex="-1"', h)                          # cel „Szczegóły” (#koszty?k=rozwoj)
        self.assertIn('href="#koszty?k=rozwoj"', h)
        self.assertIn("D.deploy=raw.deploy", h)                                    # odświeżanie samych agentów też
        self.assertNotIn("setInterval(load", h)


PAGE = r"""
import json, sys
from playwright.sync_api import sync_playwright
U, SHOT = sys.argv[1], sys.argv[2]
out, errs = {}, []
with sync_playwright() as p:
    b = p.chromium.launch()
    for w in (1440, 390):
        pg = b.new_page(viewport={"width": w, "height": 900})
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(U + "#asystent"); pg.wait_for_selector(".wd-bar")
        r = out[str(w)] = {"bar": pg.locator(".wd-bar").inner_text()}
        if SHOT:
            pg.screenshot(path=SHOT + "-asystent-%d.png" % w)
        pg.locator(".wd-bar a[data-wdgo]").click(); pg.wait_for_timeout(800)
        r["hash"] = pg.evaluate("location.hash")
        r["fails"] = pg.locator("#srv-rozwoj .wd-fails").inner_text()
        r["open"] = pg.evaluate("document.getElementById('srv-rozwoj').open")
        r["hscroll"] = pg.evaluate("document.documentElement.scrollWidth>innerWidth+1")
        if SHOT:
            pg.locator("#srv-rozwoj").screenshot(path=SHOT + "-serwer-%d.png" % w)
        pg.locator(".wd-bar .wd-x").click(); pg.wait_for_timeout(300)
        r["closed"] = pg.locator(".wd-bar").count() == 0
        pg.close()
    b.close()
print(json.dumps({"out": out, "errs": errs}, ensure_ascii=False))
"""


@unittest.skipUnless(PW and not os.environ.get("PANEL_TESTY_BEZ_RENDERU"), "brak Playwright albo PANEL_TESTY_BEZ_RENDERU")
class Przegladarka(Serwer):
    """Cała strona w Chromium: pasek nad Asystentem, „Szczegóły” prowadzi do Serwer → Rozwój panelu z testami
    z błędem na wierzchu, zamknięcie paska, bez poziomego przewijania na telefonie i bez błędów JS."""

    def setUp(self):
        super().setUp()
        self.dev = os.path.join(self.tmp, "dev-repo")
        git = tw.git
        git(self.tmp, "init", "-q", "-b", "rozwoj", self.dev)
        with open(os.path.join(self.dev, "a.py"), "w") as f:
            f.write("1")
        git(self.dev, "add", "a.py")
        git(self.dev, "commit", "-q", "-m", "Nowy widok")
        head = subprocess.run(["git", "-C", self.dev, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        self.old = {k: getattr(server, k) for k in ("DEV_REPO", "DEPLOY_DIR", "TEST_ENV")}
        server.DEV_REPO, server.DEPLOY_DIR = self.dev, os.path.join(self.tmp, "wdrozenie")
        server.TEST_ENV = os.path.join(self.tmp, "brak.env")
        os.makedirs(server.DEPLOY_DIR)
        with open(os.path.join(server.DEPLOY_DIR, "stan.json"), "w") as f:
            json.dump(stan("error", "testy nie przeszły (dziennik wdrożenia)", "2026-11-26T21:16:40+01:00", sha=head), f)
        with open(os.path.join(server.DEPLOY_DIR, "ostatnie.log"), "w") as f:
            f.write(LOG_BLAD)
        self._branch = server._deploy_branch
        server._deploy_branch = lambda: {"ahead": 1, "behind": 0, "stat": "", "commits": [{"sha": head[:7], "at": "", "subject": "Nowy widok"}]}

    def tearDown(self):
        server._deploy_branch = self._branch
        for k, v in self.old.items():
            setattr(server, k, v)
        super().tearDown()

    def test_pasek_i_serwer(self):
        env = dict(os.environ)
        if not env.get("PLAYWRIGHT_BROWSERS_PATH") and os.path.isdir("/opt/ms-playwright"):
            env["PLAYWRIGHT_BROWSERS_PATH"] = "/opt/ms-playwright"
        r = subprocess.run([PW, "-c", PAGE, "http://127.0.0.1:%d/" % self.port, os.environ.get("PANEL_ZRZUTY_WD", "")],
                           capture_output=True, text=True, timeout=240, env=env)
        self.assertEqual(r.returncode, 0, r.stderr[-3000:])
        res = json.loads(r.stdout.strip().split("\n")[-1])
        self.assertEqual(res["errs"], [])
        for w, o in res["out"].items():
            self.assertIn("Wdrożenie: nieudane: 3 testy (test_pasek)", o["bar"], w)
            self.assertIn("Szczegóły", o["bar"])
            self.assertEqual(o["hash"], "#koszty", w)
            self.assertTrue(o["open"], w)
            for s in ("3 testy nie przeszły", "test_pasek", "AssertionError: 1 != 2 PANEL_TOKEN=***", "test_dane"):
                self.assertIn(s, o["fails"], w)
            self.assertNotIn("tajne123", o["fails"])
            self.assertFalse(o["hscroll"], w)
            self.assertTrue(o["closed"], w)


if __name__ == "__main__":
    unittest.main()
