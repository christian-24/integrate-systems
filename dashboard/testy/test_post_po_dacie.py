"""Folder posta po dacie: edytor posta, wgranie filmu i nagranie filmu szukają folderu publikacji tak jak scenariusz
(materiał:, nazwa i tytuł, data tylko bez wątpliwości), po parametrze id publikacji. Dwie publikacje jednego dnia
(post ze zdjęciami i film) nie biorą swoich folderów nawzajem; po zmianie kiedy: post zostaje przy publikacji."""
import datetime
import json
import os
import unittest
from urllib.parse import quote

from test_serwer import Serwer

import agents  # noqa: E402  (ścieżki ustawia wspolne.py)
import scenariusz  # noqa: E402
import server  # noqa: E402

TODAY = datetime.date.today()
D = lambda n: (TODAY + datetime.timedelta(days=n)).isoformat()   # noqa: E731
DAY, OLD, NEW = D(4), D(-2), D(6)

PHOTO = "Opublikuj post „Zimowe opony”"                          # post ze zdjęciami, kanał bez filmu
FILM = "Opublikuj film „Ten sam puk”"                            # film tego samego dnia
MOVED = "Opublikuj post „Cennik na grudzień”"                    # post przeniesiony z OLD na NEW
DIR_PHOTO = DAY + "-post-zimowe-opony"
DIR_FILM = DAY + "-film-ten-sam-puk"
DIR_MOVED = OLD + "-post-cennik-na-grudzien"
DIR_OTHER_NEW = NEW + "-inny-post"                               # cudzy folder z nową datą przeniesionego posta


def write(path, text, mode="w"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, mode, **({} if "b" in mode else {"encoding": "utf-8"})) as f:
        f.write(text)


class FakeRecorder:
    def __init__(self):
        self.calls = []

    def start(self, folder, title=""):
        self.calls.append(folder)
        return (404, "Nie ma posta na ten dzień.") if not folder else (202, "", {"state": "running"})


class PostPoDacie(Serwer):
    def setUp(self):
        super().setUp()
        rows = [(PHOTO, "facebook, instagram", DAY), (FILM, "reels, tiktok", DAY), (MOVED, "facebook", NEW)]
        write(os.path.join(self.folder, "kampanie", "rytm.md"),
              "# Kampania: Rytm\n\n- stan: w toku\n- kanały: facebook\n\n## Grupa docelowa\nx\n\n## Przekaz\nx\n\n"
              "## Harmonogram\n" + "".join("- [ ] %s | kto: ty | kanał: %s | kiedy: %s\n" % r for r in rows)
              + "\n## Wyniki i wnioski\n")
        posty = os.path.join(self.folder, "posty")
        write(os.path.join(posty, DIR_PHOTO, "post.md"), "# Zimowe opony\n\n## Facebook\nOpis zdjęć\n")
        write(os.path.join(posty, DIR_PHOTO, "grafika.png"), b"PNG", "wb")
        write(os.path.join(posty, DIR_FILM, "post.md"), "# Ten sam puk\n\n## Reels\nOpis filmu\n")
        write(os.path.join(posty, DIR_FILM, "scenariusz.json"), "{}")
        write(os.path.join(posty, DIR_MOVED, "post.md"), "# Cennik\n\n## Facebook\nOpis cennika\n")
        write(os.path.join(posty, DIR_OTHER_NEW, "post.md"), "# Inny\n\n## Facebook\nCudzy post\n")
        self.pid = self.data()["projects"][0]["id"]
        self.rec = FakeRecorder()

    def nagraj(self, body):
        """record_film z podstawioną nagrywarką (tylko na czas wywołania; dane panelu pytają prawdziwą)."""
        saved, server.get_recorder = server.get_recorder, lambda: self.rec
        try:
            server.record_film(body)
        finally:
            server.get_recorder = saved

    def pub(self, title):
        return next(t for t in self.data()["tasks"] if t["title"] == title)

    def editor(self, title=None, day=DAY):
        q = "/api/post?project=%s&date=%s" % (self.pid, day)
        if title:
            q += "&id=" + quote(self.pub(title)["id"])
        status, _, text = self.request("GET", q)
        return status, json.loads(text)

    def upload(self, title, day=DAY):
        status, _, text = self.request("POST", "/api/post/film?project=%s&date=%s&id=%s" % (self.pid, day, quote(self.pub(title)["id"])),
                                       raw=b"MP4DATA", ctype="video/mp4")
        return status, json.loads(text)

    def record(self, title, day=DAY):
        self.rec.calls.clear()
        self.nagraj({"project": self.pid, "date": day, "id": self.pub(title)["id"], "title": title})
        return os.path.basename(self.rec.calls[0] or "") if self.rec.calls else None

    def path(self, *parts):
        return os.path.join(self.folder, "posty", *parts)

    # --- dwie publikacje jednego dnia: post ze zdjęciami i film ---
    def test_edytor_dwie_publikacje_jednego_dnia(self):
        status, d = self.editor(PHOTO)
        self.assertEqual((status, d["folder"]), (200, DIR_PHOTO))
        status, d = self.editor(FILM)
        self.assertEqual((status, d["folder"]), (200, DIR_FILM))
        status, d = self.editor()                                  # sama data: dwa różne posty, bez zgadywania
        self.assertEqual(status, 404)
        # zapis opisu trafia do posta tej publikacji
        code, err = server.post_set_text({"project": self.pid, "date": DAY, "id": self.pub(FILM)["id"],
                                          "section": "Reels", "text": "Nowy opis filmu", "old": "Opis filmu"})
        self.assertEqual(code, 200, err)
        with open(self.path(DIR_FILM, "post.md"), encoding="utf-8") as f:
            self.assertIn("Nowy opis filmu", f.read())
        with open(self.path(DIR_PHOTO, "post.md"), encoding="utf-8") as f:
            self.assertNotIn("Nowy opis filmu", f.read())

    def test_wgranie_filmu_dwie_publikacje_jednego_dnia(self):
        status, ans = self.upload(FILM)
        self.assertEqual(status, 200, ans)
        self.assertTrue(os.path.isfile(self.path(DIR_FILM, "film.mp4")))
        self.assertFalse(os.path.exists(self.path(DIR_PHOTO, "film.mp4")))   # post ze zdjęciami bez filmu

    def test_nagranie_dwie_publikacje_jednego_dnia(self):
        self.assertEqual(self.record(FILM), DIR_FILM)
        self.assertEqual(self.record(PHOTO), DIR_PHOTO)
        self.rec.calls.clear()
        self.nagraj({"project": self.pid, "date": DAY, "title": FILM})   # bez id: dzień niejednoznaczny
        self.assertEqual(self.rec.calls, [None])

    def test_post_bez_filmu_nie_bierze_folderu_filmu(self):
        os.remove(self.path(DIR_PHOTO, "post.md"))
        os.remove(self.path(DIR_PHOTO, "grafika.png"))
        os.rmdir(self.path(DIR_PHOTO))
        status, _ = self.editor(PHOTO)
        self.assertEqual(status, 404)                              # folder filmu z tą samą datą nie jest jego
        self.assertEqual(self.record(PHOTO), "")
        self.assertEqual(self.editor(FILM)[1]["folder"], DIR_FILM)
        # i odwrotnie: film bez własnego folderu nie bierze posta ze zdjęciami
        write(self.path(DIR_PHOTO, "post.md"), "# Zimowe opony\n")
        for n in os.listdir(self.path(DIR_FILM)):
            os.remove(self.path(DIR_FILM, n))
        os.rmdir(self.path(DIR_FILM))
        self.assertEqual(self.editor(FILM)[0], 404)
        self.assertEqual(self.upload(FILM)[0], 400)
        self.assertFalse(os.path.exists(self.path(DIR_PHOTO, "film.mp4")))
        self.assertEqual(self.editor(PHOTO)[1]["folder"], DIR_PHOTO)

    # --- przeniesiona data: folder z OLD, publikacja na NEW, tego dnia leży cudzy folder ---
    def test_przeniesiona_data_edytor_wgranie_nagranie(self):
        for day in (NEW, OLD):                                     # okno otwarte przed albo po zmianie daty
            status, d = self.editor(MOVED, day)
            self.assertEqual((status, d["folder"]), (200, DIR_MOVED), day)
        self.assertEqual(self.record(MOVED, NEW), DIR_MOVED)
        status, ans = self.upload(MOVED, NEW)
        self.assertEqual(status, 200, ans)
        self.assertTrue(os.path.isfile(self.path(DIR_MOVED, "film.mp4")))
        self.assertFalse(os.path.exists(self.path(DIR_OTHER_NEW, "film.mp4")))

    def test_zmiana_daty_w_panelu_dopisuje_material(self):
        t = self.pub(PHOTO)
        code, err = server.update_task({"id": t["id"], "title": t["title"], "changes": {"date": NEW}})[:2]
        self.assertEqual(code, 200, err)
        t = self.pub(PHOTO)
        self.assertEqual(str(t["date"])[:10], NEW)
        self.assertIn("posty/%s/post.md" % DIR_PHOTO, json.dumps(t["detail"].get("refs"), ensure_ascii=False))
        status, d = self.editor(PHOTO, NEW)
        self.assertEqual((status, d["folder"]), (200, DIR_PHOTO))
        self.assertEqual(self.editor(FILM)[1]["folder"], DIR_FILM)

    def test_automat_nie_zaklada_drugiego_posta_po_zmianie_daty(self):
        posts = os.path.join(self.folder, "posty")
        tasks = [t for t in self.data()["tasks"] if t.get("kind") == "publikacja"]
        owned = scenariusz.assign_posts(self.folder, tasks)
        moved = self.pub(MOVED)["id"]
        got = agents.day_posts(posts, sorted(os.listdir(posts)), NEW, owned, moved)
        self.assertIn(self.path(DIR_MOVED), got)
        photo = agents.day_posts(posts, sorted(os.listdir(posts)), DAY, owned, self.pub(PHOTO)["id"])
        self.assertNotIn(self.path(DIR_FILM), photo)               # folder filmu tego dnia nie jest postem zdjęć


if __name__ == "__main__":
    unittest.main()
