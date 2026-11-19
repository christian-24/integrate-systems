# Opisarnia (generator opisów mebli)

- faza: marketing
- klient: nie
- próg: pełna
- priorytet: 1
- stan: aktywny
- maszyna: chmura
- repozytorium: serwer `~/projekty/generator-opisow-mebli` (GitHub, po migracji D13); wcześniej PC `C:\Users\Guest\Desktop\generator-opisow-mebli`

Szkic uzupełniony danymi z PC (audyt 2026-11-14, `szkice/AUDYT-PC-2026-11-14.md`). Od 21.06: 101 commitów na master (PR #60–#134),
ostatni commit 2026-11-05; w 14 dniach do 14.11: 38 commitów i 8 sesji Claude.
Odpowiedzi właściciela z 2026-11-14: produkcja aktualna (deploy #126–#134, silnik Haiku działa od 13.11), JDG w CEIDG, Stripe live działa.
Faza od 2026-11-14: marketing — promocja produktu i ocena zwrotu.

Karta jest umową między właścicielem a agentami pracującymi w tym projekcie. Agent czyta ją na początku każdej sesji.

## Cel
Opisarnia to narzędzie SaaS, które z ustrukturyzowanych atrybutów mebla generuje gotowe opisy produktowe po polsku i po niemiecku, dopasowane do wymogów marketplace'u (Allegro, Empik, Mirakl/XXXLutz). Jest przeznaczona dla polskich sprzedawców mebli, zwłaszcza eksportujących do Niemiec, i ma skrócić im czas wystawiania ofert oraz poprawić jakość opisów. Pierwszym celem jest walidacja popytu przez darmowy generator i listę mailową, a potem pierwszy płacący klient.

## Zakres
- Generator opisu PL i DE z atrybutów mebla, z profilem marketplace (ogólny, Allegro), edycją wyniku, kopiowaniem i eksportem CSV.
- Konto użytkownika: rejestracja z weryfikacją e-mail, logowanie (cookie httpOnly), onboarding, ustawienia, historia opisów (Centrum opisów).
- Limity: 1 darmowy opis dla anonima, limit planu dla zalogowanego, quota egzekwowana przed wywołaniem LLM.
- Płatności: Stripe Billing (subskrypcje, Customer Portal, webhooki), faktury lokalne z interfejsem pod KSeF; plany Free/Solo/Pro/Max (0/49/149/399 zł).
- Import katalogu (CSV/XLSX) z mapowaniem kolumn i generacja wsadowa (Celery), tabela wyników.
- RODO: retencja historii 90 dni, eksport i usunięcie konta, anonimizacja faktur.
- Warstwa LLM za jednym interfejsem `LLMProvider.generate(attrs, lang, marketplace)`; od 13.11 silnik Claude Haiku z zapasowym Mistralem (ADR 0045); harness ewaluacji i strojenia promptu offline.
- Eksport pod Allegro i ZIP, EAN/GTIN, korektor anty-halucynacyjny, landing z komodą 3D; analiza zdjęć ZDJ-1 za flagą.
- Marketing walidacyjny: posty LinkedIn (publikacja ręczna) i outreach wyłącznie do osób ze zgodą.

## Poza zakresem
- Wypychanie ofert przez API marketplace'ów (tylko eksport i kopiowanie).
- Analiza zdjęć i automatyczne atrybuty poza ZDJ-1 za flagą (ZDJ-5 tylko po decyzji „go”).
- Integracja z ERP i BaseLinkerem.
- Pełne mapowanie taksonomii kategorii Mirakla.
- Aplikacja natywna (tylko responsywny web).

## Definicja ukończenia
- Użytkownik wpisuje atrybuty i w mniej niż 10 s dostaje sensowny opis PL i DE, który kopiuje na Allegro (plan projektu, sekcja 1).
- Płaci, gdy przekroczy darmowy limit: płatność przez Stripe w trybie produkcyjnym działa.
- Aplikacja działa produkcyjnie na Hetzner (region DE) z HTTPS, monitoringiem błędów, monitoringiem dostępności i nocnym backupem z testem przywrócenia.
- Audyt bezpieczeństwa SEC-1..SEC-5 zamknięty (CRITICAL i HIGH naprawione) przed wejściem płacących użytkowników.
- Walidacja do 2026-12-23 (plan z 27.10, zastąpił bramkę 200 adresów z ADR 0001): 40 kont Free, 20 aktywnych, 3 płacących.
  Checkpoint 2026-11-30: przy mniej niż 10 kontach zmiana kanałów.

## Zasady pracy agentów
- Poziom swobody: 2 (agent pracuje sam, pyta przed operacjami ryzykownymi).
- Wymagają zgody właściciela: wdrożenie, publikacja, wysyłka wiadomości, migracja danych, `git push --force`, usuwanie danych, wydatki.
- Merge PR robi właściciel albo auto-merge przy zielonym CI; znalezisko CRITICAL z audytu bezpieczeństwa wymaga akceptacji właściciela przed mergem.
- Agent nie publikuje postów i nie wysyła maili; przygotowuje drafty. Mailing tylko do adresów z udokumentowaną zgodą (rejestr zgód).
- Twarde zasady techniczne z CLAUDE.md projektu: log generacji z kosztem per użytkownik, quota i limit długości wejścia przed wywołaniem LLM, brak sekretów w repo, provider LLM tylko za interfejsem, płatności tylko realnie przez Stripe.
- Posty marketingowe przygotowuje według STYL.md w folderze karty (stały rytm: post co 2 dni, kampanie/staly-rytm.md); publikuje właściciel po akceptacji.
- Stan pracy agent zapisuje w ZADANIA.md, decyzje w DECYZJE.md.

## Zasoby i ograniczenia
- Właściciel buduje solo, po godzinach; priorytet: szybkie MVP, walidacja, niskie koszty stałe.
- Usługi: GitHub (repo, CI), Hetzner Cloud CX22, Cloudflare DNS, Stripe (live), Anthropic API (Haiku), Mistral API (zapas), Sentry, UptimeRobot, OpenAI (tylko sędzia w ewaluacji offline), domena opisarnia.pl.
- Koszt stały szacowany w planie na ok. 800–1 100 zł/mc przy 80 płacących.
- Praca toczy się na PC; kopia na Macu wymaga `git pull`.
- Marketing: plan publikacji T1–T8 na 03.11–23.12; 10.11 zaplanowano 3 publikacje (LinkedIn, Facebook, Reels) i filmy o przejściu na modele Anthropic.
- JDG zarejestrowana, Stripe w trybie live (potwierdził właściciel 2026-11-14).
- _Do uzupełnienia: budżet na promocję._

## Pytania do właściciela
1. Czy przyjmujesz terminy etapów: deploy #126–#134 z kluczem Anthropic 17.11, test płatności za 2 zł 17.11, checkpoint 30.11, go/no-go 23.12, ZDJ-5 tylko po „go” w styczniu 2027?
   Odpowiedź: tak
2. Czy po 06.11 był deploy #126–#134 i czy backend produkcyjny ma klucz Anthropic (przełączenie silnika miało ruszyć 13.11)?
   Odpowiedź: tak i ruszylo
3. Czy JDG jest w CEIDG i czy Stripe działa w trybie live?
   Odpowiedź: Tak
4. Faza: zostaje „budowa”, czy przechodzimy na „utrzymanie + walidacja” (rekomendacja z 27.10)?
   Odpowiedź: Tak, powinnismy zarządzać marketingiem i może pójść w rozpromowanie produktu i jego potencjalny zwrot
5. Co jest w 778 niezacommitowanych zmianach na gałęzi `feat/pokaz-opisarnia` i czy ta gałąź ma trafić na origin?
   Odpowiedź: Pokaz to było nowy widok i poc, docelowo jeszcze będzie rozwijane ale nadal UI mnie się nie podobało wiec trzeba będzie to podrasować
6. Ile jest filmów, o czym są i gdzie leżą? Od tego zależy, czy film A (slot 20.11) trzeba nagrać od nowa.
   termin: 2026-11-19
   propozycja: nagrać film A od nowa według scenariusza zastępczego z planu (punkt 6), nagranie ekranu do 60 s; stare filmy przejrzeć dopiero przed filmem C (27.11)
   skutek: nowe: Przejrzyj stare filmy przed nagraniem filmu C | kto: ty | kiedy: 2026-11-26 | czas: 15
   Odpowiedź: nagrać film A od nowa według scenariusza zastępczego z planu (punkt 6), nagranie ekranu do 60 s; stare filmy przejrzeć dopiero przed filmem C (27.11)
7. Czy posty z planu T1–T8 (od 03.11) były publikowane, i które? Od tego zależy, czy posty 2–4 (23.11, 25.11, 27.11) nie powtarzają tematu.
   termin: 2026-11-22
   propozycja: sprawdzić na LinkedIn (profil → Aktywność → Posty) posty od 03.11; gdy żaden z tematów postów 2–4 nie wyszedł, zostawić posty 2–4 bez zmian
   Odpowiedź: byly wyslane
8. Ilu masz kontaktów na LinkedIn, w tym z branży meblowej? Od tego zależy, czy szacunek 2–4 kont z postów jest realny i czy rezerwę z planu (pkt 7) uruchomić wcześniej.
   termin: 2026-11-21
   propozycja: podać liczbę z LinkedIn (Moja sieć → Kontakty); rezerwę uruchomić według punktu 7 planu, czyli przy mniej niż 4 kontach Free 25.11
   Odpowiedź: z 4
9. Czy „konto aktywne” to konto z co najmniej 1 udaną generacją w ostatnich 14 dniach, czy okno 30 dni albo co najmniej 3 generacje? Od tego zależy liczenie celu 20 aktywnych w pomiarze.
   termin: 2026-11-22
   propozycja: co najmniej 1 udana generacja w ostatnich 14 dniach; tak liczy zapytanie z metryki.md (punkt 6, kolumna aktywne_14d)
   skutek: nowe: Oznacz definicję konta aktywnego w metryki.md jako przyjętą | kto: claude | gdzie: chmura | kiedy: 2026-11-23
   Odpowiedź: co najmniej 1 udana generacja w ostatnich 14 dniach; tak liczy zapytanie z metryki.md (punkt 6, kolumna aktywne_14d)
10. Czy 40 kont liczymy łącznie od początku, czy tylko konta założone od 2026-10-27? Od tego zależy pomiar w metryki.md i ocena checkpointu 30.11.
   termin: 2026-11-22
   propozycja: łącznie od początku, bez kont własnych i testowych; pomiar startowy 2026-11-18 to 0 kont, więc oba sposoby dają dziś ten sam wynik
   Odpowiedź: łącznie od początku, bez kont własnych i testowych; pomiar startowy 2026-11-18 to 0 kont, więc oba sposoby dają dziś ten sam wynik
11. Które identyfikatory kont są własne lub testowe i mają być wyłączone z liczenia? Od tego zależy zapytanie z metryki.md (pkt 6) w pomiarze 23.11.
   termin: 2026-11-22
   propozycja: podać identyfikatory raz (panel admina, lista użytkowników) i wpisać je do `ARRAY[...]` w metryki.md (punkt 6); nowe konta testowe zakładać na adres z domeny opisarnia.pl
   Odpowiedź: podać identyfikatory raz (panel admina, lista użytkowników) i wpisać je do `ARRAY[...]` w metryki.md (punkt 6); nowe konta testowe zakładać na adres z domeny opisarnia.pl
12. Liczby kanałów: ręcznie ze statystyk LinkedIn, Facebooka i Instagrama, czy parametr UTM i pole źródła przy rejestracji (osobne zadanie w kodzie)? Od tego zależy podział kont na kanały w decyzji 30.11.
   termin: 2026-11-21
   propozycja: do 30.11 ręcznie: wyniki ze statystyk LinkedIn, Facebooka i Instagrama pod wierszami publikacji w kampanie/staly-rytm.md (wyświetlenia, kliknięcia, konta); UTM i pole źródła jako zadanie dla Claude po checkpoincie 30.11
   skutek: nowe: Dodaj parametr UTM i pole źródła przy rejestracji | kto: claude | gdzie: chmura | kiedy: 2026-12-01
   Odpowiedź: do 30.11 ręcznie: wyniki ze statystyk LinkedIn, Facebooka i Instagrama pod wierszami publikacji w kampanie/staly-rytm.md (wyświetlenia, kliknięcia, konta); UTM i pole źródła jako zadanie dla Claude po checkpoincie 30.11
13. Post 1 (19.11), film A (20.11) i wiadomości do znajomych kierują ludzi do rejestracji, a DPA z Anthropic i Mistral oraz regulamin nie są potwierdzone (zadanie z terminem 17.11). Czy wstrzymać posty do potwierdzenia DPA?
   termin: 2026-11-19
   propozycja: wstrzymać posty i komentarze do potwierdzenia DPA; publikacje w kampanii i wiadomości mają już po: Potwierdź DPA, potwierdzenie zajmuje ok. 15 min, więc post 1 może wyjść jeszcze 19.11
   skutek: po: Potwierdź DPA → Odpowiedz na komentarze pod postem 1
   skutek: po: Potwierdź DPA → Odpowiedz na komentarze pod postami 2 i 3
   skutek: po: Potwierdź DPA → Napisz 5 komentarzy pod cudzymi postami
   Odpowiedź: wstrzymać posty i komentarze do potwierdzenia DPA; publikacje w kampanii i wiadomości mają już po: Potwierdź DPA, potwierdzenie zajmuje ok. 15 min, więc post 1 może wyjść jeszcze 19.11
14. Które formy marketingu (poza stałym rytmem i Reels) wchodzą na grudzień? Opis pięciu form i czterech wariantów: marketing/formy-grudzien.md. Od tego zależy, które wiersze trafią na oś czasu od 30.11.
   termin: 2026-11-30
   propozycja: wariant 2: darmowy przegląd opisu (A), grupy sprzedawców na Facebooku (C) i maile aktywacyjne do założonych kont (D); 0 zł wydatków, ok. 2 h tygodniowo ponad stały rytm; pozostałe wiersze z punktu 5 pliku dopisze agent po przyjęciu
   skutek: nowe: Przygotuj ogłoszenie, przypomnienie i szablony darmowego przeglądu opisu | kto: claude | gdzie: chmura | kiedy: 2026-11-30
   skutek: nowe: Wybierz 3–5 grup sprzedawców na Facebooku i przeczytaj regulaminy | kto: ty | kiedy: 2026-12-01 | czas: 30
   skutek: nowe: Przygotuj teksty 3 maili aktywacyjnych z oceną RODO | kto: claude | gdzie: chmura | kiedy: 2026-12-02
