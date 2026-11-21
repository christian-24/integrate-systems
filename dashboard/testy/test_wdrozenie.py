"""Rozwój panelu na serwerze: stan gałęzi rozwoj wobec produkcji, hasło panelu testowego, przycisk „Wdróż”."""
import json
import os
import shutil
import subprocess
import tempfile
import unittest

from wspolne import server


def git(repo, *args):
    subprocess.run(["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@t", *args], check=True,
                   capture_output=True)


class Wdrozenie(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.prod = os.path.join(self.tmp, "prod")
        self.dev = os.path.join(self.tmp, "dev")
        os.makedirs(os.path.join(self.prod, "szkice"))
        git(self.tmp, "init", "-q", "-b", "main", self.prod)
        self.commit(self.prod, "a.py", "1", "start")
        git(self.tmp, "clone", "-q", self.prod, self.dev)
        git(self.dev, "checkout", "-q", "-b", "rozwoj")
        self.env = os.path.join(self.tmp, "panel-testowy.env")
        with open(self.env, "w") as f:
            f.write("PANEL_TOKEN=abc123\n")
        self.calls = []
        self.old = {k: getattr(server, k) for k in ("DEV_REPO", "PROD_REPO", "DEPLOY_DIR", "TEST_ENV", "DEPLOY_CMD")}
        server.DEV_REPO, server.PROD_REPO, server.TEST_ENV = self.dev, self.prod, self.env
        server.DEPLOY_DIR = os.path.join(self.tmp, "wdrozenie")
        server.DEPLOY_CMD = ["true"]
        server._deploy.update(at=0.0, value=None)

    def tearDown(self):
        for k, v in self.old.items():
            setattr(server, k, v)
        server._deploy.update(at=0.0, value=None)
        shutil.rmtree(self.tmp)

    def commit(self, repo, name, text, msg):
        with open(os.path.join(repo, name), "w") as f:
            f.write(text)
        git(repo, "add", name)
        git(repo, "commit", "-q", "-m", msg)

    def state(self):
        server._deploy["at"] = 0.0
        return server.deploy_state()

    def test_stan_i_wdrozenie(self):
        st = self.state()
        self.assertEqual((st["ahead"], st["behind"], st["testPassword"], st["last"]), (0, 0, "abc123", None))
        self.assertEqual(st["auto"], os.path.exists(server.AUTO_UNIT))
        self.assertEqual(server.start_deploy({})[0], 400)                      # nic do wdrożenia
        self.commit(self.dev, "b.py", "2", "Nowy widok")
        self.commit(self.prod, "szkice/k.md", "x", "Panel: zmiany z serwera")  # karty nie liczą się do „nowsze”
        st = self.state()
        self.assertEqual((st["ahead"], st["behind"]), (1, 0))
        self.assertEqual(st["commits"][0]["subject"], "Nowy widok")
        self.assertIn("1 file changed", st["stat"])
        self.assertEqual(server.start_deploy({}), (200, ""))
        last = self.state()["last"]
        self.assertEqual(last["state"], "queued")
        self.assertEqual(server.start_deploy({})[0], 409)                      # już trwa
        with open(os.path.join(server.DEPLOY_DIR, "stan.json"), "w") as f:
            json.dump({"state": "rolledback", "text": "panel nie odpowiada", "at": "2026-11-20T23:00:00"}, f)
        with open(os.path.join(server.DEPLOY_DIR, "ostatnie.log"), "w") as f:
            f.write("23:00:01 BŁĄD: panel nie odpowiada\n")
        st = self.state()
        self.assertIn("panel nie odpowiada", st["log"])
        server.DEPLOY_CMD = ["false"]
        self.assertEqual(server.start_deploy({})[0], 500)
        self.commit(self.prod, "c.py", "3", "Poprawka na produkcji")
        self.assertEqual(self.state()["behind"], 1)

    def test_bez_kopii_roboczej(self):
        server.DEV_REPO = os.path.join(self.tmp, "nie-ma")
        self.assertIsNone(server.deploy_state())
        self.assertEqual(server.start_deploy({})[0], 400)


if __name__ == "__main__":
    unittest.main()
