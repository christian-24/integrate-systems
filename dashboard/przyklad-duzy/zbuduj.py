"""Duży zestaw testowy panelu w skali produkcji (dane syntetyczne, daty liczone od dziś).

Użycie:  python3 dashboard/przyklad-duzy/zbuduj.py <katalog>
Potem:   PANEL_REGISTRY=<katalog>/projekty.json PANEL_PORT=4803 python3 dashboard/server.py

Zawartość: 10 aktywnych projektów (nazwy z nawiasami i znakami „&”), 44 sprawy dla Ciebie, w tym 30 po terminie
(28 Twoich zadań i 2 zgody), 7 na dziś, 4 w ciągu 7 dni, 3 później; tytuły do 150 znaków; 12 publikacji w najbliższych
7 dniach; pytania z opcjami i propozycją, zgody, odbiory, zadania zablokowane, w toku i zrobione (postęp projektów).
Liczby są stałe (test_asystent_duzy.py je sprawdza): zmiana zestawu = zmiana testu.
"""
import datetime
import json
import os
import sys

TODAY = datetime.date.today()


def day(n):
    return (TODAY + datetime.timedelta(days=n)).isoformat()


LONG = [
    "Przygotuj i wyślij klientowi zestawienie zmian w umowie serwisowej wraz z harmonogramem wdrożenia i listą osób kontaktowych",
    "Sprawdź z księgowością rozliczenie faktur za trzeci kwartał, uzgodnij korekty i potwierdź terminy płatności z dostawcami",
    "Nagraj krótkie wideo z demonstracją nowego formularza zamówień dla zespołu sprzedaży, z napisami i wersją na telefon",
    "Uzgodnij z prawnikiem treść regulaminu promocji świątecznej, w tym zasady zwrotów, reklamacji i ochrony danych osobowych",
]
SHORT = ["Zatwierdź tekst na stronę główną", "Odpisz partnerowi w sprawie terminu", "Wybierz zdjęcie do wpisu",
         "Podpisz umowę z podwykonawcą", "Przejrzyj ofertę hostingu", "Zadzwoń do klienta w sprawie odbioru",
         "Uzupełnij dane do faktury", "Sprawdź wersję próbną aplikacji", "Wyślij materiały do drukarni",
         "Odpowiedz na pytania z ankiety", "Popraw opis produktu w sklepie", "Ustal termin spotkania z zespołem"]

PROJECTS = [
    # id, nazwa, faza, priorytet
    ("shield", "Shield & Silent (market research)", "budowa", 1),
    ("czesci", "Sklep z częściami (B2B, hurt)", "wdrozenie", 2),
    ("mobilna", "Aplikacja mobilna (iOS i Android)", "budowa", 2),
    ("firmowa", "Strona firmowa (nowa wersja 2027)", "marketing", 3),
    ("jesien", "Kampania jesienna (LinkedIn & newsletter)", "marketing", 3),
    ("portal", "Portal klienta (logowanie, faktury, zgłoszenia serwisowe)", "budowa", 3),
    ("erp", "Integracja ERP (zamówienia i stany magazynowe)", "wdrozenie", 4),
    ("wideo", "Kanał wideo (krótkie formy)", "marketing", 4),
    ("newsletter", "Newsletter (co tydzień)", "utrzymanie", 5),
    ("niemcy", "Badanie rynku (Niemcy, Austria)", "pomysl", 5),
]
PHASE_OUT = {"pomysl": "pomysł", "budowa": "budowa", "wdrozenie": "wdrożenie", "marketing": "marketing",
             "utrzymanie": "utrzymanie"}

LEGEND = "> Zestaw testowy panelu (dashboard/przyklad-duzy). Dane syntetyczne.\n"


def karta(name, phase, prio, questions):
    q = ""
    if questions:
        q = "\n## Pytania do właściciela\n" + "".join(questions)
    return ("# Karta projektu: %s\n\n- stan: aktywny\n- faza: %s\n- priorytet: %d\n- klient: nie\n- próg: lekka\n"
            "- maszyna: chmura\n- założono: %s\n\n## Cel\nProjekt testowy panelu.\n\n## Zakres\n- Zadania i publikacje "
            "w skali produkcji.\n\n## Poza zakresem\n- Prawdziwe dane.\n\n## Definicja ukończenia\n- Wszystkie zadania "
            "zrobione.\n%s" % (name, PHASE_OUT[phase], prio, day(-60), q))


def question(n, text, date, options, proposal, effects=()):
    out = "%d. %s\n" % (n, text)
    if date is not None:
        out += "   termin: %s\n" % day(date)
    out += "".join("   opcja: %s\n" % o for o in options)
    if proposal:
        out += "   propozycja: %s\n" % proposal
    out += "".join("   skutek: %s\n" % e for e in effects)
    return out


def build(root):
    os.makedirs(root, exist_ok=True)
    tasks = {pid: {"late": [], "now": [], "week": [], "later": [], "agent": [], "done": []} for pid, *_ in PROJECTS}
    ids = [p[0] for p in PROJECTS]
    # 28 Twoich zadań po terminie: po 3 w 8 projektach, po 2 w 2 projektach; co trzecie z długim tytułem
    k = 0
    for i, pid in enumerate(ids):
        for j in range(3 if i < 8 else 2):
            title = LONG[k % len(LONG)] if k % 3 == 0 else "%s (%s)" % (SHORT[k % len(SHORT)], j + 1)
            tasks[pid]["late"].append("- [ ] %s | kto: ty | kiedy: %s | czas: %d" % (title, day(-(k % 25) - 1), 30 + 15 * (k % 4)))
            k += 1
    # 2 zgody po terminie
    tasks["czesci"]["late"].append("- [ ] Wdróż nową wersję cennika hurtowego na produkcję | kto: claude | kiedy: %s | wymaga: zgoda" % day(-2))
    tasks["erp"]["late"].append("- [ ] Uruchom migrację stanów magazynowych z pliku z ostatniej inwentaryzacji | kto: codex | kiedy: %s | wymaga: zgoda" % day(-4))
    # dziś: 4 Twoje zadania, zgoda, odbiór (pytanie z terminem dziś jest w karcie)
    tasks["shield"]["now"].append("- [ ] %s | kto: ty | kiedy: %s | czas: 45" % (LONG[1], day(0)))
    tasks["mobilna"]["now"].append("- [ ] Przetestuj logowanie przez Apple na telefonie | kto: ty | kiedy: %s | czas: 20" % day(0))
    tasks["firmowa"]["now"].append("- [ ] Wybierz zdjęcia zespołu na stronę O nas | kto: ty | kiedy: %s | czas: 15" % day(0))
    tasks["newsletter"]["now"].append("- [ ] Przeczytaj szkic wydania i zgłoś uwagi | kto: ty | kiedy: %s" % day(0))
    tasks["portal"]["now"].append("- [ ] Włącz logowanie dwuskładnikowe dla wszystkich kont klientów portalu | kto: claude | kiedy: %s | wymaga: zgoda" % day(0))
    tasks["wideo"]["now"].append("- [ ] Zmontuj zapowiedź serii o kulisach produkcji | kto: claude | kiedy: %s | wymaga: odbiór\n  wynik: wideo/zapowiedz.mp4" % day(0))
    # 7 dni: 2 Twoje zadania, odbiór (pytanie z terminem +2 w karcie)
    tasks["jesien"]["week"].append("- [ ] Zatwierdź budżet reklam na listopad | kto: ty | kiedy: %s | czas: 20" % day(2))
    tasks["niemcy"]["week"].append("- [ ] Umów rozmowy z trzema dystrybutorami | kto: ty | kiedy: %s | czas: 60" % day(5))
    tasks["erp"]["week"].append("- [ ] Przygotuj raport różnic stanów między ERP a sklepem | kto: claude | kiedy: %s | wymaga: odbiór\n  wynik: raport-roznic.md" % day(3))
    # później: 2 Twoje zadania (pytanie bez terminu w karcie)
    tasks["portal"]["later"].append("- [ ] Zdecyduj o dostawcy poczty transakcyjnej | kto: ty | kiedy: %s | czas: 30" % day(20))
    tasks["czesci"]["later"].append("- [ ] Spisz wymagania do programu lojalnościowego | kto: ty | czas: 60")
    # agenci i zrobione: postęp różny w każdym projekcie
    for i, pid in enumerate(ids):
        for j in range(2 + i % 4):
            tasks[pid]["done"].append("- [x] Zadanie zrobione %d w projekcie | kto: claude" % (j + 1))
        tasks[pid]["agent"].append("- [ ] Opisz wyniki testów z ostatniego tygodnia | kto: claude | kiedy: %s" % day(1 + i % 5))
        if i % 3 == 0:
            tasks[pid]["agent"].append("- [~] Napraw testy formularza zamówień | kto: codex | kiedy: %s" % day(0))
        if i % 4 == 1:
            tasks[pid]["agent"].append("- [!] Podłącz bramkę płatności testowej | kto: codex | blokada: brak klucza testowego operatora")
    questions = {
        "shield": [question(1, "Czy w raporcie z badania pokazujemy nazwy konkurentów, czy tylko kategorie rynku?", 0,
                            ["nazwy konkurentów", "tylko kategorie"], "tylko kategorie",
                            ["kiedy: %s → Przygotuj raport końcowy" % day(4)])],
        "jesien": [question(1, "Który kanał dostaje większą część budżetu w listopadzie: LinkedIn czy newsletter?", 2,
                            ["LinkedIn", "newsletter", "po równo"], "LinkedIn")],
        "niemcy": [question(1, "Czy badanie obejmuje też Szwajcarię?", None, ["tak", "nie"], "")],
    }
    paths = []
    for i, (pid, name, phase, prio) in enumerate(PROJECTS):
        folder = os.path.join(root, pid)
        os.makedirs(os.path.join(folder, "kampanie"), exist_ok=True)
        T = tasks[pid]
        body = ["# Zadania: %s" % name, "", LEGEND]
        if i in (1, 4):      # etap po terminie bez Twoich zadań (ryzyko projektu, nie zmienia liczby spraw)
            body += ["## Etap: Poprzedni etap", "termin: %s" % day(-5), "",
                     "- [x] Zadanie zamknięte w poprzednim etapie | kto: claude",
                     "- [ ] Dokończ opis zmian z poprzedniego etapu | kto: claude | kiedy: %s" % day(-5), ""]
        body += ["## Etap: Bieżące sprawy", "termin: %s" % day(6), ""]
        body += T["done"][:2] + T["late"] + T["now"]
        body += ["", "## Etap: Następne kroki", "termin: %s" % day(14 + i), ""] + T["done"][2:] + T["week"] + T["agent"]
        body += ["", "## Do rozplanowania", ""] + T["later"] + [""]
        with open(os.path.join(folder, "ZADANIA.md"), "w", encoding="utf-8") as f:
            f.write("\n".join(body))
        with open(os.path.join(folder, "KARTA.md"), "w", encoding="utf-8") as f:
            f.write(karta(name, phase, prio, questions.get(pid)))
        for doc in ("DECYZJE.md", "README.md"):
            with open(os.path.join(folder, doc), "w", encoding="utf-8") as f:
                f.write("# %s\n\n_Do uzupełnienia._\n" % doc[:-3].capitalize())
        paths.append(folder)
    # 12 publikacji w najbliższych 7 dniach (agenci, bez zgody: nie liczą się do spraw dla Ciebie)
    pubs = {
        "jesien": [(0, "LinkedIn", "Jak skrócić obsługę zamówień o połowę: przykład klienta z branży części zamiennych i wnioski po trzech miesiącach"),
                   (1, "newsletter", "Newsletter nr 4: zapowiedź webinaru"), (2, "LinkedIn", "Kulisy pracy zespołu wsparcia"),
                   (4, "LinkedIn", "Pięć pytań, które zadają nam klienci przed wdrożeniem"), (6, "newsletter", "Podsumowanie miesiąca")],
        "wideo": [(0, "YouTube", "Krótki film: nowy formularz zamówień w 30 sekund"), (2, "Instagram", "Zapowiedź serii o kulisach produkcji (odcinek 1 z 6)"),
                  (3, "YouTube", "Krótki film: pytania od widzów"), (5, "Instagram", "Relacja z targów branżowych w Poznaniu, część druga: rozmowy z wystawcami i nowości")],
        "firmowa": [(1, "LinkedIn", "Nowa strona firmowa: co się zmieniło"), (3, "X", "Wątek: trzy błędy przy wyborze dostawcy"),
                    (6, "LinkedIn", "Zespół: poznaj osoby od wdrożeń")],
    }
    for pid, items in pubs.items():
        lines = ["# Kampania: Publikacje testowe", "", "- stan: w toku", "- cel: Zestaw testowy", "- cel liczbowy: 100",
                 "- kanały: LinkedIn, newsletter", "- start: %s" % day(-10), "- koniec: %s" % day(30), "", "## Harmonogram"]
        lines.append("- [x] Wpis zrobiony wcześniej | kanał: LinkedIn | kiedy: %s | kto: claude" % day(-3))
        lines += ["- [ ] %s | kanał: %s | kiedy: %s | kto: claude" % (t, ch, day(d)) for d, ch, t in items]
        with open(os.path.join(root, pid, "kampanie", "publikacje-testowe.md"), "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    with open(os.path.join(root, "projekty.json"), "w", encoding="utf-8") as f:
        json.dump({"projekty": paths}, f, ensure_ascii=False, indent=2)
    return root


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Użycie: python3 dashboard/przyklad-duzy/zbuduj.py <katalog>")
    print(build(os.path.abspath(sys.argv[1])))
