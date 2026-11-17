"""Pulpit projektów (PULPIT.md, część Backend): pola projektu, faza, zbieracz, historia, /api/project/meta."""
import datetime
import json
import os
import unittest

from test_serwer import Serwer
from wspolne import Baza, projekt, quiet, server
import historia

KARTA = """# Karta projektu: Wzorcowy

- stan: %(stan)s
%(pola)s- maszyna: mac

## Cel
Pierwsze zdanie celu.
Drugie zdanie tego samego akapitu.

Drugi akapit nie wchodzi do opisu.

## Zakres
- Coś.

## Poza zakresem
- Nic.

## Definicja ukończenia
- Działa.

## Zasady pracy agentów
- Poziom swobody: 2.
"""


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class PolaProjektu(Baza):
    """Odczyt nowych pól z KARTA.md i faza wyliczona (standard/projekt.py)."""

    def karta(self, stan="aktywny", pola=""):
        write(os.path.join(self.folder, "KARTA.md"), KARTA % {"stan": stan, "pola": pola})

    def project(self, decision=None):
        return projekt.read_project(self.folder, decision=decision)["project"]

    def test_pola_z_karty(self):
        self.karta(pola="- faza: wdrożenie\n- klient: nie\n- próg: pełna\n")
        p = self.project()
        self.assertEqual((p["phase"], p["phaseSource"], p["client"], p["threshold"], p["alias"], p["state"]),
                         ("wdrozenie", "karta", False, "pelna", None, "active"))
        self.assertEqual(p["description"], "Pierwsze zdanie celu. Drugie zdanie tego samego akapitu.")
        self.assertEqual(p["goal"], "Pierwsze zdanie celu.")
        self.assertEqual([d["key"] for d in p["book"]], [d[0] for d in projekt.DOCS])
        self.assertEqual(set(p["book"][0]), {"key", "label", "file", "status", "gaps"})
        self.assertEqual((p["bookOk"], p["bookTotal"]), (p["docsOk"], p["docsTotal"]))
        self.assertEqual(p["book"], p["docs"])

    def test_wartosci_domyslne(self):
        self.karta(pola="- faza: pomysl\n")                       # zapis bez polskich znaków też działa
        p = self.project()
        self.assertEqual((p["phase"], p["client"], p["threshold"]), ("pomysl", True, "pelna"))
        self.karta(pola="- klient: nie\n")
        self.assertEqual(self.project()["threshold"], "lekka")
        self.karta(pola="- klient: nie\n- prog: pełna\n")
        self.assertEqual(self.project()["threshold"], "pelna")

    def test_bledne_wartosci_to_braki_karty(self):
        self.karta(pola="- faza: gotowe\n- klient: może\n- próg: średnia\n")
        p = self.project()
        karta = p["book"][0]
        self.assertEqual(karta["status"], "gaps")
        self.assertEqual(len(karta["gaps"]), 3)
        self.assertEqual((p["phase"], p["phaseSource"], p["client"], p["threshold"]),
                         ("ksiega", "wyliczona", True, "pelna"))

    def test_opis_do_300_znakow(self):
        long = " ".join("Zdanie numer %d jest dość długie, ale pełne." % i for i in range(20))
        write(os.path.join(self.folder, "KARTA.md"), (KARTA % {"stan": "aktywny", "pola": ""}).replace(
            "Pierwsze zdanie celu.\nDrugie zdanie tego samego akapitu.", long))
        d = self.project()["description"]
        self.assertLessEqual(len(d), 300)
        self.assertTrue(d.endswith("pełne."))

    def test_faza_wyliczona(self):
        tasks = os.path.join(self.folder, "ZADANIA.md")
        # karta z szablonu ma braki -> księga
        self.assertEqual((self.project()["phase"], self.project()["phaseSource"]), ("ksiega", "wyliczona"))
        self.karta()
        self.assertEqual(self.project()["phase"], "budowa")
        # backlog wygrywa z brakami
        self.karta(stan="backlog")
        self.assertEqual((self.project()["state"], self.project()["phase"]), ("backlog", "pomysl"))
        self.karta()
        # wszystkie etapy zrobione -> utrzymanie
        write(tasks, "# Zadania\n\n## Etap: Jeden\ntermin: 2026-01-01\n\n- [x] A\n\n## Etap: Dwa\ntermin: 2026-01-02\n"
                     "stan: zamknięty\n\n- [ ] B\n")
        self.assertEqual(self.project()["phase"], "utrzymanie")
        # kampania w toku -> marketing (przed utrzymaniem)
        quiet(projekt.cmd_kampania, self.folder, "Start")
        camp = os.path.join(self.folder, "kampanie", "start.md")
        write(camp, read(camp).replace("- stan: plan", "- stan: w toku"))
        self.assertEqual(self.project()["phase"], "marketing")
        # brak karty -> księga
        os.remove(os.path.join(self.folder, "KARTA.md"))
        self.assertEqual(self.project()["phase"], "ksiega")

    def test_decyzja_zbieracza(self):
        self.karta()
        p = self.project({"stan": "backlog", "klient": False, "alias": "K-ab12"})
        self.assertEqual((p["state"], p["client"], p["threshold"], p["alias"]), ("active", False, "lekka", "K-ab12"))
        write(os.path.join(self.folder, "KARTA.md"), read(os.path.join(self.folder, "KARTA.md"))
              .replace("- stan: aktywny\n", ""))
        p = self.project({"stan": "backlog", "klient": False, "alias": "K-ab12"})
        self.assertEqual((p["state"], p["phase"]), ("backlog", "pomysl"))
        self.assertEqual(self.project({"stan": "wstrzymany"})["state"], "paused")
        self.karta(pola="- klient: tak\n")
        self.assertTrue(self.project({"klient": False})["client"])          # karta wygrywa z decyzją


class Historia(Baza):
    def tasks(self):
        data, _ = server.load_projects()
        return data["tasks"]

    def test_liczenie_stanow(self):
        write(os.path.join(self.folder, "ZADANIA.md"),
              "# Zadania\n\n## Etap: E\ntermin: 2026-01-01\n\n- [ ] a\n- [ ] b\n- [~] c\n- [~] d | wymaga: odbiór\n"
              "- [!] e | blokada: x\n- [!] f | wymaga: odbiór\n- [x] g | wymaga: odbiór\n- [ ] h | wymaga: zgoda\n")
        quiet(projekt.cmd_kampania, self.folder, "Start")                    # publikacje nie wchodzą do historii
        entry = historia.snapshot(self.tasks(), ["projekt-testowy", "pusty"], datetime.date(2026, 11, 12))
        self.assertEqual(entry, {"date": "2026-11-12", "projects": {
            "projekt-testowy": {"todo": 3, "wip": 1, "rev": 2, "blocked": 1, "done": 1, "total": 8},
            "pusty": {"todo": 0, "wip": 0, "rev": 0, "blocked": 0, "done": 0, "total": 0}}})

    def test_zapis_i_odczyt(self):
        today = datetime.date(2026, 11, 12)
        for back in (0, 1, 62, 63, 70):
            day = today - datetime.timedelta(days=back)
            historia.save({"date": day.isoformat(), "projects": {"p": dict.fromkeys(historia.KEYS, back)}})
        historia.save({"date": "2026-11-13", "projects": {}})                 # przyszłość pomijana
        write(os.path.join(self.history_dir, "2026-11-10.json"), "{uszkodzony")
        write(os.path.join(self.history_dir, "notatka.json"), "{}")
        entries = historia.load(today)
        self.assertEqual([e["date"] for e in entries], ["2026-09-11", "2026-11-11", "2026-11-12"])
        self.assertEqual(entries[-1]["projects"]["p"]["total"], 0)
        # nadpisanie pliku z tego dnia, bez plików tymczasowych
        self.assertTrue(historia.save({"date": "2026-11-12", "projects": {"p": dict.fromkeys(historia.KEYS, 5)}}))
        self.assertFalse(historia.save({"date": "2026-11-12", "projects": {"p": dict.fromkeys(historia.KEYS, 5)}}))
        self.assertEqual(historia.load(today)[-1]["projects"]["p"]["done"], 5)
        self.assertFalse([f for f in os.listdir(self.history_dir) if f.startswith(".tmp")])

    def test_katalog_ze_zmiennej(self):
        self.assertEqual(historia.directory(), self.history_dir)
        os.environ["PANEL_HISTORY_DIR"] = ""
        try:
            self.assertEqual(historia.directory(), os.path.join(os.path.dirname(server.HERE), "historia"))
        finally:
            os.environ["PANEL_HISTORY_DIR"] = self.history_dir

    def test_przyklad_zgodny_z_projektami_przykladowymi(self):
        today = datetime.date(2026, 11, 12)
        entries = historia.sample(server.SAMPLE_HISTORY, today)
        self.assertEqual((entries[0]["date"], entries[-1]["date"]), ("2026-09-17", "2026-11-12"))
        self.assertEqual(len(entries), 57)
        self.assertEqual([e["date"] for e in historia.sample(server.SAMPLE_HISTORY)][:2], ["-56", "-55"])
        current = {}
        for folder in server.sample_folders():
            d = projekt.read_project(folder)
            current[d["project"]["id"]] = historia.counts(d["tasks"])
        self.assertEqual(entries[-1]["projects"], current)
        prev = {}
        for e in entries:
            for pid, c in e["projects"].items():
                self.assertIn(pid, current)
                self.assertEqual(sum(c[k] for k in historia.KEYS[:5]), c["total"])
                if pid in prev:
                    self.assertGreaterEqual(c["done"], prev[pid]["done"])
                prev[pid] = c


class Pulpit(Serwer):
    def test_dane_z_nowymi_polami_i_historia(self):
        data = self.data()
        p = data["projects"][0]
        for key in ("phase", "phaseSource", "client", "threshold", "description", "alias", "book", "bookOk",
                    "bookTotal", "origin"):
            self.assertIn(key, p)
        self.assertEqual((p["phase"], p["origin"]), ("ksiega", "registry"))
        today = datetime.date.today().isoformat()
        self.assertEqual(data["history"][-1]["date"], today)
        self.assertEqual(data["history"][-1]["projects"]["projekt-testowy"]["total"], 11)
        self.assertTrue(os.path.exists(os.path.join(self.history_dir, today + ".json")))

    def test_meta(self):
        meta = lambda body: self.post("/api/project/meta", body)
        karta = os.path.join(self.folder, "KARTA.md")
        before = read(karta)
        self.assertEqual(meta({"id": "projekt-testowy", "phase": "wdrozenie", "client": False}),
                         (200, {"ok": True, "error": ""}))
        text = read(karta)
        head = text.split("\n## ")[0]
        self.assertIn("- faza: wdrożenie\n- klient: nie\n", head)
        self.assertEqual(text.replace("- faza: wdrożenie\n- klient: nie\n", ""), before)   # reszta bez zmian
        p = self.data()["projects"][0]
        self.assertEqual((p["phase"], p["phaseSource"], p["client"], p["threshold"]),
                         ("wdrozenie", "karta", False, "lekka"))
        # zmiana istniejących wierszy w miejscu, dopisanie progu
        self.assertEqual(meta({"id": "projekt-testowy", "phase": "marketing", "client": True, "threshold": "pełna"})[0],
                         200)
        text = read(karta)
        self.assertEqual((text.count("- faza:"), text.count("- klient:"), text.count("- próg:")), (1, 1, 1))
        self.assertIn("- faza: marketing\n- klient: tak\n- próg: pełna\n", text)
        self.assertFalse([f for f in os.listdir(self.folder) if f.startswith(".tmp")])

    def test_meta_karta_bez_pol(self):
        karta = os.path.join(self.folder, "KARTA.md")
        write(karta, "<!-- komentarz -->\n# Karta projektu: X\n\n## Cel\nCoś.\n")
        self.assertEqual(self.post("/api/project/meta", {"id": "projekt-testowy", "threshold": "lekka"})[0], 200)
        self.assertEqual(read(karta), "<!-- komentarz -->\n# Karta projektu: X\n\n- próg: lekka\n\n## Cel\nCoś.\n")

    def test_meta_odmowy(self):
        meta = lambda body: self.post("/api/project/meta", body)
        karta = os.path.join(self.folder, "KARTA.md")
        before = read(karta)
        self.assertEqual(meta({"phase": "budowa"})[0], 404)
        self.assertEqual(meta({"id": "nie-ma", "phase": "budowa"})[0], 404)
        self.assertEqual(meta({"id": "projekt-testowy"})[0], 400)
        self.assertEqual(meta({"id": "projekt-testowy", "phase": "gotowe"})[0], 400)
        self.assertEqual(meta({"id": "projekt-testowy", "client": "tak"})[0], 400)
        self.assertEqual(meta({"id": "projekt-testowy", "threshold": "średnia"})[0], 400)
        self.assertEqual(meta({"id": "projekt-testowy", "phase": "budowa", "inne": 1})[0], 200)  # obce pola pomijane
        write(karta, before)
        self.assertEqual(self.request("POST", "/api/project/meta", raw=b"x", ctype="text/plain")[0], 400)
        self.assertEqual(self.request("POST", "/api/project/meta", body={"id": "projekt-testowy", "phase": "budowa"},
                                      headers={"Origin": "http://obca.strona"})[0], 403)
        os.remove(karta)
        self.assertEqual(meta({"id": "projekt-testowy", "phase": "budowa"})[0], 400)
        self.assertFalse(os.path.exists(karta))
        write(karta, before)


class Zbieracz(Serwer):
    registered = False

    def setUp(self):
        super().setUp()
        self.other = os.path.join(self.tmp, "ze-zbieracza")
        os.makedirs(self.other)                                              # folder bez plików standardu

    def test_bez_plikow_zbieracza(self):
        self.assertEqual(projekt.collector_projects(), [])
        data = self.data()
        self.assertEqual(data["projectsSource"], "sample")
        self.assertEqual(data["history"][-1]["date"], datetime.date.today().isoformat())
        self.assertEqual(len(data["history"]), 57)
        self.assertFalse(os.path.exists(self.history_dir))                  # przykłady nie zapisują historii

    def test_projekty_ze_zbieracza(self):
        self.collector({
            self.folder: [{"stan": "backlog"}, {"stan": "w realizacji", "klient": False, "alias": "K-0000"}],
            self.other: {"stan": "backlog", "alias": "K-0001"},
            os.path.join(self.tmp, "wykluczony"): {"stan": "wykluczony"},
            os.path.join(self.tmp, "nie-ma"): {"stan": "w realizacji"},
        })
        os.makedirs(os.path.join(self.tmp, "wykluczony"))
        data = self.data()
        self.assertEqual(data["projectsSource"], "registry")
        projects = {p["id"]: p for p in data["projects"]}
        self.assertEqual(sorted(projects), ["projekt-testowy", "ze-zbieracza"])
        p = projects["projekt-testowy"]
        self.assertEqual((p["origin"], p["alias"], p["client"], p["state"]), ("collector", "K-0000", False, "active"))
        q = projects["ze-zbieracza"]
        self.assertEqual((q["state"], q["phase"], q["alias"], q["bookOk"]), ("backlog", "pomysl", "K-0001", 0))
        self.assertTrue(all(d["status"] == "missing" for d in q["book"]))
        self.assertEqual(os.listdir(self.other), [])                         # nic nie zakładamy
        self.assertEqual(set(data["history"][-1]["projects"]), {"projekt-testowy", "ze-zbieracza"})
        # meta działa dla projektu ze zbieracza; usuwanie z rejestru nie
        self.assertEqual(self.post("/api/project/meta", {"id": "projekt-testowy", "phase": "budowa"})[0], 200)
        self.assertEqual(self.post("/api/project/meta", {"id": "ze-zbieracza", "phase": "budowa"})[0], 400)
        self.assertEqual(self.post("/api/project/remove", {"id": "projekt-testowy"})[0], 409)

    def test_bez_duplikatow_z_rejestrem(self):
        quiet(projekt.cmd_dodaj, self.folder)
        link = os.path.join(self.tmp, "dowiazanie")
        os.symlink(self.folder, link)
        self.collector({link: {"stan": "w przygotowaniu", "alias": "K-0000"}})
        folders = projekt.all_folders()
        self.assertEqual(len(folders), 1)
        self.assertEqual(folders[0][:2], (self.folder, "registry"))
        data = self.data()
        self.assertEqual([(p["id"], p["origin"], p["alias"]) for p in data["projects"]],
                         [("projekt-testowy", "registry", "K-0000")])

    def test_uszkodzone_pliki_zbieracza(self):
        os.makedirs(os.path.join(self.stan, "mac"))
        os.makedirs(self.lokalne)
        write(os.path.join(self.lokalne, "aliasy.json"), json.dumps({"a": {"sciezka": self.other}, "b": "x"}))
        write(os.path.join(self.stan, "mac", "decyzje.jsonl"),
              'nie json\n[1]\n{"tozsamosc": "a", "stan": "w realizacji"}\n{"tozsamosc": "b", "stan": "backlog"}\n')
        self.assertEqual(projekt.collector_projects(), [(self.other, {"tozsamosc": "a", "stan": "w realizacji"})])
        write(os.path.join(self.lokalne, "aliasy.json"), "[]")
        self.assertEqual(projekt.collector_projects(), [])


class Podglad(Serwer):
    def test_podglad_ma_historie_i_pola(self):
        preview = server.preview_data()
        self.assertEqual(preview["history"][-1]["date"], "+0")
        self.assertEqual(preview["history"][0]["date"], "-56")
        phases = {p["id"]: (p["phase"], p["phaseSource"], p["client"], p["threshold"]) for p in preview["projects"]}
        self.assertEqual(phases, {"apka-ios": ("budowa", "karta", True, "lekka"),
                                  "landing": ("marketing", "wyliczona", False, "lekka"),
                                  "sklep-api": ("wdrozenie", "karta", True, "pelna")})
        status, _, page = self.request("GET", "/podglad")
        self.assertEqual(status, 200)
        self.assertNotIn(self.tmp, page)


if __name__ == "__main__":
    unittest.main()
