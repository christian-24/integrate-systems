"""Logowanie Claude przez panel na serwerze bez okna: adres strony logowania i kod wklejony w panelu."""
import unittest

from wspolne import Baza


class LogowanieWeb(Baza):
    def setUp(self):
        super().setUp()
        self.web = self.new_manager(PANEL_LOGIN_WEB="1")

    def test_adres_i_dobry_kod(self):
        code, err, extra = self.web.open_login("claude")
        self.assertEqual(code, 200, err)
        self.assertTrue(extra["url"].startswith("https://claude.com/cai/oauth/authorize"))
        snap = self.web.snapshot()
        self.assertEqual(snap["login"], {"active": True, "url": extra["url"]})
        self.assertTrue(snap["loginWeb"])
        self.assertEqual(self.web.open_login("claude")[2]["url"], extra["url"])     # drugi klik: ten sam proces
        code, err, extra = self.web.submit_login_code("kod#dobry")
        self.assertEqual(code, 200, err)
        self.assertTrue(extra["loggedIn"])
        self.assertEqual(self.web.snapshot()["login"], {"active": False})

    def test_niepelny_kod_pozwala_poprawic(self):
        self.web.open_login("claude")
        code, err, _ = self.web.submit_login_code("niepelny")
        self.assertEqual(code, 400)
        self.assertIn("full code", err)
        self.assertNotIn("Paste code", err)
        self.assertTrue(self.web.snapshot()["login"]["active"])
        self.assertEqual(self.web.submit_login_code("kod#dobry")[0], 200)

    def test_zly_kod_konczy_logowanie(self):
        self.web.open_login("claude")
        code, err, _ = self.web.submit_login_code("kod#zly")
        self.assertEqual(code, 400)
        self.assertIn("invalid code", err)
        self.assertFalse(self.web.snapshot()["login"]["active"])
        self.assertEqual(self.web.submit_login_code("kod#dobry")[0], 409)

    def test_odmowy(self):
        self.assertEqual(self.web.submit_login_code("kod#dobry")[0], 409)          # bez rozpoczętego logowania
        self.web.open_login("claude")
        self.assertEqual(self.web.submit_login_code("")[0], 400)
        self.assertEqual(self.web.submit_login_code("dwa slowa")[0], 400)
        self.assertEqual(self.web.open_login("codex")[0], 409)

    def test_trasa_serwera(self):
        import server
        self.assertIn("/api/agent/login-code", server.WRITES)


if __name__ == "__main__":
    unittest.main()
