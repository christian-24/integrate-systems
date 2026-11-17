#!/usr/bin/env python3
"""Repositories with unfinished work -> Ratusz Port. Run every 15 minutes (cron / launchd / Task Scheduler):
  python3 ~/ratusz/adapters/repo-status.py ~/Projects/*
For every git repo given: files without a commit and commits not pushed become one repo_dirty event
(or nothing, when the repo is clean). Environment: RATUSZ_URL, RATUSZ_TOKEN, RATUSZ_MACHINE.
"""
import json, os, socket, subprocess, sys, urllib.request

URL = os.environ.get("RATUSZ_URL", "http://127.0.0.1:4791").rstrip("/")
TOKEN = os.environ.get("RATUSZ_TOKEN", "")
MACHINE = os.environ.get("RATUSZ_MACHINE") or socket.gethostname().split(".")[0]

def git(root, *args):
    try: return subprocess.run(["git", "-C", root, *args], capture_output=True, text=True, timeout=20).stdout.strip()
    except Exception: return ""

def main():
    events = []
    for root in sys.argv[1:]:
        root = os.path.abspath(root)
        if not os.path.isdir(os.path.join(root, ".git")): continue
        dirty = len([l for l in git(root, "status", "--porcelain").split("\n") if l.strip()])
        branch = git(root, "rev-parse", "--abbrev-ref", "HEAD")
        ahead = git(root, "rev-list", "--count", "@{u}..HEAD") or "0"
        parts = []
        if dirty: parts.append(f"{dirty} plików bez commita")
        if ahead != "0": parts.append(f"{ahead} commitów nie wypchniętych ({branch})")
        if not parts: continue
        events.append({"type": "repo_dirty", "source": "repo", "machine": MACHINE, "project": os.path.basename(root), "root": root,
                       "title": " · ".join(parts), "payload": {"dirty": dirty, "ahead": int(ahead), "branch": branch}})
    if not events: return
    req = urllib.request.Request(URL + "/api/events", data=json.dumps(events).encode(), method="POST",
                                 headers={"Content-Type": "application/json", **({"Authorization": "Bearer " + TOKEN} if TOKEN else {})})
    try: urllib.request.urlopen(req, timeout=8).read()
    except Exception as ex: print(f"ratusz: {ex}", file=sys.stderr)

if __name__ == "__main__": main()
