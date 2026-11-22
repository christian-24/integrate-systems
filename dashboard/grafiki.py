"""Grafiki do postów przez Codex na logowaniu ChatGPT (bez klucza API). Kontrakt: AGENCI.md, sekcja „Grafiki (Codex)”.

Dwa tryby: „zachowaj” (domyślny: klasyczna obróbka zdjęcia skryptem Pythona z Pillow, bez generowania, ten sam kadr
i obiekty) i „nowa” (wbudowane narzędzie obrazów $imagegen). Codex pracuje w folderze posta i zapisuje wynik jako
wariant-<n>.png. Rozmowa o grafice (polecenia, odpowiedzi, oczekująca wersja) leży w .grafika-rozmowa.json obok posta;
kolejne polecenie poprawia ostatnią wersję. „Zaakceptuj” podmienia grafikę (albo zdjęcie karuzeli), poprzednia zostaje
jako grafika-poprzednia-<czas>; „Odrzuć” usuwa wersję. Uruchomienie prowadzi agents.Manager.run_graphic.
"""
import datetime
import json
import os
import re
import shutil
import struct
import subprocess
import threading

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
CHAT = ".grafika-rozmowa.json"   # rozmowa o grafice posta (ukryty plik obok post.md)
CHAT_MAX = 60                    # najwyżej tyle wpisów rozmowy
TRYBY = ("zachowaj", "nowa")     # zachowaj: obróbka zdjęcia bez generowania (domyślnie); nowa: $imagegen
RATIO_TOL = 0.015                # dopuszczalna różnica proporcji wyniku i źródła w trybie „zachowaj”
DONE_REPLY = "Gotowe: nowa wersja w podglądzie."
# prośba o zmianę kadru albo formatu: wtedy wynik może mieć inne proporcje niż źródło
CROP = re.compile(r"przytn|przyci|kadr|\b\d{1,2}\s*[:x×/]\s*\d{1,2}\b|format|kwadrat|pionow|w pion|do pionu|poziomo|"
                  r"w poziom|obr[oó][cć]|"
                  r"wyprost|panoram", re.I)
_chat_lock = threading.RLock()


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
    return "\n".join([
        "Przygotuj grafikę do posta w mediach społecznościowych. Użyj wbudowanego narzędzia obrazów ($imagegen). "
        "Nie używaj klucza API ani skryptów wymagających OPENAI_API_KEY.",
        "",
        "Polecenie właściciela: „%s”" % text,
        source,
        "",
        "Zasady:",
        "- Gotowy obraz zapisz w bieżącym folderze (%s) jako PNG pod nazwą wariant-%d.png (od n=%d). Jeden obraz: "
        "panel pokaże go właścicielowi jako nową wersję." % (folder, start, start),
        "- Narzędzie zapisuje obrazy w $CODEX_HOME/generated_images/: skopiuj wynik stamtąd do bieżącego folderu "
        "pod nazwą wariantu.",
        "- Nie nadpisuj, nie zmieniaj i nie usuwaj istniejących plików (grafika.png, zdjęcia, warianty, post.md, film). "
        "Zapisuj tylko nowe pliki wariant-<n>.png.",
        "- Gdy polecenie podaje format (np. 4:5, 1:1, 9:16), dopasuj do niego kadr.",
        "- Nie dodawaj napisów ani logo, chyba że polecenie o to prosi.",
        "- Niczego nie publikuj i nie wysyłaj.",
        "- Na koniec odpowiedz po polsku jednym krótkim zdaniem na każdy wariant: co zmieniłeś. Bez ścieżek i nazw "
        "plików.",
    ]) + "\n"


def crop_asked(text):
    """True, gdy polecenie prosi o kadr, format albo obrót (wynik może mieć inne proporcje)."""
    return bool(CROP.search(str(text or "")))


def prompt_keep(text, name, start, folder):
    """Polecenie trybu „zachowaj”: klasyczna obróbka jednego zdjęcia skryptem Pythona z Pillow, bez generowania."""
    crop = crop_asked(text)
    return "\n".join([
        "Przygotuj grafikę do posta w mediach społecznościowych przez klasyczną obróbkę zdjęcia.",
        "",
        "Polecenie właściciela: „%s”" % text,
        "Zdjęcie źródłowe (dołączone do rozmowy, plik w bieżącym folderze): %s." % name,
        "",
        "Zasady (obowiązkowe):",
        "- To ma być TO SAMO zdjęcie: te same obiekty, ludzie, tło, ujęcie, perspektywa i kadr. Niczego nie dodawaj, "
        "nie usuwaj, nie przesuwaj i nie dorysowuj.",
        "- NIE generuj obrazu i nie edytuj go modelem AI: nie używaj wbudowanego narzędzia obrazów ani żadnego "
        "generatora czy usługi w sieci.",
        "- Obrób zdjęcie skryptem Pythona z biblioteką Pillow (PIL), uruchomionym wprost (python3 - <<'EOF' … EOF), "
        "bez zapisywania skryptu w folderze posta. Najpierw ImageOps.exif_transpose. Dozwolone: wyostrzenie "
        "(ImageFilter.UnsharpMask), redukcja szumu (np. ImageFilter.MedianFilter albo lekkie rozmycie z maską), "
        "kontrast, jasność i ekspozycja, nasycenie (ImageEnhance), balans bieli (skalowanie kanałów RGB), korekta "
        "krzywych.",
        ("- Polecenie prosi o kadr, format albo prostowanie: zmień kadr dokładnie tak, jak prosi, bez dodawania treści."
         if crop else
         "- Nie kadruj, nie obracaj i nie zmieniaj proporcji: wynik ma te same proporcje co zdjęcie źródłowe."),
        "- Wynik zapisz jako PNG w bieżącym folderze (%s) pod nazwą wariant-%d.png (od n=%d), "
        "Image.save(..., optimize=True). Jeden plik." % (folder, start, start),
        "- Nie nadpisuj, nie zmieniaj i nie usuwaj istniejących plików (grafika.png, zdjęcia, warianty, post.md, film).",
        "- Niczego nie publikuj i nie wysyłaj.",
        "- Na koniec odpowiedz po polsku jednym krótkim zdaniem: co zmieniłeś. Bez ścieżek i nazw plików.",
    ]) + "\n"


def image_size(path):
    """(szerokość, wysokość) obrazu PNG, JPG (z obrotem z EXIF) albo WebP bez bibliotek; None, gdy nie da się."""
    try:
        with open(path, "rb") as f:
            head = f.read(32)
            if head.startswith(b"\x89PNG\r\n\x1a\n") and head[12:16] == b"IHDR":
                return struct.unpack(">II", head[16:24])
            if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
                kind = head[12:16]
                if kind == b"VP8X":
                    return (int.from_bytes(head[24:27], "little") + 1, int.from_bytes(head[27:30], "little") + 1)
                if kind == b"VP8L":
                    b = int.from_bytes(head[21:25], "little")
                    return ((b & 0x3FFF) + 1, ((b >> 14) & 0x3FFF) + 1)
                if kind == b"VP8 ":
                    w, h = struct.unpack("<HH", head[26:30])
                    return (w & 0x3FFF, h & 0x3FFF)
                return None
            if head[:2] == b"\xff\xd8":
                f.seek(2)
                return _jpeg_size(f)
    except (OSError, struct.error):
        return None
    return None


def _jpeg_size(f):
    orient = 1
    while True:
        b = f.read(1)
        while b and b != b"\xff":
            b = f.read(1)
        while b == b"\xff":
            b = f.read(1)
        if not b:
            return None
        m = b[0]
        if m in (0xD8, 0x01) or 0xD0 <= m <= 0xD7:
            continue
        if m in (0xD9, 0xDA):
            return None
        length = struct.unpack(">H", f.read(2))[0]
        if m in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            h, w = struct.unpack(">xHH", f.read(5))
            return (h, w) if orient in (5, 6, 7, 8) else (w, h)
        data = f.read(length - 2)
        if m == 0xE1 and data[:6] == b"Exif\x00\x00":
            orient = _exif_orientation(data[6:]) or orient


def _exif_orientation(t):
    try:
        e = "<" if t[:2] == b"II" else ">"
        off = struct.unpack(e + "I", t[4:8])[0]
        count = struct.unpack(e + "H", t[off:off + 2])[0]
        for i in range(count):
            p = off + 2 + 12 * i
            if struct.unpack(e + "H", t[p:p + 2])[0] == 0x0112:
                return struct.unpack(e + "H", t[p + 8:p + 10])[0]
    except struct.error:
        return 0
    return 0


def same_ratio(a, b):
    """True, gdy dwa rozmiary mają te same proporcje (z tolerancją RATIO_TOL)."""
    if not a or not b or not a[1] or not b[1]:
        return False
    ra, rb = a[0] / a[1], b[0] / b[1]
    return abs(ra - rb) / ra <= RATIO_TOL


def new_images(where, since):
    """Obrazy zapisane w katalogu (np. sesji generated_images) od chwili since."""
    if not where or not os.path.isdir(where):
        return []
    out = []
    for root, _, files in os.walk(where):
        for n in files:
            p = os.path.join(root, n)
            try:
                if os.path.splitext(n)[1].lower() in IMAGE_EXT and os.path.getmtime(p) >= since - 1:
                    out.append(p)
            except OSError:
                continue
    return out


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


# ---------- rozmowa o grafice: polecenia właściciela, odpowiedzi, oczekująca wersja ----------
def _now():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def chat_read(folder):
    """Rozmowa posta: {"items": [...], "pending": nazwa wersji czekającej na decyzję albo "", "source": plik, który
    wersja zastąpi po akceptacji ("" albo grafika.png: grafika posta; zdjecie-<n>: to zdjęcie karuzeli)}."""
    try:
        with open(os.path.join(folder, CHAT), encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    items = [x for x in data.get("items") or [] if isinstance(x, dict)]
    pending = str(data.get("pending") or "")
    if pending and (not VARIANT.match(pending) or not _plain(folder, pending)):
        pending = ""
    return {"items": items, "pending": pending, "source": str(data.get("source") or "")}


def chat_write(folder, data):
    data = dict(data, items=(data.get("items") or [])[-CHAT_MAX:])
    path = os.path.join(folder, CHAT)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def sources(folder):
    """Obrazy posta, które można poprawiać: grafika.png i zdjęcia karuzeli."""
    return (["grafika.png"] if _plain(folder, "grafika.png") else []) + udostepnij.photos(folder)


def chat_base(folder, wanted=""):
    """(obraz wejściowy, źródło) dla nowego polecenia: oczekująca wersja (iteracja), inaczej wskazany obraz posta,
    inaczej grafika albo pierwsze zdjęcie; ("", "") gdy post nie ma obrazu."""
    with _chat_lock:
        chat = chat_read(folder)
    if chat["pending"]:
        return chat["pending"], chat["source"]
    cands = sources(folder)
    pick = wanted if wanted in cands else (cands[0] if cands else "")
    return pick, pick


def chat_start(folder, run_id, text, mode, name, source):
    """Nowe polecenie w rozmowie (stan „w toku”)."""
    with _chat_lock:
        chat = chat_read(folder)
        if not chat["pending"]:
            chat["source"] = source
        chat["items"].append({"id": run_id, "at": _now(), "text": text, "mode": mode, "input": name,
                              "state": "run", "reply": "", "version": ""})
        chat_write(folder, chat)


def clean_reply(text):
    """Krótka odpowiedź Codexa dla właściciela: pierwsze zdanie, bez ścieżek i nazw plików; "" gdy się nie da."""
    s = re.sub(r"\s+", " ", str(text or "")).strip()
    s = re.split(r"(?<=[.!?])\s", s, maxsplit=1)[0][:160]
    if not s or re.search(r"[/\\~$`]|\b[\w-]+\.(png|jpe?g|webp|py|md|json|svg)\b|\bwariant-\d", s, re.I):
        return ""
    return s


RUN_ERRORS = {"login": "Codex wymaga ponownego logowania (Agenci).",
              "limit": "Limit subskrypcji ChatGPT. Spróbuj później.",
              "timeout": "Przekroczony czas. Spróbuj jeszcze raz.", "stopped": "Zatrzymane.",
              "unknown": "Przerwane. Wyślij polecenie jeszcze raz."}


def _drop(folder, names):
    for n in names:
        try:
            os.remove(os.path.join(folder, n))
        except OSError:
            pass


def chat_finish(folder, run_id, made, state, error, result, generated="", since=0.0):
    """Koniec polecenia: sprawdza wynik i ustawia oczekującą wersję. W trybie „zachowaj” odrzuca wynik z generowania
    (nowy obraz w katalogu sesji generated_images) i wynik o innych proporcjach niż źródło (gdy nie proszono o kadr).
    Zwraca (stan, błąd, wynik, wersja) dla uruchomienia."""
    with _chat_lock:
        chat = chat_read(folder)
        item = next((x for x in reversed(chat["items"]) if x.get("id") == run_id), None)
        if item is None:
            return state, error, result, ""
        bad = ""
        if state != "done":
            why = clean_reply(error)
            bad = RUN_ERRORS.get(state) or ("Nie wyszło: " + why if why else
                                            "Nie wyszło. Spróbuj jeszcze raz albo zmień polecenie.")
        elif item.get("mode") == "zachowaj" and new_images(generated, since):
            bad = "Odrzucone: Codex wygenerował nowy obraz zamiast poprawić zdjęcie. Wyślij polecenie jeszcze raz."
        elif not made:
            bad = "Codex nie zapisał obrazu. Spróbuj jeszcze raz albo zmień polecenie."
        out = made[0] if made and not bad else ""
        if out and item.get("mode") == "zachowaj" and not crop_asked(item.get("text")):
            src = image_size(os.path.join(folder, item.get("input") or ""))
            got = image_size(os.path.join(folder, out))
            if src and not got:
                bad, out = "Odrzucone: wynik nie jest poprawnym obrazem.", ""
            elif src and not same_ratio(src, got):
                bad = ("Odrzucone: wynik ma inne proporcje niż zdjęcie (%d×%d zamiast %d×%d). Jeśli chcesz inny kadr, "
                       "napisz np. „przytnij do 4:5”." % (got + src))
                out = ""
        _drop(folder, [n for n in made if n != out])
        if bad:
            item.update(state="error", reply=bad)
            chat_write(folder, chat)
            return ("error" if state == "done" else state), (bad if state == "done" else error), "", ""
        if chat["pending"] and chat["pending"] != out:          # poprzednia wersja tej rozmowy: zastąpiona
            _drop(folder, [chat["pending"]])
        chat["pending"] = out
        note = clean_reply(result)
        item.update(state="ok", version=out, reply=DONE_REPLY + (" " + note if note else ""))
        chat_write(folder, chat)
        return state, error, item["reply"], out


def chat_settle(folder, live):
    """Polecenia „w toku” bez żywego uruchomienia (np. po ponownym starcie panelu) oznacza jako przerwane.
    live(id) -> True, gdy uruchomienie trwa. Pomija wpisy młodsze niż 30 s (zlecenie właśnie powstaje)."""
    with _chat_lock:
        chat = chat_read(folder)
        cut = datetime.datetime.now().astimezone() - datetime.timedelta(seconds=30)
        changed = False
        for x in chat["items"]:
            if x.get("state") != "run" or live(x.get("id")):
                continue
            try:
                young = datetime.datetime.fromisoformat(str(x.get("at"))) > cut
            except (TypeError, ValueError):
                young = False
            if not young:
                x.update(state="error", reply=RUN_ERRORS["unknown"])
                changed = True
        if changed:
            chat_write(folder, chat)


def chat_public(folder):
    """Rozmowa dla edytora posta: bez nazw plików wejściowych; wersja z czasem (odświeżenie podglądu) i rozmiarem."""
    with _chat_lock:
        chat = chat_read(folder)
    items = [{k: x.get(k) for k in ("at", "text", "mode", "state", "reply", "action") if x.get(k) is not None}
             for x in chat["items"]]
    pend = None
    if chat["pending"]:
        path = os.path.join(folder, chat["pending"])
        size = image_size(path) or (0, 0)
        pend = {"name": chat["pending"], "at": int(os.path.getmtime(path)), "w": size[0], "h": size[1]}
    src = chat["source"] if chat["source"] in sources(folder) else ""
    return {"items": items, "pending": pend, "source": src}


def _close(folder, chat, action):
    chat["pending"] = ""
    chat["items"].append({"at": _now(), "action": action})
    chat_write(folder, chat)


def _check_pending(chat, name):
    if not chat["pending"] or chat["pending"] != str(name or ""):
        return "Ta wersja jest już nieaktualna. Odświeżam."
    return ""


def _replace_photo(folder, photo, name):
    """Zdjęcie karuzeli zastąpione wersją: zdjecie-<n>.png; poprzednie zostaje jako grafika-poprzednia-<czas>-<nazwa>."""
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    stem, ext = os.path.splitext(photo)
    new_ext = os.path.splitext(name)[1].lower().replace(".jpeg", ".jpg")
    if new_ext == ".webp":
        return 400, "Ta wersja jest w formacie WebP. Poproś Codexa o wersję PNG.", {}
    kept = _free(folder, "grafika-poprzednia-%s-%s" % (stamp, stem), ext)
    os.replace(os.path.join(folder, photo), os.path.join(folder, kept))
    target = stem + new_ext
    if os.path.lexists(os.path.join(folder, target)):
        target = _free(folder, stem + "-nowe", new_ext)
    os.replace(os.path.join(folder, name), os.path.join(folder, target))
    return 200, "", {"previous": kept, "name": target}


def accept(folder, name):
    """„Zaakceptuj”: oczekująca wersja zastępuje grafikę posta (albo zdjęcie karuzeli, z którego powstała)."""
    with _chat_lock:
        chat = chat_read(folder)
        bad = _check_pending(chat, name)
        if bad:
            return 409, bad, {}
        src = chat["source"]
        if src and src != "grafika.png" and udostepnij.PHOTO.match(src) and _plain(folder, src):
            code, err, extra = _replace_photo(folder, src, chat["pending"])
        else:
            code, err, extra = use_as_graphic(folder, chat["pending"])
        if code == 200:
            _close(folder, chat, "akceptuj")
        return code, err, extra


def reject(folder, name):
    """„Odrzuć”: usuwa oczekującą wersję; następne polecenie poprawia aktualną grafikę posta."""
    with _chat_lock:
        chat = chat_read(folder)
        bad = _check_pending(chat, name)
        if bad:
            return 409, bad, {}
        _drop(folder, [chat["pending"]])
        _close(folder, chat, "odrzuc")
        return 200, "", {}


def to_carousel(folder, name):
    """Oczekująca wersja jako kolejne zdjęcie karuzeli (menu ⋯ edytora)."""
    with _chat_lock:
        chat = chat_read(folder)
        bad = _check_pending(chat, name)
        if bad:
            return 409, bad, {}
        code, err, extra = add_to_carousel(folder, chat["pending"])
        if code == 200:
            _close(folder, chat, "karuzela")
        return code, err, extra
