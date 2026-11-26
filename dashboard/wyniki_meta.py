"""Odczyt z Meta (Graph API v26, tylko GET): statystyki postów Facebooka i Instagrama, reklamy (Marketing API).

Panel niczego w Meta nie zmienia: wszystkie wywołania to GET. Nazwy metryk: Meta w 2025 r. zastąpiła część metryk
post_impressions* metrykami „views”, więc panel pyta o listę kandydatów i pomija te, których v26 nie zwraca
(błąd #100 „metric”); nieobsługiwane nazwy zapamiętuje (bad), żeby nie pytać o nie przy każdym odczycie.
"""
import json
import re
import urllib.parse

from publikacja import FB, ApiError, http as default_http

# kandydaci, w kolejności: pierwsza dostępna wartość wygrywa
FB_POST_METRICS = ("post_media_view", "post_impressions", "post_total_media_view_unique", "post_impressions_unique",
                   "post_clicks")
FB_VIDEO_METRICS = ("blue_reels_play_count", "fb_reels_total_plays", "total_video_views", "post_video_views",
                    "total_video_impressions_unique", "post_impressions_unique")
IG_METRICS = ("reach", "views", "likes", "comments", "shares", "saved", "total_interactions")
IG_REELS_METRICS = ("ig_reels_avg_watch_time", "ig_reels_video_view_total_time")
CONVERSATION = "onsite_conversion.messaging_conversation_started_7d"
AD_FIELDS = "ad_id,ad_name,adset_name,campaign_name,spend,impressions,reach,frequency,clicks,ctr,cpm,actions,cost_per_action_type"


class PermError(ApiError):
    """Brak uprawnienia albo wygasły token: odczyt się nie powtórzy, dopóki właściciel nie połączy ponownie."""


class MetricError(ApiError):
    pass


def graph(path, params, http=None):
    """GET {FB}/{path}?params -> dict. Błędy Graph API jako PermError, MetricError albo ApiError (bez tokenu w treści)."""
    url = path if path.startswith("https://") else "%s/%s?%s" % (FB, path.lstrip("/"), urllib.parse.urlencode(params))
    status, _, raw = (http or default_http)("GET", url)
    try:
        data = json.loads(raw.decode("utf-8") or "{}")
    except (ValueError, UnicodeDecodeError):
        data = {}
    if status < 400 and not (isinstance(data, dict) and data.get("error")):
        return data if isinstance(data, dict) else {}
    err = (data.get("error") if isinstance(data, dict) else None) or {}
    code, msg = err.get("code"), str(err.get("message") or "")[:200]
    msg = re.sub(r"access_token=[^&\s]+", "access_token=…", msg)
    if code == 190 or status == 401:
        raise PermError("token wygasł albo został unieważniony")
    if code in (10, 200, 3) or (isinstance(code, int) and 200 <= code < 300) or "permission" in msg.lower():
        raise PermError("brak uprawnienia: %s" % msg if msg else "brak uprawnienia")
    if code == 100 and "metric" in msg.lower():
        raise MetricError(msg)
    if code == 100 and ("does not exist" in msg.lower() or "nonexisting" in msg.lower()):
        raise ApiError("post nie istnieje (usunięty?)")
    raise ApiError("błąd %s%s" % (code or status, ": " + msg if msg else ""))


def insights(obj, edge, metrics, token, bad, http=None, extra=None):
    """{metryka: liczba} z /{obj}/{edge}. Metryki z bad pomija; nieznane dopisuje do bad (pyta po jednej)."""
    want = [m for m in metrics if m not in bad]
    if not want:
        return {}

    def ask(names):
        d = graph("%s/%s" % (obj, edge), dict(extra or {}, metric=",".join(names), access_token=token), http)
        out = {}
        for row in d.get("data") or []:
            vals = row.get("values") or []
            v = vals[-1].get("value") if vals else row.get("total_value", {}).get("value")
            if isinstance(v, dict):                 # np. post_clicks_by_type
                v = sum(x for x in v.values() if isinstance(x, (int, float)))
            if isinstance(v, (int, float)):
                out[row.get("name")] = v
        return out

    try:
        return ask(want)
    except MetricError:
        out = {}
        for m in want:
            try:
                out.update(ask([m]))
            except MetricError:
                bad.add(m)
        return out


def first(d, names):
    return next((d[n] for n in names if isinstance(d.get(n), (int, float))), None)


def fb_target(link):
    """Link posta Facebooka -> ("post", id) / ("video", id) / ("szukaj", link) (pfbid, link ręczny)."""
    s = str(link or "")
    m = re.search(r"facebook\.com/(?:reel|[^/]+/videos|watch/\?v=|video\.php\?v=)/?(\d+)", s)
    if m:
        return "video", m.group(1)
    m = re.search(r"facebook\.com/(\d+_\d+)(?:[/?#]|$)", s)
    if m:
        return "post", m.group(1)
    m = re.search(r"facebook\.com/(\d+)/posts/(\d+)", s)
    if m:
        return "post", "%s_%s" % (m.group(1), m.group(2))
    m = re.search(r"[?&]story_fbid=(\d+)&id=(\d+)", s)
    if m:
        return "post", "%s_%s" % (m.group(2), m.group(1))
    return "szukaj", s


def _plain(link):
    s = re.sub(r"[?#].*$", "", str(link or "")).rstrip("/").lower()
    return re.sub(r"^https?://(www\.|m\.)?", "", s)


def read_facebook(page, link, known, bad, http=None):
    """Statystyki posta strony. known: {"kind", "id"} z poprzedniego odczytu albo {}. -> (known, liczby)."""
    token = page["token"]
    kind, oid = (known.get("kind"), known.get("id")) if known.get("id") else fb_target(link)
    if kind == "szukaj":
        want = _plain(link)
        d = graph("%s/published_posts" % page["id"], {"fields": "id,permalink_url", "limit": 100, "access_token": token}, http)
        hit = next((p for p in d.get("data") or [] if _plain(p.get("permalink_url")) == want), None)
        if not hit:
            raise ApiError("nie znaleziono posta na stronie (sprawdź link)")
        kind, oid = "post", hit["id"]
    out = {}
    if kind == "video":
        m = insights(oid, "video_insights", FB_VIDEO_METRICS, token, bad, http)
        out["wyswietlenia"] = first(m, FB_VIDEO_METRICS[:4])
        out["zasieg"] = first(m, FB_VIDEO_METRICS[4:])
    else:
        m = insights(oid, "insights", FB_POST_METRICS, token, bad, http)
        out["wyswietlenia"] = first(m, ("post_media_view", "post_impressions"))
        out["zasieg"] = first(m, ("post_total_media_view_unique", "post_impressions_unique"))
        out["klikniecia"] = m.get("post_clicks")
        f = graph(oid, {"fields": "reactions.summary(total_count).limit(0),comments.summary(total_count).limit(0),shares",
                        "access_token": token}, http)
        out["reakcje"] = ((f.get("reactions") or {}).get("summary") or {}).get("total_count")
        out["komentarze"] = ((f.get("comments") or {}).get("summary") or {}).get("total_count")
        out["udostepnienia"] = (f.get("shares") or {}).get("count", 0 if f else None)
    vals = [out.get(k) for k in ("reakcje", "komentarze", "udostepnienia")]
    if any(isinstance(v, (int, float)) for v in vals):
        out["interakcje"] = sum(v for v in vals if isinstance(v, (int, float)))
    return {"kind": kind, "id": oid}, {k: v for k, v in out.items() if v is not None}


def read_instagram(page, link, known, bad, http=None):
    """Statystyki posta Instagrama (konto firmowe połączone ze stroną). -> (known, liczby)."""
    token, ig = page["token"], (page.get("ig") or {}).get("id")
    if not ig:
        raise ApiError("strona nie ma połączonego konta Instagram")
    mid, reels = known.get("id"), known.get("reels")
    if not mid:
        want = _plain(link).replace("/reel/", "/p/")
        d = graph("%s/media" % ig, {"fields": "id,permalink,media_product_type", "limit": 50, "access_token": token}, http)
        hit = next((p for p in d.get("data") or [] if _plain(p.get("permalink")).replace("/reel/", "/p/") == want), None)
        if not hit:
            raise ApiError("nie znaleziono posta na koncie Instagram (sprawdź link)")
        mid, reels = hit["id"], hit.get("media_product_type") == "REELS"
    m = insights(mid, "insights", IG_METRICS + (IG_REELS_METRICS if reels else ()), token, bad, http)
    out = {"zasieg": m.get("reach"), "wyswietlenia": m.get("views"), "reakcje": m.get("likes"),
           "komentarze": m.get("comments"), "udostepnienia": m.get("shares"), "zapisania": m.get("saved"),
           "interakcje": m.get("total_interactions"), "czasOgladania": first(m, IG_REELS_METRICS)}
    return {"kind": "reels" if reels else "post", "id": mid, "reels": bool(reels)}, {k: v for k, v in out.items() if v is not None}


# ---------- reklamy (Marketing API, ads_read) ----------
def ad_accounts(token, http=None):
    """Konta reklamowe widoczne dla tokenu: [{"id": "act_…", "name", "status"}]."""
    d = graph("me/adaccounts", {"fields": "id,name,account_status", "limit": 100, "access_token": token}, http)
    return [{"id": str(a.get("id")), "name": str(a.get("name") or ""), "status": a.get("account_status")}
            for a in d.get("data") or [] if str(a.get("id") or "").startswith("act_")]


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _action(actions, kind):
    return sum(_num(a.get("value")) for a in actions or [] if a.get("action_type") == kind)


AD_CODE = re.compile(r"^\s*([A-Za-z]{1,3}\d{1,3})(?=\s|·|-|–|:|\||$)")


def ad_code(name):
    """„S1 · Drzwi od 1590 · 2026-11-28” -> "S1"; bez kodu na początku nazwy -> ""."""
    m = AD_CODE.match(str(name or ""))
    return m.group(1).upper() if m else ""


def ad_row(r):
    """Wiersz insights (level=ad, time_increment=1) -> wiersz zapisu panelu."""
    return {"data": str(r.get("date_start") or "")[:10], "ad": str(r.get("ad_id") or ""), "nazwa": str(r.get("ad_name") or "")[:200],
            "zestaw": str(r.get("adset_name") or "")[:200], "kampania": str(r.get("campaign_name") or "")[:200],
            "kod": ad_code(r.get("ad_name")), "wydano": round(_num(r.get("spend")), 2),
            "wyswietlenia": int(_num(r.get("impressions"))), "zasieg": int(_num(r.get("reach"))),
            "czestotliwosc": round(_num(r.get("frequency")), 2), "klikniecia": int(_num(r.get("clicks"))),
            "rozmowy": int(_action(r.get("actions"), CONVERSATION))}


def ads_insights(act, token, since, until, http=None, daily=True):
    """Dzienne wiersze reklam konta act_… od since do until (RRRR-MM-DD), z kolejnymi stronami."""
    params = {"level": "ad", "fields": AD_FIELDS, "time_range": json.dumps({"since": since, "until": until}),
              "limit": 500, "access_token": token}
    if daily:
        params["time_increment"] = 1
    d = graph("%s/insights" % act, params, http)
    rows = list(d.get("data") or [])
    for _ in range(50):
        nxt = (d.get("paging") or {}).get("next")
        if not nxt or not nxt.startswith(FB):
            break
        d = graph(nxt, {}, http)
        rows += d.get("data") or []
    return rows


# ---------- połączenie pozycji osi publikacji z istniejącą reklamą (tylko odczyt) ----------
ADS_MANAGER = "https://adsmanager.facebook.com/adsmanager/manage/ads"
AD_LINK = re.compile(r"^https://adsmanager\.facebook\.com/adsmanager/manage/ads\?(?:[^#\s]*&)?selected_ad_ids=(\d{1,30})(?:[&#]|$)")
AD_LIST_FIELDS = "id,name,effective_status,created_time,campaign{name},creative{thumbnail_url,title,body}"
AD_STATES = {"ACTIVE": "aktywna", "PAUSED": "wstrzymana", "CAMPAIGN_PAUSED": "kampania wstrzymana",
             "ADSET_PAUSED": "zestaw wstrzymany", "PENDING_REVIEW": "w weryfikacji", "IN_PROCESS": "w weryfikacji",
             "PREAPPROVED": "wstępnie zatwierdzona", "DISAPPROVED": "odrzucona", "WITH_ISSUES": "z problemami",
             "PENDING_BILLING_INFO": "brak płatności", "ARCHIVED": "zarchiwizowana", "DELETED": "usunięta"}


def ad_link(act, ad_id):
    """Link reklamy w Menedżerze reklam: zapisany w polu „link:” pozycji osi (jak link posta)."""
    return "%s?%s" % (ADS_MANAGER, urllib.parse.urlencode({"act": str(act).replace("act_", ""), "selected_ad_ids": ad_id}))


def ad_link_id(link):
    """Id reklamy z linku Menedżera reklam albo ""."""
    m = AD_LINK.match(str(link or "").strip())
    return m.group(1) if m else ""


def ad_list(act, token, http=None, limit=50):
    """Ostatnie reklamy konta act_… (GET /act_…/ads): [{"id", "nazwa", "stan", "data", "kampania", "miniatura", "tytul", "tekst", "link"}]."""
    d = graph("%s/ads" % act, {"fields": AD_LIST_FIELDS, "limit": limit, "access_token": token}, http)
    out = []
    for a in d.get("data") or []:
        aid = str(a.get("id") or "")
        if not aid.isdigit():
            continue
        cr = a.get("creative") or {}
        st = str(a.get("effective_status") or "")
        thumb = str(cr.get("thumbnail_url") or "")
        out.append({"id": aid, "nazwa": str(a.get("name") or "")[:200], "stan": AD_STATES.get(st, st.lower().replace("_", " ")),
                    "aktywna": st == "ACTIVE", "data": str(a.get("created_time") or "")[:10],
                    "kampania": str((a.get("campaign") or {}).get("name") or "")[:200],
                    "miniatura": thumb if thumb.startswith("https://") else "",
                    "tytul": str(cr.get("title") or "")[:140], "tekst": str(cr.get("body") or "")[:140],
                    "link": ad_link(act, aid)})
    out.sort(key=lambda x: x["data"], reverse=True)
    return out[:limit]


def ad_totals(ad_id, token, http=None):
    """Nazwa i wyniki jednej reklamy od początku (gdy panel nie ma jej dziennych wierszy): {"nazwa", "stan", liczby}."""
    d = graph(str(ad_id), {"fields": "name,effective_status,insights.date_preset(maximum){spend,impressions,reach,clicks,actions}",
                           "access_token": token}, http)
    r = ((d.get("insights") or {}).get("data") or [{}])[0]
    st = str(d.get("effective_status") or "")
    return {"nazwa": str(d.get("name") or "")[:200], "stan": AD_STATES.get(st, st.lower().replace("_", " ")),
            "wydano": round(_num(r.get("spend")), 2), "wyswietlenia": int(_num(r.get("impressions"))),
            "zasieg": int(_num(r.get("reach"))), "klikniecia": int(_num(r.get("clicks"))),
            "rozmowy": int(_action(r.get("actions"), CONVERSATION))}
