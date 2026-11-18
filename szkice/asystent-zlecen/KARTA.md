# Szukanie auta (asystent OLX i OTOMOTO)

- faza: budowa
- klient: nie
- próg: lekka
- stan: aktywny
- maszyna: chmura
- repozytorium: serwer `~/projekty/szukanie-auta` (GitHub, od 2026-11-16); rozszerzenie w Chrome na Macu; wcześniej PC `C:\Users\Guest\Zlecenia`
- założono: 2026-10-29

Szkic tylko z audytu PC z 2026-11-14 (sesje Codex i pliki folderu). Kodu nie czytano.
Część Useme i Facebooka należy do projektu Oprogramowani (właściciel, 2026-11-14); ta karta obejmuje tylko szukanie auta.
30 sesji Codex od 29.10 do 13.11, w tym 18 w ostatnich 14 dniach; log z 14.11, działa codziennie.

Karta jest umową między właścicielem a agentami pracującymi w tym projekcie. Agent czyta ją na początku każdej sesji.

## Cel
Prywatne narzędzie do szukania samochodu: przegląda ogłoszenia na OLX i OTOMOTO i ocenia je według kryteriów właściciela. Ma oszczędzić codzienne przeglądanie portali.

## Zakres
- Backend w Pythonie i rozszerzenie Chrome.
- Rozszerzenie „Asystent aut OLX + OTOMOTO” (wersja 2.12.0): indeks 1,5–2,7 tys. ofert, analiza AI według kryteriów, harmonogram.
- Panel „Garaż” z wynikami.
- Analizy przez Codex CLI na koncie ChatGPT (wcześniej OpenAI API).

## Poza zakresem
- Monitoring Useme i Facebooka (projekt Oprogramowani).
- Kontakt ze sprzedającymi bez zgody właściciela.
- _Do uzupełnienia._

## Definicja ukończenia
_Do uzupełnienia: kiedy narzędzie jest gotowe (np. codzienny raport zleceń i aut bez ręcznej pracy)._

## Zasady pracy agentów
- Poziom swobody: 1 (agent przygotowuje szkice, nie wysyła ofert i nie pisze do sprzedających).
- Wymagają zgody właściciela: wysłanie oferty na Useme, kontakt ze sprzedającym, wydatki, logowanie na konta portali.
- Agent nie wpisuje haseł.
- Stan pracy agent zapisuje w ZADANIA.md, decyzje w DECYZJE.md.

## Zasoby i ograniczenia
- Praca tylko na PC; Codex Desktop od 29.10.
- Środki na OpenAI API wyczerpane; analizy idą przez Codex CLI.
- Folder wspólny z częścią Useme; do rozdzielenia na dwa repozytoria.

## Pytania do właściciela
1. Czy zlecenia (Useme, Facebook) i samochody (OLX, OTOMOTO) to jeden projekt, czy dwa osobne?
   Odpowiedź: Nie dwa osobne, jedno to szukanie auta a drugie to cos bardzo ważnego, useme są połączeni z oprogramowani
2. Czy założyć dla tego folderu repozytorium git, żeby zmiany były zapisane?
   Odpowiedź: Tak jak napisalem, to osobne rzeczy
3. Czy oferta na Useme (2500 zł, 7 dni) została wysłana i jaki jest jej wynik?
   Odpowiedź: Nic nie odpisal\
