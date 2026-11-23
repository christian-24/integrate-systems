"""Kopia projektu a GitHub (kopie.py, /api/github/*): lokalne repozytorium „bare” jako origin, bez sieci.

Stan przed/za, wysłanie, odrzucone wysłanie, klon na start, blokady usunięcia kopii, przeniesienie do kosza."""
import os
import subprocess
import unittest

from wspolne import Baza, projekt, server
import kopie  # noqa: E402  (ścieżkę do dashboard/ ustawia wspolne)

GIT_ID = ["-c", "user.name=Test", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", "-c", "init.defaultBranch=main"]


def git(cwd, *args):
    r = subprocess.run(["git", *GIT_ID, *args], cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        raise AssertionError("git %s: %s" % (" ".join(args), r.stderr))
    return r.stdout.strip()


class KopiaBaza(Baza):
    github = "firma/strona"

    def setUp(self):
        super().setUp()
        self._cards, self._url = projekt.CARDS, os.environ.get("PANEL_GITHUB_URL")
        projekt.CARDS = os.path.join(self.tmp, "karty")
        self.addCleanup(setattr, projekt, "CARDS", self._cards)
        self.addCleanup(self._restore_url)
        os.environ["PANEL_GITHUB_URL"] = os.path.join(self.tmp, "gh", "{repo}.git")
        self.bare = os.path.join(self.tmp, "gh", self.github + ".git")
        os.makedirs(self.bare)
        git(self.bare, "init", "-q", "--bare")
        # karta i zadania w „IntegrateSystems/szkice/<projekt>”, w folderze projektu dowiązania (jak na serwerze)
        cards = os.path.join(projekt.CARDS, "projekt-testowy")
        os.makedirs(cards)
        for n in ("KARTA.md", "ZADANIA.md", "DECYZJE.md"):
            os.replace(os.path.join(self.folder, n), os.path.join(cards, n))
            os.symlink(os.path.join(cards, n), os.path.join(self.folder, n))
        self.card_field("github", self.github)
        git(self.folder, "init", "-q")
        git(self.folder, "remote", "add", "origin", self.bare)
        with open(os.path.join(self.folder, ".git", "info", "exclude"), "a", encoding="utf-8") as f:
            f.write("KARTA.md\nZADANIA.md\nDECYZJE.md\n")
        git(self.folder, "add", "-A")
        git(self.folder, "commit", "-q", "-m", "start")
        git(self.folder, "push", "-q", "-u", "origin", "main")
        # druga osoba z własną kopią (nowsze commity na GitHubie)
        self.other = os.path.join(self.tmp, "inna-kopia")
        git(self.tmp, "clone", "-q", self.bare, self.other)

    def _restore_url(self):
        if self._url is None:
            os.environ.pop("PANEL_GITHUB_URL", None)
        else:
            os.environ["PANEL_GITHUB_URL"] = self._url

    def card_field(self, key, value):
        path = os.path.join(self.folder, "KARTA.md")
        with open(path, encoding="utf-8") as f:
            lines = f.read().split("\n")
        i = next(n for n, line in enumerate(lines) if line.startswith("# "))
        lines.insert(i + 1, "- %s: %s" % (key, value))
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def commit(self, where, name, text="x"):
        with open(os.path.join(where, name), "w", encoding="utf-8") as f:
            f.write(text)
        git(where, "add", name)
        git(where, "commit", "-q", "-m", name)

    def pid(self):
        return server.load_projects(resolve=False)[0]["projects"][0]["id"]

    def api(self, fn, **body):
        r = fn(dict(body, project=self.pid()))
        return r[0], r[1], (r[2] if len(r) > 2 else {})


class Stan(KopiaBaza):
    def test_przed_i_za_origin_po_sprawdzeniu(self):
        self.commit(self.folder, "lokalny.txt")
        self.commit(self.other, "zdalny.txt")
        git(self.other, "push", "-q", "origin", "main")
        code, _, out = self.api(server.github_state)
        st = out["state"]
        self.assertEqual((code, st["branch"], st["ahead"], st["behind"]), (200, "main", 1, 0))
        self.assertEqual(st["remoteBranch"], "origin/main")
        self.assertTrue(st["originOk"])
        code, _, out = self.api(server.github_state, fetch=True)       # „Sprawdź”: git fetch
        self.assertEqual(code, 200, out)
        self.assertEqual((out["state"]["ahead"], out["state"]["behind"]), (1, 1))
        self.assertTrue(out["state"]["fetchedAt"])

    def test_galezie_bez_odpowiednika_i_pliki(self):
        git(self.folder, "branch", "agent/2026-11-23-wizytowka")
        git(self.folder, "checkout", "-q", "-b", "nowa")
        self.commit(self.folder, "nowa.txt")
        git(self.folder, "checkout", "-q", "main")
        for rel in ("brudny.txt", ".agent/x/plik", "node_modules/a/b.js", ".zrzuty/z.png", "site/dist/index.html"):
            os.makedirs(os.path.dirname(os.path.join(self.folder, rel)) or self.folder, exist_ok=True)
            with open(os.path.join(self.folder, rel), "w", encoding="utf-8") as f:
                f.write("x")
        st = self.api(server.github_state)[2]["state"]
        by = {b["name"]: b for b in st["branches"]}
        self.assertEqual(by["nowa"]["remote"], "")
        self.assertEqual(by["nowa"]["unpushed"], 1)
        self.assertTrue(by["agent/2026-11-23-wizytowka"]["agent"])
        self.assertEqual(by["agent/2026-11-23-wizytowka"]["unpushed"], 0)    # ten sam commit co origin/main
        self.assertEqual([d["path"] for d in st["dirty"]], ["brudny.txt"])     # bez .agent, node_modules, zrzutów, dist
        self.assertTrue(st["cardsLinked"])

    def test_adres_bez_danych_logowania(self):
        git(self.folder, "remote", "set-url", "origin", "https://x:ghp_TAJNY@github.com/firma/strona.git")
        st = self.api(server.github_state)[2]["state"]
        self.assertEqual(st["origin"], "https://github.com/firma/strona.git")
        self.assertTrue(st["originOk"])


class Wyslanie(KopiaBaza):
    def test_wyslano_potem_nic_do_wyslania(self):
        self.commit(self.folder, "a.txt")
        code, err, out = self.api(server.github_push)
        self.assertEqual((code, out["result"]), (200, "sent"), err)
        self.assertEqual(git(self.bare, "rev-parse", "main"), git(self.folder, "rev-parse", "HEAD"))
        self.assertEqual(out["state"]["ahead"], 0)
        code, _, out = self.api(server.github_push)
        self.assertEqual((code, out["result"]), (200, "nothing"))

    def test_wybrana_galaz_dodatkowo(self):
        git(self.folder, "checkout", "-q", "-b", "agent/2026-11-23-x")
        self.commit(self.folder, "b.txt")
        git(self.folder, "checkout", "-q", "main")
        code, err, out = self.api(server.github_push, branches=["agent/2026-11-23-x"])
        self.assertEqual(code, 200, err)
        self.assertEqual(git(self.bare, "rev-parse", "agent/2026-11-23-x"), git(self.folder, "rev-parse", "agent/2026-11-23-x"))
        self.assertEqual(self.api(server.github_push, branches=["nie-ma"])[0], 400)

    def test_odrzucone_bez_force(self):
        self.commit(self.other, "zdalny.txt")
        git(self.other, "push", "-q", "origin", "main")
        remote_head = git(self.bare, "rev-parse", "main")
        self.commit(self.folder, "lokalny.txt")
        code, err, out = self.api(server.github_push)
        self.assertEqual((code, out["result"]), (409, "rejected"))
        self.assertIn("nowsze commity", err)
        self.assertEqual(git(self.bare, "rev-parse", "main"), remote_head)      # GitHub bez zmian

    def test_brak_repozytorium_na_github(self):
        git(self.folder, "remote", "set-url", "origin", os.path.join(self.tmp, "gh", "nie", "ma.git"))
        self.commit(self.folder, "a.txt")
        st = self.api(server.github_state)[2]["state"]
        self.assertFalse(st["originOk"])
        code, err, _ = self.api(server.github_push)
        self.assertEqual(code, 409)                 # origin nie zgadza się z polem github:
        self.assertIn("inne repozytorium", err)

    def test_komunikat_braku_dostepu(self):
        kind, msg = kopie.net_error("git@github.com: Permission denied (publickey).\nfatal: Could not read from remote "
                                    "repository.", "firma/strona")
        self.assertEqual(kind, "access")
        self.assertIn("klucz", msg)
        self.assertEqual(kopie.net_error("timeout")[0], "timeout")
        self.assertEqual(kopie.net_error("ERROR: Repository not found.")[0], "missing")


class Usuniecie(KopiaBaza):
    def blocks(self):
        return self.api(server.github_state)[2]["state"]["blocks"]

    def test_blokady(self):
        self.assertEqual(self.blocks(), [])
        with open(os.path.join(self.folder, "nowy.txt"), "w", encoding="utf-8") as f:
            f.write("x")
        self.assertTrue(any(b.startswith("Pliki niezatwierdzone") for b in self.blocks()))
        os.unlink(os.path.join(self.folder, "nowy.txt"))
        git(self.folder, "checkout", "-q", "-b", "agent/2026-11-23-y")
        self.commit(self.folder, "y.txt")
        git(self.folder, "checkout", "-q", "main")
        self.assertTrue(any("agent/2026-11-23-y (1)" in b for b in self.blocks()))
        code, err, _ = self.api(server.github_remove, confirm=True)
        self.assertEqual(code, 409)
        self.assertIn("niewysłane", err)
        self.assertTrue(os.path.isdir(os.path.join(self.folder, ".git")))
        # gałąź scalona w gałąź, która jest na GitHubie, nie blokuje
        git(self.folder, "merge", "-q", "--ff-only", "agent/2026-11-23-y")
        git(self.folder, "push", "-q", "origin", "main")
        self.assertEqual(self.blocks(), [])

    def test_agent_pracuje(self):
        self.manager.has_live = lambda pid: True
        self.assertIn("Agent pracuje w projekcie", self.blocks())
        self.assertEqual(self.api(server.github_remove, confirm=True)[0], 409)

    def test_bez_pola_github_i_bez_potwierdzenia(self):
        self.assertEqual(self.api(server.github_remove)[0], 400)
        path = os.path.join(self.folder, "KARTA.md")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        with open(path, "w", encoding="utf-8") as f:
            f.write(text.replace("- github: %s\n" % self.github, ""))
        self.assertIn("Brak pola github: w karcie", self.blocks())

    def test_kosz_i_klon_na_start(self):
        code, err, out = self.api(server.github_remove, confirm=True)
        self.assertEqual(code, 200, err)
        trash = os.path.join(self.tmp, ".kosz", "projekt-testowy-" + server.datetime.date.today().isoformat())
        self.assertTrue(os.path.isdir(os.path.join(trash, ".git")))          # przeniesione, nie skasowane
        self.assertEqual(sorted(os.listdir(self.folder)), sorted(["KARTA.md", "ZADANIA.md", "DECYZJE.md", kopie.MARKER]))
        self.assertTrue(out["state"]["stub"])
        data, _ = server.load_projects()                                      # projekt zostaje z kartą i zadaniami
        self.assertEqual(data["projects"][0]["github"], self.github)
        self.assertTrue(any(t["title"] == "Zadanie A" for t in data["tasks"]))
        # druga osoba wysyła zmianę; klon na start bierze stan z GitHuba
        self.commit(self.other, "z-githuba.txt")
        git(self.other, "push", "-q", "origin", "main")
        code, err, extra = self.run_task("Zadanie A")
        self.assertEqual(code, 200, err)
        rec = self.wait(extra["id"])
        self.assertTrue(any("Sklonowano z GitHuba: firma/strona" in s["text"] for s in rec["steps"]))
        self.assertTrue(os.path.isfile(os.path.join(self.folder, "z-githuba.txt")))
        self.assertTrue(os.path.islink(os.path.join(self.folder, "KARTA.md")))
        self.assertFalse(os.path.exists(os.path.join(self.folder, kopie.MARKER)))
        st = self.api(server.github_state)[2]["state"]
        self.assertEqual(st["dirty"], [])                                     # dowiązania karty w exclude
        self.assertTrue(st["repo"])
        # drugi raz tego samego dnia: osobny katalog w koszu
        self.assertEqual(kopie.trash_path(self.folder), trash + "-2")

    def test_klon_wybranej_galezi(self):
        git(self.other, "checkout", "-q", "-b", "nowa-koncepcja")
        self.commit(self.other, "koncepcja.txt")
        git(self.other, "push", "-q", "origin", "nowa-koncepcja")
        self.card_field("github gałąź", "nowa-koncepcja")
        self.assertEqual(self.api(server.github_remove, confirm=True)[0], 200)
        p = server.load_projects(resolve=False)[0]["projects"][0]
        ok, note = self.manager.ensure_copy(p, self.folder)
        self.assertTrue(ok, note)
        self.assertEqual(git(self.folder, "symbolic-ref", "--short", "HEAD"), "nowa-koncepcja")

    def test_blad_klonu_blokuje_uruchomienie(self):
        self.assertEqual(self.api(server.github_remove, confirm=True)[0], 200)
        os.rename(self.bare, self.bare + ".zniknelo")
        code, err, _ = self.run_task("Zadanie A")
        self.assertEqual(code, 409)
        self.assertIn("Nie sklonowano z GitHuba", err)
        self.assertIn("[ ] Zadanie A", self.row("Zadanie A"))                  # zadanie nie ruszyło
        self.assertTrue(os.path.islink(os.path.join(self.folder, "KARTA.md")))

    def test_folder_z_plikami_bez_repo_nie_jest_nadpisany(self):
        self.assertEqual(self.api(server.github_remove, confirm=True)[0], 200)
        with open(os.path.join(self.folder, "notatka.txt"), "w", encoding="utf-8") as f:
            f.write("ważne")
        code, err, _ = self.run_task("Zadanie A")
        self.assertEqual(code, 409)
        self.assertIn("nie nadpisze", err)


class PoleKarty(unittest.TestCase):
    def test_pola(self):
        f = projekt.card_fields({"github": "https://github.com/Firma/Strona.git", "github gałąź": "nowa-koncepcja"})
        self.assertEqual((f["github"], f["githubBranch"], f["errors"]), ("Firma/Strona", "nowa-koncepcja", []))
        f = projekt.card_fields({"github": "tylko-nazwa", "github gałąź": "zła gałąź"})
        self.assertEqual((f["github"], f["githubBranch"]), ("", ""))
        self.assertEqual(len(f["errors"]), 2)
        self.assertEqual(kopie.repo_name("git@github.com:firma/repo.git"), "firma/repo")
        self.assertEqual(kopie.repo_name("../etc"), "")


if __name__ == "__main__":
    unittest.main()
