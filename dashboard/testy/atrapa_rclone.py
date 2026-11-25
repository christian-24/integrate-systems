#!/usr/bin/env python3
"""Atrapa rclone dla test_drive.py: listremotes, config create (drive: serwer logowania na ATRAPA_RCLONE_PORT;
alias: od razu, cel w <config>.alias), config delete, lsjson (foldery konta; ATRAPA_RCLONE_BLAD: błąd z „tokenem”).
Połączenia zapisuje w <config>.zdalne. Po „zalogowaniu” wypisuje udawany token (test sprawdza, że nie wycieka)."""
import http.server
import json
import os
import sys
import urllib.parse

args = sys.argv[1:]
conf = args[args.index("--config") + 1]
rest = [a for i, a in enumerate(args) if a != "--config" and (i == 0 or args[i - 1] != "--config")]
state_file = conf + ".zdalne"


def remotes():
    out = []
    try:
        with open(state_file) as f:
            out = [x for x in f.read().split() if x]
    except OSError:
        pass
    try:                                          # wpisy zapisane przez panel wprost (własny klient OAuth)
        with open(conf) as f:
            out += [x.strip()[1:-1] for x in f if x.strip().startswith("[")]
    except OSError:
        pass
    return out


if rest[0] == "listremotes":
    print("\n".join(r + ":" for r in remotes()))
elif rest[:2] == ["config", "delete"]:
    keep = [r for r in remotes() if r != rest[2]]
    with open(state_file, "w") as f:
        f.write("\n".join(keep))
elif rest[0] == "lsd":
    remote = rest[1].split(":")[0]
    error = os.environ.get("ATRAPA_RCLONE_BLAD", "")
    if "," not in remote and os.environ.get("ATRAPA_RCLONE_ALIAS_BLAD"):
        error = "didn't find section in config file"
    if error or remote.split(",")[0] not in remotes():
        sys.stderr.write('Failed to lsd: %s TAJNY-TOKEN\n' % (error or "didn't find section in config file"))
        sys.exit(1)
elif rest[0] == "lsjson":
    blad = os.environ.get("ATRAPA_RCLONE_BLAD", "")
    if blad or rest[1].split(":")[0] not in remotes():
        sys.stderr.write('Failed to lsjson: %s {"access_token":"TAJNY-TOKEN"}\n' % (blad or "didn't find section in config file"))
        sys.exit(1)
    print(json.dumps([
        {"Path": "Marketing", "Name": "Marketing", "IsDir": True, "ID": "1MarketingId00"},
        {"Path": "Marketing/Cupra", "Name": "Cupra", "IsDir": True, "ID": "1CupraFolderId"},
        {"Path": "Marketing/Cupra/Zdjęcia", "Name": "Zdjęcia", "IsDir": True, "ID": "1CupraZdjecia0"},
        {"Path": "Prywatne", "Name": "Prywatne", "IsDir": True, "ID": "1PrywatneId000"},
    ]))
elif rest[:2] == ["config", "create"] and rest[3] == "alias":
    with open(state_file, "a") as f:
        f.write("\n" + rest[2])
    with open(conf + ".alias", "a") as f:
        f.write("%s %s\n" % (rest[2], rest[4]))
elif rest[:2] == ["config", "create"]:
    name, port, state = rest[2], int(os.environ["ATRAPA_RCLONE_PORT"]), "St4te-xyz"

    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            u = urllib.parse.urlsplit(self.path)
            q = urllib.parse.parse_qs(u.query)
            if u.path == "/auth":
                self.send_response(307)
                self.send_header("Location", "https://accounts.google.com/o/oauth2/auth?state=" + state)
                self.end_headers()
            elif q.get("state") == [state] and q.get("code"):
                self.send_response(200)
                self.end_headers()
                srv.done = True
            else:
                self.send_response(400)
                self.end_headers()

    with open(state_file, "a") as f:              # jak prawdziwy rclone: wpis zapisany przed zalogowaniem
        f.write("\n" + name)
    srv = http.server.HTTPServer(("127.0.0.1", port), H)
    srv.done = False
    print("NOTICE: If your browser doesn't open automatically go to the following link: "
          "http://127.0.0.1:%d/auth?state=%s" % (port, state), flush=True)
    while not srv.done:
        srv.handle_request()
    print('token = {"access_token":"TAJNY-TOKEN"}', flush=True)
