#!/usr/bin/env python3
"""Pracownik rozpoznawania mowy dla asystenta panelu: faster-whisper (domyślnie model small, int8), język polski.

Uruchamia go panel (dashboard/glos.py) interpreterem z PANEL_GLOS_PYTHON (venv z faster-whisper) i rozmawia przez
stdin/stdout, jeden wiersz JSON na żądanie:
  żądanie:   {"id": 1, "plik": "/tmp/nagranie.webm", "podpowiedz": "Projekty: Alfa, Beta."}
  odpowiedź: {"id": 1, "tekst": "…", "ms": 812}   albo   {"id": 1, "blad": "…"}
Po starcie jeden wiersz: {"gotowy": true} albo {"gotowy": false, "blad": "…"} (wtedy koniec, kod 3).
Koniec wejścia (panel zamyka stdin po bezczynności) kończy proces i zwalnia pamięć modelu.

Ustawienia (zmienne środowiska): PANEL_GLOS_MODEL (small), PANEL_GLOS_MODELE (katalog modeli, np. ten, do którego
pobrał je zainstaluj-glos.sh), PANEL_GLOS_WATKI (2), PANEL_GLOS_WIAZKA (beam_size, 1 = najszybciej).
Testy: GLOS_ATRAPA=1 bez faster-whisper, tekst to część pliku po pierwszym znaku „|”; GLOS_ATRAPA=brak jak brak pakietu.
"""
import json
import os
import sys
import time

# Odpowiedzi idą osobnym deskryptorem; wszystko, co biblioteki wypiszą na stdout, trafia do stderr i nie psuje protokołu.
OUT = os.fdopen(os.dup(1), "w", encoding="utf-8")
os.dup2(2, 1)


def send(obj):
    OUT.write(json.dumps(obj, ensure_ascii=False) + "\n")
    OUT.flush()


def load():
    """Funkcja (plik, podpowiedź) -> tekst albo wyjątek ImportError/RuntimeError z opisem."""
    fake = os.environ.get("GLOS_ATRAPA", "")
    if fake == "brak":
        raise ImportError("brak pakietu faster-whisper")
    if fake:
        def fake_run(path, prompt):
            with open(path, "rb") as f:
                data = f.read()
            return data.split(b"|", 1)[1].decode("utf-8", "replace").strip() if b"|" in data else ""
        return fake_run
    from faster_whisper import WhisperModel   # noqa: E402  (ImportError: czytelny błąd dla panelu)
    try:            # PyAV 15+ nie zna argumentu metadata_errors, którego używa faster-whisper 1.2 przy dekodowaniu
        import av
        _av_open = av.open

        def _open(*args, **kw):
            kw.pop("metadata_errors", None)
            return _av_open(*args, **kw)
        if int(av.__version__.split(".")[0]) >= 15:
            av.open = _open
    except (ImportError, ValueError):
        pass
    name = os.environ.get("PANEL_GLOS_MODEL") or "small"
    root = os.environ.get("PANEL_GLOS_MODELE") or None
    threads = int(os.environ.get("PANEL_GLOS_WATKI") or 2)
    beam = max(1, int(os.environ.get("PANEL_GLOS_WIAZKA") or 1))
    try:            # najpierw bez sieci: model pobrany przy instalacji
        model = WhisperModel(name, device="cpu", compute_type="int8", cpu_threads=threads, download_root=root,
                             local_files_only=True)
    except Exception:  # noqa: BLE001  (brak modelu na dysku: pobranie przy pierwszym użyciu)
        model = WhisperModel(name, device="cpu", compute_type="int8", cpu_threads=threads, download_root=root)

    def run(path, prompt):
        segments, _ = model.transcribe(path, language="pl", initial_prompt=prompt or None, beam_size=beam,
                                       vad_filter=True, condition_on_previous_text=False)
        return " ".join(s.text.strip() for s in segments).strip()
    return run


def main():
    try:
        run = load()
    except Exception as e:  # noqa: BLE001
        send({"gotowy": False, "blad": "%s: %s" % (type(e).__name__, str(e)[:200])})
        return 3
    send({"gotowy": True})
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except ValueError:
            continue
        rid = req.get("id")
        start = time.time()
        try:
            text = run(str(req.get("plik") or ""), str(req.get("podpowiedz") or "")[:800])
            send({"id": rid, "tekst": text, "ms": int((time.time() - start) * 1000)})
        except Exception as e:  # noqa: BLE001  (uszkodzone nagranie nie kończy pracownika)
            send({"id": rid, "blad": "%s: %s" % (type(e).__name__, str(e)[:200])})
    return 0


if __name__ == "__main__":
    sys.exit(main())
