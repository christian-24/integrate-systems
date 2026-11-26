# Panel projektów

Raport PM, monitor zadań z edycją, uruchamianie agentów, kampanie i kalendarz w jednym miejscu.
Panel niczego nie przechowuje sam: czyta i zmienia pliki projektów opisane w `../standard/STANDARD.md`.

## Uruchomienie

    python3 server.py

Bez terminala: dwuklik `Panel.command` w folderze IntegrateSystems (uruchamia panel i otwiera stronę; gdy panel już działa, tylko otwiera stronę).

Panel: http://localhost:4801/ (sam Python 3). `http://localhost:4801/podglad` to ta sama strona
z danymi przykładowymi; zmiany zostają tam tylko w pamięci strony.

Stałe uruchamianie na Macu i na PC, logowanie narzędzi i dostęp z telefonu: `../INSTALACJA.md`.
Ustawienia: zmienne środowiska albo `panel.env` (wzór: `panel.env.przyklad`).

## Widoki

Układ i kontrakt: `PULPIT.md`. Menu: Asystent (z liczbą spraw dla Ciebie), Marketing, Media, Agenci, Serwer, pod nimi
lista projektów z wyszukiwarką; na telefonie dolny pasek (Asystent, Marketing, Media, Agenci, „Więcej”: Serwer i projekty).

| Widok | Adres | Do czego |
|---|---|---|
| Asystent | `#asystent` | strona startowa: sprawy dla Ciebie na dziś (liczba i 3 najważniejsze, z przyciskami), notatka PM, „Pokaż” kart; rozmowa głosem i tekstem, odpowiedzi jako karty |
| Marketing | `#marketing` | tydzień postów i filmów, kampanie w toku z „Wpisz wynik”, kanały publikacji, studio filmów |
| Media | `#media` | zdjęcia i filmy ze wszystkich projektów |
| Agenci | `#agenci` | logowanie, limit, samodzielne uruchamianie, Raport PM, Teraz (co trwa, kamienie, szacunek), użycie Claude i Codex, publikacje, ostatnie 24 h, uruchomienia (zwinięte) |
| Serwer | `#koszty` | stan i zasoby, Google Drive (jeden wiersz stanu, „Połącz Google Drive”, reszta w „Szczegóły”), kalendarz (połączenie, subskrypcja ICS), koszty, rozwój panelu, sesje |
| Informacje | `#informacje` | Księga projektów (pliki standardu we wszystkich projektach, „Zleć agentowi uzupełnienie”), opis standardu, skróty i pliki opisowe repozytorium (`GET /api/informacje`, stała lista w `server.py` `INFO_FILES`) z podglądem, tylko odczyt |
| Projekt | `#p-<id>` | opis, faza (zmiana z panelu), tablica, wskaźniki ze spalaniem etapu, etapy i terminy, księga, marketing; projekt z częściami: `#p-<id>?cz=<id części>` |
| Odbiór pracy | `#odbior?z=<id zadania>` | wersje wyniku, porównanie, Akceptuję, Popraw |

Dawne widoki Start, Dla Ciebie, Przegląd, Wskaźniki, Tablica, Terminy, Blokady i Projekty (usunięte 2026-11-24) pokazuje
Asystent kartami z tych samych danych i z tymi samymi przyciskami (typ karty `panel`, `karty.PANEL_VIEWS`):

| Karta (id) | Dawniej | Co pokazuje i co można zrobić |
|---|---|---|
| `sprawy-dzis` (na starcie) | Przegląd → Decyzje, Dziś | liczba spraw na dziś, 3 najważniejsze (termin, odblokowane, priorytet), Zatwierdź, Odbierz, Odpowiedz, Zrobione, „Ponad plan” z „Przesuń na jutro” |
| `raport-pm` (na starcie: część „Proponuję”) | Przegląd → Podsumowanie PM | notatka z `raporty/`, „Raport PM”, stan ostatniego raportu |
| `sprawy` | Dla Ciebie | filtr rodzaju i projektu, Decyzje, Dziś, 7 dni, Później, Do zamknięcia (Zamknij), czekające na inne |
| `terminy` | Terminy, Przegląd → Ryzyka, Terminy 7 dni | filtr projektu, rodzaju i kalendarzy, po terminie i zagrożone, dziś, jutro, 7 dni, później, wolne okna dziś i jutro |
| `blokady` | Blokady | co wstrzymuje ile zadań, do zrobienia najpierw, zablokowane, mapa, zależności do poprawy (Usuń warunek, Dodaj zadanie) |
| `wskazniki` | Wskaźniki, Start | postęp, tempo, przepływ, porównanie projektów; wybór projektu otwiera wskaźniki projektu |
| `zadania` | Tablica | zadania ze wszystkich projektów z filtrem projektu i stanu; wiersz otwiera szczegóły zadania |

„Pokaż” na stronie Asystent (i polecenia „sprawy”, „terminy”, „blokady”, „wskaźniki”, „zadania”, „raport PM”) pokazuje
kartę bez pytania modelu: w trybie Sceny jako odpowiedź, w trybie Karty na górze płótna (`PF.apShow`). Stare adresy
(`#start`, `#ty`, `#przeglad`, `#wskazniki`, `#tablica`, `#terminy`, `#blokady`, `#projekty`, także z `?p=` i `?z=`)
prowadzą do Asystenta z pasującą kartą; `#asystent?k=<id karty>` robi to samo z odnośników panelu,
`#koszty?k=kalendarz|drive` przewija Serwer do sekcji, `#koszty?k=projekty` otwiera okno „Dodaj projekt”.
Projekt dodaje przycisk „+” przy nagłówku Projekty w menu (na telefonie: Więcej → „+ Dodaj projekt”); w tym samym
oknie pod „Projekty w panelu” jest folder projektu i „Usuń z rejestru…”. Naprawa brakującego poprzednika (pole `po:`) jest też
w szczegółach zadania.

Karta zadania otwiera szufladę: stan, termin, wymaga, blokada, uruchomienie agenta.

### Strona projektu

- Układ według `dashboard/WYGLAD.md`. Wiersz nazwy: stan projektu, po prawej „Szczegóły” (fazy, kafle, Księga, GitHub
  zwykłymi słowami; stan `pj-ov`) i „Rozmowa”. Przy projekcie z częściami przy nazwie mała lista „Część” (Całość,
  <część główna>, <części>; domyślnie Całość). Pod nazwą jedna linia: faza · postęp · bieżący etap. Całość pokazuje
  zadania, etapy i decyzje wszystkich części z etykietą części (np. „Strona WWW”); wybrana część pokazuje tylko swoje
  i swoje zakładki (np. Strona). Zakładki (Zadania, Strona, Marketing, Etapy, Wskaźniki, Księga, Połączenia) zawsze
  widoczne w jednym wierszu, na telefonie przewijane w poziomie. Bez zakładki Plan: stary adres `#p-<id>-plan` prowadzi
  do Zadań.
- Zadania (domyślna zakładka): na górze sekcja **Decyzje** (pytania, zgody, odbiory projektu; rozwijana, stan `pp-dec`),
  pod nią „Dodaj zadanie” i tablica.
- Połączenia: jedna karta na usługę, na wierzchu jeden wiersz stanu (przy projekcie z częściami wiersz na część),
  „Szczegóły” rozwija działania (stan `pj-con-gh`, `pj-con-dr`, `pj-con-meta`). **GitHub**: „zgodne z GitHubem”, „N zmian
  do wysłania”, „nie połączono z GitHubem”; w Szczegółach Sprawdź, Wyślij na GitHub, Usuń kopię z serwera, gałęzie,
  pliki, zatwierdź/odłóż zmiany. **Google Drive**: ścieżka folderu z kontem, N pozycji, albo „bez folderu”; w Szczegółach
  wybór folderu z listy folderów konta (drzewo z wyszukiwaniem; „Albo wklej link do folderu”), „Zmień folder”, „Odłącz
  folder”. **Meta Business (Facebook i Instagram)**: strony Facebook przypisane do projektu w Kanałach publikacji
  i konto Instagram strony; bez strony „Niepołączone” i „Połącz” (Marketing → Kanały publikacji). W Szczegółach wybór
  strony dla projektu z połączonych i profile z karty (`facebook:`, `instagram:`). Karta Meta jest w projektach, które
  mają albo mogą mieć kanały: strona przypisana, profil w karcie, kampania albo publikacja w zadaniach.
- **Google Drive** w Połączeniach pokazuje konta przypisane do projektu lub części. Nowe połączenie
  przypisuje konto do wybranego projektu i jego obecnych części. „Użyj konta z innego projektu” pozwala
  dodać istniejące konto po potwierdzeniu. W Serwer → Google Drive → „Szczegóły” widać przypisania i można odłączyć konto
  od wskazanej karty. Dostęp do Google Drive jest tylko do odczytu. Łączenie idzie
  tylko jednym kliknięciem, z własnym klientem OAuth (Serwer → Google Drive → „Szczegóły” → „Logowanie jednym kliknięciem”,
  INSTALACJA.md, „Google Drive”): Google wraca do panelu. Bez klienta panel pokazuje, jak go ustawić; dawne łączenie
  z wklejaniem adresu (klient rclone) jest w interfejsie wyłączone (decyzja właściciela 2026-11-25).
  Folder projektu montuje się w `szkice/<karta>/media/drive` (usługa `drive@<projekt>`), agent dostaje tę ścieżkę
  w instrukcji zadania. Połączenia sprzed kont (osobne logowanie na folder) działają dalej; „Zmień folder” przenosi
  je na konto.
- **Rozmowa** (Rozmowa w projekcie): z agentem rozmawia się tylko tu i w Asystencie; obie rozmowy mają te same
  uprawnienia i tę samą drogę działania (AGENCI.md, „Rozmowy: dwa miejsca, jeden silnik”). Przycisk „Rozmowa” w nagłówku
  strony projektu i szczegółów zadania (w odbiorze pracy w prawym dolnym rogu) rozwija okno czatu (na komputerze 380×520 px, przy otwartych
  szczegółach obok nich; na telefonie arkusz od dołu na całą szerokość, nad klawiaturą ekranową); „Zwiń” albo Esc je
  zwija. Rozmowa dotyczy bieżącego projektu: przy projekcie z częściami całości (rozmowa projektu głównego, czyta
  i zmienia też pliki części) albo wybranej części (jej własna rozmowa); w szczegółach zadania projektu albo części
  tego zadania. Część główna i Całość mają tę samą rozmowę. Okno zachowuje historię, przy przycisku widać
  „czeka na odpowiedź” i „nowa odpowiedź”. Prośba o pracę zakłada i uruchamia zadanie agenta (`POST
  /api/project/chat`). Treść strony ma odstęp na dole, żeby przycisk niczego nie zasłaniał.
  - **Rozmowa** w nagłówku szczegółów zadania (w zadaniu nie ma osobnego czatu) otwiera rozmowę
    z odnośnikiem „O zadaniu: …”: agent dostaje tytuł, szczegóły i ostatnie uruchomienie. Przy zadaniu agenta obok
    „Wyślij” jest „Wyślij i wykonaj” (polecenie pod zadaniem i uruchomienie), a gdy agent pracuje, „Wyślij do agenta”.
    Odnośnik usuwa „×”. Dawna rozmowa o zadaniu zostaje do odczytu w szczegółach („Dawna rozmowa o zadaniu”).
  - **Strona**: „Napisz uwagę” albo element wskazany przez „Wskaż” otwiera rozmowę z załącznikiem (podstrona, widok,
    element); „Wyślij uwagę” zakłada zadanie agenta strony albo przekazuje uwagę pracującemu agentowi. Lista „Uwagi”
    pokazuje stan.

### Projekt z częściami

Projekt, który ma kilka folderów i repozytoriów (np. integracje i strona WWW), to w panelu jeden projekt. Karta
części ma wiersz `- część projektu: <projekt główny>` (folder projektu głównego, np. `company-audits`; pasuje też
nazwa folderu jego karty). Część dalej ma swój folder, repozytorium, `ZADANIA.md`, agentów i zakładkę Strona; nic
się nie przenosi. W panelu:

- listy projektów (menu, okno „Dodaj projekt”, wybór projektu w filtrach kart Asystenta) mają jeden wpis;
  filtr projektu obejmuje części; zadania i terminy części mają nazwę „Projekt · Część”;
- nazwa części to tytuł jej karty bez nazwy projektu głównego („Oprogramowani – strona WWW” albo „Strona WWW” →
  „Strona WWW”); projekt główny traci nawias z tytułu („Oprogramowani (integracje ERP ↔ sprzedaż)” → nazwa
  „Oprogramowani”, część główna „Integracje ERP ↔ sprzedaż”); bez nawiasu część główna to „Główna część”;
- stary adres części (`#p-<część>…`) przechodzi na `#p-<główny>…?cz=<część>`;
- przełącznik części pod nazwą projektu ma wygląd zakładek („Część: Całość · … · Strona WWW”); „Całość” ma zakładkę
  Strona, gdy którakolwiek część ma `strona:` (podgląd tej części; przy kilku częściach ze stroną wybór części
  w zakładce);
- raport PM (`standard/pm.py`) liczy sprawy jak dotąd i podpisuje je „Projekt · Część”; lista projektów, następny
  krok i braki dokumentów liczone dla całości (`parts` w `projects`);
- dane: część ma `partOf` i `partLabel`, projekt główny `parts` (`[{id, label}]`) i `partLabel`; `cardName` to tytuł
  z karty. Wskazanie na nieistniejący projekt, na siebie albo na inną część jest brakiem karty, a projekt zostaje
  zwykłym projektem.

## Klawisze

| Klawisz | Działanie |
|---|---|
| `/` | szukaj projektu |
| `g` potem `s` `m` `e` `a` `k` | Asystent, Marketing, Media, Agenci, Serwer |
| `r` | w otwartej szufladzie: uruchom agenta |
| Esc | zamknij szufladę |

## Agenci

Panel uruchamia Claude Code i Codex na tym komputerze, na Twoim logowaniu (subskrypcja), bez kluczy API.
Pełny opis: `AGENCI.md`.

- Zadanie: `r` albo przycisk przy zadaniu. Agent dostaje jedno zadanie i zmienia tylko jego wiersz.
- Raport PM i test połączenia: przyciski w widoku Agenci.
- Logowanie: gdy Claude nie jest zalogowany, widok Agenci ma przycisk „Zaloguj”. Otwiera okno Terminala z `claude auth login`
  (`/api/agent/login`); logujesz się w przeglądarce, panel nie widzi danych logowania. Potem „Sprawdź ponownie” (`/api/agent/recheck`).
  Na Macu za pierwszym razem system pyta, czy Python może sterować Terminalem.
- Automat: sam bierze zadania z `kto: claude|codex`, `gdzie:` tego komputera (bez `gdzie:` na serwerze, węźle domyślnym)
  i datą `kiedy:` nie późniejszą niż dziś (także z przeszłości), gdy poprzednicy z `po:` są zrobieni; domyślnie wyłączony.
  Rytm marketingu (`kampanie/staly-rytm.md`) zakłada zadania postów i wpisania wyników; opis w `AGENCI.md`.
  Wiersz „Nagraj film…” albo „Obejrzyj film…” i publikacja z `po:` wskazującym taki wiersz nie dostają zadania posta, dopóki film nie jest nagrany.
- Post: odbiór „Przygotować post na …” pokazuje teksty i grafikę oraz zdanie „Twój ruch”. Publikacja z kampanii ma
  „Kopiuj i otwórz Facebook/LinkedIn/Reels” (kopiuje tekst i otwiera stronę publikowania; bez API) i „Opublikowane”,
  po którym wpisujesz link i wyniki.
- Zadania Claude dostają `--allowedTools` z listą bezpiecznych narzędzi (lokalny git, testy, pliki; bez push i sieci).
- Projekt w repozytorium git: panel zakłada gałąź `agent/RRRR-MM-DD-nazwa` i katalog roboczy `.agent/<id>`, agent
  pracuje w nim, po zakończeniu panel zatwierdza zmiany, zapisuje listę zmienionych plików (`changes`) i usuwa katalog.
  Scalenie do bazy: `POST /api/agent/merge`; podgląd zmian: `GET /api/agent/diff?id=`. Opis: `AGENCI.md`.
- Ścieżki plików z `wynik:` trafiają jako `materiał:` do zadań, które mają `po:` na tym zadaniu.
- `PANEL_AGENT_USER`: agenci jako osobny użytkownik systemu (`sudo -n -u`).
- Tryb uprawnień `acceptEdits`; polecenia powłoki dopuszcza `.claude/settings.json` projektu. Trybu z pominięciem uprawnień panel nie używa.
- Rekordy: `../uruchomienia/<id>.json`, surowy zapis `<id>.log`.

## Publikacja

Panel publikuje posty sam (`publikacja.py`): Facebook (strona projektu: zdjęcie, film, Reels) i Instagram (konto
firmowe połączone ze stroną; grafika jako JPEG albo film jako Reels). LinkedIn nie: regulamin API LinkedIn zabrania
automatycznego publikowania, więc w poście jest „Udostępnij” (telefon: systemowe menu z grafiką albo filmem
i tekstem, `GET /api/post/film`) i „Kopiuj i otwórz LinkedIn” (edytor z wpisanym tekstem); plan ustawiasz w LinkedIn.
- Połączenie: Marketing → Kanały publikacji. Facebook: App ID, App Secret i token z Graph API Explorer; panel zapisuje tokeny
  stron (nie wygasają) i przypisuje stronę do projektu. LinkedIn: token z OAuth Token Tools (60 dni).
  Tokeny w `PANEL_PUBLIKACJA_DIR` (domyślnie `~/dane/publikacja`, pliki 0600), nigdy w `/api/data`.
- Plan: w publikacji z kampanii „Zaplanuj” (kanały, dzień, godzina) albo „Opublikuj teraz”; wiersz
  `zaplanowane: RRRR-MM-DD GG:MM; kanały`. Pętla co 30 s publikuje tekst z `post.md` (sekcje Facebook, LinkedIn,
  Reels, Instagram) z `grafika.png` albo `film.mp4|mov` (wgranie w poście, `POST /api/post/film`, do 300 MB).
  Po sukcesie: link, wynik, stan zrobione i powiadomienie; po błędzie `zostało:` i powiadomienie; opublikowany
  kanał nie wychodzi drugi raz (`stan.json`).
- Instagram pobiera pliki z publicznego adresu `/media/<token>/…` (token na godzinę); wymaga `PANEL_PUBLIC_URL`
  i biblioteki Pillow (`python3-pil`) do JPEG. TikTok: jeszcze nie (wymaga audytu aplikacji przez TikTok).
- „Udostępnij na …” przez rozszerzenie Chrome (edytor posta, zakładka platformy bez publikacji przez API): Instagram
  (też gdy karta ma `- instagram: @profil`), Facebook (strona niepołączona w Kanałach publikacji), LinkedIn, TikTok.
  Panel tworzy pakiet (`udostepnij.py`, `POST /api/udostepnij {id, title, platforma}`; dawna trasa
  `/api/instagram/udostepnij` to Instagram): opis (sekcja platformy w post.md, inaczej najbliższa), pliki (film sam;
  inaczej `grafika.png` i zdjęcia `zdjecie-1.jpg`, `zdjecie-2.png`, `slajd-3.jpg`… do 10; TikTok tylko film) i
  profil z karty (`instagram:`, `facebook:`, `linkedin:`, `tiktok:`). Pakiet żyje 30 minut pod `/udostepnij/<token>`
  (bez sesji; CORS tylko dla dokładnych adresów platformy pakietu: https://www.instagram.com,
  https://business.facebook.com, https://www.facebook.com, https://www.linkedin.com, https://www.tiktok.com).
  Panel otwiera stronę tworzenia posta z `#us=<adres pakietu>`; rozszerzenie (`uruchom/chrome-udostepnij/`, instalacja
  w README tam) sprawdza konto, wgrywa pliki, wkleja opis i zatrzymuje się: publikujesz sam. Bez rozszerzenia (panel
  na adresie z manifestu nie widzi atrybutu `data-panel-rozszerzenie`) od razu, a inaczej po ~25 s bez pobrania pakietu
  panel pokazuje okno: dlaczego (i jak zainstalować) oraz „Kopiuj opis” i „Pobierz pliki”. Telefon: systemowe
  udostępnianie.
- Edytor posta: zakładki podglądu Instagram, Facebook (też dla `reels`) i TikTok dla kanałów z pola kanału (Instagram
  tylko ze zdjęciem albo filmem, TikTok tylko z filmem): układ jak w aplikacji, opis ucięty przed „więcej”
  (Instagram 125 znaków, Facebook 250, TikTok 80, albo na pierwszym końcu wiersza), profil i awatar projektu.
- Wyniki postów (`wyniki.py`, `wyniki_meta.py`, tylko odczyt): dla publikacji z linkiem z publikatora (`stan.json`)
  albo z pola `link:` (Facebook, Instagram) panel czyta statystyki tokenem strony: co 6 h przez pierwsze 3 dni, potem
  raz dziennie do 30 dni. Facebook: `/{post}/insights` (`post_media_view`, `post_total_media_view_unique`,
  `post_clicks`, a gdy v26 ich nie zwraca: `post_impressions*`) i pola reakcji, komentarzy, udostępnień; filmy
  `/{film}/video_insights`. Instagram: `/{media}/insights` (`reach`, `views`, `likes`, `comments`, `shares`, `saved`,
  `total_interactions`, przy Reels czas oglądania). Metryk, których v26 nie zwraca, panel nie pyta ponownie
  (`badMetrics` w `~/dane/reklamy/stan-wynikow.json`). Historia odczytów w `wyniki.json` w folderze posta
  (bez folderu: `~/dane/reklamy/organiczne-<projekt>.json`), najnowsze liczby w wierszu publikacji
  (`wyświetlenia:` suma kanałów, `kliknięcia:` z Facebooka; `konta:` zostaje ręczne). Post z `wyniki.json` nie dostaje
  zadania „Wpisz wynik publikacji…”. Błąd (wygasły token, brak uprawnienia, usunięty post): jedno powiadomienie,
  znacznik „wyniki: błąd odczytu” przy publikacji i bez ponawiania do ponownego połączenia Facebooka. Brak uprawnień
  (`read_insights`, `instagram_basic`, `instagram_manage_insights`) panel pokazuje w Kanałach publikacji.
- Reklamy Meta (Marketing API, `ads_read`, tylko odczyt): Kanały publikacji → „Konto reklamowe Meta”: token
  użytkownika systemowego z Business Managera (nie wygasa; token z Graph API Explorer tylko awaryjnie, z ostrzeżeniem
  o dacie końca po 60 dniach) w `PANEL_PUBLIKACJA_DIR/meta-reklamy.json` (0600, nigdy w `/api/data`). Panel pokazuje
  konta widoczne dla tokenu; konto `act_…` przypisujesz do projektu (jedno konto, jeden projekt; `polaczenia.json`).
  Codziennie od 6:00: `/act_{id}/insights?level=ad&time_increment=1` od ostatniego dnia (pierwszy raz od startu
  kampanii, najwyżej 90 dni) do wczoraj oraz suma 7 dni (częstotliwość). Rozmowy: akcja
  `onsite_conversion.messaging_conversation_started_7d`. Kod reklamy to początek nazwy (`S1 · Drzwi od 1590` → `S1`);
  reklamy bez kodu widok Wyniki wypisuje z prośbą o zmianę nazwy. Zapis: `PANEL_REKLAMY_DIR` (domyślnie
  `~/dane/reklamy/<projekt>.json`, 0600).
- Alerty reklam: zadanie `kto: ty` na dziś w `ZADANIA.md` z `kampania:` (kampania w toku projektu), najwyżej jedno na
  reklamę na tydzień: „Wyłącz reklamę {kod}: 0 rozmów za 60 zł”, „Wymień reklamę {kod}” (koszt rozmowy ponad 40 zł
  w 7 dniach), „Odśwież grafikę {kod}” (częstotliwość ponad 3 w 7 dniach). Progi w karcie: `- meta progi: 60; 40; 3`.
- Połączenia projektu (Marketing projektu → Połączenia, `wyConnCard`; `polaczenia.json` w `PANEL_PUBLIKACJA_DIR`, bez
  sekretów): Meta (strona i Instagram z Kanałów publikacji, konto reklamowe), LinkedIn (strona firmowa z id albo profil,
  stan wniosku o Community Management API: nie złożony, złożony, przyznany; reklamy LinkedIn), Google Ads (identyfikator
  klienta). Widok Wyniki i alerty biorą dane tylko z połączeń danego projektu. Przy dodaniu połączenia panel zakłada raz
  zadanie właściciela (Meta: token użytkownika systemowego, gdy go nie ma; LinkedIn: wniosek; Google Ads: wklejenie skryptu).
- LinkedIn: po „przyznany” i z tokenem LinkedIn panel czyta statystyki postów strony firmowej z linkiem
  `urn:li:share|ugcPost` (`/rest/organizationalEntityShareStatistics`: wyświetlenia, kliknięcia, reakcje, komentarze,
  udostępnienia) w tym samym rytmie co Facebook. Bez zgody i dla profilu prywatnego: wpis ręczny jak dotąd. 7 dni przed
  końcem ważności tokenu LinkedIn zadanie „Odnów token LinkedIn (wygasa DD.MM)” w projektach z LinkedIn (raz). Panel nie
  odświeża tokenu sam (wymagałoby to sekretu aplikacji LinkedIn na serwerze).
- Google Ads bez tokenu dewelopera (`wyniki_google.py`): „Pokaż skrypt” tworzy klucz projektu (zapis tylko skrótu
  SHA-256; nowy klucz unieważnia poprzedni, „Unieważnij klucz”) i skrypt z adresem `PANEL_PUBLIC_URL` i kluczem; klucz
  widać tylko w tej chwili. Skrypt (Narzędzia → Działania zbiorcze → Skrypty, harmonogram codziennie) czyta wczorajsze
  grupy reklam (wyświetlenia, kliknięcia, koszt, konwersje, w tym telefony) i wyszukiwane hasła z kosztem i wysyła
  `POST /api/wyniki/google-ads` z nagłówkiem `X-Klucz-Projektu` (bez sesji panelu, JSON do 512 KB). Zły klucz: 403
  „Odmowa.”; konto inne niż w połączeniu projektu: 400; ten sam dzień wysłany drugi raz zastępuje poprzedni. Kod
  wiersza: `G · <kampania>`. Alerty z `- google progi: 150; 4; 20` (zł bez konwersji w 7 dni na kampanię, limit
  średniego CPC, zł za hasło bez konwersji: zadanie „Wyklucz hasło „…” w G · …”).

## Marketing i filmy

Widok Marketing (`#marketing`): oś czasu tygodnia z postami kampanii (grafika albo film, stan, kanały). Post
otwiera szufladę z podglądem, filmem, „Co poprawić” (`POST /api/post/popraw`: zadanie agenta „Popraw post na …”)
i czatem. Nic nie publikuje się samo, dopóki nie klikniesz „Zaplanuj”.
Edytor posta: zakładki platform (Instagram, Facebook, LinkedIn, TikTok według kanałów i formy posta), pod zakładką
podgląd i edycja opisu (`POST /api/post/tekst`: sekcja post.md) oraz grafiki (`POST /api/post/grafika`). Jedna akcja
„Udostępnij na …”: publikacja przez API (z potwierdzeniem), inaczej rozszerzenie Chrome na stronie tworzenia posta
(telefon i zakładka „Post”: strona tworzenia posta, opis w schowku i pobrane pliki). „Oznacz jako opublikowane” i odwrotnie w menu „⋯” (z „Cofnij”).

Zakładka Marketing projektu ma części Kampanie, Wyniki i Klienci (`wyTab` w `panel.html`).
- Klienci (`klienci.py`): szybki formularz (data, auto, źródło z listy, kod reklamy albo posta, usługa, wycena), potem
  w wierszu „Umówiony” i „Wykonane (zł)”. Bez imion i telefonów (pole z numerem telefonu jest odrzucane). Dane poza
  repozytorium: `PANEL_KLIENCI_DIR` (domyślnie `~/dane/klienci/<projekt>.json`, 0600); wpisy czyta `GET /api/klienci`,
  w `/api/data` są tylko sumy. Import CSV (`;`, kolumny po nazwach: data, auto, źródło, kod, usługa, wycena, umówiony,
  wykonane; inne kolumny pomija, powtórzone wiersze nie wchodzą). Podsumowanie: bieżący tydzień i od startu kampanii,
  podział na źródła. Kampania z `- miernik: zapytania z reklam` ma wynik z dziennika: zapytania w okresie kampanii
  z kodem albo ze źródłem „Meta – reklama” lub „Google Ads” (ręczny `wynik:` wygrywa, gdy jest większy).
- Wyniki (`GET /api/wyniki?project=&okres=7|30|start&kampania=`): wiersz na kod posta albo reklamy (posty: kod z tytułu,
  np. `S1`, albo `post DD.MM`; Google Ads: `G · <kampania>`): zasięg, wyświetlenia, interakcje, wydano, rozmowy
  (reklamy z API, posty: zapytania z kodem posta), koszt rozmowy, umówieni, wykonane, przychód, koszt klienta,
  przychód na 1 zł. Kolejność: przychód, potem koszt klienta. Wiersz posta otwiera post, wiersz reklamy wykres dzienny
  wydatku i rozmów (`GET /api/wyniki/historia`). Zasięg reklam to suma dziennych zasięgów. Projekt bez połączenia
  reklam pokazuje „brak połączenia” z odnośnikiem do połączeń. Na Przeglądzie projektu: przychód z marketingu w tym
  miesiącu i wydatek na reklamy.

Filmy nagrywa panel (`film.py`) według `scenariusz.json` w folderze posta: prawdziwa przeglądarka (Playwright,
`~/narzedzia/film`), kursor i podświetlenie kliknięć, napisy, MP4 1080×1920 (ffmpeg). Nagranie startuje samo, gdy
film jest starszy niż scenariusz albo obrazy posta, albo przyciskiem „Nagraj film”. Zmiana samego studia (szablon,
marka, muzyka, logo) nagrywa od nowa tylko posty z dniem od dziś, nieopublikowane i bez filmu wgranego ręcznie
(znacznik `.film-wgrany` przy wgraniu); starsze dostają w poście „Film jest starszy niż szablon albo marka”.
Logowanie kontem demo z `~/dane/film/konto.json` (wpisujesz w Marketing → Kanały publikacji), tylko na hoście z `strony` w marce
i tym samym co `url`; host sprawdzany także po przekierowaniu, nawigacja głównej ramki poza strony marki jest
blokowana. Bez `strony` w marce pokaz otwiera tylko publiczne nazwy domen (bez adresów IP i sieci lokalnej).
Przy błędzie zrzut `.film-blad.png` w folderze posta. Czekanie dłuższe niż 1,5 s (`czekaj_na`) jest wycięte z filmu.
Film ma ścieżkę dźwięku (cisza albo `muzyka` z marki).

Studio filmów: `studio/` obok `KARTA.md` projektu. `studio/marka.json` (kolory, czcionki z grubością np. `Inter:Bold`,
styl napisów, `strony` do nagrań, `logo` i `muzyka` jako pliki w `studio/` sprawdzane po treści, plansza startowa
i końcowa) i `studio/szablony/<nazwa>.json` (kroki z parametrami `{{nazwa}}`, `tytul` dla właściciela, wartości
przykładowe w `parametry`, `wymagane` (treść posta), `limity` (`max`, `opcje`, `cyfry`), `etykiety`, `opis` dla agenta
i `dla_wlasciciela`: jedno zdanie, co widz zobaczy). Pokaz nagrywa tylko hosty z `strony` w marce. Scenariusz posta:
`{"szablon": "…", "parametry": {…}}`, pełne kroki (pokaz strony, także z `plansze_przed` i `plansze_po`: 1–4 plansze
objaśnienia przed i po nagraniu) albo objaśnienie `{"typ": "objasnienie", "plansze": [{"tekst", "podpis", "czas",
"obraz"}]}` (tylko ffmpeg; tekst do 90 znaków, `*słowo*` w kolorze akcentu). Czas każdej planszy, także startowej
i końcowej, wydłuża się do czasu czytania (1,2 s + 15 znaków/s, plansze marki plus przejście); plansza bez podpisu
ma domyślnie 2,5 s, hak (pierwsza plansza filmu) liczy 0,6 s + znaki, bo stoi od pierwszej klatki. Napis pokazu stoi
co najmniej czas czytania (nagrywarka czeka przed następnym). Plansze marki są
doklejane do obu rodzajów; scenariusz może je wyłączyć (`false`) albo zmienić obiektem: z własnym `tytul` (hak) bierze
z marki tylko kolory, bez tytułu uzupełnia planszę marki; przy szablonie łączy się z planszą szablonu. Pierwsza klatka
pokazuje tekst bez animacji (miniatura). Między planszami treść najpierw gaśnie do tła, potem tło przenika w następną
planszę (bez podwójnej ekspozycji i bez czerni przed planszą końcową); między tłem jasnym i ciemnym następna plansza
wsuwa się od dołu, a jej treść wchodzi po przejściu; przez czerń tylko przy nagraniu strony. Marka może mieć `ukryj`
(selektory CSS elementów strony ukrywanych w pokazie: baner zgody, przycisk „Opinia”, czat; scenariusz pokazu też),
`braki` (opisy braków marki dla właściciela) i `do_potwierdzenia` (`{"plansza_koncowa": "co potwierdzić"}`: tekst
tymczasowy, ostrzeżenie przy filmie). Nieznany klucz marki to ostrzeżenie, nie błąd. Nagranie strony jest
wyostrzane po powiększeniu 2×, napis na stronie ma prawie nieprzezroczyste pudełko i znika przed przejściem. Wersja 4:5
w czasie nagrania strony pokazuje cały kadr zmniejszony na tle marki. Poprzedni film zostaje jako `.film-poprzedni.mp4`
(porównanie w poście). Układ trzyma
się poza strefami interfejsu Reels/TikTok (góra 250 px, dół 480 px), wiersze łamią się po polsku. W scenariuszu
pisanym ręcznie `{{` to zwykły tekst, a klucz `opis` to komentarz.
Sprawdzenie bez nagrania: `python3 dashboard/film.py sprawdz <folder posta>` (błędy, ostrzeżenia, długość; ostrzega
też o powtórce szablonu i treści względem wcześniejszych postów, o planszach z przykładowym tekstem, o objaśnieniu
powyżej 30 s, o długim haku i o filmie bez muzyki). Błąd wartości po podstawieniu wskazuje parametr posta, nie szablon; błąd w planszy albo podkładzie nadpisanym
w poście to „scenariusz posta: …”. Parametr posta, którego szablon już nie ma, jest pomijany z ostrzeżeniem. W poście
„Co jest w filmie, po kolei” ma grupy: Plansze (przycisk „Zmień” przy planszy), Napisy na filmie i Dane wpisywane
w formularz (po jednym formularzu na grupę); skąd pochodzi każde pole, mówi serwer (`filmInfo.fields`), limity
szablonu trafiają do formularza (długość, lista, cyfry), „Wyróżnij zaznaczone słowo” wstawia `*słowo*` z podglądem.
`POST /api/film/zmien {project, date, params | slides}` zapisuje scenariusz po kontroli i nagrywa film od nowa; gdy
scenariusz zmienił się w międzyczasie (np. agent), odpowiada 409. Szuflada zadania posta (także zablokowanego) i zadania
„Nagraj film …” albo „Obejrzyj film …” (film nagrywa panel, właściciel ogląda) ma na górze skrót filmu: rodzaj, szablon, długość, kto i kiedy nagra, „Nagraj film”, „Obejrzyj”.
Marketing pokazuje „Studio filmów” (każdy projekt zwinięty osobno) z marką, miniaturami plansz w jej kolorach,
szablonami, postami, których scenariusz po zmianie szablonu się nie nagra, przykładowym filmem i prośbą do agenta o zmianę marki albo nowy
szablon (`POST /api/studio/popros`, zadanie „Zmień studio filmów: …”).
Test renderowania na serwerze: `dashboard/testy/render_na_serwerze.sh panel@<adres>` (pracuje w `/tmp`).

## Koszty Hetzner

Widok Serwer (`#koszty`, w menu): ten miesiąc, łącznie od założenia, pełny
miesiąc; tabela na serwer (z kopiami i adresem IP) i lista pozycji. Szacunek z cennika API Hetzner Cloud (godziny × stawka,
najwyżej cena miesięczna, brutto, EUR; kurs z NBP), odczyt co 6 h w tle (`koszty.py`). Usuniętych serwerów API nie
pokazuje; dokładne kwoty są na fakturach. Tokeny (Read, jeden na projekt Hetzner) w `/etc/integrate/hetzner.tokeny`
(`PANEL_HETZNER_TOKENY`), wpisuje je `sudo ustaw-token-hetznera` (`uruchom/serwer/ustaw-token-hetznera.sh`).

## PM

- `python3 ../standard/pm.py` liczy raport z plików; karty Asystenta (sprawy, terminy, blokady) liczą to samo.
- Agent `pm` (`.claude/agents/pm.md`) i polecenie `/raport` w Claude Code, rola w `../standard/PM.md`
  (Codex czyta ją przez `../AGENTS.md`). Z panelu: „Raport PM” w karcie Notatka PM na stronie Asystent albo w Agentach.
- Notatka PM trafia do `../raporty/RRRR-MM-DD.md`; panel pokazuje najnowszą na stronie Asystent (start: część
  „Proponuję”, karta `raport-pm`: cała).
- `pm.py --json`: kampania ma `marketing` (zapytania, zapytania z reklam, wykonane, przychód, wydatek na reklamy,
  przychód na 1 zł w okresie kampanii) z dziennika klientów i zapisu reklam (`klienci.marketing_numbers`); same sumy.

### Co dziś robimy

Plan dnia układasz w Asystencie („plan dnia”, „co mam dziś”). Sekcji „Plan dnia” w Agentach już nie ma (2026-11-25);
trasy `/api/plan/ask` i `/api/plan/accept` zostały na serwerze bez przycisku w panelu. Opis trasy: piszesz, co chcesz dziś zrobić; PM (Claude, bez narzędzi, niczego nie zmienia)
dostaje listę otwartych zadań wszystkich projektów i układa plan: najwyżej 6 zadań dla agentów i 5 dla Ciebie.
Zadania dla agentów są zaznaczone; „Uruchom zaznaczone” uruchamia je jak „Uruchom agenta” (te same reguły i kolejka).
Plan bierze tylko zadania z kart: id spoza listy i zadania, których agent nie może wykonać, są odrzucane.
Plan z dzisiejszego dnia zostaje widoczny do następnego.

## Projekty

- Rejestr `../projekty.json`, osobny na każdym komputerze. Dopóki go nie ma, panel pokazuje trzy projekty przykładowe z `przyklad/`.
- Z panelu: „+” przy nagłówku Projekty w menu (ścieżka folderu; opcjonalnie założenie brakujących plików standardu).
- Nowy projekt z terminala: `python3 ../standard/projekt.py nowy <folder> --nazwa "Nazwa" --rejestruj`
- Istniejący folder z terminala: `python3 ../standard/projekt.py dodaj <folder>`
- Na projektach przykładowych zadań nie da się uruchomić; raport PM i test połączenia działają.

### Projekty ze zbieracza

Panel pokazuje też foldery zakwalifikowane zbieraczem na tym komputerze (`../system/zbieracz.py kwalifikuj`),
bez dopisywania ich do rejestru:

- folder: `LOKALNE_DIR/aliasy.json`, stan: ostatnia decyzja z `STAN_DIR/mac/decyzje.jsonl`
  (`w realizacji`, `w przygotowaniu`, `wstrzymany`, `backlog`; pozostałe stany są pomijane);
- ścieżki z `../system/system.env` albo zmiennych środowiska (`STAN_DIR`, `LOKALNE_DIR`); brak plików zbieracza to nie błąd;
- folder z rejestru i ze zbieracza pokazuje się raz (porównanie po rzeczywistej ścieżce); pole `origin`: `registry`, `collector`, `sample`;
- folder bez plików standardu ma fazę „księga” i braki w księdze; panel niczego w nim nie zakłada;
- projektu ze zbieracza nie usuwa się z panelu (409): zmień decyzję w zbieraczu.

Projekty przykładowe pojawiają się tylko wtedy, gdy rejestr i zbieracz są puste.

### Pola karty

Wiersze pod tytułem `KARTA.md`, obok `- stan:`:

| Wiersz | Wartości | Bez wiersza |
|---|---|---|
| `- faza:` | pomysł, księga, budowa, wdrożenie, marketing, utrzymanie | faza wyliczona |
| `- instagram:` | nazwa profilu, np. `@marka` (litery, cyfry, `.` i `_`) | bez sprawdzania profilu przy udostępnianiu |
| `- klient:` | tak, nie | decyzja zbieracza, inaczej tak |
| `- część projektu:` | folder projektu głównego, np. `company-audits` | samodzielny projekt |
| `- próg:` | lekka, pełna | pełna dla projektu klienta, lekka dla własnego |
| `- stan:` | aktywny, wstrzymany, zakończony, backlog | decyzja zbieracza, inaczej aktywny |

Faza wyliczona (pierwsza pasująca): backlog → pomysł; brak karty albo karta z brakami → księga;
kampania w toku → marketing; wszystkie etapy zrobione → utrzymanie; inaczej budowa.
Błędna wartość pola jest brakiem karty. W `/api/data` pola projektu: `phase`, `phaseSource` (`karta`, `wyliczona`),
`client`, `threshold` (`lekka`, `pelna`), `description` (pierwszy akapit „Cel”, do 300 znaków), `alias`, `book`, `bookOk`, `bookTotal`, `questions`,
`nextStep`.

### Szczegóły zadania i następny krok

Format wciętych wierszy pod zadaniem opisuje `standard/STANDARD.md` (sekcja „Szczegóły zadania”). W `/api/data` każde zadanie ma:

```
"needsYou": "odbiór",                    pierwsza wartość pola wymaga (jak dotąd)
"needs": ["odbiór", "zgoda"],            wszystkie wartości pola wymaga
"detail": {"goal": "", "doneWhen": "", "refs": [{"path": "marketing/plan.md", "anchor": "5"}],
           "steps": [{"done": false, "text": "Kedameble"}], "result": "", "decision": "", "left": "", "notes": []}
```

Zadanie ma też:

```
"after": ["makietę"],                                       fragmenty z pola po:
"waitingFor": [{"title": "Przygotuj makietę", "done": false, "id": "…"}],   poprzednicy; id "" gdy fragment nie pasuje
"ownerNeeds": ["odbiór"],                                   wartości wymaga, które są sprawą właściciela (bez zgody przy kto: ty)
"stateSince": "2026-11-15",                                 od kiedy w toku albo do odbioru ("" poza tymi stanami i w przykładach)
"stalled": false,                                           [~] bez agenta dłużej niż 3 dni
"reviewOverdue": false,                                     odbiór czeka dłużej niż 2 dni
"check": {"key": "kopia", "ok": true, "at": "2026-11-19T03:05:00"},   pole sprawdza:; null bez pola
"unlocks": [{"id": "…", "title": "Zbuduj stronę", "executor": "claude", "date": ""}],   zadania z po: na tym zadaniu
"unlockCount": 1
```

Kontrola przy zadaniu (wiersz `sprawdza: <klucz>`, format w `standard/STANDARD.md`): klucz z `server.checks`
(`kopia`, `kopia-poza`, `claude`, `claude-agent`, `zapis-kart`, `panel`, `useme`, `dysk`; `ok` = stan `ok`, `at` = czas
pliku kontroli zdrowia) albo `plik <ścieżka>` (plik istnieje w folderze projektu albo karty). Bez stanu serwera
(Mac, PC, podgląd) `ok` klucza serwera nie jest `true`. Otwarte zadanie z `check.ok: true` panel pokazuje jako
„Wygląda na zrobione”; „Zamknij” (`POST /api/task/close-checked`) zapisuje `[x]` i notatkę
`zamknięte na podstawie kontroli serwera z RRRR-MM-DD HH:MM`.

Pola, które dodaje odczyt plików (`standard/STANDARD.md`: `priority` projektu, `proposal` pytania, `target`
i `result` kampanii, szczegóły publikacji), serwer przekazuje bez filtrowania. `dayMinutes` na najwyższym poziomie
`/api/data` to dzienna pojemność właściciela w minutach (`PANEL_DZIEN_MIN`, domyślnie 120).

`detail` ma dodatkowo `fix` (wiersz `poprawka:`) i `next` (wiersz `następne:`). `runBlock` „Czeka na: …” podaje
niezrobionych poprzedników. Dzień wejścia w stan panel zapisuje w `../uruchomienia/stan.json` (pole `since`), skąd
czyta go też `pm.py`.

Liczniki spraw właściciela na najwyższym poziomie `/api/data` (projekty poza stanem wstrzymany i backlog, zadania
i pytania bez odpowiedzi): `youToday` (dziś i po terminie), `youWeek` (w ciągu 7 dni), `youLater` (później albo bez daty).

Projekt ma `nextStep`: `{"title", "taskId", "executor", "date"}` dla otwartego zadania z najwcześniejszą datą,
a bez dat pierwszego otwartego z polem `kto`; `null`, gdy takiego nie ma.

`GET /api/plik?project=<id>&path=<ścieżka>&anchor=<opcjonalnie>` zwraca `{"ok": true, "path", "title", "text"}`:
tekst pliku `.md` albo `.txt` (najwyżej 200 KB) z folderu projektu albo folderu jego karty (gdy `KARTA.md` jest
dowiązaniem do `szkice/`). Z `anchor` tylko sekcja: nagłówek `##` z numerem („5” → `## 5. …`) albo z tekstem
(także w zapisie `partia-1`), a gdy takiego nie ma, nagłówek innego poziomu. Ścieżki sprawdzane po `realpath`:
plik poza tymi folderami, dowiązanie wychodzące na zewnątrz, inny typ pliku, brak pliku albo sekcji → 404
`{"ok": false, "error"}`. Wymaga zalogowania jak inne `/api/`.

### Pytania do właściciela

Sekcja `## Pytania do właściciela` w `KARTA.md`: wiersze `1. pytanie` albo `- pytanie`, pod pytaniem wcięty wiersz `   Odpowiedź: …`.
Panel pokazuje pytania bez odpowiedzi na stronie Asystent (sprawy dla Ciebie), w decyzjach projektu i w księdze projektu. Odpowiedź z panelu
(`/api/question/answer` `{id, n, answer}`) zapisuje albo zmienia ten wiersz; pusta odpowiedź go usuwa.

Pod propozycją mogą stać wcięte wiersze `   skutek: <operacja>` (w danych pytania `effects`: lista tekstów operacji):
`po: <fragment poprzednika> → <fragment tytułu>`, `kiedy: RRRR-MM-DD → <fragment tytułu>`,
`stan: zrobione|wstrzymane → <fragment tytułu>`, `nowe: <wiersz zadania>`.

- „Przyjmij propozycję” (`{id, n, "accept": true}`, albo pierwsza odpowiedź równa propozycji): odpowiedź = propozycja,
  skutki wykonane na `ZADANIA.md` projektu, pod każdym zmienionym zadaniem notatka `z pytania N, RRRR-MM-DD`.
  Odpowiedź `{"ok": true, "applied": [...], "failed": [...], "task": ""}`; operacja bez pasującego zadania trafia do `failed`.
  Pytanie z odpowiedzią albo bez propozycji: 409 albo 400.
- Inna odpowiedź na pytanie ze skutkami: skutki nie są wykonywane; panel zakłada w „Do rozplanowania” zadanie
  „Zastosuj odpowiedź na pytanie N” (`kto: claude`, `kiedy:` dziś, `materiał: KARTA.md#Pytania do właściciela`),
  gdy otwartego zadania o tym tytule jeszcze nie ma; `task` w odpowiedzi to jego tytuł.
- Pytanie bez skutków: odpowiedź `{"ok": true, "error": ""}` jak dotąd.
Pod pytaniem może stać wcięty wiersz `   termin: RRRR-MM-DD` (albo „do RRRR-MM-DD” w treści); pytanie w `questions`
ma pole `date` (`"RRRR-MM-DD"` albo `""`). Pytanie po terminie to ryzyko w raporcie PM.

### Stan serwera

`/api/data` → `server`:

```
"server": {"checks": {"panel": "ok", "kopia": "zle", "useme": "brak"},
           "backupAt": "2026-11-19T03:00:00", "backupOff": true, "at": "2026-11-19T09:10:00"}
```

- `checks`: wiersze `nazwa=ok|zle|brak` z pliku kontroli zdrowia (`PANEL_ZDROWIE_STAN`, domyślnie `/home/panel/.zdrowie-stan`);
  `at`: czas zmiany tego pliku.
- `backupAt`: pole `at` z pliku ostatniej kopii (`PANEL_KOPIA_STAN`, domyślnie `/home/panel/kopie/ostatnia.json`);
  `backupOff`: kopia poza serwerem (`offsiteAt`, albo `offsite: true` przy `at`) w ostatnich 26 h.
- Brak obu plików (Mac, PC) → `"server": null`.

### Historia

- Przy każdym odczycie danych na prawdziwych projektach panel zapisuje stan zadań z dziś do `../historia/RRRR-MM-DD.json`
  (`historia.py`, zapis atomowy, plik z tego dnia nadpisywany). Inny katalog: `PANEL_HISTORY_DIR`.
- Liczone są tylko zadania (bez publikacji): `done`, `rev` (otwarte z `wymaga: odbiór`), `blocked`, `wip`, `todo`, `total`.
- `/api/data` → `history`: wpisy z ostatnich 63 dni, rosnąco. Dla projektów przykładowych: `historia-przyklad.json`
  (8 tygodni, daty względne; w `/podglad` i `--export` zostają względne jak inne daty podglądu).

## Zapis z panelu

Panel zmienia `ZADANIA.md`, `kampanie/*.md` i pola karty (`KARTA.md`) projektów oraz rejestr projektów. Resztę plików zmieniają agenci.

| Żądanie | Zmiana |
|---|---|
| `POST /api/task/state` | `{id, title, state}`: stan zadania; z `"count": n` (tylko `state: done`) także wynik licznika jak `/api/task/count` |
| `POST /api/task/count` | `{id, title, count}`: zadanie z polem `licznik: <nazwa>` dopisuje w kampanii (`kampania: <plik>` zadania, kampania publikacji, a bez tego pierwsza kampania projektu w toku) w sekcji „Wyniki i wnioski” wiersz `- RRRR-MM-DD · <nazwa> <n> · <tytuł>`; kampania ma `counters` {nazwa: suma}, a `result` to większa z liczb: ręczny `wynik:` i suma licznika z `miernik:`; 400 bez pola licznik albo przy złej liczbie (0–1000000), 409 bez kampanii (stan zadania wtedy bez zmian) |
| `POST /api/task/close-checked` | `{id, title}`: `[x]` i notatka o kontroli serwera; 409, gdy `check.ok` nie jest `true` albo zadanie jest zrobione |
| `POST /api/task/update` | pola zadania: tytuł, stan, kto, gdzie, kiedy, pora, czas, wymaga, blokada, kanał |
| `POST /api/task/detail` | `{id, title, key, value}`: jeden klucz szczegółów pod wierszem zadania (`cel`, `gotowe gdy`, `materiał`, `wynik`, `decyzja`, `zostało`, `poprawka`, `następne`; dla publikacji `wyświetlenia`, `kliknięcia`, `konta`, `link`); pusta wartość usuwa wiersz, `materiał` przyjmuje kilka wartości w osobnych wierszach; `następne` to „Tytuł \| kto: … \| kiedy: …” (sprawdzany jak wiersz zadania); `krok` z value `{"index": n, "done": bool}` zmienia n-ty krok (od 0) |
| `POST /api/task/add` | nowe zadanie w etapie, w kampanii albo w „Do rozplanowania” (pod szczegółami ostatniego zadania) |
| `POST /api/stage/update` | termin etapu |
| `POST /api/campaign/update` | wynik i stan kampanii |
| `POST /api/agent/run` | uruchamia zadanie; wiersz dostaje `[~]`, `kto:` i `gdzie:` |
| `POST /api/agent/pm` | uruchamia raport PM |
| `POST /api/plan/ask` | `{"text"}`: PM układa plan dnia (uruchomienie `plan`) |
| `POST /api/plan/accept` | `{"id", "ids"}`: uruchamia wybrane zadania z planu; odpowiedź `started`, `failed` |
| `POST /api/agent/check` | test połączenia |
| `POST /api/agent/stop` | zatrzymuje uruchomienie albo zdejmuje je z kolejki |
| `POST /api/agent/merge` | `{id}`: scala gałąź uruchomienia do bazy (`git merge --no-ff`, bez push); 409 z opisem przy konflikcie, niezatwierdzonych zmianach albo plikach sekretów na gałęzi (`.env*`, `*.key`, `*.pem`) |
| `POST /api/agent/automat` | włącza i wyłącza Automat |
| `POST /api/project/add` | dopisuje folder do rejestru; opcjonalnie zakłada brakujące pliki standardu |
| `POST /api/project/remove` | usuwa projekt z rejestru; pliki zostają |
| `POST /api/project/meta` | `faza`, `klient`, `próg` w `KARTA.md` projektu z rejestru albo ze zbieracza |
| `POST /api/session/logout-all` | `{}`: unieważnia wszystkie sesje (nowy losowy klucz sesji w `../uruchomienia/stan.json`) |

Gdy plik zmienił się w międzyczasie (agent albo edytor), serwer odmawia (409), a panel wczytuje stan od nowa.
Żądania z obcej strony są odrzucane (403).

## Dostęp

| Skąd | Warunek |
|---|---|
| ten komputer, odczyt | bez hasła |
| ten komputer, zapis (`POST`) | bez hasła na Macu i PC; przy `PANEL_LOKALNY_KLUCZ_PLIK`, `PANEL_AGENT_USER` albo `PANEL_MACHINE=cloud` sesja albo nagłówek `X-Panel-Klucz` z pliku klucza (`AGENCI.md`, „Dostęp”) |
| inne urządzenie | `PANEL_HOST=0.0.0.0`, nazwa hosta w `PANEL_ALLOWED_HOSTS`, hasło w `PANEL_TOKEN`; logowanie na `/wejscie` |
| inne urządzenie, bez `PANEL_TOKEN` | odmowa (403) |

Błędne hasło: odpowiedź po 1 s, najwyżej 10 prób na minutę. Kroki dla iPhone'a: `../INSTALACJA.md`.
Sesja wygasa po 30 dniach. „Wyloguj wszystkie urządzenia” (`/api/session/logout-all`) unieważnia od razu wszystkie sesje.

## Kalendarz

- Odczyt (tylko Mac): `build/PanelKalendarz.app` (źródło `kalendarz.swift`), EventKit, tylko do odczytu.
  Pierwszy odczyt wymaga zgody: przycisk „Połącz kalendarz”.
- Bez połączonego kalendarza wydarzenia przykładowe (`kalendarz-przyklad.json`) pojawiają się tylko przy projektach
  przykładowych; przy projektach z rejestru albo zbieracza `calendar` ma `source: "none"` i pustą listę `events`.
- Po zmianie `kalendarz.swift` uruchom `./zbuduj-kalendarz.sh`; macOS zapyta wtedy o zgodę ponownie.
- Eksport: `/terminy.ics` (terminy etapów i daty publikacji). Z tego komputera bez klucza; z innego urządzenia
  adres z kluczem `/terminy.ics?k=…`, który panel pokazuje w zakładce Kalendarz.

## Pliki

| Plik | Rola |
|---|---|
| `server.py` | serwer: strona, `/api/data`, zapis, dostęp, `/terminy.ics` |
| `agents.py` | uruchamianie agentów, kolejka, Automat, rekordy |
| `historia.py` | dzienny stan zadań projektów, odczyt 63 dni |
| `historia-przyklad.json` | przykładowa historia (8 tygodni) dla projektów z `przyklad/` |
| `panel.html` | strona panelu |
| `AGENCI.md` | kontrakt uruchamiania agentów: ustawienia, stany, żądania |
| `panel.env.przyklad` | wzór ustawień; własne ustawienia w `panel.env` (poza repozytorium) |
| `agenci-przyklad.json` | przykładowe uruchomienia dla `/podglad` i eksportu |
| `testy/` | testy uruchamiania na atrapie polecenia `claude` |
| `przyklad/` | trzy projekty przykładowe i przykładowa notatka PM (daty względne, np. `+3`) |
| `przyklad-odtworz.py` | przywraca `przyklad/` do stanu początkowego |
| `kalendarz-przyklad.json` | przykładowe wydarzenia (tylko przy projektach przykładowych) |
| `kalendarz.swift`, `kalendarz-Info.plist`, `zbuduj-kalendarz.sh` | pomocnik kalendarza |
| `podglad.html` | wynik `python3 server.py --export podglad.html`, strona bez serwera |
| `../uruchom/` | skrypty stałego uruchamiania (Mac, Windows) i ręcznego startu |
| `../uruchomienia/` | rekordy uruchomień, surowe zapisy, `stan.json` |
| `../historia/` | pliki `RRRR-MM-DD.json` z historią stanów (powstają przy pracy panelu) |

## Testy

W folderze IntegrateSystems, bez sieci i bez zużycia limitu:

    python3 -m unittest discover -s dashboard/testy

Runda 2 (kolejność `po:`, kroki, poprawka, następne, terminy pytań, liczniki, Automat, stan serwera, sesje): `testy/test_runda2.py`.
Runda 3, agenci (gałąź uruchomienia na tymczasowym repozytorium git, scalenie, diff, materiał z wyniku, szczegóły
zadań Automatu, `PANEL_AGENT_USER`, klucz zapisu z loopback, nowe pola w `/api/data`): `testy/test_runda3_agenci.py`.
Runda 5, serwer (`sprawdza:` i zamknięcie po kontroli, `licznik:` do kampanii, skutki pytań, `unlocks`, prompt agenta,
odmowa scalenia z plikami sekretów): `testy/test_runda5_serwer.py`.

## Poza zakresem

Sterowanie sesją w trakcie (dopisywanie poleceń do pracującego agenta), zapis wydarzeń do kalendarza,
edycja dokumentów z panelu, wspólny widok wielu węzłów (każdy komputer pokazuje własne uruchomienia).
