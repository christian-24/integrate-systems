# Zadania: Oprogramowani (integracje ERP ↔ sprzedaż)

> Jedyna lista zadań projektu. Czyta ją panel i agenci.
> Wiersz: `- [ ] Tytuł | kto: claude | gdzie: pc | kiedy: RRRR-MM-DD | pora: noc | czas: 30 | wymaga: zgoda`
> Stany: `[ ]` do zrobienia, `[~]` w toku, `[!]` zablokowane (dodaj `blokada: powód`), `[x]` zrobione.
> Pola są opcjonalne. kto: claude, codex, ty. gdzie: pc, mac, chmura. pora: dzień, noc. czas: minuty Twojej pracy. wymaga: zgoda, odbiór.
> Etap to nagłówek `## Etap: nazwa` i wiersz `termin: RRRR-MM-DD` pod nim. Etap bez otwartych zadań jest zamknięty.

> Uzupełnione danymi z PC (audyt 2026-11-14). `[x]` tylko dla rzeczy widocznych w plikach lub dokumentach.

## Etap: Narzędzia i wiedza

- [x] Biblioteka wiedzy: research, branża, uzasadnienia, walidacja
- [x] Narzędzie audytu z backendem i raportem PDF
- [x] Lokalny model AI w audycie (propozycje, gotowość, analiza)
- [x] Dokumentacja systemu śledzenia zleceń (scanner/)
- [ ] Wyjaśnić błąd 502 w ocenie gotowości AI | kto: claude | gdzie: mac
- [ ] Przetestować AI na 15 scenariuszach testowych | kto: claude | gdzie: mac | wymaga: odbiór

## Etap: Założenie firmy

- [x] Projekty umowy wspólników, NDA z klientem, umowy o dzieło i wdrożeniowej
- [x] Zgoda pracodawcy na działalność (dokument z 2026-10-27)
- [ ] Wybrać kancelarię i wysłać brief | kto: ty | wymaga: zgoda
- [x] Forma działalności: JDG + umowa o dzieło, sp. z o.o. później (D09, 2026-11-14)
- [ ] Podpisać umowę wspólników i zarejestrować firmę | kto: ty
- [x] Nazwa marki: Oprogramowani (strategia 2026-08-24)

## Etap: Walidacja rynku

- [x] Lista firm z danych publicznych: LeadyV2 ocenił 145 firm meblarskich (2026-09-02)
- [ ] Wybrać pierwsze 10 firm z listy LeadyV2 i przygotować szkice wiadomości | kto: claude | wymaga: odbiór
- [ ] Kontakt z wybranymi firmami z listy LeadyV2 | kto: ty
- [~] Plan 4 tygodni od 2026-10-28: 10 ofert, 3 rozmowy, 1 zlecenie; do 14.11 bez postępu | kto: ty
- [ ] Opisać nowy kanał rozmów z klientami | kto: ty | czas: 10
- [x] Oferta na Useme: 2500 zł, 7 dni (bez odpowiedzi do 14.11)
- [x] Asystent Useme na serwerze: usługa, 188 testów, bez automatycznej wysyłki i komentarzy (2026-11-17)
- [ ] Hasło do panelu zleceń: `ssh -t ops@2.29.181.133 sudo ustaw-haslo-zlecen` | kto: ty | czas: 2
- [ ] Przykładowy e-mail od Useme o nowym zleceniu (do napisania odczytu) | kto: ty | czas: 5
- [ ] Odczyt e-maili Useme na serwerze: zlecenia do asystenta, powiadomienie ntfy | kto: claude | gdzie: chmura
- [ ] Przenieść historię zleceń (data/jobs.db) z kopii PC na serwer | kto: claude | gdzie: chmura
- [ ] Przegląd skuteczności asystenta Useme (wysłane oferty, odpowiedzi, odrzucone zlecenia) | kto: claude | gdzie: chmura | wymaga: odbiór
- [ ] Przeprowadzić 5–10 rozmów walidacyjnych | kto: ty
- [ ] Konsultacja u radcy prawnego IT | kto: ty
- [ ] Walidacja cen i narzędzi u znajomej firmy z branży | kto: ty
- [ ] Zaktualizować białe plamy i decyzje po rozmowach | kto: claude | wymaga: odbiór

## Etap: Pilotaż u klienta 1

- [x] Narada nad MVP śledzenia zleceń i lista pytań do firmy
- [!] Uzyskać od klienta 1 odpowiedzi na pytania | kto: ty | blokada: brak klienta, najpierw pozyskanie klientów
- [!] Zdecydować: własna apka z kodami QR czy Prodio z wdrożeniem | kto: ty | blokada: brak klienta
- [ ] Przygotować ofertę pilotażu w trzech wariantach | kto: claude | wymaga: odbiór
- [ ] Uruchomić pilotaż na jednej linii i mierzyć pominięcia skanu | kto: ty

## Do rozplanowania

- [x] Zebrać nowsze materiały z PC (audyt 2026-11-14)
- [x] Zacommitować nieśledzone pliki w CompanyAudits (commit „wip: migracja z PC”, 2026-11-16)
- [x] Część Useme w osobnym repozytorium asystent-useme (2026-11-16)
- [ ] Materiał o infrastrukturze IT dla klienta 2: niewysłany; zdecydować, czy wysyłać | kto: ty
- [x] Strona oprogramowani.com, nowa wersja (2026-11-04)
