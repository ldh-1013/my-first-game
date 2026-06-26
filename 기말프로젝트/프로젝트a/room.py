# -*- coding: utf-8 -*-
import math
import pygame
from room_data import ROOMS

class Room:
    """방 하나의 상태(배경·충돌·문·오브젝트)를 관리한다."""

    INTERACT_RADIUS = 60  # 상호작용 가능 거리 (px)
    DOOR_RADIUS     = 50  # 문 진입 감지 거리 (px)

    def __init__(self, room_id, loader):
        data = ROOMS.get(room_id)
        if data is None:
            raise KeyError(f"알 수 없는 방 ID: {room_id}")

        self.room_id = room_id
        self.data    = data
        self.music   = data.get("music", "")

        # 배경 이미지
        self.bg = loader.load_bg(data["bg"])

        # 충돌 사각형 목록 (pygame.Rect)
        self.collision_rects = [
            pygame.Rect(x, y, w, h)
            for (x, y, w, h) in data.get("collision_rects", [])
        ]

        # 문 정의: 이름 → {rect: Rect, target, target_pos, requires_key}
        self.doors = {}
        for name, d in data.get("doors", {}).items():
            self.doors[name] = {
                "rect":         pygame.Rect(*d["rect"]),
                "target":       d["target"],
                "target_pos":   d["target_pos"],
                "requires_key": d.get("requires_key"),
            }

        # 은신처 (Phase 2+)
        self.hide_spots = [
            pygame.Rect(*h) for h in data.get("hide_spots", [])
        ]

        # 상호작용 오브젝트 (Phase 2+) — 픽업 후 remove가 가능하도록 복사본 사용
        self.interactables = list(data.get("interactables", []))

        # 아이템 스폰 목록 (Phase 2+에서 게임 오브젝트로 변환)
        self.item_spawns = list(data.get("item_spawns", []))

    # ── 렌더 ─────────────────────────────────────────────
    def draw(self, surface):
        surface.blit(self.bg, (0, 0))
        self._draw_item_markers(surface)

    def _draw_item_markers(self, surface):
        """아이템 위치에 반짝이는 마커 표시."""
        t = pygame.time.get_ticks() / 1000.0
        for obj in self.interactables:
            ox, oy = obj["pos"]
            act    = obj.get("action", "")
            if act == "pickup":
                alpha = int(160 + 80 * math.sin(t * 3.5))
                size  = 9
                pts   = [(ox, oy - size), (ox + size, oy),
                         (ox, oy + size), (ox - size, oy)]
                m  = pygame.Surface((size * 2 + 4, size * 2 + 4), pygame.SRCALPHA)
                lp = [(p[0] - ox + size + 2, p[1] - oy + size + 2) for p in pts]
                pygame.draw.polygon(m, (200, 169, 110, alpha),            lp)
                pygame.draw.polygon(m, (255, 220, 130, min(255, alpha + 40)), lp, 1)
                surface.blit(m, (ox - size - 2, oy - size - 2))
            elif act in ("read_note", "examine"):
                alpha2 = int(120 + 60 * math.sin(t * 2.2))
                m2 = pygame.Surface((24, 24), pygame.SRCALPHA)
                pygame.draw.circle(m2, (200, 200, 255, alpha2), (12, 12), 9, 2)
                surface.blit(m2, (ox - 12, oy - 12))

    def draw_debug(self, surface):
        """충돌 영역·문 영역 시각화 (개발용 F9 디버그 모드)."""
        for r in self.collision_rects:
            pygame.draw.rect(surface, (255, 0, 0), r, 1)
        for name, d in self.doors.items():
            pygame.draw.rect(surface, (0, 255, 0), d["rect"], 2)

    # ── 충돌 조회 ─────────────────────────────────────────
    def get_collision_rects(self):
        return self.collision_rects

    # ── 문 조회 ──────────────────────────────────────────
    def get_door_at(self, player_rect):
        """플레이어 rect가 문 rect와 겹치면 해당 문 정보 반환, 없으면 None."""
        for name, d in self.doors.items():
            if player_rect.colliderect(d["rect"]):
                return d
        return None

    def nearest_door(self, pos):
        """pos 에서 가장 가까운 문과 거리 반환. (door_info, dist) 또는 (None, inf)."""
        best, best_d = None, float("inf")
        px, py = pos
        for d in self.doors.values():
            cx = d["rect"].centerx
            cy = d["rect"].centery
            dist = ((px - cx) ** 2 + (py - cy) ** 2) ** 0.5
            if dist < best_d:
                best, best_d = d, dist
        return best, best_d

    # ── 은신처 조회 ──────────────────────────────────────
    def nearest_hide_spot(self, pos):
        """가장 가까운 은신처와 거리 반환. (Rect, dist) 또는 (None, inf)."""
        best, best_d = None, float("inf")
        px, py = pos
        for r in self.hide_spots:
            dist = ((px - r.centerx) ** 2 + (py - r.centery) ** 2) ** 0.5
            if dist < best_d:
                best, best_d = r, dist
        return best, best_d

    # ── 상호작용 오브젝트 제거 ───────────────────────────
    def remove_interactable(self, obj):
        """아이템 픽업 후 호출 — 해당 오브젝트를 목록에서 제거한다."""
        if obj in self.interactables:
            self.interactables.remove(obj)

    # ── 상호작용 오브젝트 조회 ───────────────────────────
    def get_interactable_at(self, pos):
        """pos 근처(INTERACT_RADIUS 이내) 상호작용 오브젝트 반환, 없으면 None."""
        px, py = pos
        for obj in self.interactables:
            ox, oy = obj["pos"]
            if ((px - ox) ** 2 + (py - oy) ** 2) ** 0.5 <= self.INTERACT_RADIUS:
                return obj
        return None
