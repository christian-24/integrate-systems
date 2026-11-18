# Zadania: NaulikApp

> Jedyna lista zadań projektu. Czyta ją panel i agenci.
> Wiersz: `- [ ] Tytuł | kto: claude | gdzie: pc | kiedy: RRRR-MM-DD | pora: noc | czas: 30 | wymaga: zgoda`
> Stany: `[ ]` do zrobienia, `[~]` w toku, `[!]` zablokowane (dodaj `blokada: powód`), `[x]` zrobione.
> Pola są opcjonalne. kto: claude, codex, ty. gdzie: pc, mac, chmura. pora: dzień, noc. czas: minuty Twojej pracy. wymaga: zgoda, odbiór.
> Etap to nagłówek `## Etap: nazwa` i wiersz `termin: RRRR-MM-DD` pod nim. Etap bez otwartych zadań jest zamknięty.
> Uzupełnione danymi z PC (audyt 2026-11-14). Stany T34–T44 z 2026-05-29; RC1 zmergowany 2026-10-27, więc część z nich mogła zostać zamknięta.

## Etap: v1.0.0 MVP

- [x] T01 Motyw, typografia i tokeny
- [x] T01c Refaktor wspólnych widgetów na tokeny
- [x] T02 Migracja schematu bazy v5 do v6
- [x] T03–T11 Jednostka i rejs: walidacja MMSI, PIN, tworzenie, lista, szczegóły, zamknięcie z przytrzymaniem
- [x] T12–T17 Ruch portowy i usterki: tabele, DAO, formularze, oś czasu
- [x] T18–T19 Sealed log i eksport PDF
- [x] T20–T21 Limity Free Tier i onboarding
- [~] T22 Test dymny E2E (zielony); test manualny przeniesiony do T44
- [~] T23 Migracja starych ekranów; surowe wartości zostały, przeniesione do T42

## Etap: v1.0.1 Zgodność UI z makietami

- [x] T24–T33 Motyw jasny domyślnie, dolna nawigacja, formularz rejsu, szczegóły jednostki, puste stany, ekran PDF

## Etap: v1.0.2 Porządki i testy

- [ ] T34 Kontrast okna PIN w trybie jasnym | kto: claude
- [ ] T35 Przycisk Wstecz 48 dp (F15) | kto: claude
- [ ] T37 Naprawić test vessel_edit_page (sharedPreferences) | kto: claude
- [ ] T38 Wspólny helper `_purposeLabel` w lib/core/i18n | kto: claude
- [ ] T36, T39, T40 Drobne porządki w jednym PR | kto: claude
- [ ] T42 Usunąć surowe kolory, odstępy i rozmiary czcionek z features | kto: claude
- [ ] T43 Testy dla 10 DAO bez pokrycia | kto: claude
- [x] T41 Ikony morskie: rezygnacja z MarineIcons.ttf na rzecz Material Symbols (2026-11-14)
- [x] Zastąpić ikony morskie odpowiednikami z Material Symbols | kto: claude | gdzie: chmura
- [x] T44 Manualny plan testów TC-01..TC-20 na urządzeniu | kto: ty

## Etap: RC1 i zamknięty test Google Play
termin: 2026-12-13

- [x] Faza 0: T50a–d, T51 (2026-06-01)
- [x] T48c (2026-07-17)
- [x] RC1 1.0.0+2 zmergowany (#121/#122, 2026-10-27)
- [x] Zmergować gałęzie fix/rc1-nagrania i marketing/kampania-rc1 (PR #124, przed merge pełna suita testów) | kto: ty
- [x] Naprawić check CI claude-review (odrzucony klucz API) | kto: ty | czas: 10
- [x] Zdecydować, czy materiały marketingowe trzymać w repozytorium | kto: ty | czas: 5
- [x] Keystore i podpisany build | kto: ty | gdzie: mac
- [x] Polityka prywatności | kto: claude
- [x] Test akceptacyjny RC1 | kto: ty
- [x] Konto Google Play założone (potwierdził właściciel 2026-11-14)
- [x] Zebrać 12 testerów; test trwa 14 dni, więc start najpóźniej 29.11 | kto: ty | kiedy: 2026-11-29
- [x] Zamknięty test (12+ testerów × 14 dni) | kto: ty
- [x] Wniosek o produkcję w Google Play | kto: ty | kiedy: 2026-12-13

## Do rozplanowania

- [x] Zebrać nowsze materiały z PC (audyt 2026-11-14)
- [x] Zsynchronizować kopię na Macu z origin | kto: ty | gdzie: mac | czas: 5
- [x] T48 a/e/g/h/m/n/q/t/v/w: wskazać niezbędne do v1.0.0 i je zrealizować | kto: claude | gdzie: chmura
- [ ] v1.0.3 Release readiness (T54–T66, część zamknięta w RC1) | kto: claude
- [ ] Odtworzyć plan testów MVP usunięty z docs/testing w commicie 2026-05-29 albo wskazać jego nowe miejsce | kto: claude
- [x] Cel: 500 instalacji do 2027-04-30 | kto: ty
- [x] Projekt modułów infrastrukturalnych: sync, subskrypcja, OAuth, powiadomienia | kto: claude
- [x] Finalizacja przypisań funkcji do wersji v1.1.0–v4.0.0 | kto: ty
