# Instalacja

Panel projektów uruchamia Claude Code i Codex na Twoim logowaniu (subskrypcja), bez kluczy API.
Ustawienia: `dashboard/panel.env` (wzór w `dashboard/panel.env.przyklad`). Zasady uruchamiania: `dashboard/AGENCI.md`.

## Co gdzie działa

| Urządzenie | Rola | Co instalujesz |
|---|---|---|
| PC z Windows, włączony stale | węzeł główny: Automat, raport PM, dostęp z telefonu | Python 3, Git, Claude Code, Tailscale; opcjonalnie Codex |
| Mac | praca przy komputerze, zadania `gdzie: mac`, kalendarz | Claude Code; opcjonalnie Codex |
| iPhone | panel PC w przeglądarce, powiadomienia, terminy w Kalendarzu | Tailscale; opcjonalnie ntfy |

Każdy komputer ma własny panel, własną listę projektów i własne rekordy uruchomień (`uruchomienia/`).
Pliki projektów przenosi git danego projektu.

## Logowanie narzędzi

Loginy, hasła i tokeny wpisujesz samodzielnie. Panel i agenci ich nie znają i o nie nie pytają.

Claude Code, na każdym komputerze:

```bash
claude auth login
```

Komunikat `command not found: claude` na Macu oznacza, że folderu `~/.local/bin` nie ma w PATH terminala.
Użyj pełnej ścieżki (panel pokazuje ją we wskazówce logowania w widoku Agenci):

```bash
~/.local/bin/claude auth login
```

PC bez przeglądarki pod ręką: wygeneruj token i wpisz go do `dashboard/panel.env` jako `CLAUDE_CODE_OAUTH_TOKEN=…`.

```bash
claude setup-token
```

Codex (zadania `kto: codex` i grafiki do postów):

```bash
codex login
```

### Codex do grafik

Grafiki do postów (edytor posta → „Grafika (Codex)”) robi Codex na Twoim planie ChatGPT (bez klucza API; plan Free
nie ma generowania obrazów). Na serwerze instalacja jednym poleceniem, potem logowanie:

```bash
sudo bash /home/panel/IntegrateSystems/uruchom/serwer/zainstaluj-codex.sh
```

Logowanie: w ChatGPT włącz w ustawieniach bezpieczeństwa logowanie kodem urządzenia, potem w panelu kliknij
„Zaloguj Codex” w edytorze posta i wpisz pokazany kod na stronie OpenAI. Bez panelu:
`sudo -u agent -H /home/agent/.local/bin/codex login --device-auth`. Na Macu: `codex login`.
Szczegóły: `dashboard/AGENCI.md`, sekcja „Grafiki (Codex)”.

Sprawdzenie: widok Agenci → „Test połączenia”. Panel usuwa klucze API ze środowiska agentów,
więc praca idzie na limit subskrypcji. Koszt w panelu to równowartość, nie opłata.

### Podgląd stron WWW

Zakładka „Strona” (projekty z polem karty `- strona: site`) buduje stronę na serwerze (Node.js) i daje agentowi
zrzuty ekranu (Playwright agenta w `/home/agent/narzedzia/pw`). Instalacja i próba jednym poleceniem:

```bash
sudo bash /home/panel/IntegrateSystems/uruchom/serwer/zainstaluj-podglad.sh
```

Szczegóły: `dashboard/AGENCI.md`, sekcja „Podgląd strony”.

## PC z Windows

1. Zainstaluj Python 3 z python.org (zaznacz „Add python.exe to PATH”) i Git for Windows.
2. Zainstaluj Claude Code (PowerShell):

   ```powershell
   irm https://claude.ai/install.ps1 | iex
   ```

3. Skopiuj folder IntegrateSystems na PC. Pliku `dashboard/panel.env` i folderu `uruchomienia/` nie przenoś między komputerami.
4. Zaloguj narzędzia (sekcja wyżej).
5. Skopiuj `dashboard\panel.env.przyklad` jako `dashboard\panel.env`. Do pracy tylko na tym komputerze nie trzeba nic zmieniać.
6. Próba ręczna, w folderze IntegrateSystems (zatrzymanie: Ctrl+C):

   ```powershell
   uruchom\start.cmd
   ```

   Otwórz `http://localhost:4801/`, widok Agenci, „Test połączenia”.
7. Stałe uruchamianie (start przy logowaniu, wznowienie po awarii, bez uprawnień administratora):

   ```powershell
   powershell -ExecutionPolicy Bypass -File uruchom\windows-zainstaluj.ps1
   ```

8. Ustaw w Windows, żeby komputer nie usypiał. Po restarcie panel startuje dopiero po zalogowaniu na konto.

Po każdej zmianie `panel.env` uruchom skrypt z punktu 7 ponownie. Wyłączenie:

```powershell
powershell -ExecutionPolicy Bypass -File uruchom\windows-odinstaluj.ps1
```

## Mac

1. Zainstaluj Claude Code:

   ```bash
   curl -fsSL https://claude.ai/install.sh | bash
   ```

2. Zaloguj narzędzia (sekcja wyżej).
3. Próba ręczna, w folderze IntegrateSystems (zatrzymanie: Ctrl+C):

   ```bash
   ./uruchom/start.sh
   ```

4. Stałe uruchamianie (start przy logowaniu, wznowienie po awarii):

   ```bash
   ./uruchom/mac-zainstaluj.sh
   ```

Po każdej zmianie `panel.env` uruchom skrypt z punktu 4 ponownie. Wyłączenie:

```bash
./uruchom/mac-odinstaluj.sh
```

## iPhone

Telefon łączy się z panelem na PC przez Tailscale. Bez hasła panel odrzuca połączenia spoza komputera.

1. Zainstaluj Tailscale na PC i na iPhonie, zaloguj oba na to samo konto.
2. Wygeneruj hasło panelu (na PC):

   ```powershell
   python -c "import secrets; print(secrets.token_urlsafe(24))"
   ```

3. W `dashboard\panel.env` na PC ustaw (nazwę PC pokazuje aplikacja Tailscale):

   ```
   PANEL_HOST=0.0.0.0
   PANEL_ALLOWED_HOSTS=nazwa-pc,nazwa-pc.twoja-siec.ts.net
   PANEL_TOKEN=hasło z punktu 2
   ```

4. Uruchom ponownie `uruchom\windows-zainstaluj.ps1`. Gdy zapora Windows zapyta o dostęp dla Pythona, zezwól.
5. Na iPhonie otwórz `http://nazwa-pc:4801/wejscie` i wpisz hasło. Stronę możesz dodać do ekranu początkowego.
6. Terminy w Kalendarzu iOS: w panelu, Serwer → Połączenie z kalendarzem, skopiuj adres subskrypcji (`/terminy.ics?k=…`),
   potem Ustawienia → Aplikacje → Kalendarz → Konta kalendarzy → Dodaj konto → Inne → Dodaj subskrybowany kalendarz.

Adres subskrypcji zawiera klucz: traktuj go jak hasło. Zmiana `PANEL_TOKEN` unieważnia zalogowane urządzenia i ten adres.
iPhone widzi panel tylko przy włączonym Tailscale.

## Projekty

- Z panelu: „+” przy nagłówku Projekty w menu (ścieżka folderu; opcjonalnie założenie brakujących plików standardu).
- Z terminala, nowy projekt:

  ```bash
  python3 standard/projekt.py nowy ~/Projekty/nazwa --nazwa "Nazwa" --rejestruj
  ```

- Z terminala, istniejący folder:

  ```bash
  python3 standard/projekt.py dodaj ~/Projekty/nazwa
  ```

Projekt dodajesz na każdym komputerze, na którym mają nad nim pracować agenci. Pole `gdzie:` w zadaniu wskazuje komputer.
Między komputerami pliki przenosi git: repozytorium projektu sklonowane na obu. `PANEL_GIT_PULL=1` sprawia,
że przed uruchomieniem zadania panel robi `git pull --ff-only` (tylko gdy repozytorium jest czyste).
Panel nie wysyła zmian (`git push`); robisz to samodzielnie.

## Google Drive

Serwer → Google Drive → „Połącz Google Drive”: logowanie Google (wybór konta), dostęp tylko do odczytu
(`drive.readonly`), jedno połączenie na całe konto. Folder dla projektu albo części wybierasz potem z listy
w „Kod i pliki”; panel montuje go w `szkice/<karta>/media/drive` (usługa `drive@<projekt>`).

Bez dodatkowej konfiguracji panel używa klienta OAuth wbudowanego w rclone. Google odsyła wtedy przeglądarkę na
`http://127.0.0.1:53682/…`, a tej strony na telefonie i Macu nie da się otworzyć: adres z paska wklejasz raz na
konto (pole w panelu, „Wklej ze schowka” albo wklejenie w pole od razu łączy).

### Własny klient OAuth (bez wklejania adresu)

1. https://console.cloud.google.com → nowy projekt (np. „Panel”) → „APIs & Services” → włącz **Google Drive API**.
2. „Google Auth Platform” (ekran zgody): typ **External** (konto prywatne) albo **Internal** (Google Workspace:
   bez limitu 7 dni i bez weryfikacji). Nazwa aplikacji i e-mail. Zakres (Data access):
   `https://www.googleapis.com/auth/drive.readonly`. W „Audience” dodaj swoje konta Google jako użytkowników testowych.
3. „Clients” → „Create client” → **Web application** → „Authorized redirect URIs”:
   `https://2-29-181-133.sslip.io/api/drive/powrot`. Skopiuj Client ID i Client secret.
4. Na serwerze (jako root) zapisz plik, którego panel nie wypisuje:

   ```bash
   sudo install -d -m 700 -o panel -g panel /home/panel/.config/integrate
   sudo -u panel nano /home/panel/.config/integrate/google-oauth.json
   sudo chmod 600 /home/panel/.config/integrate/google-oauth.json
   ```

   Zawartość:

   ```json
   {"client_id": "….apps.googleusercontent.com", "client_secret": "…",
    "redirect_uri": "https://2-29-181-133.sslip.io/api/drive/powrot"}
   ```

   Inna ścieżka: `PANEL_GOOGLE_OAUTH` w środowisku panelu. Restart panelu nie jest potrzebny.
5. Serwer → Google Drive → „Połącz Google Drive” → wybór konta → Google wraca do panelu: „Google Drive połączony”.

Tryb **Testing** (External, aplikacja nieopublikowana): Google unieważnia dostęp po 7 dniach, więc konto trzeba
łączyć co tydzień. Żeby tego uniknąć: „Audience” → „Publish app” (In production). `drive.readonly` to zakres
zastrzeżony: bez weryfikacji Google pokazuje przy logowaniu ostrzeżenie „Google hasn't verified this app”
(„Advanced” → „Go to …”), limit 100 użytkowników; dla własnych kont to wystarcza. Konta połączone wcześniej przez
klienta rclone działają dalej (bez limitu 7 dni). Usunięcie pliku przywraca łączenie z wklejaniem adresu.

## Uprawnienia agentów

| Narzędzie | Tryb | Co wolno bez pytania |
|---|---|---|
| Claude Code | `acceptEdits` | edycja plików w folderze projektu; polecenia powłoki tylko z listy projektu |
| Codex | `workspace-write` | zapis w folderze projektu, bez sieci |

Trybu z pominięciem uprawnień panel nie używa. Polecenia powłoki dla Claude dopuszczasz w `.claude/settings.json` projektu:

```json
{
  "permissions": {
    "allow": [
      "Bash(npm test:*)",
      "Bash(npm run build:*)",
      "Bash(git status:*)",
      "Bash(git diff:*)",
      "Bash(git add:*)",
      "Bash(git commit:*)"
    ],
    "deny": [
      "Bash(git push:*)"
    ]
  }
}
```

Polecenie spoza listy jest odrzucane (nikt nie potwierdza w trakcie); odmowy widać w szczegółach uruchomienia.
Operacje wymagające zgody (wdrożenie, publikacja, wysyłka, płatność) agent przygotowuje, oznacza `wymaga: zgoda` i zatrzymuje się.

## Automat

Wyłączony domyślnie; włączasz go w widoku Agenci. Co minutę bierze zadania, które spełniają wszystkie warunki:

| Warunek | Wartość |
|---|---|
| stan | `[ ]` |
| `kto` | `claude` albo `codex` |
| `gdzie` | nazwa tego komputera (`pc`, `mac`) |
| `kiedy` | ustawione, dziś albo wcześniej |
| `pora` | `noc`: 22:00–6:00, `dzień`: 6:00–22:00, bez pola: zawsze |
| `wymaga` | brak `wymaga: zgoda` |
| dziś | zadanie nie było dziś uruchamiane |

Przykład zadania na noc:

```
- [ ] Testy modułu importu | kto: claude | gdzie: pc | kiedy: 2026-11-12 | pora: noc
```

Naraz pracuje najwyżej `PANEL_AGENTS_MAX` uruchomień. Po limicie subskrypcji Automat czeka do odnowienia.
Raz dziennie po godzinie `PANEL_PM_HOUR` Automat uruchamia raport PM, jeśli nie ma jeszcze `raporty/<dziś>.md`.
Skończone zadanie ma stan `[x]` albo `[~]` z `wymaga: odbiór` (czeka na Twój przegląd).

## Powiadomienia

W `panel.env` ustaw adres tematu ntfy, a na iPhonie zasubskrybuj ten temat w aplikacji ntfy:

```
PANEL_NTFY_URL=https://ntfy.sh/losowa-nazwa-tematu
```

Tytuł zadania i wynik uruchomienia trafiają wtedy na wybrany serwer ntfy. Temat na ntfy.sh czyta każdy, kto zna jego nazwę:
użyj losowej nazwy albo własnego serwera i nie wpisuj w tytułach zadań danych poufnych.

## Gdy coś nie działa

| Objaw | Co zrobić |
|---|---|
| stan `login` | na tym komputerze `claude auth login` (albo nowy token z `claude setup-token` w `panel.env`), potem „Test połączenia” |
| stan `limit` | limit subskrypcji; panel pokazuje godzinę odnowienia, Automat wznawia sam |
| stan `error` | szczegóły uruchomienia w widoku Agenci; surowy zapis w `uruchomienia/<id>.log` |
| stan `timeout` | podziel zadanie albo zwiększ `PANEL_AGENT_TIMEOUT` |
| „Brak polecenia claude” | ustaw pełną ścieżkę w `PANEL_CLAUDE` (dla Codex: `PANEL_CODEX`) |
| port zajęty (`Address already in use`) | działa druga kopia panelu: zatrzymaj ją (Ctrl+C) albo ustaw inny `PANEL_PORT` |
| telefon dostaje 403 | brak `PANEL_TOKEN` albo nazwy hosta w `PANEL_ALLOWED_HOSTS` |
| telefon się nie łączy | Tailscale włączony na obu urządzeniach; zapora Windows przepuszcza `python.exe` i `pythonw.exe` |
| odmowa przy wpisywaniu hasła (429) | za dużo prób: odczekaj minutę |
| ostrzeżenie o kluczu API w panelu | w ustawieniach Claude Code jest klucz; usuń go, żeby praca szła na subskrypcję |
| Mac pyta o dostęp do folderu dla `python3` | projekt leży w Dokumentach albo na Biurku: zezwól albo przenieś projekt |

| Co | Gdzie |
|---|---|
| log panelu, Mac | `~/Library/Logs/panel-projektow.log` |
| log panelu, Windows | `%LOCALAPPDATA%\PanelProjektow\panel.log` |
| rekordy i surowe zapisy uruchomień | `uruchomienia/` |
| stan Automatu, znacznik logowania, limit | `uruchomienia/stan.json` |
| notatki PM | `raporty/` |
