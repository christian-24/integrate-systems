# Zadania: Szukanie auta (asystent OLX i OTOMOTO)

> Jedyna lista zadań projektu. Czyta ją panel i agenci.
> Wiersz: `- [ ] Tytuł | kto: claude | gdzie: pc | kiedy: RRRR-MM-DD | pora: noc | czas: 30 | wymaga: zgoda`
> Stany: `[ ]` do zrobienia, `[~]` w toku, `[!]` zablokowane (dodaj `blokada: powód`), `[x]` zrobione.
> Pola są opcjonalne. kto: claude, codex, ty. gdzie: pc, mac, chmura. pora: dzień, noc. czas: minuty Twojej pracy. wymaga: zgoda, odbiór.

> Szkic z audytu PC (2026-11-14). Kodu nie czytano.

## Etap: Działająca wersja

- [x] Rozszerzenie „Asystent aut OLX + OTOMOTO” do wersji 2.12.0 (indeks, analiza AI, harmonogram)
- [x] Przejście analiz z OpenAI API na Codex CLI
- [x] Panel „Garaż”
- [ ] Prowadź codzienny przegląd ogłoszeń aut z OLX i OTOMOTO | kto: codex | gdzie: mac
  cel: nowe ogłoszenia oceniane codziennie według kryteriów właściciela, wyniki w panelu „Garaż”
  gotowe gdy: przegląd działa sam 7 kolejnych dni bez PC, a „Garaż” pokazuje oceny z każdego dnia
  materiał: KARTA.md#Zakres
  Rozszerzenie działa w Chrome na Macu, analizy przez Codex CLI na koncie ChatGPT.

## Do rozplanowania

- [x] Rozdział: szukanie auta osobno, Useme do Oprogramowani (2026-11-14)
- [x] Część aut w osobnym repozytorium szukanie-auta (2026-11-16)
- [ ] Opisz uruchomienie i harmonogram w README repozytorium szukanie-auta | kto: claude | gdzie: chmura | kiedy: 2026-11-21
  cel: README pozwala uruchomić narzędzie na Macu bez PC
  gotowe gdy: README ma sekcje „Jak uruchomić” (backend, rozszerzenie Chrome, Codex CLI) i „Harmonogram” (kiedy i jak działa przegląd)
  materiał: README.md
  materiał: KARTA.md#Zakres
