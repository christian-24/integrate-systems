#!/bin/bash
# Zapisuje token API Hetzner Cloud (tylko do odczytu) dla kosztów w panelu, bez pokazywania go na ekranie.
# Jeden token na projekt Hetzner Cloud; ten sam projekt podany drugi raz zastępuje poprzedni token.
# Instalacja (ops):  sudo install -m 750 /home/panel/IntegrateSystems/uruchom/serwer/ustaw-token-hetznera.sh /usr/local/sbin/ustaw-token-hetznera
# Użycie:            sudo ustaw-token-hetznera            usunięcie: sudo ustaw-token-hetznera --usun NAZWA
set -euo pipefail
F=/etc/integrate/hetzner.tokeny
[ "$(id -u)" = 0 ] || { echo "Uruchom przez sudo."; exit 1; }
touch "$F"
if [ "${1:-}" = "--usun" ]; then
  [ -n "${2:-}" ] || { echo "Podaj nazwę projektu."; exit 1; }
  grep -v "^$2=" "$F" > "$F.tmp" || true
  install -m 640 -o root -g panel "$F.tmp" "$F"; rm -f "$F.tmp"
  echo "Usunięto token projektu $2."; exit 0
fi
echo "Token tworzysz w Hetzner Console: projekt → Security → API tokens → Generate API token, uprawnienie Read."
read -r -p "Nazwa projektu w panelu (np. agenci, opisarnia): " N
[[ "$N" =~ ^[A-Za-z0-9._-]{1,40}$ ]] || { echo "Nazwa: litery, cyfry, . _ - (do 40 znaków). Nic nie zmieniono."; exit 1; }
read -r -s -p "Token API: " T; echo
[[ "$T" =~ ^[A-Za-z0-9]{20,}$ ]] || { echo "To nie wygląda na token Hetznera. Nic nie zmieniono."; exit 1; }
KOD=$(printf 'Authorization: Bearer %s\n' "$T" | curl -sS -o /dev/null -w '%{http_code}' -H @- \
  "https://api.hetzner.cloud/v1/servers?per_page=1" || true)
[ "$KOD" = 200 ] || { echo "API Hetzner odrzuciło token (kod $KOD). Nic nie zmieniono."; exit 1; }
grep -v "^$N=" "$F" > "$F.tmp" || true
printf '%s=%s\n' "$N" "$T" >> "$F.tmp"
install -m 640 -o root -g panel "$F.tmp" "$F"; rm -f "$F.tmp"
unset T
echo "Token projektu $N zapisany. Panel odczyta koszty w ciągu minuty (menu → Koszty)."
