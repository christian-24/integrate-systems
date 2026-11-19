# Uruchamianie agentów z panelu

Panel uruchamia Claude Code i Codex na tym komputerze, na Twoim logowaniu (subskrypcja), bez kluczy API.
Ten plik jest kontraktem między serwerem (`server.py`, `agents.py`), stroną (`panel.html`) i skryptami w `../uruchom/`.

## Węzły

Ten sam serwer działa na każdym komputerze. Każdy węzeł uruchamia tylko własne procesy i ma własny rejestr projektów.

| Węzeł | `PANEL_MACHINE` | Rola |
|---|---|---|
| serwer (po D13) | `cloud` (`gdzie: chmura`) | główny: Automat, raport PM, dostęp z telefonu; węzeł domyślny |
| PC z Windows | `pc` | zadania `gdzie: pc` |
| Mac | `mac` | praca przy komputerze, zadania `gdzie: mac` |

Węzeł domyślny bierze w Automacie także zadania bez pola `gdzie:`. Domyślnie jest nim każdy węzeł poza Makiem;
`PANEL_DEFAULT_NODE=1` albo `0` ustawia to wprost.

Pliki projektów przenosi między komputerami git danego projektu.

## Ustawienia

Zmienne środowiska albo plik `dashboard/panel.env` (wiersze `NAZWA=wartość`, `#` to komentarz). Zmienna środowiska wygrywa z plikiem.

| Zmienna | Domyślnie | Znaczenie |
|---|---|---|
| `PANEL_HOST`, `PANEL_PORT` | `127.0.0.1`, `4801` | adres serwera |
| `PANEL_ALLOWED_HOSTS` | brak | dodatkowe nazwy hosta (np. nazwa w Tailscale) |
| `PANEL_TOKEN` | brak | hasło panelu dla połączeń spoza tego komputera |
| `PANEL_MACHINE` | `mac` na macOS, inaczej `pc` | nazwa węzła |
| `PANEL_DEFAULT_NODE` | `1` poza Makiem | `1`: Automat bierze też zadania bez `gdzie:` |
| `PANEL_RUNS_DIR` | `../uruchomienia` | rekordy uruchomień i `stan.json` (czyta je też `standard/pm.py`) |
| `PANEL_ZDROWIE_STAN` | `/home/panel/.zdrowie-stan` | wynik kontroli zdrowia serwera (`server.checks` w `/api/data`) |
| `PANEL_KOPIA_STAN` | `/home/panel/kopie/ostatnia.json` | stan ostatniej kopii (`server.backupAt`, `server.backupOff`) |
| `PANEL_CLAUDE`, `PANEL_CODEX` | z `PATH` (Claude także `~/.local/bin/claude`) | ścieżki poleceń |
| `PANEL_AGENTS_MAX` | `2` | ile uruchomień naraz |
| `PANEL_AGENT_TIMEOUT` | `3600` | limit czasu jednego uruchomienia, sekundy |
| `PANEL_AGENT_MODEL`, `PANEL_PM_MODEL` | model domyślny CLI | model dla zadań i dla raportu PM |
| `PANEL_PM_HOUR` | `7` | godzina dziennego raportu PM w Automacie |
| `PANEL_GIT_PULL` | `0` | `1`: przed uruchomieniem `git pull --ff-only`, gdy repozytorium jest czyste |
| `PANEL_NTFY_URL` | brak | adres tematu ntfy; powiadomienie po zakończeniu uruchomienia i gdy Claude wymaga logowania |
| `CLAUDE_CODE_OAUTH_TOKEN` | brak | token z `claude setup-token` dla komputera bez przeglądarki |

## Dostęp

- Połączenie z tego komputera (loopback): bez hasła.
- Połączenie z innego urządzenia: wymagane `PANEL_TOKEN`. Bez ustawionego hasła serwer odmawia (403).
  Strona `GET /wejscie` ma jedno pole; `POST /wejscie` (formularz, pole `haslo`) ustawia ciasteczko
  `panel_sesja` (HttpOnly, SameSite=Strict, Max-Age 30 dni) i przekierowuje na `/`. Wartość to `chwila.podpis`:
  chwila logowania i HMAC z hasła, losowego klucza sesji (`sessionKey` w `stan.json`) i tej chwili, nie samo hasło.
  Sesja starsza niż 30 dni nie działa. `POST /api/session/logout-all` losuje nowy klucz sesji: wszystkie
  dotychczasowe ciasteczka, także bieżące, przestają działać.
  Gdy żądanie przyszło przez HTTPS (pośrednik, np. Caddy, ustawia `X-Forwarded-Proto: https`), ciasteczko ma też `Secure`.
  Żądanie bez ciasteczka: strony → 303 na `/wejscie`, `/api/*` → 401 `{"ok":false,"error":"Wymagane hasło."}`.
  Błędne hasło: odpowiedź po 1 s, najwyżej 10 prób na minutę (potem 429).
- `GET /terminy.ics?k=<klucz>`: kalendarz do subskrypcji bez ciasteczka; klucz jest pochodną hasła
  (inny niż ciasteczko) i jest częścią `icsPath` w `/api/data`.
- Ochrona hosta, źródła (`Origin`) i typu `application/json` zostaje jak dotąd.

## Uruchomienie

Rodzaje (`kind`): `task` (jedno zadanie z `ZADANIA.md`), `pm` (raport PM), `check` (test połączenia),
`plan` (plan dnia: PM bez narzędzi, tryb uprawnień `default`, tylko `Read`; pola `ask`, `plan` {agents, you, note}, `accepted`).

Stany (`state`): `queued` w kolejce, `running` pracuje, `done` zakończone, `error` błąd, `login` wymaga logowania,
`limit` limit subskrypcji, `stopped` zatrzymane, `timeout` przekroczony czas.

Rekord uruchomienia (JSON):

```
id            "20261110-213455-a3f1"
kind          task | pm | check | plan
tool          claude | codex
state         jak wyżej
auto          true, gdy uruchomił Automat
machine       mac | pc
project       id projektu albo ""
projectName   nazwa projektu albo ""
taskId        "projekt|plik|wiersz" z chwili startu albo ""
file, title   plik i tytuł zadania (dla pm i check: title to "Raport PM", "Test połączenia")
queuedAt, startedAt, endedAt   czas lokalny "RRRR-MM-DDTHH:MM:SS" albo null
durationMs    liczba albo null
activity      ostatnia czynność, jeden wiersz (w trakcie pracy)
steps         ostatnie najwyżej 30 czynności: [{"t":"21:35:02","text":"Edit: src/api.py"}]
result        końcowa odpowiedź agenta, najwyżej 4000 znaków
error         krótki opis błędu, najwyżej 300 znaków
turns, tokensIn, tokensOut, costUsd   liczby (costUsd to równowartość, przy subskrypcji nie jest pobierana)
model         nazwa modelu
keySource     "none" oznacza subskrypcję; inna wartość to ostrzeżenie w panelu
denials       odmowy uprawnień, najwyżej 10 krótkich wierszy
```

Pliki: `../uruchomienia/<id>.json` (rekord), `../uruchomienia/<id>.log` (surowy strumień),
`../uruchomienia/stan.json` (Automat, znacznik logowania, limit; `since`: od kiedy zadanie jest w toku albo czeka
na odbiór, `{"projekt|plik|tytuł": {"s": "doing|review", "d": "RRRR-MM-DD"}}`; `sessionKey`: klucz sesji panelu;
`rytmDone`: publikacje, dla których powstało już zadanie wpisania wyniku). Serwer trzyma 200 ostatnich rekordów.
Po restarcie serwera uruchomienia `queued` i `running` dostają stan `stopped`.

### Polecenia

Prompt idzie przez stdin (bez problemów z cudzysłowami na Windows). Katalog roboczy: folder projektu.

| Rodzaj | Polecenie |
|---|---|
| task, Claude | `claude -p --output-format stream-json --verbose --permission-mode acceptEdits [--model M] [--add-dir <folder karty>] --allowedTools "<lista>"` |
| pm | w folderze IntegrateSystems: jak wyżej oraz `--agent pm --allowedTools "Bash(python3 standard/pm.py:*),Bash(python standard/pm.py:*),Read,Write,Edit,Glob,Grep"` |
| check | `claude -p --output-format stream-json --verbose --model haiku`, prompt „Odpowiedz jednym słowem: ok” |
| task, Codex | `codex exec --json --sandbox workspace-write --skip-git-repo-check -C <folder> -` |

Lista dla zadań Claude (`TASK_TOOLS` w `agents.py`), bez push i bez sieci:
`Bash(git status:*)`, `Bash(git diff:*)`, `Bash(git log:*)`, `Bash(git switch -c:*)`, `Bash(git checkout -b:*)`,
`Bash(git add:*)`, `Bash(git commit:*)`, `Bash(python3 -m pytest:*)`, `Bash(pytest:*)`, `Bash(python3 -m unittest:*)`,
`Read`, `Edit`, `Write`, `Glob`, `Grep`.

Panel nigdy nie używa `--dangerously-skip-permissions`, `bypassPermissions` ani odpowiedników w Codex.
Polecenia powłoki, na które agent ma zgodę, ustala `.claude/settings.json` projektu; odmowy widać w rekordzie (`denials`).

Środowisko procesu: usunięte `ANTHROPIC_*`, `OPENAI_API_KEY`, `PANEL_TOKEN`, `PANEL_NTFY_URL` oraz `CLAUDE*`
poza `CLAUDE_CODE_OAUTH_TOKEN` i `CLAUDE_CONFIG_DIR`. Dzięki temu praca idzie na logowanie subskrypcji.

### Zadanie

Przy starcie serwer zmienia wiersz zadania: stan `[~]`, `kto:` narzędzie, `gdzie:` ten węzeł.
Agent dostaje prompt: jedno zadanie (plik, wiersz, tytuł, etap) i jego szczegóły (cel, gotowe gdy, materiały,
kroki, notatki, wynik i „zostało” z poprzedniej pracy; format w `standard/STANDARD.md`), zakaz zmiany innych zadań
i terminów, zakaz zmiany tytułu zadania i dopisywania do niego raportu, zakaz działań nieodwracalnych i wychodzących
na zewnątrz. Na koniec agent odhacza wykonane kroki, dopisuje pod swoim wierszem wcięte wiersze `wynik:`, `decyzja:`
(gdy coś do zatwierdzenia) i `zostało:` (gdy coś zostało), może dopisać jeden wiersz
`następne: Tytuł | kto: … | kiedy: RRRR-MM-DD` (propozycja; nowych zadań nie zakłada), pytania do właściciela dopisuje
do sekcji „Pytania do właściciela” w `KARTA.md`, z wierszem `   termin: RRRR-MM-DD`, gdy to potrzebne (poza tym karty
nie zmienia), zmienia stan własnego wiersza (`[x]`; `[~]` + `wymaga: odbiór`; gdy „gotowe gdy” nie jest spełnione
albo nie może iść dalej: `[!]` + `blokada:`, bez `wymaga: odbiór`) i odpowiada: Zrobione, Sprawdzone, Zostało.
Gdy pod zadaniem jest `poprawka:` (uwagi właściciela przy „Do poprawy”), prompt ją podaje, a agent poprawia pracę według niej.
Pracę w repozytorium git agent zapisuje na nowej gałęzi `agent/RRRR-MM-DD-krotka-nazwa` jednym lokalnym commitem
(bez push, bez plików KARTA.md, ZADANIA.md, DECYZJE.md) i podaje gałąź i skrót commita w `wynik:`.

Po zakończeniu:
- stan inny niż `done`, a wiersz dalej `[~]`: serwer przywraca `[ ]`;
- stan `done`, a wiersz dalej `[~]` bez pola `wymaga`: serwer dopisuje `wymaga: odbiór`.

### Kiedy zadania nie da się uruchomić (`runBlock`)

Pierwszy pasujący powód; pusty tekst oznacza, że można uruchomić.

| Warunek | `runBlock` |
|---|---|
| projekty przykładowe | `Projekty przykładowe` |
| publikacja w kampanii | `Publikację wykonujesz samodzielnie` |
| stan zrobione | `Zrobione` |
| `kto: ty` | `Zadanie po Twojej stronie` |
| `zgoda` w polu `wymaga` (także `wymaga: odbiór, zgoda`) | `Czeka na Twoją zgodę` |
| niezrobiony poprzednik z `po:` (także fragment bez pasującego wiersza) | `Czeka na: Tytuł poprzednika, …` |
| brak polecenia (`claude`; dla `kto: codex` polecenie `codex`) | `Brak polecenia claude` / `Brak polecenia codex` |
| uruchomienie w kolejce albo w toku | `W toku` |

Zadanie bez pola `kto` uruchamia Claude.

### Automat

Wyłączony domyślnie; stan w `stan.json`. Co 60 s bierze zadania, które spełniają wszystko:
`runBlock` pusty (w tym poprzednicy z `po:` zrobieni), stan `[ ]`, `kto: claude` albo `kto: codex`, `gdzie:` równe
temu węzłowi albo brak `gdzie:` na węźle domyślnym, `kiedy:` ustawione i nie później niż dziś (przeszła data też),
`pora` zgodna (noc 22:00–6:00, dzień 6:00–22:00, brak pola: zawsze), brak dzisiejszego uruchomienia tego zadania,
brak aktywnego limitu i znacznika logowania. Raz dziennie po `PANEL_PM_HOUR` uruchamia raport PM, gdy nie ma `raporty/<dziś>.md`.

Rytm marketingu, przy każdym przebiegu, dla projektów z rejestru z plikiem `kampanie/staly-rytm.md` (poza stanem
wstrzymany i backlog), zadania trafiają do „Do rozplanowania”:
- dotychczasowy rytm: „Przygotować post na RRRR-MM-DD (stały rytm)” przed kolejnym terminem z ustawień rytmu;
- publikacja niezrobiona z `kiedy` od dziś do 2 dni naprzód, bez folderu `posty/<kiedy>-*` (obok `KARTA.md`):
  „Przygotować post na <kiedy>: <tytuł publikacji>” (`kto: claude`, `gdzie:` ten węzeł, `kiedy:` dziś,
  `materiał: kampanie/staly-rytm.md`), gdy takiego zadania jeszcze nie ma;
- publikacja `[x]` z `kiedy` dawniej niż 2 dni (48 h) i bez wiersza `wynik:`: „Wpisz wynik publikacji <tytuł>”
  (`kto: ty`, `kiedy:` dziś, `czas: 3`). Tylko raz: klucz publikacji trafia do `rytmDone` w `stan.json`, więc usunięte
  zadanie nie wraca.

### Powiadomienia (ntfy)

Przy `PANEL_NTFY_URL` serwer wysyła wiadomość po każdym uruchomieniu (poza testem połączenia i zatrzymaniem):
`Tytuł zadania (Projekt): stan`. W projektach klienckich (`client: true`, także bez pola `- klient:` w karcie)
bez tytułu zadania: `Zadanie w projekcie <alias albo nazwa>: stan`. Gdy Claude zaczyna wymagać logowania
(`needsLogin` po uruchomieniu albo odczyt narzędzi: polecenie jest, ale niezalogowane), jedna wiadomość
„Claude wymaga logowania…”; kolejna dopiero po zalogowaniu i ponownej utracie logowania.

### Plan dnia

`plan_candidates`: otwarte zadania z polami `id`, `project`, `kind`, `title`, `goal` (cel ze szczegółów), `minutes`
(pole `czas`), `stage`, `stageDue`, `date`, `executor`, `state`, `needsYou`, `agent`, `why`, oraz publikacje z kampanii
z `zgoda` w polu `wymaga` (`kind: publikacja`, `agent: false`) jako sprawy dla właściciela.

### Logowanie i limit

- Błąd logowania (401, wygasły token): stan `login`, `needsLogin: true` do pierwszego udanego uruchomienia.
  Naprawa po stronie właściciela: `claude auth login` (albo `claude setup-token` i `CLAUDE_CODE_OAUTH_TOKEN` w `panel.env`).
  `tools.<narzędzie>.loginCmd` to to samo polecenie z pełną ścieżką znalezionego narzędzia (powłoka nie zawsze ma je w PATH);
  strona pokazuje je we wskazówce logowania, a bez tego pola pokazuje `claude auth login`.
- Limit subskrypcji (429, komunikat o limicie, zdarzenie `rate_limit_event` ze statusem odmowy): stan `limit`,
  `limitUntil` = czas odnowienia, a gdy nieznany, godzina od teraz. Automat czeka do tej chwili.

## `/api/data`

Każde zadanie w `tasks` ma dodatkowo: `runId` (id uruchomienia w kolejce albo w toku, inaczej `""`), `runBlock`,
`stateSince`, `stalled`, `reviewOverdue`, `ownerNeeds`, a z odczytu plików `detail`, `needs`, `after` i `waitingFor`
(opis w `README.md`, „Szczegóły zadania i następny krok”). Poza tym `/api/data` ma `youToday`, `youWeek`, `youLater`
i `server` (README, „Stan serwera”).

```
"agents": {
  "machine": "mac",
  "tools": {
    "claude": {"found": true, "version": "2.1.156", "loggedIn": true, "subscription": "max", "loginCmd": "~/.local/bin/claude auth login"},
    "codex":  {"found": false, "version": "", "loggedIn": false, "subscription": "", "loginCmd": "codex login"}
  },
  "needsLogin": false,
  "limitUntil": null,
  "automat": false,
  "maxParallel": 2,
  "canRunTasks": true,
  "today": {"runs": 3, "tokens": 41200, "costUsd": 0.82},
  "runs": [ rekordy, najnowsze pierwsze, najwyżej 40 ]
}
```

`canRunTasks` jest `false` przy projektach przykładowych; raport PM i test połączenia działają zawsze.
Dane przykładowe dla `/podglad` i eksportu: `agenci-przyklad.json` (ten sam kształt; czasy względne `"-35m"`, `"+90m"`
liczone od chwili otwarcia strony).

## Żądania

`POST`, `Content-Type: application/json`, odpowiedź `{"ok": bool, "error": str}` (+ `id` nowego uruchomienia).

| Żądanie | Treść | Działanie |
|---|---|---|
| `/api/agent/run` | `{"id": taskId, "title": tytuł}` | uruchamia zadanie; 409, gdy wiersz się zmienił albo `runBlock` niepusty |
| `/api/task/detail` | `{"id": taskId, "title": tytuł, "key": klucz, "value": tekst}` | jeden klucz szczegółów: `cel`, `gotowe gdy`, `materiał`, `wynik`, `decyzja`, `zostało`, `poprawka`, `następne`; `krok` z value `{"index": n, "done": bool}`; 400 przy złej wartości, 409, gdy wiersz się zmienił |
| `/api/session/logout-all` | `{}` | unieważnia wszystkie sesje panelu (nowy klucz sesji) |
| `/api/agent/pm` | `{}` | raport PM; 409, gdy już trwa |
| `/api/agent/check` | `{"tool": "claude"}` | test połączenia |
| `/api/agent/stop` | `{"id": runId}` | zatrzymuje albo zdejmuje z kolejki |
| `/api/agent/automat` | `{"enabled": bool}` | włącza i wyłącza Automat |
| `/api/project/add` | `{"path": folder, "name"?: nazwa, "files": bool}` | dopisuje istniejący folder do rejestru; `files: true` zakłada brakujące pliki standardu (niczego nie nadpisuje) |
| `/api/project/remove` | `{"id": projekt}` | usuwa z rejestru; pliki zostają |

## Testy

`python3 -m unittest discover -s dashboard/testy` — uruchamianie na atrapie polecenia `claude` (bez sieci i bez limitu).
