# Zadania: Warsztat (silnik i język WDL)

> Jedyna lista zadań projektu. Czyta ją panel i agenci.
> Wiersz: `- [ ] Tytuł | kto: claude | gdzie: pc | kiedy: RRRR-MM-DD | pora: noc | czas: 30 | wymaga: zgoda`
> Stany: `[ ]` do zrobienia, `[~]` w toku, `[!]` zablokowane (dodaj `blokada: powód`), `[x]` zrobione.
> Pola są opcjonalne. kto: claude, codex, ty. gdzie: pc, mac, chmura. pora: dzień, noc. czas: minuty Twojej pracy. wymaga: zgoda, odbiór.
> Etap to nagłówek `## Etap: nazwa` i wiersz `termin: RRRR-MM-DD` pod nim. Etap bez otwartych zadań jest zamknięty.

> Szkic z `docs/STATE.md` i CHANGELOG repozytorium (stan 2026-11-06). Szczegółowe historyjki są w repo (`docs/k*-stories.md`).

## Etap: v1.0 (K0–K6)

- [x] K0 język WDL, K1 pakiety i meble, K2 geometria i eksporty, K3–K6 (2026-10-27 do 2026-11-03)
- [x] Wydanie v1.0: silnik, CLI, MCP, klient WPF, STEP

## Etap: v1.1–v1.3 (K7–K14)

- [x] K7 kolizje, K9 czat AI z zaznaczeniem i podglądem zmian, wydanie 1.1.0
- [x] K10 interfejs 1.2, K11 lista części i strona złożenia, K12 jeden runtime
- [x] K13 place i group, paludarium, K14 uchwyty 3D zapisywane do WDL
- [x] Wydanie v1.3.2

## Etap: K15 kształty

- [x] Łuki, kontury, profile krawędzi, uchwyty w łańcuchu parametrów (US15.1–US15.6, 2026-11-06)

## Do rozplanowania

- [ ] Zrealizuj K16 według docs/plan-paludarium.md | kto: claude | gdzie: chmura | wymaga: zgoda
  cel: kamień K16 gotowy do bramki właściciela
  gotowe gdy: historyjki K16 zamknięte, `dotnet test Warsztat.sln` zielone na main, bramka w docs/gates/k16.md czeka na właściciela
  materiał: docs/plan-paludarium.md
  materiał: KARTA.md#Zasady pracy agentów
  Start dopiero po zatwierdzeniu bramki K15 (docs/gates/k15.md); projekt wstrzymany (2026-11-14). Build Windows w GitHub Actions.
- [ ] Uzupełnić pliki projektu według standardu | kto: claude
  cel: Uzupełnić według standard/STANDARD.md: Zadania (3 braki), README (4 braki), Architektura (brak pliku), Uruchomienie (brak pliku), Instrukcje agentów (3 braki). Niczego nie nadpisywać; na końcu python3 standard/projekt.py sprawdz bez braków w tym projekcie.
