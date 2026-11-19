# Karta projektu: Testy zlecone (TestNow)

- stan: aktywny
- faza: budowa
- klient: tak
- próg: lekka
- priorytet: 4
- maszyna: mac
- repozytorium:
- założono: 2026-10-27

Szkic z kopii na Macu. Audyt PC (2026-11-14) nie znalazł na PC żadnych materiałów o TestNow; projekt prowadzony tylko na Macu.

Karta jest umową między właścicielem a agentami pracującymi w tym projekcie. Agent czyta ją na początku każdej sesji.

## Cel
Płatne testy stron i aplikacji na zlecenie platformy testerskiej: zgłaszanie błędów funkcjonalnych, treści i wyglądu według wymagań danego testu. Projekt jest niepilny, prowadzony obok projektów głównych; kontynuowany po pozytywnym pierwszym teście.

## Zakres
- Notatki wymagań dla każdego testu (jeden plik na test, np. `test-<numer>-requirements.md`).
- Przejście funkcji z listy testu i zgłoszenia błędów w języku wymaganym przez test.
- Zapis wyniku testu: liczba zgłoszeń, przyjęte, wypłata.

## Poza zakresem
- Składanie zamówień, kontakt z obsługą klienta, wystawianie opinii na testowanych stronach (zakazane regułami testów).
- Automatyzacja zgłoszeń bez przeglądu właściciela.

## Definicja ukończenia
Test jest zakończony, gdy zgłoszenia są wysłane przez właściciela, a wynik i wypłata zapisane w ZADANIA.md.
_Do uzupełnienia: czy projekt ma cel miesięczny (liczba testów albo kwota)?_

## Zasady pracy agentów
- Poziom swobody: 1 (agent przygotowuje notatki i listy kontrolne, nie działa na testowanych stronach).
- Wymagają zgody właściciela: każde działanie na koncie platformy testerskiej, rejestracja kont testowych, wysyłka zgłoszeń.
- Agent nie wpisuje haseł ani danych kont testowych.
- Stan pracy agent zapisuje w ZADANIA.md, decyzje w DECYZJE.md.

## Zasoby i ograniczenia
- Testy idą z Maca (na PC brak materiałów).
- Najwyżej 3 godziny tygodniowo (właściciel, 2026-11-14).
- Zgłoszenia wymagają zrzutów ekranu i nagrań ekranu z własnej pracy testera.
- _Do uzupełnienia: nazwa platformy._

## Pytania do właściciela
1. Czy to stałe zajęcie (wiele testów), czy jednorazowy test z 27.10?
   Odpowiedź: Test był pozytywny, należy jednak umzoliwic nagrywanie ekranu na macu wiec docelowo trzeba by było jakoś to ogarnąć
2. Czy test #152976 jest zakończony i jaki był wynik?
   Odpowiedź: Pozytywny ale brak screenów i nagrań ekranu a powinny być z naturalnym ruchem człowieka
3. Ile czasu w tygodniu chcesz na to przeznaczać?
   Odpowiedź: max 3h
