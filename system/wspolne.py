"""Wspólne funkcje etapu 1: ustawienia, pliki, tożsamość, czas, git. Kontrakt: KONTRAKT.md."""
import datetime
import hashlib
import json
import os
import re
import subprocess
import tempfile

TU = os.path.dirname(os.path.abspath(__file__))
KORZEN = os.path.dirname(TU)                      # folder IntegrateSystems

DOMYSLNE = {
    "STAN_DIR": "~/stan-systemu",
    "LOKALNE_DIR": "~/.integrate-lokalne",
    "SKANUJ": "~",
    "GLEBOKOSC": "4",
    "CLAUDE_PROJEKTY": "~/.claude/projects",
    "HC_ZBIERACZ": "",
    "TELEGRAM_TOKEN": "",
    "TELEGRAM_CHAT": "",
    "TELEGRAM_API": "https://api.telegram.org",
    "HC_SERCE": "",
    "HC_RAPORT": "",
    "RAPORT_GODZINA": "7",
    "CISZA": "22-7",
    "CYKL_S": "300",
}
SCIEZKI = ("STAN_DIR", "LOKALNE_DIR", "CLAUDE_PROJEKTY")


def ustawienia(plik=None):
    """Słownik ustawień: domyślne < system.env < środowisko. Ścieżki rozwinięte."""
    u = dict(DOMYSLNE)
    plik = plik or os.environ.get("SYSTEM_ENV") or os.path.join(TU, "system.env")
    if os.path.isfile(plik):
        with open(plik, encoding="utf-8") as f:
            for wiersz in f:
                wiersz = wiersz.strip()
                if not wiersz or wiersz.startswith("#") or "=" not in wiersz:
                    continue
                k, _, v = wiersz.partition("=")
                u[k.strip()] = v.strip().strip('"').strip("'")
    for k in list(u):
        if k in os.environ:
            u[k] = os.environ[k]
    for k in SCIEZKI:
        u[k] = os.path.abspath(os.path.expanduser(u[k]))
    u["SKANUJ"] = ";".join(os.path.abspath(os.path.expanduser(p)) for p in u["SKANUJ"].split(";") if p.strip())
    return u


# ---------- czas ----------

try:
    from zoneinfo import ZoneInfo                   # Python 3.9+
    STREFA = ZoneInfo("Europe/Warsaw")
except Exception:                                   # Windows bez bazy stref: przybliżenie CET/CEST
    STREFA = None


def _strefa_dla(utc):
    if STREFA is not None:
        return STREFA
    rok = utc.year
    ostatnia_niedziela = lambda m: max(datetime.datetime(rok, m, d, 1, tzinfo=datetime.timezone.utc)
                                       for d in range(25, 32) if datetime.date(rok, m, d).weekday() == 6)
    lato = ostatnia_niedziela(3) <= utc < ostatnia_niedziela(10)
    return datetime.timezone(datetime.timedelta(hours=2 if lato else 1))


def teraz():
    """Bieżący czas w strefie Europe/Warsaw (świadomy strefy)."""
    utc = datetime.datetime.now(datetime.timezone.utc)
    return utc.astimezone(_strefa_dla(utc))


def iso(t=None):
    return (t or teraz()).replace(microsecond=0).isoformat()


def z_iso(tekst):
    try:
        return datetime.datetime.fromisoformat(tekst) if tekst else None
    except ValueError:
        return None


def z_timestamp(ts):
    utc = datetime.datetime.fromtimestamp(ts, datetime.timezone.utc)
    return utc.astimezone(_strefa_dla(utc))


# ---------- pliki ----------

def zapisz_atomowo(sciezka, tekst):
    os.makedirs(os.path.dirname(sciezka) or ".", exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(sciezka) or ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(tekst)
        os.replace(tmp, sciezka)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def czytaj_json(sciezka, domyslnie=None):
    try:
        with open(sciezka, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return domyslnie


def zapisz_json(sciezka, dane):
    zapisz_atomowo(sciezka, json.dumps(dane, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def czytaj_jsonl(sciezka):
    """(poprawne wiersze, niepoprawne wiersze jako tekst)."""
    dobre, zle = [], []
    try:
        with open(sciezka, encoding="utf-8") as f:
            for w in f:
                w = w.strip()
                if not w:
                    continue
                try:
                    obj = json.loads(w)
                    (dobre if isinstance(obj, dict) else zle).append(obj if isinstance(obj, dict) else w)
                except ValueError:
                    zle.append(w)
    except OSError:
        pass
    return dobre, zle


def dopisz_jsonl(sciezka, obiekty):
    os.makedirs(os.path.dirname(sciezka) or ".", exist_ok=True)
    with open(sciezka, "a", encoding="utf-8", newline="\n") as f:
        for o in obiekty:
            f.write(json.dumps(o, ensure_ascii=False, sort_keys=True) + "\n")


# ---------- tożsamość ----------

def normalizuj_zdalne(adres):
    a = (adres or "").strip().lower()
    a = re.sub(r"^[a-z+]+://[^@/]*@", lambda m: m.group(0).split("//")[0] + "//", a)   # bez danych logowania
    a = re.sub(r"\.git$", "", a).rstrip("/")
    m = re.match(r"^git@([^:]+):(.+)$", a)                                            # git@host:owner/repo
    if m:
        a = "https://%s/%s" % (m.group(1), m.group(2))
    return a


def tozsamosc(zdalne=None, sciezka=None):
    klucz = normalizuj_zdalne(zdalne) if zdalne else os.path.abspath(sciezka or "")
    return hashlib.sha256(klucz.encode("utf-8")).hexdigest()[:12]


def alias_tymczasowy(toz):
    return "K-" + toz[:4]


def id_skrot(*czesci):
    return hashlib.sha256("|".join(str(c) for c in czesci).encode("utf-8")).hexdigest()[:16]


# ---------- git ----------

class GitBlad(Exception):
    pass


def git(katalog, *args, sprawdz=True, timeout=120):
    """Uruchamia git w katalogu; zwraca stdout. Bez okna konsoli na Windows."""
    flagi = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    p = subprocess.run(["git", *args], cwd=katalog, capture_output=True, text=True, timeout=timeout,
                       creationflags=flagi, env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
    if sprawdz and p.returncode != 0:
        raise GitBlad("git %s: %s" % (args[0], (p.stderr or p.stdout).strip()[:300]))
    return p.stdout


def ping(adres, tresc=None, timeout=10):
    """Ping healthchecks; błąd nie przerywa pracy. Zwraca True przy sukcesie."""
    if not adres:
        return False
    import urllib.request
    try:
        dane = tresc.encode("utf-8") if tresc else None
        urllib.request.urlopen(urllib.request.Request(adres, data=dane), timeout=timeout).read()
        return True
    except Exception:
        return False
