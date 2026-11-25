"""Zadanie właściciela jako formularz (zlecenie 2026-11-25): pola z typami w `pyta:`, „Zrobione” zapisuje
`odpowiedź:` i zamyka zadanie, odblokowanie `po:`, propozycja pól dla zadania bez `pyta:` (atrapa modelu),
przejście przy starcie, zakaz pól na hasła, formularz w szczegółach zadania (każdy typ, Chromium 393 i 1440 px)."""
import json
import os
import subprocess
import unittest
from unittest.mock import patch

from test_asystent_duzy import PW
from test_serwer import Serwer
from wspolne import TODAY, Baza, projekt, server
import pola  # noqa: E402  (ścieżka dashboard/ z wspolne)

ZADANIA = """# Zadania: Projekt testowy

## Etap: Pierwszy

- [ ] Podaj identyfikatory kont | kto: ty | kiedy: %(d)s | czas: 5
  cel: Pomiar kont nie liczy kont właściciela ani testowych.
  pyta: Identyfikatory Twoich kont [tekst, np. 1, 2]; Brak kont testowych [tak/nie]
- [ ] Wyłącz konta z pomiaru | kto: agent | kiedy: %(d)s | po: Podaj identyfikatory kont
- [ ] Ustaw kampanię | kto: ty | kiedy: %(d)s
  cel: Agent zaplanuje kampanię.
  pyta: Kanał [wybór: LinkedIn | Facebook]; Budżet [liczba, zł]; Start [data]; Strona [link]; Wideo [tak/nie]; Hasło do Meta [hasło: w Menedżerze firmy Meta]
  - [ ] Sprawdź konto reklamowe
  - [x] Przeczytaj brief
- [ ] Wybierz dostawcę poczty | kto: ty | kiedy: %(d)s
  cel: Agent podłączy wybranego dostawcę.
- [ ] Przeczytaj szkic wydania | kto: ty | kiedy: %(d)s
- [ ] Zadanie agenta bez pól | kto: claude | kiedy: %(d)s

## Do rozplanowania
""" % {"d": TODAY}


class Parser(unittest.TestCase):
    def test_typy(self):
        f = projekt.parse_fields("Identyfikatory Twoich kont [tekst, np. 1, 2]; Brak kont testowych [tak/nie]; "
                                 "Liczba kont [liczba]; Kanał [wybór: LinkedIn | Facebook]; Data startu [data]; "
                                 "Link [link]")
        self.assertEqual([(x["label"], x["type"]) for x in f],
                         [("Identyfikatory Twoich kont", "tekst"), ("Brak kont testowych", "tak/nie"),
                          ("Liczba kont", "liczba"), ("Kanał", "wybór"), ("Data startu", "data"), ("Link", "link")])
        self.assertEqual(f[0]["hint"], "np. 1, 2")
        self.assertEqual(f[3]["options"], ["LinkedIn", "Facebook"])

    def test_zgodnosc_wstecz(self):
        d = projekt.parse_detail(["  pyta: Imię w commitach; E-mail w commitach", "  pyta: Uwagi [pilne]"])
        self.assertEqual(d["asks"], ["Imię w commitach", "E-mail w commitach", "Uwagi [pilne]"])
        self.assertEqual({f["type"] for f in d["fields"]}, {"tekst"})
        self.assertEqual(projekt.parse_field("Kanał [wybór: tylko jeden]")["type"], "tekst")   # jedna opcja = tekst

    def test_zapis_w_obie_strony(self):
        text = ("Kanał [wybór: LinkedIn | Facebook]; Budżet [liczba, zł]; Imię; Start [data]; Strona [link]; "
                "Wideo [tak/nie]; Hasło do Meta [hasło: w Menedżerze firmy]")
        self.assertEqual(projekt.asks_value(text), text)
        self.assertEqual(len(projekt.parse_fields(";".join("Pole %d" % i for i in range(12)))), projekt.FIELD_MAX)

    def test_zakaz_hasel(self):
        for label in ("Hasło do Meta", "Klucz API", "Token dostępu", "PIN do karty", "Password"):
            self.assertEqual(projekt.parse_field(label + " [tekst]")["type"], "hasło", label)
            with self.assertRaises(ValueError):
                projekt.asks_value(label)
        self.assertEqual(projekt.parse_field("Słowa kluczowe")["type"], "tekst")
        self.assertEqual(projekt.asks_value("Hasło do Meta", strict=False), "Hasło do Meta [hasło]")
        self.assertEqual(projekt.parse_field("Hasło [hasło: gdzie właściciel wpisuje je sam]")["where"], "")
        with self.assertRaises(ValueError):                                # na pole hasła nie ma odpowiedzi
            projekt.answer_of(projekt.parse_field("Hasło [hasło]"), "tajne")

    def test_odpowiedzi_wedlug_typu(self):
        f = projekt.parse_fields("A [liczba]; B [tak/nie]; C [wybór: x | y]; D [data]; E [link]; F; H [hasło]")
        self.assertEqual(projekt.answer_lines(f, ["1 200", True, "y", "2026-12-01", "https://a.pl", "brak", None]),
                         ["A = 1 200", "B = tak", "C = y", "D = 2026-12-01", "E = https://a.pl", "F = brak"])
        self.assertEqual(projekt.answer_lines(f, {"A": "3,5", "C": "x", "D": "2026-01-02", "E": "http://b", "F": "x"})[1],
                         "B = nie")
        for bad in (["dużo", True, "y", "2026-12-01", "https://a.pl", "x"], ["1", True, "z", "2026-12-01", "https://a.pl", "x"],
                    ["1", True, "y", "1.12.2026", "https://a.pl", "x"], ["1", True, "y", "2026-12-01", "a.pl", "x"],
                    ["1", True, "y", "2026-12-01", "https://a.pl", " "], ["1", "może", "y", "2026-12-01", "https://a.pl", "x"]):
            with self.assertRaises(ValueError, msg=bad):
                projekt.answer_lines(f, bad)


class Wspolne(Baza):
    def setUp(self):
        super().setUp()
        with open(os.path.join(self.folder, "ZADANIA.md"), "w", encoding="utf-8") as f:
            f.write(ZADANIA)
        self._fields = server._fields
        server._fields = None

    def tearDown(self):
        server._fields = self._fields
        super().tearDown()

    def text(self):
        with open(os.path.join(self.folder, "ZADANIA.md"), encoding="utf-8") as f:
            return f.read()


class Zapis(Wspolne):
    def test_pyta_przez_api_szczegolow(self):
        t = self.task("Wybierz dostawcę poczty")
        self.assertEqual(server.update_detail({"id": t["id"], "title": t["title"], "key": "pyta",
                                               "value": "Dostawca [wybór: Postmark | SES]"})[0], 200)
        self.assertIn("  pyta: Dostawca [wybór: Postmark | SES]", self.text())          # „|” zostaje
        code, msg = server.update_detail({"id": t["id"], "title": t["title"], "key": "pyta", "value": "Hasło do SES"})
        self.assertEqual(code, 400)
        self.assertIn("hasła", msg)

    def test_zrobione_zapisuje_i_odblokowuje(self):
        self.assertFalse(self.task("Wyłącz konta z pomiaru")["waitingFor"][0]["done"])
        t = self.task("Podaj identyfikatory kont")
        self.assertEqual(server.finish_task({"id": t["id"], "title": t["title"], "values": ["1, 2", True]}), (200, ""))
        text = self.text()
        self.assertIn("- [x] Podaj identyfikatory kont", text)
        self.assertIn("  odpowiedź: Identyfikatory Twoich kont = 1, 2\n  odpowiedź: Brak kont testowych = tak", text)
        self.assertTrue(self.task("Wyłącz konta z pomiaru")["waitingFor"][0]["done"])
        self.assertEqual(server.finish_task({"id": t["id"], "title": t["title"], "values": []})[0], 409)   # już zamknięte

    def test_zrobione_z_krokami_i_bledem(self):
        t = self.task("Ustaw kampanię")
        before = self.text()
        code, msg = server.finish_task({"id": t["id"], "title": t["title"],
                                        "values": ["Ins", "10", TODAY, "https://a.pl", False, None]})
        self.assertEqual(code, 400)
        self.assertIn("Kanał", msg)
        self.assertEqual(self.text(), before)                                            # nic nie zapisane
        code, _ = server.finish_task({"id": t["id"], "title": t["title"], "steps": [True, True],
                                      "values": ["Facebook", "1 200", TODAY, "https://a.pl", False, "tajne"]})
        self.assertEqual(code, 200)
        d = self.task("Ustaw kampanię")
        self.assertEqual(d["state"], "done")
        self.assertEqual([s["done"] for s in d["detail"]["steps"]], [True, True])
        self.assertEqual([a["label"] for a in d["detail"]["answers"]], ["Kanał", "Budżet", "Start", "Strona", "Wideo"])
        self.assertNotIn("tajne", self.text())                                           # pole hasła bez odpowiedzi

    def test_zrobione_bez_pol(self):
        t = self.task("Przeczytaj szkic wydania")
        self.assertEqual(server.finish_task({"id": t["id"], "title": t["title"]}), (200, ""))
        self.assertIn("- [x] Przeczytaj szkic wydania | kto: ty", self.text())
        self.assertNotIn("odpowiedź", self.text().split("Przeczytaj szkic")[1].split("\n- ")[0])


class Propozycja(Wspolne):
    def test_pola_dla_zadania_bez_pyta(self):
        t = self.task("Wybierz dostawcę poczty")
        self.assertTrue(pola.needs_fields(t))
        with patch.object(self.manager, "ask_fields", return_value={1: "Dostawca [wybór: Postmark | SES]; Hasło do SES"}) as ask:
            code, _, extra = server.task_fields({"id": t["id"], "title": t["title"]})
            self.assertEqual((code, extra["asks"]), (200, "Dostawca [wybór: Postmark | SES]; Hasło do SES [hasło]"))
            items = ask.call_args[0][0]
            self.assertEqual(items[0]["cel"], "Agent podłączy wybranego dostawcę.")
            self.assertIn("  pyta: Dostawca [wybór: Postmark | SES]; Hasło do SES [hasło]", self.text())
            t = self.task("Wybierz dostawcę poczty")
            self.assertEqual([f["type"] for f in t["detail"]["fields"]], ["wybór", "hasło"])
            server.task_fields({"id": t["id"], "title": t["title"]})                    # drugi raz bez modelu
            self.assertEqual(ask.call_count, 1)

    def test_bez_danych_sam_przycisk(self):
        t = self.task("Przeczytaj szkic wydania")
        before = self.text()
        with patch.object(self.manager, "ask_fields", return_value={1: ""}) as ask:
            code, _, extra = server.task_fields({"id": t["id"], "title": t["title"]})
            server.task_fields({"id": t["id"], "title": t["title"]})
        self.assertEqual((code, extra["asks"], ask.call_count), (200, "", 1))          # raz, zapis w stanie
        self.assertEqual(self.text(), before)
        with open(os.path.join(self.runs, pola.STATE_FILE), encoding="utf-8") as f:
            self.assertIn(projekt.task_key(t), json.load(f)["tasks"])

    def test_model_niedostepny(self):
        t = self.task("Wybierz dostawcę poczty")
        with patch.object(self.manager, "ask_fields", return_value=None) as ask:
            self.assertEqual(server.task_fields({"id": t["id"], "title": t["title"]})[0], 503)
            self.assertEqual(server.task_fields({"id": t["id"], "title": t["title"]})[0], 503)
        self.assertEqual(ask.call_count, 1)                                              # ponowna próba za godzinę
        self.assertNotIn("pyta: Dostawca", self.text())

    def test_bez_propozycji_dla_innych(self):
        for title in ("Podaj identyfikatory kont", "Zadanie agenta bez pól", "Wyłącz konta z pomiaru"):
            self.assertFalse(pola.needs_fields(self.task(title)), title)

    def test_przejscie(self):
        answers = {"Wybierz dostawcę poczty": "Dostawca [wybór: Postmark | SES]", "Przeczytaj szkic wydania": ""}

        def ask(items):
            return {i["n"]: answers[i["tytuł"]] for i in items}
        with patch.object(self.manager, "ask_fields", side_effect=ask) as m:
            f = server.get_fields()
            self.assertTrue(f.migrate())
            self.assertTrue(f.migrate())                                                 # jednorazowe
        self.assertEqual(m.call_count, 1)                                                # jedno wywołanie na paczkę
        summary = server.build_data()["fieldsMigration"]
        self.assertEqual((summary["done"], summary["checked"]), (True, 2))
        self.assertEqual(summary["added"], [{"project": "Projekt testowy", "title": "Wybierz dostawcę poczty",
                                             "asks": "Dostawca [wybór: Postmark | SES]"}])
        self.assertIn("Ustaw kampanię | kto: ty | kiedy: %s\n" % TODAY, self.text())    # reszta wierszy bez zmian

    def test_przejscie_czeka_na_model(self):
        with patch.object(self.manager, "ask_fields", return_value=None):
            self.assertFalse(server.get_fields().migrate())
        self.assertFalse(server.get_fields().summary().get("done"))

    def test_atrapa_claude(self):
        """ask_fields z atrapą CLI: JSON w odpowiedzi, zła odpowiedź = None."""
        with patch.object(self.manager, "claude_free", return_value=True):
            self.set_mode("pola")
            self.assertEqual(self.manager.ask_fields([{"n": 1, "tytuł": "Podaj liczbę kont"}]), {1: "Liczba kont [liczba]"})
            self.set_mode("ok")
            self.assertIsNone(self.manager.ask_fields([{"n": 1, "tytuł": "x"}]))
        prompt = next(c for c in self.calls() if "Zaproponuj pola" in str(c.get("prompt", "")))["prompt"]
        self.assertIn("Bez pól na hasła", prompt)


class Reguly(unittest.TestCase):
    def test_reguly_zakladania_zadan(self):
        from wspolne import agents
        rules = "\n".join(agents.Manager.run_rules("", __import__("datetime").date.today()))
        self.assertIn("pyta:", rules)
        self.assertIn("[tak/nie]", rules)
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        for doc in ("standard/STANDARD.md", "standard/PM.md", "dashboard/AGENCI.md"):
            with open(os.path.join(root, doc), encoding="utf-8") as f:
                self.assertIn("[tak/nie]", f.read(), doc)


PAGE = r"""
import json, sys
from playwright.sync_api import sync_playwright
url, ids = sys.argv[1], json.loads(sys.argv[2])
res, errs = {}, []
with sync_playwright() as p:
    b = p.chromium.launch()
    for w in (393, 1440):
        pg = b.new_page(viewport={"width": w, "height": 900})
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(url + "#asystent?z=" + ids["kampania"].replace("|", "%7C"))
        pg.wait_for_selector('form[data-dform="own"]', timeout=20000)
        f = pg.locator('form[data-dform="own"]')
        res[w] = {"kinds": f.evaluate("f=>[...f.querySelectorAll('[data-fv]')].map(x=>x.tagName+':'+(x.type||''))"),
                  "pw": f.locator(".own-pw").inner_text(), "steps": f.locator("[data-step]").count(),
                  "old": pg.locator("#drawer").inner_text().count("Najpierw wpiszesz"),
                  "sw": pg.evaluate("document.documentElement.scrollWidth")}
        pg.close()
    pg = b.new_page(viewport={"width": 393, "height": 852})
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(url + "#asystent?z=" + ids["konta"].replace("|", "%7C"))
    pg.wait_for_selector('form[data-dform="own"]', timeout=20000)
    pg.locator('[data-k="fv:own"]').click(); pg.wait_for_timeout(300)
    res["empty"] = pg.locator("#toast").inner_text()
    pg.fill('[data-fv="a0"]', "1, 2"); pg.check('[data-fv="a1"]')
    pg.locator('[data-k="fv:own"]').click(); pg.wait_for_timeout(2500)
    res["toast"] = pg.locator("#toast").inner_text()
    b.close()
print(json.dumps({"res": res, "errs": errs}, ensure_ascii=False))
"""


@unittest.skipUnless(PW and not os.environ.get("PANEL_TESTY_BEZ_RENDERU"), "brak Playwright albo PANEL_TESTY_BEZ_RENDERU")
class Formularz(Serwer):
    def setUp(self):
        super().setUp()
        with open(os.path.join(self.folder, "ZADANIA.md"), "w", encoding="utf-8") as f:
            f.write(ZADANIA)
        self._fields = server._fields
        server._fields = None

    def tearDown(self):
        server._fields = self._fields
        super().tearDown()

    def test_kazdy_typ_i_zrobione(self):
        ids = {"kampania": self.task("Ustaw kampanię")["id"], "konta": self.task("Podaj identyfikatory kont")["id"]}
        env = dict(os.environ)
        if not env.get("PLAYWRIGHT_BROWSERS_PATH") and os.path.isdir("/opt/ms-playwright"):
            env["PLAYWRIGHT_BROWSERS_PATH"] = "/opt/ms-playwright"
        with patch.object(self.manager, "ask_fields", return_value={1: ""}):
            r = subprocess.run([PW, "-c", PAGE, "http://127.0.0.1:%d/" % self.port, json.dumps(ids)],
                               capture_output=True, text=True, timeout=300, env=env)
        self.assertEqual(r.returncode, 0, r.stderr[-3000:])
        out = json.loads(r.stdout.strip().split("\n")[-1])
        self.assertEqual(out["errs"], [])
        for w in ("393", "1440"):
            o = out["res"][w]
            self.assertEqual(o["kinds"], ["SELECT:select-one", "INPUT:text", "INPUT:date", "INPUT:url", "INPUT:checkbox"], w)
            self.assertEqual(o["pw"], "Hasło do Meta wpisujesz sam w Menedżerze firmy Meta, nie w panelu.")
            self.assertEqual((o["steps"], o["old"]), (2, 0))
            self.assertLessEqual(o["sw"], int(w))
        self.assertEqual(out["res"]["empty"], "Wpisz: Identyfikatory Twoich kont.")
        self.assertIn("Zapisano odpowiedzi i zamknięto zadanie.", out["res"]["toast"])
        t = self.task("Podaj identyfikatory kont")
        self.assertEqual((t["state"], [a["value"] for a in t["detail"]["answers"]]), ("done", ["1, 2", "tak"]))
        self.assertTrue(self.task("Wyłącz konta z pomiaru")["waitingFor"][0]["done"])


if __name__ == "__main__":
    unittest.main()
