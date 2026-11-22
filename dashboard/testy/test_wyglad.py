"""System wyglądu panelu (panel.html): zasady w CSS, kolory z tokenów, klasy bez kolizji, jedna nazwa widoku."""
import collections
import os
import re
import unittest

PANEL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "panel.html")
BOX = {"display", "padding", "margin", "border", "gap", "grid-template-columns", "position"}


def css_of(html):
    return re.search(r"<style>(.*?)</style>", html, re.S).group(1)


def top_rules(css):
    """Reguły najwyższego poziomu (bez @media i @keyframes): [(selektor, treść)]."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    out, pos = [], 0
    while pos < len(css):
        while pos < len(css) and css[pos].isspace():
            pos += 1
        if pos >= len(css):
            break
        if css[pos] == "@":
            j, d = css.index("{", pos) + 1, 1
            while d:
                d += {"{": 1, "}": -1}.get(css[j], 0)
                j += 1
            pos = j
            continue
        j = css.find("{", pos)
        if j < 0:
            break
        k = css.index("}", j)
        out.append((css[pos:j].strip(), css[j + 1:k]))
        pos = k + 1
    return out


class Wyglad(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(PANEL, encoding="utf-8") as f:
            cls.html = f.read()
        cls.css = css_of(cls.html)

    def test_atrybut_bez_podwojnego_cudzyslowu(self):
        """data-x=""'+wartość: pusty atrybut, wartość ląduje poza nim (tak zgubił się termin etapu)."""
        import re
        self.assertEqual(re.findall(r'[\w-]+=""\'\+[A-Za-z_]', self.html), [])

    def test_zasady_na_poczatku_css(self):
        self.assertIn("SYSTEM WYGLĄDU", self.css[:12000])

    def test_ta_sama_klasa_w_dwoch_komponentach(self):
        """Ta sama klasa bazowa (.plan) zdefiniowana w dwóch osobnych regułach z układem (display, padding, ramka…)
        to dwa komponenty pod jedną nazwą: druga reguła psuje pierwszy (np. plan dnia dostawał ramkę publikacji)."""
        seen = collections.defaultdict(list)
        for sel, body in top_rules(self.css):
            if not re.fullmatch(r"\.[A-Za-z][\w-]*", sel):
                continue
            props = {re.sub(r"-(top|right|bottom|left|width|color|style|radius)$", "", p.split(":")[0].strip())
                     for p in body.split(";") if ":" in p}
            seen[sel].append(props)
        bad = []
        for sel, L in seen.items():
            for a in range(len(L)):
                for b in range(a + 1, len(L)):
                    if L[a] & L[b] & BOX:
                        bad.append((sel, sorted(L[a] & L[b] & BOX)))
        self.assertEqual(bad, [])

    def test_odpowiedz_na_pytanie_bez_kolizji(self):
        self.assertNotIn(".qa .ans{", self.css)
        self.assertIn(".qa .qa-ans{", self.css)
        self.assertIn('class="pubplan"', self.html)
        self.assertIn("closest('.pubplan')", self.html)

    def test_kolory_tylko_z_tokenow(self):
        body = re.sub(r"/\*.*?\*/", "", self.css, flags=re.S)
        body = re.sub(r":root\{.*?\}\s*", "", body, count=1, flags=re.S)
        body = re.sub(r'@media \(prefers-color-scheme:dark\)\{:root:not\(\[data-theme="light"\]\)\{.*?\}\}', "", body, flags=re.S)
        body = re.sub(r':root\[data-theme="dark"\]\{.*?\}', "", body, flags=re.S)
        self.assertEqual(re.findall(r"#[0-9a-fA-F]{3,6}\b", body), [])
        self.assertEqual(re.findall(r"rgba?\(", body), [])
        for tok in ("--shadow-1", "--shadow-2", "--media-bg", "--ctl-line", "--on-color"):
            self.assertEqual(len(re.findall(re.escape(tok) + r":", self.css)), 3, tok)   # :root i oba bloki ciemne

    def test_znaczniki_bez_wersalikow(self):
        rule = re.search(r"\n\.lz\{([^}]*)\}", self.css).group(1)
        self.assertNotIn("text-transform", rule)
        self.assertNotIn("letter-spacing", rule)

    def test_jedna_nazwa_widoku_dla_ciebie(self):
        self.assertNotIn("Wymaga Ciebie", self.html)
        self.assertIn("ty:'Dla Ciebie'", self.html)

    def test_okruszek_prowadzi_do_startu(self):
        self.assertIn("""<a href="#start">Start</a>""", self.html)

    def test_przejdz_do_tresci(self):
        self.assertIn('class="sk-skip"', self.html)
        self.assertIn('id="view" tabindex="-1"', self.html)


if __name__ == "__main__":
    unittest.main()
