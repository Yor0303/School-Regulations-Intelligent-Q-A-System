# Restart Ollama serve (optional local overrides in scripts/ollama.local.ps1)
param(
    [string]$ModelsPath = ""
)

$OllamaModelsJunction = $null
$OllamaModelsTarget = $null

$LocalScript = Join-Path $PSScriptRoot "ollama.local.ps1"
if (Test-Path $LocalScript) {
    . $LocalScript
}

if (-not $ModelsPath -and $OllamaModelsJunction) {
    $ModelsPath = $OllamaModelsJunction
}

Write-Host "=== Restart Ollama ==="

if ($OllamaModelsTarget -and $OllamaModelsJunction) {
    Write-Host "Junction: $OllamaModelsJunction -> $OllamaModelsTarget"
    if (-not (Test-Path $OllamaModelsTarget)) {
        Write-Error "Models target not found: $OllamaModelsTarget (edit scripts/ollama.local.ps1)"
        exit 1
    }
    if (-not (Test-Path $OllamaModelsJunction)) {
        cmd /c "mklink /J `"$OllamaModelsJunction`" `"$OllamaModelsTarget`""
    }
    $userOllama = Join-Path $env:USERPROFILE ".ollama"
    $userModels = Join-Path $userOllama "models"
    if (-not (Test-Path $userModels)) {
        New-Item -ItemType Directory -Path $userOllama -Force | Out-Null
        cmd /c "mklink /J `"$userModels`" `"$OllamaModelsJunction`""
    }
    $ModelsPath = $OllamaModelsJunction
}

if ($ModelsPath) {
    Write-Host "OLLAMA_MODELS = $ModelsPath"
    [Environment]::SetEnvironmentVariable("OLLAMA_MODELS", $ModelsPath, "User")
    $env:OLLAMA_MODELS = $ModelsPath
} else {
    Write-Host "No local models path; using system OLLAMA_MODELS or Ollama default."
}

Write-Host "Stopping Ollama tray + server..."
Get-Process -Name "ollama", "ollama app" -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 3

$ollamaExe = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"
if (-not (Test-Path $ollamaExe)) {
    Write-Error "ollama.exe not found: $ollamaExe"
    exit 1
}

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $ollamaExe
$psi.Arguments = "serve"
$psi.UseShellExecute = $false
$psi.CreateNoWindow = $true
foreach ($scope in @("Machine", "User", "Process")) {
    foreach ($key in [Environment]::GetEnvironmentVariables($scope).Keys) {
        $psi.EnvironmentVariables[$key] = [Environment]::GetEnvironmentVariable($key, $scope)
    }
}
if ($ModelsPath) {
    $psi.EnvironmentVariables["OLLAMA_MODELS"] = $ModelsPath
}
[System.Diagnostics.Process]::Start($psi) | Out-Null
Start-Sleep -Seconds 6

Write-Host ""
Write-Host "--- ollama list ---"
if ($ModelsPath) { $env:OLLAMA_MODELS = $ModelsPath }
ollama list

Write-Host ""
Write-Host "If qwen2.5:7b appears above, refresh Streamlit."
Write-Host "Optional: copy ollama.local.ps1.example when you need custom model paths."
