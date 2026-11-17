#!/bin/bash
# Instalacja zapisu kart na serwerze. Uruchamia właściciel: sudo bash zainstaluj-zapis-kart.sh
set -e
TU="$(cd "$(dirname "$0")" && pwd)"
install -m 755 "$TU/zapis-kart.sh" /usr/local/bin/zapis-kart
install -m 644 "$TU/zapis-kart.service" /etc/systemd/system/zapis-kart.service
install -m 644 "$TU/zapis-kart.timer" /etc/systemd/system/zapis-kart.timer
systemctl daemon-reload
systemctl enable --now zapis-kart.timer
systemctl start zapis-kart.service
journalctl -u zapis-kart --no-pager -n 3 -o cat
systemctl list-timers zapis-kart.timer --no-pager | sed -n 2p
