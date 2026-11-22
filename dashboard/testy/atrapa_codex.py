#!/usr/bin/env python3
"""Atrapa polecenia `codex` do testów: strumień `codex exec --json`.

Tryb jak w atrapa_claude.py (ATRAPA_TRYB_PLIK / ATRAPA_TRYB): ok, zostaw, blad, login; niezalogowany (login status).
Zlecenie grafiki (polecenie „Przygotuj grafikę do posta”): ok zapisuje wariant-<n>.png w bieżącym folderze,
grafika-sesja zostawia obraz tylko w $CODEX_HOME/generated_images/<wątek>/ (jak Codex bez kopiowania),
grafika-pusta nie zapisuje nic.
"""
import json
import os
import re
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
        if atrapa_claude.mode() == "niezalogowany":
            print("Not logged in")
            return 1
        print("Logged in using ChatGPT")
        return 0
    if argv[:1] == ["login"]:
        print("Follow these steps to sign in with ChatGPT using device code authorization:")
        print("1. Open this link in your browser and sign in to your account")
        print("   \x1b[94mhttps://auth.openai.com/codex/device\x1b[0m")
        print("2. Enter this one-time code (expires in 15 minutes)")
        print("   \x1b[94mABCD-1234\x1b[0m", flush=True)
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
    if "Przygotuj grafikę do posta" in prompt:
        return graphic(prompt, how)
    out({"type": "item.started", "item": {"id": "i1", "type": "command_execution", "command": "ls", "status": "in_progress"}})
    edited = "" if how == "zostaw" else atrapa_claude.edit_row(prompt, "x")
    if edited:
        out({"type": "item.completed", "item": {"id": "i2", "type": "file_change",
                                                "changes": [{"path": os.path.join(os.getcwd(), edited), "kind": "update"}]}})
    out({"type": "item.completed", "item": {"id": "i3", "type": "agent_message",
                                            "text": "Zrobione: zmiana gotowa.\nSprawdzone: testy.\nZostało: nic."}})
    out({"type": "turn.completed", "usage": {"input_tokens": 1200, "cached_input_tokens": 800, "output_tokens": 300}})
    return 0


PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4"
       b"\x89\x00\x00\x00\rIDATx\x9cc\xf8\xcf\xc0\xf0\x1f\x00\x05\x00\x01\xff\xa1\x8f\xc1\x8c\x00\x00\x00\x00IEND\xaeB`\x82")


def graphic(prompt, how):
    """Zlecenie grafiki: obraz 1×1 px jako wariant w bieżącym folderze albo tylko w katalogu sesji Codex."""
    start = int(re.search(r"od n=(\d+)", prompt).group(1))
    if how == "grafika-sesja":
        where = os.path.join(os.environ.get("CODEX_HOME") or os.path.expanduser("~/.codex"), "generated_images",
                             "atrapa-codex-1")
        os.makedirs(where, exist_ok=True)
        path = os.path.join(where, "ig_atrapa.png")
    else:
        path = os.path.join(os.getcwd(), "wariant-%d.png" % start)
    if how != "grafika-pusta":
        with open(path, "wb") as f:
            f.write(PNG)
        out({"type": "item.completed", "item": {"id": "i2", "type": "file_change",
                                                "changes": [{"path": path, "kind": "add"}]}})
    out({"type": "item.completed", "item": {"id": "i3", "type": "agent_message", "text": "Wariant %d: jaśniej." % start}})
    out({"type": "turn.completed", "usage": {"input_tokens": 900, "cached_input_tokens": 0, "output_tokens": 100}})
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
