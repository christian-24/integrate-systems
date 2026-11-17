#!/bin/sh
# Instaluje zbieracz jako zadanie launchd (co godzinę i przy logowaniu).
# Użycie: sh system/uruchom/mac-zainstaluj.sh
# Opcjonalnie: PYTHON=/ścieżka/python3 LOKALNE_DIR=/ścieżka sh mac-zainstaluj.sh
set -eu

SYSTEM="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${PYTHON:-$(command -v python3 || true)}"
LOKALNE="${LOKALNE_DIR:-$HOME/.integrate-lokalne}"
SZABLON="$SYSTEM/uruchom/pl.integrate.zbieracz.plist"
CEL="$HOME/Library/LaunchAgents/pl.integrate.zbieracz.plist"

if [ -z "$PYTHON" ]; then
	echo "Nie znaleziono python3. Podaj: PYTHON=/ścieżka/python3 sh $0" >&2
	exit 1
fi
if [ ! -d "${STAN_DIR:-$HOME/stan-systemu}/.git" ]; then
	echo "Uwaga: brak repozytorium stanu. Najpierw: $PYTHON $SYSTEM/zbieracz.py init <adres-repo>" >&2
fi

zamien() { printf '%s' "$1" | sed -e 's/[|&\\]/\\&/g'; }

mkdir -p "$LOKALNE" "$HOME/Library/LaunchAgents"
sed -e "s|__PYTHON__|$(zamien "$PYTHON")|g" \
	-e "s|__SYSTEM__|$(zamien "$SYSTEM")|g" \
	-e "s|__LOKALNE__|$(zamien "$LOKALNE")|g" \
	"$SZABLON" > "$CEL"
plutil -lint "$CEL" >/dev/null

launchctl unload "$CEL" 2>/dev/null || true
launchctl load "$CEL"
echo "Zainstalowano: $CEL"
echo "Dziennik: $LOKALNE/zbieracz.log"
PRAWDZIWY="$("$PYTHON" -c 'import os, sys; print(os.path.realpath(sys.executable))' 2>/dev/null || echo "$PYTHON")"
echo "Pełny dostęp do dysku: Ustawienia systemowe → Prywatność i ochrona → Pełny dostęp do dysku → + → Cmd+Shift+G → $PRAWDZIWY"
