"""Udostępnianie posta ręcznie, przez rozszerzenie Chrome (uruchom/chrome-udostepnij/): Instagram, Facebook (Meta
Business Suite), LinkedIn i TikTok.

Dla platform, na które projekt nie publikuje przez API. Panel tworzy pakiet: platforma, opis z post.md (sekcja
platformy), pliki posta (film albo grafika i zdjęcia) i oczekiwany profil (pole karty `instagram:`, `facebook:`,
`linkedin:`, `tiktok:`). Pakiet żyje 30 minut pod adresem /udostepnij/<token> (token losowy, 32 znaki
szesnastkowe; bez sesji panelu, bo pobiera go strona platformy, CORS tylko dla jej dokładnych adresów).
Rozszerzenie wgrywa pliki i opis, sprawdza profil i zatrzymuje się przed publikacją: publikuje właściciel.
Pakiety są tylko w pamięci procesu.
"""
import os
import re
import secrets
import threading
import time
from urllib.parse import quote

TTL = 30 * 60
MAX_FILES = 10
TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".mp4": "video/mp4", ".mov": "video/quicktime"}
# dodatkowe zdjęcia posta (karuzela): zdjecie-1.jpg, zdjęcie2.png, slajd-3.jpg … w folderze posta
PHOTO = re.compile(r"^(?:zdj[eę]cie|slajd)[-_ ]?(\d{0,3})\.(?:jpe?g|png)$", re.I)
TOKEN = re.compile(r"^[0-9a-f]{32}$")
ORIGIN = "https://www.instagram.com"          # zgodność: dawny jedyny adres
# platforma: adresy stron (CORS), strona tworzenia posta, kolejność sekcji post.md (jak SPCHAIN w panel.html),
# czy wymaga zdjęcia albo filmu, czy tylko film
PLATFORMS = {
    "instagram": {"name": "Instagram", "origins": ("https://www.instagram.com",),
                  "url": "https://www.instagram.com/", "sections": ("Instagram", "Reels", "Facebook"),
                  "media": True, "film_only": False},
    "facebook": {"name": "Facebook", "origins": ("https://business.facebook.com", "https://www.facebook.com"),
                 "url": "https://business.facebook.com/latest/composer",
                 "reels": "https://business.facebook.com/latest/reels_composer",
                 "sections": ("Facebook", "Reels", "Instagram"), "media": False, "film_only": False},
    "linkedin": {"name": "LinkedIn", "origins": ("https://www.linkedin.com",),
                 "url": "https://www.linkedin.com/feed/?shareActive=true",
                 "sections": ("LinkedIn", "Facebook", "Instagram"), "media": False, "film_only": False},
    "tiktok": {"name": "TikTok", "origins": ("https://www.tiktok.com",),
               "url": "https://www.tiktok.com/tiktokstudio/upload",
               "sections": ("TikTok", "Reels", "Instagram", "Facebook"), "media": True, "film_only": True},
}
ORIGINS = frozenset(o for p in PLATFORMS.values() for o in p["origins"])


def photos(folder):
    """Nazwy dodatkowych zdjęć posta w kolejności numerów (bez numeru: pierwsze)."""
    try:
        names = [n for n in os.listdir(folder) if PHOTO.match(n) and os.path.isfile(os.path.join(folder, n))
                 and not os.path.islink(os.path.join(folder, n))]
    except OSError:
        return []
    return sorted(names, key=lambda n: (int(PHOTO.match(n).group(1) or 0), n.lower()))


def media(folder, film, image, platform="instagram"):
    """Pliki posta: film (sam), inaczej grafika i zdjęcia (karuzela, najwyżej 10); TikTok tylko film."""
    if film:
        return [film]
    if PLATFORMS.get(platform, {}).get("film_only"):
        return []
    out = [image] if image else []
    out += [os.path.join(folder, n) for n in photos(folder)]
    return out[:MAX_FILES]


def caption(info, platform="instagram"):
    """Opis dla platformy: jej sekcja post.md, inaczej najbliższa (kolejność jak w podglądzie panelu)."""
    s = info.get("sections") or {}
    return next((s[n] for n in PLATFORMS[platform]["sections"] if s.get(n)), "")


def compose_url(platform, film=False, reels=False, text=""):
    """Strona tworzenia posta: Facebook z filmem na kanale Reels: tworzenie rolki; LinkedIn z wpisanym opisem
    (pomaga też bez rozszerzenia)."""
    p = PLATFORMS[platform]
    if platform == "facebook" and film and reels:
        return p["reels"]
    if platform == "linkedin" and text:
        return p["url"] + "&text=" + quote(text, safe="")
    return p["url"]


def origin_ok(origin, platform=None):
    """Czy adres strony (nagłówek Origin) może czytać pakiet: dokładny adres platformy pakietu (bez pakietu:
    dowolnej obsługiwanej platformy, żeby rozszerzenie odczytało komunikat „pakiet wygasł”)."""
    allowed = PLATFORMS[platform]["origins"] if platform in PLATFORMS else ORIGINS
    return origin in allowed


class Shares:
    def __init__(self, now=None):
        self.now = now or time.time
        self.items = {}
        self.lock = threading.Lock()

    def _clean(self):
        t = self.now()
        self.items = {k: v for k, v in self.items.items() if v["expires"] > t}

    def create(self, title, text, files, handle, platform="instagram"):
        if platform not in PLATFORMS:
            raise ValueError("nieznana platforma: %s" % platform)
        token = secrets.token_hex(16)
        with self.lock:
            self._clean()
            self.items[token] = {"title": title, "caption": text, "files": list(files), "handle": handle,
                                 "platform": platform, "expires": self.now() + TTL, "fetched": False}
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
        return {"ok": True, "platforma": hit["platform"], "title": hit["title"], "caption": hit["caption"],
                "handle": hit["handle"], "expires": int(hit["expires"]), "files": files}

    def platform(self, token):
        """Platforma pakietu (bez zaznaczania pobrania) albo None."""
        hit = self._hit(token)
        return hit["platform"] if hit else None

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
