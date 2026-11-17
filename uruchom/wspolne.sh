# Wspólne ustawienia skryptów w tym folderze. Wczytywane przez: . "$(dirname "$0")/wspolne.sh"
URUCHOM="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$URUCHOM")"
DASH="$ROOT/dashboard"
ENV_FILE="$DASH/panel.env"
LABEL="pl.integratesystems.panel"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG="$HOME/Library/Logs/panel-projektow.log"

# ustawienie NAZWA DOMYSLNA: zmienna środowiska wygrywa z plikiem panel.env
ustawienie() {
  eval "wartosc=\${$1-}"
  if [ -z "$wartosc" ] && [ -f "$ENV_FILE" ]; then
    wartosc="$(sed -n "s/^[[:space:]]*$1[[:space:]]*=[[:space:]]*//p" "$ENV_FILE" | tail -n 1 | sed 's/[[:space:]]*$//')"
  fi
  printf '%s' "${wartosc:-$2}"
}

adres_panelu() {
  host="$(ustawienie PANEL_HOST 127.0.0.1)"
  port="$(ustawienie PANEL_PORT 4801)"
  case "$host" in 127.0.0.1|localhost|0.0.0.0|::|::1) host="localhost" ;; esac
  printf 'http://%s:%s/' "$host" "$port"
}
