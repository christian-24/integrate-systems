# Zadania: Analiza surowicy płodowej

> Jedyna lista zadań projektu. Czyta ją panel i agenci. Format: standard/STANDARD.md.

## Etap: Etap 0 — trzy odpowiedzi
termin: 2027-02-28

- [x] Przygotuj analizę zasadności, kosztów i planu wdrożenia z raportami 8 ekspertów (19.11.2026)
- [!] Wybierz 8 największych ubojni krów z listy rzeźni i przygotuj dane do rozmów | kto: claude | gdzie: chmura | kiedy: 2026-11-23 | blokada: agent nie miał dostępu do sieci, więc nie sprawdził uboju, stron ani telefonów
  cel: lista ubojni do rozmów z Etapu 0, od największych
  gotowe gdy: plik etap_0/ubojnie-wybor.md ma 8 ubojni: nazwa, miejscowość, szacowany ubój krów tygodniowo ze źródłem, strona i telefon firmy; bez nazwisk
  materiał: etap_0/lista_rzezni_bydla.csv
  materiał: etap_0/02_rozmowy_z_ubojniami.md
  materiał: zalaczniki/07_analityk_rynku_polskiego.md
  wynik: wersja robocza etap_0/ubojnie-wybor.md: 8 kandydatów i 6 rezerwowych z wykazu GIW (nazwa, miejscowość, numer weterynaryjny, odległości), kryteria wyboru i lista czynności do dokończenia; bez nazwisk
  zostało: brak uboju krów tygodniowo ze źródłem, stron i telefonów dla wszystkich 8 zakładów (wyszukiwarka i pobieranie stron były w tej sesji zablokowane); kolejność to przypuszczenie agenta, nie ranking wielkości; lista nie nadaje się jeszcze do dzwonienia
- [!] Wybierz 6 przetwórców surowicy w UE z kontaktem do działu zakupów | kto: claude | gdzie: chmura | kiedy: 2026-11-23 | blokada: agent nie miał dostępu do sieci, więc nie odczytał ze stron firm adresów e-mail ani formularzy
  cel: lista adresatów zapytań ofertowych z Etapu 0
  gotowe gdy: plik etap_0/przetworcy-wybor.md ma 6 firm: kraj, czy kupują od zewnętrznych zbieraczy (ze źródłem), strona, adres e-mail działu zakupów lub formularz
  materiał: zalaczniki/06_analityk_rynku_surowicy.md
  materiał: etap_0/03_zapytanie_do_przetworcow.md
  wynik: wersja robocza etap_0/przetworcy-wybor.md: 6 firm (Biowest, Sera Scandia, PAN-Biotech, Capricorn Scientific, Serana Europe, Biosera) z krajem, miejscowością, stroną i stanem wiedzy o skupie od zewnętrznych zbieraczy ze źródłem; uzasadnienie kolejności, 2 firmy rezerwowe i lista czynności do dokończenia
  zostało: brak adresu e-mail lub formularza dla wszystkich 6 firm (wyszukiwarka i pobieranie stron były w tej sesji zablokowane); żadna z 6 firm nie deklaruje publicznie skupu od zewnętrznych zbieraczy, a dla 4 z nich nie ma o tym żadnej informacji (stan z raportów z 19.11.2026, nie sprawdzony ponownie); nie sprawdzono, czy Biowest i Biosera z tej samej miejscowości są powiązane; lista nie nadaje się jeszcze do wysyłki
- [ ] Wyślij pismo do powiatowego lekarza weterynarii | kto: ty | kiedy: 2026-11-27 | czas: 20
  cel: stanowisko organu w sprawie kategorii krwi płodowej i trybu rejestracji
  gotowe gdy: pismo wysłane; data i sposób wysyłki w notatce pod zadaniem
  materiał: etap_0/01_pismo_do_lekarza_weterynarii.md
  pyta: Data wysłania [data]; Sposób wysyłki [wybór: e-mail | ePUAP]
  - [ ] uzupełnij dane nadawcy i właściwy powiat
  - [ ] wyślij e-mailem albo przez ePUAP i zapisz datę
- [ ] Zadzwoń do 5–8 ubojni według listy pytań | kto: ty | kiedy: 2026-12-04 | czas: 90 | po: Wybierz 8 największych ubojni
  cel: liczba krów tygodniowo, los płodów i zgoda na pomiar
  gotowe gdy: przy każdej ubojni z listy notatka z odpowiedziami na pytania 1–9
  materiał: etap_0/02_rozmowy_z_ubojniami.md
  materiał: etap_0/ubojnie-wybor.md
  pyta: Liczba krów tygodniowo [liczba]; Zgoda na pomiar [tak/nie]; Los płodów [tekst, np. utylizacja]
- [ ] Wyślij zapytania ofertowe do 4–6 przetwórców | kto: ty | kiedy: 2026-12-04 | czas: 40 | po: Wybierz 6 przetwórców
  cel: cena za litr, minimalna dostawa i specyfikacja od przetwórców
  gotowe gdy: zapytania wysłane do co najmniej 4 przetwórców; data przy każdym
  materiał: etap_0/03_zapytanie_do_przetworcow.md
  materiał: etap_0/przetworcy-wybor.md
  pyta: Data wysłania [data]
- [ ] Przelicz model opłacalności na odpowiedziach z Etapu 0 | kto: claude | gdzie: chmura | kiedy: 2027-02-10 | po: Zadzwoń do 5–8 ubojni, Wyślij zapytania ofertowe
  cel: wynik finansowy na liczbach z ubojni i od przetwórców zamiast szacunków
  gotowe gdy: model_oplacalnosci.py ma podmienione parametry ze źródłem „Etap 0”, a wynik i różnica względem Dokumentu 2 są w etap_0/wynik-etapu-0.md
  materiał: zalaczniki/model_oplacalnosci.py
  materiał: 02_koszty_zwrot_zysk.md
- [ ] Zdecyduj: Etap 1 albo przerwanie | kto: ty | kiedy: 2027-02-28 | czas: 30 | po: Przelicz model opłacalności
  cel: decyzja według bramki z Dokumentu 3 (pkt 3, Etap 0)
  gotowe gdy: w DECYZJE.md wpis z datą, liczbami z Etapu 0 i decyzją
  materiał: 03_plan_wdrozenia.md
  pyta: Decyzja [wybór: Etap 1 | przerwanie]; Liczba krów tygodniowo z Etapu 0 [liczba]; Cena za litr z Etapu 0 [liczba]

## Do rozplanowania
- [ ] Uzupełnić pliki projektu według standardu | kto: claude
  cel: Uzupełnić według standard/STANDARD.md: README (brak pliku), Architektura (brak pliku), Uruchomienie (brak pliku), Instrukcje agentów (brak pliku). Niczego nie nadpisywać; na końcu python3 standard/projekt.py sprawdz bez braków w tym projekcie.
