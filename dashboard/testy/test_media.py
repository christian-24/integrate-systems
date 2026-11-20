"""Widok Media: lista zdjęć i filmów z kart (posty/, media/, studio/), plik z Range, wgrywanie, ochrona ścieżek."""
import json
import os
import urllib.parse

from test_serwer import Serwer
from wspolne import server


class Media(Serwer):
    def setUp(self):
        super().setUp()
        self.pid = self.data()["projects"][0]["id"]
        for rel, body in (("posty/2026-11-20-film-a/film.mp4", b"0123456789"), ("posty/2026-11-20-film-a/grafika.png", b"PNG"),
                          ("posty/2026-11-20-film-a/.film-blad.png", b"x"), ("posty/2026-11-20-film-a/post.md", b"# t"),
                          ("studio/plansze/tlo.jpg", b"JPG"), ("media/.ukryty/a.png", b"x")):
            path = os.path.join(self.folder, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(body)

    def items(self):
        status, _, text = self.request("GET", "/api/media")
        self.assertEqual(status, 200)
        return json.loads(text)["items"]

    def test_lista(self):
        got = sorted((i["source"], i["path"], i["kind"], i.get("day", "")) for i in self.items())
        self.assertEqual(got, [("posty", "posty/2026-11-20-film-a/film.mp4", "video", "2026-11-20"),
                               ("posty", "posty/2026-11-20-film-a/grafika.png", "image", "2026-11-20"),
                               ("studio", "studio/plansze/tlo.jpg", "image", "")])

    def plik(self, rel, **kw):
        q = urllib.parse.urlencode({"project": self.pid, "path": rel})
        return self.request("GET", "/api/media/plik?" + q, **kw)

    def test_plik_range_i_ochrona(self):
        status, hdr, body = self.plik("posty/2026-11-20-film-a/film.mp4", headers={"Range": "bytes=2-5"})
        self.assertEqual((status, body, hdr.get("Content-Range")), (206, "2345", "bytes 2-5/10"))
        self.assertEqual(self.plik("posty/2026-11-20-film-a/grafika.png")[0], 200)
        for bad in ("../KARTA.md", "posty/../KARTA.md", "/etc/passwd", "KARTA.md", "posty/2026-11-20-film-a/post.md",
                    "posty/2026-11-20-film-a/.film-blad.png", "media/.ukryty/a.png"):
            self.assertEqual(self.plik(bad)[0], 404, bad)

    def test_wgrywanie(self):
        q = urllib.parse.urlencode({"project": self.pid, "name": "Zdjęcie komody (1).jpg"})
        status, _, text = self.request("POST", "/api/media/wgraj?" + q, raw=b"JPEGDATA", ctype="image/jpeg")
        self.assertEqual(status, 200, text)
        rel = json.loads(text)["path"]
        self.assertTrue(rel.startswith("media/") and rel.endswith("-Zdjęcie-komody-1.jpg"), rel)
        self.assertIn(rel, [i["path"] for i in self.items() if i["source"] == "media"])
        status, _, text = self.request("POST", "/api/media/wgraj?" + q, raw=b"JPEGDATA", ctype="image/jpeg")
        self.assertTrue(json.loads(text)["path"].endswith("-2.jpg"))                  # bez nadpisywania
        bad = urllib.parse.urlencode({"project": self.pid, "name": "skrypt.sh"})
        self.assertEqual(self.request("POST", "/api/media/wgraj?" + bad, raw=b"x", ctype="text/plain")[0], 400)
        nop = urllib.parse.urlencode({"project": "nie-ma", "name": "a.jpg"})
        self.assertEqual(self.request("POST", "/api/media/wgraj?" + nop, raw=b"x", ctype="image/jpeg")[0], 400)
        self.assertEqual(server.media_file(self.pid, "media/../KARTA.md"), None)
