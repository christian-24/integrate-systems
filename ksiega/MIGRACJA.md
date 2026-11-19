# Migracja z PC do chmury (D13)

Cel: wszystko, co dziś istnieje tylko na PC, ma bezpieczne miejsce, zanim PC pójdzie na sprzedaż. Potem serwer w chmurze przejmuje pracę.
Źródło listy: audyt PC z 2026-11-14 (`szkice/AUDYT-PC-2026-11-14.md`).

## Etapy

| # | Etap | Warunek zakończenia |
|---|---|---|
| 1 | Zabezpieczenie danych z PC (PC włączony, w sieci) | każdy wiersz tabeli poniżej ma stan „gotowe”; archiwum na Macu sprawdzone (liczba plików, rozmiar) |
| 2 | Serwer w chmurze: panel z logowaniem przez HTTPS, agenci, repozytoria, nocna kopia | panel otwiera się z Maca i z iPhone'a spoza domu; jedno zadanie agenta wykonane na serwerze |
| 3 | Useme i Windows: pilnowanie zleceń przez e-maile na serwerze, rozszerzenia w Chrome na Macu, build Warsztatu w GitHub Actions, próba Windows w Azure | nowe zlecenie z Useme widoczne w panelu; zielony build Warsztatu |
| 4 | Dzień próbny bez PC | 24 h bez włączania PC i bez brakujących danych → PC do resetu i sprzedaży |

## Dane do zabrania z PC

Kanał (2026-11-16): Claude uruchomiony na samym PC według `MIGRACJA-INSTRUKCJA-PC.md`; kopia na dysk zewnętrzny podłączony do PC przez USB, do folderu `Migracja-PC-2026-11` (bez usuwania czegokolwiek na dysku). Mac nie widzi PC w obecnej sieci, a zapora PC wpuszcza SSH tylko ze starego adresu Maca.
Sekretów (pliki `.env`, klucze) nie wysyłamy do repozytoriów: zostają w archiwum na Macu, a do przeniesienia do menedżera haseł przez właściciela.

| Co | Gdzie na PC | Dokąd | Wymaga zgody | Stan |
|---|---|---|---|---|
| Opisarnia: gałąź `feat/pokaz-opisarnia` (778 zmian, PoC „Pokaz”) | `Desktop\generator-opisow-mebli` | commit „wip: pokaz” na tej gałęzi i push do prywatnego repo | tak (commit i push) | |
| Opisarnia: 5 worktree Claude (`.claude/worktrees`) | jw. | sprawdzić niewypchnięte commity; wypchnąć albo do archiwum | tak | |
| Oprogramowani: CompanyAudits (70 zmian, nieśledzone pliki) | `Desktop\CompanyAudits` | commit i push do `company-audits` (bez danych osobowych firm w jawnej formie: repo prywatne) | tak | |
| Oprogramowani: strona (4 zmiany) | `Desktop\oprogramowani-onepager` | commit i push | tak | |
| Oprogramowani: LeadyV2, LeadEngine (bez git) | `Desktop\Reaserch` | nowe prywatne repo albo folder w `company-audits` | tak (nowe repo) | |
| Asystent zleceń, część Useme i Facebook (bez git) | `C:\Users\Guest\Zlecenia`, `Documents\ChatGPT\Zlecenia` | nowe prywatne repo `asystent-useme` | tak (nowe repo) | |
| Szukanie auta, rozszerzenie OLX i OTOMOTO (bez git) | jw. | osobne prywatne repo albo tylko archiwum | decyzja | |
| NaulikApp: gałęzie `fix/rc1-nagrania`, `marketing/kampania-rc1` | `Desktop\NaulikApp` | sprawdzić, czy są na origin; jeśli nie, push | tak | |
| Warsztat | `Desktop\Warsztat` | już na GitHubie (sprawdzone 14.11); sprawdzić tylko niewypchnięte | — | |
| Wtyczki Claude: `social-publisher`, `agent-quest` | `Plugins`, `claude-mods` | prywatne repo `claude-wtyczki` | tak (nowe repo) | |
| Pozostałe własne repozytoria ze zmianami (migracja-claude-code-kit 65, AdvanceStockBotTrading 99, GymInteligentApp 16, odys_frontend, UnDrown i inne) | `source\repos`, `Desktop`, `AndroidStudioProjects` | archiwum na Macu w całości; push tylko na życzenie | decyzja | |
| Projekty bez git (sejm-radar, mountain-stories, meble-ai-agents, CostLab, OrderChecker, uigen i inne) | `Desktop`, `Downloads`, `source\repos` | archiwum na Macu | — | |
| Repozytoria pracodawcy (klient 2) | `source\repos`, `Documents\GitHub` | nie do chmury (D10): dysk zewnętrzny albo usunięcie | decyzja | |
| Rozmowy Claude Code (1012 plików) i sesje Codex (38) | `C:\Users\Guest\.claude`, `.codex` | archiwum na Macu; w jednej rozmowie jest klucz Mistral do unieważnienia | — | |
| Audyt PC i kopie robocze z WSL | `/home/claude/audyt-pc` | archiwum na Macu | — | |
| Dane Dockera (33 GB) | `E:\Docker\DockerDesktopWSL` | sprawdzić, czy jest tam coś poza lokalną bazą deweloperską; zwykle do pominięcia | decyzja | |
| Profil Chrome: rozszerzenia „Opisarnia – zbieranie opisów”, asystenci | Chrome na PC | kod rozszerzeń w repozytoriach; instalacja w Chrome na Macu | — | |
| Pliki osobiste (Pulpit, Dokumenty, Pobrane, Obrazy) | profil Guest i `dominik` | archiwum albo dysk zewnętrzny; profil `dominik` tylko z Twojego konta | decyzja | |

## Przed sprzedażą PC

- Usunąć z Harmonogramu zadań autostart asystenta, wyłączyć sshd, portproxy i reguły zapory (albo pełny reset).
- Wylogować konta (Microsoft, Google, GitHub, Claude, Codex), unieważnić klucze SSH tego komputera na GitHubie.
- Reset Windows „Usuń wszystko” z czyszczeniem dysków (C: i E:).

## Decyzje właściciela przed etapem 1

1. Repozytoria pracodawcy: dysk zewnętrzny czy usunięcie?
2. Szukanie auta: osobne repo czy tylko archiwum?
3. Pozostałe własne repozytoria: tylko archiwum czy także push na GitHub?
4. Dane Dockera na E: i pliki osobiste: co zabrać?

## Serwer: kopie i kontrola zdrowia

Pliki w `uruchom/serwer/`. Instalacja (jako ops, po pobraniu zmian na serwer przez zapis kart):

```
sudo bash /home/panel/IntegrateSystems/uruchom/serwer/zainstaluj-kopie-i-zdrowie.sh
```

Instalator najpierw sprawdza, że `uruchom/serwer` w kopii roboczej na serwerze jest taki sam jak na GitHubie (`git fetch` jako panel, potem `git diff --quiet origin/main -- uruchom/serwer`); przy różnicy albo plikach spoza gita przerywa i nic nie instaluje. Potem kopiuje skrypty i jednostki do `/usr/local/lib/integrate` (właściciel root, 755) i stamtąd instaluje `kopia`, `zdrowie`, `zapis-kart`, `odtworz` w `/usr/local/bin` oraz jednostki w `/etc/systemd/system`, włącza timery i robi pierwszy przebieg kopii i kontroli zdrowia. Zmiana w kopii roboczej (np. przez agenta) nie zmienia więc tego, co działa, dopóki właściciel nie uruchomi instalatora. `zainstaluj-zapis-kart.sh` działa tak samo dla samego zapisu kart. Ustawienia opcjonalne: `/etc/integrate/serwer.env` (wzór `serwer.env.przyklad`), powiadomienia przez `PANEL_NTFY_URL` z `/etc/integrate/panel.env`.

| Co | Kiedy | Co robi | Powiadomienie |
|---|---|---|---|
| Kopia (`kopia.timer`) | codziennie 03:30 czasu polskiego | `/home/panel/kopie/RRRR-MM-DD.tar.gz`: `dane/` (bazy SQLite jako spójna kopia w `sqlite/`), `uruchomienia/`, `historia/`, zmienione i nieśledzone pliki projektów z `git status`, niewypchnięte commity jako `git/<repo>.bundle`; zostaje 14 najnowszych. Po kopii `/home/panel/kopie/ostatnia.json`: `{"at", "size", "files", "off", "offAt"}` (panel pokazuje go w widoku serwera) | tylko przy błędzie |
| Wysyłka poza serwer | po kopii, gdy ustawiony `KOPIA_CEL` | szyfrowanie (gpg albo age), potem `rclone` albo `scp`; opis niżej | przy błędzie |
| Kontrola zdrowia (`zdrowie.timer`) | co 10 min | panel (`/api/data` lokalnie → 200), Useme (`/api/health`), wolne miejsce ≥ 15%, Claude zalogowany, kopia młodsza niż 36 h, kopia poza serwerem młodsza niż 26 h (gdy ustawiony `KOPIA_CEL`), ostatni zapis kart; stan w `/home/panel/.zdrowie-stan` (`nazwa=ok\|zle\|brak`, dalej `kopia_wiek_h=` i `kopia_poza=tak\|nie`) | przy zmianie na zły i z powrotem na dobry; codziennie od 8:00 jedno podsumowanie „Serwer: wszystko w normie” albo lista problemów; bez danych klientów |
| Zapis kart (`zapis-kart.timer`) | co 15 min | commit i push tylko zmian w `szkice/` i `raporty/` (osobny indeks, więc nic innego nie trafia do commita); inne zmiany zostają na dysku z ostrzeżeniem w dzienniku; pliki wyglądające na sekrety i bazy (`.env*`, `*.env`, `*.key`, `*.pem`, `credentials*`, `*.sqlite`, `*.db`) pomija; działa tylko na gałęzi `main`; niewypchnięte commity spoza `szkice/` i `raporty/` wstrzymują push | przez kontrolę zdrowia |

Sprawdzenie: `systemctl list-timers kopia.timer zdrowie.timer zapis-kart.timer`, `journalctl -u kopia -n 5`, `journalctl -u zdrowie -n 8`, `cat /home/panel/kopie/ostatnia.json`.
Kopia na tym samym dysku nie chroni przed utratą serwera: do tego Backups w Hetznerze (cały serwer, 7 ostatnich dni) i kopia poza serwerem (niżej). Zewnętrzny monitoring adresu panelu (UptimeRobot) zgłasza awarię całego serwera, której kontrola zdrowia na tym serwerze nie wyśle.

## Kopia poza serwerem (Storage Box)

Archiwum zawiera dane klientów, więc poza serwer idzie zaszyfrowane. Ustawienia w `/etc/integrate/serwer.env` (wzór `uruchom/serwer/serwer.env.przyklad`).

| Ustawienie | Znaczenie |
|---|---|
| `KOPIA_CEL=rclone:<zdalny>:<folder>` | zalecane: rclone ze zdalnym sftp do Storage Box; usuwa w celu archiwa starsze niż `KOPIA_CEL_DNI` (domyślnie 30) |
| `KOPIA_CEL=scp:<host>:<folder>` | scp kluczem panelu (`BatchMode`); bez usuwania starych archiwów w celu |
| `KOPIA_HASLO_PLIK=<plik>` | gpg symetryczny AES256; plik z hasłem: właściciel panel, prawa 600 (inaczej kopia kończy się błędem) |
| `KOPIA_AGE_ODBIORCY=<plik>` | zamiast gpg: age z kluczem publicznym; klucz prywatny tylko u właściciela (menedżer haseł), na serwerze go nie ma |

Bez szyfrowania `scp` jest odrzucany; `rclone` bez szyfrowania skryptem tylko do zdalnego typu `crypt`.
W celu leżą pliki `RRRR-MM-DD.tar.gz.gpg` (albo `.age`). Hasło gpg (albo klucz prywatny age) musi być też w menedżerze haseł: bez niego kopii nie da się odczytać.

Konfiguracja (jako ops; `uXXXXXX` to użytkownik Storage Box z Hetzner Robot, port SSH 23):

```
sudo apt install -y rclone gnupg
sudo -u panel ssh-keygen -t ed25519 -N '' -f /home/panel/.ssh/kopia -C kopia-serwera
sudo -u panel sh -c 'cat /home/panel/.ssh/kopia.pub | ssh -p 23 uXXXXXX@uXXXXXX.your-storagebox.de install-ssh-key'
sudo -u panel rclone config create storagebox sftp host=uXXXXXX.your-storagebox.de user=uXXXXXX port=23 key_file=/home/panel/.ssh/kopia
sudo -u panel rclone mkdir storagebox:integrate
sudo -u panel sh -c 'umask 077; openssl rand -base64 32 > /home/panel/.kopia-haslo'   # skopiuj hasło do menedżera haseł
sudo nano /etc/integrate/serwer.env    # KOPIA_CEL=rclone:storagebox:integrate, KOPIA_HASLO_PLIK=/home/panel/.kopia-haslo
sudo systemctl start kopia && journalctl -u kopia -n 6 -o cat
sudo -u panel rclone ls storagebox:integrate
```

Wynik: w dzienniku „zaszyfrowano (gpg AES256)” i „wysłano poza serwer (rclone)”, w `ostatnia.json` `"off": true`, w kontroli zdrowia `kopia-poza: ok`.

## Odtworzenie serwera

Cel: nowy serwer działa jak stary po utracie dysku albo całego serwera. Najpierw Backups Hetznera (przywrócenie całego obrazu w konsoli, kilka minut); procedura niżej, gdy obrazu nie ma.
Czas pełnej procedury: **do uzupełnienia po próbie** (data próby: —, czas: —). Czas samego `odtworz.sh` wypisuje skrypt.

Próba bez ryzyka (na działającym serwerze, nic nie nadpisuje):

```
sudo -u panel rclone copy storagebox:integrate/RRRR-MM-DD.tar.gz.gpg /tmp/proba/
sudo -u panel odtworz --sprawdz --haslo-plik /home/panel/.kopia-haslo /tmp/proba/RRRR-MM-DD.tar.gz.gpg
sudo -u panel odtworz --haslo-plik /home/panel/.kopia-haslo /tmp/proba/RRRR-MM-DD.tar.gz.gpg /tmp/proba/dane
rm -rf /tmp/proba
```

`odtworz.sh --sprawdz` sprawdza archiwum (odszyfrowanie, `gzip -t`, lista `tar`, brak ścieżek bezwzględnych i `..`, obecność `kopia-info.txt`) i wypisuje zawartość. Bez `--sprawdz` rozpakowuje do pustego katalogu, wstawia spójne kopie baz z `sqlite/` na miejsce i wypisuje kroki ręczne. Niczego poza wskazanym katalogiem nie nadpisuje.

Na czystym serwerze (Ubuntu 24.04 Arm, Hetzner CAX11), jako root, potem ops:

1. Użytkownicy `ops` (sudo) i `panel`, SSH tylko kluczem, zapora (22, 80, 443), automatyczne aktualizacje, swap.
2. Pakiety: `apt install -y python3 git sqlite3 caddy gnupg rclone age`; Claude Code dla panel (`~/.local/bin/claude`).
3. Klucz SSH panelu dodany w GitHubie; `sudo -u panel git clone <integrate-systems> /home/panel/IntegrateSystems`.
4. `/etc/integrate/panel.env` i `/etc/integrate/serwer.env` (root, 600) według wzorów; sekrety z menedżera haseł.
5. `panel.service` i `Caddyfile` z `uruchom/serwer/konfiguracja/` (wzory, porównane wcześniej z działającym serwerem); `systemctl enable --now panel`, `systemctl reload caddy`.
6. Dostęp do Storage Box (klucz panelu jak w sekcji wyżej), pobranie ostatniego archiwum, `odtworz` do pustego katalogu, kroki ręczne wypisane przez skrypt (dane, `uruchomienia/`, `historia/`, repozytoria projektów sklonowane w `~/projekty` i pliki z kopii, pakiety commitów, `chown`).
7. Useme: jednostka `useme.service` z wyniku `zbierz-konfiguracje.sh`, `systemctl enable --now useme`.
8. `sudo -u panel claude auth login` (albo logowanie z panelu).
9. Instalatory: `zainstaluj-zapis-kart.sh`, `zainstaluj-kopie-i-zdrowie.sh`.
10. Adres: nowy IP → nowy adres sslip.io w `Caddyfile` i `PANEL_ALLOWED_HOSTS`, UptimeRobot i zakładki na iPhonie.
11. Sprawdzenie: `sudo -u panel zdrowie` bez „zle”, panel z iPhone'a, jedno zadanie agenta.

## Pliki konfiguracji serwera

Wzory bez haseł: `uruchom/serwer/konfiguracja/`. Bieżące pliki z serwera (wartości sekretów ukryte) zbiera `sudo bash uruchom/serwer/zbierz-konfiguracje.sh`; wynik porównaj z wzorami i popraw wzory w repozytorium po każdej zmianie na serwerze.

| Plik na serwerze | Wzór w repozytorium | Sekrety |
|---|---|---|
| `/etc/caddy/Caddyfile` | `konfiguracja/Caddyfile` | brak (logowanie w panelu) |
| `/etc/systemd/system/panel.service` | `konfiguracja/panel.service` | brak |
| `/etc/systemd/system/useme.service` | brak wzoru: z `zbierz-konfiguracje.sh` | sprawdzić |
| `/etc/systemd/system/{kopia,zdrowie,zapis-kart}.{service,timer}` | `uruchom/serwer/*.service`, `*.timer` | brak |
| `/etc/integrate/panel.env` | `konfiguracja/panel.env.przyklad` | `PANEL_TOKEN`, `PANEL_NTFY_URL` w menedżerze haseł |
| `/etc/integrate/serwer.env` | `uruchom/serwer/serwer.env.przyklad` | adres celu kopii; hasło kopii w osobnym pliku |
| `/home/panel/.kopia-haslo` | — | hasło kopii, w menedżerze haseł |
| `/home/panel/.ssh/` (GitHub, Storage Box), `/home/panel/.config/rclone/rclone.conf` | — | klucze tworzone od nowa na nowym serwerze |
| `/usr/local/bin/{kopia,zdrowie,zapis-kart,odtworz}`, `/usr/local/lib/integrate/` | `uruchom/serwer/*.sh` | brak (instaluje instalator) |
