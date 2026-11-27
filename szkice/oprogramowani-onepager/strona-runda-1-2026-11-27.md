# Strona: runda 1 audytu (27.11), poprawki

Źródło: audyt 11 niezależnych ocen (8 typów klientów i 3 ekspertów) na stronie po zadaniu „Strona: zacznij od problemu klienta, każda obietnica raz”. Pełne wyniki są w audyt-strony-2026-11-27.md. Tutaj są tylko poprawki, które zgłosiła większość osób albo kontroler rzetelności. Średnia „chęć kliknięcia Bezpłatna wycena” wynosi 4,9/10.

Co powtarzało się najczęściej:
1. „Kim jest Paweł?”: 9 z 11 osób. „Dzwonisz do Pawła albo Krystiana”, a stopka mówi o jednoosobowej działalności Krystiana.
2. „Ile to kosztuje.” bez żadnej kwoty: 9 z 11. Nagłówek obiecuje liczbę, której nie ma. Kwot nie dodajemy, to decyzja właściciela. Nagłówek ma tylko nie obiecywać więcej, niż sekcja daje.
3. Hero i „Brzmi znajomo?” mówią tylko o ERP i integratorze. Sprzedawca z Allegro, księgowa, kierownik produkcji i właściciel stolarni nie widzą siebie aż do kafelków: 6 z 8 klientów oraz SEO i copywriter.
4. Kontroler rzetelności: „1–2 dni” bez warunku u góry strony, a warunek dopiero w cenniku. Podstrona IT nazywa „demem” plan na piśmie. Główna mówi „widełki w ciągu dnia”, a podstrony „cenę w ciągu dnia”. „Bez ryzyka” stoi obok zaliczki. „Bez zobowiązań” pada 2 razy. Stopka mówi o „symulacjach”, których nie ma.

## Zasady (bez zmian)
- Nic nie wymyślone: bez nowych kwot, klientów, opinii, liczb, terminów i gwarancji.
- `site/src/dane.js` i miejsca [UZUPEŁNIJ] zostają bez zmian. Nowe zdania mogą korzystać tylko z istniejących stałych (`PAWEL`, `PAWEL_FORMA`, `GWAR_ETAP`, `DEMO_WARUNEK` itd.).
- Każda obietnica (pokaz programu, bezpłatna wycena, stała cena, odbiór etapami, opieka) pada na stronie głównej najwyżej raz jako zdanie. Przycisk „Bezpłatna wycena” to nie zdanie. Słowo „demo” na stronie głównej PL najwyżej 2 razy.
- Bez słów „transformacja”, „AI”, „rozwiązania szyte na miarę” i bez słownictwa z gier.

## Strona główna PL (site/src/jezyki/tresc-pl.js, w razie potrzeby Strona.jsx i strona.css)

### Meta
- title: „Oprogramowani — integracje i prosty program zamiast wielkiego ERP-a”
- opis: „Integracje Allegro, BaseLinker, Subiekt GT, Optima i KSeF, makra w Excelu, planowanie produkcji i IT dla małych firm. Stała cena na piśmie. Bezpłatna wycena.”
- og: bez zmian.

### Hero
- h1a i h1b bez zmian („Po co Ci wielki ERP?” / „Napiszemy prosty program pod Twoją firmę.”).
- lead: „Albo połączymy programy, które już masz: Allegro, BaseLinkera, Subiekta, Optimę, KSeF i Excela.”
- Pod przyciskiem dodaj nowy klucz `hero.pod` (drobny tekst, jedna linia): „Opisz, co ma działać. W ciągu dnia roboczego oddzwonimy z widełkami ceny.”
  - To jedyne miejsce na stronie głównej ze zdaniem o widełkach w ciągu dnia. Z kontaktu je usuń (niżej).

### Brzmi znajomo? (problemy)
- Karty 01, 03 i 04: nagłówki i opisy bez zmian.
- Karta 02, odp.: „Po wycenie i potwierdzeniu widełek ceny w 1–2 dni pokazujemy działający program na przykładowych danych.” (warunek jest tu, przy terminie).
- Karta 04, odp.: `${GWAR_ETAP} Potem dzwonisz do nas, nie na infolinię.`
  - Imiona są w kontakcie, gdzie są przedstawione.

### Kafelki linii oferty
- Kafelek planowania, p: „Tablica zleceń zamiast kartek i Excela: kolejka, etapy i kto co robi, na hali i w biurze.”
- Kafelek integracji:
  - n: „Integracje: Allegro · BaseLinker · Subiekt · Optima · KSeF”
  - p: „Zamówienia i faktury przechodzą między programami bez przepisywania.” (bez zmian)
  - Jeśli n jest za długie na telefonie, zostaw „Integracje: Allegro · BaseLinker · Subiekt · Optima · KSeF” w dwóch liniach; nie skracaj nazw.
- Kafelki Excel i IT bez zmian.

### Ceny
- eyebrow: „Ceny”, h2a „Ile to kosztuje.”, h2b „Cenę znasz na piśmie, zanim zaczniemy.” bez zmian.
- lead: „Kwota zależy od programów, które masz, więc podajemy ją po rozmowie: najpierw widełki, potem stała cena na piśmie. Za opiekę płacisz tylko wtedy, gdy jej chcesz.”
- wycena.o: „Zadzwoń albo napisz. Do niczego nie zobowiązuje.”
- Demo.o: „Działający program na przykładowych danych, zanim zdecydujesz.” (bez DEMO_WARUNEK, bo warunek jest w karcie 02)
- Wdrożenie i Opieka bez zmian.
- warunki[2]: zostaje tylko `ZASADA` (bez zdania „Wycena jest bezpłatna i do niczego nie zobowiązuje.”, bo jest w wycena.o). Jeśli `ZASADA` jest pusta, punkt nie wyświetla się wcale (bez pustego wiersza).
- VAT, „Co płacisz poza nami” i pozostałe warunki bez zmian.

### Bez ryzyka (pewnosc)
- eyebrow: „Twoje programy zostają” zamiast „Bez ryzyka”.
- h2a, lead bez zmian.
- Pierwsza karta, p: „Optima, Subiekt, enova, BaseLinker, Allegro, KSeF albo Excel zostają. Masz już ERP? Też go nie ruszamy, tylko dokładamy to, co ludzie dziś robią obok w Excelu. Jeśli nowy program naprawdę ma sens, powiemy to wprost. Nie jesteśmy partnerem żadnego producenta, więc nie musimy Ci niczego sprzedawać.”
- Druga karta bez zmian.

### Kontakt
- h2a, h2b bez zmian.
- p: „Napisz, w jakich programach pracujesz i co dziś robicie ręcznie.”
- kto: „Rozmawia z Tobą Krystian, nie handlowiec. Programy piszą Krystian i ${PAWEL}${PAWEL_FORMA}.”
  - Użyj istniejących stałych. Gdy pola w dane.js są puste, wersja robocza pokaże żółte [UZUPEŁNIJ], a produkcja tekst zastępczy jak w innych miejscach.
  - Upewnij się, że `PAWEL_FORMA` jest tu poprawne gramatycznie, a nawias się zamyka.
- Godziny rozmów bez zmian (to dane właściciela).

### Stopka
- nota: „Przykłady na tej stronie są ilustracją, a nie danymi klientów.” (bez „symulacje”).

## Podstrony
- pod.demoPre: „Co zobaczysz przed decyzją” zamiast „Jak wygląda demo” (pasuje też do planu IT).
- pod.cenaBrak: „Widełki ceny podajemy w bezpłatnej wycenie, w ciągu dnia roboczego. Stałą cenę dostajesz na piśmie przed startem.”
- Planowanie produkcji:
  - lead: „Prosta tablica zleceń dla małej firmy, np. stolarni albo zakładu meblowego: kolejka, etapy i kto co robi. Ten sam widok na hali i w biurze.”
  - Dopisz na końcu listy `robimy`: „Handlowiec sprawdza etap zlecenia na telefonie, bez chodzenia na halę”.
- Integracje:
  - meta.title: „Integracja Allegro, BaseLinker, Subiekt GT, Optima i KSeF — Oprogramowani”
  - meta.opis: „Integracja Allegro i BaseLinkera z Subiektem GT, Optimą i KSeF: zamówienia i faktury bez przepisywania. Bezpłatna wycena.”
  - h1: „Integracja Allegro i BaseLinkera z Subiektem GT, Optimą i KSeF”
  - nazwa (kafelek „Pozostałe usługi”) taka jak n kafelka na głównej.
  - Trzeci punkt `robimy`: „Faktury z KSeF do Optimy albo Subiekta i z powrotem, bez przepisywania”.
- Excel i IT: bez zmian treści poza wspólnymi kluczami wyżej.

## DE, IT, EN
- Ta sama struktura kluczy i ten sam sens, w naturalnym języku kraju, nie słowo w słowo.
- Nowy klucz `hero.pod` we wszystkich czterech plikach.
- Polskie nazwy programów (Subiekt GT, Optima, BaseLinker, KSeF, Allegro) zostają.
- „Twoje programy zostają”:
  - DE: „Ihre Programme bleiben”
  - IT: „I tuoi programmi restano”
  - EN: „Your software stays”
  - Albo równie naturalnie.
- Zdanie o Pawle tylko ze stałymi z pliku danego języka (jeśli plik nie ma odpowiednika `PAWEL_FORMA`, dodaj go według wzoru PL, z tymi samymi polami dane.js).

## Sprawdzenie
- `npm ci && npm run build:panel` w site/ (karta).
- Zrzuty 390 i 1440 px PL i EN, strona główna i podstrona integracji, obejrzane.
- W zbudowanym dist/pl/index.html „demo” najwyżej 2 razy, a „zobowiązuje” lub „zobowiązań” najwyżej raz.
- W wynik: lista zmian sekcja po sekcji.
