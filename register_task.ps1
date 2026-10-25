# 1회만 실행: 평일 16:00(장 마감 후)에 update.ps1을 실행하는 작업 스케줄러 등록
$script = Join-Path $PSScriptRoot "update.ps1"
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$script`""
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday, Tuesday, Wednesday, Thursday, Friday -At 4:00PM
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun
Register-ScheduledTask -TaskName "KR-Sector-Dashboard-Update" -Action $action -Trigger $trigger -Settings $settings -Force
