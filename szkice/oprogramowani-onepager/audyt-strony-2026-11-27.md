# Audyt strony Oprogramowani: 3 rundy, 27.11.2026

## W skrócie
- **Wynik.** Strona przeszła 3 rundy audytu po 11 niezależnych ocen: 8 typów klientów i 3 ekspertów. Każda runda miała nowe subagenty, które dostawały tylko zrzuty, tekst i opis swojej osoby.
- **„Chęć kliknięcia »Bezpłatna wycena«”**, średnia:
  - wszystkie osoby: 4,9 → 5,3 → 5,2;
  - osoby a–g: 5,3 → 5,4 → 5,3.
- **Warunek wcześniejszego końca nie był spełniony w żadnej rundzie** (średnia ≥ 8, nikt z a–g poniżej 7, kontroler bez uwag). Zrobiłem 3 rundy, czyli maksimum. Kontroler rzetelności nie znalazł nic wymyślonego (klientów, opinii, kwot), ale do końca zgłaszał uwagi interpretacyjne (lista na dole).
- **Dlaczego wynik stoi na ok. 5–6.** Po rundzie 2 tekst przestał być przeszkodą. W rundzie 3 każda z osób a–g wymienia te same 4 blokery i żadnego z nich nie da się usunąć samym tekstem bez Twojej decyzji:
  1. brak jakiejkolwiek kwoty „od” (8 z 11 osób);
  2. brak dowodu: zrzutu tablicy, przykładowej wyceny, filmu, realizacji (wszyscy);
  3. „licencja” zamiast kodu i dostępów u klienta (sprzedawca, meble, księgowa, po ERP, sceptyk, kontroler);
  4. godziny rozmów pon–pt 15–19 czytane jako „robota po etacie” (prawie wszyscy).

  Pomysły z najwyższą średnią to właśnie te 4 sprawy: R15 „kod i dostępy zostają u Ciebie” 8,5; P12 ceny „od” 7,2; Q15 filmy po 60 s 7,1; R12 przykładowa wycena 7,0.
- **Firma IT (h)** we wszystkich rundach daje klik 2 i od razu rozumie, że strona nie jest dla niej: „bez stawki godzinowej”, brak stacku. Tak miało być.
- **Szalone pomysły na stronie: 0.** Żaden pomysł typu „sam tekst” nie miał średniej ≥ 7. Te z wysoką średnią wymagają pieniędzy, nowej obietnicy albo Twojego czasu, więc są na liście „do Twojej decyzji”.

## Jak to przebiegało
- **Krok 0.** Zadanie „Strona: zacznij od problemu klienta, każda obietnica raz” skończyło się [x] o 14:43. Jego gałąź nie była scalona, a panel zaczyna nowe zadania od `nowa-koncepcja`. Dlatego zadania rund 1 i 2 dostały pole `gałąź:` z tą gałęzią: poprawki się sumowały (decyzja w DECYZJE.md).
- **Scalanie.** O 15:24 panel sam scalił gałąź (praca z 27.11 + rundy 1 i 2) do `nowa-koncepcja`. Runda 3 poszła już zwykłą drogą i panel scalił ją o 15:37. Teraz `nowa-koncepcja` = b4763e4 i zawiera wszystko.
- **Dowiązania.** Panel zatwierdził przy tym jako „Zmiany niezatwierdzone w repozytorium” dowiązania do plików z IntegrateSystems (analizy, uwagi, specyfikacje rund). To te same dowiązania, które były w folderze projektu. Nic innego w nich nie ma.
- **Gdzie budowałem.** Każdą rundę budowałem w osobnym klonie (`/home/agent/rozwoj/strona-audyt/rN`, `npm run build:panel`) z zrzutami PL 390 i 1440 px strony głównej i 4 podstron. W repozytorium projektu nic nie edytowałem i nic nie wypychałem na GitHub ani na produkcję.
- **Wersja końcowa (b4763e4).**
  - `site/src/dane.js` bez zmian od stanu sprzed audytu (f72ae72).
  - Miejsca [UZUPEŁNIJ] są na miejscu.
  - „demo” na stronie głównej PL pada 1 raz (przed 27.11: 30).
  - DE i IT obejrzałem w tekście: ten sam sens, naturalnie.

## Oceny (1–10): 5 s = czy w 5 sekund wiem, co to jest; o mnie; zaufanie; klik = chęć kliknięcia „Bezpłatna wycena”

### Runda 1

| Osoba | 5 s | o mnie | zaufanie | klik |
|---|---|---|---|---|
| a: Sprzedawca Allegro (BaseLinker, Subiekt) | 6 | 5 | 5 | 6 |
| b: Właściciel zakładu meblowego | 8 | 6 | 4 | 6 |
| c: Kierownik produkcji | 6 | 4 | 5 | 4 |
| d: Księgowa / biuro (KSeF) | 6 | 4 | 6 | 5 |
| e: Po nieudanym ERP | 7 | 6 | 4 | 5 |
| f: Wycena integratora 3 mies. / 40 tys. | 7 | 8 | 5 | 7 |
| g: Sceptyk | 7 | 4 | 4 | 4 |
| h: Firma IT (szuka podwykonawcy) | 8 | 2 | 5 | 2 |
| X1: Copywriter | 6 | 5 | 4 | 5 |
| X2: SEO | 6 | 5 | 5 | 5 |
| X3: Kontroler rzetelności | 8 | 6 | 5 | 5 |

Średnia „klik”: wszyscy 4,9; osoby a–g 5,3; najniższa a–g 4.

### Runda 2

| Osoba | 5 s | o mnie | zaufanie | klik |
|---|---|---|---|---|
| a: Sprzedawca Allegro (BaseLinker, Subiekt) | 7 | 6 | 5 | 6 |
| b: Właściciel zakładu meblowego | 7 | 6 | 5 | 6 |
| c: Kierownik produkcji | 7 | 5 | 4 | 5 |
| d: Księgowa / biuro (KSeF) | 7 | 4 | 6 | 4 |
| e: Po nieudanym ERP | 8 | 7 | 5 | 6 |
| f: Wycena integratora 3 mies. / 40 tys. | 7 | 8 | 5 | 7 |
| g: Sceptyk | 7 | 4 | 5 | 4 |
| h: Firma IT (szuka podwykonawcy) | 8 | 2 | 4 | 2 |
| X1: Copywriter | 7 | 6 | 5 | 6 |
| X2: SEO | 7 | 6 | 5 | 6 |
| X3: Kontroler rzetelności | 8 | 6 | 5 | 6 |

Średnia „klik”: wszyscy 5,3; osoby a–g 5,4; najniższa a–g 4.

### Runda 3

| Osoba | 5 s | o mnie | zaufanie | klik |
|---|---|---|---|---|
| a: Sprzedawca Allegro (BaseLinker, Subiekt) | 7 | 6 | 5 | 6 |
| b: Właściciel zakładu meblowego | 8 | 6 | 5 | 6 |
| c: Kierownik produkcji | 6 | 5 | 5 | 5 |
| d: Księgowa / biuro (KSeF) | 7 | 4 | 5 | 4 |
| e: Po nieudanym ERP | 8 | 6 | 4 | 5 |
| f: Wycena integratora 3 mies. / 40 tys. | 7 | 8 | 5 | 7 |
| g: Sceptyk | 7 | 4 | 5 | 4 |
| h: Firma IT (szuka podwykonawcy) | 8 | 2 | 4 | 2 |
| X1: Copywriter | 7 | 6 | 4 | 6 |
| X2: SEO | 7 | 6 | 5 | 6 |
| X3: Kontroler rzetelności | 8 | 6 | 5 | 6 |

Średnia „klik”: wszyscy 5,2; osoby a–g 5,3; najniższa a–g 4.

### Zestawienie „klik”

| Osoba | R1 | R2 | R3 |
|---|---|---|---|
| a: Sprzedawca Allegro (BaseLinker, Subiekt) | 6 | 6 | 6 |
| b: Właściciel zakładu meblowego | 6 | 6 | 6 |
| c: Kierownik produkcji | 4 | 5 | 5 |
| d: Księgowa / biuro (KSeF) | 5 | 4 | 4 |
| e: Po nieudanym ERP | 5 | 6 | 5 |
| f: Wycena integratora 3 mies. / 40 tys. | 7 | 7 | 7 |
| g: Sceptyk | 4 | 4 | 4 |
| h: Firma IT (szuka podwykonawcy) | 2 | 2 | 2 |
| X1: Copywriter | 5 | 6 | 6 |
| X2: SEO | 5 | 6 | 6 |
| X3: Kontroler rzetelności | 5 | 6 | 6 |


## Co poprawiono w każdej rundzie
Zdania są w specyfikacjach strona-runda-N-2026-11-27.md. Każda zmiana jest w PL, DE, IT i EN.

**Runda 1** (zadanie „Strona: poprawki po audycie, runda 1…”, commit 6635798):
- **Paweł.** „Kim jest Paweł?” pytało 9 z 11 osób. W kontakcie jest teraz „Programy piszą Krystian i Paweł…” z nazwiskiem i formą współpracy z dane.js (dziś żółte [UZUPEŁNIJ]). Karta 04 mówi „dzwonisz do nas”.
- **Hero.**
  - Lead z nazwami programów: Allegro, BaseLinker, Subiekt, Optima, KSeF, Excel.
  - Pod przyciskiem nowa drobna linia o widełkach ceny w ciągu dnia roboczego.
- **Rzetelność.**
  - Warunek przy „1–2 dni”.
  - Na podstronach „Co zobaczysz przed decyzją” zamiast „Jak wygląda demo” (dla IT to plan, nie program).
  - Widełki zamiast „ceny w ciągu dnia”.
  - „Bez zobowiązań” raz.
  - „Bez ryzyka” usunięte (stało obok zaliczki).
  - Stopka bez „symulacji”.
- **Słowa klientów.**
  - Title i opis z integracją, Allegro, BaseLinkerem, Subiektem GT, Optimą i KSeF.
  - Kafelek „Integracje…”.
  - H1 podstrony integracji „Integracja Allegro i BaseLinkera z Subiektem GT, Optimą i KSeF”.
  - Planowanie z „stolarnią” i punktem o handlowcu, który sprawdza zlecenie na telefonie.
  - KSeF „do Optimy albo Subiekta i z powrotem”.
- **Ty i Twój ERP.** Zdanie „Masz już ERP? Też go nie ruszamy…” (dla właściciela po nieudanym wdrożeniu).

**Runda 2** (commit 0c6d0d6):
- **Codzienne problemy.** Pod „Brzmi znajomo?” zdanie o przepisywaniu z Allegro do Subiekta, kartce na hali i KSeF. Tak mówiło 6 z 11 osób: „4 karty to problemy z ERP i integratorem, nie mój dzień”. Twoje 4 chwyty zostały.
- **Cena.** „Jak ustalamy cenę.” zamiast „Ile to kosztuje.”. Nagłówek obiecywał kwotę, której nie ma (8 z 11 osób). „Ile to kosztuje.” wraca, gdy podasz kwoty „od”.
- **Kafelek integracji** łamał się na komputerze w linie zaczynające się od „·”. Teraz są przecinki. Excel: „Makra i automatyzacja Excela” (słowa z wyszukiwarki).
- **Mniej powtórzeń.**
  - „na piśmie” było 5 razy, teraz 2.
  - „Twoje programy zostają” było 4 razy z rzędu: teraz nadtytuł „Bez przesiadki”.
  - „połowa firmy” → „część firmy”.
  - „nie musimy Ci niczego sprzedawać” → „nie mamy interesu, żeby namawiać Cię na nowy system”.
- **Krystian.** „Krystian, nie handlowiec, oddzwoni…” przeniesione do hero.
- **Koszty innych firm.** Licencje i abonamenty innych firm są teraz też na głównej, nie tylko na podstronie.

**Runda 3** (commit e91e75a):
- Zdanie pod „Brzmi znajomo?” zaczyna się od „A może u Ciebie wygląda to tak…” zamiast urwanego „Albo prościej:”.
- Demo w cenniku: „Dotyczy programów, integracji i Excela”.
- Wdrożenie: abonament BaseLinkera albo moduł integracyjny Subiekta.
- Na podstronach „zwykle w ciągu dnia roboczego” i ten sam warunek „Gdy widełki ceny Ci pasują, w 1–2 dni…” co na głównej.

## Szalone pomysły i oceny (osoby a–h, 1–10)
Typ: TEKST oznacza, że da się to zrobić samym tekstem albo prostym elementem, bez nowej obietnicy. DECYZJA oznacza, że potrzebne są pieniądze, nowa obietnica, kwota, nagranie albo Twój czas. Na stronę mógł trafić pomysł typu TEKST ze średnią co najmniej 7. W żadnej rundzie nie było takiego pomysłu. Najbliżej były Q3 „Uczciwie o braku opinii” (6,5, a w osobach a–g 7,0) i P13 „Lista rzeczy, których nie zrobimy” (6,4).

### Pomysły rundy 1

| # | Pomysł | Typ | a | b | c | d | e | f | g | h | śr. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| P1 | **Mówimy słowami klienta**: „Nie potrzebujesz wdrożenia. Potrzebujesz, żeby Allegro, BaseLinker i Subiekt wreszcie się dogadały.” | TEKST | 9 | 3 | 3 | 5 | 7 | 8 | 5 | 2 | 5,2 |
| P2 | **Licznik „ile kosztowałby Cię ERP”**: suwaki stanowisk i modułów, szacunkowy koszt ERP obok kosztu jednego modułu u nas (wymaga publicznych kwot) | DECYZJA | 3 | 5 | 4 | 3 | 4 | 4 | 5 | 1 | 3,6 |
| P3 | **Kartka na hali to już system**: „Jeśli na hali wisi kartka z kolejnością zleceń, to już masz system. My go tylko przeniesiemy na ekran, żeby nikt go nie zgubił.” | TEKST | 2 | 9 | 9 | 2 | 5 | 2 | 3 | 1 | 4,1 |
| P4 | **„Rzuć nam najgłupszą wycenę integracji”**: „Ktoś Ci wycenił połączenie Allegro z Optimą jak budowę mostu? Przyślij ofertę. Pokażemy, ile to kosztuje u nas.” + co miesiąc anonimowa „Wycena miesiąca” | DECYZJA | 4 | 2 | 3 | 4 | 6 | 9 | 6 | 3 | 4,6 |
| P5 | **Słownik integratora**: żartobliwy słowniczek: „Analiza przedwdrożeniowa: jeszcze długo nic nie zobaczysz”, „Konsultant: osoba, której godzina kosztuje więcej niż Twój Excel” | TEKST | 3 | 3 | 4 | 4 | 6 | 5 | 4 | 3 | 4,0 |
| P6 | **Film „Kartka”**: 30 s: kartka zleceń spada/ginie, cięcie na tablet z tablicą zleceń. „Kartki giną. Tablica nie.” | DECYZJA | 2 | 6 | 8 | 2 | 3 | 2 | 2 | 1 | 3,2 |
| P7 | **Excel, którego nikt nie rusza**: „Masz w firmie plik, którego boi się nawet jego autor? Opisz go albo przyślij. W bezpłatnej wycenie powiemy, co da się zrobić, żeby liczył się sam.” | TEKST | 6 | 8 | 6 | 8 | 7 | 3 | 8 | 2 | 6,0 |
| P8 | **Konkurs „Najstarszy Excel w Polsce”**: autor najstarszego pliku dostaje darmowe makro; publiczna lista | DECYZJA | 3 | 2 | 3 | 3 | 3 | 1 | 3 | 1 | 2,4 |
| P9 | **Porównanie w dwóch kolumnach**: „U typowego integratora / U nas”: „3 miesiące, zanim coś zobaczysz / działający program w 1–2 dni po wycenie”, „stawka godzinowa / stała cena na piśmie”, „infolinia / telefon do Pawła albo Krystiana” | TEKST | 5 | 6 | 6 | 7 | 8 | 8 | 6 | 3 | 6,1 |
| P10 | **Tablica zleceń do przeklikania**: mała przykładowa tablica na stronie, przeciąganie zleceń | DECYZJA | 2 | 8 | 9 | 2 | 3 | 2 | 3 | 4 | 4,1 |
| P11 | **Nie wiesz, ile to ma kosztować? Normalne.**: „Nie wiesz, ile to ma kosztować? Większość nie wie. Od tego jest bezpłatna wycena.” | TEKST | 7 | 5 | 5 | 6 | 5 | 6 | 5 | 1 | 5,0 |
| P12 | **Ceny „od” dla najczęstszych połączeń**: karty „Allegro → Subiekt”, „BaseLinker → Optima”, „Faktury do KSeF” z ceną „od … zł netto” | DECYZJA | 10 | 4 | 4 | 9 | 8 | 10 | 9 | 4 | 7,2 |
| P13 | **Lista rzeczy, których nie zrobimy**: „Czego u nas nie będzie: Nie sprzedamy Ci licencji. Nie każemy zmieniać programu. Nie wyślemy konsultanta. Nie przełączymy Cię na infolinię.” | TEKST | 6 | 6 | 6 | 7 | 9 | 7 | 7 | 3 | 6,4 |
| P14 | **CRM, który nie udaje Salesforce'a**: nowa karta oferty: mały CRM w Excelu albo jako program | DECYZJA | 3 | 2 | 2 | 3 | 4 | 1 | 7 | 1 | 2,9 |
| P15 | **Wybierz swój program**: pod hasłem przyciski „Mam: Subiekt · Optima · BaseLinker · Allegro · KSeF · Excel” prowadzące do pasującej sekcji | TEKST | 8 | 4 | 3 | 8 | 5 | 7 | 4 | 3 | 5,2 |
| P16 | **Zakres zostaje u Ciebie**: „Demo Ci się nie spodobało? Nie płacisz nic, a spisany zakres zostaje u Ciebie.” | DECYZJA | 7 | 7 | 7 | 7 | 8 | 6 | 7 | 2 | 6,4 |
| P17 | **Gra słów w nazwie**: „Ktoś już Cię oprogramował na wielki system? My piszemy tylko to, czego Twoja firma naprawdę używa.” | TEKST | 4 | 3 | 4 | 4 | 5 | 5 | 4 | 2 | 3,9 |
| P18 | **Godzina na Twojej hali**: „Przyjedziemy na halę, popatrzymy, jak krążą zlecenia… bez opłat.” + kalendarz | DECYZJA | 3 | 8 | 10 | 3 | 7 | 4 | 3 | 1 | 4,9 |

### Pomysły rundy 2

| # | Pomysł | Typ | a | b | c | d | e | f | g | h | śr. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Q1 | **Kalkulator przepisywania**: 3 pola (ile zamówień/faktur dziennie przepisujecie, ile minut jedno, ile dni w miesiącu) → „Tyle godzin w miesiącu ktoś u Ciebie robi kopiuj-wklej.” Liczby wpisuje odwiedzający. | TEKST | 8 | 4 | 5 | 6 | 5 | 6 | 7 | 1 | 5,2 |
| Q2 | **Najlepszy pracownik: kopiuj-wklej**: „Twój najbardziej zapracowany pracownik nazywa się Ctrl+C. Pora dać mu wolne.” | TEKST | 5 | 2 | 3 | 3 | 3 | 4 | 3 | 1 | 3,0 |
| Q3 | **Uczciwie o braku opinii**: „Nie mamy jeszcze opinii do pokazania. Dlatego zanim zdecydujesz, pokazujemy działający program na przykładowych danych.” | TEKST | 7 | 7 | 6 | 7 | 7 | 7 | 8 | 3 | 6,5 |
| Q4 | **Gotowy mail do szefa**: blok „Musisz przekonać szefa?” + „Skopiuj wiadomość”: „Szefie, znalazłem firmę, która bezpłatnie wyceni… Najpierw podają widełki, a przed decyzją pokazują działający program. Cenę dają na piśmie, płacimy za odebrane etapy.” | TEKST | 3 | 1 | 9 | 5 | 2 | 2 | 2 | 1 | 3,1 |
| Q5 | **Kącik dla księgowej**: „Dla księgowości: faktury z Allegro i BaseLinkera same trafiają do Subiekta albo Optimy. Bez przepisywania numerów zamówień i bez szukania, czego brakuje.” | TEKST | 6 | 3 | 2 | 8 | 5 | 6 | 4 | 1 | 4,4 |
| Q6 | **KSeF bez klepania**: „KSeF już jest. A faktury dalej ktoś przepisuje ręcznie?” | TEKST | 6 | 3 | 2 | 9 | 6 | 5 | 5 | 2 | 4,8 |
| Q7 | **Podpowiedź w formularzu**: „Nie musisz znać słowa »integracja«. Napisz po swojemu, np. »Przepisujemy zamówienia z Allegro do Subiekta« albo »Kierownik planuje produkcję na kartce«.” | TEKST | 8 | 8 | 7 | 6 | 6 | 6 | 7 | 1 | 6,1 |
| Q8 | **Sobota dla szefa**: „W tygodniu nie masz czasu? Zadzwoń w sobotę między 8:00 a 16:00.” | TEKST | 6 | 7 | 6 | 4 | 4 | 7 | 6 | 2 | 5,2 |
| Q9 | **Poniedziałek, 7:40**: scenka: „Poniedziałek, 7:40. Na hali ktoś szuka kartki ze zleceniem. W biurze ktoś przepisuje zamówienia z weekendu. Księgowa pyta, gdzie jest faktura. Znasz to?” | TEKST | 4 | 6 | 8 | 5 | 4 | 4 | 5 | 1 | 4,6 |
| Q10 | **Kolejka po Black Friday**: „Szczyt minął, bałagan został. Zgłoś się do [data], a demo zobaczysz przed świętami.” | DECYZJA | 7 | 2 | 2 | 2 | 2 | 6 | 2 | 1 | 3,0 |
| Q11 | **Zdjęcie zamiast opisu**: „Nie chce Ci się pisać? Wyślij zdjęcie kartki z hali albo ekranu z Excela na WhatsApp/SMS.” | DECYZJA | 8 | 9 | 8 | 3 | 7 | 6 | 6 | 1 | 6,0 |
| Q12 | **Demo na Twoich danych**: „Wyślij eksport bez danych osobowych, a demo pokażemy na Twoich zamówieniach.” | DECYZJA | 6 | 8 | 7 | 6 | 9 | 8 | 8 | 3 | 6,9 |
| Q13 | **Kartka do powieszenia na hali**: PDF „Ile dziś przepisaliśmy?” – tabelka na tydzień do kreskowania | DECYZJA | 3 | 3 | 4 | 2 | 3 | 2 | 3 | 1 | 2,6 |
| Q14 | **Pierwsze firmy za opinię**: „Szukamy pierwszych [liczba] firm: niższa cena w zamian za opisanie wdrożenia i opinię.” | DECYZJA | 7 | 6 | 5 | 4 | 3 | 7 | 6 | 2 | 5,0 |
| Q15 | **Filmy po 60 sekund**: nagrania ekranu na przykładowych danych: „Zamówienie z Allegro wpada do Subiekta” | DECYZJA | 9 | 5 | 8 | 7 | 7 | 8 | 9 | 4 | 7,1 |
| Q16 | **Przegląd Excela za 0 zł**: „Przyślij swój arkusz, a odpiszemy, co da się w nim zrobić automatycznie.” | DECYZJA | 6 | 8 | 6 | 7 | 8 | 3 | 8 | 2 | 6,0 |

### Pomysły rundy 3

| # | Pomysł | Typ | a | b | c | d | e | f | g | h | śr. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| R1 | **Droga od telefonu do odbioru**: oś „Co się dzieje, gdy klikniesz”: piszesz/dzwonisz → Krystian oddzwania z widełkami → widełki pasują, widzisz działający program na przykładowych danych → stała cena i licencja na piśmie → płacisz za etap, gdy działa u Ciebie | TEKST | 6 | 7 | 7 | 7 | 7 | 7 | 6 | 2 | 6,1 |
| R2 | **Pytania, które warto zadać każdemu wykonawcy**: „Zanim kogokolwiek zatrudnisz (nas też), zapytaj: Czy cenę dostanę na piśmie przed startem? Kto odbierze, gdy coś przestanie działać? Czy zobaczę coś działającego, zanim zapłacę? Kto decyduje o zmianach w zakresie?” + krótkie odpowiedzi | TEKST | 4 | 4 | 4 | 6 | 8 | 9 | 7 | 2 | 5,5 |
| R3 | **Co powiedzieć, gdy zadzwonisz**: „Nie musisz się przygotowywać. Wystarczy powiedzieć: w jakich programach pracujecie, co ktoś robi ręcznie i kto to robi.” | TEKST | 8 | 8 | 8 | 6 | 5 | 6 | 6 | 1 | 6,0 |
| R4 | **„Teraz odbieramy”**: etykieta przy telefonie z godzin ze strony: „Teraz odbieramy” albo „Najbliższe rozmowy: dziś od 15:00” | TEKST | 6 | 5 | 5 | 4 | 3 | 5 | 4 | 3 | 4,4 |
| R5 | **Co dostajesz do ręki**: „Na każdym kroku masz coś konkretnego: widełki przez telefon, działający program na przykładowych danych, spisany zakres i stałą cenę, umowę z zasadami licencji, odbiór każdego etapu.” | TEKST | 5 | 6 | 6 | 7 | 6 | 6 | 6 | 2 | 5,5 |
| R6 | **Najgorszy scenariusz**: „Co najgorszego może się stać? Zadzwonisz, widełki nie będą Ci pasować i na tym koniec. Wycena i demo kosztują 0 zł.” | TEKST | 8 | 8 | 7 | 6 | 6 | 7 | 7 | 2 | 6,4 |
| R7 | **Dwie osoby, jeden numer**: „Dwie osoby. Jeden numer. Nikt Cię nigdzie nie przełączy, bo nie ma dokąd.” | TEKST | 7 | 6 | 5 | 3 | 4 | 6 | 5 | 3 | 4,9 |
| R8 | **Sprawdź nas, zanim zadzwonisz**: przy przycisku wyceny link „Sprawdź nas w CEIDG: NIP 6192067893” | TEKST | 4 | 6 | 4 | 8 | 5 | 6 | 7 | 5 | 5,6 |
| R9 | **Dziennik warsztatu**: „Nad czym siedzimy w tym tygodniu”: wpisy ze zrzutem z tego, co budują na danych testowych | DECYZJA | 5 | 3 | 8 | 4 | 3 | 6 | 7 | 6 | 5,2 |
| R10 | **Kawałek kodu na widoku**: link do publicznego repozytorium z przykładowym makrem albo skryptem | DECYZJA | 1 | 1 | 2 | 2 | 2 | 3 | 5 | 8 | 3,0 |
| R11 | **Darmowe małe narzędzie**: „Weź za darmo: arkusz, który sprawdza NIP-y kontrahentów na białej liście VAT” | DECYZJA | 6 | 2 | 2 | 8 | 4 | 4 | 6 | 3 | 4,4 |
| R12 | **Wypełniona wycena dla fikcyjnej firmy**: PDF „Tak wygląda nasza wycena” dla „Stolarni Przykładowej”, oznaczony jako przykład | DECYZJA | 7 | 7 | 7 | 7 | 8 | 9 | 8 | 3 | 7,0 |
| R13 | **Zadzwoń i sprawdź**: „Nie mamy jeszcze opinii. Mamy telefon. Zadzwoń w godzinach rozmów i sprawdź, czy odbierzemy.” | DECYZJA | 5 | 5 | 4 | 4 | 4 | 5 | 6 | 3 | 4,5 |
| R14 | **Głos Krystiana zamiast automatu**: „Jeśli nie odbierzemy, usłyszysz Krystiana, nie automat. Zostaw dwa zdania, a oddzwonimy.” | DECYZJA | 6 | 4 | 5 | 4 | 4 | 5 | 4 | 2 | 4,2 |
| R15 | **Kod i dostępy zostają u Ciebie**: „Gdybyśmy jutro zniknęli, Twój program działa dalej. Kod i hasła dostajesz przy odbiorze.” | DECYZJA | 8 | 9 | 8 | 9 | 10 | 9 | 9 | 6 | 8,5 |

## Do Twojej decyzji
Kolejność według tego, ile może dać, licząc oceny i to, jak często osoba sama o to prosiła w zdaniu „brakuje mi”. Przy każdym pomyśle jest zdanie, ile to kosztuje Ciebie.

**Najmocniejsze (to one stoją między 5–6 a 8):**
1. **Kod i dostępy zostają u klienta (R15, śr. 8,5; e: 10).** Zdanie „Gdybyśmy jutro zniknęli, Twój program działa dalej. Kod i hasła dostajesz przy odbiorze” zamiast samej „licencji”.
   - Koszt: zmiana zasad licencji z company-audits/DECYZJE.md i wzoru umowy. Oddajesz część kontroli nad kodem, ale nie płacisz pieniędzmi.
2. **Kwoty „od” (P12, śr. 7,2; sprzedawca i właściciel z wyceną 40 tys.: 10).** Np. „połączenie Allegro/BaseLinkera z Subiektem od … zł”, „tablica zleceń od … zł”, „makro od … zł”.
   - Do 26.11 strona miała Twoje kwoty: Integracja ERP od 3 500 zł, Koniec przepisywania od 2 000 zł, Mały automat od 2 000 zł. Wystarczy powiedzieć, które wracają.
   - Koszt: 15 minut i publiczne zobowiązanie do ceny minimalnej.
3. **Pokaz bez telefonu: filmy po 60 s albo zrzut tablicy (Q15, śr. 7,1; R9, śr. 5,2).** Np. „zamówienie z Allegro wpada do Subiekta”, „zlecenie przechodzi na następny etap”. Kierownik produkcji i właściciel stolarni proszą wprost: „pokażcie tablicę”.
   - Koszt: kilka godzin na nagranie i montaż każdego filmu, albo jedno popołudnie na zrzuty z przykładowymi danymi.
4. **Przykładowa wycena PDF dla fikcyjnej „Stolarni Przykładowej” albo sklepu (R12, śr. 7,0).**
   - Koszt: jedno popołudnie. Wymaga kwot, więc idzie razem z punktem 2.
5. **Godziny rozmów pon–pt 15–19.** 8 z 11 osób czyta je jako „praca po etacie”.
   - Jeśli możesz dodać choć jedno okno rano albo krótkie wyjaśnienie, to sama zmiana danych.
   - Koszt: Twój czas w ciągu dnia albo jedno zdanie wyjaśnienia.
6. **Paweł: nazwisko i forma współpracy w dane.js.** Dziś na stronie „Paweł [UZUPEŁNIJ]”.
   - Koszt: 5 minut.
7. **Czas reakcji na awarię, godziny zgłoszeń, dni poprawek, kara za opóźnienie.** Kontroler: „najmocniejsze gwarancje są puste”. W produkcji te zdania znikają, gdy pól nie ma, więc strona traci najmocniejsze argumenty.
   - Koszt: 15 minut i zobowiązanie, którego trzeba dotrzymywać.

**Pozostałe pomysły typu DECYZJA (śr. ocen a–h, koszt dla Ciebie):**
- **Q12 Demo na danych klienta (6,9).** Więcej pracy przy każdym pokazie i trzeba spisać zasady obchodzenia się z eksportem.
- **P16 Zakres zostaje u Ciebie, gdy demo się nie spodoba (6,4).** Darmowa praca nad zakresem może trafić do konkurencji.
- **Q11 Zdjęcie kartki albo ekranu na WhatsApp/SMS (6,0).** Nowy kanał, który trzeba codziennie sprawdzać. Księgowa: „dane klientów na WhatsApp to sygnał ostrzegawczy”.
- **Q16 Darmowy przegląd arkusza Excel (6,0).** Czas na każdy plik, także od tych, którzy nic nie zamówią.
- **Q14 Pierwsze firmy taniej za zgodę na opis i opinię (5,0).** Niższy zarobek na pierwszych zleceniach i trzeba ustalić rabat. Część osób czyta to jako „królik doświadczalny”.
- **R13 „Nie mamy opinii. Zadzwoń i sprawdź, czy odbierzemy” (4,5).** Każde nieodebrane połączenie w godzinach przekreśla hasło.
- **R11 Darmowy arkusz do sprawdzania NIP-ów na białej liście (4,4; księgowa: 8).** Zbudowanie i utrzymanie małego narzędzia.
- **R14 Poczta głosowa nagrana przez Krystiana (4,2).** Nagranie i oddzwanianie na każdą wiadomość.
- **R10 Publiczne repozytorium z przykładowym kodem (3,0; firma IT: 8).** Przygotowanie dopracowanego przykładu. Przyciąga raczej podwykonawców niż klientów.
- **P18 Godzina na hali bez opłat (4,9; kierownik: 10, meble: 8).** Dojazdy i czas odebrany projektom.
- **P4 „Przyślij wycenę od innego integratora” (4,6; właściciel z wyceną 40 tys.: 9, sam prosi o to zdaniem „brakuje mi”).** Czas na analizę cudzych ofert. Wersja bez „Wyceny miesiąca” (anonimowego zestawienia) nie niesie ryzyka sporu.
- **P10 Klikalna tablica zleceń na stronie (4,1; kierownik: 9, meble: 8).** Kilka dni pracy i testy na telefonach.
- **P6 Film „Kartka” z hali (3,2).** Dzień nagrań, montaż i zgoda zakładu.
- **P2 Licznik „ile kosztowałby Cię ERP” (3,6).** Trzeba bronić publicznych kwot rynkowych.
- **P14 Mały CRM w ofercie (2,9; sceptyk: 7).** Nowa usługa. SEO zauważa, że „CRM” to 1240 zleceń na Useme, a na stronie nie pada ani razu.
- **Q10 Baner „po Black Friday” z terminem (3,0).** Termin, którego trzeba dotrzymać w sezonie.
- **Q13 Kartka „Ile dziś przepisaliśmy?” do druku (2,6).** Projekt pliku.
- **P8 Konkurs „Najstarszy Excel” (2,4).** Regulamin, darmowa praca i cudze dane osobowe.
- **R9 Dziennik warsztatu ze zrzutami (5,2).** Jeden wpis co 1–2 tygodnie.

**Pomysły typu TEKST, które możesz po prostu zatwierdzić** (nie przeszły progu 7, więc nie weszły bez Ciebie):
- Q3 „Nie mamy jeszcze opinii do pokazania. Dlatego zanim zdecydujesz, pokazujemy działający program…” (6,5; osoby a–g 7,0).
- P13 „Czego u nas nie będzie: licencji do kupienia, konsultanta, infolinii” (6,4).
- R6 „Co najgorszego może się stać? Zadzwonisz, widełki nie będą pasować i na tym koniec” (6,4).
- R1 „Co się dzieje, gdy klikniesz”: 5 kroków (6,1).
- Q7 podpowiedź w formularzu „Napisz po swojemu, np. »Przepisujemy zamówienia z Allegro do Subiekta«” (6,1).
- R3 „Nie musisz się przygotowywać…” (6,0).

Koszt każdego: nic poza zgodą, bo zdania opierają się na tym, co strona już obiecuje.

**Zgłosili eksperci i osoby, wymaga decyzji o ofercie:**
- Osobne podstrony „CRM dla małej firmy”, „program magazynowy” i „Integracja KSeF” (SEO).
- Słowa o bezpieczeństwie danych i umowie powierzenia dla biur rachunkowych (księgowa).
- Kryterium „etap działa” i wzór protokołu odbioru (kontroler; blok dokumentów to dziś [UZUPEŁNIJ]).

## Uwagi kontrolera rzetelności na wersji końcowej (b4763e4)
Nic nie jest wymyślone. Zostały uwagi interpretacyjne, które proponuję rozstrzygnąć razem z decyzjami wyżej:
1. **Karta 02** zestawia „3 miesiące” wdrożenia u konkurencji z „1–2 dni” pokazu. Własny termin wdrożenia jest tylko w wycenie. Lepsza odpowiedź będzie możliwa, gdy podasz typowy czas wdrożenia albo kwoty.
2. **„Potem dzwonisz do nas, nie na infolinię”** stoi bez czasu reakcji i godzin awarii (pola [UZUPEŁNIJ]).
3. **„Robimy tylko to, czego potrzebujesz, za stałą cenę”** stoi bez dopisku „dla spisanego zakresu”. Zastrzeżenie jest dopiero w cenniku.
4. **„0 zł” przy Demo** w cenniku nie ma warunku „gdy widełki pasują”, który stoi w karcie 02.
5. **„Bez przesiadki: nie uczysz ludzi wszystkiego od nowa”** a tablica zleceń to jednak nowy ekran dla hali.
6. **Godziny rozmów 15–19** a przykładowe godziny awarii 8–16 (gdy je wpiszesz, warto je zgrać).

Punkty 3–5 można poprawić samym tekstem w jednym krótkim zadaniu. Nie zakładałem go, bo limit to 3 rundy.

## Pliki
- **Specyfikacje rund** (dowiązane w folderze projektu):
  - strona-runda-1-2026-11-27.md
  - strona-runda-2-2026-11-27.md
  - strona-runda-3-2026-11-27.md
- **Zadania w ZADANIA.md:** „Strona: poprawki po audycie, runda 1/2/3”, wszystkie [x] i scalone.
- **Pełne odpowiedzi każdej osoby** (irytuje, brakuje, uzasadnienie, oceny pomysłów): /home/agent/rozwoj/strona-audyt/wyniki-rund/rN-*.md
- **Zrzuty i teksty każdej rundy:** /home/agent/rozwoj/strona-audyt/rN/audyt/ (r4 to wersja końcowa).
