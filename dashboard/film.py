"""Nagrywanie filmu z prawdziwej strony według scenariusza (bez człowieka przed ekranem).

Scenariusz: <folder posta>/scenariusz.json
  {"url": "https://opisarnia.pl/generator", "logowanie": "https://opisarnia.pl/logowanie", "kroki": [krok, …]}
  "url" i "logowanie": tylko https; gdy marka.json ma "strony", tylko te hosty (i ich subdomeny).
  "logowanie" (opcjonalnie): przed nagraniem logowanie kontem demo z pliku PANEL_FILM_KONTO
  (domyślnie ~/dane/film/konto.json: {"email", "haslo"}; wpisuje go właściciel w panelu, pliki 0600);
  wymaga hosta z "strony" w marka.json i tego samego hosta co "url".
Krok (klucze opcjonalne, wykonywane w tej kolejności; inne klucze to błąd):
  "napis": tekst na dole filmu od tego kroku do następnego napisu (do 80 znaków)
  "wpisz": [selektor, tekst]       pisanie znak po znaku (długi tekst szybciej, najwyżej ok. 1,4 s)
  "wybierz": [selektor, wartość]   lista rozwijana
  "kliknij": selektor              kliknięcie z podświetleniem
  "przewin": selektor              przewinięcie do elementu
  "rozwin": selektor               rozwinięcie <details>, gdy jest zwinięte
  "czekaj_na": selektor            czekanie, aż element się pojawi ("limit": sekundy 1–120, domyślnie 60);
                                   czekanie dłuższe niż 1,5 s jest w filmie wycięte
  "pauza": sekundy 0–30
  "opcjonalnie": true              błąd kroku nie przerywa nagrania
Wynik: <folder posta>/film.mp4, pion 1080×1920, 30 kl./s, napisy wtopione, ścieżka dźwięku (cisza albo
"muzyka" z marki); stan w .film-stan.json.

Studio filmów (wspólny warsztat projektu, obok KARTA.md):
  studio/marka.json              kolory, czcionki, styl napisów, logo, muzyka, plansza startowa i końcowa (BRAND_HELP)
  studio/szablony/<nazwa>.json   scenariusz z parametrami {{nazwa}}; "tytul": nazwa dla właściciela, "opis": kiedy
                                 go użyć, "parametry": wartości przykładowe, "wymagane": parametry, które scenariusz
                                 posta musi podać, "limity": {parametr: {"max": znaki, "opcje": [...]}},
                                 "etykiety": {parametr: "nazwa dla właściciela"}
  studio/obrazy/<plik>.png       obrazy do plansz objaśnienia (albo plik w folderze posta)
Scenariusz posta to jedno z:
  {"szablon": "pokaz-generatora", "parametry": {...}}      szablon z podstawionymi parametrami
  {"url": …, "kroki": [...], "plansze_przed": [...], "plansze_po": [...]}
                                                            pokaz: nagranie przeglądarki, opcjonalnie 1–4 plansze
                                                            objaśnienia przed i po nagraniu strony
  {"typ": "objasnienie", "plansze": [{"tekst", "podpis", "czas", "obraz"}, …]}
                                                            objaśnienie: plansze w kolorach marki, bez przeglądarki
  Tekst planszy do 90 znaków (*słowo* = wyróżnienie kolorem akcentu), podpis do 70; czas każdej planszy (także
  startowej i końcowej) wydłuża się sam do czasu czytania: 1,2 s + 15 znaków na sekundę (plansze marki + przejście).
  W scenariuszu pisanym ręcznie "{{" to zwykły tekst, a "opis" to komentarz.
"plansza_startowa" / "plansza_koncowa": false wyłącza planszę marki; obiekt {"tytul", "podtytul", "adres", "czas"}
zmienia ją w tym filmie: z własnym "tytul" (np. hak posta) bierze z marki tylko kolory, bez tytułu uzupełnia planszę
marki. Przy szablonie obiekt łączy się z planszą szablonu. Domyślnie plansze są, gdy marka je ma.

Uruchamiane osobnym interpreterem z Playwright (PANEL_FILM_PYTHON, domyślnie ~/narzedzia/film/bin/python):
  python film.py nagraj <folder posta> [rodzaj]
  python film.py sprawdz <folder posta>      rodzaj, szablon, treść, długość i błędy scenariusza (JSON), bez nagrywania
Objaśnienie nie potrzebuje Playwright (wystarczy ffmpeg; nagrywa je interpreter panelu). Panel woła to przez Recorder.
"""
import datetime
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse

try:                                    # pomiar szerokości tekstu; bez PIL: szacunek z szerokości znaków
    from PIL import ImageFont as _PILFont
except Exception:  # noqa: BLE001
    _PILFont = None
    # interpreter z Playwright (venv) bez pillow: PIL systemowego Pythona w tej samej wersji (plansze w pokazie)
    _SYS = "/usr/lib/python3/dist-packages"
    if os.path.isdir(os.path.join(_SYS, "PIL")) and _SYS not in sys.path:
        sys.path.append(_SYS)
        try:
            from PIL import ImageFont as _PILFont
        except Exception:  # noqa: BLE001
            _PILFont = None
        if _PILFont is None:
            sys.path.remove(_SYS)

SCENARIO = "scenariusz.json"
STATE = ".film-stan.json"
MANUAL = ".film-wgrany"          # film wgrany ręcznie w panelu: zmiana studia nie nagrywa go sama od nowa
VIEW = (540, 960)                 # CSS px; nagranie 2× = 1080×1920
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
TIMEOUT = 600
HOST = socket.gethostname()   # w stanie nagrania: kto nagrywa (panel na Macu i na serwerze mogą dzielić szkice/)


def account_file():
    return os.path.expanduser(os.environ.get("PANEL_FILM_KONTO", "").strip() or "~/dane/film/konto.json")


def save_account(email, password):
    """Konto demo do nagrań: zapis 0600; hasło nigdy nie wraca do panelu."""
    path = account_file()
    os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
    fd = os.open(path + ".tmp", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump({"email": email, "haslo": password}, f)
    os.replace(path + ".tmp", path)


def account_email():
    try:
        with open(account_file(), encoding="utf-8") as f:
            return json.load(f).get("email", "")
    except (OSError, ValueError):
        return ""


# kursor i podświetlenie kliknięć: w nagraniu headless nie ma kursora systemowego; kolory z marki (cursor_js)
CURSOR_JS = """
(() => {
  const add = () => {
    if (document.getElementById('__kursor')) return;
    const c = document.createElement('div'); c.id = '__kursor';
    c.style.cssText = 'position:fixed;z-index:2147483647;width:22px;height:22px;border-radius:50%%;' +
      'background:%(fill)s;border:2px solid #fff;box-shadow:0 0 0 1px rgba(0,0,0,.35);' +
      'pointer-events:none;transform:translate(-50%%,-50%%);left:-50px;top:-50px;transition:left .25s,top .25s';
    document.documentElement.appendChild(c);
    addEventListener('mousemove', e => { c.style.left = e.clientX + 'px'; c.style.top = e.clientY + 'px'; }, true);
    addEventListener('mousedown', e => {
      const r = document.createElement('div');
      r.style.cssText = 'position:fixed;z-index:2147483646;width:16px;height:16px;border-radius:50%%;' +
        'border:3px solid %(ring)s;pointer-events:none;transform:translate(-50%%,-50%%);transition:all .5s ease-out;' +
        'left:' + e.clientX + 'px;top:' + e.clientY + 'px;opacity:1';
      document.documentElement.appendChild(r);
      requestAnimationFrame(() => { r.style.width = '70px'; r.style.height = '70px'; r.style.opacity = '0'; });
      setTimeout(() => r.remove(), 600);
    }, true);
  };
  if (document.readyState === 'loading') addEventListener('DOMContentLoaded', add); else add();
})();
"""


def cursor_js(brand):
    """Skrypt kursora w kolorach marki: wypełnienie akcent2 (85% krycia), obwódka kliknięcia akcent."""
    kol = (brand or {}).get("kolory") or DEFAULT_BRAND["kolory"]
    fill_hex = kol.get("akcent2") or kol["akcent"]
    r, g, b = _rgb(fill_hex)
    return CURSOR_JS % {"fill": "rgba(%d,%d,%d,.85)" % (r, g, b), "ring": "#" + _hex6(kol["akcent"])}


def write_state(folder, **state):
    state["at"] = datetime.datetime.now().isoformat(timespec="seconds")
    tmp = os.path.join(folder, STATE + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)
    os.replace(tmp, os.path.join(folder, STATE))


def read_state(folder):
    """Stan nagrania z .film-stan.json; uszkodzony plik albo inny typ niż obiekt JSON: {}."""
    try:
        with open(os.path.join(folder, STATE), encoding="utf-8") as f:
            st = json.load(f)
    except (OSError, ValueError):
        return {}
    return st if isinstance(st, dict) else {}


# ---------- studio: marka, szablony, rodzaj filmu ----------
STUDIO = "studio"
TEMPLATES = "szablony"
IMAGES = "obrazy"
BRAND = "marka.json"
# jedno źródło nazw rodzajów (panel bierze kindLabel i kindHelp z describe/list_templates)
KINDS = {"pokaz": "pokaz strony", "objasnienie": "objaśnienie"}
KIND_HELP = {"pokaz": "nagranie strony w przeglądarce", "objasnienie": "plansze z tekstem w kolorach marki"}
SIZE = (1080, 1920)
SAFE_TOP, SAFE_BOTTOM = 250, 480      # strefy zasłaniane przez interfejs Reels/TikTok: nic ważnego wyżej i niżej
MARGIN = 90
TEXT_W = SIZE[0] - 2 * MARGIN
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,60}$")
PARAM_NAME_RE = re.compile(r"^[a-z0-9_]{1,40}$")
PARAM_RE = re.compile(r"\{\{\s*([a-z0-9_]+)\s*\}\}")
ANY_PARAM_RE = re.compile(r"\{\{(.*?)\}\}")
COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
WEIGHTS = {"Thin": 100, "ExtraLight": 200, "Light": 300, "Regular": 400, "Medium": 500, "SemiBold": 600,
           "Bold": 700, "ExtraBold": 800, "Black": 900}
FONT_RE = re.compile(r"^[A-Za-z][A-Za-z0-9 _-]{0,40}(?::(%s))?$" % "|".join(WEIGHTS))
IMAGE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,80}\.(?:png|jpe?g)$", re.I)
AUDIO_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,80}\.(?:mp3|m4a|aac|wav|ogg)$", re.I)
HOST_RE = re.compile(r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")
FONT_DIRS = ("~/.local/share/fonts", "~/.fonts", "/usr/local/share/fonts", "/usr/share/fonts",
             "~/Library/Fonts", "/Library/Fonts")
MAX_CARDS = 12
MAX_EXTRA_CARDS = 4               # plansze_przed / plansze_po w pokazie
MAX_STEPS = 60
CARD_TIME = (1.0, 12.0)
CARD_DEFAULT = 3.5                # s: plansza objaśnienia z podpisem bez podanego czasu
CARD_SHORT = 2.5                  # s: plansza bez podpisu bez podanego czasu (krótka plansza: szybsze tempo)
TEXT_MAX, CAPTION_MAX, NAPIS_MAX = 90, 70, 80
READ_CPS = 15                     # znaki na sekundę: czas czytania planszy (1,2 s + znaki / 15)
READ_BASE = 1.2
XFADE = 0.35                      # przejście między klipami (s)
FADE_OUT = 0.2                    # s: treść planszy gaśnie do tła tuż przed przejściem (bez podwójnej ekspozycji)
CARD_TIMES = {"plansza_startowa": 1.2, "plansza_koncowa": 3.0}
CAPTION_AT = 1.1                  # s: podpis planszy wchodzi jako druga informacja, po tekście
HOOK_CAPTION_AT = 0.6             # s: podpis haka (pierwsza plansza filmu, tekst od pierwszej klatki)
HOOK_BASE = 0.6                   # s: hak stoi od pierwszej klatki, więc bez czasu na wejście tekstu
HOOK_MAX = 3.5                    # s: dłuższy hak dostaje ostrzeżenie (pierwsze sekundy decydują o obejrzeniu)
POKAZ_MAX = 75                    # s: dłuższy pokaz dostaje ostrzeżenie
OBJ_MAX = 30                      # s: dłuższe objaśnienie dostaje ostrzeżenie (Reels)
HEAD_Y = 380                      # linia bazowa nazwy marki i licznika plansz (ok. 20% wysokości, pod nakładką Reels)
BAR_Y = 408                       # pasek postępu planszy: pod nazwą marki i licznikiem
CTRL_RE = re.compile(r"[\x00-\x1f\x7f]")      # znaki sterujące (nowy wiersz, tabulator, \x00) w tekstach filmu
IMAGE_MAX = 15 * 1024 * 1024      # obraz planszy albo logo
AUDIO_MAX = 30 * 1024 * 1024      # muzyka marki
# Bez marka.json: wygląd napisów jak dotąd (biały tekst na ciemnym pasku), plansze w neutralnych kolorach.
DEFAULT_BRAND = {"nazwa": "", "zrodlo": "", "strony": [], "muzyka": "", "logo": "", "logo_w_rogu": False,
                 "kolory": {"tlo": "#f4f4f2", "tekst": "#1d1d1f", "akcent": "#3b5bdb", "akcent2": "#868e96"},
                 "czcionki": {"tytul": "", "tekst": "", "napisy": ""},
                 "napisy": {"rozmiar": 56, "kolor": "#ffffff", "tlo": "#2b1d12", "krycie": 0.85},
                 "plansza_startowa": None, "plansza_koncowa": None}
BRAND_KEYS = set(DEFAULT_BRAND)
CARD_KEYS = {"tytul", "podtytul", "adres", "czas", "tlo", "kolor"}
CARD_COLORS = ("tlo", "kolor")    # nadpisanie tytułu planszy w filmie dziedziczy z marki tylko kolory
BRAND_HELP = ('marka.json: {"nazwa", "zrodlo", "strony": ["host"], "muzyka": "plik w studio/", '
              '"logo": "plik .png w studio/ (przezroczyste tło)", "logo_w_rogu": true|false, '
              '"kolory": {"tlo", "tekst", "akcent", "akcent2"} (#rrggbb), "czcionki": {"tytul", "tekst", "napisy"} '
              '(nazwa czcionki, opcjonalnie ":Bold" itp.), "napisy": {"rozmiar" 24–120, "kolor", "tlo", "krycie" 0–1}, '
              '"plansza_startowa" / "plansza_koncowa": {"tytul", "podtytul", "adres", "czas" s, "tlo", "kolor"}}')
# klucze scenariusza według rodzaju; "opis" to komentarz (pomijany); szablon ma dodatkowo TEMPLATE_EXTRA
SC_KEYS = {"pokaz": {"typ", "opis", "url", "logowanie", "kroki", "plansze_przed", "plansze_po",
                     "plansza_startowa", "plansza_koncowa"},
           "objasnienie": {"typ", "opis", "plansze", "plansza_startowa", "plansza_koncowa"}}
TEMPLATE_EXTRA = {"opis", "tytul", "parametry", "etykiety", "wymagane", "limity", "dla_wlasciciela"}
LIMIT_KEYS = {"max", "opcje", "cyfry"}
TEXT_KEYS = {"napis", "tekst", "podpis", "tytul", "podtytul", "adres"}   # liczba z parametru staje się tekstem
WITH_TEMPLATE = {"szablon", "parametry", "plansza_startowa", "plansza_koncowa", "opis"}
STEP_KEYS = ("napis", "wpisz", "wybierz", "kliknij", "przewin", "rozwin", "czekaj_na", "limit", "pauza", "opcjonalnie")
CARD_SC_KEYS = {"tekst", "podpis", "czas", "obraz"}


def studio_dir(folder):
    """Studio projektu dla folderu posta <karta>/posty/<nazwa>/: <karta>/studio."""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(folder))), STUDIO)


def _inside(path, studio):
    """Plik studia nie wychodzi poza kartę projektu (dowiązania do innych folderów odrzucone)."""
    base = os.path.realpath(os.path.dirname(os.path.abspath(studio)))
    real = os.path.realpath(path)
    try:
        return os.path.commonpath([base, real]) == base
    except ValueError:
        return False


def _load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _num(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _strings(value):
    """Wszystkie teksty w strukturze JSON."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for v in value:
            yield from _strings(v)
    elif isinstance(value, dict):
        for v in value.values():
            yield from _strings(v)


MAGIC = {"png": (b"\x89PNG\r\n\x1a\n",), "jpg": (b"\xff\xd8\xff",), "jpeg": (b"\xff\xd8\xff",),
         "mp3": (b"ID3", b"\xff\xfb", b"\xff\xf3", b"\xff\xf2", b"\xff\xe3"), "wav": (b"RIFF",), "ogg": (b"OggS",),
         "aac": (b"\xff\xf1", b"\xff\xf9", b"ID3")}
# demuxer ffmpeg według rozszerzenia: ffmpeg nie zgaduje formatu z treści (plik .png z playlistą HLS nie wciągnie
# innych plików)
DEMUXER = {"mp3": "mp3", "wav": "wav", "ogg": "ogg", "aac": "aac", "m4a": "mov"}


def media_error(path, kind):
    """Opis błędu pliku obrazu albo muzyki (rozmiar, zgodność treści z rozszerzeniem); "" gdy w porządku."""
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            head = f.read(16)
    except OSError:
        return "nie da się odczytać pliku"
    limit = IMAGE_MAX if kind == "image" else AUDIO_MAX
    if not 0 < size <= limit:
        return "plik do %d MB" % (limit // (1024 * 1024))
    if ext == "m4a":
        return "" if head[4:8] == b"ftyp" else "treść pliku nie jest M4A"
    if ext in MAGIC and not head.startswith(MAGIC[ext]):
        return "treść pliku nie zgadza się z rozszerzeniem .%s" % ext
    if kind == "image":
        dims = _image_size(path, ext)
        if dims is None:
            return "nie da się odczytać wymiarów obrazu"
        if not (0 < dims[0] <= IMAGE_PX and 0 < dims[1] <= IMAGE_PX):
            return "obraz do %d×%d px (jest %d×%d)" % (IMAGE_PX, IMAGE_PX, dims[0], dims[1])
    return ""


IMAGE_PX = 6000                   # bok obrazu planszy albo logo (mały plik o ogromnych wymiarach zjada pamięć ffmpeg)


def _image_size(path, ext):
    """(szerokość, wysokość) z nagłówka PNG (IHDR) albo JPEG (znacznik SOF); None, gdy nie da się odczytać."""
    try:
        with open(path, "rb") as f:
            if ext == "png":
                head = f.read(24)
                return (int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")) \
                    if head[12:16] == b"IHDR" else None
            data = f.read(512 * 1024)
    except OSError:
        return None
    i = 2
    while i + 9 < len(data):
        if data[i] != 0xFF:
            return None
        marker = data[i + 1]
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        seg = int.from_bytes(data[i + 2:i + 4], "big")
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            return int.from_bytes(data[i + 7:i + 9], "big"), int.from_bytes(data[i + 5:i + 7], "big")
        i += 2 + seg
    return None


def media_input(path, seconds=None):
    """Argumenty wejścia ffmpeg dla pliku z karty: tylko protokół file i jawny demuxer (obraz: image2 bez wzorca
    nazw, zapętlony przez seconds; muzyka: demuxer z rozszerzenia, zapętlona)."""
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    if ext in DEMUXER:
        return ["-protocol_whitelist", "file", "-stream_loop", "-1", "-f", DEMUXER[ext], "-i", path]
    return ["-protocol_whitelist", "file", "-f", "image2", "-pattern_type", "none", "-loop", "1",
            "-t", "%.2f" % (seconds or 1), "-i", path]


def _card_errors(card, key, need_title=True):
    """Błędy planszy marki (marka.json albo nadpisanie w scenariuszu)."""
    err = []
    if not isinstance(card, dict):
        return ["%s: obiekt z tytul, podtytul, adres, czas" % key]
    for sub in card:
        if sub not in CARD_KEYS:
            err.append("%s.%s: nieznany klucz" % (key, sub))
    if need_title and not (isinstance(card.get("tytul"), str) and card["tytul"].strip()):
        err.append("%s.tytul: brak" % key)
    for sub, limit in (("tytul", 60), ("podtytul", 80), ("adres", 60)):
        if sub in card and not (isinstance(card[sub], str) and len(card[sub]) <= limit):
            err.append("%s.%s: tekst do %d znaków" % (key, sub, limit))
    if "czas" in card and not (_num(card["czas"]) and CARD_TIME[0] <= card["czas"] <= CARD_TIME[1]):
        err.append("%s.czas: %g–%g s" % ((key,) + CARD_TIME))
    for sub in ("tlo", "kolor"):
        if sub in card and not (isinstance(card[sub], str) and COLOR_RE.match(card[sub])):
            err.append("%s.%s: kolor #rrggbb" % (key, sub))
    return err


def validate_brand(b):
    """Błędy marka.json po polsku (pusta lista: poprawna)."""
    if not isinstance(b, dict):
        return ["marka.json: oczekiwany obiekt JSON"]
    err = ["%s: nieznany klucz" % k for k in b if k not in BRAND_KEYS]
    for key in ("nazwa", "zrodlo"):
        if key in b and not isinstance(b[key], str):
            err.append("%s: tekst" % key)
    if "strony" in b and not (isinstance(b["strony"], list) and len(b["strony"]) <= 5
                              and all(isinstance(h, str) and HOST_RE.match(h) for h in b["strony"])):
        err.append("strony: lista hostów, np. [\"opisarnia.pl\"]")
    if b.get("muzyka") and not (isinstance(b["muzyka"], str) and AUDIO_RE.match(b["muzyka"])):
        err.append("muzyka: nazwa pliku mp3/m4a/wav/ogg w studio/")
    if b.get("logo") and not (isinstance(b["logo"], str) and IMAGE_RE.match(b["logo"])):
        err.append("logo: nazwa pliku .png w studio/")
    if "logo_w_rogu" in b and not isinstance(b["logo_w_rogu"], bool):
        err.append("logo_w_rogu: true albo false")
    kol = b.get("kolory")
    if not isinstance(kol, dict):
        err.append("kolory: obiekt z tlo, tekst, akcent")
    else:
        for key in ("tlo", "tekst", "akcent"):
            if key not in kol:
                err.append("kolory.%s: brak" % key)
        for key, value in kol.items():
            if key not in ("tlo", "tekst", "akcent", "akcent2"):
                err.append("kolory.%s: nieznany klucz" % key)
            elif not (isinstance(value, str) and COLOR_RE.match(value)):
                err.append("kolory.%s: kolor #rrggbb" % key)
    cz = b.get("czcionki", {})
    if not isinstance(cz, dict) or any(k not in ("tytul", "tekst", "napisy") for k in cz):
        err.append("czcionki: obiekt z tytul, tekst, napisy (nazwy czcionek)")
    else:
        for k, v in cz.items():
            if not (isinstance(v, str) and (v == "" or FONT_RE.match(v))):
                err.append("czcionki.%s: nazwa czcionki (litery, cyfry, spacja), opcjonalnie „:Bold”; bez ścieżek" % k)
    nap = b.get("napisy", {})
    if not isinstance(nap, dict):
        err.append("napisy: obiekt")
    else:
        if "rozmiar" in nap and not (_num(nap["rozmiar"]) and 24 <= nap["rozmiar"] <= 120):
            err.append("napisy.rozmiar: liczba 24–120")
        if "krycie" in nap and not (_num(nap["krycie"]) and 0 <= nap["krycie"] <= 1):
            err.append("napisy.krycie: liczba 0–1")
        for key in ("kolor", "tlo"):
            if key in nap and not (isinstance(nap[key], str) and COLOR_RE.match(nap[key])):
                err.append("napisy.%s: kolor #rrggbb" % key)
    for key in ("plansza_startowa", "plansza_koncowa"):
        if b.get(key) is not None:
            err += _card_errors(b[key], key)
    return err


def load_brand(studio):
    """(marka z wartościami domyślnymi, błędy, czy plik jest). Błędna marka: wartości domyślne i lista błędów."""
    path = os.path.join(studio, BRAND)
    if not os.path.isfile(path):
        return json.loads(json.dumps(DEFAULT_BRAND)), [], False
    if not _inside(path, studio):
        return json.loads(json.dumps(DEFAULT_BRAND)), ["marka.json: plik poza kartą projektu"], True
    try:
        raw = _load_json(path)
    except (OSError, ValueError) as e:
        return json.loads(json.dumps(DEFAULT_BRAND)), ["marka.json: niepoprawny JSON (%s)" % str(e)[:80]], True
    errors = validate_brand(raw)
    brand = json.loads(json.dumps(DEFAULT_BRAND))
    for key, kind in (("muzyka", "audio"), ("logo", "image")):
        if not errors and raw.get(key):
            path = os.path.join(studio, raw[key])
            if not (os.path.isfile(path) and _inside(path, studio)):
                errors.append("%s: brak pliku studio/%s" % (key, raw[key]))
            else:
                bad = media_error(path, kind)
                if bad:
                    errors.append("%s: %s" % (key, bad))
    if errors:
        return brand, errors, True
    for key, value in raw.items():
        if isinstance(value, dict) and isinstance(brand.get(key), dict):
            brand[key].update(value)
        else:
            brand[key] = value
    if "akcent2" not in raw["kolory"]:           # bez drugiego akcentu: akcent marki, nie neutralny domyślny
        brand["kolory"]["akcent2"] = brand["kolory"]["akcent"]
    return brand, [], True


def _param_value(name, value):
    if isinstance(value, str) or _num(value):
        return value
    raise ValueError("parametr „%s”: tekst albo liczba (jest %s)" % (
        name, "null" if value is None else type(value).__name__.replace("dict", "obiekt").replace("list", "lista")))


def fill(value, params):
    """Podstawia {{nazwa}} w tekstach (także w listach i obiektach). Sam znacznik "{{x}}" przyjmuje typ parametru
    (liczba zostaje liczbą). Brak parametru albo wartość inna niż tekst i liczba: ValueError."""
    if isinstance(value, str):
        whole = PARAM_RE.fullmatch(value.strip())
        if whole and whole.group(1) in params and not isinstance(params[whole.group(1)], str):
            return _param_value(whole.group(1), params[whole.group(1)])

        def one(m):
            if m.group(1) not in params:
                raise ValueError("brak parametru „%s”" % m.group(1))
            return str(_param_value(m.group(1), params[m.group(1)]))
        return PARAM_RE.sub(one, value)
    if isinstance(value, list):
        return [fill(v, params) for v in value]
    if isinstance(value, dict):
        return {k: fill(v, params) for k, v in value.items()}
    return value


def placeholders(value, out=None):
    """Nazwy parametrów {{…}} użyte w szablonie."""
    out = set() if out is None else out
    for s in _strings(value):
        out.update(PARAM_RE.findall(s))
    return out


def _leftover(value):
    """Pierwszy niepodstawiony albo błędny znacznik {{…}} (np. {{Kolor}}, {{typ-mebla}}, „{{ x }”)."""
    for s in _strings(value):
        if "{{" in s or "}}" in s:
            m = ANY_PARAM_RE.search(s)
            return m.group(0) if m else s[:40]
    return ""


def kind_of(sc):
    return "objasnienie" if isinstance(sc, dict) and sc.get("typ") == "objasnienie" else "pokaz"


def _step_errors(i, k):
    err = []
    if not isinstance(k, dict):
        return ["krok %d: obiekt" % i]
    for key in k:
        if key not in STEP_KEYS:
            err.append("krok %d: nieznany klucz „%s” (dozwolone: %s)" % (i, key, ", ".join(STEP_KEYS)))
    if "napis" in k and not (isinstance(k["napis"], str) and len(k["napis"]) <= NAPIS_MAX):
        err.append("krok %d: napis do %d znaków" % (i, NAPIS_MAX))
    for key in ("wpisz", "wybierz"):
        if key in k and not (isinstance(k[key], list) and len(k[key]) == 2 and isinstance(k[key][0], str)
                             and k[key][0].strip() and (isinstance(k[key][1], str) or _num(k[key][1]))):
            err.append("krok %d: %s to [selektor, tekst]" % (i, key))
    for key in ("kliknij", "przewin", "rozwin", "czekaj_na"):
        if key in k and not (isinstance(k[key], str) and k[key].strip()):
            err.append("krok %d: %s to selektor (tekst)" % (i, key))
    if "pauza" in k and not (_num(k["pauza"]) and 0 <= k["pauza"] <= 30):
        err.append("krok %d: pauza 0–30 s" % i)
    if "limit" in k and not (_num(k["limit"]) and 1 <= k["limit"] <= 120):
        err.append("krok %d: limit 1–120 s" % i)
    if "opcjonalnie" in k and not isinstance(k["opcjonalnie"], bool):
        err.append("krok %d: opcjonalnie true albo false" % i)
    return err


def _slides_errors(cards, what, limit):
    """Błędy listy plansz objaśnienia (plansze, plansze_przed, plansze_po)."""
    if not isinstance(cards, list) or not 1 <= len(cards) <= limit:
        return ["%s: lista 1–%d plansz" % (what, limit)]
    err = []
    for i, c in enumerate(cards, 1):
        label = "plansza %d" % i if what == "plansze" else "%s, plansza %d" % (what, i)
        if not isinstance(c, dict):
            err.append("%s: obiekt z tekst, podpis, czas" % label)
            continue
        bad = sorted(set(c) - CARD_SC_KEYS)
        if bad:
            err.append("%s: nieznany klucz „%s”" % (label, bad[0]))
        if not (isinstance(c.get("tekst"), str) and 0 < len(c["tekst"].strip()) <= TEXT_MAX):
            err.append("%s: tekst 1–%d znaków" % (label, TEXT_MAX))
        elif c["tekst"].count("*") % 2:
            err.append("%s: wyróżnienie *słowo* bez drugiej gwiazdki" % label)
        if "podpis" in c and not (isinstance(c["podpis"], str) and len(c["podpis"]) <= CAPTION_MAX):
            err.append("%s: podpis do %d znaków" % (label, CAPTION_MAX))
        if "czas" in c and not (_num(c["czas"]) and CARD_TIME[0] <= c["czas"] <= CARD_TIME[1]):
            err.append("%s: czas %g–%g s" % ((label,) + CARD_TIME))
        if "obraz" in c and not (isinstance(c["obraz"], str) and IMAGE_RE.match(c["obraz"])):
            err.append("%s: obraz to nazwa pliku .png albo .jpg" % label)
    return err


def validate_scenario(sc, extra=(), template=False):
    """Błędy rozwiniętego scenariusza (po podstawieniu szablonu). extra: dodatkowe dozwolone klucze (szablon).
    template: scenariusz powstał z szablonu, więc znacznik {{…}} w tekście to niepodstawiony parametr (w scenariuszu
    pisanym ręcznie „{{” to zwykły tekst)."""
    if not isinstance(sc, dict):
        return ["scenariusz: oczekiwany obiekt JSON"]
    typ = sc.get("typ", "pokaz")
    if typ not in KINDS:
        return ["typ: „pokaz” albo „objasnienie”"]
    err = []
    left = _leftover(sc) if template else ""
    if left:
        err.append("niepodstawiony znacznik %s (nazwy parametrów: małe litery, cyfry, _)" % left)
    ctrl = next((s for s in _strings(sc) if CTRL_RE.search(s)), None)
    if ctrl is not None:
        err.append("tekst „%s”: bez znaków sterujących (nowy wiersz, tabulator)" % CTRL_RE.sub(" ", ctrl)[:40])
    unknown = sorted(k for k in sc if k not in SC_KEYS[typ] and k not in extra)
    if unknown:
        err.append("nieznany klucz „%s” w scenariuszu rodzaju %s" % (unknown[0], typ))
    if "opis" in sc and not isinstance(sc["opis"], str):
        err.append("opis: tekst (komentarz)")
    if typ == "objasnienie":
        bad = _slides_errors(sc.get("plansze"), "plansze", MAX_CARDS)
        if bad and bad[0].startswith("plansze:"):
            return err + bad
        err += bad
    else:
        if not (isinstance(sc.get("url"), str) and sc["url"].strip()):
            err.append("url: adres strony do nagrania (https://…)")
        if "logowanie" in sc and not isinstance(sc["logowanie"], str):
            err.append("logowanie: adres strony logowania (https://…)")
        steps = sc.get("kroki")
        if not isinstance(steps, list) or not 1 <= len(steps) <= MAX_STEPS:
            err.append("kroki: lista 1–%d kroków" % MAX_STEPS)
        else:
            for i, k in enumerate(steps, 1):
                err += _step_errors(i, k)
        for key in ("plansze_przed", "plansze_po"):
            if key in sc:
                err += _slides_errors(sc[key], key, MAX_EXTRA_CARDS)
    for key in ("plansza_startowa", "plansza_koncowa"):
        if key in sc and not isinstance(sc[key], bool):
            err += _card_errors(sc[key], key, need_title=False) if isinstance(sc[key], dict) else \
                ["%s: true, false albo obiekt {tytul, podtytul, adres, czas}" % key]
    return err


PRIVATE_SUFFIXES = (".local", ".localhost", ".internal", ".lan", ".home", ".corp", ".intranet", ".arpa")


def public_host(host):
    """Host publicznej strony: nazwa domenowa z TLD (nie adres IP, nie localhost ani nazwa sieci lokalnej)."""
    host = (host or "").lower().rstrip(".")
    return bool(HOST_RE.match(host)) and not host.endswith(PRIVATE_SUFFIXES) and host != "localhost"


def host_allowed(host, sites):
    """Host strony: z "strony" w marce (i ich subdomeny); bez listy: każdy publiczny host (tylko do pomocniczych
    kontroli; pokaz bez "strony" w marce się nie nagra, site_errors)."""
    host = (host or "").lower()
    if sites:
        return any(host == h or host.endswith("." + h) for h in sites)
    return public_host(host)


def _host(url):
    try:
        u = urllib.parse.urlsplit(url)
    except ValueError:
        return None, ""
    return u, (u.hostname or "").lower()


def site_errors(sc, brand):
    """Adresy pokazu: tylko https i tylko hosty z "strony" w marce (i ich subdomeny); bez "strony" pokaz się nie
    nagra (nazwa publiczna może wskazywać adres lokalny, np. przez DNS). Logowanie tylko na hoście z marki i z url."""
    if kind_of(sc) != "pokaz":
        return []
    sites = [h.lower() for h in (brand.get("strony") or [])]
    err = []
    u, host = _host(sc.get("url") or "")
    if not u or u.scheme != "https" or not host or u.username or u.password:
        err.append("url: tylko adres https://")
    elif not sites:
        err.append("url: pokaz nagrywa tylko strony z marka.json (pole strony); dopisz tam %s" % host)
    elif not host_allowed(host, sites):
        err.append("url: host %s spoza stron marki (marka.json: strony)" % host)
    if sc.get("logowanie"):
        lu, lhost = _host(sc["logowanie"])
        if not lu or lu.scheme != "https" or not lhost or lu.username or lu.password:
            err.append("logowanie: tylko adres https://")
        elif not sites or not host_allowed(lhost, sites):
            err.append("logowanie: konto demo wpisuję tylko na stronie z marka.json (pole strony)")
        elif lhost != host:
            err.append("logowanie: inny host niż url (%s)" % lhost)
    return err


def load_template(studio, name):
    """Szablon studio/szablony/<nazwa>.json; ValueError z opisem."""
    if not isinstance(name, str) or not NAME_RE.match(name):
        raise ValueError("nazwa szablonu: małe litery, cyfry i „-”")
    path = os.path.join(studio, TEMPLATES, name + ".json")
    if not os.path.isfile(path):
        raise ValueError("brak szablonu %s/%s/%s.json" % (STUDIO, TEMPLATES, name))
    if not _inside(path, studio):
        raise ValueError("szablon %s: plik poza kartą projektu" % name)
    try:
        tpl = _load_json(path)
    except (OSError, ValueError) as e:
        raise ValueError("szablon %s: niepoprawny JSON (%s)" % (name, str(e)[:80]))
    if not isinstance(tpl, dict):
        raise ValueError("szablon %s: oczekiwany obiekt JSON" % name)
    params = tpl.get("parametry", {})
    if not isinstance(params, dict):
        raise ValueError("szablon %s: parametry to obiekt" % name)
    for k, v in params.items():
        if not PARAM_NAME_RE.match(k):
            raise ValueError("szablon %s: nazwa parametru „%s” (małe litery, cyfry, _)" % (name, k))
        try:
            _param_value(k, v)
        except ValueError as e:
            raise ValueError("szablon %s: %s" % (name, e))
    labels = tpl.get("etykiety", {})
    if not (isinstance(labels, dict) and all(isinstance(v, str) for v in labels.values())):
        raise ValueError("szablon %s: etykiety to obiekt {parametr: nazwa}" % name)
    for key in ("opis", "tytul", "dla_wlasciciela"):
        if key in tpl and not isinstance(tpl[key], str):
            raise ValueError("szablon %s: %s to tekst" % (name, key))
    body = _body(tpl)
    names = set(params) | placeholders(body)
    req = tpl.get("wymagane", [])
    if not (isinstance(req, list) and all(isinstance(x, str) and x in names for x in req)):
        raise ValueError("szablon %s: wymagane to lista nazw parametrów szablonu" % name)
    lim = tpl.get("limity", {})
    if not isinstance(lim, dict):
        raise ValueError("szablon %s: limity to obiekt {parametr: {max, opcje}}" % name)
    for k, v in lim.items():
        if k not in names or not isinstance(v, dict) or set(v) - LIMIT_KEYS \
                or ("max" in v and not (_num(v["max"]) and v["max"] >= 1)) \
                or ("cyfry" in v and not isinstance(v["cyfry"], bool)) \
                or ("opcje" in v and not (isinstance(v["opcje"], list) and v["opcje"]
                                         and all(isinstance(o, (str, int, float)) for o in v["opcje"]))):
            raise ValueError("szablon %s: limity.%s: {\"max\": liczba znaków, \"opcje\": [dozwolone wartości], "
                             "\"cyfry\": true}" % (name, k))
    for s in _strings(body):
        for m in ANY_PARAM_RE.finditer(s):
            if not PARAM_NAME_RE.match(m.group(1).strip()):
                raise ValueError("szablon %s: zły znacznik %s (nazwy: małe litery, cyfry, _)" % (name, m.group(0)))
    typ = tpl.get("typ", "pokaz")
    if typ not in KINDS:
        raise ValueError("szablon %s: typ „pokaz” albo „objasnienie”" % name)
    unknown = sorted(k for k in tpl if k not in SC_KEYS.get(typ, set()) | TEMPLATE_EXTRA)
    if unknown:
        raise ValueError("szablon %s: nieznany klucz „%s”" % (name, unknown[0]))
    return tpl


def _body(tpl):
    """Część szablonu, która staje się scenariuszem (bez opisu, tytułu, parametrów, etykiet, wymagań i limitów)."""
    return {k: v for k, v in tpl.items() if k not in TEMPLATE_EXTRA}


def template_params(tpl):
    """Parametry szablonu w kolejności pojawienia się w filmie (pierwsze użycie w treści szablonu), potem
    zadeklarowane, ale nieużyte. Znaczniki liczone tylko z treści (nie z opisu, etykiet ani wartości domyślnych)."""
    used = []
    for s in _strings(_body(tpl)):
        for m in PARAM_RE.finditer(s):
            if m.group(1) not in used:
                used.append(m.group(1))
    return used + [k for k in (tpl.get("parametry") or {}) if k not in used]


def template_title(tpl, name):
    """Czytelna nazwa szablonu dla właściciela: pole "tytul", inaczej identyfikator."""
    return str(tpl.get("tytul") or "").strip()[:80] or name


def _check_value(name, value, limits):
    """Wartość parametru przed podstawieniem: tekst albo liczba, bez znaczników {{ }}, bez samych spacji,
    w limitach szablonu."""
    _param_value(name, value)
    if isinstance(value, str):
        if "{{" in value or "}}" in value:
            raise ValueError("parametr „%s”: wartość nie może zawierać {{ ani }}" % name)
        if value and not value.strip():
            raise ValueError("parametr „%s”: same spacje" % name)
        if CTRL_RE.search(value):      # \n w kroku „wpisz” to Enter w formularzu, \x00 obcina tekst planszy
            raise ValueError("parametr „%s”: bez znaków sterujących (nowy wiersz, tabulator)" % name)
    lim = limits.get(name) or {}
    if "max" in lim and len(str(value)) > lim["max"]:
        raise ValueError("parametr „%s”: najwyżej %d znaków (jest %d)" % (name, lim["max"], len(str(value))))
    if lim.get("cyfry") and not re.fullmatch(r"[0-9]+", str(value)):
        raise ValueError("parametr „%s”: same cyfry (jest „%s”)" % (name, value))
    if "opcje" in lim and str(value) not in [str(o) for o in lim["opcje"]]:
        raise ValueError("parametr „%s”: jedna z wartości %s (jest „%s”)"
                         % (name, ", ".join(str(o) for o in lim["opcje"]), value))


def _as_text(value, key=None):
    """Liczba podstawiona w polu tekstowym (napis, tekst, podpis, tytuł…) staje się tekstem."""
    if isinstance(value, dict):
        return {k: _as_text(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [_as_text(v, key if key in TEXT_KEYS else None) for v in value]
    if key in TEXT_KEYS and _num(value):
        return ("%g" % value) if isinstance(value, float) else str(value)
    return value


def expand(sc, studio, meta=None):
    """(scenariusz po podstawieniu szablonu, nazwa szablonu albo ""). ValueError przy błędzie.
    meta (słownik): uzupełniany opisem szablonu, etykietami i parametrami z wartościami (dla panelu).
    Plansza startowa albo końcowa ze scenariusza jako obiekt łączy się z planszą szablonu (po podstawieniu);
    false albo true zastępuje ją w całości."""
    if not isinstance(sc, dict):
        raise ValueError("scenariusz: oczekiwany obiekt JSON")
    if "szablon" not in sc:
        return sc, ""
    name = sc["szablon"]
    tpl = load_template(studio, name)
    extra = sorted(k for k in sc if k not in WITH_TEMPLATE)
    if extra:
        raise ValueError("obok „szablon” dozwolone tylko parametry, plansza_startowa, plansza_koncowa (jest „%s”)"
                         % extra[0])
    given = sc.get("parametry", {})
    if not isinstance(given, dict):
        raise ValueError("parametry: obiekt {nazwa: wartość}")
    body = _body(tpl)
    defaults = tpl.get("parametry") or {}
    names = template_params(tpl)
    unknown = sorted(set(given) - set(names))
    if unknown:
        raise ValueError("szablon %s nie ma parametru „%s”" % (name, unknown[0]))
    limits = tpl.get("limity") or {}
    given = coerce_params(tpl, given)
    for k, v in given.items():
        _check_value(k, v, limits)
    for k in tpl.get("wymagane") or []:
        v = given.get(k)
        if v is None or (isinstance(v, str) and not v.strip()):
            raise ValueError("brak parametru „%s” (wymagany w szablonie %s: treść tego posta)" % (k, name))
    params = dict(defaults, **given)
    for k, v in defaults.items():
        if k not in given:
            _check_value(k, v, limits)
    out = _as_text(fill(body, params))
    for key in ("plansza_startowa", "plansza_koncowa"):
        if key in sc:
            mine, base = sc[key], out.get(key)
            out[key] = dict(base, **mine) if isinstance(mine, dict) and isinstance(base, dict) else mine
    left = _leftover(out)
    if left:
        raise ValueError("niepodstawiony znacznik %s (nazwy parametrów: małe litery, cyfry, _)" % left)
    if meta is not None:
        labels = tpl.get("etykiety") or {}
        changed = {k for k, v in given.items() if k not in defaults or str(v) != str(defaults[k])}
        fields = field_map(body, out, sc)
        groups = _param_groups(fields)
        params_meta = []
        for k in names:
            lim = limits.get(k) or {}
            item = {"name": k, "label": labels.get(k) or k.replace("_", " "),
                    "value": str(params[k]) if k in params else "", "changed": k in changed,
                    "group": groups.get(k, "inne"), "markup": k in fields["markup"],
                    "max": int(lim["max"]) if "max" in lim else _default_max(k, fields),
                    "required": k in (tpl.get("wymagane") or [])}
            if "opcje" in lim:
                item["options"] = [str(o) for o in lim["opcje"]]
            if lim.get("cyfry"):
                item["digits"] = True
            params_meta.append(item)
        # plansze z przykładowym tekstem szablonu: filmy z tego szablonu nie mogą być co tydzień takie same
        cards = [c for key in ("slides", "before", "after") for c in fields[key] if c["text"] or c["params"]]
        stock = [c for c in cards if c["params"] and not any(p in changed for p in c["params"])]
        meta.update(desc=tpl.get("opis") or "", owner=str(tpl.get("dla_wlasciciela") or "").strip(),
                    title=template_title(tpl, name), params=params_meta, fields=fields,
                    same=bool(defaults) and not changed and not tpl.get("wymagane"),
                    stock=(len(stock), len(cards)), values={k: str(v) for k, v in params.items()},
                    required=list(tpl.get("wymagane") or []))
    return out, name


def coerce_params(tpl, given):
    """Wartość z formularza panelu (tekst) dla parametru, którego wartość przykładowa w szablonie jest liczbą: liczba
    (np. "5" → 5 w polu czas). Tekst, który nie jest liczbą, zostaje (kontrola zgłosi błąd w polu)."""
    defaults = tpl.get("parametry") or {}
    out = dict(given)
    for k, v in given.items():
        if isinstance(v, str) and _num(defaults.get(k)):
            try:
                num = float(v.strip().replace(",", "."))
            except ValueError:
                continue
            out[k] = int(num) if num.is_integer() and isinstance(defaults[k], int) else num
    return out


def _uses(value):
    """(parametry {{…}} w wartości po kolei, czy cała wartość to jeden znacznik)."""
    names = []
    for s in _strings(value):
        for m in PARAM_RE.finditer(s):
            if m.group(1) not in names:
                names.append(m.group(1))
    whole = isinstance(value, str) and bool(PARAM_RE.fullmatch(value.strip())) and len(names) == 1
    return names, whole


def field_map(body, out, raw):
    """Skąd pochodzi treść filmu z szablonu (dla panelu, bez zgadywania po wartościach):
    {"intro"|"outro": {"params": [...], "fields": {"tytul"|"podtytul"|"adres": parametr}} albo None,
     "slides"|"before"|"after": [{"params": [...], "text": parametr albo "", "caption": parametr albo ""}],
     "captions": [[parametry napisu]] (napisy, które są w filmie), "form": [parametry wpisywane w formularz],
     "markup": [parametry w tekście planszy, gdzie *słowo* = kolor akcentu]}.
    "text"/"caption"/"fields": parametr, gdy całe pole to jeden znacznik (inaczej pole ma kilka parametrów albo stały
    tekst i panel pokazuje do zmiany same parametry)."""
    fm = {"intro": None, "outro": None, "slides": [], "before": [], "after": [], "captions": [], "form": [],
          "markup": []}
    for key, which in (("plansza_startowa", "intro"), ("plansza_koncowa", "outro")):
        card, own = body.get(key), raw.get(key)
        if not isinstance(card, dict) or (key in raw and not isinstance(own, dict)):
            continue
        entry = {"params": [], "fields": {}}
        for sub in ("tytul", "podtytul", "adres"):
            if sub in card and not (isinstance(own, dict) and sub in own):
                names, whole = _uses(card[sub])
                entry["params"] += [n for n in names if n not in entry["params"]]
                if whole:
                    entry["fields"][sub] = names[0]
        fm[which] = entry if entry["params"] else None
    for tkey, which in (("plansze", "slides"), ("plansze_przed", "before"), ("plansze_po", "after")):
        for c in body.get(tkey) or []:
            c = c if isinstance(c, dict) else {}
            tn, tw = _uses(c.get("tekst"))
            cn, cw = _uses(c.get("podpis"))
            fm[which].append({"params": tn + [n for n in cn if n not in tn], "text": tn[0] if tw else "",
                              "caption": cn[0] if cw else ""})
            fm["markup"] += [n for n in tn if n not in fm["markup"]]
    steps, done = body.get("kroki") or [], out.get("kroki") or []
    for ts, es in zip(steps, done):
        if not isinstance(ts, dict):
            continue
        if isinstance(es, dict) and es.get("napis"):
            fm["captions"].append(_uses(ts.get("napis"))[0])
        for key in ("wpisz", "wybierz"):
            if isinstance(ts.get(key), list) and len(ts[key]) == 2:
                fm["form"] += [n for n in _uses(ts[key][1])[0] if n not in fm["form"]]
    return fm


def _param_groups(fields):
    """Grupa parametru dla panelu: "plansze" (plansze i plansza startowa/końcowa), "napisy" (napisy pokazu),
    "formularz" (dane wpisywane na stronie)."""
    groups = {}
    for which in ("intro", "outro"):
        for n in (fields[which] or {}).get("params", []):
            groups.setdefault(n, "plansze")
    for which in ("before", "slides", "after"):
        for c in fields[which]:
            for n in c["params"]:
                groups.setdefault(n, "plansze")
    for names in fields["captions"]:
        for n in names:
            groups.setdefault(n, "napisy")
    for n in fields["form"]:
        groups.setdefault(n, "formularz")
    return groups


def _default_max(name, fields):
    """Najwyższa długość pola bez limitu w szablonie: według miejsca w filmie (tekst planszy, podpis, napis)."""
    for which in ("before", "slides", "after"):
        for c in fields[which]:
            if c["caption"] == name:
                return CAPTION_MAX
            if name in c["params"]:
                return TEXT_MAX
    if any(name in names for names in fields["captions"]):
        return NAPIS_MAX
    return 120


def list_templates(studio):
    """Szablony studia: [{"name", "kind", "kindLabel", "desc", "params", "labels", "error"}], po nazwie."""
    out = []
    try:
        names = sorted(n[:-5] for n in os.listdir(os.path.join(studio, TEMPLATES)) if n.endswith(".json"))
    except OSError:
        return out
    for name in names:
        item = {"name": name, "title": name, "kind": "pokaz", "desc": "", "forOwner": "", "params": [], "labels": {},
                "required": [], "error": ""}
        try:
            tpl = load_template(studio, name)
            labels = tpl.get("etykiety") or {}
            params = template_params(tpl)
            item.update(kind=kind_of(tpl), desc=str(tpl.get("opis") or "")[:400], params=params,
                        forOwner=str(tpl.get("dla_wlasciciela") or "").strip()[:300],
                        title=template_title(tpl, name), required=list(tpl.get("wymagane") or []),
                        labels={k: labels.get(k) or k.replace("_", " ") for k in params})
        except ValueError as e:
            item["error"] = str(e)
        item["kindLabel"] = KINDS[item["kind"]]
        out.append(item)
    return out


def _card(brand, sc, key):
    """Plansza marki dla filmu; None: bez planszy. Obiekt ze scenariusza z własnym tytułem (np. hak posta) bierze
    z marki tylko kolory (podtytuł, adres i czas marki nie doklejają się do haka); bez tytułu uzupełnia planszę
    marki (np. inny czas albo adres)."""
    own = sc.get(key, True)
    if own is False:
        return None
    base = dict(brand.get(key) or {})
    if isinstance(own, dict):
        if not base and not (own.get("tytul") or "").strip():
            return None
        if (own.get("tytul") or "").strip():
            base = {k: v for k, v in base.items() if k in CARD_COLORS}
        base.update(own)
    return base or None


def image_path(folder, name):
    """Obraz planszy: najpierw folder posta, potem studio/obrazy/. None, gdy brak, poza kartą albo z błędną treścią
    (rozmiar ponad IMAGE_MAX, treść niezgodna z rozszerzeniem: ta sama kontrola co logo)."""
    path, err = image_check(folder, name)
    return None if err else path


def image_check(folder, name):
    """(ścieżka obrazu planszy albo None, opis błędu albo "")."""
    if not (isinstance(name, str) and IMAGE_RE.match(name)):
        return None, "nazwa pliku .png albo .jpg"
    studio = studio_dir(folder)
    for path in (os.path.join(folder, name), os.path.join(studio, IMAGES, name)):
        if os.path.isfile(path) and _inside(path, studio):
            bad = media_error(path, "image")
            return (None, bad) if bad else (path, "")
    return None, "brak pliku (folder posta albo studio/%s/)" % IMAGES


def sec_text(value):
    """Sekundy po polsku: 4,2 s."""
    return ("%.1f" % value).rstrip("0").rstrip(".").replace(".", ",") + " s"


def card_time(c, hook=False):
    """Czas planszy objaśnienia: podany (albo CARD_DEFAULT z podpisem, CARD_SHORT bez podpisu), wydłużony do czasu
    czytania (1,2 s + 15 znaków/s tekstu i podpisu). hook: pierwsza plansza filmu (hak): tekst stoi od pierwszej
    klatki (HOOK_BASE zamiast READ_BASE), bez wartości domyślnej; widz czyta tekst, potem podpis, więc liczą się oba
    (dlatego hak lepiej bez podpisu). (czas, potrzebny czas)."""
    text, cap = len(_plain(c.get("tekst") or "")), len(c.get("podpis") or "")
    if hook:
        need = HOOK_BASE + (text + cap) / READ_CPS
        default = 0.0
    else:
        need = READ_BASE + (text + cap) / READ_CPS
        default = CARD_DEFAULT if cap else CARD_SHORT
    given = float(c["czas"]) if _num(c.get("czas")) else default
    return round(min(CARD_TIME[1], max(given, need)), 2), round(need, 1)


def brand_time(card, which, hook=False):
    """Czas planszy startowej albo końcowej: podany (albo CARD_TIMES), wydłużony do czasu czytania tytułu,
    podtytułu i adresu (1,2 s + 15 znaków/s) plus przejście, które zabiera koniec planszy. hook: plansza startowa
    z hakiem posta, stoi od pierwszej klatki (HOOK_BASE zamiast READ_BASE). (czas, potrzebny)."""
    chars = sum(len(str(card.get(k) or "")) for k in ("tytul", "podtytul", "adres"))
    need = (HOOK_BASE if hook else READ_BASE) + chars / READ_CPS + XFADE
    given = float(card["czas"]) if _num(card.get("czas")) else CARD_TIMES[which]
    return round(min(CARD_TIME[1], max(given, need)), 2), round(need, 1)


def is_hook(sc):
    """Plansza startowa z własnym tytułem w scenariuszu (hak posta)."""
    own = sc.get("plansza_startowa") if isinstance(sc, dict) else None
    return isinstance(own, dict) and bool(str(own.get("tytul") or "").strip())


CARD_NAMES = {"plansza_startowa": "Plansza startowa", "plansza_koncowa": "Plansza końcowa"}


def _slow(label, given, sec):
    return "%s trwa %s, za krótko na przeczytanie; panel wydłuży ją do %s." % (label, sec_text(given), sec_text(sec))


def caption_need(text):
    """Czas czytania napisu pokazu (s): 1,2 s + 15 znaków na sekundę."""
    return READ_BASE + len(str(text)) / READ_CPS


def _pokaz_timeline(sc):
    """(szacowana długość nagrania strony po wycięciu czekania, liczba napisów wydłużonych pauzą). Napis stoi do
    następnego napisu; gdy następny przyszedłby przed czasem czytania, nagrywarka czeka (record_page), więc
    szacunek też."""
    total, last, paused = 0.8, None, 0
    for k in sc.get("kroki") or []:
        if k.get("napis"):
            if last is not None and total - last[0] < caption_need(last[1]):
                total, paused = last[0] + caption_need(last[1]), paused + 1
            last = (total, k["napis"])
        total += float(k.get("pauza", 0.6))
        if k.get("wpisz"):
            total += min(1.4, len(str(k["wpisz"][1])) * 0.055) + 0.3
        total += 0.6 if k.get("kliknij") else 0
        total += 0.4 if k.get("przewin") else 0
        total += 0.6 if k.get("wybierz") else 0
        total += 1.3 if k.get("czekaj_na") else 0
    if last is not None and total - last[0] < caption_need(last[1]):
        total, paused = last[0] + caption_need(last[1]), paused + 1
    return total, paused


def _pokaz_estimate(sc):
    """Szacowana długość nagrania strony (s), po wycięciu czekania i z pauzami na przeczytanie napisów."""
    return _pokaz_timeline(sc)[0]


def _slides_info(cards, folder, label, warnings, hook=False):
    """Plansze objaśnienia dla panelu: [{"text", "caption", "seconds", "image"}]; ostrzeżenia o czasie.
    hook: pierwsza plansza jest pierwszym klipem filmu (hak)."""
    out = []
    for i, c in enumerate(cards, 1):
        first = hook and i == 1
        sec, need = card_time(c, hook=first)
        if c.get("obraz"):
            path, bad = image_check(folder, c["obraz"])
            if not path:
                raise ValueError("%s %d: %s obrazu %s (%s)" % (label, i, "brak" if bad.startswith("brak") else "błąd",
                                                            c["obraz"], bad))
        if _num(c.get("czas")) and c["czas"] < need:
            warnings.append(_slow("%s %d" % (label.capitalize(), i), c["czas"], sec))
        if first and sec > HOOK_MAX:
            warnings.append("Pierwsza plansza (hak) trwa %s; widz decyduje w pierwszych 3 s. Skróć hak albo jego "
                            "podpis." % sec_text(sec))
        out.append({"text": _plain(c["tekst"]), "caption": c.get("podpis", ""), "seconds": sec,
                    "image": c.get("obraz", ""), "markup": c["tekst"], "hook": first})
    return out


class ScenarioError(ValueError):
    """Błąd scenariusza z opisem filmu dla panelu (meta: parametry i mapa pól szablonu; param: winny parametr)."""

    def __init__(self, text, meta=None, param=""):
        super().__init__(text)
        self.meta, self.param = meta or {}, param


def _culprit(raw, studio, error):
    """Parametr posta, którego wartość powoduje błąd po podstawieniu: po zamianie go na wartość przykładową
    szablonu błąd znika. "" gdy błąd jest w szablonie (wartości przykładowe też go dają)."""
    given = raw.get("parametry") if isinstance(raw.get("parametry"), dict) else {}
    try:
        defaults = load_template(studio, raw["szablon"]).get("parametry") or {}
    except ValueError:
        return ""
    for k in given:
        if k not in defaults:
            continue
        trial = dict(raw, parametry=dict(given, **{k: defaults[k]}))
        try:
            sc, name = expand(trial, studio)
        except ValueError:
            continue
        errs = validate_scenario(sc, template=True)
        if not errs or errs[0] != error:
            return k
    return ""


_PIL_LOGGED = []


def _log_no_pil():
    """Brak PIL to sprawa instalacji panelu, nie treści filmu: zapis w logu (raz), nie w ostrzeżeniach posta."""
    if not _PIL_LOGGED:
        _PIL_LOGGED.append(1)
        print("film.py: brak biblioteki PIL (pakiet pillow): wyróżnienia *słowo* w planszach wyjdą w kolorze tekstu",
              file=sys.stderr)


def _day_label(day):
    return "%s.%s" % (day[8:10], day[5:7]) if len(day) >= 10 else day


def repeat_warnings(raw, folder, meta):
    """Ostrzeżenia o powtórce względem wcześniejszych postów projektu (posty/<dzień>-…/scenariusz.json): ten sam
    szablon co w poprzednim filmie i te same wartości wymaganych parametrów (treść posta) co w którymś z ostatnich
    filmów z tego szablonu."""
    name = raw.get("szablon") if isinstance(raw, dict) else None
    base, me = os.path.dirname(os.path.abspath(folder)), os.path.basename(os.path.abspath(folder))
    day = me[:10]
    if not (isinstance(name, str) and re.match(r"^\d{4}-\d{2}-\d{2}$", day)):
        return []
    try:
        earlier = sorted((n for n in os.listdir(base) if re.match(r"^\d{4}-\d{2}-\d{2}", n) and n[:10] < day),
                         reverse=True)[:12]
    except OSError:
        return []
    out, prev_seen = [], False
    labels = {p["name"]: p["label"] for p in meta.get("params", [])}
    values = meta.get("values") or {}
    hits = {}
    for n in earlier:
        try:
            other = _load_json(os.path.join(base, n, SCENARIO))
        except (OSError, ValueError):
            continue
        if not isinstance(other, dict):
            continue
        if not prev_seen:
            prev_seen = True
            if other.get("szablon") == name:
                out.append("Poprzedni film (%s) ma ten sam szablon. Na zmianę pokaz i objaśnienie albo inny szablon."
                           % _day_label(n[:10]))
        if other.get("szablon") != name or not isinstance(other.get("parametry"), dict):
            continue
        for k in meta.get("required") or []:
            v = values.get(k, "").strip().lower()
            if k not in hits and v and str(other["parametry"].get(k, "")).strip().lower() == v:
                hits[k] = n[:10]
    for k, d in hits.items():
        out.append("„%s” taki sam jak w filmie z %s. Podaj inną treść, żeby filmy się nie powtarzały."
                   % (labels.get(k, k), _day_label(d)))
    return out


def prepare_raw(raw, folder):
    """(scenariusz rozwinięty, marka, opis) dla scenariusza raw posta w folder. ValueError z opisem po polsku
    (ScenarioError, gdy po podstawieniu szablonu: z parametrami dla panelu i nazwą winnego parametru)."""
    studio = studio_dir(folder)
    meta = {}
    sc, name = expand(raw, studio, meta)
    errors = validate_scenario(sc, template=bool(name))
    if errors:
        if not name:
            raise ValueError(errors[0])
        culprit = _culprit(raw, studio, errors[0])
        labels = {p["name"]: p["label"] for p in meta.get("params", [])}
        if culprit:
            raise ScenarioError("parametr „%s”, pole „%s”: %s" % (culprit, labels.get(culprit, culprit), errors[0]),
                                meta, culprit)
        raise ScenarioError("szablon %s: %s" % (name, errors[0]), meta)
    brand, berr, _ = load_brand(studio)
    if berr:
        raise ValueError("%s/%s: %s" % (STUDIO, BRAND, berr[0]))
    serr = site_errors(sc, brand)
    if serr:
        raise ValueError(serr[0])
    kind = kind_of(sc)
    intro, outro = _card(brand, sc, "plansza_startowa"), _card(brand, sc, "plansza_koncowa")
    hook = is_hook(sc)
    info = {"kind": kind, "template": name, "templateTitle": meta.get("title", ""),
            "templateDesc": meta.get("desc", ""), "templateOwner": meta.get("owner", ""),
            "params": meta.get("params", []), "fields": meta.get("fields"),
            "intro": bool(intro), "outro": bool(outro), "warnings": [], "music": bool(brand.get("muzyka")),
            "editable": [], "before": [], "after": []}
    stock, total = meta.get("stock") or (0, 0)
    if meta.get("same"):
        info["warnings"].append("Film ma same wartości z szablonu (jak przykład w studiu). Podaj treść tego posta.")
    elif total >= 3 and stock * 2 > total:
        info["warnings"].append("%d z %d plansz ma przykładowy tekst z szablonu. Podaj treść tego posta, inaczej "
                                "filmy będą się powtarzać." % (stock, total))
    if name and folder:
        info["warnings"] += repeat_warnings(raw, folder, meta)
    for key, which, card in (("introCard", "plansza_startowa", intro), ("outroCard", "plansza_koncowa", outro)):
        if not card:
            info[key] = None
            continue
        own_hook = hook and which == "plansza_startowa"
        sec, need = brand_time(card, which, hook=own_hook)
        if _num(card.get("czas")) and card["czas"] < need:
            info["warnings"].append(_slow(CARD_NAMES[which], card["czas"], sec))
        if own_hook and sec > HOOK_MAX + XFADE:
            info["warnings"].append("Hak na początku trwa %s; widz decyduje w pierwszych 3 s. Skróć go do ok. "
                                    "40 znaków." % sec_text(sec))
        info[key] = {"title": card.get("tytul", ""), "subtitle": card.get("podtytul", ""),
                     "address": card.get("adres", ""), "seconds": sec, "hook": own_hook}
    parts = [c["seconds"] for c in (info["introCard"], info["outroCard"]) if c]
    if kind == "objasnienie":
        info["cards"] = len(sc["plansze"])
        info["slides"] = _slides_info(sc["plansze"], folder, "plansza", info["warnings"], hook=not intro)
        parts += [c["seconds"] for c in info["slides"]]
        if not name:          # plansze pisane w scenariuszu: tekst i podpis do zmiany w panelu
            info["editable"] = ["slides"]
    else:
        info["steps"] = len(sc.get("kroki") or [])
        info["captions"] = [str(k["napis"]) for k in sc.get("kroki") or [] if k.get("napis")]
        info["sequence"] = _sequence(sc)
        info["before"] = _slides_info(sc.get("plansze_przed") or [], folder, "plansza przed pokazem", info["warnings"],
                                      hook=not intro)
        info["after"] = _slides_info(sc.get("plansze_po") or [], folder, "plansza po pokazie", info["warnings"])
        parts += [c["seconds"] for c in info["before"] + info["after"]]
        est, paused = _pokaz_timeline(sc)
        info["captionPauses"] = paused
        if est > POKAZ_MAX:
            info["warnings"].append("Pokaz potrwa około %d s; krótszy film lepiej się ogląda." % est)
        parts.append(est)
    if name:
        info["editable"] = ["params"]
    marked = [c for key in ("plansze", "plansze_przed", "plansze_po") for c in sc.get(key) or []
              if isinstance(c, dict) and "*" in str(c.get("tekst") or "")]
    if marked and _PILFont is None:
        _log_no_pil()
    info["seconds"] = round(sum(parts) - XFADE * max(0, len(parts) - 1), 1)
    if kind == "objasnienie" and info["seconds"] > OBJ_MAX:
        info["warnings"].append("Objaśnienie potrwa ok. %d s; na Reels lepiej do %d s (mniej plansz albo krótsze "
                                "teksty)." % (info["seconds"], OBJ_MAX))
    if not info["music"]:
        info["warnings"].append("Film bez muzyki: Reels i TikTok słabiej pokazują ciche filmy. Podkład dodasz w "
                                "Marketing → Studio filmów → „Zmień plansze i wygląd”.")
    return sc, brand, info


def _sequence(sc):
    """Kroki pokazu po kolei dla panelu: [{"kind": "napis"|"wpisz"|"wybierz"|"kliknij", "text"}] (bez selektorów)."""
    out = []
    for k in sc.get("kroki") or []:
        if k.get("napis"):
            out.append({"kind": "napis", "text": str(k["napis"])})
        for key in ("wpisz", "wybierz"):
            if k.get(key):
                out.append({"kind": key, "text": str(k[key][1])})
    return out


def prepare(folder):
    """(scenariusz rozwinięty, marka, opis). ValueError z opisem po polsku, gdy scenariusz albo marka są błędne."""
    try:
        raw = _load_json(os.path.join(folder, SCENARIO))
    except OSError:
        raise ValueError("brak %s" % SCENARIO)
    except ValueError as e:
        raise ValueError("%s: niepoprawny JSON (%s)" % (SCENARIO, str(e)[:80]))
    return prepare_raw(raw, folder)


def apply_changes(folder, params=None, slides=None):
    """Zmiana treści filmu z panelu bez agenta: parametry szablonu ({nazwa: wartość}) albo tekst i podpis plansz
    objaśnienia pisanego w scenariuszu ([{"n": numer od 1, "tekst", "podpis"}]). Zapis scenariusz.json tylko, gdy
    scenariusz po zmianie przechodzi te same kontrole co nagranie. Zwraca opis filmu; ValueError z opisem."""
    path = os.path.join(folder, SCENARIO)
    try:
        stamp = os.stat(path).st_mtime_ns
        raw = _load_json(path)
    except OSError:
        raise ValueError("brak %s" % SCENARIO)
    except ValueError as e:
        raise ValueError("%s: niepoprawny JSON (%s)" % (SCENARIO, str(e)[:80]))
    if not isinstance(raw, dict):
        raise ValueError("scenariusz: oczekiwany obiekt JSON")
    if params:
        if "szablon" not in raw:
            raise ValueError("ten film nie jest z szablonu; zmień treść plansz albo poproś agenta")
        if not isinstance(params, dict):
            raise ValueError("parametry: obiekt {nazwa: wartość}")
        cur = dict(raw.get("parametry") or {})
        for k, v in params.items():
            if not isinstance(v, (str, int, float)) or isinstance(v, bool):
                raise ValueError("parametr „%s”: tekst" % k)
            cur[k] = v.strip() if isinstance(v, str) else v
        try:                         # liczba z pola formularza zostaje liczbą (np. czas planszy z parametru)
            cur = coerce_params(load_template(studio_dir(folder), raw.get("szablon")), cur)
        except ValueError:
            pass                     # brak szablonu: zgłosi prepare_raw niżej
        raw["parametry"] = cur
    if slides:
        cards = raw.get("plansze")
        if "szablon" in raw or raw.get("typ") != "objasnienie" or not isinstance(cards, list):
            raise ValueError("plansze zmienia się tu tylko w objaśnieniu bez szablonu")
        for ch in slides if isinstance(slides, list) else []:
            n = ch.get("n") if isinstance(ch, dict) else None
            if not (isinstance(n, int) and 1 <= n <= len(cards) and isinstance(cards[n - 1], dict)):
                raise ValueError("plansza %s: nie ma takiej planszy" % n)
            for key in ("tekst", "podpis"):
                if key in ch:
                    if not isinstance(ch[key], str):
                        raise ValueError("plansza %d: %s to tekst" % (n, key))
                    if key == "podpis" and not ch[key].strip():
                        cards[n - 1].pop("podpis", None)
                    else:
                        cards[n - 1][key] = ch[key].strip()
    _sc, _brand, info = prepare_raw(raw, folder)
    fd, tmp = tempfile.mkstemp(dir=folder, prefix=".scenariusz-", suffix=".tmp")   # własny plik: bez wyścigu
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False, indent=1)
            f.write("\n")
        try:
            now = os.stat(path).st_mtime_ns
        except OSError:
            now = None
        if now != stamp:             # agent zapisał scenariusz w międzyczasie: nie nadpisujemy jego zmiany
            raise ScenarioChanged("scenariusz zmienił się w tym czasie; odśwież i spróbuj jeszcze raz")
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return info


class ScenarioChanged(Exception):
    """Scenariusz zmienił się między odczytem a zapisem zmiany z panelu (np. zapisał go agent)."""


ERROR_HINTS = (("wymagany w szablonie", "Brakuje treści tego posta (szablon wymaga jej w scenariuszu)."),
               ("brak parametru", "W scenariuszu brakuje danych do szablonu."),
               ("parametr „", "Jedna z wartości w filmie jest niepoprawna."),
               ("błąd obrazu", "Obraz do planszy jest za duży albo uszkodzony."),
               ("bez znaków sterujących", "W tekście filmu jest nowy wiersz albo tabulator."),
               ("nie ma parametru", "Scenariusz podaje dane, których szablon nie zna."),
               ("niepodstawiony znacznik", "W filmie zostałby znacznik {{…}} zamiast tekstu."),
               ("url:", "Adres strony w filmie jest niedozwolony."),
               ("logowanie:", "Adres logowania w filmie jest niedozwolony."),
               ("studio/marka.json", "Błąd w ustawieniach marki projektu (studio/marka.json)."),
               ("brak szablonu", "Scenariusz wskazuje szablon, którego nie ma w studiu."),
               ("brak obrazu", "Brakuje obrazu do planszy."),
               ("szablon ", "Błąd w szablonie studia."))


def error_hint(error):
    """Krótki opis błędu scenariusza dla właściciela (szczegół techniczny osobno)."""
    m = re.match(r"parametr „[^”]+”, pole „([^”]+)”: ", error)
    if m:                            # błąd w wartości jednego pola posta (nie w szablonie)
        what = error[m.end():].split(": ")[-1].replace("wyróżnienie *słowo* bez drugiej gwiazdki",
                                                         "wyróżnione słowo bez zamknięcia")
        return "Popraw pole „%s” (%s)." % (m.group(1), what)
    for key, text in ERROR_HINTS:
        if key in error:
            return text
    return "Błąd w scenariuszu filmu."


def describe(folder):
    """Rodzaj filmu, szablon i treść dla panelu; nigdy nie rzuca: {"kind", "kindLabel", "kindHelp", "template",
    "templateDesc", "params", "slides", "captions", "introCard", "outroCard", "seconds", "warnings", "intro", "outro",
    "error", "errorHint"}."""
    out = {"kind": "pokaz", "template": "", "templateTitle": "", "templateDesc": "", "params": [], "intro": False,
           "outro": False, "introCard": None, "outroCard": None, "warnings": [], "seconds": 0, "error": "",
           "errorHint": "", "editable": [], "music": False, "templateOwner": "", "fields": None, "errorParam": ""}
    try:
        _sc, _brand, info = prepare(folder)
        out.update(info)
    except ValueError as e:
        out["error"] = str(e)[:300]
        out["errorHint"] = error_hint(out["error"])
        if isinstance(e, ScenarioError) and e.meta.get("params"):   # błędne pole posta: do poprawy wprost w panelu
            out.update(params=e.meta["params"], fields=e.meta.get("fields"), editable=["params"],
                       errorParam=e.param, templateTitle=e.meta.get("title", ""),
                       templateDesc=e.meta.get("desc", ""), templateOwner=e.meta.get("owner", ""))
        try:
            raw = _load_json(os.path.join(folder, SCENARIO))
            out["template"] = str(raw.get("szablon") or "") if isinstance(raw, dict) else ""
            out["kind"] = kind_of(raw)
            if out["template"]:
                tpl = load_template(studio_dir(folder), out["template"])
                out["kind"], out["templateTitle"] = kind_of(tpl), template_title(tpl, out["template"])
        except (OSError, ValueError, AttributeError):
            pass
    out["kindLabel"] = KINDS.get(out["kind"], out["kind"])
    out["kindHelp"] = KIND_HELP.get(out["kind"], "")
    return out


def _version_paths(folder):
    """(pliki posta, pliki studia), od których zależy film: scenariusz i obrazy z folderu posta; szablon, marka,
    muzyka, logo i obrazy ze studio/obrazy/."""
    post, studio_files = [os.path.join(folder, SCENARIO)], []
    studio = studio_dir(folder)
    studio_files.append(os.path.join(studio, BRAND))
    try:
        raw = _load_json(os.path.join(folder, SCENARIO))
    except (OSError, ValueError):
        raw = None
    if isinstance(raw, dict):
        name = raw.get("szablon")
        if isinstance(name, str) and NAME_RE.match(name):
            studio_files.append(os.path.join(studio, TEMPLATES, name + ".json"))
        try:
            sc = expand(raw, studio)[0]
        except ValueError:
            sc = raw
        cards = []
        for key in ("plansze", "plansze_przed", "plansze_po"):
            part = sc.get(key) if isinstance(sc, dict) else None
            cards += part if isinstance(part, list) else []
        for c in cards:
            if isinstance(c, dict) and isinstance(c.get("obraz"), str) and IMAGE_RE.match(c["obraz"]):
                p = image_path(folder, c["obraz"])
                if p:
                    (post if os.path.dirname(p) == os.path.abspath(folder) else studio_files).append(p)
    try:
        brand = _load_json(os.path.join(studio, BRAND))
    except (OSError, ValueError):
        brand = None
    if isinstance(brand, dict):
        if isinstance(brand.get("muzyka"), str) and AUDIO_RE.match(brand["muzyka"]):
            studio_files.append(os.path.join(studio, brand["muzyka"]))
        if isinstance(brand.get("logo"), str) and IMAGE_RE.match(brand["logo"]):
            studio_files.append(os.path.join(studio, brand["logo"]))
    return post, studio_files


def _mtimes(paths):
    out = []
    for p in paths:
        try:
            out.append(os.path.getmtime(p))
        except OSError:
            pass
    return out


def scenario_version(folder):
    """Najnowszy mtime plików tego posta (scenariusz, obrazy z folderu posta): zmiana treści filmu przez post,
    nie przez studio. None, gdy nie ma scenariusza."""
    times = _mtimes(_version_paths(folder)[0]) if os.path.isfile(os.path.join(folder, SCENARIO)) else []
    return max(times) if times else None


def version(folder):
    """Wersja filmu do ponownego nagrania: najnowszy mtime scenariusza, użytego szablonu, marki, muzyki, logo
    i obrazów. None, gdy nie ma scenariusza."""
    if not os.path.isfile(os.path.join(folder, SCENARIO)):
        return None
    post, studio_files = _version_paths(folder)
    times = _mtimes(post) + _mtimes(studio_files)
    return max(times) if times else None


# ---------- typografia: czcionki, pomiar, łamanie wierszy po polsku ----------
GLUE = {"a", "i", "o", "u", "w", "z", "do", "na", "za", "po", "od", "ze", "we", "ku"}   # nie zostają na końcu wiersza
NBSP = " "


class Font:
    """Czcionka do drawtext: plik, rozmiar i pogrubienie obrysem (gdy jest tylko zmienny krój bez danej grubości)."""

    def __init__(self, path, size, bold=0.0):
        self.path, self.size, self.border = path, int(size), int(round(bold * size))

    def at(self, size):
        f = Font(self.path, size)
        f.border = int(round(self.border * size / max(1, self.size)))
        return f

    def width(self, text):
        text = text.replace(NBSP, " ").replace("*", "")
        pil = _pil(self.path, self.size)
        if pil is not None:
            try:
                return pil.getlength(text) + 2 * self.border
            except Exception:  # noqa: BLE001
                pass
        return sum(_char_em(ch) for ch in text) * self.size * 1.03 + 2 * self.border

    @property
    def exact(self):
        return _pil(self.path, self.size) is not None


_PIL_CACHE = {}


def _pil(path, size):
    if _PILFont is None or not path:
        return None
    key = (path, size)
    if key not in _PIL_CACHE:
        try:
            _PIL_CACHE[key] = _PILFont.truetype(path, size)
        except Exception:  # noqa: BLE001
            _PIL_CACHE[key] = None
    return _PIL_CACHE[key]


def _char_em(ch):
    """Szerokość znaku w em (zachowawczo, gdy nie ma PIL)."""
    if ch == " ":
        return 0.28
    if ch in "ijlI.,:;!|'’`·":
        return 0.28
    if ch in "ftr()[]-–/\"„”":
        return 0.38
    if ch in "mwMW@%":
        return 0.92
    if ch.isupper() or ch.isdigit():
        return 0.7
    return 0.57


def _default_weight(path):
    pil = _pil(path, 40)
    if pil is not None:
        try:
            for ax in pil.get_variation_axes():
                name = ax.get("name", b"")
                name = name.decode("latin-1") if isinstance(name, bytes) else str(name)
                if "weight" in name.lower():
                    return int(ax.get("default", 400))
        except Exception:  # noqa: BLE001
            pass
    return 400


def font_file(name, fallback=FONT):
    """Plik czcionki o nazwie z marki (np. „Fraunces” albo „Inter:Bold”) z katalogów czcionek; brak: fallback."""
    return font_spec(name, fallback)[0]


_FONT_CACHE = {}


def font_spec(name, fallback=FONT):
    """Jak _font_spec, z pamięcią podręczną (katalogi czcionek przeszukiwane raz na nazwę)."""
    key = (name or "", fallback)
    if key not in _FONT_CACHE:
        _FONT_CACHE[key] = _font_spec(name, fallback)
    return _FONT_CACHE[key]


def _font_spec(name, fallback=FONT):
    """(plik, pogrubienie obrysem w em). „Inter:Bold”: statyczny plik Inter-Bold, gdy jest; inaczej plik rodziny
    z obrysem w kolorze tekstu (zmienny krój bez wybranej grubości w drawtext)."""
    if not name:
        return fallback, 0.0
    family, _, weight = name.partition(":")
    key = re.sub(r"[^a-z0-9]", "", family.lower())
    if not key:
        return fallback, 0.0
    hits = {}
    for d in FONT_DIRS:
        for root, _dirs, files in os.walk(os.path.expanduser(d)):
            for f in files:
                stem, ext = os.path.splitext(f)
                if ext.lower() in (".ttf", ".otf"):
                    k = re.sub(r"[^a-z0-9]", "", stem.lower())
                    if k.startswith(key):
                        hits.setdefault(k, os.path.join(root, f))
    if not hits:
        return fallback, 0.0
    if weight:
        exact = key + weight.lower()
        for k in sorted(hits, key=len):
            if k == exact or k == exact + "regular" or (k.startswith(exact) and "italic" not in k):
                return hits[k], 0.0
    base = min(hits, key=lambda k: (len(k), k))
    path = hits[base]
    if not weight:
        return path, 0.0
    extra = WEIGHTS[weight] - _default_weight(path)
    return path, max(0.0, min(0.035, extra / 100 * 0.007))


def _tokens(text):
    """Słowa do łamania: jednoliterowe spójniki i krótkie przyimki sklejone z następnym słowem, myślnik
    z poprzednim (twarda spacja)."""
    words = text.split()
    out = []
    for w in words:
        if out and w in ("–", "—", "-"):
            out[-1] += NBSP + w
        else:
            out.append(w)
    merged, carry = [], ""
    for n, w in enumerate(out):
        bare = w.strip("*„\"(").lower()
        if bare in GLUE and n < len(out) - 1:
            carry += w + NBSP
            continue
        merged.append(carry + w)
        carry = ""
    if carry:
        merged.append(carry.rstrip(NBSP))
    return merged


VOWELS = set("aąeęioóuyAĄEĘIOÓUY")
NO_START = set("ńśćźŃŚĆŹ")        # po polsku nie zaczynają sylaby (przed samogłoską pisze się ni, si, ci, zi)
DIGRAPHS = {"cz", "sz", "rz", "ch", "dz", "dź", "dż"}


def _cut_ok(word, i):
    """Czy wolno podzielić słowo przed literą i: druga część nie zaczyna się od ń/ś/ć/ź ani od samogłoski
    (łącznik po samogłosce), a dwuznak (cz, sz, rz, ch, dz, dź, dż) zostaje w jednej części."""
    return word[i] not in NO_START and word[i - 1:i + 1].lower() not in DIGRAPHS


def _split_long(token, font, maxw):
    """Słowo szersze niż wiersz: podział z łącznikiem po samogłosce (sylaba), najwyżej tyle liter, ile się mieści,
    co najmniej 3 litery w każdej części, bez rozdzielania dwuznaków i bez części od ń/ś/ć/ź; bez takiego miejsca
    w zasięgu: podział w dowolnym dozwolonym miejscu."""
    parts, rest = [], token
    while font.width(rest) > maxw and len(rest) > 6:
        fits = [i for i in range(3, len(rest) - 2) if font.width(rest[:i] + "-") <= maxw]
        if not fits:
            break
        ok = [i for i in fits if _cut_ok(rest, i)] or fits
        syl = [i for i in ok if rest[i - 1] in VOWELS and rest[i] not in VOWELS]
        cut = max(syl) if syl and max(syl) >= max(fits) * 0.6 else max(ok)
        parts.append(rest[:cut] + "-")
        rest = rest[cut:]
    return parts + [rest]


def wrap(text, font, maxw, hyphen=False):
    """Wiersze o podobnej długości (najmniejsza liczba wierszy, potem najmniejsza najdłuższa linia).
    None, gdy słowo nie mieści się w wierszu (i hyphen=False)."""
    toks = _tokens(text)
    if hyphen:
        toks = [p for t in toks for p in (_split_long(t, font, maxw) if font.width(t) > maxw else [t])]
    if not toks:
        return []
    if any(font.width(t) > maxw for t in toks):
        return None
    n = len(toks)
    joined = lambda i, j: " ".join(toks[i:j])  # noqa: E731
    w = {}
    for i in range(n):
        for j in range(i + 1, n + 1):
            w[i, j] = font.width(joined(i, j))
    lines, i = 0, 0                     # zachłannie: najmniejsza liczba wierszy
    while i < n:
        j = i + 1
        while j < n and w[i, j + 1] <= maxw:
            j += 1
        lines, i = lines + 1, j
    best = {(0, 0): (0.0, 0.0, None)}   # (wiersze, słowa) -> (najdłuższa, suma kwadratów luzu, poprzednik)
    for k in range(1, lines + 1):
        for j in range(1, n + 1):
            cand = None
            for i in range(0, j):
                prev = best.get((k - 1, i))
                if prev is None or w[i, j] > maxw:
                    continue
                score = (max(prev[0], w[i, j]), prev[1] + (maxw - w[i, j]) ** 2, i)
                if cand is None or score[:2] < cand[:2]:
                    cand = score
            if cand:
                best[k, j] = cand
    out, j = [], n
    for k in range(lines, 0, -1):
        i = best[k, j][2]
        out.append(joined(i, j))
        j = i
    return [ln.replace(NBSP, " ") for ln in reversed(out)]


def fit(text, font, maxw, sizes, max_lines):
    """(czcionka, wiersze): największy rozmiar z sizes, przy którym tekst mieści się w max_lines wierszach."""
    for size in sizes:
        f = font.at(size)
        lines = wrap(text, f, maxw)
        if lines is not None and len(lines) <= max_lines:
            return f, lines
    for size in sizes:                  # bardzo długie słowo: najpierw łącznik na większym rozmiarze
        f = font.at(size)
        lines = wrap(text, f, maxw, hyphen=True)
        if lines is not None and len(lines) <= max_lines:
            return f, lines
    f = font.at(sizes[-1])
    return f, wrap(text, f, maxw, hyphen=True)


def _plain(text):
    return text.replace("*", "")


# ---------- montaż ffmpeg: plansze, napisy, sklejanie ----------
def _ff(path):
    """Wartość opcji filtra ffmpeg: ucieczka na poziomie opcji (\\ : ') i grafu filtrów (\\ ' [ ] , ;)."""
    level1 = re.sub(r"([\\:'])", r"\\\1", path)
    return re.sub(r"([\\'\[\],;])", r"\\\1", level1)


def _hex6(value):
    h = value.lstrip("#")
    return ("".join(c * 2 for c in h) if len(h) == 3 else h).lower()


def _rgb(value):
    h = _hex6(value)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _col(value, alpha=None):
    return "0x" + _hex6(value) + ("@%.2f" % alpha if alpha is not None else "")


def _lum(value):
    ch = [c / 255 for c in _rgb(value)]
    ch = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in ch]
    return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]


def contrast(a, b):
    """Kontrast WCAG dwóch kolorów #rrggbb (1–21)."""
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def readable(bg, *colors):
    """Pierwszy kolor z kontrastem co najmniej 3:1 do tła; gdy żaden: ostatni."""
    for c in colors:
        if c and contrast(c, bg) >= 3:
            return c
    return colors[-1]


class _Texts:
    """Pliki tekstów dla drawtext (textfile=: bez ucieczek znaków w tekście)."""

    def __init__(self, work, prefix="t"):
        self.work, self.prefix, self.n = work, prefix, 0

    def __call__(self, text):
        self.n += 1
        path = os.path.join(self.work, "%s%04d.txt" % (self.prefix, self.n))
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path


def _draw(texts, text, font, color, x, base, start=None, extra="", drift=None):
    """drawtext z linią bazową w base (równe odstępy wierszy niezależnie od ogonków i akcentów).
    start: wejście od chwili start (pojawienie się i wjazd 40 px z dołu w 0,45 s); drift (s, px): powolny ruch w górę."""
    f = "drawtext=expansion=none:fontfile=%s:textfile=%s:fontsize=%d:fontcolor=%s:x=%s" % (
        _ff(font.path), _ff(texts(text)), font.size, color, x)
    if font.border:
        f += ":borderw=%d:bordercolor=%s" % (font.border, color)
    y = "%d-max_glyph_a" % base
    if drift:
        y += "-%d*t/%.2f" % (drift[1], drift[0])
    if start is None:
        return f + ":y='%s'%s" % (y, extra)
    p = "clip((t-%.2f)/0.45,0,1)" % start
    return f + ":y='%s+40*pow(1-%s,2)':alpha='%s'%s" % (y, p, p, extra)


def _draw_line(texts, line, font, color, accent, x, base, start=None, drift=None, state=False):
    """Wiersz z wyróżnieniem *słowo* w kolorze akcentu. Zwraca (filtry, czy wyróżnienie trwa na końcu wiersza).
    Bez dokładnego pomiaru (PIL) wiersz bez wyróżnienia."""
    segs, hl = [], state
    for k, part in enumerate(line.split("*")):
        if k:
            hl = not hl
        if part:
            segs.append((part, hl))
    if not any(h for _, h in segs) or not font.exact or not str(x).isdigit():
        return [_draw(texts, _plain(line), font, color, x, base, start, drift=drift)], hl
    out, pos = [], int(x)
    for part, h in segs:
        out.append(_draw(texts, part, font, accent if h else color, str(int(round(pos))), base, start, drift=drift))
        pos += font.width(part) - (2 * font.border if font.border else 0)
    return out, hl


def _box_fade(x, top, width, height, color_hex, alpha, at, stop, steps=12, dur=0.45):
    """Pudełko napisu z wejściem w krokach krycia (drawbox nie ma krycia zależnego od czasu): kolejne pudełka
    o rosnącym kryciu w rozłącznych odcinkach czasu, ostatnie do końca."""
    out = []
    for k in range(steps):
        a = alpha * (k + 1) / steps
        t0 = at + dur * k / steps
        t1 = at + dur * (k + 1) / steps if k + 1 < steps else stop
        out.append("drawbox=x=%s:y=%d:w=%d:h=%d:color=%s:t=fill:enable='between(t,%.3f,%.3f)'"
                   % (x, top, width, height, _col(color_hex, a), t0, t1 - (0.001 if k + 1 < steps else 0)))
    return out


def caption_filters(texts, captions, end, style, start_at=None, align="center"):
    """Napisy: [(od, tekst)], każdy do następnego; jedno pudełko pod wszystkimi wierszami, dół pudełka nad dolną
    strefą bezpieczną. style: marka["napisy"] + "font" (Font). start_at: wejście (pudełko i tekst płynnie od tej
    chwili, plansze objaśnienia); align "left": pudełko i tekst przy lewym marginesie (jak tekst planszy)."""
    out = []
    font = style["font"]
    size = int(style.get("rozmiar", 56))
    box_hex, alpha = style.get("tlo", "#2b1d12"), float(style.get("krycie", 0.85))
    box = _col(box_hex, alpha)
    color = _col(style.get("kolor", "#ffffff"))
    sizes = list(range(size, max(30, int(size * 0.7)) - 1, -2))
    bottom = SIZE[1] - SAFE_BOTTOM
    for n, (at, text) in enumerate(captions):
        stop = captions[n + 1][0] if n + 1 < len(captions) else end + 1
        f, lines = fit(text, font.at(size), TEXT_W - 60, sizes, 3)
        if not lines:
            continue
        line_h = int(f.size * 1.32)
        pad_y, pad_x = int(f.size * 0.42), int(f.size * 0.6)
        width = min(SIZE[0] - 2 * 40, int(max(f.width(ln) for ln in lines)) + 2 * pad_x)
        height = len(lines) * line_h + 2 * pad_y - int(f.size * 0.3)
        top = bottom - height
        bx = str(MARGIN) if align == "left" else "(iw-%d)/2" % width
        tx = str(MARGIN + pad_x) if align == "left" else "(w-text_w)/2"
        begin = at if start_at is None else start_at
        on = "between(t,%.2f,%.2f)" % (begin, stop)
        if start_at is None:
            out.append("drawbox=x=%s:y=%d:w=%d:h=%d:color=%s:t=fill:enable='%s'" % (bx, top, width, height, box, on))
        else:
            out += _box_fade(bx, top, width, height, box_hex, alpha, begin, stop)
        for j, line in enumerate(lines):
            base = top + pad_y + int(f.size * 0.78) + j * line_h
            out.append(_draw(texts, line, f, color, tx, base, start_at, ":enable='%s'" % on))
    return out


def caption_style(brand):
    st = dict(DEFAULT_BRAND["napisy"], **(brand.get("napisy") or {}))
    path, bold = font_spec((brand.get("czcionki") or {}).get("napisy"))
    st["font"] = Font(path, int(st.get("rozmiar", 56)), bold)
    return st


def _font(brand, role, size):
    path, bold = font_spec((brand.get("czcionki") or {}).get(role))
    return Font(path, size, bold)


def _encode(args, out, final=False, seconds=None):
    """Kodowanie H.264 30 kl./s; klipy pośrednie szybko i prawie bezstratnie, film końcowy z dźwiękiem AAC."""
    codec = ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", "30",
             "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart"] if final else \
        ["-an", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "12", "-pix_fmt", "yuv420p", "-r", "30"]
    if seconds:
        codec += ["-t", "%.3f" % seconds]
    r = subprocess.run(["ffmpeg", "-y", "-v", "error"] + args + codec + [out], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("montaż: " + (r.stderr.strip().splitlines() or ["ffmpeg"])[-1][:200])
    return out


def _clip(out, bg, dur, draws, image=None, bar=None, logo=None, first=False, fade_out=True):
    """Plansza: tło w kolorze, opcjonalny obraz (image: (plik, y, maks. wysokość)), logo (logo: (plik, x, y,
    maks. wysokość), x="c" = środek), teksty, pasek postępu (bar: (kolor, y)) przez cały czas planszy.
    first: pierwszy klip filmu, obraz i logo widoczne od pierwszej klatki (miniatura). fade_out: treść gaśnie do
    koloru tła tuż przed przejściem do następnej planszy (FADE_OUT, kończy się w dur − XFADE), więc w przenikaniu
    jest samo tło i nie nakładają się dwa teksty; ostatni klip filmu bez tego."""
    args = ["-f", "lavfi", "-i", "color=c=%s:s=%dx%d:r=30:d=%.2f" % (bg, SIZE[0], SIZE[1], dur)]
    graph, cur = [], "[0:v]"
    n = 1
    fade = "" if first else ",fade=t=in:st=0.1:d=0.4:alpha=1"
    if image:
        path, y, maxh = image
        args += media_input(path, dur)
        graph.append("[%d:v]scale=w=%d:h=%d:force_original_aspect_ratio=decrease,format=rgba%s[img]"
                     % (n, TEXT_W, maxh, fade))
        graph.append("%s[img]overlay=x=(W-w)/2:y=%d+(%d-h)/2:shortest=1[b%d]" % (cur, y, maxh, n))
        cur, n = "[b%d]" % n, n + 1
    if logo:
        path, x, y, maxh = logo
        args += media_input(path, dur)
        graph.append("[%d:v]scale=w=%d:h=%d:force_original_aspect_ratio=decrease,format=rgba%s[logo]"
                     % (n, TEXT_W, maxh, fade))
        graph.append("%s[logo]overlay=x=%s:y=%d:shortest=1[b%d]" % (cur, "(W-w)/2" if x == "c" else str(x), y, n))
        cur, n = "[b%d]" % n, n + 1
    graph.append("%s%s[txt]" % (cur, ",".join(draws) if draws else "null"))
    cur = "[txt]"
    if bar:
        color, y = bar
        args += ["-f", "lavfi", "-i", "color=c=%s:s=%dx8:r=30:d=%.2f" % (color, SIZE[0], dur)]
        graph.append("%s[%d:v]overlay=x='-w+w*t/%.2f':y=%d:shortest=1[bar]" % (cur, n, dur, y))
        cur = "[bar]"
    if fade_out and dur > XFADE + FADE_OUT + 0.5:
        graph.append("%sfade=t=out:st=%.2f:d=%.2f:color=%s[faded]" % (cur, dur - XFADE - FADE_OUT, FADE_OUT, bg))
        cur = "[faded]"
    graph.append("%sformat=yuv420p[out]" % cur)
    _encode(args + ["-filter_complex", ";".join(graph), "-map", "[out]"], out, seconds=dur)
    return out, dur


def logo_path(brand, studio):
    """Plik logo marki (studio/<logo>), gdy jest i ma poprawną treść; inaczej None."""
    name = brand.get("logo")
    if not (studio and isinstance(name, str) and IMAGE_RE.match(name)):
        return None
    path = os.path.join(studio, name)
    return path if os.path.isfile(path) and _inside(path, studio) and not media_error(path, "image") else None


def brand_card(brand, card, which, work, texts, name, first=False, studio=None, hook=False):
    """Plansza startowa albo końcowa (kolory odwrócone: tło = kolor tekstu marki). Logo (gdy jest), tytuł, podtytuł,
    kreska akcentu i adres w jednym bloku na środku kadru (poza strefami zasłanianymi przez interfejs aplikacji).
    Podtytuł i adres w kolorze tekstu planszy (na startowej co najmniej 52 px, na końcowej, gdzie są wezwaniem do
    działania, co najmniej rozmiar napisów); akcent tylko na kresce. first: tekst stoi od pierwszej klatki
    (miniatura, hak). hook: plansza startowa z hakiem posta (krótszy czas, brand_time)."""
    kol = brand["kolory"]
    bg_hex, fg_hex = card.get("tlo") or kol["tekst"], card.get("kolor") or kol["tlo"]
    bg, fg = _col(bg_hex), _col(fg_hex)
    accent = _col(readable(bg_hex, kol.get("akcent2"), kol["akcent"], fg_hex))
    outro = which == "plansza_koncowa"
    dur = brand_time(card, which, hook=hook)[0]
    logo = logo_path(brand, studio)
    logo_h = 180 if logo else 0
    title_f, title = fit(card.get("tytul", ""), _font(brand, "tytul", 96), TEXT_W, list(range(96, 59, -4)), 3)
    sub_sizes = list(range(62, 55, -2)) if outro else list(range(56, 51, -2))
    sub_f, sub = fit(card.get("podtytul", ""), _font(brand, "tekst", sub_sizes[0]), TEXT_W, sub_sizes, 3 if outro else 2) \
        if card.get("podtytul") else (None, [])
    addr_f = _font(brand, "tytul" if outro else "tekst", 66 if outro else 52)
    t_h, s_h = int(title_f.size * 1.16), int(sub_f.size * 1.3) if sub_f else 0
    rule = bool(sub) and not outro            # plansza startowa: kreska akcentu między tytułem a podtytułem
    block = (logo_h + 60 if logo else 0) + len(title) * t_h + (36 + len(sub) * s_h if sub else 0) + \
        (150 if card.get("adres") else 0) + (40 if rule else 0)
    top = max(SAFE_TOP, (SAFE_TOP + SIZE[1] - SAFE_BOTTOM) // 2 - block // 2)
    still = first                  # pierwsza klatka filmu: bez wejścia
    quick = dur < 2.5
    at = lambda t: None if still else t  # noqa: E731
    draws = []
    y = top + (logo_h + 60 if logo else 0)
    draws += [_draw(texts, ln, title_f, fg, "(w-text_w)/2", y + int(title_f.size * 0.9) + j * t_h,
                    at(0.05 + (0.06 if quick else 0.12) * j)) for j, ln in enumerate(title)]
    y += len(title) * t_h
    if rule:
        draws.append("drawbox=x=(iw-120)/2:y=%d:w=120:h=6:color=%s:t=fill%s"
                     % (y + 22, accent, "" if still else ":enable='gte(t,0.3)'"))
        y += 40
    if sub:
        y += 36
        draws += [_draw(texts, ln, sub_f, fg, "(w-text_w)/2", y + int(sub_f.size * 0.9) + j * s_h,
                        at((0.15 if quick else 0.4) + 0.1 * j)) for j, ln in enumerate(sub)]
        y += len(sub) * s_h
    if card.get("adres"):
        draws.append("drawbox=x=(iw-160)/2:y=%d:w=160:h=6:color=%s:t=fill%s"
                     % (y + 44, accent, "" if still else ":enable='gte(t,0.5)'"))
        draws.append(_draw(texts, card["adres"], addr_f, fg, "(w-text_w)/2", y + 136, at(0.55)))
    return _clip(os.path.join(work, name), bg, dur, draws, logo=(logo, "c", top, logo_h) if logo else None,
                 first=first, fade_out=not outro)


def explainer_clips(cards, brand, work, texts, folder=None, prefix="plansza", counter=True, first=False):
    """Plansze objaśnienia, każda osobnym klipem. Nazwa marki (albo logo w rogu) i licznik pod górną strefą,
    pasek postępu w kolorze akcentu pod nimi, tekst (dopasowany rozmiar, *słowo* w akcencie) wchodzi wiersz po
    wierszu i powoli dryfuje, opcjonalny obraz nad tekstem, podpis wchodzi jako druga informacja w pudełku napisów
    przy lewym marginesie, nad dolną strefą. cards: lista plansz (także plansze_przed / plansze_po pokazu).
    first: pierwsza plansza jest pierwszym klipem filmu, więc tekst stoi od pierwszej klatki (hak, miniatura)."""
    kol = brand["kolory"]
    bg_hex, fg_hex = kol["tlo"], kol["tekst"]
    bg, fg = _col(bg_hex), _col(fg_hex)
    # wyróżnienie i kreski: akcent czytelny na tle i odróżnialny od koloru tekstu (granat przy czarnym tekście: akcent2)
    accent_hex = next((c for c in (kol["akcent"], kol.get("akcent2")) if c and contrast(c, bg_hex) >= 3
                       and contrast(c, fg_hex) >= 1.6), readable(bg_hex, kol["akcent"], kol.get("akcent2"), fg_hex))
    accent = _col(accent_hex)
    head_col = _col(readable(bg_hex, kol["akcent"], fg_hex))
    small = _font(brand, "tekst", 40)
    style = caption_style(brand)
    studio = studio_dir(folder) if folder else None
    corner = logo_path(brand, studio) if brand.get("logo_w_rogu") else None
    out = []
    head = HEAD_Y                              # linia bazowa nazwy marki i licznika: pod górną nakładką aplikacji
    for i, c in enumerate(cards):
        still = first and i == 0
        dur = card_time(c, hook=still)[0]
        img = image_path(folder, c["obraz"]) if folder and c.get("obraz") else None
        # pytanie albo krótkie hasło bez podpisu i obrazu: większy tekst na środku (inny rytm niż plansze z podpisem)
        center = not img and not c.get("podpis") and (_plain(c["tekst"]).strip().endswith("?")
                                                      or len(_plain(c["tekst"])) <= 32)
        sizes, max_lines = (list(range(80, 55, -4)), 3) if img else \
            (list(range(104, 67, -4)), 4) if center else (list(range(92, 59, -4)), 5)
        f, lines = fit(c["tekst"].strip(), _font(brand, "tytul", sizes[0]), TEXT_W, sizes, max_lines)
        line_h = int(f.size * 1.18)
        region = (1010, 1330) if img else (530, SIZE[1] - SAFE_BOTTOM - (230 if c.get("podpis") else 80))
        block = len(lines) * line_h
        top = max(region[0], (region[0] + region[1]) // 2 - block // 2)
        draws = []
        if brand.get("nazwa") and not corner:
            draws.append(_draw(texts, brand["nazwa"], small, head_col, str(MARGIN), head))
        if counter and len(cards) > 1:
            draws.append(_draw(texts, "%d/%d" % (i + 1, len(cards)), small,
                               _col(readable(bg_hex, kol.get("akcent2"), kol["akcent"], fg_hex)),
                               "w-%d-text_w" % MARGIN, head))
        rule_x = "(iw-120)/2" if center else str(MARGIN)
        draws.append("drawbox=x=%s:y=%d:w=120:h=10:color=%s:t=fill%s"
                     % (rule_x, top - 56, accent, "" if still else ":enable='gte(t,0.1)'"))
        step = min(0.12, 0.6 / max(1, len(lines)))
        state = False
        for j, ln in enumerate(lines):
            x = str(int(round((SIZE[0] - f.width(_plain(ln))) / 2))) if center else str(MARGIN)
            part, state = _draw_line(texts, ln, f, fg, accent, x, top + int(f.size * 0.92) + j * line_h,
                                     None if still else 0.15 + step * j, drift=(dur, 18), state=state)
            draws += part
        if c.get("podpis"):
            at = HOOK_CAPTION_AT if still else min(dur - 1.0, max(CAPTION_AT, 0.45 + step * len(lines)))
            draws += caption_filters(texts, [(at, c["podpis"])], dur, style, start_at=at, align="left")
        out.append(_clip(os.path.join(work, "%s-%02d.mp4" % (prefix, i + 1)), bg, dur, draws,
                         image=(img, 470, 500) if img else None, bar=(accent, BAR_Y),
                         logo=(corner, MARGIN, HEAD_Y - 58, 64) if corner else None, first=still))
    return out


def _duration(path):
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                           capture_output=True, text=True)
    try:
        return float(probe.stdout.strip() or 0)
    except ValueError:
        return 0.0


def transition(a, b):
    """Przejście między klipami o tłach a i b (#rrggbb albo None = nagranie strony). Między planszami: przenikanie
    (treść poprzedniej planszy najpierw gaśnie do jej tła, _clip fade_out, więc teksty się nie nakładają, a tło
    przechodzi wprost w kolor następnej planszy, bez czerni przed wezwaniem na końcu). Z nagraniem strony: przez
    czerń (obraz strony nie ma wygaszenia)."""
    if a and b:
        return "fade"
    return "fadeblack"


def assemble(parts, out, work, music=None):
    """Skleja klipy [(plik, czas)] albo [(plik, czas, tło)] przejściem (XFADE) w film.mp4 z dźwiękiem (muzyka marki
    albo cisza); zapis przez plik tymczasowy."""
    tmp = os.path.join(work, "film.mp4")
    parts = [tuple(p) + (None,) * (3 - len(p)) for p in parts]
    args, graph = [], []
    for i, (p, _d, _bg) in enumerate(parts):
        args += ["-i", p]
        graph.append("[%d:v]settb=AVTB,fps=30,setsar=1,format=yuv420p[v%d]" % (i, i))
    prev, total = "[v0]", parts[0][1]
    for i in range(1, len(parts)):
        graph.append("%s[v%d]xfade=transition=%s:duration=%.2f:offset=%.3f[x%d]"
                     % (prev, i, transition(parts[i - 1][2], parts[i][2]), XFADE, total - XFADE, i))
        prev, total = "[x%d]" % i, total + parts[i][1] - XFADE
    graph.append("%snull[vout]" % prev)
    n = len(parts)
    if music:
        args += media_input(music)
        graph.append("[%d:a]atrim=0:%.3f,afade=t=in:d=0.5,afade=t=out:st=%.3f:d=1.5,volume=0.8[aout]"
                     % (n, total, max(0, total - 1.5)))
    else:
        args += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
        graph.append("[%d:a]atrim=0:%.3f[aout]" % (n, total))
    _encode(args + ["-filter_complex", ";".join(graph), "-map", "[vout]", "-map", "[aout]"], tmp, final=True,
            seconds=total)
    shutil.move(tmp, out + ".tmp")
    os.replace(out + ".tmp", out)
    return out


def record(folder, expect_kind=None):
    """Nagrywa scenariusz do film.mp4 (pokaz albo objaśnienie, z planszami marki; pokaz także z planszami przed
    i po nagraniu strony). Zwraca ścieżkę filmu; błąd: wyjątek z opisem po polsku. expect_kind: rodzaj ustalony
    przy starcie (zmiana w trakcie: błąd)."""
    try:
        sc, brand, info = prepare(folder)
    except ValueError as e:
        raise RuntimeError("scenariusz: %s" % e)
    if expect_kind and info["kind"] != expect_kind:
        raise RuntimeError("scenariusz zmienił rodzaj w trakcie (%s → %s); nagraj ponownie" % (expect_kind, info["kind"]))
    work = tempfile.mkdtemp(prefix="film-")
    texts = _Texts(work)
    studio = studio_dir(folder)
    kol = brand["kolory"]
    try:
        parts = []
        intro, outro = _card(brand, sc, "plansza_startowa"), _card(brand, sc, "plansza_koncowa")
        card_bg = lambda c: c.get("tlo") or kol["tekst"]  # noqa: E731
        if intro:
            hook = is_hook(sc)                  # hak: sam tekst, bez logo, krótszy czas
            parts.append(brand_card(brand, intro, "plansza_startowa", work, texts, "start.mp4", first=True,
                                    studio=None if hook else studio, hook=hook) + (card_bg(intro),))

        def slides(cards, prefix, counter=True):
            return [p + (kol["tlo"],) for p in explainer_clips(cards, brand, work, texts, folder, prefix, counter,
                                                               first=not parts)]
        if info["kind"] == "objasnienie":
            parts += slides(sc["plansze"], "plansza")
        else:
            if sc.get("plansze_przed"):
                parts += slides(sc["plansze_przed"], "przed", counter=False)
            clip = record_page(folder, sc, brand, work)
            parts.append((clip, _duration(clip), None))
            if sc.get("plansze_po"):
                parts += slides(sc["plansze_po"], "po", counter=False)
        if outro:
            parts.append(brand_card(brand, outro, "plansza_koncowa", work, texts, "koniec.mp4", studio=studio)
                         + (card_bg(outro),))
        music = os.path.join(studio, brand["muzyka"]) if brand.get("muzyka") else None
        return assemble(parts, os.path.join(folder, "film.mp4"), work, music)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def record_page(folder, sc, brand, work):
    """Pokaz: nagranie przeglądarki według kroków (kursor w kolorach marki); zwraca klip 1080×1920 z napisami
    w stylu marki, z wyciętym długim czekaniem."""
    from playwright.sync_api import sync_playwright
    if not isinstance(sc.get("url"), str) or not sc["url"]:
        raise RuntimeError("scenariusz pokazu bez adresu strony (url)")
    captions, waits, t0 = [], [], None
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": VIEW[0], "height": VIEW[1]}, device_scale_factor=2,
                                  locale="pl-PL", record_video_dir=work,
                                  # kadr = ekran; nagranie Playwright (i screencast CDP) w headless ma rozmiar CSS
                                  # (540×960) mimo device_scale_factor=2, większy rozmiar tylko dokleja szare pole
                                  record_video_size={"width": VIEW[0], "height": VIEW[1]})
        ctx.add_init_script(cursor_js(brand))
        sites = [h.lower() for h in (brand.get("strony") or [])] or [_host(sc["url"])[1]]
        blocked = []

        def guard(route):
            """Nawigacja głównej ramki tylko na strony marki (przekierowanie gdzie indziej przerywa nagranie)."""
            req = route.request
            try:
                main = req.is_navigation_request() and req.frame.parent_frame is None
            except Exception:  # noqa: BLE001
                main = req.is_navigation_request()
            u, host = _host(req.url)
            if main and not (u and u.scheme == "https" and host_allowed(host, sites)):
                blocked.append(host or req.url[:60])
                return route.abort()
            return route.continue_()
        ctx.route("**/*", guard)
        page = ctx.new_page()

        def landed(what):
            u, host = _host(page.url)
            if blocked or not (u and u.scheme == "https" and host_allowed(host, sites)):
                raise RuntimeError("%s: strona przekierowała poza strony marki (%s)" % (what, (blocked or [host])[0]))
            return host
        if sc.get("logowanie"):
            try:
                with open(account_file(), encoding="utf-8") as f:
                    acc = json.load(f)
            except (OSError, ValueError):
                raise RuntimeError("brak konta demo do nagrań (panel: Agenci → Publikacja → Konto do nagrań)")
            page.goto(sc["logowanie"], wait_until="networkidle", timeout=60000)
            if landed("logowanie") != _host(sc["logowanie"])[1]:      # konto demo tylko na hoście logowania
                raise RuntimeError("logowanie: strona wylądowała na innym hoście niż adres logowania")
            page.fill("#lg-email", acc["email"])
            page.fill("#lg-pass", acc["haslo"])
            page.locator("button[type=submit]").first.click()
            try:
                page.wait_for_url(lambda u: "/logowanie" not in u, timeout=20000)
            except Exception:  # noqa: BLE001
                raise RuntimeError("logowanie kontem demo nie powiodło się (sprawdź e-mail i hasło)")
        page.goto(sc["url"], wait_until="networkidle", timeout=60000)
        landed("url")
        page.wait_for_timeout(800)
        t0 = time.monotonic()           # początek filmu: strona już wczytana
        page.mouse.move(VIEW[0] / 2, VIEW[1] / 3)

        def let_read():
            """Poprzedni napis stoi w filmie co najmniej czas czytania (wycięte czekanie się nie liczy)."""
            if captions:
                cuts = cuts_for(waits)
                shown = shift_time(time.monotonic() - t0, cuts) - shift_time(captions[-1][0], cuts)
                need = caption_need(captions[-1][1])
                if shown < need:
                    page.wait_for_timeout(int((need - shown) * 1000) + 50)
        for i, k in enumerate(sc.get("kroki") or []):
            if k.get("napis"):
                let_read()
                captions.append([time.monotonic() - t0, str(k["napis"])])
            try:
                if k.get("rozwin"):
                    page.locator(k["rozwin"]).first.evaluate("el => { el.open = true }")
                    page.wait_for_timeout(300)
                if k.get("przewin"):
                    page.locator(k["przewin"]).first.scroll_into_view_if_needed(timeout=10000)
                    page.wait_for_timeout(400)
                if k.get("wpisz"):
                    sel, text = k["wpisz"]
                    text = str(text)
                    loc = page.locator(sel).first
                    loc.scroll_into_view_if_needed(timeout=10000)
                    loc.click(timeout=10000)
                    loc.press_sequentially(text, delay=max(20, min(55, int(1400 / max(1, len(text))))))
                if k.get("wybierz"):
                    sel, value = k["wybierz"]
                    loc = page.locator(sel).first
                    loc.scroll_into_view_if_needed(timeout=10000)
                    loc.click(timeout=10000)
                    loc.select_option(str(value), timeout=10000)
                if k.get("kliknij"):
                    loc = page.locator(k["kliknij"]).first
                    loc.scroll_into_view_if_needed(timeout=10000)
                    page.wait_for_timeout(250)
                    loc.click(timeout=15000)
                if k.get("czekaj_na"):
                    w0 = time.monotonic() - t0
                    page.locator(k["czekaj_na"]).first.wait_for(timeout=int(float(k.get("limit", 60)) * 1000))
                    waits.append((w0, time.monotonic() - t0))
                page.wait_for_timeout(int(float(k.get("pauza", 0.6)) * 1000))
            except Exception as e:  # noqa: BLE001
                if k.get("opcjonalnie"):        # krok, który może nie zadziałać (np. zamknięcie baneru)
                    continue
                try:                    # zrzut ekranu z chwili błędu: łatwiej poprawić scenariusz
                    page.screenshot(path=os.path.join(folder, ".film-blad.png"), full_page=True)
                except Exception:  # noqa: BLE001
                    pass
                raise RuntimeError("krok %d (%s): %s" % (i + 1, k.get("napis") or k.get("kliknij") or k.get("wpisz"),
                                                       str(e).split("\n")[0][:200]))
        let_read()
        end = time.monotonic() - t0
        video = page.video.path()
        ctx.close()
        browser.close()
    return render(video, os.path.join(work, "pokaz.mp4"), captions, end, work, caption_style(brand), waits)


def cuts_for(waits, keep_head=0.6, keep_tail=0.5, min_len=1.5):
    """Odcinki czekania do wycięcia: z czekania dłuższego niż min_len zostaje początek i koniec."""
    out = []
    for a, b in waits:
        if b - a > min_len:
            out.append((a + keep_head, b - keep_tail))
    return out


def shift_time(t, cuts):
    """Czas w filmie po wycięciu odcinków cuts (napisy przesuwają się razem z obrazem)."""
    removed = 0.0
    for a, b in cuts:
        if t >= b:
            removed += b - a
        elif t > a:
            removed += t - a
    return t - removed


def render(src, out, captions, end, work, style=None, waits=()):
    """Przycięcie początku (wczytywanie strony), wycięcie długiego czekania, napisy wtopione (styl marki),
    H.264 1080×1920 30 kl./s (klip pośredni do sklejenia)."""
    total = _duration(src)
    lead = max(0.0, total - end - 0.2)    # nagranie zaczyna się przed t0 (wczytywanie strony): odcinamy
    if style is None:
        style = dict(DEFAULT_BRAND["napisy"], font=Font(FONT, 56))
    cuts = cuts_for(waits)
    filters = ["scale=1080:1920:flags=lanczos", "fps=30"]
    if cuts:
        cond = "+".join("between(t,%.3f,%.3f)" % (a + 0.2, b + 0.2) for a, b in cuts)   # 0,2 s: zapas z lead
        filters += ["select='not(%s)'" % cond, "setpts=N/30/TB"]
    caps = [(shift_time(at, cuts), text) for at, text in captions]
    filters += caption_filters(_Texts(work, "napis"), caps, shift_time(end, cuts), style)
    return _encode(["-ss", "%.2f" % lead, "-i", src, "-vf", ",".join(filters)], out)


class Recorder:
    """Uruchamia nagranie w tle osobnym interpreterem; stan w .film-stan.json folderu posta."""

    def __init__(self, notify=None, python=None, script=None):
        self.notify = notify or (lambda text: None)
        self.python = os.path.expanduser(python or os.environ.get("PANEL_FILM_PYTHON", "").strip()
                                         or "~/narzedzia/film/bin/python")
        self.script = script or os.path.abspath(__file__)
        self.lock = threading.Lock()
        self.busy = set()
        self.kinds = {}               # rodzaj ustalony w start(), przekazywany do nagrania

    def available(self, kind="pokaz"):
        """Pokaz: Playwright (osobny interpreter) i ffmpeg; objaśnienie: tylko ffmpeg."""
        return bool(shutil.which("ffmpeg")) and (kind == "objasnienie" or os.path.isfile(self.python))

    def interpreter(self, kind):
        """Objaśnienie bez Playwright: interpreter panelu (ma PIL do pomiaru tekstu, gdy jest zainstalowany)."""
        return self.python if kind != "objasnienie" else sys.executable

    def start(self, folder, title=""):
        if not folder:
            return 404, "Nie ma posta na ten dzień."
        if not os.path.isfile(os.path.join(folder, SCENARIO)):
            return 409, "Post nie ma scenariusza filmu (scenariusz.json)."
        info = describe(folder)
        if info["error"]:          # błąd szablonu albo marki: widoczny w poście od razu, bez uruchamiania nagrania
            keep = {k: v for k, v in read_state(folder).items() if k == "scenario"}
            write_state(folder, state="error", error="scenariusz: " + info["error"], **keep)
            return 409, "Scenariusz filmu: %s." % info["error"]
        if not (self.available() if info["kind"] == "pokaz" else self.available(info["kind"])):
            return 409, ("Na serwerze nie ma narzędzi do nagrywania (Playwright, ffmpeg)." if info["kind"] == "pokaz"
                         else "Na serwerze nie ma ffmpeg (potrzebny do objaśnień).")
        with self.lock:
            if folder in self.busy:
                return 409, "Film już się nagrywa."
            self.busy.add(folder)
            self.kinds[folder] = info["kind"]
        # host i pid: drugi egzemplarz panelu na tych samych plikach nie uzna tego nagrania za przerwane;
        # scenario zostaje (auto_record nagrywa jedną wersję scenariusza raz, także po błędzie)
        keep = {k: v for k, v in read_state(folder).items() if k == "scenario"}
        write_state(folder, state="running", error="", host=HOST, pid=os.getpid(), kind=info["kind"], **keep)
        threading.Thread(target=self._run, args=(folder, title), daemon=True).start()
        return 202, "", {"state": "running"}

    def _run(self, folder, title):
        """Nagranie w osobnej grupie procesów (przy przekroczeniu limitu ginie też ffmpeg i Chromium). Zawsze, także
        po nieoczekiwanym wyjątku, zapisuje stan i zwalnia folder (inaczej automat nagrań stałby do restartu)."""
        ok, err = False, "nieznany błąd"
        try:
            with self.lock:
                kind = self.kinds.pop(folder, None)
            kind = kind or describe(folder)["kind"]
            proc = subprocess.Popen([self.interpreter(kind), self.script, "nagraj", folder, kind],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
            try:
                out, errs = proc.communicate(timeout=TIMEOUT)
                ok = proc.returncode == 0
                err = "" if ok else ((errs or out or "").strip().splitlines() or ["nieznany błąd"])[-1][:300]
            except subprocess.TimeoutExpired:
                _kill_group(proc)
                ok, err = False, "nagrywanie trwało ponad 10 minut"
        except Exception as e:  # noqa: BLE001
            ok, err = False, "nie uruchomiono nagrania (%s)" % (str(e)[:200] or type(e).__name__)
        finally:
            try:
                keep = {k: v for k, v in read_state(folder).items() if k == "scenario"}
                write_state(folder, state="done" if ok else "error", error=err, **keep)
                if ok:
                    try:
                        os.remove(os.path.join(folder, MANUAL))
                    except OSError:
                        pass
            except OSError:
                pass
            with self.lock:
                self.busy.discard(folder)
                self.kinds.pop(folder, None)
        self.notify(("Film nagrany: %s. Obejrzyj go w poście." % (title or os.path.basename(folder))) if ok
                    else "Nie nagrano filmu (%s): %s" % (title or os.path.basename(folder), err))


def _kill_group(proc):
    """Zakończenie nagrania razem z procesami potomnymi (ffmpeg, Chromium)."""
    try:
        os.killpg(proc.pid, 15)
        proc.wait(timeout=10)
    except Exception:  # noqa: BLE001
        try:
            os.killpg(proc.pid, 9)
        except Exception:  # noqa: BLE001
            pass
    try:
        proc.communicate(timeout=5)
    except Exception:  # noqa: BLE001
        pass


if __name__ == "__main__":
    if len(sys.argv) in (3, 4) and sys.argv[1] == "nagraj":
        try:
            print(record(sys.argv[2], sys.argv[3] if len(sys.argv) == 4 else None))
        except Exception as e:  # noqa: BLE001
            print("Błąd nagrania: %s" % e, file=sys.stderr)
            sys.exit(1)
    elif len(sys.argv) == 3 and sys.argv[1] == "sprawdz":
        info = describe(sys.argv[2])
        print(json.dumps(info, ensure_ascii=False))
        sys.exit(1 if info["error"] else 0)
    else:
        print("użycie: film.py nagraj|sprawdz <folder posta> [rodzaj]", file=sys.stderr)
        sys.exit(2)
