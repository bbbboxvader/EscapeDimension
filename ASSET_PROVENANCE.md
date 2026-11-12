# 이미지와 소리 출처

`assets/sprites.png`는 사용자와 정한 메모지형 게임 콘셉트를 참고해 OpenAI 내장 `image_gen` 도구로 제작했습니다. 실제 알파 투명 배경을 사용하는 3열×2행 시트입니다. 배경·방 테두리·조준선·탄환·UI는 pico2d의 2D 그리기와 텍스트로 표시합니다.

사용 프롬프트:

> Create a GAME SPRITE ATLAS based on the detailed painted cyan hero, coral enemy and yellow crate in the reference. Actual transparent background, no paper, no shadows, no frame, NO text. EXACT uniform grid THREE COLUMNS by TWO ROWS, each equal rectangular cell. Landscape 3:2 image. Each object fully contained and centered in its cell with generous 15% transparent padding, no objects touching cell boundaries. TOP ROW left: full-body cyan-trim dark jacket dark-haired young male player standing holding pistol aimed RIGHT, front/side view. TOP ROW middle: SAME player in a slightly bent-knee ready pose aimed RIGHT (alternate animation). TOP ROW right: full-body charcoal armored enemy with CORAL-red trim and helmet holding pistol aimed LEFT. BOTTOM ROW left: full-body charcoal armored rushing enemy with dark red trim, no gun, leaning forward aimed LEFT. BOTTOM ROW middle: one yellow wooden crate, clean front face with small side/top shading, square, matching reference. BOTTOM ROW right: small neutral-gray ammo supply box with cyan cartridge pictogram but NO letters or numbers. Same polished crisp painterly 2D sprite style, cyan and coral colors, moderately stylized proportions, thick enough silhouettes to read when drawn at 50px height. Very important this is a SPRITE SHEET with actual alpha transparency and NO background at all. All six cells exactly aligned to 3 columns and 2 rows. No weapons or props outside their cell.

`assets/*.wav` 11종은 사인파·잡음과 감쇠를 조합해 직접 합성한 효과음입니다. 외부 음원이나 음악을 사용하지 않습니다. 글꼴은 실행 중 Windows의 맑은 고딕을 읽으며 별도 Windows 글꼴 파일을 배포하지 않습니다.
