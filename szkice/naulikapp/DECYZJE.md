# Decyzje: NaulikApp

Każda decyzja to osobny wpis, najnowsze na górze. Nagłówek wpisu: `## RRRR-MM-DD: krótki tytuł`.
Uzupełnione danymi z PC (audyt 2026-11-14).

## 2026-11-14: Material Symbols zamiast własnych ikon, T48 niezbędne przed v1.0.0
- Kontekst: T41 zablokowane od 16.05; otwarte zadania T48.
- Decyzja: rezygnacja z MarineIcons.ttf na rzecz Material Symbols; przed v1.0.0 realizujemy wszystkie niezbędne zadania T48.
- Skutki: brakuje 12 testerów do zamkniętego testu; konto Google Play założone.
- Kto: właściciel

## 2026-10-27: Wydanie przez zamknięty test Google Play
- Kontekst: RC1 1.0.0+2 zmergowany (#121/#122).
- Decyzja: zamknięty test w Google Play (12+ testerów × 14 dni) do 2026-12-13, potem wniosek o produkcję; iOS poza v1; cel 500 instalacji do 2027-04-30.
- Skutki: blokery wydania: keystore, polityka prywatności, test akceptacyjny RC1, konto Play.
- Kto: właściciel

## 2026-05-28: v1.0.2 jako wydanie porządkowe przed v1.1
- Kontekst: po v1.0.0 i v1.0.1 zostały drobne znaleziska z autopilota i audytu testów.
- Decyzja: zebrać je w v1.0.2 (T34–T44), bez nowych funkcji; jedno źródło stanu zadań w `docs/backlog/STATUS.md`.
- Skutki: nowe funkcje dopiero w v1.1.0.
- Kto: właściciel, Claude Code

## 2026-05-16: UI zgodne z makietami (v1.0.1)
- Kontekst: audyt UI wykazał rozbieżności aplikacji z makietami.
- Decyzja: jasny motyw navy domyślnie, ciemny bursztynowy w profilu (T24); usunięte kafelki pulpitu (T26); konfiguracja jednostki odłożona z onboardingu (T28); ekran PDF jako podgląd (T33, opcja A).
- Skutki: makiety są wzorcem dla aplikacji.
- Kto: właściciel, Claude Code

## 2026-05-10: Rdzeń 12 modułów zamknięty, zakres MVP
- Kontekst: zakończone projektowanie modułów M-01 do M-12.
- Decyzja: MVP to fundament UI oraz moduły voyage, port-move i issues; specyfikacja UI w `docs/ui/UI-SPEC.md`.
- Skutki: pozostałe moduły rdzenia i infrastrukturalne do zaprojektowania lub zbudowania później.
- Kto: właściciel

## 2026-05-08: Free Tier bez synchronizacji, degradacja planu zachowuje dane
- Kontekst: zasady subskrypcji (F12) i zamykania rejsu.
- Decyzja: dane Free wyłącznie lokalne, bez wyjątków (F12); po spadku z premium do Free dane historyczne zostają (F22); zamknięty rejs jest niezmienny dla wpisów dziennika (F23).
- Skutki: backend obsługuje w Free tylko tożsamość OAuth.
- Kto: właściciel

## 2026-05-07: Fundamenty architektury F1–F20
- Kontekst: start projektowania architektury.
- Decyzja: aplikacja dla jednostek niegigantycznych (F1); dane lokalnie, chmura jako lustro (F8); sealed log z PDF lokalnie i w backendzie (F9); logowanie OAuth Google/Apple (F11); subskrypcja hybrydowa z Free Tier (F12); PIN tylko przy akcjach oficjalnych (F16); przytrzymanie przy akcjach nieodwracalnych (F19).
- Skutki: UI projektowany pod kapitana w trudnych warunkach (F15).
- Kto: właściciel
