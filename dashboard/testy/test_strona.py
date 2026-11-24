"""Podgląd strony WWW (dashboard/strona.py): pola karty, budowanie z atrapą (bez Node.js), serwowanie /podglad/
(klucz, sesja, ścieżki poza folderem, MIME), uwaga → zadanie agenta → scalenie i nowy podgląd, koncepcja, zakładka
tylko przy `strona:`, zrzut-strony.py (pomijany bez Playwright)."""
import importlib.util
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

from test_serwer import REMOTE, Serwer
from wspolne import TESTY, TODAY, server

GIT = shutil.which("git")
IDENT = ["-c", "user.name=test", "-c", "user.email=test@example.invalid", "-c", "commit.gpgsign=false"]
BUILD = """import os, shutil, sys
os.makedirs(os.path.join("dist", "assets"), exist_ok=True)
shutil.copy("index.html", os.path.join("dist", "index.html"))
with open(os.path.join("dist", "assets", "app.js"), "w") as f:
    f.write("console.log(1)")
with open(os.path.join("dist", "assets", "styl.css"), "w") as f:
    f.write("body{color:red}")
secret = sys.argv[1] if len(sys.argv) > 1 else ""
if secret and not os.path.lexists(os.path.join("dist", "sekret.txt")):
    os.symlink(secret, os.path.join("dist", "sekret.txt"))
print("zbudowano")
"""
PAGE = "<!doctype html><html><head><title>Strona</title></head><body><h1 id=\"tytul\">Witaj</h1></body></html>\n"


class Strona(Serwer):
    card_lines = "- strona: site\n- strona build: python3 zbuduj.py {secret}\n"

    def setUp(self):
        super().setUp()
        self.secret = os.path.join(self.tmp, "tajne.txt")
        with open(self.secret, "w", encoding="utf-8") as f:
            f.write("TAJNE")
        self.set_card(self.card_lines.format(secret=self.secret))
        site = os.path.join(self.folder, "site")
        os.makedirs(os.path.join(self.folder, "docs"), exist_ok=True)
        os.makedirs(site)
        for path, text in ((os.path.join(site, "index.html"), PAGE), (os.path.join(site, "zbuduj.py"), BUILD),
                           (os.path.join(self.folder, "docs", "koncepcja.md"), "# Koncepcja\n\nJedna strona.\n")):
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
        self.pid = self.data()["projects"][0]["id"]
        self.site = self.manager.site

    def set_card(self, lines):
        path = os.path.join(self.folder, "KARTA.md")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        head, _, rest = text.partition("\n")
        with open(path, "w", encoding="utf-8") as f:
            f.write(head + "\n\n" + lines + rest)
        server.data_invalidate()

    def project(self):
        return next(p for p in self.data()["projects"] if p["id"] == self.pid)

    def info(self):
        status, _, text = self.request("GET", "/api/strona?project=" + self.pid)
        self.assertEqual(status, 200, text)
        return json.loads(text)

    def note(self, title):
        return next(n for n in self.info()["notes"] if n["title"] == title)

    def wait_note(self, title):
        self.wait_for(lambda: self.note(title)["state"] in ("zrobione", "nie wyszło"), timeout=30)
        return self.note(title)


class Karta(Strona):
    def test_pola_strony(self):
        site = self.project()["site"]
        self.assertEqual((site["dir"], site["out"], site["customBuild"]), ("site", "dist", True))
        self.assertTrue(site["build"].startswith("python3 zbuduj.py"))

    def test_domyslne_vite_i_bledne_pola(self):
        path = os.path.join(self.folder, "KARTA.md")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        with open(path, "w", encoding="utf-8") as f:
            f.write(text.replace(self.card_lines.format(secret=self.secret), "- strona: site/\n"))
        server.data_invalidate()
        site = self.project()["site"]
        self.assertEqual(site, {"dir": "site", "build": "npm ci && npm run build -- --base=./", "out": "dist",
                                "customBuild": False})
        with open(path, "w", encoding="utf-8") as f:
            f.write(text.replace(self.card_lines.format(secret=self.secret), "- strona: ../obcy\n- strona wynik: /etc\n"))
        server.data_invalidate()
        p = self.project()
        self.assertIsNone(p["site"])
        gaps = next(d for d in p["docs"] if d["key"] == "karta")["gaps"]
        self.assertTrue(any(g.startswith("strona: ../obcy") for g in gaps), gaps)

    def test_bez_pola_brak_funkcji_i_zakladki(self):
        path = os.path.join(self.folder, "KARTA.md")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        with open(path, "w", encoding="utf-8") as f:
            f.write(text.replace(self.card_lines.format(secret=self.secret), ""))
        server.data_invalidate()
        self.assertIsNone(self.project()["site"])
        status, _, text = self.request("GET", "/api/strona?project=" + self.pid)
        self.assertEqual(status, 409)
        status, body = self.post("/api/strona/uwaga", {"project": self.pid, "text": "Zmień"})
        self.assertEqual(status, 409)
        with open(os.path.join(os.path.dirname(TESTY), "panel.html"), encoding="utf-8") as f:
            html = f.read()
        self.assertIn("const ptabsOf=p=>p&&p.site?", html)      # zakładka Strona tylko przy polu strona:
        self.assertIn("if(p&&tab==='strona'&&!p.site)tab='plan';", html)
        self.assertNotIn("PTABS.filter(", html)                  # nawigacja projektu idzie przez ptabsOf


class Budowanie(Strona):
    def test_buduje_i_kopiuje_bez_dowiazan(self):
        build = self.site.build_now(self.pid)
        self.assertEqual(build["state"], "ok", build)
        out = os.path.join(self.runs, "strona", self.pid, "wynik")
        self.assertTrue(os.path.isfile(os.path.join(out, "index.html")))
        self.assertTrue(os.path.isfile(os.path.join(out, "assets", "app.js")))
        self.assertFalse(os.path.lexists(os.path.join(out, "sekret.txt")))      # dowiązanie poza wynik pominięte
        self.assertIn("zbudowano", build["log"])
        info = self.info()
        self.assertTrue(info["url"].startswith("/podglad/%s/" % self.pid))
        self.assertIn("docs/koncepcja.md", info["docs"])

    def test_blad_budowania_w_jednym_zdaniu(self):
        path = os.path.join(self.folder, "KARTA.md")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        with open(path, "w", encoding="utf-8") as f:
            f.write(text.replace("python3 zbuduj.py", "python3 -c \"import sys; print('blad kompilacji'); sys.exit(3)\" #"))
        server.data_invalidate()
        build = self.site.build_now(self.pid)
        self.assertEqual(build["state"], "error")
        self.assertIn("kod 3", build["error"])
        self.assertIn("blad kompilacji", build["error"])
        self.assertEqual(self.info()["url"], "")

    def test_przycisk_zbuduj(self):
        status, body = self.post("/api/strona/zbuduj", {"project": self.pid})
        self.assertEqual(status, 200, body)
        self.wait_for(lambda: self.info()["build"].get("state") == "ok")


class Serwowanie(Strona):
    def setUp(self):
        super().setUp()
        self.assertEqual(self.site.build_now(self.pid)["state"], "ok")
        self.url = self.info()["url"]

    def test_mime_i_skrypt_wskaz(self):
        status, headers, text = self.request("GET", self.url)
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "text/html; charset=utf-8")
        self.assertIn("sandbox allow-scripts", headers["Content-Security-Policy"])
        self.assertEqual(headers["Referrer-Policy"], "no-referrer")
        self.assertIn("pw:'wybrano'", text)                       # skrypt trybu Wskaż w <head>
        self.assertIn("<h1 id=\"tytul\">Witaj</h1>", text)
        for rel, ctype in (("assets/app.js", "text/javascript; charset=utf-8"), ("assets/styl.css", "text/css; charset=utf-8")):
            status, headers, _ = self.request("GET", self.url + rel)
            self.assertEqual((status, headers["Content-Type"]), (200, ctype), rel)
        status, headers, _ = self.request("GET", self.url.rstrip("/"))
        self.assertEqual((status, headers["Location"]), (303, self.url))

    def test_sciezki_poza_folderem(self):
        for rel in ("../stan.json", "%2e%2e/stan.json", "assets/..%2f..%2fstan.json", "sekret.txt", "..%5cstan.json",
                    "nie-ma.html"):
            status, _, text = self.request("GET", self.url + rel)
            self.assertEqual(status, 404, rel)
            self.assertNotIn("TAJNE", text)
        bad = "/podglad/%s/%s/" % (self.pid, "0" * 24)
        self.assertEqual(self.request("GET", bad)[0], 404)       # zły klucz (z tego komputera): nie ma pliku

    def test_zdalnie_klucz_albo_sesja(self):
        server.TOKEN = "haslo-do-testow"
        self.assertEqual(self.request("GET", self.url, headers=REMOTE)[0], 200)       # klucz w ścieżce: ramka bez ciasteczka
        bad = "/podglad/%s/%s/" % (self.pid, "0" * 24)
        self.assertEqual(self.request("GET", bad, headers=REMOTE)[0], 401)
        self.assertEqual(self.request("GET", "/podglad/%s/" % self.pid, headers=REMOTE)[0], 401)
        self.assertEqual(self.request("GET", "/api/strona?project=" + self.pid, headers=REMOTE)[0], 401)
        cookie = self.login("haslo-do-testow")[1]["Set-Cookie"].split(";")[0]
        status, _, text = self.request("GET", "/api/strona?project=" + self.pid, headers=dict(REMOTE, Cookie=cookie))
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(text)["url"], self.url)


class Uwagi(Strona):
    def send(self, **extra):
        body = dict({"project": self.pid, "text": "Większy nagłówek | proszę", "view": "telefon", "page": "/",
                     "selector": "#tytul", "elementText": "Witaj"}, **extra)
        status, answer = self.post("/api/strona/uwaga", body)
        self.assertEqual(status, 200, answer)
        return answer

    def test_uwaga_zadanie_uruchomienie_i_podglad(self):
        self.set_mode("strona")
        answer = self.send()
        title = answer["note"]["title"]
        self.assertEqual(title, "Strona: Większy nagłówek proszę")
        self.assertTrue(answer["runId"])
        note = self.wait_note(title)
        self.assertEqual(note["state"], "zrobione", note)
        with open(os.path.join(self.folder, "ZADANIA.md"), encoding="utf-8") as f:
            text = f.read()
        self.assertIn("- [x] %s | kto: claude | gdzie: mac | kiedy: %s" % (title, TODAY), text)
        self.assertIn("Element: #tytul, tekst „Witaj”", text)
        self.assertIn("widok telefon (390 px)", text)
        call = self.calls()[-1]
        self.assertIn("Folder strony: %s. " % os.path.join(self.folder, "site"), call["prompt"])
        self.assertIn("zrzut-strony.py", call["prompt"])
        self.assertIn(" 390 ", call["prompt"])
        self.assertIn("nie pushuj", call["prompt"])
        tools = call["argv"][call["argv"].index("--allowedTools") + 1]
        self.assertNotIn("Bash(npm", tools)            # budowanie z karty bez npm: bez reguł npm i bez ogólnego Bash
        self.assertNotIn("zbuduj.py", tools)
        self.assertIn("panel nie dał do niego uprawnienia", call["prompt"])
        self.assertIn("zrzut-strony.py:*)", tools)
        status, _, page = self.request("GET", self.info()["url"])
        self.assertIn("Zmiana agenta", page)                     # podgląd zbudowany po pracy agenta

    def test_pusta_uwaga(self):
        status, body = self.post("/api/strona/uwaga", {"project": self.pid, "text": "  "})
        self.assertEqual(status, 400)

    def test_blad_agenta_nie_wyszlo(self):
        self.set_mode("login")
        title = self.send()["note"]["title"]
        note = self.wait_note(title)
        self.assertEqual(note["state"], "nie wyszło")
        self.assertIn("logowania", note["error"])


@unittest.skipUnless(GIT, "brak polecenia git")
class UwagiGit(Strona):
    def setUp(self):
        super().setUp()
        self.git("init", "-q")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "start")

    def git(self, *args):
        return subprocess.run(["git"] + IDENT + list(args), cwd=self.folder, check=True, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, encoding="utf-8").stdout.strip()

    def test_galaz_scalona_i_podglad(self):
        self.set_mode("strona")
        status, answer = self.post("/api/strona/uwaga", {"project": self.pid, "text": "Dodaj akapit", "view": "komputer"})
        title = answer["note"]["title"]
        note = self.wait_note(title)
        self.assertEqual(note["state"], "zrobione", note)
        with open(os.path.join(self.folder, "site", "index.html"), encoding="utf-8") as f:
            self.assertIn("Zmiana agenta", f.read())             # gałąź agenta scalona do bieżącej gałęzi
        self.assertIn("Scalenie agent/", self.git("log", "-1", "--format=%s"))
        exclude = os.path.join(self.folder, ".git", "info", "exclude")
        with open(exclude, encoding="utf-8") as f:
            lines = f.read().split("\n")
        for want in ("/.agent/", ".zrzuty/", "node_modules/", "/site/dist/"):
            self.assertIn(want, lines)
        status, _, page = self.request("GET", self.info()["url"])
        self.assertIn("Zmiana agenta", page)

    def test_bez_zmian_strony(self):
        self.set_mode("strona-bez-zmian")
        status, answer = self.post("/api/strona/uwaga", {"project": self.pid, "text": "Nic"})
        note = self.wait_note(answer["note"]["title"])
        self.assertEqual((note["state"], note["error"]), ("nie wyszło", "Agent nie zmienił plików strony."))


class Koncepcja(Strona):
    def test_sciezka_poza_projektem_i_brak_pliku(self):
        for path in ("../tajne.txt", "nie-ma.md", ""):
            status, body = self.post("/api/strona/koncepcja", {"project": self.pid, "path": path})
            self.assertEqual(status, 400, path)

    def test_zadanie_wedlug_koncepcji(self):
        self.set_mode("strona")
        status, answer = self.post("/api/strona/koncepcja", {"project": self.pid, "path": "docs/koncepcja.md",
                                                             "text": "Ciemne tło"})
        self.assertEqual(status, 200, answer)
        title = answer["note"]["title"]
        self.assertEqual(title, "Strona według koncepcji: docs/koncepcja.md")
        self.assertEqual(self.wait_note(title)["state"], "zrobione")
        with open(os.path.join(self.folder, "ZADANIA.md"), encoding="utf-8") as f:
            text = f.read()
        self.assertIn("materiał: docs/koncepcja.md", text)
        self.assertIn("Uwagi właściciela: „Ciemne tło”", text)
        self.assertIn("Zrób zrzuty ekranu", self.calls()[-1]["prompt"])


def png_size(path):
    with open(path, "rb") as f:
        head = f.read(24)
    assert head[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", head[16:24])


@unittest.skipUnless(importlib.util.find_spec("playwright"), "brak pakietu playwright")
class Zrzut(unittest.TestCase):
    def test_zrzut_folderu(self):
        tmp = tempfile.mkdtemp(prefix="zrzut-")
        try:
            with open(os.path.join(tmp, "index.html"), "w", encoding="utf-8") as f:
                f.write(PAGE)
            out = os.path.join(tmp, "z", "telefon.png")
            script = os.path.join(os.path.dirname(os.path.dirname(TESTY)), "uruchom", "serwer", "zrzut-strony.py")
            p = subprocess.run([sys.executable, script, tmp, "390", out], stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, encoding="utf-8", timeout=120)
            if p.returncode != 0 and "Executable doesn't exist" in p.stdout:
                self.skipTest("brak przeglądarki Playwright")
            self.assertEqual(p.returncode, 0, p.stdout)
            self.assertEqual(png_size(out)[0], 390)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
