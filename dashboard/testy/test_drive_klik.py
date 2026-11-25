"""Formularz Google Drive i zlecanie przygotowania materiału z Marketingu."""
import datetime
import json
import stat
from pathlib import Path
from unittest import mock

import drive
from test_serwer import Serwer
from wspolne import server


class Formularz(Serwer):
    def test_klient_z_pol_lub_pliku(self):
        oauth = Path(self.tmp, "integrate", "google-oauth.json")
        d = drive.Drive(lambda _: None, rclone="/bin/true", conf=self.tmp + "/test.conf",
                        oauth_file=str(oauth), data_dir=self.tmp + "/drive")
        client = {"client_id": "atrapa.apps.googleusercontent.com", "client_secret": "SEKRET-ATRAPA"}
        web = {"web": dict(client, redirect_uris=[drive.REDIRECT_URI])}
        with mock.patch.dict(server._drive, {"obj": d}):
            for body in (client, {"json": json.dumps(web)}):
                code, answer = self.post("/api/drive/klient", body)
                self.assertEqual((code, answer), (200, {"ok": True, "error": "", "ownClient": True}))
                self.assertEqual(stat.S_IMODE(oauth.stat().st_mode), 0o600)
                self.assertEqual(json.loads(oauth.read_text()), dict(client, redirect_uri=drive.REDIRECT_URI))
                for path in ("/", "/api/drive/konta"):
                    status, _, page = self.request("GET", path)
                    self.assertEqual(status, 200)
                    self.assertNotIn(client["client_secret"], page)
                    self.assertNotIn(client["client_id"], page)
            self.assertEqual(self.post("/api/drive/klient", {"json": json.dumps({"installed": web["web"]})})[0], 400)

    def test_powrot_przekierowuje_do_panelu(self):
        with mock.patch.object(server, "get_drive") as get_drive:
            get_drive.return_value.oauth_back.return_value = (303, "/#koszty?k=drive")
            code, headers, page = self.request("GET", "/api/drive/powrot?state=atrapa&code=atrapa")
        self.assertEqual(code, 200)
        self.assertIn('content="0;url=/#koszty?k=drive"', page)
        self.assertEqual(headers["Referrer-Policy"], "no-referrer")


class Marketing(Serwer):
    def test_zlec_brakujace_materialy_raz(self):
        today = datetime.date.today()
        titles = ("Opublikuj film", "Opublikuj post", "Opublikuj grafikę",
                  "Opublikuj film gotowy", "Opublikuj gotowy post", "Opublikuj gotową grafikę")
        days = [(today + datetime.timedelta(days=i)).isoformat() for i in range(len(titles))]
        campaign = Path(self.folder, "kampanie", "przyklad.md")
        campaign.parent.mkdir(exist_ok=True)
        text = "# Kampania: Test\n\n## Harmonogram\n" + "".join(
            f"- [ ] {title} | kanał: LinkedIn | kiedy: {day} | kto: ty\n" for title, day in zip(titles, days))
        campaign.write_text(text, encoding="utf-8")
        for i, (name, content) in enumerate((("scenariusz.md", "# Scenariusz\n"),
                                               ("post.md", "# Post\n## LinkedIn\nGotowy tekst\n"),
                                               ("grafika.svg", "<svg/>")), 3):
            path = Path(self.folder, "posty", days[i] + "-test", name)
            path.parent.mkdir(parents=True)
            path.write_text(content, encoding="utf-8")

        def pub(title):
            return next(t for t in self.data()["tasks"] if t["title"] == title)

        with mock.patch.object(self.manager, "run_task", return_value=(409, "Wykonawca zajęty", {})) as run:
            for title, material, name in zip(titles[:3], ("scenariusz filmu", "tekst posta", "plik grafiki"),
                                             ("scenariusz.json", "post.md", "grafika.png")):
                t = pub(title)
                self.assertEqual(t["missingMaterial"], material)
                req = {"id": t["id"], "title": title}
                status, first = self.post("/api/post/zlec", req)
                self.assertEqual(status, 200, first)
                self.assertEqual(first["reason"], "Wykonawca zajęty")
                job = next(t for t in self.data()["tasks"] if t["id"] == first["task"])
                self.assertEqual((job["executor"], job["date"], job["file"]), ("agent", days[0], "ZADANIA.md"))
                self.assertIn(title, job["detail"]["goal"])
                self.assertIn("Pozostaw publikację właścicielowi", job["detail"]["goal"])
                self.assertIn(t["date"], job["detail"]["doneWhen"])
                self.assertIn(name, job["detail"]["doneWhen"])
                self.assertEqual(self.post("/api/post/zlec", req)[1]["task"], first["task"])
                self.assertEqual(pub(title)["materialTask"], first["task"])
                run.assert_called_once_with(job["id"], job["title"])
                run.reset_mock()
            for title in titles[3:]:
                t = pub(title)
                self.assertNotIn("missingMaterial", t)
                self.assertEqual(self.post("/api/post/zlec", {"id": t["id"], "title": title})[0], 409)
            run.assert_not_called()
        self.assertEqual(campaign.read_text(encoding="utf-8"), text)
