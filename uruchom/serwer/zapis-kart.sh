#!/bin/bash
# Zapis kart i raportów IntegrateSystems do GitHuba. Uruchamiany co 15 min przez timer zapis-kart (użytkownik panel).
# Commituje i wypycha TYLKO zmiany w szkice/ i raporty/. Zmiany w innych miejscach drzewa zostają na dysku
# bez zmian (także te dodane do indeksu); dziennik wypisuje ostrzeżenie z ich liczbą.
# Pliki wyglądające na sekrety albo bazy danych (.env*, *.env, *.key, *.pem, credentials*, *.sqlite, *.db)
# nie trafiają do commita; wyjątek: pliki przykładowe *.przyklad. Pominięte pliki są wypisane jako ostrzeżenie.
# Działa tylko na gałęzi main (ZAPIS_KART_GALAZ). Gdy agent ma wybraną inną gałąź, zapis czeka do powrotu na main.
# Lokalne commity spoza szkice/ i raporty/ blokują push: potrzebna decyzja właściciela.
set -u
cd "${ZAPIS_KART_DIR:-/home/panel/IntegrateSystems}" || exit 1
GALAZ="${ZAPIS_KART_GALAZ:-main}"
SCIEZKI=(szkice raporty)
log() { echo "zapis-kart: $*"; }

# 0, gdy ścieżka wygląda na sekret albo bazę danych.
sekret() {
  local b="${1##*/}"
  case "$b" in *.przyklad) return 1 ;; esac
  case "$b" in
    .env|.env.*|.env[-_]*|*.env|*.key|*.pem|credentials|credentials*|\
    *.sqlite|*.sqlite3|*.sqlite-wal|*.sqlite-shm|*.sqlite-journal|*.db|*.db-wal|*.db-shm|*.db-journal)
      return 0 ;;
  esac
  return 1
}

# 0, gdy ścieżka leży w szkice/ albo raporty/.
nasza() {
  local s
  for s in "${SCIEZKI[@]}"; do
    case "$1" in "$s"/*) return 0 ;; esac
  done
  return 1
}

obecna="$(git branch --show-current 2>/dev/null)"
if [ "$obecna" != "$GALAZ" ]; then
  log "OSTRZEŻENIE: wybrana gałąź '${obecna:-odłączony HEAD}' zamiast $GALAZ (praca agenta?); zapis pominięty"
  exit 0
fi

if ! git pull -q --rebase --autostash; then
  git rebase --abort 2>/dev/null
  log "BŁĄD: konflikt przy pobieraniu z GitHuba; zmiany zostają na serwerze, potrzebna decyzja właściciela"
  exit 1
fi

stan_git="$(mktemp)"
lista="$(mktemp)"
indeks="$(mktemp)"
trap 'rm -f "$stan_git" "$lista" "$indeks"' EXIT
git status --porcelain=v1 -z --untracked-files=all > "$stan_git" || { log "BŁĄD: git status nieudany"; exit 1; }

# -z: ścieżki bez cudzysłowów; przy zmianie nazwy (R, C) po nowej ścieżce idzie stara.
inne=0; inne_przyklad=""
dodaj() {  # ścieżka stan
  if ! nasza "$1"; then
    inne=$((inne + 1))
    [ "$inne" -le 3 ] && inne_przyklad="$inne_przyklad $1"
  elif sekret "$1"; then
    log "OSTRZEŻENIE: pominięto plik wyglądający na sekret albo bazę danych: $1"
  else
    printf '%s\0' "$1" >> "$lista"
  fi
}
while IFS= read -r -d '' wpis; do
  stan="${wpis:0:2}"
  dodaj "${wpis:3}"
  case "$stan" in R*|C*) IFS= read -r -d '' stara && dodaj "$stara" ;; esac
done < "$stan_git"
if [ "$inne" -gt 0 ]; then
  log "OSTRZEŻENIE: zmiany poza szkice/ i raporty/ zostają niezapisane: $inne (np.$inne_przyklad)"
fi

# Commit z osobnego indeksu zbudowanego od HEAD: to, co ktoś dodał do zwykłego indeksu poza naszymi
# ścieżkami, nie trafi do commita. Po commicie zwykły indeks dla zapisanych ścieżek dostaje stan HEAD.
if [ -s "$lista" ]; then
  export GIT_INDEX_FILE="$indeks"
  git read-tree HEAD || { log "BŁĄD: nie można przygotować indeksu"; exit 1; }
  git --literal-pathspecs add -A --pathspec-from-file="$lista" --pathspec-file-nul
  if ! git diff --cached --quiet; then
    git -c user.name="Serwer integrate" -c user.email="serwer@integrate.local" \
        commit -q --no-verify -m "Panel: zmiany z serwera $(date '+%Y-%m-%d %H:%M')" \
      || { unset GIT_INDEX_FILE; log "BŁĄD: commit nieudany"; exit 1; }
    unset GIT_INDEX_FILE
    git --literal-pathspecs reset -q --pathspec-from-file="$lista" --pathspec-file-nul 2>/dev/null \
      || log "OSTRZEŻENIE: indeks nie zaktualizowany (git status może pokazać zapisane pliki jako zmienione)"
  fi
  unset GIT_INDEX_FILE
fi

# Push tylko wtedy, gdy wszystkie niewypchnięte commity dotyczą szkice/ i raporty/.
if [ -n "$(git log --oneline '@{u}..HEAD' 2>/dev/null)" ]; then
  obce="$(git diff --name-only '@{u}' HEAD -- . ':(exclude)szkice' ':(exclude)raporty' | wc -l | tr -d ' ')"
  if [ "$obce" != "0" ]; then
    log "BŁĄD: niewypchnięte commity zmieniają pliki poza szkice/ i raporty/ ($obce); push wstrzymany, potrzebna decyzja właściciela (git log @{u}..HEAD)"
    exit 1
  fi
  if git push -q; then log "wypchnięto $(git log -1 --format=%h)"; else log "BŁĄD: push nieudany"; exit 1; fi
fi
exit 0
