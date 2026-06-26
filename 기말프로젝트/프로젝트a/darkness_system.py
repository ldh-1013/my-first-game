# -*- coding: utf-8 -*-
import random
import pygame
from settings import INTERNAL_W, INTERNAL_H, LIGHTER_R_OFF

class DarknessSystem:
    """어둠 오버레이를 렌더한다.
    BLEND_MULT 방식: 마스크 Surface를 곱셈 블렌드로 game_surface에 적용.
    흰색(255,255,255) 영역 → 원본 색 유지 / 검정(0,0,0) → 완전 암흑."""

    # 기름 수준별 기본 조명 반경 (player.py의 light_radius와 동기화)
    _DARK_ALPHA = 240   # 마스크 기본 어둠 강도 (0=투명, 255=완전 검정)

    def __init__(self):
        # 반경별 그라디언트 Surface 캐시
        self._cache = {}

    # ── 퍼블릭 API ────────────────────────────────────────
    def render(self, surface, player_center, lighter_on, oil):
        """game_surface에 어둠 레이어를 직접 blit한다."""
        radius = self._effective_radius(lighter_on, oil)

        # 깜빡임 효과: 기름 20% 이하
        if lighter_on and 0 < oil <= 20:
            flicker = int((20 - oil) * 2.0)  # 최대 40px 흔들림
            flicker = min(flicker, 35)
            radius  = max(30, radius + random.randint(-flicker // 2, flicker // 2))
            # 중심 위치도 약간 흔들기
            px = player_center[0] + random.randint(-flicker // 4, flicker // 4)
            py = player_center[1] + random.randint(-flicker // 4, flicker // 4)
        else:
            px, py = player_center

        # 마스크 생성 (검정 배경 + 흰색 원)
        mask = self._get_mask(radius)

        # 전체 어둠 Surface
        dark = pygame.Surface((INTERNAL_W, INTERNAL_H))
        dark.fill((0, 0, 0))

        # 조명 원 합성 — BLEND_ADD로 마스크를 어둠 위에 올림
        mx = int(px) - radius
        my = int(py) - radius
        dark.blit(mask, (mx, my), special_flags=pygame.BLEND_ADD)

        # game_surface에 곱셈 적용 (dark의 흰 영역은 밝고, 검정은 어둠)
        surface.blit(dark, (0, 0), special_flags=pygame.BLEND_MULT)

    # ── 내부 유틸 ─────────────────────────────────────────
    def _effective_radius(self, lighter_on, oil):
        from settings import LIGHTER_R_FULL, LIGHTER_R_LOW, LIGHTER_R_VERY
        if not lighter_on or oil <= 0:
            return LIGHTER_R_OFF
        if oil > 20:
            return LIGHTER_R_FULL
        if oil > 10:
            return LIGHTER_R_LOW
        return LIGHTER_R_VERY

    def _get_mask(self, radius):
        """반경별 그라디언트 원 Surface를 캐싱하여 반환.
        Surface 크기: (radius*2+2) × (radius*2+2), 검정 배경에 흰 그라디언트 원."""
        if radius in self._cache:
            return self._cache[radius]

        d  = radius * 2 + 2
        cx = cy = radius + 1
        surf = pygame.Surface((d, d))
        surf.fill((0, 0, 0))

        # 바깥부터 안쪽으로 밝아지는 그라디언트 (step=3으로 성능 최적화)
        step = max(1, radius // 60)
        for r in range(radius, 0, -step):
            t   = r / radius          # 1.0 = 가장자리, 0.0 = 중심
            val = int(255 * (1.0 - t ** 1.3))   # 부드러운 감쇠 곡선
            pygame.draw.circle(surf, (val, val, val), (cx, cy), r)

        # 중심은 완전 흰색
        pygame.draw.circle(surf, (255, 255, 255), (cx, cy), max(1, radius // 5))

        self._cache[radius] = surf
        return surf
