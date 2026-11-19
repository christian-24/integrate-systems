# Zadania: NaulikApp

> Jedyna lista zadań projektu. Czyta ją panel i agenci.
> Wiersz: `- [ ] Tytuł | kto: claude | gdzie: pc | kiedy: RRRR-MM-DD | pora: noc | czas: 30 | wymaga: zgoda`
> Stany: `[ ]` do zrobienia, `[~]` w toku, `[!]` zablokowane (dodaj `blokada: powód`), `[x]` zrobione.
> Pola są opcjonalne. kto: claude, codex, ty. gdzie: pc, mac, chmura. pora: dzień, noc. czas: minuty Twojej pracy. wymaga: zgoda, odbiór.
> Etap to nagłówek `## Etap: nazwa` i wiersz `termin: RRRR-MM-DD` pod nim. Etap bez otwartych zadań jest zamknięty.
> Szczegóły zadania: wcięte wiersze pod zadaniem (cel:, gotowe gdy:, materiał:, kroki `- [ ]`, wynik:, decyzja:, zostało:).
> Uzupełnione danymi z PC (audyt 2026-11-14). Stany T34–T44 z 2026-05-29; RC1 zmergowany 2026-10-27, więc część z nich mogła zostać zamknięta.
> Ścieżka krytyczna do startu zamkniętego testu najpóźniej 27.11: keystore 21.11, T48 i merge PR #124 22.11, scalenie i master na GitHubie 23.11,
> polityka pod publicznym URL 23.11, podpisany AAB i wgranie do ścieżki zamkniętego testu 24.11, zaproszenia 25.11, test akceptacyjny i 12 testerów 26.11,
> start testu 27.11, wniosek o produkcję 11.12 (14 dni testu); termin etapu 13.12 to zapas na sprawdzenie wersji przez Google.
> Pole `po:` wskazuje zadania z tego pliku, które muszą być zrobione wcześniej.

## Etap: v1.0.0 MVP

- [x] T01 Motyw, typografia i tokeny
- [x] T01c Refaktor wspólnych widgetów na tokeny
- [x] T02 Migracja schematu bazy v5 do v6
- [x] T03–T11 Jednostka i rejs: walidacja MMSI, PIN, tworzenie, lista, szczegóły, zamknięcie z przytrzymaniem
- [x] T12–T17 Ruch portowy i usterki: tabele, DAO, formularze, oś czasu
- [x] T18–T19 Sealed log i eksport PDF
- [x] T20–T21 Limity Free Tier i onboarding
- [~] Zamknij test dymny E2E (T22) | wymaga: odbiór
  cel: T22 zamknięty: test dymny E2E zielony, test manualny przeniesiony
  gotowe gdy: T22 oznaczony jako zrobiony w docs/backlog/STATUS.md
  materiał: docs/backlog/STATUS.md
  wynik: test dymny E2E zielony
  zostało: test manualny przeniesiony do T44
  decyzja: sprawdź w docs/backlog/STATUS.md, czy T22 jest oznaczony jako zrobiony; jeśli tak, zamknij zadanie
- [~] Dokończ migrację starych ekranów (T23) | wymaga: odbiór
  cel: stare ekrany korzystają z motywu i tokenów
  gotowe gdy: T23 oznaczony jako zrobiony w docs/backlog/STATUS.md
  materiał: docs/backlog/STATUS.md
  wynik: ekrany zmigrowane
  zostało: surowe wartości w features, przeniesione do T42
  decyzja: sprawdź w docs/backlog/STATUS.md, czy T23 jest oznaczony jako zrobiony (surowe wartości przeniesione do T42); jeśli tak, zamknij zadanie

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
- [~] Przygotuj szkic zaproszenia dla testerów zamkniętego testu | kto: claude | gdzie: chmura | kiedy: 2026-11-19 | wymaga: odbiór
  cel: gotowy tekst zaproszenia do zamkniętego testu dla znajomych i grup żeglarskich
  gotowe gdy: szkic w repozytorium (wiadomość prywatna i post do grupy), z instrukcją dołączenia do testu w Google Play; nic nie wysłane
  materiał: KARTA.md#Cel
  Możesz skorzystać z materiałów z gałęzi marketing/kampania-rc1. Wysyłka i publikacja tylko przez właściciela.
  wynik: szkic w docs/marketing/zaproszenie-testerzy-zamkniety-test.md (commit 0c07892 na gałęzi agent/2026-11-19-przygotuj-szkic-zaproszenia-dla-testerow; fakty zgodne z kodem: pakiet pl.naulik.app, Android 7+, 1.0.0+2): wiadomość prywatna i wersja krótka, post do grupy/forum, instrukcja dołączenia w Google Play z rozwiązywaniem problemów, przypomnienie po tygodniu; nic nie wysłane
  decyzja: zatwierdź treść i wybierz sposób dodawania testerów (Grupa Google, rekomendowane, albo lista adresów e-mail); uzupełnij [LINK-GRUPA], [LINK-TEST], [KONTAKT]; żeby zdążyć do 13.12, dwunasty tester musi dołączyć do 29.11
  zostało: wysyłka i publikacja (tylko właściciel); linki do testu powstaną dopiero po wgraniu buildu do ścieżki zamkniętego testu w Play Console
- [~] Przygotuj politykę prywatności NaulikApp | kto: claude | gdzie: chmura | kiedy: 2026-11-20 | wymaga: odbiór
  cel: treść polityki, wersja HTML i odpowiedzi do Play Console gotowe do publikacji
  gotowe gdy: właściciel odebrał treść i odpowiedzi; commit w zadaniu „Zacommituj poprawki polityki prywatności”
  wynik: treść, HTML i odpowiedzi do Play Console w docs/compliance/; ekran polityki w aplikacji poprawiony
  decyzja: odebrać treść polityki i odpowiedzi do Play Console
  zostało: zmiany niezacommitowane; brak danych wydawcy; publikacja pod publicznym URL
- [ ] Spisz listę 15 kandydatów na testerów zamkniętego testu | kto: ty | kiedy: 2026-11-20 | czas: 20
  cel: lista co najmniej 15 osób z kontem Google (zapas na rezygnacje do progu 12)
  gotowe gdy: lista 15 kandydatów zapisana poza repozytorium (adresy to dane osobowe)
  - [ ] znajomi z telefonem z Androidem i kontem Google
  - [ ] grupy żeglarskie i kluby: osoby, które odpowiedzą na post ze szkicu zaproszenia
  - [ ] przy każdej osobie adres konta Google (potrzebny przy liście e-mail w Play Console)
  Listę osób znasz tylko Ty. Trzymaj ją w menedżerze haseł albo w notatce na Macu, nie w repozytorium.
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
- [ ] Uruchom pełną suitę testów na PR #124 | kto: claude | gdzie: chmura | kiedy: 2026-11-21
  cel: wiadomo, czy PR #124 (fix/rc1-nagrania, marketing/kampania-rc1) można zmergować
  gotowe gdy: w wynik: liczba testów zaliczonych i niezaliczonych na gałęzi PR #124
  Jeśli na serwerze nie ma Flutter SDK, uruchom suitę w GitHub Actions albo oznacz [!] z blokadą.
- [ ] Odtwórz plan testów MVP usunięty z docs/testing 2026-05-29 | kto: claude | gdzie: chmura | kiedy: 2026-11-21
  cel: plan testów manualnych TC-01..TC-20 dostępny przed testem akceptacyjnym 26.11
  gotowe gdy: plik docs/testing/plan-testow-mvp.md z TC-01..TC-20 (kroki, oczekiwany wynik, kolumna wyniku) odtworzony z historii git; w wynik: commit źródłowy
  Usunięte pliki: `git log --diff-filter=D --name-only -- docs/testing`; treść: `git show <commit>^:<ścieżka>`.
- [ ] Wygeneruj keystore do podpisu wydania | kto: ty | gdzie: mac | kiedy: 2026-11-21 | czas: 20
  cel: klucz podpisu wydania gotowy do budowania AAB
  gotowe gdy: keystore i hasła zapisane w menedżerze haseł z kopią zapasową; plik keystore poza repozytorium
  - [ ] `mkdir -p ~/klucze && keytool -genkey -v -keystore ~/klucze/naulikapp-upload.jks -keyalg RSA -keysize 2048 -validity 10000 -alias upload`
  - [ ] plik `android/key.properties` w repozytorium na Macu: storePassword, keyPassword, keyAlias=upload, storeFile=/Users/krystianstryjakiewicz/klucze/naulikapp-upload.jks
  - [ ] `android/.gitignore` zawiera `key.properties` i `*.jks`; `git status` nie pokazuje key.properties
  - [ ] hasło keystore i hasło klucza w menedżerze haseł, plik .jks jako załącznik tego wpisu (kopia)
  - [ ] `android/app/build.gradle` czyta key.properties w signingConfigs.release; gdy nie czyta, zgłoś to jako zadanie dla Claude
  Play App Signing: przy pierwszym wgraniu AAB Google tworzy klucz aplikacji, a ten keystore zostaje kluczem przesyłania (można go odnowić u Google).
- [ ] Uzupełnij dane wydawcy w polityce prywatności | kto: ty | kiedy: 2026-11-21 | czas: 5
  cel: polityka prywatności ma pełne dane wydawcy wymagane przez Google Play
  gotowe gdy: pytanie 5 w KARTA.md ma odpowiedź z nazwą wydawcy, adresem i e-mailem kontaktowym
  materiał: KARTA.md#Pytania do właściciela
  Dane wpisuje agent do plików polityki w docs/compliance/ (treść, HTML, odpowiedzi do Play Console) w zadaniu „Zapisz politykę prywatności…”.
- [ ] Zmerguj PR #124 po zielonej pełnej suicie testów | kto: ty | kiedy: 2026-11-22 | czas: 10 | po: Uruchom pełną suitę testów na PR #124
  cel: gałęzie fix/rc1-nagrania i marketing/kampania-rc1 w master przed podpisanym buildem
  gotowe gdy: PR #124 zmergowany, CI na master zielone
  materiał: KARTA.md#Pytania do właściciela
  - [ ] github.com, repozytorium naulikapp, Pull requests → #124: wynik suity z zadania wyżej zielony, „Merge pull request”
  Właściciel (2026-11-14): merge możliwy; do rozważenia, czy materiały marketingowe mają być w repozytorium.
- [ ] Zrealizuj zadania T48 niezbędne do v1.0.0 | kto: claude | gdzie: chmura | kiedy: 2026-11-22 | po: Wskaż zadania T48 niezbędne
  cel: zadania T48 wskazane jako niezbędne zamknięte przed podpisanym buildem 24.11
  gotowe gdy: każde wskazane zadanie T48 zrobione na gałęzi uruchomienia (panel zapisuje gałąź i listę zmian); testy zielone
  Zadanie T48, którego nie da się zrobić przed 24.11: [!] z blokadą i nazwą zadania; nie zamykaj zadania bez niego.
  materiał: docs/backlog/STATUS.md
- [ ] Zapisz politykę prywatności na gałęzi uruchomienia | kto: claude | gdzie: chmura | kiedy: 2026-11-22 | po: Przygotuj politykę prywatności NaulikApp, Uzupełnij dane wydawcy
  cel: treść polityki z danymi wydawcy, HTML, odpowiedzi do Play Console i poprawiony ekran polityki na gałęzi uruchomienia
  gotowe gdy: zmiany w katalogu uruchomienia (panel zapisuje gałąź i listę zmian); dane wydawcy z odpowiedzi na pytanie 5 w KARTA.md wpisane; testy zielone
  materiał: docs/compliance/
  materiał: KARTA.md#Pytania do właściciela
  Pliki z 18.11 leżą niezacommitowane w głównym katalogu repozytorium (/home/panel/projekty/naulikapp/docs/compliance/ i ekran polityki).
  Przenieś je stamtąd; gdy nie masz dostępu, oznacz [!] z blokadą „brak dostępu do niezacommitowanych plików polityki”.
- [ ] Przejrzyj zmiany agenta T48 i polityki prywatności i scal w panelu | kto: ty | kiedy: 2026-11-23 | czas: 20 | po: Zrealizuj zadania T48, Zapisz politykę prywatności na gałęzi
  cel: zmiany T48 i polityka prywatności w master repozytorium NaulikApp na serwerze
  gotowe gdy: oba uruchomienia scalone w panelu do master (bez push)
  - [ ] panel, Agenci: uruchomienie „Zrealizuj zadania T48…”, lista zmian i diff przejrzane, scalone
  - [ ] to samo dla „Zapisz politykę prywatności…”
  Gdy scalenie zwraca 409 przez niezacommitowane zmiany w głównym katalogu: `ssh ops@2.29.181.133`, potem
  `sudo -u panel git -C /home/panel/projekty/naulikapp stash push -m przed-scaleniem` i scal ponownie.
- [ ] Wypchnij master NaulikApp na GitHub i pobierz go na Macu | kto: ty | kiedy: 2026-11-23 | czas: 10 | po: Przejrzyj zmiany agenta T48, Zmerguj PR #124
  cel: master na GitHubie i na Macu ma PR #124, zmiany T48 i politykę prywatności
  gotowe gdy: CI na master zielone; na Macu `git log -1` pokazuje ten sam commit co GitHub
  - [ ] `ssh ops@2.29.181.133`, `sudo -u panel git -C /home/panel/projekty/naulikapp pull --no-rebase origin master` (wnosi PR #124)
  - [ ] `sudo -u panel git -C /home/panel/projekty/naulikapp push origin master`
  - [ ] na Macu w repozytorium naulikapp: `git switch master && git pull`
- [ ] Opublikuj politykę prywatności pod publicznym URL | kto: ty | kiedy: 2026-11-23 | czas: 15 | po: Wypchnij master NaulikApp na GitHub
  cel: Google Play i ekran w aplikacji wskazują ten sam publiczny adres polityki
  gotowe gdy: polityka otwiera się pod publicznym URL bez logowania, a URL wpisany w Play Console
  materiał: docs/compliance/
  - [ ] plik HTML z docs/compliance/ na stronie bez logowania, np. GitHub Pages z osobnego publicznego repozytorium (Settings → Pages → Deploy from branch)
  - [ ] Play Console → aplikacja → Zasady i programy → Treści w aplikacji → Polityka prywatności: wpisany URL
  - [ ] adres w aplikacji (ekran polityki) taki sam jak w Play Console
- [ ] Zbuduj podpisany AAB 1.0.0 z master | kto: ty | gdzie: mac | kiedy: 2026-11-24 | czas: 30 | po: Wygeneruj keystore, Wypchnij master NaulikApp na GitHub
  cel: podpisany build wydania gotowy do testu akceptacyjnego i Play Console
  gotowe gdy: plik AAB podpisany keystore z 21.11, zbudowany z master po merge PR #124, zmian T48 i polityki prywatności
  - [ ] na Macu: `git pull`, `flutter clean && flutter build appbundle --release`
  - [ ] plik build/app/outputs/bundle/release/app-release.aab; podpis: `keytool -printcert -jarfile build/app/outputs/bundle/release/app-release.aab` pokazuje alias upload
  - [ ] wersja 1.0.0 i versionCode wyższy niż w RC1 (pubspec.yaml)
- [ ] Wgraj AAB do ścieżki zamkniętego testu | kto: ty | kiedy: 2026-11-24 | czas: 30 | po: Zbuduj podpisany AAB, Opublikuj politykę prywatności
  cel: wersja 1.0.0 w ścieżce zamkniętego testu wysłana do sprawdzenia przez Google z zapasem przed startem testu
  gotowe gdy: w Play Console wersja w ścieżce zamkniętego testu ma stan „W trakcie sprawdzania” albo „Dostępna”; lista testerów przypisana do ścieżki
  - [ ] Play Console → aplikacja → Testowanie → Testy zamknięte: ścieżka (np. Alpha), kraje: Polska
  - [ ] Testerzy: Grupa Google (rekomendacja ze szkicu zaproszenia) albo lista adresów e-mail; skopiuj link do dołączenia
  - [ ] Utwórz wersję: Play App Signing włączone, wgraj app-release.aab, opis zmian, zapisz
  - [ ] Treści w aplikacji kompletne (polityka, dostęp do aplikacji, reklamy, klasyfikacja, bezpieczeństwo danych), „Wyślij do sprawdzenia”
  Sprawdzenie pierwszej wersji nowej aplikacji może trwać kilka dni; dlatego wgranie 24.11, a start testu najpóźniej 27.11.
- [ ] Wyślij zaproszenia do testu kandydatom z listy | kto: ty | kiedy: 2026-11-25 | czas: 30 | po: Wgraj AAB do ścieżki, Przygotuj szkic zaproszenia dla testerów, Spisz listę 15 kandydatów
  cel: co najmniej 15 kandydatów dostało zaproszenie z instrukcją dołączenia do testu
  gotowe gdy: zaproszenia wysłane do wszystkich osób z listy; liczba potwierdzeń wpisana w notatce pod tym zadaniem
  materiał: docs/marketing/zaproszenie-testerzy-zamkniety-test.md
  - [ ] w szkicu wpisane [LINK-GRUPA], [LINK-TEST] z Play Console i [KONTAKT]
  - [ ] wiadomość prywatna do każdej osoby z listy 15 kandydatów
  Wysyłka tylko przez Ciebie. Kto nie odpowie do 26.11, dostaje jedno przypomnienie (szkic przypomnienia w tym samym pliku).
- [ ] Przeprowadź test akceptacyjny RC1 na podpisanym buildzie | kto: ty | kiedy: 2026-11-26 | czas: 60 | po: Zbuduj podpisany AAB, Odtwórz plan testów MVP
  cel: potwierdzenie, że podpisany build nadaje się do zamkniętego testu
  gotowe gdy: wszystkie scenariusze TC-01..TC-20 przechodzą albo błędy zapisane jako nowe zadania
  materiał: docs/testing/plan-testow-mvp.md
  docs/testing/plan-testow-mvp.md: plik powstanie w zadaniu „Odtwórz plan testów MVP…” (po:).
  - [ ] instalacja z Play (jesteś testerem własnej ścieżki) albo `bundletool build-apks --bundle=app-release.aab --output=naulik.apks --ks=$HOME/klucze/naulikapp-upload.jks --ks-key-alias=upload` i `bundletool install-apks --apks=naulik.apks`
  - [ ] TC-01..TC-20 przeprowadzone, wynik wpisany w kolumnie wyniku planu
  Błąd blokujący: poprawka, nowy AAB z wyższym versionCode i ponowne wgranie przed 27.11.
- [x] Konto Google Play założone (potwierdził właściciel 2026-11-14)
- [ ] Sprawdź liczbę testerów zamkniętego testu (co najmniej 12) | kto: ty | kiedy: 2026-11-26 | czas: 10 | po: Wyślij zaproszenia do testu kandydatom
  cel: co najmniej 12 osób z kontem Google dołączyło do zamkniętego testu
  gotowe gdy: Play Console (Testy zamknięte → Testerzy) albo Grupa Google pokazuje co najmniej 12 osób
  materiał: docs/marketing/zaproszenie-testerzy-zamkniety-test.md
  - [ ] Play Console → Testowanie → Testy zamknięte → ścieżka → Testerzy: liczba osób, które dołączyły
  - [ ] przy mniej niż 12: przypomnienie ze szkicu do osób, które nie dołączyły, i kolejni kandydaci z grup żeglarskich
- [ ] Uruchom zamknięty test w Google Play (12+ testerów × 14 dni) | kto: ty | kiedy: 2026-11-27 | czas: 30 | po: Przeprowadź test akceptacyjny RC1, Sprawdź liczbę testerów, Wgraj AAB do ścieżki
  cel: zamknięty test trwa od 27.11 do 11.12
  gotowe gdy: wersja w ścieżce zamkniętego testu ma stan „Dostępna”, a co najmniej 12 testerów dołączyło
  - [ ] URL polityki prywatności w Play Console
  - [ ] lista testerów przypisana do ścieżki
  - [ ] wersja sprawdzona przez Google i dostępna dla testerów
  Test trwa 14 dni od dnia, w którym 12 testerów jest zapisanych; start najpóźniej 27.11.
- [ ] Złóż wniosek o produkcję w Google Play | kto: ty | kiedy: 2026-12-11 | czas: 20 | po: Uruchom zamknięty test w Google Play
  cel: dostęp do produkcji w Google Play po zamkniętym teście
  gotowe gdy: wniosek wysłany w Play Console po 14 dniach testu z co najmniej 12 testerami
  materiał: KARTA.md#Definicja ukończenia

## Do rozplanowania

- [x] Zebrać nowsze materiały z PC (audyt 2026-11-14)
- [ ] Ustal otwarte zadania release readiness v1.0.3 (T54–T66) po RC1 | kto: claude
  cel: wiadomo, które zadania T54–T66 zostały zamknięte w RC1, a które są otwarte
  gotowe gdy: w wynik: lista T54–T66 ze stanem; w decyzja: które otwarte są potrzebne przed 13.12
  materiał: docs/backlog/STATUS.md
