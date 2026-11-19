#!/bin/bash
# Odtworzenie danych serwera z archiwum nocnej kopii (kopia.sh). Opis całej procedury: ksiega/MIGRACJA.md,
# sekcja „Odtworzenie serwera”.
#
#   odtworz.sh --sprawdz ARCHIWUM            weryfikacja archiwum i lista zawartości, nic nie rozpakowuje
#   odtworz.sh ARCHIWUM KATALOG              weryfikacja, rozpakowanie do pustego KATALOGU, kroki ręczne na końcu
#
# ARCHIWUM: RRRR-MM-DD.tar.gz, RRRR-MM-DD.tar.gz.gpg (hasło z --haslo-plik PLIK albo KOPIA_HASLO_PLIK,
# bez nich gpg pyta o hasło) albo RRRR-MM-DD.tar.gz.age (klucz prywatny z --klucz PLIK albo KOPIA_AGE_KLUCZ).
# Skrypt niczego nie nadpisuje poza KATALOGIEM: dane do /home/panel przenosi właściciel według kroków na końcu.
# Wynik udanej próby (sprawdzenie i rozpakowanie osobno) zapisuje w /home/panel/kopie/proba-odtworzenia.json
# (KOPIA_PROBA_STAN), gdy katalog istnieje i jest zapisywalny: {"check": {...}, "unpack": {...}}, każde z polami
# "at", "archive", "encrypted" (archiwum .gpg albo .age, czyli kopia poza serwerem), "seconds".
# Czyta go raport zainstaluj-uzytkownika-agenta.sh --sprawdz (warunki sprzedaży PC).
set -u
umask 077
log() { echo "odtworz: $*"; }
blad() { echo "odtworz: BŁĄD: $*" >&2; exit 1; }
uzycie() { sed -n '5,6p' "$0" | sed 's/^# *//'; exit 2; }

SPRAWDZ=0; HASLO="${KOPIA_HASLO_PLIK:-}"; KLUCZ="${KOPIA_AGE_KLUCZ:-}"; ARGS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --sprawdz) SPRAWDZ=1 ;;
    --haslo-plik) [ $# -ge 2 ] || uzycie; HASLO="$2"; shift ;;
    --klucz) [ $# -ge 2 ] || uzycie; KLUCZ="$2"; shift ;;
    -h|--help) uzycie ;;
    -*) blad "nieznana opcja $1" ;;
    *) ARGS+=("$1") ;;
  esac
  shift
done
[ "${#ARGS[@]}" -ge 1 ] || uzycie
ARCH="${ARGS[0]}"
CEL="${ARGS[1]:-}"
[ "$SPRAWDZ" -eq 1 ] || [ -n "$CEL" ] || uzycie
[ -f "$ARCH" ] || blad "nie ma pliku $ARCH"
if [ "$SPRAWDZ" -eq 0 ] && [ -e "$CEL" ] && [ -n "$(ls -A "$CEL" 2>/dev/null)" ]; then
  blad "$CEL nie jest pusty; wskaż nowy katalog"
fi

PROBA_STAN="${KOPIA_PROBA_STAN:-/home/panel/kopie/proba-odtworzenia.json}"

zapisz_probe() {  # check|unpack: wynik próby dla raportu warunków sprzedaży PC; błąd zapisu nie przerywa
  local d szyfr=false
  d="$(dirname "$PROBA_STAN")"
  [ -d "$d" ] && [ -w "$d" ] && command -v python3 >/dev/null || return 0
  case "$ARCH" in *.gpg|*.age) szyfr=true ;; esac
  python3 - "$PROBA_STAN" "$1" "${ARCH##*/}" "$szyfr" "$((SECONDS - START))" <<'PY' || log "OSTRZEŻENIE: nie zapisano $PROBA_STAN"
import datetime, json, os, sys
cel, tryb, arch, szyfr, sek = sys.argv[1:6]
try:
    with open(cel, encoding="utf-8") as f:
        d = json.load(f)
    if not isinstance(d, dict):
        d = {}
except (OSError, ValueError):
    d = {}
teraz = datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(timespec="seconds")
d[tryb] = {"at": teraz, "archive": arch, "encrypted": szyfr == "true", "seconds": int(sek)}
tmp = cel + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(d, f)
    f.write("\n")
os.replace(tmp, cel)
PY
}

ROB="$(mktemp -d "${TMPDIR:-/tmp}/odtworz.XXXXXX")" || blad "brak folderu roboczego"
trap 'rm -rf "$ROB"' EXIT
START=$SECONDS

# 1. Odszyfrowanie (gdy trzeba) do folderu roboczego.
TGZ="$ARCH"
case "$ARCH" in
  *.gpg)
    command -v gpg >/dev/null || blad "brak gpg (sudo apt install gnupg)"
    TGZ="$ROB/kopia.tar.gz"
    export GNUPGHOME="$ROB/gnupg"; mkdir -m 700 "$GNUPGHOME"
    if [ -n "$HASLO" ]; then
      gpg --batch --quiet --pinentry-mode loopback --passphrase-file "$HASLO" -o "$TGZ" -d "$ARCH" \
        || blad "odszyfrowanie gpg nieudane (złe hasło albo uszkodzony plik)"
    else
      gpg --quiet --pinentry-mode loopback -o "$TGZ" -d "$ARCH" \
        || blad "odszyfrowanie gpg nieudane (złe hasło albo uszkodzony plik)"
    fi
    log "odszyfrowano (gpg)" ;;
  *.age)
    command -v age >/dev/null || blad "brak age (sudo apt install age)"
    [ -n "$KLUCZ" ] || blad "podaj klucz prywatny age: --klucz PLIK"
    TGZ="$ROB/kopia.tar.gz"
    age -d -i "$KLUCZ" -o "$TGZ" "$ARCH" || blad "odszyfrowanie age nieudane"
    log "odszyfrowano (age)" ;;
esac

# 2. Weryfikacja: gzip, lista tar, bezpieczne ścieżki, opis kopii.
gzip -t "$TGZ" 2>/dev/null || blad "archiwum uszkodzone (gzip -t)"
tar -tzf "$TGZ" > "$ROB/lista" 2>/dev/null || blad "archiwum uszkodzone (tar -t)"
if grep -E -q '^/|(^|/)\.\.(/|$)' "$ROB/lista"; then
  blad "archiwum zawiera ścieżki bezwzględne albo '..'; nie rozpakowuję"
fi
grep -q -x 'kopia-info.txt' "$ROB/lista" || blad "brak kopia-info.txt: to nie jest archiwum z kopia.sh"
tar -xzf "$TGZ" -O kopia-info.txt > "$ROB/info" 2>/dev/null || blad "nie można odczytać kopia-info.txt"

wpisy=$(grep -c -v '/$' "$ROB/lista")
rozmiar="$(du -h "$ARCH" | cut -f1)"
echo
cat "$ROB/info"
echo
echo "Archiwum: ${ARCH##*/}, $rozmiar, wpisów (bez folderów): $wpisy"
echo "Wpisy według folderu:"
grep -v '/$' "$ROB/lista" | awk -F/ '{ k = (NF > 2) ? $1 "/" $2 : $1; n[k]++ } END { for (k in n) printf "  %6d  %s\n", n[k], k }' | sort -k2

if [ "$SPRAWDZ" -eq 1 ]; then
  echo
  echo "Zawartość:"
  grep -v '/$' "$ROB/lista" | sed 's/^/  /'
  echo
  log "archiwum poprawne (sprawdzenie trwało $((SECONDS - START)) s)"
  zapisz_probe check
  exit 0
fi

# 3. Rozpakowanie do pustego katalogu.
mkdir -p "$CEL" || blad "nie można utworzyć $CEL"
tar -xzf "$TGZ" --no-same-owner -C "$CEL" || blad "rozpakowanie nieudane"

# Spójne kopie baz z sqlite/<ścieżka> na miejsce <ścieżka> (w rozpakowanym katalogu, nie w /home/panel).
n_baz=0
if [ -d "$CEL/sqlite" ]; then
  while IFS= read -r -d '' b; do
    p="${b#"$CEL"/sqlite/}"
    mkdir -p "$CEL/$(dirname "$p")"
    cp -p "$b" "$CEL/$p" && rm -f "$CEL/$p-wal" "$CEL/$p-shm" "$CEL/$p-journal" && n_baz=$((n_baz + 1))
  done < <(find "$CEL/sqlite" -type f -print0)
fi
log "rozpakowano do $CEL; bazy SQLite na miejscu: $n_baz"
log "czas: $((SECONDS - START)) s (wpisz w ksiega/MIGRACJA.md po próbie)"
zapisz_probe check
zapisz_probe unpack

cat <<EOF

Kroki ręczne (jako ops, kolejno; szczegóły: ksiega/MIGRACJA.md, „Odtworzenie serwera”):
 1. Zatrzymaj usługi:            sudo systemctl stop panel useme kopia.timer zdrowie.timer zapis-kart.timer
 2. Dane asystentów:             sudo rsync -a $CEL/dane/ /home/panel/dane/
 3. Uruchomienia i historia:     sudo rsync -a $CEL/IntegrateSystems/ /home/panel/IntegrateSystems/
 4. Repozytoria projektów:       najpierw git clone do /home/panel/projekty/<repo> (jako panel), potem
                                 sudo rsync -a $CEL/projekty/ /home/panel/projekty/  (zmiany sprzed kopii)
 5. Niewypchnięte commity:       sudo -u panel git -C /home/panel/projekty/<repo> fetch $CEL/git/<repo>.bundle 'refs/heads/*:refs/remotes/kopia/*'
 6. Właściciel plików:           sudo chown -R panel:panel /home/panel/dane /home/panel/projekty /home/panel/IntegrateSystems
 7. Uruchom usługi:              sudo systemctl start panel useme; sudo systemctl start kopia.timer zdrowie.timer zapis-kart.timer
 8. Sprawdź:                     sudo -u panel zdrowie  (wszystkie stany ok), panel w przeglądarce
 9. Usuń rozpakowany katalog:    rm -rf $CEL  (zawiera dane klientów)
EOF
