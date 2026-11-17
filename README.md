# Escape Dimension

메모지 같은 공간에서 이동·중력·시간 규칙을 바꾸며 적을 섬멸하는 2D 액션 슈팅 게임

게임공학과 박태욱 · 2D 게임프로그래밍 프로젝트

![실제 게임 화면](docs/knife-room.png)

## 게임 개요

- 개발: Python, pico2d / Windows / 1280 × 800 창 모드
- 목표: 한 건물의 방 5개를 오가며 모든 적을 섬멸
- 2D: 좌우 이동, 낮은 점프, 중력과 상자 낙하 공격
- 3D: 같은 화면을 바닥으로 해석하는 8방향 이동
- 4D: 멈추면 세계 정지, 최근 4초의 과거 위치를 선택해 이동

모든 화면과 충돌 처리는 2D로 구현합니다. 3D·4D는 이동·중력·시간 규칙을 구분하는 게임 모드입니다.
탄창은 6발, 예비탄은 36발로 시작하며 보유량은 합계 최대 42발입니다.
4D는 최대 10초이고 종료하면 한 살을 먹습니다. 20세에 시작하며 40세 이상이면 처음부터 다시 시작합니다.

## 조작

| 입력 | 기능 |
|---|---|
| A / D, Space | 2D 좌우 이동, 점프 |
| W / A / S / D | 3D·4D 이동, 동시 입력으로 대각선 이동 |
| 마우스, 왼쪽 버튼 | 조준, 발사 |
| R | 장전, 이동 중에도 가능 |
| 2 / 3 / 4 | 차원 모드 전환 |
| E / Q | 가까운 상자 집기, 조준 방향으로 투척 |
| 휠 또는 좌우 방향키, Enter | 4D의 과거 위치 선택, 시간 이동 |
| Enter | 시작, 방 진행, 재도전 |
| F1 / Esc / M | 도움말, 일시정지, 효과음 켜기·끄기 |

2D에서는 하체가 좌우를 향하고 상체와 팔이 상하 조준을 따라 움직입니다.
3D·4D에서는 8방향을 바라봅니다. 빠른 칼 적과 추적 적은 벽·상자의 모서리를 우회합니다.

## 실행 방법

Python 3.10 이상과 Windows 환경을 사용합니다. 이 PC에서는 Python 3.14.3으로 확인했습니다.

`실행.bat`을 더블 클릭하면 `.venv`를 준비하고 `main.py`를 실행합니다.
명령으로 실행하려면 다음을 사용합니다.

```powershell
python tools/setup_runtime.py
.venv\Scripts\python.exe main.py
```

이미 환경을 설치했다면 `python main.py`로 실행할 수 있습니다.
필요한 패키지 버전은 [requirements.txt](requirements.txt)에 고정했습니다.

## 소스 구조

| 경로 | 내용 |
|---|---|
| [main.py](main.py) | 진입점, pico2d 렌더링, 입력, UI, 효과음 |
| [core.py](core.py) | 이동, 전투, 중력, 시간, 노화, 방 진행 |
| [navigation.py](navigation.py) | 벽·상자 모서리를 이용하는 우회 경로 |
| [visuals.py](visuals.py) | 방향과 모션 프레임, 상체 조준 변형 |
| [levels.json](levels.json) | 방·적·상자·장애물 배치 |
| [assets/](assets/) | 캐릭터·상자 이미지와 효과음 |
| [tests/](tests/) | 게임 규칙 검사 |
| [tools/](tools/) | 환경 설치, 빌드, 렌더링과 검사 도구 |
| [docs/](docs/) | 게임 화면과 구현 기록 |
| [GAME_DESIGN.md](GAME_DESIGN.md) | 게임 규칙과 설계 |

## 개발 검사

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests
.venv\Scripts\python.exe tools/verify_game.py
```

게임 규칙과 실제 SDL 입력·렌더링을 검사합니다. 검사 기록은 [verification/](verification/)에 보관합니다.

## 게임 파일과 커밋 기록

[Escape Dimension.zip](Escape%20Dimension.zip)은 게임 개발 파일만 묶은 다운로드입니다.
소스·에셋·맵·개발 문서·테스트·설치 wheel과 개발 커밋 50개를 복원할 수 있는 Git bundle을 담았습니다.
GitHub 커밋 기록에도 기존 개발 커밋 50개를 보존했습니다.
압축 안의 README에 백업 복원 방법을 적었습니다.

## 리소스 출처

| 리소스 | 출처 |
|---|---|
| 캐릭터, 모션, 칼 적, 상자와 보급품 이미지 | OpenAI image_gen으로 제작 |
| 메모지 공간, 조준선, 탄환과 UI | pico2d·SDL의 2D 그리기로 구현 |
| 효과음 11종 | 사인파·잡음과 감쇠를 조합해 직접 합성 |
| 한글 글꼴 | 실행 PC의 Windows 맑은 고딕 사용, 글꼴 파일 미포함 |

자세한 제작 기록은 [ASSET_PROVENANCE.md](ASSET_PROVENANCE.md), 사용한 패키지의 라이선스는 [THIRD_PARTY/](THIRD_PARTY/)에 있습니다.
