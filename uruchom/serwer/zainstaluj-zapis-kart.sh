#!/bin/bash
# Instalacja zapisu kart na serwerze. Uruchamia właściciel (jako ops):
#   sudo bash /home/panel/IntegrateSystems/uruchom/serwer/zainstaluj-zapis-kart.sh
# Przerywa, gdy uruchom/serwer różni się od origin/main. Instaluje z /usr/local/lib/integrate.
set -e
TU="$(cd "$(dirname "$0")" && pwd)"
source "$TU/instalacja-wspolne.sh"

install -m 755 "$LIB/zapis-kart.sh" /usr/local/bin/zapis-kart
install -m 644 "$LIB/zapis-kart.service" /etc/systemd/system/zapis-kart.service
install -m 644 "$LIB/zapis-kart.timer" /etc/systemd/system/zapis-kart.timer
systemctl daemon-reload
systemctl enable --now zapis-kart.timer
systemctl start zapis-kart.service || true
journalctl -u zapis-kart --no-pager -n 3 -o cat
systemctl list-timers zapis-kart.timer --no-pager | sed -n 2p
