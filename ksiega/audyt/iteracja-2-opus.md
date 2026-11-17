# Audyt księgi 0.2: iteracja 2, model Opus

Przegląd niezależny: audytor czytał tylko KSIEGA.md 0.2, bez wglądu w poprzednie audyty; fakty sprawdzał w internecie. 2026-11-12.

## Ocena ogólna
Spójna, dobrze ogranicza etap 1; luka blokująca: brak drogi zdarzeń Mac → PC; ryzyko wycieku danych poufnych przez kopię repozytorium na GitHubie. Werdykt: **tak po poprawkach**.

## Ustalenia
| # | Waga | Sekcja | Problem | Propozycja |
|---|---|---|---|---|
| 1 | krytyczna | 5, 14 | Etap 1 nie ma drogi Mac → PC (Tailscale w etapie 2, Mac tylko do odczytu). | Tailscale do etapu 1 albo „skrzynka Maca” w repozytorium, do której Mac pcha, a PC pobiera i scala. |
| 2 | krytyczna | 5, 7, 9 | Kopia repozytorium na GitHubie może zawierać tytuły i treść poufną (poczta, sesje, kalendarz); retencja nie usuwa historii git. | Szyfrowanie (git-crypt, age) albo w repozytorium tylko dane jawne; zbieracz „tylko metadane”; retencja z historią git. |
| 3 | wysoka | 5, 9 | Do bota może napisać każdy. | Lista dozwolonych `chat_id`; reszta odrzucana i logowana; w kryteriach etapu 1. |
| 4 | wysoka | S8, 13 | Telegram kasuje nieodebrane aktualizacje po 24 h; dłuższy przestój PC gubi pomysły i kliknięcia. | Przypadek brzegowy; po powrocie bot informuje o możliwej utracie. |
| 5 | wysoka | 9, S10 | Sygnał życia z systemu, nie z bota ani zbieracza. | Sygnał z pętli bota; osobne kontrole dla zbieracza Maca i raportu 7:00. |
| 6 | wysoka | 9, 5 | Uruchomienia w tle mogą mieć osobną pulę kredytu; limit 10 dziennie może być nierealny. | Sprawdzenie warunków w etapie 1; budżet w kredycie, nie w liczbie uruchomień. |
| 7 | średnia | 14, 1 | Kryteria niemierzalne. | Lista kontrolna (3 projekty, stan, liczba zadań, świeżość < 24 h); plik 20 zdarzeń; czas od powiadomienia do kliknięcia. |
| 8 | średnia | 14 | Mac śpi w nocy: raport 7:00 na starych danych. | „Świeżość z ostatniej pracy Maca”; launchd przy wybudzeniu i co godzinę. |
| 9 | średnia | 9, 17 | D7 „przyjęte” i zarazem „do potwierdzenia”. | Ujednolicić. |
| 10 | średnia | 4, 8 | System sam zmienia stan (14 dni, P4), a sekcja 8 wymaga odbioru. | Wyjątek dla przejść automatycznych z tabeli i powiadomienie o każdym. |
| 11 | średnia | 7 | `github:pr:123` nie jest unikalne. | `github:<owner/repo>:pr:123`; bez id źródła: skrót treści i czasu. |
| 12 | niska | 5, 11 | Notion, Codex, P12 rozpraszają przy etapie 1. | Załącznik „etapy 3–4”. |

## Brakujące scenariusze i przypadki brzegowe
- Start usług na PC bez logowania (Harmonogram zadań albo usługa).
- Dwa procesy zapisują stan naraz: blokada albo jeden zapisujący.
- Nieudany push: alarm.
- Kolejka zbieracza bez końca, zepsuty JSONL: limit i walidacja.
- Zmiana czasu CET/CEST: raport nie dwa razy i nie wcale.
- Uprawnienia macOS (pełny dostęp do dysku) dla launchd; bez nich zbieracz po cichu nic nie widzi.
- Które pola sesji czyta zbieracz.
- Utrata dysku PC: odtworzenie serca z GitHuba.
- Link „w sieci prywatnej” na iPhonie bez Tailscale.
- Odrzucony kandydat wraca w kolejnej inwentaryzacji: trwała lista wykluczeń.

## Sprawdzone fakty
- Tailscale Personal: 0 USD, do 6 użytkowników, urządzenia bez limitu (tailscale.com/pricing).
- healthchecks.io Hobbyist: bezpłatnie, 20 kontroli, powiadomienia przez Telegram (healthchecks.io/pricing, healthchecks.io/integrations/telegram).
- Telegram: long polling bez otwartych portów; webhook i getUpdates wykluczają się; nieodebrane aktualizacje kasowane po 24 h (core.telegram.org/bots/api).
- Subskrypcja Claude: limity Pro i Max zakładają zwykłe, indywidualne użycie Claude Code i Agent SDK; logowanie OAuth dopuszczone dla kupującego (code.claude.com/docs/en/legal-and-compliance).
- Osobna pula kredytu dla `claude -p` od 15.06.2026: tylko źródła zewnętrzne, niepotwierdzone oficjalnie; sprawdzić na stronie rozliczeń konta.
