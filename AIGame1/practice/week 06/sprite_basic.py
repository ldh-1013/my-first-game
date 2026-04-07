import pygame

pygame.init()
screen = pygame.display.set_mode((400, 300))
pygame.display.set_caption("Looping Sprite")
clock = pygame.time.Clock()

# 이미지 설정
img_raw = pygame.image.load("./assets/image/Snake.png").convert_alpha()
img_raw = pygame.transform.scale(img_raw, (96, 96))
img = pygame.transform.rotate(img_raw, 40)

# 초기 위치
rect = img.get_rect()
rect.topleft = (0, 0)

speed_x, speed_y = 2, 2 # 속도를 조금 높였습니다

running = True
while running:
    clock.tick(60)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # 1. 위치 업데이트
    rect.x += speed_x
    rect.y += speed_y

    # 2. 경계 체크 및 순간이동
    if rect.left > 400 or rect.top > 300:
        rect.right = 0
        rect.bottom = 0

    # 3. 그리기
    screen.fill((30, 30, 40))
    screen.blit(img, rect)
    pygame.display.flip()

pygame.quit()