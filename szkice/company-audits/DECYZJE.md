# Decyzje: Oprogramowani (integracje ERP ↔ sprzedaż)

Każda decyzja to osobny wpis, najnowsze na górze. Nagłówek wpisu: `## RRRR-MM-DD: krótki tytuł`.

> Uzupełnione danymi z PC (audyt 2026-11-14). Daty z plików, commitów i dokumentów.

## 2026-11-24: Przegląd drogi zamówienia: kształt arkusza i notatki
- Kontekst: zadanie „Przygotuj arkusz i wzór notatki bezpłatnego przeglądu drogi zamówienia” nie miało warunku „gotowe gdy”; zakres wzięty z marketing/formy-grudzien.md (forma A: arkusz 8 pytań, jednostronicowa notatka, zdanie do wiadomości, wpis na LinkedIn).
- Decyzja: (1) droga zamówienia ma sześć stałych przystanków: zamówienie przychodzi, zapis w biurze, materiał i stany, hala, wysyłka, faktura; nazwy da się zmienić w notatce; (2) jedyna liczba w notatce to godziny przepisywania w tygodniu: zamówienia w tygodniu × minuty ręcznego przepisywania na zamówienie ÷ 60, do pół godziny, z liczb rozmówcy; złotówek nie ma; (3) notatkę wypełnia właściciel w przeglądarce na swoim komputerze i sam zapisuje PDF, bo to dane klienta i nie mogą przechodzić przez agenta w chmurze; (4) notatka kończy się zdaniem „Co dalej” o audycie procesów, bez ceny i bez czasu trwania audytu; (5) podpis i kontakt jak na wizytówce (Krystian Stryjakiewicz, 663 206 373, kontakt@oprogramowani.com); (6) pliki leżą w repozytorium w przeglad-zamowienia/.
- Skutki: teksty i układ zmienia się w przeglad-zamowienia/zrodla/ i składa ponownie do PDF. Po pierwszych rozmowach pytania i przystanki warto poprawić według tego, co faktycznie padło.
- Kto: agent

## 2026-11-23: Wizytówka Oprogramowani: jeden wariant, format 89×59 mm
- Kontekst: trzecia poprawka właściciela: „tylko 1”, tekst „Łączymy…” z drugiego wariantu, „godzina na nas” zamienić na „8 lat doświadczenia”, format 89×59 mm do wgrania na stronie drukarni. Poprawka nie mówi, gdzie ma stanąć zdanie „Łączymy…” ani czym jest 89×59 mm.
- Decyzja: zostaje tylko wizytówka imienna Krystiana. Zdanie „Łączymy programy i automatyzujemy powtarzalne zadania” stoi pod nazwiskiem w miejscu roli „Procesy i rozmowa z klientem” (tam stało w wersji firmowej). Format 89×59 mm przyjęty jako wizytówka 85×55 mm ze spadem 2 mm z każdej strony; tekst 6 mm od linii cięcia. Hasło na przodzie bez zmian („Mniej ręcznej pracy w firmie.”), bo zwrot „Ty zajmujesz się firmą” zniknął już po drugiej poprawce. Plik 90×50 mm zostaje obok, bo wymaga go warunek zadania.
- Skutki: jeśli drukarnia chce innego spadu albo rola ma wrócić pod nazwisko, wystarczy zmiana w wizytowki/zrodla i ponowne złożenie plików. Liczba „8 lat” pochodzi od właściciela, w plikach projektu jej nie ma.
- Kto: agent

## 2026-11-23: Wizytówki Oprogramowani: hasło bez ERP
- Kontekst: poprawka właściciela do wizytówek: „za duża skłonność do ERP, a my przecież automatyzujemy i integrujemy”; zawężenie do ERP zamyka drogę do innych zleceń.
- Decyzja: z wizytówek znika słowo „ERP” i nazwy programów. Hasło na przodzie: „Automatyzujemy i integrujemy. Ty zajmujesz się firmą.”, podpis: „Automatyzacje i integracje dla firm”. Wersja firmowa na tyle: „Automatyzacje i integracje” oraz „Łączymy programy i zdejmujemy z ludzi ręczną robotę”. Wygląd i dane kontaktowe bez zmian.
- Skutki: hasło wizytówki różni się od nagłówka strony oprogramowani.com, która nadal mówi o zamówieniach i ERP; strony to zadanie nie zmienia. Teksty da się zmienić w wizytowki/zrodla/wizytowka.js.
- Kto: agent

## 2026-11-23: Wizytówki Oprogramowani: wygląd i źródło danych
- Kontekst: zadanie „Przygotuj projekt wizytówek Oprogramowani do weryfikacji”. Wskazany brief (strona-www/BRIEF_strona_www.md, maj 2026) opisuje dawny kierunek sprzed marki: kremowe tło, terakota, krój Fraunces. Obecna strona oprogramowani.com wygląda inaczej (Inter, biel i ciemne tło, czerwień #d93425, znak O·PRO·GRAMOWANI), a warunek zadania to spójność ze stroną. W plikach tego repozytorium dane kontaktowe są puste (`_data/firma.json`: „[DO USTALENIA]”).
- Decyzja: wygląd wizytówek wzięty z kodu obecnej strony (repozytorium oprogramowani-onepager), a nie z briefu. Dane kontaktowe też stamtąd: 663 206 373, kontakt@oprogramowani.com, Krystian Stryjakiewicz, rola „Procesy i rozmowa z klientem”. Powstały dwa warianty: imienna Krystiana i firmowa bez nazwiska. Wizytówki Pawła nie ma, bo w plikach brakuje jego nazwiska i numeru. Każdy wariant ma plik 90×50 mm i wersję ze spadami 3 mm.
- Skutki: do zmiany wystarczy poprawić teksty w wizytowki/zrodla/wizytowka.js i złożyć pliki ponownie. Druk dopiero po weryfikacji właściciela.
- Kto: agent

## 2026-11-21: Założenia robocze w miejsce luk „Do uzupełnienia” w karcie
- Kontekst: w karcie są trzy luki „Do uzupełnienia” (szkolenia z AI w ofercie; czy pilotaż u klienta 1 i zarejestrowana firma są warunkami ukończenia; termin końcowy, budżet, konta i usługi). To sprawy zakresu i pieniędzy, więc rozstrzyga je właściciel, ale agenci potrzebują ustaleń do bieżącej pracy.
- Decyzja: do czasu odpowiedzi właściciela (pytanie 8 w KARTA.md) agenci przyjmują: szkolenia z AI są poza ofertą; ukończenie to pierwszy płacący klient i opisany case, a pilotaż u klienta 1 i rejestracja firmy nie są warunkami; termin roboczy to koniec etapu „Walidacja rynku” (2026-12-18); budżet 0 zł poza kwotami z karty, każdy wydatek i każde nowe konto albo usługa wymaga zgody.
- Skutki: oferty i materiały marketingowe nie wspominają o szkoleniach z AI; agenci nie planują wydatków. Założenia są odwracalne: odpowiedź właściciela na pytanie 8 je zastępuje.
- Kto: agent

## 2026-11-21: Porządki spraw właściciela w zadaniach
- Kontekst: zadanie „Porządki spraw właściciela”; przegląd pytań w karcie i zadań kto: ty. Wszystkie 7 pytań w karcie miało już odpowiedź właściciela. W repozytoriach nie ma ani folderu Reaserch (lista LeadyV2), ani przykładowego e-maila Useme, więc agent nie zastąpi właściciela w tych dwóch sprawach.
- Decyzja: (1) drugi wiersz „Przygotuj arkusz i wzór notatki bezpłatnego przeglądu drogi zamówienia” zamknięty jako duplikat (zostaje wiersz z pytania 6, z polem gdzie: chmura); (2) w zadaniu „Zapisz przykładowy e-mail Useme…” właściciel tylko przekazuje e-mail (wkleja treść albo plik w rozmowie z Claude), a usunięcie danych osobowych i linków z tokenami oraz zapis w repozytorium robi agent; (3) w zadaniu „Wybierz 10 firm…” poprawiona notatka: wskazywała nieistniejące zadanie „Wgraj folder Reaserch (LeadyV2) na serwer”, a wgranie jest częścią zadania „Podłącz dysk z kopią PC do Maca”; (4) pozostałe zadania kto: ty zostają u właściciela, bo to rzecz fizyczna (dysk), wysyłka na zewnątrz (wiadomości, oferty), rozmowy z firmami i przyjęcie materiału do publikacji.
- Skutki: właścicielowi zostaje 6 zadań z czasem w minutach (łącznie 172 min) i jedno pytanie w karcie. Zmiany odwracalne: wystarczy przywrócić wiersze w ZADANIA.md.
- Kto: agent

## 2026-11-14: Jeden projekt Oprogramowani, D09 zatwierdzone
- Kontekst: odpowiedzi właściciela po audycie PC.
- Decyzja: company-audits, strona oprogramowani-onepager i zlecenia z Useme to jeden projekt Oprogramowani; forma działalności JDG + umowa o dzieło, sp. z o.o. później; kontakt z firmami z listy LeadyV2.
- Skutki: pilotaż u klienta 1 wstrzymany do czasu pozyskania klientów; rozmowy nowym kanałem.
- Kto: właściciel

## 2026-10-27: Plan na pierwszego klienta i zgoda pracodawcy
- Kontekst: 0 klientów i 0 zł do końca października; MAPA-I-STRATEGIA i OPROGRAMOWANI-BAZA-I-KIERUNEK.
- Decyzja: plan 4 tygodni od 28.10 (10 ofert, 3 rozmowy, 1 zlecenie); forma: JDG + umowa o dzieło, sp. z o.o. później (D09 otwarte). Pracodawca wyraził pełną zgodę na działalność.
- Skutki: cel to pierwszy płacący klient i opisany case.
- Kto: właściciel

## 2026-08-24: Marka „Oprogramowani”, integracje ERP ↔ sprzedaż
- Kontekst: same audyty dla firm meblarskich nie przyniosły klientów.
- Decyzja: oferta pod marką „Oprogramowani”: integracje ERP ↔ sprzedaż; strona oprogramowani.com jako lejek.
- Skutki: repo company-audits stoi od 01.06; praca przeniesiona do strategii i strony.
- Kto: właściciel i wspólnik

## 2026-06-08: Materiał o infrastrukturze IT bez wykonawstwa
- Kontekst: klient 2 chce uniezależnić domenę, pocztę i stronę od dotychczasowego dostawcy.
- Decyzja: przekazujemy nieodpłatny, niewiążący materiał z klauzulą; nie wykonujemy migracji i nie jesteśmy stroną sporu.
- Skutki: ewentualna odrębna oferta tylko na nową infrastrukturę. Klauzulę ma przejrzeć prawnik. _Do uzupełnienia: czy wysłano._
- Kto: właściciel i wspólnik

## 2026-06-01: MVP śledzenia zleceń dla klienta 1 jako krótki pilotaż
- Kontekst: klient 1 pyta o system śledzenia zleceń na produkcji; wycena 20–30 tys. zł za wysoka.
- Decyzja (rekomendacja narady, do potwierdzenia): pilotaż 2–3 tygodnie, QR na karcie zlecenia, telefony pracowników, jeden etap i jedna linia; domyślnie gotowy silnik (Prodio), własny system tylko gdy proces się nie mieści i jest opieka.
- Skutki: kryterium STOP: ponad 20% pominiętych skanów. RFID i lokalizacja magazynowa poza MVP.
- Kto: właściciel i wspólnik (narada agentów)

## 2026-05-26: Zamiar założenia sp. z o.o. i poinformowania pracodawcy
- Kontekst: obaj wspólnicy są zatrudnieni; brak zakazu konkurencji w umowach.
- Decyzja: informujemy pracodawcę przed założeniem spółki, niczego nie podpisujemy na miejscu; brief dla kancelarii i projekt umowy wspólników.
- Skutki: forma działalności (D09) nadal wymaga potwierdzenia u księgowej. _Do uzupełnienia: wynik rozmowy._
- Kto: właściciel i wspólnik

## 2026-05-25: Własny system śledzenia zleceń jako produkt
- Kontekst: plan produktu skanera produkcji.
- Decyzja: własny system (Flask, PostgreSQL, PWA) na licencji, wdrożenie jednorazowe plus abonament opieki, dwa pakiety (pilotaż, pełny), hosting i administracja jako opcje.
- Skutki: częściowo zmienione rekomendacją z 2026-06-01 (gotowy silnik u klienta 1).
- Kto: właściciel i wspólnik

## 2026-05-24: NDA bez zakazu konkurencji
- Kontekst: zakaz konkurencji blokowałby pracę dla innych firm z ~600 w okolicy.
- Decyzja: NDA chroni dane klienta (także przed trenowaniem AI) i wyłączność dzieła dedykowanego; wolno ponownie używać własnego know-how i ogólnych komponentów.
- Skutki: wyłączność tylko jako płatny dodatek. Kary 20–50 tys. zł, limit 200 tys. zł.
- Kto: wspólnik

## 2026-05-23: Analiza AI lokalnie, liczby ze wzoru
- Kontekst: AI w narzędziu audytu a poufność danych klienta.
- Decyzja: model lokalny przez Ollamę na Macu; AI ocenia jakościowo i uzupełnia reguły, kwoty i procenty liczy deterministyczny wzór.
- Skutki: dane klienta nie wychodzą z komputera.
- Kto: właściciel i wspólnik

## 2026-05-17: Rynek, model i cennik
- Kontekst: start działalności.
- Decyzja: firmy meblarskie 10–50 osób w powiecie kępińskim; lejek audyt → pilotaż → moduł → opieka; stawka 180–250 zł/h, domyślnie ryczałt; bez cen na pierwszym spotkaniu; w rozmowach „system”, nie „AI”; pierwsze 3–5 firm z rabatem 20–30%.
- Skutki: walidacja na pierwszych 3–5 klientach (cel: ponad 60% audytów przechodzi w pilotaż).
- Kto: właściciel i wspólnik
