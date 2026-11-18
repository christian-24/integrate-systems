#!/bin/bash
# Instalacja kopii nocnej i kontroli zdrowia na serwerze (oraz aktualizacja zapisu kart).
# Uruchamia właściciel: sudo bash /home/panel/IntegrateSystems/uruchom/serwer/zainstaluj-kopie-i-zdrowie.sh
set -e
TU="$(cd "$(dirname "$0")" && pwd)"
[ "$(id -u)" -eq 0 ] || { echo "Uruchom przez sudo."; exit 1; }
id panel >/dev/null 2>&1 || { echo "Brak użytkownika panel."; exit 1; }

install -m 755 "$TU/kopia.sh" /usr/local/bin/kopia
install -m 755 "$TU/zdrowie.sh" /usr/local/bin/zdrowie
install -m 755 "$TU/zapis-kart.sh" /usr/local/bin/zapis-kart
for u in kopia.service kopia.timer zdrowie.service zdrowie.timer; do
  install -m 644 "$TU/$u" "/etc/systemd/system/$u"
done
install -d -m 700 -o panel -g panel /home/panel/kopie
install -d -m 755 /etc/integrate
if [ ! -f /etc/integrate/serwer.env ]; then
  install -m 600 "$TU/serwer.env.przyklad" /etc/integrate/serwer.env
  echo "Utworzono /etc/integrate/serwer.env (KOPIA_CEL pusty: kopia tylko na serwerze)."
fi
grep -q '^PANEL_NTFY_URL=.' /etc/integrate/panel.env 2>/dev/null \
  || echo "UWAGA: brak PANEL_NTFY_URL w /etc/integrate/panel.env, alarmy nie będą wysyłane."

systemctl daemon-reload
systemctl enable --now kopia.timer zdrowie.timer
echo "Pierwsza kopia (może potrwać kilka minut)..."
systemctl start kopia.service || true
journalctl -u kopia --no-pager -n 4 -o cat
systemctl start zdrowie.service || true
journalctl -u zdrowie --no-pager -n 7 -o cat
systemctl list-timers kopia.timer zdrowie.timer zapis-kart.timer --no-pager
