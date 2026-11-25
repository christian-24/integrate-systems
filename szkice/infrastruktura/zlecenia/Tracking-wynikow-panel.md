# Zlecenie do panelu: odczyt wyników postów i reklam, korzyść z każdego posta

*25 lis 2026. Dla agenta rozwijającego panel IntegrateSystems (gałąź `rozwoj`). Projekt testowy: „Shield & Silent – marketing”.*

## Po co

Dziś panel publikuje posty na Facebooku i Instagramie, ale wyniki (`wyświetlenia:`, `kliknięcia:`, `konta:`) właściciel wpisuje ręcznie po 48 h, a przychodu z posta nie widać nigdzie. Klientów i źródło zapisuje w arkuszu `dziennik-klientow.csv` poza panelem. Właściciel chce w panelu zobaczyć dla każdego posta i każdej reklamy: **ile osób zobaczyło, ile napisało, ilu przyszło i ile zarobiliśmy na złotówce wydanej na reklamę.**

## Zakres, w kolejności wdrażania

### Etap 1. Dziennik klientów w panelu (bez API)
- Nowy widok w projekcie: **Marketing → Klienci**. Formularz szybki z telefonu, maks. 6 pól: data, auto (model), **źródło** (lista: Meta – reklama, Instagram, Facebook, TikTok, Google Ads, Wizytówka Google, Polecenie, Inne), **kod** (S1, F2, B1… albo post z listy opublikowanych), usługa, wycena (zł). Później dopisywane: umówiony (tak/nie), wykonane (kwota zł).
- **Dane klientów poza repozytorium** (zasada z KARTA.md): zapis w `~/dane/klienci/<projekt>.json` (0600), w gicie nic. Bez imion i telefonów, tylko model auta.
- Import istniejącego `dziennik-klientow.csv` (separator `;`, nagłówek jak w pliku `google-ads/`).
- Podsumowanie na górze: zapytania, umówieni, wykonane, przychód w bieżącym tygodniu i od startu kampanii, podział na źródła.
- Licznik kampanii: zapytanie z kodem albo źródłem z reklamy zwiększa `wynik` kampanii z `miernik: zapytania z reklam` (zamiast ręcznego licznika).

### Etap 2. Automatyczny odczyt postów organicznych (Facebook i Instagram)
- Dla każdej publikacji, która ma link albo identyfikator posta (publikacje z API panelu mają go w `stan.json`; dla „Opublikowane” ręcznie: identyfikator z wklejonego linku), panel pobiera statystyki: **co 6 h przez pierwsze 3 dni, potem raz dziennie do 30 dni.**
- **Facebook** (token strony, który panel już ma): `/{post-id}/insights` oraz pola posta (reakcje, komentarze, udostępnienia). Metryki: wyświetlenia/zasięg, kliknięcia, reakcje, komentarze, udostępnienia; dla filmów wyświetlenia filmu. Nazwy metryk sprawdź w dokumentacji Graph API v26 (Meta w 2025 r. zastąpiła część metryk `post_impressions*` metryką „views”); użyj tylko tych, które v26 zwraca bez błędu.
- **Instagram** (`instagram_business_account` strony): `/{media-id}/insights`, metryki `reach`, `views`, `likes`, `comments`, `shares`, `saved`, `total_interactions` (dla Reels także czas oglądania, jeśli dostępny).
- **Uprawnienia:** do istniejących (`pages_show_list`, `pages_read_engagement`, `pages_manage_posts`, `publish_video`) dochodzą `read_insights`, `instagram_basic`, `instagram_manage_insights`. W Kanałach publikacji: komunikat, których brakuje, i prośba o ponowne połączenie (ten sam przepływ co dziś).
- **Zapis:** `wyniki.json` w folderze posta (historia odczytów z datą) + najnowsze liczby w wierszu publikacji pod istniejącymi kluczami `wyświetlenia:`, `kliknięcia:`, `konta:`. Gdy są dane automatyczne, rytm **nie zakłada** zadania „Wpisz wynik publikacji…”.
- Błąd odczytu (wygasły token, usunięty post) → jedno powiadomienie i oznaczenie w poście, bez ponawiania co 6 h.

### Etap 3. Reklamy Meta (Marketing API)
- **Połączenie:** Marketing → Kanały publikacji → „Konto reklamowe Meta”: identyfikator `act_…` i token **użytkownika systemowego** z Business Managera z `ads_read` (nie wygasa; token z Graph API Explorer wygasa po 60 dniach, więc tylko jako awaryjny, z ostrzeżeniem o dacie). Token jak inne: `PANEL_PUBLIKACJA_DIR`, 0600, nigdy w `/api/data`. **Tylko odczyt**: panel nie tworzy, nie zmienia i nie wyłącza reklam.
- **Odczyt raz dziennie (6:00)** za wczoraj i sumy od startu: `/act_{id}/insights?level=ad&time_increment=1&fields=ad_id,ad_name,adset_name,campaign_name,spend,impressions,reach,frequency,clicks,ctr,cpm,actions,cost_per_action_type`. Rozmowy: akcja `onsite_conversion.messaging_conversation_started_7d`.
- **Powiązanie z panelem:** kod na początku nazwy reklamy (`S1 · Drzwi od 1590 · 2026-11-28` → `S1`). Reklama bez kodu trafia do listy „Bez kodu” z prośbą o zmianę nazwy.
- **Zapis:** `~/dane/reklamy/<projekt>.json` (dzienne wiersze na reklamę).
- **Alerty** (jako zadanie `kto: ty` w kampanii, najwyżej jedno na reklamę na tydzień):
  - 0 rozmów po wydaniu 60 zł → „Wyłącz reklamę {kod}: 0 rozmów za 60 zł”,
  - koszt rozmowy > 40 zł przez 7 dni → „Wymień reklamę {kod}”,
  - częstotliwość > 3 w ostatnich 7 dniach → „Odśwież grafikę {kod}”.
  Progi w polu karty projektu (np. `- meta progi: 60; 40; 3`), żeby właściciel mógł je zmienić.

### Etap 4. Widok „Wyniki” (łączy wszystko)
Marketing → **Wyniki**, filtr: projekt, kampania, okres (7 dni / 30 dni / od startu).

| Kolumna | Skąd |
|---|---|
| Kod / post, data, kanał, miniatura | panel |
| Zasięg, wyświetlenia, interakcje | etap 2 / etap 3 |
| Wydano (zł) | etap 3 (0 dla organicznych) |
| Rozmowy | etap 3 (reklamy) / etap 1 (organiczne: zapytania z kodem posta) |
| Koszt rozmowy | wydano / rozmowy |
| Umówieni, wykonane | etap 1 |
| **Przychód** | etap 1 (suma „wykonane”) |
| **Koszt klienta** | wydano / wykonane |
| **Przychód na 1 zł reklamy** | przychód / wydano |

- Sortowanie domyślnie po przychodzie, potem po koszcie klienta. Kliknięcie w wiersz otwiera post albo historię reklamy (wykres dzienny: wydatek i rozmowy).
- Na Przeglądzie projektu jedna liczba: **przychód z marketingu w tym miesiącu / wydatek na reklamy**.
- Raport PM (`/raport`) dostaje te liczby do sekcji kampanii.

### Etap 5. Połączenia dla każdego projektu osobno (Meta, LinkedIn, Google Ads)
*Dopisane 25.11 na prośbę właściciela: każdy projekt w panelu ma mieć własne konta i własne wyniki.*

- **Marketing → Kanały publikacji → projekt:** jedna karta połączeń na projekt. Pola:
  - Meta: strona FB i konto IG (już jest), **konto reklamowe `act_…`**;
  - LinkedIn: **strona firmowa (organizacja)** albo profil prywatny;
  - Google Ads: **identyfikator klienta** (np. 434-771-1860 dla Shield & Silent).
  Widok Wyniki i alerty filtrują dane po projekcie. Projekt bez połączenia pokazuje „Brak połączenia” z linkiem do karty, bez błędu.
- **Meta (organiczne i reklamy):** jak w etapach 2 i 3, z kontem reklamowym przypisanym do projektu. Jeden token użytkownika systemowego może obsługiwać kilka kont reklamowych; panel pokazuje, które konta widzi token, i pozwala przypisać je do projektów.
- **LinkedIn:**
  - Statystyki postów strony firmowej: Community Management API (`r_organization_social`, `rw_organization_admin`; endpoint `organizationalEntityShareStatistics`: wyświetlenia, kliknięcia, reakcje, komentarze, udostępnienia, zaangażowanie). **Wymaga przyznania przez LinkedIn produktu „Community Management API” dla aplikacji.** Wniosek składa właściciel w portalu dewelopera LinkedIn; panel pokazuje instrukcję i stan.
  - Posty z profilu prywatnego: tylko to, co API udostępnia dla posta członka (jeśli zakres niedostępny, wpis ręczny jak dziś).
  - Reklamy LinkedIn (jeśli projekt je ma): Advertising API (`r_ads_reporting`), osobny wniosek. Do czasu zgody: import CSV z eksportu Campaign Managera.
  - Token LinkedIn wygasa po 60 dniach: panel przypomina 7 dni wcześniej (zadanie `kto: ty`) i obsługuje odświeżanie, jeśli aplikacja ma refresh token.
- **Google Ads (bez tokenu dewelopera):**
  - **Skrypt Google Ads** (Narzędzia → Działania zbiorcze → Skrypty), który raz dziennie wysyła do panelu `POST /api/wyniki/google-ads` wiersze z wczoraj: kampania, grupa reklam, reklama, wyświetlenia, kliknięcia, koszt, konwersje (w tym „Telefon z reklamy”), wyszukiwane hasła z kosztem. Panel generuje skrypt z wpisanym adresem i **kluczem projektu** (osobny klucz na projekt, do unieważnienia w panelu); właściciel wkleja go raz i autoryzuje w Google Ads. Skrypt tylko czyta konto Google Ads.
  - Endpoint przyjmuje dane tylko z poprawnym kluczem projektu, limit rozmiaru, bez sesji panelu; zły klucz → 403 bez szczegółów.
  - Kod reklamy: dla Google Ads kampania i grupa reklam służą za kod (np. `G · Wygłuszanie`), żeby klienci z dziennika ze źródłem „Google Ads” łączyli się z wydatkiem.
  - Google Ads API z tokenem dewelopera: później, jeśli skrypt nie wystarczy.
- **Alerty Google Ads** (progi w karcie projektu): koszt bez konwersji > 150 zł w 7 dni, średni CPC powyżej limitu z karty, wyszukiwane hasło z kosztem > 20 zł bez konwersji (propozycja wykluczenia jako zadanie `kto: ty`).

**Zadania właściciela do założenia w projekcie, którego dotyczą** (panel zakłada je sam przy dodaniu połączenia):
1. Meta: użytkownik systemowy w ustawieniach firmy, dostęp do konta reklamowego, token z `ads_read`, `read_insights`, `instagram_manage_insights` (instrukcja w panelu).
2. LinkedIn: wniosek o Community Management API w aplikacji LinkedIn panelu.
3. Google Ads: wklejenie skryptu z panelu i autoryzacja, harmonogram „codziennie”.

## Gotowe, gdy
- Etap 1: wpis klienta z telefonu w < 30 s; import CSV z przykładowego pliku; dane poza gitem; testy jednostkowe zapisu, importu i podsumowań.
- Etap 2: dla opublikowanego posta FB i IG liczby pojawiają się w panelu bez ręcznego wpisu; brak zadania „Wpisz wynik…” dla takich postów; testy z nagranymi odpowiedziami API (bez sieci).
- Etap 3: przykładowa odpowiedź `insights` (plik w `dashboard/testy/`) daje poprawne sumy, koszt rozmowy i alerty; token nie pojawia się w `/api/data` ani w logach.
- Etap 4: widok działa na panelu testowym na danych przykładowych i na telefonie.
- Etap 5: dwa projekty z różnymi kontami nie widzą swoich danych nawzajem; skrypt Google Ads z panelu działa w podglądzie Google Ads i jego przykładowe dane (plik w `dashboard/testy/`) dają poprawne sumy; zły klucz projektu → 403; LinkedIn bez przyznanego API pokazuje stan wniosku i wpis ręczny zamiast błędu.
- Opis w `dashboard/README.md` (sekcje Publikacja i Marketing), teksty w interfejsie krótko i po polsku.

## Czego nie robić
- Panel nie zmienia reklam ani budżetów (tylko odczyt). Zmiany w reklamach robi właściciel (KARTA: wymagają zgody).
- Bez imion, nazwisk i telefonów klientów w gicie, `/api/data` i raportach.
- Bez nowych zależności poza biblioteką standardową Pythona (jak reszta `publikacja.py`).
