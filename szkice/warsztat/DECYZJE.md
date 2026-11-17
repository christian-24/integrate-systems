# Decyzje: Warsztat (silnik i język WDL)

Każda decyzja to osobny wpis, najnowsze na górze. Nagłówek wpisu: `## RRRR-MM-DD: krótki tytuł`.
Pełny rejestr decyzji (D01–D35) jest w repozytorium w `docs/decisions/`; tu tylko najważniejsze.

## 2026-11-14: Projekt wstrzymany na bramce K15
- Kontekst: bramka K15 otwarta od 06.11.
- Decyzja: projekt czeka, niepilny; test piły właściciel zrobi później. Cel: projekt własny, przy dobrym wyniku produkt dla klientów.
- Skutki: K16 nie startuje.
- Kto: właściciel

## 2026-11-06: D34 uchwyty 3D zapisywane do WDL zatwierdzone, K15 rozpoczęty
- Kontekst: bramka K14.
- Decyzja: właściciel zatwierdził K14 (D34); start K15 (D35 rekomendowana).
- Skutki: K16 czeka na bramkę K15.
- Kto: właściciel

## 2026-10-27: Zespół agentów i bramka człowieka
- Kontekst: start projektu (T0).
- Decyzja: praca w sesjach zespołu agentów Claude Code (D19), każdy kamień zatwierdza właściciel (D20); jednostki wewnętrzne mm, g, V, A, W (D2); zero płatnych zależności.
- Skutki: kamienie T0, K0… są sekwencyjne.
- Kto: właściciel
