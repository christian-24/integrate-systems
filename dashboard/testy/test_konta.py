"""Logowanie Meta, Google Ads i LinkedIn przez OAuth (konta.py): adres logowania, powrót, konta z jednego
logowania, wybór konta w projekcie, odczyt Google Ads przez API i trasa powrotu bez sesji."""
import base64
import datetime
import json
import os
import stat
import urllib.error
import urllib.parse
import urllib.request

from wspolne import Baza, projekt, server

import konta  # noqa: E402
import publikacja  # noqa: E402
import wyniki  # noqa: E402

NOW = datetime.datetime(2026, 11, 26, 7, 0)
SECRET = "a" * 32
GCLIENT = {"client_id": "123-abc.apps.googleusercontent.com", "client_secret": "sekret-google"}


def idtoken(email):
    body = base64.urlsafe_b64encode(json.dumps({"email": email}).encode()).decode().rstrip("=")
    return "x." + body + ".y"


class Api:
    """Atrapa Facebooka, Google (OAuth i Google Ads API) i LinkedIn."""

    def __init__(self):
        self.calls = []

    def __call__(self, method, url, headers=None, body=None, timeout=120):
        self.calls.append((method, url, headers or {}, body))
        ok = lambda d: (200, {}, json.dumps(d).encode("utf-8"))
        q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        if "graph.facebook.com" in url:
            assert method == "GET"
            if "/oauth/access_token" in url:
                if "code" in q:
                    assert q["redirect_uri"] == ["https://panel.test/api/konta/powrot"]
                    return ok({"access_token": "KROTKI"})
                return ok({"access_token": "FB-DLUGI", "expires_in": 5184000})
            if "/me/adaccounts" in url:
                return ok({"data": [{"id": "act_1", "name": "Opisarnia"}]})
            if "/me/businesses" in url:
                return ok({"data": [{"name": "Firma", "owned_ad_accounts": {"data": [{"id": "act_2", "name": "Shield"}]},
                                     "client_ad_accounts": {"data": [{"id": "act_3", "name": "Oprogramowani"},
                                                                     {"id": "act_1", "name": "Opisarnia"}]}}]})
            if "/me/accounts" in url:
                return ok({"data": [{"id": "55", "name": "Strona S", "access_token": "STRONA"}]})
            if "/me?" in url:
                return ok({"id": "999", "name": "Jan"})
            if "/insights" in url:
                return ok({"data": []})
        if url == konta.GOOGLE_TOKEN:
            form = urllib.parse.parse_qs(body.decode())
            if form["grant_type"] == ["authorization_code"]:
                return ok({"access_token": "G-AT", "refresh_token": "G-RT", "expires_in": 3600,
                           "id_token": idtoken("wlasciciel@example.com")})
            return ok({"access_token": "G-AT2", "expires_in": 3600})
        if url.startswith(konta.GADS):
            assert headers.get("developer-token") == "DEV-TOKEN-12345"
            if url.endswith("customers:listAccessibleCustomers"):
                return ok({"resourceNames": ["customers/1112223333", "customers/4347711860"]})
            query = json.loads(body.decode())["query"]
            cid = url.split("/customers/")[1].split("/")[0]
            if "FROM customer_client" in query:
                return ok({"results": [{"customerClient": {"id": "5556667777", "descriptiveName": "Opisarnia Ads"}},
                                       {"customerClient": {"id": "8889990000", "descriptiveName": "Pod-MCC",
                                                           "manager": True}}]})
            if "FROM customer" in query:
                mgr = cid == "1112223333"
                return ok({"results": [{"customer": {"id": cid, "descriptiveName": "MCC" if mgr else "Shield & Silent",
                                                     "manager": mgr}}]})
            assert headers.get("login-customer-id") == "1112223333" or cid == "4347711860"
            if "FROM search_term_view" in query:
                return ok({"results": [{"searchTermView": {"searchTerm": "wygłuszanie drzwi"}, "campaign": {"name": "K1"},
                                        "adGroup": {"name": "G1"}, "metrics": {"costMicros": "2500000", "clicks": "2"}}]})
            if "conversion_action_name" in query:
                return ok({"results": [{"campaign": {"name": "K1"}, "adGroup": {"name": "G1"},
                                        "segments": {"conversionActionName": "Połączenie telefoniczne"},
                                        "metrics": {"conversions": 1}}]})
            return ok({"results": [{"campaign": {"name": "K1"}, "adGroup": {"name": "G1"},
                                    "metrics": {"impressions": "120", "clicks": "7", "costMicros": "15500000",
                                                "conversions": 2}}]})
        if url == konta.LI_TOKEN:
            return ok({"access_token": "LI-TOKEN", "expires_in": 5184000})
        if url.endswith("/v2/userinfo"):
            return ok({"sub": "abc123", "name": "Jan K"})
        if "/rest/organizationAcls" in url:
            return ok({"elements": [{"organization": "urn:li:organization:777"}]})
        if "/rest/organizations/777" in url:
            return ok({"localizedName": "Shield & Silent"})
        raise AssertionError(url)


class Konta(Baza):
    def setUp(self):
        super().setUp()
        self.api = Api()
        self.pub = publikacja.Publisher(server.load_projects, server._write_lock, projekt, None, None, None,
                                        data_dir=os.path.join(self.tmp, "publikacja"), http_call=self.api, now=lambda: NOW)
        self.w = wyniki.Wyniki(server.load_projects, server._write_lock, projekt, None, publisher=self.pub,
                               klienci_dir=os.path.join(self.tmp, "klienci"), ads_dir=os.path.join(self.tmp, "reklamy"),
                               http_call=self.api, now=lambda: NOW)
        self.k = self.w.konta = konta.Konta(self.pub, google_client=lambda: GCLIENT, base_url="https://panel.test",
                                            http_call=self.api, now=lambda: NOW)
        self.pid = server.load_projects()[0]["projects"][0]["id"]

    def login(self, prov):
        code, err, extra = self.k.start({"provider": prov, "project": self.pid, "return": "#p-%s-polaczenia" % self.pid})
        self.assertEqual(code, 200, err)
        q = urllib.parse.parse_qs(urllib.parse.urlparse(extra["url"]).query)
        self.assertEqual(q["redirect_uri"], ["https://panel.test/api/konta/powrot"])
        code, target = self.k.back(urllib.parse.urlencode({"state": q["state"][0], "code": "KOD"}))
        self.assertEqual((code, target), (303, "/#p-%s-polaczenia" % self.pid))
        return q

    def test_meta_jedno_logowanie_trzy_konta_i_wybor_w_projekcie(self):
        self.assertEqual(self.k.start({"provider": "meta", "project": self.pid})[0], 409)   # bez danych aplikacji
        self.assertEqual(self.k.save_app({"provider": "meta", "appId": "12345678", "secret": SECRET})[0], 200)
        q = self.login("meta")
        self.assertIn("ads_read", q["scope"][0])
        self.assertTrue(konta.FB_DIALOG.startswith("https://www.facebook.com/v26.0/"))
        st = self.k.status()
        self.assertEqual([a["id"] for a in st["logins"]["meta"][0]["accounts"]], ["act_1", "act_3", "act_2"])
        self.assertNotIn("FB-DLUGI", json.dumps(st))
        self.assertNotIn(SECRET, json.dumps(st))
        # strony do publikacji z tego samego logowania
        self.assertEqual([p["name"] for p in self.pub.status()["facebook"]["pages"]], ["Strona S"])
        path = os.path.join(self.tmp, "publikacja", "logowania.json")
        self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)
        lid = st["logins"]["meta"][0]["id"]
        self.assertEqual(self.w.assign_account({"project": self.pid, "provider": "meta", "login": lid,
                                                "account": "act_9"})[0], 409)
        self.assertEqual(self.w.assign_account({"project": self.pid, "provider": "meta", "login": lid,
                                                "account": "act_2"})[0], 200)
        c = self.w.connection_status()[self.pid]
        self.assertEqual((c["metaAct"], c["metaLogin"]), ("act_2", lid))
        data, index = server.load_projects()
        self.w.meta_tick(data, index)                  # token z logowania, bez meta-reklamy.json
        self.assertTrue(any("act_2/insights" in u and "FB-DLUGI" in u for _, u, _, _ in self.api.calls))

    def test_stan_logowania_zly_i_powtorzony(self):
        self.k.save_app({"provider": "meta", "appId": "12345678", "secret": SECRET})
        self.assertEqual(self.k.back("state=zly&code=x")[0], 409)
        _, _, extra = self.k.start({"provider": "meta", "project": self.pid, "return": "javascript:alert(1)"})
        state = urllib.parse.parse_qs(urllib.parse.urlparse(extra["url"]).query)["state"][0]
        self.assertEqual(self.k.back("state=%s&code=K" % state), (303, "/#marketing"))
        self.assertEqual(self.k.back("state=%s&code=K" % state)[0], 409)          # jednorazowy

    def test_google_konta_przez_menedzera_i_odczyt_dnia(self):
        self.assertEqual(self.k.save_app({"provider": "google", "developerToken": "DEV-TOKEN-12345"})[0], 200)
        q = self.login("google")
        self.assertIn("adwords", q["scope"][0])
        self.assertEqual(q["access_type"], ["offline"])
        L = self.k.status()["logins"]["google"][0]
        self.assertEqual(L["name"], "wlasciciel@example.com")
        self.assertEqual([(a["id"], a["via"]) for a in L["accounts"]], [("555-666-7777", "111-222-3333"),
                                                                        ("434-771-1860", "")])
        self.assertEqual(self.w.assign_account({"project": self.pid, "provider": "google", "login": L["id"],
                                                "account": "555-666-7777"})[0], 200)
        data, index = server.load_projects()
        self.w.google_tick(data, index)
        rows = self.w.ads(self.pid)["google"]["rows"]
        self.assertEqual(len(rows), wyniki.META_BACK)
        r = rows[-1]
        self.assertEqual((r["data"], r["wyswietlenia"], r["koszt"], r["konwersje"], r["telefony"]),
                         ("2026-11-25", 120, 15.5, 2, 1))
        self.assertEqual(self.w.ads(self.pid)["google"]["terms"][-1]["haslo"], "wygłuszanie drzwi")
        n = len(self.api.calls)
        self.w.google_tick(data, index)                # raz dziennie
        self.assertEqual(len(self.api.calls), n)

    def test_google_bez_tokenu_dewelopera(self):
        self.login("google")
        L = self.k.status()["logins"]["google"][0]
        self.assertEqual(L["accounts"], [])
        self.assertIn("tokenu dewelopera", L["error"])
        self.assertEqual(self.k.refresh({"provider": "google", "login": L["id"]})[0], 409)

    def test_linkedin_strona_firmowa_i_profil(self):
        self.assertEqual(self.k.save_app({"provider": "linkedin", "clientId": "77abcdefgh", "secret": "S3kret.123",
                                          "org": True})[0], 200)
        q = self.login("linkedin")
        self.assertIn("r_organization_social", q["scope"][0])
        L = self.k.status()["logins"]["linkedin"][0]
        self.assertEqual(L["accounts"], [{"id": "777", "name": "Shield & Silent", "via": ""}])
        self.assertTrue(self.pub.status()["linkedin"]["connected"])            # publikowanie z tego logowania
        self.assertEqual(self.w.assign_account({"project": self.pid, "provider": "linkedin", "login": L["id"],
                                                "account": "777"})[0], 200)
        li = self.w.connection_status()[self.pid]["linkedin"]
        self.assertEqual((li["rodzaj"], li["organizacja"], li["wniosek"]), ("organizacja", "777", "przyznany"))
        self.assertEqual(self.w.assign_account({"project": self.pid, "provider": "linkedin", "login": L["id"],
                                                "account": ""})[0], 200)
        self.assertEqual(self.w.connection_status()[self.pid]["linkedin"]["rodzaj"], "profil")
        self.assertEqual(self.k.logout({"provider": "linkedin", "login": L["id"]})[0], 200)
        self.assertEqual(self.k.status()["logins"]["linkedin"], [])

    def test_trasa_powrotu_bez_sesji(self):
        import threading
        from http.server import ThreadingHTTPServer
        old = (server.TOKEN, server._wyniki["obj"])
        server.TOKEN, server._wyniki["obj"] = "haslo-panelu", self.w
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        base = "http://127.0.0.1:%d" % httpd.server_address[1]
        try:
            with self.assertRaises(urllib.error.HTTPError) as e:
                urllib.request.urlopen(base + "/api/konta/powrot?state=x&code=y", timeout=10)
            self.assertEqual(e.exception.code, 409)
            self.assertIn("Zaloguj się jeszcze raz", e.exception.read().decode())
        finally:
            httpd.shutdown()
            server.TOKEN, server._wyniki["obj"] = old
