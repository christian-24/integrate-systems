# Decyzje: Oprogramowani – strona WWW

Każda decyzja to osobny wpis, najnowsze na górze. Nagłówek wpisu: `## RRRR-MM-DD: krótki tytuł`.

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
