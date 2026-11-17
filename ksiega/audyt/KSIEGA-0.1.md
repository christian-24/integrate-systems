# Księga systemu: IntegrateSystems

Wersja 0.1, 2026-11-12. Szkic po pierwszych odpowiedziach właściciela, przed audytem.
Ta księga jest wzorem: każdy projekt ma mieć taką samą, inaczej nie jest realizowany.

## 1. Po co jest system

Jedno miejsce, które samo zbiera stan projektów, kanałów i spraw osobistych, układa go i odpowiada na pytania:
„jakie są statusy projektów?”, „co czeka na mnie?”, „co się zmieniło od wczoraj?”.
Właściciel niczego nie rejestruje ręcznie. Decyduje, zatwierdza i odbiera pracę.

Miary sukcesu (do potwierdzenia):
- pytanie o stan dowolnego projektu dostaje odpowiedź w mniej niż minutę, z telefonu albo komputera,
- nic ważnego nie ginie: każde zdarzenie z kanałów trafia do jednego strumienia,
- właściciel poświęca na obsługę systemu mniej niż 10 minut dziennie.

## 2. Dwa systemy

| | System 1: migracja (zbieranie) | System 2: docelowy (prowadzenie) |
|---|---|---|
| Cel | znaleźć i opisać wszystko, co już istnieje, na Macu, PC i w chmurze | prowadzić projekty na bieżąco |
| Wejście | foldery, sesje Claude Code i Codex, repozytoria, kalendarz, poczta, kanały | strumień zdarzeń z tych samych źródeł |
| Wyjście | inwentarz: projekty, stany, zadania; każdy z decyzją: aktywny, backlog, archiwum | statusy, powiadomienia, raporty, praca agentów |
| Kiedy | najpierw, potem okresowo dla nowych rzeczy | stale |
| Właściciel | zatwierdza, co jest projektem, a co śmieciem | decyduje, zatwierdza, odbiera |

Kolejność: najpierw system 1, bo bez inwentarza system 2 jest pusty.

## 3. Obszary

System ma dwa obszary na tym samym modelu (portfel → projekt → epik → zadanie). Budujemy najpierw Pracę; Życie projektujemy teraz, budujemy później.

| | Praca | Życie |
|---|---|---|
| Przykłady | Backend gospodarki odpadami, TestNow, Turtle (backlog), marketing, zlecenia | siłownia, dieta, jedzenie |
| Rodzaj projektu | z końcem: etapy, terminy, odbiór | ciągły: nawyk, cel liczbowy, rytm (np. 3 treningi w tygodniu) |
| Kto wykonuje | agenci i właściciel | właściciel; system przypomina i liczy |
| Miara | etap odebrany, zysk | regularność, wynik (waga, ciężar, posiłki) |
| Księga | pełna (sekcja 7) | lekka: cel, miara, rytm, przegląd co miesiąc |

## 4. Model pracy (moduł zadań w stylu Jiry)

| Poziom | Znaczenie | Przykład |
|---|---|---|
| Portfel | wszystko, co prowadzi właściciel | Praca, Życie |
| Projekt | jedna rzecz z celem i księgą | Backend gospodarki odpadami |
| Epik | duży kawałek pracy w projekcie albo zawieszony pomysł | Turtle |
| Zadanie | jedna czynność dla agenta albo właściciela | „Przejrzeć ekran logowania” |

Stany projektu: **kandydat** (znaleziony przez system 1) → **backlog** (zapisany, nie realizowany) → **w przygotowaniu** (księga niepełna) → **w realizacji** → **wstrzymany** → **zamknięty**.
Turtle: epik w backlogu, bez realizacji, ze zgromadzonymi materiałami w jednym miejscu.
Backlog właściciela: zadania `kto: ty` ze wszystkich projektów w jednym widoku.

## 5. Źródła danych

Stan na 2026-11-12, sprawdzony z Maca.

| Źródło | Rola | Dostęp teraz |
|---|---|---|
| Sesje Claude Code na Macu | inwentarz, postęp | **jest**: 3 projekty (Turtle, TestNow, Backend) |
| Sesje Claude Code w chmurze | postęp pracy agentów | do sprawdzenia |
| PC z Windows | projekty, agenci 24/7 | brak połączenia z Makiem |
| Foldery na Macu, iCloud | pliki, dokumenty | **jest** |
| Kalendarz iOS | terminy | **jest** (panel czyta lokalnie) |
| GitHub | kod, PR, CI | brak (`gh` niezainstalowany) |
| Notion | planowane wdrożenie | wymaga zalogowania przez `/mcp` |
| LinkedIn, Facebook | marketing | brak; zależy, czy profil prywatny, czy strona firmowa |
| Portale ze zleceniami | nowe zlecenia | brak; nazwy portali do ustalenia |
| Poczta | powiadomienia z kanałów bez API | brak (łącznik Gmail nieskonfigurowany) |
| Codex | praca agentów | brak na Macu; do sprawdzenia na PC |

## 6. Gdzie działa system

| Okres | Serce systemu | Uwagi |
|---|---|---|
| Teraz | PC z Windows, stale włączony | Mac i iPhone łączą się z PC |
| Docelowo | chmura w 100% albo PC + chmura | decyzja po audycie: koszt, niezawodność, dostęp do plików na PC |

Wymaganie: model danych i procesy nie mogą zależeć od tego, gdzie działa serce, żeby przeprowadzka nie wymagała przebudowy.

**Powiadomienia:** ntfy. Bezpłatna aplikacja na iPhone, jedna nazwa kanału do wpisania, bez konta. Wiadomości ważne od razu, reszta w raporcie dziennym.

## 7. Księga projektu (bramka realizacji)

Projekt nie przechodzi do stanu „w realizacji”, dopóki księga nie ma:
1. celu i miary sukcesu,
2. oceny zysków i kosztów (czas, pieniądze, ryzyko),
3. zakresu i tego, co poza zakresem,
4. etapów z terminami i definicją ukończenia,
5. mapy procesu i scenariuszy z przypadkami testowymi i brzegowymi,
6. dziennika decyzji i postępu (prowadzonego przez system, nie ręcznie).

## 8. Procesy główne

Każdy proces dostanie diagram BPMN po audycie.

| # | Proces | Wyzwalacz | Wynik |
|---|---|---|---|
| P1 | Inwentaryzacja (system 1) | pierwsze uruchomienie, potem raz w tygodniu | kandydaci z Maca, PC i chmury, do decyzji |
| P2 | Kwalifikacja | właściciel przegląda kandydata | aktywny, backlog, archiwum albo dołącz do istniejącego |
| P3 | Założenie księgi | projekt aktywny | szkic księgi z materiałów projektu; braki oznaczone |
| P4 | Bramka realizacji | księga gotowa | „w realizacji” albo „w przygotowaniu: brak X” |
| P5 | Zbieranie zdarzeń | sesja, commit, termin, mail, powiadomienie z kanału | jeden strumień zdarzeń przypisanych do projektów |
| P6 | Odpowiedź na pytanie o stan | pytanie właściciela | zrobione, w toku, czeka na Ciebie, ryzyka |
| P7 | Powiadomienie | zdarzenie ważne według reguł | wiadomość na iPhone; reszta w raporcie |
| P8 | Zlecenie pracy agentowi | zadanie gotowe | uruchomienie, wynik, praca do odbioru |
| P9 | Odbiór i decyzja | praca do przeglądu albo prośba o zgodę | zatwierdzone, odrzucone, poprawka |
| P10 | Raport dzienny | rano | notatka PM |
| P11 | Zamknięcie projektu | ostatni etap odebrany | wyniki, wnioski, porównanie z zakładanymi zyskami |
| P12 | Nawyk (obszar Życie) | rytm, np. dzień treningowy | przypomnienie, zapis wyniku, przegląd miesięczny |

## 9. Scenariusze właściciela

| # | Scenariusz | Oczekiwane zachowanie |
|---|---|---|
| S1 | Wieczorem w domu: „jakie są statusy projektów?” | lista: zrobione, w toku, czeka na Ciebie, po terminie |
| S2 | W tramwaju: powiadomienie z LinkedIna | krótka wiadomość na iPhone z przypisanym projektem albo „marketing”; szczegóły po dotknięciu |
| S3 | Agent skończył zadanie w nocy na PC | rano raport: co zrobione, co do odbioru; odbiór jednym przyciskiem |
| S4 | Nowy folder albo sesja Claude bez projektu | pytanie: nowy projekt, dołączyć do istniejącego, backlog czy pominąć |
| S5 | Termin zagrożony | ostrzeżenie z propozycją: przesunąć, zmniejszyć zakres, dodać agenta |
| S6 | Limit Claude wyczerpany | zadania czekają; informacja, kiedy ruszą |
| S7 | Nowe zlecenie na portalu | powiadomienie i kandydat na projekt do kwalifikacji |
| S8 | Pomysł z głowy, np. „wrócić do Turtle” | zapis do backlogu jednym zdaniem z telefonu |
| S9 | Dzień treningowy bez zapisu treningu | przypomnienie wieczorem; w przeglądzie miesięcznym regularność |

Przypadki brzegowe do rozpisania w audycie: brak sieci, wygasłe logowanie, PC wyłączony, dwa komputery zmieniają ten sam plik,
zdarzenie bez projektu, duplikaty powiadomień, dane prywatne w kanałach, ten sam projekt na Macu i PC pod różnymi nazwami.

## 10. Co zostaje z obecnego kodu

Decyzja po audycie. Wstępnie:
- **do użycia:** format wiersza zadania i plików (`standard/`), uruchamianie agentów na subskrypcji (`dashboard/agents.py`), dostęp z hasłem,
- **do przebudowy:** ręczny rejestr projektów (zastąpi go P1), panel jako jedyne wejście (najpierw rozmowa i powiadomienia), brak poziomów portfel i epik,
- **brakuje:** inwentaryzacji, strumienia zdarzeń, ntfy, połączenia Mac–PC, Notion, kanałów marketingowych, obszaru Życie.

## 11. Jak powstaje ta księga

| Krok | Kto | Wynik |
|---|---|---|
| 1. Szkic | Claude | ten plik |
| 2. Przegląd | właściciel | odpowiedzi na pytania (sekcja 12) |
| 3. Audyt, 3–4 iteracje | niezależne modele, inny w każdej iteracji, bez wglądu w poprzednie oceny | luki, sprzeczności, ryzyka |
| 4. Mapa BPMN | Claude | diagramy P1–P12 w `ksiega/procesy/` (.bpmn i podgląd) |
| 5. Scenariusze i testy | Claude + audyt | przypadki testowe dla scenariuszy i brzegów |
| 6. Akceptacja | właściciel | wersja 1, od niej budujemy |

Każda iteracja zapisuje się w `ksiega/DZIENNIK.md`.

## 12. Pytania do właściciela

Odpowiedziane 2026-11-12: kanały, położenie projektów, miejsce działania, powiadomienia, Turtle, obszar Życie.

Otwarte (audyt może ruszyć bez nich, oznaczy je jako założenia):
1. **Notion:** ma być tablicą, którą oglądasz (projekty, backlog, Życie na iPhonie bez budowania aplikacji), a system tylko do niej pisze? Czy własny moduł, a Notion jako dodatek? Rekomendacja: Notion jako tablica, system jako silnik.
2. **LinkedIn i Facebook:** profile prywatne czy strony firmowe? Strony mają oficjalny dostęp; profile prywatne tylko przez powiadomienia e-mail.
3. **Portale ze zleceniami:** które?
4. **„Połączone z chmurą” na PC:** chodzi o GitHub, OneDrive, sesje Claude w chmurze, czy wszystkie?
5. **Życie:** skąd dane? Apple Zdrowie, aplikacja treningowa, aplikacja do diety, ręczny zapis?
