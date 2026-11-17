@echo off
rem Reczne uruchomienie panelu na pierwszym planie. Zatrzymanie: Ctrl+C.
cd /d "%~dp0..\dashboard"
where python >nul 2>nul
if errorlevel 1 goto launcher
python server.py
goto end
:launcher
py -3 server.py
:end
