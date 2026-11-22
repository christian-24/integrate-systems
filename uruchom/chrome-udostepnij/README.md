# Rozszerzenie Chrome: udostępnij post (Instagram, Facebook, LinkedIn, TikTok)

Przycisk „Udostępnij na …” w edytorze posta (zakładka platformy bez publikacji przez API) otwiera stronę tworzenia
posta tej platformy. To rozszerzenie wgrywa pliki posta, wkleja opis i zatrzymuje się. Publikujesz sam: rozszerzenie
nigdy nie klika „Opublikuj”/„Udostępnij”/„Zaplanuj”, nie loguje się i nie przełącza kont samo.

## Instalacja (Chrome na Macu, raz)

1. Otwórz `chrome://extensions`.
2. Włącz „Tryb dewelopera” (prawy górny róg).
3. „Załaduj rozpakowane” i wskaż folder `IntegrateSystems/uruchom/chrome-udostepnij`.
4. Po zmianie plików w folderze kliknij przy rozszerzeniu ikonę odświeżenia.

Masz już starą wersję z folderu `uruchom/chrome-instagram`? Ta ścieżka jest teraz dowiązaniem do
`chrome-udostepnij`: wystarczy kliknąć odświeżenie przy rozszerzeniu (albo usunąć je i załadować nowy folder).

Rozszerzenie nie prosi o żadne uprawnienia. Działa na:

| Strona | Po co |
| --- | --- |
| `https://www.instagram.com/*` | post na Instagramie |
| `https://business.facebook.com/*`, `https://www.facebook.com/*` | post i rolka strony firmowej (Meta Business Suite) |
| `https://www.linkedin.com/*` | post na LinkedInie |
| `https://www.tiktok.com/*` | film w TikTok Studio |
| `https://2-29-181-133.sslip.io/*`, `https://*.2-29-181-133.sslip.io/*`, `http://localhost/*`, `http://127.0.0.1/*` | tylko znak obecności dla panelu (`panel.js`) |

`panel.js` ustawia na stronie panelu atrybut `data-panel-rozszerzenie` i nic nie czyta. Dzięki temu panel od razu
wie, że rozszerzenia nie ma, i od razu pokazuje „Kopiuj opis” i „Pobierz pliki”. Panel pod innym adresem: dopisz go
w `manifest.json` (ostatni wpis) albo pomiń, wtedy panel czeka na rozszerzenie ~25 s jak dawniej.

## Ustawienie w projekcie (opcjonalne)

W `KARTA.md` projektu pod tytułem, jedno pole na platformę:

```
- instagram: @nazwa_profilu
- facebook: Nazwa strony
- linkedin: Nazwa strony albo profilu
- tiktok: @nazwa_profilu
```

Instagram i TikTok: rozszerzenie pyta stronę o zalogowany profil; inny niż w karcie zatrzymuje je z czerwonym paskiem
(„Zalogowany: @x, a post jest dla @y”). Facebook i LinkedIn: rozszerzenie sprawdza tylko, czy nazwa z karty jest
widoczna na ekranie, i pisze „sprawdź, czy to wybrane konto”. Bez pola: ostrzeżenie na pasku.

## Strony tworzenia posta

| Platforma | Adres otwierany przez panel |
| --- | --- |
| Instagram | `https://www.instagram.com/#us=…` (rozszerzenie klika „Nowy post”) |
| Facebook | `https://business.facebook.com/latest/composer#us=…`; film na kanale Reels: `…/latest/reels_composer#us=…` |
| LinkedIn | `https://www.linkedin.com/feed/?shareActive=true&text=<opis>#us=…` (bez okna: rozszerzenie klika „Zacznij publikację”) |
| TikTok | `https://www.tiktok.com/tiktokstudio/upload#us=…` (tylko film) |

Adresy ustala serwer (`dashboard/udostepnij.py`, `PLATFORMS` i `compose_url`).

## Jak działa

1. Panel tworzy pakiet na 30 minut (`POST /api/udostepnij` z platformą; `/udostepnij/<token>`: platforma, opis, pliki,
   profil) i otwiera stronę tworzenia posta z `#us=<adres pakietu>` (stary `#is=` dla Instagrama też działa).
2. Rozszerzenie zapamiętuje adres w tej karcie (przetrwa logowanie i przełączenie konta na tej samej domenie), pobiera
   pakiet i pliki. Pakiet innej platformy niż strona: czerwony pasek, nic nie wgrywa.
3. Sprawdza konto, otwiera tworzenie posta, wgrywa pliki (pole pliku; gdy go nie ma: przycisk „Dodaj zdjęcie/film”,
   na końcu upuszczenie na edytor), przechodzi kroki „Dalej”/„OK”, wkleja opis (TikTok: zastępuje nazwę pliku;
   LinkedIn: nie wkleja drugi raz, gdy opis jest już z adresu).
4. Zielony pasek: „Sprawdź post i sam kliknij „Opublikuj”” (Instagram: „Udostępnij”). Przycisk publikacji ma żółtą
   obwódkę. Gdy plików nie dało się wgrać (Facebook, LinkedIn), pasek to mówi, a opis i tak jest wklejony.

Facebook: logowanie przenosi na inną domenę i gubi pakiet. Po zalogowaniu kliknij w panelu „Udostępnij” jeszcze raz.

## Gdy strona platformy zmieni wygląd

Selektory i napisy: jeden plik na platformę w `selektory/` (`instagram.js`, `facebook.js`, `linkedin.js`,
`tiktok.js`). Każda lista to warianty sprawdzane po kolei (pierwszy pasujący wygrywa), po polsku i angielsku:
pole pliku (`fileInput`), przycisk dodawania (`mediaButton`, `mediaText`, `uploadText`), pole opisu (`caption`),
kroki (`nextText`, `okText`), przycisk publikacji (`publishText`: tylko wyróżniany, `safeClick` go nie kliknie),
logowanie (`loginForm`). Pasek pokazuje, na którym kroku się zatrzymało („Nie dokończyłem: …”).

Pliki: `wspolne.js` (przebieg, pasek, `safeClick`: jedyne miejsce kliknięć), `instagram.js`, `facebook.js`,
`linkedin.js`, `tiktok.js` (kroki platformy), `panel.js` (znak obecności).

## Test

`dashboard/testy/test_instagram.py` i `dashboard/testy/test_udostepnij.py` uruchamiają skrypty w Chrome bez okna,
z pustym profilem tymczasowym, na atrapach (`dashboard/testy/atrapa_instagram.html`, `atrapa_facebook.html`,
`atrapa_linkedin.html`, `atrapa_tiktok.html`). Prawdziwych serwisów testy nie dotykają: selektory prawdziwych stron
trzeba sprawdzić ręcznie przy pierwszym udostępnieniu.
