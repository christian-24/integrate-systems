# Decyzje: Opisarnia (generator opisów mebli)

Każda decyzja to osobny wpis, najnowsze na górze. Nagłówek wpisu: `## RRRR-MM-DD: krótki tytuł`.
Szkic z kopii na Macu; źródła: decyzje/decyzje.json i docs/adr/ (ADR 0001–0030). Uzupełnione danymi z PC (audyt 2026-11-14).

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
