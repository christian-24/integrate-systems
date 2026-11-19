"""Nagrywanie filmu z prawdziwej strony według scenariusza (bez człowieka przed ekranem).

Scenariusz: <folder posta>/scenariusz.json
  {"url": "https://opisarnia.pl/generator", "logowanie": "https://opisarnia.pl/logowanie", "kroki": [krok, …]}
  "logowanie" (opcjonalnie): przed nagraniem logowanie kontem demo z pliku PANEL_FILM_KONTO
  (domyślnie ~/dane/film/konto.json: {"email", "haslo"}; wpisuje go właściciel w panelu, pliki 0600).
Krok (klucze opcjonalne, wykonywane w tej kolejności):
  "napis": tekst na dole filmu od tego kroku do następnego napisu
  "wpisz": [selektor, tekst]       pisanie znak po znaku
  "wybierz": [selektor, wartość]   lista rozwijana
  "kliknij": selektor              kliknięcie z podświetleniem
  "przewin": selektor              przewinięcie do elementu
  "rozwin": selektor               rozwinięcie <details>, gdy jest zwinięte
  "czekaj_na": selektor            czekanie, aż element się pojawi ("limit": sekundy, domyślnie 60)
  "pauza": sekundy
Wynik: <folder posta>/film.mp4, pion 1080×1920, 30 kl./s, napisy wtopione; stan w .film-stan.json.

Uruchamiane osobnym interpreterem z Playwright (PANEL_FILM_PYTHON, domyślnie ~/narzedzia/film/bin/python):
  python film.py nagraj <folder posta>
Panel woła to przez Recorder (bez Playwright w procesie panelu).
"""
import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time

SCENARIO = "scenariusz.json"
STATE = ".film-stan.json"
VIEW = (540, 960)                 # CSS px; nagranie 2× = 1080×1920
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
TIMEOUT = 600


def account_file():
    return os.path.expanduser(os.environ.get("PANEL_FILM_KONTO", "").strip() or "~/dane/film/konto.json")


def save_account(email, password):
    """Konto demo do nagrań: zapis 0600; hasło nigdy nie wraca do panelu."""
    path = account_file()
    os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
    fd = os.open(path + ".tmp", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump({"email": email, "haslo": password}, f)
    os.replace(path + ".tmp", path)


def account_email():
    try:
        with open(account_file(), encoding="utf-8") as f:
            return json.load(f).get("email", "")
    except (OSError, ValueError):
        return ""

# kursor i podświetlenie kliknięć: w nagraniu headless nie ma kursora systemowego
CURSOR_JS = """
(() => {
  const add = () => {
    if (document.getElementById('__kursor')) return;
    const c = document.createElement('div'); c.id = '__kursor';
    c.style.cssText = 'position:fixed;z-index:2147483647;width:22px;height:22px;border-radius:50%;' +
      'background:rgba(199,154,62,.85);border:2px solid #fff;box-shadow:0 0 0 1px rgba(0,0,0,.35);' +
      'pointer-events:none;transform:translate(-50%,-50%);left:-50px;top:-50px;transition:left .25s,top .25s';
    document.documentElement.appendChild(c);
    addEventListener('mousemove', e => { c.style.left = e.clientX + 'px'; c.style.top = e.clientY + 'px'; }, true);
    addEventListener('mousedown', e => {
      const r = document.createElement('div');
      r.style.cssText = 'position:fixed;z-index:2147483646;width:16px;height:16px;border-radius:50%;' +
        'border:3px solid #9e5f18;pointer-events:none;transform:translate(-50%,-50%);transition:all .5s ease-out;' +
        'left:' + e.clientX + 'px;top:' + e.clientY + 'px;opacity:1';
      document.documentElement.appendChild(r);
      requestAnimationFrame(() => { r.style.width = '70px'; r.style.height = '70px'; r.style.opacity = '0'; });
      setTimeout(() => r.remove(), 600);
    }, true);
  };
  if (document.readyState === 'loading') addEventListener('DOMContentLoaded', add); else add();
})();
"""


def write_state(folder, **state):
    state["at"] = datetime.datetime.now().isoformat(timespec="seconds")
    tmp = os.path.join(folder, STATE + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)
    os.replace(tmp, os.path.join(folder, STATE))


def read_state(folder):
    try:
        with open(os.path.join(folder, STATE), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def record(folder):
    """Nagrywa scenariusz do film.mp4. Zwraca ścieżkę filmu; błąd: wyjątek z opisem po polsku."""
    from playwright.sync_api import sync_playwright
    with open(os.path.join(folder, SCENARIO), encoding="utf-8") as f:
        sc = json.load(f)
    work = tempfile.mkdtemp(prefix="film-")
    captions, t0 = [], None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            ctx = browser.new_context(viewport={"width": VIEW[0], "height": VIEW[1]}, device_scale_factor=2,
                                      locale="pl-PL", record_video_dir=work,
                                      record_video_size={"width": VIEW[0] * 2, "height": VIEW[1] * 2})
            ctx.add_init_script(CURSOR_JS)
            page = ctx.new_page()
            if sc.get("logowanie"):
                try:
                    with open(account_file(), encoding="utf-8") as f:
                        acc = json.load(f)
                except (OSError, ValueError):
                    raise RuntimeError("brak konta demo do nagrań (panel: Agenci → Publikacja → Konto do nagrań)")
                page.goto(sc["logowanie"], wait_until="networkidle", timeout=60000)
                page.fill("#lg-email", acc["email"])
                page.fill("#lg-pass", acc["haslo"])
                page.locator("button[type=submit]").first.click()
                try:
                    page.wait_for_url(lambda u: "/logowanie" not in u, timeout=20000)
                except Exception:  # noqa: BLE001
                    raise RuntimeError("logowanie kontem demo nie powiodło się (sprawdź e-mail i hasło)")
            page.goto(sc["url"], wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(800)
            t0 = time.monotonic()           # początek filmu: strona już wczytana
            page.mouse.move(VIEW[0] / 2, VIEW[1] / 3)
            for i, k in enumerate(sc.get("kroki") or []):
                if k.get("napis"):
                    captions.append([time.monotonic() - t0, str(k["napis"])])
                try:
                    if k.get("rozwin"):
                        page.locator(k["rozwin"]).first.evaluate("el => { el.open = true }")
                        page.wait_for_timeout(300)
                    if k.get("przewin"):
                        page.locator(k["przewin"]).first.scroll_into_view_if_needed(timeout=10000)
                        page.wait_for_timeout(400)
                    if k.get("wpisz"):
                        sel, text = k["wpisz"]
                        loc = page.locator(sel).first
                        loc.scroll_into_view_if_needed(timeout=10000)
                        loc.click(timeout=10000)
                        loc.press_sequentially(str(text), delay=55)
                    if k.get("wybierz"):
                        sel, value = k["wybierz"]
                        loc = page.locator(sel).first
                        loc.scroll_into_view_if_needed(timeout=10000)
                        loc.click(timeout=10000)
                        loc.select_option(str(value), timeout=10000)
                    if k.get("kliknij"):
                        loc = page.locator(k["kliknij"]).first
                        loc.scroll_into_view_if_needed(timeout=10000)
                        page.wait_for_timeout(250)
                        loc.click(timeout=15000)
                    if k.get("czekaj_na"):
                        page.locator(k["czekaj_na"]).first.wait_for(timeout=int(float(k.get("limit", 60)) * 1000))
                    page.wait_for_timeout(int(float(k.get("pauza", 0.6)) * 1000))
                except Exception as e:  # noqa: BLE001
                    try:                    # zrzut ekranu z chwili błędu: łatwiej poprawić scenariusz
                        page.screenshot(path=os.path.join(folder, ".film-blad.png"), full_page=True)
                    except Exception:  # noqa: BLE001
                        pass
                    raise RuntimeError("krok %d (%s): %s" % (i + 1, k.get("napis") or k.get("kliknij") or k.get("wpisz"),
                                                           str(e).split("\n")[0][:200]))
            end = time.monotonic() - t0
            video = page.video.path()
            ctx.close()
            browser.close()
        out = os.path.join(folder, "film.mp4")
        render(video, out, captions, end, work)
        return out
    finally:
        shutil.rmtree(work, ignore_errors=True)


def render(src, out, captions, end, work):
    """Przycięcie początku (wczytywanie strony), napisy wtopione, H.264 1080×1920 30 kl./s."""
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src],
                           capture_output=True, text=True)
    total = float(probe.stdout.strip() or 0)
    lead = max(0.0, total - end - 0.2)    # nagranie zaczyna się przed t0 (wczytywanie strony): odcinamy
    filters = ["scale=1080:1920:flags=lanczos", "fps=30"]
    for n, (at, text) in enumerate(captions):
        stop = captions[n + 1][0] if n + 1 < len(captions) else end + 1
        path = os.path.join(work, "napis-%d.txt" % n)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        filters.append("drawtext=fontfile=%s:textfile=%s:fontsize=46:fontcolor=white:box=1:boxcolor=0x2b1d12@0.82:"
                       "boxborderw=22:x=(w-text_w)/2:y=h-300:line_spacing=10:enable='between(t,%.2f,%.2f)'"
                       % (FONT, path, at, stop))
    cmd = ["ffmpeg", "-y", "-v", "error", "-ss", "%.2f" % lead, "-i", src, "-vf", ",".join(filters), "-an",
           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("montaż: " + (r.stderr.strip().splitlines() or ["ffmpeg"])[-1][:200])


class Recorder:
    """Uruchamia nagranie w tle osobnym interpreterem; stan w .film-stan.json folderu posta."""

    def __init__(self, notify=None, python=None, script=None):
        self.notify = notify or (lambda text: None)
        self.python = os.path.expanduser(python or os.environ.get("PANEL_FILM_PYTHON", "").strip()
                                         or "~/narzedzia/film/bin/python")
        self.script = script or os.path.abspath(__file__)
        self.lock = threading.Lock()
        self.busy = set()

    def available(self):
        return os.path.isfile(self.python) and bool(shutil.which("ffmpeg"))

    def start(self, folder, title=""):
        if not folder:
            return 404, "Nie ma posta na ten dzień."
        if not os.path.isfile(os.path.join(folder, SCENARIO)):
            return 409, "Post nie ma scenariusza filmu (scenariusz.json)."
        if not self.available():
            return 409, "Na serwerze nie ma narzędzi do nagrywania (Playwright, ffmpeg)."
        with self.lock:
            if folder in self.busy:
                return 409, "Film już się nagrywa."
            self.busy.add(folder)
        write_state(folder, state="running", error="")
        threading.Thread(target=self._run, args=(folder, title), daemon=True).start()
        return 202, "", {"state": "running"}

    def _run(self, folder, title):
        try:
            r = subprocess.run([self.python, self.script, "nagraj", folder], capture_output=True, text=True,
                               timeout=TIMEOUT)
            ok = r.returncode == 0
            err = "" if ok else ((r.stderr or r.stdout).strip().splitlines() or ["nieznany błąd"])[-1][:300]
        except subprocess.TimeoutExpired:
            ok, err = False, "nagrywanie trwało ponad 10 minut"
        write_state(folder, state="done" if ok else "error", error=err)
        with self.lock:
            self.busy.discard(folder)
        self.notify(("Film nagrany: %s. Obejrzyj go w poście." % (title or os.path.basename(folder))) if ok
                    else "Nie nagrano filmu (%s): %s" % (title or os.path.basename(folder), err))


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "nagraj":
        try:
            print(record(sys.argv[2]))
        except Exception as e:  # noqa: BLE001
            print("Błąd nagrania: %s" % e, file=sys.stderr)
            sys.exit(1)
    else:
        print("użycie: film.py nagraj <folder posta>", file=sys.stderr)
        sys.exit(2)
