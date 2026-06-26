# -*- coding: utf-8 -*-
import os
import pygame
from settings import ASSETS_DIR

class AssetLoader:
    """모든 에셋(이미지·폰트·사운드)을 로드하고 캐싱한다.
    파일이 없으면 placeholder를 반환하여 에셋 없이도 실행 가능하게 한다."""

    def __init__(self):
        self._img_cache   = {}
        self._font_cache  = {}
        self._sound_cache = {}

    # ── 이미지 ───────────────────────────────────────────
    def load_image(self, rel_path, size=None):
        """Assets/ 기준 상대 경로로 이미지 로드.
        size=(w,h)이면 리사이즈. 파일 없으면 보라색 placeholder 반환."""
        key = (rel_path, size)
        if key in self._img_cache:
            return self._img_cache[key]

        full = os.path.join(ASSETS_DIR, rel_path)
        try:
            img = pygame.image.load(full).convert_alpha()
            if size:
                img = pygame.transform.scale(img, size)
        except Exception:
            w, h = size if size else (64, 64)
            img = pygame.Surface((w, h), pygame.SRCALPHA)
            img.fill((100, 50, 160, 180))  # 보라색 placeholder

        self._img_cache[key] = img
        return img

    def load_bg(self, rel_path):
        """배경 이미지를 내부 해상도(1280×720)로 로드.
        원본이 어떤 해상도여도 반드시 1280×720으로 반환한다."""
        from settings import INTERNAL_W, INTERNAL_H
        img = self.load_image(rel_path, (INTERNAL_W, INTERNAL_H))
        # 혹시 캐시된 이미지가 다른 크기로 반환될 경우 강제 리사이즈
        if img.get_size() != (INTERNAL_W, INTERNAL_H):
            img = pygame.transform.scale(img, (INTERNAL_W, INTERNAL_H))
        return img

    def load_sprite(self, rel_path, size):
        """캐릭터 스프라이트를 지정 크기로 로드."""
        return self.load_image(rel_path, size)

    # ── 폰트 ─────────────────────────────────────────────
    def load_font(self, font_path, size):
        """TTF 폰트 로드. 실패 시 시스템 폰트로 fallback."""
        key = (font_path, size)
        if key in self._font_cache:
            return self._font_cache[key]
        try:
            font = pygame.font.Font(font_path, size)
        except Exception:
            font = pygame.font.SysFont(None, size)
        self._font_cache[key] = font
        return font

    # ── 사운드 ───────────────────────────────────────────
    def load_sound(self, rel_path):
        """사운드 효과 로드. 실패 시 None 반환."""
        if rel_path in self._sound_cache:
            return self._sound_cache[rel_path]
        full = os.path.join(ASSETS_DIR, rel_path)
        try:
            snd = pygame.mixer.Sound(full)
        except Exception:
            snd = None
        self._sound_cache[rel_path] = snd
        return snd
