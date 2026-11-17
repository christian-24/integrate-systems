# Infrastruktura (serwer, GitHub, migracja z PC)

- faza: wdrozenie
- klient: nie
- próg: lekka
- stan: aktywny
- założono: 2026-11-17

Karta jest umową między właścicielem a agentami pracującymi w tym projekcie. Agent czyta ją na początku każdej sesji.

## Cel
Jedno stałe środowisko pracy w chmurze (D13): serwer z panelem, agentami i repozytoriami, dostępny z Maca i iPhone'a. Dane z PC zabezpieczone, PC sprzedany.

## Zakres
- Serwer Hetzner CAX11 (Arm, 2 vCPU, 4 GB, Helsinki), Ubuntu 26.04: użytkownik `ops` (administracja), `panel` (usługi i agenci, bez sudo), logowanie tylko kluczem, zapora SSH/HTTP/HTTPS, aktualizacje automatyczne, swap 2 GB.
- Panel jako usługa za Caddy z HTTPS i hasłem; repozytoria z GitHuba; dziennik aktywności z rozmów.
- Migracja danych z PC według `ksiega/MIGRACJA.md`.

## Poza zakresem
- Serwer Opisarni (Helsinki, x86): bez zmian.

## Definicja ukończenia
- Panel otwiera się z Maca i z iPhone'a spoza domu przez HTTPS z hasłem.
- Jedno zadanie agenta wykonane na serwerze.
- Dzień bez PC bez brakujących danych; PC zresetowany i sprzedany.

## Zasady pracy agentów
- Zmiany konfiguracji serwera, DNS, kluczy i kont tylko po zgodzie właściciela.
- Hasła i logowania wpisuje właściciel.

## Zasoby i ograniczenia
- Koszt serwera ok. 9,34 $/mies. z VAT (bez kopii zapasowych Hetznera).
