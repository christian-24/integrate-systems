#!/usr/bin/env python3
"""Atrapa polecenia `claude` do testów: bez sieci, bez limitu. Wypisuje strumień stream-json jak prawdziwe CLI.

Tryb pracy: zawartość pliku wskazanego w ATRAPA_TRYB_PLIK albo zmienna ATRAPA_TRYB (domyślnie `ok`):
  ok       zmienia wiersz zadania na [x] i kończy sukcesem
  zostaw   kończy sukcesem, wiersza nie zmienia
  odmowy   jak ok, w wyniku są odmowy uprawnień
  login    błąd 401 (wygasłe logowanie)
  limit    komunikat o limicie z czasem odnowienia
  limit-zdarzenie   zdarzenie rate_limit_event ze statusem odmowy
  wolno    uruchamia proces potomny i czeka (do zatrzymania albo limitu czasu)
  smieci   wypisuje tekst zamiast JSON i kończy kodem 2
  plan     plan dnia: 2 zadania dla agentów, 1 dla właściciela i 1 id spoza listy w bloku JSON
  plan-zly plan dnia bez bloku JSON
  plik     jak ok, a w katalogu roboczym tworzy notatki/analiza.md i dopisuje pod zadaniem wynik: z tą ścieżką
  commit   jak plik, a zmiany zatwierdza sam (git commit w katalogu roboczym)
  sekret   jak plik, a w katalogu roboczym tworzy też .env.local i certyfikat/serwer.pem (atrapy sekretów)
Rozmowa o zadaniu (argumenty `--output-format json`): jeden obiekt JSON z polami result i session_id
  (sesja-1), odpowiedź „Odpowiedź atrapy: <40 znaków ostatniego wiersza promptu>”. Tryby: czat-wolno (odpowiedź
  po 1,5 s), login (błąd 401), smieci (tekst zamiast JSON), wolno (bez odpowiedzi do limitu czasu).
Każde wywołanie dopisuje wiersz JSON do pliku z ATRAPA_DZIENNIK (argumenty, katalog, prompt, zmienne środowiska).
"""
import json
import os
import re
import subprocess
import sys
import time

SESSION = "atrapa-0001"


def out(event):
    sys.stdout.write(json.dumps(event, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def mode():
    path = os.environ.get("ATRAPA_TRYB_PLIK")
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return f.read().strip() or "ok"
    return os.environ.get("ATRAPA_TRYB", "ok")


def journal(entry):
    path = os.environ.get("ATRAPA_DZIENNIK")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def edit_row(prompt, mark):
    """Zmienia stan wiersza zadania wskazanego w prompcie. Zwraca nazwę pliku albo ''."""
    m = re.search(r"z pliku (.+?), wiersz (\d+): „(.+)”\.", prompt)
    if not m or not os.path.exists(m.group(1)):
        return ""
    with open(m.group(1), encoding="utf-8") as f:
        lines = f.read().split("\n")
    for i, line in enumerate(lines):
        if line.startswith("- [~] " + m.group(3)):
            lines[i] = "- [%s] %s" % (mark, line[6:])
            with open(m.group(1), "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            return m.group(1)
    return ""


def add_result(path, title, text):
    """Dopisuje wcięty wiersz wynik: pod wierszem zadania (jak agent na koniec pracy)."""
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")
    for i, line in enumerate(lines):
        if line.startswith("- [") and line[6:].startswith(title):
            lines.insert(i + 1, "  wynik: " + text)
            break
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def tool(name, data):
    out({"type": "assistant", "session_id": SESSION,
         "message": {"role": "assistant", "content": [{"type": "tool_use", "id": "t1", "name": name, "input": data}],
                     "usage": {"input_tokens": 3, "output_tokens": 40}}})


def result(text, error=False, status=None, denials=()):
    out({"type": "result", "subtype": "success", "is_error": error, "api_error_status": status, "duration_ms": 1200,
         "num_turns": 3, "result": text, "session_id": SESSION, "total_cost_usd": 0.0421,
         "usage": {"input_tokens": 12, "cache_creation_input_tokens": 3100, "cache_read_input_tokens": 9000,
                   "output_tokens": 240},
         "permission_denials": list(denials)})


def chat(prompt, how):
    """Rozmowa o zadaniu: odpowiedź jak `claude -p --output-format json`."""
    if how == "login":
        print(json.dumps({"type": "result", "is_error": True, "session_id": "sesja-1",
                          "result": "Failed to authenticate. API Error: 401 OAuth access token has expired."}))
        return 1
    if how == "wolno":
        time.sleep(120)
        return 0
    if how == "czat-wolno":
        time.sleep(1.5)
    last = ([x.strip() for x in prompt.split("\n") if x.strip()] or [""])[-1]
    print(json.dumps({"type": "result", "subtype": "success", "is_error": False, "session_id": "sesja-1",
                      "result": "Odpowiedź atrapy: " + last[:40]}, ensure_ascii=False))
    return 0


def main(argv):
    if "--version" in argv:
        print("2.1.156 (Claude Code)")
        return 0
    if argv[:2] == ["auth", "login"]:           # jak prawdziwe CLI bez okna: adres, potem kod z wejścia
        print("Opening browser to sign in…")
        print("If the browser didn't open, visit: https://claude.com/cai/oauth/authorize?code=true&state=atrapa")
        sys.stdout.write("Paste code here if prompted > ")
        sys.stdout.flush()
        for line in sys.stdin:
            if line.strip() == "kod#dobry":
                if os.environ.get("ATRAPA_LOGIN_PLIK"):
                    open(os.environ["ATRAPA_LOGIN_PLIK"], "w").close()
                print("Login successful.")
                return 0
            if line.strip() == "kod#zly":
                print("OAuth error: invalid code")
                return 1
            sys.stdout.write("That doesn't look like the full code. Copy all of it, including the # in the middle.\n")
            sys.stdout.write("Paste code here if prompted > ")
            sys.stdout.flush()
        return 1
    if argv[:2] == ["auth", "status"]:
        flag = os.environ.get("ATRAPA_LOGIN_PLIK")
        print(json.dumps({"loggedIn": not flag or os.path.exists(flag), "authMethod": "claude.ai", "apiProvider": "firstParty",
                          "subscriptionType": "max"}))
        return 0
    prompt = sys.stdin.read()
    how = mode()
    seen = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "PANEL_TOKEN", "PANEL_NTFY_URL", "CLAUDECODE",
            "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CODE_OAUTH_TOKEN", "CLAUDE_CONFIG_DIR")
    journal({"argv": argv, "cwd": os.getcwd(), "prompt": prompt, "mode": how,
             "env": [k for k in seen if k in os.environ]})
    if how == "smieci":
        print("Segmentation fault (atrapa)")
        return 2
    if "json" in argv and argv[argv.index("json") - 1] == "--output-format":
        return chat(prompt, how)
    out({"type": "system", "subtype": "init", "model": "claude-atrapa-1", "permissionMode": "acceptEdits",
         "apiKeySource": "none", "tools": ["Read", "Edit", "Bash"], "session_id": SESSION,
         "claude_code_version": "2.1.156"})
    out({"type": "nieznane_zdarzenie", "dane": [1, 2, 3]})
    if how == "login":
        out({"type": "system", "subtype": "api_retry", "attempt": 1, "max_retries": 10, "retry_delay_ms": 500,
             "error_status": 401, "error": "authentication_failed"})
        result("Failed to authenticate. API Error: 401 OAuth access token has expired. Re-authenticate to continue.",
               error=True, status=401)
        return 1
    if how == "limit":
        result("Claude AI usage limit reached|%d" % (int(time.time()) + 7200), error=True)
        return 1
    if how == "limit-zdarzenie":
        out({"type": "rate_limit_event", "rate_limit_info": {"status": "rejected", "rateLimitType": "five_hour",
                                                             "resetsAt": int(time.time()) + 1800}})
        result("Żądanie odrzucone.", error=True)
        return 1
    if how in ("plan", "plan-zly"):
        rows = json.loads(re.search(r"^(\[.*\])$", prompt, re.M).group(1))
        ag = [r["id"] for r in rows if r["agent"]][:2] + ["obcy|ZADANIA.md|1"]
        you = [r["id"] for r in rows if not r["agent"]][:1]
        body = "Dziś najpierw zadania z najbliższym terminem."
        if how == "plan":
            body += "\n```json\n" + json.dumps({"agenci": ag, "ty": you, "uwagi": "test"}, ensure_ascii=False) + "\n```"
        result(body)
        return 0
    tool("Read", {"file_path": os.path.join(os.getcwd(), "ZADANIA.md")})
    if how == "wolno":
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])
        pid_file = os.environ.get("ATRAPA_PID_PLIK")
        if pid_file:
            with open(pid_file, "w", encoding="utf-8") as f:
                f.write(str(child.pid))
        tool("Bash", {"command": "sleep 120\necho koniec"})
        time.sleep(120)
        return 0
    edited = "" if how == "zostaw" else edit_row(prompt, "x")
    if edited:
        tool("Edit", {"file_path": os.path.join(os.getcwd(), edited)})
    if how in ("plik", "commit", "sekret") and edited:
        if how == "sekret":
            os.makedirs("certyfikat", exist_ok=True)
            for name in (".env.local", os.path.join("certyfikat", "serwer.pem")):
                with open(name, "w", encoding="utf-8") as f:
                    f.write("ATRAPA=nie-sekret\n")
        os.makedirs("notatki", exist_ok=True)
        with open(os.path.join("notatki", "analiza.md"), "w", encoding="utf-8") as f:
            f.write("# Analiza\n\nTreść.\n")
        tool("Write", {"file_path": os.path.join(os.getcwd(), "notatki", "analiza.md")})
        m = re.search(r"z pliku (.+?), wiersz (\d+): „(.+)”\.", prompt)
        add_result(edited, m.group(3), "analiza w notatki/analiza.md, szkic w `brak/plik.md`")
        if how == "commit":
            ident = ["-c", "user.name=atrapa", "-c", "user.email=atrapa@example.invalid"]
            subprocess.run(["git", "add", "-A", "."], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["git"] + ident + ["commit", "-q", "-m", "Analiza"], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    out({"type": "assistant", "session_id": SESSION,
         "message": {"role": "assistant", "content": [{"type": "text", "text": "Zrobione: zmiana gotowa.\nSprawdzone: testy."}],
                     "usage": {"input_tokens": 3, "output_tokens": 60}}})
    denials = [{"tool_name": "Bash", "tool_use_id": "t9", "tool_input": {"command": "npm publish"}}] if how == "odmowy" else []
    result("Zrobione: zmiana gotowa.\nSprawdzone: testy.\nZostało: nic.", denials=denials)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
