"""Plan dnia: PM układa plan z otwartych zadań, właściciel uruchamia wybrane."""
import json
import os
import unittest

from wspolne import Baza, server


class PlanDnia(Baza):
    def ask(self, text="Dziś zadania z terminem"):
        code, err, extra = self.manager.run_plan(text)
        self.assertEqual(code, 200, err)
        return self.wait(extra["id"])

    def test_kandydaci_tylko_otwarte_z_powodem(self):
        cands = self.manager.plan_candidates()
        titles = {c["title"]: c for c in cands}
        self.assertNotIn("Zadanie F", titles)                         # zrobione
        self.assertTrue(titles["Zadanie A"]["agent"])
        self.assertFalse(titles["Zadanie D"]["agent"])                # kto: ty
        self.assertEqual(titles["Zadanie D"]["why"], "Zadanie po Twojej stronie")
        self.assertFalse(titles["Zadanie E"]["agent"])                # wymaga: zgoda
        self.assertEqual(titles["Zadanie A"]["stage"], "Pierwszy")

    def test_plan_z_odpowiedzi_bez_obcych_id(self):
        self.set_mode("plan")
        rec = self.ask("Najpierw zadanie A")
        self.assertEqual(rec["state"], "done", rec["error"])
        self.assertEqual(rec["ask"], "Najpierw zadanie A")
        plan = rec["plan"]
        self.assertEqual(len(plan["agents"]), 2)                     # id spoza listy odrzucone
        self.assertTrue(all("|" in a["id"] and a["title"] for a in plan["agents"]))
        self.assertEqual(len(plan["you"]), 1)
        self.assertEqual(plan["note"], "test")
        self.assertNotIn("```", rec["result"])
        call = self.calls()[-1]
        self.assertIn("Najpierw zadanie A", call["prompt"])
        self.assertIn("default", call["argv"])                       # bez acceptEdits: plan niczego nie zmienia
        self.assertNotIn("acceptEdits", call["argv"])

    def test_plan_bez_bloku_to_blad(self):
        self.set_mode("plan-zly")
        rec = self.ask()
        self.assertEqual(rec["state"], "error")
        self.assertIsNone(rec["plan"])

    def test_odmowy_wejscia(self):
        self.assertEqual(self.manager.run_plan("   ")[0], 400)
        self.assertEqual(self.manager.run_plan("x" * 1501)[0], 400)
        self.assertEqual(self.manager.accept_plan("nie-ma", ["a"])[0], 404)

    def test_akceptacja_uruchamia_tylko_zadania_z_planu(self):
        self.set_mode("plan")
        rec = self.ask()
        ids = [a["id"] for a in rec["plan"]["agents"]]
        self.set_mode("zostaw")
        code, err, extra = self.manager.accept_plan(rec["id"], ids[:1] + ["projekt|ZADANIA.md|99"])
        self.assertEqual(code, 200, err)
        self.assertEqual([s["id"] for s in extra["started"]], ids[:1])
        self.assertEqual(extra["failed"][0]["error"], "Spoza planu.")
        self.wait(extra["started"][0]["runId"])
        self.assertEqual(self.manager.get(rec["id"])["accepted"], ids[:1])
        self.assertEqual(self.manager.accept_plan(rec["id"], [])[0], 400)

    def test_trasy_serwera(self):
        self.assertIn("/api/plan/ask", server.WRITES)
        self.assertIn("/api/plan/accept", server.WRITES)


if __name__ == "__main__":
    unittest.main()
