import base64, io
import pygame

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  스프라이트 시트 Base64 데이터
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SHEET_B64 = "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"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  설정
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SCREEN_W, SCREEN_H = 480, 320
FRAME_W, FRAME_H   = 16, 16
COLS               = 4
FRAME_DELAY        = 150   # ms
DISPLAY_SCALE      = 4     # 화면 확대 배율

pygame.init()
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("Sprite Animation Demo")
clock = pygame.time.Clock()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  시트 로드 → 프레임 리스트
#  인덱스 0 ~ 15 (총 16개)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
sheet_bytes = base64.b64decode(SHEET_B64)
player_sheet = pygame.image.load(io.BytesIO(sheet_bytes)).convert_alpha()

player_frames = []
for i in range(16):
    row, col = divmod(i, COLS)
    rect = pygame.Rect(col * FRAME_W, row * FRAME_H, FRAME_W, FRAME_H)
    player_frames.append(player_sheet.subsurface(rect))

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  walk_frames: 선택한 프레임 순서
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
walk_frames = [player_frames[i] for i in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]]

frame_index = 0
frame_timer = 0
x = SCREEN_W // 2 - (FRAME_W * DISPLAY_SCALE) // 2
y = SCREEN_H // 2 - (FRAME_H * DISPLAY_SCALE) // 2

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  게임 루프
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
running = True
while running:
    dt = clock.tick(60)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            running = False

    frame_timer += dt
    if frame_timer >= FRAME_DELAY:
        frame_index = (frame_index + 1) % len(walk_frames)
        frame_timer = 0

    screen.fill((30, 30, 40))
    frame_img = pygame.transform.scale(
        walk_frames[frame_index],
        (FRAME_W * DISPLAY_SCALE, FRAME_H * DISPLAY_SCALE)
    )
    screen.blit(frame_img, (x, y))
    pygame.display.flip()

pygame.quit()
