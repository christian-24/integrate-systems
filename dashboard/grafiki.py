"""Grafiki do postów przez Codex: generowanie i poprawianie zdjęć wbudowanym narzędziem obrazów Codex ($imagegen)
na logowaniu ChatGPT (bez klucza API). Kontrakt: AGENCI.md, sekcja „Grafiki (Codex)”.

Codex pracuje w folderze posta i zapisuje wyniki jako wariant-<n>.png obok posta. Panel niczego nie nadpisuje:
„Użyj jako grafika” odkłada poprzednią grafikę jako grafika-poprzednia-<czas>.png, „Dodaj do karuzeli” zapisuje
wariant jako kolejne zdjecie-<n>. Tu tylko pliki i polecenie; uruchomienie prowadzi agents.Manager.run_graphic.
"""
import datetime
import os
import re
import shutil
import subprocess

import udostepnij

MODES = ("codex", "wylaczone")
VARIANT = re.compile(r"^wariant-(\d{1,3})\.(png|jpe?g|webp)$", re.I)
PREVIOUS = re.compile(r"^grafika-poprzednia-\d{8}-\d{6}(?:-\d+)?\.png$")
TEXT_MIN, TEXT_MAX = 3, 1000
INPUTS_MAX = 6
VARIANTS_MAX = 4            # najwyżej tyle wariantów z jednego zlecenia
TIMEOUT = 900               # s: domyślny limit czasu zlecenia grafiki (PANEL_GRAFIKA_TIMEOUT)
SIZE_MAX = 30 * 1024 * 1024
MAGIC = {"png": (b"\x89PNG\r\n\x1a\n",), "jpg": (b"\xff\xd8\xff",), "jpeg": (b"\xff\xd8\xff",), "webp": (b"RIFF",)}
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp")


def mode(env):
    """PANEL_GRAFIKA: codex (domyślnie: grafiki robi Codex na subskrypcji ChatGPT) albo wylaczone."""
    value = str((env or {}).get("PANEL_GRAFIKA") or "codex").strip().lower()
    return value if value in MODES else "codex"


def timeout(env):
    try:
        return max(60, int(str((env or {}).get("PANEL_GRAFIKA_TIMEOUT") or TIMEOUT)))
    except ValueError:
        return TIMEOUT


def _plain(folder, name):
    path = os.path.join(folder, name)
    return os.path.isfile(path) and not os.path.islink(path)


def image_ok(path):
    """True, gdy plik jest obrazem png/jpg/webp (treść zgodna z rozszerzeniem) do 30 MB."""
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            head = f.read(12)
    except OSError:
        return False
    if not 0 < size <= SIZE_MAX or ext not in MAGIC:
        return False
    return any(head.startswith(m) for m in MAGIC[ext]) and (ext != "webp" or head[8:12] == b"WEBP")


def variants(folder):
    """Warianty posta w kolejności numerów."""
    try:
        names = [n for n in os.listdir(folder) if VARIANT.match(n) and _plain(folder, n)]
    except OSError:
        return []
    return sorted(names, key=lambda n: (int(VARIANT.match(n).group(1)), n.lower()))


def inputs(folder):
    """Obrazy posta, które można dać Codexowi: grafika, zdjęcia (karuzela), warianty, poprzednie grafiki."""
    out = ["grafika.png"] if _plain(folder, "grafika.png") else []
    out += udostepnij.photos(folder) + variants(folder)
    try:
        out += sorted((n for n in os.listdir(folder) if PREVIOUS.match(n) and _plain(folder, n)), reverse=True)
    except OSError:
        pass
    return [n for n in out if "," not in n]


def next_number(folder):
    nums = [int(VARIANT.match(n).group(1)) for n in variants(folder)]
    return (max(nums) + 1) if nums else 1


def prompt(text, names, start, folder):
    """Polecenie dla `codex exec`: obrazy wejściowe są dołączone przez --image."""
    if names:
        source = ("Zdjęcia wejściowe (dołączone do rozmowy, pliki w bieżącym folderze): %s. To materiał do edycji: "
                  "zachowaj prawdziwy wygląd produktów, ludzi i miejsc, zmień tylko to, o co prosi polecenie."
                  % ", ".join(names))
    else:
        source = "Bez zdjęć wejściowych: przygotuj nowy obraz według polecenia."
    last = start + VARIANTS_MAX - 1
    return "\n".join([
        "Przygotuj grafikę do posta w mediach społecznościowych. Użyj wbudowanego narzędzia obrazów ($imagegen). "
        "Nie używaj klucza API ani skryptów wymagających OPENAI_API_KEY.",
        "",
        "Polecenie właściciela: „%s”" % text,
        source,
        "",
        "Zasady:",
        "- Każdy gotowy obraz zapisz w bieżącym folderze (%s) jako PNG pod nazwą wariant-<n>.png, od n=%d "
        "(wariant-%d.png, wariant-%d.png …, najwyżej do wariant-%d.png). Domyślnie jeden wariant; kilka tylko wtedy, "
        "gdy polecenie o nie prosi." % (folder, start, start, start + 1, last),
        "- Narzędzie zapisuje obrazy w $CODEX_HOME/generated_images/: skopiuj wynik stamtąd do bieżącego folderu "
        "pod nazwą wariantu.",
        "- Nie nadpisuj, nie zmieniaj i nie usuwaj istniejących plików (grafika.png, zdjęcia, warianty, post.md, film). "
        "Zapisuj tylko nowe pliki wariant-<n>.png.",
        "- Gdy polecenie podaje format (np. 4:5, 1:1, 9:16), dopasuj do niego kadr.",
        "- Nie dodawaj napisów ani logo, chyba że polecenie o to prosi.",
        "- Niczego nie publikuj i nie wysyłaj.",
        "- Na koniec odpowiedz po polsku jednym krótkim zdaniem na każdy wariant: co zmieniłeś.",
    ]) + "\n"


def codex_home(env, agent_user=""):
    """Katalog danych Codex użytkownika, który uruchamia agentów (PANEL_CODEX_HOME, CODEX_HOME albo ~/.codex)."""
    explicit = str((env or {}).get("PANEL_CODEX_HOME") or "").strip()
    if explicit:
        return os.path.expanduser(explicit)
    if agent_user:
        home = os.path.expanduser("~" + agent_user)
        return os.path.join(home, ".codex") if not home.startswith("~") else ""
    return os.path.expanduser(str((env or {}).get("CODEX_HOME") or "~/.codex"))


def collect(folder, start, since, generated=""):
    """Nowe warianty po zleceniu. Gdy Codex nie skopiował obrazu do folderu posta, panel bierze nowe obrazy z
    katalogu sesji w generated_images (generated: ścieżka katalogu sesji) i zapisuje je jako kolejne warianty.
    Pliki niebędące obrazem odrzuca. Zwraca listę nazw."""
    made = []
    for n in variants(folder):
        path = os.path.join(folder, n)
        if int(VARIANT.match(n).group(1)) < start:
            continue
        if image_ok(path):
            made.append(n)
        else:
            try:
                os.remove(path)
            except OSError:
                pass
    if made or not generated or not os.path.isdir(generated):
        return made
    try:
        found = sorted((os.path.join(generated, n) for n in os.listdir(generated)
                        if os.path.splitext(n)[1].lower() in IMAGE_EXT), key=os.path.getmtime)
    except OSError:
        return made
    for src in found:
        try:
            if os.path.getmtime(src) < since - 1 or not image_ok(src) or len(made) >= VARIANTS_MAX:
                continue
            name = "wariant-%d%s" % (next_number(folder), os.path.splitext(src)[1].lower().replace(".jpeg", ".jpg"))
            _copy(src, os.path.join(folder, name))
            made.append(name)
        except OSError:
            continue
    return made


def _copy(src, dst):
    tmp = os.path.join(os.path.dirname(dst), ".%s.tmp" % os.path.basename(dst))
    shutil.copyfile(src, tmp)
    os.replace(tmp, dst)


def _convert(src, dst):
    """Zmiana formatu przez ffmpeg (jpg/webp → png albo webp → jpg). False, gdy się nie da."""
    if not shutil.which("ffmpeg"):
        return False
    tmp = os.path.join(os.path.dirname(dst), ".tmp-%s" % os.path.basename(dst))
    try:
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-frames:v", "1", tmp], check=True, timeout=60,
                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.replace(tmp, dst)
        return True
    except (OSError, subprocess.SubprocessError):
        try:
            os.remove(tmp)
        except OSError:
            pass
        return False


def _free(folder, base, ext):
    name, n = base + ext, 2
    while os.path.lexists(os.path.join(folder, name)):
        name, n = "%s-%d%s" % (base, n, ext), n + 1
    return name


def _check(folder, name):
    if not VARIANT.match(str(name or "")) or not _plain(folder, name):
        return "Nie ma takiego wariantu. Odświeżam."
    return ""


def use_as_graphic(folder, name):
    """Wariant staje się grafika.png; poprzednia grafika (i grafika.svg) zostaje jako grafika-poprzednia-<czas>.
    (kod, błąd, dane)."""
    bad = _check(folder, name)
    if bad:
        return 409, bad, {}
    src = os.path.join(folder, name)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    base = "grafika-poprzednia-" + stamp
    png = os.path.join(folder, "grafika.png")
    new_png = src.lower().endswith(".png")
    staged = os.path.join(folder, ".grafika-nowa.png")
    if new_png:
        _copy(src, staged)
    elif not _convert(src, staged):
        return 400, "Ten wariant nie jest w formacie PNG, a na tym komputerze brakuje programu do zmiany formatu " \
                    "(ffmpeg). Poproś Codexa o wersję PNG.", {}
    kept = ""
    if _plain(folder, "grafika.png"):
        kept = _free(folder, base, ".png")
        os.replace(png, os.path.join(folder, kept))
    if _plain(folder, "grafika.svg"):           # inaczej panel odtworzy grafika.png z SVG
        os.replace(os.path.join(folder, "grafika.svg"), os.path.join(folder, _free(folder, base, ".svg")))
    os.replace(staged, png)
    os.remove(src)
    return 200, "", {"previous": kept}


def add_to_carousel(folder, name):
    """Wariant jako kolejne zdjęcie karuzeli (zdjecie-<n>.png|jpg). (kod, błąd, dane)."""
    bad = _check(folder, name)
    if bad:
        return 409, bad, {}
    nums = [int(udostepnij.PHOTO.match(n).group(1) or 0) for n in udostepnij.photos(folder)]
    num = (max(nums) + 1) if nums else 1
    ext = os.path.splitext(name)[1].lower().replace(".jpeg", ".jpg")
    src = os.path.join(folder, name)
    if ext == ".webp":
        target = _free(folder, "zdjecie-%d" % num, ".jpg")
        if not _convert(src, os.path.join(folder, target)):
            return 400, "Ten wariant jest w formacie WebP, a na tym komputerze brakuje programu do zmiany formatu " \
                        "(ffmpeg). Poproś Codexa o wersję PNG.", {}
        os.remove(src)
    else:
        target = _free(folder, "zdjecie-%d" % num, ext)
        os.replace(src, os.path.join(folder, target))
    if len(udostepnij.photos(folder)) + 1 > udostepnij.MAX_FILES:
        return 200, "", {"name": target, "note": "Instagram przyjmie najwyżej %d plików w karuzeli."
                                                 % udostepnij.MAX_FILES}
    return 200, "", {"name": target}


def remove(folder, name):
    bad = _check(folder, name)
    if bad:
        return 409, bad, {}
    os.remove(os.path.join(folder, name))
    return 200, "", {}
