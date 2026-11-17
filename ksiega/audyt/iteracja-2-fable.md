# Audyt księgi 0.2: iteracja 2, model Fable

Przegląd niezależny: audytor czytał tylko KSIEGA.md 0.2, bez wglądu w poprzednie audyty; fakty sprawdzał w internecie. 2026-11-12.

## Ocena ogólna
Spójna co do celu i kolejności; jako podstawa etapu 1: **tak po poprawkach**. Jedno ustalenie krytyczne (brak drogi Mac → PC w etapie 1), trzy wysokie: miejsce zadań, klasy danych, autoryzacja bota. Kryteria etapów 1 i 4 niemierzalne.

## Ustalenia
| # | Waga | Sekcja | Problem | Propozycja |
|---|---|---|---|---|
| 1 | krytyczna | 5, 6, 14 | Zbieracz Maca wysyła do serca, a Tailscale dopiero w etapie 2; Mac ma klon tylko do odczytu. | Tailscale do etapu 1 albo osobne repozytorium lub gałąź „skrzynka zdarzeń” Maca, którą PC pobiera. |
| 2 | wysoka | 5, 15, S8 | Nie wiadomo, gdzie żyją zadania: `pm.py` czyta `ZADANIA.md` w folderach projektów, a jedynym zapisującym jest PC; dwie prawdy. | Jedna reguła: zadania w repozytorium stanu albo projektu; opisać, kto zapisuje z Maca. |
| 3 | wysoka | 9, 5 | Klasy danych nie wymieniają GitHuba; S8 i pytania swobodne przesyłają treść wewnętrzną przez Telegram; link „w sieci prywatnej” nie działa w etapie 1. | Kolumna GitHub; wyjątek dla wiadomości wpisanych przez właściciela; pola zdarzenia dozwolone w repozytorium. |
| 4 | wysoka | 5, 8, 9 | Brak listy dozwolonych `chat_id`; od etapu 3 przyciski zatwierdzają scalenie i wysyłkę, więc przejęcie Telegrama = uprawnienia właściciela. | Jeden `chat_id`, reszta odrzucana i logowana; 2FA w Telegramie; drugie potwierdzenie dla scalenia i wdrożenia. |
| 5 | wysoka | 14 | „Poprawny stan”, „przechodzą testy” bez definicji; etap 4 kończy decyzja; 10 min dziennie bez pomiaru. | Lista kontrolna etapu 1: zgodność z ręcznym odczytem 3 projektów, świeżość ≤ X h, przypadki S1, S8, S10 z oczekiwanym wynikiem. |
| 6 | wysoka | 9, S10 | Sygnał życia nie wykrywa martwego bota, nieudanego push ani milczącego zbieracza Maca. | Ping po udanym cyklu (bot żyje, push udany); w raporcie „ostatnie zdarzenie z Maca starsze niż N h”. |
| 7 | średnia | 5 | Brak wymagań dla PC: start bez logowania, blokada uśpienia, Windows Update, zanik zasilania. | Dopisać do sekcji 9 i testu S10 (restart PC → bot wraca sam). |
| 8 | średnia | 9, 5 | Pytania z telefonu poza limitem = nieograniczone użycie modelu; warunki subskrypcji sprawdzane dopiero przed etapem 3. | Etap 1: S1 bez modelu; pytania swobodne z limitem i bez narzędzi zapisu; sprawdzenie warunków przed etapem 1. |
| 9 | średnia | 6 | Gmail: aplikacja OAuth w trybie „Testing” traci token po 7 dniach; `gmail.readonly` to zakres ograniczony. | Przed etapem 2 wybrać: IMAP z hasłem aplikacji, przekierowanie etykiety albo aplikacja „In production”. |
| 10 | średnia | 6, 7 | Sesje Claude Code to nieudokumentowany format, stare sesje są czyszczone; brak `id` dla sesji i folderów. | `id` dla każdego typu z etapu 1; zdarzenie „nie rozumiem pliku” przy zmianie formatu. |
| 11 | średnia | 7, 9 | Retencja w git nie usuwa historii; brak procedury usunięcia omyłkowo zapisanych danych poufnych i zachowania przy nieudanym push. | Retencja dotyczy drzewa roboczego; procedura usunięcia wpisu; push z ponowieniem i alarmem. |
| 12 | niska | 11, 14, 4 | P7 bez typów pilnych w etapie 1; „14 dni → backlog” zapełni backlog; BPMN dla 5 procesów to nadmiar. | P7 w etapie 1 tylko „system nie działa”; po 14 dniach archiwum; BPMN zastąpić tabelą kroków. |

## Brakujące scenariusze i przypadki brzegowe
- Mac uśpiony lub w podróży kilka dni: raport i znacznik świeżości.
- PC wraca po awarii: wiadomości z przerwy, zaległy raport, podwójne powiadomienia.
- Nieudany push (token, sieć); awaria dysku PC między zapisami.
- Dwa procesy na PC piszą jednocześnie.
- Wyciek tokenu bota albo GitHuba.
- Wiadomość od obcej osoby; bot dodany do grupy.
- Awaria Telegrama lub healthchecks.io: kanał zapasowy (e-mail).
- Zmiana czasu, inna strefa.
- Zmiana nazwy folderu bez zdalnego repozytorium.
- Pomysł bez projektu; wiadomość głosowa lub zdjęcie.
- Limit 5 pilnych wyczerpany, a przychodzi odbiór albo zlecenie.

## Sprawdzone fakty
- Tailscale Personal: bezpłatny; wg źródeł wtórnych tylko do użytku niekomercyjnego, co przy projektach dla klientów jest wątpliwe (strona Tailscale niesprawdzona bezpośrednio).
- healthchecks.io Hobbyist: 0 USD, 20 kontroli; Telegram jako integracja; próg 30 min osiągalny (healthchecks.io/faq).
- Telegram `getUpdates` (long polling) nie wymaga otwartego portu (core.telegram.org/bots/api); szyfrowanie end-to-end dla botów niepotwierdzone, przyjąć brak.
- `claude -p` na subskrypcji: Anthropic zapowiedział w 05.2026 osobny miesięczny kredyt na użycie programowe od 15.06.2026; źródła różnią się, czy weszło (support.claude.com, artykuł o Agent SDK z planem Claude).
- Gmail: token w trybie „Testing” wygasa po 7 dniach; `gmail.readonly` zakres ograniczony (dokumentacja Google).

## Pytania do właściciela
1. Czy treść zadań i tytuły zdarzeń mogą leżeć w prywatnym repozytorium GitHub?
2. Tailscale w etapie 1 czy transport przez git?
3. Czy projekty są komercyjne, dla klientów (plan Tailscale, klasa „poufne”)?
