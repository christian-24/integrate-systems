"""Edytor posta: zakładki platform, jedna akcja zależna od zakładki, edycja opisu i grafiki, cofnięcie „Opublikowane”.

Trasy serwera na projekcie tymczasowym; logika zakładek i akcji z panel.html w Chrome bez okna (pomijana bez Chrome
albo z PANEL_TESTY_BEZ_RENDERU)."""
import json
import os
import re
import subprocess
import tempfile
import unittest
import zlib

from test_instagram import CHROME, PANEL, panel_parts, read
from test_serwer import Serwer

DAY = "2026-11-20"


def png(w=4, h=3):
    """Najmniejszy poprawny PNG o podanych wymiarach."""
    def chunk(kind, body):
        return len(body).to_bytes(4, "big") + kind + body + zlib.crc32(kind + body).to_bytes(4, "big")
    raw = b"".join(b"\x00" + b"\x00\x00\x00" * w for _ in range(h))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", w.to_bytes(4, "big") + h.to_bytes(4, "big") + b"\x08\x02\x00\x00\x00")
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


class Trasy(Serwer):
    def setUp(self):
        super().setUp()
        os.makedirs(os.path.join(self.folder, "kampanie"), exist_ok=True)
        with open(os.path.join(self.folder, "kampanie", "rytm.md"), "w", encoding="utf-8") as f:
            f.write("# Kampania: Rytm\n\n- stan: w toku\n- kanały: facebook\n\n## Grupa docelowa\nx\n\n## Przekaz\nx\n\n"
                    "## Harmonogram\n- [ ] Opublikuj post „Start” | kto: ty | kanał: facebook, linkedin | kiedy: %s\n\n"
                    "## Wyniki i wnioski\n" % DAY)
        self.post_dir = os.path.join(self.folder, "posty", DAY + "-start")
        os.makedirs(self.post_dir)
        with open(os.path.join(self.post_dir, "post.md"), "w", encoding="utf-8") as f:
            f.write("# Start\n\n## Facebook\nOpis FB\ndruga linia\n\n## Alt\nOpis grafiki\n")
        with open(os.path.join(self.post_dir, "grafika.png"), "wb") as f:
            f.write(png())
        self.pid = self.data()["projects"][0]["id"]

    def task(self):
        return next(t for t in self.data()["tasks"] if t["title"] == "Opublikuj post „Start”")

    def post_md(self):
        with open(os.path.join(self.post_dir, "post.md"), encoding="utf-8") as f:
            return f.read()

    def info(self):
        return json.loads(self.request("GET", "/api/post?project=%s&date=%s" % (self.pid, DAY))[2])

    def test_cofniecie_opublikowane(self):
        t = self.task()
        self.assertEqual(self.post("/api/task/state", {"id": t["id"], "title": t["title"], "state": "done"})[0], 200)
        self.assertEqual(self.task()["state"], "done")
        self.assertEqual(self.post("/api/task/state", {"id": t["id"], "title": t["title"], "state": "todo"})[0], 200)
        t = self.task()
        self.assertEqual(t["state"], "todo")
        with open(os.path.join(self.folder, "kampanie", "rytm.md"), encoding="utf-8") as f:
            self.assertIn("- [ ] Opublikuj post „Start”", f.read())
        # zamknięcie z panelu znika z listy zamkniętych po ponownym otwarciu
        closed = self.data()["activity"]["closed"]
        self.assertFalse(any(c.get("title") == t["title"] for c in closed), closed)

    def test_opis_zmiana_i_nowa_sekcja(self):
        code, ans = self.post("/api/post/tekst", {"project": self.pid, "date": DAY, "section": "Facebook",
                                                  "text": "Nowy opis FB\r\n#meble", "old": "Opis FB\ndruga linia"})
        self.assertEqual(code, 200, ans)
        self.assertEqual(self.info()["sections"]["Facebook"], "Nowy opis FB\n#meble")
        self.assertEqual(self.info()["sections"]["Alt"], "Opis grafiki")
        code, ans = self.post("/api/post/tekst", {"project": self.pid, "date": DAY, "section": "LinkedIn",
                                                  "text": "Opis LI", "old": ""})
        self.assertEqual(code, 200, ans)
        s = self.info()["sections"]
        self.assertEqual((s["LinkedIn"], s["Facebook"], s["Alt"]), ("Opis LI", "Nowy opis FB\n#meble", "Opis grafiki"))
        self.assertTrue(self.post_md().startswith("# Start\n"))
        self.assertEqual(self.post_md().count("## LinkedIn"), 1)

    def test_opis_odmowy(self):
        base = {"project": self.pid, "date": DAY}
        # plik zmienił się od chwili otwarcia edytora: nic nie zapisane
        before = self.post_md()
        code, ans = self.post("/api/post/tekst", dict(base, section="Facebook", text="x", old="inny tekst"))
        self.assertEqual(code, 409, ans)
        self.assertEqual(self.post_md(), before)
        self.assertEqual(self.post("/api/post/tekst", dict(base, section="Dowolna", text="x"))[0], 400)
        self.assertEqual(self.post("/api/post/tekst", dict(base, section="Facebook", text="a\n## Wstrzyk\nb"))[0], 400)
        self.assertEqual(self.post("/api/post/tekst", dict(base, section="Facebook", text="x" * 5001))[0], 400)
        self.assertEqual(self.post("/api/post/tekst", dict(base, date="2026-01-01", section="Facebook", text="x"))[0], 404)
        self.assertEqual(self.post_md(), before)

    def test_grafika_wymiana(self):
        old = read(os.path.join(self.post_dir, "grafika.png"))
        new = png(8, 6)
        status, _, text = self.request("POST", "/api/post/grafika?project=%s&date=%s" % (self.pid, DAY), raw=new,
                                       ctype="image/png")
        self.assertEqual(status, 200, text)
        self.assertEqual(read(os.path.join(self.post_dir, "grafika.png")), new)
        self.assertEqual(read(os.path.join(self.post_dir, ".grafika-poprzednia.png")), old)
        self.assertTrue(self.info()["imageAt"] > 0)
        # treść niezgodna z typem, zły typ: grafika bez zmian, bez plików tymczasowych
        status, _, _ = self.request("POST", "/api/post/grafika?project=%s&date=%s" % (self.pid, DAY), raw=b"nie png",
                                    ctype="image/png")
        self.assertEqual(status, 400)
        status, _, _ = self.request("POST", "/api/post/grafika?project=%s&date=%s" % (self.pid, DAY), raw=new,
                                    ctype="image/gif")
        self.assertEqual(status, 400)
        self.assertEqual(read(os.path.join(self.post_dir, "grafika.png")), new)
        self.assertFalse([n for n in os.listdir(self.post_dir) if "wysylka" in n])


class Panel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = read(PANEL).decode("utf-8")

    def test_jedna_akcja_i_menu(self):
        h = self.html
        for lab in ("'na Instagramie'", "'na Facebooku'", "'na LinkedInie'", "'na TikToku'"):
            self.assertIn(lab, h)
        edacts = panel_parts(h, ["edActs"])
        self.assertEqual(edacts.count('class="btn sm"'), 1)            # jedna akcja w nagłówku, reszta w „⋯”
        menu = panel_parts(h, ["edMenu"])
        for n in ("Oznacz jako opublikowane", "Oznacz jako nieopublikowane", "Kopiuj opis", "Pobierz pliki", "Szczegóły zadania"):
            self.assertIn(n, menu)
        self.assertIn("sayUndo(st==='done'?'Oznaczono jako opublikowane.'", h)
        self.assertNotIn("data-edtab=\"grafika\"", h)
        self.assertNotIn("['tekst','Tekst']", h)
        self.assertNotIn("function igBtn(", h)                      # karta w Marketingu bez drugiego przycisku
        self.assertIn('id="ed-gfx-codex"', h)                         # miejsce na „Grafika (Codex)”
        self.assertIn("Opis skopiowany", h)
        self.assertIn("— wklej i dodaj.", h)
        card = panel_parts(h, ["mkAct"])
        self.assertEqual(len(re.findall(r"return b\('", card)), 3)


@unittest.skipUnless(CHROME and not os.environ.get("PANEL_TESTY_BEZ_RENDERU"),
                     "brak Chrome albo PANEL_TESTY_BEZ_RENDERU: test zakładek w przeglądarce pominięty")
class ZakladkiWChrome(unittest.TestCase):
    def test_zakladki_i_akcja(self):
        code = panel_parts(read(PANEL).decode("utf-8"),
                           ["esc", "CHAL", "chList", "SPN", "pvPlats", "SPCHAIN", "spCap", "chanOk", "igCan",
                            "edApi", "edPrimary", "edSecOf"])
        page = """<!doctype html><meta charset="utf-8"><body><pre id="w"></pre><script>
let LIVE=true;const IGS={},A={},PUBN={facebook:'Facebook',linkedin:'LinkedIn',reels:'Reels',instagram:'Instagram'};
const D={publish:{fb:{pages:[{project:'api',instagram:'tak'}]},li:{connected:false}}};
const P=id=>({id:id,instagram:id==='ext'?'marka':''});
%s
const img={ok:true,image:true,photos:[],sections:{Facebook:'FB'}},vid={ok:true,film:{at:1},sections:{}},scen={ok:true,scenario:true,sections:{}};
const T=(ch,p,extra)=>Object.assign({id:'x',kind:'publikacja',state:'todo',channel:ch,project:p||'bez'},extra||{});
const k=L=>L.map(x=>x[0]),r={};
r.opis=k(pvPlats(T('facebook, linkedin'),img));
r.wszystkie=k(pvPlats(T('LinkedIn, reels, TikTok, Instagram'),vid));
r.scen=k(pvPlats(T('reels, tiktok, youtube'),scen));
r.reelsBezFilmu=k(pvPlats(T('reels, tiktok'),img));
r.sekcje=k(pvPlats(T(''),{ok:true,image:true,sections:{LinkedIn:'a',Instagram:'b'}}));
r.skroty=k(pvPlats(T('FB, IG'),img));
r.nieprzygotowany=k(pvPlats(T('instagram, tiktok'),{ok:false}));
r.inne=k(pvPlats(T('newsletter'),img));
r.apiFb=edApi(T('facebook','api'),'sp-fb',img);r.apiIg=edApi(T('instagram','api'),'sp-ig',img);
r.extIg=edApi(T('instagram','ext'),'sp-ig',img);r.apiLi=edApi(T('linkedin','api'),'sp-li',img);
r.akcja=['sp-ig','sp-fb','sp-li','sp-tt','sp-gen'].map(x=>edPrimary(T('instagram'),img,x).n);
r.zgoda=edPrimary(T('facebook','bez',{needsYou:'zgoda'}),img,'sp-fb').n;
r.gotowe=edPrimary(T('facebook','bez',{state:'done'}),img,'sp-fb');
r.sekcjaIg=edSecOf(img,'sp-ig');r.capLi=spCap(img,'sp-li');
document.getElementById('w').textContent=JSON.stringify(r);
</script>""" % code
        with tempfile.TemporaryDirectory(prefix="panel-ed-") as tmp:
            path = os.path.join(tmp, "zakladki.html")
            with open(path, "w", encoding="utf-8") as f:
                f.write(page)
            out = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
                                  "--user-data-dir=" + os.path.join(tmp, "profil"), "--virtual-time-budget=3000",
                                  "--dump-dom", "file://" + path], capture_output=True, text=True, timeout=60)
        import html as H
        m = re.search(r'<pre id="w">(.*?)</pre>', out.stdout, re.S)
        self.assertTrue(m and m.group(1), out.stderr[-500:])
        r = json.loads(H.unescape(m.group(1)))
        self.assertEqual(r["opis"], ["sp-fb", "sp-li"])                   # Opisarnia: Facebook i LinkedIn
        self.assertEqual(r["wszystkie"], ["sp-ig", "sp-fb", "sp-li", "sp-tt"])
        self.assertEqual(r["scen"], ["sp-fb", "sp-tt"])                   # film w nagrywaniu liczy się jako film
        self.assertEqual(r["reelsBezFilmu"], ["sp-gen"])
        self.assertEqual(r["sekcje"], ["sp-ig", "sp-li"])
        self.assertEqual(r["skroty"], ["sp-ig", "sp-fb"])
        self.assertEqual(r["nieprzygotowany"], ["sp-ig", "sp-tt"])
        self.assertEqual(r["inne"], ["sp-gen"])
        self.assertEqual((r["apiFb"], r["apiIg"], r["extIg"], r["apiLi"]), (["facebook"], ["instagram"], [], []))
        self.assertEqual(r["akcja"], ["Udostępnij na Instagramie", "Udostępnij na Facebooku", "Udostępnij na LinkedInie",
                                      "Udostępnij na TikToku", "Kopiuj opis i pobierz pliki"])
        self.assertEqual((r["zgoda"], r["gotowe"]), ("Zatwierdź", None))
        self.assertEqual((r["sekcjaIg"], r["capLi"]), (["Instagram", "Facebook"], "FB"))


if __name__ == "__main__":
    unittest.main()
