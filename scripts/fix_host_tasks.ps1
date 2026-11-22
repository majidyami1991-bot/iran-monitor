<#
.SYNOPSIS
  Fixes or removes the legacy host-side scheduled tasks that cause the flashing console window.
  Must be executed in an elevated PowerShell session (Run as Administrator).
#>

[CmdletBinding()]
param(
    [ValidateSet('Remove', 'Disable', 'Fix')]
    [string]$Action = 'Remove'
)

$tasks = @('IranMonitor-LocalAI-Health', 'IranMonitor-LocalAI-NewsSync', 'IranMonitor-LocalAI-Backup')

switch ($Action) {
    'Remove' {
        Write-Host "Removing legacy scheduled tasks..." -ForegroundColor Cyan
        foreach ($t in $tasks) {
            if (Get-ScheduledTask -TaskName $t -ErrorAction SilentlyContinue) {
                Unregister-ScheduledTask -TaskName $t -Confirm:$false
                Write-Host "  [OK] Removed task: $t" -ForegroundColor Green
            } else {
                Write-Host "  [--] Task not found: $t" -ForegroundColor Gray
            }
        }
        Write-Host "All legacy tasks removed. No more console window flashing will occur." -ForegroundColor Green
    }
    'Disable' {
        Write-Host "Disabling legacy scheduled tasks..." -ForegroundColor Cyan
        foreach ($t in $tasks) {
            if (Get-ScheduledTask -TaskName $t -ErrorAction SilentlyContinue) {
                Disable-ScheduledTask -TaskName $t | Out-Null
                Write-Host "  [OK] Disabled task: $t" -ForegroundColor Yellow
            }
        }
    }
}
