import pygame
import math
import random
import os
import base64
import io
from dataclasses import dataclass, field
from typing import List, Optional, Set
import abc

# ══════════════════════════════════════════════════════════════
#  1. 초기 설정
# ══════════════════════════════════════════════════════════════
pygame.init()
pygame.mixer.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Snake Mission: Desert Diet")
clock = pygame.time.Clock()

# ── 색상 ──
BLACK           = (20,  20,  20)
WHITE           = (255, 255, 255)
YELLOW          = (255, 255, 0)
ORANGE_ITEM     = (255, 165, 0)
BLUE_GHOST      = (160, 210, 255)
PASTEL_HEAD     = (190, 90,  40)
PASTEL_TAIL     = (225, 180, 95)
EYE_COLOR       = (0,   0,   0)
RED             = (255, 80,  80)
EXIT_COLOR      = (100, 255, 100)
DESERT_COLOR    = (210, 180, 140)
STAR_COLOR      = (255, 220, 50)

# ── 폰트 ──
try:
    font_en_big   = pygame.font.Font("./assets/fonts/AGENCYB.TTF", 50)
    font_en_mid   = pygame.font.Font("./assets/fonts/AGENCYB.TTF", 28)
    font_en_small = pygame.font.Font("./assets/fonts/AGENCYB.TTF", 18)
    font_ko_mid   = pygame.font.Font("./assets/fonts/gmar.TTF", 22)
    font_ko_small = pygame.font.Font("./assets/fonts/gmar.TTF", 16)
except Exception:
    font_en_big   = pygame.font.SysFont("arial",        50, bold=True)
    font_en_mid   = pygame.font.SysFont("arial",        28, bold=True)
    font_en_small = pygame.font.SysFont("arial",        18)
    font_ko_mid   = pygame.font.SysFont("malgungothic", 22)
    font_ko_small = pygame.font.SysFont("malgungothic", 16)

# ── 사운드 ──
def _load_sound(path):
    try:
        return pygame.mixer.Sound(path)
    except Exception:
        return None

eat_sound         = _load_sound("./assets/sounds/eat.mp3")
minus_eat_sound   = _load_sound("./assets/sounds/minus eat.mp3")
die_sound         = _load_sound("./assets/sounds/die.mp3")
complete_sound    = _load_sound("./assets/sounds/Completed.wav")
choice_sound      = _load_sound("./assets/sounds/choice.wav")
lulu_sound        = _load_sound("./assets/sounds/lulu.wav")
warning_sound     = _load_sound("./assets/sounds/warning.mp3")
portal_open_sound = _load_sound("./assets/sounds/potalopen.wav")
portal_seal_sound = _load_sound("./assets/sounds/potalsealed.wav")
ghost_sound       = _load_sound("./assets/sounds/Ghost.mp3")
star_sound        = _load_sound("./assets/sounds/Star.mp3")
star_on_sound     = _load_sound("./assets/sounds/Star_on.wav")
combo_sounds: list = []
for _i in range(1, 8):
    _s = _load_sound(f"./assets/sounds/combo/combo{_i}.mp3")
    if _s:
        combo_sounds.append(_s)

try:
    pygame.mixer.music.load("./assets/sounds/bgm.wav")
    pygame.mixer.music.set_volume(0.5)
    pygame.mixer.music.play(-1)
except Exception:
    pass

# ── 이미지 로드 ──
def _load_img(path, size=None):
    try:
        img = pygame.image.load(path).convert_alpha()
        if size:
            img = pygame.transform.scale(img, size)
        return img
    except Exception:
        return None

green_food_img  = _load_img("./assets/images/green.png",  (22, 22))
yellow_food_img = _load_img("./assets/images/yellow.png", (26, 26))
orange_food_img = _load_img("./assets/images/orange.png", (24, 24))

try:
    sand1 = pygame.image.load("./assets/images/sand1.png").convert_alpha()
    sand2 = pygame.image.load("./assets/images/sand2.png").convert_alpha()
    sand3 = pygame.image.load("./assets/images/sand3.png").convert_alpha()
    BARRIER_HEIGHT = sand1.get_height()
    sand_variants  = [sand2, sand3]
except Exception:
    sand1 = pygame.Surface((40, 40)); sand1.fill((139, 69, 19))
    sand2 = sand1; sand3 = sand1
    BARRIER_HEIGHT = 40
    sand_variants  = [sand1]

# ── 스프라이트 시트 ──
SHEET_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAGAAAABgCAMAAADVRocKAAAABGdBTUEAALGPC/xhBQAAADNQTFRFAAAAxKju"
    "/96M7JoeYWu6nfjkiG2vo4bOY7ime9jExHxx36mI882s/7hMd4/bRzJL////Ur3JYAAAAAF0Uk5TAEDm2GY"
    "AAAQxSURBVGje7VmJcuMgDE1r11dio///2iIEWBIihh4zu52w6XhWhveEDhD4dnu1V/vDDULDx2/iR5YfgS"
    "vgnW/46GOwe2s9E35i6JRZ6EvzqG1J0EjjLGlLPqP6Hb3EWXV4T/U9HMmLSf0GCZW0kABOJxIWpUbR4bN"
    "/8o4mAAwmk6EppiZIArvEZjkQK3hQEofeyEsG6OKcDIEaKsAQHkgRe6H2Jr04CxwkWOUI2ptIJ5IBDeUeG"
    "3ykOEyDVkQdOL4DID2Bix4EyFEQCNPUHFyNBsuiyZAIoTA1sygmITTmm0/KB5lBi0kP4H7KlC6eFKScgWD"
    "jSsgbideXiHHAREiKBk/nhpE0jkJgyEqxJLk1dOjP5hghY/2yK8FPMlvzGQUWwBIIQXZ7L/dZO8af311vH"
    "Dti1X9oJ3jqkqXPObrlSVJmBZRvcetZSuVJUGdiQFgLfbZ6p+zTpzC+Z4xg/BHu3EczYEH7KY0p8tZD/BA"
    "FK31A+sxdfJXibPcpcEvgXhK8JPPM0d/ggATltou3xeNwtE725eerZkTMQCCffg3zbVACjUm5qC1TqLoDODe"
    "p+3+6+bfhC4iuFniQg4ZdAAd9z4psNuNxUqMgdQWADIW8g3jSxOTOROyota0BeGPzDPa0pVBRqPCRqQFYi"
    "1xVKawILxudAkAoQp8ulqkIs3AvLaaDaMv5sZj6fgvOnqQFIv7hdKEQE19EFX92g6tH1rSOmisYUXd8jqK9"
    "qKbq8/1910av9E7Um/Ad3OTYO8NMZfGfKFU3FYbK3VoYGTWPZ5eS20lb+ltWA8SIu/G5qq+yugEpN2dbYTl"
    "ADsjQNMx4G+iucYEZFDcjWNMj39/d935UToF4Y2UC2pijeiWDXA8R1SAuQpSkRUHPlZZ5dGNWBCk0DjhcC"
    "/oqS2BF5UYxbU65oSvr4NgxCoyCfpgF7lyPsKUtNmXjYywEonymDsOsZGECZmDR9Unhxgjhk1z4wgE5b7Io"
    "f25dJ7G3t9r10cgFExNFv9TpNwszzkAgspF3njTMP3PXCy+frYHjzD1zOdAH1X870AdUuZ75QjddueeS16SV"
    "DLxAd0cIBxKlzxvP9rBUongFdPqO1EPQAxYNMvMjYrm3UCxRMeeR2baNuICk/qp8PhJN7gEgOx/F44OPJHW"
    "abQh9Q7I/ysz/oWz4Rjx1AUR4Pye64vkTsA8ry2KI84h/K1tANVDMp3VH5/x3p5Si+mTQDFUFxkKLhhiQQ"
    "gAvGeIyjJKg5WcvJFmTRYNP0uYUIjjCDRxdBBmK3keMYxPiCL2TYORE4pwkkEKkqgCAZ+0jdUU6apokJAuZ"
    "kBZQznAG505sGAaUBN1ERphaBH34CsXAxLrWj708nN83gDC43jiLgdUYlE51hemgfEMpYfvFTpQuYHxZoycyR"
    "Mvp/lqoMPzEAsK/N9Q91tOiXBJ/+SvnF/olvSAAAAABJRU5ErkJggg=="
)
try:
    try:
        player_sheet = pygame.image.load("./assets/images/animal.png").convert_alpha()
    except Exception:
        sheet_bytes  = base64.b64decode(SHEET_B64)
        player_sheet = pygame.image.load(io.BytesIO(sheet_bytes)).convert_alpha()
    player_frames = []
    for _i in range(16):
        _r, _c = divmod(_i, 4)
        player_frames.append(player_sheet.subsurface(pygame.Rect(_c * 24, _r * 24, 24, 24)))
    red_food_frames    = [player_frames[i] for i in [0, 1, 2]]
    animal_walk_frames = [player_frames[i] for i in [8, 9, 10]]
except Exception:
    red_food_frames    = None
    animal_walk_frames = None


# ══════════════════════════════════════════════════════════════
#  2. 스테이지 정의
# ══════════════════════════════════════════════════════════════
@dataclass
class StageConfig:
    """스테이지별 설정값"""
    stage_num:        int
    goal_score:       int
    label:            str          # 화면 표시용
    obstacle_density: float        # 장애물 밀도 배율 (1.0 = 기본)
    speed_mult:       float        # 기본 속도 배율
    yoyo_max:         int          # 요요 게이지 최대치
    red_food_base:    int          # 초기 빨간 먹이 수
    purple_chance:    float        # 주황 먹이 등장 확률
    hint:             str          # 스테이지 설명

STAGES: list = [
    StageConfig(1, 300,  "STAGE 1  –  Dunes",
                1.0, 1.0, 420, 1, 0.15,
                "기본 사막. 목표: 300점"),
    StageConfig(2, 500,  "STAGE 2  –  Rock Maze",
                1.5, 1.15, 360, 2, 0.20,
                "장애물 밀집! 목표: 500점"),
    StageConfig(3, 700,  "STAGE 3  –  Sandstorm",
                2.0, 1.30, 300, 3, 0.25,
                "빠른 속도와 잦은 지렁이! 목표: 700점"),
]


# ══════════════════════════════════════════════════════════════
#  3. GameState 데이터클래스  (전역 변수 대체)
# ══════════════════════════════════════════════════════════════
@dataclass
class GameState:
    # ── 점수 / 진행 ──
    score:            int   = 0
    stage_idx:        int   = 0      # 현재 스테이지 인덱스
    can_exit:         bool  = False
    frame_count:      int   = 0

    # ── 콤보 ──
    combo_count:      int   = 0
    combo_timer:      int   = 0
    red_streak:       int   = 0

    # ── 세션 기록 ──
    session_high:     int   = 0
    foods_eaten:      int   = 0
    reds_eaten:       int   = 0
    ghost_uses:       int   = 0

    # ── 연출 타이머 ──
    shake_timer:      int   = 0
    shake_amount:     int   = 3
    screen_flash:     int   = 0
    suck_timer:       int   = 0
    milestone_flash:  int   = 0
    milestone_color:  tuple = (255, 220, 60)
    lulu_timer:       int   = 0

    # ── 포탈 사이클 ──
    exit_is_open:     bool  = False
    exit_cycle_timer: int   = 0
    exit_announced:   bool  = False

    # ── 별 마일스톤 ──
    milestones_done:  Set[int]    = field(default_factory=set)
    max_score:        int         = 0

    # ── 요요 경고 중복 방지 ──
    yoyo_warned:      bool  = False

    # ── 스폰 ──
    last_spawn_tier:  int   = -1

    # ── 일시정지 ──
    is_paused:        bool  = False

    # ── 루프 제어 ──
    played_end_sound: bool  = False

    # ── 렌더 오프셋 ──
    render_offset:    list  = field(default_factory=lambda: [0, 0])

    @property
    def stage(self) -> StageConfig:
        return STAGES[self.stage_idx]

    def reset_for_stage(self, stage_idx: int, keep_session: bool = True):
        hi = self.session_high
        self.__init__()
        self.stage_idx = stage_idx
        if keep_session:
            self.session_high = hi

    EXIT_OPEN_DURATION  = 300
    EXIT_CLOSE_DURATION = 300
    COMBO_WINDOW        = 150


# ══════════════════════════════════════════════════════════════
#  4. 게임 오브젝트 클래스
# ══════════════════════════════════════════════════════════════

# ── 파티클 ──
class Particle:
    def __init__(self, x: float, y: float, color: tuple):
        self.x, self.y = float(x), float(y)
        self.color = tuple(color[:3])
        angle  = random.uniform(0, math.pi * 2)
        speed  = random.uniform(1.5, 4.2)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed - 1.8
        self.life = self.max_life = random.randint(22, 42)
        self.radius = random.randint(2, 5)

    def update(self):
        self.x  += self.vx
        self.y  += self.vy
        self.vy += 0.18
        self.vx *= 0.97
        self.life -= 1

    def draw(self, surface, offset=(0, 0)):
        if self.life <= 0:
            return
        alpha = int(255 * self.life / self.max_life)
        s = pygame.Surface((self.radius * 2 + 1, self.radius * 2 + 1), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, alpha), (self.radius, self.radius), self.radius)
        surface.blit(s, (int(self.x - self.radius + offset[0]),
                         int(self.y - self.radius + offset[1])))


# ── 별 먹이 ──
class StarFood:
    MAX_TIMER = 480

    def __init__(self, obstacles: list):
        self.obstacles = obstacles
        self.active = False
        self.x = self.y = 0
        self.timer = 0
        self.pulse  = 0.0

    def spawn(self):
        for _ in range(100):
            x = random.randint(60, WIDTH - 60)
            y = random.randint(BARRIER_HEIGHT + 30, HEIGHT - BARRIER_HEIGHT - 30)
            rect = pygame.Rect(x - 15, y - 15, 30, 30)
            if not any(o['rect'].colliderect(rect) for o in self.obstacles):
                self.x, self.y = x, y
                break
        self.active = True
        self.timer  = self.MAX_TIMER
        self.pulse  = 0.0

    def update(self):
        if not self.active:
            return
        self.timer -= 1
        self.pulse  = (self.pulse + 0.13) % (math.pi * 2)
        if self.timer <= 0:
            self.active = False

    def draw(self, surface, offset=(0, 0)):
        if not self.active:
            return
        cx = int(self.x + offset[0])
        cy = int(self.y + offset[1])
        r_outer = int(13 + math.sin(self.pulse) * 3)
        r_inner = max(4, r_outer // 2)
        for gr in [r_outer + 10, r_outer + 5]:
            ga = max(0, 55 - (gr - r_outer) * 8)
            gs = pygame.Surface((gr * 2 + 2, gr * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(gs, (255, 240, 80, ga), (gr + 1, gr + 1), gr)
            surface.blit(gs, (cx - gr - 1, cy - gr - 1))
        pts = []
        for k in range(10):
            ang = -math.pi / 2 + k * math.pi / 5
            rad = r_outer if k % 2 == 0 else r_inner
            pts.append((cx + math.cos(ang) * rad, cy + math.sin(ang) * rad))
        pygame.draw.polygon(surface, (255, 230, 60), pts)
        pygame.draw.polygon(surface, (200, 155, 10), pts, 2)
        pygame.draw.rect(surface, (50, 50, 50),     (cx - 20, cy - r_outer - 10, 40, 4))
        pygame.draw.rect(surface, (255, 200, 0),
                         (cx - 20, cy - r_outer - 10,
                          int(40 * self.timer / self.MAX_TIMER), 4))
        lbl = font_en_small.render("+50", True, (255, 255, 180))
        surface.blit(lbl, (cx - lbl.get_width() // 2, cy + r_outer + 3))


# ── 떠다니는 텍스트 ──
class FloatingText:
    def __init__(self, x, y, text, color):
        self.x, self.y, self.text, self.color = x, y, text, color
        self.alpha, self.life = 255, 60

    def update(self):
        self.y     -= 1
        self.alpha -= 4
        self.life  -= 1

    def draw(self, surface, offset=(0, 0)):
        if self.life <= 0:
            return
        s = font_en_small.render(self.text, True, self.color)
        s.set_alpha(max(0, self.alpha))
        surface.blit(s, (self.x + offset[0], self.y + offset[1]))


# ── 루루(특수 동물) ──
class MovingAnimal:
    def __init__(self, obstacles: list):
        self.obstacles = obstacles
        self.x = self.y = 0
        self.angle = 0.0
        self.speed = 1.6
        self.active = False
        self.frame_index = 0
        self.anim_timer  = 0

    def respawn(self):
        for _ in range(200):
            x = random.randint(50, WIDTH - 50)
            y = random.randint(BARRIER_HEIGHT + 20, HEIGHT - BARRIER_HEIGHT - 20)
            rect = pygame.Rect(x - 16, y - 16, 32, 32)
            if not any(o['rect'].colliderect(rect) for o in self.obstacles):
                self.x, self.y = x, y
                self.angle = random.uniform(0, math.pi * 2)
                return
        self.x, self.y = WIDTH // 2, HEIGHT // 2
        self.angle = 0

    def update(self):
        if not self.active:
            return
        self.x += math.cos(self.angle) * self.speed
        self.y += math.sin(self.angle) * self.speed
        if random.random() < 0.02:
            self.angle += random.uniform(-0.5, 0.5)
        rect = pygame.Rect(self.x - 16, self.y - 16, 32, 32)
        wall = (rect.top < BARRIER_HEIGHT or rect.bottom > HEIGHT - BARRIER_HEIGHT or
                rect.left < 0 or rect.right > WIDTH or
                any(o['rect'].colliderect(rect) for o in self.obstacles))
        if wall:
            self.angle = (self.angle + math.pi) % (math.pi * 2)
        self.x %= WIDTH
        self.y %= HEIGHT
        self.anim_timer += 1
        if self.anim_timer >= 10:
            self.frame_index = (self.frame_index + 1) % len(animal_walk_frames)
            self.anim_timer  = 0

    def draw(self, surface, offset=(0, 0)):
        if self.active and animal_walk_frames:
            img = pygame.transform.scale(animal_walk_frames[self.frame_index], (32, 32))
            surface.blit(img, (self.x - 16 + offset[0], self.y - 16 + offset[1]))


# ── 뱀 ──
class Snake:
    def __init__(self, stage: StageConfig):
        self.stage = stage
        self.reset()

    def reset(self):
        self.x, self.y     = -200, HEIGHT // 2
        self.angle         = 0.0
        self.base_speed    = 2.5 * self.stage.speed_mult
        self.current_speed = self.base_speed
        self.turn_speed    = 0.11
        self.radius        = 10
        self.length        = 600
        self.body: list    = [(self.x - i, self.y) for i in range(int(self.length))]
        self.is_entering   = True
        self.is_ghost      = False
        self.ghost_timer   = 0
        self.cooldown_timer= 0
        self.yoyo_timer    = 0
        self.yoyo_max      = self.stage.yoyo_max
        self.effect_type: Optional[str] = None
        self.effect_timer  = 0
        self.entry_burst   = False

    def update(self, score: int) -> bool:
        """뱀 업데이트. True 반환 시 entry burst 발동."""
        burst_now = False
        temp_radius = 10
        if self.effect_timer > 0:
            self.effect_timer -= 1
            if self.effect_type == "THICK":
                temp_radius = 18
            elif self.effect_type == "THIN":
                temp_radius = 5
        else:
            self.effect_type = None
        self.radius = temp_radius

        # 점수 기반 속도
        bps = [
            (0,   2.5 * self.stage.speed_mult),
            (150, 3.0 * self.stage.speed_mult),
            (300, 4.5 * self.stage.speed_mult),
            (450, 5.5 * self.stage.speed_mult),
            (500, 6.0 * self.stage.speed_mult),
            (600, 5.5 * self.stage.speed_mult),
        ]
        sc = max(0, score)
        spd = bps[-1][1]
        for i in range(len(bps) - 1):
            s0, v0 = bps[i]; s1, v1 = bps[i + 1]
            if s0 <= sc < s1:
                t = (sc - s0) / (s1 - s0)
                spd = v0 + t * (v1 - v0)
                break
        self.current_speed = spd
        if self.effect_timer > 0:
            if self.effect_type == "FAST":
                self.current_speed = 4.5 * self.stage.speed_mult
            elif self.effect_type == "SLOW":
                self.current_speed = max(0.5, spd - 1.0)

        keys = pygame.key.get_pressed()
        if keys[pygame.K_a]:
            self.angle -= self.turn_speed
        if keys[pygame.K_d]:
            self.angle += self.turn_speed
        if keys[pygame.K_SPACE] and self.cooldown_timer <= 0:
            self.is_ghost    = True
            self.ghost_timer = 150
            self.cooldown_timer = 1080
            self.yoyo_timer = min(self.yoyo_timer + int(self.yoyo_max * 0.35), self.yoyo_max)

        if self.ghost_timer > 0:
            self.ghost_timer -= 1
        else:
            self.is_ghost = False
        if self.cooldown_timer > 0:
            self.cooldown_timer -= 1

        self.yoyo_timer += 1
        self.x += math.cos(self.angle) * self.current_speed
        self.y += math.sin(self.angle) * self.current_speed

        if self.is_entering and self.x > self.radius:
            self.is_entering = False

        if self.x >= 0 and not self.entry_burst:
            self.entry_burst = True
            burst_now = True

        self.body.insert(0, (self.x, self.y))
        if len(self.body) > self.length:
            self.body = self.body[:int(self.length)]

        return burst_now

    def check_self_collision(self) -> bool:
        if self.is_entering or self.is_ghost:
            return False
        for i, seg in enumerate(self.body):
            if i > 30 and math.hypot(self.x - seg[0], self.y - seg[1]) < self.radius * 0.7:
                return True
        return False

    def draw(self, surface, offset=(0, 0), is_dead=False):
        n = len(self.body)
        for i, seg in enumerate(self.body):
            t = i / n if n > 1 else 0
            col = BLUE_GHOST if self.is_ghost else (
                int(PASTEL_HEAD[0] * (1 - t) + PASTEL_TAIL[0] * t),
                int(PASTEL_HEAD[1] * (1 - t) + PASTEL_TAIL[1] * t),
                int(PASTEL_HEAD[2] * (1 - t) + PASTEL_TAIL[2] * t),
            )
            r = int(self.radius + 2 if i == 0 else self.radius)
            pygame.draw.circle(surface, col,
                               (int(seg[0] + offset[0]), int(seg[1] + offset[1])), r)
        if self.x > -self.radius:
            for side in [-1, 1]:
                ea = self.angle + side * math.pi / 4
                ex = self.x + math.cos(ea) * self.radius * 0.6 + offset[0]
                ey = self.y + math.sin(ea) * self.radius * 0.6 + offset[1]
                if is_dead:
                    pygame.draw.line(surface, EYE_COLOR, (ex-4, ey-4), (ex+4, ey+4), 2)
                    pygame.draw.line(surface, EYE_COLOR, (ex+4, ey-4), (ex-4, ey+4), 2)
                else:
                    pygame.draw.circle(surface, EYE_COLOR, (int(ex), int(ey)), 2)


# ── 먹이 ──
class Food:
    def __init__(self, color: tuple, value: int, obstacles: list):
        self.color    = color
        self.value    = value
        self.obstacles= obstacles
        self.active   = True
        self.max_timer= 300
        self.timer    = self.max_timer
        self.frame_index = 0
        self.anim_timer  = pygame.time.get_ticks()
        self.anim_delay  = 150
        self.respawn()

    def respawn(self):
        for _ in range(300):
            self.x = random.randint(50, WIDTH - 50)
            self.y = random.randint(BARRIER_HEIGHT + 30, HEIGHT - BARRIER_HEIGHT - 30)
            rect = pygame.Rect(self.x - 10, self.y - 10, 20, 20)
            if not any(o['rect'].colliderect(rect) for o in self.obstacles):
                break
        if self.value == 30 or self.color == RED:
            self.timer = self.max_timer

    def update(self):
        if self.color == RED:
            self.timer -= 1
            if self.timer <= 0:
                self.respawn()

    def draw(self, surface, offset=(0, 0)):
        if not self.active:
            return
        ox, oy = self.x + offset[0], self.y + offset[1]
        if self.color == RED and red_food_frames:
            now = pygame.time.get_ticks()
            if now - self.anim_timer >= self.anim_delay:
                self.frame_index = (self.frame_index + 1) % len(red_food_frames)
                self.anim_timer  = now
            img = red_food_frames[self.frame_index]
            surface.blit(img, (ox - img.get_width() // 2, oy - img.get_height() // 2))
        elif self.color == WHITE and green_food_img:
            surface.blit(green_food_img, (ox - 11, oy - 11))
        elif self.color == YELLOW and yellow_food_img:
            surface.blit(yellow_food_img, (ox - 13, oy - 13))
        elif self.value == 30 and orange_food_img:
            surface.blit(orange_food_img, (ox - 12, oy - 12))
            pygame.draw.rect(surface, (50, 50, 50),  (ox - 15, oy - 15, 30, 4))
            pygame.draw.rect(surface, ORANGE_ITEM,
                             (ox - 15, oy - 15, int((self.timer / 300) * 30), 4))
        else:
            pygame.draw.circle(surface, self.color, (int(ox), int(oy)), 8)


# ══════════════════════════════════════════════════════════════
#  5. 헬퍼 함수
# ══════════════════════════════════════════════════════════════
def spawn_particles(particles: list, x, y, color, count=10):
    for _ in range(count):
        particles.append(Particle(x, y, color))


def check_barrier_collision(x, y, radius, obstacles):
    if y < BARRIER_HEIGHT or y > HEIGHT - BARRIER_HEIGHT:
        return True
    for obs in obstacles:
        if obs['rect'].inflate(radius, radius).collidepoint(x, y):
            return True
    return False


def draw_barriers(surface, obstacles, offset=(0, 0)):
    if sand1:
        iw = sand1.get_width()
        for i in range(0, WIDTH + iw, iw):
            surface.blit(sand1, (i + offset[0], offset[1]))
            surface.blit(sand1, (i + offset[0], HEIGHT - BARRIER_HEIGHT + offset[1]))
    for obs in obstacles:
        surface.blit(obs['image'], (obs['rect'].x + offset[0], obs['rect'].y + offset[1]))


def get_random_exit_pos(obstacles=None):
    for _ in range(300):
        x = random.randint(150, WIDTH - 120)
        y = random.randint(BARRIER_HEIGHT + 80, HEIGHT - BARRIER_HEIGHT - 80)
        rect = pygame.Rect(x - 80, y - 80, 160, 160)
        if obstacles is None or not any(o['rect'].colliderect(rect) for o in obstacles):
            return x, y
    return WIDTH // 2, HEIGHT // 2


def create_random_obstacles(stage: StageConfig, exit_x: int, exit_y: int) -> list:
    obs_list = []
    cols, rows = 4, 3
    sw = WIDTH // cols
    sh = (HEIGHT - 2 * BARRIER_HEIGHT) // rows
    density_roll = stage.obstacle_density
    for r in range(rows):
        for c in range(cols):
            if c == 0 and r == 1:
                continue
            if random.random() > density_roll:
                continue
            shape  = random.choice(["L", "I", "T", "G"])
            csand  = random.choice(sand_variants)
            iw, ih = csand.get_size()
            for _ in range(20):
                group = []
                bx = random.randint(c * sw + 10, (c + 1) * sw - iw * 3)
                by = random.randint(BARRIER_HEIGHT + r * sh + 10,
                                    BARRIER_HEIGHT + (r + 1) * sh - ih * 3)
                if shape == "I":
                    horiz = random.random() < 0.5
                    for k in range(3):
                        gx = bx + (k * iw if horiz else 0)
                        gy = by + (0 if horiz else k * ih)
                        group.append({'image': csand, 'rect': pygame.Rect(gx, gy, iw, ih)})
                elif shape == "L":
                    group += [{'image': csand, 'rect': pygame.Rect(bx,      by,      iw, ih)},
                               {'image': csand, 'rect': pygame.Rect(bx,      by + ih, iw, ih)},
                               {'image': csand, 'rect': pygame.Rect(bx + iw, by + ih, iw, ih)}]
                elif shape == "T":
                    group += [{'image': csand, 'rect': pygame.Rect(bx,          by,      iw, ih)},
                               {'image': csand, 'rect': pygame.Rect(bx + iw,     by,      iw, ih)},
                               {'image': csand, 'rect': pygame.Rect(bx + iw * 2, by,      iw, ih)},
                               {'image': csand, 'rect': pygame.Rect(bx + iw,     by + ih, iw, ih)}]
                else:
                    for i2 in range(2):
                        for j2 in range(2):
                            group.append({'image': csand,
                                          'rect': pygame.Rect(bx + i2 * iw, by + j2 * ih, iw, ih)})
                er = pygame.Rect(exit_x - 80, exit_y - 80, 160, 160)
                if (not any(g['rect'].colliderect(er) for g in group) and
                        not any(any(g['rect'].inflate(20, 20).colliderect(e['rect'])
                                    for e in obs_list) for g in group)):
                    obs_list.extend(group)
                    break
    return obs_list


def draw_exit(surface, frame_count, offset, is_open, cycle_timer, max_timer, ex, ey):
    cx = ex + offset[0]
    cy = ey + offset[1]
    if is_open:
        for gr, ga in [(62, 28), (50, 50), (38, 80), (26, 120)]:
            pulse = 0.75 + 0.25 * math.sin(frame_count * 0.07)
            gs = pygame.Surface((gr * 2 + 2, gr * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(gs, (255, 190, 40, int(ga * pulse)), (gr + 1, gr + 1), gr)
            surface.blit(gs, (cx - gr - 1, cy - gr - 1))
        for i in range(8):
            ra = frame_count * 0.025 + i * math.pi * 2 / 8
            ri, ro = 20, 52 + int(math.sin(frame_count * 0.09 + i) * 6)
            x1 = cx + math.cos(ra) * ri; y1 = cy + math.sin(ra) * ri
            x2 = cx + math.cos(ra) * ro; y2 = cy + math.sin(ra) * ro
            alpha = 120 + int(80 * math.sin(frame_count * 0.12 + i * 0.8))
            rs = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pygame.draw.line(rs, (255, 210, 60, alpha), (int(x1), int(y1)), (int(x2), int(y2)), 4)
            surface.blit(rs, (0, 0))
        for i in range(16):
            da = -(frame_count * 0.03) + i * math.pi * 2 / 16
            dx = cx + math.cos(da) * 44; dy = cy + math.sin(da) * 44
            sz = 3 + int(1.5 * math.sin(da * 2 + frame_count * 0.08))
            ds = pygame.Surface((sz * 2 + 2, sz * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(ds, (255, 230, 120, 210), (sz + 1, sz + 1), sz)
            surface.blit(ds, (int(dx) - sz - 1, int(dy) - sz - 1))
        for i in range(10):
            da = frame_count * 0.05 + i * math.pi * 2 / 10
            dx = cx + math.cos(da) * 28; dy = cy + math.sin(da) * 28
            ds = pygame.Surface((8, 8), pygame.SRCALPHA)
            pygame.draw.circle(ds, (255, 255, 200, 180), (4, 4), 2)
            surface.blit(ds, (int(dx) - 4, int(dy) - 4))
        core_r = 15 + int(math.sin(frame_count * 0.11) * 4)
        for cr, ca, col in [(core_r+4, 80, (255,240,160)),
                             (core_r,   200, (255,255,220)),
                             (core_r-5, 255, (255,255,255))]:
            cs = pygame.Surface((cr*2+2, cr*2+2), pygame.SRCALPHA)
            pygame.draw.circle(cs, (*col, ca), (cr+1, cr+1), cr)
            surface.blit(cs, (cx - cr - 1, cy - cr - 1))
        arc_ratio = cycle_timer / max_timer
        arc_steps = int(arc_ratio * 48)
        arc_col   = (80, 255, 80) if arc_ratio > 0.35 else (255, 80, 80)
        for step in range(arc_steps):
            a  = -math.pi / 2 + step * math.pi * 2 / 48
            ax = cx + math.cos(a) * 58; ay = cy + math.sin(a) * 58
            pygame.draw.circle(surface, arc_col, (int(ax), int(ay)), 3)
        if cycle_timer < 180 and frame_count % 18 < 9:
            warn = font_en_mid.render("CLOSING!", True, (255, 60, 60))
            ws = pygame.Surface((warn.get_width()+12, warn.get_height()+6), pygame.SRCALPHA)
            ws.fill((0, 0, 0, 120))
            surface.blit(ws, (cx - warn.get_width()//2 - 6, cy + 52))
            surface.blit(warn, (cx - warn.get_width()//2, cy + 55))
        else:
            lbl = font_en_small.render("▶  ENTER HERE  ◀", True, (220, 255, 180))
            surface.blit(lbl, (cx - lbl.get_width()//2, cy + 60))
    else:
        wait = math.ceil(cycle_timer / 60)
        for gr, ga in [(55, 20), (42, 38), (30, 60)]:
            gs = pygame.Surface((gr*2+2, gr*2+2), pygame.SRCALPHA)
            p  = 0.6 + 0.2 * math.sin(frame_count * 0.04)
            pygame.draw.circle(gs, (90, 55, 20, int(ga * p)), (gr+1, gr+1), gr)
            surface.blit(gs, (cx - gr - 1, cy - gr - 1))
        for i in range(12):
            da = frame_count * 0.012 + i * math.pi * 2 / 12
            dx = cx + math.cos(da)*38; dy = cy + math.sin(da)*38
            ds = pygame.Surface((8, 8), pygame.SRCALPHA)
            pygame.draw.circle(ds, (130, 85, 40, 110), (4, 4), 3)
            surface.blit(ds, (int(dx)-4, int(dy)-4))
        pygame.draw.circle(surface, (50, 30, 10), (cx, cy), 18)
        pygame.draw.circle(surface, (70, 45, 20), (cx, cy), 11)
        cd = font_en_big.render(str(wait), True, (220, 150, 50))
        surface.blit(cd, (cx - cd.get_width()//2, cy - cd.get_height()//2))
        lbl = font_en_small.render("PORTAL SEALED", True, (160, 95, 35))
        surface.blit(lbl, (cx - lbl.get_width()//2, cy + 58))


# ══════════════════════════════════════════════════════════════
#  6. Scene 클래스
# ══════════════════════════════════════════════════════════════
class Scene(abc.ABC):
    @abc.abstractmethod
    def handle_event(self, event: pygame.event.Event, manager: 'SceneManager'):
        pass

    @abc.abstractmethod
    def update(self, manager: 'SceneManager'):
        pass

    @abc.abstractmethod
    def draw(self, surface: pygame.Surface, manager: 'SceneManager'):
        pass


# ── 타이틀 씬 ──
class TitleScene(Scene):
    MENU, GUIDE = "menu", "guide"

    def __init__(self):
        self.sub       = self.MENU
        self.items     = ["Play", "Guide", "Exit"]
        self.idx       = 0
        
        # ... 기존 코드 ...
    # ── 이벤트 ──
    def handle_event(self, event, manager):
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            manager.quit()
        elif event.key == pygame.K_p:
            self.gs.is_paused = not self.gs.is_paused
 
# ... 기존 코드 ...

    def handle_event(self, event, manager):
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            if self.sub == self.GUIDE:
                self.sub = self.MENU
            else:
                manager.quit()
            return
        if self.sub == self.MENU:
            if event.key == pygame.K_w:
                self.idx = (self.idx - 1) % len(self.items)
                if choice_sound: choice_sound.play()
            elif event.key == pygame.K_s:
                self.idx = (self.idx + 1) % len(self.items)
                if choice_sound: choice_sound.play()
            elif event.key == pygame.K_RETURN:
                if choice_sound: choice_sound.play()
                if self.idx == 0:
                    manager.start_game(stage_idx=0)
                elif self.idx == 1:
                    self.sub = self.GUIDE
                else:
                    manager.quit()
        elif self.sub == self.GUIDE:
            if event.key in (pygame.K_RETURN, pygame.K_BACKSPACE):
                self.sub = self.MENU

    def update(self, manager):
        pass

    def draw(self, surface, manager):
        surface.fill(DESERT_COLOR)
        panel = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        panel.fill((180, 150, 110, 200))
        surface.blit(panel, (0, 0))

        if self.sub == self.MENU:
            self._draw_menu(surface, manager)
        else:
            self._draw_guide(surface)

    def _draw_menu(self, surface, manager):
        ts  = font_en_big.render("DESERT DIET MISSION", True, (100, 50, 0))
        tsh = font_en_big.render("DESERT DIET MISSION", True, (60, 30, 0))
        tx  = WIDTH // 2 - ts.get_width() // 2
        surface.blit(tsh, (tx + 2, 72))
        surface.blit(ts,  (tx,     70))
        pygame.draw.line(surface, (100, 60, 20), (60, 140), (WIDTH - 60, 140), 2)

        # 스테이지 선택 안내
        stage_hint = font_ko_small.render("Play → 스테이지 1부터 시작", True, (80, 50, 20))
        surface.blit(stage_hint, (WIDTH // 2 - stage_hint.get_width() // 2, 155))

        mx, my, mg = 80, 220, 60
        for i, item in enumerate(self.items):
            sel  = (i == self.idx)
            col  = (150, 50, 0) if sel else (60, 40, 20)
            surf = font_en_big.render(item, True, col)
            iy   = my + i * mg
            if sel:
                hl = pygame.Surface((surf.get_width() + 20, surf.get_height()), pygame.SRCALPHA)
                hl.fill((255, 220, 150, 80))
                surface.blit(hl, (mx - 8, iy))
                pygame.draw.circle(surface, (200, 80, 40), (mx - 22, iy + surf.get_height()//2), 8)
            surface.blit(surf, (mx, iy))

        if manager.gs.session_high > 0:
            hs = font_ko_small.render(f"세션 최고 기록: {manager.gs.session_high}점", True, (120, 60, 10))
            surface.blit(hs, (WIDTH - hs.get_width() - 20, HEIGHT - 65))

        hint = font_ko_small.render("W / S : 이동    Enter : 선택    Esc : 종료", True, (80, 50, 20))
        surface.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT - 40))

    def _draw_guide(self, surface):
        gt = font_en_mid.render("HOW TO PLAY", True, (100, 50, 0))
        surface.blit(gt, (WIDTH // 2 - gt.get_width() // 2, 28))
        pygame.draw.line(surface, (100, 60, 20), (60, 68), (WIDTH - 60, 68), 2)

        sections = [
            ("[ 조작키 ]", (120, 60, 10), [
                "A / D  :  왼쪽 / 오른쪽 방향 전환",
                "Space  :  유령 모드 발동 (장애물 통과, 쿨다운 있음)",
                "P  :  일시정지 / 재개",
            ]),
            ("[ 먹이 종류 ]", (120, 60, 10), [
                "초록 (+5)  /  노란 (+15)  :  몸 길이 감소, 콤보 가능",
                "주황 (+30)  :  타이머 한정 등장",
                "★ 별 (+50)  :  마일스톤 달성 시 한정 등장!",
                "지렁이 (-20)  :  몸 길이 증가  (3연속 시 데빌 보너스 +80!)",
            ]),
            ("[ 스테이지 ]", (120, 60, 10), [
                "STAGE 1 – Dunes       : 목표 300점  (기본 사막)",
                "STAGE 2 – Rock Maze   : 목표 500점  (장애물 밀집)",
                "STAGE 3 – Sandstorm   : 목표 700점  (빠른 속도, 잦은 지렁이)",
                "각 스테이지 클리어 후 다음 스테이지로 자동 진행!",
            ]),
            ("[ 게임 규칙 ]", (120, 60, 10), [
                "요요 게이지가 차면 -20 Pts & 몸 길이 증가 (경고 주의!)",
                "루루: 70점마다 등장, 먹으면 THICK/THIN/FAST/SLOW/MAGNET 효과",
                "점수 -80 이하 시 게임 오버",
            ]),
        ]
        cy = 85
        for sec_t, tc, lines in sections:
            ss = font_ko_mid.render(sec_t, True, tc)
            surface.blit(ss, (55, cy)); cy += 28
            for ln in lines:
                ls = font_ko_small.render(ln, True, (40, 25, 10))
                surface.blit(ls, (75, cy)); cy += 22
            cy += 6

        back = font_ko_small.render("Enter 또는 Backspace : 메뉴로 돌아가기", True, (80, 50, 20))
        surface.blit(back, (WIDTH // 2 - back.get_width() // 2, HEIGHT - 35))


# ── 스테이지 선택 / 전환 씬 ──
class StageClearScene(Scene):
    def __init__(self, cleared_idx: int, final_score: int):
        self.cleared_idx = cleared_idx
        self.final_score = final_score
        self.timer       = 0

    def handle_event(self, event, manager):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                next_idx = self.cleared_idx + 1
                if next_idx < len(STAGES):
                    manager.start_game(stage_idx=next_idx)
                else:
                    manager.show_all_clear(self.final_score)
            elif event.key == pygame.K_r:
                manager.start_game(stage_idx=0)
            elif event.key == pygame.K_ESCAPE:
                manager.go_title()

    def update(self, manager):
        self.timer += 1

    def draw(self, surface, manager):
        surface.fill(DESERT_COLOR)
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surface.blit(overlay, (0, 0))

        stage = STAGES[self.cleared_idx]
        next_idx = self.cleared_idx + 1

        title = font_en_big.render(f"STAGE {stage.stage_num} CLEAR!", True, (80, 255, 120))
        surface.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//2 - 130))

        sc = font_en_mid.render(f"Score: {self.final_score}", True, WHITE)
        surface.blit(sc, (WIDTH//2 - sc.get_width()//2, HEIGHT//2 - 70))

        if next_idx < len(STAGES):
            nxt = STAGES[next_idx]
            info = font_ko_mid.render(f"다음: {nxt.label}", True, (255, 230, 100))
            surface.blit(info, (WIDTH//2 - info.get_width()//2, HEIGHT//2 - 10))
            hint2 = font_ko_small.render(nxt.hint, True, (200, 200, 200))
            surface.blit(hint2, (WIDTH//2 - hint2.get_width()//2, HEIGHT//2 + 30))
            cont = font_ko_mid.render("[ Enter / Space : 다음 스테이지 ]", True, WHITE)
            surface.blit(cont, (WIDTH//2 - cont.get_width()//2, HEIGHT//2 + 80))
        else:
            ac = font_en_big.render("ALL STAGES CLEAR!", True, STAR_COLOR)
            surface.blit(ac, (WIDTH//2 - ac.get_width()//2, HEIGHT//2 + 20))
            cont = font_ko_mid.render("[ Enter : 결과 확인 ]", True, WHITE)
            surface.blit(cont, (WIDTH//2 - cont.get_width()//2, HEIGHT//2 + 80))

        restart = font_ko_small.render("[ R : 처음부터    Esc : 타이틀 ]", True, (180, 180, 180))
        surface.blit(restart, (WIDTH//2 - restart.get_width()//2, HEIGHT - 45))


# ── 게임 씬 ──
class GameScene(Scene):
    def __init__(self, gs: 'GameState'):
        self.gs = gs
        stage = gs.stage

        self.exit_x, self.exit_y = get_random_exit_pos()
        self.obstacles  = create_random_obstacles(stage, self.exit_x, self.exit_y)
        self.exit_x, self.exit_y = get_random_exit_pos(self.obstacles)
        self.obstacles  = create_random_obstacles(stage, self.exit_x, self.exit_y)

        self.snake      = Snake(stage)
        self.foods: list= [Food(WHITE, 5, self.obstacles),
                           Food(YELLOW, 15, self.obstacles),
                           Food(RED, -20, self.obstacles)]
        self.purple     = Food(ORANGE_ITEM, 30, self.obstacles)
        self.purple.active = False
        self.star       = StarFood(self.obstacles)
        self.animal     = MovingAnimal(self.obstacles)
        self.particles: list        = []
        self.floating:  list        = []

    # ── 이벤트 ──
    def handle_event(self, event, manager):
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            manager.quit()
        elif event.key == pygame.K_p:
            self.gs.is_paused = not self.gs.is_paused
            
        elif event.key == pygame.K_h:
            self.gs.score += 100
            self.floating.append(FloatingText(self.snake.x, self.snake.y - 30, "+100 (CHEAT!)", (0, 200, 255)))
            self.gs.screen_flash = 5

    # ── 업데이트 ──
    def update(self, manager):
        gs = self.gs
        if gs.is_paused:
            return

        # 뱀 업데이트
        prev_ghost = self.snake.is_ghost
        burst = self.snake.update(gs.score)
        if not prev_ghost and self.snake.is_ghost:
            gs.ghost_uses += 1
            if ghost_sound: ghost_sound.play()
        if burst:
            self._spawn_p(0, HEIGHT // 2, DESERT_COLOR, 10)
            self._spawn_p(0, HEIGHT // 2, (200, 160, 100), 14)
            self._spawn_p(0, HEIGHT // 2, (240, 210, 150), 8)
            gs.shake_timer = 5

        # 콤보 타이머
        if gs.combo_timer > 0:
            gs.combo_timer -= 1
        else:
            gs.combo_count = 0

        gs.session_high = max(gs.session_high, gs.score)
        gs.max_score    = max(gs.max_score, gs.score)

        # 마일스톤 별
        for ms in [150, 300, 450]:
            if gs.max_score >= ms and ms not in gs.milestones_done and not self.star.active:
                gs.milestones_done.add(ms)
                self.star.spawn()
                if star_on_sound: star_on_sound.play()
                gs.milestone_flash = 90
                gs.milestone_color = (255, 220, 60)
                self.floating.append(FloatingText(WIDTH//2-60, HEIGHT//2-40, "★ BONUS STAR!", STAR_COLOR))
                self._spawn_p(WIDTH//2, HEIGHT//2, STAR_COLOR, 15)

        # 루루
        self.animal.update()
        tier = gs.score // 70
        if tier > gs.last_spawn_tier and not self.animal.active:
            self.animal.respawn()
            self.animal.active  = True
            gs.last_spawn_tier  = tier
            gs.lulu_timer       = 120
            self.floating.append(FloatingText(WIDTH//2-50, HEIGHT//2-70, "⚠ 루루 등장!", (255,160,60)))
            self._spawn_p(self.animal.x, self.animal.y, (255,160,60), 10)

        # 빨간 먹이 수 조정
        target = gs.stage.red_food_base + (gs.score // 100)
        reds = [f for f in self.foods if f.color == RED]
        while len(reds) < target:
            nb = Food(RED, -20, self.obstacles)
            self.foods.append(nb); reds.append(nb)
        while len(reds) > target:
            self.foods.remove(reds.pop())

        for f in self.foods:
            f.update()
        self.star.update()

        # 자석
        if self.snake.effect_type == "MAGNET" and self.snake.effect_timer > 0:
            all_f = self.foods + ([self.purple] if self.purple.active else []) + ([self.star] if self.star.active else [])
            for f in all_f:
                if hasattr(f,'color') and f.color == RED:
                    continue
                dx = self.snake.x - f.x; dy = self.snake.y - f.y
                dist = math.hypot(dx, dy)
                if 0 < dist < 200:
                    pull = min(3.5, 500 / (dist*dist+1))
                    f.x = max(20, min(WIDTH-20,  f.x + (dx/dist)*pull))
                    f.y = max(BARRIER_HEIGHT+10, min(HEIGHT-BARRIER_HEIGHT-10, f.y + (dy/dist)*pull))
        if self.snake.effect_type == "EVILMAG" and self.snake.effect_timer > 0:
            for f in [f for f in self.foods if f.color == RED]:
                dx = self.snake.x - f.x; dy = self.snake.y - f.y
                dist = math.hypot(dx, dy)
                if 0 < dist < 350:
                    pull = min(5.0, 800 / (dist*dist+1))
                    f.x = max(20, min(WIDTH-20,  f.x + (dx/dist)*pull))
                    f.y = max(BARRIER_HEIGHT+10, min(HEIGHT-BARRIER_HEIGHT-10, f.y + (dy/dist)*pull))

        # 몸 길이 자동 단축
        goal = gs.stage.goal_score
        tgt_len = max(30, 580 - max(0, gs.score) * (550 / max(goal, 1)))
        if self.snake.length > tgt_len:
            spd = (0.25 + (max(0, gs.score) / max(goal, 1)) * 0.35) * 1.25
            self.snake.length -= spd

        # 요요 패널티
        if self.snake.yoyo_timer >= self.snake.yoyo_max:
            gs.score -= 20
            self.snake.length += 20
            self.snake.yoyo_timer = 0
            self.floating.append(FloatingText(self.snake.x, self.snake.y-20, "-20 (YOYO!)", RED))
            gs.shake_timer = 10
            if gs.score < -80:
                manager.show_failure(gs)
                if not gs.played_end_sound and die_sound:
                    die_sound.play(); gs.played_end_sound = True
                return

        # 루루 충돌
        if self.animal.active and math.hypot(self.snake.x-self.animal.x, self.snake.y-self.animal.y) < self.snake.radius+15:
            if lulu_sound: lulu_sound.play()
            gs.lulu_timer = 0
            self.animal.active = False
            pool    = ["THICK","THIN","FAST","SLOW","MAGNET","SCORE80","EVILMAG"]
            weights = [10,     10,    10,    10,    10,      2,        8]
            eff = random.choices(pool, weights=weights, k=1)[0]
            ax, ay = self.animal.x, self.animal.y
            if eff == "SCORE80":
                gs.score += 80; gs.screen_flash = 10
                self._spawn_p(ax, ay, (255,230,60), 22)
                self.floating.append(FloatingText(ax, ay,    "★ SCORE +80!", STAR_COLOR))
                self.floating.append(FloatingText(ax, ay-30, "JACKPOT!!",    (255,200,50)))
                gs.shake_timer = 8
            elif eff == "EVILMAG":
                self.snake.effect_type, self.snake.effect_timer = eff, 450
                self.floating.append(FloatingText(ax, ay,    "EVIL MAGNET!",     RED))
                self.floating.append(FloatingText(ax, ay-28, "지렁이가 몰려온다!", (255,80,80)))
                gs.shake_timer = 6
                self._spawn_p(ax, ay, (220,40,40), 16)
            else:
                self.snake.effect_type, self.snake.effect_timer = eff, 450
                self.floating.append(FloatingText(ax, ay, f"EFFECT: {eff}!", ORANGE_ITEM))
                self._spawn_p(ax, ay, ORANGE_ITEM, 12)

        # 주황 먹이 타이머
        if self.purple.active:
            self.purple.timer -= 1
            if self.purple.timer <= 0:
                self.purple.active = False

        # 먹이 충돌
        for f in self.foods + ([self.purple] if self.purple.active else []):
            if not f.active:
                continue
            if math.hypot(self.snake.x - f.x, self.snake.y - f.y) < self.snake.radius + 8:
                self._on_eat(f, manager)
                break   # 한 프레임에 하나만

        # 별 충돌
        if self.star.active and math.hypot(self.snake.x-self.star.x, self.snake.y-self.star.y) < self.snake.radius+16:
            if star_sound: star_sound.play()
            gs.score += 50; gs.foods_eaten += 1
            self.star.active = False; gs.screen_flash = 8
            self._spawn_p(self.star.x, self.star.y, STAR_COLOR, 22)
            self.floating.append(FloatingText(self.star.x, self.star.y, "+50 STAR!", STAR_COLOR))
            gs.combo_timer = GameState.COMBO_WINDOW; gs.combo_count += 1
            if gs.combo_count >= 2:
                bonus = (gs.combo_count - 1) * 5; gs.score += bonus
                self.floating.append(FloatingText(self.star.x, self.star.y-28,
                                                  f"COMBO x{gs.combo_count}!  +{bonus}", (255,210,60)))
                idx = min(gs.combo_count-2, len(combo_sounds)-1)
                if combo_sounds: combo_sounds[idx].play()

        # 클리어 조건 — 포탈
        goal = gs.stage.goal_score
        if gs.score >= goal:
            if not gs.can_exit:
                gs.can_exit      = True
                gs.exit_is_open  = True
                gs.exit_cycle_timer = GameState.EXIT_OPEN_DURATION
                if not gs.exit_announced:
                    gs.exit_announced = True; gs.screen_flash = 12
                    if portal_open_sound: portal_open_sound.play()
                    self.floating.append(FloatingText(self.exit_x-80, self.exit_y-80,
                                                      "PORTAL OPENED!", (255,220,60)))
                    self._spawn_p(self.exit_x, self.exit_y, (255,210,60), 30)
                    gs.shake_timer = 8

            gs.exit_cycle_timer -= 1
            if gs.exit_cycle_timer <= 0:
                if gs.exit_is_open:
                    gs.exit_is_open = False
                    gs.exit_cycle_timer = GameState.EXIT_CLOSE_DURATION
                    if portal_seal_sound: portal_seal_sound.play()
                    self.floating.append(FloatingText(self.exit_x-70, self.exit_y-50,
                                                      "PORTAL SEALED!", RED))
                    gs.shake_timer = 6
                else:
                    gs.exit_is_open = True
                    gs.exit_cycle_timer = GameState.EXIT_OPEN_DURATION
                    gs.screen_flash = 8
                    if portal_open_sound: portal_open_sound.play()
                    self.floating.append(FloatingText(self.exit_x-70, self.exit_y-50,
                                                      "PORTAL OPENED!", (255,220,60)))
                    self._spawn_p(self.exit_x, self.exit_y, (255,210,60), 18)

            if gs.exit_is_open and math.hypot(self.snake.x-self.exit_x, self.snake.y-self.exit_y) < 20:
                manager.show_sucking(gs, self)
                return

        # 사망
        if ((not self.snake.is_ghost and not self.snake.is_entering and
             check_barrier_collision(self.snake.x, self.snake.y, self.snake.radius, self.obstacles)) or
                self.snake.check_self_collision() or gs.score < -80):
            manager.show_failure(gs)
            gs.shake_timer = 40
            if not gs.played_end_sound and die_sound:
                die_sound.play(); gs.played_end_sound = True
            return

        if not self.snake.is_entering:
            self.snake.x %= WIDTH; self.snake.y %= HEIGHT

        # 파티클
        for p in self.particles[:]:
            p.update()
            if p.life <= 0:
                self.particles.remove(p)

        # 렌더 오프셋
        if gs.shake_timer > 0:
            gs.render_offset = [random.randint(-gs.shake_amount, gs.shake_amount),
                                 random.randint(-gs.shake_amount, gs.shake_amount)]
            gs.shake_timer -= 1
        else:
            gs.render_offset = [0, 0]

        gs.frame_count += 1

    def _on_eat(self, f: Food, manager):
        gs = self.gs
        ex, ey = f.x, f.y
        if f.color == RED:
            if minus_eat_sound: minus_eat_sound.play()
            gs.score += f.value; self.snake.length += 10
            gs.shake_timer = 15; gs.red_streak += 1; gs.reds_eaten += 1
            gs.combo_count = 0; gs.combo_timer = 0
            self._spawn_p(ex, ey, (220,60,60), 8)
            if gs.red_streak >= 3:
                gs.score += 80; gs.red_streak = 0
                self.floating.append(FloatingText(ex, ey-35, "DEVIL BONUS! +80", (255,50,50)))
                self._spawn_p(ex, ey, (255,30,30), 18); gs.shake_timer = 8
        else:
            if eat_sound: eat_sound.play()
            gs.score += f.value
            self.snake.length = max(10, self.snake.length - (f.value * 1.25))
            gs.red_streak = 0; gs.foods_eaten += 1
            gs.combo_timer = GameState.COMBO_WINDOW; gs.combo_count += 1
            if gs.combo_count >= 2:
                bonus = (gs.combo_count-1)*5; gs.score += bonus
                self.floating.append(FloatingText(ex, ey-28,
                                                  f"COMBO x{gs.combo_count}!  +{bonus}", (255,210,60)))
                idx = min(gs.combo_count-2, len(combo_sounds)-1)
                if combo_sounds: combo_sounds[idx].play()
            pc = (100,220,100) if f.color==WHITE else (220,220,80) if f.color==YELLOW else (255,165,0)
            self._spawn_p(ex, ey, pc, 10)
        if self.snake.cooldown_timer > 0:
            self.snake.cooldown_timer = max(0, self.snake.cooldown_timer - 30)
        self.snake.yoyo_timer = 0
        fc = RED if f.value < 0 else (YELLOW if f.value >= 15 else (WHITE if f.value != 30 else ORANGE_ITEM))
        self.floating.append(FloatingText(ex, ey, f"{f.value} Pts", fc))
        if f == self.purple:
            self.purple.active = False
        else:
            f.respawn()
            if not self.purple.active and random.random() < gs.stage.purple_chance:
                self.purple.respawn(); self.purple.active = True

    def _spawn_p(self, x, y, color, count=10):
        spawn_particles(self.particles, x, y, color, count)

    # ── 그리기 ──
    def draw(self, surface, manager):
        gs  = self.gs
        off = gs.render_offset

        surface.fill(DESERT_COLOR)

        if gs.score < 0:
            tint = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            tint.fill((200, 0, 0, min(90, abs(gs.score)*2)))
            surface.blit(tint, (0, 0))

        if gs.can_exit:
            draw_exit(surface, gs.frame_count, off,
                      is_open=gs.exit_is_open,
                      cycle_timer=gs.exit_cycle_timer,
                      max_timer=(GameState.EXIT_OPEN_DURATION if gs.exit_is_open
                                 else GameState.EXIT_CLOSE_DURATION),
                      ex=self.exit_x, ey=self.exit_y)

        self.snake.draw(surface, off)
        for f in self.foods:
            f.draw(surface, off)
        if self.purple.active:
            self.purple.draw(surface, off)
        self.star.draw(surface, off)
        self.animal.draw(surface, off)
        draw_barriers(surface, self.obstacles, off)

        for p in self.particles:
            p.draw(surface, off)
        for ft in self.floating[:]:
            ft.update()
            if ft.life > 0:
                ft.draw(surface, off)
            else:
                self.floating.remove(ft)

        # 화면 플래시
        if gs.screen_flash > 0:
            fl = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            fl.fill((255, 255, 200, int(160 * gs.screen_flash / 8)))
            surface.blit(fl, (0, 0)); gs.screen_flash -= 1

        # 마일스톤 테두리
        if gs.milestone_flash > 0:
            ba = int(200 * gs.milestone_flash / 90)
            bfl = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pygame.draw.rect(bfl, (*gs.milestone_color, ba), (0, 0, WIDTH, HEIGHT), 18)
            surface.blit(bfl, (0, 0)); gs.milestone_flash -= 1

        # 루루 예고
        if gs.lulu_timer > 0 and self.animal.active:
            gs.lulu_timer -= 1
            if gs.lulu_timer % 20 < 10:
                ls = font_ko_mid.render("⚠  루루 등장!", True, (255, 140, 0))
                lb = pygame.Surface((ls.get_width()+16, ls.get_height()+6), pygame.SRCALPHA)
                lb.fill((0, 0, 0, 130))
                surface.blit(lb, (WIDTH//2 - ls.get_width()//2 - 8, 108))
                surface.blit(ls, (WIDTH//2 - ls.get_width()//2, 111))

        self._draw_ui(surface, off)

        if gs.is_paused:
            po = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            po.fill((0, 0, 0, 140))
            surface.blit(po, (0, 0))
            pt = font_en_big.render("PAUSE", True, WHITE)
            surface.blit(pt, (WIDTH//2 - pt.get_width()//2, HEIGHT//2 - 60))
            ph = font_ko_mid.render("[ P - 재개 ]", True, (200, 200, 200))
            surface.blit(ph, (WIDTH//2 - ph.get_width()//2, HEIGHT//2 + 10))

    def _draw_ui(self, surface, off):
        gs = self.gs
        stage = gs.stage

        # 점수 / 스테이지 정보
        surface.blit(font_en_mid.render(
            f"Score: {gs.score} / {stage.goal_score}", True, BLACK),
            (20 + off[0], 20 + off[1]))
        stage_lbl = font_en_small.render(stage.label, True, (100, 50, 0))
        surface.blit(stage_lbl, (20 + off[0], 52 + off[1]))

        # 효과
        if self.snake.effect_type:
            surface.blit(font_ko_small.render(
                f"상태: {self.snake.effect_type} ({self.snake.effect_timer//60}s)", True, RED),
                (20 + off[0], 70 + off[1]))

        # 콤보
        if gs.combo_count >= 2 and gs.combo_timer > 0:
            ca = int(255 * min(1.0, gs.combo_timer / 40))
            cs = font_en_mid.render(f"COMBO  x{gs.combo_count}", True, (255, 215, 50))
            cs.set_alpha(ca)
            surface.blit(cs, (20 + off[0], 90 + off[1]))

        # 세션 최고
        hs = font_en_small.render(f"BEST: {gs.session_high}", True, (100, 60, 10))
        surface.blit(hs, (20 + off[0], HEIGHT - 30 + off[1]))

        # 요요 게이지
        bx, by, bw, bh = WIDTH - 170, 40, 150, 12
        pygame.draw.rect(surface, (50, 50, 50), (bx + off[0], by + off[1], bw, bh))
        yr = min(1.0, self.snake.yoyo_timer / self.snake.yoyo_max)
        gc = RED if yr > 0.7 else YELLOW
        pygame.draw.rect(surface, gc, (bx + off[0], by + off[1], int(bw*yr), bh))
        surface.blit(font_en_small.render("YOYO GAUGE", True, BLACK),
                     (bx + off[0], by - 25 + off[1]))

        if yr > 0.78 and gs.frame_count % 28 < 14:
            ws = font_ko_mid.render("⚠  요요 위험!", True, RED)
            wb = pygame.Surface((ws.get_width()+10, ws.get_height()+4), pygame.SRCALPHA)
            wb.fill((255, 0, 0, 60))
            surface.blit(wb, (WIDTH//2 - ws.get_width()//2 - 5 + off[0], 78 + off[1]))
            surface.blit(ws, (WIDTH//2 - ws.get_width()//2 + off[0], 80 + off[1]))
        if yr > 0.78 and not gs.yoyo_warned:
            if warning_sound: warning_sound.play()
            gs.yoyo_warned = True
        elif yr <= 0.70:
            gs.yoyo_warned = False

        # 고스트 게이지
        gx = bx - 190
        pygame.draw.rect(surface, (50, 50, 50), (gx + off[0], by + off[1], bw, bh))
        gr = 1 - (self.snake.cooldown_timer / 1080)
        pygame.draw.rect(surface, BLUE_GHOST, (gx + off[0], by + off[1], int(bw*gr), bh))
        gcd = math.ceil(self.snake.cooldown_timer / 60)
        gl = f"GHOST: {gcd}s" if gcd > 0 else "GHOST: READY"
        surface.blit(font_en_small.render(gl, True, BLACK),
                     (gx + off[0], by - 25 + off[1]))
        surface.blit(font_en_small.render(f"(used: {gs.ghost_uses}x)", True, (80,100,140)),
                     (gx + off[0], by + bh + 4 + off[1]))
        if self.snake.is_ghost and self.snake.ghost_timer > 0:
            gt  = math.ceil(self.snake.ghost_timer / 60)
            gts = font_en_small.render(f"GHOST ACTIVE: {gt}s", True, BLUE_GHOST)
            gtb = pygame.Surface((gts.get_width()+10, gts.get_height()+4), pygame.SRCALPHA)
            gtb.fill((0,0,0,110))
            surface.blit(gtb, (gx + off[0] - 2, by + bh + 20 + off[1]))
            surface.blit(gts, (gx + off[0] + 3, by + bh + 22 + off[1]))


# ── 포탈 빨려들기 씬 ──
class SuckingScene(Scene):
    def __init__(self, gs: GameState, game_scene: GameScene):
        self.gs         = gs
        self.game_scene = game_scene
        self.timer      = 70
        if not gs.played_end_sound and complete_sound:
            complete_sound.play(); gs.played_end_sound = True

    def handle_event(self, event, manager):
        pass

    def update(self, manager):
        gs = self.gs
        self.timer -= 1
        prog = 1.0 - self.timer / 70.0
        ease = prog ** 3
        s    = self.game_scene.snake
        ex, ey = self.game_scene.exit_x, self.game_scene.exit_y
        dx = ex - s.x; dy = ey - s.y
        dist = math.hypot(dx, dy) or 1
        move = min(1.5 + ease * 14, dist)
        s.x += (dx / dist) * move; s.y += (dy / dist) * move
        s.body.insert(0, (s.x, s.y))
        s.length = max(1, s.length - (2 + ease * 14))
        s.body   = s.body[:int(s.length)]
        if self.timer % 10 == 0:
            spawn_particles(self.game_scene.particles, ex, ey, (255,220,100), 2)
        for p in self.game_scene.particles[:]:
            p.update()
            if p.life <= 0:
                self.game_scene.particles.remove(p)
        if self.timer <= 0:
            manager.show_stage_clear(gs)

    def draw(self, surface, manager):
        self.game_scene.draw(surface, manager)
        if self.timer < 25:
            fa = int(255 * (1 - self.timer / 25))
            fs = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            fs.fill((255, 240, 180, fa))
            surface.blit(fs, (0, 0))


# ── 결과 씬 ──
class ResultScene(Scene):
    def __init__(self, gs: GameState, success: bool):
        self.gs      = gs
        self.success = success

    def handle_event(self, event, manager):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                manager.start_game(stage_idx=0)
            elif event.key == pygame.K_ESCAPE:
                manager.go_title()

    def update(self, manager):
        pass

    def draw(self, surface, manager):
        surface.fill(DESERT_COLOR)
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surface.blit(overlay, (0, 0))

        gs = self.gs
        col = (80, 255, 120) if self.success else RED
        msg = "MISSION COMPLETE!" if self.success else "GAME OVER"
        ms  = font_en_big.render(msg, True, col)
        surface.blit(ms, (WIDTH//2 - ms.get_width()//2, HEIGHT//2 - 120))

        fs  = font_en_mid.render(f"Final Score: {gs.score}", True, WHITE)
        surface.blit(fs, (WIDTH//2 - fs.get_width()//2, HEIGHT//2 - 60))

        st  = font_ko_small.render(
            f"먹이: {gs.foods_eaten}개   지렁이: {gs.reds_eaten}개   고스트: {gs.ghost_uses}회",
            True, (200, 200, 200))
        surface.blit(st, (WIDTH//2 - st.get_width()//2, HEIGHT//2 - 20))

        if gs.session_high > 0:
            hl  = "★ 최고 기록!" if gs.score == gs.session_high and gs.score > 0 else f"세션 최고: {gs.session_high}점"
            hc  = STAR_COLOR if gs.score == gs.session_high and gs.score > 0 else (180,180,180)
            hs  = font_ko_mid.render(hl, True, hc)
            surface.blit(hs, (WIDTH//2 - hs.get_width()//2, HEIGHT//2 + 20))

        enc = "대단해요! 모든 스테이지를 탈출했습니다!" if self.success else "다시 도전해보세요!"
        es  = font_ko_small.render(enc, True, (210, 210, 210))
        surface.blit(es, (WIDTH//2 - es.get_width()//2, HEIGHT//2 + 60))

        surface.blit(font_ko_mid.render("[ R : 다시 시작    Esc : 타이틀 ]", True, WHITE),
                     (WIDTH//2 - 130, HEIGHT//2 + 100))


# ══════════════════════════════════════════════════════════════
#  7. SceneManager
# ══════════════════════════════════════════════════════════════
class SceneManager:
    def __init__(self):
        self.gs           = GameState()
        self._current:    Optional[Scene] = TitleScene()
        self._running     = True

    @property
    def running(self):
        return self._running

    def quit(self):
        self._running = False

    def go_title(self):
        self._current = TitleScene()

    def start_game(self, stage_idx: int):
        self.gs.reset_for_stage(stage_idx)
        self._current = GameScene(self.gs)

    def show_sucking(self, gs: GameState, game_scene: GameScene):
        self._current = SuckingScene(gs, game_scene)

    def show_stage_clear(self, gs: GameState):
        self._current = StageClearScene(gs.stage_idx, gs.score)

    def show_all_clear(self, final_score: int):
        self._current = ResultScene(self.gs, success=True)

    def show_failure(self, gs: GameState):
        self._current = ResultScene(gs, success=False)

    def handle_event(self, event: pygame.event.Event):
        if self._current:
            self._current.handle_event(event, self)

    def update(self):
        if self._current:
            self._current.update(self)

    def draw(self, surface: pygame.Surface):
        if self._current:
            self._current.draw(surface, self)


# ══════════════════════════════════════════════════════════════
#  8. 메인 루프
# ══════════════════════════════════════════════════════════════
manager = SceneManager()

while manager.running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            manager.quit()
        else:
            manager.handle_event(event)

    manager.update()
    manager.draw(screen)
    pygame.display.flip()
    clock.tick(60)

pygame.quit()