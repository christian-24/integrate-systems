Jesteś na moim PC z Windows (profil Guest). Przygotowuję sprzedaż tego komputera: dane mają trafić na dysk zewnętrzny podłączony przez USB, a kod do moich prywatnych repozytoriów na GitHubie. Prowadź mnie krok po kroku, jedno pytanie naraz.

ZASADY BEZWZGLĘDNE
- Dysk zewnętrzny ma cenne dane. Zapisujesz WYŁĄCZNIE do nowego folderu `Migracja-PC-2026-11` w katalogu głównym tego dysku. Poza nim niczego nie czytasz, nie zmieniasz, nie usuwasz, nie przenosisz.
- Nigdzie niczego nie usuwasz, także na PC. Kopiujesz, nie przenosisz. Robocopy bez /MIR, /PURGE i /MOV; istniejących plików w folderze docelowym nie nadpisuj (/XC /XN /XO).
- Nie otwierasz plików .env, kluczy ani haseł. Kopiujesz je tylko na dysk, nigdy do repozytoriów.
- Commit, push, zakładanie repozytoriów: tylko po moim „tak” dla każdego repozytorium.
- Nie zmieniasz ustawień systemu, zapory ani Harmonogramu zadań.
- Pomijasz katalogi do odtworzenia: node_modules, .venv, venv, bin, obj, build, dist, .gradle, .dart_tool, __pycache__.

KROK 0: SPRAWDZENIE (bez kopiowania)
1. Znajdź dysk zewnętrzny (Get-Volume): litera, etykieta, system plików, rozmiar, wolne miejsce. Pokaż mi i poczekaj, aż potwierdzę, że to ten dysk.
2. Policz rozmiar każdej pozycji z listy niżej (bez katalogów do pominięcia) i pokaż tabelę: pozycja, rozmiar, czy mieści się. Poczekaj na moją decyzję, co kopiujemy.

KROK 1: KOD DO GITHUBA (każde repo osobno, po moim „tak”)
- `Desktop\generator-opisow-mebli` (Opisarnia), gałąź `feat/pokaz-opisarnia` z ok. 778 zmianami: commit „wip: pokaz (migracja z PC)” na tej gałęzi i push. Potem sprawdź worktree w `.claude\worktrees` i inne gałęzie: czy mają commity, których nie ma na origin; pokaż listę.
- `Desktop\CompanyAudits` (70 zmian, nieśledzone pliki): pokaż, co wejdzie do commitu (bez .env i sekretów), commit i push.
- `Desktop\oprogramowani-onepager\oprogramowani-onepager` (4 zmiany): commit i push.
- `Desktop\NaulikApp`: czy gałęzie `fix/rc1-nagrania` i `marketing/kampania-rc1` są na origin; jeśli nie, push.
- `Desktop\Warsztat`: tylko sprawdź niewypchnięte commity.
- Foldery bez git: `C:\Users\Guest\Zlecenia`, `Documents\ChatGPT\Zlecenia`, `Desktop\Reaserch`, `Plugins`, `claude-mods`. Zaproponuj podział na nowe prywatne repozytoria (asystent Useme, szukanie auta, LeadyV2, wtyczki Claude), z .gitignore na sekrety. Zakładamy je dopiero po mojej zgodzie.
- Pozostałe repozytoria ze zmianami (m.in. migracja-claude-code-kit, AdvanceStockBotTrading, GymInteligentApp, odys_frontend, UnDrown): tylko lista ze stanem; decyzję podejmę ja.
- Repozytoria pracodawcy (remote z organizacji pracodawcy, gałęzie KL2-DEV, ERP, cenniki, zatwierdzanie zamówień, Odys, JiraManager, XMLReplacementFiles): NIE pushujemy nigdzie. Tylko kopia na dysk do podfolderu `pracodawca`.

KROK 2: KOPIA NA DYSK (do `Migracja-PC-2026-11`)
Podfoldery:
- `projekty\` — wszystkie moje projekty z `Desktop`, `Documents`, `source\repos`, `AndroidStudioProjects`, `IdeaProjects`, `PycharmProjects`, `Downloads\CostLab`, `Downloads\OrderChecker`, `Zlecenia`, `Plugins`, `claude-mods`, `UnDrown` (z .git, bez katalogów do pominięcia)
- `pracodawca\` — repozytoria pracodawcy
- `claude\` — `C:\Users\Guest\.claude` (rozmowy, pamięć, ustawienia) i `C:\Users\Guest\.codex` bez `auth.json`
- `wsl\` — `\\wsl$\Ubuntu\home\claude\audyt-pc` (jeśli dostępne)
- `osobiste\` — Pulpit, Dokumenty, Obrazy, Pobrane poza tym, co już jest w `projekty\` — tylko jeśli potwierdzę w kroku 0
- Docker `E:\Docker\DockerDesktopWSL` — tylko jeśli potwierdzę (najpierw powiedz, co tam jest, na podstawie nazw i rozmiarów)
Kopiuj robocopy z logiem do `Migracja-PC-2026-11\logi\`.

KROK 3: SPRAWDZENIE I SPIS
- Dla każdej pozycji porównaj liczbę plików i rozmiar źródła i kopii; różnice pokaż.
- Zapisz `Migracja-PC-2026-11\SPIS.md`: pozycja, źródło, dokąd (dysk albo repo i gałąź), rozmiar, wynik sprawdzenia, czego nie skopiowano i dlaczego.
- Na koniec wklej mi cały SPIS.md w odpowiedzi.
