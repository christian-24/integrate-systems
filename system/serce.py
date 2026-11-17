"""Serce etapu 1 (PC): scalanie gałęzi mac, bot Telegram, raport dzienny, sygnał życia. Kontrakt: KONTRAKT.md.

Uruchomienie:
  python serce.py        pętla (zadanie Harmonogramu zadań)
  python serce.py raz    jeden cykl git i raport, gdy pora
  python serce.py chat   wypisuje chat_id z ostatnich wiadomości do bota (do ustawienia TELEGRAM_CHAT)
  python serce.py init <adres-repo>   klonuje repozytorium stanu do STAN_DIR
"""
import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wspolne  # noqa: E402

LIMIT_PILNYCH = 5
PROBY_PUSH = 3
COFNIJ_H = 24
PRZERWA_H = 24
SWIEZOSC_H = 26
AWARIA_MIN = 30
STANY_AKTYWNE = (("w realizacji", "W realizacji"), ("w przygotowaniu", "W przygotowaniu"),
                 ("wstrzymany", "Wstrzymane"))
STANY_DECYZJI = ("w realizacji", "backlog", "w przygotowaniu", "archiwum", "wykluczony", "scalony")
KOMENDY = "Komendy:\n/stan — stan projektów\n/pomysl <tekst> — zapisz pomysł"
GIT_AUTOR = ("-c", "user.name=serce", "-c", "user.email=serce@localhost", "-c", "commit.gpgsign=false")


def lokalnie(t):
    """Czas świadomy strefy → Europe/Warsaw."""
    utc = t.astimezone(datetime.timezone.utc)
    return utc.astimezone(wspolne._strefa_dla(utc))


def hhmm(t):
    return lokalnie(t).strftime("%H:%M")


# ---------- Telegram ----------

class TelegramBlad(Exception):
    pass


class Telegram:
    """Klient Bot API przez urllib. Błędy nigdy nie zawierają tokenu."""

    def __init__(self, api, token):
        self.api = (api or "https://api.telegram.org").rstrip("/")
        self.token = token

    def _wywolaj(self, metoda, dane, timeout=15):
        url = "%s/bot%s/%s" % (self.api, self.token, metoda)
        req = urllib.request.Request(url, data=json.dumps(dane).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                odp = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            try:
                opis = json.loads(e.read().decode("utf-8")).get("description", "")
            except Exception:
                opis = ""
            raise TelegramBlad("%s HTTP %s %s" % (metoda, e.code, opis[:100]).replace(self.token, "***"))
        except Exception as e:
            raise TelegramBlad(("%s %s: %s" % (metoda, type(e).__name__, e)).replace(self.token, "***"))
        if not odp.get("ok"):
            raise TelegramBlad(("%s: %s" % (metoda, odp.get("description", "")))[:200].replace(self.token, "***"))
        return odp.get("result")

    def get_updates(self, offset=None, timeout=25):
        dane = {"timeout": timeout, "allowed_updates": ["message", "callback_query"]}
        if offset is not None:
            dane["offset"] = offset
        return self._wywolaj("getUpdates", dane, timeout=timeout + 10) or []

    def send(self, chat_id, tekst, przyciski=None):
        dane = {"chat_id": chat_id, "text": tekst, "disable_web_page_preview": True}
        if przyciski:
            dane["reply_markup"] = {"inline_keyboard": przyciski}
        return (self._wywolaj("sendMessage", dane) or {}).get("message_id")

    def answer_callback(self, callback_id, tekst=None):
        dane = {"callback_query_id": callback_id}
        if tekst:
            dane["text"] = tekst
        return self._wywolaj("answerCallbackQuery", dane)

    def edit(self, chat_id, message_id, tekst):
        return self._wywolaj("editMessageText", {"chat_id": chat_id, "message_id": message_id, "text": tekst})


# ---------- blokada jednego procesu ----------

class Blokada:
    """Blokada pliku na czas życia procesu (msvcrt na Windows, fcntl gdzie indziej)."""

    def __init__(self, sciezka):
        self.sciezka = sciezka
        self.f = None

    def zajmij(self):
        os.makedirs(os.path.dirname(self.sciezka), exist_ok=True)
        f = open(self.sciezka, "a+")
        try:
            if os.name == "nt":
                import msvcrt
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            f.close()
            return False
        self.f = f
        return True

    def zwolnij(self):
        if self.f:
            self.f.close()
            self.f = None


# ---------- serce ----------

class Serce:
    def __init__(self, u, tg=None, sleep=time.sleep):
        self.u = u
        self.tg = tg
        self.sleep = sleep
        self.stan_dir = u["STAN_DIR"]
        self.lokalne = u["LOKALNE_DIR"]
        self.chat = str(u.get("TELEGRAM_CHAT") or "").strip()
        self.godzina_raportu = _int(u.get("RAPORT_GODZINA"), 7)
        self.cisza = _cisza(u.get("CISZA"))
        self.cykl_s = _int(u.get("CYKL_S"), 300)
        self.proby_push = 0
        self.plik_stanu = os.path.join(self.lokalne, "serce.json")
        self.plik_dziennika = os.path.join(self.lokalne, "dziennik.log")
        self.stan = self.wczytaj_stan()

    # --- stan procesu i dziennik ---

    def wczytaj_stan(self):
        s = wspolne.czytaj_json(self.plik_stanu, {}) or {}
        s.setdefault("offset", None)
        s.setdefault("ostatni_cykl", None)
        s.setdefault("ostatnio_dziala", None)
        s.setdefault("raport_data", None)
        s.setdefault("pilne", {"data": None, "liczba": 0})
        s.setdefault("pomysly", [])
        s.setdefault("kolejka", [])
        s.setdefault("nieudany_od", None)
        s.setdefault("push_zgloszony", False)
        s.setdefault("awaria_zgloszona", False)
        return s

    def zapisz_stan(self, teraz=None):
        granica = (teraz or wspolne.teraz()) - datetime.timedelta(hours=COFNIJ_H)
        self.stan["pomysly"] = [p for p in self.stan["pomysly"]
                                if (wspolne.z_iso(p.get("czas")) or granica) > granica]
        wspolne.zapisz_json(self.plik_stanu, self.stan)

    def dziennik(self, tekst, teraz=None):
        token = self.u.get("TELEGRAM_TOKEN") or ""
        if token:
            tekst = tekst.replace(token, "***")
        try:
            os.makedirs(self.lokalne, exist_ok=True)
            if os.path.isfile(self.plik_dziennika) and os.path.getsize(self.plik_dziennika) > 1000000:
                os.replace(self.plik_dziennika, self.plik_dziennika + ".1")
            with open(self.plik_dziennika, "a", encoding="utf-8", newline="\n") as f:
                f.write("%s %s\n" % (wspolne.iso(teraz), tekst.replace("\n", " ")))
        except OSError:
            pass

    # --- pliki repozytorium stanu ---

    def p(self, *czesci):
        return os.path.join(self.stan_dir, *czesci)

    def zdarzenie(self, typ, waga, tytul, teraz, projekt=None):
        z = {"id": wspolne.id_skrot("pc", typ, wspolne.iso(teraz)), "zrodlo": "pc", "czas": wspolne.iso(teraz),
             "projekt": projekt, "typ": typ, "waga": waga, "tytul": tytul, "link": None}
        wspolne.dopisz_jsonl(self.p("pc", "zdarzenia", lokalnie(teraz).strftime("%Y-%m-%d") + ".jsonl"), [z])
        return z

    # --- wysyłanie ---

    def _do_wlasciciela(self, tekst, przyciski=None):
        if not self.tg or not self.chat:
            print("[bez Telegrama] " + tekst)
            return True
        self.tg.send(self.chat, tekst, przyciski)
        return True

    def w_ciszy(self, teraz):
        od, do = self.cisza
        h = lokalnie(teraz).hour
        if od == do:
            return False
        return (h >= od or h < do) if od > do else (od <= h < do)

    def wyslij_wlasne(self, tekst, teraz, pilne=False, awaria=False, rodzaj=None):
        """Wiadomość z własnej inicjatywy. Zwraca 'wyslano', 'kolejka' albo 'limit'."""
        if awaria:
            try:
                self._do_wlasciciela("System nie działa: " + tekst)
                self.dziennik("wysłano: awaria", teraz)
                return "wyslano"
            except Exception as e:
                self.dziennik("błąd wysyłania awarii: %s" % e, teraz)
                self.stan["kolejka"].insert(0, {"tekst": "System nie działa: " + tekst, "rodzaj": None})
                return "kolejka"
        if pilne:
            dzis = lokalnie(teraz).strftime("%Y-%m-%d")
            if self.stan["pilne"].get("data") != dzis:
                self.stan["pilne"] = {"data": dzis, "liczba": 0}
            if self.stan["pilne"]["liczba"] >= LIMIT_PILNYCH:
                self.dziennik("pominięto pilne: limit %d dziennie" % LIMIT_PILNYCH, teraz)
                return "limit"
            self.stan["pilne"]["liczba"] += 1
            tekst = "Pilne: " + tekst
        if rodzaj:
            self.stan["kolejka"] = [k for k in self.stan["kolejka"] if k.get("rodzaj") != rodzaj]
        self.stan["kolejka"].append({"tekst": tekst, "rodzaj": rodzaj})
        if self.w_ciszy(teraz):
            return "kolejka"
        self.oprozni_kolejke(teraz)
        return "wyslano" if not self.stan["kolejka"] else "kolejka"

    def oprozni_kolejke(self, teraz):
        if self.w_ciszy(teraz):
            return
        while self.stan["kolejka"]:
            try:
                self._do_wlasciciela(self.stan["kolejka"][0]["tekst"])
            except Exception as e:
                self.dziennik("błąd wysyłania: %s" % e, teraz)
                return
            self.stan["kolejka"].pop(0)

    # --- start po przerwie ---

    def start(self, teraz):
        poprzednio = wspolne.z_iso(self.stan.get("ostatnio_dziala"))
        if poprzednio and teraz - poprzednio > datetime.timedelta(hours=PRZERWA_H):
            self.zdarzenie("system-wznowiony", "info", "System wznowiony", teraz)
            self.wyslij_wlasne("System działa ponownie od %s. Wiadomości wysłane w czasie przerwy mogły zginąć."
                               % hhmm(teraz), teraz)
            self.dziennik("start po przerwie od %s" % wspolne.iso(poprzednio), teraz)
        else:
            self.dziennik("start", teraz)
        self.stan["ostatnio_dziala"] = wspolne.iso(teraz)
        self.zapisz_stan(teraz)

    # --- bot ---

    def odbierz(self, teraz_fn=wspolne.teraz, timeout=25):
        """Jeden long polling; obsługa wszystkich aktualizacji."""
        if not self.tg:
            return 0
        off = self.stan.get("offset")
        aktualizacje = self.tg.get_updates(off, timeout)
        for upd in aktualizacje:
            try:
                self.obsluz(upd, teraz_fn())
            except Exception as e:
                self.dziennik("błąd obsługi aktualizacji: %s %s" % (type(e).__name__, e), teraz_fn())
            self.stan["offset"] = upd.get("update_id", 0) + 1
            self.zapisz_stan(teraz_fn())
        return len(aktualizacje)

    def _dozwolony(self, chat):
        return bool(self.chat) and chat.get("type") == "private" and str(chat.get("id")) == self.chat

    def obsluz(self, upd, teraz):
        t0 = time.monotonic()
        if "callback_query" in upd:
            return self._obsluz_przycisk(upd["callback_query"], teraz)
        msg = upd.get("message")
        if not msg:
            return
        chat = msg.get("chat") or {}
        if not self._dozwolony(chat):
            self.dziennik("odrzucono wiadomość: chat_id=%s typ=%s" % (chat.get("id"), chat.get("type")), teraz)
            return
        tekst = msg.get("text")
        if tekst is None:
            self._do_wlasciciela("Obsługuję tylko tekst.")
            self.dziennik("odpowiedź: nie tekst", teraz)
            return
        tekst = tekst.strip()
        komenda, _, reszta = tekst.partition(" ")
        komenda = komenda.split("@")[0].lower()
        if komenda == "/stan":
            self._do_wlasciciela(self.tekst_stanu(teraz))
        elif komenda in ("/pomysl", "/pomysł"):
            reszta = " ".join(reszta.split())
            if not reszta:
                self._do_wlasciciela("Użycie: /pomysl <tekst>")
            else:
                pid = self.dodaj_pomysl(reszta, teraz)
                self._do_wlasciciela("Zapisano pomysł.", [[{"text": "Cofnij", "callback_data": "cofnij:" + pid}]])
        else:
            komenda = "inne"
            self._do_wlasciciela(KOMENDY)
        self.dziennik("odpowiedź %s %d ms" % (komenda, (time.monotonic() - t0) * 1000), teraz)

    def _obsluz_przycisk(self, cq, teraz):
        chat = (cq.get("message") or {}).get("chat") or {}
        if not self._dozwolony(chat) or str((cq.get("from") or {}).get("id")) != self.chat:
            self.dziennik("odrzucono przycisk: chat_id=%s" % chat.get("id"), teraz)
            return
        dane = cq.get("data") or ""
        if not dane.startswith("cofnij:"):
            self.tg.answer_callback(cq.get("id"))
            return
        wynik = self.cofnij_pomysl(dane.split(":", 1)[1], teraz)
        odp = {"cofnieto": "Cofnięto.", "minelo": "Minęło 24 h, nie można cofnąć.",
               "brak": "Nie znaleziono pomysłu."}[wynik]
        self.tg.answer_callback(cq.get("id"), odp)
        if wynik == "cofnieto":
            self.tg.edit(chat.get("id"), cq["message"].get("message_id"), "Pomysł cofnięty.")
        self.dziennik("przycisk cofnij: %s" % wynik, teraz)

    # --- pomysły ---

    def dodaj_pomysl(self, tekst, teraz):
        pid = wspolne.id_skrot("pomysl", wspolne.iso(teraz), tekst)[:8]
        plik = self.p("pomysly.md")
        try:
            with open(plik, encoding="utf-8") as f:
                stary = f.read()
        except OSError:
            stary = ""
        if stary and not stary.endswith("\n"):
            stary += "\n"
        wspolne.zapisz_atomowo(plik, stary + "- %s | %s | %s\n" % (lokalnie(teraz).strftime("%Y-%m-%d %H:%M"),
                                                                    pid, tekst))
        self.stan["pomysly"].append({"id": pid, "czas": wspolne.iso(teraz)})
        self.zapisz_stan(teraz)
        return pid

    def cofnij_pomysl(self, pid, teraz):
        wpis = next((p for p in self.stan["pomysly"] if p.get("id") == pid), None)
        if wpis is None:
            return "brak"
        czas = wspolne.z_iso(wpis.get("czas"))
        if not czas or teraz - czas > datetime.timedelta(hours=COFNIJ_H):
            return "minelo"
        plik = self.p("pomysly.md")
        try:
            with open(plik, encoding="utf-8") as f:
                wiersze = f.readlines()
        except OSError:
            wiersze = []
        nowe = [w for w in wiersze if _pole(w, 1) != pid]
        if len(nowe) == len(wiersze):
            return "brak"
        wspolne.zapisz_atomowo(plik, "".join(nowe))
        self.stan["pomysly"] = [p for p in self.stan["pomysly"] if p.get("id") != pid]
        self.zapisz_stan(teraz)
        return "cofnieto"

    # --- stan i raport ---

    def tekst_stanu(self, teraz, naglowek="Stan"):
        mac = wspolne.czytaj_json(self.p("mac", "stan.json"), {}) or {}
        inw = wspolne.czytaj_json(self.p("mac", "inwentarz.json"), {}) or {}
        projekty = {p.get("tozsamosc"): p for p in
                    (wspolne.czytaj_json(self.p("projekty.json"), {}) or {}).get("projekty", [])
                    if isinstance(p, dict)}
        czas_mac = wspolne.z_iso(mac.get("czas")) if isinstance(mac.get("czas"), str) else None
        if czas_mac:
            dane = hhmm(czas_mac) if lokalnie(czas_mac).date() == lokalnie(teraz).date() \
                else lokalnie(czas_mac).strftime("%d.%m %H:%M")
            wiersze = ["%s %s · dane z Maca %s" % (naglowek, hhmm(teraz), dane)]
        else:
            wiersze = ["%s %s · brak danych z Maca" % (naglowek, hhmm(teraz))]
        stany_mac = {s.get("tozsamosc"): s for s in mac.get("projekty", []) if isinstance(s, dict)}

        def etykieta(proj, s):
            if not proj.get("klient", True) and s and s.get("nazwa"):
                return str(s["nazwa"])
            return str(proj.get("alias") or wspolne.alias_tymczasowy(str(proj.get("tozsamosc") or "")))

        for stan, tytul in STANY_AKTYWNE:
            grupa = sorted((p for p in projekty.values() if p.get("stan") == stan),
                           key=lambda p: etykieta(p, stany_mac.get(p.get("tozsamosc"))).lower())
            if not grupa:
                continue
            wiersze.append(tytul)
            for proj in grupa:
                s = stany_mac.get(proj.get("tozsamosc"))
                nazwa = etykieta(proj, s)
                if not s:
                    wiersze.append("%s — brak danych z Maca" % nazwa)
                elif not s.get("ma_zadania"):
                    wiersze.append("%s — brak ZADANIA.md" % nazwa)
                else:
                    w = "%s — otwarte %d · czeka na Ciebie %d · po terminie %d" % (
                        nazwa, _int(s.get("otwarte")), _int(s.get("czeka_na_ciebie")), _int(s.get("po_terminie")))
                    if _int(s.get("zablokowane")):
                        w += " · zablokowane %d" % _int(s.get("zablokowane"))
                    wiersze.append(w)
        backlog = sorted(etykieta(p, stany_mac.get(p.get("tozsamosc"))) for p in projekty.values()
                         if p.get("stan") == "backlog")
        if backlog:
            wiersze.append("Backlog: " + ", ".join(backlog))
        kandydaci = [k for k in inw.get("kandydaci", []) if isinstance(k, dict)]
        bez = sum(1 for k in kandydaci if k.get("tozsamosc") not in projekty)
        wiersze.append("Kandydaci bez decyzji: %d" % bez)
        return "\n".join(wiersze)

    def tekst_raportu(self, teraz):
        wiersze = [self.tekst_stanu(teraz, "Raport")]
        mac = wspolne.czytaj_json(self.p("mac", "stan.json"), {}) or {}
        czas_mac = wspolne.z_iso(mac.get("czas")) if isinstance(mac.get("czas"), str) else None
        if not czas_mac or teraz - czas_mac > datetime.timedelta(hours=SWIEZOSC_H):
            wiersze.append("Uwaga: dane z Maca starsze niż %d h" % SWIEZOSC_H)
        doba = teraz - datetime.timedelta(hours=24)
        pomysly = 0
        try:
            with open(self.p("pomysly.md"), encoding="utf-8") as f:
                for w in f:
                    pole = _pole(w, 0)
                    try:
                        t = datetime.datetime.strptime(pole.lstrip("- ").strip(), "%Y-%m-%d %H:%M")
                    except ValueError:
                        continue
                    if t >= lokalnie(doba).replace(tzinfo=None):
                        pomysly += 1
        except OSError:
            pass
        odrzucone, _ = wspolne.czytaj_jsonl(self.p("pc", "odrzucone.jsonl"))
        nowe_odrz = sum(1 for o in odrzucone if (wspolne.z_iso(o.get("czas")) or doba) > doba)
        wiersze.append("Pomysły z doby: %d" % pomysly)
        wiersze.append("Odrzucone wiersze z doby: %d" % nowe_odrz)
        return "\n".join(wiersze)

    def raport_jesli_pora(self, teraz):
        """Raport raz na lokalną datę, od RAPORT_GODZINA (odporne na zmianę czasu i przestój)."""
        lok = lokalnie(teraz)
        dzis = lok.strftime("%Y-%m-%d")
        if lok.hour < self.godzina_raportu or self.stan.get("raport_data") == dzis:
            return False
        self.stan["raport_data"] = dzis
        self.wyslij_wlasne(self.tekst_raportu(teraz), teraz, rodzaj="raport")
        self.zapisz_stan(teraz)
        wspolne.ping(self.u.get("HC_RAPORT"))
        self.dziennik("raport %s" % dzis, teraz)
        return True

    # --- cykl git ---

    def _git(self, *args, sprawdz=True):
        return wspolne.git(self.stan_dir, *args, sprawdz=sprawdz)

    def przepisz_projekty(self, teraz):
        decyzje, zle = wspolne.czytaj_jsonl(self.p("mac", "decyzje.jsonl"))
        odrzuc = [("mac/decyzje.jsonl", w) for w in zle]
        ostatnie = {}
        for d in decyzje:
            if not isinstance(d.get("tozsamosc"), str) or d.get("stan") not in STANY_DECYZJI:
                odrzuc.append(("mac/decyzje.jsonl", json.dumps(d, ensure_ascii=False, sort_keys=True)))
                continue
            ostatnie[d["tozsamosc"]] = d
        projekty = [{"tozsamosc": t, "alias": str(d.get("alias") or wspolne.alias_tymczasowy(t)),
                     "stan": d["stan"], "klient": d.get("klient") is not False, "obszar": "praca",
                     "zdecydowano": d.get("czas"), "scalony_z": d.get("scalony_z")}
                    for t, d in ostatnie.items()]
        projekty.sort(key=lambda p: (p["alias"].lower(), p["tozsamosc"]))
        wspolne.zapisz_json(self.p("projekty.json"), {"projekty": projekty})
        katalog = self.p("mac", "zdarzenia")
        if os.path.isdir(katalog):
            for nazwa in sorted(os.listdir(katalog)):
                if nazwa.endswith(".jsonl"):
                    _, zle = wspolne.czytaj_jsonl(os.path.join(katalog, nazwa))
                    odrzuc += [("mac/zdarzenia/" + nazwa, w) for w in zle]
        self.zapisz_odrzucone(odrzuc, teraz)
        return projekty

    def zapisz_odrzucone(self, odrzuc, teraz):
        if not odrzuc:
            return 0
        plik = self.p("pc", "odrzucone.jsonl")
        znane = {o.get("id") for o in wspolne.czytaj_jsonl(plik)[0]}
        nowe = []
        for zrodlo, wiersz in odrzuc:
            wiersz = wiersz if isinstance(wiersz, str) else json.dumps(wiersz, ensure_ascii=False)
            oid = wspolne.id_skrot(zrodlo, wiersz)
            if oid in znane:
                continue
            znane.add(oid)
            nowe.append({"id": oid, "czas": wspolne.iso(teraz), "plik": zrodlo, "wiersz": wiersz[:500]})
        if nowe:
            wspolne.dopisz_jsonl(plik, nowe)
            self.dziennik("odrzucone wiersze: %d" % len(nowe), teraz)
        return len(nowe)

    def push(self, teraz):
        self.proby_push = 0
        for proba in range(1, PROBY_PUSH + 1):
            self.proby_push = proba
            try:
                self._git("push", "origin", "main")
                return True
            except Exception as e:
                self.dziennik("push nieudany (próba %d): %s" % (proba, e), teraz)
                if proba < PROBY_PUSH:
                    self.sleep(5 * proba)
        return False

    def cykl_git(self, teraz):
        """fetch, mac/ z origin/mac, projekty.json, commit, push. Zwraca True po udanym cyklu."""
        ok = False
        try:
            if not os.path.isdir(self.p(".git")):
                raise wspolne.GitBlad("brak repozytorium stanu w STAN_DIR")
            self._git("fetch", "origin")
            if self._git("rev-parse", "--abbrev-ref", "HEAD").strip() != "main":
                self._git("checkout", "main")
            ma_origin_main = bool(self._git("rev-parse", "--verify", "-q", "origin/main", sprawdz=False).strip())
            if ma_origin_main:
                self._git("merge", "--ff-only", "origin/main", sprawdz=False)
            if self._git("ls-tree", "-d", "origin/mac", "mac", sprawdz=False).strip():
                self._git("checkout", "origin/mac", "--", "mac/")
            self.przepisz_projekty(teraz)
            self._git("add", "-A")
            if self._git("status", "--porcelain").strip():
                self._git(*GIT_AUTOR, "commit", "-q", "-m", "serce: stan %s" % wspolne.iso(teraz))
            do_wyslania = True
            if ma_origin_main:
                do_wyslania = self._git("rev-list", "--count", "origin/main..main").strip() not in ("", "0")
            if do_wyslania and not self.push(teraz):
                if not self.stan.get("push_zgloszony"):
                    self.stan["push_zgloszony"] = True
                    self.zdarzenie("push-nieudany", "pilne", "Push nieudany", teraz)
                    self.wyslij_wlasne("push do GitHuba nieudany po %d próbach. Zmiany czekają lokalnie."
                                       % PROBY_PUSH, teraz, pilne=True)
                raise wspolne.GitBlad("push nieudany")
            ok = True
        except Exception as e:
            self.dziennik("cykl nieudany: %s" % e, teraz)
        if ok:
            self.stan.update({"ostatni_cykl": wspolne.iso(teraz), "nieudany_od": None,
                              "push_zgloszony": False, "awaria_zgloszona": False})
            wspolne.ping(self.u.get("HC_SERCE"))
        else:
            od = wspolne.z_iso(self.stan.get("nieudany_od"))
            if not od:
                self.stan["nieudany_od"] = wspolne.iso(teraz)
            elif (teraz - od >= datetime.timedelta(minutes=AWARIA_MIN)
                  and not self.stan.get("awaria_zgloszona")):
                self.stan["awaria_zgloszona"] = True
                self.wyslij_wlasne("cykl git nieudany od %s." % hhmm(od), teraz, awaria=True)
        self.zapisz_stan(teraz)
        return ok

    # --- pętla ---

    def petla(self, teraz_fn=wspolne.teraz):
        self.start(teraz_fn())
        nastepny = 0.0
        while True:
            try:
                t = teraz_fn()
                if time.monotonic() >= nastepny:
                    self.cykl_git(t)
                    nastepny = time.monotonic() + self.cykl_s
                self.raport_jesli_pora(t)
                self.oprozni_kolejke(t)
                self.stan["ostatnio_dziala"] = wspolne.iso(t)
                self.zapisz_stan(t)
                if self.tg:
                    self.odbierz(teraz_fn, timeout=25)
                else:
                    self.sleep(25)
            except KeyboardInterrupt:
                raise
            except Exception as e:
                self.dziennik("błąd pętli: %s %s" % (type(e).__name__, e), teraz_fn())
                self.sleep(10)


def _int(v, domyslnie=0):
    try:
        return int(v)
    except (TypeError, ValueError):
        return domyslnie


def _cisza(tekst):
    try:
        od, do = (int(x) for x in str(tekst).split("-"))
        if 0 <= od <= 23 and 0 <= do <= 23:
            return od, do
    except (TypeError, ValueError):
        pass
    return 22, 7


def _pole(wiersz, i):
    czesci = wiersz.rstrip("\n").split(" | ", 2)
    return czesci[i].strip() if len(czesci) == 3 else None


def lista_czatow(tg):
    """Unikalne czaty z oczekujących aktualizacji, bez zatwierdzania offsetu."""
    czaty = {}
    for upd in tg.get_updates(None, timeout=0):
        msg = upd.get("message") or (upd.get("callback_query") or {}).get("message") or {}
        nadawca = upd.get("message", {}).get("from") or (upd.get("callback_query") or {}).get("from") or {}
        chat = msg.get("chat") or {}
        if "id" in chat:
            czaty[chat["id"]] = (chat.get("type", "?"), nadawca.get("first_name") or chat.get("title") or "")
    return czaty


def _klient_tg(u):
    return Telegram(u["TELEGRAM_API"], u["TELEGRAM_TOKEN"]) if u.get("TELEGRAM_TOKEN") else None


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass
    u = wspolne.ustawienia()
    polecenie = argv[0] if argv else "petla"
    if polecenie == "chat":
        tg = _klient_tg(u)
        if not tg:
            print("Brak TELEGRAM_TOKEN.")
            return 2
        czaty = lista_czatow(tg)
        if not czaty:
            print("Brak wiadomości. Napisz do bota z telefonu i uruchom ponownie.")
        for cid, (typ, imie) in sorted(czaty.items()):
            print("%s\t%s\t%s" % (cid, typ, imie))
        return 0
    if polecenie == "init":
        if len(argv) < 2:
            print("Użycie: python serce.py init <adres-repo>")
            return 2
        if os.path.isdir(os.path.join(u["STAN_DIR"], ".git")):
            print("Repozytorium stanu już jest: " + u["STAN_DIR"])
            return 0
        os.makedirs(os.path.dirname(u["STAN_DIR"]), exist_ok=True)
        wspolne.git(os.path.dirname(u["STAN_DIR"]), "clone", argv[1], u["STAN_DIR"])
        wspolne.git(u["STAN_DIR"], "checkout", "main")
        print("Sklonowano do " + u["STAN_DIR"])
        return 0
    if polecenie not in ("petla", "raz"):
        print(__doc__)
        return 2
    blokada = Blokada(os.path.join(u["LOKALNE_DIR"], "serce.lock"))
    if not blokada.zajmij():
        print("Serce już działa.")
        return 0
    try:
        serce = Serce(u, _klient_tg(u))
        if polecenie == "raz":
            t = wspolne.teraz()
            ok = serce.cykl_git(t)
            if serce.tg:
                try:
                    print("wiadomości obsłużone: %d" % serce.odbierz(timeout=0))
                except Exception as e:
                    serce.dziennik("błąd Telegrama: %s" % e, t)
                    print("Telegram: błąd (szczegóły w dziennik.log)")
            raport = serce.raport_jesli_pora(t)
            serce.oprozni_kolejke(t)
            serce.zapisz_stan(t)
            print("cykl: %s · raport: %s" % ("udany" if ok else "nieudany (szczegóły w dziennik.log)",
                                            "wysłany" if raport else "nie teraz"))
            return 0 if ok else 1
        serce.petla()
    except KeyboardInterrupt:
        return 0
    finally:
        blokada.zwolnij()
    return 0


if __name__ == "__main__":
    sys.exit(main())
