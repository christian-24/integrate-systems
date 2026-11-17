# Ratusz

Fork pluginu **Agent Quest** (christian-24, v0.8) rozszerzony o Ratusz: to, czego wioska nie miała.

- **Petycje**: agenci proszą o zgodę (bramka PreToolUse), odbiór (PR) albo odpowiedź; Ty
  odpowiadasz w wiosce, w panelu obok czatu, na telefonie albo przyciskiem w powiadomieniu.
- **Karta posiadłości**: cel, zakres, wymagania ukończenia, swoboda agentów i lista operacji
  wymagających petycji; „Zapisz i wyślij” tworzy `KARTA.md` i `@KARTA.md` w `CLAUDE.md` projektu.
- **Port**: zdarzenia z innych maszyn (PC Windows, Codex, chmura) przez `POST /api/events`;
  agenci z innych maszyn chodzą po wyspie z nazwą maszyny nad głową.
- **Herold**: push przez ntfy z przyciskami Zatwierdź / Odrzuć.
- **Digest**: `GET /api/digest` dla Shortcuts „Przyjazd: dom”.

Układ: `app/server.js` (serwer wioski, port **4791**; oryginał zostaje na 4790) · `app/ratusz.js`
(nowe zaplecze) · `app/index.html` (wioska 3D + nowe zakładki) · `hooks/register.tsx` (panel obok
czatu) · `scanner/scan.js` (sesje Claude na tej maszynie + agenci z Portu) · `adapters/` (skrypty
dla innych maszyn, instrukcja w `adapters/README.md`).

Dane: `~/.claude/agent-quest/` (wspólne z oryginałem: todos, plany, role, skarbiec; nowe:
`events.json`, `charters.json`, `decisions.json`, `ratusz.json`).

Wymaga Node.js 20+ na komputerze z aplikacją Claude. Jako mod tej sesji ładuje się z
`~/.claude/dev-mods/<sesja>/ratusz` (dowiązanie do tego folderu); jako plugin: `--plugin-dir`
na ten folder.
