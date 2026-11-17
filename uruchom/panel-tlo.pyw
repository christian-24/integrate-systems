"""Uruchamia serwer panelu bez okna konsoli (Windows, pythonw).

pythonw nie ma konsoli, więc wyjście serwera trafia do pliku
%LOCALAPPDATA%\\PanelProjektow\\panel.log, a numer procesu do panel.pid w tym samym folderze.
Używają tego windows-zainstaluj.ps1 i windows-odinstaluj.ps1.
"""
import os
import runpy
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DASH = os.path.join(ROOT, "dashboard")
LOGDIR = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "PanelProjektow")
LOG = os.path.join(LOGDIR, "panel.log")

os.makedirs(LOGDIR, exist_ok=True)
try:
    if os.path.getsize(LOG) > 5 * 1024 * 1024:  # jeden poprzedni plik wystarczy
        os.replace(LOG, LOG + ".1")
except OSError:
    pass
out = open(LOG, "a", buffering=1, encoding="utf-8", errors="replace")
sys.stdout = sys.stderr = out
with open(os.path.join(LOGDIR, "panel.pid"), "w", encoding="ascii") as f:
    f.write(str(os.getpid()))
print(time.strftime("%Y-%m-%d %H:%M:%S"), "start panelu")

os.chdir(DASH)
sys.path.insert(0, DASH)
sys.argv = [os.path.join(DASH, "server.py")]
runpy.run_path(sys.argv[0], run_name="__main__")
