"""GitHub projektu: zamiana adresu origin na link (bez danych logowania) i pole git w /api/data."""
import subprocess
import unittest

from wspolne import Baza, server


class Adresy(unittest.TestCase):
    def test_zamiana(self):
        cases = {
            "git@github.com:Firma/Repo.git": ("github", "https://github.com/Firma/Repo", "github.com"),
            "https://github.com/firma/repo.git": ("github", "https://github.com/firma/repo", "github.com"),
            "https://github.com/firma/repo/": ("github", "https://github.com/firma/repo", "github.com"),
            "https://user:ghp_TAJNY@github.com/firma/repo.git": ("github", "https://github.com/firma/repo", "github.com"),
            "ssh://git@ssh.github.com:443/firma/repo.git": ("github", "https://github.com/firma/repo", "github.com"),
            "https://oauth2:tok@gitlab.example.com:8443/grupa/repo.git":
                ("inny", "https://gitlab.example.com:8443/grupa/repo", "gitlab.example.com"),
            "git@gitlab.com:grupa/repo.git": ("inny", "", "gitlab.com"),
            "/srv/git/repo.git": ("inny", "", ""),
            "": ("", "", ""),
        }
        for raw, want in cases.items():
            with self.subTest(raw=raw):
                got = server.git_link(raw)
                self.assertEqual(got, want)
                self.assertNotIn("TAJNY", got[1])
                self.assertNotIn("tok", got[1])


class PoleWDanych(Baza):
    def git(self, *args):
        subprocess.run(["git", "-C", self.folder, *args], check=True, capture_output=True)

    def project(self):
        return server.build_data()["projects"][0]["git"]

    def test_brak_repo(self):
        self.assertEqual(self.project(), {"repo": False, "remote": "", "url": "", "host": "", "unpushed": 0,
                                          "branch": ""})

    def test_repo_z_github_i_niewypchniete(self):
        self.git("init", "-q", "-b", "glowna")
        self.git("remote", "add", "origin", "https://x:ghp_TAJNY@github.com/firma/repo.git")
        self.git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "a")
        server._git_state["value"].pop(self.folder, None)
        g = self.project()
        self.assertEqual(g, {"repo": True, "remote": "github", "url": "https://github.com/firma/repo",
                             "host": "github.com", "unpushed": 1, "branch": "glowna"})


if __name__ == "__main__":
    unittest.main()
