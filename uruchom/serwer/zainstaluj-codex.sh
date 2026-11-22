#!/bin/bash
# Codex CLI (OpenAI) dla użytkownika agent: grafiki do postów w edytorze posta i zadania `kto: codex`.
# Uruchom raz jako root z repozytorium produkcji:
#   sudo bash /home/panel/IntegrateSystems/uruchom/serwer/zainstaluj-codex.sh             instalacja, próba, restart panelu
#   sudo bash /home/panel/IntegrateSystems/uruchom/serwer/zainstaluj-codex.sh --sprawdz   sama próba, bez zmian
# 1. bubblewrap (apt): piaskownica Codex na Linuksie (workspace-write)
# 2. Codex dla agent oficjalnym instalatorem OpenAI (https://chatgpt.com/codex/install.sh, zapisany do pliku, nie
#    przez potok): samodzielne wydanie bez Node.js, arm64/aarch64 albo x86_64; instalator sam sprawdza sumę SHA-256
#    archiwum z danymi wydania (releases.openai.com, zapasowo GitHub Releases openai/codex). Wynik:
#    /home/agent/.local/bin/codex (dowiązanie do /home/agent/.codex/packages/standalone/current).
# 3. uprawnienia: panel widzi plik polecenia (samo przejście x po katalogach) i czyta generated_images (grupa panel)
# 4. /etc/sudoers.d/91-panel-agent-codex: panel uruchamia jako agent tylko /home/agent/.local/bin/codex (visudo -c)
# 5. /etc/integrate/panel.env: PANEL_CODEX, PANEL_GRAFIKA=codex (kopia sprzed zmiany: panel.env.przed-codexem)
# 6. restart panelu
# Logowanie robi właściciel swoim kontem ChatGPT (skrypt nie loguje i nie zna haseł ani tokenów):
#   - w panelu: edytor posta → Grafika (Codex) → Zaloguj Codex (strona OpenAI i jednorazowy kod), albo
#   - w terminalu serwera: sudo -u agent -H /home/agent/.local/bin/codex login --device-auth
#   Najpierw włącz „logowanie kodem urządzenia” w ustawieniach bezpieczeństwa ChatGPT (Settings → Security).
# Wersja: CODEX_RELEASE=0.171.0 sudo -E bash …/zainstaluj-codex.sh (domyślnie najnowsza). Ponowne uruchomienie jest
# bezpieczne (aktualizuje Codex do wskazanej wersji).
set -eu
PANEL=panel
AGENT=agent
AGENT_DOM=/home/$AGENT
AGENT_CODEX=$AGENT_DOM/.local/bin/codex
OBRAZY=$AGENT_DOM/.codex/generated_images
SUDOERS=/etc/sudoers.d/91-panel-agent-codex
ENV_PLIK=/etc/integrate/panel.env
INSTALATOR_URL=https://chatgpt.com/codex/install.sh

przerwij() { echo "Przerwano: $*" >&2; exit 1; }
jako_agent() { runuser -u "$AGENT" -- env HOME="$AGENT_DOM" "$@"; }

SPRAWDZ=0
case "${1:-}" in
  "") ;;
  --sprawdz) SPRAWDZ=1 ;;
  -h|--help) sed -n '3,5p' "$0" | sed 's/^# *//'; exit 0 ;;
  *) echo "Nieznana opcja: $1 (dozwolona: --sprawdz)" >&2; exit 2 ;;
esac

[ "$(id -u)" -eq 0 ] || przerwij "uruchom przez sudo."
id "$PANEL" >/dev/null 2>&1 || przerwij "brak użytkownika $PANEL."
id "$AGENT" >/dev/null 2>&1 || przerwij "brak użytkownika $AGENT (najpierw zainstaluj-uzytkownika-agenta.sh)."
case "$(uname -m)" in
  aarch64|arm64|x86_64|amd64) ;;
  *) przerwij "architektura $(uname -m) bez wydania Codex dla Linuksa." ;;
esac

proba() {
  local wersja stan
  wersja="$(jako_agent "$AGENT_CODEX" --version 2>/dev/null)" || { echo "Codex nie odpowiada." >&2; return 1; }
  echo "Codex: $wersja"
  # Panel uruchamia Codexa przez sudo tak samo jak tutaj: reguła sudoers i przejście do pliku dla panelu.
  runuser -u "$PANEL" -- sudo -n -u "$AGENT" -- "$AGENT_CODEX" --version >/dev/null 2>&1 \
    || { echo "Panel nie może uruchomić Codexa jako $AGENT (sudoers)." >&2; return 1; }
  runuser -u "$PANEL" -- test -f "$AGENT_CODEX" || { echo "Panel nie widzi $AGENT_CODEX." >&2; return 1; }
  if jako_agent "$AGENT_CODEX" sandbox linux --full-auto -- true >/dev/null 2>&1; then
    echo "Piaskownica Codex działa."
  else
    echo "UWAGA: próba piaskownicy Codex nieudana (codex sandbox linux). Zadania mogą kończyć się błędem uprawnień;" \
         "sprawdź bubblewrap i ograniczenia przestrzeni nazw (AppArmor)." >&2
  fi
  stan="$(jako_agent "$AGENT_CODEX" login status 2>&1 || true)"
  case "$stan" in
    *"Logged in"*) echo "Logowanie: $stan" ;;
    *) echo "Logowanie: brak. Zaloguj się w panelu (edytor posta → Grafika (Codex) → Zaloguj Codex) albo:"
       echo "  sudo -u $AGENT -H $AGENT_CODEX login --device-auth" ;;
  esac
}

if [ "$SPRAWDZ" -eq 1 ]; then
  [ -x "$AGENT_CODEX" ] || przerwij "brak $AGENT_CODEX (instalacja nie była uruchomiona)."
  proba || przerwij "próba nieudana."
  grep -qx "PANEL_CODEX=$AGENT_CODEX" "$ENV_PLIK" && echo "panel.env: PANEL_CODEX ustawione." \
    || echo "BRAK: PANEL_CODEX w $ENV_PLIK."
  exit 0
fi

echo "1. bubblewrap"
command -v curl >/dev/null || przerwij "brak curl (sudo apt install curl)."
if ! command -v bwrap >/dev/null; then
  DEBIAN_FRONTEND=noninteractive apt-get install -y -q bubblewrap >/dev/null || przerwij "apt-get install bubblewrap nieudane."
fi

echo "2. Codex dla $AGENT"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
curl -fsSL --proto '=https' --tlsv1.2 "$INSTALATOR_URL" -o "$TMP/install.sh" || przerwij "nie pobrano $INSTALATOR_URL."
head -n 1 "$TMP/install.sh" | grep -q '^#!/bin/sh' || przerwij "pobrany instalator nie wygląda na skrypt powłoki."
grep -q 'verify_archive_digest' "$TMP/install.sh" || przerwij "instalator bez sprawdzania sumy SHA-256; nie uruchamiam."
chmod 755 "$TMP"
chmod 644 "$TMP/install.sh"
jako_agent env CODEX_NON_INTERACTIVE=1 CODEX_RELEASE="${CODEX_RELEASE:-latest}" sh "$TMP/install.sh" \
  || przerwij "instalator Codex nieudany."
[ -x "$AGENT_CODEX" ] || przerwij "po instalacji nie ma $AGENT_CODEX."

echo "3. Uprawnienia"
# Panel sprawdza PANEL_CODEX (os.path.isfile): przejście x po katalogach do pliku i jego celu, bez listy plików.
# auth.json Codex ma tryb 600: przejście przez ~/.codex go nie odsłania.
cel="$(readlink -f "$AGENT_CODEX")"
for p in "$AGENT_CODEX" "$cel"; do
  d="$(dirname "$p")"
  while [ "$d" != "$AGENT_DOM" ] && [ "$d" != "/" ]; do
    case "$d" in "$AGENT_DOM"/*) chmod o+x "$d" ;; esac
    d="$(dirname "$d")"
  done
done
# Obrazy z sesji Codex (gdy Codex nie skopiował wyniku do folderu posta, panel bierze go stąd): grupa panel, setgid.
install -d -o "$AGENT" -g "$PANEL" -m 2750 "$OBRAZY"
chgrp "$PANEL" "$OBRAZY"; chmod 2750 "$OBRAZY"

echo "4. $SUDOERS"
tmp="$(mktemp)"
cat > "$tmp" <<EOF
# Panel (użytkownik $PANEL) uruchamia Codex jako $AGENT (grafiki do postów, zadania kto: codex), bez hasła.
# Plik instaluje uruchom/serwer/zainstaluj-codex.sh; zmiany tylko tam.
$PANEL ALL=($AGENT) NOPASSWD: $AGENT_CODEX
EOF
chmod 440 "$tmp"
if visudo -c -q -f "$tmp" >/dev/null; then
  cmp -s "$tmp" "$SUDOERS" || install -o root -g root -m 440 "$tmp" "$SUDOERS"
else
  rm -f "$tmp"; przerwij "reguła sudoers nie przeszła visudo -c; nic nie zapisano."
fi
rm -f "$tmp"
visudo -c -q >/dev/null || { rm -f "$SUDOERS"; przerwij "visudo -c dla całej konfiguracji nieudane; $SUDOERS usunięty."; }

echo "5. Próba"
proba || przerwij "próba nieudana; panel.env bez zmian."

echo "6. $ENV_PLIK"
[ -f "$ENV_PLIK" ] || przerwij "brak $ENV_PLIK (panel nie jest zainstalowany według MIGRACJA.md)."
ustaw_env() {  # NAZWA wartość: dopisuje albo zamienia wiersz (uprawnienia pliku bez zmian)
  if grep -qx "$1=$2" "$ENV_PLIK"; then return 0; fi
  [ -f "$ENV_PLIK.przed-codexem" ] || cp -p "$ENV_PLIK" "$ENV_PLIK.przed-codexem"
  if grep -q "^$1=" "$ENV_PLIK"; then
    sed -i "s|^$1=.*|$1=$2|" "$ENV_PLIK"
  else
    printf '%s=%s\n' "$1" "$2" >> "$ENV_PLIK"
  fi
  echo "panel.env: $1=$2"
}
ustaw_env PANEL_CODEX "$AGENT_CODEX"          # reguła sudoers dopuszcza tylko tę ścieżkę
grep -q "^PANEL_GRAFIKA=" "$ENV_PLIK" || ustaw_env PANEL_GRAFIKA codex

echo "7. Restart panelu"
systemctl restart panel
echo "Gotowe. Zaloguj Codex kontem ChatGPT: panel → edytor posta → Grafika (Codex) → Zaloguj Codex."
