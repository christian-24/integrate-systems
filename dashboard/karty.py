"""Karty asystenta na stronie Asystent: katalog typów, sprawdzenie bloku ```karty``` z odpowiedzi modelu
i biblioteka zapisanych kart (plik JSON obok rozmów).

Model nie pisze HTML ani skryptów. Opisuje kartę danymi: typ z katalogu, tytuł i `zapytanie` w małym języku
(liczone w przeglądarce z /api/data, więc liczby są zawsze aktualne) albo `dane` podane wprost (np. newsy).
Wszystko spoza katalogu jest odrzucane: nieznany typ, nieznane pole, tekst ze znacznikami HTML, link inny niż http(s).
Sama biblioteka standardowa."""
import copy
import json
import os
import re
import threading
import uuid

TYPES = ("liczba", "lista", "tabela", "wykres", "postep", "tydzien", "notatka", "news", "panel")
COMMON = {"id", "typ", "tytul", "opis", "zrodlo", "rozmiar", "zapisz"}
TYPE_KEYS = {"liczba": {"zapytanie", "dane", "porownaj"}, "lista": {"zapytanie", "dane"},
             "tabela": {"zapytanie", "dane", "kolumny"}, "wykres": {"zapytanie", "dane", "rodzaj"},
             "postep": {"zapytanie"}, "tydzien": {"zapytanie"}, "notatka": {"dane"}, "news": {"dane"},
             "panel": {"widok"}}
# karta „panel”: fragment panelu z przyciskami (dawne widoki Dla Ciebie, Terminy, Blokady, Wskaźniki, Tablica, raport PM)
PANEL_VIEWS = ("sprawy-dzis", "sprawy", "terminy", "blokady", "wskazniki", "zadania", "raport")
NEED_DATA = {"liczba", "lista", "tabela", "wykres", "tydzien", "notatka", "news"}   # zapytanie albo dane
SOURCES = ("zadania", "publikacje", "etapy", "projekty", "kampanie", "zasoby")
QUERY_KEYS = {"zrodlo", "filtr", "grupuj", "miara", "sortuj", "limit"}
FILTER_KEYS = {"projekt", "stan", "kto", "czeka", "od", "do", "szukaj", "kanal", "etap"}
STATES = ("otwarte", "zrobione", "do zrobienia", "w toku", "zablokowane", "do odbioru", "po terminie",
          "aktywne", "wstrzymane", "backlog", "zakończone")
WHO = ("ty", "claude", "codex", "agent", "agenci", "dla-ciebie")
WAITS = ("zgoda", "odbiór", "dowolne")
GROUPS = ("projekt", "stan", "kto", "dzien", "tydzien", "etap", "kanal")
MEASURES = ("liczba", "minuty", "wartosc")
SORTS = ("data", "-data", "tytul", "projekt", "wartosc", "-wartosc")
COLUMNS = ("tytul", "projekt", "data", "stan", "kto", "minuty", "kanal", "etap", "postep", "wartosc")
CHARTS = ("slupki", "linia")
SIZES = ("waska", "szeroka")
DATE_RE = re.compile(r"^(dziś|dzis|jutro|wczoraj|[+-]\d{1,3}|\d{4}-\d{2}-\d{2})$")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
HTML_RE = re.compile(r"<\s*[a-zA-Z/!?]|&#?\w+;|javascript:", re.I)
LINK_RE = re.compile(r"^https?://[^\s<>\"'`]{1,500}$")
MAX_CARDS = 12           # kart w jednej odpowiedzi
MAX_ITEMS = 20           # pozycji listy i newsów
MAX_ROWS = 30            # wierszy tabeli z danymi wprost
MAX_POINTS = 60          # punktów wykresu
MAX_LIMIT = 50           # limit w zapytaniu
BLOCK_RE = re.compile(r"```karty[ \t]*\r?\n(.*?)(?:\r?\n[ \t]*```|\Z)", re.S)


class Bad(ValueError):
    pass


def _text(v, field, size):
    if not isinstance(v, str):
        raise Bad("%s: oczekiwany tekst" % field)
    v = v.strip()
    if len(v) > size:
        raise Bad("%s: najwyżej %d znaków" % (field, size))
    if HTML_RE.search(v):
        raise Bad("%s: bez HTML" % field)
    return v


def _num(v, field):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v or abs(v) > 1e12:
        raise Bad("%s: oczekiwana liczba" % field)
    return v


def _link(v, field):
    v = _text(v, field, 500)
    if not LINK_RE.match(v):
        raise Bad("%s: tylko adres http(s)" % field)
    return v


def _keys(obj, allowed, field):
    if not isinstance(obj, dict):
        raise Bad("%s: oczekiwany obiekt" % field)
    extra = sorted(set(obj) - set(allowed))
    if extra:
        raise Bad("%s: nieznane pole %s" % (field, ", ".join(extra)))


def _one_or_list(v, field, check):
    vals = v if isinstance(v, list) else [v]
    if not vals or len(vals) > 10:
        raise Bad("%s: od 1 do 10 wartości" % field)
    out = [check(x) for x in vals]
    return out if isinstance(v, list) else out[0]


def _choice(options, field):
    def check(x):
        if x not in options:
            raise Bad("%s: dozwolone %s" % (field, ", ".join(options)))
        return x
    return check


def query(q, field="zapytanie"):
    """Sprawdza zapytanie. Zwraca kopię bez zmian znaczenia albo zgłasza Bad."""
    _keys(q, QUERY_KEYS, field)
    if q.get("zrodlo") not in SOURCES:
        raise Bad("%s.zrodlo: dozwolone %s" % (field, ", ".join(SOURCES)))
    out = {"zrodlo": q["zrodlo"]}
    if "filtr" in q:
        f = q["filtr"]
        _keys(f, FILTER_KEYS, field + ".filtr")
        of = {}
        for k, v in f.items():
            name = "%s.filtr.%s" % (field, k)
            if k == "stan":
                of[k] = _one_or_list(v, name, _choice(STATES, name))
            elif k == "kto":
                of[k] = _one_or_list(v, name, _choice(WHO, name))
            elif k == "czeka":
                of[k] = _choice(WAITS, name)(v)
            elif k in ("od", "do"):
                if not isinstance(v, str) or not DATE_RE.match(v.strip()):
                    raise Bad("%s: dziś, jutro, wczoraj, +N, -N albo RRRR-MM-DD" % name)
                of[k] = v.strip()
            else:
                of[k] = _one_or_list(v, name, lambda x, n=name: _text(x, n, 80))
        out["filtr"] = of
    if "grupuj" in q:
        out["grupuj"] = _choice(GROUPS, field + ".grupuj")(q["grupuj"])
    if "miara" in q:
        out["miara"] = _choice(MEASURES, field + ".miara")(q["miara"])
    if "sortuj" in q:
        out["sortuj"] = _choice(SORTS, field + ".sortuj")(q["sortuj"])
    if "limit" in q:
        n = q["limit"]
        if isinstance(n, bool) or not isinstance(n, int) or not 1 <= n <= MAX_LIMIT:
            raise Bad("%s.limit: liczba od 1 do %d" % (field, MAX_LIMIT))
        out["limit"] = n
    return out


def _data(typ, d):
    f = "dane"
    if typ == "liczba":
        _keys(d, {"wartosc", "jednostka"}, f)
        out = {"wartosc": _num(d.get("wartosc"), f + ".wartosc")}
        if "jednostka" in d:
            out["jednostka"] = _text(d["jednostka"], f + ".jednostka", 20)
        return out
    if typ == "notatka":
        _keys(d, {"tekst"}, f)
        return {"tekst": _text(d.get("tekst"), f + ".tekst", 1500)}
    if typ == "tabela":
        _keys(d, {"kolumny", "wiersze"}, f)
        cols, rows = d.get("kolumny"), d.get("wiersze")
        if not isinstance(cols, list) or not 1 <= len(cols) <= 6:
            raise Bad("dane.kolumny: od 1 do 6 nazw")
        if not isinstance(rows, list) or len(rows) > MAX_ROWS:
            raise Bad("dane.wiersze: najwyżej %d" % MAX_ROWS)
        cols = [_text(c, "dane.kolumny", 40) for c in cols]
        out = []
        for r in rows:
            if not isinstance(r, list) or len(r) != len(cols):
                raise Bad("dane.wiersze: każdy wiersz ma %d komórek" % len(cols))
            out.append([c if isinstance(c, (int, float)) and not isinstance(c, bool) else _text(c, "dane.wiersze", 120)
                        for c in r])
        return {"kolumny": cols, "wiersze": out}
    if typ == "wykres":
        _keys(d, {"punkty"}, f)
        pts = d.get("punkty")
        if not isinstance(pts, list) or not 1 <= len(pts) <= MAX_POINTS:
            raise Bad("dane.punkty: od 1 do %d" % MAX_POINTS)
        out = []
        for p in pts:
            _keys(p, {"etykieta", "wartosc"}, "dane.punkty")
            out.append({"etykieta": _text(p.get("etykieta"), "dane.punkty.etykieta", 40),
                        "wartosc": _num(p.get("wartosc"), "dane.punkty.wartosc")})
        return {"punkty": out}
    if typ in ("lista", "news"):
        _keys(d, {"pozycje"}, f)
        items = d.get("pozycje")
        if not isinstance(items, list) or not 1 <= len(items) <= MAX_ITEMS:
            raise Bad("dane.pozycje: od 1 do %d" % MAX_ITEMS)
        out = []
        for it in items:
            if typ == "lista":
                _keys(it, {"tekst", "opis", "link"}, "dane.pozycje")
                o = {"tekst": _text(it.get("tekst"), "dane.pozycje.tekst", 200)}
                if "opis" in it:
                    o["opis"] = _text(it["opis"], "dane.pozycje.opis", 200)
            else:
                _keys(it, {"tytul", "zrodlo", "data", "link", "opis"}, "dane.pozycje")
                o = {"tytul": _text(it.get("tytul"), "dane.pozycje.tytul", 200),
                     "zrodlo": _text(it.get("zrodlo"), "dane.pozycje.zrodlo", 80)}
                if "data" in it:
                    o["data"] = _text(it["data"], "dane.pozycje.data", 30)
                if "opis" in it:
                    o["opis"] = _text(it["opis"], "dane.pozycje.opis", 300)
                if "link" not in it:
                    raise Bad("dane.pozycje.link: wymagany przy newsie")
            if "link" in it:
                o["link"] = _link(it["link"], "dane.pozycje.link")
            out.append(o)
        return {"pozycje": out}
    raise Bad("dane: niedozwolone przy typie %s" % typ)


def card(c):
    """Sprawdza jedną kartę. Zwraca czystą kopię albo zgłasza Bad. {"id": …} bez innych pól to odwołanie do karty
    z biblioteki albo wbudowanej."""
    if not isinstance(c, dict):
        raise Bad("karta: oczekiwany obiekt")
    cid = c.get("id")
    if not isinstance(cid, str) or not ID_RE.match(cid):
        raise Bad("id: małe litery, cyfry i myślniki, do 40 znaków")
    if set(c) == {"id"}:
        return {"id": cid}
    typ = c.get("typ")
    if typ not in TYPES:
        raise Bad("%s: nieznany typ %s (dozwolone: %s)" % (cid, typ, ", ".join(TYPES)))
    try:
        _keys(c, COMMON | TYPE_KEYS[typ], "karta")
        out = {"id": cid, "typ": typ, "tytul": _text(c.get("tytul"), "tytul", 80)}
        if not out["tytul"]:
            raise Bad("tytul: wymagany")
        for k, size in (("opis", 200), ("zrodlo", 120)):
            if k in c:
                out[k] = _text(c[k], k, size)
        if "rozmiar" in c:
            out["rozmiar"] = _choice(SIZES, "rozmiar")(c["rozmiar"])
        if "zapisz" in c:
            if not isinstance(c["zapisz"], bool):
                raise Bad("zapisz: true albo false")
            out["zapisz"] = c["zapisz"]
        if "zapytanie" in c and "dane" in c:
            raise Bad("zapytanie albo dane, nie oba")
        if "zapytanie" in c:
            out["zapytanie"] = query(c["zapytanie"])
        if "dane" in c:
            out["dane"] = _data(typ, c["dane"])
        if typ in NEED_DATA and "zapytanie" not in out and "dane" not in out:
            raise Bad("wymagane zapytanie albo dane")
        if "porownaj" in c:
            _keys(c["porownaj"], {"etykieta", "zapytanie"}, "porownaj")
            if "zapytanie" not in c["porownaj"]:
                raise Bad("porownaj.zapytanie: wymagane")
            out["porownaj"] = {"etykieta": _text(c["porownaj"].get("etykieta", "porównanie"), "porownaj.etykieta", 40),
                               "zapytanie": query(c["porownaj"]["zapytanie"], "porownaj.zapytanie")}
        if typ == "panel":
            out["widok"] = _choice(PANEL_VIEWS, "widok")(c.get("widok"))
        if "rodzaj" in c:
            out["rodzaj"] = _choice(CHARTS, "rodzaj")(c["rodzaj"])
        if "kolumny" in c:
            cols = c["kolumny"]
            if not isinstance(cols, list) or not 1 <= len(cols) <= 6:
                raise Bad("kolumny: od 1 do 6")
            out["kolumny"] = [_choice(COLUMNS, "kolumny")(x) for x in cols]
        if typ == "wykres" and "zapytanie" in out and "grupuj" not in out["zapytanie"]:
            raise Bad("wykres z zapytania wymaga grupuj")
    except Bad as e:
        raise Bad("%s: %s" % (cid, e))
    return out


def extract(text):
    """Bloki ```karty``` z odpowiedzi: (tekst bez bloków, {"pokaz": [karty], "usun": [id], "bledy": [opis]}).
    Blok to obiekt {"pokaz": [...], "usun": [...]} albo sama lista kart (= pokaz)."""
    ops = {"pokaz": [], "usun": [], "bledy": []}
    text = str(text or "")
    for raw in BLOCK_RE.findall(text):
        try:
            block = json.loads(raw)
        except ValueError:
            ops["bledy"].append("blok kart: nieprawidłowy JSON")
            continue
        if isinstance(block, list):
            block = {"pokaz": block}
        if not isinstance(block, dict) or set(block) - {"pokaz", "usun"}:
            ops["bledy"].append("blok kart: dozwolone tylko pokaz i usun")
            continue
        shown = block.get("pokaz") or []
        if not isinstance(shown, list):
            ops["bledy"].append("pokaz: oczekiwana lista kart")
            shown = []
        for c in shown:
            if len(ops["pokaz"]) >= MAX_CARDS:
                ops["bledy"].append("najwyżej %d kart w odpowiedzi" % MAX_CARDS)
                break
            try:
                ops["pokaz"].append(card(c))
            except Bad as e:
                ops["bledy"].append(str(e))
        gone = block.get("usun") or []
        for x in gone if isinstance(gone, list) else [gone]:
            if isinstance(x, str) and ID_RE.match(x) and x not in ops["usun"]:
                ops["usun"].append(x)
    clean = BLOCK_RE.sub("", text)
    clean = re.sub(r"\n{3,}", "\n\n", clean).strip()
    return clean, ops


# ---------- karty wbudowane ----------
# START: karty na pustym płótnie; pozostałe wbudowane model podaje samym id, a właściciel dodaje przyciskiem „Dodaj kartę”.
# Ta sama lista jest w panel.html (AP_START, test_plotno pilnuje zgodności).
STARTERS = [
    {"id": "sprawy-dzis", "typ": "panel", "widok": "sprawy-dzis", "tytul": "Sprawy dla Ciebie", "rozmiar": "szeroka",
     "opis": "Sprawy na dziś (w tym po terminie) z przyciskami Jutro, Zrobione, Odpowiedz, Zatwierdź, Obejrzyj; "
             "pełna lista w szufladzie"},
    {"id": "publikacje-tygodnia", "typ": "tydzien", "tytul": "Publikacje w tym tygodniu", "rozmiar": "szeroka",
     "opis": "Publikacje od dziś przez 7 dni, dziś wyróżniony",
     "zapytanie": {"zrodlo": "publikacje", "filtr": {"od": "dziś", "do": "+6"}}},
    {"id": "postep-projektow", "typ": "postep", "tytul": "Postęp projektów",
     "opis": "Zrobione zadania w aktywnych projektach"},
    {"id": "raport-pm", "typ": "panel", "widok": "raport", "tytul": "Notatka PM", "rozmiar": "szeroka",
     "opis": "Notatka kierownika projektów z raporty/ i przycisk raportu PM"},
    {"id": "sprawy", "typ": "panel", "widok": "sprawy", "tytul": "Sprawy dla Ciebie: pełna lista", "rozmiar": "szeroka",
     "opis": "Pytania, zgody, odbiory i Twoje zadania: dziś, 7 dni, później; filtr rodzaju i projektu"},
    {"id": "terminy", "typ": "panel", "widok": "terminy", "tytul": "Terminy", "rozmiar": "szeroka",
     "opis": "Etapy, zadania i publikacje od najpilniejszych, z filtrem projektu i rodzaju"},
    {"id": "blokady", "typ": "panel", "widok": "blokady", "tytul": "Blokady", "rozmiar": "szeroka",
     "opis": "Co wstrzymuje ile zadań, zablokowane zadania i zależności do poprawy"},
    {"id": "wskazniki", "typ": "panel", "widok": "wskazniki", "tytul": "Wskaźniki", "rozmiar": "szeroka",
     "opis": "Postęp, tempo i przepływ pracy, porównanie projektów"},
    {"id": "zadania", "typ": "panel", "widok": "zadania", "tytul": "Zadania", "rozmiar": "szeroka",
     "opis": "Zadania ze wszystkich projektów z filtrem projektu i stanu"},
]
START = ("sprawy-dzis", "publikacje-tygodnia", "postep-projektow", "raport-pm")
# dawne karty wbudowane: płótno pokazuje je jako jedną kartę (panel.html, AP_ALIAS); id są zajęte w bibliotece
ALIASES = {"sprawy": "sprawy-dzis", "dzis-dla-ciebie": "sprawy-dzis", "po-terminie": "sprawy-dzis"}


# ---------- biblioteka: zapisane karty i układ płótna ----------
class Library:
    """Plik JSON: {"karty": {id: karta}, "przypiete": [id], "ukryte": {id: czas}}. Zapis atomowy pod blokadą."""
    MAX_CARDS = 100
    MAX_BYTES = 256 * 1024

    def __init__(self, path):
        self.path = path
        self.lock = threading.Lock()

    def _read(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            data = {}
        data = data if isinstance(data, dict) else {}
        cards = {}
        for k, v in (data.get("karty") or {}).items() if isinstance(data.get("karty"), dict) else []:
            try:
                c = card(v)
            except Bad:
                continue
            if c.get("typ") and c["id"] == k:
                cards[k] = c
        pins = [x for x in data.get("przypiete") or [] if isinstance(x, str) and ID_RE.match(x)]
        hidden = {k: str(v)[:40] for k, v in (data.get("ukryte") or {}).items()
                  if isinstance(k, str) and ID_RE.match(k)} if isinstance(data.get("ukryte"), dict) else {}
        return {"karty": cards, "przypiete": list(dict.fromkeys(pins))[:60], "ukryte": hidden}

    def _write(self, data):
        text = json.dumps(data, ensure_ascii=False, indent=1)
        if len(text.encode("utf-8")) > self.MAX_BYTES:
            return False
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = "%s.tmp-%s" % (self.path, uuid.uuid4().hex[:6])
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, self.path)
        return True

    def read(self):
        with self.lock:
            return self._read()

    def summary(self):
        """Wiersze do promptu: karty wbudowane i zapisane (id, typ, tytuł, opis)."""
        lib = self.read()["karty"]
        rows = ["- %s (%s, wbudowana): %s%s" % (c["id"], c["typ"], c["tytul"], " · " + c["opis"] if c.get("opis") else "")
                for c in STARTERS]
        rows += ["- %s (%s): %s%s" % (c["id"], c["typ"], c["tytul"], " · " + c["opis"] if c.get("opis") else "")
                 for c in sorted(lib.values(), key=lambda x: x["id"])]
        return rows

    def save(self, cards):
        """Zapisuje karty (z zapytaniem albo postęp; karty z danymi wprost i odwołania pomija). (kod, błąd, zapisane id)."""
        keep = []
        for c in cards:
            c = card(c)
            if not c.get("typ") or "dane" in c:
                continue
            c.pop("zapisz", None)
            keep.append(c)
        if not keep:
            return 200, "", []
        with self.lock:
            data = self._read()
            builtin = {s["id"] for s in STARTERS} | set(ALIASES)
            for c in keep:
                if c["id"] in builtin:
                    raise Bad("%s: id karty wbudowanej" % c["id"])
                if c["id"] not in data["karty"] and len(data["karty"]) >= self.MAX_CARDS:
                    return 409, "Biblioteka ma już %d kart. Usuń nieużywane." % self.MAX_CARDS, []
                data["karty"][c["id"]] = copy.deepcopy(c)
            if not self._write(data):
                return 413, "Biblioteka kart przekracza %d kB." % (self.MAX_BYTES // 1024), []
        return 200, "", [c["id"] for c in keep]

    def remove(self, cid):
        with self.lock:
            data = self._read()
            if cid not in data["karty"]:
                return 404, "Nie ma takiej karty w bibliotece."
            del data["karty"][cid]
            data["przypiete"] = [x for x in data["przypiete"] if x != cid]
            self._write(data)
        return 200, ""

    def layout(self, pins=None, hide=None, show=None, clear_hidden=False, at=""):
        with self.lock:
            data = self._read()
            if pins is not None:
                data["przypiete"] = list(dict.fromkeys(pins))[:60]
            if hide:
                data["ukryte"][hide] = at
                data["przypiete"] = [x for x in data["przypiete"] if x != hide]
            if show:
                data["ukryte"].pop(show, None)
            if clear_hidden:
                data["ukryte"] = {}
            if len(data["ukryte"]) > 200:
                data["ukryte"] = dict(sorted(data["ukryte"].items(), key=lambda kv: kv[1])[-200:])
            if not self._write(data):
                return 413, "Układ płótna jest za duży."
        return 200, ""


# ---------- opis dla modelu (prompt asystenta) ----------
PROMPT = """Strona Asystent to płótno kart. Odpowiadasz krótko tekstem (1–3 zdania), a liczby, listy, tabele,
wykresy i newsy pokazujesz jako karty. Kartę opisujesz w bloku na końcu odpowiedzi (przed wierszami działań):
```karty
{"pokaz": [<karta>, …], "usun": ["<id karty>", …]}
```
Panel rysuje karty sam; nie piszesz HTML, CSS ani skryptów. Liczb nie podajesz z głowy: karta z `zapytanie`
liczy je w panelu z aktualnych danych. `dane` wprost tylko dla newsów, notatek i rzeczy spoza danych panelu.
Karta: {"id": "male-litery-i-myslniki", "typ": …, "tytul": "…", "opis": "jedno zdanie", "zapytanie": {…} albo
"dane": {…}, "rozmiar": "waska"|"szeroka", "zapisz": true}. Nieznany typ albo pole odrzuca kartę.
Typy:
- liczba: zapytanie (wynik: liczba pozycji albo suma miary); opcjonalnie "porownaj": {"etykieta": "…", "zapytanie": {…}};
  dane: {"wartosc": 12, "jednostka": "zł"}
- lista: zapytanie bez grupuj (zadania, publikacje, etapy; klik otwiera szczegóły) albo z grupuj (etykieta: wartość);
  dane: {"pozycje": [{"tekst": "…", "opis": "…", "link": "https://…"}]}
- tabela: zapytanie + "kolumny": [tytul, projekt, data, stan, kto, minuty, kanal, etap, postep, wartosc];
  dane: {"kolumny": ["…"], "wiersze": [["…", 1]]}
- wykres: zapytanie z grupuj + "rodzaj": "slupki"|"linia"; dane: {"punkty": [{"etykieta": "…", "wartosc": 3}]}
- postep: postęp projektów (zrobione z wszystkich zadań); zapytanie opcjonalne (filtr projekt, stan)
- tydzien: 7 dni od filtr.od (domyślnie dziś) z zadaniami albo publikacjami z zapytania
- notatka: dane: {"tekst": "…"} (zwykły tekst)
- news: dane: {"pozycje": [{"tytul": "…", "zrodlo": "nazwa serwisu", "data": "RRRR-MM-DD", "link": "https://…", "opis": "…"}]}
- panel: fragment panelu z przyciskami (odpowiedź na pytanie, zgoda, odbiór, zamknięcie, filtry); "widok": sprawy-dzis,
  sprawy, terminy, blokady, wskazniki, zadania, raport. Gotowe karty tego typu podajesz samym id (lista niżej).
Zapytanie: {"zrodlo": zadania|publikacje|etapy|projekty|kampanie|zasoby, "filtr": {…}, "grupuj": …, "miara": …,
"sortuj": …, "limit": 1–50}
- filtr: projekt (id albo nazwa, może być lista), stan (otwarte, zrobione, do zrobienia, w toku, zablokowane,
  do odbioru, po terminie; projekty: aktywne, wstrzymane, backlog, zakończone), kto (ty, claude, codex, agent, agenci,
  dla-ciebie = Twoje albo czekające na Ciebie), czeka (zgoda, odbiór, dowolne), od / do (dziś, jutro, wczoraj, +N, -N,
  RRRR-MM-DD; pozycje bez daty odpadają), szukaj (fragment tytułu), kanal (np. instagram), etap (fragment nazwy)
- grupuj: projekt, stan, kto, dzien, tydzien, etap, kanal
- miara: liczba (domyślnie), minuty (suma pola czas), wartosc (zasoby: procent zajęcia)
- sortuj: data, -data, tytul, projekt, wartosc, -wartosc
Przykłady:
- {"id": "zgody-czekaja", "typ": "liczba", "tytul": "Zgody czekają", "zapytanie": {"zrodlo": "zadania", "filtr": {"czeka": "zgoda", "stan": "otwarte"}}}
- {"id": "minuty-tydzien", "typ": "wykres", "rodzaj": "slupki", "tytul": "Twoje minuty w 7 dni", "zapytanie": {"zrodlo": "zadania", "filtr": {"kto": "ty", "od": "dziś", "do": "+6"}, "grupuj": "dzien", "miara": "minuty"}}
- {"id": "otwarte-wg-projektu", "typ": "tabela", "tytul": "Otwarte zadania", "kolumny": ["tytul", "projekt", "data"], "zapytanie": {"zrodlo": "zadania", "filtr": {"stan": "otwarte"}, "sortuj": "data", "limit": 15}}
Widoków Start, Dla Ciebie, Przegląd, Wskaźniki, Tablica, Terminy, Blokady i Projekty w panelu już nie ma: to, co
pokazywały, pokazujesz Ty kartami z tych samych danych. Sprawy dla Ciebie (pytania, zgody, odbiory, Twoje zadania
z przyciskami): {"id": "sprawy-dzis"}, pełna lista: {"id": "sprawy"}; publikacje: {"id": "publikacje-tygodnia"};
postęp projektów: {"id": "postep-projektow"}; nie twórz kart, które powtarzają te karty (np. „publikacje na dziś”:
pokaż publikacje-tygodnia, dziś jest w niej wyróżniony); terminy etapów, zadań i publikacji: {"id": "terminy"}; co
wstrzymuje ile zadań: {"id": "blokady"}; postęp, tempo, przepływ: {"id": "wskazniki"}; zadania ze wszystkich
projektów z filtrem projektu i stanu: {"id": "zadania"}; raport i notatka PM: {"id": "raport-pm"}. Węższe pytania
(np. terminy jednego projektu) odpowiadaj kartą z zapytaniem. Projekt dodaje się przyciskiem „+” przy liście projektów
w menu, Księga projektów i standard plików są w widoku Informacje (#informacje), Teraz i plan dnia w Agentach (#agenci).
Biblioteka: najpierw użyj gotowej karty z listy niżej, podając samo {"id": "…"}. Gdy żadna nie pasuje, opisz nową
z zapytaniem i dodaj "zapisz": true (panel zapamięta ją do następnego razu; karty z danymi wprost się nie zapisują).
Ten sam id w "pokaz" podmienia kartę. "usun" zdejmuje kartę z płótna. Przypina i usuwa z biblioteki właściciel.
Na tej stronie nie używaj „Pokaż:”: zamiast przełączać widok pokaż kartę. „Otwórz: <id>” otwiera szczegóły zadania."""

PROMPT_WEB = """Internet (WebSearch, WebFetch) tylko do odczytu, do kart news i ogólnych informacji. Zapytania i adresy
bez danych projektów: bez nazw klientów, projektów, osób, kwot i treści zadań; szukaj ogólnie (branża, temat,
narzędzie). Podaj źródło i link przy każdej pozycji. Nie wysyłasz niczego w formularzach."""
