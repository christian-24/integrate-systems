"""Postęp ze strumieni agentów i odczyt zleceń rozwoju."""
import collections
import datetime
import glob
import json
import math
import os
import re
import stat
from statistics import median, quantiles
import time

ORDER = re.compile(r"ZLECENIE-[\w-]+")
LOG_TAIL = 2 * 1024 * 1024
STALE = 15 * 60


def update_plan(plan, ev, now=None):
    """Plan (kamienie milowe) ze zdarzenia strumienia. now: chwila zdarzenia (s); ukończony krok dostaje doneAt,
    z którego liczy się tempo kamieni (estimate_running). Bez now nowy doneAt nie powstaje (wcześniejsze zostają)."""
    before = {_step_key(s): s.get("doneAt") for s in plan if s.get("done")}
    _apply_plan(plan, ev)
    for step in plan:
        if step.get("done") and "doneAt" not in step:
            key = _step_key(step)
            stamp = before[key] if key in before else now
            if stamp is not None:
                step["doneAt"] = stamp


def _step_key(step):
    return step.get("id") or step.get("text")


def _apply_plan(plan, ev):
    msg = ev.get("msg")
    msg = msg if isinstance(msg, dict) else ev
    item = ev.get("item") or {}
    todos = None
    if item.get("type") == "todo_list":
        todos = item.get("items")
    elif msg.get("type") in ("plan_update", "update_plan", "turn.plan.updated"):
        todos = msg.get("plan")
    if isinstance(todos, list):
        plan[:] = _steps(todos)
    if ev.get("type") != "assistant":
        return
    for block in (ev.get("message") or {}).get("content") or []:
        if not isinstance(block, dict) or block.get("type") != "tool_use":
            continue
        args = block.get("input") or {}
        name = block.get("name")
        if name == "TodoWrite" and isinstance(args.get("todos"), list):
            plan[:] = _steps(args["todos"])
        if name == "TaskUpdate" and args.get("taskId"):
            _update_task(plan, str(args["taskId"]), args)


def _steps(todos):
    result = []
    for todo in todos[:100]:
        if not isinstance(todo, dict):
            continue
        title = todo.get("content") or todo.get("text") or todo.get("step")
        if title:
            status = todo.get("status")
            result.append({"text": str(title)[:240], "done": todo.get("completed") is True or status == "completed",
                           "active": status == "in_progress"})
    return result


def _update_task(plan, task_id, args):
    step = next((s for s in plan if s.get("id") == task_id), None)
    if args.get("status") == "deleted":
        if step:
            plan.remove(step)
        return
    if step is None:
        if len(plan) >= 100:
            return
        step = {"id": task_id, "text": "", "done": False, "active": False}
        plan.append(step)
    if args.get("subject"):
        step["text"] = str(args["subject"])[:240]
    if args.get("status"):
        step.update(done=args["status"] == "completed", active=args["status"] == "in_progress")


def task_creates(pending, plan, ev):
    """Id zadania Claude jest przydzielane w odpowiedzi narzędzia TaskCreate."""
    kind = ev.get("type")
    if kind not in ("assistant", "user"):
        return
    for block in (ev.get("message") or {}).get("content") or []:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "tool_use" and block.get("name") == "TaskCreate" and len(pending) < 100:
            pending[str(block.get("id"))] = (block.get("input") or {}).get("subject")
        elif block.get("type") == "tool_result":
            subject = pending.pop(str(block.get("tool_use_id")), None)
            if not subject or block.get("is_error"):
                continue
            match = re.search(r"Task #([\w-]+) created", str(block.get("content")))
            if match:
                _update_task(plan, match[1], {"subject": subject})


def reset_time(value):
    try:
        stamp = float(value)
        return (stamp / 1000 if stamp > 1e12 else stamp) if math.isfinite(stamp) and stamp > 0 else None
    except (TypeError, ValueError):
        return None


def read_time(value, default):
    try:
        return datetime.datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except (AttributeError, ValueError, OverflowError):
        return default


def limit_windows(ev, tool, at):
    """Metadane limitów obu okien, bez pozostałych danych zdarzenia."""
    result = {}
    if tool == "codex":
        msg = ev.get("msg") or ev.get("payload") or ev
        limits = msg.get("rate_limits") or msg.get("rateLimits") or {}
        for window in (limits.get("primary"), limits.get("secondary")):
            if not isinstance(window, dict):
                continue
            minutes = window.get("window_minutes", window.get("windowDurationMins"))
            key = {300: "five", 10080: "seven"}.get(minutes)
            used = window.get("used_percent", window.get("usedPercent"))
            if key and isinstance(used, (int, float)) and 0 <= used <= 100:
                result[key] = (used / 100, at, reset_time(window.get("resets_at", window.get("resetsAt"))))
    elif tool == "claude":
        info = ev.get("rate_limit_info") or {}
        for key, name in (("five", "five_hour"), ("seven", "seven_day")):
            standalone = info if info.get("rateLimitType") == name else {}
            window = (info.get("unifiedWindows") or {}).get(name) or standalone
            if key == "five" and not standalone and info.get("rateLimitType") is None:
                standalone = info
            used = window.get("utilization")
            if isinstance(used, (int, float)) and 0 <= used <= 1:
                result[key] = (used, at, reset_time(window.get("resetsAt", standalone.get("resetsAt"))))
    return result


def codex_limit(ev):
    sample = limit_windows(ev, "codex", 0).get("five")
    return (sample[0], sample[2]) if sample else None


def session_windows(path):
    result = {}
    with _open(path) as stream:
        size = stream.seek(0, os.SEEK_END)
        stream.seek(max(0, size - LOG_TAIL))
        if size > LOG_TAIL:
            stream.readline(LOG_TAIL)
        modified = os.fstat(stream.fileno()).st_mtime
        for line in reversed(stream.read(LOG_TAIL).splitlines()):
            if b'"rate_limits"' not in line or b'"token_count"' not in line:
                continue
            try:
                event = json.loads(line)
                if event.get("type") != "event_msg" or (event.get("payload") or {}).get("type") != "token_count":
                    continue
                for key, sample in limit_windows(event, "codex", read_time(event.get("timestamp"), modified)).items():
                    result.setdefault(key, sample)
                if len(result) == 2:
                    break
            except (ValueError, AttributeError, TypeError):
                continue
    return result


def latest_session_windows(home):
    paths = glob.iglob(os.path.join(glob.escape(home), "sessions", "**", "rollout-*.jsonl"), recursive=True)
    newest = max(((st.st_mtime, path) for path in paths if (st := _info(path))), default=None)
    if newest:
        try:
            return session_windows(newest[1])
        except OSError:
            pass
    return {}


def codex_session_windows(home, thread, started_at):
    """Ostatni licznik 5 h z pliku tej sesji. Pomija wszystkie inne pola sesji."""
    if not home or not re.fullmatch(r"[0-9a-fA-F-]{36}", thread):
        return {}
    start = datetime.datetime.fromtimestamp(started_at, datetime.timezone.utc).date()
    for shift in (0, -1, 1):
        day = start + datetime.timedelta(days=shift)
        folder = os.path.join(glob.escape(home), "sessions", day.strftime("%Y/%m/%d"))
        for path in glob.glob(os.path.join(folder, "rollout-*-" + thread + ".jsonl")):
            try:
                windows = session_windows(path)
                if windows:
                    return windows
            except OSError:
                continue
    return {}


def codex_session_limit(home, thread, started_at):
    sample = codex_session_windows(home, thread, started_at).get("five")
    return (sample[0], sample[2]) if sample else None


def _open(path):
    """Tylko zwykły plik, bez dowiązań i blokowania na potoku."""
    before = os.lstat(path)
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
        raise OSError("Zlecenie wymaga zwykłego pliku")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0) |
                 getattr(os, "O_BINARY", 0))
    opened = os.fstat(fd)
    if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1 or not os.path.samestat(before, opened):
        os.close(fd)
        raise OSError("Plik zlecenia zmienił się")
    return os.fdopen(fd, "rb")


def _info(path):
    try:
        st = os.lstat(path)
        if stat.S_ISREG(st.st_mode) and st.st_nlink == 1:
            return st
    except OSError:
        pass
    return None


def _iso(st):
    return datetime.datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds")


class Orders:
    def __init__(self, folder, describe=None):
        self.folder = folder
        self.describe = describe or (lambda name, args: args.get("description") or args.get("command") or args.get("file_path") or name)
        self.cache = {}

    def result(self, name):
        if not self.folder or not ORDER.fullmatch(name):
            return None
        if not _info(os.path.join(self.folder, name + ".md")):
            return None
        try:
            with _open(os.path.join(self.folder, name + ".wynik.md")) as stream:
                return stream.read(512 * 1024).decode("utf-8", "replace")
        except OSError:
            return None

    def snapshot(self):
        if not self.folder:
            return []
        try:
            names = os.listdir(self.folder)
        except OSError:
            return []
        result = []
        cache = {}
        for file in names:
            name, ext = os.path.splitext(file)
            if ext != ".md" or not ORDER.fullmatch(name):
                continue
            path = os.path.join(self.folder, name)
            try:
                with _open(path + ".md") as stream:
                    title = stream.readline(2048).decode("utf-8", "replace").lstrip("# ").strip()
                    order = os.fstat(stream.fileno())
            except OSError:
                continue
            log, report = _info(path + ".log"), _info(path + ".wynik.md")
            rec = {"id": name, "kind": "development", "machine": "cloud", "title": title or name,
                   "projectName": "Rozwój panelu", "queuedAt": _iso(order), "state": "queued",
                   "hasResult": bool(report)}
            if log is not None:
                key = (log.st_dev, log.st_ino, log.st_size, log.st_mtime_ns)
                cached_key, data, first_seen = self.cache.get(name, (None, None, None))
                if cached_key is None or key[:2] != cached_key[:2] or key[2] < cached_key[2]:
                    first_seen = getattr(log, "st_birthtime", None) or log.st_mtime
                if cached_key != key:
                    try:
                        data = self._read_log(path + ".log")
                    except OSError:
                        data = {}
                cache[name] = (key, data, first_seen)
                rec.update({k: v for k, v in data.items() if k not in ("log", "limits")})
                rec["startedAt"] = rec.pop("eventStart", None)
                if not rec["startedAt"]:
                    rec["startedAt"] = datetime.datetime.fromtimestamp(first_seen).isoformat(timespec="seconds")
                    rec["observedStart"] = True
                if not rec.get("endedAt"):
                    rec["state"] = "running" if time.time() - log.st_mtime < STALE else "unknown"
                    if rec["state"] == "unknown":
                        rec["activity"] = "Brak nowych zdarzeń od co najmniej 15 minut"
            if report or rec.get("endedAt"):
                rec["state"] = "error" if rec.get("failed") else "done"
                rec["endedAt"] = _iso(report or log)
                if rec.get("startedAt") and not rec.get("observedStart"):
                    duration = read_time(rec["endedAt"], 0) - read_time(rec["startedAt"], 0)
                    if duration > 0:
                        rec.setdefault("durationMs", duration * 1000)
            result.append(rec)
        self.cache = cache
        return sorted(result, key=lambda r: (r.get("endedAt") or r.get("startedAt") or r["queuedAt"], r["id"]),
                      reverse=True)

    def live_log(self, name, since):
        if not ORDER.fullmatch(name):
            return None
        rec = next((r for r in self.snapshot() if r["id"] == name), None)
        if rec is None:
            return None
        _, data, _ = self.cache.get(name, (None, {}, None))
        items = data.get("log", [])
        return {"items": [row for row in items if row["n"] > since], "next": rec.get("logN", 0),
                "state": rec["state"], "tool": rec.get("tool", ""), "activity": rec.get("activity", "")}

    def _read_log(self, path):
        plan, pending, recent = [], {}, collections.deque(maxlen=200)
        data = {}
        start_limit = None
        with _open(path) as stream:
            if stream.seek(0, os.SEEK_END) > LOG_TAIL:
                stream.seek(-LOG_TAIL, os.SEEK_END)
                stream.readline(LOG_TAIL)
            else:
                stream.seek(0)
            pos = stream.tell()
            for line in stream.read(LOG_TAIL).splitlines(keepends=True):
                pos += len(line)
                try:
                    ev = json.loads(line)
                    if not isinstance(ev, dict):
                        continue
                    update_plan(plan, ev, read_time(ev.get("timestamp"), None))
                    task_creates(pending, plan, ev)
                    kind = ev.get("type") or ""
                    msg = ev.get("msg") or ev
                    item = ev.get("item") or {}
                    stamp = ev.get("timestamp")
                    if isinstance(stamp, str) and "eventStart" not in data:
                        try:
                            data["eventStart"] = datetime.datetime.fromisoformat(stamp.replace("Z", "+00:00")).isoformat()
                        except ValueError:
                            pass
                    if kind.startswith(("item.", "turn.", "thread.")) or msg is not ev:
                        data["tool"] = "codex"
                    elif kind in ("assistant", "system", "rate_limit_event", "result"):
                        data["tool"] = "claude"
                    if kind == "token_count":
                        data["tool"] = "codex"
                    if kind == "event_msg":
                        msg = ev.get("payload") or msg
                        data["tool"] = "codex"
                    windows = limit_windows(ev, data.get("tool"), read_time(stamp, os.fstat(stream.fileno()).st_mtime))
                    if windows:
                        data.setdefault("limits", {}).setdefault(data["tool"], {}).update(windows)
                    if "five" in windows:
                        used, _, reset = windows["five"]
                        if start_limit is None or (reset and data.get("limitReset") != reset):
                            start_limit = used
                        data.update(limitStart=start_limit, limitNow=used, limitReset=reset)
                    usage = ev.get("usage") or (msg.get("info") or {}).get("total_token_usage")
                    if isinstance(usage, dict):
                        data.update(tokensIn=usage.get("input_tokens", 0), tokensOut=usage.get("output_tokens", 0))
                    if kind == "result" and ev.get("duration_ms"):
                        data["durationMs"] = ev["duration_ms"]
                    if kind in ("result", "turn.completed", "turn.failed") or msg.get("type") == "task_complete":
                        data.update(endedAt=True, failed=bool(ev.get("is_error")) or kind == "turn.failed")
                    elif kind in ("assistant", "turn.started", "item.started", "item.updated"):
                        data.pop("endedAt", None)
                        data.pop("failed", None)
                    entries = []
                    if kind == "assistant":
                        entries = [(block.get("text") or self.describe(block.get("name") or "", block.get("input") or {}),
                                    "agent" if block.get("text") else "narzedzie")
                                   for block in (ev.get("message") or {}).get("content") or [] if isinstance(block, dict)]
                    elif item.get("type") == "agent_message" and kind == "item.completed":
                        entries.append((item.get("text"), "agent"))
                    elif kind == "item.started":
                        entries.append(({"command_execution": self.describe("Bash", {"command": item.get("command")}), "file_change": "Edytuje pliki",
                                         "todo_list": "Aktualizuje plan"}.get(item.get("type")), "narzedzie"))
                    elif item.get("type") == "file_change" and kind == "item.completed":
                        entries.extend((self.describe("Edit", {"file_path": change.get("path")}), "narzedzie")
                                       for change in item.get("changes") or [] if isinstance(change, dict))
                    elif msg.get("type") == "exec_command_begin":
                        entries.append((self.describe("Bash", {"command": msg.get("command")}), "narzedzie"))
                    elif msg.get("type") == "agent_message":
                        entries.append((msg.get("message"), "agent"))
                    for i, (entry, category) in enumerate(entries[:100]):
                        if entry:
                            recent.append({"n": pos * 100 + i, "text": str(entry)[:4000], "k": category, "t": ""})
                except (ValueError, TypeError, AttributeError):
                    continue
        latest = [row["text"][:300] for row in list(recent)[-3:]]
        return dict(data, plan=[step for step in plan if step.get("text")], recent=latest,
                    log=list(recent), logN=recent[-1]["n"] if recent else 0, activity=latest[-1] if latest else "")


def category(run):
    if run.get("category"):
        return run["category"]
    kind = run.get("kind")
    if kind != "task":
        return kind
    if run.get("title", "").startswith("Strona:"):
        return "site"
    if run.get("branch"):
        title = run.get("title", "")
        if not re.match(r"(?i)^(napisz|opisz|przeanalizuj|spisz|przygotuj post|raport)\b", title):
            return "repo"
    return "text"


def consumed(run):
    start, end = run.get("limitStart"), run.get("limitNow")
    if isinstance(start, (int, float)) and isinstance(end, (int, float)) and end >= start:
        return end - start
    return None


def token_count(run):
    return sum(run.get(key) or 0 for key in ("tokensIn", "tokensOut", "decisionTokensIn", "decisionTokensOut"))


def estimate(history, tool, kind):
    """Typowy czas (mediana) z co najmniej 3 zakończonych uruchomień tego narzędzia i rodzaju; low i high: kwartyle
    (zakres w podpowiedzi), limit i tokens: mediany."""
    runs = [r for r in history if tool and r.get("tool") == tool and category(r) == kind
            and r.get("state") == "done" and (r.get("durationMs") or 0) > 0]
    result = {"examples": len(runs)}
    if len(runs) >= 3:
        durations = [r["durationMs"] / 1000 for r in runs]
        result["seconds"] = median(durations)
        low, _, high = quantiles(durations, n=4, method="inclusive")
        result.update(low=low, high=high)
        for key, getter in (("limit", consumed), ("tokens", lambda r: token_count(r) or None)):
            observations = [value for r in runs if (value := getter(r)) is not None]
            if len(observations) >= 3:
                result[key] = median(observations)
    return result


MILESTONE_SPREAD = .5       # ± po pierwszym kamieniu; po n kamieniach .5/√n


def estimate_running(typical, run, now):
    """Szacunek uruchomienia w toku. Przed pierwszym ukończonym kamieniem: mediana z historii (basis history).
    Potem tempo kamieni: czas na kamień × pozostałe, ważone z historią (waga tempa n/(n+1) po n kamieniach),
    z marginesem ± malejącym z każdym kamieniem (basis milestones)."""
    elapsed = max(0, now - read_time(run.get("startedAt"), now))
    result = dict(typical, elapsed=elapsed, basis="history")
    if "seconds" in typical:
        result["typical"] = typical["seconds"]
    plan = [s for s in run.get("plan") or [] if s.get("text")]
    total, done = len(plan), sum(s.get("done") is True for s in plan)
    if total:
        result["milestones"] = {"done": done, "total": total}
    if done and elapsed > 0:
        start = read_time(run.get("startedAt"), now)
        stamps = [s["doneAt"] - start for s in plan if s.get("done") is True and isinstance(s.get("doneAt"), (int, float))]
        last = max(stamps) if len(stamps) == done else elapsed
        last = min(elapsed, max(1, last))
        pace = last / done
        left = total - done
        remaining = 0
        if left:
            since = elapsed - last
            remaining = max(pace - since, .2 * pace) + pace * (left - 1)
            if "seconds" in typical:
                weight = done / (done + 1)
                remaining = weight * remaining + (1 - weight) * typical["seconds"] * left / total
        result.update(seconds=elapsed + remaining, remaining=remaining, pace=pace, basis="milestones",
                      margin=remaining * MILESTONE_SPREAD / math.sqrt(done))
        for key, amount in (("limit", consumed(run)), ("tokens", token_count(run) or None)):
            if amount is not None:
                result[key] = amount * total / done
        return result
    if "seconds" not in typical:
        return result
    result["seconds"] = max(elapsed, result["seconds"])
    result["remaining"] = result["seconds"] - elapsed
    return result


def estimate_queue(active, queued, parallel, now):
    """Godziny w kolejności kolejki, z uwzględnieniem równoległych stanowisk."""
    lanes = sorted(now + max(0, row["estimate"]["seconds"] - row["estimate"]["elapsed"])
                   for row in active if "seconds" in row["estimate"])
    lanes.extend([now] * max(0, parallel - len(active)))
    for row in queued:
        estimate = row["estimate"]
        if not lanes:
            break
        start = min(lanes)
        lanes.remove(start)
        estimate["start"] = start
        if "seconds" in estimate:
            estimate["end"] = start + estimate["seconds"]
            lanes.append(estimate["end"])
    return {key: sum(row["estimate"][key] for row in queued)
            for key in ("seconds", "tokens", "limit") if queued and all(key in row["estimate"] for row in queued)}


FINISHED_OK = ("done",)
FINISHED_BAD = ("error", "timeout", "login", "limit")
TOP_SHOWN = 5


def usage_stats(history, now):
    """Użycie Claude i Codex z zapisanych uruchomień (bez nowych logów): liczba i tokeny dziś i w 7 dni, średni czas
    zakończonych, odsetek udanych (zakończone bez błędu i bez blokady; zatrzymane ręcznie się nie liczą) i najdroższe
    zadania 7 dni (tokeny). Dzień według czasu lokalnego tego komputera."""
    midnight = datetime.datetime.fromtimestamp(now).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    week = now - 7 * 86400
    result = {}
    for tool in ("claude", "codex"):
        stats = {"runsToday": 0, "runs7": 0, "tokensToday": 0, "tokens7": 0, "costUsd7": 0, "ok7": 0, "finished7": 0}
        durations, top = [], []
        for run in history:
            if run.get("tool") != tool:
                continue
            at = read_time(run.get("startedAt") or run.get("queuedAt"), None)
            if at is None or at < week:
                continue
            tokens = token_count(run)
            stats["runs7"] += 1
            stats["tokens7"] += tokens
            stats["costUsd7"] += (run.get("costUsd") or 0) + (run.get("decisionCostUsd") or 0)
            if at >= midnight:
                stats["runsToday"] += 1
                stats["tokensToday"] += tokens
            state = run.get("state")
            if state in FINISHED_OK or state in FINISHED_BAD:
                stats["finished7"] += 1
                if state in FINISHED_OK and run.get("outcome") != "blocked":
                    stats["ok7"] += 1
            if state == "done" and (run.get("durationMs") or 0) > 0:
                durations.append(run["durationMs"])
            if tokens and state not in ("queued", "running"):
                top.append({"id": str(run.get("id") or ""), "title": str(run.get("title") or "")[:200],
                            "projectName": str(run.get("projectName") or "")[:120], "tokens": tokens,
                            "costUsd": round((run.get("costUsd") or 0) + (run.get("decisionCostUsd") or 0), 2),
                            "limit": consumed(run), "at": run.get("startedAt") or run.get("queuedAt") or ""})
        stats["costUsd7"] = round(stats["costUsd7"], 2)
        stats["avgMs"] = round(sum(durations) / len(durations)) if durations else None
        stats["successRate"] = stats["ok7"] / stats["finished7"] if stats["finished7"] else None
        stats["top"] = sorted(top, key=lambda r: r["tokens"], reverse=True)[:TOP_SHOWN]
        result[tool] = stats
    return result
