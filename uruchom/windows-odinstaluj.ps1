# Wylacza uruchamianie panelu przy logowaniu i zatrzymuje go. Plikow projektow, rekordow i logu nie usuwa.
#   powershell -ExecutionPolicy Bypass -File uruchom\windows-odinstaluj.ps1
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'windows-wspolne.ps1')

# Najpierw proces (razem z agentami), potem zadanie, zeby Harmonogram nie wznowil panelu.
$stopped = Stop-Panel
if (Remove-PanelTask) { Write-Host ('Usunieto zadanie Harmonogramu zadan "{0}".' -f $TaskName) }
if (Test-Path $Shortcut) {
    Remove-Item -Path $Shortcut
    Write-Host ('Usunieto skrot: ' + $Shortcut)
}
if ($stopped) {
    Write-Host 'Zatrzymano panel.'
} else {
    Write-Host 'Panel w tle nie byl uruchomiony.'
}
Write-Host 'Reczne uruchomienie: uruchom\start.cmd'
