import pygame
from settings import (TILE_SIZE, TILE_KEY, TILE_LOCK, TILE_GRAY, TILE_GOAL,
                      TILE_SWITCH, TILE_TIMER, MODE_BLACK,
                      BLACK_TILE, BLACK_WALL, WHITE_TILE, WHITE_WALL)
from src.collision import can_enter
from src.switch import toggle_mode

class Player:
    def __init__(self, col, row, initial_mode):
        self.col = col
        self.row = row
        self.mode = initial_mode          # "black" or "white"
        self.has_key = False
        self.move_count = 0
        self.switch_count = 0

    def try_move(self, dcol, drow, tilemap):
        """Attempt a one-tile move. Returns True if the player moved."""
        ncol, nrow = self.col + dcol, self.row + drow
        target = tilemap.get_tile(ncol, nrow)
        if not can_enter(target, self.mode, self.has_key):
            return False
        self.col, self.row = ncol, nrow
        self.move_count += 1
        # pick up key: grant key, turn the tile into gray so it can't be re-collected
        if target == TILE_KEY:
            self.has_key = True
            tilemap.set_tile(ncol, nrow, TILE_GRAY)
        if target == TILE_SWITCH:
            tilemap.apply_zone_switch(self.col, self.row)
        if target == TILE_TIMER:
            tilemap.activate_timer(self.col, self.row)
        return True

    def try_switch(self, switch_limit):
        """Toggle black/white mode, respecting switch_limit (-1 = unlimited)."""
        if switch_limit != -1 and self.switch_count >= switch_limit:
            return False
        self.mode = toggle_mode(self.mode)
        self.switch_count += 1
        return True

    def is_at_goal(self, tilemap):
        return tilemap.get_tile(self.col, self.row) == TILE_GOAL

    def render(self, surface, offset_x, offset_y, mode):
        cx = offset_x + self.col * TILE_SIZE + TILE_SIZE // 2
        cy = offset_y + self.row * TILE_SIZE + TILE_SIZE // 2
        half = TILE_SIZE // 2 - 8  # half-diagonal of the outer diamond

        if mode == MODE_BLACK:
            fill_c    = BLACK_TILE   # bright
            outline_c = BLACK_WALL   # dark
            core_c    = WHITE_TILE   # contrasting core
        else:
            fill_c    = WHITE_TILE   # dark
            outline_c = WHITE_WALL   # light
            core_c    = BLACK_TILE   # contrasting core

        pts = [(cx, cy - half), (cx + half, cy),
               (cx, cy + half), (cx - half, cy)]
        pygame.draw.polygon(surface, fill_c, pts)
        pygame.draw.polygon(surface, outline_c, pts, 2)

        # tiny contrasting core
        core_half = 4
        core_pts = [(cx, cy - core_half), (cx + core_half, cy),
                    (cx, cy + core_half), (cx - core_half, cy)]
        pygame.draw.polygon(surface, core_c, core_pts)
