import pygame
from settings import (SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_WHITE, COLOR_BLACK,
                      FONT_PATH, TITLE)

class Menu:
    def __init__(self, items):
        # items: list of (label, action_string) tuples
        # e.g. [("START", "start"), ("QUIT", "quit")]
        self.items = items
        self.selected = 0
        try:
            self.title_font = pygame.font.Font(FONT_PATH, 64)
            self.item_font  = pygame.font.Font(FONT_PATH, 32)
        except Exception:
            self.title_font = pygame.font.SysFont(None, 72)
            self.item_font  = pygame.font.SysFont(None, 40)
        self._item_rects = []   # filled during draw, used for mouse hit-testing

    def handle_event(self, event):
        """Return an action string ('start','quit',...) when an item is
        activated, else None."""
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected = (self.selected - 1) % len(self.items)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected = (self.selected + 1) % len(self.items)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                return self.items[self.selected][1]
        elif event.type == pygame.MOUSEMOTION:
            for i, rect in enumerate(self._item_rects):
                if rect.collidepoint(event.pos):
                    self.selected = i
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in enumerate(self._item_rects):
                if rect.collidepoint(event.pos):
                    self.selected = i
                    return self.items[i][1]
        return None

    def draw(self, surface, start_y=None, draw_bg=True, draw_title=True):
        """Draw menu onto surface.

        start_y   -- vertical centre of the first item (default: SCREEN_HEIGHT//2+40)
        draw_bg   -- fill background; pass False when layering over another screen
        draw_title -- render the game title; pass False for overlay menus
        """
        if draw_bg:
            surface.fill(COLOR_BLACK)

        if draw_title:
            title = self.title_font.render(TITLE, True, COLOR_WHITE)
            surface.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2,
                                                       SCREEN_HEIGHT // 3)))

        # menu items, vertically stacked and centered
        self._item_rects = []
        if start_y is None:
            start_y = SCREEN_HEIGHT // 2 + 40
        spacing = 56
        for i, (label, _action) in enumerate(self.items):
            is_sel = (i == self.selected)
            # selected item: filled white block with black text (inverted)
            text_color = COLOR_BLACK if is_sel else COLOR_WHITE
            surf = self.item_font.render(label, True, text_color)
            rect = surf.get_rect(center=(SCREEN_WIDTH // 2, start_y + i * spacing))
            pad = pygame.Rect(rect.x - 24, rect.y - 8,
                              rect.width + 48, rect.height + 16)
            if is_sel:
                pygame.draw.rect(surface, COLOR_WHITE, pad, border_radius=8)
            else:
                pygame.draw.rect(surface, COLOR_WHITE, pad, width=2, border_radius=8)
            surface.blit(surf, rect)
            self._item_rects.append(pad)   # use the padded box for hit-testing
