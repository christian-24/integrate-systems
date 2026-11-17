# Uruchomienie etapu 1

Etap 1 według `ksiega/KSIEGA.md` (sekcja 14): zbieracz na Macu, serce z botem Telegram na PC, raport o 7:00, sygnał życia.
Kroki oznaczone **Ty** wykonujesz samodzielnie: logowania, tokeny i ustawienia systemu.

## 1. Repozytorium stanu na GitHubie (Ty, 2 min)

1. github.com → New repository → nazwa np. `stan-systemu`, **Private**, bez README.
2. Zapisz adres SSH albo HTTPS repozytorium. Mac i PC muszą mieć do niego dostęp (`git push` działa bez pytania o hasło).

## 2. Bot Telegram (Ty, 5 min)

1. W Telegramie: Ustawienia → Prywatność → Weryfikacja dwuetapowa: włącz.
2. Napisz do `@BotFather`: `/newbot`, podaj nazwę i login bota. Dostaniesz token — wpiszesz go tylko w `system.env` na PC.
3. Napisz do swojego bota dowolną wiadomość. Twój `chat_id` odczytasz na PC poleceniem z kroku 5.

## 3. Sygnał życia (Ty, 5 min, bezpłatnie)

Na healthchecks.io załóż konto i trzy kontrole:

| Kontrola | Okres | Tolerancja | Ustawienie |
|---|---|---|---|
| serce | 5 min | 10 min | `HC_SERCE` |
| zbieracz Maca | 1 h | 26 h | `HC_ZBIERACZ` |
| raport | 1 dzień | 1 h | `HC_RAPORT` |

W Integrations dodaj Telegram (HealthchecksBot) i e-mail jako kanał zapasowy.

## 4. Mac: zbieracz

1. `cp system/system.env.przyklad system/system.env` i uzupełnij `HC_ZBIERACZ`.
2. Klon repozytorium stanu:
   ```bash
   python3 system/zbieracz.py init <adres-repozytorium>
   ```
3. Sprawdzenie bez wysyłania (pokazuje tylko liczby):
   ```bash
   python3 system/zbieracz.py podglad
   ```
4. Kwalifikacja (P2): Backend i TestNow → „w realizacji”, Turtle → „backlog”, `klient` zgodnie z prawdą, alias, np. `Backend-A`. Pozostałych kandydatów na razie pomiń.
   ```bash
   python3 system/zbieracz.py kwalifikuj
   ```
5. **Ty:** Ustawienia systemowe → Prywatność i ochrona → Pełny dostęp do dysku → dodaj `python3` (ścieżkę pokaże skrypt instalacji). Bez tego zbieracz nie widzi części folderów i zgłasza „brak dostępu”.
6. **Ty:** uruchamianie co godzinę:
   ```bash
   bash system/uruchom/mac-zainstaluj.sh
   ```

## 5. PC: serce

1. Zainstaluj Python 3 i Git for Windows; skopiuj folder `IntegrateSystems` na PC (albo sklonuj).
2. `copy system\system.env.przyklad system\system.env`, uzupełnij `TELEGRAM_TOKEN`, `HC_SERCE`, `HC_RAPORT`.
3. Klon repozytorium stanu: `git clone <adres-repozytorium> %USERPROFILE%\stan-systemu`.
4. Odczyt `chat_id`: `python system\serce.py chat` (pokazuje identyfikatory czatów z ostatnich wiadomości do bota); wpisz go jako `TELEGRAM_CHAT`.
5. Próba: `python system\serce.py raz` — jeden cykl i odpowiedź na wiadomości. Napisz do bota `/stan`.
6. **Ty, PowerShell jako administrator:** `system\uruchom\windows-zainstaluj.ps1` — zadanie startujące serce bez logowania i wyłączone usypianie.

## 6. Sprawdzenie etapu

Przypadki testowe z danymi i oczekiwanym wynikiem: `system/testy/etap-1.md`. Etap jest ukończony, gdy przez 5 kolejnych dni roboczych raport 7:00 zgadza się z ręcznym odczytem i przychodzi bez Twojej interwencji, a wszystkie przypadki przechodzą.

## Awarie i bezpieczeństwo

| Sytuacja | Co robisz |
|---|---|
| Wyciek tokenu bota | `@BotFather` → `/revoke`, nowy token w `system.env` na PC, restart zadania |
| Wyciek dostępu do GitHuba | GitHub → Settings → SSH keys / tokens: usuń, utwórz nowy |
| Utrata telefonu | zakończ sesje Telegrama z innego urządzenia; wymień token bota |
| Utrata dysku PC | nowy PC: kroki z sekcji 5; stan wraca z GitHuba (`git clone`) |
| Test miesięczny | na Macu: `git clone <adres> /tmp/test-stanu`; sprawdź, że są `projekty.json`, `pomysly.md` i `mac/stan.json` z bieżącą datą (gałąź `mac`). Serca na Macu nie uruchamiaj: wypchnąłby zmiany na gałąź PC |
