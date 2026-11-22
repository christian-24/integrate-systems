#!/bin/bash
# Google Drive projektów tylko do odczytu: przycisk „Połącz Google Drive” w panelu (dashboard/drive.py).
# Uruchom raz jako root z repozytorium produkcji: sudo bash uruchom/serwer/zainstaluj-drive.sh
# Instaluje rclone i FUSE, usługę drive@.service, pomocnika /usr/local/bin/drive-wlacz z prawem sudo dla panelu
# i kopię nocną bez plików z Drive. Logowanie do Google robi właściciel w panelu; token zostaje w
# /home/panel/.config/rclone/rclone.conf (0600, panel). Powtórne uruchomienie jest bezpieczne.
set -eu
SRC=$(cd "$(dirname "$0")" && pwd)
[ "$(id -u)" = 0 ] || { echo "uruchom jako root (sudo)"; exit 1; }

echo "1. rclone i FUSE"
command -v rclone >/dev/null || DEBIAN_FRONTEND=noninteractive apt-get install -y -q rclone >/dev/null
command -v fusermount3 >/dev/null || DEBIAN_FRONTEND=noninteractive apt-get install -y -q fuse3 >/dev/null
grep -qx 'user_allow_other' /etc/fuse.conf || echo 'user_allow_other' >> /etc/fuse.conf
install -d -m 700 -o panel -g panel /home/panel/.config /home/panel/.config/rclone
install -d -m 700 -o panel -g panel /home/panel/.cache /home/panel/.cache/rclone

echo "2. Usługa drive@.service i pomocnik drive-wlacz"
sed -e "s|@UID@|$(id -u panel)|" -e "s|@GID@|$(getent group projekty | cut -d: -f3)|" \
  "$SRC/drive@.service" > /etc/systemd/system/drive@.service
install -m 755 "$SRC/drive-wlacz.sh" /usr/local/bin/drive-wlacz
install -d -m 750 /etc/integrate/drive
cat > /tmp/90-drive <<'S'
# Google Drive projektów (zainstaluj-drive.sh). Pomocnik sprawdza projekt, folder karty i połączenie.
panel ALL=(root) NOPASSWD: /usr/local/bin/drive-wlacz
S
visudo -cf /tmp/90-drive >/dev/null && install -m 440 /tmp/90-drive /etc/sudoers.d/90-drive && rm -f /tmp/90-drive
systemctl daemon-reload

echo "3. Kopia nocna bez plików z Drive (find -xdev)"
install -m 755 "$SRC/kopia.sh" /usr/local/bin/kopia
echo "Gotowe. W panelu: projekt → Plan → Google Drive → Połącz."
