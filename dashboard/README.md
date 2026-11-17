# Panel projektów

Raport PM, monitor zadań z edycją, uruchamianie agentów, kampanie i kalendarz w jednym miejscu.
Panel niczego nie przechowuje sam: czyta i zmienia pliki projektów opisane w `../standard/STANDARD.md`.

## Uruchomienie

    python3 server.py

Bez terminala: dwuklik `Panel.command` w folderze IntegrateSystems (uruchamia panel i otwiera stronę; gdy panel już działa, tylko otwiera stronę).

Panel: http://localhost:4801/ (sam Python 3). `http://localhost:4801/podglad` to ta sama strona
z danymi przykładowymi; zmiany zostają tam tylko w pamięci strony.

Stałe uruchamianie na Macu i na PC, logowanie narzędzi i dostęp z telefonu: `../INSTALACJA.md`.
Ustawienia: zmienne środowiska albo `panel.env` (wzór: `panel.env.przyklad`).

## Widoki

Układ i kontrakt: `PULPIT.md`. Panel boczny: widoki i lista projektów z wyszukiwarką; na wąskim ekranie lista rozwijana.

| Widok | Adres | Do czego |
|---|---|---|
| Przegląd | `#przeglad` | stan systemu, 4 liczby, tabela projektów (opis, faza, stan, postęp, najbliższy termin, księga), notatka PM, ryzyka, wymaga Ciebie, terminy 7 dni |
| Wskaźniki | `#wskazniki` | postęp, tempo, praca w toku, zaległe, etapy w terminie; wykresy z historii; cały portfel albo jeden projekt |
| Wymaga Ciebie | `#ty` | zgody, odbiory i Twoje zadania |
| Tablica | `#tablica` | Kanban wszystkich projektów: do zrobienia, w toku, do odbioru, zrobione |
| Terminy | `#terminy` | po terminie, ten tydzień, następny, później; kalendarz, wolne okna dziś i jutro, eksport ICS |
| Agenci | `#agenci` | logowanie, limit, Automat, Raport PM, Test połączenia, uruchomienia |
| Projekty | `#projekty` | dodawanie i usuwanie projektów, zgodność ze standardem |
| Projekt | `#p-<id>` | opis, faza (zmiana z panelu), tablica, wskaźniki ze spalaniem etapu, etapy i terminy, księga, marketing |

Karta zadania otwiera szufladę: stan, termin, wymaga, blokada, uruchomienie agenta.

## Klawisze

| Klawisz | Działanie |
|---|---|
| `/` | szukaj projektu |
| `g` potem `p` `w` `t` `d` `a` | przegląd, wskaźniki, tablica, terminy, agenci |
| `r` | w otwartej szufladzie: uruchom agenta |
| Esc | zamknij szufladę |

## Agenci

Panel uruchamia Claude Code i Codex na tym komputerze, na Twoim logowaniu (subskrypcja), bez kluczy API.
Pełny opis: `AGENCI.md`.

- Zadanie: `r` albo przycisk przy zadaniu. Agent dostaje jedno zadanie i zmienia tylko jego wiersz.
- Raport PM i test połączenia: przyciski w widoku Agenci.
- Logowanie: gdy Claude nie jest zalogowany, widok Agenci ma przycisk „Zaloguj”. Otwiera okno Terminala z `claude auth login`
  (`/api/agent/login`); logujesz się w przeglądarce, panel nie widzi danych logowania. Potem „Sprawdź ponownie” (`/api/agent/recheck`).
  Na Macu za pierwszym razem system pyta, czy Python może sterować Terminalem.
- Automat: sam bierze zadania z `kto: claude|codex`, `gdzie:` tego komputera i datą `kiedy:` nie późniejszą niż dziś; domyślnie wyłączony.
- Tryb uprawnień `acceptEdits`; polecenia powłoki dopuszcza `.claude/settings.json` projektu. Trybu z pominięciem uprawnień panel nie używa.
- Rekordy: `../uruchomienia/<id>.json`, surowy zapis `<id>.log`.

## PM

- `python3 ../standard/pm.py` liczy raport z plików; widok Przegląd liczy to samo.
- Agent `pm` (`.claude/agents/pm.md`) i polecenie `/raport` w Claude Code, rola w `../standard/PM.md`
  (Codex czyta ją przez `../AGENTS.md`). Z panelu: „Raport PM” w widoku Przegląd albo Agenci.
- Notatka PM trafia do `../raporty/RRRR-MM-DD.md`; panel pokazuje najnowszą.

### Co dziś robimy

Okno na górze widoku Przegląd. Piszesz, co chcesz dziś zrobić; PM (Claude, bez narzędzi, niczego nie zmienia)
dostaje listę otwartych zadań wszystkich projektów i układa plan: najwyżej 6 zadań dla agentów i 5 dla Ciebie.
Zadania dla agentów są zaznaczone; „Uruchom zaznaczone” uruchamia je jak „Uruchom agenta” (te same reguły i kolejka).
Plan bierze tylko zadania z kart: id spoza listy i zadania, których agent nie może wykonać, są odrzucane.
Plan z dzisiejszego dnia zostaje widoczny do następnego.

## Projekty

- Rejestr `../projekty.json`, osobny na każdym komputerze. Dopóki go nie ma, panel pokazuje trzy projekty przykładowe z `przyklad/`.
- Z panelu: widok Projekty → „Dodaj projekt” (ścieżka folderu; opcjonalnie założenie brakujących plików standardu).
- Nowy projekt z terminala: `python3 ../standard/projekt.py nowy <folder> --nazwa "Nazwa" --rejestruj`
- Istniejący folder z terminala: `python3 ../standard/projekt.py dodaj <folder>`
- Na projektach przykładowych zadań nie da się uruchomić; raport PM i test połączenia działają.

### Projekty ze zbieracza

Panel pokazuje też foldery zakwalifikowane zbieraczem na tym komputerze (`../system/zbieracz.py kwalifikuj`),
bez dopisywania ich do rejestru:

- folder: `LOKALNE_DIR/aliasy.json`, stan: ostatnia decyzja z `STAN_DIR/mac/decyzje.jsonl`
  (`w realizacji`, `w przygotowaniu`, `wstrzymany`, `backlog`; pozostałe stany są pomijane);
- ścieżki z `../system/system.env` albo zmiennych środowiska (`STAN_DIR`, `LOKALNE_DIR`); brak plików zbieracza to nie błąd;
- folder z rejestru i ze zbieracza pokazuje się raz (porównanie po rzeczywistej ścieżce); pole `origin`: `registry`, `collector`, `sample`;
- folder bez plików standardu ma fazę „księga” i braki w księdze; panel niczego w nim nie zakłada;
- projektu ze zbieracza nie usuwa się z panelu (409): zmień decyzję w zbieraczu.

Projekty przykładowe pojawiają się tylko wtedy, gdy rejestr i zbieracz są puste.

### Pola karty

Wiersze pod tytułem `KARTA.md`, obok `- stan:`:

| Wiersz | Wartości | Bez wiersza |
|---|---|---|
| `- faza:` | pomysł, księga, budowa, wdrożenie, marketing, utrzymanie | faza wyliczona |
| `- klient:` | tak, nie | decyzja zbieracza, inaczej tak |
| `- próg:` | lekka, pełna | pełna dla projektu klienta, lekka dla własnego |
| `- stan:` | aktywny, wstrzymany, zakończony, backlog | decyzja zbieracza, inaczej aktywny |

Faza wyliczona (pierwsza pasująca): backlog → pomysł; brak karty albo karta z brakami → księga;
kampania w toku → marketing; wszystkie etapy zrobione → utrzymanie; inaczej budowa.
Błędna wartość pola jest brakiem karty. W `/api/data` pola projektu: `phase`, `phaseSource` (`karta`, `wyliczona`),
`client`, `threshold` (`lekka`, `pelna`), `description` (pierwszy akapit „Cel”, do 300 znaków), `alias`, `book`, `bookOk`, `bookTotal`, `questions`.

### Pytania do właściciela

Sekcja `## Pytania do właściciela` w `KARTA.md`: wiersze `1. pytanie` albo `- pytanie`, pod pytaniem wcięty wiersz `   Odpowiedź: …`.
Panel pokazuje pytania bez odpowiedzi w Przeglądzie, w widoku Wymaga Ciebie i w księdze projektu. Odpowiedź z panelu
(`/api/question/answer` `{id, n, answer}`) zapisuje albo zmienia ten wiersz; pusta odpowiedź go usuwa.

### Historia

- Przy każdym odczycie danych na prawdziwych projektach panel zapisuje stan zadań z dziś do `../historia/RRRR-MM-DD.json`
  (`historia.py`, zapis atomowy, plik z tego dnia nadpisywany). Inny katalog: `PANEL_HISTORY_DIR`.
- Liczone są tylko zadania (bez publikacji): `done`, `rev` (otwarte z `wymaga: odbiór`), `blocked`, `wip`, `todo`, `total`.
- `/api/data` → `history`: wpisy z ostatnich 63 dni, rosnąco. Dla projektów przykładowych: `historia-przyklad.json`
  (8 tygodni, daty względne; w `/podglad` i `--export` zostają względne jak inne daty podglądu).

## Zapis z panelu

Panel zmienia `ZADANIA.md`, `kampanie/*.md` i pola karty (`KARTA.md`) projektów oraz rejestr projektów. Resztę plików zmieniają agenci.

| Żądanie | Zmiana |
|---|---|
| `POST /api/task/update` | pola zadania: tytuł, stan, kto, gdzie, kiedy, pora, czas, wymaga, blokada, kanał |
| `POST /api/task/add` | nowe zadanie w etapie, w kampanii albo w „Do rozplanowania” |
| `POST /api/stage/update` | termin etapu |
| `POST /api/campaign/update` | wynik i stan kampanii |
| `POST /api/agent/run` | uruchamia zadanie; wiersz dostaje `[~]`, `kto:` i `gdzie:` |
| `POST /api/agent/pm` | uruchamia raport PM |
| `POST /api/plan/ask` | `{"text"}`: PM układa plan dnia (uruchomienie `plan`) |
| `POST /api/plan/accept` | `{"id", "ids"}`: uruchamia wybrane zadania z planu; odpowiedź `started`, `failed` |
| `POST /api/agent/check` | test połączenia |
| `POST /api/agent/stop` | zatrzymuje uruchomienie albo zdejmuje je z kolejki |
| `POST /api/agent/automat` | włącza i wyłącza Automat |
| `POST /api/project/add` | dopisuje folder do rejestru; opcjonalnie zakłada brakujące pliki standardu |
| `POST /api/project/remove` | usuwa projekt z rejestru; pliki zostają |
| `POST /api/project/meta` | `faza`, `klient`, `próg` w `KARTA.md` projektu z rejestru albo ze zbieracza |

Gdy plik zmienił się w międzyczasie (agent albo edytor), serwer odmawia (409), a panel wczytuje stan od nowa.
Żądania z obcej strony są odrzucane (403).

## Dostęp

| Skąd | Warunek |
|---|---|
| ten komputer | bez hasła |
| inne urządzenie | `PANEL_HOST=0.0.0.0`, nazwa hosta w `PANEL_ALLOWED_HOSTS`, hasło w `PANEL_TOKEN`; logowanie na `/wejscie` |
| inne urządzenie, bez `PANEL_TOKEN` | odmowa (403) |

Błędne hasło: odpowiedź po 1 s, najwyżej 10 prób na minutę. Kroki dla iPhone'a: `../INSTALACJA.md`.

## Kalendarz

- Odczyt (tylko Mac): `build/PanelKalendarz.app` (źródło `kalendarz.swift`), EventKit, tylko do odczytu.
  Pierwszy odczyt wymaga zgody: przycisk „Połącz kalendarz”.
- Po zmianie `kalendarz.swift` uruchom `./zbuduj-kalendarz.sh`; macOS zapyta wtedy o zgodę ponownie.
- Eksport: `/terminy.ics` (terminy etapów i daty publikacji). Z tego komputera bez klucza; z innego urządzenia
  adres z kluczem `/terminy.ics?k=…`, który panel pokazuje w zakładce Kalendarz.

## Pliki

| Plik | Rola |
|---|---|
| `server.py` | serwer: strona, `/api/data`, zapis, dostęp, `/terminy.ics` |
| `agents.py` | uruchamianie agentów, kolejka, Automat, rekordy |
| `historia.py` | dzienny stan zadań projektów, odczyt 63 dni |
| `historia-przyklad.json` | przykładowa historia (8 tygodni) dla projektów z `przyklad/` |
| `panel.html` | strona panelu |
| `AGENCI.md` | kontrakt uruchamiania agentów: ustawienia, stany, żądania |
| `panel.env.przyklad` | wzór ustawień; własne ustawienia w `panel.env` (poza repozytorium) |
| `agenci-przyklad.json` | przykładowe uruchomienia dla `/podglad` i eksportu |
| `testy/` | testy uruchamiania na atrapie polecenia `claude` |
| `przyklad/` | trzy projekty przykładowe i przykładowa notatka PM (daty względne, np. `+3`) |
| `przyklad-odtworz.py` | przywraca `przyklad/` do stanu początkowego |
| `kalendarz-przyklad.json` | przykładowe wydarzenia |
| `kalendarz.swift`, `kalendarz-Info.plist`, `zbuduj-kalendarz.sh` | pomocnik kalendarza |
| `podglad.html` | wynik `python3 server.py --export podglad.html`, strona bez serwera |
| `../uruchom/` | skrypty stałego uruchamiania (Mac, Windows) i ręcznego startu |
| `../uruchomienia/` | rekordy uruchomień, surowe zapisy, `stan.json` |
| `../historia/` | pliki `RRRR-MM-DD.json` z historią stanów (powstają przy pracy panelu) |

## Testy

W folderze IntegrateSystems, bez sieci i bez zużycia limitu:

    python3 -m unittest discover -s dashboard/testy

## Poza zakresem

Sterowanie sesją w trakcie (dopisywanie poleceń do pracującego agenta), zapis wydarzeń do kalendarza,
edycja dokumentów z panelu, wspólny widok wielu węzłów (każdy komputer pokazuje własne uruchomienia).
