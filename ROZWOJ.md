# Rozwój panelu na serwerze

Panel (IntegrateSystems) rozwija agent na serwerze, nie na Macu. Właściciel rozmawia z nim w aplikacji Claude:
na telefonie i w przeglądarce przez Remote Control (zakładka Code, sesja „Rozwój panelu”), na Macu także przez SSH.
Commit na gałęzi `rozwoj` wdraża się sam.

## Układ

| Co | Gdzie | Kto |
|----|-------|-----|
| Produkcja | `/home/panel/IntegrateSystems`, port 4801, https://2-29-181-133.sslip.io | użytkownik `panel`; agent jej nie zmienia |
| Kopia robocza | `/home/agent/rozwoj/IntegrateSystems`, gałąź `rozwoj` | użytkownik `agent` (sesje SSH i Claude) |
| Panel testowy | port 4802, https://test.2-29-181-133.sslip.io, dane przykładowe, bez agentów | `panel-testowy.service` jako `agent` |
| Sesja Claude na telefonie | `claude-zdalnie.service`: Remote Control w kopii roboczej, aplikacja Claude → Code → „Rozwój panelu” | użytkownik `agent` |
| Wdrożenie | `/usr/local/bin/wdroz-panel` | samo po commicie na `rozwoj` (`wdroz-panel-auto.path`, zapasowo co 5 min); ręcznie przycisk w panelu: Serwer → Rozwój panelu |

Instalacja i aktualizacja skryptów: `sudo bash uruchom/serwer/zainstaluj-rozwoj.sh` (w repozytorium produkcji).

## Zasady dla agenta w kopii roboczej

- Pracujesz tylko na gałęzi `rozwoj` w `/home/agent/rozwoj/IntegrateSystems`. Nie masz dostępu do GitHuba, sekretów
  (`/etc/integrate`), sudo ani produkcji (port 4801 zablokowany); tak ma zostać. Klucze SSH konta `agent` są w pliku
  roota `/etc/ssh/klucze-agenta`; nie dopisujesz kluczy.
- Przed pracą: `git fetch origin && git merge origin/main` (origin to repozytorium produkcji; trafiają tam też
  zmiany kart z serwera).
- Po zmianie: testy `cd dashboard/testy && python3 -m unittest discover -q`, potem
  restart panelu testowego `pkill -u agent -f '^/usr/bin/python3 dashboard/server.py'` (systemd uruchamia go
  ponownie po 3 s) i sprawdzenie na https://test.2-29-181-133.sslip.io (albo
  `curl -s http://127.0.0.1:4802/`). Hasło panelu testowego widzi właściciel w panelu.
- **Commit na `rozwoj` = wdrożenie na produkcję** (po ok. 20 s, gdy testy przejdą). Commitujesz tylko gotową,
  sprawdzoną zmianę (testy zielone, panel testowy obejrzany), opis po polsku: co i po co. Prace w toku trzymasz
  bez commita albo na innej gałęzi.
- Nie usuwasz funkcji panelu bez zgody właściciela. Zmiany w `uruchom/serwer/` (usługi, sudo, zapora) wymagają
  ponownej instalacji przez `ops` i decyzji właściciela.

## Co robi wdrożenie (automat i przycisk)

0. Automat pomija commit, którego wdrożenie już się nie udało; następny commit na `rozwoj` próbuje ponownie.
1. Testy na zatwierdzonym commicie gałęzi `rozwoj` (jako `agent`, w osobnej kopii).
2. `git pull` produkcji, scalenie `rozwoj` do `main`.
3. Restart panelu, kontrola: `/api/data` odpowiada, strona pokazuje widok bez błędu JavaScript (Playwright).
4. Push `main` do GitHuba.
5. Błąd w punkcie 3: produkcja wraca do poprzedniego commita (`git reset --keep`, zmiany kart na dysku zostają),
   panel startuje ponownie, właściciel dostaje powiadomienie. Dziennik: panel, Serwer → Rozwój panelu.

## Kontekst

Pamięć z rozmów na Macu: `~/.claude/projects/-home-agent-rozwoj-IntegrateSystems/memory/` (użytkownik `agent`).
Rozmowy z Maca (bez obrazów, klucze zamaskowane): `/home/agent/rozwoj/rozmowy-mac/`.

## Zlecenia w widoku Agenci

Panel na serwerze czyta katalog `/home/agent/rozwoj`. Ustaw `PANEL_ROZWOJ_DIR`, aby wskazać inny
katalog. Pusta wartość wyłącza odczyt. Na Macu i PC katalog trzeba wskazać jawnie.

- Nazwij plik `ZLECENIE-nazwa.md` i wpisz tytuł w pierwszym wierszu. Sam plik `.md` oznacza kolejkę.
- Gdy zlecenie rusza, panel rozpoznaje odpowiadający mu `ZLECENIE-nazwa.log` ze zdarzeniami JSON
  Claude lub Codex (po jednym na wiersz). Odczytuje istniejące pliki i sam nie zapisuje tam logów.
- Zdarzenie końca lub plik `ZLECENIE-nazwa.wynik.md` przenosi zlecenie do historii. Wynik otwiera się
  jako tekst. Po 15 minutach bez zapisu i bez zdarzenia końca stan jest nieznany.
- Panel musi mieć prawo odczytu tych plików i dostępu do katalogu. Odczytuje ostatnie 2 MiB logu.
  Jeśli w logu brakuje daty startu, karta podaje czas od pierwszej obserwacji logu.

## Zmiany wyglądu: obowiązkowo na dużym zestawie

Dane przykładowe (`dashboard/przyklad`, 3 projekty) są za małe, żeby ocenić wygląd. Każdą zmianę wyglądu sprawdzasz
też na zestawie w skali produkcji (`dashboard/przyklad-duzy/zbuduj.py`: 10 projektów, 44 sprawy dla Ciebie, w tym
30 po terminie, tytuły ponad 100 znaków, nazwy z nawiasami, 12 publikacji w tygodniu, pytania z opcjami, zgody,
odbiory). Dane są syntetyczne, daty liczone od dziś.

```
python3 dashboard/przyklad-duzy/zbuduj.py /tmp/duzy
PANEL_REGISTRY=/tmp/duzy/projekty.json PANEL_HOST=127.0.0.1 PANEL_PORT=4803 PANEL_TOKEN= python3 dashboard/server.py
```

- Zrzuty Playwright (`/home/agent/narzedzia/pw/bin/python`) zmienionych widoków w 390 i 1440 px, w obu motywach;
  porównaj z poprzednimi (ta sama nazwa z `-przed` / `-po`). Panel zatrzymaj po sprawdzeniu.
- `dashboard/testy/test_asystent_duzy.py` (z renderem, bez `PANEL_TESTY_BEZ_RENDERU`) pilnuje na tym zestawie: liczb
  spraw z jednego źródła (`projekt.owner_counts` = `pm.py` = `/api/data` = menu = karta = listy panelu), kart domyślnych
  bez duplikatów, startu scen bez listy, braku poziomego przewijania 390–1920 px i błędów JS.
- Odpowiedź modelu z długim akapitem pokazuje atrapa Claude (`dashboard/testy/atrapa_claude.py`, wiadomość
  z „długa odpowiedź”), np. `PANEL_CLAUDE=dashboard/testy/atrapa_claude.py`.
