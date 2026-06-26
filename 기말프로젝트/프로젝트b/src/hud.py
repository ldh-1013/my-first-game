import pygame
from settings import (SCREEN_WIDTH, FONT_PATH, MODE_BLACK,
                      BLACK_BG, BLACK_TILE, WHITE_BG, WHITE_TILE)

class HUD:
    def __init__(self):
        # build fonts ONCE here, reuse every frame (never create fonts in draw)
        # SUIT-Thin lacks ●○■□∞ glyphs — detect tofu and fall back to segoeui
        self.font = self._pick_font()
        self.bar_height = 70
        self.pad = 14            # inner padding of each block
        self.gap = 12            # gap between blocks

    def _pick_font(self):
        """Return a font that renders ●○■□∞ distinctly (no tofu boxes)."""
        def glyphs_distinct(f):
            widths = [f.size(g)[0] for g in ("●", "○", "∞")]
            return len(set(widths)) > 1  # distinct widths = real glyphs

        try:
            f = pygame.font.Font(FONT_PATH, 22)
            if glyphs_distinct(f):
                return f
        except Exception:
            pass
        # segoeui has confirmed symbol coverage on Windows
        for name in ("segoeui", "dejavusans", "calibri", "arial"):
            try:
                f = pygame.font.SysFont(name, 24)
                if glyphs_distinct(f):
                    return f
            except Exception:
                pass
        return pygame.font.SysFont(None, 26)

    def _colors(self, mode):
        """Return (bg, fg) based on current mode. Shifts to cold/warm palette."""
        if mode == MODE_BLACK:
            return BLACK_BG, BLACK_TILE   # cold dark bg, bright text
        else:
            return WHITE_BG, WHITE_TILE   # warm light bg, dark text

    def _switch_text(self, used, limit):
        if limit == -1:
            return "∞"                    # infinity symbol
        used = max(0, min(used, limit))
        return "●" * used + "○" * (limit - used)   # ● filled, ○ hollow

    def draw(self, surface, stage_num, player, switch_limit):
        bg, fg = self._colors(player.mode)

        # full-width HUD bar background
        pygame.draw.rect(surface, bg, (0, 0, SCREEN_WIDTH, self.bar_height))

        mode_square = "■" if player.mode == MODE_BLACK else "□"  # ■ / □
        blocks = [
            f"STAGE {stage_num:02d}",
            f"STATE {mode_square} {player.mode.upper()}",
            f"MOVES {player.move_count}",
            self._switch_text(player.switch_count, switch_limit),
        ]

        # lay blocks left to right, each in its own rounded rect of fg-outline
        x = self.gap
        y = (self.bar_height - 34) // 2
        for text in blocks:
            label = self.font.render(text, True, fg)
            w = label.get_width() + self.pad * 2
            block_rect = pygame.Rect(x, y, w, 34)
            pygame.draw.rect(surface, bg, block_rect)
            pygame.draw.rect(surface, fg, block_rect, 2)
            surface.blit(label, (x + self.pad, y + (34 - label.get_height()) // 2))
            x += w + self.gap
