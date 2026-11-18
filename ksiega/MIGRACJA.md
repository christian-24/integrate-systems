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

## Serwer: kopie i kontrola zdrowia

Pliki w `uruchom/serwer/`. Instalacja (jako ops, po pobraniu zmian na serwer przez zapis kart):

```
sudo bash /home/panel/IntegrateSystems/uruchom/serwer/zainstaluj-kopie-i-zdrowie.sh
```

Skrypt instaluje `kopia`, `zdrowie` i nową wersję `zapis-kart` w `/usr/local/bin`, jednostki w `/etc/systemd/system`, włącza timery i robi pierwszy przebieg obu. Ustawienia opcjonalne: `/etc/integrate/serwer.env` (wzór `serwer.env.przyklad`), powiadomienia przez `PANEL_NTFY_URL` z `/etc/integrate/panel.env`.

| Co | Kiedy | Co robi | Powiadomienie |
|---|---|---|---|
| Kopia (`kopia.timer`) | codziennie 03:30 czasu polskiego | `/home/panel/kopie/RRRR-MM-DD.tar.gz`: `dane/` (bazy SQLite jako spójna kopia w `sqlite/`), `uruchomienia/`, `historia/`, zmienione i nieśledzone pliki projektów z `git status`, niewypchnięte commity jako `git/<repo>.bundle`; zostaje 14 najnowszych | tylko przy błędzie |
| Wysyłka poza serwer | po kopii, gdy ustawiony `KOPIA_CEL` | `rclone:<zdalny>:<folder>` albo `scp:<użytkownik@host>:<folder>`; bez `KOPIA_CEL` pomijana | przy błędzie |
| Kontrola zdrowia (`zdrowie.timer`) | co 10 min | panel (`/api/data` lokalnie → 200), Useme (`/api/health`), wolne miejsce ≥ 15%, Claude zalogowany, kopia młodsza niż 36 h, ostatni zapis kart; stan w `/home/panel/.zdrowie-stan` | przy zmianie na zły i z powrotem na dobry, bez danych klientów |
| Zapis kart (`zapis-kart.timer`) | co 15 min | jak dotąd; pliki wyglądające na sekrety i bazy (`.env*`, `*.env`, `*.key`, `*.pem`, `credentials*`, `*.sqlite`, `*.db`) pomija z ostrzeżeniem w dzienniku; `*.przyklad` wchodzą | przez kontrolę zdrowia |

Sprawdzenie: `systemctl list-timers kopia.timer zdrowie.timer zapis-kart.timer`, `journalctl -u kopia -n 5`, `journalctl -u zdrowie -n 7`.
Przywracanie: `tar -xzf /home/panel/kopie/RRRR-MM-DD.tar.gz -C /tmp/przywracanie`, opis w `kopia-info.txt` w archiwum. Bazy z `sqlite/<ścieżka>` zastępują pliki pod `<ścieżka>` przy zatrzymanej usłudze (`sudo systemctl stop useme`).
Kopia na tym samym dysku nie chroni przed utratą serwera: do tego Backups w Hetznerze (cały serwer, 7 ostatnich dni) albo `KOPIA_CEL` (zdalny rclone typu crypt, bo archiwum zawiera dane klientów). Zewnętrzny monitoring adresu panelu (UptimeRobot) zgłasza awarię całego serwera, której kontrola zdrowia na tym serwerze nie wyśle.
