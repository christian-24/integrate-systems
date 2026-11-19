# {{NAZWA}}: instrukcje dla agenta

@KARTA.md
@ZADANIA.md

<!-- standard-projektu:start -->
## Standard projektu
- Projekt prowadzimy według jednego standardu: KARTA.md (cel, zakres, zasady), ZADANIA.md (etapy, terminy, zadania), DECYZJE.md (dziennik decyzji), README.md i docs/ (dokumentacja), kampanie/ (kampanie).
- Stan pracy zapisuj wyłącznie w ZADANIA.md, w formacie opisanym na górze tego pliku. Zaczynasz zadanie: `[~]`. Kończysz: `[x]`. Nie możesz iść dalej: `[!]` i pole `blokada: powód`.
- Nowe zadanie bez terminu dopisz w sekcji „Do rozplanowania”. Nie twórz innych list zadań ani plików planu.
- Decyzję techniczną lub produktową dopisz do DECYZJE.md jako wpis `## RRRR-MM-DD: tytuł`.
- Zmieniasz architekturę, sposób uruchamiania albo wdrożenie: popraw odpowiedni plik w docs/ w tej samej zmianie. Nie zmieniaj nazw sekcji.
- Operacje z listy „Wymagają zgody właściciela” w KARTA.md oznacz polem `wymaga: zgoda` i zatrzymaj się przed ich wykonaniem.
- Uruchomienie z panelu (bez nadzoru): robisz jedno wskazane zadanie i zmieniasz tylko jego wiersz. Innych zadań, terminów i KARTA.md nie zmieniasz.
- Bez nadzoru nie wykonujesz działań nieodwracalnych ani wychodzących na zewnątrz (wysyłka, publikacja, wdrożenie, płatność): przygotuj, dopisz `wymaga: zgoda` i zatrzymaj się.
- Praca do przeglądu: zostaw `[~]` i dopisz `wymaga: odbiór`. Odpowiedź kończ trzema punktami: Zrobione, Sprawdzone, Zostało.
- Pytanie do właściciela (jedyna dozwolona zmiana KARTA.md) dopisz w sekcji „Pytania do właściciela”, pod nim wiersz `   propozycja: …` z Twoją rekomendacją. Odpowiedzi nie wpisujesz.
<!-- standard-projektu:end -->
