# run.ps1 - one DuoTest run: host A plus 1-3 clients, one plan, logs and snapshots into <Work>\runs\<Tag>.
#
#   .\run.ps1 -Tag smoke1 -Clients 1 -Plan smoke
#   .\run.ps1 -Tag edge1 -Clients 2 -Plan edge -Minutes 40
#   .\run.ps1 -Tag mem1 -Clients 1 -Plan rounds -Rounds plans\rounds_mem.txt -Mem
#
# The game copies A..D live in -Work (default %LOCALAPPDATA%\DuoTest, built by setup.sh; they are hardlinks
# into the Among Us install and have to stay on drive C). AppData is shared with the real game: the real save
# files are backed up before and put back after every run.
# -Tiering: run with .NET tiered compilation ON, like a normal player start (default off: the detour-loss
# described in memory project-tiering-detour-loss would make results depend on timing).
param(
    [string]$Tag = "run",
    [int]$Clients = 1,
    [string]$Plan = "smoke",
    [int]$Minutes = 25,
    [string]$Rounds = "",
    [switch]$Mem,
    [switch]$Prof,
    [switch]$Trace,
    [switch]$Tiering,
    [string]$Work = "$env:LOCALAPPDATA\DuoTest"
)
$T = $Work
$AD = "$env:USERPROFILE\AppData\LocalLow\Innersloth\Among Us"
function DuoProcs() { @(Get-Process "Among Us" -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "$T\*" }) }
if (Get-Process "Among Us" -ErrorAction SilentlyContinue | Where-Object { $_.Path -notlike "$T\*" }) { "USER GAME RUNNING - abort"; exit 3 }
if (-not (Test-Path "$T\A\Among Us.exe")) { "no game copies in $T - run setup.sh first"; exit 4 }
$letters = @("A","B","C","D")[0..$Clients]

# shared AppData: back up the real save files, restore them afterwards
$bk = "$T\appdata_backup"
New-Item -ItemType Directory -Force $bk | Out-Null
Get-ChildItem $AD -File | Where-Object { $_.Name -match '^(player\.amogus|settings\.amogus|playerStats3|regionInfo\.json)' -and $_.Name -notmatch '_DUO' } | Copy-Item -Destination $bk -Force

foreach ($x in $letters) {
  Remove-Item "$T\$x\BepInEx\LogOutput*.log", "$T\$x\player.log", "$T\$x\duo_snap.tsv", "$T\$x\duo_mem.tsv" -ErrorAction SilentlyContinue
  if ($x -eq "A") { "host A $Clients $Plan" | Set-Content "$T\A\duo_role.txt" } else { "client $x" | Set-Content "$T\$x\duo_role.txt" }
  if ($Mem) { "" | Set-Content "$T\$x\duo_mem_on" } else { Remove-Item "$T\$x\duo_mem_on" -ErrorAction SilentlyContinue }
  if ($Prof) { "" | Set-Content "$T\$x\duo_prof_on" } else { Remove-Item "$T\$x\duo_prof_on" -ErrorAction SilentlyContinue }
  if ($Trace) { "" | Set-Content "$T\$x\duo_trace_on" } else { Remove-Item "$T\$x\duo_trace_on" -ErrorAction SilentlyContinue }
  Remove-Item "$T\$x\duo_trace.tsv" -ErrorAction SilentlyContinue
}
if ($Rounds -ne "") {
  $src = if ([System.IO.Path]::IsPathRooted($Rounds)) { $Rounds } else { Join-Path $PSScriptRoot $Rounds }
  Copy-Item $src "$T\A\rounds.txt" -Force
}
if ($Tiering) { Remove-Item Env:\DOTNET_TieredCompilation -ErrorAction SilentlyContinue } else { $env:DOTNET_TieredCompilation = "0" }

function Launch($x) {
  tasklist /FI "IMAGENAME eq Among Us.exe"
  if (Get-Process "Among Us" -ErrorAction SilentlyContinue | Where-Object { $_.Path -notlike "$T\*" }) { throw "Fremdes Spiel gestartet, Test angehalten" }
  tasklist /FI "IMAGENAME eq Among Us.exe"
  if (Get-Process "Among Us" -ErrorAction SilentlyContinue | Where-Object { $_.Path -notlike "$T\*" }) { throw "Fremdes Spiel gestartet, Test angehalten" }
  Start-Process -FilePath "$T\$x\Among Us.exe" -WorkingDirectory "$T\$x" -ArgumentList @("-screen-fullscreen","0","-screen-width","800","-screen-height","450","-logFile","`"$T\$x\player.log`"")
}
function LogHas($x, $pat) { [bool](Get-Content "$T\$x\BepInEx\LogOutput.log" -ErrorAction SilentlyContinue | Select-String $pat) }

$t0 = Get-Date
Launch "A"
$deadline = (Get-Date).AddMinutes(4)
while ((Get-Date) -lt $deadline -and -not (LogHas "A" "DUO .* (lobby up|no lobby|host failed)")) {
  Start-Sleep 3
  if (-not (DuoProcs | Where-Object { $_.Path -like "$T\A\*" })) { "host process gone during boot"; break }
}
if (LogHas "A" "DUO .* lobby up") { foreach ($x in $letters) { if ($x -ne "A") { Launch $x; Start-Sleep 20 } } }
$deadline = $t0.AddMinutes($Minutes)
$relaunched = @{ "B" = 0; "C" = 0; "D" = 0 }
while ((Get-Date) -lt $deadline) {
  Start-Sleep 5
  if (LogHas "A" "DUO .* (DONE|no lobby|clients never came|host failed)") { Start-Sleep 8; break }
  foreach ($x in $letters) {
    if ($x -eq "A" -or $relaunched[$x] -ge 2) { continue }
    $alive = DuoProcs | Where-Object { $_.Path -like "$T\$x\*" }
    if (-not $alive -and -not (LogHas $x "DUO .* (client in lobby|quit)")) {
      $relaunched[$x] = $relaunched[$x] + 1
      "client $x died before joining, relaunch #$($relaunched[$x])"
      $crash = Join-Path $T ("runs\" + $Tag + "\crash_" + $x + "_" + $relaunched[$x])
      New-Item -ItemType Directory -Force $crash | Out-Null
      Copy-Item "$T\$x\BepInEx\LogOutput.log", "$T\$x\player.log" $crash -ErrorAction SilentlyContinue
      Launch $x
    }
  }
  if (-not (DuoProcs | Where-Object { $_.Path -like "$T\A\*" })) { "host process gone"; Start-Sleep 35; break }
}
$elapsed = [int]((Get-Date) - $t0).TotalSeconds
"elapsed: $elapsed s"
$out = "$T\runs\$Tag"
New-Item -ItemType Directory -Force $out | Out-Null
$left = DuoProcs
$peaks = @()
foreach ($p in $left) { $peaks += "$($p.Path.Split('\')[-2])`t$([int]($p.PeakWorkingSet64/1MB))" ; "mem $($p.Path.Split('\')[-2]): $([int]($p.PeakWorkingSet64/1MB)) MB peak" }
$left | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep 2
$peaks | Set-Content "$out\peak_mb.tsv"
"$Plan`t$Clients`t$elapsed`t$([bool]$Tiering)" | Set-Content "$out\run_info.tsv"
foreach ($x in $letters) {
  Copy-Item "$T\$x\BepInEx\LogOutput.log" "$out\log_$x.log" -ErrorAction SilentlyContinue
  Copy-Item "$T\$x\player.log" "$out\player_$x.log" -ErrorAction SilentlyContinue
  Copy-Item "$T\$x\duo_snap.tsv" "$out\snap_$x.tsv" -ErrorAction SilentlyContinue
  Copy-Item "$T\$x\duo_mem.tsv" "$out\mem_$x.tsv" -ErrorAction SilentlyContinue
  Copy-Item "$T\$x\duo_trace.tsv" "$out\trace_$x.tsv" -ErrorAction SilentlyContinue
  Remove-Item "$T\$x\duo_mem_on", "$T\$x\duo_prof_on", "$T\$x\duo_trace_on" -ErrorAction SilentlyContinue
}
Remove-Item "$T\A\rounds.txt" -ErrorAction SilentlyContinue
# restore the real save files
Get-ChildItem $bk -File | Copy-Item -Destination $AD -Force
"restored: " + ((Get-ChildItem $bk -File).Name -join ", ")
