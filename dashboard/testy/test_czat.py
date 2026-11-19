"""Rozmowa o zadaniu: POST/GET /api/task/chat, Claude tylko z narzędziami do odczytu, historia w uruchomienia/czat."""
import glob
import http.client
import json
import os
import threading
from http.server import ThreadingHTTPServer
from urllib.parse import quote

from wspolne import Baza, server


class Czat(Baza):
    def setUp(self):
        super().setUp()
        self._log = server.Handler.log_message
        server.Handler.log_message = lambda *args: None
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        self.port = self.httpd.server_address[1]
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        server.Handler.log_message = self._log
        super().tearDown()

    # ---------- pomocnicze ----------
    def request(self, method, path, body=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=15)
        try:
            headers = {"Content-Type": "application/json"} if body is not None else {}
            conn.request(method, path, body=None if body is None else json.dumps(body).encode("utf-8"), headers=headers)
            resp = conn.getresponse()
            return resp.status, json.loads(resp.read().decode("utf-8"))
        finally:
            conn.close()

    def send(self, title, message):
        t = self.task(title)
        return self.manager.chat_send(t["id"], t["title"], message)

    def chat(self, title):
        return self.manager.chat_get(self.task(title)["id"])[2]

    def settle(self, title):
        self.wait_for(lambda: not self.chat(title)["pending"])
        return self.chat(title)

    def chat_calls(self):
        return [c for c in self.calls() if "json" in c["argv"]]

    # ---------- testy ----------
    def test_odpowiedz_i_historia(self):
        self.assertEqual(self.send("Zadanie A", "  Po co jest to zadanie?  "), (202, "", {"pending": True}))
        c = self.settle("Zadanie A")
        self.assertEqual(c["error"], "")
        self.assertEqual([m["role"] for m in c["messages"]], ["ty", "claude"])
        self.assertEqual(c["messages"][0]["text"], "Po co jest to zadanie?")
        self.assertEqual(c["messages"][1]["text"], "Odpowiedź atrapy: Po co jest to zadanie?")
        files = glob.glob(os.path.join(self.runs, "czat", "*.json"))
        self.assertEqual(len(files), 1)
        self.assertRegex(os.path.basename(files[0]), r"^[0-9a-f]{40}\.json$")
        with open(files[0], encoding="utf-8") as f:
            saved = json.load(f)
        self.assertEqual(saved["session"], "sesja-1")
        self.assertFalse(saved["pending"])
        call = self.chat_calls()[0]
        argv, prompt = call["argv"], call["prompt"]
        self.assertEqual(os.path.realpath(call["cwd"]), os.path.realpath(self.folder))
        self.assertNotIn("--resume", argv)
        for text in ("Zadanie A", "ZADANIA.md", os.path.join(self.folder, "KARTA.md"), "Propozycja:", "Etap: Pierwszy",
                     "niczego nie zmieniasz", "hasła"):
            self.assertIn(text, prompt)
        self.assertTrue(prompt.rstrip().endswith("Po co jest to zadanie?"))
        self.assertEqual(call["env"], ["CLAUDE_CODE_OAUTH_TOKEN"])      # bez kluczy API i hasła panelu

        self.assertEqual(self.send("Zadanie A", "A termin?")[0], 202)
        c = self.settle("Zadanie A")
        self.assertEqual([m["role"] for m in c["messages"]], ["ty", "claude", "ty", "claude"])
        second = self.chat_calls()[1]
        self.assertEqual(second["argv"][second["argv"].index("--resume") + 1], "sesja-1")
        self.assertEqual(second["prompt"], "A termin?\n")

    def test_tylko_odczyt(self):
        self.send("Zadanie A", "Pytanie")
        self.settle("Zadanie A")
        argv = self.chat_calls()[0]["argv"]
        allowed = argv[argv.index("--allowedTools") + 1].split(",")
        self.assertEqual(sorted(allowed), ["Glob", "Grep", "LS", "Read"])
        denied = argv[argv.index("--disallowedTools") + 1].split(",")
        for name in ("Bash", "Edit", "Write", "NotebookEdit", "WebFetch"):
            self.assertIn(name, denied)
        self.assertEqual(argv[argv.index("--permission-mode") + 1], "default")
        self.assertEqual(argv[argv.index("--output-format") + 1], "json")
        self.assertIn("--strict-mcp-config", argv)
        joined = " ".join(argv)
        for bad in ("acceptEdits", "bypassPermissions", "dangerously", "stream-json"):
            self.assertNotIn(bad, joined)

    def test_zla_wiadomosc(self):
        self.assertEqual(self.send("Zadanie A", "   ")[0], 400)
        self.assertEqual(self.send("Zadanie A", "x" * 2001)[0], 400)
        self.assertEqual(self.chat("Zadanie A")["messages"], [])
        t = self.task("Zadanie A")
        self.assertEqual(self.manager.chat_send(t["id"], "Inny tytuł", "Pytanie")[0], 409)
        self.assertEqual(self.manager.chat_send("obcy|ZADANIA.md|1", "X", "Pytanie")[0], 404)
        self.assertEqual(self.calls(), [])

    def test_druga_wiadomosc_w_trakcie(self):
        self.set_mode("czat-wolno")
        self.assertEqual(self.send("Zadanie A", "Pierwsze")[0], 202)
        self.assertTrue(self.chat("Zadanie A")["pending"])
        self.assertEqual(self.send("Zadanie A", "Drugie"), (409, "Czekam jeszcze na odpowiedź.", {}))
        c = self.settle("Zadanie A")
        self.assertEqual([m["text"] for m in c["messages"] if m["role"] == "ty"], ["Pierwsze"])

    def test_bledy(self):
        self.set_mode("login")
        self.send("Zadanie A", "Pytanie")
        c = self.settle("Zadanie A")
        self.assertTrue(c["error"].startswith("Wymaga logowania"))
        self.assertEqual([m["role"] for m in c["messages"]], ["ty"])
        self.set_mode("smieci")
        self.send("Zadanie A", "Pytanie 2")
        c = self.settle("Zadanie A")
        self.assertTrue(c["error"].startswith("Nie udało się uzyskać odpowiedzi"))
        self.assertNotIn("Traceback", c["error"])
        self.set_mode("wolno")
        self.manager.chat_timeout = 1
        self.send("Zadanie A", "Pytanie 3")
        c = self.settle("Zadanie A")
        self.assertIn("Brak odpowiedzi", c["error"])
        self.set_mode("ok")
        self.send("Zadanie A", "Pytanie 4")
        c = self.settle("Zadanie A")
        self.assertEqual(c["error"], "")
        self.assertNotIn("--resume", self.chat_calls()[-1]["argv"])      # bez udanej odpowiedzi nie ma sesji

    def test_brak_claude_i_logowanie(self):
        self.manager = self.new_manager(PANEL_CLAUDE=os.path.join(self.tmp, "brak"))
        self.assertEqual(self.send("Zadanie A", "Pytanie"), (409, "Brak polecenia claude", {}))
        self.manager = self.new_manager()
        self.manager._state["needsLogin"] = True
        code, err, _ = self.send("Zadanie A", "Pytanie")
        self.assertEqual(code, 409)
        self.assertTrue(err.startswith("Wymaga logowania"))

    def test_najwyzej_100_wiadomosci(self):
        t = self.task("Zadanie A")
        path = self.manager._chat_file(t)
        os.makedirs(os.path.dirname(path))
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"session": "sesja-1", "pending": False, "error": "",
                       "messages": [{"role": "ty", "text": str(i), "at": ""} for i in range(120)]}, f)
        self.assertEqual(len(self.chat("Zadanie A")["messages"]), 100)
        self.send("Zadanie A", "Ostatnie")
        c = self.settle("Zadanie A")
        self.assertEqual(len(c["messages"]), 100)
        self.assertEqual(c["messages"][-1]["role"], "claude")

    def test_przerwana_po_restarcie(self):
        t = self.task("Zadanie A")
        path = self.manager._chat_file(t)
        os.makedirs(os.path.dirname(path))
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"session": "", "pending": True, "error": "", "messages": [{"role": "ty", "text": "x", "at": ""}]}, f)
        c = self.chat("Zadanie A")
        self.assertFalse(c["pending"])
        self.assertTrue(c["error"])
        self.assertEqual(self.send("Zadanie A", "Jeszcze raz")[0], 202)
        self.settle("Zadanie A")

    def test_serwer(self):
        t = self.task("Zadanie A")
        status, body = self.request("POST", "/api/task/chat", {"id": t["id"], "title": t["title"], "message": "ą" * 2000})
        self.assertEqual((status, body), (202, {"ok": True, "error": "", "pending": True}))
        self.wait_for(lambda: not self.request("GET", "/api/task/chat?id=" + quote(t["id"]))[1]["pending"])
        status, body = self.request("GET", "/api/task/chat?id=" + quote(t["id"]))
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertEqual(body["error"], "")
        self.assertEqual([m["role"] for m in body["messages"]], ["ty", "claude"])
        self.assertEqual(body["messages"][0]["text"], "ą" * 2000)
        status, body = self.request("POST", "/api/task/chat", {"id": t["id"], "title": t["title"], "message": ""})
        self.assertEqual(status, 400)
        self.assertFalse(body["ok"])
        status, body = self.request("GET", "/api/task/chat?id=" + quote("obcy|ZADANIA.md|1"))
        self.assertEqual((status, body), (404, {"ok": False, "error": "Nie ma tego zadania."}))
        status, body = self.request("POST", "/api/task/chat", {"id": t["id"], "title": t["title"], "message": "x" * 40000})
        self.assertEqual(status, 400)                       # treść ponad 32 KB: nieprawidłowe żądanie
        status, _ = self.request("POST", "/api/agent/stop", {"id": "x" * 5000})
        self.assertEqual(status, 400)                       # pozostałe żądania: nadal najwyżej 4 KB


if __name__ == "__main__":
    import unittest
    unittest.main()
