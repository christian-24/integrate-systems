"""Google Drive projektu (dashboard/drive.py): link folderu, adres powrotu, logowanie i odłączenie na atrapie rclone."""
import os
import shutil
import socket
import stat
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import drive  # noqa: E402

ATRAPA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "atrapa_rclone.py")


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class Adresy(unittest.TestCase):
    def test_link_folderu(self):
        self.assertEqual(drive.folder_id("https://drive.google.com/drive/folders/1AbC_d-EfGh123?usp=sharing"), "1AbC_d-EfGh123")
        self.assertEqual(drive.folder_id("https://drive.google.com/open?id=1AbC_d-EfGh123"), "1AbC_d-EfGh123")
        self.assertEqual(drive.folder_id(" 1AbC_d-EfGh123 "), "1AbC_d-EfGh123")
        for bad in ("", "krótkie", "https://drive.google.com/drive/folders/zle;id123456", "a b c d e f g h i j"):
            self.assertEqual(drive.folder_id(bad), "", bad)

    def test_adres_powrotu(self):
        ok = "http://127.0.0.1:53682/?state=S1&code=4/0Ab&scope=https://www.googleapis.com/auth/drive.readonly"
        self.assertIn("code=4%2F0Ab", drive.back_query(ok, "S1"))
        for bad in (ok.replace("S1", "S2"), ok.replace("127.0.0.1", "evil.example"), ok.replace("53682", "8080"),
                    ok.replace("http:", "https:"), ok.replace("/?", "/x?"), ok + "&x=1",
                    "http://127.0.0.1:53682/?state=S1", "http://127.0.0.1:53682/?state=S1&error=access_denied", ""):
            self.assertIsNone(drive.back_query(bad, "S1"), bad)
        self.assertIsNone(drive.back_query(ok, ""))


class Logowanie(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.card = os.path.join(self.tmp, "szkice", "proj")
        os.makedirs(self.card)
        self.rclone = os.path.join(self.tmp, "rclone")
        shutil.copy(ATRAPA, self.rclone)
        os.chmod(self.rclone, os.stat(self.rclone).st_mode | stat.S_IEXEC)
        self.port = free_port()
        os.environ["ATRAPA_RCLONE_PORT"] = str(self.port)
        log = os.path.join(self.tmp, "pomocnik")
        helper = [sys.executable, "-c", "import sys; open(%r, 'a').write(' '.join(sys.argv[1:]) + '\\n')" % log]
        self.d = drive.Drive(lambda pid: self.card if pid == "proj" else None, rclone=self.rclone, helper=helper,
                             conf=os.path.join(self.tmp, "cfg", "rclone.conf"), data_dir=os.path.join(self.tmp, "dane"),
                             port=self.port)

    def tearDown(self):
        self.d.cancel("proj")
        os.environ.pop("ATRAPA_RCLONE_PORT", None)
        shutil.rmtree(self.tmp)

    def helper_calls(self):
        try:
            with open(os.path.join(self.tmp, "pomocnik")) as f:
                return f.read().splitlines()
        except OSError:
            return []

    def test_polaczenie_i_odlaczenie(self):
        self.assertEqual(self.d.start("obcy", "1AbC_d-EfGh123")[0], 404)
        self.assertEqual(self.d.start("proj", "zly")[0], 400)
        code, err, extra = self.d.start("proj", "https://drive.google.com/drive/folders/1AbC_d-EfGh123")
        self.assertEqual((code, err), (200, ""))
        self.assertTrue(extra["loginUrl"].startswith("https://accounts.google.com/"))
        st = self.d.status("proj")[2]
        self.assertEqual((st["login"], st["connected"]), (True, False))
        self.assertEqual(self.d.finish("proj", "http://127.0.0.1:%d/?state=zly&code=1" % self.port)[0], 400)
        code, err, _ = self.d.finish("proj", "http://127.0.0.1:%d/?state=St4te-xyz&code=4/0Ab&scope=x" % self.port)
        self.assertEqual((code, err), (200, ""))
        st = self.d.status("proj")[2]
        self.assertEqual((st["connected"], st["login"], st["folder"]), (True, False, "1AbC_d-EfGh123"))
        self.assertEqual(self.helper_calls(), ["proj " + self.card])                 # montowanie przez pomocnika roota
        self.assertNotIn("TAJNY-TOKEN", repr(st) + repr(extra))
        self.assertEqual(self.d.start("proj", "1AbC_d-EfGh123")[0], 409)            # już połączony
        self.assertEqual(self.d.disconnect("proj")[:2], (200, ""))
        self.assertEqual(self.helper_calls()[-1], "--wylacz proj")
        self.assertFalse(self.d.status("proj")[2]["connected"])

    def test_anulowanie_usuwa_wpis(self):
        self.assertEqual(self.d.start("proj", "1AbC_d-EfGh123")[0], 200)
        with open(os.path.join(self.tmp, "cfg", "rclone.conf.zdalne")) as f:
            self.assertIn("drive-proj", f.read())                               # rclone zapisał wpis przed logowaniem
        self.assertFalse(self.d.status("proj")[2]["connected"])
        self.d.cancel("proj")
        st = self.d.status("proj")[2]
        self.assertEqual((st["connected"], st["login"]), (False, False))
        with open(os.path.join(self.tmp, "cfg", "rclone.conf.zdalne")) as f:
            self.assertNotIn("drive-proj", f.read())
        self.assertEqual(self.d.start("proj", "1AbC_d-EfGh123")[0], 200)        # można zacząć od nowa

    def test_bez_rclone(self):
        d = drive.Drive(lambda pid: self.card, rclone="", data_dir=self.tmp)
        self.assertEqual(d.status("proj")[2]["available"], False)
        self.assertEqual(d.start("proj", "1AbC_d-EfGh123")[0], 409)


if __name__ == "__main__":
    unittest.main()
