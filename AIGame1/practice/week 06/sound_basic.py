import pygame

# ── 초기화 ────────────────────────────────────
pygame.init()
pygame.mixer.init()

screen = pygame.display.set_mode((400, 300))
pygame.display.set_caption("Mouse Click Sound")
clock = pygame.time.Clock()

# ── ① 효과음 및 배경음악 로드 ───────────────────
try:
    shoot_sound = pygame.mixer.Sound("./assets/sound/boom.wav")
    pygame.mixer.music.load("./assets/sound/bitbgm.mp3")
except pygame.error as e:
    print(f"파일을 찾을 수 없습니다: {e}")

# ── ② 볼륨 및 배경음악 설정 (2초 페이드인) ──────
shoot_sound.set_volume(0.5)
pygame.mixer.music.set_volume(0.3)
pygame.mixer.music.play(-1, 0.0, 2000)

# ── 메인 루프 ─────────────────────────────────
running = True
while running:
    clock.tick(60)
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
        # ── ③ 마우스 클릭 이벤트 처리 ────────────────
        if event.type == pygame.MOUSEBUTTONDOWN:
            # event.button == 1: 마우스 왼쪽 클릭
            # event.button == 2: 마우스 휠 클릭
            # event.button == 3: 마우스 오른쪽 클릭
            if event.button == 1:
                shoot_sound.stop()  # 기존 소리 정지 (리셋)
                shoot_sound.play()  # 처음부터 재생
        
        # 키보드 ESC 종료는 유지
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False

    screen.fill((30, 30, 40))
    pygame.display.flip()

pygame.quit()