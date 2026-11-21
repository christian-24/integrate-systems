# Zadania: Oprogramowani (integracje ERP ↔ sprzedaż)

> Jedyna lista zadań projektu. Czyta ją panel i agenci.
> Wiersz: `- [ ] Tytuł | kto: claude | gdzie: pc | kiedy: RRRR-MM-DD | pora: noc | czas: 30 | wymaga: zgoda`
> Stany: `[ ]` do zrobienia, `[~]` w toku, `[!]` zablokowane (dodaj `blokada: powód`), `[x]` zrobione.
> Pola są opcjonalne. kto: claude, codex, ty. gdzie: pc, mac, chmura. pora: dzień, noc. czas: minuty Twojej pracy. wymaga: zgoda, odbiór.
> Etap to nagłówek `## Etap: nazwa` i wiersz `termin: RRRR-MM-DD` pod nim. Etap bez otwartych zadań jest zamknięty.
> Szczegóły zadania: wcięte wiersze pod zadaniem (cel:, gotowe gdy:, materiał:, kroki `- [ ]`, wynik:, decyzja:, zostało:).

> Uzupełnione danymi z PC (audyt 2026-11-14). `[x]` tylko dla rzeczy widocznych w plikach lub dokumentach.

## Etap: Narzędzia i wiedza

- [x] Biblioteka wiedzy: research, branża, uzasadnienia, walidacja
- [x] Narzędzie audytu z backendem i raportem PDF
- [x] Lokalny model AI w audycie (propozycje, gotowość, analiza)
- [x] Dokumentacja systemu śledzenia zleceń (scanner/)
- [ ] Znajdź przyczynę błędu 502 w ocenie gotowości AI | kto: claude | gdzie: mac
  cel: ocena gotowości w narzędziu audytu zwraca wynik zamiast błędu 502
  gotowe gdy: ocena gotowości na przykładowym kwestionariuszu kończy się wynikiem, albo w wynik: opisana przyczyna i poprawka
  materiał: KARTA.md#Zasoby i ograniczenia
  Model lokalnie przez Ollamę na Macu (qwen3:14b), backend na localhost:5050; dlatego zadanie zostaje na Macu.

## Etap: Założenie firmy

- [x] Projekty umowy wspólników, NDA z klientem, umowy o dzieło i wdrożeniowej
- [x] Zgoda pracodawcy na działalność (dokument z 2026-10-27)
- [x] Forma działalności: JDG + umowa o dzieło, sp. z o.o. później (D09, 2026-11-14)
- [x] Nazwa marki: Oprogramowani (strategia 2026-08-24)

## Etap: Walidacja rynku
termin: 2026-12-18

- [x] Lista firm z danych publicznych: LeadyV2 ocenił 145 firm meblarskich (2026-09-02)
- [ ] Podłącz dysk z kopią PC do Maca (folder Reaserch) | kto: ty | gdzie: mac | kiedy: 2026-11-20 | czas: 2
  cel: lista LeadyV2 trafia na serwer, żeby agent wybrał 10 firm
  gotowe gdy: dysk z folderem Migracja-PC-2026-11 jest podłączony do Maca, a Claude wgrał folder Reaserch na serwer
  Podłącz dysk i napisz w rozmowie z Claude: „dysk podłączony”. Wgranie (bez plików .env i kluczy) i commit robi Claude.
- [ ] Wybierz 10 firm z listy LeadyV2 i przygotuj szkice wiadomości | kto: claude | gdzie: chmura | kiedy: 2026-11-21 | po: Podłącz dysk z kopią PC do Maca
  cel: 10 firm z listy LeadyV2 do pierwszego kontaktu, każda z uzasadnieniem wyboru i szkicem wiadomości
  gotowe gdy: w repozytorium projektu plik z 10 firmami (nazwa, powód wyboru, szkic pierwszej wiadomości); nic nie wysłane
  materiał: Reaserch/LeadyV2
  materiał: KARTA.md#Cel
  materiał: kampanie/pozyskanie-klientow.md
  materiał: KARTA.md#Zasady pracy agentów
  Reaserch/LeadyV2: folder powstanie w repozytorium w zadaniu „Wgraj folder Reaserch (LeadyV2) na serwer” (po:); dziś jest tylko na dysku zewnętrznym, Migracja-PC-2026-11/projekty/Reaserch.
  Zaczyna się po wgraniu folderu Reaserch na serwer (20.11). Gdy listy nadal nie ma w Reaserch/, agent oznacza [!] z blokadą „brak listy LeadyV2 na serwerze”.
  Wiadomość bez ceny; kontakt z firmami zatwierdzony 2026-11-14, wysyłka tylko przez właściciela.
- [ ] Napisz do 10 wybranych firm z listy LeadyV2 | kto: ty | kiedy: 2026-11-25 | czas: 30 | po: Wybierz 10 firm z listy LeadyV2
  cel: pierwsza wiadomość do 10 firm wysłana nowym kanałem właściciela
  gotowe gdy: 10 firm dostało pierwszą wiadomość bez ceny; data i kanał zapisane w notatce pod tym zadaniem
  materiał: KARTA.md#Zasady pracy agentów
  materiał: kampanie/pozyskanie-klientow.md
  Szkice: wynik zadania „Wybierz 10 firm z listy LeadyV2 i przygotuj szkice wiadomości” (panel dopisze plik jako materiał). Oferta z ceną wymaga osobnej zgody.
  Termin 25.11: 4 dni po wyborze firm (21.11), zapas na wgranie listy i przegląd szkiców.
- [ ] Przeprowadź rozmowy z firmami, które odpisały | kto: ty | kiedy: 2026-12-01 | czas: 60 | po: Napisz do 10 wybranych firm | licznik: rozmowy
  cel: z każdą firmą, która odpisała, rozmowa o potrzebie integracji ERP ↔ sprzedaż albo jasna odmowa
  gotowe gdy: każda firma, która odpisała, ma rozmowę za sobą albo odmowę; pod zadaniem po jednej notatce na rozmowę (klient N: potrzeba, ERP, kanały sprzedaży), bez nazwisk
  materiał: KARTA.md#Poza zakresem
  Licznik: liczba przeprowadzonych rozmów. Bez podawania cen na pierwszym spotkaniu (KARTA.md, Poza zakresem).
- [ ] Przygotuj szkice ofert dla firm po rozmowie | kto: claude | gdzie: chmura | kiedy: 2026-12-02 | po: Przeprowadź rozmowy z firmami
  cel: dla każdej firmy po rozmowie gotowy szkic oferty: audyt procesów jako pierwszy krok, zakres i cena
  gotowe gdy: w repozytorium projektu plik oferty dla każdej firmy z notatek pod zadaniem „Przeprowadź rozmowy…” (klient N); cena wyliczona wzorem z godzin i stawki z karty; nic nie wysłane
  materiał: KARTA.md#Zasoby i ograniczenia
  materiał: KARTA.md#Zasady pracy agentów
  Kwot nie wymyśla model: godziny × stawka 220 zł/h netto, rabat dla pierwszych firm według karty; zakres bez pozycji z „Poza zakresem”.
- [ ] Wyślij oferty firmom po rozmowie | kto: ty | kiedy: 2026-12-04 | czas: 30 | po: Przygotuj szkice ofert dla firm po rozmowie | licznik: oferty
  cel: każda firma po rozmowie dostała ofertę z ceną
  gotowe gdy: każda firma z notatek rozmów dostała ofertę albo w notatce powód, dlaczego nie
  materiał: kampanie/pozyskanie-klientow.md
  Licznik: liczba wysłanych ofert. Oferta z ceną to Twoja decyzja; wysyłasz sam.
- [x] Oferta na Useme: 2500 zł, 7 dni (bez odpowiedzi do 14.11)
- [x] Asystent Useme na serwerze: usługa, 188 testów, bez automatycznej wysyłki i komentarzy (2026-11-17)
- [x] Hasło do panelu zleceń: `ssh -t ops@2.29.181.133 sudo ustaw-haslo-zlecen` | kto: ty | czas: 2
- [ ] Zapisz przykładowy e-mail Useme o nowym zleceniu w repozytorium asystenta | kto: ty | czas: 5
  cel: agent ma wzór e-maila do napisania odczytu zleceń
  gotowe gdy: plik .eml z jednym e-mailem Useme o nowym zleceniu leży w repozytorium asystent-useme (np. w danych testowych)
  Przed zapisaniem usuń dane osobowe i linki z tokenami logowania.
- [ ] Napisz odczyt e-maili Useme na serwerze, który przekazuje zlecenia asystentowi | kto: claude | gdzie: chmura | po: Zapisz przykładowy e-mail Useme
  cel: nowe zlecenie z e-maila Useme trafia do asystenta bez ręcznego kopiowania
  gotowe gdy: test na przykładowym e-mailu przechodzi, a zlecenie pojawia się w kolejce asystenta; usługa niewdrożona bez zgody
  materiał: KARTA.md#Zakres
  Czeka na przykładowy e-mail od właściciela. Asystent działa bez automatycznej wysyłki ofert i komentarzy.
- [ ] Dodaj powiadomienie ntfy o nowym zleceniu z Useme | kto: claude | gdzie: chmura | po: Napisz odczyt e-maili Useme
  cel: właściciel dostaje powiadomienie ntfy, gdy odczyt e-maili znajdzie nowe zlecenie
  gotowe gdy: test wysyła jedno powiadomienie na każde nowe zlecenie i żadnego na powtórzone
  materiał: KARTA.md#Zakres
- [ ] Przenieś historię zleceń (data/jobs.db) z kopii PC na serwer | kto: claude | gdzie: chmura
  cel: historia zleceń z PC dostępna asystentowi Useme na serwerze
  gotowe gdy: data/jobs.db na serwerze ma tyle samo zleceń co kopia z PC; asystent czyta ją bez błędów
  materiał: KARTA.md#Zasady pracy agentów
  Migracja danych wymaga zgody właściciela. Jeśli pliku z kopii PC nie ma na serwerze, oznacz [!] z blokadą.
- [ ] Podsumuj skuteczność asystenta Useme | kto: claude | gdzie: chmura
  cel: wiadomo, ile ofert wysłano, ile dostało odpowiedź i dlaczego zlecenia odrzucano
  gotowe gdy: w wynik: liczby dla każdego kroku i jedno zdanie wniosku
  - [ ] wysłane oferty
  - [ ] odpowiedzi na oferty
  - [ ] odrzucone zlecenia i powody
  Liczy z data/jobs.db; bez historii z PC wynik obejmie tylko zlecenia z serwera.

## Etap: Pilotaż u klienta 1

- [x] Narada nad MVP śledzenia zleceń i lista pytań do firmy

## Do rozplanowania

- [x] Zebrać nowsze materiały z PC (audyt 2026-11-14)
- [x] Zacommitować nieśledzone pliki w CompanyAudits (commit „wip: migracja z PC”, 2026-11-16)
- [x] Część Useme w osobnym repozytorium asystent-useme (2026-11-16)
- [x] Strona oprogramowani.com, nowa wersja (2026-11-04)
- [x] Zaproponuj formy marketingu Oprogramowani na grudzień (poza Reels) | kto: claude | gdzie: chmura | kiedy: 2026-11-19
  cel: 3–5 form marketingu dopasowanych do grupy docelowej, każda z przykładem i rytmem, gotowe do wpisania na oś czasu
  gotowe gdy: plik marketing/formy-grudzien.md w folderze karty: dla każdej formy kanał, dla kogo, przykład tematu, częstotliwość, nakład pracy i czy film robi studio (pokaz albo objaśnienie); rekomendacja 3 form na start
  materiał: KARTA.md
  wynik: powstał marketing/formy-grudzien.md (folder karty): 5 form (bezpłatny przegląd drogi zamówienia, pokaz integracji z jednostronicowym opisem, seria na LinkedIn „Gdzie ginie zamówienie”, list papierowy, grupy na Facebooku), każda z kanałem, odbiorcą, przykładem tematu, częstotliwością, nakładem pracy i filmem ze studia (pokaz albo objaśnienie); rekomendacja na start: przegląd, pokaz integracji, seria na LinkedIn; 4 warianty z kosztem i oś czasu 24.11–18.12; pytania 6 i 7 w KARTA.md
  decyzja: które formy wchodzą na grudzień (propozycja: A, B, C; pytanie 6 w KARTA.md) i czy jest demo integracji do nagrania (pytanie 7)
  następne: Przygotuj arkusz i wzór notatki bezpłatnego przeglądu drogi zamówienia | kto: claude | kiedy: 2026-11-24
- [ ] Przygotuj arkusz i wzór notatki bezpłatnego przeglądu drogi zamówienia | kto: claude | gdzie: chmura | kiedy: 2026-11-24
  z pytania 6, 2026-11-21
- [ ] Przygotuj scenariusz filmu i jednostronicowy opis pokazu integracji | kto: claude | gdzie: chmura | kiedy: 2026-11-27
  z pytania 6, 2026-11-21
- [ ] Przygotuj 3 wpisy serii „Gdzie ginie zamówienie” (1–8.12) i scenariusz filmu objaśniającego | kto: claude | gdzie: chmura | kiedy: 2026-11-30
  z pytania 6, 2026-11-21
- [ ] Przyjmij film i opis pokazu integracji | kto: ty | kiedy: 2026-12-02 | czas: 45
  z pytania 6, 2026-11-21
- [ ] Przygotuj 3 wpisy serii „Gdzie ginie zamówienie” (10–17.12) z surowca po rozmowach | kto: claude | gdzie: chmura | kiedy: 2026-12-07
  z pytania 6, 2026-11-21
- [ ] Przygotuj arkusz i wzór notatki bezpłatnego przeglądu drogi zamówienia | kto: claude | kiedy: 2026-11-24
- [ ] Porządki spraw właściciela: pytania w karcie i Twoje zadania | kto: claude | gdzie: chmura | kiedy: 2026-11-21
  cel: zostawić właścicielowi tylko sprawy, których nie rozstrzygnie nikt inny (pieniądze, dane prawne i firmowe, działania nieodwracalne albo na zewnątrz, zakres i terminy, rzeczy fizyczne, fakty znane tylko jemu); w tym zadaniu wolno zmieniać inne wiersze ZADANIA.md (bez terminów i tytułów) i dopisywać odpowiedzi w KARTA.md
  - [ ] Pytania w „Pytania do właściciela”: każde, które rozstrzygniesz sam albo sprawdzisz w plikach i repozytorium, opatrz wierszem `   Odpowiedź: … (agent, DECYZJE.md)` i zapisz decyzję w DECYZJE.md z `- Kto: agent`; powtórzone pytanie połącz z pierwszym
  - [ ] Zadania kto: ty: te, które może zrobić agent, przepisz na kto: claude; zbędne i zdublowane zamknij `[x]` z `wynik: zamknięte przy porządkach 2026-11-21 (powód)`; podobne połącz w jedno
  - [ ] Odbiory prac wewnętrznych bez `decyzja:` i bez kodu do scalenia zamknij `[x]`
  - [ ] Zostaw najwyżej jedno pytanie bez odpowiedzi; pozostałe sprawy właściciela muszą być zadaniami kto: ty z czasem w minutach
  gotowe gdy: w KARTA.md najwyżej jedno pytanie bez odpowiedzi, każda decyzja agenta ma wpis w DECYZJE.md, a w wyniku jest lista zmian: ile pytań rozstrzygnięto, ile zadań przekazano agentom, ile zamknięto, co zostało właścicielowi
  - [ ] Na koniec stan `[~]`, `wymaga: odbiór` i `decyzja: przyjęcie porządków` z listą zmian w `wynik:`
  materiał: KARTA.md#Pytania do właściciela
