"""Stała sesja asystenta: jeden długo żyjący proces `claude -p --input-format stream-json --output-format stream-json`.

Nowe `claude -p` na każdą wiadomość startuje kilka sekund; stała sesja daje pierwsze słowa po ok. 1 s. Wiadomość to
wiersz {"type":"user","message":{"role":"user","content":"…"}} na stdin, odpowiedź to zdarzenia stream_event
(text_delta: kolejne kawałki tekstu, content_block_start z tool_use: asystent czyta albo zmienia pliki) zakończone
zdarzeniem result. Proces kończy się po IDLE sekundach bez wiadomości; następna wiadomość wznawia rozmowę (--resume).
"""
import collections
import json
import os
import queue
import signal
import subprocess
import sys
import threading
import time

IDLE = 1800                 # s bez wiadomości: proces kończy pracę (zwalnia pamięć serwera)
WINDOWS = sys.platform == "win32"
# Narzędzie -> co widzi właściciel, gdy asystent go używa.
TOOL_LABEL = {"Read": "Czytam pliki projektu", "Grep": "Szukam w plikach", "Glob": "Szukam plików", "LS": "Szukam plików",
              "Edit": "Zmieniam zadanie", "Write": "Zmieniam zadanie", "MultiEdit": "Zmieniam zadanie"}


class Session:
    def __init__(self, idle=IDLE, on_rate=None):
        self.idle = idle
        self.on_rate = on_rate
        self.key = ""
        self.resumed = False          # proces wystartował z --resume (wygasła sesja: błąd przy pierwszej wiadomości)
        self._proc = None
        self._events = None
        self._err = collections.deque(maxlen=40)
        self._busy = False
        self._used = 0.0
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._watch = None

    def alive(self, key=None):
        p = self._proc
        return p is not None and p.poll() is None and (key is None or key == self.key)

    def start(self, args, cwd, env, key, resumed=False):
        """Nowy proces (poprzedni zostaje zamknięty). OSError, gdy polecenia nie da się uruchomić."""
        self.stop(keep_watch=True)
        events, err = queue.Queue(), collections.deque(maxlen=40)
        kw = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if WINDOWS else {"start_new_session": True}
        proc = subprocess.Popen(args, cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                env=env, encoding="utf-8", errors="replace", bufsize=1, **kw)

        def out_reader():
            try:
                for line in proc.stdout:
                    if self.on_rate and '"rate_limit_event"' in line:
                        try:
                            event = json.loads(line)
                            if isinstance(event, dict) and event.get("type") == "rate_limit_event":
                                self.on_rate(event)
                        except (TypeError, ValueError, AttributeError):
                            pass
                    events.put(line)
            except (OSError, ValueError):
                pass
            events.put(None)

        def err_reader():
            try:
                for line in proc.stderr:
                    err.append(line[:500])
            except (OSError, ValueError):
                pass
        threading.Thread(target=out_reader, daemon=True).start()
        threading.Thread(target=err_reader, daemon=True).start()
        with self._lock:
            self._proc, self._events, self._err = proc, events, err
            self.key, self.resumed, self._used = key, resumed, time.time()
        self._ensure_watch()

    def turn(self, text, on_text=None, on_tool=None, timeout=180):
        """Jedna wiadomość i odpowiedź. Zwraca {"ok", "text", "session", "error", "blob", "code"}:
        ok=True gdy przyszło zdarzenie result bez błędu; blob to wyjście do rozpoznania przyczyny błędu."""
        proc, events = self._proc, self._events
        res = {"ok": False, "text": "", "session": "", "error": "", "blob": "", "code": None}
        if proc is None or proc.poll() is not None:
            res["error"] = "proces"
            return res
        self._busy, self._used = True, time.time()
        noise = []
        try:
            while True:                      # resztki poprzedniej tury (np. zdarzenia po result)
                try:
                    if events.get_nowait() is None:
                        res["error"] = "proces"
                        return self._fail(res, proc, noise)
                except queue.Empty:
                    break
            line = json.dumps({"type": "user", "message": {"role": "user", "content": text}}, ensure_ascii=False)
            try:
                proc.stdin.write(line + "\n")
                proc.stdin.flush()
            except (OSError, ValueError):
                res["error"] = "proces"
                return self._fail(res, proc, noise)
            parts, end = [], time.time() + timeout
            while True:
                left = end - time.time()
                if left <= 0:
                    res["error"] = "czas"
                    self.stop(keep_watch=True)
                    return res
                try:
                    raw = events.get(timeout=left)
                except queue.Empty:
                    continue
                if raw is None:
                    res["error"] = "proces"
                    return self._fail(res, proc, noise)
                try:
                    ev = json.loads(raw)
                except ValueError:
                    noise.append(raw[:500])
                    continue
                if not isinstance(ev, dict):
                    continue
                kind = ev.get("type")
                if ev.get("session_id"):
                    res["session"] = str(ev["session_id"])
                if kind == "stream_event":
                    e = ev.get("event") or {}
                    et = e.get("type")
                    if et == "message_start" and parts and not parts[-1].endswith("\n\n"):
                        parts.append("\n\n")
                        if on_text:
                            on_text("".join(parts))
                    elif et == "content_block_start":
                        block = e.get("content_block") or {}
                        if block.get("type") == "tool_use" and on_tool:
                            on_tool(TOOL_LABEL.get(block.get("name"), "Sprawdzam"))
                    elif et == "content_block_delta":
                        d = e.get("delta") or {}
                        if d.get("type") == "text_delta" and d.get("text"):
                            parts.append(str(d["text"]))
                            if on_text:
                                on_text("".join(parts))
                elif kind == "result":
                    final = str(ev.get("result") or "").strip()
                    res["text"] = final or "".join(parts).strip()
                    if ev.get("is_error") or not res["text"]:
                        res["error"] = "wynik"
                        res["blob"] = " ".join([final, str(ev.get("api_error_status") or "")] + noise[-5:])
                        return res
                    res["ok"] = True
                    self.resumed = False
                    return res
        finally:
            self._busy, self._used = False, time.time()

    def _fail(self, res, proc, noise):
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            pass
        res["code"] = proc.poll()
        time.sleep(0.05)                     # ostatnie wiersze stderr
        res["blob"] = " ".join(noise[-10:] + list(self._err)[-10:])
        self.stop(keep_watch=True)
        return res

    def _ensure_watch(self):
        if self._watch and self._watch.is_alive():
            return

        def watch():
            step = max(0.05, min(60.0, self.idle / 4))
            while not self._stop.wait(step):
                if self.alive() and not self._busy and time.time() - self._used > self.idle:
                    self.stop(keep_watch=True)
        self._watch = threading.Thread(target=watch, daemon=True)
        self._watch.start()

    def stop(self, keep_watch=False):
        if not keep_watch:
            self._stop.set()
        with self._lock:
            proc, self._proc = self._proc, None
            self.key = ""
        if proc is None:
            return
        try:
            proc.stdin.close()               # koniec wejścia: CLI kończy pracę samo
        except (OSError, ValueError):
            pass
        try:
            proc.wait(timeout=3)
            return self._close(proc)
        except subprocess.TimeoutExpired:
            pass
        try:
            if WINDOWS:
                proc.kill()
            else:
                os.killpg(proc.pid, signal.SIGTERM)
            proc.wait(timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            try:
                if not WINDOWS:
                    os.killpg(proc.pid, signal.SIGKILL)
            except OSError:
                pass
        self._close(proc)

    @staticmethod
    def _close(proc):
        if proc.poll() is None:
            return
        time.sleep(0.05)                     # czytające wątki kończą na końcu strumienia
        for f in (proc.stdout, proc.stderr):
            try:
                f.close()
            except (OSError, ValueError):
                pass
