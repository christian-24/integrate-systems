"""Grafiki do postów przez Codex: pliki wariantów (grafiki.py), rozmowa o grafice (tryb „zachowaj” i „nowa”, oczekująca
wersja, akceptacja, odrzucenie, iteracja), trasy /api/post/warianty, /api/post/grafika-codex, /api/post/wariant,
uruchomienie Codexa na atrapie, brak Codexa, brak logowania, logowanie kodem urządzenia."""
import datetime
import json
import os
import re
import shutil
import struct
import tempfile
import unittest

from test_serwer import Serwer
from wspolne import TESTY, server

import atrapa_codex
import grafiki

PANEL = os.path.join(os.path.dirname(TESTY), "panel.html")
PNG = atrapa_codex.PNG
JPG = b"\xff\xd8\xff\xe0" + b"0" * 20
SRC = atrapa_codex.png(40, 30)          # grafika posta 4:3


def write(path, body):
    with open(path, "wb") as f:
        f.write(body)


def read(path):
    with open(path, "rb") as f:
        return f.read()


def jpeg(w, h, orient=1):
    """Minimalny nagłówek JPEG: APP1 z obrotem EXIF i SOF0 o rozmiarze w×h (bez danych obrazu)."""
    tiff = b"MM\x00\x2a\x00\x00\x00\x08" + b"\x00\x01" + struct.pack(">HHIHH", 0x0112, 3, 1, orient, 0) + b"\x00" * 4
    app1 = b"Exif\x00\x00" + tiff
    sof = b"\x08" + struct.pack(">HH", h, w) + b"\x03" + b"\x01\x11\x00\x02\x11\x01\x03\x11\x01"
    return (b"\xff\xd8" + b"\xff\xe1" + struct.pack(">H", len(app1) + 2) + app1 +
            b"\xff\xc0" + struct.pack(">H", len(sof) + 2) + sof + b"\xff\xd9")


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

    def test_polecenie_zachowaj_zdjecie(self):
        p = grafiki.prompt_keep("wyostrz, nic nie zmieniaj", "grafika.png", 3, self.dir)
        self.assertNotIn("$imagegen", p)
        self.assertNotIn("imagegen", p)
        self.assertIn("Pillow", p)
        self.assertIn("UnsharpMask", p)
        self.assertIn("Niczego nie dodawaj", p)
        self.assertIn("NIE generuj", p)
        self.assertIn("wariant-3.png", p)
        self.assertIn("Nie kadruj", p)
        self.assertIn("grafika.png", p)
        self.assertIn("Przygotuj grafikę do posta", p)             # atrapa rozpoznaje zlecenie grafiki
        crop = grafiki.prompt_keep("Przytnij do 4:5", "grafika.png", 3, self.dir)
        self.assertNotIn("Nie kadruj", crop)
        self.assertIn("zmień kadr dokładnie tak", crop)
        self.assertTrue(grafiki.crop_asked("przytnij do 1:1"))
        self.assertTrue(grafiki.crop_asked("Wyprostuj horyzont"))
        self.assertFalse(grafiki.crop_asked("Wyostrz i zmniejsz poziom szumu"))

    def test_rozmiar_obrazu(self):
        write(os.path.join(self.dir, "a.png"), atrapa_codex.png(40, 30))
        write(os.path.join(self.dir, "a.jpg"), jpeg(40, 30))
        write(os.path.join(self.dir, "b.jpg"), jpeg(40, 30, orient=6))      # zdjęcie z telefonu obrócone w EXIF
        self.assertEqual(grafiki.image_size(os.path.join(self.dir, "a.png")), (40, 30))
        self.assertEqual(grafiki.image_size(os.path.join(self.dir, "a.jpg")), (40, 30))
        self.assertEqual(grafiki.image_size(os.path.join(self.dir, "b.jpg")), (30, 40))
        self.assertIsNone(grafiki.image_size(os.path.join(self.dir, "post.md")))
        self.assertTrue(grafiki.same_ratio((4000, 3000), (1600, 1200)))
        self.assertFalse(grafiki.same_ratio((4000, 3000), (1080, 1350)))

    def test_odpowiedz_bez_sciezek(self):
        self.assertEqual(grafiki.clean_reply("Wyostrzyłem zdjęcie. Zapisano /home/panel/x/wariant-3.png"),
                         "Wyostrzyłem zdjęcie.")
        for bad in ("Zapisałem /home/panel/posty/wariant-3.png.", "Gotowe: wariant-3.png", "Plik C:\\x\\y.png.",
                    "Uruchomiłem fix.py"):
            self.assertEqual(grafiki.clean_reply(bad), "", bad)

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
        write(os.path.join(self.post_dir, "grafika.png"), SRC)
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
        self.assertNotIn(self.tmp, text)                  # żadnych ścieżek serwera w odpowiedzi dla edytora
        return json.loads(text)

    def order(self, text="wyostrz, nic nie zmieniaj", mode=None, source=None):
        body = {"project": self.pid, "date": self.DAY, "polecenie": text}
        if mode:
            body["tryb"] = mode
        if source:
            body["zrodlo"] = source
        return self.post("/api/post/grafika-codex", body)

    def act(self, what, name):
        return self.post("/api/post/wariant", {"project": self.pid, "date": self.DAY, "name": name, "akcja": what})

    def last_call(self):
        return [c for c in self.calls() if "Przygotuj grafikę" in c["prompt"]][-1]

    def image_arg(self):
        return next(a for a in self.last_call()["argv"] if a.startswith("--image="))[len("--image="):]

    def test_zachowaj_zdjecie_domyslnie(self):
        self.use()
        st = self.state()
        self.assertEqual(st["tool"]["need"], "")
        self.assertEqual(st["chat"], {"items": [], "pending": None, "source": ""})
        code, ans = self.order()
        self.assertEqual(code, 200, ans)
        rec = self.wait(ans["id"])
        self.assertEqual((rec["state"], rec["kind"], rec["tool"], rec["variants"]), ("done", "grafika", "codex",
                                                                                      ["wariant-1.png"]))
        call = self.last_call()
        argv = call["argv"]
        self.assertEqual(argv[:2], ["exec", "--json"])
        self.assertIn("workspace-write", argv)
        self.assertEqual(argv[argv.index("-C") + 1], self.post_dir)
        self.assertEqual(self.image_arg(), os.path.join(self.post_dir, "grafika.png"))
        self.assertEqual(argv[-1], "-")
        self.assertEqual(os.path.realpath(call["cwd"]), os.path.realpath(self.post_dir))
        self.assertNotIn("OPENAI_API_KEY", call["env"])          # subskrypcja ChatGPT, bez klucza API
        self.assertNotIn("imagegen", call["prompt"])              # tryb „zachowaj”: bez generowania
        self.assertIn("Pillow", call["prompt"])
        self.assertIn("Niczego nie dodawaj", call["prompt"])
        self.assertIn("wyostrz, nic nie zmieniaj", call["prompt"])
        self.assertNotIn(self.tmp, rec["result"])                 # wynik w Agentach bez ścieżek
        chat = self.state()["chat"]
        self.assertEqual(chat["pending"]["name"], "wariant-1.png")
        self.assertEqual((chat["pending"]["w"], chat["pending"]["h"]), (40, 30))
        self.assertEqual(chat["source"], "grafika.png")
        item = chat["items"][-1]
        self.assertEqual((item["text"], item["mode"], item["state"]), ("wyostrz, nic nie zmieniaj", "zachowaj", "ok"))
        self.assertTrue(item["reply"].startswith(grafiki.DONE_REPLY), item["reply"])
        self.assertNotIn("/", item["reply"])
        self.assertNotIn("input", item)
        self.assertEqual(read(os.path.join(self.post_dir, "grafika.png")), SRC)     # nic nie nadpisane
        # zlecenie widać w Agentach
        self.assertTrue(any(r["id"] == ans["id"] and r["kind"] == "grafika" for r in self.data()["agents"]["runs"]))

    def test_iteracja_i_akceptacja(self):
        self.use()
        self.wait(self.order()[1]["id"])
        # kolejne polecenie poprawia ostatnią wersję; poprzednia wersja tej rozmowy znika
        code, ans = self.order("jeszcze trochę jaśniej")
        self.assertEqual(code, 200, ans)
        self.assertEqual(self.wait(ans["id"])["variants"], ["wariant-2.png"])
        self.assertEqual(self.image_arg(), os.path.join(self.post_dir, "wariant-1.png"))
        self.assertFalse(os.path.exists(os.path.join(self.post_dir, "wariant-1.png")))
        chat = self.state()["chat"]
        self.assertEqual(chat["pending"]["name"], "wariant-2.png")
        self.assertEqual([x["text"] for x in chat["items"]], ["wyostrz, nic nie zmieniaj", "jeszcze trochę jaśniej"])
        new = read(os.path.join(self.post_dir, "wariant-2.png"))
        self.assertEqual(self.act("akceptuj", "wariant-1.png")[0], 409)         # nieaktualna wersja
        code, ans = self.act("akceptuj", "wariant-2.png")
        self.assertEqual(code, 200, ans)
        self.assertEqual(read(os.path.join(self.post_dir, "grafika.png")), new)
        self.assertEqual(read(os.path.join(self.post_dir, ans["previous"])), SRC)  # poprzednia zostaje jako kopia
        chat = self.state()["chat"]
        self.assertIsNone(chat["pending"])
        self.assertEqual(chat["items"][-1]["action"], "akceptuj")
        self.assertEqual(self.act("akceptuj", "wariant-2.png")[0], 409)
        # po akceptacji następne polecenie bierze aktualną grafikę posta
        self.wait(self.order("popraw kontrast")[1]["id"])
        self.assertEqual(self.image_arg(), os.path.join(self.post_dir, "grafika.png"))

    def test_odrzucenie(self):
        self.use()
        self.wait(self.order()[1]["id"])
        code, ans = self.act("odrzuc", "wariant-1.png")
        self.assertEqual(code, 200, ans)
        self.assertFalse(os.path.exists(os.path.join(self.post_dir, "wariant-1.png")))
        self.assertEqual(read(os.path.join(self.post_dir, "grafika.png")), SRC)
        chat = self.state()["chat"]
        self.assertIsNone(chat["pending"])
        self.assertEqual(chat["items"][-1]["action"], "odrzuc")
        self.assertEqual(self.act("odrzuc", "wariant-1.png")[0], 409)
        self.wait(self.order("inaczej")[1]["id"])
        self.assertEqual(self.image_arg(), os.path.join(self.post_dir, "grafika.png"))

    def test_inne_proporcje_odrzucone(self):
        self.use()
        self.set_mode("grafika-proporcje")
        rec = self.wait(self.order()[1]["id"])
        self.assertEqual(rec["state"], "error")
        self.assertIn("inne proporcje", rec["error"])
        self.assertEqual(grafiki.variants(self.post_dir), [])
        chat = self.state()["chat"]
        self.assertIsNone(chat["pending"])
        self.assertEqual(chat["items"][-1]["state"], "error")
        self.assertIn("przytnij do 4:5", chat["items"][-1]["reply"])
        # prośba o kadr: inne proporcje są w porządku
        rec = self.wait(self.order("Przytnij do 4:5, nic nie dodawaj")[1]["id"])
        self.assertEqual(rec["state"], "done", rec)
        self.assertIsNotNone(self.state()["chat"]["pending"])

    def test_generowanie_w_trybie_zachowaj_odrzucone(self):
        self.use()
        self.set_mode("grafika-generuje")
        rec = self.wait(self.order()[1]["id"])
        self.assertEqual(rec["state"], "error")
        self.assertIn("wygenerował", rec["error"])
        self.assertEqual(grafiki.variants(self.post_dir), [])
        self.assertIsNone(self.state()["chat"]["pending"])
        # tryb „nowa”: generowanie jest celem
        rec = self.wait(self.order("nowa grafika z kawą na stole", mode="nowa")[1]["id"])
        self.assertEqual(rec["state"], "done", rec)
        self.assertIn("$imagegen", self.last_call()["prompt"])
        self.assertEqual(self.state()["chat"]["items"][-1]["mode"], "nowa")

    def test_obraz_z_katalogu_sesji_i_brak_obrazu(self):
        self.use()
        self.set_mode("grafika-sesja")
        code, ans = self.order(mode="nowa")
        rec = self.wait(ans["id"])
        self.assertEqual((rec["state"], rec["variants"]), ("done", ["wariant-1.png"]))
        shutil.rmtree(os.path.join(self.codex_home, "generated_images"))     # nowy wątek Codex: pusty katalog sesji
        self.assertEqual(self.act("odrzuc", "wariant-1.png")[0], 200)
        self.set_mode("grafika-pusta")
        rec = self.wait(self.order()[1]["id"])
        self.assertEqual(rec["state"], "error")
        self.assertIn("nie zapisał obrazu", rec["error"])

    def test_zdjecie_karuzeli_jako_zrodlo(self):
        self.use()
        rec = self.wait(self.order(source="zdjecie-1.jpg")[1]["id"])
        self.assertEqual(rec["state"], "done", rec)
        self.assertEqual(self.image_arg(), os.path.join(self.post_dir, "zdjecie-1.jpg"))
        self.assertEqual(self.state()["chat"]["source"], "zdjecie-1.jpg")
        code, ans = self.act("akceptuj", "wariant-1.png")
        self.assertEqual(code, 200, ans)
        self.assertEqual(ans["name"], "zdjecie-1.png")
        self.assertFalse(os.path.exists(os.path.join(self.post_dir, "zdjecie-1.jpg")))
        self.assertEqual(read(os.path.join(self.post_dir, ans["previous"])), JPG)
        self.assertEqual(read(os.path.join(self.post_dir, "grafika.png")), SRC)        # grafika bez zmian
        status, _, text = self.request("GET", "/api/post?project=%s&date=%s" % (self.pid, self.DAY))
        self.assertEqual(json.loads(text)["photos"], ["zdjecie-1.png"])

    def test_karuzela_z_wersji_i_stare_akcje(self):
        self.use()
        self.wait(self.order()[1]["id"])
        code, ans = self.act("karuzela", "wariant-1.png")
        self.assertEqual((code, ans["name"]), (200, "zdjecie-2.png"), ans)
        self.assertIsNone(self.state()["chat"]["pending"])
        write(os.path.join(self.post_dir, "wariant-5.png"), PNG)
        write(os.path.join(self.post_dir, "wariant-6.png"), PNG)
        self.assertEqual(self.act("grafika", "wariant-5.png")[0], 200)
        self.assertEqual(self.act("usun", "wariant-6.png")[0], 200)
        self.assertEqual(self.act("usun", "post.md")[0], 409)
        self.assertEqual(self.act("zmien", "wariant-5.png")[0], 400)
        self.assertTrue(os.path.exists(os.path.join(self.post_dir, "post.md")))

    def test_przerwane_polecenie(self):
        self.use()
        old = (datetime.datetime.now().astimezone() - datetime.timedelta(minutes=5)).isoformat(timespec="seconds")
        with open(os.path.join(self.post_dir, grafiki.CHAT), "w", encoding="utf-8") as f:
            json.dump({"items": [{"id": "nie-ma", "at": old, "text": "wyostrz", "mode": "zachowaj", "state": "run"}],
                       "pending": "", "source": ""}, f)
        item = self.state()["chat"]["items"][-1]
        self.assertEqual(item["state"], "error")
        self.assertIn("Przerwane", item["reply"])

    def test_bledne_zlecenia(self):
        self.use()
        self.assertEqual(self.order("x")[0], 400)
        self.assertEqual(self.order(mode="inny")[0], 400)
        self.assertEqual(self.post("/api/post/grafika-codex", {"project": self.pid, "date": "2026-01-01",
                                                               "polecenie": "rozjaśnij"})[0], 404)
        # zrodlo spoza obrazów posta: panel bierze grafikę posta
        self.wait(self.order(source="../KARTA.md")[1]["id"])
        self.assertEqual(self.image_arg(), os.path.join(self.post_dir, "grafika.png"))
        # post bez obrazu: „zachowaj” niemożliwe, „nowa” działa
        self.act("odrzuc", "wariant-1.png")
        for n in ("grafika.png", "zdjecie-1.jpg"):
            os.remove(os.path.join(self.post_dir, n))
        code, ans = self.order()
        self.assertEqual(code, 409, ans)
        self.assertIn("Zachowaj zdjęcie", ans["error"])
        code, ans = self.order("nowa grafika", mode="nowa")
        self.assertEqual(code, 200, ans)
        self.wait(ans["id"])
        self.assertFalse(any(a.startswith("--image=") for a in self.last_call()["argv"]))

    def test_brak_codexa(self):
        self.use(PANEL_CODEX=os.path.join(self.tmp, "brak-codex"))
        st = self.state()
        self.assertEqual(st["tool"]["need"], "install")
        code, ans = self.order()
        self.assertEqual((code, ans["need"]), (409, "install"))
        self.assertIn("nie jest zainstalowany", ans["error"])
        self.assertEqual(self.state()["chat"]["items"], [])

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
        self.assertNotIn("Grafika (Codex)</h3>", html)                     # jedna sekcja „Grafika”
        self.assertNotIn("Zleć Codexowi", html)
        for text in ("Zachowaj zdjęcie", "Nowa wersja", "Zaakceptuj", "Odrzuć", "Przed", "Po"):
            self.assertIn(text, html)
        for act in ('data-cxv="akceptuj"', 'data-cxv="odrzuc"', "cxVariant('karuzela')", "return cxSwap(c,d,L);"):
            self.assertIn(act, html)
        self.assertNotIn("run.activity", html[html.index("function cxFill(){"):])   # bez technicznych śladów Codexa


if __name__ == "__main__":
    unittest.main()
