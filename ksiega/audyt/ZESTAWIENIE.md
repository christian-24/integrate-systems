# Audyt księgi 0.1: zestawienie iteracji 1

2026-11-12. Trzy niezależne przeglądy: Opus, Sonnet, Haiku (pliki `iteracja-1-*.md`).
Kolumna „Zgodność” mówi, ilu audytorów zgłosiło problem niezależnie.

## Ustalenia

| # | Waga | Zgodność | Problem | Poprawka w wersji 0.2 |
|---|---|---|---|---|
| 1 | krytyczna | 3/3 | LinkedIn i Facebook (profile prywatne) oraz portale ze zleceniami nie mają API do zdarzeń; scraping łamie regulaminy i grozi blokadą konta. | Kanały bez API tylko przez e-maile z powiadomieniami (wymaga podłączenia poczty); S2 i S7 w etapie 2; zakaz scrapingu. |
| 2 | krytyczna | 3/3 | Brak połączenia Mac–PC–chmura i jednego źródła prawdy; „niezależność od miejsca serca” to deklaracja. | Zbieracz na każdej maszynie wysyła zdarzenia do serca; prywatna sieć (np. Tailscale); stan w prywatnym repozytorium git, jeden zapisujący. |
| 3 | krytyczna | 1/3 (Opus) | Brak kanału telefon → system: ntfy tylko wysyła, nie da się z niego zapytać o stan, zapisać pomysłu ani odebrać pracy. | Wybrać jeden kanał dwustronny na iPhone (decyzja D1). |
| 4 | krytyczna | 3/3 | Limity Max i koszty bez budżetu; agenci w tle zabierają limit pracy interaktywnej. | Statusy i inwentarz liczone skryptami bez modelu; model tylko do podsumowań i pracy; dzienny budżet uruchomień; kolejka z priorytetem; sprawdzić warunki automatyzacji w planie. |
| 5 | wysoka | 3/3 | Kolejność „pełny system 1, potem 2” i pełna dokumentacja odsuwają pierwszą wartość o tygodnie. | Cienki pion najpierw (patrz „Pierwszy krok”); BPMN tylko dla procesów budowanych w danym kroku. |
| 6 | wysoka | 3/3 | „Niczego nie rejestruje ręcznie” przeczy P2, P9, S4, S8; 10 minut dziennie niepoliczone. | „Rejestruje tylko decyzje”; czas właściciela przy każdym procesie; kandydaci partiami, domyślnie backlog, najwyżej 3 pytania dziennie. |
| 7 | wysoka | 3/3 | Brak modelu zdarzenia: pola, przypisanie, deduplikacja, ważność. | Schemat zdarzenia; reguły ważności w konfiguracji; kolejka „bez projektu”; tożsamość projektu po zdalnym repozytorium, nie po nazwie. |
| 8 | wysoka | 3/3 | Notion jako tablica i własny moduł naraz: dwa źródła prawdy, konflikty, limity API. | Źródło prawdy: system (git). Notion później, tylko jako lustro do odczytu. |
| 9 | wysoka | 3/3 | Brak wymagań niefunkcjonalnych: bezpieczeństwo, sekrety, prywatność danych klientów, kopie i odtwarzanie, koszty. | Nowa sekcja: brak portów w internecie, dostęp przez prywatną sieć, sekrety w menedżerze, klasyfikacja danych, kopia poza PC z testem odtworzenia, budżet. |
| 10 | wysoka | 1/3 (Opus) | Brak uprawnień agentów; treści z poczty i portali mogą przemycić polecenia. | Sekcja „Uprawnienia i zgody”: wysyłka i publikacja tylko po odbiorze; treść z kanałów nigdy nie jest poleceniem. |
| 11 | średnia | 3/3 | ntfy bez konta: kto zgadnie temat, czyta powiadomienia. | Rozstrzyga D1; jeśli ntfy, to token i treść bez danych. |
| 12 | średnia | 3/3 | Turtle raz projekt, raz epik; decyzje P2 nie pasują do stanów; brak przejść między stanami. | Turtle = projekt w stanie „backlog”; jeden słownik stanów; tabela przejść (kto zatwierdza). |
| 13 | średnia | 3/3 | Pełna bramka dla każdego projektu przeczy lekkiej księdze Życia i blokuje małe zlecenia. | Dwa progi księgi: lekka i pełna, z kryterium; istniejące projekty startują z długiem dokumentacji. |
| 14 | średnia | 2/3 | Obszar Życie: źródła nieustalone, dane zdrowotne wrażliwe. | Poza wersją 1; w modelu tylko pole „obszar”; dane zdrowotne lokalnie. |
| 15 | niska | 3/3 | Brak kryterium końca audytu. | Koniec, gdy iteracja nie zgłasza ustaleń krytycznych; najwyżej 2 kolejne iteracje. |

## Przypadki brzegowe dopisane do księgi
PC wyłączony lub po aktualizacji (zewnętrzny sygnał życia, odpowiedź ze znacznikiem świeżości) · cisza powiadomień nieodróżnialna od spokoju ·
wygasłe logowania, jedno powiadomienie zamiast lawiny · agent wisi, zapętla się lub zużywa limit (limit czasu, wycofanie zmian) ·
agent i właściciel zmieniają ten sam plik · zdarzenie pasuje do dwóch projektów albo żadnego · ten sam projekt na Macu i PC ·
phishing udający powiadomienie · zmiana szablonu maila psuje odczyt po cichu · cisza nocna i limit powiadomień ·
utrata telefonu lub laptopa · dane klientów i NDA · pierwszy inwentarz z setkami kandydatów · przegląd kandydatów niezrobiony ·
strefy czasowe · przerwa w nawyku (choroba, urlop) nie jest porażką.

## Pierwszy krok (wspólny wniosek)
Cienki pion na trzech znanych projektach, zanim powstanie cała reszta:
1. Skrypt tylko do odczytu na Macu: projekty z sesji Claude Code i folderów z repozytoriami → plik inwentarza (tożsamość, ostatnia aktywność). Bez modelu, nic nie wysyła.
2. Właściciel kwalifikuje: Backend i TestNow aktywne, Turtle w backlogu.
3. Codziennie rano stan projektów na iPhone kanałem z D1.
Ukończone, gdy przez 5 dni roboczych rano przychodzi poprawny stan i właściciel z niego korzysta.

## Decyzje właściciela

| # | Decyzja | Rekomendacja |
|---|---|---|
| D1 | Kanał na iPhone: tylko powiadomienia (ntfy) czy dwustronny (pytania, zapis pomysłu, odbiór przyciskiem)? | Telegram z własnym botem: darmowy, jeden kanał na powiadomienia, pytania i przyciski odbioru; założenie bota zajmuje kilka minut. |
| D2 | Źródło prawdy | Prywatne repozytorium git z plikami stanu; Notion później jako lustro do odczytu. |
| D3 | Kanały bez API (LinkedIn, Facebook, portale) | Tylko przez e-maile z powiadomieniami, w etapie 2; wymaga podłączenia poczty. |
| D4 | Czy agenci mogą sami wysyłać albo publikować na zewnątrz? | Nigdy bez Twojego odbioru. |
| D5 | Budżet | Miesięczny koszt poza subskrypcjami (np. 0 zł na start) i liczba uruchomień agentów w tle dziennie. |
| D6 | Kolejność | Cienki pion najpierw, inwentarz i kanały dokładane źródło po źródle. |
| D7 | Dane klientów | Czy w projektach są dane, które nie mogą trafić do usług zewnętrznych (Telegram, ntfy, Notion)? |
