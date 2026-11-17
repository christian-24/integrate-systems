#!/bin/bash
# Zapis zmian w IntegrateSystems (karty, zadania, raporty) do GitHuba. Uruchamiany co 15 min przez timer zapis-kart.
set -u
cd /home/panel/IntegrateSystems || exit 1
log() { echo "zapis-kart: $*"; }
if ! git pull -q --rebase --autostash; then
  git rebase --abort 2>/dev/null
  log "BŁĄD: konflikt przy pobieraniu z GitHuba; zmiany zostają na serwerze, potrzebna decyzja właściciela"
  exit 1
fi
if [ -n "$(git status --porcelain)" ]; then
  git add -A
  git -c user.name="Serwer integrate" -c user.email="serwer@integrate.local" \
      commit -q -m "Panel: zmiany z serwera $(date '+%Y-%m-%d %H:%M')"
fi
if [ -n "$(git log --oneline '@{u}..HEAD' 2>/dev/null)" ]; then
  if git push -q; then log "wypchnięto $(git log -1 --format=%h)"; else log "BŁĄD: push nieudany"; exit 1; fi
fi
