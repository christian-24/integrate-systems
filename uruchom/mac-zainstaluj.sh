#!/bin/sh
# Uruchamia panel przy logowaniu do macOS (LaunchAgent użytkownika) i pilnuje, żeby działał.
#   ./mac-zainstaluj.sh                 instaluje i uruchamia
#   ./mac-zainstaluj.sh --podglad PLIK  tylko zapisuje plist do PLIK, niczego nie instaluje
set -eu
. "$(dirname "$0")/wspolne.sh"

PYTHON="$(command -v python3 || true)"
if [ -z "$PYTHON" ]; then
  echo "Brak polecenia python3. Zainstaluj narzędzia Xcode: xcode-select --install"
  exit 1
fi
if [ ! -f "$DASH/server.py" ]; then
  echo "Nie widzę $DASH/server.py. Uruchom skrypt z folderu uruchom/ w IntegrateSystems."
  exit 1
fi

zapisz_plist() {
  PLIST_OUT="$1" LABEL="$LABEL" PYTHON="$PYTHON" DASH="$DASH" LOG="$LOG" "$PYTHON" - <<'PY'
import os, plistlib
home = os.path.expanduser("~")
path = ":".join([home + "/.local/bin", "/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin"])
plist = {
    "Label": os.environ["LABEL"],
    "ProgramArguments": [os.environ["PYTHON"], os.path.join(os.environ["DASH"], "server.py")],
    "WorkingDirectory": os.environ["DASH"],
    "RunAtLoad": True,
    "KeepAlive": True,
    "ThrottleInterval": 30,
    "StandardOutPath": os.environ["LOG"],
    "StandardErrorPath": os.environ["LOG"],
    "EnvironmentVariables": {"PATH": path, "PYTHONUNBUFFERED": "1", "LANG": "pl_PL.UTF-8"},
}
with open(os.environ["PLIST_OUT"], "wb") as f:
    plistlib.dump(plist, f)
PY
}

if [ "${1-}" = "--podglad" ]; then
  if [ -z "${2-}" ]; then echo "Podaj plik: ./mac-zainstaluj.sh --podglad /tmp/panel.plist"; exit 1; fi
  zapisz_plist "$2"
  echo "Zapisano $2 (bez instalacji)."
  exit 0
fi

PORT="$(ustawienie PANEL_PORT 4801)"
DOMENA="gui/$(id -u)"

# Wcześniejsza instalacja zwalnia port, zanim go sprawdzimy.
if launchctl print "$DOMENA/$LABEL" >/dev/null 2>&1; then
  launchctl bootout "$DOMENA/$LABEL" >/dev/null 2>&1 || true
  sleep 2
  echo "Zatrzymano wcześniejszą instalację."
fi

ZAJETY="$(lsof -nP -iTCP:"$PORT" -sTCP:LISTEN 2>/dev/null | tail -n +2 || true)"
if [ -n "$ZAJETY" ]; then
  echo "Port $PORT jest zajęty:"
  echo "$ZAJETY" | awk '{print "  " $1 " (PID " $2 ")"}'
  echo "Jeżeli to panel uruchomiony ręcznie, zatrzymaj go (Ctrl+C w jego terminalu) i uruchom ten skrypt ponownie."
  echo "Inny port: dopisz PANEL_PORT=4802 do dashboard/panel.env."
  exit 1
fi

mkdir -p "$HOME/Library/LaunchAgents" "$HOME/Library/Logs"
zapisz_plist "$PLIST"
chmod 644 "$PLIST"
launchctl bootstrap "$DOMENA" "$PLIST"
echo "Zainstalowano: $PLIST"

i=0
while [ "$i" -lt 10 ]; do
  if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then break; fi
  sleep 1
  i=$((i + 1))
done
if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Panel działa: $(adres_panelu)"
else
  echo "Panel jeszcze nie odpowiada. Sprawdź log: $LOG"
fi
echo "Log: $LOG"
echo "Po zmianie dashboard/panel.env uruchom ten skrypt ponownie. Wyłączenie: ./mac-odinstaluj.sh"
