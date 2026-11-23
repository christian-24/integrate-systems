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
| `PANEL_AGENT_WORKTREE` | `1` | `0`: zadanie w repozytorium git bez gałęzi uruchomienia (praca w folderze projektu) |
| `PANEL_AGENT_USER` | brak | użytkownik systemu dla agentów; polecenie idzie przez `sudo -n -u <użytkownik> --` |
| `PANEL_LOKALNY_KLUCZ_PLIK` | brak | plik klucza zapisu dla żądań z tego komputera (nagłówek `X-Panel-Klucz`) |
| `PANEL_DZIEN_MIN` | `120` | dzienna pojemność właściciela w minutach (`dayMinutes` w `/api/data`) |
| `PANEL_ASYSTENT_MODEL` | `sonnet` | model asystenta (strona Asystent) |
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
`rytmDone`: publikacje, dla których powstało już zadanie wpisania wyniku). Serwer trzyma 200 ostatnich rekordów.
Po restarcie serwera uruchomienia `queued` i `running` dostają stan `stopped`.

### Polecenia

Prompt idzie przez stdin (bez problemów z cudzysłowami na Windows). Katalog roboczy: folder projektu, a dla zadania
w repozytorium git katalog roboczy gałęzi uruchomienia (niżej). Przy `PANEL_AGENT_USER` każde polecenie agenta
(zadanie, raport PM, plan, test połączenia, odczyt stanu logowania, logowanie przez panel) ma przedrostek
`["sudo", "-n", "-u", PANEL_AGENT_USER, "--"]`; bez zmiennej jak dotąd. Test połączenia i plan dnia działają wtedy
w katalogu tymczasowym systemu (agent nie musi mieć dostępu do `uruchomienia/`).

| Rodzaj | Polecenie |
|---|---|
| task, Claude | `claude -p --output-format stream-json --verbose --permission-mode acceptEdits [--model M] [--add-dir <folder karty>] --allowedTools "<lista>"`; w gałęzi uruchomienia `--add-dir` dla folderów `KARTA.md`, `ZADANIA.md`, `DECYZJE.md` i pliku zadania |
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
i wykonaj” w rozmowie o zadaniu), prompt ją podaje razem ze znacznikami (wiersze `- znacznik N (plik, położenie): uwaga`,
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

Polecenia git panelu działają bez haków repozytorium (`core.hooksPath` pusty) i bez podpisywania commitów.
Błąd git przy starcie (np. brak commita) nie blokuje zadania: praca idzie w folderze projektu, krok w rekordzie to opisuje.

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
  (domyślnie 20 punktów procentowych), panel zatrzymuje uruchomienie (stan `stopped`, `error` z powodem). Automat nie uruchamia
  nowych zadań, gdy ostatnio odczytane zużycie limitu 5 godzin ≥ `PANEL_AUTOMAT_DO_PROC` (domyślnie 80%), żeby zostawić resztę
  właścicielowi. `/api/data` → `agents.usage`: `{"five","seven","at","budget","reserve"}` (ułamki; `null`, gdy brak odczytu
  z ostatnich 5 godzin). Zadania, raport PM, rozmowy i Asystent mają `--disallowedTools` z pomocnikami, przepływami
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

`GET /api/agent/diff?id=<runId>`: `text/plain`, diff `baseCommit...branch` (najwyżej 200 KB, dłuższy obcięty z dopiskiem);
błąd jako JSON `{"ok": false, "error"}` z kodem 404 albo 409 jak przy scaleniu.
| `/api/agent/automat` | `{"enabled": bool}` | włącza i wyłącza Automat |
| `/api/strona/zbuduj` | `{"project"}` | budowanie podglądu strony w tle (gdy trwa: jeszcze raz po nim); 409 bez pola `strona:` |
| `/api/strona/uwaga` | `{"project", "text", "view": "telefon"\|"komputer", "page", "selector", "elementText"}` | zadanie agenta z uwagi i uruchomienie; odpowiedź `note`, `runId`; 400 bez tekstu |
| `/api/strona/koncepcja` | `{"project", "path", "text"?}` | zadanie „według koncepcji”; 400, gdy ścieżki nie ma w projekcie |
| `/api/project/add` | `{"path": folder, "name"?: nazwa, "files": bool}` | dopisuje istniejący folder do rejestru; `files: true` zakłada brakujące pliki standardu (niczego nie nadpisuje) |
| `/api/project/remove` | `{"id": projekt}` | usuwa z rejestru; pliki zostają |

Rozmowa o zadaniu (tylko odczyt; „Wyślij i wykonaj” w „Uruchamianie z rozmów”):
`POST /api/task/chat` z `{"id": taskId, "title": tytuł, "message": tekst}` (najwyżej 2000 znaków, treść żądania
do 32 KB) zapisuje pytanie i uruchamia w tle Claude; odpowiedź 202 `{"ok": true, "error": "", "pending": true}`;
400 pusta albo za długa wiadomość, 404 brak zadania, 409 zmieniony wiersz, poprzednia odpowiedź jeszcze trwa
(„Czekam jeszcze na odpowiedź.”), brak `claude`, wymagane logowanie, limit albo 3 rozmowy naraz.
`GET /api/task/chat?id=<taskId>`: `{"ok": true, "messages": [{"role": "ty"|"claude"|"panel", "text", "at"}], "pending": bool,
"error": str}`; 404 bez zadania. Historia (najwyżej 100 wiadomości, id sesji Claude) w
`uruchomienia/czat/<sha1 „projekt|plik|tytuł”>.json`.
Polecenie: `claude -p --output-format json --permission-mode default [--model M] [--resume <sesja>] [--add-dir …]
--allowedTools "Read,Grep,Glob,LS" --disallowedTools "Bash,Edit,MultiEdit,Write,NotebookEdit,WebFetch,WebSearch,Task"
--strict-mcp-config` w folderze projektu (prompt przez stdin, `sudo -n -u` jak przy zadaniach), limit 180 s. Pierwsza
wiadomość niesie kontekst zadania i zasady (krótko, po polsku, bez zmian w plikach, „Propozycja:” przy zbędnym albo
niejasnym zadaniu, bez próśb o hasła i klucze); kolejne idą przez `--resume` z samym pytaniem. Agent w rozmowie
niczego nie zmienia: bez powłoki, zapisu, sieci i serwerów MCP, także gdy `.claude/settings.json` projektu na nie pozwala.

### Uruchamianie z rozmów

Każda rozmowa może od razu uruchomić pracę agenta. Uruchamia zawsze serwer przez `run_task` (te same reguły co przycisk
„Uruchom”: `runBlock`, logowanie, limit, `PANEL_AGENTS_MAX`), nigdy model. Zadania z `wymaga: zgoda` czekają na
kliknięcie właściciela, `kto: ty` i publikacje nie ruszają, czaty nadal nie mają powłoki.

- **Rozmowa o zadaniu.** Obok „Wyślij” przycisk „Wyślij i wykonaj” (tylko przy zadaniu `kto: claude|codex`); to samo
  robi „zrób to”, „wykonaj” albo „wykonaj to” na końcu wiadomości (`EXEC_END`). `POST /api/task/chat` z
  `"execute": true`: bez modelu rozmowy panel zapisuje wiadomość pod zadaniem jako `poprawka:` (najwyżej 1000 znaków),
  zadanie `[x]`, `[~]` albo `[!]` wraca do `[ ]` (zdejmuje `blokada:` i `wymaga: odbiór`, `wymaga: zgoda` zostaje),
  potem `run_task`. Odpowiedź 200 `{"status": wiadomość panelu}`. Zadanie właściciela, publikacja i zadanie, nad którym
  agent już pracuje: plik bez zmian, tylko komunikat.
- **Rozmowa o projekcie** i **Asystent.** Prośba o pracę („zrób”, „przygotuj”, „napraw”…) to zadanie agenta w
  `ZADANIA.md` (`- [ ] Tytuł | kto: claude | kiedy: <dziś>` z `cel:` i `gotowe gdy:`; pasujące otwarte zadanie zamiast
  nowego) i na końcu odpowiedzi wiersz działania `Uruchom: <id projektu> | <dokładny tytuł>` (`take_run_lines`,
  najwyżej 3 w odpowiedzi; w rozmowie o projekcie projekt jest zawsze ten rozmowy, asystent przyjmuje też nazwę albo
  alias). Panel usuwa ten wiersz z odpowiedzi, szuka zadania po tytule (najpierw otwarte) i woła `run_task`. Pytanie
  o stan nie zakłada zadań i nie uruchamia.
- **Stan w rozmowie.** Po każdym uruchomieniu w historii jest wiadomość panelu (`role: "panel"`, nie od modelu):
  „Uruchomiono: …”, „W kolejce: agent pracuje nad „…”, to zadanie ruszy po nim.”, „Już w toku: …” albo „Nie uruchomiono
  „…”: powód.” (czeka na zgodę, po Twojej stronie, brak wykonawcy agenta, nie ma takiego zadania, logowanie, limit; przy
  logowaniu i limicie z dopiskiem, czy zadanie z dzisiejszą datą weźmie Automat). `GET` rozmów dokłada do takiej wiadomości
  `taskId` (link „Szczegóły”), `live` (stan uruchomienia) i `label` (w kolejce, w toku, do odbioru, zrobione, blokada,
  błąd…), liczone przy każdym odczycie; panel odświeża rozmowę co 5 s, dopóki coś jest w kolejce albo w toku.
- Zasady promptów rozmów mają wersję (`CHAT_RULES_V`); rozmowa zapisana z inną wersją zaczyna nową sesję z pełnym
  promptem, żeby dostała nowe zasady.

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
  Zapis i uruchomienie jak „Wyślij i wykonaj” (`chat_execute`, wpis w rozmowie o zadaniu); odpowiedź `{"status"}`.
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
(`assistant_facts`, z id zadań) i opis sterowania; kolejne tylko `[ekran: #adres; otwarte: …]` i nowe fakty, gdy dane
się zmieniły. Po restarcie panelu albo bezczynności proces startuje z `--resume`; nieznana sesja zaczyna rozmowę od nowa.
Odpowiedź może kończyć się wierszami działań, które panel wykonuje po kolei i ukrywa: `Pokaż: #adres`, `Otwórz: <id
zadania albo tytuł>`, `Przewiń: <nagłówek>`, `Zamknij: szczegóły` (w przeglądarce) i `Uruchom: <id projektu> | <tytuł>`
(na serwerze, „Uruchamianie z rozmów”).

Strona Asystent (`#asystent`, pierwsza w menu) to płótno kart i rozmowa (z boku od 1100 px, niżej przyklejona na dole).
Inne widoki nie mają okna asystenta; pytania ze Startu i spacja przechodzą na tę stronę. Model nie pisze HTML: kończy
odpowiedź blokiem ```` ```karty ```` z JSON `{"pokaz": [karta…], "usun": [id…]}`. Katalog typów (liczba, lista, tabela,
wykres, postep, tydzien, notatka, news), język zapytań i opis dla modelu: `dashboard/karty.py` (`PROMPT`). Panel
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
w panelu zakładkę „Strona”. Kod: `dashboard/strona.py` (`Manager.site`).

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
   Do HTML panel dopisuje w `<head>` skrypt trybu „Wskaż” (postMessage do panelu; panel przyjmuje wiadomości tylko
   z ramki zakładki).
3. **Uwaga.** „Wyślij agentowi” (`/api/strona/uwaga`) dopisuje do „Do rozplanowania” zadanie
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
   `wymaga: odbiór` (ocena w podglądzie) albo `[!]`. `--allowedTools` dostaje dodatkowo `Bash(npm ci:*)`,
   `Bash(npm install:*)`, `Bash(npm run build:*)` i `Bash(<polecenie zrzutu>:*)`. Polecenie zrzutu: `PANEL_ZRZUT`
   albo przy `PANEL_AGENT_USER` `/home/agent/narzedzia/pw/bin/python /usr/local/lib/integrate/zrzut-strony.py`
   (Python agenta z Playwright), bez niego `uruchom/serwer/zrzut-strony.py` (Python filmu albo `python3`).
   `.git/info/exclude` repozytorium dostaje `.zrzuty/`, `node_modules/` i `/<folder strony>/<wynik>/`, więc te
   pliki nie trafiają do commita gałęzi.
5. **Po uruchomieniu** (`Manager._finish` → `Site.after_run`): błąd agenta albo `[!]` → uwaga „nie wyszło” z powodem.
   Sukces na gałęzi uruchomienia: gałąź bez zmian w folderze strony → „nie wyszło”; inaczej panel scala ją
   (`/api/agent/merge`, lokalnie, bez push), buduje podgląd i zamyka zadanie (`[x]`). Bez gałęzi: samo budowanie.
   Uwaga „zrobione” dopiero po udanym budowaniu. Scalenie innej gałęzi, która zmieniła pliki strony, też przebudowuje
   podgląd.

Stany uwagi: `czeka` (w kolejce albo nieuruchomione), `pracuje` (agent albo scalenie i budowanie), `zrobione`,
`nie wyszło` (z jednym zdaniem powodu). Zrzuty przez MCP Playwright: nie, bo wymagają pakietów npm i osobnego procesu
w uruchomieniu; skrypt Pythona korzysta z Playwright, który jest już na serwerze, i daje agentowi plik PNG do Read.

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
Uruchamianie z rozmów (wiersz `Uruchom:`, `run_task` raz, kolejka przy zajętym agencie, blokady, „Wyślij i wykonaj”,
stan w rozmowie, przycisk w czacie zadania w Chromium) i render HTML → PDF/PNG: `testy/test_czat_uruchamia.py`.
Odbiór pracy (wersje po uruchomieniu, limit 20, wersja bieżąca, plik wersji i odmowa innych ścieżek, gałąź agenta,
poprawka ze znacznikami, odbiór całości i wariantów, `zmiany:`): `testy/test_odbior.py`.
Podgląd strony (pola karty, budowanie atrapą bez Node.js, `/podglad/`, uwaga → zadanie → scalenie i podgląd,
koncepcja, zrzut-strony.py pomijany bez Playwright): `testy/test_strona.py` (atrapa w trybach `strona`,
`strona-bez-zmian`). `GET /api/strona?project=`: `site`, `build` (`state` ok|building|error, `at`, `error`, `log`,
`version`), `url` (pusty bez podglądu), `notes`, `docs`, `widths`.
