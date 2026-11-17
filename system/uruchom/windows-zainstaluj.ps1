<#
  Instalacja serca IntegrateSystems na PC z Windows.
  - zadanie Harmonogramu zadań "IntegrateSystems-serce": start przy uruchomieniu systemu, bez logowania
    użytkownika, ponowne uruchomienie po awarii, kontrola co 5 min (drugi proces nie wystartuje: blokada w serce.py),
  - wyłączone usypianie i hibernacja przy zasilaniu sieciowym.

  Uruchom w PowerShell jako administrator:
    powershell -ExecutionPolicy Bypass -File system\uruchom\windows-zainstaluj.ps1
  Opcje:
    -Python C:\sciezka\python.exe   gdy python nie jest w PATH
    -S4U                            bez zapisywania hasła (wtedy git push przez HTTPS może nie mieć dostępu
                                    do Menedżera poświadczeń; użyj klucza SSH albo tokenu w adresie zdalnym)
  Usunięcie: Unregister-ScheduledTask -TaskName IntegrateSystems-serce
#>
param(
    [string]$Python = "",
    [switch]$S4U
)
$ErrorActionPreference = "Stop"
$Nazwa = "IntegrateSystems-serce"

$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) { Write-Error "Uruchom PowerShell jako administrator." }

$System = Split-Path -Parent $PSScriptRoot
$Serce = Join-Path $System "serce.py"
if (-not (Test-Path $Serce)) { Write-Error "Brak pliku $Serce" }

if (-not $Python) {
    $kandydat = Get-Command python.exe -ErrorAction SilentlyContinue
    if (-not $kandydat) { $kandydat = Get-Command py.exe -ErrorAction SilentlyContinue }
    if (-not $kandydat) { Write-Error "Nie znaleziono python.exe. Podaj -Python <ścieżka>." }
    $Python = $kandydat.Source
}
if ($Python -like "*\WindowsApps\*") {
    Write-Error "To skrót ze Sklepu Microsoft ($Python). Zainstaluj Python z python.org i podaj -Python <ścieżka>."
}
& $Python --version
if ($LASTEXITCODE -ne 0) { Write-Error "Python nie działa: $Python" }
if (-not (Get-Command git.exe -ErrorAction SilentlyContinue)) { Write-Error "Brak git w PATH." }

$Uzytkownik = "$env:USERDOMAIN\$env:USERNAME"
$Akcja = New-ScheduledTaskAction -Execute $Python -Argument "`"$Serce`"" -WorkingDirectory $System
$Wyzwalacze = @(
    (New-ScheduledTaskTrigger -AtStartup),
    (New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 5))
)
$Ustawienia = New-ScheduledTaskSettingsSet `
    -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -MultipleInstances IgnoreNew `
    -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -DontStopOnIdleEnd

if ($S4U) {
    $Zasada = New-ScheduledTaskPrincipal -UserId $Uzytkownik -LogonType S4U -RunLevel Limited
    Register-ScheduledTask -TaskName $Nazwa -Action $Akcja -Trigger $Wyzwalacze -Settings $Ustawienia `
        -Principal $Zasada -Description "IntegrateSystems: serce (bot, scalanie, raport)" -Force | Out-Null
} else {
    $Dane = Get-Credential -UserName $Uzytkownik -Message "Hasło konta Windows (zadanie działa bez logowania)"
    $Haslo = $Dane.GetNetworkCredential().Password
    Register-ScheduledTask -TaskName $Nazwa -Action $Akcja -Trigger $Wyzwalacze -Settings $Ustawienia `
        -User $Dane.UserName -Password $Haslo -RunLevel Limited `
        -Description "IntegrateSystems: serce (bot, scalanie, raport)" -Force | Out-Null
    $Haslo = $null
}

# Usypianie i hibernacja przy zasilaniu sieciowym: nigdy.
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0

Write-Host "Zadanie $Nazwa zarejestrowane. Python: $Python"
Write-Host "Start teraz: Start-ScheduledTask -TaskName $Nazwa"
Write-Host "Dziennik: LOKALNE_DIR\dziennik.log (domyślnie $env:USERPROFILE\.integrate-lokalne)"
