"""渲染器：灰色网格世界 + 环绕边界 + 植物（摆动/淡出）+ 猎物与捕食者（身体/眼睛/尾迹/辉光）+ 视野。"""
import math

import pygame

import config


class Renderer:
    def __init__(self, camera, sprites):
        self.camera = camera
        self.sprites = sprites          # [(surface, radius_px)]
        self.show_collision = False
        self.show_vision = False
        self._cache = {}                # (variant, r, rot, zoom) -> [frames]
        self._fx = None                 # 缓存的透明图层（尾迹/辉光）
        self._vision_layer = None       # 缓存的视野图层

    def _reuse_layer(self, layer, size):
        if layer is None or layer.get_size() != size:
            return pygame.Surface(size, pygame.SRCALPHA)
        layer.fill((0, 0, 0, 0))
        return layer

    def render(self, surface, plants, prey, predators):
        surface.fill(config.OUTSIDE_BACKGROUND)
        world_rect = self._world_rect()

        surface.set_clip(world_rect)
        surface.fill(config.WORLD_BACKGROUND)
        self._draw_grid(surface)
        self._draw_plants(surface, plants)
        self._draw_agents(surface, prey, predators)
        if self.show_vision:
            self._draw_vision(surface, prey, predators)
        surface.set_clip(None)

        self._draw_boundary(surface, world_rect)

    # ---- 世界矩形与网格 ----
    def _world_rect(self):
        cam = self.camera
        S = config.WORLD_SIZE
        a = cam.world_to_screen(0, 0)
        b = cam.world_to_screen(S, S)
        return pygame.Rect(int(min(a[0], b[0])), int(min(a[1], b[1])),
                           int(abs(b[0] - a[0])), int(abs(b[1] - a[1])))

    def _draw_grid(self, surface):
        cam = self.camera
        S = config.WORLD_SIZE
        g = config.GRID_SIZE
        top, left = cam.world_to_screen(0, 0)
        bottom, right = cam.world_to_screen(S, S)

        x = 0
        while x <= S:
            sx = cam.world_to_screen(x, 0)[0]
            pygame.draw.line(surface, config.GRID_LINE, (sx, top), (sx, bottom))
            x += g

        y = 0
        while y <= S:
            sy = cam.world_to_screen(0, y)[1]
            pygame.draw.line(surface, config.GRID_LINE, (left, sy), (right, sy))
            y += g

    def _draw_boundary(self, surface, rect):
        dash = 8
        x, y, w, h = rect
        for p1, p2 in (((x, y), (x + w, y)),
                       ((x + w, y), (x + w, y + h)),
                       ((x, y + h), (x + w, y + h)),
                       ((x, y), (x, y + h))):
            self._dashed_line(surface, config.BOUNDARY_LINE, p1, p2, dash)

    @staticmethod
    def _dashed_line(surface, color, a, b, dash):
        x1, y1 = a
        x2, y2 = b
        length = math.hypot(x2 - x1, y2 - y1)
        if length == 0:
            return
        ux, uy = (x2 - x1) / length, (y2 - y1) / length
        d = 0.0
        on = True
        while d < length:
            nd = min(d + dash, length)
            if on:
                pygame.draw.line(surface, color,
                                 (x1 + ux * d, y1 + uy * d),
                                 (x1 + ux * nd, y1 + uy * nd))
            on = not on
            d = nd

    # ---- 植物 ----
    def _draw_plants(self, surface, plants):
        cam = self.camera
        S = config.WORLD_SIZE
        W, H = cam.width, cam.height
        z = cam.zoom
        t = pygame.time.get_ticks() / 1000.0
        n_frames = config.SWAY_FRAMES

        for p in plants:
            r = p.radius
            half = r * z

            kxs = [0]
            if p.x - r < 0:
                kxs.append(1)
            if p.x + r > S:
                kxs.append(-1)
            kys = [0]
            if p.y - r < 0:
                kys.append(1)
            if p.y + r > S:
                kys.append(-1)

            visible = False
            for kx in kxs:
                for ky in kys:
                    sx, sy = cam.world_to_screen(p.x + kx * S, p.y + ky * S)
                    if sx + half > 0 and sx - half < W and sy + half > 0 and sy - half < H:
                        visible = True
                        break
                if visible:
                    break
            if not visible:
                continue

            frames = self._get_frames(p, z)
            idx = int(((t * config.SWAY_FREQUENCY + p.sway_phase) % 1.0) * n_frames) % n_frames
            spr = frames[idx]

            if p.dying:
                alpha = int(255 * max(0.0, p.fade_timer / config.PLANT_FADE_DURATION))
                spr = spr.copy()
                spr.set_alpha(alpha)

            for kx in kxs:
                for ky in kys:
                    sx, sy = cam.world_to_screen(p.x + kx * S, p.y + ky * S)
                    w, h = spr.get_size()
                    surface.blit(spr, (int(sx - w / 2), int(sy - h / 2)))

            if self.show_collision and not p.dying:
                cr = p.collision_radius
                for kx in kxs:
                    for ky in kys:
                        sx, sy = cam.world_to_screen(p.x + kx * S, p.y + ky * S)
                        pygame.draw.circle(surface, config.COLLISION_COLOR,
                                           (int(sx), int(sy)), max(1, int(cr * z)), 1)

    def _get_frames(self, plant, zoom):
        variant = plant.variant % len(self.sprites)
        r_bucket = int(round(plant.radius * 4))
        rot_bucket = int(round(math.degrees(plant.rotation) / 6))
        z_bucket = int(round(zoom * 1000))
        key = (variant, r_bucket, rot_bucket, z_bucket)

        cached = self._cache.get(key)
        if cached is not None:
            return cached

        base, radius_px = self.sprites[variant]
        scale = (plant.radius * zoom) / radius_px
        base_deg = math.degrees(plant.rotation)
        base_img = pygame.transform.rotozoom(base, -base_deg, scale)

        n = config.SWAY_FRAMES
        amp = config.SWAY_AMPLITUDE_DEG
        frames = []
        for i in range(n):
            ang = amp * math.sin(2 * math.pi * i / n)
            frames.append(pygame.transform.rotate(base_img, ang))

        if len(self._cache) > 2048:
            self._cache.clear()
        self._cache[key] = frames
        return frames

    # ---- 智能体（猎物 + 捕食者） ----
    def _draw_agents(self, surface, prey_list, predator_list):
        cam = self.camera
        z = cam.zoom
        W, H = cam.width, cam.height
        self._fx = self._reuse_layer(self._fx, (W, H))
        fx = self._fx

        for p in prey_list:
            self._agent_fx(fx, p, cam, config.PREY_COLOR, config.PREY_GLOW_COLOR,
                           config.PREY_FADE_DURATION)
        for p in predator_list:
            self._agent_fx(fx, p, cam, config.PREDATOR_COLOR, config.PREDATOR_GLOW_COLOR,
                           config.PREDATOR_FADE_DURATION)
        surface.blit(fx, (0, 0))

        for p in prey_list:
            self._agent_body(surface, p, cam, config.PREY_COLOR, (190, 225, 255))
        for p in predator_list:
            self._agent_body(surface, p, cam, config.PREDATOR_COLOR, (255, 215, 205))

    def _agent_fx(self, fx, p, cam, color, glow, fade_dur):
        z = cam.zoom
        W, H = cam.width, cam.height
        sx, sy = cam.world_to_screen(p.x, p.y)
        margin = p.body_radius * z * 3
        if sx < -margin or sx > W + margin or sy < -margin or sy > H + margin:
            return

        tr = p.trail
        if tr:
            n = len(tr)
            for i, (tx, ty) in enumerate(tr):
                tsx, tsy = cam.world_to_screen(tx, ty)
                f = (i + 1) / n
                alpha = int(70 * f)
                rad = max(1, int(p.body_radius * z * 0.75 * f))
                pygame.draw.circle(fx, (*color, alpha), (int(tsx), int(tsy)), rad)

        if p.dying:
            a = int(255 * max(0.0, p.fade_timer / fade_dur))
            br = max(1, int(p.body_radius * z))
            pygame.draw.circle(fx, (*color, a), (int(sx), int(sy)), br)
            return

        br = max(1, int(p.body_radius * z))
        # 冲刺状态：金黄色辉光 + 外圈，提示双倍速度/双倍代谢
        if getattr(p, "bursting", False):
            pygame.draw.circle(fx, (255, 215, 110, 46), (int(sx), int(sy)), int(br * 3.1))
            for k in range(3, 0, -1):
                rr = int(br * (1.2 + k * 0.6))
                pygame.draw.circle(fx, (255, 215, 110, 30 // k), (int(sx), int(sy)), rr)
        else:
            for k in range(3, 0, -1):
                rr = int(br * (1.0 + k * 0.55))
                pygame.draw.circle(fx, (*glow, 26 // k), (int(sx), int(sy)), rr)

    def _agent_body(self, surface, p, cam, color, highlight):
        if p.dying:
            return
        z = cam.zoom
        W, H = cam.width, cam.height
        sx, sy = cam.world_to_screen(p.x, p.y)
        margin = p.body_radius * z * 2
        if sx < -margin or sx > W + margin or sy < -margin or sy > H + margin:
            return
        br = max(1, int(p.body_radius * z))
        pygame.draw.circle(surface, color, (int(sx), int(sy)), br)
        pygame.draw.circle(surface, highlight, (int(sx), int(sy)), br, max(1, br // 4))
        fx_, fy = math.cos(p.heading), math.sin(p.heading)
        rx, ry = -fy, fx_
        eye_f = br * 0.4
        eye_s = br * 0.35
        eye_r = max(1, int(br * 0.26))
        for s in (-1, 1):
            ex = sx + fx_ * eye_f + rx * eye_s * s
            ey = sy + fy * eye_f + ry * eye_s * s
            pygame.draw.circle(surface, (245, 250, 255), (int(ex), int(ey)), eye_r)
            pr = max(1, eye_r // 2)
            pygame.draw.circle(surface, (14, 18, 26),
                               (int(ex + fx_ * eye_r * 0.35), int(ey + fy * eye_r * 0.35)), pr)

    # ---- 视野 ----
    def _draw_vision(self, surface, prey_list, predator_list):
        cam = self.camera
        z = cam.zoom
        W, H = cam.width, cam.height
        R = config.VISION_RANGE
        fov = math.radians(config.VISION_FOV_DEG)
        self._vision_layer = self._reuse_layer(self._vision_layer, (W, H))
        layer = self._vision_layer

        for p in prey_list:
            self._agent_vision(layer, p, cam, (90, 160, 255, 22))
        for p in predator_list:
            self._agent_vision(layer, p, cam, (255, 110, 90, 22))

        surface.blit(layer, (0, 0))

    def _agent_vision(self, layer, p, cam, tint):
        if p.dying:
            return
        z = cam.zoom
        W, H = cam.width, cam.height
        R = p.vision_range
        fov = math.radians(p.vision_fov)
        sx, sy = cam.world_to_screen(p.x, p.y)
        if sx < -R * z or sx > W + R * z or sy < -R * z or sy > H + R * z:
            return

        pts = [(sx, sy)]
        n = 18
        for i in range(n + 1):
            a = p.heading - fov / 2 + fov * i / n
            pts.append((sx + math.cos(a) * R * z, sy + math.sin(a) * R * z))
        pygame.draw.polygon(layer, tint, pts)

        for (t, raw), a in zip(p.vision_hits, p.vision_rays):
            dist = min(t, R)
            ex = sx + math.cos(a) * dist * z
            ey = sy + math.sin(a) * dist * z
            if t < R:
                col = (int(raw[0] * 255), int(raw[1] * 255), int(raw[2] * 255))
            else:
                col = (130, 136, 144)
            pygame.draw.line(layer, (*col, 140), (sx, sy), (ex, ey), 1)
