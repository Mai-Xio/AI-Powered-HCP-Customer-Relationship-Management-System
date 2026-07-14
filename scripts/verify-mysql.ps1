param(
  [string]$DatabaseUrl = "mysql+pymysql://aivoa_user:aivoa_password@localhost:3306/aivoa_crm",
  [int]$ApiPort = 8010,
  [switch]$SkipCompose
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$backendRoot = Join-Path $repoRoot "backend"
$python = Join-Path $repoRoot ".venv-aivoa\Scripts\python.exe"

function Invoke-Docker {
  param(
    [string[]]$DockerArgs,
    [int]$TimeoutSeconds = 30
  )

  $stdout = New-TemporaryFile
  $stderr = New-TemporaryFile
  try {
    $process = Start-Process -FilePath "docker" `
      -ArgumentList $DockerArgs `
      -RedirectStandardOutput $stdout `
      -RedirectStandardError $stderr `
      -WindowStyle Hidden `
      -PassThru

    $finished = Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction SilentlyContinue
    if (!$finished -and !$process.HasExited) {
      Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
      throw "Docker command timed out: docker $($DockerArgs -join ' ')"
    }

    $output = Get-Content $stdout -Raw
    $errorOutput = Get-Content $stderr -Raw
    if ($process.ExitCode -ne 0) {
      throw "Docker command failed: docker $($DockerArgs -join ' ')`n$output$errorOutput"
    }
    return $output
  } finally {
    Remove-Item $stdout, $stderr -Force -ErrorAction SilentlyContinue
  }
}

if (!(Test-Path $python)) {
  throw "Python venv not found at $python. Create it with: python -m venv .venv-aivoa"
}

Push-Location $repoRoot
try {
  if (!$SkipCompose) {
    Invoke-Docker -DockerArgs @("info", "--format", "{{.ServerVersion}}") -TimeoutSeconds 20 | Out-Null
    Invoke-Docker -DockerArgs @("compose", "-f", "docker-compose.mysql.yml", "up", "-d") -TimeoutSeconds 120 | Out-Null

    $deadline = (Get-Date).AddSeconds(120)
    do {
      try {
        $containerReady = (Invoke-Docker -DockerArgs @("inspect", "-f", "{{.State.Health.Status}}", "aivoa-mysql") -TimeoutSeconds 10).Trim()
      } catch {
        $containerReady = "unknown"
      }
      if ($containerReady -eq "healthy") { break }
      Start-Sleep -Seconds 5
    } while ((Get-Date) -lt $deadline)

    if ($containerReady -ne "healthy") {
      throw "MySQL container did not become healthy. Current status: $containerReady"
    }
  } else {
    $portOpen = Test-NetConnection -ComputerName "127.0.0.1" -Port 3306 -InformationLevel Quiet
    if (!$portOpen) {
      throw "SkipCompose was set, but no MySQL server is listening on 127.0.0.1:3306."
    }
  }

  $env:DATABASE_URL = $DatabaseUrl
  $env:AIVOA_USE_LIVE_LLM = "false"
  $api = Start-Process -FilePath $python `
    -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$ApiPort") `
    -WorkingDirectory $backendRoot `
    -WindowStyle Hidden `
    -PassThru

  try {
    $healthUrl = "http://127.0.0.1:$ApiPort/health"
    $deadline = (Get-Date).AddSeconds(45)
    do {
      try {
        $health = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 3
        if ($health.status -eq "ok") { break }
      } catch {
        Start-Sleep -Seconds 2
      }
    } while ((Get-Date) -lt $deadline)

    if (!$health -or $health.status -ne "ok") {
      throw "Backend did not become healthy on port $ApiPort."
    }

    $draft = @{
      hcp_name = "Dr. MySQL Smoke"
      interaction_type = "Meeting"
      interaction_date = "10/07/2026"
      interaction_time = "10:30 AM"
      interaction_timezone = "Asia/Kolkata"
      original_timezone = "Asia/Kolkata"
      date_format = "DD/MM/YYYY"
      time_format = "12h"
      time_format_preference = "12h"
      topics_discussed = "MySQL persistence smoke test"
      sentiment = "Neutral"
      materials_shared = @("brochure")
      products_discussed = @("AIVOA")
      attendees = @()
      samples_distributed = @()
      outcomes = ""
      follow_up_actions = ""
      suggested_follow_ups = @()
      hcp_questions = ""
      objections = ""
      commitments = ""
      next_steps = ""
      follow_up_date = ""
      interaction_summary = "MySQL persistence smoke test."
      completion_status = "Validated"
      confidence_score = 0
      compliance_flags = @()
      ai_confidence = ""
    }

    $saved = Invoke-RestMethod `
      -Method Post `
      -Uri "http://127.0.0.1:$ApiPort/api/interactions" `
      -ContentType "application/json" `
      -Body ($draft | ConvertTo-Json -Depth 20) `
      -TimeoutSec 10

    if (!$saved.id) {
      throw "Save response did not include an interaction id."
    }

    [pscustomobject]@{
      mysql = if ($SkipCompose) { "local-listening" } else { "compose-healthy" }
      backend = "ok"
      saved_interaction_id = $saved.id
      database_url = "mysql+pymysql://aivoa_user:<redacted>@localhost:3306/aivoa_crm"
    } | ConvertTo-Json
  } finally {
    if ($api -and !$api.HasExited) {
      Stop-Process -Id $api.Id -Force
    }
  }
} finally {
  Pop-Location
}
