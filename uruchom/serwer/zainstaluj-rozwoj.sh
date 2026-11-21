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

echo "1. Logowanie SSH jako agent: tylko klucz właściciela z pliku roota /etc/ssh/klucze-agenta"
# Zamiast DenyUsers agent (zainstaluj-uzytkownika-agenta.sh): klucze w pliku roota, ~/.ssh agenta nie działa,
# więc agent nie dopisze sobie klucza. Klucz właściciela: z konta panel.
CONF=/etc/ssh/sshd_config.d/90-zabezpieczenia.conf
if ! grep -qE '^AllowUsers .*\bagent\b' "$CONF"; then
  sed -i -E 's/^(AllowUsers .*)$/\1 agent/' "$CONF"
fi
install -m 644 -o root -g root /home/panel/.ssh/authorized_keys /etc/ssh/klucze-agenta
cp -p /etc/ssh/sshd_config.d/90-agent.conf /etc/ssh/90-agent.conf.przed-rozwojem 2>/dev/null || true
printf '%s\n' '# Rozwój panelu (zainstaluj-rozwoj.sh): agent loguje się tylko kluczem z pliku roota.' \
  'Match User agent' '    AuthorizedKeysFile /etc/ssh/klucze-agenta' '    PasswordAuthentication no' \
  '    KbdInteractiveAuthentication no' > /etc/ssh/sshd_config.d/90-agent.conf
rm -rf /home/agent/.ssh
if sshd -t; then systemctl reload ssh; else
  cp -p /etc/ssh/90-agent.conf.przed-rozwojem /etc/ssh/sshd_config.d/90-agent.conf; echo "sshd -t nieudane, wycofano"; exit 1
fi

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

echo "4. Wdrożenie: /usr/local/bin/wdroz-panel, automat po commicie na rozwoj, przycisk w panelu, uprawnienia sudo"
install -m 755 "$SRC/wdroz-panel.sh" /usr/local/bin/wdroz-panel
install -m 644 "$SRC/wdroz-panel.service" /etc/systemd/system/wdroz-panel.service
for u in wdroz-panel-auto.service wdroz-panel-auto.path wdroz-panel-auto.timer; do
  install -m 644 "$SRC/$u" "/etc/systemd/system/$u"
done
cat > /tmp/90-rozwoj <<'EOF'
# Rozwój panelu (ROZWOJ.md). Plik instaluje uruchom/serwer/zainstaluj-rozwoj.sh; zmiany tylko tam.
panel ALL=(root) NOPASSWD: /usr/bin/systemctl start --no-block wdroz-panel.service
EOF
visudo -cf /tmp/90-rozwoj >/dev/null && install -m 440 /tmp/90-rozwoj /etc/sudoers.d/90-rozwoj && rm -f /tmp/90-rozwoj
install -d -m 750 -o panel -g panel /home/panel/dane/wdrozenie

systemctl daemon-reload
systemctl enable --now panel-testowy.service >/dev/null
systemctl enable --now wdroz-panel-auto.path wdroz-panel-auto.timer >/dev/null   # automat: commit na rozwoj = wdrożenie

echo "5. Stała sesja Claude (Remote Control) w kopii roboczej: aplikacja Claude → Code → „Rozwój panelu”"
install -m 644 "$SRC/claude-zdalnie.service" /etc/systemd/system/claude-zdalnie.service
# zaufanie folderu dla Claude agenta (bez terminala nikt by o nie nie zapytał)
runuser -u agent -- python3 - "$DEV" <<'PY'
import json, os, sys
p = os.path.expanduser("~/.claude.json")
try:
    d = json.load(open(p))
except (OSError, ValueError):
    d = {}
d.setdefault("projects", {}).setdefault(sys.argv[1], {})["hasTrustDialogAccepted"] = True
tmp = p + ".tmp"
with open(tmp, "w") as f:
    json.dump(d, f, indent=2)
os.chmod(tmp, 0o600)
os.replace(tmp, p)
PY
systemctl daemon-reload
systemctl enable --now claude-zdalnie.service >/dev/null
echo "   Jeśli „Rozwój panelu” nie pojawia się w aplikacji: journalctl -u claude-zdalnie. Pierwsza zgoda na Remote"
echo "   Control wymaga jednorazowej odpowiedzi „y”: sudo -u agent -H script -qc '/home/agent/.local/bin/claude remote-control --spawn=same-dir' /dev/null"
systemctl restart panel-testowy.service
echo "Gotowe. Panel testowy: https://$HOST_TEST (hasło w panelu: Serwer → Rozwój panelu)."
