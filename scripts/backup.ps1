<#
.SYNOPSIS
  Back up the Iran Monitor news database and collector state, or restore a backup.

.DESCRIPTION
  Writes a pg_dump custom-format archive plus a copy of the collector state
  volume into runtime/backups (git-ignored). Verify restores the archive into a
  scratch database and compares row counts against it, leaving the live database
  untouched. Restore overwrites the live database and asks first.

  No credential is printed or written to the backup directory.

.EXAMPLE
  ./scripts/backup.ps1 -Action backup
  ./scripts/backup.ps1 -Action verify -Path runtime/backups/iran_monitor-20260922-085908.dump
  ./scripts/backup.ps1 -Action restore -Path runtime/backups/iran_monitor-20260922-085908.dump
#>
[CmdletBinding()]
param(
  [ValidateSet('backup', 'verify', 'restore', 'list')]
  [string]$Action = 'backup',
  [string]$Path,
  [string]$Project = 'iran-monitor-news',
  [int]$KeepDays = 30
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$BackupDir = Join-Path $Root 'runtime/backups'
$Db = "$Project-news-db-1"
$Collector = "$Project-news-collector-1"
$User = 'iran_monitor'
$Database = 'iran_monitor'

function Assert-Database {
  $state = docker inspect $Db --format '{{.State.Running}}' 2>$null
  if ($state -ne 'true') { throw "Database container $Db is not running." }
}

function Get-Counts([string]$target) {
  $sql = @"
SELECT 'news_items='||(SELECT count(*) FROM news_items)||
       ' sources='||(SELECT count(*) FROM sources)||
       ' provenance='||(SELECT count(*) FROM news_item_provenance)||
       ' runs='||(SELECT count(*) FROM collection_runs)||
       ' content='||(SELECT count(*) FROM news_item_content)||
       ' media='||(SELECT count(*) FROM news_item_media)||
       ' translations='||(SELECT count(*) FROM news_item_translations)
"@
  (docker exec $Db psql -U $User -d $target -t -A -c $sql).Trim()
}

switch ($Action) {

  'list' {
    if (-not (Test-Path $BackupDir)) { Write-Output 'No backups yet.'; break }
    Get-ChildItem "$BackupDir/*.dump" | Sort-Object LastWriteTime -Descending |
      Select-Object @{n = 'Backup'; e = { $_.Name } },
                    @{n = 'SizeKB'; e = { [math]::Round($_.Length / 1KB, 1) } },
                    LastWriteTime | Format-Table -AutoSize
  }

  'backup' {
    Assert-Database
    New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
    $stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMdd-HHmmss')
    $dump = Join-Path $BackupDir "iran_monitor-$stamp.dump"

    docker exec $Db pg_dump -U $User -d $Database -Fc -f /tmp/backup.dump
    if ($LASTEXITCODE -ne 0) { throw 'pg_dump failed.' }
    docker cp "${Db}:/tmp/backup.dump" $dump | Out-Null
    docker exec $Db rm -f /tmp/backup.dump

    # Collector checkpoints live in a named volume, not in PostgreSQL; a database
    # restore without them would replay feed positions the collector already passed.
    $stateDir = Join-Path $BackupDir "collector-state-$stamp"
    if ((docker inspect $Collector --format '{{.State.Running}}' 2>$null)) {
      docker cp "${Collector}:/state" $stateDir 2>$null | Out-Null
    }

    $hash = (Get-FileHash $dump -Algorithm SHA256).Hash
    $counts = Get-Counts $Database
    $meta = [ordered]@{
      created_utc     = (Get-Date).ToUniversalTime().ToString('o')
      dump            = Split-Path $dump -Leaf
      sha256          = $hash
      size_bytes      = (Get-Item $dump).Length
      database_counts = $counts
      collector_state = if (Test-Path $stateDir) { Split-Path $stateDir -Leaf } else { $null }
      note            = 'Restore with ./scripts/backup.ps1 -Action restore -Path <dump>. Contains no credentials.'
    }
    $meta | ConvertTo-Json | Set-Content "$dump.json" -Encoding utf8

    Write-Output "Backup written: $dump"
    Write-Output "SHA-256: $hash"
    Write-Output "Counts:  $counts"

    if ($KeepDays -gt 0) {
      $cutoff = (Get-Date).AddDays(-$KeepDays)
      Get-ChildItem "$BackupDir/*.dump" | Where-Object LastWriteTime -lt $cutoff | ForEach-Object {
        Write-Output "Removing backup older than $KeepDays days: $($_.Name)"
        Remove-Item $_.FullName, "$($_.FullName).json" -Force -ErrorAction SilentlyContinue
      }
    }
  }

  'verify' {
    Assert-Database
    if (-not $Path) { throw 'Pass -Path to the .dump file to verify.' }
    $full = (Resolve-Path $Path).Path
    $scratch = 'restore_verify_' + (Get-Date).ToUniversalTime().ToString('HHmmss')

    docker cp $full "${Db}:/tmp/verify.dump" | Out-Null
    docker exec $Db psql -U $User -d postgres -q -c "CREATE DATABASE $scratch" | Out-Null
    try {
      docker exec $Db pg_restore -U $User -d $scratch --no-owner /tmp/verify.dump 2>$null | Out-Null
      $restored = Get-Counts $scratch
      $live = Get-Counts $Database
      Write-Output "Restored: $restored"
      Write-Output "Live:     $live"
      if ($restored -eq $live) {
        Write-Output 'VERIFIED: restored counts match the live database.'
      }
      else {
        Write-Output 'DIFFERENT: the backup predates current data, which is expected for an older archive.'
      }
    }
    finally {
      docker exec $Db psql -U $User -d postgres -q -c "DROP DATABASE IF EXISTS $scratch" | Out-Null
      docker exec $Db rm -f /tmp/verify.dump
    }
  }

  'restore' {
    Assert-Database
    if (-not $Path) { throw 'Pass -Path to the .dump file to restore.' }
    $full = (Resolve-Path $Path).Path
    Write-Output "About to OVERWRITE database '$Database' from $full"
    Write-Output "Current: $(Get-Counts $Database)"
    $answer = Read-Host "Type RESTORE to continue"
    if ($answer -ne 'RESTORE') { Write-Output 'Cancelled. Nothing changed.'; break }

    # Stop the collector first: restoring under a live writer would interleave a
    # running cycle's inserts with the archive.
    docker stop $Collector 2>$null | Out-Null
    docker cp $full "${Db}:/tmp/restore.dump" | Out-Null
    docker exec $Db pg_restore -U $User -d $Database --clean --if-exists --no-owner /tmp/restore.dump
    docker exec $Db rm -f /tmp/restore.dump
    Write-Output "Restored: $(Get-Counts $Database)"
    Write-Output "Start the collector again with: docker compose -p $Project --env-file .env -f deployment/news-monitor/compose.yml --profile scheduler up -d news-collector"
  }
}
