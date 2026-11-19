#!/bin/bash
# Część wspólna instalatorów zainstaluj-*.sh (wczytywana przez `source`, nie uruchamiana osobno).
# 1. Sprawdza, że uruchom/serwer w kopii roboczej na serwerze jest identyczny z origin/main (git fetch jako
#    właściciel repozytorium, zwykle panel). Różnica albo pliki spoza gita: instalacja przerwana.
# 2. Kopiuje skrypty i jednostki do /usr/local/lib/integrate (właściciel root, 755). Instalatory instalują stamtąd,
#    więc późniejsze zmiany w kopii roboczej (np. przez agenta) nie zmieniają tego, co działa.
LIB=/usr/local/lib/integrate
REPO="$(cd "$TU/../.." && pwd)"

przerwij() { echo "Przerwano: $*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || przerwij "uruchom przez sudo."
id panel >/dev/null 2>&1 || przerwij "brak użytkownika panel."

sprawdz_zgodnosc() {
  local wl
  wl="$(stat -c %U "$REPO")"
  jako() { sudo -u "$wl" -H "$@"; }
  echo "Sprawdzam zgodność $REPO/uruchom/serwer z origin/main..."
  jako git -C "$REPO" fetch -q origin main \
    || przerwij "git fetch nieudany (sieć albo klucz GitHub użytkownika $wl); nic nie zainstalowano."
  if ! jako git -C "$REPO" diff --quiet origin/main -- uruchom/serwer; then
    jako git -C "$REPO" --no-pager diff --stat origin/main -- uruchom/serwer >&2
    przerwij "uruchom/serwer różni się od origin/main. Zainstaluj tylko to, co jest na GitHubie:
  sudo -u $wl git -C $REPO pull --ff-only   (albo wycofaj lokalne zmiany), potem uruchom instalator ponownie."
  fi
  if [ -n "$(jako git -C "$REPO" ls-files --others --exclude-standard -- uruchom/serwer)" ]; then
    jako git -C "$REPO" ls-files --others --exclude-standard -- uruchom/serwer >&2
    przerwij "w uruchom/serwer są pliki spoza gita (lista wyżej); usuń je albo dodaj do repozytorium."
  fi
  echo "Zgodne z origin/main ($(jako git -C "$REPO" rev-parse --short origin/main))."
}

kopiuj_do_lib() {
  local nowy="$LIB.nowy" f
  rm -rf "$nowy"
  install -d -o root -g root -m 755 "$nowy" "$nowy/konfiguracja"
  for f in "$TU"/*.sh; do install -o root -g root -m 755 "$f" "$nowy/"; done
  for f in "$TU"/*.service "$TU"/*.timer "$TU"/*.przyklad; do
    if [ -f "$f" ]; then install -o root -g root -m 644 "$f" "$nowy/"; fi
  done
  for f in "$TU"/konfiguracja/*; do
    if [ -f "$f" ]; then install -o root -g root -m 644 "$f" "$nowy/konfiguracja/"; fi
  done
  rm -rf "$LIB"
  mv "$nowy" "$LIB"
  echo "Skopiowano do $LIB."
}

sprawdz_zgodnosc
kopiuj_do_lib
