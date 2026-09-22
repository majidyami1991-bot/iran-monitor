<#
.SYNOPSIS
  Verify the collector recovers from a restart without losing or duplicating data.

.DESCRIPTION
  Records the database state, restarts the collector container, and checks that
  items and checkpoints survive, that scheduling resumes, that no run is left in
  `running`, and that no duplicate item was created.

  Only the collector container is restarted. The database, API and web services
  and every volume are left alone; nothing is deleted.

.EXAMPLE
  ./scripts/restart-recovery-test.ps1
#>
[CmdletBinding()]
param(
  [string]$Project = 'iran-monitor-news',
  [int]$SettleSeconds = 30
)

$ErrorActionPreference = 'Stop'
$Db = "$Project-news-db-1"
$Collector = "$Project-news-collector-1"
$Api = "$Project-news-api-1"
$User = 'iran_monitor'
$Database = 'iran_monitor'

function Sql([string]$query) { (docker exec $Db psql -U $User -d $Database -t -A -c $query).Trim() }

function Snapshot {
  [ordered]@{
    items         = [int](Sql 'SELECT count(*) FROM news_items')
    sources       = [int](Sql 'SELECT count(*) FROM sources')
    provenance    = [int](Sql 'SELECT count(*) FROM news_item_provenance')
    runs          = [int](Sql 'SELECT count(*) FROM collection_runs')
    content       = [int](Sql 'SELECT count(*) FROM news_item_content')
    media         = [int](Sql 'SELECT count(*) FROM news_item_media')
    distinct_urls = [int](Sql 'SELECT count(DISTINCT canonical_url) FROM news_items')
    checkpoints   = [int](docker exec $Collector sh -c 'ls -1 /state/*.json 2>/dev/null | wc -l').Trim()
  }
}

$results = @()
function Check([string]$name, [bool]$pass, $detail) {
  $script:results += [pscustomobject]@{ Check = $name; Result = $(if ($pass) { 'PASS' } else { 'FAIL' }); Detail = "$detail" }
}

Write-Output 'Recording state before restart...'
$before = Snapshot
$before.GetEnumerator() | ForEach-Object { Write-Output ("  {0,-14} {1}" -f $_.Key, $_.Value) }

# A cycle in flight holds the advisory lock. Restarting mid-cycle is a valid
# thing to test, but it makes "no run left running" ambiguous, so wait it out.
$waited = 0
while ((Sql "SELECT count(*) FROM collection_runs WHERE status='running'") -ne '0' -and $waited -lt 180) {
  Write-Output '  a cycle is in flight; waiting for it to finish...'
  Start-Sleep -Seconds 10
  $waited += 10
}

Write-Output "`nRestarting the collector container..."
docker restart $Collector | Out-Null

Write-Output "Waiting $SettleSeconds seconds for it to settle..."
Start-Sleep -Seconds $SettleSeconds

$after = Snapshot
Write-Output "`nState after restart:"
$after.GetEnumerator() | ForEach-Object { Write-Output ("  {0,-14} {1}" -f $_.Key, $_.Value) }

Check 'container is running'      ((docker inspect $Collector --format '{{.State.Running}}') -eq 'true') 'docker inspect'
Check 'no news item lost'         ($after.items -ge $before.items)           "before=$($before.items) after=$($after.items)"
Check 'no provenance row lost'    ($after.provenance -ge $before.provenance) "before=$($before.provenance) after=$($after.provenance)"
Check 'no source lost'            ($after.sources -eq $before.sources)       "before=$($before.sources) after=$($after.sources)"
Check 'no extracted content lost' ($after.content -ge $before.content)       "before=$($before.content) after=$($after.content)"
Check 'checkpoints survived'      ($after.checkpoints -ge $before.checkpoints) "before=$($before.checkpoints) after=$($after.checkpoints)"
Check 'no duplicate canonical URL' ($after.items -eq $after.distinct_urls)   "items=$($after.items) distinct=$($after.distinct_urls)"

$stuck = [int](Sql "SELECT count(*) FROM collection_runs WHERE status='running' AND started_at < now() - interval '1 hour'")
Check 'no run stuck in running' ($stuck -eq 0) "stuck=$stuck"

$health = docker exec $Collector cat /state/health.json 2>$null | ConvertFrom-Json
Check 'scheduling resumed'  ($health.enabled -eq $true) "enabled=$($health.enabled)"
Check 'next run scheduled'  ([bool]$health.next_run_at) "next_run_at=$($health.next_run_at)"

$revision = (docker exec $Collector cat /app/BUILD_INFO.json | ConvertFrom-Json).git_revision
$expected = (docker exec $Collector printenv EXPECTED_COLLECTOR_GIT_REVISION).Trim()
Check 'image revision matches the pin' ($revision -eq $expected) "image=$($revision.Substring(0,12)) expected=$($expected.Substring(0,12))"

Write-Output "`nResults:"
$results | Format-Table -AutoSize
$failed = @($results | Where-Object Result -eq 'FAIL').Count
Write-Output "$($results.Count - $failed)/$($results.Count) passed"
if ($failed) { exit 1 }
