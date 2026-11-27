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
- [x] Strona: poprawki po punkcie kontrolnym 1 (sekcje, wycena, animacja, telefon) | kto: agent | gdzie: chmura | kiedy: 2026-11-25
  cel: strona prostsza i nastawiona na telefon i bezpłatną wycenę, według uwag właściciela z 25.11
  gotowe gdy: wersja robocza buduje się poleceniem z karty (npm run build:panel), zmiany są we wszystkich językach (PL, DE, IT, EN), zrzuty 390 i 1440 px obejrzane, w wynik: lista zmian sekcja po sekcji; dane firmy i miejsca [UZUPEŁNIJ] bez zmian, bez wymyślonych danych
  materiał: site/src/jezyki/tresc-pl.js
  materiał: site/src/jezyki/wspolne-pl.js
  materiał: site/src/Strona.jsx
  materiał: site/src/strona.css
  gałąź: agent/2026-11-25-strona-poprawki-po-punkcie-kontrolnym-1
  poprawka: Dokończ to zadanie od swojej gałęzi (praca jest już zrobiona, przerwał ją restart panelu): scal bieżącą nowa-koncepcja, zbuduj, obejrzyj zrzuty i zamknij zadanie.
  - [x] Połącz w jedną sekcję: cennik („co realizujemy i ile kosztuje”), „Dwie rzeczy. Robimy je porządnie” i „Cenę znasz, zanim zaczniemy”; ceny zostają jako widełki „od … zł”
  - [x] Usuń motyw „cena znana przed startem” i „ocena przed wyceną” w całej stronie; zamiast tego prosta „Bezpłatna wycena” (główny przycisk zamiast „Umów darmową godzinę”; okno zgłoszenia zostaje jako prośba o wycenę)
  - [x] Wstęp zostaje, ale szarpaną animację zastąp spokojnym ruchem w tle za tekstem (płynnie, bez skoków, z prefers-reduced-motion)
  - [x] Usuń sekcję „Bez wymyślonych opinii” i sekcję „Zanim zadzwonisz” (pytania); „Cztery kroki” i „Zamiast raportów” zostają
  - [x] Strona zachęca do telefonu: numer i „Zadzwoń” w nagłówku i przy wycenie, na telefonie stały przycisk „Zadzwoń” na dole ekranu
  - [x] Pod Google Ads: dane firmy, kontakt i polityka prywatności łatwo dostępne z każdej podstrony; jeśli strona ma tagi analityki lub reklam, baner zgody z Consent Mode v2 (domyślnie odmowa); nowych tagów bez identyfikatorów od właściciela nie dodawaj
  - [x] Zbuduj, zrób zrzuty, obejrzyj, popraw; w wynik: co zmieniono w każdej sekcji
  wynik: zmiany w site/src/Strona.jsx, site/src/strona.css, site/src/dane.js, site/src/jezyki/tresc-{pl,de,it,en}.js i wspolne-{pl,de,it,en}.js, w czterech językach. Sekcja po sekcji: nagłówek — numer 663 206 373 z „Zadzwoń” i czerwony przycisk „Bezpłatna wycena”; wstęp — ten sam tekst, zamiast szarpanej animacji spokojny ruch tła za tekstem (stoi przy prefers-reduced-motion), przyciski „Bezpłatna wycena” i „Zadzwoń”; „Pracujemy na tym, co masz” i kalkulator — treść bez zmian, przycisk „Bezpłatna wycena”; „Co robimy i ile to kosztuje” — jedna sekcja zamiast cennika, „Dwie rzeczy” i „Cenę znasz, zanim zaczniemy”, ceny jako widełki „od … zł”, na końcu czarna karta „Bezpłatna wycena 0 zł” z przyciskiem i telefonem; „Cztery kroki” i „Zamiast raportów” zostały; „Bez wymyślonych opinii” i pytania „Zanim zadzwonisz” usunięte; „Kto to robi” — karty osób i miejsce na film; kontakt — bezpłatna wycena z telefonem na pierwszym planie, okno zgłoszenia jako prośba o wycenę; stopka — dane firmy (NIP), telefon, mail, Prywatność, Cookies i Regulamin na każdej podstronie; na telefonie stały przycisk „Zadzwoń 663 206 373” na dole ekranu. Strona nie ma tagów reklam, a analityka (Plausible bez ciasteczek) jest wyłączona, dopóki nie zostaną wpisane dane, więc baneru zgody nie dodano. Zrzuty 390 i 1440 px (.zrzuty/telefon.png, .zrzuty/komputer.png, .zrzuty/telefon-film.png, .zrzuty/komputer-stopka.png) obejrzane: układ czysty, żółte [UZUPEŁNIJ] bez zmian, nic nie wymyślone
  zmiany: dołączone zmiany z nowa-koncepcja (miejsce na film i opis zdjęć w „Kto to robi”, we wszystkich czterech językach); strona zbudowana, zrzuty obejrzane; poprawka: zrobione
  zostało: gdy dojdzie Google Ads albo inny tag reklamowy, trzeba dodać baner zgody (Consent Mode v2); film i zdjęcia czekają na pliki od właściciela

- [x] Strona: bez wyboru języka, język z przeglądarki | kto: agent | gdzie: chmura | kiedy: 2026-11-25 | po: Strona: poprawki po punkcie kontrolnym 1
  wykonawca: tylko claude
  cel: właściciel nie chce przełącznika języków (PL·DE·IT·EN) na stronie; strona sama wybiera język z ustawień przeglądarki i systemu
  gotowe gdy: w nagłówku i menu na telefonie nie ma przełącznika języków; adres główny kieruje na język z navigator.languages (domyślnie PL); każda wersja językowa ma dalej własny adres i znaczniki hreflang (Google i linki z reklam działają); wersja robocza buduje się poleceniem z karty; zrzuty 390 i 1440 px obejrzane
  materiał: site/src/Strona.jsx
  materiał: site/src/i18n.js
  - [x] Usuń przełącznik języków z nagłówka i menu (komponent Jezyki i jego style, jeśli nigdzie indziej nie są używane)
  - [x] Sprawdź wykrywanie języka na adresie głównym (pl, de, it, en, inny język → PL) i zapamiętanie wyboru tylko z adresu, bez pliku cookie
  - [x] Zostaw adresy /pl/, /de/, /it/, /en/ i hreflang; zbuduj, zrób zrzuty, obejrzyj
  wynik: przełącznika języków nie ma w nagłówku ani na dole strony (site/src/Strona.jsx, site/src/strona.css); adres główny przenosi na język przeglądarki: pl, de, it, en, każdy inny → PL (site/src/main.jsx, site/src/i18n.js); /pl/, /de/, /it/, /en/ działają osobno i każda ma znaczniki hreflang do czterech wersji, x-default → /pl/ (site/scripts/prerender.mjs). Wersja robocza buduje się (poprawiony błąd w kalkulatorze, przez który wcześniej się nie budowała). Na zrzutach 390 i 1440 px nagłówek ma tylko logo, menu sekcji (na komputerze), telefon i „Wycena”; przeglądarka testowa po angielsku trafiła z adresu głównego na /en/.
  zostało: w przeglądarce sprawdzony tylko język angielski; pl/de/it/inny język i domyślne PL sprawdzone w kodzie, nie na żywo.

- [ ] Podaj dane firmy do strony: prawo i RODO | kto: ty | kiedy: 2026-11-27 | czas: 15
  cel: dane prawne, bez których strona nie może wyjść na produkcję
  materiał: site/src/dane.js
  pyta: Ceny netto plus VAT czy zwolnienie z VAT; Sprzedajecie tylko firmom czy także konsumentom; Adres dokładnie jak w CEIDG; Link do wpisu w CEIDG; Data wejścia regulaminu w życie; Dostawca serwera i kraj; Narzędzie do rozmów online i kraj dostawcy; Brevo trzyma dane w EOG czy poza EOG; Ile miesięcy trzymamy rozmowy bez umowy; Ile dni trzymamy logi serwera; Po ilu dniach dane znikają z kopii zapasowych
- [ ] Podaj warunki współpracy do strony: płatności, ceny, godziny | kto: ty | kiedy: 2026-11-27 | czas: 15
  cel: warunki, które strona obiecuje klientom
  materiał: site/src/dane.js
  pyta: Zaliczka w procentach (0 = bez zaliczki); Termin płatności faktury w dniach; Gwarancja w dniach po odbiorze; Stawka opieki po wdrożeniu w zł za godzinę; Czas reakcji na awarię w dniach roboczych; Godziny prac przy projektach; Godziny odbierania telefonu; Zasada bezpłatnej rozmowy jednym zdaniem; Górna cena integracji ERP w zł; Górna cena końca przepisywania w zł; Górna cena małego automatu w zł; Obniżka ceny etapu za tydzień opóźnienia w procentach; Po ilu tygodniach opóźnienia klient może odstąpić; Subiekt GT czy Subiekt nexo; Platformy sklepów, z którymi łączycie
- [ ] Strona: wpisz dane firmy i przygotuj wersję do publikacji | kto: agent | gdzie: chmura | kiedy: 2026-11-25 | po: Oceń nową stronę, prawo i RODO, warunki współpracy
  cel: dane z odpowiedzi właściciela są w site/src/dane.js i w tekstach strony
  gotowe gdy: produkcyjne `npm run build` przechodzi bez błędu; zrzuty 390 i 1440 px nie mają [UZUPEŁNIJ] w polach wymaganych; każda wpisana wartość pochodzi z odpowiedzi właściciela, nic nie jest wymyślone
  materiał: site/src/dane.js
  - [ ] Wpisz odpowiedzi do site/src/dane.js; pola bez odpowiedzi zostaw puste i wypisz w zostało:
  - [ ] Zbuduj wersję produkcyjną i roboczą, zrób zrzuty, obejrzyj je
- [ ] Strona: sprawdź stronę pięcioma audytami i popraw | kto: agent | gdzie: chmura | kiedy: 2026-11-26 | po: wpisz dane firmy, Strona: nowa strategia
  cel: strona gotowa do publikacji w ocenie pięciu audytorów: klient, krytyczny klient, prawnik, projektant interfejsu, specjalista od konwersji
  gotowe gdy: w wynik: ocena każdego audytora (1–10) z jednym powodem; poprawione wszystko, co nie wymaga danych właściciela; reszta w zostało:
  - [ ] Oceń stronę z perspektywy każdego audytora na zrzutach 390 i 1440 px
  - [ ] Popraw znalezione błędy, zbuduj, zrób zrzuty jeszcze raz
- [ ] Oceń stronę przed publikacją (punkt kontrolny 2) | kto: ty | kiedy: 2026-11-27 | czas: 20 | po: pięcioma audytami
  cel: decyzja, czy strona może wyjść na oprogramowani.com
  gotowe gdy: uwagi wysłane z zakładki Strona albo zadanie zamknięte, co oznacza zgodę na publikację
  materiał: site
  pyta: Decyzja o publikacji [wybór: zgoda na publikację | uwagi wysłane z zakładki Strona]
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
- [x] Strona: scal ofertę, połącz kroki z wiadomościami, usuń sekcję o osobach | kto: agent | gdzie: chmura | kiedy: 2026-11-26
  cel: strona prostsza według uwag właściciela z 26.11: jedna oferta, jedna sekcja kroków, mniej tekstu o kosztach, bez sekcji o osobach i bez informacji, gdzie działa automat
  gotowe gdy: wersja robocza buduje się poleceniem z karty (npm run build:panel), zmiany są w PL, DE, IT i EN, zrzuty 390 i 1440 px obejrzane; w wynik: lista zmian sekcja po sekcji; ceny „od … zł”, kalkulator, „Bezpłatna wycena”, dane firmy i miejsca [UZUPEŁNIJ] bez zmian, nic nie wymyślone
  materiał: site/src/Strona.jsx
  materiał: site/src/jezyki/tresc-pl.js
  materiał: site/src/jezyki/wspolne-pl.js
  materiał: site/src/strona.css
  - [x] Scal „Budujemy integracje i małe automaty” oraz „Pilnujemy projektu, który robi ktoś inny” w jedną ofertę (jedna lista pozycji z cenami „od … zł”, bez dwóch grup); „Bezpłatna wycena” zostaje
  - [x] Połącz „Cztery kroki” z „Zamiast raportów na 20 stron” w jedną sekcję (kroki, a pod nimi krótka wiadomość zamiast raportów)
  - [x] Skróć „Co płacisz poza nami” do krótkiej wersji (np. jedno zdanie i krótka lista)
  - [x] W „To Twój automat. Nie jesteś skazany na nas” zmień nagłówek na sens „To automaty dla Ciebie”; usuń zdania o tym, czy automat działa u klienta, na jego serwerze albo lokalnie (decyzję zostawia właściciel)
  - [x] Usuń całkowicie sekcję „Dwie osoby” („Kto wdraża integracje”: karty Pawła i Krystiana, zdjęcia, film) razem z menu i stylami, których nic innego nie używa
  - [x] Zbuduj, zrób zrzuty, obejrzyj, popraw
  poprawka: Poprzednie uruchomienie przerwał restart panelu (2026-11-26 19:09). Twoja dotychczasowa praca jest na gałęzi agent/2026-11-26-strona-scal-oferte-polacz-kroki-z-wiadom: sprawdź ją (git log, git diff) i dokończ zadanie.
  wynik: zmiany w site/src/Strona.jsx, site/src/strona.css oraz site/src/jezyki/tresc-pl.js, tresc-de.js, tresc-it.js, tresc-en.js (wszystkie cztery języki). Sekcja po sekcji: Menu: bez „O nas”. Oferta i ceny: zamiast dwóch grup (Wykonanie / Prowadzenie) jedna lista 7 pozycji (Integracja ERP od 3 500 zł, Koniec przepisywania od 2 000 zł, Mały automat od 2 000 zł, Przegląd oferty 290 zł, Karta projektu 690 zł, Prowadzenie projektu od 490 zł / mies., Opieka i poprawki), nad nią 4 przykłady z ptaszkami, wstęp mówi o obu rodzajach pracy; ceny, widełki, dopłaty, blok „Bezpłatna wycena” i warunki bez zmian. Co płacisz poza nami: jedno zdanie i 3 krótkie punkty (moduł ERP, abonament BaseLinkera, opłaty przewoźnika); usunięty punkt „Komputer albo serwer”. Jak pracujemy: cztery kroki, a pod nimi w tej samej sekcji „Zamiast raportów na 20 stron: krótka wiadomość.” z przykładową rozmową na telefonie (osobna sekcja usunięta). Bez uzależnienia: nagłówek „To automaty dla Ciebie.” (DE „Automatisierungen für Sie.”, IT „Automazioni per te.”, EN „Automations built for you.”); punkt „Automat działa u Ciebie” zamieniony na „Licencje na Twoją firmę” (tylko zdanie o licencjach, bez tego, gdzie działa automat). Kto wdraża integracje: sekcja usunięta w całości (karty Pawła i Krystiana, zdjęcia, film oraz ich style). Kalkulator, wstęp, kontakt i dane firmy bez zmian. Zrzuty 390 i 1440 px (PL i EN) obejrzane: oferta jako jedna lista, kroki z rozmową pod spodem, nic nie wychodzi poza ekran.
  zostało: znikają żółte miejsca [UZUPEŁNIJ] związane wyłącznie z usuniętą sekcją o osobach (nazwisko i LinkedIn Pawła, zdjęcia, lata każdej osoby, film); pola w dane.js zostają bez zmian, a lata doświadczenia nadal są we wstępie
  zmiany: poprzednia gałąź nie miała zapisanej pracy, więc zadanie zrobione od nowa w całości; poprawka: zrobione

- [x] Strona: zacznij od problemu klienta, każda obietnica raz | kto: agent | gdzie: chmura | kiedy: 2026-11-27
  wykonawca: tylko claude
  cel: według uwag właściciela z 27.11: strona zaczyna od jego chwytów (koszty ERP, integrator na 3 miesiące, cena jak za system za jeden moduł, integracja znowu nie działa), bez powtarzania „demo”, „najpierw widzisz, potem płacisz”, „Od wyceny do opieki”, „Co robimy”, „Zanim zadzwonisz”; dokładna treść sekcja po sekcji w strona-uwagi-2026-11-27.md
  gotowe gdy: strona główna i 4 podstrony mają treść z pliku uwag we wszystkich językach (PL, DE, IT, EN); na stronie głównej PL słowo „demo” najwyżej 2 razy (policz w zbudowanym HTML); niezatwierdzone zmiany z 26.11 w głównym drzewie (strona-bez-powtorzen-2026-11-26.diff) są przejęte albo zastąpione, a drzewo czyste po scaleniu; wersja robocza buduje się poleceniem z karty (npm run build:panel); zrzuty 390 i 1440 px PL i EN obejrzane; dane firmy, ceny i miejsca [UZUPEŁNIJ] bez zmian, nic nie wymyślone; w wynik: lista zmian sekcja po sekcji i liczba „demo” przed i po
  materiał: strona-uwagi-2026-11-27.md
  materiał: strona-bez-powtorzen-2026-11-26.diff
  materiał: site/src/jezyki/tresc-pl.js
  materiał: site/src/Strona.jsx
  materiał: site/src/strona.css
  wynik: zmiany w site/src/Strona.jsx, site/src/strona.css, site/src/jezyki/tresc-pl.js, tresc-de.js, tresc-it.js, tresc-en.js (PL, DE, IT, EN). Sekcja po sekcji: Meta: tytuł „Oprogramowani — prosty program zamiast wielkiego ERP-a”, opis i og z pliku uwag. Menu: „Jak to działa” → „Problemy” (do „Brzmi znajomo?”). Hero: „Po co Ci wielki ERP? Napiszemy prosty program pod Twoją firmę.”, lead „Albo połączymy programy, które już masz.”, przycisk „Bezpłatna wycena”; „Najpierw demo. Potem płacisz.” usunięte. Brzmi znajomo?: nowa sekcja z 4 kartami (koszty ERP, integrator na 3 miesiące, cena jak za system za jeden moduł, zintegrowane a znowu nie działa), każda z jedną linią odpowiedzi; 4. karta bierze zdanie o etapie z GWAR_ETAP; kroki „Od wyceny do opieki” usunięte w całości. Kafelki oferty: treść bez zmian, bez widocznego nagłówka „Co robimy”. Ceny: „Ile to kosztuje. Cenę znasz na piśmie, zanim zaczniemy.”, nowy lead, pozycje i kwoty te same, opis Demo z pliku uwag (z warunkiem), wdrożenie „Stała cena” bez „po demie”; VAT, „Co płacisz poza nami” i warunki zostały (pierwszy warunek skrócony o zdanie o demie). Bez ryzyka: „Dokładamy, nie wymieniamy.” z 2 kartami, w pierwszej dopisane zdanie o braku partnerstwa z producentem. Zanim zadzwonisz: sekcja usunięta. Kontakt: „Opisz, co ma działać. W ciągu dnia oddzwonimy z widełkami ceny.”. Podstrony (4): meta bez „Najpierw demo, potem płacisz”, w sekcji pokazu jedno zdanie (bez „Nie płacisz…” i warunku dema), cena „Cenę podajemy w bezpłatnej wycenie, w ciągu dnia.”, integracje: trzeci problem „Zintegrowane, a znowu nie działa” (KSeF został w liście), IT: [UZUPEŁNIJ] o planie i oględzinach został. Niezatwierdzone zmiany z 26.11 (strona-bez-powtorzen-2026-11-26.diff) zastąpione tą wersją. Słowo „demo” (z odmianami) w zbudowanym dist/pl/index.html: przed 30, po 1 (pozycja „Demo” w cenniku). Wersja robocza buduje się (npm run build:panel). Zrzuty 390 i 1440 px PL i EN obejrzane: hero z pytaniem o ERP, 4 karty problemów w rzędzie na komputerze i jedna pod drugą na telefonie, nic nie wychodzi poza ekran; dane firmy, ceny i żółte [UZUPEŁNIJ] bez zmian.
  zostało: nie sprawdziłem, czy główne drzewo jest czyste po scaleniu; stare zmiany z 26.11 są zastąpione tą wersją, więc przy scalaniu wygrywa ta wersja
  następne: Strona: obejrzyj podgląd z „Brzmi znajomo?” i zatwierdź teksty DE, IT, EN | kto: ty | kiedy: 2026-11-28

- [x] Strona: poprawki po audycie, runda 1 (Paweł, ceny, słowa klientów, rzetelność) | kto: agent | gdzie: chmura | kiedy: 2026-11-27 | po: Strona: zacznij od problemu klienta
  wykonawca: tylko claude
  gałąź: agent/2026-11-27-strona-zacznij-od-problemu-klienta-kazda
  wynik: zmiany w site/src/jezyki/tresc-pl.js, tresc-de.js, tresc-it.js, tresc-en.js, site/src/Strona.jsx, site/src/strona.css, sekcja po sekcji (PL, DE, IT, EN): Meta: nowy tytuł i opis z Allegro, BaseLinker, Subiekt GT, Optima, KSeF; Hero: lead z nazwami programów i nowa drobna linia pod przyciskiem („Opisz, co ma działać. W ciągu dnia roboczego oddzwonimy z widełkami ceny.”); Brzmi znajomo?: karta 02 z warunkiem „po wycenie i potwierdzeniu widełek”, karta 04 „dzwonisz do nas”; Kafelki: planowanie „zamiast kartek i Excela”, integracje „Integracje: Allegro · BaseLinker · Subiekt · Optima · KSeF” (nazwy nieskrócone); Ceny: nowy lead o widełkach i stałej cenie, wycena „Zadzwoń albo napisz. Do niczego nie zobowiązuje.”, Demo bez powtórzonego warunku, trzeci warunek tylko z zasadą rozmowy z dane.js (pusta = punkt znika); Pewność: nagłówek „Twoje programy zostają” zamiast „Bez ryzyka”, zdanie o ERP, którego nie ruszamy; Kontakt: nowy tekst o programach i ręcznej pracy, zdanie „Programy piszą Krystian i Paweł…” z nazwiskiem i formą z dane.js (dziś żółte [UZUPEŁNIJ]), zdanie o widełkach przeniesione do hero; Stopka: bez „symulacji”; Podstrony: „Co zobaczysz przed decyzją” zamiast „Jak wygląda demo”, widełki w ciągu dnia roboczego i stała cena na piśmie; planowanie z przykładem stolarni i punktem o handlowcu z telefonem; integracje z nowym tytułem, opisem, H1, nazwą i punktem „Faktury z KSeF do Optimy albo Subiekta i z powrotem”. Wersja robocza się buduje; w dist/pl/index.html „demo” 1 raz, „zobowiązuje” 1 raz. Obejrzane zrzuty 390 i 1440 px: strona główna PL i EN, podstrona integracji PL (390) i EN (1440); nowe zdania są na miejscu, na komputerze nagłówek kafelka integracji zajmuje 4 linie. dane.js bez zmian, nic nie wymyślone.
  zostało: zdanie o Pawle pokaże nazwisko i formę współpracy dopiero po wpisaniu ich do danych firmy (do tego czasu na produkcji: „Programy piszą Krystian i Paweł.”)
  cel: strona po rundzie 1 audytu (11 ocen): Paweł przedstawiony w kontakcie z danymi z dane.js, ceny bez obietnicy kwoty, hero i kafelki ze słowami klientów (Allegro, BaseLinker, Subiekt, Optima, KSeF, Excel), poprawki kontrolera rzetelności (warunek przy „1–2 dni”, IT bez „demo”, widełki zamiast ceny w ciągu dnia, bez „Bez ryzyka” i podwójnego „bez zobowiązań”); dokładne zdania w strona-runda-1-2026-11-27.md
  gotowe gdy: zmiany ze specyfikacji są w PL, DE, IT i EN (strona główna i 4 podstrony); wersja robocza buduje się poleceniem z karty (npm ci && npm run build:panel); zrzuty 390 i 1440 px PL i EN obejrzane; w dist/pl/index.html „demo” najwyżej 2 razy; dane.js i miejsca [UZUPEŁNIJ] bez zmian, nic nie wymyślone; w wynik lista zmian sekcja po sekcji
  materiał: strona-runda-1-2026-11-27.md
  materiał: site/src/jezyki/tresc-pl.js
  materiał: site/src/Strona.jsx
  materiał: site/src/strona.css

- [x] Strona: poprawki po audycie, runda 2 (codzienne problemy, cena, rzetelność) | kto: agent | gdzie: chmura | kiedy: 2026-11-27 | po: Strona: poprawki po audycie, runda 1
  wykonawca: tylko claude
  gałąź: agent/2026-11-27-strona-zacznij-od-problemu-klienta-kazda
  wynik: zmiany w site/src/jezyki/tresc-pl.js, tresc-de.js, tresc-it.js, tresc-en.js i site/src/Strona.jsx (nowy akapit pod „Brzmi znajomo?”), sekcja po sekcji (PL, DE, IT, EN): Meta: opis strony głównej „Stała cena przed startem” zamiast „na piśmie”; Hero: drobna linia „Opisz, co ma działać. Krystian, nie handlowiec, oddzwoni z widełkami ceny, zwykle w ciągu dnia roboczego.”; Brzmi znajomo?: nowe zdanie o Allegro i Subiekcie, kartce na hali i KSeF, karta 01 „część firmy” i „za stałą cenę”, karta 02 „Gdy widełki ceny Ci pasują… Termin całego wdrożenia podajemy w wycenie.”; Kafelki: „Integracje Allegro, BaseLinker, Subiekt, Optima, KSeF” (przecinki), „Makra i automatyzacja Excela”; Ceny: nagłówek „Jak ustalamy cenę.” (DE „So entsteht der Preis.”, IT „Come fissiamo il prezzo.”, EN „How we set the price.”), nowy lead bez „na piśmie”, Wdrożenie z licencjami innych firm (abonament BaseLinkera); Dokładamy, nie wymieniamy: nadtytuł „Bez przesiadki”, lead o danych i nauce od nowa, karta 1 kończy się „nie mamy interesu, żeby namawiać Cię na nowy system”; Kontakt: tylko „Programy piszą Krystian i Paweł…”; Podstrony: planowanie z „i stolarni” w tytule, nazwy integracji i Excela jak na kafelkach. Wersja robocza się buduje; w dist/pl/index.html „demo” 1 raz, „na piśmie” 2 razy. Zrzuty 390 i 1440 px PL i EN obejrzane: nowe zdanie pod „Brzmi znajomo?” jest na miejscu, kafelek integracji na 1440 px ma 4 krótkie linie, ale żadna nie zaczyna się od przecinka ani „·”. dane.js i [UZUPEŁNIJ] bez zmian, nic nie wymyślone.
  zostało: nowe zdania DE, IT i EN przetłumaczyłem sam i nikt ich jeszcze nie czytał; w kontakcie nadal jest „odpisujemy zwykle w ciągu dnia roboczego” (specyfikacja kazała zostawić)
  cel: strona po rundzie 2 audytu (11 nowych ocen): pod „Brzmi znajomo?” zdanie o codziennych problemach (Allegro i Subiekt, kartka na hali, KSeF), „Jak ustalamy cenę” zamiast obietnicy kwoty, kafelek integracji bez łamania na „·”, mniej powtórzeń „na piśmie” i „Twoje programy zostają”, poprawki kontrolera rzetelności; dokładne zdania w strona-runda-2-2026-11-27.md
  gotowe gdy: zmiany ze specyfikacji są w PL, DE, IT i EN (strona główna i 4 podstrony); wersja robocza buduje się poleceniem z karty (npm ci && npm run build:panel); zrzuty 390 i 1440 px PL i EN obejrzane; w dist/pl/index.html „demo” najwyżej 2 razy i „na piśmie” najwyżej 3 razy; dane.js i miejsca [UZUPEŁNIJ] bez zmian, nic nie wymyślone; w wynik lista zmian sekcja po sekcji
  materiał: strona-runda-2-2026-11-27.md
  materiał: site/src/jezyki/tresc-pl.js
  materiał: site/src/Strona.jsx
  materiał: site/src/strona.css

- [~] Strona: poprawki po audycie, runda 3 (spójność demo, widełek i kosztów) | kto: agent | gdzie: chmura | kiedy: 2026-11-27 | po: Strona: poprawki po audycie, runda 2
  wykonawca: tylko claude
  cel: ostatnie poprawki po rundzie 3 audytu: to samo zdanie o pokazie programu i widełkach na głównej i podstronach, demo w cenniku tylko dla programów, integracji i Excela, koszty innych firm na głównej, lepsze zdanie pod „Brzmi znajomo?”; dokładne zdania w strona-runda-3-2026-11-27.md
  gotowe gdy: zmiany ze specyfikacji są w PL, DE, IT i EN; wersja robocza buduje się poleceniem z karty (npm ci && npm run build:panel); zrzuty 390 i 1440 px PL i EN obejrzane; w dist/pl/index.html „demo” najwyżej 2 razy; dane.js i miejsca [UZUPEŁNIJ] bez zmian, nic nie wymyślone; w wynik lista zmian
  materiał: strona-runda-3-2026-11-27.md
  materiał: site/src/jezyki/tresc-pl.js

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
- [x] Strona: nowa strategia „Najpierw demo. Potem płacisz.” i cztery linie oferty | kto: agent | gdzie: chmura | kiedy: 2026-11-26
  wykonawca: tylko claude
  wygląd: bez zmian (właściciel 26.11: obecny wygląd mu się podoba). Te same kolory, czcionki, odstępy, komponenty i animacje; nowe elementy (kafelki, podstrony, sekcja kroków) budujesz z istniejących komponentów i stylów strony; nie przebudowujesz interfejsu, zmieniasz treść i kolejność sekcji
  cel: strona oprogramowani.com zgodna ze strategią przyjętą przez właściciela 26.11 (/home/panel/projekty/company-audits/strategia-2026-11-26.md); różnice względem obecnej wersji opisane w krokach poniżej; najpierw PL, pozostałe języki w następnym zadaniu
  gotowe gdy: wersja robocza buduje się poleceniem z karty (npm run build:panel); zrzuty 390 i 1440 px strony głównej i każdej z 4 podstron obejrzane; w wynik: lista zmian sekcja po sekcji (było → jest); żadne dane firmy, ceny, opinie ani liczby nie są wymyślone; brakujące dane zostają jako [UZUPEŁNIJ]
  materiał: site/src/Strona.jsx
  materiał: site/src/jezyki/tresc-pl.js
  materiał: site/src/jezyki/wspolne-pl.js
  materiał: site/src/dane.js
  - [x] Nagłówek strony głównej: duże hasło „Najpierw demo. Potem płacisz.”, pod nim jedno zdanie „Proste programy i dodatki dla małych firm.” i jeden przycisk „Bezpłatna wycena”; usuń z nagłówka „Zamówienia same trafiają do ERP” i słowo ERP
  - [x] Pod nagłówkiem 4 kafelki linii oferty, każdy prowadzi do swojej podstrony: „Planowanie produkcji” (/planowanie-produkcji), „Optima · Subiekt · BaseLinker · KSeF” (/integracje), „Excel bez ręcznej pracy” (/excel), „IT i sprzęt w firmie” (/it)
  - [x] Podstrony: nagłówek H1 i tytuł strony z frazą, której ludzie szukają: „Program do planowania produkcji”, „Integracja Optima, Subiekt, BaseLinker i KSeF”, „Makra i automatyzacja Excela”, „IT i sprzęt w małej firmie”; na każdej: 3 typowe problemy (scenki z życia firmy, bez nazw firm), co robimy, jak wygląda demo, przycisk „Bezpłatna wycena”; meta description do 155 znaków z tą samą frazą
  - [x] Sekcja „Jak to działa” w 4 krokach: bezpłatna wycena w ciągu dnia; demo w 1–2 dni na przykładowych danych, nie płacisz, jeśli nie chcesz dalej; wdrożenie za stałą cenę; opieka, gdy chcesz
  - [x] Z oferty usuń ogólny „system CRM”, strony, sklepy i aplikacje, jeśli są; hasło „Nie kupuj wielkiego ERP-a” tylko jako jedna sekcja na podstronie /integracje dla szukających ERP
  - [x] Kontakt: e-mail kontakt@oprogramowani.com w dane.js, w stopce i przy formularzu „Bezpłatna wycena” (adres działa, potwierdził właściciel 26.11); telefon i inne dane tylko z dane.js
  - [x] Ceny: zostaw istniejące kwoty „od … zł” tylko tam, gdzie pasują do nowych linii; nowych kwot nie wymyślaj; gdzie brak ceny, zostaje „Bezpłatna wycena”
  - [x] Zbuduj, zrób zrzuty, obejrzyj, popraw; w zostało: co wymaga decyzji właściciela
  wynik: polska strona według strategii z 26.11 (site/src/Strona.jsx, site/src/jezyki/tresc-pl.js, site/src/jezyki/wspolne-pl.js, site/src/dane.js, site/src/strona.css, site/scripts/prerender.mjs); buduje się (npm run build:panel), zrzuty 390 i 1440 px strony głównej i 4 podstron obejrzane. Sekcja po sekcji (było → jest): nagłówek „Zamówienia same trafiają do ERP. Ty zajmujesz się firmą.” + 2 przyciski, cena, „Co dalej” → „Najpierw demo. Potem płacisz.”, „Proste programy i dodatki dla małych firm.”, jeden przycisk „Bezpłatna wycena” (bez słowa ERP); lista programów i kalkulator na głównej → 4 kafelki linii oferty z linkami do podstron (lista programów i kalkulator przeniesione na /integracje); „Jak pracujemy” (wycena, zakres, etapy, przekazanie) po cenniku → „Jak to działa” zaraz po kafelkach: wycena w ciągu dnia, demo w 1–2 dni (nie płacisz, jeśli nie chcesz dalej), wdrożenie za stałą cenę, opieka w ryczałcie, gdy chcesz; cennik 7 pozycji (integracja ERP, przepisywanie, automat, przegląd oferty 290 zł, karta projektu 690 zł, prowadzenie od 490 zł/mies., opieka za stawkę) → 4 linie oferty + opieka: integracje od 3 500 zł, planowanie, Excel i IT „Bezpłatna wycena”, opieka [UZUPEŁNIJ: ryczałt]; „To automaty dla Ciebie” → „To programy dla Ciebie” (opieka nieobowiązkowa); kontakt: e-mail i telefon z dane.js, e-mail także w nagłówku okna „Bezpłatna wycena” i w stopce. Nowe podstrony: /pl/planowanie-produkcji, /pl/integracje (z sekcją „Nie kupuj wielkiego ERP-a”, cenami od 3 500 i od 2 000 zł oraz kosztami poza nami), /pl/excel, /pl/it; na każdej H1 i title z frazą, 3 scenki, co robimy, jak wygląda demo, przycisk „Bezpłatna wycena”, meta description 130–153 znaki. Tematy w oknie wyceny: Planowanie produkcji / Integracja lub dodatek / Excel albo IT / Jeszcze nie wiem. CRM, strony, sklepów ani aplikacji w ofercie nie było. DE, IT i EN bez zmian (stary układ)
  zostało: kwota opieki w ryczałcie (pytanie w karcie); do potwierdzenia przez właściciela: czy usługi doradcze (przegląd oferty, karta projektu, prowadzenie projektu) mają wrócić na stronę oraz czy przy IT „demo” to plan na piśmie, a oględziny na miejscu są bezpłatne (na /pl/it żółte pole); podstrony są pod /pl/…, bo /it to włoska wersja strony; scenki na podstronach to przykłady napisane przez agenta, bez danych klientów
  następne: Strona: przenieś nową strukturę do DE, IT i EN | kto: agent | kiedy: 2026-11-28
- [~] Wizytówka i kontakt pod nową strategię | kto: agent | gdzie: chmura | kiedy: 2026-11-26 | wymaga: odbiór
  wykonawca: tylko claude
  cel: nowa wizytówka Oprogramowani i jednolite dane kontaktowe zgodne ze strategią z 26.11 (/home/panel/projekty/company-audits/strategia-2026-11-26.md), z działającym adresem kontakt@oprogramowani.com
  gotowe gdy: w folderze wizytowka/ jest nowa wersja (wizytowka-2026-11.pdf, 2 strony, 85×55 mm plus 3 mm spadu; przod.png i tyl.png 300 dpi; podglad.png do obejrzenia): przód z logo i hasłem „Najpierw demo. Potem płacisz.”, tył z imieniem i nazwiskiem z poprzedniej wizytówki, cztery linie oferty jednym wierszem, kontakt@oprogramowani.com i oprogramowani.com; jest też stopka e-mail (stopka-email.html i stopka-email.txt) z tymi samymi danymi; telefon i inne dane tylko z odpowiedzi właściciela, bez wymyślania; poprzednia wizytówka zostaje bez zmian
  materiał: wizytowka/
  materiał: site/src/dane.js
  - [x] Obejrzyj poprzednią wizytówkę i styl strony; trzymaj ten sam wygląd
  - [x] Zrób przód, tył, PDF do druku i podgląd; zrób stopkę e-mail
  - [x] Jeśli brakuje telefonu albo roli pod nazwiskiem, zadaj pytanie w karcie (pyta:) zamiast zgadywać
  wynik: wizytowka/wizytowka-2026-11.pdf (2 strony 91×61 mm = 85×55 mm + 3 mm spadu), wizytowka/przod.png i wizytowka/tyl.png (1075×720 px, 300 dpi), wizytowka/podglad.png (obie strony z linią cięcia), wizytowka/stopka-email.html i wizytowka/stopka-email.txt (podgląd: wizytowka/stopka-email.png); źródło: wizytowka/wizytowka-2026-11.html, .css, .js. Wygląd jak poprzednia wizytówka i strona (biel, Inter, czerwone PRO w logo). Przód: logo, „Najpierw demo. Potem płacisz.” (druga część szara jak na stronie), „Proste programy i dodatki dla małych firm.”. Tył: Krystian Stryjakiewicz, „Procesy i rozmowa z klientem”, 663 206 373, kontakt@oprogramowani.com, oprogramowani.com, pod kreską „Planowanie produkcji · Integracje · Excel · IT i sprzęt”. Stopka e-mail z tymi samymi danymi. Poprzednia wizytówka z 23.11 bez zmian
  decyzja: czy telefon 663 206 373 i rola „Procesy i rozmowa z klientem” (obie z poprzedniej wizytówki) zostają na nowej wizytówce i w stopce; nowego pytania w karcie nie dodałem, bo czeka tam pytanie o ryczałt
  zostało: wizytówka nie jest wysłana do drukarni (przed drukiem warto zamówić próbny wydruk); stopki nie sprawdzałem w Gmailu ani Outlooku, tylko w przeglądarce
- [~] Koncepcja: rezerwacje ze strony do kalendarza Apple i powiadomienie ntfy | kto: agent | gdzie: chmura | kiedy: 2026-11-27 | wymaga: odbiór
  wykonawca: tylko claude
  cel: właściciel chce, żeby każda rezerwacja albo zgłoszenie ze strony oprogramowani.com pojawiało się jako wydarzenie w jego kalendarzu Apple (iCloud) i dawało powiadomienie ntfy; dziś rezerwacje (mailhook/rezerwacje.sh) nie są połączone z żadnym kalendarzem; to koncepcja do decyzji, bez wdrażania
  gotowe gdy: jest plik koncepcja-rezerwacje-kalendarz.md z sekcjami: (1) jak dziś działa rezerwacja (mailhook: contact.sh, rezerwacje.sh, lib-rezerwacje.sh, listener.sh) i gdzie trafiają dane; (2) 2–3 sposoby połączenia z kalendarzem Apple z zaletami i wadami, m.in. zapis wydarzenia przez CalDAV iCloud (hasło aplikacji wpisuje właściciel sam do pliku 0600 na serwerze), zaproszenie .ics wysłane e-mailem na adres Apple ID, kalendarz subskrybowany (adres .ics); (3) powiadomienie ntfy z tego samego miejsca (jaki temat, co w treści, bez danych osobowych w treści); (4) RODO: jakie dane klienta idą do kalendarza i powiadomienia, jak długo zostają; (5) rekomendacja i szacunek pracy; nic nie zmieniasz w kodzie, nie tworzysz kont ani haseł
  materiał: mailhook/
  materiał: site/src/dane.js
  wynik: koncepcja-rezerwacje-kalendarz.md z 5 sekcjami: (1) jak dziś działa mailhook i dokąd trafiają dane; (2) trzy warianty z zaletami i wadami: A zapis do iCloud przez CalDAV (hasło aplikacji tylko w pliku 0600 na serwerze), B zaproszenie .ics e-mailem, C kalendarz subskrybowany; (3) ntfy na osobnym, losowym temacie, w treści tylko termin, forma i temat; (4) RODO i czas przechowywania; (5) rekomendacja A + ntfy, wcześniej naprawa zapisu rezerwacji, ok. 2 dni pracy agenta i 15 min właściciela. Ważne: od 19.08 strona nie zapisuje rezerwacji i nie sprawdza zajętych godzin (zmiana „Repairs”), więc dwie osoby mogą zarezerwować tę samą godzinę; zgłoszenia przychodzą tylko mailem
  decyzja: wariant kalendarza A (zapis do iCloud, Ty tworzysz hasło aplikacji i wpisujesz je na serwerze) albo C (subskrypcja bez hasła, wydarzenie pojawia się z opóźnieniem do ok. godziny); w kalendarzu i ntfy domyślnie bez e-maila i telefonu gościa (inaczej Apple trzeba dopisać w polityce prywatności); czy kalendarz ma widzieć Paweł
  zostało: nic nie jest wdrożone ani przetestowane na prawdziwym iCloud i ntfy; okres przechowywania rezerwacji (dane.js, retencja.rozmowy) jest wciąż pusty, a od niego zależy automatyczne sprzątanie kalendarza
  następne: Mailhook: przywrócić zapis rezerwacji i dodać ntfy oraz kalendarz według koncepcji | kto: agent | kiedy: 2026-12-01
- [x] Strona: polski ma pierwszeństwo, gdy przeglądarka zna polski | kto: agent | gdzie: chmura | kiedy: 2026-11-26
  wykonawca: tylko claude
  cel: właściciel ma w przeglądarce najpierw angielski, a dalej polski, więc adres główny i podgląd w panelu pokazują wersję EN i nie da się przejść na PL (przełącznika nie ma); wybór języka w site/src/i18n.js ma brać polski, jeśli jest gdziekolwiek na liście navigator.languages, w pozostałych przypadkach jak dotąd (pierwszy z de, it, en; domyślnie PL)
  gotowe gdy: w i18n.js wybór języka działa według celu; wersja robocza buduje się (npm run build:panel); w wynik: sprawdzenie w przeglądarce z listą języków [en-US, pl-PL] → /pl/, [de-DE] → /de/, [fr-FR] → /pl/; nic poza wyborem języka się nie zmienia
  materiał: site/src/i18n.js
  wynik: site/src/i18n.js: polski wygrywa, gdy jest gdziekolwiek na liście języków przeglądarki; poza tym jak dotąd (pierwszy z de, it, en; brak → PL); zmieniona tylko ta jedna funkcja; wersja robocza buduje się (npm run build:panel), nowy kod jest w zbudowanej stronie; w przeglądarce z samym angielskim (bez polskiego) adres główny prowadzi do /en/, zrzuty (telefon, komputer) pokazują wersję EN bez zmian w wyglądzie
  zostało: nie sprawdziłem w przeglądarce trzech list z warunku ([en-US, pl-PL] → /pl/, [de-DE] → /de/, [fr-FR] → /pl/), bo przeglądarka agenta ma stałą listę języków, a skrypt, który ją zmienia, został odrzucony (brak uprawnień); według kodu wyniki będą zgodne z celem
  następne: Strona: sprawdzić wybór języka dla list [en-US, pl-PL], [de-DE], [fr-FR] | kto: agent | kiedy: 2026-11-27
- [x] Strona: przenieś nową strukturę do DE, IT i EN | kto: agent | gdzie: chmura | kiedy: 2026-11-26 | po: Strona: polski ma pierwszeństwo
  wykonawca: tylko claude
  wygląd: bez zmian; ten sam układ i komponenty co w nowej wersji PL
  cel: wersje DE, IT i EN mają tę samą strukturę i treść co nowa wersja PL z 26.11 (nagłówek „Najpierw demo. Potem płacisz.”, 4 kafelki i 4 podstrony, „Jak to działa”, kontakt@oprogramowani.com); dziś EN pokazuje jeszcze starą stronę
  gotowe gdy: /de/, /it/, /en/ i ich 4 podstrony odpowiadają PL; tłumaczenia naturalne, nie dosłowne; frazy w tytułach podstron w języku danej wersji; wersja robocza buduje się (npm run build:panel); zrzuty 390 i 1440 px każdej wersji obejrzane; w wynik: lista podstron w każdym języku; nic nie wymyślone, brakujące dane jako [UZUPEŁNIJ] jak w PL
  materiał: site/src/jezyki/tresc-pl.js
  materiał: site/src/jezyki/
  materiał: site/src/Strona.jsx
  wynik: site/src/jezyki/tresc-de.js, tresc-it.js, tresc-en.js przepisane na układ PL: „Erst die Demo. Dann zahlen Sie.” / „Prima la demo. Poi paghi.” / „Demo first. Then you pay.”, 4 kafelki, „Jak to działa” (4 kroki + wiadomość), ceny jak w PL, „To programy dla Ciebie”, kontakt z kontakt@oprogramowani.com; podstrony: DE /de/produktionsplanung, /de/integrationen, /de/excel, /de/it; IT /it/pianificazione-produzione, /it/integrazioni, /it/excel, /it/informatica; EN /en/production-planning, /en/integrations, /en/excel, /en/it; tytuły podstron z frazą w języku wersji (np. „Software für Produktionsplanung”, „Integrazione Optima, Subiekt, BaseLinker e KSeF”, „Excel macros and automation”); kwot nie dodano, brakujące dane jako żółte [UZUPEŁNIJ] jak w PL; site/src/Strona.jsx rozpoznaje podstronę z cennikiem po polu w treści, nie po polskim adresie; wersja robocza buduje się (npm run build:panel, 12 podstron DE/IT/EN); zrzuty 390 i 1440 px /de, /it, /en oraz /en/integrations i /it/pianificazione-produzione obejrzane: układ jak w PL; jedną usterkę (DE, „Produktionsplanung” łamane w środku słowa na komputerze) poprawiłem
  zostało: zrzutami obejrzałem 2 z 12 podstron DE/IT/EN (pozostałe mają ten sam układ, zbudowały się, ale ich nie oglądałem); tłumaczenia zrobione przeze mnie, nikt mówiący tymi językami od urodzenia ich nie sprawdzał
  następne: Strona: hreflang między podstronami PL/DE/IT/EN | kto: agent | kiedy: 2026-11-28
- [x] Strona: cała strona główna według nowej strategii (stare sekcje ERP, cennik, projekty) | kto: agent | gdzie: chmura | kiedy: 2026-11-26
  wykonawca: tylko claude
  wygląd: bez zmian; te same kolory, czcionki, komponenty; sekcje usuwasz albo zmieniasz treść, nie przebudowujesz interfejsu
  cel: po zadaniu „Strona: nowa strategia” nagłówek, kafelki, kroki i podstrony są nowe, ale niżej na stronie głównej zostały sekcje ze starej strategii (integracje ERP, ceny, usługi doradcze); właściciel 26.11: strona ma w całości mówić nową strategią z /home/panel/projekty/company-audits/strategia-2026-11-26.md, we wszystkich językach (PL, DE, IT, EN)
  gotowe gdy: na stronie głównej i podstronach w PL, DE, IT i EN nie ma: sekcji z nazwami ERP (systemy: Subiekt, Optima, WAPRO jako „zamówienia do ERP”), kalkulatora przepisywania zamówień, starego cennika z kwotami (integracja ERP od 3 500 zł, koniec przepisywania od 2 000 zł, mały automat od 2 000 zł, przegląd oferty innego wykonawcy 290 zł, karta projektu 690 zł, prowadzenie cudzego projektu od 490 zł/mies.) ani listy usług doradczych; słowo „ERP” zostaje tylko w sekcji „Nie kupuj wielkiego ERP-a” na podstronie /integracje; wersja robocza buduje się (npm run build:panel); zrzuty całej strony głównej (wszystkie sekcje, w częściach, jeśli zrzut się ucina) w 390 i 1440 px w każdym języku obejrzane; w wynik: lista sekcji strony głównej od góry do dołu (było → jest)
  materiał: site/src/Strona.jsx
  materiał: site/src/jezyki/
  materiał: site/src/dane.js
  - [x] Usuń sekcję „systemy” (lista ERP) i sekcję kalkulatora („policz”) ze strony głównej
  - [x] Zastąp stary cennik krótką sekcją „Ile to kosztuje”: wycena 0 zł, demo 0 zł, wdrożenie za stałą cenę ustaloną po demie; bez kwot (nowych nie wymyślaj)
  - [x] Usuń usługi doradcze (przegląd oferty innego wykonawcy, karta projektu, prowadzenie cudzego projektu) ze wszystkich sekcji i stopki
  - [x] Sekcję „pewność” przepisz pod demo przed płatnością i cztery linie oferty, bez ERP
  - [x] Pytania (FAQ): 5 pytań pod nową strategię: ile trwa demo; co, jeśli demo mi nie pasuje; jak liczycie cenę wdrożenia; czy muszę zmieniać program, którego używam; czy robicie też IT i sprzęt
  - [x] Teksty prawne i warunki: „producent ERP” zmień na „producent programu”; sens warunków bez zmian
  - [x] To samo w DE, IT i EN; zbuduj, zrób zrzuty całej strony, obejrzyj każdą sekcję, popraw
  wynik: strona główna PL/DE/IT/EN od góry (było → jest): Wstęp „Najpierw demo. Potem płacisz.” → bez zmian; Oferta (4 kafelki) → bez zmian; Jak to działa (4 kroki + wiadomość) → bez zmian; Oferta i ceny (5 pozycji, integracja od 3 500 zł) → „Ile to kosztuje”: bezpłatna wycena 0 zł, demo 0 zł, wdrożenie „stała cena po demie”, opieka „miesięczny ryczałt”, warunki, bez kwot; „To programy dla Ciebie” (licencje Optimy, Subiekta…) → „Najpierw widzisz, potem płacisz”: demo przed płatnością, stała cena po demie, zostajesz przy swoich programach, wszystko zostaje u Ciebie; (brak) → nowa sekcja „Pytania” z 5 rozwijanymi pytaniami; Kontakt i stopka → bez zmian, ze stopki znika WAPRO. Na podstronie /integracje (i jej odpowiednikach DE/IT/EN) zniknęły lista systemów, kalkulator i cennik z kwotami 3 500 / 2 000 / 2 000 zł; jest „Cenę podajemy w bezpłatnej wycenie” i „Co płacisz poza nami”. „ERP” zostało tylko w sekcji „Nie kupuj wielkiego ERP-a” (sprawdzone w zbudowanych stronach); „producent ERP” → „producent programu” we wszystkich językach; usług doradczych na stronie już nie było. Pliki: site/src/Strona.jsx, site/src/jezyki/tresc-pl.js, tresc-de.js, tresc-it.js, tresc-en.js, site/index.html (tytuł i opis bez ERP). Wersja robocza się buduje; obejrzałem zrzuty każdej sekcji w 390 i 1440 px w PL, DE, IT i EN (oraz /pl/integracje); jedna poprawka po zrzutach: krótszy szary nagłówek cen w DE/IT/EN, bo na telefonie dochodził do krawędzi
  zostało: odpowiedzi w pytaniach i nowe teksty DE/IT/EN napisałem sam (bez kwot i bez obietnic spoza strategii); tłumaczeń nie sprawdzała osoba mówiąca tymi językami od urodzenia
- [x] Strona: poprawki po sprawdzeniu zgodności ze strategią | kto: agent | gdzie: chmura | kiedy: 2026-11-26
  wykonawca: tylko claude
  wygląd: bez zmian
  cel: sprawdzenie 26.11 (build:panel z gałęzi nowa-koncepcja 4e2a302, zrzuty 390 i 1440 px, tekst stron PL/DE/IT/EN) pokazało, że zadanie „Strona: cała strona główna według nowej strategii…” jest tylko na gałęzi agent/2026-11-26-strona-cala-strona-glowna-wedlug-nowej-s (822e4e6), nie w nowa-koncepcja; wersja robocza nadal pokazuje stary cennik, listę ERP i kalkulator; gałąź 822e4e6 (sprawdzona tak samo) jest zgodna ze strategią
  gotowe gdy: w nowa-koncepcja (wersja robocza) na stronie głównej i 4 podstronach PL/DE/IT/EN nie ma kwot poza „0 zł”, listy systemów, kalkulatora ani WAPRO; „ERP” tylko w sekcji „Nie kupuj wielkiego ERP-a” na podstronie integracji; npm run build:panel przechodzi; zrzuty 390 i 1440 px obejrzane; wygląd bez zmian
  materiał: site/src/jezyki/
  materiał: site/src/Strona.jsx
  materiał: site/index.html
  - [x] Scal 822e4e6 do nowa-koncepcja (przed scaleniem sprawdź, czy nie działa agent strony); to usuwa wszystkie punkty poniżej poza ostatnim
  - [x] PL, DE, IT, EN, strona główna, „Oferta i ceny”: „Integracje … od 3 500 zł” (DE „ab 3 500 zł”, IT „da 3 500 zł”, EN „from 3,500 zł”) → „Ile to kosztuje”: wycena 0 zł, demo 0 zł, wdrożenie „stała cena po demie”, opieka „miesięczny ryczałt”
  - [x] PL, DE, IT, EN, strona główna, „To programy dla Ciebie” („Licencje Optimy, Subiekta…”) → „Najpierw widzisz, potem płacisz” (demo przed płatnością)
  - [x] PL, DE, IT, EN, podstrona integracji, cennik: „Integracja zamówień od 3 500 zł”, „Koniec przepisywania od 2 000 zł”, „Mały dodatek od 2 000 zł” → bez kwot, „Cenę podajemy w bezpłatnej wycenie”
  - [x] PL, DE, IT, EN, podstrona integracji, lista systemów („Comarch Optima, Subiekt, enova, WAPRO…”) → usunąć
  - [x] PL, DE, IT, EN, podstrona integracji, kalkulator „Policz sam: Przepisywanie zamówień…” (DE „Rechnen Sie selbst”, IT „Fai il conto”, EN „Do the maths”) z „od 3 500 zł” → usunąć
  - [x] PL, DE, IT, EN, stopka (wszystkie strony), znaki towarowe: „…enova, WAPRO, Microsoft Excel…” → bez WAPRO
  - [x] site/index.html: title „integracje ERP i małe automaty…”, opis „…z Subiektem, Optimą i WAPRO” → tytuł i opis bez ERP i WAPRO (jak w 822e4e6)
  - [x] PL, DE, IT, EN, strona główna, „Jak to działa”, przykładowa rozmowa: „Projekt: sklep ↔ magazyn” (DE „Shop ↔ Lager”, IT „negozio ↔ magazzino”, EN „shop ↔ warehouse”) → przykład z linii oferty, np. „Allegro ↔ Optima” albo planowanie produkcji
  poprawka: Poprzednie uruchomienie przerwał restart panelu (2026-11-26 21:33). Twoja dotychczasowa praca jest na gałęzi agent/2026-11-26-strona-poprawki-po-sprawdzeniu-zgodnosci: sprawdź ją (git log, git diff) i dokończ zadanie.
  wynik: do wersji roboczej trafiła cała treść z 822e4e6 (site/src/Strona.jsx, site/src/jezyki/tresc-pl.js, tresc-de.js, tresc-it.js, tresc-en.js, site/index.html): „Ile to kosztuje” z wyceną i demem za 0 zł, wdrożeniem „stała cena po demie” i opieką „miesięczny ryczałt”; sekcja „Najpierw widzisz, potem płacisz”; na podstronie integracji „Cenę podajemy w bezpłatnej wycenie” zamiast cennika, bez listy systemów i kalkulatora; stopka bez WAPRO; tytuł i opis bez ERP i WAPRO. Przykładowa rozmowa we wszystkich 4 językach to teraz „Allegro ↔ Optima”. Strona się buduje. Na wszystkich 20 stronach PL/DE/IT/EN jedyna kwota to „0 zł”, nie ma WAPRO ani kalkulatora, a „ERP” jest tylko w „Nie kupuj wielkiego ERP-a”. Obejrzałem zrzuty strony głównej i /pl/integracje w 390 i 1440 px: układ i styl bez zmian
  zmiany: poprzednia praca sprawdzona i dokończona: w porównaniu z 822e4e6 różni się tylko przykładowa rozmowa (8 wierszy); strona zbudowana i sprawdzona od nowa; poprawka: zrobione
  zostało: zrzuty obejrzane dla strony głównej (na zrzucie ładuje się wersja EN) i dla /pl/integracje; pozostałe języki i podstrony sprawdziłem w tekście zbudowanych stron, bez zrzutów
- [x] Strona: scal „4 rzeczy” z „4 krokami”, zmniejsz sekcję o raportach, usuń „Wszystko zostaje u Ciebie” | kto: agent | gdzie: chmura | kiedy: 2026-11-26
  wykonawca: tylko claude
  wygląd: bez zmian; te same komponenty i kolory, zmieniasz tylko treść i liczbę sekcji
  cel: uwagi właściciela po obejrzeniu nowej strony 26.11 (PL, DE, IT, EN): strona ma dwie podobne czwórki („4 rzeczy, które robimy” i „4 kroki”), co myli; sekcja „Zamiast raportów na 20 stron: jedna krótka wiadomość” jest za duża; zdanie „Wszystko zostaje u Ciebie” jest nieprawdziwe (program jest na licencji, decyzja w /home/panel/projekty/company-audits/DECYZJE.md) i już było omawiane; „Zanim zadzwonisz” i „Ile to kosztuje” zostają
  gotowe gdy: strona główna ma jedną sekcję z 4 krokami (wycena, demo, wdrożenie, opieka), a cztery linie oferty są w niej albo tuż nad nią jako krótkie kafelki z linkami do podstron, bez drugiego nagłówka z liczbą 4; sekcja o raportach skrócona do 2–3 zdań albo połączona z krokiem „wdrożenie/opieka”; w żadnym języku nie ma „Wszystko zostaje u Ciebie” ani innych obietnic, że program po zapłacie należy do klienta; wersja robocza buduje się (npm run build:panel); zrzuty całej strony głównej 390 i 1440 px w PL, DE, IT, EN obejrzane; w wynik: lista sekcji od góry do dołu (było → jest) i liczba słów strony głównej PL przed i po
  materiał: site/src/Strona.jsx
  materiał: site/src/jezyki/
  - [x] Połącz „4 rzeczy” i „4 kroki” w jedną sekcję; kafelki linii oferty zostają jako linki do podstron
  - [x] Skróć sekcję „Zamiast raportów na 20 stron” do 2–3 zdań albo włącz ją w krok opieki
  - [x] Usuń „Wszystko zostaje u Ciebie” i podobne obietnice własności we wszystkich językach; zamiast tego jedno prawdziwe zdanie zgodne z decyzją o licencji albo nic
  - [x] To samo w DE, IT, EN; zbuduj, zrób zrzuty całej strony, obejrzyj każdą sekcję, policz słowa
  wynik: strona główna PL/DE/IT/EN (site/src/Strona.jsx, site/src/jezyki/tresc-pl.js, tresc-de.js, tresc-it.js, tresc-en.js, site/src/strona.css). Było: Hero → „Oferta: Cztery rzeczy, które robimy” (4 kafelki) → „Jak to działa: Cztery kroki” + „Zamiast raportów na 20 stron: krótka wiadomość” z telefonem i przykładową rozmową → „Ile to kosztuje” → „Bez ryzyka: Najpierw widzisz, potem płacisz” (4 punkty, w tym „Wszystko zostaje u Ciebie”) → „Zanim zadzwonisz” → Kontakt → stopka. Jest: Hero → „Jak to działa: Od wyceny do opieki” (4 kroki: wycena, demo, wdrożenie, opieka; pod nimi „Co robimy” i 4 kafelki z linkami do podstron) → „Ile to kosztuje” → „Bez ryzyka” (4. punkt to teraz „Licencja na piśmie: Z programu korzystasz na licencji, a jej zasady spisujemy w umowie, zanim zaczniemy.”) → „Zanim zadzwonisz” → Kontakt → stopka. Z sekcji o raportach zostało jedno zdanie w kroku wdrożenia, a zdanie „Dzwonisz i odbiera Paweł albo Krystian” trafiło do kroku opieki. Z kroków usunąłem też „Pliki i dostępy od początku są u Ciebie” i „instrukcję i dostępy masz u siebie”. W żadnym języku nie ma już „Wszystko zostaje u Ciebie” (DE „Alles bleibt bei Ihnen”, IT „Tutto resta a te”, EN „Everything stays with you”) ani „program jest Twój”. Słowa strony głównej PL (treść główna razem z odpowiedziami w pytaniach, bez żółtych pól): ok. 871 przed → ok. 758 po. Strona się buduje. Zrzuty całej strony głównej 390 i 1440 px w PL, DE, IT, EN obejrzane: jest jedna sekcja z krokami, kafelki pod nimi, wygląd i kolory bez zmian
