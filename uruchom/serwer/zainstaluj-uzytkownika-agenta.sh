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
#  8. pliki sekretów w repozytoriach projektów (.env*, *.key, *.pem, credentials*, bazy SQLite; bez katalogów testów):
#     właściciel panel, grupa panel, 600, bez ACL
#  9. zapora: nftables (tabela inet integrate_agent) odrzuca połączenia użytkownika agent z 127.0.0.1 na portach panelu
#     (4801), asystenta Useme (8765) i API administracyjnego Caddy (2019); /etc/nftables.d/integrate-agent.nft
#     ładuje jednostka agent-zapora.service (także po restarcie serwera)
# 10. nowe wersje zdrowie i odtworz (gdy zainstalowane), restart panelu, raport
# Raport sprawdza też warunki sprzedaży PC (kopia poza serwerem, próba odtworzenia); te nie liczą się do BRAK.
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
ZAPORA_NFT=/etc/nftables.d/integrate-agent.nft
ZAPORA_JEDNOSTKA=agent-zapora.service
ZAPORA_PORTY="4801 8765 2019"                  # panel, asystent Useme, API administracyjne Caddy
KOPIE=$PANEL_DOM/kopie
PROBA_STAN=$KOPIE/proba-odtworzenia.json       # zapisuje odtworz.sh po udanej próbie
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

# Pliki sekretów w repozytoriach projektów (wzorce jak w zapis-kart.sh), rozdzielone \0. Pomija katalogi testów,
# zależności, .git i worktree agentów (.agent/), wzory (.example, .sample, .template, .przyklad, .dist) oraz kod źródłowy
# o nazwie credentials* (np. credentials.py).
sekrety() {
  [ -d "$PROJEKTY" ] || return 0
  find "$PROJEKTY" \
    \( -type d \( -name .git -o -name .agent -o -name node_modules -o -name .venv -o -name venv -o -name test -o -name tests \
         -o -name __tests__ -o -name spec -o -name fixtures -o -name testdata \) -prune \) -o \
    \( -type f \( -name '.env*' -o -name '*.env' -o -name '*.key' -o -name '*.pem' -o -name 'credentials*' \
         -o -name '*.sqlite' -o -name '*.sqlite3' -o -name '*.db' -o -name '*.sqlite-wal' -o -name '*.sqlite-shm' \
         -o -name '*.sqlite-journal' -o -name '*.db-wal' -o -name '*.db-shm' -o -name '*.db-journal' \) \
       ! -name '*.example' ! -name '*.sample' ! -name '*.template' ! -name '*.przyklad' ! -name '*.dist' \
       ! \( -name 'credentials*' \( -name '*.py' -o -name '*.js' -o -name '*.mjs' -o -name '*.cjs' -o -name '*.ts' \
            -o -name '*.tsx' -o -name '*.jsx' -o -name '*.go' -o -name '*.rs' -o -name '*.java' -o -name '*.kt' \
            -o -name '*.swift' -o -name '*.rb' -o -name '*.php' -o -name '*.cs' -o -name '*.md' \) \) -print0 \)
}

w_gicie() {  # plik: śledzony w repozytorium projektu (wtedy agent czyta treść z .git/objects mimo praw 600)
  local rel="${1#"$PROJEKTY"/}" r
  r="$PROJEKTY/${rel%%/*}"
  [ -d "$r/.git" ] || return 1
  runuser -u "$PANEL" -- git -c core.fsmonitor=false -C "$r" ls-files --error-unmatch -- "${rel#*/}" >/dev/null 2>&1
}

zabezpiecz_sekrety() {  # po wspolny_katalog: ten nadaje grupie projekty ACL także na pliki sekretów
  local f n=0
  while IFS= read -r -d '' f; do
    setfacl -b "$f" 2>/dev/null
    if chown "$PANEL:$PANEL" "$f" && chmod 600 "$f"; then n=$((n + 1)); else uwaga "nie zabezpieczono ${f#"$PANEL_DOM"/}"; fi
    if w_gicie "$f"; then
      uwaga "${f#"$PANEL_DOM"/} jest w gicie: agent czyta go z .git/objects. Unieważnij sekret u dostawcy i usuń plik z repozytorium."
    fi
  done < <(sekrety)
  log "Sekrety w projektach: $n plików tylko dla $PANEL (600, bez ACL)."
}

zapora() {  # reguła nftables dla uid agent i jednostka, która ładuje ją przy starcie
  local nft tmp zmiana=0 porty
  if ! command -v nft >/dev/null; then
    log "Instaluję pakiet nftables..."
    apt-get install -y -q nftables >/dev/null || przerwij "brak nft (sudo apt install nftables)."
  fi
  nft="$(command -v nft)"
  porty="$(echo "$ZAPORA_PORTY" | sed 's/ /, /g')"
  tmp="$(mktemp)"
  # „table” i „delete table” na początku: plik zawsze zakłada tabelę od nowa (powtarzalne ładowanie, jedna transakcja).
  cat > "$tmp" <<EOF
# Zapora dla użytkownika $AGENT: odrzuca jego połączenia z panelem (4801), asystentem Useme (8765) i API administracyjnym
# Caddy (2019) na adresach lokalnych. Inne połączenia agenta (GitHub, Claude) bez zmian.
# Plik instaluje uruchom/serwer/zainstaluj-uzytkownika-agenta.sh; zmiany tylko tam. Ładuje go $ZAPORA_JEDNOSTKA.
table inet integrate_agent
delete table inet integrate_agent
table inet integrate_agent {
	chain output {
		type filter hook output priority 0; policy accept;
		meta skuid $AGENT ip daddr 127.0.0.0/8 tcp dport { $porty } reject
		meta skuid $AGENT ip6 daddr ::1 tcp dport { $porty } reject
	}
}
EOF
  "$nft" -c -f "$tmp" || { rm -f "$tmp"; przerwij "reguła nftables nie przeszła nft -c; nic nie zapisano."; }
  install -d -o root -g root -m 755 "${ZAPORA_NFT%/*}"
  if ! cmp -s "$tmp" "$ZAPORA_NFT"; then
    install -o root -g root -m 644 "$tmp" "$ZAPORA_NFT" && log "Zapisano $ZAPORA_NFT."
    zmiana=1
  fi
  cat > "$tmp" <<EOF
# Zapora dla użytkownika $AGENT ($ZAPORA_NFT). Instaluje uruchom/serwer/zainstaluj-uzytkownika-agenta.sh.
[Unit]
Description=Zapora użytkownika $AGENT (bez dostępu do panelu i asystenta Useme)
DefaultDependencies=no
Wants=network-pre.target
After=nftables.service ufw.service
Before=network-pre.target shutdown.target panel.service useme.service
Conflicts=shutdown.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=$nft -f $ZAPORA_NFT
ExecStop=$nft delete table inet integrate_agent

[Install]
WantedBy=sysinit.target
EOF
  if ! cmp -s "$tmp" "/etc/systemd/system/$ZAPORA_JEDNOSTKA"; then
    install -o root -g root -m 644 "$tmp" "/etc/systemd/system/$ZAPORA_JEDNOSTKA" && log "Zapisano $ZAPORA_JEDNOSTKA."
    systemctl daemon-reload
    zmiana=1
  fi
  rm -f "$tmp"
  systemctl is-enabled --quiet "$ZAPORA_JEDNOSTKA" || systemctl enable --quiet "$ZAPORA_JEDNOSTKA"
  if [ "$zmiana" -eq 1 ] || ! systemctl is-active --quiet "$ZAPORA_JEDNOSTKA"; then
    if systemctl restart "$ZAPORA_JEDNOSTKA"; then log "Zapora agenta załadowana."; else uwaga "zapora agenta nie załadowana (journalctl -u $ZAPORA_JEDNOSTKA)."; fi
  fi
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
  local zmiana_env=0 zmiana_grup=0 u g e x

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
  # Wyjątek: rozwój panelu (zainstaluj-rozwoj.sh, ROZWOJ.md) wpuszcza agenta tylko z kluczami z pliku roota
  # /etc/ssh/klucze-agenta (AuthorizedKeysFile w bloku Match); ~/.ssh agenta nie działa, więc sam klucza nie dopisze.
  if grep -qs "AuthorizedKeysFile /etc/ssh/klucze-agenta" "$SSHD_DROP"; then
    log "SSH agenta: tylko klucze z /etc/ssh/klucze-agenta (rozwój panelu)."
  elif [ -d /etc/ssh/sshd_config.d ] && ! grep -qs "^DenyUsers.*[[:space:]]$AGENT\([[:space:]]\|\$\)" "$SSHD_DROP"; then
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
    zabezpiecz_sekrety
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

  # 9. Zapora dla uid agent.
  zapora

  # 10. Kontrola zdrowia (sprawdza logowanie agenta) i odtworz (zapisuje wynik próby) w nowej wersji, restart panelu.
  for x in zdrowie odtworz; do
    if [ -x "/usr/local/bin/$x" ] && [ -f "$LIB/$x.sh" ] && ! cmp -s "$LIB/$x.sh" "/usr/local/bin/$x"; then
      install -m 755 "$LIB/$x.sh" "/usr/local/bin/$x" && log "Zaktualizowano /usr/local/bin/$x."
    fi
  done
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
pomin() { printf '  --    %s\n' "$*"; }
spr() { local o="$1"; shift; if "$@" >/dev/null 2>&1; then ok "$o"; else zle "$o"; fi; }
nie() { local o="$1"; shift; if "$@" >/dev/null 2>&1; then zle "$o"; else ok "$o"; fi; }
jako() { local u="$1"; shift; runuser -u "$u" -- "$@"; }
# Dostęp sprawdzany próbą odczytu (ls katalogu, bajt pliku), nie test -r/-w: te dają fałszywe „nie” przy ACL.
dostep() { jako "$AGENT" sh -c 'if [ -d "$1" ]; then ls -- "$1"; else head -c1 -- "$1"; fi' _ "$1"; }
w_grupie() { id -nG "$1" 2>/dev/null | tr ' ' '\n' | grep -qx "$2"; }
# Zapis sprawdzany prawdziwym plikiem: test -w daje fałszywe „nie” przy prawach nadanych przez ACL.
zapisuje() { jako "$AGENT" sh -c 'f="$1/.proba-agenta-$$"; touch "$f" && rm -f "$f"' _ "$1"; }

proba_portu() {  # port: panel łączy się z 127.0.0.1:port, agent nie (curl, kod 7 = połączenie odrzucone)
  local port="$1" opis kod
  case "$port" in 4801) opis=panel ;; 8765) opis="asystent Useme" ;; 2019) opis="API Caddy" ;; *) opis="port $port" ;; esac
  if ! command -v curl >/dev/null; then zle "$opis: brak curl, próby nie wykonano"; return; fi
  if ! jako "$PANEL" curl -s -o /dev/null --max-time 5 "http://127.0.0.1:$port/" 2>/dev/null; then
    if [ "$port" = 4801 ]; then
      zle "$opis: 127.0.0.1:$port nie odpowiada także dla $PANEL, próby nie wykonano"
    else
      pomin "$opis: 127.0.0.1:$port nie odpowiada także dla $PANEL, próby nie wykonano"
    fi
    return
  fi
  jako "$AGENT" curl -s -o /dev/null --max-time 5 "http://127.0.0.1:$port/" 2>/dev/null
  kod=$?
  case "$kod" in
    7) ok "$opis: połączenie $AGENT z 127.0.0.1:$port odrzucone" ;;
    0) zle "$opis: $AGENT łączy się z 127.0.0.1:$port" ;;
    *) zle "$opis: $AGENT → 127.0.0.1:$port, curl kod $kod (oczekiwany 7: odrzucone)" ;;
  esac
}

# Warunki sprzedaży PC (ksiega/MIGRACJA.md, „Przed sprzedażą PC”). Wypisuje wiersze tak/nie, kod wyjścia: liczba „nie”.
warunki_sprzedazy() {
  python3 - "$KOPIE/ostatnia.json" "$PROBA_STAN" "$IS/ksiega/MIGRACJA.md" "$IS/szkice/infrastruktura/ZADANIA.md" <<'PY'
import datetime, json, re, sys
kopia, proba, migracja, zadania = sys.argv[1:5]
teraz = datetime.datetime.now(datetime.timezone.utc)
nie = 0
def wiersz(tak, tekst):
    global nie
    if not tak:
        nie += 1
    print("  %-5s %s" % ("tak" if tak else "nie", tekst))
def czytaj(p):
    try:
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return None
def czas(v):
    try:
        t = datetime.datetime.fromisoformat(v)
        return t if t.tzinfo else t.replace(tzinfo=datetime.timezone.utc)
    except (TypeError, ValueError):
        return None

d = czytaj(kopia)
if d is None:
    wiersz(False, "kopia poza serwerem: brak %s (kopia nie działa)" % kopia)
else:
    off_at = czas(d.get("offAt") or (d.get("at") if d.get("off") is True else None))
    if off_at is None:
        wiersz(False, "kopia poza serwerem: jeszcze żadnej wysyłki (KOPIA_CEL, sekcja „Kopia poza serwerem”)")
    else:
        h = int((teraz - off_at).total_seconds() // 3600)
        wiersz(h < 26, "kopia poza serwerem: ostatnia wysyłka %s (%d h temu, wymagane < 26 h)" % (d.get("offAt") or d.get("at"), h))

p = czytaj(proba) or {}
u = p.get("unpack") if isinstance(p.get("unpack"), dict) else {}
c = p.get("check") if isinstance(p.get("check"), dict) else {}
if czas(u.get("at")) and u.get("encrypted") is True:
    wiersz(True, "próba odtworzenia: %s, %s, %s s" % (u.get("at"), u.get("archive"), u.get("seconds")))
elif czas(u.get("at")):
    wiersz(False, "próba odtworzenia %s na archiwum bez szyfrowania (%s); potrzebna na archiwum .gpg ze Storage Box" % (u.get("at"), u.get("archive")))
elif czas(c.get("at")):
    wiersz(False, "próba odtworzenia: tylko sprawdzenie archiwum (%s), bez rozpakowania do /tmp/proba" % c.get("at"))
else:
    wiersz(False, "próba odtworzenia: brak wyniku w %s (odtworz zapisuje go po udanej próbie)" % proba)

try:
    with open(migracja, encoding="utf-8") as f:
        m = f.read()
    wiersz(not re.search(r"data próby: —", m), "czas próby wpisany w ksiega/MIGRACJA.md („Odtworzenie serwera”)")
except OSError:
    pass
try:
    with open(zadania, encoding="utf-8") as f:
        z = f.read()
    wiersz(bool(re.search(r"^- \[x\] Przeprowadź dzień próbny bez PC", z, re.M)), "dzień próbny bez PC zakończony (zadanie w Infrastrukturze)")
except OSError:
    pass
sys.exit(min(nie, 100))
PY
}

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
  spr "SSH: DenyUsers $AGENT albo klucze tylko z pliku roota" sh -c \
    "grep -hiE '^[[:space:]]*DenyUsers' /etc/ssh/sshd_config /etc/ssh/sshd_config.d/*.conf 2>/dev/null | grep -qw $AGENT ||
     { grep -qs 'AuthorizedKeysFile /etc/ssh/klucze-agenta' $SSHD_DROP && [ \"\$(stat -c %U /etc/ssh/klucze-agenta)\" = root ]; }"
  spr "grupa $GRUPA: $AGENT" w_grupie "$AGENT" "$GRUPA"
  spr "grupa $GRUPA: $PANEL" w_grupie "$PANEL" "$GRUPA"

  echo "Zapis agenta:"
  if [ -d "$PROJEKTY" ]; then
    spr "przejście do $PROJEKTY" jako "$AGENT" test -x "$PROJEKTY"
    for p in "$PROJEKTY"/*/; do
      p="${p%/}"
      [ -L "$p" ] && continue
      spr "zapis: ${p#$PANEL_DOM/}" zapisuje "$p"
      g="$p/.git"
      [ -d "$g" ] || continue
      spr "  core.sharedRepository=group" sh -c "[ \"\$(runuser -u $PANEL -- git -C '$p' config --get core.sharedRepository)\" = group ]"
      spr "  zapis .git/objects, refs/heads, worktrees" jako "$AGENT" sh -c \
        'test -w "$1/objects" && test -w "$1/refs/heads" && test -w "$1/worktrees"' _ "$g"
      nie "  bez zapisu .git, config, hooks, info" jako "$AGENT" sh -c \
        'for f in "$1" "$1/config" "$1/hooks" "$1/info"; do touch -c -- "$f" 2>/dev/null && exit 0; done; exit 1' _ "$g"
      spr "  .agent/ w .git/info/exclude" grep -qxF '.agent/' "$g/info/exclude"
    done
  else
    zle "brak $PROJEKTY"
  fi
  for x in $WSPOLNE_IS; do spr "zapis: IntegrateSystems/$x" zapisuje "$IS/$x"; done
  spr "odczyt: IntegrateSystems/standard (raport PM)" jako "$AGENT" test -r "$IS/standard/pm.py"
  spr "przejście: IntegrateSystems/uruchomienia (katalog testu i planu dnia)" jako "$AGENT" test -x "$IS/uruchomienia"
  spr "git safe.directory dla $AGENT" sh -c "runuser -u $AGENT -- git config --global --get-all safe.directory | grep -qxF '*'"

  echo "Brak dostępu agenta:"
  for x in $ZAKAZANE; do
    [ -e "$x" ] || continue
    nie "$x" dostep "$x"
  done
  spr "$ETC: root:$PANEL 750" sh -c "[ \"\$(stat -c '%U:%G %a' $ETC)\" = 'root:$PANEL 750' ]"

  echo "Sekrety w projektach (próba odczytu jako $AGENT):"
  local n=0 przed=$PROBLEMY f
  while IFS= read -r -d '' f; do
    n=$((n + 1))
    if dostep "$f" >/dev/null 2>&1; then zle "$AGENT czyta ${f#"$PANEL_DOM"/} (instalator ustawia 600)"; fi
    if w_gicie "$f"; then zle "w gicie, $AGENT czyta z .git/objects: ${f#"$PANEL_DOM"/} (unieważnij sekret, usuń z repozytorium)"; fi
  done < <(sekrety)
  if [ "$PROBLEMY" -eq "$przed" ]; then ok "plików sekretów: $n, $AGENT nie czyta żadnego"; fi

  echo "Zapora agenta:"
  spr "$ZAPORA_NFT" test -f "$ZAPORA_NFT"
  spr "$ZAPORA_JEDNOSTKA włączona i aktywna" sh -c \
    "systemctl is-enabled --quiet $ZAPORA_JEDNOSTKA && systemctl is-active --quiet $ZAPORA_JEDNOSTKA"
  spr "nftables: tabela inet integrate_agent z regułą dla $AGENT" sh -c \
    "nft list table inet integrate_agent 2>/dev/null | grep -q 'skuid'"
  for x in $ZAPORA_PORTY; do proba_portu "$x"; done

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
echo
echo "Przed sprzedażą PC (ksiega/MIGRACJA.md; nie liczy się do BRAK):"
warunki_sprzedazy
NIESPELNIONE=$?
if [ "$NIESPELNIONE" -eq 0 ]; then
  echo "Warunki sprzedaży PC spełnione: dalej kroki z sekcji „Przed sprzedażą PC”."
else
  echo "PC jeszcze nie do sprzedaży (niespełnione: $NIESPELNIONE)."
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
