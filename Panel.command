#!/bin/zsh
# Dwuklik w Finderze: uruchamia panel projektów (port 4801) i otwiera go w przeglądarce.
# Jeśli panel już działa, tylko otwiera stronę. Okno Terminala można zminimalizować; zamknięcie go zatrzymuje panel.
cd "$(dirname "$0")"
if curl -s -o /dev/null --max-time 2 http://127.0.0.1:4801/; then
  open http://localhost:4801/
  exit 0
fi
( sleep 2; open http://localhost:4801/ ) &
exec python3 dashboard/server.py
