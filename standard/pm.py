#!/usr/bin/env python3
"""Raport PM: stan wszystkich projektów w jednym miejscu, liczony z plików standardu.

  python3 pm.py            raport tekstowy
  python3 pm.py --json     te same fakty jako JSON (dla agenta w roli PM)

Projekty pochodzą z rejestru ../projekty.json i z decyzji zbieracza (system/); gdy obu brak, z projektów przykładowych panelu.
Reguły są te same, co w panelu (zakładka Raport) i opisane w STANDARD.md, sekcja „Raport PM”.
Stan uruchomień agentów (zadania w toku, od kiedy zadanie jest w toku albo czeka na odbiór) pochodzi z folderu
../uruchomienia (albo PANEL_RUNS_DIR), który prowadzi panel; bez niego tych ryzyk nie ma.
Stan kontroli serwera (pole „sprawdza:” zadań, lista „do zamknięcia”) pochodzi z pliku PANEL_ZDROWIE_STAN
(domyślnie /home/panel/.zdrowie-stan); bez niego pomijane są kontrole serwera, kontrole „plik <ścieżka>” zostają.
Tylko odczyt. Tylko biblioteka standardowa Pythona.
"""
import argparse
import datetime
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import projekt  # noqa: E402

SAMPLES = os.path.join(os.path.dirname(HERE), "dashboard", "przyklad")
RUNS = os.path.join(os.path.dirname(HERE), "uruchomienia")
QUESTION_MINUTES = 2
REL = re.compile(r"^([+-]\d+)$")
DNI = ["poniedziałek", "wtorek", "środa", "czwartek", "piątek", "sobota", "niedziela"]
MD = ["stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca", "lipca", "sierpnia", "września",
      "października", "listopada", "grudnia"]
STAGE = {"late": ("■", "po terminie"), "you": ("◆", "czeka na Ciebie"), "risk": ("▲", "zagrożony"),
         "ok": ("●", "w normie"), "done": ("✓", "zrobione"), "": ("·", "bez terminu")}
WORST = ["late", "risk", "you", "ok", "done", ""]


def is_day(value):
    return bool(re.match(r"^\d{4}-\d\d-\d\d$", value or ""))


def load(today):
    """Wszystkie projekty z datami bezwzględnymi."""
    folders, source = [(f, dec) for f, _, dec in projekt.all_folders()], "registry"   # rejestr i zbieracz
    if not folders:
        folders, source = [(p, None) for p in sorted(glob.glob(os.path.join(SAMPLES, "*"))) if os.path.isdir(p)], "sample"

    def day(value):
        m = REL.match(value or "")
        return (today + datetime.timedelta(days=int(m.group(1)))).isoformat() if m else value

    out = {"projects": [], "stages": [], "tasks": [], "campaigns": [], "source": source, "roots": {}}
    seen = set()
    for folder, decision in folders:
        base = pid = projekt.slug(os.path.basename(folder))
        n = 2
        while pid in seen:
            pid, n = "%s-%d" % (base, n), n + 1
        seen.add(pid)
        d = projekt.read_project(folder, pid, decision)
        out["roots"][pid] = folder
        out["projects"].append(d["project"])
        for k in ("stages", "tasks", "campaigns"):
            out[k] += d[k]
    projekt.link_parts(out["projects"], out["roots"])     # część projektu: nazwa „Główny · Część”
    for item in out["stages"] + out["tasks"]:
        item["date"] = day(item["date"])
    for t in out["tasks"]:
        for u in t.get("unlocks") or []:
            u["date"] = day(u.get("date", ""))
    for c in out["campaigns"]:
        c["start"], c["end"] = day(c["start"]), day(c["end"])
    for p in out["projects"]:
        if p.get("nextStep"):
            p["nextStep"]["date"] = day(p["nextStep"]["date"])
        for q in p.get("questions") or []:
            q["date"] = day(q.get("date", ""))
    return out


def runs_info(runs_dir=None):
    """Stan z folderu uruchomień panelu: ({klucz zadania: {"s", "d"}}, {klucze z agentem w toku}, {klucz: dzień
    ostatniego zakończenia}). Klucz zadania to projekt|plik|tytuł. Brak folderu albo plików to puste wyniki."""
    runs_dir = runs_dir or os.environ.get("PANEL_RUNS_DIR", "").strip() or RUNS
    since, live, ended = {}, set(), {}
    try:
        names = os.listdir(runs_dir)
    except OSError:
        return since, live, ended
    for name in names:
        if not name.endswith(".json"):
            continue
        try:
            with open(os.path.join(runs_dir, name), encoding="utf-8") as f:
                rec = json.load(f)
        except (OSError, ValueError):
            continue
        if not isinstance(rec, dict):
            continue
        if name == "stan.json":
            raw = rec.get("since")
            since = {k: v for k, v in raw.items() if isinstance(v, dict)} if isinstance(raw, dict) else {}
            continue
        if rec.get("kind") != "task":
            continue
        key = "%s|%s|%s" % (rec.get("project", ""), rec.get("file", ""), rec.get("title", ""))
        if rec.get("state") in ("queued", "running"):
            live.add(key)
        end = str(rec.get("endedAt") or "")[:10]
        if is_day(end) and end > ended.get(key, ""):
            ended[key] = end
    return since, live, ended


def stage_state(stage, tasks, today):
    """Stan etapu z terminem; kolejność reguł jak w panelu."""
    if not is_day(stage["date"]):
        return ""
    mine = [t for t in tasks if t["stage"] == stage["id"]]
    left = [t for t in mine if t["state"] not in projekt.CLOSED_TASK_STATES]
    days = (datetime.date.fromisoformat(stage["date"]) - today).days
    if stage["closed"] or (mine and not left):
        return "done"
    if days < 0:
        return "late"
    if left and all(t["executor"] == "ty" or t["needsYou"] for t in left):
        return "you"
    if len(left) > days:
        return "risk"
    return "ok"


DURATION_NOTE = re.compile(r"^trwa\s*:\s*(\d+)\s*dni\b", re.I)
DURATION_TITLE = re.compile(r"\b(\d+)\s*dni\b", re.I)


def duration_days(t):
    """Dni trwania zadania: notatka „trwa: N dni” pod zadaniem, inaczej „N dni” w tytule, inaczej 0."""
    for note in (t.get("detail") or {}).get("notes") or []:
        m = DURATION_NOTE.match(note)
        if m:
            return int(m.group(1))
    m = DURATION_TITLE.search(t.get("title") or "")
    return int(m.group(1)) if m else 0


def stage_end(stage, tasks):
    """(najpóźniejszy koniec otwartych zadań etapu z datą: data + dni trwania, zadanie) albo ("", None)."""
    best, pick = "", None
    for t in tasks:
        if t["stage"] != stage["id"] or t["state"] in projekt.CLOSED_TASK_STATES or not is_day(t["date"]):
            continue
        end = (datetime.date.fromisoformat(t["date"]) + datetime.timedelta(days=duration_days(t))).isoformat()
        if end > best:
            best, pick = end, t
    return best, pick


def over_capacity(items, limit):
    """Zadania do przesunięcia, gdy suma minut dzisiejszych spraw właściciela przekracza limit: najpierw najniższy
    priorytet projektu (najwyższa liczba), potem najpóźniejsza data i najdłuższe, aż suma zmieści się w limicie."""
    total = sum(t["minutes"] for t in items)
    move = []
    for t in sorted((t for t in items if t["minutes"]),
                    key=lambda t: (t["priority"], t["date"] if is_day(t["date"]) else "", t["minutes"]), reverse=True):
        if total <= limit:
            break
        move.append(t)
        total -= t["minutes"]
    return move


def waiting_groups(rows):
    """„Czeka na Ciebie” pogrupowane po Twoim zadaniu-poprzedniku: [{"project", "title", "date", "where", "count",
    "tasks": [tytuły], "nearest": {"title", "date"}}]; najbliższe to zależne zadanie z najwcześniejszą datą
    (bez daty na końcu). Kolejność: więcej wstrzymanych zadań, potem data poprzednika."""
    groups = {}
    for r in rows:
        g = groups.setdefault((r["project"], r["afterWhere"]), {
            "project": r["project"], "title": r["after"], "date": r["afterDate"], "where": r["afterWhere"],
            "count": 0, "tasks": [], "nearest": None})
        g["count"] += 1
        g["tasks"].append(r["title"])
        if g["nearest"] is None or (is_day(r["date"]) and (not is_day(g["nearest"]["date"])
                                                           or r["date"] < g["nearest"]["date"])):
            g["nearest"] = {"title": r["title"], "date": r["date"]}
    return sorted(groups.values(), key=lambda g: (-g["count"], g["date"] if is_day(g["date"]) else "9999", g["title"]))


def today_key(b):
    """Kolejność „Dziś” i „Jutro”: po terminie najpierw (najstarsza data), potem więcej odblokowanych zadań
    (unlockCount), potem priorytet projektu, tytuł."""
    late = bool(b.get("late"))
    return (0 if late else 1, b["date"] if late and is_day(b["date"]) else "", -b.get("unlockCount", 0),
            b["priority"], b["title"])


def facts(today=None, runs_dir=None):
    today = today or datetime.date.today()
    key = today.isoformat()
    tomorrow = (today + datetime.timedelta(days=1)).isoformat()
    week = (today + datetime.timedelta(days=7)).isoformat()
    d = load(today)
    names = {p["id"]: p["name"] for p in d["projects"]}
    prio = {p["id"]: p.get("priority", projekt.PRIORITY_DEFAULT) for p in d["projects"]}
    limit = projekt.day_minutes()
    stages = {s["id"]: s for s in d["stages"]}
    by_id = {t["id"]: t for t in d["tasks"]}
    for s in d["stages"]:
        s["state"] = stage_state(s, d["tasks"], today)
    open_tasks = [t for t in d["tasks"] if t["state"] not in projekt.CLOSED_TASK_STATES]
    quiet = {p["id"] for p in d["projects"] if p.get("state") in projekt.QUIET_STATES}
    since, live, ended = runs_info(runs_dir) if d["source"] == "registry" else ({}, set(), {})
    health = projekt.read_health()
    for t in d["tasks"]:
        if t.get("check"):
            t["check"] = projekt.check_task(t, health, d["roots"].get(t["project"]))

    def late(t):
        s = stages.get(t["stage"])
        return (is_day(t["date"]) and t["date"] < key) or bool(s and s["state"] == "late")

    def need(t):
        n = projekt.owner_needs(t)
        return n[0] if n else ""

    def brief(t):
        s = stages.get(t["stage"])
        return {"project": names.get(t["project"], t["project"]), "priority": prio.get(t["project"], 3),
                "title": t["title"], "state": t["state"],
                "kind": t["kind"], "executor": t["executor"], "date": t["date"], "minutes": t["minutes"],
                "needsYou": need(t), "blocked": t["blocked"], "channel": t["channel"],
                "stage": s["title"] if s else t["group"], "where": "%s:%d" % (t["file"], t["line"]),
                "unlockCount": t.get("unlockCount", 0), "late": late(t)}

    def stage_brief(s):
        mine = [t for t in d["tasks"] if t["stage"] == s["id"] and t["state"] != "cancelled"]
        return {"project": names.get(s["project"], s["project"]), "title": s["title"], "date": s["date"],
                "state": s["state"], "done": sum(1 for t in mine if t["state"] == "done"), "total": len(mine)}

    def question(p, q):
        return {"project": p["name"], "priority": prio.get(p["id"], 3), "title": q["text"], "state": "todo",
                "kind": "pytanie", "executor": "ty", "date": q["date"], "minutes": QUESTION_MINUTES, "needsYou": "",
                "blocked": "", "channel": "", "stage": projekt.QUESTIONS_TITLE, "where": "KARTA.md:%d" % q["line"],
                "proposal": q.get("proposal", "")}

    you = [t for t in open_tasks if t["project"] not in quiet and projekt.for_owner(t)]
    questions = [(p, q) for p in d["projects"] if p["id"] not in quiet
                 for q in p.get("questions") or [] if not q.get("answer")]
    decided = [t for t in you if need(t) or (is_day(t["date"]) and t["date"] <= tomorrow)]
    items = [(brief(t), late(t)) for t in decided]
    items += [(question(p, q), is_day(q["date"]) and q["date"] < key) for p, q in questions]
    decisions = sorted(items, key=lambda x: (x[0]["priority"], x[0]["date"] or "9999", x[0]["title"]))
    top = [b for b, _ in sorted(decisions, key=lambda x: importance(x[0], x[1], key))[:TOP]]
    active = {p["id"] for p in d["projects"] if p.get("state") == "active"}
    # projekt z częściami to jeden projekt: następny krok, lista projektów i braki liczone dla całości
    group = {p["id"]: p.get("partOf") or p["id"] for p in d["projects"]}
    members = {}
    for p in d["projects"]:
        members.setdefault(group[p["id"]], []).append(p)
    no_next = [p for p in d["projects"] if not p.get("partOf") and any(m["id"] in active for m in members[p["id"]])
               and not any(group.get(t["project"]) == p["id"] and is_day(t["date"]) and t["date"] <= week
                           for t in open_tasks)]
    no_date = [s for s in d["stages"] if s["project"] in active and not is_day(s["date"])
               and not projekt.stage_done(s, d["tasks"])]

    order, waiting_you = [], []
    for t in open_tasks:
        if t["project"] in quiet:
            continue
        for w in t.get("waitingFor") or []:
            pred = by_id.get(w.get("id"))
            if not pred or pred["state"] in projekt.CLOSED_TASK_STATES:
                continue
            if not is_day(pred["date"]) or (is_day(t["date"]) and t["date"] < pred["date"]):
                order.append(dict(brief(t), after=pred["title"], afterDate=pred["date"]))
            if pred["executor"] == "ty":
                waiting_you.append(dict(brief(t), after=pred["title"], afterDate=pred["date"],
                                        afterWhere="%s:%d" % (pred["file"], pred["line"])))

    stalled, review = [], []
    for t in open_tasks:
        k = projekt.task_key(t)
        status = projekt.task_status(t)
        seen = since.get(k) if isinstance(since.get(k), dict) and since[k].get("s") == status else None
        day_ = (seen or {}).get("d") or ended.get(k, "")
        if t["project"] in quiet or not status or not day_:
            continue
        is_stalled, is_review = projekt.state_flags(t, day_, k in live, today)
        if is_stalled:
            stalled.append(dict(brief(t), since=day_))
        elif is_review:
            review.append(dict(brief(t), since=day_))
    questions_late = [question(p, q) for p, q in questions if is_day(q["date"]) and q["date"] < key]
    to_close = [dict(brief(t), check=t["check"]) for t in open_tasks if t["project"] not in quiet
                and isinstance(t.get("check"), dict) and t["check"].get("ok") is True]
    closable = {(t["project"], t["where"]) for t in to_close}

    no_slack = []
    for s in d["stages"]:
        if s["state"] in ("", "late", "done"):
            continue
        end, t = stage_end(s, d["tasks"])
        if end and end >= s["date"]:
            no_slack.append(dict(stage_brief(s), end=end, task=t["title"], days=duration_days(t)))

    late_stages = {s["id"] for s in d["stages"] if s["state"] == "late"}
    mine_today = [brief(t) for t in you if (is_day(t["date"]) and t["date"] <= key) or t["stage"] in late_stages]
    today_minutes = sum(t["minutes"] for t in mine_today)
    capacity = {"minutes": today_minutes, "limit": limit, "over": today_minutes > limit,
                "move": over_capacity(mine_today, limit) if today_minutes > limit else []}

    projects = []
    for p in d["projects"]:
        if p.get("partOf"):
            continue
        ids = {m["id"] for m in members[p["id"]]}
        mine = [t for t in d["tasks"] if t["project"] in ids and t["kind"] != "publikacja" and t["state"] != "cancelled"]
        st = [s for s in d["stages"] if s["project"] in ids]
        upcoming = sorted((s for s in st if s["state"] not in ("", "done")), key=lambda s: s["date"])
        worst = min((s["state"] for s in st), key=WORST.index, default="")
        projects.append({"id": p["id"], "name": p["name"], "priority": prio[p["id"]], "done": sum(1 for t in mine if t["state"] == "done"),
                         "total": len(mine), "state": worst, "next": stage_brief(upcoming[0]) if upcoming else None,
                         "docsOk": sum(m["docsOk"] for m in members[p["id"]]),
                         "docsTotal": sum(m["docsTotal"] for m in members[p["id"]]),
                         "parts": [m["partLabel"] for m in members[p["id"]] if m.get("partOf")],
                         "gaps": [{"file": (m["partLabel"] + ": " if m.get("partOf") else "") + x["file"],
                                   "gaps": x["gaps"]} for m in members[p["id"]] for x in m["docs"]
                                  if x["status"] != "ok"]})
    pubs = [t for t in open_tasks if t["kind"] == "publikacja" and is_day(t["date"]) and t["date"] <= week]
    counts = {"you": len(you) + len(questions),
              "risk": sum(1 for s in d["stages"] if s["state"] == "risk"),
              "blocked": sum(1 for t in open_tasks if t["state"] == "blocked"),
              "noNextStep": len(no_next), "stagesNoDate": len(no_date), "noSlack": len(no_slack),
              "overCapacity": 1 if capacity["over"] else 0, "toClose": len(to_close)}
    counts.update(projekt.owner_counts(d["projects"], d["stages"], d["tasks"], today))   # youToday… i late: jedno źródło z panelem
    out = {
        "today": key, "source": d["source"], "dayMinutes": limit,
        "counts": counts,
        "decisions": [b for b, _ in decisions],
        "top": top,
        "topMinutes": sum(t["minutes"] for t in top),
        "noNextStep": [{"project": p["name"], "nextStep": p.get("nextStep")} for p in no_next],
        "stagesNoDate": [stage_brief(s) for s in no_date],
        "stagesLate": [stage_brief(s) for s in d["stages"] if s["state"] == "late"],
        "stagesRisk": [stage_brief(s) for s in d["stages"] if s["state"] == "risk"],
        "stagesNoSlack": no_slack,
        "capacity": capacity,
        "blocked": [brief(t) for t in open_tasks if t["state"] == "blocked"],
        "order": order,
        "waitingOnYou": waiting_you,
        "waitingOnYouBy": waiting_groups(waiting_you),
        "toClose": to_close,
        "stalled": stalled,
        "reviewWaiting": review,
        "questionsLate": questions_late,
        "late": [brief(t) for t in open_tasks if late(t)],
        "today_tasks": sorted((b for b in (brief(t) for t in open_tasks if t["date"] == key)
                               if (b["project"], b["where"]) not in closable), key=today_key),
        "tomorrow_tasks": sorted((brief(t) for t in open_tasks if t["date"] == tomorrow), key=today_key),
        "publications": [brief(t) for t in sorted(pubs, key=lambda t: t["date"])],
        "projects": projects,
        "campaigns": [{"project": names.get(c["project"], c["project"]), "name": c["name"], "state": c["state"],
                       "metric": c["metric"], "result": c["result"], "target": c["target"], "end": c["end"],
                       "progress": round(100 * c["result"] / c["target"]) if c["target"] and c["result"] is not None
                       else None}
                      for c in d["campaigns"]],
    }
    if d.get("source") == "registry":           # wyniki marketingu (dashboard/klienci.py); dane klientów poza gitem, tu tylko sumy
        try:
            sys.path.insert(0, os.path.join(HERE, "..", "dashboard"))
            import klienci
            for c, src in zip(out["campaigns"], d["campaigns"]):
                c["marketing"] = klienci.marketing_numbers(src["project"], src.get("start") or "", src.get("end") or "")
        except (ImportError, OSError, ValueError):
            pass
    return out


TOP = 3
NEED_RANK = {"zgoda": 0, "pytanie": 1, "odbiór": 2}


def importance(t, is_late, today):
    """Kolejność najważniejszych decyzji: po terminie (najstarsze najpierw), więcej odblokowanych zadań (unlockCount),
    priorytet projektu (1 pierwszy), najbliższa data, zgoda, pytanie, odbiór, krótsze najpierw."""
    need = "pytanie" if t.get("kind") == "pytanie" else t["needsYou"]
    date = t["date"] if is_day(t["date"]) else "9999"
    return (0 if is_late else 1, date if is_late else "", -t.get("unlockCount", 0),
            t.get("priority", projekt.PRIORITY_DEFAULT), date, NEED_RANK.get(need, 3), t["minutes"] or 9999, t["title"])


def days_since(value, today):
    return (today - datetime.date.fromisoformat(value)).days


def minutes_text(m):
    return "%d min" % m if m else "czas nieznany"


def when(value, today):
    if not is_day(value):
        return "bez daty"
    n = (datetime.date.fromisoformat(value) - today).days
    return {0: "dziś", 1: "jutro", -1: "wczoraj"}.get(n, "za %d dni" % n if n > 0 else "%d dni temu" % -n)


def text(f):
    today = datetime.date.fromisoformat(f["today"])
    c = f["counts"]
    out = ["Raport PM · %s, %d %s %d%s" % (DNI[today.weekday()], today.day, MD[today.month - 1], today.year,
                                          " · projekty przykładowe" if f["source"] == "sample" else ""),
           "Wymaga Ciebie %d (dziś %d, w tym po terminie %d, 7 dni %d, później %d) · Po terminie wszystkie %d · Zagrożone etapy %d · Zablokowane %d"
           " · Bez następnego kroku %d · Etapy bez terminu %d · Bez zapasu %d%s"
           % (c["you"], c["youToday"], c["youLate"], c["youWeek"], c["youLater"], c["late"], c["risk"], c["blocked"],
              c["noNextStep"], c["stagesNoDate"], c["noSlack"],
              " · Do zamknięcia %d" % c["toClose"] if c.get("toClose") else "")]

    def block(title, rows):
        if rows:
            out.extend(["", title] + ["  " + r for r in rows])

    def task(t, extra=""):
        return "%s · %s%s" % (t["project"], t["title"], extra)

    def waiting(g):
        if g["count"] == 1:
            return "◆ czeka na Ciebie: %s · %s · po Twoim zadaniu „%s”" % (g["project"], g["tasks"][0], g["title"])
        n = g["nearest"]
        return "◆ czeka na Ciebie: %s · %s wstrzymuje %d zadań (najbliższe: %s, %s)" % (
            g["project"], g["title"], g["count"], n["title"], when(n["date"], today))

    def stamp(at):
        return str(at).replace("T", " ")[:16]

    def decision(t):
        label = "pytanie" if t["kind"] == "pytanie" else t["needsYou"] or "Twoje"
        row = "◆ %-7s %s" % (label, task(t, " (%s, %s)" % (when(t["date"], today), minutes_text(t["minutes"]))))
        return row + (" · propozycja: %s" % t["proposal"] if t.get("proposal") else "")

    rest = [t for t in f["decisions"] if t not in f["top"]]
    rows = []
    if f["top"]:
        unknown = sum(1 for t in f["top"] if not t["minutes"])
        rows = ["Najważniejsze %d (%s%s):" % (len(f["top"]), minutes_text(f["topMinutes"]),
                                             "; bez czasu: %d" % unknown if unknown and f["topMinutes"] else "")] \
            + [decision(t) for t in f["top"]] + (["Pozostałe:"] if rest else []) + [decision(t) for t in rest]
    block("DECYZJE DLA CIEBIE", rows)
    block("RYZYKA",
          ["%s %s: %s · etap %s (termin %s, %d/%d)" % (STAGE[s["state"]] + (s["project"], s["title"],
                                                        when(s["date"], today), s["done"], s["total"]))
           for s in f["stagesLate"] + f["stagesRisk"]]
          + ["▲ bez zapasu: %s · etap %s (termin %s), ostatnie zadanie „%s” kończy się %s"
             % (s["project"], s["title"], s["date"], s["task"], s["end"]) for s in f["stagesNoSlack"]]
          + (["▲ ponad pojemność: Twoje sprawy na dziś %d min, limit %d min; do przesunięcia: %s"
              % (f["capacity"]["minutes"], f["capacity"]["limit"],
                 "; ".join("%s (%s, %d min)" % (task(t), "priorytet %d" % t["priority"], t["minutes"])
                           for t in f["capacity"]["move"]))] if f["capacity"]["over"] else [])
          + ["■ zablokowane: %s" % task(t, " (%s)" % t["blocked"] if t["blocked"] else "") for t in f["blocked"]]
          + ["■ pytanie po terminie: %s" % task(t, " (termin %s%s)" % (when(t["date"], today), ", propozycja: %s"
                                                                     % t["proposal"] if t.get("proposal") else ""))
             for t in f["questionsLate"]]
          + [waiting(g) for g in f["waitingOnYouBy"]]
          + ["✓ wygląda na zrobione: %s (kontrola %s%s): zamknij" % (task(t), t["check"]["key"], ", %s" % stamp(t["check"]["at"])
                                                                     if t["check"].get("at") else "")
             for t in f["toClose"]]
          + ["▲ kolejność: %s (%s) przed poprzednikiem „%s” (%s)"
             % (task(t), when(t["date"], today), t["after"], when(t["afterDate"], today)) for t in f["order"]]
          + ["▲ zawieszone: %s (w toku %d dni, bez agenta)" % (task(t), days_since(t["since"], today))
             for t in f["stalled"]]
          + ["◆ odbiór czeka %d dni: %s" % (days_since(t["since"], today), task(t)) for t in f["reviewWaiting"]]
          + ["□ bez następnego kroku: %s (brak otwartego zadania z datą w ciągu 7 dni)" % p["project"]
             for p in f["noNextStep"]]
          + ["□ etap bez terminu: %s · etap %s (%d/%d)" % (s["project"], s["title"], s["done"], s["total"])
             for s in f["stagesNoDate"]])
    block("DZIŚ", [task(t, " · " + (t["executor"] or "bez wykonawcy")) for t in f["today_tasks"]])
    block("JUTRO", [task(t, " · " + (t["executor"] or "bez wykonawcy")) for t in f["tomorrow_tasks"]])
    block("PROJEKTY", [
        "%s %-22s %2d/%-2d  %s" % (STAGE[p["state"]][0], p["name"][:22], p["done"], p["total"],
                                  "najbliższy termin: %s, %s" % (p["next"]["title"], when(p["next"]["date"], today))
                                  if p["next"] else "brak otwartych terminów")
        for p in f["projects"]])
    block("PUBLIKACJE (7 dni)", [
        "%s %s%s" % ("■" if t["date"] < f["today"] else "○", task(t),
                     " · %s, %s" % (t["channel"] or "kanał?", when(t["date"], today)))
        for t in f["publications"]])
    block("STANDARD", ["%s: dokumenty %d/%d" % (p["name"], p["docsOk"], p["docsTotal"])
                       for p in f["projects"] if p["docsOk"] < p["docsTotal"]])
    return "\n".join(out)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--rejestr")
    parser.add_argument("--tylko-rejestr", action="store_true")
    args = parser.parse_args()
    if args.rejestr:
        projekt.REGISTRY = os.path.abspath(os.path.expanduser(args.rejestr))
    data = facts()
    if args.tylko_rejestr and data["source"] != "registry":
        parser.exit(1, "Raport PM: brak projektów w rejestrze lub zbieraczu.\n")
    print(json.dumps(data, ensure_ascii=False, indent=1) if args.json else text(data))
