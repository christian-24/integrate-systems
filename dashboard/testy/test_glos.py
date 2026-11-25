"""Głos asystenta: pracownik rozpoznawania mowy (atrapa bez faster-whisper), trasa POST /api/asystent/glos
(typ, rozmiar, brak rozpoznawania), wczytanie przy pierwszym użyciu i koniec po bezczynności."""
import http.client
import json
import os
import sys
import threading
import time
import unittest
from http.server import ThreadingHTTPServer

from wspolne import Baza, server

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import glos  # noqa: E402

WEBM = b"\x1a\x45\xdf\xa3" + b"\0" * 96
MP4 = b"\0\0\0\x20ftypisom" + b"\0" * 96


def recognizer(mode="1", **kw):
    return glos.Recognizer({"PANEL_GLOS_PYTHON": sys.executable, "GLOS_ATRAPA": mode, "PATH": os.environ.get("PATH", "")},
                           **kw)


class Pracownik(unittest.TestCase):
    def test_rozpoznaje_i_konczy_po_bezczynnosci(self):
        r = recognizer(idle=0.4)
        try:
            self.assertTrue(r.available())
            self.assertFalse(r.running())                 # model dopiero przy pierwszym użyciu
            self.assertEqual(r.transcribe(WEBM + "|Pokaż marketing".encode(), ".webm", "Projekty: Alfa"),
                             (200, "", "Pokaż marketing"))
            self.assertTrue(r.running())
            self.assertEqual(r.transcribe(MP4 + "|drugie".encode(), ".mp4")[2], "drugie")   # ten sam proces
            end = time.time() + 5
            while r.running() and time.time() < end:
                time.sleep(0.05)
            self.assertFalse(r.running())                 # pamięć zwolniona po bezczynności
            self.assertEqual(r.transcribe(WEBM + b"|znowu", ".webm")[2], "znowu")   # i znowu startuje
        finally:
            r.stop()

    def test_brak_faster_whisper(self):
        r = recognizer("brak")
        try:
            code, err, text = r.transcribe(WEBM + b"|x", ".webm")
            self.assertEqual((code, text), (409, ""))
            self.assertIn("nie jest zainstalowane", err)
            self.assertFalse(r.available())               # panel chowa mikrofon
        finally:
            r.stop()

    def test_bez_interpretera(self):
        r = glos.Recognizer({})
        self.assertFalse(r.available())
        self.assertEqual(r.transcribe(WEBM, ".webm")[0], 409)

    def test_rozgrzewka(self):
        r = recognizer()
        try:
            r.warm()
            end = time.time() + 10
            while not r.running() and time.time() < end:
                time.sleep(0.05)
            self.assertTrue(r.running())
        finally:
            r.stop()
        self.assertFalse(r.running())

    def test_sprawdzenie_nagrania(self):
        self.assertEqual(glos.check_audio("audio/webm;codecs=opus", WEBM), (".webm", ""))
        self.assertEqual(glos.check_audio("audio/mp4", MP4), (".mp4", ""))
        self.assertIn("Nieobsługiwany", glos.check_audio("text/plain", WEBM)[1])
        self.assertIn("puste", glos.check_audio("audio/webm", b"")[1])
        self.assertIn("nie jest nagraniem", glos.check_audio("audio/webm", MP4)[1])
        self.assertIn("za długie", glos.check_audio("audio/webm", WEBM + b"\0" * glos.AUDIO_MAX)[1])


class Trasa(Baza):
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

    def use(self, **extra):
        server._agents = self.manager = self.new_manager(**extra)

    def post_audio(self, data, ctype="audio/webm", query="?view=%23ty", length=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=20)
        try:
            conn.putrequest("POST", "/api/asystent/glos" + query)
            conn.putheader("Content-Type", ctype)
            conn.putheader("Content-Length", str(len(data) if length is None else length))
            conn.endheaders()
            if length is None:
                conn.send(data)
            resp = conn.getresponse()
            return resp.status, json.loads(resp.read().decode("utf-8"))
        finally:
            conn.close()

    def get(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        try:
            conn.request("GET", "/api/asystent")
            resp = conn.getresponse()
            return json.loads(resp.read().decode("utf-8"))
        finally:
            conn.close()

    def test_nagranie_do_asystenta(self):
        self.use(PANEL_GLOS_PYTHON=sys.executable, GLOS_ATRAPA="1")
        self.assertTrue(self.get()["voice"])
        status, body = self.post_audio(WEBM + "|Co mam dziś zrobić?".encode())
        self.assertEqual(status, 202, body)
        self.assertEqual(body["text"], "Co mam dziś zrobić?")
        self.wait_for(lambda: not self.get()["pending"])
        msgs = self.get()["messages"]
        self.assertEqual([m["role"] for m in msgs], ["ty", "claude"])
        self.assertEqual(msgs[0]["text"], "Co mam dziś zrobić?")
        prompt = [c for c in self.calls() if c.get("stream")][0]["prompt"]
        self.assertIn("[ekran: #ty]", prompt)

    def test_transkrypcja_do_pola_rozmowy(self):
        self.use(PANEL_GLOS_PYTHON=sys.executable, GLOS_ATRAPA="1")
        text = "Zmień kolor nagłówka."
        status, body = self.post_audio(MP4 + ("|" + text).encode(), ctype="audio/mp4", query="?draft=1")
        self.assertEqual(status, 200, body)
        self.assertEqual(body["text"], text)
        self.assertTrue(self.manager.voice.running())
        self.assertEqual(self.get()["messages"], [])
        self.assertEqual(self.calls(), [])

    def test_typ_rozmiar_i_puste(self):
        self.use(PANEL_GLOS_PYTHON=sys.executable, GLOS_ATRAPA="1")
        self.assertEqual(self.post_audio(WEBM + b"|x", ctype="application/json")[0], 400)
        self.assertEqual(self.post_audio(WEBM + b"|x", ctype="text/plain")[0], 400)
        status, body = self.post_audio(b"", length=glos.AUDIO_MAX + 1)
        self.assertEqual(status, 400)
        self.assertIn("Nagranie do 4 MB", body["error"])
        self.assertEqual(self.post_audio(MP4 + b"|x")[0], 400)                 # webm w nagłówku, mp4 w pliku
        status, body = self.post_audio(WEBM + b"|   ")
        self.assertEqual(status, 422)                                          # nic nie rozpoznano
        self.assertEqual(self.calls(), [])                                     # do asystenta nic nie poszło

    def test_bez_rozpoznawania(self):
        self.use(PANEL_GLOS_PYTHON="")
        self.assertFalse(self.get()["voice"])
        status, body = self.post_audio(WEBM + b"|x")
        self.assertEqual(status, 409)
        self.assertFalse(body["voice"])
        self.use(PANEL_GLOS_PYTHON=sys.executable, GLOS_ATRAPA="brak")
        status, body = self.post_audio(WEBM + b"|x")
        self.assertEqual(status, 409)
        self.assertFalse(self.get()["voice"])


if __name__ == "__main__":
    unittest.main()
