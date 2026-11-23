#!/usr/bin/env python3
"""HTML → PDF i PNG dla agenta zadania (dashboard/AGENCI.md, „Render HTML do PDF i PNG”).

Użycie:
  html-do-pdf.py <plik.html> <wynik.pdf|wynik.png> [<wynik2.png|.pdf>] [--strona A4|90x50mm|1440x900px]
                 [--szerokosc 1440] [--skala 2] [--ekran]

- tylko plik lokalny .html/.htm (bez adresów http); zasoby z sieci są blokowane (fonty i obrazy trzymaj obok pliku);
- wynik w folderze bieżącym albo w folderze pliku HTML (inne miejsca są odrzucane);
- PDF: rozmiar strony z CSS (@page size) albo z --strona (A4, A5, Letter, np. 90x50mm), z tłem;
- PNG: okno --szerokosc px (domyślnie 1440, przy --strona w mm: rozmiar strony), skala --skala (domyślnie 2),
  cała strona albo tylko pierwszy ekran (--ekran).
Wypisuje ścieżki wyników. Kod 3: brak Playwright (komunikat mówi, czego brakuje).

Wymaga Pythona z pakietem playwright i Chromium (na serwerze /home/agent/narzedzia/pw, przeglądarki w
/opt/ms-playwright). Panel podaje agentowi pełne polecenie z właściwym Pythonem (agents.render_command).
"""
import argparse
import os
import re
import sys
import urllib.parse

SIZE = re.compile(r"^(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)(mm|px)$")
PAPER = ("A3", "A4", "A5", "A6", "Letter", "Legal")
MM_PX = 96 / 25.4


def inside(base, path):
    try:
        return os.path.commonpath([os.path.realpath(base), os.path.realpath(path)]) == os.path.realpath(base)
    except ValueError:
        return False


def main(argv=None):
    ap = argparse.ArgumentParser(description="HTML → PDF i PNG (Playwright, Chromium), bez sieci.")
    ap.add_argument("html", help="plik .html albo .htm")
    ap.add_argument("wyniki", nargs="+", help="plik .pdf i/lub .png (najwyżej 4)")
    ap.add_argument("--strona", default="", help="A4, A5, Letter albo wymiar, np. 90x50mm lub 1080x1350px")
    ap.add_argument("--szerokosc", type=int, default=0, help="szerokość okna w px dla PNG (200–3840)")
    ap.add_argument("--skala", type=float, default=2, help="skala PNG (1–3)")
    ap.add_argument("--ekran", action="store_true", help="PNG: tylko pierwszy ekran")
    a = ap.parse_args(argv)
    src = os.path.abspath(a.html)
    if "://" in a.html or not src.lower().endswith((".html", ".htm")):
        ap.error("podaj plik lokalny .html albo .htm (adresy z sieci są niedozwolone)")
    if not os.path.isfile(src):
        print("Nie ma pliku: %s" % src, file=sys.stderr)
        return 2
    if len(a.wyniki) > 4:
        ap.error("najwyżej 4 pliki wyniku")
    outs = [os.path.abspath(p) for p in a.wyniki]
    for p in outs:
        if not p.lower().endswith((".pdf", ".png")):
            ap.error("wynik musi mieć rozszerzenie .pdf albo .png: %s" % p)
        if not (inside(os.getcwd(), p) or inside(os.path.dirname(src), p)):
            ap.error("wynik zapisuję tylko w folderze bieżącym albo w folderze pliku HTML: %s" % p)
    paper, size = "", None
    if a.strona:
        m = SIZE.match(a.strona.strip().lower())
        if m:
            size = (float(m.group(1)), float(m.group(2)), m.group(3))
        elif a.strona.strip().capitalize() in [x.capitalize() for x in PAPER]:
            paper = next(x for x in PAPER if x.lower() == a.strona.strip().lower())
        else:
            ap.error("--strona: A4, A5, Letter albo wymiar, np. 90x50mm")
    if a.szerokosc and not 200 <= a.szerokosc <= 3840:
        ap.error("--szerokosc od 200 do 3840 px")
    if not 1 <= a.skala <= 3:
        ap.error("--skala od 1 do 3")

    if not os.environ.get("PLAYWRIGHT_BROWSERS_PATH") and os.path.isdir("/opt/ms-playwright"):
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/opt/ms-playwright"
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Render niedostępny: brak pakietu playwright w tym Pythonie (%s). Na serwerze jest w "
              "/home/agent/narzedzia/pw; na Macu i PC ustaw PANEL_RENDER_PYTHON." % sys.executable, file=sys.stderr)
        return 3

    if size and size[2] == "px":
        width, height = int(size[0]), int(size[1])
    elif size:
        width, height = round(size[0] * MM_PX), round(size[1] * MM_PX)
    else:
        width, height = a.szerokosc or 1440, 900
    if a.szerokosc:
        width = a.szerokosc
    url = "file://" + urllib.parse.quote(src)
    blocked = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            ctx = browser.new_context(viewport={"width": width, "height": height}, device_scale_factor=a.skala,
                                      reduced_motion="reduce", java_script_enabled=True, offline=True)
            # tylko pliki lokalne: http(s), ws i inne schematy są przerywane (agent nie pobiera nic z sieci)
            ctx.route("**/*", lambda r: r.continue_() if r.request.url.startswith(("file://", "data:", "blob:"))
                      else (blocked.append(r.request.url), r.abort()))
            page = ctx.new_page()
            page.goto(url, wait_until="load", timeout=30000)
            page.wait_for_timeout(400)
            for out in outs:
                os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
                if out.lower().endswith(".pdf"):
                    opts = {"path": out, "print_background": True, "prefer_css_page_size": True}
                    if paper:
                        opts["format"] = paper
                    elif size:
                        unit = "mm" if size[2] == "mm" else "px"
                        opts.update(width="%g%s" % (size[0], unit), height="%g%s" % (size[1], unit),
                                    margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
                    page.pdf(**opts)
                else:
                    page.screenshot(path=out, full_page=not a.ekran)
                print(out)
            browser.close()
    except Exception as e:      # komunikat dla agenta bez śladu stosu
        print("Render nieudany: %s" % str(e).split("\n")[0][:300], file=sys.stderr)
        return 1
    if blocked:
        print("Zablokowano %d zasobów z sieci (np. %s). Użyj plików lokalnych obok HTML." % (len(blocked), blocked[0][:120]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
