# 변경 이력

## 2026-11-13

이번 작업은 실제 작업 순서에 따라 다음 단위로 커밋했습니다. 과거 날짜를 붙여 개발 이력을 재현하지 않습니다.

1. `feat: import playable Escape Dimension prototype and design`
   - 이전에 만든 Python·pico2d 게임과 기획서, 에셋, 규칙 테스트 등록.
2. `fix: stabilize room entry and redesign five combat layouts`
   - 로드 시 상자·캐릭터를 지지면에 배치하고 겹침을 검사.
   - 5개 방의 엄폐·선반·적 배치와 3D 우회 동선 재구성.
   - 시작 시 적 생존·재도전·낙하 공격 유지·우회 동선 회귀 검사.
3. `feat: add eight-direction character art and detailed memo-room rendering`
   - 플레이어와 적에 8방향 전용 투명 이미지 적용.
   - 마우스 방향·적 목표 방향에 맞춰 앞뒤와 대각선 프레임 선택.
   - 종이 질감, 접힘, 구역 표식, 선반과 출입구 표시 추가.
4. `build: package refreshed game and document verification`
   - 실행 파일 재빌드 방법, 검사 결과와 화면 예시 정리.

방을 여는 순간 물리 연산을 진행하며 초기 배치의 적이 죽는 문제를 방지했습니다. 게임 도중 플레이어가 만든 낙하·투척 피해는 유지됩니다.
