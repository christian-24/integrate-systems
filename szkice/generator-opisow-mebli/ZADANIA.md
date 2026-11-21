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
- [x] Zamknij SEC-2: SAST frontendu (XSS, open redirect, storage, CSP) | kto: claude | gdzie: chmura | kiedy: 2026-11-20
  cel: frontend bez znalezisk CRITICAL, HIGH i MEDIUM z SAST (XSS, open redirect, storage, CSP)
  gotowe gdy: raport SEC-2 odebrany przez właściciela; commit i wdrożenie poprawek w zadaniach następczych poniżej
  materiał: docs/security/raport-audytu.md
  wynik: poprawki scalone do master 19.11 (commit 4f68382, bez push); wdrożenie w zadaniu „Wdróż poprawki SEC-2 i SEC-4”
- [x] Zamknij SEC-4: infra, nagłówki bezpieczeństwa, CORS, rate-limit | kto: claude | gdzie: chmura | kiedy: 2026-11-20
  cel: infrastruktura bez znalezisk CRITICAL i HIGH; nagłówki, CORS i limity zgodne z raportem
  gotowe gdy: raport SEC-4 odebrany przez właściciela; commit i wdrożenie poprawek w zadaniach następczych poniżej
  materiał: docs/security/raport-audytu.md
  wynik: poprawki scalone do master 19.11 (commit 4f68382, bez push); wdrożenie w zadaniu „Wdróż poprawki SEC-2 i SEC-4”
- [x] Zapisz poprawki SEC-2 (3 LOW) na gałęzi uruchomienia | kto: claude | gdzie: chmura | kiedy: 2026-11-21 | po: Zamknij SEC-2
  cel: poprawki 3 LOW z SAST frontendu zapisane na gałęzi uruchomienia, gotowe do scalenia w panelu
  gotowe gdy: poprawki 3 LOW są w katalogu uruchomienia (panel zapisuje gałąź i listę zmian); testy frontendu zielone
  materiał: docs/security/raport-audytu.md
  Poprawki z re-audytu leżą niezacommitowane w głównym katalogu repozytorium (/home/panel/projekty/generator-opisow-mebli), poza katalogiem uruchomienia.
  Przenieś je stamtąd (`git -C /home/panel/projekty/generator-opisow-mebli diff -- <pliki frontendu>`); gdy nie masz dostępu, nanieś 3 LOW ponownie według raportu.
  Bez Node.js na serwerze testów frontendu nie uruchomisz: wtedy [!] z blokadą „brak Node.js do testów frontendu”, poprawki zostają w katalogu uruchomienia.
  wynik: zmiany są na gałęzi agent/2026-11-19-sec2-sec4-poprawki (commit 98ca001, razem z SEC-4); testów przy zapisie nie uruchomiono, sprawdzenie przy wdrożeniu
- [x] Zapisz poprawki SEC-4 (limit body Caddy, 2 LOW) na gałęzi uruchomienia | kto: claude | gdzie: chmura | kiedy: 2026-11-21 | po: Zamknij SEC-4
  cel: limit body na Caddy i poprawki 2 LOW zapisane na gałęzi uruchomienia, gotowe do scalenia w panelu
  gotowe gdy: zmiany są w katalogu uruchomienia (panel zapisuje gałąź i listę zmian); `caddy validate` i pytest zielone
  materiał: docs/security/raport-audytu.md
  Poprawki leżą niezacommitowane w głównym katalogu repozytorium; przenieś je jak przy SEC-2 albo nanieś ponownie według raportu.
  Gdy `caddy validate` albo pytest nie da się uruchomić (brak uprawnień): [!] z blokadą i poleceniem, które trzeba dopuścić.
  wynik: zmiany są na gałęzi agent/2026-11-19-sec2-sec4-poprawki (commit 98ca001, razem z SEC-4); testów przy zapisie nie uruchomiono, sprawdzenie przy wdrożeniu
- [x] Przejrzyj zmiany agenta SEC-2 i SEC-4 i scal w panelu | kto: ty | kiedy: 2026-11-22 | czas: 15 | po: Zapisz poprawki SEC-2, Zapisz poprawki SEC-4
  cel: poprawki SEC-2 i SEC-4 w gałęzi master repozytorium Opisarni na serwerze
  gotowe gdy: gałąź scalona w panelu do master (bez push)
  materiał: docs/security/raport-audytu.md
  gałąź: agent/2026-11-19-sec2-sec4-poprawki
  W szczegółach zadania: „Pokaż zmiany” (12 plików, +427 −4), potem „Scal”. Scalenie zamyka zadanie.
  wynik: scalił Claude 19.11 na Twoje polecenie: commit 4f68382 w master na serwerze, 12 plików, bez push
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

- [x] Unieważnij testowy klucz API Mistral wklejony do rozmowy 26.10 | kto: ty | kiedy: 2026-11-19 | czas: 5
  cel: klucz Mistral z historii rozmowy przestaje działać
  gotowe gdy: klucz ma w konsoli Mistral stan unieważniony, a zapasowy silnik Opisarni działa na innym kluczu
  - [x] console.mistral.ai → API Keys: sprawdź, czy klucz z 26.10 (ostatnie znaki jak w rozmowie) jest kluczem produkcji
  - [ ] gdy tak: utwórz nowy klucz, wpisz go w pliku .env produkcji Opisarni (zmienna z kluczem Mistral), `docker compose -f docker-compose.prod.yml up -d backend`
  - [ ] console.mistral.ai → API Keys: przy kluczu z 26.10 „Revoke” albo „Delete”
  - [ ] po zmianie: jedna generacja na opisarnia.pl działa (Haiku); zapasowy Mistral nie zgłasza błędu 401 w logach backendu
  Klucz leży jawnie w historii Claude Code z PC (archiwum rozmów na Macu, ksiega/MIGRACJA.md).
  wynik: Usuniete
- [x] Serwer Hetzner, Caddy z HTTPS, docker-compose.prod (ADR 0004, 0034)
- [x] Auto-deploy przez GitHub Actions (#70)
- [x] Ręczny deploy do #125 (2026-11-03)
- [x] Deploy #126–#134 na produkcję i klucz Anthropic; silnik Haiku działa od 13.11 (potwierdził właściciel 2026-11-14)
- [x] Stripe w trybie live (potwierdził właściciel 2026-11-14)
- [x] JDG w CEIDG (potwierdził właściciel 2026-11-14)
- [x] Potwierdź DPA z dostawcami LLM, regulamin i politykę prywatności | kto: ty | kiedy: 2026-11-17 | czas: 15
  cel: przed płacącymi Opisarnia ma podpisane DPA z dostawcami LLM oraz aktualny regulamin i politykę prywatności
  gotowe gdy: wszystkie kroki zaznaczone, a data akceptacji DPA wpisana przy kroku
  materiał: KARTA.md#Zasoby i ograniczenia
  - [x] DPA Anthropic (silnik Haiku)
  - [x] DPA Mistral (silnik zapasowy)
  - [x] regulamin na opisarnia.pl wymienia obu dostawców (wersja 1.1 od 13.11.2026, § 6 ust. 4; sprawdzone 2026-11-19 na stronie)
  - [x] polityka prywatności na opisarnia.pl wymienia obu dostawców (wersja 1.1 od 13.11.2026, pkt 5 i 6; sprawdzone 2026-11-19 na stronie)
  Jak: Anthropic: anthropic.com/legal, DPA jest częścią warunków komercyjnych API; zapisz wersję i datę przy kroku.
  Mistral: mistral.ai/terms, sekcja Data Processing Agreement; zapisz wersję i datę przy kroku.
  Regulamin i polityka: stopka opisarnia.pl, w każdym dokumencie wyszukaj „Anthropic” i „Mistral” (Cmd+F).
  Gdy dostawcy brakuje w dokumencie: zadanie dla Claude „Dopisz Anthropic i Mistral do regulaminu i polityki prywatności”; wdrożenie po Twojej zgodzie.
  Wszystkie wiadomości do ludzi (zaproszenia, wiadomości, przypomnienia) i publikacje w kampanie/staly-rytm.md czekają na to zadanie (po:); komentarze: pytanie 13 w KARTA.md.
  wynik: Regulamin, wersja 1.1 od 13.11.2026: § 6 ust. 4 wymienia Anthropic, PBC jako główny silnik (USA) i Mistral AI jako zapasowy (UE). Polityka prywatności, wersja 1.1 od 13.11.2026: pkt 5 wymienia obu jako podmioty przetwarzające, a pkt 6 opisuje przekazywanie danych do USA.

## Etap: Walidacja i marketing
termin: 2026-12-23

- [x] Opublikować pierwsze posty LinkedIn (2026-06-08, 2026-06-12)
- [x] Bramka ADR 0001 zastąpiona celami do 23.12 (2026-10-27; 200 adresów nie zebrano, Brevo wyłączył klucz SMTP 14.10)
- [x] Metryki: metryki.md w repozytorium, pomiar startowy 2026-11-18: 0 kont, 0 aktywnych, 0 płacących
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
- [x] Scal rejestr kontaktów z gałęzi agent/2026-11-19-rejestr-kontaktow | kto: ty | kiedy: 2026-11-19 | czas: 5
  cel: marketing/kontakty.md jest w master repozytorium Opisarni, więc zadania kontaktowe i agenci go widzą
  gotowe gdy: `git log -1 -- marketing/kontakty.md` na master repozytorium na serwerze pokazuje commit z rejestrem
  - [x] `ssh ops@2.29.181.133`; w repozytorium /home/panel/projekty/generator-opisow-mebli ustaw `git config user.name` i `user.email` (jako panel)
  - [x] w katalogu uruchomienia gałęzi agent/2026-11-19-rejestr-kontaktow: `sudo -u panel git commit -m "docs(marketing): rejestr kontaktów partii 1–4"`
  - [ ] panel, Agenci: uruchomienie „Załóż rejestr kontaktów…”, diff przejrzany, scalone do master
  Plik leży w indeksie gałęzi bez commita (zostało: zadania „Załóż rejestr kontaktów…”), dlatego scalenie w panelu wymaga najpierw commita.
  wynik: marketing/kontakty.md jest na master od commita d90f5fc (19.11); sprawdził Claude, zamknięte bez Twojej pracy
- [x] Przygotuj szkice wiadomości 1 dla 24 firm z partii 1–3 | kto: claude | gdzie: chmura | kiedy: 2026-11-20
  cel: przy każdej firmie z partii 1–3 gotowa wiadomość 1 ze zdaniem o tej firmie, do skopiowania bez poprawek
  gotowe gdy: plik wiadomosci/wiadomosc-1-partie-1-3.md w folderze karty ma 24 sekcje (firma, partia, wiadomość 1 ze szkicu z punktu 5 planu ze zdaniem z pierwszego akapitu draftu firmy); bez nazwisk i adresów; nic nie wysłane
  materiał: marketing/plan-10-kont.md#5
  materiał: marketing/outreach/drafts/
  materiał: STYL.md
  Firma bez draftu w marketing/outreach/drafts/: zdanie z punktu 5 planu (kolumna „Dlaczego te”) i dopisek „bez draftu” w sekcji.
  wynik: wiadomosci/wiadomosc-1-partie-1-3.md (folder karty): 24 sekcje (firma, partia, draft, wiadomość 1 według szablonu z punktu 5 planu ze zdaniem z pierwszego akapitu draftu); wszystkie 24 firmy miały draft; bez nazwisk, adresów i linków; nic nie wysłane
  decyzja: 14 sekcji ma wiersz „uwaga”. STIPA i Ramaro mają już strony po niemiecku (plan każe takie pomijać): wysłać czy pominąć? Przy Alan Meble, Meble North, Miloni i VERYSIMPL draft nie potwierdza sprzedaży za granicę, więc pytanie o opisy po niemiecku może nie trafić: zostawić szablon czy pominąć te firmy? Fakty pochodzą z researchu z czerwca i lipca, nie sprawdzałem ich ponownie.
- [ ] Wyślij zaproszenia LinkedIn do 24 firm z partii 1–3 | kto: ty | kiedy: 2026-11-21 | czas: 45 | licznik: zaproszenia
  cel: 24 zaproszenia do osób decyzyjnych w firmach z partii 1–3, bez oferty
  gotowe gdy: przy każdej firmie krok zaznaczony: zaproszenie wysłane albo pominięta (nie działa, ma już opisy po niemiecku)
  materiał: marketing/plan-10-kont.md#5
  - [ ] Kedameble
  - [ ] Bambooko
  - [ ] Meble z Polski 24
  - [ ] PLMEBLE
  - [ ] DANZZ
  - [ ] RaWood
  - [ ] STIPA
  - [ ] Smartwood
  - [ ] ERMA Meble
  - [ ] ATB Meble
  - [ ] Alan Meble
  - [ ] Meble North
  - [ ] Shik
  - [ ] Miloni
  - [ ] VERYSIMPL
  - [ ] Lano Meble
  - [ ] Meble Emilia
  - [ ] Brattex
  - [ ] Vilmax
  - [ ] OneLoft
  - [ ] Ramaro
  - [ ] New Elegance
  - [ ] Comforteo
  - [ ] MGK Meble
  Możesz rozłożyć na 3 dni po 8. W większych firmach (od Meble Emilia) szukaj osoby od e-commerce lub marketingu.
- [ ] Wyślij wiadomość do 10–15 znajomych z branży (wariant B) | kto: ty | kiedy: 2026-11-20 | czas: 30 | licznik: linki
  cel: osoby z branży, które znasz osobiście, dostają link do darmowego konta
  gotowe gdy: 10–15 osób z branży dostało wiadomość z linkiem opisarnia.pl/rejestracja
  materiał: marketing/plan-10-kont.md#5
  Szkic wiadomości jest na końcu punktu 5. Listę osób znasz tylko Ty.
- [ ] Wyślij wiadomość 1 do osób, które przyjęły zaproszenie | kto: ty | kiedy: 2026-11-24 | czas: 30 | po: Wyślij zaproszenia LinkedIn do 24 firm, Przygotuj szkice wiadomości 1 | licznik: przyjęte
  cel: każda osoba, która przyjęła zaproszenie, dostaje pytanie bez linku
  gotowe gdy: każda osoba z partii 1–3, która przyjęła zaproszenie, dostała wiadomość 1
  materiał: wiadomosci/wiadomosc-1-partie-1-3.md
  Gotowe teksty przy każdej firmie przygotuje agent. Licznik: liczba osób, które przyjęły zaproszenie. Link dopiero po odpowiedzi „tak”.
- [ ] Wyślij przypomnienia tam, gdzie była rozmowa | kto: ty | kiedy: 2026-11-27 | czas: 15 | po: Wyślij wiadomość 1 do osób, które przyjęły | licznik: rozmowy
  cel: jedno przypomnienie do osób, które rozmawiały, a nie założyły konta
  gotowe gdy: każda rozmowa bez konta ma jedno przypomnienie; brak odpowiedzi kończy kontakt
  materiał: marketing/plan-10-kont.md#5
  Licznik: liczba rozmów (osoby, które odpisały na wiadomość 1).
- [ ] Wpisz liczbę kont 30.11 i wybierz kanały na grudzień | kto: ty | kiedy: 2026-11-30 | czas: 15 | licznik: konta
  cel: liczba kont Free na 30.11 i decyzja, które kanały zostają
  gotowe gdy: liczba kont podana przy zamknięciu; wariant z tabeli „Decyzja 30.11” w notatce pod zadaniem
  materiał: marketing/plan-10-kont.md#8
  materiał: metryki.md#3
  Progi: 10 i więcej kont: kanały zostają; 5–9: zostaje najlepszy kanał; 0–4: zmiana kanałów, najpierw sprawdzenie rejestracji.

## Do rozplanowania

- [ ] Popraw stan ZDJ-1 w plikach zadań repozytorium | kto: claude | gdzie: chmura
  cel: pliki zadań w repozytorium opisują ZDJ-1 jako zmergowane za flagą (#126–#134), nie jako bez merge
  gotowe gdy: żaden plik w tasks/ nie opisuje ZDJ-1 jako niezmergowanego; zmiana w jednym commicie
  materiał: tasks/README.md
- [x] Zaktualizuj tasks/README.md do stanu z listopada | kto: claude | gdzie: chmura
  cel: tasks/README.md opisuje bieżący stan prac zamiast stanu z czerwca
  gotowe gdy: README nie zawiera nieaktualnych zadań z czerwca i wskazuje ZADANIA.md karty jako listę zadań
  materiał: tasks/README.md
  wynik: scalone do master 19.11 (commit 64f999b, bez push)
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
- [x] Przygotować post na 2026-11-20: Opublikuj film A „Opis mebla po polsku i niemiecku w 10 sekund” | kto: claude | gdzie: chmura | kiedy: 2026-11-19
  materiał: kampanie/staly-rytm.md
  wynik: teksty pod film A przyjęte 19.11 (Claude za właściciela); publikacja po nagraniu filmu
- [ ] Oznacz definicję konta aktywnego w metryki.md jako przyjętą | kto: claude | gdzie: chmura | kiedy: 2026-11-23
  z pytania 9, 2026-11-19
- [ ] Dodaj parametr UTM i pole źródła przy rejestracji | kto: claude | gdzie: chmura | kiedy: 2026-12-01
  z pytania 12, 2026-11-19
- [x] Zaproponuj formy marketingu Opisarni na grudzień (poza Reels) | kto: claude | gdzie: chmura | kiedy: 2026-11-19
  cel: 3–5 form marketingu dopasowanych do grupy docelowej, każda z przykładem i rytmem, gotowe do wpisania na oś czasu
  gotowe gdy: plik marketing/formy-grudzien.md w folderze karty: dla każdej formy kanał, dla kogo, przykład tematu, częstotliwość, nakład pracy i czy film robi studio (pokaz albo objaśnienie); rekomendacja 3 form na start
  materiał: KARTA.md
  wynik: powstał marketing/formy-grudzien.md (folder karty): 5 form (darmowy przegląd opisu, karuzela „przed i po”, grupy sprzedawców na Facebooku, maile aktywacyjne, poradnik z filmem), każda z kanałem, odbiorcą, przykładem tematu, częstotliwością, nakładem pracy i filmem ze studia (pokaz albo objaśnienie); rekomendacja na start: przegląd opisu, grupy na Facebooku, maile aktywacyjne; 4 warianty z kosztem i oś czasu 30.11–23.12; pytanie 14 w KARTA.md
  decyzja: wybór form na grudzień (pytanie 14 w KARTA.md; propozycja: wariant 2, 0 zł, ok. 2 h tygodniowo ponad stały rytm)
  zostało: nazw i regulaminów grup na Facebooku oraz przepisów o mailach marketingowych nie sprawdziłem w sieci (brak uprawnienia do wyszukiwania); szacunki kont to założenia, nie pomiary; plik leży w folderze karty, więc w repozytorium nie ma commita
- [ ] Przygotuj ogłoszenie, przypomnienie i szablony darmowego przeglądu opisu | kto: claude | gdzie: chmura | kiedy: 2026-11-30
  z pytania 14, 2026-11-21
- [ ] Wybierz 3–5 grup sprzedawców na Facebooku i przeczytaj regulaminy | kto: ty | kiedy: 2026-12-01 | czas: 30
  z pytania 14, 2026-11-21
- [ ] Przygotuj teksty 3 maili aktywacyjnych z oceną RODO | kto: claude | gdzie: chmura | kiedy: 2026-12-02
  z pytania 14, 2026-11-21
- [ ] Dokończ: nazw i regulaminów grup na Facebooku oraz przepisów o mailach marketingowych nie sprawdziłem w sieci (brak upra | kto: claude
  cel: nazw i regulaminów grup na Facebooku oraz przepisów o mailach marketingowych nie sprawdziłem w sieci (brak uprawnienia do wyszukiwania); szacunki kont to założenia, nie pomiary; plik leży w folderze karty, więc w repozytorium nie ma commita
