"""Postęp ze strumieni agentów i odczyt zleceń rozwoju."""
import collections
import datetime
import glob
import json
import os
import re
import stat
import time

ORDER = re.compile(r"ZLECENIE-[\w-]+")
LOG_TAIL = 2 * 1024 * 1024
STALE = 15 * 60


def update_plan(plan, ev):
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


def codex_limit(ev):
    msg = ev.get("msg") or ev.get("payload") or ev
    limits = msg.get("rate_limits") or msg.get("rateLimits") or {}
    for window in (limits.get("primary"), limits.get("secondary")):
        if not isinstance(window, dict) or window.get("window_minutes", window.get("windowDurationMins")) != 300:
            continue
        used = window.get("used_percent", window.get("usedPercent"))
        reset = window.get("resets_at", window.get("resetsAt"))
        if isinstance(used, (float, int)) and 0 <= used <= 100:
            return used / 100, reset if isinstance(reset, (float, int)) else None
    return None


def codex_session_limit(home, thread, started_at):
    """Ostatni licznik 5 h z pliku tej sesji. Pomija wszystkie inne pola sesji."""
    if not home or not re.fullmatch(r"[0-9a-fA-F-]{36}", thread):
        return None
    start = datetime.datetime.fromtimestamp(started_at, datetime.timezone.utc).date()
    for shift in (0, -1, 1):
        day = start + datetime.timedelta(days=shift)
        folder = os.path.join(glob.escape(home), "sessions", day.strftime("%Y/%m/%d"))
        for path in glob.glob(os.path.join(folder, "rollout-*-" + thread + ".jsonl")):
            try:
                with _open(path) as stream:
                    size = stream.seek(0, os.SEEK_END)
                    offset = max(0, size - 512 * 1024)
                    stream.seek(offset)
                    if offset:
                        stream.readline(512 * 1024)
                    for line in reversed(stream.read(512 * 1024).splitlines()):
                        if b'"rate_limits"' not in line:
                            continue
                        try:
                            ev = json.loads(line)
                            if ev.get("type") == "event_msg" and (ev.get("payload") or {}).get("type") == "token_count":
                                limit = codex_limit(ev)
                                if limit:
                                    return limit
                        except (ValueError, AttributeError, TypeError):
                            continue
            except OSError:
                continue
    return None


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
    def __init__(self, folder):
        self.folder = folder
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
                rec.update({k: v for k, v in data.items() if k != "log"})
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

    @staticmethod
    def _read_log(path):
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
                    update_plan(plan, ev)
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
                    limit = codex_limit(ev)
                    if limit:
                        start_limit = limit[0] if start_limit is None else start_limit
                        data.update(limitStart=start_limit, limitNow=limit[0])
                    info = ev.get("rate_limit_info") or {}
                    win = (info.get("unifiedWindows") or {}).get("five_hour") or (
                        info if info.get("rateLimitType") == "five_hour" else {})
                    used = win.get("utilization")
                    if isinstance(used, (int, float)) and 0 <= used <= 1:
                        start_limit = used if start_limit is None else start_limit
                        data.update(limitStart=start_limit, limitNow=used)
                    if kind in ("result", "turn.completed", "turn.failed") or msg.get("type") == "task_complete":
                        data.update(endedAt=True, failed=bool(ev.get("is_error")) or kind == "turn.failed")
                    elif kind in ("assistant", "turn.started", "item.started", "item.updated"):
                        data.pop("endedAt", None)
                        data.pop("failed", None)
                    entries = []
                    if kind == "assistant":
                        entries = [(block.get("text") or block.get("name"), "agent" if block.get("text") else "narzedzie")
                                   for block in (ev.get("message") or {}).get("content") or [] if isinstance(block, dict)]
                    elif item.get("type") == "agent_message" and kind == "item.completed":
                        entries.append((item.get("text"), "agent"))
                    elif kind == "item.started":
                        entries.append(({"command_execution": "Uruchamia polecenie", "file_change": "Edytuje pliki",
                                         "todo_list": "Aktualizuje plan"}.get(item.get("type")), "narzedzie"))
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
