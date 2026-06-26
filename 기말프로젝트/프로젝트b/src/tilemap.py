import json, os, pygame
from settings import (STAGES_DIR, TILE_SIZE, TILE_WALL,
                      TILE_GOAL, TILE_KEY, TILE_LOCK, TILE_SWITCH, TILE_TIMER,
                      palette)

def load_stage(stage_number):
    """Read Assets/stages/stage_XX.json and return the parsed dict."""
    path = os.path.join(STAGES_DIR, f"stage_{stage_number:02d}.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

class TileMap:
    def __init__(self, stage_data):
        # store a DEEP COPY of the map so resets/edits never mutate the source
        self.map    = [row[:] for row in stage_data["map"]]
        self.width  = stage_data["width"]
        self.height = stage_data["height"]
        # optional advanced data
        self.zone_regions = stage_data.get("zone_regions", {})
        self.timer_delays = stage_data.get("timer_delays", {})
        self.active_timers = {}   # (col,row) -> expiry time in ms
        # one reusable font for timer countdown labels (created once)
        self._timer_font = pygame.font.SysFont(None, 28)

    def get_tile(self, col, row):
        if 0 <= row < self.height and 0 <= col < self.width:
            return self.map[row][col]
        return TILE_WALL

    def set_tile(self, col, row, value):
        if 0 <= row < self.height and 0 <= col < self.width:
            self.map[row][col] = value

    def apply_zone_switch(self, col, row):
        """Fire the zone switch at (col, row) if it exists and hasn't fired yet.
        Toggles each listed tile: 0→1, 1→0.
        Marks the switch as used by setting its own tile to TILE_GRAY (3).
        Does nothing if (col, row) is not in zone_regions or already fired.
        """
        key = f"{col},{row}"
        if key not in self.zone_regions:
            return
        for tc, tr in self.zone_regions[key]:
            current = self.get_tile(tc, tr)
            if current == 0:
                self.set_tile(tc, tr, 1)
            elif current == 1:
                self.set_tile(tc, tr, 0)
        self.set_tile(col, row, 3)   # mark switch as used
        del self.zone_regions[key]   # prevent re-firing

    def activate_timer(self, col, row):
        """Start the countdown for a timer tile if it isn't already running."""
        if self.get_tile(col, row) != 8:      # not a timer tile
            return
        if (col, row) in self.active_timers:   # already counting
            return
        delay_sec = self.timer_delays.get(f"{col},{row}", 3)
        self.active_timers[(col, row)] = pygame.time.get_ticks() + delay_sec * 1000

    def update_timers(self):
        """Call once per frame. Turn expired timer tiles into walls."""
        now = pygame.time.get_ticks()
        for (col, row), expiry in list(self.active_timers.items()):
            if now >= expiry:
                self.set_tile(col, row, 2)         # becomes a wall
                del self.active_timers[(col, row)]

    def render_timer_labels(self, surface, offset_x, offset_y, mode):
        fg = palette(mode)["fg"]
        now = pygame.time.get_ticks()
        for (col, row), expiry in self.active_timers.items():
            ms_left = max(0, expiry - now)
            remaining = ms_left // 1000 + (1 if ms_left % 1000 else 0)
            if remaining < 1:
                remaining = 1
            label = self._timer_font.render(str(remaining), True, fg)
            cx = offset_x + col * TILE_SIZE + TILE_SIZE // 2
            cy = offset_y + row * TILE_SIZE + TILE_SIZE // 2
            surface.blit(label, label.get_rect(center=(cx, cy)))

    def render(self, surface, offset_x, offset_y, mode):
        pal    = palette(mode)
        tile_c = pal["tile"]
        wall_c = pal["wall"]
        line_c = pal["line"]
        goal_c = pal["goal"]
        fg_c   = pal["fg"]
        T = TILE_SIZE
        M = 4  # inset margin for open cells

        for row in range(self.height):
            for col in range(self.width):
                t = self.map[row][col]
                x = offset_x + col * T
                y = offset_y + row * T
                cell = pygame.Rect(x, y, T, T)
                cx, cy = x + T // 2, y + T // 2

                if t == TILE_WALL:
                    # solid block + inner double-line
                    pygame.draw.rect(surface, wall_c, cell)
                    inner = pygame.Rect(x + 3, y + 3, T - 6, T - 6)
                    pygame.draw.rect(surface, line_c, inner, 1)

                elif t in (0, 1, 3):
                    # open cell: inset filled square
                    inset = pygame.Rect(x + M, y + M, T - 2 * M, T - 2 * M)
                    pygame.draw.rect(surface, tile_c, inset)
                    pygame.draw.rect(surface, line_c, inset, 1)

                elif t == TILE_GOAL:
                    # hollow double square frame — no fill
                    outer = pygame.Rect(x + 5, y + 5, T - 10, T - 10)
                    pygame.draw.rect(surface, goal_c, outer, 2)
                    hs = 14
                    inner = pygame.Rect(cx - hs // 2, cy - hs // 2, hs, hs)
                    pygame.draw.rect(surface, goal_c, inner, 2)

                elif t == TILE_KEY:
                    # circle head + stem + one tooth
                    pygame.draw.circle(surface, fg_c, (cx, cy - 5), 7, 2)
                    pygame.draw.line(surface, fg_c, (cx, cy + 2), (cx, cy + 14), 2)
                    pygame.draw.line(surface, fg_c, (cx, cy + 9), (cx + 5, cy + 9), 2)

                elif t == TILE_LOCK:
                    # padlock body + shackle arc
                    bw, bh = 16, 12
                    bx, by = cx - bw // 2, cy - 1
                    pygame.draw.rect(surface, fg_c, pygame.Rect(bx, by, bw, bh), 2)
                    pygame.draw.arc(surface, fg_c,
                                    pygame.Rect(bx + 1, by - 10, bw - 2, 12),
                                    0, 3.14159, 2)

                elif t == TILE_SWITCH:
                    # hollow diamond
                    half = 13
                    pts = [(cx, cy - half), (cx + half, cy),
                           (cx, cy + half), (cx - half, cy)]
                    pygame.draw.polygon(surface, line_c, pts, 2)

                elif t == TILE_TIMER:
                    # hollow square + center-to-top clock hand
                    sq = 20
                    sx, sy_t = cx - sq // 2, cy - sq // 2
                    pygame.draw.rect(surface, line_c,
                                     pygame.Rect(sx, sy_t, sq, sq), 2)
                    pygame.draw.line(surface, line_c, (cx, cy), (cx, sy_t + 2), 2)

                # lattice line on every cell boundary
                pygame.draw.rect(surface, line_c, cell, 1)
