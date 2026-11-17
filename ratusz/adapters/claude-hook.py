#!/usr/bin/env python3
"""Claude Code hook -> Ratusz Port (Mac / Linux). One script for every hook event.

settings.json (~/.claude/settings.json), with your own URL and token:
  "hooks": {
    "SessionStart":     [{"hooks": [{"type": "command", "command": "python3 ~/ratusz/adapters/claude-hook.py"}]}],
    "UserPromptSubmit": [{"hooks": [{"type": "command", "command": "python3 ~/ratusz/adapters/claude-hook.py"}]}],
    "Stop":             [{"hooks": [{"type": "command", "command": "python3 ~/ratusz/adapters/claude-hook.py"}]}],
    "Notification":     [{"hooks": [{"type": "command", "command": "python3 ~/ratusz/adapters/claude-hook.py"}]}],
    "SessionEnd":       [{"hooks": [{"type": "command", "command": "python3 ~/ratusz/adapters/claude-hook.py"}]}],
    "PreToolUse":       [{"matcher": "Bash", "hooks": [{"type": "command", "command": "python3 ~/ratusz/adapters/claude-hook.py --gate", "timeout": 660}]}]
  }
Environment (put it in ~/.claude/settings.json "env" or in the shell): RATUSZ_URL, RATUSZ_TOKEN, RATUSZ_MACHINE.
The gate (--gate) files a petition when a command matches a rule of the project's charter and waits
for your answer up to RATUSZ_GATE_SECONDS (600). No answer, or the Port unreachable, means the
normal permission prompt, never a silent allow.
"""
import json, os, socket, sys, time, urllib.parse, urllib.request

URL = os.environ.get("RATUSZ_URL", "http://127.0.0.1:4791").rstrip("/")
TOKEN = os.environ.get("RATUSZ_TOKEN", "")
MACHINE = os.environ.get("RATUSZ_MACHINE") or socket.gethostname().split(".")[0]
DEFAULT_RULES = ["git push --force", "rm -rf", "DROP TABLE", "deploy", "migrate"]

def call(path, body=None, timeout=6):
    req = urllib.request.Request(URL + path, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json", **({"Authorization": "Bearer " + TOKEN} if TOKEN else {})},
                                 method="POST" if body is not None else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode() or "null")

def last_assistant_text(transcript, limit=500):
    try:
        with open(transcript, "rb") as f:
            f.seek(0, 2); size = f.tell(); f.seek(max(0, size - 200_000)); tail = f.read().decode("utf-8", "ignore")
        for line in reversed(tail.split("\n")):
            try: e = json.loads(line)
            except Exception: continue
            if e.get("type") == "assistant":
                parts = [c.get("text", "") for c in e.get("message", {}).get("content", []) if isinstance(c, dict) and c.get("type") == "text"]
                text = " ".join(parts).strip()
                if text: return text[:limit]
    except Exception: pass
    return ""

def main():
    raw = sys.stdin.read()
    try: h = json.loads(raw or "{}")
    except Exception: h = {}
    cwd = h.get("cwd") or os.getcwd()
    project = os.path.basename(cwd.rstrip("/\\"))
    base = {"source": "claude-code", "machine": MACHINE, "project": project, "root": cwd, "session": h.get("session_id", ""),
            "payload": {"name": f"Claude Code · {project}"}}
    ev = h.get("hook_event_name", "")

    if "--gate" in sys.argv:
        tool = h.get("tool_name", ""); inp = h.get("tool_input", {}) or {}
        text = inp.get("command", "") if tool == "Bash" else json.dumps(inp, ensure_ascii=False)
        try: rules = (call(f"/api/charter?name={urllib.parse.quote(project)}") or {}).get("rules") or DEFAULT_RULES
        except Exception: rules = DEFAULT_RULES
        hit = next((r for r in rules if r and r.lower() in text.lower()), None)
        if not hit: return
        try:
            d = call("/api/decisions", {"kind": "approval", "source": "claude-code", "machine": MACHINE, "project": project, "session": h.get("session_id", ""),
                                        "agent": f"Claude Code · {project}", "title": f"Zgoda na: {text[:120]}", "command": text[:500], "rule": hit})
        except Exception as e:
            print(f"ratusz: Port nieosiągalny ({e}); zwykłe pytanie o zgodę", file=sys.stderr); return
        deadline = time.time() + float(os.environ.get("RATUSZ_GATE_SECONDS", "600"))
        status = "pending"
        while time.time() < deadline:
            time.sleep(2)
            try: status = (call(f"/api/decisions/{d['id']}") or {}).get("status", "pending")
            except Exception: continue
            if status != "pending": break
        if status == "approved":
            out = {"permissionDecision": "allow", "permissionDecisionReason": f"Ratusz: zatwierdzone z {MACHINE}"}
        elif status == "rejected":
            out = {"permissionDecision": "deny", "permissionDecisionReason": "Ratusz: odrzucone. Zaproponuj inne rozwiązanie i zapytaj."}
        else:
            print("ratusz: petycja bez odpowiedzi; zwykłe pytanie o zgodę", file=sys.stderr); return
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", **out}})); return

    if ev == "SessionStart": e = {"type": "session_started", "title": f"nowa sesja w {project}", "verb": "zaczyna"}
    elif ev == "UserPromptSubmit": e = {"type": "turn_started", "title": (h.get("prompt") or "")[:160], "verb": "pracuje"}
    elif ev == "Stop": e = {"type": "turn_finished", "title": "skończył turę", "verb": "skończył turę", "payload": {**base["payload"], "text": last_assistant_text(h.get("transcript_path", ""))}}
    elif ev == "Notification": e = {"type": "blocked", "title": (h.get("message") or "czeka na Ciebie")[:200], "verb": "czeka na Ciebie"}
    elif ev == "SessionEnd": e = {"type": "session_ended", "title": f"sesja zakończona ({h.get('reason', '')})", "verb": "skończył"}
    else: return
    try: call("/api/events", {**base, **e})
    except Exception as ex: print(f"ratusz: {ex}", file=sys.stderr)

if __name__ == "__main__":
    main()
