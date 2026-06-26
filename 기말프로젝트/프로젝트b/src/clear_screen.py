import pygame
from settings import (SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_WHITE, COLOR_BLACK,
                      FONT_PATH)

def compute_stars(score, thresholds):
    t3, t2, t1 = thresholds
    if score <= t3:
        return 3
    if score <= t2:
        return 2
    return 1

class ClearScreen:
    def __init__(self):
        try:
            self.big_font  = pygame.font.Font(FONT_PATH, 56)
            self.star_font = pygame.font.Font(FONT_PATH, 64)
            self.info_font = pygame.font.Font(FONT_PATH, 26)
        except Exception:
            self.big_font  = pygame.font.SysFont(None, 64)
            self.star_font = pygame.font.SysFont(None, 72)
            self.info_font = pygame.font.SysFont(None, 32)
        # star glyphs: SUIT-Thin likely lacks ★☆, so pick a font that has them
        self.star_font = self._pick_star_font()

    def _pick_star_font(self):
        def has_stars(f):
            w1 = f.size("★")[0]  # ★
            w2 = f.size("☆")[0]  # ☆
            return w1 > 4 and w2 > 4 and w1 != f.size("?")[0]
        try:
            f = pygame.font.Font(FONT_PATH, 64)
            if has_stars(f):
                return f
        except Exception:
            pass
        for name in ("segoeui", "dejavusans", "calibri", "arial"):
            try:
                f = pygame.font.SysFont(name, 64)
                if has_stars(f):
                    return f
            except Exception:
                pass
        return pygame.font.SysFont(None, 72)

    def draw(self, surface, stage_num, stars, score, thresholds,
             best_stars=0, best_score=None):
        # monochrome: black background, white content
        surface.fill(COLOR_BLACK)

        # "STAGE 07 CLEAR"
        title = self.big_font.render(f"STAGE {stage_num:02d} CLEAR", True, COLOR_WHITE)
        surface.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2,
                                                   SCREEN_HEIGHT // 4)))

        # stars: filled ★ up to `stars`, hollow ☆ for the rest of 3
        star_str = "★" * stars + "☆" * (3 - stars)
        star_surf = self.star_font.render(star_str, True, COLOR_WHITE)
        surface.blit(star_surf, star_surf.get_rect(center=(SCREEN_WIDTH // 2,
                                                           SCREEN_HEIGHT // 2 - 40)))

        # score line: "SCORE 18   3-STAR ≤ 14"
        t3 = thresholds[0]
        info = self.info_font.render(f"SCORE {score}   3-STAR ≤ {t3}",
                                     True, COLOR_WHITE)
        surface.blit(info, info.get_rect(center=(SCREEN_WIDTH // 2,
                                                 SCREEN_HEIGHT // 2 + 10)))

        # best record line
        is_new_best = (best_score is None or score < best_score or stars > best_stars)
        if best_score is None:
            best_line = "FIRST CLEAR!"
        else:
            best_star_str = "★" * best_stars + "☆" * (3 - best_stars)
            best_line = f"BEST {best_star_str}  SCORE {best_score}"
            if is_new_best:
                best_line += "  NEW BEST!"
        best_surf = self.info_font.render(best_line, True, COLOR_WHITE)
        surface.blit(best_surf, best_surf.get_rect(center=(SCREEN_WIDTH // 2,
                                                           SCREEN_HEIGHT // 2 + 44)))
