"""
██╗     ██╗██████╗ ██████╗  █████╗ ██████╗ ██╗   ██╗
██║     ██║██╔══██╗██╔══██╗██╔══██╗██╔══██╗╚██╗ ██╔╝
██║     ██║██████╔╝██████╔╝███████║██████╔╝ ╚████╔╝
██║     ██║██╔══██╗██╔══██╗██╔══██╗██╔══██╗  ╚██╔╝
███████╗██║██████╔╝██║  ██║██║  ██║██║  ██║   ██║
╚══════╝╚═╝╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝
          E S C A P E   /  도서관 탈출  /  공포 게임

Controls:
  WASD / Arrow keys - Move
  1~9,0 - Select hotbar slot
  E - Interact / Pick up item
  F - Use lighter (toggle light)
  ESC - Pause / Menu
"""

import pygame, sys, math, random, os, time

# ─────────────────────────── PATHS ─────────────────────────────
ASSET_DIR = os.path.join(os.path.dirname(__file__), "assets")

pygame.init()
pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)

# ─────────────────────────── CONSTANTS ──────────────────────────
SCREEN_W, SCREEN_H = 1024, 768
TILE = 64
HB_HEIGHT = 80   # hotbar height
PLAY_H = SCREEN_H - HB_HEIGHT
FPS = 60

# Colours
BLACK  = (0, 0, 0)
WHITE  = (255, 255, 255)
RED    = (200, 0, 0)
DKRED  = (120, 0, 0)
GREEN  = (0, 200, 0)
AMBER  = (255, 160, 0)
GREY   = (80, 80, 80)
DKGREY = (30, 30, 35)
BLOOD  = (140, 0, 0)

# Map tile types
T_FLOOR  = 0
T_WALL   = 1
T_BOOK   = 2
T_TABLE  = 3
T_DOOR   = 4   # locked exit
T_EXIT   = 5   # open exit

GLITCH_CHARS = "▓▒░█▄▀╬╫╪▲▼◄►◀▶§¶†‡«»±×÷∞∩∪∅∆∇∈∉∋∌∏∑√∫≈≠≡≤≥⌠⌡"

# ─────────────────────────── ASSET LOADER ───────────────────────
_cache = {}
def load(name, size=None):
    key = (name, size)
    if key in _cache:
        return _cache[key]
    path = os.path.join(ASSET_DIR, name)
    try:
        img = pygame.image.load(path).convert_alpha()
    except:
        img = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
        img.fill((255, 0, 255, 180))
    if size:
        img = pygame.transform.smoothscale(img, size)
    _cache[key] = img
    return img

# ─────────────────────────── SOUND GEN ──────────────────────────
def make_noise(freq=440, dur=0.15, vol=0.3, wave='square'):
    sr = 22050
    n  = int(sr * dur)
    buf = bytearray(n * 2)
    for i in range(n):
        t   = i / sr
        fade = min(1.0, (n - i) / (sr * 0.05))
        if wave == 'square':
            v = 1 if (i * freq / sr % 1) < 0.5 else -1
        elif wave == 'noise':
            v = random.uniform(-1, 1)
        elif wave == 'sine':
            v = math.sin(2 * math.pi * freq * t)
        else:
            v = 0
        sample = int(v * vol * fade * 32767)
        sample = max(-32768, min(32767, sample))
        buf[i*2]   = sample & 0xFF
        buf[i*2+1] = (sample >> 8) & 0xFF
    sound = pygame.sndarray.make_sound(
        pygame.sndarray.array(pygame.mixer.Sound(buffer=bytes(buf)))
    )
    return sound

def gen_sounds():
    sounds = {}
    # heartbeat - low thump
    def heartbeat():
        sr = 22050; dur = 0.12; n = int(sr*dur)
        buf = bytearray(n*2)
        for i in range(n):
            env = math.exp(-i/(sr*0.04))
            v   = math.sin(2*math.pi*60*(i/sr)) * env
            s   = int(v*0.6*32767); s = max(-32768,min(32767,s))
            buf[i*2]=s&0xFF; buf[i*2+1]=(s>>8)&0xFF
        return pygame.mixer.Sound(buffer=bytes(buf))

    # lighter click
    def lighter_click():
        sr=22050; dur=0.08; n=int(sr*dur)
        buf=bytearray(n*2)
        for i in range(n):
            env=math.exp(-i/(sr*0.01))
            v=random.uniform(-1,1)*env
            s=int(v*0.5*32767); s=max(-32768,min(32767,s))
            buf[i*2]=s&0xFF; buf[i*2+1]=(s>>8)&0xFF
        return pygame.mixer.Sound(buffer=bytes(buf))

    # pickup jingle
    def pickup():
        sr=22050; dur=0.2; n=int(sr*dur)
        buf=bytearray(n*2)
        for i in range(n):
            env=min(1.0,(n-i)/(sr*0.05))
            v=math.sin(2*math.pi*880*(i/sr))*env*0.4+math.sin(2*math.pi*1320*(i/sr))*env*0.3
            s=int(v*32767); s=max(-32768,min(32767,s))
            buf[i*2]=s&0xFF; buf[i*2+1]=(s>>8)&0xFF
        return pygame.mixer.Sound(buffer=bytes(buf))

    # jumpscare screech
    def screech():
        sr=22050; dur=0.8; n=int(sr*dur)
        buf=bytearray(n*2)
        for i in range(n):
            env=math.exp(-i/(sr*0.3))
            freq=800+random.uniform(-200,800)
            v=math.sin(2*math.pi*freq*(i/sr))*env+random.uniform(-0.3,0.3)*env
            s=int(v*0.7*32767); s=max(-32768,min(32767,s))
            buf[i*2]=s&0xFF; buf[i*2+1]=(s>>8)&0xFF
        return pygame.mixer.Sound(buffer=bytes(buf))

    # ambient drone
    def drone():
        sr=22050; dur=3.0; n=int(sr*dur)
        buf=bytearray(n*2)
        for i in range(n):
            t=i/sr
            v=math.sin(2*math.pi*55*t)*0.15+math.sin(2*math.pi*110*t)*0.08+random.uniform(-0.02,0.02)
            s=int(v*32767); s=max(-32768,min(32767,s))
            buf[i*2]=s&0xFF; buf[i*2+1]=(s>>8)&0xFF
        return pygame.mixer.Sound(buffer=bytes(buf))

    try:
        sounds['heartbeat']   = heartbeat()
        sounds['lighter']     = lighter_click()
        sounds['pickup']      = pickup()
        sounds['screech']     = screech()
        sounds['drone']       = drone()
    except:
        pass
    return sounds

# ─────────────────────────── MAP ────────────────────────────────
# 0=floor, 1=wall, 2=bookcase, 3=table, 4=locked door, 5=exit
MAP_DATA = [
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
    [1,0,0,0,1,0,0,0,0,0,0,0,1,0,0,1],
    [1,0,2,0,1,0,2,2,0,2,2,0,1,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,2,0,1,0,2,0,0,0,2,0,1,0,2,1],
    [1,0,0,0,1,0,0,0,0,0,0,0,1,0,0,1],
    [1,1,0,1,1,0,0,3,3,0,0,0,1,0,0,1],
    [1,0,0,0,0,0,0,3,3,0,0,0,0,0,0,1],
    [1,0,2,0,1,0,0,0,0,0,0,0,1,0,2,1],
    [1,0,0,0,0,0,2,0,0,2,0,0,0,0,0,1],
    [1,0,2,0,1,0,0,0,0,0,0,0,1,0,0,1],
    [1,0,0,0,0,0,3,3,3,3,0,0,0,0,0,1],
    [1,1,0,1,1,0,0,0,0,0,0,0,1,0,0,1],
    [1,0,0,0,1,0,2,2,0,2,2,0,1,0,0,1],
    [1,0,2,0,0,0,0,0,0,0,0,0,0,0,2,1],
    [1,1,4,1,1,1,1,1,1,1,1,1,1,1,1,1],
]
ROWS = len(MAP_DATA)
COLS = len(MAP_DATA[0])

# Item positions: (row, col) -> item_type
ITEMS_INIT = {
    (2, 7):  'torch',
    (4, 9):  'map_item',
    (7, 2):  'lighter',
    (9, 12): 'torch',
    (11,4):  'map_item',
    (13,10): 'key',
    (3, 13): 'torch',
    (5, 5):  'map_item',
}
# Key must be collected to open door at row=15, col=2

# Ghost patrol paths: list of (row, col) waypoints
GHOST_PATHS = [
    [(2,1),(2,3),(4,3),(4,1)],
    [(8,6),(8,9),(11,9),(11,6)],
    [(2,9),(2,14),(5,14),(5,9)],
]
SHADOW_PATHS = [
    [(6,2),(12,2),(12,4),(6,4)],
    [(6,9),(6,14),(12,14),(12,9)],
]

# ─────────────────────────── GLITCH TEXT ─────────────────────────
class GlitchText:
    def __init__(self):
        self.messages = []

    def add(self, text, x, y, dur=2.5, color=RED, size=28, glitch=True):
        self.messages.append({
            'text': text, 'x': x, 'y': y,
            'dur': dur, 'timer': 0, 'color': color,
            'size': size, 'glitch': glitch
        })

    def update(self, dt):
        self.messages = [m for m in self.messages if m['timer'] < m['dur']]
        for m in self.messages:
            m['timer'] += dt

    def draw(self, surf, fonts):
        for m in self.messages:
            ratio = m['timer'] / m['dur']
            alpha = int(255 * (1 - ratio**2))
            font = pygame.font.SysFont('Courier New', m['size'], bold=True)
            text = m['text']
            # glitch effect: randomly corrupt chars
            if m['glitch'] and random.random() < 0.3:
                lst = list(text)
                for _ in range(random.randint(1, 3)):
                    i = random.randint(0, len(lst)-1)
                    lst[i] = random.choice(GLITCH_CHARS)
                text = ''.join(lst)
            # chromatic aberration: draw 3x with offset
            for dx, dy, col in [(-2,0,(255,0,0)),(2,0,(0,0,255)),(0,0,m['color'])]:
                s = font.render(text, True, col)
                s.set_alpha(alpha)
                surf.blit(s, (m['x']+dx, m['y']+dy))

# ─────────────────────────── FOG OF WAR / LIGHTING ──────────────
def draw_fog(surf, player_cx, player_cy, light_radius, lighter_on, torch_radius=0):
    fog = pygame.Surface((SCREEN_W, PLAY_H), pygame.SRCALPHA)
    fog.fill((0, 0, 0, 255))

    # base light radius
    r = light_radius
    if lighter_on:
        r = max(r, 160)
    r += torch_radius

    # soft gradient circle
    for rad in range(r, 0, -3):
        t = rad / r
        base_a = int(255 * t * t)
        if lighter_on:
            # warm amber flicker
            flicker = random.randint(-8, 8)
            col = (0, 0, 0, max(0, base_a + flicker))
        else:
            col = (0, 0, 0, base_a)
        pygame.draw.circle(fog, col, (player_cx, player_cy), rad)

    surf.blit(fog, (0, 0))

# ─────────────────────────── ENTITY: GHOST ──────────────────────
class Ghost:
    def __init__(self, path, speed=40, sprite_name='ghost'):
        self.path    = path
        self.wpt_idx = 0
        self.speed   = speed
        self.x       = path[0][1] * TILE + TILE//2
        self.y       = path[0][0] * TILE + TILE//2
        self.alpha   = 160
        self.sprite  = load(f'{sprite_name}.png', (48, 48))
        self.bob     = 0.0
        self.name    = sprite_name

    def update(self, dt):
        tx = self.path[self.wpt_idx][1] * TILE + TILE//2
        ty = self.path[self.wpt_idx][0] * TILE + TILE//2
        dx = tx - self.x
        dy = ty - self.y
        dist = math.hypot(dx, dy)
        if dist < 4:
            self.wpt_idx = (self.wpt_idx + 1) % len(self.path)
        else:
            self.x += dx / dist * self.speed * dt
            self.y += dy / dist * self.speed * dt
        self.bob += dt * 3
        self.alpha = 140 + int(30 * math.sin(self.bob))

    def draw(self, surf, cam_x, cam_y):
        sx = int(self.x - cam_x)
        sy = int(self.y - cam_y + math.sin(self.bob) * 4) - 24
        if -64 < sx < SCREEN_W+64 and -64 < sy < PLAY_H+64:
            img = self.sprite.copy()
            img.set_alpha(self.alpha)
            # eerie green tint for shadow demon
            if self.name == 'shadow_demon':
                tint = pygame.Surface(img.get_size(), pygame.SRCALPHA)
                tint.fill((0, 20, 0, 60))
                img.blit(tint, (0,0), special_flags=pygame.BLEND_RGBA_ADD)
            surf.blit(img, (sx - 24, sy))

    def rect(self):
        return pygame.Rect(self.x-20, self.y-20, 40, 40)

# ─────────────────────────── PLAYER ─────────────────────────────
class Player:
    SPEED = 120

    def __init__(self, row, col):
        self.x     = col * TILE + TILE//2
        self.y     = row * TILE + TILE//2
        self.hp    = 100
        self.sprite = load('player.png', (40, 40))
        # hotbar: 10 slots (0-9), values = item name or None
        self.hotbar    = [None]*10
        self.selected  = 0
        self.has_map   = False
        self.has_key   = False
        self.map_pieces= 0
        self.lighter_on= False
        self.torch_lit = False  # torch equipped+on
        self.sanity    = 100
        self.stamina   = 100
        self.footstep  = 0.0

    def add_item(self, item):
        for i in range(10):
            if self.hotbar[i] is None:
                self.hotbar[i] = item
                return True
        return False  # full

    def current_item(self):
        return self.hotbar[self.selected]

    def light_radius(self):
        r = 55
        if self.lighter_on:
            r = max(r, 170)
        if self.torch_lit:
            r = max(r, 220)
        return r

    def move(self, dx, dy, tilemap, dt):
        speed = self.SPEED
        nx = self.x + dx * speed * dt
        ny = self.y + dy * speed * dt
        # tile collision
        def passable(px, py):
            for corner in [(px-18,py-18),(px+18,py-18),(px-18,py+18),(px+18,py+18)]:
                cr, cc = int(corner[1]//TILE), int(corner[0]//TILE)
                if cr < 0 or cc < 0 or cr >= ROWS or cc >= COLS:
                    return False
                t = tilemap[cr][cc]
                if t in (T_WALL, T_BOOK, T_TABLE, T_DOOR):
                    return False
            return True
        if passable(nx, self.y): self.x = nx
        if passable(self.x, ny): self.y = ny

        if dx != 0 or dy != 0:
            self.footstep += dt
        else:
            self.footstep = 0

    def rect(self):
        return pygame.Rect(self.x-16, self.y-16, 32, 32)

# ─────────────────────────── JUMPSCARE ──────────────────────────
class Jumpscare:
    def __init__(self, sounds):
        self.active  = False
        self.timer   = 0
        self.dur     = 1.4
        self.img     = load('jumpscare.png', (600, 600))
        self.sounds  = sounds
        self._played = False

    def trigger(self):
        if not self.active:
            self.active  = True
            self.timer   = 0
            self._played = False

    def update(self, dt):
        if self.active:
            self.timer += dt
            if not self._played and self.timer > 0.05:
                if 'screech' in self.sounds:
                    self.sounds['screech'].play()
                self._played = True
            if self.timer > self.dur:
                self.active = False

    def draw(self, surf):
        if not self.active:
            return
        ratio = self.timer / self.dur
        # flash white first
        if ratio < 0.15:
            wf = pygame.Surface((SCREEN_W, SCREEN_H))
            wf.fill(WHITE)
            wf.set_alpha(int(255 * (1 - ratio/0.15)))
            surf.blit(wf, (0,0))
        else:
            fade = 1 - ((ratio - 0.15) / 0.85) ** 0.5
            img  = self.img.copy()
            img.set_alpha(int(255 * fade))
            sx   = SCREEN_W//2 - 300 + random.randint(-8,8)
            sy   = SCREEN_H//2 - 300 + random.randint(-8,8)
            surf.blit(img, (sx, sy))
            # red vignette
            vign = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            pygame.draw.rect(vign, (200,0,0,int(120*fade)), (0,0,SCREEN_W,SCREEN_H))
            surf.blit(vign, (0,0))

# ─────────────────────────── HUD HOTBAR ─────────────────────────
HOTBAR_ICONS = {}
def get_hotbar_icons():
    global HOTBAR_ICONS
    if not HOTBAR_ICONS:
        HOTBAR_ICONS = {
            'torch':    load('torch.png', (48,48)),
            'lighter':  load('lighter.png', (48,48)),
            'map_item': load('map_item.png', (48,48)),
            'key':      load('key.png', (48,48)),
        }
    return HOTBAR_ICONS

def draw_hotbar(surf, player, fonts):
    icons = get_hotbar_icons()
    bar_y = PLAY_H
    # background
    bg = pygame.Surface((SCREEN_W, HB_HEIGHT), pygame.SRCALPHA)
    bg.fill((10, 8, 12, 220))
    # minecraft-style top border
    pygame.draw.line(bg, (80,70,90), (0,0), (SCREEN_W,0), 2)
    surf.blit(bg, (0, bar_y))

    slot_w = 72
    total_w = slot_w * 10
    start_x = (SCREEN_W - total_w) // 2

    for i in range(10):
        sx = start_x + i * slot_w
        sy = bar_y + 4
        # slot background
        slot_col = (50,45,55,200) if i != player.selected else (180,120,40,220)
        slot_surf = pygame.Surface((68, 68), pygame.SRCALPHA)
        slot_surf.fill(slot_col)
        pygame.draw.rect(slot_surf, (90,80,100,255), (0,0,68,68), 2)
        if i == player.selected:
            pygame.draw.rect(slot_surf, (255,200,80,255), (0,0,68,68), 2)
        surf.blit(slot_surf, (sx, sy))

        # item icon
        item = player.hotbar[i]
        if item and item in icons:
            surf.blit(icons[item], (sx+10, sy+10))

        # slot number
        num = str(i+1) if i < 9 else '0'
        nf  = pygame.font.SysFont('Courier New', 13, bold=True)
        ns  = nf.render(num, True, (180,160,200))
        surf.blit(ns, (sx+4, sy+3))

    # Status bars (HP, Sanity)
    # HP bar
    hx = 10; hy = bar_y + 10
    hf = pygame.font.SysFont('Courier New', 14, bold=True)
    pygame.draw.rect(surf, (60,0,0), (hx, hy, 120, 14))
    pygame.draw.rect(surf, (200,0,0), (hx, hy, int(120*player.hp/100), 14))
    surf.blit(hf.render('HP', True, WHITE), (hx, hy-14))

    # Sanity bar
    sx2 = 10; sy2 = bar_y + 38
    sanity_col = (0, int(180*(player.sanity/100)), int(200*(player.sanity/100)))
    pygame.draw.rect(surf, (0,30,50), (sx2, sy2, 120, 14))
    pygame.draw.rect(surf, sanity_col, (sx2, sy2, int(120*player.sanity/100), 14))
    surf.blit(hf.render('정신력', True, (100,200,255)), (sx2, sy2-14))

    # current item name
    ci = player.current_item()
    if ci:
        ITEM_NAMES_KR = {'torch':'횃불','lighter':'라이터','map_item':'지도 조각','key':'도서관 열쇠'}
        label = ITEM_NAMES_KR.get(ci, ci)
        nf2 = pygame.font.SysFont('Malgun Gothic', 16, bold=True)
        try:
            ts = nf2.render(label, True, AMBER)
        except:
            ts = pygame.font.SysFont('Courier New', 16, bold=True).render(label, True, AMBER)
        surf.blit(ts, (SCREEN_W//2 - ts.get_width()//2, bar_y + 58))

    # lighter status
    if player.lighter_on:
        lf = pygame.font.SysFont('Courier New', 13)
        flicker = random.choice([(255,200,0),(255,180,20),(240,160,0)])
        surf.blit(lf.render('[F] 라이터 ON 🔥', True, flicker), (SCREEN_W-200, bar_y+10))

    # map pieces
    mf = pygame.font.SysFont('Courier New', 14, bold=True)
    mp_text = f'지도: {player.map_pieces}/3'
    surf.blit(mf.render(mp_text, True, (150,200,150)), (SCREEN_W-200, bar_y+35))
    if player.has_key:
        surf.blit(mf.render('🔑 열쇠 보유', True, (255,220,50)), (SCREEN_W-200, bar_y+55))

# ─────────────────────────── MINIMAP ─────────────────────────────
def draw_minimap(surf, tilemap, player, items, ghosts, map_known):
    mw = COLS * 6 + 4
    mh = ROWS * 6 + 4
    mx = SCREEN_W - mw - 10
    my = 10
    ms = pygame.Surface((mw, mh), pygame.SRCALPHA)
    ms.fill((0, 0, 0, 180))

    if player.map_pieces == 0:
        # no map - show only immediate area
        pr = int(player.y // TILE)
        pc = int(player.x // TILE)
        for r in range(max(0,pr-3), min(ROWS, pr+4)):
            for c in range(max(0,pc-3), min(COLS, pc+4)):
                t = tilemap[r][c]
                col = (50,45,55) if t==T_WALL else \
                      (80,60,80) if t in (T_BOOK,T_TABLE) else \
                      (30,28,35) if t==T_FLOOR else \
                      (200,100,0) if t==T_DOOR else \
                      (0,200,100) if t==T_EXIT else (0,0,0)
                pygame.draw.rect(ms, col, (2+c*6, 2+r*6, 5, 5))
    else:
        # show explored areas based on map pieces
        for r in range(ROWS):
            for c in range(COLS):
                if not map_known[r][c] and player.map_pieces < 3:
                    continue
                t = tilemap[r][c]
                col = (50,45,55) if t==T_WALL else \
                      (80,60,80) if t in (T_BOOK,T_TABLE) else \
                      (30,28,35) if t==T_FLOOR else \
                      (200,100,0) if t==T_DOOR else \
                      (0,200,100) if t==T_EXIT else (0,0,0)
                pygame.draw.rect(ms, col, (2+c*6, 2+r*6, 5, 5))
        # items
        for (ir,ic), itype in items.items():
            col = (255,200,0) if itype=='key' else \
                  (255,150,0) if itype=='torch' else \
                  (0,200,255) if itype=='map_item' else \
                  (180,180,180)
            pygame.draw.rect(ms, col, (2+ic*6+1, 2+ir*6+1, 3,3))
        # ghosts (flicker)
        if random.random() < 0.5:
            for g in ghosts:
                gr = int(g.y//TILE); gc = int(g.x//TILE)
                pygame.draw.rect(ms, (0,255,100,180), (2+gc*6, 2+gr*6, 5, 5))

    # player dot
    pr2 = int(player.y//TILE); pc2 = int(player.x//TILE)
    pygame.draw.rect(ms, (255,80,80), (2+pc2*6, 2+pr2*6, 5, 5))
    pygame.draw.rect(ms, WHITE, (2+pc2*6+1,2+pr2*6+1,3,3))

    pygame.draw.rect(ms, (100,80,110), (0,0,mw,mh), 1)
    surf.blit(ms, (mx, my))

    # label
    mf = pygame.font.SysFont('Courier New', 11, bold=True)
    surf.blit(mf.render('[ MAP ]', True, (150,130,160)), (mx+2, my+mh+2))

# ─────────────────────────── TITLE SCREEN ────────────────────────
def draw_title(surf, tick):
    surf.fill((5, 3, 8))
    # background static
    for _ in range(80):
        x = random.randint(0, SCREEN_W)
        y = random.randint(0, SCREEN_H)
        w = random.randint(10, 80)
        a = random.randint(5, 30)
        s = pygame.Surface((w, 2), pygame.SRCALPHA)
        s.fill((random.randint(0,40), random.randint(0,20), random.randint(0,40), a))
        surf.blit(s, (x,y))

    # blood drips from top
    random.seed(12345)
    for i in range(8):
        bx = random.randint(50, SCREEN_W-50)
        blen = random.randint(20, 80) + int(math.sin(tick*0.05 + i)*10)
        pygame.draw.line(surf, (120,0,0), (bx,0), (bx,blen), random.randint(2,5))
        pygame.draw.circle(surf, (150,0,0), (bx, blen), random.randint(3,6))

    random.seed()

    # Title with glitch
    title_lines = [
        "██╗     ██╗██████╗ ██████╗  █████╗ ██████╗ ██╗   ██╗",
        "██╗     ██╗██╔══██╗██╔══██╗██╔══██╗██╔══██╗╚██╗ ██╔╝",
    ]
    main_title = "도 서 관 탈 출"
    subtitle   = "L I B R A R Y   E S C A P E"

    tf = pygame.font.SysFont('Malgun Gothic', 52, bold=True)
    try:
        ts = tf.render(main_title, True, (200, 0, 0))
    except:
        ts = pygame.font.SysFont('Courier New', 52, bold=True).render('LIBRARY ESCAPE', True, (200,0,0))

    # glitch shift
    gx = random.randint(-4, 4) if random.random() < 0.15 else 0
    # red copy
    ts_r = ts.copy(); ts_r.set_alpha(120)
    surf.blit(ts_r, (SCREEN_W//2 - ts.get_width()//2 - 3, 180))
    surf.blit(ts, (SCREEN_W//2 - ts.get_width()//2 + gx, 180))

    sf = pygame.font.SysFont('Courier New', 20)
    ss = sf.render(subtitle, True, (120, 90, 130))
    surf.blit(ss, (SCREEN_W//2 - ss.get_width()//2, 245))

    # story text
    story = [
        "도서관에 갇혔다.",
        "열쇠를 찾아 탈출하라.",
        "그들은 이미 여기 있다...",
    ]
    sf2 = pygame.font.SysFont('Malgun Gothic', 18)
    try:
        for i, line in enumerate(story):
            col_a = int(180 + 50*math.sin(tick*0.04 + i))
            s2 = sf2.render(line, True, (col_a, col_a//3, col_a//4))
            surf.blit(s2, (SCREEN_W//2 - s2.get_width()//2, 310 + i*34))
    except:
        pass

    # controls
    cf = pygame.font.SysFont('Courier New', 16)
    controls = [
        "WASD / 방향키  :  이동",
        "E  :  아이템 줍기 / 상호작용",
        "F  :  라이터 켜기/끄기",
        "1~9,0  :  아이템 슬롯 선택",
        "",
        "[ ENTER ] 게임 시작",
        "[ ESC ]   종료",
    ]
    for i, line in enumerate(controls):
        col = AMBER if 'ENTER' in line or 'ESC' in line else (140, 120, 150)
        s3 = cf.render(line, True, col)
        surf.blit(s3, (SCREEN_W//2 - s3.get_width()//2, 430 + i*24))

    # scanlines
    for y in range(0, SCREEN_H, 4):
        sl = pygame.Surface((SCREEN_W, 2), pygame.SRCALPHA)
        sl.fill((0,0,0,40))
        surf.blit(sl, (0,y))

# ─────────────────────────── GAME OVER / WIN ─────────────────────
def draw_game_over(surf, tick, won=False):
    if won:
        surf.fill((0,5,0))
        msg = "탈출 성공!"
        sub = "당신은 도서관을 빠져나왔다..."
        col = (0,200,100)
    else:
        surf.fill((5,0,0))
        msg = "죽었습니다."
        sub = "도서관이 당신을 집어삼켰다..."
        col = (200,0,0)
        # blood effect
        for _ in range(30):
            x=random.randint(0,SCREEN_W)
            y=random.randint(0,SCREEN_H)
            pygame.draw.circle(surf, (100+random.randint(0,50),0,0), (x,y), random.randint(2,15))

    mf = pygame.font.SysFont('Malgun Gothic', 72, bold=True)
    try:
        ms = mf.render(msg, True, col)
    except:
        ms = pygame.font.SysFont('Courier New', 72, bold=True).render(msg if won else 'YOU DIED', True, col)

    # glitch
    gx = random.randint(-6,6) if random.random()<0.2 else 0
    ms_r = ms.copy(); ms_r.set_alpha(100)
    surf.blit(ms_r, (SCREEN_W//2-ms.get_width()//2-4, SCREEN_H//2-80))
    surf.blit(ms, (SCREEN_W//2-ms.get_width()//2+gx, SCREEN_H//2-80))

    sf = pygame.font.SysFont('Malgun Gothic', 22)
    try:
        ss = sf.render(sub, True, (180,160,180))
    except:
        ss = pygame.font.SysFont('Courier New',22).render(sub,True,(180,160,180))
    surf.blit(ss, (SCREEN_W//2-ss.get_width()//2, SCREEN_H//2))

    rf = pygame.font.SysFont('Courier New', 18)
    rs = rf.render('[ ENTER ]  다시 시작    [ ESC ]  종료', True, AMBER)
    surf.blit(rs, (SCREEN_W//2-rs.get_width()//2, SCREEN_H//2+80))

# ─────────────────────────── TILE RENDERER ──────────────────────
def draw_tilemap(surf, tilemap, cam_x, cam_y, items, tick):
    floor_img  = load('floor_tile.png', (TILE, TILE))
    wall_img   = load('wall_tile.png',  (TILE, TILE))
    book_img   = load('bookcaseBooks_S.png',  (TILE, TILE*2))
    table_img  = load('longTable_S.png',      (TILE*2, TILE))
    candle_img = load('candleStand_S.png',    (TILE, TILE))
    door_img   = None  # drawn procedurally
    item_imgs  = {
        'torch':    load('torch.png',    (36,36)),
        'lighter':  load('lighter.png',  (36,36)),
        'map_item': load('map_item.png', (36,36)),
        'key':      load('key.png',      (36,36)),
    }

    for r in range(ROWS):
        for c in range(COLS):
            sx = c * TILE - cam_x
            sy = r * TILE - cam_y
            if sx > SCREEN_W or sy > PLAY_H or sx+TILE < 0 or sy+TILE < 0:
                continue

            t = tilemap[r][c]
            # floor everywhere
            surf.blit(floor_img, (sx, sy))

            if t == T_WALL:
                surf.blit(wall_img, (sx, sy))
            elif t == T_BOOK:
                surf.blit(book_img, (sx, sy - TILE))
            elif t == T_TABLE:
                surf.blit(table_img, (sx, sy))
            elif t == T_DOOR:
                # draw a spooky door
                d_surf = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
                d_surf.fill((30,20,10,255))
                pygame.draw.rect(d_surf, (60,40,20), (8,0,48,63), 0)
                pygame.draw.rect(d_surf, (80,50,20), (8,0,48,63), 2)
                pygame.draw.circle(d_surf, (150,120,0), (50,32), 5)
                # lock icon
                lf = pygame.font.SysFont('Courier New',18,bold=True)
                ls = lf.render('🔒', True, (200,150,0))
                d_surf.blit(ls, (20,22))
                surf.blit(d_surf, (sx, sy))
            elif t == T_EXIT:
                d_surf = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
                d_surf.fill((0,30,10,255))
                pygame.draw.rect(d_surf, (20,80,40), (8,0,48,63), 0)
                pygame.draw.rect(d_surf, (40,150,60), (8,0,48,63), 2)
                lf = pygame.font.SysFont('Courier New',18,bold=True)
                ls = lf.render('🚪', True, (0,200,80))
                d_surf.blit(ls, (16,18))
                surf.blit(d_surf, (sx, sy))

            # items on floor
            if (r, c) in items:
                itype = items[(r,c)]
                iimg  = item_imgs.get(itype)
                if iimg:
                    bob = int(math.sin(tick*0.05 + r+c)*3)
                    surf.blit(iimg, (sx + 14, sy + 14 + bob))
                    # glow
                    gsurf = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
                    ga = int(60 + 30*math.sin(tick*0.06))
                    gc2 = (255,220,0,ga) if itype=='key' else (255,150,0,ga)
                    pygame.draw.circle(gsurf, gc2, (32,32), 20)
                    surf.blit(gsurf, (sx,sy))

# ─────────────────────────── MAIN GAME ──────────────────────────
def main():
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("도서관 탈출 - Library Escape")
    clock  = pygame.time.Clock()

    fonts = {
        'main': pygame.font.SysFont('Malgun Gothic', 24, bold=True),
        'mono': pygame.font.SysFont('Courier New', 18, bold=True),
        'big':  pygame.font.SysFont('Malgun Gothic', 36, bold=True),
    }

    sounds = gen_sounds()

    # play ambient drone
    if 'drone' in sounds:
        sounds['drone'].set_volume(0.3)
        try:
            sounds['drone'].play(-1)
        except:
            pass

    def new_game():
        tilemap = [row[:] for row in MAP_DATA]
        items   = dict(ITEMS_INIT)
        player  = Player(1, 1)
        ghosts  = [Ghost(p, speed=38) for p in GHOST_PATHS]
        shadows = [Ghost(p, speed=55, sprite_name='shadow_demon') for p in SHADOW_PATHS]
        map_known = [[False]*COLS for _ in range(ROWS)]
        return tilemap, items, player, ghosts, shadows, map_known

    tilemap, items, player, ghosts, shadows, map_known = new_game()

    glitch_text = GlitchText()
    jumpscare   = Jumpscare(sounds)

    # ── State machine ──────────────────────────────────
    STATE = 'title'   # title / game / dead / won
    tick  = 0

    # Jumpscare schedule: will fire at random intervals
    next_jumpscare_time = random.uniform(20, 45)  # seconds
    game_time = 0.0
    last_jumpscare = 0.0

    # Sanity events
    sanity_msg_timer = 0.0

    # Heartbeat
    hb_timer = 0.0
    hb_interval = 2.0

    # Glitch story triggers
    story_triggers = [
        (5,  "그들이 옵니다..."),
        (15, "여기서 나가야 해..."),
        (30, "지도를 찾아라"),
        (60, "열쇠... 어디에 있지..."),
        (90, "뒤를 봐"),
    ]
    story_idx = 0

    # Explore tracking
    explore_timer = 0.0

    running = True
    while running:
        dt   = min(clock.tick(FPS) / 1000.0, 0.05)
        tick += 1

        # ── Events ────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if STATE == 'title':
                    if event.key == pygame.K_RETURN:
                        STATE = 'game'
                        glitch_text.add("도서관에 갇혔다...", SCREEN_W//2-200, PLAY_H//2-40, dur=3, color=RED, size=32)
                    elif event.key == pygame.K_ESCAPE:
                        running = False

                elif STATE == 'game':
                    # Slot selection
                    slot_keys = {
                        pygame.K_1:0, pygame.K_2:1, pygame.K_3:2, pygame.K_4:3,
                        pygame.K_5:4, pygame.K_6:5, pygame.K_7:6, pygame.K_8:7,
                        pygame.K_9:8, pygame.K_0:9
                    }
                    if event.key in slot_keys:
                        player.selected = slot_keys[event.key]

                    # Lighter toggle
                    elif event.key == pygame.K_f:
                        # use lighter if in inventory
                        has_lighter = any(h == 'lighter' for h in player.hotbar)
                        if has_lighter:
                            player.lighter_on = not player.lighter_on
                            if 'lighter' in sounds:
                                sounds['lighter'].play()
                            msg = "라이터 켜짐 — 불꽃이 흔들린다" if player.lighter_on else "라이터 꺼짐"
                            glitch_text.add(msg, 80, PLAY_H//2, dur=1.5, color=AMBER, size=20, glitch=False)
                        else:
                            glitch_text.add("라이터가 없다...", 80, PLAY_H//2, dur=1.5, color=GREY, size=20, glitch=True)

                    # Interact / pick up
                    elif event.key == pygame.K_e:
                        pr = int(player.y // TILE)
                        pc = int(player.x // TILE)
                        # check adjacent cells
                        for dr in range(-1,2):
                            for dc in range(-1,2):
                                pos = (pr+dr, pc+dc)
                                if pos in items:
                                    itype = items[pos]
                                    if player.add_item(itype):
                                        del items[pos]
                                        if 'pickup' in sounds:
                                            sounds['pickup'].play()
                                        # special items
                                        if itype == 'key':
                                            player.has_key = True
                                            glitch_text.add(
                                                "열쇠를 획득했다!  출구로 달려라!",
                                                SCREEN_W//2-260, PLAY_H//2-60,
                                                dur=3, color=(255,220,0), size=30, glitch=True
                                            )
                                            jumpscare.trigger()
                                        elif itype == 'map_item':
                                            player.map_pieces = min(3, player.map_pieces+1)
                                            msgs = [
                                                "지도 조각을 발견했다!",
                                                f"지도 {player.map_pieces}/3 조각 모음",
                                                "지도가 완성되었다!" if player.map_pieces==3 else f"지도 {player.map_pieces}/3"
                                            ]
                                            glitch_text.add(msgs[player.map_pieces-1], 80, PLAY_H//2, dur=2, color=(0,200,255), size=22)
                                        elif itype == 'torch':
                                            glitch_text.add("횃불 획득!  [E]로 배치 가능", 80, PLAY_H//2, dur=2, color=AMBER, size=22)
                                    else:
                                        glitch_text.add("인벤토리가 꽉 찼다!", 80, PLAY_H//2, dur=1.5, color=RED, size=20)

                        # Use key on door
                        for dr in range(-1,2):
                            for dc in range(-1,2):
                                nr = pr+dr; nc = pc+dc
                                if 0<=nr<ROWS and 0<=nc<COLS:
                                    if tilemap[nr][nc] == T_DOOR:
                                        if player.has_key:
                                            tilemap[nr][nc] = T_EXIT
                                            glitch_text.add(
                                                "문이 열렸다!!!  탈출하라!!",
                                                SCREEN_W//2-240, PLAY_H//2-60,
                                                dur=3, color=(0,255,100), size=34, glitch=True
                                            )
                                        else:
                                            glitch_text.add(
                                                "잠겨있다...  열쇠를 찾아라",
                                                SCREEN_W//2-220, PLAY_H//2,
                                                dur=2.5, color=RED, size=24, glitch=True
                                            )

                    elif event.key == pygame.K_ESCAPE:
                        STATE = 'title'
                        tilemap, items, player, ghosts, shadows, map_known = new_game()
                        game_time = 0; story_idx = 0

                elif STATE in ('dead','won'):
                    if event.key == pygame.K_RETURN:
                        STATE = 'game'
                        tilemap, items, player, ghosts, shadows, map_known = new_game()
                        game_time = 0; story_idx = 0
                        glitch_text = GlitchText()
                    elif event.key == pygame.K_ESCAPE:
                        running = False

        # ── Title screen ──────────────────────────────────
        if STATE == 'title':
            draw_title(screen, tick)
            pygame.display.flip()
            continue

        # ── Game Over / Win ───────────────────────────────
        if STATE in ('dead','won'):
            draw_game_over(screen, tick, won=(STATE=='won'))
            pygame.display.flip()
            continue

        # ══════════════════ GAME LOGIC ═══════════════════

        game_time += dt

        # ── Player movement ───────────────────────────────
        keys = pygame.key.get_pressed()
        dx = dy = 0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:  dx = -1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx =  1
        if keys[pygame.K_w] or keys[pygame.K_UP]:    dy = -1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:  dy =  1
        if dx and dy:
            dx *= 0.707; dy *= 0.707
        player.move(dx, dy, tilemap, dt)

        # Check exit
        pr = int(player.y // TILE)
        pc = int(player.x // TILE)
        for dr in range(-1,2):
            for dc in range(-1,2):
                nr=pr+dr; nc=pc+dc
                if 0<=nr<ROWS and 0<=nc<COLS and tilemap[nr][nc]==T_EXIT:
                    if player.has_key:
                        dist = math.hypot(player.x-(nc*TILE+TILE//2), player.y-(nr*TILE+TILE//2))
                        if dist < TILE:
                            STATE = 'won'

        # Update explored cells
        explore_timer += dt
        if explore_timer > 0.2:
            explore_timer = 0
            r0=int(player.y//TILE); c0=int(player.x//TILE)
            for dr in range(-5,6):
                for dc in range(-5,6):
                    rr=r0+dr; cc=c0+dc
                    if 0<=rr<ROWS and 0<=cc<COLS:
                        map_known[rr][cc] = True

        # ── Ghost update & collision ──────────────────────
        all_entities = ghosts + shadows
        for e in all_entities:
            e.update(dt)
            dist = math.hypot(player.x - e.x, player.y - e.y)
            if dist < 32:
                if e in ghosts:
                    player.hp       -= 30 * dt
                    player.sanity   -= 20 * dt
                else:  # shadow demon
                    player.hp       -= 50 * dt
                    player.sanity   -= 35 * dt
                # push player back
                if dist > 1:
                    px = (player.x - e.x)/dist; py=(player.y - e.y)/dist
                    player.x += px*80*dt; player.y += py*80*dt
                # random glitch scream
                if random.random() < 0.02:
                    msgs = ["살려줘", "도망쳐", "뒤에 있다", "거기 있어!", "AAAHH"]
                    glitch_text.add(random.choice(msgs), random.randint(50,700), random.randint(50,PLAY_H-80),
                                    dur=0.8, color=RED, size=24, glitch=True)

        player.hp     = max(0, min(100, player.hp))
        player.sanity = max(0, min(100, player.sanity))

        if player.hp <= 0 or player.sanity <= 0:
            STATE = 'dead'
            continue

        # ── Sanity effects ────────────────────────────────
        if player.sanity < 40:
            sanity_msg_timer += dt
            if sanity_msg_timer > 4:
                sanity_msg_timer = 0
                msgs_insane = [
                    "저게 움직인다...",
                    "눈이 보여...",
                    "목소리가 들려...",
                    "▓▒░ 위험 ░▒▓",
                    "████ 정신 붕괴 ████",
                ]
                glitch_text.add(random.choice(msgs_insane),
                    random.randint(100, SCREEN_W-300), random.randint(50, PLAY_H-100),
                    dur=2.5, color=(200,0,200), size=26, glitch=True)

        # ── Sanity drain in dark ──────────────────────────
        light = player.light_radius()
        if light < 80 and not player.lighter_on and not player.torch_lit:
            player.sanity -= 3 * dt

        # Torch equipped
        player.torch_lit = (player.hotbar[player.selected] == 'torch')

        # ── Scheduled jumpscare ───────────────────────────
        if game_time - last_jumpscare > next_jumpscare_time:
            last_jumpscare = game_time
            next_jumpscare_time = random.uniform(25, 60)
            jumpscare.trigger()

        # ── Story glitch triggers ─────────────────────────
        if story_idx < len(story_triggers):
            ttime, tmsg = story_triggers[story_idx]
            if game_time > ttime:
                glitch_text.add(tmsg, SCREEN_W//2 - 200, PLAY_H//2 - 40,
                                dur=3.5, color=RED, size=28, glitch=True)
                story_idx += 1

        # ── Heartbeat ────────────────────────────────────
        hb_timer += dt
        if player.hp < 40:
            hb_interval = 0.6
        elif player.hp < 70:
            hb_interval = 1.2
        else:
            hb_interval = 2.0
        if hb_timer > hb_interval:
            hb_timer = 0
            if 'heartbeat' in sounds:
                sounds['heartbeat'].set_volume(min(0.6, (100-player.hp)/100 + 0.1))
                sounds['heartbeat'].play()

        jumpscare.update(dt)
        glitch_text.update(dt)

        # ── Camera ───────────────────────────────────────
        cam_x = int(player.x - SCREEN_W // 2)
        cam_y = int(player.y - PLAY_H  // 2)
        cam_x = max(0, min(cam_x, COLS*TILE - SCREEN_W))
        cam_y = max(0, min(cam_y, ROWS*TILE - PLAY_H))

        # ══════════════════ RENDERING ════════════════════

        # Draw world
        screen.fill(DKGREY)
        draw_tilemap(screen, tilemap, cam_x, cam_y, items, tick)

        # Draw entities
        for e in all_entities:
            e.draw(screen, cam_x, cam_y)

        # Draw player
        px_screen = int(player.x - cam_x) - 20
        py_screen = int(player.y - cam_y) - 20
        # shadow under player
        shadow_s = pygame.Surface((40,16), pygame.SRCALPHA)
        shadow_s.fill((0,0,0,80))
        screen.blit(shadow_s, (px_screen, py_screen+28))
        screen.blit(player.sprite, (px_screen, py_screen))

        # Fog of war
        torch_r = 120 if player.torch_lit else 0
        draw_fog(screen, int(player.x - cam_x), int(player.y - cam_y),
                 player.light_radius(), player.lighter_on, torch_r)

        # Glitch text overlay
        glitch_text.draw(screen, fonts)

        # Sanity screen warp
        if player.sanity < 30 and random.random() < 0.04:
            warp = pygame.Surface((SCREEN_W, PLAY_H), pygame.SRCALPHA)
            warp.fill((random.randint(0,20),0,random.randint(0,15),
                       random.randint(10,40)))
            screen.blit(warp, (0,0))

        # Random scan lines for low sanity
        if player.sanity < 60:
            for _ in range(int((60-player.sanity)//3)):
                sy = random.randint(0, PLAY_H)
                sw = random.randint(30, SCREEN_W)
                sx = random.randint(0, SCREEN_W-sw)
                sl = pygame.Surface((sw, random.randint(1,4)), pygame.SRCALPHA)
                sl.fill((random.randint(0,80),0,0,random.randint(20,80)))
                screen.blit(sl, (sx,sy))

        # Minimap
        draw_minimap(screen, tilemap, player, items, all_entities, map_known)

        # HP vignette (red edges when low)
        if player.hp < 60:
            vig = pygame.Surface((SCREEN_W, PLAY_H), pygame.SRCALPHA)
            va  = int((60-player.hp)/60 * 120)
            for vr in range(0, 40, 4):
                pygame.draw.rect(vig,(200,0,0,max(0,va-vr*3)),(vr,vr,SCREEN_W-vr*2,PLAY_H-vr*2),1)
            screen.blit(vig,(0,0))

        # Hotbar
        draw_hotbar(screen, player, fonts)

        # Jumpscare on top
        jumpscare.draw(screen)

        # Scanlines overlay (always subtle)
        for y in range(0, SCREEN_H, 3):
            sl = pygame.Surface((SCREEN_W, 1), pygame.SRCALPHA)
            sl.fill((0,0,0,25))
            screen.blit(sl, (0,y))

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == '__main__':
    main()
