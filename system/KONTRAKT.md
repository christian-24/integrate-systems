# Kontrakt etapu 1

Wiążący dla `zbieracz.py` (Mac) i `serce.py` (PC). Podstawa: `ksiega/KSIEGA.md` wersja 1, sekcje 4–9, 11–14.
Python 3.9, tylko biblioteka standardowa, polecenie `git` w PATH. Kod działa na macOS i Windows.

## Pliki kodu

| Plik | Kto pisze | Rola |
|---|---|---|
| `wspolne.py` | gotowy | ustawienia, zapis atomowy, JSON, JSONL, tożsamość, czas, git |
| `zbieracz.py` | subagent A | Mac: inwentarz, stan projektów, decyzje P2, wypchnięcie gałęzi `mac` |
| `serce.py` | subagent B | PC: scalanie, bot Telegram, raport 7:00, sygnał życia |
| `testy/` | A i B | `python3 -m unittest discover -s system/testy`, bez sieci (atrapa Telegrama, lokalne repozytorium bare) |

## Ustawienia

Zmienne środowiska albo plik `system/system.env` (`KLUCZ=wartość`, `#` komentarz; środowisko ma pierwszeństwo). Czyta `wspolne.ustawienia()`.

| Klucz | Kto | Domyślnie | Znaczenie |
|---|---|---|---|
| `STAN_DIR` | oba | `~/stan-systemu` | lokalny klon repozytorium stanu |
| `LOKALNE_DIR` | oba | `~/.integrate-lokalne` | pliki, które nigdy nie trafiają do git |
| `SKANUJ` | zbieracz | `~` | katalogi do szukania repozytoriów, rozdzielone `;` |
| `GLEBOKOSC` | zbieracz | `4` | maksymalna głębokość szukania `.git` |
| `CLAUDE_PROJEKTY` | zbieracz | `~/.claude/projects` | katalog sesji Claude Code |
| `HC_ZBIERACZ` | zbieracz | puste | adres pingu healthchecks dla zbieracza |
| `TELEGRAM_TOKEN` | serce | — | token bota (wymagany do bota) |
| `TELEGRAM_CHAT` | serce | — | jedyny dozwolony `chat_id` |
| `TELEGRAM_API` | serce | `https://api.telegram.org` | adres API (testy: atrapa) |
| `HC_SERCE`, `HC_RAPORT` | serce | puste | adresy pingów healthchecks |
| `RAPORT_GODZINA` | serce | `7` | godzina raportu Europe/Warsaw |
| `CISZA` | serce | `22-7` | cisza nocna |
| `CYKL_S` | serce | `300` | odstęp cyklu git |

Sekretów nie ma w repozytorium stanu ani w logach.

## Repozytorium stanu

Gałąź `main` pisze tylko serce. Gałąź `mac` pisze tylko zbieracz i zmienia w niej wyłącznie katalog `mac/`.

```
projekty.json            serce   {"projekty": [Projekt]}
pomysly.md               serce   wiersze "- RRRR-MM-DD HH:MM | <id> | tekst"
mac/inwentarz.json       Mac     {"czas": ISO, "kandydaci": [Kandydat]}
mac/stan.json            Mac     {"czas": ISO, "projekty": [StanProjektu]}
mac/decyzje.jsonl        Mac     Decyzja na wiersz, tylko dopisywane
mac/zdarzenia/RRRR-MM-DD.jsonl  Mac   Zdarzenie
pc/zdarzenia/RRRR-MM-DD.jsonl   serce Zdarzenie
pc/odrzucone.jsonl       serce   wiersze, których nie da się odczytać
.gitignore               init    lokalne/, *.tmp
```

Czas: ISO 8601 ze strefą Europe/Warsaw (`wspolne.teraz()`).

**Kandydat** (tylko dane jawne; nazwa i ścieżka nigdy):
`{"tozsamosc": "a1b2c3d4e5f6", "alias": "K-a1b2", "zrodla": ["git","claude"], "ostatnia_aktywnosc": ISO|null, "commity": int, "sesje": int}`

**Decyzja** (P2 na Macu): `{"czas": ISO, "tozsamosc": str, "stan": "w realizacji"|"backlog"|"w przygotowaniu"|"archiwum"|"wykluczony"|"scalony", "alias": str, "klient": bool, "scalony_z": str|null}`

**Projekt** (`projekty.json`, serce przepisuje z decyzji; ostatnia decyzja dla tożsamości wygrywa):
`{"tozsamosc": str, "alias": str, "stan": str, "klient": bool, "obszar": "praca", "zdecydowano": ISO, "scalony_z": str|null}`

**StanProjektu** (tylko projekty ze stanem „w realizacji”, „w przygotowaniu”, „wstrzymany”, „backlog”):
`{"tozsamosc": str, "alias": str, "nazwa": str|null, "otwarte": int, "zrobione": int, "czeka_na_ciebie": int, "po_terminie": int, "zablokowane": int, "ma_zadania": bool, "ostatni_commit": ISO|null, "ostatnia_sesja": ISO|null}`
`nazwa` jest wypełniona tylko gdy `klient` = false. Liczby z `standard/projekt.py` (`parse_tasks`) na `ZADANIA.md` projektu, logika „po terminie” i „czeka na Ciebie” jak w `standard/pm.py`.

**Zdarzenie**: `{"id": str, "zrodlo": str, "czas": ISO, "projekt": alias|null, "typ": str, "waga": "pilne"|"info"|"szum", "tytul": str, "link": str|null}`
`tytul` tworzy kod z typu (np. „Nowy commit”, „Brak dostępu do katalogu”), nigdy z treści źródła. Typy etapu 1: `commit`, `sesja`, `kandydat`, `brak-dostepu`, `nie-rozumiem-pliku`, `push-nieudany`, `system-wznowiony`.

## Pliki lokalne (`LOKALNE_DIR`, nigdy w git)

| Plik | Kto | Treść |
|---|---|---|
| `aliasy.json` | zbieracz | `{tozsamosc: {"nazwa", "sciezka", "zdalne"}}` |
| `kolejka.jsonl` | zbieracz | zdarzenia czekające na wypchnięcie (najwyżej 10 000, najstarsze odpadają) |
| `serce.json` | serce | `offset` Telegrama, czas ostatniego udanego cyklu, data ostatniego raportu, liczba pilnych dziś, ostatnie pomysły do cofnięcia |
| `dziennik.log` | serce | odrzucone wiadomości, czasy odpowiedzi, błędy (bez tokenu) |

## Tożsamość

`wspolne.tozsamosc(zdalne, sciezka)`: SHA-256 z adresu zdalnego repozytorium (bez `.git`, bez danych logowania, małe litery) albo, gdy go nie ma, z pełnej ścieżki; pierwsze 12 znaków hex. Alias tymczasowy: `K-` + 4 pierwsze znaki.

## Zbieracz (`python3 system/zbieracz.py <polecenie>`)

| Polecenie | Działanie |
|---|---|
| `init <adres-repo>` | klonuje repozytorium stanu do `STAN_DIR` (albo zakłada puste z `.gitignore` i gałęziami `main`, `mac`, gdy repozytorium jest puste), ustawia gałąź `mac` |
| `zbierz` (domyślne) | skanuje, liczy, zapisuje `mac/`, commit i push gałęzi `mac` (3 próby), ping `HC_ZBIERACZ` po udanym push; bez sieci zdarzenia czekają w kolejce |
| `kandydaci` | lista kandydatów z nazwą i ścieżką z `aliasy.json` (tylko na ekran) |
| `kwalifikuj` | interaktywnie: dla każdego kandydata bez decyzji pyta o stan, klient (domyślnie tak), alias; dopisuje do `mac/decyzje.jsonl`; potem `zbierz` |
| `podglad` | to samo co `zbierz`, ale bez git: wypisuje liczby (ilu kandydatów, ile projektów), żadnych nazw |

Skanowanie: katalogi z `.git` do `GLEBOKOSC`, z pominięciem `node_modules`, `.venv`, `venv`, `Library`, `.Trash`, ukrytych katalogów (poza `.git` jako znacznikiem), klonów bez commitów autora (gdy `git log --author=$(git config user.email)` puste i jest zdalne). Sesje Claude: tylko pole `cwd` z pierwszych wierszy plików `.jsonl` oraz czas modyfikacji i liczba plików; treści nie czyta. Projekt Claude bez repozytorium = kandydat po ścieżce. Brak uprawnień → zdarzenie `brak-dostepu`. Nieczytelny plik sesji → `nie-rozumiem-pliku`.

## Serce (`python serce.py`)

Jedna pętla, jeden wątek, jedyny zapisujący:
1. long polling `getUpdates` (timeout 25 s, `offset` z `serce.json`); obsługa wiadomości,
2. co `CYKL_S`: `git fetch`, `git checkout origin/mac -- mac/` na `main`, przepisanie `projekty.json` z `mac/decyzje.jsonl`, commit, push z 3 próbami; po udanym cyklu ping `HC_SERCE`; nieudany push po ponowieniach → zdarzenie pilne,
3. o `RAPORT_GODZINA` raz dziennie (data w `serce.json`) raport, potem ping `HC_RAPORT`.

Bot:
- wiadomość z innego `chat_id` albo z grupy → brak odpowiedzi, wpis w `dziennik.log`,
- `/stan` → stan z `mac/stan.json` i `projekty.json`: aktywne projekty (alias albo nazwa, otwarte, czeka na Ciebie, po terminie, zablokowane, „brak ZADANIA.md”), backlog (aliasy), „dane z Maca z HH:MM”, liczba kandydatów bez decyzji,
- `/pomysl <tekst>` → wpis w `pomysly.md`, odpowiedź z przyciskiem „Cofnij” (`callback_data` `cofnij:<id>`), cofnięcie działa 24 h,
- inna komenda → lista komend; zdjęcie, głos, plik → „Obsługuję tylko tekst.”,
- start po przerwie dłuższej niż 24 h → „System działa ponownie od HH:MM. Wiadomości wysłane w czasie przerwy mogły zginąć.” i jedno zdarzenie `system-wznowiony`,
- cisza nocna: wiadomości z własnej inicjatywy czekają do końca ciszy, poza „system nie działa” (pilne); najwyżej 5 pilnych dziennie.

Raport 7:00: to samo co `/stan` + świeżość danych z Maca (ostrzeżenie, gdy starsze niż 26 h) + liczba pomysłów z ostatniej doby + liczba wierszy w `pc/odrzucone.jsonl` z ostatniej doby.

Dane w wiadomościach: dla projektów z `klient: true` tylko alias i liczby (sekcja 9 księgi).
