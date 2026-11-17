# Audyt księgi 0.2: zestawienie iteracji 2

2026-11-12. Trzy niezależne przeglądy: Fable, Opus, Sonnet (`iteracja-2-*.md`), z weryfikacją faktów w internecie.
Werdykt wszystkich trzech: **tak po poprawkach**. Ustaleń krytycznych mniej niż w iteracji 1 (4 → 3), wszystkie dotyczą etapu 1 i mają konkretne poprawki.

## Ustalenia

| # | Waga | Zgodność | Problem | Poprawka w wersji 0.3 |
|---|---|---|---|---|
| 1 | krytyczna | 3/3 | Etap 1 nie ma drogi zdarzeń z Maca na PC (Tailscale dopiero w etapie 2, Mac tylko czyta). | Decyzja D8. |
| 2 | krytyczna | 1/3 (Opus), wysoka w 2/3 | Kopia stanu na GitHubie może zawierać dane poufne (tytuły maili, treść sesji); historia git nie znika po 12 miesiącach. | Decyzja D9; zbieracz zapisuje tylko metadane; klasy danych z kolumną GitHub. |
| 3 | krytyczna | 1/3 (Sonnet), wysoka i średnia w 2/3 | Rozliczanie `claude -p` na subskrypcji niepewne (doniesienia o osobnej puli kredytu od 15.06.2026, niepotwierdzone oficjalnie). | Etap 1 w całości bez modelu (S1 i S8 skryptem); sprawdzenie rozliczeń przed etapem 3; budżet w kredycie. |
| 4 | wysoka | 3/3 | Bot odpowie każdemu, kto go znajdzie. | Jeden dozwolony `chat_id`, reszta odrzucana i logowana; long polling; od etapu 3 drugie potwierdzenie dla scalenia i wysyłki. |
| 5 | wysoka | 3/3 | Sygnał życia nie wykrywa martwego bota, nieudanego push ani milczącego Maca. | Sygnał z pętli bota po udanym cyklu; osobne kontrole: zbieracz Maca, raport 7:00. |
| 6 | wysoka | 3/3 | „Poprawny stan” i testy bez definicji. | Lista kontrolna etapu 1 i plik z przypadkami testowymi. |
| 7 | wysoka | 1/3 (Fable) | Zadania w dwóch miejscach: `ZADANIA.md` w projektach i repozytorium stanu. | Zadania zostają w repozytoriach projektów; repozytorium stanu trzyma tylko inwentarz, zdarzenia i backlog pomysłów. |
| 8 | wysoka | 1/3 (Opus) | Telegram kasuje nieodebrane wiadomości po 24 h. | Przypadek brzegowy; po powrocie bot pisze o możliwej utracie. |
| 9 | średnia | 3/3 | Usługi na PC: start bez logowania, aktualizacje, zasilanie; Mac: launchd, uprawnienia dostępu do dysku, uśpienie. | Wymagania w sekcji 9 i w teście S10. |
| 10 | średnia | 2/3 | Sesje Claude Code to nieudokumentowany format; `id` niejednoznaczne. | `id` dla każdego typu; `github:<owner/repo>:pr:N`; zdarzenie „nie rozumiem pliku”. |
| 11 | średnia | 2/3 | Automatyczne przejścia stanu kłócą się z sekcją 8; 14 dni → backlog zapełni backlog. | Wyjątek w sekcji 8 z powiadomieniem; po 14 dniach archiwum; trwała lista wykluczeń. |
| 12 | średnia | 1/3 (Fable) | Gmail przez OAuth w trybie testowym traci token po 7 dniach. | Przed etapem 2 wybrać IMAP z hasłem aplikacji albo przekierowanie. |
| 13 | niska | 3/3 | Cisza nocna i limit pilnych bez wyjątków; BPMN dla 5 procesów to nadmiar; Notion, Codex, Życie rozpraszają. | „System nie działa” poza limitem; tabele kroków zamiast BPMN w etapie 1; etapy 3–4 w załączniku. |

## Fakty sprawdzone przez audytorów
- Tailscale Personal: bezpłatny, do 6 użytkowników. Jedno źródło zewnętrzne mówi o użytku niekomercyjnym — do sprawdzenia, jeśli projekty są komercyjne.
- healthchecks.io: bezpłatny plan, 20 kontroli, powiadomienia przez Telegram.
- Telegram: long polling bez otwartych portów; nieodebrane wiadomości kasowane po 24 h; boty bez szyfrowania end-to-end.
- Gmail OAuth w trybie testowym: token wygasa po 7 dniach.
- Subskrypcja Claude: dozwolone zwykłe, indywidualne użycie Claude Code i Agent SDK; osobna pula kredytu dla trybu nieinteraktywnego — doniesienia, niepotwierdzone.

## Decyzje właściciela

| # | Decyzja | Rekomendacja |
|---|---|---|
| D8 | Droga Mac → PC w etapie 1 | Przez repozytorium stanu: Mac zapisuje tylko własny katalog `mac/`, PC tylko resztę. Bez nowych instalacji; Tailscale w etapie 2. |
| D9 | Co może leżeć w prywatnym repozytorium na GitHubie | Tylko metadane: nazwy projektów, ścieżki, daty, liczby, stany, tytuły zadań. Bez treści maili, sesji i danych klientów; wtedy szyfrowanie zbędne. |
| D10 | Czy projekty są komercyjne, dla klientów | Odpowiedź wpływa na klasę „poufne” i na plan Tailscale. |
| D11 | Mac w nocy | Raport 7:00 pokazuje dane z ostatniej pracy Maca, z godziną. |
