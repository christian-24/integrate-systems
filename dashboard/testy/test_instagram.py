"""Udostępnienie posta na Instagramie: pakiet (udostepnij.py), trasy serwera, przycisk i podglądy w panelu,
rozszerzenie Chrome (uruchom/chrome-instagram) na atrapie strony tworzenia posta.

Test rozszerzenia uruchamia Chrome bez okna z pustym, tymczasowym profilem (nigdy profil właściciela) i tylko na
lokalnej atrapie; bez Chrome albo z PANEL_TESTY_BEZ_RENDERU jest pomijany."""
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

from test_serwer import REMOTE, Serwer
from wspolne import TESTY, projekt, server

import udostepnij

ROOT = os.path.dirname(os.path.dirname(TESTY))
EXT = os.path.join(ROOT, "uruchom", "chrome-instagram")
PANEL = os.path.join(ROOT, "dashboard", "panel.html")
CHROME = next((p for p in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                           shutil.which("google-chrome") or "", shutil.which("chromium") or "",
                           shutil.which("chromium-browser") or "") if p and os.path.exists(p)), "")
IG = {"Origin": "https://www.instagram.com"}


def read(path):
    with open(path, "rb") as f:
        return f.read()


class Pakiet(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="panel-ig-")
        for n in ("grafika.png", "zdjecie-2.jpg", "zdjecie-10.jpg", "zdjecie.png", "slajd-1.jpg", "inne.jpg", "film.mp4"):
            with open(os.path.join(self.tmp, n), "wb") as f:
                f.write(b"x" * 3)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_zdjecia_w_kolejnosci_i_film_sam(self):
        self.assertEqual(udostepnij.photos(self.tmp), ["zdjecie.png", "slajd-1.jpg", "zdjecie-2.jpg", "zdjecie-10.jpg"])
        g = os.path.join(self.tmp, "grafika.png")
        self.assertEqual([os.path.basename(p) for p in udostepnij.media(self.tmp, None, g)],
                         ["grafika.png", "zdjecie.png", "slajd-1.jpg", "zdjecie-2.jpg", "zdjecie-10.jpg"])
        self.assertEqual(udostepnij.media(self.tmp, os.path.join(self.tmp, "film.mp4"), g), [os.path.join(self.tmp, "film.mp4")])

    def test_opis_z_sekcji(self):
        self.assertEqual(udostepnij.caption({"sections": {"Facebook": "fb", "Instagram": "ig"}}), "ig")
        self.assertEqual(udostepnij.caption({"sections": {"Facebook": "fb"}}), "fb")

    def test_wygasa_i_zly_token(self):
        clock = [1000.0]
        sh = udostepnij.Shares(now=lambda: clock[0])
        tok = sh.create("Post", "opis", [os.path.join(self.tmp, "grafika.png")], "marka")
        self.assertEqual(sh.status(tok)["fetched"], False)
        pkg = sh.package(tok)
        self.assertEqual((pkg["handle"], pkg["files"][0]["url"], pkg["files"][0]["type"]), ("marka", tok + "/0", "image/png"))
        self.assertTrue(sh.status(tok)["fetched"])
        self.assertEqual(sh.file(tok, "0")[1], "image/png")
        self.assertIsNone(sh.file(tok, "1"))
        self.assertIsNone(sh.file(tok, "../0"))
        self.assertIsNone(sh.package("x" * 32))
        clock[0] += udostepnij.TTL + 1
        self.assertIsNone(sh.package(tok))
        self.assertIsNone(sh.file(tok, "0"))


class Trasy(Serwer):
    DAY = "2026-11-20"

    def setUp(self):
        super().setUp()
        os.makedirs(os.path.join(self.folder, "kampanie"), exist_ok=True)
        with open(os.path.join(self.folder, "kampanie", "rytm.md"), "w", encoding="utf-8") as f:
            f.write("# Kampania: Rytm\n\n- stan: w toku\n- kanały: instagram\n\n## Grupa docelowa\nx\n\n## Przekaz\nx\n\n"
                    "## Harmonogram\n- [ ] Opublikuj post „Start” | kto: ty | kanał: instagram, facebook | kiedy: %s\n"
                    "- [ ] Opublikuj post „Inny” | kto: ty | kanał: facebook | kiedy: %s\n\n## Wyniki i wnioski\n"
                    % (self.DAY, self.DAY))
        post = os.path.join(self.folder, "posty", self.DAY + "-start")
        os.makedirs(post)
        for n, body in (("grafika.png", b"PNG1"), ("zdjecie-1.jpg", b"JPG22"),
                        ("post.md", "# Start\n\n## Instagram\nOpis IG\n\n## Facebook\nOpis FB\n".encode("utf-8"))):
            with open(os.path.join(post, n), "wb") as f:
                f.write(body)
        self.karta("- instagram: @Shield.Silent")

    def karta(self, line):
        path = os.path.join(self.folder, "KARTA.md")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        text = re.sub(r"\n- instagram:.*", "", text)
        head, rest = text.split("\n", 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(head + "\n" + (line + "\n" if line else "") + rest)

    def task(self, title):
        return next(t for t in self.data()["tasks"] if t["title"] == title)

    def test_pole_karty(self):
        p = self.data()["projects"][0]
        self.assertEqual(p["instagram"], "shield.silent")
        self.karta("- instagram: zła nazwa!")
        p = self.data()["projects"][0]
        self.assertEqual(p["instagram"], "")
        self.assertTrue(any("instagram:" in g for d in p["book"] for g in d["gaps"]))

    def test_pakiet_pliki_i_cors(self):
        t = self.task("Opublikuj post „Start”")
        code, ans = self.post("/api/instagram/udostepnij", {"id": t["id"], "title": t["title"]})
        self.assertEqual(code, 200, ans)
        self.assertEqual((ans["handle"], ans["files"], ans["warning"]), ("shield.silent", 2, ""))
        self.assertRegex(ans["path"], r"^/udostepnij/[0-9a-f]{32}$")
        status, _, text = self.request("GET", "/api/instagram/udostepnij?t=" + ans["token"])
        self.assertFalse(json.loads(text)["fetched"])
        # pakiet bez sesji (zdalnie), CORS tylko dla instagram.com
        server.TOKEN = "haslo-do-testow"
        status, hdr, text = self.request("GET", ans["path"], headers=dict(REMOTE, **IG))
        self.assertEqual(status, 200)
        self.assertEqual(hdr.get("Access-Control-Allow-Origin"), "https://www.instagram.com")
        pkg = json.loads(text)
        self.assertEqual((pkg["caption"], [f["name"] for f in pkg["files"]]), ("Opis IG", ["grafika.png", "zdjecie-1.jpg"]))
        status, hdr, body = self.request("GET", "/udostepnij/" + pkg["files"][1]["url"], headers=dict(REMOTE, **IG))
        self.assertEqual((status, body, hdr["Content-Type"]), (200, "JPG22", "image/jpeg"))
        self.assertEqual(hdr.get("Access-Control-Allow-Origin"), "https://www.instagram.com")
        status, hdr, _ = self.request("GET", ans["path"], headers=dict(REMOTE, Origin="https://zla.example"))
        self.assertNotIn("Access-Control-Allow-Origin", hdr)
        status, hdr, _ = self.request("OPTIONS", ans["path"], headers=dict(REMOTE, **IG, **{
            "Access-Control-Request-Method": "GET", "Access-Control-Request-Private-Network": "true"}))
        self.assertEqual((status, hdr.get("Access-Control-Allow-Private-Network")), (204, "true"))
        status, hdr, _ = self.request("GET", "/udostepnij/" + pkg["files"][0]["url"] + "?pobierz=1", headers=REMOTE)
        self.assertTrue(hdr["Content-Disposition"].startswith("attachment"))
        self.assertEqual(self.request("GET", "/udostepnij/" + "0" * 32, headers=REMOTE)[0], 404)
        self.assertEqual(self.request("GET", "/udostepnij/" + ans["token"] + "/../../projekty.json", headers=REMOTE)[0], 404)
        # stan pobrania i tworzenie pakietu tylko z sesją
        self.assertEqual(self.request("GET", "/api/instagram/udostepnij?t=" + ans["token"], headers=REMOTE)[0], 401)
        self.assertEqual(self.request("POST", "/api/instagram/udostepnij", body={"id": t["id"], "title": t["title"]},
                                      headers=REMOTE)[0], 401)
        server.TOKEN = ""
        status, _, text = self.request("GET", "/api/instagram/udostepnij?t=" + ans["token"])
        self.assertTrue(json.loads(text)["fetched"])

    def test_bez_profilu_ostrzezenie_i_odmowy(self):
        self.karta("")
        t = self.task("Opublikuj post „Start”")
        code, ans = self.post("/api/instagram/udostepnij", {"id": t["id"], "title": t["title"]})
        self.assertEqual((code, ans["handle"]), (200, ""))
        self.assertIn("instagram:", ans["warning"])
        t2 = self.task("Opublikuj post „Inny”")
        self.assertEqual(self.post("/api/instagram/udostepnij", {"id": t2["id"], "title": t2["title"]})[0], 400)
        self.assertEqual(self.post("/api/instagram/udostepnij", {"id": t["id"], "title": "inny tytuł"})[0], 409)

    def test_zdjecia_w_danych_posta(self):
        pid = self.data()["projects"][0]["id"]
        status, _, text = self.request("GET", "/api/post?project=%s&date=%s" % (pid, self.DAY))
        self.assertEqual(json.loads(text)["photos"], ["zdjecie-1.jpg"])


class Panel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = read(PANEL).decode("utf-8")

    def test_przycisk_i_zapas(self):
        h = self.html
        self.assertIn("Udostępnij na Instagramie", h)
        self.assertIn("/api/instagram/udostepnij", h)
        self.assertIn("https://www.instagram.com/#is=", h)
        self.assertIn("Kopiuj opis", h)          # zapas bez rozszerzenia
        self.assertIn("Pobierz pliki", h)

    def test_podglady_platform(self):
        h = self.html
        for name in ("function pvPlats(", "function pvIg(", "function pvFb(", "function pvTt(", "function pvCut("):
            self.assertIn(name, h)
        self.assertIn("IG_MORE=125", h)
        for tok in ("--sp-bg", "--sp-ink", "--sp-ink-2", "--sp-line", "--sp-dot", "--sp-dot-on", "--sp-shade", "--sp-chip"):
            self.assertEqual(len(re.findall(re.escape(tok) + r":", h)), 3, tok)    # :root i oba bloki ciemne


def panel_parts(html, names):
    """Kod wskazanych stałych i funkcji z panel.html (od nagłówka do następnej definicji najwyższego poziomu)."""
    out = []
    for n in names:
        m = re.search(r"^(?:const %s\b|(?:async )?function %s\().*?(?=^(?:const |let |function |async function |/\*)|\Z)"
                      % (re.escape(n), re.escape(n)), html, re.M | re.S)
        assert m, n
        out.append(m.group(0))
    return "\n".join(out)


@unittest.skipUnless(CHROME and not os.environ.get("PANEL_TESTY_BEZ_RENDERU"),
                     "brak Chrome albo PANEL_TESTY_BEZ_RENDERU: test podglądów w przeglądarce pominięty")
class PodgladyWChrome(unittest.TestCase):
    """Funkcje podglądów z panel.html w Chrome bez okna: zakładki, ucięcie opisu, karuzela, profil z karty."""

    def test_zakladki_uciecie_i_uklad(self):
        html = read(PANEL).decode("utf-8")
        code = panel_parts(html, ["esc", "AVINK", "av", "IG_MORE", "pvPlats", "spCap", "pvCut", "spMedia", "SPI", "spIco",
                                  "spVid", "spSlides", "spWho", "pvIg", "pvFb", "pvTt"])
        long_text = "A" * 130 + " koniec"
        page = """<!doctype html><meta charset="utf-8"><body><pre id="w"></pre><script>
const ED={more:false,slide:0},D={publish:null};
const P=id=>id==='bez'?{id:id,name:'Bez profilu',ci:1,ini:'BP',instagram:''}:{id:id,name:'Shield & Silent',ci:0,ini:'SS',instagram:'shield.silent'};
const pShort=p=>p.name,projName=id=>id,postQ=(p,d)=>'project='+p+'&date='+d;
%s
const img={ok:true,image:true,photos:['zdjecie-1.jpg','zdjecie-2.jpg'],folder:'2026-11-20-start',sections:{Instagram:%s,Facebook:'FB'}};
const vid={ok:true,film:{at:1,name:'film.mp4'},photos:[],sections:{Instagram:'Pierwsza linia\\nDruga linia'}};
const c={pid:'ss',day:'2026-11-20'},r={};
r.plImg=pvPlats({channel:'instagram, tiktok, linkedin'},img).map(x=>x[0]);
r.plVid=pvPlats({channel:'reels, instagram, tiktok'},vid).map(x=>x[0]);
r.plTxt=pvPlats({channel:'instagram, facebook'},{ok:true,sections:{}}).map(x=>x[0]);
r.cutLong=pvCut(%s,IG_MORE,'więcej');
r.cutLine=pvCut('Pierwsza linia\\nDruga linia',IG_MORE,'więcej');
const ig=pvIg(c,img);r.igUser=ig.includes('<b>shield.silent</b>');r.igCnt=(ig.match(/sp-cnt">([^<]*)/)||[])[1];
r.igDots=(ig.match(/<i[ >]/g)||[]).length;r.igNote=ig.includes('sp-note');r.igRatio=ig.includes('sp-r11');
ED.slide=2;r.igLast=pvIg(c,img).includes('zdjecie-2.jpg');ED.slide=0;
r.igBez=pvIg({pid:'bez',day:c.day},img).includes('sp-note');
r.igVid=pvIg(c,vid).includes('sp-r45');
r.fb=pvFb(c,img).includes('+2');
r.tt=pvTt(c,vid).includes('@shield.silent');
ED.more=true;r.more=pvCut(%s,IG_MORE,'więcej').includes('koniec');
document.getElementById('w').textContent=JSON.stringify(r);
</script>""" % (code, json.dumps(long_text), json.dumps(long_text), json.dumps(long_text))
        with tempfile.TemporaryDirectory(prefix="panel-ig-pv-") as tmp:
            path = os.path.join(tmp, "podglad.html")
            with open(path, "w", encoding="utf-8") as f:
                f.write(page)
            out = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
                                  "--user-data-dir=" + os.path.join(tmp, "profil"), "--virtual-time-budget=3000",
                                  "--dump-dom", "file://" + path], capture_output=True, text=True, timeout=60)
        import html as H
        m = re.search(r'<pre id="w">(.*?)</pre>', out.stdout, re.S)
        self.assertTrue(m and m.group(1), out.stderr[-500:])
        r = json.loads(H.unescape(m.group(1)))
        self.assertEqual(r["plImg"], ["sp-ig"])                       # TikTok bez filmu nie, LinkedIn bez podglądu
        self.assertEqual(r["plVid"], ["sp-fb", "sp-ig", "sp-tt"])
        self.assertEqual(r["plTxt"], ["sp-fb"])                       # Instagram bez zdjęcia i filmu nie
        self.assertTrue(r["cutLong"].startswith("A" * 125 + "… "), r["cutLong"])
        self.assertIn("data-spmore", r["cutLong"])
        self.assertTrue(r["cutLine"].startswith("Pierwsza linia… "), r["cutLine"])
        self.assertEqual((r["igUser"], r["igCnt"], r["igDots"], r["igNote"], r["igRatio"]), (True, "1/3", 3, False, True))
        self.assertTrue(r["igLast"] and r["igBez"] and r["igVid"] and r["fb"] and r["tt"] and r["more"], r)


class Rozszerzenie(unittest.TestCase):
    def test_bez_klikania_udostepnij(self):
        js = read(os.path.join(EXT, "instagram.js")).decode("utf-8")
        self.assertEqual(len(re.findall(r"\.click\(\)", js)), 1)              # jedno miejsce kliknięć: safeClick
        self.assertIn("próba kliknięcia przycisku publikacji", js)
        man = json.loads(read(os.path.join(EXT, "manifest.json")))
        self.assertEqual(man["manifest_version"], 3)
        self.assertEqual(man["content_scripts"][0]["matches"], ["https://www.instagram.com/*"])
        self.assertNotIn("permissions", man)


class Atrapa(BaseHTTPRequestHandler):
    shares = None
    user = "shield.silent"

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
        if path == "/atrapa.html":
            return self._out(200, read(os.path.join(TESTY, "atrapa_instagram.html")), "text/html; charset=utf-8")
        if path.startswith("/ext/") and path[5:] in ("selektory.js", "instagram.js"):
            return self._out(200, read(os.path.join(EXT, path[5:])), "text/javascript; charset=utf-8")
        if path == "/api/v1/accounts/current_user/":
            return self._out(200, json.dumps({"user": {"username": self.user}}), "application/json")
        parts = path.split("/")
        if path.startswith("/udostepnij/") and len(parts) == 3:
            pkg = self.shares.package(parts[2])
            return self._out(200 if pkg else 404, json.dumps(pkg or {"ok": False, "error": "wygasł"}), "application/json")
        if path.startswith("/udostepnij/") and len(parts) == 4:
            hit = self.shares.file(parts[2], parts[3])
            if hit:
                return self._out(200, read(hit[0]), hit[1])
        return self._out(404, "", "text/plain")


@unittest.skipUnless(CHROME and not os.environ.get("PANEL_TESTY_BEZ_RENDERU"),
                     "brak Chrome albo PANEL_TESTY_BEZ_RENDERU: test rozszerzenia na atrapie pominięty")
class NaAtrapie(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="panel-ig-chrome-")
        Atrapa.shares = udostepnij.Shares()
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Atrapa)
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

    def run_page(self, handle, files, caption="Opis posta\nDruga linia #marka"):
        tok = Atrapa.shares.create("Post", caption, files, handle)
        url = "%s/atrapa.html#is=%s" % (self.base, urllib.parse.quote(self.base + "/udostepnij/" + tok, safe=""))
        out = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
                              "--user-data-dir=" + os.path.join(self.tmp, "profil"), "--virtual-time-budget=20000",
                              "--dump-dom", url], capture_output=True, text=True, timeout=90)
        m = re.search(r"<html([^>]*)>", out.stdout)
        self.assertTrue(m, out.stderr[-500:])
        return dict(re.findall(r'(data-[\w-]+)="([^"]*)"', m.group(1)))

    def test_zdjecia_i_opis_bez_publikacji(self):
        Atrapa.user = "shield.silent"
        attrs = self.run_page("shield.silent", self.files("grafika.png", "zdjecie-1.jpg"))
        self.assertEqual(attrs.get("data-panel-is"), "gotowe", attrs)
        self.assertEqual(attrs.get("data-pliki"), "grafika.png:22:image/png,zdjecie-1.jpg:26:image/jpeg")
        self.assertIn("Opis posta", attrs.get("data-opis", ""))
        self.assertIn("Druga linia #marka", attrs.get("data-opis", ""))
        self.assertNotIn("data-opublikowane", attrs)
        self.assertIn("Udostępnij", attrs.get("data-panel-is-text", ""))

    def test_film_przez_komunikat_ok(self):
        Atrapa.user = "shield.silent"
        attrs = self.run_page("shield.silent", self.files("film.mp4"))
        self.assertEqual(attrs.get("data-panel-is"), "gotowe", attrs)
        self.assertEqual(attrs.get("data-pliki"), "film.mp4:16:video/mp4")
        self.assertNotIn("data-opublikowane", attrs)

    def test_inne_konto_zatrzymuje(self):
        Atrapa.user = "prywatne"
        attrs = self.run_page("shield.silent", self.files("grafika.png"))
        self.assertEqual(attrs.get("data-panel-is"), "konto", attrs)
        self.assertIn("Zalogowany: @prywatne, a post jest dla @shield.silent", attrs.get("data-panel-is-text", ""))
        self.assertNotIn("data-pliki", attrs)


if __name__ == "__main__":
    unittest.main()
