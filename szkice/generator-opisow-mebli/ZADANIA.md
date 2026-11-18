# Zadania: Opisarnia (generator opisów mebli)

> Jedyna lista zadań projektu. Czyta ją panel i agenci.
> Wiersz: `- [ ] Tytuł | kto: claude | gdzie: pc | kiedy: RRRR-MM-DD | pora: noc | czas: 30 | wymaga: zgoda`
> Stany: `[ ]` do zrobienia, `[~]` w toku, `[!]` zablokowane (dodaj `blokada: powód`), `[x]` zrobione.
> Pola są opcjonalne. kto: claude, codex, ty. gdzie: pc, mac, chmura. pora: dzień, noc. czas: minuty Twojej pracy. wymaga: zgoda, odbiór.
> Etap to nagłówek `## Etap: nazwa` i wiersz `termin: RRRR-MM-DD` pod nim. Etap bez otwartych zadań jest zamknięty.

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
- [ ] Sprawdzić, czy wszystkie ekrany biorą dane z realnego API (DEMOCK) | kto: claude | gdzie: chmura | wymaga: odbiór

## Etap: Bezpieczeństwo przed płacącymi

- [x] SEC-3, SEC-5, SEC-1: zależności, sekrety i RODO, SAST backendu (2026-06-16)
- [ ] SEC-2: SAST frontendu (XSS, open redirect, storage, CSP); stan po VI nieznany | kto: claude | gdzie: chmura | wymaga: odbiór
- [ ] SEC-4: infra, nagłówki bezpieczeństwa, CORS, rate-limit; stan po VI nieznany | kto: claude | gdzie: chmura | wymaga: odbiór

## Etap: Testy

- [x] Testy E2E (VI–VII, według historii commitów)
- [ ] Potwierdzić, czy RUN-1..6 (uruchomienie natywne bez Dockera) są jeszcze potrzebne | kto: ty | czas: 5

## Etap: Produkcja
termin: 2026-11-17

- [ ] Unieważnić testowy klucz API Mistral wklejony do rozmowy 26.10 (leży jawnie w historii Claude Code na PC) | kto: ty | czas: 5
- [x] Serwer Hetzner, Caddy z HTTPS, docker-compose.prod (ADR 0004, 0034)
- [x] Auto-deploy przez GitHub Actions (#70)
- [x] Ręczny deploy do #125 (2026-11-03)
- [x] Deploy #126–#134 na produkcję i klucz Anthropic; silnik Haiku działa od 13.11 (potwierdził właściciel 2026-11-14)
- [x] Stripe w trybie live (potwierdził właściciel 2026-11-14)
- [ ] Sentry, monitoring dostępności, nocny backup z testem przywrócenia: potwierdzić stan | kto: ty | czas: 15
- [x] JDG w CEIDG (potwierdził właściciel 2026-11-14)
- [ ] Potwierdzić DPA z dostawcami LLM, regulamin i politykę prywatności | kto: ty | kiedy: 2026-11-17 | czas: 15

## Etap: Walidacja i marketing
termin: 2026-12-23

- [x] Opublikować pierwsze posty LinkedIn (2026-06-08, 2026-06-12)
- [x] Bramka ADR 0001 zastąpiona celami do 23.12 (2026-10-27; 200 adresów nie zebrano, Brevo wyłączył klucz SMTP 14.10)
- [~] Publikacje z planu T1–T8 (2026-11-03 do 2026-12-23) | kto: ty
- [x] Metryki: metryki.md w repozytorium, pomiar startowy 2026-11-18: 0 kont, 0 aktywnych, 0 płacących
- [ ] Pomiar tygodniowy w metryki.md (poniedziałki) | kto: ty | kiedy: 2026-11-23 | czas: 10
- [x] Plan promocji produktu z szacunkiem zwrotu (koszt pozyskania konta, przychód przy 3 płacących) | kto: claude
- [ ] Checkpoint: co najmniej 10 kont Free, inaczej zmiana kanałów | kto: ty | kiedy: 2026-11-30
- [ ] Decyzja go/no-go: co najmniej 3 płacących i 20 aktywnych → go; inaczej zamrożenie albo pivot | kto: ty | kiedy: 2026-12-23

## Do rozplanowania

- [ ] Uporządkować pliki zadań w repo: ZDJ-1 opisane jako bez merge, tasks/README z czerwca | kto: claude | gdzie: chmura
- [ ] Widok „Pokaz” (PoC na gałęzi feat/pokaz-opisarnia, 778 zmian): dopracować UI i zacommitować | kto: claude | gdzie: chmura | wymaga: odbiór
- [ ] Lokalny master na 26.10: zsynchronizować z origin | kto: ty | czas: 5
- [ ] Zsynchronizować kopię na Macu z origin | kto: ty | gdzie: mac | czas: 5
- [ ] Dług a11y: drawer overlay i aria-modal, role menu w nawigacji | kto: claude
- [ ] Dług zależności: vite 5.x i wyjątek pip w gate CI | kto: claude
- [ ] ZDJ-5: analiza zdjęć, tylko po decyzji „go” (styczeń 2027) | kto: ty | wymaga: zgoda
- [ ] Faza 2: style i tony, słownik atrybutów, własne szablony, języki CZ/SK/FR | kto: ty
