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
| `PANEL_AGENTS_MAX` | `2` | ile uruchomień naraz, gdy w panelu nie ma ustawienia (Agenci → „Naraz”, `parallel` w `stan.json` wygrywa) |
| `PANEL_PRZEBIEG` | `1` | `0`: zadanie i raport PM bez pośrednika `przebieg.py` (proces z potokiem do panelu, ginie z panelem) |
| `PANEL_WDROZENIE_DIR` | `~/dane/wdrozenie` | stan wdrożenia (`stan.json`); stan `waiting` wstrzymuje start nowych zadań |
| `PANEL_PRZEGLADARKA_MCP` | `/home/agent/narzedzia/mcp/node_modules/@playwright/mcp/cli.js` | Playwright MCP dla agenta strony; brak pliku albo `0`: bez przeglądarki |
| `PANEL_PRZEGLADARKA_CHROME` | `/opt/ms-playwright/chromium-*/…/chrome` | przeglądarka dla Playwright MCP |
| `PANEL_NAPRAWY` | `1` | `0`: bez jednorazowych napraw po starcie (`naprawy.py`, tylko węzeł `cloud`) |
| `PANEL_AGENT_TIMEOUT` | `3600` | limit czasu jednego uruchomienia, sekundy |
| `PANEL_AGENT_MODEL`, `PANEL_PM_MODEL` | model domyślny CLI | model dla zadań i dla raportu PM |
| `PANEL_PM_HOUR` | `7` | godzina dziennego raportu PM w Automacie |
| `PANEL_GIT_PULL` | `0` | `1`: przed uruchomieniem `git pull --ff-only`, gdy repozytorium jest czyste |
| `PANEL_AGENT_WORKTREE` | `1` | `0`: zadanie w repozytorium git bez gałęzi uruchomienia (praca w folderze projektu) |
| `PANEL_AGENT_USER` | brak | użytkownik systemu dla agentów; polecenie idzie przez `sudo -n -u <użytkownik> --` |
| `PANEL_LOKALNY_KLUCZ_PLIK` | brak | plik klucza zapisu dla żądań z tego komputera (nagłówek `X-Panel-Klucz`) |
| `PANEL_DZIEN_MIN` | `120` | dzienna pojemność właściciela w minutach (`dayMinutes` w `/api/data`) |
| `PANEL_ASYSTENT_MODEL` | `sonnet` | model obu rozmów: Asystent i Rozmowa w projekcie |
| `PANEL_ASYSTENT_INTERNET` | `1` | `0` zabiera asystentowi WebSearch i WebFetch (karty news); domyślnie włączone, tylko odczyt |
| `PANEL_ASYSTENT_KARTY` | `<katalog uruchomień>/czat/asystent-karty.json` | biblioteka kart asystenta i układ płótna |
| `PANEL_ASYSTENT_BEZCZYNNOSC` | `1800` | po tylu sekundach bez wiadomości stała sesja asystenta kończy pracę |
| `PANEL_GLOS_PYTHON` | brak | interpreter venv z faster-whisper (`uruchom/serwer/zainstaluj-glos.sh`); bez niego panel chowa „Mów” |
| `PANEL_GLOS_MODELE`, `PANEL_GLOS_MODEL` | brak, `small` | katalog pobranych modeli i nazwa modelu Whisper |
| `PANEL_GLOS_BEZCZYNNOSC` | `600` | po tylu sekundach bez nagrania pracownik mowy kończy pracę (zwalnia pamięć) |
| `PANEL_GRAFIKA` | `codex` | grafiki do postów: `codex` (Codex na subskrypcji ChatGPT) albo `wylaczone` (sekcja „Grafiki (Codex)”) |
| `PANEL_GRAFIKA_TIMEOUT` | `900` | limit czasu jednego zlecenia grafiki, sekundy |
| `PANEL_CODEX_HOME` | `~<PANEL_AGENT_USER>/.codex` albo `CODEX_HOME`, `~/.codex` | katalog danych Codex (obrazy z `generated_images/<wątek>/`) |
| `PANEL_NTFY_URL` | brak | adres tematu ntfy; powiadomienie po zakończeniu uruchomienia i gdy Claude wymaga logowania |
| `CLAUDE_CODE_OAUTH_TOKEN` | brak | token z `claude setup-token` dla komputera bez przeglądarki |

## Dostęp

- Połączenie z tego komputera (loopback): odczyty (`GET`: strona, `/api/data`, `/api/post*`, `/api/plik`,
  `/api/agent/diff`, `/terminy.ics`) bez hasła. Zapis (`POST`) bez hasła tylko wtedy, gdy ochrona zapisu jest wyłączona.
- Ochrona zapisu z tego komputera działa, gdy ustawione jest `PANEL_LOKALNY_KLUCZ_PLIK` albo `PANEL_AGENT_USER`,
  albo węzeł to serwer (`PANEL_MACHINE=cloud`). Wtedy `POST` z loopback wymaga sesji (logowanie na `/wejscie`
  działa też z loopback) albo nagłówka `X-Panel-Klucz` równego zawartości pliku z `PANEL_LOKALNY_KLUCZ_PLIK`;
  inaczej 401 `{"ok":false,"error":"Zapis z tego komputera wymaga zalogowania albo klucza lokalnego."}`.
  Plik klucza: co najmniej 16 znaków, prawa `600` (właściciel `panel`) albo `640` z grupą, do której agent nie należy
  (`root:panel 640`). Plik z prawami dla innych albo dla grupy użytkownika `PANEL_AGENT_USER` jest odrzucany, bo mógłby
  go przeczytać agent. Klucz działa tylko z loopback, nie przez pośrednika.
  Na Macu i PC bez tych ustawień zapis z tego komputera działa jak dotąd (agent i tak działa jako właściciel).
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

Zadanie w repozytorium git (gałąź uruchomienia) ma dodatkowo; inne rekordy tych pól nie mają:

```
branch        "agent/2026-11-19-krotka-nazwa"
base          gałąź bazowa z chwili startu ("main"); przy odłączonym HEAD skrót commita
baseCommit    commit, od którego powstała gałąź
changes       [{"path": "notatki/analiza.md", "added": 3, "removed": 0}]   git diff --numstat baseCommit...branch,
              ścieżki względem katalogu głównego repozytorium, najwyżej 200; plik binarny: 0, 0 i "binary": true
commits       liczba commitów gałęzi ponad baseCommit
fix           treść `poprawka:` zadania w chwili startu; Automat uruchamia zadanie drugi raz tego samego dnia tylko przy nowej poprawce
merged, mergeCommit   po /api/agent/merge: czas scalenia i commit scalenia
```

Pliki: `../uruchomienia/<id>.json` (rekord), `../uruchomienia/<id>.log` (surowy strumień),
`../uruchomienia/stan.json` (Automat, znacznik logowania, limit; `since`: od kiedy zadanie jest w toku albo czeka
na odbiór, `{"projekt|plik|tytuł": {"s": "doing|review", "d": "RRRR-MM-DD"}}`; `marks`: od kiedy zadanie jest
zrobione albo zablokowane, `{"projekt|plik|tytuł": {"s": "done|blocked", "d": "RRRR-MM-DD"}}`, tylko znane daty,
zrobione starsze niż 90 dni usuwane; `sessionKey`: klucz sesji panelu;
`rytmDone`: publikacje, dla których powstało już zadanie wpisania wyniku; `parallel`: ile uruchomień naraz;
`naprawy`: wykonane jednorazowe naprawy). Serwer trzyma 200 ostatnich rekordów.
Po restarcie serwera uruchomienia `queued` dostają stan `stopped`; `running` niżej, „Restart panelu”.

### Restart panelu (wdrożenie) nie przerywa agentów

- Zadanie i raport PM idą przez pośrednika `dashboard/przebieg.py` (własna sesja procesów, bez potoków do panelu):
  wyjście agenta pisze do `<id>.log`, wejście bierze z `<id>.wej` (panel dopisuje wiersze JSON), kod końca zapisuje
  w `<id>.koniec`. Dane robocze uruchomienia (folder, katalog roboczy, gałąź, części, podgląd) są w `<id>.przebieg`.
  Rekord ma `runner` (`pid` pośrednika) i `logPos` (ile bajtów przebiegu panel już przeczytał); w `/api/data` tych pól nie ma.
- Panel kończący pracę (SIGTERM) nie zatrzymuje tych uruchomień i nie zamyka ich rekordów. Po starcie: pośrednik żyje
  albo zapisał koniec → panel czyta przebieg dalej od `logPos` (krok „Panel uruchomił się ponownie; agent pracował
  dalej”), limit czasu liczy się od startu uruchomienia.
- Uruchomienie przerwane mimo to (pośrednik zniknął, agent zabity sygnałem bez zdarzenia `result`): zadanie z pracą
  zatwierdzoną na gałęzi uruchomienia (commity od `startCommit`, bez commita panelu z końca) kończy się jak zwykle
  (stan `done`, `recovered: "commit"`, `wymaga: odbiór` albo scalenie i podgląd strony); bez commita: stan `stopped`
  (`recovered: "restart"`), panel zatwierdza resztę zmian na gałęzi, dopisuje do `poprawka:` „Poprzednie uruchomienie
  przerwał restart panelu…” i uruchamia zadanie ponownie od tej gałęzi (`recoveredFrom`, `recoverN`, najwyżej 2 razy z rzędu).
- Usługa: `uruchom/serwer/panel-agenci.conf` (`KillMode=process`, instaluje `zainstaluj-rozwoj.sh`): systemd zabija przy
  restarcie tylko proces panelu. Bez tej nakładki restart zabija agentów, a panel po starcie dokańcza zadania jak wyżej.
- `wdroz-panel` po testach czeka, aż nie będzie uruchomień `running` zadań i raportu PM (najwyżej `WDROZ_CZEKAJ_AGENCI`,
  1800 s), ze stanem wdrożenia `waiting`; panel w tym czasie nie startuje nowych zadań z kolejki (`agents.deployHold`).

### Ile naraz

Najwyżej `maxParallel` uruchomień naraz (domyślnie 2, Agenci → „Naraz” 1–4, `POST /api/agent/rownolegle {"value": n}`),
zadania najwyżej jedno na projekt (część projektu liczy się z projektem głównym, pole rekordu `family`); kolejne zadanie
tego projektu czeka w kolejce, Automat bierze je w następnym obiegu. Bezpiecznik zużycia liczy sumę: przy n pracujących
uruchomieniach Claude próg to n × `PANEL_RUN_BUDGET_PROC`, mierzony od startu najdłużej pracującego, i to ono jest
zatrzymywane. Próg Automatu (`PANEL_AUTOMAT_DO_PROC`) dotyczy zużycia całego okna 5 h.

### Polecenia

Prompt idzie przez stdin (bez problemów z cudzysłowami na Windows). Zadanie Claude dostaje go jako pierwszą wiadomość
`--input-format stream-json` i stdin zostaje otwarty do zdarzenia `result` (niżej, „Praca na żywo”). Katalog roboczy: folder projektu, a dla zadania
w repozytorium git katalog roboczy gałęzi uruchomienia (niżej). Przy `PANEL_AGENT_USER` każde polecenie agenta
(zadanie, raport PM, plan, test połączenia, odczyt stanu logowania, logowanie przez panel) ma przedrostek
`["sudo", "-n", "-u", PANEL_AGENT_USER, "--"]`; bez zmiennej jak dotąd. Test połączenia i plan dnia działają wtedy
w katalogu tymczasowym systemu (agent nie musi mieć dostępu do `uruchomienia/`).

| Rodzaj | Polecenie |
|---|---|
| task, Claude | `claude -p --output-format stream-json --verbose --permission-mode acceptEdits [--model M] --input-format stream-json [--add-dir <folder karty>] --allowedTools "<lista>"`; w gałęzi uruchomienia `--add-dir` dla folderów `KARTA.md`, `ZADANIA.md`, `DECYZJE.md` i pliku zadania |
| pm | w folderze IntegrateSystems: jak wyżej oraz `--agent pm --allowedTools "Bash(python3 standard/pm.py:*),Bash(python standard/pm.py:*),Read,Write,Edit,Glob,Grep"` |
| check | `claude -p --output-format stream-json --verbose --model haiku`, prompt „Odpowiedz jednym słowem: ok” |
| task, Codex | `codex exec --json --sandbox workspace-write --skip-git-repo-check -C <folder> -`; w gałęzi uruchomienia `-C <katalog roboczy> --add-dir <folder> … -` |

Lista dla zadań Claude (`TASK_TOOLS` w `agents.py`), bez push i bez sieci:
`Bash(git status:*)`, `Bash(git diff:*)`, `Bash(git log:*)`, `Bash(git switch -c:*)`, `Bash(git checkout -b:*)`,
`Bash(git add:*)`, `Bash(git commit:*)`, `Bash(python3 -m pytest:*)`, `Bash(pytest:*)`, `Bash(python3 -m unittest:*)`,
`Read`, `Edit`, `Write`, `Glob`, `Grep`, a gdy render jest dostępny także `Bash(<python> <panel>/dashboard/html-do-pdf.py:*)`
(niżej). Ogólnego `Bash` zadania nie dostają.

#### Render HTML do PDF i PNG

`dashboard/html-do-pdf.py <plik.html> <wynik.pdf> [<wynik.png>] [--strona A4|90x50mm|1080x1350px] [--szerokosc px]
[--skala 1–3] [--ekran]`: wizytówka, ulotka, grafika z HTML. Tylko plik lokalny (adresy http odrzucone), zasoby
z sieci blokowane (Chromium bez sieci, liczba zablokowanych w wyniku), wynik tylko w folderze bieżącym albo w folderze
pliku HTML, najwyżej 4 pliki; PDF z tłem i rozmiarem z CSS `@page` albo `--strona`. Python z Playwright
(`render_command` w `agents.py`): `PANEL_RENDER` (całe polecenie) → `PANEL_RENDER_PYTHON` → na serwerze
`/home/agent/narzedzia/pw/bin/python` (jak zrzuty strony) → `~/narzedzia/pw`, `~/narzedzia/film` (Mac). Bez takiego
Pythona (i na Windows) polecenie zadania mówi, że render jest niedostępny i agent wpisuje to w `zostało:`; Python bez
Playwright kończy skrypt kodem 3 z czytelnym komunikatem. Skrypt leży w repozytorium panelu, którego agent nie zmienia
(na serwerze `/home/panel/…`), więc reguła `Bash(<python> <skrypt>:*)` nie daje mu innych poleceń. Codex dostaje tę samą
wskazówkę w poleceniu (ma własną piaskownicę).

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
(gdy coś do zatwierdzenia) i `zostało:` (gdy coś zostało; tylko sprawy ważne dla właściciela, bez technicznych:
miejsca pliku, commita, gałęzi), może dopisać jeden wiersz
`następne: Tytuł | kto: … | kiedy: RRRR-MM-DD` (propozycja; nowych zadań nie zakłada), pytania do właściciela dopisuje
do sekcji „Pytania do właściciela” w `KARTA.md` (tylko sprawy, których nie rozstrzygnie nikt poza właścicielem:
pieniądze, dane prawne i firmowe, działania nieodwracalne albo na zewnątrz, zakres i terminy, rzeczy fizyczne, fakty
znane tylko jemu; najwyżej jedno otwarte pytanie na projekt; resztę agent rozstrzyga sam i zapisuje w `DECYZJE.md`
z `- Kto: agent`; `wymaga: odbiór` tylko dla pracy wychodzącej na zewnątrz, z `decyzja:` albo z kodem do scalenia), z wierszem `   termin: RRRR-MM-DD`, gdy to potrzebne (poza tym karty
nie zmienia); przy pytaniu z wyborem dopisuje 2–3 wiersze `   opcja: …` (krótko, wzajemnie wykluczające się; panel
pokazuje je jako odpowiedzi do wyboru), rekomendację dopisuje jako `   propozycja: …` (przy opcjach: jedna z nich), a gdy jej przyjęcie zmienia zadania, zawsze z wierszami
`   skutek: <operacja>` (`po: … → …`, `kiedy: RRRR-MM-DD → …`, `stan: zrobione|wstrzymane → …`, `nowe: <wiersz zadania>`;
panel wykonuje je po przyjęciu propozycji, README „Pytania do właściciela”). Wiersza `gotowe gdy:` agent nie zmienia
i nie łagodzi (bez „albo w zostało:”); niespełniony warunek opisuje w `zostało:` i kończy stanem `[!]`. Agent zmienia stan własnego wiersza (`[x]`; `[~]` + `wymaga: odbiór`; gdy „gotowe gdy” nie jest spełnione
albo nie może iść dalej: `[!]` + `blokada:`, bez `wymaga: odbiór`) i odpowiada: Zrobione, Sprawdzone, Zostało.
Gdy pod zadaniem jest `poprawka:` (uwagi właściciela przy „Do poprawy”, ze strony odbioru albo polecenie z „Wyślij
i wykonaj” w Rozmowie w projekcie), prompt ją podaje razem ze znacznikami (wiersze `- znacznik N (plik, położenie): uwaga`,
ścieżka obrazu albo filmu względem folderu projektu), a agent wykonuje polecenie, poprawia pracę według niej i dopisuje
`zmiany:` (2–3 zmiany rozdzielone „; ”, przy każdej uwadze i znaczniku „zrobione” albo powód).
Folder bez repozytorium git (albo `PANEL_AGENT_WORKTREE=0`): pracę w repozytorium agent zapisuje na nowej gałęzi
`agent/RRRR-MM-DD-krotka-nazwa` jednym lokalnym commitem (bez push, bez plików KARTA.md, ZADANIA.md, DECYZJE.md)
i podaje gałąź i skrót commita w `wynik:`. W repozytorium git gałąź zakłada panel (niżej).

Po zakończeniu:
- stan inny niż `done`, a wiersz dalej `[~]`: serwer przywraca `[ ]`;
- stan `done`, a wiersz dalej `[~]` bez pola `wymaga`: serwer dopisuje `wymaga: odbiór`;
- gałąź uruchomienia: commit, `changes`, usunięcie katalogu roboczego (niżej), przy każdym stanie końcowym;
- stan `done`: ścieżki plików z `wynik:` zadania (rozszerzenia md, txt, csv, json, html, svg, png, jpg, pdf, yaml),
  które istnieją w folderze projektu, w folderze karty albo na gałęzi uruchomienia, panel dopisuje jako
  `materiał: <ścieżka>` (względem folderu projektu) do otwartych zadań tego samego pliku, które mają `po:` na tym
  zadaniu; ścieżki, które zadanie już ma w `materiał:`, pomija; najwyżej 10 ścieżek.
- stan `done`: nowa wersja wyniku (niżej, „Odbiór pracy”), gdy zadanie ma `wynik:`, `zostało:` albo `decyzja:`.

### Gałąź uruchomienia (git worktree)

Gdy folder projektu leży w repozytorium git z co najmniej jednym commitem (i folder jest w nim śledzony), a
repozytorium to nie jest sam folder IntegrateSystems:

1. Przy starcie panel (nie agent) zakłada gałąź `agent/<RRRR-MM-DD>-<krótka-nazwa>` od bieżącego `HEAD`
   (zajęta nazwa dostaje `-2`, `-3`…) i katalog roboczy `<repozytorium>/.agent/<id uruchomienia>`
   (`git worktree add`). `/.agent/` trafia do `.git/info/exclude` (lokalnie, bez commita).
2. Agent pracuje w tym katalogu (podfolder, gdy projekt to podfolder repozytorium). Plik zadania i kartę zmienia
   pod ścieżkami bezwzględnymi z promptu (prawdziwe pliki w folderze projektu, dostępne przez `--add-dir`);
   prompt podaje gałąź i każe zatwierdzić pracę na niej, bez zmiany gałęzi i bez push.
3. Po zakończeniu panel zatwierdza niezatwierdzone zmiany agenta na tej gałęzi (bez `KARTA.md`, `ZADANIA.md`,
   `DECYZJE.md` i pliku zadania; autor z konfiguracji repozytorium, a bez niej „Panel projektów”), zapisuje w rekordzie
   `branch`, `base`, `baseCommit`, `changes`, `commits` i usuwa katalog roboczy. Gałąź zostaje. Gdy agent przełączył
   katalog na własną gałąź, rekord wskazuje tę gałąź.
4. Uruchomienie przerwane restartem serwera: to samo przy starcie serwera.
5. **Ponowne uruchomienie zadania** (np. `[!]` → `[ ]` z `poprawka:`) zaczyna od gałęzi poprzedniej pracy: najpierw
   gałąź z pola `gałąź:` zadania, potem gałęzie wcześniejszych uruchomień tego zadania (najnowsze najpierw). Bierze
   pierwszą, która istnieje i ma commity spoza bieżącego `HEAD` (`git worktree add <katalog> <gałąź>`, bez nowej
   gałęzi); `baseCommit` to punkt rozejścia (`git merge-base`), więc `changes` obejmuje całą gałąź. Prompt mówi
   agentowi, że gałąź ma już jego wcześniejszą pracę. Gałąź scalona albo bez commitów: nowa gałąź jak w punkcie 1.

6. **Części projektu** (pole karty `część projektu:`): zadanie projektu głównego dostaje dla każdej części z własnym
   repozytorium git (innym niż repozytorium zadania; najwyżej 4) gałąź `agent/RRRR-MM-DD-nazwa` i katalog roboczy
   `<repozytorium części>/.agent/<id>` (`--add-dir`, prompt: „katalog roboczy … (gałąź …)”). Folder części jest dla
   agenta tylko do odczytu: `--disallowedTools` z `Edit(//<folder części>/<wpis>)` (i `/**` dla folderów) dla każdego
   wpisu poza `.agent` i `.git`. Po zakończeniu panel zatwierdza zmiany w katalogu części na jej gałęzi, usuwa katalog,
   gałąź bez commitów kasuje; rekord ma `parts` [{project, label, branch, base, baseCommit, changes, commits}]. Panel
   pokazuje te gałęzie przy zmianach agenta z przyciskiem „Połącz zmiany” (`/api/agent/merge {project, branch}`).

Polecenia git panelu działają bez haków repozytorium (`core.hooksPath` pusty) i bez podpisywania commitów.

### Zmiany niezatwierdzone w repozytorium projektu

„Kod i pliki” (stan z `/api/github/stan`) pokazuje pliki niezatwierdzone, `sources` (uruchomienia z ostatnich 3 dni,
które zapisywały te pliki narzędziem Edit/Write poza swoim katalogiem roboczym) i `stashes` (schowek git). Działania
wykonuje proces panelu: `POST /api/repo/zatwierdz {project}` (jeden commit na bieżącej gałęzi, autor „Panel projektów”,
opis z tytułem zadania i id uruchomienia), `POST /api/repo/odloz {project}` (`git stash push -u` z opisem),
`POST /api/repo/przywroc {project, ref}` (`git stash apply` i `drop`; tylko przy czystym repozytorium, przy kolizji
schowek zostaje). Bez katalogów `.agent/`, `node_modules/`, wyników budowania i dowiązań karty. Scalanie przy takich
zmianach odpowiada 409 z listą plików i nazwą przycisków; zakładka Strona pokazuje to samo (`repo` w `/api/strona`).
Błąd git przy starcie (np. brak commita) nie blokuje zadania: praca idzie w folderze projektu, krok w rekordzie to opisuje.

### Kopia projektu i GitHub

Repozytorium na GitHubie (pole karty `- github: właściciel/repozytorium`, opcjonalnie `- github gałąź: nazwa`) jest
źródłem prawdy. Kopia w folderze projektu na serwerze jest potrzebna tylko na czas pracy (zadania agentów,
podgląd strony). Moduł `dashboard/kopie.py`, widok: Serwer → „Projekty i GitHub” (wiersz projektu z repozytorium git
albo z polem `github:`; stan wczytuje się po rozwinięciu wiersza). Na stronie projektu kopia usunięta ma znacznik
„Kopia na GitHubie”.

- **Stan** (bez sieci): `origin` (bez danych logowania), bieżąca gałąź, commity przed/za `origin/<gałąź>`, lokalne
  gałęzie bez odpowiednika na GitHubie (osobno `agent/…`), pliki niezatwierdzone i nieśledzone (bez `.agent/`,
  `node_modules/`, `.zrzuty/` i wyników budowania: `dist/`, `build/`, `.next/` itp.; bez dowiązań karty), czas
  ostatniego `git fetch`. **„Sprawdź”** robi `git fetch --prune origin` z limitem czasu (`PANEL_GITHUB_TIMEOUT`, 60 s).
- **„Wyślij na GitHub”**: `git push origin <gałąź>:<gałąź>` bieżącej gałęzi i zaznaczonych innych gałęzi z niewysłanymi
  commitami, z procesu panelu (jego klucz SSH), bez `--force` i bez haków. Gałąź nowa na GitHubie dostaje upstream.
  Komunikat: wysłano / nic do wysłania / odrzucone (na GitHubie są nowsze commity) / brak dostępu (co ustawić: klucz
  SSH konta panelu z prawem zapisu) / brak repozytorium / brak odpowiedzi. `origin` inny niż pole `github:` blokuje
  wysłanie.
- **„Usuń kopię z serwera”**: aktywne, gdy pole `github:` jest w karcie, `origin` to to repozytorium, nie ma plików
  niezatwierdzonych i nieśledzonych (poza wykluczonymi), każda lokalna gałąź jest na GitHubie albo scalona w gałąź,
  która tam jest (`git rev-list <gałąź> --not --remotes=origin` puste), nie ma katalogów roboczych w `.agent/`,
  `KARTA.md` i `ZADANIA.md` są dowiązaniami do `szkice/` w IntegrateSystems, nie pracuje agent, nie trwa budowanie
  podglądu, a projekt jest z rejestru. Inaczej przycisk jest wyłączony, a pod nim lista blokad. Po potwierdzeniu panel
  wstrzymuje przyjmowanie zadań, robi `git fetch` (błąd = kopia zostaje), sprawdza blokady jeszcze raz i przenosi folder
  do `<folder nadrzędny>/.kosz/<projekt>-RRRR-MM-DD` (kolejne tego dnia: `-2`, `-3`). Niczego nie kasuje. W folderze
  projektu zostają dowiązania karty (`KARTA.md`, `ZADANIA.md`, `DECYZJE.md`, `kampanie`) i plik
  `.kopia-na-githubie.json` (kiedy, dokąd), więc projekt zostaje w rejestrze i w panelu z kartą i zadaniami.
- **Klon na start**: gdy karta ma `github:`, a folder projektu nie ma repozytorium, panel przed zadaniem agenta
  (`/api/agent/run`, Automat, uruchomienia z rozmów i uwag do strony) i przed budowaniem podglądu klonuje
  repozytorium (gałąź z `github gałąź:`, bez niej domyślną) obok folderu, przenosi do klonu dowiązania karty
  (dopisane do `.git/info/exclude` razem z `/.agent/`, `.zrzuty/`, `node_modules/`) i podmienia folder. Krok
  uruchomienia: „Sklonowano z GitHuba: …”. Błąd klonu blokuje start z powodem (409, np. „Nie sklonowano z GitHuba: brak
  dostępu…”); podgląd strony dostaje ten powód jako błąd budowania. Folder z innymi plikami bez repozytorium nie jest
  nadpisywany (409).
- Adres klonu: `PANEL_GITHUB_URL` z `{repo}` (domyślnie `git@github.com:{repo}.git`). Git bez pytań o hasło
  (`BatchMode=yes`, `StrictHostKeyChecking=accept-new`, `GIT_TERMINAL_PROMPT=0`). Jedna operacja naraz na folder.
- Agent zadania dalej nie ma `git push` (`TASK_TOOLS`); wysyła tylko panel na przycisk.

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
`runBlock` pusty (w tym poprzednicy z `po:` zrobieni), stan `[ ]`, `kto: agent`, `kto: claude` albo `kto: codex`, `gdzie:` równe
temu węzłowi albo brak `gdzie:` na węźle domyślnym, `kiedy:` ustawione i nie później niż dziś (przeszła data też),
`pora` zgodna (noc 22:00–6:00, dzień 6:00–22:00, brak pola: zawsze), brak dzisiejszego uruchomienia tego zadania,
brak aktywnego limitu i znacznika logowania. Raz dziennie po `PANEL_PM_HOUR` uruchamia raport PM, gdy nie ma `raporty/<dziś>.md`.

Rytm marketingu, przy każdym przebiegu, dla projektów z rejestru z plikiem `kampanie/staly-rytm.md` (poza stanem
wstrzymany i backlog), zadania trafiają do „Do rozplanowania”:
- dotychczasowy rytm: „Przygotować post na RRRR-MM-DD (stały rytm)” przed kolejnym terminem z ustawień rytmu;
- publikacja niezrobiona z `kiedy` od dziś do 2 dni naprzód, bez `materiał:` w szczegółach i bez folderu
  `posty/<kiedy>-*` (obok `KARTA.md`): „Przygotować post na <kiedy>: <tytuł publikacji>” (`kto: claude`, `gdzie:`
  ten węzeł, `kiedy:` dziś, `czas: 5` na przejrzenie przez właściciela), gdy takiego zadania jeszcze nie ma;
  szczegóły: `cel:` (data, kanał, tytuł), `gotowe gdy:` (folder `posty/<kiedy>-<nazwa>/` z `post.md` w sekcjach
  Facebook, LinkedIn, Alt i grafiką), `materiał:` `kampanie/staly-rytm.md`, `STYL.md` i plan marketingu, gdy istnieją
  (`STYL.md`, `marketing/STYL.md`, `kampanie/STYL.md`; `marketing/plan*.md`, `kampanie/plan*.md`, `PLAN.md`, `plan*.md`;
  w folderze projektu albo karty);
- publikacja `[x]` z `kiedy` dawniej niż 2 dni (48 h) bez wyniku (wiersz `wynik:` albo `wyświetlenia:`, `kliknięcia:`,
  `konta:`): „Wpisz wynik publikacji <tytuł>” (`kto: ty`, `kiedy:` dziś, `czas: 3`; `cel:`, `gotowe gdy:` z wierszami
  wyniku, `materiał:` rytm i plan). Tylko raz: klucz publikacji trafia do `rytmDone` w `stan.json`, więc usunięte
  zadanie nie wraca.
- `PANEL_RYTM` (dotychczasowy rytm) zakłada zadanie z tymi samymi szczegółami.

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
- Bezpiecznik zużycia (od 2026-11-23, po zadaniu „wizytówki”, które przez 33 własnych pomocników zużyło cały limit
  5 godzin): każde `rate_limit_event` niesie zużycie okien limitu (`unifiedWindows.five_hour.utilization`, 0–1). Rekord
  uruchomienia ma `limitStart` (pierwszy odczyt) i `limitNow` (ostatni). Gdy `limitNow − limitStart` ≥ `PANEL_RUN_BUDGET_PROC`
  (domyślnie 20 punktów procentowych), panel zatrzymuje uruchomienie (stan `stopped`, `error` z powodem). Przy wyborze wykonawcy panel pomija narzędzie, gdy odczytane zużycie dowolnego okna osiąga
  `PANEL_AUTOMAT_DO_PROC` (domyślnie 80%). `/api/data` → `agents.usage` podaje ułamki i czasy odczytu obu okien. Zadania, raport PM, rozmowy i Asystent mają `--disallowedTools` z pomocnikami, przepływami
  i harmonogramem (`RUN_DENY`), a zadania i raport PM także `--strict-mcp-config` (bez konektorów konta).

## `/api/data`

Pola z odczytu plików (np. `priority` projektu, `proposal` pytania, `target` i `result` kampanii) serwer przekazuje
bez filtrowania; `dayMinutes` to `PANEL_DZIEN_MIN`. Każde zadanie w `tasks` ma dodatkowo: `runId` (id uruchomienia w kolejce albo w toku, inaczej `""`), `runBlock`,
`stateSince`, `doneAt`, `blockedSince`, `stalled`, `reviewOverdue`, `ownerNeeds`, `check` (pole `sprawdza:` z `server.checks` albo plikiem;
`null` bez pola), a z odczytu plików `detail`, `needs`, `after`, `waitingFor`, `unlocks` i `unlockCount`
(opis w `README.md`, „Szczegóły zadania i następny krok”). `doneAt` („RRRR-MM-DD” od kiedy `[x]`) i `blockedSince` (od kiedy `[!]` albo pole `blokada:`)
są `""`, gdy zadanie jest w innym stanie albo data jest nieznana: zmiana widziana przez panel liczy się od dnia, w którym
panel ją zobaczył; zadanie zastane w tym stanie dostaje dzień końca ostatniego uruchomienia agenta dla zadania, a bez
uruchomienia `""`. Projekty przykładowe: `""`. Pytania mają `effects` i `options` (wiersze `opcja:`, bez nich `[]`),
kampanie `counters`. Poza tym `/api/data` ma `youToday`, `youWeek`, `youLater`
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
| `/api/task/detail` | `{"id": taskId, "title": tytuł, "key": klucz, "value": tekst}` | jeden klucz szczegółów: `cel`, `gotowe gdy`, `materiał`, `wynik`, `decyzja`, `zostało`, `zmiany`, `poprawka`, `następne`, a dla publikacji `wyświetlenia`, `kliknięcia`, `konta`, `link`; `krok` z value `{"index": n, "done": bool}`; 400 przy złej wartości, 409, gdy wiersz się zmienił |
| `/api/session/logout-all` | `{}` | unieważnia wszystkie sesje panelu (nowy klucz sesji) |
| `/api/agent/pm` | `{}` | raport PM; 409, gdy już trwa |
| `/api/agent/check` | `{"tool": "claude"}` | test połączenia |
| `/api/agent/stop` | `{"id": runId}` | zatrzymuje albo zdejmuje z kolejki |
| `/api/agent/merge` | `{"id": runId}` | `git merge --no-ff` gałęzi uruchomienia do `base` w repozytorium projektu, bez push; odpowiedź `commit`; 404 bez gałęzi albo repozytorium; 409 z opisem: uruchomienie trwa, już scalona, w repozytorium wybrana inna gałąź niż `base`, trwa inne scalanie, niezatwierdzone zmiany (poza `KARTA.md`, `ZADANIA.md`, `DECYZJE.md`, które zmienia panel), brak zmian, pliki sekretów na gałęzi (dodane albo zmienione `.env*`, `*.key`, `*.pem`; scalenie nie startuje, lista plików w opisie), konflikt (scalenie przerwane, repozytorium bez zmian) |

Gałąź bez uruchomienia (pole `gałąź:` zadania): `/api/agent/merge` z `{"project", "branch"}` i
`/api/agent/diff?project=&branch=`; tylko gałęzie `agent/…`, baza to gałąź wybrana teraz w repozytorium.
Zasada w poleceniu agenta: bez zlecania właścicielowi kroków technicznych; potrzebne dane jako pytanie w `KARTA.md`.
Odpowiedzi z formularza `pyta:` poprzedników (`po:`) trafiają do polecenia jako „Dane od właściciela”.
Zadanie `kto: ty`, które wymaga danych od właściciela, dostaje od razu `pyta:` z typami (`Etykieta [tekst, np. …]`,
`[tak/nie]`, `[liczba]`, `[wybór: A | B]`, `[data]`, `[link]`; format w STANDARD.md); dotyczy Asystenta, Rozmowy
w projekcie, PM i agentów. Pól na hasła nie ma: `Hasło do X [hasło: gdzie je wpisać]` daje tylko zdanie.
Zadanie właściciela bez `pyta:` panel pokazuje raz Claude Haiku (`POST /api/task/pola`, `dashboard/pola.py`),
a przy pierwszym starcie po wdrożeniu robi to jednorazowo dla wszystkich otwartych zadań właściciela z rejestru;
lista dopisanych pól jest w `pola-zadan.json` (katalog uruchomień) i w danych panelu (`fieldsMigration`).
„Zrobione” w formularzu to `POST /api/task/finish {id, title, values, count?}`: odpowiedzi sprawdzone według typu,
`odpowiedź:`, kroki, stan `[x]` w jednym zapisie.

`GET /api/agent/diff?id=<runId>`: `text/plain`, diff `baseCommit...branch` (najwyżej 200 KB, dłuższy obcięty z dopiskiem);
błąd jako JSON `{"ok": false, "error"}` z kodem 404 albo 409 jak przy scaleniu.
| `/api/agent/automat` | `{"enabled": bool}` | włącza i wyłącza Automat |
| `/api/strona/zbuduj` | `{"project"}` | budowanie podglądu strony w tle (gdy trwa: jeszcze raz po nim); 409 bez pola `strona:` |
| `/api/strona/uwaga` | `{"project", "text", "view": "telefon"\|"komputer", "page", "selector", "elementText"}` | zadanie agenta z uwagi i uruchomienie; odpowiedź `note`, `runId`; 400 bez tekstu |
| `/api/strona/koncepcja` | `{"project", "path", "text"?}` | zadanie „według koncepcji”; 400, gdy ścieżki nie ma w projekcie |
| `/api/project/add` | `{"path": folder, "name"?: nazwa, "files": bool}` | dopisuje istniejący folder do rejestru; `files: true` zakłada brakujące pliki standardu (niczego nie nadpisuje) |
| `/api/project/remove` | `{"id": projekt}` | usuwa z rejestru; pliki zostają |
| `/api/github/stan` | `{"project", "fetch"?: bool}` | stan kopii (`state`: `repo`, `stub`, `removed`, `github`, `githubBranch`, `origin`, `originOk`, `branch`, `remoteBranch`, `ahead`, `behind`, `branches` [`name`, `remote`, `ahead`, `behind`, `unpushed`, `agent`, `current`], `dirty`, `dirtyCount`, `worktrees`, `fetchedAt`, `cardsLinked`, `agentLive`, `blocks`, `removable`); `fetch: true` najpierw `git fetch` (502 z opisem, gdy się nie udał) |
| `/api/github/wyslij` | `{"project", "branches"?: [nazwy]}` | push bieżącej gałęzi i podanych, bez `--force`; `result`: `sent`/`nothing` (200), `rejected`/`error` (409), `access`/`missing`/`timeout` (502); `results` po gałęziach, `message`, `state` |
| `/api/github/usun-kopie` | `{"project", "confirm": true}` | przeniesienie kopii do kosza (opis wyżej); 400 bez potwierdzenia, 409 z blokadami, 502 gdy `git fetch` się nie udał; odpowiedź `trash`, `message`, `state` |

### Rozmowy: dwa miejsca, jeden silnik

Z agentem rozmawia się tylko w dwóch miejscach:

- **Asystent** (strona Asystent): sprawy wszystkich projektów (`POST /api/asystent`, głos `POST /api/asystent/glos`).
- **Rozmowa w projekcie** (przycisk „Rozmowa” w nagłówku strony projektu, w prawym dolnym rogu odbioru pracy;
  w szczegółach zadania „Zapytaj o to zadanie”): sprawy projektu i jego części (`POST /api/project/chat`). W szczegółach zadania i w odbiorze przycisk
  „Zapytaj o to zadanie” otwiera tę rozmowę z odnośnikiem do zadania; zadanie części otwiera rozmowę tej części.

Obie mają te same uprawnienia i tę samą drogę działania (`Manager.chat_tools`, `chat_args`, `chat_rules`,
`chat_launches`), więc żadna nie odmawia tego, co robi druga:

- polecenie `claude -p --permission-mode default --model <PANEL_ASYSTENT_MODEL> --add-dir <karty i foldery>
  --allowedTools "Read,Grep,Glob,LS[,WebSearch,WebFetch],Edit(/<karta>/ZADANIA.md),Edit(/<karta>/DECYZJE.md),
  Edit(/<karta>/kampanie/**)…" --disallowedTools "<ASSIST_DENY>" --strict-mcp-config`. Zakazy (`CHAT_DENY`): powłoka,
  zapis innych plików, `MultiEdit`, `NotebookEdit`, pomocnicy i przepływy (`RUN_DENY`); internet tylko do odczytu, gdy
  `PANEL_ASYSTENT_INTERNET` jest różne od 0. Asystent ma edycję plików wszystkich projektów, Rozmowa w projekcie
  plików projektu i jego części. Asystent działa w stałej sesji stream-json, Rozmowa w projekcie jednym wywołaniem
  `--output-format json` z `--resume`;
- zasady w promptach z jednego źródła (`chat_rules`): zmiany tylko w ZADANIA.md, DECYZJE.md i kampanie/ na prośbę
  właściciela, anulowanie przez `[x]` i `wynik: anulowane`, wiersz „Zmieniono:”, link do podglądu strony, bez kart,
  kodu, poleceń, publikacji i próśb o hasła;
- wiersze działań na końcu odpowiedzi (`take_actions`; panel wykonuje je i usuwa z odpowiedzi):
  - `Uruchom: <id projektu> | <tytuł>`: `launch_task` → `run_task`;
  - `Polecenie: <id projektu> | <tytuł> | <polecenie>`: `_execute_order` (poprawka pod zadaniem, uruchomienie albo
    wiadomość do pracującego agenta, jak „Wyślij i wykonaj”);
  - `Odpowiedź na pytanie: <id projektu> | <numer> | <odpowiedź>`: `server.answer_question` (ta sama droga co
    przycisk przy pytaniu, ze skutkami `skutek:`);

  najwyżej 3 uruchomienia i polecenia razem oraz 3 odpowiedzi w jednej odpowiedzi; Rozmowa w projekcie działa tylko
  na zadaniach swojego projektu i jego części;
- twarde zasady bez zmian w obu: `wymaga: zgoda` czeka na kliknięcie, `kto: ty` i publikacje nie ruszają, nic nie
  publikują, bez powłoki; uruchamia zawsze serwer.

`POST /api/project/chat` z `{"project", "message", "task"?: id zadania, "execute"?: true, "attach"?: {...}}`
(wiadomość najwyżej 2000 znaków, treść żądania do 32 KB):

- bez `execute` i `attach`: wiadomość dla modelu; odpowiedź 202 `{"pending": true}`, odpowiedź modelu w tle.
  Z `task` panel dokleja przed wiadomością kontekst zadania (`task_context`: tytuł, projekt, plik i wiersz, stan,
  wykonawca, termin, etap, szczegóły z `cel:`, `gotowe gdy:`, krokami, poprawką, ostatnie uruchomienie: stan, koniec,
  wynik albo błąd, gałąź), także w trwającej sesji; wiadomość w historii ma `task: {id, title, project}`;
- `execute: true` przy zadaniu `kto: agent|claude|codex` (albo „zrób to”, „wykonaj”, „wykonaj to” na końcu,
  `EXEC_END`): bez modelu panel zapisuje wiadomość jako `poprawka:` (najwyżej 1000 znaków), zadanie `[x]`, `[~]` albo
  `[!]` wraca do `[ ]` (zdejmuje `blokada:` i `wymaga: odbiór`, `wymaga: zgoda` zostaje), potem `run_task`; przy
  pracującym agencie wiadomość do tego uruchomienia („Praca na żywo”). Odpowiedź 200 `{"status": wiadomość panelu}`.
  Zadanie właściciela: zwykła wiadomość dla modelu;
- `attach: {"kind": "strona", "project": <część ze stroną>, "page", "view", "selector", "elementText"}` (zakładka
  Strona): uwaga do strony bez modelu, ta sama droga co dawny formularz (`site.add_note`: zadanie agenta strony
  i `run_task` albo wiadomość do pracującego agenta strony); odpowiedź 200 `{"note", "runId", "status"}`; wiadomość
  w historii ma `attach`.

Błędy: 400 pusta albo za długa wiadomość, 404 brak projektu albo zadania spoza projektu, 409 poprzednia odpowiedź
jeszcze trwa („Czekam jeszcze na odpowiedź.”), brak `claude`, wymagane logowanie, limit albo 3 rozmowy naraz.
`GET /api/project/chat?project=`: `{"messages": [{"role": "ty"|"claude"|"panel", "text", "at", "task"?, "attach"?,
"exec"?}], "pending", "error"}`. Historia (najwyżej 100 wiadomości, id sesji) w
`uruchomienia/czat/projekt-<sha1 id>.json`. Limit odpowiedzi 180 s.

**Dawny czat przy zadaniu** (do 2026-11-25) nie istnieje: `POST /api/task/chat` zwraca 404. Historia zostaje do odczytu
(`GET /api/task/chat?id=`, w szczegółach zadania „Dawna rozmowa o zadaniu”). „Do poprawy” w szczegółach i „Popraw”
w odbiorze (`/api/odbior/popraw`) zapisują polecenie i stan w Rozmowie w projekcie zadania.

**Przyciski jednego działania** nie rozmawiają z modelem: zakładają albo zmieniają zadanie i wołają `run_task` (te same
reguły co „Uruchom”): Marketing „Zleć” (`/api/post/zlec`), „Co poprawić” w poście i filmie (`/api/post/popraw`),
scenariusz „Przygotuj” i „Co zmienić?” (`/api/scenariusz/przygotuj|popraw`), studio filmów „Poproś”
(`/api/studio/popros`), Strona „Zleć wykonanie według koncepcji” (`/api/strona/koncepcja`), Serwer → Projekty
„Zleć agentowi uzupełnienie”, „Do poprawy” i odbiór. Wyjątki z własnym wywołaniem modelu, bez rozmowy: raport PM
(`/api/agent/pm`, rola PM z `PM_TOOLS`, wiersze `Uruchom:` przez `launch_task`), plan dnia (`/api/plan/ask`, przyjęcie
przez `run_task`) i grafika posta przez Codex (`/api/post/grafika-codex`, obróbka jednego obrazu w folderze posta).

### Uruchamianie z rozmów

Każda rozmowa może od razu uruchomić pracę agenta. Uruchamia zawsze serwer przez `run_task` (te same reguły co przycisk
„Uruchom”: `runBlock`, logowanie, limit, `PANEL_AGENTS_MAX`), nigdy model.

- Prośba o pracę („zrób”, „przygotuj”, „napraw”…) to zadanie agenta w `ZADANIA.md` (`- [ ] Tytuł | kto: agent |
  kiedy: <dziś>` z `cel:` i `gotowe gdy:`; pasujące otwarte zadanie zamiast nowego) i wiersz `Uruchom:`. Panel szuka
  zadania po tytule (najpierw otwarte) i woła `run_task`. Pytanie o stan nie zakłada zadań i nie uruchamia.
- Polecenie do istniejącego zadania agenta: wiersz `Polecenie:` albo przycisk „Wyślij i wykonaj” / „Wyślij do agenta”
  przy odnośniku do zadania.
- **Stan w rozmowie.** Po każdym uruchomieniu w historii jest wiadomość panelu (`role: "panel"`, nie od modelu):
  „Uruchomiono: …”, „W kolejce: agent pracuje nad „…”, to zadanie ruszy po nim.”, „Już w toku: …” albo „Nie uruchomiono
  „…”: powód.” (czeka na zgodę, po Twojej stronie, brak wykonawcy agenta, nie ma takiego zadania, logowanie, limit; przy
  logowaniu i limicie z dopiskiem, czy zadanie z dzisiejszą datą weźmie Automat). `GET` rozmów dokłada do takiej wiadomości
  `taskId` (link „Szczegóły”), `live` (stan uruchomienia) i `label` (w kolejce, w toku, do odbioru, zrobione, blokada,
  błąd…), liczone przy każdym odczycie; panel odświeża rozmowę co 5 s, dopóki coś jest w kolejce albo w toku.
- Zasady promptów rozmów mają wersję (`CHAT_RULES_V`); rozmowa zapisana z inną wersją zaczyna nową sesję z pełnym
  promptem, żeby dostała nowe zasady.

### Praca na żywo (wiadomość w trakcie, podgląd przebiegu)

**Wiadomość do pracującego agenta** (`Manager.live_message`). W Rozmowie w projekcie z odnośnikiem do zadania, gdy
agent pracuje albo czeka w kolejce, przycisk „Wyślij do agenta” („Wyślij” pyta model jak zwykle); wiersz `Polecenie:`
z odpowiedzi rozmowy idzie tak samo. Droga jest ta sama co „Wyślij i wykonaj” (`POST /api/project/chat` z `"task"`
i `"execute": true`); panel:

1. zawsze dopisuje polecenie do wiersza `poprawka:` zadania (`stara / nowa`, najwyżej 1500 znaków, znaczniki
   zostają), żeby następne uruchomienie też je znało; rekord dostaje nowe `fix` (Automat nie powtarza przez to
   tego uruchomienia);
2. **Claude w toku:** zapisuje na stdin wiersz `{"type":"user","message":{"role":"user","content":"…"}}`. Claude
   Code dołącza go do bieżącej tury przy następnym kroku (sprawdzone na CLI 2.1: jedno zdarzenie `result`, agent
   uwzględnił wiadomość). Wiadomość panelu: „Przekazano agentowi.”; w przebiegu wiersz „Ty: …”. Wiadomość wysłana
   przed startem procesu idzie zaraz po poleceniu;
3. **po zdarzeniu `result`** panel zamyka stdin (CLI kończy pracę). Wiadomość, której agent nie odczytał (po jej
   wysłaniu nie było już wyniku narzędzia i kolejnej odpowiedzi), dostaje 20 s (`GRACE`) na nową turę; bez niej
   i dla wiadomości wysłanej już po `result`: „Agent skończył, polecenie zapisane jako poprawka. Zadanie uruchomi się
   ponownie z tym poleceniem.” Po zakończeniu panel robi to samo co „Wyślij i wykonaj” (przy zadaniu strony po
   scaleniu i podglądzie). Po „Zatrzymaj” bez ponownego uruchomienia;
4. **zadanie w kolejce:** polecenie trafia do polecenia startowego („polecenie dołączone do zadania”);
5. **Codex** (`codex exec` nie przyjmuje wejścia w trakcie): tylko zapis poprawki i przycisk „Zatrzymaj i uruchom
   z poprawką” (`POST /api/agent/restart {"id"}`: zatrzymanie, potem `launch_task`).

„Zatrzymaj”, limit czasu i bezpiecznik zużycia działają jak dotąd (zabijają grupę procesów).

**Uwaga z zakładki Strona** (Rozmowa w projekcie z załącznikiem Strony) przy uruchomieniu zadania strony tego projektu w kolejce albo w toku
idzie tą samą drogą do tego uruchomienia (tekst „Uwaga do strony: … (podstrona, widok, element)”), bez nowego
zadania; uwaga dostaje tytuł tego zadania i jego wynik.

**Podgląd przebiegu.** Rekord uruchomienia ma pole `log` (ostatnie 200 wierszy `{"n", "t", "k", "text"}`; `k`: `agent`
pełna wypowiedź do 4000 znaków, `narzedzie` z krótkim argumentem, `odmowa` (wynik narzędzia z odmową uprawnień
i `permission_denials` z wyniku), `ty`, `panel`) i licznik `logN`. Rekord zapisuje się w trakcie najrzadziej co 10 s;
osobnych plików logów nie ma. `/api/data` ma tylko `logN` i `takesMsg` (agent przyjmie wiadomość na stdin).
`GET /api/agent/przebieg?id=&od=<n>` oddaje wiersze o numerze większym niż `n`, stan i najnowsze zrzuty strony;
`GET /api/agent/zrzut?id=&plik=telefon.png` oddaje PNG z `.zrzuty/` katalogu roboczego tego uruchomienia (nazwa
`[\w.-]+.png`, bez dowiązań, bez wyjścia poza katalog, sygnatura PNG, do 15 MB). W szczegółach zadania (blok „Agent
pracuje”) i w podglądzie uruchomienia lista odświeża się co 3 s; przewijanie przyklejone do dołu, dopóki właściciel
nie przewinie w górę („Najnowsze” wraca); lista ma fokus z klawiatury (strzałki, End).

### Odbiór pracy (wersje wyniku, znaczniki)

Strona odbioru w panelu (`#odbior?z=<taskId>`) pokazuje wynik zadania w wersjach, z porównaniem, „Akceptuję” i „Popraw”.

- **Wersja** = stan wyniku po jednym udanym uruchomieniu zadania. Po `_finish` ze stanem `done` panel zapisuje
  `uruchomienia/wersje/<sha1 „projekt|plik|tytuł”[:16]>/<n>/meta.json` i kopie plików z wyniku (`plik-<i>.<rozszerzenie>`):
  `{"n", "at", "runId", "result", "left", "decision", "changes": [...], "fixes": [{"text", "pins": [...]}],
  "files": [{"path", "kind": "image|pdf|text|video", "size", "copy"?, "skipped"?}]}`. Pliki z wyniku: ścieżki
  .md/.txt/.png/.jpg/.jpeg/.webp/.pdf/.mp4/.mov z `wynik:` i `zostało:` (jak `resFiles` w panelu, bez `..`, `ZADANIA.md`
  i materiałów zadania, najwyżej 12), z folderu projektu albo karty, a gdy ich tam nie ma, z gałęzi uruchomienia. Plik
  ponad 15 MB albo ponad 60 MB razem: bez kopii, z polem `skipped` (odczyt wtedy z folderu albo gałęzi). `fixes` to
  poprawka, na którą odpowiadało uruchomienie (`fix` i `pins` rekordu); `changes` puste, gdy agent nie odnowił `zmiany:`.
  Wersje nie są nadpisywane, najwyżej 20 na zadanie (najstarsze usuwane). Bez wersji zapisanych (stare zadania) API
  zwraca jedną wersję bieżącą z pól zadania (`n: 1`, `saved: false`).
- **Znaczniki**: pod `poprawka:` wiersze `  - znacznik N (plik, 34% od lewej, 60% od góry): uwaga`, przy filmie
  `(plik, 0:12)` (oba naraz też); parsowane do `detail.pins` (`{"n", "file", "x", "y", "t", "note"}`, x i y w %, t w s).
  Każdy zapis `poprawka:` zastępuje stare znaczniki. Rekord uruchomienia ma `pins` obok `fix`.
- `GET /api/odbior?id=<taskId>`: `{"ok", "task": {"id", "title", "project", "projectName", "stage", "state", "needsYou",
  "executor", "goal", "doneWhen", "decision", "left", "fix", "pins"}, "versions": [{"n", "at", "saved", "runId",
  "result", "decision", "left", "changes", "fixes", "files": [{"path", "name", "kind", "size", "url", "skipped"?}]}]`
  (od najstarszej), `"run": {"id", "state", "queuedAt", "startedAt", "endedAt", "steps": [{"t", "text"}], "activity",
  "error", "position"} | null` (bieżące albo ostatnie uruchomienie; `position` w kolejce od 1), `"accepted": [nazwy]}`;
  404 bez zadania.
- `GET /api/odbior/plik?id=&v=&path=`: bajty pliku wymienionego w wersji `v` (kopia wersji; dla wersji bieżącej albo
  pliku `skipped` folder projektu lub gałąź agenta), typ jak `/api/plik/surowy` plus `text/plain` (.md, .txt) i
  `video/mp4`, `video/quicktime`; bez SVG i HTML; `nosniff`, `no-store`, `Range` (206, film w Safari). Inne ścieżki: 404.
- `POST /api/odbior/popraw` `{"id", "title", "text", "pins": [{"file", "x", "y", "t", "note"}]}`: tekst do 1000 znaków,
  najwyżej 12 znaczników, x i y 0–100 (oba albo żaden), t w sekundach, uwaga do 300 znaków, plik obrazu albo filmu
  (bez `..`). Pusty tekst i brak znaczników: 400; sam znacznik: `poprawka: Popraw według znaczników poniżej.`
  Zapis i uruchomienie jak „Wyślij i wykonaj” (`chat_execute`, wpis w Rozmowie w projekcie zadania); odpowiedź `{"status"}`.
- `POST /api/odbior/akceptuj` `{"id", "title", "variants": [nazwy] | null}`: zadanie `[x]` bez `wymaga:` (jak „Odbierz”).
  Warianty to obrazy ostatniej wersji (nazwa pliku bez rozszerzenia). Gdy podano nie wszystkie: pod zadaniem
  `odpowiedź: odebrane warianty = a, b` (pozostałe odpowiedzi zostają); odpowiedź `{"accepted": [...]}`. 400 przy
  pustej liście albo nieznanym wariancie, 409 przy zmienionym wierszu albo gdy agent jeszcze pracuje.

### Asystent i głos

`POST /api/asystent` z `{"message", "view": "#adres", "open": id otwartego zadania}`; `GET /api/asystent`: historia,
`pending`, `partial` (odpowiedź w trakcie pisania), `activity` („Czytam pliki projektu”), `voice` (czy działa
rozpoznawanie mowy). Asystent to jeden długo żyjący proces `claude -p --input-format stream-json --output-format
stream-json --verbose --include-partial-messages` (`dashboard/asystent.py`, jako `PANEL_AGENT_USER` jak zadania, te same
narzędzia: odczyt i edycja tylko `ZADANIA.md`, `DECYZJE.md`, `kampanie/`). Pierwsza wiadomość niesie fakty
(`assistant_facts`, z id zadań; na początku liczby spraw z ostatniej odpowiedzi `/api/data`, czyli `projekt.owner_counts`,
te same co w menu, na starcie Asystenta i w raporcie PM, z podpisami) i opis sterowania; odpowiedź to jedno zdanie i najwyżej
5 punktów, liczby i listy jako karty; kolejne tylko `[ekran: #adres; otwarte: …]` i nowe fakty, gdy dane
się zmieniły. Po restarcie panelu albo bezczynności proces startuje z `--resume`; nieznana sesja zaczyna rozmowę od nowa.
Odpowiedź może kończyć się wierszami działań, które panel wykonuje po kolei i ukrywa: `Pokaż: #adres`, `Otwórz: <id
zadania albo tytuł>`, `Przewiń: <nagłówek>`, `Zamknij: szczegóły` (w przeglądarce) i `Uruchom: <id projektu> | <tytuł>`
(na serwerze, „Uruchamianie z rozmów”).

Strona Asystent (`#asystent`, pierwsza w menu) to płótno kart i rozmowa (z boku od 1100 px, niżej przyklejona na dole).
Inne widoki nie mają okna asystenta; spacja przechodzi na tę stronę. Strona jest startowa: przy pustej rozmowie pokazuje
sprawy dla Ciebie na dziś (liczba i 3 najważniejsze) i notatkę PM. Treść dawnych widoków Start, Dla Ciebie, Przegląd,
Wskaźniki, Tablica, Terminy, Blokady i Projekty to karty wbudowane typu `panel` (`sprawy-dzis`, `sprawy`, `terminy`,
`blokady`, `wskazniki`, `zadania`, `raport-pm`; `karty.STARTERS`, na pustym płótnie `karty.START`): fragmenty panelu
z tymi samymi przyciskami (odpowiedź na pytanie, zgoda, odbiór, Zrobione, Zamknij, filtry). Model wie, że to jego dane
(`karty.PROMPT`), i podaje je samym id; „Pokaż” i stare adresy pokazują je bez modelu. Model nie pisze HTML: kończy
odpowiedź blokiem ```` ```karty ```` z JSON `{"pokaz": [karta…], "usun": [id…]}`. Katalog typów (liczba, lista, tabela,
wykres, postep, tydzien, notatka, news, panel), język zapytań i opis dla modelu: `dashboard/karty.py` (`PROMPT`). Panel
sprawdza blok (`karty.extract`: nieznany typ, nieznane pole, HTML, link inny niż http(s) odrzucają kartę) i oddaje
karty w `GET /api/asystent` (`messages[].cards`: `pokaz`, `usun`, `bledy`). Karta z `zapytanie` jest liczona w
przeglądarce z `/api/data` (`kqRun` w panel.html), więc liczby są aktualne; `dane` wprost tylko dla newsów i notatek.
Biblioteka: `GET /api/asystent/karty` (zapisane, wbudowane, przypięte, ukryte), `POST /api/asystent/karty` z jednym
z `{"zapisz": karta}`, `{"usun": id}`, `{"przypiete": [id]}`, `{"ukryj": id}`, `{"pokaz": id}` (sesja jak każdy zapis;
najwyżej 100 kart i 256 kB). Karty z `"zapisz": true` zapisuje panel po odpowiedzi; lista gotowych kart idzie w prompcie
(i ponownie, gdy się zmieni), więc model najpierw podaje samo `{"id": …}`. Nowa rozmowa zdejmuje karty rozmowy,
przypięte zostają. Na stronie Asystent działanie `Pokaż:` jest pomijane (odpowiedzią jest karta).

`POST /api/asystent/glos?view=&open=`: nagranie (`audio/webm` z Chrome, `audio/mp4` z Safari, także ogg i wav; typ
sprawdzany po nagłówku i pierwszych bajtach, do 4 MB) → tekst z `dashboard/glos_stt.py` (faster-whisper, `language=pl`,
`initial_prompt` z nazwami projektów) → wiadomość jak wyżej; odpowiedź `{"text", "pending"}`. 409 z `"voice": false`,
gdy rozpoznawanie nie jest zainstalowane; 422, gdy nic nie rozpoznano. `POST /api/asystent/glos/start` wczytuje model
w tle (przy naciśnięciu „Mów”). Pracownik działa jako użytkownik panelu, startuje przy pierwszym nagraniu i kończy się
po `PANEL_GLOS_BEZCZYNNOSC`. W panelu: przycisk „Mów” (klik: start, klik: stop; myszką także przytrzymanie) albo
spacja, gdy fokus nie jest w polu ani na przycisku (przytrzymaj albo naciśnij dwa razy); Esc przerywa nagranie.

### Podgląd strony (zakładka „Strona”)

Projekt z polem karty `- strona: folder` (opcjonalnie `strona build:`, `strona wynik:`; `standard/STANDARD.md`) ma
w panelu zakładkę „Strona”; projekt główny ma ją też w „Całość”, gdy strona jest w jego części. Kod:
`dashboard/strona.py` (`Manager.site`).

Drogi do zakładki: zadanie właściciela o ocenie strony (tytuł z „zakładce Strona” albo „podgląd strony”, albo
`materiał:` w folderze strony) ma w szczegółach i na liście spraw przycisk „Otwórz podgląd”. Rozmowy o projekcie
i Asystent dostają w poleceniu adresy zakładki (`[Otwórz podgląd](#p-<główny>-strona?cz=<część>)`); panel zamienia
taki zapis i słowa „zakładka Strona” w odpowiedzi na link.

1. **Budowanie podglądu.** Panel uruchamia polecenie budowania w folderze strony w folderze projektu (domyślnie
   `npm ci && npm run build -- --base=./`). Przy `PANEL_AGENT_USER` jako agent: `sudo -n -u agent --
   /usr/local/lib/integrate/podglad-buduj.sh <folder strony> <polecenie>` (skrypt i reguła sudoers z
   `uruchom/serwer/zainstaluj-podglad.sh`; skrypt przyjmuje tylko foldery w `/home/panel/projekty`), bez tego
   `/bin/sh -c`. Czas najwyżej 15 min. Wynik (`dist`) panel kopiuje bez dowiązań (najwyżej 5000 plików, 300 MB) do
   `<PANEL_RUNS_DIR>/strona/<projekt>/wynik`; nieudane budowanie zostawia poprzedni podgląd. Stan i uwagi:
   `<PANEL_RUNS_DIR>/strona/<projekt>/stan.json`, dziennik ostatniego budowania obok.
2. **Serwowanie.** `GET /podglad/<projekt>/<klucz>/<ścieżka>`: klucz to HMAC z hasła panelu i id projektu (adres z
   `/api/strona`). Z innego urządzenia wystarcza ważny klucz albo sesja; bez nich 401. Odpowiedzi mają nagłówek
   `Content-Security-Policy: sandbox allow-scripts allow-forms allow-popups` (strona nie ma dostępu do ciasteczek
   i API panelu, także otwarta w nowej karcie), `Referrer-Policy: no-referrer` i `Access-Control-Allow-Origin: *`
   (moduły JS i czcionki z dokumentu w piaskownicy). Ścieżki z `..` albo `\`, dowiązania i pliki poza wynikiem: 404.
   Folder bez `/` na końcu (np. `/pl/prywatnosc` z routera strony) przekierowuje na adres z `/`, żeby względne
   adresy zasobów (`../assets/…`) trafiały.
   Do HTML panel dopisuje w `<head>` skrypt trybu „Wskaż” (postMessage do panelu; panel przyjmuje wiadomości tylko
   z ramki zakładki).
3. **Uwaga.** „Napisz uwagę” albo element wskazany przyciskiem „Wskaż” otwiera Rozmowę w projekcie z załącznikiem
   (podstrona, widok, selektor i tekst elementu); wysłana uwaga idzie przez `POST /api/project/chat` z `attach`
   (`/api/strona/uwaga` zostaje dla zgodności, panel go nie używa). Lista „Uwagi” pokazuje stan. Uwaga dopisuje do
   „Do rozplanowania” zadanie
   `Strona: <początek uwagi> | kto: claude | kiedy: dziś` z `cel:` (uwaga, podstrona, widok telefon 390 px albo
   komputer 1440 px, selektor CSS i tekst wskazanego elementu) i `gotowe gdy:`, i od razu je uruchamia jak
   `/api/agent/run` (gdy uruchomienie jest zablokowane, zadanie czeka w Zadaniach, a uwaga pokazuje powód).
   „Zleć wykonanie według koncepcji” (`/api/strona/koncepcja`) zakłada tak samo zadanie
   `Strona według koncepcji: <ścieżka>` z `materiał:` (plik albo folder w projekcie; podpowiedzi: pliki `.md`
   i foldery z nimi do 3 poziomów).
4. **Polecenie agenta** (zadania `Strona: …` i `Strona według koncepcji: …`, tylko Claude): zwykłe zasady zadania
   oraz: kod w folderze strony; budowanie (`npm ci --prefix …`, `npm run build --prefix … -- --base=./` albo
   polecenie z karty); zrzuty ekranu `zrzut-strony.py <wynik> 390|1440 <katalog roboczy>/.zrzuty/….png`, obejrzane
   narzędziem Read i porównane z celem (najwyżej 3 rundy); bez publikacji, wdrożenia i push; koniec `[x]` bez
   `wymaga: odbiór` (ocena w podglądzie) albo `[!]`. `--allowedTools` dostaje dodatkowo `Bash(<polecenie zrzutu>:*)`
   i reguły budowania: bez `strona build:` `Bash(npm ci)`, `Bash(npm install)`, `Bash(npm run build)` z wariantami
   `:*`; z `strona build:` (`strona.build_rules`) każdy człon `npm ci`, `npm install` i `npm run <skrypt>` (także
   z `--prefix folder` i `-- --base=./`) dostaje regułę dokładną i z `:*`, np. `npm ci && npm run build:panel` →
   `Bash(npm ci)`, `Bash(npm ci:*)`, `Bash(npm run build:panel)`, `Bash(npm run build:panel:*)`. Claude Code sprawdza
   każdy człon `&&` osobno (sprawdzone na CLI 2.1: `cd <folder strony> && npm ci && npm run build:panel` przechodzi,
   `npm run build` przy regule `build:panel` nie; stara reguła `Bash(npm run build:*)` nie przepuszczała
   `npm run build:panel`). Inne człony (`cd`, `npx`, potoki, zmienne, `npm install <pakiet>`) nie dostają reguł;
   polecenie dla agenta podaje dokładnie dozwolone polecenia i każe pominięte opisać w `zostało:`. Polecenie zrzutu: `PANEL_ZRZUT`
   albo przy `PANEL_AGENT_USER` `/home/agent/narzedzia/pw/bin/python /usr/local/lib/integrate/zrzut-strony.py`
   (Python agenta z Playwright), bez niego `uruchom/serwer/zrzut-strony.py` (Python filmu albo `python3`).
   `.git/info/exclude` repozytorium dostaje `.zrzuty/`, `node_modules/` i `/<folder strony>/<wynik>/`, więc te
   pliki nie trafiają do commita gałęzi.
5. **Po uruchomieniu** (`Manager._finish` → `Site.after_run`): błąd agenta albo `[!]` → uwaga „nie wyszło” z powodem.
   Sukces na gałęzi uruchomienia: gałąź bez zmian w folderze strony → „nie wyszło”; inaczej panel scala ją
   (`/api/agent/merge`, lokalnie, bez push), buduje podgląd i zamyka zadanie (`[x]`). Bez gałęzi: samo budowanie.
   Uwaga „zrobione” dopiero po udanym budowaniu. Scalenie innej gałęzi, która zmieniła pliki strony, też przebudowuje
   podgląd.

6. **Budowa na żywo.** Gdy agent strony pracuje, `/api/strona` ma `live`: `runId`, `title`, `state` (`queued`,
   `running`), `activity`, `steps` (ostatnie 8), `recent` (ostatnie wypowiedzi i narzędzia), `plan`, `shots` (zrzuty
   z `.zrzuty/` jego katalogu roboczego), `builtAt` (czas `index.html` wyniku budowania w katalogu roboczym), `url`
   (`/podglad/<projekt>/<klucz>/~budowa/`: wersja w budowie prosto z katalogu agenta, te same zasady serwowania;
   bez agenta 404) i `browser`. Zakładka pokazuje to w sekcji „Agent pracuje nad stroną” z przyciskami „Pokaż wersję
   w budowie” (ramka odświeża się po każdym budowaniu agenta), „Wiadomość do agenta” (Rozmowa, jak „Napisz do
   pracującego agenta”) i „Cały przebieg”. Pole `repo` (niezatwierdzone zmiany w repozytorium strony) daje ostrzeżenie
   z odnośnikiem do „Kod i pliki”.
7. **Przeglądarka dla agenta strony** (Claude, gdy jest `PANEL_PRZEGLADARKA_MCP`): panel uruchamia na czas pracy
   serwer plików wyniku budowania z katalogu roboczego agenta na `127.0.0.1:<port>` (port zapamiętany w danych
   uruchomienia, także po restarcie panelu) i daje agentowi `--mcp-config` z Playwright MCP (`--headless --isolated`,
   `--allowed-origins http://127.0.0.1:<port>`, zrzuty do `.zrzuty/przegladarka`, pamięć podręczna w `.zrzuty/.pamiec`),
   `--allowedTools` z `mcp__przegladarka__browser_navigate`, `…_snapshot`, `…_click`, `…_resize`,
   `…_take_screenshot` i innymi bez wykonywania kodu, `--disallowedTools` z `…_run_code_unsafe`, `…_evaluate`,
   `…_file_upload`, `…_drop`, oraz `--strict-mcp-config`. Polecenie podaje adres i każe oglądać stronę w 390 i 1440 px;
   inne adresy przeglądarka blokuje (`ERR_BLOCKED_BY_CLIENT`). Instalacja bez sudo:
   `cd /home/agent/narzedzia/mcp && npm install @playwright/mcp` (przeglądarka z `/opt/ms-playwright`). Agent strony
   ma też `Bash(git merge:*)` (scalenie bieżącej wersji strony do swojej gałęzi przy konflikcie).

Stany uwagi: `czeka` (w kolejce albo nieuruchomione), `pracuje` (agent albo scalenie i budowanie), `zrobione`,
`nie wyszło` (z jednym zdaniem powodu). Zrzuty skryptem Pythona (`zrzut-strony.py`) zostają: właściciel widzi je
w panelu, a agent ogląda plik PNG narzędziem Read.

### Grafiki (Codex)

Podział pracy: grafiki (generowanie i poprawianie zdjęć do postów) robi Codex wbudowanym narzędziem obrazów
(`$imagegen`, model obrazów OpenAI) na logowaniu ChatGPT, bez klucza API; teksty, zadania i resztę dalej Claude.
Ustawienie: `PANEL_GRAFIKA` (`codex` domyślnie, `wylaczone`). Wybór wykonawcy zadań (`kto:`) się nie zmienia.
Generowanie zużywa limit planu ChatGPT 3–5 razy szybciej niż zwykła tura; plan Free go nie ma.

W edytorze posta jedna sekcja „Grafika”: rozmowa z Codexem (polecenia właściciela i krótkie odpowiedzi), gotowe
polecenia do wstawienia w pole, przełącznik „Zachowaj zdjęcie” (domyślnie włączony) i „Wgraj plik”. Wynik to nowa wersja
w podglądzie platformy po lewej (pasek „Nowa wersja”: Przed/Po, Zaakceptuj, Odrzuć); „Dodaj nową wersję do karuzeli”
jest w menu ⋯. Kolejne polecenie poprawia ostatnią wersję. Ścieżek serwera panel nie pokazuje.

- Tryby: `zachowaj` (domyślny) — klasyczna obróbka zdjęcia skryptem Pythona z Pillow (wyostrzenie, szum, kontrast,
  ekspozycja, balans bieli; kadr tylko na prośbę), bez `$imagegen` i bez dodawania czy usuwania obiektów; `nowa` —
  `$imagegen` jak dotąd. W trybie `zachowaj` panel odrzuca wynik, gdy w `<CODEX_HOME>/generated_images/<wątek>/`
  pojawił się nowy obraz (generowanie mimo zakazu) albo gdy wynik ma inne proporcje niż źródło (tolerancja 1,5%),
  a polecenie nie prosiło o kadr, format, obrót ani prostowanie.
- Rozmowa: `.grafika-rozmowa.json` w folderze posta: `items` (`id` uruchomienia, `at`, `text`, `mode`, `input`,
  `state` `run|ok|error`, `reply`, `version`; albo `action` `akceptuj|odrzuc|karuzela`), `pending` (wersja czekająca na
  decyzję, `wariant-<n>.png`), `source` (obraz, który wersja zastąpi: `grafika.png` albo `zdjecie-<n>`). Wejście
  kolejnego polecenia: `pending`, inaczej `zrodlo` z żądania (obraz widoczny w podglądzie), inaczej grafika albo
  pierwsze zdjęcie. Nowa wersja usuwa poprzednią oczekującą. Wpis `run` bez żywego uruchomienia (np. po restarcie
  panelu) staje się błędem „Przerwane”.
- `GET /api/post/warianty?project=&date=`: `chat` (`items` bez `id` i `input`, `pending` `{name, at, w, h}` albo
  `null`, `source`), `variants` i `inputs` (`[{name, at}]`), `folder`, `max`, `runs` (ostatnie 5 zleceń tego posta:
  `id`, `state`, `error`, `result`, `ask`, `variants`), `tool`: `need` (`""` gotowy, `off`, `install`, `login`),
  `loginCmd`, `loginWeb`, `agentUser`, `login` (`active`, `url`, `code` logowania kodem urządzenia).
- `POST /api/post/grafika-codex {project, date, polecenie, tryb: zachowaj|nowa, zrodlo}`: polecenie w rozmowie
  (rodzaj uruchomienia `grafika`, widać je w Agentach, limit `PANEL_GRAFIKA_TIMEOUT`). Polecenie: `codex exec --json
  --sandbox workspace-write --skip-git-repo-check -C <folder posta> --image=<wejście> -` (jako `PANEL_AGENT_USER`).
  Codex zapisuje wynik jako `wariant-<n>.png` od pierwszego wolnego numeru i niczego nie nadpisuje; w trybie `nowa`
  panel bierze też obraz z katalogu sesji, gdy Codex go nie skopiował. Brak obrazu przy udanym przebiegu to `error`.
  Wynik uruchomienia (Agenci) to krótka odpowiedź bez ścieżek. 409: `zachowaj` przy poście bez obrazu, brak Codexa,
  brak logowania, grafiki wyłączone (`need`); jedno zlecenie naraz na post.
- `POST /api/post/wariant {project, date, name, akcja}`: dla oczekującej wersji (`name` = `pending`, inaczej 409)
  `akceptuj` (zastępuje `source`: grafika przez `grafika.png`, poprzednia i `grafika.svg` zostają jako
  `grafika-poprzednia-<czas>`; zdjęcie karuzeli jako `zdjecie-<n>.png`, poprzednie jako
  `grafika-poprzednia-<czas>-zdjecie-<n>`), `odrzuc` (usuwa wersję), `karuzela` (wersja jako kolejne `zdjecie-<n>`);
  dla dowolnego wariantu `grafika` i `usun`.
- Logowanie Codex z panelu: na Macu i PC `POST /api/agent/login {"tool": "codex"}` otwiera Terminal z `codex login`;
  na serwerze (`PANEL_LOGIN_WEB`) panel uruchamia `codex login --device-auth` jako agent i zwraca `{url, code}`:
  właściciel otwiera stronę OpenAI i wpisuje kod (wymaga włączonego logowania kodem urządzenia w ustawieniach
  bezpieczeństwa ChatGPT). Panel nie widzi haseł ani tokenów.
- Zadania `kto: codex` dostają zasadę: grafiki przez `$imagegen`, wynik jako `wariant-<n>.png` w folderze posta.
  Tak Claude (albo asystent) zleca grafikę bez panelu: zakłada zadanie `kto: codex`; z panelu ta sama trasa
  `/api/post/grafika-codex`.
- Klucz API zamiast subskrypcji (decyzja właściciela): `codex login --with-api-key` dla użytkownika agenta; wtedy
  generowanie idzie według cennika API. Panel niczego nie zmienia.

## Testy

`python3 -m unittest discover -s dashboard/testy` — uruchamianie na atrapie polecenia `claude` (bez sieci i bez limitu).
Gałąź uruchomienia, scalenie, diff, materiał z wyniku, `PANEL_AGENT_USER` i klucz lokalny: `testy/test_runda3_agenci.py`
(tymczasowe repozytorium git). Skutki pytań, licznik, kontrola serwera przy zadaniu, prompt (`skutek:`, `gotowe gdy`)
i odmowa scalenia z plikami sekretów: `testy/test_runda5_serwer.py` (atrapa w trybie `sekret`).
Rozmowa w projekcie (odnośnik do zadania i kontekst, te same narzędzia i zasady co Asystent, dawna historia zadania
do odczytu): `testy/test_czat.py`. Uruchamianie z rozmów (wiersze `Uruchom:`, `Polecenie:`, `Odpowiedź na pytanie:`,
`run_task` raz, kolejka przy zajętym agencie, blokady, „Wyślij i wykonaj”, stan w rozmowie, przycisk „Zapytaj o to
zadanie” w Chromium) i render HTML → PDF/PNG: `testy/test_czat_uruchamia.py`. Jedna rozmowa w panelu (brak czatu przy
zadaniu, uwaga ze Strony z załącznikiem, przyciski jednego działania przez `run_task`, układ 393 px jak iPhone 15):
`testy/test_jedna_rozmowa.py`.
Odbiór pracy (wersje po uruchomieniu, limit 20, wersja bieżąca, plik wersji i odmowa innych ścieżek, gałąź agenta,
poprawka ze znacznikami, odbiór całości i wariantów, `zmiany:`): `testy/test_odbior.py`.
Podgląd strony (pola karty, budowanie atrapą bez Node.js, `/podglad/`, uwaga → zadanie → scalenie i podgląd,
koncepcja, zrzut-strony.py pomijany bez Playwright): `testy/test_strona.py` (atrapa w trybach `strona`,
`strona-bez-zmian`). `GET /api/strona?project=`: `site`, `build` (`state` ok|building|error, `at`, `error`, `log`,
`version`), `url` (pusty bez podglądu), `notes`, `docs`, `widths`.
Praca na żywo (wiadomość na stdin, zamknięcie stdin po `result`, wiadomość po `result` jako poprawka i ponowne
uruchomienie, Zatrzymaj, bezpiecznik, kolejka, Codex i „Zatrzymaj i uruchom z poprawką”, przebieg i jego limity,
zrzuty bez wyjścia poza `.zrzuty/`, uwaga strony do pracującego agenta, reguły z `strona build:`, start od gałęzi
poprzedniego uruchomienia i z pola `gałąź:`): `testy/test_na_zywo.py` (atrapa w trybach `na-zywo`, `ignoruje`,
`po-wyniku`, `odmowa-w-trakcie`, `dlugi-tekst`, `zrzuty`, `wolno`).

## Widok Agenci i wybór wykonawcy

„Teraz” odświeża się co 3 sekundy. Karta pokazuje zadanie, projekt, komputer, upływ czasu,
trzy ostatnie wpisy i zużycie limitu 5 h, gdy strumień je podaje. Postęp pochodzi z listy Claude
(`TodoWrite`, `TaskCreate`, `TaskUpdate`) lub planu Codex (`todo_list`, zdarzenia planu). Gdy planu
brakuje, panel pokazuje kroki pod zadaniem, a bez kroków ostatnią czynność. Pasek liczy ukończone kroki.
„Przebieg na żywo” otwiera szczegóły uruchomienia. Pod kartami widać uruchomienia w kolejce, zadania
gotowe dla włączonego Automatu oraz zlecenia rozwoju czekające na start (patrz `ROZWOJ.md`).

`kto: agent`, `kto: claude` i `kto: codex` wskazują zadanie agenta. Panel pyta Claude Haiku o wykonawcę,
gdy oba narzędzia są zalogowane i poniżej progu Automatu. `wykonawca: tylko claude` lub `wykonawca: tylko codex`
przypina narzędzie. Po błędzie decyzji panel stosuje reguły lokalne. Decyzja i powód są zapisywane przy
uruchomieniu. Panel pamięta decyzję do końca dnia i przy ponowieniu sprawdza dostępność narzędzia.

Ostatnie odczyty okna 5 h i tygodnia trafiają do istniejącego `stan.json` wraz z czasem odczytu i odnowienia.
Źródła obejmują zdarzenia uruchomień panelu, logi zleceń rozwoju i pola limitów w sesjach Codex. Na serwerze
panel sprawdza najnowszą sesję konta `agent`. Katalog można wskazać przez `PANEL_CODEX_HOME`.
„Odczytaj limity” uruchamia krótkie próby obu narzędzi po kliknięciu. Po odnowieniu okna panel pokazuje
0% do następnego odczytu.

Szacunki czasu, tokenów i zużycia 5 h to mediany zakończonych uruchomień tego samego narzędzia i rodzaju.
Każda wielkość wymaga przynajmniej trzech odczytów. Ukończone kroki pozwalają skorygować szacunek trwającej pracy.
Godziny w kolejce uwzględniają przewidywany koniec uruchomień w toku oraz liczbę równoległych prac.
Raport PM korzysta z rejestru lub zbieracza i może uruchomić gotowe zadania agentów zgodnie ze standardem PM.
