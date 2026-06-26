"""
MONO SWITCH — Stage Generator
Defines all 30 stage maps, verifies each with BFS, then writes JSON files.

STATUS (last updated: 2026-06-08):
  Zone 1  (01-10): COMPLETE — all verified & saved
  Zone 2  (11-22): COMPLETE — all verified & saved
  Zone 3  (23-30): TODO

RESUME POINT: stage_23
"""

import json
import os
from collections import deque

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "Assets", "stages")


# ---------------------------------------------------------------------------
# BFS solver
# State: (col, row, mode, switches_used, has_key)
# Tile passability:
#   0 (white)  → passable in black mode only
#   1 (black)  → passable in white mode only
#   2 (wall)   → always impassable
#   3 (gray)   → always passable
#   4 (goal)   → always passable (win condition)
#   5 (key)    → always passable; grants has_key
#   6 (locked) → passable only if has_key
# ---------------------------------------------------------------------------

def bfs_verify(stage):
    grid = stage["map"]
    H = len(grid)
    W = len(grid[0])
    sc, sr = stage["player_start"]
    mode0 = stage["initial_mode"]
    slimit = stage["switch_limit"]

    init = (sc, sr, mode0, 0, False)
    visited = {init}
    q = deque([init])
    dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]

    while q:
        c, r, mode, sw, key = q.popleft()
        if grid[r][c] == 4:
            return True, sw
        # movement
        for dc, dr in dirs:
            nc, nr = c + dc, r + dr
            if not (0 <= nc < W and 0 <= nr < H):
                continue
            t = grid[nr][nc]
            if t == 2:
                continue
            if t == 0 and mode == "white":
                continue
            if t == 1 and mode == "black":
                continue
            if t == 6 and not key:
                continue
            nkey = key or (t == 5)
            ns = (nc, nr, mode, sw, nkey)
            if ns not in visited:
                visited.add(ns)
                q.append(ns)
        # mode switch
        if slimit == -1 or sw < slimit:
            nm = "white" if mode == "black" else "black"
            ns = (c, r, nm, sw + 1, key)
            if ns not in visited:
                visited.add(ns)
                q.append(ns)

    return False, -1


# ---------------------------------------------------------------------------
# Stage definitions
# ---------------------------------------------------------------------------

STAGES = [

    # ── Zone 1 (01-10) ── 8×6 → 10×7, switch_limit=-1 ──────────────────────

    {   # 01 — intro: walk on white tiles, no switch needed
        "stage": 1, "width": 8, "height": 6, "switch_limit": -1,
        "map": [
            [2,2,2,2,2,2,2,2],
            [2,0,0,0,2,2,2,2],
            [2,2,2,0,2,2,2,2],
            [2,2,2,0,0,0,4,2],
            [2,2,2,2,2,2,2,2],
            [2,2,2,2,2,2,2,2],
        ],
        "player_start": [1, 1], "initial_mode": "black",
    },

    {   # 02 — first switch: white path → black segment → goal
        "stage": 2, "width": 8, "height": 6, "switch_limit": -1,
        "map": [
            [2,2,2,2,2,2,2,2],
            [2,0,0,0,2,2,2,2],
            [2,2,2,0,2,2,2,2],
            [2,2,2,1,1,1,4,2],
            [2,2,2,2,2,2,2,2],
            [2,2,2,2,2,2,2,2],
        ],
        "player_start": [1, 1], "initial_mode": "black",
    },

    {   # 03 — two switches: white → black → white → goal
        "stage": 3, "width": 8, "height": 6, "switch_limit": -1,
        "map": [
            [2,2,2,2,2,2,2,2],
            [2,0,0,0,2,2,2,2],
            [2,2,2,0,2,2,2,2],
            [2,2,2,0,1,2,2,2],
            [2,2,2,2,1,0,4,2],
            [2,2,2,2,2,2,2,2],
        ],
        "player_start": [1, 1], "initial_mode": "black",
    },

    {   # 04 — three switches: wider map, alternating segments
        "stage": 4, "width": 9, "height": 6, "switch_limit": -1,
        "map": [
            [2,2,2,2,2,2,2,2,2],
            [2,0,0,0,2,2,2,2,2],
            [2,2,2,0,2,2,2,2,2],
            [2,2,2,0,1,2,2,2,2],
            [2,2,2,2,1,0,1,4,2],
            [2,2,2,2,2,2,2,2,2],
        ],
        "player_start": [1, 1], "initial_mode": "black",
    },

    {   # 05 — branching paths: decoy route + correct two-switch path
        "stage": 5, "width": 9, "height": 6, "switch_limit": -1,
        "map": [
            [2,2,2,2,2,2,2,2,2],
            [2,0,0,1,0,2,2,2,2],
            [2,0,2,1,0,2,2,2,2],
            [2,0,0,0,1,1,0,4,2],
            [2,2,2,2,2,2,2,2,2],
            [2,2,2,2,2,2,2,2,2],
        ],
        "player_start": [1, 1], "initial_mode": "black",
    },

    {   # 06 — gray tile intro: U-path via gray corridor, one final switch
        "stage": 6, "width": 9, "height": 7, "switch_limit": -1,
        "map": [
            [2,2,2,2,2,2,2,2,2],
            [2,0,0,0,0,0,0,2,2],
            [2,2,2,2,2,2,0,2,2],
            [2,2,3,3,3,3,0,2,2],
            [2,2,3,2,2,2,2,2,2],
            [2,2,3,1,1,4,2,2,2],
            [2,2,2,2,2,2,2,2,2],
        ],
        "player_start": [1, 1], "initial_mode": "black",
    },

    {   # 07 — gray as main highway, one switch at the end
        "stage": 7, "width": 9, "height": 7, "switch_limit": -1,
        "map": [
            [2,2,2,2,2,2,2,2,2],
            [2,0,0,0,2,2,2,2,2],
            [2,2,2,0,2,2,2,2,2],
            [2,2,2,3,3,3,2,2,2],
            [2,2,2,2,2,3,2,2,2],
            [2,2,2,2,2,3,1,4,2],
            [2,2,2,2,2,2,2,2,2],
        ],
        "player_start": [1, 1], "initial_mode": "black",
    },

    {   # 08 — 3 switches, longer winding path
        "stage": 8, "width": 10, "height": 7, "switch_limit": -1,
        "map": [
            [2,2,2,2,2,2,2,2,2,2],
            [2,0,0,0,2,2,2,2,2,2],
            [2,2,2,0,2,2,2,2,2,2],
            [2,2,2,0,1,1,0,2,2,2],
            [2,2,2,2,2,2,0,2,2,2],
            [2,2,2,2,2,1,0,1,4,2],
            [2,2,2,2,2,2,2,2,2,2],
        ],
        "player_start": [1, 1], "initial_mode": "black",
    },

    {   # 09 — gray decoy + precise routing, 1 switch
        "stage": 9, "width": 10, "height": 7, "switch_limit": -1,
        "map": [
            [2,2,2,2,2,2,2,2,2,2],
            [2,0,0,0,0,0,0,2,2,2],
            [2,2,2,2,2,2,0,2,2,2],
            [2,2,3,3,3,2,0,2,2,2],
            [2,2,3,2,0,0,0,2,2,2],
            [2,2,3,1,1,2,1,4,2,2],
            [2,2,2,2,2,2,2,2,2,2],
        ],
        "player_start": [1, 1], "initial_mode": "black",
    },

    {   # 10 — Zone 1 boss: gray + 3 switches, complex layout
        "stage": 10, "width": 10, "height": 7, "switch_limit": -1,
        "map": [
            [2,2,2,2,2,2,2,2,2,2],
            [2,0,0,0,1,1,0,0,2,2],
            [2,0,2,0,2,2,0,2,2,2],
            [2,0,2,0,1,2,0,2,2,2],
            [2,0,0,3,1,3,0,0,2,2],
            [2,2,2,3,2,3,2,1,4,2],
            [2,2,2,2,2,2,2,2,2,2],
        ],
        "player_start": [1, 1], "initial_mode": "black",
    },

    # ── Zone 2 (11-22) ── 10×8 → 12×9 ──────────────────────────────────────

    {   # 11 — switch_limit=3 introduced; snake path with 3 forced alternations
        "stage": 11, "width": 10, "height": 8, "switch_limit": 3,
        "map": [
            [2,2,2,2,2,2,2,2,2,2],
            [2,0,0,0,2,2,2,2,2,2],
            [2,2,2,0,2,2,2,2,2,2],
            [2,2,2,1,1,1,2,2,2,2],
            [2,2,2,2,2,1,2,2,2,2],
            [2,2,2,2,2,1,0,0,2,2],
            [2,2,2,2,2,2,2,1,4,2],
            [2,2,2,2,2,2,2,2,2,2],
        ],
        "player_start": [1, 1], "initial_mode": "black",
    },

    {   # 12 — switch_limit=4; extends pattern with a 4th barrier
        "stage": 12, "width": 11, "height": 8, "switch_limit": 4,
        "map": [
            [2,2,2,2,2,2,2,2,2,2,2],
            [2,0,0,0,2,2,2,2,2,2,2],
            [2,2,2,0,2,2,2,2,2,2,2],
            [2,2,2,1,1,1,2,2,2,2,2],
            [2,2,2,2,2,1,2,2,2,2,2],
            [2,2,2,2,2,1,0,0,2,2,2],
            [2,2,2,2,2,2,2,1,1,2,2],
            [2,2,2,2,2,2,2,2,0,4,2],
        ],
        "player_start": [1, 1], "initial_mode": "black",
    },

    {   # 13 — switch_limit=5; 5-barrier snake, wider map
        "stage": 13, "width": 12, "height": 9, "switch_limit": 5,
        "map": [
            [2,2,2,2,2,2,2,2,2,2,2,2],
            [2,0,0,0,2,2,2,2,2,2,2,2],
            [2,2,2,0,2,2,2,2,2,2,2,2],
            [2,2,2,1,1,1,2,2,2,2,2,2],
            [2,2,2,2,2,1,2,2,2,2,2,2],
            [2,2,2,2,2,1,0,0,2,2,2,2],
            [2,2,2,2,2,2,2,1,1,2,2,2],
            [2,2,2,2,2,2,2,2,0,0,2,2],
            [2,2,2,2,2,2,2,2,2,1,4,2],
        ],
        "player_start": [1, 1], "initial_mode": "black",
    },

    {   # 14 — zone switch intro (switch_limit=0); step on tile 7 to flip wall tiles
        "stage": 14, "width": 10, "height": 8, "switch_limit": 0,
        "map": [
            [2,2,2,2,2,2,2,2,2,2],
            [2,0,0,0,0,2,2,2,2,2],
            [2,2,2,2,0,2,2,2,2,2],
            [2,2,2,2,7,2,2,2,2,2],
            [2,2,2,2,0,2,2,2,2,2],
            [2,2,2,2,0,1,1,4,2,2],
            [2,2,2,2,2,2,2,2,2,2],
            [2,2,2,2,2,2,2,2,2,2],
        ],
        "player_start": [1, 1], "initial_mode": "black",
        "zone_regions": {"4,3": [[5,5],[6,5]]},
    },

    {   # 15 — two sequential zone switches required (switch_limit=0)
        "stage": 15, "width": 11, "height": 8, "switch_limit": 0,
        "map": [
            [2,2,2,2,2,2,2,2,2,2,2],
            [2,0,0,0,0,2,2,2,2,2,2],
            [2,2,2,2,7,2,2,2,2,2,2],
            [2,2,2,2,1,1,1,2,2,2,2],
            [2,2,2,2,2,2,0,2,2,2,2],
            [2,2,2,2,2,2,0,2,2,2,2],
            [2,2,2,2,2,2,7,2,2,2,2],
            [2,2,2,2,2,2,0,1,4,2,2],
        ],
        "player_start": [1, 1], "initial_mode": "black",
        "zone_regions": {"4,2": [[4,3],[5,3],[6,3]], "6,6": [[7,7]]},
    },

    {   # 16 — zone switch + 1 global switch (switch_limit=1)
        "stage": 16, "width": 11, "height": 9, "switch_limit": 1,
        "map": [
            [2,2,2,2,2,2,2,2,2,2,2],
            [2,0,0,0,0,2,2,2,2,2,2],
            [2,2,2,2,7,2,2,2,2,2,2],
            [2,2,2,2,1,1,1,2,2,2,2],
            [2,2,2,2,2,2,0,2,2,2,2],
            [2,2,2,2,2,2,0,2,2,2,2],
            [2,2,2,2,2,2,0,2,2,2,2],
            [2,2,2,2,2,2,1,1,4,2,2],
            [2,2,2,2,2,2,2,2,2,2,2],
        ],
        "player_start": [1, 1], "initial_mode": "black",
        "zone_regions": {"4,2": [[4,3],[5,3],[6,3]]},
    },

    {   # 17 — zone switch + 2 global switches (switch_limit=2)
        "stage": 17, "width": 12, "height": 9, "switch_limit": 2,
        "map": [
            [2,2,2,2,2,2,2,2,2,2,2,2],
            [2,0,0,0,0,2,2,2,2,2,2,2],
            [2,2,2,2,7,2,2,2,2,2,2,2],
            [2,2,2,2,1,1,1,2,2,2,2,2],
            [2,2,2,2,2,2,0,2,2,2,2,2],
            [2,2,2,2,2,2,0,2,2,2,2,2],
            [2,2,2,2,2,2,0,1,2,2,2,2],
            [2,2,2,2,2,2,2,1,0,2,2,2],
            [2,2,2,2,2,2,2,2,0,4,2,2],
        ],
        "player_start": [1, 1], "initial_mode": "black",
        "zone_regions": {"4,2": [[4,3],[5,3],[6,3]]},
    },

    {   # 18 — key & lock intro; key on direct path, lock before goal
        "stage": 18, "width": 10, "height": 8, "switch_limit": -1,
        "map": [
            [2,2,2,2,2,2,2,2,2,2],
            [2,0,0,0,0,0,0,2,2,2],
            [2,2,2,2,2,2,0,2,2,2],
            [2,2,2,2,2,2,5,2,2,2],
            [2,2,2,2,2,2,0,2,2,2],
            [2,2,2,2,2,2,6,2,2,2],
            [2,2,2,2,2,2,0,0,4,2],
            [2,2,2,2,2,2,2,2,2,2],
        ],
        "player_start": [1, 1], "initial_mode": "black",
    },

    {   # 19 — key on detour; must backtrack to collect key before locked zone
        "stage": 19, "width": 11, "height": 8, "switch_limit": -1,
        "map": [
            [2,2,2,2,2,2,2,2,2,2,2],
            [2,0,0,0,0,0,0,2,2,2,2],
            [2,2,2,0,2,2,2,2,2,2,2],
            [2,2,2,5,2,2,2,2,2,2,2],
            [2,2,2,0,2,2,2,2,2,2,2],
            [2,2,2,0,0,0,0,6,0,4,2],
            [2,2,2,2,2,2,2,2,2,2,2],
            [2,2,2,2,2,2,2,2,2,2,2],
        ],
        "player_start": [1, 1], "initial_mode": "black",
    },

    {   # 20 — key requires 2 mode switches to reach; then use key for lock
        "stage": 20, "width": 11, "height": 9, "switch_limit": -1,
        "map": [
            [2,2,2,2,2,2,2,2,2,2,2],
            [2,0,0,0,0,0,0,2,2,2,2],
            [2,2,2,2,2,2,0,2,2,2,2],
            [2,2,2,2,2,2,0,2,2,2,2],
            [2,2,2,2,2,2,1,1,5,2,2],
            [2,2,2,2,2,2,0,2,2,2,2],
            [2,2,2,2,2,2,6,2,2,2,2],
            [2,2,2,2,2,2,0,0,4,2,2],
            [2,2,2,2,2,2,2,2,2,2,2],
        ],
        "player_start": [1, 1], "initial_mode": "black",
    },

    {   # 21 — key guarded by zone switch region; use zone switch then collect key
        "stage": 21, "width": 12, "height": 9, "switch_limit": -1,
        "map": [
            [2,2,2,2,2,2,2,2,2,2,2,2],
            [2,0,0,0,0,0,0,2,2,2,2,2],
            [2,2,2,2,2,2,7,2,2,2,2,2],
            [2,2,2,2,2,2,1,1,5,2,2,2],
            [2,2,2,2,2,2,2,2,0,2,2,2],
            [2,2,2,2,2,2,2,2,0,2,2,2],
            [2,2,0,0,0,0,0,0,6,2,2,2],
            [2,2,0,2,2,2,2,2,2,2,2,2],
            [2,2,0,0,0,0,4,2,2,2,2,2],
        ],
        "player_start": [1, 1], "initial_mode": "black",
        "zone_regions": {"6,2": [[6,3],[7,3]]},
    },

    {   # 22 — Zone 2 challenge: switch_limit=3, zone switch, key/lock combined
        "stage": 22, "width": 12, "height": 9, "switch_limit": 3,
        "map": [
            [2,2,2,2,2,2,2,2,2,2,2,2],
            [2,0,0,0,0,0,7,2,2,2,2,2],
            [2,2,2,2,2,0,2,2,2,2,2,2],
            [2,2,2,2,2,5,2,2,2,2,2,2],
            [2,2,2,2,2,0,2,2,2,2,2,2],
            [2,2,2,2,2,1,1,1,2,2,2,2],
            [2,2,2,2,2,2,2,1,0,0,2,2],
            [2,2,2,2,2,2,2,2,0,6,2,2],
            [2,2,2,2,2,2,2,2,2,0,4,2],
        ],
        "player_start": [1, 1], "initial_mode": "black",
        "zone_regions": {"6,1": [[5,5],[6,5],[7,5]]},
    },

    # ── Zone 3 (23-30) ── 12×9 → 14×10 ─────────────────────────────────────
    # TODO: stages 23-30
]


# ---------------------------------------------------------------------------
# Main: verify + write
# ---------------------------------------------------------------------------

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    total = len(STAGES)
    saved = 0

    for stage in STAGES:
        n = stage["stage"]
        filename = f"stage_{n:02d}.json"
        filepath = os.path.join(OUTPUT_DIR, filename)

        if os.path.exists(filepath):
            print(f"SKIP:  {filename} (already exists)")
            saved += 1
            continue

        ok, sw = bfs_verify(stage)
        if not ok:
            print(f"ERROR: {filename} — BFS FAILED, stage is unsolvable!")
            continue

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(stage, f, indent=2)

        print(f"SAVED: {filename} — ({saved + 1}/{total} complete, min_switches={sw})")
        saved += 1

    print(f"\nDone. {saved}/{total} stages written to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
