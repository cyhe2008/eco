"""猎物（食草者）实体：视觉感知 + 神经网络决策 + 移动 + 进食 + 分裂。"""
import math
import random

import config
from brain import Brain


class Prey:
    _next_id = 0

    def __init__(self, x, y, energy=None, genome=None, heading=None):
        Prey._next_id += 1
        self.id = Prey._next_id
        self.x = x
        self.y = y
        self.heading = heading if heading is not None else random.uniform(0, math.tau)
        self.energy = config.PREY_INITIAL_ENERGY if energy is None else energy
        self.brain = Brain(genome)
        self.split_cd = 0.0
        self.dying = False
        self.fade_timer = 0.0
        self.trail = []                # 最近位置（用于尾迹）
        self.v = 0.0                   # 当前线速度
        self.w_deg = 0.0               # 当前角速度（度/秒）
        self.vision = []               # 归一化视觉输入（脑输入）
        self.vision_hits = []          # [(t, raw_color)]（用于画射线）
        self.vision_rays = []          # 每条射线的绝对角度（用于画射线）
        self.memory = 0.0              # 目标记忆强度（红色，衰减）
        self.mem_dir = 0.0             # 目标记忆方向（相对朝向，弧度）
        self.food_eaten = 0.0          # 一生累计进食能量（适应度基础）
        self.age = 0.0                 # 年龄（秒）
        self.offspring = 0             # 已产生后代数

    @property
    def body_radius(self):
        """体型（可进化）：基础半径 × 体型倍率。"""
        return config.PREY_BODY_RADIUS * self.brain.traits["size"]

    @property
    def vision_range(self):
        """视距（可进化）：基础视距 × 视距倍率。"""
        return config.VISION_RANGE * self.brain.traits["vision"]

    @property
    def max_speed(self):
        """最大线速度（可进化）：基础速度 × 速度倍率。"""
        return config.PREY_MAX_LINEAR_SPEED * self.brain.traits["speed"]

    @property
    def split_cd_duration(self):
        """繁殖冷却时长（可进化）。"""
        return self.brain.traits["cd"]

    @property
    def metabolism(self):
        """代谢率：速度越快、体型越大、视距越远，消耗越大。"""
        s = self.brain.traits["speed"]
        z = self.brain.traits["size"]
        v = self.brain.traits["vision"]
        return config.PREY_METABOLISM * (0.5 + 0.5 * s) * (0.5 + 0.5 * z) * (0.9 + 0.1 * v)

    @property
    def vision_fov(self):
        return config.VISION_FOV_DEG

    @property
    def memory_channel(self):
        return 0                       # 记住红色通道（捕食者）

    def start_dying(self):
        self.dying = True
        self.fade_timer = config.PREY_FADE_DURATION
