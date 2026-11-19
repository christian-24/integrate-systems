"""Publikacja postów (dashboard/publikacja.py) na atrapie API Facebooka i LinkedIna, bez sieci."""
import datetime
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
import urllib.parse

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "standard"))
import projekt  # noqa: E402
import publikacja  # noqa: E402

NOW = datetime.datetime(2026, 11, 21, 9, 5)
KAMPANIA = """# Kampania: Stały rytm

- stan: w toku
- kanały: facebook, linkedin

## Grupa docelowa
Sprzedawcy mebli.

## Przekaz
Opis w 10 sekund.

## Harmonogram
- [ ] Opublikuj post „Start” | kto: ty | kanał: facebook, linkedin | kiedy: 2026-11-21

## Wyniki i wnioski
"""
POST = "# Start\n\n## Facebook\nTekst FB\n\n## LinkedIn\nTekst (LI) #1 @firma\n\n## Alt\nPlansza\n"


class Api:
    """Atrapa: zapisuje wywołania i odpowiada jak Graph API i LinkedIn."""

    def __init__(self):
        self.calls = []
        self.fail_li = False
        self.fail_fb = False

    def __call__(self, method, url, headers=None, body=None, timeout=120):
        self.calls.append((method, url, headers or {}, body))
        ok = lambda d, h=None: (200, h or {}, json.dumps(d).encode("utf-8"))
        if "oauth/access_token" in url:
            return ok({"access_token": "DLUGI"})
        if "/me/accounts" in url:
            return ok({"data": [{"id": "111", "name": "Opisarnia", "access_token": "TOKEN-STRONY",
                                 "instagram_business_account": {"id": "555", "username": "opisarnia"}}]})
        if url.endswith("/555/media"):
            return ok({"id": "c1"})
        if "/c1?" in url:
            return ok({"status_code": "FINISHED"})
        if url.endswith("/555/media_publish"):
            return ok({"id": "m1"})
        if "/m1?" in url:
            return ok({"permalink": "https://www.instagram.com/p/abc/"})
        if url.endswith("/111/photos"):
            if self.fail_fb:
                return 403, {}, json.dumps({"error": {"message": "brak uprawnień"}}).encode("utf-8")
            return ok({"id": "9", "post_id": "111_9"})
        if url.endswith("/v2/userinfo"):
            return ok({"sub": "abc", "name": "Właściciel"})
        if "images?action=initializeUpload" in url:
            return ok({"value": {"uploadUrl": "https://upload.example/img", "image": "urn:li:image:1"}})
        if url == "https://upload.example/img":
            return 201, {}, b""
        if url.endswith("/rest/posts"):
            if self.fail_li:
                return 403, {}, json.dumps({"message": "brak uprawnień"}).encode("utf-8")
            return 201, {"x-restli-id": "urn:li:share:7"}, b""
        raise AssertionError(url)


class Publikacja(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.folder = os.path.join(self.tmp, "projekt")
        os.makedirs(os.path.join(self.folder, "kampanie"))
        os.makedirs(os.path.join(self.folder, "posty", "2026-11-21-start"))
        with open(os.path.join(self.folder, "kampanie", "staly-rytm.md"), "w", encoding="utf-8") as f:
            f.write(KAMPANIA)
        with open(os.path.join(self.folder, "posty", "2026-11-21-start", "post.md"), "w", encoding="utf-8") as f:
            f.write(POST)
        with open(os.path.join(self.folder, "posty", "2026-11-21-start", "grafika.png"), "wb") as f:
            f.write(b"PNG")
        self.api = Api()
        self.notes = []
        self.pub = publikacja.Publisher(self.load, threading.Lock(), projekt, self.post_folder, self.post_info,
                                        lambda pf: os.path.join(pf, "grafika.png"), notify=self.notes.append,
                                        data_dir=os.path.join(self.tmp, "dane"), http_call=self.api, now=lambda: NOW)
        self.pub.sync = True

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def load(self, resolve=True):
        with open(os.path.join(self.folder, "kampanie", "staly-rytm.md"), encoding="utf-8") as f:
            _, tasks = projekt.parse_campaign(f.read(), "opis", "kampanie/staly-rytm.md")
        for t in tasks:
            t.setdefault("waitingFor", [])
        return {"tasks": tasks, "projects": [{"id": "inny", "name": "Inny projekt", "alias": None},
                                             {"id": "opis", "name": "Opisarnia (generator)", "alias": None}]}, {"opis": self.folder}

    def post_folder(self, pid, day):
        path = os.path.join(self.folder, "posty", day + "-start")
        return path if os.path.isdir(path) else None

    def post_info(self, folder):
        sections, name = {}, None
        with open(os.path.join(folder, "post.md"), encoding="utf-8") as f:
            text = f.read()
        for line in text.split("\n"):
            if line.startswith("## "):
                name = line[3:]
                sections[name] = ""
            elif name:
                sections[name] += line + "\n"
        return {"title": "Start", "sections": {k: v.strip() for k, v in sections.items()}, "image": True}

    def task(self):
        return self.load()[0]["tasks"][0]

    def connect(self):
        self.assertEqual(self.pub.connect_facebook({"appId": "123456", "appSecret": "ab" * 16, "token": "K" * 40})[0], 200)
        self.assertEqual(self.pub.connect_linkedin({"token": "L" * 40})[0], 200)

    def test_polaczenia_bez_tokenow_w_stanie(self):
        self.assertEqual(self.pub.connect_facebook({"appId": "x", "appSecret": "y", "token": "z"})[0], 400)
        self.connect()
        st = self.pub.status()
        self.assertEqual(st["facebook"]["pages"], [{"id": "111", "name": "Opisarnia", "project": "opis", "instagram": "opisarnia"}])
        self.assertTrue(st["linkedin"]["connected"])
        self.assertNotIn("TOKEN-STRONY", json.dumps(st))
        self.assertNotIn("L" * 40, json.dumps(st))
        mode = os.stat(os.path.join(self.tmp, "dane", "facebook.json")).st_mode & 0o777
        self.assertEqual(mode, 0o600)
        with open(os.path.join(self.tmp, "dane", "facebook.json"), encoding="utf-8") as f:
            self.assertNotIn("ab" * 16, f.read())                                   # sekret aplikacji nie zostaje

    def test_plan_i_publikacja(self):
        t = self.task()
        self.assertIn("Facebook nie jest połączony", self.pub.plan({"id": t["id"], "title": t["title"], "channels": ["facebook"],
                                                                     "at": "2026-11-21 09:00"})[1])
        self.connect()
        self.assertIn("LinkedIn publikujesz sam", self.pub.plan({"id": t["id"], "title": t["title"],
                                                               "channels": ["facebook", "linkedin"], "at": "2026-11-21 09:00"})[1])
        code, err = self.pub.plan({"id": t["id"], "title": t["title"], "channels": ["facebook"], "at": "2026-11-21 09:00"})
        self.assertEqual(code, 200, err)
        self.assertEqual(self.task()["detail"]["scheduled"], "2026-11-21 09:00; facebook")
        self.pub.tick()
        t = self.task()
        self.assertEqual(t["state"], "done")
        self.assertEqual(t["detail"]["link"], "https://www.facebook.com/111_9")
        self.assertFalse(t["detail"].get("scheduled"))
        self.assertEqual(self.notes, ["Opublikowano: Opublikuj post „Start” (facebook)"])
        self.assertEqual(publikacja.li_text("Tekst (LI) #1 @firma"), "Tekst \\(LI\\) \\#1 \\@firma")

    def test_blad_kanalu_i_ponowienie_bez_duplikatu(self):
        self.connect()
        publikacja.PUBLIC_URL, old = "https://panel.example", publikacja.PUBLIC_URL
        self.pub.jpeg = lambda png, out: shutil.copy(png, out) and out
        self.api.fail_fb = True
        t = self.task()
        try:
            self.pub.plan({"id": t["id"], "title": t["title"], "channels": ["instagram", "facebook"], "at": "2026-11-21 09:00"})
            self.pub.tick()
            t = self.task()
            self.assertEqual(t["state"], "todo")
            self.assertIn("brak uprawnień", t["detail"]["left"])
            self.assertIn("opublikowane już: instagram", t["detail"]["left"])
            self.assertTrue(self.notes[-1].startswith("Nie opublikowano"))
            self.api.fail_fb = False
            self.pub.plan({"id": t["id"], "title": t["title"], "channels": ["instagram", "facebook"], "now": True})
        finally:
            publikacja.PUBLIC_URL = old
        self.assertEqual(sum(1 for c in self.api.calls if c[1].endswith("/555/media_publish")), 1)   # Instagram raz
        self.assertEqual(self.task()["state"], "done")

    def test_instagram_z_publicznym_adresem(self):
        self.connect()
        t = self.task()
        old = publikacja.PUBLIC_URL
        publikacja.PUBLIC_URL = ""
        self.assertIn("PANEL_PUBLIC_URL", self.pub.plan({"id": t["id"], "title": t["title"], "channels": ["instagram"], "now": True})[1])
        publikacja.PUBLIC_URL = "https://panel.example"
        self.pub.jpeg = lambda png, out: shutil.copy(png, out) and out
        try:
            code, err = self.pub.plan({"id": t["id"], "title": t["title"], "channels": ["instagram"], "now": True})
        finally:
            publikacja.PUBLIC_URL = old
        self.assertEqual(code, 200, err)
        self.assertEqual(self.task()["detail"]["link"], "https://www.instagram.com/p/abc/")
        body = next(c[3] for c in self.api.calls if c[1].endswith("/555/media")).decode("utf-8")
        url = urllib.parse.parse_qs(body)["image_url"][0]
        self.assertTrue(url.startswith("https://panel.example/media/"))
        token, name = url.split("/")[-2:]
        self.assertEqual(name, ".instagram.jpg")
        self.assertTrue(self.pub.media_file(token).endswith(".instagram.jpg"))
        self.assertIsNone(self.pub.media_file("0" * 32))

    def test_strony_bez_uprawnien_instagrama(self):
        api = self.api

        def bez_ig(method, url, headers=None, body=None, timeout=120):
            if "/me/accounts" in url and "instagram_business_account" in urllib.parse.unquote(url):
                return 400, {}, json.dumps({"error": {"message": "(#100) Missing permissions"}}).encode("utf-8")
            return api(method, url, headers, body, timeout)
        self.pub.http = bez_ig
        code, err, extra = self.pub.connect_facebook({"appId": "123456", "appSecret": "ab" * 16, "token": "K" * 40})
        self.assertEqual(code, 200, err)
        self.assertEqual(extra["pages"][0]["project"], "opis")

    def test_plan_w_przyszlosci_czeka(self):
        self.connect()
        t = self.task()
        self.pub.plan({"id": t["id"], "title": t["title"], "channels": ["facebook"], "at": "2026-11-21 18:00"})
        self.pub.tick()
        self.assertEqual(self.task()["state"], "todo")
        self.assertFalse(any(c[1].endswith("/photos") for c in self.api.calls))
        self.assertEqual(self.pub.cancel({"id": t["id"], "title": t["title"]})[0], 200)
        self.assertFalse(self.task()["detail"].get("scheduled"))


if __name__ == "__main__":
    unittest.main()
