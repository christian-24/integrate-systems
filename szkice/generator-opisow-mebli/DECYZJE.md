# Decyzje: Opisarnia (generator opisów mebli)

Każda decyzja to osobny wpis, najnowsze na górze. Nagłówek wpisu: `## RRRR-MM-DD: krótki tytuł`.
Szkic z kopii na Macu; źródła: decyzje/decyzje.json i docs/adr/ (ADR 0001–0030). Uzupełnione danymi z PC (audyt 2026-11-14).

## 2026-11-21: Porządki: wdrożenie SEC-2 i SEC-4 wykonuje agent za zgodą
- Kontekst: zadanie „Wdróż poprawki SEC-2 i SEC-4 na produkcję” było u właściciela (20 min) i składało się z poleceń w terminalu (push, sprawdzenie CI, `caddy validate`, `curl`).
- Decyzja: zadanie przechodzi na agenta z polem `wymaga: zgoda`; właściciel tylko zgadza się na wdrożenie.
- Skutki: gdy agent nie ma uprawnienia do push albo dostępu do serwera Opisarni, zadanie kończy się blokadą z nazwą brakującego uprawnienia. Odwracalne: wystarczy przywrócić `kto: ty`.
- Kto: agent

## 2026-11-21: Porządki: grupy na Facebooku wyszukuje agent, dubel zamknięty
- Kontekst: „Wybierz 3–5 grup sprzedawców na Facebooku i przeczytaj regulaminy” było u właściciela (30 min); obok wisiało zadanie „Dokończ: nazw i regulaminów grup…” z tym samym zakresem i dopiskiem o przepisach o mailach marketingowych.
- Decyzja: listę grup z zasadami o promocji przygotuje agent (marketing/grupy-facebook.md w folderze karty); „Dokończ…” zamknięte jako dubel, a sprawdzenie przepisów o mailach przeniesione do „Przygotuj teksty 3 maili aktywacyjnych z oceną RODO”.
- Skutki: u właściciela zostaje dołączenie do grup i pisanie w nich. Regulamin grupy prywatnej może być widoczny dopiero po dołączeniu; agent zaznaczy to przy grupie.
- Kto: agent

## 2026-11-21: Porządki: firmy z uwagami w wiadomości 1 (STIPA, Ramaro i cztery bez potwierdzonego eksportu)
- Kontekst: zadanie „Przygotuj szkice wiadomości 1…” zostawiło otwarty wybór: STIPA i Ramaro mają strony po niemiecku, a przy Alan Meble, Meble North, Miloni i VERYSIMPL draft nie potwierdza sprzedaży za granicę. Plan (marketing/plan-10-kont.md, punkt 5) każe pomijać firmy, które mają już opisy po niemiecku.
- Decyzja: STIPA pominięta (ma niemiecką wersję sklepu). Ramaro dostaje zaproszenie; wiadomość 1 tylko wtedy, gdy opisy produktów nie są po niemiecku. Cztery firmy bez potwierdzonego eksportu zostają z szablonem: odpowiedź „nie mamy opisów po niemiecku” też otwiera rozmowę.
- Skutki: 23 zaproszenia zamiast 24. Fakty pochodzą z researchu z czerwca i lipca; właściciel sprawdza firmę 2 minuty przed kontaktem i może zdecydować inaczej.
- Kto: agent

## 2026-11-21: Porządki: identyfikatory kont własnych jako zadanie właściciela
- Kontekst: pytanie 11 w KARTA.md ma odpowiedź przyjmującą sposób (podać identyfikatory raz), ale samych liczb nie ma; zna je tylko właściciel. Bez nich pomiar 23.11 liczy konto z testu rejestracji z 18.11 jako konto Free.
- Decyzja: nowe zadanie „Podaj identyfikatory kont własnych i testowych do pomiaru” (właściciel, 5 min, 2026-11-23) zamiast kolejnego pytania w karcie; wpisanie do metryki.md zrobi agent. Zadanie „Zdecyduj go/no-go” dostało czas 15 min.
- Skutki: w KARTA.md nie ma pytania bez odpowiedzi. Zadania „Przejrzyj stare filmy przed nagraniem filmu C” (skutek pytania 6) nie zakładam: filmy nagrywa teraz panel ze scenariusza, a filmu C nie ma w harmonogramie do 30.11.
- Kto: agent

## 2026-11-18: Maile weryfikacyjne przywrócone
- Kontekst: przy rejestracji nie przychodził mail weryfikacyjny; Brevo wyłączył nieużywany klucz SMTP 14.10, więc nikt nie mógł dokończyć rejestracji (0 kont).
- Decyzja: nowy klucz SMTP Brevo w .env produkcji (/home/deploy/generator-opisow-mebli, nie /opt jak w docs/deploy-hetzner.md), restart backendu i workera.
- Skutki: rejestracja działa; promocja może ruszyć. Klucz ujawniony w rozmowie do usunięcia w Brevo.
- Kto: właściciel

## 2026-11-18: Pierwsze 10 kont: wariant B
- Kontekst: pomiar startowy 18.11: 0 kont, 0 aktywnych, 0 płacących; checkpoint 30.11 wymaga co najmniej 10 kont Free.
- Decyzja: plan z marketing/plan-10-kont.md w wariancie B: 4 posty LinkedIn, 3 filmy, 24 firmy w 3 partiach i 10–15 wiadomości do znajomych z branży; 0 zł, ok. 8 h w 12 dni. Najpierw sprawdzenie rejestracji (mail weryfikacyjny).
- Skutki: publikuje i pisze do ludzi tylko właściciel; punkt kontrolny 25.11 (mniej niż 4 konta uruchamia rezerwę).
- Kto: właściciel

## 2026-11-14: Faza marketing i terminy etapów
- Kontekst: produkcja aktualna, Stripe live, JDG zarejestrowana.
- Decyzja: projekt przechodzi w fazę marketingu (promocja i ocena zwrotu); terminy: produkcja 17.11, checkpoint 30.11, go/no-go 23.12, ZDJ-5 tylko po „go” w styczniu 2027.
- Skutki: widok „Pokaz” rozwijany dalej po poprawie UI.
- Kto: właściciel

## 2026-10-29: Silnik Claude Haiku z zapasowym Mistralem
- Kontekst: wybór dostawcy LLM w produkcji.
- Decyzja: Claude Haiku jako główny silnik, Mistral jako zapas; przełączenie od 2026-11-13 (#123, ADR 0045).
- Skutki: backend produkcyjny potrzebuje klucza Anthropic; wg stanu z 06.11 go nie miał.
- Kto: właściciel, Claude Code

## 2026-10-27: Cele walidacji zamiast bramki 200 adresów
- Kontekst: bramka ADR 0001 niespełniona; Brevo wyłączył klucz SMTP 14.10.
- Decyzja: cele do 2026-12-23: 40 kont Free, 20 aktywnych, 3 płacących; checkpoint 30.11 (mniej niż 10 kont → zmiana kanałów).
- Skutki: formalna decyzja go/no-go przesunięta na 23.12. Rekomendacja z tego dnia: faza „utrzymanie + walidacja”.
- Kto: właściciel, Claude Code

## 2026-06-21: Auto-strojenie promptu z granicami przeciw dopasowaniu do zbioru testowego
- Kontekst: jakość opisów stroiliśmy ręcznie.
- Decyzja: automatyczna pętla wariant, ocena, wybór, z ograniczeniami przeciw overfittingowi (ADR 0030).
- Skutki: zmiany promptu przechodzą przez ocenę na zbiorze ewaluacyjnym.
- Kto: właściciel, Claude Code

## 2026-06-17: Ewaluacja promptu oddzielona od providera produkcyjnego
- Kontekst: harness strojenia używa sędziego AI.
- Decyzja: sędzia (OpenAI nano) działa tylko offline, z konfiguracją rozłączną od produkcji (ADR 0029).
- Skutki: produkcja zostaje na providerze zgodnym z RODO.
- Kto: właściciel, Claude Code

## 2026-06-17: Język niemiecki dla wszystkich, bez blokady planem
- Kontekst: DE był zablokowany w POST /generate.
- Decyzja: odblokowanie DE dla wszystkich użytkowników, także w demo anonima (ADR 0027).
- Skutki: quota anonima liczona per język.
- Kto: właściciel, Claude Code

## 2026-06-16: Bezpieczeństwo: gate skanu zależności, anonimizacja faktur, real-IP, jednolity 401
- Kontekst: audyt SEC-3, SEC-5, SEC-1 przed wejściem płacących.
- Decyzja: pip-audit i npm audit w CI, anonimizacja faktur przy usunięciu konta, real-IP za proxy, 401 zamiast 403 przeciw enumeracji użytkowników (ADR 0023–0026).
- Skutki: SEC-2 i SEC-4 nadal otwarte.
- Kto: właściciel, Claude Code

## 2026-06-13: Jeden prefiks /api i rewrite w proxy
- Kontekst: uruchomienie bez Dockera nie działało przez niespójne ścieżki.
- Decyzja: front woła tylko /api/*, proxy usuwa prefiks (ADR 0021).
- Skutki: działają oba tryby, Docker i natywny.
- Kto: właściciel, Claude Code

## 2026-06-10: Stripe i generacja wsadowa
- Kontekst: Faza 1, płatności i import.
- Decyzja: synchronizacja subskrypcji i idempotencja webhooków Stripe, faktury lokalne z interfejsem KSeF, batch przez Celery z pollingiem (ADR 0016–0019).
- Skutki: Stripe działa w trybie testowym; klucze produkcyjne podaje właściciel.
- Kto: właściciel, Claude Code

## 2026-06-08: Retencja historii 90 dni
- Kontekst: historia treści to dane klientów (RODO).
- Decyzja: retencja 90 dni z opcją usunięcia (ADR 0012); hasła hashowane argon2id (ADR 0010).
- Skutki: zadanie czyszczące w Celery beat.
- Kto: właściciel, Claude Code

## 2026-06-07: Routing SPA i sesja w cookie httpOnly
- Kontekst: front bez routingu i bez sesji.
- Decyzja: react-router-dom v6, sesja w cookie httpOnly z globalną obsługą 401 (ADR 0007, 0009).
- Skutki: trasy konta za RequireAuth.
- Kto: właściciel, Claude Code

## 2026-06-05: JDG i Stripe Billing
- Kontekst: forma działalności i płatności.
- Decyzja: jednoosobowa działalność, Stripe Billing, faktury pod KSeF przez ifirma/inFakt (ADR 0006).
- Skutki: _Do uzupełnienia: czy JDG jest zarejestrowana._
- Kto: właściciel

## 2026-06-05: Tani model i cennik 49/149/399 zł
- Kontekst: koszt LLM i cennik.
- Decyzja: tani model jako opcja kosztowa, cennik Solo 49, Pro 149, Max 399 zł (ADR 0005).
- Skutki: każdy model inny niż Mistral wymaga oceny rezydencji UE przed produkcją.
- Kto: właściciel

## 2026-06-05: Hosting Hetzner Cloud w UE
- Kontekst: gdzie hostować.
- Decyzja: Hetzner Cloud VPS, region DE, wszystko w Dockerze (ADR 0004).
- Skutki: runbook w docs/deploy-hetzner.md.
- Kto: właściciel

## 2026-06-05: Mistral API jako subprocesor (RODO)
- Kontekst: przetwarzanie danych klientów przez LLM.
- Decyzja: Mistral API, siedziba i dane w UE, bez trenowania na danych (ADR 0003).
- Skutki: DPA z Mistral do podpisania przed produkcją.
- Kto: właściciel

## 2026-06-05: Stack FastAPI, PostgreSQL 16, Redis 7, React i Vite
- Kontekst: wybór architektury.
- Decyzja: Python 3.12 + FastAPI, PostgreSQL 16, Redis 7, React 18 + Vite, LLM za interfejsem LLMProvider (ADR 0002).
- Skutki: Azure-ready przez konteneryzację.
- Kto: właściciel

## 2026-06-05: MVP jako darmowy tool walidacyjny
- Kontekst: ryzyko zbudowania produktu bez popytu.
- Decyzja: darmowy generator i lista mailowa; bramka go/no-go 200 adresów z branży w 4 tygodnie (ADR 0001).
- Skutki: bramka niespełniona; 2026-10-27 zastąpiona celami do 23.12.
- Kto: właściciel
