# Kontrakt: nowy pulpit projektów

Wiążący dla przebudowy panelu na porcie 4801. Wzór wyglądu i układu: `ksiega/pulpit-projektow.html`
(prototyp na danych przykładowych). Zasady dostępu, agentów i zapisu z `dashboard/AGENCI.md` i `dashboard/README.md` obowiązują bez zmian.

Cel: właściciel otwiera panel i od razu wie, gdzie jest każdy projekt (faza, stan, postęp, najbliższy termin, zgodność z księgą),
co czeka na niego, a w razie potrzeby wchodzi w projekt: tablica, wskaźniki, etapy, księga, marketing.

## Backend (`server.py`, `standard/projekt.py`, nowy `historia.py`)

### 1. Nowe pola projektu (`/api/data` → `projects[]`)

| Pole | Skąd | Wartości |
|---|---|---|
| `phase` | `KARTA.md`, wiersz `- faza:`; bez niego wyliczane | `pomysl`, `ksiega`, `budowa`, `wdrozenie`, `marketing`, `utrzymanie` |
| `phaseSource` | | `karta` albo `wyliczona` |
| `client` | `KARTA.md`, `- klient: tak|nie`; bez niego z decyzji zbieracza; domyślnie `true` | bool |
| `threshold` | `KARTA.md`, `- próg: lekka|pełna`; domyślnie `pełna` dla `client`, `lekka` dla pozostałych | `lekka`, `pelna` |
| `description` | pierwszy akapit sekcji „Cel” (to samo co `goal`, pełne zdania, do 300 znaków) | tekst |
| `alias` | decyzja zbieracza, gdy jest | tekst albo null |
| `state` | jak dziś, plus `backlog` (z `- stan: backlog` albo decyzji zbieracza) | `active`, `paused`, `done`, `backlog` |
| `book` | lista z `docs` w kolejności standardu: `{key, label, file, status, gaps}`; `bookOk`, `bookTotal` | status `ok`, `gaps`, `missing` |

Faza wyliczona, pierwsza pasująca: `state` = `backlog` → `pomysl`; brak `KARTA.md` albo karta z brakami → `ksiega`;
kampania w stanie „w toku” → `marketing`; wszystkie etapy zrobione → `utrzymanie`; inaczej → `budowa`.

### 2. Projekty bez ręcznej rejestracji

Źródła folderów projektów, sumowane bez duplikatów (po realpath):
1. rejestr `projekty.json` (jak dziś),
2. projekty zakwalifikowane zbieraczem na tym komputerze: `LOKALNE_DIR/aliasy.json` (ścieżka) + ostatnia decyzja z `STAN_DIR/mac/decyzje.jsonl`
   o stanie `w realizacji`, `w przygotowaniu`, `wstrzymany` albo `backlog`. Ustawienia czytane przez `system/wspolne.ustawienia()`.
   Brak plików zbieracza to nie błąd.

`projectsSource` = `registry`, gdy jest choć jeden projekt z 1 albo 2; inaczej `sample`. Projekty przykładowe tylko gdy oba źródła puste.
Folder z decyzji zbieracza, który nie ma plików standardu, pokazuje się z fazą `ksiega` i brakami w `book` (nie jest zakładany automatycznie).

### 3. Historia stanów (`historia.py`)

- Przy każdym `build_data()` dla `projectsSource` = `registry`: zapis `HISTORIA_DIR/RRRR-MM-DD.json` (domyślnie `IntegrateSystems/historia/`,
  zmienna `PANEL_HISTORY_DIR` do testów), zapis atomowy, nadpisuje plik z tego dnia:
  `{"date": "RRRR-MM-DD", "projects": {"<pid>": {"todo": n, "wip": n, "rev": n, "blocked": n, "done": n, "total": n}}}`.
- `/api/data` → `history`: lista takich wpisów z ostatnich 63 dni, rosnąco po dacie.
- Dla `sample`: `history` z pliku `dashboard/historia-przyklad.json` (daty względne `-56` … `0`, zamieniane na bezwzględne), spójny z projektami przykładowymi.
- Liczenie stanów zadania (tylko `kind` = `zadanie`, publikacje kampanii osobno): `done` = stan zrobione; `rev` = otwarte z `wymaga: odbiór`;
  `blocked` = stan `[!]`; `wip` = stan `[~]`; `todo` = reszta otwartych.

### 4. Edycja pól karty

`POST /api/project/meta` `{"id", "phase"?, "client"?, "threshold"?}` → zmienia albo dopisuje wiersze `- faza:`, `- klient:`, `- próg:` pod tytułem `KARTA.md`
(zapis atomowy, tylko projekty z rejestru albo ze zbieracza). Błędy jak w innych zapisach.

### 5. Bez zmian

Wszystkie istniejące pola i trasy zostają (`tasks`, `stages`, `campaigns`, `calendar`, `agents`, `pmNote`, `icsPath`, `standard`, zapisy `/api/task/*`,
`/api/stage/update`, `/api/campaign/update`, `/api/project/add|remove`, `/api/agent/*`, `/api/calendar/connect`, `/podglad`, `--export`, dostęp z hasłem).
`agenci-przyklad.json`, `kalendarz-przyklad.json` i przykłady w `przyklad/` mogą dostać nowe pola karty (`faza`, `klient`, `próg`).

## Frontend (`panel.html`, przepisany)

Kontrakt strony jak dziś: bez `<!doctype>/<html>/<head>/<body>`, tokeny na `:root`, jasny i ciemny motyw, `const PREVIEW=/*PREVIEW*/null; const LIVE=PREVIEW===null;`,
localStorage w try/catch, jedna funkcja IIFE, brak poziomego przewijania przy 375, 1000 i 1400 px, odświeżanie danych jak dziś (60 s, 3 s gdy agent pracuje, 15 s przy edycji).

Wygląd i układ jak `ksiega/pulpit-projektow.html`: czcionka systemowa, plakietki stanów, panel boczny (widoki + lista projektów z wyszukiwarką `/`),
okruszki, na wąskim ekranie lista rozwijana zamiast panelu bocznego.

| Widok (adres `#…`) | Zawartość |
|---|---|
| `przeglad` | stan systemu (dane z Maca, agenci, kalendarz), 4 liczby, tabela projektów (nazwa, opis, faza, stan, postęp, najbliższy termin, księga), „Wymaga Ciebie”, terminy 7 dni, notatka PM (`pmNote`) z przyciskiem „Raport PM” |
| `wskazniki` | zakres: cały portfel albo projekt; kafelki (postęp, tempo, praca w toku, zaległe, etapy w terminie), wykresy z `history` (postęp w czasie, zakończone na tydzień, przepływ), kto wykonuje, porównanie projektów; gdy historii jest mniej niż 2 tygodnie: komunikat „Historia od DD.MM, wykresy wypełnią się z czasem” zamiast pustych wykresów |
| `ty` | zadania `kto: ty` i z `wymaga` ze wszystkich projektów |
| `tablica` | Kanban wszystkich projektów: Do zrobienia, W toku, Do odbioru, Zrobione; filtr projektu (lista), „Tylko moje”; zablokowane w kolumnie W toku z plakietką „zablokowane” i powodem |
| `terminy` | po terminie, ten tydzień, następny, później: końce etapów, terminy zadań, publikacje, wydarzenia kalendarza; łączenie kalendarza i adres ICS jak dziś |
| `agenci` | wszystko z dzisiejszej zakładki Agenci: stan logowania z poleceniem `loginCmd` i „Kopiuj”, limit, Automat, Raport PM, Test połączenia, lista uruchomień z zatrzymaniem i podglądem |
| `projekty` | dzisiejsza zakładka Standard: dodawanie projektu (formularz), usuwanie z rejestru z potwierdzeniem, opis standardu, braki |
| `p-<id>` z podwidokami `-tablica`, `-wskazniki`, `-etapy`, `-ksiega`, `-marketing` | nagłówek (nazwa, alias, stan, klient/własny, opis, pasek faz z edycją fazy przez `/api/project/meta`, 4 fakty), tablica projektu, wskaźniki projektu ze spalaniem bieżącego etapu, etapy z osią czasu i edycją terminu (`/api/stage/update`), księga (`book` z brakami), marketing (kampanie, publikacje, cel i wynik; edycja jak dziś) |

Karta zadania otwiera szufladę: tytuł, projekt, etap, stan, wykonawca, termin, wymaga, blokada, plik i wiersz; przyciski zmiany stanu (`/api/task/state`),
edycja tytułu i terminu (`/api/task/update`), „Uruchom agenta” z `runBlock` jako powodem wyłączenia (`/api/agent/run`), podgląd uruchomienia (`runId`).
Dodawanie zadania z tablicy projektu (`/api/task/add`).

Klawisze: `/` szukaj projektu, `g` potem `p`/`w`/`t`/`d`/`a` przejście do widoku (przegląd, wskaźniki, tablica, terminy, agenci), `Esc` zamyka szufladę,
w szufladzie `r` uruchamia agenta. Wszystko osiągalne klawiaturą.

Teksty krótko i rzeczowo, bez słownictwa z gier. Kolory projektów z palety w kolejności (niebieski, pomarańczowy, morski, żółty, magenta, zielony, fiolet, czerwony),
stany etapów: w normie, zagrożony, po terminie, czeka na Ciebie, zrobione — zawsze kolor z podpisem.

## Testy

`python3 -m unittest discover -s dashboard/testy` przechodzi. Nowe testy: pola projektu i faza wyliczona, projekty ze zbieracza (katalogi tymczasowe),
zapis i odczyt historii, `/api/project/meta`, `/api/data` w trybie przykładowym zawiera `history`.
