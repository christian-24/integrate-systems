"""Udostępnianie na Facebooku, LinkedInie i TikToku (i Instagramie) przez jedno rozszerzenie Chrome
(uruchom/chrome-udostepnij): pakiet z platformą (udostepnij.py), trasa POST /api/udostepnij, CORS tylko dla dokładnych
adresów platformy pakietu, pola karty facebook:/linkedin:/tiktok:, wybór platformy i okno zapasowe w panelu,
rozszerzenie na atrapach stron tworzenia posta.

Testy w Chrome uruchamiają przeglądarkę bez okna z pustym profilem tymczasowym (nigdy profil właściciela) i tylko na
lokalnych atrapach; bez Chrome albo z PANEL_TESTY_BEZ_RENDERU są pomijane."""
import html as H
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import unittest
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import test_instagram as ti
from test_instagram import CHROME, EXT, PANEL, panel_parts, read
from test_serwer import REMOTE
from wspolne import TESTY, server

import udostepnij

BEZ_CHROME = not CHROME or bool(os.environ.get("PANEL_TESTY_BEZ_RENDERU"))
ORIG = {"instagram": "https://www.instagram.com", "business": "https://business.facebook.com",
        "facebook": "https://www.facebook.com", "linkedin": "https://www.linkedin.com", "tiktok": "https://www.tiktok.com"}


class Pakiet(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="panel-ud-")
        for n in ("grafika.png", "zdjecie-1.jpg", "film.mp4"):
            with open(os.path.join(self.tmp, n), "wb") as f:
                f.write(b"x")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_opis_platformy(self):
        s = {"sections": {"Facebook": "fb", "Instagram": "ig", "LinkedIn": "li", "Reels": "re"}}
        self.assertEqual([udostepnij.caption(s, p) for p in ("instagram", "facebook", "linkedin", "tiktok")],
                         ["ig", "fb", "li", "re"])
        self.assertEqual(udostepnij.caption({"sections": {"Instagram": "ig"}}, "linkedin"), "ig")
        self.assertEqual(udostepnij.caption({"sections": {}}, "tiktok"), "")

    def test_pliki_tiktok_tylko_film(self):
        g, f = os.path.join(self.tmp, "grafika.png"), os.path.join(self.tmp, "film.mp4")
        self.assertEqual(udostepnij.media(self.tmp, None, g, "tiktok"), [])
        self.assertEqual(udostepnij.media(self.tmp, f, g, "tiktok"), [f])
        self.assertEqual(len(udostepnij.media(self.tmp, None, g, "linkedin")), 2)

    def test_adresy_tworzenia(self):
        self.assertEqual(udostepnij.compose_url("facebook"), "https://business.facebook.com/latest/composer")
        self.assertEqual(udostepnij.compose_url("facebook", film=True, reels=True),
                         "https://business.facebook.com/latest/reels_composer")
        self.assertEqual(udostepnij.compose_url("facebook", film=False, reels=True),
                         "https://business.facebook.com/latest/composer")
        self.assertEqual(udostepnij.compose_url("linkedin", text="a b&c"),
                         "https://www.linkedin.com/feed/?shareActive=true&text=a%20b%26c")
        self.assertEqual(udostepnij.compose_url("tiktok"), "https://www.tiktok.com/tiktokstudio/upload")
        self.assertEqual(udostepnij.compose_url("instagram"), "https://www.instagram.com/")

    def test_cors_dokladne_adresy(self):
        self.assertTrue(udostepnij.origin_ok("https://business.facebook.com", "facebook"))
        self.assertTrue(udostepnij.origin_ok("https://www.facebook.com", "facebook"))
        self.assertFalse(udostepnij.origin_ok("https://www.instagram.com", "facebook"))
        self.assertFalse(udostepnij.origin_ok("https://facebook.com", "facebook"))
        self.assertFalse(udostepnij.origin_ok("https://www.linkedin.com.zla.example", "linkedin"))
        self.assertFalse(udostepnij.origin_ok("http://www.tiktok.com", "tiktok"))
        self.assertTrue(udostepnij.origin_ok("https://www.tiktok.com"))          # pakiet nieznany: każda platforma
        self.assertFalse(udostepnij.origin_ok("https://zla.example"))
        self.assertEqual(udostepnij.ORIGINS, frozenset(ORIG.values()))

    def test_pakiet_z_platforma(self):
        sh = udostepnij.Shares()
        tok = sh.create("Post", "opis", [os.path.join(self.tmp, "film.mp4")], "marka", "tiktok")
        self.assertEqual(sh.platform(tok), "tiktok")
        self.assertFalse(sh.status(tok)["fetched"])                # platform() nie zaznacza pobrania
        self.assertEqual(sh.package(tok)["platforma"], "tiktok")
        self.assertEqual(sh.package(sh.create("P", "", [], ""))["platforma"], "instagram")
        with self.assertRaises(ValueError):
            sh.create("P", "", [], "", "myspace")


class TrasyPlatform(ti.Trasy):
    """Trasa /api/udostepnij dla każdej platformy (folder posta z grafiką i zdjęciem jak w test_instagram.Trasy)."""

    def setUp(self):
        super().setUp()
        path = os.path.join(self.folder, "kampanie", "rytm.md")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        text = text.replace("kanał: facebook | kiedy", "kanał: facebook, linkedin, tiktok, reels | kiedy")
        text = text.replace("## Wyniki", "- [ ] Opublikuj post „Film” | kto: ty | kanał: tiktok, reels | kiedy: 2026-11-21\n\n## Wyniki")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        post = os.path.join(self.folder, "posty", "2026-11-21-film")
        os.makedirs(post)
        for n, body in (("film.mp4", b"MP4"), ("post.md", "# Film\n\n## Reels\nOpis rolki\n".encode("utf-8"))):
            with open(os.path.join(post, n), "wb") as f:
                f.write(body)
        self.karta("- instagram: @Shield.Silent\n- facebook: Shield & Silent\n- linkedin: Shield Silent sp. z o.o.\n- tiktok: @Shield.Silent")

    def karta(self, line):
        path = os.path.join(self.folder, "KARTA.md")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        text = re.sub(r"\n- (?:instagram|facebook|linkedin|tiktok):.*", "", text)
        head, rest = text.split("\n", 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(head + "\n" + (line + "\n" if line else "") + rest)

    def share(self, title, platform, **kw):
        t = self.task(title)
        return self.post("/api/udostepnij", {"id": t["id"], "title": t["title"], "platforma": platform}, **kw)

    def test_pola_karty(self):
        p = self.data()["projects"][0]
        self.assertEqual((p["facebook"], p["linkedin"], p["tiktok"]), ("Shield & Silent", "Shield Silent sp. z o.o.", "shield.silent"))
        self.karta("- tiktok: zła nazwa!\n- facebook: " + "x" * 120)
        p = self.data()["projects"][0]
        self.assertEqual((p["tiktok"], p["facebook"], p["linkedin"]), ("", "", ""))
        gaps = [g for d in p["book"] for g in d["gaps"]]
        self.assertTrue(any("tiktok:" in g for g in gaps) and any("facebook:" in g for g in gaps), gaps)

    def test_pakiety_platform(self):
        code, ans = self.share("Opublikuj post „Inny”", "facebook")
        self.assertEqual(code, 200, ans)
        self.assertEqual((ans["platform"], ans["handle"], ans["files"], ans["url"]),
                         ("facebook", "Shield & Silent", 2, "https://business.facebook.com/latest/composer"))
        code, ans = self.share("Opublikuj post „Inny”", "linkedin")
        self.assertEqual((code, ans["handle"]), (200, "Shield Silent sp. z o.o."))
        self.assertTrue(ans["url"].startswith("https://www.linkedin.com/feed/?shareActive=true&text="), ans["url"])
        code, ans = self.share("Opublikuj post „Film”", "tiktok")
        self.assertEqual((code, ans["files"], ans["handle"]), (200, 1, "shield.silent"))
        self.assertEqual(ans["url"], "https://www.tiktok.com/tiktokstudio/upload")
        code, ans = self.share("Opublikuj post „Film”", "facebook")           # film na kanale reels: tworzenie rolki
        self.assertEqual(ans["url"], "https://business.facebook.com/latest/reels_composer")
        # dawna trasa: Instagram
        t = self.task("Opublikuj post „Start”")
        code, ans = self.post("/api/instagram/udostepnij", {"id": t["id"], "title": t["title"]})
        self.assertEqual((code, ans["platform"], ans["url"]), (200, "instagram", "https://www.instagram.com/"))

    def test_odmowy(self):
        self.assertEqual(self.share("Opublikuj post „Inny”", "tiktok")[0], 409)            # TikTok bez filmu
        self.assertEqual(self.share("Opublikuj post „Start”", "tiktok")[0], 400)           # kanał bez TikToka
        self.assertEqual(self.share("Opublikuj post „Film”", "linkedin")[0], 400)          # kanał bez LinkedIna
        self.assertEqual(self.share("Opublikuj post „Inny”", "myspace")[0], 400)
        self.karta("")
        code, ans = self.share("Opublikuj post „Inny”", "linkedin")
        self.assertEqual((code, ans["handle"]), (200, ""))
        self.assertIn("linkedin:", ans["warning"])

    def test_cors_per_platforma(self):
        code, fb = self.share("Opublikuj post „Inny”", "facebook")
        code, tt = self.share("Opublikuj post „Film”", "tiktok")
        server.TOKEN = "haslo-do-testow"
        try:
            for origin in (ORIG["business"], ORIG["facebook"]):
                status, hdr, text = self.request("GET", fb["path"], headers=dict(REMOTE, Origin=origin))
                self.assertEqual((status, hdr.get("Access-Control-Allow-Origin")), (200, origin))
                self.assertEqual(json.loads(text)["platforma"], "facebook")
            for origin in (ORIG["instagram"], ORIG["tiktok"], "https://zla.example", "https://facebook.com"):
                status, hdr, _ = self.request("GET", fb["path"], headers=dict(REMOTE, Origin=origin))
                self.assertNotIn("Access-Control-Allow-Origin", hdr, origin)
            status, hdr, body = self.request("GET", tt["path"] + "/0", headers=dict(REMOTE, Origin=ORIG["tiktok"]))
            self.assertEqual((status, body, hdr.get("Access-Control-Allow-Origin")), (200, "MP4", ORIG["tiktok"]))
            status, hdr, _ = self.request("GET", tt["path"] + "/0", headers=dict(REMOTE, Origin=ORIG["linkedin"]))
            self.assertNotIn("Access-Control-Allow-Origin", hdr)
            status, hdr, _ = self.request("OPTIONS", tt["path"], headers=dict(REMOTE, Origin=ORIG["tiktok"], **{
                "Access-Control-Request-Method": "GET", "Access-Control-Request-Private-Network": "true"}))
            self.assertEqual((status, hdr.get("Access-Control-Allow-Origin"), hdr.get("Access-Control-Allow-Private-Network")),
                             (204, ORIG["tiktok"], "true"))
            status, hdr, _ = self.request("OPTIONS", tt["path"], headers=dict(REMOTE, Origin="https://zla.example"))
            self.assertEqual(status, 204)
            self.assertNotIn("Access-Control-Allow-Origin", hdr)
            # pakiet wygasły: komunikat czytelny dla każdej platformy, dla obcego adresu bez nagłówka
            status, hdr, _ = self.request("GET", "/udostepnij/" + "0" * 32, headers=dict(REMOTE, Origin=ORIG["linkedin"]))
            self.assertEqual((status, hdr.get("Access-Control-Allow-Origin")), (404, ORIG["linkedin"]))
            status, hdr, _ = self.request("GET", "/udostepnij/" + "0" * 32, headers=dict(REMOTE, Origin="https://zla.example"))
            self.assertNotIn("Access-Control-Allow-Origin", hdr)
            # stan pobrania i tworzenie pakietu tylko z sesją
            self.assertEqual(self.request("GET", "/api/udostepnij?t=" + tt["token"], headers=REMOTE)[0], 401)
            self.assertEqual(self.share("Opublikuj post „Film”", "tiktok", headers=REMOTE)[0], 401)
        finally:
            server.TOKEN = ""
        status, _, text = self.request("GET", "/api/udostepnij?t=" + fb["token"])
        self.assertTrue(json.loads(text)["fetched"])
        status, _, text = self.request("GET", "/api/udostepnij?t=" + tt["token"])
        self.assertFalse(json.loads(text)["fetched"])                # sam plik to nie pobranie pakietu


class PanelKod(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = read(PANEL).decode("utf-8")

    def test_okno_zapasowe_i_obecnosc(self):
        h = self.html
        self.assertIn("Rozszerzenie Chrome nie jest zainstalowane albo nieaktywne.", h)
        self.assertIn("chrome://extensions", h)
        self.assertIn("uruchom/chrome-udostepnij", h)
        self.assertIn("data-panel-rozszerzenie", h)
        self.assertIn("UDP={'sp-ig':'instagram','sp-fb':'facebook','sp-li':'linkedin','sp-tt':'tiktok'}", h)
        self.assertIn("for(const f of ['facebook','linkedin','tiktok'])", h)

    def test_manifest_panel_i_platformy(self):
        man = json.loads(read(os.path.join(EXT, "manifest.json")))
        by = {tuple(c["js"]): c["matches"] for c in man["content_scripts"]}
        self.assertEqual(by[("wspolne.js", "selektory/facebook.js", "facebook.js")],
                         ["https://business.facebook.com/*", "https://www.facebook.com/*"])
        self.assertEqual(by[("wspolne.js", "selektory/linkedin.js", "linkedin.js")], ["https://www.linkedin.com/*"])
        self.assertEqual(by[("wspolne.js", "selektory/tiktok.js", "tiktok.js")], ["https://www.tiktok.com/*"])
        self.assertIn("https://2-29-181-133.sslip.io/*", by[("panel.js",)])
        self.assertNotIn("permissions", man)
        self.assertNotIn("host_permissions", man)
        for root, _, names in os.walk(EXT):
            for n in names:
                if n.endswith(".js") and n != "wspolne.js":
                    js = read(os.path.join(root, n)).decode("utf-8")
                    self.assertNotIn(".click()", js, n)          # klika tylko safeClick w wspolne.js
                    self.assertNotIn("execCommand", js, n)
        # panel wie o tych samych adresach co manifest
        self.assertIn(r"2-29-181-133\.sslip\.io|localhost|127\.0\.0\.1", self.html)


def chrome_dump(url, tmp, budget=20000):
    out = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
                          "--user-data-dir=" + os.path.join(tmp, "profil"), "--virtual-time-budget=%d" % budget,
                          "--dump-dom", url], capture_output=True, text=True, timeout=90)
    return out


@unittest.skipIf(BEZ_CHROME, "brak Chrome albo PANEL_TESTY_BEZ_RENDERU: test panelu w przeglądarce pominięty")
class PanelWChrome(unittest.TestCase):
    """Wybór drogi w edytorze posta (API, rozszerzenie, telefon) i okno zapasowe, funkcje z panel.html w Chrome."""

    def test_wybor_platformy_i_zapas(self):
        h = read(PANEL).decode("utf-8")
        code = panel_parts(h, ["esc", "CHAL", "chList", "SPN", "SPCHAIN", "spCap", "chanOk", "UDP", "UDS", "udKey", "udExt",
                               "udKnown", "udPubName", "igCan", "udShare", "udWatch", "udClose", "udFallback", "igCopy",
                               "igGet", "edApi", "edGo"])
        panel_js = read(os.path.join(EXT, "panel.js")).decode("utf-8")
        page = """<!doctype html><meta charset="utf-8"><body><pre id="w"></pre><script>
let LIVE=true,coarse=false;const PRV='podgląd',PUBN={facebook:'Facebook',reels:'Reels',instagram:'Instagram',linkedin:'LinkedIn'};
const calls=[],opened=[];
const D={tasks:[{id:'t1',kind:'publikacja',state:'todo',project:'p',date:'2026-11-20',title:'Post',channel:'instagram, facebook, linkedin, tiktok, reels'}],
  publish:{fb:{pages:[]},li:{connected:false},state:{}}};
const P=()=>({instagram:''}),ED={cur:{tid:'t1',pid:'p',day:'2026-11-20'}},PD={'p|2026-11-20':{ok:true,film:{name:'film.mp4'},sections:{Facebook:'FB',LinkedIn:'LI',Reels:'RE'}}};
const say=m=>calls.push(['say',m]),igRedraw=()=>{},confirm=()=>true,enqueue=f=>calls.push(['api']),failMsg=()=>'',copyText=async()=>true;
const canShare=()=>coarse;window.matchMedia=()=>({matches:coarse});
function edManual(t,d,k){calls.push(['manual',k])}
async function post(u,b){calls.push(['post',u,b.platforma]);return {ok:true,data:{url:'https://example.test/compose?a=1',path:'/udostepnij/'+'a'.repeat(32),token:'a'.repeat(32),files:2,warning:''}}}
window.open=(u)=>{const w={location:{},close(){}};opened.push(w);return w};
window.fetch=async()=>({ok:true,json:async()=>({fetched:false})});
%s
(async()=>{
const r={};
for(const k of ['sp-ig','sp-fb','sp-li','sp-tt']){calls.length=0;edGo(k);await new Promise(x=>setTimeout(x,50));r[k]=calls.map(c=>c.join(':'))}
r.url=opened[0].location.href;
D.publish.fb.pages=[{project:'p',instagram:''}];calls.length=0;edGo('sp-fb');r.api=calls.map(c=>c[0]);
coarse=true;calls.length=0;edGo('sp-li');r.phone=calls.map(c=>c.join(':'));coarse=false;
calls.length=0;edGo('sp-gen');r.gen=calls.map(c=>c.join(':'));
udFallback('t1|sp-tt',false);r.noExt=document.getElementById('igfb').innerText;
r.btns=[...document.querySelectorAll('#igfb button')].map(b=>b.textContent);
udFallback('t1|sp-tt',true);r.ext=document.getElementById('igfb').innerText;
r.before=udExt();
%s
r.after=udExt();
document.getElementById('w').textContent=JSON.stringify(r);
})();
</script>""" % (code, panel_js)
        with tempfile.TemporaryDirectory(prefix="panel-ud-pv-") as tmp:
            path = os.path.join(tmp, "panel.html")
            with open(path, "w", encoding="utf-8") as f:
                f.write(page)
            out = chrome_dump("file://" + path, tmp, 3000)
        m = re.search(r'<pre id="w">(.*?)</pre>', out.stdout, re.S)
        self.assertTrue(m and m.group(1), out.stderr[-800:])
        r = json.loads(H.unescape(m.group(1)))
        for k, pl in (("sp-ig", "instagram"), ("sp-fb", "facebook"), ("sp-li", "linkedin"), ("sp-tt", "tiktok")):
            self.assertIn("post:/api/udostepnij:" + pl, r[k], r)
        self.assertTrue(r["url"].startswith("https://example.test/compose?a=1#us="), r["url"])
        self.assertTrue(r["url"].endswith(urllib.parse.quote("/udostepnij/" + "a" * 32, safe="")), r["url"])
        self.assertEqual(r["api"], ["api"])                        # Facebook z połączoną stroną: publikacja przez API
        self.assertEqual(r["phone"], ["manual:sp-li"])             # telefon: systemowe udostępnianie
        self.assertEqual(r["gen"], ["manual:sp-gen"])
        self.assertIn("Rozszerzenie Chrome nie jest zainstalowane albo nieaktywne.", r["noExt"])
        self.assertIn("chrome://extensions", r["noExt"])
        self.assertIn("Załaduj rozpakowane", r["noExt"])
        self.assertEqual(r["btns"], ["Kopiuj opis", "Pobierz pliki", "Zamknij"])
        self.assertIn("Rozszerzenie nie wczytało posta.", r["ext"])
        self.assertEqual((r["before"], r["after"]), ("", "1"))


@unittest.skipIf(BEZ_CHROME, "brak Chrome albo PANEL_TESTY_BEZ_RENDERU: test safeClick pominięty")
class SafeClick(unittest.TestCase):
    def test_odmawia_publikacji(self):
        js = read(os.path.join(EXT, "wspolne.js")).decode("utf-8")
        page = """<!doctype html><meta charset="utf-8"><body>
<button id="a">Opublikuj</button><div role="button" id="b"><span id="c">Share now</span></div><button id="d" aria-label="Publish"></button>
<button id="e">Dalej</button><pre id="w"></pre><script>%s
const r={};
for(const id of ['a','b','c','d','e']){try{PanelUd.safeClick(document.getElementById(id));r[id]='klik'}catch(e){r[id]=e.message}}
document.getElementById('w').textContent=JSON.stringify(r);
</script>""" % js
        with tempfile.TemporaryDirectory(prefix="panel-ud-sc-") as tmp:
            path = os.path.join(tmp, "sc.html")
            with open(path, "w", encoding="utf-8") as f:
                f.write(page)
            out = chrome_dump("file://" + path, tmp, 2000)
        m = re.search(r'<pre id="w">(.*?)</pre>', out.stdout, re.S)
        self.assertTrue(m and m.group(1), out.stderr[-500:])
        r = json.loads(H.unescape(m.group(1)))
        for k in "abcd":
            self.assertEqual(r[k], "próba kliknięcia przycisku publikacji", k)
        self.assertEqual(r["e"], "klik")


class AtrapaPlatform(BaseHTTPRequestHandler):
    shares = None
    tiktok_user = "shield.silent"

    def log_message(self, *a):
        pass

    def _out(self, code, body, ctype):
        raw = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        m = re.match(r"^/atrapa_(facebook|linkedin|tiktok)\.html$", path)
        if m:
            return self._out(200, read(os.path.join(TESTY, "atrapa_%s.html" % m.group(1))), "text/html; charset=utf-8")
        if path.startswith("/ext/"):
            rel = path[5:]
            full = os.path.realpath(os.path.join(EXT, rel))
            if re.match(r"^(?:selektory/)?[a-z]+\.js$", rel) and full.startswith(os.path.realpath(EXT)) and os.path.isfile(full):
                return self._out(200, read(full), "text/javascript; charset=utf-8")
        if path == "/passport/web/account/info/":
            return self._out(200, json.dumps({"data": {"username": self.tiktok_user}}), "application/json")
        parts = path.split("/")
        if path.startswith("/udostepnij/") and len(parts) == 3:
            pkg = self.shares.package(parts[2])
            return self._out(200 if pkg else 404, json.dumps(pkg or {"ok": False, "error": "wygasł"}), "application/json")
        if path.startswith("/udostepnij/") and len(parts) == 4:
            hit = self.shares.file(parts[2], parts[3])
            if hit:
                return self._out(200, read(hit[0]), hit[1])
        return self._out(404, "", "text/plain")


@unittest.skipIf(BEZ_CHROME, "brak Chrome albo PANEL_TESTY_BEZ_RENDERU: test rozszerzenia na atrapach pominięty")
class NaAtrapachPlatform(unittest.TestCase):
    CAPTION = "Opis posta\nDruga linia #marka"

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="panel-ud-chrome-")
        AtrapaPlatform.shares = udostepnij.Shares()
        AtrapaPlatform.tiktok_user = "shield.silent"
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), AtrapaPlatform)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.base = "http://127.0.0.1:%d" % self.httpd.server_address[1]

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def files(self, *names):
        out = []
        for n in names:
            p = os.path.join(self.tmp, n)
            with open(p, "wb") as f:
                f.write(n.encode("ascii") * 2)
            out.append(p)
        return out

    def run_page(self, atrapa, platform, handle, files, query="", caption=CAPTION):
        tok = AtrapaPlatform.shares.create("Post", caption, files, handle, platform)
        url = "%s/atrapa_%s.html%s#us=%s" % (self.base, atrapa, query,
                                              urllib.parse.quote(self.base + "/udostepnij/" + tok, safe=""))
        out = chrome_dump(url, self.tmp)
        m = re.search(r"<html([^>]*)>", out.stdout)
        self.assertTrue(m, out.stderr[-500:])
        return {k: H.unescape(v) for k, v in re.findall(r'(data-[\w-]+)="([^"]*)"', m.group(1))}

    def ready(self, attrs):
        self.assertEqual(attrs.get("data-panel-is"), "gotowe", attrs)
        self.assertNotIn("data-opublikowane", attrs)
        self.assertIn("Opublikuj", attrs.get("data-panel-is-text", ""))

    def test_facebook_zdjecia_przez_menu(self):
        attrs = self.run_page("facebook", "facebook", "Shield & Silent", self.files("grafika.png", "zdjecie-1.jpg"))
        self.ready(attrs)
        self.assertEqual(attrs.get("data-pliki"), "grafika.png:22:image/png,zdjecie-1.jpg:26:image/jpeg")
        self.assertEqual(attrs.get("data-opis"), self.CAPTION)
        self.assertEqual(attrs.get("data-panel-is-konto"), "zgodne")

    def test_facebook_rolka_przez_dalej(self):
        attrs = self.run_page("facebook", "facebook", "Inna strona", self.files("film.mp4"), query="?reels=1")
        self.ready(attrs)
        self.assertEqual(attrs.get("data-pliki"), "film.mp4:16:video/mp4")
        self.assertEqual(attrs.get("data-opis"), self.CAPTION)
        self.assertEqual(attrs.get("data-panel-is-konto"), "nieznane")       # nazwy strony nie widać: ostrzeżenie
        self.assertIn("sprawdź, czy to „Inna strona”", attrs.get("data-panel-is-text", ""))

    def test_facebook_sam_tekst(self):
        attrs = self.run_page("facebook", "facebook", "", [])
        self.ready(attrs)
        self.assertNotIn("data-pliki", attrs)
        self.assertEqual(attrs.get("data-panel-is-konto"), "brak")

    def test_linkedin_okno_samo_i_multimedia(self):
        attrs = self.run_page("linkedin", "linkedin", "Shield Silent sp. z o.o.", self.files("grafika.png"),
                              query="?shareActive=true")
        self.ready(attrs)
        self.assertEqual(attrs.get("data-pliki"), "grafika.png:22:image/png")
        self.assertEqual(attrs.get("data-opis"), self.CAPTION)
        self.assertEqual(attrs.get("data-panel-is-konto"), "zgodne")

    def test_linkedin_opis_z_adresu_bez_podwojenia(self):
        q = "?shareActive=true&text=" + urllib.parse.quote(self.CAPTION, safe="")
        attrs = self.run_page("linkedin", "linkedin", "", self.files("grafika.png"), query=q)
        self.ready(attrs)
        self.assertEqual(attrs.get("data-opis"), self.CAPTION)

    def test_linkedin_przycisk_zacznij(self):
        attrs = self.run_page("linkedin", "linkedin", "", [])
        self.ready(attrs)
        self.assertEqual(attrs.get("data-opis"), self.CAPTION)

    def test_tiktok_film_i_opis_zamiast_nazwy(self):
        attrs = self.run_page("tiktok", "tiktok", "shield.silent", self.files("film.mp4"))
        self.ready(attrs)
        self.assertEqual(attrs.get("data-pliki"), "film.mp4:16:video/mp4")
        self.assertEqual(attrs.get("data-opis"), self.CAPTION)                # nazwa pliku zastąpiona
        self.assertEqual(attrs.get("data-panel-is-konto"), "zgodne")

    def test_tiktok_inne_konto_zatrzymuje(self):
        AtrapaPlatform.tiktok_user = "prywatne"
        attrs = self.run_page("tiktok", "tiktok", "shield.silent", self.files("film.mp4"))
        self.assertEqual(attrs.get("data-panel-is"), "konto", attrs)
        self.assertIn("Zalogowany: @prywatne, a post jest dla @shield.silent", attrs.get("data-panel-is-text", ""))
        self.assertNotIn("data-pliki", attrs)

    def test_pakiet_innej_platformy(self):
        attrs = self.run_page("tiktok", "facebook", "", self.files("film.mp4"))
        self.assertEqual(attrs.get("data-panel-is"), "blad", attrs)
        self.assertIn("Ten post jest na Facebook", attrs.get("data-panel-is-text", ""))
        self.assertNotIn("data-pliki", attrs)


if __name__ == "__main__":
    unittest.main()
