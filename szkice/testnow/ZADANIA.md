# Zadania: Testy zlecone (TestNow)

> Jedyna lista zadań projektu. Czyta ją panel i agenci.
> Wiersz: `- [ ] Tytuł | kto: claude | gdzie: pc | kiedy: RRRR-MM-DD | pora: noc | czas: 30 | wymaga: zgoda`
> Stany: `[ ]` do zrobienia, `[~]` w toku, `[!]` zablokowane (dodaj `blokada: powód`), `[x]` zrobione.

## Etap: Test #152976

- [x] Spisać wymagania testu | kto: claude | gdzie: mac | kiedy: 2026-10-27
- [x] Test zakończony, wynik pozytywny; zabrakło zrzutów i nagrań ekranu (2026-11-14)

## Do rozplanowania

- [ ] Przygotuj szablon notatki wymagań testu | kto: claude
  cel: każdy kolejny test zaczyna się od tej samej notatki wymagań
  gotowe gdy: w folderze karty plik szablonu z sekcjami: zakres testu, funkcje do przejścia, język zgłoszeń, zakazy, termin, wynik i wypłata
  materiał: KARTA.md#Zakres
  Nazwa notatki dla testu: test-<numer>-requirements.md.
- [x] Limit: najwyżej 3 h tygodniowo (2026-11-14)
- [ ] Sprawdź nagrywanie ekranu na Macu przed kolejnym testem | kto: ty | gdzie: mac | kiedy: 2026-11-22 | czas: 15
  cel: zgłoszenia mają zrzuty i nagrania ekranu z naturalnym ruchem kursora
  gotowe gdy: próbne nagranie 1 minuty z widocznym kursorem i kliknięciami zapisane i odtworzone
  materiał: KARTA.md#Zasoby i ograniczenia
  - [ ] nagranie przez Cmd+Shift+5 albo QuickTime
  - [ ] pokazywanie kliknięć i kursora w nagraniu
  - [ ] stałe miejsce zapisu nagrań i zrzutów
- [ ] Przygotuj listę kontrolną przebiegu testu i zgłoszenia błędu | kto: claude
  cel: przy każdym błędzie zgłoszenie ma komplet dowodów i spełnia reguły testu
  gotowe gdy: w folderze karty lista kontrolna z krokami poniżej, gotowa do skopiowania do notatki testu
  materiał: KARTA.md#Poza zakresem
  - [ ] zrzut ekranu przy każdym błędzie
  - [ ] nagranie ekranu z naturalnym ruchem człowieka
  - [ ] zgłoszenie w języku wymaganym przez test
  - [ ] wynik testu i wypłata zapisane w ZADANIA.md
- [ ] Uzupełnić pliki projektu według standardu | kto: claude
  cel: Uzupełnić według standard/STANDARD.md: Zadania (1 brak), README (brak pliku), Architektura (brak pliku), Uruchomienie (brak pliku), Instrukcje agentów (brak pliku). Niczego nie nadpisywać; na końcu python3 standard/projekt.py sprawdz bez braków w tym projekcie.
