#!/bin/bash
# Google Drive Shield & Silent tylko do odczytu w panelu (widok Media) i dla agentów projektu, bez kopii na serwerze.
# Uruchom jako root z katalogu repozytorium produkcji, z identyfikatorem folderu Shield & Silent na Drive
# (część linku po /folders/):
#   sudo bash uruchom/serwer/zainstaluj-drive.sh <id-folderu>
# Logowanie Google: skrypt wypisuje tylko adres logowania (http://127.0.0.1:53682/...). Otwórz go w przeglądarce na
# Macu przez tunel SSH: ssh -L 53682:127.0.0.1:53682 <serwer>. Token zostaje w /home/panel/.config/rclone/rclone.conf
# (0600, użytkownik panel); skrypt nigdy go nie wypisuje. Powtórne uruchomienie jest bezpieczne (logowanie pomija,
# gdy zdalny „drive-shield” już jest).
set -eu
PROD=/home/panel/IntegrateSystems
MNT=$PROD/szkice/shield-silent/media/drive
CONF=/home/panel/.config/rclone/rclone.conf
SRC=$(cd "$(dirname "$0")" && pwd)
FOLDER=${1:-}
[ "$(id -u)" = 0 ] || { echo "uruchom jako root (sudo)"; exit 1; }

echo "1. rclone i FUSE"
command -v rclone >/dev/null || DEBIAN_FRONTEND=noninteractive apt-get install -y -q rclone fuse3 >/dev/null
command -v fusermount3 >/dev/null || DEBIAN_FRONTEND=noninteractive apt-get install -y -q fuse3 >/dev/null
grep -qx 'user_allow_other' /etc/fuse.conf || echo 'user_allow_other' >> /etc/fuse.conf

echo "2. Logowanie Google (zakres drive.readonly, folder $FOLDER)"
install -d -m 700 -o panel -g panel /home/panel/.config /home/panel/.config/rclone
if runuser -u panel -- rclone --config "$CONF" listremotes 2>/dev/null | grep -qx 'drive-shield:'; then
  echo "   zdalny drive-shield już jest, pomijam logowanie"
else
  [ -n "$FOLDER" ] || { echo "podaj identyfikator folderu Shield & Silent: sudo bash $0 <id-folderu>"; exit 1; }
  case "$FOLDER" in *[!A-Za-z0-9_-]*) echo "identyfikator folderu ma tylko litery, cyfry, - i _"; exit 1 ;; esac
  echo "   Na Macu: ssh -L 53682:127.0.0.1:53682 <serwer>, potem otwórz adres poniżej i zaloguj się kontem Google."
  # wyjście rclone (z tokenem po zalogowaniu) nie trafia na ekran: tylko wiersz z adresem logowania
  runuser -u panel -- rclone --config "$CONF" config create drive-shield drive scope=drive.readonly \
    root_folder_id="$FOLDER" --auth-no-open-browser 2>&1 | grep --line-buffered -o 'http://127\.0\.0\.1:53682/auth[^ ]*' || true
  runuser -u panel -- rclone --config "$CONF" listremotes | grep -qx 'drive-shield:' || { echo "logowanie nieudane"; exit 1; }
  echo "   zalogowano"
fi
chown panel:panel "$CONF" && chmod 600 "$CONF"

echo "3. Montowanie tylko do odczytu: $MNT"
install -d -m 2750 -o panel -g projekty "$MNT"
sed -e "s|@UID@|$(id -u panel)|" -e "s|@GID@|$(getent group projekty | cut -d: -f3)|" \
  "$SRC/drive-shield.service" > /etc/systemd/system/drive-shield.service
systemctl daemon-reload
systemctl enable --now drive-shield.service >/dev/null
systemctl restart drive-shield.service

echo "4. Kopia nocna bez plików z Drive (/usr/local/bin/kopia)"
install -m 755 "$SRC/kopia.sh" /usr/local/bin/kopia

echo "5. Kontrola"
sleep 3
mountpoint -q "$MNT" || { echo "BŁĄD: $MNT nie jest zamontowany; journalctl -u drive-shield"; exit 1; }
echo "   plików (do 2 poziomów): $(find "$MNT" -maxdepth 2 -type f | wc -l)"
runuser -u agent -- test -r "$MNT" && echo "   agent czyta katalog" || echo "UWAGA: agent nie czyta $MNT"
touch "$MNT/.proba" 2>/dev/null && { rm -f "$MNT/.proba"; echo "UWAGA: montowanie pozwala na zapis"; } || echo "   tylko do odczytu"
