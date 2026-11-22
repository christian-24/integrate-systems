#!/bin/bash
# Kopia serwera na Macu: pobiera nocne archiwa (kopia.sh, /home/panel/kopie/RRRR-MM-DD.tar.gz) do ~/Kopie-serwera.
# Druga kopia poza serwerem: gdy serwer przepadnie, projekty (commity jako git bundle), zmiany, media i dane są tutaj.
# Uruchamia launchd (pl.integrate.kopia-z-serwera) codziennie o 9:00 i przy wybudzeniu, jeśli pominięto.
# Instalacja: bash uruchom/mac-kopia-z-serwera.sh --zainstaluj   Ręcznie: bash uruchom/mac-kopia-z-serwera.sh
set -u
SERWER="${KOPIA_SERWER:-panel@2.29.181.133}"
CEL="${KOPIA_CEL_MAC:-$HOME/Kopie-serwera}"
ZOSTAW=7
ETYKIETA=pl.integrate.kopia-z-serwera

if [ "${1:-}" = "--zainstaluj" ]; then
  SKRYPT="$HOME/Library/Application Support/IntegrateSystems/kopia-z-serwera.sh"
  mkdir -p "$(dirname "$SKRYPT")" "$HOME/Library/Logs"
  install -m 755 "$0" "$SKRYPT"
  PLIST="$HOME/Library/LaunchAgents/$ETYKIETA.plist"
  cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$ETYKIETA</string>
  <key>ProgramArguments</key><array><string>/bin/bash</string><string>$SKRYPT</string></array>
  <key>StartCalendarInterval</key><dict><key>Hour</key><integer>9</integer><key>Minute</key><integer>0</integer></dict>
  <key>StandardOutPath</key><string>$HOME/Library/Logs/kopia-z-serwera.log</string>
  <key>StandardErrorPath</key><string>$HOME/Library/Logs/kopia-z-serwera.log</string>
</dict></plist>
PL
  launchctl bootout "gui/$(id -u)/$ETYKIETA" 2>/dev/null
  launchctl bootstrap "gui/$(id -u)" "$PLIST" && echo "Zainstalowano: codziennie 9:00, folder $CEL"
  exit $?
fi

mkdir -p "$CEL" && chmod 700 "$CEL"
echo "$(date '+%F %T') start"
# tylko archiwa RRRR-MM-DD.tar.gz; częściowe pliki nie zastępują pełnych (rsync --partial-dir)
if ! rsync -t --partial-dir=.czesciowe -e "ssh -o BatchMode=yes -o ConnectTimeout=20" \
     "$SERWER:kopie/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].tar.gz" "$CEL/"; then
  echo "$(date '+%F %T') BŁĄD pobierania"
  osascript -e 'display notification "Nie pobrano kopii z serwera. Log: ~/Library/Logs/kopia-z-serwera.log" with title "Kopia serwera"' 2>/dev/null
  exit 1
fi
chmod 600 "$CEL"/*.tar.gz 2>/dev/null
# sprawdzenie najnowszego archiwum (czy da się rozpakować spis)
NOWE=$(ls "$CEL"/*.tar.gz 2>/dev/null | sort | tail -1)
if [ -z "$NOWE" ] || ! tar -tzf "$NOWE" >/dev/null 2>&1; then
  echo "$(date '+%F %T') BŁĄD: brak albo uszkodzone archiwum ${NOWE:-}"
  osascript -e 'display notification "Brak kopii z serwera albo jest uszkodzona." with title "Kopia serwera"' 2>/dev/null
  exit 1
fi
# zostaje ZOSTAW najnowszych
NADMIAR=$(( $(ls "$CEL"/*.tar.gz 2>/dev/null | wc -l) - ZOSTAW ))
[ "$NADMIAR" -gt 0 ] && ls "$CEL"/*.tar.gz | sort | head -n "$NADMIAR" | while read -r f; do rm -f "$f"; done
ILE=$(ls "$CEL"/*.tar.gz 2>/dev/null | wc -l | tr -d ' ')
# znacznik na serwerze: panel może pokazać, kiedy kopia ostatnio trafiła na Maca
ssh -o BatchMode=yes -o ConnectTimeout=20 "$SERWER" "date -Iseconds > kopie/.na-macu" 2>/dev/null
echo "$(date '+%F %T') ok: $ILE archiwów, najnowsze $(basename "$NOWE")"
