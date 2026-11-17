# Księga systemu: IntegrateSystems

Wersja 1, 2026-11-12. Zaakceptowana przez właściciela; podstawa budowy etapu 1.
Historia: `audyt/KSIEGA-0.1.md`, `audyt/KSIEGA-0.2.md`, `audyt/KSIEGA-0.3.md`, audyty w `audyt/`, zmiany w `DZIENNIK.md`.

## 1. Po co jest system

System sam zbiera stan projektów i kanałów, układa go i odpowiada na pytania „jakie są statusy projektów?”, „co czeka na mnie?”, „co się zmieniło od wczoraj?”.
Właściciel rejestruje tylko decyzje: kwalifikuje, zatwierdza, odbiera. Resztę zbiera system.

| Miara | Wartość | Jak sprawdzamy |
|---|---|---|
| Odpowiedź na „jakie są statusy?” z telefonu | do 60 s, gdy PC działa | czas w dzienniku bota (wiadomość przyszła → odpowiedź wysłana) |
| Gdy PC albo bot nie działa | w ciągu 30 min wiadomość „system nie odpowiada” | test S10 |
| Kompletność | 20 z 20 zdarzeń z pliku testowego w strumieniu | `testy/zdarzenia-20.jsonl`, etap 2 |
| Czas właściciela | do 3 pytań dziennie od systemu; do 10 min dziennie | liczba pytań i czas od powiadomienia do kliknięcia w dzienniku bota |

## 2. Dwa systemy i kolejność

System 1 (migracja) znajduje i opisuje to, co istnieje; system 2 (docelowy) prowadzi projekty na bieżąco.
Nie budujemy najpierw pełnego systemu 1. Budujemy cienki pion przez oba systemy na trzech znanych projektach, potem dokładamy źródła po jednym (sekcja 14).

## 3. Obszary

Jeden model dla dwóch obszarów. W wersji 1 tylko **Praca**. **Życie** (siłownia, dieta jako projekty ciągłe) ma w modelu pole „obszar” i wraca w etapie 4 (załącznik A).

## 4. Model pracy

| Poziom | Znaczenie | Gdzie zapisane |
|---|---|---|
| Portfel | wszystko, co prowadzi właściciel | repozytorium stanu |
| Projekt | rzecz z celem i księgą; stan projektu | repozytorium stanu (`projekty.json`) |
| Epik | grupa zadań w projekcie | `ZADANIA.md` w projekcie (sekcja etapu) |
| Zadanie | jedna czynność dla agenta albo właściciela | `ZADANIA.md` w projekcie, format z `standard/STANDARD.md` |

Zadania żyją w repozytoriach projektów, nie w repozytorium stanu. Pomysły z telefonu (S8) trafiają do `pomysly.md` w repozytorium stanu
i właściciel przenosi je do projektu przy kwalifikacji.

Turtle jest **projektem w stanie backlog**.

| Z | Do | Kto | Warunek |
|---|---|---|---|
| — | kandydat | system (P1) | znaleziony w źródle, a jego tożsamości nie ma jeszcze w `projekty.json` (każdy stan, w tym archiwum i wykluczony, blokuje ponowne zgłoszenie) |
| kandydat | w realizacji / backlog / w przygotowaniu / archiwum / scalony / wykluczony | właściciel (P2) | decyzja wraz z polem `klient` i aliasem; „w realizacji” tylko dla projektów istniejących; „scalony” pokazuje listę projektów do wyboru |
| kandydat | archiwum | system | brak decyzji przez 14 dni |
| backlog | w przygotowaniu | właściciel | decyzja |
| w przygotowaniu | w realizacji | system (P4) | księga kompletna dla swojego progu |
| w realizacji | wstrzymany | właściciel | decyzja; system proponuje przy blokadzie dłuższej niż 7 dni |
| wstrzymany | w realizacji | właściciel | decyzja |
| w realizacji | zamknięty | właściciel (P11) | ostatni etap odebrany |
| zamknięty, archiwum | backlog | właściciel | wznowienie |

„Wykluczony” trafia na trwałą listę wykluczeń i nie wraca w kolejnych inwentaryzacjach.
Przejścia wykonywane przez system są tylko te z tabeli; o każdym system informuje w raporcie dziennym.

## 5. Architektura

| Element | Rozwiązanie |
|---|---|
| Serce (D13) | serwer Linux w chmurze (Hetzner), stale włączony: panel jako API z logowaniem przez HTTPS (Mac, iPhone), agenci, repozytoria pobierane z GitHuba, pilnowanie Useme przez e-maile, raport 7:00, nocna kopia zapasowa. PC z Windows sprzedany po migracji |
| Podział pracy (D13) | `gdzie: serwer` (domyślnie), `gdzie: mac` (Chrome z rozszerzeniami, grupy Facebooka, iOS, emulator Androida, TestNow), `gdzie: windows` (build i testy w GitHub Actions; debugowanie na maszynie Windows w Azure włączanej na godziny). Wymiana przez GitHub. Plan: `ksiega/MIGRACJA.md` |
| Źródło prawdy (D2) | prywatne repozytorium git „stan”, kopia na GitHubie |
| Zapisujący (D8) | jeden zapisujący na gałąź: Mac wypycha tylko gałąź `mac` (wyłącznie katalog `mac/`); PC jedyny pisze gałąź główną i scala do niej `mac/` z gałęzi `mac`. Dwa push nigdy nie trafiają w tę samą gałąź |
| Droga Mac → PC w etapie 1 (D8) | Mac wypycha gałąź `mac` na GitHub, PC pobiera ją co 5 min. Tailscale w etapie 2 |
| Zbieracz Maca | skrypt, który źródła tylko czyta, a zapisuje wyłącznie do `mac/`; launchd przy zalogowaniu i co godzinę (w czasie snu Maca nie działa); potrzebuje pełnego dostępu do dysku w ustawieniach macOS (nadaje właściciel); kolejka do 10 000 zdarzeń |
| Zbieracz PC | etap 2 |
| Telefon (D1) | bot Telegram, long polling (bez otwartych portów), odpowiada tylko na jeden `chat_id` właściciela |
| Liczenie stanu | skrypty bez modelu (`pm.py` i następcy) |
| Model językowy | **etap 1 bez modelu.** Od etapu 3: pytania swobodne, podsumowania, praca agentów, w budżecie z sekcji 9 |
| Notion, Codex | załącznik A |

Zapis plików atomowy (plik tymczasowy, potem zamiana). Jeden proces na PC zapisuje stan; bot przekazuje mu zapisy kolejką.
Przeprowadzka serca do chmury: te same pliki i ten sam bot na nowej maszynie; zbieracz Maca zostaje na Macu (sesje, kalendarz, iCloud są tylko tam).

## 6. Źródła danych

| Źródło | Etap | Droga |
|---|---|---|
| Sesje Claude Code na Macu | 1 | zbieracz Maca: tylko metadane (folder, data ostatniej aktywności, liczba sesji); treści nie czyta |
| Foldery i repozytoria git na Macu | 1 | zbieracz Maca: nazwa, ścieżka, zdalne repozytorium, data ostatniego commitu, liczba commitów |
| `ZADANIA.md` projektów na Macu | 1 | `pm.py` na Macu, wynik (liczby i stany) do `mac/` |
| Foldery, repozytoria, sesje na PC | 2 | zbieracz PC |
| GitHub | 2 | `gh` z tokenem tylko do odczytu |
| Kalendarz iOS | 2 | zbieracz Maca: data i godzina; tytuł tylko na Macu |
| Poczta | 2 | IMAP z hasłem aplikacji albo przekierowanie etykiety (OAuth w trybie testowym traci token po 7 dniach) |
| LinkedIn, Facebook, portale (D3) | 2 | wyłącznie e-maile z powiadomieniami; bez scrapingu i logowania agentów |
| Sesje Claude w chmurze | 3 | pośrednio: wyniki w repozytoriach na GitHubie |

Format sesji Claude Code jest nieudokumentowany: gdy zbieracz nie rozumie pliku, zapisuje zdarzenie „nie rozumiem pliku” zamiast milczeć.
Tożsamość projektu: zdalne repozytorium; bez niego ścieżka + nazwa zatwierdzona przez właściciela; zmiana ścieżki → pytanie w P2 o scalenie. Aliasy w `projekty.json`.

## 7. Zdarzenie

```
{"id":"github:owner/repo:pr:123", "zrodlo":"github", "czas":"2026-11-12T08:15:00+01:00", "projekt":"backend-odpady",
 "typ":"pr-zmergowany", "waga":"info", "tytul":"PR scalony", "link":"…"}
```

| Typ źródła | `id` |
|---|---|
| GitHub | `github:<owner/repo>:<rodzaj>:<numer>:<stan>` (otwarcie i scalenie PR to dwa zdarzenia) |
| folder / repozytorium lokalne | `<maszyna>:repo:<ścieżka>:<hash ostatniego commitu>` |
| sesja Claude Code | `<maszyna>:sesja:<folder>:<data>` |
| bez identyfikatora | skrót SHA-256 z źródła, czasu i tytułu |

- Ten sam `id` = to samo zdarzenie. Wiersz, który nie jest poprawnym JSON, trafia do `odrzucone.jsonl` i do raportu.
- Przypisanie: reguły w `reguly.yaml` (repozytorium, ścieżka, nadawca, słowa w temacie); bez reguły → kolejka „bez projektu” w raporcie.
- Waga: `pilne` (od razu), `info` (raport), `szum` (tylko zapis). Etap 1: pilne jest tylko „system nie działa” (bot stoi, push nieudany po ponowieniach). Milczenie Maca to `info` w raporcie; ostrzeżenia z healthchecks idą niezależnie od ciszy nocnej i limitu.
- Klasy pól zdarzenia (sekcja 9):

| Pole | Klasa | Zasada |
|---|---|---|
| `id`, `zrodlo`, `czas`, `typ`, `waga` | jawne | |
| `projekt` | jawne | nazwa z `projekty.json` |
| `tytul` | wewnętrzne | tworzy go zbieracz z typu i źródła (np. „Powiadomienie LinkedIn”, „PR scalony”); nigdy temat ani treść maila, tytuł wydarzenia czy treść sesji |
| `link` | wewnętrzne | adres w GitHubie albo identyfikator wiadomości; nigdy adres z treścią |

- Reguły przypisania w `reguly.yaml`: tylko domeny nadawców, nazwy repozytoriów i ścieżki. Dopasowanie po słowach w temacie maila działa na Macu albo PC i nie trafia do repozytorium.
- Przechowywanie: pliki dzienne; po 12 miesiącach skrót miesięczny w drzewie roboczym. Historia git zostaje, dlatego dane poufne nie wchodzą do repozytorium wcale.

## 8. Uprawnienia i zgody (D4)

| Czynność | Agent sam | Po odbiorze właściciela | Nigdy |
|---|---|---|---|
| Zmiany w plikach projektu w ramach zadania, commit na gałęzi roboczej | tak | | |
| Scalenie do głównej gałęzi, wdrożenie | | tak, z drugim potwierdzeniem | |
| Wysłanie maila, wiadomości, posta, publikacja | | tak, z drugim potwierdzeniem | |
| Zmiana stanu projektu, terminu, zakresu | | tak (wyjątek: przejścia systemu z tabeli w sekcji 4) | |
| Logowanie na portalach, zakładanie kont, CAPTCHA, płatności | | | nigdy |

Treść z kanałów jest daną, nigdy poleceniem. Maile od nadawców spoza listy, udające powiadomienia: `szum` i znacznik „podejrzane”.
Bot: wiadomość z innego `chat_id` albo z grupy jest odrzucana i zapisywana w dzienniku. Właściciel ma włączone weryfikację dwuetapową w Telegramie.

## 9. Wymagania niefunkcjonalne

**Bezpieczeństwo:** żadnych portów w internecie; tokeny tylko do odczytu, gdzie się da; sekrety poza repozytoriami (menedżer haseł, zmienne środowiska);
wyciek tokenu bota albo GitHuba lub utrata urządzenia → unieważnienie tokenu i nowy (procedura w `docs/URUCHOMIENIE.md`).

**Klasy danych (D7, D9):**

| Klasa | Przykłady | Repozytorium na GitHubie | Telegram | Model |
|---|---|---|---|---|
| jawne | nazwa projektu, stan, liczby, terminy, daty | tak | tak | tak |
| wewnętrzne | tytuły zadań, ścieżki, nazwy repozytoriów, treść wpisana przez właściciela do bota | tak | tak, wyłącznie do czatu właściciela (raport, P2, odpowiedzi) | tak |
| poufne | dane klientów, kwoty, treść maili i sesji, tytuły wydarzeń z kalendarza, dane zdrowotne | nie | nie | tylko w zadaniu, które ich wymaga |

**Projekty klienckie (D10):** projekty są prowadzone dla klientów. Każdy projekt w `projekty.json` ma pole `klient: tak|nie`. Dla projektu klienckiego:
- poza komputerami właściciela występuje tylko **alias** (np. „Backend-A”) nadany w P2; prawdziwa nazwa, nazwa repozytorium i ścieżka zostają w pliku `lokalne/aliasy.json` na Macu i PC, poza repozytorium (w `.gitignore`),
- do repozytorium na GitHubie i do Telegrama trafiają tylko dane jawne: alias, stan, liczby zadań, terminy, świeżość; tytuły zadań i ścieżki zostają lokalnie,
- pełny widok z nazwami i tytułami zadań: panel na komputerze (od etapu 2 także z iPhone'a przez Tailscale),
- zbieracz domyślnie traktuje nowego kandydata jak klienckiego, dopóki właściciel w P2 nie zdecyduje inaczej.

**Koszty i limity (D5):** 0 zł miesięcznie poza subskrypcjami Claude i Codex. Etap 1 nie używa modelu.
Przed etapem 3 właściciel sprawdza na stronie rozliczeń konta Claude, jak liczone są uruchomienia nieinteraktywne (`claude -p`);
budżet agentów ustalamy wtedy w kredycie albo w liczbie uruchomień.

**Niezawodność:**
- Sygnał życia do healthchecks.io (plan bezpłatny, powiadomienie przez Telegram i e-mail jako kanał zapasowy): z pętli bota po udanym cyklu (pobranie, scalenie, push) co 5 min, tolerancja 10 min. Osobne kontrole: zbieracz Maca (tolerancja 26 h), raport 7:00.
- PC: bot i scalanie startują jako zadanie Harmonogramu zadań bez logowania użytkownika; usypianie wyłączone; restart po aktualizacji i zaniku zasilania → start samoczynny.
- Nieudany push: 3 ponowienia, potem zdarzenie pilne.
- Telegram kasuje nieodebrane wiadomości po 24 h: po przestoju dłuższym niż 24 h bot pisze „wiadomości z czasu przerwy mogły zginąć”.
- Raport 7:00 Europe/Warsaw, raz dziennie także przy zmianie czasu; dzień raportu zapisany, żeby nie wyszedł dwa razy.
- Cisza nocna 22:00–7:00 i najwyżej 5 pilnych dziennie; „system nie działa” poza limitem i ciszą.

**Kopie:** GitHub przy każdym udanym push; raz w miesiącu test odtworzenia serca z GitHuba na Macu.

## 10. Księga projektu (bramka P4)

| Próg | Kiedy | Wymagane |
|---|---|---|
| Lekka | do 2 tygodni pracy albo bez klienta | cel i miara, zakres, etapy z terminami |
| Pełna | dłuższy albo dla klienta | jak lekka + zyski i koszty, mapa procesu, scenariusze z testami i przypadkami brzegowymi |

Projekty istniejące (Backend, TestNow) właściciel kwalifikuje w P2 od razu jako „w realizacji”; braki księgi stają się zadaniami.

## 11. Procesy

| # | Proces | Wyzwalacz | Wynik | Czas właściciela | Etap |
|---|---|---|---|---|---|
| P1 | Inwentaryzacja | launchd na Macu | kandydaci w `mac/inwentarz.json` | 0 | 1 |
| P2 | Kwalifikacja | nowi kandydaci | etap 1: polecenie `kwalifikuj` na Macu (tylko tam są prawdziwe nazwy); od etapu 2: przyciski w Telegramie z nazwami pokazywanymi przez sieć prywatną, partie po 5 | 1 min na partię | 1 |
| P5 | Zbieranie zdarzeń | zbieracze | strumień zdarzeń | 0 | 1 (Mac), 2 |
| P6 | Odpowiedź na pytanie | polecenie do bota (`/stan`, `/pomysl`) | stan albo potwierdzenie zapisu | 0 | 1 |
| P7 | Powiadomienie | zdarzenie pilne | wiadomość | sekundy | 1 („system nie działa”) |
| P10 | Raport dzienny | 7:00 | stan, świeżość źródeł, „bez projektu”, przejścia systemu | 2 min | 1 |
| P3, P4, P11 | Księga, bramka, zamknięcie | — | — | — | 2 |
| P8, P9 | Zlecenie agentowi, odbiór | — | — | — | 3 |

Etap 1 opisujemy tabelami kroków; BPMN tylko dla procesów, w których bierze udział więcej niż dwóch uczestników (od etapu 2).

## 12. Scenariusze etapu 1

| # | Scenariusz | Oczekiwane zachowanie | Test |
|---|---|---|---|
| S1 | Wieczorem `/stan` | w 60 s: 3 projekty (klienckie pod aliasem), stan, liczba zadań otwartych, czeka na Ciebie, po terminie; „dane z Maca z HH:MM” | liczby zgodne z ręcznym odczytem `ZADANIA.md` 3 projektów; w wiadomości i w repozytorium na GitHubie nie ma prawdziwych nazw ani tytułów zadań projektów klienckich |
| S4 | Nowy folder z repozytorium na Macu | kandydat w `mac/inwentarz.json`; do P2 trafia w etapie 2 | nowy folder testowy jest w inwentarzu w ciągu 2 h pracy Maca |
| S8 | `/pomysl Wrócić do Turtle` | wpis w `pomysly.md`, potwierdzenie z przyciskiem „cofnij” | wpis jest w repozytorium; „cofnij” go usuwa |
| S10 | Bot zatrzymany przy działającym PC; PC wyłączony; push nieudany; Mac milczy 26 h | w 30 min wiadomość z healthchecks (Telegram i e-mail); dla Maca po 26 h | cztery przypadki sprawdzone |
| S11 | Wiadomość do bota z obcego konta | brak odpowiedzi, wpis w dzienniku | sprawdzone drugim kontem |
| S12 | Restart PC; przestój dłuższy niż 24 h | bot wraca bez logowania, sygnał wznowiony; po przestoju komunikat o możliwej utracie wiadomości i jeden zaległy raport | oba przypadki sprawdzone |

Scenariusze etapów 2–4 (LinkedIn, zlecenia, odbiór pracy agenta, nawyki): załącznik A.

## 13. Przypadki brzegowe

| Przypadek | Zachowanie |
|---|---|
| Mac śpi lub w podróży | raport pokazuje godzinę ostatnich danych z Maca; po 26 h kontrola zbieracza wysyła ostrzeżenie |
| Brak sieci na Macu | zbieracz kolejkuje (do 10 000 zdarzeń), wypycha po powrocie |
| Brak uprawnień macOS dla zbieracza | zbieracz zapisuje zdarzenie „brak dostępu” zamiast pustego wyniku |
| Pierwszy inwentarz z setkami kandydatów | filtr (bez folderów zależności i klonów bez własnych commitów); w etapie 1 kwalifikujemy tylko 3 znane projekty, reszta czeka na etap 2 |
| Kandydat odrzucony | stan „wykluczony”; nie wraca |
| Zmiana nazwy lub ścieżki projektu | pytanie w P2 o scalenie |
| Zepsuty wiersz zdarzenia | `odrzucone.jsonl` i wpis w raporcie |
| PC wraca po przestoju > 24 h | komunikat o możliwej utracie wiadomości; zaległy raport tylko jeden |
| Nieudany push | 3 ponowienia, potem pilne |
| Dwa procesy na PC | jeden zapisujący, kolejka |
| Zmiana czasu | raport raz dziennie według daty lokalnej |
| Awaria Telegrama lub healthchecks | e-mail z healthchecks jako kanał zapasowy |
| Utrata dysku PC | odtworzenie z GitHuba według `docs/URUCHOMIENIE.md` |
| Wiadomość głosowa lub zdjęcie do bota | odpowiedź „obsługuję tylko tekst” |

## 14. Etapy budowy

| Etap | Zakres | Ukończony, gdy |
|---|---|---|
| 1. Cienki pion | repozytorium stanu; zbieracz Maca; P2 na Macu dla Backend, TestNow, Turtle; bot (`/stan`, `/pomysl`); raport 7:00; sygnał życia; `docs/URUCHOMIENIE.md` | przez 5 kolejnych dni roboczych raport 7:00 jest zgodny z ręcznym odczytem 3 projektów i przychodzi bez ręcznej interwencji, a S1, S4, S8, S10, S11, S12 przechodzą testy z `testy/etap-1.md` (dane wejściowe i oczekiwany wynik każdego przypadku) |
| 2. Źródła | Tailscale (po sprawdzeniu warunków planu), zbieracz PC, GitHub, kalendarz, poczta z kanałami, P3, P4, P11, inwentarz pozostałych kandydatów | 20 z 20 zdarzeń z `testy/zdarzenia-20.jsonl` w strumieniu z poprawnym projektem |
| 3. Agenci | sprawdzenie rozliczeń, uruchamianie na PC w budżecie, odbiór z telefonu, pytania swobodne z modelem | 5 zadań wykonanych i odebranych z telefonu, koszt w budżecie |
| 4. Życie i chmura | załącznik A | test przeprowadzki: wszystkie testy etapu 1 przechodzą na nowej maszynie |

## 15. Co zostaje z obecnego kodu

- **używamy:** format plików i wiersza zadania (`standard/`), `pm.py`, uruchamianie agentów z `dashboard/agents.py` (etap 3),
- **przebudowa:** ręczny rejestr projektów (zastąpi go inwentarz i `projekty.json` w repozytorium stanu), panel zostaje do przeglądu na komputerze, nie jest głównym wejściem,
- **nowe:** zbieracz Maca, repozytorium stanu, bot Telegram, sygnał życia, reguły zdarzeń.

## 16. Jak powstaje księga

Iteracje audytu: niezależne modele bez wglądu w poprzednie oceny. Iteracja 1 (0.1): 4 krytyczne. Iteracja 2 (0.2): 3 krytyczne, werdykt 3/3 „gotowa po poprawkach”.
Wersja 0.3 zamyka wszystkie ustalenia krytyczne; sprawdzenie spójności (Sonnet) nie znalazło nowych krytycznych, poprawki wprowadzone. Wersja 1 zaakceptowana 2026-11-12; od niej budujemy etap 1. Zmiany w `DZIENNIK.md`.

## 17. Decyzje

| # | Decyzja | Stan |
|---|---|---|
| D1 | Telefon: bot Telegram | przyjęta |
| D2 | Źródło prawdy: prywatne repozytorium git | przyjęta |
| D3 | Kanały bez API tylko przez e-maile, etap 2 | przyjęta |
| D4 | Wysyłka i publikacja tylko po odbiorze | przyjęta |
| D5 | 0 zł poza subskrypcjami | przyjęta |
| D6 | Cienki pion najpierw | przyjęta |
| D7, D9 | Klasy danych; na GitHubie tylko jawne i wewnętrzne | przyjęta |
| D8 | Mac → PC przez repozytorium, jeden zapisujący na katalog | przyjęta |
| D10 | Projekty komercyjne, dla klientów: aliasy i tylko dane jawne poza komputerami właściciela (sekcja 9) | przyjęta; przed etapem 2 sprawdzić, czy bezpłatny plan Tailscale dopuszcza użycie komercyjne, inaczej plan płatny albo inna sieć prywatna |
| D11 | Raport z danymi z ostatniej pracy Maca | przyjęta |
| D12 | Bez chmury: panel jako serwer API na PC, Mac drugim węzłem, podział zadań polem `gdzie:`, wymiana przez Git | przyjęta 2026-11-14; zastąpiona przez D13 2026-11-16 |
| D13 | Chmura zamiast PC: serwer Linux (Hetzner) dla panelu, agentów i repozytoriów; Windows tylko na godziny (Azure) i w GitHub Actions; Mac do Chrome, iOS i Androida; PC sprzedany po pełnym zabezpieczeniu danych. Powód: brak miejsca, hałas, przeprowadzka za 2 miesiące, ryzyko awarii PC. Koszt docelowy ok. 55–70 zł/mies. | przyjęta 2026-11-16 |

Otwarte przed etapem 2: nazwy portali ze zleceniami; LinkedIn i Facebook — profile prywatne czy strony firmowe.

## Załącznik A: etapy 3–4

- **Agenci (etap 3):** P8 zlecenie, P9 odbiór (zatwierdź, odrzuć z usunięciem gałęzi, poprawka jako nowe zadanie); limit czasu 60 min; Codex jako drugi wykonawca.
- **Notion (etap 3):** lustro do odczytu, zapisuje system; bez synchronizacji dwustronnej.
- **Scenariusze:** S2 powiadomienie z LinkedIna (mail) → wiadomość z kanałem i projektem; S3 praca agenta z nocy → przyciski rano; S5 termin zagrożony → propozycja; S6 limit wyczerpany → zadania czekają; S7 nowe zlecenie (mail) → pilne i kandydat; S9 nawyk niezapisany → przypomnienie, przerwa nie jest porażką.
- **Życie (etap 4):** P12 nawyk, źródła do ustalenia, dane zdrowotne tylko na komputerach właściciela.
- **Chmura (etap 4):** przeprowadzka serca, test jak w sekcji 14.
