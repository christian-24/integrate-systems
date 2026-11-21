# Decyzje: NaulikApp

Każda decyzja to osobny wpis, najnowsze na górze. Nagłówek wpisu: `## RRRR-MM-DD: krótki tytuł`.
Uzupełnione danymi z PC (audyt 2026-11-14).

## 2026-11-21: Adres polityki prywatności i pozostałe pola polityki ustala agent
- Kontekst: porządki spraw właściciela (drugie przejście). W treści polityki poza danymi wydawcy zostały trzy puste pola: publiczny adres URL, okres przechowywania korespondencji i dostawca poczty. Zadanie „Opublikuj politykę…” zostawiało właścicielowi wybór adresu i dopilnowanie, żeby adres w aplikacji był taki sam.
- Decyzja: adres polityki to `https://christian-24.github.io/naulikapp-polityka/` (GitHub Pages, osobne publiczne repozytorium `naulikapp-polityka` na koncie właściciela, plik `index.html`). Okres przechowywania korespondencji: 12 miesięcy od zakończenia sprawy. Dostawcę poczty agent ustala z domeny adresu e-mail podanego przez właściciela. Agent wpisuje te wartości i przygotowuje `docs/compliance/index.html` w zadaniu „Zapisz politykę prywatności na gałęzi uruchomienia”.
- Skutki: właściciel tylko zakłada repozytorium o tej nazwie, wgrywa gotowy plik, włącza Pages i wkleja adres w Play Console; nie wybiera adresu i nie poprawia aplikacji. Odwracalne do chwili publikacji: inny adres to zmiana jednego wiersza w polityce.
- Kto: agent

## 2026-11-21: Numer buildu 1.0.0+3 ustawia agent
- Kontekst: krok „wersja 1.0.0 i versionCode wyższy niż w RC1” leżał w zadaniu właściciela „Zbuduj podpisany AAB…”, a to zmiana w `naulikapp/pubspec.yaml`. RC1 miał 1.0.0+2.
- Decyzja: agent ustawił `version: 1.0.0+3` na gałęzi tego zadania; właściciel na Macu tylko pobiera master i buduje.
- Skutki: jeden krok mniej po stronie właściciela. Zmiana jednego wiersza, testów nie uruchomiono (brak Flutter SDK na serwerze). Odwracalne.
- Kto: agent

## 2026-11-21: Plan TC-01..TC-20 jest warunkiem startu zamkniętego testu
- Kontekst: karta ma w „Definicji ukończenia” wiersz „Do uzupełnienia: czy manualny plan testów TC-01..TC-20 jest warunkiem wydania”. W ZADANIA.md test akceptacyjny 26.11 już poprzedza start testu 27.11.
- Decyzja: tak, w brzmieniu z zadania „Przeprowadź test akceptacyjny RC1…”: przed startem zamkniętego testu przechodzą wszystkie scenariusze albo błędy są zapisane jako zadania; start wstrzymuje tylko błąd blokujący (utrata danych, awaria przy zapisie rejsu, zamknięciu dziennika albo eksporcie PDF).
- Skutki: bez zmian w zadaniach i terminach; wiersz w karcie zostaje do uzupełnienia przez właściciela (agent dopisuje w karcie tylko odpowiedzi na pytania). Odwracalne.
- Kto: agent

## 2026-11-21: Merge PR #124 i wypchnięcie master robi agent
- Kontekst: porządki spraw właściciela; zadania „Zmerguj PR #124…” i „Wypchnij master NaulikApp…” były przypisane właścicielowi, choć to kroki techniczne (git). Zgodę na merge właściciel dał 2026-11-14.
- Decyzja: oba zadania przechodzą na agenta. Merge: agent scala commity 534c8f0 i 5577d64 na gałęzi uruchomienia, panel scala ją do master. Wypchnięcie na GitHub: agent, z polem `wymaga: zgoda`, bo wychodzi na zewnątrz. Pobranie na Macu zostaje pierwszym krokiem zadania „Zbuduj podpisany AAB…”.
- Skutki: właścicielowi zostaje 10 zadań (257 minut) i jedna zgoda na wypchnięcie; merge nadal czeka na wynik pełnej suity testów. Odwracalne: wystarczy przywrócić `kto: ty`.
- Kto: agent

## 2026-11-21: Żadne zadanie T48 nie wchodzi przed v1.0.0
- Kontekst: właściciel (2026-11-14): „zrealizujmy wszystko niezbędne”. Analiza z 20.11 (`docs/backlog/v1.0.2/T48-zakres-v1.0.0.md`) wykazała, że żadne z zadań T48 a/e/g/h/m/n/q/t/v/w nie jest niezbędne: makiety T48 zastąpił redesign z 08–10.2026, a RC1 ma przegląd UI z 27.10.
- Decyzja: wszystkie dziesięć zadań T48 po v1.0.0; zadanie „Zrealizuj zadania T48 niezbędne do v1.0.0” zamknięte jako zbędne (lista pusta).
- Skutki: podpisany build 24.11 nie czeka na T48; przegląd T48 pod nowy prototyp zaplanowany na 2026-12-15. Ocena z kodu i przeglądu UI, bez uruchamiania aplikacji.
- Kto: agent

## 2026-11-21: Materiały marketingowe zostają w repozytorium
- Kontekst: pytanie 2 w karcie; właściciel dopuścił merge gałęzi `marketing/kampania-rc1` i zostawił do rozważenia, czy marketing ma być w gicie.
- Decyzja: dokumenty marketingowe (plany, szkice tekstów) zostają w repozytorium w `docs/marketing/`; nie zakładamy osobnego miejsca. Dane osobowe (lista testerów, adresy) poza repozytorium.
- Skutki: gałąź `marketing/kampania-rc1` (1 commit, sama dokumentacja) wchodzi do master razem z PR #124. Odwracalne: katalog można później przenieść.
- Kto: agent

## 2026-11-14: Material Symbols zamiast własnych ikon, T48 niezbędne przed v1.0.0
- Kontekst: T41 zablokowane od 16.05; otwarte zadania T48.
- Decyzja: rezygnacja z MarineIcons.ttf na rzecz Material Symbols; przed v1.0.0 realizujemy wszystkie niezbędne zadania T48.
- Skutki: brakuje 12 testerów do zamkniętego testu; konto Google Play założone.
- Kto: właściciel

## 2026-10-27: Wydanie przez zamknięty test Google Play
- Kontekst: RC1 1.0.0+2 zmergowany (#121/#122).
- Decyzja: zamknięty test w Google Play (12+ testerów × 14 dni) do 2026-12-13, potem wniosek o produkcję; iOS poza v1; cel 500 instalacji do 2027-04-30.
- Skutki: blokery wydania: keystore, polityka prywatności, test akceptacyjny RC1, konto Play.
- Kto: właściciel

## 2026-05-28: v1.0.2 jako wydanie porządkowe przed v1.1
- Kontekst: po v1.0.0 i v1.0.1 zostały drobne znaleziska z autopilota i audytu testów.
- Decyzja: zebrać je w v1.0.2 (T34–T44), bez nowych funkcji; jedno źródło stanu zadań w `docs/backlog/STATUS.md`.
- Skutki: nowe funkcje dopiero w v1.1.0.
- Kto: właściciel, Claude Code

## 2026-05-16: UI zgodne z makietami (v1.0.1)
- Kontekst: audyt UI wykazał rozbieżności aplikacji z makietami.
- Decyzja: jasny motyw navy domyślnie, ciemny bursztynowy w profilu (T24); usunięte kafelki pulpitu (T26); konfiguracja jednostki odłożona z onboardingu (T28); ekran PDF jako podgląd (T33, opcja A).
- Skutki: makiety są wzorcem dla aplikacji.
- Kto: właściciel, Claude Code

## 2026-05-10: Rdzeń 12 modułów zamknięty, zakres MVP
- Kontekst: zakończone projektowanie modułów M-01 do M-12.
- Decyzja: MVP to fundament UI oraz moduły voyage, port-move i issues; specyfikacja UI w `docs/ui/UI-SPEC.md`.
- Skutki: pozostałe moduły rdzenia i infrastrukturalne do zaprojektowania lub zbudowania później.
- Kto: właściciel

## 2026-05-08: Free Tier bez synchronizacji, degradacja planu zachowuje dane
- Kontekst: zasady subskrypcji (F12) i zamykania rejsu.
- Decyzja: dane Free wyłącznie lokalne, bez wyjątków (F12); po spadku z premium do Free dane historyczne zostają (F22); zamknięty rejs jest niezmienny dla wpisów dziennika (F23).
- Skutki: backend obsługuje w Free tylko tożsamość OAuth.
- Kto: właściciel

## 2026-05-07: Fundamenty architektury F1–F20
- Kontekst: start projektowania architektury.
- Decyzja: aplikacja dla jednostek niegigantycznych (F1); dane lokalnie, chmura jako lustro (F8); sealed log z PDF lokalnie i w backendzie (F9); logowanie OAuth Google/Apple (F11); subskrypcja hybrydowa z Free Tier (F12); PIN tylko przy akcjach oficjalnych (F16); przytrzymanie przy akcjach nieodwracalnych (F19).
- Skutki: UI projektowany pod kapitana w trudnych warunkach (F15).
- Kto: właściciel
