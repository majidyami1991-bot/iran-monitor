<#
.SYNOPSIS
  Registers the three scheduled tasks of the 3003 Local-AI lab. To be run BY
  THE OWNER (in this session Task Scheduler registration was denied:
  "Access is denied"). Review with -WhatIf first.

  IranMonitor-LocalAI-NewsSync     every 15 min at :05/:20/:35/:50 (4 min after the Production collector)
                                   scripts/news_sync_scheduled.py --max-new 500 (lock file, skips when Docker is down)
  IranMonitor-LocalAI-Health       every 2 min, read-only health probe -> runtime/ops-status/health/*.jsonl
  IranMonitor-LocalAI-Backup       daily 03:30, scripts/backup_local_ai.py (pg_dump + SHA-256 + isolated restore test + D: copy)

  All run as the signed-in user, "only when the user is logged on" (no password
  stored) — consistent with Docker Desktop, which itself only runs after sign-in.
  Hidden window (pythonw / -WindowStyle Hidden). Never deletes anything.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File "E:\Iran monitor-local-ai\scripts\register_local_ai_tasks.ps1" -WhatIf
  powershell -ExecutionPolicy Bypass -File "E:\Iran monitor-local-ai\scripts\register_local_ai_tasks.ps1"
  # remove again:  Unregister-ScheduledTask -TaskName 'IranMonitor-LocalAI-*' -Confirm:$false
#>
[CmdletBinding(SupportsShouldProcess)]
param(
  [string]$Root = 'E:\Iran monitor-local-ai',
  [string]$PythonW = 'C:\Program Files\Python312\pythonw.exe',
  [string]$HealthScript = 'E:\Iran monitor-redesign\scripts\ops\health_monitor.ps1'
)
$user = "$env:USERDOMAIN\$env:USERNAME"
$principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
  -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

function Next-Slot([int[]]$minutes) {
  $n = Get-Date
  foreach ($h in 0..1) { foreach ($m in $minutes) { $t = $n.Date.AddHours($n.Hour + $h).AddMinutes($m); if ($t -gt $n.AddMinutes(1)) { return $t } } }
}

$tasks = @(
  @{ Name = 'IranMonitor-LocalAI-NewsSync'; Desc = 'One-way read-only news sync Production -> 3003 (scripts/news_sync_scheduled.py)'
     Action = (New-ScheduledTaskAction -Execute $PythonW -Argument "`"$Root\scripts\news_sync_scheduled.py`" --max-new 500" -WorkingDirectory $Root)
     Trigger = (New-ScheduledTaskTrigger -Once -At (Next-Slot @(5, 20, 35, 50)) -RepetitionInterval (New-TimeSpan -Minutes 15)) },
  @{ Name = 'IranMonitor-LocalAI-Health'; Desc = 'Read-only health probe of 3001/3003/OpenCTI/Docker/collector (runtime/ops-status/health)'
     Action = (New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$HealthScript`" -LogDir `"$Root\runtime\ops-status\health`"")
     Trigger = (New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(2) -RepetitionInterval (New-TimeSpan -Minutes 2)) },
  @{ Name = 'IranMonitor-LocalAI-Backup'; Desc = '3003 DB backup + SHA-256 + isolated restore test + D: copy (scripts/backup_local_ai.py)'
     Action = (New-ScheduledTaskAction -Execute $PythonW -Argument "`"$Root\scripts\backup_local_ai.py`"" -WorkingDirectory $Root)
     Trigger = (New-ScheduledTaskTrigger -Daily -At '03:30') }
)
foreach ($t in $tasks) {
  if ($PSCmdlet.ShouldProcess($t.Name, 'Register scheduled task')) {
    Register-ScheduledTask -TaskName $t.Name -Description $t.Desc -Action $t.Action -Trigger $t.Trigger -Settings $settings -Principal $principal -Force | Out-Null
    $i = Get-ScheduledTaskInfo -TaskName $t.Name
    "{0}: registered, next run {1}" -f $t.Name, $i.NextRunTime
  }
}
