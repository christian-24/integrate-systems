"""Koszty Hetznera: szacunek z cennika (dashboard/koszty.py), bez sieci."""
import datetime
import io
import os
import sys
import tempfile
import unittest
import urllib.error

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import koszty  # noqa: E402

UTC = datetime.timezone.utc
NOW = datetime.datetime(2026, 11, 19, 12, 0, tzinfo=UTC)


def price(loc, h, m):
    return {"location": loc, "price_hourly": {"net": "0", "gross": str(h)}, "price_monthly": {"net": "0", "gross": str(m)}}


API = {
    "servers": {"servers": [
        {"name": "agenci", "created": "2026-11-17T12:00:00+00:00", "backup_window": None,
         "datacenter": {"location": {"name": "hel1"}},
         "server_type": {"name": "cax11", "prices": [price("fsn1", 0.01, 5), price("hel1", 0.01, 5.0)]}},
        {"name": "prod", "created": "2026-09-10T00:00:00+00:00", "backup_window": "22-02",
         "datacenter": {"location": {"name": "fsn1"}},
         "server_type": {"name": "cx22", "prices": [price("fsn1", 0.01, 5.0)]}}],
        "meta": {"pagination": {"next_page": None}}},
    "primary_ips": {"primary_ips": [{"name": "ip-agenci", "type": "ipv4", "created": "2026-11-17T12:00:00+00:00",
                                     "location": {"name": "hel1"}},
                                    {"name": "ip6", "type": "ipv6", "created": "2026-11-17T12:00:00+00:00",
                                     "location": {"name": "hel1"}}], "meta": {}},
    "volumes": {"volumes": [], "meta": {}},
    "pricing": {"pricing": {"primary_ips": [{"type": "ipv4", "prices": [price("hel1", 0.001, 0.6)]}],
                            "volume": {"price_per_gb_month": {"gross": "0.05"}}}},
}


def fake_get(url, token=None, timeout=20):
    if url == koszty.NBP:
        return {"rates": [{"mid": 4.25, "effectiveDate": "2026-11-19"}]}
    if token == "zly":
        raise urllib.error.HTTPError(url, 401, "Unauthorized", {}, io.BytesIO(b""))
    for key, value in API.items():
        if url.startswith("%s/%s" % (koszty.API, key)):
            return value
    raise AssertionError(url)


class Koszty(unittest.TestCase):
    def test_limit_miesieczny_i_miesiace(self):
        start = datetime.datetime(2026, 10, 30, 0, 0, tzinfo=UTC)
        total, month = koszty.billed(start, NOW, 0.01, 5.0)
        # październik: 48 h × 0,01 = 0,48; listopad do 19.11 12:00: 444 h × 0,01 = 4,44
        self.assertEqual((total, month), (4.92, 4.44))
        total, month = koszty.billed(datetime.datetime(2026, 9, 1, tzinfo=UTC), NOW, 0.01, 5.0)
        self.assertEqual((total, month), (14.44, 4.44))                     # wrzesień i październik po 5,00 (limit)

    def test_zbiorczo(self):
        out = koszty.collect([("glowny", "dobry"), ("inny", "zly")], fake_get, NOW)
        glowny, inny = out["projects"]
        self.assertEqual(inny["error"], "token odrzucony")
        kinds = [(i["name"], i["kind"]) for i in glowny["items"]]
        self.assertEqual(kinds, [("agenci", "serwer"), ("prod", "serwer"), ("prod", "kopie"), ("ip-agenci", "adres")])
        agenci = glowny["items"][0]
        self.assertEqual((agenci["monthly"], agenci["month"], agenci["total"], agenci["since"]), (5.0, 0.48, 0.48, "2026-11-17"))
        self.assertEqual(glowny["items"][2]["monthly"], 1.0)                 # kopie: 20% ceny serwera
        self.assertEqual(out["eurPln"], 4.25)
        self.assertNotIn("dobry", repr(out))                                 # token nie trafia do wyniku

    def test_plik_tokenow(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "tokeny")
            self.assertIsNone(koszty.read_tokens(path))
            with open(path, "w", encoding="utf-8") as f:
                f.write("# komentarz\nagenci=abc\n\nbez-tokenu=\nopisarnia = def \n")
            self.assertEqual(koszty.read_tokens(path), [("agenci", "abc"), ("opisarnia", "def")])
            old = os.environ.get("PANEL_HETZNER_TOKENY")
            try:
                os.environ["PANEL_HETZNER_TOKENY"] = os.path.join(d, "brak", "tokeny")
                self.assertIsNone(koszty.Costs(fake_get).state())             # nie serwer: bez bloku
                os.environ["PANEL_HETZNER_TOKENY"] = os.path.join(d, "puste")
                self.assertEqual(koszty.Costs(fake_get).state(), {"configured": False})
            finally:
                if old is None:
                    os.environ.pop("PANEL_HETZNER_TOKENY", None)
                else:
                    os.environ["PANEL_HETZNER_TOKENY"] = old


if __name__ == "__main__":
    unittest.main()
