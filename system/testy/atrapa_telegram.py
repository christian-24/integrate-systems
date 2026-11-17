"""Atrapy do testów: Telegram Bot API i healthchecks na lokalnym, losowym porcie. Bez prawdziwej sieci."""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class AtrapaTelegram:
    """Serwer Bot API: kolejka aktualizacji wstrzykiwanych przez test, zapis wywołań."""

    def __init__(self, token="123:TEST"):
        self.token = token
        self.aktualizacje = []
        self.wyslane = []          # sendMessage
        self.odpowiedzi = []       # answerCallbackQuery
        self.edycje = []           # editMessageText
        self.wywolania = []        # (metoda, dane)
        self._nastepne_id = 1
        self._nastepna_wiad = 100
        self._warunek = threading.Condition()
        atrapa = self

        class Obsluga(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                dlugosc = int(self.headers.get("Content-Length") or 0)
                try:
                    dane = json.loads(self.rfile.read(dlugosc) or b"{}")
                except ValueError:
                    dane = {}
                kod, odp = atrapa._obsluz(self.path, dane)
                tresc = json.dumps(odp).encode("utf-8")
                self.send_response(kod)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(tresc)))
                self.end_headers()
                self.wfile.write(tresc)

        self.serwer = ThreadingHTTPServer(("127.0.0.1", 0), Obsluga)
        self.adres = "http://127.0.0.1:%d" % self.serwer.server_address[1]
        self._watek = threading.Thread(target=self.serwer.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        self._watek.start()

    def zamknij(self):
        self.serwer.shutdown()
        self.serwer.server_close()

    # --- obsługa API ---

    def _obsluz(self, sciezka, dane):
        prefiks = "/bot%s/" % self.token
        if not sciezka.startswith(prefiks):
            return 401, {"ok": False, "error_code": 401, "description": "Unauthorized"}
        metoda = sciezka[len(prefiks):]
        with self._warunek:
            self.wywolania.append((metoda, dane))
        if metoda == "getUpdates":
            return 200, {"ok": True, "result": self._pobierz(dane)}
        if metoda == "sendMessage":
            with self._warunek:
                self._nastepna_wiad += 1
                wiad = dict(dane, message_id=self._nastepna_wiad)
                self.wyslane.append(wiad)
            return 200, {"ok": True, "result": {"message_id": wiad["message_id"],
                                                "chat": {"id": dane.get("chat_id")}, "text": dane.get("text")}}
        if metoda == "answerCallbackQuery":
            self.odpowiedzi.append(dane)
            return 200, {"ok": True, "result": True}
        if metoda == "editMessageText":
            self.edycje.append(dane)
            return 200, {"ok": True, "result": True}
        return 404, {"ok": False, "error_code": 404, "description": "Not Found"}

    def _pobierz(self, dane):
        offset = dane.get("offset")
        czekaj = min(float(dane.get("timeout") or 0), 1.0)
        with self._warunek:
            if offset is not None:
                self.aktualizacje = [a for a in self.aktualizacje if a["update_id"] >= offset]
            if not self.aktualizacje and czekaj > 0:
                self._warunek.wait(czekaj)
            return list(self.aktualizacje)

    # --- wstrzykiwanie ---

    def wstrzyknij(self, aktualizacja):
        with self._warunek:
            aktualizacja = dict(aktualizacja, update_id=self._nastepne_id)
            self._nastepne_id += 1
            self.aktualizacje.append(aktualizacja)
            self._warunek.notify_all()
        return aktualizacja

    def tekst(self, chat_id, tekst, typ="private", imie="Test"):
        return self.wstrzyknij({"message": {"message_id": self._nastepne_id, "text": tekst,
                                            "chat": {"id": chat_id, "type": typ},
                                            "from": {"id": chat_id, "first_name": imie}}})

    def zdjecie(self, chat_id):
        return self.wstrzyknij({"message": {"message_id": self._nastepne_id,
                                            "photo": [{"file_id": "x", "width": 1, "height": 1}],
                                            "chat": {"id": chat_id, "type": "private"},
                                            "from": {"id": chat_id, "first_name": "Test"}}})

    def przycisk(self, chat_id, dane, message_id):
        return self.wstrzyknij({"callback_query": {"id": "cb%d" % self._nastepne_id, "data": dane,
                                                   "from": {"id": chat_id, "first_name": "Test"},
                                                   "message": {"message_id": message_id,
                                                               "chat": {"id": chat_id, "type": "private"}}}})

    def teksty(self):
        return [w.get("text") for w in self.wyslane]


class AtrapaHC:
    """Healthchecks: liczy żądania według ścieżki."""

    def __init__(self):
        self.pingi = []
        atrapa = self

        class Obsluga(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _ok(self):
                atrapa.pingi.append(self.path)
                self.send_response(200)
                self.send_header("Content-Length", "2")
                self.end_headers()
                self.wfile.write(b"OK")

            do_GET = _ok
            do_POST = _ok

        self.serwer = ThreadingHTTPServer(("127.0.0.1", 0), Obsluga)
        self.adres = "http://127.0.0.1:%d" % self.serwer.server_address[1]
        threading.Thread(target=self.serwer.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()

    def ile(self, sciezka):
        return self.pingi.count(sciezka)

    def zamknij(self):
        self.serwer.shutdown()
        self.serwer.server_close()
