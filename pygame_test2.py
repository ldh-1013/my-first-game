import pygame
import random
import math

# 초기화
pygame.init()

WIDTH, HEIGHT = 900, 600
# 입자 효과를 극대화하기 위해 하드웨어 가속 및 이중 버퍼링 사용
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.DOUBLEBUF)
pygame.display.set_caption("Neon Particle Fountain")

clock = pygame.time.Clock()

class Particle:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        
        # 더 역동적인 확산
        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(2, 8)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed

        # 수명과 시작 크기
        self.max_life = random.randint(30, 60)
        self.life = self.max_life
        self.initial_size = random.randint(4, 8)
        self.size = self.initial_size

        # 네온 컬러 테마 (Cyan, Pink, Purple 등)
        colors = [
            (255, 50, 150), # 핑크
            (50, 255, 255), # 시안
            (150, 50, 255), # 퍼플
            (255, 255, 255) # 화이트
        ]
        self.color = list(random.choice(colors))

    def update(self):
        self.x += self.vx
        self.y += self.vy

        # 중력 및 마찰력 적용
        self.vy += 0.15 
        self.vx *= 0.98
        self.vy *= 0.98
        
        self.life -= 1
        
        # 시간에 따라 크기가 서서히 줄어듦
        self.size = max(0, (self.life / self.max_life) * self.initial_size)

    def draw(self, surf):
        # 입자가 작아지면 그리지 않음
        if self.size > 0.5:
            # 부드러운 빛 효과를 위해 원을 그림
            # 실제 게임에서는 여기에 작은 발광 이미지를 넣으면 더 예쁩니다.
            pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), int(self.size))

def main():
    particles = []
    running = True
    
    # 잔상 효과를 위한 전용 레이어
    overlay = pygame.Surface((WIDTH, HEIGHT))
    overlay.set_alpha(60) # 이 수치가 낮을수록 잔상이 길게 남습니다.
    overlay.fill((10, 10, 20))

    while running:
        # 1. 배경 그리기 (잔상 효과)
        screen.blit(overlay, (0, 0))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # 2. 마우스 입력 및 입자 생성
        mouse_pos = pygame.mouse.get_pos()
        mouse_buttons = pygame.mouse.get_pressed()

        if mouse_buttons[0]: # 왼쪽 클릭 시 폭발하듯 생성
            for _ in range(10):
                particles.append(Particle(*mouse_pos))
        
        # 마우스를 누르지 않아도 조금씩 흘러나오게 하면 더 멋집니다.
        elif random.random() > 0.5:
            particles.append(Particle(*mouse_pos))

        # 3. 입자 업데이트 및 그리기
        # 입자를 뒤에서부터 순회하여 제거 시 인덱스 에러 방지
        for p in particles[:]:
            p.update()
            if p.life <= 0:
                particles.remove(p)
            else:
                p.draw(screen)

        # 4. 화면 업데이트
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()