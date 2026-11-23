# Decyzje: Infrastruktura

Każda decyzja to osobny wpis, najnowsze na górze. Nagłówek wpisu: `## RRRR-MM-DD: krótki tytuł`.

## 2026-11-24: Konektory agentów przez własną konfigurację na projekt
- Kontekst: konektory z claude.ai są wspólne dla całego konta, nie dają zakresu do jednego folderu ani twardego trybu tylko do odczytu; uruchomienia z panelu mają je wyłączone (`--strict-mcp-config`). Google Drive i Notion nie są podłączone na koncie.
- Decyzja: agenci nie używają konektorów konta. Dostęp nadaje panel na projekt: Google Drive przez rclone (`drive.readonly`, jeden folder, montowanie tylko do odczytu), Notion przez własną integrację z uprawnieniem odczytu w pliku `--mcp-config` projektu. `--strict-mcp-config` zostaje.
- Skutki: pole konektorów w karcie wskazuje konfigurację projektu, nie konektor konta; projekt bez wpisu nie ma dostępu. Token integracji Notion musi być czytelny dla procesu agenta, dlatego tylko odczyt i tylko wybrane strony. Odwracalne: wystarczy zdjąć flagę i wpis.
- Kto: agent

## 2026-11-17: Osobny serwer Arm dla panelu i agentów
- Kontekst: tani CX23 w Niemczech niedostępny po usunięciu; rozważane współdzielenie serwera Opisarni.
- Decyzja: osobny CAX11 (Arm) w Helsinkach; Opisarnia zostaje na swoim serwerze bez zmian.
- Skutki: błąd agenta nie dotyka produkcji Opisarni.
- Kto: właściciel

## 2026-11-16: Chmura zamiast PC (D13)
- Kontekst: brak miejsca, hałas, przeprowadzka za 2 miesiące.
- Decyzja: serwer w chmurze, Windows na godziny, Mac do Chrome i urządzeń mobilnych; PC na sprzedaż.
- Skutki: plan w `ksiega/MIGRACJA.md`.
- Kto: właściciel
