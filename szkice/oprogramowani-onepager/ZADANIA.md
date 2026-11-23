# Zadania: Oprogramowani – strona WWW

> Jedyna lista zadań projektu. Czyta ją panel i agenci.
> Wiersz: `- [ ] Tytuł | kto: claude | kiedy: RRRR-MM-DD`

## Do rozplanowania
- [!] Przygotuj wizytówkę Oprogramowani dla Krystiana | kto: claude | gdzie: chmura | kiedy: 2026-11-23 | blokada: agent nie ma uprawnień do uruchomienia żadnego programu, który zamienia projekt na PDF i PNG; jest tylko wizytowka.html
  cel: wizytówka Krystiana Stryjakiewicza (Oprogramowani) w stylu nowej strony: biel, czerń, jeden czerwony akcent z logo, Inter, dużo powietrza
  gotowe gdy: w folderze wizytowka/ są wizytowka.pdf (2 strony: przód i tył, 85×55 mm plus 3 mm spadu), przod.png i tyl.png (300 dpi) oraz wizytowka.html do podglądu; każdy napis na karcie pochodzi z plików strony, bez wymyślonych danych
  materiał: site/src/dane.js
  materiał: site/src/tresc-pl.js
  materiał: site/src/jezyki/wspolne-pl.js
  materiał: site/public
  - [x] Zbierz z plików strony logo, kolory, krój pisma oraz imię i nazwisko, rolę, telefon, e-mail, adres strony i NIP; czego brakuje, wypisz w zostało:, nie zgaduj
  - [x] Zaprojektuj przód (logo i jedno zdanie, co robicie) i tył (dane kontaktowe); tekst nie bliżej niż 4 mm od krawędzi cięcia
  - [ ] Zrób PDF do druku i PNG, obejrzyj PNG i popraw wyrównania, łamania i kontrast
  - [x] W wynik: wpisz, co jest na karcie i gdzie leżą pliki
  wynik: powstał tylko projekt do podglądu i druku: wizytowka/wizytowka.html (2 strony 91×61 mm, czyli 85×55 mm plus 3 mm spadu; tekst 7 mm od linii cięcia). Przód: logo O[PRO]GRAMOWANI i zdanie ze strony „Łączymy Allegro, sklep i BaseLinkera z Twoim programem do faktur i magazynu (ERP): Subiektem, Optimą albo WAPRO.”. Tył: Krystian Stryjakiewicz, „Procesy i rozmowa z klientem”, 663 206 373, kontakt@oprogramowani.com, oprogramowani.com, małe logo, NIP 6192067893. Biel, czerń, szary tekst pomocniczy, czerwony tylko w logo, Inter. Wszystkie dane były w plikach strony, niczego nie brakowało.
  zostało: nie ma wizytowka.pdf, przod.png ani tyl.png, bo agent nie mógł uruchomić żadnego programu do renderu; z tego samego powodu nikt jeszcze nie obejrzał karty: wyrównania, łamanie zdania na przodzie i kontrast są niesprawdzone. Telefon i e-mail na karcie to ogólne dane firmy ze strony (strona nie podaje osobnych dla Krystiana).
  następne: Wyrenderuj wizytówkę Krystiana do PDF i PNG i popraw po obejrzeniu | kto: claude | kiedy: 2026-11-24
