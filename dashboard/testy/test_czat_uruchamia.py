"""Czaty uruchamiają pracę (AGENCI.md, „Uruchamianie z rozmów”): wiersz „Uruchom:” w odpowiedzi rozmowy o projekcie
i asystenta, „Polecenie:” i „Odpowiedź na pytanie:”, „Wyślij i wykonaj” w Rozmowie w projekcie z odnośnikiem do zadania,
stan uruchomienia w historii rozmowy. Render HTML → PDF/PNG."""
import http.client
import json
import os
import time
import re
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer

from test_instagram import CHROME, PANEL, panel_parts, read
from wspolne import TODAY, Baza, agents, server

EXTRA = """- [x] Gotowe agenta | kto: claude
- [ ] Zgoda agenta | kto: claude | kiedy: %s | wymaga: zgoda
""" % TODAY


class WierszDzialania(unittest.TestCase):
    def test_parsowanie(self):
        text, found = agents.take_run_lines(
            "Zakładam zadanie.\nZmieniono: ZADANIA.md\nUruchom: proj | Przygotuj wizytówkę\n"
            "- uruchom:  „Napisz ofertę”\nUruchom: proj | Przygotuj wizytówkę\n`Uruchom: inny | A | B`")
        self.assertEqual(text, "Zakładam zadanie.\nZmieniono: ZADANIA.md")
        self.assertEqual(found, [("proj", "Przygotuj wizytówkę"), ("", "Napisz ofertę"), ("inny | A", "B")])
        many = "\n".join("Uruchom: p | Z%d" % i for i in range(5))
        self.assertEqual(len(agents.take_run_lines(many)[1]), agents.RUN_MAX)
        self.assertEqual(agents.take_run_lines("Bez działań.\nUruchomię to jutro."), ("Bez działań.\nUruchomię to jutro.", []))
        self.assertEqual(agents.take_run_lines("Uruchom:   ")[1], [])

    def test_polecenie_i_odpowiedz(self):
        text, found = agents.take_actions(
            "Dobrze.\nPolecenie: proj | Strona: nagłówek | Zmień kolor na granatowy | i pogrub\n"
            "Odpowiedź na pytanie: proj | 2 | Tak, wersja B\nPolecenie: proj | bez polecenia\nUruchom: proj | X")
        self.assertEqual(text, "Dobrze.")
        self.assertEqual(found, [("order", ("proj", "Strona: nagłówek", "Zmień kolor na granatowy | i pogrub")),
                                 ("answer", ("proj", "2", "Tak, wersja B")), ("run", ("proj", "X"))])
        many = "\n".join("Polecenie: p | Z%d | zrób" % i for i in range(3)) + "\nUruchom: p | Y"
        self.assertEqual(len(agents.take_actions(many)[1]), agents.RUN_MAX)   # razem z Uruchom: najwyżej 3

    def test_zrob_to_na_koncu(self):
        for t in ("Dodaj stopkę. Zrób to", "popraw kolory, wykonaj", "Wykonaj to!", "zrob to."):
            self.assertTrue(agents.EXEC_END.search(t), t)
        for t in ("Jak mam to zrobić?", "wykonaj test jutro?", "Kto wykona to zadanie?"):
            self.assertFalse(agents.EXEC_END.search(t), t)


class Uruchamianie(Baza):
    def setUp(self):
        super().setUp()
        with open(os.path.join(self.folder, "ZADANIA.md"), encoding="utf-8") as f:
            text = f.read()
        with open(os.path.join(self.folder, "ZADANIA.md"), "w", encoding="utf-8") as f:
            f.write(text.replace("\n## Do rozplanowania", EXTRA + "\n## Do rozplanowania"))
        self.pid = self.task("Zadanie A")["project"]

    def tearDown(self):
        for m in self.managers:
            for r in list(m._runs.values()):
                if r["state"] in agents.LIVE:
                    m.stop(r["id"])
        super().tearDown()

    def text(self):
        with open(os.path.join(self.folder, "ZADANIA.md"), encoding="utf-8") as f:
            return f.read()

    def task_runs(self, title=None, manager=None):
        runs = (manager or self.manager)._runs.values()
        return [r for r in runs if r["kind"] == "task" and (title is None or r["title"] == title)]

    def launch(self, line, manager=None, pid=None):
        return (manager or self.manager).chat_launches("Odpowiedź.\n" + line, self.pid if pid is None else pid)[1]

    # ---------- rozmowa o projekcie ----------
    def test_rozmowa_o_projekcie_uruchamia_raz(self):
        self.set_mode("ok")
        code, _, _ = self.manager.project_chat_send(self.pid, "Przygotuj to. Uruchom: %s | Auto dziś" % self.pid)
        self.assertEqual(code, 202)
        self.wait_for(lambda: not self.manager.project_chat_get(self.pid)[2]["pending"])
        msgs = self.manager.project_chat_get(self.pid)[2]["messages"]
        self.assertEqual([m["role"] for m in msgs], ["ty", "claude", "panel"])
        self.assertNotIn("Uruchom:", msgs[1]["text"])               # wiersz działania nie trafia do rozmowy
        self.assertEqual(msgs[2]["text"], "Uruchomiono: Auto dziś")
        self.assertEqual(msgs[2]["taskId"], self.task("Auto dziś")["id"])
        runs = self.task_runs("Auto dziś")
        self.assertEqual(len(runs), 1)                              # run_task wołany raz
        self.wait(runs[0]["id"])
        last = self.manager.project_chat_get(self.pid)[2]["messages"][-1]
        self.assertEqual((last["live"], last["label"]), ("done", "zrobione"))   # stan aktualizuje się sam
        prompt = [c for c in self.calls() if "json" in c["argv"]][0]["prompt"]
        self.assertIn("Uruchom: %s | <dokładny tytuł zadania>" % self.pid, prompt)
        self.assertIn("kto: agent | kiedy: %s" % TODAY, prompt)

    def test_rozmowa_bez_prosby_nie_uruchamia(self):
        self.manager.project_chat_send(self.pid, "Co mam zrobić jutro?")
        self.wait_for(lambda: not self.manager.project_chat_get(self.pid)[2]["pending"])
        msgs = self.manager.project_chat_get(self.pid)[2]["messages"]
        self.assertEqual([m["role"] for m in msgs], ["ty", "claude"])
        self.assertEqual(self.task_runs(), [])

    def test_kolejka_przy_zajetym_agencie(self):
        m = self.new_manager(PANEL_AGENTS_MAX="1")
        self.set_mode("wolno")
        self.assertEqual(self.run_task("Auto dziś", manager=m)[0], 200)
        msg = self.launch("Uruchom: %s | Zadanie A" % self.pid, manager=m)[0]
        self.assertEqual(msg["text"], "W kolejce: agent pracuje nad „Auto dziś”, to zadanie ruszy po nim.")
        self.assertEqual(m.get(msg["runId"])["state"], "queued")
        self.assertEqual(m.panel_view([msg])[0]["label"], "w kolejce")
        self.assertEqual(len(self.task_runs("Zadanie A", manager=m)), 1)
        again = self.launch("Uruchom: Zadanie A", manager=m)[0]       # drugi raz: bez nowego uruchomienia
        self.assertEqual((again["text"], again["runId"]), ("Już w toku: Zadanie A", msg["runId"]))
        self.assertEqual(len(self.task_runs("Zadanie A", manager=m)), 1)

    def test_blokady(self):
        cases = {"Zgoda agenta": "Nie uruchomiono „Zgoda agenta”: czeka na Twoją zgodę.",
                 "Zadanie E": "Nie uruchomiono „Zadanie E”: czeka na Twoją zgodę.",
                 "Zadanie D": "Nie uruchomiono „Zadanie D”: zadanie po Twojej stronie.",
                 "Zadanie B": "Nie uruchomiono „Zadanie B”: zadanie nie ma wykonawcy agenta (kto: agent, claude albo codex).",
                 "Nie ma takiego": "Nie uruchomiono „Nie ma takiego”: nie ma takiego zadania w ZADANIA.md."}
        for title, text in cases.items():
            msg = self.launch("Uruchom: %s | %s" % (self.pid, title))[0]
            self.assertEqual((msg["text"], msg["runId"]), (text, ""), title)
        self.assertEqual(self.task_runs(), [])
        self.assertIn("wymaga: zgoda", self.row("Zgoda agenta"))
        self.assertTrue(self.row("Zgoda agenta").startswith("- [ ]"))

    def test_logowanie_i_limit(self):
        self.manager._state["needsLogin"] = True
        msg = self.launch("Uruchom: Auto dziś")[0]
        self.assertEqual(msg["text"], "Uruchomiono: Auto dziś")
        self.assertEqual(self.wait(msg["runId"])["tool"], "codex")
        self.manager._state["needsLogin"] = False
        self.manager._state["limitUntil"] = "2999-01-01T13:45:00"
        self.manager._record_limits("codex", {"five": (0.9, time.time(), time.time() + 60)})
        msg = self.launch("Uruchom: Zadanie A")[0]
        self.assertIn("Żaden dozwolony wykonawca", msg["text"])
        self.assertEqual(len(self.task_runs()), 1)

    def test_asystent_projekt_z_nazwy(self):
        self.set_mode("wolno")
        msg = self.launch("Uruchom: Projekt testowy | Zadanie A", pid="")[0]
        self.assertEqual(msg["text"], "Uruchomiono: Zadanie A")
        self.assertEqual(len(self.task_runs("Zadanie A")), 1)

    def test_asystent_uruchamia(self):
        self.set_mode("ok")
        code, _, _ = self.manager.assistant_send("Zrób to. Uruchom: %s | Auto dziś" % self.pid)
        self.assertEqual(code, 202)
        self.wait_for(lambda: not self.manager.assistant_get()[2]["pending"])
        msgs = self.manager.assistant_get()[2]["messages"]
        self.assertEqual([m["role"] for m in msgs], ["ty", "claude", "panel"])
        self.assertNotIn("Uruchom", msgs[1]["text"])
        self.assertEqual(msgs[2]["text"], "Uruchomiono: Auto dziś")
        self.assertEqual(len(self.task_runs("Auto dziś")), 1)

    def test_stara_sesja_zaczyna_od_nowa(self):
        """Rozmowa zapisana przed nowymi zasadami (bez v) nie jest wznawiana: nowa sesja dostaje pełny prompt."""
        path = self.manager._project_chat_file(self.pid)
        os.makedirs(os.path.dirname(path))
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"session": "stara", "pending": False, "error": "", "messages": []}, f)
        self.manager.project_chat_send(self.pid, "Pytanie")
        self.wait_for(lambda: not self.manager.project_chat_get(self.pid)[2]["pending"])
        argv = [c for c in self.calls() if "json" in c["argv"]][-1]["argv"]
        self.assertNotIn("--resume", argv)
        self.manager.project_chat_send(self.pid, "Drugie")
        self.wait_for(lambda: not self.manager.project_chat_get(self.pid)[2]["pending"])
        argv = [c for c in self.calls() if "json" in c["argv"]][-1]["argv"]
        self.assertEqual(argv[argv.index("--resume") + 1], "sesja-1")

    # ---------- Rozmowa w projekcie z odnośnikiem do zadania: Wyślij i wykonaj ----------
    def execute(self, title, text, **kw):
        t = self.task(title)
        return self.manager.project_chat_send(self.pid, text, t["id"], **kw)

    def msgs(self):
        return self.manager.project_chat_get(self.pid)[2]["messages"]

    def test_wyslij_i_wykonaj(self):
        self.set_mode("wolno")
        code, err, extra = self.execute("Zadanie A", "Dopisz sekcję o cenach.", execute=True)
        self.assertEqual((code, err), (200, ""))
        self.assertEqual(extra["status"]["text"], "Uruchomiono: Zadanie A")
        self.assertEqual(extra["status"]["label"], "w toku")
        with open(os.path.join(self.folder, "ZADANIA.md"), encoding="utf-8") as f:
            self.assertIn("- [~] Zadanie A | kto: claude | gdzie: mac\n  poprawka: Dopisz sekcję o cenach.", f.read())
        self.assertEqual(len(self.task_runs("Zadanie A")), 1)
        self.assertEqual([c for c in self.calls() if "json" in c["argv"]], [])      # bez modelu rozmowy
        msgs = self.msgs()
        self.assertEqual([m["role"] for m in msgs], ["ty", "panel"])
        self.assertTrue(msgs[0]["exec"])
        self.assertEqual(msgs[0]["task"]["title"], "Zadanie A")

    def test_polecenie_z_odpowiedzi_rozmowy(self):
        """Model w Rozmowie w projekcie (albo w Asystencie) daje polecenie do istniejącego zadania: poprawka i run_task."""
        self.set_mode("wolno")
        out = self.launch("Polecenie: %s | Gotowe agenta | Zmień kolor na granatowy" % self.pid)
        self.assertEqual(out[0]["text"], "Uruchomiono: Gotowe agenta")
        self.assertIn("poprawka: Zmień kolor na granatowy", self.text())
        out = self.manager.chat_launches("Ok.\nPolecenie: %s | Zadanie D | zrób za mnie" % self.pid, "")[1]
        self.assertIn("nie jest dla agenta (kto: ty)", out[0]["text"])            # Asystent: te same reguły
        out = self.launch("Polecenie: %s | Zgoda agenta | dodaj logo" % self.pid)
        self.assertEqual(out[0]["text"], "Nie uruchomiono „Zgoda agenta”: czeka na Twoją zgodę.")
        self.assertEqual(len(self.task_runs()), 1)

    def test_odpowiedz_na_pytanie_z_rozmowy(self):
        seen = []
        self.manager.answer_hook = lambda body: (seen.append(body) or (200, ""))
        out = self.launch("Odpowiedź na pytanie: %s | 1 | Tak, wersja B" % self.pid)
        self.assertEqual(seen, [{"id": self.pid, "n": 1, "answer": "Tak, wersja B"}])
        self.assertTrue(out[0]["text"].startswith("Zapisano odpowiedź na pytanie 1"))
        self.manager.answer_hook = lambda body: (400, "Nie zapisano: nie ma takiego pytania.")
        out = self.manager.chat_launches("Ok.\nOdpowiedź na pytanie: %s | 9 | x" % self.pid, "")[1]
        self.assertIn("Nie zapisano odpowiedzi na pytanie 9", out[0]["text"])
        out = self.launch("Odpowiedź na pytanie: obcy | 1 | x")
        self.assertIn("Nie zapisano", out[0]["text"])
        import inspect                                                    # ta sama droga co przycisk przy pytaniu
        self.assertIn("answer_hook = answer_question", inspect.getsource(server.get_agents))

    def test_zrob_to_wraca_zrobione_do_poprawy(self):
        self.set_mode("wolno")
        code, _, extra = self.execute("Gotowe agenta", "Zmień kolor na granatowy, zrób to")
        self.assertEqual(code, 200)
        self.assertEqual(extra["status"]["text"], "Uruchomiono: Gotowe agenta")
        self.assertTrue(self.row("Gotowe agenta").startswith("- [~]"))
        rid = extra["status"]["runId"]
        prompt = self.manager._priv[rid]["prompt"]
        self.assertIn("Poprawka od właściciela (wiersz poprawka:): Zmień kolor na granatowy, zrób to", prompt)

    def test_wykonaj_przy_zadaniu_wlasciciela_i_zgodzie(self):
        before = self.text()
        code, _, extra = self.execute("Zadanie D", "Zrób to za mnie", execute=True)
        self.assertEqual((code, extra), (202, {"pending": True}))         # zadanie właściciela: zwykła rozmowa
        self.wait_for(lambda: not self.manager.project_chat_get(self.pid)[2]["pending"])
        self.assertEqual(self.text(), before)
        code, _, extra = self.execute("Zgoda agenta", "Dodaj logo", execute=True)
        self.assertEqual(extra["status"]["text"], "Nie uruchomiono „Zgoda agenta”: czeka na Twoją zgodę.")
        self.assertIn("wymaga: zgoda", self.row("Zgoda agenta"))       # polecenie zapisane, zgoda zostaje
        self.assertEqual(self.task_runs(), [])

    def test_do_odbioru_po_pracy(self):
        self.set_mode("zostaw")                 # agent kończy bez [x]: panel dopisuje wymaga: odbiór
        rid = self.execute("Zadanie A", "Zrób szkic", execute=True)[2]["status"]["runId"]
        self.wait(rid)
        last = self.manager.project_chat_get(self.pid)[2]["messages"][-1]
        self.assertEqual((last["live"], last["label"]), ("done", "do odbioru"))
        # poprawka po odbiorze: odbiór znika, zadanie wraca do pracy
        self.set_mode("wolno")
        extra = self.execute("Zadanie A", "Krótszy tytuł", execute=True)[2]
        self.assertEqual(extra["status"]["text"], "Uruchomiono: Zadanie A")
        self.assertNotIn("odbiór", self.row("Zadanie A"))

    def test_serwer(self):
        self._log = server.Handler.log_message
        server.Handler.log_message = lambda *args: None
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        try:
            self.set_mode("wolno")
            t = self.task("Zadanie A")
            conn = http.client.HTTPConnection("127.0.0.1", httpd.server_address[1], timeout=15)
            conn.request("POST", "/api/project/chat", body=json.dumps(
                {"project": self.pid, "task": t["id"], "message": "Popraw", "execute": True}).encode("utf-8"),
                headers={"Content-Type": "application/json"})
            resp = conn.getresponse()
            body = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(resp.status, 200)
            self.assertEqual(body["status"]["text"], "Uruchomiono: Zadanie A")
        finally:
            httpd.shutdown()
            httpd.server_close()
            server.Handler.log_message = self._log

    # ---------- render HTML → PDF/PNG ----------
    def test_render_w_narzedziach_i_poleceniu(self):
        m = self.new_manager(PANEL_RENDER="/opt/py /opt/html-do-pdf.py")
        self.set_mode("ok")
        t = self.task("Zadanie A")
        rid = m.run_task(t["id"], t["title"])[2]["id"]
        self.wait(rid, manager=m)
        call = [c for c in self.calls() if "stream-json" in c["argv"]][-1]
        allowed = call["argv"][call["argv"].index("--allowedTools") + 1].split(",")
        self.assertIn("Bash(/opt/py /opt/html-do-pdf.py:*)", allowed)
        self.assertNotIn("Bash", allowed)
        self.assertIn("`/opt/py /opt/html-do-pdf.py <plik.html> <wynik.pdf> <wynik.png>`", call["prompt"])
        none = self.new_manager(PANEL_RENDER_PYTHON=os.path.join(self.tmp, "brak-pythona"))
        self.assertEqual(none.render_command(), "")
        self.assertIn("niedostępna", " ".join(none.render_rules()))
        self.assertEqual(self.new_manager(PANEL_RENDER_PYTHON=sys.executable).render_command(),
                         "%s %s" % (sys.executable, agents.RENDER_SCRIPT))


SCRIPT = agents.RENDER_SCRIPT
PW = next((p for p in ("/home/agent/narzedzia/pw/bin/python",) if os.path.isfile(p)), "")


class SkryptRenderu(unittest.TestCase):
    def run_script(self, args, cwd, py=sys.executable):
        return subprocess.run([py, SCRIPT] + args, cwd=cwd, capture_output=True, text=True, timeout=120)

    def test_odrzuca_adres_i_wynik_poza_folderem(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "a.html"), "w") as f:
                f.write("<p>x</p>")
            r = self.run_script(["https://example.com/a.html", "a.pdf"], tmp)
            self.assertEqual(r.returncode, 2)
            self.assertIn("adresy z sieci", r.stderr)
            r = self.run_script(["a.html", "/tmp/../tmp/poza-%d.pdf" % os.getpid()], os.path.join(tmp))
            self.assertEqual(r.returncode, 2)
            self.assertIn("tylko w folderze", r.stderr)
            r = self.run_script(["a.html", "a.exe"], tmp)
            self.assertEqual(r.returncode, 2)

    @unittest.skipUnless(PW and not os.environ.get("PANEL_TESTY_BEZ_RENDERU"), "brak Playwright albo PANEL_TESTY_BEZ_RENDERU")
    def test_pdf_i_png(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "w.html"), "w", encoding="utf-8") as f:
                f.write("<!doctype html><meta charset=utf-8><style>@page{size:90mm 50mm;margin:0}</style>"
                        "<h1>Wizytówka</h1><img src='https://example.com/x.png'>")
            r = self.run_script(["w.html", "out/w.pdf", "out/w.png", "--strona", "90x50mm"], tmp, py=PW)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("Zablokowano 1 zasobów z sieci", r.stdout)
            self.assertEqual(read(os.path.join(tmp, "out", "w.pdf"))[:5], b"%PDF-")
            self.assertEqual(read(os.path.join(tmp, "out", "w.png"))[:8], b"\x89PNG\r\n\x1a\n")


PW_PAGE = """import sys
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page()
    pg.goto("file://" + sys.argv[1])
    print(pg.inner_text("#w"))
    b.close()
"""


def page_result(path, tmp):
    """Tekst #w strony po wykonaniu skryptu: Chromium z Playwright (serwer) albo Chrome bez okna (Mac)."""
    if PW:
        env = dict(os.environ)
        if not env.get("PLAYWRIGHT_BROWSERS_PATH") and os.path.isdir("/opt/ms-playwright"):
            env["PLAYWRIGHT_BROWSERS_PATH"] = "/opt/ms-playwright"
        out = subprocess.run([PW, "-c", PW_PAGE, path], capture_output=True, text=True, timeout=90, env=env)
        return out.stdout.strip(), out.stderr
    out = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
                          "--user-data-dir=" + os.path.join(tmp, "profil"), "--virtual-time-budget=3000",
                          "--dump-dom", "file://" + path], capture_output=True, text=True, timeout=60)
    import html as H
    m = re.search(r'<pre id="w">(.*?)</pre>', out.stdout, re.S)
    return (H.unescape(m.group(1)) if m else ""), out.stderr


@unittest.skipUnless((PW or CHROME) and not os.environ.get("PANEL_TESTY_BEZ_RENDERU"),
                     "brak Playwright i Chrome albo PANEL_TESTY_BEZ_RENDERU: test czatu zadania w przeglądarce pominięty")
class CzatZadaniaWChrome(unittest.TestCase):
    def test_przycisk_i_stan(self):
        code = panel_parts(read(PANEL).decode("utf-8"), ["esc", "shortT", "chatText", "PNL", "pnMsg", "attLabel", "chatRef",
                                                         "chatMsg", "pnLive", "chatBox"])
        page = """<!doctype html><meta charset="utf-8"><body><pre id="w"></pre><script>
const LIVE=true,DR={kind:'task',id:'a'},loadChat=()=>{},P=()=>null,wwLinks=h=>h;
const CH={a:{messages:[{role:'ty',text:'Zrób szkic'},{role:'panel',text:'Uruchomiono: A',label:'w toku',live:'running',taskId:'a'}],
  pending:false,error:''},b:{messages:[{role:'panel',text:'Uruchomiono: B',label:'do odbioru',live:'done',taskId:'b'}],pending:false,error:''},
  d:{messages:[],pending:false,error:''}};
%s
const r={};
const ha=chatBox({id:'a',executor:'claude',title:'A'}),hd=chatBox({id:'d',executor:'ty',title:'D'});
r.ask=!/data-askt|Zapytaj o to zadanie/.test(ha+hd)&&hd==='';
r.field=/<textarea|<form|data-chatexec|Wyślij/.test(ha+hd);
r.old=/Dawna rozmowa o zadaniu \\(2\\)/.test(ha)&&!/Dawna rozmowa/.test(hd);
r.stan=(ha.match(/<span class="lz [a-z]+">[^<]+/g)||[]).map(x=>x.replace(/.*class="lz /,'').replace('">',':'));
r.linkHere=/data-task="a"/.test(ha);
r.linkOther=/data-task="b"/.test(pnMsg(CH.b.messages[0],'a'));
r.ref=chatMsg({role:'ty',text:'x',task:{id:'b',title:'Zadanie B'},exec:true},'a',null);
r.live=[pnLive(CH.a.messages),pnLive(CH.b.messages)];
document.getElementById('w').textContent=JSON.stringify(r);
</script>""" % code
        with tempfile.TemporaryDirectory(prefix="panel-czat-") as tmp:
            path = os.path.join(tmp, "czat.html")
            with open(path, "w", encoding="utf-8") as f:
                f.write(page)
            text, err = page_result(path, tmp)
        self.assertTrue(text, err[-500:])
        r = json.loads(text)
        self.assertTrue(r["ask"])                        # w zadaniu bez „Zapytaj o to zadanie” (decyzja 2026-11-25)
        self.assertFalse(r["field"])                     # bez pola rozmowy i „Wyślij i wykonaj”
        self.assertTrue(r["old"])                        # dawna rozmowa do odczytu
        self.assertEqual(r["stan"], ["blue:w toku"])
        self.assertFalse(r["linkHere"])                  # w szufladzie tego zadania bez linku do niego samego
        self.assertTrue(r["linkOther"])
        self.assertIn("O zadaniu:", r["ref"])
        self.assertIn('data-task="b"', r["ref"])
        self.assertEqual(r["live"], [True, False])


if __name__ == "__main__":
    unittest.main()
