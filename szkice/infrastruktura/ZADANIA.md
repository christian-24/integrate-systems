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
- [x] Zapis kart z serwera do GitHuba co 15 min: instalacja `uruchom/serwer/zainstaluj-zapis-kart.sh` | kto: ty | czas: 2
- [x] Pole „gdzie:” w zadaniach po D13: chmura, mac; pc tylko dla Windows i migracji (2026-11-17)
- [x] Automat, raport PM o 7:00, powiadomienia ntfy (2026-11-17)
- [ ] Uruchom synchronizację rozmów z Maca na serwer | kto: claude | gdzie: chmura
  cel: rozmowy Claude Code z Maca trafiają na serwer bez ręcznego kopiowania
  gotowe gdy: rozmowa z Maca z ostatniej godziny jest widoczna na serwerze; zmiany konfiguracji serwera po zgodzie właściciela
  materiał: KARTA.md#Zakres
  materiał: KARTA.md#Zasady pracy agentów
- [ ] Zbuduj dziennik aktywności z rozmów w panelu | kto: claude | gdzie: chmura
  cel: panel pokazuje dziennik aktywności złożony z rozmów z Maca i serwera
  gotowe gdy: dziennik w panelu pokazuje wpisy z obu maszyn z ostatnich 24 h
  materiał: KARTA.md#Zakres
  Zaczyna się po synchronizacji rozmów z Maca.
- [ ] Zainstaluj kopie i kontrolę zdrowia | kto: ty | gdzie: chmura | kiedy: 2026-11-19 | czas: 5
  cel: nocna kopia danych i kontrola zdrowia z powiadomieniami ntfy działają na serwerze
  gotowe gdy: `systemctl list-timers` pokazuje kopia.timer i zdrowie.timer, a w /home/panel/kopie jest archiwum z dzisiejszą datą
  Opis kopii i kontroli zdrowia: ksiega/MIGRACJA.md, sekcja „Serwer: kopie i kontrola zdrowia”.
  - [ ] ssh ops na serwer, `sudo bash /home/panel/IntegrateSystems/uruchom/serwer/zainstaluj-kopie-i-zdrowie.sh`
  - [ ] w wyniku: „zapisano /home/panel/kopie/…” i stany kontroli zdrowia bez „zle”
- [ ] Włącz Backups serwera w Hetznerze | kto: ty | kiedy: 2026-11-20 | czas: 2
  cel: Hetzner robi codzienną kopię całego serwera (7 ostatnich dni) poza jego dyskiem
  gotowe gdy: w Hetzner Cloud Console przy serwerze zakładka Backups ma stan włączony i pierwszą kopię
- [ ] Dodaj zewnętrzny monitoring adresu panelu (UptimeRobot, darmowy) | kto: ty | kiedy: 2026-11-21 | czas: 10
  cel: powiadomienie, gdy adres panelu nie odpowiada z zewnątrz (awaria całego serwera albo Caddy)
  gotowe gdy: monitor HTTPS na https://2-29-181-133.sslip.io/wejscie ma stan Up i alert na e-mail albo w aplikacji

## Etap: Migracja z PC

- [x] Zabezpieczenie danych z PC na dysk i GitHub (`ksiega/MIGRACJA-INSTRUKCJA-PC.md`) | kto: ty | gdzie: pc
- [ ] Przenieś stan z SPIS.md kopii PC do planu migracji | kto: claude | gdzie: mac
  cel: plan migracji pokazuje, co z PC jest już bezpieczne, a czego brakuje
  gotowe gdy: w ksiega/MIGRACJA.md kolumna „Stan” tabeli „Dane do zabrania z PC” wypełniona w każdym wierszu według SPIS.md
  SPIS.md leży na dysku zewnętrznym w Migracja-PC-2026-11; agent na Macu potrzebuje podłączonego dysku, inaczej oznacza [!] z blokadą.
- [x] Repozytoria projektów na serwerze w ~/projekty, karty podpięte dowiązaniami (2026-11-17)
- [ ] Przeprowadź dzień próbny bez PC | kto: ty
  cel: potwierdzenie, że do pracy nie jest potrzebny PC
  gotowe gdy: 24 h bez włączania PC i bez brakujących danych; braki zapisane w notatce pod tym zadaniem
  Warunek etapu 4 z ksiega/MIGRACJA.md; po nim PC idzie do resetu i sprzedaży.
- [ ] Przygotuj PC do sprzedaży | kto: ty | gdzie: pc
  cel: PC bez danych, kont i dostępu do serwerów i GitHuba
  gotowe gdy: wszystkie kroki zaznaczone; reset Windows zakończony
  - [ ] usuń autostart asystenta z Harmonogramu zadań
  - [ ] wyłącz sshd, portproxy i reguły zapory
  - [ ] wyloguj konta Microsoft, Google, GitHub, Claude i Codex
  - [ ] usuń klucze SSH tego PC z GitHuba
  - [ ] zresetuj Windows opcją „Usuń wszystko” z czyszczeniem dysków C: i E:
  Dopiero po dniu próbnym bez PC.
