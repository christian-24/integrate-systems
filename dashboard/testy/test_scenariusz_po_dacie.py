"""Scenariusz filmu po zmianie daty publikacji (zgłoszenie właściciela, 7. raz): publikacja z filmem zachowuje swój
folder posta i scenariusz.md niezależnie od kiedy: (materiał:, tytuł w scenariusz.md, data tylko bez wątpliwości).
Układ jak w Shield & Silent 26.11: trzy filmy przeniesione na jeden dzień, scenariusz jednego leży w folderze posta
ze zdjęciami."""
import datetime
import json
import os
import tempfile
import unittest
from urllib.parse import quote

from test_serwer import Serwer

import scenariusz  # noqa: E402  (ścieżki ustawia wspolne.py)
import server  # noqa: E402

TODAY = datetime.date.today()
D = lambda n: (TODAY + datetime.timedelta(days=n)).isoformat()   # noqa: E731
NEW, OLD_A, OLD_B, OLD_C = D(3), D(-2), D(-1), D(1)            # nowy dzień i dni sprzed przeplanowania

FILM_A = "Opublikuj film Wygłuszanie: „To samo auto. Lewe drzwi: fabryka. Prawe: wygłuszone.”"
FILM_B = "Opublikuj film Wygłuszanie: „Ten sam puk. Miernik nie kłamie.”"
FILM_C = "Opublikuj film Auto klienta (archiwum 1)"
PHOTO = "Opublikuj post „Tak wygląda wygłuszenie od środka”"
PHOTO_NEW = "Opublikuj post „Zima w warsztacie”"
DIR_A = OLD_A + "-wygluszenie-od-srodka"                       # folder posta ze zdjęciami + scenariusz filmu A
DIR_B = OLD_B + "-film-wygluszanie-ten-sam-puk-miernik-nie"
DIR_C = OLD_C + "-film-auto-klienta-archiwum-1"
DIR_PHOTO_NEW = NEW + "-zima-w-warsztacie"                     # inny post z tą samą datą co filmy


def script(title, day, extra=""):
    return ("# Scenariusz nagrania: %s\n\n- stan: propozycja\n- publikacja: %s\n- nagranie: %s\n\n"
            "## Po co\nPokazać różnicę w hałasie.%s\n\n## Co nagrać\n- [ ] Drzwi z bliska | 5 s\n- [ ] Miernik | 10 s\n\n"
            "## Jak\n- Miejsce: warsztat\n\n## Co powiedzieć\nTo samo auto, inna cisza.\n\n## Na koniec\nNapisz model auta.\n\n"
            "## Gotowe gdy\nDwa ujęcia, razem 15 s.\n" % (title, day, day, extra))


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


class Przypisanie(unittest.TestCase):
    """scenariusz.assign bez serwera: daty z opisu zgłoszenia (folder 2026-11-23, kiedy 2026-11-27)."""

    def test_przeniesiona_data_i_obcy_post(self):
        with tempfile.TemporaryDirectory() as cards:
            write(os.path.join(cards, "posty", "2026-11-23-film-wygluszanie-ten-sam-puk-miernik-nie", "scenariusz.md"),
                  script("Film Wygłuszanie: „Ten sam puk. Miernik nie kłamie.”", "2026-11-23"))
            write(os.path.join(cards, "posty", "2026-11-27-zima-w-warsztacie", "post.md"), "# Post\n")
            pubs = [{"id": "f", "title": FILM_B, "date": "2026-11-27", "channel": "reels"},
                    {"id": "p", "title": PHOTO_NEW, "date": "2026-11-27", "channel": "facebook"}]
            got = scenariusz.assign(cards, pubs)
            self.assertEqual(os.path.basename(got["f"]), "2026-11-23-film-wygluszanie-ten-sam-puk-miernik-nie")
            self.assertNotIn("p", got)                                  # post bez filmu: po dacie, nie przez assign
            # bez scenariusza: film nie bierze folderu innego posta z tą samą datą
            os.remove(os.path.join(got["f"], "scenariusz.md"))
            self.assertEqual(scenariusz.assign(cards, pubs), {})

    def test_material_wygrywa_i_tytul_po_normalizacji(self):
        with tempfile.TemporaryDirectory() as cards:
            write(os.path.join(cards, "posty", "2026-11-01-cokolwiek", "scenariusz.md"), script("Inny tytuł", "2026-11-01"))
            pub = {"id": "f", "title": FILM_C, "date": "2026-11-27", "channel": "reels",
                   "detail": {"refs": [{"path": "posty/2026-11-01-cokolwiek/scenariusz.md", "anchor": ""}]}}
            self.assertEqual(os.path.basename(scenariusz.assign(cards, [pub])["f"]), "2026-11-01-cokolwiek")
            self.assertTrue(scenariusz.same_title("Film Wygłuszanie: „Ten sam puk. Miernik nie kłamie.”",
                                                  "film  wygłuszanie: \"TEN SAM PUK. Miernik nie kłamie.\""))
            self.assertFalse(scenariusz.same_title("Film Auto klienta (archiwum 1)", "Film Auto klienta (archiwum 2)"))


class PoDacie(Serwer):
    def setUp(self):
        super().setUp()
        path = os.path.join(self.folder, "KARTA.md")
        with open(path, encoding="utf-8") as f:
            first, rest = f.read().split("\n", 1)
        write(path, first + "\n\n- nagrywa: ty\n" + rest)
        rows = [(PHOTO, "instagram, facebook", OLD_A, "x"), (PHOTO_NEW, "facebook", NEW, " "),
                (FILM_A, "reels, tiktok", NEW, " "), (FILM_B, "reels, tiktok", NEW, " "), (FILM_C, "reels, tiktok", NEW, " ")]
        write(os.path.join(self.folder, "kampanie", "zima.md"),
              "# Kampania: Zima\n\n- stan: w toku\n- kanały: reels\n\n## Grupa docelowa\nx\n\n## Przekaz\nx\n\n## Harmonogram\n"
              + "".join("- [%s] %s | kto: ty | kanał: %s | kiedy: %s\n" % (st, t, ch, d) for t, ch, d, st in rows)
              + "\n## Wyniki i wnioski\n")
        posty = os.path.join(self.folder, "posty")
        write(os.path.join(posty, DIR_A, "post.md"), "# Post\n\n## Post\nTak wygląda wygłuszenie od środka.\n")
        write(os.path.join(posty, DIR_A, "grafika.png"), "png")
        write(os.path.join(posty, DIR_A, "scenariusz.md"),
              script("Film Wygłuszanie: „To samo auto. Lewe drzwi: fabryka. Prawe: wygłuszone.”", OLD_A))
        write(os.path.join(posty, DIR_B, "scenariusz.md"), script("Film Wygłuszanie: „Ten sam puk. Miernik nie kłamie.”", OLD_B))
        write(os.path.join(posty, DIR_C, "scenariusz.md"), script("Film Auto klienta (archiwum 1)", OLD_C))
        write(os.path.join(posty, DIR_PHOTO_NEW, "post.md"), "# Post\n\n## Post\nZima w warsztacie.\n")
        self.pid = self.data()["projects"][0]["id"]

    def pub(self, title):
        return next(t for t in self.data()["tasks"] if t["title"] == title)

    def info(self, title):
        status, _, text = self.request("GET", "/api/scenariusz?project=%s&date=%s&id=%s"
                                       % (self.pid, NEW, quote(self.pub(title)["id"])))
        self.assertEqual(status, 200, text)
        return json.loads(text)

    def test_trzy_filmy_jeden_dzien_kazdy_swoj_scenariusz(self):
        want = {FILM_A: (DIR_A, "To samo auto"), FILM_B: (DIR_B, "Ten sam puk"), FILM_C: (DIR_C, "Auto klienta")}
        for title, (folder, words) in want.items():
            info = self.info(title)
            self.assertTrue(info["exists"], title)
            self.assertEqual(info["post"], folder, title)
            self.assertIn(words, info["text"])
            self.assertIn(words, info["script"]["title"])
        for title in want:                                       # dane panelu: stan scenariusza przy każdym filmie
            self.assertEqual(self.pub(title)["script"]["shots"], 2, title)
            self.assertNotIn("missingMaterial", self.pub(title))
        self.assertNotIn("script", self.pub(PHOTO_NEW))           # post ze zdjęciami nie dostaje scenariusza filmu

    def test_przeniesiona_data_przez_funkcje_trasy(self):
        code, _, extra = server.script_info(self.pid, NEW, self.pub(FILM_B)["id"])
        self.assertEqual((code, extra["post"], extra["date"]), (200, DIR_B, NEW))
        # okno otwarte przed przeplanowaniem (stary dzień w żądaniu): id wskazuje tę samą publikację
        code, _, extra = server.script_info(self.pid, OLD_B, self.pub(FILM_B)["id"])
        self.assertEqual((code, extra["post"]), (200, DIR_B))
        # podgląd publikacji na osi czasu (przycisk „Kopiuj scenariusz”): pełny tekst scenariusza po id
        status, _, text = self.request("GET", "/api/reklama/tekst?project=%s&date=%s&kod=&id=%s"
                                       % (self.pid, NEW, quote(self.pub(FILM_C)["id"])))
        self.assertEqual(status, 200)
        with open(os.path.join(self.folder, "posty", DIR_C, "scenariusz.md"), encoding="utf-8") as f:
            self.assertEqual(json.loads(text)["scenario"], f.read())

    def test_film_nie_dostaje_folderu_innego_posta(self):
        os.remove(os.path.join(self.folder, "posty", DIR_C, "scenariusz.md"))
        os.rmdir(os.path.join(self.folder, "posty", DIR_C))
        info = self.info(FILM_C)
        self.assertFalse(info["exists"])
        self.assertNotEqual(info["post"], DIR_PHOTO_NEW)          # ten sam dzień, inny post: nie jego folder
        self.assertEqual(info["post"], "")
        self.assertEqual(self.pub(FILM_C)["script"]["state"], "")

    def test_zmiana_daty_bez_nowego_zadania_scenariusza(self):
        data, index = server.load_projects()
        self.assertFalse(self.manager._plan_scripts(data, index, TODAY))
        self.assertFalse([t for t in self.data()["tasks"] if t["title"].startswith(scenariusz.PREP_TASK)])
        code, ans = self.post("/api/scenariusz/przygotuj", {"project": self.pid, "date": NEW, "id": self.pub(FILM_A)["id"]})
        self.assertEqual(code, 409, ans)                           # scenariusz już jest
        self.assertFalse([t for t in self.data()["tasks"] if t["title"].startswith(scenariusz.PREP_TASK)])
        self.assertEqual(sorted(os.listdir(os.path.join(self.folder, "posty"))),
                         sorted([DIR_A, DIR_B, DIR_C, DIR_PHOTO_NEW]))   # żaden nowy pusty folder

    def test_nowy_scenariusz_dopisuje_material_pod_publikacja(self):
        os.remove(os.path.join(self.folder, "posty", DIR_B, "scenariusz.md"))
        data, index = server.load_projects()
        self.assertTrue(self.manager._plan_scripts(data, index, TODAY))
        prep = [t for t in self.data()["tasks"] if t["title"].startswith(scenariusz.PREP_TASK)]
        self.assertEqual([scenariusz.prep_of(t["title"], self.pub(FILM_B)) for t in prep], [True])
        name = os.path.basename(scenariusz.new_post_dir(self.folder, NEW, scenariusz.pub_title(self.pub(FILM_B))))
        rel = "posty/%s/scenariusz.md" % name
        self.assertIn(rel, [r["path"] for r in self.pub(FILM_B)["detail"]["refs"]])   # materiał: pod publikacją
        self.assertIn(rel, prep[0]["detail"]["doneWhen"])
        # agent zapisał scenariusz z innym nagłówkiem, potem publikacja zmieniła kiedy: materiał: trzyma powiązanie
        write(os.path.join(self.folder, rel), script("Zupełnie inny nagłówek", NEW))
        path = os.path.join(self.folder, "kampanie", "zima.md")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        write(path, text.replace("%s | kto: ty | kanał: reels, tiktok | kiedy: %s" % (FILM_B, NEW),
                                 "%s | kto: ty | kanał: reels, tiktok | kiedy: %s" % (FILM_B, D(5))))
        self.assertEqual(self.pub(FILM_B)["date"][:10], D(5))
        self.assertEqual(self.info(FILM_B)["post"], name)
        data, index = server.load_projects()
        self.assertFalse(self.manager._plan_scripts(data, index, TODAY))
        self.assertEqual(len([t for t in self.data()["tasks"] if t["title"].startswith(scenariusz.PREP_TASK)]), 1)

    def test_krotszy_tekst_nie_kasuje_po_cichu(self):
        info = self.info(FILM_B)
        path = os.path.join(self.folder, "posty", DIR_B, "scenariusz.md")
        with open(path, encoding="utf-8") as f:
            before = f.read()
        body = {"project": self.pid, "date": NEW, "id": self.pub(FILM_B)["id"], "old": info["version"],
                "text": "# Scenariusz nagrania: Film\n\n## Po co\nKrótko.\n"}
        code, ans = self.post("/api/scenariusz/tekst", body)
        self.assertEqual((code, ans.get("confirm")), (409, True), ans)
        with open(path, encoding="utf-8") as f:
            self.assertEqual(f.read(), before)                     # bez potwierdzenia nic się nie zmienia
        code, ans = self.post("/api/scenariusz/tekst", dict(body, text=""))
        self.assertEqual(code, 400)                                # pusty tekst nigdy
        code, ans = self.post("/api/scenariusz/tekst", dict(body, potwierdz=True))
        self.assertEqual(code, 200, ans)
        # nowy nagłówek („Film”) nie zrywa powiązania: panel dopisał materiał: pod publikacją
        self.assertIn("posty/%s/scenariusz.md" % DIR_B, [r["path"] for r in self.pub(FILM_B)["detail"]["refs"]])
        with open(os.path.join(self.folder, "posty", DIR_B, scenariusz.BACKUP), encoding="utf-8") as f:
            self.assertEqual(f.read(), before)                     # poprzednia wersja zostaje obok
        # przywrócenie pełnej treści i drobna poprawka bez utraty sekcji: zapis od razu, bez pytania
        for text in (before, before.replace("razem 15 s", "razem 20 s")):
            code, ans = self.post("/api/scenariusz/tekst", dict(body, old=self.info(FILM_B)["version"], text=text))
            self.assertEqual(code, 200, ans)
        self.assertIn("razem 20 s", self.info(FILM_B)["text"])
        # usunięcie treści całej sekcji też wymaga potwierdzenia
        cut = before.replace("To samo auto, inna cisza.", "").replace("razem 15 s", "razem 20 s")
        code, ans = self.post("/api/scenariusz/tekst", dict(body, old=self.info(FILM_B)["version"], text=cut))
        self.assertEqual((code, ans.get("confirm")), (409, True), ans)
        self.assertIn("Co powiedzieć", ans["error"])


if __name__ == "__main__":
    unittest.main()
