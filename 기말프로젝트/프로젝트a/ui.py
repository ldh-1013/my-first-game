# -*- coding: utf-8 -*-
import pygame
from settings import (
    INTERNAL_W, INTERNAL_H,
    GOLD, RED, DIM, BRIGHT, BLACK, WHITE, PANEL,
    FONT_REGULAR, FONT_EXTRABOLD,
    GAME_START_MIN, TIME_SCALE,
)

# 인벤토리 슬롯 표시 크기
_SLOT_SIZE   = 40
_SLOT_GAP    = 6
_INV_SLOTS   = 6

class UI:
    """HUD를 담당한다: 시계 / 라이터 게이지 / 인벤토리 / 위치 표시."""

    def __init__(self, loader):
        self.loader = loader
        self._font_clock  = loader.load_font(FONT_EXTRABOLD, 26)
        self._font_label  = loader.load_font(FONT_REGULAR,   16)
        self._font_hud    = loader.load_font(FONT_REGULAR,   18)
        self._font_prompt = loader.load_font(FONT_REGULAR,   20)
        self._font_msg    = loader.load_font(FONT_REGULAR,   22)

        # 인벤토리 슬롯 배경 이미지 (없으면 placeholder)
        self._slot_img = loader.load_image("ui/ui_inventory_slot.png", (_SLOT_SIZE, _SLOT_SIZE))
        # 상호작용 프롬프트 이미지
        self._prompt_img = loader.load_image("ui/ui_interact_prompt.png", (120, 30))

        # 아이템 아이콘 캐시: item_id → Surface
        self._item_icons = {}

    # ── 메인 HUD ─────────────────────────────────────────
    def draw(self, surface, game_time_sec, player, inventory, room_id):
        """매 프레임 HUD 전체 렌더."""
        self._draw_clock(surface, game_time_sec)
        self._draw_location(surface, room_id)
        self._draw_lighter_gauge(surface, player)
        self._draw_inventory(surface, inventory)

    # ── 시계 ─────────────────────────────────────────────
    def _draw_clock(self, surface, game_time_sec):
        # 실제 경과 초 → 게임 내 분 계산
        game_min_elapsed = int(game_time_sec * TIME_SCALE / 60)
        total_min = GAME_START_MIN + game_min_elapsed
        hour   = (total_min // 60) % 24
        minute = total_min % 60
        text   = f"{hour:02d}:{minute:02d} AM"

        surf = self._font_clock.render(text, True, RED)
        # 상단 좌측에서 약간 안쪽
        surface.blit(surf, (16, 10))

    # ── 위치 표시 ─────────────────────────────────────────
    _ROOM_NAMES = {
        "mainhall_1f":   "1F — 메인홀",
        "readingroom_a": "1F — 열람실 A",
        "readingroom_b": "1F — 열람실 B",
        "librarydesk":   "1F — 사서 데스크",
        "restroom":      "1F — 화장실",
        "archive":       "2F — 자료실",
        "studyroom":     "2F — 학습 공간",
        "breakroom":     "2F — 휴게실",
        "mediaroom":     "2F — 미디어룸",
        "exhibition":    "2F — 전시체험 공간",
    }

    def _draw_location(self, surface, room_id):
        name = self._ROOM_NAMES.get(room_id, room_id)
        surf = self._font_label.render(name, True, DIM)
        surface.blit(surf, (16, 40))

    # ── 라이터 게이지 ─────────────────────────────────────
    _BAR_W  = 120
    _BAR_H  = 10
    _BAR_X  = 16
    _BAR_Y  = INTERNAL_H - 36

    def _draw_lighter_gauge(self, surface, player):
        oil = player.oil
        on  = player.lighter_on

        # 라벨
        label_color = RED if (on and oil <= 20) else DIM
        label = "LIGHTER OIL"
        lsurf = self._font_label.render(label, True, label_color)
        surface.blit(lsurf, (self._BAR_X, self._BAR_Y - 18))

        # 아이콘 (간단한 사각형)
        icon_x = self._BAR_X
        icon_y = self._BAR_Y
        pygame.draw.rect(surface, GOLD if on else DIM,
                         (icon_x, icon_y, 10, self._BAR_H))

        # 배경 바
        bx = icon_x + 14
        pygame.draw.rect(surface, (30, 40, 53), (bx, icon_y, self._BAR_W, self._BAR_H))

        # 채움 바
        fill_w = int(self._BAR_W * oil / 100)
        fill_color = RED if oil <= 20 else GOLD
        if fill_w > 0:
            pygame.draw.rect(surface, fill_color, (bx, icon_y, fill_w, self._BAR_H))

        # 외곽선
        border_color = RED if (oil <= 20 and on) else (42, 58, 74)
        pygame.draw.rect(surface, border_color, (bx, icon_y, self._BAR_W, self._BAR_H), 1)

        # 퍼센트 숫자
        pct_surf = self._font_label.render(f"{int(oil)}%", True, fill_color)
        surface.blit(pct_surf, (bx + self._BAR_W + 6, icon_y - 1))

    # ── 인벤토리 ─────────────────────────────────────────
    def _draw_inventory(self, surface, inventory):
        total_w = _INV_SLOTS * (_SLOT_SIZE + _SLOT_GAP) - _SLOT_GAP
        base_x  = INTERNAL_W - total_w - 16
        base_y  = INTERNAL_H - _SLOT_SIZE - 16

        for i, item_id in enumerate(inventory.slots):
            sx = base_x + i * (_SLOT_SIZE + _SLOT_GAP)
            sy = base_y

            # 슬롯 배경
            surface.blit(self._slot_img, (sx, sy))

            if item_id:
                icon = self._get_item_icon(item_id)
                surface.blit(icon, (sx, sy))
            else:
                # 빈 슬롯 표시: 흐릿한 사각형
                placeholder = pygame.Surface((_SLOT_SIZE, _SLOT_SIZE), pygame.SRCALPHA)
                placeholder.fill((255, 255, 255, 20))
                surface.blit(placeholder, (sx, sy))

    def _get_item_icon(self, item_id):
        if item_id not in self._item_icons:
            path = f"items/{item_id}.png"
            self._item_icons[item_id] = self.loader.load_image(path, (_SLOT_SIZE, _SLOT_SIZE))
        return self._item_icons[item_id]

    # ── 상호작용 프롬프트 ─────────────────────────────────
    def draw_interact_prompt(self, surface, text="[E]"):
        """화면 하단 중앙에 상호작용 힌트 표시."""
        surf = self._font_prompt.render(text, True, GOLD)
        x = (INTERNAL_W - surf.get_width()) // 2
        y = INTERNAL_H - 80
        # 반투명 배경
        bg = pygame.Surface((surf.get_width() + 20, surf.get_height() + 8), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 140))
        surface.blit(bg, (x - 10, y - 4))
        surface.blit(surf, (x, y))

    # ── 피드백 메시지 ─────────────────────────────────────
    def draw_message(self, surface, text, kind="info"):
        """화면 하단 중앙에 다색 피드백 메시지 표시. 40자 단위로 줄바꿈."""
        color_map = {
            "success": (80,  210, 120),
            "error":   (220, 80,  80),
            "info":    (210, 185, 130),
        }
        color = color_map.get(kind, color_map["info"])

        # 40자 단위 줄 분할
        lines = []
        while len(text) > 40:
            lines.append(text[:40])
            text = text[40:]
        lines.append(text)

        line_h  = self._font_msg.get_linesize()
        total_h = line_h * len(lines) + 12
        max_w   = max(self._font_msg.size(l)[0] for l in lines) + 28
        y_base  = INTERNAL_H - 130

        bg = pygame.Surface((max_w, total_h), pygame.SRCALPHA)
        bg.fill((8, 8, 16, 195))
        bx = (INTERNAL_W - max_w) // 2
        surface.blit(bg, (bx, y_base))

        for i, line in enumerate(lines):
            surf = self._font_msg.render(line, True, color)
            lx   = bx + (max_w - surf.get_width()) // 2
            surface.blit(surf, (lx, y_base + 6 + i * line_h))

    # ── 일시정지 오버레이 ─────────────────────────────────
    def draw_pause_overlay(self, surface):
        overlay = pygame.Surface((INTERNAL_W, INTERNAL_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surface.blit(overlay, (0, 0))

        font = self._font_clock
        txt  = font.render("일 시 정 지", True, GOLD)
        surface.blit(txt, ((INTERNAL_W - txt.get_width()) // 2,
                            INTERNAL_H // 2 - 60))

        hint = self._font_hud.render("ESC: 계속하기   Q: 게임 종료", True, DIM)
        surface.blit(hint, ((INTERNAL_W - hint.get_width()) // 2,
                             INTERNAL_H // 2 + 20))
