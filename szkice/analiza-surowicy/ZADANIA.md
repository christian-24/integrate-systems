# Zadania: Analiza surowicy płodowej

> Jedyna lista zadań projektu. Czyta ją panel i agenci. Format: standard/STANDARD.md.

## Etap: Etap 0 — trzy odpowiedzi
termin: 2027-02-28

- [x] Przygotuj analizę zasadności, kosztów i planu wdrożenia z raportami 8 ekspertów (19.11.2026)
- [ ] Wybierz 8 największych ubojni krów z listy rzeźni i przygotuj dane do rozmów | kto: claude | gdzie: chmura | kiedy: 2026-11-23
  cel: lista ubojni do rozmów z Etapu 0, od największych
  gotowe gdy: plik etap_0/ubojnie-wybor.md ma 8 ubojni: nazwa, miejscowość, szacowany ubój krów tygodniowo ze źródłem, strona i telefon firmy; bez nazwisk
  materiał: etap_0/lista_rzezni_bydla.csv
  materiał: etap_0/02_rozmowy_z_ubojniami.md
  materiał: zalaczniki/07_analityk_rynku_polskiego.md
- [ ] Wybierz 6 przetwórców surowicy w UE z kontaktem do działu zakupów | kto: claude | gdzie: chmura | kiedy: 2026-11-23
  cel: lista adresatów zapytań ofertowych z Etapu 0
  gotowe gdy: plik etap_0/przetworcy-wybor.md ma 6 firm: kraj, czy kupują od zewnętrznych zbieraczy (ze źródłem), strona, adres e-mail działu zakupów lub formularz
  materiał: zalaczniki/06_analityk_rynku_surowicy.md
  materiał: etap_0/03_zapytanie_do_przetworcow.md
- [ ] Wyślij pismo do powiatowego lekarza weterynarii | kto: ty | kiedy: 2026-11-27 | czas: 20
  cel: stanowisko organu w sprawie kategorii krwi płodowej i trybu rejestracji
  gotowe gdy: pismo wysłane; data i sposób wysyłki w notatce pod zadaniem
  materiał: etap_0/01_pismo_do_lekarza_weterynarii.md
  - [ ] uzupełnij dane nadawcy i właściwy powiat
  - [ ] wyślij e-mailem albo przez ePUAP i zapisz datę
- [ ] Zadzwoń do 5–8 ubojni według listy pytań | kto: ty | kiedy: 2026-12-04 | czas: 90 | po: Wybierz 8 największych ubojni
  cel: liczba krów tygodniowo, los płodów i zgoda na pomiar
  gotowe gdy: przy każdej ubojni z listy notatka z odpowiedziami na pytania 1–9
  materiał: etap_0/02_rozmowy_z_ubojniami.md
- [ ] Wyślij zapytania ofertowe do 4–6 przetwórców | kto: ty | kiedy: 2026-12-04 | czas: 40 | po: Wybierz 6 przetwórców
  cel: cena za litr, minimalna dostawa i specyfikacja od przetwórców
  gotowe gdy: zapytania wysłane do co najmniej 4 przetwórców; data przy każdym
  materiał: etap_0/03_zapytanie_do_przetworcow.md
- [ ] Przelicz model opłacalności na odpowiedziach z Etapu 0 | kto: claude | gdzie: chmura | kiedy: 2027-02-10 | po: Zadzwoń do 5–8 ubojni, Wyślij zapytania ofertowe
  cel: wynik finansowy na liczbach z ubojni i od przetwórców zamiast szacunków
  gotowe gdy: model_oplacalnosci.py ma podmienione parametry ze źródłem „Etap 0”, a wynik i różnica względem Dokumentu 2 są w etap_0/wynik-etapu-0.md
  materiał: zalaczniki/model_oplacalnosci.py
  materiał: 02_koszty_zwrot_zysk.md
- [ ] Zdecyduj: Etap 1 albo przerwanie | kto: ty | kiedy: 2027-02-28 | czas: 30 | po: Przelicz model opłacalności
  cel: decyzja według bramki z Dokumentu 3 (pkt 3, Etap 0)
  gotowe gdy: w DECYZJE.md wpis z datą, liczbami z Etapu 0 i decyzją
  materiał: 03_plan_wdrozenia.md

## Do rozplanowania
- [ ] Uzupełnić pliki projektu według standardu | kto: claude
  cel: Uzupełnić według standard/STANDARD.md: README (brak pliku), Architektura (brak pliku), Uruchomienie (brak pliku), Instrukcje agentów (brak pliku). Niczego nie nadpisywać; na końcu python3 standard/projekt.py sprawdz bez braków w tym projekcie.
