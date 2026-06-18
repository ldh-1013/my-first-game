import pygame
import sys
import os
import math
import random

# --- PyInstaller-aware paths -------------------------------------------------
if hasattr(sys, '_MEIPASS'):
    BASE_PATH = sys._MEIPASS
else:
    BASE_PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_PATH)

if getattr(sys, 'frozen', False):
    SAVE_DIR = os.path.dirname(sys.executable)
else:
    SAVE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_PATH_NORMAL   = os.path.join(SAVE_DIR, 'highscore_normal.txt')
SAVE_PATH_HARDCORE = os.path.join(SAVE_DIR, 'highscore_hardcore.txt')

from data.core_funcs import (swap_color, advance_deg, alpha_line, blit_center,
                              sign_func, normalize, dis_func, mirror_angle,
                              check_line_sides, doIntersect)
from data.entities import (load_assets, Particle, Spark,
                            LineEffect, CircleEffect)
from data.text import Font

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
RENDER_W, RENDER_H = 275, 400
BORDER_WIDTH = 70
SCREEN_W = RENDER_W * 2 + BORDER_WIDTH * 2   # 690
SCREEN_H = RENDER_H * 2                       # 800
FPS = 60

background_color      = (13,  20,  33)   # initial value (biomes override per-frame)
line_placing_color    = ( 32, 163, 166)
player_color          = ( 45, 226, 230)
laser_color           = (190,  40, 100)
SHIELD_COLOR          = (255, 176,  46)   # amber-gold
PICKUP_R              = 6                  # shield orb radius (render px)
LINE_WIDTH            = 3
MAX_SPEED             = 6     # velocity magnitude cap (5=easy, 6=default, 7=hard)

# ---------------------------------------------------------------------------
# Zone boundaries — single source of truth for all zone-dependent systems.
# Edit only this list; background crossfade and biome colors follow automatically.
# ---------------------------------------------------------------------------
ZONE_BOUNDS = [0, 3000, 5000, 8000, 12000]   # city / clouds / space / milky way / deep space

ZONE_NAMES = ['NEON CITY', 'CLOUD', 'SPACE', 'THE MILKY WAY', 'DEEP SPACE']

def zone_index(score):
    for i in range(len(ZONE_BOUNDS) - 1, -1, -1):
        if score >= ZONE_BOUNDS[i]:
            return i
    return 0

def combo_mult(combo):
    if combo < 2:
        return 1
    return min(combo, 5)

def load_high_score(mode='normal'):
    path = SAVE_PATH_HARDCORE if mode == 'hardcore' else SAVE_PATH_NORMAL
    try:
        with open(path, 'r') as f:
            return int(f.read().strip())
    except Exception:
        return 0

def save_high_score(v, mode='normal'):
    path = SAVE_PATH_HARDCORE if mode == 'hardcore' else SAVE_PATH_NORMAL
    try:
        with open(path, 'w') as f:
            f.write(str(int(v)))
    except Exception as e:
        print('highscore save failed:', e)

# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------
pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()
pygame.mixer.set_num_channels(32)

screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), 0, 32)
pygame.display.set_caption('ZENITH')

display = pygame.Surface((RENDER_W, RENDER_H))
display.set_colorkey(background_color)

gui_display = pygame.Surface((RENDER_W, RENDER_H))
gui_display.set_colorkey((0, 0, 0))

mainClock = pygame.time.Clock()

# ---------------------------------------------------------------------------
# Assets
# ---------------------------------------------------------------------------
load_assets(BASE_PATH)

def _load_snd(name):
    try:
        return pygame.mixer.Sound(os.path.join(BASE_PATH, 'data', 'sfx', name))
    except Exception:
        return None

bounce_s       = _load_snd('bounce.wav')
death_s        = _load_snd('death.wav')
laser_charge_s = _load_snd('laser_charge.wav')
laser_explode_s= _load_snd('laser_explode.wav')
place_s        = _load_snd('place.wav')
restart_s      = _load_snd('restart.wav')

def _vol(snd, v):
    if snd: snd.set_volume(v)

_vol(bounce_s, 0.7); _vol(place_s, 0.9); _vol(laser_charge_s, 0.05)

try:
    pygame.mixer.music.load(os.path.join(BASE_PATH, 'data', 'music.wav'))
    pygame.mixer.music.set_volume(0.7)
    pygame.mixer.music.play(-1)
except Exception:
    pass

_SFX          = [bounce_s, death_s, laser_charge_s, laser_explode_s, place_s, restart_s]
_SFX_DEFAULTS = [0.7, 1.0, 0.05, 1.0, 0.9, 1.0]
_MUSIC_VOL    = 0.7
muted         = False

def set_muted(m):
    global muted
    muted = m
    if pygame.mixer.get_init():
        pygame.mixer.music.set_volume(0.0 if m else _MUSIC_VOL)
        for snd, vol in zip(_SFX, _SFX_DEFAULTS):
            if snd:
                snd.set_volume(0.0 if m else vol)

_TTF = os.path.join(BASE_PATH, 'data', 'fonts', 'dogica.ttf')
font  = Font(_TTF, 8, (255, 255, 255))
font2 = Font(_TTF, 8, (0, 0, 1))
combo_big    = Font(_TTF, 16, (255, 180, 60))   # warm, big — high-combo indicator
combo_big_sh = Font(_TTF, 16, (0, 0, 1))

ZONE_BANNER_DUR  = 150
zb_big      = Font(_TTF, 24, (255, 255, 255))
zb_big_sh   = Font(_TTF, 24, (0, 0, 1))
zb_small    = Font(_TTF, 12, (160, 140, 220))
zb_small_sh = Font(_TTF, 12, (0, 0, 1))
zone_banner_surf = pygame.Surface((SCREEN_W, 80))
zone_banner_surf.set_colorkey((0, 0, 0))

_transition_surf = pygame.Surface((SCREEN_W, SCREEN_H))
_transition_surf.fill((0, 0, 0))

# ---------------------------------------------------------------------------
# Screen baseline
# ---------------------------------------------------------------------------
screen.fill(background_color)   # one-time baseline; never clear again

hs_normal   = load_high_score('normal')
hs_hardcore = load_high_score('hardcore')
high_score  = hs_normal   # overwritten after mode selection

sq_surf = pygame.Surface((RENDER_W, RENDER_H), pygame.SRCALPHA)
_NEON_SQ_COLORS = [(45, 226, 230), (160, 140, 220)]

# ---------------------------------------------------------------------------
# Background image assets (loaded once, scaled to game width)
# ---------------------------------------------------------------------------
if hasattr(sys, '_MEIPASS'):
    _BG_DIR = os.path.join(BASE_PATH, 'assets', 'data', 'backgrounds')
else:
    _BG_DIR = os.path.join(BASE_PATH, '..', 'assets', 'data', 'backgrounds')
_BG_FILES = ['1.png', '2.png', '3.png', '4.png', '5.png']   # zone 0..4 mapping

_IMG_W     = SCREEN_W                   # 690 — full window width
_IMG_H     = int(3000 * _IMG_W / 1920)  # 1078 (proportional from 1920×3000 source)
_IMG_EXTRA = max(0, _IMG_H - SCREEN_H)  # ~278 px parallax headroom

bg_images = []
for _f in _BG_FILES:
    try:
        _img = pygame.image.load(os.path.join(_BG_DIR, _f)).convert()
        bg_images.append(pygame.transform.scale(_img, (_IMG_W, _IMG_H)))
    except Exception as _e:
        print(f'bg image load failed: {_f}: {_e}')
        bg_images.append(None)

veil_surf  = pygame.Surface((SCREEN_W, SCREEN_H))
veil_surf.set_alpha(85)
cross_surf = pygame.Surface((_IMG_W, _IMG_H))

# shield sprites (optional image assets; fall back to procedural rings if missing)
try:
    shield_img = pygame.image.load(
        os.path.join(BASE_PATH, 'data', 'images', 'shield.png')).convert_alpha()
except Exception as _e:
    print(f'shield image load failed: {_e}')
    shield_img = None
try:
    pickup_img = pygame.image.load(
        os.path.join(BASE_PATH, 'data', 'images', 'shield_pickup.png')).convert_alpha()
except Exception as _e:
    pickup_img = None

# Pre-render divider lines (play boundary at x=BORDER_WIDTH and x=SCREEN_W-BORDER_WIDTH)
divider_surf = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
for _dx in (BORDER_WIDTH, SCREEN_W - BORDER_WIDTH):
    pygame.draw.line(divider_surf, ( 40,  30,  55,  80), (_dx, 0), (_dx, SCREEN_H), 9)
    pygame.draw.line(divider_surf, ( 80,  60, 110, 140), (_dx, 0), (_dx, SCREEN_H), 5)
    pygame.draw.line(divider_surf, (140, 110, 170, 200), (_dx, 0), (_dx, SCREEN_H), 2)
    pygame.draw.line(divider_surf, (201, 171, 201, 255), (_dx, 0), (_dx, SCREEN_H), 1)

# ---- Edge-proximity warning vignettes (red glow near play boundary) ----
WARN_DIST  = 70
_WARN_W    = WARN_DIST * 2
_WARN_MAXA = 140
_WARN_COL  = (255, 40, 50)
vig_left  = pygame.Surface((_WARN_W, SCREEN_H), pygame.SRCALPHA)
vig_right = pygame.Surface((_WARN_W, SCREEN_H), pygame.SRCALPHA)
for _c in range(_WARN_W):
    _fl = 1.0 - _c / _WARN_W
    pygame.draw.line(vig_left,  (*_WARN_COL, int(_WARN_MAXA * _fl * _fl)),
                     (_c, 0), (_c, SCREEN_H))
    _fr = _c / _WARN_W
    pygame.draw.line(vig_right, (*_WARN_COL, int(_WARN_MAXA * _fr * _fr)),
                     (_c, 0), (_c, SCREEN_H))

BG_BLEND_RANGE = 400

def bg_zone_alpha(altitude):
    """Returns (zone_index, t) where current zone fades out as t rises to 1."""
    for i in range(len(ZONE_BOUNDS) - 1, 0, -1):
        fade_start = ZONE_BOUNDS[i] - BG_BLEND_RANGE
        fade_end   = ZONE_BOUNDS[i] + BG_BLEND_RANGE
        if altitude >= fade_start:
            if altitude < fade_end:
                t = (altitude - fade_start) / (BG_BLEND_RANGE * 2)
                return i - 1, min(1.0, max(0.0, t))
            break
    zone = 0
    for i in range(len(ZONE_BOUNDS) - 1, -1, -1):
        if altitude >= ZONE_BOUNDS[i]:
            zone = min(i, 4)
            break
    return zone, 0.0


# ---------------------------------------------------------------------------
# Title / start screen — isolated loop, runs once before gameplay.
# Does NOT touch the game state (g) or the bloom composite.
# ---------------------------------------------------------------------------
title_font   = Font(_TTF, 48, player_color)
title_shadow = Font(_TTF, 48, (0, 0, 1))
title_sub    = Font(_TTF, 14, (160, 140, 220))
title_info   = Font(_TTF, 12, (200, 200, 210))
mode_font     = Font(_TTF, 18, (255, 255, 255))   # unselected option — white
mode_font_sel = Font(_TTF, 18, player_color)       # selected option   — aqua

_title_dark = pygame.Surface((SCREEN_W, SCREEN_H))
_title_dark.set_alpha(160)
_title_dark.fill((0, 0, 0))

def _title_centered(fnt, text, y, shadow=None):
    x = SCREEN_W // 2 - fnt.width(text) // 2
    if shadow is not None:
        shadow.render(text, screen, (x + 3, y + 3))
    fnt.render(text, screen, (x, y))

def title_screen():
    t = 0
    sel = 0   # 0 = normal, 1 = hardcore
    modes = [('NORMAL',   '10 lives - checkpoints'),
             ('HARDCORE', '1 life - no checkpoint')]
    while True:
        t += 1
        cy = SCREEN_H // 2
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()
                if event.key in (pygame.K_UP, pygame.K_w, pygame.K_LEFT):
                    sel = (sel - 1) % 2
                if event.key in (pygame.K_DOWN, pygame.K_s, pygame.K_RIGHT):
                    sel = (sel + 1) % 2
                if event.key == pygame.K_1:
                    return 'normal'
                if event.key == pygame.K_2:
                    return 'hardcore'
                if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    return 'normal' if sel == 0 else 'hardcore'
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                _my = event.pos[1]
                if abs(_my - (cy + 10)) < 16:
                    return 'normal'
                if abs(_my - (cy + 50)) < 16:
                    return 'hardcore'
                return 'normal' if sel == 0 else 'hardcore'

        # background: darkened city zone image (fallback flat color)
        if bg_images[0] is not None:
            screen.blit(bg_images[0], (0, -(_IMG_H - SCREEN_H)))
            screen.blit(_title_dark, (0, 0))
        else:
            screen.fill(background_color)
        screen.blit(divider_surf, (0, 0))

        _title_centered(title_font, 'ZENITH',      cy - 170, shadow=title_shadow)
        _title_centered(title_sub,  'neon ascent', cy - 110)
        _title_centered(title_info, 'NORMAL BEST: ' + str(hs_normal),  cy - 70)
        _title_centered(title_info, 'HC BEST: '    + str(hs_hardcore), cy - 55)

        # mode options — unselected white, selected aqua, NO drop shadow
        for i, (name, desc) in enumerate(modes):
            oy = cy + 10 + i * 40
            if i == sel:
                _title_centered(mode_font_sel, '> ' + name + ' <', oy)
                _title_centered(title_info,    desc,               oy + 20)
            else:
                _title_centered(mode_font, name, oy)

        if (t // 30) % 2 == 0:
            _title_centered(title_info, 'UP / DOWN to choose   -   SPACE to start', cy + 120)
        _title_centered(title_info, 'draw lines  -  bounce up  -  avoid the sides', cy + 148)

        pygame.display.update()
        mainClock.tick(FPS)


# ---------------------------------------------------------------------------
# Game-state initialiser (also called on full reset)
# ---------------------------------------------------------------------------
def init_game(mode='normal'):
    return dict(
        platforms      = [[[0, RENDER_H - 1], [RENDER_W, RENDER_H - 1]]],
        last_point     = [RENDER_W // 2, RENDER_H],
        player_pos     = [float(RENDER_W // 2), float(RENDER_H // 2)],
        player_vel     = [0.0, 0.0],
        player_path    = [],
        game_score     = 0,       # height gained this session (resets on continue)
        bonus_score    = 0,       # combo bonus this session
        combo          = 0,
        mode           = mode,    # 'normal' | 'hardcore'
        score_baseline = 0,       # checkpoint score added to game_score+bonus
        checkpoint     = 0,       # highest n*1000 reached (revival point)
        lives          = 0,       # extra retries earned
        next_milestone = 1000,    # next score that grants a life
        is_new_best    = False,
        life_msg_timer = 0,       # frames to show "+1 LIFE" flash
        end_game       = False,
        last_place     = 50,
        scroll         = 0.0,
        bounce_cd      = 0,
        lasers         = [],
        particles      = [],
        sparks         = [],
        line_effects   = [],
        circle_effects = [],
        neon_squares   = [],
        game_text_loc  = -120.0,
        end_text_loc   = -220.0,
        screen_shake   = 0,
        shielded        = False,
        shield_items    = [],
        shield_flash    = 0,
        transition     = 30,
        zone_idx         = -1,
        zone_banner_idx  = 0,
        zone_banner_timer= 0,
        newbest_timer  = 0,
        best_passed    = False,
        line_color     = (255, 255, 255),
        frame          = 0,
    )


def continue_game(g):
    """Consume one life and restart from checkpoint. Mutates g in place."""
    g['lives']         -= 1
    g['score_baseline'] = g['checkpoint']
    g['game_score']     = 0
    g['bonus_score']    = 0
    g['combo']          = 0
    g['player_pos']     = [float(RENDER_W // 2), float(RENDER_H // 2)]
    g['player_vel']     = [0.0, 0.0]
    g['player_path']    = []
    g['scroll']         = 0.0
    g['bounce_cd']      = 0
    g['platforms']      = [[[0, RENDER_H - 1], [RENDER_W, RENDER_H - 1]]]
    g['last_point']     = [RENDER_W // 2, RENDER_H]
    g['last_place']     = 50
    g['lasers']         = []
    g['particles']      = []
    g['sparks']         = []
    g['line_effects']   = []
    g['circle_effects'] = []
    g['neon_squares']   = []
    g['shield_items']   = []
    g['shielded']       = False
    g['shield_flash']   = 0
    g['end_game']       = False
    g['is_new_best']    = False
    g['screen_shake']   = 0
    g['life_msg_timer'] = 0
    g['transition']     = 30
    g['zone_idx']          = -1
    g['zone_banner_timer'] = 0
    g['newbest_timer']  = 0
    g['best_passed']    = False
    g['game_text_loc']  = -120.0
    g['end_text_loc']   = -220.0
    g['line_color']     = (255, 255, 255)


_chosen_mode = title_screen()
screen.fill(background_color)   # clean handoff so bloom accumulation starts fresh
high_score = hs_normal if _chosen_mode == 'normal' else hs_hardcore
g = init_game(_chosen_mode)

# ---------------------------------------------------------------------------
# Pause state + pre-rendered overlay (snapshot method avoids bloom build-up)
# ---------------------------------------------------------------------------
paused          = False
pause_snapshot  = None

_pause_big    = Font(_TTF, 32, (255, 255, 255))
_pause_big_sh = Font(_TTF, 32, (0, 0, 1))
_pause_small  = Font(_TTF, 12, (200, 200, 210))

pause_overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
pause_overlay.fill((0, 0, 0, 150))
def _po_center(fnt, text, y, sh=None):
    x = SCREEN_W // 2 - fnt.width(text) // 2
    if sh is not None:
        sh.render(text, pause_overlay, (x + 2, y + 2))
    fnt.render(text, pause_overlay, (x, y))
_po_center(_pause_big,   'PAUSED',           SCREEN_H // 2 - 40, _pause_big_sh)
_po_center(_pause_small, 'P / ESC : resume', SCREEN_H // 2 + 20)
_po_center(_pause_small, 'Q : quit',         SCREEN_H // 2 + 40)

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
running = True
while running:
    # ---- PAUSE (handled before any gameplay update; freezes via snapshot) ----
    if paused:
        if pause_snapshot is None:
            pause_snapshot = screen.copy()
            pygame.mixer.music.pause()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_p, pygame.K_ESCAPE):
                    paused = False
                elif event.key == pygame.K_q:
                    running = False
        if not paused:                              # resuming this frame
            screen.blit(pause_snapshot, (0, 0))    # restore clean frame
            pause_snapshot = None
            pygame.mixer.music.unpause()
            pygame.display.update()
            mainClock.tick(FPS)
            continue
        screen.blit(pause_snapshot, (0, 0))
        screen.blit(pause_overlay, (0, 0))
        pygame.display.update()
        mainClock.tick(FPS)
        continue

    g['frame'] += 1
    frame = g['frame']

    # ---- unpack frequently used refs ----
    player_pos    = g['player_pos']
    player_vel    = g['player_vel']
    platforms     = g['platforms']
    particles     = g['particles']
    sparks        = g['sparks']
    line_effects  = g['line_effects']
    circle_effects= g['circle_effects']
    neon_squares  = g['neon_squares']

    # ---- per-frame counters ----
    if g['transition']   > 0: g['transition']    -= 1
    if g['screen_shake'] > 0: g['screen_shake']  -= 1
    if g['life_msg_timer'] > 0: g['life_msg_timer'] -= 1
    if g['newbest_timer']  > 0: g['newbest_timer']  -= 1

    # ---- scroll / line color ----
    if not g['end_game']:
        g['line_color'] = (255, 255, 255)
        if player_pos[1] - 200 < g['scroll']:
            g['scroll'] += (player_pos[1] - 200 - g['scroll']) / 10
    else:
        g['line_color'] = (190, 197, 208)
        g['scroll'] += -g['scroll'] / 100

    scroll = g['scroll']

    # ---- periodic platform cleanup (remove platforms far below visible area) ----
    if frame % 120 == 0 and len(platforms) > 10:
        cutoff = scroll + RENDER_H + 300
        platforms[:] = [p for p in platforms if min(p[0][1], p[1][1]) <= cutoff]

    # ---- platform auto-spawn ----
    if not g['end_game'] and -scroll - g['last_place'] > 50:
        if random.randint(1, 3) <= 2:
            base_y = scroll - 80
            base_x = random.randint(0, RENDER_W)
            nl = [[base_x, base_y],
                  [base_x + random.randint(0, 200) - 100,
                   base_y + random.randint(0, 100) - 50]]
            dx = nl[1][0] - nl[0][0]
            dy = nl[1][1] - nl[0][1]
            if math.sqrt(dx*dx + dy*dy) > 30:
                nl.sort()
                platforms.append(nl)
        g['last_place'] += 50

    g['game_score'] = max(g['game_score'],
                          -(player_pos[1] - RENDER_H // 2))

    # ---- final score (used everywhere for display / milestones / high score) ----
    final_score = g['score_baseline'] + int(g['game_score']) + g['bonus_score']

    # ---- milestone check: every 1000 pts ----
    #   normal   : +1 life (cap 10 total = 9 extra) + checkpoint advances
    #   hardcore : no life, no checkpoint
    while final_score >= g['next_milestone']:
        _ms = g['next_milestone']
        g['next_milestone'] += 1000
        if g['mode'] == 'normal':
            g['checkpoint'] = _ms                  # checkpoint keeps advancing
            if g['lives'] < 9:                     # cap: 9 extra + current = 10 shown
                g['lives']          += 1
                g['life_msg_timer']  = 90
                for _ in range(20):
                    a = random.randint(0, 359)
                    sparks.append(Spark(
                        list(player_pos),
                        a,
                        random.randint(7, 10) / 10,
                        6 * random.randint(5, 10) / 10,
                        (255, 220, 100)))

    # ---- live new-best detection ----
    if not g['end_game'] and not g['best_passed'] and final_score > high_score:
        g['best_passed'] = True
        g['newbest_timer'] = 100

    # ---- zone-entry banner trigger ----
    if not g['end_game']:
        _cz = zone_index(final_score)
        if _cz > g['zone_idx']:
            g['zone_idx']          = _cz
            g['zone_banner_idx']   = _cz
            g['zone_banner_timer'] = ZONE_BANNER_DUR

    # ---- clear render target ----
    display.fill(background_color)
    gui_display.fill((0, 0, 0))

    # ---- mouse in render-space ----
    mx_raw, my_raw = pygame.mouse.get_pos()
    mx = (mx_raw - BORDER_WIDTH) // 2
    my = my_raw // 2

    # ---- score-based physics scaling (mode-dependent difficulty curve) ----
    score = final_score
    if g['mode'] == 'hardcore':
        # gravity & fall speed climb higher and faster → progressively harder
        player_gravity           = min(0.30, 0.05 + score / 22000)
        player_terminal_velocity = min(6.0,  1    + score / 2400)
        bounce_strength          = min(2.5,  1    + score / 8000)
    else:
        player_gravity           = min(0.19, 0.05 + score / 30000)
        player_terminal_velocity = min(4.0,  1    + score / 3000)
        bounce_strength          = min(2.5,  1    + score / 8000)

    # =======================================================================
    # NEON SQUARE EFFECTS (spawned in world space, composited additive)
    # =======================================================================
    if not g['end_game'] and random.randint(1, 90) == 1:
        neon_squares.append([
            random.uniform(0, RENDER_W),        # x
            scroll - 60,                         # y (world, starts above view)
            random.uniform(0, 360),              # angle (deg)
            random.randint(20, 50),              # size (half-diagonal)
            0,                                   # age
            random.randint(200, 350),            # max_age
            random.uniform(-0.3, 0.3),           # rot_speed (deg/frame)
            random.uniform(-0.15, 0.15),         # vx drift
            random.uniform(-0.4, -0.15),         # vy (float upward)
            random.randint(0, 1),                # color index
        ])

    # =======================================================================
    # LINE EFFECTS
    # =======================================================================
    line_effects = [le for le in line_effects
                    if not le.update(display, scroll)]

    # =======================================================================
    # CIRCLE EFFECTS
    # =======================================================================
    circle_effects = [ce for ce in circle_effects
                      if not ce.update(display, scroll)]

    # =======================================================================
    # SPARKS
    # =======================================================================
    sparks = [sp for sp in sparks if not sp.update(display, scroll)]

    # =======================================================================
    # PLAYER PREVIEW LINE + PATH
    # =======================================================================
    if not g['end_game']:
        pygame.draw.line(display, line_placing_color,
                         [g['last_point'][0], g['last_point'][1] - scroll],
                         [mx, my])

    g['player_path'] = g['player_path'][-50:]
    if len(g['player_path']) > 2:
        path_screen = [[v[0], v[1] - scroll] for v in g['player_path']]
        pygame.draw.lines(display, line_placing_color, False, path_screen)

    # =======================================================================
    # LASERS (score > 600)  format: [lx, width, timer]
    # =======================================================================
    if score > 600:
        if not g['lasers'] and random.randint(1, 900) == 1:
            g['lasers'].append([random.randint(40, RENDER_W - 40),
                                random.randint(44, 70), 20])

        alive_lasers = []
        for laser in g['lasers']:
            lx, lw, lt = laser[0], laser[1], laser[2]
            half    = lw / 2
            left_x  = lx - half
            right_x = lx + half

            # charge intensity: brightens + flickers toward explosion
            progress  = max(0.0, min(1.0, (lt - 20) / 160.0))
            flicker   = 0.5 + 0.5 * math.sin(lt * 0.5)
            intensity = 0.20 + 0.65 * progress + 0.15 * flicker
            lc = laser_color
            draw_color = (min(255, int(lc[0] * intensity * 1.4)),
                          min(255, int(lc[1] * intensity * 1.4)),
                          min(255, int(lc[2] * intensity * 1.4)))
            line_w = 2 if intensity > 0.75 else 1

            # danger-zone boundary lines (left + right edges of the band)
            pygame.draw.line(display, draw_color,
                             (int(left_x), 0), (int(left_x), RENDER_H), line_w)
            pygame.draw.line(display, draw_color,
                             (int(right_x), 0), (int(right_x), RENDER_H), line_w)

            # converging warning lines (comb sweep, edges → center) + charge sound
            if lt % 12 == 0 and lt < 170:
                _ty = scroll
                _by = scroll + RENDER_H
                line_effects.append(LineEffect(
                    [[left_x,  _ty], [left_x,  _by]],
                    [[lx,      _ty], [lx,      _by]], laser_color, 6, 14))
                line_effects.append(LineEffect(
                    [[right_x, _ty], [right_x, _by]],
                    [[lx,      _ty], [lx,      _by]], laser_color, 6, 14))
                if laser_charge_s: laser_charge_s.play()

            laser[2] += 1

            if lt > 180:
                if laser_explode_s: laser_explode_s.play()
                # hitbox: full band width (matches the visible danger zone)
                if left_x < player_pos[0] < right_x:
                    player_vel[0] += 4 if player_pos[0] > lx else -4
                    for _ in range(30):
                        sparks.append(Spark(
                            list(player_pos),
                            random.randint(0, 359),
                            random.randint(7, 10) / 10 * 3,
                            9 * random.randint(5, 10) / 10,
                            (170, 170, 170)))
                        a = random.randint(0, 359)
                        s = random.randint(20, 50) / 10
                        particles.append(Particle(
                            list(player_pos), 'p',
                            [math.cos(math.radians(a)) * s,
                             math.sin(math.radians(a)) * s],
                            5, frame, (170, 170, 170)))
                    g['screen_shake'] = 8

                # explosion particles spread across the band
                for _ in range(300):
                    side = 1 if random.randint(0, 1) == 0 else -1
                    pv = [side * (4 + random.randint(0, 20) / 10),
                          random.randint(0, 10) / 10 - 3]
                    py = random.randint(0, RENDER_H + 30) + scroll - 30
                    px = random.uniform(left_x, right_x)
                    particles.append(Particle(
                        [px, py], 'p', pv, 5, frame, (160, 40, 80)))
                # laser expired — don't keep
            else:
                alive_lasers.append(laser)
        g['lasers'] = alive_lasers

    # =======================================================================
    # SHIELD PICKUPS  (collect → one-time wall save)  format: [x, world_y]
    # =======================================================================
    if (not g['end_game'] and not g['shielded'] and not g['shield_items']
            and score > 300 and random.randint(1, 600) == 1):
        g['shield_items'].append([random.uniform(40, RENDER_W - 40), scroll - 60])

    for it in g['shield_items'][:]:
        _dx = player_pos[0] - it[0]
        _dy = player_pos[1] - it[1]
        if (not g['end_game']) and (_dx * _dx + _dy * _dy < (PICKUP_R + 5) ** 2):
            g['shielded'] = True
            g['shield_items'].remove(it)
            for _ in range(18):
                sparks.append(Spark(list(player_pos), random.randint(0, 359),
                              random.randint(7, 10) / 10 * 1.5,
                              7 * random.randint(5, 10) / 10, SHIELD_COLOR))
            continue
        if it[1] - scroll > RENDER_H + 60:
            g['shield_items'].remove(it)
            continue
        _ox, _oy = int(it[0]), int(it[1] - scroll)
        if pickup_img is not None:
            _pd = max(4, (PICKUP_R + int(1.5 * math.sin(frame * 0.2))) * 2)
            _ps = pygame.transform.smoothscale(pickup_img, (_pd, _pd))
            display.blit(_ps, (_ox - _pd // 2, _oy - _pd // 2))
        else:
            _op = PICKUP_R + int(1.5 * math.sin(frame * 0.2))
            pygame.draw.circle(display, SHIELD_COLOR, (_ox, _oy), _op, 1)
            pygame.draw.circle(display, SHIELD_COLOR, (_ox, _oy), 2)

    # =======================================================================
    # PLATFORMS  (draw + ambient sparks)
    # =======================================================================
    for plat in platforms:
        y_min = min(plat[0][1], plat[1][1])
        y_max = max(plat[0][1], plat[1][1])
        if y_min > scroll + RENDER_H + 20:
            continue
        if y_max < scroll - 20:
            continue
        p0s = [plat[0][0], plat[0][1] - scroll]
        p1s = [plat[1][0], plat[1][1] - scroll]
        pygame.draw.line(display, g['line_color'], p0s, p1s, LINE_WIDTH)
        pygame.draw.circle(display, g['line_color'],
                           [int(p0s[0]), int(p0s[1])], 6, 2)
        pygame.draw.circle(display, g['line_color'],
                           [int(p1s[0]), int(p1s[1])], 6, 2)
        if random.randint(0, 10) == 0:
            c = random.randint(150, 220)
            sparks.append(Spark(
                list(random.choice(plat)),
                random.randint(0, 359),
                random.randint(7, 10) / 10,
                5 * random.randint(5, 10) / 10,
                (c, c, c)))

    # =======================================================================
    # PLAYER PHYSICS + BOUNCE
    # =======================================================================
    if not g['end_game']:
        # trail particle — heats up (aqua→gold) & thickens with combo
        _cm = combo_mult(g['combo'])
        _heat = (_cm - 1) / 4.0                      # 0 at x1 … 1 at x5
        _tc = (int(45  + (255 - 45)  * _heat),       # aqua → warm gold
               int(226 + (170 - 226) * _heat),
               int(230 + (60  - 230) * _heat))
        for _ in range(_cm):                          # 1 particle at x1 … 5 at x5
            particles.append(Particle(
                list(player_pos), 'p',
                [random.randint(0, 20)/40 - 0.25,
                 random.randint(0, 10)/15 - 1],
                5, frame, _tc))

        line_locations = check_line_sides(platforms, player_pos)
        start_pos = list(player_pos)

        player_vel[1] = min(player_terminal_velocity,
                            player_vel[1] + player_gravity)
        _spd = dis_func(player_vel)
        if _spd > MAX_SPEED:
            player_vel[0] *= MAX_SPEED / _spd
            player_vel[1] *= MAX_SPEED / _spd
        player_pos[0] += player_vel[0]
        player_pos[1] += player_vel[1]
        player_vel[1]  = normalize(player_vel[1], 0.02)

        g['player_path'].append(list(player_pos))

        if g['bounce_cd'] > 0:
            g['bounce_cd'] -= 1
    else:
        line_locations = check_line_sides(platforms, player_pos)

    line_locations_post = check_line_sides(platforms, player_pos)
    for i, side in enumerate(line_locations):
        if sign_func(side) != sign_func(line_locations_post[i]):
            if sign_func(side) == -1:
                if doIntersect([start_pos if not g['end_game'] else player_pos,
                                player_pos], platforms[i]):
                    if 0 < player_pos[0] < RENDER_W:
                        if g['bounce_cd'] == 0:
                            if bounce_s: bounce_s.play()
                            ang = math.atan2(
                                platforms[i][1][1] - platforms[i][0][1],
                                platforms[i][1][0] - platforms[i][0][0])
                            normal = ang - math.pi * 0.5
                            vel_ang = math.degrees(
                                math.atan2(-player_vel[1], -player_vel[0]))
                            b_ang = math.radians(
                                mirror_angle(vel_ang, math.degrees(normal)) % 360)
                            spd = dis_func(player_vel) + 1
                            player_vel[0] = math.cos(b_ang) * spd
                            player_vel[1] = math.sin(b_ang) * spd
                            player_vel[1] -= 2 * bounce_strength
                            _spd = dis_func(player_vel)
                            if _spd > MAX_SPEED:
                                player_vel[0] *= MAX_SPEED / _spd
                                player_vel[1] *= MAX_SPEED / _spd
                            for _ in range(random.randint(4, 6)):
                                sa = math.degrees(normal) + random.randint(0, 180) - 90
                                sparks.append(Spark(
                                    list(player_pos), sa,
                                    spd / 3 * random.randint(7, 10) / 10,
                                    spd * 2 * random.randint(5, 10) / 10,
                                    (232, 211, 232)))
                            g['bounce_cd'] = 3
                            # combo accumulation
                            g['combo'] += 1
                            mult = combo_mult(g['combo'])
                            g['bonus_score'] += 10 * mult
                            # combo-scaled bounce burst (bigger & warmer with the streak)
                            _hb = (mult - 1) / 4.0
                            _bc = (int(45  + (255 - 45)  * _hb),
                                   int(226 + (170 - 226) * _hb),
                                   int(230 + (60  - 230) * _hb))
                            for _ in range(4 + mult * 3):       # 7 sparks at x1 … 19 at x5
                                sparks.append(Spark(
                                    list(player_pos), random.randint(0, 359),
                                    random.randint(7, 10) / 10 * (1 + _hb),
                                    6 * random.randint(5, 10) / 10, _bc))

    # =======================================================================
    # DEATH CHECK
    # =======================================================================
    if not g['end_game']:
        if player_pos[0] < 0 or player_pos[0] > RENDER_W:
            if g['shielded']:
                g['shielded'] = False
                g['shield_flash'] = 18
                if player_pos[0] < 0:
                    player_pos[0] = 1
                    player_vel[0] = abs(player_vel[0])
                else:
                    player_pos[0] = RENDER_W - 1
                    player_vel[0] = -abs(player_vel[0])
                if bounce_s: bounce_s.play()
                g['screen_shake'] = 6
                for _ in range(22):
                    sparks.append(Spark(list(player_pos), random.randint(0, 359),
                                  random.randint(7, 10) / 10 * 2,
                                  8 * random.randint(5, 10) / 10, SHIELD_COLOR))
            else:
                if death_s: death_s.play()
                circle_effects.append(CircleEffect(
                    list(player_pos), 6, [6, 0.15], [10, 0.2], laser_color))
                circle_effects.append(CircleEffect(
                    list(player_pos), 6, [6, 0.05], [5, 0.04],  laser_color))
                g['screen_shake'] = 12
                g['end_game'] = True
                g['combo'] = 0
                g['player_path'] = []
                # recalc final score at death moment
                death_final = g['score_baseline'] + int(g['game_score']) + g['bonus_score']
                if death_final > high_score:
                    high_score = death_final
                    if g['mode'] == 'normal':
                        hs_normal = high_score
                    else:
                        hs_hardcore = high_score
                    save_high_score(high_score, g['mode'])
                    g['is_new_best'] = True

    # =======================================================================
    # DRAW PLAYER
    # =======================================================================
    if high_score > 0:
        _bsy = int(RENDER_H // 2 - high_score - scroll)
        if 0 <= _bsy <= RENDER_H:
            alpha_line(display, (255, 200, 60, 60), [0, _bsy], [RENDER_W, _bsy])
    pygame.draw.circle(display, player_color,
                       (int(player_pos[0]), int(player_pos[1] - scroll)), 4)

    if g['shielded'] or g['shield_flash'] > 0:
        _rr = 8 + int(1.5 * math.sin(frame * 0.25))
        if g['shield_flash'] > 0:
            g['shield_flash'] -= 1
            _rr += (18 - g['shield_flash'])
        _cx, _cy = int(player_pos[0]), int(player_pos[1] - scroll)
        if shield_img is not None:
            _d = max(2, _rr * 2)
            _sp = pygame.transform.smoothscale(shield_img, (_d, _d))
            display.blit(_sp, (_cx - _d // 2, _cy - _d // 2))
        else:
            pygame.draw.circle(display, SHIELD_COLOR, (_cx, _cy), _rr, 1)

    # =======================================================================
    # PARTICLES
    # =======================================================================
    particles = [p for p in particles
                 if not p.update(display, frame, offset=(0, scroll))]

    # write back mutated lists
    g['particles']      = particles
    g['sparks']         = sparks
    g['line_effects']   = line_effects
    g['circle_effects'] = circle_effects

    # =======================================================================
    # UI  (drawn on gui_display)
    # =======================================================================
    score_str = str(final_score)
    best_str  = 'best: ' + str(high_score)
    gtl = g['game_text_loc']
    etl = g['end_text_loc']

    # -- in-game HUD (top-left) --
    font2.render('score: ' + score_str, gui_display, (int(gtl) + 2, 6))
    font2.render(best_str,              gui_display, (int(gtl) + 2, 16))
    font2.render('lives: ' + str(g['lives'] + 1), gui_display, (int(gtl) + 2, 26))
    font.render('score: ' + score_str,  gui_display, (int(gtl), 4))
    font.render(best_str,               gui_display, (int(gtl), 14))
    font.render('lives: ' + str(g['lives'] + 1), gui_display, (int(gtl), 24))
    if g['mode'] == 'hardcore':
        font2.render('HARDCORE', gui_display, (int(gtl) + 2, 36))
        font.render('HARDCORE',  gui_display, (int(gtl), 34))
    if muted:
        _mw = font.width('MUTED')
        font2.render('MUTED', gui_display, (RENDER_W - _mw - 3, 6))
        font.render('MUTED', gui_display, (RENDER_W - _mw - 4, 4), color=(255, 80, 80))

    # -- death / continue screen (center) --
    if g['lives'] > 0:
        # continue screen
        cont_str  = 'CONTINUE?'
        lives_str = 'lives: ' + str(g['lives'] + 1)
        font2.render(cont_str,  gui_display,
                     (RENDER_W // 2 - font.width(cont_str)  // 2 + 2, int(etl) + 2))
        font2.render(lives_str, gui_display,
                     (RENDER_W // 2 - font.width(lives_str) // 2 + 2, int(etl) + 14))
        font2.render('press R', gui_display,
                     (RENDER_W // 2 - font.width('press R') // 2 + 2, int(etl) + 26))
        font.render(cont_str,  gui_display,
                    (RENDER_W // 2 - font.width(cont_str)  // 2, int(etl)))
        font.render(lives_str, gui_display,
                    (RENDER_W // 2 - font.width(lives_str) // 2, int(etl) + 12))
        font.render('press R', gui_display,
                    (RENDER_W // 2 - font.width('press R') // 2, int(etl) + 24))
        font2.render('ESC: title', gui_display,
                     (RENDER_W // 2 - font.width('ESC: title') // 2 + 2, int(etl) + 38))
        font.render('ESC: title', gui_display,
                    (RENDER_W // 2 - font.width('ESC: title') // 2, int(etl) + 36))
    else:
        # game over screen
        over_str = 'GAME OVER'
        font2.render(over_str,   gui_display,
                     (RENDER_W // 2 - font.width(over_str)  // 2 + 2, int(etl) + 2))
        font2.render(score_str,  gui_display,
                     (RENDER_W // 2 - font.width(score_str) // 2 + 2, int(etl) + 14))
        font2.render(best_str,   gui_display,
                     (RENDER_W // 2 - font.width(best_str)  // 2 + 2, int(etl) + 26))
        if g['is_new_best']:
            font2.render('NEW BEST!', gui_display,
                         (RENDER_W // 2 - font.width('NEW BEST!') // 2 + 2, int(etl) + 38))
        font2.render('press R', gui_display,
                     (RENDER_W // 2 - font.width('press R') // 2 + 2, int(etl) + 50))
        font.render(over_str,   gui_display,
                    (RENDER_W // 2 - font.width(over_str)  // 2, int(etl)))
        font.render(score_str,  gui_display,
                    (RENDER_W // 2 - font.width(score_str) // 2, int(etl) + 12))
        font.render(best_str,   gui_display,
                    (RENDER_W // 2 - font.width(best_str)  // 2, int(etl) + 24))
        if g['is_new_best']:
            font.render('NEW BEST!', gui_display,
                        (RENDER_W // 2 - font.width('NEW BEST!') // 2, int(etl) + 36))
        font.render('press R', gui_display,
                    (RENDER_W // 2 - font.width('press R') // 2, int(etl) + 48))
        if g['mode'] == 'hardcore':
            font2.render('HARDCORE', gui_display,
                         (RENDER_W // 2 - font.width('HARDCORE') // 2 + 2, int(etl) + 62))
            font.render('HARDCORE', gui_display,
                        (RENDER_W // 2 - font.width('HARDCORE') // 2, int(etl) + 60),
                        color=(190, 40, 100))
        font2.render('ESC: title', gui_display,
                     (RENDER_W // 2 - font.width('ESC: title') // 2 + 2, int(etl) + 78))
        font.render('ESC: title', gui_display,
                    (RENDER_W // 2 - font.width('ESC: title') // 2, int(etl) + 76))

    # -- combo indicator near player (escalates with the streak) --
    if not g['end_game'] and g['combo'] >= 2:
        mult = combo_mult(g['combo'])
        cx = int(player_pos[0]) + 8
        cy = int(player_pos[1] - scroll) - 10
        combo_str = 'x' + str(mult)
        if mult >= 4:                                # x4 / x5 : big, warm, pulsing
            _cp = 1 if (frame // 6) % 2 == 0 else 0
            combo_big_sh.render(combo_str, gui_display, (cx + 1, cy - 4 + 1 - _cp))
            combo_big.render(combo_str,    gui_display, (cx,     cy - 4 - _cp))
        else:
            font2.render(combo_str, gui_display, (cx + 1, cy + 1))
            font.render(combo_str,  gui_display, (cx, cy))

    # -- +1 LIFE flash --
    if g['life_msg_timer'] > 0:
        font2.render('+1 LIFE', gui_display,
                     (RENDER_W // 2 - font.width('+1 LIFE') // 2 + 2,
                      int(player_pos[1] - scroll) - 22))
        font.render('+1 LIFE', gui_display,
                    (RENDER_W // 2 - font.width('+1 LIFE') // 2,
                     int(player_pos[1] - scroll) - 24))

    # -- NEW BEST! live flash --
    if g['newbest_timer'] > 0:
        font2.render('NEW BEST!', gui_display,
                     (RENDER_W // 2 - font.width('NEW BEST!') // 2 + 2,
                      int(player_pos[1] - scroll) - 36))
        font.render('NEW BEST!', gui_display,
                    (RENDER_W // 2 - font.width('NEW BEST!') // 2,
                     int(player_pos[1] - scroll) - 38))

    # animate text positions
    if g['end_game']:
        g['game_text_loc'] += (-120 - gtl) / 20
        g['end_text_loc']  += (200  - etl) / 20
    else:
        g['game_text_loc'] += (6    - gtl) / 10
        g['end_text_loc']  += (-220 - etl) / 20

    # =======================================================================
    # EVENTS
    # =======================================================================
    _do_continue = False
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if g['end_game']:
                    _chosen_mode = title_screen()
                    screen.fill(background_color)
                    high_score = hs_normal if _chosen_mode == 'normal' else hs_hardcore
                    g = init_game(_chosen_mode)
                    paused = False
                    pause_snapshot = None
                    display.fill(background_color)
                    gui_display.fill((0, 0, 0))
                    _do_continue = True
                    break
                else:
                    paused = True           # ESC now pauses during play
            if event.key == pygame.K_p and not g['end_game']:
                paused = True
            if event.key == pygame.K_m:
                set_muted(not muted)
            if event.key == pygame.K_r and g['end_game']:
                if restart_s: restart_s.play()
                if g['lives'] > 0:
                    continue_game(g)
                    screen.fill(background_color)
                else:
                    g = init_game(g['mode'])
                    screen.fill(background_color)
                display.fill(background_color)
                gui_display.fill((0, 0, 0))
                _do_continue = True
                break

        if event.type == pygame.ACTIVEEVENT:
            if event.state & 2 and not event.gain and not g['end_game']:
                paused = True

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and not g['end_game']:
                _new_pt = [mx, my + scroll]
                _dx = _new_pt[0] - g['last_point'][0]
                _dy = _new_pt[1] - g['last_point'][1]
                if math.sqrt(_dx*_dx + _dy*_dy) >= 10:
                    line = [g['last_point'], _new_pt]
                    line.sort()
                    g['platforms'].append(line)
                    g['last_point'] = _new_pt
                    g['circle_effects'].append(CircleEffect(
                        [mx, my + scroll], 4, [4, 0.2], [4, 0.3], (255, 255, 255)))
                    if place_s: place_s.play()
                g['combo'] = 0

    if _do_continue:
        pygame.display.update()
        mainClock.tick(FPS)
        continue

    # =======================================================================
    # BLOOM COMPOSITE  (do not reorder)
    # =======================================================================
    shake_x = random.randint(-5, 5) if g['screen_shake'] > 0 else 0
    shake_y = random.randint(-5, 5) if g['screen_shake'] > 0 else 0

    # 1. Fuzzy bloom halo
    display_bg = display.copy()
    display_bg.set_alpha(25)
    screen.blit(
        pygame.transform.scale(display_bg, (RENDER_W*2+40, RENDER_H*2+40)),
        (-20 + BORDER_WIDTH, 0))

    # 2. Image veil → fades previous frames toward background image
    _bzone, _bt = bg_zone_alpha(final_score)
    _yoff = max(0, min(_IMG_EXTRA, int(-scroll * 0.005)))
    veil_surf.fill((0, 0, 0))
    _img_cur = bg_images[_bzone]
    if _img_cur:
        veil_surf.blit(_img_cur, (0, -_yoff))
    else:
        veil_surf.fill(background_color)
    if _bt > 0:
        _img_nxt = bg_images[min(_bzone + 1, 4)]
        if _img_nxt:
            cross_surf.blit(_img_nxt, (0, 0))
            cross_surf.set_alpha(int(_bt * 255))
            veil_surf.blit(cross_surf, (0, -_yoff))
    screen.blit(veil_surf, (0, 0))

    # 2.5. Neon squares (world-space, BLEND_ADD — above bg, below gameplay)
    sq_surf.fill((0, 0, 0, 0))
    surviving_sq = []
    for sq in neon_squares:
        sq[0] += sq[7]   # x += vx
        sq[1] += sq[8]   # y += vy
        sq[2] += sq[6]   # angle += rot_speed
        sq[4] += 1        # age++
        if sq[4] >= sq[5]:
            continue
        fade = math.sin(sq[4] / sq[5] * math.pi)
        a = int(40 * fade)
        if a > 0:
            col = _NEON_SQ_COLORS[sq[9]]
            half = sq[3] / 2
            rad = math.radians(sq[2])
            ca, sa = math.cos(rad), math.sin(rad)
            sx, sy = sq[0], sq[1] - scroll
            pts = [(int(sx + (dx*ca - dy*sa)*half),
                    int(sy + (dx*sa + dy*ca)*half))
                   for dx, dy in ((-1,-1),(1,-1),(1,1),(-1,1))]
            pygame.draw.polygon(sq_surf, (*col, a), pts, 1)
        surviving_sq.append(sq)
    neon_squares[:] = surviving_sq
    g['neon_squares'] = neon_squares
    screen.blit(
        pygame.transform.scale(sq_surf, (RENDER_W * 2, RENDER_H * 2)),
        (BORDER_WIDTH, 0), special_flags=pygame.BLEND_ADD)

    # 3. Sharp display (background_color is transparent via colorkey)
    screen.blit(
        pygame.transform.scale(display, (RENDER_W*2, RENDER_H*2)),
        (BORDER_WIDTH + shake_x, shake_y))

    # 4. GUI overlay (no shake)
    screen.blit(
        pygame.transform.scale(gui_display, (RENDER_W*2, RENDER_H*2)),
        (BORDER_WIDTH, 0))

    # 5. Divider lines at play boundary (x=70, x=620)
    screen.blit(divider_surf, (0, 0))

    # 5.6. Edge-proximity warning (red vignette; scales with closeness, no build-up)
    if not g['end_game']:
        _px = player_pos[0]
        _li = min(1.0, max(0.0, (WARN_DIST - _px) / WARN_DIST))
        _ri = min(1.0, max(0.0, (_px - (RENDER_W - WARN_DIST)) / WARN_DIST))
        if _li > 0.01:
            _sv = vig_left.copy()
            _sv.fill((255, 255, 255, int(255 * _li)), special_flags=pygame.BLEND_RGBA_MULT)
            screen.blit(_sv, (BORDER_WIDTH, 0))
        if _ri > 0.01:
            _sv = vig_right.copy()
            _sv.fill((255, 255, 255, int(255 * _ri)), special_flags=pygame.BLEND_RGBA_MULT)
            screen.blit(_sv, (SCREEN_W - BORDER_WIDTH - _WARN_W, 0))

    # 5.5. Zone-entry banner — redrawn fresh each frame (no bloom build-up)
    if g['zone_banner_timer'] > 0:
        g['zone_banner_timer'] -= 1
        _tl = g['zone_banner_timer']
        if _tl > ZONE_BANNER_DUR - 20:
            _ba = (ZONE_BANNER_DUR - _tl) / 20.0
        elif _tl < 40:
            _ba = _tl / 40.0
        else:
            _ba = 1.0
        _ba = max(0.0, min(1.0, _ba))
        _zname = ZONE_NAMES[g['zone_banner_idx']]
        zone_banner_surf.fill((0, 0, 0))
        _x1 = SCREEN_W // 2 - zb_small.width('ENTERING') // 2
        zb_small_sh.render('ENTERING', zone_banner_surf, (_x1 + 2, 4))
        zb_small.render(   'ENTERING', zone_banner_surf, (_x1,     2))
        _x2 = SCREEN_W // 2 - zb_big.width(_zname) // 2
        zb_big_sh.render(_zname, zone_banner_surf, (_x2 + 2, 26))
        zb_big.render(   _zname, zone_banner_surf, (_x2,     24))
        zone_banner_surf.set_alpha(int(255 * _ba))
        screen.blit(zone_banner_surf, (0, SCREEN_H // 2 - 130))

    # 6. Fade-in transition
    if g['transition'] > 0:
        _transition_surf.set_alpha(int(255 * g['transition'] / 30))
        screen.blit(_transition_surf, (0, 0))

    pygame.display.update()
    mainClock.tick(FPS)

pygame.quit()
sys.exit()
