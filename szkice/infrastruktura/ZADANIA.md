# Zadania: Infrastruktura

> Jedyna lista zadań projektu. Czyta ją panel i agenci.
> Wiersz: `- [ ] Tytuł | kto: claude | gdzie: pc | kiedy: RRRR-MM-DD | pora: noc | czas: 30 | wymaga: zgoda`
> Stany: `[ ]` do zrobienia, `[~]` w toku, `[!]` zablokowane (dodaj `blokada: powód`), `[x]` zrobione.

## Etap: Serwer

- [x] Serwer CAX11 utworzony, klucz Maca (2026-11-17)
- [x] Zabezpieczenie: użytkownicy ops i panel, SSH tylko kluczem, zapora, aktualizacje, swap (2026-11-17)
- [x] Python, git, Caddy, Claude Code (2026-11-17)
- [x] Klucz serwera dodany w GitHubie (2026-11-17)
- [x] Prywatne repozytorium integrate-systems (2026-11-17)
- [x] IntegrateSystems wypchnięty, skan sekretów czysty (2026-11-17)
- [x] Claude zalogowany na serwerze (Max); test połączenia z panelu przeszedł (2026-11-17)
- [x] Adres panelu: https://2-29-181-133.sslip.io (bez domen Opisarni i Oprogramowani)
- [x] Panel jako usługa systemd za Caddy z HTTPS (2026-11-17)
- [x] Hasło panelu ustawione (2026-11-17)
- [ ] Połączenie SSH „Serwer” w aplikacji Claude na Macu (użytkownik panel) | kto: ty | czas: 5
- [ ] Zapis kart z serwera do GitHuba co 15 min: instalacja `uruchom/serwer/zainstaluj-zapis-kart.sh` | kto: ty | czas: 2
- [x] Pole „gdzie:” w zadaniach po D13: chmura, mac; pc tylko dla Windows i migracji (2026-11-17)
- [ ] Synchronizacja rozmów z Maca i dziennik aktywności | kto: claude | gdzie: chmura

## Etap: Migracja z PC

- [~] Zabezpieczenie danych z PC na dysk i GitHub (`ksiega/MIGRACJA-INSTRUKCJA-PC.md`) | kto: ty | gdzie: pc
- [ ] Przenieść SPIS.md z PC do planu migracji | kto: claude | gdzie: mac
- [x] Repozytoria projektów na serwerze w ~/projekty, karty podpięte dowiązaniami (2026-11-17)
- [ ] Dzień próbny bez PC | kto: ty
- [ ] Przed sprzedażą: autostart, SSH, zapora, wylogowanie kont, klucze PC na GitHubie, reset „Usuń wszystko” | kto: ty | gdzie: pc
