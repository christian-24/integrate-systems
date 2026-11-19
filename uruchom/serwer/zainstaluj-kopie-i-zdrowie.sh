#!/bin/bash
# Instalacja kopii nocnej, kontroli zdrowia, odtworzenia i aktualizacja zapisu kart na serwerze.
# Uruchamia właściciel (jako ops):
#   sudo bash /home/panel/IntegrateSystems/uruchom/serwer/zainstaluj-kopie-i-zdrowie.sh
# Przerywa, gdy uruchom/serwer różni się od origin/main. Instaluje z /usr/local/lib/integrate.
set -e
TU="$(cd "$(dirname "$0")" && pwd)"
source "$TU/instalacja-wspolne.sh"

install -m 755 "$LIB/kopia.sh" /usr/local/bin/kopia
install -m 755 "$LIB/zdrowie.sh" /usr/local/bin/zdrowie
install -m 755 "$LIB/zapis-kart.sh" /usr/local/bin/zapis-kart
install -m 755 "$LIB/odtworz.sh" /usr/local/bin/odtworz
for u in kopia.service kopia.timer zdrowie.service zdrowie.timer; do
  install -m 644 "$LIB/$u" "/etc/systemd/system/$u"
done
install -d -m 700 -o panel -g panel /home/panel/kopie
install -d -o root -g panel -m 750 /etc/integrate   # agent (PANEL_AGENT_USER) nie wchodzi do /etc/integrate
if [ ! -f /etc/integrate/serwer.env ]; then
  install -m 600 "$LIB/serwer.env.przyklad" /etc/integrate/serwer.env
  echo "Utworzono /etc/integrate/serwer.env (KOPIA_CEL pusty: kopia tylko na serwerze)."
fi
grep -q '^PANEL_NTFY_URL=.' /etc/integrate/panel.env 2>/dev/null \
  || echo "UWAGA: brak PANEL_NTFY_URL w /etc/integrate/panel.env, alarmy nie będą wysyłane."
if grep -q '^KOPIA_CEL=.' /etc/integrate/serwer.env 2>/dev/null; then
  for p in gpg rclone; do
    if ! command -v "$p" >/dev/null; then echo "UWAGA: brak $p, jeśli ustawienia kopii go wymagają (sudo apt install ${p/gpg/gnupg})."; fi
  done
else
  echo "UWAGA: KOPIA_CEL pusty: kopia tylko na serwerze (konfiguracja: ksiega/MIGRACJA.md, „Kopia poza serwerem”)."
fi

systemctl daemon-reload
systemctl enable --now kopia.timer zdrowie.timer
echo "Kopia (może potrwać kilka minut)..."
systemctl start kopia.service || true
journalctl -u kopia --no-pager -n 5 -o cat
systemctl start zdrowie.service || true
journalctl -u zdrowie --no-pager -n 8 -o cat
systemctl list-timers kopia.timer zdrowie.timer zapis-kart.timer --no-pager
