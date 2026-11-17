# Przypadki testowe etapu 1

Na prawdziwym sprzęcie, po instalacji z `URUCHOMIENIE.md`. Wynik zapisuj w `ksiega/DZIENNIK.md`.

| # | Scenariusz | Dane wejściowe | Oczekiwany wynik |
|---|---|---|---|
| S1 | `/stan` wieczorem | 3 projekty zakwalifikowane; w `ZADANIA.md` Backendu ręcznie policz otwarte, czekające na Ciebie i po terminie | odpowiedź w 60 s; liczby zgodne z ręcznym odczytem; projekty klienckie tylko pod aliasem; na GitHubie (`git grep -i <prawdziwa nazwa>` w klonie stanu) brak trafień |
| S4 | nowy folder | `mkdir ~/test-s4 && cd ~/test-s4 && git init && git commit --allow-empty -m test` | w ciągu 2 h pracy Maca `python3 system/zbieracz.py kandydaci` pokazuje `test-s4`; w `mac/inwentarz.json` tylko alias |
| S8 | pomysł z telefonu | `/pomysl Test S8` | potwierdzenie z przyciskiem „Cofnij”; po cyklu wpis w `pomysly.md`; „Cofnij” usuwa wpis |
| S10a | bot zatrzymany, PC działa | zatrzymaj zadanie „IntegrateSystems serce” w Harmonogramie | w ciągu 30 min wiadomość z healthchecks (Telegram i e-mail) |
| S10b | PC wyłączony | wyłącz PC | jak S10a |
| S10c | push nieudany | na PC zmień adres zdalny repozytorium na błędny, poczekaj 2 cykle | wiadomość pilna o nieudanym wypchnięciu; po naprawie adresu kontrola wraca do normy |
| S10d | Mac milczy | Mac wyłączony przez 26 h | wiadomość z healthchecks dla zbieracza; raport pokazuje godzinę ostatnich danych z Maca i ostrzeżenie |
| S11 | obce konto | wiadomość do bota z drugiego konta Telegram | brak odpowiedzi; wpis w `dziennik.log` na PC |
| S12a | restart PC | restart bez logowania do Windows | bot odpowiada na `/stan` w ciągu 5 min; kontrola serca w normie |
| S12b | przestój > 24 h | PC wyłączony na 25 h | po starcie wiadomość o możliwej utracie wiadomości i jeden raport |
