"""Runda 3, agenci i serwer: gałąź uruchomienia w git worktree, changes, /api/agent/merge i /api/agent/diff,
materiał z wyniku dla następników, pełne szczegóły zadań Automatu, PANEL_AGENT_USER, zapis z loopback z kluczem,
nowe pola w /api/data."""
import datetime
import getpass
import json
import os
import shutil
import subprocess
import time
import unittest

from test_serwer import REMOTE, Serwer
from wspolne import TODAY, Baza, agents, projekt, server

GIT = shutil.which("git")
IDENT = ["-c", "user.name=test", "-c", "user.email=test@example.invalid", "-c", "commit.gpgsign=false"]
NASTEPNIK = "- [ ] Opisz wnioski z analizy | kto: ty | po: Zadanie A\n- [x] Zamknięte po A | po: Zadanie A\n"


def day(n):
    return (datetime.date.today() + datetime.timedelta(days=n)).isoformat()


class Repo(Baza):
    """Projekt testowy jako repozytorium git z jednym commitem; zadanie z po: na „Zadanie A”."""

    def setUp(self):
        super().setUp()
        path = os.path.join(self.folder, "ZADANIA.md")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        with open(path, "w", encoding="utf-8") as f:
            f.write(text.replace("\n## Do rozplanowania", NASTEPNIK + "\n## Do rozplanowania"))
        self.git("init", "-q")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "start")
        self.main = self.git("symbolic-ref", "--short", "HEAD")
        self.head = self.git("rev-parse", "HEAD")

    def git(self, *args, cwd=None):
        p = subprocess.run(["git"] + IDENT + list(args), cwd=cwd or self.folder, check=True, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, encoding="utf-8")
        return p.stdout.strip()

    def run_done(self, title, mode="plik", manager=None):
        self.set_mode(mode)
        code, err, extra = self.run_task(title, manager)
        self.assertEqual(code, 200, err)
        rec = self.wait(extra["id"], manager=manager)
        self.assertEqual(rec["state"], "done", rec)
        return rec


@unittest.skipUnless(GIT, "brak polecenia git")
class Galaz(Repo):
    def test_galaz_katalog_roboczy_i_changes(self):
        rec = self.run_done("Zadanie A")
        self.assertEqual(rec["branch"], "agent/%s-zadanie-a" % TODAY)
        self.assertEqual((rec["base"], rec["baseCommit"], rec["commits"]), (self.main, self.head, 1))
        self.assertEqual(rec["changes"], [{"path": "notatki/analiza.md", "added": 3, "removed": 0}])
        call = self.calls()[-1]
        wt = os.path.join(self.folder, ".agent", rec["id"])
        self.assertEqual(os.path.realpath(call["cwd"]), wt)                      # agent pracował w katalogu roboczym
        self.assertFalse(os.path.exists(wt))                                     # panel go usunął
        self.assertEqual(call["argv"][call["argv"].index("--add-dir") + 1], self.folder)
        self.assertIn("na gałęzi `%s`" % rec["branch"], call["prompt"])
        self.assertIn("z pliku %s, wiersz" % os.path.join(self.folder, "ZADANIA.md"), call["prompt"])
        self.assertNotIn("git switch -c", call["prompt"])
        self.assertTrue(self.row("Zadanie A").startswith("- [x] Zadanie A"))   # wiersz w prawdziwym ZADANIA.md
        self.assertFalse(os.path.exists(os.path.join(self.folder, "notatki")))  # praca tylko na gałęzi
        self.assertEqual(self.git("log", "-1", "--format=%s", rec["branch"]), "Zadanie A")
        self.assertEqual(self.git("rev-parse", "HEAD"), self.head)
        self.assertEqual(self.git("status", "--porcelain"), "M ZADANIA.md")      # .agent/ wykluczony lokalnie
        self.assertEqual(self.git("worktree", "list", "--porcelain").count("worktree "), 1)
        self.assertEqual(self.manager.get(rec["id"])["branch"], rec["branch"])
        # druga gałąź tego samego dnia i tytułu dostaje przyrostek
        self.assertEqual(self.manager._branch_name(self.folder, "Zadanie A"), rec["branch"] + "-2")

    def test_material_dla_nastepnikow(self):
        rec = self.run_done("Zadanie A")
        detail = self.task("Opisz wnioski z analizy")["detail"]
        self.assertEqual(detail["refs"], [{"path": "notatki/analiza.md", "anchor": ""}])     # brak/plik.md nie istnieje
        self.assertEqual(self.task("Zamknięte po A")["detail"]["refs"], [])                 # zrobione: bez zmian
        # drugi przebieg nie dubluje materiału
        self.manager._pass_materials(rec, {"top": self.folder, "rel": ".", "worktree": "", "branch": rec["branch"]})
        self.assertEqual(self.task("Opisz wnioski z analizy")["detail"]["refs"],
                         [{"path": "notatki/analiza.md", "anchor": ""}])

    def test_agent_sam_zatwierdza(self):
        rec = self.run_done("Zadanie A", mode="commit")
        self.assertEqual(rec["commits"], 1)
        self.assertEqual(self.git("log", "-1", "--format=%s", rec["branch"]), "Analiza")
        self.assertEqual(rec["changes"], [{"path": "notatki/analiza.md", "added": 3, "removed": 0}])

    def test_bez_zmian_i_wylaczone(self):
        rec = self.run_done("Zadanie A", mode="ok")
        self.assertEqual((rec["changes"], rec["commits"]), ([], 0))
        m = self.new_manager(PANEL_AGENT_WORKTREE="0")
        rec = self.run_done("Zadanie B", mode="ok", manager=m)
        self.assertNotIn("branch", rec)
        self.assertEqual(os.path.realpath(self.calls()[-1]["cwd"]), self.folder)

    def test_diff_i_merge(self):
        rec = self.run_done("Zadanie A")
        code, text = self.manager.diff(rec["id"])
        self.assertEqual(code, 200)
        self.assertIn("+++ b/notatki/analiza.md", text)
        self.assertIn("+Treść.", text)
        self.assertEqual(self.manager.diff("nie-ma")[0], 404)
        # niezatwierdzona zmiana poza plikami standardu blokuje
        with open(os.path.join(self.folder, "CLAUDE.md"), "a", encoding="utf-8") as f:
            f.write("\nzmiana\n")
        code, err, _ = self.manager.merge(rec["id"])
        self.assertEqual(code, 409)
        self.assertIn("Niezatwierdzone zmiany w repozytorium: CLAUDE.md", err)
        self.git("checkout", "--", "CLAUDE.md")
        # inna gałąź wybrana w repozytorium
        self.git("switch", "-q", "-c", "inna")
        self.assertIn("wybrana jest gałąź inna", self.manager.merge(rec["id"])[1])
        self.git("switch", "-q", self.main)
        # ZADANIA.md zmienione przez panel nie przeszkadza
        code, err, extra = self.manager.merge(rec["id"])
        self.assertEqual((code, err), (200, ""))
        self.assertEqual(self.git("rev-parse", "HEAD"), extra["commit"])
        self.assertEqual(len(self.git("log", "-1", "--format=%P").split()), 2)       # --no-ff: commit scalenia
        self.assertTrue(os.path.isfile(os.path.join(self.folder, "notatki", "analiza.md")))
        self.assertTrue(self.manager.get(rec["id"])["merged"])
        self.assertEqual(self.manager.merge(rec["id"])[0], 409)                      # drugi raz nie

    def test_konflikt(self):
        rec = self.run_done("Zadanie A")
        os.makedirs(os.path.join(self.folder, "notatki"))
        with open(os.path.join(self.folder, "notatki", "analiza.md"), "w", encoding="utf-8") as f:
            f.write("# Inna treść\n")
        self.git("add", "notatki")
        self.git("commit", "-q", "-m", "inna analiza")
        before = self.git("rev-parse", "HEAD")
        code, err, _ = self.manager.merge(rec["id"])
        self.assertEqual(code, 409)
        self.assertIn("Konflikt w: notatki/analiza.md", err)
        self.assertEqual(self.git("rev-parse", "HEAD"), before)
        self.assertEqual(subprocess.run(["git", "rev-parse", "-q", "--verify", "MERGE_HEAD"], cwd=self.folder,
                                        stdout=subprocess.DEVNULL).returncode, 1)
        self.assertFalse(self.manager.get(rec["id"]).get("merged"))

    def test_zatrzymanie_i_restart(self):
        self.set_mode("wolno")
        rid = self.run_task("Zadanie A")[2]["id"]
        wt = os.path.join(self.folder, ".agent", rid)
        self.wait_for(lambda: os.path.isdir(wt) and os.path.exists(self.pid_file))
        self.assertEqual(self.manager.merge(rid)[0], 409)                          # w toku
        self.manager.stop(rid)
        rec = self.wait(rid)
        self.assertEqual(rec["state"], "stopped")
        self.assertFalse(os.path.exists(wt))
        # uruchomienie przerwane restartem: katalog roboczy zostaje sprzątnięty przy starcie serwera
        rid = "20261119-000000-ab12"
        branch = "agent/%s-restart" % TODAY
        wt = os.path.join(self.folder, ".agent", rid)
        self.git("worktree", "add", "-q", "-b", branch, wt, self.head)
        with open(os.path.join(wt, "nowy.md"), "w", encoding="utf-8") as f:
            f.write("a\nb\n")
        task = self.task("Zadanie B")
        rec = dict(self.manager._new("task", "claude", "Zadanie B", project=task["project"], task_id=task["id"],
                                     file="ZADANIA.md"), id=rid, state="running", branch=branch, base=self.main,
                   baseCommit=self.head, changes=[], commits=0)
        with open(os.path.join(self.runs, rid + ".json"), "w", encoding="utf-8") as f:
            json.dump(rec, f)
        m = self.new_manager()
        m.start()
        rec = m.get(rid)
        self.assertEqual((rec["state"], rec["changes"], rec["commits"]),
                         ("stopped", [{"path": "nowy.md", "added": 2, "removed": 0}], 1))
        self.assertFalse(os.path.exists(wt))

    def test_folder_w_podfolderze_repozytorium(self):
        # repozytorium obejmuje folder nadrzędny; projekt to podfolder
        shutil.rmtree(os.path.join(self.folder, ".git"))
        parent = os.path.dirname(self.folder)
        self.git("init", "-q", cwd=parent)
        self.git("add", os.path.basename(self.folder), cwd=parent)
        self.git("commit", "-q", "-m", "start", cwd=parent)
        rec = self.run_done("Zadanie A")
        self.assertEqual(os.path.realpath(self.calls()[-1]["cwd"]),
                         os.path.join(parent, ".agent", rec["id"], os.path.basename(self.folder)))
        self.assertEqual(rec["changes"], [{"path": "projekt-testowy/notatki/analiza.md", "added": 3, "removed": 0}])
        self.assertEqual(self.task("Opisz wnioski z analizy")["detail"]["refs"],
                         [{"path": "notatki/analiza.md", "anchor": ""}])


class SciezkiWyniku(Baza):
    def test_sciezki_z_wyniku(self):
        os.makedirs(os.path.join(self.folder, "wyniki"))
        for name in ("wyniki/a.md", "b.txt"):
            with open(os.path.join(self.folder, name), "w", encoding="utf-8") as f:
                f.write("x")
        text = "Powstały wyniki/a.md, `b.txt` i %s; nie ma c.md ani ../x.md, plik wyniki/a.md." % \
            os.path.join(self.folder, "b.txt")
        self.assertEqual(self.manager.result_paths(text, self.folder), ["wyniki/a.md", "b.txt"])
        self.assertEqual(self.manager.result_paths("", self.folder), [])


class UzytkownikAgenta(Baza):
    def test_sudo(self):
        m = self.new_manager(PANEL_AGENT_USER="agent", PANEL_AGENT_WORKTREE="0")
        m.refresh_tools = lambda *a, **k: None              # bez prawdziwego sudo w testach
        seen = []
        original = agents.subprocess.Popen

        def fake(args, *a, **kw):
            seen.append(list(args))
            raise OSError(1, "atrapa")
        agents.subprocess.Popen = fake
        try:
            rec = self.wait(self.run_task("Zadanie A", m)[2]["id"], manager=m)
        finally:
            agents.subprocess.Popen = original
        self.assertEqual(rec["state"], "error")
        self.assertEqual(seen[-1][:5], ["sudo", "-n", "-u", "agent", "--"])
        self.assertIn("--allowedTools", seen[-1])
        self.assertEqual(self.manager.as_agent(["claude"]), ["claude"])            # bez zmiennej jak dotąd
        self.assertTrue(self.row("Zadanie A").startswith("- [ ] Zadanie A"))


KAMPANIA = """# Kampania: Stały rytm

- stan: w toku
- kanały: facebook

## Harmonogram

- [ ] Post jutro | kanał: facebook | kiedy: %(t1)s
- [ ] Post z materiałem | kanał: facebook | kiedy: %(t2)s
  materiał: posty/szkic.md
- [x] Post stary | kanał: linkedin | kiedy: %(m3)s
- [x] Post z liczbami | kanał: facebook | kiedy: %(m3)s
  wyświetlenia: 120
  kliknięcia: 4
""" % {"t1": day(1), "t2": day(2), "m3": day(-3)}


class AutomatSzczegoly(Baza):
    def setUp(self):
        super().setUp()
        for rel, text in (("kampanie/staly-rytm.md", KAMPANIA), ("STYL.md", "# Styl\n"),
                          ("marketing/plan-10-kont.md", "# Plan\n")):
            os.makedirs(os.path.dirname(os.path.join(self.folder, rel)) or self.folder, exist_ok=True)
            with open(os.path.join(self.folder, rel), "w", encoding="utf-8") as f:
                f.write(text)
        self.m = self.new_manager(PANEL_MACHINE="chmura")

    def test_pelne_szczegoly_i_bez_dublowania(self):
        data, index = self.m.load_projects()
        self.assertTrue(self.m._plan_rhythm(data, index, datetime.date.today()))
        tasks = {t["title"]: t for t in self.m.load_projects()[0]["tasks"]
                 if t["title"].startswith((agents.POST_TASK, agents.RESULT_TASK))}
        self.assertEqual(sorted(tasks), ["Przygotować post na %s: Post jutro" % day(1),
                                         "Wpisz wynik publikacji Post stary"])
        post = tasks["Przygotować post na %s: Post jutro" % day(1)]
        d = post["detail"]
        self.assertIn("post na %s (facebook): Post jutro" % day(1), d["goal"])
        self.assertIn("posty/%s-" % day(1), d["doneWhen"])
        self.assertEqual([r["path"] for r in d["refs"]], ["kampanie/staly-rytm.md", "STYL.md", "marketing/plan-10-kont.md"])
        self.assertEqual((post["executor"], post["minutes"]), ("claude", agents.POST_REVIEW_MINUTES))
        res = tasks["Wpisz wynik publikacji Post stary"]
        self.assertIn("(linkedin)", res["detail"]["goal"])
        self.assertIn("wyświetlenia:", res["detail"]["doneWhen"])
        self.assertEqual([r["path"] for r in res["detail"]["refs"]], ["kampanie/staly-rytm.md", "marketing/plan-10-kont.md"])
        self.assertEqual((res["executor"], res["minutes"]), ("ty", 3))

    def test_post_do_filmu_po_nagraniu(self):
        path = os.path.join(self.folder, "kampanie", "staly-rytm.md")
        film = ("- [ ] Nagraj film A | kto: ty | kiedy: %s\n"
                "- [ ] Opublikuj film A | kanał: facebook | kiedy: %s | po: Nagraj film A\n") % (day(0), day(1))
        with open(path, "w", encoding="utf-8") as f:
            f.write(KAMPANIA.split("- [ ] Post jutro")[0] + film)
        prep = lambda: [t["title"] for t in self.m.load_projects()[0]["tasks"] if t["title"].startswith(agents.POST_TASK)]
        data, index = self.m.load_projects()
        self.m._plan_rhythm(data, index, datetime.date.today())
        self.assertEqual(prep(), [])                                              # filmu nie ma: bez opisu pod film
        with open(path, "w", encoding="utf-8") as f:
            f.write(KAMPANIA.split("- [ ] Post jutro")[0] + film.replace("- [ ] Nagraj", "- [x] Nagraj"))
        data, index = self.m.load_projects()
        self.assertTrue(self.m._plan_rhythm(data, index, datetime.date.today()))
        self.assertEqual(prep(), ["Przygotować post na %s: Opublikuj film A" % day(1)])

    def test_wynik_publikacji(self):
        self.assertTrue(agents.has_result({"result": "120 wyświetleń"}))
        self.assertTrue(agents.has_result({"notes": ["wyświetlenia: 120"]}))
        self.assertTrue(agents.has_result({"views": 120}))
        self.assertFalse(agents.has_result({"notes": ["link: https://example.invalid"], "result": ""}))

    def test_stary_rytm_ma_szczegoly(self):
        with open(os.path.join(self.folder, "kampanie", "staly-rytm.md"), "w", encoding="utf-8") as f:
            f.write(KAMPANIA.split("- [ ] Post jutro")[0])                       # bez przyszłych publikacji
        m = self.new_manager(PANEL_RYTM="%s=2" % os.path.basename(self.folder), PANEL_MACHINE="chmura")
        data, index = m.load_projects()
        self.assertTrue(m._plan_posts(data, index, datetime.date.today()))
        [t] = [t for t in m.load_projects()[0]["tasks"] if t["title"].endswith(agents.RYTM_SUFFIX)]
        self.assertTrue(t["detail"]["goal"] and t["detail"]["doneWhen"])
        self.assertEqual(t["detail"]["refs"][0]["path"], "kampanie/staly-rytm.md")


class KluczLokalny(Serwer):
    KEY = "k" * 40

    def setUp(self):
        super().setUp()
        self.key_file = os.path.join(self.tmp, "klucz")
        with open(self.key_file, "w", encoding="utf-8") as f:
            f.write(self.KEY + "\n")
        os.chmod(self.key_file, 0o600)

    def automat(self, **kw):
        return self.post("/api/agent/automat", {"enabled": False}, **kw)[0]

    def test_post_wymaga_klucza_albo_sesji(self):
        self.assertEqual(self.automat(), 200)                                     # Mac bez ustawień: jak dotąd
        server.LOCAL_KEY_FILE = self.key_file
        self.assertEqual(self.automat(), 401)
        self.assertEqual(self.automat(headers={"X-Panel-Klucz": "zly"}), 401)
        self.assertEqual(self.automat(headers={"X-Panel-Klucz": self.KEY}), 200)
        for path in ("/api/data", "/", "/api/plik?project=projekt-testowy&path=KARTA.md"):
            self.assertEqual(self.request("GET", path)[0], 200, path)              # odczyty bez zmian (zdrowie.sh)
        self.assertEqual(self.request("GET", "/api/post?project=projekt-testowy&date=2026-11-20")[0], 404)
        server.TOKEN = "haslo-do-testow"                                         # klucz działa tylko z loopback
        self.assertEqual(self.automat(headers=dict(REMOTE, **{"X-Panel-Klucz": self.KEY})), 401)
        os.chmod(self.key_file, 0o640)                                           # grupa panelu (root:panel 640)
        self.assertEqual(self.automat(headers={"X-Panel-Klucz": self.KEY}), 200)
        os.chmod(self.key_file, 0o644)                                           # czytelny dla innych: odrzucony
        self.assertEqual(self.automat(headers={"X-Panel-Klucz": self.KEY}), 401)
        os.chmod(self.key_file, 0o640)                                           # grupa, w której jest agent: odrzucony
        st = os.stat(self.key_file)
        self.assertTrue(server.key_file_exposed(st, getpass.getuser()))
        self.assertFalse(server.key_file_exposed(st, ""))
        os.chmod(self.key_file, 0o600)
        self.assertFalse(server.key_file_exposed(os.stat(self.key_file), getpass.getuser()))

    def test_serwer_bez_pliku_klucza(self):
        server._agents = self.new_manager(PANEL_MACHINE="cloud")
        self.assertEqual(self.automat(), 401)
        self.assertEqual(self.request("GET", "/api/data")[0], 200)
        server.TOKEN = "haslo-do-testow"
        status, _, page = self.request("GET", "/wejscie")                        # logowanie także z loopback
        self.assertEqual(status, 200)
        self.assertIn('name="haslo"', page)
        from urllib.parse import urlencode
        status, headers, _ = self.request("POST", "/wejscie", raw=urlencode({"haslo": "haslo-do-testow"}).encode(),
                                          ctype="application/x-www-form-urlencoded")
        self.assertEqual(status, 303)
        cookie = headers["Set-Cookie"].split(";")[0]
        self.assertEqual(self.automat(headers={"Cookie": cookie}), 200)
        self.assertEqual(self.request("GET", "/wejscie", headers={"Cookie": cookie})[0], 303)

    def test_uzytkownik_agenta_wlacza_ochrone(self):
        os.environ["PANEL_AGENT_USER"] = "agent"
        self.assertEqual(self.automat(), 401)


@unittest.skipUnless(GIT, "brak polecenia git")
class GalazSerwer(Serwer, Repo):
    def test_merge_i_diff_przez_api(self):
        rec = self.run_done("Zadanie A")
        status, headers, text = self.request("GET", "/api/agent/diff?id=" + rec["id"])
        self.assertEqual((status, headers["Content-Type"]), (200, "text/plain; charset=utf-8"))
        self.assertIn("notatki/analiza.md", text)
        status, _, text = self.request("GET", "/api/agent/diff?id=nie-ma")
        self.assertEqual((status, json.loads(text)["ok"]), (404, False))
        self.assertEqual(self.post("/api/agent/merge", {"id": rec["id"]}),
                         (200, {"ok": True, "error": "", "commit": self.git("rev-parse", "HEAD")}))
        status, answer = self.post("/api/agent/merge", {"id": rec["id"]})
        self.assertEqual((status, answer["ok"]), (409, False))
        run = next(r for r in self.data()["agents"]["runs"] if r["id"] == rec["id"])
        self.assertEqual((run["branch"], run["changes"][0]["path"]), (rec["branch"], "notatki/analiza.md"))
        self.assertTrue(run["merged"])


class NowePolaDanych(Serwer):
    def test_przepuszczone_pola_i_dzien(self):
        original = server.projekt.read_project

        def read(folder, pid=None, decision=None):
            d = original(folder, pid, decision)
            d["project"]["priority"] = 1
            for q in d["project"].get("questions") or []:
                q["proposal"] = "tak"
            return d
        server.projekt.read_project = read
        try:
            data = self.data()
        finally:
            server.projekt.read_project = original
        self.assertEqual(data["projects"][0]["priority"], 1)
        self.assertEqual(data["dayMinutes"], 120)
        os.environ["PANEL_DZIEN_MIN"] = "90"
        self.assertEqual(self.data()["dayMinutes"], 90)
        os.environ["PANEL_DZIEN_MIN"] = "zle"
        self.assertEqual(self.data()["dayMinutes"], 120)
        self.assertEqual(server.preview_data()["dayMinutes"], 120)

    def test_klucze_publikacji(self):
        seen = []
        original = server.projekt.set_detail
        server.projekt.set_detail = lambda root, f, line, title, key, value: seen.append((key, value)) or True
        try:
            t = self.task("Zadanie B")
            for key in ("wyświetlenia", "wyswietlenia", "kliknięcia", "konta", "link"):
                status, answer = self.post("/api/task/detail", {"id": t["id"], "title": t["title"], "key": key,
                                                                "value": "12"})
                self.assertEqual((status, answer["ok"]), (200, True), key)
        finally:
            server.projekt.set_detail = original
        self.assertEqual([k for k, _ in seen], ["wyświetlenia", "wyświetlenia", "kliknięcia", "konta", "link"])


if __name__ == "__main__":
    unittest.main()
