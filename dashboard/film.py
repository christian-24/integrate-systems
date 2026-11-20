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
                                   środek czekania dłuższego niż 1,5 s jest w filmie przyspieszony (znak „×N”)
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
import math
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
SRT = "film.srt"                  # napisy filmu jako osobny plik (platformy, które wolą napisy obok wideo)
FEED = "film-4x5.mp4"             # wersja 4:5 do feedu LinkedIn i Facebook (kadr 1080×1350 ze środka filmu)
FEED_CROP = (1350, 300)           # wysokość i górna krawędź kadru 4:5: nagłówek planszy i napisy zostają w kadrze
ERROR_SHOT = ".film-blad.png"     # zrzut strony z chwili błędu kroku pokazu (panel pokazuje go przy błędzie)
PREVIOUS = ".film-poprzedni.mp4"  # poprzednia wersja filmu po nagraniu nowej (panel: porównanie wersji)
MUSIC_PIN = ".film-podklad"       # podkład z listy marki wybrany przy pierwszym nagraniu (stała rotacja podkładów)
MANUAL = ".film-wgrany"          # film wgrany ręcznie w panelu: zmiana studia nie nagrywa go sama od nowa
VIEW = (540, 960)                 # CSS px; nagranie 2× = 1080×1920
# czcionka zastępcza (marka bez czcionek albo czcionka nie znaleziona): pierwszy istniejący plik; Linux (serwer), macOS
FONT_FALLBACKS = ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                  "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
                  "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                  "/Library/Fonts/Arial Bold.ttf",
                  "/System/Library/Fonts/Supplemental/Verdana Bold.ttf")
FONT = next((f for f in FONT_FALLBACKS if os.path.isfile(f)), FONT_FALLBACKS[0])
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
    try {          // po przejściu na inną stronę kursor zostaje tam, gdzie był (bez znikania do następnego ruchu)
      const p = JSON.parse(sessionStorage.getItem('__kursor') || 'null');
      if (p) { c.style.transition = 'none'; c.style.left = p[0] + 'px'; c.style.top = p[1] + 'px';
               requestAnimationFrame(() => { c.style.transition = 'left .25s,top .25s'; }); }
    } catch (e) {}
    addEventListener('mousemove', e => {
      c.style.left = e.clientX + 'px'; c.style.top = e.clientY + 'px';
      try { sessionStorage.setItem('__kursor', JSON.stringify([e.clientX, e.clientY])); } catch (err) {}
    }, true);
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


# aktywny element pokazu: przewinięcie płynne do pasa między górną strefą aplikacji a napisem (CSS px kadru 540×960;
# dół: nad pudełkiem napisu, które sięga ok. y 1250 z 1920). Zwraca przesunięcie w px (0: bez przewijania).
BAND = (145, 600)                 # SAFE_TOP / 2 + 20 (CSS px)
BAND_JS = """(el, band) => {
  const r = el.getBoundingClientRect();
  let dy = 0;
  if (r.top < band[0] || r.height > band[1] - band[0]) dy = r.top - band[0];
  else if (r.bottom > band[1]) dy = r.bottom - band[1];
  if (Math.abs(dy) < 3) return 0;
  window.scrollBy({top: dy, behavior: 'smooth'});
  return Math.abs(dy);
}"""


HIDE_JS = """
(() => {
  const sels = %s;
  const add = () => {
    if (document.getElementById('__ukryj')) return;
    const st = document.createElement('style'); st.id = '__ukryj';
    (document.head || document.documentElement).appendChild(st);
    for (const s of sels) {          // każdy selektor osobno: błędny nie psuje pozostałych
      try { st.sheet.insertRule(s + '{display:none!important}', st.sheet.cssRules.length); } catch (e) {}
    }
  };
  if (document.readyState === 'loading') addEventListener('DOMContentLoaded', add); else add();
})();
"""


def hide_list(brand, sc):
    """Selektory elementów ukrywanych w pokazie: z marki („ukryj”, np. baner zgody na całej stronie) i ze scenariusza
    (tylko ten film), bez powtórzeń, najwyżej HIDE_MAX."""
    out = []
    for src in ((brand or {}).get("ukryj"), (sc or {}).get("ukryj")):
        for x in src if isinstance(src, list) else []:
            if isinstance(x, str) and HIDE_RE.match(x) and "/*" not in x and x.strip() not in out:
                out.append(x.strip())
    return out[:HIDE_MAX]


def hide_js(sels):
    """Skrypt ukrywający elementy strony (CSS display:none) od pierwszego wczytania każdej strony pokazu."""
    return HIDE_JS % json.dumps(list(sels))


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
NUMBER_RE = re.compile(r"[0-9]{1,9}(?:[.,][0-9]{1,6})?")
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
CARD_CPS = 17                     # znaki na sekundę na planszach w środku objaśnienia (krótkie zdania, szybsze tempo
                                  # Reels); hak i plansze marki: READ_CPS
XFADE = 0.35                      # przejście między klipami (s)
LOOP_X = 1.5                      # s: przenikanie na szwie podkładu krótszego niż film
FADE_OUT = 0.2                    # s: treść planszy gaśnie do tła tuż przed przejściem (bez podwójnej ekspozycji)
CARD_TIMES = {"plansza_startowa": 1.2, "plansza_koncowa": 3.0}
CAPTION_AT = 0.9                  # s: podpis planszy wchodzi jako druga informacja, po tekście (wcześniej 1,1 s: widz czekał)
HOOK_CAPTION_AT = 0.6             # s: podpis haka (pierwsza plansza filmu, tekst od pierwszej klatki)
HOOK_BASE = 0.6                   # s: hak stoi od pierwszej klatki, więc bez czasu na wejście tekstu
HOOK_MAX = 3.5                    # s: dłuższy hak dostaje ostrzeżenie (pierwsze sekundy decydują o obejrzeniu)
HOOK_CHARS = int((HOOK_MAX - HOOK_BASE) * READ_CPS)   # znaków haka (bez gwiazdek) mieszczących się w HOOK_MAX: 43
END_MAX = 4.0                     # s: plansza końcowa bez podanego czasu (wezwanie wchodzi etapami, nie stoi długo)
POKAZ_MAX = 60                    # s: dłuższy pokaz dostaje ostrzeżenie (cel kampanii: film do 60 s)
OBJ_MAX = 30                      # s: dłuższe objaśnienie dostaje ostrzeżenie (Reels)
HEAD_Y = 380                      # linia bazowa nazwy marki i licznika plansz (ok. 20% wysokości, pod nakładką Reels)
BAR_Y = 408                       # pasek postępu planszy: pod nazwą marki i licznikiem
CTRL_RE = re.compile(r"[\x00-\x1f\x7f]")      # znaki sterujące (nowy wiersz, tabulator, \x00) w tekstach filmu
IMAGE_MAX = 15 * 1024 * 1024      # obraz planszy albo logo
AUDIO_MAX = 30 * 1024 * 1024      # muzyka marki
MUSIC_MAX = 12                    # podkładów marki na zmianę (kolejne filmy projektu dostają kolejne)
# Bez marka.json: wygląd napisów jak dotąd (biały tekst na ciemnym pasku), plansze w neutralnych kolorach.
DEFAULT_BRAND = {"nazwa": "", "zrodlo": "", "strony": [], "muzyka": "", "logo": "", "logo_w_rogu": False,
                 "kolory": {"tlo": "#f4f4f2", "tekst": "#1d1d1f", "akcent": "#3b5bdb", "akcent2": "#868e96"},
                 "czcionki": {"tytul": "", "tekst": "", "napisy": ""},
                 "napisy": {"rozmiar": 56, "kolor": "#ffffff", "tlo": "#2b1d12", "krycie": 0.85},
                 "plansza_startowa": None, "plansza_koncowa": None,
                 # elementy strony ukrywane w pokazie (selektory CSS: baner zgody, pływający przycisk „Opinia”, czat)
                 "ukryj": [],
                 # braki marki dla właściciela (np. krój strony niedostępny na serwerze): panel pokazuje je w Studiu
                 "braki": [],
                 # plansze marki z tekstem tymczasowym: {"plansza_koncowa": "co potwierdzić i gdzie"}
                 "do_potwierdzenia": {}}
BRAND_KEYS = set(DEFAULT_BRAND)
HIDE_MAX = 20                     # selektorów „ukryj” (marka i scenariusz razem)
HIDE_RE = re.compile(r"^[^{}<>\\\x00-\x1f]{1,120}$")    # selektor CSS bez nawiasów klamrowych, znaczników i odwrotnego ukośnika
CARD_KEYS = {"tytul", "podtytul", "adres", "czas", "tlo", "kolor"}
CARD_COLORS = ("tlo", "kolor")    # nadpisanie tytułu planszy w filmie dziedziczy z marki tylko kolory
BRAND_HELP = ('marka.json: {"nazwa", "zrodlo", "strony": ["host"], "muzyka": "plik w studio/" albo ["plik", …] (na zmianę), '
              '"logo": "plik .png (przezroczyste tło) albo .jpg w studio/", "logo_w_rogu": true|false, '
              '"kolory": {"tlo", "tekst", "akcent", "akcent2"} (#rrggbb), "czcionki": {"tytul", "tekst", "napisy"} '
              '(nazwa czcionki, opcjonalnie ":Bold" itp.), "napisy": {"rozmiar" 24–120, "kolor", "tlo", "krycie" 0–1}, '
              '"plansza_startowa" / "plansza_koncowa": {"tytul", "podtytul", "adres", "czas" s, "tlo", "kolor"}, '
              '"ukryj": ["selektor CSS elementu strony ukrytego w pokazie"], "braki": ["brak marki dla właściciela"], '
              '"do_potwierdzenia": {"plansza_koncowa": "co potwierdzić"}}')
# klucze scenariusza według rodzaju; "opis" i "komentarz" to komentarze (pomijane), "muzyka" to podkład tego filmu;
# szablon ma dodatkowo TEMPLATE_EXTRA
COMMENT_KEYS = {"opis", "komentarz"}
SC_KEYS = {"pokaz": {"typ", "url", "logowanie", "kroki", "plansze_przed", "plansze_po",
                     "plansza_startowa", "plansza_koncowa", "muzyka", "ukryj"} | COMMENT_KEYS,
           "objasnienie": {"typ", "plansze", "plansza_startowa", "plansza_koncowa", "muzyka"} | COMMENT_KEYS}
TEMPLATE_EXTRA = {"opis", "tytul", "parametry", "etykiety", "wymagane", "limity", "dla_wlasciciela", "aliasy"}
LOGIN_KEYS = {"url": None, "email": "#lg-email", "haslo": "#lg-pass", "wyslij": "button[type=submit]"}
LIMIT_KEYS = {"max", "opcje", "cyfry"}
TEXT_KEYS = {"napis", "tekst", "podpis", "tytul", "podtytul", "adres"}   # liczba z parametru staje się tekstem
WITH_ORDER = ("szablon", "parametry", "plansza_startowa", "plansza_koncowa", "muzyka", "opis", "komentarz")
WITH_TEMPLATE = set(WITH_ORDER)
STEP_KEYS = ("napis", "wpisz", "wybierz", "kliknij", "przewin", "rozwin", "czekaj_na", "limit", "pauza", "opcjonalnie")
CARD_SC_KEYS = {"tekst", "podpis", "czas", "obraz", "uklad"}


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
    """Liczba skończona (bez True/False, NaN i nieskończoności)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


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


def media_input(path, seconds=None, loop=True):
    """Argumenty wejścia ffmpeg dla pliku z karty: tylko protokół file i jawny demuxer (obraz: image2 bez wzorca
    nazw, zapętlony przez seconds; muzyka: demuxer z rozszerzenia, zapętlona, gdy loop)."""
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    if ext in DEMUXER:
        return ["-protocol_whitelist", "file"] + (["-stream_loop", "-1"] if loop else []) + \
            ["-f", DEMUXER[ext], "-i", path]
    return ["-protocol_whitelist", "file", "-f", "image2", "-pattern_type", "none", "-loop", "1", "-framerate", "30",
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


def hide_errors(value, key="ukryj"):
    """Błędy listy selektorów CSS elementów ukrywanych w pokazie (marka albo scenariusz)."""
    if not (isinstance(value, list) and len(value) <= HIDE_MAX
            and all(isinstance(x, str) and HIDE_RE.match(x) and x.strip() and "/*" not in x for x in value)):
        return ["%s: lista do %d selektorów CSS (np. \"#baner-zgody\", \".opinia\"), bez { } < >" % (key, HIDE_MAX)]
    return []


def brand_warnings(b):
    """Nieznane klucze marka.json (literówka, pole dodane przez agenta): ostrzeżenie, nie błąd blokujący filmy."""
    if not isinstance(b, dict):
        return []
    out = ["marka.json: nieznany klucz „%s” (pomijany)" % k for k in b if k not in BRAND_KEYS]
    kol = b.get("kolory")
    if isinstance(kol, dict):
        out += ["marka.json: nieznany klucz „kolory.%s” (pomijany)" % k for k in kol
                if k not in ("tlo", "tekst", "akcent", "akcent2")]
    return out


def validate_brand(b):
    """Błędy marka.json po polsku (pusta lista: poprawna). Nieznane klucze nie są błędem (brand_warnings)."""
    if not isinstance(b, dict):
        return ["marka.json: oczekiwany obiekt JSON"]
    err = []
    for key in ("nazwa", "zrodlo"):
        if key in b and not isinstance(b[key], str):
            err.append("%s: tekst" % key)
    if "strony" in b and not (isinstance(b["strony"], list) and len(b["strony"]) <= 5
                              and all(isinstance(h, str) and HOST_RE.match(h) for h in b["strony"])):
        err.append("strony: lista hostów, np. [\"opisarnia.pl\"]")
    if b.get("muzyka") and not (isinstance(b["muzyka"], str) and AUDIO_RE.match(b["muzyka"])) and not (
            isinstance(b["muzyka"], list) and 1 <= len(b["muzyka"]) <= MUSIC_MAX
            and all(isinstance(m, str) and AUDIO_RE.match(m) for m in b["muzyka"])):
        err.append("muzyka: nazwa pliku mp3/m4a/wav/ogg w studio/ albo lista do %d takich plików (filmy dostają "
                   "je na zmianę)" % MUSIC_MAX)
    if b.get("logo") and not (isinstance(b["logo"], str) and IMAGE_RE.match(b["logo"])):
        err.append("logo: nazwa pliku .png albo .jpg w studio/ (najlepiej png z przezroczystym tłem)")
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
                continue                         # nieznany kolor: ostrzeżenie (brand_warnings)
            if not (isinstance(value, str) and COLOR_RE.match(value)):
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
    if "ukryj" in b:
        err += hide_errors(b["ukryj"])
    if "braki" in b and not (isinstance(b["braki"], list) and len(b["braki"]) <= 8
                             and all(isinstance(x, str) and 0 < len(x.strip()) <= 200 for x in b["braki"])):
        err.append("braki: lista do 8 krótkich opisów (do 200 znaków)")
    tmp = b.get("do_potwierdzenia")
    if tmp is not None and not (isinstance(tmp, dict) and all(k in CARD_NAMES for k in tmp)
                                and all(isinstance(v, str) and 0 < len(v.strip()) <= 200 for v in tmp.values())):
        err.append("do_potwierdzenia: obiekt {\"plansza_startowa\" albo \"plansza_koncowa\": \"co potwierdzić\"}")
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
        for name in (music_list(raw.get(key)) if key == "muzyka" else [raw.get(key)] if raw.get(key) else []):
            if errors:
                break
            path = os.path.join(studio, name)
            if not (os.path.isfile(path) and _inside(path, studio)):
                errors.append("%s: brak pliku studio/%s" % (key, name))
            else:
                bad = media_error(path, kind)
                if bad:
                    errors.append("%s: %s" % (key, bad))
    if errors:
        return brand, errors, True
    for key, value in raw.items():
        if key not in BRAND_KEYS:              # nieznany klucz: pomijany (ostrzeżenie w brand_warnings)
            continue
        if key == "kolory":
            brand[key].update({k: v for k, v in value.items() if k in brand[key]})
        elif isinstance(value, dict) and isinstance(brand.get(key), dict):
            brand[key].update(value)
        else:
            brand[key] = value
    if "akcent2" not in raw["kolory"]:           # bez drugiego akcentu: akcent marki, nie neutralny domyślny
        brand["kolory"]["akcent2"] = brand["kolory"]["akcent"]
    return brand, [], True


def music_list(value):
    """Podkłady marki jako lista nazw plików (marka.json: "muzyka" to jeden plik albo lista)."""
    if isinstance(value, str):
        return [value] if value else []
    return [m for m in value if isinstance(m, str) and m] if isinstance(value, list) else []


def music_name(folder, brand, sc):
    """Podkład filmu: "muzyka" ze scenariusza (plik w studio/; false: film bez muzyki), inaczej kolejny z listy
    marki według liczby wcześniejszych postów projektu ze scenariuszem (kolejne filmy mają różne podkłady). "" bez
    muzyki."""
    own = sc.get("muzyka") if isinstance(sc, dict) else None
    if own is False:
        return ""
    if isinstance(own, str) and own:
        return own
    names = music_list((brand or {}).get("muzyka"))
    pinned = music_pinned(folder)
    if pinned and pinned in names:        # podkład z pierwszego nagrania: nowy albo usunięty wcześniejszy post go nie zmienia
        return pinned
    if len(names) < 2:
        return names[0] if names else ""
    me = os.path.basename(os.path.abspath(folder)) if folder else ""
    try:
        base = os.path.dirname(os.path.abspath(folder))
        earlier = [n for n in os.listdir(base) if n < me and os.path.isfile(os.path.join(base, n, SCENARIO))]
    except (OSError, TypeError):
        earlier = []
    return names[len(earlier) % len(names)]


def music_pinned(folder):
    """Podkład zapisany przy pierwszym nagraniu filmu posta (plik MUSIC_PIN w folderze posta) albo ""."""
    if not folder:
        return ""
    try:
        with open(os.path.join(folder, MUSIC_PIN), encoding="utf-8") as f:
            name = f.read().strip()
    except OSError:
        return ""
    return name if AUDIO_RE.match(name) else ""


def pin_music(folder, name):
    """Zapisuje podkład filmu posta (kolejne posty i zmiany listy marki go nie przesuwają)."""
    if folder and name and AUDIO_RE.match(name) and music_pinned(folder) != name:
        try:
            _write_atomic(os.path.join(folder, MUSIC_PIN), name + "\n")
        except OSError:
            pass


TYPE_NAMES = {"NoneType": "puste pole (null)", "bool": "prawda/fałsz", "dict": "obiekt", "list": "lista",
              "str": "tekst", "int": "liczba", "float": "liczba"}


def type_name(value):
    """Rodzaj wartości JSON po polsku (komunikat o złym typie)."""
    return TYPE_NAMES.get(type(value).__name__, "inna wartość")


def _param_value(name, value):
    if isinstance(value, str) or _num(value):
        return value
    raise ValueError("parametr „%s”: tekst albo liczba (jest %s)" % (name, type_name(value)))


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
        if "uklad" in c:
            lay = c["uklad"]
            if lay not in LAYOUTS:
                err.append("%s: uklad jeden z: %s" % (label, ", ".join(LAYOUTS)))
            elif lay == "zrzut" and not c.get("obraz"):
                err.append("%s: układ zrzut wymaga obrazu (obraz)" % label)
            elif lay == "lista" and isinstance(c.get("tekst"), str) and not \
                    2 <= len([x for x in c["tekst"].split(";") if x.strip()]) <= LIST_MAX:
                err.append("%s: układ lista to 2–%d punktów oddzielonych średnikiem" % (label, LIST_MAX))
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
    for key in COMMENT_KEYS:
        if key in sc and not isinstance(sc[key], str):
            err.append("%s: tekst (komentarz)" % key)
    if "muzyka" in sc and not (sc["muzyka"] is False or (isinstance(sc["muzyka"], str)
                                                        and AUDIO_RE.match(sc["muzyka"]))):
        err.append("muzyka: nazwa pliku mp3/m4a/wav/ogg w studio/ albo false (film bez muzyki)")
    if typ == "objasnienie":
        bad = _slides_errors(sc.get("plansze"), "plansze", MAX_CARDS)
        if bad and bad[0].startswith("plansze:"):
            return err + bad
        err += bad
    else:
        if not (isinstance(sc.get("url"), str) and sc["url"].strip()):
            err.append("url: adres strony do nagrania (https://…)")
        if "logowanie" in sc:
            err += login_errors(sc["logowanie"])
        steps = sc.get("kroki")
        if not isinstance(steps, list) or not 1 <= len(steps) <= MAX_STEPS:
            err.append("kroki: lista 1–%d kroków" % MAX_STEPS)
        else:
            for i, k in enumerate(steps, 1):
                err += _step_errors(i, k)
        for key in ("plansze_przed", "plansze_po"):
            if key in sc:
                err += _slides_errors(sc[key], key, MAX_EXTRA_CARDS)
        if "ukryj" in sc:
            err += hide_errors(sc["ukryj"])
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


def login_spec(value):
    """Logowanie pokazu: adres strony logowania (tekst; pola jak w Opisarni) albo {"url", "email", "haslo",
    "wyslij"} z selektorami pól innej aplikacji. Zwraca słownik z uzupełnionymi selektorami."""
    if isinstance(value, dict):
        return {k: (value.get(k) if value.get(k) else d) for k, d in LOGIN_KEYS.items()}
    return dict(LOGIN_KEYS, url=value if isinstance(value, str) else None)


def login_errors(value):
    """Błędy pola "logowanie" scenariusza (adres albo obiekt z selektorami)."""
    if isinstance(value, str):
        return [] if value.strip() else ["logowanie: adres strony logowania (https://…)"]
    if not isinstance(value, dict):
        return ["logowanie: adres strony logowania albo {\"url\", \"email\", \"haslo\", \"wyslij\"} (selektory pól)"]
    err = ["logowanie: nieznany klucz „%s” (dozwolone: %s)" % (k, ", ".join(LOGIN_KEYS)) for k in sorted(value)
           if k not in LOGIN_KEYS]
    if not (isinstance(value.get("url"), str) and value["url"].strip()):
        err.append("logowanie.url: adres strony logowania (https://…)")
    for k in ("email", "haslo", "wyslij"):
        if k in value and not (isinstance(value[k], str) and value[k].strip() and len(value[k]) <= 200):
            err.append("logowanie.%s: selektor pola (tekst)" % k)
    return err


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
        lu, lhost = _host(login_spec(sc["logowanie"])["url"])
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
    al = tpl.get("aliasy", {})
    if not (isinstance(al, dict) and all(isinstance(k, str) and PARAM_NAME_RE.match(k) and k not in names
                                         and isinstance(v, str) and v in names for k, v in al.items())):
        raise ValueError("szablon %s: aliasy to obiekt {stara nazwa parametru: obecna nazwa} (po zmianie nazwy "
                         "parametru starsze posty dalej się nagrywają)" % name)
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
    for k, v in params.items():          # wartość przykładowa w limitach szablonu (inaczej każdy post bez własnej
        try:                             # wartości dostaje błąd, choć winny jest szablon)
            _check_value(k, v, lim)
        except ValueError as e:
            raise ValueError("szablon %s: przykład parametru „%s”: %s" % (name, k, str(e).split(": ", 1)[-1]))
    return tpl


DUMMIES = ("Tekst; tekst", 3, "obraz.png")   # wartości zastępcze parametrów bez przykładu (tekst, liczba, plik)


def template_check(tpl):
    """Pierwszy błąd treści szablonu po podstawieniu wartości przykładowych (np. nieznany klucz planszy, tekst ponad
    limit) albo "". Parametr bez przykładu dostaje po kolei wartości zastępcze; błąd liczy się tylko wtedy, gdy
    wychodzi przy każdej z nich (inaczej to sprawa wartości w poście, nie szablonu)."""
    defaults = tpl.get("parametry") or {}
    names = template_params(tpl)
    found = None
    for dummy in DUMMIES:
        params = dict({k: dummy for k in names}, **defaults)
        try:
            errs = validate_scenario(_as_text(fill(_body(tpl), params)), template=True)
        except ValueError as e:
            errs = [str(e)]
        found = set(errs) if found is None else found & set(errs)
        if not found:
            return ""
    return next((e for e in errs if e in found), "")


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
    # gwiazdki wyróżnienia *słowo* nie są widoczne w filmie: limit liczy znaki bez nich (jak HOOK_CHARS)
    seen = len(str(value).replace("*", ""))
    if "max" in lim and seen > lim["max"]:
        raise ValueError("parametr „%s”: najwyżej %d znaków (jest %d)" % (name, lim["max"], seen))
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


def expand(sc, studio, meta=None, lenient=False):
    """(scenariusz po podstawieniu szablonu, nazwa szablonu albo ""). ValueError przy błędzie.
    meta (słownik): uzupełniany opisem szablonu, etykietami i parametrami z wartościami (dla panelu).
    Błąd w wartości jednego parametru posta (brak wymaganej treści, limit znaków, opcje): ScenarioError z opisem
    filmu (meta) i nazwą parametru, więc panel pokazuje pole do poprawy także wtedy, gdy film się nie rozwinął.
    Plansza startowa albo końcowa ze scenariusza jako obiekt łączy się z planszą szablonu (po podstawieniu);
    false albo true zastępuje ją w całości.
    lenient: parametr posta, którego szablon już nie ma (usunięty z szablonu), jest pomijany zamiast błędu; jego
    nazwy trafiają do meta["dropped"] (ostrzeżenie w opisie filmu). Bez lenient: ValueError (zmiana z panelu)."""
    if not isinstance(sc, dict):
        raise ValueError("scenariusz: oczekiwany obiekt JSON")
    if "szablon" not in sc:
        return sc, ""
    name = sc["szablon"]
    tpl = load_template(studio, name)
    extra = sorted(k for k in sc if k not in WITH_TEMPLATE)
    if extra:
        raise ValueError("obok „szablon” dozwolone tylko: %s (jest „%s”)"
                         % (", ".join(k for k in WITH_ORDER if k != "szablon"), extra[0]))
    given = sc.get("parametry", {})
    if not isinstance(given, dict):
        raise ValueError("parametry: obiekt {nazwa: wartość}")
    given = with_aliases(tpl, given)
    body = _body(tpl)
    defaults = tpl.get("parametry") or {}
    names = template_params(tpl)
    unknown = sorted(set(given) - set(names))
    if unknown and not lenient:
        raise ValueError("szablon %s nie ma parametru „%s”" % (name, unknown[0]))
    if unknown:
        given = {k: v for k, v in given.items() if k not in unknown}
        if meta is not None:
            meta["dropped"] = unknown
    limits = tpl.get("limity") or {}
    given = coerce_params(tpl, given)
    bad = None                            # (parametr, opis błędu): pierwszy błąd wartości posta
    for k, v in given.items():
        try:
            _check_value(k, v, limits)
        except ValueError as e:
            bad = bad or (k, str(e))
    for k in tpl.get("wymagane") or []:
        v = given.get(k)
        if bad is None and (v is None or (isinstance(v, str) and not v.strip())):
            bad = (k, "brak parametru „%s” (wymagany w szablonie %s: treść tego posta)" % (k, name))
    if bad is not None:
        info = {}
        for vals in (given, {k: v for k, v in given.items() if k != bad[0]}):   # błędna wartość w polu do poprawy
            try:
                _template_meta(tpl, name, body, sc, vals, info, placeholder=True)
                break
            except ValueError:
                info = {}
        raise ScenarioError(bad[1], info, bad[0])
    params = dict(defaults, **given)
    for k, v in defaults.items():
        if k not in given:
            _check_value(k, v, limits)
    out = _as_text(fill(body, params))
    for key in ("plansza_startowa", "plansza_koncowa"):
        if key in sc:
            mine, base = sc[key], out.get(key)
            out[key] = dict(base, **mine) if isinstance(mine, dict) and isinstance(base, dict) else mine
    if "muzyka" in sc:                    # podkład tego filmu zamiast podkładu z szablonu albo marki
        out["muzyka"] = sc["muzyka"]
    left = _leftover(out)
    if left:
        raise ValueError("niepodstawiony znacznik %s (nazwy parametrów: małe litery, cyfry, _)" % left)
    if meta is not None:
        _template_meta(tpl, name, body, sc, given, meta, out=out)
    return out, name


def _template_meta(tpl, name, body, sc, given, meta, out=None, placeholder=False):
    """Opis filmu z szablonu dla panelu: parametry (etykieta, wartość, grupa, limit), mapa pól, opis szablonu.
    placeholder: film się nie rozwinął (błąd wartości posta), więc brakujące parametry dostają pustą wartość tylko
    do zbudowania mapy pól."""
    defaults = tpl.get("parametry") or {}
    names = template_params(tpl)
    limits = tpl.get("limity") or {}
    params = dict(defaults, **given)
    if out is None:
        safe = {k: params.get(k, "") for k in names}
        out = _as_text(fill(body, safe))
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
        if k in fields.get("list", []):
            item["list"] = True          # punkty listy: w panelu każdy w osobnym wierszu (zapis: „; ”)
        if k in fields.get("images", []):
            item["image"] = True         # obraz planszy: w panelu wgranie pliku zamiast wpisywania nazwy
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
                required=list(tpl.get("wymagane") or []), kind=kind_of(tpl))
    return meta


def with_aliases(tpl, given):
    """Parametry posta po zmianie nazwy parametru w szablonie ("aliasy": {stara: obecna}): stara nazwa liczy się jak
    obecna (gdy post ma obie, wygrywa obecna)."""
    al = tpl.get("aliasy") or {}
    out = {k: v for k, v in given.items() if k not in al}
    for k, v in given.items():
        if k in al:
            out.setdefault(al[k], v)
    return out


def coerce_params(tpl, given):
    """Wartość z formularza panelu (tekst) dla parametru, którego wartość przykładowa w szablonie jest liczbą: liczba
    (np. "5" → 5 w polu czas, "4,5" → 4.5). Tylko zapis cyframi (bez „nan”, „inf”, „1e400”, „1_0”): inny tekst
    zostaje tekstem (kontrola zgłosi błąd w polu), a w scenariuszu nie powstaje NaN ani Infinity."""
    defaults = tpl.get("parametry") or {}
    numeric = _numeric_params(_body(tpl))
    out = dict(given)
    for k, v in given.items():
        if isinstance(v, str) and (_num(defaults.get(k)) or k in numeric) and NUMBER_RE.fullmatch(v.strip()):
            num = float(v.strip().replace(",", "."))
            if not math.isfinite(num):
                continue
            out[k] = int(num) if num.is_integer() and isinstance(defaults.get(k, 0), int) else num
    return out


NUMERIC_KEYS = ("czas", "pauza", "limit")


def _numeric_params(value, out=None):
    """Parametry, które w treści szablonu są całą wartością pola liczbowego (czas, pauza, limit): wartość z formularza
    panelu staje się liczbą także wtedy, gdy parametr nie ma przykładu w szablonie."""
    out = set() if out is None else out
    if isinstance(value, dict):
        for k, v in value.items():
            m = PARAM_RE.fullmatch(v.strip()) if k in NUMERIC_KEYS and isinstance(v, str) else None
            if m:
                out.add(m.group(1))
            else:
                _numeric_params(v, out)
    elif isinstance(value, list):
        for v in value:
            _numeric_params(v, out)
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
          "markup": [], "list": [], "images": []}
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
            if c.get("uklad") == "lista" and tw and tn[0] not in fm["list"]:
                fm["list"].append(tn[0])
            on, ow = _uses(c.get("obraz"))
            if ow and on[0] not in fm["images"]:
                fm["images"].append(on[0])       # obraz planszy z parametru: w panelu wgranie pliku
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
            try:                       # podgląd z wartości przykładowych (parametr bez przykładu: bez podglądu)
                body = _as_text(fill(_body(tpl), tpl.get("parametry") or {}))
            except ValueError:
                body = {}
            first = next((c for key in ("plansze", "plansze_przed") for c in (body.get(key) or [])
                          if isinstance(c, dict)), None)
            item["preview"] = {"text": str(first.get("tekst") or "")[:120], "caption": str(first.get("podpis") or "")[:80],
                               "layout": str(first.get("uklad") or "")} if first else None
            if not first and kind_of(tpl) == "pokaz" and body:      # pokaz bez plansz przed: hak i kadr nagrania
                hook = body.get("plansza_startowa")
                cap = next((str(k.get("napis")) for k in body.get("kroki") or [] if isinstance(k, dict)
                            and k.get("napis")), "")
                item["preview"] = {"text": "", "caption": cap[:80], "layout": "", "page": True,
                                   "hook": str(hook.get("tytul") or "")[:80] if isinstance(hook, dict) else ""}
            raw_body = _body(tpl)
            item["layouts"] = sorted({str(c.get("uklad")) for key in ("plansze", "plansze_przed", "plansze_po")
                                      for c in (raw_body.get(key) or []) if isinstance(c, dict) and c.get("uklad")})
            # plansza startowa marki (z nazwą marki): nie false i nie własny tytuł (hak posta)
            item["intro"] = raw_body.get("plansza_startowa", True) is not False and not (
                isinstance(raw_body.get("plansza_startowa"), dict) and raw_body["plansza_startowa"].get("tytul"))
            bad = template_check(tpl)
            if bad:
                item["error"] = "szablon %s: %s" % (name, bad)
            req = list(tpl.get("wymagane") or [])
            defaults = tpl.get("parametry") or {}
            imgs = [n for key in ("plansze", "plansze_przed", "plansze_po") for c in (raw_body.get(key) or [])
                    if isinstance(c, dict) for n in _uses(c.get("obraz"))[0]]
            # szablon wymaga danych, których agent nie zmyśli (cytat, zdjęcie, fakt): przykład w nawiasach albo obraz
            needs = [k for k in req if k in imgs or str(defaults.get(k, "")).lstrip("*„").startswith("[")]
            item["needsData"] = bool(needs)
            # czego szablon potrzebuje od właściciela (etykiety pól; obraz: zrzut albo zdjęcie do wgrania)
            item["needs"] = [{"label": labels.get(k) or k.replace("_", " "), "image": k in imgs} for k in needs]
            item.update(kind=kind_of(tpl), desc=str(tpl.get("opis") or "")[:400], params=params,
                        forOwner=str(tpl.get("dla_wlasciciela") or "").strip()[:300],
                        title=template_title(tpl, name), required=list(tpl.get("wymagane") or []),
                        labels={k: labels.get(k) or k.replace("_", " ") for k in params})
        except ValueError as e:
            item["error"] = str(e)
        item["kindLabel"] = KINDS[item["kind"]]
        item["kindHelp"] = KIND_HELP.get(item["kind"], "")
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
        need = READ_BASE + (text + cap) / CARD_CPS
        default = CARD_DEFAULT if cap else CARD_SHORT
    given = float(c["czas"]) if _num(c.get("czas")) else default
    return round(min(CARD_TIME[1], max(given, need)), 2), round(need, 1)


def brand_time(card, which, hook=False):
    """Czas planszy startowej albo końcowej: podany (albo CARD_TIMES), wydłużony do czasu czytania tytułu,
    podtytułu i adresu (1,2 s + 15 znaków/s) plus przejście, które zabiera koniec planszy. hook: plansza startowa
    z hakiem posta, stoi od pierwszej klatki (HOOK_BASE zamiast READ_BASE). Plansza końcowa bez podanego czasu
    najwyżej END_MAX: tytuł, podtytuł i adres wchodzą po kolei, więc widz czyta je w trakcie, a długo stojące
    wezwanie traci widzów. (czas, potrzebny)."""
    chars = sum(len(str(card.get(k) or "")) for k in ("tytul", "podtytul", "adres"))
    # hak czyta się także w pierwszej połowie przejścia (treść następnego klipu wchodzi dopiero w drugiej)
    need = (HOOK_BASE if hook else READ_BASE) + chars / READ_CPS + (XFADE / 2 if hook else XFADE)
    given = float(card["czas"]) if _num(card.get("czas")) else CARD_TIMES[which]
    sec = min(CARD_TIME[1], max(given, need))
    if which == "plansza_koncowa" and not _num(card.get("czas")):
        sec = min(sec, max(given, END_MAX))
        need = min(need, sec)
    return round(sec, 2), round(need, 1)


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
            warnings.append("Pierwsza plansza (hak) trwa %s; widz decyduje w pierwszych 3 s. Skróć hak do %d znaków"
                            "%s." % (sec_text(sec), HOOK_CHARS, " razem z podpisem albo usuń podpis" if c.get("podpis")
                                                               else ""))
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
        # parametr bez przykładu w szablonie: wartości zastępcze (tekst, liczba, plik); któraś usuwa błąd = winne pole
        for alt in ([defaults[k]] if k in defaults else list(DUMMIES)):
            trial = dict(raw, parametry=dict(given, **{k: alt}))
            try:
                sc, name = expand(trial, studio, lenient=True)
            except ValueError:
                continue
            errs = validate_scenario(sc, template=True)
            if not errs or errs[0] != error:
                return k
    return ""


OVERRIDES = ("plansza_startowa", "plansza_koncowa", "muzyka")   # pola posta nadpisujące szablon (poza parametrami)


def _override_culprit(raw, studio, error):
    """Pole posta nadpisujące szablon (plansza startowa, końcowa, muzyka), które powoduje błąd: bez niego błąd
    znika. "" gdy błąd jest w szablonie."""
    for key in OVERRIDES:
        if key not in raw or not error.startswith(key):
            continue
        trial = {k: v for k, v in raw.items() if k != key}
        try:
            sc, _name = expand(trial, studio, lenient=True)
        except ValueError:
            continue
        if error not in validate_scenario(sc, template=True):
            return key
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
    recent = []                           # szablony ostatnich filmów (najnowszy pierwszy): rotacja A-B-A-B
    for n in earlier:
        try:
            other = _load_json(os.path.join(base, n, SCENARIO))
        except (OSError, ValueError):
            continue
        if not isinstance(other, dict):
            continue
        if len(recent) < REPEAT_WINDOW:
            recent.append((n[:10], other.get("szablon")))
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
    same = [d for d, t in recent if t == name]
    if len(same) >= 2 and not (recent and recent[0][1] == name):
        out.append("Ten szablon był w %d z %d ostatnich filmów (%s). Widz zobaczy ten sam układ co kilka dni: użyj "
                   "innego szablonu albo poproś o nowy w Studiu filmów." % (len(same), len(recent),
                                                                         ", ".join(_day_label(d) for d in same)))
    for k, d in hits.items():
        out.append("„%s” taki sam jak w filmie z %s. Podaj inną treść, żeby filmy się nie powtarzały."
                   % (labels.get(k, k), _day_label(d)))
    return out


REPEAT_WINDOW = 4                         # tyle ostatnich filmów projektu sprawdza ostrzeżenie o rotacji szablonów


def prepare_raw(raw, folder):
    """(scenariusz rozwinięty, marka, opis) dla scenariusza raw posta w folder. ValueError z opisem po polsku
    (ScenarioError, gdy po podstawieniu szablonu: z parametrami dla panelu i nazwą winnego parametru)."""
    studio = studio_dir(folder)
    meta = {}
    sc, name = expand(raw, studio, meta, lenient=True)
    errors = validate_scenario(sc, template=bool(name))
    if errors:
        if not name:
            raise ValueError(errors[0])
        culprit = _culprit(raw, studio, errors[0])
        labels = {p["name"]: p["label"] for p in meta.get("params", [])}
        if culprit:
            raise ScenarioError("parametr „%s”, pole „%s”: %s" % (culprit, labels.get(culprit, culprit), errors[0]),
                                meta, culprit)
        if _override_culprit(raw, studio, errors[0]):     # pole nadpisane w poście, nie błąd szablonu
            raise ScenarioError("scenariusz posta: %s" % errors[0], meta)
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
    song = music_name(folder, brand, sc)
    if song and isinstance(sc.get("muzyka"), str):        # podkład wybrany w scenariuszu: plik musi być w studiu
        mpath = os.path.join(studio, song)
        bad = media_error(mpath, "audio") if os.path.isfile(mpath) and _inside(mpath, studio) else \
            "brak pliku studio/%s" % song
        if bad:
            raise ValueError("muzyka: %s" % bad)
    info = {"kind": kind, "template": name, "templateTitle": meta.get("title", ""),
            "templateDesc": meta.get("desc", ""), "templateOwner": meta.get("owner", ""),
            "params": meta.get("params", []), "fields": meta.get("fields"),
            "intro": bool(intro), "outro": bool(outro), "warnings": [], "music": bool(song), "musicName": song,
            # podkład wybrany dla tego filmu: plik, "off" (bez muzyki) albo "" (z listy marki na zmianę)
            "musicChoice": sc["muzyka"] if isinstance(sc.get("muzyka"), str) else "off" if sc.get("muzyka") is False
            else "",
            "editable": [], "before": [], "after": []}
    stock, total = meta.get("stock") or (0, 0)
    for k in meta.get("dropped") or []:
        info["warnings"].append("Szablon nie ma już pola „%s”: ta wartość posta jest pomijana. Usuń ją ze scenariusza "
                                "albo przekaż agentowi." % k)
    try:
        info["warnings"] += [w + "." for w in brand_warnings(_load_json(os.path.join(studio, BRAND)))]
    except (OSError, ValueError):
        pass
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
        if own_hook and sec > HOOK_MAX + XFADE / 2:
            info["warnings"].append("Hak na początku trwa %s, zanim widz zobaczy %s; widz decyduje w pierwszych 3 s. "
                                    "Skróć go do %d znaków." % (sec_text(sec), "stronę" if kind == "pokaz" else
                                                                "treść", HOOK_CHARS))
        info[key] = {"title": card.get("tytul", ""), "subtitle": card.get("podtytul", ""),
                     "address": card.get("adres", ""), "seconds": sec, "hook": own_hook}
        pending = (brand.get("do_potwierdzenia") or {}).get(which)
        own = sc.get(which) if isinstance(sc.get(which), dict) else {}
        if pending and not any(own.get(k) for k in ("tytul", "podtytul", "adres")):   # tekst marki, nie posta
            info[key]["pending"] = pending
            info["warnings"].append("%s marki jest tymczasowa (do potwierdzenia: %s). Film wyjdzie z tym tekstem."
                                    % (CARD_NAMES[which], pending.rstrip(".")))
    parts = [c["seconds"] for c in (info["introCard"], info["outroCard"]) if c]
    try:
        if kind == "objasnienie":
            info["cards"] = len(sc["plansze"])
            info["slides"] = _slides_info(sc["plansze"], folder, "plansza", info["warnings"], hook=not intro)
        else:
            info["before"] = _slides_info(sc.get("plansze_przed") or [], folder, "plansza przed pokazem",
                                          info["warnings"], hook=not intro)
            info["after"] = _slides_info(sc.get("plansze_po") or [], folder, "plansza po pokazie", info["warnings"])
    except ValueError as e:
        # brak albo błąd obrazu z parametru szablonu (np. zrzut ekranu): pole do wgrania pliku w panelu
        images = (meta.get("fields") or {}).get("images") or []
        values = meta.get("values") or {}
        culprit = next((k for k in images if values.get(k) and values[k] in str(e)), "")
        if name and culprit:
            raise ScenarioError(str(e), meta, culprit)
        raise
    if kind == "objasnienie":
        parts += [c["seconds"] for c in info["slides"]]
        if not name:          # plansze pisane w scenariuszu: tekst i podpis do zmiany w panelu
            info["editable"] = ["slides"]
    else:
        info["steps"] = len(sc.get("kroki") or [])
        info["captions"] = [str(k["napis"]) for k in sc.get("kroki") or [] if k.get("napis")]
        info["sequence"] = _sequence(sc)
        parts += [c["seconds"] for c in info["before"] + info["after"]]
        est, paused = _pokaz_timeline(sc)
        info["captionPauses"] = paused
        parts.append(est)
    if name:
        info["editable"] = ["params"]
    marked = [c for key in ("plansze", "plansze_przed", "plansze_po") for c in sc.get(key) or []
              if isinstance(c, dict) and "*" in str(c.get("tekst") or "")]
    if marked and _PILFont is None:
        _log_no_pil()
    info["seconds"] = round(sum(parts) - XFADE * max(0, len(parts) - 1), 1)
    if kind == "pokaz" and info["seconds"] > POKAZ_MAX:
        info["warnings"].append("Film potrwa około %d s, a ma trwać do %d s. Usuń część kroków albo napisów."
                                % (info["seconds"], POKAZ_MAX))
    if kind == "objasnienie" and info["seconds"] > OBJ_MAX:
        info["warnings"].append("Objaśnienie potrwa ok. %d s; na Reels lepiej do %d s (mniej plansz albo krótsze "
                                "teksty)." % (info["seconds"], OBJ_MAX))
    if not info["music"] and sc.get("muzyka") is not False:        # muzyka: false to świadomy film bez podkładu
        info["warnings"].append("Film bez muzyki: Reels i TikTok słabiej pokazują ciche filmy. Podkład dodasz w "
                                "Marketing → Studio filmów → projekt → „Dodaj podkład”.")
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


UNSET = object()


def apply_changes(folder, params=None, slides=None, music=UNSET):
    """Zmiana treści filmu z panelu bez agenta: parametry szablonu ({nazwa: wartość}) albo tekst i podpis plansz
    objaśnienia pisanego w scenariuszu ([{"n": numer od 1, "tekst", "podpis"}]). Pusty tekst w polu, które nie jest
    wymagane, przywraca wartość przykładową szablonu (klucz znika z parametrów posta). Zapis scenariusz.json tylko,
    gdy scenariusz po zmianie przechodzi te same kontrole co nagranie. music: podkład tego filmu (plik z listy marki,
    False: film bez muzyki, "": podkład z marki na zmianę). Zwraca opis filmu; ValueError z opisem."""
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
        try:
            tpl = load_template(studio_dir(folder), raw.get("szablon"))
        except ValueError:
            tpl = None               # brak szablonu: zgłosi prepare_raw niżej
        required = set((tpl or {}).get("wymagane") or [])
        if tpl is not None:          # pole spoza szablonu z panelu: błąd (post z usuniętym polem nagra się bez niego)
            known = set(template_params(tpl)) | set(tpl.get("aliasy") or {})
            bad = sorted(k for k in params if k not in known)
            if bad:
                raise ValueError("szablon %s nie ma parametru „%s”" % (raw.get("szablon"), bad[0]))
        for k, v in params.items():
            if not isinstance(v, (str, int, float)) or isinstance(v, bool) or (isinstance(v, float)
                                                                              and not math.isfinite(v)):
                raise ValueError("parametr „%s”: tekst" % k)
            v = v.strip() if isinstance(v, str) else v
            if v == "" and tpl is not None and k not in required and k in (tpl.get("parametry") or {}):
                cur.pop(k, None)     # puste pole: wartość przykładowa szablonu (także pod starą nazwą)
                for old, new in (tpl.get("aliasy") or {}).items():
                    if new == k:
                        cur.pop(old, None)
            else:
                cur[k] = v
        if tpl is not None:          # liczba z pola formularza zostaje liczbą (np. czas planszy z parametru)
            cur = coerce_params(tpl, with_aliases(tpl, cur))
        raw["parametry"] = cur
    if slides:
        cards = raw.get("plansze")
        if "szablon" in raw or raw.get("typ") != "objasnienie" or not isinstance(cards, list):
            raise ValueError("plansze zmienia się tu tylko w objaśnieniu bez szablonu")
        if not isinstance(slides, list):
            raise ValueError("zmiany plansz: lista [{n, tekst, podpis}]")
        for ch in slides:
            if not isinstance(ch, dict) or "n" not in ch:
                raise ValueError("zmiana planszy bez numeru (n)")
            n = ch["n"]
            if not (isinstance(n, int) and not isinstance(n, bool) and 1 <= n <= len(cards)
                    and isinstance(cards[n - 1], dict)):
                raise ValueError("plansza %s: nie ma takiej planszy (jest %d)" % (n, len(cards)))
            for key in ("tekst", "podpis"):
                if key in ch:
                    if not isinstance(ch[key], str):
                        raise ValueError("plansza %d: %s to tekst" % (n, key))
                    if key == "podpis" and not ch[key].strip():
                        cards[n - 1].pop("podpis", None)
                    else:
                        cards[n - 1][key] = ch[key].strip()
    if music is not UNSET:
        if music == "" or music is None:
            raw.pop("muzyka", None)
        elif music is False:
            raw["muzyka"] = False
        else:
            brand = load_brand(studio_dir(folder))[0]
            if not (isinstance(music, str) and music in music_list(brand.get("muzyka"))):
                raise ValueError("podkład: wybierz plik z listy podkładów marki")
            raw["muzyka"] = music
    try:
        _sc, _brand, info = prepare_raw(raw, folder)
    except ScenarioError as e:
        # brak pliku w innym polu obrazu (zrzuty wgrywa się po jednym): zapis tej zmiany, film nagra się po ostatnim
        img = next((p for p in e.meta.get("params") or [] if p["name"] == e.param and p.get("image")), None)
        if not img or e.param in (params or {}):
            raise
        info = {"seconds": 0, "error": str(e), "missing": img["label"]}
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
               ("scenariusz posta:", "Błąd w polu tego posta (plansza startowa, końcowa albo podkład), nie w szablonie. "
                                     "Przekaż agentowi do poprawy scenariusza posta."),
               ("muzyka:", "Podkład tego filmu jest niedostępny albo ma zły format. Wybierz inny podkład przy filmie "
                           "albo wgraj plik w Studiu filmów."),
               ("parametry: obiekt", "Dane filmu w scenariuszu mają zły format. Przekaż agentowi do poprawy."),
               ("ukryj:", "Lista elementów strony do ukrycia w pokazie ma zły format. Przekaż agentowi do poprawy."),
               ("obok „szablon”", "Scenariusz ma pole, którego film z szablonu nie przyjmuje (np. „typ”). "
                                  "Przekaż agentowi do poprawy."),
               ("przykład parametru", "Błąd w szablonie studia: wartość przykładowa nie mieści się w limicie. "
                                      "Przekaż agentowi do poprawy szablonu."),
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
               ("brak obrazu", "Brakuje obrazu do planszy (zrzutu ekranu albo zdjęcia)."),
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
            pm = next((p for p in e.meta["params"] if p["name"] == e.param), {})
            label = pm.get("label", "")
            if label and pm.get("image"):
                out["errorHint"] = "Brakuje pliku w polu „%s”: wgraj zrzut ekranu albo zdjęcie przyciskiem niżej." % label
            elif label and "wymagany w szablonie" in out["error"]:
                out["errorHint"] = "Brakuje treści tego posta: uzupełnij pole „%s”." % label
            elif label and out["error"].startswith("parametr „%s”: " % e.param):
                out["errorHint"] = "Popraw pole „%s” (%s)." % (label, out["error"].split(": ", 1)[1])
        try:
            raw = _load_json(os.path.join(folder, SCENARIO))
            out["template"] = str(raw.get("szablon") or "") if isinstance(raw, dict) else ""
            out["kind"] = kind_of(raw)
            if out["template"]:
                tpl = load_template(studio_dir(folder), out["template"])
                out["kind"], out["templateTitle"] = kind_of(tpl), template_title(tpl, out["template"])
        except (OSError, ValueError, AttributeError):
            pass
    out["limit"] = POKAZ_MAX if out["kind"] == "pokaz" else OBJ_MAX      # długość docelowa (próg ostrzeżenia)
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
        song = music_name(folder, brand, sc if isinstance(raw, dict) else {})
        if song and AUDIO_RE.match(song):
            studio_files.append(os.path.join(studio, song))
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
        # krótki przyimek i liczba („3 dotknięcia”, „10 opisów”, „12 h”) zostają z następnym słowem
        if (bare in GLUE or re.fullmatch(r"[0-9]+(?:[.,][0-9]+)?", bare)) and n < len(out) - 1:
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
    """Wiersze o podobnej długości: najmniejsza liczba wierszy, potem najmniejsza suma kwadratów luzu wierszy
    (bez wiersza z jednym krótkim słowem w środku tekstu wyśrodkowanego), przy remisie krótsza najdłuższa linia.
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
    stars = [0] * (n + 1)                # gwiazdki przed słowem j (nieparzysta liczba: wewnątrz wyróżnienia)
    for k, t in enumerate(toks):
        stars[k + 1] = stars[k] + t.count("*")
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
                # samotne krótkie słowo w wierszu, który nie jest ostatni: kara (w tekście na środku wygląda jak dziura)
                lone = (0.6 * maxw) ** 2 if j < n and j - i == 1 and w[i, j] < 0.5 * maxw else 0.0
                # koniec wiersza w środku wyróżnienia *…*: fraza rozdzielona na dwa wiersze (kara)
                split = (0.5 * maxw) ** 2 if j < n and stars[j] % 2 else 0.0
                score = (max(prev[0], w[i, j]), prev[1] + (maxw - w[i, j]) ** 2 + lone + split, i)
                if cand is None or (score[1], score[0]) < (cand[1], cand[0]):
                    cand = score
            if cand:
                best[k, j] = cand
    out, j = [], n
    for k in range(lines, 0, -1):
        i = best[k, j][2]
        out.append(joined(i, j))
        j = i
    return [ln.replace(NBSP, " ") for ln in reversed(out)]


def fit(text, font, maxw, sizes, max_lines, fewer=0.0):
    """(czcionka, wiersze): największy rozmiar z sizes, przy którym tekst mieści się w max_lines wierszach.
    fewer (np. 0.84): mniejszy rozmiar (do tej części największego pasującego), gdy daje mniej wierszy (tytuł
    w dwóch wierszach zamiast trzech)."""
    for n, size in enumerate(sizes):
        f = font.at(size)
        lines = wrap(text, f, maxw)
        if lines is not None and len(lines) <= max_lines:
            for smaller in sizes[n + 1:] if fewer and len(lines) > 1 else []:
                if smaller < size * fewer:
                    break
                g = font.at(smaller)
                other = wrap(text, g, maxw)
                if other is not None and len(other) < len(lines):
                    return g, other
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


def caption_filters(texts, captions, end, style, start_at=None, align="center", last_stop=None):
    """Napisy: [(od, tekst)], każdy do następnego; jedno pudełko pod wszystkimi wierszami, dół pudełka nad dolną
    strefą bezpieczną. style: marka["napisy"] + "font" (Font). start_at: wejście (pudełko i tekst płynnie od tej
    chwili, plansze objaśnienia); align "left": pudełko i tekst przy lewym marginesie (jak tekst planszy).
    last_stop: ostatni napis znika w tej chwili (przed przejściem do następnego klipu), inaczej stoi do końca."""
    out = []
    font = style["font"]
    size = int(style.get("rozmiar", 56))
    box_hex, alpha = style.get("tlo", "#2b1d12"), float(style.get("krycie", 0.85))
    box = _col(box_hex, alpha)
    color = _col(style.get("kolor", "#ffffff"))
    sizes = list(range(size, max(30, int(size * 0.7)) - 1, -2))
    bottom = SIZE[1] - SAFE_BOTTOM
    for n, (at, text) in enumerate(captions):
        stop = captions[n + 1][0] if n + 1 < len(captions) else (last_stop if last_stop is not None else end + 1)
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
        # wejście jak na planszach objaśnienia (pudełko narasta, tekst wjeżdża): jeden styl napisów w całym filmie
        out += _box_fade(bx, top, width, height, box_hex, alpha, begin, stop, steps=8, dur=0.3)
        for j, line in enumerate(lines):
            base = top + pad_y + int(f.size * 0.78) + j * line_h
            out.append(_draw(texts, line, f, color, tx, base, begin, ":enable='%s'" % on))
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
    try:
        r = subprocess.run(["ffmpeg", "-y", "-v", "error"] + args + codec + [out], capture_output=True, text=True,
                           timeout=ENCODE_TIMEOUT)
    except subprocess.TimeoutExpired:
        raise RuntimeError("montaż: ffmpeg nie skończył w %d s" % ENCODE_TIMEOUT)
    if r.returncode != 0:
        raise RuntimeError("montaż: " + (r.stderr.strip().splitlines() or ["ffmpeg"])[-1][:200])
    return out


def _clip(out, bg, dur, draws, image=None, bar=None, logo=None, first=False, fade_out=True, fade_from=None,
          zoom=False):
    """Plansza: tło w kolorze, opcjonalny obraz (image: (plik, y, maks. wysokość)), logo (logo: (plik, x, y,
    maks. wysokość), x="c" = środek), teksty, pasek postępu (bar: (kolor, y)) przez cały czas planszy.
    first: pierwszy klip filmu, obraz i logo widoczne od pierwszej klatki (miniatura). fade_out: treść gaśnie do
    koloru tła tuż przed przejściem do następnej planszy (FADE_OUT, kończy się w dur − XFADE), więc w przenikaniu
    jest samo tło i nie nakładają się dwa teksty; ostatni klip filmu bez tego. fade_from (y): gaśnie tylko treść
    poniżej tej linii (nagłówek z nazwą marki, licznik i pasek postępu planszy objaśnienia stoją bez mrugnięcia).
    bar: (kolor, y) albo (kolor, y, od, do): pasek rośnie od części od do części do szerokości przez czas planszy
    do początku przejścia (postęp całej serii plansz). zoom: obraz powoli się przybliża (zrzut ekranu)."""
    args = ["-f", "lavfi", "-i", "color=c=%s:s=%dx%d:r=30:d=%.2f" % (bg, SIZE[0], SIZE[1], dur)]
    graph, cur = [], "[0:v]"
    n = 1
    fade = "" if first else ",fade=t=in:st=0.1:d=0.4:alpha=1"
    if image:
        path, y, maxh = image
        args += media_input(path, dur)
        dims = _image_size(path, os.path.splitext(path)[1].lower().lstrip(".")) if zoom else None
        if dims and dims[1] > dims[0] * PORTRAIT:
            # pionowy zrzut telefonu: cała szerokość kadru, okno przesuwa się płynnie z góry na dół (pan), zamiast
            # mieścić cały ekran w 1/3 szerokości
            run = max(0.5, dur - XFADE - FADE_OUT - 0.9)
            graph.append("[%d:v]scale=w=%d:h=-2,crop=w=%d:h=%d:x=0:y='(ih-oh)*(0.5-0.5*cos(PI*clip((t-0.6)/%.2f,0,1)))'"
                         ",format=rgba%s[img]" % (n, TEXT_W, TEXT_W, maxh, run, fade))
        elif dims:
            # przybliżenie bez drgań: obraz powiększony 3× przed zoompan (położenie co 1/3 piksela), +10% przez planszę
            k = min(TEXT_W / dims[0], maxh / dims[1])
            w0, h0 = max(2, int(dims[0] * k) // 2 * 2), max(2, int(dims[1] * k) // 2 * 2)
            frames = max(1, int(dur * 30))
            graph.append("[%d:v]scale=w=%d:h=%d,zoompan=z='1+0.10*on/%d':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2'"
                         ":d=1:s=%dx%d:fps=30,format=rgba%s[img]" % (n, w0 * 3, h0 * 3, frames, w0, h0, fade))
        else:
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
    fading = fade_out and dur > XFADE + FADE_OUT + 0.5
    if fading and fade_from is not None:       # treść gaśnie pod nagłówkiem, nagłówek i pasek zostają
        bg_hex = bg[2:8] if bg.startswith("0x") else bg
        graph.append("%s%s[faded]" % (cur, ",".join(_box_fade("0", fade_from, SIZE[0], SIZE[1] - fade_from,
                                                                 "#" + bg_hex, 1.0, dur - XFADE - FADE_OUT, dur + 1,
                                                                 steps=6, dur=FADE_OUT))))
        cur = "[faded]"
    if bar:
        color, y = bar[:2]
        f0, f1 = (bar[2], bar[3]) if len(bar) >= 4 else (0.0, 1.0)
        run = max(0.5, dur - XFADE) if len(bar) >= 4 else dur
        args += ["-f", "lavfi", "-i", "color=c=%s:s=%dx8:r=30:d=%.2f" % (color, SIZE[0], dur)]
        graph.append("%s[%d:v]overlay=x='-w+w*min(%.4f,%.4f+%.4f*t/%.2f)':y=%d:shortest=1[bar]"
                     % (cur, n, f1, f0, f1 - f0, run, y))
        cur = "[bar]"
    if fading and fade_from is None:
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


def brand_card(brand, card, which, work, texts, name, first=False, studio=None, hook=False, delay=0.0):
    """Plansza startowa albo końcowa (kolory odwrócone: tło = kolor tekstu marki). Logo (gdy jest), tytuł, podtytuł,
    kreska akcentu i adres w jednym bloku na środku kadru (poza strefami zasłanianymi przez interfejs aplikacji).
    Podtytuł i adres w kolorze tekstu planszy (na startowej co najmniej 52 px, na końcowej, gdzie są wezwaniem do
    działania, co najmniej rozmiar napisów); akcent tylko na kresce. first: tekst stoi od pierwszej klatki
    (miniatura, hak). hook: plansza startowa z hakiem posta (krótszy czas, brand_time). delay (s): treść wchodzi
    później (plansza po planszy w innym kolorze tła: tytuł nie wjeżdża w trakcie przenikania tła)."""
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
    at = lambda t: None if still else t + delay  # noqa: E731
    draws = []
    y = top + (logo_h + 60 if logo else 0)
    draws += [_draw(texts, ln, title_f, fg, "(w-text_w)/2", y + int(title_f.size * 0.9) + j * t_h,
                    at(0.05 + (0.06 if quick else 0.12) * j)) for j, ln in enumerate(title)]
    y += len(title) * t_h
    if rule:
        draws.append("drawbox=x=(iw-120)/2:y=%d:w=120:h=6:color=%s:t=fill%s"
                     % (y + 22, accent, "" if still else ":enable='gte(t,%.2f)'" % (0.3 + delay)))
        y += 40
    if sub:
        y += 36
        draws += [_draw(texts, ln, sub_f, fg, "(w-text_w)/2", y + int(sub_f.size * 0.9) + j * s_h,
                        at((0.15 if quick else 0.4) + 0.1 * j)) for j, ln in enumerate(sub)]
        y += len(sub) * s_h
    if card.get("adres"):
        draws.append("drawbox=x=(iw-160)/2:y=%d:w=160:h=6:color=%s:t=fill%s"
                     % (y + 44, accent, "" if still else ":enable='gte(t,%.2f)'" % (0.5 + delay)))
        draws.append(_draw(texts, card["adres"], addr_f, fg, "(w-text_w)/2", y + 136, at(0.55)))
    return _clip(os.path.join(work, name), bg, dur, draws, logo=(logo, "c", top, logo_h) if logo else None,
                 first=first, fade_out=not outro)


LAYOUTS = {"tekst": "tekst od lewej, podpis w pudełku", "srodek": "tekst na środku",
           "liczba": "duża liczba albo słowo *w gwiazdkach* na środku, opis pod nią",
           "cytat": "cytat z dużym cudzysłowem, podpis jako autor",
           "lista": "lista do 5 punktów (oddzielonych średnikiem) wchodzących po kolei",
           "zrzut": "duży obraz pod nagłówkiem, tekst pod nim: pionowy zrzut telefonu na całą szerokość, przesuwany "
                    "z góry na dół; zdjęcie albo poziomy zrzut z powolnym przybliżeniem"}
LIST_MAX = 5
PORTRAIT = 1.25                   # obraz wyższy niż szerszy o tyle: zrzut telefonu (układ „zrzut”: pełna szerokość i pan)


def _layout_center(c):
    """Plansza, która sama nadaje się na środek: bez podpisu i obrazu, pytanie albo krótkie hasło."""
    return not c.get("obraz") and not c.get("podpis") and (_plain(c["tekst"]).strip().endswith("?")
                                                          or len(_plain(c["tekst"])) <= 32)


def layouts(cards):
    """Układ każdej planszy serii: "uklad" z planszy, inaczej według serii, nie długości jednego tekstu: plansza
    otwierająca (pytanie, krótkie hasło) może być na środku, pozostałe są na środku tylko wtedy, gdy wszystkie się
    do tego nadają (kroki 1, 2 i 3 w tym samym układzie)."""
    rest = cards[1:]
    rest_center = bool(rest) and all(_layout_center(c) for c in rest)
    out = []
    for i, c in enumerate(cards):
        own = c.get("uklad")
        if own in LAYOUTS:
            out.append(own)
        elif c.get("obraz"):
            out.append("tekst")
        elif _layout_center(c) and (i == 0 or rest_center):
            out.append("srodek")
        else:
            out.append("tekst")
    return out


def _number_split(text):
    """Plansza „liczba”: (liczba, opis) z pierwszego *wyróżnienia* (albo pierwszego słowa)."""
    m = re.search(r"\*([^*]+)\*", text)
    if m:
        return m.group(1).strip(), (text[:m.start()] + text[m.end():]).replace("*", "").strip(" ,.:–-")
    head, _, tail = text.strip().partition(" ")
    return head.replace("*", ""), tail.replace("*", "").strip()


def explainer_clips(cards, brand, work, texts, folder=None, prefix="plansza", counter=True, first=False,
                    fade_last=False, delay_first=0.0):
    """Plansze objaśnienia, każda osobnym klipem. Nazwa marki (albo logo w rogu) i licznik pod górną strefą,
    pasek postępu całej serii w kolorze akcentu pod nimi: te elementy stoją bez wygaszania, gaśnie tylko treść.
    Układ planszy (layouts): tekst od lewej (wchodzi wiersz po wierszu i powoli dryfuje, podpis w pudełku przy lewym
    marginesie nad dolną strefą), środek, liczba, cytat, lista punktów, zrzut (duży obraz z przybliżeniem).
    cards: lista plansz (także plansze_przed / plansze_po pokazu). first: pierwsza plansza jest pierwszym klipem
    filmu, więc tekst stoi od pierwszej klatki (hak, miniatura). fade_last: po ostatniej planszy idzie plansza
    w innym kolorze tła (plansza końcowa marki), więc gaśnie cała klatka, także nazwa marki, licznik i pasek
    (w przenikaniu tła nie zostaje nagłówek na wchodzącej planszy). delay_first (s): treść pierwszej planszy wchodzi
    później (plansza wsuwa się po planszy w innym kolorze tła: tekst dopiero po przejściu)."""
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
    plan = layouts(cards)
    total = sum(card_time(c, hook=first and i == 0)[0] for i, c in enumerate(cards))
    done = 0.0
    bottom = SIZE[1] - SAFE_BOTTOM
    for i, c in enumerate(cards):
        still = first and i == 0
        dur = card_time(c, hook=still)[0]
        lay = plan[i]
        img = image_path(folder, c["obraz"]) if folder and c.get("obraz") else None
        d0 = 0.0 if still or i else float(delay_first or 0.0)
        at = lambda t: None if still else t + d0  # noqa: E731
        draws = []
        if brand.get("nazwa") and not corner:
            draws.append(_draw(texts, brand["nazwa"], small, head_col, str(MARGIN), head))
        if counter and len(cards) > 1:
            # w czasie przenikania licznik pokazuje jeszcze poprzedni numer (bez mieszania „1/4” z „2/4”)
            cnt_col = _col(readable(bg_hex, kol.get("akcent2"), kol["akcent"], fg_hex))
            if i:
                draws.append(_draw(texts, "%d/%d" % (i, len(cards)), small, cnt_col, "w-%d-text_w" % MARGIN, head,
                                   extra=":enable='lt(t,%.2f)'" % XFADE))
            draws.append(_draw(texts, "%d/%d" % (i + 1, len(cards)), small, cnt_col, "w-%d-text_w" % MARGIN, head,
                               extra=":enable='gte(t,%.2f)'" % XFADE if i else ""))
        caption_left = True
        if lay == "liczba":
            num, rest = _number_split(c["tekst"])
            nf, nl = fit(num, _font(brand, "tytul", 300), TEXT_W, list(range(300, 119, -20)), 1)
            df, dl = fit(rest, _font(brand, "tytul", 76), TEXT_W, list(range(76, 51, -4)), 3, fewer=0.84) \
                if rest else (None, [])
            nh, dh = int(nf.size * 1.05), (int(df.size * 1.2) if df else 0)
            block = nh + (40 + len(dl) * dh if dl else 0)
            top = max(530, (530 + bottom - (230 if c.get("podpis") else 80)) // 2 - block // 2)
            draws += [_draw(texts, ln, nf, accent, "(w-text_w)/2", top + int(nf.size * 0.92), at(0.1))
                      for ln in nl]
            draws += [_draw(texts, ln, df, fg, "(w-text_w)/2", top + nh + 40 + int(df.size * 0.92) + j * dh,
                            at(0.45 + 0.1 * j)) for j, ln in enumerate(dl)]
        elif lay == "cytat":
            f, lines = fit(c["tekst"].strip().strip("„”\""), _font(brand, "tytul", 84), TEXT_W - 40,
                           list(range(84, 55, -4)), 5)
            line_h = int(f.size * 1.22)
            qf = _font(brand, "tytul", 260)
            block = 170 + len(lines) * line_h + (110 if c.get("podpis") else 0)
            top = max(500, (500 + bottom - 80) // 2 - block // 2)
            # duży górny cudzysłów nad tekstem (znak cytatu, nie zamknięcie); wchodzi po przejściu z poprzedniej planszy
            draws.append(_draw(texts, "“", qf, accent, str(MARGIN - 10), top + 190, at(XFADE)))
            state = False
            for j, ln in enumerate(lines):
                part, state = _draw_line(texts, ln, f, fg, accent, str(MARGIN), top + 170 + int(f.size * 0.92)
                                         + j * line_h, at(0.2 + 0.1 * j), state=state)
                draws += part
            if c.get("podpis"):
                af = _font(brand, "tekst", 52)
                draws.append(_draw(texts, "— " + c["podpis"], af, accent, str(MARGIN),
                                   top + 170 + len(lines) * line_h + 80, at(CAPTION_AT if not still else 0.4)))
            caption_left = False
        elif lay == "lista":
            items = [x.strip() for x in c["tekst"].split(";") if x.strip()][:LIST_MAX]
            sizes = list(range(76, 51, -4))
            f = _font(brand, "tytul", sizes[0])
            for size in sizes:
                f = f.at(size)
                if all(wrap(x, f, TEXT_W - 110) and len(wrap(x, f, TEXT_W - 110)) <= 2 for x in items):
                    break
            rows = [wrap(x, f, TEXT_W - 110) or [x] for x in items]
            line_h, gap = int(f.size * 1.18), int(f.size * 0.55)
            block = sum(len(r) for r in rows) * line_h + gap * (len(rows) - 1)
            top = max(530, (530 + bottom - (230 if c.get("podpis") else 80)) // 2 - block // 2)
            y = top
            step = min(0.6, max(0.3, (dur - 1.5) / max(1, len(rows))))
            for k, r in enumerate(rows):
                when = None if still and k == 0 else 0.2 + step * k + d0
                draws.append(_draw(texts, "%d." % (k + 1), f, accent, str(MARGIN), y + int(f.size * 0.92), when))
                state = False
                for j, ln in enumerate(r):
                    part, state = _draw_line(texts, ln, f, fg, accent, str(MARGIN + 110),
                                             y + int(f.size * 0.92) + j * line_h, when, state=state)
                    draws += part
                y += len(r) * line_h + gap
        else:
            center = lay == "srodek"
            big = lay == "zrzut" and img
            sizes, max_lines = (list(range(64, 47, -4)), 2) if big else (list(range(80, 55, -4)), 3) if img else \
                (list(range(104, 67, -4)), 4) if center else (list(range(92, 59, -4)), 5)
            f, lines = fit(c["tekst"].strip(), _font(brand, "tytul", sizes[0]), TEXT_W, sizes, max_lines,
                           fewer=0.84 if center else 0.0)
            line_h = int(f.size * 1.18)
            region = (1330, bottom - (230 if c.get("podpis") else 60)) if big else (1010, 1330) if img else \
                (530, bottom - (230 if c.get("podpis") else 80))
            block = len(lines) * line_h
            top = max(region[0], (region[0] + region[1]) // 2 - block // 2)
            rule_x = "(iw-120)/2" if center else str(MARGIN)
            if not big:
                draws.append("drawbox=x=%s:y=%d:w=120:h=10:color=%s:t=fill%s"
                             % (rule_x, top - 56, accent, "" if still else ":enable='gte(t,%.2f)'" % (0.1 + d0)))
            step = min(0.12, 0.6 / max(1, len(lines)))
            state = False
            for j, ln in enumerate(lines):
                x = str(int(round((SIZE[0] - f.width(_plain(ln))) / 2))) if center else str(MARGIN)
                part, state = _draw_line(texts, ln, f, fg, accent, x, top + int(f.size * 0.92) + j * line_h,
                                         None if still else 0.15 + step * j + d0, drift=(dur, 18), state=state)
                draws += part
        if c.get("podpis") and caption_left:
            n_items = len(draws)
            at_cap = HOOK_CAPTION_AT if still else min(dur - 1.0, max(CAPTION_AT, 0.45 + 0.1 * min(6, n_items)) + d0)
            draws += caption_filters(texts, [(at_cap, c["podpis"])], dur, style, start_at=at_cap, align="left")
        image = None
        if img:
            image = (img, 470, 820) if lay == "zrzut" else (img, 470, 500)
        f0, f1 = done / total if total else 0.0, (done + dur) / total if total else 1.0
        done += dur
        out.append(_clip(os.path.join(work, "%s-%02d.mp4" % (prefix, i + 1)), bg, dur, draws, image=image,
                         bar=(accent, BAR_Y, f0, f1), logo=(corner, MARGIN, HEAD_Y - 58, 64) if corner else None,
                         first=still, fade_from=None if fade_last and i == len(cards) - 1 else BAR_Y + 14,
                         zoom=lay == "zrzut" and bool(img)))
    return out


PROBE_DEMUXER = dict(DEMUXER, mp4="mov", webm="matroska")    # klipy montażu i nagranie Playwright
PROBE_TIMEOUT = 30                # s: ffprobe jednego pliku
ENCODE_TIMEOUT = 300              # s: jedno wywołanie ffmpeg (także `film.py nagraj` z wiersza poleceń)


def _duration(path):
    """Długość pliku (s) z ffprobe: tylko pliki lokalne, demuxer z rozszerzenia (jak media_input), z limitem czasu;
    0.0, gdy się nie da."""
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    fmt = ["-f", PROBE_DEMUXER[ext]] if ext in PROBE_DEMUXER else []
    try:
        probe = subprocess.run(["ffprobe", "-v", "error", "-protocol_whitelist", "file"] + fmt +
                               ["-show_entries", "format=duration", "-of", "csv=p=0", path],
                               capture_output=True, text=True, timeout=PROBE_TIMEOUT)
    except (OSError, subprocess.TimeoutExpired):
        return 0.0
    try:
        return float(probe.stdout.strip() or 0)
    except ValueError:
        return 0.0


def far_bg(a, b):
    """Tła o dużej różnicy jasności (jasna plansza objaśnienia i ciemna plansza marki): przenikanie przeszłoby przez
    szarość, więc przejście to przesunięcie."""
    try:
        return bool(a and b) and contrast(str(a), str(b)) >= 3
    except (TypeError, ValueError):
        return False


def transition(a, b):
    """Przejście między klipami o tłach a i b (#rrggbb albo None = nagranie strony). Między planszami w podobnych
    kolorach: przenikanie (treść poprzedniej planszy najpierw gaśnie do jej tła, _clip fade_out, więc teksty się nie
    nakładają). Jasne tło ↔ ciemne: następna plansza wsuwa się od dołu (bez brudnej szarości w przenikaniu), a jej
    treść wchodzi po przejściu. Z nagraniem strony: przez czerń."""
    if a and b:
        return "slideup" if far_bg(a, b) else "fade"
    return "fadeblack"


def assemble(parts, out, work, music=None, previous=None):
    """Skleja klipy [(plik, czas)] albo [(plik, czas, tło)] przejściem (XFADE) w film.mp4 z dźwiękiem (podkład
    z normalizacją głośności albo cisza); zapis przez plik tymczasowy. previous: dotychczasowy film zostaje pod tą
    nazwą (porównanie wersji w panelu)."""
    tmp = os.path.join(work, "film.mp4")
    parts = [tuple(p) + (None,) * (3 - len(p)) for p in parts]
    args, graph = [], []
    for i, (p, _d, _bg) in enumerate(parts):
        args += ["-protocol_whitelist", "file", "-i", p]
        graph.append("[%d:v]settb=AVTB,fps=30,setsar=1,format=yuv420p[v%d]" % (i, i))
    prev, total = "[v0]", parts[0][1]
    for i in range(1, len(parts)):
        graph.append("%s[v%d]xfade=transition=%s:duration=%.2f:offset=%.3f[x%d]"
                     % (prev, i, transition(parts[i - 1][2], parts[i][2]), XFADE, total - XFADE, i))
        prev, total = "[x%d]" % i, total + parts[i][1] - XFADE
    graph.append("%snull[vout]" % prev)
    n = len(parts)
    if music:
        mdur = _duration(music)
        src = "[%d:a]" % n
        if LOOP_X * 2 < mdur < total + 0.5:
            # utwór krótszy niż film: kolejne kopie z przenikaniem na szwie (bez słyszalnego cięcia pętli)
            copies = min(8, max(2, int(math.ceil((total - LOOP_X) / (mdur - LOOP_X)))))
            for _ in range(copies):
                args += media_input(music, loop=False)
            for k in range(1, copies):
                graph.append("%s[%d:a]acrossfade=d=%.2f:c1=tri:c2=tri[m%d]" % (src, n + k, LOOP_X, k))
                src = "[m%d]" % k
        else:
            args += media_input(music)
        # głośność wyrównana do poziomu platform (ok. -14 LUFS, szczyty do -1,5 dBTP), potem wejście i wyciszenie
        graph.append("%satrim=0:%.3f,asetpts=PTS-STARTPTS,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000,"
                     "afade=t=in:d=0.5,afade=t=out:st=%.3f:d=1.5[aout]" % (src, total, max(0, total - 1.5)))
    else:
        args += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
        graph.append("[%d:a]atrim=0:%.3f[aout]" % (n, total))
    _encode(args + ["-filter_complex", ";".join(graph), "-map", "[vout]", "-map", "[aout]"], tmp, final=True,
            seconds=total)
    shutil.move(tmp, out + ".tmp")
    if previous and os.path.isfile(out):
        try:
            os.replace(out, previous)
        except OSError:
            pass
    os.replace(out + ".tmp", out)
    return out


def record(folder, expect_kind=None):
    """Nagrywa scenariusz do film.mp4 (pokaz albo objaśnienie, z planszami marki; pokaz także z planszami przed
    i po nagraniu strony), obok film.srt (napisy i teksty plansz z czasami) i film-4x5.mp4 (wersja do feedu).
    Zwraca ścieżkę filmu; błąd: wyjątek z opisem po polsku. expect_kind: rodzaj ustalony przy starcie (zmiana
    w trakcie: błąd)."""
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
        parts, subs = [], []          # subs: napisy każdej części [(od, do, tekst)] względem jej początku
        intro, outro = _card(brand, sc, "plansza_startowa"), _card(brand, sc, "plansza_koncowa")
        card_bg = lambda c: c.get("tlo") or kol["tekst"]  # noqa: E731
        card_text = lambda c: "\n".join(str(c.get(k)) for k in ("tytul", "podtytul", "adres") if c.get(k))  # noqa: E731
        if intro:
            hook = is_hook(sc)                  # hak: sam tekst, bez logo, krótszy czas
            parts.append(brand_card(brand, intro, "plansza_startowa", work, texts, "start.mp4", first=True,
                                    studio=None if hook else studio, hook=hook) + (card_bg(intro),))
            subs.append([(0.0, parts[-1][1] - XFADE, card_text(intro))])

        # po ostatniej planszy plansza końcowa w innym kolorze tła: cała klatka gaśnie, tytuł wchodzi po przejściu
        contrast_end = bool(outro) and str(card_bg(outro)).lower() != str(kol["tlo"]).lower()

        def slides(cards, prefix, counter=True, last=False):
            # po planszy w innym kolorze tła (hak, plansza marki) plansza wsuwa się, a tekst wchodzi po przejściu
            late = XFADE if parts and far_bg(parts[-1][2], kol["tlo"]) else 0.0
            out = [p + (kol["tlo"],) for p in explainer_clips(cards, brand, work, texts, folder, prefix, counter,
                                                              first=not parts, fade_last=last and contrast_end,
                                                              delay_first=late)]
            for c, p in zip(cards, out):
                subs.append([(0.15 if parts or p is not out[0] else 0.0, p[1] - XFADE,
                              _plain(c["tekst"]) + ("\n" + c["podpis"] if c.get("podpis") else ""))])
            return out
        if info["kind"] == "objasnienie":
            parts += slides(sc["plansze"], "plansza", last=True)
        else:
            if sc.get("plansze_przed"):
                parts += slides(sc["plansze_przed"], "przed", counter=False)
            clip, page_subs = record_page(folder, sc, brand, work)
            parts.append((clip, _duration(clip), None))
            subs.append(page_subs)
            if sc.get("plansze_po"):
                parts += slides(sc["plansze_po"], "po", counter=False, last=True)
        if outro:
            after_card = bool(parts) and parts[-1][2] is not None and contrast_end
            late = XFADE if after_card and far_bg(parts[-1][2], card_bg(outro)) else XFADE * 0.7 if after_card else 0.0
            parts.append(brand_card(brand, outro, "plansza_koncowa", work, texts, "koniec.mp4", studio=studio,
                                    delay=late) + (card_bg(outro),))
            subs.append([(0.05, parts[-1][1], card_text(outro))])
        song = music_name(folder, brand, sc)
        music = os.path.join(studio, song) if song else None
        out = assemble(parts, os.path.join(folder, "film.mp4"), work, music,
                       previous=os.path.join(folder, PREVIOUS))
        if song and not isinstance(sc.get("muzyka"), str):
            pin_music(folder, song)           # podkład z listy marki zostaje przy tym poście
        for name in (FEED, SRT):              # dodatki poprzedniego filmu nie mogą zostać przy nowym
            try:
                os.remove(os.path.join(folder, name))
            except OSError:
                pass
        timeline, at, page_span = [], 0.0, None
        for n, ((_p, dur, bg), items) in enumerate(zip(parts, subs)):
            # napis części kończy się przed początkiem następnej (SRT bez nakładających się wpisów)
            cap = dur - XFADE if n + 1 < len(parts) else dur
            timeline += [(at + a, at + min(b, cap), t) for a, b, t in items if t and min(b, cap) > a]
            if bg is None:                    # nagranie strony: środek przejść przez czerń (zmiana kadru 4:5)
                page_span = (at + (XFADE / 2 if n else 0.0), at + dur - (XFADE / 2 if n + 1 < len(parts) else 0.0))
                # zmiana kadru 4:5 w środku przejścia przez czerń (feed_crop): skok niewidoczny
            at += dur - XFADE
        _write_atomic(os.path.join(folder, SRT), srt_text(timeline))
        try:
            feed_variant(out, os.path.join(folder, FEED), work, page=page_span, bg=kol["tlo"])
        except RuntimeError as e:             # wersja 4:5 to dodatek: film główny zostaje
            print("film.py: wersja 4:5: %s" % e, file=sys.stderr)
        return out
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _srt_time(sec):
    ms = int(round(max(0.0, sec) * 1000))
    return "%02d:%02d:%02d,%03d" % (ms // 3600000, ms // 60000 % 60, ms // 1000 % 60, ms % 1000)


def srt_text(items):
    """Napisy SRT z [(od, do, tekst)] (tekst może mieć kilka wierszy)."""
    out = []
    for n, (a, b, text) in enumerate(items, 1):
        out += [str(n), "%s --> %s" % (_srt_time(a), _srt_time(b)), str(text).strip(), ""]
    return "\n".join(out)


def _write_atomic(path, text):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def feed_crop(page=None, bg="#000000"):
    """Filtr kadru 4:5 (-filter_complex, wyjście [v]): plansze przycięte FEED_CROP. W czasie nagrania strony (page:
    (od, do) w filmie) cały pionowy kadr zmniejszony do wysokości 1350 na tle marki (bg): zostaje pasek strony
    z logo i napis na dole (przycięcie zabrałoby jedno albo drugie)."""
    h, y = FEED_CROP
    crop = "crop=%d:%d:0:%d" % (SIZE[0], h, y)
    if not page:
        return "[0:v]%s[v]" % crop
    w = int(SIZE[0] * h / SIZE[1]) // 2 * 2
    return ("[0:v]split[a][b];[a]%s[c];[b]scale=%d:%d:flags=lanczos,pad=%d:%d:(ow-iw)/2:0:color=%s[p];"
            "[c][p]overlay=0:0:enable='between(t,%.3f,%.3f)'[v]" % (crop, w, h, SIZE[0], h, "0x" + _hex6(bg),
                                                                     page[0], page[1]))


def feed_variant(src, out, work, page=None, bg="#000000"):
    """Wersja 4:5 (1080×1350) do feedu LinkedIn i Facebook: kadr ze środka filmu pionowego (FEED_CROP; nagranie
    strony zmniejszone na tle marki, feed_crop), dźwięk bez zmian; zapis przez plik tymczasowy."""
    tmp = os.path.join(work, "feed.mp4")
    try:
        r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-protocol_whitelist", "file", "-i", src,
                            "-filter_complex", feed_crop(page, bg), "-map", "[v]", "-map", "0:a?",
                            "-c:v", "libx264", "-preset", "medium", "-crf", "21",
                            "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", tmp],
                           capture_output=True, text=True, timeout=ENCODE_TIMEOUT)
    except subprocess.TimeoutExpired:
        raise RuntimeError("ffmpeg nie skończył w %d s" % ENCODE_TIMEOUT)
    if r.returncode != 0:
        raise RuntimeError((r.stderr.strip().splitlines() or ["ffmpeg"])[-1][:200])
    shutil.move(tmp, out + ".tmp")
    os.replace(out + ".tmp", out)
    return out


def step_label(k):
    """Krok pokazu po polsku dla komunikatu błędu (bez selektorów): co robi i z jakim napisem."""
    what = "wpisanie „%s”" % str(k["wpisz"][1])[:40] if k.get("wpisz") else \
        "wybór „%s”" % str(k["wybierz"][1])[:40] if k.get("wybierz") else \
        "kliknięcie" if k.get("kliknij") else "czekanie na wynik" if k.get("czekaj_na") else \
        "przewinięcie strony" if k.get("przewin") else "rozwinięcie sekcji" if k.get("rozwin") else "napis"
    return what + (", napis „%s”" % str(k["napis"])[:40] if k.get("napis") and what != "napis" else
                   " „%s”" % str(k["napis"])[:40] if k.get("napis") else "")


def step_error(e):
    """Pierwsze zdanie błędu Playwright po polsku tam, gdzie się da."""
    msg = str(e).split("\n")[0][:200]
    if "Timeout" in msg or "timeout" in msg:
        return "element strony nie pojawił się na czas (zmieniła się strona albo selektor w scenariuszu)"
    if "not attached" in msg or "not visible" in msg or "outside of the viewport" in msg:
        return "element strony jest niewidoczny albo zniknął"
    return msg


RECORD_HINTS = (("brak konta demo", "Dodaj konto demo do nagrań: Agenci → Publikacja → Konto do nagrań."),
                ("logowanie kontem demo", "Panel nie zalogował się kontem demo. Sprawdź e-mail i hasło w Agenci → "
                                          "Publikacja → Konto do nagrań."),
                ("logowanie:", "Logowanie nie zadziałało tak, jak zakłada scenariusz. Przekaż błąd agentowi."),
                ("przekierowała poza", "Strona przekierowała na adres spoza marki. Przekaż błąd agentowi."),
                ("krok ", "Strona nie zareagowała tak, jak zakłada scenariusz (zrzut ekranu z chwili błędu niżej). "
                          "Przekaż błąd agentowi albo kliknij „Nagraj ponownie”, jeśli strona chwilowo nie działała."),
                ("montaż:", "Nie udało się złożyć filmu z części (ffmpeg). Przekaż błąd agentowi."),
                ("ponad 10 minut", "Nagranie trwało za długo (strona mogła się zawiesić). Kliknij „Nagraj ponownie”."),
                ("przerwan", "Nagranie przerwał restart panelu. Kliknij „Nagraj ponownie”."),
                ("nie ruszyło", "Nagranie nie ruszyło. Kliknij „Nagraj ponownie”."))


def record_hint(error):
    """Jedno zdanie dla właściciela do błędu nagrania (szczegół techniczny zostaje osobno)."""
    error = str(error or "")
    if not error:
        return ""
    if error.startswith("Błąd nagrania: "):
        error = error[len("Błąd nagrania: "):]
    if error.startswith("scenariusz: "):
        return error_hint(error[len("scenariusz: "):])
    for key, text in RECORD_HINTS:
        if key in error:
            return text
    return "Nie udało się nagrać filmu. Przekaż błąd agentowi albo kliknij „Nagraj ponownie”."


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
        hidden = hide_list(brand, sc)
        if hidden:                      # baner zgody, przycisk „Opinia”, czat: poza kadrem całego pokazu
            ctx.add_init_script(hide_js(hidden))
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
        t_open = time.monotonic()       # nagranie Playwright zaczyna się z otwarciem strony (zapas, gdy brak ffprobe)

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
            login = login_spec(sc["logowanie"])
            page.goto(login["url"], wait_until="networkidle", timeout=60000)
            if landed("logowanie") != _host(login["url"])[1]:      # konto demo tylko na hoście logowania
                raise RuntimeError("logowanie: strona wylądowała na innym hoście niż adres logowania")
            login_path = (_host(login["url"])[0].path or "/").rstrip("/") or "/"
            try:
                page.fill(login["email"], acc["email"], timeout=15000)
                page.fill(login["haslo"], acc["haslo"], timeout=15000)
                page.locator(login["wyslij"]).first.click(timeout=15000)
            except Exception as e:  # noqa: BLE001
                raise RuntimeError("logowanie: nie znaleziono pól logowania na stronie (%s); sprawdź selektory "
                                   "email, haslo, wyslij w polu logowanie scenariusza" % step_error(e))
            try:
                page.wait_for_url(lambda u: ((_host(u)[0].path if _host(u)[0] else "") or "/").rstrip("/") or "/"
                                  != login_path, timeout=20000)
            except Exception:  # noqa: BLE001
                raise RuntimeError("logowanie kontem demo nie powiodło się (sprawdź e-mail i hasło)")
            try:                        # strona po zalogowaniu zapisuje sesję; bez tego przejście dalej wraca do logowania
                page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:  # noqa: BLE001
                pass
            page.wait_for_timeout(1500)
        page.goto(sc["url"], wait_until="networkidle", timeout=60000)
        if sc.get("logowanie") and (_host(page.url)[0].path or "").rstrip("/") == login_path:
            raise RuntimeError("logowanie: po zalogowaniu strona wróciła do logowania (sesja nie została zapisana)")
        landed("url")
        page.wait_for_timeout(800)
        t0 = time.monotonic()           # początek filmu: strona już wczytana
        page.mouse.move(VIEW[0] / 2, VIEW[1] / 3)

        def bring(loc):
            """Element do pasa między strefami (płynnie); potem jeszcze kontrola Playwright (przewijane ramki)."""
            dy = loc.evaluate(BAND_JS, list(BAND))
            if dy:
                page.wait_for_timeout(int(min(900, 300 + dy)))
            loc.scroll_into_view_if_needed(timeout=10000)

        def point(loc):
            """Kursor dojeżdża do środka elementu przed kliknięciem (pierścień kliknięcia tam, gdzie kursor)."""
            box = loc.bounding_box()
            if box:
                page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, steps=8)
                page.wait_for_timeout(300)

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
                    bring(page.locator(k["przewin"]).first)
                    page.wait_for_timeout(200)
                if k.get("wpisz"):
                    sel, text = k["wpisz"]
                    text = str(text)
                    loc = page.locator(sel).first
                    bring(loc)
                    point(loc)
                    loc.click(timeout=10000)
                    loc.press_sequentially(text, delay=max(20, min(55, int(1400 / max(1, len(text))))))
                if k.get("wybierz"):
                    sel, value = k["wybierz"]
                    loc = page.locator(sel).first
                    bring(loc)
                    point(loc)
                    loc.click(timeout=10000)
                    loc.select_option(str(value), timeout=10000)
                if k.get("kliknij"):
                    loc = page.locator(k["kliknij"]).first
                    bring(loc)
                    point(loc)
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
                    page.screenshot(path=os.path.join(folder, ERROR_SHOT), full_page=False)
                except Exception:  # noqa: BLE001
                    pass
                raise RuntimeError("krok %d (%s): %s" % (i + 1, step_label(k), step_error(e)))
        let_read()
        # ostatni napis znika przed przejściem do następnej planszy (jak treść planszy), więc stoi o tyle dłużej
        if captions:
            page.wait_for_timeout(int((XFADE + FADE_OUT) * 1000))
        end = time.monotonic() - t0
        video = page.video.path()
        ctx.close()
        browser.close()
    cuts = cuts_for(waits)
    caps = [(shift_time(at, cuts) + LEAD_PAD, text) for at, text in captions]
    # ostatni napis strony kończy się przed przejściem (SRT bez nakładania na pierwszy napis następnej części)
    stop = shift_time(end, cuts) + LEAD_PAD - XFADE - FADE_OUT
    page_subs = [(a, caps[n + 1][0] if n + 1 < len(caps) else stop, text) for n, (a, text) in enumerate(caps)]
    return render(video, os.path.join(work, "pokaz.mp4"), captions, end, work, caption_style(brand), waits,
                  logo=logo_path(brand, studio_dir(folder)) if brand.get("logo_w_rogu") else None,
                  lead_hint=t0 - t_open), page_subs


PAGE_CAPTION_ALPHA = 0.97         # krycie pudełka napisu na nagraniu strony (co najmniej)
FAST_LEN = 0.8                    # s: tyle trwa w filmie przyspieszony środek długiego czekania (znak „×N” w rogu)
LEAD_PAD = 0.2                    # s: klip nagrania strony zaczyna się tyle przed początkiem filmu (t0)


def cuts_for(waits, keep_head=0.6, keep_tail=0.5, min_len=1.5):
    """Odcinki czekania do przyspieszenia: z czekania dłuższego niż min_len zostaje początek i koniec w normalnym
    tempie, środek trwa w filmie najwyżej FAST_LEN (przyspieszenie z oznaczeniem, nie ukryte cięcie)."""
    out = []
    for a, b in waits:
        if b - a > min_len:
            out.append((a + keep_head, b - keep_tail))
    return out


def _kept(a, b):
    """Czas w filmie przyspieszonego odcinka (a, b)."""
    return min(b - a, FAST_LEN)


def speed_of(a, b):
    """Przyspieszenie odcinka (a, b): ×N w filmie."""
    return (b - a) / _kept(a, b) if b > a else 1.0


def shift_time(t, cuts):
    """Czas w filmie po przyspieszeniu odcinków cuts (napisy przesuwają się razem z obrazem)."""
    removed = 0.0
    for a, b in cuts:
        cut = (b - a) - _kept(a, b)
        if t >= b:
            removed += cut
        elif t > a:
            removed += (t - a) * cut / (b - a)
    return t - removed


def render(src, out, captions, end, work, style=None, waits=(), logo=None, lead_hint=None):
    """Przycięcie początku (wczytywanie strony), przyspieszenie długiego czekania (początek i koniec czekania
    w normalnym tempie, środek szybciej ze znakiem „×N”), napisy wtopione (styl marki) w chwili akcji, logo marki
    w prawym górnym rogu (logo_w_rogu), H.264 1080×1920 30 kl./s (klip pośredni do sklejenia). lead_hint (s): czas
    od otwarcia strony do początku filmu, gdy ffprobe nie poda długości nagrania (bez niego do filmu weszłoby
    wczytywanie strony i logowanie)."""
    total = _duration(src)
    if total > 0:
        lead = max(0.0, total - end - LEAD_PAD)   # nagranie zaczyna się przed t0 (wczytywanie strony): odcinamy
    else:
        lead = max(0.0, (lead_hint or 0.0) - LEAD_PAD)
    if style is None:
        style = dict(DEFAULT_BRAND["napisy"], font=Font(FONT, 56))
    # na ruchliwej stronie pudełko napisu prawie nieprzezroczyste (przy 0,85–0,9 prześwituje tekst strony)
    style = dict(style, krycie=max(PAGE_CAPTION_ALPHA, float(style.get("krycie", 0.85))))
    cuts = cuts_for(waits)
    texts = _Texts(work, "napis")
    # nagranie 540×960 powiększone 2×: lanczos i lekkie wyostrzenie (drobny tekst strony mniej rozmyty)
    filters = ["scale=1080:1920:flags=lanczos", "unsharp=5:5:0.7:5:5:0.0"]
    if cuts:
        # czas w klipie = czas od t0 + LEAD_PAD; każdy odcinek czekania trwa w filmie _kept zamiast całej długości
        expr = "+".join("clip(T-%.3f,0,%.3f)*%.5f" % (a + LEAD_PAD, b - a, 1 - _kept(a, b) / (b - a))
                        for a, b in cuts)
        filters.append("setpts='(T-(%s))/TB'" % expr)
    filters.append("fps=30")
    for a, b in cuts:                     # znak przyspieszenia w lewym górnym rogu na czas przyspieszonego odcinka
        at = shift_time(a, cuts) + LEAD_PAD
        filters.append(_draw(texts, "przyspieszone ×%d" % round(speed_of(a, b)), style["font"].at(40),
                             _col(style.get("kolor", "#ffffff")), str(MARGIN), SAFE_TOP + 70,
                             extra=":box=1:boxcolor=%s:boxborderw=16:enable='between(t,%.2f,%.2f)'"
                             % (_col(style.get("tlo", "#2b1d12"), float(style.get("krycie", 0.85))), at,
                                at + _kept(a, b))))
    # napisy w chwili akcji: klip zaczyna się LEAD_PAD przed t0, więc czasy napisów (względem t0) + LEAD_PAD
    caps = [(shift_time(at, cuts) + LEAD_PAD, text) for at, text in captions]
    clip_end = shift_time(end, cuts) + LEAD_PAD
    filters += caption_filters(texts, caps, clip_end, style, last_stop=clip_end - XFADE - FADE_OUT)
    if not logo:
        return _encode(["-ss", "%.2f" % lead, "-protocol_whitelist", "file", "-i", src, "-vf", ",".join(filters)], out)
    graph = "[0:v]%s[pg];[1:v]scale=w=-1:h=64,format=rgba[lg];[pg][lg]overlay=x=W-w-%d:y=%d:shortest=1[out]" % (
        ",".join(filters), MARGIN, SAFE_TOP + 20)
    return _encode(["-ss", "%.2f" % lead, "-protocol_whitelist", "file", "-i", src] + media_input(logo, total or end + 5) +
                   ["-filter_complex", graph, "-map", "[out]"], out)


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
        self.versions = {}            # wersja filmu (version()) z chwili startu: czas modyfikacji nagranego pliku
        self.waiting = []             # [(folder, tytuł)]: czekają na koniec bieżącego nagrania (jedno naraz)

    def available(self, kind="pokaz"):
        """Pokaz: Playwright (osobny interpreter) i ffmpeg; objaśnienie: tylko ffmpeg. Oba: plik czcionki zastępczej
        (FONT), bez niej montaż plansz i napisów kończy się błędem ffmpeg."""
        return bool(shutil.which("ffmpeg")) and os.path.isfile(FONT) and (kind == "objasnienie"
                                                                          or os.path.isfile(self.python))

    def interpreter(self, kind):
        """Objaśnienie bez Playwright: interpreter panelu (ma PIL do pomiaru tekstu, gdy jest zainstalowany)."""
        return self.python if kind != "objasnienie" else sys.executable

    def start(self, folder, title=""):
        """Nagranie filmu posta w tle: (kod, komunikat, dane). Jedno nagranie naraz: gdy nagrywa się inny film (albo
        ten sam, a scenariusz zmienił się w trakcie), ten czeka w kolejce i rusza zaraz po bieżącym ({"state":
        "queued"}). Zawsze trzy elementy."""
        if not folder:
            return 404, "Nie ma posta na ten dzień.", {}
        if not os.path.isfile(os.path.join(folder, SCENARIO)):
            return 409, "Post nie ma scenariusza filmu (scenariusz.json).", {}
        info = describe(folder)
        if info["error"]:          # błąd szablonu albo marki: widoczny w poście od razu, bez uruchamiania nagrania
            keep = {k: v for k, v in read_state(folder).items() if k == "scenario"}
            write_state(folder, state="error", error="scenariusz: " + info["error"], **keep)
            return 409, "Scenariusz filmu: %s." % info["error"], {}
        if not (self.available() if info["kind"] == "pokaz" else self.available(info["kind"])):
            return 409, ("Ten panel nie ma narzędzi do nagrywania (Playwright, ffmpeg); film nagra panel na serwerze."
                         if info["kind"] == "pokaz" else
                         "Ten panel nie ma ffmpeg (potrzebny do objaśnień); film nagra panel na serwerze."), {}
        with self.lock:
            same = folder in self.busy
            wait = same or bool(self.busy)
            if wait:
                if all(f != folder for f, _t in self.waiting):
                    self.waiting.append((folder, title))
                pos = 1 + [f for f, _t in self.waiting].index(folder)
            else:
                self.busy.add(folder)
                self.kinds[folder] = info["kind"]
                self.versions[folder] = version(folder)
        keep = {k: v for k, v in read_state(folder).items() if k == "scenario"}
        if wait:
            if not same:           # ten sam folder: stan „running” zostaje do końca bieżącego nagrania
                write_state(folder, state="queued", error="", host=HOST, pid=os.getpid(), kind=info["kind"], **keep)
            return 202, "", {"state": "queued", "position": pos,
                             "note": "Nagrywa się teraz ten film; zmiana nagra się zaraz po nim." if same else
                             "Nagrywa się inny film; ten nagra się zaraz po nim."}
        # host i pid: drugi egzemplarz panelu na tych samych plikach nie uzna tego nagrania za przerwane;
        # scenario zostaje (auto_record nagrywa jedną wersję scenariusza raz, także po błędzie)
        write_state(folder, state="running", error="", host=HOST, pid=os.getpid(), kind=info["kind"],
                    version=self.versions.get(folder), **keep)
        threading.Thread(target=self._run, args=(folder, title), daemon=True).start()
        return 202, "", {"state": "running"}

    def _next(self):
        """Następny film z kolejki (po zakończeniu bieżącego). Start, który nie ruszył: błąd w stanie posta (stan
        „queued” nie może zostać bez nagrania)."""
        with self.lock:
            if self.busy or not self.waiting:
                return
            folder, title = self.waiting.pop(0)
        try:
            code, msg, _data = self.start(folder, title)
        except Exception as e:  # noqa: BLE001
            code, msg = 500, "%s: %s" % (type(e).__name__, e)
        if code >= 400 and read_state(folder).get("state") == "queued":
            keep = {k: v for k, v in read_state(folder).items() if k == "scenario"}
            try:
                write_state(folder, state="error", error="nagranie nie ruszyło: %s" % str(msg)[:200], **keep)
            except OSError:
                pass

    def _run(self, folder, title):
        """Nagranie w osobnej grupie procesów (przy przekroczeniu limitu ginie też ffmpeg i Chromium). Zawsze, także
        po nieoczekiwanym wyjątku, zapisuje stan i zwalnia folder (inaczej automat nagrań stałby do restartu).
        Udany film dostaje czas modyfikacji wersji, z której powstał (version() z chwili startu): zmiana scenariusza
        w trakcie nagrania jest nowsza niż film, więc automat nagra ją jeszcze raz. Zrzut z błędu kroku pokazu
        (.film-blad.png) znika na starcie nagrania: przy następnym, innym błędzie (scenariusz, ffmpeg, przerwanie)
        panel nie pokaże starego zrzutu."""
        ok, err = False, "nieznany błąd"
        try:
            os.remove(os.path.join(folder, ERROR_SHOT))
        except OSError:
            pass
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
            with self.lock:
                v = self.versions.pop(folder, None)
            try:
                keep = {k: val for k, val in read_state(folder).items() if k == "scenario"}
                write_state(folder, state="done" if ok else "error", error=err, **keep)
                if ok:
                    for name in (MANUAL, ERROR_SHOT):
                        try:
                            os.remove(os.path.join(folder, name))
                        except OSError:
                            pass
                    path = os.path.join(folder, "film.mp4")
                    if v and os.path.isfile(path):
                        os.utime(path, (v, v))
            except OSError:
                pass
            with self.lock:
                self.busy.discard(folder)
                self.kinds.pop(folder, None)
        self.notify(("Film nagrany: %s. Obejrzyj go w poście." % (title or os.path.basename(folder))) if ok
                    else "Nie nagrano filmu (%s): %s" % (title or os.path.basename(folder), err))
        self._next()


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
