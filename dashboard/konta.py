"""Logowanie do Meta, Google Ads i LinkedIn przez oficjalne strony (OAuth) i konta widoczne z każdego logowania.

Właściciel klika „Zaloguj” w zakładce Połączenia projektu, loguje się na stronie Facebooka, Google albo LinkedIn,
a serwis wraca na GET /api/konta/powrot (bez sesji panelu; chroni go jednorazowy state ważny 15 minut). Panel wymienia
kod na token, odczytuje listę kont (Meta: konta reklamowe z profilu i z firm Business Managera, Google Ads: konta
dostępne dla loginu, także przez konto menedżera, LinkedIn: strony firmowe, którymi zarządza) i zapisuje logowanie.
Jedno logowanie może mieć wiele kont; konto wybiera się osobno w każdym projekcie (przypisanie w polaczenia.json,
wyniki.py). Logowań jednego serwisu może być kilka (różne osoby albo firmy).

Pliki (0600, w katalogu publikacji): aplikacje-logowania.json (identyfikatory i sekrety aplikacji, wpisywane raz),
logowania.json (tokeny i listy kont). Do /api/data idą tylko nazwy, identyfikatory kont i daty, bez tokenów.
Klient Google OAuth jest ten sam co dla Google Drive (google-oauth.json); do listy kont i odczytu wyników Google Ads
potrzebny jest jeszcze token dewelopera Google Ads (Centrum API w koncie menedżera).
"""
import base64
import datetime
import json
import re
import secrets
import threading
import time
import urllib.parse

from publikacja import FB, LI, LI_VERSION, ApiError, http as default_http

PROVIDERS = ("meta", "google", "linkedin")
RETURN_PATH = "/api/konta/powrot"
STATE_TTL = 15 * 60
FB_DIALOG = FB.replace("graph.facebook.com", "www.facebook.com") + "/dialog/oauth"
META_SCOPES = ("ads_read,business_management,pages_show_list,pages_read_engagement,pages_manage_posts,publish_video,"
               "read_insights,instagram_basic,instagram_content_publish,instagram_manage_insights")
GOOGLE_AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN = "https://oauth2.googleapis.com/token"
GOOGLE_SCOPE = "https://www.googleapis.com/auth/adwords openid email"
GADS = "https://googleads.googleapis.com/v26"
LI_AUTH = "https://www.linkedin.com/oauth/v2/authorization"
LI_TOKEN = "https://www.linkedin.com/oauth/v2/accessToken"
LI_SCOPES = "openid profile w_member_social"
LI_ORG_SCOPES = " r_organization_social rw_organization_admin"
MAX_ACCOUNTS = 200
NAMES = {"meta": "Facebook", "google": "Google", "linkedin": "LinkedIn"}


def _jwt_email(id_token):
    """E-mail z id_token Google (prosto z punktu tokenów przez TLS, bez weryfikacji podpisu: tylko etykieta)."""
    try:
        part = str(id_token).split(".")[1]
        d = json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)).decode("utf-8"))
        return str(d.get("email") or "")
    except (IndexError, ValueError, UnicodeDecodeError):
        return ""


def _load(status, raw, what):
    try:
        d = json.loads(raw.decode("utf-8") or "{}")
    except (ValueError, UnicodeDecodeError, AttributeError):
        d = {}
    if status >= 400 or not isinstance(d, dict) or d.get("error"):
        err = d.get("error") if isinstance(d, dict) else None
        msg = err.get("message") if isinstance(err, dict) else (d.get("error_description") if isinstance(d, dict) else "")
        raise ApiError("%s: %s" % (what, str(msg or err or "błąd %d" % status)[:200]))
    return d


def gads_customer(value):
    """„434-771-1860” albo „4347711860” -> „434-771-1860”; inaczej ''."""
    d = re.sub(r"\D", "", str(value or ""))
    return "%s-%s-%s" % (d[:3], d[3:6], d[6:]) if len(d) == 10 else ""


class Konta:
    def __init__(self, publisher, google_client=None, base_url="", http_call=None, now=None):
        self.publisher = publisher                    # Publisher albo funkcja, która go zwraca (pliki 0600)
        self.google_client = google_client or (lambda: None)
        self.base_url = str(base_url or "").rstrip("/")
        self.http = http_call or default_http
        self.now = now or datetime.datetime.now
        self.lock = threading.Lock()
        self.pending = {}                             # state -> {provider, project, return, at}
        self.gtokens = {}                             # login Google -> (access token, ważny do)

    # ---------- pliki ----------
    def _pub(self):
        return self.publisher() if callable(self.publisher) else self.publisher

    def apps(self):
        a = self._pub()._read("aplikacje-logowania.json", {})
        return a if isinstance(a, dict) else {}

    def logins(self):
        d = self._pub()._read("logowania.json", {})
        return {k: [x for x in (d.get(k) or []) if isinstance(x, dict)] for k in PROVIDERS} if isinstance(d, dict) \
            else {k: [] for k in PROVIDERS}

    def _save_logins(self, d):
        self._pub()._write("logowania.json", d)

    def login(self, provider, lid):
        return next((x for x in self.logins().get(provider) or [] if x.get("id") == lid), None)

    @property
    def redirect(self):
        return self.base_url + RETURN_PATH if self.base_url else ""

    # ---------- ustawienia aplikacji (raz) ----------
    def app_ready(self, provider):
        a = self.apps().get(provider) or {}
        if provider == "meta":
            fb = self._pub()._read("facebook.json", {})
            return bool((a.get("appId") or fb.get("appId")) and a.get("secret"))
        if provider == "google":
            return bool(self.google_client())
        return bool(a.get("clientId") and a.get("secret"))

    def save_app(self, body):
        """{"provider", "appId"/"clientId", "secret", "configId"?, "developerToken"?, "org"?}: puste pole = bez zmian."""
        prov = str(body.get("provider") or "")
        if prov not in PROVIDERS:
            return 400, "Nieznany serwis."
        allapps = self.apps()
        a = dict(allapps.get(prov) or {})
        g = lambda k: str(body.get(k) or "").strip()
        if prov == "meta":
            if g("appId") and not re.fullmatch(r"\d{5,20}", g("appId")):
                return 400, "App ID to same cyfry (Meta for Developers → aplikacja → Ustawienia → Podstawowe)."
            if g("secret") and not re.fullmatch(r"[0-9a-f]{20,64}", g("secret")):
                return 400, "App Secret: 32 znaki 0–9 i a–f (Ustawienia → Podstawowe → Klucz tajny aplikacji)."
            if g("configId") and not re.fullmatch(r"\d{5,25}", g("configId")):
                return 400, "Identyfikator konfiguracji logowania to same cyfry."
            for k in ("appId", "secret", "configId"):
                if g(k):
                    a[k] = g(k)
        elif prov == "linkedin":
            if g("clientId") and not re.fullmatch(r"[A-Za-z0-9]{8,40}", g("clientId")):
                return 400, "Client ID z zakładki Auth aplikacji LinkedIn."
            if g("secret") and not re.fullmatch(r"[A-Za-z0-9._=-]{8,120}", g("secret")):
                return 400, "Primary Client Secret z zakładki Auth aplikacji LinkedIn."
            for k in ("clientId", "secret"):
                if g(k):
                    a[k] = g(k)
            if "org" in body:
                a["org"] = bool(body.get("org"))
        else:
            if g("developerToken") and not re.fullmatch(r"[A-Za-z0-9_-]{10,60}", g("developerToken")):
                return 400, "Token dewelopera z Google Ads: Narzędzia → Centrum API (w koncie menedżera)."
            if g("developerToken"):
                a["developerToken"] = g("developerToken")
            if g("loginCustomer") and not gads_customer(g("loginCustomer")):
                return 400, "Konto menedżera: 10 cyfr, np. 123-456-7890."
            if "loginCustomer" in body:
                a["loginCustomer"] = gads_customer(g("loginCustomer"))
        allapps[prov] = a
        self._pub()._write("aplikacje-logowania.json", allapps)
        return 200, ""

    # ---------- stan dla panelu (bez tokenów i sekretów) ----------
    def status(self):
        apps, L, now = self.apps(), self.logins(), self.now().isoformat()
        fb = self._pub()._read("facebook.json", {})
        out = {"redirect": self.redirect, "apps": {
            "meta": {"ready": self.app_ready("meta"), "appId": (apps.get("meta") or {}).get("appId") or fb.get("appId", "")},
            "google": {"ready": self.app_ready("google"), "devToken": bool((apps.get("google") or {}).get("developerToken")),
                       "loginCustomer": (apps.get("google") or {}).get("loginCustomer", "")},
            "linkedin": {"ready": self.app_ready("linkedin"), "org": bool((apps.get("linkedin") or {}).get("org"))}},
            "logins": {}}
        for prov in PROVIDERS:
            out["logins"][prov] = [{"id": x["id"], "name": x.get("name", ""), "at": x.get("at", ""),
                                    "expiresAt": x.get("expiresAt", ""),
                                    "expired": bool(x.get("expiresAt") and x["expiresAt"] < now),
                                    "error": x.get("error", ""),
                                    "accounts": [{"id": a["id"], "name": a.get("name", ""), "via": a.get("via", "")}
                                                 for a in x.get("accounts") or []]}
                                   for x in L.get(prov) or []]
        return out

    # ---------- logowanie: adres strony serwisu ----------
    def start(self, body):
        prov, project = str(body.get("provider") or ""), str(body.get("project") or "")
        if prov not in PROVIDERS:
            return 400, "Nieznany serwis.", {}
        if not self.redirect:
            return 409, "Logowanie wymaga publicznego adresu panelu (PANEL_PUBLIC_URL).", {}
        if not self.app_ready(prov):
            return 409, "Najpierw wpisz dane aplikacji %s (jeden raz)." % NAMES[prov], {}
        ret = str(body.get("return") or "")
        ret = "/" + ret if re.fullmatch(r"#[A-Za-z0-9_/?&=.%+~:-]{1,500}", ret) else "/#marketing"
        state = secrets.token_urlsafe(24)
        with self.lock:
            t = time.time()
            self.pending = {k: v for k, v in self.pending.items() if t - v["at"] < STATE_TTL}
            self.pending[state] = {"provider": prov, "project": project, "return": ret, "at": t}
        a = self.apps().get(prov) or {}
        if prov == "meta":
            app_id = a.get("appId") or self._pub()._read("facebook.json", {}).get("appId", "")
            q = {"client_id": app_id, "redirect_uri": self.redirect, "state": state, "response_type": "code"}
            if a.get("configId"):
                q["config_id"] = a["configId"]          # Facebook Login for Business (aplikacja typu Firma)
            else:
                q["scope"] = META_SCOPES
            url = FB_DIALOG + "?" + urllib.parse.urlencode(q)
        elif prov == "google":
            c = self.google_client()
            url = GOOGLE_AUTH + "?" + urllib.parse.urlencode({
                "client_id": c["client_id"], "redirect_uri": self.redirect, "response_type": "code",
                "scope": GOOGLE_SCOPE, "access_type": "offline", "prompt": "consent select_account", "state": state})
        else:
            url = LI_AUTH + "?" + urllib.parse.urlencode({
                "response_type": "code", "client_id": a["clientId"], "redirect_uri": self.redirect, "state": state,
                "scope": LI_SCOPES + (LI_ORG_SCOPES if a.get("org") else "")})
        return 200, "", {"url": url}

    # ---------- powrót z serwisu ----------
    def back(self, query):
        """GET /api/konta/powrot: (kod, tekst albo adres powrotu przy 303)."""
        q = urllib.parse.parse_qs(str(query or ""))
        state, code = (q.get("state") or [""])[0], (q.get("code") or [""])[0]
        with self.lock:
            pend = None
            for k in list(self.pending):
                if state and secrets.compare_digest(k.encode(), state.encode()):
                    pend = self.pending.pop(k)
            if not pend or time.time() - pend["at"] > STATE_TTL:
                return 409, "Logowanie wygasło albo adres jest nieprawidłowy. Zaloguj się jeszcze raz w panelu."
        prov = pend["provider"]
        if not code:
            return 400, "%s nie przekazał zgody. Zaloguj się jeszcze raz w panelu." % NAMES[prov]
        try:
            rec = getattr(self, "_back_" + prov)(code)
        except (ApiError, KeyError, TypeError, ValueError) as e:
            return 502, "%s: logowanie nie udało się (%s). Zaloguj się jeszcze raz w panelu." % (NAMES[prov], str(e)[:200])
        rec["at"] = self.now().isoformat(timespec="seconds")
        with self.lock:
            L = self.logins()
            L[prov] = [x for x in L[prov] if x.get("id") != rec["id"]] + [rec]
            self._save_logins(L)
        return 303, pend["return"]

    # Meta: token długoterminowy (60 dni), konta reklamowe z profilu i z firm, strony do publikacji
    def _back_meta(self, code):
        a = self.apps().get("meta") or {}
        app_id = a.get("appId") or self._pub()._read("facebook.json", {}).get("appId", "")
        g = lambda path, params, what: _load(*self.http("GET", "%s/%s?%s" % (FB, path, urllib.parse.urlencode(params)))[::2],
                                             what=what)
        short = g("oauth/access_token", {"client_id": app_id, "client_secret": a["secret"], "redirect_uri": self.redirect,
                                         "code": code}, "Wymiana kodu")["access_token"]
        tok = g("oauth/access_token", {"grant_type": "fb_exchange_token", "client_id": app_id, "client_secret": a["secret"],
                                       "fb_exchange_token": short}, "Token długoterminowy")
        token = tok["access_token"]
        me = g("me", {"fields": "id,name", "access_token": token}, "Profil")
        accounts = {}
        d = g("me/adaccounts", {"fields": "id,name,account_status", "limit": MAX_ACCOUNTS, "access_token": token},
              "Konta reklamowe")
        for x in d.get("data") or []:
            accounts[str(x.get("id"))] = {"id": str(x.get("id")), "name": str(x.get("name") or "")}
        try:                                          # konta firm z Business Managera (business_management)
            d = g("me/businesses", {"fields": "name,owned_ad_accounts.limit(%d){id,name},client_ad_accounts.limit(%d){id,name}"
                                    % (MAX_ACCOUNTS, MAX_ACCOUNTS), "limit": 50, "access_token": token}, "Firmy")
            for b in d.get("data") or []:
                for edge in ("owned_ad_accounts", "client_ad_accounts"):
                    for x in (b.get(edge) or {}).get("data") or []:
                        aid = str(x.get("id") or "")
                        if aid and aid not in accounts:
                            accounts[aid] = {"id": aid, "name": str(x.get("name") or ""), "via": str(b.get("name") or "")}
        except ApiError:
            pass
        rec = {"id": "fb-" + str(me["id"]), "name": str(me.get("name") or "Facebook"), "token": token,
               "accounts": [v for k, v in sorted(accounts.items(), key=lambda kv: kv[1]["name"].lower())
                            if k.startswith("act_")][:MAX_ACCOUNTS]}
        if tok.get("expires_in"):
            rec["expiresAt"] = (self.now() + datetime.timedelta(seconds=int(tok["expires_in"]))).isoformat(timespec="seconds")
        res = self._pub().adopt_facebook(app_id, token, merge=True)   # strony i Instagram do publikacji
        if res[0] != 200:
            rec["error"] = "Strony: " + str(res[1])[:200]
        return rec

    # Google: refresh token, e-mail, konta Google Ads (z tokenem dewelopera)
    def _back_google(self, code):
        c = self.google_client()
        data = urllib.parse.urlencode({"code": code, "client_id": c["client_id"], "client_secret": c["client_secret"],
                                       "redirect_uri": self.redirect, "grant_type": "authorization_code"}).encode()
        tok = _load(*self.http("POST", GOOGLE_TOKEN, {"Content-Type": "application/x-www-form-urlencoded"}, data)[::2],
                    what="Wymiana kodu")
        if not tok.get("refresh_token"):
            raise ApiError("Google nie wydał stałego dostępu")
        email = _jwt_email(tok.get("id_token")) or "Konto Google"
        rec = {"id": "g-" + re.sub(r"[^a-z0-9]+", "-", email.lower()).strip("-")[:60], "name": email,
               "refresh": tok["refresh_token"], "accounts": []}
        self.gtokens[rec["id"]] = (tok["access_token"], time.time() + int(tok.get("expires_in") or 3600) - 60)
        try:
            rec["accounts"] = self.google_accounts(rec)
        except ApiError as e:
            rec["error"] = str(e)[:200]
        return rec

    def google_access(self, rec):
        hit = self.gtokens.get(rec["id"])
        if hit and hit[1] > time.time():
            return hit[0]
        c = self.google_client()
        if not c:
            raise ApiError("brak klienta Google OAuth")
        data = urllib.parse.urlencode({"client_id": c["client_id"], "client_secret": c["client_secret"],
                                       "refresh_token": rec["refresh"], "grant_type": "refresh_token"}).encode()
        tok = _load(*self.http("POST", GOOGLE_TOKEN, {"Content-Type": "application/x-www-form-urlencoded"}, data)[::2],
                    what="Odświeżenie dostępu Google")
        self.gtokens[rec["id"]] = (tok["access_token"], time.time() + int(tok.get("expires_in") or 3600) - 60)
        return tok["access_token"]

    def gads_search(self, rec, customer, query, login_customer=""):
        """Wiersze GAQL (REST googleAds:search, wszystkie strony). Pola jak w skrypcie Google Ads (camelCase)."""
        dev = (self.apps().get("google") or {}).get("developerToken")
        if not dev:
            raise ApiError("brak tokenu dewelopera Google Ads")
        cid = re.sub(r"\D", "", customer)
        h = {"Authorization": "Bearer " + self.google_access(rec), "developer-token": dev,
             "Content-Type": "application/json"}
        lc = re.sub(r"\D", "", login_customer or (self.apps().get("google") or {}).get("loginCustomer") or "")
        if lc:
            h["login-customer-id"] = lc
        out, page = [], ""
        for _ in range(50):
            body = {"query": query}
            if page:
                body["pageToken"] = page
            d = _load(*self.http("POST", "%s/customers/%s/googleAds:search" % (GADS, cid), h,
                                 json.dumps(body).encode())[::2], what="Google Ads")
            out += d.get("results") or []
            page = d.get("nextPageToken") or ""
            if not page:
                break
        return out

    def google_accounts(self, rec):
        dev = (self.apps().get("google") or {}).get("developerToken")
        if not dev:
            raise ApiError("lista kont wymaga tokenu dewelopera Google Ads")
        h = {"Authorization": "Bearer " + self.google_access(rec), "developer-token": dev}
        d = _load(*self.http("GET", GADS + "/customers:listAccessibleCustomers", h)[::2], what="Konta Google Ads")
        found = {}
        for rn in (d.get("resourceNames") or [])[:30]:
            cid = rn.split("/")[-1]
            try:
                r = self.gads_search(rec, cid, "SELECT customer.id, customer.descriptive_name, customer.manager FROM customer",
                                     login_customer=cid)
            except ApiError:
                continue
            c = (r[0] if r else {}).get("customer") or {}
            if c.get("manager"):
                try:
                    kids = self.gads_search(rec, cid, "SELECT customer_client.id, customer_client.descriptive_name, "
                                            "customer_client.manager FROM customer_client WHERE customer_client.level = 1",
                                            login_customer=cid)
                except ApiError:
                    kids = []
                for k in kids:
                    cc = k.get("customerClient") or {}
                    kid = gads_customer(cc.get("id"))
                    if kid and not cc.get("manager") and kid not in found:
                        found[kid] = {"id": kid, "name": str(cc.get("descriptiveName") or ""), "via": gads_customer(cid)}
            else:
                kid = gads_customer(c.get("id") or cid)
                found.setdefault(kid, {"id": kid, "name": str(c.get("descriptiveName") or "")})
        return sorted(found.values(), key=lambda x: (x["name"].lower(), x["id"]))[:MAX_ACCOUNTS]

    def refresh(self, body):
        """Ponowne odczytanie listy kont logowania (Google po dodaniu tokenu dewelopera)."""
        prov, lid = str(body.get("provider") or ""), str(body.get("login") or "")
        if prov != "google":
            return 400, "Listę kont Meta i LinkedIn odświeża ponowne zalogowanie."
        with self.lock:
            L = self.logins()
            rec = next((x for x in L["google"] if x.get("id") == lid), None)
            if not rec:
                return 404, "Nie ma takiego logowania."
            try:
                rec["accounts"], rec["error"] = self.google_accounts(rec), ""
            except ApiError as e:
                rec["error"] = str(e)[:200]
                self._save_logins(L)
                return 409, "Google Ads: %s" % rec["error"]
            self._save_logins(L)
        return 200, "", {"accounts": len(rec["accounts"])}

    # LinkedIn: token (60 dni), profil, strony firmowe (przy zgodzie na Community Management API)
    def _back_linkedin(self, code):
        a = self.apps().get("linkedin") or {}
        data = urllib.parse.urlencode({"grant_type": "authorization_code", "code": code, "client_id": a["clientId"],
                                       "client_secret": a["secret"], "redirect_uri": self.redirect}).encode()
        tok = _load(*self.http("POST", LI_TOKEN, {"Content-Type": "application/x-www-form-urlencoded"}, data)[::2],
                    what="Wymiana kodu")
        token = tok["access_token"]
        me = _load(*self.http("GET", LI + "/v2/userinfo", {"Authorization": "Bearer " + token})[::2], what="Profil")
        exp = (self.now() + datetime.timedelta(seconds=int(tok.get("expires_in") or 60 * 86400))).isoformat(timespec="seconds")
        rec = {"id": "li-" + re.sub(r"[^A-Za-z0-9_-]", "", str(me["sub"]))[:60], "name": str(me.get("name") or "LinkedIn"),
               "token": token, "sub": str(me["sub"]), "expiresAt": exp, "accounts": []}
        if tok.get("refresh_token"):
            rec["refresh"] = tok["refresh_token"]
        if a.get("org"):
            h = {"Authorization": "Bearer " + token, "LinkedIn-Version": LI_VERSION, "X-Restli-Protocol-Version": "2.0.0"}
            try:
                d = _load(*self.http("GET", LI + "/rest/organizationAcls?q=roleAssignee&role=ADMINISTRATOR&state=APPROVED",
                                     h)[::2], what="Strony firmowe")
                for el in (d.get("elements") or [])[:20]:
                    oid = str(el.get("organization") or "").rsplit(":", 1)[-1]
                    if not oid.isdigit():
                        continue
                    name = ""
                    try:
                        name = _load(*self.http("GET", LI + "/rest/organizations/" + oid, h)[::2],
                                     what="Strona").get("localizedName") or ""
                    except ApiError:
                        pass
                    rec["accounts"].append({"id": oid, "name": str(name)})
            except ApiError as e:
                rec["error"] = str(e)[:200]
        # publikowanie na LinkedIn (publikacja.py czyta linkedin.json): ostatnie logowanie
        self._pub()._write("linkedin.json", {"token": token, "sub": rec["sub"], "name": rec["name"], "expiresAt": exp})
        return rec

    def logout(self, body):
        prov, lid = str(body.get("provider") or ""), str(body.get("login") or "")
        if prov not in PROVIDERS:
            return 400, "Nieznany serwis."
        with self.lock:
            L = self.logins()
            n = len(L[prov])
            L[prov] = [x for x in L[prov] if x.get("id") != lid]
            if len(L[prov]) == n:
                return 404, "Nie ma takiego logowania."
            self._save_logins(L)
        self.gtokens.pop(lid, None)
        return 200, ""

    # ---------- dla wyniki.py ----------
    def token_for(self, provider, lid, account=""):
        """Token logowania (Meta, LinkedIn) albo None; bez lid: pierwsze logowanie, które widzi konto."""
        for x in self.logins().get(provider) or []:
            if (lid and x.get("id") == lid) or (not lid and account and
                                                 any(a.get("id") == account for a in x.get("accounts") or [])):
                return x.get("token")
        return None
