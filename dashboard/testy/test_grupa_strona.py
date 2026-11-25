"""Zakładka Strona po zmianach 2026-11-25 (grupa „strona”).

Serwer: podgląd buduje się sam, gdy pliki strony w repozytorium są nowsze niż ostatni podgląd (scalenie ręczne,
commit, pobranie z GitHuba), także po ręcznym scaleniu gałęzi zadania strony („Nie scalono zmian” → „zrobione”);
Codex dostaje tę samą przeglądarkę MCP co Claude (-c mcp_servers…, bez pytania o zgodę), zrzuty przeglądarki trafiają
do .zrzuty/ (widać je w panelu), a czynności w przeglądarce są opisane po polsku.
Wygląd (Chromium, duży zestaw z częścią ze stroną): pasek tylko Telefon, Komputer, Wskaż, Zbuduj podgląd; bez
„Strona części”, „Zbudowano”, „Otwórz w nowej karcie” na wierzchu; jedna karta Uwagi z „Więcej”; przy pracującym
agencie (atrapa odpowiedzi /api/strona) domyślnie wersja w budowie z przełącznikiem; bez poziomego przewijania 393–1440 px.
"""
import json
import os
import subprocess
import unittest

from test_strona import GIT, IDENT, Strona
from wspolne import agents, server
import strona

HERE = os.path.dirname(os.path.abspath(__file__))


class Opisy(unittest.TestCase):
    def test_czynnosci_w_przegladarce(self):
        d = agents.describe_tool
        self.assertEqual(d("mcp__przegladarka__browser_navigate", {"url": "http://127.0.0.1:4567/kontakt"}),
                         "Przeglądarka: otwiera /kontakt")
        self.assertEqual(d("mcp__przegladarka__browser_resize", {"width": 390, "height": 844}),
                         "Przeglądarka: szerokość 390×844")
        self.assertEqual(d("mcp__przegladarka__browser_take_screenshot", {}), "Przeglądarka: zrzut ekranu")
        self.assertEqual(d("mcp__przegladarka__browser_click", {"element": "Menu", "ref": "e3"}), "Przeglądarka: klika Menu")
        self.assertEqual(d("Edit", {"file_path": "/r/a.py"}, "/r"), "Edit: a.py")              # inne bez zmian


class PrzegladarkaCodex(Strona):
    card_lines = "- strona: site\n- strona build: npm run build:panel\n- strona wynik: dist\n"

    def setUp(self):
        super().setUp()
        self.cli = os.path.join(self.tmp, "cli.js")
        open(self.cli, "w").close()
        self.m = self.new_manager(PANEL_PRZEGLADARKA_MCP=self.cli, PANEL_PRZEGLADARKA_CHROME="/opt/chrome")
        server._agents = self.m
        with open(os.path.join(self.folder, "ZADANIA.md"), "a", encoding="utf-8") as f:
            f.write("- [ ] Strona: większy nagłówek | kto: codex\n")
        server.data_invalidate()

    def test_codex_dostaje_przegladarke(self):
        self.set_mode("ok")
        t = self.task("Strona: większy nagłówek")
        code, err, extra = self.m.run_task(t["id"], t["title"])
        self.assertEqual(code, 200, err)
        self.wait(extra["id"], manager=self.m)
        call = [c for c in self.calls() if "Strona: większy nagłówek" in (c.get("prompt") or "")][-1]
        args = call["argv"]
        self.assertIn("exec", args)
        conf = [args[i + 1] for i, a in enumerate(args) if a == "-c" and args[i + 1].startswith("mcp_servers.przegladarka.")]
        keys = {c.split("=", 1)[0]: c.split("=", 1)[1] for c in conf}
        self.assertEqual(keys["mcp_servers.przegladarka.default_tools_approval_mode"], '"approve"')
        self.assertIn("browser_navigate", json.loads(keys["mcp_servers.przegladarka.enabled_tools"]))
        self.assertNotIn("browser_run_code_unsafe", keys["mcp_servers.przegladarka.enabled_tools"])
        mcp_args = json.loads(keys["mcp_servers.przegladarka.args"])
        self.assertEqual(mcp_args[0], self.cli)
        out = mcp_args[mcp_args.index("--output-dir") + 1]
        self.assertEqual(os.path.basename(out), ".zrzuty")                     # zrzuty przeglądarki widać w panelu
        self.assertTrue(any(a.startswith("http://127.0.0.1:") for a in mcp_args))
        self.assertIn("mcp_servers.przegladarka.env.XDG_CACHE_HOME", keys)      # pamięć Chromium w katalogu roboczym
        self.assertIn("mcp__przegladarka", call["prompt"])                      # zasady przeglądarki w poleceniu
        self.assertEqual(args[-1], "-")                                         # polecenie z wejścia na końcu

    def test_czynnosci_codex_w_przebiegu(self):
        rec = self.m._new("task", "codex", "Strona: x", project=self.pid, file="ZADANIA.md")
        self.m._runs[rec["id"]] = rec
        self.m._on_codex(rec, {"type": "item.started", "item": {"type": "mcp_tool_call", "server": "przegladarka",
                                                               "tool": "browser_navigate",
                                                               "arguments": {"url": "http://127.0.0.1:5000/"}}}, {}, "/r")
        self.assertIn("Przeglądarka: otwiera /", [x["text"] for x in rec.get("log") or []])


@unittest.skipUnless(GIT, "brak polecenia git")
class SamoBudowanie(Strona):
    def setUp(self):
        super().setUp()
        self.git("init", "-q")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "start")

    def git(self, *args):
        return subprocess.run(["git"] + IDENT + list(args), cwd=self.folder, check=True, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, encoding="utf-8").stdout.strip()

    def test_nowsze_pliki_strony_buduja_podglad(self):
        build = self.site.build_now(self.pid)
        self.assertEqual(build["state"], "ok", build)
        version = build["version"]
        self.assertTrue(build["tree"])
        self.assertEqual(self.info()["build"]["state"], "ok")                  # to samo drzewo: bez budowania
        with open(os.path.join(self.folder, "docs", "inne.md"), "w", encoding="utf-8") as f:
            f.write("inne\n")
        self.git("add", "docs/inne.md")                                         # (wynik budowania site/dist nie w repozytorium)
        self.git("commit", "-q", "-m", "poza strona")
        self.assertEqual(self.info()["build"]["state"], "ok")                  # zmiana poza folderem strony
        path = os.path.join(self.folder, "site", "index.html")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        with open(path, "w", encoding="utf-8") as f:
            f.write(text.replace("</body>", "<p>Nowy akapit</p></body>"))
        self.git("commit", "-qam", "zmiana strony")                             # np. scalenie ręczne albo pobranie
        self.info()
        self.wait_for(lambda: self.info()["build"].get("version", 0) > version and
                      self.info()["build"]["state"] == "ok", timeout=30)
        status, _, page = self.request("GET", self.info()["url"])
        self.assertIn("Nowy akapit", page)

    def test_blad_nie_buduje_w_kolko(self):
        path = os.path.join(self.folder, "KARTA.md")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        with open(path, "w", encoding="utf-8") as f:
            f.write(text.replace("python3 zbuduj.py", "python3 -c \"import sys; sys.exit(3)\" #"))
        server.data_invalidate()
        build = self.site.build_now(self.pid)
        self.assertEqual(build["state"], "error")
        self.assertEqual(self.info()["build"]["state"], "error")                # ten sam błąd: bez ponownego budowania
        self.assertEqual(self.site._read(self.pid)["build"]["at"], build["at"])

    def test_reczne_scalenie_po_bledzie(self):
        title = "Strona: Dodaj akapit"
        note = {"id": "n1", "kind": "uwaga", "at": strona.now_iso(), "text": "Dodaj akapit", "title": title,
                "outcome": "nie wyszło", "error": "Nie scalono zmian: Scalenie zmieniłoby niezatwierdzone pliki: a."}
        self.site._update(self.pid, note=note)
        self.site.after_merge({"title": title, "project": self.pid, "changes": []})
        self.wait_for(lambda: self.note(title)["state"] == "zrobione", timeout=30)
        self.assertEqual(self.site._read(self.pid)["build"]["state"], "ok")


PAGE = r"""
import json, sys
from playwright.sync_api import sync_playwright
U = sys.argv[1]
H = "#p-portal-strona?cz=portal-www"
out, errs = {}, []
def fake(route):
    r = route.fetch(); j = r.json()
    if j.get("url"):
        j["live"] = {"runId": "20261125-120000-0001", "title": "Strona: popraw nagłówek", "state": "running",
                     "activity": "Przeglądarka: zrzut ekranu", "startedAt": "2026-11-25T12:00:00+01:00",
                     "steps": [{"t": "12:03", "text": "Przeglądarka: otwiera /"}], "recent": [], "plan": [],
                     "shots": [], "builtAt": "2026-11-25T12:02:30+01:00", "url": j["url"] + "~budowa/", "browser": True}
    route.fulfill(response=r, body=json.dumps(j), headers=dict(r.headers, **{"content-type": "application/json"}))
TXT = ("Strona części", "Zbudowano", "Otwórz w nowej karcie", "Uwaga do strony", "Otwórz podgląd w nowej karcie")
def look(pg):
    for _ in range(40):
        if pg.locator(".ww-fit:not([hidden]) iframe").count(): break
        pg.wait_for_timeout(500)
    pg.wait_for_timeout(400)
    txt = pg.evaluate("document.querySelector('#view').innerText")
    return {"sw": pg.evaluate("document.documentElement.scrollWidth"),
            "bar": pg.evaluate("[...document.querySelectorAll('.ww-bar button')].filter(e=>e.checkVisibility()).map(e=>e.textContent.trim())"),
            "cards": pg.evaluate("[...document.querySelectorAll('.ww-side h2')].filter(e=>e.checkVisibility()).map(e=>e.firstChild.textContent.trim())"),
            "txt": {k: k in txt for k in TXT},
            "src": pg.evaluate("(document.querySelector('.ww-fit iframe')||{}).src||''"),
            "pressed": pg.evaluate("[...document.querySelectorAll('[data-wwlv][aria-pressed=true]')].map(e=>e.dataset.wwlv)")}
with sync_playwright() as p:
    b = p.chromium.launch()
    for w in (393, 768, 1024, 1440):
        ctx = b.new_context(viewport={"width": w, "height": 852 if w < 500 else 900}, is_mobile=w < 500, has_touch=w < 500)
        pg = ctx.new_page(); pg.on("pageerror", lambda e: errs.append("%d: %s" % (w, e)))
        pg.goto(U + H); r = out[w] = {"zwykly": look(pg)}
        pg.locator("[data-wwcondet] > summary").click(); pg.wait_for_timeout(200)
        r["wiecej"] = pg.evaluate("document.querySelector('[data-wwcondet]').innerText")
        r["sw-wiecej"] = pg.evaluate("document.documentElement.scrollWidth")
        pg.route("**/api/strona?*", fake)
        pg.reload(); r["agent"] = look(pg)
        pg.locator("[data-wwlv=built]").click(); pg.wait_for_timeout(300)
        r["po"] = {"src": pg.evaluate("document.querySelector('.ww-fit iframe').src"),
                   "pressed": pg.evaluate("[...document.querySelectorAll('[data-wwlv][aria-pressed=true]')].map(e=>e.dataset.wwlv)")}
        ctx.close()
    b.close()
print(json.dumps({"out": out, "errs": errs}, ensure_ascii=False))
"""


try:
    from test_asystent_duzy import PW, Duzy
    from test_ui_przebudowa import PART_CARD, add_part
except ImportError:  # pragma: no cover
    PW, Duzy = "", unittest.TestCase


@unittest.skipUnless(PW and not os.environ.get("PANEL_TESTY_BEZ_RENDERU"), "brak Playwright albo PANEL_TESTY_BEZ_RENDERU")
class Wyglad(Duzy):
    def setUp(self):
        super().setUp()
        import test_ui_przebudowa as t
        card = t.PART_CARD
        t.PART_CARD = card.replace("- strona: www\n", "- strona: www\n- strona build: mkdir -p dist && cp index.html dist/\n")
        try:
            add_part(self.big)
        finally:
            t.PART_CARD = card
        server.data_invalidate()

    def test_pasek_karta_uwagi_i_praca_agenta(self):
        env = dict(os.environ)
        if not env.get("PLAYWRIGHT_BROWSERS_PATH") and os.path.isdir("/opt/ms-playwright"):
            env["PLAYWRIGHT_BROWSERS_PATH"] = "/opt/ms-playwright"
        r = subprocess.run([PW, "-c", PAGE, "http://127.0.0.1:%d/" % self.port], capture_output=True, text=True,
                           timeout=600, env=env)
        self.assertEqual(r.returncode, 0, r.stderr[-3000:])
        res = json.loads(r.stdout.strip().split("\n")[-1])
        self.assertEqual(res["errs"], [])
        for w, o in res["out"].items():
            w = int(w)
            z, a = o["zwykly"], o["agent"]
            self.assertEqual(z["bar"], ["Telefon", "Komputer", "Wskaż", "Zbuduj podgląd"], w)   # podgląd zbudował się sam
            self.assertEqual(z["txt"], {k: False for k in z["txt"]}, w)
            self.assertEqual(z["cards"], ["Uwagi"], w)                                        # jedna karta
            self.assertIn("/podglad/portal-www/", z["src"])
            self.assertIn("Nowa wersja według koncepcji", o["wiecej"])                       # pod „Więcej”
            self.assertIn("Otwórz podgląd w nowej karcie", o["wiecej"])
            self.assertEqual(a["bar"][:2], ["Wersja w budowie", "Ostatnia zbudowana"], w)
            self.assertIn("/~budowa/", a["src"])                                              # domyślnie wersja w budowie
            self.assertEqual(a["pressed"], ["live"])
            self.assertEqual(a["cards"], ["Agent pracuje nad stroną", "Uwagi"], w)
            self.assertNotIn("~budowa", o["po"]["src"])                                       # przełącznik
            self.assertEqual(o["po"]["pressed"], ["built"])
            for k in ("zwykly", "agent"):
                self.assertLessEqual(o[k]["sw"], w, (w, k))                                   # bez poziomego przewijania
            self.assertLessEqual(o["sw-wiecej"], w, w)


if __name__ == "__main__":
    unittest.main()
