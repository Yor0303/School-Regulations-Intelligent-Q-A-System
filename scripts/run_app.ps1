$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Error "Virtual env not found: $VenvPython"
    exit 1
}

Write-Host "Starting Streamlit (Ollama paths: see rapid_rag/config.local.yaml if needed)"
& $VenvPython -m streamlit run app.py
