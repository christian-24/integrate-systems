"""Rozpoznawanie mowy dla asystenta: panel (stdlib) rozmawia z pracownikiem glos_stt.py przez stdin/stdout.

Pracownik działa interpreterem z PANEL_GLOS_PYTHON (venv z faster-whisper, uruchom/serwer/zainstaluj-glos.sh).
Startuje przy pierwszym nagraniu (albo wcześniej: warm() przy naciśnięciu „Mów”, model wczytuje się, gdy właściciel
mówi) i kończy się sam po GLOS_IDLE sekundach bezczynności, żeby nie trzymać modelu w pamięci serwera.
"""
import json
import os
import queue
import subprocess
import sys
import tempfile
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
WORKER = os.path.join(HERE, "glos_stt.py")
AUDIO_MAX = 4 * 1024 * 1024        # bajtów nagrania (minuta mowy w opus to ok. 0,3 MB)
GLOS_IDLE = 600                    # s bez nagrania: pracownik kończy pracę
START_TIMEOUT = 180                # s na wczytanie modelu (pierwsze użycie bez pobranego modelu: pobranie)
RUN_TIMEOUT = 90                   # s na jedno nagranie
RETRY_AFTER = 600                  # s: po nieudanym starcie (brak pakietu) następna próba dopiero po tym czasie
# Typ z nagłówka -> (rodzaj, rozszerzenie). Rodzaj sprawdzamy też po pierwszych bajtach pliku.
TYPES = {"audio/webm": ("webm", ".webm"), "video/webm": ("webm", ".webm"), "audio/mp4": ("mp4", ".mp4"),
         "audio/x-m4a": ("mp4", ".m4a"), "audio/m4a": ("mp4", ".m4a"), "audio/aac": ("mp4", ".m4a"),
         "video/mp4": ("mp4", ".mp4"), "audio/ogg": ("ogg", ".ogg"), "audio/wav": ("wav", ".wav"),
         "audio/x-wav": ("wav", ".wav"), "audio/wave": ("wav", ".wav")}
UNAVAILABLE = "Rozpoznawanie mowy nie jest zainstalowane na serwerze."


def audio_kind(data):
    if data[:4] == b"\x1a\x45\xdf\xa3":
        return "webm"
    if data[4:8] == b"ftyp":
        return "mp4"
    if data[:4] == b"OggS":
        return "ogg"
    if data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return "wav"
    return ""


def check_audio(ctype, data):
    """(rozszerzenie, błąd): nagranie z przeglądarki (webm z Chrome, mp4 z Safari) o rozsądnym rozmiarze."""
    ctype = (ctype or "").split(";")[0].strip().lower()
    if ctype not in TYPES:
        return "", "Nieobsługiwany format nagrania (%s)." % (ctype or "brak typu")
    if not data or len(data) < 64:
        return "", "Nagranie jest puste."
    if len(data) > AUDIO_MAX:
        return "", "Nagranie za długie (najwyżej %d MB)." % (AUDIO_MAX // (1 << 20))
    kind, ext = TYPES[ctype]
    if audio_kind(data) != kind:
        return "", "Plik nie jest nagraniem %s." % kind
    return ext, ""


def worker_env(env):
    """Środowisko pracownika: bez haseł panelu i kluczy (nie są mu potrzebne)."""
    out = {}
    for k, v in env.items():
        up = k.upper()
        if up in ("PANEL_TOKEN", "PANEL_NTFY_URL", "OPENAI_API_KEY") or up.startswith("ANTHROPIC_") or up.startswith("CLAUDE"):
            continue
        out[k] = v
    return out


class Recognizer:
    def __init__(self, env=None, idle=GLOS_IDLE, script=WORKER):
        self.env = dict(os.environ if env is None else env)
        self.python = os.path.expanduser((self.env.get("PANEL_GLOS_PYTHON") or "").strip())
        self.script = script
        self.idle = idle
        self._lock = threading.Lock()        # jedno nagranie naraz i jeden start pracownika
        self._proc = None
        self._lines = None
        self._used = 0.0
        self._failed, self._failed_at = "", 0.0
        self._seq = 0
        self._watch = None
        self._stop = threading.Event()

    # ---------- stan ----------
    def available(self):
        if not self.python or not os.path.isfile(self.python):
            return False
        return not (self._failed and time.time() - self._failed_at < RETRY_AFTER)

    def running(self):
        p = self._proc
        return p is not None and p.poll() is None

    # ---------- proces pracownika ----------
    def _start(self):
        """Pod self._lock. '' gdy pracownik gotowy, inaczej opis błędu."""
        if self.running():
            return ""
        lines = queue.Queue()
        kw = {} if sys.platform == "win32" else {"start_new_session": True}
        try:
            proc = subprocess.Popen([self.python, self.script], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                    stderr=subprocess.DEVNULL, cwd=os.path.dirname(self.script),
                                    env=worker_env(self.env), encoding="utf-8", errors="replace", bufsize=1, **kw)
        except OSError as e:
            return "Nie udało się uruchomić rozpoznawania mowy (%s)." % e.strerror

        def reader():
            try:
                for line in proc.stdout:
                    lines.put(line)
            except (OSError, ValueError):
                pass
            lines.put(None)
        threading.Thread(target=reader, daemon=True).start()
        self._proc, self._lines, self._used = proc, lines, time.time()
        first = self._read(START_TIMEOUT)
        if not first or first.get("gotowy") is not True:
            why = (first or {}).get("blad") or "pracownik nie odpowiedział"
            self._kill()
            self._failed, self._failed_at = why, time.time()
            return "%s (%s)" % (UNAVAILABLE, why) if "faster" in why.lower() or "import" in why.lower() \
                else "Rozpoznawanie mowy nie wystartowało (%s)." % why
        self._failed = ""
        self._ensure_watch()
        return ""

    def _read(self, timeout, rid=None):
        """Następny obiekt JSON od pracownika (z danym id, gdy podane) albo None (koniec procesu, czas)."""
        end = time.time() + timeout
        while True:
            left = end - time.time()
            if left <= 0:
                return None
            try:
                line = self._lines.get(timeout=left)
            except queue.Empty:
                return None
            if line is None:
                return None
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            if isinstance(obj, dict) and (rid is None or obj.get("id") == rid):
                return obj

    def _kill(self):
        proc, self._proc = self._proc, None
        if proc is None:
            return
        try:
            proc.stdin.close()
        except OSError:
            pass
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                pass
        for f in (proc.stdout,):
            try:
                f.close()
            except (OSError, ValueError):
                pass

    def _ensure_watch(self):
        if self._watch and self._watch.is_alive():
            return

        def watch():
            step = max(0.05, min(30.0, self.idle / 4))
            while not self._stop.wait(step):
                if self._proc is None:
                    break
                if time.time() - self._used > self.idle and self._lock.acquire(blocking=False):
                    try:
                        if time.time() - self._used > self.idle:
                            self._kill()
                    finally:
                        self._lock.release()
        self._watch = threading.Thread(target=watch, daemon=True)
        self._watch.start()

    # ---------- API ----------
    def warm(self):
        """Start pracownika w tle (naciśnięcie „Mów”): model wczytuje się, gdy właściciel mówi."""
        if not self.available() or self.running():
            return

        def go():
            if self._lock.acquire(timeout=1):
                try:
                    self._start()
                finally:
                    self._lock.release()
        threading.Thread(target=go, daemon=True).start()

    def transcribe(self, data, ext, prompt=""):
        """(kod, błąd, tekst). 409 gdy rozpoznawanie niedostępne albo zajęte."""
        if not self.available():
            return 409, UNAVAILABLE, ""
        if not self._lock.acquire(timeout=60):
            return 409, "Rozpoznaję poprzednie nagranie. Spróbuj za chwilę.", ""
        path = ""
        try:
            err = self._start()
            if err:
                return 409, err, ""
            fd, path = tempfile.mkstemp(prefix="glos-", suffix=ext)
            with os.fdopen(fd, "wb") as f:
                f.write(data)
            self._seq += 1
            rid = self._seq
            try:
                self._proc.stdin.write(json.dumps({"id": rid, "plik": path, "podpowiedz": prompt},
                                                  ensure_ascii=False) + "\n")
                self._proc.stdin.flush()
            except (OSError, ValueError):
                self._kill()
                return 500, "Rozpoznawanie mowy przerwane. Spróbuj jeszcze raz.", ""
            res = self._read(RUN_TIMEOUT, rid)
            self._used = time.time()
            if res is None:
                self._kill()
                return 500, "Rozpoznawanie mowy nie odpowiedziało. Spróbuj jeszcze raz.", ""
            if res.get("blad"):
                return 422, "Nie udało się odczytać nagrania.", ""
            return 200, "", str(res.get("tekst") or "").strip()
        finally:
            if path:
                try:
                    os.unlink(path)
                except OSError:
                    pass
            self._lock.release()

    def stop(self):
        self._stop.set()
        with self._lock:
            self._kill()
