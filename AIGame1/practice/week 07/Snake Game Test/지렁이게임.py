import pygame

import math

import random

import os



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



# --- [에셋 로드] ---

try:

    background_img = pygame.image.load("./assets/images/background.jpg").convert()

    background_img = pygame.transform.scale(background_img, (WIDTH, HEIGHT))

except:

    background_img = None



try:

    eat_sound = pygame.mixer.Sound("./assets/sounds/eat.mp3")

except:

    eat_sound = None



try:

    pygame.mixer.music.load("./assets/sounds/bgm.wav")

    pygame.mixer.music.set_volume(0.5)

    pygame.mixer.music.play(-1)

except:

    pass



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

    def draw(self, surface):

        if self.life > 0:

            text_surf = small_font.render(self.text, True, self.color)

            text_surf.set_alpha(max(0, self.alpha))

            surface.blit(text_surf, (self.x, self.y))



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



    def draw(self, surface):

        body_count = len(self.body)

        for i, segment in enumerate(self.body):

            if segment[0] < -self.radius or segment[0] > WIDTH + self.radius: continue

            ratio = i / body_count if body_count > 1 else 0

            current_color = BLUE_GHOST if self.is_ghost else (

                int(PASTEL_PURPLE_HEAD[0]*(1-ratio)+PASTEL_PURPLE_TAIL[0]*ratio),

                int(PASTEL_PURPLE_HEAD[1]*(1-ratio)+PASTEL_PURPLE_TAIL[1]*ratio),

                int(PASTEL_PURPLE_HEAD[2]*(1-ratio)+PASTEL_PURPLE_TAIL[2]*ratio)

            )

            # 깔끔하게 단색 원으로 복구

            seg_rad = int(self.radius if i > 0 else self.radius+2)

            pygame.draw.circle(surface, current_color, (int(segment[0]), int(segment[1])), seg_rad)

        

        if self.x > -self.radius:

            for side in [-1, 1]:

                eye_angle = self.angle + (side * math.pi / 4)

                ex = self.x + math.cos(eye_angle) * (self.radius * 0.6)

                ey = self.y + math.sin(eye_angle) * (self.radius * 0.6)

                pygame.draw.circle(surface, EYE_COLOR, (int(ex), int(ey)), 2)



class Food:

    def __init__(self, color, value):

        self.color, self.value = color, value

        self.active = (value != 30)

        self.timer = 0

        self.max_timer = 300

        self.respawn()

    def respawn(self):

        self.x, self.y = random.randint(50, WIDTH - 50), random.randint(50, HEIGHT - 50)

        if self.value == 30: self.timer = self.max_timer

    def draw(self, surface):

        if self.active:

            r = 7 if self.value == 30 else 8

            pygame.draw.circle(surface, self.color, (self.x, self.y), r)

            pygame.draw.circle(surface, WHITE, (self.x, self.y), r, 1) 

            

            if self.value == 30 and self.timer > 0:

                bar_width = 30

                bar_height = 4

                pygame.draw.rect(surface, (50, 50, 50), (self.x - bar_width//2, self.y - 15, bar_width, bar_height))

                current_bar_w = (self.timer / self.max_timer) * bar_width

                pygame.draw.rect(surface, PURPLE_ITEM, (self.x - bar_width//2, self.y - 15, current_bar_w, bar_height))



def draw_exit(surface, frame_count):

    cx, cy = WIDTH // 2, HEIGHT // 2

    for r in range(5, 35, 4):

        pulse_r = r + (frame_count % 15) / 3

        alpha = max(0, 200 - (pulse_r / 35) * 200)

        s = pygame.Surface((pulse_r * 2, pulse_r * 2), pygame.SRCALPHA)

        pygame.draw.circle(s, (*EXIT_COLOR, int(alpha)), (pulse_r, pulse_r), pulse_r, 2)

        surface.blit(s, (cx - pulse_r, cy - pulse_r))

    pygame.draw.circle(surface, WHITE, (cx, cy), 4)



# 초기화

snake = Snake()

foods = [Food(WHITE, 5), Food(YELLOW, 15)]

purple_food = Food(PURPLE_ITEM, 30)

floating_texts, score = [], 0

purple_count, frame_count, can_exit = 0, 0, False



running = True

while running:

    if background_img:

        screen.blit(background_img, (0, 0))

    else:

        screen.fill(BLACK)

    

    for event in pygame.event.get():

        if event.type == pygame.QUIT: running = False

        if event.type == pygame.KEYDOWN:

            if event.key == pygame.K_ESCAPE: running = False

            if scene == TITLE and event.key == pygame.K_q: scene = GAME

            elif (scene == SUCCESS or scene == FAILURE) and event.key == pygame.K_r:

                snake.reset(); score = 0; purple_count = 0; can_exit = False

                purple_food.active = False; floating_texts = []; scene = GAME



    if scene == TITLE:

        title_txt = big_font.render("DESERT DIET MISSION", True, WHITE)

        screen.blit(title_txt, (WIDTH//2 - title_txt.get_width()//2, HEIGHT//2 - 180))

        controls = [

            "Controls: A, D - Turn", 

            "Space - Ghost Mode (High Risk!)", 

            "주의: 유령 모드 사용 시 요요 게이지 35% 즉시 상승!", 

            "팁: 쿨타임 중 먹이를 먹으면 유령 모드 대기시간 1초 감소!",

            "R - Restart", "Esc - Quit"

        ]

        for i, txt in enumerate(controls):

            ctrl_surf = font.render(txt, True, WHITE)

            screen.blit(ctrl_surf, (WIDTH//2 - ctrl_surf.get_width()//2, HEIGHT//2 - 40 + i*35))

        start_txt = big_font.render("[ Q - Start Game ]", True, YELLOW)

        screen.blit(start_txt, (WIDTH//2 - start_txt.get_width()//2, HEIGHT - 100))



    elif scene == GAME:

        snake.update()

        if snake.yoyo_timer >= snake.yoyo_max:

            score -= 20; snake.length += 50; snake.yoyo_timer = 0

            floating_texts.append(FloatingText(snake.x, snake.y - 20, "-20 (YOYO!)", RED))

            if score < 0: scene = FAILURE



        if purple_food.active:

            purple_food.timer -= 1

            if purple_food.timer <= 0: purple_food.active = False

            

        for f in foods + ([purple_food] if purple_food.active else []):

            if math.hypot(snake.x - f.x, snake.y - f.y) < snake.radius + 8:

                if eat_sound: eat_sound.play()

                score += f.value

                snake.length = max(10, snake.length - (f.value * 1.8))

                if snake.cooldown_timer > 0:

                    snake.cooldown_timer = max(0, snake.cooldown_timer - 60)

                snake.yoyo_timer = 0 

                floating_texts.append(FloatingText(f.x, f.y, f"+{f.value} Pts", YELLOW if f.value >= 15 else WHITE))

                if f == purple_food: purple_food.active = False

                else:

                    f.respawn()

                    if not purple_food.active and random.random() < 0.15:

                        purple_food.respawn(); purple_food.active = True

        

        if score >= 600:

            can_exit = True

            if math.hypot(snake.x - WIDTH//2, snake.y - HEIGHT//2) < 20: scene = SUCCESS

            

        if snake.check_self_collision(): scene = FAILURE

        if not snake.is_entering: snake.x %= WIDTH; snake.y %= HEIGHT

        if can_exit: draw_exit(screen, frame_count)

        

        snake.draw(screen)

        for f in foods: f.draw(screen)

        if purple_food.active: purple_food.draw(screen)

        for ft in floating_texts[:]:

            ft.update(); ft.draw(screen) if ft.life > 0 else floating_texts.remove(ft)

        

        screen.blit(font.render(f"Score: {score}", True, WHITE), (20, 20))

        

        bar_w, bar_h, text_m = 150, 12, 25

        y_x, y_y = WIDTH - bar_w - 20, 40

        pygame.draw.rect(screen, (50, 50, 50), (y_x, y_y, bar_w, bar_h))

        y_ratio = min(1.0, snake.yoyo_timer / snake.yoyo_max)

        pygame.draw.rect(screen, RED if y_ratio > 0.7 else YELLOW, (y_x, y_y, bar_w * y_ratio, bar_h))

        screen.blit(small_font.render("YOYO GAUGE", True, WHITE), (y_x, y_y - text_m))



        g_x = y_x - bar_w - 40

        pygame.draw.rect(screen, (50, 50, 50), (g_x, y_y, bar_w, bar_h))

        g_ratio = 1 - (snake.cooldown_timer / 1080)

        pygame.draw.rect(screen, BLUE_GHOST, (g_x, y_y, bar_w * g_ratio, bar_h))

        g_cd = math.ceil(snake.cooldown_timer / 60)

        g_label = f"GHOST: {g_cd}s" if g_cd > 0 else "GHOST: READY"

        screen.blit(small_font.render(g_label, True, WHITE), (g_x, y_y - text_m))



    elif scene == SUCCESS or scene == FAILURE:

        txt = "DIET COMPLETE" if scene == SUCCESS else "Game Over"

        msg = big_font.render(txt, True, YELLOW if scene == SUCCESS else RED)

        screen.blit(msg, (WIDTH//2 - msg.get_width()//2, HEIGHT//2 - 80))

        if scene == FAILURE:

            score_txt = font.render(f"Final Score: {score}", True, WHITE)

            screen.blit(score_txt, (WIDTH//2 - score_txt.get_width()//2, HEIGHT//2))

        screen.blit(font.render("[ R - Play Again ]", True, WHITE), (WIDTH//2 - 100, HEIGHT//2 + 80))



    frame_count += 1

    pygame.display.flip()

    clock.tick(60)

pygame.quit()
