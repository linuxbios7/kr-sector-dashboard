# 한국 업종별 종목 지표

업종별 현재가·시총·PER·Forward P/E·ROE 대시보드 (정적 페이지: `index.html` + `data.js`).

| 파일 | 역할 |
|---|---|
| `sectors.py` | 업종/세부업종/종목코드 정의 (종목 추가·삭제는 여기서) |
| `fetch_data.py` | 키움 OpenAPI(가격) + 네이버(EPS·BPS·ROE·컨센서스) → `data.js` |
| `update.ps1` | 수집 → 변경 시 커밋·푸시 (매일 실행) |
| `register_task.ps1` | 평일 16:00 작업 스케줄러 등록 (1회) |
| `.github/workflows/pages.yml` | 푸시되면 GitHub Pages 자동 배포 |

## 1회 설정 (사용자가 직접)

1. **Git 설치**: `winget install Git.Git` 후 새 터미널
2. **키움 kwcli 설치·인증** (`kiwoom` 모듈 필요): `uv tool install kwcli` → `kiwoomcli setup`
   (앱키/시크릿 입력. 이 PC의 IP가 키움에 등록돼 있어야 하므로 GitHub 서버가 아닌 **이 PC에서** 수집함)
   - `python -c "import kiwoom"`이 되도록 kwcli와 같은 환경에서 실행하거나 `uv pip install kwcli`
   - 미설치 시 가격은 네이버로 자동 대체됨
3. **GitHub 로그인·저장소**: `gh auth login` → 
   `git init -b main; git add .; git commit -m init; gh repo create <이름> --public --source . --push`
4. **Pages 켜기**: 저장소 Settings → Pages → Source = GitHub Actions
5. **스케줄 등록**: `powershell -ExecutionPolicy Bypass -File register_task.ps1`

수동 갱신: `powershell -File update.ps1`
