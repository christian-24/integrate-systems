#!/usr/bin/env python3
"""Atrapa rclone dla test_drive.py: listremotes, config create (serwer logowania na ATRAPA_RCLONE_PORT), config delete.
Połączenia zapisuje w <config>.zdalne. Po „zalogowaniu” wypisuje udawany token (test sprawdza, że nie wycieka)."""
import http.server
import os
import sys
import urllib.parse

args = sys.argv[1:]
conf = args[args.index("--config") + 1]
rest = [a for i, a in enumerate(args) if a != "--config" and (i == 0 or args[i - 1] != "--config")]
state_file = conf + ".zdalne"


def remotes():
    try:
        with open(state_file) as f:
            return [x for x in f.read().split() if x]
    except OSError:
        return []


if rest[0] == "listremotes":
    print("\n".join(r + ":" for r in remotes()))
elif rest[:2] == ["config", "delete"]:
    with open(state_file, "w") as f:
        f.write("\n".join(r for r in remotes() if r != rest[2]))
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
