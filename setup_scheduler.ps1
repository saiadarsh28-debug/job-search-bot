$ErrorActionPreference = "Stop"

$taskName = "Job Search Bot - Every 12 Hours"
$projectDir = "C:\job-search-bot"
$runner = Join-Path $projectDir "run_job_bot.ps1"

if (!(Test-Path $runner)) {
    throw "Missing runner script: $runner"
}

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$runner`"" `
    -WorkingDirectory $projectDir

$trigger1 = New-ScheduledTaskTrigger -Daily -At 8:00AM
$trigger2 = New-ScheduledTaskTrigger -Daily -At 8:00PM

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger @($trigger1, $trigger2) `
    -Settings $settings `
    -Description "Runs C:\job-search-bot every 12 hours and emails matching job alerts." `
    -Force

Write-Host "Scheduled task created: $taskName"
Write-Host "It will run daily at 8:00 AM and 8:00 PM local time."
