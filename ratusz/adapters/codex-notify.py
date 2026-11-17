#!/usr/bin/env python3
"""Codex CLI notify -> Ratusz Port. In ~/.codex/config.toml:
  notify = ["python3", "/Users/you/ratusz/adapters/codex-notify.py"]
(on Windows: notify = ["python", "C:\\ratusz\\adapters\\codex-notify.py"])
Codex appends one JSON argument, e.g. {"type":"agent-turn-complete","turn-id":"...","last-assistant-message":"..."}.
Environment: RATUSZ_URL, RATUSZ_TOKEN, RATUSZ_MACHINE, RATUSZ_PROJECT (defaults to the current folder's name).
"""
import json, os, socket, sys, urllib.request

URL = os.environ.get("RATUSZ_URL", "http://127.0.0.1:4791").rstrip("/")
TOKEN = os.environ.get("RATUSZ_TOKEN", "")
MACHINE = os.environ.get("RATUSZ_MACHINE") or socket.gethostname().split(".")[0]

def main():
    try: n = json.loads(sys.argv[-1]) if len(sys.argv) > 1 else {}
    except Exception: n = {}
    cwd = n.get("cwd") or os.getcwd()
    project = os.environ.get("RATUSZ_PROJECT") or os.path.basename(cwd.rstrip("/\\"))
    kind = n.get("type", "")
    session = n.get("thread-id") or n.get("session-id") or f"codex-{project}"
    last = (n.get("last-assistant-message") or "")[:500]
    if kind == "agent-turn-complete": e = {"type": "turn_finished", "title": "Codex skończył turę", "verb": "skończył turę"}
    elif "approval" in kind: e = {"type": "needs_decision", "title": "Codex prosi o zgodę", "verb": "petycja"}
    else: e = {"type": "note", "title": kind[:100] or "codex", "verb": "pracuje"}
    body = {"source": "codex", "machine": MACHINE, "project": project, "root": cwd, "session": session, **e,
            "payload": {"name": f"Codex · {project}", "text": last}}
    req = urllib.request.Request(URL + "/api/events", data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", **({"Authorization": "Bearer " + TOKEN} if TOKEN else {})})
    try: urllib.request.urlopen(req, timeout=6).read()
    except Exception as ex: print(f"ratusz: {ex}", file=sys.stderr)

if __name__ == "__main__": main()
