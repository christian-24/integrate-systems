# Audyt księgi 0.1: iteracja 1, model Haiku

Przegląd niezależny: audytor czytał tylko KSIEGA.md, bez wglądu w inne audyty. 2026-11-12.

## Ocena ogólna
Kierunek spójny, ale dużo procesu przed pierwszą wartością, a trzy twarde ograniczenia (dostęp do LinkedIna, Facebooka i portali; rozproszenie Mac–PC–chmura; limity subskrypcji) potraktowane jako szczegóły.

## Ustalenia
| # | Waga | Sekcja | Problem | Propozycja |
|---|---|---|---|---|
| 1 | krytyczna | 5, S2, S7, 12 | Profile prywatne bez API; scraping łamie regulaminy; S2 i S7 niewykonalne legalnie. | Wersja 1: przekazany mail; strony firmowe i portale po sprawdzeniu regulaminu i API. |
| 2 | krytyczna | 5, 6 | Inwentaryzacja sesji, kalendarza, iCloud działa tylko na Macu; chmura jej nie wykona; brak łączności Mac–PC, wybudzania PC, konfliktów plików. | Agent czyta lokalnie i wysyła zdarzenia do serca; łączność (np. VPN); jedno źródło prawdy na plik. |
| 3 | krytyczna | 5, 10, 12 | Uruchomienia 24/7, raporty, inwentarz zużyją Max bez budżetu; nie sprawdzono warunków automatyzacji na subskrypcji. | Budżet uruchomień dziennie, priorytety, kolejka; sprawdzić regulamin przed budową. |
| 4 | wysoka | 4, 12 | Notion jako tablica wymaga reguły, która wersja jest prawdą. | System źródłem prawdy, Notion tylko do odczytu, decyzje w panelu. |
| 5 | wysoka | 1, 7, 8 | Ukryta praca właściciela; 10 minut nierealne przy wielu kandydatach. | Mierzyć minuty; kandydaci zbiorczo, domyślnie backlog, najwyżej 3 pytania dziennie. |
| 6 | wysoka | 1 | Miary nieweryfikowalne. | 60 s przy włączonym PC; lista typów ważnych zdarzeń; test 20 zdarzeń. |
| 7 | wysoka | 6, P5 | Brak schematu zdarzenia i tabeli aliasów projektów. | Wzorcowy wiersz zdarzenia; aliasy zatwierdza właściciel. |
| 8 | wysoka | 3, 7 | Lekka vs pełna bramka sprzeczne; dane zdrowotne bez zasad prywatności. | Bramka: Praca pełna, Życie lekka; dane zdrowotne tylko lokalnie, nie w powiadomieniach. |
| 9 | wysoka | 6, 10 | Brak bezpieczeństwa: panel z iPhone'a, ekspozycja PC, sekrety, logi, rotacja. | Dostęp tylko przez VPN, HTTPS, żadnych portów w internecie, sekrety poza projektami, log zdarzeń. |
| 10 | średnia | 6 | ntfy: nazwa kanału jedynym zabezpieczeniem. | Treść bez danych, losowy kanał albo własny serwer. |
| 11 | średnia | 4 | Stany bez przejść. | Tabela przejść: skąd, dokąd, kto zatwierdza. |
| 12 | średnia | 3, 4, 5 | Turtle projekt czy epik. | Epik w projekcie „Pomysły” albo projekt w backlogu. |
| 13 | średnia | 2, 10 | Codex bez procesu uruchamiania; kalendarz i poczta niepotrzebne do pierwszej wartości. | Wersja 1: jeden runner (Claude CLI); kalendarz i poczta w etapie 2. |
| 14 | średnia | 11 | Za dużo dokumentu przed wartością; brak kryterium końca audytu. | Najwyżej 2 iteracje; BPMN dla P5–P7 i P9; koniec przy braku luk krytycznych. |

## Brakujące scenariusze i przypadki brzegowe
- Błąd agenta: cofnięcie zmiany i zgłoszenie, nie tylko „do odbioru”.
- Portal wymaga konta lub CAPTCHA: system tylko przypomina właścicielowi.
- Dane klienta lub NDA: kto widzi, gdzie leżą, jak długo.
- Zdarzenie pasujące do dwóch projektów albo do żadnego: kolejka „do przypisania”.
- Agent zmienia stan lub termin bez zgody.
- PC wyłączony w nocy: widoczne „nie dostarczono”.
- Kopia księgi i strumienia zdarzeń, test przywracania.
- Limit wydatków na API i chmurę.

## Pierwszy krok
Skrypt tylko do odczytu na Macu: projekty i sesje Claude Code do lokalnego pliku kandydatów (nazwa, ścieżka, ostatnia aktywność), nic nie wysyła. Właściciel kwalifikuje trzy znane projekty.

## Pytania do właściciela
1. LinkedIn i Facebook w wersji 1 tylko przez ręczne przekazanie treści?
2. Ile uruchomień agentów dziennie z subskrypcji Max?
3. PC dostępny z Maca i iPhone'a przez VPN (np. Tailscale) czy chmura?
4. Notion w wersji 1 tylko do odczytu czy z zapisem z systemu?
5. Dane zdrowotne na PC czy tylko na Macu?
