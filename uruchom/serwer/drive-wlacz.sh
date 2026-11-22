#!/bin/bash
# Montowanie Google Drive projektu (root, przez sudo z panelu). Instaluje uruchom/serwer/zainstaluj-drive.sh.
#   drive-wlacz <projekt> <folder karty>   punkt montowania <folder karty>/media/drive, usługa drive@<projekt>
#   drive-wlacz --wylacz <projekt>         zatrzymuje i wyłącza usługę
set -eu
SZKICE=/home/panel/IntegrateSystems/szkice
CONF=/home/panel/.config/rclone/rclone.conf
ENVD=/etc/integrate/drive
[ "$(id -u)" = 0 ] || { echo "tylko root"; exit 1; }
ok_pid() { [[ "$1" =~ ^[a-z0-9][a-z0-9-]{0,63}$ ]] || { echo "zły identyfikator projektu"; exit 2; }; }

if [ "${1:-}" = "--wylacz" ]; then
  pid=${2:-}; ok_pid "$pid"
  systemctl disable --now "drive@$pid.service" >/dev/null 2>&1 || true
  rm -f "$ENVD/$pid.env"
  echo "wyłączono"; exit 0
fi

pid=${1:-}; ok_pid "$pid"
karta=$(realpath -e -- "${2:-/nie-ma}") || { echo "brak folderu karty"; exit 2; }
[[ "$karta" =~ ^$SZKICE/[A-Za-z0-9._-]+$ ]] || { echo "folder karty poza szkice/"; exit 2; }
[ -f "$karta/KARTA.md" ] || { echo "folder bez KARTA.md"; exit 2; }
runuser -u panel -- rclone --config "$CONF" listremotes | grep -qx "drive-$pid:" || { echo "brak połączenia drive-$pid"; exit 2; }
mnt="$karta/media/drive"
runuser -u panel -- mkdir -p "$mnt" "/home/panel/.cache/rclone/$pid"
chgrp projekty "$mnt" && chmod 2750 "$mnt"
install -d -m 750 "$ENVD"
printf 'MNT=%s\n' "$mnt" > "$ENVD/$pid.env"
systemctl enable "drive@$pid.service" >/dev/null 2>&1
systemctl restart "drive@$pid.service"
for _ in $(seq 1 20); do mountpoint -q "$mnt" && { echo "zamontowano"; exit 0; }; sleep 1; done
echo "montowanie nieudane (journalctl -u drive@$pid)"; exit 1
