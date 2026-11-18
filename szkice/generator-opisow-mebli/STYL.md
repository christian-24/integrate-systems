# Styl postów Opisarni

Zadanie „Przygotować post na RRRR-MM-DD (stały rytm)” wykonujesz według tego pliku. Folder karty to ten, w którym leży KARTA.md
(dowiązania w repozytorium prowadzą do niego); wszystkie ścieżki niżej są względem folderu karty.

## Co powstaje
1. Folder `posty/RRRR-MM-DD-krotka-nazwa/` (data z tytułu zadania, nazwa małymi literami bez polskich znaków).
2. `post.md`:
   ```
   # Tytuł posta (do 70 znaków)

   ## Facebook
   Tekst: 2–5 zdań, konkret dla sprzedawcy mebli, na końcu „opisarnia.pl”. Bez hasztagów lub najwyżej 2.

   ## LinkedIn
   Tekst: 4–8 krótkich akapitów, ton osobisty (właściciel pisze od siebie), na końcu pytanie albo zaproszenie do testu.

   ## Alt
   Jedno zdanie: co widać na grafice.
   ```
3. `grafika.svg`: kopia `szablony/post-kwadrat.svg`. Zmieniasz wyłącznie teksty w `<tspan>` (nagłówek: do 3 wierszy po ok. 18 znaków;
   tekst: do 5 wierszy po ok. 38 znaków; zbędne `<tspan>` usuń). Kolorów, czcionek i układu nie zmieniaj. PNG robi panel.
4. Wiersz w `kampanie/staly-rytm.md`, sekcja „Harmonogram”:
   `- [ ] Tytuł posta | kanał: facebook, linkedin | kiedy: RRRR-MM-DD | wymaga: zgoda`
5. Swoje zadanie oznacz `[x]`.

## Treść
- Źródła: `marketing/plan-10-kont.md` (kalendarz, gotowe posty w `marketing/linkedin/drafts/`), `metryki.md`, DECYZJE.md.
  Najpierw wykorzystaj post przewidziany w planie na ten dzień albo najbliższy niewykorzystany; sprawdź w Harmonogramie, czego już użyto.
- Obiecuj tylko to, co daje konto Free: 10 opisów miesięcznie, po polsku i po niemiecku, bez karty. Nie obiecuj importu z pliku ani analizy zdjęć.
- Nigdy „buduję”, „wkrótce”, „gdy ruszy”: Opisarnia działa produkcyjnie.
- Bez nazw firm, klientów i osób. Bez liczb, których nie ma w repozytorium.
- Język: polski, rzeczowo, bez wykrzykników i emotek (najwyżej jedna).

## Czego nie robisz
Nie publikujesz, nie wysyłasz, nie zmieniasz kodu Opisarni ani szablonu.
