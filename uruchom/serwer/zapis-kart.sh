#!/bin/bash
# Zapis zmian w IntegrateSystems (karty, zadania, raporty) do GitHuba. Uruchamiany co 15 min przez timer zapis-kart.
# Pliki wyglądające na sekrety albo bazy danych (.env*, *.env, *.key, *.pem, credentials*, *.sqlite, *.db)
# nie trafiają do commita; wyjątek: pliki przykładowe *.przyklad. Pominięte pliki są wypisane jako ostrzeżenie.
set -u
cd "${ZAPIS_KART_DIR:-/home/panel/IntegrateSystems}" || exit 1
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

if ! git pull -q --rebase --autostash; then
  git rebase --abort 2>/dev/null
  log "BŁĄD: konflikt przy pobieraniu z GitHuba; zmiany zostają na serwerze, potrzebna decyzja właściciela"
  exit 1
fi

stan_git="$(mktemp)"
lista="$(mktemp)"
trap 'rm -f "$stan_git" "$lista"' EXIT
git status --porcelain=v1 -z --untracked-files=all > "$stan_git" || { log "BŁĄD: git status nieudany"; exit 1; }
# -z: ścieżki bez cudzysłowów; przy zmianie nazwy (R, C) po nowej ścieżce idzie stara.
while IFS= read -r -d '' wpis; do
  stan="${wpis:0:2}"
  sciezka="${wpis:3}"
  case "$stan" in R*|C*) IFS= read -r -d '' _stara || true ;; esac
  if sekret "$sciezka"; then
    log "OSTRZEŻENIE: pominięto plik wyglądający na sekret albo bazę danych: $sciezka"
    # Plik wcześniej dodany do indeksu: wycofaj go z indeksu, na dysku zostaje bez zmian.
    case "${stan:0:1}" in " "|"?") ;; *) git reset -q -- "$sciezka" 2>/dev/null ;; esac
  else
    printf '%s\0' "$sciezka" >> "$lista"
  fi
done < "$stan_git"

if [ -s "$lista" ]; then
  git --literal-pathspecs add -A --pathspec-from-file="$lista" --pathspec-file-nul
fi
if ! git diff --cached --quiet; then
  git -c user.name="Serwer integrate" -c user.email="serwer@integrate.local" \
      commit -q -m "Panel: zmiany z serwera $(date '+%Y-%m-%d %H:%M')"
fi
if [ -n "$(git log --oneline '@{u}..HEAD' 2>/dev/null)" ]; then
  if git push -q; then log "wypchnięto $(git log -1 --format=%h)"; else log "BŁĄD: push nieudany"; exit 1; fi
fi
