# Zadania: Oprogramowani (integracje ERP ↔ sprzedaż)

> Jedyna lista zadań projektu. Czyta ją panel i agenci.
> Wiersz: `- [ ] Tytuł | kto: claude | gdzie: pc | kiedy: RRRR-MM-DD | pora: noc | czas: 30 | wymaga: zgoda`
> Stany: `[ ]` do zrobienia, `[~]` w toku, `[!]` zablokowane (dodaj `blokada: powód`), `[x]` zrobione.
> Pola są opcjonalne. kto: claude, codex, ty. gdzie: pc, mac, chmura. pora: dzień, noc. czas: minuty Twojej pracy. wymaga: zgoda, odbiór.
> Etap to nagłówek `## Etap: nazwa` i wiersz `termin: RRRR-MM-DD` pod nim. Etap bez otwartych zadań jest zamknięty.
> Szczegóły zadania: wcięte wiersze pod zadaniem (cel:, gotowe gdy:, materiał:, kroki `- [ ]`, wynik:, decyzja:, zostało:).

> Uzupełnione danymi z PC (audyt 2026-11-14). `[x]` tylko dla rzeczy widocznych w plikach lub dokumentach.

## Etap: Narzędzia i wiedza

- [x] Biblioteka wiedzy: research, branża, uzasadnienia, walidacja
- [x] Narzędzie audytu z backendem i raportem PDF
- [x] Lokalny model AI w audycie (propozycje, gotowość, analiza)
- [x] Dokumentacja systemu śledzenia zleceń (scanner/)
- [ ] Znajdź przyczynę błędu 502 w ocenie gotowości AI | kto: claude | gdzie: mac
  cel: ocena gotowości w narzędziu audytu zwraca wynik zamiast błędu 502
  gotowe gdy: ocena gotowości na przykładowym kwestionariuszu kończy się wynikiem, albo w wynik: opisana przyczyna i poprawka
  materiał: KARTA.md#Zasoby i ograniczenia
  Model lokalnie przez Ollamę na Macu (qwen3:14b), backend na localhost:5050; dlatego zadanie zostaje na Macu.

## Etap: Założenie firmy

- [x] Projekty umowy wspólników, NDA z klientem, umowy o dzieło i wdrożeniowej
- [x] Zgoda pracodawcy na działalność (dokument z 2026-10-27)
- [x] Forma działalności: JDG + umowa o dzieło, sp. z o.o. później (D09, 2026-11-14)
- [x] Nazwa marki: Oprogramowani (strategia 2026-08-24)

## Etap: Walidacja rynku
termin: 2026-12-18

- [x] Lista firm z danych publicznych: LeadyV2 ocenił 145 firm meblarskich (2026-09-02)
- [ ] Wgraj folder Reaserch (LeadyV2) na serwer | kto: ty | gdzie: mac | kiedy: 2026-11-20 | czas: 15
  cel: lista LeadyV2 dostępna dla agenta w folderze projektu na serwerze
  gotowe gdy: folder Reaserch z LeadyV2 leży w repozytorium projektu na serwerze, bez plików .env i kluczy
  materiał: KARTA.md#Zakres
  - [ ] na Macu, dysk zewnętrzny podłączony: `rsync -av --exclude '.env*' --exclude '*.key' --exclude '*.pem' "/Volumes/<dysk>/Migracja-PC-2026-11/projekty/Reaserch/" ops@2.29.181.133:/tmp/Reaserch/`
  - [ ] `ssh ops@2.29.181.133`, potem `sudo rsync -a /tmp/Reaserch/ /home/panel/projekty/company-audits/Reaserch/ && sudo chown -R panel:panel /home/panel/projekty/company-audits/Reaserch && rm -rf /tmp/Reaserch`
  - [ ] `sudo -u panel git -C /home/panel/projekty/company-audits add Reaserch && sudo -u panel git -C /home/panel/projekty/company-audits commit -m "Reaserch: lista LeadyV2"`
  Commit jest potrzebny, bo agent pracuje w osobnym katalogu uruchomienia od bieżącego commita i nie widzi plików niezacommitowanych.
  Źródło: dysk zewnętrzny, Migracja-PC-2026-11/projekty/Reaserch. Sekrety zostają poza repozytorium (ksiega/MIGRACJA.md).
- [ ] Wybierz 10 firm z listy LeadyV2 i przygotuj szkice wiadomości | kto: claude | gdzie: chmura | kiedy: 2026-11-21 | po: Wgraj folder Reaserch
  cel: 10 firm z listy LeadyV2 do pierwszego kontaktu, każda z uzasadnieniem wyboru i szkicem wiadomości
  gotowe gdy: w repozytorium projektu plik z 10 firmami (nazwa, powód wyboru, szkic pierwszej wiadomości); nic nie wysłane
  materiał: Reaserch/LeadyV2
  materiał: KARTA.md#Cel
  materiał: KARTA.md#Zasady pracy agentów
  Lista LeadyV2 jest dziś tylko w kopii PC: dysk zewnętrzny, Migracja-PC-2026-11/projekty/Reaserch.
  Zaczyna się po wgraniu folderu Reaserch na serwer (20.11). Gdy listy nadal nie ma w Reaserch/, agent oznacza [!] z blokadą „brak listy LeadyV2 na serwerze”.
  Wiadomość bez ceny; kontakt z firmami zatwierdzony 2026-11-14, wysyłka tylko przez właściciela.
- [ ] Napisz do 10 wybranych firm z listy LeadyV2 | kto: ty | kiedy: 2026-11-25 | czas: 30 | po: Wybierz 10 firm z listy LeadyV2
  cel: pierwsza wiadomość do 10 firm wysłana nowym kanałem właściciela
  gotowe gdy: 10 wiadomości wysłanych; data i kanał zapisane w notatce pod tym zadaniem
  materiał: KARTA.md#Zasady pracy agentów
  Szkice: wynik zadania „Wybierz 10 firm z listy LeadyV2 i przygotuj szkice wiadomości”. Oferta z ceną wymaga osobnej zgody.
- [x] Oferta na Useme: 2500 zł, 7 dni (bez odpowiedzi do 14.11)
- [x] Asystent Useme na serwerze: usługa, 188 testów, bez automatycznej wysyłki i komentarzy (2026-11-17)
- [x] Hasło do panelu zleceń: `ssh -t ops@2.29.181.133 sudo ustaw-haslo-zlecen` | kto: ty | czas: 2
- [ ] Zapisz przykładowy e-mail Useme o nowym zleceniu w repozytorium asystenta | kto: ty | czas: 5
  cel: agent ma wzór e-maila do napisania odczytu zleceń
  gotowe gdy: plik .eml z jednym e-mailem Useme o nowym zleceniu leży w repozytorium asystent-useme (np. w danych testowych)
  Przed zapisaniem usuń dane osobowe i linki z tokenami logowania.
- [ ] Napisz odczyt e-maili Useme na serwerze, który przekazuje zlecenia asystentowi | kto: claude | gdzie: chmura | po: Zapisz przykładowy e-mail Useme
  cel: nowe zlecenie z e-maila Useme trafia do asystenta bez ręcznego kopiowania
  gotowe gdy: test na przykładowym e-mailu przechodzi, a zlecenie pojawia się w kolejce asystenta; usługa niewdrożona bez zgody
  materiał: KARTA.md#Zakres
  Czeka na przykładowy e-mail od właściciela. Asystent działa bez automatycznej wysyłki ofert i komentarzy.
- [ ] Dodaj powiadomienie ntfy o nowym zleceniu z Useme | kto: claude | gdzie: chmura | po: Napisz odczyt e-maili Useme
  cel: właściciel dostaje powiadomienie ntfy, gdy odczyt e-maili znajdzie nowe zlecenie
  gotowe gdy: test wysyła jedno powiadomienie na każde nowe zlecenie i żadnego na powtórzone
  materiał: KARTA.md#Zakres
- [ ] Przenieś historię zleceń (data/jobs.db) z kopii PC na serwer | kto: claude | gdzie: chmura
  cel: historia zleceń z PC dostępna asystentowi Useme na serwerze
  gotowe gdy: data/jobs.db na serwerze ma tyle samo zleceń co kopia z PC; asystent czyta ją bez błędów
  materiał: KARTA.md#Zasady pracy agentów
  Migracja danych wymaga zgody właściciela. Jeśli pliku z kopii PC nie ma na serwerze, oznacz [!] z blokadą.
- [ ] Podsumuj skuteczność asystenta Useme | kto: claude | gdzie: chmura
  cel: wiadomo, ile ofert wysłano, ile dostało odpowiedź i dlaczego zlecenia odrzucano
  gotowe gdy: w wynik: liczby dla każdego kroku i jedno zdanie wniosku
  - [ ] wysłane oferty
  - [ ] odpowiedzi na oferty
  - [ ] odrzucone zlecenia i powody
  Liczy z data/jobs.db; bez historii z PC wynik obejmie tylko zlecenia z serwera.

## Etap: Pilotaż u klienta 1

- [x] Narada nad MVP śledzenia zleceń i lista pytań do firmy

## Do rozplanowania

- [x] Zebrać nowsze materiały z PC (audyt 2026-11-14)
- [x] Zacommitować nieśledzone pliki w CompanyAudits (commit „wip: migracja z PC”, 2026-11-16)
- [x] Część Useme w osobnym repozytorium asystent-useme (2026-11-16)
- [x] Strona oprogramowani.com, nowa wersja (2026-11-04)
