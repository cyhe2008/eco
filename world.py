"""环形世界（torus）的坐标辅助函数。

四周为环绕边界：从左边出去、右边进来，避免"墙角死局"破坏进化压力。
"""
import config


def wrap(v, size=config.WORLD_SIZE):
    """将坐标折叠回 [0, size)。"""
    return ((v % size) + size) % size


def wrap_delta(d, size=config.WORLD_SIZE):
    """环面上最短有符号距离，返回结果满足 |result| <= size/2。"""
    d = d % size
    if d > size / 2:
        d -= size
    if d < -size / 2:
        d += size
    return d


def torus_distance(ax, ay, bx, by, size=config.WORLD_SIZE):
    """环面上两点间的最短欧氏距离。"""
    dx = wrap_delta(bx - ax, size)
    dy = wrap_delta(by - ay, size)
    return (dx * dx + dy * dy) ** 0.5
