"""Udostępnianie posta na Instagramie ręcznie, przez rozszerzenie Chrome (uruchom/chrome-instagram/).

Dla projektów, które nie publikują na Instagram przez API. Panel tworzy pakiet: opis z post.md, pliki posta
(film albo grafika i zdjęcia) i oczekiwany profil (pole karty `instagram:`). Pakiet żyje 30 minut pod adresem
/udostepnij/<token> (token losowy, 32 znaki szesnastkowe; bez sesji panelu, bo pobiera go strona instagram.com).
Rozszerzenie wgrywa pliki i opis, sprawdza zalogowany profil i zatrzymuje się przed „Udostępnij”: publikuje
właściciel. Pakiety są tylko w pamięci procesu.
"""
import os
import re
import secrets
import threading
import time

TTL = 30 * 60
MAX_FILES = 10
TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".mp4": "video/mp4", ".mov": "video/quicktime"}
# dodatkowe zdjęcia posta (karuzela): zdjecie-1.jpg, zdjęcie2.png, slajd-3.jpg … w folderze posta
PHOTO = re.compile(r"^(?:zdj[eę]cie|slajd)[-_ ]?(\d{0,3})\.(?:jpe?g|png)$", re.I)
TOKEN = re.compile(r"^[0-9a-f]{32}$")
ORIGIN = "https://www.instagram.com"


def photos(folder):
    """Nazwy dodatkowych zdjęć posta w kolejności numerów (bez numeru: pierwsze)."""
    try:
        names = [n for n in os.listdir(folder) if PHOTO.match(n) and os.path.isfile(os.path.join(folder, n))
                 and not os.path.islink(os.path.join(folder, n))]
    except OSError:
        return []
    return sorted(names, key=lambda n: (int(PHOTO.match(n).group(1) or 0), n.lower()))


def media(folder, film, image):
    """Pliki posta na Instagram: film (sam), inaczej grafika i zdjęcia (karuzela, najwyżej 10)."""
    if film:
        return [film]
    out = [image] if image else []
    out += [os.path.join(folder, n) for n in photos(folder)]
    return out[:MAX_FILES]


def caption(info):
    s = info.get("sections") or {}
    return s.get("Instagram") or s.get("Reels") or s.get("Facebook") or ""


class Shares:
    def __init__(self, now=None):
        self.now = now or time.time
        self.items = {}
        self.lock = threading.Lock()

    def _clean(self):
        t = self.now()
        self.items = {k: v for k, v in self.items.items() if v["expires"] > t}

    def create(self, title, text, files, handle):
        token = secrets.token_hex(16)
        with self.lock:
            self._clean()
            self.items[token] = {"title": title, "caption": text, "files": list(files), "handle": handle,
                                 "expires": self.now() + TTL, "fetched": False}
        return token

    def _hit(self, token):
        if not TOKEN.match(token or ""):
            return None
        with self.lock:
            self._clean()
            return self.items.get(token)

    def package(self, token):
        """Pakiet dla rozszerzenia (adresy plików względne do adresu pakietu) albo None. Zaznacza pobranie."""
        hit = self._hit(token)
        if not hit:
            return None
        hit["fetched"] = True
        files = []
        for i, p in enumerate(hit["files"]):
            ext = os.path.splitext(p)[1].lower()
            files.append({"name": os.path.basename(p), "type": TYPES.get(ext, "application/octet-stream"),
                          "size": os.path.getsize(p) if os.path.isfile(p) else 0, "url": "%s/%d" % (token, i)})
        return {"ok": True, "title": hit["title"], "caption": hit["caption"], "handle": hit["handle"],
                "expires": int(hit["expires"]), "files": files}

    def file(self, token, n):
        """(ścieżka, typ) pliku n pakietu albo None."""
        hit = self._hit(token)
        if not hit or not str(n).isdigit() or int(n) >= len(hit["files"]):
            return None
        p = hit["files"][int(n)]
        ext = os.path.splitext(p)[1].lower()
        return (p, TYPES[ext]) if ext in TYPES and os.path.isfile(p) else None

    def status(self, token):
        hit = self._hit(token)
        return {"fetched": hit["fetched"], "expires": int(hit["expires"])} if hit else None
