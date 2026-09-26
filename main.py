"""生态缸 · 捕食者-猎物进化模拟 —— 入口。

运行：python main.py
控制：
  左键拖拽     平移视口
  鼠标滚轮     缩放（以光标为锚点）
  空格         暂停 / 继续
  [ / ]        减速 / 加速（0.5× – 64×）
  C            显示 / 隐藏碰撞体积
  V            显示 / 隐藏猎物视野
  H            显示 / 隐藏操作说明
  F11 / F      切换全屏
  F5 / F9      保存 / 载入备份
  B            保存当前最优大脑存档
  N            查看神经网络存档
  0            恢复 50% 视图
  Esc          退出
"""
import sys

import pygame

import brain_archive
import config
from brain import decode_traits, input_size
from camera import Camera
from plant_sprite import generate_plant_sprites
from renderer import Renderer
from simulation import Simulation


def load_font(size, bold=False):
    """加载支持中文的系统字体，失败则退回默认字体。"""
    for name in ("simhei", "microsoftyahei", "simsun"):
        path = pygame.font.match_font(name, bold=bold)
        if path:
            return pygame.font.Font(path, size)
    return pygame.font.Font(None, size)


def lerp_color(a, b, t):
    t = max(0.0, min(1.0, t))
    return (int(a[0] + (b[0] - a[0]) * t),
            int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t))


class Button:
    """可点击的界面按钮（带悬停提示与激活态）。"""

    def __init__(self, id_, label, action, tip=""):
        self.id = id_
        self.label = label
        self.action = action
        self.tip = tip
        self.rect = pygame.Rect(0, 0, 40, 40)

    def draw(self, surface, font, hover=False, active=False):
        if active:
            bg, border = (46, 96, 74), (111, 207, 151)
        elif hover:
            bg, border = (64, 70, 80), (92, 100, 112)
        else:
            bg, border = (40, 44, 52), (70, 76, 86)
        pygame.draw.rect(surface, bg, self.rect, border_radius=10)
        pygame.draw.rect(surface, border, self.rect, 1, border_radius=10)
        text = font.render(self.label, True, (232, 234, 237))
        surface.blit(text, text.get_rect(center=self.rect.center))

    def hit(self, pos):
        return self.rect.collidepoint(pos)


class App:
    def __init__(self):
        pygame.init()
        info = pygame.display.Info()
        self.desktop_short = min(info.current_w, info.current_h)
        self.win_w = max(720, int(info.current_w * 0.75))
        self.win_h = max(540, int(info.current_h * 0.75))
        self.screen = pygame.display.set_mode((self.win_w, self.win_h), pygame.RESIZABLE)
        pygame.display.set_caption("生态缸 · 捕食者-猎物进化模拟")

        self.clock = pygame.time.Clock()
        self.font = load_font(16)
        self.font_small = load_font(13)
        self.font_big = load_font(20)

        self.camera = Camera(config.WORLD_SIZE)
        self.sprites = generate_plant_sprites()
        self.renderer = Renderer(self.camera, self.sprites)
        self.sim = Simulation()
        self.sim.seed()

        sw, sh = self.screen.get_size()
        self.camera.resize(sw, sh)
        self.camera.fit(ref_side=self.desktop_short)   # 地图 = 电脑全屏的 50%

        self.show_collision = False
        self.show_vision = False
        self.show_help = False
        self.show_chart = False
        self.chart_show = {"plants": True, "prey": True, "predators": True}
        self._chart_legend_rects = {}
        self.fullscreen = False
        self.dragging = False
        self.last_mouse = (0, 0)
        self.mouse_pos = (0, 0)

        self.paused = False
        self.speed_index = config.DEFAULT_SPEED_INDEX
        self.message = ""
        self.message_timer = 0.0
        self._autosave_timer = 0.0
        self.show_brains = False
        self._bv_list = []
        self._bv_index = 0

        # 显示顺序（从左到右）：减速 · 加速 · 暂停 · 碰撞 · 视野 · 帮助
        self.buttons = [
            Button("slower", "减速", self.slower, "减速（[）"),
            Button("faster", "加速", self.faster, "加速（]）"),
            Button("pause", "暂停", self.toggle_pause, "暂停 / 继续（空格）"),
            Button("collision", "碰撞", self.toggle_collision, "碰撞体积（C）"),
            Button("vision", "视野", self.toggle_vision, "视野：猎物+捕食者（V）"),
            Button("chart", "图表", self.toggle_chart, "种群曲线（T）"),
            Button("help", "帮助", self.toggle_help, "操作说明（H）"),
        ]
        self._layout_buttons()

    # ---- 速度 ----
    @property
    def speed(self):
        return config.SPEED_LEVELS[self.speed_index]

    def toggle_pause(self):
        self.paused = not self.paused

    def slower(self):
        self.speed_index = max(0, self.speed_index - 1)

    def faster(self):
        self.speed_index = min(len(config.SPEED_LEVELS) - 1, self.speed_index + 1)

    def toggle_collision(self):
        self.show_collision = not self.show_collision

    def toggle_vision(self):
        self.show_vision = not self.show_vision

    def toggle_help(self):
        self.show_help = not self.show_help

    def toggle_chart(self):
        self.show_chart = not self.show_chart

    # ---- 备份 ----
    def _show_message(self, text):
        self.message = text
        self.message_timer = 2.5

    def _save_backup(self):
        try:
            self.sim.save(config.BACKUP_PATH)
            self._show_message("已保存备份（F9 载入）")
        except Exception as e:
            self._show_message(f"保存失败: {e}")

    def _load_backup(self):
        try:
            self.sim = Simulation.load(config.BACKUP_PATH)
            self._show_message("已载入备份")
        except FileNotFoundError:
            self._show_message("无备份文件")
        except Exception as e:
            self._show_message(f"载入失败: {e}")

    # ---- 神经网络存档 ----
    def _save_best_brains(self):
        """保存当前猎物与捕食者中能量最高的个体大脑（多份存档，按时间命名）。"""
        base = {
            "sim_time": round(self.sim.time, 2),
            "population": {
                "plants": len(self.sim.plants),
                "prey": len(self.sim.prey),
                "predators": len(self.sim.predators),
            },
            "input_size": input_size(),
            "hidden_sizes": [config.BRAIN_HIDDEN1, config.BRAIN_HIDDEN2],
        }
        saved = []
        best_prey = max((q for q in self.sim.prey if not q.dying),
                        key=lambda q: q.energy, default=None)
        if best_prey is not None:
            brain_archive.save_brain("prey", best_prey.brain,
                                     {**base, "id": best_prey.id,
                                      "energy": round(best_prey.energy, 3),
                                      "generation": self.sim.splits_prey,
                                      "offspring": best_prey.offspring})
            saved.append("猎物")
        best_pred = max((r for r in self.sim.predators if not r.dying),
                        key=lambda r: r.energy, default=None)
        if best_pred is not None:
            brain_archive.save_brain("predator", best_pred.brain,
                                     {**base, "id": best_pred.id,
                                      "energy": round(best_pred.energy, 3),
                                      "generation": self.sim.splits_predator,
                                      "offspring": best_pred.offspring})
            saved.append("捕食者")
        if saved:
            self._show_message(f"已存档最优大脑: {' + '.join(saved)}")
        else:
            self._show_message("无存活个体可存档")

    def toggle_brains(self):
        self.show_brains = not self.show_brains
        if self.show_brains:
            self._bv_list = brain_archive.list_archives()
            self._bv_index = len(self._bv_list) - 1 if self._bv_list else 0

    def _brain_viewer_handle(self, event):
        if event.type == pygame.QUIT:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_n):
                self.show_brains = False
            elif event.key == pygame.K_UP and self._bv_list:
                self._bv_index = max(0, self._bv_index - 1)
            elif event.key == pygame.K_DOWN and self._bv_list:
                self._bv_index = min(len(self._bv_list) - 1, self._bv_index + 1)
            elif event.key == pygame.K_PAGEUP and self._bv_list:
                self._bv_index = max(0, self._bv_index - 10)
            elif event.key == pygame.K_PAGEDOWN and self._bv_list:
                self._bv_index = min(len(self._bv_list) - 1, self._bv_index + 10)
        elif event.type == pygame.MOUSEWHEEL and self._bv_list:
            self._bv_index = max(0, min(len(self._bv_list) - 1, self._bv_index - event.y))
        return True

    # ---- 布局 ----
    def _layout_buttons(self):
        # 右上角两行按钮（每行最多 4 个，右对齐），避免与左上信息面板重叠
        margin, gap, size = 12, 8, 40
        per_row = 4
        for i, b in enumerate(self.buttons):
            row = i // per_row
            col = i % per_row
            row_count = min(per_row, len(self.buttons) - row * per_row)
            row_w = row_count * size + (row_count - 1) * gap
            row_x = self.camera.width - margin - row_w
            b.rect = pygame.Rect(row_x + col * (size + gap),
                                 margin + row * (size + gap), size, size)
        for b in self.buttons:
            if b.id == "pause":
                b.label = "继续" if self.paused else "暂停"

    def _handle_button_click(self, pos):
        for b in self.buttons:
            if b.hit(pos):
                b.action()
                return True
        return False

    # ---- 全屏 ----
    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode((self.win_w, self.win_h), pygame.RESIZABLE)
        w, h = self.screen.get_size()
        self.camera.resize(w, h)

    # ---- 事件 ----
    def handle_event(self, event):
        if event.type == pygame.QUIT:
            return False
        if event.type == pygame.VIDEORESIZE:
            self.win_w, self.win_h = event.w, event.h
            self.camera.resize(event.w, event.h)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                if self.show_help:
                    self.show_help = False
                    return True
                if self._handle_button_click(event.pos):
                    return True
                if self.show_chart:
                    for key, rect in self._chart_legend_rects.items():
                        if rect.collidepoint(event.pos):
                            self.chart_show[key] = not self.chart_show[key]
                            return True
                self.dragging = True
                self.last_mouse = event.pos
            elif event.button == 4:
                self.camera.zoom_at(*event.pos, config.ZOOM_STEP)
            elif event.button == 5:
                self.camera.zoom_at(*event.pos, 1 / config.ZOOM_STEP)
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.dragging = False
        elif event.type == pygame.MOUSEMOTION:
            self.mouse_pos = event.pos
            if self.dragging:
                dx = event.pos[0] - self.last_mouse[0]
                dy = event.pos[1] - self.last_mouse[1]
                self.last_mouse = event.pos
                self.camera.pan_screen(dx, dy)
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return False
            elif event.key in (pygame.K_F11, pygame.K_f):
                self.toggle_fullscreen()
            elif event.key == pygame.K_SPACE:
                self.toggle_pause()
            elif event.key == pygame.K_h:
                self.toggle_help()
            elif event.key == pygame.K_v:
                self.toggle_vision()
            elif event.key == pygame.K_c:
                self.toggle_collision()
            elif event.key == pygame.K_t:
                self.toggle_chart()
            elif event.key == pygame.K_LEFTBRACKET:
                self.slower()
            elif event.key == pygame.K_RIGHTBRACKET:
                self.faster()
            elif event.key in (pygame.K_PLUS, pygame.K_EQUALS):
                self.camera.zoom_at(self.camera.width / 2, self.camera.height / 2,
                                    config.ZOOM_STEP)
            elif event.key == pygame.K_MINUS:
                self.camera.zoom_at(self.camera.width / 2, self.camera.height / 2,
                                    1 / config.ZOOM_STEP)
            elif event.key == pygame.K_0:
                self.camera.fit(ref_side=self.desktop_short)
            elif event.key == pygame.K_F5:
                self._save_backup()
            elif event.key == pygame.K_F9:
                self._load_backup()
            elif event.key == pygame.K_b:
                self._save_best_brains()
            elif event.key == pygame.K_n:
                self.toggle_brains()
        return True

    # ---- 模拟 ----
    def update(self, dt):
        if not self.paused:
            self.sim.step(min(dt, config.MAX_FRAME_DT) * self.speed)

        if self.message_timer > 0.0:
            self.message_timer -= dt
            if self.message_timer <= 0.0:
                self.message = ""

        if config.AUTOSAVE_INTERVAL > 0:
            self._autosave_timer += dt
            if self._autosave_timer >= config.AUTOSAVE_INTERVAL:
                self._autosave_timer = 0.0
                try:
                    self.sim.save(config.AUTOSAVE_PATH)
                    self._show_message("自动备份完成")
                except Exception:
                    self._show_message("自动备份失败")

    # ---- HUD ----
    def draw_hud(self):
        panel = pygame.Surface((430, 132), pygame.SRCALPHA)
        panel.fill((20, 22, 26, 195))
        self.screen.blit(panel, (12, 12))

        title = self.font.render("生态缸 · 捕食者-猎物进化", True, (232, 234, 237))
        self.screen.blit(title, (24, 18))

        stats = self.font_small.render(
            f"植物: {len(self.sim.plants)} · 猎物: {len(self.sim.prey)} · "
            f"捕食者: {len(self.sim.predators)}",
            True, (174, 180, 189))
        self.screen.blit(stats, (24, 42))

        gen = self.font_small.render(
            f"分裂: 猎物 {self.sim.splits_prey} · 捕食者 {self.sim.splits_predator}",
            True, (174, 180, 189))
        self.screen.blit(gen, (24, 62))

        fit = self.font_small.render(
            f"最佳适应度: 猎物 {self.sim.best_prey_fitness:.3f}/s · "
            f"捕食者 {self.sim.best_predator_fitness:.3f}/s",
            True, (111, 207, 151))
        self.screen.blit(fit, (24, 82))

        speed = self.font_small.render(
            f"帧率: {int(self.clock.get_fps())} FPS · 速度: {self.speed:g}×",
            True, (111, 207, 151))
        self.screen.blit(speed, (24, 102))
        if self.paused:
            badge = self.font_small.render("已暂停", True, (240, 150, 80))
            self.screen.blit(badge, (24 + speed.get_width() + 10, 102))

        self._layout_buttons()
        for b in self.buttons:
            active = (b.id == "pause" and self.paused) or \
                     (b.id == "collision" and self.show_collision) or \
                     (b.id == "vision" and self.show_vision) or \
                     (b.id == "chart" and self.show_chart)
            b.draw(self.screen, self.font_small,
                   hover=b.rect.collidepoint(self.mouse_pos), active=active)
        for b in self.buttons:
            if b.tip and b.rect.collidepoint(self.mouse_pos):
                self._draw_tooltip(b)

        hint = self.font_small.render(
            "拖拽平移 · 滚轮缩放 · 空格 暂停 · [ ] 速度 · C 碰撞 · V 视野 · H 帮助 · F11 全屏",
            True, (174, 180, 189))
        w = hint.get_width()
        self.screen.blit(hint, ((self.camera.width - w) / 2, self.camera.height - 30))

        if self.message:
            m = self.font_small.render(self.message, True, (255, 232, 150))
            pad = 10
            # 提示条放在底部中央（底部操作提示上方），避免遮挡顶部面板与按钮
            rect = pygame.Rect((self.camera.width - m.get_width()) // 2 - pad,
                               self.camera.height - 72,
                               m.get_width() + pad * 2, 26)
            pygame.draw.rect(self.screen, (30, 34, 40), rect, border_radius=8)
            pygame.draw.rect(self.screen, (96, 102, 112), rect, 1, border_radius=8)
            self.screen.blit(m, (rect.x + pad, rect.y + 5))

        if self.show_help:
            self._draw_help_overlay()

        if self.show_chart:
            self._draw_population_chart()

    # ---- 种群曲线（左侧，随时间变化） ----
    def _draw_population_chart(self):
        hist = self.sim.history
        W, H = self.camera.width, self.camera.height
        pw = 430
        ph = min(230, max(140, int(H * 0.28)))
        px, py = 12, 158
        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel.fill((20, 22, 26, 195))
        self.screen.blit(panel, (px, py))

        title = self.font_small.render(f"种群数量（近 {config.CHART_WINDOW:g}s）", True, (232, 234, 237))
        self.screen.blit(title, (px + 10, py + 8))

        legend = [("plants", "植物", (111, 207, 151)),
                  ("prey", "猎物", (70, 160, 255)),
                  ("predators", "捕食者", (235, 80, 70))]
        self._chart_legend_rects = {}
        lx = px + 10
        for key, label, col in legend:
            on = self.chart_show[key]
            dot = "●" if on else "○"
            txt = self.font_small.render(f"{dot} {label}", True, col if on else (130, 136, 144))
            self.screen.blit(txt, (lx, py + 28))
            self._chart_legend_rects[key] = pygame.Rect(lx - 2, py + 26,
                                                        txt.get_width() + 4, 20)
            lx += txt.get_width() + 16

        gx, gy = px + 8, py + 52
        gw = pw - 16
        gh = ph - 52 - 24
        pygame.draw.rect(self.screen, (30, 34, 40), (gx, gy, gw, gh), border_radius=6)
        pygame.draw.rect(self.screen, (70, 76, 86), (gx, gy, gw, gh), 1, border_radius=6)

        if not hist:
            t = self.font_small.render("采样中…", True, (160, 166, 174))
            self.screen.blit(t, (gx + 10, gy + 10))
            return
        t_end = hist[-1][0]
        t0 = t_end - config.CHART_WINDOW
        ymax = 1
        for (t, pl, pr, pd) in hist:
            if t >= t0:
                for key, v in (("plants", pl), ("prey", pr), ("predators", pd)):
                    if self.chart_show[key]:
                        ymax = max(ymax, v)
        ymax = max(1, int(ymax * 1.1) + 1)

        def to_screen(t, v):
            x = gx + (t - t0) / config.CHART_WINDOW * gw
            y = gy + gh - (v / ymax) * (gh - 6) - 3
            return x, y

        for i in range(1, 5):
            yv = ymax * i / 4
            yy = gy + gh - (yv / ymax) * (gh - 6) - 3
            pygame.draw.line(self.screen, (58, 64, 72), (gx, yy), (gx + gw, yy))
            lab = self.font_small.render(str(int(yv)), True, (160, 166, 174))
            self.screen.blit(lab, (gx + 3, yy - 13))

        colors = {"plants": (111, 207, 151), "prey": (70, 160, 255), "predators": (235, 80, 70)}
        for key in ("plants", "prey", "predators"):
            if not self.chart_show[key]:
                continue
            pts = []
            for (t, pl, pr, pd) in hist:
                if t >= t0:
                    v = pl if key == "plants" else pr if key == "prey" else pd
                    pts.append(to_screen(t, v))
            if len(pts) >= 2:
                pygame.draw.lines(self.screen, colors[key], False, pts, 2)

        cur = hist[-1]
        val_txt = self.font_small.render(
            f"植物 {cur[1]} · 猎物 {cur[2]} · 捕食者 {cur[3]}", True, (222, 226, 231))
        self.screen.blit(val_txt, (gx, py + ph - 20))

    def _draw_tooltip(self, b):
        text = self.font_small.render(b.tip, True, (232, 234, 237))
        pad_x, pad_y = 8, 5
        w = text.get_width() + pad_x * 2
        h = text.get_height() + pad_y * 2
        # 提示放在按钮左侧（朝向地图一侧），避免与下一行按钮重叠
        x = b.rect.left - w - 6
        if x < 4:
            x = b.rect.right + 6
        y = b.rect.centery - h // 2
        y = max(4, min(self.camera.height - h - 4, y))
        rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(self.screen, (30, 34, 40), rect, border_radius=6)
        pygame.draw.rect(self.screen, (70, 76, 86), rect, 1, border_radius=6)
        self.screen.blit(text, (rect.x + pad_x, rect.y + pad_y))

    def _draw_help_overlay(self):
        W, H = self.camera.width, self.camera.height
        dim = pygame.Surface((W, H), pygame.SRCALPHA)
        dim.fill((10, 12, 16, 150))
        self.screen.blit(dim, (0, 0))

        rows = [
            ("左键拖拽", "平移视口"),
            ("鼠标滚轮", "缩放（以光标为锚点）"),
            ("空格", "暂停 / 继续"),
            ("[  /  ]", "减速 / 加速（0.5× – 64×）"),
            ("C", "显示 / 隐藏碰撞体积"),
            ("V", "显示 / 隐藏视野（猎物+捕食者）"),
            ("T", "显示 / 隐藏种群曲线（点击图例切换显示）"),
            ("H", "显示 / 隐藏本说明"),
            ("F11 / F", "切换全屏"),
            ("F5", "保存备份"),
            ("F9", "载入备份"),
            ("B", "保存当前最优大脑存档"),
            ("N", "查看神经网络存档"),
            ("自动", f"每 {config.AUTOSAVE_INTERVAL:g} 秒自动备份"),
            ("0", "恢复 50% 视图"),
            ("Esc", "退出"),
        ]
        pad = 20
        title_h = 34
        row_h = 26
        pw = 370
        ph = pad * 2 + title_h + row_h * len(rows) + 8
        panel = pygame.Rect((W - pw) // 2, (H - ph) // 2, pw, ph)
        pygame.draw.rect(self.screen, (26, 30, 36), panel, border_radius=12)
        pygame.draw.rect(self.screen, (80, 88, 100), panel, 1, border_radius=12)

        t = self.font_big.render("操作说明", True, (232, 234, 237))
        self.screen.blit(t, (panel.x + (pw - t.get_width()) // 2, panel.y + 14))

        y = panel.y + pad + title_h
        for key, desc in rows:
            k = self.font_small.render(key, True, (111, 207, 151))
            d = self.font_small.render(desc, True, (222, 226, 231))
            self.screen.blit(k, (panel.x + 30, y))
            self.screen.blit(d, (panel.x + 160, y))
            y += row_h

        tip = self.font_small.render("点击任意处或按 H 关闭", True, (160, 166, 174))
        self.screen.blit(tip, (panel.x + (pw - tip.get_width()) // 2, panel.bottom - 26))

    # ---- 神经网络存档查看器 ----
    def _draw_brain_viewer(self):
        W, H = self.camera.width, self.camera.height
        dim = pygame.Surface((W, H), pygame.SRCALPHA)
        dim.fill((10, 12, 16, 175))
        self.screen.blit(dim, (0, 0))

        lx, ly, lw, lh = 20, 44, 300, H - 88
        pygame.draw.rect(self.screen, (26, 30, 36), (lx, ly, lw, lh), border_radius=12)
        pygame.draw.rect(self.screen, (80, 88, 100), (lx, ly, lw, lh), 1, border_radius=12)
        t = self.font.render("神经网络存档", True, (232, 234, 237))
        self.screen.blit(t, (lx + 14, ly + 10))
        sub = self.font_small.render(f"brains/ 共 {len(self._bv_list)} 份", True, (160, 166, 174))
        self.screen.blit(sub, (lx + 14, ly + 36))

        row_h = 30
        list_top = ly + 62
        for i, (fn, data) in enumerate(self._bv_list):
            ry = list_top + i * row_h
            if ry + row_h < list_top or ry > ly + lh - 6:
                continue
            if i == self._bv_index:
                pygame.draw.rect(self.screen, (46, 52, 60), (lx + 8, ry, lw - 16, row_h - 4),
                                 border_radius=6)
                pygame.draw.rect(self.screen, (111, 207, 151), (lx + 8, ry, lw - 16, row_h - 4),
                                 1, border_radius=6)
            species = data.get("species", "?") if data else "?"
            if species == "prey":
                color = (70, 160, 255)
            elif species == "predator":
                color = (235, 80, 70)
            else:
                color = (174, 180, 189)
            dot = self.font_small.render("●", True, color)
            self.screen.blit(dot, (lx + 16, ry + 6))
            label = (fn[:24] if data else f"{fn[:24]} (损坏)")
            txt = self.font_small.render(label, True, (222, 226, 231))
            self.screen.blit(txt, (lx + 34, ry + 6))

        rx, ry, rw, rh = 336, 44, W - 356, H - 88
        pygame.draw.rect(self.screen, (26, 30, 36), (rx, ry, rw, rh), border_radius=12)
        pygame.draw.rect(self.screen, (80, 88, 100), (rx, ry, rw, rh), 1, border_radius=12)
        if self._bv_list:
            fn, data = self._bv_list[self._bv_index]
            self._draw_brain_detail(pygame.Rect(rx + 16, ry + 12, rw - 32, rh - 24), fn, data)
        else:
            t = self.font.render("暂无存档（模拟中按 B 保存最优大脑）", True, (174, 180, 189))
            self.screen.blit(t, (rx + 30, ry + 30))

        tip = self.font_small.render("↑↓ 选择 · 滚轮滚动 · N / Esc 关闭", True, (160, 166, 174))
        self.screen.blit(tip, (lx, H - 36))

    def _draw_brain_detail(self, rect, fn, data):
        x, y = rect.x, rect.y
        if data is None:
            t = self.font.render("文件损坏", True, (240, 150, 80))
            self.screen.blit(t, (x, y))
            return
        species = data.get("species", "?")
        st = data.get("stats", {})
        meta = data.get("meta", {})
        if species == "prey":
            color, name = (70, 160, 255), "猎物"
        elif species == "predator":
            color, name = (235, 80, 70), "捕食者"
        else:
            color, name = (232, 234, 237), species
        title = self.font.render(f"{name} · {fn}", True, color)
        self.screen.blit(title, (x, y))
        y += 28

        pop = meta.get("population", {})
        hs = st.get("hidden_sizes") or [st.get("hidden_size") or 10]
        genome = data.get("genome", [])
        traits_line = "形态性状: 未知"
        if genome:
            try:
                tr = decode_traits(genome)
                traits_line = (f"形态性状: 视距×{tr['vision']:.2f} · 体型×{tr['size']:.2f} · "
                               f"繁殖CD {tr['cd']:.1f}s · 速度×{tr['speed']:.2f}")
            except Exception:
                pass
        lines = [
            f"存档时间: {data.get('saved_at', '?')}",
            f"模拟时间: {meta.get('sim_time', '?')}s · 个体能量: {meta.get('energy', '?')}"
            f" · 世代(分裂数): {meta.get('generation', '?')}",
            f"种群: 植物 {pop.get('plants', '?')} · 猎物 {pop.get('prey', '?')}"
            f" · 捕食者 {pop.get('predators', '?')}",
            f"基因组: {st.get('genome_size', '?')} 个基因 · "
            f"结构 {st.get('input_size', '?')} → {hs[0] if hs else '?'} → {hs[1] if len(hs) > 1 else '?'} → 3",
            traits_line,
            f"权重: min {st.get('min', 0):.3f} · max {st.get('max', 0):.3f} · "
            f"mean {st.get('mean', 0):.3f} · std {st.get('std', 0):.3f}",
        ]
        for ln in lines:
            t = self.font_small.render(ln, True, (200, 205, 212))
            self.screen.blit(t, (x, y))
            y += 20
        y += 6

        if not genome:
            return
        n_in = st.get("input_size") or 0
        hs = st.get("hidden_sizes") or [st.get("hidden_size") or 10]
        hid = hs[0]
        maxabs = max(abs(st.get("min", 0.0)), abs(st.get("max", 0.0)), 1e-9)

        t = self.font_small.render("权重分布直方图（蓝=负，红=正）", True, (174, 180, 189))
        self.screen.blit(t, (x, y))
        y += 18
        hist_w = min(rect.w, 480)
        hist_h = 88
        bins = 40
        counts = [0] * bins
        for v in genome:
            idx = int((v + maxabs) / (2 * maxabs) * bins)
            idx = max(0, min(bins - 1, idx))
            counts[idx] += 1
        cmax = max(counts) or 1
        bw = hist_w / bins
        for i, c in enumerate(counts):
            bh = int(hist_h * c / cmax)
            if i < bins / 2:
                col = (60, 110, 230)
            else:
                col = (230, 90, 70)
            pygame.draw.rect(self.screen, col, (x + i * bw, y + hist_h - bh, max(1, bw - 1), bh))
        pygame.draw.rect(self.screen, (80, 88, 100), (x, y, hist_w, hist_h), 1)
        y += hist_h + 16

        if n_in > 0 and hid > 0 and len(genome) >= n_in * hid:
            t = self.font_small.render(
                f"W1 热力图（{n_in} 行输入 × {hid} 列隐层1，蓝=负 红=正）", True, (174, 180, 189))
            self.screen.blit(t, (x, y))
            y += 18
            cw = 9
            ch = max(4, min(12, (rect.bottom - y - 12) // max(1, n_in)))
            for r in range(n_in):
                for c in range(hid):
                    v = genome[r * hid + c]
                    frac = abs(v) / maxabs
                    if v >= 0:
                        col = lerp_color((52, 56, 64), (235, 90, 70), min(1.0, frac))
                    else:
                        col = lerp_color((52, 56, 64), (70, 130, 255), min(1.0, frac))
                    pygame.draw.rect(self.screen, col,
                                     (x + c * cw, y + r * ch, cw - 1, ch - 1))
            pygame.draw.rect(self.screen, (80, 88, 100), (x, y, hid * cw, n_in * ch), 1)

    def run(self):
        running = True
        while running:
            dt = min(self.clock.tick(60) / 1000.0, config.MAX_FRAME_DT)

            if self.show_brains:
                for event in pygame.event.get():
                    running = self._brain_viewer_handle(event)
            else:
                for event in pygame.event.get():
                    if not self.handle_event(event):
                        running = False
                self.update(dt)

            self.renderer.show_collision = self.show_collision
            self.renderer.show_vision = self.show_vision
            self.renderer.render(self.screen, self.sim.plants, self.sim.prey, self.sim.predators)
            self.draw_hud()
            if self.show_brains:
                self._draw_brain_viewer()
            pygame.display.flip()

        pygame.quit()
        sys.exit(0)


def main():
    from settings import SettingsScreen
    result = SettingsScreen().run()   # None=退出 | "start"=新开局 | "continue"=接上次进度
    if result is None:
        return
    app = App()
    if result == "continue":
        try:
            app.sim = Simulation.load(config.BACKUP_PATH)
            app._show_message("已接上上次进度")
        except Exception as e:
            app._show_message(f"进度载入失败: {e}")
    app.run()


if __name__ == "__main__":
    main()
