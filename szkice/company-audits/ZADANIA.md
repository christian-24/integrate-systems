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
  Reaserch/LeadyV2: folder powstanie w repozytorium w zadaniu „Podłącz dysk z kopią PC do Maca (folder Reaserch)” (po:); dziś jest tylko na dysku zewnętrznym, Migracja-PC-2026-11/projekty/Reaserch.
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
  Wystarczy, że wkleisz treść e-maila (albo plik .eml) w rozmowie z Claude. Dane osobowe i linki z tokenami logowania usuwa agent i to on zapisuje plik w repozytorium (porządki 2026-11-21).
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
- [~] Przygotuj arkusz i wzór notatki bezpłatnego przeglądu drogi zamówienia | kto: claude | gdzie: chmura | kiedy: 2026-11-24 | wymaga: odbiór
  z pytania 6, 2026-11-21
  wynik: powstał folder przeglad-zamowienia/: arkusz rozmowy na 30 minut (przeglad-zamowienia/arkusz-rozmowy.pdf, 2 strony A4: 8 pytań z dopytaniami, rysunek sześciu przystanków zamówienia, wzór na godziny przepisywania, zamknięcie i lista „czego nie robię”); notatka dla firmy do wypełnienia w przeglądarce (przeglad-zamowienia/notatka.html: klikasz w tekst, zaznaczasz przystanki z ręcznym przepisywaniem, godziny liczy wzór, przycisk zapisuje PDF); pusty wzór (przeglad-zamowienia/notatka-wzor.pdf) i przykład na zmyślonych danych (przeglad-zamowienia/notatka-przyklad.pdf); teksty (przeglad-zamowienia/teksty.md): zdanie do pierwszej wiadomości w dwóch wersjach, odpowiedź na „o co chodzi?”, wpis na LinkedIn, wiadomość z notatką. Nic nie zostało wysłane ani opublikowane.
  decyzja: czy arkusz, wzór notatki i teksty idą w tej postaci do wiadomości z 25.11 i na rozmowy; do potwierdzenia zwłaszcza zdanie „Co dalej” w notatce (audyt procesów jako następny krok, bez ceny), podpis Krystiana z numerem 663 206 373 i obietnica „notatka w dwa dni”
  zostało: wypełniania notatki w przeglądarce (klikanie w pola, zaznaczanie przystanków, zapamiętywanie treści, przycisk PDF) nie sprawdziłem ręcznie; sprawdzony jest wygląd pustego wzoru i przykładu oraz wynik wzoru w przykładzie (75 × 16 min = 20 godzin); arkusz nie był wypróbowany w rozmowie, więc 8 pytań w 30 minut to założenie; pliki złożone krojem zastępczym, bo krojów strony nie ma na serwerze; w wpisie na LinkedIn „cztery razy” i „dzień pracy” to obraz z biblioteki wiedzy, nie nasz pomiar
- [ ] Przygotuj scenariusz filmu i jednostronicowy opis pokazu integracji | kto: claude | gdzie: chmura | kiedy: 2026-11-27
  z pytania 6, 2026-11-21
- [ ] Przygotuj 3 wpisy serii „Gdzie ginie zamówienie” (1–8.12) i scenariusz filmu objaśniającego | kto: claude | gdzie: chmura | kiedy: 2026-11-30
  z pytania 6, 2026-11-21
- [ ] Przyjmij film i opis pokazu integracji | kto: ty | kiedy: 2026-12-02 | czas: 45
  z pytania 6, 2026-11-21
- [ ] Przygotuj 3 wpisy serii „Gdzie ginie zamówienie” (10–17.12) z surowca po rozmowach | kto: claude | gdzie: chmura | kiedy: 2026-12-07
  z pytania 6, 2026-11-21
- [x] Przygotuj arkusz i wzór notatki bezpłatnego przeglądu drogi zamówienia | kto: claude | kiedy: 2026-11-24
  wynik: zamknięte przy porządkach 2026-11-21 (duplikat: to samo zadanie jest wyżej, z pytania 6, z polem gdzie: chmura)
- [~] Porządki spraw właściciela: pytania w karcie i Twoje zadania | kto: claude | gdzie: chmura | kiedy: 2026-11-21 | wymaga: odbiór
  cel: zostawić właścicielowi tylko sprawy, których nie rozstrzygnie nikt inny (pieniądze, dane prawne i firmowe, działania nieodwracalne albo na zewnątrz, zakres i terminy, rzeczy fizyczne, fakty znane tylko jemu); w tym zadaniu wolno zmieniać inne wiersze ZADANIA.md (bez terminów i tytułów) i dopisywać odpowiedzi w KARTA.md
  - [x] Pytania w „Pytania do właściciela”: każde, które rozstrzygniesz sam albo sprawdzisz w plikach i repozytorium, opatrz wierszem `   Odpowiedź: … (agent, DECYZJE.md)` i zapisz decyzję w DECYZJE.md z `- Kto: agent`; powtórzone pytanie połącz z pierwszym
  - [x] Zadania kto: ty: te, które może zrobić agent, przepisz na kto: claude; zbędne i zdublowane zamknij `[x]` z `wynik: zamknięte przy porządkach 2026-11-21 (powód)`; podobne połącz w jedno
  - [x] Odbiory prac wewnętrznych bez `decyzja:` i bez kodu do scalenia zamknij `[x]`
  - [x] Zostaw najwyżej jedno pytanie bez odpowiedzi; pozostałe sprawy właściciela muszą być zadaniami kto: ty z czasem w minutach
  gotowe gdy: w KARTA.md najwyżej jedno pytanie bez odpowiedzi, każda decyzja agenta ma wpis w DECYZJE.md, a w wyniku jest lista zmian: ile pytań rozstrzygnięto, ile zadań przekazano agentom, ile zamknięto, co zostało właścicielowi
  - [x] Na koniec stan `[~]`, `wymaga: odbiór` i `decyzja: przyjęcie porządków` z listą zmian w `wynik:`
  materiał: KARTA.md#Pytania do właściciela
  wynik: pytania rozstrzygnięte przez agenta: 0 (wszystkie 7 miało już Twoją odpowiedź, powtórzeń nie było); zadania przekazane agentom: 0 w całości, 1 częściowo (przy „Zapisz przykładowy e-mail Useme…” tylko przekazujesz e-mail, resztę robi agent); zamknięte: 1 (duplikat „Przygotuj arkusz i wzór notatki…”); odbiory prac wewnętrznych do zamknięcia: 0; poprawiona notatka w „Wybierz 10 firm…”. Zostało Tobie 6 zadań, razem 172 min: podłączenie dysku (2), e-mail Useme (5), wiadomości do 10 firm (30), rozmowy (60), wysyłka ofert (30), przyjęcie filmu i opisu pokazu (45) oraz 1 pytanie w karcie (nr 8: założenia robocze w miejsce luk „Do uzupełnienia”). Dwa wpisy w DECYZJE.md (2026-11-21).
  decyzja: przyjęcie porządków: zamknięcie duplikatu, uproszczenie zadania z e-mailem Useme i założenia robocze z pytania 8 w KARTA.md
  zostało: „Podłącz dysk z kopią PC do Maca” miało termin 20.11 i nadal czeka; bez niego nie ruszy wybór 10 firm (21.11) ani wysyłka wiadomości (25.11). Terminów nie zmieniałem.
- [ ] Uzupełnić pliki projektu według standardu | kto: claude
  cel: Uzupełnić według standard/STANDARD.md: Zadania (5 braków), README (4 braki), Architektura (brak pliku), Uruchomienie (brak pliku), Instrukcje agentów (brak pliku). Niczego nie nadpisywać; na końcu python3 standard/projekt.py sprawdz bez braków w tym projekcie.
- [~] Przygotuj projekt wizytówek Oprogramowani do weryfikacji | kto: claude | gdzie: chmura | kiedy: 2026-11-23 | wymaga: odbiór
  cel: gotowy projekt wizytówek marki Oprogramowani (przód i tył), który właściciel sam zweryfikuje przed drukiem
  gotowe gdy: w repozytorium projektu jest folder wizytowki/ z plikiem do druku (PDF, 90×50 mm, przód i tył) i podglądem do obejrzenia; wygląd spójny ze stroną oprogramowani.com; danych kontaktowych agent nie wymyśla: bierze je z plików projektu, a brakujące wypisuje w wynik:; nic nie zamówione ani nie wysłane do drukarni
  materiał: strona-www/BRIEF_strona_www.md
  materiał: KARTA.md#Cel
  wynik: po czwartej poprawce doszły obrazy wizytówki do wklejenia na stronę, w PNG zamiast JPG: wizytowki/na-strone-przod-i-tyl.png (przód i tył obok siebie na jasnym tle, 2268×850 px), wizytowki/na-strone-przod.png i wizytowki/na-strone-tyl.png (sam przód i sam tył po przycięciu, 963×624 px). Projekt bez zmian: jedna wizytówka, imienna Krystiana Stryjakiewicza, przód i tył. Plik do wgrania w drukarni: wizytowki/wizytowka-krystian-89x59.pdf (89×59 mm, 2 strony); to samo osobno jako przód i tył: wizytowki/wizytowka-krystian-89x59-przod.pdf i wizytowki/wizytowka-krystian-89x59-tyl.pdf oraz obrazy PNG o tych samych nazwach. Podgląd: wizytowki/podglad.png. Wersja 90×50 mm: wizytowki/wizytowka-krystian-90x50.pdf. Opis: wizytowki/README.md. Przód: „Automatyzujemy i integrujemy. Mniej ręcznej pracy w firmie.”, na dole „Automatyzacje i integracje dla firm” i oprogramowani.com. Tył: Krystian Stryjakiewicz, pod nazwiskiem „Łączymy programy i automatyzujemy powtarzalne zadania”, 663 206 373, kontakt@oprogramowani.com, oprogramowani.com, w rogu „8 lat doświadczenia”. Wygląd jak na obecnej stronie (krój Inter, znak O·PRO·GRAMOWANI, czerwień, ciemny przód). Telefon, e-mail i nazwisko z kodu strony; „8 lat” z Twojej poprawki. Brakujące dane: nazwisko, rola i numer Pawła (pytanie 9 w KARTA.md), adres firmy, profile LinkedIn. Nic nie zamówiono ani nie wysłano.
  decyzja: czy wizytówka w tej postaci idzie do druku; w szczególności czy pod nazwiskiem ma zostać „Łączymy programy i automatyzujemy powtarzalne zadania” zamiast roli „Procesy i rozmowa z klientem” i czy 89×59 mm to u Twojej drukarni wizytówka 85×55 mm ze spadem 2 mm (tak ją złożyłem)
  zostało: nie ma pliku JPG, o który prosiłeś: moje narzędzie zapisuje tylko PDF i PNG, a na zamianę PNG na JPG nie mam uprawnień. PNG wklejasz na stronę www tak samo jak JPG; jeśli chodziło o stronę drukarni, która przyjmuje wyłącznie JPG, tych plików nie przyjmie. Nie wiem, w której drukarni wgrywasz plik, więc nie sprawdziłem jej wymagań: przyjąłem, że 89×59 mm to 85×55 mm plus 2 mm spadu z każdej strony; kolory są ekranowe (RGB), nie CMYK; strona w PDF ma 88,9×58,9 mm (0,1 mm mniej przez zaokrąglenie), co drukarnia może odrzucić. Strona oprogramowani.com nadal ma w nagłówku „Ty zajmujesz się firmą” i ERP; strony nie zmieniałem.
  poprawka: no spoko a dasz to jako jpg abym wkleił w stronę ?
  zmiany: obrazy wizytówki na stronę (przód, tył i oba obok siebie): zrobione, ale w PNG; JPG: niezrobione, bo nie mam uprawnień do zamiany PNG na JPG; projekt wizytówki i pliki do druku: bez zmian
  następne: Usuń zwrot „Ty zajmujesz się firmą” z nagłówka strony oprogramowani.com i dopasuj hasło do wizytówki | kto: claude | kiedy: 2026-11-25
- [x] Zaplanuj filmy na grudzień według podziału z karty | kto: claude | gdzie: chmura | kiedy: 2026-11-24
  cel: dopisz do harmonogramu kampanii projektu 4–6 publikacji z filmem na grudzień (tytuł ze słowem „film”, kanał np. reels, linkedin), tematy z kampanii i dokumentów marketingu; podział filmów jak w polu karty „nagrywa: ai 50, ty 30, panel 20” (panel nagrywa ekran strony, AI: film z gotowych poleceń, Ty: nagranie telefonem tam, gdzie trzeba pokazać prawdziwą rzecz)
  gotowe gdy: w kampanii są nowe wiersze publikacji z filmem z datami w grudniu, kto: ty, każda z kanałem; scenariuszy nie zakładasz (panel przygotuje je sam 7 dni przed publikacją według podziału)
  wynik: w harmonogramie kampanii (kampanie/pozyskanie-klientow.md) jest 6 nowych publikacji z filmem, każda kto: ty, z kanałem i czasem 15 min: 2.12 „plan produkcji ułożony rano, nieaktualny przed południem” (reels, AI), 7.12 „jak wygląda 30-minutowy przegląd drogi zamówienia” (linkedin, Ty telefonem: wydrukowany arkusz), 9.12 „droga od ręcznego przepisywania do audytu na oprogramowani.com” (reels, panel nagrywa stronę), 11.12 „program mówi 12 sztuk, na regale jest 9” (reels, AI), 14.12 „jedna kartka po przeglądzie, co zostaje w firmie” (linkedin, Ty telefonem: wydruk przykładu), 16.12 „najlepiej sprzedający się mebel bywa najmniej opłacalny” (reels, AI). Podział: 3 AI, 2 Ty, 1 panel. Scenariuszy nie zakładałem. Uzasadnienie w DECYZJE.md (2026-11-24).
  zostało: trzy filmy (11, 14 i 16.12) wychodzą po dacie końca kampanii 8.12; daty końca nie zmieniałem. Sposób nagrania (AI, Ty, panel) przydziela panel sam; w notatkach pod publikacjami jest kolejność, którą powinien wyliczyć, ale nie mogłem sprawdzić, czy przydzieli tak samo. Te 6 filmów dochodzi do dwóch już zaplanowanych (1.12 i 4.12) i do 6 wpisów serii, więc grudzień ma dla Ciebie więcej pracy niż 1,5 h tygodniowo z wariantu 2.
- [~] Przygotuj scenariusz nagrania na 2026-12-02: Film: plan produkcji ułożony rano, nieaktualny przed południem | kto: claude | gdzie: chmura | kiedy: 2026-11-25 | wymaga: odbiór
  cel: scenariusz filmu do publikacji „Film: plan produkcji ułożony rano, nieaktualny przed południem” z 2026-12-02 (reels), który właściciel zrobi 2026-12-01 w narzędziu AI do wideo (np. CapCut, Runway, Kling): dla każdej sceny gotowe polecenie do skopiowania (co widać, ruch kamery, styl, długość), tekst lektora i napisy, muzyka; bez prawdziwych ludzi i bez udawania prawdziwego produktu — ujęcia, które muszą pokazać prawdziwy produkt albo ekran, oznacz „nagraj telefonem” albo „zrzut ekranu” (przeczytaj kampanię, plan filmów i dokumenty projektu)
  gotowe gdy: obok KARTA.md jest plik posty/2026-12-02-film-plan-produkcji-ulozony-rano-nieaktu/scenariusz.md w układzie: „# Scenariusz nagrania: <tytuł>”, pola „- stan: propozycja”, „- publikacja: 2026-12-02”, „- nagranie: 2026-12-01”, „- sposób: ai”, sekcje ## Po co (cel, dla kogo), ## Co nagrać (wiersze „- [ ] polecenie dla AI / 5 s”), ## Jak (narzędzie, format pionowy albo poziomy, styl i spójność scen), ## Co powiedzieć (tekst albo punkty), ## Na koniec (wezwanie do działania), ## Gotowe gdy; każda sekcja wypełniona; post.md i zadania nagrania bez zmian
  materiał: kampanie/pozyskanie-klientow.md
  materiał: STYL.md
- [!] Dodaj na stronie miejsca na zdjęcia, LinkedIn, dane firmy i film | kto: agent | gdzie: chmura | kiedy: 2026-11-25 | blokada: nie mogłem zbudować strony ani zrobić zrzutów (brak uprawnień do npm), a produkcyjna wersja z założenia nie zbuduje się bez 23 danych firmy w dane.js
  cel: strona oprogramowani-onepager ma gotowe miejsca na rzeczy, które uwiarygodnią firmę i które właściciel dostarczy sam: (1) zdjęcia Krystiana i Pawła w miejscu inicjałów, przy każdym jedno zdanie roli i link do LinkedIn; (2) NIP, adres i link do wpisu CEIDG w stopce; (3) sekcja z krótkim filmem 60–90 s, w którym obaj mówią, kim są i jak wygląda bezpłatna rozmowa
  gotowe gdy: w wersji roboczej (`npm run build:panel`) każde z trzech miejsc jest widoczne jako żółte [UZUPEŁNIJ] z opisem, co tam wstawić (zdjęcie, link, plik filmu); wartości trzyma site/src/dane.js, więc po wpisaniu danych miejsca same się wypełniają, a puste pola nie pokazują się w wersji produkcyjnej; produkcyjne `npm run build` przechodzi; zrzuty 390 i 1440 px obejrzane; wersja na komputer poza tymi miejscami bez zmian; żadne dane nie są wymyślone
  poprawka: Zrób to
  wynik: wszystkie trzy miejsca są teraz w kodzie strony i biorą wartości z dane.js: (1) zdjęcie zamiast inicjału, rola i LinkedIn, (2) NIP, adres i link CEIDG w stopce, (3) nowy blok filmu pod kartami osób w „Kto to robi”: bez pliku wersja robocza pokazuje żółtą ramkę z opisem (plik MP4, plakat, napisy), a produkcja nic; teksty w czterech językach; opis miejsc w strona-www/miejsca-wiarygodnosci.md; uzasadnienie w DECYZJE.md (2026-11-25)
  zostało: strony nie zbudowałem i nie obejrzałem zrzutów 390 i 1440 px (brak uprawnień), więc nie sprawdziłem, czy film i żółte miejsca wyglądają dobrze ani czy reszta wersji na komputer jest bez zmian; zmiana w kodzie strony czeka na zatwierdzenie. Wersja produkcyjna zbuduje się dopiero, gdy w danych strony będą m.in. VAT, adres z CEIDG, ceny, gwarancja i okresy RODO (23 pola)
  zmiany: dodany blok filmu z polem DANE.film (plik, plakat, napisy); dokładniejszy opis żółtego miejsca na zdjęcie we wszystkich językach; poprawka „Zrób to”: zrobione w kodzie, bez builda i zrzutów
  następne: Zbuduj wersję roboczą strony, obejrzyj zrzuty 390 i 1440 px z filmem i zatwierdź zmianę w repozytorium strony | kto: agent | kiedy: 2026-11-26
- [ ] Zaudytuj stronę dwoma agentami i poprawiaj do oceny 9/10 | kto: agent | kiedy: 2026-11-25 | po: Dodaj na stronie miejsca na zdjęcia, LinkedIn, dane firmy i film
  cel: strona oprogramowani-onepager w ocenie dwóch audytorów ma co najmniej 9/10: (1) właściciel firmy meblarskiej 10–50 osób (czy rozumie ofertę i chce się umówić na rozmowę), (2) sceptyczny klient (czy wierzy, że firma jest prawdziwa i rzetelna)
  gotowe gdy: obaj audytorzy dają co najmniej 9/10 na zrzutach 390 i 1440 px, a po każdej rundzie poprawki są zbudowane i obejrzane; najwyżej 3 rundy; w wynik: ocena każdego audytora w każdej rundzie z powodami; ocena zakłada, że miejsca [UZUPEŁNIJ] zostaną wypełnione; czego nie da się poprawić bez danych właściciela, trafia do zostało:; nie dopisuje wymyślonych opinii, liczb ani klientów; nic nie publikuje
  materiał: strona-www/miejsca-wiarygodnosci.md
  materiał: DECYZJE.md
