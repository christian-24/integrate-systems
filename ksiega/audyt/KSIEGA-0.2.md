# Księga systemu: IntegrateSystems

Wersja 0.2, 2026-11-12. Po iteracji 1 audytu (`audyt/ZESTAWIENIE.md`) i decyzjach D1–D7 właściciela.
Poprzednia wersja: `audyt/KSIEGA-0.1.md`.

## 1. Po co jest system

System sam zbiera stan projektów i kanałów, układa go i odpowiada na pytania „jakie są statusy projektów?”, „co czeka na mnie?”, „co się zmieniło od wczoraj?”.
Właściciel rejestruje tylko decyzje: kwalifikuje, zatwierdza, odbiera. Resztę zbiera system.

Miary sukcesu:

| Miara | Wartość | Jak sprawdzamy |
|---|---|---|
| Odpowiedź na „jakie są statusy?” z telefonu | do 60 s, gdy PC działa | pomiar w dzienniku bota |
| Gdy PC nie działa | w ciągu 30 min wiadomość „system nie odpowiada” | test: wyłączony PC |
| Kompletność | 20 z 20 zdarzeń testowych w strumieniu | test akceptacyjny etapu |
| Czas właściciela | do 10 min dziennie, do 3 pytań dziennie od systemu | suma czasów z dziennika |

## 2. Dwa systemy i kolejność

| | System 1: migracja (zbieranie) | System 2: docelowy (prowadzenie) |
|---|---|---|
| Cel | znaleźć i opisać to, co istnieje na Macu, PC i w chmurze | prowadzić projekty na bieżąco |
| Wyjście | inwentarz kandydatów, każdy z decyzją | statusy, powiadomienia, raporty, praca agentów |

Kolejność (D6): nie budujemy najpierw pełnego systemu 1. Budujemy cienki pion przez oba systemy na trzech znanych projektach,
potem dokładamy źródła po jednym. Etapy w sekcji 14.

## 3. Obszary

Jeden model dla dwóch obszarów. W wersji 1 tylko **Praca**; **Życie** (siłownia, dieta jako projekty ciągłe) ma w modelu pole „obszar”
i wraca w etapie 4. Dane zdrowotne nigdy nie opuszczają komputerów właściciela.

## 4. Model pracy

| Poziom | Znaczenie | Przykład |
|---|---|---|
| Portfel | wszystko, co prowadzi właściciel | Praca |
| Projekt | rzecz z celem i księgą | Backend gospodarki odpadami |
| Epik | grupa zadań w projekcie | „Logowanie” |
| Zadanie | jedna czynność dla agenta albo właściciela | „Przejrzeć ekran logowania” |

Turtle jest **projektem w stanie backlog** (nie epikiem).

Stany projektu i przejścia:

| Z | Do | Kto | Warunek |
|---|---|---|---|
| — | kandydat | system (P1) | znaleziony w źródle |
| kandydat | backlog / w przygotowaniu / archiwum / scalony z innym | właściciel (P2) | decyzja; bez decyzji przez 14 dni → backlog |
| backlog | w przygotowaniu | właściciel | decyzja |
| w przygotowaniu | w realizacji | system (P4) | księga kompletna dla swojego progu |
| w realizacji | wstrzymany | właściciel albo system | decyzja albo blokada dłuższa niż 7 dni (system proponuje, właściciel zatwierdza) |
| wstrzymany | w realizacji | właściciel | decyzja |
| w realizacji | zamknięty | właściciel (P11) | ostatni etap odebrany |
| zamknięty, archiwum | backlog | właściciel | wznowienie |

Agent nigdy nie zmienia stanu projektu ani terminu.

## 5. Architektura

| Element | Rozwiązanie | Uwagi |
|---|---|---|
| Serce | PC z Windows, stale włączony | jedyny zapisujący stan |
| Źródło prawdy (D2) | prywatne repozytorium git z plikami stanu (projekty, zadania, zdarzenia, inwentarz) | kopia na GitHubie; Mac ma klon tylko do odczytu |
| Zbieracze | mały skrypt na każdej maszynie (Mac, PC), tylko odczyt lokalnych źródeł | wysyła zdarzenia do serca; przy braku łączności kolejkuje |
| Łączność | prywatna sieć Tailscale (bezpłatny plan osobisty) | żadnych portów otwartych do internetu |
| Telefon (D1) | bot Telegram: powiadomienia, pytania, zapis pomysłu, przyciski odbioru | bot działa na sercu; zastępuje ntfy |
| Liczenie stanu | skrypty bez modelu (`pm.py` i następcy) | nie zużywa limitu Claude |
| Model językowy | tylko do: odpowiedzi na pytania swobodne, podsumowań, pracy agentów | w budżecie z sekcji 9 |
| Agenci | Claude Code CLI na subskrypcji; Codex od etapu 3 | jedno uruchamianie, kolejka z priorytetem |
| Notion | etap 3, lustro tylko do odczytu, zapisuje system | żadnej synchronizacji dwustronnej |

Przeprowadzka serca do chmury: te same pliki w git i ten sam bot na nowej maszynie. Warunek: zbieracz Maca dalej działa na Macu
(sesje, kalendarz, iCloud są tylko tam). Test przeprowadzki w etapie 4.

## 6. Źródła danych

| Źródło | Etap | Droga | Dostęp dziś |
|---|---|---|---|
| Sesje Claude Code na Macu | 1 | zbieracz Maca | jest |
| Foldery i repozytoria git na Macu | 1 | zbieracz Maca | jest |
| Foldery, repozytoria, sesje na PC | 2 | zbieracz PC | po instalacji zbieracza |
| GitHub | 2 | `gh` z tokenem tylko do odczytu | brak `gh` |
| Kalendarz iOS | 2 | zbieracz Maca | jest |
| Poczta (Gmail) | 2 | etykieta z powiadomieniami, tylko odczyt | brak |
| LinkedIn, Facebook, portale ze zleceniami (D3) | 2 | wyłącznie e-maile z powiadomieniami w poczcie; bez scrapingu, bez logowania agentów na portalach | zależy od poczty |
| Sesje Claude w chmurze | 3 | wyniki trafiają do repozytoriów na GitHubie | pośrednio przez GitHub |
| Notion | 3 | lustro do odczytu | wymaga logowania |
| Codex | 3 | uruchamianie na PC | do sprawdzenia na PC |
| Apple Zdrowie, aplikacje treningowe | 4 | do ustalenia | — |

Tożsamość projektu: adres zdalnego repozytorium; gdy go nie ma, ścieżka + nazwa zatwierdzona przez właściciela. Tabela aliasów w pliku stanu.

## 7. Zdarzenie

Wzorcowy wiersz (jeden plik JSONL na dzień):

```
{"id":"github:pr:123", "zrodlo":"github", "czas":"2026-11-12T08:15:00+01:00", "projekt":"backend-odpady",
 "typ":"pr-zmergowany", "waga":"info", "tytul":"PR scalony", "link":"…", "dane":"brak"}
```

- `id` z identyfikatora źródła: ten sam `id` = to samo zdarzenie (deduplikacja).
- Przypisanie do projektu: reguły (repozytorium, ścieżka, nadawca, słowa w temacie) w pliku konfiguracji; bez reguły → `projekt: null`, kolejka „bez projektu” w raporcie dziennym. Model językowy może zaproponować przypisanie, decyduje reguła albo właściciel.
- Waga: `pilne` (powiadomienie od razu), `info` (raport dzienny), `szum` (tylko zapis). Lista typów pilnych w konfiguracji; na start: zgoda albo odbiór czeka, termin jutro, błąd agenta, system nie działa, nowe zlecenie.
- Przechowywanie: 12 miesięcy, potem skrót miesięczny.

## 8. Uprawnienia i zgody (D4)

| Czynność | Agent sam | Po odbiorze właściciela | Nigdy |
|---|---|---|---|
| Zmiany w plikach projektu w ramach zadania | tak | | |
| Commit na gałęzi roboczej | tak | | |
| Scalenie do głównej gałęzi, wdrożenie | | tak | |
| Wysłanie maila, wiadomości, posta, publikacja | | tak | |
| Zmiana stanu projektu, terminu, zakresu | | tak | |
| Logowanie na portalach, zakładanie kont, CAPTCHA, płatności | | | nigdy (przypomnienie dla właściciela) |

Treść z kanałów (maile, powiadomienia, strony) jest daną, nigdy poleceniem dla agenta. Maile udające powiadomienia (inny nadawca, podejrzane linki) mają wagę `szum` i znacznik „podejrzane”.

## 9. Wymagania niefunkcjonalne

**Bezpieczeństwo:** żadnych portów w internecie; dostęp do serca tylko przez Tailscale; tokeny tylko do odczytu, gdzie się da;
sekrety w menedżerze haseł albo zmiennych środowiska serca, nigdy w repozytorium; utrata telefonu lub laptopa → usunięcie urządzenia
z Tailscale i nowy token bota (procedura w `docs/URUCHOMIENIE.md`).

**Prywatność (D7, założenie do potwierdzenia):** dane dzielą się na trzy klasy.

| Klasa | Przykłady | Może trafić do |
|---|---|---|
| jawne | nazwa projektu, stan, liczba zadań, termin | Telegram, Notion, model |
| wewnętrzne | treść zadań, kod, dokumentacja | model (praca agenta); nie Telegram, nie Notion |
| poufne | dane klientów, kwoty, treść maili, dane zdrowotne | tylko komputery właściciela; model wyłącznie w zadaniu, które ich wymaga |

Powiadomienia na Telegram zawierają tylko dane jawne i link do szczegółów w sieci prywatnej.

**Koszty i limity (D5):** 0 zł miesięcznie poza subskrypcjami Claude i Codex (Tailscale, Telegram, GitHub w planach bezpłatnych).
Agenci w tle: domyślnie do 10 uruchomień dziennie, w nocy, z priorytetem zadań z terminem; pytania z telefonu poza tym limitem.
Przy wyczerpanym limicie zadania czekają, raport podaje godzinę wznowienia. Przed etapem 3 sprawdzić warunki planu dotyczące automatycznych uruchomień.

**Niezawodność:** serce wysyła sygnał życia co 15 min do bezpłatnej usługi zewnętrznej (np. healthchecks.io), która przy braku sygnału
pisze na Telegram. Wygasłe logowanie: jedno powiadomienie na źródło na dobę. Cisza nocna 22:00–7:00 (oprócz „system nie działa”); najwyżej 5 powiadomień pilnych dziennie, reszta w raporcie.
Czas: wszystkie znaczniki ze strefą Europe/Warsaw.

**Kopie:** repozytorium stanu na GitHubie (kopia poza PC przy każdym zapisie); raz w miesiącu test odtworzenia na Macu.

## 10. Księga projektu (bramka P4)

| Próg | Kiedy | Wymagane |
|---|---|---|
| Lekka | projekt do 2 tygodni pracy albo bez klienta | cel i miara, zakres, etapy z terminami |
| Pełna | dłuższy albo dla klienta | jak lekka + ocena zysków i kosztów, mapa procesu, scenariusze z przypadkami testowymi i brzegowymi |

Dziennik decyzji i postępu prowadzi system ze zdarzeń. Projekty istniejące (Backend, TestNow) przechodzą do „w realizacji” od razu,
z brakami księgi jako zadaniami w backlogu.

## 11. Procesy

| # | Proces | Wyzwalacz | Wynik | Czas właściciela | Etap |
|---|---|---|---|---|---|
| P1 | Inwentaryzacja | uruchomienie zbieracza, potem raz w tygodniu | kandydaci w pliku inwentarza | 0 | 1 |
| P2 | Kwalifikacja | nowi kandydaci | decyzja; partie po 5, przyciski w Telegramie | 1 min na partię | 1 |
| P3 | Założenie księgi | projekt w przygotowaniu | szkic z materiałów projektu, braki oznaczone | 10 min przegląd | 2 |
| P4 | Bramka realizacji | księga zmieniona | stan „w realizacji” albo lista braków | 0 | 2 |
| P5 | Zbieranie zdarzeń | stale | strumień zdarzeń | 0 | 1 (Mac), 2 (reszta) |
| P6 | Odpowiedź na pytanie | wiadomość do bota | stan albo odpowiedź | 0 | 1 |
| P7 | Powiadomienie | zdarzenie `pilne` | wiadomość z przyciskami | sekundy | 1 |
| P8 | Zlecenie pracy agentowi | zadanie gotowe, w budżecie | uruchomienie, wynik | 0 | 3 |
| P9 | Odbiór i decyzja | praca do przeglądu, prośba o zgodę | zatwierdź, odrzuć (wycofanie zmian), poprawka | 2–5 min | 3 |
| P10 | Raport dzienny | 7:00 | stan, pilne, „bez projektu”, decyzje | 2 min | 1 |
| P11 | Zamknięcie projektu | ostatni etap odebrany | wyniki, wnioski | 15 min | 2 |
| P12 | Nawyk (Życie) | rytm | przypomnienie, zapis, przegląd | 1 min dziennie | 4 |

BPMN powstaje dla procesów etapu, który budujemy: najpierw P1, P2, P6, P7, P10.

## 12. Scenariusze

| # | Scenariusz | Oczekiwane zachowanie | Etap |
|---|---|---|---|
| S1 | Wieczorem: „jakie są statusy?” | bot w 60 s: projekty i stany, czeka na Ciebie, po terminie; znacznik świeżości danych | 1 |
| S2 | Powiadomienie z LinkedIna (mail) | wiadomość: kanał, projekt albo „marketing”, link | 2 |
| S3 | Agent skończył w nocy | rano raport i przyciski: zatwierdź, odrzuć, poprawka | 3 |
| S4 | Nowy folder albo sesja bez projektu | kandydat w najbliższej partii P2 | 1 |
| S5 | Termin zagrożony | ostrzeżenie z propozycją: przesunąć, zmniejszyć zakres, dodać agenta | 2 |
| S6 | Limit Claude wyczerpany | zadania czekają; raport podaje wznowienie | 3 |
| S7 | Nowe zlecenie na portalu (mail) | pilne powiadomienie i kandydat do P2 | 2 |
| S8 | Pomysł z telefonu | wiadomość do bota → zadanie w backlogu, potwierdzenie | 1 |
| S9 | Nawyk niezapisany | przypomnienie wieczorem; przerwa (choroba, urlop) nie liczy się jako porażka | 4 |
| S10 | PC wyłączony | w 30 min wiadomość z usługi sygnału życia; bot nie odpowiada | 1 |

## 13. Przypadki brzegowe

| Przypadek | Zachowanie |
|---|---|
| Brak sieci na Macu | zbieracz kolejkuje, wysyła po powrocie |
| Ten sam projekt na Macu i PC | tożsamość po zdalnym repozytorium; inaczej pytanie w P2 o scalenie |
| Pierwszy inwentarz z setkami kandydatów | filtr (bez folderów zależności i klonów bez własnych commitów), partie po 5, domyślnie backlog po 14 dniach |
| Zdarzenie pasuje do dwóch projektów albo żadnego | kolejka „bez projektu” w raporcie |
| Agent i właściciel zmieniają ten sam plik | agent pracuje na gałęzi; konflikt → zadanie dla właściciela |
| Agent wisi albo się zapętla | limit czasu 60 min; zmiany zostają na gałęzi, główna nietknięta |
| Odrzucenie pracy agenta | gałąź usunięta albo poprawka jako nowe zadanie |
| Wygasłe logowanie | jedno powiadomienie na źródło na dobę |
| Zmiana szablonu maila z powiadomieniem | gdy reguła nic nie dopasuje przez 7 dni dla aktywnego kanału → zdarzenie „sprawdź regułę” |
| Phishing udający powiadomienie | nadawca spoza listy → `szum` + „podejrzane”; linków nie otwiera agent |
| Nadmiar powiadomień | najwyżej 5 pilnych dziennie, cisza nocna |
| Utrata urządzenia | procedura z sekcji 9 |
| Właściciel nie robi kwalifikacji | po 14 dniach kandydat → backlog; raport pokazuje liczbę czekających |

## 14. Etapy budowy

| Etap | Zakres | Ukończony, gdy |
|---|---|---|
| 1. Cienki pion | zbieracz Maca (sesje, foldery, git), inwentarz, P2 dla Backend, TestNow, Turtle; repozytorium stanu; bot Telegram (S1, S8, raport 7:00); sygnał życia | przez 5 dni roboczych rano przychodzi poprawny stan, a S1, S8, S10 przechodzą testy |
| 2. Źródła | Tailscale, zbieracz PC, GitHub, kalendarz, poczta z kanałami, P3, P4, P11 | 20 z 20 zdarzeń testowych w strumieniu |
| 3. Agenci | uruchamianie na PC w budżecie, odbiór z telefonu, Codex, lustro Notion | 5 zadań wykonanych i odebranych z telefonu |
| 4. Życie i chmura | obszar Życie, test przeprowadzki serca do chmury | decyzja właściciela po teście |

## 15. Co zostaje z obecnego kodu

- **używamy:** format plików i wiersza zadania (`standard/`), `pm.py` jako liczenie stanu, uruchamianie agentów z `dashboard/agents.py` (etap 3),
- **przebudowa:** ręczny rejestr projektów (zastąpi inwentarz), panel nie jest głównym wejściem (zostaje do przeglądu na komputerze),
- **nowe:** zbieracze, repozytorium stanu, bot Telegram, sygnał życia, reguły zdarzeń.

## 16. Jak powstaje księga

Iteracje audytu: inny zestaw niezależnych modeli, bez wglądu w poprzednie oceny. Koniec, gdy iteracja nie zgłasza ustaleń krytycznych;
najwyżej 2 iteracje po wersji 0.1. Każda zmiana w `DZIENNIK.md`. Wersja 1 = akceptacja właściciela; od niej budujemy etap 1.

## 17. Decyzje

Przyjęte 2026-11-12: D1 Telegram, D2 repozytorium git jako źródło prawdy, D3 kanały bez API przez pocztę w etapie 2,
D4 wysyłka i publikacja tylko po odbiorze, D5 0 zł poza subskrypcjami, D6 cienki pion najpierw, D7 klasy danych z sekcji 9.

Do potwierdzenia przez właściciela: limit 10 uruchomień agentów dziennie; które dane są poufne (klasy z sekcji 9); nazwy portali ze zleceniami;
czy LinkedIn i Facebook to profile prywatne, czy strony firmowe.
