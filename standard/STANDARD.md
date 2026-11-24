# Standard projektu

Każdy projekt ma ten sam zestaw plików, te same sekcje i jeden format wiersza zadania.
Dzięki temu panel, Claude Code i Codex czytają każdy projekt tak samo, a Ty wiesz, gdzie czego szukać.

## Pliki

| Plik | Do czego służy | Stałe sekcje |
|---|---|---|
| `KARTA.md` | Umowa z agentami: cel, zakres, zasady | Cel, Zakres, Poza zakresem, Definicja ukończenia, Zasady pracy agentów |
| `ZADANIA.md` | Jedyna lista zadań: etapy z terminami | `## Etap: nazwa` + `termin:`, `## Do rozplanowania` |
| `DECYZJE.md` | Dziennik decyzji | `## RRRR-MM-DD: tytuł`, najnowsze na górze |
| `README.md` | Wejście do projektu | Co to jest, Jak uruchomić, Struktura, Dokumentacja |
| `docs/ARCHITEKTURA.md` | Jak system jest zbudowany | Przegląd, Komponenty, Dane, Integracje |
| `docs/URUCHOMIENIE.md` | Uruchomienie, testy, wdrożenie | Wymagania, Uruchomienie lokalne, Testy, Wdrożenie |
| `CLAUDE.md`, `AGENTS.md` | Te same zasady dla Claude Code i Codex | blok „Standard projektu” |
| `kampanie/<nazwa>.md` | Jedna kampania w jednym pliku (opcjonalnie) | Grupa docelowa, Przekaz, Harmonogram, Wyniki i wnioski |

Sekcja z tekstem `_Do uzupełnienia…_` liczy się jako brak. Nazw sekcji nie zmieniamy.

Pod tytułem karty stoją pola (`- stan:`, `- faza:`, `- klient:`, `- próg:`, opis w `dashboard/README.md`) oraz
`- priorytet: 1–5`: 1 to projekt najważniejszy, brak wiersza = 3. Inna wartość jest brakiem karty. Priorytet ustala
kolejność spraw w raporcie PM i to, które zadania przesunąć, gdy dzień jest pełny (`priority` w danych projektu).
`- instagram: @profil` to profil Instagram projektu: panel sprawdza go przy „Udostępnij na Instagramie” i pokazuje
w podglądzie posta (`instagram` w danych projektu, bez @). Tak samo, opcjonalnie: `- tiktok: @profil` (profil TikTok,
bez @), `- facebook: Nazwa strony` i `- linkedin: Nazwa strony albo profilu` (nazwa jak na ekranie, do 100 znaków).
Rozszerzenie Chrome sprawdza je przy „Udostępnij na …” (`facebook`, `linkedin`, `tiktok` w danych projektu).
`- nagrywa: ty`: filmy projektu nagrywa właściciel według scenariusza nagrania (sekcja „Scenariusz nagrania”);
`panel` albo brak pola: film robi panel ze scenariusza filmu (`filmOwner` w danych projektu). `- nagrywa: ai`: filmy
robi właściciel w narzędziu AI według gotowych poleceń. Podział, np. `- nagrywa: panel 50, ai 40, ty 10`: Automat
przydziela każdemu filmowi sposób tak, żeby trzymać ten podział (`filmMix` w danych projektu; wybór zapisany w panelu).
Film „panel” robi studio panelu, filmy „ty” i „ai” dostają scenariusz.
`- strona: site`: projekt ma stronę WWW w tym folderze (względem folderu projektu, `.` to sam folder). Panel pokazuje
wtedy zakładkę „Strona”: podgląd, uwagi do agenta i zlecenie według koncepcji (`site` w danych projektu; opis
w `dashboard/AGENCI.md`, „Podgląd strony”). Opcjonalnie `- strona build: polecenie` (domyślnie
`npm ci && npm run build -- --base=./`, Vite ze ścieżkami względnymi) i `- strona wynik: folder` (względem folderu
strony, domyślnie `dist`). Ścieżka z `..`, z `/` na początku albo ze spacją jest brakiem karty. Bez pola `strona:`
projekt nie ma podglądu.
`- github: właściciel/repozytorium`: repozytorium projektu na GitHubie, źródło prawdy dla kodu (`github` w danych
projektu). Opcjonalnie `- github gałąź: nazwa` (gałąź bazowa klonu, domyślnie gałąź domyślna na GitHubie;
`githubBranch`). Kopia na serwerze jest potrzebna tylko na czas pracy: panel pokazuje jej stan względem GitHuba,
wysyła gałęzie na GitHub, usuwa kopię do kosza, gdy nic lokalnego nie zginie, i klonuje ją przed następnym zadaniem
agenta albo budowaniem podglądu (opis w `dashboard/AGENCI.md`, „Kopia projektu i GitHub”). Karta i zadania zostają
w IntegrateSystems (dowiązania w folderze projektu). Wartość, która nie jest `właściciel/repozytorium`, jest brakiem
karty. Pole `- repozytorium:` zostaje wolnym opisem.
`- część projektu: <projekt główny>`: ten projekt jest częścią innego (np. strona WWW projektu z integracjami).
Wartość to folder projektu głównego (np. `company-audits`; pasuje też nazwa folderu jego karty). Część zachowuje
swój folder, repozytorium, `ZADANIA.md` i agentów; panel i raport PM pokazują ją jako jeden projekt z projektem
głównym, a jej zadania podpisują „Projekt · Część”. Nazwa części to tytuł jej karty (np. `# Strona WWW`; przedrostek
z nazwą projektu głównego panel pomija). Wskazanie na nieistniejący projekt, na siebie albo na inną część jest
brakiem karty (`partOf`, `partLabel`, `parts` w danych projektu; opis w `dashboard/README.md`, „Projekt z częściami”).

Karta może mieć sekcję `## Pytania do właściciela` (lista `1. pytanie`, pod pytaniem `   Odpowiedź: …`); panel pokazuje ją jako sprawy do Ciebie.
Termin odpowiedzi: wcięty wiersz `   termin: RRRR-MM-DD` pod pytaniem albo „do RRRR-MM-DD” w treści pytania.
Agent może dopisać pod pytaniem swoją rekomendację: wcięty wiersz `   propozycja: …` (w danych `proposal`).
Propozycja nie jest odpowiedzią: pytanie czeka na Twoją `Odpowiedź:`.
Pytanie z wyborem ma pod sobą 2–4 wcięte wiersze `   opcja: …` (w danych `options`, lista tekstów w kolejności;
bez opcji `[]`): krótkie, wzajemnie wykluczające się odpowiedzi; `propozycja:` wskazuje wtedy jedną z nich.
Wybór opcji w panelu zapisuje `Odpowiedź:` równą tekstowi opcji (jak każda odpowiedź; opcja równa propozycji
działa jak jej przyjęcie).
Gdy propozycja zmienia zadania, pod nią stoją wcięte wiersze `   skutek: …` (w danych `effects`, lista tekstów),
po jednym na operację w `ZADANIA.md` tego projektu:

| Operacja | Działanie |
|---|---|
| `po: <fragment poprzednika> → <fragment tytułu>` | dopisuje fragment do pola `po:` zadania |
| `kiedy: RRRR-MM-DD → <fragment tytułu>` | zmienia `kiedy:` zadania |
| `stan: zrobione → <fragment tytułu>` | stan `[x]` |
| `stan: wstrzymane → <fragment tytułu>` | stan `[!]`, a bez blokady pole `blokada: wstrzymane: z pytania N, RRRR-MM-DD` |
| `nowe: <wiersz zadania bez stanu>` | nowe zadanie `- [ ] …` w „Do rozplanowania” |

Strzałka: `→` albo `->`. Zadanie wskazuje fragment tytułu bez wielkości liter: jedno otwarte zadanie, a gdy otwartego
nie ma, jedno dowolne; fragment pasujący do kilku zadań albo do żadnego to błąd tej operacji (pozostałe się wykonują).
Poprzednik w `po:` musi pasować do jakiegoś wiersza zadań projektu (najpierw tego samego pliku).

Przyjęcie propozycji w panelu zapisuje `Odpowiedź:` równą propozycji i wykonuje skutki; pod każdym zmienionym
(i nowym) zadaniem dopisuje notatkę `z pytania N, RRRR-MM-DD`. Odpowiedź o innej treści skutków nie wykonuje: panel
zakłada zadanie agenta „Zastosuj odpowiedź na pytanie N” (`kto: claude`, `kiedy:` dziś,
`materiał: KARTA.md#Pytania do właściciela`).

```
## Pytania do właściciela
1. Czy wstrzymać posty do potwierdzenia DPA?
   termin: 2026-11-21
   opcja: wstrzymać post 2 do potwierdzenia DPA
   opcja: publikować bez zmian
   propozycja: wstrzymać post 2 do potwierdzenia DPA
   skutek: po: potwierdź DPA → opublikuj post 2
   skutek: kiedy: 2026-11-23 → opublikuj post 2
   Odpowiedź: wstrzymać post 2 do potwierdzenia DPA
```

## Jeden format wiersza

Zadania w `ZADANIA.md` i publikacje w harmonogramie kampanii zapisujemy tak samo:

```
- [ ] Tytuł | kto: claude | gdzie: pc | kiedy: 2026-11-12 | pora: noc | czas: 30 | wymaga: zgoda
```

| Element | Wartości |
|---|---|
| stan | `[ ]` do zrobienia, `[~]` w toku, `[!]` zablokowane, `[x]` zrobione |
| `kto` | agent (panel wybiera Claude lub Codex), claude, codex, ty |
| `gdzie` | pc, mac, chmura |
| `kiedy` | data RRRR-MM-DD |
| `pora` | dzień, noc |
| `czas` | minuty Twojej pracy (np. `30` albo `1h 30`) |
| `wymaga` | zgoda (agent czeka na decyzję), odbiór (praca czeka na przegląd) |
| `blokada` | powód, przy stanie `[!]` |
| `kanał` | kanał publikacji, w kampaniach |
| `po` | fragmenty tytułów zadań tego projektu (po przecinku), które muszą być `[x]` wcześniej; najpierw z tego samego pliku |
| `sprawdza` | kontrola, która potwierdza wykonanie: klucz kontroli serwera (`kopia`, `kopia-poza`, `claude`, `claude-agent`, `zapis-kart`, `panel`, `useme`, `dysk`) albo `plik <ścieżka>` (plik w folderze projektu albo karty) |
| `licznik` | liczba podawana przy zamknięciu: zaproszenia, przyjęte, rozmowy, linki, konta, oferty, odpowiedzi |
| `kampania` | plik kampanii, do której trafia licznik (`kampanie/nazwa.md`, `nazwa.md` albo `nazwa`); bez pola: pierwsza kampania w toku |

Wszystkie pola są opcjonalne. Etap bez otwartych zadań jest zamknięty.
`wymaga` może mieć kilka wartości po przecinku (`wymaga: odbiór, zgoda`); każda z nich obowiązuje.
`po: makietę, zatwierdź teksty`: poprzednikiem jest pierwszy wiersz tego samego pliku, którego tytuł zawiera fragment
(bez wielkości liter). Gdy w tym pliku nie ma takiego wiersza, poprzednikiem jest pierwszy pasujący wiersz innego pliku
zadań tego projektu: najpierw `ZADANIA.md`, potem pliki kampanii w kolejności nazw (np. publikacja w kampanii z
`po: Potwierdź DPA` czeka na zadanie z `ZADANIA.md`). Dopóki któryś poprzednik nie jest `[x]` (albo fragment nie pasuje do żadnego wiersza),
zadania nie da się uruchomić („Czeka na: …”).
W drugą stronę każde zadanie ma w danych `unlocks` (`[{"id", "title", "executor", "date"}]`: otwarte zadania z `po:`
na nim, w kolejności wierszy) i `unlockCount` (ich liczba).

`sprawdza: kopia` (albo `sprawdza: plik docs/WDROZENIE.md`): w danych zadania `check` = `{"key", "ok", "at"}`
(bez pola `null`). `ok`: `true`, gdy kontrola serwera ma stan `ok` albo plik istnieje; `false` przy `zle`, `brak`
albo braku pliku; `null` bez stanu serwera (Mac, PC) albo przy nieznanym kluczu. `at`: czas kontroli (ISO).
Otwarte zadanie z `ok: true` nie trafia do „Dziś”; panel pokazuje „Wygląda na zrobione (…)” i „Zamknij”, które zapisuje
`[x]` i notatkę `zamknięte na podstawie kontroli serwera z RRRR-MM-DD HH:MM`.

`licznik: zaproszenia`: przy zamknięciu zadania podajesz liczbę; panel dopisuje w sekcji „Wyniki i wnioski” kampanii
wiersz `- RRRR-MM-DD · zaproszenia 8 · <tytuł zadania>` (sekcję zakłada, gdy jej brak, wiersz `_Do uzupełnienia…_` usuwa).

## Szczegóły zadania

Pod wierszem zadania (w `ZADANIA.md` i w harmonogramie kampanii) mogą stać wiersze wcięte o 2 spacje.
Należą do zadania nad nimi i kończą się na pierwszym wierszu bez wcięcia (także pustym).

```
- [ ] Wyślij zaproszenia LinkedIn do 8 firm z partii 1 | kto: ty | kiedy: 2026-11-19 | czas: 20 | licznik: zaproszenia
  cel: 8 zaproszeń do osób decyzyjnych w firmach z partii 1
  gotowe gdy: 8 zaproszeń wysłanych do osób z listy partii 1
  materiał: marketing/plan-10-kont.md#5
  - [ ] Kedameble
  - [ ] Bambooko
```

| Klucz | Znaczenie | Kto pisze |
|---|---|---|
| `cel:` | co ma powstać lub się zmienić, jedno zdanie | właściciel, PM |
| `gotowe gdy:` | sprawdzalny warunek ukończenia | właściciel, PM |
| `materiał:` | ścieżka względem folderu projektu, opcjonalnie `#5` (sekcja `## 5.`) albo `#Nagłówek`; może wystąpić kilka razy | właściciel, PM |
| `  - [ ] krok` | krok zadania; `[x]` zrobiony. Kroki nie są osobnymi zadaniami | wszyscy |
| `wynik:` | krótki wynik pracy | agent |
| `decyzja:` | co właściciel ma zatwierdzić przy odbiorze | agent |
| `zostało:` | czego nie zrobiono | agent |
| `poprawka:` | uwagi właściciela przy „Do poprawy”, ze strony odbioru („Popraw”) albo polecenie z „Wyślij i wykonaj” w rozmowie o zadaniu; agent wykonuje je i poprawia pracę | właściciel, panel |
| `  - znacznik N (plik, położenie): uwaga` | wiersze pod `poprawka:`: uwaga do miejsca na obrazie (`wizytowki/podglad.png, 34% od lewej, 60% od góry`) albo chwili filmu (`film/zapowiedz.mp4, 0:12`); najwyżej 12; nowa poprawka je zastępuje, agent ich nie zmienia | panel |
| `zmiany:` | po pracy z `poprawka:`: 2–3 krótkie zmiany rozdzielone `; `, przy każdej uwadze i znaczniku „zrobione” albo powód (`zmiany: tło granatowe; znacznik 1: zrobione`) | agent |
| `następne:` | jedna propozycja kolejnego zadania w formacie wiersza bez stanu: `Tytuł \| kto: … \| kiedy: …` | agent |
| `trwa: N dni` | notatka: zadanie trwa N dni od `kiedy` (raport PM liczy z tego zapas etapu) | właściciel, PM |
| `wyświetlenia:`, `kliknięcia:`, `konta:` | wynik publikacji, liczba całkowita (`1200` albo `1 200`) | właściciel, agent |
| `link:` | adres opublikowanego wpisu, `http://` albo `https://` | właściciel, agent |
| `gałąź:` | gałąź agenta `agent/…` do przejrzenia: panel pokazuje zmiany i „Scal”, scalenie zamyka zadanie | PM, agent |
| `pyta:` | pola formularza dla właściciela, rozdzielone `;` (np. `pyta: Imię w commitach; E-mail w commitach`); bez haseł i kluczy | PM, agent |
| `odpowiedź:` | `etykieta = wartość`, wiersz na pole; zapisuje panel z formularza `pyta:`, agent z `po:` na tym zadaniu dostaje je w poleceniu | panel |

Kroki zmienia się po kolejności (od 0, liczone tylko wiersze `- [ ]`/`- [x]` pod zadaniem).
Zadanie właściciela nie zawiera kroków technicznych (git, commit, konfiguracja, polecenia w terminalu): scalenie to `gałąź:` i przycisk w panelu, a potrzebne dane to `pyta:` i zadanie agenta z `po:` na tym zadaniu. `następne:` nie jest zadaniem: właściciel decyduje, czy je założyć. Każdy inny wcięty wiersz to notatka. Tytułu zadania agent nie zmienia; wynik zapisuje w szczegółach, nie w tytule.
Tytuł zaczyna się od czasownika („Wyślij”, „Przygotuj”) i ma najwyżej 120 znaków.

Wyniki publikacji (`wyświetlenia`, `kliknięcia`, `konta`, `link`) zapisuje się pod wierszem publikacji w harmonogramie
kampanii; w danych publikacji są w `detail` jako `views`, `clicks`, `accounts` (liczba albo `null`) i `link` (tekst).
Zła wartość zostaje notatką.

```
- [x] Post o ofercie | kanał: LinkedIn | kiedy: 2026-11-20 | kto: ty | czas: 15
  materiał: posty/2026-11-20-oferta/post.md
  wyświetlenia: 1 200
  kliknięcia: 34
  konta: 2
  link: https://www.linkedin.com/feed/update/…
```

Braki zgłaszane przy `ZADANIA.md` (`projekt.py sprawdz`, księga w panelu), najwyżej 5 przykładów w wierszu;
liczą się otwarte zadania z `ZADANIA.md` (bez publikacji):

| Brak | Reguła |
|---|---|
| bez `gotowe gdy` | zadanie w etapie z terminem bez `gotowe gdy:` |
| długi tytuł | tytuł dłuższy niż 120 znaków |
| tytuł nie zaczyna się od czasownika | pierwsze słowo to rzeczownik odczasownikowy („Wdrożenie…”, „Przygotowanie…”) |
| Twoje zadanie bez kroków i materiału | `kto: ty`, `kiedy` najpóźniej za 7 dni (także po terminie), bez kroków i bez `materiał:` |
| Twoje zadanie bez `czas` | `kto: ty` bez pola `czas` |
| zadanie agenta bez `kiedy` | `kto: agent`, `claude` albo `codex` w aktywnym projekcie, bez `kiedy`, poza sekcją „Do rozplanowania” |
| `wynik:` bez odbioru | stan `[ ]`, jest `wynik:`, nie ma `wymaga` (praca zrobiona, a zadanie wisi: zamknij albo daj do odbioru) |
| kampania bez celu liczbowego | kampania w stanie „w toku” bez pola `cel liczbowy` z liczbą |
| `sprawdza:` z nieznanym kluczem | klucz spoza listy kontroli serwera i nie `plik <ścieżka>` |
| słabe `gotowe gdy` | zawiera „albo w zostało” albo jest tylko wpisem do tabeli (słowa „tabel…” i „wpis…”, bez „i”, „oraz”, „a”, „;”) |

Braki zgłaszane przy `KARTA.md` z pytań bez odpowiedzi:

| Brak | Reguła |
|---|---|
| zły wiersz `skutek:` | operacja spoza listy albo zły zapis (brak strzałki, zła data, stan inny niż zrobione/wstrzymane) |
| zła liczba opcji | pod pytaniem bez odpowiedzi jest jeden wiersz `opcja:` albo więcej niż 4 |
| propozycja bez skutku | propozycja zawiera „wstrzymać”, „przesunąć”, „zamknąć” albo „dodać” (także formy „wstrzymaj”, „przesuń”, „zamknij”, „dodaj”), a pod pytaniem nie ma `skutek:` |

## Kampania

Pod tytułem pliku kampanii są pola: `stan` (plan, w toku, zakończona, wstrzymana), `cel`, `miernik`,
`cel liczbowy`, `wynik`, `kanały`, `start`, `koniec`, `budżet`. Publikacje to wiersze w sekcji Harmonogram.
`cel liczbowy` i `wynik` to liczby (pierwsza liczba w wierszu: „40 kont” → 40, „1 200” → 1200); w danych kampanii
`target` i `result` (liczba albo `null`). Kampania w toku powinna mieć `cel liczbowy`.
Sekcja „Wyniki i wnioski” jest wymagana dopiero po zakończeniu kampanii.

Wiersze `- RRRR-MM-DD · <licznik> <n> · <tytuł zadania>` w sekcji „Wyniki i wnioski” (dopisuje je panel przy zamknięciu
zadania z `licznik:`) dają w danych kampanii `counters` = `{licznik: suma}`; pozostałe wiersze to wnioski.
Gdy `miernik` to nazwa licznika (`- miernik: konta`), `result` to większa z liczb: ręczny `wynik:` albo suma tego
licznika (`resultManual`: sam ręczny wynik, `counterMetric`: nazwa licznika albo `""`).

```
## Wyniki i wnioski
- 2026-11-19 · zaproszenia 8 · Wyślij zaproszenia LinkedIn do 8 firm z partii 1
- 2026-11-21 · przyjęte 3 · Sprawdź przyjęte zaproszenia z partii 1
```

## Scenariusz nagrania

Film, który nagrywa właściciel (karta z `- nagrywa: ty`), ma scenariusz w pliku `scenariusz.md` w folderze posta
`posty/<dzień publikacji>-<nazwa>/` obok `KARTA.md`. Filmem jest publikacja ze słowem „film” (wideo, reel)
w tytule albo z kanałem Reels, TikTok, YouTube. Dzień nagrania: dzień przed publikacją, najwcześniej dziś.
Pole `- sposób:` mówi, kto robi film: `ty` (nagrywasz telefonem; „Co nagrać” to ujęcia), `ai` (robisz w narzędziu AI;
„Co nagrać” to gotowe polecenia scen do skopiowania, a ujęcia z prawdziwym produktem są oznaczone „nagraj telefonem”).

```
# Scenariusz nagrania: Miernik w akcji

- stan: propozycja
- publikacja: 2026-11-25
- nagranie: 2026-11-24
- sposób: ty

## Po co
Cel filmu i dla kogo.

## Co nagrać
- [ ] Zbliżenie na uszczelkę | 6 s
- [ ] Miernik przy obudowie, wynik na ekranie | 8 s

## Jak
- Miejsce, światło, kadr (telefon pionowo albo poziomo), rekwizyty

## Co powiedzieć
Tekst albo punkty.

## Na koniec
Wezwanie do działania.

## Gotowe gdy
Sprawdzalny warunek.
```

Stan: `propozycja` (pisze agent) → `do realizacji` (właściciel wysłał) → `nagrane`; cofnięcie do `propozycja`
z obu późniejszych. Stan zmienia panel. Ujęcie to wiersz `- [ ] opis | 5 s` (czas na końcu po `|`).
Zadania wokół scenariusza (w „Do rozplanowania”, tytuł z dniem publikacji):

| Zadanie | Kto | Kiedy powstaje |
|---|---|---|
| `Przygotuj scenariusz nagrania na <dzień>: <tytuł>` | claude | Automat dla filmów z publikacją w ciągu 7 dni bez pliku (raz); „Przygotuj scenariusz” w panelu |
| `Popraw scenariusz nagrania na <dzień>: <uwaga>` | claude | uwaga w rozmowie o scenariuszu (`poprawka:` z uwagą) |
| `Nagraj według scenariusza na <dzień>: <tytuł>` | ty, `kiedy:` dzień nagrania | „Wyślij do realizacji”; „Nagrane” zamyka je `[x]` |
| `Zrób film według scenariusza na <dzień>: <tytuł>` | claude | „Wyślij do realizacji” w projekcie bez `nagrywa: ty` |

## Raport PM

`python3 standard/pm.py` liczy raport z plików wszystkich projektów; panel liczy to samo w zakładce Raport.

| Pojęcie | Reguła |
|---|---|
| wymaga Ciebie | otwarte zadanie z `kto: ty` albo z polem `wymaga`, oraz pytanie bez odpowiedzi; bez projektów o stanie wstrzymany i backlog |
| zgoda na zadaniu właściciela | `wymaga: zgoda` przy `kto: ty` nie jest decyzją, tylko zwykłym zadaniem właściciela |
| dziś / 7 dni / później | `youToday`: po terminie (data przed dziś albo etap po terminie) albo data dziś, bez zadań czekających na niezrobionego poprzednika z `po:` i bez zadań do zamknięcia; `youLate`: ile z nich jest po terminie; `youWeek`: data w ciągu 7 dni (także czekające na poprzednika); `youLater`: później albo bez daty. Te same liczby pokazuje panel (menu Asystent, start, karty) i dostaje rozmowa z asystentem |
| po terminie | otwarte zadanie z datą wcześniejszą niż dziś albo w etapie po terminie (`late`: wszystkie, także agentów) |
| zablokowane | zadanie w stanie `[!]` |
| stan etapu | pierwsza pasująca: zrobione → po terminie → czeka na Ciebie (wszystkie otwarte zadania wymagają Ciebie) → zagrożony (otwartych zadań więcej niż dni do terminu) → w normie |
| bez następnego kroku | aktywny projekt bez otwartego zadania z datą najpóźniej za 7 dni |
| etap bez terminu | otwarty etap aktywnego projektu bez wiersza `termin:` |
| następny krok projektu | otwarte zadanie z najwcześniejszą datą, a bez dat pierwsze otwarte z polem `kto` |
| najważniejsze decyzje | 3 pierwsze sprawy dla Ciebie: po terminie, potem najbliższa data, zgoda, pytanie, odbiór, z czasem `czas:` w minutach |
| pytanie | otwarte pytanie z karty to decyzja rodzaju „pytanie”, 2 min; pytanie po terminie to ryzyko |
| kolejność | otwarte zadanie z `po:`, którego data jest wcześniejsza niż data niezrobionego poprzednika albo poprzednik nie ma daty |
| czeka na Ciebie | otwarte zadanie z `po:`, którego niezrobiony poprzednik ma `kto: ty`; raport grupuje po poprzedniku: jedno zadanie „· po Twoim zadaniu „…””, kilka „<poprzednik> wstrzymuje N zadań (najbliższe: …)” (`waitingOnYouBy`) |
| do zamknięcia | otwarte zadanie z `sprawdza:`, którego kontrola ma `ok: true` (`toClose`); takie zadanie nie trafia do „Dziś”. Stan serwera z `PANEL_ZDROWIE_STAN` (domyślnie `/home/panel/.zdrowie-stan`); bez pliku kontrole serwera są pomijane, `plik <ścieżka>` zostaje |
| kolejność „Dziś” i najważniejszych | po terminie najpierw (najstarsze), potem więcej odblokowanych zadań (`unlockCount`), potem priorytet projektu, potem data |
| zawieszone | `[~]` bez odbioru i bez pracującego agenta dłużej niż 3 dni (od zmiany stanu, zapis panelu w `uruchomienia/stan.json`) |
| odbiór czeka | otwarte zadanie z `wymaga: odbiór` dłużej niż 2 dni |
| priorytet | `- priorytet:` z karty (1–5, brak = 3); decyzje sortowane po priorytecie projektu, potem po dacie; „Dziś” i „Jutro”: po terminie, `unlockCount`, priorytet; najważniejsze decyzje: po terminie, `unlockCount`, priorytet, data, zgoda, pytanie, odbiór |
| bez zapasu | etap z terminem (nie po terminie, nie zrobiony), w którym najpóźniejszy koniec otwartego zadania z datą (`kiedy` plus dni z notatki `trwa: N dni`, a bez niej z „N dni” w tytule) wypada w dniu terminu albo później |
| ponad pojemność | suma `czas:` Twoich spraw na dziś (data najpóźniej dziś albo etap po terminie) większa niż `PANEL_DZIEN_MIN` (domyślnie 120 min); do przesunięcia zadania od najniższego priorytetu, aż suma się zmieści |
| propozycja | pytanie z wierszem `propozycja:` pokazane z „propozycja: …” |

Rola agenta, który raportuje, jest opisana w `standard/PM.md`. Notatki PM trafiają do `raporty/RRRR-MM-DD.md`.

## Uruchamianie z panelu

Panel uruchamia agenta dla jednego zadania; pełny opis w `dashboard/AGENCI.md`.

| Chwila | Wiersz zadania |
|---|---|
| start | stan `[~]`, `kto:` narzędzie, `gdzie:` komputer, na którym działa panel |
| koniec, agent skończył | `[x]` |
| koniec, praca do przeglądu | `[~]` i `wymaga: odbiór` (panel dopisuje pole, gdy agent zostawił samo `[~]`) |
| koniec, agent nie może iść dalej albo „gotowe gdy” nie jest spełnione | `[!]` i `blokada: powód` (bez `wymaga: odbiór`) |
| błąd, limit, zatrzymanie, przekroczony czas | panel przywraca `[ ]` |

Agent czyta szczegóły zadania (cel, gotowe gdy, materiały, kroki), odhacza wykonane kroki, a na koniec dopisuje pod
swoim wierszem `wynik:`, gdy trzeba `decyzja:` i `zostało:`; może dopisać jeden wiersz `następne:`. Przy wierszu
`poprawka:` poprawia pracę według niego (i według znaczników pod nim) i dopisuje `zmiany:`. Pytania do Ciebie dopisuje do sekcji „Pytania do właściciela” w `KARTA.md`
(z `   termin:`, gdy odpowiedź jest potrzebna do konkretnego dnia, z 2–3 wierszami `   opcja:`, gdy to pytanie
z wyborem, i z `   propozycja:`, gdy ma rekomendację; przy opcjach propozycja wskazuje jedną z nich).
Propozycja, która zmienia zadania (wstrzymać, przesunąć, zamknąć, dodać, kolejność), zawsze ma wiersze `   skutek:`
z operacjami z sekcji o pytaniach. Wiersza `gotowe gdy:` agent nie łagodzi: nie dopisuje „albo w zostało:”;
warunek niespełniony kończy zadanie stanem `[!]`.
Agent angażuje Cię tylko w sprawy, których nie rozstrzygnie nikt inny: pieniądze, dane prawne i firmowe, działania
nieodwracalne albo na zewnątrz, zakres i terminy, rzeczy fizyczne, fakty znane tylko Tobie. Najwyżej jedno otwarte
pytanie na projekt. Resztę rozstrzyga sam odwracalną opcją i zapisuje w `DECYZJE.md` (`- Kto: agent`). `wymaga: odbiór`
tylko dla pracy wychodzącej na zewnątrz, z `decyzja:` albo z kodem do scalenia; prace wewnętrzne kończy `[x]`.
W projekcie z repozytorium git panel zakłada osobny katalog roboczy (`<repo>/.agent/<id uruchomienia>`) na nowej gałęzi
`agent/RRRR-MM-DD-krotka-nazwa` od bieżącego stanu; agent pracuje tylko tam. Po zakończeniu panel zapisuje
niezacommitowane zmiany jednym lokalnym commitem na tej gałęzi (bez push), a scalenie do gałęzi bazowej następuje
dopiero na Twoje polecenie z panelu. Pliki wskazane w `wynik:` panel dopisuje jako `materiał:` do otwartych zadań,
które mają `po:` na tym zadaniu.

Zadanie nie startuje, gdy jest zrobione, ma `kto: ty` albo `zgoda` w polu `wymaga`, jest publikacją w kampanii,
ma niezrobionego poprzednika z `po:`, już pracuje albo należy do projektów przykładowych.
Zadanie bez pola `kto` uruchamia Claude. Automat bierze zadanie bez `gdzie:` na serwerze (węzeł domyślny).

## Polecenia

```
python3 standard/projekt.py nowy <folder> --nazwa "Nazwa" --rejestruj   # zakłada brakujące pliki, niczego nie nadpisuje
python3 standard/projekt.py kampania <folder> "Nazwa kampanii"
python3 standard/projekt.py sprawdz [<folder>]                          # raport braków; kod wyjścia 1, gdy są braki
python3 standard/projekt.py dodaj <folder> | usun <folder> | lista      # projekty widoczne w panelu
python3 standard/pm.py [--json]                                         # raport PM ze wszystkich projektów
```

W istniejącym projekcie `nowy` dopisuje tylko brakujące pliki, a do istniejących `CLAUDE.md` i `AGENTS.md` dokleja blok standardu.
Rejestr projektów panelu to `projekty.json` w folderze IntegrateSystems.
