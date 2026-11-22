"""Google Drive projektu tylko do odczytu (rclone), podłączany przyciskiem w panelu, także z telefonu.

Przepływ: start(pid, link) uruchamia `rclone config create drive-<pid> drive scope=drive.readonly root_folder_id=<id>`
(rclone czeka na kod na 127.0.0.1:53682) i oddaje adres strony logowania Google. Po zalogowaniu przeglądarka trafia
na http://127.0.0.1:53682/?state=…&code=… (strona się nie otwiera); właściciel wkleja ten adres, finish() sprawdza go
i przekazuje rclone na serwerze. Potem pomocnik roota (drive-wlacz, sudo) montuje folder tylko do odczytu
w szkice/<karta>/media/drive (usługa drive@<pid>). Token zostaje w konfiguracji rclone użytkownika panel (0600);
moduł nigdy nie wypisuje wyjścia rclone poza adresem logowania. Instalacja: uruchom/serwer/zainstaluj-drive.sh.
"""
import http.client
import json
import os
import re
import shutil
import subprocess
import threading
import time
import urllib.parse

PORT = 53682
LOGIN_TTL = 600                     # s na zalogowanie; potem rclone jest zatrzymywany
FOLDER_RE = re.compile(r"^[A-Za-z0-9_-]{10,200}$")
PID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
BACK_KEYS = {"state", "code", "scope", "authuser", "prompt", "hd", "iss"}


def folder_id(link):
    """Id folderu z linku Google Drive (…/folders/<id>, ?id=<id>) albo samo id; '' gdy niepoprawne."""
    s = str(link or "").strip()
    m = re.search(r"/folders/([A-Za-z0-9_-]+)", s) or re.search(r"[?&]id=([A-Za-z0-9_-]+)", s)
    fid = m.group(1) if m else s
    return fid if FOLDER_RE.match(fid) else ""


def back_query(url, state, port=PORT):
    """Zapytanie z adresu powrotu po zalogowaniu (http://127.0.0.1:<port>/?state=…&code=…) albo None."""
    try:
        u = urllib.parse.urlsplit(str(url or "").strip())
        uport = u.port
    except ValueError:
        return None
    if u.scheme != "http" or u.hostname not in ("127.0.0.1", "localhost") or uport != port or u.path not in ("", "/"):
        return None
    q = urllib.parse.parse_qs(u.query, keep_blank_values=True)
    if not q or set(q) - BACK_KEYS or any(len(v) != 1 for v in q.values()):
        return None
    if not state or q.get("state", [""])[0] != state or not q.get("code", [""])[0]:
        return None
    return urllib.parse.urlencode({k: v[0] for k, v in q.items()})


class Drive:
    """Połączenia Google Drive projektów. card_dir: funkcja pid -> folder karty albo None."""

    def __init__(self, card_dir, rclone=None, helper=None, conf=None, data_dir=None, port=PORT):
        self.card_dir = card_dir
        self.rclone = rclone if rclone is not None else (shutil.which("rclone") or "")
        self.helper = helper or ["sudo", "-n", "/usr/local/bin/drive-wlacz"]
        self.conf = conf or os.path.expanduser("~/.config/rclone/rclone.conf")
        self.data_dir = data_dir or os.path.expanduser("~/dane/drive")
        self.port = port
        self.lock = threading.Lock()
        self.login = None               # {"pid", "proc", "state", "folder", "at"}

    # ---------- pomocnicze ----------
    def _rc(self, *args, timeout=30):
        return subprocess.run([self.rclone, "--config", self.conf, *args], stdin=subprocess.DEVNULL,
                              capture_output=True, text=True, timeout=timeout)

    def _remotes(self):
        try:
            r = self._rc("listremotes")
        except (OSError, subprocess.SubprocessError):
            return set()
        return {x.strip().rstrip(":") for x in r.stdout.splitlines() if x.strip()}

    def _side(self, pid):
        return os.path.join(self.data_dir, pid + ".json")

    def _mnt(self, pid):
        card = self.card_dir(pid)
        return os.path.join(card, "media", "drive") if card else ""

    def _helper(self, *args):
        try:
            r = subprocess.run(self.helper + list(args), stdin=subprocess.DEVNULL, capture_output=True, text=True,
                               timeout=60)
        except (OSError, subprocess.SubprocessError) as e:
            return False, str(e)[:200]
        return r.returncode == 0, (r.stdout + r.stderr).strip()[-200:]

    def _connected(self, pid):
        """Połączony = udane logowanie (plik dane/drive/<pid>.json) i wpis drive-<pid> w konfiguracji rclone.
        rclone zapisuje wpis już przed zalogowaniem, więc sam wpis niczego nie znaczy."""
        return os.path.exists(self._side(pid)) and ("drive-" + pid) in self._remotes()

    def _drop_remote(self, pid):
        try:
            self._rc("config", "delete", "drive-" + pid)
        except (OSError, subprocess.SubprocessError):
            pass

    def _stop_login(self, drop=True):
        """Wywołanie pod self.lock. drop: usuń niedokończony wpis rclone (logowanie przerwane)."""
        lg, self.login = self.login, None
        if not lg:
            return
        if lg["proc"].poll() is None:
            lg["proc"].kill()
        try:
            lg["proc"].wait(timeout=5)
        except subprocess.SubprocessError:
            pass
        if lg["proc"].stdout:
            try:
                lg["proc"].stdout.close()
            except OSError:
                pass
        if drop and not os.path.exists(self._side(lg["pid"])):
            self._drop_remote(lg["pid"])

    def _check(self, pid):
        pid = str(pid or "")
        if not PID_RE.match(pid) or not self.card_dir(pid):
            return None, (404, "Nie ma tego projektu.", {})
        if not self.rclone:
            return None, (409, "Na serwerze brakuje rclone (uruchom/serwer/zainstaluj-drive.sh).", {})
        return pid, None

    # ---------- API ----------
    def status(self, pid):
        pid = str(pid or "")
        if not PID_RE.match(pid) or not self.card_dir(pid):
            return 404, "Nie ma tego projektu.", {}
        out = {"available": bool(self.rclone), "connected": False, "mounted": False, "files": None, "folder": "",
               "login": False}
        if not self.rclone:
            return 200, "", out
        out["connected"] = self._connected(pid)
        try:
            with open(self._side(pid), encoding="utf-8") as f:
                out["folder"] = str(json.load(f).get("folder") or "")
        except (OSError, ValueError, AttributeError):
            pass
        mnt = self._mnt(pid)
        out["mounted"] = bool(mnt) and os.path.ismount(mnt)
        if out["mounted"]:
            try:
                out["files"] = sum(1 for e in os.scandir(mnt) if not e.name.startswith("."))
            except OSError:
                out["files"] = None
        with self.lock:
            lg = self.login
            if lg and (lg["proc"].poll() is not None or time.time() - lg["at"] > LOGIN_TTL):
                self._stop_login()
                lg = None
            out["login"] = bool(lg and lg["pid"] == pid)
            if out["login"]:
                out["loginUrl"] = lg["url"]
        return 200, "", out

    def start(self, pid, link):
        pid, err = self._check(pid)
        if err:
            return err
        fid = folder_id(link)
        if not fid:
            return 400, "Wklej link do folderu na Google Drive (…/drive/folders/…).", {}
        if self._connected(pid):
            return 409, "Ten projekt ma już połączony Drive. Najpierw odłącz.", {}
        with self.lock:
            lg = self.login
            if lg and lg["proc"].poll() is None and time.time() - lg["at"] < LOGIN_TTL and lg["pid"] != pid:
                return 409, "Trwa logowanie Drive w innym projekcie. Spróbuj za kilka minut.", {}
            self._stop_login()
            if ("drive-" + pid) in self._remotes():
                self._drop_remote(pid)                  # wpis po przerwanym logowaniu
            os.makedirs(os.path.dirname(self.conf), mode=0o700, exist_ok=True)
            proc = subprocess.Popen([self.rclone, "--config", self.conf, "config", "create", "drive-" + pid, "drive",
                                     "scope=drive.readonly", "root_folder_id=" + fid], stdin=subprocess.DEVNULL,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace")
            found = {}
            pat = re.compile(r"http://127\.0\.0\.1:%d/auth\?state=([\w-]+)" % self.port)

            def read():
                try:
                    for line in proc.stdout:            # reszta wyjścia (z tokenem na końcu) nie jest zapisywana
                        m = pat.search(line)
                        if m and "state" not in found:
                            found["state"] = m.group(1)
                except (OSError, ValueError):            # wyjście zamknięte przez _stop_login
                    pass
            threading.Thread(target=read, daemon=True).start()
            end = time.time() + 20
            while "state" not in found and time.time() < end and proc.poll() is None:
                time.sleep(0.1)
            if "state" not in found:
                self.login = {"proc": proc, "pid": pid, "at": time.time(), "state": "", "url": ""}
                self._stop_login()
                return 500, "rclone nie podał adresu logowania.", {}
            url = self._google_url(found["state"])
            if not url:
                self.login = {"proc": proc, "pid": pid, "at": time.time(), "state": "", "url": ""}
                self._stop_login()
                return 500, "Nie udało się otworzyć logowania Google.", {}
            self.login = {"proc": proc, "pid": pid, "at": time.time(), "state": found["state"], "folder": fid,
                          "url": url}
        return 200, "", {"loginUrl": url}

    def _google_url(self, state):
        try:
            c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
            c.request("GET", "/auth?state=" + urllib.parse.quote(state))
            r = c.getresponse()
            loc = r.getheader("Location") or ""
            c.close()
        except (OSError, http.client.HTTPException):
            return ""
        return loc if 300 <= r.status < 400 and loc.startswith("https://accounts.google.com/") else ""

    def finish(self, pid, url):
        pid, err = self._check(pid)
        if err:
            return err
        with self.lock:
            lg = self.login
            if not lg or lg["pid"] != pid or lg["proc"].poll() is not None:
                return 409, "Logowanie wygasło. Kliknij „Połącz Google Drive” jeszcze raz.", {}
            q = back_query(url, lg["state"], self.port)
            if q is None:
                return 400, "To nie jest adres po zalogowaniu. Skopiuj cały adres z paska (http://127.0.0.1:%d/?state=…)." % self.port, {}
            try:
                c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
                c.request("GET", "/?" + q)
                c.getresponse().read()
                c.close()
            except (OSError, http.client.HTTPException):
                pass
            try:
                lg["proc"].wait(timeout=60)
            except subprocess.SubprocessError:
                pass
            folder, done = lg["folder"], lg["proc"].returncode == 0
            if not done or ("drive-" + pid) not in self._remotes():
                self._stop_login()                      # usuwa niedokończony wpis
                return 500, "Google nie potwierdził logowania. Spróbuj jeszcze raz.", {}
            self._stop_login(drop=False)
        try:
            os.chmod(self.conf, 0o600)
        except OSError:
            pass
        os.makedirs(self.data_dir, exist_ok=True)
        with open(self._side(pid), "w", encoding="utf-8") as f:
            json.dump({"folder": folder, "at": time.strftime("%Y-%m-%dT%H:%M:%S")}, f)
        ok, msg = self._helper(pid, self.card_dir(pid))
        if not ok:
            return 500, "Połączono, ale montowanie nieudane: %s" % msg, {}
        return 200, "", {}

    def mount(self, pid):
        pid, err = self._check(pid)
        if err:
            return err
        if not self._connected(pid):
            return 409, "Drive nie jest połączony.", {}
        ok, msg = self._helper(pid, self.card_dir(pid))
        return (200, "", {}) if ok else (500, "Montowanie nieudane: %s" % msg, {})

    def cancel(self, pid):
        with self.lock:
            if self.login and self.login["pid"] == str(pid or ""):
                self._stop_login()
        return 200, "", {}

    def disconnect(self, pid):
        pid, err = self._check(pid)
        if err:
            return err
        ok, msg = self._helper("--wylacz", pid)
        if not ok:
            return 500, "Nie odłączono: %s" % msg, {}
        try:
            self._rc("config", "delete", "drive-" + pid)
        except (OSError, subprocess.SubprocessError):
            return 500, "Odmontowano, ale nie usunięto połączenia.", {}
        try:
            os.remove(self._side(pid))
        except OSError:
            pass
        return 200, "", {}
