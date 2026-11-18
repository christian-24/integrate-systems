# Zadania: NaulikApp

> Jedyna lista zadań projektu. Czyta ją panel i agenci.
> Wiersz: `- [ ] Tytuł | kto: claude | gdzie: pc | kiedy: RRRR-MM-DD | pora: noc | czas: 30 | wymaga: zgoda`
> Stany: `[ ]` do zrobienia, `[~]` w toku, `[!]` zablokowane (dodaj `blokada: powód`), `[x]` zrobione.
> Pola są opcjonalne. kto: claude, codex, ty. gdzie: pc, mac, chmura. pora: dzień, noc. czas: minuty Twojej pracy. wymaga: zgoda, odbiór.
> Etap to nagłówek `## Etap: nazwa` i wiersz `termin: RRRR-MM-DD` pod nim. Etap bez otwartych zadań jest zamknięty.
> Szczegóły zadania: wcięte wiersze pod zadaniem (cel:, gotowe gdy:, materiał:, kroki `- [ ]`, wynik:, decyzja:, zostało:).
> Uzupełnione danymi z PC (audyt 2026-11-14). Stany T34–T44 z 2026-05-29; RC1 zmergowany 2026-10-27, więc część z nich mogła zostać zamknięta.
> Ścieżka krytyczna do startu zamkniętego testu 29.11: keystore 21.11, merge PR #124 22.11, polityka prywatności 23.11,
> podpisany build 24.11, test akceptacyjny 26.11, 12 testerów 27.11, start testu 29.11, wniosek o produkcję 13.12.

## Etap: v1.0.0 MVP

- [x] T01 Motyw, typografia i tokeny
- [x] T01c Refaktor wspólnych widgetów na tokeny
- [x] T02 Migracja schematu bazy v5 do v6
- [x] T03–T11 Jednostka i rejs: walidacja MMSI, PIN, tworzenie, lista, szczegóły, zamknięcie z przytrzymaniem
- [x] T12–T17 Ruch portowy i usterki: tabele, DAO, formularze, oś czasu
- [x] T18–T19 Sealed log i eksport PDF
- [x] T20–T21 Limity Free Tier i onboarding
- [~] Zamknij test dymny E2E (T22)
  cel: T22 zamknięty: test dymny E2E zielony, test manualny przeniesiony
  gotowe gdy: T22 oznaczony jako zrobiony w docs/backlog/STATUS.md
  materiał: docs/backlog/STATUS.md
  wynik: test dymny E2E zielony
  zostało: test manualny przeniesiony do T44
- [~] Dokończ migrację starych ekranów (T23)
  cel: stare ekrany korzystają z motywu i tokenów
  gotowe gdy: T23 oznaczony jako zrobiony w docs/backlog/STATUS.md
  materiał: docs/backlog/STATUS.md
  wynik: ekrany zmigrowane
  zostało: surowe wartości w features, przeniesione do T42

## Etap: v1.0.1 Zgodność UI z makietami

- [x] T24–T33 Motyw jasny domyślnie, dolna nawigacja, formularz rejsu, szczegóły jednostki, puste stany, ekran PDF

## Etap: v1.0.2 Porządki i testy

- [ ] Popraw kontrast okna PIN w trybie jasnym (T34) | kto: claude
  cel: tekst i przyciski okna PIN czytelne w trybie jasnym
  gotowe gdy: kontrast tekstu w oknie PIN co najmniej 4,5:1 w trybie jasnym; testy widgetów zielone
  materiał: docs/backlog/STATUS.md
- [ ] Powiększ przycisk Wstecz do 48 dp (T35, F15) | kto: claude
  cel: przycisk Wstecz łatwy do trafienia mokrą ręką
  gotowe gdy: obszar dotyku przycisku Wstecz ma co najmniej 48 × 48 dp na wszystkich ekranach; testy zielone
  materiał: docs/backlog/STATUS.md
- [ ] Napraw test vessel_edit_page (sharedPreferences) (T37) | kto: claude
  cel: test vessel_edit_page przechodzi bez zależności od stanu sharedPreferences
  gotowe gdy: `flutter test` dla vessel_edit_page zielony trzy razy z rzędu
  materiał: docs/backlog/STATUS.md
- [ ] Wydziel wspólny helper `_purposeLabel` do lib/core/i18n (T38) | kto: claude
  cel: jedna funkcja etykiety celu rejsu zamiast kopii w features
  gotowe gdy: `_purposeLabel` istnieje tylko w lib/core/i18n; testy zielone
  materiał: docs/backlog/STATUS.md
- [ ] Zrób drobne porządki T36, T39 i T40 w jednym PR | kto: claude
  cel: trzy drobne zadania porządkowe zamknięte jednym PR
  gotowe gdy: PR otwarty, CI zielone, trzy kroki zaznaczone
  materiał: docs/backlog/STATUS.md
  - [ ] T36
  - [ ] T39
  - [ ] T40
- [ ] Usuń surowe kolory, odstępy i rozmiary czcionek z features (T42) | kto: claude
  cel: features korzystają wyłącznie z tokenów motywu
  gotowe gdy: w lib/features brak literałów kolorów, odstępów i rozmiarów czcionek; testy zielone
  materiał: docs/backlog/STATUS.md
- [ ] Dopisz testy dla 10 DAO bez pokrycia (T43) | kto: claude
  cel: każde DAO ma test jednostkowy
  gotowe gdy: 10 nowych plików testów DAO, wszystkie zielone
  materiał: docs/backlog/STATUS.md
- [x] T41 Ikony morskie: rezygnacja z MarineIcons.ttf na rzecz Material Symbols (2026-11-14)
- [ ] Zastąp ikony morskie odpowiednikami z Material Symbols | kto: claude | gdzie: chmura
  cel: aplikacja nie korzysta z MarineIcons.ttf; ikony morskie mają odpowiedniki z Material Symbols
  gotowe gdy: brak odwołań do MarineIcons w kodzie; w wynik: tabela ikona → odpowiednik; testy zielone
  materiał: docs/backlog/STATUS.md

## Etap: RC1 i zamknięty test Google Play
termin: 2026-12-13

- [x] Faza 0: T50a–d, T51 (2026-06-01)
- [x] T48c (2026-07-17)
- [x] RC1 1.0.0+2 zmergowany (#121/#122, 2026-10-27)
- [ ] Przygotuj szkic zaproszenia dla testerów zamkniętego testu | kto: claude | gdzie: chmura | kiedy: 2026-11-19
  cel: gotowy tekst zaproszenia do zamkniętego testu dla znajomych i grup żeglarskich
  gotowe gdy: szkic w repozytorium (wiadomość prywatna i post do grupy), z instrukcją dołączenia do testu w Google Play; nic nie wysłane
  materiał: KARTA.md#Cel
  Możesz skorzystać z materiałów z gałęzi marketing/kampania-rc1. Wysyłka i publikacja tylko przez właściciela.
- [ ] Uruchom pełną suitę testów na PR #124 | kto: claude | gdzie: chmura | kiedy: 2026-11-21
  cel: wiadomo, czy PR #124 (fix/rc1-nagrania, marketing/kampania-rc1) można zmergować
  gotowe gdy: w wynik: liczba testów zaliczonych i niezaliczonych na gałęzi PR #124
  Jeśli na serwerze nie ma Flutter SDK, uruchom suitę w GitHub Actions albo oznacz [!] z blokadą.
- [ ] Zmerguj PR #124 po zielonej pełnej suicie testów | kto: ty | kiedy: 2026-11-22 | wymaga: zgoda
  cel: gałęzie fix/rc1-nagrania i marketing/kampania-rc1 w master przed podpisanym buildem
  gotowe gdy: PR #124 zmergowany, CI na master zielone
  materiał: KARTA.md#Pytania do właściciela
  Właściciel (2026-11-14): merge możliwy; do rozważenia, czy materiały marketingowe mają być w repozytorium.
- [ ] Wygeneruj keystore do podpisu wydania | kto: ty | gdzie: mac | kiedy: 2026-11-21 | czas: 20
  cel: klucz podpisu wydania gotowy do budowania AAB
  gotowe gdy: keystore i hasła zapisane w menedżerze haseł z kopią zapasową; plik keystore poza repozytorium
  Rozważ Play App Signing: Google trzyma klucz aplikacji, Ty klucz przesyłania.
- [~] Przygotuj politykę prywatności NaulikApp | kto: claude | gdzie: chmura | wymaga: odbiór
  cel: treść polityki, wersja HTML i odpowiedzi do Play Console gotowe do publikacji
  gotowe gdy: właściciel odebrał treść i odpowiedzi; zmiany zacommitowane
  wynik: treść, HTML i odpowiedzi do Play Console w docs/compliance/; ekran polityki w aplikacji poprawiony
  decyzja: odebrać treść polityki i odpowiedzi do Play Console
  zostało: zmiany niezacommitowane; brak danych wydawcy; publikacja pod publicznym URL
- [ ] Uzupełnij dane wydawcy w polityce prywatności | kto: ty | kiedy: 2026-11-22 | czas: 10
  cel: polityka prywatności ma pełne dane wydawcy wymagane przez Google Play
  gotowe gdy: w plikach z docs/compliance/ brak pól do uzupełnienia przy danych wydawcy
- [ ] Opublikuj politykę prywatności pod publicznym URL | kto: ty | kiedy: 2026-11-23 | czas: 15
  cel: Google Play i ekran w aplikacji wskazują ten sam publiczny adres polityki
  gotowe gdy: polityka otwiera się pod publicznym URL bez logowania, a URL wpisany w Play Console
- [ ] Zbuduj podpisany AAB 1.0.0 z master | kto: ty | gdzie: mac | kiedy: 2026-11-24 | czas: 30
  cel: podpisany build wydania gotowy do testu akceptacyjnego i Play Console
  gotowe gdy: plik AAB podpisany keystore z 21.11, zbudowany z master po merge PR #124
- [ ] Przeprowadź test akceptacyjny RC1 na podpisanym buildzie | kto: ty | kiedy: 2026-11-26
  cel: potwierdzenie, że podpisany build nadaje się do zamkniętego testu
  gotowe gdy: wszystkie scenariusze planu testów przechodzą albo błędy zapisane jako nowe zadania
  Plan testów MVP (TC-01..TC-20) usunięto z docs/testing 2026-05-29; jego odtworzenie jest w „Do rozplanowania”.
- [x] Konto Google Play założone (potwierdził właściciel 2026-11-14)
- [ ] Zbierz 12 testerów do zamkniętego testu Google Play | kto: ty | kiedy: 2026-11-27
  cel: co najmniej 12 osób z kontem Google zapisanych na liście testerów
  gotowe gdy: lista testerów w Play Console ma co najmniej 12 adresów
  - [ ] lista co najmniej 15 kandydatów (zapas na rezygnacje)
  - [ ] zaproszenia wysłane (szkic od agenta z 19.11)
  - [ ] 12 adresów na liście testerów w Play Console
  Test trwa 14 dni, więc start najpóźniej 29.11.
- [ ] Uruchom zamknięty test w Google Play (12+ testerów × 14 dni) | kto: ty | kiedy: 2026-11-29 | wymaga: zgoda
  cel: zamknięty test trwa od 29.11 do 13.12
  gotowe gdy: test w Play Console ma stan aktywny, a co najmniej 12 testerów dołączyło
  - [ ] AAB wgrany na ścieżkę testu zamkniętego
  - [ ] URL polityki prywatności w Play Console
  - [ ] lista testerów przypisana do ścieżki
- [ ] Złóż wniosek o produkcję w Google Play | kto: ty | kiedy: 2026-12-13 | wymaga: zgoda
  cel: dostęp do produkcji w Google Play po zamkniętym teście
  gotowe gdy: wniosek wysłany w Play Console po 14 dniach testu z co najmniej 12 testerami
  materiał: KARTA.md#Definicja ukończenia

## Do rozplanowania

- [x] Zebrać nowsze materiały z PC (audyt 2026-11-14)
- [ ] Wskaż zadania T48 niezbędne do v1.0.0 | kto: claude | gdzie: chmura | kiedy: 2026-11-20
  cel: wiadomo, które z zadań T48 muszą wejść przed podpisanym buildem 24.11
  gotowe gdy: w wynik: każda pozycja z kroków oznaczona „przed v1.0.0” albo „po” z uzasadnieniem
  materiał: docs/backlog/STATUS.md
  - [ ] T48a
  - [ ] T48e
  - [ ] T48g
  - [ ] T48h
  - [ ] T48m
  - [ ] T48n
  - [ ] T48q
  - [ ] T48t
  - [ ] T48v
  - [ ] T48w
  Właściciel (2026-11-14): realizujemy wszystko, co niezbędne przed v1.0.0.
- [ ] Zrealizuj zadania T48 niezbędne do v1.0.0 | kto: claude | gdzie: chmura
  cel: zadania T48 wskazane jako niezbędne zamknięte przed podpisanym buildem
  gotowe gdy: każde wskazane zadanie T48 ma zmergowany PR albo opis w zostało:
  Zaczyna się po zadaniu „Wskaż zadania T48 niezbędne do v1.0.0”.
- [ ] Ustal otwarte zadania release readiness v1.0.3 (T54–T66) po RC1 | kto: claude
  cel: wiadomo, które zadania T54–T66 zostały zamknięte w RC1, a które są otwarte
  gotowe gdy: w wynik: lista T54–T66 ze stanem; w decyzja: które otwarte są potrzebne przed 13.12
  materiał: docs/backlog/STATUS.md
- [ ] Odtwórz plan testów MVP usunięty z docs/testing 2026-05-29 | kto: claude | kiedy: 2026-11-23
  cel: plan testów manualnych (TC-01..TC-20) dostępny przed testem akceptacyjnym 26.11
  gotowe gdy: plan testów w docs/testing z historii git albo w wynik: wskazane jego nowe miejsce
