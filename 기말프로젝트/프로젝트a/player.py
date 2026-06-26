# -*- coding: utf-8 -*-
import math
import pygame
from settings import (
    PLAYER_SIZE, PLAYER_SPRITE_SIZE,
    PLAYER_SPEED_WALK, PLAYER_SPEED_RUN,
    LIGHTER_DRAIN, LIGHTER_R_FULL, LIGHTER_R_LOW, LIGHTER_R_VERY,
)

# 스프라이트 상대 경로 (Assets/ 기준)
_SPR_BASE = "characters/sprites/Hajun"
_SPRITE_PATHS = {
    # ── idle (현재 보유한 이미지) ──────────────────────────
    "idle_down":  f"{_SPR_BASE}/player_idle_down.png",
    "idle_up":    f"{_SPR_BASE}/player_idle_up.png",
    "idle_left":  f"{_SPR_BASE}/player_idle_left.png",
    "idle_right": f"{_SPR_BASE}/player_idle_right.png",
    "hide":       f"{_SPR_BASE}/player_hide.png",
    # ── walk (나중에 이미지 추가 시 경로 입력, 지금은 None → idle fallback)
    "walk_down_0":  None,
    "walk_down_1":  None,
    "walk_up_0":    None,
    "walk_up_1":    None,
    "walk_left_0":  None,
    "walk_left_1":  None,
    "walk_right_0": None,
    "walk_right_1": None,
}

class Player:
    """플레이어(하준) 클래스 — 이동·충돌·라이터·은신·bob 애니메이션 담당."""

    FOOTSTEP_WALK_INTERVAL = 0.45
    FOOTSTEP_RUN_INTERVAL  = 0.25

    def __init__(self, pos, loader):
        self.loader = loader

        # ── 위치·사각형 ───────────────────────────────────
        cw, ch = PLAYER_SIZE                        # 충돌박스: 40 × 28
        self.rect = pygame.Rect(0, 0, cw, ch)
        self.rect.center = (int(pos[0]), int(pos[1]))
        self.sprite_w, self.sprite_h = PLAYER_SPRITE_SIZE  # 스프라이트: 72 × 96

        # ── 방향·상태 ─────────────────────────────────────
        self.direction  = "down"
        self.is_hiding  = False
        self.is_running = False
        self._is_moving = False

        # ── 라이터 ───────────────────────────────────────
        self.lighter_on = False
        self.oil        = 100.0

        # ── Bob 애니메이션 ────────────────────────────────
        self._bob_timer  = 0.0   # 누적 이동 시간
        self._bob_offset = 0.0   # 현재 y 오프셋 (px)

        # ── 발소리 / 워크 프레임 ──────────────────────────
        self._step_timer = 0.0
        self._walk_frame = 0     # 0=L, 1=R  (walk 프레임 인덱스)

        # ── 스프라이트 캐시 (None 경로는 None으로 저장) ──
        spr_size = (self.sprite_w, self.sprite_h)
        self._sprites = {}
        for key, path in _SPRITE_PATHS.items():
            if path is not None:
                self._sprites[key] = loader.load_sprite(path, spr_size)
            else:
                self._sprites[key] = None   # 나중에 이미지 추가 시 채움

    # ── 업데이트 ─────────────────────────────────────────
    def update(self, keys, room, dt, sound=None):
        # ── 이동 방향 계산 ────────────────────────────────
        dx = dy = 0
        if keys[pygame.K_LEFT]  or keys[pygame.K_a]: dx = -1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: dx =  1
        if keys[pygame.K_UP]    or keys[pygame.K_w]: dy = -1
        if keys[pygame.K_DOWN]  or keys[pygame.K_s]: dy =  1

        if dx != 0 and dy != 0:
            dx *= 0.7071
            dy *= 0.7071

        self.is_running = (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]) and bool(dx or dy)
        speed = PLAYER_SPEED_RUN if self.is_running else PLAYER_SPEED_WALK
        self._is_moving = bool(dx or dy)

        # ── 방향 업데이트 ─────────────────────────────────
        if not self.is_hiding:
            if   dx < 0: self.direction = "left"
            elif dx > 0: self.direction = "right"
            elif dy < 0: self.direction = "up"
            elif dy > 0: self.direction = "down"

        # ── 충돌 처리 (x/y 분리) ─────────────────────────
        move_x = dx * speed * dt
        move_y = dy * speed * dt

        self.rect.x += int(move_x)
        for col in room.get_collision_rects():
            if self.rect.colliderect(col):
                if move_x > 0: self.rect.right  = col.left
                elif move_x < 0: self.rect.left = col.right

        self.rect.y += int(move_y)
        for col in room.get_collision_rects():
            if self.rect.colliderect(col):
                if move_y > 0: self.rect.bottom = col.top
                elif move_y < 0: self.rect.top  = col.bottom

        from settings import INTERNAL_W, INTERNAL_H
        self.rect.clamp_ip(pygame.Rect(0, 0, INTERNAL_W, INTERNAL_H))

        # ── Bob 애니메이션 ────────────────────────────────
        if self._is_moving:
            spd = 10.0 if self.is_running else 7.0
            self._bob_timer  += dt * spd
            self._bob_offset  = math.sin(self._bob_timer) * 3.5
        else:
            self._bob_offset *= max(0.0, 1.0 - dt * 12)
            if abs(self._bob_offset) < 0.1:
                self._bob_offset = 0.0
                self._bob_timer  = 0.0

        # ── 발소리 ────────────────────────────────────────
        if self._is_moving and sound:
            interval = self.FOOTSTEP_RUN_INTERVAL if self.is_running else self.FOOTSTEP_WALK_INTERVAL
            self._step_timer += dt
            if self._step_timer >= interval:
                self._step_timer = 0.0
                sfx = "footstep_L" if self._walk_frame == 0 else "footstep_R"
                sound.play_sfx(sfx)
                self._walk_frame ^= 1
        else:
            self._step_timer = 0.0

        # ── 라이터 기름 소모 ──────────────────────────────
        if self.lighter_on:
            self.oil = max(0.0, self.oil - LIGHTER_DRAIN * dt)
            if self.oil <= 0:
                self.lighter_on = False
                if sound:
                    sound.play_sfx("lighter_extinguish")

    # ── 이벤트 처리 ──────────────────────────────────────
    def handle_event(self, event, room, inventory, sound=None):
        if event.type != pygame.KEYDOWN:
            return None

        if event.key == pygame.K_f:
            if self.oil > 0:
                self.lighter_on = not self.lighter_on
                sfx = "lighter_ignite" if self.lighter_on else "lighter_extinguish"
                if sound:
                    sound.play_sfx(sfx)
            return None

        if event.key == pygame.K_e:
            return self._try_interact(room, inventory, sound)

        return None

    def _try_interact(self, room, inventory, sound):
        pos = self.rect.center

        hide_spot, dist = room.nearest_hide_spot(pos)
        if hide_spot and dist <= room.INTERACT_RADIUS:
            self.is_hiding = not self.is_hiding
            return None

        obj = room.get_interactable_at(pos)
        if obj:
            return {"action": "interact", "obj": obj}

        door = room.get_door_at(self.rect)
        if door:
            return {"action": "door", "door": door}

        return None

    # ── 렌더 ─────────────────────────────────────────────
    def draw(self, surface):
        if self.is_hiding:
            spr_key = "hide"
        elif self._is_moving:
            walk_key = f"walk_{self.direction}_{self._walk_frame}"
            spr_key  = walk_key if self._sprites.get(walk_key) else f"idle_{self.direction}"
        else:
            spr_key = f"idle_{self.direction}"

        spr = self._sprites.get(spr_key) or self._sprites.get("idle_down")
        if spr is None:
            return

        draw_x = self.rect.centerx - self.sprite_w // 2
        draw_y = self.rect.bottom  - self.sprite_h + int(self._bob_offset)
        surface.blit(spr, (draw_x, draw_y))

    # ── 속성 조회 ─────────────────────────────────────────
    @property
    def pos(self):
        return self.rect.center

    @property
    def light_radius(self):
        if not self.lighter_on or self.oil <= 0:
            return LIGHTER_R_VERY
        if self.oil > 20:
            return LIGHTER_R_FULL
        if self.oil > 10:
            return LIGHTER_R_LOW
        return LIGHTER_R_VERY

    def refill_oil(self, amount=33.0):
        self.oil = min(100.0, self.oil + amount)
