# Urban Researcher CLI (가상 랩 미팅)

AI 기반 도시 연구 자동화 CLI. 먼저 CLI 틀을 안정화(Shell-first)하고, 이후 MCP 도구를 하나씩 증분 통합합니다.

## 요구 사항
- Python 3.10 이상(3.11 권장)
- `pip`

## 빠른 시작
```
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
python -m pip install -r requirements.txt
python cli.py --help
python cli.py --version
```

## 기본 사용 예시
- 설정 저장/조회
```
python cli.py config set --key api-key --value YOUR_KEY
python cli.py config get --key api-key
python cli.py config list
```
- 프로젝트 초기화
```
python cli.py init "urban_regeneration_study"
```
- 프로젝트 상태 확인
```
python cli.py project status --dir urban_regeneration_study
```
- 로깅
```
python cli.py --verbose --help
```

## 설계 메모
- 로깅: `--verbose` 시 DEBUG. 기본은 INFO. 형식: `time | level | logger | message`
- 에러 처리: 사용자 메시지는 `click.ClickException` 기반으로 일관 출력
- 경로/호환성: `pathlib` 사용으로 OS 독립 경로 처리. 기본 테스트 환경은 macOS/Linux이며 Windows는 `python` 명령 사용을 권장
- 구성요소
  - `cli.py`: 엔트리포인트/명령 그룹
  - `urban_cli/config.py`: ConfigManager(ENV 우선, 원자적 쓰기)
  - `urban_cli/project.py`: ProjectManager(표준 디렉터리/메타)
  - `urban_cli/logutil.py`: 로깅 설정
  - `urban_cli/version.py`: 버전 단일 소스

## 다음 단계
- Debate MVP(Phase 4) 설계/구현 후 단일 도구(CodeInterpreter)를 순차 통합
- 세부 단계는 `앞으로의_작업_계획서.md` 참조
