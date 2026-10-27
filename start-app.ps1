$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$projectPython = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python314\python.exe'
if (-not (Test-Path -LiteralPath $projectPython)) {
    $projectPython = 'python'
}
& $projectPython -m streamlit run (Join-Path $PSScriptRoot 'app.py')
