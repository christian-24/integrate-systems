"""Zasoby serwera (dashboard/zasoby.py): /proc, dysk, rozmiary folderów i projektów bez .git i dowiązań."""
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import zasoby  # noqa: E402

MEMINFO = "MemTotal:        3800000 kB\nMemFree:          200000 kB\nMemAvailable:    3100000 kB\nSwapTotal:       2097148 kB\nSwapFree:        2000000 kB\n"


class Zasoby(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def put(self, rel, size):
        path = os.path.join(self.tmp, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(b"x" * size)
        return path

    def test_proc(self):
        path = os.path.join(self.tmp, "meminfo")
        with open(path, "w") as f:
            f.write(MEMINFO)
        self.assertEqual(zasoby.meminfo(path), {"total": 3800000 * 1024, "available": 3100000 * 1024,
                                                 "swapTotal": 2097148 * 1024, "swapFree": 2000000 * 1024})
        self.assertIsNone(zasoby.meminfo(os.path.join(self.tmp, "brak")))
        with open(path, "w") as f:
            f.write("0.25 0.10 0.05 1/200 999\n")
        self.assertEqual(zasoby.loadavg(path), [0.25, 0.10, 0.05])
        with open(path, "w") as f:
            f.write("266400.12 500000.00\n")
        self.assertEqual(zasoby.uptime(path), 266400)

    def test_rozmiary_bez_git_i_dowiazan(self):
        self.put("repo/a.md", 5000)
        self.put("repo/rozmowy/r.jsonl", 9000)
        self.put("repo/.git/objects/x", 7000)
        card = os.path.dirname(self.put("karta/media/f.mp4", 200000))
        os.symlink(os.path.join(self.tmp, "karta/media/f.mp4"), os.path.join(self.tmp, "repo/link.mp4"))
        size, git, files = zasoby.tree_size(os.path.join(self.tmp, "repo"))
        self.assertEqual(files, 2)
        self.assertGreaterEqual(size, 14000)
        self.assertLess(size, 100000)                   # dowiązanie do filmu nie liczone
        self.assertGreaterEqual(git, 7000)
        res = zasoby.Resources([("Repo", os.path.join(self.tmp, "repo")), ("Brak", os.path.join(self.tmp, "nie-ma"))],
                               lambda: {"p": ("Projekt", [os.path.join(self.tmp, "repo"), os.path.dirname(card),
                                                          os.path.join(self.tmp, "repo")])},
                               disk=self.tmp, background=False)
        st = res.state()
        self.assertEqual([f["label"] for f in st["folders"]], ["Repo"])
        self.assertEqual(st["projects"][0]["files"], 3)  # repo (2) + karta (1), repo raz
        self.assertGreater(st["disk"]["total"], 0)
        self.assertEqual(st["cpus"], os.cpu_count() or 1)

    def test_pamiec_podreczna(self):
        now = [1000.0]
        calls = []
        res = zasoby.Resources([], lambda: calls.append(1) or {}, disk=self.tmp, clock=lambda: now[0], background=False)
        res.state()
        res.state()
        self.assertEqual(len(calls), 1)                  # rozmiary liczone raz na FOLDERS_TTL
        now[0] += zasoby.FOLDERS_TTL + 1
        res.state()
        self.assertEqual(len(calls), 2)
        res2 = zasoby.Resources([], lambda: 1 / 0, disk=self.tmp, background=False)
        self.assertEqual(res2.state()["projects"], [])   # zepsuty rejestr: bez listy, bez wyjątku


if __name__ == "__main__":
    unittest.main()
