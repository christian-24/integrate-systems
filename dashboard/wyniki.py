"""Wyniki marketingu w panelu: dziennik klientów (klienci.py), odczyt postów i reklam, widok Marketing → Wyniki.

Wpięcie w server.py: get_wyniki() (jeden obiekt na proces), WRITES.update(get_wyniki().writes()),
GET przez get_wyniki().api_get(ścieżka, zapytanie), /api/data przez get_wyniki().annotate(out).
Tylko odczyt z Meta i Google Ads: panel nie tworzy, nie zmienia i nie wyłącza reklam ani postów.
Tokeny i klucze leżą w plikach 0600 poza repozytorium i nie trafiają do /api/data ani do odpowiedzi API.
"""
import datetime
import json
import os
import re
import threading
import urllib.parse

import klienci
import wyniki_google as google
import wyniki_meta as meta
from publikacja import LI, LI_VERSION, PUBLIC_URL, ApiError, http as default_http

ORG_FAST_HOURS = 6          # odczyt postu co 6 h przez pierwsze 3 dni
ORG_FAST_DAYS = 3
ORG_DAYS = 30               # potem raz dziennie do 30 dni od publikacji
ORG_READS = 60              # najwyżej tyle odczytów w historii jednego kanału
TICK = 600                  # s: pętla w tle
META_HOUR = 6               # odczyt reklam raz dziennie od 6:00 (za wczoraj)
META_BACK = 30              # pierwszy odczyt: tyle dni wstecz (albo od startu kampanii, najwyżej META_MAX)
META_MAX = 90
META_TMP_DAYS = 60          # token z Graph API Explorer wygasa po 60 dniach
META_LIMITS = (60.0, 40.0, 3.0)   # „- meta progi: 60; 40; 3”: zł bez rozmów, zł za rozmowę (7 dni), częstotliwość (7 dni)
ALERT_DAYS = 7              # najwyżej jedno zadanie na reklamę na tydzień
GOOGLE_LIMITS = (150.0, None, 20.0)  # „- google progi: 150; 4; 20”: zł bez konwersji (7 dni), maks. średni CPC, zł za hasło bez konwersji
LI_REMIND_DAYS = 7          # przypomnienie o tokenie LinkedIn tyle dni przed wygaśnięciem
LI_STATES = ("nie złożony", "złożony", "przyznany")


def _norm_metric(text):
    return re.sub(r"\s+", " ", klienci.norm(text))


class Wyniki:
    def __init__(self, load_projects, write_lock, projekt, post_folder=None, notify=None, publisher=None,
                 klienci_dir=None, ads_dir=None, http_call=None, now=None):
        self.load_projects, self.write_lock, self.projekt = load_projects, write_lock, projekt
        self.post_folder = post_folder
        self.notify = notify or (lambda text, link="#marketing": None)
        self.publisher = publisher
        self.now = now or datetime.datetime.now
        self.klienci = klienci.Klienci(klienci_dir, now=self.now)
        self.ads_dir = os.path.expanduser(ads_dir or os.environ.get("PANEL_REKLAMY_DIR", "").strip() or "~/dane/reklamy")
        self.http = http_call
        self.lock = threading.Lock()
        self._stop = threading.Event()

    # ---------- pliki (0600, katalogi 0700) ----------
    @staticmethod
    def _read_json(path, default):
        try:
            with open(path, encoding="utf-8") as f:
                d = json.load(f)
            return d if isinstance(d, type(default)) else default
        except (OSError, ValueError):
            return default

    @staticmethod
    def _write_json(path, data, private=True):
        os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
        tmp = path + ".tmp"
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600 if private else 0o644)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        os.replace(tmp, path)

    def _ads_path(self, name):
        return os.path.join(self.ads_dir, re.sub(r"[^a-z0-9_.-]", "_", name.lower()))

    def state(self):
        return self._read_json(self._ads_path("stan-wynikow.json"), {})

    def _save_state(self, st):
        self._write_json(self._ads_path("stan-wynikow.json"), st)

    def _pub(self):
        return self.publisher() if callable(self.publisher) else self.publisher

    # ---------- pętla w tle ----------
    def start(self):
        threading.Thread(target=self._loop, daemon=True).start()

    def shutdown(self):
        self._stop.set()

    def _loop(self):
        while not self._stop.wait(TICK):
            try:
                self.tick()
            except Exception:  # noqa: BLE001  (wątek w tle nie może zatrzymać panelu)
                pass

    def tick(self):
        data, index = self.load_projects()
        self.organic_tick(data, index)
        self.meta_tick(data, index)
        self.linkedin_remind(data, index)

    # ---------- etap 5: LinkedIn ----------
    def read_linkedin(self, token, org, link):
        """Statystyki posta strony firmowej (Community Management API, organizationalEntityShareStatistics)."""
        m = re.search(r"urn:li:(share|ugcPost):(\d+)", urllib.parse.unquote(link or ""))
        if not m:
            raise ApiError("link LinkedIn bez identyfikatora posta (urn:li:share albo urn:li:ugcPost)")
        urn = "urn:li:%s:%s" % (m.group(1), m.group(2))
        q = "q=organizationalEntity&organizationalEntity=%s&%s=List(%s)" % (
            urllib.parse.quote("urn:li:organization:%s" % org, safe=""), "shares" if m.group(1) == "share" else "ugcPosts",
            urllib.parse.quote(urn, safe=""))
        status, _, raw = (self.http or default_http)("GET", LI + "/rest/organizationalEntityShareStatistics?" + q,
                                                     {"Authorization": "Bearer " + token, "LinkedIn-Version": LI_VERSION,
                                                      "X-Restli-Protocol-Version": "2.0.0"})
        if status in (401, 403):
            raise meta.PermError("LinkedIn: brak dostępu (Community Management API, r_organization_social)")
        try:
            d = json.loads(raw.decode("utf-8") or "{}")
        except (ValueError, UnicodeDecodeError):
            d = {}
        if status >= 400:
            raise ApiError("LinkedIn: błąd %d" % status)
        tot = ((d.get("elements") or [{}])[0] or {}).get("totalShareStatistics") or {}
        nums = {"wyswietlenia": tot.get("impressionCount"), "zasieg": tot.get("uniqueImpressionsCount"),
                "klikniecia": tot.get("clickCount"), "reakcje": tot.get("likeCount"), "komentarze": tot.get("commentCount"),
                "udostepnienia": tot.get("shareCount")}
        vals = [nums[k] for k in ("reakcje", "komentarze", "udostepnienia") if isinstance(nums[k], (int, float))]
        if vals:
            nums["interakcje"] = sum(vals)
        return {"kind": "post", "id": urn}, {k: v for k, v in nums.items() if v is not None}

    def linkedin_remind(self, data, index):
        """Token LinkedIn wygasa za 7 dni albo mniej: zadanie „kto: ty” w projektach z połączeniem LinkedIn (raz)."""
        pub = self._pub()
        li = pub._read("linkedin.json", {}) if pub else {}
        exp = str(li.get("expiresAt") or "")
        if not exp:
            return []
        try:
            left = datetime.datetime.fromisoformat(exp) - self.now()
        except ValueError:
            return []
        if left > datetime.timedelta(days=LI_REMIND_DAYS):
            return []
        st = self.state()
        if st.get("liReminded") == exp:
            return []
        made = []
        title = "Odnów token LinkedIn (wygasa %s.%s)" % (exp[8:10], exp[5:7])
        for pid, c in self.connections().items():
            if (c.get("linkedin") or {}).get("rodzaj") and pid in index and self.owner_task(
                    pid, index[pid], data, title, "token LinkedIn panelu wygasa %s; wygeneruj nowy i wklej w Kanałach publikacji"
                    % exp[:10], minutes=5):
                made.append(pid)
        st["liReminded"] = exp
        self._save_state(st)
        return made

    # ---------- etap 5: połączenia projektu i Google Ads ----------
    def save_connection(self, body):
        """{"project", "linkedin": {"rodzaj", "organizacja", "wniosek", "reklamy"}?, "googleKlient"?}."""
        p, folder = self._project(body.get("project"))
        if not p:
            return 404, "Nie ma takiego projektu."
        conns = self.connections()
        c = conns.setdefault(p["id"], {})
        new_kinds = []
        if isinstance(body.get("linkedin"), dict):
            b = body["linkedin"]
            rodzaj = str(b.get("rodzaj") or "")
            if rodzaj not in ("", "organizacja", "profil"):
                return 400, "LinkedIn: strona firmowa (organizacja) albo profil prywatny."
            org = re.sub(r"\D", "", str(b.get("organizacja") or ""))[:20]
            if rodzaj == "organizacja" and not org:
                return 400, "Podaj identyfikator strony firmowej LinkedIn (liczba z adresu linkedin.com/company/…/admin)."
            wniosek = str(b.get("wniosek") or "nie złożony")
            if wniosek not in LI_STATES:
                return 400, "Stan wniosku: nie złożony, złożony albo przyznany."
            if rodzaj and not (c.get("linkedin") or {}).get("rodzaj"):
                new_kinds.append("linkedin")
            c["linkedin"] = {"rodzaj": rodzaj, "organizacja": org if rodzaj == "organizacja" else "",
                             "wniosek": wniosek, "reklamy": bool(b.get("reklamy"))}
        if "googleKlient" in body:
            raw = str(body.get("googleKlient") or "").strip()
            cust = google.customer_ok(raw)
            if raw and not cust:
                return 400, "Identyfikator klienta Google Ads: 10 cyfr, np. 434-771-1860."
            g = c.setdefault("google", {})
            if cust and google.digits(cust) != google.digits(g.get("klient")):
                g.pop("keyHash", None)              # inne konto: stary klucz przestaje działać
                new_kinds.append("google")
            g["klient"] = cust
        self._save_connections(conns)
        for kind in new_kinds:
            self.owner_tasks(p["id"], kind)
        return 200, ""

    def google_key(self, body):
        """Nowy klucz projektu (unieważnia poprzedni) i skrypt do wklejenia; klucz widać tylko w tej odpowiedzi."""
        p, _ = self._project(body.get("project"))
        if not p:
            return 404, "Nie ma takiego projektu."
        conns = self.connections()
        g = (conns.get(p["id"]) or {}).get("google") or {}
        if not g.get("klient"):
            return 409, "Najpierw wpisz identyfikator klienta Google Ads."
        base = (os.environ.get("PANEL_PUBLIC_URL", "").strip() or PUBLIC_URL).rstrip("/")
        if not base:
            return 409, "Skrypt wymaga publicznego adresu panelu (PANEL_PUBLIC_URL w ustawieniach serwera)."
        key = google.new_key()
        try:
            text = google.script(p.get("name") or p["id"], g["klient"], base + google.INGEST_PATH, key)
        except ValueError:
            return 409, "Publiczny adres panelu ma niedozwolone znaki."
        g.update(keyHash=google.key_hash(key), keyAt=self.now().isoformat(timespec="seconds"))
        conns.setdefault(p["id"], {})["google"] = g
        self._save_connections(conns)
        return 200, "", {"skrypt": text}

    def google_revoke(self, body):
        p, _ = self._project(body.get("project"))
        if not p:
            return 404, "Nie ma takiego projektu."
        conns = self.connections()
        g = (conns.get(p["id"]) or {}).get("google") or {}
        g.pop("keyHash", None)
        g.pop("keyAt", None)
        self._save_connections(conns)
        return 200, ""

    def google_ingest(self, key, raw):
        """POST /api/wyniki/google-ads od skryptu (bez sesji panelu): (kod, tekst). Zły klucz: 403 bez szczegółów."""
        conns = self.connections() if self._pub() else {}
        pid = google.find_project(conns, key)
        if not pid:
            return 403, "Odmowa."
        cust = (conns[pid].get("google") or {}).get("klient") or ""
        try:
            body = json.loads(raw.decode("utf-8"))
            day, rows, terms = google.parse(body, cust)
        except (ValueError, UnicodeDecodeError, AttributeError) as e:
            return 400, "Złe dane: %s." % (str(e)[:80] or "format")
        with self.lock:
            whole = google.store(self.ads(pid), cust, day, rows, terms, self.now())
            self._write_json(self.ads_file(pid), whole)
        data, index = self.load_projects(resolve=False)
        if pid in index:
            self.google_alerts(pid, index[pid], data)
        return 200, "Przyjęto %s: %d wierszy, %d haseł." % (day, len(rows), len(terms))

    def google_alerts(self, pid, folder, data):
        """Zadania właściciela z progów karty „- google progi: 150; 4; 20” (raz w tygodniu na kampanię i na hasło)."""
        whole = self.ads(pid)
        g = whole.get("google") or {}
        t1, t2, t3 = self.limits(self.card_meta(folder).get("google progi"), GOOGLE_LIMITS)
        today = self.now().date()
        week = (today - datetime.timedelta(days=7)).isoformat()
        sent = whole.setdefault("alerty", {})
        fresh = lambda k: (sent.get(k) or "") > (today - datetime.timedelta(days=ALERT_DAYS)).isoformat()
        made = []
        by = {}
        for r in g.get("rows") or []:
            if r["data"] >= week:
                by.setdefault(google_code(r), []).append(r)
        for code, L in sorted(by.items()):
            cost, conv, clicks = sum(r["koszt"] for r in L), sum(r["konwersje"] for r in L), sum(r["klikniecia"] for r in L)
            key = "google|" + code
            if fresh(key):
                continue
            title = None
            if t1 is not None and cost > t1 and conv == 0:
                title, goal = "Sprawdź kampanię %s: %s zł bez konwersji w 7 dni" % (code, fmt(cost)), \
                    "kampania wydała %s zł w 7 dni bez konwersji (próg %s zł); sprawdź hasła i stronę docelową" % (fmt(cost), fmt(t1))
            elif t2 is not None and clicks and cost / clicks > t2:
                title, goal = "Obniż stawki w %s: średni CPC %s zł" % (code, fmt(cost / clicks)), \
                    "średni koszt kliknięcia %s zł w 7 dni, limit z karty %s zł" % (fmt(cost / clicks), fmt(t2))
            if title and self.owner_task(pid, folder, data, title, goal):
                sent[key] = today.isoformat()
                made.append(title)
        terms = {}
        for r in g.get("terms") or []:
            if r["data"] >= week:
                t = terms.setdefault((r["haslo"].lower(), r["kampania"]), [r["haslo"], 0.0, 0.0])
                t[1] += r["koszt"]
                t[2] += r["konwersje"]
        for (low, camp), (term, cost, conv) in sorted(terms.items()):
            key = "google|haslo|%s|%s" % (camp, low)
            if t3 is None or cost <= t3 or conv or fresh(key):
                continue
            title = "Wyklucz hasło „%s” w G · %s" % (term[:60], camp[:40])
            goal = "hasło kosztowało %s zł w 7 dni bez konwersji (próg %s zł); propozycja: dodaj je jako wykluczające" % (
                fmt(cost), fmt(t3))
            if self.owner_task(pid, folder, data, title, goal, minutes=3):
                sent[key] = today.isoformat()
                made.append(title)
        self._write_json(self.ads_file(pid), whole)
        return made

    # ---------- połączenia projektów (polaczenia.json obok tokenów publikacji; bez sekretów) ----------
    def connections(self):
        pub = self._pub()
        return pub._read("polaczenia.json", {}) if pub else {}

    def _save_connections(self, c):
        self._pub()._write("polaczenia.json", c)

    def card_meta(self, folder):
        """Pola karty projektu (KARTA.md) jako słownik; pola wyników: meta progi, google progi."""
        text = self.projekt.read(os.path.join(folder, "KARTA.md")) if folder else None
        if not text:
            return {}
        return self.projekt.meta_of(self.projekt.parse_doc(text)[1])

    @staticmethod
    def limits(value, default):
        """„60; 40; 3” -> (60.0, 40.0, 3.0); brakujące albo złe wartości z default (None = próg wyłączony)."""
        parts = [x.strip() for x in str(value or "").split(";")]
        out = []
        for i, d in enumerate(default):
            try:
                out.append(float(parts[i].replace(",", ".").replace("zł", "").strip()) if i < len(parts) and parts[i] else d)
            except ValueError:
                out.append(d)
        return tuple(out)

    def ads_file(self, pid):
        return self._ads_path("%s.json" % pid)

    def ads(self, pid):
        return self._read_json(self.ads_file(pid), {})

    # ---------- etap 3: reklamy Meta (Marketing API, tylko odczyt) ----------
    def meta_status(self):
        m = self._pub()._read("meta-reklamy.json", {}) if self._pub() else {}
        exp = m.get("expiresAt", "")
        return {"connected": bool(m.get("token")), "kind": m.get("rodzaj", ""), "expiresAt": exp,
                "expired": bool(exp and exp < self.now().isoformat()),
                "accounts": [{"id": a["id"], "name": a.get("name", "")} for a in m.get("accounts") or []]}

    def connect_meta(self, body):
        token, kind = str(body.get("token") or "").strip(), str(body.get("rodzaj") or "system")
        if len(token) < 30 or re.search(r"\s", token):
            return 400, "Wklej token użytkownika systemowego z Business Managera (ads_read)."
        if kind not in ("system", "tymczasowy"):
            return 400, "Rodzaj tokenu: system albo tymczasowy."
        try:
            accounts = meta.ad_accounts(token, self.http)
        except ApiError as e:
            return 409, "Meta nie przyjęła tokenu: %s" % e
        if not accounts:
            return 409, "Token nie widzi żadnego konta reklamowego. Daj użytkownikowi systemowemu dostęp do konta (ads_read)."
        exp = (self.now() + datetime.timedelta(days=META_TMP_DAYS)).isoformat(timespec="seconds") if kind == "tymczasowy" else ""
        self._pub()._write("meta-reklamy.json", {"token": token, "rodzaj": kind, "expiresAt": exp, "accounts": accounts,
                                                 "at": self.now().isoformat(timespec="seconds")})
        return 200, "", {"accounts": [{"id": a["id"], "name": a["name"]} for a in accounts], "expiresAt": exp}

    def disconnect_meta(self, body):
        try:
            os.remove(os.path.join(self._pub().dir, "meta-reklamy.json"))
        except OSError:
            pass
        return 200, ""

    def meta_assign(self, body):
        """{"project", "act"}: konto reklamowe projektu ("" odłącza). Jedno konto należy do jednego projektu."""
        p, _ = self._project(body.get("project"))
        if not p:
            return 404, "Nie ma takiego projektu."
        act = str(body.get("act") or "").strip()
        if act and not re.fullmatch(r"act_\d{3,20}", act):
            return 400, "Konto reklamowe w formacie act_123456789."
        st = self.meta_status()
        if act and st["connected"] and act not in [a["id"] for a in st["accounts"]]:
            return 409, "Token nie widzi tego konta reklamowego."
        conns = self.connections()
        other = next((k for k, v in conns.items() if k != p["id"] and act and v.get("metaAct") == act), None)
        if other:
            return 409, "To konto jest już przypisane do innego projektu."
        conns.setdefault(p["id"], {})["metaAct"] = act
        self._save_connections(conns)
        if act:
            self.owner_tasks(p["id"], "meta")
        return 200, ""

    def meta_tick(self, data, index, force=False):
        """Raz dziennie od 6:00: odczyt za wczoraj (i brakujące dni) dla projektów z kontem reklamowym, potem alerty."""
        now = self.now()
        today = now.date().isoformat()
        st = self.state()
        if not force and (now.hour < META_HOUR or st.get("metaDay") == today):
            return
        m = self._pub()._read("meta-reklamy.json", {}) if self._pub() else {}
        if not m.get("token"):
            return
        for pid, conn in self.connections().items():
            act = conn.get("metaAct")
            if act and pid in index:
                self.meta_sync(pid, act, m["token"], data)
                self.meta_alerts(pid, index[pid], data)
        st = self.state()
        st["metaDay"] = today
        self._save_state(st)

    def meta_sync(self, pid, act, token, data):
        now = self.now()
        yesterday = (now.date() - datetime.timedelta(days=1)).isoformat()
        whole = self.ads(pid)
        rec = whole.get("meta") or {}
        if rec.get("act") != act:
            rec = {"act": act, "rows": []}
        days = sorted({r["data"] for r in rec.get("rows") or []})
        if days:
            since = (datetime.date.fromisoformat(days[-1]) + datetime.timedelta(days=1)).isoformat()
        else:
            start = self.campaign_start(data, pid) or (now.date() - datetime.timedelta(days=META_BACK)).isoformat()
            since = max(start, (now.date() - datetime.timedelta(days=META_MAX)).isoformat())
        try:
            if since <= yesterday:
                rows = [meta.ad_row(r) for r in meta.ads_insights(act, token, since, yesterday, self.http)]
                keep = [r for r in rec.get("rows") or [] if r["data"] < since]
                rec["rows"] = sorted(keep + [r for r in rows if r["data"]], key=lambda r: (r["data"], r["ad"]))
            week = (now.date() - datetime.timedelta(days=7)).isoformat()
            last7 = meta.ads_insights(act, token, week, yesterday, self.http, daily=False)
            rec["last7"] = {str(r.get("ad_id")): {"czestotliwosc": round(meta._num(r.get("frequency")), 2),
                                                  "zasieg": int(meta._num(r.get("reach")))} for r in last7}
            rec.update(syncedAt=now.isoformat(timespec="seconds"), error="")
        except ApiError as e:
            first = not rec.get("error")
            rec.update(error=str(e)[:300], errorAt=now.isoformat(timespec="seconds"))
            if first:
                self.notify("Nie odczytano reklam Meta (%s): %s" % (pid, str(e)[:160]), "#marketing")
        whole["meta"] = rec
        self._write_json(self.ads_file(pid), whole)

    def meta_alerts(self, pid, folder, data):
        """Zadania właściciela z progów karty (najwyżej jedno na reklamę na tydzień); zwraca tytuły nowych zadań."""
        whole = self.ads(pid)
        rows = (whole.get("meta") or {}).get("rows") or []
        if not rows:
            return []
        t1, t2, t3 = self.limits(self.card_meta(folder).get("meta progi"), META_LIMITS)
        today = self.now().date()
        week = (today - datetime.timedelta(days=7)).isoformat()
        last7 = (whole.get("meta") or {}).get("last7") or {}
        by = {}
        for r in rows:
            by.setdefault(r["kod"] or r["nazwa"], []).append(r)
        sent = whole.setdefault("alerty", {})
        made = []
        for code, L in sorted(by.items()):
            last = sent.get("meta|" + code)
            if last and last > (today - datetime.timedelta(days=ALERT_DAYS)).isoformat():
                continue
            spend, conv = sum(r["wydano"] for r in L), sum(r["rozmowy"] for r in L)
            W = [r for r in L if r["data"] >= week]
            s7, c7 = sum(r["wydano"] for r in W), sum(r["rozmowy"] for r in W)
            freq = max([last7.get(r["ad"], {}).get("czestotliwosc", 0) for r in W] or [0])
            title = None
            if t1 is not None and spend >= t1 and conv == 0:
                title, goal = "Wyłącz reklamę %s: 0 rozmów za %s zł" % (code, fmt(t1)), \
                    "reklama %s wydała %s zł i nie dała rozmowy; wyłącz ją w Menedżerze reklam" % (code, fmt(spend))
            elif t2 is not None and c7 and min(r["data"] for r in L) <= week and s7 / c7 > t2:
                title, goal = "Wymień reklamę %s" % code, \
                    "koszt rozmowy %s zł przez 7 dni (próg %s zł); przygotuj nową wersję" % (fmt(s7 / c7), fmt(t2))
            elif t3 is not None and freq > t3:
                title, goal = "Odśwież grafikę %s" % code, \
                    "częstotliwość %s w ostatnich 7 dniach (próg %s); ludzie widzą tę samą grafikę za często" % (fmt(freq), fmt(t3))
            if title and self.owner_task(pid, folder, data, title, goal):
                sent["meta|" + code] = today.isoformat()
                made.append(title)
        self._write_json(self.ads_file(pid), whole)
        return made

    def owner_task(self, pid, folder, data, title, goal, minutes=5):
        """Zadanie „kto: ty” na dziś w ZADANIA.md, przypisane polem kampania: do kampanii w toku. False przy błędzie."""
        camp = next((c for c in data.get("campaigns") or [] if c.get("project") == pid and c.get("state") == "active"), None)
        today = self.now().date().isoformat()
        try:
            with self.write_lock:
                read = lambda: self.projekt.read_project(folder, pid)["tasks"]
                if any(t["title"] == title and t["state"] not in ("done", "cancelled") for t in read()):
                    return False
                self.projekt.add_task(folder, title)
                t = next(x for x in read() if x["title"] == title and x["file"] == "ZADANIA.md")
                self.projekt.update_task(folder, t["file"], t["line"], title,
                                         {"executor": "ty", "date": today, "minutes": minutes})
                if camp:
                    path = os.path.join(folder, "ZADANIA.md")
                    lines = self.projekt.read(path).split("\n")
                    lines[t["line"] - 1] = lines[t["line"] - 1].rstrip() + " | kampania: " + camp["file"]
                    self.projekt.write_atomic(path, "\n".join(lines))
                self.projekt.set_detail(folder, t["file"], t["line"], title, "cel", goal[:300])
            return True
        except (ValueError, OSError, StopIteration):
            return False

    # ---------- etap 4: widok Wyniki ----------
    def period(self, data, pid, okres, kampania):
        """(od, do, kampania albo None) dla filtra: okres 7, 30 albo start; kampania zawęża do swoich dat."""
        today = self.now().date()
        until = today.isoformat()
        camp = next((c for c in data.get("campaigns") or [] if c.get("id") == kampania and c.get("project") == pid), None)
        if okres == "7":
            since = (today - datetime.timedelta(days=6)).isoformat()
        elif okres == "30":
            since = (today - datetime.timedelta(days=29)).isoformat()
        else:
            since = (camp or {}).get("start") or self.campaign_start(data, pid) or ""
        if camp:
            since = max(since, camp.get("start") or "")
            until = min(until, camp.get("end") or until)
        return since, until, camp

    def report(self, pid, okres="30", kampania="", data=None, index=None):
        """Wiersze widoku Wyniki: posty (etap 2), reklamy Meta (etap 3) i Google Ads (etap 5) z klientami (etap 1)."""
        if data is None:
            data, index = self.load_projects(resolve=False)
        since, until, camp = self.period(data, pid, okres, kampania)
        inr = lambda d: klienci.in_range(d or "", since, until)
        rows = {}

        def row(code, **kw):
            key = code.lower()
            r = rows.get(key)
            if not r:
                r = rows[key] = {"kod": code, "tytul": "", "data": "", "kanal": "", "rodzaj": "", "link": "", "zadanie": "",
                                 "miniatura": "", "zasieg": 0, "wyswietlenia": 0, "interakcje": 0, "wydano": 0.0,
                                 "rozmowy": 0, "zapytania": 0, "umowieni": 0, "wykonane": 0, "przychod": 0.0}
            for k, v in kw.items():
                if isinstance(v, (int, float)) and not isinstance(v, bool) and k in r and isinstance(r[k], (int, float)):
                    r[k] += v
                elif v and not r.get(k):
                    r[k] = v
            return r

        for t in data.get("tasks") or []:
            day = str(t.get("date") or "")[:10]
            if t.get("project") != pid or t.get("kind") != "publikacja" or t.get("state") != "done" or not inr(day):
                continue
            if camp and t.get("campaign") != camp["id"]:
                continue
            rec = (self.organic_record(t, day, index or {}).get("kanaly") or {}) if index is not None else {}
            nums = [c.get("liczby") or {} for c in rec.values()]
            d = t.get("detail") or {}
            views = sum(n.get("wyswietlenia") or 0 for n in nums) or (d.get("views") or 0)
            pf = self.post_folder(pid, day, index) if self.post_folder and index is not None else None
            img = bool(pf and any(os.path.isfile(os.path.join(pf, n)) for n in ("grafika.png", "grafika.jpg")))
            row(post_code(t), tytul=t["title"], data=day, kanal=t.get("channel") or "", rodzaj="post",
                link=str(d.get("link") or "") or next((c.get("link") for c in rec.values() if c.get("link")), ""),
                zadanie=t.get("id", ""), miniatura="/api/post/grafika?project=%s&date=%s" % (pid, day) if img else "",
                zasieg=sum(n.get("zasieg") or 0 for n in nums), wyswietlenia=views,
                interakcje=sum(n.get("interakcje") or 0 for n in nums) or (d.get("clicks") or 0))
        ads = self.ads(pid)
        no_code = {}
        for r in (ads.get("meta") or {}).get("rows") or []:
            if not inr(r["data"]):
                continue
            if not r["kod"]:
                no_code[r["nazwa"]] = no_code.get(r["nazwa"], 0) + r["wydano"]
            row(r["kod"] or "Meta · bez kodu", tytul=r["nazwa"] if r["kod"] else "Reklamy bez kodu w nazwie", data=r["data"],
                kanal="Meta", rodzaj="reklama", wydano=r["wydano"], rozmowy=r["rozmowy"], zasieg=r["zasieg"],
                wyswietlenia=r["wyswietlenia"], interakcje=r["klikniecia"])
        for r in (ads.get("google") or {}).get("rows") or []:
            if inr(r["data"]):
                row(google_code(r), tytul=r.get("kampania", ""), data=r["data"], kanal="Google Ads", rodzaj="reklama",
                    wydano=r["koszt"], rozmowy=r["konwersje"], wyswietlenia=r["wyswietlenia"], interakcje=r["klikniecia"])
        # dzień wiersza: najwcześniejszy (row() zostawia pierwszą wartość, reklamy idą po dniach rosnąco)
        rest = {"zapytania": 0, "umowieni": 0, "wykonane": 0, "przychod": 0.0}
        google = [r for r in rows.values() if r["kanal"] == "Google Ads"]
        for e in self.klienci.entries(pid):
            if not inr(e.get("data")):
                continue
            key = (e.get("kod") or "").strip().lower()
            r = rows.get(key)
            if not r and e.get("zrodlo") == "Google Ads" and len(google) == 1:
                r = google[0]              # jedna kampania Google: klient z Google Ads bez kodu należy do niej
            target = r if r else rest
            target["zapytania"] += 1
            target["umowieni"] += 1 if e.get("umowiony") else 0
            target["wykonane"] += 1 if e.get("wykonane") else 0
            target["przychod"] += e.get("wykonane") or 0
        for r in rows.values():
            if r["rodzaj"] == "post":
                r["rozmowy"] = r["zapytania"]          # organiczne: rozmowy = zapytania z kodem posta
            derive(r)
        L = sorted(rows.values(), key=lambda r: (-r["przychod"], r["kosztKlienta"] if r["kosztKlienta"] is not None else 1e12,
                                                 r["data"]))
        total = {k: round(sum(r[k] for r in L) + rest.get(k, 0), 2) for k in ("wydano", "zapytania", "umowieni", "wykonane", "przychod")}
        total["rozmowy"] = sum(r["rozmowy"] for r in L)
        derive(total)
        conn = self.connections().get(pid, {}) if self._pub() else {}
        return {"since": since, "until": until, "campaign": camp["id"] if camp else "", "rows": L, "sum": total,
                "bezKodu": [{"nazwa": k, "wydano": round(v, 2)} for k, v in sorted(no_code.items())],
                "bezKoduKlienci": {k: round(v, 2) for k, v in rest.items()},
                "polaczenia": {"meta": bool(conn.get("metaAct")), "google": bool((conn.get("google") or {}).get("klient")),
                               "metaError": (ads.get("meta") or {}).get("error", ""),
                               "metaSync": (ads.get("meta") or {}).get("syncedAt", ""),
                               "googleAt": (ads.get("google") or {}).get("receivedAt", "")},
                "campaigns": [{"id": c["id"], "name": c["name"]} for c in data.get("campaigns") or [] if c.get("project") == pid]}

    def history(self, pid, code):
        """Dzienny wydatek i rozmowy reklamy (kod) z Meta i Google Ads."""
        ads, days = self.ads(pid), {}
        want = str(code or "").strip().lower()
        for r in (ads.get("meta") or {}).get("rows") or []:
            if (r["kod"] or "Meta · bez kodu").lower() == want:
                d = days.setdefault(r["data"], {"data": r["data"], "wydano": 0.0, "rozmowy": 0, "wyswietlenia": 0})
                d["wydano"] += r["wydano"]
                d["rozmowy"] += r["rozmowy"]
                d["wyswietlenia"] += int(r.get("wyswietlenia") or 0)
        for r in (ads.get("google") or {}).get("rows") or []:
            if google_code(r).lower() == want:
                d = days.setdefault(r["data"], {"data": r["data"], "wydano": 0.0, "rozmowy": 0, "wyswietlenia": 0})
                d["wydano"] += r["koszt"]
                d["rozmowy"] += r["konwersje"]
                d["wyswietlenia"] += int(r.get("wyswietlenia") or 0)
        return [dict(d, wydano=round(d["wydano"], 2)) for _, d in sorted(days.items())]

    def month(self, pid):
        """Przychód z marketingu w tym miesiącu i wydatek na reklamy (Meta + Google) — liczba na Przeglądzie."""
        first = self.now().date().replace(day=1).isoformat()
        rev = sum(e.get("wykonane") or 0 for e in self.klienci.entries(pid) if (e.get("data") or "") >= first)
        ads = self.ads(pid)
        spend = sum(r["wydano"] for r in (ads.get("meta") or {}).get("rows") or [] if r["data"] >= first) + \
            sum(r["koszt"] for r in (ads.get("google") or {}).get("rows") or [] if r["data"] >= first)
        return {"przychod": round(rev, 2), "wydatek": round(spend, 2)}

    def connection_status(self):
        """Połączenia projektów dla /api/data (bez kluczy i tokenów): konto reklamowe, ostatni odczyt, błąd."""
        out = {}
        for pid, c in (self.connections() if self._pub() else {}).items():
            ads = self.ads(pid) if c.get("metaAct") or c.get("google") else {}
            m, g = ads.get("meta") or {}, ads.get("google") or {}
            gc = c.get("google") or {}
            out[pid] = {"metaAct": c.get("metaAct", ""), "metaSync": m.get("syncedAt", ""), "metaError": m.get("error", ""),
                        "linkedin": c.get("linkedin") or {},
                        "google": {"klient": gc.get("klient", ""), "klucz": bool(gc.get("keyHash")),
                                   "kluczOd": gc.get("keyAt", ""), "ostatnio": g.get("receivedAt", "")}}
        return out

    OWNER_TASKS = {
        "meta": ("Meta: token użytkownika systemowego dla panelu",
                 "w Ustawieniach firmy dodaj użytkownika systemowego, daj mu dostęp do konta reklamowego i stron, "
                 "wygeneruj token (nie wygasa) z ads_read, read_insights, instagram_manage_insights i wklej w "
                 "Marketing → Kanały publikacji → Konto reklamowe Meta"),
        "linkedin": ("LinkedIn: wniosek o Community Management API",
                     "w portalu deweloperów LinkedIn (aplikacja panelu → Products) poproś o Community Management API; "
                     "po zgodzie ustaw w połączeniach projektu „przyznany”"),
        "google": ("Google Ads: wklej skrypt z panelu i ustaw „codziennie”",
                   "w połączeniach projektu „Pokaż skrypt”, w Google Ads Narzędzia → Działania zbiorcze → Skrypty → +, "
                   "wklej, autoryzuj, „Podgląd”, potem harmonogram codziennie"),
    }

    def owner_tasks(self, pid, kind):
        """Zadanie właściciela przy dodaniu połączenia (raz na projekt i rodzaj), gdy krok nie jest jeszcze zrobiony."""
        if kind == "meta" and self.meta_status()["connected"]:
            return False
        conns = self.connections()
        c = conns.setdefault(pid, {})
        if kind in (c.get("zadania") or []):
            return False
        data, index = self.load_projects(resolve=False)
        title, goal = self.OWNER_TASKS[kind]
        if pid in index and self.owner_task(pid, index[pid], data, title, goal, minutes=15):
            c.setdefault("zadania", []).append(kind)
            self._save_connections(conns)
            return True
        return False

    # ---------- etap 2: posty organiczne (Facebook, Instagram) ----------
    def organic_targets(self, data):
        """[(publikacja, dzień, {kanał: (link, opublikowano)})]: publikacje z linkiem z publikatora albo z pola link:."""
        pub = self._pub()
        st = pub._read("stan.json", {}) if pub else {}
        out = []
        for t in data.get("tasks") or []:
            if t.get("kind") != "publikacja" or t.get("state") == "cancelled":
                continue
            day = str(t.get("date") or "")[:10]
            if not re.match(r"^\d{4}-\d\d-\d\d$", day):
                continue
            links = {}
            for ch, v in (st.get("%s|%s|%s" % (t["project"], t["file"], t["title"])) or {}).items():
                if isinstance(v, dict) and v.get("ok") and str(v.get("link") or "").startswith("https://"):
                    name = "instagram" if ch == "instagram" else "facebook" if ch in ("facebook", "reels") else ""
                    if name and name not in links:
                        links[name] = (v["link"], str(v.get("at") or ""))
            link = str((t.get("detail") or {}).get("link") or "")
            for name, host in (("facebook", "facebook.com/"), ("instagram", "instagram.com/"), ("linkedin", "linkedin.com/")):
                if name not in links and host in link:
                    links[name] = (link, "")
            if links:
                out.append((t, day, links))
        return out

    def _org_file(self, t, day, index):
        """(ścieżka, klucz): wyniki.json w folderze posta, a bez folderu plik projektu w katalogu reklam."""
        pf = self.post_folder(t["project"], day, index) if self.post_folder else None
        if pf:
            return os.path.join(pf, "wyniki.json"), None
        return self._ads_path("organiczne-%s.json" % t["project"]), "%s|%s" % (day, t["title"])

    def organic_record(self, t, day, index):
        path, key = self._org_file(t, day, index)
        d = self._read_json(path, {})
        return (d.get(key) if key else d) or {}

    def organic_tick(self, data, index):
        pub = self._pub()
        if not pub:
            return
        fb = pub._read("facebook.json", {})
        li = pub._read("linkedin.json", {})
        conns = self.connections()
        now = self.now()
        st = self.state()
        bad = set(st.get("badMetrics") or [])
        perm = dict(st.get("perm") or {})
        for t, day, links in self.organic_targets(data):
            page = pub._page(t["project"])
            lic = (conns.get(t["project"]) or {}).get("linkedin") or {}
            li_ok = bool(li.get("token") and lic.get("rodzaj") == "organizacja" and lic.get("organizacja")
                         and lic.get("wniosek") == "przyznany")
            links = {ch: v for ch, v in links.items() if (page if ch != "linkedin" else li_ok)}
            if not links:
                continue                      # bez połączenia: wpis ręczny jak dotąd
            path, key = self._org_file(t, day, index)
            whole = self._read_json(path, {})
            rec = (whole.get(key) if key else whole) or {}
            chans = rec.setdefault("kanaly", {})
            changed = False
            for ch, (link, at) in links.items():
                conn = str(li.get("expiresAt") or "") if ch == "linkedin" else str(fb.get("at") or "")
                try:
                    published = datetime.datetime.fromisoformat(at) if at else datetime.datetime.fromisoformat(day + "T09:00")
                except ValueError:
                    published = datetime.datetime.fromisoformat(day + "T09:00")
                age = now - published
                if age > datetime.timedelta(days=ORG_DAYS) or age < datetime.timedelta(0):
                    continue
                r = chans.setdefault(ch, {})
                if r.get("link") != link:
                    r.clear()
                    r["link"] = link
                if r.get("stop") and r.get("conn") == conn:
                    continue                                    # błąd: bez ponawiania do ponownego połączenia
                every = datetime.timedelta(hours=ORG_FAST_HOURS if age < datetime.timedelta(days=ORG_FAST_DAYS) else 24)
                last = r.get("at")
                if last and not r.get("stop"):
                    try:
                        if now - datetime.datetime.fromisoformat(last) < every - datetime.timedelta(minutes=5):
                            continue
                    except ValueError:
                        pass
                stamp = now.isoformat(timespec="seconds")
                try:
                    if ch == "linkedin":
                        known, nums = self.read_linkedin(li["token"], lic["organizacja"], link)
                    else:
                        reader = meta.read_instagram if ch == "instagram" else meta.read_facebook
                        known, nums = reader(page, link, {"kind": r.get("kind"), "id": r.get("id"), "reels": r.get("reels")}
                                             if r.get("id") else {}, bad, self.http)
                    r.update(known)
                    r.update({"at": stamp, "liczby": nums, "error": "", "stop": False})
                    r.setdefault("odczyty", []).append(dict(nums, at=stamp))
                    del r["odczyty"][:-ORG_READS]
                    perm.pop(ch, None)
                except ApiError as e:
                    first = not r.get("stop")
                    r.update({"at": stamp, "error": str(e)[:300], "stop": True, "conn": conn})
                    if isinstance(e, meta.PermError):
                        perm[ch] = str(e)[:200]
                    if first:
                        self.notify("Nie odczytano wyników: %s (%s): %s" % (t["title"], ch, str(e)[:160]),
                                    "#marketing?z=" + t["id"])
                changed = True
            if not changed:
                continue
            if key:
                whole[key] = rec
                self._write_json(path, whole)
            else:
                self._write_json(path, rec, private=False)
            self._write_counts(t, index, chans)
        st.update(badMetrics=sorted(bad), perm=perm)
        self._save_state(st)

    def _write_counts(self, t, index, chans):
        """Najnowsze liczby w wierszu publikacji: wyświetlenia (suma kanałów) i kliknięcia (Facebook)."""
        nums = [c.get("liczby") or {} for c in chans.values() if not c.get("error")]
        views = [n["wyswietlenia"] for n in nums if isinstance(n.get("wyswietlenia"), (int, float))]
        clicks = [n["klikniecia"] for n in nums if isinstance(n.get("klikniecia"), (int, float))]
        detail = t.get("detail") or {}
        folder = index.get(t["project"])
        if not folder:
            return
        with self.write_lock:
            for key, field, vals in (("wyświetlenia", "views", views), ("kliknięcia", "clicks", clicks)):
                if vals and detail.get(field) != int(sum(vals)):
                    self.projekt.set_detail(folder, t["file"], t["line"], t["title"], key, str(int(sum(vals))))

    # ---------- pomocnicze ----------
    def _project(self, pid):
        """(projekt z danych, folder) albo (None, None)."""
        data, index = self.load_projects(resolve=False)
        pid = str(pid or "")
        p = next((x for x in data.get("projects") or [] if x.get("id") == pid), None)
        return (p, index.get(pid)) if p and index.get(pid) else (None, None)

    @staticmethod
    def campaign_start(data, pid):
        """Start kampanii projektu: najwcześniejszy start: kampanii w toku albo zakończonej, inaczej ""."""
        days = [c.get("start") for c in data.get("campaigns") or []
                if c.get("project") == pid and c.get("start") and c.get("state") in ("active", "done")]
        return min(days) if days else ""

    # ---------- /api/data ----------
    def annotate(self, out):
        """Licznik kampanii z miernikiem „zapytania z reklam” z dziennika klientów (zamiast ręcznego licznika)."""
        cache = {}
        for c in out.get("campaigns") or []:
            if _norm_metric(c.get("metric")) != klienci.METRIC:
                continue
            pid = c.get("project")
            if pid not in cache:
                cache[pid] = self.klienci.entries(pid)
            n = klienci.ad_inquiries(cache[pid], c.get("start") or "", c.get("end") or "")
            c.setdefault("counters", {})[klienci.METRIC] = n
            c["counterMetric"] = klienci.METRIC
            manual = c.get("resultManual")
            c["result"] = n if manual is None else max(manual, n)
        st = self.state()
        out["wyniki"] = {"perm": st.get("perm") or {}, "meta": self.meta_status() if self._pub() else None,
                         "projects": self.connection_status(), "month": {}}
        for p in out.get("projects") or []:
            pid = p.get("id")
            if pid and (os.path.isfile(self.klienci._path(pid)) or os.path.isfile(self.ads_file(pid))):
                out["wyniki"]["month"][pid] = self.month(pid)
        # publikacje z automatycznym odczytem: kiedy i czy z błędem (bez liczb: te są w wierszu publikacji)
        _, index = self.load_projects(resolve=False)
        for t, day, _links in self.organic_targets(out):
            rec = self.organic_record(t, day, index).get("kanaly") or {}
            if rec:
                t["auto"] = {ch: {"at": r.get("at", ""), "error": r.get("error", "")} for ch, r in rec.items()}

    # ---------- API ----------
    def timeline(self, pid, data, index):
        """Oś publikacji (widok Marketing): odczyty postów z API po kanałach i wyniki reklam po kodzie.
        {"posty": {id zadania: {kanał: {link, error, liczby, odczyty}}}, "reklamy": {kod małymi: {sumy, dni}}}"""
        posts = {}
        for t in data.get("tasks") or []:
            if t.get("project") != pid or t.get("kind") != "publikacja" or t.get("state") == "cancelled":
                continue
            day = str(t.get("date") or "")[:10]
            if not re.match(r"^\d{4}-\d\d-\d\d$", day):
                continue
            chans = (self.organic_record(t, day, index or {}).get("kanaly") or {}) if index is not None else {}
            if chans:
                posts[t.get("id", "")] = {ch: {"link": c.get("link", ""), "error": c.get("error", ""), "at": c.get("at", ""),
                                               "liczby": c.get("liczby") or {},
                                               "odczyty": [{"at": o.get("at", ""), "wyswietlenia": o.get("wyswietlenia")}
                                                           for o in c.get("odczyty") or []]}
                                          for ch, c in chans.items()}
        ads, out = self.ads(pid), {}
        for r in (ads.get("meta") or {}).get("rows") or []:
            if r.get("kod"):
                a = out.setdefault(r["kod"].lower(), {"zrodlo": "meta", "wyswietlenia": 0, "zasieg": 0, "wydano": 0.0, "rozmowy": 0})
                a["wyswietlenia"] += int(r.get("wyswietlenia") or 0)
                a["zasieg"] += int(r.get("zasieg") or 0)
                a["wydano"] += r.get("wydano") or 0
                a["rozmowy"] += r.get("rozmowy") or 0
        for r in (ads.get("google") or {}).get("rows") or []:
            k = google_code(r).lower()
            if k:
                a = out.setdefault(k, {"zrodlo": "google", "wyswietlenia": 0, "zasieg": 0, "wydano": 0.0, "rozmowy": 0})
                a["wyswietlenia"] += int(r.get("wyswietlenia") or 0)
                a["wydano"] += r.get("koszt") or 0
                a["rozmowy"] += r.get("konwersje") or 0
        for k, a in out.items():
            a["wydano"] = round(a["wydano"], 2)
            a["dni"] = [{"data": d["data"], "wyswietlenia": d.get("wyswietlenia", 0)} for d in self.history(pid, k)]
        return {"posty": posts, "reklamy": out}

    def api_posts(self, pid):
        """Ostatnie posty strony Facebook i konta Instagram projektu z API (do połączenia publikacji z postem)."""
        pub = self._pub()
        page = pub._page(pid) if pub else None
        if not page or not page.get("token"):
            return 409, {"ok": False, "error": "Projekt nie ma połączonej strony Facebook (Marketing → Kanały i studio)."}
        token, items, errs = page["token"], [], []
        try:
            d = meta.graph("%s/published_posts" % page["id"], {"fields": "permalink_url,created_time,message,full_picture",
                                                                "limit": 30, "access_token": token}, self.http)
            for p in d.get("data") or []:
                items.append({"kanal": "facebook", "link": p.get("permalink_url", ""), "data": str(p.get("created_time") or "")[:10],
                              "tekst": str(p.get("message") or "")[:140], "miniatura": p.get("full_picture", ""), "film": False})
        except ApiError as e:
            errs.append("Facebook: %s" % str(e)[:160])
        try:
            d = meta.graph("%s/videos" % page["id"], {"fields": "permalink_url,created_time,description,picture",
                                                       "limit": 20, "access_token": token}, self.http)
            for p in d.get("data") or []:
                link = str(p.get("permalink_url") or "")
                link = link if link.startswith("http") else "https://www.facebook.com" + link
                if not any(i["link"] == link for i in items):
                    items.append({"kanal": "facebook", "link": link, "data": str(p.get("created_time") or "")[:10],
                                  "tekst": str(p.get("description") or "")[:140], "miniatura": p.get("picture", ""), "film": True})
        except ApiError as e:
            errs.append("Facebook (filmy): %s" % str(e)[:160])
        ig = (page.get("ig") or {}).get("id")
        if ig:
            try:
                d = meta.graph("%s/media" % ig, {"fields": "permalink,timestamp,caption,media_type,thumbnail_url,media_url",
                                                  "limit": 30, "access_token": token}, self.http)
                for p in d.get("data") or []:
                    film = p.get("media_type") == "VIDEO"
                    items.append({"kanal": "instagram", "link": p.get("permalink", ""), "data": str(p.get("timestamp") or "")[:10],
                                  "tekst": str(p.get("caption") or "")[:140], "film": film,
                                  "miniatura": p.get("thumbnail_url") if film else p.get("media_url", "")})
            except ApiError as e:
                errs.append("Instagram: %s" % str(e)[:160])
        items = [i for i in items if str(i.get("link") or "").startswith("https://")]
        items.sort(key=lambda i: i["data"], reverse=True)
        return 200, {"ok": True, "posty": items[:60], "bledy": errs}

    def api_get(self, path, query):
        """GET: (kod, obiekt) albo None, gdy ścieżka nie należy do wyników."""
        one = lambda k: (query.get(k) or [""])[0]
        if path in ("/api/wyniki/os", "/api/wyniki/posty-api"):
            p, _ = self._project(one("project"))
            if not p:
                return 404, {"ok": False, "error": "Nie ma takiego projektu."}
            if path == "/api/wyniki/posty-api":
                return self.api_posts(p["id"])
            data, index = self.load_projects(resolve=False)
            return 200, dict(self.timeline(p["id"], data, index), ok=True)
        if path in ("/api/wyniki", "/api/wyniki/historia"):
            p, _ = self._project(one("project"))
            if not p:
                return 404, {"ok": False, "error": "Nie ma takiego projektu."}
            if path == "/api/wyniki/historia":
                return 200, {"ok": True, "days": self.history(p["id"], one("kod"))}
            data, index = self.load_projects(resolve=False)
            return 200, dict(self.report(p["id"], one("okres") or "30", one("kampania"), data, index), ok=True)
        if path == "/api/klienci":
            p, folder = self._project(one("project"))
            if not p:
                return 404, {"ok": False, "error": "Nie ma takiego projektu."}
            data, _ = self.load_projects(resolve=False)
            out = self.klienci.view(p["id"], self.campaign_start(data, p["id"]))
            out["codes"] = self.codes(p["id"], data)
            return 200, dict(out, ok=True)
        return None

    def codes(self, pid, data):
        """Kody do wyboru w formularzu klienta: kody z tytułów publikacji projektu (np. S1) i opublikowane posty."""
        out = []
        for t in data.get("tasks") or []:
            if t.get("project") != pid or t.get("kind") != "publikacja":
                continue
            code = post_code(t)
            if code and code not in (x[0] for x in out):
                out.append((code, t.get("title", "")[:80]))
        return [{"kod": k, "opis": d} for k, d in out][:200]

    def _with_project(self, body, fn):
        p, _ = self._project(body.get("project"))
        if not p:
            return 404, "Nie ma takiego projektu."
        return fn(p["id"])

    def post(self, path, body):
        """POST z WRITE_PATHS: (kod, błąd[, dane])."""
        return self.writes()[path](body)

    def writes(self):
        """POST: ścieżka -> funkcja(body) -> (kod, błąd[, dane])."""
        return {
            "/api/klienci/dodaj": lambda b: self._with_project(b, lambda pid: self.klienci.add(pid, b)),
            "/api/klienci/zmien": lambda b: self._with_project(b, lambda pid: self.klienci.update(pid, b)),
            "/api/klienci/import": lambda b: self._with_project(b, lambda pid: self.klienci.import_csv(pid, b.get("csv"))),
            "/api/wyniki/meta": self.connect_meta,
            "/api/wyniki/meta/odlacz": self.disconnect_meta,
            "/api/wyniki/meta/konto": self.meta_assign,
            "/api/wyniki/polaczenie": self.save_connection,
            "/api/wyniki/google/klucz": self.google_key,
            "/api/wyniki/google/uniewaznij": self.google_revoke,
        }

    # rozmiar ciała żądania dla ścieżek większych niż domyślne 4 KB
    BODY_LIMITS = {"/api/klienci/import": klienci.MAX_CSV + 4096}


WRITE_PATHS = ("/api/klienci/dodaj", "/api/klienci/zmien", "/api/klienci/import",
               "/api/wyniki/meta", "/api/wyniki/meta/odlacz", "/api/wyniki/meta/konto",
               "/api/wyniki/polaczenie", "/api/wyniki/google/klucz", "/api/wyniki/google/uniewaznij")


def derive(r):
    """Koszt rozmowy, koszt klienta i przychód na 1 zł reklamy (None, gdy dzielnik 0)."""
    r["wydano"] = round(r["wydano"], 2)
    r["przychod"] = round(r["przychod"], 2)
    r["kosztRozmowy"] = round(r["wydano"] / r["rozmowy"], 2) if r["wydano"] and r["rozmowy"] else None
    r["kosztKlienta"] = round(r["wydano"] / r["wykonane"], 2) if r["wydano"] and r["wykonane"] else None
    r["zwrot"] = round(r["przychod"] / r["wydano"], 2) if r["wydano"] else None


def google_code(r):
    """Kod wiersza Google Ads: „G · <kampania>” (klient z dziennika z tym kodem łączy się z wydatkiem)."""
    return "G · %s" % (r.get("kampania") or "bez kampanii")


def fmt(v):
    """Liczba po polsku: 60 -> „60”, 41.5 -> „41,5”."""
    v = round(float(v), 2)
    return ("%d" % v if v == int(v) else ("%.2f" % v).rstrip("0")).replace(".", ",")

CODE = re.compile(r"(?<![A-Za-z0-9])([A-Z]{1,2}\d{1,2})(?![A-Za-z0-9])")


def post_code(t):
    """Kod publikacji: kod z tytułu (np. „Opublikuj post S1 „Drzwi””) albo „post DD.MM” z dnia publikacji."""
    m = CODE.search(str(t.get("title") or ""))
    if m:
        return m.group(1)
    day = str(t.get("date") or "")[:10]
    return "post %s.%s" % (day[8:10], day[5:7]) if re.match(r"^\d{4}-\d\d-\d\d$", day) else ""
