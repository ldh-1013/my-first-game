# -*- coding: utf-8 -*-
import os

# 기본 경로
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "Assets")

# 내부 렌더 해상도 (모든 좌표계 기준)
INTERNAL_W = 1280
INTERNAL_H = 720
FPS        = 60

# ── 씬 상수 ──────────────────────────────────────────────
SCENE_TITLE    = "TITLE"
SCENE_SETTINGS = "SETTINGS"
SCENE_GAME     = "GAME"
SCENE_PAUSE    = "PAUSE"
SCENE_EVENT    = "EVENT"
SCENE_GAMEOVER = "GAMEOVER"
SCENE_ENDING_A = "ENDING_A"
SCENE_ENDING_B = "ENDING_B"
SCENE_ENDING_C = "ENDING_C"

# ── 색상 ─────────────────────────────────────────────────
BLACK  = (0,   0,   0)
WHITE  = (255, 255, 255)
GOLD   = (200, 169, 110)
GOLD2  = (232, 200, 122)
RED    = (217,  64,  64)
RED2   = (255, 107, 107)
DIM    = (90,   99, 114)
BRIGHT = (232, 235, 240)
PANEL  = (13,   17,  23)
GHOST_COLOR = (150, 200, 255)

# ── 폰트 경로 ────────────────────────────────────────────
FONT_REGULAR   = os.path.join(ASSETS_DIR, "fonts", "NanumMyeongjoRegular.ttf")
FONT_EXTRABOLD = os.path.join(ASSETS_DIR, "fonts", "NanumMyeongjoExtraBold.ttf")
FONT_CHOSUN    = os.path.join(ASSETS_DIR, "fonts", "ChosunCentennial.ttf")
FONT_BRUSH     = os.path.join(ASSETS_DIR, "fonts", "NanumBrush.ttf")

# ── 플레이어 ─────────────────────────────────────────────
PLAYER_SPRITE_SIZE = (72, 96)   # 화면에 표시되는 스프라이트 크기 (2.25 × 3타일)
PLAYER_SIZE        = (40, 28)   # 충돌박스 (하단 영역만, 스프라이트보다 좁게)
PLAYER_SPEED_WALK = 150        # px/s
PLAYER_SPEED_RUN  = 250        # px/s

# ── 라이터 ───────────────────────────────────────────────
LIGHTER_DRAIN  = 0.08   # %/s (ON 상태)
LIGHTER_R_FULL = 180    # 기름 > 20% 일 때 조명 반경
LIGHTER_R_LOW  = 120    # 기름 10~20%
LIGHTER_R_VERY = 60     # 기름 1~10%
LIGHTER_R_OFF  = 60     # 꺼진 상태 (암흑 속 최소 시야)

# ── 게임 시간 ────────────────────────────────────────────
# 실제 1초 = 게임 내 TIME_SCALE 초
TIME_SCALE     = 10
GAME_START_MIN = 60    # 01:00 AM (자정 기준 분)
GAME_END_MIN   = 300   # 05:00 AM
