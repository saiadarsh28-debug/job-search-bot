$ErrorActionPreference = "Stop"

# ---------------------------------------------------------
# PATH SETUP
# ---------------------------------------------------------

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Set-Location $ProjectRoot

# ---------------------------------------------------------
# LOGGING
# ---------------------------------------------------------

$LogsDir = Join-Path $ProjectRoot "logs"

if (!(Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir | Out-Null
}

$RunnerLog = Join-Path $LogsDir "scheduler.log"

function Write-RunnerLog($Message) {

    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

    $Line = "[$Timestamp] $Message"

    Write-Host $Line

    Add-Content -Path $RunnerLog -Value $Line
}

# ---------------------------------------------------------
# START
# ---------------------------------------------------------

Write-RunnerLog "=================================================="
Write-RunnerLog "SCHEDULER RUN STARTED"

# ---------------------------------------------------------
# PYTHON CHECK
# ---------------------------------------------------------

try {

    $PythonVersion = python --version

    Write-RunnerLog "Python detected: $PythonVersion"

}
catch {

    Write-RunnerLog "Python not found"

    exit 1
}

# ---------------------------------------------------------
# MAIN EXECUTION
# ---------------------------------------------------------

try {

    Write-RunnerLog "Launching job bot"

    python main.py

    if ($LASTEXITCODE -ne 0) {

        Write-RunnerLog "main.py exited with code $LASTEXITCODE"

        exit $LASTEXITCODE
    }

    Write-RunnerLog "Job bot completed successfully"
}
catch {

    Write-RunnerLog "RUN FAILED: $_"

    exit 1
}

# ---------------------------------------------------------
# COMPLETE
# ---------------------------------------------------------

Write-RunnerLog "SCHEDULER RUN FINISHED"
Write-RunnerLog "=================================================="