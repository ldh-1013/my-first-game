import pygame
import math

pygame.init()
screen_width, screen_height = 800, 600
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("Circle Collision Detection")

WHITE = (255, 255, 255)
GRAY = (128, 128, 128)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)

clock = pygame.time.Clock()

player_rect = pygame.Rect(100, 100, 50, 50)
player_radius = 25
player_speed = 5

static_rect = pygame.Rect(350, 250, 100, 100)
static_radius = 50

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT]: player_rect.x -= player_speed
    if keys[pygame.K_RIGHT]: player_rect.x += player_speed
    if keys[pygame.K_UP]: player_rect.y -= player_speed
    if keys[pygame.K_DOWN]: player_rect.y += player_speed

    player_rect.clamp_ip(screen.get_rect())

    dist = math.hypot(player_rect.centerx - static_rect.centerx, player_rect.centery - static_rect.centery)
    
    if dist <= (player_radius + static_radius):
        bg_color = YELLOW
    else:
        bg_color = WHITE

    screen.fill(bg_color)

    pygame.draw.rect(screen, GRAY, static_rect)
    pygame.draw.rect(screen, GRAY, player_rect)
    pygame.draw.rect(screen, RED, static_rect, 2)
    pygame.draw.rect(screen, RED, player_rect, 2)
    
    pygame.draw.circle(screen, BLUE, static_rect.center, static_radius, 2)
    pygame.draw.circle(screen, BLUE, player_rect.center, player_radius, 2)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()