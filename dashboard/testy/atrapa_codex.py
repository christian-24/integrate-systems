#!/usr/bin/env python3
"""Atrapa polecenia `codex` do testów: strumień `codex exec --json`.

Tryb jak w atrapa_claude.py (ATRAPA_TRYB_PLIK / ATRAPA_TRYB): ok, zostaw, blad, login.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import atrapa_claude  # noqa: E402  (wspólne: tryb, dziennik, zmiana wiersza)


def out(event):
    sys.stdout.write(json.dumps(event, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def main(argv):
    if "--version" in argv:
        print("codex-cli 0.50.0")
        return 0
    if argv[:2] == ["login", "status"]:
        print("Logged in using ChatGPT")
        return 0
    prompt = sys.stdin.read()
    how = atrapa_claude.mode()
    atrapa_claude.journal({"argv": argv, "cwd": os.getcwd(), "prompt": prompt, "mode": how,
                           "env": [k for k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "PANEL_TOKEN") if k in os.environ]})
    out({"type": "thread.started", "thread_id": "atrapa-codex-1"})
    out({"type": "turn.started"})
    if how == "login":
        out({"type": "error", "message": "401 Unauthorized: not logged in. Run codex login."})
        return 1
    if how == "blad":
        out({"type": "turn.failed", "error": {"message": "Nie udało się wykonać polecenia."}})
        return 1
    out({"type": "item.started", "item": {"id": "i1", "type": "command_execution", "command": "ls", "status": "in_progress"}})
    edited = "" if how == "zostaw" else atrapa_claude.edit_row(prompt, "x")
    if edited:
        out({"type": "item.completed", "item": {"id": "i2", "type": "file_change",
                                                "changes": [{"path": os.path.join(os.getcwd(), edited), "kind": "update"}]}})
    out({"type": "item.completed", "item": {"id": "i3", "type": "agent_message",
                                            "text": "Zrobione: zmiana gotowa.\nSprawdzone: testy.\nZostało: nic."}})
    out({"type": "turn.completed", "usage": {"input_tokens": 1200, "cached_input_tokens": 800, "output_tokens": 300}})
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
