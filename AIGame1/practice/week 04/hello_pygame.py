import pygame
import math

pygame.init()
screen_width, screen_height = 800, 600
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("Collision Comparison: Circle vs AABB vs OBB")
font = pygame.font.SysFont("arial", 24, bold=True)

WHITE, GRAY, BLACK = (255, 255, 255), (128, 128, 128), (0, 0, 0)
RED, GREEN, BLUE, YELLOW = (255, 0, 0), (0, 255, 0), (0, 100, 255), (255, 255, 0)

fixed_pos = pygame.Vector2(400, 300)
fixed_size = (150, 100)
fixed_radius = int(math.sqrt(fixed_size[0]**2 + fixed_size[1]**2) // 2)
angle = 0

movable_pos = pygame.Vector2(150, 150)
movable_size = (80, 80)
movable_radius = int(math.sqrt(movable_size[0]**2 + movable_size[1]**2) // 2)
movable_speed = 5

def get_obb_vertices(center, size, angle):
    w, h = size[0] / 2, size[1] / 2
    vertices = [pygame.Vector2(-w, -h), pygame.Vector2(w, -h), 
                pygame.Vector2(w, h), pygame.Vector2(-w, h)]
    return [v.rotate(-angle) + center for v in vertices]

def sat_collision(poly1, poly2):
    for poly in [poly1, poly2]:
        for i in range(len(poly)):
            p1, p2 = poly[i], poly[(i + 1) % len(poly)]
            edge = p2 - p1
            if edge.length() == 0: continue
            normal = pygame.Vector2(-edge.y, edge.x).normalize()
            
            def get_projection(p, axis):
                projs = [v.dot(axis) for v in p]
                return min(projs), max(projs)
            
            min1, max1 = get_projection(poly1, normal)
            min2, max2 = get_projection(poly2, normal)
            if max1 < min2 or max2 < min1: return False
    return True

temp_surface = pygame.Surface((screen_width, screen_height))

clock = pygame.time.Clock()
running = True

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False

    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT]:  movable_pos.x -= movable_speed
    if keys[pygame.K_RIGHT]: movable_pos.x += movable_speed
    if keys[pygame.K_UP]:    movable_pos.y -= movable_speed
    if keys[pygame.K_DOWN]:  movable_pos.y += movable_speed
    angle += (5 if keys[pygame.K_z] else 1)

    poly1_obb = get_obb_vertices(fixed_pos, fixed_size, angle)
    poly2_obb = get_obb_vertices(movable_pos, movable_size, 0)
    
    fixed_rect_aabb = pygame.draw.polygon(temp_surface, GRAY, poly1_obb)
    movable_rect_aabb = pygame.draw.polygon(temp_surface, BLUE, poly2_obb)

    dist_sq = (fixed_pos - movable_pos).length_squared()
    hit_circle = dist_sq <= (fixed_radius + movable_radius)**2
    
    hit_aabb = fixed_rect_aabb.colliderect(movable_rect_aabb)
    
    hit_obb = sat_collision(poly1_obb, poly2_obb)
    
    screen.fill(RED if hit_obb else BLACK) 

    
    pygame.draw.circle(screen, BLUE, (int(fixed_pos.x), int(fixed_pos.y)), fixed_radius, 1)
    pygame.draw.circle(screen, BLUE, (int(movable_pos.x), int(movable_pos.y)), movable_radius, 1)

    pygame.draw.rect(screen, RED, fixed_rect_aabb, 1)
    pygame.draw.rect(screen, RED, movable_rect_aabb, 1)
    
    
    pygame.draw.polygon(screen, GRAY, poly1_obb)
    pygame.draw.polygon(screen, BLUE, poly2_obb)
    pygame.draw.polygon(screen, GREEN, poly1_obb, 2)
    pygame.draw.polygon(screen, GREEN, poly2_obb, 2)

    
    status_list = [
        (f"Circle: {'HIT' if hit_circle else 'SAFE'}", BLUE if hit_circle else WHITE),
        (f"AABB: {'HIT' if hit_aabb else 'SAFE'}", RED if hit_aabb else WHITE),
        (f"OBB: {'HIT' if hit_obb else 'SAFE'}", GREEN if hit_obb else WHITE)
    ]
    
    for i, (msg, color) in enumerate(status_list):
        text_surf = font.render(msg, True, color)
        screen.blit(text_surf, (20, 20 + i * 35))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()