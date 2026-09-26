"""植物实体：随时间积累能量并长大，成熟后停止生长并散播后代。"""
import math
import random

import config


class Plant:
    _next_id = 0

    def __init__(self, x, y, energy=None, variant=0):
        Plant._next_id += 1
        self.id = Plant._next_id
        self.x = x
        self.y = y
        self.energy = config.PLANT_INITIAL_ENERGY if energy is None else energy
        self.variant = variant          # 贴图变体
        self.rotation = random.uniform(0, math.tau)
        self.mature = False
        self.reproduced = False
        self.sway_phase = random.uniform(0.0, 1.0)   # 摆动动画相位
        self.dying = False
        self.fade_timer = 0.0

    @property
    def radius(self):
        """叶片半径（仅用于外观）：随能量增长（按面积开方，生长更自然）。"""
        t = min(self.energy / config.PLANT_MAX_ENERGY, 1.0)
        return (config.PLANT_BASE_RADIUS +
                (config.PLANT_MAX_RADIUS - config.PLANT_BASE_RADIUS) * math.sqrt(t))

    @property
    def collision_radius(self):
        """物理碰撞半径：较小、位于中心，不计叶片（供互挤与智能体寻路）。"""
        return config.PLANT_COLLISION_RADIUS

    def start_dying(self):
        """被吃掉：进入淡出状态。"""
        self.dying = True
        self.fade_timer = config.PLANT_FADE_DURATION

    def update(self, dt, growth_mult=1.0):
        """推进生长（growth_mult 为密度反馈倍率：植物越少积累越快）；成熟瞬间返回新后代列表。"""
        if self.dying:
            return []
        if self.mature:
            return []
        self.energy += config.PLANT_GROWTH_RATE * growth_mult * dt
        if self.energy >= config.PLANT_MAX_ENERGY:
            self.energy = config.PLANT_MAX_ENERGY
            self.mature = True
            return self.reproduce()
        return []

    def reproduce(self):
        """在周围随机位置生成 1–3 株能量 0 的新植株（每株只繁殖一次）。"""
        if self.reproduced:
            return []
        self.reproduced = True
        n = random.randint(config.PLANT_OFFSPRING_MIN, config.PLANT_OFFSPRING_MAX)
        kids = []
        for _ in range(n):
            a = random.uniform(0, math.tau)
            d = random.uniform(0, config.PLANT_SPREAD_RADIUS)
            kids.append(Plant(
                self.x + math.cos(a) * d,
                self.y + math.sin(a) * d,
                config.PLANT_OFFSPRING_ENERGY,
                self.variant,
            ))
        return kids
