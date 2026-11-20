# Rozwój panelu na serwerze

Panel (IntegrateSystems) rozwija agent na serwerze, nie na Macu. Właściciel rozmawia z nim w aplikacji Claude
(zakładka Code, połączenie SSH) i wdraża zmiany przyciskiem w panelu.

## Układ

| Co | Gdzie | Kto |
|----|-------|-----|
| Produkcja | `/home/panel/IntegrateSystems`, port 4801, https://2-29-181-133.sslip.io | użytkownik `panel`; agent jej nie zmienia |
| Kopia robocza | `/home/agent/rozwoj/IntegrateSystems`, gałąź `rozwoj` | użytkownik `agent` (sesje SSH i Claude) |
| Panel testowy | port 4802, https://test.2-29-181-133.sslip.io, dane przykładowe, bez agentów | `panel-testowy.service` jako `agent` |
| Wdrożenie | `/usr/local/bin/wdroz-panel` (`wdroz-panel.service`) | przycisk „Wdróż” w panelu: Serwer → Rozwój panelu |

Instalacja i aktualizacja skryptów: `sudo bash uruchom/serwer/zainstaluj-rozwoj.sh` (w repozytorium produkcji).

## Zasady dla agenta w kopii roboczej

- Pracujesz tylko na gałęzi `rozwoj` w `/home/agent/rozwoj/IntegrateSystems`. Nie masz dostępu do GitHuba, sekretów
  (`/etc/integrate`) ani produkcji (port 4801 zablokowany); tak ma zostać.
- Przed pracą: `git fetch origin && git merge origin/main` (origin to repozytorium produkcji; trafiają tam też
  zmiany kart z serwera).
- Po zmianie: testy `cd dashboard/testy && python3 -m unittest discover -q`, potem
  `sudo systemctl restart panel-testowy.service` i sprawdzenie na https://test.2-29-181-133.sslip.io (albo
  `curl -s http://127.0.0.1:4802/`). Hasło panelu testowego widzi właściciel w panelu.
- Gotową zmianę zapisujesz commitem na `rozwoj` (opis po polsku, co i po co). Nie wdrażasz sam: właściciel klika
  „Wdróż”.
- Nie usuwasz funkcji panelu bez zgody właściciela. Zmiany w `uruchom/serwer/` (usługi, sudo, zapora) wymagają
  ponownej instalacji przez `ops` i decyzji właściciela.

## Co robi „Wdróż”

1. Testy na zatwierdzonym commicie gałęzi `rozwoj` (jako `agent`, w osobnej kopii).
2. `git pull` produkcji, scalenie `rozwoj` do `main`.
3. Restart panelu, kontrola: `/api/data` odpowiada, strona pokazuje widok bez błędu JavaScript (Playwright).
4. Push `main` do GitHuba.
5. Błąd w punkcie 3: produkcja wraca do poprzedniego commita (`git reset --keep`, zmiany kart na dysku zostają),
   panel startuje ponownie, właściciel dostaje powiadomienie. Dziennik: panel, Serwer → Rozwój panelu.

## Kontekst

Pamięć z rozmów na Macu: `~/.claude/projects/-home-agent-rozwoj-IntegrateSystems/memory/` (użytkownik `agent`).
Rozmowy z Maca (bez obrazów, klucze zamaskowane): `/home/agent/rozwoj/rozmowy-mac/`.
