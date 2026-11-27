# Strona: runda 3 audytu (27.11), ostatnie poprawki tekstu

Źródło: 11 nowych, niezależnych ocen po rundzie 2 (pełne wyniki: audyt-strony-2026-11-27.md). Średnia „chęć kliknięcia” wynosi 5,2 (w rundzie 2: 5,3, w rundzie 1: 4,9). Tekst nie jest już tym, co hamuje. Każdy klient a–g wymienia te same 4 rzeczy, które zależą od właściciela:
- kwoty „od”;
- dowód: zrzut tablicy, przykładowa wycena, film;
- licencja zamiast kodu i dostępów;
- godziny 15–19.

Są na liście decyzji w raporcie. Tutaj zostają tylko drobne poprawki spójności od kontrolera rzetelności i copywritera.

## Zasady (bez zmian)
- Nic nie wymyślone, dane.js i [UZUPEŁNIJ] bez zmian, każda obietnica raz, „demo” najwyżej 2 razy na głównej.

## Strona główna PL
1. **Brzmi znajomo?, problemy.lead.** Copywriter: „Albo prościej:” nie wiadomo, prościej niż co. Nowe zdanie: „A może u Ciebie wygląda to tak: ktoś codziennie przepisuje zamówienia z Allegro do Subiekta, plan produkcji wisi na kartce, a faktury do KSeF wklepujecie ręcznie?”
2. **Ceny, pozycja Demo, o.** Kontroler: podstrona IT nie ma działającego programu. Nowe zdanie: „Działający program na przykładowych danych, zanim zdecydujesz. Dotyczy programów, integracji i Excela.”
3. **Ceny, pozycja Wdrożenie, o.** Kontroler: główna wymienia tylko BaseLinkera. Nowe zdanie: „Cały spisany zakres. Bez stawki godzinowej. Licencje i opłaty innych firm (np. abonament BaseLinkera albo moduł integracyjny Subiekta) opłacasz u nich jak dotąd.”

## Podstrony
4. **pod.cenaBrak.** Kontroler: na głównej jest „zwykle”, na podstronach go nie ma. Nowe zdanie: „Widełki ceny podajemy w bezpłatnej wycenie, zwykle w ciągu dnia roboczego. Stałą cenę dostajesz na piśmie przed startem.”
5. **Zdanie `demo` w planowaniu, integracjach i Excelu.** Zamień początek „W 1–2 dni po wycenie” na „Gdy widełki ceny Ci pasują, w 1–2 dni”, tak samo jak w karcie 02 na głównej.
   - Excel: „Gdy widełki ceny Ci pasują, w 1–2 dni pokazujemy działające makro albo kalkulator na przykładowym pliku bez prawdziwych danych albo według Twojego opisu.”
   - Reszta każdego zdania bez zmian.

## DE, IT, EN
- Te same zmiany sensu, naturalnie, nie słowo w słowo. Polskie nazwy programów zostają.

## Sprawdzenie
- `npm ci && npm run build:panel` (karta).
- Zrzuty 390 i 1440 px PL i EN obejrzane.
- W dist/pl/index.html „demo” najwyżej 2 razy.
- W wynik: lista zmian.
