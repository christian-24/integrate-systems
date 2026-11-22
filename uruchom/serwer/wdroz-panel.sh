#!/bin/bash
# Wdrożenie panelu z gałęzi rozwoj (kopia robocza agenta) na produkcję, jako root.
# Automat: wdroz-panel-auto.path (nowy commit na rozwoj) i wdroz-panel-auto.timer (co 5 min) uruchamiają
# „wdroz-panel --auto”: bez nowych commitów albo przy commicie, którego wdrożenie już się nie udało, kończy bez śladu.
# Ręcznie: przycisk w panelu (sudo systemctl start --no-block wdroz-panel.service), także ponowienie nieudanego.
# Kolejność: testy jako agent na sprawdzanym commicie → pull produkcji → scalenie → restart → kontrola strony
# → push do GitHuba. Błąd po scaleniu: produkcja wraca do poprzedniego commita (git reset --keep, zmiany kart
# na dysku zostają) i panel startuje ponownie. Stan dla panelu: $STAN (JSON), dziennik: $LOG.
# Instaluje uruchom/serwer/zainstaluj-rozwoj.sh; zmiany tylko w repozytorium.
set -u
PROD=${WDROZ_PROD:-/home/panel/IntegrateSystems}
DEV=${WDROZ_DEV:-/home/agent/rozwoj/IntegrateSystems}
GAL=${WDROZ_GALAZ:-rozwoj}
DIR=${WDROZ_STAN_DIR:-/home/panel/dane/wdrozenie}
STAN=$DIR/stan.json
LOG=$DIR/ostatnie.log
KLUCZ=/etc/integrate/lokalny.klucz
ENVF=/etc/integrate/panel.env
VENV_PY=/home/panel/narzedzia/film/bin/python
SPRAWDZ="$PROD/uruchom/serwer/sprawdz-panel.py"

AUTO=""; [ "${1:-}" = "--auto" ] && AUTO=1
as_panel() { runuser -u panel -- "$@"; }
as_agent() { runuser -u agent -- "$@"; }

# jedno wdrożenie naraz (automat i przycisk)
exec 9>/run/wdroz-panel.lock
flock -n 9 || { echo "wdrożenie już trwa"; exit 0; }
mkdir -p "$DIR" && chown panel:panel "$DIR" && chmod 750 "$DIR"

if [ -n "$AUTO" ]; then
  sleep "${WDROZ_ZWLOKA:-20}"     # agent kończy serię commitów
  SHA=$(as_agent git -C "$DEV" rev-parse --verify -q "$GAL^{commit}") || exit 0
  as_panel git -C "$PROD" fetch -q --no-tags --no-write-fetch-head "$DEV" "+$GAL:refs/rozwoj/kandydat" || exit 0
  as_panel git -C "$PROD" merge-base --is-ancestor "$SHA" HEAD && exit 0          # nic nowego
  if python3 - "$STAN" "$SHA" <<'PY'
import json, sys
try:
    st = json.load(open(sys.argv[1]))
except (OSError, ValueError):
    sys.exit(1)
sys.exit(0 if st.get("sha") == sys.argv[2] and st.get("state") in ("error", "rolledback") else 1)
PY
  then exit 0; fi                                                                   # ten commit już się nie udał
fi

: > "$LOG" && chown panel:panel "$LOG"
exec >>"$LOG" 2>&1
log() { echo "$(date '+%H:%M:%S') $*"; }
env_val() { sed -n "s/^$1=//p" "$ENVF" 2>/dev/null | tail -n1 | sed "s/^[\"']//; s/[\"']\$//"; }

START=$(date -Iseconds)
SHA="" PREV="" NEW="" N=0
# stan state [opis]: zapis atomowy, czytelny dla panelu
stan() {
  local tmp
  tmp=$(mktemp "$DIR/.stan.XXXX")
  python3 - "$1" "${2:-}" "$START" "$SHA" "$PREV" "$NEW" "$N" >"$tmp" <<'PY'
import datetime, json, sys
state, text, start, sha, prev, new, n = sys.argv[1:8]
print(json.dumps({"state": state, "text": text, "startedAt": start,
                  "at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
                  "sha": sha, "prev": prev, "new": new, "commits": int(n or 0)}, ensure_ascii=False))
PY
  chown panel:panel "$tmp" && chmod 640 "$tmp" && mv -f "$tmp" "$STAN"
}
powiadom() {
  local url pub
  url=$(env_val PANEL_NTFY_URL)
  pub=$(env_val PANEL_PUBLIC_URL)
  [ -n "$url" ] || return 0
  curl -s -m 10 -H "Content-Type: text/plain; charset=utf-8" ${pub:+-H "Click: ${pub%/}/#koszty"} --data-binary "$1" "$url" >/dev/null || true
}
TMP=""
sprzataj() { [ -n "$TMP" ] && as_agent git -C "$DEV" worktree remove --force "$TMP" >/dev/null 2>&1; true; }
trap sprzataj EXIT
blad() {   # błąd przed scaleniem: produkcja nietknięta
  log "BŁĄD: $1"
  stan error "$1"
  powiadom "Wdrożenie panelu nieudane: $1. Produkcja bez zmian."
  exit 1
}
cofnij() { # błąd po scaleniu: powrót do $PREV
  log "BŁĄD: $1; wracam do ${PREV:0:7}"
  as_panel git -C "$PROD" reset -q --keep "$PREV" || log "reset --keep nieudany; sprawdź ręcznie"
  systemctl restart panel
  sleep 3
  stan rolledback "$1"
  powiadom "Wdrożenie panelu cofnięte: $1. Działa poprzednia wersja."
  exit 1
}

stan running "Sprawdzam gałąź $GAL"
log "Gałąź $GAL w $DEV${AUTO:+ (automat)}"
SHA=$(as_agent git -C "$DEV" rev-parse --verify -q "$GAL^{commit}") || blad "brak gałęzi $GAL w kopii roboczej"

stan running "Testy"
TMP=$(as_agent mktemp -d /tmp/wdrozenie-XXXXXX) || blad "nie utworzono katalogu testów"
rmdir "$TMP"
as_agent git -C "$DEV" worktree add -q --detach "$TMP" "$SHA" || blad "nie przygotowano kopii do testów"
log "Testy na ${SHA:0:7}"
WYNIK=$(mktemp)
# bez renderowania filmów (ffmpeg trwa na serwerze kilkanaście minut); render: dashboard/testy/render_na_serwerze.sh
(cd "$TMP/dashboard/testy" && timeout 1200 runuser -u agent -- env PANEL_TESTY_BEZ_RENDERU=1 python3 -m unittest discover -q) >"$WYNIK" 2>&1
st=$?
tail -n 40 "$WYNIK"; rm -f "$WYNIK"
[ "$st" = 0 ] || blad "testy nie przeszły (dziennik wdrożenia)"
sprzataj; TMP=""

stan running "Scalam z produkcją"
[ "$(as_panel git -C "$PROD" branch --show-current)" = "main" ] || blad "produkcja nie jest na gałęzi main"
as_panel git -C "$PROD" pull -q --rebase --autostash || blad "git pull na produkcji nieudany"
PREV=$(as_panel git -C "$PROD" rev-parse HEAD)
as_panel git -C "$PROD" fetch -q --no-tags --no-write-fetch-head "$DEV" "+$GAL:refs/rozwoj/kandydat" || blad "nie pobrano gałęzi $GAL"
[ "$(as_panel git -C "$PROD" rev-parse refs/rozwoj/kandydat)" = "$SHA" ] || blad "gałąź $GAL zmieniła się w trakcie testów; wdróż ponownie"
N=$(as_panel git -C "$PROD" rev-list --count "HEAD..$SHA")
[ "$N" -gt 0 ] || { stan ok "Nic nowego do wdrożenia"; log "Brak nowych commitów"; exit 0; }
# tożsamość jak w zapis-kart.sh: bez niej scalenie z commitem scalającym kończy się błędem (panel nie ma user.email)
if ! as_panel git -C "$PROD" -c user.name="Serwer integrate" -c user.email="serwer@integrate.local" merge -q --no-edit -m "Wdrożenie z gałęzi $GAL (${SHA:0:7})" "$SHA"; then
  as_panel git -C "$PROD" merge --abort
  blad "konflikt przy scalaniu; połącz main z $GAL w kopii roboczej"
fi
NEW=$(as_panel git -C "$PROD" rev-parse HEAD)
log "Scalono $N commitów: ${PREV:0:7} → ${NEW:0:7}"

stan running "Restart i kontrola"
systemctl restart panel
ok=""
for _ in $(seq 1 30); do
  sleep 2
  code=$(curl -s -o /dev/null -w '%{http_code}' -m 10 -H "X-Panel-Klucz: $(cat "$KLUCZ" 2>/dev/null)" http://127.0.0.1:4801/api/data)
  [ "$code" = "200" ] && { ok=1; break; }
done
[ -n "$ok" ] || cofnij "panel nie odpowiada po restarcie"
if [ -x "$VENV_PY" ] && [ -f "$SPRAWDZ" ]; then
  as_panel "$VENV_PY" "$SPRAWDZ" || cofnij "strona panelu nie działa (dziennik wdrożenia)"
else
  log "Brak Playwright: kontrola strony pominięta"
fi

if as_panel git -C "$PROD" push -q origin HEAD:main; then
  stan ok "Wdrożono $N $( [ "$N" = 1 ] && echo commit || echo commitów )"
else
  stan ok "Wdrożono, ale push do GitHuba nieudany (zapis kart spróbuje później)"
fi
log "Gotowe"
powiadom "Wdrożono panel: $N $( [ "$N" = 1 ] && echo zmiana || echo zmian ) z gałęzi $GAL."
