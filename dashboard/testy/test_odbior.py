"""Strona „Odbiór pracy” (AGENCI.md, „Odbiór pracy”): wersje wyniku po uruchomieniu, /api/odbior, plik wersji,
poprawka ze znacznikami, odbiór całości i części wariantów, klucz zmiany:."""
import http.client
import json
import os
import shutil
import subprocess
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.parse import quote

from wspolne import Baza, agents, projekt, server

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64
EXTRA = """- [~] Wizytówka | kto: claude | wymaga: odbiór
  cel: wizytówka firmy
  wynik: przód wizytowki/przod.png, tył wizytowki/tyl.png; opis w wizytowki/opis.md
"""


class Odbior(Baza):
    def setUp(self):
        super().setUp()
        with open(os.path.join(self.folder, "ZADANIA.md"), encoding="utf-8") as f:
            text = f.read()
        with open(os.path.join(self.folder, "ZADANIA.md"), "w", encoding="utf-8") as f:
            f.write(text.replace("\n## Do rozplanowania", EXTRA + "\n## Do rozplanowania"))
        os.makedirs(os.path.join(self.folder, "wizytowki"))
        for name, blob in (("przod.png", PNG + b"p"), ("tyl.png", PNG + b"t"), ("opis.md", "# Opis\n".encode()),
                           ("inny.png", PNG)):
            with open(os.path.join(self.folder, "wizytowki", name), "wb") as f:
                f.write(blob)
        self.httpd = None

    def tearDown(self):
        for m in self.managers:
            for r in list(m._runs.values()):
                if r["state"] in agents.LIVE:
                    m.stop(r["id"])
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()
            server.Handler.log_message = self._log
        super().tearDown()

    def text(self):
        with open(os.path.join(self.folder, "ZADANIA.md"), encoding="utf-8") as f:
            return f.read()

    def http(self, method, path, body=None, headers=None):
        if not self.httpd:
            self._log = server.Handler.log_message
            server.Handler.log_message = lambda *args: None
            self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
            threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        conn = http.client.HTTPConnection("127.0.0.1", self.httpd.server_address[1], timeout=15)
        h = dict(headers or {})
        if body is not None:
            h["Content-Type"] = "application/json"
            body = json.dumps(body).encode("utf-8")
        conn.request(method, path, body=body, headers=h)
        resp = conn.getresponse()
        return resp.status, resp.read(), dict(resp.getheaders())

    def review(self, title="Wizytówka"):
        status, raw, _ = self.http("GET", "/api/odbior?id=" + quote(self.task(title)["id"]))
        return status, json.loads(raw.decode("utf-8"))

    def run_done(self, title="Wizytówka"):
        t = self.task(title)
        if t["state"] != "todo":
            projekt.update_task(self.folder, t["file"], t["line"], t["title"], {"state": "todo", "needsYou": ""})
        code, err, extra = self.run_task(title)
        self.assertEqual(code, 200, err)
        return self.wait(extra["id"])

    # ---------- wersje ----------
    def test_wersja_po_uruchomieniu_bez_nadpisywania(self):
        self.set_mode("zostaw")
        rec = self.run_done()
        self.assertEqual(rec["state"], "done")
        key = ("Wizytówka", self.task("Wizytówka"))
        saved = self.manager.versions(key[1]["project"], key[1]["file"], key[0])
        self.assertEqual([m["n"] for m in saved], [1])
        meta = saved[0]
        self.assertEqual(meta["runId"], rec["id"])
        self.assertEqual([(f["path"], f["kind"]) for f in meta["files"]],
                         [("wizytowki/przod.png", "image"), ("wizytowki/tyl.png", "image"), ("wizytowki/opis.md", "text")])
        self.assertTrue(meta["result"].startswith("przód wizytowki/przod.png"))
        # druga praca: nowa wersja, kopia pierwszej zostaje
        with open(os.path.join(self.folder, "wizytowki", "przod.png"), "wb") as f:
            f.write(PNG + b"nowy")
        self.run_done()
        saved = self.manager.versions(key[1]["project"], key[1]["file"], key[0])
        self.assertEqual([m["n"] for m in saved], [1, 2])
        tid = self.task("Wizytówka")["id"]
        self.assertEqual(self.manager.review_file(tid, 1, "wizytowki/przod.png")[1], PNG + b"p")
        self.assertEqual(self.manager.review_file(tid, 2, "wizytowki/przod.png")[1], PNG + b"nowy")
        status, body = self.review()
        self.assertEqual(status, 200)
        self.assertEqual([(v["n"], v["saved"]) for v in body["versions"]], [(1, True), (2, True)])
        self.assertEqual(body["run"]["state"], "done")
        self.assertNotIn("copy", body["versions"][0]["files"][0])

    def test_poprawka_i_zmiany_w_wersji(self):
        t = self.task("Wizytówka")
        projekt.set_detail(self.folder, t["file"], t["line"], t["title"], "poprawka", "większe logo",
                           pins=[{"file": "wizytowki/przod.png", "x": 34, "y": 60, "note": "tu logo"}])
        projekt.set_detail(self.folder, t["file"], t["line"], t["title"], "zmiany", ["logo większe", "znacznik 1: zrobione"])
        self.set_mode("zostaw")
        self.run_done()
        meta = self.manager.versions(t["project"], t["file"], t["title"])[0]
        self.assertEqual(meta["changes"], ["logo większe", "znacznik 1: zrobione"])
        self.assertEqual(meta["fixes"][0]["text"], "większe logo")
        self.assertEqual(meta["fixes"][0]["pins"][0]["note"], "tu logo")
        self.run_done()                     # zmiany: nie odnowione przez agenta -> pusta lista w nowej wersji
        self.assertEqual(self.manager.versions(t["project"], t["file"], t["title"])[1]["changes"], [])

    @unittest.skipUnless(shutil.which("git"), "brak polecenia git")
    def test_wersja_z_galezi_agenta(self):
        for args in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "start"]):
            subprocess.run(["git", "-c", "user.name=test", "-c", "user.email=test@example.invalid"] + args,
                           cwd=self.folder, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.set_mode("plik")
        rec = self.wait(self.run_task("Zadanie A")[2]["id"])
        self.assertTrue(rec["branch"].startswith("agent/"))
        self.assertFalse(os.path.exists(os.path.join(self.folder, "notatki", "analiza.md")))   # plik tylko na gałęzi
        t = self.task("Zadanie A")
        meta = self.manager.versions(t["project"], t["file"], t["title"])[0]
        self.assertEqual([(f["path"], f["kind"]) for f in meta["files"]], [("notatki/analiza.md", "text")])
        status, raw, _ = self.http("GET", "/api/odbior/plik?id=%s&v=1&path=%s" % (quote(t["id"]), quote("notatki/analiza.md")))
        self.assertEqual(status, 200)
        self.assertTrue(raw)
        # bez zapisanych wersji (stare zadanie): wersja bieżąca czyta plik z gałęzi ostatniego uruchomienia
        shutil.rmtree(self.manager._versions_dir(t["project"], t["file"], t["title"]))
        v = self.review("Zadanie A")[1]["versions"]
        self.assertEqual([(x["n"], x["saved"]) for x in v], [(1, False)])
        self.assertEqual(self.http("GET", v[0]["files"][0]["url"])[:2], (200, raw))

    def test_limit_wersji(self):
        t = self.task("Wizytówka")
        rec = {"id": "r", "project": t["project"], "file": t["file"], "title": t["title"], "fix": ""}
        for _ in range(agents.VERSIONS_KEEP + 2):
            self.manager._save_version(rec)
        saved = self.manager.versions(t["project"], t["file"], t["title"])
        self.assertEqual(len(saved), agents.VERSIONS_KEEP)
        self.assertEqual((saved[0]["n"], saved[-1]["n"]), (3, agents.VERSIONS_KEEP + 2))
        self.assertEqual(len(os.listdir(self.manager._versions_dir(t["project"], t["file"], t["title"]))),
                         agents.VERSIONS_KEEP)

    def test_plik_wiekszy_pominiety(self):
        t = self.task("Wizytówka")
        with open(os.path.join(self.folder, "wizytowki", "tyl.png"), "wb") as f:
            f.truncate(agents.VERSION_FILE_MAX + 1)
        rec = {"id": "r", "project": t["project"], "file": t["file"], "title": t["title"], "fix": ""}
        meta = self.manager._save_version(rec)
        tyl = next(f for f in meta["files"] if f["path"] == "wizytowki/tyl.png")
        self.assertIn("skipped", tyl)
        self.assertNotIn("copy", tyl)

    # ---------- /api/odbior ----------
    def test_wersja_biezaca_bez_zapisu(self):
        status, body = self.review()
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertEqual((body["task"]["title"], body["task"]["projectName"], body["task"]["needsYou"]),
                         ("Wizytówka", "Projekt testowy", "odbiór"))
        self.assertEqual(body["task"]["goal"], "wizytówka firmy")
        self.assertEqual(len(body["versions"]), 1)
        v = body["versions"][0]
        self.assertEqual((v["n"], v["saved"]), (1, False))
        self.assertEqual([(f["name"], f["kind"]) for f in v["files"]],
                         [("przod.png", "image"), ("tyl.png", "image"), ("opis.md", "text")])
        self.assertIsNone(body["run"])
        self.assertEqual(body["accepted"], [])
        status, raw, head = self.http("GET", v["files"][0]["url"])
        self.assertEqual((status, raw, head["Content-Type"]), (200, PNG + b"p", "image/png"))
        self.assertEqual(head["X-Content-Type-Options"], "nosniff")
        self.assertEqual(head["Cache-Control"], "no-store")
        status, raw, head = self.http("GET", v["files"][0]["url"], headers={"Range": "bytes=0-7"})
        self.assertEqual((status, raw, head["Content-Range"]), (206, PNG[:8], "bytes 0-7/%d" % (len(PNG) + 1)))
        self.assertEqual(self.http("GET", "/api/odbior?id=" + quote(self.task("Wizytówka")["project"] + "|ZADANIA.md|999"))[0],
                         404)

    def test_plik_tylko_z_wersji(self):
        tid = quote(self.task("Wizytówka")["id"])
        for path in ("wizytowki/inny.png", "../projekt-testowy/wizytowki/przod.png", "KARTA.md", "ZADANIA.md",
                     "/etc/passwd", "wizytowki/przod.svg"):
            status, _, _ = self.http("GET", "/api/odbior/plik?id=%s&v=1&path=%s" % (tid, quote(path)))
            self.assertEqual(status, 404, path)
        self.assertEqual(self.http("GET", "/api/odbior/plik?id=%s&v=2&path=%s" % (tid, quote("wizytowki/przod.png")))[0], 404)
        status, raw, head = self.http("GET", "/api/odbior/plik?id=%s&v=1&path=%s" % (tid, quote("wizytowki/opis.md")))
        self.assertEqual((status, head["Content-Type"]), (200, "text/plain; charset=utf-8"))
        # wersja zapisana: plik spoza listy wersji odrzucony, nawet gdy jest w folderze
        t = self.task("Wizytówka")
        self.manager._save_version({"id": "r", "project": t["project"], "file": t["file"], "title": t["title"]})
        self.assertEqual(self.http("GET", "/api/odbior/plik?id=%s&v=1&path=%s" % (tid, quote("wizytowki/inny.png")))[0], 404)
        self.assertEqual(self.http("GET", "/api/odbior/plik?id=%s&v=1&path=%s" % (tid, quote("wizytowki/tyl.png")))[0], 200)

    # ---------- popraw ----------
    def test_popraw_ze_znacznikami(self):
        self.set_mode("wolno")
        t = self.task("Wizytówka")
        pins = [{"file": "wizytowki/przod.png", "x": 34, "y": 60.5, "note": "Logo za małe"},
                {"file": "film/zapowiedz.mp4", "t": 12, "note": "Za szybko"}]
        status, raw, _ = self.http("POST", "/api/odbior/popraw", {"id": t["id"], "title": t["title"],
                                                                  "text": "Popraw logo", "pins": pins})
        body = json.loads(raw.decode("utf-8"))
        self.assertEqual(status, 200, body)
        self.assertEqual(body["status"]["text"], "Uruchomiono: Wizytówka")
        text = self.text()
        self.assertIn("  poprawka: Popraw logo\n"
                      "  - znacznik 1 (wizytowki/przod.png, 34% od lewej, 60.5% od góry): Logo za małe\n"
                      "  - znacznik 2 (film/zapowiedz.mp4, 0:12): Za szybko\n", text)
        self.assertNotIn("odbiór", self.row("Wizytówka"))
        rid = body["status"]["runId"]
        rec = self.manager.get(rid)
        self.assertEqual(rec["fix"], "Popraw logo")
        self.assertEqual([(p["file"], p["x"], p["t"]) for p in rec["pins"]],
                         [("wizytowki/przod.png", 34.0, None), ("film/zapowiedz.mp4", None, 12)])
        prompt = self.manager._priv[rid]["prompt"]
        self.assertIn("- znacznik 1 (wizytowki/przod.png, 34% od lewej, 60.5% od góry): Logo za małe", prompt)
        self.assertIn("zmiany:", prompt)
        d = self.task("Wizytówka")["detail"]
        self.assertEqual(d["fix"], "Popraw logo")
        self.assertEqual(d["notes"], [])
        self.assertEqual(len(d["pins"]), 2)
        status, body = self.review()
        self.assertIn(body["run"]["state"], ("queued", "running"))
        self.assertEqual(body["run"]["id"], rid)
        # nowa poprawka zastępuje stare znaczniki
        self.manager.stop(rid)
        self.wait(rid)
        t = self.task("Wizytówka")
        projekt.set_detail(self.folder, t["file"], t["line"], t["title"], "poprawka", "Inaczej")
        self.assertNotIn("znacznik", self.text())

    def test_popraw_same_znaczniki_i_bledy(self):
        self.set_mode("wolno")
        t = self.task("Wizytówka")
        bad = [({"text": "", "pins": []}, 400), ({"text": "  "}, 400),
               ({"text": "x", "pins": [{"file": "a.png", "x": 120, "y": 5}]}, 400),
               ({"text": "x", "pins": [{"file": "a.png", "x": 5}]}, 400),
               ({"text": "x", "pins": [{"file": "../a.png", "x": 5, "y": 5}]}, 400),
               ({"text": "x", "pins": [{"file": "a.png", "x": 5, "y": 5, "note": "n" * 301}]}, 400),
               ({"text": "x", "pins": [{"file": "a.png", "x": 5, "y": 5}] * 13}, 400),
               ({"text": "x", "title": "Inny tytuł"}, 409)]
        for extra, code in bad:
            body = dict({"id": t["id"], "title": t["title"]}, **extra)
            self.assertEqual(self.http("POST", "/api/odbior/popraw", body)[0], code, extra)
        self.assertEqual(self.manager._runs, {})
        status, raw, _ = self.http("POST", "/api/odbior/popraw", {"id": t["id"], "title": t["title"], "text": "",
                                                                  "pins": [{"file": "wizytowki/tyl.png", "x": 1, "y": 2}]})
        self.assertEqual(status, 200)
        self.assertIn("  poprawka: %s\n  - znacznik 1 (wizytowki/tyl.png, 1%% od lewej, 2%% od góry):\n"
                      % agents.REVIEW_FIX_DEFAULT, self.text())

    # ---------- akceptuj ----------
    def test_akceptuj_calosc(self):
        t = self.task("Wizytówka")
        status, raw, _ = self.http("POST", "/api/odbior/akceptuj", {"id": t["id"], "title": t["title"], "variants": None})
        self.assertEqual(status, 200, raw)
        self.assertTrue(self.row("Wizytówka").startswith("- [x] Wizytówka"))
        self.assertNotIn("odbiór", self.row("Wizytówka"))
        self.assertNotIn("odebrane", self.text())
        self.assertEqual(self.http("POST", "/api/odbior/akceptuj", {"id": t["id"], "title": "Zmieniony"})[0], 409)

    def test_akceptuj_czesc_wariantow(self):
        t = self.task("Wizytówka")
        for variants in (["nieznany"], [], "przod"):
            self.assertEqual(self.http("POST", "/api/odbior/akceptuj",
                                       {"id": t["id"], "title": t["title"], "variants": variants})[0], 400, variants)
        status, _, _ = self.http("POST", "/api/odbior/akceptuj", {"id": t["id"], "title": t["title"], "variants": ["tyl"]})
        self.assertEqual(status, 200)
        self.assertIn("  odpowiedź: odebrane warianty = tyl\n", self.text())
        self.assertTrue(self.row("Wizytówka").startswith("- [x]"))
        self.assertEqual(self.review()[1]["accepted"], ["tyl"])

    def test_akceptuj_wszystkie_warianty_bez_notatki(self):
        t = self.task("Wizytówka")
        status, _, _ = self.http("POST", "/api/odbior/akceptuj",
                                 {"id": t["id"], "title": t["title"], "variants": ["tyl", "przod"]})
        self.assertEqual(status, 200)
        self.assertNotIn("odebrane", self.text())

    # ---------- zmiany: ----------
    def test_zmiany_w_szczegolach(self):
        t = self.task("Wizytówka")
        status, raw, _ = self.http("POST", "/api/task/detail", {"id": t["id"], "title": t["title"], "key": "zmiany",
                                                                "value": "tło granatowe; logo większe"})
        self.assertEqual(status, 200, raw)
        self.assertIn("  zmiany: tło granatowe; logo większe\n", self.text())
        data = json.loads(self.http("GET", "/api/data")[1].decode("utf-8"))
        task = next(x for x in data["tasks"] if x["title"] == "Wizytówka")
        self.assertEqual(task["detail"]["changes"], ["tło granatowe", "logo większe"])
        self.assertEqual(self.task("Zadanie A")["detail"]["changes"], [])


if __name__ == "__main__":
    unittest.main()
