"""Szczegóły zadania (wcięte wiersze pod zadaniem), następny krok projektu, /api/plik, /api/task/detail,
ciasteczko Secure, prompt agenta, powiadomienia i ryzyka raportu PM."""
import datetime
import json
import os
import sys
import time
import unittest

from test_serwer import REMOTE, Serwer
from wspolne import TODAY, TOMORROW, Baza, agents, projekt, server

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "standard"))
import pm  # noqa: E402

DAY = datetime.date.today()


def day(n):
    return (DAY + datetime.timedelta(days=n)).isoformat()


ZADANIA = """# Zadania: Projekt testowy

## Etap: Kontakty
termin: %(t5)s

- [ ] Wyślij zaproszenia LinkedIn do 8 firm z partii 1 | kto: ty | kiedy: %(t1)s | czas: 20 | wymaga: odbiór, zgoda
  cel: 8 zaproszeń do osób decyzyjnych w firmach z partii 1
  gotowe gdy: w tabeli z punktu 8 planu wpisane „Zaproszenia wysłane: 8”
  materiał: marketing/plan.md#5
  materiał: marketing/plan.md#Partia 1
  - [ ] Kedameble
  - [x] Bambooko
  zapytać o osobę od zakupów
- [ ] Przygotuj listę firm z partii 2 | kto: claude | kiedy: %(t3)s
  cel: lista 10 firm
- [x] Wdrożenie formularza
- [ ] Opracowanie raportu kwartalnego | kto: codex

## Etap: Bez terminu

- [ ] Sprawdź ofertę | kto: claude

## Do rozplanowania
- [ ] Pomysł na później
  - [ ] krok pomysłu
""" % {"t1": day(1), "t3": day(3), "t5": day(5)}

PLAN = """# Plan 10 kont

Wstęp.

## 4. Kanały

Tekst czwartej sekcji.

## 5. Zaproszenia

Wyślij zaproszenia.

### 5.1 Szczegóły

Podsekcja.

## Partia 1

Kedameble, Bambooko.
"""


class Wspolne(Baza):
    def setUp(self):
        super().setUp()
        self.write("ZADANIA.md", ZADANIA)

    def write(self, rel, text):
        path = os.path.join(self.folder, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    def text(self, rel="ZADANIA.md"):
        with open(os.path.join(self.folder, rel), encoding="utf-8") as f:
            return f.read()

    def read(self):
        return projekt.read_project(self.folder, "projekt-testowy")

    def get(self, title):
        return next(t for t in self.read()["tasks"] if t["title"] == title)


class Parser(Wspolne):
    def test_szczegoly_i_kroki_nie_sa_zadaniami(self):
        tasks = self.read()["tasks"]
        titles = [t["title"] for t in tasks]
        self.assertEqual(titles, ["Wyślij zaproszenia LinkedIn do 8 firm z partii 1", "Przygotuj listę firm z partii 2",
                                  "Wdrożenie formularza", "Opracowanie raportu kwartalnego", "Sprawdź ofertę",
                                  "Pomysł na później"])
        for step in ("Kedameble", "Bambooko", "krok pomysłu"):
            self.assertNotIn(step, titles)
        d = tasks[0]["detail"]
        self.assertEqual(d["goal"], "8 zaproszeń do osób decyzyjnych w firmach z partii 1")
        self.assertEqual(d["doneWhen"], "w tabeli z punktu 8 planu wpisane „Zaproszenia wysłane: 8”")
        self.assertEqual(d["refs"], [{"path": "marketing/plan.md", "anchor": "5"},
                                     {"path": "marketing/plan.md", "anchor": "Partia 1"}])
        self.assertEqual(d["steps"], [{"done": False, "text": "Kedameble"}, {"done": True, "text": "Bambooko"}])
        self.assertEqual(d["notes"], ["zapytać o osobę od zakupów"])
        self.assertEqual((d["result"], d["decision"], d["left"]), ("", "", ""))
        self.assertEqual(tasks[1]["detail"]["goal"], "lista 10 firm")
        self.assertEqual(tasks[2]["detail"], projekt.blank_detail())
        self.assertEqual(tasks[5]["detail"]["steps"], [{"done": False, "text": "krok pomysłu"}])

    def test_kilka_wartosci_wymaga(self):
        t = self.get("Wyślij zaproszenia LinkedIn do 8 firm z partii 1")
        self.assertEqual((t["needsYou"], t["needs"]), ("odbiór", ["odbiór", "zgoda"]))
        self.assertEqual(self.get("Sprawdź ofertę")["needs"], [])
        self.assertEqual(agents.run_block(t, "registry", {}, {"claude": True}), "Zadanie po Twojej stronie")
        t = dict(t, executor="claude")
        self.assertEqual(agents.run_block(t, "registry", {}, {"claude": True}), "Czeka na Twoją zgodę")
        bad = projekt.parse_task("- [ ] X | wymaga: odbiór, coś")
        self.assertEqual((bad["needs"], len(bad["errors"])), (["odbiór"], 1))

    def test_kampania_ze_szczegolami(self):
        self.write("kampanie/jesien.md", "# Kampania: Jesień\n\n- stan: w toku\n- cel: x\n- kanały: LinkedIn\n"
                   "- start: %s\n- koniec: %s\n\n## Grupa docelowa\nfirmy\n\n## Przekaz\nkrótko\n\n## Harmonogram\n"
                   "- [ ] Wpis o ofercie | kanał: LinkedIn | kiedy: %s | wymaga: zgoda\n  cel: 3 komentarze\n"
                   "  - [ ] grafika\n- [ ] Drugi wpis | kanał: LinkedIn\n\n## Wyniki i wnioski\n" % (TODAY, TOMORROW, TOMORROW))
        pubs = [t for t in self.read()["tasks"] if t["kind"] == "publikacja"]
        self.assertEqual([p["title"] for p in pubs], ["Wpis o ofercie", "Drugi wpis"])
        self.assertEqual(pubs[0]["detail"]["goal"], "3 komentarze")
        self.assertEqual(pubs[0]["detail"]["steps"], [{"done": False, "text": "grafika"}])

    def test_braki_w_ksiedze(self):
        long = "Napisz " + "bardzo " * 20 + "długi tytuł"
        self.write("ZADANIA.md", ZADANIA.replace("- [ ] Sprawdź ofertę | kto: claude",
                                                 "- [ ] Sprawdź ofertę | kto: claude\n- [ ] %s" % long))
        doc = next(d for d in self.read()["project"]["book"] if d["key"] == "zadania")
        self.assertEqual(doc["status"], "gaps")
        gaps = " | ".join(doc["gaps"])
        # bez „gotowe gdy”: tylko otwarte zadania w etapie z terminem
        self.assertIn("zadania bez „gotowe gdy” w etapie z terminem: 2 („Przygotuj listę firm z partii 2”, "
                      "„Opracowanie raportu kwartalnego”)", gaps)
        self.assertIn("tytuł dłuższy niż 120 znaków: 1", gaps)
        self.assertIn("tytuł nie zaczyna się od czasownika: 1 („Opracowanie raportu kwartalnego”)", gaps)
        self.assertNotIn("Wdrożenie formularza", gaps)                          # zrobione nie są brakiem
        many = "\n".join("- [ ] Zrób rzecz %d" % i for i in range(8))
        self.write("ZADANIA.md", "## Etap: A\ntermin: %s\n\n%s\n" % (TOMORROW, many))
        doc = next(d for d in self.read()["project"]["book"] if d["key"] == "zadania")
        self.assertEqual(doc["gaps"], ["zadania bez „gotowe gdy” w etapie z terminem: 8 („Zrób rzecz 0”, „Zrób rzecz 1”, "
                                       "„Zrób rzecz 2”, „Zrób rzecz 3”, „Zrób rzecz 4” i 3 inne)"])


class Zapis(Wspolne):
    def test_dodawanie_po_szczegolach(self):
        stage = self.read()["stages"][0]
        projekt.add_task(self.folder, "Nowe w etapie", "ZADANIA.md", stage["line"])
        projekt.add_task(self.folder, "Nowe w skrzynce")
        lines = self.text().split("\n")
        i = lines.index("- [ ] Nowe w etapie")
        self.assertEqual(lines[i - 1], "- [ ] Opracowanie raportu kwartalnego | kto: codex")
        self.assertEqual(lines[-3:], ["  - [ ] krok pomysłu", "- [ ] Nowe w skrzynce", ""])
        titles = [t["title"] for t in self.read()["tasks"]]
        self.assertIn("Nowe w etapie", titles)
        self.assertEqual(self.get("Pomysł na później")["detail"]["steps"], [{"done": False, "text": "krok pomysłu"}])
        # zadanie dopisane pod szczegółami ostatniego zadania nie przejmuje ich
        self.write("ZADANIA.md", "## Etap: A\ntermin: %s\n\n- [ ] Pierwsze\n  cel: c\n  - [ ] krok\n\n## Do rozplanowania\n"
                   % TOMORROW)
        projekt.add_task(self.folder, "Drugie", "ZADANIA.md", 1)
        self.assertIn("  - [ ] krok\n- [ ] Drugie\n", self.text())
        self.assertEqual(self.get("Drugie")["detail"], projekt.blank_detail())
        self.assertEqual(self.get("Pierwsze")["detail"]["goal"], "c")

    def test_zmiana_wiersza_zostawia_szczegoly(self):
        t = self.get("Wyślij zaproszenia LinkedIn do 8 firm z partii 1")
        self.assertTrue(projekt.update_task(self.folder, "ZADANIA.md", t["line"], t["title"], {"minutes": 30}))
        self.assertIn("czas: 30 | wymaga: odbiór, zgoda\n  cel: 8 zaproszeń", self.text())
        self.assertTrue(projekt.update_task(self.folder, "ZADANIA.md", t["line"], t["title"], {"needsYou": "zgoda"}))
        self.assertEqual(self.get(t["title"])["needs"], ["zgoda"])
        self.assertTrue(projekt.update_task(self.folder, "ZADANIA.md", t["line"], t["title"],
                                            {"needs": ["odbiór", "zgoda"]}))
        self.assertIn("wymaga: odbiór, zgoda", self.text())
        self.assertTrue(projekt.update_task(self.folder, "ZADANIA.md", t["line"], t["title"], {"needsYou": ""}))
        self.assertNotIn("wymaga:", self.text().split("\n")[t["line"] - 1])
        with self.assertRaises(ValueError):
            projekt.update_task(self.folder, "ZADANIA.md", t["line"], t["title"], {"needs": ["inne"]})
        self.assertTrue(projekt.set_state(self.folder, "ZADANIA.md", t["line"], t["title"], "done"))
        self.assertEqual(self.get(t["title"])["detail"]["steps"][1], {"done": True, "text": "Bambooko"})

    def test_set_detail(self):
        t = self.get("Przygotuj listę firm z partii 2")
        put = lambda key, value: projekt.set_detail(self.folder, "ZADANIA.md", t["line"], t["title"], key, value)
        self.assertTrue(put("wynik", "lista w marketing/partia-2.md"))
        self.assertTrue(put("gotowe gdy", "10 firm w tabeli"))
        self.assertTrue(put("zostało", "2 firmy bez kontaktu"))
        self.assertTrue(put("decyzja", "zatwierdź listę"))
        self.assertTrue(put("materiał", "marketing/plan.md#5\nmarketing/lista.md"))
        block = self.text().split("- [ ] Przygotuj listę firm z partii 2 | kto: claude | kiedy: %s\n" % day(3))[1]
        self.assertTrue(block.startswith("  cel: lista 10 firm\n  gotowe gdy: 10 firm w tabeli\n"
                                         "  materiał: marketing/plan.md#5\n  materiał: marketing/lista.md\n"
                                         "  wynik: lista w marketing/partia-2.md\n  decyzja: zatwierdź listę\n"
                                         "  zostało: 2 firmy bez kontaktu\n- [x] Wdrożenie formularza"), block)
        self.assertTrue(put("wynik", "nowy | wynik"))                          # zamiana, bez znaku „|”
        self.assertTrue(put("zostało", ""))                                    # pusta wartość usuwa wiersz
        d = self.get(t["title"])["detail"]
        self.assertEqual((d["result"], d["left"], d["decision"]), ("nowy / wynik", "", "zatwierdź listę"))
        self.assertEqual(len(d["refs"]), 2)
        self.assertEqual(self.get(t["title"])["line"], t["line"])             # tytuł i wiersz bez zmian
        self.assertFalse(projekt.set_detail(self.folder, "ZADANIA.md", t["line"], "Inny tytuł", "wynik", "x"))
        with self.assertRaises(ValueError):
            put("tytuł", "x")
        # pod zadaniem bez szczegółów: pierwszy wcięty wiersz
        t = self.get("Sprawdź ofertę")
        self.assertTrue(projekt.set_detail(self.folder, "ZADANIA.md", t["line"], t["title"], "cel", "oferta X"))
        self.assertIn("- [ ] Sprawdź ofertę | kto: claude\n  cel: oferta X\n", self.text())


class NastepnyKrok(Wspolne):
    def test_najwczesniejsza_data_potem_kto(self):
        step = self.read()["project"]["nextStep"]
        self.assertEqual(step, {"title": "Wyślij zaproszenia LinkedIn do 8 firm z partii 1",
                                "taskId": "projekt-testowy|ZADANIA.md|6", "executor": "ty", "date": day(1)})
        self.write("ZADANIA.md", "## Etap: A\n\n- [ ] Bez kto\n- [x] Zrobione | kto: ty\n- [ ] Z kto | kto: codex\n")
        self.assertEqual(self.read()["project"]["nextStep"]["title"], "Z kto")
        self.write("ZADANIA.md", "## Etap: A\n\n- [ ] Bez kto\n")
        self.assertIsNone(self.read()["project"]["nextStep"])
        self.write("ZADANIA.md", "## Etap: A\n\n- [ ] Później | kiedy: +5\n- [ ] Wcześniej | kiedy: +2\n")
        self.assertEqual(self.read()["project"]["nextStep"]["title"], "Wcześniej")


class Agent(Wspolne):
    def test_prompt_ze_szczegolami_i_bez_zmiany_tytulu(self):
        t = self.get("Przygotuj listę firm z partii 2")
        projekt.set_detail(self.folder, "ZADANIA.md", t["line"], t["title"], "materiał", "marketing/plan.md#5")
        rec = self.wait(self.run_task("Przygotuj listę firm z partii 2")[2]["id"])
        self.assertEqual(rec["state"], "done")
        prompt = self.calls()[-1]["prompt"]
        for part in ("„Przygotuj listę firm z partii 2”", "Cel: lista 10 firm", "- marketing/plan.md#5",
                     "Nigdy nie zmieniaj tytułu zadania", "`  wynik: …`", "`  decyzja: …`", "`  zostało: …`",
                     "„## Pytania do właściciela”", "nie dopisuj do niego raportu"):
            self.assertIn(part, prompt)
        after = self.get("Przygotuj listę firm z partii 2")                    # tytuł i szczegóły zostają
        self.assertEqual((after["state"], after["detail"]["goal"]), ("done", "lista 10 firm"))

    def test_prompt_kroki_i_poprzedni_wynik(self):
        m = self.manager
        detail = dict(projekt.blank_detail(), goal="g", doneWhen="w", steps=[{"done": True, "text": "a"},
                                                                            {"done": False, "text": "b"}],
                      result="pierwsza wersja", left="testy")
        p = m.task_prompt("codex", "P", "ZADANIA.md", 4, "Tytuł", "", detail)
        self.assertIn("Gotowe gdy: w", p)
        self.assertIn("- [x] a\n- [ ] b", p)
        self.assertIn("Wynik poprzedniej pracy: pierwsza wersja", p)
        self.assertIn("Zostało z poprzedniej pracy: testy", p)
        self.assertIn("AGENTS.md", p)
        self.assertNotIn("Szczegóły zadania", m.task_prompt("claude", "P", "ZADANIA.md", 4, "Tytuł", "", None))

    def test_plan_cel_czas_i_publikacje_do_zgody(self):
        self.write("kampanie/jesien.md", "# Kampania: Jesień\n\n- stan: w toku\n\n## Harmonogram\n"
                   "- [ ] Wpis do zgody | kanał: LinkedIn | kiedy: %s | wymaga: zgoda | czas: 10\n"
                   "- [ ] Wpis bez zgody | kanał: LinkedIn\n" % TOMORROW)
        cands = {c["title"]: c for c in self.manager.plan_candidates()}
        self.assertEqual((cands["Przygotuj listę firm z partii 2"]["goal"],
                          cands["Wyślij zaproszenia LinkedIn do 8 firm z partii 1"]["minutes"]), ("lista 10 firm", 20))
        pub = cands["Wpis do zgody"]
        self.assertEqual((pub["kind"], pub["agent"], pub["minutes"], pub["stage"]), ("publikacja", False, 10, "Jesień"))
        self.assertNotIn("Wpis bez zgody", cands)
        prompt = self.manager.plan_prompt("dziś", list(cands.values()), TODAY)
        row = next(json.loads(l) for l in prompt.split("\n") if l.startswith("["))
        self.assertEqual(set(row[0]), {"id", "project", "kind", "title", "goal", "minutes", "stage", "stageDue", "date",
                                       "executor", "state", "needsYou", "agent"})

    def test_powiadomienie_o_logowaniu_raz_na_zmiane(self):
        sent = []
        m = self.new_manager(PANEL_NTFY_URL="http://127.0.0.1:9/nieuzywany")
        m._send_ntfy = sent.append
        m._login_alert()
        self.assertEqual(sent, [])
        m._state["needsLogin"] = True
        m._login_alert()
        m._login_alert()
        self.assertEqual(sent, ["Claude wymaga logowania. Zaloguj się w panelu: Agenci, Zaloguj."])
        m._state["needsLogin"] = False
        m._tools, m._tools_at = {"claude": {"found": True, "loggedIn": True}}, time.time()
        m._login_alert()
        m._tools["claude"]["loggedIn"] = False                                  # odczyt narzędzi: wylogowany
        m._login_alert()
        self.assertEqual(len(sent), 2)
        # zakończenie uruchomienia z błędem logowania: jedno powiadomienie o logowaniu i jedno o zadaniu
        sent.clear()
        m._tools, m._login_sent = {"claude": {"found": True, "loggedIn": True}}, False
        m.refresh_tools = lambda force=False, wait=False: None
        self.set_mode("login")
        self.wait(self.run_task("Przygotuj listę firm z partii 2", m)[2]["id"], manager=m)
        self.assertEqual(sent, ["Zadanie w projekcie Projekt testowy: wymaga logowania",
                                "Claude wymaga logowania. Zaloguj się w panelu: Agenci, Zaloguj."])


class Api(Serwer):
    def setUp(self):
        super().setUp()
        with open(os.path.join(self.folder, "ZADANIA.md"), "w", encoding="utf-8") as f:
            f.write(ZADANIA)
        os.makedirs(os.path.join(self.folder, "marketing"))
        with open(os.path.join(self.folder, "marketing", "plan.md"), "w", encoding="utf-8") as f:
            f.write(PLAN)

    def plik(self, path, anchor=None, project="projekt-testowy", headers=None):
        from urllib.parse import urlencode
        q = {"project": project, "path": path}
        if anchor is not None:
            q["anchor"] = anchor
        status, _, text = self.request("GET", "/api/plik?" + urlencode(q), headers=headers)
        return status, json.loads(text) if text.startswith("{") else text

    def test_dane_zadan_i_projektow(self):
        data = self.data()
        t = next(x for x in data["tasks"] if x["title"].startswith("Wyślij zaproszenia"))
        self.assertEqual(set(t["detail"]), {"goal", "doneWhen", "refs", "steps", "result", "decision", "left", "notes"})
        self.assertEqual((t["needsYou"], t["needs"]), ("odbiór", ["odbiór", "zgoda"]))
        self.assertTrue(all("detail" in x and "needs" in x for x in data["tasks"]))
        p = data["projects"][0]
        self.assertEqual(p["nextStep"]["taskId"], t["id"])
        self.assertEqual(p["nextStep"]["date"], day(1))
        preview = server.preview_data()
        self.assertTrue(all("nextStep" in x for x in preview["projects"]))

    def test_plik_i_sekcje(self):
        status, answer = self.plik("marketing/plan.md")
        self.assertEqual(status, 200)
        self.assertEqual((answer["ok"], answer["path"], answer["title"]), (True, "marketing/plan.md", "Plan 10 kont"))
        self.assertEqual(answer["text"], PLAN)
        status, answer = self.plik("marketing/plan.md", "5")
        self.assertEqual((status, answer["title"]), (200, "5. Zaproszenia"))
        self.assertTrue(answer["text"].startswith("## 5. Zaproszenia"))
        self.assertIn("### 5.1 Szczegóły", answer["text"])                      # podsekcja należy do sekcji
        self.assertNotIn("Partia 1", answer["text"])
        self.assertEqual(self.plik("marketing/plan.md", "5.")[1]["title"], "5. Zaproszenia")
        self.assertEqual(self.plik("marketing/plan.md", "partia 1")[1]["text"], "## Partia 1\n\nKedameble, Bambooko.")
        self.assertEqual(self.plik("marketing/plan.md", "partia-1")[1]["title"], "Partia 1")
        self.assertEqual(self.plik("marketing/plan.md", "5.1")[1]["title"], "5.1 Szczegóły")
        self.assertEqual(self.plik("marketing/plan.md", "9"), (404, {"ok": False, "error": "Nie ma takiej sekcji w pliku."}))

    def test_plik_odmowy(self):
        outside = os.path.join(self.tmp, "poza.md")
        with open(outside, "w", encoding="utf-8") as f:
            f.write("# tajne\n")
        with open(os.path.join(self.folder, "dane.json"), "w", encoding="utf-8") as f:
            f.write("{}")
        with open(os.path.join(self.folder, "duzy.md"), "w", encoding="utf-8") as f:
            f.write("x" * (server.FILE_MAX + 1))
        os.symlink(outside, os.path.join(self.folder, "dowiazanie.md"))
        for path in ("../poza.md", outside, "marketing/../../poza.md", "dowiazanie.md", "~/poza.md", "dane.json",
                     "duzy.md", "nie-ma.md", "marketing", ""):
            status, answer = self.plik(path)
            self.assertEqual((status, answer["ok"]), (404, False), path)
            self.assertNotIn("tajne", json.dumps(answer))
        self.assertEqual(self.plik("marketing/plan.md", project="nie-ma")[0], 404)
        server.TOKEN = "haslo-do-testow"
        self.assertEqual(self.plik("marketing/plan.md", headers=REMOTE),
                         (401, {"ok": False, "error": "Wymagane hasło."}))

    def test_plik_z_folderu_karty(self):
        cards = os.path.join(self.tmp, "karty", "projekt")
        os.makedirs(os.path.join(cards, "notatki"))
        os.replace(os.path.join(self.folder, "KARTA.md"), os.path.join(cards, "KARTA.md"))
        os.symlink(os.path.join(cards, "KARTA.md"), os.path.join(self.folder, "KARTA.md"))
        with open(os.path.join(cards, "notatki", "brief.txt"), "w", encoding="utf-8") as f:
            f.write("brief klienta\n")
        status, answer = self.plik("notatki/brief.txt")
        self.assertEqual((status, answer["text"], answer["title"]), (200, "brief klienta\n", "brief.txt"))
        self.assertEqual(self.plik("../projekt/KARTA.md")[0], 200)              # karta jest w dozwolonym folderze
        self.assertEqual(self.plik("../../poza.md")[0], 404)

    def test_zapis_szczegolow(self):
        t = next(x for x in self.data()["tasks"] if x["title"] == "Sprawdź ofertę")
        ok = self.post("/api/task/detail", {"id": t["id"], "title": t["title"], "key": "wynik", "value": "gotowe"})
        self.assertEqual(ok, (200, {"ok": True, "error": ""}))
        t = next(x for x in self.data()["tasks"] if x["title"] == "Sprawdź ofertę")
        self.assertEqual(t["detail"]["result"], "gotowe")
        self.assertEqual(self.post("/api/task/detail", {"id": t["id"], "title": t["title"], "key": "kto",
                                                        "value": "x"})[0], 400)
        self.assertEqual(self.post("/api/task/detail", {"id": t["id"], "title": "Inny", "key": "cel",
                                                        "value": "x"})[0], 409)
        self.assertEqual(self.post("/api/task/detail", {"id": "nie-ma|ZADANIA.md|3", "title": "x", "key": "cel",
                                                        "value": "x"})[0], 404)
        self.assertEqual(self.post("/api/task/detail", {"id": t["id"], "title": t["title"], "key": "cel",
                                                        "value": 5})[0], 400)


class Ciasteczko(Serwer):
    def test_secure_przez_https(self):
        server.TOKEN = "haslo-do-testow"
        _, headers, _ = self.login("haslo-do-testow")
        self.assertNotIn("Secure", headers["Set-Cookie"])
        from urllib.parse import urlencode
        status, headers, _ = self.request("POST", "/wejscie", raw=urlencode({"haslo": "haslo-do-testow"}).encode(),
                                          ctype="application/x-www-form-urlencoded",
                                          headers=dict(REMOTE, **{"X-Forwarded-Proto": "https"}))
        self.assertEqual(status, 303)
        self.assertTrue(headers["Set-Cookie"].endswith("; Secure"))
        for part in ("HttpOnly", "SameSite=Strict", "Path=/"):
            self.assertIn(part, headers["Set-Cookie"])


class RaportPM(Wspolne):
    def facts(self):
        return pm.facts(DAY)

    def test_ryzyka_i_decyzje(self):
        f = self.facts()
        self.assertEqual(f["source"], "registry")
        # etap „Bez terminu” ma otwarte zadanie: ryzyko w aktywnym projekcie
        self.assertEqual([(s["title"], s["done"], s["total"]) for s in f["stagesNoDate"]], [("Bez terminu", 0, 1)])
        self.assertEqual(f["noNextStep"], [])                                   # zadanie z datą jutro
        self.assertEqual((f["counts"]["noNextStep"], f["counts"]["stagesNoDate"]), (0, 1))
        top = f["top"]
        self.assertEqual([t["title"] for t in top], ["Wyślij zaproszenia LinkedIn do 8 firm z partii 1"])
        self.assertEqual((top[0]["minutes"], f["topMinutes"]), (20, 20))
        text = pm.text(f)
        self.assertIn("Najważniejsze 1 (20 min):", text)
        self.assertIn("(jutro, 20 min)", text)
        self.assertIn("□ etap bez terminu: Projekt testowy · etap Bez terminu (0/1)", text)

    def test_bez_nastepnego_kroku(self):
        self.write("ZADANIA.md", "## Etap: A\ntermin: %s\n\n- [ ] Za dwa tygodnie | kiedy: %s\n- [ ] Bez daty | kto: ty\n"
                   % (day(30), day(14)))
        f = self.facts()
        self.assertEqual([p["project"] for p in f["noNextStep"]], ["Projekt testowy"])
        self.assertEqual(f["noNextStep"][0]["nextStep"]["title"], "Za dwa tygodnie")
        self.assertIn("□ bez następnego kroku: Projekt testowy", pm.text(f))
        card = self.text("KARTA.md")
        self.assertIn("- stan: aktywny", card)
        self.write("KARTA.md", card.replace("- stan: aktywny", "- stan: wstrzymany"))
        f = self.facts()
        self.assertEqual((f["noNextStep"], f["stagesNoDate"]), ([], []))         # wstrzymany projekt bez tych ryzyk

    def test_trzy_najwazniejsze(self):
        rows = "\n".join([
            "- [ ] Odbiór później | wymaga: odbiór | kiedy: %s | czas: 15" % day(3),
            "- [ ] Zgoda jutro | wymaga: zgoda | kiedy: %s | czas: 5" % day(1),
            "- [ ] Po terminie | kto: ty | kiedy: %s | czas: 40" % day(-2),
            "- [ ] Odbiór jutro | wymaga: odbiór | kiedy: %s" % day(1),
            "- [ ] Zgoda bez daty | wymaga: zgoda | czas: 10"])
        self.write("ZADANIA.md", "## Etap: A\ntermin: %s\n\n%s\n" % (day(10), rows))
        f = self.facts()
        self.assertEqual([t["title"] for t in f["top"]], ["Po terminie", "Zgoda jutro", "Odbiór jutro"])
        self.assertEqual(f["topMinutes"], 45)
        self.assertEqual(len(f["decisions"]), 5)
        text = pm.text(f)
        self.assertIn("Najważniejsze 3 (45 min; bez czasu: 1):", text)
        self.assertIn("Pozostałe:", text)
        self.assertLess(text.index("Po terminie"), text.index("Odbiór później"))


if __name__ == "__main__":
    unittest.main()
