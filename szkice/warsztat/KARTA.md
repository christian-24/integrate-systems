# Warsztat (silnik i język WDL)

- faza: budowa
- klient: nie
- próg: pełna
- stan: wstrzymany
- maszyna: chmura
- repozytorium: GitHub christian-24/Warsztat, serwer `~/projekty/warsztat` (gałąź main, po migracji D13); build Windows (WPF) w GitHub Actions
- założono: 2026-10-27

Szkic z repozytorium na GitHubie (stan 2026-11-06, sesja-29) i audytu PC z 2026-11-14.
343 commity od 27.10; 229 w ostatnich 14 dniach. Źródło prawdy o stanie: `docs/STATE.md` w repo.
Wstrzymany na bramce K15, niepilny (właściciel, 2026-11-14).

Karta jest umową między właścicielem a agentami pracującymi w tym projekcie. Agent czyta ją na początku każdej sesji.

## Cel
Warsztat to silnik i deklaratywny język WDL do opisu obiektów fizycznych: geometrii, elektryki i wykonania. Jeden plik tekstowy jest źródłem prawdy; silnik liczy z niego złożenie 3D, rysunki, szablony 1:1, listę cięć, wagę, koszt i elektrykę LED oraz eksportuje DXF, SVG, PDF, STEP, CSV i JSON. Lokalny serwer MCP pozwala AI walidować i przeliczać projekt zamiast zgadywać. Projekt referencyjny: wiszący regał „Kurma”.

## Zakres
- Język WDL (specyfikacja `spec/wdl-0.1.md`, zamrożona po K0), parser, walidacja z kodami błędów.
- Pakiety: meble, LED, terrarium; obliczenia geometrii, cięć, elektryki.
- Eksporty: DXF, SVG, PDF (rysunki z wymiarami, szablony 1:1), STEP, OBJ/GLB, CSV, JSON.
- CLI `wdl`, serwer MCP, klient WPF z edytorem, widokiem 3D, uchwytami i czatem AI (Haiku/Sonnet z limitem).
- Wydania: v1.0, v1.1.0, v1.3.2 (zip, test w Windows Sandbox).

## Poza zakresem
- Operacje boolowskie 3D w v1 (D6).
- Płatne zależności (tylko open source).
- Funkcje bez historyjki w planie; pomysły trafiają do `PARKING.md`.

## Definicja ukończenia
- Każdy kamień K zatwierdzony przez właściciela w `docs/gates/k<n>.md`.
- `dotnet test Warsztat.sln` zielone na `main` po każdej sesji.
- Projekt własny; jeśli okaże się mocny, zostanie rozwinięty w produkt dla klientów (sklep).

## Zasady pracy agentów
- Zespół agentów Claude Code w sesjach według `docs/SESSION.md`; role w `.claude/agents/`; zasady w `CLAUDE.md` repozytorium.
- WIP = 1 epik, 1 aktywny agent dev; QA w osobnym kontekście, merge przez PM po QA.
- Kolejny kamień dopiero po zatwierdzeniu poprzedniego przez właściciela.
- Wartości referencyjne testów (waga, koszt, prąd) liczy właściciel ręcznie.
- Stan pracy agent zapisuje w ZADANIA.md tego szkicu tylko na polecenie właściciela; w repo w `docs/STATE.md`.

## Zasoby i ograniczenia
- .NET 8, Windows (WPF), praca na PC.
- Anthropic API tylko w panelu czatu, z twardym limitem miesięcznym.
- Plan projektu w prywatnym artefakcie (link w `docs/STATE.md`).
- _Do uzupełnienia: budżet tokenów na sesję, termin._

## Pytania do właściciela
1. Bramka K15 jest otwarta od 06.11: wypróbujesz paludarium i rozstrzygniesz K15-1…K15-4, czy projekt czeka?
   Odpowiedź: Czeka i nie jest to pilne na razie
2. Test piły (P-14): czy wydrukowałeś szablon 1:1 i wyciąłeś półkę lub panele z `samples/kurma-export/`?
   Odpowiedź: Nie ale będę robil
3. Czy Warsztat to projekt własny bez klienta, i jaki jest jego cel końcowy (publiczne wydanie, sprzedaż, narzędzie do własnej pracowni)?
   Odpowiedź: Własny ale jak będzie mocny zostanie pociągnięty w store kientowa
