#!/bin/sh
# Ręczne uruchomienie panelu na pierwszym planie. Zatrzymanie: Ctrl+C.
cd "$(dirname "$0")/../dashboard" || exit 1
exec python3 server.py
