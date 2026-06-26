from settings import (TILE_WHITE, TILE_BLACK, TILE_WALL, TILE_GRAY, TILE_GOAL,
                      TILE_KEY, TILE_LOCK, TILE_SWITCH, TILE_TIMER,
                      MODE_BLACK, MODE_WHITE)

def can_enter(tile, mode, has_key):
    """Return True if the player may step onto this tile."""
    if tile == TILE_WALL:
        return False
    if tile == TILE_WHITE:
        return mode == MODE_BLACK
    if tile == TILE_BLACK:
        return mode == MODE_WHITE
    if tile == TILE_LOCK:
        return has_key
    # GRAY, GOAL, KEY, SWITCH, TIMER are always enterable in the core loop
    return True
