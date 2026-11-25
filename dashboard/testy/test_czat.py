"""Rozmowa w projekcie (POST/GET /api/project/chat): odnośnik do zadania („Zapytaj o to zadanie”) z kontekstem zadania,
te same narzędzia i zasady co Asystent, historia w uruchomienia/czat. Dawny czat przy zadaniu: tylko odczyt historii."""
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
            raw = resp.read().decode("utf-8")
            try:
                return resp.status, json.loads(raw)
            except ValueError:
                return resp.status, raw
        finally:
            conn.close()

    @property
    def pid(self):
        return self.task("Zadanie A")["project"]

    def send(self, title, message, **kw):
        """Wiadomość w Rozmowie w projekcie z odnośnikiem do zadania (przycisk „Zapytaj o to zadanie”)."""
        return self.manager.project_chat_send(self.pid, message, self.task(title)["id"] if title else "", **kw)

    def chat(self):
        return self.manager.project_chat_get(self.pid)[2]

    def settle(self):
        self.wait_for(lambda: not self.chat()["pending"])
        return self.chat()

    def chat_calls(self):
        return [c for c in self.calls() if "json" in c["argv"]]

    # ---------- testy ----------
    def test_zapytaj_o_zadanie_kontekst_i_historia(self):
        self.assertEqual(self.send("Zadanie A", "  Po co jest to zadanie?  "), (202, "", {"pending": True}))
        c = self.settle()
        self.assertEqual(c["error"], "")
        self.assertEqual([m["role"] for m in c["messages"]], ["ty", "claude"])
        mine = c["messages"][0]
        self.assertEqual(mine["text"], "Po co jest to zadanie?")
        self.assertEqual(mine["task"]["title"], "Zadanie A")             # odnośnik widać w historii
        self.assertTrue(c["messages"][1]["text"].startswith("Odpowiedź atrapy:"))
        files = glob.glob(os.path.join(self.runs, "czat", "projekt-*.json"))
        self.assertEqual(len(files), 1)                                  # jedna rozmowa: projektu, nie zadania
        with open(files[0], encoding="utf-8") as f:
            saved = json.load(f)
        self.assertEqual(saved["session"], "sesja-1")
        call = self.chat_calls()[0]
        argv, prompt = call["argv"], call["prompt"]
        self.assertEqual(os.path.realpath(call["cwd"]), os.path.realpath(self.folder))
        self.assertNotIn("--resume", argv)
        for text in ("[zadanie: „Zadanie A”", "etap: Pierwszy", "kto: claude", "Ostatnie uruchomienie agenta: brak",
                     os.path.join(self.folder, "KARTA.md"), "Propozycja:", "Uruchom:", "Polecenie:",
                     "Odpowiedź na pytanie:", "hasła"):
            self.assertIn(text, prompt)
        self.assertTrue(prompt.rstrip().endswith("Po co jest to zadanie?"))
        self.assertEqual(call["env"], ["CLAUDE_CODE_OAUTH_TOKEN"])      # bez kluczy API i hasła panelu

        # druga wiadomość w tej samej sesji: kontekst zadania znów przed wiadomością (stan mógł się zmienić)
        rid = self.run_task("Zadanie A")[2]["id"]
        self.wait(rid)
        self.assertEqual(self.send("Zadanie A", "A termin?")[0], 202)
        c = self.settle()
        self.assertEqual([m["role"] for m in c["messages"]], ["ty", "claude", "ty", "claude"])
        second = self.chat_calls()[-1]
        self.assertEqual(second["argv"][second["argv"].index("--resume") + 1], "sesja-1")
        self.assertTrue(second["prompt"].startswith("[zadanie: „Zadanie A”"))
        self.assertIn("Ostatnie uruchomienie agenta: zakończone", second["prompt"])
        self.assertTrue(second["prompt"].endswith("A termin?\n"))

        # bez odnośnika: sama wiadomość
        self.assertEqual(self.send("", "Co dalej?")[0], 202)
        self.settle()
        self.assertEqual(self.chat_calls()[-1]["prompt"], "Co dalej?\n")

    def test_te_same_narzedzia_co_asystent(self):
        """To, czego odmawiał dawny czat zadania (zapis w ZADANIA.md, uruchamianie), Rozmowa w projekcie może:
        te same narzędzia, zakazy, model i tryb co Asystent."""
        self.send("Zadanie A", "Pytanie")
        self.settle()
        argv = self.chat_calls()[0]["argv"]
        allowed = argv[argv.index("--allowedTools") + 1].split(",")
        a_allow, a_deny, _ = self.manager.chat_tools([self.folder])
        self.assertEqual(allowed, a_allow)
        self.assertEqual(argv[argv.index("--disallowedTools") + 1], a_deny)
        self.assertEqual(a_deny, self.manager.ASSIST_DENY)               # ta sama lista zakazów co Asystent
        as_allow, _ = self.manager._assistant_tools({self.pid: self.folder})
        self.assertEqual(sorted(allowed), sorted(as_allow))
        cards = os.path.dirname(os.path.realpath(os.path.join(self.folder, "KARTA.md"))).rstrip("/")
        self.assertIn("Edit(/%s/ZADANIA.md)" % cards, allowed)
        self.assertIn("Edit(/%s/kampanie/**)" % cards, allowed)
        self.assertNotIn("Edit", allowed)                                 # bez edycji dowolnych plików
        denied = argv[argv.index("--disallowedTools") + 1].split(",")
        for name in ("Bash", "Write", "MultiEdit", "NotebookEdit", "Agent", "Task", "Workflow"):
            self.assertIn(name, denied)
        self.assertEqual(argv[argv.index("--permission-mode") + 1], "default")
        self.assertEqual(argv[argv.index("--model") + 1], self.manager.assist_model)
        self.assertIn("--strict-mcp-config", argv)
        joined = " ".join(argv)
        for bad in ("acceptEdits", "bypassPermissions", "dangerously"):
            self.assertNotIn(bad, joined)
        # zasady w obu promptach z jednego źródła
        import datetime
        rules = self.manager.chat_rules("%s | " % self.pid, datetime.date.today())
        prompt = self.chat_calls()[0]["prompt"]
        for line in rules:
            self.assertIn(line, prompt)
        data, index = self.manager.load_projects()
        as_prompt = self.manager.assistant_prompt(data, index, "x", "#asystent")
        for line in self.manager.chat_rules("<id projektu> | ", datetime.date.today(), self.manager.site_links(data)):
            self.assertIn(line, as_prompt)

    def test_zla_wiadomosc(self):
        self.assertEqual(self.send("Zadanie A", "   ")[0], 400)
        self.assertEqual(self.send("Zadanie A", "x" * 2001)[0], 400)
        self.assertEqual(self.chat()["messages"], [])
        self.assertEqual(self.manager.project_chat_send(self.pid, "Pytanie", "obcy|ZADANIA.md|1")[0], 404)
        self.assertEqual(self.manager.project_chat_send("obcy", "Pytanie")[0], 404)
        self.assertEqual(self.calls(), [])

    def test_druga_wiadomosc_w_trakcie(self):
        self.set_mode("czat-wolno")
        self.assertEqual(self.send("Zadanie A", "Pierwsze")[0], 202)
        self.assertTrue(self.chat()["pending"])
        self.assertEqual(self.send("Zadanie A", "Drugie"), (409, "Czekam jeszcze na odpowiedź.", {}))
        c = self.settle()
        self.assertEqual([m["text"] for m in c["messages"] if m["role"] == "ty"], ["Pierwsze"])

    def test_bledy(self):
        self.set_mode("login")
        self.send("Zadanie A", "Pytanie")
        c = self.settle()
        self.assertTrue(c["error"].startswith("Wymaga logowania"))
        self.assertEqual([m["role"] for m in c["messages"]], ["ty"])
        self.set_mode("smieci")
        self.send("Zadanie A", "Pytanie 2")
        c = self.settle()
        self.assertTrue(c["error"].startswith("Nie udało się uzyskać odpowiedzi"))
        self.assertNotIn("Traceback", c["error"])
        self.set_mode("wolno")
        self.manager.chat_timeout = 1
        self.send("Zadanie A", "Pytanie 3")
        c = self.settle()
        self.assertIn("Brak odpowiedzi", c["error"])
        self.set_mode("ok")
        self.send("Zadanie A", "Pytanie 4")
        c = self.settle()
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
        path = self.manager._project_chat_file(self.pid)
        os.makedirs(os.path.dirname(path))
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"session": "sesja-1", "pending": False, "error": "",
                       "messages": [{"role": "ty", "text": str(i), "at": ""} for i in range(120)]}, f)
        self.assertEqual(len(self.chat()["messages"]), 100)
        self.send("Zadanie A", "Ostatnie")
        c = self.settle()
        self.assertEqual(len(c["messages"]), 100)
        self.assertEqual(c["messages"][-1]["role"], "claude")

    def test_przerwana_po_restarcie(self):
        path = self.manager._project_chat_file(self.pid)
        os.makedirs(os.path.dirname(path))
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"session": "", "pending": True, "error": "", "messages": [{"role": "ty", "text": "x", "at": ""}]}, f)
        c = self.chat()
        self.assertFalse(c["pending"])
        self.assertTrue(c["error"])
        self.assertEqual(self.send("Zadanie A", "Jeszcze raz")[0], 202)
        self.settle()

    def test_dawna_rozmowa_o_zadaniu_do_odczytu(self):
        t = self.task("Zadanie A")
        path = self.manager._chat_file(t)
        os.makedirs(os.path.dirname(path))
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"session": "s", "pending": False, "error": "",
                       "messages": [{"role": "ty", "text": "Stare pytanie", "at": ""},
                                    {"role": "claude", "text": "Stara odpowiedź", "at": ""}]}, f)
        status, body = self.request("GET", "/api/task/chat?id=" + quote(t["id"]))
        self.assertEqual(status, 200)
        self.assertEqual([m["text"] for m in body["messages"]], ["Stare pytanie", "Stara odpowiedź"])
        status, _ = self.request("POST", "/api/task/chat", {"id": t["id"], "title": t["title"], "message": "Nowe"})
        self.assertEqual(status, 404)                                     # czatu przy zadaniu już nie ma
        self.assertFalse(hasattr(self.manager, "chat_send"))
        self.assertEqual(self.calls(), [])

    def test_serwer(self):
        t = self.task("Zadanie A")
        status, body = self.request("POST", "/api/project/chat", {"project": self.pid, "task": t["id"], "message": "ą" * 2000})
        self.assertEqual((status, body), (202, {"ok": True, "error": "", "pending": True}))
        self.wait_for(lambda: not self.request("GET", "/api/project/chat?project=" + quote(self.pid))[1]["pending"])
        status, body = self.request("GET", "/api/project/chat?project=" + quote(self.pid))
        self.assertEqual(status, 200)
        self.assertEqual(body["error"], "")
        self.assertEqual([m["role"] for m in body["messages"]], ["ty", "claude"])
        self.assertEqual(body["messages"][0]["text"], "ą" * 2000)
        self.assertEqual(body["messages"][0]["task"]["id"], t["id"])
        status, body = self.request("POST", "/api/project/chat", {"project": self.pid, "message": ""})
        self.assertEqual(status, 400)
        status, body = self.request("POST", "/api/project/chat", {"project": self.pid, "message": "x" * 40000})
        self.assertEqual(status, 400)                       # treść ponad 32 KB: nieprawidłowe żądanie
        status, _ = self.request("POST", "/api/agent/stop", {"id": "x" * 5000})
        self.assertEqual(status, 400)                       # pozostałe żądania: nadal najwyżej 4 KB

    def test_rozmowa_o_projekcie(self):
        pid = self.pid
        self.assertEqual(self.manager.project_chat_send(pid, "Co mam zrobić jutro?"), (202, "", {"pending": True}))
        self.assertEqual(self.manager.project_chat_send(pid, "Druga"), (409, "Czekam jeszcze na odpowiedź.", {}))
        self.wait_for(lambda: not self.manager.project_chat_get(pid)[2]["pending"])
        c = self.manager.project_chat_get(pid)[2]
        self.assertEqual(([m["role"] for m in c["messages"]], c["error"]), (["ty", "claude"], ""))
        self.assertEqual(self.manager.project_chat_get("obcy")[0], 404)
        self.assertEqual(self.manager.project_chat_send(pid, " ")[0], 400)
        status, body = self.request("GET", "/api/project/chat?project=" + quote(pid))
        self.assertEqual((status, len(body["messages"])), (200, 2))
        status, body = self.request("POST", "/api/project/chat", {"project": pid, "message": "Anuluj zadanie B"})
        self.assertEqual((status, body["pending"]), (202, True))


if __name__ == "__main__":
    import unittest
    unittest.main()
