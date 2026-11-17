#!/usr/bin/env python3
"""Zbieracz Maca (etap 1): inwentarz, stan projektów, decyzje P2, wypchnięcie gałęzi `mac`.

  python3 zbieracz.py init <adres-repo>   klon repozytorium stanu do STAN_DIR, gałąź mac
  python3 zbieracz.py [zbierz]            skan, zapis mac/, commit i push gałęzi mac
  python3 zbieracz.py kandydaci           kandydaci z nazwą i ścieżką (tylko na ekran)
  python3 zbieracz.py kwalifikuj          decyzje dla kandydatów bez decyzji, potem zbierz
  python3 zbieracz.py podglad             to samo co zbierz, bez git i bez zapisu: same liczby

Kontrakt: KONTRAKT.md, sekcja „Zbieracz”. Do repozytorium trafiają tylko dane jawne
(tożsamość, alias, liczby, daty; nazwa tylko w stan.json dla klient = false).
Nazwy, ścieżki i adresy zdalne zostają w LOKALNE_DIR/aliasy.json.
"""
import datetime
import json
import os
import re
import sys
import time

TU = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TU)
sys.path.insert(0, os.path.join(os.path.dirname(TU), "standard"))
import wspolne as w  # noqa: E402
import projekt  # noqa: E402
import pm  # noqa: E402

MASZYNA = "mac"
POMIJAJ = {"node_modules", ".venv", "venv", "Library", ".Trash"}
STANY = ["w realizacji", "backlog", "w przygotowaniu", "archiwum", "wykluczony", "scalony"]
STANY_STANU = {"w realizacji", "w przygotowaniu", "wstrzymany", "backlog"}
BEZ_ZDARZEN = {"wykluczony", "scalony"}
KOLEJKA_MAX = 10000
PONOWIENIA = 3
PRZERWY_S = (5, 20, 60)          # odstępy między ponowieniami push
WIERSZE_SESJI = 20               # ile pierwszych wierszy pliku sesji przeglądamy w poszukiwaniu `cwd`
DLUGOSC_WIERSZA = 1 << 20        # najwyżej 1 MB z jednego wiersza
CWD = re.compile(r'"cwd"\s*:\s*"((?:[^"\\]|\\.)*)"')

TYTULY = {
    "commit": "Nowy commit",
    "sesja": "Sesja Claude Code",
    "kandydat": "Nowy kandydat",
    "brak-dostepu": "Brak dostępu do katalogu",
    "nie-rozumiem-pliku": "Nie rozumiem pliku sesji",
    "push-nieudany": "Wypchnięcie z Maca nieudane",
}
WAGI = {"commit": "info", "sesja": "szum", "kandydat": "info", "brak-dostepu": "info",
        "nie-rozumiem-pliku": "info", "push-nieudany": "info"}


class Blad(Exception):
    """Błąd z komunikatem dla użytkownika."""


# ---------- pliki ----------

def sciezki(u):
    s, l = u["STAN_DIR"], u["LOKALNE_DIR"]
    return {
        "mac": os.path.join(s, "mac"),
        "inwentarz": os.path.join(s, "mac", "inwentarz.json"),
        "stan": os.path.join(s, "mac", "stan.json"),
        "decyzje": os.path.join(s, "mac", "decyzje.jsonl"),
        "zdarzenia": os.path.join(s, "mac", "zdarzenia"),
        "aliasy": os.path.join(l, "aliasy.json"),
        "kolejka": os.path.join(l, "kolejka.jsonl"),
        "pamiec": os.path.join(l, "zbieracz.json"),
        "blokada": os.path.join(l, "zbieracz.lock"),
    }


def zdarzenie(typ, id_, projekt_=None, czas=None):
    return {"id": id_, "zrodlo": MASZYNA, "czas": czas or w.iso(), "projekt": projekt_, "typ": typ,
            "waga": WAGI[typ], "tytul": TYTULY[typ], "link": None}


def zdarzenie_bez_id(typ, klucz, dzien):
    """Zdarzenie bez naturalnego identyfikatora: skrót ze źródła, typu, klucza i dnia (raz dziennie)."""
    return zdarzenie(typ, w.id_skrot(MASZYNA, typ, klucz, dzien))


def najnowsze_decyzje(plik):
    """{tozsamosc: ostatnia decyzja}."""
    out = {}
    dobre, _ = w.czytaj_jsonl(plik)
    for d in dobre:
        if isinstance(d.get("tozsamosc"), str) and d.get("stan") in STANY + ["wstrzymany"]:
            out[d["tozsamosc"]] = d
    return out


def ogranicz_kolejke(zdarzenia):
    widziane, out = set(), []
    for z in zdarzenia:
        if z.get("id") not in widziane:
            widziane.add(z.get("id"))
            out.append(z)
    return out[-KOLEJKA_MAX:]


def zapisz_jsonl(sciezka, obiekty):
    w.zapisz_atomowo(sciezka, "".join(json.dumps(o, ensure_ascii=False, sort_keys=True) + "\n" for o in obiekty))


class Blokada:
    """Jeden zbieracz naraz (launchd i ręczne uruchomienie)."""

    def __init__(self, plik):
        self.plik, self.f = plik, None

    def __enter__(self):
        import fcntl
        os.makedirs(os.path.dirname(self.plik), exist_ok=True)
        self.f = open(self.plik, "w")
        try:
            fcntl.flock(self.f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.f.close()
            raise Blad("Zbieracz już działa.")
        return self

    def __exit__(self, *a):
        self.f.close()


# ---------- skanowanie ----------

def _git(katalog, *args):
    """git bez wyjątku: stdout albo ''."""
    try:
        return w.git(katalog, *args, sprawdz=False, timeout=60).strip()
    except Exception:
        return ""


def znajdz_repozytoria(korzenie, glebokosc, pomin, brak_dostepu):
    """Katalogi z `.git` do głębokości `glebokosc` (korzeń = 0)."""
    wynik, stos = [], [(k, 0) for k in korzenie]
    while stos:
        d, poziom = stos.pop()
        if os.path.realpath(d) in pomin:
            continue
        try:
            with os.scandir(d) as it:
                wpisy = list(it)
        except PermissionError:
            brak_dostepu.append(d)
            continue
        except OSError:
            continue
        if any(e.name == ".git" for e in wpisy):
            wynik.append(os.path.realpath(d))
            continue
        if poziom >= glebokosc:
            continue
        for e in wpisy:
            if e.name.startswith(".") or e.name in POMIJAJ:
                continue
            try:
                if e.is_dir(follow_symlinks=False):
                    stos.append((e.path, poziom + 1))
            except OSError:
                continue
    return sorted(set(wynik))


def opisz_repo(sciezka, filtruj_klony=True):
    """Słownik z danymi repozytorium albo None (klon bez własnych commitów)."""
    zdalne = _git(sciezka, "config", "--get", "remote.origin.url")
    if not zdalne:
        nazwy = _git(sciezka, "remote").split()
        zdalne = _git(sciezka, "remote", "get-url", nazwy[0]) if nazwy else ""
    ostatni = _git(sciezka, "log", "-1", "--format=%H %ct").split()
    if filtruj_klony and zdalne:
        email = _git(sciezka, "config", "user.email")
        if email and not _git(sciezka, "log", "-1", "--format=%H", "--fixed-strings", "--author=" + email):
            return None
    licznik = _git(sciezka, "rev-list", "--count", "HEAD") if ostatni else ""
    return {
        "tozsamosc": w.tozsamosc(zdalne or None, sciezka),
        "nazwa": os.path.basename(sciezka),
        "sciezka": sciezka,
        "zdalne": w.normalizuj_zdalne(zdalne) if zdalne else None,
        "zrodla": {"git"},
        "commity": int(licznik) if licznik.isdigit() else 0,
        "hash": ostatni[0] if len(ostatni) == 2 else None,
        "commit_ts": int(ostatni[1]) if len(ostatni) == 2 and ostatni[1].isdigit() else None,
        "sesje": 0,
        "sesja_ts": None,
        "pliki_sesji": [],
    }


def cwd_z_pliku(plik):
    """Pole `cwd` z pierwszych wierszy pliku sesji. None, gdy go nie ma. Reszty wiersza nie interpretuje."""
    with open(plik, "rb") as f:
        for _ in range(WIERSZE_SESJI):
            wiersz = f.readline(DLUGOSC_WIERSZA)
            if not wiersz:
                return None
            m = CWD.search(wiersz.decode("utf-8", "replace"))
            if m:
                try:
                    cwd = json.loads('"%s"' % m.group(1))
                except ValueError:
                    return None
                return cwd if cwd.startswith("/") else None
    return None


def czytaj_sesje(katalog, brak_dostepu, nieczytelne):
    """{cwd: [czasy modyfikacji plików]}; treści sesji nie czyta."""
    out = {}
    try:
        with os.scandir(katalog) as it:
            podkatalogi = sorted(e.path for e in it if e.is_dir(follow_symlinks=False))
    except FileNotFoundError:
        return out
    except PermissionError:
        brak_dostepu.append(katalog)
        return out
    except OSError:
        return out
    for pod in podkatalogi:
        try:
            with os.scandir(pod) as it:
                pliki = sorted((e.path, e.stat().st_mtime) for e in it
                               if e.name.endswith(".jsonl") and e.is_file(follow_symlinks=False))
        except PermissionError:
            brak_dostepu.append(pod)
            continue
        except OSError:
            continue
        for plik, mtime in pliki:
            try:
                cwd = cwd_z_pliku(plik)
            except OSError:
                cwd = None
            if not cwd:
                nieczytelne.append(plik)
                continue
            out.setdefault(os.path.realpath(cwd), []).append(mtime)
    return out


def skanuj(u):
    """Kandydaci (z danymi lokalnymi) i listy problemów. Nic nie zapisuje."""
    brak, nieczytelne = [], []
    pomin = {os.path.realpath(u["STAN_DIR"]), os.path.realpath(u["LOKALNE_DIR"])}
    korzenie = [k for k in u["SKANUJ"].split(";") if k]
    try:
        glebokosc = int(u["GLEBOKOSC"])
    except ValueError:
        glebokosc = 4
    kandydaci = {}
    for sciezka in znajdz_repozytoria(korzenie, glebokosc, pomin, brak):
        k = opisz_repo(sciezka)
        if k and k["tozsamosc"] not in kandydaci:
            kandydaci[k["tozsamosc"]] = k
    po_sciezce = sorted(((k["sciezka"], k) for k in kandydaci.values()), key=lambda x: -len(x[0]))
    for cwd, czasy in czytaj_sesje(u["CLAUDE_PROJEKTY"], brak, nieczytelne).items():
        if cwd in pomin:
            continue
        k = next((k for s, k in po_sciezce if cwd == s or cwd.startswith(s + os.sep)), None)
        if k is None and os.path.exists(os.path.join(cwd, ".git")):
            k = opisz_repo(cwd, filtruj_klony=False)
            if k:
                k = kandydaci.setdefault(k["tozsamosc"], k)
                po_sciezce.insert(0, (cwd, k))
        if k is None:
            toz = w.tozsamosc(None, cwd)
            k = kandydaci.setdefault(toz, {
                "tozsamosc": toz, "nazwa": os.path.basename(cwd) or cwd, "sciezka": cwd, "zdalne": None,
                "zrodla": set(), "commity": 0, "hash": None, "commit_ts": None, "sesje": 0, "sesja_ts": None,
                "pliki_sesji": []})
        k["zrodla"].add("claude")
        k["sesje"] += len(czasy)
        k["pliki_sesji"] += czasy
        k["sesja_ts"] = max([k["sesja_ts"] or 0] + czasy)
    return kandydaci, brak, nieczytelne


# ---------- liczby z ZADANIA.md ----------

def _dzien(wartosc, dzis):
    m = pm.REL.match(wartosc or "")
    return (dzis + datetime.timedelta(days=int(m.group(1)))).isoformat() if m else wartosc


def liczby_zadan(sciezka, dzis):
    """Liczby jak w standard/pm.py dla ZADANIA.md jednego projektu."""
    out = {"otwarte": 0, "zrobione": 0, "czeka_na_ciebie": 0, "po_terminie": 0, "zablokowane": 0,
           "ma_zadania": False}
    tekst = projekt.read(os.path.join(sciezka, "ZADANIA.md")) if sciezka else None
    if tekst is None:
        return out
    etapy, zadania, _ = projekt.parse_tasks(tekst, "p")
    for x in etapy + zadania:
        x["date"] = _dzien(x["date"], dzis)
    stan_etapu = {s["id"]: pm.stage_state(s, zadania, dzis) for s in etapy}
    klucz = dzis.isoformat()
    otwarte = [t for t in zadania if t["state"] != "done"]
    out.update({
        "ma_zadania": True,
        "otwarte": len(otwarte),
        "zrobione": len(zadania) - len(otwarte),
        "czeka_na_ciebie": sum(1 for t in otwarte if t["executor"] == "ty" or t["needsYou"]),
        "po_terminie": sum(1 for t in otwarte if (pm.is_day(t["date"]) and t["date"] < klucz)
                           or stan_etapu.get(t["stage"]) == "late"),
        "zablokowane": sum(1 for t in otwarte if t["state"] == "blocked"),
    })
    return out


# ---------- wynik zbierania ----------

def _iso_ts(ts):
    return w.iso(w.z_timestamp(ts)) if ts else None


def oblicz(pamiec, decyzje, kandydaci, brak, nieczytelne, aliasy, start_ts=None):
    """Inwentarz, stan i nowe zdarzenia (dane jawne) z wyniku skanu. start_ts: chwila rozpoczęcia skanu."""
    teraz = w.teraz()
    czas, dzien = w.iso(teraz), teraz.date().isoformat()
    pop_ts = pamiec.get("ostatnie_zbieranie_ts")
    znani = set(pamiec.get("znani", []))
    commity = pamiec.get("commity", {})

    def alias(toz):
        d = decyzje.get(toz)
        return d["alias"] if d and d.get("alias") else w.alias_tymczasowy(toz)

    inwentarz, zdarzenia = [], []
    for toz in sorted(kandydaci):
        k = kandydaci[toz]
        aktywnosc = max(k["commit_ts"] or 0, k["sesja_ts"] or 0)
        inwentarz.append({"tozsamosc": toz, "alias": alias(toz), "zrodla": sorted(k["zrodla"]),
                          "ostatnia_aktywnosc": _iso_ts(aktywnosc), "commity": k["commity"], "sesje": k["sesje"]})
        stan = (decyzje.get(toz) or {}).get("stan")
        if toz not in znani and toz not in decyzje:
            zdarzenia.append(zdarzenie("kandydat", "%s:kandydat:%s" % (MASZYNA, toz), alias(toz)))
        if stan in BEZ_ZDARZEN:
            continue
        if k["hash"] and toz in commity and commity[toz] != k["hash"]:
            zdarzenia.append(zdarzenie("commit", "%s:repo:%s:%s" % (MASZYNA, toz, k["hash"]), alias(toz),
                                       _iso_ts(k["commit_ts"])))
        if pop_ts is not None:
            dni = {}
            for ts in k["pliki_sesji"]:
                if ts > pop_ts:
                    d = w.z_timestamp(ts).date().isoformat()
                    dni[d] = max(dni.get(d, 0), ts)
            for d, ts in sorted(dni.items()):
                zdarzenia.append(zdarzenie("sesja", "%s:sesja:%s:%s" % (MASZYNA, toz, d), alias(toz), _iso_ts(ts)))
    for d in sorted(set(brak)):
        zdarzenia.append(zdarzenie_bez_id("brak-dostepu", os.path.realpath(d), dzien))
    for p in sorted({os.path.dirname(os.path.realpath(x)) for x in nieczytelne}):   # raz dziennie na katalog sesji
        zdarzenia.append(zdarzenie_bez_id("nie-rozumiem-pliku", p, dzien))

    projekty = []
    for toz in sorted(decyzje):
        d = decyzje[toz]
        if d.get("stan") not in STANY_STANU:
            continue
        k = kandydaci.get(toz)
        lokalne = aliasy.get(toz, {})
        sciezka = k["sciezka"] if k else lokalne.get("sciezka")
        klient = d.get("klient") is not False
        wpis = {"tozsamosc": toz, "alias": alias(toz),
                "nazwa": None if klient else (k["nazwa"] if k else lokalne.get("nazwa")),
                "ostatni_commit": _iso_ts(k["commit_ts"]) if k else None,
                "ostatnia_sesja": _iso_ts(k["sesja_ts"]) if k else None}
        wpis.update(liczby_zadan(sciezka, teraz.date()))
        projekty.append(wpis)

    nowa_pamiec = {"ostatnie_zbieranie": czas, "ostatnie_zbieranie_ts": start_ts or teraz.timestamp(),
                   "znani": sorted(znani | set(kandydaci)),
                   "commity": dict(commity, **{t: k["hash"] for t, k in kandydaci.items() if k["hash"]})}
    nowe_aliasy = dict(aliasy)
    for toz, k in kandydaci.items():
        nowe_aliasy[toz] = {"nazwa": k["nazwa"], "sciezka": k["sciezka"], "zdalne": k["zdalne"]}
    return {"inwentarz": {"czas": czas, "kandydaci": inwentarz}, "stan": {"czas": czas, "projekty": projekty},
            "zdarzenia": zdarzenia, "pamiec": nowa_pamiec, "aliasy": nowe_aliasy}


def zbierz_dane(u):
    p = sciezki(u)
    pamiec = w.czytaj_json(p["pamiec"], {}) or {}
    decyzje = najnowsze_decyzje(p["decyzje"])
    aliasy = w.czytaj_json(p["aliasy"], {}) or {}
    start_ts = time.time()
    kandydaci, brak, nieczytelne = skanuj(u)
    return oblicz(pamiec, decyzje, kandydaci, brak, nieczytelne, aliasy, start_ts), decyzje


# ---------- git repozytorium stanu ----------

def _upewnij_tozsamosc_git(katalog):
    if not _git(katalog, "config", "user.email"):
        w.git(katalog, "config", "user.email", "zbieracz@mac.local")
    if not _git(katalog, "config", "user.name"):
        w.git(katalog, "config", "user.name", "zbieracz")


def _sprawdz_stan_dir(u):
    if not os.path.isdir(os.path.join(u["STAN_DIR"], ".git")):
        raise Blad("Brak repozytorium stanu w %s. Najpierw: python3 zbieracz.py init <adres-repo>" % u["STAN_DIR"])


def init(u, adres):
    stan = u["STAN_DIR"]
    if not os.path.isdir(os.path.join(stan, ".git")):
        if os.path.isdir(stan) and os.listdir(stan):
            raise Blad("Katalog %s istnieje i nie jest pusty." % stan)
        os.makedirs(os.path.dirname(stan) or ".", exist_ok=True)
        try:
            w.git(os.path.dirname(stan) or ".", "clone", "--quiet", adres, stan, timeout=300)
        except w.GitBlad as e:
            raise Blad("Nie udało się sklonować repozytorium: %s" % e)
    _upewnij_tozsamosc_git(stan)
    if not _git(stan, "ls-remote", "--heads", "origin"):
        w.git(stan, "symbolic-ref", "HEAD", "refs/heads/main")
        w.zapisz_atomowo(os.path.join(stan, ".gitignore"), "lokalne/\n*.tmp\n")
        w.git(stan, "add", ".gitignore")
        w.git(stan, "commit", "--quiet", "-m", "init: repozytorium stanu")
        w.git(stan, "push", "--quiet", "origin", "refs/heads/main:refs/heads/main", timeout=300)
        w.git(stan, "checkout", "--quiet", "-b", "mac")
        w.git(stan, "push", "--quiet", "-u", "origin", "refs/heads/mac:refs/heads/mac", timeout=300)
        print("Założono repozytorium stanu (gałęzie main i mac).")
        return 0
    w.git(stan, "fetch", "--quiet", "origin", timeout=300)
    zdalne_galezie = _git(stan, "branch", "-r").split()
    if _git(stan, "rev-parse", "--verify", "--quiet", "refs/heads/mac"):
        w.git(stan, "checkout", "--quiet", "mac")
    elif "origin/mac" in zdalne_galezie:
        w.git(stan, "checkout", "--quiet", "-b", "mac", "--track", "origin/mac")
    else:
        baza = "origin/main" if "origin/main" in zdalne_galezie else "HEAD"
        w.git(stan, "checkout", "--quiet", "-b", "mac", baza)
        w.git(stan, "push", "--quiet", "-u", "origin", "refs/heads/mac:refs/heads/mac", timeout=300)
    print("Repozytorium stanu gotowe, gałąź mac.")
    return 0


def _przelacz_na_mac(stan):
    if _git(stan, "rev-parse", "--abbrev-ref", "HEAD") != "mac":
        try:
            w.git(stan, "checkout", "--quiet", "mac")
        except w.GitBlad as e:
            raise Blad("Nie mogę przełączyć repozytorium stanu na gałąź mac: %s" % e)


def zapisz_zdarzenia(katalog, zdarzenia):
    """Dopisuje do mac/zdarzenia/RRRR-MM-DD.jsonl zdarzenia, których id jeszcze tam nie ma."""
    dni = {}
    for z in zdarzenia:
        dni.setdefault((z.get("czas") or w.iso())[:10], []).append(z)
    for dzien, lista in sorted(dni.items()):
        plik = os.path.join(katalog, dzien + ".jsonl")
        dobre, _ = w.czytaj_jsonl(plik)
        ids = {d.get("id") for d in dobre}
        nowe = [z for z in lista if z["id"] not in ids]
        if nowe:
            w.dopisz_jsonl(plik, nowe)


def zatwierdz(stan, czas):
    """Commit wyłącznie katalogu mac/. True, gdy powstał commit."""
    w.git(stan, "add", "--all", "--", "mac")
    zmienione = [x for x in _git(stan, "diff", "--cached", "--name-only").splitlines() if x]
    obce = [x for x in zmienione if not x.startswith("mac/")]
    if obce:
        w.git(stan, "reset", "--quiet")
        raise Blad("W indeksie są pliki spoza mac/; przerywam bez commita.")
    if not zmienione:
        return False
    w.git(stan, "commit", "--quiet", "-m", "mac: zbieranie %s" % czas, "--", "mac")
    return True


def wypchnij(stan):
    """Push gałęzi mac z ponowieniami. True przy sukcesie."""
    for proba in range(PONOWIENIA + 1):
        try:
            w.git(stan, "push", "--quiet", "origin", "refs/heads/mac:refs/heads/mac", timeout=120)
            return True
        except Exception:
            if proba < PONOWIENIA:
                time.sleep(PRZERWY_S[min(proba, len(PRZERWY_S) - 1)])
    return False


# ---------- polecenia ----------

def zbierz(u):
    _sprawdz_stan_dir(u)
    p = sciezki(u)
    stan = u["STAN_DIR"]
    with Blokada(p["blokada"]):
        _przelacz_na_mac(stan)
        _upewnij_tozsamosc_git(stan)
        wynik, _ = zbierz_dane(u)
        w.zapisz_json(p["aliasy"], wynik["aliasy"])
        w.zapisz_json(p["inwentarz"], wynik["inwentarz"])
        w.zapisz_json(p["stan"], wynik["stan"])
        kolejka, _ = w.czytaj_jsonl(p["kolejka"])
        kolejka = ogranicz_kolejke(kolejka + wynik["zdarzenia"])
        zapisz_jsonl(p["kolejka"], kolejka)
        w.zapisz_json(p["pamiec"], wynik["pamiec"])
        zapisz_zdarzenia(p["zdarzenia"], kolejka)
        zatwierdz(stan, wynik["inwentarz"]["czas"])
        if wypchnij(stan):
            zapisz_jsonl(p["kolejka"], [])
            w.ping(u.get("HC_ZBIERACZ"))
            print("Zebrano: kandydaci %d, projekty %d, zdarzenia %d. Wypchnięto."
                  % (len(wynik["inwentarz"]["kandydaci"]), len(wynik["stan"]["projekty"]), len(kolejka)))
            return 0
        z = zdarzenie_bez_id("push-nieudany", "mac", wynik["inwentarz"]["czas"][:10])
        zapisz_jsonl(p["kolejka"], ogranicz_kolejke(kolejka + [z]))
        print("Wypchnięcie nieudane po %d ponowieniach. Zdarzenia w kolejce: %d." % (PONOWIENIA, len(kolejka) + 1))
        return 1


def podglad(u):
    wynik, decyzje = zbierz_dane(u)
    kand = wynik["inwentarz"]["kandydaci"]
    typy = {}
    for z in wynik["zdarzenia"]:
        typy[z["typ"]] = typy.get(z["typ"], 0) + 1
    print("Kandydaci: %d (bez decyzji: %d)" % (len(kand), sum(1 for k in kand if k["tozsamosc"] not in decyzje)))
    print("Projekty w stan.json: %d" % len(wynik["stan"]["projekty"]))
    print("Nowe zdarzenia: %d%s" % (len(wynik["zdarzenia"]), "".join(
        "\n  %s: %d" % (t, n) for t, n in sorted(typy.items()))))
    return 0


def kandydaci(u):
    p = sciezki(u)
    aliasy = w.czytaj_json(p["aliasy"], {}) or {}
    inw = w.czytaj_json(p["inwentarz"])
    if inw is None:
        wynik, _ = zbierz_dane(u)
        inw, aliasy = wynik["inwentarz"], wynik["aliasy"]
    decyzje = najnowsze_decyzje(p["decyzje"])
    lista = sorted(inw.get("kandydaci", []), key=lambda k: k.get("ostatnia_aktywnosc") or "", reverse=True)
    if not lista:
        print("Brak kandydatów.")
        return 0
    for k in lista:
        a = aliasy.get(k["tozsamosc"], {})
        d = decyzje.get(k["tozsamosc"])
        print("%-12s %-10s %-16s commity %-5d sesje %-4d %-10s %s  %s" % (
            k["tozsamosc"], k["alias"], d["stan"] if d else "bez decyzji", k["commity"], k["sesje"],
            (k.get("ostatnia_aktywnosc") or "-")[:10], a.get("nazwa", "?"), a.get("sciezka", "?")))
    return 0


def _pytanie(pytaj, tekst):
    try:
        return pytaj(tekst).strip()
    except EOFError:
        return "k"


def kwalifikuj(u, pytaj=input, wypisz=print, zbieraj=True):
    _sprawdz_stan_dir(u)
    p = sciezki(u)
    _przelacz_na_mac(u["STAN_DIR"])
    wynik, decyzje = zbierz_dane(u)
    aliasy = wynik["aliasy"]
    w.zapisz_json(p["aliasy"], aliasy)
    bez = [k for k in wynik["inwentarz"]["kandydaci"] if k["tozsamosc"] not in decyzje]
    if not bez:
        wypisz("Brak kandydatów bez decyzji.")
    menu = ", ".join("%d %s" % (i + 1, s) for i, s in enumerate(STANY))
    znane_aliasy = {d.get("alias"): t for t, d in decyzje.items() if d.get("alias")}
    nowe = 0
    for i, k in enumerate(bez, 1):
        a = aliasy.get(k["tozsamosc"], {})
        wypisz("\n[%d/%d] %s  %s\n      commity %d, sesje %d, ostatnio %s" % (
            i, len(bez), a.get("nazwa", "?"), a.get("sciezka", "?"), k["commity"], k["sesje"],
            (k.get("ostatnia_aktywnosc") or "-")[:10]))
        odp = _pytanie(pytaj, "Stan (%s; Enter pomiń, k koniec): " % menu).lower()
        if odp in ("k", "q"):
            break
        if not odp:
            continue
        if odp.isdigit() and 1 <= int(odp) <= len(STANY):
            stan = STANY[int(odp) - 1]
        elif odp in STANY:
            stan = odp
        else:
            wypisz("Nieznany stan, pomijam.")
            continue
        klient, alias, scalony_z = True, k["alias"], None
        if stan == "scalony":
            cel = _pytanie(pytaj, "Scalony z (alias albo tożsamość): ")
            scalony_z = znane_aliasy.get(cel) or (cel if cel in decyzje or cel in aliasy else None)
            if not scalony_z:
                wypisz("Nie znam takiego projektu, pomijam.")
                continue
        elif stan != "wykluczony":
            klient = _pytanie(pytaj, "Klient? [T/n]: ").lower() not in ("n", "nie")
            while True:
                alias = _pytanie(pytaj, "Alias [%s]: " % k["alias"]) or k["alias"]
                if klient and alias.lower() == (a.get("nazwa") or "").lower():
                    wypisz("Alias projektu klienckiego nie może być jego nazwą.")
                    continue
                break
        d = {"czas": w.iso(), "tozsamosc": k["tozsamosc"], "stan": stan, "alias": alias, "klient": klient,
             "scalony_z": scalony_z}
        w.dopisz_jsonl(p["decyzje"], [d])
        decyzje[k["tozsamosc"]] = d
        znane_aliasy[alias] = k["tozsamosc"]
        nowe += 1
    wypisz("\nZapisano decyzji: %d." % nowe)
    return zbierz(u) if zbieraj else 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    u = w.ustawienia()
    polecenie = argv[0] if argv else "zbierz"
    try:
        if polecenie == "init":
            if len(argv) != 2:
                raise Blad("Użycie: python3 zbieracz.py init <adres-repo>")
            return init(u, argv[1])
        if polecenie in ("zbierz", "podglad", "kandydaci", "kwalifikuj") and len(argv) <= 1:
            return {"zbierz": zbierz, "podglad": podglad, "kandydaci": kandydaci, "kwalifikuj": kwalifikuj}[polecenie](u)
        raise Blad("Polecenia: init <adres-repo>, zbierz, kandydaci, kwalifikuj, podglad")
    except Blad as e:
        print(e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
