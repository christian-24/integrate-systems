# Zadania: {{NAZWA}}

> Jedyna lista zadań projektu. Czyta ją panel i agenci.
> Wiersz: `- [ ] Tytuł | kto: claude | gdzie: pc | kiedy: RRRR-MM-DD | pora: noc | czas: 30 | wymaga: zgoda | po: fragment tytułu`
> Stany: `[ ]` do zrobienia, `[~]` w toku, `[!]` zablokowane (dodaj `blokada: powód`), `[x]` zrobione.
> Pola są opcjonalne. kto: agent, claude, codex, ty. gdzie: pc, mac, chmura. pora: dzień, noc. czas: minuty Twojej pracy. wymaga: zgoda, odbiór.
> Etap to nagłówek `## Etap: nazwa` i wiersz `termin: RRRR-MM-DD` pod nim. Etap bez otwartych zadań jest zamknięty.
> Tytuł zaczyna się od czasownika w trybie rozkazującym („Wyślij”, „Przygotuj”), najwyżej 120 znaków.
> Szczegóły: wiersze wcięte o 2 spacje pod zadaniem: `cel:`, `gotowe gdy:`, `materiał:` (ścieżka, opcjonalnie `#5`),
> kroki `- [ ] krok`, notatka `trwa: N dni` (zadanie trwa dłużej niż jeden dzień). Agent dopisuje `wynik:`, `decyzja:`, `zostało:`.
> Twoje zadanie (`kto: ty`) ma `czas:`, a na najbliższe 7 dni także kroki albo materiał. Zadanie agenta ma `kiedy:`.
> Pola dodatkowe: `sprawdza: kopia` (kontrola serwera) albo `sprawdza: plik <ścieżka>` potwierdza wykonanie;
> `licznik: zaproszenia` (liczba podawana przy zamknięciu, trafia do „Wyniki i wnioski” kampanii), `kampania: nazwa.md`.

## Etap: Start projektu
termin: {{DATA+14}}

- [ ] Uzupełnij Kartę projektu | kto: ty | kiedy: {{DATA+2}} | czas: 20
  cel: Karta opisuje cel, zakres i zasady pracy agentów
  gotowe gdy: `projekt.py sprawdz` nie zgłasza braków w KARTA.md
  materiał: KARTA.md
  - [ ] Cel i Zakres
  - [ ] Poza zakresem i Definicja ukończenia
  - [ ] priorytet projektu (1–5)
- [ ] Uzupełnij README i docs/ | kto: claude | kiedy: {{DATA+3}} | po: kartę projektu
  cel: README i docs/ opisują projekt według Karty
  gotowe gdy: `projekt.py sprawdz` nie zgłasza braków w README.md i docs/
  materiał: KARTA.md

## Do rozplanowania
