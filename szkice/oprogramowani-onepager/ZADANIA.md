# Zadania: Oprogramowani – strona WWW

> Jedyna lista zadań projektu. Czyta ją panel i agenci.
> Wiersz: `- [ ] Tytuł | kto: claude | kiedy: RRRR-MM-DD`

## Etap: Nowa strona

- [!] Strona: przygotuj podgląd nowej strony w panelu (wersja robocza) | kto: claude | gdzie: chmura | kiedy: 2026-11-23 | blokada: agent nie ma uprawnień do `npm run build:panel` (dozwolone jest tylko `npm run build`), więc wersja robocza nie została zbudowana i nie ma zrzutów
  cel: zakładka Strona pokazuje nową stronę z gałęzi nowa-koncepcja na telefonie i komputerze, z żółtymi [UZUPEŁNIJ] tam, gdzie brakuje danych firmy
  gotowe gdy: `npm run build:panel` w folderze site buduje wersję roboczą (VITE_SZKIC=1) ze ścieżkami względnymi, więc strona główna, wersje językowe i polityki działają pod dowolnym adresem (np. /podglad/<projekt>/<klucz>/); zrzuty 390 i 1440 px pokazują całą stronę bez błędów; produkcyjne `npm run build` działa jak dotąd
  materiał: site/package.json
  materiał: site/scripts/prerender.mjs
  materiał: site/src/dane.js
  - [x] Dodaj w site/package.json skrypt build:panel (wersja robocza, ścieżki względne); produkcyjnego build nie zmieniaj
  - [ ] Zbuduj, zrób zrzuty strony głównej i jednej podstrony na telefonie i komputerze, obejrzyj je i popraw ścieżki, jeśli coś się nie ładuje
  - [ ] W wynik: wpisz, co widać na zrzutach i ile miejsc ma [UZUPEŁNIJ]; treści i danych firmy nie zmieniaj
  wynik: kod gotowy, ale niesprawdzony w działaniu. Dodany skrypt build:panel w site/package.json (wersja robocza ze ścieżkami względnymi); obsługa dowolnego adresu w site/src/baza.js, site/scripts/prerender.mjs, site/vite.config.js, site/src/main.jsx, site/src/Strona.jsx, site/src/Umow.jsx, site/src/analityka.js. Strona główna, /pl /de /it /en i strony Regulamin/Prywatność dostają adresy względne do swojego położenia; formularz w podglądzie nie wyśle nic poza adres podglądu. Produkcyjne `npm run build` uruchomione: zachowuje się jak dotąd (pliki strony się budują, potem zatrzymuje się celowo na 23 wymaganych, pustych polach w site/src/dane.js). Treści i danych firmy nie zmieniałem.
  zostało: `npm run build:panel` (także `build:szkic` i `build:podglad`) zostało odrzucone przez uprawnienia agenta, więc wersji roboczej nie zbudowałem, zrzutów 390 i 1440 px nie ma i nie policzyłem miejsc [UZUPEŁNIJ] na stronie (wiadomo tylko, że w site/src/dane.js pustych jest 37 pól). Nie sprawdzone: czy pod adresem podglądu wszystko się ładuje.
  następne: Strona: zbuduj podgląd poleceniem build:panel, zrób zrzuty 390 i 1440 px i policz [UZUPEŁNIJ] (po dodaniu agentowi uprawnienia do npm run build:panel) | kto: claude | kiedy: 2026-11-24
- [ ] Oceń nową stronę w zakładce Strona (punkt kontrolny 1: kierunek) | kto: ty | kiedy: 2026-11-24 | czas: 20 | po: przygotuj podgląd nowej strony
  cel: decyzja, czy nowa strona idzie w dobrym kierunku
  gotowe gdy: uwagi wysłane z zakładki Strona („Wskaż” i „Wyślij agentowi”) albo zadanie zamknięte bez uwag
  materiał: site
  materiał: site/package.json
  - [ ] Obejrzyj stronę na telefonie i komputerze
  - [ ] Wskaż, co zmienić, albo zamknij zadanie
- [ ] Podaj dane firmy do strony: prawo i RODO | kto: ty | kiedy: 2026-11-25 | czas: 15
  cel: dane prawne, bez których strona nie może wyjść na produkcję
  materiał: site/src/dane.js
  pyta: Ceny netto plus VAT czy zwolnienie z VAT; Sprzedajecie tylko firmom czy także konsumentom; Adres dokładnie jak w CEIDG; Link do wpisu w CEIDG; Data wejścia regulaminu w życie; Dostawca serwera i kraj; Narzędzie do rozmów online i kraj dostawcy; Brevo trzyma dane w EOG czy poza EOG; Ile miesięcy trzymamy rozmowy bez umowy; Ile dni trzymamy logi serwera; Po ilu dniach dane znikają z kopii zapasowych
- [ ] Podaj warunki współpracy do strony: płatności, ceny, godziny | kto: ty | kiedy: 2026-11-25 | czas: 15
  cel: warunki, które strona obiecuje klientom
  materiał: site/src/dane.js
  pyta: Zaliczka w procentach (0 = bez zaliczki); Termin płatności faktury w dniach; Gwarancja w dniach po odbiorze; Stawka opieki po wdrożeniu w zł za godzinę; Czas reakcji na awarię w dniach roboczych; Godziny prac przy projektach; Godziny odbierania telefonu; Zasada bezpłatnej rozmowy jednym zdaniem; Górna cena integracji ERP w zł; Górna cena końca przepisywania w zł; Górna cena małego automatu w zł; Obniżka ceny etapu za tydzień opóźnienia w procentach; Po ilu tygodniach opóźnienia klient może odstąpić; Subiekt GT czy Subiekt nexo; Platformy sklepów, z którymi łączycie
- [ ] Strona: wpisz dane firmy i przygotuj wersję do publikacji | kto: claude | gdzie: chmura | kiedy: 2026-11-25 | po: Oceń nową stronę, prawo i RODO, warunki współpracy
  cel: dane z odpowiedzi właściciela są w site/src/dane.js i w tekstach strony
  gotowe gdy: produkcyjne `npm run build` przechodzi bez błędu; zrzuty 390 i 1440 px nie mają [UZUPEŁNIJ] w polach wymaganych; każda wpisana wartość pochodzi z odpowiedzi właściciela, nic nie jest wymyślone
  materiał: site/src/dane.js
  - [ ] Wpisz odpowiedzi do site/src/dane.js; pola bez odpowiedzi zostaw puste i wypisz w zostało:
  - [ ] Zbuduj wersję produkcyjną i roboczą, zrób zrzuty, obejrzyj je
- [ ] Strona: sprawdź stronę pięcioma audytami i popraw | kto: claude | gdzie: chmura | kiedy: 2026-11-26 | po: wpisz dane firmy
  cel: strona gotowa do publikacji w ocenie pięciu audytorów: klient, krytyczny klient, prawnik, projektant interfejsu, specjalista od konwersji
  gotowe gdy: w wynik: ocena każdego audytora (1–10) z jednym powodem; poprawione wszystko, co nie wymaga danych właściciela; reszta w zostało:
  - [ ] Oceń stronę z perspektywy każdego audytora na zrzutach 390 i 1440 px
  - [ ] Popraw znalezione błędy, zbuduj, zrób zrzuty jeszcze raz
- [ ] Oceń stronę przed publikacją (punkt kontrolny 2) | kto: ty | kiedy: 2026-11-27 | czas: 20 | po: pięcioma audytami
  cel: decyzja, czy strona może wyjść na oprogramowani.com
  gotowe gdy: uwagi wysłane z zakładki Strona albo zadanie zamknięte, co oznacza zgodę na publikację
  materiał: site
  - [ ] Przeczytaj oceny audytorów w wyniku poprzedniego zadania
  - [ ] Obejrzyj stronę i zdecyduj

## Do rozplanowania
- [~] Przygotuj wizytówkę Oprogramowani dla Krystiana | kto: claude | gdzie: chmura | kiedy: 2026-11-23 | wymaga: odbiór
  cel: wizytówka Krystiana Stryjakiewicza (Oprogramowani) w stylu nowej strony: biel, czerń, jeden czerwony akcent z logo, Inter, dużo powietrza
  gotowe gdy: w folderze wizytowka/ są wizytowka.pdf (2 strony: przód i tył, 85×55 mm plus 3 mm spadu), przod.png i tyl.png (300 dpi) oraz wizytowka.html do podglądu; każdy napis na karcie pochodzi z plików strony, bez wymyślonych danych
  materiał: site/src/dane.js
  materiał: site/src/tresc-pl.js
  materiał: site/src/jezyki/wspolne-pl.js
  materiał: site/public
  - [x] Zbierz z plików strony logo, kolory, krój pisma oraz imię i nazwisko, rolę, telefon, e-mail, adres strony i NIP; czego brakuje, wypisz w zostało:, nie zgaduj
  - [x] Zaprojektuj przód (logo i jedno zdanie, co robicie) i tył (dane kontaktowe); tekst nie bliżej niż 4 mm od krawędzi cięcia
  - [x] Zrób PDF do druku i PNG, obejrzyj PNG i popraw wyrównania, łamania i kontrast
  - [x] W wynik: wpisz, co jest na karcie i gdzie leżą pliki
  wynik: w folderze wizytowka/ (gałąź agent/2026-11-23-przygotuj-wizytowke-oprogramowani-dla-kr, commit ae35241) są wizytowka.pdf (2 strony 91×61 mm: 85×55 mm plus 3 mm spadu, tekst 7 mm od cięcia), przod.png i tyl.png (1075 px, 300 dpi) oraz wizytowka.html. Przód: logo, „Budujemy integracje i małe automaty.”, „Pilnujemy projektu, który robi ktoś inny.” i zdanie o zamówieniach, stanach, fakturach i etykietach (teksty z sekcji oferty na stronie). Tył: Krystian Stryjakiewicz, „Procesy i rozmowa z klientem”, 663 206 373, kontakt@oprogramowani.com, oprogramowani.com, logo, NIP. Wszystkie dane ze strony.
  zostało: telefon i e-mail to ogólne dane firmy ze strony; osobnych dla Krystiana strona nie podaje.
