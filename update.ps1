[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

# Publish a new immutable language-pack release from the assets in Lexicons/.
Set-Location -LiteralPath $PSScriptRoot

$branch = (& git branch --show-current).Trim()
if ($LASTEXITCODE -ne 0) {
    throw 'Could not determine the current Git branch.'
}

if ($branch -ne 'main') {
    throw 'Switch to main before publishing language packs.'
}

& git add -A
if ($LASTEXITCODE -ne 0) {
    throw 'Failed to stage changes.'
}

& git diff --cached --quiet
if ($LASTEXITCODE -eq 1) {
    & git commit -m 'Update language packs'
    if ($LASTEXITCODE -ne 0) {
        throw 'Failed to commit staged changes.'
    }
} elseif ($LASTEXITCODE -ne 0) {
    throw 'Failed to inspect staged changes.'
}

& git push origin "HEAD:refs/heads/$branch"
if ($LASTEXITCODE -ne 0) {
    throw 'Failed to push the branch.'
}

Write-Host "Pushed $branch. Relevant changes on main publish through GitHub Actions; check the workflow for completion."
