"""Asystent: fakty dla modelu (Twoje sprawy, po terminie, postęp) bez czytania plików, stała sesja stream-json
(atrapa CLI), odpowiedź w trakcie pisania, wznowienie po restarcie, działania sterujące panelem (asActs w panel.html)."""
import datetime
import json
import os
import re
import sys
import time
import unittest

from wspolne import Baza
from test_blokady import JS, PANEL, run_js

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import agents  # noqa: E402


class Fakty(unittest.TestCase):
    def test_fakty(self):
        today = datetime.date(2026, 11, 22)
        data = {"projects": [{"id": "a", "name": "Alfa", "state": "active"}, {"id": "b", "name": "Beta", "state": "paused"}],
                "tasks": [
                    {"project": "a", "title": "Nagraj film", "executor": "ty", "state": "todo", "date": "2026-11-23", "kind": "zadanie"},
                    {"project": "a", "title": "Stare", "executor": "claude", "state": "todo", "date": "2026-11-20", "kind": "zadanie"},
                    {"project": "a", "title": "Zrobione", "executor": "ty", "state": "done", "date": "2026-11-21", "kind": "zadanie"},
                    {"project": "a", "title": "Daleko", "executor": "ty", "state": "todo", "date": "2027-01-10", "kind": "zadanie"},
                    {"project": "b", "title": "Wstrzymany", "executor": "ty", "state": "todo", "date": "2026-11-23", "kind": "zadanie"}]}
        f = agents.Manager.assistant_facts(data, today)
        self.assertIn("Alfa: 25% (1 z 4 zadań)", f)
        self.assertIn("Alfa | Nagraj film | 2026-11-23", f)
        self.assertIn("Alfa | Stare | 2026-11-20", f.split("Po terminie (")[1])
        # liczby z projekt.owner_counts (jedno źródło z panelem i pm.py), z podpisami
        self.assertIn("- sprawy dla Ciebie na dziś: 0, w tym po terminie: 0", f)
        self.assertIn("- sprawy dla Ciebie w ciągu 7 dni: 1, później: 1", f)
        self.assertIn("- wszystkie zadania po terminie (także agentów): 1", f)
        given = {"youToday": 37, "youLate": 30, "youWeek": 4, "youLater": 3, "late": 32}
        self.assertIn("na dziś: 37, w tym po terminie: 30", agents.Manager.assistant_facts(data, today, given))
        self.assertNotIn("Daleko", f)
        self.assertNotIn("Wstrzymany", f)

    def test_id_i_publikacje(self):
        today = datetime.date(2026, 11, 22)
        data = {"projects": [{"id": "a", "name": "Alfa", "state": "active"}],
                "tasks": [{"id": "a|ZADANIA.md|5", "project": "a", "title": "Zatwierdź", "executor": "claude",
                           "needsYou": "zgoda", "state": "todo", "date": "2026-11-23", "kind": "zadanie"},
                          {"id": "a|kampanie/k.md|9", "project": "a", "title": "Opublikuj film", "executor": "ty",
                           "state": "todo", "date": "2026-11-24", "kind": "publikacja"}]}
        f = agents.Manager.assistant_facts(data, today)
        self.assertIn("Alfa | Zatwierdź | 2026-11-23 | czeka na: zgoda | id: a|ZADANIA.md|5", f)
        pubs = f.split("Publikacje do")[1].split("Po terminie (")[0]
        self.assertIn("Opublikuj film | 2026-11-24 | id: a|kampanie/k.md|9", pubs)
        self.assertNotIn("Opublikuj film", f.split("Publikacje do")[0])


class StalaSesja(Baza):
    """Jeden proces claude na wiele wiadomości (atrapa w trybie stream-json)."""

    def ask(self, text, view="#start", opened="", manager=None):
        m = manager or self.manager
        self.assertEqual(m.assistant_send(text, view, opened), (202, "", {"pending": True}))
        self.wait_for(lambda: not m.assistant_get()[2]["pending"], timeout=15)
        return m.assistant_get()[2]

    def streams(self):
        return [c for c in self.calls() if c.get("stream")]

    def test_jeden_proces_i_krotki_prefiks(self):
        a = self.ask("Co mam dziś zrobić?")
        self.assertEqual(a["error"], "")
        self.assertEqual(a["messages"][-1]["text"], "Odpowiedź atrapy 1: Co mam dziś zrobić?")
        b = self.ask("A jutro?", view="#ty", opened=self.task("Zadanie D")["id"])
        self.assertEqual(b["messages"][-1]["text"], "Odpowiedź atrapy 2: A jutro?")    # ten sam proces
        s = self.streams()
        self.assertEqual(len({c["pid"] for c in s}), 1)
        self.assertIn("Sterowanie panelem", s[0]["prompt"])
        self.assertIn("Otwórz: <id zadania>", s[0]["prompt"])
        self.assertIn("#p-<id>-marketing", s[0]["prompt"])
        self.assertIn("Postęp projektów", s[0]["prompt"])
        self.assertTrue(s[1]["prompt"].startswith("[ekran: #ty; otwarte: zadanie „Zadanie D” (id: "), s[1]["prompt"])
        self.assertNotIn("Postęp projektów", s[1]["prompt"])                          # dane bez zmian
        argv = s[0]["argv"]
        self.assertIn("stream-json", argv)
        self.assertIn("--include-partial-messages", argv)
        self.assertEqual(argv[argv.index("--disallowedTools") + 1], self.manager.ASSIST_DENY)
        # zmiana danych: przy następnej wiadomości świeże fakty
        with open(os.path.join(self.folder, "ZADANIA.md"), "a", encoding="utf-8") as f:
            f.write("- [ ] Nowe moje | kto: ty | kiedy: %s\n" % datetime.date.today().isoformat())
        self.ask("Coś nowego?")
        self.assertIn("Aktualne fakty", self.streams()[2]["prompt"])
        self.assertIn("Nowe moje", self.streams()[2]["prompt"])

    def test_odpowiedz_w_trakcie_pisania(self):
        self.set_mode("czat-wolno")
        self.manager.assistant_send("Użyj narzędzie i opowiedz coś dłuższego", "#start")
        seen, acts = set(), set()
        end = time.time() + 15
        while time.time() < end:
            g = self.manager.assistant_get()[2]
            if g["partial"]:
                seen.add(g["partial"])
            if g["activity"]:
                acts.add(g["activity"])
            if not g["pending"]:
                break
            time.sleep(0.05)
        self.assertGreaterEqual(len(seen), 2, seen)                      # tekst rośnie kawałkami
        self.assertTrue(all(x.startswith("Odpowiedź atrapy") for x in seen), seen)
        self.assertIn("Czytam pliki projektu", acts)
        g = self.manager.assistant_get()[2]
        self.assertEqual((g["partial"], g["activity"]), ("", ""))
        self.assertTrue(g["messages"][-1]["text"].startswith("Odpowiedź atrapy 1"))

    def test_wznowienie_po_restarcie_i_wygasla_sesja(self):
        self.ask("Pierwsza")
        other = self.new_manager()                    # panel uruchomiony ponownie: nowy proces z --resume
        a = self.ask("Druga", manager=other)
        self.assertEqual(a["messages"][-1]["text"], "Odpowiedź atrapy 1: Druga")
        argv = self.streams()[-1]["argv"]
        self.assertEqual(argv[argv.index("--resume") + 1], "strumien-1")
        self.assertIn("Aktualne fakty", self.streams()[-1]["prompt"])    # nowy proces panelu nie zna wysłanych faktów
        # sesja, której CLI już nie zna: nowa rozmowa z pełnym promptem, bez błędu dla właściciela
        path = other._project_chat_file(other.ASSIST)
        with open(path, encoding="utf-8") as f:
            chat = json.load(f)
        chat["session"] = "wygasla"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(chat, f)
        third = self.new_manager()
        b = self.ask("Trzecia", manager=third)
        self.assertEqual(b["error"], "")
        self.assertEqual(b["messages"][-1]["text"], "Odpowiedź atrapy 1: Trzecia")
        self.assertIn("Sterowanie panelem", self.streams()[-1]["prompt"])
        self.assertNotIn("--resume", self.streams()[-1]["argv"])

    def test_logowanie_i_nowa_rozmowa(self):
        self.set_mode("login")
        a = self.ask("Cześć")
        self.assertTrue(a["error"].startswith("Wymaga logowania"), a["error"])
        self.assertFalse(self.manager._as.alive())
        self.set_mode("ok")
        self.ask("Cześć")
        self.assertTrue(self.manager._as.alive())
        self.assertEqual(self.manager.assistant_reset()[0], 200)
        self.assertFalse(self.manager._as.alive())                # nowa rozmowa: nowy proces z pełnym promptem
        self.ask("Od nowa")
        self.assertIn("Sterowanie panelem", self.streams()[-1]["prompt"])

    def test_koniec_po_bezczynnosci(self):
        m = self.new_manager(PANEL_ASYSTENT_BEZCZYNNOSC="1")
        self.ask("Cześć", manager=m)
        self.assertTrue(m._as.alive())
        self.wait_for(lambda: not m._as.alive(), timeout=5)


@unittest.skipUnless(JS, "brak silnika JS (osascript albo node)")
class Dzialania(unittest.TestCase):
    def test_parsowanie(self):
        with open(PANEL, encoding="utf-8") as f:
            src = re.search(r"/\*asActs:start\*/(.*?)/\*asActs:end\*/", f.read(), re.S).group(1)
        text = ("Masz dwie sprawy.\nZmieniono: Alfa: Zadanie D\nPokaż: #p-alfa-marketing\n"
                "Otwórz: alfa|ZADANIA.md|12\nprzewiń: Po terminie\nZamknij:\nOtwórz:")
        r = run_js(src + "\nJSON.stringify(asActs(%s))" % json.dumps(text))
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertEqual(out["text"], "Masz dwie sprawy.\nZmieniono: Alfa: Zadanie D\nOtwórz:")
        self.assertEqual(out["acts"], [{"k": "pokaż", "v": "#p-alfa-marketing"}, {"k": "otwórz", "v": "alfa|ZADANIA.md|12"},
                                       {"k": "przewiń", "v": "Po terminie"}, {"k": "zamknij", "v": ""}])


if __name__ == "__main__":
    unittest.main()
