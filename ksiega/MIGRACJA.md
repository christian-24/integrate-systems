# Migracja z PC do chmury (D13)

Cel: wszystko, co dziś istnieje tylko na PC, ma bezpieczne miejsce, zanim PC pójdzie na sprzedaż. Potem serwer w chmurze przejmuje pracę.
Źródło listy: audyt PC z 2026-11-14 (`szkice/AUDYT-PC-2026-11-14.md`).

## Etapy

| # | Etap | Warunek zakończenia |
|---|---|---|
| 1 | Zabezpieczenie danych z PC (PC włączony, w sieci) | każdy wiersz tabeli poniżej ma stan „gotowe”; archiwum na Macu sprawdzone (liczba plików, rozmiar) |
| 2 | Serwer w chmurze: panel z logowaniem przez HTTPS, agenci, repozytoria, nocna kopia | panel otwiera się z Maca i z iPhone'a spoza domu; jedno zadanie agenta wykonane na serwerze |
| 3 | Useme i Windows: pilnowanie zleceń przez e-maile na serwerze, rozszerzenia w Chrome na Macu, build Warsztatu w GitHub Actions, próba Windows w Azure | nowe zlecenie z Useme widoczne w panelu; zielony build Warsztatu |
| 4 | Dzień próbny bez PC | 24 h bez włączania PC i bez brakujących danych → PC do resetu i sprzedaży |

## Dane do zabrania z PC

Kanał (2026-11-16): Claude uruchomiony na samym PC według `MIGRACJA-INSTRUKCJA-PC.md`; kopia na dysk zewnętrzny podłączony do PC przez USB, do folderu `Migracja-PC-2026-11` (bez usuwania czegokolwiek na dysku). Mac nie widzi PC w obecnej sieci, a zapora PC wpuszcza SSH tylko ze starego adresu Maca.
Sekretów (pliki `.env`, klucze) nie wysyłamy do repozytoriów: zostają w archiwum na Macu, a do przeniesienia do menedżera haseł przez właściciela.

| Co | Gdzie na PC | Dokąd | Wymaga zgody | Stan |
|---|---|---|---|---|
| Opisarnia: gałąź `feat/pokaz-opisarnia` (778 zmian, PoC „Pokaz”) | `Desktop\generator-opisow-mebli` | commit „wip: pokaz” na tej gałęzi i push do prywatnego repo | tak (commit i push) | |
| Opisarnia: 5 worktree Claude (`.claude/worktrees`) | jw. | sprawdzić niewypchnięte commity; wypchnąć albo do archiwum | tak | |
| Oprogramowani: CompanyAudits (70 zmian, nieśledzone pliki) | `Desktop\CompanyAudits` | commit i push do `company-audits` (bez danych osobowych firm w jawnej formie: repo prywatne) | tak | |
| Oprogramowani: strona (4 zmiany) | `Desktop\oprogramowani-onepager` | commit i push | tak | |
| Oprogramowani: LeadyV2, LeadEngine (bez git) | `Desktop\Reaserch` | nowe prywatne repo albo folder w `company-audits` | tak (nowe repo) | |
| Asystent zleceń, część Useme i Facebook (bez git) | `C:\Users\Guest\Zlecenia`, `Documents\ChatGPT\Zlecenia` | nowe prywatne repo `asystent-useme` | tak (nowe repo) | |
| Szukanie auta, rozszerzenie OLX i OTOMOTO (bez git) | jw. | osobne prywatne repo albo tylko archiwum | decyzja | |
| NaulikApp: gałęzie `fix/rc1-nagrania`, `marketing/kampania-rc1` | `Desktop\NaulikApp` | sprawdzić, czy są na origin; jeśli nie, push | tak | |
| Warsztat | `Desktop\Warsztat` | już na GitHubie (sprawdzone 14.11); sprawdzić tylko niewypchnięte | — | |
| Wtyczki Claude: `social-publisher`, `agent-quest` | `Plugins`, `claude-mods` | prywatne repo `claude-wtyczki` | tak (nowe repo) | |
| Pozostałe własne repozytoria ze zmianami (migracja-claude-code-kit 65, AdvanceStockBotTrading 99, GymInteligentApp 16, odys_frontend, UnDrown i inne) | `source\repos`, `Desktop`, `AndroidStudioProjects` | archiwum na Macu w całości; push tylko na życzenie | decyzja | |
| Projekty bez git (sejm-radar, mountain-stories, meble-ai-agents, CostLab, OrderChecker, uigen i inne) | `Desktop`, `Downloads`, `source\repos` | archiwum na Macu | — | |
| Repozytoria pracodawcy (klient 2) | `source\repos`, `Documents\GitHub` | nie do chmury (D10): dysk zewnętrzny albo usunięcie | decyzja | |
| Rozmowy Claude Code (1012 plików) i sesje Codex (38) | `C:\Users\Guest\.claude`, `.codex` | archiwum na Macu; w jednej rozmowie jest klucz Mistral do unieważnienia | — | |
| Audyt PC i kopie robocze z WSL | `/home/claude/audyt-pc` | archiwum na Macu | — | |
| Dane Dockera (33 GB) | `E:\Docker\DockerDesktopWSL` | sprawdzić, czy jest tam coś poza lokalną bazą deweloperską; zwykle do pominięcia | decyzja | |
| Profil Chrome: rozszerzenia „Opisarnia – zbieranie opisów”, asystenci | Chrome na PC | kod rozszerzeń w repozytoriach; instalacja w Chrome na Macu | — | |
| Pliki osobiste (Pulpit, Dokumenty, Pobrane, Obrazy) | profil Guest i `dominik` | archiwum albo dysk zewnętrzny; profil `dominik` tylko z Twojego konta | decyzja | |

## Przed sprzedażą PC

- Usunąć z Harmonogramu zadań autostart asystenta, wyłączyć sshd, portproxy i reguły zapory (albo pełny reset).
- Wylogować konta (Microsoft, Google, GitHub, Claude, Codex), unieważnić klucze SSH tego komputera na GitHubie.
- Reset Windows „Usuń wszystko” z czyszczeniem dysków (C: i E:).

## Decyzje właściciela przed etapem 1

1. Repozytoria pracodawcy: dysk zewnętrzny czy usunięcie?
2. Szukanie auta: osobne repo czy tylko archiwum?
3. Pozostałe własne repozytoria: tylko archiwum czy także push na GitHub?
4. Dane Dockera na E: i pliki osobiste: co zabrać?
