#!/usr/bin/env python3
"""Zrzut ekranu strony WWW dla agenta (zadania „Strona: …” z panelu; dashboard/AGENCI.md, „Podgląd strony”).

Użycie:
  zrzut-strony.py <adres|folder|plik.html> <szerokość> <wynik.png> [--sciezka /podstrona] [--wysokosc 900]
                  [--do 6000] [--ekran]

- adres http(s)://…: otwiera stronę wprost;
- folder (np. site/dist) albo plik .html: serwuje folder na 127.0.0.1 (losowy port, tylko na czas zrzutu), dzięki
  temu działają ścieżki /assets/… i moduły JS;
- szerokość w px (390 telefon, 1440 komputer); poniżej 600 px tryb telefonu (dotyk, mobilny user agent);
- domyślnie cała strona, najwyżej --do px wysokości; --ekran: tylko pierwszy ekran.
Wypisuje ścieżkę zrzutu i wymiary strony. Wynik obejrzyj narzędziem Read (obraz).

Wymaga Pythona z pakietem playwright i przeglądarki Chromium (na serwerze /home/agent/narzedzia/pw,
przeglądarki w /opt/ms-playwright). Bez zależności poza Playwright.
"""
import argparse
import functools
import http.server
import os
import sys
import threading
import urllib.parse


def serve(folder):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=folder)
    handler.log_message = lambda *a: None
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def main(argv=None):
    ap = argparse.ArgumentParser(description="Zrzut ekranu strony (Playwright, Chromium).")
    ap.add_argument("cel", help="adres http(s), folder z index.html albo plik .html")
    ap.add_argument("szerokosc", type=int, help="szerokość okna w px, np. 390 albo 1440")
    ap.add_argument("wynik", help="ścieżka pliku .png")
    ap.add_argument("--sciezka", default="/", help="podstrona, np. /kontakt (dla folderu albo pliku)")
    ap.add_argument("--wysokosc", type=int, default=0, help="wysokość okna w px (domyślnie 844 albo 900)")
    ap.add_argument("--do", type=int, default=6000, help="najwyżej tyle px wysokości zrzutu całej strony")
    ap.add_argument("--ekran", action="store_true", help="tylko pierwszy ekran zamiast całej strony")
    a = ap.parse_args(argv)
    if not 200 <= a.szerokosc <= 3840:
        ap.error("szerokość od 200 do 3840 px")
    if not os.environ.get("PLAYWRIGHT_BROWSERS_PATH") and os.path.isdir("/opt/ms-playwright"):
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/opt/ms-playwright"
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Brak pakietu playwright w tym Pythonie (%s)." % sys.executable, file=sys.stderr)
        return 3

    httpd, url = None, a.cel
    if not a.cel.startswith(("http://", "https://")):
        path = os.path.abspath(a.cel)
        if os.path.isfile(path):
            folder, page = os.path.dirname(path), "/" + os.path.basename(path)
        elif os.path.isdir(path):
            folder, page = path, a.sciezka if a.sciezka.startswith("/") else "/" + a.sciezka
        else:
            print("Nie ma pliku ani folderu: %s" % path, file=sys.stderr)
            return 2
        httpd = serve(folder)
        url = "http://127.0.0.1:%d%s" % (httpd.server_address[1], urllib.parse.quote(page))
    mobile = a.szerokosc < 600
    height = a.wysokosc or (844 if mobile else 900)
    os.makedirs(os.path.dirname(os.path.abspath(a.wynik)) or ".", exist_ok=True)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            ctx = browser.new_context(viewport={"width": a.szerokosc, "height": height}, device_scale_factor=1,
                                      is_mobile=mobile, has_touch=mobile, reduced_motion="reduce")
            page = ctx.new_page()
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            resp = page.goto(url, wait_until="networkidle", timeout=45000)
            page.wait_for_timeout(600)
            full = page.evaluate("Math.max(document.documentElement.scrollHeight, document.body ? "
                                 "document.body.scrollHeight : 0)")
            if a.ekran:
                page.screenshot(path=a.wynik)
            else:
                clip_h = min(int(full or height), a.do)
                page.screenshot(path=a.wynik, full_page=True,
                                clip={"x": 0, "y": 0, "width": a.szerokosc, "height": max(clip_h, 1)})
            browser.close()
    finally:
        if httpd:
            httpd.shutdown()
    print("Zrzut: %s (%d px szerokości, strona %d px wysokości%s)" % (
        a.wynik, a.szerokosc, full or 0, ", przycięty do %d px" % a.do if (full or 0) > a.do and not a.ekran else ""))
    if resp is not None and resp.status >= 400:
        print("Uwaga: strona odpowiedziała kodem %d." % resp.status)
    for e in errors[:5]:
        print("Błąd JS na stronie: %s" % e[:300])
    return 0


if __name__ == "__main__":
    sys.exit(main())
