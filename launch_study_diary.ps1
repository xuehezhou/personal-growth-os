$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$appUrl = "http://127.0.0.1:8501/"
$healthUrl = "http://127.0.0.1:8501/_stcore/health"
$logDirectory = Join-Path $projectRoot "logs"
$stdoutLog = Join-Path $logDirectory "streamlit-launcher.log"
$stderrLog = Join-Path $logDirectory "streamlit-launcher-error.log"

function Test-StudyDiaryHealth {
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $healthUrl -TimeoutSec 2
        return $response.StatusCode -eq 200
    }
    catch {
        return $false
    }
}

function Show-LauncherError([string]$message) {
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.MessageBox]::Show(
        $message,
        "Study Diary could not start",
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Error
    ) | Out-Null
}

try {
    if (-not (Test-StudyDiaryHealth)) {
        $venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
        if (Test-Path -LiteralPath $venvPython) {
            $python = $venvPython
        }
        else {
            $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
            if (-not $pythonCommand) {
                $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
            }
            if (-not $pythonCommand) {
                throw "Python was not found. Install Python 3.11+ and the packages in requirements.txt."
            }
            $python = $pythonCommand.Source
        }

        New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
        Start-Process `
            -FilePath $python `
            -ArgumentList @(
                "-m", "streamlit", "run", "app.py",
                "--server.address", "127.0.0.1",
                "--server.port", "8501",
                "--server.headless", "true"
            ) `
            -WorkingDirectory $projectRoot `
            -WindowStyle Hidden `
            -RedirectStandardOutput $stdoutLog `
            -RedirectStandardError $stderrLog

        $ready = $false
        for ($attempt = 0; $attempt -lt 40; $attempt++) {
            Start-Sleep -Milliseconds 500
            if (Test-StudyDiaryHealth) {
                $ready = $true
                break
            }
        }

        if (-not $ready) {
            throw "The app did not start within 20 seconds. Check the log: $stderrLog"
        }
    }

    Start-Process $appUrl
}
catch {
    Show-LauncherError $_.Exception.Message
    exit 1
}
