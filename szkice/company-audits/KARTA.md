# Oprogramowani (integracje ERP ↔ sprzedaż)

- faza: budowa
- klient: tak
- próg: pełna
- priorytet: 2
- stan: aktywny
- maszyna: chmura
- nagrywa: panel
- marketing: posty statyczne (grafika i tekst przygotowuje agent); bez filmów do nagrywania przez właściciela (decyzja 2026-11-26)
- repozytorium: serwer `~/projekty/company-audits` i `~/projekty/asystent-useme` (GitHub, po migracji D13); strona `oprogramowani-onepager` na GitHubie; wcześniej PC `C:\Users\Guest\Desktop\CompanyAudits`
- założono: 2026-05-17

Szkic uzupełniony danymi z PC (audyt 2026-11-14, `szkice/AUDYT-PC-2026-11-14.md`).
Od sierpnia kierunek zmienił się na markę „Oprogramowani”: integracje ERP ↔ sprzedaż (strategia 24.08, MAPA-I-STRATEGIA 27.10).
Dawna nazwa projektu: Audyty firm meblarskich. Strona oprogramowani-onepager i zlecenia z Useme należą do tego projektu (właściciel, 2026-11-14).
Stan na 2026-11-14: 0 klientów; pilotaż nie ruszył; oferta na Useme (2500 zł) bez odpowiedzi. Rozmowy z klientami będą prowadzone nowym kanałem.

Karta jest umową między właścicielem a agentami pracującymi w tym projekcie. Agent czyta ją na początku każdej sesji.

## Cel
Projekt to działalność konsultingowo-wdrożeniowa dla firm meblarskich zatrudniających 10–50 osób w powiecie kępińskim i okolicy (do 50 km), prowadzona przez właściciela ze wspólnikiem. Oferujemy audyt procesów jako niski próg wejścia, a potem pilotaż, moduły i stałą opiekę, rozliczane głównie ryczałtowo. Repozytorium zbiera narzędzia do audytu, bibliotekę wiedzy uzasadniającą ceny i umowy oraz materiały dla konkretnych klientów.

## Zakres
- Narzędzie audytu (kwestionariusz SPIN w 5 fazach, ocena bólu i gotowości, propozycje modułów, raport PDF) z backendem i lokalnym modelem AI.
- Biblioteka wiedzy: stawki i ceny rynkowe, klauzule umowne, specyfika branży, uzasadnienia decyzji, lista białych plam.
- Walidacja rynku: rozmowy z firmami, konsultacje u prawnika i księgowej.
- Założenie firmy: forma działalności, umowa wspólników, wzory NDA i umów z klientem, nazwa marki, strona www.
- Produkt śledzenia zleceń na produkcji (skan QR, etap procesu, tablica właściciela) i pilotaż u klienta 1.
- Materiały dla klientów (folder `klienci/`, wnioski z narad nad MVP).
- Marka „Oprogramowani”: strona oprogramowani.com jako lejek usług integracji ERP ↔ sprzedaż.
- Zlecenia z Useme i grup na Facebooku: asystent w `C:\Users\Guest\Zlecenia` sprawdza Useme co 10 min (7–22), AI pisze ofertę, a model weryfikator wysyła ją automatycznie (do 3 dziennie; powyżej 10 000 zł decyduje właściciel). Komentarze jako strona Oprogramowani w grupach FB. Wynik do 04.11: 114 zleceń w 3 dni, 12 po filtrze, 6 ofert wysłanych; odpowiedzi: brak.
- Lista firm: LeadyV2 ocenił 145 firm meblarskich (z CEIDG i KRS); kontakt z nimi zatwierdzony 2026-11-14.

## Poza zakresem
- Migracje i prace na cudzej infrastrukturze IT oraz udział w sporach o domeny i hosting.
- RFID, bramki i adresowany magazyn w pierwszej wersji śledzenia zleceń.
- Zakaz konkurencji wobec innych firm z branży (tylko jako osobny płatny dodatek).
- Podawanie cen na pierwszym spotkaniu.
- _Do uzupełnienia: czy szkolenia z AI dla firm (jak w repo Presentation) należą do oferty._

## Definicja ukończenia
- Pierwszy płacący klient i opisany case.
- Plan 4 tygodni od 28.10 (do ok. 24.11): 10 ofert, 3 rozmowy, 1 zlecenie.
- Po 3 miesiącach: 40 ofert, 15 rozmów, 3–4 zlecenia, 1 case.
- _Do uzupełnienia: czy pilotaż u klienta 1 i zarejestrowana firma są warunkami ukończenia._

## Zasady pracy agentów
- Poziom swobody: 2 (agent pracuje sam, pyta przed operacjami ryzykownymi).
- Wymagają zgody właściciela: wdrożenie, publikacja, wysyłka wiadomości, migracja danych, `git push --force`, usuwanie danych, wydatki.
- Dodatkowo wymagają zgody: każdy kontakt z klientem, oferta z ceną, podpisanie lub wysłanie umowy.
- Dane klientów są poufne: nie trafiają do usług zewnętrznych; analiza AI działa lokalnie. W raportach i panelu klientów oznaczamy jako „klient 1”, „klient 2”.
- Twierdzenia w dokumentacji oznaczamy: [FAKT], [INTERPRETACJA], [OPINIA], [DO USTALENIA]. Kwot w raporcie dla klienta nie wymyśla model; liczy je wzór.
- Stan pracy agent zapisuje w ZADANIA.md, decyzje w DECYZJE.md.

## Zasoby i ograniczenia
- Stawka 180–250 zł/h netto (domyślnie 220), audyt 3–5 tys. zł, opieka 3–5 tys. zł/mies.; pierwsze 3–5 firm z rabatem 20–30%.
- Budżet na radcę prawnego IT: 2000–3500 zł.
- Model AI lokalnie przez Ollamę na Macu (qwen3:14b); backend na localhost:5050.
- Pracodawca wyraził pełną zgodę na działalność (dokument z 27.10).
- Forma działalności: JDG + umowa o dzieło, sp. z o.o. później (D09 zatwierdzone 2026-11-14).
- _Do uzupełnienia: termin końcowy, budżet całkowity, konta i usługi, z których wolno korzystać._

## Pytania do właściciela
1. Czy projekt zmieniamy na „Oprogramowani” (integracje ERP ↔ sprzedaż) i strona oprogramowani-onepager ma być jego częścią, czy osobnym projektem?
   Odpowiedź: To samo jest\
2. Pilotaż u klienta 1: własna prosta apka z kodami QR (1,5–4 tys. zł, zalecenie z 01.06) czy Prodio z wdrożeniem (27.10)?
   Odpowiedź: Nic nie trafiło się, nadal musimy znalesc klientow
3. Forma działalności (D09): JDG + umowa o dzieło teraz, sp. z o.o. później — zatwierdzasz?
   Odpowiedź: zatwierdzam\
4. Jaki jest postęp planu 4 tygodni od 28.10 (oferty, rozmowy, zlecenia) i czy materiał o infrastrukturze IT został wysłany?
   Odpowiedź: nie, ale docelowo znalazłem kolejna możliwość komunikacji z klientem, rozmowy będą przeprowadzone w innym miejscu
5. Czy kontaktujemy się z firmami z listy LeadyV2 (145 ocenionych) i od których zacząć?
   Odpowiedź: Tak, będziemy
6. Które formy marketingu (poza Reels) wchodzą na grudzień? Opis pięciu form i czterech wariantów: marketing/formy-grudzien.md. Od tego zależy, które wiersze trafią na oś czasu od 24.11.
   termin: 2026-11-23
   propozycja: wariant 2, czyli formy A, B i C: bezpłatny 30-minutowy przegląd drogi zamówienia, pokaz integracji z jednostronicowym opisem, seria 6 wpisów na LinkedIn „Gdzie ginie zamówienie”; 0 zł, ok. 1,5 h tygodniowo
   skutek: nowe: Przygotuj arkusz i wzór notatki bezpłatnego przeglądu drogi zamówienia | kto: claude | gdzie: chmura | kiedy: 2026-11-24
   skutek: nowe: Przygotuj scenariusz filmu i jednostronicowy opis pokazu integracji | kto: claude | gdzie: chmura | kiedy: 2026-11-27
   skutek: nowe: Przygotuj 3 wpisy serii „Gdzie ginie zamówienie” (1–8.12) i scenariusz filmu objaśniającego | kto: claude | gdzie: chmura | kiedy: 2026-11-30
   skutek: nowe: Przyjmij film i opis pokazu integracji | kto: ty | kiedy: 2026-12-02 | czas: 45
   skutek: nowe: Przygotuj 3 wpisy serii „Gdzie ginie zamówienie” (10–17.12) z surowca po rozmowach | kto: claude | gdzie: chmura | kiedy: 2026-12-07
   Odpowiedź: wariant 2, czyli formy A, B i C: bezpłatny 30-minutowy przegląd drogi zamówienia, pokaz integracji z jednostronicowym opisem, seria 6 wpisów na LinkedIn „Gdzie ginie zamówienie”; 0 zł, ok. 1,5 h tygodniowo
7. Czy istnieje działające demo integracji ERP ↔ sprzedaż (np. zamówienie z Allegro albo BaseLinkera trafia do programu magazynowego), które studio może nagrać jako pokaz, i gdzie leży? Bez demo film z formy B powstanie jako objaśnienie na planszach.
   termin: 2026-11-26
   propozycja: jeśli demo nie ma, zacząć od objaśnienia na planszach, a przykład na zmyślonych danych zbudować w osobnym zadaniu po pierwszych rozmowach
   Odpowiedź: jeśli demo nie ma, zacząć od objaśnienia na planszach, a przykład na zmyślonych danych zbudować w osobnym zadaniu po pierwszych rozmowach
8. Czy przyjmujesz założenia robocze w miejsce trzech luk „Do uzupełnienia” w karcie: (a) szkolenia z AI są poza ofertą, (b) ukończenie to pierwszy płacący klient i opisany case, bez warunku pilotażu u klienta 1 i rejestracji firmy, (c) budżet 0 zł poza kwotami z karty, każdy wydatek i nowe konto za Twoją zgodą, termin roboczy 2026-12-18? Jeśli któryś punkt ma być inny, napisz który i jak.
   termin: 2026-11-28
   propozycja: przyjąć wszystkie trzy założenia (a, b, c); agenci już według nich pracują (DECYZJE.md, 2026-11-21)
   Odpowiedź: przyjąć wszystkie trzy założenia (a, b, c); agenci już według nich pracują (DECYZJE.md, 2026-11-21)
9. Wizytówki: czy ma powstać także imienna wizytówka Pawła? Jeśli tak, podaj nazwisko, rolę do wpisania pod nazwiskiem i numer telefonu (własny czy wspólny 663 206 373). W plikach tych danych nie ma. Gotowe są dwa warianty: imienna Krystiana Stryjakiewicza i firmowa bez nazwiska (wizytowki/podglad.png).
   termin: 2026-11-30
   propozycja: na razie bez wizytówki Pawła; Paweł rozdaje wersję firmową bez nazwiska, a imienną dorobimy, gdy poda dane
   Odpowiedź: na razie bez wizytówki Pawła; Paweł rozdaje wersję firmową bez nazwiska, a imienną dorobimy, gdy poda dane
