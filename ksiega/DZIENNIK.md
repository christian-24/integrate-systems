# Dziennik księgi

## 2026-11-12: wersja 0
- Szkic na podstawie rozmowy z właścicielem i sprawdzenia dostępnych źródeł z Maca.
- Następny krok: odpowiedzi na pytania z sekcji 10, potem audyt.

## 2026-11-12: wersja 0.1
- Odpowiedzi właściciela: kanały GitHub, Notion (wdrożenie), LinkedIn, Facebook, portale ze zleceniami; projekty także na PC i w chmurze; serce na PC, docelowo możliwa chmura; powiadomienia: cokolwiek darmowego i prostego.
- Decyzje: najpierw system 1 (inwentarz); powiadomienia przez ntfy; Turtle jako epik w backlogu; dwa obszary, Praca i Życie (dieta, siłownia jako projekty ciągłe), Życie budowane później.
- Dodano: obszary, model portfel → projekt → epik → zadanie, stany projektu, P2 kwalifikacja, P12 nawyk, scenariusze S7–S9.

## 2026-11-12: audyt, iteracja 1
- Trzy niezależne przeglądy wersji 0.1: Opus, Sonnet, Haiku (`audyt/iteracja-1-*.md`), zestawienie w `audyt/ZESTAWIENIE.md`.
- 4 ustalenia krytyczne: kanały bez API, brak połączenia Mac–PC i źródła prawdy, brak kanału telefon → system, limity i koszty bez budżetu.
- Wspólny wniosek: cienki pion na 3 znanych projektach przed pełnym systemem 1.
- Następny krok: decyzje D1–D7 właściciela, potem wersja 0.2 i iteracja 2 audytu.

## 2026-11-12: wersja 0.2 i audyt, iteracja 2
- Wersja 0.2 po decyzjach D1–D7; poprzednia w `audyt/KSIEGA-0.1.md`.
- Iteracja 2: Fable, Opus, Sonnet, z weryfikacją faktów (`audyt/iteracja-2-*.md`, `audyt/ZESTAWIENIE-2.md`).
- Werdykt 3/3: gotowa po poprawkach. Krytyczne: brak drogi Mac → PC w etapie 1, dane poufne w kopii na GitHubie, niepewne rozliczanie `claude -p` na subskrypcji.
- Następny krok: decyzje D8–D11, wersja 0.3, akceptacja właściciela jako wersja 1.

## 2026-11-12: wersja 0.3
- Decyzje D8, D9, D11 przyjęte; D10 (czy projekty są komercyjne) otwarta, do rozstrzygnięcia przed etapem 1.
- Poprawki wszystkich 13 ustaleń iteracji 2; etap 1 bez modelu; etapy 3–4 w załączniku A.
- Sprawdzenie spójności (Sonnet): brak nowych krytycznych; poprawione: osobna gałąź `mac` (Mac nie wypycha do gałęzi PC), klasy pól zdarzenia, raport do czatu właściciela, brak powrotu zarchiwizowanych kandydatów, testy etapu 1 w `testy/etap-1.md`.
- Następny krok: D10 i akceptacja właściciela → wersja 1.

## 2026-11-12: wersja 1
- D10: projekty są komercyjne, dla klientów. Projekty klienckie występują poza komputerami właściciela tylko pod aliasem i tylko z danymi jawnymi; prawdziwe nazwy w `lokalne/aliasy.json` poza repozytorium.
- Przed etapem 2: sprawdzić, czy bezpłatny plan Tailscale dopuszcza użycie komercyjne.
- Księga zaakceptowana jako wersja 1. Następny krok: budowa etapu 1 (sekcja 14).

## 2026-11-12: budowa etapu 1, zmiana w wersji 1
- Kod w `system/`: kontrakt `system/KONTRAKT.md`, instrukcja `system/URUCHOMIENIE.md`, przypadki testowe `system/testy/etap-1.md`.
- Zmiana: P2 w etapie 1 odbywa się na Macu (`zbieracz.py kwalifikuj`), nie w Telegramie. Powód: projekty klienckie poza Makiem występują tylko pod aliasem, więc w Telegramie nie da się pokazać prawdziwych nazw kandydatów. Przyciski P2 w Telegramie wracają w etapie 2 razem z siecią prywatną.
- Zbudowane: `system/zbieracz.py` (Mac), `system/serce.py` (PC, bot Telegram), skrypty instalacji w `system/uruchom/`. Testy: 42 (zbieracz 17, serce 23, całość 2), bez sieci i bez prawdziwych danych.
- Próba zbieracza na Macu w trybie `podglad` (tylko liczby): 11 kandydatów, 1 katalog bez dostępu.
- Nie sprawdzone: prawdziwy Telegram, GitHub, healthchecks, PC z Windows, launchd. To kroki właściciela z `system/URUCHOMIENIE.md`; potem testy z `system/testy/etap-1.md` przez 5 dni roboczych.

## 2026-11-12: kierunek interfejsu
- Pulpit w stylu narzędzia do zadań (czytelna czcionka systemowa, plakietki stanów): przegląd z tabelą projektów (opis, faza, stan, postęp, najbliższy termin, zgodność z księgą), strona projektu (opis, faza od pomysłu do utrzymania, tablica, etapy i terminy, księga, marketing), tablica zadań ze wszystkich projektów, terminy, „wymaga Ciebie”. Projekty wybiera się z listy z wyszukiwarką, nie z zakładek.
- Prototyp na danych przykładowych: `ksiega/pulpit-projektow.html`.
- Fazy projektu: Pomysł, Księga, Budowa, Wdrożenie, Marketing, Utrzymanie. Osobne widoki stanu marketingu i projektu później.
- Wizualizacja w stylu pixel art (postacie pokazujące przepływ pracy) zostaje jako opcjonalny, ostatni element: mała ramka w tle.
- Pulpit dostał widok „Wskaźniki” (cały portfel albo jeden projekt) i zakładkę „Wskaźniki” na stronie projektu: postęp %, tempo, praca w toku, zaległe, etapy w terminie, czas zadania; wykresy postępu w czasie, zadań zakończonych na tydzień, przepływu pracy, spalania etapu; porównanie projektów. Wymaga od systemu codziennego zapisu liczby zadań w każdym stanie (historia tygodni).

## 2026-11-12: nowy pulpit w panelu
- Panel na porcie 4801 przebudowany według `dashboard/PULPIT.md`: widoki Przegląd, Wskaźniki, Wymaga Ciebie, Tablica, Terminy, Agenci, Projekty oraz strona projektu (tablica, wskaźniki, etapy, księga, marketing). Dawne funkcje zachowane.
- Karta projektu ma nowe pola: `faza`, `klient`, `próg`; faza wyliczana, gdy jej brak. Panel czyta też projekty zakwalifikowane zbieraczem, bez ręcznej rejestracji. Codzienny zapis historii stanów zadań w `historia/` zasila wykresy.
- Nie przeniesione: siatka kalendarza na 3 tygodnie, propozycje okien czasu dla zadań, wspólna oś kampanii, skróty dawnego Monitora.
- Sprawdzone na porcie testowym z projektem tymczasowym i atrapą agenta: zapis stanu zadania, zmiana fazy, uruchomienie agenta, szerokość 375 px. Testy: 67.

## 2026-11-13: baza wiedzy, pytania i logowanie w panelu
- Kwalifikacja 11 kandydatów z Maca (`szkice/KWALIFIKACJA.md`); szkice kart dla Opisarni, audytów, NaulikApp, TestNow w `szkice/`, dodane do rejestru panelu.
- Panel: pytania z sekcji „Pytania do właściciela” z odpowiedzią zapisywaną w KARTA.md; przycisk „Zaloguj” otwiera Terminal z logowaniem; `Panel.command` uruchamia panel dwuklikiem; poprawione łamanie braków w księdze.

## 2026-11-14: audyt PC i decyzja D12
- Audyt PC (repozytoria, sesje Codex, rozmowy Claude Code): `szkice/AUDYT-PC-2026-11-14.md`. Szkice 6 projektów uzupełnione i odpowiedzi właściciela wpisane do kart. Na PC przechowywanie rozmów Claude Code ustawione na 365 dni.
- Rozważona migracja do chmury (serwer Hetzner, agenci w chmurze Anthropic). Właściciel odrzucił: 100% w jednym miejscu nie jest możliwe (grupy Facebooka, build na Windows, iPhone), a częściowa chmura to kolejne miejsce do pilnowania.
- D12: panel jako serwer API na PC, Mac drugim węzłem, podział zadań polem `gdzie:`, wymiana przez Git. PC nie musi działać całą dobę.
- Następne kroki: dokończyć w panelu okno „Co dziś robimy?” (plan dnia od PM, uruchamianie zaznaczonych zadań); uruchomić panel na PC z dostępem z Maca i iPhone'a w sieci domowej; przypisać `gdzie:` zadaniom w kartach.
- Panel: okno „Co dziś robimy?” w Przeglądzie (plan dnia od PM z otwartych zadań, uruchamianie zaznaczonych). Sprawdzone na porcie testowym z kopią projektów i atrapą agenta, także przy 375 px. Testy: 79.

## 2026-11-16: D13, migracja do chmury
- Właściciel zmienił D12: brak miejsca na PC w kawalerce, hałas w nocy, kolejna przeprowadzka za 2 miesiące, ryzyko zawieszenia PC pod nieobecność. PC idzie na sprzedaż po migracji.
- D13: serwer Linux (Hetzner) dla panelu, agentów i repozytoriów; Windows w Azure tylko na godziny i build w GitHub Actions; Mac do Chrome, iOS i Androida. Szacunek: ok. 55–70 zł/mies.
- Plan i lista danych do zabrania z PC: `MIGRACJA.md`.
