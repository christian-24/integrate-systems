"""Koszty Hetznera w panelu: szacunek z API Hetzner Cloud, bez faktur (Hetzner nie udostępnia faktur przez API).

Tokeny (tylko do odczytu) w pliku PANEL_HETZNER_TOKENY (domyślnie /etc/integrate/hetzner.tokeny), wiersze
„nazwa=token”: jeden wiersz na projekt Hetzner Cloud. Plik ustawia `sudo ustaw-token-hetznera`.

Szacunek tak jak rozlicza Hetzner: w każdym miesiącu kalendarzowym godziny działania × stawka godzinowa,
najwyżej stawka miesięczna. Liczone: serwery (z kopiami zapasowymi +20%), adresy IPv4 i dyski (volumes).
Kwoty brutto w EUR; kurs EUR z tabeli A NBP. Usuniętych zasobów API już nie pokazuje: nie ma ich w sumie.
Tokenów nie zapisujemy w wyniku ani w dzienniku.
"""
import datetime
import json
import math
import os
import threading
import time
import urllib.error
import urllib.request

API = "https://api.hetzner.cloud/v1"
NBP = "https://api.nbp.pl/api/exchangerates/rates/a/eur/?format=json"
TTL = 6 * 3600          # sekundy między odczytami API
RETRY = 15 * 60         # po błędzie ponowna próba po tylu sekundach
BACKUP_SHARE = 0.20     # kopie zapasowe serwera: 20% ceny serwera
UTC = datetime.timezone.utc


def tokens_file():
    return os.path.expanduser(os.environ.get("PANEL_HETZNER_TOKENY", "").strip() or "/etc/integrate/hetzner.tokeny")


def read_tokens(path):
    """[(nazwa, token)] z pliku albo None, gdy pliku nie ma lub nie da się go odczytać."""
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return None
    out = []
    for line in text.splitlines():
        name, sep, token = line.strip().partition("=")
        if sep and name.strip() and token.strip() and not name.startswith("#"):
            out.append((name.strip()[:40], token.strip()))
    return out


def http_get(url, token=None, timeout=20):
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "panel-projektow"})
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _all(get, token, path, key):
    items, page = [], 1
    while page:
        data = get("%s/%s?per_page=50&page=%d" % (API, path, page), token)
        items += data.get(key) or []
        page = ((data.get("meta") or {}).get("pagination") or {}).get("next_page")
    return items


def _when(value):
    try:
        d = datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=UTC)


def _money(p):
    try:
        return float((p or {}).get("gross"))
    except (TypeError, ValueError):
        return 0.0


def _next_month(d):
    return datetime.datetime(d.year + (d.month == 12), d.month % 12 + 1, 1, tzinfo=UTC)


def billed(start, now, hourly, monthly):
    """(łącznie od start, w bieżącym miesiącu): w każdym miesiącu godziny × stawka, najwyżej stawka miesięczna."""
    total = month = 0.0
    cur = start
    while cur < now:
        end = min(_next_month(cur), now)
        hours = math.ceil((end - cur).total_seconds() / 3600)
        cost = min(hours * hourly, monthly) if hourly else monthly
        total += cost
        if (cur.year, cur.month) == (now.year, now.month):
            month += cost
        cur = end
    return round(total, 2), round(month, 2)


def _price(prices, location):
    for p in prices or []:
        if p.get("location") == location:
            return _money(p.get("price_hourly")), _money(p.get("price_monthly"))
    return None


def _loc(x):
    """Lokalizacja zasobu: pole „location” (obecne API) albo „datacenter.location” (starsze odpowiedzi)."""
    return ((x.get("location") or {}).get("name")) or ((((x.get("datacenter") or {}).get("location")) or {}).get("name", ""))


def _item(name, kind, detail, location, start, now, hourly, monthly):
    total, month = billed(start, now, hourly, monthly)
    return {"name": name, "kind": kind, "detail": detail, "location": location, "since": start.date().isoformat(),
            "monthly": round(monthly, 2), "month": month, "total": total}


def project_costs(get, token, now):
    """Pozycje kosztów jednego projektu Hetzner Cloud."""
    servers = _all(get, token, "servers", "servers")
    ips = _all(get, token, "primary_ips", "primary_ips")
    volumes = _all(get, token, "volumes", "volumes")
    pricing = get(API + "/pricing", token).get("pricing") or {}
    items = []
    names = {s.get("id"): s.get("name", "") for s in servers}
    for s in servers:
        start = _when(s.get("created"))
        loc = _loc(s)
        st = s.get("server_type") or {}
        p = _price(st.get("prices"), loc)
        if not start or not p:
            continue
        hourly, monthly = p
        items.append(_item(s.get("name", ""), "serwer", st.get("name", ""), loc, start, now, hourly, monthly))
        if s.get("backup_window"):
            items.append(_item(s.get("name", ""), "kopie", "+20%", loc, start, now, hourly * BACKUP_SHARE,
                               monthly * BACKUP_SHARE))
    ip_prices = {x.get("type"): x.get("prices") for x in pricing.get("primary_ips") or []}
    for ip in ips:
        start = _when(ip.get("created"))
        loc = _loc(ip)
        p = _price(ip_prices.get(ip.get("type")), loc)
        if not start or not p or not (p[0] or p[1]):
            continue
        owner = names.get(ip.get("assignee_id")) if ip.get("assignee_type", "server") == "server" else None
        name = owner or "%s (nieprzypisany)" % (ip.get("ip") or ip.get("name") or "adres")   # nieprzypisany adres też kosztuje
        items.append(_item(name, "adres", ip.get("type", ""), loc, start, now, *p))
    per_gb = _money((pricing.get("volume") or {}).get("price_per_gb_month"))
    for v in volumes:
        start = _when(v.get("created"))
        if not start or not per_gb:
            continue
        monthly = per_gb * float(v.get("size") or 0)
        items.append(_item(v.get("name", ""), "dysk", "%s GB" % v.get("size"), (v.get("location") or {}).get("name", ""),
                           start, now, 0, monthly))
    return items


def _sum(items, key):
    return round(sum(i[key] for i in items), 2)


def collect(tokens, get=http_get, now=None):
    """Blok "costs" dla /api/data."""
    now = now or datetime.datetime.now(UTC)
    projects = []
    for name, token in tokens:
        p = {"name": name, "items": [], "error": ""}
        try:
            p["items"] = project_costs(get, token, now)
        except urllib.error.HTTPError as e:
            p["error"] = "token odrzucony" if e.code in (401, 403) else "API Hetzner: błąd %d" % e.code
        except (urllib.error.URLError, OSError, ValueError, TypeError, AttributeError):
            p["error"] = "brak połączenia z API Hetzner"
        for k in ("monthly", "month", "total"):
            p[k] = _sum(p["items"], k)
        projects.append(p)
    out = {"configured": True, "at": now.isoformat(timespec="seconds"), "currency": "EUR", "projects": projects,
           "eurPln": None, "rateDate": ""}
    for k in ("monthly", "month", "total"):
        out[k] = round(sum(p[k] for p in projects), 2)
    try:
        rate = (get(NBP, None).get("rates") or [{}])[0]
        out["eurPln"], out["rateDate"] = float(rate["mid"]), str(rate.get("effectiveDate", ""))
    except (urllib.error.URLError, OSError, ValueError, TypeError, KeyError, AttributeError):
        pass
    return out


class Costs:
    """Odczyt w tle co TTL; /api/data dostaje ostatni wynik i nie czeka na API."""

    def __init__(self, get=http_get):
        self.get = get
        self.lock = threading.Lock()
        self.data = None
        self.next = 0.0
        self.busy = False

    def state(self):
        path = tokens_file()
        tokens = read_tokens(path)
        if tokens is None and not os.path.isdir(os.path.dirname(path)):
            return None                      # nie serwer (np. Mac): bez bloku kosztów
        if not tokens:
            return {"configured": False}
        with self.lock:
            if not self.busy and time.time() >= self.next:
                self.busy = True
                threading.Thread(target=self._refresh, args=(tokens,), daemon=True).start()
            return self.data or {"configured": True, "loading": True}

    def _refresh(self, tokens):
        try:
            data = collect(tokens, self.get)
            ok = not any(p["error"] for p in data["projects"])
        except Exception:  # noqa: BLE001  (wątek w tle nie może zatrzymać panelu)
            data, ok = None, False
        with self.lock:
            if data:
                self.data = data
            self.next = time.time() + (TTL if ok else RETRY)
            self.busy = False
