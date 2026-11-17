"""Test całości etapu 1: zbieracz (Mac) → repozytorium „GitHub” (bare) → serce (PC) → bot (atrapa Telegrama).

Bez sieci i bez prawdziwych danych: wszystko w katalogu tymczasowym.
"""
import io
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

TU = os.path.dirname(os.path.abspath(__file__))
SYSTEM = os.path.dirname(TU)
sys.path[:0] = [SYSTEM, TU]

import wspolne  # noqa: E402
import zbieracz  # noqa: E402
import serce  # noqa: E402
from atrapa_telegram import AtrapaTelegram  # noqa: E402

TAJNE = ("KlientTajnySA", "backend-tajny", "Zadanie-tajne-123")
CHAT = 555


def sh(katalog, *args):
    subprocess.run(args, cwd=katalog, check=True, capture_output=True)


class Calosc(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        r = self.tmp.name
        cfg = os.path.join(r, "gitconfig")
        with open(cfg, "w") as f:
            f.write("[user]\n\tname = Wlasciciel\n\temail = wl@example.test\n[init]\n\tdefaultBranch = main\n"
                    "[commit]\n\tgpgsign = false\n")
        self.env = mock.patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": cfg, "GIT_CONFIG_NOSYSTEM": "1"})
        self.env.start()
        self.gh = os.path.join(r, "github", "stan.git")
        os.makedirs(self.gh)
        sh(self.gh, "git", "init", "--bare", "-b", "main")
        skan = os.path.join(r, "dom")
        # Backend: projekt kliencki z ZADANIA.md i tajną nazwą w adresie zdalnym
        self.backend = os.path.join(skan, "Documents", "backend-tajny")
        os.makedirs(self.backend)
        with open(os.path.join(self.backend, "ZADANIA.md"), "w", encoding="utf-8") as f:
            f.write("# Zadania\n\n## Etap: Start\ntermin: 2099-01-01\n\n"
                    "- [ ] Zadanie-tajne-123 | kto: claude\n"
                    "- [ ] Odbiór dla KlientTajnySA | kto: ty\n"
                    "- [ ] Zaległe | kto: claude | kiedy: 2020-01-01\n"
                    "- [x] Zrobione | kto: claude\n")
        for k in (["git", "init"], ["git", "add", "."], ["git", "commit", "-m", "start"],
                  ["git", "remote", "add", "origin", "git@github.com:KlientTajnySA/backend-tajny.git"]):
            sh(self.backend, *k)
        # TestNow bez ZADANIA.md, Turtle do backlogu
        for nazwa in ("TestNow", "Turtle"):
            p = os.path.join(skan, nazwa)
            os.makedirs(p)
            sh(p, "git", "init")
            sh(p, "git", "commit", "--allow-empty", "-m", "start")
        claude = os.path.join(r, "claude-projects")
        os.makedirs(os.path.join(claude, "-x-TestNow"))
        with open(os.path.join(claude, "-x-TestNow", "s.jsonl"), "w") as f:
            f.write('{"cwd": "%s", "message": "treść, której nie wolno czytać"}\n' % os.path.join(skan, "TestNow"))
        wspolne_env = {"SKANUJ": skan, "GLEBOKOSC": "3", "CLAUDE_PROJEKTY": claude, "HC_ZBIERACZ": "", "HC_SERCE": "",
                       "HC_RAPORT": "", "TELEGRAM_TOKEN": "", "TELEGRAM_CHAT": ""}
        self.mac = self._u(wspolne_env, STAN_DIR=os.path.join(r, "mac-stan"), LOKALNE_DIR=os.path.join(r, "mac-lok"))
        self.tg = AtrapaTelegram()
        self.pc = self._u(wspolne_env, STAN_DIR=os.path.join(r, "pc-stan"), LOKALNE_DIR=os.path.join(r, "pc-lok"),
                          TELEGRAM_TOKEN=self.tg.token, TELEGRAM_CHAT=str(CHAT), TELEGRAM_API=self.tg.adres,
                          CISZA="0-0", RAPORT_GODZINA="0")

    def tearDown(self):
        self.tg.zamknij()
        self.env.stop()
        self.tmp.cleanup()

    def _u(self, baza, **kw):
        with mock.patch.dict(os.environ, {**baza, **kw}):
            return wspolne.ustawienia(os.path.join(self.tmp.name, "brak.env"))

    def _cicho(self, fn, *a, **kw):
        with redirect_stdout(io.StringIO()):
            return fn(*a, **kw)

    def _mac_kwalifikuje(self):
        self._cicho(zbieracz.init, self.mac, self.gh)
        odpowiedzi = []
        decyzje = {"backend-tajny": ["1", "t", "Backend-A"], "TestNow": ["1", "n", "TestNow"],
                   "Turtle": ["2", "n", "Turtle"]}
        ostatnia = {"nazwa": None}

        def wypisz(tekst=""):
            for nazwa in decyzje:
                if "] %s " % nazwa in tekst:
                    ostatnia["nazwa"] = nazwa
                    odpowiedzi[:] = list(decyzje[nazwa])

        def pytaj(_):
            return odpowiedzi.pop(0) if odpowiedzi else ""
        self.assertEqual(zbieracz.STANY[0], "w realizacji")
        self.assertEqual(zbieracz.STANY[1], "backlog")
        self._cicho(zbieracz.kwalifikuj, self.mac, pytaj=pytaj, wypisz=wypisz)

    def _serce(self):
        s = serce.Serce(self.pc, serce.Telegram(self.tg.adres, self.tg.token), sleep=lambda *_: None)
        return s

    def test_od_maca_do_telefonu(self):
        self._mac_kwalifikuje()
        with mock.patch.dict(os.environ, {"STAN_DIR": self.pc["STAN_DIR"], "LOKALNE_DIR": self.pc["LOKALNE_DIR"]}):
            self._cicho(serce.main, ["init", self.gh])
        s = self._serce()
        t = wspolne.teraz()
        self.assertTrue(s.cykl_git(t))
        self.tg.tekst(CHAT, "/stan")
        self.tg.tekst(CHAT, "/pomysl Wrócić do Turtle")
        self.tg.tekst(999, "/stan")                       # obce konto
        s.odbierz(timeout=0)
        self.assertTrue(s.cykl_git(t))                    # pomysł trafia do GitHuba
        odp = [x for x in self.tg.wyslane if str(x.get("chat_id")) == str(CHAT)]
        stan = next(x["text"] for x in odp if x["text"].startswith("Stan"))
        self.assertIn("Backend-A", stan)
        self.assertIn("TestNow", stan)
        self.assertIn("Turtle", stan)
        self.assertNotIn("KlientTajnySA", stan)
        self.assertNotIn("backend-tajny", stan)
        self.assertNotIn("Zadanie-tajne", stan)
        self.assertRegex(stan, r"Backend-A.*otwarte 3")
        self.assertRegex(stan, r"czeka na Ciebie 1")
        self.assertRegex(stan, r"po terminie 1")
        self.assertIn("brak ZADANIA.md", stan)
        self.assertFalse([x for x in self.tg.wyslane if str(x.get("chat_id")) == "999"])
        # GitHub: żadnej tajnej nazwy w żadnym obiekcie żadnej gałęzi
        obiekty = subprocess.run(["git", "rev-list", "--all", "--objects"], cwd=self.gh, capture_output=True,
                                 text=True, check=True).stdout.split()
        tresc = ""
        for o in set(obiekty):
            if len(o) == 40:
                tresc += subprocess.run(["git", "cat-file", "-p", o], cwd=self.gh, capture_output=True,
                                        text=True).stdout
        for tajne in TAJNE + ("treść, której nie wolno czytać", self.tmp.name):
            self.assertNotIn(tajne, tresc, tajne)
        self.assertIn("Wrócić do Turtle", tresc)
        # gałąź mac zmienia tylko mac/
        pliki_mac = subprocess.run(["git", "ls-tree", "-r", "--name-only", "mac"], cwd=self.gh,
                                   capture_output=True, text=True, check=True).stdout.split()
        self.assertTrue(pliki_mac and all(p.startswith("mac/") or p == ".gitignore" for p in pliki_mac), pliki_mac)

    def test_raport_z_danymi_z_maca(self):
        self._mac_kwalifikuje()
        with mock.patch.dict(os.environ, {"STAN_DIR": self.pc["STAN_DIR"], "LOKALNE_DIR": self.pc["LOKALNE_DIR"]}):
            self._cicho(serce.main, ["init", self.gh])
        s = self._serce()
        t = wspolne.teraz()
        self.assertTrue(s.cykl_git(t))
        self.assertTrue(s.raport_jesli_pora(t))
        self.assertFalse(s.raport_jesli_pora(t))          # raz dziennie
        raport = self.tg.teksty()[-1]
        if os.environ.get("POKAZ"):
            print("\n" + raport)
        self.assertIn("Backend-A", raport)
        self.assertNotIn("backend-tajny", raport)


if __name__ == "__main__":
    unittest.main()
