"""Podgląd strony WWW projektu (pole karty `- strona: folder`; dashboard/AGENCI.md, „Podgląd strony”).

Panel buduje stronę w folderze projektu (na serwerze jako użytkownik agenta), kopiuje wynik do
<uruchomienia>/strona/<projekt>/wynik i serwuje go pod /podglad/<projekt>/<klucz>/…. Uwagi właściciela z zakładki
„Strona” to zadania agenta („Strona: …”); po udanym uruchomieniu panel scala gałąź agenta i buduje podgląd od nowa.

Sama biblioteka standardowa. Moduł nie importuje serwera; zarządca uruchomień (agents.Manager) podaje się w Site().
"""
import datetime
import hashlib
import hmac
import json
import os
import re
import secrets
import shutil
import signal
import stat
import subprocess
import sys
import threading
import time
import urllib.parse
import uuid

SITE_TASK = "Strona: "                          # zadanie z uwagi właściciela
CONCEPT_TASK = "Strona według koncepcji: "      # pierwsza wersja strony według dokumentów koncepcji
BUILD_TIMEOUT = 900                             # s: npm ci + build
MAX_FILES = 5000                                # pliki wyniku budowania
MAX_BYTES = 300 * 1024 * 1024
LOG_TAIL = 40                                   # wierszy dziennika budowania w odpowiedzi API
NOTES_KEEP = 200
NOTE_MAX = 1000
PID = re.compile(r"^[a-z0-9][a-z0-9-]{0,80}$")
KEY = re.compile(r"^[0-9a-f]{24}$")
WIDTH = {"telefon": 390, "komputer": 1440}
WRAPPER = "/usr/local/lib/integrate/podglad-buduj.sh"   # uruchom/serwer/zainstaluj-podglad.sh
SHOT_SCRIPT = "/usr/local/lib/integrate/zrzut-strony.py"
SHOT_PYTHON = "/home/agent/narzedzia/pw/bin/python"
SKIP_DIRS = {".git", ".agent", "node_modules", ".zrzuty", "dist", "build", ".next", ".cache", "venv", ".venv"}
TYPES = {".html": "text/html; charset=utf-8", ".htm": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
         ".js": "text/javascript; charset=utf-8", ".mjs": "text/javascript; charset=utf-8",
         ".json": "application/json", ".map": "application/json", ".webmanifest": "application/manifest+json",
         ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
         ".gif": "image/gif", ".webp": "image/webp", ".avif": "image/avif", ".ico": "image/x-icon",
         ".woff2": "font/woff2", ".woff": "font/woff", ".ttf": "font/ttf", ".otf": "font/otf",
         ".txt": "text/plain; charset=utf-8", ".xml": "application/xml", ".pdf": "application/pdf",
         ".mp4": "video/mp4", ".webm": "video/webm", ".mp3": "audio/mpeg", ".wasm": "application/wasm"}
# Odpowiedzi /podglad/: strona w piaskownicy (bez dostępu do ciasteczek i API panelu), klucz nie wycieka w Referer,
# CORS dla skryptów modułowych i czcionek (dokument w piaskownicy ma nieprzezroczyste pochodzenie).
SERVE_HEADERS = [("Content-Security-Policy", "sandbox allow-scripts allow-forms allow-popups"),
                 ("Referrer-Policy", "no-referrer"), ("Access-Control-Allow-Origin", "*")]
STATE_TEXT = {"error": "agent zakończył się błędem", "timeout": "przekroczony czas", "login": "wymaga logowania",
              "limit": "limit subskrypcji", "stopped": "zatrzymane"}

# Ramka podglądu ma sandbox bez allow-same-origin (strona nie widzi ciasteczek panelu). Safari na iPhonie blokuje
# w takiej ramce history.pushState/replaceState i localStorage (SecurityError): strona z routerem mignęła treścią
# i zostawała biała (2026-11-25, oprogramowani-onepager). Ten skrypt idzie przed skryptami strony: zablokowana zmiana
# adresu nic nie robi, a zamiast niedostępnej pamięci jest pamięć na czas otwarcia podglądu.
SANDBOX_JS = (
    "(function(){['pushState','replaceState'].forEach(function(k){var f=history[k];if(!f)return;"
    "history[k]=function(){try{return f.apply(history,arguments)}catch(e){}}});"
    "['localStorage','sessionStorage'].forEach(function(k){var ok=true;try{var s=window[k];s.getItem('x')}catch(e){ok=false}"
    "if(ok)return;var d={},m={getItem:function(a){return Object.prototype.hasOwnProperty.call(d,a)?d[a]:null},"
    "setItem:function(a,b){d[a]=String(b)},removeItem:function(a){delete d[a]},clear:function(){d={}},"
    "key:function(i){return Object.keys(d)[i]||null}};Object.defineProperty(m,'length',{get:function(){return Object.keys(d).length}});"
    "try{Object.defineProperty(window,k,{value:m,configurable:true})}catch(e){}})})();")

# Skrypt wstrzykiwany do podglądu: tryb „Wskaż” (obrys elementu pod kursorem, klik wybiera element i wysyła
# selektor, tekst i położenie do panelu przez postMessage). Panel przyjmuje wiadomości tylko z tej ramki.
PICKER_JS = r"""(function(){if(window.parent===window)return;var on=false,hb=null,sb=null;
function box(c){var b=document.createElement('div');b.setAttribute('data-pw','1');b.style.cssText='position:absolute;z-index:2147483647;pointer-events:none;border:2px '+(c?'solid':'dashed')+' #d4a72c;border-radius:3px;box-shadow:0 0 0 1px rgba(0,0,0,.35);display:none';(document.body||document.documentElement).appendChild(b);return b}
function place(b,el){var r=el.getBoundingClientRect();b.style.left=(r.left+scrollX-3)+'px';b.style.top=(r.top+scrollY-3)+'px';b.style.width=(r.width+2)+'px';b.style.height=(r.height+2)+'px';b.style.display='block'}
function esc(s){return window.CSS&&CSS.escape?CSS.escape(s):s.replace(/[^a-zA-Z0-9_-]/g,'\\$&')}
function sel(el){var out=[];while(el&&el.nodeType===1&&el!==document.documentElement){var t=el.tagName.toLowerCase();
 if(el.id&&document.querySelectorAll('#'+esc(el.id)).length===1){out.unshift('#'+esc(el.id));break}
 var p=el.parentElement,s=t;if(p){var same=[].filter.call(p.children,function(x){return x.tagName===el.tagName});if(same.length>1)s+=':nth-of-type('+(same.indexOf(el)+1)+')'}
 out.unshift(s);el=p;if(out.length>7)break}return out.join(' > ')}
function page(){var p=location.pathname.replace(/^\/podglad\/[^\/]+\/[^\/]+/,'');return (p||'/').replace(/index\.html$/,'')}
addEventListener('message',function(e){if(e.source!==window.parent)return;var d=e.data||{};
 if(d.pw==='wskaz'){on=!!d.on;if(!on&&hb)hb.style.display='none'}
 if(d.pw==='czysc'&&sb)sb.style.display='none';
 if(d.pw==='pokaz'&&d.sel){try{var el=document.querySelector(d.sel);if(el){sb=sb||box(1);place(sb,el);el.scrollIntoView({block:'center'})}}catch(x){}}});
document.addEventListener('mouseover',function(e){if(!on||e.target.getAttribute('data-pw'))return;hb=hb||box(0);place(hb,e.target)},true);
function pick(e){if(!on)return;e.preventDefault();e.stopPropagation();if(e.type!=='click')return;var el=e.target;if(hb)hb.style.display='none';sb=sb||box(1);place(sb,el);
 var r=el.getBoundingClientRect(),tx=(el.innerText||el.getAttribute('alt')||el.getAttribute('aria-label')||el.getAttribute('title')||'').replace(/\s+/g,' ').trim().slice(0,300);
 window.parent.postMessage({pw:'wybrano',sel:sel(el),text:tx,tag:el.tagName.toLowerCase(),page:page(),vw:innerWidth,
  rect:{x:Math.round(r.left+scrollX),y:Math.round(r.top+scrollY),w:Math.round(r.width),h:Math.round(r.height)}},'*')}
['click','mousedown','mouseup','pointerdown','submit'].forEach(function(n){document.addEventListener(n,pick,true)});
addEventListener('load',function(){window.parent.postMessage({pw:'gotowe',page:page()},'*')})})();"""


def now_iso(when=None):
    return datetime.datetime.fromtimestamp(when or time.time()).astimezone().isoformat(timespec="seconds")


def _short(text, limit):
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"


def _clean(text, limit):
    """Jeden wiersz do zadania: bez |, `, znaków nowego wiersza i nadmiaru spacji."""
    return _short(re.sub(r"[|`\x00-\x1f]", " ", str(text or "")), limit)


def _inside(base, path):
    base, path = os.path.realpath(base), os.path.realpath(path)
    return path == base or path.startswith(base.rstrip(os.sep) + os.sep)


def log(text):
    sys.stdout.write("[strona] %s\n" % text)
    sys.stdout.flush()


def copy_tree(src, dst):
    """Kopia wyniku budowania bez dowiązań (agent nie wskaże plików panelu) i z limitem plików i bajtów."""
    count = size = 0
    for root, dirs, files in os.walk(src, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not os.path.islink(os.path.join(root, d)))
        rel = os.path.relpath(root, src)
        target = dst if rel == "." else os.path.join(dst, rel)
        os.makedirs(target, exist_ok=True)
        for name in files:
            path = os.path.join(root, name)
            try:
                st = os.lstat(path)
            except OSError:
                continue
            if not stat.S_ISREG(st.st_mode):
                continue
            count, size = count + 1, size + st.st_size
            if count > MAX_FILES or size > MAX_BYTES:
                raise ValueError("wynik budowania ma ponad %d plików albo %d MB" % (MAX_FILES, MAX_BYTES >> 20))
            fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0))
            with os.fdopen(fd, "rb") as fi, open(os.path.join(target, name), "wb") as fo:
                shutil.copyfileobj(fi, fo)
    return count


class Site:
    def __init__(self, manager):
        self.m = manager
        self.base = os.path.join(manager.runs_dir, "strona")
        self.secret = secrets.token_bytes(32)    # server.py podmienia na pochodną hasła (klucz trwa po restarcie)
        self.build_timeout = BUILD_TIMEOUT
        get = manager.env.get
        self.wrapper = (get("PANEL_PODGLAD_BUDUJ") or WRAPPER).strip()
        self._lock = threading.RLock()
        self._cond = threading.Condition(self._lock)
        self._busy, self._again, self._finishing = set(), set(), set()

    # ---------- projekt i pliki stanu ----------
    def project(self, pid):
        """(projekt, folder) albo (None, None)."""
        pid = str(pid or "")
        if not PID.match(pid):
            return None, None
        data, index = self.m.load_projects(resolve=False)
        p = next((x for x in data["projects"] if x["id"] == pid), None)
        return (p, index.get(pid)) if p and index.get(pid) else (None, None)

    def _dir(self, pid):
        return os.path.join(self.base, pid)

    def _read(self, pid):
        try:
            with open(os.path.join(self._dir(pid), "stan.json"), encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                data.setdefault("build", {})
                data.setdefault("notes", [])
                return data
        except (OSError, ValueError):
            pass
        return {"build": {}, "notes": []}

    def _write(self, pid, data):
        os.makedirs(self._dir(pid), exist_ok=True)
        path = os.path.join(self._dir(pid), "stan.json")
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        os.replace(tmp, path)

    def _update(self, pid, build=None, note=None):
        """Zmiana stanu budowania (słownik pól) albo jednej uwagi (po id, nowa na początku listy)."""
        with self._lock:
            data = self._read(pid)
            if build is not None:
                data["build"].update(build)
            if note is not None:
                old = next((n for n in data["notes"] if n.get("id") == note.get("id")), None)
                if old:
                    old.update(note)
                else:
                    data["notes"].insert(0, note)
                    del data["notes"][NOTES_KEEP:]
            self._write(pid, data)
            return data

    # ---------- klucz adresu podglądu ----------
    def key(self, pid):
        return hmac.new(self.secret, ("podglad:" + pid).encode("utf-8"), hashlib.sha256).hexdigest()[:24]

    def key_ok(self, path):
        """/podglad/<projekt>/<klucz>/…: klucz pasuje do projektu (dostęp bez ciasteczka: ramka w piaskownicy)."""
        parts = str(path).split("/")
        if len(parts) < 4 or parts[1] != "podglad" or not PID.match(parts[2]) or not KEY.match(parts[3]):
            return False
        return hmac.compare_digest(parts[3], self.key(parts[2]))

    def url(self, pid):
        return "/podglad/%s/%s/" % (pid, self.key(pid))

    # ---------- serwowanie ----------
    def serve(self, path):
        """(kod, treść, typ, nagłówki) dla GET /podglad/<projekt>/<klucz>/<ścieżka>. Klucz sprawdza też server._allowed."""
        parts = str(path).split("/", 4)
        if len(parts) < 4 or not self.key_ok(path):
            return 404, b"Nie znaleziono", "text/plain; charset=utf-8", SERVE_HEADERS
        if len(parts) == 4:      # /podglad/<p>/<klucz> bez ukośnika: względne adresy zasobów wymagają „/” na końcu
            return 303, b"", "text/plain; charset=utf-8", SERVE_HEADERS + [("Location", path + "/")]
        pid, rest = parts[2], urllib.parse.unquote(parts[4])
        root = os.path.join(self._dir(pid), "wynik")
        names = [x for x in rest.split("/") if x not in ("", ".")]
        if "\\" in rest or "\x00" in rest or ".." in names or not os.path.isdir(root):
            return 404, b"Nie znaleziono", "text/plain; charset=utf-8", SERVE_HEADERS
        fpath = os.path.join(root, *names)
        if os.path.isdir(fpath):
            if names and not rest.endswith("/"):   # /pl/prywatnosc → /pl/prywatnosc/: inaczej „../” w stronie wskazuje obok
                return 303, b"", "text/plain; charset=utf-8", SERVE_HEADERS + [("Location", path + "/")]
            fpath = os.path.join(fpath, "index.html")
        elif not os.path.exists(fpath) and not os.path.splitext(fpath)[1] and os.path.isfile(fpath + ".html"):
            fpath += ".html"
        if os.path.islink(fpath) or not os.path.isfile(fpath) or not _inside(root, fpath):
            return 404, b"Nie znaleziono", "text/plain; charset=utf-8", SERVE_HEADERS
        ext = os.path.splitext(fpath)[1].lower()
        ctype = TYPES.get(ext, "application/octet-stream")
        with open(fpath, "rb") as f:
            body = f.read()
        if ext in (".html", ".htm"):
            body = self.inject(body)
        return 200, body, ctype, SERVE_HEADERS

    @staticmethod
    def inject(body):
        tag = ("<script>%s</script><script>%s</script>" % (SANDBOX_JS, PICKER_JS)).encode("utf-8")
        m = re.search(rb"<head[^>]*>", body, re.I)
        if m:
            return body[:m.end()] + tag + body[m.end():]
        return tag + body

    # ---------- budowanie ----------
    def _build_args(self, sdir, command):
        if self.m.agent_user and os.name != "nt":
            return ["sudo", "-n", "-u", self.m.agent_user, "--", self.wrapper, sdir, command]
        if os.name == "nt":
            return ["cmd", "/c", command]
        return ["/bin/sh", "-c", command]

    def build_api(self, pid):
        """POST /api/strona/zbuduj."""
        p, _ = self.project(pid)
        if not p:
            return 404, "Nie ma takiego projektu.", {}
        if not p.get("site"):
            return 409, "Karta projektu nie ma pola strona:.", {}
        self.request_build(pid)
        return 200, "", {"build": self._read(pid)["build"]}

    def request_build(self, pid):
        """Budowanie w tle; gdy już trwa, po nim jeszcze raz (zmiany mogły przyjść w trakcie)."""
        with self._lock:
            if pid in self._busy:
                self._again.add(pid)
                return False
            self._busy.add(pid)
            self._update(pid, build={"state": "building", "startedAt": now_iso()})
        threading.Thread(target=self._build_loop, args=(pid,), daemon=True).start()
        return True

    def build_now(self, pid, timeout=None):
        """Budowanie i czekanie na wynik (po uruchomieniu agenta). Zwraca stan budowania."""
        with self._lock:
            mine = pid not in self._busy
            if mine:
                self._busy.add(pid)
                self._update(pid, build={"state": "building", "startedAt": now_iso()})
            else:
                self._again.add(pid)
        if mine:
            self._build_loop(pid)
        else:
            end = time.time() + (timeout or self.build_timeout * 3)
            with self._cond:
                while pid in self._busy and time.time() < end:
                    self._cond.wait(1)
        return self._read(pid)["build"]

    def _build_loop(self, pid):
        try:
            while True:
                try:
                    self._build_once(pid)
                except Exception as e:  # noqa: BLE001  (błąd budowania nie może zatrzymać panelu)
                    self._update(pid, build={"state": "error", "error": _short("Błąd panelu: %s" % e, 300),
                                             "at": now_iso()})
                with self._lock:
                    if pid not in self._again:
                        break
                    self._again.discard(pid)
                    self._update(pid, build={"state": "building", "startedAt": now_iso()})
        finally:
            with self._cond:
                self._busy.discard(pid)
                self._cond.notify_all()

    def _fail(self, pid, error, tail=None):
        self._update(pid, build={"state": "error", "error": _short(error, 300), "at": now_iso(),
                                 "log": list(tail or [])[-LOG_TAIL:]})

    def _build_once(self, pid):
        p, folder = self.project(pid)
        site = (p or {}).get("site")
        if not site:
            return self._fail(pid, "Karta projektu nie ma pola strona:.")
        ok, note = self.m.ensure_copy(p, folder)            # kopia usunięta z serwera: klon z GitHuba przed budowaniem
        if not ok:
            return self._fail(pid, note)
        sdir = os.path.realpath(os.path.join(folder, site["dir"]))
        if not _inside(folder, sdir) or not os.path.isdir(sdir):
            return self._fail(pid, "Nie ma folderu strony %s w projekcie." % site["dir"])
        os.makedirs(self._dir(pid), exist_ok=True)
        log_path = os.path.join(self._dir(pid), "budowanie.log")
        import agents   # moduł już wczytany (agents importuje strona); bez cyklu przy imporcie
        env = agents.child_env(self.m.env)
        env["CI"] = "1"
        t0 = time.time()
        with open(log_path, "w", encoding="utf-8", errors="replace") as out:
            out.write("$ %s\n" % site["build"])
            out.flush()
            try:
                proc = subprocess.Popen(self._build_args(sdir, site["build"]), cwd=sdir, stdin=subprocess.DEVNULL,
                                        stdout=out, stderr=subprocess.STDOUT, env=env,
                                        **({} if os.name == "nt" else {"start_new_session": True}))
            except OSError as e:
                return self._fail(pid, "Nie uruchomiono budowania: %s." % (e.strerror or e))
            try:
                code = proc.wait(timeout=self.build_timeout)
            except subprocess.TimeoutExpired:
                with_kill(proc)
                code = None
        with open(log_path, encoding="utf-8", errors="replace") as f:
            tail = [x.rstrip() for x in f.read().splitlines() if x.strip()][-LOG_TAIL:]
        if code is None:
            return self._fail(pid, "Budowanie przekroczyło %d min." % (self.build_timeout // 60), tail)
        if code != 0:
            last = tail[-1] if len(tail) > 1 else ""
            return self._fail(pid, "Budowanie nie powiodło się (kod %s)%s" % (code, ": " + last if last else "."), tail)
        odir = os.path.realpath(os.path.join(sdir, site["out"]))
        if not _inside(sdir, odir) or not os.path.isdir(odir):
            return self._fail(pid, "Po budowaniu nie ma folderu %s w folderze strony." % site["out"], tail)
        if not os.path.isfile(os.path.join(odir, "index.html")):
            return self._fail(pid, "W folderze %s nie ma pliku index.html." % site["out"], tail)
        new, cur, old = (os.path.join(self._dir(pid), n) for n in ("wynik.nowy", "wynik", "wynik.stary"))
        for d in (new, old):
            shutil.rmtree(d, ignore_errors=True)
        try:
            files = copy_tree(odir, new)
        except (OSError, ValueError) as e:
            shutil.rmtree(new, ignore_errors=True)
            return self._fail(pid, "Nie skopiowano wyniku: %s." % e, tail)
        if os.path.isdir(cur):
            os.replace(cur, old)
        os.replace(new, cur)
        shutil.rmtree(old, ignore_errors=True)
        self._update(pid, build={"state": "ok", "error": "", "at": now_iso(), "version": int(time.time() * 1000),
                                 "seconds": round(time.time() - t0, 1), "files": files, "log": tail})

    # ---------- dane dla zakładki Strona ----------
    def info(self, pid):
        """GET /api/strona?project=: konfiguracja, stan budowania, adres podglądu, uwagi z ich stanem, podpowiedzi."""
        p, folder = self.project(pid)
        if not p:
            return 404, "Nie ma takiego projektu.", {}
        if not p.get("site"):
            return 409, "Karta projektu nie ma pola strona:.", {}
        data = self._read(pid)
        build = dict(data["build"])
        with self._lock:
            if pid in self._busy:
                build["state"] = "building"
        has = os.path.isfile(os.path.join(self._dir(pid), "wynik", "index.html"))
        runs = self._runs(pid)
        notes = [self._note_view(n, runs) for n in data["notes"]]
        return 200, "", {"site": p["site"], "build": build, "url": self.url(pid) if has else "",
                         "notes": notes, "docs": self.docs(folder, p["site"]), "widths": WIDTH}

    def _runs(self, pid):
        """{tytuł zadania: najnowsze uruchomienie} dla projektu."""
        out = {}
        with self.m._lock:
            for rec in self.m._runs.values():
                if rec.get("project") == pid and rec.get("kind") == "task":
                    out[rec.get("title")] = dict(rec)
        return out

    def _note_view(self, note, runs):
        n = {k: note.get(k) for k in ("id", "kind", "at", "text", "page", "view", "selector", "elementText", "title",
                                      "path", "doneAt", "forwarded")}
        rec = runs.get(note.get("title"))
        n["runId"] = rec["id"] if rec else ""
        if note.get("outcome"):
            n["state"], n["error"] = note["outcome"], note.get("error") or ""
        elif rec and rec["state"] == "queued":
            n["state"], n["error"] = "czeka", ""
        elif rec and (rec["state"] == "running" or (rec["state"] == "done" and note.get("title") in self._finishing)):
            n["state"], n["error"] = "pracuje", rec.get("activity") or ""
        elif rec and rec["state"] == "done":
            n["state"], n["error"] = "zrobione", ""
        elif rec:
            n["state"], n["error"] = "nie wyszło", _short(rec.get("error") or STATE_TEXT.get(rec["state"], ""), 300)
        else:
            n["state"], n["error"] = "czeka", note.get("startError") or ""
        if rec and rec.get("result") and n["state"] in ("zrobione", "nie wyszło"):
            n["result"] = _short(rec["result"], 600)
        return n

    @staticmethod
    def docs(folder, site):
        """Podpowiedzi do pola koncepcji: pliki .md i foldery z plikami .md (do 3 poziomów), najwyżej 80."""
        out, skip = [], set(SKIP_DIRS)
        top = os.path.realpath(folder)
        for root, dirs, files in os.walk(top):
            rel = os.path.relpath(root, top)
            depth = 0 if rel == "." else rel.count(os.sep) + 1
            dirs[:] = sorted(d for d in dirs if d not in skip and not d.startswith(".") and depth < 3
                             and not os.path.islink(os.path.join(root, d)))
            md = sorted(f for f in files if f.lower().endswith(".md"))
            if rel != "." and md:
                out.append(rel.replace(os.sep, "/") + "/")
            out += [(f if rel == "." else rel.replace(os.sep, "/") + "/" + f) for f in md]
            if len(out) >= 80:
                break
        std = {"KARTA.md", "ZADANIA.md", "DECYZJE.md", "CLAUDE.md", "AGENTS.md"}
        first = [x for x in out if re.search(r"koncep|brief|makiet|projekt|tre[sś]", x, re.I) and x not in std]
        return (first + [x for x in out if x not in first and x not in std])[:80]

    # ---------- uwagi i koncepcja: zadania agenta ----------
    def _title(self, data, pid, base):
        titles = {t["title"] for t in data["tasks"] if t["project"] == pid}
        title, n = base, 2
        while title in titles:
            title, n = "%s (%d)" % (base, n), n + 1
        return title

    def _task(self, pid, folder, title, detail):
        """Zadanie `kto: agent | kiedy: dziś` w „Do rozplanowania” i uruchomienie. (kod, błąd, id uruchomienia)."""
        with self.m.write_lock:
            self.m._add_task(folder, pid, title, {"executor": "agent",
                                                   "date": datetime.date.today().isoformat()}, detail)
        task = next((t for t in self.m.load_projects()[0]["tasks"] if t["project"] == pid and t["title"] == title),
                    None)
        if not task:
            return 409, "Nie zapisano zadania.", ""
        code, err, extra = self.m.run_task(task["id"], title)
        return code, err, (extra or {}).get("id", "")

    def add_note(self, body):
        """POST /api/strona/uwaga: {project, text, page, view, selector, elementText}."""
        body = body if isinstance(body, dict) else {}
        pid = str(body.get("project") or "")
        p, folder = self.project(pid)
        if not p:
            return 404, "Nie ma takiego projektu.", {}
        if not p.get("site"):
            return 409, "Karta projektu nie ma pola strona:.", {}
        text = _clean(body.get("text"), NOTE_MAX)
        if not text:
            return 400, "Opisz, co zmienić.", {}
        view = body.get("view") if body.get("view") in WIDTH else "komputer"
        page = _clean(body.get("page"), 200) or "/"
        if not page.startswith("/"):
            page = "/" + page
        selector, el_text = _clean(body.get("selector"), 300), _clean(body.get("elementText"), 200)
        where = "Podstrona %s, widok %s (%d px)." % (page, view, WIDTH[view])
        if selector:
            where += " Element: %s%s." % (selector, ", tekst „%s”" % _short(el_text, 150) if el_text else "")
        live = self.live_run(pid)
        if live:            # agent strony tego projektu pracuje: uwaga idzie do niego (jak „Wyślij do agenta”)
            return self._forward(pid, live, text, page, view, selector, el_text, where)
        data, _ = self.m.load_projects(resolve=False)
        title = self._title(data, pid, SITE_TASK + _short(text, 70))
        detail = {"cel": _short("Zmień stronę według uwagi właściciela: „%s”. %s" % (text, where), 1000),
                  "gotowe gdy": "zmianę z uwagi widać na zrzucie ekranu zbudowanej strony (widok %s, %d px), "
                                "strona się buduje" % (view, WIDTH[view])}
        note = {"id": uuid.uuid4().hex[:12], "kind": "uwaga", "at": now_iso(), "text": text, "page": page,
                "view": view, "selector": selector, "elementText": el_text, "title": title}
        self._update(pid, note=note)
        code, err, rid = self._task(pid, folder, title, detail)
        if code != 200:
            note["startError"] = "Zadanie czeka w Zadaniach: %s" % err
            self._update(pid, note={"id": note["id"], "startError": note["startError"]})
        return 200, "", {"note": self._note_view(note, self._runs(pid)), "runId": rid}

    def live_run(self, pid):
        """Uruchomienie zadania strony tego projektu w kolejce albo w toku (najnowsze) albo None."""
        with self.m._lock:
            runs = [dict(r) for r in self.m._runs.values() if r.get("project") == pid and r.get("kind") == "task"
                    and r.get("state") in ("queued", "running")
                    and str(r.get("title", "")).startswith((SITE_TASK, CONCEPT_TASK))]
        return runs[-1] if runs else None

    def _forward(self, pid, rec, text, page, view, selector, el_text, where):
        """Uwaga z zakładki Strona do pracującego agenta: ta sama droga co wiadomość z rozmowy o zadaniu
        (Manager.live_order). Uwaga trafia na listę z tytułem tego zadania i dzieli jego wynik."""
        order = "Uwaga do strony: %s (%s)" % (text, where.rstrip("."))
        code, err, msg = self.m.live_message(rec["id"], order)
        if code != 200:
            return code, err, {}
        note = {"id": uuid.uuid4().hex[:12], "kind": "uwaga", "at": now_iso(), "text": text, "page": page,
                "view": view, "selector": selector, "elementText": el_text, "title": rec["title"],
                "forwarded": msg.get("text", "")}
        self._update(pid, note=note)
        view_note = self._note_view(note, self._runs(pid))
        view_note["error"] = view_note.get("error") or msg.get("text", "")
        return 200, "", {"note": view_note, "runId": rec["id"], "forwarded": msg.get("text", "")}

    def concept(self, body):
        """POST /api/strona/koncepcja: {project, path, text}: nowa wersja strony według dokumentów koncepcji."""
        body = body if isinstance(body, dict) else {}
        pid = str(body.get("project") or "")
        p, folder = self.project(pid)
        if not p:
            return 404, "Nie ma takiego projektu.", {}
        if not p.get("site"):
            return 409, "Karta projektu nie ma pola strona:.", {}
        path = str(body.get("path") or "").strip().strip("/").replace("\\", "/")
        full = os.path.join(folder, *[x for x in path.split("/") if x])
        if not path or ".." in path.split("/") or not _inside(folder, full) or not os.path.exists(full):
            return 400, "Wskaż plik albo folder koncepcji w projekcie.", {}
        text = _clean(body.get("text"), NOTE_MAX)
        data, _ = self.m.load_projects(resolve=False)
        title = self._title(data, pid, CONCEPT_TASK + _short(path, 80))
        detail = {"cel": _short("Wykonaj nową wersję strony w folderze %s według koncepcji: %s.%s"
                                % (p["site"]["dir"], path, " Uwagi właściciela: „%s”." % text if text else ""), 1000),
                  "gotowe gdy": "strona według koncepcji buduje się, zrzuty ekranu 390 i 1440 px są zgodne "
                                "z koncepcją",
                  "materiał": [path + ("/" if os.path.isdir(full) else "")]}
        note = {"id": uuid.uuid4().hex[:12], "kind": "koncepcja", "at": now_iso(), "text": text or "",
                "path": path, "page": "/", "view": "komputer", "selector": "", "elementText": "", "title": title}
        self._update(pid, note=note)
        code, err, rid = self._task(pid, folder, title, detail)
        if code != 200:
            self._update(pid, note={"id": note["id"], "startError": "Zadanie czeka w Zadaniach: %s" % err})
        return 200, "", {"note": self._note_view(self._find_note(pid, title) or note, self._runs(pid)),
                         "runId": rid}

    def _find_note(self, pid, title):
        return next((n for n in self._read(pid)["notes"] if n.get("title") == title), None)

    # ---------- polecenie dla agenta ----------
    def shot_command(self):
        """Polecenie zrzutu ekranu (prefiks) dla agenta: PANEL_ZRZUT albo domyślne dla serwera i komputera."""
        given = (self.m.env.get("PANEL_ZRZUT") or "").strip()
        if given:
            return given
        if self.m.agent_user:
            return "%s %s" % (SHOT_PYTHON, SHOT_SCRIPT)
        here = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uruchom", "serwer",
                            "zrzut-strony.py")
        py = os.path.expanduser(self.m.env.get("PANEL_FILM_PYTHON") or "~/narzedzia/film/bin/python")
        return "%s %s" % (py if os.path.isfile(py) else "python3", here)

    def task_site(self, project, title):
        """Dane strony do polecenia agenta dla zadań „Strona: …” i „Strona według koncepcji: …”, inaczej None."""
        if not title.startswith((SITE_TASK, CONCEPT_TASK)) or not (project or {}).get("site"):
            return None
        site = project["site"]
        _, folder = self.project(project.get("id"))
        top = self.m._git_top(folder) if folder else ""
        if top:     # zrzuty, zależności i wynik budowania nie trafiają do commita gałęzi agenta
            prefix = self.site_prefix(folder, site)
            out = "/" + "/".join(x for x in (prefix if prefix not in ("", ".") else "", site["out"]) if x) + "/"
            self.m._exclude_agent_dir(top, (".zrzuty/", "node_modules/", out))
        return dict(site, shot=self.shot_command())

    def tools(self, site):
        rules = build_rules(site["build"])[0] if site.get("customBuild") else list(DEFAULT_BUILD_RULES)
        return rules + ["Bash(%s:*)" % site["shot"]]

    @staticmethod
    def rules(site, cwd):
        sdir = os.path.normpath(os.path.join(cwd, site["dir"]))
        out = os.path.join(sdir, site["out"])
        shots = os.path.join(cwd, ".zrzuty")
        skipped = []
        if site.get("customBuild"):
            _, cmds, skipped = build_rules(site["build"])
            if cmds:
                build = "w folderze strony (`cd %s`) poleceniem z karty: `%s`. Masz uprawnienie dokładnie do tych " \
                        "poleceń (każde osobno albo połączone `&&`, także z `--prefix %s`): %s" \
                        % (sdir, " && ".join(cmds), sdir, ", ".join("`%s`" % c for c in cmds))
            else:
                build = "poleceniem z karty `%s`; panel nie dał do niego uprawnienia (tylko `npm ci`, " \
                        "`npm install` i `npm run <skrypt>`), więc wpisz to w `zostało:`" % site["build"]
        else:
            build = "`npm ci --prefix %s` (gdy nie ma node_modules), potem `npm run build --prefix %s -- --base=./`" \
                    % (sdir, sdir)
        more = ["- Tych członów polecenia budowania z karty nie uruchamiaj (brak uprawnienia): %s. Opisz je "
                "w `zostało:`." % ", ".join("`%s`" % s for s in skipped)] if skipped else []
        return [
            "- Zadanie strony WWW. Folder strony: %s. Kod zmieniaj w tym folderze (inne pliki tylko, gdy wymaga "
            "tego uwaga)." % sdir,
            "- Po zmianie zbuduj stronę: %s. Wynik: %s." % (build, out)] + more + [
            "- Zrób zrzuty ekranu zbudowanej strony: `%s %s 390 %s/telefon.png` i `%s %s 1440 %s/komputer.png` "
            "(inna podstrona: dopisz `--sciezka /podstrona`). Każdy zrzut obejrzyj narzędziem Read (to obraz) "
            "i porównaj z celem zadania. Gdy wynik nie odpowiada celowi, popraw kod, zbuduj i zrób zrzuty jeszcze "
            "raz (najwyżej 3 rundy)." % (site["shot"], out, shots, site["shot"], out, shots),
            "- Zrzutów i wyniku budowania nie dodawaj do repozytorium (%s/ jest wykluczony)." % shots,
            "- Nie publikuj strony, nie wdrażaj (Dockerfile, Caddyfile, serwer produkcyjny) i nie pushuj. Panel sam "
            "scali gałąź i zbuduje podgląd, a właściciel oceni zmianę w podglądzie.",
            "- Wyjątek od zasady o odbiorze: zakończ stanem `[x]` z wierszem `wynik:` (co zmieniłeś i co widać na "
            "zrzutach), bez `wymaga: odbiór`. Gdy strona się nie buduje albo zmiany nie da się zrobić: `[!]` "
            "z `blokada:`.",
            "- Gdy narzędzie odmówi polecenia (npm, zrzut), wpisz to w `zostało:`, a zmianę kodu i tak zrób.",
        ]

    # ---------- po uruchomieniu agenta i po scaleniu ----------
    def site_prefix(self, folder, site):
        """Folder strony względem katalogu głównego repozytorium (ścieżki z git diff) albo ''."""
        top = self.m._git_top(folder)
        if not top:
            return ""
        rel = os.path.relpath(os.path.realpath(os.path.join(folder, site["dir"])), top)
        return "" if rel.startswith("..") else rel.replace(os.sep, "/")

    @staticmethod
    def touches(changes, prefix):
        if prefix in ("", "."):
            return bool(changes)
        return any(c.get("path") == prefix or str(c.get("path", "")).startswith(prefix + "/") for c in changes or [])

    def after_run(self, rec):
        """Manager._finish: zadanie strony skończone → scalenie gałęzi agenta i nowy podgląd (w tle)."""
        if rec.get("kind") != "task" or not str(rec.get("title", "")).startswith((SITE_TASK, CONCEPT_TASK)):
            return
        with self._lock:
            self._finishing.add(rec["title"])
        threading.Thread(target=self._after_site_run, args=(dict(rec),), daemon=True).start()

    def after_merge(self, rec):
        """Manager.merge: scalona gałąź innego zadania zmieniła pliki strony → nowy podgląd."""
        if str(rec.get("title", "")).startswith((SITE_TASK, CONCEPT_TASK)):
            return              # zadania strony buduje _after_site_run
        p, folder = self.project(rec.get("project"))
        if p and p.get("site") and self.touches(rec.get("changes"), self.site_prefix(folder, p["site"])):
            self.request_build(p["id"])

    def _outcome(self, pid, title, state, error=""):
        """Wynik uruchomienia dla uwag tego zadania: pierwszej i przekazanych agentowi w trakcie pracy."""
        notes = [n for n in self._read(pid)["notes"] if n.get("title") == title and not n.get("outcome")]
        for note in notes or [n for n in [self._find_note(pid, title)] if n]:
            self._update(pid, note={"id": note["id"], "outcome": state, "error": _short(error, 300),
                                    "doneAt": now_iso()})

    def _after_site_run(self, rec):
        pid, title = rec.get("project", ""), rec["title"]
        try:
            self._site_run_end(rec, pid, title)
        except Exception as e:  # noqa: BLE001
            log("Po uruchomieniu %s: %s" % (rec.get("id"), e))
            self._outcome(pid, title, "nie wyszło", "Błąd panelu: %s" % e)
        finally:
            with self._lock:
                self._finishing.discard(title)

    def _site_run_end(self, rec, pid, title):
        if rec.get("state") != "done":
            return self._outcome(pid, title, "nie wyszło", rec.get("error") or STATE_TEXT.get(rec.get("state"), ""))
        p, folder = self.project(pid)
        if not p or not p.get("site"):
            return self._outcome(pid, title, "nie wyszło", "Karta projektu nie ma już pola strona:.")
        data, _ = self.m.load_projects(resolve=False)
        task = next((t for t in data["tasks"] if t["project"] == pid and t["title"] == title), None)
        if task and task["state"] == "blocked":
            return self._outcome(pid, title, "nie wyszło", task.get("blocked") or "Agent zgłosił blokadę.")
        if rec.get("branch"):
            if not self.touches(rec.get("changes"), self.site_prefix(folder, p["site"])):
                return self._outcome(pid, title, "nie wyszło", "Agent nie zmienił plików strony.")
            code, err, _ = self.m.merge(rec["id"])
            if code != 200:
                return self._outcome(pid, title, "nie wyszło", "Nie scalono zmian: %s" % err)
        build = self.build_now(pid)
        if build.get("state") != "ok":
            return self._outcome(pid, title, "nie wyszło", "Podgląd się nie zbudował: %s" % build.get("error", ""))
        if task and task["state"] != "done":      # zmianę ocenia właściciel w podglądzie: bez osobnego odbioru
            try:
                with self.m.write_lock:
                    self.m.projekt.update_task(folder, task["file"], task["line"], title,
                                               {"state": "done", "needsYou": ""})
            except (ValueError, OSError):
                pass
        self._outcome(pid, title, "zrobione")


# Domyślne budowanie (karta bez `strona build:`): npm ci i npm run build z --prefix (Site.rules).
DEFAULT_BUILD_RULES = ("Bash(npm ci)", "Bash(npm ci:*)", "Bash(npm install)", "Bash(npm install:*)",
                       "Bash(npm run build)", "Bash(npm run build:*)")
NPM_SCRIPT = re.compile(r"^[A-Za-z0-9][\w:.@/+-]{0,80}$")
SHELL_META = re.compile(r"[|&;<>()$`\\\"'*?\[\]{}~!#\n]")


def build_rules(command):
    """Reguły uprawnień dla polecenia `strona build:` z karty: ([reguły Bash(…)], [dozwolone człony], [pominięte]).

    Claude Code sprawdza każdy człon połączony `&&` (także `||`, `;`) osobno, więc każdy człon `npm ci`,
    `npm install` i `npm run <skrypt>` dostaje własne reguły: dokładną (`Bash(npm run build:panel)`) i z dalszymi
    argumentami (`Bash(npm run build:panel:*)`, np. `--prefix folder -- --base=./`). Reguła `Bash(npm run build:*)`
    nie przepuszcza `npm run build:panel`. Inne człony (cd, rm, npx, potoki, zmienne) są pomijane: bez ogólnego Bash."""
    rules, cmds, skipped = [], [], []
    for part in re.split(r"&&|\|\||;", str(command or "")):
        part = " ".join(part.split())
        if not part:
            continue
        words = part.split(" ")
        head = None
        if not SHELL_META.search(part) and words[0] == "npm":
            rest, i = [], 1
            while i < len(words):                 # --prefix folder / --prefix=folder przed poleceniem npm
                if words[i] == "--prefix" and i + 1 < len(words):
                    i += 2
                    continue
                if words[i].startswith("--prefix="):
                    i += 1
                    continue
                rest = words[i:]
                break
            if rest[:1] in (["ci"], ["install"]) and (len(rest) == 1 or rest[1].startswith("-")):
                head = "npm " + rest[0]
            elif rest[:1] in (["run"], ["run-script"]) and len(rest) > 1 and NPM_SCRIPT.match(rest[1]):
                head = "npm run " + rest[1]
        if not head:
            skipped.append(part)
            continue
        if head not in cmds:
            cmds.append(head)
            rules += ["Bash(%s)" % head, "Bash(%s:*)" % head]
    return rules, cmds, skipped


def with_kill(proc):
    """Zatrzymanie budowania po przekroczeniu czasu: cała grupa procesów, potem sam proces."""
    try:
        if os.name != "nt":
            os.killpg(proc.pid, signal.SIGTERM)
        proc.terminate()
        proc.wait(timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        try:
            if os.name != "nt":
                os.killpg(proc.pid, signal.SIGKILL)
            proc.kill()
        except OSError:
            pass
