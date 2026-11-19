#!/bin/bash
# Nocna kopia danych serwera. Uruchamiana codziennie o 03:30 przez timer kopia (użytkownik panel).
# Archiwum <BAZA>/kopie/RRRR-MM-DD.tar.gz zawiera:
#   dane/                                 (asystent Useme i inne; bazy SQLite jako spójna kopia przez sqlite3 backup)
#   IntegrateSystems/uruchomienia/, IntegrateSystems/historia/
#   projekty/<repo>/...                   pliki z `git status --porcelain` (zmienione i nieśledzone, bez ignorowanych)
#   git/<repo>.bundle                     commity, których nie ma na zdalnym repozytorium (gdy są)
#   kopia-info.txt                        data, liczby plików, HEAD każdego repozytorium
# Zostaje 14 najnowszych archiwów. Po kopii: <BAZA>/kopie/ostatnia.json
#   {"at": ISO, "size": bajty, "files": n, "off": bool, "offAt": ISO|null}   (off: wysłano poza serwer w tym przebiegu)
# Ustawienia (opcjonalne, /etc/integrate/serwer.env; opis w serwer.env.przyklad i ksiega/MIGRACJA.md):
#   KOPIA_CEL=rclone:<zdalny>:<folder>        rclone copy (zdalny z `sudo -u panel rclone config`, np. sftp do Storage Box)
#   KOPIA_CEL=scp:<host-z-ssh-config>:<folder> scp kluczem użytkownika panel, bez pytań (BatchMode)
#   KOPIA_HASLO_PLIK=<plik>      szyfrowanie przed wysyłką: gpg symetryczny AES256 (plik z hasłem: panel, 600)
#   KOPIA_AGE_ODBIORCY=<plik>    zamiast gpg: age z kluczem publicznym (klucz prywatny tylko u właściciela)
#   KOPIA_CEL_DNI=30             rclone: archiwa starsze niż tyle dni są usuwane z celu (0 = bez usuwania)
# scp bez szyfrowania jest odrzucany (archiwum zawiera dane klientów); rclone bez szyfrowania tylko do zdalnego typu crypt.
# Przy błędzie: powiadomienie ntfy (PANEL_NTFY_URL z /etc/integrate/panel.env), bez nazw plików i danych klientów.
set -u
umask 077
BAZA="${KOPIA_BAZA:-/home/panel}"
KOPIE="$BAZA/kopie"
ZOSTAW=14
DZIS="$(date +%F)"
log() { echo "kopia: $*"; }

ntfy() {
  [ -n "${PANEL_NTFY_URL:-}" ] || return 0
  curl -fsS -m 10 -H "Content-Type: text/plain; charset=utf-8" -H "Priority: high" -H "Tags: warning" \
       --data-binary "$1" "$PANEL_NTFY_URL" >/dev/null 2>&1 || log "nie udało się wysłać powiadomienia"
}

ROB=""
SZYFR=""
sprzataj() {
  [ -n "$ROB" ] && rm -rf "$ROB"
  rm -f "$KOPIE/.$DZIS.tar.gz.tmp" "$KOPIE/.$DZIS.tar.tmp" "$KOPIE/.ostatnia.json.tmp"
  [ -n "$SZYFR" ] && rm -rf "$SZYFR"
}
trap sprzataj EXIT

blad() {
  log "BŁĄD: $1"
  ntfy "Serwer: kopia z $DZIS nieudana ($1). Szczegóły: journalctl -u kopia"
  exit 1
}

mkdir -p "$KOPIE" || blad "brak folderu kopii"
chmod 700 "$KOPIE" 2>/dev/null
ROB="$(mktemp -d "$KOPIE/.rob.XXXXXX")" || blad "brak folderu roboczego"
LISTA="$ROB/lista"
: > "$LISTA"
uwagi=0
n_dane=0; n_proj=0; n_baz=0; n_bundle=0

jest_sqlite() {
  case "${1##*/}" in *.sqlite|*.sqlite3|*.db) ;; *) return 1 ;; esac
  [ "$(head -c 15 "$1" 2>/dev/null)" = "SQLite format 3" ]
}

# 1. Foldery w całości. Bazy SQLite kopiujemy przez API backup (spójny stan mimo zapisów), surowe pliki bazy pomijamy.
for f in dane IntegrateSystems/uruchomienia IntegrateSystems/historia; do
  [ -d "$BAZA/$f" ] || { log "brak $f, pomijam"; continue; }
  while IFS= read -r -d '' p; do
    p="${p#./}"
    if [ -f "$BAZA/$p" ] && [ ! -L "$BAZA/$p" ] && jest_sqlite "$BAZA/$p"; then
      mkdir -p "$ROB/sqlite/$(dirname "$p")"
      if python3 - "$BAZA/$p" "$ROB/sqlite/$p" <<'PY'
import sqlite3, sys
src = sqlite3.connect(sys.argv[1], timeout=60)
dst = sqlite3.connect(sys.argv[2])
src.backup(dst)
dst.close()
src.close()
PY
      then
        n_baz=$((n_baz + 1))
        echo "$p" >> "$ROB/bazy"
        continue
      fi
      log "OSTRZEŻENIE: spójna kopia bazy nieudana, biorę plik bez zmian"
      rm -f "$ROB/sqlite/$p"
      uwagi=$((uwagi + 1))
    fi
    printf '%s\0' "$p" >> "$LISTA"
  done < <(cd "$BAZA" && find "./$f" \( -type f -o -type l \) -print0)
done
# Pliki towarzyszące skopiowanym bazom (-wal, -shm, -journal) są już w spójnej kopii.
if [ -s "$ROB/bazy" ]; then
  sed -e 's/$/-wal/' -e 'p' -e 's/-wal$/-shm/' -e 'p' -e 's/-shm$/-journal/' "$ROB/bazy" > "$ROB/pomin"
  { tr '\0' '\n' < "$LISTA" | grep -v -x -F -f "$ROB/pomin" || true; } | tr '\n' '\0' > "$LISTA.2"
  mv "$LISTA.2" "$LISTA"
fi
n_dane=$(tr -cd '\0' < "$LISTA" | wc -c | tr -d ' ')

# 2. Niezacommitowane zmiany i niewypchnięte commity w repozytoriach projektów.
mkdir -p "$ROB/git"
for repo in "$BAZA"/projekty/*/; do
  repo="${repo%/}"
  [ -d "$repo/.git" ] || [ -f "$repo/.git" ] || continue
  nazwa="${repo##*/}"
  echo "$nazwa $(git -C "$repo" rev-parse --short HEAD 2>/dev/null || echo brak-HEAD) $(git -C "$repo" branch --show-current 2>/dev/null)" >> "$ROB/repo"
  if ! git -C "$repo" status --porcelain=v1 -z --untracked-files=all > "$ROB/status" 2>/dev/null; then
    log "OSTRZEŻENIE: git status nieudany w jednym repozytorium"
    uwagi=$((uwagi + 1))
    continue
  fi
  while IFS= read -r -d '' wpis; do
    stan="${wpis:0:2}"
    p="${wpis:3}"
    case "$stan" in R*|C*) IFS= read -r -d '' _stara || true ;; esac
    if [ -L "$repo/$p" ] || [ -f "$repo/$p" ]; then
      printf '%s\0' "projekty/$nazwa/$p" >> "$LISTA"
      n_proj=$((n_proj + 1))
    fi
  done < "$ROB/status"
  # Commity bez kopii na zdalnym repozytorium; pusty pakiet (wszystko wypchnięte) git odrzuca, wtedy nic nie dodajemy.
  if git -C "$repo" bundle create "$ROB/git/$nazwa.bundle" --branches --not --remotes >/dev/null 2>&1; then
    n_bundle=$((n_bundle + 1))
  else
    rm -f "$ROB/git/$nazwa.bundle"
  fi
done

{
  echo "Kopia serwera: $(date '+%F %T %z'), $(hostname)"
  echo "Pliki z folderów: $n_dane; spójne kopie baz SQLite (sqlite/): $n_baz"
  echo "Pliki zmienione w projektach: $n_proj; pakiety niewypchniętych commitów (git/): $n_bundle"
  echo "Przywracanie: tar -xzf $DZIS.tar.gz; bazy z sqlite/<ścieżka> zastępują pliki pod <ścieżka>;"
  echo "commity: git -C <repo> fetch git/<repo>.bundle 'refs/heads/*:refs/remotes/kopia/*'"
  echo
  echo "Repozytoria (nazwa, HEAD, gałąź):"
  cat "$ROB/repo" 2>/dev/null
} > "$ROB/kopia-info.txt"

# 3. Archiwum: najpierw pliki z listy (względem BAZA), potem dopisane kopie baz, pakiety i opis.
TAR_GNU=()
if tar --version 2>/dev/null | grep -q GNU; then
  TAR_GNU=(--ignore-failed-read --warning=no-file-changed --verbatim-files-from)
fi
TMP_TAR="$KOPIE/.$DZIS.tar.tmp"
tar -cf "$TMP_TAR" ${TAR_GNU[@]+"${TAR_GNU[@]}"} -C "$BAZA" --null -T "$LISTA"
kod=$?
# GNU tar: 1 = plik zmienił się w trakcie czytania (np. dziennik uruchomienia); to nie jest błąd kopii.
[ "$kod" -le 1 ] || blad "tar zwrócił $kod"
dopisz=(kopia-info.txt)
[ -d "$ROB/sqlite" ] && dopisz+=(sqlite)
[ -n "$(ls -A "$ROB/git" 2>/dev/null)" ] && dopisz+=(git)
tar -rf "$TMP_TAR" -C "$ROB" "${dopisz[@]}" || blad "dopisanie do archiwum"
gzip -6 -c "$TMP_TAR" > "$KOPIE/.$DZIS.tar.gz.tmp" || blad "kompresja (miejsce na dysku?)"
rm -f "$TMP_TAR"
gzip -t "$KOPIE/.$DZIS.tar.gz.tmp" || blad "archiwum uszkodzone"
mv -f "$KOPIE/.$DZIS.tar.gz.tmp" "$KOPIE/$DZIS.tar.gz" || blad "zapis archiwum"
ARCH="$KOPIE/$DZIS.tar.gz"
log "zapisano $ARCH ($(du -h "$ARCH" | cut -f1); pliki $n_dane + $n_proj, bazy $n_baz, pakiety $n_bundle)"

# 4. Rotacja: zostaje $ZOSTAW najnowszych archiwów (nazwy RRRR-MM-DD sortują się według daty).
archiwa=()
for a in "$KOPIE"/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].tar.gz; do
  [ -f "$a" ] && archiwa+=("$a")
done
usun=$(( ${#archiwa[@]} - ZOSTAW ))
i=0
while [ "$i" -lt "$usun" ]; do
  rm -f "${archiwa[$i]}" && log "usunięto starą kopię ${archiwa[$i]##*/}"
  i=$((i + 1))
done

# Stan ostatniej kopii dla panelu i kontroli zdrowia. offAt: ostatnia udana wysyłka poza serwer (także z wcześniejszych dni).
ROZMIAR="$(stat -c %s "$ARCH" 2>/dev/null || stat -f %z "$ARCH")"
PLIKI=$((n_dane + n_proj + n_baz + n_bundle + 1))
zapisz_stan() {  # off (true|false)
  python3 - "$KOPIE/ostatnia.json" "$KOPIE/.ostatnia.json.tmp" "$ROZMIAR" "$PLIKI" "$1" <<'PY' || log "OSTRZEŻENIE: nie zapisano ostatnia.json"
import datetime, json, os, sys
cel, tmp, rozmiar, pliki, off = sys.argv[1:6]
teraz = datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(timespec="seconds")
off_at = None
try:
    with open(cel, encoding="utf-8") as f:
        off_at = json.load(f).get("offAt")
except (OSError, ValueError, AttributeError):
    pass
if off == "true":
    off_at = teraz
stan = {"at": teraz, "size": int(rozmiar), "files": int(pliki), "off": off == "true", "offAt": off_at}
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(stan, f)
    f.write("\n")
os.replace(tmp, cel)
PY
}
zapisz_stan false

# 5. Wysyłka poza serwer, tylko gdy ustawiono KOPIA_CEL. Najpierw szyfrowanie, gdy ustawione.
plik_prywatny() {  # plik opis: istnieje, czytelny, bez praw dla grupy i innych
  [ -r "$1" ] || blad "$2 nie istnieje albo brak dostępu"
  prawa="$(stat -c %a "$1" 2>/dev/null || stat -f %Lp "$1")"
  case "$prawa" in 600|400) ;; *) blad "$2 ma prawa $prawa (wymagane 600: chmod 600, właściciel panel)" ;; esac
}
cel="${KOPIA_CEL:-}"
WYSLIJ="$ARCH"
if [ -n "$cel" ]; then
  if [ -n "${KOPIA_AGE_ODBIORCY:-}" ]; then
    command -v age >/dev/null || blad "KOPIA_AGE_ODBIORCY ustawione, a age nie jest zainstalowany"
    [ -r "$KOPIA_AGE_ODBIORCY" ] || blad "plik KOPIA_AGE_ODBIORCY nie istnieje"
    SZYFR="$(mktemp -d "$KOPIE/.szyfr.XXXXXX")" || blad "brak folderu roboczego"
    WYSLIJ="$SZYFR/$DZIS.tar.gz.age"
    age -e -R "$KOPIA_AGE_ODBIORCY" -o "$WYSLIJ" "$ARCH" || blad "szyfrowanie age"
    log "zaszyfrowano (age)"
  elif [ -n "${KOPIA_HASLO_PLIK:-}" ]; then
    command -v gpg >/dev/null || blad "KOPIA_HASLO_PLIK ustawione, a gpg nie jest zainstalowany"
    plik_prywatny "$KOPIA_HASLO_PLIK" "plik KOPIA_HASLO_PLIK"
    SZYFR="$(mktemp -d "$KOPIE/.szyfr.XXXXXX")" || blad "brak folderu roboczego"
    WYSLIJ="$SZYFR/$DZIS.tar.gz.gpg"
    GNUPGHOME="$SZYFR/gnupg" && mkdir -m 700 "$GNUPGHOME" && export GNUPGHOME
    gpg --batch --quiet --yes --pinentry-mode loopback --passphrase-file "$KOPIA_HASLO_PLIK" \
        --symmetric --cipher-algo AES256 --compress-algo none -o "$WYSLIJ" "$ARCH" || blad "szyfrowanie gpg"
    log "zaszyfrowano (gpg AES256)"
  else
    case "$cel" in
      scp:*) blad "KOPIA_CEL=scp bez szyfrowania (ustaw KOPIA_HASLO_PLIK albo KOPIA_AGE_ODBIORCY)" ;;
      rclone:*) log "bez szyfrowania skryptem: zdalny rclone powinien być typu crypt" ;;
    esac
  fi
fi
case "$cel" in
  "") log "KOPIA_CEL nieustawiony, kopia tylko na serwerze" ;;
  rclone:*)
    command -v rclone >/dev/null || blad "KOPIA_CEL wskazuje rclone, a rclone nie jest zainstalowany"
    rclone copy -q "$WYSLIJ" "${cel#rclone:}" || blad "wysyłka rclone"
    log "wysłano poza serwer (rclone)"
    dni="${KOPIA_CEL_DNI:-30}"
    if [ "$dni" -gt 0 ] 2>/dev/null; then
      rclone delete -q --min-age "${dni}d" --include '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].tar.gz*' "${cel#rclone:}" \
        || { log "OSTRZEŻENIE: usuwanie starych kopii w celu nieudane"; uwagi=$((uwagi + 1)); }
    fi
    zapisz_stan true ;;
  scp:*)
    scp -q -o BatchMode=yes -o ConnectTimeout=20 "$WYSLIJ" "${cel#scp:}" || blad "wysyłka scp"
    log "wysłano poza serwer (scp)"
    zapisz_stan true ;;
  *) blad "KOPIA_CEL ma nieznany format (oczekiwane rclone:... albo scp:...)" ;;
esac

if [ "$uwagi" -gt 0 ]; then
  log "kopia zrobiona z uwagami: $uwagi"
  ntfy "Serwer: kopia z $DZIS zrobiona z uwagami ($uwagi). Szczegóły: journalctl -u kopia"
fi
exit 0
