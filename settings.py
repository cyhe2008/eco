"""启动参数设置屏：模拟开始前以图形界面调整一系列参数。

操作：
  滚轮/点击      滚动与选中参数行
  ← → 或 [-] [+] 减小/增大（Shift 放大 10 倍步进）
  Enter          直接输入数值（数字/负号/小数点，Enter 确认，Esc 取消）
  R              恢复默认值
  开始模拟 / Enter  应用参数并进入模拟（设置自动保存，下次运行直接沿用）
  继续上次进度      载入上次手动存档（含开局设置），接着上次的进度继续
"""
import json
import os
import pickle

import pygame

import config


def load_font(size, bold=False):
    for name in ("simhei", "microsoftyahei", "simsun"):
        path = pygame.font.match_font(name, bold=bold)
        if path:
            return pygame.font.Font(path, size)
    return pygame.font.Font(None, size)


def load_saved_settings():
    """读取上次保存的开局设置（json）。"""
    try:
        with open(config.SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_settings(values):
    """把开局设置写入磁盘，下次运行直接沿用。"""
    try:
        with open(config.SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(values, f, ensure_ascii=False, indent=1)
    except Exception:
        pass


def backup_has_config():
    return os.path.exists(config.BACKUP_PATH)


def apply_backup_config():
    """读取备份中保存的开局设置并应用到 config 模块（供"继续上次进度"）。"""
    with open(config.BACKUP_PATH, "rb") as f:
        data = pickle.load(f)
    snap = data.get("config")
    if snap:
        for k, v in snap.items():
            if k.isupper():
                try:
                    setattr(config, k, v)
                except Exception:
                    pass


# (config 属性名, 中文标签, 类型, 最小值, 最大值, 步进)
SCHEMA = [
    ("WORLD_SIZE", "世界边长", int, 300, 2000, 100),
    ("PLANT_INITIAL_COUNT", "初始植物", int, 20, 600, 20),
    ("PLANT_GROWTH_RATE", "植物生长速率", float, 0.02, 0.30, 0.02),
    ("PLANT_MAX_ENERGY", "植物成熟能量", float, 2.0, 10.0, 0.5),
    ("PLANT_MAX_COUNT", "植物上限", int, 200, 3000, 100),
    ("PLANT_SEED_RATE", "种子雨（株/秒）", float, 0.0, 5.0, 0.2),
    ("PLANT_SCARCITY_BONUS", "植物稀缺增益", float, 0.0, 6.0, 0.5),
    ("PLANT_SCARCITY_REFERENCE", "植物稀缺基准", int, 50, 1000, 50),
    ("PREY_INITIAL_COUNT", "初始猎物", int, 5, 150, 5),
    ("PREY_MAX_COUNT", "猎物上限", int, 50, 800, 50),
    ("PREY_METABOLISM", "猎物代谢", float, 0.01, 0.20, 0.01),
    ("PREY_SPLIT_THRESHOLD", "猎物分裂阈值", float, 5.0, 20.0, 0.5),
    ("PREY_MAX_LINEAR_SPEED", "猎物速度", float, 2.0, 15.0, 0.5),
    ("VISION_RANGE", "猎物视距", float, 10.0, 80.0, 5.0),
    ("VISION_FOV_DEG", "猎物视野角", int, 90, 360, 10),
    ("PREDATOR_INITIAL_COUNT", "初始捕食者", int, 1, 60, 1),
    ("PREDATOR_MAX_COUNT", "捕食者上限", int, 10, 200, 10),
    ("PREDATOR_METABOLISM", "捕食者代谢", float, 0.01, 0.20, 0.01),
    ("PREDATOR_SPLIT_THRESHOLD", "捕食者分裂阈值", float, 5.0, 25.0, 0.5),
    ("PREDATOR_MAX_LINEAR_SPEED", "捕食者速度", float, 2.0, 15.0, 0.5),
    ("PREDATOR_VISION_RANGE", "捕食者视距", float, 20.0, 160.0, 5.0),
    ("PREDATOR_VISION_FOV_DEG", "捕食者视野角", int, 60, 360, 10),
    ("PREDATOR_EAT_RADIUS", "捕食者口器半径", float, 1.0, 10.0, 0.5),
    ("PREDATOR_CANNIBALISM", "同类相食（0关1开）", int, 0, 1, 1),
    ("PREDATOR_BURST_DURATION", "冲刺持续（秒）", float, 0.5, 8.0, 0.5),
    ("PREDATOR_BURST_CD", "冲刺冷却（秒）", float, 1.0, 15.0, 1.0),
    ("VISION_RAYS", "射线数量", int, 4, 32, 1),
    ("BRAIN_HIDDEN1", "隐层1神经元", int, 8, 64, 4),
    ("BRAIN_HIDDEN2", "隐层2神经元", int, 4, 32, 2),
    ("BRAIN_TICK", "决策间隔（模拟秒）", float, 0.02, 0.50, 0.02),
    ("GA_MUTATION_RATE", "变异概率", float, 0.0, 0.50, 0.01),
    ("GA_MUTATION_MAGNITUDE", "变异幅度（0–5%）", float, 0.005, 0.10, 0.005),
    ("SELECTION_GRACE", "幼体保护期（秒）", float, 0.0, 60.0, 5.0),
    ("FITNESS_OFFSPRING_WEIGHT", "繁殖权重", float, 0.0, 40.0, 2.0),
    ("REPRODUCTION_COST", "繁殖基础成本", float, 0.0, 10.0, 0.5),
    ("AUTOSAVE_INTERVAL", "自动备份（秒，0 关）", float, 0.0, 600.0, 15.0),
]

DEFAULTS = {key: getattr(config, key) for (key, *_) in SCHEMA}


def fmt(row):
    v = row["value"]
    return str(int(v)) if row["typ"] is int else f"{v:g}"


class SettingsScreen:
    def __init__(self):
        pygame.init()
        info = pygame.display.Info()
        self.w = max(760, int(info.current_w * 0.75))
        self.h = max(540, int(info.current_h * 0.75))
        self.screen = pygame.display.set_mode((self.w, self.h), pygame.RESIZABLE)
        pygame.display.set_caption("生态缸 · 参数设置")
        self.clock = pygame.time.Clock()
        self.font = load_font(18)
        self.font_small = load_font(14)
        self.font_title = load_font(24, bold=True)

        saved = load_saved_settings()
        self.rows = []
        for (k, lab, t, mn, mx, st) in SCHEMA:
            v = saved.get(k, DEFAULTS[k])
            try:
                v = t(v)
                v = max(mn, min(mx, v))
            except Exception:
                v = DEFAULTS[k]
            self.rows.append({"key": k, "label": lab, "typ": t, "min": mn, "max": mx,
                              "step": st, "value": v})
        self.scroll = 0
        self.selected = 0
        self.typing = None          # 正在输入的缓冲区
        self.start_rect = pygame.Rect(0, 0, 200, 48)
        self.save_rect = pygame.Rect(0, 0, 130, 48)
        self.reset_rect = pygame.Rect(0, 0, 130, 48)
        self.continue_rect = pygame.Rect(0, 0, 210, 48)
        self.feedback = ""
        self.feedback_until = 0

    # ---- 布局 ----
    @property
    def list_rect(self):
        # 底部为"继续上次进度"按钮留出空间，避免行被按钮遮挡
        return pygame.Rect(30, 70, self.w - 60, self.h - 232)

    def _row_rect(self, i):
        lr = self.list_rect
        return pygame.Rect(lr.x, lr.y + i * 34 - self.scroll, lr.w, 34)

    def _max_scroll(self):
        return max(0, len(self.rows) * 34 - self.list_rect.height)

    # ---- 值操作 ----
    def _adjust(self, row, delta):
        v = row["value"] + delta
        v = max(row["min"], min(row["max"], v))
        row["value"] = round(v, 6) if row["typ"] is float else int(round(v))
        row["value"] = row["typ"](row["value"])

    def _commit_typing(self):
        row = self.rows[self.selected]
        try:
            v = float(self.typing)
            v = max(row["min"], min(row["max"], v))
            row["value"] = row["typ"](v)
        except ValueError:
            pass
        self.typing = None

    def _apply(self):
        for row in self.rows:
            setattr(config, row["key"], row["value"])
        # 记住本次开局设置，下次运行直接沿用
        save_settings({row["key"]: row["value"] for row in self.rows})

    def _reset(self):
        for row in self.rows:
            row["value"] = DEFAULTS[row["key"]]

    # ---- 事件 ----
    def _handle(self, event):
        if event.type == pygame.QUIT:
            return "quit"
        if event.type == pygame.VIDEORESIZE:
            self.w, self.h = event.w, event.h
            return None
        if event.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, min(self._max_scroll(), self.scroll - event.y * 34))
            return None
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if self.start_rect.collidepoint(pos):
                self._apply()
                return "start"
            if self.save_rect.collidepoint(pos):
                save_settings({row["key"]: row["value"] for row in self.rows})
                self.feedback = "已保存参数设置"
                self.feedback_until = pygame.time.get_ticks() + 2000
                return None
            if self.reset_rect.collidepoint(pos):
                self._reset()
                return None
            if self.continue_rect.collidepoint(pos) and backup_has_config():
                try:
                    apply_backup_config()
                    return "continue"
                except Exception:
                    return None
            for i, row in enumerate(self.rows):
                r = self._row_rect(i)
                if r.collidepoint(pos):
                    self.selected = i
                    # 行内 [-] [+] 按钮
                    btns = pygame.Rect(r.x + r.w - 110, r.y + 4, 48, 26)
                    btp = pygame.Rect(r.x + r.w - 56, r.y + 4, 48, 26)
                    if btns.collidepoint(pos):
                        self._adjust(row, -row["step"])
                    elif btp.collidepoint(pos):
                        self._adjust(row, row["step"])
                    self.typing = None
                    return None
            return None
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "quit"
            if self.typing is not None:
                if event.key == pygame.K_RETURN:
                    self._commit_typing()
                elif event.key == pygame.K_BACKSPACE:
                    self.typing = self.typing[:-1]
                elif event.unicode and event.unicode in "0123456789.-":
                    self.typing += event.unicode
                return None
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._apply()
                return "start"
            if event.key == pygame.K_r:
                self._reset()
            elif event.key == pygame.K_UP:
                self.selected = max(0, self.selected - 1)
            elif event.key == pygame.K_DOWN:
                self.selected = min(len(self.rows) - 1, self.selected + 1)
            elif event.key == pygame.K_PAGEUP:
                self.selected = max(0, self.selected - 8)
            elif event.key == pygame.K_PAGEDOWN:
                self.selected = min(len(self.rows) - 1, self.selected + 8)
            elif event.key in (pygame.K_LEFT, pygame.K_MINUS, pygame.K_KP_MINUS):
                self._adjust(self.rows[self.selected],
                             -self.rows[self.selected]["step"] * (10 if pygame.key.get_mods() & pygame.KMOD_SHIFT else 1))
            elif event.key in (pygame.K_RIGHT, pygame.K_EQUALS, pygame.K_KP_PLUS):
                self._adjust(self.rows[self.selected],
                             self.rows[self.selected]["step"] * (10 if pygame.key.get_mods() & pygame.KMOD_SHIFT else 1))
            elif event.key == pygame.K_RETURN:
                self._apply()
                return "start"
            elif event.key == pygame.K_e:
                self.typing = ""
            # 保持选中行可见
            self._ensure_visible()
        return None

    def _ensure_visible(self):
        lr = self.list_rect
        r = self._row_rect(self.selected)
        if r.top < lr.top:
            self.scroll -= (lr.top - r.top)
        elif r.bottom > lr.bottom:
            self.scroll += (r.bottom - lr.bottom)
        self.scroll = max(0, min(self._max_scroll(), self.scroll))

    # ---- 绘制 ----
    def _draw(self):
        s = self.screen
        s.fill((24, 26, 30))
        title = self.font_title.render("生态缸 · 参数设置", True, (232, 234, 237))
        s.blit(title, (30, 20))

        lr = self.list_rect
        s.set_clip(lr)
        for i, row in enumerate(self.rows):
            r = self._row_rect(i)
            if r.bottom < lr.top or r.top > lr.bottom:
                continue
            sel = (i == self.selected)
            bg = (46, 52, 60) if sel else (33, 36, 42)
            pygame.draw.rect(s, bg, r, border_radius=8)
            if sel:
                pygame.draw.rect(s, (111, 207, 151), r, 1, border_radius=8)
            label = self.font.render(row["label"], True, (222, 226, 231))
            s.blit(label, (r.x + 14, r.y + 5))
            text = self.typing if (sel and self.typing is not None) else fmt(row)
            val = self.font.render(text, True, (111, 207, 151) if sel else (174, 180, 189))
            s.blit(val, (r.x + r.w - 210, r.y + 5))
            # [-] [+] 按钮
            bm = pygame.Rect(r.x + r.w - 110, r.y + 4, 48, 26)
            bp = pygame.Rect(r.x + r.w - 56, r.y + 4, 48, 26)
            pygame.draw.rect(s, (40, 44, 52), bm, border_radius=6)
            pygame.draw.rect(s, (40, 44, 52), bp, border_radius=6)
            pygame.draw.rect(s, (70, 76, 86), bm, 1, border_radius=6)
            pygame.draw.rect(s, (70, 76, 86), bp, 1, border_radius=6)
            m = self.font_small.render("-", True, (232, 234, 237))
            p_ = self.font_small.render("+", True, (232, 234, 237))
            s.blit(m, m.get_rect(center=bm.center))
            s.blit(p_, p_.get_rect(center=bp.center))
        s.set_clip(None)

        # 滚动条
        max_scroll = self._max_scroll()
        if max_scroll > 0:
            sb = pygame.Rect(self.w - 14, lr.y, 8, lr.height)
            pygame.draw.rect(s, (40, 44, 52), sb, border_radius=4)
            th = max(30, int(lr.height * lr.height / (lr.height + max_scroll)))
            ty = lr.y + int(self.scroll / max_scroll * (lr.height - th))
            pygame.draw.rect(s, (90, 96, 106), (self.w - 14, ty, 8, th), border_radius=4)

        # 底部按钮
        self.start_rect = pygame.Rect(self.w // 2 - 250, self.h - 90, 200, 48)
        self.save_rect = pygame.Rect(self.w // 2 - 40, self.h - 90, 130, 48)
        self.reset_rect = pygame.Rect(self.w // 2 + 100, self.h - 90, 130, 48)
        pygame.draw.rect(s, (46, 96, 74), self.start_rect, border_radius=10)
        pygame.draw.rect(s, (111, 207, 151), self.start_rect, 1, border_radius=10)
        pygame.draw.rect(s, (40, 44, 52), self.save_rect, border_radius=10)
        pygame.draw.rect(s, (70, 76, 86), self.save_rect, 1, border_radius=10)
        pygame.draw.rect(s, (40, 44, 52), self.reset_rect, border_radius=10)
        pygame.draw.rect(s, (70, 76, 86), self.reset_rect, 1, border_radius=10)
        st = self.font.render("开始模拟 (Enter)", True, (232, 234, 237))
        sv = self.font.render("保存设置", True, (232, 234, 237))
        rt = self.font.render("恢复默认 (R)", True, (232, 234, 237))
        s.blit(st, st.get_rect(center=self.start_rect.center))
        s.blit(sv, sv.get_rect(center=self.save_rect.center))
        s.blit(rt, rt.get_rect(center=self.reset_rect.center))

        # 保存反馈
        if self.feedback and pygame.time.get_ticks() < self.feedback_until:
            fb = self.font_small.render(self.feedback, True, (255, 232, 150))
            s.blit(fb, ((self.w - fb.get_width()) // 2, self.h - 112))

        # 继续上次进度按钮
        can_continue = backup_has_config()
        self.continue_rect = pygame.Rect(self.w // 2 - 210, self.h - 150, 200, 44)
        if can_continue:
            pygame.draw.rect(s, (52, 84, 110), self.continue_rect, border_radius=10)
            pygame.draw.rect(s, (110, 160, 210), self.continue_rect, 1, border_radius=10)
            ct = self.font.render("继续上次进度", True, (232, 234, 237))
        else:
            pygame.draw.rect(s, (34, 36, 40), self.continue_rect, border_radius=10)
            pygame.draw.rect(s, (58, 62, 68), self.continue_rect, 1, border_radius=10)
            ct = self.font.render("无上次进度", True, (120, 126, 134))
        s.blit(ct, ct.get_rect(center=self.continue_rect.center))

        hint = self.font_small.render(
            "选中行后：← → 或点击 [-] [+] 调整（Shift 加速）· Enter 直接输入 · 滚轮滚动"
            " · 可点「保存设置」存档",
            True, (160, 166, 174))
        s.blit(hint, ((self.w - hint.get_width()) // 2, self.h - 36))

    def run(self):
        while True:
            for event in pygame.event.get():
                result = self._handle(event)
                if result == "start":
                    return True
                if result == "quit":
                    return False
            self._draw()
            pygame.display.flip()
            self.clock.tick(60)
