import pygame
import os
import math

from data.core_funcs import (swap_color, blit_center, advance_deg, alpha_line)

particle_images = []


def load_assets(base_path):
    global particle_images
    particle_images = []
    p_dir = os.path.join(base_path, 'data', 'images', 'particles')
    for i in range(6):
        path = os.path.join(p_dir, f'{i}.png')
        try:
            img = pygame.image.load(path).convert()
            img.set_colorkey((0, 0, 0))
        except Exception:
            img = pygame.Surface((8, 8))
            img.set_colorkey((0, 0, 0))
            r = max(1, 4 - i)
            pygame.draw.circle(img, (255, 255, 255), (4, 4), r)
        particle_images.append(img)


# ---------------------------------------------------------------------------
# Particle
# ---------------------------------------------------------------------------
class Particle:
    def __init__(self, loc, ptype, motion, decay_rate, start_frame,
                 custom_color=None, physics=False):
        self.loc = list(loc)
        self.ptype = ptype
        self.motion = list(motion)
        self.decay_rate = max(1, int(decay_rate))
        self.start_frame = start_frame
        self.physics = physics

        if custom_color and particle_images:
            self.imgs = [swap_color(img, (255, 255, 255), custom_color)
                         for img in particle_images]
        else:
            self.imgs = particle_images[:]

    def update(self, surf, frame, offset=(0, 0)):
        """Returns True when dead. offset=(ox,oy) applied when drawing."""
        idx = (frame - self.start_frame) // self.decay_rate
        if idx >= len(self.imgs):
            return True

        self.loc[0] += self.motion[0]
        self.loc[1] += self.motion[1]
        if self.physics:
            self.motion[1] = min(self.motion[1] + 0.1, 5)

        if self.imgs:
            draw_pos = (self.loc[0] - offset[0], self.loc[1] - offset[1])
            blit_center(surf, self.imgs[idx], draw_pos)
        return False


# ---------------------------------------------------------------------------
# Spark
# ---------------------------------------------------------------------------
class Spark:
    def __init__(self, loc, angle_deg, scale, speed, color=(255, 255, 255)):
        self.loc = list(loc)
        self.angle = angle_deg   # degrees
        self.scale = scale
        self.speed = speed
        self.color = color

    def update(self, surf, scroll=0):
        s, sc = self.speed, self.scale
        pts = [
            advance_deg(self.loc, self.angle,       2   * s * sc),
            advance_deg(self.loc, self.angle + 90,  0.3 * s * sc),
            advance_deg(self.loc, self.angle,      -1   * s * sc),
            advance_deg(self.loc, self.angle - 90,  0.3 * s * sc),
        ]
        pts_screen = [[v[0], v[1] - scroll] for v in pts]
        try:
            pygame.draw.polygon(surf, self.color, pts_screen)
        except Exception:
            pass
        self.loc = advance_deg(self.loc, self.angle, s)
        self.speed -= 0.5
        return self.speed <= 0


# ---------------------------------------------------------------------------
# LineEffect
# ---------------------------------------------------------------------------
class LineEffect:
    def __init__(self, start_pair, target_pair, color, divisor, timer):
        self.cur = [list(start_pair[0]), list(start_pair[1])]
        self.tgt = [list(target_pair[0]), list(target_pair[1])]
        self.color = color
        self.divisor = divisor
        self.timer = timer
        self.initial_timer = timer

    def update(self, surf, scroll=0):
        for i in range(2):
            for j in range(2):
                self.cur[i][j] += (self.tgt[i][j] - self.cur[i][j]) / self.divisor
        self.timer -= 1
        if self.timer <= 0:
            return True
        opacity = int(255 * (self.timer / self.initial_timer))
        p1 = [self.cur[0][0], self.cur[0][1] - scroll]
        p2 = [self.cur[1][0], self.cur[1][1] - scroll]
        alpha_line(surf, (*self.color, opacity), p1, p2)
        return False


# ---------------------------------------------------------------------------
# CircleEffect
# ---------------------------------------------------------------------------
class CircleEffect:
    def __init__(self, pos, radius, width_info, speed_info, color):
        self.pos = list(pos)
        self.radius = float(radius)
        self.width = float(width_info[0])
        self.width_decay = float(width_info[1])
        self.speed = float(speed_info[0])
        self.speed_decay = float(speed_info[1])
        self.color = color

    def update(self, surf, scroll=0):
        self.radius += self.speed
        self.width -= self.width_decay
        self.speed -= self.speed_decay
        if self.width < 1:
            return True
        cx = int(self.pos[0])
        cy = int(self.pos[1] - scroll)
        pygame.draw.circle(surf, self.color, (cx, cy),
                           int(self.radius), int(self.width))
        return False

