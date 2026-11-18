# Zadania: Opisarnia (generator opisów mebli)

> Jedyna lista zadań projektu. Czyta ją panel i agenci.
> Wiersz: `- [ ] Tytuł | kto: claude | gdzie: pc | kiedy: RRRR-MM-DD | pora: noc | czas: 30 | wymaga: zgoda`
> Stany: `[ ]` do zrobienia, `[~]` w toku, `[!]` zablokowane (dodaj `blokada: powód`), `[x]` zrobione.
> Pola są opcjonalne. kto: claude, codex, ty. gdzie: pc, mac, chmura. pora: dzień, noc. czas: minuty Twojej pracy. wymaga: zgoda, odbiór.
> Etap to nagłówek `## Etap: nazwa` i wiersz `termin: RRRR-MM-DD` pod nim. Etap bez otwartych zadań jest zamknięty.
> Szczegóły zadania: wcięte wiersze pod zadaniem (cel:, gotowe gdy:, materiał:, kroki `- [ ]`, wynik:, decyzja:, zostało:).
> Ścieżki w „materiał:” są względem repozytorium Opisarni albo folderu karty (KARTA.md, STYL.md, kampanie/).
> Publikacje (posty i filmy) są w `kampanie/staly-rytm.md`; tu zostają kontakty i pomiary.

> Uzupełnione danymi z PC (audyt 2026-11-14) i odpowiedziami właściciela z 2026-11-14 (terminy etapów zatwierdzone).

## Etap: MVP i Faza 1 (kod)

- [x] Backend MVP: FastAPI, Postgres, Redis, auth, konto, historia, feedback, docker compose (2026-06-08)
- [x] Ekrany UI MVP i Fazy 1 (11 ekranów, Pulpit, Centrum opisów)
- [x] Płatności Stripe w trybie testowym i faktury pod KSeF (F1-STRIPE-1..3, 2026-06-10)
- [x] Import katalogu i generacja wsadowa Celery (F1-BATCH-1..2, 2026-06-10)
- [x] Retencja 90 dni i eksport/usunięcie konta (F1-RETENCJA, 2026-06-10)
- [x] Język niemiecki w generatorze i w demo (2026-06-17)
- [x] Strojenie jakości opisów: bramki promptu, harness ewaluacji, auto-strojenie (VI–VII)
- [x] Eksport pod Allegro, walidator wejścia, rejestr portali, korektor anty-halucynacyjny, reset hasła, eksport ZIP, ATTR-1..3 (VI–X)
- [x] EAN/GTIN, korektor v3/v4, ukryty plan testowy za 2 zł (#122, 2026-10-27)
- [x] Silnik Claude Haiku z zapasowym Mistralem (#123, ADR 0045, 2026-10-29)
- [x] Polityka cookies, fonty bez Google (#124–#125, 2026-11-02)
- [x] Eksport ZIP, Excel, portal Stripe, nowy landing z komodą 3D, refund limitu, ZDJ-1 za flagą (#126–#134, 2026-11-06)

## Etap: Bezpieczeństwo przed płacącymi

- [x] SEC-3, SEC-5, SEC-1: zależności, sekrety i RODO, SAST backendu (2026-06-16)
- [~] Zamknij SEC-2: SAST frontendu (XSS, open redirect, storage, CSP) | kto: claude | gdzie: chmura | wymaga: odbiór
  cel: frontend bez znalezisk CRITICAL, HIGH i MEDIUM z SAST (XSS, open redirect, storage, CSP)
  gotowe gdy: poprawki 3 LOW zacommitowane, testy frontendu zielone, raport odebrany przez właściciela
  materiał: docs/security/raport-audytu.md
  wynik: re-audyt 2026-11-18: 0 CRITICAL, 0 HIGH, 0 MEDIUM; 3 LOW naprawione w kodzie
  decyzja: odebrać raport SEC-2 i zgodzić się na commit poprawek 3 LOW
  zostało: poprawki niezacommitowane; testy frontendu nieuruchomione (brak Node.js na serwerze)
- [~] Zamknij SEC-4: infra, nagłówki bezpieczeństwa, CORS, rate-limit | kto: claude | gdzie: chmura | wymaga: odbiór
  cel: infrastruktura bez znalezisk CRITICAL i HIGH; nagłówki, CORS i limity zgodne z raportem
  gotowe gdy: poprawki zacommitowane i wdrożone, `caddy validate` i pytest zielone, raport odebrany przez właściciela
  materiał: docs/security/raport-audytu.md
  wynik: re-audyt 2026-11-18: 0 CRITICAL, 0 HIGH; 1 MEDIUM (brak limitu body na Caddy) i 2 LOW naprawione w repo; 2 LOW zapisane jako dług
  decyzja: odebrać raport SEC-4 i zgodzić się na commit oraz wdrożenie limitu body na Caddy
  zostało: poprawki niezacommitowane i niewdrożone; `caddy validate` i pytest nieuruchomione (brak uprawnień)

## Etap: Testy

- [x] Testy E2E (VI–VII, według historii commitów)

## Etap: Produkcja
termin: 2026-11-17

- [ ] Unieważnij testowy klucz API Mistral wklejony do rozmowy 26.10 | kto: ty | czas: 5
  cel: klucz Mistral z historii rozmowy przestaje działać
  gotowe gdy: klucz ma w konsoli Mistral stan unieważniony, a zapasowy silnik Opisarni działa na innym kluczu
  Klucz leży jawnie w historii Claude Code z PC (archiwum rozmów na Macu, ksiega/MIGRACJA.md).
- [x] Serwer Hetzner, Caddy z HTTPS, docker-compose.prod (ADR 0004, 0034)
- [x] Auto-deploy przez GitHub Actions (#70)
- [x] Ręczny deploy do #125 (2026-11-03)
- [x] Deploy #126–#134 na produkcję i klucz Anthropic; silnik Haiku działa od 13.11 (potwierdził właściciel 2026-11-14)
- [x] Stripe w trybie live (potwierdził właściciel 2026-11-14)
- [x] JDG w CEIDG (potwierdził właściciel 2026-11-14)
- [ ] Potwierdź DPA z dostawcami LLM, regulamin i politykę prywatności | kto: ty | kiedy: 2026-11-17 | czas: 15
  cel: przed płacącymi Opisarnia ma podpisane DPA z dostawcami LLM oraz aktualny regulamin i politykę prywatności
  gotowe gdy: wszystkie kroki zaznaczone, a data akceptacji DPA wpisana przy kroku
  materiał: KARTA.md#Zasoby i ograniczenia
  - [ ] DPA Anthropic (silnik Haiku)
  - [ ] DPA Mistral (silnik zapasowy)
  - [ ] regulamin na opisarnia.pl wymienia obu dostawców
  - [ ] polityka prywatności na opisarnia.pl wymienia obu dostawców

## Etap: Walidacja i marketing
termin: 2026-12-23

- [x] Opublikować pierwsze posty LinkedIn (2026-06-08, 2026-06-12)
- [x] Bramka ADR 0001 zastąpiona celami do 23.12 (2026-10-27; 200 adresów nie zebrano, Brevo wyłączył klucz SMTP 14.10)
- [x] Metryki: metryki.md w repozytorium, pomiar startowy 2026-11-18: 0 kont, 0 aktywnych, 0 płacących
- [ ] Wpisz pomiar tygodniowy do metryki.md | kto: ty | kiedy: 2026-11-23 | czas: 10
  cel: wiersz 2026-11-23 w tabeli pomiarów uzupełniony liczbami z produkcji
  gotowe gdy: w metryki.md, punkt 3, wiersz 2026-11-23 ma liczby w kolumnach konta Free, nowe konta, aktywne, płacący i MRR
  materiał: metryki.md#3
  materiał: metryki.md#6
  Pomiar co poniedziałek; kolejne: 2026-11-30 (checkpoint), 2026-12-07, 2026-12-14.
- [x] Plan pierwszych 10 kont do 30.11: marketing/plan-10-kont.md, przyjęty wariant B (2026-11-18)
- [ ] Zdecyduj go/no-go dla Opisarni | kto: ty | kiedy: 2026-12-23
  cel: decyzja go, zamrożenie albo pivot zapisana w DECYZJE.md
  gotowe gdy: w DECYZJE.md wpis z 2026-12-23 z liczbami z metryki.md (punkt 3) i wybraną drogą
  materiał: metryki.md#1
  materiał: metryki.md#3
  materiał: KARTA.md#Definicja ukończenia
  Reguła: co najmniej 3 płacących i 20 aktywnych → go; inaczej zamrożenie albo pivot.

## Etap: Pierwsze 10 kont (wariant B)
termin: 2026-11-30

- [x] Sprawdź rejestrację na telefonie: mail weryfikacyjny dochodzi (działa od 2026-11-18, potwierdził właściciel)
- [ ] Załóż tabelę dziennego pomiaru z planu (pkt 8) | kto: ty | kiedy: 2026-11-19 | czas: 5
  cel: jedno miejsce na dzienne liczby kontaktów i kont od 19.11 do 30.11
  gotowe gdy: tabela z punktu 8 planu ma wiersze 19.11–30.11 i wpisane liczby z 19.11
  materiał: marketing/plan-10-kont.md#8
  Tabela zawiera tylko liczby; nazwiska i adresy wyłącznie w marketing/outreach/rejestr-zgod.md (plan, pkt 9).
- [ ] Wyślij zaproszenia LinkedIn do 8 firm z partii 1 | kto: ty | kiedy: 2026-11-19 | czas: 20
  cel: 8 zaproszeń do osób decyzyjnych w firmach z partii 1
  gotowe gdy: w tabeli z punktu 8 planu wpisane „Zaproszenia wysłane: 8” przy 19.11
  materiał: marketing/plan-10-kont.md#5
  - [ ] Kedameble
  - [ ] Bambooko
  - [ ] Meble z Polski 24
  - [ ] PLMEBLE
  - [ ] DANZZ
  - [ ] RaWood
  - [ ] STIPA
  - [ ] Smartwood
  Przed zaproszeniem 2 minuty na sprawdzenie, czy firma działa i nie ma już opisów po niemiecku. Zaproszenie bez oferty.
- [ ] Wyślij wiadomość do 5 znajomych z branży (wariant B, tura 1) | kto: ty | kiedy: 2026-11-20 | czas: 15
  cel: 5 osób z branży, które znasz osobiście, dostaje link do darmowego konta
  gotowe gdy: 5 wiadomości wysłanych; w tabeli z punktu 8 przy 20.11 wpisane „Linki podane: 5”
  materiał: marketing/plan-10-kont.md#5
  Szkic „wiadomości do znajomego z branży” jest na końcu punktu 5. Listę osób znasz tylko Ty.
- [ ] Odpowiedz na komentarze pod postem 1 | kto: ty | kiedy: 2026-11-20 | czas: 10
  cel: każdy komentarz pod postem z 19.11 ma odpowiedź
  gotowe gdy: pod postem 1 na LinkedIn i Facebooku nie ma komentarza bez odpowiedzi
  materiał: marketing/plan-10-kont.md#4
  Szkic odpowiedzi „jak to wypróbować” jest w punkcie 4.
- [ ] Wyślij zaproszenia LinkedIn do 8 firm z partii 2 | kto: ty | kiedy: 2026-11-21 | czas: 20
  cel: 8 zaproszeń do osób decyzyjnych w firmach z partii 2
  gotowe gdy: w tabeli z punktu 8 planu wpisane „Zaproszenia wysłane: 8” przy 21.11
  materiał: marketing/plan-10-kont.md#5
  - [ ] ERMA Meble
  - [ ] ATB Meble
  - [ ] Alan Meble
  - [ ] Meble North
  - [ ] Shik
  - [ ] Miloni
  - [ ] VERYSIMPL
  - [ ] Lano Meble
- [ ] Wyślij wiadomość 1 do osób z partii 1, które przyjęły zaproszenie | kto: ty | kiedy: 2026-11-21 | czas: 20
  cel: każda osoba, która przyjęła zaproszenie, dostaje pytanie bez linku
  gotowe gdy: w tabeli z punktu 8 przy 21.11 wpisane liczby „Przyjęte” i „Rozmowy”
  materiał: marketing/plan-10-kont.md#5
  Zdanie o firmie weź z pierwszego akapitu jej draftu w marketing/outreach/drafts/. Link dopiero po odpowiedzi „tak” (wiadomość 2).
- [ ] Napisz 5 komentarzy pod cudzymi postami o Allegro i eksporcie mebli | kto: ty | kiedy: 2026-11-22 | czas: 30
  cel: wyjście poza własną sieć kontaktów bez kosztów
  gotowe gdy: 5 merytorycznych komentarzy pod postami 5 różnych autorów, bez linku do Opisarni
  materiał: marketing/plan-10-kont.md#10
- [ ] Wyślij wiadomość do 5 kolejnych znajomych z branży (wariant B, tura 2) | kto: ty | kiedy: 2026-11-23 | czas: 15
  cel: kolejne 5 osób z branży dostaje link do darmowego konta
  gotowe gdy: 5 wiadomości wysłanych; w tabeli z punktu 8 przy 23.11 wpisane „Linki podane”
  materiał: marketing/plan-10-kont.md#5
- [ ] Wyślij zaproszenia LinkedIn do 8 firm z partii 3 | kto: ty | kiedy: 2026-11-24 | czas: 20
  cel: 8 zaproszeń do osób od e-commerce lub marketingu w firmach z partii 3
  gotowe gdy: w tabeli z punktu 8 planu wpisane „Zaproszenia wysłane: 8” przy 24.11
  materiał: marketing/plan-10-kont.md#5
  - [ ] Meble Emilia
  - [ ] Brattex
  - [ ] Vilmax
  - [ ] OneLoft
  - [ ] Ramaro
  - [ ] New Elegance
  - [ ] Comforteo
  - [ ] MGK Meble
  Większe firmy: szukaj osoby od e-commerce lub marketingu, nie właściciela.
- [ ] Wyślij wiadomość 1 do nowych kontaktów z partii 1 i 2 | kto: ty | kiedy: 2026-11-24 | czas: 15
  cel: każda osoba, która przyjęła zaproszenie po 21.11, dostaje pytanie bez linku
  gotowe gdy: w tabeli z punktu 8 przy 24.11 wpisane liczby „Przyjęte” i „Rozmowy”
  materiał: marketing/plan-10-kont.md#5
- [ ] Wyślij przypomnienia do partii 1 tam, gdzie była rozmowa | kto: ty | kiedy: 2026-11-25 | czas: 10
  cel: jedno przypomnienie do osób z partii 1, które rozmawiały, a nie założyły konta
  gotowe gdy: każda rozmowa z partii 1 bez konta ma jedno przypomnienie; brak odpowiedzi kończy kontakt
  materiał: marketing/plan-10-kont.md#5
- [ ] Policz konta na punkt kontrolny 25.11 | kto: ty | kiedy: 2026-11-25 | czas: 10
  cel: decyzja, czy uruchomić rezerwę z punktu 7 planu
  gotowe gdy: liczba kont z 25.11 wpisana w tabeli z punktu 8; przy wyniku poniżej 4 uruchomiona rezerwa
  materiał: marketing/plan-10-kont.md#7
  materiał: metryki.md#6
  Rezerwa (partia 4): Kerbe Design, Lofthron, Albero Meble, Kverko, Mille Tavoli, Stol Poprosze, Sleep Home, Valor Meble.
  Rezerwa obejmuje też dodatkowy post 28.11 (marketing/linkedin/drafts/2026-06-24-chatgpt-nie-wystarcza-workflow.md).
- [ ] Wyślij wiadomość 1 do kontaktów z partii 3 | kto: ty | kiedy: 2026-11-26 | czas: 15
  cel: każda osoba z partii 3, która przyjęła zaproszenie, dostaje pytanie bez linku
  gotowe gdy: w tabeli z punktu 8 przy 26.11 wpisane liczby „Przyjęte” i „Rozmowy”
  materiał: marketing/plan-10-kont.md#5
- [ ] Odpowiedz na komentarze pod postami 2 i 3 | kto: ty | kiedy: 2026-11-26 | czas: 15
  cel: każdy komentarz pod postami z 23.11 i 25.11 ma odpowiedź
  gotowe gdy: pod postami 2 i 3 nie ma komentarza bez odpowiedzi
  materiał: marketing/plan-10-kont.md#4
- [ ] Wyślij przypomnienia do partii 2 tam, gdzie była rozmowa | kto: ty | kiedy: 2026-11-27 | czas: 10
  cel: jedno przypomnienie do osób z partii 2, które rozmawiały, a nie założyły konta
  gotowe gdy: każda rozmowa z partii 2 bez konta ma jedno przypomnienie; brak odpowiedzi kończy kontakt
  materiał: marketing/plan-10-kont.md#5
- [ ] Wpisz zgody na kontakt mailowy do rejestru zgód | kto: ty | kiedy: 2026-11-27 | czas: 15
  cel: każda zgoda z rozmów na LinkedIn zapisana, zanim użyjesz draftu maila
  gotowe gdy: w marketing/outreach/rejestr-zgod.md każda zgoda ma datę, osobę i podstawę „LinkedIn”; prośby o brak kontaktu jako „opt-out”
  materiał: marketing/outreach/rejestr-zgod.md
  materiał: marketing/plan-10-kont.md#9
- [ ] Wyślij wiadomość do ostatnich znajomych z branży (wariant B, tura 3) | kto: ty | kiedy: 2026-11-28 | czas: 15
  cel: łącznie 10–15 osób z branży dostało link do darmowego konta
  gotowe gdy: wiadomości wysłane; w tabeli z punktu 8 przy 28.11 wpisane „Linki podane”
  materiał: marketing/plan-10-kont.md#5
- [ ] Sprawdź, które nowe konta nie wygenerowały opisu | kto: ty | kiedy: 2026-11-28 | czas: 10
  cel: lista kont bez pierwszej generacji do krótkiej wiadomości 29.11
  gotowe gdy: liczba kont bez udanej generacji wpisana w tabeli z punktu 8 przy 28.11
  materiał: metryki.md#6
  Konto bez wygenerowanego opisu nie liczy się do celu 20 aktywnych (plan, pkt 10).
- [ ] Wyślij krótką wiadomość do nowych kont bez generacji | kto: ty | kiedy: 2026-11-29 | czas: 15
  cel: osoby z kontem, ale bez opisu, generują pierwszy opis
  gotowe gdy: każda osoba z listy z 28.11, z którą już rozmawiasz, dostała jedną wiadomość
  materiał: marketing/plan-10-kont.md#3
  Tylko do osób, z którymi już rozmawiasz.
- [ ] Uzupełnij tabelę kanałów w metryki.md | kto: ty | kiedy: 2026-11-29 | czas: 15
  cel: wiadomo, który kanał dał konta przed checkpointem 30.11
  gotowe gdy: w metryki.md, punkt 4, wiersze T3 i T4 mają publikacje, wyświetlenia, kliknięcia i nowe konta dla LinkedIn, Facebooka i filmów
  materiał: metryki.md#4
- [ ] Wpisz pomiar checkpointu 30.11 do metryki.md | kto: ty | kiedy: 2026-11-30 | czas: 10
  cel: liczba kont Free na checkpoint 30.11 z produkcji
  gotowe gdy: w metryki.md, punkt 3, wiersz 2026-11-30 ma liczby we wszystkich kolumnach
  materiał: metryki.md#3
  materiał: metryki.md#6
- [ ] Zdecyduj o kanałach na grudzień według progu z planu (pkt 8) | kto: ty | kiedy: 2026-11-30 | czas: 10
  cel: decyzja, które kanały zostają, a które wymieniasz
  gotowe gdy: w DECYZJE.md wpis z 2026-11-30 z liczbą kont i wybranym wariantem z tabeli „Decyzja 30.11”
  materiał: marketing/plan-10-kont.md#8
  materiał: KARTA.md#Definicja ukończenia
  Progi: 10 i więcej kont: kanały zostają; 5–9: zostaje najlepszy kanał; 0–4: zmiana kanałów, najpierw sprawdzenie rejestracji.

## Do rozplanowania

- [ ] Popraw stan ZDJ-1 w plikach zadań repozytorium | kto: claude | gdzie: chmura
  cel: pliki zadań w repozytorium opisują ZDJ-1 jako zmergowane za flagą (#126–#134), nie jako bez merge
  gotowe gdy: żaden plik w tasks/ nie opisuje ZDJ-1 jako niezmergowanego; zmiana w jednym commicie
  materiał: tasks/README.md
- [ ] Zaktualizuj tasks/README.md do stanu z listopada | kto: claude | gdzie: chmura
  cel: tasks/README.md opisuje bieżący stan prac zamiast stanu z czerwca
  gotowe gdy: README nie zawiera nieaktualnych zadań z czerwca i wskazuje ZADANIA.md karty jako listę zadań
  materiał: tasks/README.md
- [ ] Zapisz PoC widoku „Pokaz” w commicie na gałęzi feat/pokaz-opisarnia | kto: claude | gdzie: chmura
  cel: 778 niezacommitowanych zmian PoC zapisanych na gałęzi, bez merge do master
  gotowe gdy: `git status` na gałęzi feat/pokaz-opisarnia jest czysty, a ostatni commit opisuje PoC „Pokaz”
  materiał: KARTA.md#Pytania do właściciela
  Jeśli tych zmian nie ma w repozytorium na serwerze (mogą być tylko w kopii PC), oznacz [!] z blokadą.
- [ ] Dopracuj UI widoku „Pokaz” | kto: claude | gdzie: chmura
  cel: widok „Pokaz” z poprawionym UI, gotowy do oceny przez właściciela
  gotowe gdy: zmiany zacommitowane na gałęzi feat/pokaz-opisarnia; w wynik: opis zmian i zrzuty ekranu przed i po
  materiał: KARTA.md#Pytania do właściciela
  Właściciel (2026-11-14, pytanie 5): UI widoku mu się nie podoba i wymaga poprawy. Gdy brak wskazówek, co zmienić, zapytaj w KARTA.md.
- [ ] Spłać dług a11y w nawigacji i drawerze | kto: claude
  cel: drawer i nawigacja zgodne z wymaganiami dostępności
  gotowe gdy: oba kroki zrobione i testy frontendu zielone
  - [ ] drawer: overlay i aria-modal
  - [ ] nawigacja: role menu
- [ ] Spłać dług zależności w CI | kto: claude
  cel: gate CI bez wyjątków dla znanych podatności zależności
  gotowe gdy: oba kroki zrobione i CI zielone bez wyjątku pip
  - [ ] zaktualizuj vite z wersji 5.x
  - [ ] usuń wyjątek pip w gate CI
- [x] Przygotować post na 2026-11-19 (stały rytm) | kto: claude | gdzie: chmura | kiedy: 2026-11-18
