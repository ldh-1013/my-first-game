import pygame
import random


pygame.init()


WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Smooth Movement & Collision")
clock = pygame.time.Clock()
font = pygame.font.SysFont("malgungothic", 24) 


GREEN = (34, 139, 34)
WHITE = (255, 255, 255)


radius = 20
x, y = WIDTH // 2, HEIGHT // 2
vel_x, vel_y = 0, 0
accel = 0.8  
friction = 0.92  
bounce = 0.7  


particles = []

class Particle:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = random.uniform(-5, 5)
        self.vy = random.uniform(-5, 5)
        self.lifetime = 255

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.lifetime -= 10 

    def draw(self, surface):
        if self.lifetime > 0:
            pygame.draw.circle(surface, (255, 255, 255), (int(self.x), int(self.y)), 3)

running = True
while running:
    screen.fill(GREEN)
    
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    
    keys = pygame.key.get_pressed()
    if keys[pygame.K_a]: vel_x -= accel
    if keys[pygame.K_d]: vel_x += accel
    if keys[pygame.K_w]: vel_y -= accel
    if keys[pygame.K_s]: vel_y += accel

   
    vel_x *= friction
    vel_y *= friction
    x += vel_x
    y += vel_y

    
    collided = False
   
    if x - radius < 0:
        x = radius
        vel_x *= -bounce
        collided = "left"
    elif x + radius > WIDTH:
        x = WIDTH - radius
        vel_x *= -bounce
        collided = "right"

    
    if y - radius < 0:
        y = radius
        vel_y *= -bounce
        collided = "top"
    elif y + radius > HEIGHT:
        y = HEIGHT - radius
        vel_y *= -bounce
        collided = "bottom"

    
    if collided:
        px, py = x, y
        if collided == "left": px = 0
        elif collided == "right": px = WIDTH
        elif collided == "top": py = 0
        elif collided == "bottom": py = HEIGHT
        
        for _ in range(10):
            particles.append(Particle(px, py))

   
    for p in particles[:]:
        p.update()
        p.draw(screen)
        if p.lifetime <= 0:
            particles.remove(p)

    
    pygame.draw.circle(screen, WHITE, (int(x), int(y)), radius)

    
    fps_text = font.render(f"현재 프레임: {int(clock.get_fps())}", True, WHITE)
    screen.blit(fps_text, (10, 10))

    pygame.display.flip()
    clock.tick(60) 

pygame.quit()