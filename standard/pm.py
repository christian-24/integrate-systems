#!/usr/bin/env python3
"""Raport PM: stan wszystkich projektów w jednym miejscu, liczony z plików standardu.

  python3 pm.py            raport tekstowy
  python3 pm.py --json     te same fakty jako JSON (dla agenta w roli PM)

Projekty pochodzą z rejestru ../projekty.json i z decyzji zbieracza (system/); gdy obu brak, z projektów przykładowych panelu.
Reguły są te same, co w panelu (zakładka Raport) i opisane w STANDARD.md, sekcja „Raport PM”.
Tylko odczyt. Tylko biblioteka standardowa Pythona.
"""
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

    out = {"projects": [], "stages": [], "tasks": [], "campaigns": [], "source": source}
    seen = set()
    for folder, decision in folders:
        base = pid = projekt.slug(os.path.basename(folder))
        n = 2
        while pid in seen:
            pid, n = "%s-%d" % (base, n), n + 1
        seen.add(pid)
        d = projekt.read_project(folder, pid, decision)
        out["projects"].append(d["project"])
        for k in ("stages", "tasks", "campaigns"):
            out[k] += d[k]
    for item in out["stages"] + out["tasks"]:
        item["date"] = day(item["date"])
    for c in out["campaigns"]:
        c["start"], c["end"] = day(c["start"]), day(c["end"])
    for p in out["projects"]:
        if p.get("nextStep"):
            p["nextStep"]["date"] = day(p["nextStep"]["date"])
    return out


def stage_state(stage, tasks, today):
    """Stan etapu z terminem; kolejność reguł jak w panelu."""
    if not is_day(stage["date"]):
        return ""
    mine = [t for t in tasks if t["stage"] == stage["id"]]
    left = [t for t in mine if t["state"] != "done"]
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


def facts(today=None):
    today = today or datetime.date.today()
    key = today.isoformat()
    tomorrow = (today + datetime.timedelta(days=1)).isoformat()
    week = (today + datetime.timedelta(days=7)).isoformat()
    d = load(today)
    names = {p["id"]: p["name"] for p in d["projects"]}
    stages = {s["id"]: s for s in d["stages"]}
    for s in d["stages"]:
        s["state"] = stage_state(s, d["tasks"], today)
    open_tasks = [t for t in d["tasks"] if t["state"] != "done"]

    def late(t):
        s = stages.get(t["stage"])
        return (is_day(t["date"]) and t["date"] < key) or bool(s and s["state"] == "late")

    def brief(t):
        s = stages.get(t["stage"])
        return {"project": names.get(t["project"], t["project"]), "title": t["title"], "state": t["state"],
                "kind": t["kind"], "executor": t["executor"], "date": t["date"], "minutes": t["minutes"],
                "needsYou": t["needsYou"], "blocked": t["blocked"], "channel": t["channel"],
                "stage": s["title"] if s else t["group"], "where": "%s:%d" % (t["file"], t["line"])}

    def stage_brief(s):
        mine = [t for t in d["tasks"] if t["stage"] == s["id"]]
        return {"project": names.get(s["project"], s["project"]), "title": s["title"], "date": s["date"],
                "state": s["state"], "done": sum(1 for t in mine if t["state"] == "done"), "total": len(mine)}

    you = [t for t in open_tasks if t["executor"] == "ty" or t["needsYou"]]
    decisions = [t for t in you if t["needsYou"] or (is_day(t["date"]) and t["date"] <= tomorrow)]
    decisions.sort(key=lambda t: (t["date"] or "9999", t["title"]))
    top = sorted(decisions, key=lambda t: importance(t, late(t), key))[:TOP]
    active = {p["id"] for p in d["projects"] if p.get("state") == "active"}
    no_next = [p for p in d["projects"] if p["id"] in active and not any(
        t["project"] == p["id"] and is_day(t["date"]) and t["date"] <= week for t in open_tasks)]
    no_date = [s for s in d["stages"] if s["project"] in active and not is_day(s["date"])
               and not projekt.stage_done(s, d["tasks"])]
    projects = []
    for p in d["projects"]:
        mine = [t for t in d["tasks"] if t["project"] == p["id"] and t["kind"] != "publikacja"]
        st = [s for s in d["stages"] if s["project"] == p["id"]]
        upcoming = sorted((s for s in st if s["state"] not in ("", "done")), key=lambda s: s["date"])
        worst = min((s["state"] for s in st), key=WORST.index, default="")
        projects.append({"id": p["id"], "name": p["name"], "done": sum(1 for t in mine if t["state"] == "done"),
                         "total": len(mine), "state": worst, "next": stage_brief(upcoming[0]) if upcoming else None,
                         "docsOk": p["docsOk"], "docsTotal": p["docsTotal"],
                         "gaps": [{"file": x["file"], "gaps": x["gaps"]} for x in p["docs"] if x["status"] != "ok"]})
    pubs = [t for t in open_tasks if t["kind"] == "publikacja" and is_day(t["date"]) and t["date"] <= week]
    return {
        "today": key, "source": d["source"],
        "counts": {"you": len(you), "late": sum(1 for t in open_tasks if late(t)),
                   "risk": sum(1 for s in d["stages"] if s["state"] == "risk"),
                   "blocked": sum(1 for t in open_tasks if t["state"] == "blocked"),
                   "noNextStep": len(no_next), "stagesNoDate": len(no_date)},
        "decisions": [brief(t) for t in decisions],
        "top": [brief(t) for t in top],
        "topMinutes": sum(t["minutes"] for t in top),
        "noNextStep": [{"project": p["name"], "nextStep": p.get("nextStep")} for p in no_next],
        "stagesNoDate": [stage_brief(s) for s in no_date],
        "stagesLate": [stage_brief(s) for s in d["stages"] if s["state"] == "late"],
        "stagesRisk": [stage_brief(s) for s in d["stages"] if s["state"] == "risk"],
        "blocked": [brief(t) for t in open_tasks if t["state"] == "blocked"],
        "late": [brief(t) for t in open_tasks if late(t)],
        "today_tasks": [brief(t) for t in open_tasks if t["date"] == key],
        "tomorrow_tasks": [brief(t) for t in open_tasks if t["date"] == tomorrow],
        "publications": [brief(t) for t in sorted(pubs, key=lambda t: t["date"])],
        "projects": projects,
        "campaigns": [{"project": names.get(c["project"], c["project"]), "name": c["name"], "state": c["state"],
                       "metric": c["metric"], "result": c["result"], "target": c["target"], "end": c["end"]}
                      for c in d["campaigns"]],
    }


TOP = 3
NEED_RANK = {"zgoda": 0, "odbiór": 1}


def importance(t, is_late, today):
    """Kolejność najważniejszych decyzji: po terminie, potem najbliższa data, zgoda przed odbiorem, krótsze najpierw."""
    return (0 if is_late else 1, t["date"] if is_day(t["date"]) else "9999", NEED_RANK.get(t["needsYou"], 2),
            t["minutes"] or 9999, t["title"])


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
           "Wymaga Ciebie %d · Po terminie %d · Zagrożone etapy %d · Zablokowane %d · Bez następnego kroku %d"
           " · Etapy bez terminu %d"
           % (c["you"], c["late"], c["risk"], c["blocked"], c["noNextStep"], c["stagesNoDate"])]

    def block(title, rows):
        if rows:
            out.extend(["", title] + ["  " + r for r in rows])

    def task(t, extra=""):
        return "%s · %s%s" % (t["project"], t["title"], extra)

    def decision(t):
        return "◆ %-7s %s" % (t["needsYou"] or "Twoje", task(t, " (%s, %s)" % (when(t["date"], today),
                                                                             minutes_text(t["minutes"]))))

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
          + ["■ zablokowane: %s" % task(t, " (%s)" % t["blocked"] if t["blocked"] else "") for t in f["blocked"]]
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
    data = facts()
    print(json.dumps(data, ensure_ascii=False, indent=1) if "--json" in sys.argv[1:] else text(data))
