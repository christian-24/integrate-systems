# Claude Code hook -> Ratusz Port (Windows). One script for every hook event; -Gate for PreToolUse.
#
# %USERPROFILE%\.claude\settings.json, with your own URL and token in "env":
#   "env": { "RATUSZ_URL": "http://mac.tailnet:4791", "RATUSZ_TOKEN": "...", "RATUSZ_MACHINE": "win-pc" },
#   "hooks": {
#     "SessionStart":     [{"hooks": [{"type": "command", "command": "powershell -NoProfile -ExecutionPolicy Bypass -File C:\\ratusz\\adapters\\claude-hook.ps1"}]}],
#     "UserPromptSubmit": [{"hooks": [{"type": "command", "command": "powershell -NoProfile -ExecutionPolicy Bypass -File C:\\ratusz\\adapters\\claude-hook.ps1"}]}],
#     "Stop":             [{"hooks": [{"type": "command", "command": "powershell -NoProfile -ExecutionPolicy Bypass -File C:\\ratusz\\adapters\\claude-hook.ps1"}]}],
#     "Notification":     [{"hooks": [{"type": "command", "command": "powershell -NoProfile -ExecutionPolicy Bypass -File C:\\ratusz\\adapters\\claude-hook.ps1"}]}],
#     "SessionEnd":       [{"hooks": [{"type": "command", "command": "powershell -NoProfile -ExecutionPolicy Bypass -File C:\\ratusz\\adapters\\claude-hook.ps1"}]}],
#     "PreToolUse":       [{"matcher": "Bash", "hooks": [{"type": "command", "command": "powershell -NoProfile -ExecutionPolicy Bypass -File C:\\ratusz\\adapters\\claude-hook.ps1 -Gate", "timeout": 660}]}]
#   }
param([switch]$Gate)
$ErrorActionPreference = "SilentlyContinue"
$Url = if ($env:RATUSZ_URL) { $env:RATUSZ_URL.TrimEnd("/") } else { "http://127.0.0.1:4791" }
$Token = $env:RATUSZ_TOKEN
$Machine = if ($env:RATUSZ_MACHINE) { $env:RATUSZ_MACHINE } else { $env:COMPUTERNAME.ToLower() }
$DefaultRules = @("git push --force", "rm -rf", "DROP TABLE", "deploy", "migrate")
$Headers = @{ "Content-Type" = "application/json" }
if ($Token) { $Headers["Authorization"] = "Bearer $Token" }

function Call($Path, $Body) {
  if ($null -ne $Body) { return Invoke-RestMethod -Uri ($Url + $Path) -Method Post -Headers $Headers -Body ([System.Text.Encoding]::UTF8.GetBytes(($Body | ConvertTo-Json -Depth 6 -Compress))) -TimeoutSec 6 }
  return Invoke-RestMethod -Uri ($Url + $Path) -Method Get -Headers $Headers -TimeoutSec 6
}
function LastAssistantText($Transcript) {
  if (-not $Transcript -or -not (Test-Path $Transcript)) { return "" }
  $lines = Get-Content -Path $Transcript -Tail 300 -Encoding UTF8
  for ($i = $lines.Count - 1; $i -ge 0; $i--) {
    try { $e = $lines[$i] | ConvertFrom-Json } catch { continue }
    if ($e.type -eq "assistant") {
      $t = ($e.message.content | Where-Object { $_.type -eq "text" } | ForEach-Object { $_.text }) -join " "
      if ($t.Trim()) { return $t.Trim().Substring(0, [Math]::Min(500, $t.Trim().Length)) }
    }
  }
  return ""
}

$raw = [Console]::In.ReadToEnd()
try { $h = $raw | ConvertFrom-Json } catch { $h = @{} }
$cwd = if ($h.cwd) { $h.cwd } else { (Get-Location).Path }
$project = Split-Path -Leaf $cwd
$base = @{ source = "claude-code"; machine = $Machine; project = $project; root = $cwd; session = "$($h.session_id)"; payload = @{ name = "Claude Code · $project" } }

if ($Gate) {
  $tool = "$($h.tool_name)"
  $text = if ($tool -eq "Bash") { "$($h.tool_input.command)" } else { ($h.tool_input | ConvertTo-Json -Compress -Depth 6) }
  $rules = $DefaultRules
  try { $c = Call ("/api/charter?name=" + [Uri]::EscapeDataString($project)); if ($c.rules) { $rules = $c.rules } } catch {}
  $hit = $rules | Where-Object { $_ -and $text.ToLower().Contains($_.ToLower()) } | Select-Object -First 1
  if (-not $hit) { exit 0 }
  try {
    $d = Call "/api/decisions" @{ kind = "approval"; source = "claude-code"; machine = $Machine; project = $project; session = "$($h.session_id)"; agent = "Claude Code · $project"; title = "Zgoda na: " + $text.Substring(0, [Math]::Min(120, $text.Length)); command = $text.Substring(0, [Math]::Min(500, $text.Length)); rule = $hit }
  } catch { [Console]::Error.WriteLine("ratusz: Port nieosiągalny; zwykłe pytanie o zgodę"); exit 0 }
  $seconds = if ($env:RATUSZ_GATE_SECONDS) { [double]$env:RATUSZ_GATE_SECONDS } else { 600 }
  $deadline = (Get-Date).AddSeconds($seconds); $status = "pending"
  while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 2
    try { $status = (Call "/api/decisions/$($d.id)").status } catch { continue }
    if ($status -ne "pending") { break }
  }
  if ($status -eq "approved") { $out = @{ permissionDecision = "allow"; permissionDecisionReason = "Ratusz: zatwierdzone z $Machine" } }
  elseif ($status -eq "rejected") { $out = @{ permissionDecision = "deny"; permissionDecisionReason = "Ratusz: odrzucone. Zaproponuj inne rozwiązanie i zapytaj." } }
  else { [Console]::Error.WriteLine("ratusz: petycja bez odpowiedzi; zwykłe pytanie o zgodę"); exit 0 }
  $out["hookEventName"] = "PreToolUse"
  [Console]::Out.Write((@{ hookSpecificOutput = $out } | ConvertTo-Json -Compress -Depth 4))
  exit 0
}

switch ("$($h.hook_event_name)") {
  "SessionStart"     { $e = @{ type = "session_started"; title = "nowa sesja w $project"; verb = "zaczyna" } }
  "UserPromptSubmit" { $e = @{ type = "turn_started"; title = "$($h.prompt)".Substring(0, [Math]::Min(160, "$($h.prompt)".Length)); verb = "pracuje" } }
  "Stop"             { $e = @{ type = "turn_finished"; title = "skończył turę"; verb = "skończył turę"; payload = @{ name = "Claude Code · $project"; text = (LastAssistantText $h.transcript_path) } } }
  "Notification"     { $e = @{ type = "blocked"; title = "$($h.message)"; verb = "czeka na Ciebie" } }
  "SessionEnd"       { $e = @{ type = "session_ended"; title = "sesja zakończona ($($h.reason))"; verb = "skończył" } }
  default            { exit 0 }
}
$body = $base.Clone(); foreach ($k in $e.Keys) { $body[$k] = $e[$k] }
try { Call "/api/events" $body | Out-Null } catch { [Console]::Error.WriteLine("ratusz: $_") }
