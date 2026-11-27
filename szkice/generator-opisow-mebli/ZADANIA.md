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
- [!] Wdróż poprawki SEC-2 i SEC-4 na produkcję | kto: claude | gdzie: chmura | kiedy: 2026-11-22 | po: Przejrzyj zmiany agenta SEC-2 i SEC-4 | blokada: agent nie ma uprawnienia do `git push origin master` (ani do `gh` i `curl`)
  cel: poprawki SEC-2 i limit body na Caddy działają na opisarnia.pl
  gotowe gdy: master z poprawkami na GitHubie, CI i auto-deploy zielone, `caddy validate` na serwerze Opisarni zielone, opisarnia.pl odpowiada
  Przekazane agentowi przy porządkach 2026-11-21 (DECYZJE.md): od właściciela potrzebna tylko zgoda na wdrożenie, kroki wykonuje agent.
  Gdy agent nie ma uprawnienia do push albo dostępu do serwera Opisarni: [!] z blokadą i nazwą brakującego uprawnienia.
  - [ ] `git -C /home/panel/projekty/generator-opisow-mebli push origin master` (bez --force)
  - [ ] GitHub, zakładka Actions repozytorium Opisarni: CI i auto-deploy zielone
  - [ ] serwer Opisarni: `docker compose -f docker-compose.prod.yml exec caddy caddy validate --config /etc/caddy/Caddyfile`, potem `caddy reload` tym samym poleceniem
  - [ ] `curl -sI https://opisarnia.pl` zwraca 200 i nagłówki Content-Security-Policy oraz Strict-Transport-Security
  Nazwa usługi Caddy i ścieżka Caddyfile według docker-compose.prod.yml; push uruchamia auto-deploy (#70).
  wynik: nic nie wdrożono, produkcja bez zmian. Sprawdzone lokalnie 22.11: master (64f999b) zawiera poprawki SEC-2 i SEC-4 i czeka na wysłanie (5 commitów, 16 plików, +893 −31, w tym Caddyfile i docker-compose.prod.yml); usługa `caddy` i ścieżka `/etc/caddy/Caddyfile` z kroków zgadzają się z docker-compose.prod.yml. Żaden plik nie powstał.
  zostało: wszystkie 4 kroki. Środowisko agenta odrzuciło: `git -C /home/panel/projekty/generator-opisow-mebli push origin master`, `git ls-remote origin master`, `gh run list` (podgląd CI i auto-deploy) oraz `curl -sI https://opisarnia.pl`; dostępu do serwera Opisarni (`caddy validate`, `caddy reload`) nie próbowano, bo bez push nie ma czego tam sprawdzać, a adresu serwera nie ma w zadaniu. Nie sprawdzono więc stanu GitHuba, CI, Caddy na serwerze ani tego, czy opisarnia.pl odpowiada. Po dopuszczeniu tych poleceń w panelu zadanie można uruchomić ponownie bez zmian.

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
- [x] Zdecyduj go/no-go dla Opisarni | kto: ty | kiedy: 2026-12-23 | czas: 15
  cel: decyzja go, zamrożenie albo pivot zapisana w DECYZJE.md
  gotowe gdy: w DECYZJE.md wpis z 2026-12-23 z liczbami z metryki.md (punkt 3) i wybraną drogą
  materiał: metryki.md#1
  materiał: metryki.md#3
  materiał: KARTA.md#Definicja ukończenia
  pyta: Wybrana droga [wybór: go | zamrożenie | pivot]
  odpowiedź: Wybrana droga = go
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
  Rozstrzygnięte przy porządkach 2026-11-21 (agent, DECYZJE.md): STIPA pominięta (ma niemiecką wersję sklepu, reguła z punktu 5 planu); Ramaro dostaje zaproszenie, a wiadomość 1 tylko wtedy, gdy opisy produktów nie są po niemiecku; Alan Meble, Meble North, Miloni i VERYSIMPL zostają z szablonem. Fakty pochodzą z researchu z czerwca i lipca, bez ponownego sprawdzenia.
- [ ] Wyślij zaproszenia LinkedIn do 24 firm z partii 1–3 | kto: ty | kiedy: 2026-11-27 | czas: 45 | licznik: zaproszenia
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
  - [x] Meble North
  - [ ] Shik
  - [ ] Miloni
  - [ ] VERYSIMPL
  - [x] Lano Meble
  - [ ] Meble Emilia
  - [ ] Brattex
  - [ ] Vilmax
  - [x] OneLoft
  - [ ] Ramaro
  - [ ] New Elegance
  - [ ] Comforteo
  - [ ] MGK Meble
  Możesz rozłożyć na 3 dni po 8. W większych firmach (od Meble Emilia) szukaj osoby od e-commerce lub marketingu.
  Porządki 2026-11-21 (DECYZJE.md): STIPA zaznacz jako pominiętą (ma niemiecką wersję sklepu); Ramaro i pozostałe firmy dostają zaproszenie.
- [x] Wyślij wiadomość do 10–15 znajomych z branży (wariant B) | kto: ty | kiedy: 2026-11-20 | czas: 30 | licznik: linki
  cel: osoby z branży, które znasz osobiście, dostają link do darmowego konta
  gotowe gdy: 10–15 osób z branży dostało wiadomość z linkiem opisarnia.pl/rejestracja
  materiał: marketing/plan-10-kont.md#5
  Szkic wiadomości jest na końcu punktu 5. Listę osób znasz tylko Ty.
- [ ] Wyślij wiadomość 1 do osób, które przyjęły zaproszenie | kto: ty | kiedy: 2026-11-24 | czas: 30 | po: Wyślij zaproszenia LinkedIn do 24 firm, Przygotuj szkice wiadomości 1 | licznik: przyjęte
  cel: każda osoba, która przyjęła zaproszenie, dostaje pytanie bez linku
  gotowe gdy: każda osoba z partii 1–3, która przyjęła zaproszenie, dostała wiadomość 1
  materiał: wiadomosci/wiadomosc-1-partie-1-3.md
  Gotowe teksty przy każdej firmie są w pliku z materiału (23 firmy, STIPA pominięta). Licznik: liczba osób, które przyjęły zaproszenie. Link dopiero po odpowiedzi „tak”.
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

- [x] Popraw stan ZDJ-1 w plikach zadań repozytorium | kto: claude | gdzie: chmura
  cel: pliki zadań w repozytorium opisują ZDJ-1 jako zmergowane za flagą (#126–#134), nie jako bez merge
  gotowe gdy: żaden plik w tasks/ nie opisuje ZDJ-1 jako niezmergowanego; zmiana w jednym commicie
  materiał: tasks/README.md
  wynik: ZDJ-1 opisane jako zrobione i w master od 2026-11-06 (#134), wyłączone flagą VISION_ENABLED, w docs/tasks/task-zdjecia/00-README-zdjecia.md i docs/tasks/task-zdjecia/01-backend-analiza-zdjec.md; z docs/tasks/README.md usunięta uwaga o nieaktualnym nagłówku. W docs/tasks/ nie ma już wzmianki „bez merge”.
  zostało: agent nie miał uprawnień do zapisania commita, więc trzy zmienione pliki czekają na zatwierdzenie przez panel jako jeden commit. Sam merge ZDJ-1 to #134; #126–#133 z celu zadania to inne zmiany (eksport, landing, quota), więc w plikach podany jest tylko #134.
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
- [x] Oznacz definicję konta aktywnego w metryki.md jako przyjętą | kto: claude | gdzie: chmura | kiedy: 2026-11-23
  z pytania 9, 2026-11-19
  wynik: w metryki.md definicja „konta aktywnego” (co najmniej 1 udana generacja w ostatnich 14 dniach) ma status „przyjęta 2026-11-19”; zaktualizowane punkty 2 i 7, zapytanie pomiarowe bez zmian (już tak liczyło)
- [ ] Podaj identyfikatory kont własnych i testowych do pomiaru | kto: ty | kiedy: 2026-11-27 | czas: 5
  cel: pomiar kont nie liczy kont właściciela ani testowych
  gotowe gdy: identyfikatory podane przy zamknięciu zadania (pole notatki), np. „1, 2”, albo „brak”
  materiał: metryki.md#6
  pyta: Identyfikatory kont [tekst, np. 1, 2 albo brak]
  Z pytania 11 w KARTA.md (odpowiedź przyjęła sposób, ale bez liczb); dopisane przy porządkach 2026-11-21. Panel admina → lista użytkowników → kolumna ID przy Twoich kontach (także konto z testu rejestracji na telefonie 18.11).
  Wpisanie liczb do `ARRAY[...]` w metryki.md zrobi agent.
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
- [ ] Wybierz 3–5 grup sprzedawców na Facebooku i przeczytaj regulaminy | kto: claude | gdzie: chmura | kiedy: 2026-12-01
  z pytania 14, 2026-11-21
  cel: lista 3–5 grup sprzedawców (meble, Allegro, eksport do DE) z zasadami o promocji, gotowa do dołączenia przez właściciela
  gotowe gdy: plik marketing/grupy-facebook.md w folderze karty: dla każdej grupy nazwa, link, liczba członków, zasada o promocji i linkach (cytat albo „regulamin widoczny dopiero po dołączeniu”), data sprawdzenia
  materiał: marketing/formy-grudzien.md
  Przekazane agentowi przy porządkach 2026-11-21 (DECYZJE.md); połączone z zadaniem „Dokończ: nazw i regulaminów grup…”. Dołączenie do grup i pisanie w nich zostaje u właściciela (wiersze grudniowe).
  Gdy brak uprawnienia do wyszukiwania w sieci: [!] z blokadą „brak wyszukiwania w sieci”.
- [ ] Przygotuj teksty 3 maili aktywacyjnych z oceną RODO | kto: claude | gdzie: chmura | kiedy: 2026-12-02
  z pytania 14, 2026-11-21
  Porządki 2026-11-21: ocena RODO obejmuje sprawdzenie w sieci aktualnych przepisów o mailach marketingowych (zgoda na komunikację handlową), przeniesione z zadania „Dokończ: nazw i regulaminów grup…”.
- [x] Dokończ: nazw i regulaminów grup na Facebooku oraz przepisów o mailach marketingowych nie sprawdziłem w sieci (brak upra | kto: claude
  cel: nazw i regulaminów grup na Facebooku oraz przepisów o mailach marketingowych nie sprawdziłem w sieci (brak uprawnienia do wyszukiwania); szacunki kont to założenia, nie pomiary; plik leży w folderze karty, więc w repozytorium nie ma commita
  wynik: zamknięte przy porządkach 2026-11-21 (dubel: grupy i regulaminy są w „Wybierz 3–5 grup sprzedawców na Facebooku…”, przepisy o mailach w „Przygotuj teksty 3 maili aktywacyjnych z oceną RODO”)
- [x] Porządki spraw właściciela: pytania w karcie i Twoje zadania | kto: claude | gdzie: chmura | kiedy: 2026-11-21
  cel: zostawić właścicielowi tylko sprawy, których nie rozstrzygnie nikt inny (pieniądze, dane prawne i firmowe, działania nieodwracalne albo na zewnątrz, zakres i terminy, rzeczy fizyczne, fakty znane tylko jemu); w tym zadaniu wolno zmieniać inne wiersze ZADANIA.md (bez terminów i tytułów) i dopisywać odpowiedzi w KARTA.md
  - [x] Pytania w „Pytania do właściciela”: każde, które rozstrzygniesz sam albo sprawdzisz w plikach i repozytorium, opatrz wierszem `   Odpowiedź: … (agent, DECYZJE.md)` i zapisz decyzję w DECYZJE.md z `- Kto: agent`; powtórzone pytanie połącz z pierwszym
  - [x] Zadania kto: ty: te, które może zrobić agent, przepisz na kto: claude; zbędne i zdublowane zamknij `[x]` z `wynik: zamknięte przy porządkach 2026-11-21 (powód)`; podobne połącz w jedno
  - [x] Odbiory prac wewnętrznych bez `decyzja:` i bez kodu do scalenia zamknij `[x]`
  - [x] Zostaw najwyżej jedno pytanie bez odpowiedzi; pozostałe sprawy właściciela muszą być zadaniami kto: ty z czasem w minutach
  gotowe gdy: w KARTA.md najwyżej jedno pytanie bez odpowiedzi, każda decyzja agenta ma wpis w DECYZJE.md, a w wyniku jest lista zmian: ile pytań rozstrzygnięto, ile zadań przekazano agentom, ile zamknięto, co zostało właścicielowi
  - [x] Na koniec stan `[~]`, `wymaga: odbiór` i `decyzja: przyjęcie porządków` z listą zmian w `wynik:`
  materiał: KARTA.md#Pytania do właściciela
  wynik: pytania w KARTA.md: 0 rozstrzygniętych przez agenta, bo wszystkie 14 miało już odpowiedź (0 bez odpowiedzi, 0 powtórzonych, karta bez zmian); rozstrzygnięty 1 otwarty wybór z zadania „Przygotuj szkice wiadomości 1…” (STIPA pominięta, Ramaro i 4 firmy zostają). Zadania przekazane agentom: 2 („Wdróż poprawki SEC-2 i SEC-4 na produkcję” z `wymaga: zgoda`, „Wybierz 3–5 grup sprzedawców na Facebooku…”). Zamknięte: 1 („Dokończ: nazw i regulaminów grup…”, dubel). Odbiory do zamknięcia: 0 (nie było żadnego otwartego). Dopisane: 1 zadanie właściciela „Podaj identyfikatory kont własnych i testowych do pomiaru” (5 min) i czas 15 min przy „Zdecyduj go/no-go”; usunięte 2 omyłkowe kroki tego zadania spod zadań o widoku „Pokaz”. Przy ponownym przejściu 21.11 stan sprawdzony (14 pytań z odpowiedzią, 7 zadań właściciela z czasem, 6 wierszy publikacji) i dopisana 1 decyzja: odpowiedź „z 4” w pytaniu 8 czytana jako około 4 kontakty z branży, rezerwa według punktu 7 planu, bez nowego pytania; poprawiona notatka przy „Wyślij wiadomość 1…” (teksty są gotowe). 5 wpisów w DECYZJE.md z 2026-11-21. Zostało właścicielowi w ZADANIA.md 7 zadań, razem 155 min: zaproszenia LinkedIn (45), wiadomość do znajomych (30), wiadomość 1 (30), przypomnienia (15), identyfikatory kont (5), liczba kont i kanały 30.11 (15), go/no-go 23.12 (15); do tego zgoda na wdrożenie SEC-2 i SEC-4 oraz 6 wierszy publikacji w kampanie/staly-rytm.md (80 min, bez zmian)
  decyzja: przyjęcie porządków: wdrożenie SEC-2 i SEC-4 robi agent za Twoją zgodą; grupy na Facebooku wyszukuje agent; STIPA pominięta w zaproszeniach (23 zamiast 24); identyfikatory kont własnych podajesz w nowym zadaniu; odpowiedź „z 4” (pytanie 8) czytana jako około 4 kontakty z branży
  zostało: nie sprawdzałem, czy agent ma uprawnienie do wysłania zmian na GitHub i dostęp do serwera Opisarni (wyjdzie przy zadaniu wdrożenia); wierszy w kampanie/staly-rytm.md nie zmieniałem; zadanie agenta „Popraw stan ZDJ-1 w plikach zadań repozytorium” wisi w stanie „w toku” bez wyniku, nie ruszałem go
- [ ] Uzupełnić pliki projektu według standardu | kto: claude
  cel: Uzupełnić według standard/STANDARD.md: Zadania (2 braki), README (3 braki), Architektura (brak pliku), Uruchomienie (brak pliku), Instrukcje agentów (3 braki). Niczego nie nadpisywać; na końcu python3 standard/projekt.py sprawdz bez braków w tym projekcie.
- [ ] Dokończ: nie sprawdzałem, czy agent ma uprawnienie do wysłania zmian na GitHub i dostęp do serwera Opisarni (wyjdzie prz | kto: claude
  cel: nie sprawdzałem, czy agent ma uprawnienie do wysłania zmian na GitHub i dostęp do serwera Opisarni (wyjdzie przy zadaniu wdrożenia); wierszy w kampanie/staly-rytm.md nie zmieniałem; zadanie agenta „Popraw stan ZDJ-1 w plikach zadań repozytorium” wisi w stanie „w toku” bez wyniku, nie ruszałem go
- [x] Zaplanuj filmy na grudzień według podziału z karty | kto: claude | gdzie: chmura | kiedy: 2026-11-24
  cel: dopisz do harmonogramu kampanii projektu 4–6 publikacji z filmem na grudzień (tytuł ze słowem „film”, kanał np. reels, linkedin), tematy z kampanii i dokumentów marketingu; podział filmów jak w polu karty „nagrywa: panel 50, ai 40, ty 10” (panel nagrywa ekran strony, AI: film z gotowych poleceń, Ty: nagranie telefonem tam, gdzie trzeba pokazać prawdziwą rzecz)
  gotowe gdy: w kampanii są nowe wiersze publikacji z filmem z datami w grudniu, kto: ty, każda z kanałem; scenariuszy nie zakładasz (panel przygotuje je sam 7 dni przed publikacją według podziału)
  wynik: w kampanie/staly-rytm.md (folder karty) jest 6 nowych wierszy „Opublikuj film …”, każdy kto: ty, z kanałem i czasem 15 min: 3.12 „Zwrot z Niemiec przez nieprecyzyjny opis” (panel), 7.12 „Szafa, która nie weszła po schodach: 5 wymiarów w opisie” (AI), 10.12 „Pierwszy opis w 2 minuty” (panel), 12.12 „Pierwsze zdanie opisu decyduje…” (AI), 15.12 „Od miarki do opisu: prawdziwy mebel w 60 sekund” (Ty, telefon), 17.12 „Ten sam mebel, trzy opisy” (panel); podział 3 panel, 2 AI, 1 Ty; scenariuszy nie zakładałem; decyzja o datach i podziale w DECYZJE.md
  zostało: sposób nagrania w wierszach to propozycja, ostatecznie przydziela go panel przy scenariuszu (może wyjść inaczej niż w wierszu); filmy B (24.11) i C (28.11) z planu 10 kont nadal nie mają wierszy w kampanii, temat B wszedł jako film z 3.12; film z 15.12 wymaga prawdziwego mebla i miarki do nagrania 14.12
- [x] Przygotuj publikację na 2026-11-25 (771bded7d129dd9e): Opublikuj post „Rachunek ryzyka eksportu mebli do Niemiec” | kto: agent | gdzie: chmura | kiedy: 2026-11-25
  cel: Przygotuj tekst posta do publikacji „Opublikuj post „Rachunek ryzyka eksportu mebli do Niemiec”” (linkedin), termin 2026-11-25. Pozostaw publikację właścicielowi.
  gotowe gdy: Tekst posta jest w posty/2026-11-25-publikacja/post.md, zgodny z wpisem w kampanie/staly-rytm.md i gotowy do odbioru przed publikacją 2026-11-25.
  materiał: kampanie/staly-rytm.md
  wynik: tekst posta na LinkedIn w posty/2026-11-25-publikacja/post.md (z pierwszym komentarzem z linkiem i tekstem alternatywnym) oraz grafika posty/2026-11-25-publikacja/grafika.svg z szablonu; podstawa to draft z 26.06 z ostatnim akapitem według planu 10 kont (post 3); zdanie o 38% zwrotów poprawione zgodnie ze źródłem (dotyczy zdjęcia, nie opisu), wpis w DECYZJE.md
  zostało: publikujesz Ty na LinkedIn po „Potwierdź DPA” (tak stoi w wierszu kampanii); PNG grafiki zrobi panel, wyrenderowanej grafiki nie oglądałem
- [x] Przygotuj scenariusz nagrania na 2026-11-27: Film A „Opis mebla po polsku i niemiecku w 10 sekund” | kto: claude | gdzie: chmura | kiedy: 2026-11-26
  cel: scenariusz filmu do publikacji „Film A „Opis mebla po polsku i niemiecku w 10 sekund”” z 2026-11-27 (linkedin, facebook, reels), który właściciel zrobi 2026-11-26 w narzędziu AI do wideo (np. CapCut, Runway, Kling): dla każdej sceny gotowe polecenie do skopiowania (co widać, ruch kamery, styl, długość), tekst lektora i napisy, muzyka; bez prawdziwych ludzi i bez udawania prawdziwego produktu — ujęcia, które muszą pokazać prawdziwy produkt albo ekran, oznacz „nagraj telefonem” albo „zrzut ekranu” (przeczytaj kampanię, plan filmów i dokumenty projektu)
  gotowe gdy: obok KARTA.md jest plik posty/2026-11-27-film-a-opis-mebla-po-polsku-i-niemiecku/scenariusz.md w układzie: „# Scenariusz nagrania: <tytuł>”, pola „- stan: propozycja”, „- publikacja: 2026-11-27”, „- nagranie: 2026-11-26”, „- sposób: ai”, sekcje ## Po co (cel, dla kogo), ## Co nagrać (wiersze „- [ ] polecenie dla AI / 5 s”), ## Jak (narzędzie, format pionowy albo poziomy, styl i spójność scen), ## Co powiedzieć (tekst albo punkty), ## Na koniec (wezwanie do działania), ## Gotowe gdy; każda sekcja wypełniona; post.md i zadania nagrania bez zmian
  materiał: kampanie/staly-rytm.md
  materiał: STYL.md
  materiał: marketing/plan-10-kont.md
  wynik: scenariusz w posty/2026-11-27-film-a-opis-mebla-po-polsku-i-niemiecku/scenariusz.md: 8 scen po 5 s (40 s, pion 9:16); 3 sceny AI z gotowymi poleceniami (ilustracyjna komoda, bez ludzi, napisów i logo), 4 sceny „zrzut ekranu” wycięte z filmu panelu z 20.11 (posty/2026-11-20-film-a-opis-pl-de/film.mp4, czasy podane), plansza końcowa w kolorach marki; lektor i napisy w tabeli, muzyka i narzędzia (Kling albo Runway + CapCut); opis pod filmem zostaje z post.md z 20.11 (bez zmian); wpis w DECYZJE.md
  decyzja: który film publikujesz 27.11: gotowy film panelu z 20.11 czy wersję AI według scenariusza (propozycja: wersja AI na Reels, bo ma hak w pierwszej sekundzie; film z 20.11 na LinkedIn)
  zostało: nie sprawdzałem aktualnych limitów darmowych kredytów w Kling, Runway i CapCut ani tego, czy kadry z filmu z 20.11 są czytelne po przycięciu do pionu (scenariusz podaje zastępstwo: zrzut ekranu z telefonu)
