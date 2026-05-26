from PIL import Image, ImageDraw, ImageFilter
import os, math

def save(img, name):
    img.save(f'/home/claude/game/assets/{name}.png')
    print(f"Saved {name}.png")

# ── Player (top-down 32x32, pale survivor) ──────────────────────────────────
def make_player():
    sz = 64
    img = Image.new('RGBA', (sz, sz), (0,0,0,0))
    d = ImageDraw.Draw(img)
    # body
    d.ellipse([16,20,48,56], fill=(80,60,50,255))  # coat
    d.ellipse([22,26,42,52], fill=(60,45,35,255))
    # head
    d.ellipse([20,4,44,28], fill=(220,180,140,255))
    # hair
    d.ellipse([20,4,44,16], fill=(40,25,15,255))
    # eyes
    d.ellipse([25,14,29,18], fill=(10,10,10,255))
    d.ellipse([35,14,39,18], fill=(10,10,10,255))
    # eye gleam
    d.ellipse([26,14,28,16], fill=(255,255,255,200))
    d.ellipse([36,14,38,16], fill=(255,255,255,200))
    save(img, 'player')

# ── Ghost (translucent white wisp) ──────────────────────────────────────────
def make_ghost():
    sz = 64
    img = Image.new('RGBA', (sz, sz), (0,0,0,0))
    d = ImageDraw.Draw(img)
    # main body
    d.ellipse([8,0,56,44], fill=(200,220,255,180))
    # wavy bottom
    for i in range(4):
        x = 8 + i*12
        d.ellipse([x,36,x+16,56], fill=(200,220,255,160))
    # blank eyes
    d.ellipse([18,14,28,24], fill=(0,0,0,200))
    d.ellipse([36,14,46,24], fill=(0,0,0,200))
    # glow blur effect
    img2 = img.filter(ImageFilter.GaussianBlur(1))
    save(img2, 'ghost')

# ── Shadow demon (dark blob with red eyes) ──────────────────────────────────
def make_shadow():
    sz = 72
    img = Image.new('RGBA', (sz, sz), (0,0,0,0))
    d = ImageDraw.Draw(img)
    d.ellipse([4,4,68,68], fill=(10,5,15,220))
    d.ellipse([0,8,64,72], fill=(15,5,20,200))
    # red eyes
    d.ellipse([18,22,30,34], fill=(200,0,0,255))
    d.ellipse([42,22,54,34], fill=(200,0,0,255))
    d.ellipse([21,24,27,32], fill=(255,80,80,255))
    d.ellipse([45,24,51,32], fill=(255,80,80,255))
    img2 = img.filter(ImageFilter.GaussianBlur(1))
    save(img2, 'shadow_demon')

# ── Lighter ──────────────────────────────────────────────────────────────────
def make_lighter():
    sz = 48
    img = Image.new('RGBA', (sz, sz), (0,0,0,0))
    d = ImageDraw.Draw(img)
    # body
    d.rounded_rectangle([10,18,38,46], radius=4, fill=(180,150,60,255), outline=(100,80,20,255), width=2)
    # top cap
    d.rounded_rectangle([12,14,36,20], radius=2, fill=(140,120,50,255))
    # flint wheel
    d.ellipse([16,10,32,18], fill=(100,100,100,255), outline=(60,60,60,255), width=1)
    # flame (unlit)
    d.polygon([(24,2),(20,12),(28,12)], fill=(255,180,0,200))
    d.polygon([(24,4),(21,11),(27,11)], fill=(255,240,100,240))
    # wick
    d.line([(24,10),(24,14)], fill=(80,60,40,255), width=2)
    save(img, 'lighter')

# ── Torch (wall item) ────────────────────────────────────────────────────────
def make_torch():
    sz = 48
    img = Image.new('RGBA', (sz, sz), (0,0,0,0))
    d = ImageDraw.Draw(img)
    # handle
    d.rectangle([21,20,27,44], fill=(100,60,20,255))
    # wrap
    for y in range(20,44,6):
        d.line([(20,y),(28,y)], fill=(70,40,10,255), width=1)
    # flame base
    d.ellipse([16,10,32,26], fill=(255,120,0,230))
    d.ellipse([18,8,30,22], fill=(255,200,0,255))
    d.ellipse([20,4,28,16], fill=(255,240,180,255))
    save(img, 'torch')

# ── Map (rolled parchment) ───────────────────────────────────────────────────
def make_map():
    sz = 48
    img = Image.new('RGBA', (sz, sz), (0,0,0,0))
    d = ImageDraw.Draw(img)
    d.rectangle([6,8,42,40], fill=(220,190,130,255), outline=(140,100,50,255), width=2)
    d.ellipse([2,6,10,42], fill=(190,160,100,255), outline=(140,100,50,255), width=1)
    d.ellipse([38,6,46,42], fill=(190,160,100,255), outline=(140,100,50,255), width=1)
    # map lines
    for y in range(14,36,5):
        d.line([(10,y),(38,y)], fill=(140,100,50,150), width=1)
    d.rectangle([12,14,22,24], fill=(100,150,80,100))
    d.line([(26,16),(36,20)], fill=(180,80,50,200), width=2)
    d.ellipse([29,18,33,22], fill=(200,50,50,220))
    save(img, 'map_item')

# ── Key ──────────────────────────────────────────────────────────────────────
def make_key():
    sz = 48
    img = Image.new('RGBA', (sz, sz), (0,0,0,0))
    d = ImageDraw.Draw(img)
    d.ellipse([8,8,28,28], fill=(200,170,0,255), outline=(150,120,0,255), width=2)
    d.ellipse([12,12,24,24], fill=(0,0,0,0))
    d.rectangle([26,16,44,20], fill=(200,170,0,255))
    d.rectangle([38,20,42,26], fill=(200,170,0,255))
    d.rectangle([33,20,37,24], fill=(200,170,0,255))
    save(img, 'key')

# ── Floor tile (dark stone) ──────────────────────────────────────────────────
def make_floor():
    sz = 64
    img = Image.new('RGBA', (sz, sz), (0,0,0,0))
    d = ImageDraw.Draw(img)
    d.rectangle([0,0,63,63], fill=(35,30,40,255))
    d.line([(0,32),(63,32)], fill=(25,20,30,255), width=1)
    d.line([(32,0),(32,63)], fill=(25,20,30,255), width=1)
    d.line([(0,0),(63,63)], fill=(45,40,50,100), width=1)
    save(img, 'floor_tile')

# ── Wall tile ────────────────────────────────────────────────────────────────
def make_wall():
    sz = 64
    img = Image.new('RGBA', (sz, sz), (0,0,0,0))
    d = ImageDraw.Draw(img)
    d.rectangle([0,0,63,63], fill=(50,45,55,255))
    for y in range(0,64,16):
        offset = 16 if (y//16)%2 else 0
        for x in range(-16,80,32):
            d.rectangle([x+offset,y,x+offset+28,y+13], fill=(60,55,65,255), outline=(40,35,45,255), width=1)
    save(img, 'wall_tile')

# ── Jumpscare face ──────────────────────────────────────────────────────────
def make_jumpscare():
    sz = 400
    img = Image.new('RGBA', (sz, sz), (0,0,0,0))
    d = ImageDraw.Draw(img)
    # distorted face - pale and horrific
    d.ellipse([40,30,360,370], fill=(240,220,200,255))
    # deep dark eyes
    d.ellipse([80,100,160,200], fill=(0,0,0,255))
    d.ellipse([240,100,320,200], fill=(0,0,0,255))
    # bloodshot veins
    for i in range(8):
        a = i * 45
        r = 30
        ex = 120 + int(r*math.cos(math.radians(a)))
        ey = 150 + int(r*math.sin(math.radians(a)))
        d.line([(120,150),(ex,ey)], fill=(200,0,0,200), width=2)
        ex2 = 280 + int(r*math.cos(math.radians(a)))
        ey2 = 150 + int(r*math.sin(math.radians(a)))
        d.line([(280,150),(ex2,ey2)], fill=(200,0,0,200), width=2)
    # glowing eye whites
    d.ellipse([95,115,145,165], fill=(240,0,0,255))
    d.ellipse([255,115,305,165], fill=(240,0,0,255))
    d.ellipse([105,125,135,155], fill=(0,0,0,255))
    d.ellipse([265,125,295,155], fill=(0,0,0,255))
    # horrible mouth
    d.arc([80,250,320,380], start=0, end=180, fill=(0,0,0,255), width=8)
    for i in range(7):
        tx = 100 + i*32
        d.line([(tx,260),(tx-5,320)], fill=(220,180,160,255), width=8)
    # cracks
    d.line([(200,30),(190,150),(210,200)], fill=(150,0,0,180), width=3)
    d.line([(50,80),(120,160)], fill=(150,0,0,150), width=2)
    save(img, 'jumpscare')

# ── Scream text glitch overlay ───────────────────────────────────────────────
def make_glitch_overlay():
    sz = 512
    img = Image.new('RGBA', (sz, 80), (0,0,0,0))
    d = ImageDraw.Draw(img)
    import random
    random.seed(42)
    for i in range(20):
        x = random.randint(0, sz-60)
        y = random.randint(0, 60)
        w = random.randint(30,120)
        h = random.randint(2, 10)
        c = random.choice([(255,0,0,180),(0,255,0,100),(0,0,255,120),(255,255,0,150)])
        d.rectangle([x,y,x+w,y+h], fill=c)
    save(img, 'glitch_bar')

make_player()
make_ghost()
make_shadow()
make_lighter()
make_torch()
make_map()
make_key()
make_floor()
make_wall()
make_jumpscare()
make_glitch_overlay()
print("All assets generated!")
