# Wzór wyglądu panelu

Krótki wzór dla strony projektu, szczegółów zadania, zakładki Strona i widoku Agenci. Uzupełnia zasady w komentarzu
na początku `panel.html` (punkty 1–11). Style są w bloku „Wzór” na końcu arkusza w `panel.html`. Test:
`dashboard/testy/test_ui_przebudowa.py`.

## Odstępy (siatka 4/8)

| Token | px | Gdzie |
|-------|----|-------|
| `--g-xs` | 4 | tekst pod tytułem wiersza, odstęp między przyciskami w grupie segmentowej |
| `--g-s` | 8 | między przyciskami, w nagłówku projektu, góra i dół wiersza listy |
| `--g-m` | 12 | między sekcjami (kartami), wnętrze karty w pionie |
| `--g-p` | 16 | wnętrze karty w poziomie (na telefonie 12) |
| `--g-xl` | 24 | odstęp na dole treści |

Innych wartości nie używamy. Odstęp daje `gap` rodzica, nie marginesy dzieci.

## Tekst: trzy wielkości

- 12 px (`--fs-xs`): opis pod tytułem wiersza, licznik, termin, etykieta pola.
- 14 px (`--fs-md`): treść, tytuły wierszy, nagłówki sekcji (650), przyciski.
- 20 px (`--fs-title`): tytuł strony (nazwa projektu, tytuł zadania w szczegółach).

## Karta

Jedna karta: tło `--surface`, ramka 1 px `--line`, promień `--r-lg` (8 px), wnętrze 12/16 px. Ten sam wygląd mają
sekcje Planu, „Kod i pliki”, ramki w szczegółach zadania („Twój ruch”, zgoda, praca agenta) i karty Agentów.
Wyróżnienie tylko lewą krawędzią 3 px: niebieska = Twój ruch, żółta = coś czeka (np. pliki do zatwierdzenia).
Bez kolorowego tła całej karty (wyjątek: błąd).

## Nagłówek sekcji

`<details class="panel psec">` z `<summary><h2>Nazwa <span class="cnt">n</span></h2><small>…</small></summary>`:
nazwa 14 px, licznik w szarej pigułce (czerwonej przy „Po terminie”), po prawej jedna krótka informacja (np. minuty
na dziś). Rozwijanie strzałką przed nazwą; stan zwinięcia w `PF.more[klucz]` (pamiętany na urządzeniu). Sekcja z treścią
na dziś otwarta, reszta zwinięta.

## Znaczniki

- Stan (`.lz`): tylko gdy wymaga uwagi (po terminie, zablokowane, czeka na zgodę). Jeden na wiersz, nie powtarzany.
- Termin (`.due`): zwykły tekst 12 px, „dziś”, „jutro”, „pt. 27.11”; po terminie czerwony („po terminie 3 dni”).
  Bez plakietki „Po terminie” w każdym wierszu: nagłówek sekcji już to mówi.
- Rodzaj (publikacja, agent, część projektu) szarym tekstem albo `.ptag`.

## Wiersz listy

Tytuł (14 px) i pod nim jedna linia 12 px (termin, część, rodzaj, minuty); po prawej jeden przycisk działania
`.btn.sec.sm` (Zrobione, Zatwierdź, Obejrzyj, Odpowiedz). Na telefonie przycisk przechodzi pod tytuł, gdy brakuje
miejsca; cel dotyku 44 px.

## Nagłówek strony projektu

1. Nazwa (20 px) i stan projektu; po prawej „Szczegóły” i „Rozmowa”.
2. Jedna linia faktów: faza · postęp · bieżący etap.
3. Przełącznik części (gdy są) jako przyciski segmentowe w jednym wierszu.
4. Zakładki w jednym wierszu (wszystkie, bez „Więcej”).

Szczegóły techniczne (GitHub, gałąź, pliki) nie są na wierzchu: są pod „Szczegóły” i w „Kod i pliki”, zwykłymi
słowami („nie połączono z GitHubem”, „3 zmiany do wysłania”), bez „origin”, „commit”, „pole github:”.

## Telefon (do 820 px)

- Zakładki i przełącznik części w jednym wierszu, przewijane w poziomie (`.hscroll`), bez zawijania; wybrana pozycja
  przewija się do widoku.
- Bez awatara projektu w nagłówku; etap w osobnej linii.
- Strona bez poziomego przewijania od 393 do 1920 px.

## Przycisk Rozmowy

Na stronie projektu „Rozmowa” jest w nagłówku (nie pływa nad treścią); znacznik „czeka na odpowiedź” / „nowa
odpowiedź” przy nim. Otwarte okno rozmowy: na komputerze w prawym dolnym rogu, na telefonie arkusz od dołu. Szczegóły
zadania mają „Rozmowa” w swoim nagłówku (z odnośnikiem do zadania), pływający przycisk jest wtedy ukryty. Odbiór pracy: przycisk w rogu,
treść ma odstęp na dole.

## Teksty

Krótko i rzeczowo. Podpowiedź najwyżej jedno zdanie; dłuższe wyjaśnienie w `title` albo w „Szczegóły”.
