# Watchdog for local model evaluation runs (phase 9).
# Samples every 5 s: total CPU, llama-server RSS, free RAM, and Production health (every 15 s).
# On RSS > LimitGB, or two consecutive non-200 health checks, it unloads the model
# (keep_alive 0) and writes BREACH lines. Output paths are explicit parameters so
# no earlier evidence file can be overwritten.
param(
  [Parameter(Mandatory = $true)][string]$Out,
  [Parameter(Mandatory = $true)][string]$Model,
  [double]$LimitGB = 24,
  [int]$MaxMinutes = 240
)
if (Test-Path $Out) { throw "refusing to overwrite existing file: $Out" }
'time,total_cpu_pct,runner_rss_gb,free_ram_gb,prod_3001,event' | Out-File -Encoding utf8 $Out
$fails = 0; $peak = 0.0
$end = (Get-Date).AddMinutes($MaxMinutes)
$i = 0
while ((Get-Date) -lt $end) {
  $cpu = (Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average
  $rss = ((Get-Process llama-server -ErrorAction SilentlyContinue | Measure-Object WorkingSet64 -Sum).Sum) / 1GB
  $free = (Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1MB
  if ($rss -gt $peak) { $peak = $rss }
  $code = ''
  $event = ''
  if ($i % 3 -eq 0) {
    try { $code = (Invoke-WebRequest -UseBasicParsing -TimeoutSec 10 http://127.0.0.1:3001/).StatusCode } catch { $code = 'ERR' }
    if ($code -ne 200) { $fails++ } else { $fails = 0 }
  }
  if ($rss -gt $LimitGB) { $event = "BREACH_RAM_$([math]::Round($rss,2))GB" }
  if ($fails -ge 2) { $event = 'BREACH_PROD_HEALTH' }
  if ($event) {
    try { Invoke-RestMethod -Method Post -Uri http://127.0.0.1:11434/api/generate -Body (@{model = $Model; keep_alive = 0} | ConvertTo-Json) -ContentType 'application/json' | Out-Null } catch {}
  }
  '{0},{1},{2:N2},{3:N1},{4},{5}' -f (Get-Date -Format 'HH:mm:ss'), $cpu, $rss, $free, $code, $event | Out-File -Append -Encoding utf8 $Out
  if ($event) { "BREACH $event" | Out-File -Append -Encoding utf8 ($Out + '.breach') }
  $i++
  Start-Sleep -Seconds 5
}
