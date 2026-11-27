# Strona: zaczynamy od problemu klienta, każda obietnica raz (uwagi właściciela 27.11)

Słowa właściciela 27.11: „demo 5 razy jest demo… that's not the point”. Hasła powtarzają się w kilku miejscach: „Najpierw widzisz, potem płacisz”, „Bezpłatna wycena”, „Co robimy”, „Od wyceny do opieki”, „Zanim zadzwonisz”. Właściciel podał chwyty, od których strona ma zaczynać:
- „Denerwują cię koszty ERP?”
- „Kolejny integrator mówi, że zajmie to 3 miesiące?”
- „Podają nieludzkie pieniądze za prosty moduł?”
- „Zintegrowałeś i po raz kolejny system nie działa?”

Kierunek właściciela z 26.11:
- „Po co ci wielki ERP?”
- „Nie wydawaj pieniędzy na ERP-a.”
- „Dobierzemy produkt dla ciebie, a jeśli wystarczy mały program, napiszemy go.”
- „Nie jesteśmy partnerami Comarcha.”
- „Najpierw zobacz, dostosujemy do twojego środowiska.”

## Zasada
Każda obietnica pada na stronie głównej najwyżej raz:
- pokaz działającego programu,
- bezpłatna wycena,
- stała cena,
- odbiór etapami,
- opieka.

Przycisk „Bezpłatna wycena” może być w menu, w hero i w kontakcie, bo to przycisk, nie zdanie. Słowo „demo” pada na stronie głównej najwyżej 2 razy: w jednej karcie problemu i w cenniku.

## Strona główna, nowa kolejność
1. **Hero**
   - h1a: „Po co Ci wielki ERP?”
   - h1b: „Napiszemy prosty program pod Twoją firmę.”
   - lead: „Albo połączymy programy, które już masz.”
   - cta: „Bezpłatna wycena”
   - Usuń „Najpierw demo. Potem płacisz.”
2. **Nowa sekcja „Brzmi znajomo?”** zastępuje „Jak to działa: Od wyceny do opieki” z 4 krokami. Kroki usuń w całości. Ma 4 karty, każda to problem i jedna linia odpowiedzi:
   - „Koszty ERP rosną bez końca”: „Licencje, wdrożenie, konsultanci, a połowa firmy i tak pracuje w Excelu.” Odpowiedź: „Robimy tylko to, czego potrzebujesz, za stałą cenę podaną na piśmie przed startem.”
   - „Kolejny integrator mówi: 3 miesiące”: „Na prostą rzecz czekasz kwartał, zanim cokolwiek zobaczysz.” Odpowiedź: „Działający program na przykładowych danych pokazujemy w 1–2 dni po wycenie.”
   - „Cena jak za cały system, a chodzi o jeden moduł”: „Za jedną funkcję dostajesz ofertę jak za wdrożenie całej firmy.” Odpowiedź: „Płacisz za ten jeden moduł, nie za system dookoła.”
   - „Zintegrowane, a znowu nie działa”: „Po wdrożeniu coś się sypie, a integrator nie odbiera.” Odpowiedź: „Płacisz za etap, gdy działa u Ciebie. Potem dzwonisz do Pawła albo Krystiana, nie na infolinię.”
   - Warunek zaliczki: zdanie „Płacisz za etap, gdy działa u Ciebie” bierz z GWAR_ETAP w tresc-pl.js, bo przy zaliczce brzmi inaczej.
3. **Kafelki 4 linii oferty**, bez zmian w treści kafelków.
   - Nagłówek „Co robimy” zamień na „Planowanie, integracje, Excel, IT”, albo usuń nagłówek, jeśli kafelki są czytelne bez niego.
4. **Ceny**
   - h2a: „Ile to kosztuje.”
   - h2b: „Cenę znasz na piśmie, zanim zaczniemy.”
   - lead: „Płacisz za wdrożenie, a za opiekę tylko wtedy, gdy jej chcesz.”
   - Pozycje bez zmian: Wycena 0 zł, Demo 0 zł, Wdrożenie, Opieka. Opis pozycji Demo: „Działający program na przykładowych danych, zanim zdecydujesz. Robimy go, gdy zlecenie jest opisane, a widełki ceny potwierdzone.”
   - Bloki „Co płacisz poza nami”, VAT i warunki zostają bez zmian.
5. **Bez ryzyka**: „Dokładamy, nie wymieniamy.” zostaje z 2 kartami. W pierwszej karcie dopisz na końcu: „Nie jesteśmy partnerem żadnego producenta, więc nie musimy Ci niczego sprzedawać.” W stopce już jest zdanie o braku partnerstwa, więc to jest prawdziwe.
6. **Pytania „Zanim zadzwonisz”**: usuń całą sekcję (wszystkie 3 pytania powtarzają resztę strony).
7. **Kontakt**
   - h2a: „Bezpłatna wycena.”
   - h2b: „Zadzwoń, napisz albo zostaw prośbę.”
   - p: „Opisz, co ma działać. W ciągu dnia oddzwonimy z widełkami ceny.” (bez „terminu dema” i bez „Bez prezentacji i bez zobowiązań”)
8. **Meta**
   - title: „Oprogramowani — prosty program zamiast wielkiego ERP-a”
   - opis: „Programy i dodatki dla małych firm: planowanie produkcji, integracje Optima, Subiekt, BaseLinker i KSeF, Excel, IT. Stała cena na piśmie. Bezpłatna wycena.”
   - og: „Po co Ci wielki ERP? Napiszemy prosty program pod Twoją firmę.”
9. **Menu**: link „Jak to działa” prowadził do usuniętych kroków. Zamień go na „Problemy” (kotwica do sekcji „Brzmi znajomo?”) albo usuń.

## Podstrony (/pl/planowanie-produkcji, /integracje, /excel, /it)
- meta opis: usuń „Najpierw demo, potem płacisz.” Zostaje „Bezpłatna wycena.”
- Sekcja demo: zostaw jedno zdanie o pokazie. Usuń „Nie płacisz, jeśli nie chcesz dalej.” i warunek dema (DEMO_WARUNEK), bo te zdania są w cenniku.
- cenaBrak: „Cenę podajemy w bezpłatnej wycenie, w ciągu dnia.”
- Podstrona integracje: trzeci problem „Faktury dwa razy” zamień na:
  - h: „Zintegrowane, a znowu nie działa”
  - p: „Programy połączył integrator. Po aktualizacji przestały się dogadywać, a do niego nie można się dodzwonić.”
  - KSeF zostaje w liście „Co robimy” tej podstrony.
- Podstrona IT: zostaw miejsce [UZUPEŁNIJ] o planie i oględzinach.

## Bez zmian, nic nie wymyślone
- Dane firmy, ceny, miejsca [UZUPEŁNIJ] i dane.js zostają.
- Nie dodawaj kwot wdrożeń ERP (właściciel mówił o 2–4 mln, ale to nie jest sprawdzona liczba, nie wpisuj jej).
- Nie dodawaj opinii ani realizacji klientów.

## Języki
- DE, IT i EN: ta sama struktura i ten sam sens, w naturalnym języku danego kraju. Nie tłumacz słowo w słowo.
- Polskie nazwy programów zostają.
