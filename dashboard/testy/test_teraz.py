"""„Teraz” w Przeglądzie: blok activity w /api/data (filmy, rozmowy czekające na odpowiedź, zamknięte zadania)."""
import contextlib
import datetime
import io
import json
import os

from wspolne import Baza, server

film = server.film


def task(title, state="todo", project="p", file="ZADANIA.md"):
    return {"project": project, "file": file, "title": title, "state": state}


class Zamkniete(Baza):
    NOW = datetime.datetime(2026, 11, 19, 12, 0, 0)

    def test_pierwszy_odczyt_nic_nie_zamyka(self):
        st = server.track_closed([task("A", "done"), task("B")], {}, self.NOW)
        self.assertEqual(st["closed"], [])
        self.assertEqual(st["open"], ["p|ZADANIA.md|B"])

    def test_otwarte_potem_zrobione(self):
        st = server.track_closed([task("A"), task("B")], {}, self.NOW)
        later = self.NOW + datetime.timedelta(minutes=5)
        st = server.track_closed([task("A", "done"), task("B")], st, later)
        self.assertEqual(st["closed"], [{"project": "p", "file": "ZADANIA.md", "title": "A",
                                         "at": later.isoformat(timespec="seconds"), "how": "seen"}])
        self.assertEqual(st["open"], ["p|ZADANIA.md|B"])
        # kolejny odczyt bez zmian: bez nowego wpisu
        self.assertEqual(server.track_closed([task("A", "done"), task("B")], st, later)["closed"], st["closed"])

    def test_ponowne_zamkniecie_jeden_wpis(self):
        st = server.track_closed([task("A")], {}, self.NOW)
        st = server.track_closed([task("A", "done")], st, self.NOW)
        st = server.track_closed([task("A")], st, self.NOW + datetime.timedelta(hours=1))
        st = server.track_closed([task("A", "done")], st, self.NOW + datetime.timedelta(hours=2))
        self.assertEqual(len(st["closed"]), 1)
        self.assertEqual(st["closed"][0]["at"], (self.NOW + datetime.timedelta(hours=2)).isoformat(timespec="seconds"))

    def test_usuniete_i_zmieniony_tytul_to_nie_zamkniecie(self):
        st = server.track_closed([task("A"), task("B")], {}, self.NOW)
        st = server.track_closed([task("A2")], st, self.NOW)
        self.assertEqual(st["closed"], [])

    def test_stare_wpisy_i_smieci_odrzucone(self):
        prev = {"open": [], "closed": [
            {"project": "p", "file": "ZADANIA.md", "title": "stare", "at": "2026-11-16T10:00:00"},
            {"project": "p", "file": "ZADANIA.md", "title": "nowe", "at": "2026-11-19T09:00:00"},
            {"project": "p", "title": "bez pliku", "at": "2026-11-19T09:00:00"}, "tekst"]}
        st = server.track_closed([], prev, self.NOW)
        self.assertEqual([c["title"] for c in st["closed"]], ["nowe"])

    def test_czas_z_pliku_albo_uruchomienia(self):
        st = server.track_closed([task("A"), task("B")], {}, self.NOW)
        later = self.NOW + datetime.timedelta(hours=2)
        file_t = self.NOW + datetime.timedelta(minutes=30)
        run_t = self.NOW + datetime.timedelta(minutes=20)
        when = lambda t: [(run_t, "run"), (file_t, "file")] if t["title"] == "A" else [(file_t, "file")]
        got = server.track_closed([task("A", "done"), task("B", "done")], st, later, when)["closed"]
        self.assertEqual({c["title"]: (c["at"], c["how"]) for c in got},
                         {"A": (run_t.isoformat(timespec="seconds"), "run"),
                          "B": (file_t.isoformat(timespec="seconds"), "file")})

    def test_czas_sprzed_poprzedniego_odczytu_odrzucony(self):
        st = server.track_closed([task("A")], {}, self.NOW)
        old = self.NOW - datetime.timedelta(hours=3)
        got = server.track_closed([task("A", "done")], st, self.NOW + datetime.timedelta(hours=1),
                                  lambda t: [(old, "run")])["closed"]
        self.assertEqual(got[0]["how"], "seen")

    def test_wykryte_po_30_h_nie_trafia_do_24_h(self):
        runs = os.path.join(self.tmp, "u30")
        t0 = self.NOW - datetime.timedelta(hours=31)
        server.closed_recent([task("A")], runs, t0)
        closed_at = self.NOW - datetime.timedelta(hours=30)
        got = server.closed_recent([task("A", "done")], runs, self.NOW, lambda t: [(closed_at, "file")])
        self.assertEqual(got, [])
        # bez czasu z pliku: chwila wykrycia, oznaczona jako „zauważone”
        server.closed_recent([task("B")], runs, self.NOW)
        got = server.closed_recent([task("B", "done")], runs, self.NOW + datetime.timedelta(minutes=1))
        self.assertEqual([(c["title"], c["how"]) for c in got], [("B", "seen")])

    def test_duplikaty_tytulu_w_pliku(self):
        st = server.track_closed([task("A"), task("A")], {}, self.NOW)
        self.assertEqual(st["open"], ["p|ZADANIA.md|A", "p|ZADANIA.md|A"])
        st = server.track_closed([task("A", "done"), task("A")], st, self.NOW)
        self.assertEqual([c["title"] for c in st["closed"]], ["A"])
        # bez zmian w liczbie otwartych: nic nowego
        again = server.track_closed([task("A", "done"), task("A")], st, self.NOW + datetime.timedelta(hours=1))
        self.assertEqual(again["closed"], st["closed"])

    def test_bez_zmian_bez_zapisu(self):
        runs = os.path.join(self.tmp, "u2")
        server.closed_recent([task("A")], runs, self.NOW)
        path = os.path.join(runs, server.CLOSED_FILE)
        os.utime(path, (1, 1))
        server.closed_recent([task("A")], runs, self.NOW + datetime.timedelta(minutes=1))
        self.assertEqual(os.path.getmtime(path), 1)

    def test_zapis_w_katalogu_uruchomien(self):
        runs = os.path.join(self.tmp, "u")
        self.assertEqual(server.closed_recent([task("A")], runs), [])
        got = server.closed_recent([task("A", "done")], runs)
        self.assertEqual([c["title"] for c in got], ["A"])
        with open(os.path.join(runs, server.CLOSED_FILE), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["open"], [])


    def test_ponownie_otwarte_znika(self):
        st = server.track_closed([task("A"), task("B")], {}, self.NOW)
        st = server.track_closed([task("A", "done"), task("B")], st, self.NOW)
        self.assertEqual([c["title"] for c in st["closed"]], ["A"])
        st = server.track_closed([task("A"), task("B")], st, self.NOW + datetime.timedelta(minutes=5))
        self.assertEqual(st["closed"], [])
        # dwa zadania o tym samym tytule: jedno nadal [x], wpis zostaje
        st = server.track_closed([task("C"), task("C")], {}, self.NOW)
        st = server.track_closed([task("C", "done"), task("C")], st, self.NOW)
        st = server.track_closed([task("C", "done"), task("C")], st, self.NOW + datetime.timedelta(minutes=5))
        self.assertEqual([c["title"] for c in st["closed"]], ["C"])

    def test_dolna_granica_to_ostatni_odczyt(self):
        runs = os.path.join(self.tmp, "u3")
        server.closed_recent([task("A")], runs, self.NOW)
        # drugi odczyt bez zmian: plik się nie zmienia, ale granica przesuwa się w pamięci procesu
        server.closed_recent([task("A")], runs, self.NOW + datetime.timedelta(hours=1))
        between = self.NOW + datetime.timedelta(minutes=30)          # przed drugim odczytem: nie mogło być zamknięcia
        got = server.closed_recent([task("A", "done")], runs, self.NOW + datetime.timedelta(hours=2),
                                   lambda t: [(between, "run")])
        self.assertEqual([(c["title"], c["how"]) for c in got], [("A", "seen")])

    def test_plik_w_podkatalogu_i_przeniesienie(self):
        runs = os.path.join(self.tmp, "u4")
        os.makedirs(runs)
        with open(os.path.join(runs, server.CLOSED_OLD), "w", encoding="utf-8") as f:
            json.dump({"open": ["p|ZADANIA.md|A"], "closed": [], "readAt": self.NOW.isoformat()}, f)
        got = server.closed_recent([task("A", "done")], runs, self.NOW + datetime.timedelta(minutes=1))
        self.assertEqual([c["title"] for c in got], ["A"])
        self.assertFalse(os.path.exists(os.path.join(runs, server.CLOSED_OLD)))
        self.assertTrue(os.path.isfile(os.path.join(runs, server.CLOSED_FILE)))
        self.assertNotEqual(os.path.dirname(server.CLOSED_FILE), "")

    def test_manager_nie_bierze_pliku_za_uruchomienie(self):
        os.makedirs(self.runs, exist_ok=True)
        legacy = os.path.join(self.runs, server.CLOSED_OLD)
        with open(legacy, "w", encoding="utf-8") as f:
            json.dump({"open": [], "closed": []}, f)
        m = self.new_manager()
        self.assertEqual(m.recent_runs(), [])
        self.assertTrue(os.path.isfile(legacy))
        self.assertIn("zamkniete.json", server.agents.NOT_RUNS)


class Filmy(Baza):
    def post(self, name, state=None, title=None):
        pf = os.path.join(self.folder, "posty", name)
        os.makedirs(pf, exist_ok=True)
        if title:
            with open(os.path.join(pf, "post.md"), "w", encoding="utf-8") as f:
                f.write("# %s\n\n## Facebook\ntekst\n" % title)
        if state:
            with open(os.path.join(pf, film.STATE), "w", encoding="utf-8") as f:
                json.dump(state, f)
        return pf

    def test_stany_filmow(self):
        now = datetime.datetime(2026, 11, 19, 12, 0, 0)
        iso = lambda **kw: (now - datetime.timedelta(**kw)).isoformat(timespec="seconds")
        self.post("2026-11-20-start", {"state": "running", "at": iso(minutes=2)}, "Start sklepu")
        self.post("2026-11-21-kolejka", {"state": "queued", "at": iso(seconds=10)})
        self.post("2026-11-18-wczoraj", {"state": "done", "at": iso(hours=3)}, "Zapowiedź")
        self.post("2026-11-17-blad", {"state": "error", "at": iso(hours=5), "error": "x" * 500})
        self.post("2026-11-10-stary", {"state": "done", "at": iso(days=3)})
        self.post("2026-11-09-zawieszony", {"state": "running", "at": iso(hours=2)})
        self.post("2026-11-08-bez-czasu", {"state": "running"})
        self.post("bez-stanu", None, "Bez filmu")
        _, index = server.load_projects(resolve=False)
        busy = {os.path.join(self.folder, "posty", "2026-11-20-start")}
        got = {f["post"]: f for f in server.film_activity(index, now, busy)}
        # running tylko z busy (nagrywa ten proces); queued, running bez busy i bez czasu: pominięte
        self.assertEqual(sorted(got), ["2026-11-17-blad", "2026-11-18-wczoraj", "2026-11-20-start"])
        start = got["2026-11-20-start"]
        self.assertEqual((start["title"], start["state"], start["day"], start["project"]),
                         ("Start sklepu", "running", "2026-11-20", "projekt-testowy"))
        self.assertEqual(got["2026-11-18-wczoraj"]["title"], "Zapowiedź")
        self.assertEqual(len(got["2026-11-17-blad"]["error"]), 200)
        self.assertEqual([f["post"] for f in server.film_activity(index, now, busy)][0], "2026-11-20-start")  # najnowsze
        self.assertNotIn("2026-11-08-bez-czasu", [f["post"] for f in server.film_activity(index, now, busy)])

    def test_przerwane_przy_restarcie(self):
        a = self.post("2026-11-20-a", {"state": "running", "at": "2026-11-19T10:00:00", "scenario": 12.5})
        b = self.post("2026-11-21-b", {"state": "queued"})
        c = self.post("2026-11-22-c", {"state": "done", "at": "2026-11-19T10:00:00"})
        _, index = server.load_projects(resolve=False)
        self.assertEqual(server.mark_interrupted_films(index), 2)
        self.assertEqual((film.read_state(a)["state"], film.read_state(a)["error"], film.read_state(a)["scenario"]),
                         ("error", server.FILM_INTERRUPTED, 12.5))
        self.assertEqual(film.read_state(b)["state"], "error")
        self.assertEqual(film.read_state(c)["state"], "done")
        self.assertEqual(server.mark_interrupted_films(index), 0)          # raz

    def test_inny_proces_nagrywa(self):
        now = datetime.datetime.now().replace(microsecond=0)
        at = (now - datetime.timedelta(minutes=1)).isoformat()
        other = self.post("2026-11-20-inny-host", {"state": "running", "at": at, "host": "inny-komputer", "pid": 1})
        dead = self.post("2026-11-21-martwy", {"state": "running", "at": at, "host": film.HOST, "pid": 999999})
        old = self.post("2026-11-22-stary", {"state": "running", "at": "2026-01-01T10:00:00", "host": "inny-komputer"})
        _, index = server.load_projects(resolve=False)
        got = {f["post"]: f["state"] for f in server.film_activity(index, now)}
        self.assertEqual(got, {"2026-11-20-inny-host": "running"})          # stare i martwy proces: nie
        self.assertEqual(server.mark_interrupted_films(index), 1)           # tylko własny host i martwy proces
        self.assertEqual(film.read_state(other)["state"], "running")
        self.assertEqual(film.read_state(old)["state"], "running")
        self.assertEqual(film.read_state(dead)["state"], "error")

    def test_kolejka_nagran(self):
        now = datetime.datetime.now().replace(microsecond=0)
        a = self.post("2026-11-20-a", None, "Pierwszy")
        b = self.post("2026-11-21-b", None, "Drugi")
        for pf, t in ((a, 100), (b, 50)):
            with open(os.path.join(pf, film.SCENARIO), "w", encoding="utf-8") as f:
                f.write("{}")
            os.utime(os.path.join(pf, film.SCENARIO), (t, t))
        done = self.post("2026-11-22-c", {"state": "error", "at": now.isoformat(), "scenario": 70.0})
        with open(os.path.join(done, film.SCENARIO), "w", encoding="utf-8") as f:
            f.write("{}")
        os.utime(os.path.join(done, film.SCENARIO), (70, 70))         # ta wersja już raz nagrywana: nie w kolejce
        _, index = server.load_projects(resolve=False)
        self.assertEqual([x[1] for x in server.film_queue(index)], ["2026-11-21-b", "2026-11-20-a"])
        self.assertNotIn("queued", [f["state"] for f in server.film_activity(index, now)])
        q = [(f["post"], f["pos"], f["title"]) for f in server.film_activity(index, now, queue=True) if f["state"] == "queued"]
        self.assertEqual(sorted(q, key=lambda x: x[1]), [("2026-11-21-b", 1, "Drugi"), ("2026-11-20-a", 2, "Pierwszy")])

    def test_nagrywarka_zapisuje_host_i_scenariusz(self):
        pf = self.post("2026-11-20-r", {"state": "queued", "scenario": 12.5})
        with open(os.path.join(pf, film.SCENARIO), "w", encoding="utf-8") as f:
            f.write('{"url": "https://example.org", "kroki": [{"pauza": 1}]}')
        os.makedirs(film.studio_dir(pf), exist_ok=True)                  # pokaz nagrywa tylko strony z marki
        with open(os.path.join(film.studio_dir(pf), film.BRAND), "w", encoding="utf-8") as f:
            json.dump({"strony": ["example.org"], "kolory": {"tlo": "#ffffff", "tekst": "#000000", "akcent": "#3b5bdb"}}, f)
        rec = film.Recorder(python="/bin/false")
        rec.available = lambda: True
        rec._run = lambda folder, title: None                        # bez nagrania: tylko stan startu
        self.assertEqual(rec.start(pf)[0], 202)
        st = film.read_state(pf)
        self.assertEqual((st["state"], st["host"], st["pid"], st["scenario"]), ("running", film.HOST, os.getpid(), 12.5))
        self.assertFalse(server.film_elsewhere(st))

    def test_pamiec_podreczna(self):
        _, index = server.load_projects(resolve=False)
        server._films_cache.update(at=0.0, key=None, value=[])
        self.assertEqual(server.films_cached(index), [])
        self.post("2026-11-20-x", {"state": "done", "at": datetime.datetime.now().isoformat(timespec="seconds")})
        self.assertEqual(server.films_cached(index), [])                   # w TTL: stara wartość
        pf = os.path.join(self.folder, "posty", "2026-11-20-x")
        film.write_state(pf, state="running")
        got = server.films_cached(index, {pf})                              # nowe nagranie: od razu
        self.assertEqual([(f["post"], f["state"]) for f in got], [("2026-11-20-x", "running")])
        server._films_cache["at"] -= server.ACTIVITY_TTL                    # po TTL: odczyt od nowa
        self.assertEqual(server.films_cached(index), [])

    def test_tryb_przykladowy_puste_bez_zapisu(self):
        data = {"projectsSource": "sample", "tasks": [task("A")]}
        got = server.activity(data, {}, self.manager)
        self.assertEqual(got, {"films": [], "chats": [], "closed": [], "runs": [], "recorder": False})
        self.assertFalse(os.path.exists(os.path.join(self.manager.runs_dir, server.CLOSED_FILE)))

    def test_activity_w_danych(self):
        self.post("2026-11-20-start", {"state": "done", "at": datetime.datetime.now().isoformat(timespec="seconds")})
        server._films_cache.update(at=0.0, key=None, value=[])
        data = server.build_data()
        self.assertEqual(sorted(data["activity"]), ["chats", "closed", "films", "recorder", "runs"])
        self.assertEqual([f["post"] for f in data["activity"]["films"]], ["2026-11-20-start"])
        self.assertEqual(data["activity"]["chats"], [])

    def test_zamkniete_w_danych(self):
        server.build_data()
        t = self.task("Zadanie B")
        self.assertEqual(server.change_task({"id": t["id"], "title": t["title"], "state": "done"})[0], 200)
        closed = server.build_data()["activity"]["closed"]
        # zamknięcie z panelu: dokładny czas zapisu ("set"), nie czas zmiany pliku
        self.assertEqual([(c["title"], c["how"]) for c in closed], [("Zadanie B", "set")])
        self.assertTrue(os.path.isfile(os.path.join(self.manager.runs_dir, server.CLOSED_FILE)))


class Uruchomienia(Baza):
    def test_zakonczone_z_24_h(self):
        self.set_mode("ok")
        rid = self.run_task("Zadanie A")[2]["id"]
        self.wait_for(lambda: (self.manager.get(rid) or {}).get("state") == "done")
        got = self.manager.recent_runs()
        self.assertEqual([r["id"] for r in got], [rid])
        self.assertNotIn("steps", got[0])
        # uruchomienie z agents.runs nie wraca drugi raz w activity.runs
        data = server.build_data()
        self.assertIn(rid, [r["id"] for r in data["agents"]["runs"]])
        self.assertEqual(data["activity"]["runs"], [])
        with self.manager._lock:
            self.manager._runs[rid]["endedAt"] = "2000-01-01T00:00:00"
        self.assertEqual(self.manager.recent_runs(), [])


class Rozmowy(Baza):
    def test_czeka_na_odpowiedz(self):
        self.set_mode("czat-wolno")
        t = self.task("Zadanie A")
        self.assertEqual(self.manager.chat_send(t["id"], t["title"], "Co dalej?")[0], 202)
        pend = self.manager.chat_pending()
        self.assertEqual([(c["title"], c["project"], c["file"], c["taskId"]) for c in pend],
                         [("Zadanie A", t["project"], t["file"], t["id"])])
        self.assertRegex(pend[0]["since"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d$")
        self.assertEqual([c["title"] for c in server.build_data()["activity"]["chats"]], ["Zadanie A"])
        self.wait_for(lambda: not self.manager.chat_pending())


if __name__ == "__main__":
    import unittest
    unittest.main()


class Odpornosc(Baza):
    """Runda 3: uszkodzony stan filmu, stare „running” z cudzym PID, wyjątek w activity, zamknięcie z panelu,
    pamięć /api/data."""
    post = Filmy.post

    def test_stan_filmu_nie_obiekt(self):
        for i, raw in enumerate(("[1, 2]", "7", '"tekst"', "null")):
            pf = self.post("2026-11-2%d-zly" % i)
            with open(os.path.join(pf, film.STATE), "w", encoding="utf-8") as f:
                f.write(raw)
            self.assertEqual(film.read_state(pf), {})
        _, index = server.load_projects(resolve=False)
        self.assertEqual(server.film_activity(index, queue=True), [])
        self.assertEqual(server.mark_interrupted_films(index), 0)
        server._films_cache.update(at=0.0, key=None, value=[])
        self.assertNotIn("error", server.build_data()["activity"])

    def test_stare_running_z_zywym_pid_nie_wstrzymuje_kolejki(self):
        old = (datetime.datetime.now() - datetime.timedelta(seconds=film.TIMEOUT + 120)).isoformat(timespec="seconds")
        # PID 1 żyje zawsze: ten sam host, ale proces nagrania dawno padł, a PID przejął inny proces
        pf = self.post("2026-11-20-pid", {"state": "running", "at": old, "host": film.HOST, "pid": 1})
        with open(os.path.join(pf, film.SCENARIO), "w", encoding="utf-8") as f:
            f.write("{}")
        st = film.read_state(pf)
        self.assertTrue(server.film_stale(st))
        self.assertIsNotNone(server.film_pending(pf))
        _, index = server.load_projects(resolve=False)
        self.assertEqual([x[1] for x in server.film_queue(index)], ["2026-11-20-pid"])
        # świeże running z innego procesu nadal wstrzymuje
        fresh = datetime.datetime.now().isoformat(timespec="seconds")
        self.post("2026-11-20-pid", {"state": "running", "at": fresh, "host": film.HOST, "pid": 1})
        self.assertFalse(server.film_stale(film.read_state(pf)))
        self.assertIsNone(server.film_pending(pf))

    def test_auto_record_zamyka_stare_running(self):
        old = (datetime.datetime.now() - datetime.timedelta(seconds=film.TIMEOUT + 120)).isoformat(timespec="seconds")
        pf = self.post("2026-11-20-st", {"state": "running", "at": old, "host": "inny-komputer", "scenario": 5.0})
        rec = film.Recorder(python="/bin/false")
        rec.available = lambda: True
        started = []
        rec.start = lambda folder, title="": started.append(folder) or (202, "")
        saved = server._recorder
        server._recorder = rec
        try:
            server.auto_record()
        finally:
            server._recorder = saved
        st = film.read_state(pf)
        self.assertEqual((st["state"], st["error"], st["scenario"]), ("error", server.FILM_STALE, 5.0))

    def test_wyjatek_w_activity_nie_wywraca_danych(self):
        orig = server.closed_recent

        def boom(*a, **kw):
            raise RuntimeError("x")
        server.closed_recent = boom
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                data = server.build_data()
        finally:
            server.closed_recent = orig
        act = data["activity"]
        self.assertEqual((act["films"], act["chats"], act["closed"], act["runs"]), ([], [], [], []))
        self.assertIn("RuntimeError", act["error"])
        self.assertTrue(data["tasks"])

    def test_zamkniecie_z_panelu_dokladny_czas(self):
        runs = os.path.join(self.tmp, "u-set")
        now = datetime.datetime(2026, 11, 19, 12, 0, 0)
        server.closed_recent([task("A")], runs, now)
        at = now + datetime.timedelta(minutes=3)
        server.note_closed("p", "ZADANIA.md", "A", runs, at)
        # następny odczyt nie dodaje drugiego wpisu z czasem wykrycia
        got = server.closed_recent([task("A", "done")], runs, now + datetime.timedelta(minutes=10))
        self.assertEqual([(c["title"], c["at"], c["how"]) for c in got], [("A", at.isoformat(timespec="seconds"), "set")])

    def test_pamiec_api_data(self):
        server.DATA_TTL = 60
        server.data_invalidate()
        first = server.data_cached()
        self.assertIs(server.data_cached(), first)                     # w TTL: ta sama odpowiedź
        server.data_invalidate()                                        # zapis (POST) unieważnia
        self.assertIsNot(server.data_cached(), first)
        self.assertIsNot(server.data_cached(ttl=0), server.data_cached(ttl=0))
