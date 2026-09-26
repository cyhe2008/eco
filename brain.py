"""神经网络（大脑）与遗传算法的基因组工具。

结构：输入(视觉 RGB+体型 + 目标记忆 + 自身状态 + 递归反馈) → 隐层1(tanh) → 隐层2(tanh)
      → 输出 [线速度归一化, 角速度归一化]。
基因组 = 网络权重/偏置 + 4 个可进化形态性状基因（视距/体型/繁殖冷却/速度），
变异/交叉作用于整个基因组；前向用 numpy 向量化。
"""
import math
import random

import numpy as np

import config

TRAIT_ORDER = ["vision", "size", "cd", "speed"]
TRAIT_BOUNDS = {
    "vision": config.TRAIT_VISION_RANGE,
    "size": config.TRAIT_SIZE_RANGE,
    "cd": config.TRAIT_CD_RANGE,
    "speed": config.TRAIT_SPEED_RANGE,
}
TRAIT_COUNT = len(TRAIT_ORDER)


def input_size():
    # 12 射线 × (RGB + 体型) 48 + 目标记忆强度/方向 3 + 自身能量/速度/体型 3
    # + 上一决策隐层2状态反馈（隐层2大小）
    return config.VISION_RAYS * 4 + 6 + hidden_sizes()[1]


def hidden_sizes():
    return (config.BRAIN_HIDDEN1, config.BRAIN_HIDDEN2)


def nn_size():
    n_in = input_size()
    h1, h2 = hidden_sizes()
    return n_in * h1 + h1 + h1 * h2 + h2 + h2 * 3 + 3   # W1+b1+W2+b2+W3+b3（输出：速度/转向/冲刺）


def genome_size():
    return nn_size() + TRAIT_COUNT


def _random_traits():
    return [random.uniform(*TRAIT_BOUNDS[k]) for k in TRAIT_ORDER]


def random_genome():
    n_in = input_size()
    h1, h2 = hidden_sizes()
    g = []
    for _ in range(n_in * h1):
        g.append(random.gauss(0.0, 1.0 / math.sqrt(n_in)))   # W1（Xavier 尺度）
    g += [0.0] * h1                                         # b1
    for _ in range(h1 * h2):
        g.append(random.gauss(0.0, 1.0 / math.sqrt(h1)))     # W2
    g += [0.0] * h2                                         # b2
    for _ in range(h2 * 3):
        g.append(random.gauss(0.0, 1.0 / math.sqrt(h2)))     # W3
    g += [0.0, 0.0, 0.0]                                    # b3
    g += _random_traits()                                   # 形态性状
    return g


def decode_traits(g):
    """从基因组尾部解码 4 个形态性状（钳制到合法范围）。"""
    n = len(g)
    out = {}
    for k, v in zip(TRAIT_ORDER, g[n - TRAIT_COUNT:n]):
        lo, hi = TRAIT_BOUNDS[k]
        out[k] = min(hi, max(lo, float(v)))
    return out


class Brain:
    """两层前馈网络 + 形态性状：视觉 -> (v_norm ∈ [0,1], w_norm ∈ [-1,1])。"""

    def __init__(self, genome=None):
        self.genome = list(genome) if genome is not None else random_genome()
        self._unpack()
        # 递归记忆：上一决策的隐层2状态（作为下次输入的反馈）
        self.last_h2 = np.zeros(hidden_sizes()[1])

    def _unpack(self):
        n_in = input_size()
        h1, h2 = hidden_sizes()
        g = self.genome
        pos = 0
        self.w1 = np.array(g[pos:pos + n_in * h1], dtype=float).reshape(n_in, h1)
        pos += n_in * h1
        self.b1 = np.array(g[pos:pos + h1], dtype=float)
        pos += h1
        self.w2 = np.array(g[pos:pos + h1 * h2], dtype=float).reshape(h1, h2)
        pos += h1 * h2
        self.b2 = np.array(g[pos:pos + h2], dtype=float)
        pos += h2
        self.w3 = np.array(g[pos:pos + h2 * 3], dtype=float).reshape(h2, 3)
        pos += h2 * 3
        self.b3 = np.array(g[pos:pos + 3], dtype=float)
        self.traits = decode_traits(g)

    def forward(self, vision):
        """vision: 长度 = input_size() 的浮点列表（含上一决策隐层反馈）。

        返回 (v_norm ∈ [0,1], w_norm ∈ [-1,1], sprint_p ∈ [0,1])。
        第三输出为"冲刺"倾向（捕食者用：付出双倍代谢获得双倍速度）。
        """
        x = np.asarray(vision, dtype=float)
        h1 = np.tanh(x @ self.w1 + self.b1)
        h2 = np.tanh(h1 @ self.w2 + self.b2)
        self.last_h2 = h2.copy()              # 递归记忆（供下一次输入）
        y = h2 @ self.w3 + self.b3
        v = 1.0 / (1.0 + math.exp(-float(y[0])))   # sigmoid -> [0,1]
        w = math.tanh(float(y[1]))                 # tanh -> [-1,1]
        p = 1.0 / (1.0 + math.exp(-float(y[2])))   # sigmoid -> [0,1]（冲刺倾向）
        return v, w, p

    def mutated(self):
        """返回一个带变异的子代大脑。

        变异幅度严格限制：每个被选中变异的基因，其数值按**相对比例**增加或缩小
        0–5%（均匀分布，方向随机）——不会再出现"突变巨兽"。
        对接近 0 的权重使用小绝对步长，保证权重仍可跨越零点探索。
        性状基因变异后钳制回合法范围。
        """
        g = list(self.genome)
        n = len(g)
        rate = config.GA_MUTATION_RATE
        mag = config.GA_MUTATION_MAGNITUDE
        n_t = TRAIT_COUNT
        for i in range(n):
            if random.random() < rate:
                is_trait = i >= n - n_t
                base = max(abs(g[i]), 0.1)
                g[i] += random.uniform(-mag, mag) * base
                if is_trait:
                    lo, hi = TRAIT_BOUNDS[TRAIT_ORDER[i - (n - n_t)]]
                    g[i] = min(hi, max(lo, g[i]))
        return Brain(g)


def breed_genome(genome_a, genome_b):
    """有性繁殖：均匀交叉（每个基因随机取自亲代 A 或 B）+ 变异。"""
    crossed = [a if random.random() < 0.5 else b for a, b in zip(genome_a, genome_b)]
    return Brain(crossed).mutated().genome


def instinct_genome(kind):
    """初代"本能"基因组（GA 的暖启动，之后由进化自由修改）。

    - "predator"：追逐蓝色（猎物），持续快速游动；
    - "prey"：趋向绿色（植物）、逃离红色（捕食者），遇险冲刺。

    实现：隐层1 放置 4 个探测器（转向/存在性），隐层2 直通前 4 个神经元，
    输出层与旧单层网络等价。形态性状取中性值（1×/1×/物种默认CD/1×）。
    """
    n_in = input_size()
    h1, h2 = hidden_sizes()
    assert h2 >= 4, "隐层2至少需要 4 个神经元用于本能直通"
    n_rays = config.VISION_RAYS
    fov = math.radians(config.PREDATOR_VISION_FOV_DEG if kind == "predator"
                       else config.VISION_FOV_DEG)
    offsets = [-fov / 2 + fov * i / (n_rays - 1) for i in range(n_rays)]

    w1 = np.zeros((n_in, h1))
    b1 = np.zeros(h1)
    w2 = np.zeros((h1, h2))
    b2 = np.zeros(h2)
    w3 = np.zeros((h2, 3))
    b3 = np.zeros(3)

    i_mem = config.VISION_RAYS * 4          # 记忆输入下标

    def channel(slot, ch, gain, weights):
        for i in range(n_rays):
            w1[i * 4 + ch, slot] = gain * weights[i]

    if kind == "predator":
        channel(0, 2, 1.0, [math.sin(a) * 0.6 for a in offsets])   # h0：朝蓝转向
        channel(1, 2, 1.0, [1.0] * n_rays)                          # h1：蓝色存在性
        w1[i_mem, 1] = 0.8                                          # 记忆（蓝色）→ h1
        b1[1] = -0.3
        w2[0, 0] = w2[1, 1] = w2[2, 2] = w2[3, 3] = 1.5             # 直通
        w3[0, 1] = 2.5     # 朝蓝转向 -> 角速度
        w3[1, 0] = 1.5     # 蓝色存在 -> 线速度
        b3[0] = 2.0        # 线速度基线（高速巡游）
        b3[1] = 0.2        # 角速度小基线
        b3[2] = -1.0       # 冲刺倾向基线（本能默认不冲刺，由进化学习何时用）
        cd = config.PREDATOR_SPLIT_CD
    elif kind == "prey":
        channel(0, 1, 1.0, [math.sin(a) * 0.6 for a in offsets])   # h0：朝绿转向
        channel(1, 1, 1.0, [0.5] * n_rays)                          # h1：绿色存在性
        channel(2, 0, -1.0, [math.sin(a) * 1.5 for a in offsets])   # h2：离红转向
        channel(3, 0, 1.0, [1.0] * n_rays)                          # h3：红色存在性
        w1[i_mem, 3] = 0.8                                          # 记忆（红色）→ h3
        b1[1] = -1.5       # 绿色需要累积
        b1[3] = -1.0       # 红色近距离才触发
        w2[0, 0] = w2[1, 1] = w2[2, 2] = w2[3, 3] = 1.5             # 直通
        w3[0, 1] = 2.2     # 绿转 -> 角速度
        w3[2, 1] = 4.0     # 红逃 -> 角速度（强）
        w3[1, 0] = 0.5     # 绿存 -> 线速度（温和）
        w3[3, 0] = 5.0     # 红存 -> 线速度（冲刺）
        b3[0] = 0.3        # 线速度基线（缓游）
        b3[1] = 0.0
        b3[2] = -1.0       # 冲刺输出（猎物不使用）
        cd = config.PREY_SPLIT_CD
    else:
        raise ValueError(kind)

    g = list(w1.flatten()) + list(b1) + list(w2.flatten()) + list(b2) \
        + list(w3.flatten()) + list(b3)
    # 中性形态性状（体型/视距/速度 1×，繁殖CD为物种默认）
    g += [1.0, 1.0, cd, 1.0]
    return g
