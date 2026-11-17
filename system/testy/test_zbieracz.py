"""Testy zbieracza Maca. Wszystko w katalogach tymczasowych, bez sieci.

Fałszywy HOME z repozytoriami, fałszywy katalog sesji Claude, lokalne repozytorium bare jako „GitHub”.
"""
import contextlib
import io
import json
import os
import plistlib
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

SYSTEM = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SYSTEM)
import wspolne as w  # noqa: E402
import zbieracz  # noqa: E402

ZADANIA = """# Zadania

## Etap: Start
termin: 2999-12-31

- [ ] A | kto: ty
- [ ] B | wymaga: zgoda | kiedy: 2000-01-01
- [!] C | blokada: czeka na dostęp
- [x] D
- [~] E | kto: claude

## Etap: Stary
termin: 2000-01-01

- [ ] F | kto: claude

## Do rozplanowania

- [ ] G
"""
# Ręczny odczyt: otwarte A B C E F G, zrobione D, czeka na Ciebie A B, po terminie B (data) i F (etap), zablokowane C.
LICZBY = {"otwarte": 6, "zrobione": 1, "czeka_na_ciebie": 2, "po_terminie": 2, "zablokowane": 1, "ma_zadania": True}

# Słowa, które nie mogą trafić do repozytorium stanu (poza nazwą projektu z klient = false w stan.json).
TAJNE = ["tajnyklientalfa", "pustygamma", "sesjaepsilon", "obcyklon", "ukrytydelta", "SEKRETNA",
         "wlasciciel-repo", "zamkniety"]


def sh(katalog, *args, env=None):
    return subprocess.run(["git", *args], cwd=katalog, check=True, capture_output=True, text=True,
                          env=env).stdout.strip()


class Baza(unittest.TestCase):
    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp(prefix="zbieracz-test-"))
        self.addCleanup(self._sprzatnij)
        self.home = os.path.join(self.tmp, "home")
        self.stan = os.path.join(self.home, "stan-systemu")
        self.lokalne = os.path.join(self.home, ".integrate-lokalne")
        self.claude = os.path.join(self.home, ".claude", "projects")
        self.bare = os.path.join(self.tmp, "github", "stan.git")
        os.makedirs(self.home)
        with open(os.path.join(self.home, ".gitconfig"), "w") as f:
            f.write("[user]\n\temail = wlasciciel@example.test\n\tname = Wlasciciel\n"
                    "[init]\n\tdefaultBranch = main\n[commit]\n\tgpgsign = false\n")
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        env.update({
            "HOME": self.home, "XDG_CONFIG_HOME": os.path.join(self.home, ".config"),
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.path.join(self.home, ".gitconfig"),
            "SYSTEM_ENV": os.path.join(self.tmp, "brak.env"),
            "STAN_DIR": self.stan, "LOKALNE_DIR": self.lokalne, "SKANUJ": self.home, "GLEBOKOSC": "4",
            "CLAUDE_PROJEKTY": self.claude, "HC_ZBIERACZ": "",
        })
        p = mock.patch.dict(os.environ, env, clear=True)
        p.start()
        self.addCleanup(p.stop)
        p2 = mock.patch.object(zbieracz, "PRZERWY_S", (0, 0, 0))
        p2.start()
        self.addCleanup(p2.stop)

        kod = os.path.join(self.home, "kod")
        self.alfa = self.repo(os.path.join(kod, "tajnyklientalfa"), commity=2,
                              zdalne="https://token@github.com/wlasciciel/wlasciciel-repo.git", zadania=ZADANIA)
        self.beta = self.repo(os.path.join(kod, "jawnybeta"), commity=1, zadania=ZADANIA)
        self.gamma = self.repo(os.path.join(kod, "pustygamma"), commity=0)
        self.repo(os.path.join(kod, "obcyklon"), commity=3, zdalne="https://github.com/obcy/obcyklon.git",
                  autor="obcy@example.test")
        self.repo(os.path.join(kod, "web", "node_modules", "ukrytydelta"), commity=1)
        self.epsilon = os.path.join(self.home, "notatki", "sesjaepsilon")
        os.makedirs(self.epsilon)

        self.sesja(self.alfa + "/src", "a")
        self.sesja(self.alfa, "b")
        self.sesja(self.epsilon, "c")
        os.makedirs(os.path.dirname(self.bare))
        sh(self.tmp, "init", "--quiet", "--bare", self.bare)
        sh(self.bare, "symbolic-ref", "HEAD", "refs/heads/main")

    def _sprzatnij(self):
        for korzen, katalogi, _ in os.walk(self.tmp):
            for d in katalogi:
                try:
                    os.chmod(os.path.join(korzen, d), 0o755)
                except OSError:
                    pass
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ---------- pomocnicze ----------

    def repo(self, sciezka, commity=1, zdalne=None, autor=None, zadania=None):
        os.makedirs(sciezka)
        sh(sciezka, "init", "--quiet")
        if zadania:
            with open(os.path.join(sciezka, "ZADANIA.md"), "w", encoding="utf-8") as f:
                f.write(zadania)
        for i in range(commity):
            args = ["-c", "user.email=" + autor] if autor else []
            sh(sciezka, *args, "commit", "--quiet", "--allow-empty", "-m", "c%d" % i)
        if zdalne:
            sh(sciezka, "remote", "add", "origin", zdalne)
        return os.path.realpath(sciezka)

    def sesja(self, cwd, nazwa, tekst=None):
        katalog = os.path.join(self.claude, "-" + cwd.strip("/").replace("/", "-"))
        os.makedirs(katalog, exist_ok=True)
        plik = os.path.join(katalog, nazwa + ".jsonl")
        with open(plik, "w", encoding="utf-8") as f:
            f.write(tekst if tekst is not None else (
                json.dumps({"type": "summary", "summary": "SEKRETNA rozmowa"}) + "\n"
                + json.dumps({"type": "user", "cwd": cwd, "message": {"content": "SEKRETNA TRESC"}}) + "\n"))
        return plik

    def u(self):
        return w.ustawienia()

    def cicho(self, f, *a, **k):
        with contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()):
            wynik = f(*a, **k)
        return wynik, out.getvalue()

    def init(self):
        self.assertEqual(self.cicho(zbieracz.init, self.u(), self.bare)[0], 0)

    def zbierz(self):
        return self.cicho(zbieracz.zbierz, self.u())[0]

    def plik_z_bare(self, sciezka, galaz="mac"):
        return sh(self.bare, "show", "%s:%s" % (galaz, sciezka))

    def tresc_repozytorium(self):
        """Całe repozytorium bare: każdy obiekt (commity, drzewa z nazwami plików, pliki)."""
        obiekty = sh(self.bare, "rev-list", "--all", "--objects").split("\n")
        return "\n".join(sh(self.bare, "cat-file", "-p", o.split()[0]) for o in obiekty if o.strip())

    def toz(self, sciezka, zdalne=None):
        return w.tozsamosc(zdalne, sciezka)


class TestInit(Baza):
    def test_puste_repozytorium(self):
        self.init()
        galezie = sh(self.bare, "for-each-ref", "--format=%(refname:short)", "refs/heads").split()
        self.assertEqual(sorted(galezie), ["mac", "main"])
        gitignore = self.plik_z_bare(".gitignore", "main")
        self.assertIn("lokalne/", gitignore)
        self.assertIn("*.tmp", gitignore)
        self.assertEqual(sh(self.stan, "rev-parse", "--abbrev-ref", "HEAD"), "mac")

    def test_istniejace_repozytorium(self):
        self.init()
        self.zbierz()
        shutil.rmtree(self.stan)
        self.init()
        self.assertEqual(sh(self.stan, "rev-parse", "--abbrev-ref", "HEAD"), "mac")
        self.assertTrue(os.path.isfile(os.path.join(self.stan, "mac", "inwentarz.json")))

    def test_zbierz_bez_init(self):
        wynik, _ = self.cicho(zbieracz.main, ["zbierz"])
        self.assertEqual(wynik, 2)


class TestInwentarz(Baza):
    def test_kandydaci_i_brak_nazw_w_repozytorium(self):
        self.init()
        self.assertEqual(self.zbierz(), 0)
        inw = json.loads(self.plik_z_bare("mac/inwentarz.json"))
        kand = {k["tozsamosc"]: k for k in inw["kandydaci"]}
        t_alfa = self.toz(self.alfa, "https://github.com/wlasciciel/wlasciciel-repo")
        oczekiwane = {t_alfa, self.toz(self.beta), self.toz(self.gamma), self.toz(self.epsilon)}
        self.assertEqual(set(kand), oczekiwane)          # bez klonu obcego autora i bez node_modules
        self.assertEqual(kand[t_alfa]["zrodla"], ["claude", "git"])
        self.assertEqual(kand[t_alfa]["sesje"], 2)
        self.assertEqual(kand[t_alfa]["commity"], 2)
        self.assertEqual(kand[t_alfa]["alias"], "K-" + t_alfa[:4])
        self.assertEqual(kand[self.toz(self.gamma)]["commity"], 0)
        self.assertIsNone(kand[self.toz(self.gamma)]["ostatnia_aktywnosc"])
        self.assertEqual(kand[self.toz(self.epsilon)]["zrodla"], ["claude"])
        self.assertEqual(set(kand[t_alfa]), {"tozsamosc", "alias", "zrodla", "ostatnia_aktywnosc", "commity", "sesje"})

        tresc = self.tresc_repozytorium()
        for slowo in TAJNE + ["jawnybeta", self.home, "github.com/wlasciciel", "token"]:
            self.assertNotIn(slowo, tresc, slowo)

        aliasy = w.czytaj_json(os.path.join(self.lokalne, "aliasy.json"))
        self.assertEqual(aliasy[t_alfa]["nazwa"], "tajnyklientalfa")
        self.assertEqual(aliasy[t_alfa]["sciezka"], self.alfa)
        self.assertNotIn("token", aliasy[t_alfa]["zdalne"])
        zdarzenia = self.plik_z_bare("mac/zdarzenia/%s.jsonl" % w.teraz().date().isoformat())
        typy = [json.loads(x)["typ"] for x in zdarzenia.splitlines()]
        self.assertEqual(typy.count("kandydat"), 4)

    def test_podglad_bez_nazw_i_bez_zapisu(self):
        wynik, out = self.cicho(zbieracz.podglad, self.u())
        self.assertEqual(wynik, 0)
        self.assertIn("Kandydaci: 4 (bez decyzji: 4)", out)
        for slowo in TAJNE + ["jawnybeta", self.home]:
            self.assertNotIn(slowo, out)
        self.assertFalse(os.path.exists(self.lokalne))

    def test_kandydaci_na_ekran_z_nazwa(self):
        self.init()
        self.zbierz()
        _, out = self.cicho(zbieracz.kandydaci, self.u())
        self.assertIn("tajnyklientalfa", out)
        self.assertIn(self.alfa, out)


class Odpowiedzi:
    """Odpowiedzi na pytania kwalifikacji zależne od nazwy ostatnio pokazanego kandydata."""

    def __init__(self, plan):
        self.plan, self.biezacy, self.wypisane = plan, None, []

    def wypisz(self, tekst=""):
        self.wypisane.append(tekst)
        for nazwa in self.plan:
            if nazwa in tekst:
                self.biezacy = list(self.plan[nazwa])

    def pytaj(self, pytanie):
        return self.biezacy.pop(0) if self.biezacy else ""


class TestKwalifikacja(Baza):
    def kwalifikuj(self, plan):
        o = Odpowiedzi(plan)
        wynik, _ = self.cicho(zbieracz.kwalifikuj, self.u(), pytaj=o.pytaj, wypisz=o.wypisz)
        return wynik, o

    def test_decyzje_stan_i_nazwa_tylko_dla_nieklienckich(self):
        self.init()
        self.zbierz()
        wynik, o = self.kwalifikuj({
            "tajnyklientalfa": ["1", "", "tajnyklientalfa", "Backend-A"],   # alias = nazwa odrzucony
            "jawnybeta": ["2", "n", ""],
            "pustygamma": ["5"],
            "sesjaepsilon": [""],
        })
        self.assertEqual(wynik, 0)
        self.assertTrue(any("nie może być jego nazwą" in x for x in o.wypisane))
        t_alfa = self.toz(self.alfa, "https://github.com/wlasciciel/wlasciciel-repo")
        t_beta, t_gamma = self.toz(self.beta), self.toz(self.gamma)

        decyzje = [json.loads(x) for x in self.plik_z_bare("mac/decyzje.jsonl").splitlines()]
        po_toz = {d["tozsamosc"]: d for d in decyzje}
        self.assertEqual(set(po_toz), {t_alfa, t_beta, t_gamma})
        self.assertEqual((po_toz[t_alfa]["stan"], po_toz[t_alfa]["alias"], po_toz[t_alfa]["klient"]),
                         ("w realizacji", "Backend-A", True))
        self.assertEqual((po_toz[t_beta]["stan"], po_toz[t_beta]["klient"]), ("backlog", False))
        self.assertEqual(po_toz[t_gamma]["stan"], "wykluczony")
        for d in decyzje:
            self.assertEqual(set(d), {"czas", "tozsamosc", "stan", "alias", "klient", "scalony_z"})

        stan = json.loads(self.plik_z_bare("mac/stan.json"))
        projekty = {p["tozsamosc"]: p for p in stan["projekty"]}
        self.assertEqual(set(projekty), {t_alfa, t_beta})
        alfa, beta = projekty[t_alfa], projekty[t_beta]
        self.assertIsNone(alfa["nazwa"])
        self.assertEqual(alfa["alias"], "Backend-A")
        self.assertEqual(beta["nazwa"], "jawnybeta")
        for k, v in LICZBY.items():
            self.assertEqual(alfa[k], v, k)
            self.assertEqual(beta[k], v, k)
        self.assertIsNotNone(alfa["ostatni_commit"])
        self.assertIsNotNone(alfa["ostatnia_sesja"])
        self.assertIsNone(beta["ostatnia_sesja"])

        tresc = self.tresc_repozytorium()
        for slowo in TAJNE + [self.home]:
            self.assertNotIn(slowo, tresc, slowo)
        # nazwa nieklienckiego projektu występuje tylko w mac/stan.json
        for sciezka in sh(self.bare, "ls-tree", "-r", "--name-only", "mac").split():
            tekst = self.plik_z_bare(sciezka)
            self.assertEqual("jawnybeta" in tekst, sciezka == "mac/stan.json", sciezka)

        # druga kwalifikacja: tylko kandydat bez decyzji
        _, o2 = self.kwalifikuj({"sesjaepsilon": ["k"]})
        pokazane = [x for x in o2.wypisane if x.startswith("\n[")]
        self.assertEqual(len(pokazane), 1)
        self.assertIn("sesjaepsilon", pokazane[0])

    def test_projekt_bez_zadan(self):
        self.init()
        self.kwalifikuj({"sesjaepsilon": ["3", "", "Notatki"], "tajnyklientalfa": [""], "jawnybeta": [""],
                         "pustygamma": [""]})
        stan = json.loads(self.plik_z_bare("mac/stan.json"))
        self.assertEqual(len(stan["projekty"]), 1)
        p = stan["projekty"][0]
        self.assertEqual((p["alias"], p["ma_zadania"], p["otwarte"], p["ostatni_commit"]), ("Notatki", False, 0, None))


class TestLiczby(unittest.TestCase):
    def test_liczby_jak_pm(self):
        import datetime
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        with open(os.path.join(tmp, "ZADANIA.md"), "w", encoding="utf-8") as f:
            f.write(ZADANIA)
        self.assertEqual(zbieracz.liczby_zadan(tmp, datetime.date(2026, 11, 12)), LICZBY)
        self.assertFalse(zbieracz.liczby_zadan(os.path.join(tmp, "brak"), datetime.date(2026, 11, 12))["ma_zadania"])


class TestKolejka(Baza):
    def test_bez_sieci_i_wypchniecie_po_naprawie(self):
        self.init()
        self.assertEqual(self.zbierz(), 0)
        sh(self.stan, "remote", "set-url", "origin", os.path.join(self.tmp, "nie-ma.git"))
        sh(self.beta, "commit", "--quiet", "--allow-empty", "-m", "nowy")
        nowy_hash = sh(self.beta, "rev-parse", "HEAD")
        mac_przed = sh(self.bare, "rev-parse", "mac")

        with mock.patch.object(zbieracz.w, "ping") as ping:
            self.assertEqual(self.zbierz(), 1)
            ping.assert_not_called()
        self.assertEqual(sh(self.bare, "rev-parse", "mac"), mac_przed)
        kolejka, _ = w.czytaj_jsonl(os.path.join(self.lokalne, "kolejka.jsonl"))
        typy = [z["typ"] for z in kolejka]
        self.assertIn("commit", typy)
        self.assertIn("push-nieudany", typy)
        commit = next(z for z in kolejka if z["typ"] == "commit")
        self.assertEqual(commit["id"], "mac:repo:%s:%s" % (self.toz(self.beta), nowy_hash))
        self.assertEqual(commit["tytul"], "Nowy commit")
        self.assertIsNone(commit["link"])

        sh(self.stan, "remote", "set-url", "origin", self.bare)
        with mock.patch.dict(os.environ, {"HC_ZBIERACZ": "http://hc.test/zbieracz"}), \
                mock.patch.object(zbieracz.w, "ping") as ping:
            self.assertEqual(self.zbierz(), 0)
            ping.assert_called_once_with("http://hc.test/zbieracz")
        kolejka, _ = w.czytaj_jsonl(os.path.join(self.lokalne, "kolejka.jsonl"))
        self.assertEqual(kolejka, [])
        wszystkie = []
        for sciezka in sh(self.bare, "ls-tree", "-r", "--name-only", "mac", "mac/zdarzenia").split():
            wszystkie += [json.loads(x) for x in self.plik_z_bare(sciezka).splitlines()]
        ids = [z["id"] for z in wszystkie]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertIn(commit["id"], ids)
        self.assertIn("push-nieudany", [z["typ"] for z in wszystkie])
        # trzecie zbieranie bez zmian nie powtarza zdarzeń
        self.zbierz()
        self.assertEqual(sh(self.bare, "ls-tree", "-r", "--name-only", "mac", "mac/zdarzenia").split().__len__(),
                         len({z["czas"][:10] for z in wszystkie}))

    def test_limit_kolejki(self):
        zd = [{"id": str(i)} for i in range(zbieracz.KOLEJKA_MAX + 5)]
        out = zbieracz.ogranicz_kolejke(zd + [{"id": "3"}])
        self.assertEqual(len(out), zbieracz.KOLEJKA_MAX)
        self.assertEqual(out[0]["id"], "5")


class TestProblemy(Baza):
    def zdarzenia(self):
        wynik, _ = zbieracz.zbierz_dane(self.u())
        return wynik["zdarzenia"]

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "root ma dostęp do wszystkiego")
    def test_brak_dostepu(self):
        zamkniety = os.path.join(self.home, "zamkniety")
        os.makedirs(os.path.join(zamkniety, "repo"))
        os.chmod(zamkniety, 0)
        zd = [z for z in self.zdarzenia() if z["typ"] == "brak-dostepu"]
        self.assertEqual(len(zd), 1)
        self.assertEqual(zd[0]["tytul"], "Brak dostępu do katalogu")
        self.assertEqual(zd[0]["waga"], "info")
        self.assertNotIn("zamkniety", json.dumps(zd))

    def test_nieczytelny_plik_sesji(self):
        self.sesja("/x", "zepsuty", tekst="to nie jest json\n\x00\x01")
        self.sesja("/y", "bez-cwd", tekst=json.dumps({"type": "summary"}) + "\n")
        zd = [z for z in self.zdarzenia() if z["typ"] == "nie-rozumiem-pliku"]
        self.assertEqual(len(zd), 2)
        self.assertEqual(zd[0]["tytul"], "Nie rozumiem pliku sesji")
        self.assertIsNone(zd[0]["projekt"])

    def test_sesja_po_poprzednim_zbieraniu(self):
        self.init()
        self.zbierz()
        plik = self.sesja(self.alfa, "nowa")
        przyszlosc = time.time() + 5
        os.utime(plik, (przyszlosc, przyszlosc))
        zd = [z for z in self.zdarzenia() if z["typ"] == "sesja"]
        t_alfa = self.toz(self.alfa, "https://github.com/wlasciciel/wlasciciel-repo")
        self.assertEqual([z["id"] for z in zd], ["mac:sesja:%s:%s" % (t_alfa, w.z_timestamp(przyszlosc).date())])
        self.assertEqual(zd[0]["projekt"], "K-" + t_alfa[:4])


class TestGalaz(Baza):
    def test_push_tylko_mac_i_tylko_katalog_mac(self):
        self.init()
        main_po_init = sh(self.bare, "rev-parse", "main")
        with open(os.path.join(self.stan, "obcy.txt"), "w") as f:
            f.write("nie do repozytorium\n")
        self.assertEqual(self.zbierz(), 0)
        self.assertEqual(sh(self.bare, "rev-parse", "main"), main_po_init)
        zmienione = sh(self.bare, "diff", "--name-only", "main", "mac").split()
        self.assertTrue(zmienione)
        self.assertTrue(all(x.startswith("mac/") for x in zmienione), zmienione)
        self.assertEqual(sorted(sh(self.bare, "for-each-ref", "--format=%(refname:short)", "refs/heads").split()),
                         ["mac", "main"])

    def test_obcy_plik_w_indeksie_przerywa(self):
        self.init()
        mac_przed = sh(self.bare, "rev-parse", "mac")
        with open(os.path.join(self.stan, "obcy.txt"), "w") as f:
            f.write("x\n")
        sh(self.stan, "add", "obcy.txt")
        wynik, _ = self.cicho(zbieracz.main, ["zbierz"])
        self.assertEqual(wynik, 2)
        self.assertEqual(sh(self.bare, "rev-parse", "mac"), mac_przed)


class TestUruchom(unittest.TestCase):
    def test_szablon_plist(self):
        with open(os.path.join(SYSTEM, "uruchom", "pl.integrate.zbieracz.plist"), encoding="utf-8") as f:
            tekst = f.read()
        for znacznik in ("__PYTHON__", "__SYSTEM__", "__LOKALNE__"):
            self.assertIn(znacznik, tekst)
        tekst = (tekst.replace("__PYTHON__", "/usr/bin/python3").replace("__SYSTEM__", "/x/system")
                 .replace("__LOKALNE__", "/x/lok"))
        p = plistlib.loads(tekst.encode("utf-8"))
        self.assertTrue(p["RunAtLoad"])
        self.assertEqual(p["StartInterval"], 3600)
        self.assertEqual(p["ProgramArguments"], ["/usr/bin/python3", "/x/system/zbieracz.py", "zbierz"])
        skrypt = os.path.join(SYSTEM, "uruchom", "mac-zainstaluj.sh")
        self.assertTrue(os.stat(skrypt).st_mode & stat.S_IXUSR)
        subprocess.run(["sh", "-n", skrypt], check=True)


if __name__ == "__main__":
    unittest.main()
