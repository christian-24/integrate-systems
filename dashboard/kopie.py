"""Kopia projektu na serwerze a repozytorium na GitHubie: stan, pobranie (fetch), wysłanie (push), klon na start,
przeniesienie kopii do kosza.

Źródłem prawdy jest repozytorium na GitHubie (pole karty `github: właściciel/repozytorium`, opcjonalnie
`github gałąź: nazwa`). Kopia w folderze projektu jest potrzebna tylko na czas pracy. Po usunięciu kopii folder
projektu zostaje z samymi dowiązaniami do karty i zadań (KARTA.md, ZADANIA.md, DECYZJE.md, kampanie), więc rejestr
i panel działają jak dotąd; przy następnym zadaniu albo budowaniu podglądu panel klonuje repozytorium i przenosi
dowiązania do nowej kopii.

Zasady: bez --force, bez przepisywania historii, bez haków repozytorium, git bez pytań o hasło i z limitem czasu.
Sama biblioteka standardowa; moduł nie importuje serwera ani zarządcy.
"""
import datetime
import getpass
import json
import os
import re
import shutil
import subprocess
import threading

CARD_LINKS = ("KARTA.md", "ZADANIA.md", "DECYZJE.md", "kampanie")
CARD_REQUIRED = ("KARTA.md", "ZADANIA.md")
# Pomijane w stanie i przy usuwaniu kopii: katalogi robocze agentów, zależności, wyniki budowania, zrzuty.
SKIP_PARTS = {".agent", "node_modules", ".zrzuty", "dist", "build", "dist-ssr", ".next", ".nuxt", ".svelte-kit",
              ".astro", ".turbo", ".vite", ".parcel-cache", ".cache", "__pycache__", ".pytest_cache"}
EXCLUDE = ("/.agent/", ".zrzuty/", "node_modules/")
MARKER = ".kopia-na-githubie.json"           # w folderze po usunięciu kopii: kiedy i dokąd przeniesiono
TRASH = ".kosz"
REPO = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}/[A-Za-z0-9_.-]{1,100}$")
BRANCH = re.compile(r"^(?!-)(?!.*\.\.)(?!.*//)[A-Za-z0-9._/-]{1,200}$")
LIST_MAX = 20
_locks = {}
_locks_lock = threading.Lock()


def _timeout():
    try:
        return max(5, int(os.environ.get("PANEL_GITHUB_TIMEOUT", "") or 60))
    except ValueError:
        return 60


def folder_lock(folder):
    """Jedna operacja naraz na folderze projektu (klon, wysłanie, usunięcie)."""
    key = os.path.realpath(folder)
    with _locks_lock:
        return _locks.setdefault(key, threading.Lock())


# ---------- pole karty ----------
def repo_name(value):
    """Pole `github:` albo adres origin → "właściciel/repozytorium" (bez .git); "" gdy to nie GitHub."""
    v = str(value or "").strip().strip("`").strip()
    m = re.match(r"^(?:https?://(?:[^@/]+@)?(?:www\.)?github\.com/|ssh://git@(?:ssh\.)?github\.com(?::\d+)?/|"
                 r"git@github\.com:)(.+)$", v, re.I)
    if m:
        v = m.group(1)
    v = v.strip("/")
    if v.lower().endswith(".git"):
        v = v[:-4]
    if not REPO.match(v) or ".." in v:
        return ""
    return v


def branch_name(value):
    v = str(value or "").strip().strip("`").strip()
    return v if BRANCH.match(v) and not v.endswith((".", "/", ".lock")) else ""


def clone_url(repo):
    """Adres klonu: PANEL_GITHUB_URL ({repo} = właściciel/repozytorium), domyślnie przez SSH."""
    tpl = os.environ.get("PANEL_GITHUB_URL", "").strip() or "git@github.com:{repo}.git"
    return tpl.replace("{repo}", repo)


def safe_url(url):
    """Adres bez danych logowania (user:token@) do pokazania w panelu."""
    url = str(url or "").strip()
    return re.sub(r"^([a-z][a-z0-9+.-]*://)[^/@]+@", r"\1", url, flags=re.I)


# ---------- git ----------
def _git(cwd, args, timeout=20, net=False):
    """(kod, stdout, stderr); kod -1 przy braku gita albo przekroczonym czasie (stderr "timeout")."""
    # GIT_OPTIONAL_LOCKS=0: odczyt stanu (git status) nie zakłada index.lock, więc nie blokuje scalania obok
    env = dict(os.environ, LC_ALL="C", LANG="C", GIT_TERMINAL_PROMPT="0", GIT_ASKPASS="true", SSH_ASKPASS="true",
               GIT_OPTIONAL_LOCKS="0")
    if net and not env.get("GIT_SSH_COMMAND"):
        env["GIT_SSH_COMMAND"] = "ssh -o BatchMode=yes -o ConnectTimeout=15 -o StrictHostKeyChecking=accept-new"
    base = ["git", "-c", "core.hooksPath=" + os.devnull, "-c", "core.fsmonitor=false", "-c", "core.quotePath=false",
            "-c", "credential.interactive=never"]
    try:
        p = subprocess.run(base + list(args), cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, encoding="utf-8", errors="replace", timeout=timeout, env=env)
        return p.returncode, p.stdout or "", p.stderr or ""
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"
    except (OSError, subprocess.SubprocessError) as e:
        return -1, "", str(e)


def has_repo(folder):
    return bool(folder) and os.path.exists(os.path.join(folder, ".git"))


def _who():
    try:
        return getpass.getuser()
    except Exception:  # noqa: BLE001
        return "panelu"


def net_error(err, repo=""):
    """("access" | "timeout" | "missing" | "error", tekst dla właściciela) z komunikatu gita."""
    e = (err or "").lower()
    where = (" " + repo) if repo else ""
    if e == "timeout":
        return "timeout", "GitHub nie odpowiedział w %d s. Spróbuj ponownie później." % _timeout()
    if any(x in e for x in ("permission denied", "could not read username", "authentication failed",
                            "host key verification failed", "access denied", "the requested url returned error: 403",
                            "terminal prompts disabled", "publickey", "write access to repository not granted")):
        return "access", ("Brak dostępu do GitHuba%s z serwera (konto %s). Ustaw klucz SSH konta %s na GitHubie: "
                          "klucz wdrożeniowy repozytorium z prawem zapisu albo klucz konta z dostępem."
                          % (where, _who(), _who()))
    if any(x in e for x in ("repository not found", "does not appear to be a git repository", "not found")):
        return "missing", ("Nie znaleziono repozytorium%s na GitHubie albo konto %s nie ma do niego dostępu. "
                           "Sprawdź pole github: w karcie i klucz konta %s." % (where, _who(), _who()))
    if any(x in e for x in ("could not resolve host", "network is unreachable", "connection timed out",
                            "connection refused")):
        return "timeout", "Brak połączenia z GitHubem z serwera. Spróbuj ponownie później."
    line = next((x.strip() for x in (err or "").splitlines() if x.strip().lower().startswith(("fatal", "error"))),
                (err or "").strip().splitlines()[-1].strip() if (err or "").strip() else "nieznany błąd")
    return "error", "Git: %s" % line[:200]


# ---------- stan ----------
def _skip(path):
    parts = [x for x in path.rstrip("/").split("/") if x]
    return any(x in SKIP_PARTS for x in parts)


def _dirty(folder):
    """[(kod, ścieżka)] plików niezatwierdzonych i nieśledzonych bez katalogów pomijanych i dowiązań karty."""
    skip = [":(exclude,glob)**/%s/**" % x for x in sorted(SKIP_PARTS)]
    code, out, _ = _git(folder, ["status", "--porcelain=v1", "-z", "--untracked-files=all", "--", "."] + skip,
                        timeout=30)
    if code != 0:
        return None
    items, parts, i = [], out.split("\0"), 0
    while i < len(parts):
        entry = parts[i]
        i += 1
        if len(entry) < 4:
            continue
        xy, path = entry[:2], entry[3:]
        if xy[0] in "RC":
            i += 1                                   # druga ścieżka zmiany nazwy
        if _skip(path):
            continue
        top = path.rstrip("/")
        if "/" not in top and top in CARD_LINKS and os.path.islink(os.path.join(folder, top)):
            continue
        items.append((xy.strip() or "?", path))
    return items


# ---------- zmiany niezatwierdzone: zatwierdzenie i odłożenie na bok (AGENCI.md, „Zmiany niezatwierdzone”) ----------
STASH_MAX = 10
STASH_REF = re.compile(r"^stash@\{\d{1,3}\}$")


def _pathspec(folder):
    """Ścieżki zmian projektu: folder bez katalogów pomijanych i bez dowiązań karty."""
    spec = ["--", "."] + [":(exclude,glob)**/%s/**" % x for x in sorted(SKIP_PARTS)]
    spec += [":(exclude)%s" % n for n in CARD_LINKS if os.path.islink(os.path.join(folder, n))]
    return spec


def commit_dirty(folder, message, name="Panel projektów", email="panel@localhost"):
    """Zatwierdza pliki niezatwierdzone i nieśledzone (jak w stanie kopii) jednym commitem na bieżącej gałęzi.
    (True, skrót commita) albo (False, powód)."""
    dirty = _dirty(folder)
    if dirty is None:
        return False, "Nie odczytano stanu repozytorium."
    if not dirty:
        return False, "Nie ma zmian do zatwierdzenia."
    code, _, err = _git(folder, ["add", "-A"] + _pathspec(folder), timeout=120)
    if code != 0:
        return False, "git add: %s" % (err.strip().splitlines() or ["błąd"])[-1][:200]
    ident = ["-c", "user.name=%s" % name, "-c", "user.email=%s" % email, "-c", "commit.gpgsign=false"]
    code, _, err = _git(folder, ident + ["commit", "-q", "--no-verify", "-m", message] + _pathspec(folder),
                        timeout=120)
    if code != 0:
        return False, "git commit: %s" % (err.strip().splitlines() or ["błąd"])[-1][:200]
    code, sha, _ = _git(folder, ["rev-parse", "--short", "HEAD"])
    return True, sha.strip()


def stash_save(folder, message):
    """Odkłada zmiany (także nieśledzone) do schowka git z opisem; do przywrócenia (stash_restore). (True, ref)."""
    dirty = _dirty(folder)
    if dirty is None:
        return False, "Nie odczytano stanu repozytorium."
    if not dirty:
        return False, "Nie ma zmian do odłożenia."
    code, _, err = _git(folder, ["stash", "push", "-u", "-q", "-m", message] + _pathspec(folder), timeout=120)
    if code != 0:
        return False, "git stash: %s" % (err.strip().splitlines() or ["błąd"])[-1][:200]
    return True, "stash@{0}"


def stash_list(folder):
    """[{"ref", "message", "at", "files"}] schowka repozytorium, najnowsze pierwsze, najwyżej STASH_MAX."""
    code, out, _ = _git(folder, ["stash", "list", "--format=%gd%x09%cI%x09%gs"])
    if code != 0:
        return []
    items = []
    for line in out.splitlines()[:STASH_MAX]:
        parts = line.split("\t", 2)
        if len(parts) != 3 or not STASH_REF.match(parts[0]):
            continue
        msg = re.sub(r"^On [^:]+: ", "", parts[2])
        code, names, _ = _git(folder, ["stash", "show", "--include-untracked", "--name-only", parts[0]])
        if code != 0:
            code, names, _ = _git(folder, ["stash", "show", "--name-only", parts[0]])
        items.append({"ref": parts[0], "at": parts[1][:19], "message": msg[:300],
                      "files": [x for x in names.splitlines() if x.strip()][:LIST_MAX]})
    return items


def stash_restore(folder, ref):
    """Przywraca odłożone zmiany (git stash apply, potem drop). Tylko przy czystym repozytorium; przy konflikcie
    repozytorium wraca do stanu sprzed próby, a schowek zostaje. (True, "") albo (False, powód)."""
    ref = str(ref or "")
    if not STASH_REF.match(ref):
        return False, "Nieznany wpis schowka."
    dirty = _dirty(folder)
    if dirty is None:
        return False, "Nie odczytano stanu repozytorium."
    if dirty:
        return False, "Najpierw zatwierdź albo odłóż obecne zmiany (%d %s)." % (
            len(dirty), "plik" if len(dirty) == 1 else "pliki")
    if _git(folder, ["rev-parse", "-q", "--verify", ref])[0] != 0:
        return False, "Nie ma już tego wpisu schowka."
    code, out, err = _git(folder, ["stash", "apply", "-q", ref], timeout=120)
    if code != 0:
        _git(folder, ["reset", "-q", "--merge"], timeout=60)
        _git(folder, ["checkout", "-q", "--", "."], timeout=60)
        left = _dirty(folder) or []
        for code_, path in left:
            if code_ == "??":
                full = os.path.join(folder, path)
                if os.path.isfile(full) and not os.path.islink(full):
                    os.remove(full)     # nieśledzone pliki z nieudanej próby: są też w schowku
        return False, "Zmiany kolidują z obecnym stanem plików; schowek zostaje. %s" % (
            (err or out).strip().splitlines() or [""])[-1][:160]
    _git(folder, ["stash", "drop", "-q", ref], timeout=60)
    return True, ""


def _refs(folder, prefix):
    code, out, _ = _git(folder, ["for-each-ref", "--format=%(refname)%09%(upstream)", prefix])
    if code != 0:
        return []
    return [tuple((line.split("\t") + [""])[:2]) for line in out.splitlines() if line.strip()]


def _count(folder, args):
    code, out, _ = _git(folder, ["rev-list", "--count"] + args)
    return int(out.strip()) if code == 0 and out.strip().isdigit() else 0


def _ahead_behind(folder, local, remote):
    code, out, _ = _git(folder, ["rev-list", "--left-right", "--count", "%s...%s" % (local, remote)])
    parts = out.split()
    if code != 0 or len(parts) != 2 or not all(x.isdigit() for x in parts):
        return 0, 0
    return int(parts[0]), int(parts[1])


def cards_linked(folder, cards_dir=""):
    """Czy karta i zadania są dowiązaniami (do kart w IntegrateSystems, gdy podano cards_dir)."""
    for name in CARD_REQUIRED:
        path = os.path.join(folder, name)
        if not os.path.islink(path):
            return False
        if cards_dir:
            real, cards = os.path.realpath(path), os.path.realpath(cards_dir)
            if os.path.commonpath([real, cards]) != cards or not os.path.exists(real):
                return False
    return True


def read_marker(folder):
    try:
        with open(os.path.join(folder, MARKER), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def is_stub(folder):
    """Folder bez kopii: brak folderu albo same dowiązania karty i plik informacji o usunięciu."""
    if not os.path.isdir(folder):
        return not os.path.lexists(folder)
    try:
        names = os.listdir(folder)
    except OSError:
        return False
    return all(n == MARKER or os.path.islink(os.path.join(folder, n)) for n in names)


def _fetched_at(folder):
    code, out, _ = _git(folder, ["rev-parse", "--git-path", "FETCH_HEAD"])
    path = out.strip()
    if code != 0 or not path:
        return ""
    path = path if os.path.isabs(path) else os.path.join(folder, path)
    try:
        return datetime.datetime.fromtimestamp(os.path.getmtime(path)).isoformat(timespec="seconds")
    except OSError:
        return ""


def origin_matches(origin, github):
    """Czy origin to repozytorium z pola github: (adres GitHuba albo adres z PANEL_GITHUB_URL)."""
    if not origin or not github:
        return False
    return repo_name(origin).lower() == github.lower() or origin.strip() == clone_url(github)


def state(folder, github="", github_branch="", cards_dir=""):
    """Stan kopii względem origin (bez pobierania z sieci). Pola opisane w dashboard/AGENCI.md."""
    gh, gb = repo_name(github), branch_name(github_branch)
    out = {"github": gh, "githubBranch": gb, "exists": os.path.isdir(folder), "repo": has_repo(folder),
           "stub": False, "removed": {}, "origin": "", "originOk": False, "branch": "", "remoteBranch": "",
           "ahead": 0, "behind": 0, "branches": [], "dirty": [], "dirtyCount": 0, "worktrees": 0,
           "fetchedAt": "", "cardsLinked": cards_linked(folder, cards_dir) if os.path.isdir(folder) else False,
           "blocks": []}
    if not out["repo"]:
        out["stub"] = bool(gh) and is_stub(folder)
        out["removed"] = read_marker(folder) if out["exists"] else {}
        out["blocks"] = ["Kopii nie ma na serwerze" if out["stub"] else "Folder nie jest repozytorium git"]
        return out
    code, origin, _ = _git(folder, ["config", "--get", "remote.origin.url"])
    origin = origin.strip() if code == 0 else ""
    out["origin"] = safe_url(origin)
    out["originOk"] = origin_matches(origin, gh)
    code, cur, _ = _git(folder, ["symbolic-ref", "--short", "-q", "HEAD"])
    out["branch"] = cur.strip() if code == 0 else ""
    remotes = {r for r, _ in _refs(folder, "refs/remotes/origin/")}
    branches = []
    for ref, upstream in _refs(folder, "refs/heads/"):
        name = ref[len("refs/heads/"):]
        remote = upstream if upstream.startswith("refs/remotes/origin/") and upstream in remotes else \
            ("refs/remotes/origin/" + name if "refs/remotes/origin/" + name in remotes else "")
        ahead, behind = _ahead_behind(folder, ref, remote) if remote else (0, 0)
        unpushed = _count(folder, [ref, "--not", "--remotes=origin"]) if remotes else _count(folder, [ref])
        branches.append({"name": name, "remote": remote[len("refs/remotes/"):] if remote else "", "ahead": ahead,
                         "behind": behind, "unpushed": unpushed, "agent": name.startswith("agent/"),
                         "current": name == out["branch"]})
    out["branches"] = branches
    cur = next((b for b in branches if b["current"]), None)
    if cur:
        out.update(remoteBranch=cur["remote"], ahead=cur["ahead"] if cur["remote"] else cur["unpushed"],
                   behind=cur["behind"])
    dirty = _dirty(folder)
    if dirty is None:
        out["blocks"].append("Nie odczytano stanu plików (git status)")
        dirty = []
    out["dirtyCount"] = len(dirty)
    out["dirty"] = [{"code": c, "path": p} for c, p in dirty[:LIST_MAX]]
    code, wt, _ = _git(folder, ["worktree", "list", "--porcelain"])
    out["worktrees"] = max(0, sum(1 for line in wt.splitlines() if line.startswith("worktree ")) - 1) if code == 0 else 0
    out["fetchedAt"] = _fetched_at(folder)
    out["blocks"] = remove_blocks(out)
    return out


def remove_blocks(st):
    """Powody, dla których kopii nie można usunąć (bez sprawdzenia pracy agenta: to dopisuje panel)."""
    out = []
    if not st.get("github"):
        out.append("Brak pola github: w karcie")
    if not st.get("repo"):
        out.append("Folder nie jest repozytorium git")
        return out
    if not st.get("origin"):
        out.append("Brak origin w repozytorium")
    elif st.get("github") and not st.get("originOk"):
        out.append("origin wskazuje inne repozytorium niż pole github:")
    if st.get("dirtyCount"):
        names = ", ".join(d["path"] for d in st["dirty"][:3])
        out.append("Pliki niezatwierdzone i nieśledzone: %d (%s%s)"
                   % (st["dirtyCount"], names, ", …" if st["dirtyCount"] > 3 else ""))
    late = [b for b in st.get("branches") or [] if b["unpushed"]]
    if late:
        out.append("Gałęzie niewysłane na GitHub: " + ", ".join(
            "%s (%d)" % (b["name"], b["unpushed"]) for b in late[:5]) + (", …" if len(late) > 5 else ""))
    if st.get("worktrees"):
        out.append("Katalogi robocze agentów w .agent/: %d" % st["worktrees"])
    if not st.get("cardsLinked"):
        out.append("KARTA.md i ZADANIA.md nie są dowiązaniami do kart w IntegrateSystems")
    return out


# ---------- sieć: pobranie i wysłanie ----------
def fetch(folder, repo=""):
    """git fetch --prune origin z limitem czasu. (True, "") albo (False, tekst)."""
    code, _, err = _git(folder, ["fetch", "--prune", "--no-tags", "origin"], timeout=_timeout(), net=True)
    if code == 0:
        return True, ""
    return False, net_error(err, repo)[1]


def push(folder, branches, repo=""):
    """Wysłanie gałęzi bez --force. Zwraca listę {"branch", "result", "message"}; result: sent, nothing, access,
    rejected, timeout, missing, error. Po kolei, bez przerywania przy błędzie jednej gałęzi (poza brakiem dostępu)."""
    results = []
    for b in branches:
        if git_check_ref(folder, b) is False:
            results.append({"branch": b, "result": "error", "message": "Nie ma gałęzi %s." % b})
            continue
        remote = "refs/remotes/origin/" + b
        has_remote = _git(folder, ["rev-parse", "--verify", "-q", remote])[0] == 0
        if has_remote and _count(folder, ["%s..refs/heads/%s" % (remote, b)]) == 0:
            results.append({"branch": b, "result": "nothing", "message": "%s: nic do wysłania." % b})
            continue
        code, up, _ = _git(folder, ["config", "--get", "branch.%s.remote" % b])
        args = ["push", "--porcelain"] + ([] if code == 0 and up.strip() else ["--set-upstream"]) + \
            ["origin", "refs/heads/%s:refs/heads/%s" % (b, b)]
        code, out, err = _git(folder, args, timeout=_timeout(), net=True)
        text = (out + "\n" + err).lower()
        if code == 0:
            if "[up to date]" in text:
                results.append({"branch": b, "result": "nothing", "message": "%s: nic do wysłania." % b})
            else:
                results.append({"branch": b, "result": "sent", "message": "%s: wysłano." % b})
            continue
        if "[rejected]" in text or "non-fast-forward" in text or "fetch first" in text or "[remote rejected]" in text:
            why = "na GitHubie są nowsze commity" if "remote rejected" not in text else "GitHub nie przyjął zmian"
            results.append({"branch": b, "result": "rejected",
                            "message": "%s: odrzucone, %s. Najpierw scal je w tej gałęzi (panel nie wysyła z --force)."
                            % (b, why)})
            continue
        kind, msg = net_error(err or out, repo)
        results.append({"branch": b, "result": kind, "message": msg})
        if kind in ("access", "timeout", "missing"):
            break
    return results


def git_check_ref(folder, b):
    if not branch_name(b):
        return False
    return _git(folder, ["rev-parse", "--verify", "-q", "refs/heads/" + b])[0] == 0


# ---------- klon na start ----------
def _exclude(folder, names):
    path = os.path.join(folder, ".git", "info", "exclude")
    try:
        text = ""
        if os.path.exists(path):
            with open(path, encoding="utf-8", errors="replace") as f:
                text = f.read()
        want = [x for x in names if x not in text.split("\n")]
        if want:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write(("" if not text or text.endswith("\n") else "\n") + "\n".join(want) + "\n")
    except OSError:
        pass


def clone(folder, github, github_branch=""):
    """Klon repozytorium do folderu projektu, gdy kopii nie ma. (True, notatka) albo (False, powód blokady).

    Folder z samymi dowiązaniami karty (po usunięciu kopii) zostaje zastąpiony klonem, a dowiązania przechodzą do
    klonu (dopisane do .git/info/exclude). Folder z innymi plikami bez repozytorium nie jest ruszany."""
    repo, br = repo_name(github), branch_name(github_branch)
    if not repo:
        return False, "Pole github: w karcie nie wskazuje repozytorium (właściciel/repozytorium)."
    if github_branch and not br:
        return False, "Pole github gałąź: w karcie ma niedozwoloną nazwę."
    with folder_lock(folder):
        if has_repo(folder):
            return True, ""
        if not is_stub(folder):
            return False, ("Folder projektu ma pliki, ale nie jest repozytorium git. Panel go nie nadpisze; "
                           "przenieś pliki albo usuń pole github: z karty.")
        parent, name = os.path.split(os.path.normpath(folder))
        tmp = os.path.join(parent, ".%s.klon-%d" % (name, os.getpid()))
        try:
            os.makedirs(parent, exist_ok=True)
            if os.path.lexists(tmp):
                shutil.rmtree(tmp)
        except OSError as e:
            return False, "Nie przygotowano miejsca na klon: %s." % (e.strerror or e)
        args = ["clone", "-q"] + (["--branch", br] if br else []) + ["--", clone_url(repo), tmp]
        code, _, err = _git(parent, args, timeout=max(_timeout(), 300), net=True)
        if code != 0:
            shutil.rmtree(tmp, ignore_errors=True)
            if br and "remote branch" in (err or "").lower() and "not found" in (err or "").lower():
                return False, "Nie sklonowano z GitHuba: na GitHubie nie ma gałęzi %s (pole github gałąź:)." % br
            return False, "Nie sklonowano z GitHuba: " + net_error(err, repo)[1]
        try:
            moved = []
            if os.path.isdir(folder):
                for n in sorted(os.listdir(folder)):
                    src = os.path.join(folder, n)
                    if n == MARKER:
                        os.unlink(src)
                    elif os.path.lexists(os.path.join(tmp, n)):
                        os.unlink(src)                      # repozytorium ma własny plik o tej nazwie
                    else:
                        os.rename(src, os.path.join(tmp, n))
                        moved.append(n)
                os.rmdir(folder)
            os.rename(tmp, folder)
        except OSError as e:
            return False, "Sklonowano, ale nie przeniesiono do folderu projektu: %s." % (e.strerror or e)
        _exclude(folder, list(EXCLUDE) + moved)
        code, cur, _ = _git(folder, ["symbolic-ref", "--short", "-q", "HEAD"])
        return True, "Sklonowano z GitHuba: %s (gałąź %s)" % (repo, cur.strip() or br or "domyślna")


# ---------- usunięcie kopii ----------
def trash_path(folder, day=None):
    parent, name = os.path.split(os.path.normpath(folder))
    base = os.path.join(parent, TRASH, "%s-%s" % (name, (day or datetime.date.today()).isoformat()))
    path, n = base, 2
    while os.path.lexists(path):
        path, n = "%s-%d" % (base, n), n + 1
    return path


def move_to_trash(folder, github, day=None):
    """Przenosi folder kopii do kosza (<nadrzędny>/.kosz/<projekt>-RRRR-MM-DD) i odtwarza folder z dowiązaniami
    karty oraz informacją o usunięciu. Wywołujący sprawdza wcześniej blokady. (True, ścieżka) albo (False, powód)."""
    dest = trash_path(folder, day)
    links = [(n, os.readlink(os.path.join(folder, n))) for n in CARD_LINKS if os.path.islink(os.path.join(folder, n))]
    try:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        os.rename(folder, dest)
    except OSError as e:
        return False, "Nie przeniesiono do kosza: %s." % (e.strerror or e)
    try:
        os.makedirs(folder)
        for n, target in links:
            os.symlink(target, os.path.join(folder, n))
        with open(os.path.join(folder, MARKER), "w", encoding="utf-8") as f:
            json.dump({"github": repo_name(github), "removedAt": datetime.datetime.now().isoformat(timespec="seconds"),
                       "trash": dest}, f, ensure_ascii=False)
            f.write("\n")
    except OSError as e:
        return False, "Kopia jest w koszu (%s), ale nie odtworzono dowiązań karty: %s." % (dest, e.strerror or e)
    return True, dest
