import pygame
import math


def swap_color(img, old_c, new_c):
    """Replace old_c pixels with new_c; result has colorkey=(0,0,0)."""
    img = img.copy()
    img.set_colorkey(old_c)
    new_img = pygame.Surface(img.get_size())
    new_img.fill(new_c)
    new_img.blit(img, (0, 0))
    new_img.set_colorkey((0, 0, 0))
    return new_img


def advance_deg(pos, angle_deg, distance):
    """Polar move using DEGREES."""
    rad = math.radians(angle_deg)
    return [pos[0] + math.cos(rad) * distance,
            pos[1] + math.sin(rad) * distance]


_alpha_line_cache = {}

def alpha_line(surf, color, start, end):
    r, g, b = color[0], color[1], color[2]
    a = color[3] if len(color) > 3 else 255
    size = surf.get_size()
    if size not in _alpha_line_cache:
        _alpha_line_cache[size] = pygame.Surface(size, pygame.SRCALPHA)
    temp = _alpha_line_cache[size]
    temp.fill((0, 0, 0, 0))
    pygame.draw.line(temp, (r, g, b, a),
                     (int(start[0]), int(start[1])),
                     (int(end[0]), int(end[1])), 1)
    surf.blit(temp, (0, 0))


def blit_center(dest, src, pos):
    dest.blit(src, (int(pos[0]) - src.get_width() // 2,
                    int(pos[1]) - src.get_height() // 2))


# ---------------------------------------------------------------------------
# Game math helpers
# ---------------------------------------------------------------------------

def sign_func(num):
    if num != 0:
        return num / abs(num)
    return 1


def normalize(value, speed):
    """Decay value toward 0 by speed per call."""
    if abs(value) > speed:
        return value - speed * sign_func(value)
    return 0


def dis_func(vec):
    return math.sqrt(vec[0] ** 2 + vec[1] ** 2)


def mirror_angle(original, base):
    """Reflect angle in degrees about a base angle (degrees)."""
    dif = 180 - base
    base_val = 180
    new = (original + dif) % 360
    dif2 = base_val - new
    return original + dif2 * 2


def check_line_sides(lines, point):
    """Return cross-product sign for each line relative to point."""
    result = []
    for line in lines:
        cross = ((line[1][0] - line[0][0]) * (point[1] - line[0][1]) -
                 (line[1][1] - line[0][1]) * (point[0] - line[0][0]))
        result.append(cross)
    return result


def doIntersect(seg1, seg2):
    """True if line segment seg1 intersects seg2."""
    p1, p2 = seg1[0], seg1[1]
    p3, p4 = seg2[0], seg2[1]

    d1 = ((p4[0]-p3[0]) * (p1[1]-p3[1]) - (p4[1]-p3[1]) * (p1[0]-p3[0]))
    d2 = ((p4[0]-p3[0]) * (p2[1]-p3[1]) - (p4[1]-p3[1]) * (p2[0]-p3[0]))
    d3 = ((p2[0]-p1[0]) * (p3[1]-p1[1]) - (p2[1]-p1[1]) * (p3[0]-p1[0]))
    d4 = ((p2[0]-p1[0]) * (p4[1]-p1[1]) - (p2[1]-p1[1]) * (p4[0]-p1[0]))

    if ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and \
       ((d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)):
        return True
    return False
