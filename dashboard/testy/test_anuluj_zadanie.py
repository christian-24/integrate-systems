"""Anulowanie zachowuje wiersz, zatrzymuje agenta i wymaga decyzji o zależnościach."""
import os
import subprocess
import unittest

from test_asystent_duzy import PW
from test_serwer import Serwer
from wspolne import TODAY, projekt, server
import pm


class Zadania(Serwer):
    def setUp(self):
        super().setUp()
        with open(os.path.join(self.folder, "ZADANIA.md"), "a", encoding="utf-8") as f:
            f.write("""
- [ ] Zbierz dane | kto: ty | kiedy: 2000-01-01
  pyta: Liczba [liczba]
- [ ] Opracuj dane | kto: codex | po: Zbierz dane, Zadanie A
- [ ] Porównaj dane | kto: ty | po: Zbierz dane
""")

    def body(self, title, **extra):
        return {"id": self.task(title)["id"], "title": title, **extra}


class Anulowanie(Zadania):
    def test_parser_i_liczniki(self):
        task = projekt.parse_task("- [-] Zbierz dane | anulowano: 2026-11-25 | powód: zmiana zakresu")
        self.assertEqual((task["state"], task["cancelledAt"], task["cancelReason"], task["errors"]),
                         ("cancelled", "2026-11-25", "zmiana zakresu", []))
        old = self.data()
        self.assertEqual(self.post("/api/task/cancel", self.body("Zbierz dane", reason="Zmiana zakresu"))[0], 200)
        new = self.data()
        for key in ("youToday", "youLate", "late"):
            self.assertEqual(new[key], old[key] - 1, key)
        self.assertEqual(pm.facts()["counts"]["late"], new["late"])
        self.assertNotIn("Zbierz dane", str(pm.facts()["projects"]))
        self.assertIn("anulowano: " + TODAY + " | powód: Zmiana zakresu", self.row("Zbierz dane"))
        task = self.task("Zbierz dane")
        self.assertEqual(task["detail"]["fields"][0]["type"], "liczba")

    def test_przywrocenie_i_zaleznosci(self):
        body = self.body("Zbierz dane")
        dep = self.body("Opracuj dane", fragment="Zbierz dane")
        self.assertEqual(self.post("/api/task/skip-cancelled-dependency", dep)[0], 409)
        self.assertEqual(self.post("/api/task/cancel", body)[0], 200)
        self.assertEqual(self.run_task("Opracuj dane")[:2], (409, "Poprzednik anulowany"))
        self.assertEqual(self.post("/api/task/skip-cancelled-dependency", dep)[0], 200)
        self.assertEqual(self.task("Opracuj dane")["after"], ["Zadanie A"])
        self.assertEqual(self.post("/api/task/cancel", self.body("Porównaj dane"))[0], 200)
        self.assertEqual(self.task("Porównaj dane")["after"], ["Zbierz dane"])
        self.assertEqual(self.post("/api/task/restore", body)[0], 200)
        self.assertEqual(self.row("Zbierz dane"), "- [ ] Zbierz dane | kto: ty | kiedy: 2000-01-01")
        self.assertEqual(self.post("/api/task/cancel", self.body("Zadanie F"))[0], 409)

    def test_zatrzymanie_pracujacego_agenta(self):
        self.set_mode("wolno")
        rid = self.run_task("Zadanie A")[2]["id"]
        self.wait_for(lambda: os.path.exists(self.pid_file) and self.manager.get(rid)["activity"].startswith("Bash"))
        self.assertEqual(self.post("/api/task/cancel", self.body("Zadanie A"))[0], 200)
        self.assertEqual(self.manager.get(rid)["state"], "stopped")
        self.assertEqual(self.task("Zadanie A")["state"], "cancelled")
        self.assertEqual(self.run_task("Zadanie A")[:2], (409, "Anulowane"))

    def test_obie_rozmowy_uzywaja_operacji_panelu(self):
        self.manager.cancel_hook = server.cancel_task
        pid = self.task("Zbierz dane")["project"]
        for launch, title in (("*", "Zbierz dane"), (pid, "Zadanie B")):
            with self.subTest(launch=launch):
                text, messages = self.manager._after_answer(f"Anuluj zadanie: {pid} | {title} | Zmiana planu", launch)
                self.assertEqual(text, "")
                self.assertEqual(messages[0]["text"], "Anulowano: " + title)
                self.assertEqual(self.task(title)["cancelReason"], "Zmiana planu")


BROWSER = r"""
import sys
from playwright.sync_api import sync_playwright
url, owner, dependent, other, done = sys.argv[1:]
with sync_playwright() as pw:
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": 393, "height": 852})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(url + "#asystent")
    page.wait_for_selector(".as-today")
    drawer = page.locator("#drawer")
    page.goto(url + "#asystent?z=" + done.replace("|", "%7C"))
    drawer.get_by_role("heading", name="Zadanie F").wait_for()
    assert not drawer.get_by_text("Anuluj zadanie", exact=True).count()
    page.goto(url + "#asystent?z=" + owner.replace("|", "%7C"))
    drawer.get_by_label("Liczba", exact=True).wait_for()
    drawer.get_by_role("button", name="Anuluj zadanie", exact=True).click()
    drawer.get_by_label("Powód (opcjonalnie)").fill("Zmiana planu")
    drawer.get_by_role("button", name="Potwierdź anulowanie").click()
    drawer.get_by_text("Zmiana planu", exact=True).wait_for()
    page.goto(url + "#asystent?z=" + other.replace("|", "%7C"))
    drawer.get_by_role("button", name="Anuluj też to").click()
    drawer.get_by_role("button", name="Potwierdź anulowanie").click()
    drawer.get_by_role("button", name="Przywróć").wait_for()
    page.goto(url + "#asystent?z=" + dependent.replace("|", "%7C"))
    drawer.locator(".move-box").get_by_text("Poprzednik anulowany", exact=True).wait_for()
    drawer.get_by_role("button", name="Rób bez niego").click()
    drawer.locator(".move-box").get_by_text("Poprzednik anulowany", exact=True).wait_for(state="detached")
    page.goto(url + "#asystent?z=" + owner.replace("|", "%7C"))
    drawer.get_by_role("button", name="Przywróć").click()
    drawer.get_by_label("Liczba", exact=True).wait_for()
    assert not errors, errors
"""


@unittest.skipUnless(PW and not os.environ.get("PANEL_TESTY_BEZ_RENDERU"), "brak renderu Playwright")
class Przegladarka(Zadania):
    def test_przyciski_i_potwierdzenie(self):
        env = dict(os.environ)
        if os.path.isdir("/opt/ms-playwright"):
            env.setdefault("PLAYWRIGHT_BROWSERS_PATH", "/opt/ms-playwright")
        subprocess.run([PW, "-c", BROWSER, f"http://127.0.0.1:{self.port}/",
                        *(self.body(title)["id"] for title in
                          ("Zbierz dane", "Opracuj dane", "Porównaj dane", "Zadanie F"))],
                       env=env, check=True, timeout=55)
