# -*- coding: utf-8 -*-
import os
import pygame
from settings import ASSETS_DIR

class SoundManager:
    """BGM(pygame.mixer.music)과 SFX(채널별 Sound)를 관리한다."""

    def __init__(self):
        self._bgm_vol     = 0.7
        self._sfx_vol     = 0.8
        self._current_bgm = None
        self._sfx         = {}   # name → pygame.mixer.Sound

    # ── BGM ──────────────────────────────────────────────
    def play_bgm(self, rel_path, loop=True, fade_ms=500):
        """BGM 재생. 동일 파일이 이미 재생 중이면 무시."""
        if self._current_bgm == rel_path:
            return
        full = os.path.join(ASSETS_DIR, rel_path)
        try:
            pygame.mixer.music.fadeout(fade_ms)
            pygame.mixer.music.load(full)
            pygame.mixer.music.set_volume(self._bgm_vol)
            pygame.mixer.music.play(-1 if loop else 0)
            self._current_bgm = rel_path
        except Exception:
            pass

    def stop_bgm(self, fade_ms=500):
        pygame.mixer.music.fadeout(fade_ms)
        self._current_bgm = None

    def pause_bgm(self):
        pygame.mixer.music.pause()

    def resume_bgm(self):
        pygame.mixer.music.unpause()

    # ── SFX ──────────────────────────────────────────────
    def preload_sfx(self, name, rel_path):
        """SFX를 이름으로 등록. 게임 시작 시 미리 호출한다."""
        full = os.path.join(ASSETS_DIR, rel_path)
        try:
            snd = pygame.mixer.Sound(full)
            snd.set_volume(self._sfx_vol)
            self._sfx[name] = snd
        except Exception:
            pass

    def play_sfx(self, name):
        try:
            snd = self._sfx.get(name)
            if snd:
                snd.play()
        except Exception:
            pass

    def stop_sfx(self, name):
        snd = self._sfx.get(name)
        if snd:
            snd.stop()

    # ── 볼륨 ─────────────────────────────────────────────
    def set_bgm_vol(self, vol):
        self._bgm_vol = max(0.0, min(1.0, vol))
        pygame.mixer.music.set_volume(self._bgm_vol)

    def set_sfx_vol(self, vol):
        self._sfx_vol = max(0.0, min(1.0, vol))
        for s in self._sfx.values():
            s.set_volume(self._sfx_vol)
