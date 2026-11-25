"""Google Ads bez tokenu dewelopera: skrypt Google Ads (Narzędzia → Działania zbiorcze → Skrypty) raz dziennie wysyła
do panelu POST /api/wyniki/google-ads wiersze z wczoraj. Skrypt tylko czyta konto Google Ads.

Klucz projektu: osobny na projekt, panel zapisuje tylko jego skrót SHA-256 (polaczenia.json); sam klucz widać raz,
w skrypcie pokazanym zaraz po wygenerowaniu. Nowy klucz unieważnia poprzedni. Zły klucz -> 403 bez szczegółów.
"""
import datetime
import hashlib
import hmac
import json
import re
import secrets

INGEST_PATH = "/api/wyniki/google-ads"
KEY_HEADER = "X-Klucz-Projektu"
MAX_BODY = 512 * 1024
MAX_ROWS = 2000
MAX_TERMS = 5000
KEEP_DAYS = 400
DAY = re.compile(r"^\d{4}-\d\d-\d\d$")


def new_key():
    return "gk_" + secrets.token_urlsafe(24)


def key_hash(key):
    return hashlib.sha256(str(key or "").encode("utf-8")).hexdigest()


def find_project(conns, key):
    """Projekt, którego skrót klucza pasuje (porównanie stałoczasowe), albo None."""
    if not isinstance(key, str) or not re.fullmatch(r"gk_[A-Za-z0-9_-]{20,64}", key):
        return None
    h = key_hash(key)
    hit = None
    for pid, c in conns.items():
        stored = str(((c or {}).get("google") or {}).get("keyHash") or "")
        if stored and hmac.compare_digest(stored, h):
            hit = pid
    return hit


def digits(customer):
    return re.sub(r"\D", "", str(customer or ""))


def customer_ok(value):
    """Identyfikator klienta Google Ads: 10 cyfr, zapis 123-456-7890."""
    d = digits(value)
    return "%s-%s-%s" % (d[:3], d[3:6], d[6:]) if len(d) == 10 else ""


def _n(v, integer=False):
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise ValueError("liczba")
    if x < 0 or x > 1e9:
        raise ValueError("liczba")
    return int(round(x)) if integer else round(x, 2)


def _t(v, limit=200):
    return re.sub(r"\s+", " ", str(v or "")).strip()[:limit]


def parse(body, customer):
    """Ciało od skryptu -> (dzień, wiersze, hasła). ValueError z krótkim opisem."""
    if not isinstance(body, dict):
        raise ValueError("zły format")
    day = str(body.get("dzien") or "")
    if not DAY.match(day):
        raise ValueError("dzien")
    datetime.date.fromisoformat(day)
    if customer and digits(body.get("konto")) != digits(customer):
        raise ValueError("konto Google Ads nie pasuje do projektu")
    rows, terms = body.get("wiersze") or [], body.get("hasla") or []
    if not isinstance(rows, list) or not isinstance(terms, list) or len(rows) > MAX_ROWS or len(terms) > MAX_TERMS:
        raise ValueError("za dużo wierszy")
    out = [{"data": day, "kampania": _t(r.get("kampania")), "grupa": _t(r.get("grupa")),
            "wyswietlenia": _n(r.get("wyswietlenia"), True), "klikniecia": _n(r.get("klikniecia"), True),
            "koszt": _n(r.get("koszt")), "konwersje": _n(r.get("konwersje")), "telefony": _n(r.get("telefony") or 0)}
           for r in rows if isinstance(r, dict)]
    ts = [{"data": day, "haslo": _t(r.get("haslo"), 120), "kampania": _t(r.get("kampania")), "grupa": _t(r.get("grupa")),
           "koszt": _n(r.get("koszt")), "klikniecia": _n(r.get("klikniecia"), True), "konwersje": _n(r.get("konwersje"))}
          for r in terms if isinstance(r, dict)]
    return day, out, ts


def store(whole, customer, day, rows, terms, now):
    """Zastępuje dzień w zapisie projektu (ponowne wysłanie tego samego dnia nie dubluje)."""
    g = whole.get("google") or {}
    if g.get("konto") and digits(g["konto"]) != digits(customer):
        g = {}
    keep = (now.date() - datetime.timedelta(days=KEEP_DAYS)).isoformat()
    g["konto"] = customer
    g["rows"] = sorted([r for r in g.get("rows") or [] if r["data"] != day and r["data"] >= keep] + rows,
                       key=lambda r: (r["data"], r["kampania"], r["grupa"]))
    g["terms"] = sorted([r for r in g.get("terms") or [] if r["data"] != day and r["data"] >= keep] + terms,
                        key=lambda r: (r["data"], r["kampania"], r["haslo"]))
    g["receivedAt"] = now.isoformat(timespec="seconds")
    whole["google"] = g
    return whole


SCRIPT = r"""/**
 * Panel IntegrateSystems: wyniki Google Ads projektu „%(name)s” (konto %(customer)s).
 * Skrypt tylko CZYTA konto Google Ads i raz dziennie wysyła do panelu wiersze z wczoraj:
 * kampania, grupa reklam, wyświetlenia, kliknięcia, koszt, konwersje (w tym telefony) i wyszukiwane hasła z kosztem.
 * Wklej go w Google Ads: Narzędzia → Działania zbiorcze → Skrypty → +, autoryzuj, harmonogram „Codziennie”.
 * Klucz poniżej to klucz projektu z panelu; nowy klucz w panelu unieważnia ten.
 */
var PANEL = '%(url)s';
var KLUCZ = '%(key)s';
var DNI = 1;   // pierwsze uruchomienie: wpisz np. 30, żeby wysłać ostatnie 30 dni; potem wróć do 1

function main() {
  var konto = AdsApp.currentAccount();
  var tz = konto.getTimeZone();
  for (var i = DNI; i >= 1; i--) {
    var dzien = Utilities.formatDate(new Date(Date.now() - i * 86400000), tz, 'yyyy-MM-dd');
    wyslij(konto.getCustomerId(), dzien);
  }
}

function wiersze(zapytanie) {
  var out = [], it = AdsApp.search(zapytanie);
  while (it.hasNext()) out.push(it.next());
  return out;
}

function wyslij(konto, dzien) {
  var gdzie = " WHERE segments.date = '" + dzien + "'";
  var lista = [], po = {};
  wiersze('SELECT campaign.name, ad_group.name, metrics.impressions, metrics.clicks, metrics.cost_micros, ' +
          'metrics.conversions FROM ad_group' + gdzie + ' AND metrics.impressions > 0').forEach(function (r) {
    var w = {kampania: r.campaign.name, grupa: r.adGroup.name, wyswietlenia: Number(r.metrics.impressions || 0),
             klikniecia: Number(r.metrics.clicks || 0), koszt: Number(r.metrics.costMicros || 0) / 1e6,
             konwersje: Number(r.metrics.conversions || 0), telefony: 0};
    po[w.kampania + '\u0001' + w.grupa] = w;
    lista.push(w);
  });
  wiersze('SELECT campaign.name, ad_group.name, segments.conversion_action_name, segments.conversion_action_category, ' +
          'metrics.conversions FROM ad_group' + gdzie + ' AND metrics.conversions > 0').forEach(function (r) {
    var w = po[r.campaign.name + '\u0001' + r.adGroup.name];
    var nazwa = String(r.segments.conversionActionName || ''), rodzaj = String(r.segments.conversionActionCategory || '');
    if (w && (/telefon|połącz|call/i.test(nazwa) || /PHONE_CALL/.test(rodzaj))) w.telefony += Number(r.metrics.conversions || 0);
  });
  var hasla = wiersze('SELECT search_term_view.search_term, campaign.name, ad_group.name, metrics.cost_micros, ' +
                      'metrics.clicks, metrics.conversions FROM search_term_view' + gdzie + ' AND metrics.cost_micros > 0')
    .map(function (r) {
      return {haslo: r.searchTermView.searchTerm, kampania: r.campaign.name, grupa: r.adGroup.name,
              koszt: Number(r.metrics.costMicros || 0) / 1e6, klikniecia: Number(r.metrics.clicks || 0),
              konwersje: Number(r.metrics.conversions || 0)};
    });
  var odp = UrlFetchApp.fetch(PANEL, {method: 'post', contentType: 'application/json', muteHttpExceptions: true,
    headers: {'X-Klucz-Projektu': KLUCZ},
    payload: JSON.stringify({konto: konto, dzien: dzien, wiersze: lista, hasla: hasla})});
  Logger.log(dzien + ': ' + lista.length + ' grup reklam, ' + hasla.length + ' haseł -> panel ' + odp.getResponseCode() +
             ' ' + odp.getContentText().slice(0, 200));
  if (odp.getResponseCode() !== 200) throw new Error('Panel nie przyjął danych (' + odp.getResponseCode() + ')');
}
"""


def script(name, customer, url, key):
    """Tekst skryptu z adresem panelu i kluczem projektu. ValueError przy złym adresie."""
    if not re.fullmatch(r"https?://[A-Za-z0-9.:/_-]+", url or ""):
        raise ValueError("adres panelu")
    safe = lambda s: re.sub(r"['\\\n\r]|\*/", " ", str(s or ""))
    return SCRIPT % {"name": safe(name), "customer": safe(customer), "url": url, "key": key}
