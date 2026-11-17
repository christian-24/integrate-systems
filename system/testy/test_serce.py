"""Testy serca: atrapa Telegrama, atrapa healthchecks, lokalne repozytorium bare jako GitHub."""
import contextlib
import datetime
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

TU = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TU)
sys.path.insert(0, os.path.dirname(TU))

import wspolne  # noqa: E402
import serce  # noqa: E402
from atrapa_telegram import AtrapaHC, AtrapaTelegram  # noqa: E402

TOKEN = "123:TEST-nie-prawdziwy"
WLASCICIEL = 5550001
OBCY = 5550002
AUTOR = ("-c", "user.name=test", "-c", "user.email=test@localhost", "-c", "commit.gpgsign=false")

A, B, C, D = "aaaa11112222", "bbbb33334444", "cccc55556666", "dddd77778888"


def t(rok, mies, dzien, godz, minuta=0):
    """Czas lokalny Europe/Warsaw."""
    naiwny = datetime.datetime(rok, mies, dzien, godz, minuta)
    if wspolne.STREFA is not None:
        return naiwny.replace(tzinfo=wspolne.STREFA)
    utc = naiwny.replace(tzinfo=datetime.timezone.utc) - datetime.timedelta(hours=1)
    return utc.astimezone(wspolne._strefa_dla(utc))


def decyzja(czas, toz, stan, alias, klient):
    return {"czas": czas, "tozsamosc": toz, "stan": stan, "alias": alias, "klient": klient, "scalony_z": None}


def stan_projektu(toz, alias, nazwa, otwarte=0, czeka=0, po_terminie=0, zablokowane=0, ma_zadania=True):
    return {"tozsamosc": toz, "alias": alias, "nazwa": nazwa, "otwarte": otwarte, "zrobione": 2,
            "czeka_na_ciebie": czeka, "po_terminie": po_terminie, "zablokowane": zablokowane,
            "ma_zadania": ma_zadania, "ostatni_commit": None, "ostatnia_sesja": None}


@contextlib.contextmanager
def srodowisko(**env):
    stare = {k: os.environ.get(k) for k in env}
    os.environ.update(env)
    try:
        yield
    finally:
        for k, v in stare.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


class Baza(unittest.TestCase):
    CZAS_MAC = "2026-11-12T21:12:00+01:00"

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="serce-test-")
        self.bare = os.path.join(self.tmp, "github.git")
        os.makedirs(self.bare)
        wspolne.git(self.bare, "init", "-q", "--bare")
        self.mac = os.path.join(self.tmp, "mac-klon")
        wspolne.git(self.tmp, "clone", "-q", self.bare, self.mac)
        wspolne.git(self.mac, "checkout", "-q", "-b", "main")
        self.zapisz(self.mac, ".gitignore", "lokalne/\n*.tmp\n")
        self.commit(self.mac, "init")
        wspolne.git(self.mac, "push", "-q", "origin", "main")
        wspolne.git(self.mac, "checkout", "-q", "-b", "mac")
        self.decyzje = [
            decyzja("2026-11-01T10:00:00+01:00", A, "backlog", "Backend-A", True),
            decyzja("2026-11-02T10:00:00+01:00", A, "w realizacji", "Backend-A", True),
            decyzja("2026-11-02T10:01:00+01:00", B, "w realizacji", "K-bbbb", False),
            decyzja("2026-11-02T10:02:00+01:00", C, "backlog", "K-cccc", False),
            decyzja("2026-11-02T10:03:00+01:00", D, "backlog", "Sklep-B", True),
        ]
        self.wypchnij_mac(zepsuty=True)
        self.stan_dir = os.path.join(self.tmp, "stan")
        wspolne.git(self.tmp, "clone", "-q", self.bare, self.stan_dir)
        wspolne.git(self.stan_dir, "checkout", "-q", "main")
        self.lokalne = os.path.join(self.tmp, "lokalne")
        self.tg = AtrapaTelegram(TOKEN)
        self.hc = AtrapaHC()
        self.u = dict(wspolne.DOMYSLNE, STAN_DIR=self.stan_dir, LOKALNE_DIR=self.lokalne,
                      TELEGRAM_TOKEN=TOKEN, TELEGRAM_CHAT=str(WLASCICIEL), TELEGRAM_API=self.tg.adres,
                      HC_SERCE=self.hc.adres + "/serce", HC_RAPORT=self.hc.adres + "/raport")
        self.s = self.nowe_serce()

    def tearDown(self):
        self.tg.zamknij()
        self.hc.zamknij()
        shutil.rmtree(self.tmp, ignore_errors=True)

    # --- pomocnicze ---

    def nowe_serce(self):
        return serce.Serce(self.u, serce.Telegram(self.u["TELEGRAM_API"], TOKEN), sleep=lambda s: None)

    def zapisz(self, katalog, sciezka, tekst):
        pelna = os.path.join(katalog, *sciezka.split("/"))
        os.makedirs(os.path.dirname(pelna), exist_ok=True)
        with open(pelna, "w", encoding="utf-8", newline="\n") as f:
            f.write(tekst)

    def commit(self, katalog, opis):
        wspolne.git(katalog, "add", "-A")
        wspolne.git(katalog, *AUTOR, "commit", "-q", "-m", opis)

    def wypchnij_mac(self, zepsuty=False):
        stan = {"czas": self.CZAS_MAC, "projekty": [
            stan_projektu(A, "Backend-A", "TajnaNazwaKlienta", otwarte=4, czeka=1),
            stan_projektu(B, "K-bbbb", "TestNow", ma_zadania=False),
            stan_projektu(C, "K-cccc", "Turtle"),
            stan_projektu(D, "Sklep-B", None),
        ]}
        kandydaci = [{"tozsamosc": x, "alias": "K-" + x[:4], "zrodla": ["git"], "ostatnia_aktywnosc": None,
                      "commity": 3, "sesje": 0} for x in (A, B, C, D, "eeee00000000", "ffff00000000")]
        self.zapisz(self.mac, "mac/stan.json", json.dumps(stan, ensure_ascii=False))
        self.zapisz(self.mac, "mac/inwentarz.json", json.dumps({"czas": self.CZAS_MAC, "kandydaci": kandydaci}))
        wiersze = [json.dumps(d, ensure_ascii=False) for d in self.decyzje]
        if zepsuty:
            wiersze.insert(2, '{"czas": "2026-11-02T10:00:00+01:00", "tozsamosc": ')
        self.zapisz(self.mac, "mac/decyzje.jsonl", "\n".join(wiersze) + "\n")
        self.commit(self.mac, "mac")
        wspolne.git(self.mac, "push", "-q", "origin", "mac")

    def w_github(self, galaz, plik):
        return wspolne.git(self.bare, "show", "%s:%s" % (galaz, plik), sprawdz=False)

    def sha(self, galaz):
        return wspolne.git(self.bare, "rev-parse", galaz).strip()

    def dziennik(self):
        with open(os.path.join(self.lokalne, "dziennik.log"), encoding="utf-8") as f:
            return f.read()

    def odbierz(self, teraz):
        return self.s.odbierz(lambda: teraz, timeout=0)


class TestCyklGit(Baza):
    def test_projekty_z_decyzji_ostatnia_wygrywa_i_mac_nietkniety(self):
        mac_przed = self.sha("mac")
        self.assertTrue(self.s.cykl_git(t(2026, 11, 12, 21, 30)))
        projekty = {p["tozsamosc"]: p for p in json.loads(self.w_github("main", "projekty.json"))["projekty"]}
        self.assertEqual(projekty[A]["stan"], "w realizacji")
        self.assertEqual(projekty[A]["zdecydowano"], "2026-11-02T10:00:00+01:00")
        self.assertEqual(projekty[A]["obszar"], "praca")
        self.assertTrue(projekty[A]["klient"])
        self.assertFalse(projekty[B]["klient"])
        self.assertEqual(len(projekty), 4)
        self.assertIn("decyzje.jsonl", wspolne.git(self.bare, "ls-tree", "-r", "--name-only", "main", "mac"))
        self.assertEqual(self.sha("mac"), mac_przed)
        # druga zmiana na Macu: ostatnia decyzja znowu wygrywa
        self.decyzje.append(decyzja("2026-11-12T20:00:00+01:00", A, "archiwum", "Backend-A", True))
        self.wypchnij_mac(zepsuty=True)
        mac_przed = self.sha("mac")
        self.assertTrue(self.s.cykl_git(t(2026, 11, 12, 21, 35)))
        projekty = {p["tozsamosc"]: p for p in json.loads(self.w_github("main", "projekty.json"))["projekty"]}
        self.assertEqual(projekty[A]["stan"], "archiwum")
        self.assertEqual(self.sha("mac"), mac_przed)
        self.assertEqual(wspolne.git(self.bare, "for-each-ref", "--format=%(refname:short)", "refs/heads").split(), ["mac", "main"])

    def test_zepsuty_wiersz_do_odrzuconych_bez_duplikatow(self):
        self.s.cykl_git(t(2026, 11, 12, 21, 30))
        self.s.cykl_git(t(2026, 11, 12, 21, 35))
        wiersze = [json.loads(w) for w in self.w_github("main", "pc/odrzucone.jsonl").splitlines() if w]
        self.assertEqual(len(wiersze), 1)
        self.assertEqual(wiersze[0]["plik"], "mac/decyzje.jsonl")
        self.assertTrue(wiersze[0]["wiersz"].endswith('"tozsamosc":'))

    def test_ping_tylko_po_udanym_cyklu(self):
        self.assertTrue(self.s.cykl_git(t(2026, 11, 12, 12)))
        self.assertEqual(self.hc.ile("/serce"), 1)
        wspolne.git(self.stan_dir, "remote", "set-url", "--push", "origin", os.path.join(self.tmp, "nie-ma.git"))
        self.s.dodaj_pomysl("coś do wypchnięcia", t(2026, 11, 12, 12, 1))
        self.assertFalse(self.s.cykl_git(t(2026, 11, 12, 12, 5)))
        self.assertEqual(self.hc.ile("/serce"), 1)
        self.assertEqual(self.hc.ile("/raport"), 0)

    def test_push_nieudany_pilne_po_3_probach(self):
        wspolne.git(self.stan_dir, "remote", "set-url", "--push", "origin", os.path.join(self.tmp, "nie-ma.git"))
        teraz = t(2026, 11, 12, 12)
        self.assertFalse(self.s.cykl_git(teraz))
        self.assertEqual(self.s.proby_push, 3)
        pilne = [x for x in self.tg.teksty() if x.startswith("Pilne:")]
        self.assertEqual(len(pilne), 1)
        self.assertIn("push", pilne[0])
        z, _ = wspolne.czytaj_jsonl(os.path.join(self.stan_dir, "pc", "zdarzenia", "2026-11-12.jsonl"))
        self.assertEqual([(x["typ"], x["waga"]) for x in z], [("push-nieudany", "pilne")])
        # kolejny nieudany cykl nie powtarza pilnego; po 30 min „system nie działa”
        self.assertFalse(self.s.cykl_git(t(2026, 11, 12, 12, 5)))
        self.assertFalse(self.s.cykl_git(t(2026, 11, 12, 12, 35)))
        self.assertEqual(len([x for x in self.tg.teksty() if x.startswith("Pilne:")]), 1)
        self.assertEqual(len([x for x in self.tg.teksty() if x.startswith("System nie działa")]), 1)
        # naprawa: zdarzenie trafia do GitHuba
        wspolne.git(self.stan_dir, "remote", "set-url", "--push", "origin", self.bare)
        self.assertTrue(self.s.cykl_git(t(2026, 11, 12, 12, 40)))
        self.assertIn("push-nieudany", self.w_github("main", "pc/zdarzenia/2026-11-12.jsonl"))


class TestBot(Baza):
    def setUp(self):
        super().setUp()
        self.s.cykl_git(t(2026, 11, 12, 21, 30))

    def test_stan(self):
        teraz = t(2026, 11, 12, 21, 40)
        self.tg.tekst(WLASCICIEL, "/stan")
        self.assertEqual(self.odbierz(teraz), 1)
        odp = self.tg.teksty()[-1]
        self.assertEqual(odp.splitlines(), [
            "Stan 21:40 · dane z Maca 21:12",
            "W realizacji",
            "Backend-A — otwarte 4 · czeka na Ciebie 1 · po terminie 0",
            "TestNow — brak ZADANIA.md",
            "Backlog: Sklep-B, Turtle",
            "Kandydaci bez decyzji: 2",
        ])
        self.assertNotIn("TajnaNazwaKlienta", odp)
        self.assertIn("odpowiedź /stan", self.dziennik())
        # offset zatwierdzony: druga runda nic nie zwraca
        self.assertEqual(self.odbierz(teraz), 0)

    def test_stan_z_innego_dnia_i_cisza_nie_blokuje_odpowiedzi(self):
        teraz = t(2026, 11, 13, 23, 10)
        self.tg.tekst(WLASCICIEL, "/stan@moj_bot")
        self.odbierz(teraz)
        self.assertTrue(self.tg.teksty()[-1].startswith("Stan 23:10 · dane z Maca 12.11 21:12"))

    def test_pomysl_i_cofnij_w_repozytorium(self):
        teraz = t(2026, 11, 12, 21, 41)
        self.tg.tekst(WLASCICIEL, "/pomysl Wrócić do Turtle")
        self.odbierz(teraz)
        wiad = self.tg.wyslane[-1]
        self.assertEqual(wiad["text"], "Zapisano pomysł.")
        przycisk = wiad["reply_markup"]["inline_keyboard"][0][0]
        self.assertEqual(przycisk["text"], "Cofnij")
        self.assertTrue(przycisk["callback_data"].startswith("cofnij:"))
        pid = przycisk["callback_data"].split(":", 1)[1]
        self.assertTrue(self.s.cykl_git(t(2026, 11, 12, 21, 45)))
        self.assertEqual(self.w_github("main", "pomysly.md"), "- 2026-11-12 21:41 | %s | Wrócić do Turtle\n" % pid)
        stan = wspolne.czytaj_json(os.path.join(self.lokalne, "serce.json"))
        self.assertEqual([p["id"] for p in stan["pomysly"]], [pid])
        self.tg.przycisk(WLASCICIEL, przycisk["callback_data"], wiad["message_id"])
        self.odbierz(t(2026, 11, 12, 22, 0))
        self.assertEqual(self.tg.odpowiedzi[-1]["text"], "Cofnięto.")
        self.assertEqual(self.tg.edycje[-1]["message_id"], wiad["message_id"])
        self.assertTrue(self.s.cykl_git(t(2026, 11, 12, 22, 5)))
        self.assertNotIn("Turtle", self.w_github("main", "pomysly.md"))

    def test_cofnij_po_24h_nie_dziala(self):
        self.tg.tekst(WLASCICIEL, "/pomysl Stary pomysł")
        self.odbierz(t(2026, 11, 12, 10, 0))
        dane = self.tg.wyslane[-1]["reply_markup"]["inline_keyboard"][0][0]["callback_data"]
        self.assertEqual(self.s.cofnij_pomysl(dane.split(":")[1], t(2026, 11, 13, 10, 1)), "minelo")
        with open(os.path.join(self.stan_dir, "pomysly.md"), encoding="utf-8") as f:
            self.assertIn("Stary pomysł", f.read())

    def test_obcy_i_grupa_bez_odpowiedzi(self):
        teraz = t(2026, 11, 12, 21, 40)
        self.tg.tekst(OBCY, "/stan")
        self.tg.tekst(WLASCICIEL, "/stan", typ="group")
        self.tg.tekst(-100123, "/stan", typ="supergroup")
        self.tg.przycisk(OBCY, "cofnij:abcd", 5)
        self.assertEqual(self.odbierz(teraz), 4)
        self.assertEqual(self.tg.wyslane, [])
        self.assertEqual(self.tg.odpowiedzi, [])
        log = self.dziennik()
        self.assertIn("odrzucono wiadomość: chat_id=%d typ=private" % OBCY, log)
        self.assertIn("typ=group", log)
        self.assertIn("typ=supergroup", log)
        self.assertNotIn(TOKEN, log)

    def test_zdjecie_i_inna_komenda(self):
        teraz = t(2026, 11, 12, 21, 40)
        self.tg.zdjecie(WLASCICIEL)
        self.tg.tekst(WLASCICIEL, "/start")
        self.tg.tekst(WLASCICIEL, "/pomysl")
        self.odbierz(teraz)
        self.assertEqual(self.tg.teksty(), ["Obsługuję tylko tekst.", serce.KOMENDY, "Użycie: /pomysl <tekst>"])

    def test_polecenie_chat_bez_zatwierdzania_offsetu(self):
        self.tg.tekst(WLASCICIEL, "cześć", imie="Właściciel")
        self.tg.tekst(WLASCICIEL, "druga", imie="Właściciel")
        self.tg.tekst(-100777, "x", typ="group", imie="Ktoś")
        wyjscie = io.StringIO()
        with srodowisko(TELEGRAM_TOKEN=TOKEN, TELEGRAM_API=self.tg.adres, TELEGRAM_CHAT="",
                        SYSTEM_ENV=os.path.join(self.tmp, "brak")), contextlib.redirect_stdout(wyjscie):
            self.assertEqual(serce.main(["chat"]), 0)
        wiersze = wyjscie.getvalue().splitlines()
        self.assertEqual(wiersze, ["-100777\tgroup\tKtoś", "%d\tprivate\tWłaściciel" % WLASCICIEL])
        self.assertTrue(all("offset" not in d for m, d in self.tg.wywolania if m == "getUpdates"))
        self.assertEqual(self.tg.wyslane, [])
        self.assertEqual(len(self.tg.aktualizacje), 3)
        self.assertNotIn(TOKEN, wyjscie.getvalue())


    def test_polecenie_raz_cykl_i_odpowiedz(self):
        self.tg.tekst(WLASCICIEL, "/stan")
        env = {k: self.u[k] for k in ("STAN_DIR", "LOKALNE_DIR", "TELEGRAM_TOKEN", "TELEGRAM_CHAT", "TELEGRAM_API",
                                      "HC_SERCE", "HC_RAPORT")}
        wyjscie = io.StringIO()
        with srodowisko(SYSTEM_ENV=os.path.join(self.tmp, "brak"), **env), contextlib.redirect_stdout(wyjscie):
            self.assertEqual(serce.main(["raz"]), 0)
        self.assertIn("cykl: udany", wyjscie.getvalue())
        self.assertTrue(any(x.startswith("Stan ") for x in self.tg.teksty()))
        self.assertEqual(self.hc.ile("/serce"), 2)


class TestWiadomosciWlasne(Baza):
    def test_cisza_nocna_kolejka_do_7(self):
        self.assertEqual(self.s.wyslij_wlasne("informacja", t(2026, 11, 12, 23, 0)), "kolejka")
        self.s.oprozni_kolejke(t(2026, 11, 13, 6, 59))
        self.assertEqual(self.tg.wyslane, [])
        # stan przetrwa restart procesu
        self.s.zapisz_stan(t(2026, 11, 13, 6, 59))
        self.s = self.nowe_serce()
        self.s.oprozni_kolejke(t(2026, 11, 13, 7, 0))
        self.assertEqual(self.tg.teksty(), ["informacja"])

    def test_system_nie_dziala_mimo_ciszy_i_limitu(self):
        teraz = t(2026, 11, 12, 23, 30)
        for i in range(7):
            self.s.wyslij_wlasne("pilne %d" % i, t(2026, 11, 12, 12, i), pilne=True)
        self.assertEqual(self.s.wyslij_wlasne("brak cyklu", teraz, awaria=True), "wyslano")
        self.assertEqual(self.tg.teksty()[-1], "System nie działa: brak cyklu")

    def test_limit_5_pilnych_dziennie(self):
        wyniki = [self.s.wyslij_wlasne("p%d" % i, t(2026, 11, 12, 12, i), pilne=True) for i in range(7)]
        self.assertEqual(wyniki, ["wyslano"] * 5 + ["limit"] * 2)
        self.assertEqual(len(self.tg.wyslane), 5)
        self.assertIn("limit", self.dziennik())
        self.assertEqual(self.s.wyslij_wlasne("nowy dzień", t(2026, 11, 13, 12, 0), pilne=True), "wyslano")
        # pilne w ciszy czeka do 7:00
        self.assertEqual(self.s.wyslij_wlasne("nocne", t(2026, 11, 13, 23, 0), pilne=True), "kolejka")

    def test_komunikat_po_przerwie_ponad_24h(self):
        self.s.stan["ostatnio_dziala"] = wspolne.iso(t(2026, 11, 11, 9, 0))
        self.s.start(t(2026, 11, 12, 10, 15))
        self.assertEqual(self.tg.teksty(), [
            "System działa ponownie od 10:15. Wiadomości wysłane w czasie przerwy mogły zginąć."])
        z, _ = wspolne.czytaj_jsonl(os.path.join(self.stan_dir, "pc", "zdarzenia", "2026-11-12.jsonl"))
        self.assertEqual([x["typ"] for x in z], ["system-wznowiony"])

    def test_bez_komunikatu_po_krotkiej_przerwie(self):
        self.s.stan["ostatnio_dziala"] = wspolne.iso(t(2026, 11, 12, 8, 0))
        self.s.start(t(2026, 11, 12, 10, 15))
        self.s.start(t(2026, 11, 12, 10, 16))
        self.assertEqual(self.tg.wyslane, [])


class TestRaport(Baza):
    def setUp(self):
        super().setUp()
        self.s.cykl_git(t(2026, 11, 12, 21, 30))

    def wyslane_raporty(self):
        return [x for x in self.tg.teksty() if x.startswith("Raport")]

    def test_raport_tresc_i_ping(self):
        self.s.dodaj_pomysl("jeden", t(2026, 11, 13, 6, 0))
        self.assertFalse(self.s.raport_jesli_pora(t(2026, 11, 13, 6, 59)))
        self.assertTrue(self.s.raport_jesli_pora(t(2026, 11, 13, 7, 0)))
        self.assertFalse(self.s.raport_jesli_pora(t(2026, 11, 13, 7, 5)))
        raport = self.wyslane_raporty()
        self.assertEqual(len(raport), 1)
        self.assertTrue(raport[0].startswith("Raport 07:00 · dane z Maca 12.11 21:12"))
        self.assertIn("Pomysły z doby: 1", raport[0])
        self.assertIn("Odrzucone wiersze z doby: 1", raport[0])
        self.assertNotIn("starsze niż", raport[0])
        self.assertEqual(self.hc.ile("/raport"), 1)

    def test_ostrzezenie_o_starych_danych_i_zalegly_raport_jeden(self):
        self.assertTrue(self.s.raport_jesli_pora(t(2026, 11, 14, 15, 0)))
        self.assertFalse(self.s.raport_jesli_pora(t(2026, 11, 14, 16, 0)))
        raport = self.wyslane_raporty()
        self.assertEqual(len(raport), 1)
        self.assertIn("Uwaga: dane z Maca starsze niż 26 h", raport[0])

    def przebieg_doby(self, dzien):
        self.u["HC_RAPORT"] = ""
        self.s = self.nowe_serce()
        poczatek = t(*dzien, 0, 0).astimezone(datetime.timezone.utc)
        godziny = []
        for krok in range(0, 26 * 12):
            teraz = serce.lokalnie(poczatek + datetime.timedelta(minutes=5 * krok))
            if teraz.date() != datetime.date(*dzien):
                continue
            if self.s.raport_jesli_pora(teraz):
                godziny.append(teraz.strftime("%H:%M"))
        return godziny

    def test_raport_raz_przy_zmianie_czasu_jesienia(self):
        self.assertEqual(self.przebieg_doby((2026, 10, 25)), ["07:00"])

    def test_raport_raz_przy_zmianie_czasu_wiosna(self):
        self.assertEqual(self.przebieg_doby((2026, 3, 29)), ["07:00"])

    def test_raport_w_ciszy_czeka_i_nie_dubluje(self):
        self.u["RAPORT_GODZINA"] = "6"
        self.s = self.nowe_serce()
        self.assertTrue(self.s.raport_jesli_pora(t(2026, 11, 13, 6, 0)))
        self.assertEqual(self.wyslane_raporty(), [])
        self.s.oprozni_kolejke(t(2026, 11, 13, 7, 0))
        self.assertEqual(len(self.wyslane_raporty()), 1)


class TestBlokada(unittest.TestCase):
    def test_drugi_proces_nie_wejdzie(self):
        tmp = tempfile.mkdtemp(prefix="serce-blok-")
        try:
            sciezka = os.path.join(tmp, "serce.lock")
            a, b = serce.Blokada(sciezka), serce.Blokada(sciezka)
            self.assertTrue(a.zajmij())
            self.assertFalse(b.zajmij())
            a.zwolnij()
            self.assertTrue(b.zajmij())
            b.zwolnij()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
