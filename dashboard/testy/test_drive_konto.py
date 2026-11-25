"""Google Drive na całe konto (dashboard/drive.py): łączenie konta, lista folderów, folder dla projektu i części,
stare połączenie projektu, własny klient OAuth, brak wycieku wyjścia rclone i tokenów, ścieżka Drive w instrukcji
agenta. Na atrapie rclone (atrapa_rclone.py)."""
import http.server
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.parse
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import drive  # noqa: E402
from test_drive import ATRAPA, free_port  # noqa: E402
from wspolne import Baza, agents, projekt  # noqa: E402

SECRET = "TAJNY-TOKEN"


class Konto(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.cards = {}
        for pid in ("proj", "proj-www"):
            self.cards[pid] = os.path.join(self.tmp, "szkice", pid)
            os.makedirs(self.cards[pid])
        self.rclone = os.path.join(self.tmp, "rclone")
        shutil.copy(ATRAPA, self.rclone)
        os.chmod(self.rclone, os.stat(self.rclone).st_mode | stat.S_IEXEC)
        self.port = free_port()
        os.environ["ATRAPA_RCLONE_PORT"] = str(self.port)
        os.environ.pop("ATRAPA_RCLONE_BLAD", None)
        self.log = os.path.join(self.tmp, "pomocnik")
        helper = [sys.executable, "-c", "import sys; open(%r, 'a').write(' '.join(sys.argv[1:]) + '\\n')" % self.log]
        self.conf = os.path.join(self.tmp, "cfg", "rclone.conf")
        self.oauth = os.path.join(self.tmp, "google-oauth.json")
        self.d = drive.Drive(self.cards.get, rclone=self.rclone, helper=helper, conf=self.conf,
                             data_dir=os.path.join(self.tmp, "dane"), port=self.port, oauth_file=self.oauth,
                             parts=lambda pid: ["proj-www"] if pid == "proj" else [])

    def tearDown(self):
        self.d.cancel_account("proj")
        self.d.cancel("proj")
        os.environ.pop("ATRAPA_RCLONE_PORT", None)
        os.environ.pop("ATRAPA_RCLONE_BLAD", None)
        shutil.rmtree(self.tmp)

    def finish(self, url):
        return self.d.finish_account(url, project="proj")

    def calls(self):
        try:
            with open(self.log) as f:
                return f.read().splitlines()
        except OSError:
            return []

    def aliases(self):
        with open(self.conf + ".alias") as f:
            return f.read().splitlines()

    def connect(self, label="Firma"):
        code, err, extra = self.d.start_account(label, project="proj")
        self.assertEqual((code, err, extra["mode"]), (200, "", "paste"))
        self.assertTrue(extra["loginUrl"].startswith("https://accounts.google.com/"))
        code, err, extra = self.finish("http://127.0.0.1:%d/?state=St4te-xyz&code=4/0Ab&scope=x" % self.port)
        self.assertEqual((code, err), (200, ""), err)
        self.assertNotIn(SECRET, repr(extra))
        return extra["account"]

    def test_polaczenie_konta(self):
        self.assertEqual(self.d.accounts()[2]["accounts"], [])
        code, _, extra = self.d.start_account("Firma Łódź", project="proj")
        st = self.d.accounts("proj")[2]
        self.assertEqual(st["login"]["mode"], "paste")
        self.assertEqual(st["login"]["account"], "firma-lodz")
        self.assertEqual(st["accounts"], [])                                # przed zalogowaniem konta nie ma
        self.assertEqual(self.finish("http://127.0.0.1:%d/?state=zly&code=1" % self.port)[0], 400)
        self.assertEqual(self.finish("https://zly.example/?state=St4te-xyz")[0], 400)
        code, err, _ = self.finish("http://127.0.0.1:%d/?state=St4te-xyz&code=4/0Ab" % self.port)
        self.assertEqual((code, err), (200, ""))
        st = self.d.accounts()[2]
        self.assertIsNone(st["login"])
        self.assertEqual([(a["id"], a["label"], a["connected"], a["projects"]) for a in st["accounts"]],
                         [("firma-lodz", "Firma Łódź", True, ["proj", "proj-www"])])
        self.assertNotIn(SECRET, json.dumps(st))
        self.assertEqual(self.d.start_account("firma łódź", project="proj")[0], 409)        # ta sama nazwa
        self.assertEqual(self.connect("Prywatne"), "prywatne")                # drugie konto
        self.assertEqual(len(self.d.accounts()[2]["accounts"]), 2)

    def test_kod_i_tekst_po_ponownej_probie(self):
        for label, value in (("Firma", "4/0Ab"), ("Prywatne", "Google: code=4%2F0Ab&state=St4te-xyz gotowe")):
            first = self.d.start_account(label, project="proj")
            self.assertEqual(self.d.start_account(label, project="proj"), first)  # drugie okno nie wymienia state
            for wrong, hint in (("state=obcy&code=4/0Ab", "z innego logowania"),
                                ("code=&state=St4te-xyz", "Brakuje kodu")):
                code, error, _ = self.finish(wrong)
                self.assertEqual(code, 400)
                self.assertIn(hint, error)
            proc = self.d.login["proc"]
            with mock.patch.object(proc, "wait", side_effect=subprocess.TimeoutExpired("rclone", 2)):
                self.assertEqual(self.finish(value), (202, "", {"pending": True}))
            self.assertIsNotNone(self.d.accounts("proj")[2]["login"])
            self.assertEqual(self.finish(value)[:2], (200, ""))

    def test_anulowanie_konta(self):
        self.assertEqual(self.d.start_account("Firma", project="proj")[0], 200)
        self.d.cancel_account("proj")
        self.assertNotIn("gdrive-firma", self.d._remotes())                   # niedokończony wpis usunięty
        self.assertEqual(self.finish("http://127.0.0.1:%d/?state=St4te-xyz&code=1" % self.port)[0], 409)

    def test_lista_folderow(self):
        acc = self.connect()
        code, err, extra = self.d.folders(acc, project="proj")
        self.assertEqual((code, err), (200, ""))
        self.assertEqual([f["path"] for f in extra["folders"]],
                         ["Marketing", "Marketing/Cupra", "Marketing/Cupra/Zdjęcia", "Prywatne"])
        self.assertEqual(extra["folders"][1]["id"], "1CupraFolderId")
        self.assertEqual(self.d.folders("obce")[0], 404)

    def test_bledy_bez_wycieku(self):
        acc = self.connect()
        for blad, zdanie in (("oauth2: cannot fetch token: 400 invalid_grant", "Połącz konto ponownie"),
                             ("dial tcp: lookup www.googleapis.com: no such host", "Brak połączenia z Google"),
                             ("cos zupelnie innego", "Nie udało się odczytać")):
            os.environ["ATRAPA_RCLONE_BLAD"] = blad
            code, err, extra = self.d.folders(acc, refresh=True, project="proj")
            self.assertEqual(code, 502)
            self.assertIn(zdanie, err)
            self.assertNotIn(SECRET, err + json.dumps(extra))
            self.assertNotIn("lsjson", err)

    def test_folder_dla_projektu_i_czesci(self):
        acc = self.connect()
        self.d.folders(acc, project="proj")
        self.assertEqual(self.d.choose("proj", acc, "zly")[0], 400)
        self.assertEqual(self.d.choose("obcy", acc, "1CupraFolderId")[0], 404)
        self.assertEqual(self.d.choose("proj", "obce", "1CupraFolderId")[0], 404)
        self.assertEqual(self.d.choose("proj", acc, "1CupraFolderId")[:2], (200, ""))
        self.assertEqual(self.d.choose("proj-www", acc,
                                       "https://drive.google.com/drive/folders/1PrywatneId000?usp=sharing")[:2],
                         (200, ""))
        self.assertEqual(self.aliases(), ["drive-proj remote=gdrive-firma,root_folder_id=1CupraFolderId:",
                                          "drive-proj-www remote=gdrive-firma,root_folder_id=1PrywatneId000:"])
        self.assertEqual(self.calls(), ["proj " + self.cards["proj"], "proj-www " + self.cards["proj-www"]])
        st = self.d.status("proj")[2]
        self.assertEqual((st["connected"], st["legacy"], st["path"], st["accountLabel"], st["folder"]),
                         (True, False, "Marketing/Cupra", "Firma", "1CupraFolderId"))
        self.assertEqual(self.d.status("proj-www")[2]["path"], "Prywatne")   # ścieżka z listy także dla linku
        self.assertEqual(self.d.accounts()[2]["accounts"][0]["projects"], ["proj", "proj-www"])
        self.assertEqual(self.d.remove_account(acc)[0], 409)                  # konto w użyciu
        self.assertEqual(self.d.disconnect("proj")[:2], (200, ""))
        self.assertEqual(self.d.disconnect("proj-www")[:2], (200, ""))
        self.assertEqual(self.calls()[-2:], ["--wylacz proj", "--wylacz proj-www"])
        self.assertNotIn("drive-proj", self.d._remotes())
        self.assertIn("gdrive-firma", self.d._remotes())                      # konto zostaje
        self.assertEqual(self.d.unassign_account("proj", acc)[:2], (200, ""))
        self.assertEqual(self.d.unassign_account("proj-www", acc)[:2], (200, ""))
        self.assertEqual(self.d.remove_account(acc)[:2], (200, ""))
        self.assertNotIn("gdrive-firma", self.d._remotes())
        self.assertEqual(self.d.accounts()[2]["accounts"], [])

    def test_diagnoza_aliasu_i_ponowne_montowanie(self):
        acc = self.connect()
        self.assertEqual(self.d.choose("proj", acc, "1CupraFolderId")[0], 200)
        with mock.patch.dict(os.environ, {"ATRAPA_RCLONE_ALIAS_BLAD": "1"}):
            status = self.d.status("proj")[2]
            self.assertEqual(status["repair"], "alias")
            self.assertIn("wpis Drive projektu", status["reason"])
            self.assertNotIn(SECRET, repr(status))
            self.assertEqual(self.d.mount("proj")[:2], (200, ""))
        self.assertEqual(self.aliases()[-2:], [self.aliases()[0]] * 2)
        self.assertEqual(self.calls(), ["proj " + self.cards["proj"]] * 2)
        with mock.patch.dict(os.environ, {"ATRAPA_RCLONE_BLAD": "invalid_grant"}):
            status = self.d.status("proj")[2]
            self.assertEqual(status["repair"], "reconnect")
            code, message, _ = self.d.mount("proj")
            self.assertEqual(code, 409)
            self.assertNotIn(SECRET, message)
        self.assertEqual(len(self.calls()), 2)

    def test_ponowne_polaczenie_konta(self):
        acc = self.connect()
        self.assertEqual(self.d.choose("proj", acc, "1CupraFolderId")[:2], (200, ""))
        os.environ["ATRAPA_RCLONE_BLAD"] = "oauth2: cannot fetch token: 400 Bad Request invalid_grant"
        self.assertIn("Połącz konto ponownie", self.d.folders(acc, refresh=True, project="proj")[1])
        os.environ.pop("ATRAPA_RCLONE_BLAD")
        self.assertEqual(self.d.start_account("", account="obce")[0], 404)
        code, _, extra = self.d.start_account("", account=acc, project="proj")
        self.assertEqual((code, extra["account"]), (200, acc))
        self.assertEqual(self.finish("http://127.0.0.1:%d/?state=St4te-xyz&code=1" % self.port)[:2],
                         (200, ""))
        self.assertEqual([a["id"] for a in self.d.accounts()[2]["accounts"]], [acc])     # to samo konto
        self.assertEqual(self.calls()[-1], "proj " + self.cards["proj"])                 # montowanie od nowa
        self.assertTrue(self.d.status("proj")[2]["connected"])

    def test_stare_polaczenie_dziala_i_przechodzi_na_konto(self):
        code, _, _ = self.d.start("proj", "1StaryFolder123")
        self.assertEqual(code, 200)
        self.assertEqual(self.d.finish("proj", "http://127.0.0.1:%d/?state=St4te-xyz&code=1" % self.port)[:2],
                         (200, ""))
        st = self.d.status("proj")[2]
        self.assertEqual((st["connected"], st["legacy"], st["folder"], st["account"]),
                         (True, True, "1StaryFolder123", ""))
        self.assertEqual(self.d.mount("proj")[:2], (200, ""))                 # stara usługa montuje dalej
        acc = self.connect()
        self.assertEqual(self.d.choose("proj", acc, "1MarketingId00")[:2], (200, ""))
        st = self.d.status("proj")[2]
        self.assertEqual((st["connected"], st["legacy"], st["path"]), (True, False, ""))
        self.assertEqual(self.aliases(), ["drive-proj remote=gdrive-firma,root_folder_id=1MarketingId00:"])
        self.d._accounts_write({acc: {"label": "Firma", "at": "2026-11-25T10:00:00"}})
        self.d.migrate_accounts()
        self.assertEqual(self.d.accounts()[2]["accounts"][0]["projects"], ["proj"])
        self.assertEqual(self.d.status("proj")[2]["folder"], "1MarketingId00")

    def test_wlasny_klient_oauth(self):
        got = {}

        class H(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                got.update(urllib.parse.parse_qs(self.rfile.read(int(self.headers["Content-Length"])).decode()))
                body = json.dumps({"access_token": SECRET, "refresh_token": SECRET + "-R", "expires_in": 3599,
                                   "token_type": "Bearer"}).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
        srv = http.server.HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        self.d.token_url = "http://127.0.0.1:%d/token" % srv.server_port
        self.assertFalse(self.d.accounts()[2]["ownClient"])
        red = "https://2-29-181-133.sslip.io/api/drive/powrot"
        self.assertEqual(self.d.save_client({"client_id": "123-abc.apps.googleusercontent.com",
                                             "client_secret": "SEKRET-KLIENTA"})[0], 200)
        st = self.d.accounts()[2]
        self.assertTrue(st["ownClient"])
        self.assertNotIn("SEKRET-KLIENTA", json.dumps(st))
        code, _, extra = self.d.start_account("Firma", project="proj", return_to="#projekt/test?tab=plan")
        self.assertEqual((code, extra["mode"]), (200, "own"))
        q = urllib.parse.parse_qs(urllib.parse.urlsplit(extra["loginUrl"]).query)
        self.assertEqual((q["redirect_uri"], q["scope"], q["access_type"]), ([red], [drive.SCOPE], ["offline"]))
        self.assertNotIn("SEKRET-KLIENTA", extra["loginUrl"])
        self.assertEqual(self.d.oauth_back("state=zly&code=1")[0], 409)
        code, text = self.d.oauth_back("state=%s&code=4/0Ab" % q["state"][0], redirect=True)
        self.assertEqual((code, text), (303, "/#projekt/test?tab=plan"))
        self.assertNotIn(SECRET, text)
        self.assertEqual((got["code"], got["redirect_uri"], got["grant_type"]), (["4/0Ab"], [red], ["authorization_code"]))
        self.assertEqual(oct(os.stat(self.conf).st_mode & 0o777), "0o600")
        with open(self.conf) as f:
            conf = f.read()
        self.assertIn("[gdrive-firma]", conf)
        self.assertIn('"refresh_token": "%s-R"' % SECRET, conf)
        self.assertIn("scope = drive.readonly", conf)
        acc = self.d.accounts()[2]["accounts"]
        self.assertEqual([(a["id"], a["connected"]) for a in acc], [("firma", True)])
        self.assertEqual(self.d.oauth_back("state=%s&code=4/0Ab" % q["state"][0])[0], 409)   # state jednorazowy

    def test_zly_plik_klienta(self):
        for bad in ({"client_id": "x", "client_secret": "s", "redirect_uri": "https://a/api/drive/powrot"},
                    {"client_id": "1.apps.googleusercontent.com", "client_secret": "",
                     "redirect_uri": "https://a/api/drive/powrot"},
                    {"client_id": "1.apps.googleusercontent.com", "client_secret": "s",
                     "redirect_uri": "http://a/api/drive/powrot"}):
            with open(self.oauth, "w") as f:
                json.dump(bad, f)
            self.assertIsNone(self.d.own_client())


    def test_przypisanie_i_odlaczenie_od_innego_projektu(self):
        self.cards["inny"] = os.path.join(self.tmp, "inny")
        acc = self.connect()
        self.assertEqual(self.d.accounts("inny")[2]["accounts"], [])
        self.assertEqual(self.d.folders(acc, project="inny")[0], 404)
        self.assertEqual(self.d.choose("inny", acc, "1CupraFolderId")[0], 404)
        self.assertEqual(self.d.assign_account("inny", acc)[0], 400)
        self.assertEqual(self.d.assign_account("inny", acc, True)[0], 200)
        self.assertEqual(self.d.accounts("inny")[2]["accounts"][0]["id"], acc)
        self.assertEqual(self.d.folders(acc, project="inny")[0], 200)
        self.assertEqual(self.d.choose("inny", acc, "1CupraFolderId")[0], 200)
        self.assertEqual(self.d.unassign_account("inny", acc)[0], 200)
        self.assertEqual(self.calls()[-1], "--wylacz inny")
        self.assertEqual(self.d.status("inny")[2]["folder"], "")
        self.assertEqual(self.d.accounts("inny")[2]["accounts"], [])
        self.assertEqual(self.d.folders(acc, project="inny")[0], 404)
        self.assertEqual(self.d.accounts("proj")[2]["accounts"][0]["id"], acc)

    def test_migracja_zachowuje_folder_shield_i_ponawia_nieudane_odlaczenie(self):
        pids = ("shield-silent", "detailing-kepno", "company-audits", "oprogramowani-onepager")
        self.cards.update({pid: os.path.join(self.tmp, pid) for pid in pids})
        acc = self.connect()
        self.d._accounts_write({acc: {"label": "Shield & Silent", "at": "2026-11-25T10:00:00"}})
        selected = {"account": acc, "folder": "1CupraFolderId", "path": "Marketing/Cupra"}
        for pid in (pids[0], *pids[2:]):
            self.d._side_write(pid, selected)
            self.assertTrue(self.d._write_alias(pid, self.d._alias_target(acc, selected["folder"])))
        helper = self.d._helper
        with mock.patch.object(self.d, "_helper", side_effect=lambda *args:
                               (False, "awaria") if args == ("--wylacz", pids[2]) else helper(*args)):
            self.d.migrate_accounts()
        report = self.d.accounts()[2]["accounts"][0]["migration"]
        self.assertEqual(report["before"], sorted((pids[0], *pids[2:])))
        self.assertEqual(report["after"], sorted(pids[:2]))
        self.assertEqual(report["pending"], [pids[2]])
        with mock.patch("os.path.ismount", return_value=True):
            self.assertEqual(self.d.mount_path(pids[2]), "")
        self.assertEqual(self.d.status(pids[2])[2]["folder"], "")
        self.assertEqual(self.d.retry_migration()[0], 200)
        self.assertEqual(self.d._side_read(pids[0]), selected)
        for pid in pids[2:]:
            self.assertEqual(self.d._side_read(pid), {})
            self.assertNotIn("drive-" + pid, self.d._remotes())
        self.assertEqual(self.d.accounts()[2]["accounts"][0]["migration"]["pending"], [])
        self.assertEqual(self.d.unassign_account(pids[1], acc)[0], 200)
        self.d.migrate_accounts()
        self.assertEqual(self.d.accounts(pids[1])[2]["accounts"], [])


class InstrukcjaAgenta(Baza):
    def test_sciezka_drive_w_instrukcji(self):
        cards = os.path.dirname(os.path.realpath(os.path.join(self.folder, "KARTA.md")))
        mnt = os.path.join(cards, "media", "drive")
        self.assertEqual(agents.drive_dir(self.folder), "")                    # bez montowania nic
        real = os.path.ismount
        with mock.patch("os.path.ismount", lambda p: p == mnt or real(p)):
            self.assertEqual(agents.drive_dir(self.folder), mnt)
            t = {"tool": "claude", "path": "claude", "name": "P", "file": "ZADANIA.md", "line": 4, "title": "Tytuł",
                 "stage": "", "detail": projekt.blank_detail(), "site": ""}
            priv = {"task": t, "folder": self.folder}
            self.manager._task_command(priv)
        self.assertIn("Pliki projektu z Google Drive są w %s (tylko do odczytu" % mnt, priv["prompt"])
        i = priv["args"].index(mnt)
        self.assertEqual(priv["args"][i - 1], "--add-dir")
        p = self.manager.task_prompt("claude", "P", "ZADANIA.md", 4, "Tytuł", "", projekt.blank_detail())
        self.assertNotIn("Google Drive", p)

    def test_agent_nie_dostaje_odlaczonej_sciezki(self):
        from wspolne import server

        scope = drive.Drive(lambda pid: self.folder, data_dir=os.path.join(self.tmp, "drive"))
        scope._accounts_write({"firma": {"projects": ["shield-silent"]}})
        mnt = os.path.join(self.folder, "media", "drive")
        task = {"tool": "claude", "path": "claude", "name": "Audyt", "file": "ZADANIA.md",
                "line": 4, "title": "Tytuł", "stage": "", "detail": projekt.blank_detail(),
                "project": "company-audits"}
        priv = {"task": task, "folder": self.folder}
        with mock.patch.object(server, "_agents", None), mock.patch.object(server, "get_drive", return_value=scope):
            manager = server.get_agents()
            self.managers.append(manager)
            with mock.patch("os.path.ismount", return_value=True):
                manager._task_command(priv)
                self.assertNotIn(mnt, priv["args"])
                self.assertNotIn(mnt, priv["prompt"])
                scope._side_write("company-audits", {"account": "firma", "folder": "1MarketingId00"})
                manager._task_command(priv)
                self.assertNotIn(mnt, priv["args"])
                self.assertNotIn(mnt, priv["prompt"])
                task["project"] = "shield-silent"
                scope._side_write("shield-silent", {"account": "firma", "folder": "1MarketingId00"})
                manager._task_command(priv)
                self.assertIn(mnt, priv["args"])
                self.assertIn(mnt, priv["prompt"])


if __name__ == "__main__":
    unittest.main()
