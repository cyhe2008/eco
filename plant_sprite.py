"""程序化绘制植物俯视贴图（莲座状叶片，多种绿色变体）。

贴图以高分辨率（SS = MAX_ZOOM，即每世界单位 SS 像素）绘制，
渲染时按 (plant.radius / maxRadius) 等比缩放，保证最大缩放下依然清晰。
"""
import math
import colorsys

import pygame

import config


SS = int(config.MAX_ZOOM)  # 超采样：每世界单位 = SS 像素


def _hsl(h, s, l):
    """h, s, l ∈ [0,1] -> (r, g, b) ∈ [0,255]。"""
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return (int(r * 255), int(g * 255), int(b * 255))


def _bezier(p0, p1, p2, p3, t):
    """三次贝塞尔曲线插值。"""
    u = 1 - t
    return (u ** 3 * p0 + 3 * u * u * t * p1 + 3 * u * t * t * p2 + t ** 3 * p3)


def _leaf_polygon(length, width, n=18):
    """一片叶子的轮廓点（尖端在 +x 方向，基部在原点）。"""
    pts = []
    for i in range(n):
        t = i / (n - 1)
        x = _bezier(0.0, 0.9 * width, 0.55 * length, length, t)
        y = _bezier(0.0, -0.7 * width, -0.55 * width, 0.0, t)
        pts.append((x, y))
    for i in range(n - 1, -1, -1):
        t = i / (n - 1)
        x = _bezier(0.0, 0.9 * width, 0.55 * length, length, t)
        y = _bezier(0.0, 0.7 * width, 0.55 * width, 0.0, t)
        pts.append((x, y))
    return pts


class _Random:
    """确定性伪随机（每种变体外观稳定）。"""

    def __init__(self, seed):
        self.a = seed & 0xFFFFFFFF

    def next(self):
        self.a = (self.a * 1664525 + 1013904223) & 0xFFFFFFFF
        return self.a / 4294967296.0


def generate_plant_sprites():
    """返回 [(surface, radius_px)]，radius_px 对应成熟半径 maxRadius 的像素值。"""
    max_r = config.PLANT_MAX_RADIUS
    pad = int(max_r * SS * 0.2)
    size = int(max_r * 2 * SS) + pad * 2
    radius_px = max_r * SS

    sprites = []
    for seed in range(config.PLANT_SPRITE_VARIANTS):
        rnd = _Random(seed * 7919 + 17)
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        cx = cy = size / 2

        leaf_count = 5 + int(rnd.next() * 4)          # 5–8 片叶
        hue = 0.30 + rnd.next() * 0.10                # 绿色区间
        base_light = 0.34 + rnd.next() * 0.12
        phase = rnd.next() * math.tau

        for i in range(leaf_count):
            angle = phase + (i / leaf_count) * math.tau
            length = max_r * (0.72 + rnd.next() * 0.28)
            width = length * (0.34 + rnd.next() * 0.12)
            sat = 0.45 + rnd.next() * 0.30
            light = base_light + rnd.next() * 0.10
            leaf_hue = hue + (rnd.next() - 0.5) * 0.03

            pts = _leaf_polygon(length, width)
            cos_a, sin_a = math.cos(angle), math.sin(angle)
            px_pts = [
                (int(cx + (x * cos_a - y * sin_a) * SS),
                 int(cy + (x * sin_a + y * cos_a) * SS))
                for x, y in pts
            ]
            pygame.draw.polygon(surf, _hsl(leaf_hue, sat, light), px_pts)

            # 中脉
            base = (int(cx + length * 0.10 * cos_a * SS),
                    int(cy + length * 0.10 * sin_a * SS))
            tip = (int(cx + length * 0.95 * cos_a * SS),
                   int(cy + length * 0.95 * sin_a * SS))
            pygame.draw.line(surf, _hsl(leaf_hue, sat, min(1.0, light + 0.18)),
                             base, tip, max(1, int(SS * 0.16)))

        # 中心生长点（同心圆模拟柔和渐变）
        center_r = max_r * (0.16 + rnd.next() * 0.08)
        for k in range(4, 0, -1):
            rr = center_r * k / 4
            col = _hsl(hue, 0.5, base_light - 0.08 + 0.04 * (k / 4))
            pygame.draw.circle(surf, col, (int(cx), int(cy)), max(1, int(rr * SS)))

        sprites.append((surf, radius_px))
    return sprites
