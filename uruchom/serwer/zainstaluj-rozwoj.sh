#!/bin/bash
# Rozwój panelu na serwerze (ROZWOJ.md): kopia robocza agenta, panel testowy, wdrożenie przyciskiem „Wdróż”.
# Uruchom jako root z katalogu repozytorium produkcji: sudo bash uruchom/serwer/zainstaluj-rozwoj.sh
# Powtórne uruchomienie jest bezpieczne: istniejąca kopia robocza i hasło panelu testowego zostają.
set -eu
PROD=/home/panel/IntegrateSystems
ROZ=/home/agent/rozwoj
DEV=$ROZ/IntegrateSystems
HOST_TEST=${HOST_TEST:-test.2-29-181-133.sslip.io}
SRC=$(cd "$(dirname "$0")" && pwd)
[ "$(id -u)" = 0 ] || { echo "uruchom jako root (sudo)"; exit 1; }

echo "1. Logowanie SSH jako agent (klucz właściciela z konta panel, bez hasła)"
CONF=/etc/ssh/sshd_config.d/90-zabezpieczenia.conf
if ! grep -qE '^AllowUsers .*\bagent\b' "$CONF"; then
  sed -i -E 's/^(AllowUsers .*)$/\1 agent/' "$CONF"
fi
install -d -m 700 -o agent -g agent /home/agent/.ssh
install -m 600 -o agent -g agent /home/panel/.ssh/authorized_keys /home/agent/.ssh/authorized_keys
sshd -t && systemctl reload ssh

echo "2. Kopia robocza $DEV (gałąź rozwoj)"
install -d -m 2750 -o agent -g projekty "$ROZ"
if [ ! -d "$DEV/.git" ]; then
  runuser -u agent -- git clone -q "$PROD" "$DEV"
  runuser -u agent -- git -C "$DEV" checkout -q -b rozwoj
fi
runuser -u agent -- git -C "$DEV" config user.name "Agent (rozwój panelu)"
runuser -u agent -- git -C "$DEV" config user.email "agent@localhost"
chgrp -R projekty "$ROZ" && chmod -R g+rX "$ROZ"
runuser -u panel -- git config --global --get-all safe.directory | grep -qx "$DEV" ||
  runuser -u panel -- git config --global --add safe.directory "$DEV"

echo "3. Panel testowy: 127.0.0.1:4802, dane przykładowe, bez agentów, https://$HOST_TEST"
if [ ! -f /etc/integrate/panel-testowy.env ]; then
  umask 027
  printf 'PANEL_TOKEN=%s\n' "$(openssl rand -hex 12)" > /etc/integrate/panel-testowy.env
  umask 022
fi
chown root:panel /etc/integrate/panel-testowy.env && chmod 640 /etc/integrate/panel-testowy.env
install -d -m 750 -o agent -g agent "$ROZ/dane-testowe"
sed "s|@HOST_TEST@|$HOST_TEST|g" "$SRC/panel-testowy.service" > /etc/systemd/system/panel-testowy.service
printf '%s {\n\tencode gzip\n\treverse_proxy 127.0.0.1:4802\n}\n' "$HOST_TEST" > /etc/caddy/panel-testowy.caddy
grep -q 'panel-testowy.caddy' /etc/caddy/Caddyfile || echo 'import /etc/caddy/panel-testowy.caddy' >> /etc/caddy/Caddyfile
caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile >/dev/null && systemctl reload caddy

echo "4. Wdrożenie: /usr/local/bin/wdroz-panel, wdroz-panel.service, uprawnienia sudo"
install -m 755 "$SRC/wdroz-panel.sh" /usr/local/bin/wdroz-panel
install -m 644 "$SRC/wdroz-panel.service" /etc/systemd/system/wdroz-panel.service
cat > /tmp/90-rozwoj <<'EOF'
# Rozwój panelu (ROZWOJ.md). Plik instaluje uruchom/serwer/zainstaluj-rozwoj.sh; zmiany tylko tam.
panel ALL=(root) NOPASSWD: /usr/bin/systemctl start --no-block wdroz-panel.service
agent ALL=(root) NOPASSWD: /usr/bin/systemctl restart panel-testowy.service
EOF
visudo -cf /tmp/90-rozwoj >/dev/null && install -m 440 /tmp/90-rozwoj /etc/sudoers.d/90-rozwoj && rm -f /tmp/90-rozwoj
install -d -m 750 -o panel -g panel /home/panel/dane/wdrozenie

systemctl daemon-reload
systemctl enable --now panel-testowy.service >/dev/null
systemctl restart panel-testowy.service
echo "Gotowe. Panel testowy: https://$HOST_TEST (hasło w panelu: Serwer → Rozwój panelu)."
