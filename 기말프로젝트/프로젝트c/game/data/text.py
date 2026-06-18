import pygame


class Font:
    def __init__(self, path, size, color=(255, 255, 255), antialias=False):
        pygame.font.init()
        self.font = pygame.font.Font(path, size)
        self.color = color
        self.antialias = antialias
        self.line_height = self.font.get_height()

    def render(self, text, surf, loc, color=None):
        surf.blit(
            self.font.render(str(text), self.antialias, color or self.color),
            loc)

    def width(self, text):
        return self.font.size(str(text))[0]
