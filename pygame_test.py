import pygame
import random
import math


pygame.init()

WIDTH, HEIGHT = 900, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Optimized Neon Particles")

clock = pygame.time.Clock()
particles = []


overlay = pygame.Surface((WIDTH, HEIGHT))
overlay.set_alpha(40) 
overlay.fill((0, 0, 0))

class Particle:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(2, 7)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = random.randint(30, 60)
        self.max_life = self.life
        self.size = random.randint(3, 6)
        self.color = random.choice([(255, 50, 50), (50, 255, 50), (50, 100, 255), (255, 255, 100)])

    def update(self):
        self.vx *= 0.96 
        self.vy *= 0.96
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.15 
        self.life -= 1

    def draw(self, surf):
        
        ratio = self.life / self.max_life
        current_size = max(1, int(self.size * ratio))
        
        faded_color = [max(0, int(c * ratio)) for c in self.color]
        pygame.draw.circle(surf, faded_color, (int(self.x), int(self.y)), current_size)

running = True
while running:
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    
    screen.blit(overlay, (0, 0))

   
    mouse_pos = pygame.mouse.get_pos()
    if pygame.mouse.get_pressed()[0]:
        
        if len(particles) < 1000:
            for _ in range(5):
                particles.append(Particle(*mouse_pos))

    
    for p in particles[:]: 
        p.update()
        if p.life <= 0:
            particles.remove(p)
        else:
            p.draw(screen)

    
    pygame.display.flip()
    clock.tick(60)

pygame.quit()