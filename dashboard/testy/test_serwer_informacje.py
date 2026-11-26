"""Serwer bez Projektów, GitHuba i Księgi (2026-11-25): dodawanie projektu z „+” w menu, Google Drive zwinięty
do jednego wiersza, nowy widok Informacje z plikami opisowymi (GET /api/informacje, tylko odczyt)."""
import json
import re
import unittest

from test_blokady import PANEL
from test_instagram import panel_parts
from test_serwer import REMOTE, Serwer
from wspolne import server


def html():
    with open(PANEL, encoding="utf-8") as f:
        return f.read()


class Informacje(Serwer):
    def get(self, path, **kw):
        status, _, text = self.request("GET", path, **kw)
        return status, json.loads(text)

    def test_lista_i_tresc(self):
        status, j = self.get("/api/informacje")
        self.assertEqual(status, 200)
        ids = [f["id"] for f in j["files"]]
        for i in ("standard", "agenci", "panel", "rozwoj"):
            self.assertIn(i, ids)
        status, f = self.get("/api/informacje?plik=standard")
        self.assertEqual((status, f["path"]), (200, "standard/STANDARD.md"))
        self.assertIn("ZADANIA.md", f["text"])

    def test_tylko_pliki_z_listy(self):
        for bad in ("../CLAUDE.md", "standard/STANDARD.md", "x"):
            status, f = self.get("/api/informacje?plik=" + bad)
            self.assertEqual(status, 404, bad)
            self.assertNotIn("text", f)

    def test_zdalnie_wymaga_hasla(self):
        saved = server.TOKEN
        server.TOKEN = "tajne"
        try:
            status, _, _ = self.request("GET", "/api/informacje?plik=standard", headers=REMOTE)
            self.assertEqual(status, 401)
        finally:
            server.TOKEN = saved


class Panel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = html()

    def test_serwer_bez_trzech_sekcji(self):
        v = panel_parts(self.html, ["vKoszty"])
        for gone in ("ghPanel()", "prjPanel", "drvPanel"):
            self.assertNotIn(gone, v)
        self.assertIn("srvsDrv()", v)
        self.assertIsNone(re.search(r"function prjPanel\(", self.html))

    def test_plus_w_menu_otwiera_dodawanie(self):
        self.assertRegex(self.html, r'<button type="button" class="srvs-add" id="srvs-add" data-srvs="padd"[^>]*aria-label="Dodaj projekt"')
        add = panel_parts(self.html, ["srvsAddHtml"])
        self.assertIn('id="padd"', add)                 # ten sam formularz (addProject, submit #padd)
        self.assertIn('data-ag="prm"', add)             # usuwanie z rejestru zostaje w oknie
        self.assertIn("else if(kind==='padd')", self.html)

    def test_drive_zwiniety(self):
        d = panel_parts(self.html, ["srvsDrv"])
        self.assertIn("<summary>Szczegóły</summary>", d)
        self.assertIn("draClient()", d)                 # „Logowanie jednym kliknięciem” pod „Szczegóły”
        self.assertIn("Połącz Google Drive", d)

    def test_informacje_w_menu(self):
        self.assertIn("informacje:'Informacje'", self.html)
        v = panel_parts(self.html, ["vInformacje"])
        self.assertIn("/api/informacje", self.html)
        self.assertIn("srvsBook", self.html)
        self.assertIn('data-srvs="inf"', v)
