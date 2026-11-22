# Rozszerzenie Chrome: udostępnij na Instagramie

Przycisk „Udostępnij na Instagramie” w panelu (Marketing, edytor posta) otwiera instagram.com. To rozszerzenie
wgrywa pliki posta, wkleja opis i zatrzymuje się. „Udostępnij” na Instagramie klikasz sam: rozszerzenie nigdy
go nie klika, nie loguje się i nie przełącza kont samo.

## Instalacja (Chrome na Macu)

1. Otwórz `chrome://extensions`.
2. Włącz „Tryb dewelopera” (prawy górny róg).
3. „Załaduj rozpakowane” i wskaż ten folder (`uruchom/chrome-instagram`).
4. Po zmianie plików w folderze kliknij przy rozszerzeniu ikonę odświeżenia.

Rozszerzenie działa tylko na `https://www.instagram.com/*` i nie potrzebuje żadnych uprawnień.

## Ustawienie w projekcie

W `KARTA.md` projektu pod tytułem: `- instagram: @nazwa_profilu` (profil, na który idą posty). Bez tego pola
rozszerzenie nie sprawdza profilu i pokazuje ostrzeżenie.

## Jak działa

1. Panel tworzy pakiet na 30 minut (`/udostepnij/<token>`: opis, pliki, profil) i otwiera
   `https://www.instagram.com/#is=<adres pakietu>`.
2. Rozszerzenie zapamiętuje adres w tej karcie (przetrwa przełączenie konta), pobiera pakiet i pliki.
3. Sprawdza zalogowany profil. Inny niż w karcie: czerwony pasek „Zalogowany: @x, a post jest dla @y” i przycisk
   „Przełącz konto” (otwiera menu przełączania; konto wybierasz sam). Po przełączeniu rozszerzenie dokończy.
4. Otwiera tworzenie posta, wgrywa pliki (film albo grafika i zdjęcia jako karuzela), przechodzi „Dalej”
   (przy filmie zamyka komunikat „OK” o rolkach), wkleja opis.
5. Zielony pasek: „Sprawdź post i sam kliknij Udostępnij”. Przycisk „Udostępnij” ma żółtą obwódkę.

Gdy rozszerzenie nie pobierze pakietu w ~25 s, panel pokazuje „Kopiuj opis” i „Pobierz pliki” (ręcznie).

## Gdy Instagram zmieni wygląd

Wszystkie selektory i napisy są w `selektory.js` (listy wariantów, pierwszy pasujący wygrywa, po polsku i angielsku):
przycisk tworzenia (`create`), podmenu „Post” (`postMenuText`), pole pliku (`fileInput`), „Dalej” (`nextText`),
„OK” (`okText`), pole opisu (`caption`), „Udostępnij” (`shareText`, tylko wyróżniany), zalogowany profil
(`currentUser`, `profileAlt`), formularz logowania (`loginForm`), przełączanie kont (`moreMenu`, `switchText`).
Pasek pokazuje, na którym kroku się zatrzymało („Nie dokończyłem: …”).

## Test

`dashboard/testy/test_instagram.py` uruchamia rozszerzenie w Chrome bez okna, z pustym profilem tymczasowym, na
atrapie strony (`dashboard/testy/atrapa_instagram.html`). Prawdziwego Instagrama testy nie dotykają.
