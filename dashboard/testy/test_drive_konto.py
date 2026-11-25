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
                             data_dir=os.path.join(self.tmp, "dane"), port=self.port, oauth_file=self.oauth)

    def tearDown(self):
        self.d.cancel_account()
        self.d.cancel("proj")
        os.environ.pop("ATRAPA_RCLONE_PORT", None)
        os.environ.pop("ATRAPA_RCLONE_BLAD", None)
        shutil.rmtree(self.tmp)

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
        code, err, extra = self.d.start_account(label)
        self.assertEqual((code, err, extra["mode"]), (200, "", "paste"))
        self.assertTrue(extra["loginUrl"].startswith("https://accounts.google.com/"))
        code, err, extra = self.d.finish_account("http://127.0.0.1:%d/?state=St4te-xyz&code=4/0Ab&scope=x" % self.port)
        self.assertEqual((code, err), (200, ""), err)
        self.assertNotIn(SECRET, repr(extra))
        return extra["account"]

    def test_polaczenie_konta(self):
        self.assertEqual(self.d.accounts()[2]["accounts"], [])
        code, _, extra = self.d.start_account("Firma Łódź")
        st = self.d.accounts()[2]
        self.assertEqual(st["login"]["mode"], "paste")
        self.assertEqual(st["login"]["account"], "firma-lodz")
        self.assertEqual(st["accounts"], [])                                # przed zalogowaniem konta nie ma
        self.assertEqual(self.d.finish_account("http://127.0.0.1:%d/?state=zly&code=1" % self.port)[0], 400)
        self.assertEqual(self.d.finish_account("https://zly.example/?state=St4te-xyz")[0], 400)
        code, err, _ = self.d.finish_account("http://127.0.0.1:%d/?state=St4te-xyz&code=4/0Ab" % self.port)
        self.assertEqual((code, err), (200, ""))
        st = self.d.accounts()[2]
        self.assertIsNone(st["login"])
        self.assertEqual([(a["id"], a["label"], a["connected"], a["projects"]) for a in st["accounts"]],
                         [("firma-lodz", "Firma Łódź", True, [])])
        self.assertNotIn(SECRET, json.dumps(st))
        self.assertEqual(self.d.start_account("firma łódź")[0], 409)        # ta sama nazwa
        self.assertEqual(self.connect("Prywatne"), "prywatne")                # drugie konto
        self.assertEqual(len(self.d.accounts()[2]["accounts"]), 2)

    def test_kod_i_tekst_po_ponownej_probie(self):
        for label, value in (("Firma", "4/0Ab"), ("Prywatne", "Google: code=4%2F0Ab&state=St4te-xyz gotowe")):
            first = self.d.start_account(label)
            self.assertEqual(self.d.start_account(label), first)  # drugie okno nie wymienia state
            for wrong, hint in (("state=obcy&code=4/0Ab", "z innego logowania"),
                                ("code=&state=St4te-xyz", "Brakuje kodu")):
                code, error, _ = self.d.finish_account(wrong)
                self.assertEqual(code, 400)
                self.assertIn(hint, error)
            proc = self.d.login["proc"]
            with mock.patch.object(proc, "wait", side_effect=subprocess.TimeoutExpired("rclone", 2)):
                self.assertEqual(self.d.finish_account(value), (202, "", {"pending": True}))
            self.assertIsNotNone(self.d.accounts()[2]["login"])
            self.assertEqual(self.d.finish_account(value)[:2], (200, ""))

    def test_anulowanie_konta(self):
        self.assertEqual(self.d.start_account("Firma")[0], 200)
        self.d.cancel_account()
        self.assertNotIn("gdrive-firma", self.d._remotes())                   # niedokończony wpis usunięty
        self.assertEqual(self.d.finish_account("http://127.0.0.1:%d/?state=St4te-xyz&code=1" % self.port)[0], 409)

    def test_lista_folderow(self):
        acc = self.connect()
        code, err, extra = self.d.folders(acc)
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
            code, err, extra = self.d.folders(acc, refresh=True)
            self.assertEqual(code, 502)
            self.assertIn(zdanie, err)
            self.assertNotIn(SECRET, err + json.dumps(extra))
            self.assertNotIn("lsjson", err)

    def test_folder_dla_projektu_i_czesci(self):
        acc = self.connect()
        self.d.folders(acc)
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
        self.assertIn("Połącz konto ponownie", self.d.folders(acc, refresh=True)[1])
        os.environ.pop("ATRAPA_RCLONE_BLAD")
        self.assertEqual(self.d.start_account("", account="obce")[0], 404)
        code, _, extra = self.d.start_account("", account=acc)
        self.assertEqual((code, extra["account"]), (200, acc))
        self.assertEqual(self.d.finish_account("http://127.0.0.1:%d/?state=St4te-xyz&code=1" % self.port)[:2],
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
        code, _, extra = self.d.start_account("Firma", return_to="#projekt/test?tab=plan")
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


if __name__ == "__main__":
    unittest.main()
