"""Dziennik klientów projektu (Marketing → Klienci): skąd przyszło zapytanie, wycena, umówienie, wykonanie.

Dane klientów są poza repozytorium: PANEL_KLIENCI_DIR (domyślnie ~/dane/klienci), plik <projekt>.json, 0600.
Bez imion, nazwisk i telefonów: wpis ma dzień, model auta, źródło, kod (reklamy albo posta), usługę i kwoty.
Do /api/data trafiają tylko sumy (podsumowanie i licznik kampanii); wpisy czyta GET /api/klienci.

Wpis: {"id", "data", "auto", "zrodlo", "kod", "usluga", "wycena", "umowiony", "wykonane", "dodano"}
- wycena, wykonane: kwota w zł (liczba) albo None; umowiony: True, False albo None (jeszcze nie wiadomo).
Import CSV: separator ; (także , i tabulator), kolumny rozpoznane po nazwach; kolumny z imieniem albo telefonem pomija.
"""
import csv
import datetime
import io
import json
import os
import re
import threading
import unicodedata

SOURCES = ("Meta – reklama", "Instagram", "Facebook", "TikTok", "Google Ads", "Wizytówka Google", "Polecenie", "Inne")
AD_SOURCES = ("Meta – reklama", "Google Ads")
# miernik kampanii liczony z dziennika: zapytanie z kodem albo ze źródłem z reklamy
METRIC = "zapytania z reklam"
MAX_ENTRIES = 20000
MAX_CSV = 2 * 1024 * 1024
PHONE = re.compile(r"(?:\d[\s-]?){7,}")
DAY = re.compile(r"^\d{4}-\d\d-\d\d$")


def norm(text):
    """Małe litery bez polskich znaków i spacji na brzegach (porównywanie nazw kolumn i źródeł)."""
    s = unicodedata.normalize("NFKD", str(text or "").strip().lower().replace("ł", "l"))
    return "".join(c for c in s if not unicodedata.combining(c))


def source_of(value):
    """Nazwa źródła z listy SOURCES albo "" (puste). Nieznane źródło -> „Inne”."""
    n = norm(value)
    if not n:
        return ""
    for s in SOURCES:
        if n == norm(s):
            return s
    if "google" in n and ("ads" in n or "reklam" in n or "adwords" in n):
        return "Google Ads"
    if "wizyt" in n or "maps" in n or "mapy" in n or "profil firmy" in n or n == "google":
        return "Wizytówka Google"
    if "meta" in n or (("facebook" in n or n.startswith("fb") or "instagram" in n) and ("reklam" in n or "ads" in n)):
        return "Meta – reklama"
    if "insta" in n or n == "ig":
        return "Instagram"
    if "facebook" in n or n == "fb":
        return "Facebook"
    if "tiktok" in n:
        return "TikTok"
    if "polec" in n or "znajom" in n:
        return "Polecenie"
    return "Inne"


def amount(value):
    """„1 590 zł”, „1590,50”, 1590 -> 1590.0 / 1590.5; puste -> None; zła wartość -> ValueError."""
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise ValueError("kwota")
    if isinstance(value, (int, float)):
        v = float(value)
    else:
        s = re.sub(r"(?i)\s*(zł|zl|pln)\s*$", "", str(value).strip()).replace(" ", "").replace(" ", "")
        if not s:
            return None
        if re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d{1,2})?", s):        # 1.590,50
            s = s.replace(".", "")
        s = s.replace(",", ".")
        if not re.fullmatch(r"\d+(\.\d{1,2})?", s):
            raise ValueError("kwota")
        v = float(s)
    if v < 0 or v > 10_000_000:
        raise ValueError("kwota")
    return round(v, 2)


def yes_no(value):
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    n = norm(value)
    if n in ("tak", "t", "1", "yes", "y", "true", "x", "umowiony", "umowiona"):
        return True
    if n in ("nie", "n", "0", "no", "false"):
        return False
    raise ValueError("tak albo nie")


def day_of(value, today):
    """RRRR-MM-DD, DD.MM.RRRR, DD.MM (rok bieżący) -> RRRR-MM-DD; puste -> dziś."""
    s = str(value or "").strip()
    if not s:
        return today
    m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", s) or None
    if m:
        y, mo, d = m.groups()
    else:
        m = re.fullmatch(r"(\d{1,2})[./](\d{1,2})(?:[./](\d{2,4}))?", s)
        if not m:
            raise ValueError("data")
        d, mo, y = m.groups()
        y = y or today[:4]
        if len(y) == 2:
            y = "20" + y
    return datetime.date(int(y), int(mo), int(d)).isoformat()


def text_field(value, limit, label):
    s = re.sub(r"\s+", " ", str(value or "")).strip()
    if PHONE.search(s):
        raise ValueError("%s: bez numerów telefonów" % label)
    return s[:limit]


def in_range(day, start, end):
    return (not start or day >= start) and (not end or day <= end)


def summarize(entries, today, start=""):
    """Podsumowanie: bieżący tydzień (od poniedziałku) i od startu kampanii (start: RRRR-MM-DD albo "" = całość),
    oraz podział na źródła (od startu). Liczby: zapytania, umówieni, wykonane, przychód (zł)."""
    t = datetime.date.fromisoformat(today)
    week = (t - datetime.timedelta(days=t.weekday())).isoformat()

    def block(L):
        done = [e for e in L if e.get("wykonane")]
        return {"zapytania": len(L), "umowieni": sum(1 for e in L if e.get("umowiony")),
                "wykonane": len(done), "przychod": round(sum(e["wykonane"] for e in done), 2),
                "wycena": round(sum(e.get("wycena") or 0 for e in L), 2)}

    since = [e for e in entries if in_range(e.get("data", ""), start, today)]
    sources = {}
    for e in since:
        sources.setdefault(e.get("zrodlo") or "Inne", []).append(e)
    return {"tydzien": block([e for e in entries if in_range(e.get("data", ""), week, today)]),
            "start": start, "odStartu": block(since),
            "zrodla": [dict(block(L), zrodlo=s) for s, L in sorted(sources.items(), key=lambda kv: -len(kv[1]))]}


def ad_inquiries(entries, start="", end=""):
    """Licznik kampanii z miernikiem „zapytania z reklam”: zapytania z kodem albo ze źródłem z reklamy w okresie."""
    return sum(1 for e in entries if in_range(e.get("data", ""), start, end)
               and (e.get("kod") or e.get("zrodlo") in AD_SOURCES))


COLUMNS = {   # znormalizowana nazwa kolumny CSV -> pole wpisu
    "data": "data", "dzien": "data", "date": "data", "kiedy": "data",
    "auto": "auto", "model": "auto", "samochod": "auto", "auto (model)": "auto", "marka i model": "auto", "pojazd": "auto",
    "zrodlo": "zrodlo", "skad": "zrodlo", "kanal": "zrodlo", "source": "zrodlo",
    "kod": "kod", "post": "kod", "reklama": "kod", "kod reklamy": "kod", "kod / post": "kod",
    "usluga": "usluga", "uslugi": "usluga", "zakres": "usluga",
    "wycena": "wycena", "wycena (zl)": "wycena", "wycena zl": "wycena", "cena": "wycena", "oferta": "wycena",
    "umowiony": "umowiony", "umowiona": "umowiony", "umowienie": "umowiony", "termin": "umowiony",
    "wykonane": "wykonane", "wykonane (zl)": "wykonane", "wykonane zl": "wykonane", "zrealizowane": "wykonane",
    "kwota": "wykonane", "przychod": "wykonane", "zaplacono": "wykonane",
}


class Klienci:
    def __init__(self, data_dir=None, now=None):
        self.dir = os.path.expanduser(data_dir or os.environ.get("PANEL_KLIENCI_DIR", "").strip() or "~/dane/klienci")
        self.now = now or datetime.datetime.now
        self.lock = threading.Lock()

    def today(self):
        return self.now().date().isoformat()

    # ---------- pliki ----------
    def _path(self, pid):
        name = re.sub(r"[^a-z0-9_.-]", "_", str(pid).lower()).strip(".") or "_"
        return os.path.join(self.dir, name + ".json")

    def load(self, pid):
        try:
            with open(self._path(pid), encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError):
            d = {}
        d.setdefault("entries", [])
        d.setdefault("seq", len(d["entries"]))
        return d

    def _save(self, pid, data):
        os.makedirs(self.dir, mode=0o700, exist_ok=True)
        path = self._path(pid)
        tmp = path + ".tmp"
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=0)
        os.replace(tmp, path)

    def entries(self, pid):
        return self.load(pid)["entries"]

    # ---------- wpis ----------
    def _clean(self, body, old=None):
        """Wpis z danych formularza (pola, których nie ma w body, zostają z old). ValueError z opisem."""
        e = dict(old or {})
        today = self.today()
        try:
            if "data" in body or not old:
                e["data"] = day_of(body.get("data"), today)
        except (ValueError, TypeError):
            raise ValueError("Data w formacie RRRR-MM-DD.")
        for key, limit, label in (("auto", 60, "Auto"), ("kod", 40, "Kod"), ("usluga", 80, "Usługa")):
            if key in body or not old:
                e[key] = text_field(body.get(key), limit, label)
        if "zrodlo" in body or not old:
            src = str(body.get("zrodlo") or "").strip()
            if src not in SOURCES:
                raise ValueError("Wybierz źródło z listy.")
            e["zrodlo"] = src
        for key, label in (("wycena", "Wycena"), ("wykonane", "Wykonane")):
            if key in body or not old:
                try:
                    e[key] = amount(body.get(key))
                except ValueError:
                    raise ValueError("%s: kwota w zł, np. 1590." % label)
        if "umowiony" in body or not old:
            try:
                e["umowiony"] = yes_no(body.get("umowiony"))
            except ValueError:
                raise ValueError("Umówiony: tak albo nie.")
        if e.get("wykonane") and e.get("umowiony") is None:
            e["umowiony"] = True
        return e

    def add(self, pid, body):
        try:
            e = self._clean(body)
        except ValueError as err:
            return 400, str(err)
        with self.lock:
            d = self.load(pid)
            if len(d["entries"]) >= MAX_ENTRIES:
                return 409, "Dziennik jest pełny."
            d["seq"] += 1
            e["id"] = "k%d" % d["seq"]
            e["dodano"] = self.now().isoformat(timespec="seconds")
            d["entries"].append(e)
            self._save(pid, d)
        return 200, "", {"entry": e}

    def update(self, pid, body):
        eid = str(body.get("id") or "")
        with self.lock:
            d = self.load(pid)
            i = next((n for n, x in enumerate(d["entries"]) if x.get("id") == eid), None)
            if i is None:
                return 404, "Nie ma tego wpisu."
            if body.get("usun") is True:
                del d["entries"][i]
            else:
                try:
                    d["entries"][i] = self._clean({k: v for k, v in body.items() if k not in ("id", "project")},
                                                  d["entries"][i])
                except ValueError as err:
                    return 400, str(err)
            self._save(pid, d)
        return 200, ""

    # ---------- import CSV ----------
    def import_csv(self, pid, text):
        """Dopisuje wiersze z CSV (pomija powtórzone i puste). (kod, błąd, {"dodane", "pominiete", "bledy"})."""
        if not isinstance(text, str) or not text.strip():
            return 400, "Wklej albo wybierz plik CSV."
        if len(text.encode("utf-8")) > MAX_CSV:
            return 400, "Plik CSV do 2 MB."
        text = text.lstrip("﻿")
        first = text.split("\n", 1)[0]
        sep = max((";", ",", "\t"), key=first.count)
        rows = list(csv.reader(io.StringIO(text), delimiter=sep))
        if len(rows) < 2:
            return 400, "W pliku nie ma wierszy pod nagłówkiem."
        cols = [COLUMNS.get(norm(h)) for h in rows[0]]
        if "data" not in cols or "zrodlo" not in cols:
            return 400, "Nagłówek CSV musi mieć kolumny „data” i „źródło”."
        today = self.today()
        added, skipped, errors = [], 0, []
        for no, row in enumerate(rows[1:], start=2):
            if not any(c.strip() for c in row):
                continue
            raw = {}
            for col, val in zip(cols, row):
                if col and col not in raw:
                    raw[col] = val
            try:
                raw["data"] = day_of(raw.get("data"), today)
                raw["zrodlo"] = source_of(raw.get("zrodlo")) or "Inne"
                yn = raw.get("umowiony")
                if yn is not None and str(yn).strip() and not re.fullmatch(r"(?i)\s*(tak|nie|t|n|0|1|x)\s*", str(yn)):
                    raw["umowiony"] = "tak"             # np. data wizyty w kolumnie „termin”
                e = self._clean(raw)
            except (ValueError, TypeError) as err:
                if len(errors) < 5:
                    errors.append("wiersz %d: %s" % (no, str(err).rstrip(".")))
                skipped += 1
                continue
            added.append(e)
        key = lambda e: (e["data"], e["auto"].lower(), e["zrodlo"], e["kod"], e["usluga"].lower(), e["wycena"])
        with self.lock:
            d = self.load(pid)
            seen = {key(e) for e in d["entries"]}
            n = 0
            for e in added:
                if key(e) in seen or len(d["entries"]) >= MAX_ENTRIES:
                    skipped += 1
                    continue
                seen.add(key(e))
                d["seq"] += 1
                e["id"] = "k%d" % d["seq"]
                e["dodano"] = self.now().isoformat(timespec="seconds")
                d["entries"].append(e)
                n += 1
            if n:
                self._save(pid, d)
        return 200, "", {"dodane": n, "pominiete": skipped, "bledy": errors}

    # ---------- odczyt dla panelu ----------
    def view(self, pid, start=""):
        """GET /api/klienci: wpisy (najnowsze pierwsze), podsumowanie, lista źródeł."""
        L = sorted(self.entries(pid), key=lambda e: (e.get("data", ""), e.get("dodano", "")), reverse=True)
        return {"entries": L, "summary": summarize(L, self.today(), start), "sources": list(SOURCES)}


def marketing_numbers(pid, start="", end="", klienci_dir=None, ads_dir=None):
    """Liczby kampanii dla raportu PM (pm.py): zapytania, zapytania z reklam, wykonane, przychód i wydatek na reklamy
    (Meta i Google Ads z ~/dane/reklamy) w okresie start..end. None, gdy projekt nie ma dziennika ani reklam."""
    k = Klienci(klienci_dir)
    ads_path = os.path.join(os.path.expanduser(ads_dir or os.environ.get("PANEL_REKLAMY_DIR", "").strip() or "~/dane/reklamy"),
                            re.sub(r"[^a-z0-9_.-]", "_", ("%s.json" % pid).lower()))
    if not os.path.isfile(k._path(pid)) and not os.path.isfile(ads_path):
        return None
    try:
        with open(ads_path, encoding="utf-8") as f:
            ads = json.load(f)
    except (OSError, ValueError):
        ads = {}
    L = [e for e in k.entries(pid) if in_range(e.get("data", ""), start, end)]
    spend = sum(r.get("wydano") or 0 for r in (ads.get("meta") or {}).get("rows") or [] if in_range(r.get("data", ""), start, end)) + \
        sum(r.get("koszt") or 0 for r in (ads.get("google") or {}).get("rows") or [] if in_range(r.get("data", ""), start, end))
    revenue = round(sum(e.get("wykonane") or 0 for e in L), 2)
    return {"inquiries": len(L), "adInquiries": ad_inquiries(L), "done": sum(1 for e in L if e.get("wykonane")),
            "revenue": revenue, "adSpend": round(spend, 2), "revenuePerZl": round(revenue / spend, 2) if spend else None}

