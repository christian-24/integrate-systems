#!/bin/bash
# Zbiera bieżącą konfigurację serwera bez sekretów, do porównania z wzorami w uruchom/serwer/konfiguracja/.
#   sudo bash zbierz-konfiguracje.sh [KATALOG]      (domyślnie /root/konfiguracja-RRRR-MM-DD)
# Zbiera: /etc/caddy/Caddyfile, jednostki systemd panel, useme, caddy (systemctl cat) oraz /etc/integrate/*.env.
# W plikach .env zostają nazwy zmiennych; wartości są jawne tylko dla nazw z listy JAWNE, reszta to <ukryte>.
# W Caddyfile hasze haseł ($2a$..., $2b$...) są zastąpione <ukryte>. Przejrzyj wynik przed skopiowaniem do repozytorium.
set -u
umask 077
[ "$(id -u)" -eq 0 ] || { echo "Uruchom przez sudo."; exit 1; }
CEL="${1:-/root/konfiguracja-$(date +%F)}"
mkdir -p "$CEL" || exit 1
JAWNE=" PANEL_HOST PANEL_PORT PANEL_MACHINE PANEL_CLAUDE PANEL_CODEX PANEL_AGENTS_MAX PANEL_AGENT_TIMEOUT PANEL_PM_HOUR \
PANEL_GIT_PULL PANEL_AGENT_MODEL PANEL_PM_MODEL PANEL_ZDROWIE_STAN PANEL_KOPIA_STAN USEME_URL ZDROWIE_PROG_DYSKU \
KOPIA_HASLO_PLIK KOPIA_AGE_ODBIORCY KOPIA_CEL_DNI "

if [ -f /etc/caddy/Caddyfile ]; then
  sed -E 's/\$2[aby]\$[^[:space:]]+/<ukryte>/g' /etc/caddy/Caddyfile > "$CEL/Caddyfile"
fi
for u in panel useme caddy; do
  systemctl cat "$u.service" > "$CEL/$u.service" 2>/dev/null || rm -f "$CEL/$u.service"
done
for e in /etc/integrate/*.env; do
  [ -f "$e" ] || continue
  while IFS= read -r w || [ -n "$w" ]; do
    case "$w" in
      ''|'#'*) echo "$w" ;;
      *=*)
        n="${w%%=*}"; n="${n// /}"; v="${w#*=}"
        if [ -z "$v" ] || [[ "$JAWNE" == *" $n "* ]]; then echo "$n=$v"; else echo "$n=<ukryte>"; fi ;;
      *) echo "<ukryte>" ;;
    esac
  done < "$e" > "$CEL/${e##*/}.przyklad"
done
ls -l "$CEL"
echo "Porównaj: diff -r $CEL /home/panel/IntegrateSystems/uruchom/serwer/konfiguracja"
