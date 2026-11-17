# Adaptery: jak inne maszyny meldują do Ratusza

Ratusz to serwer wioski (`app/server.js`, port 4791) na komputerze z aplikacją Claude. Inne maszyny
wysyłają do niego zdarzenia przez Tailscale. Każdy adapter to jeden skrypt bez zależności:
Python 3 na Macu/Linuxie, PowerShell na Windows.

## 1. Konfiguracja Ratusza (raz, na komputerze z wioską)

Plik `~/.claude/agent-quest/ratusz.json`:

```json
{
  "token": "wklej-tu-dlugi-losowy-sekret",
  "publicBase": "http://nazwa-maca.tailnet-xyz.ts.net:4791",
  "ntfy": { "url": "https://ntfy.sh", "topic": "ratusz-twoj-losowy-temat", "token": "" }
}
```

- `token`: inne maszyny wysyłają go jako `Authorization: Bearer …`. Gdy jest ustawiony, serwer
  nasłuchuje na wszystkich interfejsach (w praktyce: na adresie Tailscale). Bez tokenu Port jest
  zamknięty, a serwer słucha tylko lokalnie, jak dotąd.
- `publicBase`: adres, pod którym telefon i przyciski w powiadomieniu znajdą ten serwer.
  Z Tailscale to nazwa maszyny w tailnecie.
- `ntfy`: herold. Zainstaluj aplikację ntfy na iPhonie i zasubskrybuj ten temat. Temat jest hasłem,
  więc niech będzie długi i losowy. Własny serwer ntfy: wpisz jego `url` i `token`.

Po zmianie pliku uruchom serwer ponownie (zamknij sesję Claude albo poczekaj, aż plugin go
przeładuje). W wiosce kliknij budynek **Port**: pokaże, czy Port jest otwarty, i wyśle próbne
powiadomienie.

Wymaganie: Node.js 20+ na komputerze z wioską (serwer i skaner to skrypty Node).

## 2. Mac / Linux: hooki Claude Code

W `~/.claude/settings.json`:

```json
{
  "env": { "RATUSZ_URL": "http://127.0.0.1:4791", "RATUSZ_TOKEN": "", "RATUSZ_MACHINE": "mac" },
  "hooks": {
    "SessionStart":     [{ "hooks": [{ "type": "command", "command": "python3 ~/IntegrateSystems/ratusz/adapters/claude-hook.py" }] }],
    "UserPromptSubmit": [{ "hooks": [{ "type": "command", "command": "python3 ~/IntegrateSystems/ratusz/adapters/claude-hook.py" }] }],
    "Stop":             [{ "hooks": [{ "type": "command", "command": "python3 ~/IntegrateSystems/ratusz/adapters/claude-hook.py" }] }],
    "Notification":     [{ "hooks": [{ "type": "command", "command": "python3 ~/IntegrateSystems/ratusz/adapters/claude-hook.py" }] }],
    "SessionEnd":       [{ "hooks": [{ "type": "command", "command": "python3 ~/IntegrateSystems/ratusz/adapters/claude-hook.py" }] }],
    "PreToolUse":       [{ "matcher": "Bash", "hooks": [{ "type": "command", "command": "python3 ~/IntegrateSystems/ratusz/adapters/claude-hook.py --gate", "timeout": 660 }] }]
  }
}
```

Na komputerze z wioską skaner i tak widzi sesje Claude bez hooków; hooki są potrzebne tylko dla
bramki `--gate` (petycje) i dla ostatnich słów agenta.

## 3. Windows: hooki Claude Code

Skopiuj folder `adapters` na PC (np. `C:\ratusz\adapters`). W `%USERPROFILE%\.claude\settings.json`
wpisz to samo co wyżej, z PowerShellem:

```json
{
  "env": { "RATUSZ_URL": "http://nazwa-maca.tailnet-xyz.ts.net:4791", "RATUSZ_TOKEN": "ten-sam-sekret", "RATUSZ_MACHINE": "win-pc" },
  "hooks": {
    "SessionStart":     [{ "hooks": [{ "type": "command", "command": "powershell -NoProfile -ExecutionPolicy Bypass -File C:\\ratusz\\adapters\\claude-hook.ps1" }] }],
    "UserPromptSubmit": [{ "hooks": [{ "type": "command", "command": "powershell -NoProfile -ExecutionPolicy Bypass -File C:\\ratusz\\adapters\\claude-hook.ps1" }] }],
    "Stop":             [{ "hooks": [{ "type": "command", "command": "powershell -NoProfile -ExecutionPolicy Bypass -File C:\\ratusz\\adapters\\claude-hook.ps1" }] }],
    "Notification":     [{ "hooks": [{ "type": "command", "command": "powershell -NoProfile -ExecutionPolicy Bypass -File C:\\ratusz\\adapters\\claude-hook.ps1" }] }],
    "SessionEnd":       [{ "hooks": [{ "type": "command", "command": "powershell -NoProfile -ExecutionPolicy Bypass -File C:\\ratusz\\adapters\\claude-hook.ps1" }] }],
    "PreToolUse":       [{ "matcher": "Bash", "hooks": [{ "type": "command", "command": "powershell -NoProfile -ExecutionPolicy Bypass -File C:\\ratusz\\adapters\\claude-hook.ps1 -Gate", "timeout": 660 }] }]
  }
}
```

Agenci z PC pojawiają się w wiosce z napisem `win-pc` nad głową i wchodzą do posiadłości o tej
samej nazwie folderu co na Macu (`sklep-api` tu i tam to jedna posiadłość).

## 4. Bramka petycji (PreToolUse)

Hook `--gate` / `-Gate` patrzy na komendę Bash. Jeśli zawiera którąś z reguł z **karty posiadłości**
(zakładka Karta w wiosce; domyślnie `git push --force`, `rm -rf`, `DROP TABLE`, `deploy`, `migrate`),
składa petycję i czeka na Twoją odpowiedź: w wiosce, w panelu obok czatu, w aplikacji na telefonie
albo przyciskiem w powiadomieniu ntfy.

- Zatwierdzona: komenda wykonuje się bez dalszych pytań.
- Odrzucona: agent dostaje odmowę z prośbą o inne rozwiązanie.
- Bez odpowiedzi w 10 minut (`RATUSZ_GATE_SECONDS`) albo gdy Port nie odpowiada: zwykłe pytanie
  o zgodę w Claude Code. Bramka nigdy nie przepuszcza po cichu.

`"timeout": 660` w settings.json musi być dłuższy niż czas czekania, inaczej Claude Code przerwie hook.

## 5. Codex CLI

W `~/.codex/config.toml` (na PC: `%USERPROFILE%\.codex\config.toml`):

```toml
notify = ["python3", "/Users/ty/IntegrateSystems/ratusz/adapters/codex-notify.py"]
```

Zmienne `RATUSZ_URL`, `RATUSZ_TOKEN`, `RATUSZ_MACHINE` z otoczenia procesu Codexa (na Windows:
zmienne użytkownika w Ustawieniach systemu).

## 6. Niedokończone repozytoria

Co 15 minut, na każdej maszynie z projektami:

```
python3 ~/IntegrateSystems/ratusz/adapters/repo-status.py ~/Projects/*
```

(na Macu: launchd albo `crontab -e`; na Windows: Harmonogram zadań z `python`). Każde repo z plikami
bez commita albo commitami bez pusha trafia do digestu jako niedokończone.

## 7. Telefon

- Tailscale na iPhonie. Dashboard: `http://nazwa-maca.tailnet-xyz.ts.net:4791/?k=…` (klucz z przycisku
  **Telefon** w wiosce; QR raz, potem ciasteczko).
- Shortcuts, automatyzacja „Przyjazd: dom”: *Pobierz zawartość URL* `…/api/digest` z nagłówkiem
  `Authorization: Bearer <token>` → *Pokaż powiadomienie* z polem `text` odpowiedzi.

## Zdarzenia, które Port rozumie

`session_started` `turn_started` `turn_finished` `needs_decision` `blocked` `session_ended`
`pr_opened` `ci_failed` `ci_passed` `repo_dirty` `note`. Każde: `{ type, source, machine, project,
root, session, title, verb, role, payload }`. Jedno zdarzenie albo tablica w jednym `POST /api/events`.
