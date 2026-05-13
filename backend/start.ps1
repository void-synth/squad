$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Test-TcpPort {
  param([int]$Port)
  try {
    $c = New-Object System.Net.Sockets.TcpClient("localhost", $Port)
    $c.Close() | Out-Null
    return $true
  } catch {
    return $false
  }
}

if (-not (Test-TcpPort -Port 5432)) {
  Write-Host "PostgreSQL does not appear to be listening on localhost:5432" -ForegroundColor Red
  exit 1
}

if (-not (Test-TcpPort -Port 6379)) {
  Write-Host "Redis does not appear to be listening on localhost:6379" -ForegroundColor Red
  exit 1
}

if (Test-Path ".\venv\Scripts\Activate.ps1") {
  . .\venv\Scripts\Activate.ps1
}

if (-not (Test-Path ".\.env")) {
  Copy-Item .\.env.example .\.env
  Write-Host "Created .env from .env.example — fill in SQUAD_* keys before demo." -ForegroundColor Yellow
}

Write-Host "Titan backend is running at http://localhost:8000" -ForegroundColor Green
python -m uvicorn main:app --reload --port 8000
