# Escape Dimension 구현 참고 문서

작성일: 2026-11-14

현재 구현을 35개 주제로 정리한 문서입니다. 각 항목은 실제 코드의 동작과 확인 위치를 설명합니다.
기존 15개 개발 커밋을 유지하고 이 문서의 항목을 순서대로 추가했습니다.

## 01. 게임 개요와 기본 실행 진입점

Escape Dimension은 Python과 pico2d로 구현한 방 단위 액션 슈팅 게임이다. 모든 표시는 2D이며, 2D·3D·4D라는 이름은 이동·중력·시간 규칙의 구분이다.

게임의 기본 진입점은 `main.py`다. 프로젝트 폴더에서 `python main.py`로 실행하거나 `실행.bat`를 사용한다. 관련 안내는 [README](../README.md)에 있다.

## 02. 프로젝트 전용 실행 환경

실행 라이브러리는 프로젝트의 `.venv`에 설치한다. `main.py`를 일반 Python으로 실행하면 준비된 프로젝트 Python을 다시 사용하도록 연결되어 있다.

환경 복구는 `python tools/setup_runtime.py`로 진행한다. 다운로드한 wheel이 `.runtime/wheels`에 있으면 오프라인 설치를 우선한다. 필요한 버전은 `requirements.txt`에 명시되어 있다.

## 03. 파일별 책임과 수정 위치

`core.py`는 그래픽에 의존하지 않는 규칙과 상태, `main.py`는 입력·화면·효과음, `visuals.py`는 방향·프레임·상체 변형 계산을 담당한다. `navigation.py`는 적의 우회 경로를 계산한다.

방 배치는 `levels.json`, 이미지는 `assets`, 검사는 `tests`에 있다. 소스 실행에서는 파일 수정 후 다시 실행해 결과를 확인한다.
