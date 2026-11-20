"""Zasoby serwera dla panelu: pamięć, swap, dysk, obciążenie, czas pracy i rozmiary folderów.

Odczyt z /proc (Linux) i shutil.disk_usage; poza Linuksem pamięć i obciążenie są None.
Rozmiary folderów liczy wątek w tle (raz na FOLDERS_TTL sekund), bo przejście po kilkuset MB trwa;
/api/data dostaje ostatni gotowy wynik i nigdy na niego nie czeka.
"""
import os
import shutil
import stat
import threading
import time

TTL = 30                 # s: pamięć, dysk, obciążenie
FOLDERS_TTL = 600        # s: rozmiary folderów


def meminfo(path="/proc/meminfo"):
    """{'total','available','swapTotal','swapFree'} w bajtach albo None."""
    try:
        with open(path, encoding="ascii") as f:
            raw = dict(line.split(":", 1) for line in f if ":" in line)
    except OSError:
        return None

    def kb(name):
        try:
            return int(raw[name].split()[0]) * 1024
        except (KeyError, ValueError, IndexError):
            return 0
    if not kb("MemTotal"):
        return None
    return {"total": kb("MemTotal"), "available": kb("MemAvailable") or kb("MemFree"),
            "swapTotal": kb("SwapTotal"), "swapFree": kb("SwapFree")}


def loadavg(path="/proc/loadavg"):
    try:
        with open(path, encoding="ascii") as f:
            parts = f.read().split()
        return [float(x) for x in parts[:3]]
    except (OSError, ValueError):
        return None


def uptime(path="/proc/uptime"):
    try:
        with open(path, encoding="ascii") as f:
            return int(float(f.read().split()[0]))
    except (OSError, ValueError, IndexError):
        return None


def tree_size(root):
    """(bajty bez .git, bajty .git, pliki) bez podążania za dowiązaniami; nieczytelne pomija."""
    size = git = files = 0
    for dirpath, dirnames, filenames in os.walk(root, onerror=lambda e: None):
        in_git = ".git" in os.path.relpath(dirpath, root).split(os.sep)
        for name in filenames:
            try:
                st = os.lstat(os.path.join(dirpath, name))
            except OSError:
                continue
            if stat.S_ISLNK(st.st_mode):
                continue
            used = st.st_blocks * 512 if hasattr(st, "st_blocks") else st.st_size
            if in_git:
                git += used
            else:
                size += used
                files += 1
    return size, git, files


class Resources:
    """state() dla /api/data. folders: lista (etykieta, ścieżka); projects: funkcja -> {id: (nazwa, [foldery])}, np. repozytorium i folder karty."""

    def __init__(self, folders, projects=None, disk="/", clock=time.time, background=True):
        self.folders = folders
        self.projects = projects or (lambda: {})
        self.disk = disk
        self.clock = clock
        self.background = background
        self.lock = threading.Lock()
        self.cache = None
        self.cache_at = 0
        self.sizes = None
        self.sizes_at = 0
        self.busy = False

    def _measure_sizes(self):
        out = {"at": None, "folders": [], "projects": []}
        for label, path in self.folders:
            if os.path.isdir(path):
                size, git, files = tree_size(path)
                out["folders"].append({"label": label, "path": path, "size": size + git, "files": files})
        try:
            projects = self.projects()
        except Exception:  # noqa: BLE001  (rejestr nieczytelny: bez listy projektów)
            projects = {}
        for pid, (name, folders) in projects.items():
            size = git = files = 0
            seen = set()
            for folder in folders:
                real = os.path.realpath(folder) if folder else ""
                if not real or real in seen or not os.path.isdir(real) or any(real.startswith(s + os.sep) for s in seen):
                    continue
                seen.add(real)
                a, b, c = tree_size(real)
                size, git, files = size + a, git + b, files + c
            if seen:
                out["projects"].append({"id": pid, "name": name, "size": size, "git": git, "files": files})
        out["projects"].sort(key=lambda p: -(p["size"] + p["git"]))
        out["at"] = self.clock()
        return out

    def _refresh_sizes(self):
        try:
            sizes = self._measure_sizes()
        finally:
            with self.lock:
                self.busy = False
        with self.lock:
            self.sizes = sizes
            self.sizes_at = self.clock()

    def _sizes(self):
        now = self.clock()
        with self.lock:
            stale = self.sizes is None or now - self.sizes_at >= FOLDERS_TTL
            start = stale and not self.busy
            if start:
                self.busy = True
        if start:
            if self.background:
                threading.Thread(target=self._refresh_sizes, daemon=True, name="zasoby").start()
            else:
                self._refresh_sizes()
        with self.lock:
            return self.sizes

    def state(self):
        now = self.clock()
        with self.lock:
            fresh = self.cache is not None and now - self.cache_at < TTL
            cached = self.cache
        if not fresh:
            try:
                du = shutil.disk_usage(self.disk)
                disk = {"total": du.total, "used": du.used, "free": du.free}
            except OSError:
                disk = None
            cached = {"memory": meminfo(), "load": loadavg(), "cpus": os.cpu_count() or 1,
                      "uptime": uptime(), "disk": disk}
            with self.lock:
                self.cache, self.cache_at = cached, now
        out = dict(cached)
        sizes = self._sizes()
        out["folders"] = sizes["folders"] if sizes else None
        out["projects"] = sizes["projects"] if sizes else None
        out["sizesAt"] = sizes["at"] if sizes else None
        out["at"] = now
        return out
