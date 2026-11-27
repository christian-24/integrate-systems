# Strona: runda 2 audytu (27.11), poprawki

Źródło: 11 nowych, niezależnych ocen strony po rundzie 1 (pełne wyniki: audyt-strony-2026-11-27.md). Średnia „chęć kliknięcia” wzrosła z 4,9 do 5,3. Tekst przestał przeszkadzać. Hamują głównie trzy rzeczy, które zależą od właściciela: brak kwot „od”, brak dowodu (zrzut, film, realizacja) i godziny rozmów 15–19. Te sprawy są na liście dla właściciela, tutaj ich nie ruszamy.

Co powtarzało się w tej rundzie:
1. Sprzedawca z Allegro, właściciel stolarni, kierownik produkcji, księgowa i copywriter mówią to samo: hero i 4 karty to problemy z ERP i integratorem, a ich codzienny ból (przepisywanie, kartki na hali, faktury z KSeF) pojawia się dopiero na podstronach.
2. „Ile to kosztuje.” nadal obiecuje kwotę, której nie ma. Mówi tak 8 z 11 osób, w tym copywriter: „bez kwot nagłówek trzeba zmienić na »Jak ustalamy cenę«”.
3. Kontroler rzetelności:
   - „W ciągu dnia roboczego oddzwonimy” w hero, a „odpisujemy zwykle w ciągu dnia roboczego” w kontakcie;
   - „potwierdzenie widełek” stoi obok „do niczego nie zobowiązuje”;
   - „na piśmie” pada 5 razy, „Twoje programy zostają” 4 razy z rzędu;
   - „połowa firmy” brzmi jak statystyka;
   - „nie musimy Ci niczego sprzedawać” jest nielogiczne, bo firma sprzedaje;
   - koszty u innych firm są tylko na podstronie integracji.
4. Nagłówek kafelka integracji łamie się na komputerze w 4 linie, a linie zaczynają się od „·” (widać na zrzucie 1440 px).

## Zasady (bez zmian)
- Nic nie wymyślone: bez nowych kwot, klientów, opinii, liczb, terminów i gwarancji.
- dane.js i [UZUPEŁNIJ] bez zmian.
- Każda obietnica pada na stronie głównej najwyżej raz jako zdanie. „demo” najwyżej 2 razy.
- Cztery karty „Brzmi znajomo?” to chwyty właściciela: ich nagłówki zostają.

## Strona główna PL

### Hero
- h1a, h1b i lead bez zmian.
- hero.pod: „Opisz, co ma działać. Krystian oddzwoni z widełkami ceny, zwykle w ciągu dnia roboczego.”

### Brzmi znajomo?
- Dodaj lead pod h2 (nowy klucz `problemy.lead`, jedno zdanie, zwykły tekst): „Albo prościej: ktoś codziennie przepisuje zamówienia z Allegro do Subiekta, plan produkcji wisi na kartce, a faktury do KSeF wklepujecie ręcznie.”
- Karta 01:
  - p: „Licencje, wdrożenie, konsultanci, a część firmy i tak pracuje w Excelu.”
  - odp: „Robimy tylko to, czego potrzebujesz, za stałą cenę.”
- Karta 02, odp: „Gdy widełki ceny Ci pasują, w 1–2 dni pokazujemy działający program na przykładowych danych. Termin całego wdrożenia podajemy w wycenie.”
- Karty 03 i 04 bez zmian.

### Kafelki
- Planowanie: bez zmian.
- Integracje, n: „Integracje Allegro, BaseLinker, Subiekt, Optima, KSeF” (przecinki zamiast „·”, bez dwukropka).
  - Sprawdź na 1440 px, że żadna linia nie zaczyna się od znaku interpunkcyjnego.
  - Ta sama nazwa w `podstrony.integracje.nazwa`.
- Excel, n: „Makra i automatyzacja Excela”. Ta sama nazwa w `podstrony.excel.nazwa`, a p bez zmian.
- IT bez zmian.

### Ceny
- h2a: „Jak ustalamy cenę.” (zamiast „Ile to kosztuje.”; wraca, gdy właściciel poda kwoty „od”).
- h2b bez zmian („Cenę znasz na piśmie, zanim zaczniemy.”).
- lead: „Kwota zależy od programów, które masz: najpierw podajemy widełki, potem stałą cenę. Za opiekę płacisz tylko wtedy, gdy jej chcesz.”
- Wdrożenie, o: „Cały spisany zakres. Bez stawki godzinowej. Licencje innych firm (np. abonament BaseLinkera) opłacasz u nich jak dotąd.”
- Reszta bez zmian.

### Dokładamy, nie wymieniamy (pewnosc)
- eyebrow: „Bez przesiadki”.
- lead: „Nie przenosisz danych do nowego systemu i nie uczysz ludzi wszystkiego od nowa.”
  - Zdanie „zasady… spisujemy w umowie” zostaje tylko w karcie „Licencja na piśmie”.
- Karta 1, p: „Optima, Subiekt, enova, BaseLinker, Allegro, KSeF albo Excel zostają. Masz już ERP? Też go nie ruszamy, tylko dokładamy to, co ludzie dziś robią obok w Excelu. Jeśli nowy program naprawdę ma sens, powiemy to wprost. Nie jesteśmy partnerem żadnego producenta, więc nie mamy interesu, żeby namawiać Cię na nowy system.”
- Karta 2 bez zmian.

### Kontakt
- kto: zostaje tylko zdanie o tym, kto pisze programy: „Programy piszą Krystian i ${PAWEL}${PAWEL_FORMA}.”
  - „Rozmawia z Tobą Krystian, nie handlowiec.” przenieś do hero.pod (już tam jest sens „Krystian oddzwoni”). W kontakcie tego zdania nie powtarzaj.
- Reszta bez zmian.

## Podstrony
- Planowanie produkcji, meta.title: „Program do planowania produkcji dla małych firm i stolarni — Oprogramowani”.
- Integracje: nazwa jak kafelek (wyżej). H1, title i opis bez zmian.
- Excel: nazwa jak kafelek (wyżej). H1 bez zmian.
- `pod.problemyH` („Brzmi znajomo?”) zostaje.

## DE, IT, EN
- Te same zmiany sensu i nowy klucz `problemy.lead` we wszystkich językach, naturalnie, nie słowo w słowo.
- Polskie nazwy programów zostają.
- „Jak ustalamy cenę.”:
  - DE: „So entsteht der Preis.”
  - IT: „Come fissiamo il prezzo.”
  - EN: „How we set the price.”
  - Albo równie naturalnie.

## Sprawdzenie
- `npm ci && npm run build:panel` (karta).
- Zrzuty 390 i 1440 px PL i EN obejrzane, w tym kafelek integracji na 1440 px.
- W dist/pl/index.html: „demo” najwyżej 2 razy, „na piśmie” najwyżej 3 razy.
- W wynik: lista zmian sekcja po sekcji.
