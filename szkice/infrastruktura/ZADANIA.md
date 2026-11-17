# Zadania: Infrastruktura

> Jedyna lista zadań projektu. Czyta ją panel i agenci.
> Wiersz: `- [ ] Tytuł | kto: claude | gdzie: pc | kiedy: RRRR-MM-DD | pora: noc | czas: 30 | wymaga: zgoda`
> Stany: `[ ]` do zrobienia, `[~]` w toku, `[!]` zablokowane (dodaj `blokada: powód`), `[x]` zrobione.

## Etap: Serwer

- [x] Serwer CAX11 utworzony, klucz Maca (2026-11-17)
- [x] Zabezpieczenie: użytkownicy ops i panel, SSH tylko kluczem, zapora, aktualizacje, swap (2026-11-17)
- [x] Python, git, Caddy, Claude Code (2026-11-17)
- [ ] Klucz serwera dodany w GitHub → Settings → SSH keys | kto: ty | czas: 2
- [ ] Puste prywatne repozytorium integrate-systems na GitHubie | kto: ty | czas: 2
- [ ] Wypchnąć IntegrateSystems do integrate-systems | kto: claude | gdzie: mac | wymaga: zgoda
- [ ] Logowanie Claude na serwerze | kto: ty | czas: 5
- [ ] Rekord A dla adresu panelu w Cloudflare | kto: ty | czas: 5
- [ ] Panel jako usługa za Caddy z HTTPS i hasłem | kto: claude | gdzie: chmura
- [ ] Połączenie SSH „Serwer” w aplikacji Claude na Macu (użytkownik panel) | kto: ty | czas: 5
- [ ] Synchronizacja rozmów z Maca i dziennik aktywności | kto: claude | gdzie: chmura

## Etap: Migracja z PC

- [~] Zabezpieczenie danych z PC na dysk i GitHub (`ksiega/MIGRACJA-INSTRUKCJA-PC.md`) | kto: ty | gdzie: pc
- [ ] Przenieść SPIS.md z PC do planu migracji | kto: claude | gdzie: mac
- [ ] Pobrać repozytoria projektów na serwer | kto: claude | gdzie: chmura
- [ ] Dzień próbny bez PC | kto: ty
- [ ] Przed sprzedażą: autostart, SSH, zapora, wylogowanie kont, klucze PC na GitHubie, reset „Usuń wszystko” | kto: ty | gdzie: pc
