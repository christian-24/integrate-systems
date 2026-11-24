"""Serwer panelu (server.py): żądania agentów i projektów, dane dla strony, dostęp z innych urządzeń."""
import http.client
import json
import os
import threading
import time
import unittest
from http.server import ThreadingHTTPServer
from urllib.parse import urlencode

from wspolne import Baza, agents, projekt, quiet, server

REMOTE = {"X-Forwarded-For": "100.64.0.7"}        # żądanie przez pośrednika liczy się jak zdalne


class Serwer(Baza):
    def setUp(self):
        super().setUp()
        self._saved = (dict(server._cal), server.NOTES, server.LOGIN_DELAY, server.Handler.log_message)
        server.Handler.log_message = lambda *args: None
        # Testy nie uruchamiają pomocnika kalendarza i nie czytają prawdziwych notatek.
        server._cal.update(at=time.time() + 3600, data={"status": "no_helper", "error": ""}, connecting=False)
        server.NOTES = self.notes
        server.LOGIN_DELAY = 0
        server._fails.clear()
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        self.port = self.httpd.server_address[1]
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        cal, server.NOTES, server.LOGIN_DELAY, server.Handler.log_message = self._saved
        server._cal.clear()
        server._cal.update(cal)
        server._fails.clear()
        super().tearDown()

    def request(self, method, path, body=None, headers=None, raw=None, ctype="application/json"):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=15)
        try:
            headers = dict(headers or {})
            if body is not None:
                raw = json.dumps(body).encode("utf-8")
            if raw is not None:
                headers.setdefault("Content-Type", ctype)
            conn.request(method, path, body=raw, headers=headers)
            resp = conn.getresponse()
            return resp.status, dict(resp.getheaders()), resp.read().decode("utf-8")
        finally:
            conn.close()

    def post(self, path, body, **kw):
        status, _, text = self.request("POST", path, body=body, **kw)
        return status, json.loads(text)

    def data(self, **kw):
        status, _, text = self.request("GET", "/api/data", **kw)
        self.assertEqual(status, 200)
        return json.loads(text)

    def login(self, password):
        return self.request("POST", "/wejscie", raw=urlencode({"haslo": password}).encode("utf-8"),
                            ctype="application/x-www-form-urlencoded", headers=REMOTE)


class Dane(Serwer):
    def test_blok_agentow_zgodny_z_przykladem(self):
        with open(server.SAMPLE_AGENTS, encoding="utf-8") as f:
            sample = json.load(f)
        self.manager.refresh_tools(force=True, wait=True)
        rid = self.post("/api/agent/run", {"id": self.task("Zadanie A")["id"], "title": "Zadanie A"})[1]["id"]
        self.wait(rid)
        data = self.data()
        block = data["agents"]
        self.assertEqual(set(block), set(sample))
        self.assertEqual(set(block["runs"][0]), set(sample["runs"][0]) | {"choiceReason", "outcome"})
        self.assertEqual(block["runs"][0]["outcome"], "done")
        self.assertEqual(set(block["today"]), set(sample["today"]))
        self.assertEqual({k: set(v) for k, v in block["tools"].items()}, {k: set(v) for k, v in sample["tools"].items()})
        self.assertEqual((block["machine"], block["automat"], block["maxParallel"], block["canRunTasks"],
                          block["needsLogin"], block["limitUntil"]), ("mac", False, 2, True, False, None))
        self.assertEqual(block["today"], {"runs": 1, "tokens": 3352, "costUsd": 0.04})
        self.assertEqual((block["runs"][0]["id"], block["runs"][0]["state"]), (rid, "done"))
        tasks = {t["title"]: t for t in data["tasks"]}
        self.assertEqual((tasks["Zadanie B"]["runBlock"], tasks["Zadanie B"]["runId"]), ("", ""))
        self.assertEqual(tasks["Zadanie D"]["runBlock"], "Zadanie po Twojej stronie")
        self.assertEqual(tasks["Zadanie E"]["runBlock"], "Czeka na Twoją zgodę")
        self.assertEqual(tasks["Zadanie A"]["runBlock"], "Zrobione")
        self.assertEqual(data["icsPath"], "/terminy.ics")

    def test_podglad_i_eksport(self):
        status, _, page = self.request("GET", "/podglad")
        self.assertEqual(status, 200)
        self.assertIn("przyklad-5", page)
        self.assertNotIn("/Users", page)
        self.assertNotIn(self.tmp, page)
        preview = server.preview_data()
        self.assertEqual(preview["agents"]["runs"][0]["id"], "przyklad-5")
        running = next(t for t in preview["tasks"] if t["title"] == "Eksport CSV: zapis strumieniowy")
        self.assertEqual((running["runBlock"], running["runId"]), ("W toku", "przyklad-5"))
        self.assertTrue(all("runBlock" in t and "runId" in t for t in preview["tasks"]))
        target = os.path.join(self.tmp, "podglad.html")
        quiet(server.export_preview, target)
        with open(target, encoding="utf-8") as f:
            self.assertNotIn("/Users", f.read())

    def test_strona_i_nieznana_sciezka(self):
        self.assertEqual(self.request("GET", "/")[0], 200)
        self.assertEqual(self.request("GET", "/nie-ma")[0], 404)
        self.assertEqual(self.request("POST", "/api/nie-ma", body={})[0], 404)
        self.assertEqual(self.request("GET", "/wejscie")[0], 303)            # z tego komputera hasło nie jest potrzebne


class Zadania(Serwer):
    def test_uruchomienie_z_panelu(self):
        task = self.task("Zadanie A")
        status, answer = self.post("/api/agent/run", {"id": task["id"], "title": "Zadanie A"})
        self.assertEqual((status, answer["ok"], answer["error"]), (200, True, ""))
        self.assertEqual(self.wait(answer["id"])["state"], "done")
        self.assertTrue(self.row("Zadanie A").startswith("- [x] Zadanie A"))
        self.assertEqual(self.post("/api/agent/stop", {"id": answer["id"]}),
                         (409, {"ok": False, "error": "Uruchomienie już się zakończyło."}))

    def test_odmowy(self):
        task = self.task("Zadanie A")
        self.assertEqual(self.post("/api/agent/run", {})[0], 400)
        self.assertEqual(self.post("/api/agent/run", {"id": task["id"], "title": "Inny"}),
                         (409, {"ok": False, "error": agents.CONFLICT}))
        self.assertEqual(self.post("/api/agent/run", {"id": "nie-ma|ZADANIA.md|3", "title": "x"})[0], 404)
        self.assertEqual(self.post("/api/agent/run", {"id": self.task("Zadanie D")["id"], "title": "Zadanie D"}),
                         (409, {"ok": False, "error": "Zadanie po Twojej stronie"}))
        self.assertEqual(self.post("/api/agent/stop", {"id": "nie-ma"})[0], 404)
        self.assertEqual(self.post("/api/agent/stop", {})[0], 404)
        self.assertEqual(self.post("/api/agent/check", {"tool": "inne"})[0], 400)
        self.assertEqual(self.post("/api/agent/automat", {"enabled": "tak"})[0], 400)
        self.assertEqual(self.post("/api/agent/automat", {})[0], 400)
        status, _, text = self.request("POST", "/api/agent/pm", raw=b"{}", ctype="text/plain")
        self.assertEqual((status, json.loads(text)["error"]), (400, "Nieprawidłowe żądanie."))
        self.assertEqual(self.request("POST", "/api/agent/pm", raw=b"[1]")[0], 400)
        self.assertEqual(self.request("POST", "/api/agent/pm", body={}, headers={"Origin": "http://obca.example"})[0], 403)
        self.assertEqual(self.request("GET", "/api/data", headers={"Host": "obca.example"})[0], 403)
        self.assertEqual(self.calls(), [])

    def test_zatrzymanie_raport_test_automat(self):
        self.set_mode("wolno")
        task = self.task("Zadanie A")
        rid = self.post("/api/agent/run", {"id": task["id"], "title": "Zadanie A"})[1]["id"]
        self.wait(rid, ("running",))
        data = self.data()
        row = next(t for t in data["tasks"] if t["title"] == "Zadanie A")
        self.assertEqual((row["state"], row["runBlock"], row["runId"]), ("doing", "W toku", rid))
        self.assertEqual(self.post("/api/project/remove", {"id": "projekt-testowy"})[0], 409)
        self.assertEqual(self.post("/api/agent/stop", {"id": rid}), (200, {"ok": True, "error": ""}))
        self.assertEqual(self.wait(rid)["state"], "stopped")
        status, answer = self.post("/api/agent/pm", {})
        self.assertEqual(status, 200)
        self.assertEqual(self.post("/api/agent/pm", {}), (409, {"ok": False, "error": "Raport PM już trwa."}))
        self.post("/api/agent/stop", {"id": answer["id"]})
        self.wait(answer["id"])
        self.set_mode("ok")
        status, answer = self.post("/api/agent/check", {"tool": "claude"})
        self.assertEqual(status, 200)
        self.assertEqual(self.wait(answer["id"])["kind"], "check")
        self.assertEqual(self.post("/api/agent/automat", {"enabled": True})[0], 200)
        self.assertTrue(self.data()["agents"]["automat"])
        self.assertEqual(self.post("/api/agent/automat", {"enabled": False})[0], 200)
        self.assertFalse(self.data()["agents"]["automat"])


class Projekty(Serwer):
    def test_dodanie_i_usuniecie(self):
        new = os.path.join(self.tmp, "nowy-projekt")
        os.makedirs(new)
        with open(os.path.join(new, "README.md"), "w", encoding="utf-8") as f:
            f.write("moje README\n")
        self.assertEqual(self.post("/api/project/add", {"path": new, "name": "Nowy projekt", "files": True}),
                         (200, {"ok": True, "error": ""}))
        self.assertTrue(os.path.exists(os.path.join(new, "ZADANIA.md")))
        with open(os.path.join(new, "README.md"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "moje README\n")                     # istniejący plik zostaje
        data = self.data()
        self.assertEqual(sorted(p["id"] for p in data["projects"]), ["nowy-projekt", "projekt-testowy"])
        self.assertEqual(next(p["name"] for p in data["projects"] if p["id"] == "nowy-projekt"), "Nowy projekt")
        self.assertEqual(self.post("/api/project/add", {"path": new, "files": False})[0], 409)
        self.assertEqual(self.post("/api/project/remove", {"id": "nowy-projekt"}), (200, {"ok": True, "error": ""}))
        self.assertTrue(os.path.exists(os.path.join(new, "ZADANIA.md")))    # pliki zostają
        self.assertEqual(self.post("/api/project/remove", {"id": "nowy-projekt"})[0], 404)
        bare = os.path.join(self.tmp, "bez-plikow")
        os.makedirs(bare)
        self.assertEqual(self.post("/api/project/add", {"path": bare, "files": False})[0], 200)
        self.assertEqual(os.listdir(bare), [])                               # files: false niczego nie zakłada
        self.assertIn(bare, projekt.registry())

    def test_odmowy(self):
        add = lambda body: self.post("/api/project/add", body)[0]
        self.assertEqual(add({}), 400)
        self.assertEqual(add({"path": "  ", "files": True}), 400)
        self.assertEqual(add({"path": "projekty/x", "files": True}), 400)
        self.assertEqual(add({"path": self.folder, "files": "tak"}), 400)
        self.assertEqual(add({"path": self.folder, "name": 5, "files": True}), 400)
        self.assertEqual(add({"path": os.path.join(self.tmp, "nie-ma"), "files": True}), 404)
        self.assertEqual(add({"path": "~", "files": True}), 400)
        self.assertEqual(add({"path": os.sep, "files": True}), 400)
        self.assertEqual(add({"path": os.path.join(server.SAMPLES, "landing"), "files": True}), 400)
        self.assertEqual(add({"path": self.folder, "files": True}), 409)
        self.assertEqual(self.post("/api/project/remove", {})[0], 404)
        self.assertEqual(self.post("/api/project/remove", {"id": "nie-ma"})[0], 404)
        self.assertEqual(projekt.registry(), [self.folder])


class BezRejestru(Serwer):
    registered = False

    def test_projekty_przykladowe(self):
        data = self.data()
        self.assertEqual((data["projectsSource"], data["agents"]["canRunTasks"]), ("sample", False))
        self.assertEqual({t["runBlock"] for t in data["tasks"]}, {"Projekty przykładowe"})
        task = data["tasks"][0]
        self.assertEqual(self.post("/api/agent/run", {"id": task["id"], "title": task["title"]}),
                         (409, {"ok": False, "error": "Projekty przykładowe"}))
        self.assertEqual(self.post("/api/project/remove", {"id": data["projects"][0]["id"]})[0], 404)
        self.assertEqual(self.post("/api/project/add", {"path": self.folder, "files": False})[0], 200)
        data = self.data()
        self.assertEqual((data["projectsSource"], data["agents"]["canRunTasks"]), ("registry", True))


class Dostep(Serwer):
    def test_bez_hasla_inne_urzadzenia_odrzucane(self):
        server.TOKEN = ""
        for method, path in (("GET", "/"), ("GET", "/api/data"), ("GET", "/wejscie"), ("GET", "/terminy.ics")):
            self.assertEqual(self.request(method, path, headers=REMOTE)[0], 403, path)
        self.assertEqual(self.request("POST", "/api/agent/pm", body={}, headers=REMOTE)[0], 403)
        self.assertEqual(self.login("cokolwiek")[0], 403)
        self.assertEqual(self.request("GET", "/api/data")[0], 200)           # z tego komputera bez hasła
        self.assertEqual(self.calls(), [])

    def test_haslo_i_ciasteczko(self):
        server.TOKEN = "haslo-do-testow"
        status, headers, _ = self.request("GET", "/", headers=REMOTE)
        self.assertEqual((status, headers["Location"]), (303, "/wejscie"))
        self.assertEqual(self.request("GET", "/podglad", headers=REMOTE)[0], 303)
        status, _, text = self.request("GET", "/api/data", headers=REMOTE)
        self.assertEqual((status, json.loads(text)), (401, {"ok": False, "error": "Wymagane hasło."}))
        status, _, text = self.request("POST", "/api/agent/pm", body={}, headers=REMOTE)
        self.assertEqual((status, json.loads(text)), (401, {"ok": False, "error": "Wymagane hasło."}))
        status, _, page = self.request("GET", "/wejscie", headers=REMOTE)
        self.assertEqual(status, 200)
        self.assertIn('name="haslo"', page)
        status, headers, page = self.login("zle")
        self.assertEqual(status, 401)
        self.assertIn("Błędne hasło.", page)
        self.assertEqual(self.login(" haslo-do-testow\n")[0], 303)            # odstępy wokół hasła nie przeszkadzają
        self.assertNotIn("Set-Cookie", headers)
        status, headers, _ = self.login("haslo-do-testow")
        self.assertEqual((status, headers["Location"]), (303, "/"))
        cookie = headers["Set-Cookie"]
        self.assertTrue(cookie.startswith("panel_sesja="))
        for part in ("HttpOnly", "SameSite=Strict", "Path=/"):
            self.assertIn(part, cookie)
        value = cookie.split(";")[0].split("=", 1)[1]
        self.assertNotIn("haslo-do-testow", cookie)                          # ciasteczko nie zawiera hasła
        session = dict(REMOTE, Cookie="panel_sesja=" + value)
        self.assertEqual(self.request("GET", "/", headers=session)[0], 200)
        self.assertEqual(self.request("GET", "/wejscie", headers=session)[0], 303)
        data = self.data(headers=session)
        self.assertEqual(self.post("/api/agent/automat", {"enabled": False}, headers=session)[0], 200)
        self.assertEqual(self.request("GET", "/api/data", headers=dict(REMOTE, Cookie="panel_sesja=" + "0" * 64))[0], 401)
        self.assertEqual(self.request("GET", "/api/data", headers=dict(REMOTE, Cookie="panel_sesja=haslo-do-testow"))[0], 401)
        # klucz kalendarza: inny niż ciasteczko, działa bez ciasteczka i tylko dla /terminy.ics
        self.assertTrue(data["icsPath"].startswith("/terminy.ics?k="))
        key = data["icsPath"].split("k=")[1]
        self.assertNotEqual(key, value)
        status, headers, text = self.request("GET", data["icsPath"], headers=REMOTE)
        self.assertEqual(status, 200)
        self.assertIn("BEGIN:VCALENDAR", text)
        self.assertEqual(self.request("GET", "/terminy.ics", headers=REMOTE)[0], 401)
        self.assertEqual(self.request("GET", "/terminy.ics?k=zly", headers=REMOTE)[0], 401)
        self.assertEqual(self.request("GET", "/api/data?k=" + key, headers=REMOTE)[0], 401)
        self.assertEqual(self.request("GET", "/api/data", headers=dict(REMOTE, Cookie="panel_sesja=" + key))[0], 401)

    def test_pliki_aplikacji_bez_logowania(self):
        server.TOKEN = "haslo-do-testow"
        status, headers, text = self.request("GET", "/app/manifest.webmanifest", headers=REMOTE)
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "application/manifest+json")
        man = json.loads(text)
        self.assertEqual((man["start_url"], man["display"]), ("/", "standalone"))
        self.assertEqual(self.request("GET", "/app/ikona.svg", headers=REMOTE)[0], 200)
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=15)
        conn.request("GET", "/app/ikona-180.png", headers=REMOTE)
        resp = conn.getresponse()
        self.assertEqual((resp.status, resp.getheader("Content-Type"), resp.read()[:4]), (200, "image/png", b"\x89PNG"))
        conn.close()
        self.assertEqual(self.request("GET", "/app/nie-ma.png", headers=REMOTE)[0], 303)       # tylko znane pliki
        self.assertEqual(self.request("GET", "/app/../projekty.json", headers=REMOTE)[0], 303)
        status, _, page = self.request("GET", "/wejscie", headers=REMOTE)
        self.assertIn('rel="manifest"', page)
        self.assertIn('rel="apple-touch-icon"', page)
        self.assertNotIn("@@APP@@", page)
        status, _, page = self.request("GET", "/")
        self.assertIn('rel="manifest"', page)

    def test_limit_prob(self):
        server.TOKEN = "haslo-do-testow"
        for _ in range(10):
            self.assertEqual(self.login("zle")[0], 401)
        status, _, page = self.login("zle")
        self.assertEqual(status, 429)
        self.assertIn("Za dużo prób", page)
        self.assertEqual(self.login("haslo-do-testow")[0], 429)              # blokada obejmuje też poprawne hasło
        server._fails.clear()
        self.assertEqual(self.login("haslo-do-testow")[0], 303)

    def test_opoznienie_blednej_proby(self):
        server.TOKEN = "haslo-do-testow"
        server.LOGIN_DELAY = 0.3
        start = time.time()
        self.assertEqual(self.login("zle")[0], 401)
        self.assertGreaterEqual(time.time() - start, 0.3)

    def test_polaczenie_zdalne_bez_posrednika(self):
        server.TOKEN = "haslo-do-testow"
        original = server.Handler._client_local
        server.Handler._client_local = lambda handler: False
        try:
            self.assertEqual(self.request("GET", "/api/data")[0], 401)
            self.assertEqual(self.request("GET", "/")[0], 303)
        finally:
            server.Handler._client_local = original


class Ustawienia(Baza):
    def test_plik_panel_env(self):
        path = os.path.join(self.tmp, "panel.env")
        with open(path, "w", encoding="utf-8-sig") as f:
            f.write("# komentarz\nPANEL_TEST_A=wartość\nPANEL_TEST_B = \"w cudzysłowie\"\nPANEL_TEST_C=\n"
                    "PANEL_TEST_D=z pliku\nPANEL_TEST_E=z pliku\nbez znaku równości\n")
        os.environ["PANEL_TEST_D"] = "ze środowiska"
        os.environ["PANEL_TEST_E"] = ""
        try:
            server.load_env_file(path)
            self.assertEqual(os.environ["PANEL_TEST_A"], "wartość")
            self.assertEqual(os.environ["PANEL_TEST_B"], "w cudzysłowie")
            self.assertNotIn("PANEL_TEST_C", os.environ)                     # pusty wpis to brak wartości
            self.assertEqual(os.environ["PANEL_TEST_D"], "ze środowiska")    # środowisko ma pierwszeństwo
            self.assertEqual(os.environ["PANEL_TEST_E"], "z pliku")          # puste środowisko nie przesłania pliku
            server.load_env_file(os.path.join(self.tmp, "nie-ma.env"))       # brak pliku nie jest błędem
        finally:
            for key in "ABCDE":
                os.environ.pop("PANEL_TEST_" + key, None)

    def test_brak_wyjscia_nie_przerywa(self):
        import sys
        saved = sys.stderr
        sys.stderr = None                                                    # tak działa pythonw na Windows
        try:
            agents.log("wiersz dziennika")
        finally:
            sys.stderr = saved


if __name__ == "__main__":
    unittest.main()
