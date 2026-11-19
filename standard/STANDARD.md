# Standard projektu

Każdy projekt ma ten sam zestaw plików, te same sekcje i jeden format wiersza zadania.
Dzięki temu panel, Claude Code i Codex czytają każdy projekt tak samo, a Ty wiesz, gdzie czego szukać.

## Pliki

| Plik | Do czego służy | Stałe sekcje |
|---|---|---|
| `KARTA.md` | Umowa z agentami: cel, zakres, zasady | Cel, Zakres, Poza zakresem, Definicja ukończenia, Zasady pracy agentów |
| `ZADANIA.md` | Jedyna lista zadań: etapy z terminami | `## Etap: nazwa` + `termin:`, `## Do rozplanowania` |
| `DECYZJE.md` | Dziennik decyzji | `## RRRR-MM-DD: tytuł`, najnowsze na górze |
| `README.md` | Wejście do projektu | Co to jest, Jak uruchomić, Struktura, Dokumentacja |
| `docs/ARCHITEKTURA.md` | Jak system jest zbudowany | Przegląd, Komponenty, Dane, Integracje |
| `docs/URUCHOMIENIE.md` | Uruchomienie, testy, wdrożenie | Wymagania, Uruchomienie lokalne, Testy, Wdrożenie |
| `CLAUDE.md`, `AGENTS.md` | Te same zasady dla Claude Code i Codex | blok „Standard projektu” |
| `kampanie/<nazwa>.md` | Jedna kampania w jednym pliku (opcjonalnie) | Grupa docelowa, Przekaz, Harmonogram, Wyniki i wnioski |

Sekcja z tekstem `_Do uzupełnienia…_` liczy się jako brak. Nazw sekcji nie zmieniamy.
Karta może mieć sekcję `## Pytania do właściciela` (lista `1. pytanie`, pod pytaniem `   Odpowiedź: …`); panel pokazuje ją jako sprawy do Ciebie.
Termin odpowiedzi: wcięty wiersz `   termin: RRRR-MM-DD` pod pytaniem albo „do RRRR-MM-DD” w treści pytania.

```
## Pytania do właściciela
1. Który kolor logo?
   termin: 2026-11-21
   Odpowiedź: niebieski
```

## Jeden format wiersza

Zadania w `ZADANIA.md` i publikacje w harmonogramie kampanii zapisujemy tak samo:

```
- [ ] Tytuł | kto: claude | gdzie: pc | kiedy: 2026-11-12 | pora: noc | czas: 30 | wymaga: zgoda
```

| Element | Wartości |
|---|---|
| stan | `[ ]` do zrobienia, `[~]` w toku, `[!]` zablokowane, `[x]` zrobione |
| `kto` | claude, codex, ty |
| `gdzie` | pc, mac, chmura |
| `kiedy` | data RRRR-MM-DD |
| `pora` | dzień, noc |
| `czas` | minuty Twojej pracy (np. `30` albo `1h 30`) |
| `wymaga` | zgoda (agent czeka na decyzję), odbiór (praca czeka na przegląd) |
| `blokada` | powód, przy stanie `[!]` |
| `kanał` | kanał publikacji, w kampaniach |
| `po` | fragmenty tytułów zadań z tego samego pliku (po przecinku), które muszą być `[x]` wcześniej |

Wszystkie pola są opcjonalne. Etap bez otwartych zadań jest zamknięty.
`wymaga` może mieć kilka wartości po przecinku (`wymaga: odbiór, zgoda`); każda z nich obowiązuje.
`po: makietę, zatwierdź teksty`: poprzednikiem jest pierwszy wiersz tego samego pliku, którego tytuł zawiera fragment
(bez wielkości liter). Dopóki któryś poprzednik nie jest `[x]` (albo fragment nie pasuje do żadnego wiersza),
zadania nie da się uruchomić („Czeka na: …”).

## Szczegóły zadania

Pod wierszem zadania (w `ZADANIA.md` i w harmonogramie kampanii) mogą stać wiersze wcięte o 2 spacje.
Należą do zadania nad nimi i kończą się na pierwszym wierszu bez wcięcia (także pustym).

```
- [ ] Wyślij zaproszenia LinkedIn do 8 firm z partii 1 | kto: ty | kiedy: 2026-11-19 | czas: 20
  cel: 8 zaproszeń do osób decyzyjnych w firmach z partii 1
  gotowe gdy: w tabeli z punktu 8 planu wpisane „Zaproszenia wysłane: 8”
  materiał: marketing/plan-10-kont.md#5
  - [ ] Kedameble
  - [ ] Bambooko
```

| Klucz | Znaczenie | Kto pisze |
|---|---|---|
| `cel:` | co ma powstać lub się zmienić, jedno zdanie | właściciel, PM |
| `gotowe gdy:` | sprawdzalny warunek ukończenia | właściciel, PM |
| `materiał:` | ścieżka względem folderu projektu, opcjonalnie `#5` (sekcja `## 5.`) albo `#Nagłówek`; może wystąpić kilka razy | właściciel, PM |
| `  - [ ] krok` | krok zadania; `[x]` zrobiony. Kroki nie są osobnymi zadaniami | wszyscy |
| `wynik:` | krótki wynik pracy | agent |
| `decyzja:` | co właściciel ma zatwierdzić przy odbiorze | agent |
| `zostało:` | czego nie zrobiono | agent |
| `poprawka:` | uwagi właściciela przy „Do poprawy”; agent poprawia pracę według nich | właściciel |
| `następne:` | jedna propozycja kolejnego zadania w formacie wiersza bez stanu: `Tytuł \| kto: … \| kiedy: …` | agent |

Kroki zmienia się po kolejności (od 0, liczone tylko wiersze `- [ ]`/`- [x]` pod zadaniem).
`następne:` nie jest zadaniem: właściciel decyduje, czy je założyć. Każdy inny wcięty wiersz to notatka. Tytułu zadania agent nie zmienia; wynik zapisuje w szczegółach, nie w tytule.
Tytuł zaczyna się od czasownika („Wyślij”, „Przygotuj”) i ma najwyżej 120 znaków.

Braki zgłaszane przy `ZADANIA.md` (`projekt.py sprawdz`, księga w panelu), najwyżej 5 przykładów w wierszu:
otwarte zadanie w etapie z terminem bez `gotowe gdy:`; tytuł dłuższy niż 120 znaków;
tytuł zaczynający się od rzeczownika odczasownikowego („Wdrożenie…”, „Przygotowanie…”).

## Kampania

Pod tytułem pliku kampanii są pola: `stan` (plan, w toku, zakończona, wstrzymana), `cel`, `miernik`,
`cel liczbowy`, `wynik`, `kanały`, `start`, `koniec`, `budżet`. Publikacje to wiersze w sekcji Harmonogram.
Sekcja „Wyniki i wnioski” jest wymagana dopiero po zakończeniu kampanii.

## Raport PM

`python3 standard/pm.py` liczy raport z plików wszystkich projektów; panel liczy to samo w zakładce Raport.

| Pojęcie | Reguła |
|---|---|
| wymaga Ciebie | otwarte zadanie z `kto: ty` albo z polem `wymaga`, oraz pytanie bez odpowiedzi; bez projektów o stanie wstrzymany i backlog |
| zgoda na zadaniu właściciela | `wymaga: zgoda` przy `kto: ty` nie jest decyzją, tylko zwykłym zadaniem właściciela |
| dziś / 7 dni / później | `youToday`: data najpóźniej dziś albo etap po terminie; `youWeek`: data w ciągu 7 dni; `youLater`: później albo bez daty |
| po terminie | otwarte zadanie z datą wcześniejszą niż dziś albo w etapie po terminie |
| zablokowane | zadanie w stanie `[!]` |
| stan etapu | pierwsza pasująca: zrobione → po terminie → czeka na Ciebie (wszystkie otwarte zadania wymagają Ciebie) → zagrożony (otwartych zadań więcej niż dni do terminu) → w normie |
| bez następnego kroku | aktywny projekt bez otwartego zadania z datą najpóźniej za 7 dni |
| etap bez terminu | otwarty etap aktywnego projektu bez wiersza `termin:` |
| następny krok projektu | otwarte zadanie z najwcześniejszą datą, a bez dat pierwsze otwarte z polem `kto` |
| najważniejsze decyzje | 3 pierwsze sprawy dla Ciebie: po terminie, potem najbliższa data, zgoda, pytanie, odbiór, z czasem `czas:` w minutach |
| pytanie | otwarte pytanie z karty to decyzja rodzaju „pytanie”, 2 min; pytanie po terminie to ryzyko |
| kolejność | otwarte zadanie z `po:`, którego data jest wcześniejsza niż data niezrobionego poprzednika albo poprzednik nie ma daty |
| czeka na Ciebie | otwarte zadanie z `po:`, którego niezrobiony poprzednik ma `kto: ty` |
| zawieszone | `[~]` bez odbioru i bez pracującego agenta dłużej niż 3 dni (od zmiany stanu, zapis panelu w `uruchomienia/stan.json`) |
| odbiór czeka | otwarte zadanie z `wymaga: odbiór` dłużej niż 2 dni |

Rola agenta, który raportuje, jest opisana w `standard/PM.md`. Notatki PM trafiają do `raporty/RRRR-MM-DD.md`.

## Uruchamianie z panelu

Panel uruchamia agenta dla jednego zadania; pełny opis w `dashboard/AGENCI.md`.

| Chwila | Wiersz zadania |
|---|---|
| start | stan `[~]`, `kto:` narzędzie, `gdzie:` komputer, na którym działa panel |
| koniec, agent skończył | `[x]` |
| koniec, praca do przeglądu | `[~]` i `wymaga: odbiór` (panel dopisuje pole, gdy agent zostawił samo `[~]`) |
| koniec, agent nie może iść dalej albo „gotowe gdy” nie jest spełnione | `[!]` i `blokada: powód` (bez `wymaga: odbiór`) |
| błąd, limit, zatrzymanie, przekroczony czas | panel przywraca `[ ]` |

Agent czyta szczegóły zadania (cel, gotowe gdy, materiały, kroki), odhacza wykonane kroki, a na koniec dopisuje pod
swoim wierszem `wynik:`, gdy trzeba `decyzja:` i `zostało:`; może dopisać jeden wiersz `następne:`. Przy wierszu
`poprawka:` poprawia pracę według niego. Pytania do Ciebie dopisuje do sekcji „Pytania do właściciela” w `KARTA.md`
(z `   termin:`, gdy odpowiedź jest potrzebna do konkretnego dnia). Pracę w repozytorium git zapisuje na nowej gałęzi
`agent/RRRR-MM-DD-krotka-nazwa` jednym lokalnym commitem (bez push) i podaje gałąź i commit w `wynik:`.

Zadanie nie startuje, gdy jest zrobione, ma `kto: ty` albo `zgoda` w polu `wymaga`, jest publikacją w kampanii,
ma niezrobionego poprzednika z `po:`, już pracuje albo należy do projektów przykładowych.
Zadanie bez pola `kto` uruchamia Claude. Automat bierze zadanie bez `gdzie:` na serwerze (węzeł domyślny).

## Polecenia

```
python3 standard/projekt.py nowy <folder> --nazwa "Nazwa" --rejestruj   # zakłada brakujące pliki, niczego nie nadpisuje
python3 standard/projekt.py kampania <folder> "Nazwa kampanii"
python3 standard/projekt.py sprawdz [<folder>]                          # raport braków; kod wyjścia 1, gdy są braki
python3 standard/projekt.py dodaj <folder> | usun <folder> | lista      # projekty widoczne w panelu
python3 standard/pm.py [--json]                                         # raport PM ze wszystkich projektów
```

W istniejącym projekcie `nowy` dopisuje tylko brakujące pliki, a do istniejących `CLAUDE.md` i `AGENTS.md` dokleja blok standardu.
Rejestr projektów panelu to `projekty.json` w folderze IntegrateSystems.
