#!/bin/bash
# Osobny użytkownik systemu „agent” dla uruchomień agentów z panelu (PANEL_AGENT_USER, dashboard/AGENCI.md).
# Uruchamia właściciel (jako ops):
#   sudo bash /home/panel/IntegrateSystems/uruchom/serwer/zainstaluj-uzytkownika-agenta.sh             instalacja i raport
#   sudo bash /home/panel/IntegrateSystems/uruchom/serwer/zainstaluj-uzytkownika-agenta.sh --sprawdz   sam raport, bez zmian
# Instalacja przerywa, gdy uruchom/serwer różni się od origin/main (instalacja-wspolne.sh). Każdy krok można powtórzyć.
#  1. grupa projekty (panel, agent); użytkownik agent: bez sudo, hasło zablokowane, DenyUsers w sshd, dom 711
#  2. /home/panel/projekty/*, IntegrateSystems/szkice i IntegrateSystems/raporty: grupa projekty, setgid na katalogach,
#     ACL rwX dla grupy projekty i panelu (także domyślne, dla nowych plików)
#  3. każde repozytorium w projekty/: core.sharedRepository=group, .agent/ w .git/info/exclude; sam katalog .git,
#     pliki w nim (config, HEAD, index, packed-refs), hooks/ i info/ zapisuje tylko panel; objects/, refs/, logs/,
#     worktrees/ wspólne z agentem
#  4. agent przechodzi przez /home/panel (ACL --x), pozostałe wpisy domu panelu (.ssh, .claude, kopie, .config, dane…)
#     bez praw dla innych; /etc/integrate root:panel 750
#  5. /etc/sudoers.d/90-panel-agent: panel uruchamia jako agent tylko /home/agent/.local/bin/claude (visudo -c)
#  6. Claude Code dla agenta (oficjalny instalator), git safe.directory dla agenta
#  7. /etc/integrate/panel.env: PANEL_AGENT_USER, PANEL_CLAUDE, PANEL_LOKALNY_KLUCZ_PLIK; klucz root:panel 640
#  8. nowa wersja zdrowie (gdy zainstalowana), restart panelu, raport
# Logowanie Claude agenta: panel, przycisk „Zaloguj” (po restarcie panel uruchamia claude jako agent).
# Opis: ksiega/MIGRACJA.md, sekcja „Użytkownik agenta”.
set -u
TU="$(cd "$(dirname "$0")" && pwd)"
SKRYPT="$TU/$(basename "$0")"
cd / || exit 1      # runuser i git jako panel/agent: katalog bieżący dostępny dla każdego

SPRAWDZ=0
case "${1:-}" in
  "") ;;
  --sprawdz) SPRAWDZ=1 ;;
  -h|--help) sed -n '3,5p' "$0" | sed 's/^# *//'; exit 0 ;;
  *) echo "Nieznana opcja: $1 (dozwolona: --sprawdz)" >&2; exit 2 ;;
esac

AGENT=agent
GRUPA=projekty
PANEL=panel
PANEL_DOM=/home/panel
PROJEKTY=$PANEL_DOM/projekty
IS=$PANEL_DOM/IntegrateSystems
WSPOLNE_IS="szkice raporty"                      # katalogi IntegrateSystems z zapisem dla agenta
AGENT_DOM=/home/$AGENT
AGENT_CLAUDE=$AGENT_DOM/.local/bin/claude
SUDOERS=/etc/sudoers.d/90-panel-agent
SSHD_DROP=/etc/ssh/sshd_config.d/90-agent.conf
ETC=/etc/integrate
ENV_PLIK=$ETC/panel.env
KLUCZ=$ETC/lokalny.klucz
ACL_WSPOLNE="g:$GRUPA:rwX,u:$PANEL:rwX,d:g:$GRUPA:rwX,d:u:$PANEL:rwX,d:o::---"
# Ścieżki, do których agent nie może mieć dostępu (sprawdzane w raporcie, gdy istnieją).
ZAKAZANE="$PANEL_DOM/.ssh $PANEL_DOM/.claude $PANEL_DOM/.claude.json $PANEL_DOM/kopie $PANEL_DOM/.kopia-haslo
$PANEL_DOM/.config $PANEL_DOM/dane $ETC $ENV_PLIK $ETC/serwer.env $KLUCZ $IS/dashboard/panel.env"

przerwij() { echo "Przerwano: $*" >&2; exit 1; }
log() { echo "$*"; }
uwaga() { echo "UWAGA: $*" >&2; }

[ "$(id -u)" -eq 0 ] || przerwij "uruchom przez sudo."
id "$PANEL" >/dev/null 2>&1 || przerwij "brak użytkownika $PANEL."

# ---------------------------------------------------------------- instalacja
panel_git() { runuser -u "$PANEL" -- git "$@"; }

wspolny_katalog() {  # katalog [-R]: grupa projekty, setgid na katalogach, ACL dla grupy i panelu
  local d="$1"
  [ -d "$d" ] || return 0
  chgrp -R "$GRUPA" "$d"
  find "$d" -type d -exec chmod g+s {} +
  setfacl -R -m "$ACL_WSPOLNE" "$d"
}

tylko_panel() {  # ścieżka: bez ACL, grupa panel, bez zapisu dla grupy i innych (rekurencyjnie)
  local p="$1"
  [ -e "$p" ] || return 0
  setfacl -R -b "$p"
  chgrp -R "$PANEL" "$p"
  chmod -R go-w "$p"
  if [ -d "$p" ]; then find "$p" -type d -exec chmod g-s {} +; fi
}

zabezpiecz_repo() {  # repozytorium projektu (po wspolny_katalog na projekty/)
  local r="$1" g="$1/.git" d f
  panel_git -C "$r" config core.sharedRepository group || uwaga "$r: git config nieudany"
  mkdir -p "$g/info"
  grep -qxF '.agent/' "$g/info/exclude" 2>/dev/null || echo '.agent/' >> "$g/info/exclude"
  chown "$PANEL" "$g/info" "$g/info/exclude"
  # Katalogi wspólne: agent tworzy obiekty, gałęzie agent/… i pliki swojego worktree.
  for d in objects refs refs/heads logs logs/refs logs/refs/heads worktrees; do
    if [ ! -d "$g/$d" ]; then install -d -o "$PANEL" -g "$GRUPA" -m 2775 "$g/$d"; fi
    chgrp "$GRUPA" "$g/$d"; chmod g+ws "$g/$d"
    setfacl -m "$ACL_WSPOLNE" "$g/$d"
  done
  # Tylko panel: sam .git (agent nie dopisze tam commondir, config ani innych plików), pliki w nim, hooks/, info/.
  setfacl -b "$g"
  chgrp "$PANEL" "$g"
  chmod 755 "$g"; chmod g-s "$g"
  for f in "$g"/* "$g"/.[!.]*; do
    if [ -f "$f" ] && [ ! -L "$f" ]; then setfacl -b "$f"; chgrp "$PANEL" "$f"; chmod go-w "$f"; fi
  done
  tylko_panel "$g/hooks"
  tylko_panel "$g/info"
}

instaluj() {
  local zmiana_env=0 zmiana_grup=0 u g e

  # 1. Grupa i użytkownik.
  getent group "$GRUPA" >/dev/null || { groupadd --system "$GRUPA" && log "Utworzono grupę $GRUPA."; }
  if ! id "$AGENT" >/dev/null 2>&1; then
    useradd --create-home --home-dir "$AGENT_DOM" --shell /bin/bash --user-group --comment "Agenci panelu" "$AGENT" \
      || przerwij "useradd $AGENT nieudany."
    log "Utworzono użytkownika $AGENT."
  fi
  [ "$(passwd -S "$AGENT" 2>/dev/null | awk '{print $2}')" = L ] || passwd -l "$AGENT" >/dev/null
  for g in sudo admin wheel adm lxd docker; do
    if id -nG "$AGENT" | tr ' ' '\n' | grep -qx "$g"; then gpasswd -d "$AGENT" "$g" >/dev/null && log "Usunięto $AGENT z grupy $g."; fi
  done
  for u in "$AGENT" "$PANEL"; do
    if ! id -nG "$u" | tr ' ' '\n' | grep -qx "$GRUPA"; then
      usermod -aG "$GRUPA" "$u" && log "Dodano $u do grupy $GRUPA."
      [ "$u" = "$PANEL" ] && zmiana_grup=1
    fi
  done
  chmod 711 "$AGENT_DOM"     # panel sprawdza istnienie $AGENT_CLAUDE; listy plików agenta nie widzi

  # SSH: agent nie loguje się (nie ma też hasła ani kluczy; to zabezpieczenie na wypadek, gdyby dopisał sobie klucz).
  if [ -d /etc/ssh/sshd_config.d ] && ! grep -qs "^DenyUsers.*[[:space:]]$AGENT\([[:space:]]\|\$\)" "$SSHD_DROP"; then
    printf '# Zakaz logowania SSH dla użytkownika agentów panelu (zainstaluj-uzytkownika-agenta.sh).\nDenyUsers %s\n' \
      "$AGENT" > "$SSHD_DROP"
    chmod 644 "$SSHD_DROP"
    install -d -m 755 /run/sshd
    if sshd -t; then
      systemctl reload ssh 2>/dev/null || systemctl reload sshd 2>/dev/null || true
      log "Dopisano DenyUsers $AGENT ($SSHD_DROP)."
    else
      rm -f "$SSHD_DROP"; uwaga "sshd -t nieudane, $SSHD_DROP wycofany."
    fi
  fi

  # 2–4. Prawa do plików.
  if ! command -v setfacl >/dev/null; then
    log "Instaluję pakiet acl..."
    apt-get install -y -q acl >/dev/null || przerwij "brak setfacl (sudo apt install acl)."
  fi
  if [ -d "$PROJEKTY" ]; then
    log "Prawa w $PROJEKTY (może potrwać przy dużych repozytoriach)..."
    wspolny_katalog "$PROJEKTY"
    for r in "$PROJEKTY"/*/; do
      r="${r%/}"
      if [ -d "$r/.git" ] && [ ! -L "$r" ]; then zabezpiecz_repo "$r"; fi
    done
  else
    uwaga "brak $PROJEKTY."
  fi
  for e in $WSPOLNE_IS; do
    if [ ! -d "$IS/$e" ]; then install -d -o "$PANEL" -g "$GRUPA" -m 2775 "$IS/$e"; fi
    wspolny_katalog "$IS/$e"
  done
  setfacl -m "g:$GRUPA:--x" "$PANEL_DOM"
  setfacl -m "g:$GRUPA:r-x" "$IS"
  # Dom panelu: poza projekty/ i IntegrateSystems/ nic dla innych (agent ma tylko przejście przez /home/panel).
  u="$(systemctl show -p User --value useme.service 2>/dev/null || true)"
  if [ -n "$u" ] && [ "$u" != "$PANEL" ]; then
    uwaga "useme.service działa jako $u, nie $PANEL: prawa wpisów w $PANEL_DOM bez zmian (sprawdź ręcznie)."
  else
    find "$PANEL_DOM" -mindepth 1 -maxdepth 1 ! -type l ! -name projekty ! -name IntegrateSystems \
      -perm /o=rwx -exec chmod o-rwx {} +
  fi
  if [ -f "$IS/dashboard/panel.env" ]; then chmod o-rwx "$IS/dashboard/panel.env"; fi
  install -d -o root -g "$PANEL" -m 750 "$ETC"
  chown root:"$PANEL" "$ETC"; chmod 750 "$ETC"

  # 5. sudoers: tylko ta jedna ścieżka. Środowisko: sudo je czyści (env_reset), HOME=/home/agent; panel nie przekazuje
  # zmiennych, więc SETENV nie jest potrzebne.
  local tmp
  tmp="$(mktemp)"
  cat > "$tmp" <<EOF
# Panel (użytkownik $PANEL) uruchamia agentów jako $AGENT, tylko Claude Code z domu agenta, bez hasła.
# Plik instaluje uruchom/serwer/zainstaluj-uzytkownika-agenta.sh; zmiany tylko tam.
Defaults:$PANEL !lecture
$PANEL ALL=($AGENT) NOPASSWD: $AGENT_CLAUDE
EOF
  chmod 440 "$tmp"
  if visudo -c -q -f "$tmp" >/dev/null; then
    if ! cmp -s "$tmp" "$SUDOERS"; then
      install -o root -g root -m 440 "$tmp" "$SUDOERS" && log "Zapisano $SUDOERS."
    fi
  else
    rm -f "$tmp"; przerwij "reguła sudoers nie przeszła visudo -c; nic nie zapisano."
  fi
  rm -f "$tmp"
  visudo -c -q >/dev/null || { rm -f "$SUDOERS"; przerwij "visudo -c dla całej konfiguracji nieudane; $SUDOERS usunięty."; }

  # 6. Claude Code dla agenta i git.
  if [ ! -x "$AGENT_CLAUDE" ]; then
    command -v curl >/dev/null || przerwij "brak curl (sudo apt install curl)."
    log "Instaluję Claude Code dla $AGENT (oficjalny instalator)..."
    runuser -u "$AGENT" -- bash -c 'cd ~ && curl -fsSL https://claude.ai/install.sh | bash' \
      || przerwij "instalacja Claude Code dla $AGENT nieudana."
    [ -x "$AGENT_CLAUDE" ] || przerwij "po instalacji nie ma $AGENT_CLAUDE."
  fi
  # Panel (agents.py) sprawdza, czy PANEL_CLAUDE istnieje: przejście (samo x) do pliku i jego celu, bez listy plików.
  for d in .local .local/bin .local/share .local/share/claude .local/share/claude/versions; do
    if [ -d "$AGENT_DOM/$d" ]; then chmod o+x "$AGENT_DOM/$d"; fi
  done
  chmod o+rx "$(readlink -f "$AGENT_CLAUDE")" 2>/dev/null || true
  # Worktree zakłada panel (właściciel katalogu: panel), więc git agenta musi je uznać. Git 2.43 (Ubuntu 24.04) nie ma
  # wzorców ścieżek w safe.directory, a katalogi .agent/<runId> są nowe przy każdym uruchomieniu: stąd „*”.
  # Agent ma zapis tylko w repozytoriach panelu, więc „*” nie otwiera mu cudzych repozytoriów.
  if ! runuser -u "$AGENT" -- git config --global --get-all safe.directory 2>/dev/null | grep -qxF '*'; then
    runuser -u "$AGENT" -- git config --global --add safe.directory '*'
  fi
  if ! runuser -u "$AGENT" -- git config --global user.email >/dev/null 2>&1; then
    runuser -u "$AGENT" -- git config --global user.name "Agent panelu"
    runuser -u "$AGENT" -- git config --global user.email "agent@localhost"
  fi

  # 7. Klucz lokalny i panel.env.
  if [ ! -s "$KLUCZ" ]; then
    ( umask 077; openssl rand -hex 32 > "$KLUCZ" ) || przerwij "nie udało się wygenerować $KLUCZ."
    log "Wygenerowano $KLUCZ."
  fi
  chown root:"$PANEL" "$KLUCZ"; chmod 640 "$KLUCZ"
  [ -f "$ENV_PLIK" ] || przerwij "brak $ENV_PLIK (panel nie jest zainstalowany według MIGRACJA.md)."
  ustaw_env() {  # NAZWA wartość: dopisuje albo zamienia wiersz
    if grep -qx "$1=$2" "$ENV_PLIK"; then return 0; fi
    [ -f "$ENV_PLIK.przed-agentem" ] || cp -p "$ENV_PLIK" "$ENV_PLIK.przed-agentem"
    if grep -q "^$1=" "$ENV_PLIK"; then
      sed -i "s|^$1=.*|$1=$2|" "$ENV_PLIK"
    else
      printf '%s=%s\n' "$1" "$2" >> "$ENV_PLIK"
    fi
    log "panel.env: $1=$2"
    zmiana_env=1
  }
  ustaw_env PANEL_AGENT_USER "$AGENT"
  ustaw_env PANEL_CLAUDE "$AGENT_CLAUDE"      # reguła sudoers dopuszcza tylko tę ścieżkę
  ustaw_env PANEL_LOKALNY_KLUCZ_PLIK "$KLUCZ"
  chown root:root "$ENV_PLIK"; chmod 600 "$ENV_PLIK"

  # 8. Kontrola zdrowia w nowej wersji (sprawdza logowanie agenta) i restart panelu.
  if [ -x /usr/local/bin/zdrowie ] && [ -f "$LIB/zdrowie.sh" ] && ! cmp -s "$LIB/zdrowie.sh" /usr/local/bin/zdrowie; then
    install -m 755 "$LIB/zdrowie.sh" /usr/local/bin/zdrowie && log "Zaktualizowano /usr/local/bin/zdrowie."
  fi
  local pid
  pid="$(systemctl show -p MainPID --value panel.service 2>/dev/null)"
  if [ "$zmiana_env" -eq 1 ] || [ "$zmiana_grup" -eq 1 ] || ! panel_ma_grupe "$pid"; then
    if grep -qs '"state": *"running"' "$IS"/uruchomienia/2*.json; then
      uwaga "trwa uruchomienie agenta; restart panelu je zatrzyma (stan stopped)."
    fi
    systemctl restart panel.service && log "Panel uruchomiony ponownie." || uwaga "restart panelu nieudany (journalctl -u panel)."
    sleep 2
  fi
}

panel_ma_grupe() {  # pid: proces panelu ma grupę projekty
  local gid
  gid="$(getent group "$GRUPA" | cut -d: -f3)"
  [ -n "${1:-}" ] && [ "$1" != 0 ] && [ -n "$gid" ] \
    && awk '/^Groups:/' "/proc/$1/status" 2>/dev/null | tr ' \t' '\n\n' | grep -qx "$gid"
}

# ---------------------------------------------------------------- raport
PROBLEMY=0
ok() { printf '  ok    %s\n' "$*"; }
zle() { printf '  BRAK  %s\n' "$*"; PROBLEMY=$((PROBLEMY + 1)); }
spr() { local o="$1"; shift; if "$@" >/dev/null 2>&1; then ok "$o"; else zle "$o"; fi; }
nie() { local o="$1"; shift; if "$@" >/dev/null 2>&1; then zle "$o"; else ok "$o"; fi; }
jako() { local u="$1"; shift; runuser -u "$u" -- "$@"; }
dostep() { jako "$AGENT" sh -c 'test -r "$1" || test -w "$1" || test -x "$1"' _ "$1"; }
w_grupie() { id -nG "$1" 2>/dev/null | tr ' ' '\n' | grep -qx "$2"; }

raport() {
  local r g p x pid wynik
  echo
  echo "Użytkownik agenta:"
  if ! id "$AGENT" >/dev/null 2>&1; then
    zle "użytkownik $AGENT nie istnieje"; return
  fi
  ok "użytkownik $AGENT istnieje"
  nie "$AGENT bez grup sudo/admin/wheel" sh -c "id -nG $AGENT | tr ' ' '\n' | grep -qxE 'sudo|admin|wheel'"
  spr "$AGENT bez prawa do sudo" sh -c "LC_ALL=C sudo -l -U $AGENT 2>&1 | grep -q 'not allowed'"
  spr "hasło $AGENT zablokowane" sh -c "[ \"\$(passwd -S $AGENT | awk '{print \$2}')\" = L ]"
  spr "SSH: DenyUsers $AGENT" sh -c \
    "grep -hiE '^[[:space:]]*DenyUsers' /etc/ssh/sshd_config /etc/ssh/sshd_config.d/*.conf 2>/dev/null | grep -qw $AGENT"
  spr "grupa $GRUPA: $AGENT" w_grupie "$AGENT" "$GRUPA"
  spr "grupa $GRUPA: $PANEL" w_grupie "$PANEL" "$GRUPA"

  echo "Zapis agenta:"
  if [ -d "$PROJEKTY" ]; then
    spr "przejście do $PROJEKTY" jako "$AGENT" test -x "$PROJEKTY"
    for p in "$PROJEKTY"/*/; do
      p="${p%/}"
      [ -L "$p" ] && continue
      spr "zapis: ${p#$PANEL_DOM/}" jako "$AGENT" test -w "$p"
      g="$p/.git"
      [ -d "$g" ] || continue
      spr "  core.sharedRepository=group" sh -c "[ \"\$(runuser -u $PANEL -- git -C '$p' config --get core.sharedRepository)\" = group ]"
      spr "  zapis .git/objects, refs/heads, worktrees" jako "$AGENT" sh -c \
        'test -w "$1/objects" && test -w "$1/refs/heads" && test -w "$1/worktrees"' _ "$g"
      nie "  bez zapisu .git, config, hooks, info" jako "$AGENT" sh -c \
        'test -w "$1" || test -w "$1/config" || test -w "$1/hooks" || test -w "$1/info"' _ "$g"
      spr "  .agent/ w .git/info/exclude" grep -qxF '.agent/' "$g/info/exclude"
    done
  else
    zle "brak $PROJEKTY"
  fi
  for x in $WSPOLNE_IS; do spr "zapis: IntegrateSystems/$x" jako "$AGENT" test -w "$IS/$x"; done
  spr "odczyt: IntegrateSystems/standard (raport PM)" jako "$AGENT" test -r "$IS/standard/pm.py"
  spr "przejście: IntegrateSystems/uruchomienia (katalog testu i planu dnia)" jako "$AGENT" test -x "$IS/uruchomienia"
  spr "git safe.directory dla $AGENT" sh -c "runuser -u $AGENT -- git config --global --get-all safe.directory | grep -qxF '*'"

  echo "Brak dostępu agenta:"
  for x in $ZAKAZANE; do
    [ -e "$x" ] || continue
    nie "$x" dostep "$x"
  done
  spr "$ETC: root:$PANEL 750" sh -c "[ \"\$(stat -c '%U:%G %a' $ETC)\" = 'root:$PANEL 750' ]"

  echo "sudo i Claude:"
  spr "$SUDOERS" test -f "$SUDOERS"
  spr "visudo -c" visudo -c -q
  spr "panel → $AGENT: tylko $AGENT_CLAUDE" sh -c \
    "LC_ALL=C sudo -l -U $PANEL | grep -q '($AGENT) NOPASSWD: $AGENT_CLAUDE'"
  spr "Claude Code dla $AGENT" test -x "$AGENT_CLAUDE"
  spr "panel widzi $AGENT_CLAUDE" jako "$PANEL" test -f "$AGENT_CLAUDE"
  if [ -x "$AGENT_CLAUDE" ]; then
    wynik="$(cd / && runuser -u "$PANEL" -- sudo -n -u "$AGENT" -- "$AGENT_CLAUDE" --version 2>&1 | head -n 1)"
    if [ -n "$wynik" ] && ! printf '%s' "$wynik" | grep -qi 'password\|sudo:'; then
      ok "panel uruchamia claude jako $AGENT ($wynik)"
    else
      zle "panel nie uruchamia claude jako $AGENT (${wynik:-brak odpowiedzi})"
    fi
    if (cd / && runuser -u "$PANEL" -- timeout 60 sudo -n -u "$AGENT" -- "$AGENT_CLAUDE" auth status 2>/dev/null) \
         | grep -Eq '"loggedIn"[[:space:]]*:[[:space:]]*true'; then
      ok "Claude agenta zalogowany"
    else
      zle "Claude agenta niezalogowany: panel → Zaloguj (opis na końcu)"
    fi
  fi

  echo "Panel:"
  for x in "PANEL_AGENT_USER=$AGENT" "PANEL_CLAUDE=$AGENT_CLAUDE" "PANEL_LOKALNY_KLUCZ_PLIK=$KLUCZ"; do
    spr "panel.env: $x" grep -qx "$x" "$ENV_PLIK"
  done
  spr "$KLUCZ: root:$PANEL 640, niepusty" sh -c "[ -s $KLUCZ ] && [ \"\$(stat -c '%U:%G %a' $KLUCZ)\" = 'root:$PANEL 640' ]"
  spr "panel czyta klucz" jako "$PANEL" test -r "$KLUCZ"
  spr "usługa panel działa" systemctl is-active --quiet panel.service
  pid="$(systemctl show -p MainPID --value panel.service 2>/dev/null)"
  spr "proces panelu ma grupę $GRUPA" panel_ma_grupe "$pid"
  if [ -x /usr/local/bin/zdrowie ]; then
    spr "zdrowie sprawdza logowanie agenta" grep -q 'claude-agent' /usr/local/bin/zdrowie
  fi
}

# ---------------------------------------------------------------- przebieg
if [ "$SPRAWDZ" -eq 0 ]; then
  source "$TU/instalacja-wspolne.sh"     # zgodność z origin/main, kopia do /usr/local/lib/integrate ($LIB)
  instaluj
fi
echo "Raport$( [ "$SPRAWDZ" -eq 1 ] && echo ' (bez zmian)'):"
raport
echo
if [ "$PROBLEMY" -eq 0 ]; then
  echo "Wszystko w porządku."
else
  echo "Do poprawy: $PROBLEMY (wiersze BRAK)."
fi
cat <<EOF

Logowanie Claude dla $AGENT (raz, potem co kilka miesięcy po wygaśnięciu):
  1. Panel → widok agentów: przy Claude „Wymaga logowania” → Zaloguj. Panel uruchamia
     „$AGENT_CLAUDE auth login” jako $AGENT i pokazuje adres strony logowania.
  2. Otwórz adres (Mac albo iPhone), zaloguj kontem Max, skopiuj kod i wklej go w panelu.
  3. Test połączenia w panelu ma wynik „ok”; potem: sudo bash $SKRYPT --sprawdz.
  Bez panelu (ssh jako ops): sudo -u $AGENT -H $AGENT_CLAUDE auth login
EOF
[ "$PROBLEMY" -eq 0 ]
