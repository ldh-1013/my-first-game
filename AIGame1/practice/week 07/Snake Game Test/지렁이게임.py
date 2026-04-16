import pygame
import math
import random
import os
import base64
import io

# 1. 초기 설정
pygame.init()
pygame.mixer.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Snake Mission: Desert Diet")
clock = pygame.time.Clock()

# 색상 정의
BLACK = (20, 20, 20)
WHITE = (255, 255, 255)
YELLOW = (255, 255, 0)
ORANGE_ITEM = (255, 165, 0) 
BLUE_GHOST = (160, 210, 255)
PASTEL_PURPLE_HEAD = (200, 160, 255)
PASTEL_PURPLE_TAIL = (235, 220, 255)
EYE_COLOR = (0, 0, 0)
RED = (255, 80, 80)
EXIT_COLOR = (100, 255, 100)
DESERT_COLOR = (210, 180, 140)

# 화면 흔들림 설정
shake_timer = 0
shake_amount = 3 

# --- [폰트 설정] ---
try:
    font_en_big = pygame.font.Font("./assets/fonts/AGENCYB.TTF", 50)
    font_en_mid = pygame.font.Font("./assets/fonts/AGENCYB.TTF", 28)
    font_en_small = pygame.font.Font("./assets/fonts/AGENCYB.TTF", 18)
    font_ko_mid = pygame.font.Font("./assets/fonts/gmar.TTF", 22)
    font_ko_small = pygame.font.Font("./assets/fonts/gmar.TTF", 16)
except:
    font_en_big = pygame.font.SysFont("arial", 50, bold=True)
    font_en_mid = pygame.font.SysFont("arial", 28, bold=True)
    font_en_small = pygame.font.SysFont("arial", 18)
    font_ko_mid = pygame.font.SysFont("malgungothic", 22)
    font_ko_small = pygame.font.SysFont("malgungothic", 16)

# --- [에셋 로드] ---
try:
    eat_sound = pygame.mixer.Sound("./assets/sounds/eat.mp3")
    minus_eat_sound = pygame.mixer.Sound("./assets/sounds/minus eat.mp3")
    die_sound = pygame.mixer.Sound("./assets/sounds/die.mp3")       
    complete_sound = pygame.mixer.Sound("./assets/sounds/Completed.wav")
except:
    eat_sound = None
    minus_eat_sound = None
    die_sound = None
    complete_sound = None

try:
    pygame.mixer.music.load("./assets/sounds/bgm.wav")
    pygame.mixer.music.set_volume(0.5)
    pygame.mixer.music.play(-1)
except:
    pass

# --- [먹이 이미지 로드] ---
try:
    green_food_img = pygame.image.load("./assets/images/green.png").convert_alpha()
    green_food_img = pygame.transform.scale(green_food_img, (22, 22))
except:
    green_food_img = None
try:
    yellow_food_img = pygame.image.load("./assets/images/yellow.png").convert_alpha()
    yellow_food_img = pygame.transform.scale(yellow_food_img, (26, 26))
except:
    yellow_food_img = None
try:
    orange_food_img = pygame.image.load("./assets/images/orange.png").convert_alpha()
    orange_food_img = pygame.transform.scale(orange_food_img, (24, 24))
except:
    orange_food_img = None

# --- [장애물 이미지 로드] ---
try:
    sand1 = pygame.image.load("./assets/images/sand1.png").convert_alpha()
    sand2 = pygame.image.load("./assets/images/sand2.png").convert_alpha()
    sand3 = pygame.image.load("./assets/images/sand3.png").convert_alpha()
    BARRIER_HEIGHT = sand1.get_height()
    sand_variants = [sand2, sand3]
except:
    sand1 = pygame.Surface((40, 40)); sand1.fill((139, 69, 19))
    sand2 = sand1; sand3 = sand1
    BARRIER_HEIGHT = 40
    sand_variants = [sand1]

# --- [스프라이트 시트 로드 (Base64)] ---
SHEET_B64 = "iVBORw0KGgoAAAANSUhEUgAAAGAAAABgCAMAAADVRocKAAAABGdBTUEAALGPC/xhBQAAADNQTFRFAAAAxKju/96M7JoeYWu6nfjkiG2vo4bOY7ime9jExHxx36mI882s/7hMd4/bRzJL////Ur3JYAAAAAF0Uk5TAEDm2GYAAAQxSURBVGje7VmJcuMgDE1r11dio///2iIEWBIihh4zu52w6XhWhveEDhD4dnu1V/vDDULDx2/iR5YfgSvgnW/46GOwe2s9E35i6JRZ6EvzqG1J0EjjLGlLPqP6Hb3EWXV4T/U9HMmLSf0GCZW0kABOJxIWpUbR4bN/8o4mAAwmk6EppiZIArvEZjkQK3hQEofeyEsG6OKcDIEaKsAQHkgRe6H2Jr04CxwkWOUI2ptIJ5IBDeUeG3ykOEyDVkQdOL4DID2Bix4EyFEQCNPUHFyNBsuiyZAIoTA1sygmITTmm0/KB5lBi0kP4H7KlC6eFKScgWDjSsgbideXiHHAREiKBk/nhpE0jkJgyEqxJLk1dOjP5hghY/2yK8FPMlvzGQUWwBIIQXZ7L/dZO8af311vHDti1X9oJ3jqkqXPObrlSVJmBZRvcetZSuVJUGdiQFgLfbZ6p+zTpzC+Z4xg/BHu3EczYEH7KY0p8tZD/BAFK31A+sxdfJXibPcpcEvgXhK8JPPM0d/ggATltou3xeNwtE725eerZkTMQCCffg3zbVACjUm5qC1TqLoDODep+3+6+bfhC4iuFniQg4ZdAAd9z4psNuNxUqMgdQWADIW8g3jSxOTOROyota0BeGPzDPa0pVBRqPCRqQFYi1xVKawILxudAkAoQp8ulqkIs3AvLaaDaMv5sZj6fgvOnqQFIv7hdKEQE19EFX92g6tH1rSOmisYUXd8jqK9qKbq8/1910av9E7Um/Ad3OTYO8NMZfGfKFU3FYbK3VoYGTWPZ5eS20lb+ltWA8SIu/G5qq+yugEpN2dbYTlADsjQNMx4G+iucYEZFDcjWNMj39/d935UToF4Y2UC2pijeiWDXA8R1SAuQpSkRUHPlZZ5dGNWBCk0DjhcC/oqS2BF5UYxbU65oSvr4NgxCoyCfpgF7lyPsKUtNmXjYywEonyLBsOsZGECZmDR9Unhxgjhk1z4wgE5b7Eof25dJ7G3t9r10cgFExNFv9TpNwszzkAgspF3njTMP3PXCy+frYHjzD1zOdAH1X870AdUuZ75QjddueeS16SVDLxAd0cIBxKlzxvP9rBUongFdPqO1EPQAxYNMvMjYrm3UCxRMeeR2baNuICk/qp8PhJN7gEgOx/F44OPJnTabQh9Q7I/ysz/oWz4Rjx1AUR4Pye64vkTsA8ry2KI84h/K1tANVDMp3VH5/x3p5Si+mTQDFUFxkKLhhiQQgAvGeIyjJKg5WcvJFmTRYNP0uYUIjjCDRxdBBmK3keMYxPiCL2TYORE4pwkkEKkqgCAZ+0jdUU6apokJAuZkBZQznAG505sGAaUBN1ERphaBH34CsXAxLrWj708nN83gDC43jiLgdUYlE51hemgfEMpYfvFTpQuYHxZoycyRMvp/lqoMPzEAsK/N9Q91tOiXBJ/+SvnF/olvSAAAAABJRU5ErkJggg=="

try:
    try:
        player_sheet = pygame.image.load("./assets/images/animal.png").convert_alpha()
    except:
        sheet_bytes = base64.b64decode(SHEET_B64)
        player_sheet = pygame.image.load(io.BytesIO(sheet_bytes)).convert_alpha()
    player_frames = []
    for i in range(16):
        row, col = divmod(i, 4)
        rect = pygame.Rect(col * 24, row * 24, 24, 24)
        player_frames.append(player_sheet.subsurface(rect))
    red_food_frames = [player_frames[i] for i in [0, 1, 2]]
    animal_walk_frames = [player_frames[i] for i in [8, 9, 10]]
except:
    red_food_frames = None
    animal_walk_frames = None

# Scene 상태
TITLE, GAME, SUCCESS, FAILURE = 0, 1, 2, 3
scene = TITLE
played_end_sound = False 

class FloatingText:
    def __init__(self, x, y, text, color):
        self.x, self.y, self.text, self.color = x, y, text, color
        self.alpha, self.life = 255, 60
    def update(self):
        self.y -= 1; self.alpha -= 4; self.life -= 1
    def draw(self, surface, offset=(0, 0)):
        if self.life > 0:
            text_surf = font_en_small.render(self.text, True, self.color)
            text_surf.set_alpha(max(0, self.alpha))
            surface.blit(text_surf, (self.x + offset[0], self.y + offset[1]))

class MovingAnimal:
    def __init__(self):
        self.respawn()
        self.frame_index = 0
        self.anim_timer = 0
    def respawn(self):
        while True:
            self.x, self.y = random.randint(50, WIDTH - 50), random.randint(BARRIER_HEIGHT + 20, HEIGHT - BARRIER_HEIGHT - 20)
            rect = pygame.Rect(self.x-16, self.y-16, 32, 32)
            if not any(obs['rect'].colliderect(rect) for obs in obstacles): break
        self.angle = random.uniform(0, math.pi * 2)
        self.speed = 1.6
        self.active = False 
    def update(self):
        if not self.active: return
        self.x += math.cos(self.angle) * self.speed
        self.y += math.sin(self.angle) * self.speed
        if random.random() < 0.02: self.angle += random.uniform(-0.5, 0.5)
        # 맵 영역 경계 및 장애물 충돌 확인
        rect = pygame.Rect(self.x - 16, self.y - 16, 32, 32)
        collided = rect.top < BARRIER_HEIGHT or rect.bottom > HEIGHT - BARRIER_HEIGHT or rect.left < 0 or rect.right > WIDTH or any(obs['rect'].colliderect(rect) for obs in obstacles)
        if collided: # 충돌 시 튕겨나가는 효과
            self.angle += math.pi # 각도를 반대로 변경
            self.angle %= math.pi * 2
        
        self.x %= WIDTH; self.y %= HEIGHT
        self.anim_timer += 1
        if self.anim_timer >= 10:
            self.frame_index = (self.frame_index + 1) % len(animal_walk_frames)
            self.anim_timer = 0
    def draw(self, surface, offset=(0, 0)):
        if self.active and animal_walk_frames:
            img = pygame.transform.scale(animal_walk_frames[self.frame_index], (32, 32))
            surface.blit(img, (self.x - 16 + offset[0], self.y - 16 + offset[1]))

class Snake:
    def __init__(self):
        self.reset()
    def reset(self):
        self.x, self.y = -200, HEIGHT // 2
        self.angle, self.base_speed, self.max_speed = 0, 2.5, 7.5
        self.current_speed, self.turn_speed, self.radius = self.base_speed, 0.11, 10
        self.length = 600 
        self.body = [(self.x - i, self.y) for i in range(int(self.length))]
        self.is_entering, self.is_ghost, self.ghost_timer, self.cooldown_timer = True, False, 0, 0
        self.yoyo_timer, self.yoyo_max = 0, 420 
        self.effect_type = None
        self.effect_timer = 0
        
    def update(self):
        temp_max_speed = self.max_speed
        temp_radius = 10
        if self.effect_timer > 0:
            self.effect_timer -= 1
            if self.effect_type == "THICK": temp_radius = 18
            elif self.effect_type == "THIN": temp_radius = 5
            elif self.effect_type == "FAST": temp_max_speed = 7.5
            elif self.effect_type == "SLOW": temp_max_speed = 2.5
        else: self.effect_type = None

        self.radius = temp_radius
        speed_progress = (600 - self.length) / 590
        self.current_speed = self.base_speed + (speed_progress * (temp_max_speed - self.base_speed))
        
        keys = pygame.key.get_pressed()
        if keys[pygame.K_a]: self.angle -= self.turn_speed
        if keys[pygame.K_d]: self.angle += self.turn_speed
        if keys[pygame.K_SPACE] and self.cooldown_timer <= 0:
            self.is_ghost, self.ghost_timer, self.cooldown_timer = True, 150, 1080
            self.yoyo_timer += (self.yoyo_max * 0.35)
        if self.ghost_timer > 0: self.ghost_timer -= 1
        else: self.is_ghost = False
        if self.cooldown_timer > 0: self.cooldown_timer -= 1
        self.yoyo_timer += 1
        self.x += math.cos(self.angle) * self.current_speed
        self.y += math.sin(self.angle) * self.current_speed
        if self.is_entering and self.x > self.radius: self.is_entering = False
        self.body.insert(0, (self.x, self.y))
        if len(self.body) > self.length: self.body = self.body[:int(self.length)]
        
    def check_self_collision(self):
        if self.is_entering or self.is_ghost: return False 
        for i, seg in enumerate(self.body):
            if i > 30 and math.hypot(self.x - seg[0], self.y - seg[1]) < self.radius * 0.7: return True
        return False

    def draw(self, surface, offset=(0, 0), is_dead=False):
        body_count = len(self.body)
        for i, segment in enumerate(self.body):
            ratio = i / body_count if body_count > 1 else 0
            current_color = BLUE_GHOST if self.is_ghost else (
                int(PASTEL_PURPLE_HEAD[0]*(1-ratio)+PASTEL_PURPLE_TAIL[0]*ratio),
                int(PASTEL_PURPLE_HEAD[1]*(1-ratio)+PASTEL_PURPLE_TAIL[1]*ratio),
                int(PASTEL_PURPLE_HEAD[2]*(1-ratio)+PASTEL_PURPLE_TAIL[2]*ratio)
            )
            seg_rad = int(self.radius if i > 0 else self.radius+2)
            pygame.draw.circle(surface, current_color, (int(segment[0] + offset[0]), int(segment[1] + offset[1])), seg_rad)
        if self.x > -self.radius:
            for side in [-1, 1]:
                eye_angle = self.angle + (side * math.pi / 4)
                ex, ey = self.x + math.cos(eye_angle) * (self.radius * 0.6) + offset[0], self.y + math.sin(eye_angle) * (self.radius * 0.6) + offset[1]
                if is_dead:
                    pygame.draw.line(surface, EYE_COLOR, (ex-4, ey-4), (ex+4, ey+4), 2)
                    pygame.draw.line(surface, EYE_COLOR, (ex+4, ey-4), (ex-4, ey+4), 2)
                else: pygame.draw.circle(surface, EYE_COLOR, (int(ex), int(ey)), 2)

class Food:
    def __init__(self, color, value):
        self.color, self.value, self.active = color, value, (value != 30)
        self.max_timer = 300
        self.timer, self.frame_index, self.anim_timer, self.anim_delay = self.max_timer, 0, pygame.time.get_ticks(), 150
        self.respawn()
    def respawn(self):
        while True:
            self.x, self.y = random.randint(50, WIDTH - 50), random.randint(BARRIER_HEIGHT + 30, HEIGHT - BARRIER_HEIGHT - 30)
            rect = pygame.Rect(self.x-10, self.y-10, 20, 20)
            if not any(obs['rect'].colliderect(rect) for obs in obstacles): break
        if self.value == 30 or self.color == RED: self.timer = self.max_timer
    def update(self):
        if self.color == RED:
            self.timer -= 1
            if self.timer <= 0: self.respawn()
    def draw(self, surface, offset=(0, 0)):
        if self.active:
            if self.color == RED and red_food_frames:
                now = pygame.time.get_ticks()
                if now - self.anim_timer >= self.anim_delay:
                    self.frame_index = (self.frame_index + 1) % len(red_food_frames); self.anim_timer = now
                img = red_food_frames[self.frame_index]; img_w, img_h = img.get_size()
                surface.blit(img, (self.x - img_w//2 + offset[0], self.y - img_h//2 + offset[1]))
            elif self.color == WHITE and green_food_img:
                surface.blit(green_food_img, (self.x - 11 + offset[0], self.y - 11 + offset[1]))
            elif self.color == YELLOW and yellow_food_img:
                surface.blit(yellow_food_img, (self.x - 13 + offset[0], self.y - 13 + offset[1]))
            elif self.value == 30 and orange_food_img:
                surface.blit(orange_food_img, (self.x - 12 + offset[0], self.y - 12 + offset[1]))
            else:
                r = 8; pygame.draw.circle(surface, self.color, (self.x + offset[0], self.y + offset[1]), r)
            if self.value == 30 and self.timer > 0:
                pygame.draw.rect(surface, (50, 50, 50), (self.x - 15 + offset[0], self.y - 15 + offset[1], 30, 4))
                pygame.draw.rect(surface, ORANGE_ITEM, (self.x - 15 + offset[0], self.y - 15 + offset[1], (self.timer / 300) * 30, 4))

def draw_exit(surface, frame_count, offset=(0, 0)):
    cx, cy = WIDTH // 2 + offset[0], HEIGHT // 2 + offset[1]
    for r in range(5, 35, 4):
        pulse_r = r + (frame_count % 15) / 3; alpha = max(0, 200 - (pulse_r / 35) * 200)
        s = pygame.Surface((pulse_r * 2, pulse_r * 2), pygame.SRCALPHA); pygame.draw.circle(s, (*EXIT_COLOR, int(alpha)), (pulse_r, pulse_r), pulse_r, 2)
        surface.blit(s, (cx - pulse_r, cy - pulse_r))
    pygame.draw.circle(surface, WHITE, (cx, cy), 4)

def check_barrier_collision(x, y, radius):
    if y < BARRIER_HEIGHT or y > HEIGHT - BARRIER_HEIGHT:
        return True
    for obs in obstacles:
        if obs['rect'].inflate(radius, radius).collidepoint(x, y):
            return True
    return False

def draw_barriers(surface, offset=(0, 0)):
    if sand1:
        img_w = sand1.get_width()
        for i in range(0, WIDTH + img_w, img_w):
            surface.blit(sand1, (i + offset[0], 0 + offset[1]))
            surface.blit(sand1, (i + offset[0], HEIGHT - BARRIER_HEIGHT + offset[1]))
        for obs in obstacles:
            surface.blit(obs['image'], (obs['rect'].x + offset[0], obs['rect'].y + offset[1]))

def create_random_obstacles():
    obs_list = []
    cols, rows = 4, 3
    section_w = WIDTH // cols
    section_h = (HEIGHT - 2 * BARRIER_HEIGHT) // rows
    
    for r in range(rows):
        for c in range(cols):
            if c == 0 and r == 1: continue 
            shape_type = random.choice(["L", "I", "T", "G"]) 
            current_sand = random.choice(sand_variants)
            img_w, img_h = current_sand.get_size()
            placed = False
            for _ in range(20):
                temp_group = []
                base_x = random.randint(c * section_w + 10, (c + 1) * section_w - (img_w * 3))
                base_y = random.randint(BARRIER_HEIGHT + r * section_h + 10, BARRIER_HEIGHT + (r + 1) * section_h - (img_h * 3))
                if shape_type == "I":
                    horizontal = random.random() < 0.5
                    for i in range(3):
                        x = base_x + (i * img_w if horizontal else 0)
                        y = base_y + (0 if horizontal else i * img_h)
                        temp_group.append({'image': current_sand, 'rect': pygame.Rect(x, y, img_w, img_h)})
                elif shape_type == "L":
                    temp_group.append({'image': current_sand, 'rect': pygame.Rect(base_x, base_y, img_w, img_h)})
                    temp_group.append({'image': current_sand, 'rect': pygame.Rect(base_x, base_y + img_h, img_w, img_h)})
                    temp_group.append({'image': current_sand, 'rect': pygame.Rect(base_x + img_w, base_y + img_h, img_w, img_h)})
                elif shape_type == "T":
                    temp_group.append({'image': current_sand, 'rect': pygame.Rect(base_x, base_y, img_w, img_h)})
                    temp_group.append({'image': current_sand, 'rect': pygame.Rect(base_x + img_w, base_y, img_w, img_h)})
                    temp_group.append({'image': current_sand, 'rect': pygame.Rect(base_x + img_w * 2, base_y, img_w, img_h)})
                    temp_group.append({'image': current_sand, 'rect': pygame.Rect(base_x + img_w, base_y + img_h, img_w, img_h)})
                else: 
                    for i in range(2):
                        for j in range(2):
                            temp_group.append({'image': current_sand, 'rect': pygame.Rect(base_x + i * img_w, base_y + j * img_h, img_w, img_h)})
                exit_rect = pygame.Rect(WIDTH//2 - 80, HEIGHT//2 - 80, 160, 160)
                collision_with_exit = any(new['rect'].colliderect(exit_rect) for new in temp_group)
                if not collision_with_exit:
                    if not any(any(new['rect'].inflate(20, 20).colliderect(existing['rect']) for existing in obs_list) for new in temp_group):
                        obs_list.extend(temp_group)
                        placed = True
                        break
    return obs_list

# 초기화
obstacles = create_random_obstacles()
snake, foods, purple_food = Snake(), [Food(WHITE, 5), Food(YELLOW, 15), Food(RED, -20)], Food(ORANGE_ITEM, 30)
special_animal = MovingAnimal()
last_spawn_tier = -1 
floating_texts, score, frame_count, can_exit, running = [], 0, 0, False, True

while running:
    render_offset = [0, 0]
    if shake_timer > 0:
        render_offset = [random.randint(-shake_amount, shake_amount), random.randint(-shake_amount, shake_amount)]; shake_timer -= 1
    screen.fill(DESERT_COLOR)
    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE: running = False
            if scene == TITLE and event.key == pygame.K_q: scene = GAME
            elif scene in [SUCCESS, FAILURE] and event.key == pygame.K_r:
                obstacles = create_random_obstacles()
                snake.reset(); score = 0; can_exit = False; purple_food.active = False; special_animal.active = False; last_spawn_tier = -1; floating_texts, scene, shake_timer = [], GAME, 0
                played_end_sound = False 

    if scene == TITLE:
        title_txt = font_en_big.render("DESERT DIET MISSION", True, BLACK); screen.blit(title_txt, (WIDTH//2 - title_txt.get_width()//2, HEIGHT//2 - 180))
        controls = ["A, D - 방향 전환  /  Space - 유령 모드", "상/하단 장애물을 조심하세요!", "특수 동물은 70점마다 1회 등장합니다!", "R - Restart  /  Esc - Quit"]
        for i, txt in enumerate(controls):
            ctrl_surf = font_ko_mid.render(txt, True, BLACK); screen.blit(ctrl_surf, (WIDTH//2 - ctrl_surf.get_width()//2, HEIGHT//2 - 40 + i*35))
        start_txt = font_en_big.render("[ Q - Start Game ]", True, (150, 50, 0)); screen.blit(start_txt, (WIDTH//2 - start_txt.get_width()//2, HEIGHT - 100))
    elif scene in [GAME, FAILURE, SUCCESS]:
        if scene == GAME:
            snake.update()
            special_animal.update()
            current_tier = score // 70
            if current_tier > last_spawn_tier and not special_animal.active:
                special_animal.respawn()
                special_animal.active = True
                last_spawn_tier = current_tier
            target_bugs = 1 + (score // 100); red_foods = [f for f in foods if f.color == RED]
            while len(red_foods) < target_bugs:
                nb = Food(RED, -20); foods.append(nb); red_foods.append(nb)
            while len(red_foods) > target_bugs: foods.remove(red_foods.pop())
            for f in foods: f.update()
            if snake.yoyo_timer >= snake.yoyo_max:
                score -= 20; snake.length += 50; snake.yoyo_timer = 0
                floating_texts.append(FloatingText(snake.x, snake.y - 20, "-20 (YOYO!)", RED))
                if score < -40: 
                    scene = FAILURE; shake_timer = 40
                    if not played_end_sound and die_sound: die_sound.play(); played_end_sound = True
            if special_animal.active and math.hypot(snake.x - special_animal.x, snake.y - special_animal.y) < snake.radius + 15:
                if eat_sound: eat_sound.play()
                special_animal.active = False
                effect = random.choice(["THICK", "THIN", "FAST", "SLOW"])
                snake.effect_type, snake.effect_timer = effect, 600
                floating_texts.append(FloatingText(special_animal.x, special_animal.y, f"EFFECT: {effect}", ORANGE_ITEM))
            if purple_food.active:
                purple_food.timer -= 1
                if purple_food.timer <= 0: purple_food.active = False
            for f in foods + ([purple_food] if purple_food.active else []):
                if math.hypot(snake.x - f.x, snake.y - f.y) < snake.radius + 8:
                    if f.color == RED:
                        if minus_eat_sound: minus_eat_sound.play()
                        score += f.value; snake.length += 10; shake_timer = 15
                    else:
                        if eat_sound: eat_sound.play()
                        score += f.value; snake.length = max(10, snake.length - (f.value * 1.8))
                    if snake.cooldown_timer > 0: snake.cooldown_timer = max(0, snake.cooldown_timer - 30)
                    snake.yoyo_timer = 0; f_color = RED if f.value < 0 else (YELLOW if f.value >= 15 else (WHITE if f.value != 30 else ORANGE_ITEM))
                    floating_texts.append(FloatingText(f.x, f.y, f"{f.value} Pts", f_color))
                    if f == purple_food: purple_food.active = False
                    else:
                        f.respawn()
                        if not purple_food.active and random.random() < 0.15: purple_food.respawn(); purple_food.active = True
            if score >= 600:
                can_exit = True
                if math.hypot(snake.x - WIDTH//2, snake.y - HEIGHT//2) < 20: 
                    scene = SUCCESS
                    if not played_end_sound and complete_sound: complete_sound.play(); played_end_sound = True
            if (not snake.is_ghost and not snake.is_entering and check_barrier_collision(snake.x, snake.y, snake.radius)) or \
               snake.check_self_collision() or score < -40: 
                scene = FAILURE; shake_timer = 40
                if not played_end_sound and die_sound: die_sound.play(); played_end_sound = True
            if not snake.is_entering: snake.x %= WIDTH; snake.y %= HEIGHT
        
        if can_exit: draw_exit(screen, frame_count, render_offset)
        snake.draw(screen, render_offset, is_dead=(scene == FAILURE))
        for f in foods: f.draw(screen, render_offset)
        if purple_food.active: purple_food.draw(screen, render_offset)
        special_animal.draw(screen, render_offset)
        draw_barriers(screen, render_offset)
        for ft in floating_texts[:]:
            ft.update(); ft.draw(screen, render_offset) if ft.life > 0 else floating_texts.remove(ft)
        
        # UI
        screen.blit(font_en_mid.render(f"Score: {score} / 600", True, BLACK), (20 + render_offset[0], 20 + render_offset[1]))
        if snake.effect_type:
            screen.blit(font_ko_small.render(f"상태: {snake.effect_type} ({snake.effect_timer//60}s)", True, RED), (20 + render_offset[0], 50 + render_offset[1]))
        
        bx, by, bw, bh = WIDTH - 170, 40, 150, 12
        pygame.draw.rect(screen, (50, 50, 50), (bx + render_offset[0], by + render_offset[1], bw, bh))
        yr = min(1.0, snake.yoyo_timer / snake.yoyo_max)
        pygame.draw.rect(screen, RED if yr > 0.7 else YELLOW, (bx + render_offset[0], by + render_offset[1], bw * yr, bh))
        screen.blit(font_en_small.render("YOYO GAUGE", True, BLACK), (bx + render_offset[0], by - 25 + render_offset[1]))
        
        gx = bx - 190
        pygame.draw.rect(screen, (50, 50, 50), (gx + render_offset[0], by + render_offset[1], bw, bh))
        gr = 1 - (snake.cooldown_timer / 1080)
        pygame.draw.rect(screen, BLUE_GHOST, (gx + render_offset[0], by + render_offset[1], bw * gr, bh))
        gcd = math.ceil(snake.cooldown_timer / 60)
        gl = f"GHOST: {gcd}s" if gcd > 0 else "GHOST: READY"
        screen.blit(font_en_small.render(gl, True, BLACK), (gx + render_offset[0], by - 25 + render_offset[1]))

        if scene in [SUCCESS, FAILURE]:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); overlay.fill((0, 0, 0, 150)); screen.blit(overlay, (0, 0))
            msg = font_en_big.render("MISSION COMPLETE" if scene == SUCCESS else "GAME OVER", True, (0, 255, 0) if scene == SUCCESS else RED)
            screen.blit(msg, (WIDTH//2 - msg.get_width()//2 + render_offset[0], HEIGHT//2 - 100 + render_offset[1]))
            final_score_txt = font_en_mid.render(f"Final Score: {score}", True, WHITE)
            screen.blit(final_score_txt, (WIDTH//2 - final_score_txt.get_width()//2, HEIGHT//2 - 20))
            screen.blit(font_ko_mid.render("[ R - 다시 시작 ]", True, WHITE), (WIDTH//2 - 80, HEIGHT//2 + 80))
    
    frame_count += 1; pygame.display.flip(); clock.tick(60)

pygame.quit()
