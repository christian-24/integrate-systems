#!/bin/sh
# Wyłącza uruchamianie panelu przy logowaniu. Plików projektów, rekordów i logu nie usuwa.
set -eu
. "$(dirname "$0")/wspolne.sh"

DOMENA="gui/$(id -u)"
if launchctl print "$DOMENA/$LABEL" >/dev/null 2>&1; then
  launchctl bootout "$DOMENA/$LABEL" >/dev/null 2>&1 || true
  echo "Zatrzymano panel."
else
  echo "Panel nie był uruchomiony przez LaunchAgent."
fi
if [ -f "$PLIST" ]; then
  rm "$PLIST"
  echo "Usunięto: $PLIST"
fi
echo "Ręczne uruchomienie: ./start.sh"
