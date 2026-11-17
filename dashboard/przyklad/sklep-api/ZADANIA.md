# Zadania: sklep-api

> Jedyna lista zadań projektu. Czyta ją panel i agenci.
> Wiersz: `- [ ] Tytuł | kto: claude | gdzie: pc | kiedy: RRRR-MM-DD | pora: noc | czas: 30 | wymaga: zgoda`
> Stany: `[ ]` do zrobienia, `[~]` w toku, `[!]` zablokowane (dodaj `blokada: powód`), `[x]` zrobione.
> Projekt przykładowy: daty zapisane względnie (`+3` to za trzy dni), żeby przykład był zawsze aktualny.

## Etap: Rabaty w koszyku
termin: -1

- [x] Model kodu rabatowego | kto: claude | gdzie: pc
- [x] Naliczanie rabatu w koszyku | kto: claude | gdzie: pc
- [x] Testy rabatów | kto: codex | gdzie: chmura

## Etap: Eksport zamówień do CSV
termin: +3

- [x] Format pliku i lista kolumn | kto: ty | czas: 15
- [~] Eksport CSV: zapis strumieniowy | kto: claude | gdzie: pc | kiedy: +0 | pora: noc
- [ ] Eksport CSV: testy i PR | kto: claude | gdzie: pc | kiedy: +2 | pora: dzień

## Etap: Płatności testowe na stagingu
termin: +11

- [x] Konto testowe u operatora płatności | kto: ty | czas: 20
- [ ] Migracja discount_code | kto: claude | gdzie: pc | kiedy: +1 | pora: dzień | wymaga: zgoda
- [!] Webhook potwierdzenia płatności | kto: codex | gdzie: chmura | blokada: brak klucza testowego operatora
- [ ] Płatności testowe: integracja | kto: claude | gdzie: pc | kiedy: +7 | pora: noc

## Do rozplanowania
- [ ] Limit zapytań na klucz API | kto: codex
- [ ] Opis punktów końcowych w OpenAPI
