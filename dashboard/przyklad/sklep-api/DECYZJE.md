# Decyzje: sklep-api

Najnowsze na górze. Nagłówek wpisu: `## RRRR-MM-DD: krótki tytuł`.

## -3: Eksport CSV zapisujemy strumieniowo
- Kontekst: przy 50 tys. zamówień eksport w pamięci przekraczał limit kontenera.
- Decyzja: zapis strumieniowy, plik powstaje wiersz po wierszu.
- Skutki: brak sortowania po stronie API, sortuje zapytanie do bazy.
- Kto: Ty, na wniosek Claude Code.

## -12: Rabaty liczymy po stronie API
- Kontekst: aplikacja mobilna i strona liczyły rabat inaczej.
- Decyzja: jedyne źródło ceny po rabacie to API.
- Skutki: klienci nie liczą cen lokalnie.
- Kto: Ty.
