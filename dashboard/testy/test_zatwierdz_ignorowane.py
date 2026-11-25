"""commit_dirty i stash_save w repozytorium z dowiązaniem KARTA.md wykluczonym w .git/info/exclude (błąd „paths are ignored”)."""
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "standard"))
import kopie  # noqa: E402


def git(cwd, *a):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t"] + list(a), cwd=cwd, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class Ignorowane(unittest.TestCase):
    def repo(self, d):
        r = os.path.join(d, "r")
        os.makedirs(os.path.join(r, "site", "node_modules", "x"))
        git(d, "init", "-q", "r")
        with open(os.path.join(r, "a.txt"), "w") as f:
            f.write("a\n")
        with open(os.path.join(r, ".gitignore"), "w") as f:
            f.write("node_modules/\n")
        git(r, "add", "a.txt", ".gitignore")
        git(r, "commit", "-qm", "i")
        with open(os.path.join(r, "a.txt"), "a") as f:
            f.write("b\n")
        with open(os.path.join(r, "nowy.js"), "w") as f:
            f.write("n\n")
        with open(os.path.join(r, "site", "node_modules", "x", "f"), "w") as f:
            f.write("y\n")
        os.symlink(d, os.path.join(r, "KARTA.md"))
        with open(os.path.join(r, ".git", "info", "exclude"), "a") as f:
            f.write("KARTA.md\n")
        return r

    def test_zatwierdz(self):
        with tempfile.TemporaryDirectory() as d:
            r = self.repo(d)
            ok, sha = kopie.commit_dirty(r, "test")
            self.assertTrue(ok, sha)
            out = subprocess.run(["git", "show", "--name-only", "--format=", "HEAD"], cwd=r, capture_output=True,
                                 text=True).stdout.split()
            self.assertEqual(sorted(out), ["a.txt", "nowy.js"])

    def test_odloz(self):
        with tempfile.TemporaryDirectory() as d:
            r = self.repo(d)
            ok, ref = kopie.stash_save(r, "test")
            self.assertTrue(ok, ref)
            self.assertFalse(os.path.exists(os.path.join(r, "nowy.js")))


if __name__ == "__main__":
    unittest.main()
