# Audyt księgi 0.1: iteracja 1, model Sonnet

Przegląd niezależny: audytor czytał tylko KSIEGA.md, bez wglądu w inne audyty. 2026-11-12.

## Ocena ogólna
Dobra struktura (dwa systemy, model pracy, bramka), ale szersza niż jedna osoba zbuduje, a najkruchsze założenia (kanały zewnętrzne, Mac–PC, limity Claude) potraktowane jako szczegóły. Brak wymagań niefunkcjonalnych i wskazania źródła prawdy. Pierwszą wartość da wąski pion: inwentarz + statusy + ntfy, bez kanałów marketingowych i Życia.

## Ustalenia
| # | Waga | Sekcja | Problem | Propozycja |
|---|---|---|---|---|
| 1 | krytyczna | 6, 5 | Brak mechanizmu połączenia Mac–PC (transport, uwierzytelnienie, tryb przy wyłączonym PC); P1 wymaga zbieracza na każdej maszynie. | Lekki zbieracz na każdej maszynie wysyła zdarzenia do jednego magazynu; wybrać transport (np. Tailscale + HTTP albo repozytorium GitHub jako szyna); tryb awaryjny. |
| 2 | krytyczna | brak | Brak wymagań niefunkcjonalnych: sekrety na PC 24/7, prywatność (poczta, sesje z danymi klientów), koszty, kopie i odtwarzanie. | Nowa sekcja: sekrety w menedżerze, najmniejsze uprawnienia, budżet miesięczny, kopia magazynu i test odtworzenia. |
| 3 | krytyczna | 5, P5, S2, S7 | LinkedIn/Facebook (profile prywatne) i portale nie mają API do powiadomień; scraping łamie regulaminy i grozi blokadą. | Kanały bez oficjalnego API tylko przez e-maile z powiadomieniami; S2 i S7 jako „best effort” poza wersją 1; bez scrapingu. |
| 4 | wysoka | 2, 11 | „System 1 przed 2” i pełna dokumentacja przed kodem opóźniają wartość o tygodnie. | Cienki pion P1 (Mac) → P2 → P6 → P7 w tydzień; BPMN tylko dla procesów budowanych w danym kroku. |
| 5 | wysoka | 5, P6, S6 | Limity Max współdzielone z pracą interaktywną; stanu limitu nie da się pewnie odczytać. | Statusy i inwentarz liczone skryptami bez LLM; LLM tylko do podsumowań; kolejka z priorytetem i budżet limitu dla agentów w tle. |
| 6 | wysoka | 12.1, 10 | Moduł „jak Jira” i Notion jako tablica naraz: dwa źródła prawdy, konflikty, limity API Notion. | Źródło prawdy: pliki w repozytorium; Notion tylko widok jednostronny albo poza wersją 1; bez synchronizacji dwustronnej. |
| 7 | wysoka | 1 | „Niczego nie rejestruje ręcznie” sprzeczne z P2, P9, S4, S8, S9; cel 10 minut niemierzalny. | Policzyć obciążenie; domyślne reguły (auto-archiwum), partie po 10 kandydatów, limit pytań dziennie; zmienić na „minimalizuje”. |
| 8 | wysoka | P5, P7 | Brak modelu zdarzenia: przypisanie, deduplikacja, reguły ważności, poprawianie przypisań. | Schemat zdarzenia (źródło, czas, id zewnętrzne, projekt albo „nieprzypisane”, ważność); reguły w konfiguracji; kolejka „nieprzypisane” w raporcie. |
| 9 | średnia | 6 | ntfy.sh bez konta: nazwa kanału to jedyne zabezpieczenie, treść idzie przez obcy serwer. | Długi losowy temat, w treści tylko tytuł i link; własna instancja, gdy treści wrażliwe. |
| 10 | średnia | 3, P12 | Życie zajmuje model i procesy, źródła nieustalone, dane zdrowotne to kategoria szczególna. | Poza wersją 1; w modelu tylko pole „obszar”. |
| 11 | średnia | 7 | Pełna bramka nieproporcjonalna dla małych i odziedziczonych projektów. | Księga lekka i pełna; istniejące projekty „w realizacji” z długiem dokumentacji. |
| 12 | średnia | 4 | Turtle raz epik, raz projekt w backlogu; stany tylko dla projektu. | Turtle jako projekt w stanie „backlog”; epik tylko jako grupa zadań. |
| 13 | średnia | 5, 12.4 | Sesje Claude w chmurze i format sesji lokalnych bez stabilnego API. | Inwentarz na GitHubie i folderach; sesje jako wzbogacenie. |
| 14 | niska | 11 | Brak kryterium zakończenia audytu i scalania uwag. | Koniec, gdy dwie kolejne iteracje bez ustaleń krytycznych i wysokich; scala właściciel. |
| 15 | niska | P11, 7.6 | Porównanie zysków wymaga danych (czas, koszt), których system nie zbiera. | Dziennik z automatycznych zdarzeń; zyski jako pole opcjonalne. |

## Brakujące scenariusze i przypadki brzegowe
- Pierwsze P1: setki kandydatów (śmieci, klony), partie do kwalifikacji.
- Tożsamość projektu Mac vs PC: zdalne repo albo pierwszy commit, nie nazwa.
- PC wyłączony lub aktualizacja Windows: kolejka, wykrycie „martwego serca”, zewnętrzny heartbeat.
- Awaria powiadomień: cisza nieodróżnialna od spokoju.
- Wygasłe logowania (GitHub, Notion, Gmail, Claude): jedno powiadomienie, bez lawiny.
- Agent zmienia plik edytowany przez właściciela; przerwane zadanie; idempotencja; pętla zdarzeń.
- Odbiór z iPhone'a przy słabej łączności; odrzucenie i wersje poprawek.
- Sekrety z repozytoriów i sesji trafiające do strumienia, Notion, ntfy; poufność zleceń.
- Zmiana szablonu maila z powiadomieniem: parser milczy.
- S1 bez danych z jakiegoś źródła: „dane z X sprzed N godzin”.
- Strefy czasowe, godziny ciszy.
- Awaria dysku PC, przypadkowe usunięcie projektu.

## Pierwszy krok
Na Macu jeden skrypt bez LLM: skanuje foldery z repozytoriami i sesje Claude Code, zapisuje kandydatów (klucz tożsamości, ostatnia aktywność, liczba commitów) do pliku inwentarza, wysyła podsumowanie przez ntfy. Właściciel kwalifikuje 10 pierwszych; dla zatwierdzonych działa „jakie są statusy”.

## Pytania do właściciela
1. Miesięczny budżet na narzędzia i jaka część limitu Max dla agentów w tle?
2. Czy na PC i w chmurze są dane klientów, które nie mogą trafić do Notion lub ntfy.sh?
3. Kanały bez API tylko przez e-maile z powiadomieniami i poza wersją 1?
4. Źródło prawdy w repozytorium GitHub, Notion tylko do podglądu albo wcale w wersji 1?
5. Ile mniej więcej projektów i folderów na Macu i PC; auto-archiwizacja nieaktywnych?
