"""Publikacja postów z panelu: Facebook (strony, zdjęcie, film, Reels) i LinkedIn (profil właściciela).

Połączenia wkleja właściciel w panelu (Marketing → Kanały publikacji); tokeny leżą w PANEL_PUBLIKACJA_DIR
(domyślnie ~/dane/publikacja, pliki 0600) i nie trafiają do /api/data ani do dziennika.
- Facebook: App ID, App Secret i token użytkownika z Graph API Explorer (pages_show_list, pages_read_engagement,
  pages_manage_posts, publish_video). Panel wymienia go na token długoterminowy i zapisuje tokeny stron
  (nie wygasają); sekretu aplikacji nie zapisuje. Strona ma przypisany projekt panelu.
- LinkedIn: token z generatora tokenów LinkedIn (openid, profile, w_member_social), ważny 60 dni.

Planowanie: wiersz `zaplanowane: RRRR-MM-DD GG:MM; kanał, kanał` pod publikacją z kampanii. Pętla w tle co 30 s
publikuje zaplanowane na teraz albo wcześniej: tekst z post.md (sekcje Facebook, LinkedIn, Reels), grafika.png
albo film.mp4 z folderu posta. Po sukcesie: link, wynik i stan zrobione; po błędzie: zostało: i powiadomienie.
Stan kanałów w stan.json, więc opublikowany kanał nie wychodzi drugi raz.
"""
import datetime
import json
import mimetypes
import os
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

FB = "https://graph.facebook.com/v26.0"
FB_VIDEO = "https://graph-video.facebook.com/v26.0"
FB_RUPLOAD = "https://rupload.facebook.com/video-upload/v26.0"
LI = "https://api.linkedin.com"
LI_VERSION = os.environ.get("PANEL_LINKEDIN_VERSION", "").strip() or "202609"
LI_DAYS = 60
CHANNELS = ("facebook", "linkedin", "reels", "instagram")
PUBLIC_URL = os.environ.get("PANEL_PUBLIC_URL", "").strip().rstrip("/")
MEDIA_TTL = 3600            # sekundy: tyle żyje publiczny adres pliku dla Instagrama
FILM_NAMES = ("film.mp4", "film.mov")
FILM_MAX = 300 * 1024 * 1024
SCHED = re.compile(r"^(\d{4}-\d\d-\d\d) (\d\d:\d\d)(?:;\s*(.*))?$")
LI_RESERVED = re.compile(r"([\\|{}@\[\]()<>#*_~])")


class ApiError(Exception):
    pass


def http(method, url, headers=None, body=None, timeout=120):
    """(status, nagłówki, bajty). Błąd HTTP też zwraca status; błąd sieci: ApiError."""
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, {k.lower(): v for k, v in r.headers.items()}, r.read()
    except urllib.error.HTTPError as e:
        return e.code, {k.lower(): v for k, v in (e.headers or {}).items()}, e.read() or b""
    except (urllib.error.URLError, OSError) as e:
        raise ApiError("brak połączenia (%s)" % getattr(e, "reason", e))


def parse_schedule(value):
    """„2026-11-21 09:00; facebook, linkedin” -> (datetime, [kanały]) albo None."""
    m = SCHED.match(str(value or "").strip())
    if not m:
        return None
    try:
        at = datetime.datetime.strptime(m.group(1) + " " + m.group(2), "%Y-%m-%d %H:%M")
    except ValueError:
        return None
    chans = [c.strip().lower() for c in (m.group(3) or "").split(",") if c.strip().lower() in CHANNELS]
    return at, chans


def li_text(text):
    """Tekst posta LinkedIn: znaki zastrzeżone formatu „little text” poprzedzone ukośnikiem."""
    return LI_RESERVED.sub(r"\\\1", text)


def multipart(fields, file_field=None, path=None):
    boundary = "----panel" + uuid.uuid4().hex
    out = []
    for k, v in fields.items():
        out.append(("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n" % (boundary, k, v)).encode("utf-8"))
    if file_field and path:
        ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
        with open(path, "rb") as f:
            data = f.read()
        out.append(("--%s\r\nContent-Disposition: form-data; name=\"%s\"; filename=\"%s\"\r\nContent-Type: %s\r\n\r\n"
                    % (boundary, file_field, os.path.basename(path), ctype)).encode("utf-8") + data + b"\r\n")
    out.append(("--%s--\r\n" % boundary).encode("utf-8"))
    return b"".join(out), "multipart/form-data; boundary=" + boundary


def _json(status, body, what):
    try:
        data = json.loads(body.decode("utf-8") or "{}")
    except (ValueError, UnicodeDecodeError):
        data = {}
    if status >= 400:
        err = data.get("error") if isinstance(data, dict) else None
        msg = (err.get("message") if isinstance(err, dict) else None) or (data.get("message") if isinstance(data, dict) else None)
        raise ApiError("%s: błąd %d%s" % (what, status, (": " + str(msg)[:200]) if msg else ""))
    return data


class Publisher:
    def __init__(self, load_projects, write_lock, projekt, post_folder, post_info, post_image, notify=None,
                 data_dir=None, http_call=None, now=None):
        self.load_projects, self.write_lock, self.projekt = load_projects, write_lock, projekt
        self.post_folder, self.post_info, self.post_image = post_folder, post_info, post_image
        self.notify = notify or (lambda text: None)
        self.dir = os.path.expanduser(data_dir or os.environ.get("PANEL_PUBLIKACJA_DIR", "").strip() or "~/dane/publikacja")
        self.http = http_call or http
        self.now = now or datetime.datetime.now
        self.lock = threading.Lock()
        self.busy = set()
        self._stop = threading.Event()
        self.sync = False           # testy: „Opublikuj teraz” bez osobnego wątku

    # ---------- pliki ----------
    def _read(self, name, default):
        try:
            with open(os.path.join(self.dir, name), encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return default

    def _write(self, name, data):
        os.makedirs(self.dir, mode=0o700, exist_ok=True)
        path = os.path.join(self.dir, name)
        tmp = path + ".tmp"
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        os.replace(tmp, path)

    # ---------- stan dla panelu (bez tokenów) ----------
    def status(self):
        fb, li = self._read("facebook.json", {}), self._read("linkedin.json", {})
        exp = li.get("expiresAt", "")
        return {
            "facebook": {"connected": bool(fb.get("pages")),
                         "pages": [{"id": p["id"], "name": p.get("name", ""), "project": p.get("project", ""),
                                    "instagram": (p.get("ig") or {}).get("username", "") or ("tak" if p.get("ig") else "")}
                                   for p in fb.get("pages") or []]},
            "linkedin": {"connected": bool(li.get("token")) and (not exp or exp > self.now().isoformat()),
                         "name": li.get("name", ""), "expiresAt": exp},
            "state": self._read("stan.json", {}),
        }

    # ---------- połączenia ----------
    def connect_facebook(self, body):
        app_id, secret, token = (str(body.get(k) or "").strip() for k in ("appId", "appSecret", "token"))
        if not (re.match(r"^\d{5,20}$", app_id) and re.match(r"^[0-9a-f]{20,64}$", secret) and len(token) > 30):
            return 400, "Podaj App ID (cyfry), App Secret i token użytkownika z Graph API Explorer."
        try:
            q = urllib.parse.urlencode({"grant_type": "fb_exchange_token", "client_id": app_id,
                                        "client_secret": secret, "fb_exchange_token": token})
            long = _json(*self.http("GET", FB + "/oauth/access_token?" + q)[::2], what="Wymiana tokenu")["access_token"]
            pages = None
            for fields in ("id,name,access_token,instagram_business_account{id,username}", "id,name,access_token"):
                q = urllib.parse.urlencode({"fields": fields, "limit": 50, "access_token": long})
                try:                        # bez uprawnień Instagrama pole konta Instagram daje błąd: same strony
                    pages = _json(*self.http("GET", FB + "/me/accounts?" + q)[::2], what="Lista stron").get("data") or []
                    break
                except ApiError:
                    if fields == "id,name,access_token":
                        raise
        except (ApiError, KeyError) as e:
            return 409, "Facebook nie przyjął danych: %s" % e
        if not pages:
            return 409, "Token nie daje dostępu do żadnej strony. W Graph API Explorer wybierz strony i uprawnienia pages_manage_posts."
        old = {p["id"]: p.get("project", "") for p in self._read("facebook.json", {}).get("pages") or []}
        data, index = self.load_projects(resolve=False)
        out = []
        for p in pages:
            proj = old.get(p["id"]) or self._guess_project(p.get("name", ""), data)
            ig = p.get("instagram_business_account") or {}
            out.append({"id": str(p["id"]), "name": p.get("name", ""), "token": p["access_token"], "project": proj,
                         "ig": {"id": str(ig["id"]), "username": ig.get("username", "")} if ig.get("id") else None})
        self._write("facebook.json", {"appId": app_id, "pages": out, "at": self.now().isoformat(timespec="seconds")})
        return 200, "", {"pages": [{"id": p["id"], "name": p["name"], "project": p["project"]} for p in out]}

    @staticmethod
    def _guess_project(name, data):
        n = str(name or "").lower()
        for p in data.get("projects") or []:
            for key in (p.get("name"), p.get("alias"), p.get("id")):
                word = str(key or "").lower().split(" (")[0].strip()
                if word and (word in n or n in word):
                    return p["id"]
        return ""

    def map_page(self, body):
        fb = self._read("facebook.json", {})
        pid, proj = str(body.get("page") or ""), str(body.get("project") or "")
        for p in fb.get("pages") or []:
            if p["id"] == pid:
                p["project"] = proj
                self._write("facebook.json", fb)
                return 200, ""
        return 404, "Nie ma tej strony."

    def connect_linkedin(self, body):
        token = str(body.get("token") or "").strip()
        if len(token) < 30 or " " in token:
            return 400, "Wklej token z generatora tokenów LinkedIn."
        try:
            st, _, raw = self.http("GET", LI + "/v2/userinfo", {"Authorization": "Bearer " + token})
            me = _json(st, raw, "Profil LinkedIn")
        except ApiError as e:
            return 409, "LinkedIn nie przyjął tokenu: %s" % e
        if not me.get("sub"):
            return 409, "Token nie ma zakresu openid. Zaznacz openid, profile i w_member_social."
        exp = (self.now() + datetime.timedelta(days=LI_DAYS)).isoformat(timespec="seconds")
        self._write("linkedin.json", {"token": token, "sub": me["sub"], "name": me.get("name", ""), "expiresAt": exp})
        return 200, "", {"name": me.get("name", ""), "expiresAt": exp}

    def disconnect(self, body):
        name = {"facebook": "facebook.json", "linkedin": "linkedin.json"}.get(str(body.get("service")))
        if not name:
            return 400, "Nieznana usługa."
        try:
            os.remove(os.path.join(self.dir, name))
        except OSError:
            pass
        return 200, ""

    # ---------- planowanie ----------
    def _task(self, tid, title):
        data, index = self.load_projects()
        t = next((x for x in data["tasks"] if x["id"] == tid and x["title"] == title), None)
        return t, index.get(t["project"]) if t else None

    def plan(self, body):
        t, folder = self._task(str(body.get("id") or ""), str(body.get("title") or ""))
        if not t or t.get("kind") != "publikacja":
            return 404, "Nie ma tej publikacji."
        chans = [c for c in body.get("channels") or [] if c in CHANNELS]
        if "linkedin" in chans:             # regulamin API LinkedIn zabrania automatycznego publikowania
            return 400, "LinkedIn publikujesz sam: w poście „Udostępnij na LinkedInie”, godzinę ustawiasz w LinkedIn."
        if not chans:
            return 400, "Wybierz co najmniej jeden kanał."
        at = str(body.get("at") or "")
        if body.get("now"):
            at = self.now().strftime("%Y-%m-%d %H:%M")
        if not parse_schedule(at):
            return 400, "Data i godzina w formacie RRRR-MM-DD GG:MM."
        problem = self.check(t, chans)
        if problem:
            return 409, problem
        with self.write_lock:
            ok = self.projekt.set_detail(folder, t["file"], t["line"], t["title"], "zaplanowane",
                                         "%s; %s" % (at, ", ".join(chans)))
        if not ok:
            return 409, "Wiersz zmienił się. Odśwież panel."
        if body.get("now"):
            if self.sync:
                self.tick()
            else:
                threading.Thread(target=self.tick, daemon=True).start()
        return 200, ""

    def cancel(self, body):
        t, folder = self._task(str(body.get("id") or ""), str(body.get("title") or ""))
        if not t:
            return 404, "Nie ma tej publikacji."
        with self.write_lock:
            ok = self.projekt.set_detail(folder, t["file"], t["line"], t["title"], "zaplanowane", "")
        return (200, "") if ok else (409, "Wiersz zmienił się. Odśwież panel.")

    def check(self, t, chans):
        """Powód, dla którego publikacja nie wyjdzie, albo ""."""
        st = self.status()
        if ("facebook" in chans or "reels" in chans) and not self._page(t["project"]):
            return "Facebook nie jest połączony ze stroną tego projektu (Marketing → Kanały publikacji)."
        if "linkedin" in chans and not st["linkedin"]["connected"]:
            return "LinkedIn nie jest połączony albo token wygasł (Marketing → Kanały publikacji)."
        folder = self.post_folder(t["project"], str(t.get("date") or "")[:10])
        if not folder:
            return "Nie ma przygotowanego posta na dzień publikacji."
        if "reels" in chans and not self.film(folder):
            return "Reels wymaga filmu: dodaj film w poście."
        if "instagram" in chans:
            page = self._page(t["project"])
            if not (page or {}).get("ig"):
                return "Strona Facebooka tego projektu nie ma połączonego konta Instagram (firmowego)."
            if not PUBLIC_URL:
                return "Instagram wymaga PANEL_PUBLIC_URL w ustawieniach serwera."
        return ""

    def _page(self, project):
        return next((p for p in self._read("facebook.json", {}).get("pages") or [] if p.get("project") == project), None)

    @staticmethod
    def film(folder):
        return next((os.path.join(folder, n) for n in FILM_NAMES if os.path.isfile(os.path.join(folder, n))), None)

    # ---------- pętla ----------
    def start(self):
        threading.Thread(target=self._loop, daemon=True).start()

    def shutdown(self):
        self._stop.set()

    def _loop(self):
        while not self._stop.wait(30):
            try:
                self.tick()
            except Exception:  # noqa: BLE001  (wątek w tle nie może zatrzymać panelu)
                pass

    def tick(self):
        data, index = self.load_projects()
        now = self.now()
        for t in data["tasks"]:
            if t.get("kind") != "publikacja" or t["state"] in ("done", "cancelled"):
                continue
            sched = parse_schedule((t.get("detail") or {}).get("scheduled"))
            if not sched or sched[0] > now:
                continue
            key = "%s|%s|%s" % (t["project"], t["file"], t["title"])
            with self.lock:
                if key in self.busy:
                    continue
                self.busy.add(key)
            try:
                self.publish(t, index.get(t["project"]), key, sched[1])
            finally:
                with self.lock:
                    self.busy.discard(key)

    def publish(self, t, folder, key, chans):
        state = self._read("stan.json", {})
        done = state.get(key, {})
        waits = self.projekt.waiting_titles(t)
        errors = []
        if waits:
            errors.append("czeka na: " + "; ".join(waits))
        else:
            problem = self.check(t, chans)
            if problem:
                errors.append(problem)
        if not errors:
            pf = self.post_folder(t["project"], str(t.get("date") or "")[:10])
            info = self.post_info(pf)
            for ch in chans:
                if (done.get(ch) or {}).get("ok"):
                    continue
                try:
                    link = getattr(self, "_" + ch)(t, pf, info)
                    done[ch] = {"ok": True, "link": link, "at": self.now().isoformat(timespec="seconds")}
                except (ApiError, KeyError, OSError, ValueError) as e:
                    done[ch] = {"ok": False, "error": str(e)[:300], "at": self.now().isoformat(timespec="seconds")}
                    errors.append("%s: %s" % (ch, str(e)[:200]))
                state[key] = done
                self._write("stan.json", state)
        links = ["%s %s" % (ch, done[ch]["link"]) for ch in chans if (done.get(ch) or {}).get("ok")]
        with self.write_lock:
            f = (folder, t["file"], t["line"], t["title"])
            self.projekt.set_detail(*f, "zaplanowane", "")
            if errors:
                self.projekt.set_detail(*f, "zostało", "publikacja nieudana %s: %s%s" % (
                    self.now().strftime("%d.%m %H:%M"), "; ".join(errors),
                    ("; opublikowane już: " + ", ".join(links)) if links else ""))
            else:
                first = next(done[ch]["link"] for ch in chans if (done.get(ch) or {}).get("ok"))
                self.projekt.set_detail(*f, "link", first)
                self.projekt.set_detail(*f, "wynik", "opublikowane %s: %s" % (self.now().strftime("%d.%m %H:%M"), ", ".join(links)))
                self.projekt.set_detail(*f, "zostało", "")
                self.projekt.set_state(*f, "done")
        self.notify(("Nie opublikowano: %s. %s" % (t["title"], "; ".join(errors))) if errors
                    else "Opublikowano: %s (%s)" % (t["title"], ", ".join(ch for ch in chans)), "#marketing?z=" + t["id"])

    # ---------- Facebook ----------
    def _facebook(self, t, pf, info):
        page = self._page(t["project"])
        text = info["sections"].get("Facebook") or info.get("title", "")
        film = self.film(pf)
        if film:
            body, ctype = multipart({"description": text, "access_token": page["token"]}, "source", film)
            d = _json(*self.http("POST", "%s/%s/videos" % (FB_VIDEO, page["id"]), {"Content-Type": ctype}, body, 600)[::2],
                      what="Film na Facebooku")
            return "https://www.facebook.com/%s/videos/%s" % (page["id"], d["id"])
        image = self.post_image(pf) if info.get("image") else None
        if image:
            body, ctype = multipart({"message": text, "access_token": page["token"]}, "source", image)
            d = _json(*self.http("POST", "%s/%s/photos" % (FB, page["id"]), {"Content-Type": ctype}, body)[::2],
                      what="Zdjęcie na Facebooku")
            return "https://www.facebook.com/%s" % (d.get("post_id") or d["id"])
        form = urllib.parse.urlencode({"message": text, "access_token": page["token"]}).encode("utf-8")
        d = _json(*self.http("POST", "%s/%s/feed" % (FB, page["id"]),
                             {"Content-Type": "application/x-www-form-urlencoded"}, form)[::2], what="Post na Facebooku")
        return "https://www.facebook.com/%s" % d["id"]

    def _reels(self, t, pf, info):
        page = self._page(t["project"])
        film = self.film(pf)
        text = info["sections"].get("Reels") or info["sections"].get("Facebook") or info.get("title", "")
        form = lambda d: urllib.parse.urlencode(d).encode("utf-8")
        hdr = {"Content-Type": "application/x-www-form-urlencoded"}
        start = _json(*self.http("POST", "%s/%s/video_reels" % (FB, page["id"]), hdr,
                                 form({"upload_phase": "start", "access_token": page["token"]}))[::2], what="Reels: start")
        vid = start["video_id"]
        size = os.path.getsize(film)
        with open(film, "rb") as f:
            data = f.read()
        _json(*self.http("POST", "%s/%s" % (FB_RUPLOAD, vid), {"Authorization": "OAuth " + page["token"],
                                                               "offset": "0", "file_size": str(size)}, data, 900)[::2],
              what="Reels: wysyłka filmu")
        _json(*self.http("POST", "%s/%s/video_reels" % (FB, page["id"]), hdr,
                         form({"upload_phase": "finish", "video_id": vid, "video_state": "PUBLISHED",
                               "description": text, "access_token": page["token"]}))[::2], what="Reels: publikacja")
        return "https://www.facebook.com/reel/%s" % vid

    # ---------- Instagram (konto firmowe połączone ze stroną; pliki z publicznego adresu) ----------
    def media_url(self, path):
        token = uuid.uuid4().hex
        with self.lock:
            now = time.time()
            self.media = {k: v for k, v in getattr(self, "media", {}).items() if v[1] > now}
            self.media[token] = (path, now + MEDIA_TTL)
        return "%s/media/%s/%s" % (PUBLIC_URL, token, os.path.basename(path))

    def media_file(self, token):
        """Ścieżka pliku pod publicznym adresem /media/<token>/… albo None (nieznany albo wygasły)."""
        with self.lock:
            hit = getattr(self, "media", {}).get(token)
        return hit[0] if hit and hit[1] > time.time() and os.path.isfile(hit[0]) else None

    @staticmethod
    def jpeg(png, out):
        try:
            from PIL import Image
        except ImportError:
            raise ApiError("Instagram przyjmuje tylko JPEG, a na serwerze nie ma biblioteki Pillow (python3-pil)")
        Image.open(png).convert("RGB").save(out, "JPEG", quality=92)
        return out

    def _instagram(self, t, pf, info):
        page = self._page(t["project"])
        ig, token = page["ig"]["id"], page["token"]
        text = info["sections"].get("Instagram") or info["sections"].get("Reels") or info["sections"].get("Facebook") or ""
        film = self.film(pf)
        form = lambda d: urllib.parse.urlencode(dict(d, access_token=token)).encode("utf-8")
        hdr = {"Content-Type": "application/x-www-form-urlencoded"}
        if film:
            fields = {"media_type": "REELS", "video_url": self.media_url(film), "caption": text}
        else:
            png = self.post_image(pf) if info.get("image") else None
            if not png:
                raise ApiError("Instagram wymaga grafiki albo filmu")
            fields = {"image_url": self.media_url(self.jpeg(png, os.path.join(pf, ".instagram.jpg"))), "caption": text}
        cid = _json(*self.http("POST", "%s/%s/media" % (FB, ig), hdr, form(fields))[::2], what="Instagram: przygotowanie")["id"]
        for _ in range(60 if film else 1):     # film: Instagram pobiera i przetwarza go chwilę
            q = urllib.parse.urlencode({"fields": "status_code", "access_token": token})
            code = _json(*self.http("GET", "%s/%s?%s" % (FB, cid, q))[::2], what="Instagram: stan").get("status_code")
            if code in (None, "FINISHED"):
                break
            if code == "ERROR":
                raise ApiError("Instagram nie przetworzył pliku")
            time.sleep(0 if self.http is not http else 5)
        mid = _json(*self.http("POST", "%s/%s/media_publish" % (FB, ig), hdr, form({"creation_id": cid}))[::2],
                    what="Instagram: publikacja")["id"]
        q = urllib.parse.urlencode({"fields": "permalink", "access_token": token})
        try:
            return _json(*self.http("GET", "%s/%s?%s" % (FB, mid, q))[::2], what="Instagram: link").get("permalink") \
                or "https://www.instagram.com/"
        except ApiError:
            return "https://www.instagram.com/"

    # ---------- LinkedIn ----------
    def _li_headers(self, token, json_body=True):
        h = {"Authorization": "Bearer " + token, "LinkedIn-Version": LI_VERSION, "X-Restli-Protocol-Version": "2.0.0"}
        if json_body:
            h["Content-Type"] = "application/json"
        return h

    def _linkedin(self, t, pf, info):
        li = self._read("linkedin.json", {})
        token, owner = li["token"], "urn:li:person:" + li["sub"]
        text = info["sections"].get("LinkedIn") or info.get("title", "")
        post = {"author": owner, "commentary": li_text(text), "visibility": "PUBLIC",
                "distribution": {"feedDistribution": "MAIN_FEED", "targetEntities": [], "thirdPartyDistributionChannels": []},
                "lifecycleState": "PUBLISHED", "isReshareDisabledByAuthor": False}
        film = self.film(pf)
        image = None if film else (self.post_image(pf) if info.get("image") else None)
        if film:
            post["content"] = {"media": {"id": self._li_video(token, owner, film)}}
        elif image:
            post["content"] = {"media": {"id": self._li_image(token, owner, image),
                                         "altText": (info["sections"].get("Alt") or "")[:300]}}
        st, hdr, raw = self.http("POST", LI + "/rest/posts", self._li_headers(token), json.dumps(post).encode("utf-8"))
        _json(st, raw, "Post na LinkedIn")
        urn = hdr.get("x-restli-id") or hdr.get("x-linkedin-id") or ""
        return "https://www.linkedin.com/feed/update/%s/" % urn if urn else "https://www.linkedin.com/in/me/recent-activity/all/"

    def _li_image(self, token, owner, path):
        body = json.dumps({"initializeUploadRequest": {"owner": owner}}).encode("utf-8")
        v = _json(*self.http("POST", LI + "/rest/images?action=initializeUpload", self._li_headers(token), body)[::2],
                  what="LinkedIn: obraz")["value"]
        with open(path, "rb") as f:
            st, _, raw = self.http("PUT", v["uploadUrl"], {"Authorization": "Bearer " + token,
                                                           "Content-Type": "application/octet-stream"}, f.read())
        if st >= 400:
            raise ApiError("LinkedIn: wysyłka obrazu: błąd %d" % st)
        return v["image"]

    def _li_video(self, token, owner, path):
        size = os.path.getsize(path)
        body = json.dumps({"initializeUploadRequest": {"owner": owner, "fileSizeBytes": size,
                                                       "uploadCaptions": False, "uploadThumbnail": False}}).encode("utf-8")
        v = _json(*self.http("POST", LI + "/rest/videos?action=initializeUpload", self._li_headers(token), body)[::2],
                  what="LinkedIn: film")["value"]
        etags = []
        with open(path, "rb") as f:
            for part in v["uploadInstructions"]:
                f.seek(part["firstByte"])
                chunk = f.read(part["lastByte"] - part["firstByte"] + 1)
                st, hdr, _ = self.http("PUT", part["uploadUrl"], {"Content-Type": "application/octet-stream"}, chunk, 600)
                if st >= 400:
                    raise ApiError("LinkedIn: wysyłka filmu: błąd %d" % st)
                etags.append(hdr.get("etag", "").strip('"'))
        body = json.dumps({"finalizeUploadRequest": {"video": v["video"], "uploadToken": v.get("uploadToken", ""),
                                                     "uploadedPartIds": etags}}).encode("utf-8")
        _json(*self.http("POST", LI + "/rest/videos?action=finalizeUpload", self._li_headers(token), body)[::2],
              what="LinkedIn: zakończenie wysyłki filmu")
        urn = urllib.parse.quote(v["video"], safe="")
        for _ in range(40):                     # film musi być przetworzony, zanim powstanie post
            d = _json(*self.http("GET", LI + "/rest/videos/" + urn, self._li_headers(token, False))[::2],
                      what="LinkedIn: stan filmu")
            if d.get("status") == "AVAILABLE":
                return v["video"]
            if d.get("status") == "PROCESSING_FAILED":
                raise ApiError("LinkedIn nie przetworzył filmu")
            time.sleep(0 if self.http is not http else 6)
        raise ApiError("LinkedIn przetwarza film zbyt długo; spróbuj ponownie później")
