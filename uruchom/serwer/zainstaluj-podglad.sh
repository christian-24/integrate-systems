#!/bin/bash
# Podgląd stron WWW projektów w panelu (zakładka „Strona”, dashboard/strona.py, dashboard/AGENCI.md „Podgląd strony”).
# Uruchamia właściciel (jako ops), po instalacji użytkownika agenta (zainstaluj-uzytkownika-agenta.sh):
#   sudo bash /home/panel/IntegrateSystems/uruchom/serwer/zainstaluj-podglad.sh             instalacja i próba
#   sudo bash /home/panel/IntegrateSystems/uruchom/serwer/zainstaluj-podglad.sh --sprawdz   sama próba, bez zmian
# 1. Node.js (wersja 20 lub nowsza) z npm: pakiet Ubuntu, gdy ma wersję ≥ 20; inaczej repozytorium NodeSource node_22.x
#    (podpisane, aktualizacje przez apt jak reszta systemu). Bez skryptów curl | bash.
# 2. /usr/local/lib/integrate/podglad-buduj.sh (root, 755): budowanie podglądu jako agent, tylko w /home/panel/projekty
# 3. /usr/local/lib/integrate/zrzut-strony.py (root, 644): zrzuty ekranu dla agenta (Python z Playwright agenta)
# 4. /etc/sudoers.d/91-panel-podglad: panel uruchamia jako agent tylko podglad-buduj.sh (visudo -c)
# 5. próba: node i npm jako agent przez sudo panelu, mała strona zbudowana atrapą, zrzut 390 px
# Panel nie wymaga restartu (czyta pliki przy budowaniu). Powtórne uruchomienie jest bezpieczne.
set -u
TU="$(cd "$(dirname "$0")" && pwd)"
SPRAWDZ=0
case "${1:-}" in
  "") ;;
  --sprawdz) SPRAWDZ=1 ;;
  -h|--help) sed -n '3,5p' "$0" | sed 's/^# *//'; exit 0 ;;
  *) echo "Nieznana opcja: $1 (dozwolona: --sprawdz)" >&2; exit 2 ;;
esac
PANEL=panel
AGENT=agent
LIB=/usr/local/lib/integrate
BUDUJ=$LIB/podglad-buduj.sh
ZRZUT=$LIB/zrzut-strony.py
SUDOERS=/etc/sudoers.d/91-panel-podglad
PW_PY=/home/$AGENT/narzedzia/pw/bin/python
NODE_MIN=20
NODESOURCE=node_22.x
BRAK=0

przerwij() { echo "Przerwano: $*" >&2; exit 1; }
log() { echo "$*"; }
brak() { echo "BRAK: $*"; BRAK=1; }

[ "$(id -u)" -eq 0 ] || przerwij "uruchom przez sudo."
id "$PANEL" >/dev/null 2>&1 || przerwij "brak użytkownika $PANEL."
id "$AGENT" >/dev/null 2>&1 || przerwij "brak użytkownika $AGENT (najpierw zainstaluj-uzytkownika-agenta.sh)."
cd / || exit 1

node_major() { node -v 2>/dev/null | sed -n 's/^v\([0-9]*\).*/\1/p'; }

instaluj_node() {
  local m cand
  m="$(node_major)"
  if [ -n "$m" ] && [ "$m" -ge "$NODE_MIN" ] && command -v npm >/dev/null; then
    log "1. Node.js $(node -v) i npm $(npm -v) już są."
    return 0
  fi
  apt-get update -q >/dev/null || przerwij "apt-get update nieudane."
  cand="$(apt-cache policy nodejs 2>/dev/null | sed -n 's/^ *Kandydujący: *\(.*\)$/\1/p;s/^ *Candidate: *\(.*\)$/\1/p' | head -1)"
  cand="${cand#*:}"
  if [ -n "$cand" ] && [ "$cand" != "(none)" ] && [ "$(echo "$cand" | sed 's/\..*//')" -ge "$NODE_MIN" ] 2>/dev/null; then
    log "1. Node.js z Ubuntu ($cand)..."
    DEBIAN_FRONTEND=noninteractive apt-get install -y -q nodejs npm >/dev/null || przerwij "apt nodejs npm nieudane."
  else
    log "1. Ubuntu ma Node.js ${cand:-brak} (< $NODE_MIN): repozytorium NodeSource $NODESOURCE..."
    command -v curl >/dev/null || DEBIAN_FRONTEND=noninteractive apt-get install -y -q curl >/dev/null
    command -v gpg >/dev/null || DEBIAN_FRONTEND=noninteractive apt-get install -y -q gnupg >/dev/null
    install -d -m 755 /etc/apt/keyrings
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor --yes -o /etc/apt/keyrings/nodesource.gpg \
      || przerwij "nie pobrano klucza NodeSource."
    chmod 644 /etc/apt/keyrings/nodesource.gpg
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/$NODESOURCE nodistro main" \
      > /etc/apt/sources.list.d/nodesource.list
    apt-get update -q >/dev/null || przerwij "apt-get update z NodeSource nieudane."
    DEBIAN_FRONTEND=noninteractive apt-get install -y -q nodejs >/dev/null || przerwij "apt nodejs (NodeSource) nieudane."
  fi
  m="$(node_major)"
  [ -n "$m" ] && [ "$m" -ge "$NODE_MIN" ] || przerwij "po instalacji node -v: $(node -v 2>&1)."
  command -v npm >/dev/null || przerwij "po instalacji brak npm."
  log "   Node.js $(node -v), npm $(npm -v)."
}

instaluj_pliki() {
  install -d -o root -g root -m 755 "$LIB"
  local tmp
  tmp="$(mktemp)"
  cat > "$tmp" <<'EOF'
#!/bin/bash
# Budowanie podglądu strony jako agent: panel uruchamia `sudo -n -u agent -- podglad-buduj.sh <folder strony> <polecenie>`
# (dashboard/strona.py). Plik instaluje uruchom/serwer/zainstaluj-podglad.sh; zmiany tylko tam.
set -u
[ $# -eq 2 ] || { echo "Użycie: $0 <folder strony> <polecenie>" >&2; exit 2; }
DIR="$(realpath -e -- "$1" 2>/dev/null)" || { echo "Nie ma folderu: $1" >&2; exit 2; }
case "$DIR" in /home/panel/projekty/*) ;; *) echo "Folder poza /home/panel/projekty: $DIR" >&2; exit 2 ;; esac
cd "$DIR" || exit 2
export HOME=/home/agent PATH=/usr/local/bin:/usr/bin:/bin CI=1 npm_config_update_notifier=false \
  npm_config_fund=false npm_config_audit=false npm_config_cache=/home/agent/.npm
umask 002
exec /bin/bash -c "$2"
EOF
  install -o root -g root -m 755 "$tmp" "$BUDUJ"
  rm -f "$tmp"
  install -o root -g root -m 644 "$TU/zrzut-strony.py" "$ZRZUT"
  install -d -o "$AGENT" -g "$AGENT" -m 700 "/home/$AGENT/.npm"
  log "2-3. $BUDUJ i $ZRZUT zainstalowane."

  tmp="$(mktemp)"
  cat > "$tmp" <<EOF
# Panel (użytkownik $PANEL) buduje podgląd strony projektu jako $AGENT, tylko tym jednym skryptem, bez hasła.
# Plik instaluje uruchom/serwer/zainstaluj-podglad.sh; zmiany tylko tam.
$PANEL ALL=($AGENT) NOPASSWD: $BUDUJ
EOF
  chmod 440 "$tmp"
  if visudo -c -q -f "$tmp" >/dev/null; then
    cmp -s "$tmp" "$SUDOERS" || { install -o root -g root -m 440 "$tmp" "$SUDOERS" && log "4. Zapisano $SUDOERS."; }
  else
    rm -f "$tmp"; przerwij "reguła sudoers nie przeszła visudo -c; nic nie zapisano."
  fi
  rm -f "$tmp"
  visudo -c -q >/dev/null || { rm -f "$SUDOERS"; przerwij "visudo -c nieudane; $SUDOERS usunięty."; }
}

proba() {
  local m d out
  m="$(node_major)"
  if [ -n "$m" ] && [ "$m" -ge "$NODE_MIN" ]; then log "OK: node $(node -v), npm $(npm -v 2>/dev/null)"; else brak "Node.js ≥ $NODE_MIN"; fi
  [ -x "$BUDUJ" ] && log "OK: $BUDUJ" || brak "$BUDUJ"
  [ -f "$ZRZUT" ] && log "OK: $ZRZUT" || brak "$ZRZUT"
  [ -f "$SUDOERS" ] && log "OK: $SUDOERS" || brak "$SUDOERS"
  # Budowanie atrapą w folderze projektów (wrapper przyjmuje tylko /home/panel/projekty/*).
  d="/home/panel/projekty/.proba-podgladu"
  rm -rf "$d"
  install -d -o "$PANEL" -g "$PANEL" -m 2775 "$d"
  setfacl -m "u:$AGENT:rwx" "$d" 2>/dev/null || chmod 777 "$d"
  printf '<!doctype html><title>Próba</title><h1>Próba podglądu</h1>\n' > "$d/index.html"
  chown "$PANEL:$PANEL" "$d/index.html"; chmod 644 "$d/index.html"
  out="$(runuser -u "$PANEL" -- sudo -n -u "$AGENT" -- "$BUDUJ" "$d" 'node -v && npm -v && mkdir -p dist && cp index.html dist/' 2>&1)"
  if [ -f "$d/dist/index.html" ]; then log "OK: budowanie jako $AGENT ($(echo "$out" | tr '\n' ' '))"; else brak "budowanie jako $AGENT: $out"; fi
  if [ -x "$PW_PY" ]; then
    out="$(runuser -u "$AGENT" -- "$PW_PY" "$ZRZUT" "$d/dist" 390 "/tmp/proba-podgladu-$$.png" 2>&1)"
    if [ -s "/tmp/proba-podgladu-$$.png" ]; then log "OK: zrzut 390 px jako $AGENT"; else brak "zrzut jako $AGENT: $out"; fi
    rm -f "/tmp/proba-podgladu-$$.png"
  else
    brak "$PW_PY (Python agenta z Playwright; zrzuty stron)"
  fi
  rm -rf "$d"
}

if [ "$SPRAWDZ" -eq 0 ]; then
  instaluj_node
  instaluj_pliki
fi
echo "Próba:"
proba
[ "$BRAK" -eq 0 ] && echo "Podgląd stron gotowy." || { echo "Są braki (BRAK wyżej)."; exit 1; }
