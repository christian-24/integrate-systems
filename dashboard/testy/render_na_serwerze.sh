#!/bin/sh
# Test studia filmów z renderowaniem (ffmpeg) na serwerze: kopia dashboard/, standard/ i studiów kart do /tmp,
# python3 -m unittest test_studio test_studio_r2 test_studio_r3, sprzątanie. Pliki panelu na serwerze i usługi zostają nietknięte.
# Użycie: testy/render_na_serwerze.sh panel@<adres serwera>   (albo PANEL_SERWER=panel@<adres>)
set -e
HOST=${1:-${PANEL_SERWER:?podaj serwer: render_na_serwerze.sh panel@adres}}
DIR=/tmp/film-test-$$
cd "$(dirname "$0")/../.."
COPYFILE_DISABLE=1 tar cf - --exclude=__pycache__ --exclude='._*' dashboard standard szkice/*/studio \
    szkice/generator-opisow-mebli/posty/2026-11-20-film-a-opis-pl-de/scenariusz.json |
  ssh -o BatchMode=yes "$HOST" "mkdir -p $DIR && tar xf - -C $DIR 2>/dev/null; cd $DIR/dashboard/testy && \
    python3 -m unittest -v test_studio test_studio_r2 test_studio_r3 > $DIR/wynik.txt 2>&1; s=\$?; tail -n 15 $DIR/wynik.txt; rm -rf $DIR; exit \$s"
