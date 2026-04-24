[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

function Get-CommandInfo {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    $command = Get-Command $Name -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $command) {
        return [ordered]@{
            name = $Name
            available = $false
        }
    }

    $version = $null
    try {
        $version_output = & $command.Source --version 2>&1 | Out-String
        if ($version_output) {
            $version = $version_output.Trim()
        }
    }
    catch {
        $version = $null
    }

    return [ordered]@{
        name = $Name
        available = $true
        path = $command.Source
        command_type = [string]$command.CommandType
        version = $version
    }
}

$python = Get-CommandInfo -Name "python"
$skill_seekers = Get-CommandInfo -Name "skill-seekers"
$claude = Get-CommandInfo -Name "claude"
$codex_cmd = Get-CommandInfo -Name "codex.cmd"
$codex = Get-CommandInfo -Name "codex"

$codex_cmd_hint = Join-Path $env:APPDATA "npm\codex.cmd"

$api_keys = [ordered]@{
    anthropic_present = [bool]$env:ANTHROPIC_API_KEY
    anthropic_base_url = $env:ANTHROPIC_BASE_URL
    openai_present = [bool]$env:OPENAI_API_KEY
    google_present = [bool]$env:GOOGLE_API_KEY
    moonshot_present = [bool]$env:MOONSHOT_API_KEY
}

$utf8 = [ordered]@{
    pythonioencoding = $env:PYTHONIOENCODING
    pythonutf8 = $env:PYTHONUTF8
    recommended = ($env:PYTHONIOENCODING -eq "utf-8" -and $env:PYTHONUTF8 -eq "1")
}

$paths = [ordered]@{
    appdata_config = Join-Path $env:APPDATA "skill-seekers\config.json"
    localappdata_progress = Join-Path $env:LOCALAPPDATA "skill-seekers\progress"
    codex_cmd_hint = $codex_cmd_hint
    codex_cmd_hint_exists = (Test-Path -LiteralPath $codex_cmd_hint)
}

$recommendations = [System.Collections.Generic.List[string]]::new()

if (-not $python.available) {
    $recommendations.Add("Install Python and make sure `python` is callable from PowerShell.")
}

if (-not $skill_seekers.available) {
    $recommendations.Add("Install Skill Seekers with `pip install skill-seekers` before running workflows.")
}

if (-not $utf8.recommended) {
    $recommendations.Add("Set `$env:PYTHONIOENCODING = `"utf-8`"` and `$env:PYTHONUTF8 = `"1`"` before diagnostics or local enhancement.")
}

if (-not $claude.available) {
    $recommendations.Add("Claude Code is not on PATH. If you want local Claude enhancement, install it or expose the executable.")
}

if (-not $codex_cmd.available -and $paths.codex_cmd_hint_exists) {
    $recommendations.Add("Codex may exist outside PATH. Prefer the explicit path in `codex_cmd_hint` when building `--agent-cmd`.")
}

if (-not $codex_cmd.available -and -not $paths.codex_cmd_hint_exists) {
    $recommendations.Add("Codex command was not found. If the user requests Codex, verify that `codex.cmd` is installed and callable.")
}

if ($codex_cmd.available) {
    $recommendations.Add("If the user explicitly chooses Codex and the workspace is trusted, prefer `codex.cmd exec --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check ...` for reliable write-back.")
}

if (-not $api_keys.anthropic_present -and -not $api_keys.openai_present -and -not $api_keys.google_present -and -not $api_keys.moonshot_present) {
    $recommendations.Add("No supported API key is present. API enhancement is blocked until a provider key is configured.")
}

$result = [ordered]@{
    timestamp = (Get-Date).ToString("s")
    platform = "windows"
    shell = "powershell"
    python = $python
    skill_seekers = $skill_seekers
    claude = $claude
    codex_cmd = $codex_cmd
    codex = $codex
    api_keys = $api_keys
    utf8 = $utf8
    paths = $paths
    recommendations = $recommendations
}

$result | ConvertTo-Json -Depth 6
