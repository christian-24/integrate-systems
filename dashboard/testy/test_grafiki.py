"""Grafiki do postów przez Codex: pliki wariantów (grafiki.py), trasy /api/post/warianty, /api/post/grafika-codex,
/api/post/wariant, uruchomienie Codexa na atrapie, brak Codexa, brak logowania, logowanie kodem urządzenia."""
import os
import re
import shutil
import tempfile
import unittest

from test_serwer import Serwer
from wspolne import TESTY, server

import atrapa_codex
import grafiki

PANEL = os.path.join(os.path.dirname(TESTY), "panel.html")
PNG = atrapa_codex.PNG
JPG = b"\xff\xd8\xff\xe0" + b"0" * 20


def write(path, body):
    with open(path, "wb") as f:
        f.write(body)


def read(path):
    with open(path, "rb") as f:
        return f.read()


class Pliki(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="panel-grafiki-")
        for n, body in (("grafika.png", b"STARA" + PNG), ("grafika.svg", b"<svg/>"), ("zdjecie-1.jpg", JPG),
                        ("wariant-2.png", PNG), ("wariant-10.png", PNG), ("post.md", b"# P\n"), ("inne.png", PNG)):
            write(os.path.join(self.dir, n), body)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_lista_i_numer(self):
        self.assertEqual(grafiki.variants(self.dir), ["wariant-2.png", "wariant-10.png"])
        self.assertEqual(grafiki.inputs(self.dir), ["grafika.png", "zdjecie-1.jpg", "wariant-2.png", "wariant-10.png"])
        self.assertEqual(grafiki.next_number(self.dir), 11)
        p = grafiki.prompt("rozjaśnij, format 4:5", ["grafika.png"], 11, self.dir)
        self.assertIn("$imagegen", p)
        self.assertIn("wariant-11.png", p)
        self.assertIn("rozjaśnij, format 4:5", p)
        self.assertIn("grafika.png", p)
        self.assertIn("Bez zdjęć wejściowych", grafiki.prompt("nowa", [], 1, self.dir))

    def test_uzyj_jako_grafika_zostawia_kopie(self):
        code, err, extra = grafiki.use_as_graphic(self.dir, "wariant-2.png")
        self.assertEqual(code, 200, err)
        self.assertEqual(read(os.path.join(self.dir, "grafika.png")), PNG)
        self.assertFalse(os.path.exists(os.path.join(self.dir, "wariant-2.png")))
        self.assertFalse(os.path.exists(os.path.join(self.dir, "grafika.svg")))
        self.assertRegex(extra["previous"], r"^grafika-poprzednia-\d{8}-\d{6}\.png$")
        self.assertEqual(read(os.path.join(self.dir, extra["previous"])), b"STARA" + PNG)
        self.assertTrue(os.path.exists(os.path.join(self.dir, extra["previous"][:-4] + ".svg")))
        self.assertIn(extra["previous"], grafiki.inputs(self.dir))       # poprzednią można dać Codexowi
        # druga zamiana w tej samej sekundzie: kopia pod inną nazwą
        code, _, extra2 = grafiki.use_as_graphic(self.dir, "wariant-10.png")
        self.assertEqual(code, 200)
        self.assertNotEqual(extra2["previous"], extra["previous"])

    def test_karuzela_usun_i_zle_nazwy(self):
        code, _, extra = grafiki.add_to_carousel(self.dir, "wariant-2.png")
        self.assertEqual((code, extra["name"]), (200, "zdjecie-2.png"))
        self.assertTrue(os.path.exists(os.path.join(self.dir, "zdjecie-2.png")))
        self.assertEqual(grafiki.remove(self.dir, "wariant-10.png")[0], 200)
        self.assertEqual(grafiki.variants(self.dir), [])
        for bad in ("../post.md", "grafika.png", "wariant-1.png", "wariant-2.png/..", ""):
            self.assertEqual(grafiki.remove(self.dir, bad)[0], 409, bad)
            self.assertEqual(grafiki.use_as_graphic(self.dir, bad)[0], 409, bad)
        self.assertTrue(os.path.exists(os.path.join(self.dir, "post.md")))

    def test_zbieranie(self):
        write(os.path.join(self.dir, "wariant-11.png"), b"to nie jest obraz")
        write(os.path.join(self.dir, "wariant-12.png"), PNG)
        self.assertEqual(grafiki.collect(self.dir, 11, 0), ["wariant-12.png"])
        self.assertFalse(os.path.exists(os.path.join(self.dir, "wariant-11.png")))
        # Codex nie skopiował: obraz z katalogu sesji jako kolejny wariant
        session = os.path.join(self.dir, ".sesja")
        os.makedirs(session)
        write(os.path.join(session, "exec-1.png"), PNG)
        write(os.path.join(session, "notatka.txt"), b"x")
        self.assertEqual(grafiki.collect(self.dir, 13, 0, session), ["wariant-13.png"])
        self.assertEqual(grafiki.collect(self.dir, 14, 0, os.path.join(self.dir, "brak")), [])


class Trasy(Serwer):
    DAY = "2026-11-20"

    def setUp(self):
        super().setUp()
        self.post_dir = os.path.join(self.folder, "posty", self.DAY + "-start")
        os.makedirs(self.post_dir)
        write(os.path.join(self.post_dir, "grafika.png"), b"STARA" + PNG)
        write(os.path.join(self.post_dir, "zdjecie-1.jpg"), JPG)
        write(os.path.join(self.post_dir, "post.md"), "# Start\n\n## Instagram\nOpis\n".encode("utf-8"))
        self.pid = self.data()["projects"][0]["id"]
        self.codex_home = os.path.join(self.tmp, "codex-home")

    def use(self, **extra):
        extra.setdefault("PANEL_CODEX_HOME", self.codex_home)
        extra.setdefault("CODEX_HOME", self.codex_home)
        m = self.new_manager(**extra)
        server._agents = m
        self.manager = m
        m.refresh_tools(force=True, wait=True)
        return m

    def state(self):
        status, _, text = self.request("GET", "/api/post/warianty?project=%s&date=%s" % (self.pid, self.DAY))
        self.assertEqual(status, 200, text)
        return __import__("json").loads(text)

    def order(self, text="rozjaśnij, tło w warsztacie, format 4:5", names=None):
        return self.post("/api/post/grafika-codex", {"project": self.pid, "date": self.DAY, "polecenie": text,
                                                     "zdjecia": names or []})

    def test_zlecenie_wariant_i_obrazy_wejsciowe(self):
        self.use()
        st = self.state()
        self.assertEqual(st["tool"]["need"], "")
        self.assertEqual([x["name"] for x in st["inputs"]], ["grafika.png", "zdjecie-1.jpg"])
        code, ans = self.order(names=["grafika.png", "zdjecie-1.jpg"])
        self.assertEqual(code, 200, ans)
        rec = self.wait(ans["id"])
        self.assertEqual((rec["state"], rec["kind"], rec["tool"], rec["variants"]), ("done", "grafika", "codex", ["wariant-1.png"]))
        call = [c for c in self.calls() if "Przygotuj grafikę" in c["prompt"]][-1]
        argv = call["argv"]
        self.assertEqual(argv[:2], ["exec", "--json"])
        self.assertIn("workspace-write", argv)
        self.assertEqual(argv[argv.index("-C") + 1], self.post_dir)
        self.assertIn("--image=%s,%s" % (os.path.join(self.post_dir, "grafika.png"),
                                         os.path.join(self.post_dir, "zdjecie-1.jpg")), argv)
        self.assertEqual(argv[-1], "-")
        self.assertEqual(os.path.realpath(call["cwd"]), os.path.realpath(self.post_dir))
        self.assertNotIn("OPENAI_API_KEY", call["env"])          # subskrypcja ChatGPT, bez klucza API
        self.assertIn("rozjaśnij, tło w warsztacie, format 4:5", call["prompt"])
        st = self.state()
        self.assertEqual([x["name"] for x in st["variants"]], ["wariant-1.png"])
        self.assertEqual((st["runs"][0]["state"], st["runs"][0]["variants"]), ("done", ["wariant-1.png"]))
        self.assertEqual(read(os.path.join(self.post_dir, "grafika.png")), b"STARA" + PNG)   # nic nie nadpisane
        # kolejne zlecenie: następny numer, bez nadpisania
        code, ans = self.order("druga wersja, bardziej ciepłe światło")
        self.assertEqual(self.wait(ans["id"])["variants"], ["wariant-2.png"])
        # zlecenie widać w Agentach
        self.assertTrue(any(r["id"] == ans["id"] and r["kind"] == "grafika" for r in self.data()["agents"]["runs"]))

    def test_bledne_zlecenia(self):
        self.use()
        self.assertEqual(self.order("x")[0], 400)
        code, ans = self.order(names=["../KARTA.md"])
        self.assertEqual(code, 409, ans)
        self.assertEqual(self.order(names=["post.md"])[0], 409)
        self.assertEqual(self.post("/api/post/grafika-codex", {"project": self.pid, "date": "2026-01-01",
                                                               "polecenie": "rozjaśnij"})[0], 404)
        self.assertEqual(self.order(names="grafika.png")[0], 400)

    def test_obraz_z_katalogu_sesji_i_brak_obrazu(self):
        self.use()
        self.set_mode("grafika-sesja")
        code, ans = self.order()
        rec = self.wait(ans["id"])
        self.assertEqual((rec["state"], rec["variants"]), ("done", ["wariant-1.png"]))
        self.assertEqual(read(os.path.join(self.post_dir, "wariant-1.png")), PNG)
        shutil.rmtree(os.path.join(self.codex_home, "generated_images"))     # nowy wątek Codex: pusty katalog sesji
        self.set_mode("grafika-pusta")
        code, ans = self.order()
        rec = self.wait(ans["id"])
        self.assertEqual(rec["state"], "error")
        self.assertIn("nie zapisał żadnego obrazu", rec["error"])

    def test_uzycie_karuzela_usuwanie(self):
        self.use()
        for n in (1, 2, 3):
            write(os.path.join(self.post_dir, "wariant-%d.png" % n), PNG)
        act = lambda name, what: self.post("/api/post/wariant", {"project": self.pid, "date": self.DAY,
                                                                  "name": name, "akcja": what})
        code, ans = act("wariant-1.png", "grafika")
        self.assertEqual(code, 200, ans)
        self.assertEqual(read(os.path.join(self.post_dir, "grafika.png")), PNG)
        self.assertEqual(read(os.path.join(self.post_dir, ans["previous"])), b"STARA" + PNG)
        code, ans = act("wariant-2.png", "karuzela")
        self.assertEqual((code, ans["name"]), (200, "zdjecie-2.png"))
        status, _, text = self.request("GET", "/api/post?project=%s&date=%s" % (self.pid, self.DAY))
        self.assertIn("zdjecie-2.png", __import__("json").loads(text)["photos"])
        self.assertEqual(act("wariant-3.png", "usun")[0], 200)
        self.assertEqual(self.state()["variants"], [])
        self.assertEqual(act("wariant-3.png", "usun")[0], 409)
        self.assertEqual(act("post.md", "usun")[0], 409)
        self.assertEqual(act("wariant-3.png", "zmien")[0], 400)
        self.assertTrue(os.path.exists(os.path.join(self.post_dir, "post.md")))

    def test_brak_codexa(self):
        self.use(PANEL_CODEX=os.path.join(self.tmp, "brak-codex"))
        st = self.state()
        self.assertEqual(st["tool"]["need"], "install")
        code, ans = self.order()
        self.assertEqual((code, ans["need"]), (409, "install"))
        self.assertIn("nie jest zainstalowany", ans["error"])

    def test_codex_niezalogowany(self):
        self.set_mode("niezalogowany")
        self.use()
        st = self.state()
        self.assertEqual(st["tool"]["need"], "login")
        code, ans = self.order()
        self.assertEqual((code, ans["need"]), (409, "login"))
        self.assertEqual(self.calls(), [])

    def test_wylaczone(self):
        self.use(PANEL_GRAFIKA="wylaczone")
        self.assertEqual(self.state()["tool"]["need"], "off")
        self.assertEqual(self.order()[1]["need"], "off")

    def test_logowanie_kodem_urzadzenia(self):
        self.use(PANEL_LOGIN_WEB="1")
        code, ans = self.post("/api/agent/login", {"tool": "codex"})
        self.assertEqual(code, 200, ans)
        self.assertEqual((ans["url"], ans["code"]), ("https://auth.openai.com/codex/device", "ABCD-1234"))

    def test_panel_sekcja_w_edytorze(self):
        with open(PANEL, encoding="utf-8") as f:
            html = f.read()
        self.assertEqual(len(re.findall(r"\bcxFill\(\);", html)), 1)        # jedno wywołanie w edFill
        self.assertIn("function cxFill(){", html)
        self.assertIn("grafika:'Grafika (Codex)'", html)
        for route in ("/api/post/warianty?", "/api/post/grafika-codex", "/api/post/wariant'"):
            self.assertIn(route, html)


if __name__ == "__main__":
    unittest.main()
