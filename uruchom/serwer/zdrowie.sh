#!/bin/bash
# Kontrola zdrowia serwera co 10 min (timer zdrowie, użytkownik panel).
# Sprawdza: panel (/api/data lokalnie), asystent Useme (/api/health), wolne miejsce na dysku (>= 15%),
# logowanie Claude (claude auth status), wiek ostatniej kopii (< 36 h) i ostatni przebieg zapisu kart.
# Powiadomienie ntfy tylko przy zmianie stanu: dobry -> zły i zły -> dobry. Treść bez danych klientów.
# Stan poprzedni: /home/panel/.zdrowie-stan (wiersze nazwa=ok|zle|brak).
# Ustawienia (opcjonalne, /etc/integrate/serwer.env): USEME_URL (pełny adres /api/health), ZDROWIE_PROG_DYSKU (domyślnie 15).
set -u
BAZA="${ZDROWIE_BAZA:-/home/panel}"
STAN="${ZDROWIE_STAN:-$BAZA/.zdrowie-stan}"
PANEL_URL="${ZDROWIE_PANEL_URL:-http://127.0.0.1:4801/api/data}"
PROG="${ZDROWIE_PROG_DYSKU:-15}"
log() { echo "zdrowie: $*"; }

ntfy() {
  [ -n "${PANEL_NTFY_URL:-}" ] || { log "PANEL_NTFY_URL nieustawiony, bez powiadomienia"; return 0; }
  curl -fsS -m 10 -H "Content-Type: text/plain; charset=utf-8" -H "Priority: $2" -H "Tags: $3" \
       --data-binary "$1" "$PANEL_NTFY_URL" >/dev/null 2>&1 || log "nie udało się wysłać powiadomienia"
}

# Wyniki: NAZWY[i], WYNIK[i] (ok|zle|brak), OPIS[i] (krótko, bez danych klientów).
NAZWY=(); WYNIK=(); OPIS=()
wynik() { NAZWY+=("$1"); WYNIK+=("$2"); OPIS+=("$3"); }

kod_http() {  # adres [nagłówek]; wypisuje kod HTTP albo 000; treści odpowiedzi nie czytamy
  if [ -n "${2:-}" ]; then
    curl -s -o /dev/null -w '%{http_code}' -m 15 -H "$2" "$1" 2>/dev/null
  else
    curl -s -o /dev/null -w '%{http_code}' -m 15 "$1" 2>/dev/null
  fi
}

# 1. Panel: połączenie lokalne z Host: localhost przechodzi bez hasła (dashboard/AGENCI.md).
k="$(kod_http "$PANEL_URL" "Host: localhost")"
if [ "$k" = "200" ]; then wynik panel ok "panel działa"
else wynik panel zle "panel nie odpowiada poprawnie (HTTP ${k:-000})"; fi

# 2. Asystent Useme. Adres z USEME_URL; bez niego port z nasłuchu procesu usługi useme.
useme_url="${USEME_URL:-}"
if [ -z "$useme_url" ] && systemctl cat useme.service >/dev/null 2>&1; then
  pid="$(systemctl show -p MainPID --value useme.service 2>/dev/null)"
  if [ -n "$pid" ] && [ "$pid" != "0" ]; then
    port="$(ss -ltnpH 2>/dev/null | grep "pid=$pid," | awk '{print $4}' | sed -n 's/.*:\([0-9][0-9]*\)$/\1/p' | head -n 1)"
    [ -n "$port" ] && useme_url="http://127.0.0.1:$port/api/health"
  fi
fi
if [ -n "$useme_url" ]; then
  k="$(kod_http "$useme_url")"
  if [ "$k" = "200" ]; then wynik useme ok "asystent Useme działa"
  else wynik useme zle "asystent Useme nie odpowiada (HTTP ${k:-000})"; fi
elif systemctl cat useme.service >/dev/null 2>&1; then
  if systemctl is-active --quiet useme.service; then wynik useme ok "asystent Useme działa (bez adresu /api/health)"
  else wynik useme zle "usługa useme nie działa"; fi
else
  wynik useme brak "usługa useme nie jest zainstalowana"
fi

# 3. Wolne miejsce: / i folder panelu (gdy to inny system plików).
dysk=ok; dysk_opis=""
for mp in $(df -P / "$BAZA" 2>/dev/null | awk 'NR>1 {print $6}' | sort -u); do
  wolne="$(df -P "$mp" | awk 'NR==2 && $2 > 0 {printf "%d", $4 * 100 / $2}')"
  [ -n "$wolne" ] || continue
  if [ "$wolne" -lt "$PROG" ]; then dysk=zle; dysk_opis="$dysk_opis $mp: $wolne% wolnego;"; fi
done
if [ "$dysk" = ok ]; then wynik dysk ok "miejsce na dysku w normie"
else wynik dysk zle "mało miejsca na dysku:${dysk_opis%;}"; fi

# 4. Claude zalogowany. Wypisujemy tylko loggedIn; adresu konta nie zapisujemy.
claude_bin="$(command -v claude 2>/dev/null || true)"
[ -n "$claude_bin" ] || { [ -x "$BAZA/.local/bin/claude" ] && claude_bin="$BAZA/.local/bin/claude"; }
limit_czasu=(); command -v timeout >/dev/null && limit_czasu=(timeout 60)
if [ -z "$claude_bin" ]; then
  wynik claude zle "nie znaleziono polecenia claude"
elif ${limit_czasu[@]+"${limit_czasu[@]}"} "$claude_bin" auth status 2>/dev/null | grep -Eq '"loggedIn"[[:space:]]*:[[:space:]]*true'; then
  wynik claude ok "Claude zalogowany"
else
  wynik claude zle "Claude niezalogowany: zaloguj w panelu albo przez ssh (claude auth login)"
fi

# 5. Ostatnia kopia nie starsza niż 36 h (pomijane, dopóki nie ma żadnej kopii).
ostatnia=""
for a in "$BAZA"/kopie/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].tar.gz; do [ -f "$a" ] && ostatnia="$a"; done
if [ -z "$ostatnia" ]; then
  wynik kopia brak "brak kopii"
else
  wiek=$(( ( $(date +%s) - $(stat -c %Y "$ostatnia" 2>/dev/null || stat -f %m "$ostatnia") ) / 3600 ))
  if [ "$wiek" -lt 36 ] && ! systemctl is-failed --quiet kopia.service 2>/dev/null; then wynik kopia ok "kopia aktualna"
  else wynik kopia zle "ostatnia kopia sprzed $wiek h albo ostatni przebieg nieudany (journalctl -u kopia)"; fi
fi

# 6. Zapis kart do GitHuba: ostatni przebieg usługi.
if systemctl cat zapis-kart.service >/dev/null 2>&1; then
  if systemctl is-failed --quiet zapis-kart.service; then
    wynik zapis-kart zle "zapis kart do GitHuba nieudany (journalctl -u zapis-kart)"
  else
    wynik zapis-kart ok "zapis kart działa"
  fi
else
  wynik zapis-kart brak "zapis kart nie jest zainstalowany"
fi

# Porównanie ze stanem poprzednim i powiadomienia przy zmianie.
poprzedni() { [ -f "$STAN" ] && sed -n "s/^$1=//p" "$STAN" | head -n 1; }
nowy_stan="$(mktemp "${STAN}.XXXXXX")" || { log "BŁĄD: nie można zapisać stanu"; exit 1; }
zle_teraz=0; zmiany_zle=""; zmiany_ok=""
i=0
while [ "$i" -lt "${#NAZWY[@]}" ]; do
  n="${NAZWY[$i]}"; w="${WYNIK[$i]}"; o="${OPIS[$i]}"
  echo "$n=$w" >> "$nowy_stan"
  p="$(poprzedni "$n")"
  [ "$w" = zle ] && zle_teraz=$((zle_teraz + 1))
  if [ "$w" = zle ] && [ "$p" != zle ]; then zmiany_zle="$zmiany_zle- $o"$'\n'
  elif [ "$w" = ok ] && [ "$p" = zle ]; then zmiany_ok="$zmiany_ok- $o"$'\n'; fi
  log "$n: $w ($o)"
  i=$((i + 1))
done
mv -f "$nowy_stan" "$STAN"

if [ -n "$zmiany_zle" ]; then
  ntfy "Serwer: problem"$'\n'"${zmiany_zle%$'\n'}" high warning
fi
if [ -n "$zmiany_ok" ]; then
  ntfy "Serwer: znów w porządku"$'\n'"${zmiany_ok%$'\n'}" default white_check_mark
fi
[ "$zle_teraz" -eq 0 ]
