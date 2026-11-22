#!/bin/bash
# Rozpoznawanie mowy dla asystenta panelu (przycisk „Mów”, dashboard/glos.py i dashboard/glos_stt.py).
# Uruchom raz jako root z repozytorium produkcji:
#   sudo bash /home/panel/IntegrateSystems/uruchom/serwer/zainstaluj-glos.sh             instalacja, próba, restart panelu
#   sudo bash /home/panel/IntegrateSystems/uruchom/serwer/zainstaluj-glos.sh --sprawdz   sama próba, bez zmian
# 1. python3-venv (apt), venv /home/panel/narzedzia/glos (właściciel panel), pakiet faster-whisper
# 2. model small (int8) pobrany do /home/panel/narzedzia/glos/modele: panel nie pobiera nic przy pierwszym nagraniu
# 3. próba: pracownik glos_stt.py startuje i rozpoznaje sekundę ciszy
# 4. /etc/integrate/panel.env: PANEL_GLOS_PYTHON, PANEL_GLOS_MODELE (kopia pliku sprzed zmiany: panel.env.przed-glosem)
# 5. restart panelu (mikrofon pojawia się w oknie asystenta)
# Pamięć: model wczytuje się przy pierwszym nagraniu (ok. 0,5 GB) i zwalnia po 10 min bez nagrań.
# Powtórne uruchomienie jest bezpieczne.
set -eu
TU="$(cd "$(dirname "$0")" && pwd)"
IS="$(cd "$TU/../.." && pwd)"
PANEL=panel
NARZEDZIA=/home/$PANEL/narzedzia
VENV=$NARZEDZIA/glos
MODELE=$VENV/modele
MODEL=small
ENV_PLIK=/etc/integrate/panel.env
PRACOWNIK=$IS/dashboard/glos_stt.py

przerwij() { echo "Przerwano: $*" >&2; exit 1; }
jako_panel() { runuser -u "$PANEL" -- "$@"; }

SPRAWDZ=0
case "${1:-}" in
  "") ;;
  --sprawdz) SPRAWDZ=1 ;;
  -h|--help) sed -n '3,5p' "$0" | sed 's/^# *//'; exit 0 ;;
  *) echo "Nieznana opcja: $1 (dozwolona: --sprawdz)" >&2; exit 2 ;;
esac

[ "$(id -u)" -eq 0 ] || przerwij "uruchom przez sudo."
id "$PANEL" >/dev/null 2>&1 || przerwij "brak użytkownika $PANEL."
[ -f "$PRACOWNIK" ] || przerwij "brak $PRACOWNIK (stara wersja panelu? najpierw wdrożenie)."

proba() {
  local wav
  wav="$(mktemp --suffix=.wav)"
  # najpierw zapis (root), potem właściciel: w /tmp root nie otworzy do zapisu cudzego pliku (protected_regular)
  python3 - "$wav" <<'P'   # systemowy python: root nie uruchamia plików z venv panelu
import sys, wave
with wave.open(sys.argv[1], "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000); w.writeframes(b"\0\0" * 16000)
P
  chown "$PANEL" "$wav"
  local wynik
  wynik="$(printf '{"id": 1, "plik": "%s", "podpowiedz": "Panel projektów."}\n' "$wav" \
    | jako_panel env PANEL_GLOS_MODELE="$MODELE" PANEL_GLOS_MODEL="$MODEL" timeout 300 "$VENV/bin/python" "$PRACOWNIK" 2>/dev/null)"
  rm -f "$wav"
  echo "$wynik" | grep -q '"gotowy": true' || { echo "$wynik" >&2; return 1; }
  echo "$wynik" | grep -q '"id": 1, "tekst"' || { echo "$wynik" >&2; return 1; }
  echo "Próba: pracownik wczytał model i rozpoznał nagranie ($(echo "$wynik" | sed -n 's/.*"ms": \([0-9]*\).*/\1/p') ms)."
}

if [ "$SPRAWDZ" -eq 1 ]; then
  [ -x "$VENV/bin/python" ] || przerwij "brak $VENV (instalacja nie była uruchomiona)."
  proba || przerwij "próba nieudana."
  grep -q "^PANEL_GLOS_PYTHON=$VENV/bin/python$" "$ENV_PLIK" && echo "panel.env: PANEL_GLOS_PYTHON ustawione." \
    || echo "BRAK: PANEL_GLOS_PYTHON w $ENV_PLIK."
  exit 0
fi

echo "1. venv i faster-whisper"
command -v python3 >/dev/null || przerwij "brak python3."
if ! python3 -c "import ensurepip, venv" 2>/dev/null; then
  DEBIAN_FRONTEND=noninteractive apt-get install -y -q python3-venv >/dev/null
fi
install -d -m 750 -o "$PANEL" -g "$PANEL" "$NARZEDZIA"
[ -x "$VENV/bin/python" ] || jako_panel python3 -m venv "$VENV"
jako_panel "$VENV/bin/python" -m pip install -q --upgrade pip
jako_panel "$VENV/bin/python" -m pip install -q --upgrade faster-whisper

echo "2. Model $MODEL (int8) do $MODELE"
install -d -m 750 -o "$PANEL" -g "$PANEL" "$MODELE"
jako_panel "$VENV/bin/python" -c "
from faster_whisper import WhisperModel
WhisperModel('$MODEL', device='cpu', compute_type='int8', download_root='$MODELE')
print('Model gotowy.')"

echo "3. Próba pracownika"
proba || przerwij "próba nieudana; panel.env bez zmian."

echo "4. $ENV_PLIK"
[ -f "$ENV_PLIK" ] || przerwij "brak $ENV_PLIK (panel nie jest zainstalowany według MIGRACJA.md)."
ustaw_env() {  # NAZWA wartość: dopisuje albo zamienia wiersz (uprawnienia pliku bez zmian)
  if grep -qx "$1=$2" "$ENV_PLIK"; then return 0; fi
  [ -f "$ENV_PLIK.przed-glosem" ] || cp -p "$ENV_PLIK" "$ENV_PLIK.przed-glosem"
  if grep -q "^$1=" "$ENV_PLIK"; then
    sed -i "s|^$1=.*|$1=$2|" "$ENV_PLIK"
  else
    printf '%s=%s\n' "$1" "$2" >> "$ENV_PLIK"
  fi
  echo "panel.env: $1=$2"
}
ustaw_env PANEL_GLOS_PYTHON "$VENV/bin/python"
ustaw_env PANEL_GLOS_MODELE "$MODELE"

echo "5. Restart panelu"
systemctl restart panel
echo "Gotowe. W panelu: Asystent → Mów (albo przytrzymaj spację)."
