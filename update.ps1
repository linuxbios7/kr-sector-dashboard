# 수동 업데이트: 데이터 수집(키움+네이버) -> data.js 변경 시 커밋·푸시 -> GitHub Pages 자동 배포
#   .\update.ps1            수집 + 커밋 + 푸시(배포)
#   .\update.ps1 -NoPush    수집만 (로컬 확인용, 커밋·푸시 안 함)
# (자동 실행은 register_task.ps1로 작업 스케줄러에 등록)
param([switch]$NoPush)
$ErrorActionPreference = "Stop"
# 스케줄러 환경에서도 git/uv/gh를 찾도록 PATH 갱신
$env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
Set-Location $PSScriptRoot
$log = Join-Path $PSScriptRoot "update.log"
Start-Transcript -Path $log -Append | Out-Null
try {
    # kwcli(uv tool)의 파이썬을 써야 `kiwoom` 모듈을 import 할 수 있다
    $py = Join-Path (uv tool dir) "kwcli\Scripts\python.exe"
    if (-not (Test-Path $py)) { $py = "python" }
    & $py fetch_data.py
    if ($LASTEXITCODE -ne 0) { throw "fetch_data.py 실패 (exit $LASTEXITCODE) - 푸시하지 않음" }
    if ($NoPush) { Write-Host "data.js 갱신 완료 (-NoPush: 커밋·푸시 생략)"; return }
    git add data.js
    git diff --cached --quiet
    if ($LASTEXITCODE -ne 0) {
        git commit -m ("data: " + (Get-Date -Format "yyyy-MM-dd HH:mm"))
        git push
    } else {
        Write-Host "변경 없음"
    }
} finally {
    Stop-Transcript | Out-Null
}
