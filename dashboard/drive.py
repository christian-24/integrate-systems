"""Google Drive tylko do odczytu (rclone): jedno połączenie na konto Google, folder z tego konta dla projektu.

Konto: start_account(nazwa) uruchamia `rclone config create gdrive-<id> drive scope=drive.readonly` (bez
root_folder_id) i oddaje adres logowania Google. Z wbudowanym klientem OAuth rclone Google wraca na
http://127.0.0.1:53682/?state=…&code=… (na telefonie i Macu ta strona się nie otwiera): właściciel wkleja ten adres raz
na konto, finish_account() przekazuje go rclone na serwerze. Z własnym klientem OAuth właściciela (plik
~/.config/integrate/google-oauth.json: client_id, client_secret, redirect_uri; panel go nie wypisuje) Google wraca
na adres panelu (GET /api/drive/powrot): panel wymienia kod na token i zapisuje wpis konta w konfiguracji rclone.

Projekt: choose(pid, konto, id folderu) zapisuje wpis `drive-<pid>` typu alias na `gdrive-<id>,root_folder_id=<folder>:`
(token zostaje tylko we wpisie konta). Usługa drive@<pid> (pomocnik roota drive-wlacz, sudo) montuje `drive-<pid>:`
tylko do odczytu w szkice/<karta>/media/drive, tak samo jak dla połączeń sprzed kont (wpis drive-<pid> typu drive
z własnym tokenem), które działają dalej. Część projektu ma własną kartę, więc może mieć własny folder.
Moduł nigdy nie wypisuje wyjścia rclone ani tokenów: błędy zamienia na jedno zdanie (reason()).
"""
import configparser
import datetime
import html
import http.client
import json
import os
import re
import secrets
import shutil
import subprocess
import tempfile
import threading
import time
import unicodedata
import urllib.parse
import urllib.request

PORT = 53682
LOGIN_TTL = 600                     # s na zalogowanie; potem rclone jest zatrzymywany
FOLDER_RE = re.compile(r"^[A-Za-z0-9_-]{10,200}$")
PID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
ACC_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,30}$")
ACC_PREFIX = "gdrive-"              # wpis rclone konta Google: gdrive-<id>
BACK_KEYS = {"state", "code", "scope", "authuser", "prompt", "hd", "iss"}
REDIRECT_URI = "https://2-29-181-133.sslip.io/api/drive/powrot"
SCOPE = "https://www.googleapis.com/auth/drive.readonly"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
MAX_FOLDERS = 5000                  # lista folderów konta (drzewo w panelu)
FOLDERS_TTL = 300                   # s pamięci listy folderów
LIST_TIMEOUT = 120

# (fragment komunikatu rclone, zdanie dla właściciela); wyjście rclone nigdy nie trafia dalej
REASONS = (
    (("didn't find section", "not found in config", "couldn't find type", "config file not found"),
     "Brak połączenia z kontem na serwerze. Połącz konto ponownie."),
    (("invalid_grant", "expired or revoked", "token expired", "unauthorized_client", "invalid_client",
      "empty token", "oauth2: cannot fetch token", "401"),
     "Google cofnął albo unieważnił dostęp. Połącz konto ponownie."),
    (("notfound", "file not found", "directory not found", "not found", "404", "insufficientpermissions", "403"),
     "Folder nie istnieje albo konto nie ma do niego dostępu."),
    (("fuse", "fusermount", "transport endpoint"), "Montowanie (FUSE) na serwerze nie działa."),
    (("dial tcp", "no such host", "timeout", "connection refused", "network is unreachable", "tls handshake"),
     "Brak połączenia z Google. Spróbuj za chwilę."),
)


def reason(text):
    """Jedno zdanie po polsku z komunikatu rclone (dopasowanie fragmentu); nigdy sam komunikat."""
    low = str(text or "").lower()
    for keys, msg in REASONS:
        if any(k in low for k in keys):
            return msg
    return "Nie udało się odczytać Google Drive."


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


def account_back_query(value, state):
    """Kod albo wartości z tekstu. Do rclone zawsze trafia zapytanie dla bieżącego logowania."""
    value = html.unescape(str(value or "").strip())
    fields = {}
    for key, data in re.findall(r'(?<![\w-])((?:code|state|error))=([^&\s<>"\']*)', value):
        if key in fields:
            return None, "Wklej jeden adres albo jeden kod logowania."
        fields[key] = urllib.parse.unquote_plus(data)
    if fields.get("error"):
        return None, "Google nie przekazał zgody. Otwórz logowanie i zatwierdź dostęp."
    if "state" in fields and fields["state"] != state:
        return None, "Ten adres pochodzi z innego logowania. Wklej adres z aktualnego linku."
    code = fields.get("code", value if not fields else "")
    if not re.fullmatch(r"[A-Za-z0-9/_+.%=-]{1,2048}", code):
        return None, "Brakuje kodu Google. Wklej cały adres lub sam kod."
    return urllib.parse.urlencode({"state": state, "code": code}), ""


def return_page(value):
    value = str(value or "")
    return "/" + value if re.fullmatch(r"#[A-Za-z0-9_/?&=.%+~:-]{1,500}", value) else "/#koszty?k=drive"


def account_id(label, taken=()):
    """Id konta (część nazwy wpisu rclone) z nazwy nadanej przy łączeniu: małe litery ASCII, cyfry, „-”."""
    s = unicodedata.normalize("NFKD", str(label or "").replace("ł", "l").replace("Ł", "L"))
    s = re.sub(r"[^a-z0-9]+", "-", s.encode("ascii", "ignore").decode().lower()).strip("-")[:24] or "konto"
    out, n = s, 2
    while out in taken:
        out, n = "%s-%d" % (s, n), n + 1
    return out


class Drive:
    """Konta Google Drive i foldery projektów. card_dir: funkcja pid -> folder karty albo None."""

    def __init__(self, card_dir, rclone=None, helper=None, conf=None, data_dir=None, port=PORT, oauth_file=None,
                 token_url=TOKEN_URL):
        self.card_dir = card_dir
        self.rclone = rclone if rclone is not None else (shutil.which("rclone") or "")
        self.helper = helper or ["sudo", "-n", "/usr/local/bin/drive-wlacz"]
        self.conf = conf or os.path.expanduser("~/.config/rclone/rclone.conf")
        self.data_dir = data_dir or os.path.expanduser("~/dane/drive")
        self.oauth_file = oauth_file or os.environ.get("PANEL_GOOGLE_OAUTH") or \
            os.path.expanduser("~/.config/integrate/google-oauth.json")
        self.token_url = token_url
        self.port = port
        self.lock = threading.Lock()
        self.conf_lock = threading.Lock()
        self.login = None               # {"key", "kind", "proc", "state", "url", "at", "folder" | "acc", "label"}
        self._folders = {}              # konto -> (czas, wynik)

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

    def _side_read(self, pid):
        try:
            with open(self._side(pid), encoding="utf-8") as f:
                d = json.load(f)
            return d if isinstance(d, dict) else {}
        except (OSError, ValueError):
            return {}

    def _side_write(self, pid, data):
        os.makedirs(self.data_dir, exist_ok=True)
        tmp = self._side(pid) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp, self._side(pid))

    def _accounts_file(self):
        return os.path.join(self.data_dir, "konta.json")

    def _accounts_read(self):
        try:
            with open(self._accounts_file(), encoding="utf-8") as f:
                d = json.load(f)
            return {k: v for k, v in d.items() if ACC_RE.match(k) and isinstance(v, dict)} if isinstance(d, dict) else {}
        except (OSError, ValueError):
            return {}

    def _accounts_write(self, data):
        os.makedirs(self.data_dir, exist_ok=True)
        tmp = self._accounts_file() + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp, self._accounts_file())

    def _project_sides(self):
        """{pid: dane folderu} wszystkich projektów z połączonym folderem (pliki dane/drive/<pid>.json)."""
        out = {}
        try:
            names = os.listdir(self.data_dir)
        except OSError:
            return out
        for n in names:
            if n.endswith(".json") and n != "konta.json" and PID_RE.match(n[:-5]):
                out[n[:-5]] = self._side_read(n[:-5])
        return out

    def _mnt(self, pid):
        card = self.card_dir(pid)
        return os.path.join(card, "media", "drive") if card else ""

    def mount_path(self, pid):
        """Zamontowany folder Drive projektu (tylko do odczytu) albo ''."""
        mnt = self._mnt(str(pid or "")) if PID_RE.match(str(pid or "")) else ""
        return mnt if mnt and os.path.ismount(mnt) else ""

    def _helper(self, *args):
        """(udało się, krótki powód). Wyjście pomocnika (polskie komunikaty drive-wlacz) bez śladów rclone."""
        try:
            r = subprocess.run(self.helper + list(args), stdin=subprocess.DEVNULL, capture_output=True, text=True,
                               timeout=60)
        except (OSError, subprocess.SubprocessError) as e:
            return False, "pomocnik niedostępny (%s)" % type(e).__name__
        out = (r.stdout + r.stderr).strip().splitlines()
        last = out[-1][:160] if out else ""
        if "sudo" in last.lower() or "password" in last.lower():
            last = "brak zgody sudo dla pomocnika drive-wlacz"
        return r.returncode == 0, last

    def _connected(self, pid):
        """Połączony = udane połączenie (plik dane/drive/<pid>.json) i wpis drive-<pid> w konfiguracji rclone.
        rclone zapisuje wpis już przed zalogowaniem, więc sam wpis niczego nie znaczy."""
        return os.path.exists(self._side(pid)) and ("drive-" + pid) in self._remotes()

    def _drop_remote(self, name):
        try:
            self._rc("config", "delete", name)
        except (OSError, subprocess.SubprocessError):
            pass

    def _stop_login(self, drop=True):
        """Wywołanie pod self.lock. drop: usuń niedokończony wpis rclone (logowanie przerwane)."""
        lg, self.login = self.login, None
        if not lg:
            return
        proc = lg.get("proc")
        if proc:
            if proc.poll() is None:
                proc.kill()
            try:
                proc.wait(timeout=5)
            except subprocess.SubprocessError:
                pass
            if proc.stdout:
                try:
                    proc.stdout.close()
                except OSError:
                    pass
        if not drop or not proc:
            return
        if lg["kind"] == "project" and not os.path.exists(self._side(lg["key"])):
            self._drop_remote("drive-" + lg["key"])
        elif lg["kind"] == "account" and lg["acc"] not in self._accounts_read():
            self._drop_remote(ACC_PREFIX + lg["acc"])

    def _login_alive(self):
        """Wywołanie pod self.lock: bieżące logowanie albo None (wygasłe i zakończone sprząta)."""
        lg = self.login
        if lg and (time.time() - lg["at"] > LOGIN_TTL
                   or (lg.get("proc") and not lg.get("sent") and lg["proc"].poll() is not None)):
            self._stop_login()
            lg = None
        return lg

    def _check(self, pid):
        pid = str(pid or "")
        if not PID_RE.match(pid) or not self.card_dir(pid):
            return None, (404, "Nie ma tego projektu.", {})
        if not self.rclone:
            return None, (409, "Na serwerze brakuje rclone (uruchom/serwer/zainstaluj-drive.sh).", {})
        return pid, None

    def _rclone_login(self, remote, params):
        """Wywołanie pod self.lock: `rclone config create` z logowaniem na 127.0.0.1:<port>.
        (proces, state, adres Google) albo (None, '', komunikat błędu)."""
        os.makedirs(os.path.dirname(self.conf), mode=0o700, exist_ok=True)
        try:
            proc = subprocess.Popen([self.rclone, "--config", self.conf, "config", "create", remote, *params],
                                    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, errors="replace")
        except OSError:
            return None, "", "Nie udało się uruchomić rclone."
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
        url = self._google_url(found["state"]) if "state" in found else ""
        if not url:
            if proc.poll() is None:
                proc.kill()
            try:
                proc.wait(timeout=5)
                proc.stdout.close()
            except (OSError, subprocess.SubprocessError):
                pass
            self._drop_remote(remote)
            return None, "", ("rclone nie podał adresu logowania." if "state" not in found
                              else "Nie udało się otworzyć logowania Google.")
        return proc, found["state"], url

    def _rclone_finish(self, lg, url):
        """Wywołanie pod self.lock: przekazuje adres powrotu do rclone. '' albo komunikat błędu."""
        q = back_query(url, lg["state"], self.port)
        if q is None:
            return "Wklej cały adres z paska przeglądarki po zalogowaniu (zaczyna się od http://127.0.0.1:%d/?state=)." \
                % self.port
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
        return ""

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

    def own_client(self):
        """Własny klient OAuth właściciela (plik oauth_file) albo None. Wartości nie wychodzą poza moduł."""
        try:
            with open(self.oauth_file, encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError):
            return None
        if not isinstance(d, dict):
            return None
        cid, sec, red = (str(d.get(k) or "").strip() for k in ("client_id", "client_secret", "redirect_uri"))
        if not cid.endswith(".apps.googleusercontent.com") or not sec or not red.startswith("https://") \
                or not red.endswith("/api/drive/powrot"):
            return None
        return {"client_id": cid, "client_secret": sec, "redirect_uri": red}

    def save_client(self, body):
        """Zapis ustawień klienta z formularza panelu."""
        supplied = body.get("json")
        if supplied:
            try:
                web = json.loads(supplied).get("web")
                if not isinstance(web, dict) or REDIRECT_URI not in (web.get("redirect_uris") or []):
                    return 400, "Wybierz JSON klienta typu Aplikacja internetowa z adresem powrotu podanym wyżej.", {}
            except (TypeError, ValueError, AttributeError):
                return 400, "Nie udało się odczytać pliku JSON klienta Google.", {}
        else:
            web = body
        cid, secret = (str(web.get(k) or "").strip() for k in ("client_id", "client_secret"))
        if not re.fullmatch(r"[A-Za-z0-9_-]+\.apps\.googleusercontent\.com", cid) or not re.fullmatch(
                r"[A-Za-z0-9_-]{1,256}", secret):
            return 400, "Podaj identyfikator i sekret klienta z Google Cloud.", {}
        with self.lock:
            tmp = None
            try:
                parent = os.path.dirname(os.path.abspath(self.oauth_file))
                os.makedirs(parent, mode=0o700, exist_ok=True)
                with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=parent, delete=False) as f:
                    tmp = f.name
                    json.dump({"client_id": cid, "client_secret": secret, "redirect_uri": REDIRECT_URI}, f)
                os.replace(tmp, self.oauth_file)
            except OSError:
                return 500, "Nie udało się zapisać klienta na serwerze.", {}
            finally:
                if tmp and os.path.exists(tmp):
                    os.unlink(tmp)
        return 200, "", {"ownClient": True}

    # ---------- konta Google ----------
    def accounts(self):
        out = {"available": bool(self.rclone), "ownClient": False, "redirectUri": REDIRECT_URI, "scope": SCOPE,
               "accounts": [], "login": None}
        if not self.rclone:
            return 200, "", out
        out["ownClient"] = self.own_client() is not None
        meta, remotes, sides = self._accounts_read(), self._remotes(), self._project_sides()
        for acc, m in sorted(meta.items(), key=lambda x: str(x[1].get("label") or x[0]).lower()):
            out["accounts"].append({"id": acc, "label": str(m.get("label") or acc), "at": str(m.get("at") or ""),
                                    "connected": (ACC_PREFIX + acc) in remotes,
                                    "projects": sorted(p for p, s in sides.items() if s.get("account") == acc)})
        with self.lock:
            lg = self._login_alive()
            if lg and lg["kind"] == "account":
                out["login"] = {"account": lg["acc"], "label": lg["label"], "url": lg["url"], "mode": lg["mode"]}
        return 200, "", out

    def start_account(self, label, account="", return_to=""):
        """Logowanie nowego konta (label) albo ponowne istniejącego (account: cofnięty albo wygasły dostęp)."""
        if not self.rclone:
            return 409, "Na serwerze brakuje rclone (uruchom/serwer/zainstaluj-drive.sh).", {}
        meta = self._accounts_read()
        if account:
            if account not in meta:
                return 404, "Nie ma tego konta.", {}
            acc, label = account, str(meta[account].get("label") or account)
        else:
            label = re.sub(r"\s+", " ", str(label or "")).strip()[:60]
            if not label:
                label = "Konto Google" if not meta else "Konto Google %d" % (len(meta) + 1)
            if any(str(m.get("label") or "").lower() == label.lower() for m in meta.values()):
                return 409, "Konto o tej nazwie jest już połączone. Podaj inną nazwę.", {}
            acc = account_id(label, set(meta) | {r[len(ACC_PREFIX):] for r in self._remotes()
                                                 if r.startswith(ACC_PREFIX)})
        with self.lock:
            lg = self._login_alive()
            if lg and lg["kind"] == "project":
                return 409, "Trwa logowanie Drive w projekcie. Spróbuj za kilka minut.", {}
            if lg:
                if lg["mode"] == "paste" and (lg["acc"] == acc or (not account and lg["label"] == label)):
                    return 200, "", {"loginUrl": lg["url"], "mode": "paste", "account": lg["acc"]}
                if lg["mode"] == "paste":
                    return 409, "Trwa logowanie innego konta. Dokończ je albo anuluj.", {}
            self._stop_login()
            own = self.own_client()
            if own:
                state = secrets.token_urlsafe(24)
                url = AUTH_URL + "?" + urllib.parse.urlencode({
                    "client_id": own["client_id"], "redirect_uri": own["redirect_uri"], "response_type": "code",
                    "scope": SCOPE, "access_type": "offline", "prompt": "consent select_account", "state": state})
                self.login = {"key": "konto:" + acc, "kind": "account", "mode": "own", "proc": None, "state": state,
                              "url": url, "at": time.time(), "acc": acc, "label": label,
                              "return": return_page(return_to), "client": own}
            else:
                if account:
                    self._drop_remote(ACC_PREFIX + acc)      # wpis z cofniętym tokenem; aliasy projektów zostają
                proc, state, url = self._rclone_login(ACC_PREFIX + acc, ["drive", "scope=drive.readonly"])
                if not proc:
                    return 500, url, {}
                self.login = {"key": "konto:" + acc, "kind": "account", "mode": "paste", "proc": proc,
                              "state": state, "url": url, "at": time.time(), "acc": acc, "label": label}
            return 200, "", {"loginUrl": url, "mode": self.login["mode"], "account": acc}

    def _account_done(self, acc, label):
        try:
            os.chmod(self.conf, 0o600)
        except OSError:
            pass
        meta = self._accounts_read()
        meta[acc] = {"label": label, "at": time.strftime("%Y-%m-%dT%H:%M:%S")}
        self._accounts_write(meta)
        self._folders.pop(acc, None)
        for pid, side in self._project_sides().items():          # ponowne połączenie: montowania od nowa
            if side.get("account") == acc and self.card_dir(pid):
                self._helper(pid, self.card_dir(pid))

    def finish_account(self, url):
        if not self.rclone:
            return 409, "Na serwerze brakuje rclone.", {}
        with self.lock:
            lg = self._login_alive()
            if not lg or lg["kind"] != "account" or lg["mode"] != "paste":
                return 409, "Logowanie wygasło. Kliknij „Połącz Google Drive” jeszcze raz.", {}
            query, err = account_back_query(url, lg["state"])
            if err:
                return 400, err, {}
            proc = lg["proc"]
            if not lg.get("sent"):
                conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=8)
                try:
                    conn.request("GET", "/?" + query)
                    lg["sent"] = True
                    with conn.getresponse() as response:
                        if response.status >= 400:
                            lg["sent"] = False
                            return 400, "rclone odrzucił kod. Sprawdź adres i spróbuj ponownie.", {}
                except (OSError, http.client.HTTPException):
                    if not lg.get("sent"):
                        return 503, "Nie udało się przekazać kodu do rclone. Spróbuj ponownie w tym samym oknie.", {}
                finally:
                    conn.close()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                return 202, "", {"pending": True}
            acc, label = lg["acc"], lg["label"]
            if proc.returncode != 0 or (ACC_PREFIX + acc) not in self._remotes():
                self._stop_login()
                return 409, "rclone zakończył logowanie bez dostępu. Otwórz nowe logowanie.", {}
            self._account_done(acc, label)
            self._stop_login(drop=False)
        return 200, "", {"account": acc}

    def oauth_back(self, query, redirect=False):
        """GET /api/drive/powrot (własny klient OAuth): (kod HTTP, zdanie dla właściciela)."""
        q = urllib.parse.parse_qs(str(query or ""))
        state, code = (q.get("state") or [""])[0], (q.get("code") or [""])[0]
        with self.lock:
            lg = self._login_alive()
            if not lg or lg["kind"] != "account" or lg["mode"] != "own" or not state \
                    or not secrets.compare_digest(state.encode(), lg["state"].encode()):
                return 409, "Logowanie wygasło albo adres jest nieprawidłowy. Połącz konto jeszcze raz w panelu."
            if not code:
                self._stop_login()
                return 400, "Google nie przekazał zgody. Połącz konto jeszcze raz w panelu."
            own = lg["client"]
            self._stop_login(drop=False)
            try:
                data = urllib.parse.urlencode({"code": code, "client_id": own["client_id"],
                                               "client_secret": own["client_secret"],
                                               "redirect_uri": own["redirect_uri"],
                                               "grant_type": "authorization_code"}).encode()
                with urllib.request.urlopen(urllib.request.Request(self.token_url, data=data), timeout=30) as r:
                    tok = json.loads(r.read().decode("utf-8"))
            except (OSError, ValueError):
                return 502, "Google nie wydał dostępu. Połącz konto jeszcze raz w panelu."
            if not isinstance(tok, dict) or not tok.get("access_token") or not tok.get("refresh_token"):
                return 502, "Google nie wydał stałego dostępu. Połącz konto jeszcze raz w panelu."
            exp = datetime.datetime.now(datetime.timezone.utc) + \
                datetime.timedelta(seconds=int(tok.get("expires_in") or 3600))
            token = json.dumps({"access_token": tok["access_token"], "token_type": tok.get("token_type") or "Bearer",
                                "refresh_token": tok["refresh_token"],
                                "expiry": exp.isoformat(timespec="seconds").replace("+00:00", "Z")})
            ok = self._conf_section(ACC_PREFIX + lg["acc"], {
                "type": "drive", "client_id": own["client_id"], "client_secret": own["client_secret"],
                "scope": "drive.readonly", "token": token})
        if not ok:
            return 500, "Nie zapisano połączenia na serwerze."
        self._account_done(lg["acc"], lg["label"])
        if redirect:
            return 303, lg["return"]
        return 200, "Google Drive połączony (%s). Wróć do panelu." % lg["label"]

    def _conf_section(self, name, values):
        """Dopisuje wpis do konfiguracji rclone (plik 0600 użytkownika panelu). Wartości nie są wypisywane."""
        with self.conf_lock:
            cp = configparser.RawConfigParser()
            cp.optionxform = str
            try:
                cp.read(self.conf, encoding="utf-8")
            except configparser.Error:
                return False
            if cp.has_section(name):
                cp.remove_section(name)
            cp.add_section(name)
            for k, v in values.items():
                cp.set(name, k, v)
            os.makedirs(os.path.dirname(self.conf), mode=0o700, exist_ok=True)
            tmp = self.conf + ".tmp"
            fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                cp.write(f)
            os.replace(tmp, self.conf)
        return True

    def cancel_account(self):
        with self.lock:
            if self.login and self.login["kind"] == "account":
                self._stop_login()
        return 200, "", {}

    def remove_account(self, acc):
        acc = str(acc or "")
        meta = self._accounts_read()
        if acc not in meta:
            return 404, "Nie ma tego konta.", {}
        used = sorted(p for p, s in self._project_sides().items() if s.get("account") == acc)
        if used:
            return 409, "Tego konta używają projekty: %d. Najpierw odłącz w nich Drive." % len(used), \
                {"projects": used}
        if self.rclone:
            self._drop_remote(ACC_PREFIX + acc)
        meta.pop(acc, None)
        self._accounts_write(meta)
        self._folders.pop(acc, None)
        return 200, "", {}

    def folders(self, acc, refresh=False):
        """Foldery konta (bez plików): [{"id", "path"}] posortowane po ścieżce, najwyżej MAX_FOLDERS."""
        acc = str(acc or "")
        if acc not in self._accounts_read():
            return 404, "Nie ma tego konta.", {}
        if not self.rclone:
            return 409, "Na serwerze brakuje rclone.", {}
        hit = self._folders.get(acc)
        if hit and not refresh and time.time() - hit[0] < FOLDERS_TTL:
            return 200, "", hit[1]
        try:
            r = self._rc("lsjson", ACC_PREFIX + acc + ":", "--dirs-only", "-R", "--fast-list", "--no-modtime",
                         "--no-mimetype", timeout=LIST_TIMEOUT)
        except subprocess.TimeoutExpired:
            return 504, "Google Drive odpowiada zbyt długo. Spróbuj za chwilę.", {}
        except (OSError, subprocess.SubprocessError):
            return 500, "Nie udało się uruchomić rclone.", {}
        if r.returncode != 0:
            return 502, reason(r.stderr), {}
        try:
            items = json.loads(r.stdout or "[]")
        except ValueError:
            return 502, "Nie udało się odczytać Google Drive.", {}
        out = []
        for e in items if isinstance(items, list) else []:
            if isinstance(e, dict) and e.get("IsDir") and FOLDER_RE.match(str(e.get("ID") or "")) and e.get("Path"):
                out.append({"id": e["ID"], "path": str(e["Path"])[:500]})
        out.sort(key=lambda x: x["path"].lower())
        res = {"folders": out[:MAX_FOLDERS], "truncated": len(out) > MAX_FOLDERS}
        self._folders[acc] = (time.time(), res)
        return 200, "", res

    # ---------- folder projektu ----------
    def choose(self, pid, acc, folder, path=""):
        """Folder z konta dla projektu (albo części): wpis alias drive-<pid> i montowanie usługą drive@<pid>."""
        pid, err = self._check(pid)
        if err:
            return err
        acc = str(acc or "")
        meta = self._accounts_read()
        if acc not in meta:
            return 404, "Nie ma tego konta. Połącz Google Drive.", {}
        fid = folder_id(folder)
        if not fid:
            return 400, "Wybierz folder z listy albo wklej link do folderu (…/drive/folders/…).", {}
        remotes = self._remotes()
        if (ACC_PREFIX + acc) not in remotes:
            return 409, "Brak połączenia z kontem na serwerze. Połącz konto ponownie.", {}
        known = {f["id"]: f["path"] for f in (self._folders.get(acc) or (0, {"folders": []}))[1]["folders"]}
        path = known.get(fid) or re.sub(r"[\x00-\x1f]", "", str(path or "")).strip()[:500]
        with self.lock:
            lg = self._login_alive()
            if lg and lg["kind"] == "project" and lg["key"] == pid:
                self._stop_login()
        name = "drive-" + pid
        if name in remotes:
            self._drop_remote(name)                     # stary wpis (własny token albo inny folder)
        try:
            r = self._rc("config", "create", name, "alias", "remote=%s%s,root_folder_id=%s:" % (ACC_PREFIX, acc, fid))
        except (OSError, subprocess.SubprocessError):
            return 500, "Nie zapisano folderu projektu.", {}
        if r.returncode != 0 or name not in self._remotes():
            return 500, "Nie zapisano folderu projektu.", {}
        self._side_write(pid, {"account": acc, "folder": fid, "path": path,
                               "at": time.strftime("%Y-%m-%dT%H:%M:%S")})
        ok, msg = self._helper(pid, self.card_dir(pid))
        if not ok:
            return 500, "Folder zapisany, ale montowanie nieudane: %s" % msg, {}
        return 200, "", {}

    # ---------- API projektu ----------
    def status(self, pid):
        pid = str(pid or "")
        if not PID_RE.match(pid) or not self.card_dir(pid):
            return 404, "Nie ma tego projektu.", {}
        out = {"available": bool(self.rclone), "connected": False, "mounted": False, "files": None, "folder": "",
               "login": False, "account": "", "accountLabel": "", "path": "", "legacy": False}
        if not self.rclone:
            return 200, "", out
        out["connected"] = self._connected(pid)
        side = self._side_read(pid)
        out["folder"] = str(side.get("folder") or "")
        out["account"] = str(side.get("account") or "")
        out["path"] = str(side.get("path") or "")
        if out["account"]:
            out["accountLabel"] = str(self._accounts_read().get(out["account"], {}).get("label") or out["account"])
        out["legacy"] = out["connected"] and not out["account"]
        mnt = self._mnt(pid)
        out["mounted"] = bool(mnt) and os.path.ismount(mnt)
        if out["mounted"]:
            out["mountPath"] = mnt
            try:
                out["files"] = sum(1 for e in os.scandir(mnt) if not e.name.startswith("."))
            except OSError:
                out["files"] = None
        with self.lock:
            lg = self._login_alive()
            out["login"] = bool(lg and lg["key"] == pid)
            if out["login"]:
                out["loginUrl"] = lg["url"]
        return 200, "", out

    def start(self, pid, link):
        """Połączenie sprzed kont: osobne logowanie dla jednego folderu (wpis drive-<pid> z własnym tokenem)."""
        pid, err = self._check(pid)
        if err:
            return err
        fid = folder_id(link)
        if not fid:
            return 400, "Wklej link do folderu na Google Drive (…/drive/folders/…).", {}
        if self._connected(pid):
            return 409, "Ten projekt ma już połączony Drive. Najpierw odłącz.", {}
        with self.lock:
            lg = self._login_alive()
            if lg and lg["key"] != pid:
                return 409, "Trwa inne logowanie Google Drive. Spróbuj za kilka minut.", {}
            self._stop_login()
            if ("drive-" + pid) in self._remotes():
                self._drop_remote("drive-" + pid)       # wpis po przerwanym logowaniu
            proc, state, url = self._rclone_login("drive-" + pid, ["drive", "scope=drive.readonly",
                                                                    "root_folder_id=" + fid])
            if not proc:
                return 500, url, {}
            self.login = {"key": pid, "kind": "project", "mode": "paste", "proc": proc, "state": state,
                          "folder": fid, "url": url, "at": time.time()}
        return 200, "", {"loginUrl": url}

    def finish(self, pid, url):
        pid, err = self._check(pid)
        if err:
            return err
        with self.lock:
            lg = self._login_alive()
            if not lg or lg["key"] != pid:
                return 409, "Logowanie wygasło. Kliknij „Połącz Google Drive” jeszcze raz.", {}
            err = self._rclone_finish(lg, url)
            if err:
                return 400, err, {}
            folder, done = lg["folder"], lg["proc"].returncode == 0
            if not done or ("drive-" + pid) not in self._remotes():
                self._stop_login()                      # usuwa niedokończony wpis
                return 500, "Google nie potwierdził logowania. Spróbuj jeszcze raz.", {}
            self._stop_login(drop=False)
        try:
            os.chmod(self.conf, 0o600)
        except OSError:
            pass
        self._side_write(pid, {"folder": folder, "at": time.strftime("%Y-%m-%dT%H:%M:%S")})
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
            if self.login and self.login["key"] == str(pid or ""):
                self._stop_login()
        return 200, "", {}

    def disconnect(self, pid):
        """Odłącza folder od projektu: zatrzymuje montowanie, usuwa wpis drive-<pid>. Konto zostaje."""
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
