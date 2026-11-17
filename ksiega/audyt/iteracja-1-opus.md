# Audyt księgi 0.1: iteracja 1, model Opus

Przegląd niezależny: audytor czytał tylko KSIEGA.md, bez wglądu w inne audyty. 2026-11-12.

## Ocena ogólna
Dobrze ustawione cel, model pracy i scenariusze. Za mało mechaniki: skąd dane, gdzie jedno źródło prawdy, jak telefon zadaje pytanie, co agentom wolno. „Najpierw pełna inwentaryzacja” odsuwa pierwszą wartość; LinkedIn, Facebook i portale mają dziś zerowy realny dostęp.

## Ustalenia
| # | Waga | Sekcja | Problem | Propozycja |
|---|---|---|---|---|
| 1 | krytyczna | 6, S1, S8, 1 | ntfy działa tylko w jedną stronę; nie ma kanału telefon → system dla pytań i zapisu pomysłu; miara „< 1 min z telefonu” bez mechanizmu. | Wybrać kanał wejścia: aplikacja Claude z dostępem do stanu, bot (np. Telegram) albo panel przez Tailscale; zapisać jako decyzję architektury. |
| 2 | krytyczna | 6, 10 | Brak jednego źródła prawdy i połączenia Mac–PC–chmura. | Magazyn stanu (git albo baza na PC), transport (Tailscale/SSH), jeden zapisujący, reszta czyta. |
| 3 | krytyczna | 5, 12, S2, S7 | LinkedIn: API stron wymaga zatwierdzenia (Community Management API), dla profili praktycznie brak; Facebook Graph tylko strony i App Review; portale bez API, scraping łamie regulaminy. | Poczta (alerty, RSS) jako szyna kanałów bez API, więc Gmail jest warunkiem; S2 i S7 poza wersją 1. |
| 4 | wysoka | 1 vs 8, 9 | „Niczego nie rejestruje ręcznie” przeczy P2, P9, S4, S8, Życiu; 10 min/dzień niepoliczone. | „Rejestruje tylko decyzje”; czas właściciela dla każdego procesu. |
| 5 | wysoka | P8, 10 | Brak modelu uprawnień agentów (zmiany, wysyłanie, publikacja, sekrety); treści z poczty i portali to droga do prompt injection. | Sekcja „Uprawnienia i zgody”: akcje wymagające odbioru, piaskownica, treści z kanałów nigdy jako polecenia. |
| 6 | wysoka | 6 | ntfy bez konta: kto zgadnie temat, czyta. | Token dostępu albo własna instancja; minimum danych w treści. |
| 7 | wysoka | S6, 8 | Limity Max i Codex tylko w S6; brak budżetu, priorytetów, oceny czy 24/7 mieści się w warunkach planu; brak kosztów całości. | Wymagania kosztowe: limit miesięczny, kolejność przy braku limitu, zachowanie przy przekroczeniu. |
| 8 | wysoka | 2, 11 | System 1 duży i zależny od niezrobionego połączenia z PC; system 2 dla 3 znanych projektów może ruszyć od razu. | Odwrócić: cienki system 2 dla 3 projektów, inwentarz dokładać źródło po źródle. |
| 9 | wysoka | 5, P5 | Brak modelu zdarzenia: pola, przypisanie (reguły czy LLM), deduplikacja, retencja, „ważne”. | Schemat zdarzenia, jawne reguły ważności, kolejka „bez projektu”. |
| 10 | średnia | 3, 4, 5 | Turtle raz projekt, raz epik; decyzje P2 nie pasują do stanów. | Jeden słownik stanów; jednoznacznie Turtle. |
| 11 | średnia | 3 vs 7 | „Każdy projekt ma taką samą księgę” vs lekka księga Życia; pełna bramka zabije małe zlecenia. | Dwa progi księgi z kryterium (czas, kwota). |
| 12 | średnia | 12.1, 10 | Notion rekomendowany i zarazem brak; synchronizacja dwustronna = konflikty, limit ok. 3 zapytań/s. | Notion tylko lustro do odczytu albo odłożyć. |
| 13 | średnia | brak | Brak kopii, odtwarzania, historii zmian, dziennika audytu. | Stan w git z kopią poza PC, sekrety w menedżerze haseł, procedura odtworzenia. |
| 14 | średnia | 5 | Sesje, poczta, kalendarz z danymi klientów przetwarzane przez modele w chmurze; brak klasyfikacji danych. | Klasyfikacja: co może opuścić maszynę, co idzie do modelu, Notion, powiadomień. |
| 15 | niska | 11 | 12 BPMN i 3–4 audyty przed budową to nadmiar. | BPMN tylko P5–P8, reszta tabelą kroków. |

## Brakujące scenariusze i przypadki brzegowe
- Pytanie z telefonu przy wyłączonym PC: odpowiedź ze znacznikiem świeżości.
- Agent w nocy wisi, zapętla się, zużywa limit; brak limitu czasu i wycofania zmian.
- Agent proponuje działanie zewnętrzne (mail, post): ścieżka zgody z telefonu.
- Gdzie jest przycisk odbioru z S3, skoro ntfy nie ma logiki zwrotnej.
- Wygasłe tokeny (GitHub, Notion, Gmail, Claude na PC).
- Zdarzenie pasuje do dwóch projektów; zmiana nazwy; repozytorium współdzielone.
- Nadmiar powiadomień: limit dzienny, cisza nocna.
- Utrata lub kradzież telefonu czy laptopa: odcięcie dostępu.
- Phishing udający powiadomienie z LinkedIna lub portalu.
- Przeprowadzka serca do chmury: test bez zmian w danych i procesach.
- Życie: choroba, urlop, zmiana celu; przerwa nie jest porażką.
- Właściciel nie robi przeglądu kandydatów: rosnąca kolejka.

## Pierwszy krok
Cienki pion dla Backend, TestNow i Turtle (backlog): zapisać je w formacie `standard/` (10 minut właściciela), na PC codziennie rano `pm.py`, 3–5 wierszy przez ntfy z tokenem. Ukończone, gdy przez 5 dni roboczych rano przychodzi poprawny stan i właściciel z niego korzysta. Potem pytanie z telefonu i GitHub.

## Pytania do właściciela
1. Jak zadawać pytanie z telefonu: aplikacja Claude, bot w komunikatorze, panel przez prywatną sieć?
2. Czy agenci mogą kiedykolwiek sami wysyłać lub publikować, czy zawsze po odbiorze?
3. Jaki miesięczny koszt systemu poza subskrypcjami?
4. Notion: źródło prawdy, lustro czy pominąć w wersji 1?
5. LinkedIn, Facebook, portale w wersji 1 tylko przez alerty e-mail (wymaga podłączenia poczty)?
