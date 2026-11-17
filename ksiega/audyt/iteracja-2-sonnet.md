# Audyt księgi 0.2: iteracja 2, model Sonnet

Przegląd niezależny: audytor czytał tylko KSIEGA.md 0.2, bez wglądu w poprzednie audyty; fakty sprawdzał w internecie. 2026-11-12.

## Ocena ogólna
Spójna, dobrze rozdzielone etapy, ale etap 1 ma dwie luki: swobodne odpowiedzi bota z modelem kłócą się z budżetem, a droga zdarzeń Mac → PC nie istnieje przed Tailscale (etap 2). Werdykt: **tak po poprawkach**.

## Ustalenia
| # | Waga | Sekcja | Problem | Propozycja |
|---|---|---|---|---|
| 1 | krytyczna | 5, 14 | Zbieracz Maca „wysyła do serca”, a Tailscale dopiero w etapie 2; sprzeczne z „Mac tylko do odczytu, PC jedynym zapisującym”. | Tailscale do etapu 1 albo Mac wypycha zdarzenia do osobnego katalogu w repozytorium (jeden zapisujący na maszynę), PC scala. |
| 2 | krytyczna | 5, 9 | Wg źródeł wtórnych od 15.06.2026 tryb nieinteraktywny (`claude -p`, Agent SDK) korzysta z osobnej puli kredytów, nie z limitu subskrypcji; „0 zł poza subskrypcją” może nie zachodzić. Niepotwierdzone w dokumentacji Anthropic. | Sprawdzić u źródła przed etapem 1; w etapie 1 bot tylko skryptem (S1, S8); twardy limit i alert kosztu. |
| 3 | wysoka | 5, 9 | Zapis przy każdym zdarzeniu i push: brak opisu konfliktów, częstotliwości commitów, rozmiaru; dane wewnętrzne trafiają na GitHub, czego klasy danych nie opisują. | GitHub (prywatny) przyjmuje dane wewnętrzne, poufne nie; commity co 15 min; jeden plik JSONL na maszynę i dzień. |
| 4 | wysoka | 9, S10 | Ping co 15 min + tolerancja = granica 30 min; brak rozróżnienia „PC żyje, bot padł”. | Ping wysyła proces bota; okres 5 min, tolerancja 10 min; test „bot zatrzymany, PC włączony”. |
| 5 | wysoka | 14 | „Poprawny stan” bez definicji; dziennik bota nieopisany; zbiór 20 zdarzeń nieokreślony. | Poprawny = zgodny z ręcznie spisaną listą 3 projektów; 5 dni bez ręcznej interwencji; zbiór testowy jako plik w repozytorium. |
| 6 | wysoka | 5, 9 | Bot odpowie każdemu, kto go znajdzie; przyciski zatwierdzania bez weryfikacji; brak szyfrowania end-to-end dla botów. | Lista dozwolonych chat_id właściciela; long polling zamiast webhooka. |
| 7 | średnia | 6, 11 | Zbieracz czyta sesje i foldery (dane poufne); brak reguły, co zapisuje. | Inwentarz tylko z metadanych jawnych; treści sesji nie trafiają do repozytorium. |
| 8 | średnia | 4, 13 | Kwalifikacja setek kandydatów partiami po 5 to dziesiątki partii. | Etap 1: tylko 3 projekty, reszta „poza zakresem” do etapu 2. |
| 9 | średnia | 5 | Mac uśpiony: brak harmonogramu (launchd) i progu świeżości. | launchd co 30 min; znacznik świeżości na źródło z progiem. |
| 10 | średnia | 9 | Cisza nocna i limit 5 pilnych vs „system nie działa”, „termin jutro”. | „System nie działa” poza limitem i ciszą; reszta w limicie. |
| 11 | niska | 5, 15 | Bot jako usługa Windows: autostart, restart po aktualizacji, wyłączone usypianie. | Opis w `docs/URUCHOMIENIE.md` jako część kryterium etapu 1. |
| 12 | niska | 16, 17 | Klasy danych i limit uruchomień otwarte, a od klas zależy etap 1. | Zamknąć klasy przed etapem 1; limit uruchomień do etapu 3. |

## Brakujące scenariusze i przypadki brzegowe
- Mac i PC jednocześnie wypychają do repozytorium; utrata historii przy force-push.
- Zmiana nazwy lub przeniesienie folderu projektu.
- Rozrost repozytorium stanu (JSONL przez 12 miesięcy).
- Telegram niedostępny, bot zablokowany, token unieważniony: brak kanału zapasowego (np. e-mail).
- Restart PC w trakcie zapisu: zapis atomowy.
- Zmiana czasu letni/zimowy przy raporcie 7:00.
- Dwie instancje bota na PC.
- Test odtworzenia z kopii poza kryterium etapu 1.
- S8 bez potwierdzenia przypisania do projektu i bez cofnięcia.

## Sprawdzone fakty
- Tailscale, plan osobisty: bezpłatny, do 6 użytkowników — potwierdzone, tailscale.com/pricing.
- healthchecks.io, plan bezpłatny: 20 kontroli — potwierdzone; integracja z Telegramem i minimalny okres niepotwierdzone na stronie cennika, healthchecks.io/pricing.
- Rozliczanie `claude -p` / Agent SDK na subskrypcji: źródła wtórne mówią o osobnej puli od 15.06.2026; niepotwierdzone w dokumentacji Anthropic.
- Telegram Bot API, API LinkedIn i Facebooka: niesprawdzone.

## Pytania do właściciela
1. Czy w etapie 1 bot odpowiada tylko skryptem, bez modelu, do czasu sprawdzenia kosztu?
2. Tailscale w etapie 1 czy samo repozytorium GitHub jako droga Mac → PC?
3. Nazwy projektów i stany na Telegram, treść zadań tylko w prywatnym repozytorium?
