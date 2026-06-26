"""
compute_stars.py — one-shot tool to compute BFS-optimal cost for every stage
and write star_thresholds back into each stage JSON.

Scoring rule used by the game:
    score = player.move_count + player.switch_count
    if score <= star_thresholds[0]: 3 stars
    elif score <= star_thresholds[1]: 2 stars
    else: 1 star  (always at least 1 for clearing)
"""

import json, math, os
from collections import deque

STAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "Assets", "stages")

# Tile type constants (mirrors settings.py)
TILE_WHITE  = 0
TILE_BLACK  = 1
TILE_WALL   = 2
TILE_GRAY   = 3
TILE_GOAL   = 4
TILE_KEY    = 5
TILE_LOCK   = 6
TILE_SWITCH = 7
TILE_TIMER  = 8


def effective_tile(grid, col, row, zone_regions, activated):
    """Return the effective tile type at (col, row) given activated zone keys."""
    t = grid[row][col]
    if t in (TILE_SWITCH, TILE_TIMER):
        return TILE_SWITCH   # always passable (treated as gray for BFS)
    for zk in activated:
        for tc, tr in zone_regions.get(zk, []):
            if tc == col and tr == row:
                return 1 - t   # flip 0<->1
    return t


def can_enter(tile, mode, has_key):
    if tile == TILE_WALL:
        return False
    if tile == TILE_WHITE:
        return mode == "black"
    if tile == TILE_BLACK:
        return mode == "white"
    if tile == TILE_LOCK:
        return has_key
    return True   # GRAY, GOAL, KEY, SWITCH (effective), TIMER always passable


def bfs_optimal(stage):
    """
    BFS over (col, row, mode, switches_used, has_key, activated_zones).
    Every move costs 1; every mode switch costs 1 (also counts as switches_used).
    Zone switch activation is modeled: stepping on tile 7 adds its key to
    activated_zones, which flips the cells listed in zone_regions.
    Returns the minimum total cost to reach a GOAL tile, or None if unsolvable.
    """
    grid         = stage["map"]
    H            = stage["height"]
    W            = stage["width"]
    sc, sr       = stage["player_start"]
    mode0        = stage["initial_mode"]
    switch_limit = stage["switch_limit"]
    zone_regions = stage.get("zone_regions", {})

    init = (sc, sr, mode0, 0, False, frozenset())
    dist = {init: 0}
    q    = deque([init])
    dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]

    while q:
        col, row, mode, sw_used, has_key, activated = q.popleft()
        d = dist[(col, row, mode, sw_used, has_key, activated)]

        # goal check (effective tile at current position)
        if effective_tile(grid, col, row, zone_regions, activated) == TILE_GOAL:
            return d

        # ── move to neighbour ──
        for dc, dr in dirs:
            nc, nr = col + dc, row + dr
            if not (0 <= nc < W and 0 <= nr < H):
                continue
            eff = effective_tile(grid, nc, nr, zone_regions, activated)
            if not can_enter(eff, mode, has_key):
                continue
            nkey = has_key or (eff == TILE_KEY)
            # activate zone switch if stepping onto an unfired tile 7
            nact = activated
            if grid[nr][nc] == TILE_SWITCH:
                zk = f"{nc},{nr}"
                if zk in zone_regions and zk not in activated:
                    nact = activated | frozenset([zk])
            ns = (nc, nr, mode, sw_used, nkey, nact)
            nd = d + 1
            if ns not in dist or dist[ns] > nd:
                dist[ns] = nd
                q.append(ns)

        # ── mode switch (in place, costs 1) ──
        if switch_limit == -1 or sw_used < switch_limit:
            nmode = "white" if mode == "black" else "black"
            nsw   = sw_used + 1
            ns    = (col, row, nmode, nsw, has_key, activated)
            nd    = d + 1
            if ns not in dist or dist[ns] > nd:
                dist[ns] = nd
                q.append(ns)

    return None   # unsolvable


def compute_thresholds(optimal):
    three = optimal
    two   = math.ceil(optimal * 1.3)
    one   = math.ceil(optimal * 1.6)
    return [three, two, one]


def main():
    updated = 0
    for n in range(1, 31):
        path = os.path.join(STAGES_DIR, f"stage_{n:02d}.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        optimal = bfs_optimal(data)
        if optimal is None:
            print(f"stage {n:02d}: ERROR - BFS found no solution, file NOT modified")
            continue

        thresholds = compute_thresholds(optimal)
        data["star_thresholds"] = thresholds

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"stage {n:02d}: optimal={optimal:3d} -> {thresholds}")
        updated += 1

    print(f"\n{updated}/30 stages updated.")


if __name__ == "__main__":
    main()
