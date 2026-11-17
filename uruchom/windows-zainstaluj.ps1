# Uruchamia panel przy logowaniu do Windows i wznawia go po awarii.
# Bez uprawnien administratora i bez zapisywania hasla: zadanie dziala tylko w sesji zalogowanego uzytkownika.
#   powershell -ExecutionPolicy Bypass -File uruchom\windows-zainstaluj.ps1
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'windows-wspolne.ps1')

if (-not (Test-Path (Join-Path $Dash 'server.py'))) {
    Write-Host ('Nie widze ' + (Join-Path $Dash 'server.py') + '. Uruchom skrypt z folderu uruchom w IntegrateSystems.')
    exit 1
}

$python = Get-Command python.exe -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host 'Brak polecenia python. Zainstaluj Python 3 z python.org i zaznacz "Add python.exe to PATH".'
    exit 1
}
$exe = & $python.Path -c "import sys; print(sys.executable)"
if ($LASTEXITCODE -ne 0 -or -not $exe) {
    Write-Host 'Polecenie python nie dziala. Zainstaluj Python 3 z python.org.'
    exit 1
}
$exe = ([string]$exe).Trim()
$pythonw = Join-Path (Split-Path -Parent $exe) 'pythonw.exe'
if (-not (Test-Path $pythonw)) {
    $pythonw = $exe
    Write-Host 'Brak pythonw.exe: panel bedzie mial widoczne okno konsoli.'
}

# Wczesniejsza instalacja zwalnia port, zanim go sprawdzimy. Najpierw proces (razem z agentami), potem zadanie.
$hadProcess = Stop-Panel
$hadTask = Remove-PanelTask
if ($hadTask -or $hadProcess) {
    Start-Sleep -Seconds 2
    Write-Host 'Zatrzymano wczesniejsza instalacje.'
}

$port = [int](Get-Setting 'PANEL_PORT' '4801')
if (Test-PanelPort $port) {
    $conn = Get-NetTCPConnection -LocalPort $port -State Listen | Select-Object -First 1
    $owner = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
    $ownerName = 'nieznany proces'
    if ($owner) { $ownerName = $owner.ProcessName }
    Write-Host ('Port {0} jest zajety: {1} (PID {2}).' -f $port, $ownerName, $conn.OwningProcess)
    Write-Host 'Jezeli to panel uruchomiony recznie, zatrzymaj go (Ctrl+C w jego oknie) i uruchom ten skrypt ponownie.'
    Write-Host 'Inny port: dopisz PANEL_PORT=4802 do dashboard\panel.env.'
    exit 1
}

New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
$argument = '"' + $Launcher + '"'
$execute = $pythonw
if ($execute -match ' ') { $execute = '"' + $pythonw + '"' }
$user = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$mode = 'zadanie'
try {
    $action = New-ScheduledTaskAction -Execute $execute -Argument $argument -WorkingDirectory $Dash
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $user
    $principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable `
        -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings `
        -Description 'Panel projektow: serwer lokalny i uruchamianie agentow.' -Force | Out-Null
    Start-ScheduledTask -TaskName $TaskName
    Write-Host ('Zainstalowano zadanie Harmonogramu zadan "{0}" (start przy logowaniu, wznowienie po awarii).' -f $TaskName)
}
catch {
    # Konto bez prawa do tworzenia zadan: skrot w folderze Autostart. Dziala przy logowaniu, bez wznawiania po awarii.
    $mode = 'autostart'
    Write-Host ('Harmonogram zadan odmowil: ' + $_.Exception.Message)
    $shell = New-Object -ComObject WScript.Shell
    $link = $shell.CreateShortcut($Shortcut)
    $link.TargetPath = $pythonw
    $link.Arguments = $argument
    $link.WorkingDirectory = $Dash
    $link.WindowStyle = 7
    $link.Save()
    Start-Process -FilePath $pythonw -ArgumentList $argument -WorkingDirectory $Dash -WindowStyle Hidden
    Write-Host ('Zainstalowano skrot w Autostarcie: ' + $Shortcut + ' (start przy logowaniu, bez wznawiania po awarii).')
}

$ready = $false
for ($i = 0; $i -lt 10; $i++) {
    if (Test-PanelPort $port) { $ready = $true; break }
    Start-Sleep -Seconds 1
}
if ($ready) {
    Write-Host ('Panel dziala: ' + (Get-PanelAddress))
} else {
    Write-Host ('Panel jeszcze nie odpowiada. Sprawdz log: ' + $LogFile)
}
Write-Host ('Log: ' + $LogFile)
Write-Host 'Po zmianie dashboard\panel.env uruchom ten skrypt ponownie. Wylaczenie: uruchom\windows-odinstaluj.ps1'
