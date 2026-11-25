"""Jednorazowe naprawy wykonywane przez panel po starcie (konto panelu, bez ręcznych kroków na serwerze).

Każda naprawa ma id; wykonana albo nie do zastosowania trafia do `naprawy` w stan.json i nie wraca. Naprawa sama
sprawdza, czy jej warunki są spełnione (rekordy, gałęzie, pliki); niczego nie usuwa (zmiany zatwierdza albo zostawia).

2026-11-25-oprogramowani: zadanie strony „Strona: poprawki po punkcie kontrolnym 1…” przerwane wdrożeniem panelu
(uruchomienie 20261125-172031-0002, commit na gałęzi agenta) i niezatwierdzone zmiany w repozytorium strony, które
zrobiło zadanie projektu głównego (20261125-084246-e47f) w głównym katalogu repozytorium części. Panel: zatwierdza te
zmiany z opisem, scala gałąź poprawek, zamyka zadanie `[x]` z `wynik:` i przebudowuje podgląd. Konflikt przy scalaniu:
zadanie strony dla agenta (na gałęzi poprawek) zamiast zgadywania.
"""
import os
import threading

import agents as _agents

OPRO = {"id": "2026-11-25-oprogramowani", "run": "20261125-172031-0002", "source": "20261125-084246-e47f",
        "merge_task": "Strona: scal poprawki po punkcie kontrolnym 1 z bieżącą wersją strony"}


def _log(text):
    _agents.log("Naprawa: %s" % text)


def opro_fix(m, spec=OPRO):
    """"done" (wykonana), "skip" (nie dotyczy tego panelu) albo "retry" (np. agent pracuje w projekcie)."""
    rec = m.get(spec["run"])
    if not rec or rec.get("kind") != "task" or not rec.get("branch"):
        return "skip"
    if rec.get("merged") or rec.get("state") in _agents.LIVE:
        return "skip" if rec.get("merged") else "retry"
    pid, branch, base = rec["project"], rec["branch"], rec.get("base") or ""
    data, index = m.load_projects(resolve=False)
    folder = index.get(pid)
    top = m._git_top(folder) if folder else ""
    if not top or not base:
        return "skip"
    if _agents.git_run(top, ["rev-parse", "--verify", "-q", "refs/heads/" + branch], timeout=15)[0] != 0:
        return "skip"
    task = next((t for t in data["tasks"] if t["project"] == pid and t["title"] == rec["title"]), None)
    if not task or task["state"] == "done":
        return "skip"
    if m.has_live(pid):
        return "retry"
    # 1. zmiany w głównym katalogu repozytorium strony: zatwierdzić z opisem, gdy wszystkie pochodzą od zadania źródłowego
    import kopie
    dirty = kopie._dirty(top) or []
    if dirty:
        src = m.get(spec["source"]) or {}
        found = {f for s in m.dirty_sources(top, [p for _, p in dirty]) if s["runId"] == spec["source"]
                 for f in s["files"]}
        if not src or {p for _, p in dirty} - found:
            _log("%s: niezatwierdzone zmiany nie pochodzą (wszystkie) z zadania %s; zostają do decyzji właściciela "
                 "(Kod i pliki)" % (spec["id"], spec["source"]))
            return "retry"
        msg = ("Zmiany agenta z zadania „%s” (%s, uruchomienie %s): miejsca na zdjęcia, LinkedIn, dane firmy i film.\n\n"
               "Agent pisał w głównym katalogu repozytorium strony zamiast na swojej gałęzi; zatwierdził panel "
               "(naprawa %s)." % (src.get("title") or "", src.get("projectName") or src.get("project") or "",
                                  spec["source"], spec["id"]))
        with m._git_lock, kopie.folder_lock(top):
            ok, out = kopie.commit_dirty(top, msg)
        if not ok:
            _log("%s: commit nieudany: %s" % (spec["id"], out))
            return "skip"
        _log("%s: zatwierdzono zmiany z %s jako %s" % (spec["id"], spec["source"], out))
    # 2. scalenie gałęzi poprawek
    code, err, extra = m.merge(rec["id"])
    if code != 200:
        if "Konflikt" in err:
            return _merge_task(m, rec, folder, spec, err)
        _log("%s: nie scalono: %s" % (spec["id"], err))
        return "skip"
    sha = extra.get("commit", "")[:8]
    # 3. zamknięcie zadania z wynikiem z gałęzi (zaraz, żeby Automat nie uruchomił go ponownie), potem podgląd
    p = next((x for x in data["projects"] if x["id"] == pid), {})
    changes = rec.get("changes") or []
    added = sum(int(c.get("added") or 0) for c in changes)
    removed = sum(int(c.get("removed") or 0) for c in changes)
    files = ", ".join(os.path.basename(c["path"]) for c in changes[:6]) + (", …" if len(changes) > 6 else "")
    wynik = ("poprawki zatwierdzone przed przerwaniem pracy (gałąź %s) scalone do %s (%s): %d plików, +%d/−%d (%s); "
             "zmiany oceniasz w podglądzie strony" % (branch, base, sha, len(changes), added, removed, files))
    _close(m, pid, folder, rec["title"], {"wynik": wynik}, done=True)
    build = m.site.build_now(pid) if p.get("site") else {"state": "ok"}
    if build.get("state") != "ok":
        _close(m, pid, folder, rec["title"], {"zostało": "podgląd strony się nie zbudował: %s" % _agents._short(
            build.get("error") or "błąd budowania", 200)})
    with m._lock:
        live = m._runs.get(rec["id"])
        if live is not None:
            live["recovered"] = "naprawa"
            live["steps"] = (list(live.get("steps") or []) + [
                {"t": _agents.now_iso()[11:19], "text": "Panel dokończył: scalono %s, zadanie zamknięte" % sha}])[-30:]
            m._save(live)
    _log("%s: scalono %s, podgląd: %s" % (spec["id"], sha, build.get("state")))
    return "done"


def _close(m, pid, folder, title, details, done=False):
    """Szczegóły zadania (wynik:, zostało:) i stan zrobione, pod blokadą zapisu."""
    def find():
        return next((t for t in m.load_projects(resolve=False)[0]["tasks"]
                     if t["project"] == pid and t["title"] == title), None)
    with m.write_lock:
        for key, value in details.items():
            task = find()
            if task:
                m.projekt.set_detail(folder, task["file"], task["line"], title, key, value)
        task = find()
        if task and done:
            m.projekt.update_task(folder, task["file"], task["line"], title, {"state": "done", "needsYou": ""})


def _merge_task(m, rec, folder, spec, err):
    """Konflikt: zadanie strony dla agenta na gałęzi poprawek (scal bazę, rozstrzygnij według poprawek)."""
    data, _ = m.load_projects(resolve=False)
    if any(t["project"] == rec["project"] and t["title"] == spec["merge_task"] for t in data["tasks"]):
        return "done"
    detail = {"cel": "Scal gałąź %s z bieżącą wersją strony (%s): w katalogu roboczym `git merge %s`, konflikty "
                     "rozstrzygnij według poprawek po punkcie kontrolnym 1; miejsce na film „Kto to robi” zostaje, "
                     "jeśli nie koliduje z poprawkami. %s" % (rec["branch"], rec["base"], rec["base"], err),
              "gotowe gdy": "na gałęzi jest commit scalenia bez znaczników konfliktu, strona się buduje, zrzuty "
                            "390 i 1440 px obejrzane",
              "gałąź": rec["branch"]}
    code, why, _ = m.site._task(rec["project"], folder, spec["merge_task"], detail)
    _log("%s: konflikt, zadanie dla agenta (%s %s)" % (spec["id"], code, why))
    return "done"


FIXES = [(OPRO["id"], opro_fix)]


def run(m, fixes=None):
    """Wykonuje naprawy, których nie ma jeszcze w stan.json (`naprawy`)."""
    with m._lock:
        done = set(m._state.get("naprawy") or [])
    for fid, fn in fixes or FIXES:
        if fid in done:
            continue
        try:
            result = fn(m)
        except Exception as e:  # noqa: BLE001  (naprawa nie może zatrzymać panelu)
            _log("%s: błąd %s" % (fid, e))
            result = "retry"
        if result in ("done", "skip"):
            with m._lock:
                m._state["naprawy"] = sorted(set(m._state.get("naprawy") or []) | {fid})
                m._save_state()


def start(m, delay=20):
    """Naprawy w tle, po starcie panelu (po podjęciu przerwanych uruchomień)."""
    t = threading.Timer(delay, run, [m])
    t.daemon = True
    t.start()
    return t
