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
- [x] Zapis kart z serwera do GitHuba co 15 min: instalacja `uruchom/serwer/zainstaluj-zapis-kart.sh` | kto: ty | czas: 2 | sprawdza: zapis-kart
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
- [x] Zainstaluj kopie i kontrolę zdrowia | kto: ty | gdzie: chmura | kiedy: 2026-11-19 | czas: 5 | sprawdza: kopia
  cel: nocna kopia danych i kontrola zdrowia z powiadomieniami ntfy działają na serwerze
  gotowe gdy: `systemctl list-timers` pokazuje kopia.timer i zdrowie.timer, a w /home/panel/kopie jest archiwum z dzisiejszą datą
  Opis kopii i kontroli zdrowia: ksiega/MIGRACJA.md, sekcja „Serwer: kopie i kontrola zdrowia”.
  - [x] ssh ops na serwer, `sudo bash /home/panel/IntegrateSystems/uruchom/serwer/zainstaluj-kopie-i-zdrowie.sh`
  - [x] w wyniku: „zapisano /home/panel/kopie/…” i stany kontroli zdrowia bez „zle”
  zamknięte 2026-11-19 na podstawie kontroli serwera (kopia: ok, ostatnia kopia 2026-11-19 06:02; kopia poza serwerem: brak, osobne zadanie)
- [x] Włącz Backups serwera w Hetznerze | kto: ty | kiedy: 2026-11-20 | czas: 2
  cel: Hetzner robi codzienną kopię całego serwera (7 ostatnich dni) poza jego dyskiem
  gotowe gdy: w Hetzner Cloud Console przy serwerze zakładka Backups ma stan włączony i pierwszą kopię
  - [ ] console.hetzner.cloud → projekt → Servers → serwer CAX11 (Helsinki) → zakładka Backups → „Enable backups”
  - [ ] następnego dnia ta sama zakładka pokazuje pierwszą kopię
  Koszt: 20% ceny serwera, ok. 1,87 $/mies. z VAT przy 9,34 $/mies. za serwer.
  wynik: API Hetzner 19.11: kopie zapasowe włączone na obu serwerach (okna 10-14 i 18-22)
- [x] Zainstaluj użytkownika agenta | kto: ty | gdzie: chmura | kiedy: 2026-11-20 | czas: 10 | sprawdza: claude-agent
  cel: agenci z panelu działają jako osobny użytkownik agent, bez dostępu do kluczy SSH, logowania Claude panelu, /etc/integrate i kopii
  gotowe gdy: `sudo bash /home/panel/IntegrateSystems/uruchom/serwer/zainstaluj-uzytkownika-agenta.sh --sprawdz` nie ma wierszy BRAK poza „Claude agenta niezalogowany”
  - [ ] zmiany rundy 3 są na GitHubie i na serwerze (zapis kart pobiera je co 15 min; inaczej `sudo -u panel git -C /home/panel/IntegrateSystems pull --ff-only`)
  - [ ] ssh ops na serwer, `sudo bash /home/panel/IntegrateSystems/uruchom/serwer/zainstaluj-uzytkownika-agenta.sh`
  - [ ] w raporcie na końcu jedyny BRAK to „Claude agenta niezalogowany”; panel działa po restarcie
  Opis: ksiega/MIGRACJA.md, sekcja „Użytkownik agenta”. Restart panelu zatrzymuje trwające uruchomienia: instaluj, gdy żaden agent nie pracuje.
  Kontrola zdrowia 2026-11-19 nie ma jeszcze wiersza claude-agent; „ok” pojawi się po logowaniu Claude agenta (następne zadanie), wtedy oba zadania wyglądają na zrobione.
  zamknięte na podstawie kontroli serwera z 2026-11-19 17:38
- [x] Zaloguj Claude dla agenta w panelu | kto: ty | gdzie: chmura | kiedy: 2026-11-20 | czas: 5 | po: Zainstaluj użytkownika agenta | sprawdza: claude-agent
  cel: Claude użytkownika agent jest zalogowany kontem Max, więc Automat i przyciski panelu uruchamiają agentów jako agent
  gotowe gdy: test połączenia w panelu kończy się „ok”, a `sudo systemctl start zdrowie && journalctl -u zdrowie -n 10 -o cat` pokazuje „claude-agent: ok”
  - [ ] panel → agenci: przy Claude „Wymaga logowania” → Zaloguj; otwórz pokazany adres, zaloguj kontem Max, wklej kod w panelu
  - [ ] panel → Test połączenia: „ok”
  - [ ] `sudo bash /home/panel/IntegrateSystems/uruchom/serwer/zainstaluj-uzytkownika-agenta.sh --sprawdz`: „Wszystko w porządku.”
  Bez panelu: przez ssh jako ops `sudo -u agent -H /home/agent/.local/bin/claude auth login`.
  zamknięte na podstawie kontroli serwera z 2026-11-19 17:38
- [ ] Załóż Storage Box i konto tylko do zapisu | kto: ty | gdzie: chmura | kiedy: 2026-11-21 | czas: 15
  cel: Storage Box z kontem pomocniczym tylko dla serwera i codziennymi migawkami, których kod z serwera nie może usunąć
  gotowe gdy: w Hetzner Console Storage Box (inna lokalizacja niż serwer) ma plan migawek codziennie, 14 sztuk, i konto pomocnicze z katalogiem integrate-serwer i samym SSH; login i hasło konta pomocniczego oraz konta głównego są w menedżerze haseł
  - [ ] konto Hetzner ma włączone 2FA
  - [ ] Hetzner Console: zamów Storage Box BX11 w innej lokalizacji niż serwer (serwer w Helsinkach → Falkenstein), zapisz uXXXXXX
  - [ ] Snapshots: plan automatyczny codziennie o 05:00, 14 migawek
  - [ ] Sub-accounts: nowe konto, katalog bazowy integrate-serwer, SSH tak, Samba i WebDAV nie; zapisz login uXXXXXX-subN
  Opis i powód (migawki zamiast borg append-only i restic): ksiega/MIGRACJA.md, sekcja „Kopia poza serwerem (Storage Box)”. Klucz i rclone na koncie pomocniczym: zadanie „Skonfiguruj kopię poza serwerem” (ma po: na tym zadaniu).
  Po założeniu napisz w rozmowie z Claude: „Storage Box gotowy”. Claude ustawi kopię poza serwerem i zrobi próbę odtworzenia.
- [x] Zaktualizuj ochronę agenta (sekrety, zapora) | kto: ty | gdzie: chmura | kiedy: 2026-11-20 | czas: 5 | sprawdza: plik /etc/nftables.d/integrate-agent.nft
  cel: agent nie czyta plików sekretów w repozytoriach projektów i nie łączy się z panelem, asystentem Useme ani API Caddy na serwerze
  gotowe gdy: `sudo bash /home/panel/IntegrateSystems/uruchom/serwer/zainstaluj-uzytkownika-agenta.sh --sprawdz` nie ma wierszy BRAK w częściach „Sekrety w projektach” i „Zapora agenta”
  - [ ] zmiany rundy 5 są na GitHubie i na serwerze (zapis kart pobiera je co 15 min; inaczej `sudo -u panel git -C /home/panel/IntegrateSystems pull --ff-only`)
  - [ ] ssh ops na serwer, `sudo bash /home/panel/IntegrateSystems/uruchom/serwer/zainstaluj-uzytkownika-agenta.sh`
  - [ ] w raporcie „Sekrety w projektach” i „Zapora agenta” bez BRAK; „w gicie” przy pliku: unieważnij ten sekret u dostawcy i usuń plik z repozytorium
  - [ ] część „Przed sprzedażą PC” w raporcie: warunki z „nie” zostają w zadaniach kopii poza serwerem i próby odtworzenia
  Opis: ksiega/MIGRACJA.md, sekcja „Użytkownik agenta”, „Sekrety i zapora”. Gdy „Zainstaluj użytkownika agenta” jest jeszcze otwarte, jedno uruchomienie instalatora zamyka oba zadania.
  wynik: instalator uruchomiony 19.11, kontrola --sprawdz: 80 ok, bez BRAK; zapora agenta aktywna

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

## Etap: Konektory agentów
termin: 2026-12-05

- [ ] Sprawdź konektory konta Claude w agentach na serwerze | kto: claude | gdzie: chmura | kiedy: 2026-11-24 | czas: 30
  cel: wiadomo, czy konektory z claude.ai (Google Drive, Notion) działają w uruchomieniach agentów na serwerze i w sesji „Rozwój panelu”, czy potrzebna jest własna konfiguracja (MCP, rclone)
  gotowe gdy: w szczegółach zadania: co działa, jak ograniczyć konektor do jednego projektu, czy da się wymusić tylko odczyt
- [ ] Zaproponuj konektory dla każdego projektu | kto: claude | gdzie: chmura | kiedy: 2026-11-24 | czas: 30
  cel: lista projekt → konektor → do czego → odczyt albo zapis, na podstawie kart, zadań i rozmów
  gotowe gdy: lista w szczegółach zadania, gotowa do zatwierdzenia przez właściciela
- [ ] Zatwierdź konektory projektów | kto: ty | kiedy: 2026-11-26 | czas: 10 | po: Zaproponuj konektory dla każdego projektu
  cel: decyzja właściciela, które projekty i jacy agenci dostają który konektor
  pyta: Lista zatwierdzona (tak albo co zmienić); Link do folderu Shield & Silent na Google Drive
- [ ] Dodaj pole konektorów do karty i panelu | kto: claude | gdzie: chmura | kiedy: 2026-11-28 | po: Sprawdź konektory konta Claude w agentach na serwerze, Zatwierdź konektory projektów
  cel: agent dostaje tylko konektory wpisane w karcie projektu; panel pokazuje je przy projekcie
  gotowe gdy: STANDARD.md opisuje pole; panel pokazuje konektory projektu; test: agent w projekcie bez wpisu nie ma dostępu do konektora
- [ ] Zaloguj Google dla Drive Shield & Silent | kto: ty | kiedy: 2026-11-30 | czas: 5 | po: Dodaj pole konektorów do karty i panelu
  cel: dostęp tylko do odczytu do folderu Shield & Silent; link do logowania przygotowuje Claude, logujesz się sam na stronie Google
- [ ] Podłącz Drive Shield & Silent tylko do odczytu | kto: claude | gdzie: chmura | kiedy: 2026-12-01 | po: Zaloguj Google dla Drive Shield & Silent
  cel: zdjęcia i filmy z Drive dostępne w panelu i dla agentów Shield & Silent bez pełnej kopii na serwerze
  gotowe gdy: pliki z Drive widoczne w Media projektu; agent projektu je czyta; pamięć podręczna do 1 GB; kopia nocna i Zasoby nie liczą plików z Drive
