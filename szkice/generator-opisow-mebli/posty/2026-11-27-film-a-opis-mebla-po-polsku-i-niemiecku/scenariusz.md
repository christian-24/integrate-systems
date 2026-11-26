# Scenariusz nagrania: Film A „Opis mebla po polsku i niemiecku w 10 sekund”

- stan: propozycja
- publikacja: 2026-11-27
- nagranie: 2026-11-26
- sposób: ai

## Po co

- Cel: w 40 sekundach pokazać drogę od atrybutów mebla do gotowego opisu po polsku i po niemiecku i skierować widza do darmowego
  konta (10 opisów miesięcznie, bez karty). Film liczy się do celu kampanii „Stały rytm”: 10 kont Free do 30.11.
- Dla kogo: właściciele małych firm meblowych, którzy sami wystawiają oferty na Allegro albo sprzedają do Niemiec
  i dziś piszą opis niemiecki ręcznie, tłumaczem albo wcale.
- Kanały: LinkedIn, Facebook, Reels (wiersz „Opublikuj film A…” w kampanie/staly-rytm.md). Opis pod filmem jest gotowy
  w posty/2026-11-20-film-a-opis-pl-de/post.md (sekcje Facebook, LinkedIn, Reels); tego pliku nie zmieniam.
- Różnica wobec filmu z 20.11 (nagranie ekranu przez panel): tamten film to pokaz formularza od początku do końca (ok. 50 s).
  Ta wersja jest krótsza i ma ujęcia AI na początku i na końcu, żeby zatrzymać przewijanie w Reels. Ekran Opisarni pokazują
  te same kadry, co w filmie z 20.11, więc nic nie jest udawane.

## Co nagrać

Osiem scen po 5 s, razem 40 s. Sceny AI (1, 2, 7) generujesz z polecenia; polecenie kopiujesz w całości (po angielsku,
bo narzędzia AI do wideo rozumieją je dokładniej). Sceny 3–6 to **zrzut ekranu**: wycinasz je z gotowego filmu
`posty/2026-11-20-film-a-opis-pl-de/film.mp4` (czasy niżej), bez nowego nagrania. Scena 8 to plansza zrobiona w edytorze.
W poleceniach AI nie ma żadnych napisów ani logo: litery wygenerowane przez AI wychodzą krzywe, napisy dodajesz w edytorze.

- [ ] Scena 1 (AI, hak): `Minimalist 3D render of a simple white chest of drawers with four drawers and light oak top, standing alone in an empty bright studio with warm cream background (#fbf7f1), soft daylight from the left, gentle shadow on the floor. Slow camera push-in from medium shot to close-up of the drawers. Clean product-illustration style, matte materials, no logo, no text, no people, no hands. Calm, premium mood. 5 seconds, vertical 9:16.` / 5 s
- [ ] Scena 2 (AI, problem): `Top-down view of a wooden desk with a closed laptop, a yellow tape measure, an empty notepad and two blank paper sheets, one with a small red-white flag sticker and one with a black-red-gold flag sticker. Warm cream and brown color palette, soft morning light. Very slow camera rotation clockwise from above. Illustrative, calm, tidy. No people, no hands, no readable text, no logos. 5 seconds, vertical 9:16.` / 5 s
- [ ] Scena 3 (zrzut ekranu, atrybuty): fragment 00:16–00:30 filmu z 20.11 (wpisywanie typu, wymiarów 80 × 90 × 40 cm, materiału i koloru komody), przyspieszony do 5 s / 5 s
- [ ] Scena 4 (zrzut ekranu, generowanie): fragment 00:31–00:36 filmu z 20.11 (profil Allegro, klik „Generuj opis”, oczekiwanie) bez przyspieszania, żeby czas generowania był prawdziwy / 5 s
- [ ] Scena 5 (zrzut ekranu, opis PL): fragment 00:37–00:41 filmu z 20.11 (gotowy opis po polsku), stop-klatka na ostatniej sekundzie, delikatny zoom 100 → 110% w edytorze / 5 s
- [ ] Scena 6 (zrzut ekranu, opis DE): fragment 00:41–00:46 filmu z 20.11 (ten sam mebel po niemiecku), delikatny zoom 100 → 110% w edytorze / 5 s
- [ ] Scena 7 (AI, efekt): `Two neat stacks of blank paper cards slide onto a wooden desk next to a small white chest of drawers model, the cards align themselves into two tidy columns. Warm cream background (#fbf7f1), brown and amber accents (#9e5f18), soft daylight. Slow camera pull-back from close-up to medium shot. Clean illustrative 3D style, matte, no people, no hands, no readable text, no logos. 5 seconds, vertical 9:16.` / 5 s
- [ ] Scena 8 (plansza w edytorze): tło #fbf7f1, tytuł „10 opisów miesięcznie za darmo” (Fraunces, #2b1d12), pod nim „Konto Free, bez karty” (Inter, #2b1d12) i „opisarnia.pl” (Inter SemiBold, #9e5f18); teksty i kolory jak plansza końcowa w studio/marka.json. Bez animacji poza łagodnym pojawieniem się (0,5 s) / 5 s

Gdy scena AI wyjdzie z ludźmi, rękami, napisami albo logo, wygeneruj ją ponownie (najwyżej 2 próby), a potem zastąp
stop-klatką z poprzedniej udanej sceny AI. Gdy zrzut ekranu z filmu z 20.11 jest nieczytelny po przycięciu do 9:16,
zrób w tym miejscu **zrzut ekranu** strony opisarnia.pl na telefonie (ta sama komoda z atrybutami z
posty/2026-11-20-film-a-opis-pl-de/scenariusz.json).

## Jak

- Narzędzie: sceny 1, 2 i 7 w Kling albo Runway (tryb tekst → wideo, 5 s, proporcje 9:16); montaż, napisy, lektor i muzyka
  w CapCut. Wszystko na darmowych kredytach; gdy ich zabraknie, scena 7 może zostać pominięta (film ma wtedy 35 s).
- Format: pionowy 9:16, 1080 × 1920, 30 kl./s. Ten sam plik idzie na Reels, Facebook i LinkedIn (LinkedIn wyświetla pion
  w feedzie). Sceny ekranu z filmu z 20.11 wstaw na tło #fbf7f1 z marginesem, nie rozciągaj ich do pełnego pionu.
- Styl i spójność: we wszystkich scenach AI ten sam opis koloru (kremowe tło #fbf7f1, brąz i bursztyn #9e5f18), to samo
  miękkie światło z lewej i ten sam typ mebla (biała komoda z blatem w kolorze dębu), żeby sceny wyglądały jak jeden film.
  Ruch kamery tylko powolny (najazd, odjazd, obrót). Przejścia między scenami: zwykłe cięcie, przy przejściu ze sceny 2
  do 3 i z 6 do 7 krótkie przenikanie 0,3 s.
- Napisy: Inter SemiBold, biały tekst #fbf7f1 na ciemnym pasku #2b1d12 (krycie ok. 88%), w dolnej trzeciej części kadru,
  najwyżej 2 wiersze; ten sam układ co w filmie z 20.11 (studio/marka.json).
- Muzyka: instrumentalna, spokojna (lo-fi albo lekki akustyczny podkład), ok. 90–100 uderzeń na minutę, bez wokalu.
  Utwór z biblioteki CapCut oznaczony jako dozwolony do użytku komercyjnego; w Reels możesz zamiast tego wybrać utwór
  z biblioteki Instagrama. Głośność ok. 20% pod lektorem, na planszy końcowej 40%.
- Lektor: głos AI z CapCut (tekst na mowę, język polski, spokojny męski albo żeński głos) albo Twój własny głos z telefonu.
  Tempo ok. 2,3 słowa na sekundę; tekst niżej mieści się w 40 s.
- Bez prawdziwych ludzi i bez prawdziwego produktu w scenach AI: komoda w scenach 1, 2 i 7 to ilustracja, nie oferta
  konkretnej firmy. Prawdziwe jest tylko to, co na zrzutach ekranu Opisarni.

## Co powiedzieć

| Scena | Lektor | Napis na ekranie |
|---|---|---|
| 1 | „Ile trwa opis komody na Allegro i do Niemiec? Sprawdzam.” | Opis komody? Sprawdzam |
| 2 | „Zwykle to wymiary, materiał, kolor i dwa teksty do napisania.” | Dwa teksty do napisania |
| 3 | „W Opisarni wpisuję typ, wymiary, materiał i kolor.” | Typ, wymiary, materiał, kolor |
| 4 | „Wybieram profil Allegro i klikam „Generuj”.” | Profil Allegro → Generuj |
| 5 | „Po kilku sekundach jest opis po polsku.” | Opis PL gotowy |
| 6 | „A obok ten sam mebel po niemiecku. Kopiuję i wklejam do oferty.” | Ten sam mebel po niemiecku |
| 7 | „Dwa opisy, jeden formularz.” | Dwa opisy, jeden formularz |
| 8 | „Dziesięć opisów miesięcznie za darmo, bez karty. Opisarnia kropka pe el.” | (plansza: 10 opisów miesięcznie za darmo · Konto Free, bez karty · opisarnia.pl) |

Hak (scena 1) ma 25 znaków i nie powtarza „po polsku i po niemiecku” z planszy końcowej (STYL.md, Filmy).
W filmie nie pada nic, czego konto Free nie daje: bez importu z pliku i bez analizy zdjęć.

## Na koniec

- Wezwanie na planszy (scena 8): „10 opisów miesięcznie za darmo. Konto Free, bez karty. opisarnia.pl”.
- Wezwanie w opisie pod filmem: gotowe w posty/2026-11-20-film-a-opis-pl-de/post.md, sekcja odpowiednia dla kanału
  (na LinkedIn: „Wygeneruj opis jednego swojego mebla i napisz mi wprost, co wyszło źle.”). Link opisarnia.pl
  na LinkedIn w pierwszym komentarzu.
- Publikacja 27.11 według wiersza w kampanie/staly-rytm.md (po „Potwierdź DPA”); publikujesz Ty.

## Gotowe gdy

- [ ] Plik wideo 9:16, 35–40 s, ma 8 scen (albo 7 bez sceny 7) w kolejności z „Co nagrać”.
- [ ] W scenach AI nie ma ludzi, rąk, czytelnych napisów ani logo; komoda wygląda podobnie we wszystkich scenach AI.
- [ ] Sceny 3–6 pochodzą z prawdziwej Opisarni (film z 20.11 albo nowy zrzut ekranu) i są czytelne na telefonie.
- [ ] Napisy z tabeli „Co powiedzieć” są w każdej scenie, w kolorach marki; lektor i muzyka słyszalne, muzyka nie zagłusza głosu.
- [ ] Plansza końcowa ma „10 opisów miesięcznie za darmo”, „Konto Free, bez karty” i „opisarnia.pl”.
- [ ] Film zapisany w tym folderze jako film.mp4 przed publikacją 27.11.
