"""Pośrednik uruchomienia agenta: proces niezależny od panelu (AGENCI.md, „Uruchomienie przeżywa restart panelu”).

    python3 przebieg.py <katalog uruchomień> <id> -- polecenie agenta …

Panel uruchamia pośrednika we własnej sesji (setsid), bez potoków do siebie. Pośrednik:
- uruchamia polecenie agenta (dziedziczy katalog i środowisko), jego wyjście dopisuje do <id>.log;
- przekazuje na wejście agenta to, co panel dopisuje do <id>.wej (wiersze JSON: {"d": tekst} albo {"zamknij": true});
- po końcu agenta zapisuje <id>.koniec ({"code": kod, "at": czas}) i kończy pracę.

Restart panelu nie przerywa agenta, gdy usługa nie zabija całej grupy (KillMode=process). Panel po starcie znajduje
pośrednika po rekordzie (pole runner) i czyta dalej <id>.log od zapamiętanego miejsca. SIGTERM pośrednik ignoruje
(dostaje go agent z tej samej grupy procesów); koniec agenta zapisuje zawsze.
Sama biblioteka standardowa; bez importu panelu.
"""
import json
import os
import signal
import subprocess
import sys
import threading
import time

POLL = 0.2


def _write_end(path, code):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"code": code, "at": time.strftime("%Y-%m-%dT%H:%M:%S")}, f)
    os.replace(tmp, path)


def _feed(inbox, proc, done):
    """Przekazuje wiersze z pliku wejścia na stdin agenta, od początku pliku."""
    pos, buf, closed = 0, b"", False
    while not done.is_set():
        try:
            with open(inbox, "rb") as f:
                f.seek(pos)
                chunk = f.read()
        except OSError:
            chunk = b""
        if chunk:
            pos += len(chunk)
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                try:
                    msg = json.loads(line.decode("utf-8"))
                except (ValueError, UnicodeDecodeError):
                    continue
                if not isinstance(msg, dict) or closed:
                    continue
                try:
                    if msg.get("zamknij"):
                        proc.stdin.close()
                        closed = True
                    elif isinstance(msg.get("d"), str):
                        proc.stdin.write(msg["d"].encode("utf-8"))
                        proc.stdin.flush()
                except (OSError, ValueError):
                    closed = True
        done.wait(POLL)


def main(argv):
    if len(argv) < 4 or "--" not in argv:
        sys.stderr.write("użycie: przebieg.py <katalog> <id> -- polecenie\n")
        return 2
    sep = argv.index("--")
    runs_dir, rid, cmd = argv[1], argv[2], argv[sep + 1:]
    if not cmd:
        return 2
    base = os.path.join(runs_dir, rid)
    for name in ("SIGTERM", "SIGHUP", "SIGINT"):
        signal.signal(getattr(signal, name), signal.SIG_IGN)
    end = base + ".koniec"
    log = open(base + ".log", "ab", buffering=0)
    try:
        # agent dostaje domyślną obsługę sygnałów (SIG_IGN dziedziczy się przez exec)
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=log, stderr=subprocess.STDOUT,
                                preexec_fn=lambda: [signal.signal(getattr(signal, n), signal.SIG_DFL)
                                                    for n in ("SIGTERM", "SIGHUP", "SIGINT")])
    except OSError as e:
        log.write(("Nie udało się uruchomić polecenia: %s\n" % (e.strerror or e)).encode("utf-8"))
        log.close()
        _write_end(end, -1)
        return 1
    done = threading.Event()
    feeder = threading.Thread(target=_feed, args=(base + ".wej", proc, done), daemon=True)
    feeder.start()
    code = proc.wait()
    done.set()
    feeder.join(2)
    log.close()
    _write_end(end, code)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
