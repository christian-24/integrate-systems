# Wspolne ustawienia skryptow Windows. Komunikaty bez polskich znakow, zeby dzialaly w kazdej konsoli.
$TaskName = 'Panel projektow'
$Root = Split-Path -Parent $PSScriptRoot
$Dash = Join-Path $Root 'dashboard'
$Launcher = Join-Path $PSScriptRoot 'panel-tlo.pyw'
$EnvFile = Join-Path $Dash 'panel.env'
$LogDir = Join-Path $env:LOCALAPPDATA 'PanelProjektow'
$LogFile = Join-Path $LogDir 'panel.log'
$PidFile = Join-Path $LogDir 'panel.pid'
$Shortcut = Join-Path ([Environment]::GetFolderPath('Startup')) 'Panel projektow.lnk'

# Zmienna srodowiska wygrywa z plikiem dashboard\panel.env.
function Get-Setting([string]$Name, [string]$Default) {
    $value = [Environment]::GetEnvironmentVariable($Name)
    if (-not $value -and (Test-Path $EnvFile)) {
        foreach ($line in (Get-Content -Path $EnvFile -Encoding UTF8)) {
            if ($line -match ('^\s*' + [regex]::Escape($Name) + '\s*=\s*(.*?)\s*$')) { $value = $Matches[1] }
        }
    }
    if ($value) { return $value }
    return $Default
}

function Get-PanelAddress {
    $hostName = Get-Setting 'PANEL_HOST' '127.0.0.1'
    $port = Get-Setting 'PANEL_PORT' '4801'
    if (@('127.0.0.1', 'localhost', '0.0.0.0', '::', '::1') -contains $hostName) { $hostName = 'localhost' }
    return ('http://{0}:{1}/' -f $hostName, $port)
}

function Test-PanelPort([int]$Port) {
    $found = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    return [bool]$found
}

# Zatrzymuje panel uruchomiony w tle razem z procesami agentow.
function Stop-Panel {
    if (-not (Test-Path $PidFile)) { return $false }
    $stopped = $false
    $id = 0
    $first = Get-Content -Path $PidFile -TotalCount 1
    if ([int]::TryParse([string]$first, [ref]$id) -and $id -gt 0) {
        $proc = Get-Process -Id $id -ErrorAction SilentlyContinue
        if ($proc -and $proc.ProcessName -like 'python*') {
            & taskkill.exe /PID $id /T /F | Out-Null
            $stopped = $true
        }
    }
    Remove-Item -Path $PidFile -ErrorAction SilentlyContinue
    return $stopped
}

function Remove-PanelTask {
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if (-not $task) { return $false }
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    return $true
}
