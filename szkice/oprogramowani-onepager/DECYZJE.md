# Decyzje: Oprogramowani – strona WWW

Każda decyzja to osobny wpis, najnowsze na górze. Nagłówek wpisu: `## RRRR-MM-DD: krótki tytuł`.

## 2026-11-27: Kalendarz i ntfy dla rezerwacji: minimum danych, osobny temat ntfy, bez nowego pytania w karcie

Kontekst: koncepcja koncepcja-rezerwacje-kalendarz.md (rezerwacje ze strony do kalendarza Apple i ntfy). W karcie czeka pytanie o ryczałt, więc nowego pytania nie wolno dodać. Przy czytaniu kodu wyszło, że od zmiany „Repairs” (19.08.2026) contact.sh nie zapisuje rezerwacji do rezerwacje.jsonl i nie obsługuje GET /api/terminy.
Decyzja: domyślnie wydarzenie w kalendarzu i powiadomienie ntfy bez danych osobowych gościa (tylko termin, forma, temat, ID rezerwacji; e-mail i telefon zostają w mailu). Osobny, losowy temat ntfy dla strony (nie temat panelu), adres w .env mailhooka. Osobny kalendarz iCloud „Oprogramowani – rozmowy”. Rekomendowany wariant A (CalDAV) + ntfy, poprzedzony przywróceniem zapisu rezerwacji; wybór A albo C i zakres danych właściciel zatwierdza przy odbiorze (wiersz decyzja:).
Skutki: przy minimalnym zakresie polityka prywatności nie wymaga dopisania Apple; wariant pełny (e-mail i telefon w kalendarzu) wymaga dopisania Apple jako odbiorcy w 4 językach. Wdrożenie to osobne zadanie (proponowane w następne:).
- Kto: agent

## 2026-11-26: Jedna sekcja „Jak to działa” z kafelkami oferty, zdanie o licencji zamiast „Wszystko zostaje u Ciebie”

Kontekst: uwagi właściciela po obejrzeniu strony 26.11: dwie czwórki („4 rzeczy” i „4 kroki”) mylą, sekcja „Zamiast raportów na 20 stron” jest za duża, a „Wszystko zostaje u Ciebie” jest nieprawdziwe, bo program jest na licencji (company-audits/DECYZJE.md, 2026-05-25).
Decyzja: na stronie głównej jest jedna sekcja „Jak to działa: Od wyceny do opieki” z czterema krokami. Pod krokami jest mały nagłówek „Co robimy” (bez liczby) i cztery kafelki z linkami do podstron; menu: najpierw „Jak to działa”, potem „Oferta”. Sekcję o raportach razem z przykładową rozmową na telefonie usunąłem. Zostało z niej jedno zdanie w kroku 3, a zdanie „Dzwonisz i odbiera Paweł albo Krystian” jest teraz w kroku 4. Punkt „Wszystko zostaje u Ciebie” zastąpiłem punktem „Licencja na piśmie: Z programu korzystasz na licencji, a jej zasady spisujemy w umowie, zanim zaczniemy.”. Z kroków usunąłem „pliki i dostępy są u Ciebie”. To samo w DE, IT, EN.
Skutki: zakres licencji (np. czy klient może zmienić wykonawcę) trzeba spisać we wzorze umowy; strona nic więcej nie obiecuje.
- Kto: agent

## 2026-11-26: Adresy podstron DE, IT i EN w języku wersji

Kontekst: wersje DE, IT i EN dostały nową strukturę z PL, w tym cztery podstrony linii oferty. Polskie adresy (/en/planowanie-produkcji) byłyby dla obcojęzycznego gościa i wyszukiwarki niezrozumiałe; regulamin i prywatność już mają adresy w języku wersji (/de/agb, /en/terms).
Decyzja: adresy podstron w języku wersji: /de/produktionsplanung, /de/integrationen, /de/excel, /de/it; /it/pianificazione-produzione, /it/integrazioni, /it/excel, /it/informatica; /en/production-planning, /en/integrations, /en/excel, /en/it. Polskie adresy bez zmian. Podstrona z cennikiem integracji, kalkulatorem i listą programów rozpoznawana po polu `ceny` w treści, nie po adresie „integracje”. KSeF w DE/IT/EN objaśniony raz jako polski system e-faktur; kwoty i braki ([UZUPEŁNIJ]) jak w PL.
Skutki: podstrony nie mają jeszcze hreflangów między językami (adresy się różnią); dodanie ich to osobna, mała zmiana w prerenderze. Zmiana adresu = zmiana klucza w podstrony i adres w kafelkach oraz cenniku danego języka.
- Kto: agent

## 2026-11-26: Wizytówka 2026-11: telefon i rola z poprzedniej wizytówki

Kontekst: nowa wizytówka i stopka e-mail pod strategię „Najpierw demo. Potem płacisz.”; telefon i rola pod nazwiskiem mają pochodzić od właściciela, a w karcie jest już otwarte pytanie (ryczałt opieki), więc nowego pytania nie wolno dodać. Poprzednia wizytówka (23.11) leży tylko na swojej gałęzi i ma pliki o tych samych nazwach (przod.png, tyl.png).
Decyzja: telefon 663 206 373 i rola „Procesy i rozmowa z klientem” wzięte z poprzedniej wizytówki, odebranej przez właściciela (telefon jest też w site/src/dane.js); właściciel potwierdza je przy odbiorze (wiersz decyzja:). Bez NIP i bez innych danych. Cztery linie oferty w skrócie jednym wierszem: „Planowanie produkcji · Integracje · Excel · IT i sprzęt”. Na przodzie hasło jak w nagłówku strony (druga część szara) i zdanie „Proste programy i dodatki dla małych firm.”. Poprzednia wizytówka zostaje bez zmian na swojej gałęzi; nowa ma treść w jednym pliku wizytowka/wizytowka-2026-11.js.
Skutki: zmiana roli albo telefonu = jeden wiersz w wizytowka-2026-11.js i w stopka-email.html/.txt, potem render od nowa. Gałęzi starej wizytówki nie scalać bez zmiany nazw jej plików (kolizja przod.png, tyl.png).
- Kto: agent

## 2026-11-26: Strona PL pod strategię „Najpierw demo. Potem płacisz.”

Kontekst: zadanie każe dać podstrony /planowanie-produkcji, /integracje, /excel, /it i usunąć z oferty to, co nie pasuje do czterech linii; adres /it jest już zajęty przez włoską wersję strony, a w cenniku były usługi doradcze (przegląd oferty 290 zł, karta projektu 690 zł, prowadzenie projektu od 490 zł / mies.) i opieka za stawkę godzinową.
Decyzja: podstrony mają adresy pod językiem: /pl/planowanie-produkcji, /pl/integracje, /pl/excel, /pl/it (bez kolizji z /it). Usługi doradcze zniknęły z oferty (nie należą do żadnej z czterech linii); jedyna zostawiona kwota z dawnych to integracja od 3 500 zł, a na /integracje także „koniec przepisywania” i „mały dodatek” od 2 000 zł. Opieka zgodnie ze strategią w miesięcznym ryczałcie (pole DANE.ryczalt, puste = „cena w wycenie”) zamiast stawki godzinowej. Tematy w oknie wyceny: Planowanie produkcji / Integracja lub dodatek / Excel albo IT / Jeszcze nie wiem (zmienione we wszystkich 4 językach, żeby numeracja tematów się zgadzała). Przy IT „demo” to plan na piśmie (sieć, sprzęt, cena) przed zakupami. Kalkulator i lista programów przeszły na /integracje. DE/IT/EN zostają w starym układzie do następnego zadania. E-mail i telefon są w dane.js (DANE.kontakt).
Skutki: powrót usług doradczych = dopisanie pozycji w tresc-pl.js; podstrony w DE/IT/EN wymagają tłumaczenia sekcji „podstrony” w kolejnym zadaniu.
- Kto: agent

## 2026-11-25: Bez banera zgody; regulamin bez zmian treści

Kontekst: uwagi z 25.11 każą dodać baner zgody z Consent Mode v2, jeśli strona ma tagi analityki lub reklam; strona przeszła z „darmowej godziny” na „bezpłatną wycenę”.
Decyzja: strona nie ładuje żadnego tagu Google ani piksela reklamowego (jedyna analityka to opcjonalny Plausible bez cookies, wyłączony, dopóki DANE.analityka jest puste), więc baneru zgody nie dodajemy. Baner z Consent Mode v2 (domyślnie odmowa) dodamy razem z tagiem Google Ads, gdy właściciel poda identyfikator konta. Regulamin i polityka prywatności zostają bez zmian treści (zmieniona tylko nazwa formularza na „Bezpłatna wycena”); zdania o „pierwszej rozmowie” w regulaminie dopasujemy przy zadaniu z danymi prawnymi. Usunięte dane strukturalne FAQPage, bo sekcji pytań już nie ma.
Skutki: dodanie Google Ads = nowy tag + baner + wpis w CSP (Caddyfile.oprogramowani.snippet i kopia w repozytorium Opisarni).
- Kto: agent

## 2026-11-23: Treść i układ wizytówki Krystiana

Kontekst: wizytówka ma mieć wyłącznie napisy z plików strony; trzeba było wybrać zdanie na przód, rolę i tło.
Decyzja: na przodzie pierwsze zdanie z hero.lead („Łączymy Allegro, sklep i BaseLinkera z Twoim programem do faktur i magazynu (ERP): Subiektem, Optimą albo WAPRO.”), bo to pełne zdanie strony, które mówi, co robimy. Rola to „Procesy i rozmowa z klientem” z sekcji „O nas”. Obie strony białe, czerwony tylko w logo, tekst 7 mm od linii cięcia. Telefon i e-mail to ogólne dane firmy ze strony.
Skutki: zmiana zdania albo roli to podmiana jednego wiersza w wizytowka/wizytowka.html; PDF i PNG trzeba potem wyrenderować od nowa.
- Kto: agent
