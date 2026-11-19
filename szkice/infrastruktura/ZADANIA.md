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
- [ ] Zbuduj dziennik aktywności z rozmów w panelu | kto: claude | gdzie: chmura | po: Uruchom synchronizację rozmów z Maca
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
  Stan serwera w panelu 2026-11-19 06:02: kopia „ok”, ostatnia kopia 2026-11-19 06:02, kopia poza serwerem „brak”. Gdy `systemctl list-timers` pokazuje oba timery, zamknij zadanie.
- [ ] Włącz Backups serwera w Hetznerze | kto: ty | kiedy: 2026-11-20 | czas: 2
  cel: Hetzner robi codzienną kopię całego serwera (7 ostatnich dni) poza jego dyskiem
  gotowe gdy: w Hetzner Cloud Console przy serwerze zakładka Backups ma stan włączony i pierwszą kopię
  - [ ] console.hetzner.cloud → projekt → Servers → serwer CAX11 (Helsinki) → zakładka Backups → „Enable backups”
  - [ ] następnego dnia ta sama zakładka pokazuje pierwszą kopię
  Koszt: 20% ceny serwera, ok. 1,87 $/mies. z VAT przy 9,34 $/mies. za serwer.
- [ ] Dodaj zewnętrzny monitoring adresu panelu (UptimeRobot, darmowy) | kto: ty | kiedy: 2026-11-21 | czas: 10
  cel: powiadomienie, gdy adres panelu nie odpowiada z zewnątrz (awaria całego serwera albo Caddy)
  gotowe gdy: monitor HTTPS na https://2-29-181-133.sslip.io/wejscie ma stan Up i alert na e-mail albo w aplikacji
  - [ ] uptimerobot.com: konto darmowe, „Add New Monitor”, typ HTTP(s), URL https://2-29-181-133.sslip.io/wejscie, interwał 5 min
  - [ ] Alert Contacts: Twój e-mail albo aplikacja UptimeRobot na iPhonie; monitor ma stan Up
- [ ] Skonfiguruj kopię poza serwerem (Storage Box) | kto: ty | gdzie: chmura | kiedy: 2026-11-21 | czas: 20 | po: Zainstaluj kopie i kontrolę zdrowia
  cel: nocna kopia trafia zaszyfrowana poza serwer, więc utrata serwera nie zabiera danych
  gotowe gdy: `journalctl -u kopia` pokazuje „zaszyfrowano” i „wysłano poza serwer”, w /home/panel/kopie/ostatnia.json jest "off": true, a hasło kopii jest w menedżerze haseł
  Kroki: ksiega/MIGRACJA.md, sekcja „Kopia poza serwerem (Storage Box)”.
  - [ ] zamów Storage Box BX11 w Hetzner Robot, włącz SSH, zapisz użytkownika uXXXXXX
  - [ ] klucz kopii panelu, zdalny rclone `storagebox`, plik hasła /home/panel/.kopia-haslo (600)
  - [ ] KOPIA_CEL i KOPIA_HASLO_PLIK w /etc/integrate/serwer.env, `sudo systemctl start kopia`
- [ ] Wykonaj próbę odtworzenia (odtworz.sh --sprawdz) | kto: ty | gdzie: chmura | kiedy: 2026-11-22 | czas: 30 | po: Skonfiguruj kopię poza serwerem
  cel: wiadomo, że kopię z Storage Box da się odczytać i ile trwa odtworzenie
  gotowe gdy: `odtworz --sprawdz` na archiwum pobranym ze Storage Box kończy się „archiwum poprawne”, rozpakowanie do /tmp działa, a czas próby jest wpisany w ksiega/MIGRACJA.md, sekcja „Odtworzenie serwera”
  - [ ] `ssh ops@2.29.181.133`, `sudo -u panel rclone copy storagebox:integrate/<RRRR-MM-DD>.tar.gz.gpg /tmp/proba/` (najnowsze archiwum)
  - [ ] `sudo -u panel odtworz --sprawdz --haslo-plik /home/panel/.kopia-haslo /tmp/proba/<RRRR-MM-DD>.tar.gz.gpg`: „archiwum poprawne”
  - [ ] `sudo -u panel odtworz --haslo-plik /home/panel/.kopia-haslo /tmp/proba/<RRRR-MM-DD>.tar.gz.gpg /tmp/proba/dane`; czas zanotowany
  - [ ] `rm -rf /tmp/proba` (dane klientów); data i czas próby w ksiega/MIGRACJA.md, sekcja „Odtworzenie serwera”
  Polecenia z ksiega/MIGRACJA.md, sekcja „Odtworzenie serwera”, próba bez ryzyka: niczego poza /tmp/proba nie nadpisuje.
- [ ] Zainstaluj użytkownika agenta | kto: ty | gdzie: chmura | kiedy: 2026-11-20 | czas: 10
  cel: agenci z panelu działają jako osobny użytkownik agent, bez dostępu do kluczy SSH, logowania Claude panelu, /etc/integrate i kopii
  gotowe gdy: `sudo bash /home/panel/IntegrateSystems/uruchom/serwer/zainstaluj-uzytkownika-agenta.sh --sprawdz` nie ma wierszy BRAK poza „Claude agenta niezalogowany”
  - [ ] zmiany rundy 3 są na GitHubie i na serwerze (zapis kart pobiera je co 15 min; inaczej `sudo -u panel git -C /home/panel/IntegrateSystems pull --ff-only`)
  - [ ] ssh ops na serwer, `sudo bash /home/panel/IntegrateSystems/uruchom/serwer/zainstaluj-uzytkownika-agenta.sh`
  - [ ] w raporcie na końcu jedyny BRAK to „Claude agenta niezalogowany”; panel działa po restarcie
  Opis: ksiega/MIGRACJA.md, sekcja „Użytkownik agenta”. Restart panelu zatrzymuje trwające uruchomienia: instaluj, gdy żaden agent nie pracuje.
- [ ] Zaloguj Claude dla agenta w panelu | kto: ty | gdzie: chmura | kiedy: 2026-11-20 | czas: 5 | po: Zainstaluj użytkownika agenta
  cel: Claude użytkownika agent jest zalogowany kontem Max, więc Automat i przyciski panelu uruchamiają agentów jako agent
  gotowe gdy: test połączenia w panelu kończy się „ok”, a `sudo systemctl start zdrowie && journalctl -u zdrowie -n 10 -o cat` pokazuje „claude-agent: ok”
  - [ ] panel → agenci: przy Claude „Wymaga logowania” → Zaloguj; otwórz pokazany adres, zaloguj kontem Max, wklej kod w panelu
  - [ ] panel → Test połączenia: „ok”
  - [ ] `sudo bash /home/panel/IntegrateSystems/uruchom/serwer/zainstaluj-uzytkownika-agenta.sh --sprawdz`: „Wszystko w porządku.”
  Bez panelu: przez ssh jako ops `sudo -u agent -H /home/agent/.local/bin/claude auth login`.
- [ ] Załóż Storage Box i konto tylko do zapisu | kto: ty | gdzie: chmura | kiedy: 2026-11-21 | czas: 15
  cel: Storage Box z kontem pomocniczym tylko dla serwera i codziennymi migawkami, których kod z serwera nie może usunąć
  gotowe gdy: w Hetzner Console Storage Box (inna lokalizacja niż serwer) ma plan migawek codziennie, 14 sztuk, i konto pomocnicze z katalogiem integrate-serwer i samym SSH; login i hasło konta pomocniczego oraz konta głównego są w menedżerze haseł
  - [ ] konto Hetzner ma włączone 2FA
  - [ ] Hetzner Console: zamów Storage Box BX11 w innej lokalizacji niż serwer (serwer w Helsinkach → Falkenstein), zapisz uXXXXXX
  - [ ] Snapshots: plan automatyczny codziennie o 05:00, 14 migawek
  - [ ] Sub-accounts: nowe konto, katalog bazowy integrate-serwer, SSH tak, Samba i WebDAV nie; zapisz login uXXXXXX-subN
  Opis i powód (migawki zamiast borg append-only i restic): ksiega/MIGRACJA.md, sekcja „Kopia poza serwerem (Storage Box)”. Klucz i rclone na koncie pomocniczym: zadanie „Skonfiguruj kopię poza serwerem”.

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
- [ ] Przygotuj PC do sprzedaży | kto: ty | gdzie: pc | po: Przeprowadź dzień próbny bez PC
  cel: PC bez danych, kont i dostępu do serwerów i GitHuba
  gotowe gdy: wszystkie kroki zaznaczone; reset Windows zakończony
  - [ ] usuń autostart asystenta z Harmonogramu zadań
  - [ ] wyłącz sshd, portproxy i reguły zapory
  - [ ] wyloguj konta Microsoft, Google, GitHub, Claude i Codex
  - [ ] usuń klucze SSH tego PC z GitHuba
  - [ ] zresetuj Windows opcją „Usuń wszystko” z czyszczeniem dysków C: i E:
  Dopiero po dniu próbnym bez PC.
