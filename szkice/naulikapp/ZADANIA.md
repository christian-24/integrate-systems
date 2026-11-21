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
- [x] Zamknij test dymny E2E (T22)
  cel: T22 zamknięty: test dymny E2E zielony, test manualny przeniesiony
  gotowe gdy: T22 oznaczony jako zrobiony w docs/backlog/STATUS.md
  materiał: docs/backlog/STATUS.md
  wynik: przyjęte 19.11 (Claude za właściciela): test dymny zielony, test manualny w T44
- [x] Dokończ migrację starych ekranów (T23)
  cel: stare ekrany korzystają z motywu i tokenów
  gotowe gdy: T23 oznaczony jako zrobiony w docs/backlog/STATUS.md
  materiał: docs/backlog/STATUS.md
  wynik: przyjęte 19.11 (Claude za właściciela): ekrany zmigrowane, surowe wartości w T42

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
- [x] Przygotuj szkic zaproszenia dla testerów zamkniętego testu | kto: claude | gdzie: chmura | kiedy: 2026-11-19
  cel: gotowy tekst zaproszenia do zamkniętego testu dla znajomych i grup żeglarskich
  gotowe gdy: szkic w repozytorium (wiadomość prywatna i post do grupy), z instrukcją dołączenia do testu w Google Play; nic nie wysłane
  materiał: KARTA.md#Cel
  Możesz skorzystać z materiałów z gałęzi marketing/kampania-rc1. Wysyłka i publikacja tylko przez właściciela.
  wynik: szkic przyjęty 19.11 (Claude za właściciela): docs/marketing/zaproszenie-testerzy-zamkniety-test.md; testerów dodajesz przez Grupę Google
- [x] Przygotuj politykę prywatności NaulikApp | kto: claude | gdzie: chmura | kiedy: 2026-11-20
  cel: treść polityki, wersja HTML i odpowiedzi do Play Console gotowe do publikacji
  gotowe gdy: właściciel odebrał treść i odpowiedzi; commit w zadaniu „Zacommituj poprawki polityki prywatności”
  wynik: treść przyjęta 19.11 (Claude za właściciela); dane wydawcy i zapis na gałęzi w kolejnych zadaniach
- [ ] Spisz listę 15 kandydatów na testerów zamkniętego testu | kto: ty | kiedy: 2026-11-20 | czas: 20
  cel: lista co najmniej 15 osób z kontem Google (zapas na rezygnacje do progu 12)
  gotowe gdy: lista 15 kandydatów zapisana poza repozytorium (adresy to dane osobowe)
  - [ ] znajomi z telefonem z Androidem i kontem Google
  - [ ] grupy żeglarskie i kluby: osoby, które odpowiedzą na post ze szkicu zaproszenia
  - [ ] przy każdej osobie adres konta Google (potrzebny przy liście e-mail w Play Console)
  Listę osób znasz tylko Ty. Trzymaj ją w menedżerze haseł albo w notatce na Macu, nie w repozytorium.
- [x] Wskaż zadania T48 niezbędne do v1.0.0 | kto: claude | gdzie: chmura | kiedy: 2026-11-20
  cel: wiadomo, które z zadań T48 muszą wejść przed podpisanym buildem 24.11
  gotowe gdy: w wynik: każda pozycja z kroków oznaczona „przed v1.0.0” albo „po” z uzasadnieniem
  materiał: docs/backlog/STATUS.md
  - [x] T48a
  - [x] T48e
  - [x] T48g
  - [x] T48h
  - [x] T48m
  - [x] T48n
  - [x] T48q
  - [x] T48t
  - [x] T48v
  - [x] T48w
  Właściciel (2026-11-14): realizujemy wszystko, co niezbędne przed v1.0.0.
  wynik: żadne nie jest niezbędne, wszystkie „po”. T48a po: makieta to logowanie Apple/Google, v1 nie ma kont. T48e po: Dziennik po redesignie to lista rejsów, filtry i FAB wpisów nie mają zastosowania. T48g po: przebudowa ekranu, obecny działa. T48h po: błędy naprawione w RC1, zostaje wygląd. T48m po: baner Premium i „Wyloguj” byłyby atrapami. T48n po: zarzut o ikonie nieaktualny. T48q po: powaga i zdjęcie to nowe funkcje z migracją bazy. T48t po: kosmetyka, przegląd 27.10 „OK”. T48v po: brak tylko przycisków zoomu i kompasu. T48w po: moduł poza MVP. Pełne uzasadnienie: docs/backlog/v1.0.2/T48-zakres-v1.0.0.md
  decyzja: zatwierdź, że żadne zadanie T48 nie wchodzi przed buildem 24.11 (makiety T48 zastąpił redesign z 08–10.2026, a RC1 ma przegląd UI z 27.10)
  zostało: ocena z kodu i przeglądu UI z 27.10, bez uruchamiania aplikacji; plik niezatwierdzony commitem (brak uprawnień do indeksu git w katalogu roboczym), zatwierdzi panel
  następne: Przejrzyj zadania T48 pod nowy prototyp (zamknij nieaktualne, przepisz resztę) | kto: claude | kiedy: 2026-12-15
- [!] Uruchom pełną suitę testów na PR #124 | kto: claude | gdzie: chmura | kiedy: 2026-11-21 | blokada: brak Flutter SDK na serwerze i brak uprawnień agenta do poleceń gh (GitHub Actions)
  cel: wiadomo, czy PR #124 (fix/rc1-nagrania, marketing/kampania-rc1) można zmergować
  gotowe gdy: w wynik: liczba testów zaliczonych i niezaliczonych na gałęzi PR #124
  Jeśli na serwerze nie ma Flutter SDK, uruchom suitę w GitHub Actions albo oznacz [!] z blokadą.
  wynik: suita nieuruchomiona, liczby testów zaliczonych i niezaliczonych brak. Na serwerze nie ma Flutter SDK (brak flutter, dart i fvm). Odczyt wyniku CI z GitHub Actions zablokowany: polecenia gh (pr view, pr checks, run list) wymagają zgody, której sesja agenta nie ma. Ustalone z lokalnego repozytorium: origin/fix/rc1-nagrania to 1 commit ponad master (534c8f0, 4 pliki w naulikapp/lib, +56/−10, bez zmian w testach); origin/marketing/kampania-rc1 to 1 commit z dokumentacją (5577d64). Workflow .github/workflows/ci.yml uruchamia `flutter analyze` i `flutter test` przy każdym PR, więc wynik dla PR #124 powinien już być w GitHub Actions. Plików nie utworzono.
  zostało: odczytać z GitHub Actions wynik zadania „analyze + test” dla PR #124 (liczba testów zaliczonych i niezaliczonych); wymaga dopuszczenia agentowi poleceń gh tylko do odczytu (gh pr checks, gh run view) albo instalacji Flutter 3.41.5 na serwerze. Nie sprawdzono, której z dwóch gałęzi dotyczy PR #124.
  następne: Odczytaj wynik CI dla PR #124 po dopuszczeniu gh w panelu | kto: claude | kiedy: 2026-11-23
- [x] Odtwórz plan testów MVP usunięty z docs/testing 2026-05-29 | kto: claude | gdzie: chmura | kiedy: 2026-11-21
  cel: plan testów manualnych TC-01..TC-20 dostępny przed testem akceptacyjnym 26.11
  gotowe gdy: plik docs/testing/plan-testow-mvp.md z TC-01..TC-20 (kroki, oczekiwany wynik, kolumna wyniku) odtworzony z historii git; w wynik: commit źródłowy
  Usunięte pliki: `git log --diff-filter=D --name-only -- docs/testing`; treść: `git show <commit>^:<ścieżka>`.
  wynik: odtworzony docs/testing/plan-testow-mvp.md: 20 przypadków TC-01..TC-20, każdy z krokami i oczekiwanym wynikiem, na końcu tabela wyników (kolumny Android, iOS, Notes). Commit źródłowy: 35cc410 (2026-05-12, „Add”, plik docs/testing/v1.0.0-mvp-test-plan.md); plik usunięty commitem 3daa56f (2026-05-29, „Clean backlog”), treść pobrana z 3daa56f^. Treść przypadków bez zmian, po angielsku jak w oryginale; dopisana tylko 6-wierszowa nota o pochodzeniu. Plik niezatwierdzony w gałęzi agenta (agent nie ma prawa zapisu do indeksu git), zatwierdzi go panel.
  zostało: planu nie porównano z RC1: opisuje aplikację z maja 2026, więc nazwy przycisków, ekranów i limit jednostek w TC-13 mogą się różnić. Plan odsyła do plików, których nie ma w repozytorium: docs/testing/bugs-v1.0.0.md, docs/testing/web-platform-notes.md, naulikapp/integration_test/mvp_smoke_test.dart.
  następne: Zaktualizuj plan testów MVP do stanu RC1 (nazwy ekranów i przycisków, TC-13) | kto: claude | kiedy: 2026-11-24
- [ ] Wygeneruj keystore do podpisu wydania | kto: ty | gdzie: mac | kiedy: 2026-11-21 | czas: 20
  cel: klucz podpisu wydania gotowy do budowania AAB
  gotowe gdy: keystore i hasła zapisane w menedżerze haseł z kopią zapasową; plik keystore poza repozytorium
  - [ ] `mkdir -p ~/klucze && keytool -genkey -v -keystore ~/klucze/naulikapp-upload.jks -keyalg RSA -keysize 2048 -validity 10000 -alias upload`
  - [ ] plik `android/key.properties` w repozytorium na Macu: storePassword, keyPassword, keyAlias=upload, storeFile=/Users/krystianstryjakiewicz/klucze/naulikapp-upload.jks
  - [x] `android/.gitignore` zawiera `key.properties` i `*.jks` (sprawdził agent 2026-11-21)
  - [ ] hasło keystore i hasło klucza w menedżerze haseł, plik .jks jako załącznik tego wpisu (kopia)
  - [x] `android/app/build.gradle.kts` czyta key.properties w signingConfigs.release (sprawdził agent 2026-11-21)
  Play App Signing: przy pierwszym wgraniu AAB Google tworzy klucz aplikacji, a ten keystore zostaje kluczem przesyłania (można go odnowić u Google).
- [ ] Uzupełnij dane wydawcy w polityce prywatności | kto: ty | kiedy: 2026-11-21 | czas: 2
  cel: polityka prywatności ma dane wydawcy wymagane przez Google Play
  pyta: Wydawca (imię i nazwisko albo firma); Adres wydawcy; E-mail kontaktowy
  Wpisz trzy pola i „Zapisz i zakończ”. Resztę zrobi agent w zadaniu „Zapisz politykę prywatności…”.
- [ ] Zmerguj PR #124 po zielonej pełnej suicie testów | kto: claude | gdzie: chmura | kiedy: 2026-11-22 | po: Uruchom pełną suitę testów na PR #124
  cel: gałęzie fix/rc1-nagrania i marketing/kampania-rc1 w master przed podpisanym buildem
  gotowe gdy: commity 534c8f0 (fix/rc1-nagrania) i 5577d64 (marketing/kampania-rc1) scalone na gałęzi uruchomienia (panel scala ją do master); testy zielone
  materiał: KARTA.md#Pytania do właściciela
  materiał: .github/workflows/ci.yml
  - [ ] scal origin/fix/rc1-nagrania i origin/marketing/kampania-rc1 na gałęzi uruchomienia (po jednym commicie ponad master: kod w naulikapp/lib i dokumentacja)
  Przekazane agentowi przy porządkach 2026-11-21: scalanie to krok techniczny, zgodę na merge właściciel dał 2026-11-14. Wypchnięcie na GitHub jest w zadaniu „Wypchnij master…” (wymaga: zgoda).
  Właściciel (2026-11-14): merge możliwy; do rozważenia, czy materiały marketingowe mają być w repozytorium.
- [x] Zrealizuj zadania T48 niezbędne do v1.0.0 | kto: claude | gdzie: chmura | kiedy: 2026-11-22 | po: Wskaż zadania T48 niezbędne
  cel: zadania T48 wskazane jako niezbędne zamknięte przed podpisanym buildem 24.11
  gotowe gdy: każde wskazane zadanie T48 zrobione na gałęzi uruchomienia (panel zapisuje gałąź i listę zmian); testy zielone
  Zadanie T48, którego nie da się zrobić przed 24.11: [!] z blokadą i nazwą zadania; nie zamykaj zadania bez niego.
  materiał: docs/backlog/STATUS.md
  materiał: docs/backlog/v1.0.2/T48-zakres-v1.0.0.md
  wynik: zamknięte przy porządkach 2026-11-21 (zbędne: lista niezbędnych zadań T48 jest pusta, wszystkie dziesięć przesunięte po v1.0.0; uzasadnienie w docs/backlog/v1.0.2/T48-zakres-v1.0.0.md)
- [ ] Zapisz politykę prywatności na gałęzi uruchomienia | kto: claude | gdzie: chmura | kiedy: 2026-11-22 | po: Przygotuj politykę prywatności NaulikApp, Uzupełnij dane wydawcy
  cel: treść polityki z danymi wydawcy, HTML, odpowiedzi do Play Console i poprawiony ekran polityki na gałęzi uruchomienia
  gotowe gdy: zmiany w katalogu uruchomienia (panel zapisuje gałąź i listę zmian); dane wydawcy z formularza wpisane; testy zielone
  materiał: docs/compliance/
  Pliki z 18.11 leżą niezacommitowane w głównym katalogu repozytorium (/home/panel/projekty/naulikapp/docs/compliance/ i ekran polityki).
  Przenieś je stamtąd; gdy nie masz dostępu, oznacz [!] z blokadą „brak dostępu do niezacommitowanych plików polityki”.
- [ ] Wypchnij master NaulikApp na GitHub i pobierz go na Macu | kto: claude | gdzie: chmura | kiedy: 2026-11-23 | wymaga: zgoda | po: Zrealizuj zadania T48, Zapisz politykę prywatności na gałęzi, Zmerguj PR #124
  cel: master na GitHubie i na Macu ma PR #124, zmiany T48 i politykę prywatności
  gotowe gdy: origin/master na GitHubie ma ten sam commit co master na serwerze (z PR #124 i polityką prywatności)
  Przekazane agentowi przy porządkach 2026-11-21: Twoja część to tylko zgoda w panelu (wypchnięcie wychodzi na zewnątrz). Pobranie na Macu to pierwszy krok zadania „Zbuduj podpisany AAB…” (`git pull`).
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
- [ ] Uruchom zamknięty test w Google Play (12+ testerów × 14 dni) | kto: ty | kiedy: 2026-11-27 | czas: 30 | po: Przeprowadź test akceptacyjny RC1, Wyślij zaproszenia do testu kandydatom, Wgraj AAB do ścieżki
  - [ ] co najmniej 12 osób dołączyło (Play Console → Testy zamknięte → Testerzy); przy mniej przypomnienie ze szkicu
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
- [ ] Przejrzyj zadania T48 pod nowy prototyp (zamknij nieaktualne, przepisz resztę) | kto: claude | kiedy: 2026-12-15

## Do rozplanowania

- [x] Zebrać nowsze materiały z PC (audyt 2026-11-14)
- [ ] Ustal otwarte zadania release readiness v1.0.3 (T54–T66) po RC1 | kto: claude
  cel: wiadomo, które zadania T54–T66 zostały zamknięte w RC1, a które są otwarte
  gotowe gdy: w wynik: lista T54–T66 ze stanem; w decyzja: które otwarte są potrzebne przed 13.12
  materiał: docs/backlog/STATUS.md
- [~] Porządki spraw właściciela: pytania w karcie i Twoje zadania | kto: claude | gdzie: chmura | kiedy: 2026-11-21 | wymaga: odbiór
  cel: zostawić właścicielowi tylko sprawy, których nie rozstrzygnie nikt inny (pieniądze, dane prawne i firmowe, działania nieodwracalne albo na zewnątrz, zakres i terminy, rzeczy fizyczne, fakty znane tylko jemu); w tym zadaniu wolno zmieniać inne wiersze ZADANIA.md (bez terminów i tytułów) i dopisywać odpowiedzi w KARTA.md
  - [x] Pytania w „Pytania do właściciela”: każde, które rozstrzygniesz sam albo sprawdzisz w plikach i repozytorium, opatrz wierszem `   Odpowiedź: … (agent, DECYZJE.md)` i zapisz decyzję w DECYZJE.md z `- Kto: agent`; powtórzone pytanie połącz z pierwszym
  - [x] Zadania kto: ty: te, które może zrobić agent, przepisz na kto: claude; zbędne i zdublowane zamknij `[x]` z `wynik: zamknięte przy porządkach 2026-11-21 (powód)`; podobne połącz w jedno
  - [x] Odbiory prac wewnętrznych bez `decyzja:` i bez kodu do scalenia zamknij `[x]`
  - [x] Zostaw najwyżej jedno pytanie bez odpowiedzi; pozostałe sprawy właściciela muszą być zadaniami kto: ty z czasem w minutach
  gotowe gdy: w KARTA.md najwyżej jedno pytanie bez odpowiedzi, każda decyzja agenta ma wpis w DECYZJE.md, a w wyniku jest lista zmian: ile pytań rozstrzygnięto, ile zadań przekazano agentom, ile zamknięto, co zostało właścicielowi
  - [x] Na koniec stan `[~]`, `wymaga: odbiór` i `decyzja: przyjęcie porządków` z listą zmian w `wynik:`
  materiał: KARTA.md#Pytania do właściciela
  wynik: Pytania: w karcie 6 pytań, wszystkie miały już odpowiedź właściciela, bez odpowiedzi zostaje 0; agent rozstrzygnął 2 wątki otwarte w tych odpowiedziach (pyt. 2: materiały marketingowe zostają w repozytorium w docs/marketing; pyt. 4: żadne zadanie T48 nie wchodzi przed v1.0.0); powtórzonych pytań nie było. Zadania przekazane agentom: 2 („Zmerguj PR #124…” na kto: claude; „Wypchnij master…” na kto: claude z wymaga: zgoda). Zamknięte: 1 („Zrealizuj zadania T48 niezbędne do v1.0.0”, lista pusta). Odbiory prac wewnętrznych do zamknięcia: 0 (żadne zadanie nie czekało na odbiór). W „Wygeneruj keystore…” odhaczone 2 kroki sprawdzone w repozytorium (.gitignore, build.gradle.kts); spod „Zmerguj PR #124…” usunięty zabłąkany krok z tego zadania. Właścicielowi zostaje 10 zadań kto: ty, razem 257 minut: lista 15 testerów (20), keystore na Macu (20), dane wydawcy (2), publikacja polityki pod URL (15), podpisany AAB na Macu (30), wgranie AAB do Play Console (30), wysyłka zaproszeń (30), test akceptacyjny (60), start zamkniętego testu (30), wniosek o produkcję (20); do tego jedna zgoda w panelu na wypchnięcie master. Trzy decyzje agenta w DECYZJE.md (2026-11-21). Plików w repozytorium nie zmieniono.
  decyzja: przyjęcie porządków: 2 zadania przekazane agentom (merge PR #124, wypchnięcie master za Twoją zgodą), 1 zamknięte (realizacja T48, lista pusta), materiały marketingowe zostają w repozytorium, żadne zadanie T48 przed v1.0.0
  zostało: „Zmerguj PR #124…” czeka na zablokowane „Uruchom pełną suitę testów na PR #124” (na serwerze nie ma Flutter SDK, agent nie ma odczytu GitHub Actions), więc termin 22.11 jest zagrożony. Wiersze karty „Do uzupełnienia” (czy plan TC-01..TC-20 jest warunkiem wydania; budżet, backend) leżą poza sekcją pytań i zostały bez zmian.
