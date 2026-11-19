# Formy marketingu Opisarni na grudzień 2026 (poza Reels)

> Utworzone 2026-11-19. Okno: 1–23.12 (go/no-go 23.12: 40 kont Free, 20 aktywnych, 3 płacących; stan 18.11: 0 / 0 / 0).
> Wszystko poniżej to propozycje. Agent niczego nie opublikował ani nie wysłał; publikuje i pisze do ludzi wyłącznie właściciel.
> Formy są dodatkiem do stałego rytmu (post co 2 dni, kampanie/staly-rytm.md) i do Reels, nie zamiast nich.
> „Studio” to studio filmów w panelu, które z pliku scenariusz.json nagrywa film: **pokaz** (nagranie ekranu Opisarni z napisami,
> jak film A) albo **objaśnienie** (plansze z napisami tłumaczące jeden temat, bez ekranu aplikacji).

## 1. Rekomendacja

Na start trzy formy: **A (darmowy przegląd opisu)**, **C (grupy sprzedawców na Facebooku)**, **D (maile aktywacyjne do założonych kont)**.

- A daje konta, które od razu są aktywne, bo człowiek widzi opis własnego mebla. Daje też rozmowy, czyli jedyne źródło wiedzy, dlaczego ktoś zapłaci albo nie.
- C wychodzi poza LinkedIn. Sieć kontaktów właściciela na LinkedIn jest mała (pytanie 8 w KARTA.md; odpowiedź „z 4” czytam jako kilka osób z branży, to moja interpretacja), więc same posty tam nie dowiozą 40 kont.
- D nie daje nowych kont, ale pracuje na dwa pozostałe cele: 20 aktywnych i 3 płacących. Dziś aplikacja wysyła tylko mail weryfikacyjny i reset hasła (`backend/app/services/mailer.py`), więc konto bez pierwszego opisu nie dostaje żadnego przypomnienia.

Koszt trzech form: 0 zł wydatków, około 2 godzin pracy właściciela tygodniowo ponad stały rytm, 5 zadań agenta.
B i E zostają w odwodzie: B można włączyć w każdej chwili w slot stałego rytmu, E daje efekt dopiero po 23.12.

## 2. Zestawienie

Nakład właściciela to czas ponad stały rytm. Szacunki kont to moje założenia, nie pomiary (dotąd nie ma żadnych danych o konwersji).

| | Forma | Kanał | Częstotliwość | Nakład właściciela | Nakład agenta | Film ze studia | Szacunek do 23.12 | Koszt |
|---|---|---|---|---|---|---|---|---|
| **A** | Darmowy przegląd opisu | LinkedIn, grupy FB, otwarte rozmowy | 2 ogłoszenia, do 10 przeglądów | ok. 3 h w miesiącu | 1 zadanie | nie na start; później pokaz | 5–7 kont, 4–5 aktywnych | 0 zł |
| B | Karuzela „przed i po” | LinkedIn (dokument), Facebook (album) | 1 na tydzień, w slocie rytmu | 15 min na publikację | 1 zadanie na odcinek | tak, pokaz (co drugi odcinek) | 1–3 konta | 0 zł |
| **C** | Grupy sprzedawców na Facebooku | grupy FB o Allegro i eksporcie | 3 odpowiedzi na tydzień, 1 poradnik na 2 tygodnie | 30 min raz, potem ok. 40 min na tydzień | 1 zadanie na poradnik | tak, objaśnienie (do poradnika) | 2–6 kont | 0 zł |
| **D** | Maile aktywacyjne | e-mail z aplikacji | 3 maile na konto, automatycznie | ok. 30 min (akceptacja tekstów) | 2 zadania (teksty z oceną RODO, kod) | tak, pokaz (link w mailu 1) | 0 kont; aktywacja z ok. 30% do ok. 50% | 0 zł |
| E | Poradnik z filmem | YouTube, strona poradnika na opisarnia.pl | 1 na 2 tygodnie | ok. 30 min na odcinek | 2 zadania na odcinek i sekcja poradnika w kodzie | tak, objaśnienie | 0–1 konto | 0 zł |

Suma form A, C i D to według tych założeń 7–13 kont. Reszta do 40 musi przyjść z tego, co już działa (stały rytm, Reels, firmy z researchu, znajomi z branży).
Cel 40 kont jest więc nadal niepewny i warto to wiedzieć przed 23.12, a nie w dniu decyzji.

## 3. Formy

### A. Darmowy przegląd opisu (rekomendowana)

- **Kanał:** post na LinkedIn i Facebooku w slocie stałego rytmu; grupy z formy C tam, gdzie regulamin pozwala; osoby z partii 1–3, z którymi rozmowa już trwa.
- **Dla kogo:** właściciel małej firmy meblowej z ofertami na Allegro, który ma opisy przepisane od dostawcy albo tylko po polsku, a sprzedaje lub chce sprzedawać do Niemiec.
- **Przykład tematu:** „Przejrzę opis jednego Twojego mebla na Allegro. Dostaniesz 3 konkretne uwagi i gotową wersję po polsku i po niemiecku. 10 miejsc do 11 grudnia, wystarczy link do oferty w komentarzu.”
- **Częstotliwość:** ogłoszenie 1.12, przypomnienie 8.12 („zostało X miejsc”); odpowiedź na zgłoszenie w 48 godzin; limit 10 przeglądów w grudniu.
- **Nakład pracy:** właściciel ok. 15 minut na przegląd (wpisanie atrybutów z oferty do Opisarni, 3 uwagi według szablonu, odpowiedź z linkiem opisarnia.pl/rejestracja), czyli 2,5 h przy 10 przeglądach plus 30 minut na dwa ogłoszenia. Agent: jedno zadanie (ogłoszenie, przypomnienie, szablon 3 uwag, szablon odpowiedzi).
- **Film ze studia:** nie na start. Po pierwszych 3 przeglądach studio może zrobić pokaz „Przegląd jednego opisu w 60 sekund” na meblu przykładowym, bez oferty zgłaszającego.
- **Miernik:** zgłoszenia, konta, konta z pierwszym opisem; wpis w kolumnie „Źródło nowych kont” jako „przegląd”.
- **RODO i prawo:** odpowiadasz na prośbę osoby, więc nie jest to niezamówiona oferta. Adresu zgłaszającego nie dopisujesz do żadnej listy bez osobnej zgody. W poście „po przeglądzie” nie podajesz nazwy firmy ani treści cudzej oferty.
- **Ryzyko:** brak zgłoszeń przy małym zasięgu postu; wtedy tę samą propozycję składasz w wiadomości 2 do firm z partii 1–3 zamiast samego linku.

### B. Karuzela „przed i po” (odwód)

- **Kanał:** LinkedIn jako dokument PDF (3–4 kwadraty), Facebook jako album; w slocie stałego rytmu, bez dodatkowego dnia publikacji.
- **Dla kogo:** sprzedawca, który wkleja opis od producenta i nie widzi różnicy między listą cech a opisem; także osoby pytające „po co mi to, skoro mam ChatGPT”.
- **Przykład tematu:** „Ten sam mebel, trzy opisy: od dostawcy, z Opisarni po polsku, z Opisarni po niemiecku.” Materiał wyjściowy jest gotowy: `marketing/linkedin/drafts/2026-07-20-cechy-vs-korzysci-ten-sam-mebel.md` i `2026-07-08-opis-od-dostawcy-kopiuj-wklej.md`.
- **Częstotliwość:** 1 na tydzień, czwartki 3.12, 10.12, 17.12.
- **Nakład pracy:** właściciel 15 minut na publikację. Agent: jedno zadanie na odcinek. Wymaga dopisku w STYL.md (dziś jedna grafika na post, tu 3–4 kwadraty z tego samego szablonu).
- **Film ze studia:** tak, pokaz 30–45 s: te same atrybuty wpisane w Opisarni i przełączenie PL/DE. Co drugi odcinek, jako wersja na Facebooka.
- **Ryzyko:** opis „przed” musi być przykładem własnym, nie cudzą ofertą.

### C. Grupy sprzedawców na Facebooku (rekomendowana)

- **Kanał:** 3–5 grup na Facebooku dla sprzedawców Allegro i dla eksportujących do Niemiec. Plan pierwszych 10 kont (punkt 8) wskazuje ten kanał jako zamiennik przy wyniku 5–9 kont; proponuję włączyć go w grudniu niezależnie od wyniku 30.11.
- **Dla kogo:** mikrofirmy i jednoosobowi sprzedawcy, których nie ma na LinkedIn; decyzja u właściciela, pytają o praktykę (zwroty, opisy, wymiary, tłumaczenia).
- **Przykład tematu:** poradnik „5 pól z wymiarami, które wpisuję w opisie szafy, żeby nie wróciła, bo nie weszła po schodach” (z draftu `2026-06-29-wymiary-mebel-nie-wjedzie.md`). Przykład odpowiedzi w cudzym wątku: ktoś pyta o tłumaczenie ofert na niemiecki, a Ty opisujesz, co sprawdzić w nazwach materiałów i wymiarach; o Opisarni piszesz dopiero zapytany.
- **Częstotliwość:** 3 merytoryczne odpowiedzi na tydzień (poniedziałek, środa, piątek po 10 minut); własny poradnik raz na 2 tygodnie: 4.12 i 18.12.
- **Nakład pracy:** właściciel 30 minut na start (wybór grup, przeczytanie regulaminów, dołączenie), potem ok. 40 minut na tydzień. Agent: jedno zadanie na poradnik (tekst w wersji bez reklamy i lista 5 typowych pytań z gotowymi odpowiedziami).
- **Film ze studia:** tak, objaśnienie 60–90 s dodane do poradnika jako film wgrany w grupie (bez linku na zewnątrz). Na 4.12 jeden film, kolejny po sprawdzeniu, czy pierwszy miał wyświetlenia.
- **Miernik:** odpowiedzi, wejścia z Facebooka, konta. Od 1.12 pomoże pole źródła i UTM (zadanie już jest w ZADANIA.md).
- **RODO i prawo:** post i komentarz publiczny nie są marketingiem bezpośrednim. Wiadomość prywatna z ofertą do osoby z grupy już jest, więc link wysyłasz tylko na prośbę.
- **Ryzyko:** regulaminy wielu grup zakazują autopromocji; link w poście bez zgody administratora kończy się usunięciem z grupy. Nie znam nazw ani wielkości grup: w tej sesji nie miałem dostępu do sieci, więc wybór grup jest pierwszym krokiem właściciela.

### D. Maile aktywacyjne do założonych kont (rekomendowana)

- **Kanał:** e-mail wysyłany przez aplikację (SMTP Brevo działa od 18.11).
- **Dla kogo:** osoba, która założyła konto i nie wygenerowała opisu (cel 20 aktywnych), oraz osoba bliska limitu 10 opisów (cel 3 płacących).
- **Przykład tematu:** mail 1, dzień po rejestracji bez opisu: „Pierwszy opis w 2 minuty: typ mebla, wymiary, materiał”. Mail 2, po 3 dniach: „Ten sam mebel po niemiecku, jednym kliknięciem”. Mail 3, przy 8 z 10 opisów: „Zostały Ci 2 opisy w tym miesiącu” z informacją o planie Solo za 49 zł.
- **Częstotliwość:** najwyżej 3 maile na konto, każdy raz; wysyłka automatyczna po spełnieniu warunku.
- **Nakład pracy:** właściciel ok. 30 minut (akceptacja tekstów, zgoda na wdrożenie). Agent: zadanie 1: teksty z oceną RODO; zadanie 2: kod (warunki wysyłki, log wysyłek, link rezygnacji, testy). Start wysyłki realnie od 9.12.
- **Film ze studia:** tak, pokaz 30–45 s „pierwszy opis w 2 minuty”, podlinkowany w mailu 1 (link, nie załącznik). Można użyć filmu A, jeśli jest przyjęty.
- **Miernik:** odsetek kont z pierwszym opisem w 7 dni od rejestracji; liczba kont, które doszły do limitu; płacący.
- **RODO i prawo:** to najważniejsze ryzyko tej formy. Maile 1 i 2 to instrukcja korzystania z założonej usługi, bez oferty. Mail 3 zawiera cenę, więc może być uznany za marketing, a rejestracja zbiera dziś tylko jedną, wymaganą zgodę (`backend/app/consent.py` zastrzega, że zgoda marketingowa musi być osobna). Dlatego teksty przechodzą ocenę RODO przed kodem; wariant bezpieczny to mail 3 bez ceny, z samą informacją o limicie i linkiem do ustawień konta. Każdy mail ma link rezygnacji. Przepisów nie sprawdziłem w sieci w tej sesji.
- **Ryzyko:** przy kilku kontach efekt będzie niemierzalny; do czasu wdrożenia zostaje ręczna wiadomość tylko do osób, z którymi już rozmawiasz (punkt 3 planu, 29.11).

### E. Poradnik z filmem objaśniającym (odwód, po 23.12)

- **Kanał:** YouTube (film 2–3 minuty) i strona poradnika na opisarnia.pl z tym samym tekstem; link do poradnika w postach stałego rytmu.
- **Dla kogo:** sprzedawca, który szuka w Google albo na YouTube, jak napisać opis mebla na Allegro lub po niemiecku; także materiał, do którego odsyłasz z grup (forma C).
- **Przykład tematu:** „Jak napisać opis komody na Allegro: 4 elementy i wzór do skopiowania” (z draftu `2026-06-10-opis-pod-allegro-jak-pisac.md`).
- **Częstotliwość:** 1 na 2 tygodnie: 9.12 i 21.12.
- **Nakład pracy:** właściciel ok. 30 minut na odcinek (obejrzenie, publikacja na YouTube). Agent: scenariusz i tekst poradnika na odcinek oraz jednorazowo sekcja poradnika w kodzie (dziś frontend jej nie ma), wdrożenie po zgodzie.
- **Film ze studia:** tak, objaśnienie 2–3 min, w poziomie.
- **Ryzyko:** ruch z wyszukiwarki pojawia się po tygodniach, więc do 23.12 ta forma nie pomoże w liczbach. Sens ma dopiero przy decyzji „go”.

## 4. Warianty

| Wariant | Co wchodzi | Wydatki | Czas właściciela ponad rytm | Szacunek kont | Plusy | Minusy |
|---|---|---|---|---|---|---|
| 1 | A + B | 0 zł | ok. 1 h na tydzień | 6–10 | najmniej pracy, wszystko w obecnych kanałach | zasięg ograniczony do małej sieci; nic dla aktywacji |
| **2 (rekomendacja)** | A + C + D | 0 zł | ok. 2 h na tydzień | 7–13 i wyższa aktywacja | nowy kanał poza LinkedIn; praca na wszystkie trzy cele | D wymaga kodu, oceny RODO i zgody na wdrożenie |
| 3 | A + C + D + B | 0 zł | ok. 2,25 h na tydzień | 8–16 | B zużywa gotowe drafty | więcej zadań agenta do odbioru |
| 4 | wariant 2 + płatna reklama Meta | ok. 300 zł | ok. 2,5 h na tydzień | 9–18 | szybki dopływ ruchu | wydatek wymaga zgody; budżetu na promocję nie ma w KARTA.md; koszt konta 60–150 zł to założenie z planu 10 kont |

## 5. Oś czasu (wiersze do wpisania)

Daty dla wariantu 2. Wiersze agenta mają termin dzień lub dwa przed publikacją.

| Kiedy | Kto | Co | Forma |
|---|---|---|---|
| 2026-11-30 | claude | Przygotuj ogłoszenie, przypomnienie i szablony darmowego przeglądu opisu | A |
| 2026-12-01 | ty (15 min) | Opublikuj ogłoszenie darmowego przeglądu opisu (LinkedIn, Facebook) | A |
| 2026-12-01 | ty (30 min) | Wybierz 3–5 grup sprzedawców na Facebooku i przeczytaj regulaminy | C |
| 2026-12-02 | claude | Przygotuj teksty 3 maili aktywacyjnych z oceną RODO | D |
| 2026-12-02 | claude | Przygotuj poradnik do grup „5 pól z wymiarami” i scenariusz filmu objaśniającego | C |
| od 2026-12-02, pon/śr/pt | ty (10 min) | 1 merytoryczna odpowiedź w grupie | C |
| 2026-12-04 | ty (15 min) | Opublikuj poradnik z filmem w grupach, które na to pozwalają | C |
| 2026-12-04 | ty (15 min) | Przyjmij teksty maili aktywacyjnych | D |
| 2026-12-07 | claude | Dodaj wysyłkę maili aktywacyjnych (kod, testy); wdrożenie po zgodzie | D |
| 2026-12-08 | ty (10 min) | Opublikuj przypomnienie o przeglądzie („zostało X miejsc”) | A |
| 2026-12-09 | ty | Zgoda na wdrożenie maili aktywacyjnych | D |
| 2026-12-11 | ty | Koniec zgłoszeń do przeglądu; ostatnie odpowiedzi do 13.12 | A |
| 2026-12-14 | ty (10 min) | Pomiar: konta i aktywne według źródła (przegląd, grupy, reszta) | A, C, D |
| 2026-12-16 | claude | Przygotuj drugi poradnik do grup | C |
| 2026-12-18 | ty (15 min) | Opublikuj drugi poradnik w grupach | C |
| 2026-12-23 | ty | Liczby form w decyzji go/no-go | A, C, D |

## 6. Ryzyka

1. Suma szacunków (7–13 kont) nie zamyka celu 40. Formy poprawiają szanse, ale wynik zależy też od kanałów uruchomionych w listopadzie.
2. Grudzień to szczyt sprzedaży: do ok. 15.12 sprzedawcy mają mało czasu, po 20.12 nie odpisują. Realne okno to 1–18.12.
3. Czas właściciela: stały rytm, kontakty z planu 10 kont i 2 godziny na nowe formy mogą się nie zmieścić wieczorami. Przy braku czasu pierwsza odpada forma C, nie A.
4. Maile aktywacyjne bez oceny RODO to ryzyko prawne, a wdrożenie po 9.12 zostawia tylko dwa tygodnie na efekt.
5. Usunięcie z grupy za autopromocję zamyka kanał C na stałe; stąd zasada: link tylko na prośbę.
6. Konta z przeglądu mogą być „z grzeczności”. Liczy się, czy wygenerują drugi opis bez Twojej pomocy.

## 7. Otwarte pytania

1. Które formy wchodzą na grudzień (propozycja: A, C, D)? Pytanie 14 w KARTA.md.
2. Czy jest budżet na promocję (pole do uzupełnienia w KARTA.md)? Bez niego wariant 4 odpada.
3. Czy masz konto na Facebooku, z którego chcesz pisać w grupach jako osoba, a nie strona?
4. Czy mail 3 ma zawierać cenę planu Solo, czy tylko informację o limicie (wariant bezpieczny)?
