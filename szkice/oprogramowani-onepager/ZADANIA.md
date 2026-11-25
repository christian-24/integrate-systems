# Zadania: Oprogramowani – strona WWW

> Jedyna lista zadań projektu. Czyta ją panel i agenci.
> Wiersz: `- [ ] Tytuł | kto: claude | kiedy: RRRR-MM-DD`

## Etap: Nowa strona

- [x] Strona: przygotuj podgląd nowej strony w panelu (wersja robocza) | kto: claude | gdzie: chmura | kiedy: 2026-11-23
  cel: zakładka Strona pokazuje nową stronę z gałęzi nowa-koncepcja na telefonie i komputerze, z żółtymi [UZUPEŁNIJ] tam, gdzie brakuje danych firmy
  gotowe gdy: `npm run build:panel` w folderze site buduje wersję roboczą (VITE_SZKIC=1) ze ścieżkami względnymi, więc strona główna, wersje językowe i polityki działają pod dowolnym adresem (np. /podglad/<projekt>/<klucz>/); zrzuty 390 i 1440 px pokazują całą stronę bez błędów; produkcyjne `npm run build` działa jak dotąd
  materiał: site/package.json
  materiał: site/scripts/prerender.mjs
  materiał: site/src/dane.js
  - [x] Dodaj w site/package.json skrypt build:panel (wersja robocza, ścieżki względne); produkcyjnego build nie zmieniaj
  - [x] Zbuduj, zrób zrzuty strony głównej i jednej podstrony na telefonie i komputerze, obejrzyj je i popraw ścieżki, jeśli coś się nie ładuje
  - [x] W wynik: wpisz, co widać na zrzutach i ile miejsc ma [UZUPEŁNIJ]; treści i danych firmy nie zmieniaj
  wynik: `npm run build:panel` w folderze site buduje wersję roboczą ze ścieżkami względnymi (site/package.json, site/src/baza.js, site/scripts/prerender.mjs); kodu nie trzeba było poprawiać. Zrzuty 390 i 1440 px strony głównej i Regulaminu, a dodatkowo całej strony głównej, wersji /de i Prywatności pod adresem zagnieżdżonym (tak jak w podglądzie panelu): style, kroje pisma, skrypty i plik języka się ładują, bez błędów na stronie. Widać: żółty pasek „Wersja robocza” na górze, menu z przełącznikiem PL·DE·IT·EN, nagłówek z dwoma przyciskami, symulację zamówień, kalkulator, dwie usługi, cztery kroki, rozmowę w telefonie, sekcję dowodów, cennik, ciemną sekcję o własności, dwie osoby z inicjałami, pytania, kontakt i stopkę; na telefonie jedna kolumna, nic nie wychodzi poza ekran. Regulamin i Prywatność to strony tekstu z przyciskami „Drukuj / zapisz PDF” i „Wróć na stronę”. Żółtych [UZUPEŁNIJ]: strona główna 66 miejsc (najczęściej VAT, 14 razy; do tego zaliczka, górne ceny, stawka, gwarancja, adres i CEIDG, dane Pawła, zdjęcia, LinkedIn, godziny), Regulamin 3, Prywatność 9; w site/src/dane.js pustych jest 37 pól. Treści i danych firmy nie zmieniałem.
  zostało: przeglądarka do zrzutów ma język angielski, więc strona główna jest na nich w wersji EN (tak działa wykrywanie języka); polską wersję widać na zrzutach Regulaminu i Prywatności. Nie klikałem przełącznika języka ani formularza. Część z 66 miejsc siedzi w zwiniętych odpowiedziach na pytania, więc na zrzucie widać ich mniej. Produkcyjnego `npm run build` nie uruchamiałem ponownie: kod nie zmienił się od poprzedniego sprawdzenia.
  poprawka: Zacznij od gałęzi agent/2026-11-23-strona-przygotuj-podglad-nowej-strony-w (commit 68af8b7): kod podglądu jest gotowy. Zbuduj go poleceniem z karty, zrób zrzuty 390 i 1440 px, obejrzyj je i dokończ kroki 2–3.
  zmiany: podgląd zbudowany poleceniem z karty: zrobione; zrzuty 390 i 1440 px zrobione i obejrzane: zrobione; kroki 2–3 dokończone, [UZUPEŁNIJ] policzone: zrobione
- [x] Oceń nową stronę w zakładce Strona (punkt kontrolny 1: kierunek) | kto: ty | kiedy: 2026-11-24 | czas: 20 | po: przygotuj podgląd nowej strony
  cel: decyzja, czy nowa strona idzie w dobrym kierunku
  gotowe gdy: uwagi wysłane z zakładki Strona („Wskaż” i „Wyślij agentowi”) albo zadanie zamknięte bez uwag
  materiał: site
  materiał: site/package.json
  - [ ] Obejrzyj stronę na telefonie i komputerze
  - [ ] Wskaż, co zmienić, albo zamknij zadanie
  wynik: właściciel ocenił stronę 25.11; uwagi w zadaniu „Strona: poprawki po punkcie kontrolnym 1”
- [~] Strona: poprawki po punkcie kontrolnym 1 (sekcje, wycena, animacja, telefon) | kto: agent | gdzie: chmura | kiedy: 2026-11-25
  cel: strona prostsza i nastawiona na telefon i bezpłatną wycenę, według uwag właściciela z 25.11
  gotowe gdy: wersja robocza buduje się poleceniem z karty (npm run build:panel), zmiany są we wszystkich językach (PL, DE, IT, EN), zrzuty 390 i 1440 px obejrzane, w wynik: lista zmian sekcja po sekcji; dane firmy i miejsca [UZUPEŁNIJ] bez zmian, bez wymyślonych danych
  materiał: site/src/jezyki/tresc-pl.js
  materiał: site/src/jezyki/wspolne-pl.js
  materiał: site/src/Strona.jsx
  materiał: site/src/strona.css
  - [ ] Połącz w jedną sekcję: cennik („co realizujemy i ile kosztuje”), „Dwie rzeczy. Robimy je porządnie” i „Cenę znasz, zanim zaczniemy”; ceny zostają jako widełki „od … zł”
  - [ ] Usuń motyw „cena znana przed startem” i „ocena przed wyceną” w całej stronie; zamiast tego prosta „Bezpłatna wycena” (główny przycisk zamiast „Umów darmową godzinę”; okno zgłoszenia zostaje jako prośba o wycenę)
  - [ ] Wstęp zostaje, ale szarpaną animację zastąp spokojnym ruchem w tle za tekstem (płynnie, bez skoków, z prefers-reduced-motion)
  - [ ] Usuń sekcję „Bez wymyślonych opinii” i sekcję „Zanim zadzwonisz” (pytania); „Cztery kroki” i „Zamiast raportów” zostają
  - [ ] Strona zachęca do telefonu: numer i „Zadzwoń” w nagłówku i przy wycenie, na telefonie stały przycisk „Zadzwoń” na dole ekranu
  - [ ] Pod Google Ads: dane firmy, kontakt i polityka prywatności łatwo dostępne z każdej podstrony; jeśli strona ma tagi analityki lub reklam, baner zgody z Consent Mode v2 (domyślnie odmowa); nowych tagów bez identyfikatorów od właściciela nie dodawaj
  - [ ] Zbuduj, zrób zrzuty, obejrzyj, popraw; w wynik: co zmieniono w każdej sekcji

- [ ] Podaj dane firmy do strony: prawo i RODO | kto: ty | kiedy: 2026-11-25 | czas: 15
  cel: dane prawne, bez których strona nie może wyjść na produkcję
  materiał: site/src/dane.js
  pyta: Ceny netto plus VAT czy zwolnienie z VAT; Sprzedajecie tylko firmom czy także konsumentom; Adres dokładnie jak w CEIDG; Link do wpisu w CEIDG; Data wejścia regulaminu w życie; Dostawca serwera i kraj; Narzędzie do rozmów online i kraj dostawcy; Brevo trzyma dane w EOG czy poza EOG; Ile miesięcy trzymamy rozmowy bez umowy; Ile dni trzymamy logi serwera; Po ilu dniach dane znikają z kopii zapasowych
- [ ] Podaj warunki współpracy do strony: płatności, ceny, godziny | kto: ty | kiedy: 2026-11-25 | czas: 15
  cel: warunki, które strona obiecuje klientom
  materiał: site/src/dane.js
  pyta: Zaliczka w procentach (0 = bez zaliczki); Termin płatności faktury w dniach; Gwarancja w dniach po odbiorze; Stawka opieki po wdrożeniu w zł za godzinę; Czas reakcji na awarię w dniach roboczych; Godziny prac przy projektach; Godziny odbierania telefonu; Zasada bezpłatnej rozmowy jednym zdaniem; Górna cena integracji ERP w zł; Górna cena końca przepisywania w zł; Górna cena małego automatu w zł; Obniżka ceny etapu za tydzień opóźnienia w procentach; Po ilu tygodniach opóźnienia klient może odstąpić; Subiekt GT czy Subiekt nexo; Platformy sklepów, z którymi łączycie
- [ ] Strona: wpisz dane firmy i przygotuj wersję do publikacji | kto: agent | gdzie: chmura | kiedy: 2026-11-25 | po: Oceń nową stronę, prawo i RODO, warunki współpracy
  cel: dane z odpowiedzi właściciela są w site/src/dane.js i w tekstach strony
  gotowe gdy: produkcyjne `npm run build` przechodzi bez błędu; zrzuty 390 i 1440 px nie mają [UZUPEŁNIJ] w polach wymaganych; każda wpisana wartość pochodzi z odpowiedzi właściciela, nic nie jest wymyślone
  materiał: site/src/dane.js
  - [ ] Wpisz odpowiedzi do site/src/dane.js; pola bez odpowiedzi zostaw puste i wypisz w zostało:
  - [ ] Zbuduj wersję produkcyjną i roboczą, zrób zrzuty, obejrzyj je
- [ ] Strona: sprawdź stronę pięcioma audytami i popraw | kto: agent | gdzie: chmura | kiedy: 2026-11-26 | po: wpisz dane firmy
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
- [!] Strona: skróć teksty na stronie głównej | kto: agent | gdzie: chmura | kiedy: 2026-11-25 | blokada: produkcyjne `npm run build` nie może przejść, dopóki w danych firmy brakuje wymaganych pól (VAT, adres, gwarancja, stawka i inne); wersja robocza buduje się bez błędu
  cel: strona ma mniej tekstu: krótsze akapity, jedno zdanie na punkt, bez powtórzeń między sekcjami
  gotowe gdy: produkcyjne `npm run build` przechodzi bez błędu; zrzuty 390 i 1440 px obejrzane; w wynik: liczba słów strony głównej przed i po; sens, ceny, dane firmy i miejsca [UZUPEŁNIJ] bez zmian
  materiał: site/src/tresc-pl.js
  materiał: site/src/jezyki/wspolne-pl.js
  - [x] Policz słowa każdej sekcji i skróć najdłuższe (najpierw sekcje z najdłuższym tekstem)
  - [x] Zbuduj, zrób zrzuty, obejrzyj
  wynik: strona główna PL ma 1643 słowa zamiast 1909 (−14%; bez żółtych [UZUPEŁNIJ]). Po sekcjach przed → po: Pytania 442→372, Cennik 369→313, Oferta 154→132, Hero 145→138, Kontakt 140→135, Pewność 133→91, Czat 106→98, Jak pracujemy 102→79, Kalkulator 94→85, Dowody 86→72, O nas 84→74. Usunięte powtórzenia: „cena na piśmie” (zostaje w hero, krokach, cenniku i FAQ), licencje i pliki na Twoim koncie (tylko w „Bez uzależnienia” i FAQ), „60 minut, bez zobowiązań” (tylko w „Pierwsza rozmowa”). Punkty i kroki mają po jednym zdaniu. Ceny, dane firmy, zdania składane z danych firmy i miejsca [UZUPEŁNIJ] są bez zmian. Plik: site/src/jezyki/tresc-pl.js. Zrzuty 390 i 1440 px (/pl): układ się nie rozjechał, akapity w kartach i krokach są wyraźnie krótsze.
  zostało: produkcyjne `npm run build` nie było uruchamiane (brak uprawnień), a i tak zatrzyma się na pustych wymaganych polach w danych firmy; zrzut kończy się na 6000 px, więc Cennika, Pytań i Kontaktu nie oglądałem na obrazie (liczyłem je w kodzie); wersje DE, IT i EN nie są skrócone
  następne: Strona: skróć teksty w wersjach DE, IT i EN tak jak w PL | kto: agent | kiedy: 2026-11-26

## Do rozplanowania
- [x] Przygotuj wizytówkę Oprogramowani dla Krystiana | kto: claude | gdzie: chmura | kiedy: 2026-11-23 | wymaga: odbiór
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
