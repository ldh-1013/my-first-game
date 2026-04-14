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
PURPLE_ITEM = (180, 0, 255)
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

# --- [에셋 로드] ---
try:
    eat_sound = pygame.mixer.Sound("./assets/sounds/eat.mp3")
    minus_eat_sound = pygame.mixer.Sound("./assets/sounds/minus eat.mp3")
except:
    eat_sound = None
    minus_eat_sound = None

try:
    pygame.mixer.music.load("./assets/sounds/bgm.wav")
    pygame.mixer.music.set_volume(0.5)
    pygame.mixer.music.play(-1)
except:
    pass

# --- [스프라이트 시트 로드] ---
SHEET_B64 = "iVBORw0KGgoAAAANSUhEUgAAAGAAAABgCAMAAADVRocKAAAABGdBTUEAALGPC/xhBQAAADNQTFRFAAAAxKju/96M7JoeYWu6nfjkiG2vo4bOY7ime9jExHxx36mI882s/7hMd4/bRzJL////Ur3JYAAAAAF0Uk5TAEDm2GYAAAQxSURBVGje7VmJcuMgDE1r11dio///2iIEWBIihh4zu52w6XhWhveEDhD4dnu1V/vDDULDx2/iR5YfgSvgnW/46GOwe2s9E35i6Jy4JRZ6EvzqG1J0EjjLGlLPqP6Hb3EWXV4T/U9HMmLSf0GCZW0kABOJxIWpUbR4bN/8o4mAAwmk6EppiZIArvEZjkQK3hQEofeyEsG6OKcDIEaKsAQHkgRe6H2Jr04CxwkWOUI2ptIJ5IBDeUeG3ykOEyDVkQdOL4DID2Bix4EyFEQCNPUHFyNBsuiyZAIoTA1sygmITTmm0/KB5lBi0kP4H7KlC6eFKScgWDjSsgbideXiHHAREiKBk/nhpE0jkJgyEqxJLk1dOjP5hghY/2yK8FPMlvzGQUWwBIIQXZ7L/dZO8af311vHDti1X9oJ3jqkqXPObrlSVJmBZRvcetZSuVJUGdiQFgLfbZ6p+zTpzC+Z4xg/BHu3EczYEH7KY0p8tZD/BAFK31A+sxdfJXibPcpcEvgXhK8JPPM0d/ggATltou3xeNwtE725eerZkTMQCCffg3zbVACjUm5qC1TqLoDODep+3+6+bfhC4iuFniQg4ZdAAd9z4psNuNxUqMgdQWADIW8g3jSxOTOROyota0BeGPzDNa0pVBRqPCRqQFYi1xVKawILxudAkAoQp8ulqkIs3AvLaaDaMv5sZj6fgvOnqQFIv7hdKEQE19EFX92g6tH1rSOmisYUXd8jqK9qKbq8/1910av9E7Um/Ad3OTYO8NMZfGfKFU3FYbK3VoYGTWPZ5eS20lb+ltWA8SIu/G5qq+yugEpN2dbYTlADsjQNMx4G+iucYEZFDcjWNMj39/d935UToF4Y2UC2pijeiWDXA8R1SAuQpSkRUHPlZZ5dGNWBCk0DjhcC/oqS2BF5UYxbU65oSvr4NgxCoyCfpgF7lyPsKUtNmXjYywEonyLBsOsZGECZmDR9Unhxgjhk1z4wgE5b7Eof25dJ7G3t9r10cgFExNFv9TpNwszzkAgspF3njTMP3PXCy+frYHjzD1zOdAH1X870AdUuZ75QjddueeS16SVDLxAd0cIBxKlzxvP9rBUongFdPqO1EPQAxYNMvMjYrm3UCxRMeeR2baNuICk/qp8PhJN7gEgOx/F44OPJnTabQh9Q7I/ysz/oWz4Rjx1AUR4Pye64vkTsA8ry2KI84h/K1tANVDMp3VH5/x3p5Si+mTQDFUFxkKLhhiQQgAvGeIyjJKg5WcvJFmTRYNP0uYUIjjCDRxdBBmK3keMYxPiCL2TYORE4pwkkEKkqgCAZ+0jdUU6apokJAuZkBZQznAG505sGAaUBN1ERphaBH34CsXAxLrWj708nN83gDC43jiLgdUYlE51hemgfEMpYfvFTpQuYHxZoycyRMvp/lqoMPzEAsK/N9Q91tOiXBJ/+SvnF/olvSAAAAABJRU5ErkJggg=="
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
except Exception as e:
    red_food_frames = None

# Scene 상태 정의
TITLE, GAME, SUCCESS, FAILURE = 0, 1, 2, 3
scene = TITLE

# 폰트 설정
font = pygame.font.SysFont("malgungothic", 25)
big_font = pygame.font.SysFont("malgungothic", 50, bold=True)
small_font = pygame.font.SysFont("malgungothic", 18)

class FloatingText:
    def __init__(self, x, y, text, color):
        self.x, self.y = x, y
        self.text, self.color = text, color
        self.alpha, self.life = 255, 60
    def update(self):
        self.y -= 1
        self.alpha -= 4
        self.life -= 1
    def draw(self, surface, offset=(0, 0)):
        if self.life > 0:
            text_surf = small_font.render(self.text, True, self.color)
            text_surf.set_alpha(max(0, self.alpha))
            surface.blit(text_surf, (self.x + offset[0], self.y + offset[1]))

class Snake:
    def __init__(self):
        self.reset()
    def reset(self):
        self.x = -200
        self.y = HEIGHT // 2
        self.angle = 0 
        self.base_speed = 2.5
        self.max_speed = 8.0
        self.current_speed = self.base_speed
        self.turn_speed = 0.11
        self.radius = 10
        self.length = 600 
        self.body = []
        for i in range(int(self.length)):
            self.body.append((self.x - i, self.y))
        self.is_entering = True
        self.is_ghost = False      
        self.ghost_timer = 0        
        self.cooldown_timer = 0
        self.yoyo_timer = 0
        self.yoyo_max = 420 
        
    def update(self):
        speed_progress = (600 - self.length) / 590
        self.current_speed = self.base_speed + (speed_progress * (self.max_speed - self.base_speed))
        
        keys = pygame.key.get_pressed()
        if keys[pygame.K_a]: self.angle -= self.turn_speed
        if keys[pygame.K_d]: self.angle += self.turn_speed
        
        if keys[pygame.K_SPACE] and self.cooldown_timer <= 0:
            self.is_ghost = True
            self.ghost_timer = 150   
            self.cooldown_timer = 1080
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
        for i, segment in enumerate(self.body):
            if i > 30:
                if math.hypot(self.x - segment[0], self.y - segment[1]) < self.radius * 0.7:
                    return True
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
                ex = self.x + math.cos(eye_angle) * (self.radius * 0.6) + offset[0]
                ey = self.y + math.sin(eye_angle) * (self.radius * 0.6) + offset[1]
                
                if is_dead:
                    size = 4
                    pygame.draw.line(surface, EYE_COLOR, (ex-size, ey-size), (ex+size, ey+size), 2)
                    pygame.draw.line(surface, EYE_COLOR, (ex+size, ey-size), (ex-size, ey+size), 2)
                else:
                    pygame.draw.circle(surface, EYE_COLOR, (int(ex), int(ey)), 2)

class Food:
    def __init__(self, color, value):
        self.color, self.value = color, value
        self.active = (value != 30)
        self.max_timer = 300  # 보라 아이템과 벌레(RED) 공통 300 프레임
        self.timer = self.max_timer
        
        # 애니메이션 속성
        self.frame_index = 0
        self.anim_timer = pygame.time.get_ticks()
        self.anim_delay = 150 # ms
        
        self.respawn()
        
    def respawn(self):
        self.x, self.y = random.randint(50, WIDTH - 50), random.randint(50, HEIGHT - 50)
        if self.value == 30 or self.color == RED: 
            self.timer = self.max_timer
            
    def update(self):
        # 벌레(RED)일 경우 타이머 감소 및 랜던 스폰 처리
        if self.color == RED:
            self.timer -= 1
            if self.timer <= 0:
                self.respawn()
        
    def draw(self, surface, offset=(0, 0)):
        if self.active:
            if self.color == RED and red_food_frames:
                now = pygame.time.get_ticks()
                if now - self.anim_timer >= self.anim_delay:
                    self.frame_index = (self.frame_index + 1) % len(red_food_frames)
                    self.anim_timer = now
                
                img = red_food_frames[self.frame_index]
                img_w, img_h = img.get_size()
                surface.blit(img, (self.x - img_w//2 + offset[0], self.y - img_h//2 + offset[1]))
            
            else:
                r = 7 if self.value == 30 else 8
                pygame.draw.circle(surface, self.color, (self.x + offset[0], self.y + offset[1]), r)
                pygame.draw.circle(surface, WHITE, (self.x + offset[0], self.y + offset[1]), r, 1) 
                
                if self.value == 30 and self.timer > 0:
                    bar_width = 30
                    bar_height = 4
                    pygame.draw.rect(surface, (50, 50, 50), (self.x - bar_width//2 + offset[0], self.y - 15 + offset[1], bar_width, bar_height))
                    current_bar_w = (self.timer / self.max_timer) * bar_width
                    pygame.draw.rect(surface, PURPLE_ITEM, (self.x - bar_width//2 + offset[0], self.y - 15 + offset[1], current_bar_w, bar_height))

def draw_exit(surface, frame_count, offset=(0, 0)):
    cx, cy = WIDTH // 2 + offset[0], HEIGHT // 2 + offset[1]
    for r in range(5, 35, 4):
        pulse_r = r + (frame_count % 15) / 3
        alpha = max(0, 200 - (pulse_r / 35) * 200)
        s = pygame.Surface((pulse_r * 2, pulse_r * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*EXIT_COLOR, int(alpha)), (pulse_r, pulse_r), pulse_r, 2)
        surface.blit(s, (cx - pulse_r, cy - pulse_r))
    pygame.draw.circle(surface, WHITE, (cx, cy), 4)

# 초기화
snake = Snake()
foods = [Food(WHITE, 5), Food(YELLOW, 15), Food(RED, -20)]
purple_food = Food(PURPLE_ITEM, 30)
floating_texts, score = [], 0
purple_count, frame_count, can_exit = 0, 0, False

running = True
while running:
    render_offset = [0, 0]
    if shake_timer > 0:
        render_offset[0] = random.randint(-shake_amount, shake_amount)
        render_offset[1] = random.randint(-shake_amount, shake_amount)
        shake_timer -= 1

    screen.fill(DESERT_COLOR)
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE: running = False
            if scene == TITLE and event.key == pygame.K_q: scene = GAME
            elif (scene == SUCCESS or scene == FAILURE) and event.key == pygame.K_r:
                snake.reset(); score = 0; purple_count = 0; can_exit = False
                purple_food.active = False; floating_texts = []; scene = GAME; shake_timer = 0

    if scene == TITLE:
        title_txt = big_font.render("DESERT DIET MISSION", True, BLACK)
        screen.blit(title_txt, (WIDTH//2 - title_txt.get_width()//2, HEIGHT//2 - 180))
        controls = [
            "A, D - 방향 전환  /  Space - 유령 모드", 
            "벌레(동물)를 피하세요! (Score -20 & 길이 대폭 증가)", 
            "게임 오버 기준 점수: -40 미만", 
            "R - Restart  /  Esc - Quit"
        ]
        for i, txt in enumerate(controls):
            ctrl_surf = font.render(txt, True, BLACK)
            screen.blit(ctrl_surf, (WIDTH//2 - ctrl_surf.get_width()//2, HEIGHT//2 - 40 + i*35))
        start_txt = big_font.render("[ Q - Start Game ]", True, (150, 50, 0))
        screen.blit(start_txt, (WIDTH//2 - start_txt.get_width()//2, HEIGHT - 100))

    elif scene in [GAME, FAILURE, SUCCESS]:
        if scene == GAME:
            snake.update()
            
            # --- 벌레(RED) 동적 생성 및 타이머 업데이트 로직 ---
            expected_bugs = 1
            if score >= 500: expected_bugs = 5
            elif score >= 400: expected_bugs = 4
            elif score >= 300: expected_bugs = 3
            elif score >= 200: expected_bugs = 2
            
            red_foods = [f for f in foods if f.color == RED]
            # 벌레가 부족하면 추가
            while len(red_foods) < expected_bugs:
                new_bug = Food(RED, -20)
                foods.append(new_bug)
                red_foods.append(new_bug)
            # 벌레가 많으면 제거 (점수 하락 시 대비)
            while len(red_foods) > expected_bugs:
                bug_to_remove = red_foods.pop()
                foods.remove(bug_to_remove)
                
            # 먹이 상태 업데이트 (벌레 타이머 감소용)
            for f in foods:
                f.update()
            # --------------------------------------------------
            
            if snake.yoyo_timer >= snake.yoyo_max:
                score -= 20; snake.length += 50; snake.yoyo_timer = 0
                floating_texts.append(FloatingText(snake.x, snake.y - 20, "-20 (YOYO!)", RED))
                if score < -40: scene = FAILURE; shake_timer = 40

            if purple_food.active:
                purple_food.timer -= 1
                if purple_food.timer <= 0: purple_food.active = False
                
            for f in foods + ([purple_food] if purple_food.active else []):
                if math.hypot(snake.x - f.x, snake.y - f.y) < snake.radius + 8:
                    if f.color == RED:
                        if minus_eat_sound: minus_eat_sound.play()
                        score += f.value
                        snake.length += 50
                        shake_timer = 15
                    else:
                        if eat_sound: eat_sound.play()
                        score += f.value
                        snake.length = max(10, snake.length - (f.value * 1.8))
                    
                    if snake.cooldown_timer > 0:
                        snake.cooldown_timer = max(0, snake.cooldown_timer - 60)
                    snake.yoyo_timer = 0 
                    
                    f_text = f"{f.value} Pts"
                    f_color = RED if f.value < 0 else (YELLOW if f.value >= 15 else WHITE)
                    floating_texts.append(FloatingText(f.x, f.y, f_text, f_color))
                    
                    if f == purple_food: purple_food.active = False
                    else:
                        f.respawn()
                        if not purple_food.active and random.random() < 0.15:
                            purple_food.respawn(); purple_food.active = True
            
            if score >= 600:
                can_exit = True
                if math.hypot(snake.x - WIDTH//2, snake.y - HEIGHT//2) < 20: scene = SUCCESS
                
            if snake.check_self_collision(): scene = FAILURE; shake_timer = 40
            if score < -40: scene = FAILURE; shake_timer = 40
            if not snake.is_entering: snake.x %= WIDTH; snake.y %= HEIGHT

        if can_exit: draw_exit(screen, frame_count, render_offset)
        snake.draw(screen, render_offset, is_dead=(scene == FAILURE))
        for f in foods: f.draw(screen, render_offset)
        if purple_food.active: purple_food.draw(screen, render_offset)
        for ft in floating_texts[:]:
            ft.update(); ft.draw(screen, render_offset) if ft.life > 0 else floating_texts.remove(ft)
        
        screen.blit(font.render(f"Score: {score}", True, BLACK), (20 + render_offset[0], 20 + render_offset[1]))
        
        bar_w, bar_h, text_m = 150, 12, 25
        y_x, y_y = WIDTH - bar_w - 20, 40
        pygame.draw.rect(screen, (50, 50, 50), (y_x + render_offset[0], y_y + render_offset[1], bar_w, bar_h))
        y_ratio = min(1.0, snake.yoyo_timer / snake.yoyo_max)
        pygame.draw.rect(screen, RED if y_ratio > 0.7 else YELLOW, (y_x + render_offset[0], y_y + render_offset[1], bar_w * y_ratio, bar_h))
        screen.blit(small_font.render("YOYO GAUGE", True, BLACK), (y_x + render_offset[0], y_y - text_m + render_offset[1]))

        g_x = y_x - bar_w - 40
        pygame.draw.rect(screen, (50, 50, 50), (g_x + render_offset[0], y_y + render_offset[1], bar_w, bar_h))
        g_ratio = 1 - (snake.cooldown_timer / 1080)
        pygame.draw.rect(screen, BLUE_GHOST, (g_x + render_offset[0], y_y + render_offset[1], bar_w * g_ratio, bar_h))
        g_cd = math.ceil(snake.cooldown_timer / 60)
        g_label = f"GHOST: {g_cd}s" if g_cd > 0 else "GHOST: READY"
        screen.blit(small_font.render(g_label, True, BLACK), (g_x + render_offset[0], y_y - text_m + render_offset[1]))

        if scene == SUCCESS or scene == FAILURE:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 80))
            screen.blit(overlay, (0, 0))
            txt = "DIET COMPLETE" if scene == SUCCESS else "Game Over"
            msg = big_font.render(txt, True, (0, 100, 0) if scene == SUCCESS else RED)
            screen.blit(msg, (WIDTH//2 - msg.get_width()//2 + render_offset[0], HEIGHT//2 - 80 + render_offset[1]))
            if scene == FAILURE:
                score_txt = font.render(f"Final Score: {score}", True, WHITE)
                screen.blit(score_txt, (WIDTH//2 - score_txt.get_width()//2, HEIGHT//2))
            screen.blit(font.render("[ R - Play Again ]", True, WHITE), (WIDTH//2 - 100, HEIGHT//2 + 80))

    frame_count += 1
    pygame.display.flip()
    clock.tick(60)
pygame.quit()