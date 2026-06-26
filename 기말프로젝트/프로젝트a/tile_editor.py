# -*- coding: utf-8 -*-
"""
한밤의관 — 타일 에디터 (독립 실행)
사용법: python tile_editor.py

편집한 결과는 room_data.py를 직접 덮어씌워 저장한다.
저장 전 room_data_backup.py 자동 백업.
"""

import os
import sys
import shutil
import pygame

# ── 상수 ─────────────────────────────────────────────────
EDITOR_W = 1280
EDITOR_H = 720
PANEL_H  = 80
WIN_H    = EDITOR_H + PANEL_H
GRID     = 32

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "Assets")

PANEL_BG = (22, 22, 32)

# ── 편집 모드 ──────────────────────────────────────────────
M_COLL = 0   # 충돌 영역
M_DOOR = 1   # 문
M_HIDE = 2   # 은신처
M_STRT = 3   # 시작 위치

M_LABEL  = ["충돌", "문", "은신처", "시작위치"]
M_FILL   = [
    (200,  50,  50, 110),   # 빨강
    ( 50, 200,  50, 110),   # 초록
    ( 50, 100, 200, 110),   # 파랑
    (220, 200,  50, 190),   # 노랑
]
M_BORDER = [
    (230,  90,  90),
    ( 90, 230,  90),
    ( 90, 140, 230),
    (245, 225,  80),
]


# ─────────────────────────────────────────────────────────
class Editor:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((EDITOR_W, WIN_H))
        pygame.display.set_caption("한밤의관 — 타일 에디터  [ESC 종료]")
        self.clock = pygame.time.Clock()

        # 폰트 (맑은 고딕 우선)
        try:
            self.fnt   = pygame.font.SysFont("malgungothic", 15)
            self.fnt_b = pygame.font.SysFont("malgungothic", 18)
        except Exception:
            self.fnt   = pygame.font.SysFont(None, 18)
            self.fnt_b = pygame.font.SysFont(None, 22)

        # room_data.py 파싱
        self.all_rooms = self._parse_rooms()
        self.keys      = list(self.all_rooms.keys())
        self.idx       = 0

        # 편집용 딥 카피 (collision_rects / doors / hide_spots / player_start)
        self.ed = {}
        for k, v in self.all_rooms.items():
            self.ed[k] = {
                "collision_rects": [tuple(r) for r in v.get("collision_rects", [])],
                "doors":           {dk: dict(dv) for dk, dv in v.get("doors", {}).items()},
                "hide_spots":      [tuple(r) for r in v.get("hide_spots", [])],
                "player_start":    tuple(v.get("player_start", (640, 400))),
            }
            # door rect를 반드시 tuple로
            for dk in self.ed[k]["doors"]:
                self.ed[k]["doors"][dk]["rect"] = tuple(self.ed[k]["doors"][dk]["rect"])
                self.ed[k]["doors"][dk]["target_pos"] = tuple(
                    self.ed[k]["doors"][dk].get("target_pos", (640, 400))
                )

        self.mode     = M_COLL
        self.grid_on  = True
        self.drag_st  = None    # 드래그 시작점 (스냅 적용)
        self.drag_cur = None    # 드래그 현재점
        self.save_t   = 0.0    # 저장 메시지 타이머
        self.bg_cache = {}
        self.mouse_pos = (0, 0)   # 현재 마우스 위치 (좌표 표시용)

        # ── 패널 버튼 Rect ────────────────────────────────
        py  = EDITOR_H
        bh  = 44
        by  = py + (PANEL_H - bh) // 2

        self.btn_prev  = pygame.Rect(10,  by, 42, bh)
        self.btn_next  = pygame.Rect(515, by, 42, bh)
        # 방 이름 표시 영역: x=58 ~ 510

        # 모드 버튼 (4개, 각 62px)
        self.btn_modes = [pygame.Rect(582 + i * 66, py + 10, 61, 60) for i in range(4)]

        # 툴 버튼
        self.btn_grid = pygame.Rect(858, by, 84, bh)
        self.btn_save = pygame.Rect(952, by, 90, bh)

    # ── room_data.py 파싱 ─────────────────────────────────
    def _parse_rooms(self):
        path = os.path.join(BASE_DIR, "room_data.py")
        with open(path, "r", encoding="utf-8") as f:
            src = f.read()
        ns = {}
        exec(src, ns)
        return ns["ROOMS"]

    # ── 배경 로드 / 캐시 ──────────────────────────────────
    def _load_bg(self, key):
        if key not in self.bg_cache:
            rel  = self.all_rooms[key].get("bg", "")
            full = os.path.join(ASSETS_DIR, rel)
            try:
                img = pygame.image.load(full).convert()
                img = pygame.transform.scale(img, (EDITOR_W, EDITOR_H))
            except Exception:
                img = pygame.Surface((EDITOR_W, EDITOR_H))
                img.fill((30, 30, 45))
                t = self.fnt_b.render(f"배경 없음: {rel}", True, (160, 160, 190))
                img.blit(t, (16, 16))
            self.bg_cache[key] = img
        return self.bg_cache[key]

    # ── 유틸 ─────────────────────────────────────────────
    def _cur_key(self): return self.keys[self.idx]
    def _cur_ed(self):  return self.ed[self._cur_key()]

    def _snap(self, v):
        return (v // GRID) * GRID if self.grid_on else v

    def _snap_pos(self, pos):
        x = max(0, min(EDITOR_W - 1, pos[0]))
        y = max(0, min(EDITOR_H - 1, pos[1]))
        return (self._snap(x), self._snap(y))

    def _in_canvas(self, pos):
        return pos[1] < EDITOR_H

    def _make_rect(self, start, end):
        sx, sy = start; ex, ey = end
        x = min(sx, ex); y = min(sy, ey)
        w = abs(ex - sx); h = abs(ey - sy)
        return (x, y, w, h)

    def _next_door_key(self, ed):
        existing = set(ed["doors"].keys())
        i = 0
        while f"door_{i}" in existing:
            i += 1
        return f"door_{i}"

    # ── 메인 루프 ────────────────────────────────────────
    def run(self):
        running = True
        while running:
            dt = self.clock.tick(60) / 1000.0
            self.save_t = max(0.0, self.save_t - dt)

            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    running = False
                elif ev.type == pygame.KEYDOWN:
                    if not self._on_key(ev):
                        running = False
                elif ev.type == pygame.MOUSEBUTTONDOWN:
                    self._on_mdown(ev)
                elif ev.type == pygame.MOUSEBUTTONUP:
                    self._on_mup(ev)
                elif ev.type == pygame.MOUSEMOTION:
                    self.mouse_pos = ev.pos
                    self._on_mmove(ev)

            self._draw()

        pygame.quit()

    # ── 키 입력 ───────────────────────────────────────────
    def _on_key(self, ev):
        k    = ev.key
        ctrl = bool(ev.mod & pygame.KMOD_CTRL)

        if k == pygame.K_ESCAPE:
            return False
        if k == pygame.K_g:
            self.grid_on = not self.grid_on
        if ctrl and k == pygame.K_s:
            self._save()
        if k == pygame.K_z:
            self._undo()
        if k == pygame.K_1: self.mode = M_COLL
        if k == pygame.K_2: self.mode = M_DOOR
        if k == pygame.K_3: self.mode = M_HIDE
        if k == pygame.K_4: self.mode = M_STRT
        if k == pygame.K_LEFT:
            self.idx = (self.idx - 1) % len(self.keys)
            self.drag_st = None
        if k == pygame.K_RIGHT:
            self.idx = (self.idx + 1) % len(self.keys)
            self.drag_st = None
        return True

    # ── 마우스 ───────────────────────────────────────────
    def _on_mdown(self, ev):
        pos = ev.pos

        if not self._in_canvas(pos):
            if ev.button == 1:
                self._on_panel_click(pos)
            return

        if ev.button == 1:
            if self.mode == M_STRT:
                sp = self._snap_pos(pos)
                self._cur_ed()["player_start"] = sp
            else:
                self.drag_st  = self._snap_pos(pos)
                self.drag_cur = self._snap_pos(pos)

        elif ev.button == 3:
            self._delete_at(pos)

    def _on_mup(self, ev):
        if ev.button == 1 and self.drag_st is not None:
            end = self._snap_pos(ev.pos)
            r   = self._make_rect(self.drag_st, end)
            if r[2] >= 4 and r[3] >= 4:
                self._add_rect(r)
            self.drag_st  = None
            self.drag_cur = None

    def _on_mmove(self, ev):
        if self.drag_st is not None:
            self.drag_cur = self._snap_pos(ev.pos)

    def _on_panel_click(self, pos):
        if self.btn_prev.collidepoint(pos):
            self.idx = (self.idx - 1) % len(self.keys)
            self.drag_st = None
        elif self.btn_next.collidepoint(pos):
            self.idx = (self.idx + 1) % len(self.keys)
            self.drag_st = None
        elif self.btn_grid.collidepoint(pos):
            self.grid_on = not self.grid_on
        elif self.btn_save.collidepoint(pos):
            self._save()
        else:
            for i, b in enumerate(self.btn_modes):
                if b.collidepoint(pos):
                    self.mode = i
                    break

    # ── 편집 액션 ────────────────────────────────────────
    def _add_rect(self, r):
        ed = self._cur_ed()
        if self.mode == M_COLL:
            ed["collision_rects"].append(r)
        elif self.mode == M_DOOR:
            dk = self._next_door_key(ed)
            ed["doors"][dk] = {
                "rect":         r,
                "target":       "EDIT_ME",
                "target_pos":   (640, 400),
                "requires_key": None,
            }
        elif self.mode == M_HIDE:
            ed["hide_spots"].append(r)

    def _delete_at(self, pos):
        x, y = pos
        ed = self._cur_ed()

        if self.mode == M_COLL:
            for i, (rx, ry, rw, rh) in enumerate(ed["collision_rects"]):
                if rx <= x < rx + rw and ry <= y < ry + rh:
                    ed["collision_rects"].pop(i)
                    return

        elif self.mode == M_DOOR:
            for dk in list(ed["doors"].keys()):
                rx, ry, rw, rh = ed["doors"][dk]["rect"]
                if rx <= x < rx + rw and ry <= y < ry + rh:
                    del ed["doors"][dk]
                    return

        elif self.mode == M_HIDE:
            for i, (rx, ry, rw, rh) in enumerate(ed["hide_spots"]):
                if rx <= x < rx + rw and ry <= y < ry + rh:
                    ed["hide_spots"].pop(i)
                    return

    def _undo(self):
        ed = self._cur_ed()
        if self.mode == M_COLL and ed["collision_rects"]:
            ed["collision_rects"].pop()
        elif self.mode == M_DOOR and ed["doors"]:
            last = list(ed["doors"].keys())[-1]
            del ed["doors"][last]
        elif self.mode == M_HIDE and ed["hide_spots"]:
            ed["hide_spots"].pop()

    # ── 렌더 ─────────────────────────────────────────────
    def _draw(self):
        key = self._cur_key()
        ed  = self._cur_ed()

        # 배경
        self.screen.blit(self._load_bg(key), (0, 0))

        # 그리드
        if self.grid_on:
            gs = pygame.Surface((EDITOR_W, EDITOR_H), pygame.SRCALPHA)
            for gx in range(0, EDITOR_W + 1, GRID):
                pygame.draw.line(gs, (50, 50, 50, 70), (gx, 0), (gx, EDITOR_H))
            for gy in range(0, EDITOR_H + 1, GRID):
                pygame.draw.line(gs, (50, 50, 50, 70), (0, gy), (EDITOR_W, gy))
            self.screen.blit(gs, (0, 0))

        # 기존 Rect 오버레이
        ov = pygame.Surface((EDITOR_W, EDITOR_H), pygame.SRCALPHA)

        def fill_rect(r, fill4, border3, bw=1):
            pygame.draw.rect(ov, fill4,             r)
            pygame.draw.rect(ov, border3 + (255,),  r, bw)

        active_bw = 2  # 현재 모드 테두리 굵기

        # 충돌
        bw = active_bw if self.mode == M_COLL else 1
        for r in ed["collision_rects"]:
            fill_rect(r, M_FILL[M_COLL], M_BORDER[M_COLL], bw)

        # 문
        bw = active_bw if self.mode == M_DOOR else 1
        for dk, dv in ed["doors"].items():
            r = dv["rect"]
            fill_rect(r, M_FILL[M_DOOR], M_BORDER[M_DOOR], bw)
            # "DOOR" 레이블
            lt = self.fnt.render("DOOR", True, M_BORDER[M_DOOR])
            ov.blit(lt, (r[0] + 3, r[1] + 3))

        # 은신처
        bw = active_bw if self.mode == M_HIDE else 1
        for r in ed["hide_spots"]:
            fill_rect(r, M_FILL[M_HIDE], M_BORDER[M_HIDE], bw)

        self.screen.blit(ov, (0, 0))

        # 시작 위치 (원)
        ps = ed["player_start"]
        pygame.draw.circle(self.screen, M_FILL[M_STRT][:3], ps, 14)
        pygame.draw.circle(self.screen, M_BORDER[M_STRT], ps, 14,
                           3 if self.mode == M_STRT else 2)
        st = self.fnt.render("S", True, M_BORDER[M_STRT])
        self.screen.blit(st, (ps[0] - st.get_width() // 2, ps[1] - st.get_height() // 2))

        # 드래그 미리보기
        if self.drag_st and self.drag_cur and self.mode != M_STRT:
            dr = self._make_rect(self.drag_st, self.drag_cur)
            if dr[2] > 0 and dr[3] > 0:
                pv = pygame.Surface((EDITOR_W, EDITOR_H), pygame.SRCALPHA)
                pygame.draw.rect(pv, M_FILL[self.mode],             dr)
                pygame.draw.rect(pv, M_BORDER[self.mode] + (255,),  dr, 2)
                self.screen.blit(pv, (0, 0))
                # 드래그 크기 표시
                info = f"{dr[2]} × {dr[3]}"
                it = self.fnt.render(info, True, (255, 255, 200))
                self.screen.blit(it, (dr[0] + 4, dr[1] + 4))

        # 패널
        self._draw_panel(ed, key)

        # 저장 완료 메시지
        if self.save_t > 0:
            msg = self.fnt_b.render("✔  저장 완료!", True, (100, 255, 120))
            bx  = (EDITOR_W - msg.get_width()) // 2
            bg  = pygame.Surface((msg.get_width() + 24, msg.get_height() + 12), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 200))
            self.screen.blit(bg,  (bx - 12, EDITOR_H // 2 - 6))
            self.screen.blit(msg, (bx,       EDITOR_H // 2))

        pygame.display.flip()

    def _draw_panel(self, ed, key):
        py = EDITOR_H

        # 패널 배경
        pygame.draw.rect(self.screen, PANEL_BG, (0, py, EDITOR_W, PANEL_H))
        pygame.draw.line(self.screen, (55, 55, 80), (0, py), (EDITOR_W, py), 2)

        def draw_btn(rect, text, active=False, bg_col=None):
            col = bg_col if bg_col else ((55, 85, 55) if active else (38, 38, 58))
            pygame.draw.rect(self.screen, col, rect)
            pygame.draw.rect(self.screen, (70, 70, 100), rect, 1)
            t = self.fnt_b.render(text, True, (240, 240, 245))
            self.screen.blit(t, (rect.centerx - t.get_width() // 2,
                                  rect.centery - t.get_height() // 2))

        # ◀ ▶
        draw_btn(self.btn_prev, "◀")
        draw_btn(self.btn_next, "▶")

        # 방 이름 (1/10 형식)
        name = f"  {self.idx + 1}/{len(self.keys)}   {key}"
        nt   = self.fnt_b.render(name, True, (190, 205, 230))
        self.screen.blit(nt, (self.btn_prev.right + 6,
                               py + (PANEL_H - nt.get_height()) // 2))

        # 모드 버튼
        for i, (b, lbl) in enumerate(zip(self.btn_modes, M_LABEL)):
            active = (i == self.mode)
            bg  = tuple(min(255, c) for c in M_BORDER[i]) if active else (38, 38, 58)
            draw_btn(b, lbl, bg_col=bg)

        # 구분선
        pygame.draw.line(self.screen, (55, 55, 80), (848, py + 8), (848, py + PANEL_H - 8))

        # G 그리드 / 저장
        draw_btn(self.btn_grid, "G 그리드", self.grid_on)
        draw_btn(self.btn_save, "저  장",  bg_col=(38, 68, 38))

        # 통계 (우측 하단)
        nc = len(ed["collision_rects"])
        nd = len(ed["doors"])
        nh = len(ed["hide_spots"])
        stat = f"충돌:{nc}  문:{nd}  은신:{nh}"
        st   = self.fnt.render(stat, True, (120, 130, 150))
        self.screen.blit(st, (EDITOR_W - st.get_width() - 10, py + PANEL_H - st.get_height() - 5))

        # 마우스 좌표 표시
        mx, my = self.mouse_pos
        if self._in_canvas(self.mouse_pos):
            coord = f"({mx}, {my})"
            if self.grid_on:
                sx, sy = self._snap(mx), self._snap(my)
                coord = f"({sx}, {sy})  raw({mx},{my})"
            ct = self.fnt.render(coord, True, (160, 170, 190))
            self.screen.blit(ct, (10, py + PANEL_H - ct.get_height() - 5))

        # 단축키 힌트 (우측 상단)
        hints = "1:충돌  2:문  3:은신  4:시작  G:그리드  Z:취소  Ctrl+S:저장  ◀▶:방 선택  ESC:종료"
        ht = self.fnt.render(hints, True, (75, 80, 100))
        self.screen.blit(ht, (EDITOR_W - ht.get_width() - 10, py + 6))

    # ── 저장 ─────────────────────────────────────────────
    def _save(self):
        src = os.path.join(BASE_DIR, "room_data.py")
        bak = os.path.join(BASE_DIR, "room_data_backup.py")

        # 백업
        if os.path.exists(src):
            shutil.copy2(src, bak)

        # 편집 결과를 all_rooms에 병합
        for k in self.keys:
            e = self.ed[k]
            self.all_rooms[k]["collision_rects"] = list(e["collision_rects"])
            self.all_rooms[k]["doors"]           = dict(e["doors"])
            self.all_rooms[k]["hide_spots"]      = list(e["hide_spots"])
            self.all_rooms[k]["player_start"]    = tuple(e["player_start"])

        code = self._gen_code()
        with open(src, "w", encoding="utf-8") as f:
            f.write(code)

        self.save_t = 2.0

    def _gen_code(self):
        """room_data.py 전체를 새로 생성한다. 편집 불가 필드는 그대로 유지."""
        L = [
            "# -*- coding: utf-8 -*-\n",
            "# room_data.py — tile_editor.py 로 자동 생성\n",
            "# collision_rects / doors / hide_spots / player_start 는\n",
            "# tile_editor.py 로 편집하세요.\n\n",
            "ROOMS = {\n",
        ]

        for key, data in self.all_rooms.items():
            L.append(f'    "{key}": {{\n')
            L.append(f'        "bg": {repr(data["bg"])},\n')
            L.append(f'        "music": {repr(data.get("music", ""))},\n')

            # collision_rects
            L.append( '        "collision_rects": [\n')
            for r in data.get("collision_rects", []):
                L.append(f'            {tuple(r)},\n')
            L.append( '        ],\n')

            # doors
            L.append( '        "doors": {\n')
            for dk, dv in data.get("doors", {}).items():
                L.append(f'            "{dk}": {{\n')
                L.append(f'                "rect":         {tuple(dv["rect"])},\n')
                L.append(f'                "target":       {repr(dv["target"])},\n')
                L.append(f'                "target_pos":   {tuple(dv.get("target_pos", (640, 400)))},\n')
                L.append(f'                "requires_key": {repr(dv.get("requires_key"))},\n')
                L.append( '            },\n')
            L.append( '        },\n')

            # hide_spots
            L.append( '        "hide_spots": [\n')
            for r in data.get("hide_spots", []):
                L.append(f'            {tuple(r)},\n')
            L.append( '        ],\n')

            # player_start
            L.append(f'        "player_start": {tuple(data.get("player_start", (640, 400)))},\n')

            # 편집 불가 필드 보존
            for field in ("item_spawns", "npc_spawns", "interactables"):
                val = data.get(field, [])
                L.append(f'        "{field}": {repr(val)},\n')

            L.append( '    },\n')

        L.append("}\n")
        return "".join(L)


# ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    Editor().run()
