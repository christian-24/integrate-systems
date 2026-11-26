# Decyzje: Oprogramowani (integracje ERP ↔ sprzedaż)

Każda decyzja to osobny wpis, najnowsze na górze. Nagłówek wpisu: `## RRRR-MM-DD: krótki tytuł`.

> Uzupełnione danymi z PC (audyt 2026-11-14). Daty z plików, commitów i dokumentów.

## 2026-11-27: Pokaz integracji: film na planszach i opis na jednej stronie
- Kontekst: zadanie „Przygotuj scenariusz filmu i jednostronicowy opis pokazu integracji” (forma B). Działającego demo nie ma (odpowiedź na pytanie 7), właściciel nie nagrywa filmów (decyzja 26.11, `nagrywa: panel`), od 26.11 obowiązuje strategia „Najpierw demo. Potem płacisz.”. Plansza końcowa w studio/marka.json mówi jeszcze „Na początek audyt procesów”.
- Decyzja: (1) film to objaśnienie z szablonu studia `porownanie-przed-po` (do 30 s, składa panel), bo pokaz jest schematem przed i po, a szablon `objasnienie-integracji` zostaje dla filmu serii z 1.12; (2) przykład: zamówienie z Allegro, 4 ręczne kroki zamiast 1 kroku zatwierdzenia, bez słowa „ERP” (uwaga właściciela z 23.11), bez liczb minut i złotówek; (3) opis A4 bierze obietnicę i 4 kroki współpracy ze strategii z 26.11, listę programów z linii „Integracje i dodatki”, z dopiskiem, że to przykład i termin ustalamy w wycenie; (4) studio/marka.json bez zmian, bo dotyczy wszystkich filmów; obietnica „demo” jest w opisie i w tekście posta; (5) publikacja 4.12 na LinkedIn jak w osi czasu form.
- Skutki: pliki posty/2026-12-04-film-pokaz-integracji/ i pokaz-integracji/ w repozytorium; teksty da się zmienić w scenariusz.json i opis-pokazu.html. Nic nie opublikowane ani nie wysłane.
- Kto: agent

## 2026-11-26: Plan marketingu na grudzień: podstrony, podział budżetu testu, karuzele
- Kontekst: zadanie „Przygotuj plan marketingowy według strategii z 26.11”. Strategia wymaga podstrony dla każdej frazy Google Ads, ale strona to jeden ekran bez podstron; budżet 300 zł czeka na właściciela; w karcie są otwarte pytania 8 i 9, więc nowego pytania nie zadaję.
- Decyzja: (1) adresy podstron: /planowanie-produkcji, /integracja-ksef, /makra-excel, /integracja-baselinker na oprogramowani.com; reklamy nie ruszają, dopóki podstrony nie działają; (2) 4 osobne kampanie po 5 zł dziennie (280 zł w 14 dni), 20 zł zapasu na przesunięcie po 7 dniach; (3) karuzele scenek zastępują 6 postów statycznych z kampanii w tych samych datach, bez nazw programów, firm i cen; szósta karuzela dotyczy linii IT i sprzęt; (4) zapytanie liczy się, gdy ktoś sam pisze albo dzwoni z prośbą o wycenę lub demo, kontakt lokalny to rozmowa z osobą decyzyjną albo wizyta z kartką; (5) telefon do firm oznaczony jako niesprawdzony prawnie, tak jak e-maile w strategii.
- Skutki: plik marketing-plan-2026-12.md; przebudowa strony musi dać cztery podstrony z formularzem; panel potrzebuje zadań z licznikami zapytania, kontakty, dema, zlecenia. Wszystko odwracalne, nic nie uruchomione.
- Kto: agent

## 2026-11-26: Strategia „Najpierw demo. Potem płacisz.” i cztery linie oferty
- Kontekst: od sierpnia integracje ERP dały 0 klientów; badanie rynku 26.11 (100 zleceń IT z Useme, 40 fraz z planera Google Ads) pokazało, że ludzie szukają funkcji („program do planowania produkcji”, „program magazynowy”, „ksef integracja”, „makra excel”), a nie „programu na zamówienie”, i że klienci sami proszą o działające demo.
- Decyzja (właściciel): przyjęta strategia z pliku strategia-2026-11-26.md: obietnica „Najpierw demo. Potem płacisz.”, cztery linie (planowanie produkcji; integracje i dodatki Optima/Subiekt/enova/BaseLinker/Allegro/KSeF; Excel bez ręcznej pracy; IT i sprzęt jako usługa uzupełniająca), bez ogólnego CRM, stron i aplikacji. Kontakt: kontakt@oprogramowani.com.
- Do decyzji: budżet testu Google Ads (propozycja 300 zł na 2 tygodnie); zakres karty bez zmian (IT i sprzęt tylko w strategii).
- Skutki: zadania dla agentów: plan marketingowy, przebudowa strony, wizytówka i kontakt (26.11).

## 2026-11-26: Marketing: posty statyczne zamiast filmów
- Kontekst: właściciel nie będzie nagrywał filmów; w kampanii „Pozyskanie klientów” było 6 filmów na 2–16.12 (decyzja z 24.11, podział z pola „nagrywa”) i ani jednego posta statycznego.
- Decyzja (właściciel): wszystkie 6 filmów zamienione na posty statyczne na LinkedIn i Facebook, te same tematy i daty; grafikę i tekst przygotowuje agent, właściciel zatwierdza i publikuje. W karcie `nagrywa: panel` (bez nagrań właściciela i narzędzia AI) i pole `marketing: posty statyczne`.
- Skutki: agenci planują posty statyczne, nie filmy. Scenariusz filmu z 2.12 przeniesiony do kopii (rozwoj/kopia-oprogramowani-2026-11-26).

## 2026-11-25: Strona: film w sekcji „Kto to robi”, kod zmieniony przed buildem
- Kontekst: poprawka właściciela „Zrób to” do zadania „Dodaj na stronie miejsca na zdjęcia, LinkedIn, dane firmy i film”. Agent znów nie miał uprawnień do `npm` (build, zrzuty) ani gita w repozytorium strony. W karcie jest otwarte pytanie, więc nowego nie zadaję.
- Decyzja: (1) zmieniam kod strony mimo braku builda (zmiana poprzedniej decyzji punkt 1), bo właściciel kazał to zrobić; zmiana jest mała i odwracalna, a na produkcję nie wyjdzie bez builda i obejrzenia; (2) film nie dostaje osobnej sekcji z tłem, tylko blok pod kartami osób w „Kto to robi”, żeby nie zmieniać rytmu jasnych i ciemnych sekcji na komputerze; (3) nagłówek „Poznaj nas, zanim zadzwonisz”, zdanie bez czasu trwania i bez obietnic; w DE, EN i IT dopisek, że film jest po polsku; napisy .vtt jako ścieżka „Polski”.
- Skutki: kolejne zadanie z uprawnieniami do `npm` buduje wersję roboczą, robi zrzuty 390 i 1440 px i zatwierdza zmianę w repozytorium strony. Produkcyjne `npm run build` nadal nie przejdzie bez 23 wymaganych pól w dane.js.
- Kto: agent

## 2026-11-25: Strona: miejsce na film jako pole opcjonalne, bez zmian w kodzie przed buildem
- Kontekst: zadanie „Dodaj na stronie miejsca na zdjęcia, LinkedIn, dane firmy i film”. Zdjęcia, LinkedIn, NIP, adres i link CEIDG mają już miejsca w kodzie strony (oprogramowani-onepager), brakuje sekcji filmu. Agent nie miał uprawnień do builda, zrzutów ani gita w repozytorium strony. W karcie jest otwarte pytanie 9, więc nowego pytania nie zadaję.
- Decyzja: (1) kodu strony nie zmieniam, dopóki nie da się go zbudować i obejrzeć, bo strona idzie na produkcję; (2) film to pole opcjonalne `DANE.film` (plik MP4, plakat, napisy .vtt z własnego serwera, bez YouTube, więc bez zmian w CSP), bez autoodtwarzania; bez pliku w produkcji sekcji nie ma; (3) plan zmian w strona-www/miejsca-wiarygodnosci.md.
- Skutki: kolejne zadanie z uprawnieniami do builda dopisuje sekcję filmu według planu. Produkcyjne `npm run build` i tak nie przejdzie, dopóki w dane.js brakuje 23 wymaganych pól (VAT, adres, ceny, gwarancja, RODO).
- Kto: agent

## 2026-11-24: Filmy na grudzień: 6 publikacji, podział 3 AI, 2 Ty, 1 panel
- Kontekst: zadanie „Zaplanuj filmy na grudzień według podziału z karty” (4–6 publikacji z filmem, podział „nagrywa: ai 50, ty 30, panel 20”). Kampania „Pozyskanie klientów” kończy się 8.12, a okno marketingu z marketing/formy-grudzien.md trwa do 18.12. W karcie jest otwarte pytanie 9, więc nowego pytania nie zadaję.
- Decyzja: (1) 6 filmów, bo tylko przy tej liczbie podział wychodzi w całych filmach: 3 AI, 2 Ty, 1 panel; (2) daty 2, 7, 9, 11, 14 i 16.12, poza dniami wpisów serii na LinkedIn (wtorki i czwartki) i poza filmami z zadań (1.12 i 4.12), pierwszy termin tak, żeby scenariusz powstał 7 dni wcześniej; (3) kolejność sposobów AI, Ty, panel, AI, Ty, AI, czyli taka, jaką panel sam wylicza z podziału karty przy pustej historii; planowany sposób jest zapisany w notatce pod każdą publikacją; (4) kanały: reels dla filmów AI i nagrania strony (4 filmy), linkedin dla nagrań telefonem (2 filmy), bo tam odbiorca sprawdza nadawcę; (5) nagrania telefonem pokazują tylko wydruki z przeglad-zamowienia/ (arkusz i przykład na zmyślonych danych), żadnych danych firm; (6) trzy filmy wychodzą po 8.12, daty końca kampanii nie zmieniam.
- Skutki: właściciel publikuje 6 filmów (po 15 min), z czego 3 robi w narzędziu AI i 2 nagrywa telefonem; czas nagrań panel doliczy przy scenariuszach. Jeśli panel przydzieli sposób inaczej niż w notatce (ma własną historię filmów), temat trzeba dopasować w scenariuszu albo zamienić daty dwóch publikacji. STYL.md mówi, że strona nie ma pokazu do nagrania; film z 9.12 to zwykłe przejście po stronie oprogramowani.com, nie pokaz integracji.
- Kto: agent

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
