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

Wszystkie pola są opcjonalne. Etap bez otwartych zadań jest zamknięty.

## Kampania

Pod tytułem pliku kampanii są pola: `stan` (plan, w toku, zakończona, wstrzymana), `cel`, `miernik`,
`cel liczbowy`, `wynik`, `kanały`, `start`, `koniec`, `budżet`. Publikacje to wiersze w sekcji Harmonogram.
Sekcja „Wyniki i wnioski” jest wymagana dopiero po zakończeniu kampanii.

## Raport PM

`python3 standard/pm.py` liczy raport z plików wszystkich projektów; panel liczy to samo w zakładce Raport.

| Pojęcie | Reguła |
|---|---|
| wymaga Ciebie | otwarte zadanie z `kto: ty` albo z polem `wymaga` |
| po terminie | otwarte zadanie z datą wcześniejszą niż dziś albo w etapie po terminie |
| zablokowane | zadanie w stanie `[!]` |
| stan etapu | pierwsza pasująca: zrobione → po terminie → czeka na Ciebie (wszystkie otwarte zadania wymagają Ciebie) → zagrożony (otwartych zadań więcej niż dni do terminu) → w normie |

Rola agenta, który raportuje, jest opisana w `standard/PM.md`. Notatki PM trafiają do `raporty/RRRR-MM-DD.md`.

## Uruchamianie z panelu

Panel uruchamia agenta dla jednego zadania; pełny opis w `dashboard/AGENCI.md`.

| Chwila | Wiersz zadania |
|---|---|
| start | stan `[~]`, `kto:` narzędzie, `gdzie:` komputer, na którym działa panel |
| koniec, agent skończył | `[x]` |
| koniec, praca do przeglądu | `[~]` i `wymaga: odbiór` (panel dopisuje pole, gdy agent zostawił samo `[~]`) |
| koniec, agent nie może iść dalej | `[!]` i `blokada: powód` |
| błąd, limit, zatrzymanie, przekroczony czas | panel przywraca `[ ]` |

Zadanie nie startuje, gdy jest zrobione, ma `kto: ty` albo `wymaga: zgoda`, jest publikacją w kampanii,
już pracuje albo należy do projektów przykładowych. Zadanie bez pola `kto` uruchamia Claude.

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
