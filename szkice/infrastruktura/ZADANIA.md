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

- [x] Sprawdź konektory konta Claude w agentach na serwerze | kto: claude | gdzie: chmura | kiedy: 2026-11-24 | czas: 30
  cel: wiadomo, czy konektory z claude.ai (Google Drive, Notion) działają w uruchomieniach agentów na serwerze i w sesji „Rozwój panelu”, czy potrzebna jest własna konfiguracja (MCP, rclone)
  gotowe gdy: w szczegółach zadania: co działa, jak ograniczyć konektor do jednego projektu, czy da się wymusić tylko odczyt
  Co działa (stan 2026-11-24, z kodu panelu, konfiguracji konta agenta i dokumentacji Claude Code):
  - Uruchomienia z panelu (zadania, raport PM, rozmowy, Asystent): konektorów konta nie ma. Panel od 2026-11-23 startuje je z `--strict-mcp-config` (`dashboard/agents.py`); to uruchomienie też nie dostało żadnego narzędzia konektora.
  - Sesja „Rozwój panelu” (Remote Control, logowanie konta agenta): Claude Code sam pobiera konektory z claude.ai, bez ograniczeń. Na koncie były dotąd łączone: Claude Docs, PubMed, Atlassian, Three.js 3D Viewer, Canva. Google Drive i Notion nie były łączone, więc dziś nie działają nigdzie.
  - Konektory konta wymagają logowania subskrypcji (`claude auth login`). Z tokenem z `claude setup-token` (`CLAUDE_CODE_OAUTH_TOKEN`) nie ładują się wcale.
  - Google Drive przez rclone jest już w repozytorium (`dashboard/drive.py`, `uruchom/serwer/drive@.service`): osobne połączenie na projekt, montowane w `media/drive` karty. Żaden projekt nie ma jeszcze połączenia.
  Ograniczenie do jednego projektu:
  - Konektor konta jest wspólny dla całego konta; claude.ai nie przypisuje go do folderu. Po stronie serwera da się go tylko wyłączać: wszystkie (`disableClaudeAiConnectors: true` w `.claude/settings.json` projektu albo `ENABLE_CLAUDEAI_MCP_SERVERS=false`), pojedynczo (`deniedMcpServers` z nazwą, np. `claude.ai Notion`).
  - Pewna droga: własna konfiguracja na projekt. Panel zostawia `--strict-mcp-config` i dokłada `--mcp-config <plik projektu>` tylko tam, gdzie karta ma wpis. Projekt bez wpisu nie ma konektora (to jest test z zadania „Dodaj pole konektorów do karty i panelu”).
  - Drive: rclone już działa na projekt (`drive-<projekt>`, `root_folder_id` = jeden folder).
  Tylko odczyt:
  - Drive: tak, twardo. rclone loguje z zakresem `drive.readonly` i montuje z `--read-only`; token leży u użytkownika `panel`, agent go nie czyta.
  - Notion: tak, twardo, ale tylko przez własną integrację Notion (uprawnienie „Read content”, udostępnione wybrane strony) podaną w `--mcp-config`. Konektor Notion z claude.ai ma pełny dostęp konta do odczytu i zapisu.
  - Konektor konta: tylko miękko, regułami Claude Code. `--allowedTools` z nazwami narzędzi odczytu (`mcp__claude_ai_<konektor>__<narzędzie>`) i `--disallowedTools` dla zapisu; zabronione wygrywa z dozwolonym, a w uruchomieniu bez okna narzędzie spoza listy jest odrzucane. Token konektora dalej pozwala na zapis, a zakresu do folderu nie ma.
  wynik: Ustalenia powyżej. Konektory konta nie działają w uruchomieniach z panelu (celowo wyłączone), działają tylko w sesji „Rozwój panelu”; Google Drive i Notion nie są podłączone na koncie. Zalecenie zapisane w DECYZJE.md: własna konfiguracja na projekt (Drive przez rclone tylko do odczytu, Notion przez własną integrację tylko do odczytu), bez konektorów konta. Bez zmian w kodzie.
  zostało: Nie sprawdzono na żywo listy konektorów w sesji „Rozwój panelu” (polecenie `claude mcp list` poza uprawnieniami zadania); lista łączonych konektorów pochodzi z pliku konfiguracji konta. Sesja „Rozwój panelu” ma dziś dostęp do wszystkich konektorów konta (m.in. Atlassian, Canva) bez ograniczeń.
  następne: Wyłącz konektory konta w sesji „Rozwój panelu” | kto: claude | kiedy: 2026-11-28
- [x] Zaproponuj konektory dla każdego projektu | kto: claude | gdzie: chmura | kiedy: 2026-11-24 | czas: 30
  cel: lista projekt → konektor → do czego → odczyt albo zapis, na podstawie kart, zadań i rozmów
  gotowe gdy: lista w szczegółach zadania, gotowa do zatwierdzenia przez właściciela
  Propozycja (stan 2026-11-24, z kart i zadań 11 projektów z rejestru panelu). Zasada: konektor dostaje projekt, którego agent regularnie potrzebuje plików albo danych spoza repozytorium i nie da się ich tanio wkleić; domyślnie tylko odczyt, jeden folder. Repozytoria z GitHuba agenci mają już w folderze projektu, to nie jest konektor.
  Dostaje konektor:
  - Shield & Silent – marketing → Google Drive, jeden folder ze zdjęciami prac i filmami studia → scenariusze i montaż 3 filmów tygodniowo, zdjęcia do wizytówki Google, landing page i reklam → odczyt. Kto: agenci zadań i rozmów tego projektu oraz studio filmów; raport PM i Asystent nie. W folderze tylko materiały do publikacji, bez danych klientów studia (karta: nazwiska i telefony poza repozytorium).
  Bez konektora:
  - Detailing Kępno → brak. Faza 0 nie ruszyła (start i budżet do ustalenia 28.11); na razie same teksty. Gdy ruszy wizytówka „Shield & Silent Kępno”, wystarczy ten sam folder Drive tylko do odczytu.
  - Opisarnia → brak. Stripe, Sentry i baza produkcyjna mają dane klientów i pieniądze; liczby do pomiaru podajesz z zapytania w metryki.md, statystyki LinkedIn, Facebooka i Instagrama ręcznie (Twoja odpowiedź 12 w karcie). Publikacja i wysyłka są po Twojej stronie.
  - Oprogramowani (company-audits) → brak. Karta: dane klientów nie trafiają do usług zewnętrznych; materiały leżą w repozytorium.
  - Oprogramowani – strona WWW → brak. Wszystko w repozytorium, podgląd w zakładce Strona.
  - NaulikApp → brak. Play Console nie ma gotowego konektora, a publikacja w sklepie wymaga Twojej zgody; kroki w Play Console robisz sam.
  - Warsztat → brak. Wstrzymany; serwer MCP w repozytorium to część produktu, nie konektor konta.
  - Szukanie auta → brak. Poziom swobody 1, logowanie na portale tylko za zgodą.
  - Testy zlecone (TestNow) → brak. Praca na Macu, agent nie działa na koncie platformy.
  - Analiza surowicy płodowej → brak. Źródła są w `zalaczniki/`; pisma wysyłasz sam.
  - Infrastruktura → brak. Konfigurację serwera, DNS i kont zmieniasz tylko Ty albo agent po zgodzie.
  - Raport PM, Asystent, sesja „Rozwój panelu” → brak; czytają pliki projektów.
  Rozważone i odrzucone:
  - Google Ads i Meta Ads (Shield & Silent, Kępno), odczyt wyników na kontrole 6.12, 3.01 i 28.01: dostęp do interfejsu Google Ads wymaga osobnego wniosku do Google, konto należy do studia, a kontrole są trzy. Taniej: wklejasz liczby albo eksport CSV przy kontroli. Wrócić po kontroli 1, jeśli przepisywanie okaże się uciążliwe.
  - Notion: żaden projekt go dziś nie używa; w księdze jest planowany dopiero jako lustro do odczytu w etapie 3.
  - Gmail, kalendarz, LinkedIn, Facebook z zapisem: wysyłka i publikacja wymagają Twojej zgody w każdej karcie, więc agent przygotowuje szkice w plikach.
  - Konektory konta (Canva, Atlassian, PubMed): żaden projekt ich nie potrzebuje; zostają wyłączone.
  Uwaga do logowania Drive: zgoda Google obejmuje odczyt całego dysku konta, a do jednego folderu zawęża ją dopiero serwer. Jeśli folder leży na koncie studia, najlepiej zalogować konto, które widzi tylko ten folder.
  wynik: Lista powyżej: jeden konektor, Google Drive tylko do odczytu dla Shield & Silent – marketing (jeden folder ze zdjęciami i filmami); pozostałe 10 projektów oraz raport PM, Asystent i „Rozwój panelu” bez konektorów, z powodem przy każdym. Zatwierdzasz ją w zadaniu „Zatwierdź konektory projektów”. Bez zmian w kodzie, bez gałęzi i commita (zmiana tylko w ZADANIA.md).
  zostało: Nie czytano rozmów z folderów `rozmowy/` projektów (leżą poza kopią dostępną agentowi); lista opiera się na kartach i zadaniach. Nie wiadomo, na czyim koncie Google leży folder Shield & Silent (Twoim czy studia).
- [ ] Zatwierdź konektory projektów | kto: ty | kiedy: 2026-11-26 | czas: 10 | po: Zaproponuj konektory dla każdego projektu
  cel: decyzja właściciela, które projekty i jacy agenci dostają który konektor
  materiał: ZADANIA.md
  pyta: Lista zatwierdzona (tak albo co zmienić); Link do folderu Shield & Silent na Google Drive
- [ ] Dodaj pole konektorów do karty i panelu | kto: claude | gdzie: chmura | kiedy: 2026-11-28 | po: Sprawdź konektory konta Claude w agentach na serwerze, Zatwierdź konektory projektów
  cel: agent dostaje tylko konektory wpisane w karcie projektu; panel pokazuje je przy projekcie
  gotowe gdy: STANDARD.md opisuje pole; panel pokazuje konektory projektu; test: agent w projekcie bez wpisu nie ma dostępu do konektora
  materiał: DECYZJE.md
- [ ] Zaloguj Google dla Drive Shield & Silent | kto: ty | kiedy: 2026-11-30 | czas: 5 | po: Dodaj pole konektorów do karty i panelu
  cel: dostęp tylko do odczytu do folderu Shield & Silent; link do logowania przygotowuje Claude, logujesz się sam na stronie Google
- [ ] Podłącz Drive Shield & Silent tylko do odczytu | kto: claude | gdzie: chmura | kiedy: 2026-12-01 | po: Zaloguj Google dla Drive Shield & Silent
  cel: zdjęcia i filmy z Drive dostępne w panelu i dla agentów Shield & Silent bez pełnej kopii na serwerze
  gotowe gdy: pliki z Drive widoczne w Media projektu; agent projektu je czyta; pamięć podręczna do 1 GB; kopia nocna i Zasoby nie liczą plików z Drive

## Do rozplanowania
- [ ] Uzupełnić pliki projektu według standardu | kto: claude
  cel: Uzupełnić według standard/STANDARD.md: Zadania (6 braków), README (brak pliku), Architektura (brak pliku), Uruchomienie (brak pliku), Instrukcje agentów (brak pliku). Niczego nie nadpisywać; na końcu python3 standard/projekt.py sprawdz bez braków w tym projekcie.
