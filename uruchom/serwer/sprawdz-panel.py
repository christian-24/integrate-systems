"""Kontrola panelu po wdrożeniu: otwiera stronę w przeglądarce bez okna (Playwright) i sprawdza, że widok się
pokazał i strona nie zgłosiła błędu JavaScript. Wyjście 0: w porządku, 1: błąd (opis na stderr).

Użycie: <python z Playwright> sprawdz-panel.py [adres] [plik klucza]
Domyślnie http://127.0.0.1:4801/#przeglad i klucz z /etc/integrate/lokalny.klucz (nagłówek X-Panel-Klucz).
"""
import sys

from playwright.sync_api import sync_playwright

url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:4801/#przeglad"
key_file = sys.argv[2] if len(sys.argv) > 2 else "/etc/integrate/lokalny.klucz"
try:
    with open(key_file, encoding="ascii") as f:
        key = f.read().strip()
except OSError:
    key = ""

errors = []
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(extra_http_headers={"X-Panel-Klucz": key} if key else {})
    page.on("pageerror", lambda e: errors.append("błąd JavaScript: %s" % e))
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_selector("#view h1", timeout=30000)
        page.wait_for_timeout(1500)
        title = page.inner_text("#view h1")
        stuck = page.locator("text=Wczytuję dane").count()
        if stuck:
            errors.append("strona zatrzymała się na „Wczytuję dane”")
        banner = page.locator("#view .banner.bad[role=alert]").count()
        if banner:
            errors.append("widok pokazał błąd: " + page.inner_text("#view .banner.bad[role=alert]")[:200])
    except Exception as e:  # noqa: BLE001
        errors.append("strona się nie pokazała: %s" % str(e).splitlines()[0])
        title = ""
    browser.close()

if errors:
    print("\n".join(errors), file=sys.stderr)
    sys.exit(1)
print("panel działa: " + title)
