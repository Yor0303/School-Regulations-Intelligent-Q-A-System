$OllamaModelsJunction = $null
$OllamaModelsTarget = $null

$LocalScript = Join-Path $PSScriptRoot "ollama.local.ps1"
if (Test-Path $LocalScript) {
    . $LocalScript
}

$ModelsPath = $env:OLLAMA_MODELS
if ($OllamaModelsJunction) {
    $ModelsPath = $OllamaModelsJunction
}

if ($ModelsPath) {
    $env:OLLAMA_MODELS = $ModelsPath
    Write-Host "OLLAMA_MODELS = $env:OLLAMA_MODELS"
} else {
    Write-Host "Using system OLLAMA_MODELS or Ollama default model directory."
}

Write-Host "Starting ollama serve..."
ollama serve
