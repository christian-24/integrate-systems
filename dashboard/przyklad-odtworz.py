"""Zapisuje trzy projekty przykładowe w standardzie (daty względne wobec dzisiaj)."""
import datetime, os, shutil, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT + "/standard")
import projekt as P
OUT = ROOT + "/dashboard/przyklad"
LEGEND = """> Jedyna lista zadań projektu. Czyta ją panel i agenci.
> Wiersz: `- [ ] Tytuł | kto: claude | gdzie: pc | kiedy: RRRR-MM-DD | pora: noc | czas: 30 | wymaga: zgoda`
> Stany: `[ ]` do zrobienia, `[~]` w toku, `[!]` zablokowane (dodaj `blokada: powód`), `[x]` zrobione.
> Projekt przykładowy: daty zapisane względnie (`+3` to za trzy dni), żeby przykład był zawsze aktualny.
"""
RULES = """## Zasady pracy agentów
- Poziom swobody: 2 (pracuje sam, pyta o ryzyko).
- Zgody właściciela wymagają: wdrożenie, migracja danych, `git push --force`, usuwanie danych, wydatki.
- Stan pracy agent zapisuje w ZADANIA.md, decyzje w DECYZJE.md.
"""

def karta(name, machine, goal, scope, out, done, fields=""):
    return """# Karta projektu: %s

- stan: aktywny
%s- maszyna: %s
- repozytorium: github.com/przyklad/%s
- założono: -30

## Cel
%s

## Zakres
%s

## Poza zakresem
%s

## Definicja ukończenia
%s

%s
## Zasoby i ograniczenia
- Budżet miesięczny na agentów: 150 zł.
""" % (name, fields, machine, name, goal, scope, out, done, RULES)

def doc(title, sections):
    return "# %s\n\n" % title + "\n".join("## %s\n%s\n" % (h, b) for h, b in sections)

TODO = "_Do uzupełnienia._"
DOCS_LINKS = "- [Karta projektu](KARTA.md)\n- [Zadania](ZADANIA.md)\n- [Decyzje](DECYZJE.md)\n- [Architektura](docs/ARCHITEKTURA.md)\n- [Uruchomienie](docs/URUCHOMIENIE.md)"

F = {}

# ------------------------------------------------------------------ sklep-api (komplet)
F["sklep-api/KARTA.md"] = karta("sklep-api", "pc",
    "API sklepu: koszyk, zamówienia, płatności testowe.",
    "- Koszyk z rabatami.\n- Zamówienia i eksport do CSV.\n- Płatności w trybie testowym operatora.",
    "- Płatności produkcyjne.\n- Panel administracyjny.",
    "- Testy przechodzą w CI.\n- Staging przyjmuje zamówienie z płatnością testową.",
    "- faza: wdrożenie\n- klient: tak\n- próg: pełna\n")
F["sklep-api/ZADANIA.md"] = """# Zadania: sklep-api

%s
## Etap: Rabaty w koszyku
termin: -1

- [x] Model kodu rabatowego | kto: claude | gdzie: pc
- [x] Naliczanie rabatu w koszyku | kto: claude | gdzie: pc
- [x] Testy rabatów | kto: codex | gdzie: chmura

## Etap: Eksport zamówień do CSV
termin: +3

- [x] Format pliku i lista kolumn | kto: ty | czas: 15
- [~] Eksport CSV: zapis strumieniowy | kto: claude | gdzie: pc | kiedy: +0 | pora: noc
- [ ] Eksport CSV: testy i PR | kto: claude | gdzie: pc | kiedy: +2 | pora: dzień

## Etap: Płatności testowe na stagingu
termin: +11

- [x] Konto testowe u operatora płatności | kto: ty | czas: 20
- [ ] Migracja discount_code | kto: claude | gdzie: pc | kiedy: +1 | pora: dzień | wymaga: zgoda
- [!] Webhook potwierdzenia płatności | kto: codex | gdzie: chmura | blokada: brak klucza testowego operatora
- [ ] Płatności testowe: integracja | kto: claude | gdzie: pc | kiedy: +7 | pora: noc

## Do rozplanowania
- [ ] Limit zapytań na klucz API | kto: codex
- [ ] Opis punktów końcowych w OpenAPI
""" % LEGEND
F["sklep-api/DECYZJE.md"] = """# Decyzje: sklep-api

Najnowsze na górze. Nagłówek wpisu: `## RRRR-MM-DD: krótki tytuł`.

## -3: Eksport CSV zapisujemy strumieniowo
- Kontekst: przy 50 tys. zamówień eksport w pamięci przekraczał limit kontenera.
- Decyzja: zapis strumieniowy, plik powstaje wiersz po wierszu.
- Skutki: brak sortowania po stronie API, sortuje zapytanie do bazy.
- Kto: Ty, na wniosek Claude Code.

## -12: Rabaty liczymy po stronie API
- Kontekst: aplikacja mobilna i strona liczyły rabat inaczej.
- Decyzja: jedyne źródło ceny po rabacie to API.
- Skutki: klienci nie liczą cen lokalnie.
- Kto: Ty.
"""
F["sklep-api/README.md"] = doc("sklep-api", [
    ("Co to jest", "API sklepu: koszyk, zamówienia i płatności w trybie testowym."),
    ("Jak uruchomić", "`make dev` uruchamia API na porcie 8000. Szczegóły: docs/URUCHOMIENIE.md."),
    ("Struktura", "- `api/` punkty końcowe\n- `core/` logika koszyka i zamówień\n- `tests/` testy"),
    ("Dokumentacja", DOCS_LINKS)])
F["sklep-api/docs/ARCHITEKTURA.md"] = doc("Architektura: sklep-api", [
    ("Przegląd", "Jedna usługa HTTP z bazą PostgreSQL. Klienci: aplikacja iOS i strona."),
    ("Komponenty", "- API (FastAPI)\n- Kolejka zadań eksportu\n- Moduł płatności testowych"),
    ("Dane", "Tabele: cart, cart_item, order, discount_code. Migracje w `migrations/`."),
    ("Integracje", "Operator płatności (tryb testowy), poczta transakcyjna.")])
F["sklep-api/docs/URUCHOMIENIE.md"] = doc("Uruchomienie: sklep-api", [
    ("Wymagania", "Python 3.12, Docker."),
    ("Uruchomienie lokalne", "`make dev`"),
    ("Testy", "`make test`"),
    ("Wdrożenie", "Staging wdraża się po scaleniu do `main`. Wdrożenie wymaga zgody właściciela.")])

# ------------------------------------------------------------------ apka-ios (luki w architekturze, brak AGENTS.md)
F["apka-ios/KARTA.md"] = karta("apka-ios", "mac",
    "Aplikacja mobilna sklepu na iPhone’a.",
    "- Logowanie i koszyk.\n- Wersja beta dla testerów w TestFlight.",
    "- Wersja na iPada.\n- Płatności w aplikacji.",
    "- Wersja beta dostępna dla 20 testerów.\n- Brak błędów krytycznych z pierwszego tygodnia testów.",
    "- faza: budowa\n- klient: tak\n- próg: lekka\n")
F["apka-ios/ZADANIA.md"] = """# Zadania: apka-ios

%s
## Etap: Ekran logowania
termin: +1

- [x] Formularz logowania | kto: claude | gdzie: mac
- [x] Obsługa błędów logowania | kto: claude | gdzie: mac
- [x] Testy interfejsu logowania | kto: codex | gdzie: mac
- [ ] Odbiór PR #17: logowanie na iPhonie | kto: ty | kiedy: +1 | pora: dzień | czas: 30 | wymaga: odbiór

## Etap: Wersja beta w TestFlight
termin: +9

- [x] Konto deweloperskie i certyfikaty | kto: ty | czas: 40
- [x] Ikona i ekran startowy | kto: codex | gdzie: mac
- [ ] Onboarding: szkic ekranów | kto: codex | gdzie: pc | kiedy: +4 | pora: dzień
- [ ] Beta: zrzuty ekranu i opis | kto: codex | gdzie: mac | kiedy: +8 | pora: dzień
- [ ] Wysłanie wersji do TestFlight | kto: ty | czas: 20

## Do rozplanowania
- [ ] Tryb ciemny
""" % LEGEND
F["apka-ios/DECYZJE.md"] = """# Decyzje: apka-ios

Najnowsze na górze. Nagłówek wpisu: `## RRRR-MM-DD: krótki tytuł`.

## -6: Logowanie kodem z e-maila zamiast hasła
- Kontekst: hasła wymagały ekranu resetu i dodatkowych testów.
- Decyzja: logowanie jednorazowym kodem z e-maila.
- Skutki: mniej ekranów, zależność od poczty transakcyjnej.
- Kto: Ty.
"""
F["apka-ios/README.md"] = doc("apka-ios", [
    ("Co to jest", "Aplikacja sklepu na iPhone’a (SwiftUI)."),
    ("Jak uruchomić", "Otwórz `Sklep.xcodeproj` i uruchom schemat `Sklep` na symulatorze."),
    ("Struktura", "- `Sklep/` kod aplikacji\n- `SklepTests/` testy"),
    ("Dokumentacja", DOCS_LINKS)])
F["apka-ios/docs/ARCHITEKTURA.md"] = doc("Architektura: apka-ios", [
    ("Przegląd", "Aplikacja SwiftUI, stan w obiektach obserwowalnych, dane z API sklepu."),
    ("Komponenty", "- Ekrany: logowanie, lista produktów, koszyk\n- Klient API"),
    ("Dane", TODO), ("Integracje", TODO)])
F["apka-ios/docs/URUCHOMIENIE.md"] = doc("Uruchomienie: apka-ios", [
    ("Wymagania", "Xcode 26, symulator iPhone’a."),
    ("Uruchomienie lokalne", "Schemat `Sklep`, konfiguracja Debug."),
    ("Testy", "`xcodebuild test -scheme Sklep`"),
    ("Wdrożenie", "Archiwum z Xcode i wysyłka do TestFlight. Wymaga zgody właściciela.")])
F["apka-ios/kampanie/nabor-testerow-wersji-beta.md"] = """# Kampania: Nabór testerów wersji beta

- stan: plan
- cel: Zebrać testerów wersji beta przed wysyłką do TestFlight
- miernik: zgłoszenia testerów
- cel liczbowy: 20
- wynik: 0
- kanały: LinkedIn, e-mail
- start: +6
- koniec: +20
- budżet: 0 zł

## Grupa docelowa
Obecni klienci sklepu z iPhone’em, którzy kupili co najmniej dwa razy.

## Przekaz
%s

## Harmonogram
- [ ] Zaproszenie do testów dla klientów | kanał: e-mail | kiedy: +6 | kto: claude | wymaga: zgoda
- [ ] Wpis: szukamy testerów | kanał: LinkedIn | kiedy: +7 | kto: claude
- [ ] Przypomnienie dla niezdecydowanych | kanał: e-mail | kiedy: +13 | kto: codex

## Wyniki i wnioski
%s
""" % (TODO, TODO)

# ------------------------------------------------------------------ landing (luki w README, brak docs/URUCHOMIENIE.md)
F["landing/KARTA.md"] = karta("landing", "pc",
    "Strona produktu z formularzem kontaktowym.",
    "- Strona główna z opisem produktu.\n- Formularz kontaktowy z ochroną przed spamem.",
    "- Blog.\n- Wersje językowe.",
    "- Strona opublikowana pod domeną produktu.\n- Formularz dostarcza wiadomości na skrzynkę.",
    "- klient: nie\n- próg: lekka\n")      # bez „faza:”: faza wyliczona (kampania w toku -> marketing)
F["landing/ZADANIA.md"] = """# Zadania: landing

%s
## Etap: Teksty na stronę główną
termin: -2

- [x] Nagłówek i opis produktu | kto: claude | gdzie: pc
- [x] Sekcja pytań i odpowiedzi | kto: claude | gdzie: pc
- [ ] Poprawki tekstów po terminie | kto: ty | kiedy: +2 | pora: dzień | czas: 45

## Etap: Formularz kontaktowy
termin: +2

- [x] Makieta formularza | kto: codex | gdzie: chmura
- [~] Naprawa testów formularza | kto: claude | gdzie: pc | kiedy: +0 | pora: dzień
- [ ] Formularz: walidacja i wysyłka | kto: codex | gdzie: chmura | kiedy: +1 | pora: noc
- [ ] Ochrona przed spamem | kto: claude | gdzie: pc

## Etap: Publikacja strony
termin: +18

- [ ] Domena i certyfikat | kto: ty | czas: 30
- [ ] Polityka prywatności | kto: claude | gdzie: pc
- [ ] Pomiar ruchu bez plików cookie | kto: codex | gdzie: chmura
- [ ] Publikacja | kto: claude | gdzie: pc | wymaga: zgoda

## Do rozplanowania
""" % LEGEND
F["landing/DECYZJE.md"] = """# Decyzje: landing

Najnowsze na górze. Nagłówek wpisu: `## RRRR-MM-DD: krótki tytuł`.

## -8: Strona statyczna bez systemu CMS
- Kontekst: treść zmienia się rzadko, a CMS to dodatkowe utrzymanie.
- Decyzja: strona statyczna, teksty w plikach Markdown.
- Skutki: zmiany tekstów przez repozytorium.
- Kto: Ty.

## -15: Lista oczekujących przed publikacją
- Kontekst: chcemy sprawdzić zainteresowanie przed startem.
- Decyzja: formularz zapisu i kampania „Lista oczekujących przed startem”.
- Skutki: formularz musi działać przed publikacją pełnej strony.
- Kto: Ty.
"""
F["landing/README.md"] = doc("landing", [
    ("Co to jest", "Strona produktu z formularzem kontaktowym i zapisem na listę oczekujących."),
    ("Jak uruchomić", "`npm run dev`"),
    ("Struktura", TODO),
    ("Dokumentacja", DOCS_LINKS)])
F["landing/docs/ARCHITEKTURA.md"] = doc("Architektura: landing", [
    ("Przegląd", "Strona statyczna generowana przy budowaniu, formularz obsługuje funkcja bezserwerowa."),
    ("Komponenty", "- Strona główna\n- Formularz kontaktowy\n- Funkcja wysyłki wiadomości"),
    ("Dane", "Zgłoszenia z formularza trafiają na skrzynkę i do arkusza listy oczekujących."),
    ("Integracje", "Poczta transakcyjna, dostawca hostingu.")])
F["landing/kampanie/lista-oczekujacych-przed-startem.md"] = """# Kampania: Lista oczekujących przed startem

- stan: w toku
- cel: Zebrać listę osób zainteresowanych przed publikacją strony
- miernik: zapisy na listę
- cel liczbowy: 200
- wynik: 64
- kanały: LinkedIn, newsletter, X
- start: -7
- koniec: +18
- budżet: 300 zł

## Grupa docelowa
Właściciele małych sklepów internetowych, którzy sami prowadzą sprzedaż i obsługę klienta.

## Przekaz
Mniej ręcznej pracy przy zamówieniach: jeden panel zamiast trzech narzędzi. Zapis na listę daje dostęp w pierwszej turze.

## Harmonogram
- [x] Zapowiedź produktu | kanał: LinkedIn | kiedy: -7 | kto: ty
- [x] Wątek: problem, który rozwiązujemy | kanał: X | kiedy: -4 | kto: claude
- [ ] Newsletter nr 1: zaproszenie na listę | kanał: newsletter | kiedy: -1 | kto: claude | wymaga: zgoda
- [ ] Wpis z demonstracją formularza | kanał: LinkedIn | kiedy: +3 | kto: claude
- [ ] Wątek: kulisy budowy | kanał: X | kiedy: +8 | kto: codex
- [ ] Newsletter nr 2: data startu | kanał: newsletter | kiedy: +15 | kto: ty | czas: 30

## Wyniki i wnioski
%s
""" % TODO

F["raport.md"] = """## Najważniejsze
- landing: etap „Teksty na stronę główną” jest 2 dni po terminie, zostało 1 zadanie.
- landing: „Formularz kontaktowy” ma 3 otwarte zadania na 2 dni.
- sklep-api: webhook płatności stoi, brakuje klucza testowego operatora.

## Proponuję
- **Zgoda na migrację discount_code** dziś, Claude wykona ją jutro w dzień.
- **Odbiór PR #17** jutro rano, 30 minut; to zamyka etap „Ekran logowania”.
- Przesunąć termin „Formularza kontaktowego” o 2 dni albo zdjąć z etapu jedno zadanie.
"""

if os.path.isdir(OUT):
    shutil.rmtree(OUT)
today = datetime.date.today()
for name, agents in (("sklep-api", True), ("apka-ios", False), ("landing", True)):
    F[name + "/CLAUDE.md"] = P._fill(P.read(P.TEMPLATE + "/CLAUDE.md"), name, today)
    if agents:
        F[name + "/AGENTS.md"] = P._fill(P.read(P.TEMPLATE + "/AGENTS.md"), name, today)
for rel, body in F.items():
    path = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
print(len(F), "plików")
