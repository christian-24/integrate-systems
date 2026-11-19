# NaulikApp

- faza: budowa
- klient: nie
- próg: pełna
- priorytet: 1
- maszyna: chmura
- repozytorium: serwer `~/projekty/naulikapp` (GitHub, gałąź master, po migracji D13); keystore i podpisany build na Macu; wcześniej PC `C:\Users\Guest\Desktop\NaulikApp`

Szkic uzupełniony danymi z PC (audyt 2026-11-14, `szkice/AUDYT-PC-2026-11-14.md`). Własny produkt: własny biznesplan, repo i kampania.
RC1 1.0.0+2 zmergowany 2026-10-27 (#121/#122). Niezmergowane gałęzie: `fix/rc1-nagrania`, `marketing/kampania-rc1` (03.11).

Karta jest umową między właścicielem a agentami pracującymi w tym projekcie. Agent czyta ją na początku każdej sesji.

## Cel
NaulikApp to mobilny dziennik pokładowy dla polskich kapitanów małych i średnich jednostek: rybaków, żeglarzy, motorówek i jednostek roboczych. Aplikacja ma działać w trudnych warunkach na pokładzie (mokre ręce, ruch jednostki, słabe światło) i zapisywać rejsy, ruchy portowe i usterki w niezmiennym, podpisanym dzienniku z eksportem do PDF. Model sprzedaży to subskrypcja z darmowym planem demonstracyjnym z limitami.

## Zakres
- Aplikacja mobilna Flutter, dane lokalnie (Drift), działanie offline.
- v1.0.0 (MVP): fundament UI (motyw, tokeny, komponenty), jednostka, rejs, ruch portowy, usterki, onboarding, sealed log z PDF, limity Free Tier.
- Rdzeń 12 modułów opisany w `docs/architecture/` (M-00 do M-12, F1–F25, V1–V6); poza MVP: crew, position, map, engine, fuel, attachments, weather-observation, instruments.
- Moduły infrastrukturalne: sync, subskrypcja, logowanie OAuth Google/Apple, powiadomienia wewnętrzne, benchmarki zasobowe.
- Plan wersji: v1.1.0 (certyfikaty jednostki, statystyki), v2.0.0 (zgodność z prawem morskim), v3.0.0 (klient webowy), v4.0.0 (predyktor dryfu); przypisania wstępne.

## Poza zakresem
- Charter, floty i zarządzanie jachtami jako priorytet (F1: kierunek na przyszłość).
- Klient webowy przed v3.0.0.
- Synchronizacja danych w planie Free (F12: dane Free wyłącznie lokalne).
- Powiadomienia push systemowe (F7: tylko alarmy wewnętrzne).

## Definicja ukończenia
- v1.0.0 w Google Play: zamknięty test (12+ testerów × 14 dni) do 2026-12-13, w tym samym tygodniu wniosek o produkcję.
- iOS poza zakresem v1.
- Cel po wydaniu: 500 instalacji do 2027-04-30.
- _Do uzupełnienia: czy manualny plan testów TC-01..TC-20 jest warunkiem wydania._

## Zasady pracy agentów
- Poziom swobody: 2 (agent pracuje sam, pyta przed operacjami ryzykownymi).
- Wymagają zgody właściciela: wdrożenie, publikacja w sklepach, publikacja postów, wysyłka wiadomości, migracja danych, `git push --force`, usuwanie danych, wydatki.
- Stan pracy agent zapisuje w ZADANIA.md, decyzje w DECYZJE.md.
- Specyfikacja modułów w `docs/architecture/` jest źródłem prawdy; zmiany decyzji F/M tylko za zgodą właściciela.
- Rozmowa projektowa: jedno pytanie naraz, opcje A/B/C z rekomendacją (`docs/architecture/_collaboration-style.md`).

## Zasoby i ograniczenia
- Repozytorium git na GitHubie (konto właściciela), gałąź `master`; dotychczasowa praca przez PR i autopilota Claude Code (`naulikapp/.claude/`).
- Stan zadań w repo: `docs/backlog/STATUS.md` (ostatnia aktualizacja 2026-05-28).
- Ostatni commit w kopii na Macu: 2026-05-29. Zdalne `origin/master` ma nowsze commity i gałąź `docs/T48-backlog-tickets-from-audit`, których kopia na Macu nie ma.
- Blokery wydania: keystore, polityka prywatności, test akceptacyjny RC1, konto Google Play.
- _Do uzupełnienia: budżet, backend._

## Pytania do właściciela
1. T41 (ikony morskie, zablokowane od 16.05): eksportujesz SVG i generujemy `MarineIcons.ttf`, czy rezygnujemy na rzecz Material Symbols?
   Odpowiedź: Na rzecz materiał symbols
2. Czy gałęzie `fix/rc1-nagrania` i `marketing/kampania-rc1` mają być zmergowane przed zamkniętym testem?
   Odpowiedź: Może być ale to są branch marketingowe, tutaj możemy zastanowić się czy marketing powinien być na gicie
3. Czy konto Google Play i keystore już są, a 12 testerów zebranych (test ma trwać do 13.12)?
   Odpowiedź: Nie mam 12 testerów ale konto założone
4. Które zadania T48 (a/e/g/h/m/n/q/t/v/w) wchodzą przed wydaniem v1.0.0, a które po?
   Odpowiedź: Moze zrealizujmy wszystko niezbędne
5. Dane wydawcy do polityki prywatności NaulikApp i Play Console: nazwa wydawcy, adres, e-mail kontaktowy w sprawie danych?
   termin: 2026-11-21
   propozycja: dane działalności z CEIDG (nazwa i adres jak we wpisie) oraz osobny adres e-mail dla aplikacji, ten sam w polityce i w Play Console
   Odpowiedź: dane działalności z CEIDG (nazwa i adres jak we wpisie) oraz osobny adres e-mail dla aplikacji, ten sam w polityce i w Play Console
