# Karta projektu: sklep-api

- stan: aktywny
- faza: wdrożenie
- klient: tak
- próg: pełna
- maszyna: pc
- repozytorium: github.com/przyklad/sklep-api
- założono: -30

## Cel
API sklepu: koszyk, zamówienia, płatności testowe.

## Zakres
- Koszyk z rabatami.
- Zamówienia i eksport do CSV.
- Płatności w trybie testowym operatora.

## Poza zakresem
- Płatności produkcyjne.
- Panel administracyjny.

## Definicja ukończenia
- Testy przechodzą w CI.
- Staging przyjmuje zamówienie z płatnością testową.

## Zasady pracy agentów
- Poziom swobody: 2 (pracuje sam, pyta o ryzyko).
- Zgody właściciela wymagają: wdrożenie, migracja danych, `git push --force`, usuwanie danych, wydatki.
- Stan pracy agent zapisuje w ZADANIA.md, decyzje w DECYZJE.md.

## Zasoby i ograniczenia
- Budżet miesięczny na agentów: 150 zł.
