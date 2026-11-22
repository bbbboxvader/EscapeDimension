# 이미지와 소리 출처

## 2026-11-22: 유탄병과 보스

`assets/special_enemies.png`는 기존 캐릭터 시트를 화풍 참고로 사용하고 OpenAI 내장 `image_gen` 도구로 제작한 실제 RGBA 투명 스프라이트입니다. 유탄병, 중간보스, 최종보스 각각의 8방향을 담은 4열×6행 시트입니다. 방향은 두 행씩 E·NE·N·NW / W·SW·S·SE 순입니다. 최종 프롬프트는 [special_enemies.prompt.txt](assets/special_enemies.prompt.txt)에 보관합니다.

걷기는 위치에 따른 상하 움직임, 사망은 회전·하강으로 표현하며 기존 플레이어의 걷기·장전·사망 시트는 유지합니다. 폭발·파편·공격 예고는 게임 코드의 기본 그리기로 표시합니다. `grenade.wav`, `explosion.wav`는 [tools/generate_combat_sounds.py](tools/generate_combat_sounds.py)의 사인파·잡음 합성으로 제작했습니다.

## 칼 추적 적

`assets/knife_enemy.png`는 기존 `characters_8dir.png`를 화풍과 시점 참고 자료로 사용하여 OpenAI 내장 `image_gen` 도구로 제작했습니다. 주황색 후드·검은 장비·은색 칼을 갖춘 8방향 × 2달리기 프레임의 4열×4행 알파 투명 시트입니다. 전체 프롬프트는 [knife_enemy.prompt.txt](assets/knife_enemy.prompt.txt)에 보관합니다.

상하체 분리는 기존 시트의 허리 위·아래 영역을 pico2d에서 별도로 그리는 방식입니다. 원본 이미지를 덮어쓰지 않고 상체 조준·장전과 하체 걷기를 합성합니다. 칼 적 사망 시에도 같은 칼 에셋을 유지하며 회전·하강 표현으로 쓰러집니다.

상하 조준의 허리 연결 개선에는 새 비트맵 생성 없이 기존 PNG를 사용합니다. SDL의 텍스처 메시에서 허리 정점은 고정하고 팔·어깨 쪽에 연속적인 변형 가중치를 적용합니다. `docs/connected-aim.png`는 수정된 게임 렌더러의 실제 출력이며, `tools/render_aim.py`로 다시 만들 수 있습니다.

## 모션 에셋

`walk_player.png`, `walk_enemy.png`, `reload_player.png`, `death_both.png`는 기존 `characters_8dir.png`를 정체성과 화풍 참고 자료로 사용하여 OpenAI 내장 `image_gen` 도구로 제작했습니다. 실제 알파 투명도를 유지한 4열×4행 시트입니다. 전체 프롬프트는 [motion_prompts.md](assets/motion_prompts.md)에 있습니다.

걷기 시트는 앞의 8칸이 첫 번째 발걸음, 뒤의 8칸이 반대 발걸음입니다. 장전 시트는 앞의 8칸이 탄창을 꺼내는 자세, 뒤의 8칸이 끼우는 자세입니다. 방향 순서는 모두 E, NE, N, NW, W, SW, S, SE입니다. 사망 시트는 행별로 플레이어 오른쪽·왼쪽, 적 오른쪽·왼쪽이며 열별로 피격·무릎 꺾임·주저앉음·완전한 쓰러짐입니다.

## 2026-11-13: 8방향 캐릭터

`assets/characters_8dir.png`는 OpenAI 내장 `image_gen` 도구로 새로 생성한 실제 알파 투명 PNG입니다. 4열×4행이며 플레이어 8방향과 적 8방향을 담았습니다. 각 캐릭터의 순서는 E, NE, N, NW, W, SW, S, SE입니다. 원본을 재색칠하거나 좌우 반전해 방향을 대신하지 않고 방향별 이미지를 사용합니다.

생성에 사용한 전체 프롬프트는 [characters_8dir.prompt.txt](assets/characters_8dir.prompt.txt)에 보관합니다. 맵의 점선·구역·선반·접힌 종이 모서리는 pico2d 기본 그리기로 표시합니다. 상자와 보급품은 기존 `sprites.png`를 사용합니다.

## 초기 프로토타입 에셋

`assets/sprites.png`는 사용자와 정한 메모지형 게임 콘셉트를 참고해 OpenAI 내장 `image_gen` 도구로 제작했습니다. 실제 알파 투명 배경을 사용하는 3열×2행 시트입니다. 배경·방 테두리·조준선·탄환·UI는 pico2d의 2D 그리기와 텍스트로 표시합니다.

사용 프롬프트:

> Create a GAME SPRITE ATLAS based on the detailed painted cyan hero, coral enemy and yellow crate in the reference. Actual transparent background, no paper, no shadows, no frame, NO text. EXACT uniform grid THREE COLUMNS by TWO ROWS, each equal rectangular cell. Landscape 3:2 image. Each object fully contained and centered in its cell with generous 15% transparent padding, no objects touching cell boundaries. TOP ROW left: full-body cyan-trim dark jacket dark-haired young male player standing holding pistol aimed RIGHT, front/side view. TOP ROW middle: SAME player in a slightly bent-knee ready pose aimed RIGHT (alternate animation). TOP ROW right: full-body charcoal armored enemy with CORAL-red trim and helmet holding pistol aimed LEFT. BOTTOM ROW left: full-body charcoal armored rushing enemy with dark red trim, no gun, leaning forward aimed LEFT. BOTTOM ROW middle: one yellow wooden crate, clean front face with small side/top shading, square, matching reference. BOTTOM ROW right: small neutral-gray ammo supply box with cyan cartridge pictogram but NO letters or numbers. Same polished crisp painterly 2D sprite style, cyan and coral colors, moderately stylized proportions, thick enough silhouettes to read when drawn at 50px height. Very important this is a SPRITE SHEET with actual alpha transparency and NO background at all. All six cells exactly aligned to 3 columns and 2 rows. No weapons or props outside their cell.

`assets/*.wav` 11종은 사인파·잡음과 감쇠를 조합해 직접 합성한 효과음입니다. 외부 음원이나 음악을 사용하지 않습니다. 글꼴은 실행 중 Windows의 맑은 고딕을 읽으며 별도 Windows 글꼴 파일을 배포하지 않습니다.
