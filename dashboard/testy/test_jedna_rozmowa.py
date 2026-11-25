"""Jedna rozmowa (zlecenie 2026-11-25): z agentem rozmawia się tylko w Asystencie i w Rozmowie w projekcie.

Sprawdza: w panelu nie ma czatu przy zadaniu (tylko „Zapytaj o to zadanie”), uwaga ze Strony idzie przez Rozmowę
w projekcie z załącznikiem (to samo zadanie agenta i run_task co dawny formularz), przyciski jednego działania wołają
run_task, a w Chromium z emulacją iPhone 15 (393 px, dotyk) na dużym zestawie: brak poziomego przewijania, okna
w ekranie, przewijanie szuflady, odblokowana strona po zamknięciu, cele dotyku ≥ 44 px w szufladzie i rozmowie,
rozmowa nad klawiaturą ekranową (visualViewport)."""
import json
import os
import re
import subprocess
import unittest

from test_asystent_duzy import PW, Duzy
from test_instagram import PANEL, read
from test_strona import Strona
from wspolne import Baza, agents, server


class Panel(unittest.TestCase):
    """panel.html: jedno okno rozmowy, bez czatu w szczegółach zadania i bez formularza „Co zmienić?” na Stronie."""

    @classmethod
    def setUpClass(cls):
        cls.html = read(PANEL).decode("utf-8")

    def test_brak_czatu_przy_zadaniu(self):
        self.assertNotIn("post('/api/task/chat'", self.html)              # nic nie wysyła do dawnego czatu zadania
        for gone in ("data-chatexec", "data-chatask", "sendChat(", "odAskSend", "data-odform=\"ask\"", "Tylko zapytaj"):
            self.assertNotIn(gone, self.html)
        box = re.search(r"function chatBox\(t\)\{(.*?)\n\}", self.html, re.S).group(1)
        self.assertIn("Zapytaj o to zadanie", box)
        self.assertNotIn("<textarea", box)
        self.assertIn("Dawna rozmowa o zadaniu", box)                     # historia zostaje do odczytu

    def test_strona_bez_osobnego_formularza(self):
        for gone in ("data-wwform", "wwSend(", "'/api/strona/uwaga'", "Wyślij agentowi</button></div></form></section>'+\n      '<section class=\"panel\"><h2>Uwagi"):
            self.assertNotIn(gone, self.html)
        self.assertIn("data-wwnote", self.html)                           # „Napisz uwagę” otwiera Rozmowę
        self.assertIn("pjdAttach(pid,s)", self.html)                      # „Wskaż” też: załącznik w Rozmowie
        self.assertIn("body.attach={kind:'strona'", self.html)

    def test_jedna_droga_wysylki(self):
        posts = set(re.findall(r"post\('(/api/(?:project/chat|asystent|task/chat))'", self.html))
        self.assertEqual(posts, {"/api/project/chat", "/api/asystent"})   # dwie rozmowy, jedna droga zapisu
        fix = re.search(r"function sendFix\(t,text\)\{(.*?)\n\}", self.html, re.S).group(1)
        self.assertIn("post('/api/project/chat',{project:t.project,task:t.id,message:text,execute:true})", fix)
        prx = re.search(r"function prxDelegate\(pid\)\{(.*?)\n\}", self.html, re.S).group(1)
        self.assertIn("post('/api/agent/run'", prx)                       # „Zleć agentowi uzupełnienie” uruchamia

    def test_rozmowa_w_szufladzie_i_odbiorze(self):
        tgt = re.search(r"function dockTarget\(r\)\{(.*?)\n\}", self.html, re.S).group(1)
        for where in ("DR.kind==='task'", "r.v==='odbior'", "r.v==='projekt'"):
            self.assertIn(where, tgt)
        self.assertIn("visualViewport", self.html)                        # klawiatura ekranowa


class StronaPrzezRozmowe(Strona):
    def test_uwaga_z_zalacznikiem(self):
        self.set_mode("strona")
        att = {"kind": "strona", "project": self.pid, "page": "/", "view": "telefon", "selector": "#tytul",
               "elementText": "Witaj"}
        status, answer = self.post("/api/project/chat", {"project": self.pid, "message": "Większy nagłówek", "attach": att})
        self.assertEqual(status, 200, answer)
        title = answer["note"]["title"]
        self.assertEqual(title, "Strona: Większy nagłówek")
        self.assertTrue(answer["runId"])
        self.assertEqual(answer["status"]["text"], "Uwaga do strony: zadanie „Strona: Większy nagłówek” dla agenta.")
        note = self.wait_note(title)                                      # lista uwag zostaje jako stan
        self.assertEqual(note["state"], "zrobione", note)
        with open(os.path.join(self.folder, "ZADANIA.md"), encoding="utf-8") as f:
            text = f.read()
        self.assertIn("Element: #tytul, tekst „Witaj”", text)
        self.assertIn("widok telefon (390 px)", text)
        self.assertEqual([c for c in self.calls() if "json" in c["argv"] and "--output-format" in c["argv"]
                          and c["argv"][c["argv"].index("--output-format") + 1] == "json"], [])   # bez modelu rozmowy
        msgs = self.manager.project_chat_get(self.pid)[2]["messages"]
        self.assertEqual([m["role"] for m in msgs], ["ty", "panel"])
        self.assertEqual(msgs[0]["attach"]["selector"], "#tytul")
        self.assertEqual(msgs[1]["runId"], answer["runId"])
        # strona spoza projektu rozmowy: odmowa
        status, answer = self.post("/api/project/chat", {"project": self.pid, "message": "x",
                                                         "attach": dict(att, project="obcy")})
        self.assertEqual(status, 404)


class JednaDroga(Baza):
    """Przyciski jednego działania zakładają zadanie i wołają run_task (te same reguły co „Uruchom”)."""

    def setUp(self):
        super().setUp()
        server._agents = self.manager
        self.started = []
        real = self.manager.run_task
        self.manager.run_task = lambda tid, title, **kw: (self.started.append(title) or real(tid, title, **kw))

    def test_studio_popros_uruchamia(self):
        self.set_mode("wolno")
        code, err, extra = server.studio_request({"project": "projekt-testowy", "rodzaj": "marka",
                                                  "uwaga": "Logo większe na końcu"})
        self.assertEqual((code, err), (200, ""))
        self.assertEqual(self.started, [extra["title"]])
        self.assertTrue(extra["started"])

    def test_odbior_popraw_przez_rozmowe(self):
        self.set_mode("wolno")
        t = self.task("Zadanie A")
        code, _, extra = self.manager.review_fix(t["id"], t["title"], "Krótszy tytuł", [])
        self.assertEqual(code, 200)
        self.assertEqual(self.started, ["Zadanie A"])
        msgs = self.manager.project_chat_get(t["project"])[2]["messages"]   # stan w Rozmowie w projekcie
        self.assertEqual([m["role"] for m in msgs], ["ty", "panel"])
        self.assertEqual(msgs[0]["task"]["title"], "Zadanie A")
        self.assertEqual(msgs[1]["text"], "Uruchomiono: Zadanie A")
        self.assertEqual(self.manager.chat_get(t["id"])[2]["messages"], [])  # nic nie trafia do dawnego czatu

    def test_polecenie_z_asystenta_i_rozmowy_ta_sama_droga(self):
        self.set_mode("wolno")
        pid = self.task("Zadanie A")["project"]
        a = self.manager.chat_launches("Ok.\nPolecenie: %s | Zadanie A | dopisz stopkę" % pid, "")[1]
        self.assertEqual(a[0]["text"], "Uruchomiono: Zadanie A")
        b = self.manager.chat_launches("Ok.\nPolecenie: %s | Zadanie A | i nagłówek" % pid, pid)[1]
        self.assertIn(b[0]["text"], ("Przekazano agentowi.", "Zadanie czeka w kolejce: polecenie dołączone do zadania "
                                     "(poprawka).", "Agent skończył, polecenie zapisane jako poprawka. Zadanie uruchomi "
                                     "się ponownie z tym poleceniem.",
                                     "Codex nie przyjmuje wiadomości w trakcie pracy. Polecenie zapisane jako poprawka: "
                                     "zatrzymaj i uruchom z poprawką albo poczekaj na koniec pracy."))
        self.assertEqual(self.started, ["Zadanie A"])                     # drugie polecenie: do pracującego agenta


IPHONE = r"""
import json, sys
from playwright.sync_api import sync_playwright
U = sys.argv[1]
FAKE = '''(()=>{const t=new EventTarget();t.width=393;t.height=659;t.offsetTop=0;t.offsetLeft=0;t.scale=1;t.pageTop=0;
Object.defineProperty(window,'visualViewport',{get:()=>t,configurable:true});window.__vv=t})();'''
M = '''(sel)=>{const W=innerWidth,H=innerHeight,de=document.documentElement,vis=e=>{const s=getComputedStyle(e);return s.display!=='none'&&s.visibility!=='hidden'};
 const r={sw:Math.max(de.scrollWidth,document.body.scrollWidth),W,out:[],small:[]};
 for(const s of ['#drawer','.pjd-win','.pjd-btn','.od-box'])for(const e of document.querySelectorAll(s)){if(!vis(e))continue;const b=e.getBoundingClientRect();
   if(b.width&&(b.left<-1||b.top<-1||b.right>W+1||b.bottom>H+1))r.out.push(s)}
 if(sel)for(const e of document.querySelectorAll(sel)){if(!vis(e))continue;const b=e.getBoundingClientRect();if(!b.width||!b.height)continue;
   if(e.matches('input')&&e.closest('label')){const l=e.closest('label').getBoundingClientRect();if(l.height>=44)continue}
   if(e.matches('.lk')&&getComputedStyle(e).display.startsWith('inline'))continue;
   if(b.height<44||b.width<44)r.small.push((e.textContent||e.getAttribute('aria-label')||'').trim().slice(0,30)+' '+Math.round(b.width)+'x'+Math.round(b.height))}
 return r}'''
T = '#drawer button,#drawer .btn,#drawer summary,#drawer select,#drawer input[type=checkbox],#pjdock button,#pjdock .btn'
out, errs = {}, []
with sync_playwright() as p:
    dev = dict(p.devices["iPhone 15"]); dev.pop("default_browser_type", None)
    b = p.chromium.launch(); ctx = b.new_context(**dev); ctx.add_init_script(FAKE); pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
    def go(h): pg.goto(U + h); pg.wait_for_timeout(900)
    def task(tid): pg.evaluate("id=>{const b=document.createElement('button');b.dataset.task=id;document.body.appendChild(b);b.click();b.remove()}", tid); pg.wait_for_timeout(500)
    for h in ("#asystent", "#marketing", "#media", "#agenci", "#koszty", "#p-firmowa", "#p-firmowa-tablica", "#p-firmowa-marketing",
              "#p-firmowa-etapy", "#p-firmowa-wskazniki", "#p-firmowa-ksiega", "#p-firmowa-strona?cz=firmowa-onepager",
              "#p-firmowa-tablica?cz=firmowa-onepager"):
        go(h); out[h] = pg.evaluate(M, "")
    go("#p-firmowa"); pg.locator("#pjdock [data-pjd=open]").click(); pg.wait_for_timeout(400)
    out["rozmowa"] = pg.evaluate(M, "#pjdock button,#pjdock .btn")
    pg.locator("#pjdock [data-pjd=close]").click(); pg.wait_for_timeout(300)
    out["rozmowa"]["po"] = pg.evaluate("document.body.classList.contains('sl')")
    go("#p-firmowa-tablica"); task("firmowa-onepager|ZADANIA.md|6")
    pg.evaluate("()=>document.querySelectorAll('#drawer details').forEach(d=>d.open=true)"); pg.wait_for_timeout(400)
    r = out["szuflada"] = pg.evaluate(M, T)
    r["lock"] = pg.evaluate("document.body.classList.contains('sl')")
    r["scroll"] = pg.evaluate("(()=>{const d=document.querySelector('#drawer');const a=d.scrollTop;d.scrollTop=a+200;const ok=d.scrollTop>a||d.scrollHeight<=d.clientHeight;d.scrollTop=a;return ok})()")
    r["textarea"] = pg.locator("#drawer textarea[data-cq]").count()
    pg.locator("#drawer [data-askt]").first.click(); pg.wait_for_timeout(500)
    r = out["zapytaj"] = pg.evaluate(M, "#pjdock button,#pjdock .btn")
    r["ref"] = pg.locator("#pjdock .pjd-chip").inner_text()
    r["exec"] = pg.locator("#pjdock [data-pjdx]").count()
    pg.locator("#pjdock textarea").focus()
    pg.evaluate("()=>{window.__vv.height=359;window.__vv.dispatchEvent(new Event('resize'))}"); pg.wait_for_timeout(400)
    r["kb"] = pg.evaluate("(()=>{const t=document.querySelector('#pjdock textarea').getBoundingClientRect(),w=document.querySelector('#pjdock .pjd-win').getBoundingClientRect();return [Math.round(w.top),Math.round(t.bottom)]})()")
    pg.evaluate("()=>{window.__vv.height=659;window.__vv.dispatchEvent(new Event('resize'))}"); pg.wait_for_timeout(200)
    pg.locator("#pjdock [data-pjd=close]").click(); pg.wait_for_timeout(200)
    pg.locator("#drawer [data-close]").first.click(); pg.wait_for_timeout(300)
    out["zamknij"] = pg.evaluate("(()=>{scrollTo(0,300);const y=scrollY;scrollTo(0,0);return {lock:document.body.classList.contains('sl'),y:y}})()")
    go("#p-firmowa-strona?cz=firmowa-onepager"); pg.wait_for_timeout(600)
    pg.locator("[data-wwnote]").first.click(); pg.wait_for_timeout(500)
    r = out["strona"] = pg.evaluate(M, "#pjdock button,#pjdock .btn")
    r["att"] = pg.locator("#pjdock .pjd-chip").inner_text()
    go("#odbior?z=erp%7CZADANIA.md%7C20"); pg.wait_for_timeout(800)
    out["odbior"] = pg.evaluate(M, "")
    out["odbior"]["ask"] = pg.locator("#view [data-askt]").count()
    d = pg.locator("#view .od-det")
    out["odbior"]["details"] = d.evaluate("el=>el.open")
    d.locator("summary").first.click()
    out["odbior"]["after"] = d.evaluate("el=>el.open")
    b.close()
print(json.dumps({"out": out, "errs": errs}, ensure_ascii=False))
"""


def add_site_part(big):
    """Część „firmowa-onepager” (strona: site) projektu „firmowa” w dużym zestawie: zakładka Strona i zadanie z krokami."""
    part = os.path.join(big, "firmowa-onepager")
    os.makedirs(os.path.join(part, "site", "dist"))
    with open(os.path.join(big, "firmowa", "KARTA.md"), encoding="utf-8") as f:
        card = f.read()
    head, _, rest = card.partition("\n")
    with open(os.path.join(part, "KARTA.md"), "w", encoding="utf-8") as f:
        f.write("# Karta projektu: Strona firmowa – Strona WWW\n\n- część projektu: firmowa\n- strona: site\n"
                "- strona build: true\n- strona wynik: dist\n" + rest)
    with open(os.path.join(part, "ZADANIA.md"), "w", encoding="utf-8") as f:
        f.write("# Zadania: Strona WWW\n\n## Etap: Wersja robocza\ntermin: 2026-12-10\n\n"
                "- [ ] Strona: przygotuj podgląd nowej strony w panelu (wersja robocza, nagłówek, sekcja usług, stopka "
                "z danymi kontaktowymi) | kto: claude\n  cel: pierwsza wersja strony do oceny w zakładce Strona\n"
                "  gotowe gdy: podgląd buduje się\n  - [x] krok: szkielet strony\n  - [ ] krok: sekcja usług\n\n"
                "## Do rozplanowania\n")
    with open(os.path.join(part, "site", "dist", "index.html"), "w", encoding="utf-8") as f:
        f.write("<!doctype html><title>Firma</title><h1>Nowa strona</h1>")
    path = os.path.join(big, "projekty.json")
    with open(path, encoding="utf-8") as f:
        reg = json.load(f)
    reg["projekty"].append(part)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(reg, f)


@unittest.skipUnless(PW and not os.environ.get("PANEL_TESTY_BEZ_RENDERU"), "brak Playwright albo PANEL_TESTY_BEZ_RENDERU")
class Iphone15(Duzy):
    """Chromium z emulacją iPhone 15 (393x659 widoczne, dotyk) na dużym zestawie z częścią ze stroną."""

    def test_uklad_393(self):
        add_site_part(self.big)
        server.data_invalidate()
        self.manager.site.build_api("firmowa-onepager")
        self.wait_for(lambda: self.manager.site.info("firmowa-onepager")[2].get("url"), timeout=20)
        env = dict(os.environ)
        if not env.get("PLAYWRIGHT_BROWSERS_PATH") and os.path.isdir("/opt/ms-playwright"):
            env["PLAYWRIGHT_BROWSERS_PATH"] = "/opt/ms-playwright"
        r = subprocess.run([PW, "-c", IPHONE, "http://127.0.0.1:%d/" % self.port], capture_output=True, text=True,
                           timeout=600, env=env)
        self.assertEqual(r.returncode, 0, r.stderr[-3000:])
        res = json.loads(r.stdout.strip().split("\n")[-1])
        self.assertEqual(res["errs"], [])
        out = res["out"]
        for k, o in out.items():
            if "sw" in o:
                self.assertLessEqual(o["sw"], o["W"], k)                  # bez poziomego przewijania
                self.assertEqual(o["out"], [], k)                         # okna i szuflady w ekranie
                self.assertEqual(o["small"], [], k)                       # cele dotyku ≥ 44 px
        self.assertFalse(out["rozmowa"]["po"])                            # po zwinięciu strona się przewija
        s = out["szuflada"]
        self.assertTrue(s["lock"])                                        # tło stoi pod szufladą
        self.assertTrue(s["scroll"])
        self.assertEqual(s["textarea"], 0)                                # bez czatu w szczegółach zadania
        z = out["zapytaj"]
        self.assertIn("O zadaniu:", z["ref"])
        self.assertIn("Strona: przygotuj podgląd", z["ref"])
        self.assertEqual(z["exec"], 1)                                    # „Wyślij i wykonaj” przy zadaniu agenta
        self.assertGreaterEqual(z["kb"][0], 0)
        self.assertLessEqual(z["kb"][1], 359)                             # pole nad klawiaturą ekranową
        self.assertFalse(out["zamknij"]["lock"])                          # po zamknięciu nic nie blokuje strony
        self.assertIn("Załącznik: Strona", out["strona"]["att"])
        self.assertFalse(out["odbior"]["details"])
        self.assertTrue(out["odbior"]["after"])
        self.assertEqual(out["odbior"]["ask"], 1)                         # odbiór: „Zapytaj o to zadanie”


if __name__ == "__main__":
    unittest.main()
