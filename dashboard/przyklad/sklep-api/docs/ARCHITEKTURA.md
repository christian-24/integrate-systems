# Architektura: sklep-api

## Przegląd
Jedna usługa HTTP z bazą PostgreSQL. Klienci: aplikacja iOS i strona.

## Komponenty
- API (FastAPI)
- Kolejka zadań eksportu
- Moduł płatności testowych

## Dane
Tabele: cart, cart_item, order, discount_code. Migracje w `migrations/`.

## Integracje
Operator płatności (tryb testowy), poczta transakcyjna.
