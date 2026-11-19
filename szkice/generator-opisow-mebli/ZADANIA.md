# Zadania: Opisarnia (generator opisów mebli)

> Jedyna lista zadań projektu. Czyta ją panel i agenci.
> Wiersz: `- [ ] Tytuł | kto: claude | gdzie: pc | kiedy: RRRR-MM-DD | pora: noc | czas: 30 | wymaga: zgoda`
> Stany: `[ ]` do zrobienia, `[~]` w toku, `[!]` zablokowane (dodaj `blokada: powód`), `[x]` zrobione.
> Pola są opcjonalne. kto: claude, codex, ty. gdzie: pc, mac, chmura. pora: dzień, noc. czas: minuty Twojej pracy. wymaga: zgoda, odbiór.
> Etap to nagłówek `## Etap: nazwa` i wiersz `termin: RRRR-MM-DD` pod nim. Etap bez otwartych zadań jest zamknięty.
> Szczegóły zadania: wcięte wiersze pod zadaniem (cel:, gotowe gdy:, materiał:, kroki `- [ ]`, wynik:, decyzja:, zostało:).
> Ścieżki w „materiał:” są względem repozytorium Opisarni albo folderu karty (KARTA.md, STYL.md, kampanie/).
> Publikacje (posty i filmy) i nagrania filmów są w `kampanie/staly-rytm.md`; tu zostają kontakty i pomiary.
> Pole `po:` wskazuje zadania z tego pliku, które muszą być zrobione wcześniej. Stan kontaktu z firmą: marketing/kontakty.md.

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
termin: 2026-11-25

- [x] SEC-3, SEC-5, SEC-1: zależności, sekrety i RODO, SAST backendu (2026-06-16)
- [~] Zamknij SEC-2: SAST frontendu (XSS, open redirect, storage, CSP) | kto: claude | gdzie: chmura | kiedy: 2026-11-20 | wymaga: odbiór
  cel: frontend bez znalezisk CRITICAL, HIGH i MEDIUM z SAST (XSS, open redirect, storage, CSP)
  gotowe gdy: raport SEC-2 odebrany przez właściciela; commit i wdrożenie poprawek w zadaniach następczych poniżej
  materiał: docs/security/raport-audytu.md
  wynik: re-audyt 2026-11-18: 0 CRITICAL, 0 HIGH, 0 MEDIUM; 3 LOW naprawione w kodzie
  decyzja: odebrać raport SEC-2 i zgodzić się na commit poprawek 3 LOW
  zostało: poprawki niezacommitowane; testy frontendu nieuruchomione (brak Node.js na serwerze)
- [~] Zamknij SEC-4: infra, nagłówki bezpieczeństwa, CORS, rate-limit | kto: claude | gdzie: chmura | kiedy: 2026-11-20 | wymaga: odbiór
  cel: infrastruktura bez znalezisk CRITICAL i HIGH; nagłówki, CORS i limity zgodne z raportem
  gotowe gdy: raport SEC-4 odebrany przez właściciela; commit i wdrożenie poprawek w zadaniach następczych poniżej
  materiał: docs/security/raport-audytu.md
  wynik: re-audyt 2026-11-18: 0 CRITICAL, 0 HIGH; 1 MEDIUM (brak limitu body na Caddy) i 2 LOW naprawione w repo; 2 LOW zapisane jako dług
  decyzja: odebrać raport SEC-4 i zgodzić się na commit oraz wdrożenie limitu body na Caddy
  zostało: poprawki niezacommitowane i niewdrożone; `caddy validate` i pytest nieuruchomione (brak uprawnień)
- [ ] Zapisz poprawki SEC-2 (3 LOW) na gałęzi uruchomienia | kto: claude | gdzie: chmura | kiedy: 2026-11-21 | po: Zamknij SEC-2
  cel: poprawki 3 LOW z SAST frontendu zapisane na gałęzi uruchomienia, gotowe do scalenia w panelu
  gotowe gdy: poprawki 3 LOW są w katalogu uruchomienia (panel zapisuje gałąź i listę zmian); testy frontendu zielone
  materiał: docs/security/raport-audytu.md
  Poprawki z re-audytu leżą niezacommitowane w głównym katalogu repozytorium (/home/panel/projekty/generator-opisow-mebli), poza katalogiem uruchomienia.
  Przenieś je stamtąd (`git -C /home/panel/projekty/generator-opisow-mebli diff -- <pliki frontendu>`); gdy nie masz dostępu, nanieś 3 LOW ponownie według raportu.
  Bez Node.js na serwerze testów frontendu nie uruchomisz: wtedy [!] z blokadą „brak Node.js do testów frontendu”, poprawki zostają w katalogu uruchomienia.
- [ ] Zapisz poprawki SEC-4 (limit body Caddy, 2 LOW) na gałęzi uruchomienia | kto: claude | gdzie: chmura | kiedy: 2026-11-21 | po: Zamknij SEC-4
  cel: limit body na Caddy i poprawki 2 LOW zapisane na gałęzi uruchomienia, gotowe do scalenia w panelu
  gotowe gdy: zmiany są w katalogu uruchomienia (panel zapisuje gałąź i listę zmian); `caddy validate` i pytest zielone
  materiał: docs/security/raport-audytu.md
  Poprawki leżą niezacommitowane w głównym katalogu repozytorium; przenieś je jak przy SEC-2 albo nanieś ponownie według raportu.
  Gdy `caddy validate` albo pytest nie da się uruchomić (brak uprawnień): [!] z blokadą i poleceniem, które trzeba dopuścić.
- [ ] Przejrzyj zmiany agenta SEC-2 i SEC-4 i scal w panelu | kto: ty | kiedy: 2026-11-22 | czas: 15 | po: Zapisz poprawki SEC-2, Zapisz poprawki SEC-4
  cel: poprawki SEC-2 i SEC-4 w gałęzi master repozytorium Opisarni na serwerze
  gotowe gdy: oba uruchomienia scalone w panelu do master (bez push); w notatce pod zadaniem liczba zmienionych plików
  materiał: docs/security/raport-audytu.md
  - [ ] panel, Agenci: uruchomienie „Zapisz poprawki SEC-2…”, lista zmian i diff przejrzane, scalone
  - [ ] to samo dla „Zapisz poprawki SEC-4…”
  Gdy scalenie zwraca 409 przez niezacommitowane zmiany w głównym katalogu: `ssh ops@2.29.181.133`, potem
  `sudo -u panel git -C /home/panel/projekty/generator-opisow-mebli stash push -m sec-przed-scaleniem` i scal ponownie.
- [ ] Wdróż poprawki SEC-2 i SEC-4 na produkcję | kto: ty | kiedy: 2026-11-22 | czas: 20 | po: Przejrzyj zmiany agenta SEC-2 i SEC-4
  cel: poprawki SEC-2 i limit body na Caddy działają na opisarnia.pl
  gotowe gdy: master z poprawkami na GitHubie, CI i auto-deploy zielone, `caddy validate` na serwerze Opisarni zielone, opisarnia.pl odpowiada
  - [ ] `ssh ops@2.29.181.133`, `sudo -u panel git -C /home/panel/projekty/generator-opisow-mebli push origin master`
  - [ ] GitHub, zakładka Actions repozytorium Opisarni: CI i auto-deploy zielone
  - [ ] serwer Opisarni: `docker compose -f docker-compose.prod.yml exec caddy caddy validate --config /etc/caddy/Caddyfile`, potem `caddy reload` tym samym poleceniem
  - [ ] `curl -sI https://opisarnia.pl` zwraca 200 i nagłówki Content-Security-Policy oraz Strict-Transport-Security
  Nazwa usługi Caddy i ścieżka Caddyfile według docker-compose.prod.yml; push uruchamia auto-deploy (#70).

## Etap: Testy

- [x] Testy E2E (VI–VII, według historii commitów)

## Etap: Produkcja
termin: 2026-11-17

- [ ] Unieważnij testowy klucz API Mistral wklejony do rozmowy 26.10 | kto: ty | kiedy: 2026-11-19 | czas: 5
  cel: klucz Mistral z historii rozmowy przestaje działać
  gotowe gdy: klucz ma w konsoli Mistral stan unieważniony, a zapasowy silnik Opisarni działa na innym kluczu
  - [ ] console.mistral.ai → API Keys: sprawdź, czy klucz z 26.10 (ostatnie znaki jak w rozmowie) jest kluczem produkcji
  - [ ] gdy tak: utwórz nowy klucz, wpisz go w pliku .env produkcji Opisarni (zmienna z kluczem Mistral), `docker compose -f docker-compose.prod.yml up -d backend`
  - [ ] console.mistral.ai → API Keys: przy kluczu z 26.10 „Revoke” albo „Delete”
  - [ ] po zmianie: jedna generacja na opisarnia.pl działa (Haiku); zapasowy Mistral nie zgłasza błędu 401 w logach backendu
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
  Jak: Anthropic: anthropic.com/legal, DPA jest częścią warunków komercyjnych API; zapisz wersję i datę przy kroku.
  Mistral: mistral.ai/terms, sekcja Data Processing Agreement; zapisz wersję i datę przy kroku.
  Regulamin i polityka: stopka opisarnia.pl, w każdym dokumencie wyszukaj „Anthropic” i „Mistral” (Cmd+F).
  Gdy dostawcy brakuje w dokumencie: zadanie dla Claude „Dopisz Anthropic i Mistral do regulaminu i polityki prywatności”; wdrożenie po Twojej zgodzie.
  Wszystkie wiadomości do ludzi (zaproszenia, wiadomości, przypomnienia) i publikacje w kampanie/staly-rytm.md czekają na to zadanie (po:); komentarze: pytanie 13 w KARTA.md.

## Etap: Walidacja i marketing
termin: 2026-12-23

- [x] Opublikować pierwsze posty LinkedIn (2026-06-08, 2026-06-12)
- [x] Bramka ADR 0001 zastąpiona celami do 23.12 (2026-10-27; 200 adresów nie zebrano, Brevo wyłączył klucz SMTP 14.10)
- [x] Metryki: metryki.md w repozytorium, pomiar startowy 2026-11-18: 0 kont, 0 aktywnych, 0 płacących
- [ ] Wpisz pomiar tygodniowy do metryki.md | kto: ty | kiedy: 2026-11-23 | czas: 10
  cel: liczby produktu z 23.11 (konta, aktywne, płacący, MRR) z produkcji, podstawa decyzji go/no-go
  gotowe gdy: w metryki.md, punkt 3, wiersz 2026-11-23 ma liczby w kolumnach konta Free, nowe konta, aktywne, płacący i MRR
  materiał: metryki.md#3
  materiał: metryki.md#6
  Pomiar co poniedziałek; kolejne: 2026-11-30 (checkpoint), 2026-12-07, 2026-12-14.
  Bez licznika: konta w kampanii liczą zadania 25.11 i 30.11 (przyrost), żeby wynik kampanii nie liczył kont dwa razy.
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

> Liczby kontaktów i kont zbiera pole `licznik:`: przy „Zrobione” podajesz liczbę, panel dopisuje ją w kampanie/staly-rytm.md, sekcja „Wyniki i wnioski”.
> Licznik liczy przyrost od poprzedniego zadania z tym samym licznikiem. Wiadomości do ludzi czekają na „Potwierdź DPA” (po:).

- [x] Sprawdź rejestrację na telefonie: mail weryfikacyjny dochodzi (działa od 2026-11-18, potwierdził właściciel)
- [x] Załóż rejestr kontaktów marketing/kontakty.md bez nazwisk | kto: claude | gdzie: chmura | kiedy: 2026-11-19
  wynik: powstał marketing/kontakty.md: 10 wymaganych kolumn, 32 wiersze (po 8 firm w partiach 1–3 i 8 firm rezerwy w partii 4), wszystkie komórki stanu startowo „nie”, bez nazwisk, stanowisk i adresów; plik jest dodany do indeksu na gałęzi agent/2026-11-19-rejestr-kontaktow, bez commita
  zostało: commit nie powstał, bo w repozytorium nie ma ustawionej tożsamości git (user.name, user.email), a polecenie z tożsamością podaną jednorazowo wymagało zgody; na gałęzi agent/2026-11-19-rejestr-kontaktow wystarczy `git commit -m "docs(marketing): rejestr kontaktów partii 1–4"` (plik jest już w indeksie)
  cel: jedna tabela stanu kontaktu z każdą firmą z partii 1–4, bez nazwisk i adresów
  gotowe gdy: marketing/kontakty.md ma kolumny firma, partia, zaproszenie, przyjęte, wiadomość 1, odpowiedź, link, konto, przypomnienie, koniec oraz po jednym wierszu dla 24 firm z partii 1–3 i 8 firm rezerwy (partia 4)
  materiał: marketing/plan-10-kont.md#5
  materiał: marketing/plan-10-kont.md#7
  materiał: marketing/plan-10-kont.md#9
  Bez nazwisk, stanowisk i adresów: dane osobowe tylko w marketing/outreach/rejestr-zgod.md. W kolumnach daty RRRR-MM-DD albo „tak”/„nie”.
- [ ] Scal rejestr kontaktów z gałęzi agent/2026-11-19-rejestr-kontaktow | kto: ty | kiedy: 2026-11-19 | czas: 5
  cel: marketing/kontakty.md jest w master repozytorium Opisarni, więc zadania kontaktowe i agenci go widzą
  gotowe gdy: `git log -1 -- marketing/kontakty.md` na master repozytorium na serwerze pokazuje commit z rejestrem
  - [ ] `ssh ops@2.29.181.133`; w repozytorium /home/panel/projekty/generator-opisow-mebli ustaw `git config user.name` i `user.email` (jako panel)
  - [ ] w katalogu uruchomienia gałęzi agent/2026-11-19-rejestr-kontaktow: `sudo -u panel git commit -m "docs(marketing): rejestr kontaktów partii 1–4"`
  - [ ] panel, Agenci: uruchomienie „Załóż rejestr kontaktów…”, diff przejrzany, scalone do master
  Plik leży w indeksie gałęzi bez commita (zostało: zadania „Załóż rejestr kontaktów…”), dlatego scalenie w panelu wymaga najpierw commita.
- [ ] Przygotuj szkice wiadomości 1 dla 24 firm z partii 1–3 | kto: claude | gdzie: chmura | kiedy: 2026-11-20
  cel: przy każdej firmie z partii 1–3 gotowa wiadomość 1 ze zdaniem o tej firmie, do skopiowania bez poprawek
  gotowe gdy: plik wiadomosci/wiadomosc-1-partie-1-3.md w folderze karty ma 24 sekcje (firma, partia, wiadomość 1 ze szkicu z punktu 5 planu ze zdaniem z pierwszego akapitu draftu firmy); bez nazwisk i adresów; nic nie wysłane
  materiał: marketing/plan-10-kont.md#5
  materiał: marketing/outreach/drafts/
  materiał: STYL.md
  Firma bez draftu w marketing/outreach/drafts/: zdanie z punktu 5 planu (kolumna „Dlaczego te”) i dopisek „bez draftu” w sekcji.
- [ ] Przygotuj 8 tez do komentarzy pod postami o Allegro i eksporcie mebli | kto: claude | gdzie: chmura | kiedy: 2026-11-21
  cel: właściciel ma gotowe merytoryczne tezy, które dopasowuje do cudzych postów w 5 minut
  gotowe gdy: plik wiadomosci/komentarze-tezy.md w folderze karty ma 8 tez po 2–3 zdania, każda z jednym faktem albo liczbą z planu lub draftów postów, bez linku i bez nazwy Opisarni; nic nie opublikowane
  materiał: marketing/plan-10-kont.md#10
  materiał: marketing/linkedin/drafts/
  materiał: STYL.md
- [ ] Przygotuj szkic wiadomości do kont bez pierwszej generacji | kto: claude | gdzie: chmura | kiedy: 2026-11-27
  cel: krótka wiadomość, po której osoba z kontem generuje pierwszy opis
  gotowe gdy: plik wiadomosci/konta-bez-generacji.md w folderze karty ma szkic do 400 znaków z jednym krokiem (typ, wymiary, materiał, „Generuj”) i pytaniem, co przeszkodziło; oferta zgodna z punktem 2 planu; nic nie wysłane
  materiał: marketing/plan-10-kont.md#2
  materiał: marketing/plan-10-kont.md#3
  materiał: STYL.md
- [ ] Wyślij zaproszenia LinkedIn do 8 firm z partii 1 | kto: ty | kiedy: 2026-11-19 | czas: 20 | po: Potwierdź DPA, Scal rejestr kontaktów | licznik: zaproszenia
  cel: 8 zaproszeń do osób decyzyjnych w firmach z partii 1
  gotowe gdy: każda z 8 firm ma zaznaczony krok: zaproszenie wysłane albo notatkę, dlaczego nie (firma nie działa, ma już opisy po niemiecku)
  materiał: marketing/plan-10-kont.md#5
  materiał: marketing/kontakty.md
  - [ ] Kedameble
  - [ ] Bambooko
  - [ ] Meble z Polski 24
  - [ ] PLMEBLE
  - [ ] DANZZ
  - [ ] RaWood
  - [ ] STIPA
  - [ ] Smartwood
  Przed zaproszeniem 2 minuty na sprawdzenie, czy firma działa i nie ma już opisów po niemiecku. Zaproszenie bez oferty.
  marketing/kontakty.md: plik powstanie w master w zadaniu „Scal rejestr kontaktów…” (dziś tylko na gałęzi agenta).
- [ ] Wyślij wiadomość do 5 znajomych z branży (wariant B, tura 1) | kto: ty | kiedy: 2026-11-20 | czas: 15 | po: Potwierdź DPA | licznik: linki
  cel: 5 osób z branży, które znasz osobiście, dostaje link do darmowego konta
  gotowe gdy: 5 osób z branży dostało wiadomość z linkiem opisarnia.pl/rejestracja
  materiał: marketing/plan-10-kont.md#5
  Szkic „wiadomości do znajomego z branży” jest na końcu punktu 5. Listę osób znasz tylko Ty.
- [ ] Odpowiedz na komentarze pod postem 1 | kto: ty | kiedy: 2026-11-20 | czas: 10
  cel: każdy komentarz pod postem z 19.11 ma odpowiedź
  gotowe gdy: pod postem 1 na LinkedIn i Facebooku nie ma komentarza bez odpowiedzi
  materiał: marketing/plan-10-kont.md#4
  Szkic odpowiedzi „jak to wypróbować” jest w punkcie 4.
- [ ] Wyślij zaproszenia LinkedIn do 8 firm z partii 2 | kto: ty | kiedy: 2026-11-21 | czas: 20 | po: Potwierdź DPA, Scal rejestr kontaktów | licznik: zaproszenia
  cel: 8 zaproszeń do osób decyzyjnych w firmach z partii 2
  gotowe gdy: każda z 8 firm ma zaznaczony krok: zaproszenie wysłane albo notatkę, dlaczego nie (firma nie działa, ma już opisy po niemiecku)
  materiał: marketing/plan-10-kont.md#5
  materiał: marketing/kontakty.md
  - [ ] ERMA Meble
  - [ ] ATB Meble
  - [ ] Alan Meble
  - [ ] Meble North
  - [ ] Shik
  - [ ] Miloni
  - [ ] VERYSIMPL
  - [ ] Lano Meble
  marketing/kontakty.md: plik powstanie w master w zadaniu „Scal rejestr kontaktów…”.
- [ ] Wyślij wiadomość 1 do osób z partii 1, które przyjęły zaproszenie | kto: ty | kiedy: 2026-11-21 | czas: 20 | po: Wyślij zaproszenia LinkedIn do 8 firm z partii 1, Przygotuj szkice wiadomości 1, Potwierdź DPA | licznik: przyjęte
  cel: każda osoba, która przyjęła zaproszenie, dostaje pytanie bez linku
  gotowe gdy: każda osoba z partii 1, która przyjęła zaproszenie, dostała wiadomość 1 bez linku
  materiał: wiadomosci/wiadomosc-1-partie-1-3.md
  materiał: marketing/plan-10-kont.md#5
  materiał: marketing/kontakty.md
  Licznik: liczba osób, które przyjęły zaproszenie. wiadomosci/wiadomosc-1-partie-1-3.md: plik powstanie w zadaniu „Przygotuj szkice wiadomości 1…”. Link dopiero po odpowiedzi „tak” (wiadomość 2).
- [ ] Napisz 5 komentarzy pod cudzymi postami o Allegro i eksporcie mebli | kto: ty | kiedy: 2026-11-22 | czas: 30 | po: Przygotuj 8 tez do komentarzy
  cel: wyjście poza własną sieć kontaktów bez kosztów
  gotowe gdy: 5 merytorycznych komentarzy pod postami 5 różnych autorów, bez linku do Opisarni
  materiał: wiadomosci/komentarze-tezy.md
  materiał: marketing/plan-10-kont.md#10
  wiadomosci/komentarze-tezy.md: plik powstanie w zadaniu „Przygotuj 8 tez do komentarzy…”.
- [ ] Wyślij wiadomość do 5 kolejnych znajomych z branży (wariant B, tura 2) | kto: ty | kiedy: 2026-11-23 | czas: 15 | po: Wyślij wiadomość do 5 znajomych z branży, Potwierdź DPA | licznik: linki
  cel: kolejne 5 osób z branży dostaje link do darmowego konta
  gotowe gdy: 5 kolejnych osób z branży dostało wiadomość z linkiem opisarnia.pl/rejestracja
  materiał: marketing/plan-10-kont.md#5
- [ ] Wyślij zaproszenia LinkedIn do 8 firm z partii 3 | kto: ty | kiedy: 2026-11-24 | czas: 20 | po: Potwierdź DPA, Scal rejestr kontaktów | licznik: zaproszenia
  cel: 8 zaproszeń do osób od e-commerce lub marketingu w firmach z partii 3
  gotowe gdy: każda z 8 firm ma zaznaczony krok: zaproszenie wysłane albo notatkę, dlaczego nie (firma nie działa, ma już opisy po niemiecku)
  materiał: marketing/plan-10-kont.md#5
  materiał: marketing/kontakty.md
  - [ ] Meble Emilia
  - [ ] Brattex
  - [ ] Vilmax
  - [ ] OneLoft
  - [ ] Ramaro
  - [ ] New Elegance
  - [ ] Comforteo
  - [ ] MGK Meble
  Większe firmy: szukaj osoby od e-commerce lub marketingu, nie właściciela.
  marketing/kontakty.md: plik powstanie w master w zadaniu „Scal rejestr kontaktów…”.
- [ ] Wyślij wiadomość 1 do nowych kontaktów z partii 1 i 2 | kto: ty | kiedy: 2026-11-24 | czas: 15 | po: Wyślij zaproszenia LinkedIn do 8 firm z partii 2, Przygotuj szkice wiadomości 1, Potwierdź DPA | licznik: przyjęte
  cel: każda osoba, która przyjęła zaproszenie po 21.11, dostaje pytanie bez linku
  gotowe gdy: każda osoba z partii 1 i 2, która przyjęła zaproszenie po 21.11, dostała wiadomość 1 bez linku
  materiał: wiadomosci/wiadomosc-1-partie-1-3.md
  materiał: marketing/plan-10-kont.md#5
  materiał: marketing/kontakty.md
  Licznik: liczba osób, które przyjęły zaproszenie po 21.11.
- [ ] Wyślij przypomnienia do partii 1 tam, gdzie była rozmowa | kto: ty | kiedy: 2026-11-25 | czas: 10 | po: Wyślij wiadomość 1 do osób z partii 1, Potwierdź DPA | licznik: rozmowy
  cel: jedno przypomnienie do osób z partii 1, które rozmawiały, a nie założyły konta
  gotowe gdy: każda rozmowa z partii 1 bez konta ma jedno przypomnienie; brak odpowiedzi kończy kontakt
  materiał: marketing/plan-10-kont.md#5
  materiał: marketing/kontakty.md
  Licznik: liczba rozmów z partii 1 (osoby, które odpisały na wiadomość 1).
- [ ] Policz konta na punkt kontrolny 25.11 | kto: ty | kiedy: 2026-11-25 | czas: 10 | licznik: konta
  cel: decyzja, czy uruchomić rezerwę z punktu 7 planu
  gotowe gdy: liczba kont Free z 25.11 (bez własnych i testowych) podana przy zamknięciu; przy wyniku poniżej 4 w notatce pod zadaniem decyzja o rezerwie
  materiał: marketing/plan-10-kont.md#7
  materiał: metryki.md#6
  Licznik: konta Free razem na 25.11 (start 18.11: 0, więc to przyrost).
  Rezerwa (partia 4): Kerbe Design, Lofthron, Albero Meble, Kverko, Mille Tavoli, Stol Poprosze, Sleep Home, Valor Meble.
  Rezerwa obejmuje też dodatkowy post 28.11 (marketing/linkedin/drafts/2026-06-24-chatgpt-nie-wystarcza-workflow.md).
- [ ] Wyślij wiadomość 1 do kontaktów z partii 3 | kto: ty | kiedy: 2026-11-26 | czas: 15 | po: Wyślij zaproszenia LinkedIn do 8 firm z partii 3, Przygotuj szkice wiadomości 1, Potwierdź DPA | licznik: przyjęte
  cel: każda osoba z partii 3, która przyjęła zaproszenie, dostaje pytanie bez linku
  gotowe gdy: każda osoba z partii 3, która przyjęła zaproszenie, dostała wiadomość 1 bez linku
  materiał: wiadomosci/wiadomosc-1-partie-1-3.md
  materiał: marketing/plan-10-kont.md#5
  materiał: marketing/kontakty.md
  Licznik: liczba osób z partii 3, które przyjęły zaproszenie.
- [ ] Odpowiedz na komentarze pod postami 2 i 3 | kto: ty | kiedy: 2026-11-26 | czas: 15
  cel: każdy komentarz pod postami z 23.11 i 25.11 ma odpowiedź
  gotowe gdy: pod postami 2 i 3 nie ma komentarza bez odpowiedzi
  materiał: marketing/plan-10-kont.md#4
- [ ] Wyślij przypomnienia do partii 2 tam, gdzie była rozmowa | kto: ty | kiedy: 2026-11-27 | czas: 10 | po: Wyślij wiadomość 1 do nowych kontaktów z partii 1 i 2, Potwierdź DPA | licznik: rozmowy
  cel: jedno przypomnienie do osób z partii 2, które rozmawiały, a nie założyły konta
  gotowe gdy: każda rozmowa z partii 2 bez konta ma jedno przypomnienie; brak odpowiedzi kończy kontakt
  materiał: marketing/plan-10-kont.md#5
  materiał: marketing/kontakty.md
  Licznik: liczba rozmów z partii 2.
- [ ] Wpisz zgody na kontakt mailowy do rejestru zgód | kto: ty | kiedy: 2026-11-27 | czas: 15
  cel: każda zgoda z rozmów na LinkedIn zapisana, zanim użyjesz draftu maila
  gotowe gdy: w marketing/outreach/rejestr-zgod.md każda zgoda ma datę, osobę i podstawę „LinkedIn”; prośby o brak kontaktu jako „opt-out”
  materiał: marketing/outreach/rejestr-zgod.md
  materiał: marketing/plan-10-kont.md#9
- [ ] Wyślij wiadomość do ostatnich znajomych z branży (wariant B, tura 3) | kto: ty | kiedy: 2026-11-28 | czas: 15 | po: Wyślij wiadomość do 5 kolejnych znajomych, Potwierdź DPA | licznik: linki
  cel: łącznie 10–15 osób z branży dostało link do darmowego konta
  gotowe gdy: łącznie 10–15 osób z branży (z turami 1 i 2) dostało wiadomość z linkiem opisarnia.pl/rejestracja
  materiał: marketing/plan-10-kont.md#5
- [ ] Sprawdź, które nowe konta nie wygenerowały opisu | kto: ty | kiedy: 2026-11-28 | czas: 10
  cel: lista kont bez pierwszej generacji do krótkiej wiadomości 29.11
  gotowe gdy: lista osób z kontem bez udanej generacji gotowa poza repozytorium (dane osobowe), tylko osoby, z którymi już rozmawiasz
  materiał: metryki.md#6
  Konto bez wygenerowanego opisu nie liczy się do celu 20 aktywnych (plan, pkt 10).
- [ ] Wyślij krótką wiadomość do nowych kont bez generacji | kto: ty | kiedy: 2026-11-29 | czas: 15 | po: które nowe konta nie wygenerowały opisu, Przygotuj szkic wiadomości do kont bez pierwszej generacji, Potwierdź DPA
  cel: osoby z kontem, ale bez opisu, generują pierwszy opis
  gotowe gdy: każda osoba z listy z 28.11, z którą już rozmawiasz, dostała jedną wiadomość
  materiał: wiadomosci/konta-bez-generacji.md
  materiał: marketing/plan-10-kont.md#3
  Tylko do osób, z którymi już rozmawiasz. wiadomosci/konta-bez-generacji.md: plik powstanie w zadaniu „Przygotuj szkic wiadomości do kont bez pierwszej generacji”.
- [ ] Wpisz pomiar checkpointu 30.11 do metryki.md | kto: ty | kiedy: 2026-11-30 | czas: 10 | licznik: konta
  cel: liczba kont Free na checkpoint 30.11 z produkcji
  gotowe gdy: w metryki.md, punkt 3, wiersz 2026-11-30 ma liczby we wszystkich kolumnach
  materiał: metryki.md#3
  materiał: metryki.md#6
  Licznik: nowe konta Free od pomiaru 25.11, więc suma licznika kont w kampanii to stan na 30.11.
- [ ] Zdecyduj o kanałach na grudzień według progu z planu (pkt 8) | kto: ty | kiedy: 2026-11-30 | czas: 10 | po: Wpisz pomiar checkpointu 30.11
  cel: decyzja, które kanały zostają, a które wymieniasz
  gotowe gdy: w DECYZJE.md wpis z 2026-11-30 z liczbą kont i wybranym wariantem z tabeli „Decyzja 30.11”
  materiał: marketing/plan-10-kont.md#8
  materiał: kampanie/staly-rytm.md#Wyniki i wnioski
  materiał: KARTA.md#Definicja ukończenia
  Progi: 10 i więcej kont: kanały zostają; 5–9: zostaje najlepszy kanał; 0–4: zmiana kanałów, najpierw sprawdzenie rejestracji.
  Dane kanałów: wyniki pod wierszami publikacji w kampanie/staly-rytm.md (wyświetlenia, kliknięcia, konta) i liczniki z sekcji „Wyniki i wnioski”.

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
- [~] Przygotować post na 2026-11-20: Opublikuj film A „Opis mebla po polsku i niemiecku w 10 sekund” | kto: claude | gdzie: chmura | kiedy: 2026-11-19 | wymaga: odbiór
  materiał: kampanie/staly-rytm.md
  wynik: w folderze karty powstał posty/2026-11-20-film-a-opis-pl-de/: post.md (opisy pod film na Facebook, LinkedIn i Reels oraz alt) i grafika.svg (plansza z szablonu, zmienione tylko teksty); w kampanie/staly-rytm.md wiersz filmu A dostał materiał: posty/2026-11-20-film-a-opis-pl-de/post.md; folder karty bez repozytorium, więc bez gałęzi i commita
  decyzja: zatwierdzić teksty pod film przed publikacją 20.11; tekst LinkedIn i Facebook opisuje film według scenariusza zastępczego z planu (komoda, profil Allegro, „Generuj”, „Kopiuj”), więc przy innym nagraniu popraw 2–3 zdania
  zostało: film A nie istnieje w repozytorium (nagranie to Twój wiersz „Nagraj film A”, pytanie 6 w KARTA.md bez odpowiedzi); grafika.png zrobi panel; publikacja po Twojej stronie
