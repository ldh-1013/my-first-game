import os

# Screen
SCREEN_WIDTH  = 900
SCREEN_HEIGHT = 700
FPS           = 60
TITLE         = "MONO SWITCH"

# Tile
TILE_SIZE = 48

# Tile type constants
TILE_WHITE  = 0   # passable in BLACK mode
TILE_BLACK  = 1   # passable in WHITE mode
TILE_WALL   = 2   # never passable
TILE_GRAY   = 3   # always passable
TILE_GOAL   = 4   # always passable, win condition
TILE_KEY    = 5   # always passable, grants key
TILE_LOCK   = 6   # passable only with key
TILE_SWITCH = 7   # zone switch (toggles specific tiles) - implemented later
TILE_TIMER  = 8   # timer tile - implemented later

# Modes
MODE_BLACK = "black"
MODE_WHITE = "white"

# Colors (R, G, B) — legacy, kept for menu/clear_screen compatibility
COLOR_BG        = (18,  18,  18)
COLOR_WHITE     = (235, 235, 235)
COLOR_BLACK     = (35,  35,  35)
COLOR_WALL      = (70,  70,  70)
COLOR_GRAY      = (140, 140, 140)
COLOR_GOAL      = (90,  200, 120)
COLOR_KEY       = (220, 180, 70)
COLOR_LOCK      = (200, 90,  90)
COLOR_SWITCH    = (80,  180, 190)
COLOR_TIMER     = (190, 100, 200)
COLOR_GRID      = (55,  55,  55)
COLOR_PLAYER_B  = (30,  30,  30)
COLOR_PLAYER_W  = (235, 235, 235)
COLOR_HUD_TEXT  = (240, 240, 240)

# --- Monochrome palette (graphics only) ---
# BLACK MODE (cold blue-gray)
BLACK_BG   = (14,  15,  18)     # #0E0F12  background
BLACK_TILE = (232, 234, 237)    # #E8EAED  light/passable tile
BLACK_WALL = (37,  39,  44)     # #25272C  wall
BLACK_LINE = (90,  95,  106)    # #5A5F6A  accent/grid line
# WHITE MODE (warm ivory-gray)
WHITE_BG   = (244, 242, 238)    # #F4F2EE  background
WHITE_TILE = (21,  21,  21)     # #151515  dark/passable tile
WHITE_WALL = (216, 213, 206)    # #D8D5CE  wall
WHITE_LINE = (119, 115, 106)    # #77736A  accent/grid line
# Goal frame follows the "bright element" of each mode
GOAL_BLACK = (232, 234, 237)    # #E8EAED
GOAL_WHITE = (21,  21,  21)     # #151515

def palette(mode):
    """Return a dict of resolved colors for the current mode."""
    if mode == MODE_BLACK:
        return {"bg": BLACK_BG, "tile": BLACK_TILE, "wall": BLACK_WALL,
                "line": BLACK_LINE, "goal": GOAL_BLACK,
                "fg": BLACK_TILE, "dim": BLACK_WALL}
    else:
        return {"bg": WHITE_BG, "tile": WHITE_TILE, "wall": WHITE_WALL,
                "line": WHITE_LINE, "goal": GOAL_WHITE,
                "fg": WHITE_TILE, "dim": WHITE_WALL}

# Paths (settings.py sits in the project root next to the Assets folder)
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "Assets")
STAGES_DIR = os.path.join(ASSETS_DIR, "stages")
ICONS_DIR  = os.path.join(ASSETS_DIR, "icons")
FONTS_DIR  = os.path.join(ASSETS_DIR, "fonts")
BGM_DIR    = os.path.join(ASSETS_DIR, "sounds", "bgm")
SFX_DIR    = os.path.join(ASSETS_DIR, "sounds", "stx")
FONT_PATH  = os.path.join(FONTS_DIR, "SUIT-Thin.ttf")
SAVE_PATH  = os.path.join(BASE_DIR, "save.json")

# Stage data layout reminder:
#   map is indexed as map[row][col]
#   player_start is [col, row]
#   switch_limit: -1 means unlimited mode switches
TOTAL_STAGES = 30
