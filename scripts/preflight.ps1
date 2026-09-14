# Read-only installation gate. No configuration output or credentials are printed.
$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$pin = '18fdf8512f69e63d0856a7a4f5633ef7e482e5c0'
$script:passedChecks = 0
$sourceHash = '3F7522C94952DD85254F45CADF600A64EE6F264D27E30E3D2BF3297D59C47980'
function Require($condition, [string]$message) {
    if (-not $condition) { throw $message }
    $script:passedChecks++
    if ($message.EndsWith(' SET')) { Write-Output $message }
}
function Native([string]$exe, [string[]]$arguments) {
    # Keep stdout in memory; discard potentially credential-bearing diagnostics.
    $old = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $result = @(& $exe @arguments 2>$null)
    $code = $LASTEXITCODE
    $ErrorActionPreference = $old
    if ($code -ne 0) { throw "Read-only command failed: $exe (details withheld)" }
    return ($result -join "`n")
}
try {
    $context = Native docker @('context','show')
    Require ($context.Trim() -eq 'desktop-linux') 'Docker context desktop-linux'
    $info = (Native docker @('info','--format','{{json .}}')) | ConvertFrom-Json
    Require (-not [string]::IsNullOrWhiteSpace($info.ServerVersion)) 'Docker Engine reachable'
    $composeVersion = Native docker @('compose','version','--short')
    Require ([version]($composeVersion.Trim().TrimStart('v')) -ge [version]'2.24.4') 'Compose supports override merge tags'
    Require ($info.NCPU -ge 8) 'Docker CPUs >= 8'
    Require ($info.MemTotal -ge 16GB) 'Docker RAM >= 16 GiB'
    Require ($info.KernelVersion -match 'WSL2') 'Docker uses WSL2'
    $running = (Native wsl @('--list','--running','--quiet')).Replace([string][char]0,'')
    Require ($running -match '(?m)^\s*docker-desktop\s*$') 'docker-desktop already running'
    $map = Native wsl @('-d','docker-desktop','-u','root','--','sysctl','vm.max_map_count')
    if ($map -notmatch '=\s*(\d+)' -or [long]$Matches[1] -lt 1048575) {
        Write-Output 'wsl -d docker-desktop -u root -- sysctl -w vm.max_map_count=1048575'
        throw 'vm.max_map_count below 1048575 or unreadable; explicit approval required to correct it'
    }
    Write-Output 'PASS vm.max_map_count >= 1048575'
    $listeners = @(Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -eq 8080 })
    Require ($listeners.Count -eq 0) 'Port 8080 not listening'
    foreach ($family in @('ipv4','ipv6')) {
        $ranges = Native netsh @('interface',$family,'show','excludedportrange','protocol=tcp')
        foreach ($line in ($ranges -split "`n")) {
            if ($line -match '^\s*(\d+)\s+(\d+)\s*\*?\s*$') {
                Require (-not (8080 -ge [int]$Matches[1] -and 8080 -le [int]$Matches[2])) "Port 8080 outside $family reservation"
            }
        }
    }
    # Known backing file from Phase 0. Fail closed if it moves.
    $disk = Join-Path $env:LOCALAPPDATA 'Docker\wsl\disk\docker_data.vhdx'
    Require (Test-Path -LiteralPath $disk) 'Known Docker backing disk exists'
    $drive = [IO.Path]::GetPathRoot($disk).Substring(0,1)
    $free = (Get-Volume -DriveLetter $drive).SizeRemaining
    Require ($free -ge 64GB) 'Docker backing drive has >= 64 GiB free (initial floor)'
    $projectDrive = [IO.Path]::GetPathRoot($root).Substring(0,1)
    Require ((Get-Volume -DriveLetter $projectDrive).SizeRemaining -ge 1GB) 'Project drive has >= 1 GiB free'
    $envPath = Join-Path $root '.env'
    Require (Test-Path -LiteralPath $envPath) '.env exists'
    $values = @{}
    foreach ($line in [IO.File]::ReadAllLines($envPath)) {
        if ($line -match '^([A-Z][A-Z0-9_]*)=(.*)$') {
            if ($values.ContainsKey($Matches[1])) { throw 'Duplicate environment key' }
            $values[$Matches[1]] = $Matches[2]
        } elseif ($line.Trim() -and -not $line.Trim().StartsWith('#')) { throw 'Unsupported environment line' }
    }
    $upstream = Join-Path $root 'vendor\opencti-docker'
    Require (Test-Path -LiteralPath (Join-Path $upstream '.git')) 'Submodule exists'
    Require ((Native git @('-C',$upstream,'rev-parse','HEAD')).Trim() -eq $pin) 'Submodule exact commit pin'
    Require ([string]::IsNullOrWhiteSpace((Native git @('-C',$upstream,'status','--porcelain')))) 'Submodule unmodified'
    $composePath = Join-Path $root 'deployment\opencti\compose.pinned.yml'
    $required = @([regex]::Matches([IO.File]::ReadAllText($composePath), '\$\{([A-Z][A-Z0-9_]*)') | ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique)
    Require ([Convert]::FromBase64String($values.OPENCTI_ENCRYPTION_KEY).Length -eq 32) 'Encryption key is 32 bytes'
    $seen = @{}
    foreach ($key in $required) {
        Require ($values.ContainsKey($key) -and -not [string]::IsNullOrWhiteSpace($values[$key])) "$key SET"
        Require ([Environment]::GetEnvironmentVariable($key) -eq $null) "$key has no shell override"
        if ($key.EndsWith('_ID') -or $key -eq 'OPENCTI_ADMIN_TOKEN') {
            $v = $values[$key]
            Require ($v -match '^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-4[0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$') "$key UUIDv4 valid"
            Require (-not $seen.ContainsKey($v)) "$key UUID unique"
            $seen[$v] = $true
        } elseif ($key -match 'PASSWORD|PASS$|ACCESS_KEY|ROOT_USER|DEFAULT_USER') {
            Require ($values[$key] -match '^[0-9a-f]{64}$') "$key generated credential format"
        }
    }
    Require ($values.COMPOSE_PROJECT_NAME -eq 'iran-monitor-opencti' -and $values.OPENCTI_PORT -eq '8080' -and $values.OPENCTI_HOST -eq 'localhost' -and $values.OPENCTI_EXTERNAL_SCHEME -eq 'http') 'Local web address and project name'
    Require ((Native git @('-C',$root,'check-ignore','.env')).Trim() -eq '.env') '.env ignored'
    Require ([string]::IsNullOrWhiteSpace((Native git @('-C',$root,'ls-files','--','.env')))) '.env untracked'
    Require ((Get-FileHash -LiteralPath (Join-Path $root 'sites.docx') -Algorithm SHA256).Hash -eq $sourceHash) 'Original source hash unchanged'
    $argsCompose = @('compose','--project-name','iran-monitor-opencti','--env-file',$envPath,'-f',$composePath)
    $config = (Native docker ($argsCompose + @('config','--format','json'))) | ConvertFrom-Json
    Require ($config.name -eq 'iran-monitor-opencti') 'Effective Compose project name'
    $published = @()
    foreach ($entry in $config.services.PSObject.Properties) {
        $s = $entry.Value
        Require (-not $s.container_name -and -not $s.privileged -and $s.network_mode -ne 'host' -and -not $s.build) "$($entry.Name) isolation"
        Require ($s.image -notmatch ':(latest|rolling|master|edge|nightly)$' -and $s.image -match '[:@]') "$($entry.Name) versioned image"
        foreach ($mount in $s.volumes) { Require ($mount.source -notmatch 'docker.sock' -and $mount.target -notmatch 'docker.sock') "$($entry.Name) no Docker socket" }
        foreach ($port in $s.ports) {
            $published += $port
            Require ($entry.Name -eq 'opencti' -and $port.published -eq '8080' -and $port.target -eq 8080 -and $port.host_ip -eq '127.0.0.1') 'Only loopback OpenCTI port published'
        }
    }
    Require ($published.Count -eq 1) 'Exactly one host port publication'
    foreach ($kind in @('networks','volumes')) {
        foreach ($entry in $config.$kind.PSObject.Properties) {
            Require (-not $entry.Value.external -and $entry.Value.name.StartsWith('iran-monitor-opencti_')) "$kind project isolation"
        }
    }
    $conflicts = Native docker @('ps','-aq','--filter','label=com.docker.compose.project=iran-monitor-opencti')
    Require ([string]::IsNullOrWhiteSpace($conflicts)) 'No existing project containers'
    foreach ($kind in @('network','volume')) {
        $names = Native docker @($kind,'ls','--format','{{.Name}}')
        Require ($names -notmatch '(?m)^iran-monitor-opencti_') "No existing project $kind names"
    }
    $null = Native docker ($argsCompose + @('config','--images'))
    Write-Output 'WARNING Runtime sysctl is not persistent; image tags are not immutable digests. No images pulled or runtime tested.'
    Write-Output ('PASS ' + $script:passedChecks + ' read-only checks; Docker, WSL2, resources, source hash, pin, credentials and port isolation validated')
    Write-Output 'PREFLIGHT_STATUS=PASS'
    exit 0
} catch {
    # Only explicitly authored failures are safe to print; never print native payloads.
    if ($_.InvocationInfo.MyCommand.Name -in @('Require','Native') -or $_.Exception.Message -match '^(Duplicate environment|Unsupported environment|vm.max_map_count)') {
        Write-Output ('FAIL ' + $_.Exception.Message)
    } else { Write-Output 'FAIL Read-only validation could not complete; inspect script and tool availability without logging credentials.' }
    Write-Output 'PREFLIGHT_STATUS=FAIL'
    exit 1
}
