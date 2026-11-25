"""Pola formularza zadań właściciela (`pyta:`), gdy zadanie ich nie ma.

Panel pyta model (Claude Haiku, jedno małe wywołanie, jak przy wyborze wykonawcy), czy zadanie `kto: ty` potrzebuje
danych od właściciela, i dopisuje `pyta:` z typami pod wierszem zadania. Decyzja zapada raz na zadanie: zapis
w pliku zadania (`pyta:`) albo, gdy danych nie trzeba, wpis w `pola-zadan.json` (katalog uruchomień), bez zmiany
pliku. Przejście (zadanie przy starcie panelu, jeden raz) robi to samo dla wszystkich otwartych zadań właściciela
w projektach z rejestru i zapisuje listę dopisanych pól (projekt, zadanie, pola) w tym samym pliku.

Format pól: standard/STANDARD.md (pole `pyta:`). Bez pól na hasła i klucze: model może zwrócić tylko
„… [hasło: gdzie je wpisać]”, a pole o haśle bez takiego zapisu zamienia się w taką informację.
"""
import datetime
import json
import os
import threading

import projekt

STATE_FILE = "pola-zadan.json"
BATCH = 12                    # zadań w jednym wywołaniu modelu
RETRY_S = 3600                # po nieudanym wywołaniu to samo zadanie najwcześniej za godzinę
MIGRATION_DELAY_S = 20        # przejście rusza tyle sekund po starcie panelu
MIGRATION_RETRY_S = 1800      # model niedostępny: następna próba przejścia

PROMPT = (
    "Zaproponuj pola formularza dla zadań właściciela. Pole dodajesz tylko wtedy, gdy właściciel ma podać dane, "
    "które ktoś inny wykorzysta dalej: zadanie z listy „potem” (agent) albo cel lub „gotowe gdy” mówi, że właściciel "
    "podaje, wpisuje albo wybiera wynik (identyfikatory, liczby, wybór, datę, adres). Zadanie, które właściciel po "
    "prostu wykonuje sam (przeczytaj, odpisz, zadzwoń, umów, zatwierdź, nagraj, przetestuj, przejrzyj), nie "
    "potrzebuje pól: zwróć wtedy \"\". Nie pytaj o dane, których właściciel używa sam (adresy e-mail, osoby, "
    "terminy spotkań). W razie wątpliwości zwróć \"\". Najwyżej 3 pola. Zapis pola: Etykieta [typ], pola "
    "rozdzielone „; ”. Typy: [tekst, np. przykład], [tak/nie] (pole wyboru), [liczba], [wybór: A | B] (opcje tylko "
    "z treści zadania), [data], [link]. Bez pól na hasła, klucze, tokeny i kody: gdy zadanie wymaga hasła, zwróć "
    "„Hasło do <serwis> [hasło: gdzie właściciel wpisuje je sam]”. Etykiety krótkie, po polsku, bez znaków ; = [ ]. "
    "Zwróć tylko JSON {\"zadania\":[{\"n\":1,\"pyta\":\"…\"}]}.\n")


def needs_fields(task):
    """Czy otwarte zadanie właściciela nie ma jeszcze pól (`pyta:`) i może ich potrzebować."""
    d = task.get("detail") or {}
    return (task.get("state") != "done" and task.get("executor") == "ty" and task.get("kind") != "publikacja"
            and not task.get("needsYou") and not task.get("counter") and not d.get("asks")
            and not d.get("branch") and not str(task.get("file") or "").startswith("kampanie/"))


def _now():
    return datetime.datetime.now().isoformat(timespec="seconds")


class Fields:
    """Propozycje pól; ask(items) -> {n: "pyta" albo ""} albo None (model niedostępny), domyślnie Manager.ask_fields."""

    def __init__(self, runs_dir, load, folder_of, ask, write_lock):
        self.path = os.path.join(runs_dir, STATE_FILE)
        self.load, self.folder_of, self.ask, self.write_lock = load, folder_of, ask, write_lock
        self._lock = threading.Lock()
        self._busy = set()

    # ---------- stan ----------
    def state(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                s = json.load(f)
        except (OSError, ValueError):
            s = {}
        s = s if isinstance(s, dict) else {}
        for k in ("tasks", "failed"):
            if not isinstance(s.get(k), dict):
                s[k] = {}
        return s

    def _save(self, s):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        projekt.write_atomic(self.path, json.dumps(s, ensure_ascii=False, indent=1) + "\n")

    def decided(self, task, s=None):
        return projekt.task_key(task) in (s or self.state())["tasks"]

    def _due(self, task, s):
        k = projekt.task_key(task)
        if k in s["tasks"] or k in self._busy:
            return False
        try:
            at = datetime.datetime.fromisoformat(str(s["failed"].get(k) or ""))
        except ValueError:
            return True
        return (datetime.datetime.now() - at).total_seconds() >= RETRY_S

    # ---------- propozycja ----------
    def propose(self, tasks, data):
        """Pola dla zadań bez `pyta:` (jedno wywołanie modelu na BATCH zadań). Zwraca [{task, asks}] dla zadań
        z decyzją (asks "" = bez pól) albo None, gdy model nie odpowiedział."""
        with self._lock:
            s = self.state()
            todo = [t for t in tasks if needs_fields(t) and self._due(t, s)]
            self._busy.update(projekt.task_key(t) for t in todo)
        out, failed = [], False
        try:
            for i in range(0, len(todo), BATCH):
                part = todo[i:i + BATCH]
                answer = self.ask(self.items(part, data))
                if answer is None:
                    failed = True
                    self._mark_failed(part)
                    continue
                for n, t in enumerate(part, 1):
                    try:
                        asks = projekt.asks_value(str(answer.get(n) or ""), strict=False)
                    except ValueError:
                        asks = ""
                    out.append({"task": t, "asks": asks})
                    self._apply(t, asks)
        finally:
            with self._lock:
                self._busy.difference_update(projekt.task_key(t) for t in todo)
        return None if failed and not out else out

    @staticmethod
    def items(tasks, data=None):
        """Dane zadań dla modelu: tytuł, cel, warunek, kroki i zadania, które czekają na to zadanie (`po:`)."""
        out = []
        for n, t in enumerate(tasks, 1):
            d = t.get("detail") or {}
            later = [u.get("title") for u in t.get("unlocks") or [] if isinstance(u, dict) and u.get("title")]
            out.append({"n": n, "tytuł": t.get("title"), "cel": d.get("goal") or "", "gotowe gdy": d.get("doneWhen") or "",
                        "kroki": [s.get("text") for s in d.get("steps") or []][:8], "potem": later[:4]})
        return out

    def _mark_failed(self, tasks):
        with self._lock:
            s = self.state()
            for t in tasks:
                s["failed"][projekt.task_key(t)] = _now()
            self._save(s)

    def _apply(self, task, asks):
        """Zapis decyzji: `pyta:` pod zadaniem (gdy są pola) i wpis w stanie. Zadanie zmienione od odczytu: bez zapisu."""
        written = False
        if asks:
            folder = self.folder_of(task["project"])
            try:
                with self.write_lock:
                    cur = next((x for x in projekt.read_project(folder, task["project"])["tasks"]
                                if x["file"] == task["file"] and x["title"] == task["title"]), None) if folder else None
                    if cur and needs_fields(cur):
                        written = projekt.set_detail(folder, cur["file"], cur["line"], cur["title"], "pyta", asks)
            except (OSError, ValueError):
                written = False
            if not written:
                return False
        with self._lock:
            s = self.state()
            s["tasks"][projekt.task_key(task)] = {"at": _now(), "asks": asks}
            s["failed"].pop(projekt.task_key(task), None)
            self._save(s)
        return True

    def for_task(self, task_id, title):
        """POST /api/task/pola: propozycja dla jednego zadania. (kod, komunikat, {"asks"})."""
        data, _ = self.load()
        t = next((x for x in data["tasks"] if x["id"] == str(task_id)), None)
        if not t or t["title"] != str(title or ""):
            return 409, "Plik zmienił się od ostatniego odczytu. Odświeżam listę."
        if t["detail"].get("asks"):
            return 200, "", {"asks": "; ".join(projekt.field_text(f) for f in t["detail"].get("fields") or []), "done": True}
        s = self.state()
        if projekt.task_key(t) in s["tasks"]:
            return 200, "", {"asks": s["tasks"][projekt.task_key(t)].get("asks", ""), "done": True}
        if not needs_fields(t):
            return 200, "", {"asks": "", "done": True}
        got = self.propose([t], data)
        if not got:
            return 503, "Nie udało się teraz przygotować pól. Zadanie zamkniesz przyciskiem Zrobione."
        return 200, "", {"asks": got[0]["asks"], "done": True}

    # ---------- przejście ----------
    def migrate(self):
        """Jednorazowe przejście: pola dla otwartych zadań właściciela we wszystkich projektach. True, gdy skończone."""
        s = self.state()
        if (s.get("migration") or {}).get("done"):
            return True
        data, _ = self.load()
        if data.get("projectsSource") != "registry":
            return False
        names = {p["id"]: p.get("name") or p["id"] for p in data.get("projects", [])}
        cands = [t for t in data["tasks"] if needs_fields(t)]
        got = self.propose(cands, data)
        if got is None:
            return False
        with self._lock:
            s = self.state()
            left = [t for t in cands if projekt.task_key(t) not in s["tasks"]]
            m = s.get("migration") if isinstance(s.get("migration"), dict) else {"added": [], "checked": 0}
            m["added"] = m.get("added", []) + [{"project": names.get(g["task"]["project"], g["task"]["project"]),
                                               "title": g["task"]["title"], "asks": g["asks"]} for g in got if g["asks"]]
            m["checked"] = int(m.get("checked") or 0) + len(got)
            m["at"] = _now()
            m["done"] = not left
            s["migration"] = m
            self._save(s)
        return m["done"]

    def migration_loop(self, ready, sleep):
        """Wątek przy starcie: czeka MIGRATION_DELAY_S, potem próbuje przejścia do skutku (co MIGRATION_RETRY_S)."""
        sleep(MIGRATION_DELAY_S)
        while True:
            try:
                if ready() and self.migrate():
                    return
            except Exception:  # noqa: BLE001  (przejście nie może zatrzymać panelu)
                pass
            sleep(MIGRATION_RETRY_S)

    def summary(self):
        """Wynik przejścia dla panelu (Serwer): {"done", "at", "checked", "added": [{project, title, asks}]}."""
        m = self.state().get("migration")
        return m if isinstance(m, dict) else {}
