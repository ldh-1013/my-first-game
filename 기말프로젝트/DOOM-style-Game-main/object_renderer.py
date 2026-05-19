import pygame
import random
import math

# =====================
# 게임 설정
# =====================
SCREEN_WIDTH  = 800
SCREEN_HEIGHT = 600
TILE_SIZE     = 10
COLS = SCREEN_WIDTH  // TILE_SIZE
ROWS = SCREEN_HEIGHT // TILE_SIZE

FILL_PROB   = 0.45   # 초기 벽 비율
ITERATIONS  = 5      # 시뮬레이션 반복 횟수
BIRTH_LIMIT = 4      # 이웃 벽 >= 이 수면 벽으로 탄생
DEATH_LIMIT = 3      # 이웃 벽 <= 이 수면 벽이면 바닥으로 소멸

NUM_ENEMIES = 8      # 생성할 적의 수

# 색상 정의
COLOR_WALL  = (60,  50,  80)
COLOR_FLOOR = (180, 160, 130)
COLOR_BG    = (20,  20,  30)
COLOR_TEXT  = (255, 255, 255)
COLOR_START = (50, 150, 255) # 시작점 (파란색)
COLOR_EXIT  = (50, 255, 50)  # 탈출구 (초록색)
COLOR_ENEMY = (255, 50, 50)  # 적 (빨간색)

# 3D 렌더링 색상
COLOR_CEILING = (40, 40, 50)
COLOR_GROUND  = (80, 70, 60)

# =====================
# 적(Enemy) 클래스
# =====================
class Enemy:
    def __init__(self, x, y):
        self.x = x + 0.5
        self.y = y + 0.5
        self.alive = True
        self.health = 100

# =====================
# 셀룰러 오토마타 맵 생성 함수
# =====================
def init_map(seed=None):
    if seed is not None:
        random.seed(seed)
    return [[1 if random.random() < FILL_PROB else 0
             for _ in range(COLS)] for _ in range(ROWS)]

def count_neighbors(tilemap, cx, cy):
    count = 0
    for dy in range(-1, 2):
        for dx in range(-1, 2):
            if dx == 0 and dy == 0:
                continue
            nx, ny = cx + dx, cy + dy
            if nx < 0 or nx >= COLS or ny < 0 or ny >= ROWS:
                count += 1
            elif tilemap[ny][nx] == 1:
                count += 1
    return count

def step(tilemap):
    new_map = [[0] * COLS for _ in range(ROWS)]
    for y in range(ROWS):
        for x in range(COLS):
            n = count_neighbors(tilemap, x, y)
            if tilemap[y][x] == 1:
                new_map[y][x] = 1 if n >= DEATH_LIMIT else 0
            else:
                new_map[y][x] = 1 if n > BIRTH_LIMIT else 0
    return new_map

def generate(seed=None):
    tilemap = init_map(seed)
    for _ in range(ITERATIONS):
        tilemap = step(tilemap)
    for y in range(ROWS):
        tilemap[y][0] = 1
        tilemap[y][COLS-1] = 1
    for x in range(COLS):
        tilemap[0][x] = 1
        tilemap[ROWS-1][x] = 1
    return tilemap

def find_positions(tilemap):
    empty_spaces = [(x, y) for y in range(ROWS) for x in range(COLS) if tilemap[y][x] == 0]
    if not empty_spaces:
        return (1, 1), (1, 1), []

    start_node = random.choice(empty_spaces)
    
    # BFS로 가장 먼 탈출구 탐색
    queue = [start_node]
    visited = {start_node}
    furthest_node = start_node

    while queue:
        curr = queue.pop(0)
        furthest_node = curr
        cx, cy = curr
        for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < COLS and 0 <= ny < ROWS and tilemap[ny][nx] == 0:
                if (nx, ny) not in visited:
                    visited.add((nx, ny))
                    queue.append((nx, ny))
                    
    tilemap[furthest_node[1]][furthest_node[0]] = 2
    
    # 적 스폰 위치 선택 (시작점과 탈출구 제외한 빈 공간)
    enemy_candidates = [p for p in empty_spaces if p != start_node and p != furthest_node]
    num_to_spawn = min(NUM_ENEMIES, len(enemy_candidates))
    enemy_positions = random.sample(enemy_candidates, num_to_spawn)
    
    enemies = [Enemy(p[0], p[1]) for p in enemy_positions]
    return start_node, furthest_node, enemies

# =====================
# 메인 게임 클래스
# =====================
class MazeGame:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("3D 1인칭 레트로 FPS 동굴 탈출")
        self.font = pygame.font.SysFont(["malgungothic", "applegothic", "nanumgothic", None], 24)
        self.clock = pygame.time.Clock()
        
        # 3D 벽 가림 처리를 위한 Z-버퍼 데이터용 리스트
        self.z_buffer = [1e30] * SCREEN_WIDTH
        self.reset_game()

    def reset_game(self):
        self.seed = random.randint(0, 99999)
        self.tilemap = generate(self.seed)
        self.start_pos, self.exit_pos, self.enemies = find_positions(self.tilemap)
        
        # 플레이어 초기화
        self.pos_x = self.start_pos[0] + 0.5
        self.pos_y = self.start_pos[1] + 0.5
        self.dir_x = -1.0
        self.dir_y = 0.0
        self.plane_x = 0.0
        self.plane_y = 0.66 
        
        # 전투 시스템 변수
        self.is_shooting = False
        self.shoot_cooldown = 0.0
        self.flash_timer = 0.0
        
        self.state = "MAP" # MAP, PLAYING, WIN

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(60) / 1000.0 # 델타 타임(초 단위)
            
            # 쿨다운 감소 처리
            if self.shoot_cooldown > 0: self.shoot_cooldown -= dt
            if self.flash_timer > 0:
                self.flash_timer -= dt
                if self.flash_timer <= 0: self.is_shooting = False

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN and self.state == "MAP":
                        self.state = "PLAYING"
                        pygame.mouse.get_rel() 
                    elif event.key == pygame.K_r:
                        self.reset_game()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1 and self.state == "PLAYING": # 마우스 왼쪽 클릭 사격
                        self.shoot_weapon()

            if self.state == "PLAYING":
                pygame.mouse.set_visible(False)
                pygame.event.set_grab(True)
                self.handle_input(dt)
            else:
                pygame.mouse.set_visible(True)
                pygame.event.set_grab(False)
                
            self.draw()
            pygame.display.flip()

        pygame.quit()

    def handle_input(self, dt):
        keys = pygame.key.get_pressed()
        move_speed = 4.0 * dt  

        # 1. 마우스 시점 회전
        mouse_dx, _ = pygame.mouse.get_rel()
        mouse_sensitivity = 0.15  
        rot_speed = -mouse_dx * mouse_sensitivity * dt

        if rot_speed != 0:
            old_dir_x = self.dir_x
            self.dir_x = self.dir_x * math.cos(rot_speed) - self.dir_y * math.sin(rot_speed)
            self.dir_y = old_dir_x * math.sin(rot_speed) + self.dir_y * math.cos(rot_speed)
            old_plane_x = self.plane_x
            self.plane_x = self.plane_x * math.cos(rot_speed) - self.plane_y * math.sin(rot_speed)
            self.plane_y = old_plane_x * math.sin(rot_speed) + self.plane_y * math.cos(rot_speed)

        # 2. 키보드 이동 (W, A, S, D)
        if keys[pygame.K_w]:
            if self.tilemap[int(self.pos_y)][int(self.pos_x + self.dir_x * move_speed)] == 0: self.pos_x += self.dir_x * move_speed
            if self.tilemap[int(self.pos_y + self.dir_y * move_speed)][int(self.pos_x)] == 0: self.pos_y += self.dir_y * move_speed
        if keys[pygame.K_s]:
            if self.tilemap[int(self.pos_y)][int(self.pos_x - self.dir_x * move_speed)] == 0: self.pos_x -= self.dir_x * move_speed
            if self.tilemap[int(self.pos_y - self.dir_y * move_speed)][int(self.pos_x)] == 0: self.pos_y -= self.dir_y * move_speed
        if keys[pygame.K_a]: # 왼쪽 옆걸음
            sx, sy = -self.dir_y, self.dir_x
            if self.tilemap[int(self.pos_y)][int(self.pos_x + sx * move_speed)] == 0: self.pos_x += sx * move_speed
            if self.tilemap[int(self.pos_y + sy * move_speed)][int(self.pos_x)] == 0: self.pos_y += sy * move_speed
        if keys[pygame.K_d]: # 오른쪽 옆걸음
            sx, sy = self.dir_y, -self.dir_x
            if self.tilemap[int(self.pos_y)][int(self.pos_x + sx * move_speed)] == 0: self.pos_x += sx * move_speed
            if self.tilemap[int(self.pos_y + sy * move_speed)][int(self.pos_x)] == 0: self.pos_y += sy * move_speed

        # 승리 조건 체크: 모든 적 처치 + 탈출구 도달
        enemies_alive = any(e.alive for e in self.enemies)
        if not enemies_alive and int(self.pos_x) == self.exit_pos[0] and int(self.pos_y) == self.exit_pos[1]:
            self.state = "WIN"

    def shoot_weapon(self):
        if self.shoot_cooldown > 0:
            return
            
        self.is_shooting = True
        self.shoot_cooldown = 0.4  # 연사 속도 조절
        self.flash_timer = 0.1     # 총구 불꽃 유지 시간
        
        # 조준점(화면 중앙 정면)에 가장 가까운 적 찾기
        target_enemy = None
        min_angle_diff = 0.15 # 조준 오차 허용 범위 (약 8도)
        closest_dist = 1e30

        for enemy in self.enemies:
            if not enemy.alive: continue
            
            vx = enemy.x - self.pos_x
            vy = enemy.y - self.pos_y
            dist = math.hypot(vx, vy)
            
            # 플레이어 시선 각도와 적의 상대 각도 비교
            enemy_angle = math.atan2(vy, vx)
            player_angle = math.atan2(self.dir_y, self.dir_x)
            
            diff = (enemy_angle - player_angle + math.pi) % (2 * math.pi) - math.pi
            
            if abs(diff) < min_angle_diff:
                # 조준선 중앙의 벽 거리를 체크하여 벽 뒤의 적은 안 맞도록 처리
                center_wall_dist = self.z_buffer[SCREEN_WIDTH // 2]
                if dist < center_wall_dist and dist < closest_dist:
                    closest_dist = dist
                    target_enemy = enemy

        if target_enemy:
            target_enemy.health -= 50
            if target_enemy.health <= 0:
                target_enemy.alive = False

    def draw(self):
        if self.state == "MAP":
            self.draw_2d_map()
        elif self.state == "PLAYING":
            self.draw_3d_raycasting()
            self.draw_3d_sprites()
            self.draw_hud()
        elif self.state == "WIN":
            self.draw_win_screen()

    def draw_2d_map(self):
        self.screen.fill(COLOR_BG)
        for row in range(ROWS):
            for col in range(COLS):
                val = self.tilemap[row][col]
                color = COLOR_WALL if val == 1 else COLOR_FLOOR
                if val == 2: color = COLOR_EXIT
                pygame.draw.rect(self.screen, color, (col * TILE_SIZE, row * TILE_SIZE, TILE_SIZE, TILE_SIZE))
        
        # 적 위치 표시
        for e in self.enemies:
            if e.alive:
                pygame.draw.rect(self.screen, COLOR_ENEMY, (int(e.x)*TILE_SIZE, int(e.y)*TILE_SIZE, TILE_SIZE, TILE_SIZE))
                
        pygame.draw.rect(self.screen, COLOR_START, (self.start_pos[0] * TILE_SIZE, self.start_pos[1] * TILE_SIZE, TILE_SIZE, TILE_SIZE))

        msg1 = self.font.render("동굴과 생명체가 감지되었습니다!", True, COLOR_TEXT)
        msg2 = self.font.render("파란색: 시작점 / 초록색: 탈출구 / 빨간색: 적", True, COLOR_TEXT)
        msg3 = self.font.render("미션: 모든 적을 사살하고 탈출구로 가십시오.", True, (255, 100, 100))
        msg4 = self.font.render("[ENTER] 키를 눌러 진입하세요", True, (255, 255, 100))
        
        self.screen.blit(msg1, (10, 10))
        self.screen.blit(msg2, (10, 40))
        self.screen.blit(msg3, (10, 70))
        self.screen.blit(msg4, (10, 100))

    def draw_3d_raycasting(self):
        pygame.draw.rect(self.screen, COLOR_CEILING, (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT // 2))
        pygame.draw.rect(self.screen, COLOR_GROUND, (0, SCREEN_HEIGHT // 2, SCREEN_WIDTH, SCREEN_HEIGHT // 2))

        for x in range(SCREEN_WIDTH):
            camera_x = 2 * x / float(SCREEN_WIDTH) - 1
            ray_dir_x = self.dir_x + self.plane_x * camera_x
            ray_dir_y = self.dir_y + self.plane_y * camera_x

            map_x, map_y = int(self.pos_x), int(self.pos_y)
            delta_dist_x = abs(1 / ray_dir_x) if ray_dir_x != 0 else 1e30
            delta_dist_y = abs(1 / ray_dir_y) if ray_dir_y != 0 else 1e30

            hit = False
            side = 0
            hit_type = 0

            if ray_dir_x < 0:
                step_x, side_dist_x = -1, (self.pos_x - map_x) * delta_dist_x
            else:
                step_x, side_dist_x = 1, (map_x + 1.0 - self.pos_x) * delta_dist_x
            if ray_dir_y < 0:
                step_y, side_dist_y = -1, (self.pos_y - map_y) * delta_dist_y
            else:
                step_y, side_dist_y = 1, (map_y + 1.0 - self.pos_y) * delta_dist_y

            while not hit:
                if side_dist_x < side_dist_y:
                    side_dist_x += delta_dist_x
                    map_x += step_x
                    side = 0
                else:
                    side_dist_y += delta_dist_y
                    map_y += step_y
                    side = 1
                if self.tilemap[map_y][map_x] > 0:
                    hit = True
                    hit_type = self.tilemap[map_y][map_x]

            perp_wall_dist = (map_x - self.pos_x + (1 - step_x) / 2) / ray_dir_x if side == 0 else (map_y - self.pos_y + (1 - step_y) / 2) / ray_dir_y
            if perp_wall_dist <= 0: perp_wall_dist = 0.1
            
            # Z-버퍼에 현재 열의 벽 거리 기록 (적 그릴 때 판정용)
            self.z_buffer[x] = perp_wall_dist

            line_height = int(SCREEN_HEIGHT / perp_wall_dist)
            draw_start = max(0, -line_height // 2 + SCREEN_HEIGHT // 2)
            draw_end = min(SCREEN_HEIGHT - 1, line_height // 2 + SCREEN_HEIGHT // 2)

            color = COLOR_EXIT if hit_type == 2 else COLOR_WALL
            if side == 1:
                color = (max(color[0]-20, 0), max(color[1]-20, 0), max(color[2]-20, 0))

            pygame.draw.line(self.screen, color, (x, draw_start), (x, draw_end))

    def draw_3d_sprites(self):
        # 플레이어와의 거리에 따라 적 정렬 (원근감 구현을 위해 먼 적부터 렌더링)
        active_enemies = [e for e in self.enemies if e.alive]
        active_enemies.sort(key=lambda e: math.hypot(e.x - self.pos_x, e.y - self.pos_y), reverse=True)

        for enemy in active_enemies:
            sprite_x = enemy.x - self.pos_x
            sprite_y = enemy.y - self.pos_y

            # 카메라 매트릭스 변환 역행렬 계산
            inv_det = 1.0 / (self.plane_x * self.dir_y - self.dir_x * self.plane_y)
            transform_x = inv_det * (self.dir_y * sprite_x - self.dir_x * sprite_y)
            transform_y = inv_det * (-self.plane_y * sprite_x + self.plane_x * sprite_y) # 이게 카메라 정면 깊이(Z축)

            if transform_y <= 0: continue # 플레이어 뒤에 있는 경우 패스

            sprite_screen_x = int((SCREEN_WIDTH / 2) * (1 + transform_x / transform_y))
            
            # 화면 상의 크기 계산
            sprite_height = abs(int(SCREEN_HEIGHT / transform_y))
            draw_start_y = max(0, -sprite_height // 2 + SCREEN_HEIGHT // 2)
            draw_end_y = min(SCREEN_HEIGHT - 1, sprite_height // 2 + SCREEN_HEIGHT // 2)

            sprite_width = abs(int(SCREEN_HEIGHT / transform_y))
            draw_start_x = max(0, -sprite_width // 2 + sprite_screen_x)
            draw_end_x = min(SCREEN_WIDTH - 1, sprite_width // 2 + sprite_screen_x)

            # 세로선(Stripe) 단위로 렌더링하며 벽 뒤에 있는지 체크
            for stripe in range(draw_start_x, draw_end_x):
                if 0 <= stripe < SCREEN_WIDTH and transform_y < self.z_buffer[stripe]:
                    # 간단한 적의 형태 그리기 (기둥 모양 원통형 크리처 표현)
                    pygame.draw.line(self.screen, COLOR_ENEMY, (stripe, draw_start_y), (stripe, draw_end_y))

    def draw_hud(self):
        # 1. 조준점(Crosshair)
        cx, cy = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
        pygame.draw.line(self.screen, (255, 255, 255), (cx - 8, cy), (cx + 8, cy), 2)
        pygame.draw.line(self.screen, (255, 255, 255), (cx, cy - 8), (cx, cy + 8), 2)

        # 2. 총(Weapon) 렌더링 (화면 아래 중앙)
        gun_base_x = SCREEN_WIDTH // 2
        gun_base_y = SCREEN_HEIGHT
        
        # 총기 몸체 그리기 (폴리곤)
        gun_poly = [(gun_base_x - 25, gun_base_y), (gun_base_x - 15, gun_base_y - 120), 
                    (gun_base_x + 15, gun_base_y - 120), (gun_base_x + 25, gun_base_y)]
        pygame.draw.polygon(self.screen, (70, 70, 70), gun_poly)
        pygame.draw.rect(self.screen, (40, 40, 40), (gun_base_x - 8, gun_base_y - 135, 16, 40)) # 총열

        # 사격 시 총구 불꽃(Muzzle Flash) 효과
        if self.is_shooting:
            pygame.draw.circle(self.screen, (255, 180, 0), (gun_base_x, gun_base_y - 140), 25)
            pygame.draw.circle(self.screen, (255, 255, 255), (gun_base_x, gun_base_y - 140), 12)

        # 3. 상태창 텍스트
        alive_count = sum(1 for e in self.enemies if e.alive)
        status_str = f"생존한 적: {alive_count}명" if alive_count > 0 else "탈출구가 열렸습니다! 초록색 벽으로 가세요!"
        status_color = (255, 100, 100) if alive_count > 0 else (100, 255, 100)
        
        msg = self.font.render(f"W,A,S,D: 이동 | 마우스: 회전 | 클릭: 사격 | {status_str}", True, status_color)
        self.screen.blit(msg, (10, 10))

    def draw_win_screen(self):
        self.screen.fill((20, 100, 20))
        msg1 = self.font.render("MISSION COMPLETE - 탈출 성공!", True, (255, 255, 255))
        msg2 = self.font.render("[R] 키를 눌러 새로운 작전 시작", True, (200, 255, 200))
        
        self.screen.blit(msg1, (SCREEN_WIDTH//2 - msg1.get_width()//2, SCREEN_HEIGHT//2 - 30))
        self.screen.blit(msg2, (SCREEN_WIDTH//2 - msg2.get_width()//2, SCREEN_HEIGHT//2 + 10))

if __name__ == "__main__":
    game = MazeGame()
    game.run()