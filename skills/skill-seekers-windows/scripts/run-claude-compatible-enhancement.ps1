[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$SkillDir,

    [switch]$PatchOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$MAX_PROMPT_CHARS = 24000
$MAX_REFERENCE_CHARS = 18000

$resolved_skill_dir = (Resolve-Path -LiteralPath $SkillDir -ErrorAction Stop).Path
$skill_md_path = Join-Path $resolved_skill_dir "SKILL.md"
$references_dir = Join-Path $resolved_skill_dir "references"

if (-not (Test-Path -LiteralPath $skill_md_path)) {
    throw "SKILL.md not found: $skill_md_path"
}

$claude_command = Get-Command -Name "claude" -ErrorAction SilentlyContinue
if (-not $claude_command) {
    throw "Claude command was not found on PATH."
}

$mode_name = if ($PatchOnly) { "PATCH_ONLY" } else { "FULL_ENHANCEMENT" }
$mode_instruction = if ($PatchOnly) {
    @(
        "Patch the existing SKILL.md only.",
        "Preserve correct high-value content that is already present.",
        "Do not rewrite from scratch unless the current structure blocks the required fixes."
    ) -join " "
}
else {
    @(
        "Enhance SKILL.md in one pass.",
        "Treat this single run as both the main enhancement and the default Windows quality patch.",
        "Rewrite aggressively if needed, but keep the result concise and high-signal."
    ) -join " "
}

$skill_md_content = Get-Content -LiteralPath $skill_md_path -Raw -Encoding UTF8
$reference_sections = @()
$remaining_reference_chars = $MAX_REFERENCE_CHARS

if (Test-Path -LiteralPath $references_dir) {
    $reference_files = Get-ChildItem -LiteralPath $references_dir -File -Filter "*.md" | Sort-Object Name
    foreach ($reference_file in $reference_files) {
        if ($remaining_reference_chars -le 0) {
            break
        }

        $reference_content = Get-Content -LiteralPath $reference_file.FullName -Raw -Encoding UTF8
        $slice_length = [Math]::Min($reference_content.Length, $remaining_reference_chars)
        $reference_excerpt = $reference_content.Substring(0, $slice_length)
        $remaining_reference_chars -= $slice_length

        if ($slice_length -lt $reference_content.Length) {
            $reference_excerpt += "`n[TRUNCATED FOR PROMPT BUDGET]"
        }

        $reference_sections += (
            "REFERENCE FILE: $($reference_file.Name)`n" +
            "-----`n" +
            $reference_excerpt
        )
    }
}

if ($reference_sections.Count -eq 0) {
    $reference_sections = @("REFERENCE FILES: none")
}

$prompt_sections = @(
    "You are enhancing a generated Skill Seekers output directory on Windows.",
    "Working directory: $resolved_skill_dir",
    "Mode: $mode_name",
    $mode_instruction,
    "Modify SKILL.md directly in place.",
    "Do not modify references, assets, or scripts.",
    "Do not ask clarifying questions. If there is ambiguity, choose a reasonable default and continue.",
    "Required quality bar:",
    "- Fix any frontmatter description that is too narrow for the actual chapter, paper, or manual coverage.",
    "- Treat derived indexes as navigation aids, not as independent primary sources.",
    "- Add high-value quick-reference anchors with chapter, page, and keyword cues when the source supports them.",
    "- Clearly mark OCR noise, fake code blocks, and the boundary between paper or textbook content and executable code or vendor API docs.",
    "- Remove boilerplate filler and replace it with concrete, reusable skill guidance.",
    "- Keep the final result focused on SKILL.md quality rather than generic documentation filler.",
    "Current SKILL.md:",
    "-----",
    $skill_md_content,
    "Reference excerpts:",
    "-----",
    ($reference_sections -join "`n`n")
) -join "`n"

if ($prompt_sections.Length -gt $MAX_PROMPT_CHARS) {
    $prompt = $prompt_sections.Substring(0, $MAX_PROMPT_CHARS) + "`n[PROMPT TRUNCATED FOR WINDOWS COMMAND LIMIT]"
}
else {
    $prompt = $prompt_sections
}

$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

$before_item = Get-Item -LiteralPath $skill_md_path
$before_hash = (Get-FileHash -LiteralPath $skill_md_path -Algorithm SHA256).Hash
$output_lines = @()
$exit_code = 0

Push-Location -LiteralPath $resolved_skill_dir
try {
    $output_lines = & $claude_command.Source --dangerously-skip-permissions -p $prompt 2>&1
    $exit_code = $LASTEXITCODE
}
finally {
    Pop-Location
}

if ($exit_code -ne 0) {
    if ($output_lines.Count -gt 0) {
        $output_lines | Write-Output
    }
    throw "Claude exited with code $exit_code."
}

$after_item = Get-Item -LiteralPath $skill_md_path
$after_hash = (Get-FileHash -LiteralPath $skill_md_path -Algorithm SHA256).Hash

if ($before_hash -eq $after_hash) {
    if ($output_lines.Count -gt 0) {
        $output_lines | Write-Output
    }
    throw "Claude finished but SKILL.md was not updated. BEFORE_HASH and AFTER_HASH are identical."
}

if ($output_lines.Count -gt 0) {
    $output_lines | Write-Output
}

Write-Output "__CLAUDE_COMPAT_RESULT__"
Write-Output ("MODE={0}" -f $mode_name)
Write-Output ("SKILL_DIR={0}" -f $resolved_skill_dir)
Write-Output ("BEFORE_LENGTH={0}" -f $before_item.Length)
Write-Output ("AFTER_LENGTH={0}" -f $after_item.Length)
Write-Output ("BEFORE_HASH={0}" -f $before_hash)
Write-Output ("AFTER_HASH={0}" -f $after_hash)
Write-Output ("BEFORE_TIME={0}" -f $before_item.LastWriteTimeUtc.ToString("o"))
Write-Output ("AFTER_TIME={0}" -f $after_item.LastWriteTimeUtc.ToString("o"))
