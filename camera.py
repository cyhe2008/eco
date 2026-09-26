"""视口相机：世界坐标 <-> 屏幕坐标、缩放（以光标为锚点）与平移。"""
import config


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


class Camera:
    def __init__(self, world_size):
        self.world_size = world_size
        self.x = world_size / 2.0   # 视口中心的世界坐标
        self.y = world_size / 2.0
        self.zoom = 1.0             # 像素 / 世界单位
        self.width = 0              # 视口像素尺寸
        self.height = 0

    def resize(self, width, height):
        self.width = width
        self.height = height

    def fit(self, fraction=config.INITIAL_FRACTION, ref_side=None):
        """让整张地图占参考边长的 fraction 比例并居中。

        ref_side 缺省时取视口短边；传入桌面短边即可实现"占电脑全屏 50%"。
        """
        if ref_side is None:
            ref_side = min(self.width, self.height)
        self.zoom = clamp(fraction * ref_side / self.world_size,
                          config.MIN_ZOOM, config.MAX_ZOOM)
        self.x = self.world_size / 2.0
        self.y = self.world_size / 2.0

    def screen_to_world(self, sx, sy):
        return (
            self.x + (sx - self.width / 2) / self.zoom,
            self.y + (sy - self.height / 2) / self.zoom,
        )

    def world_to_screen(self, wx, wy):
        return (
            (wx - self.x) * self.zoom + self.width / 2,
            (wy - self.y) * self.zoom + self.height / 2,
        )

    def zoom_at(self, sx, sy, factor):
        """以屏幕某点为锚点缩放，保持该点下的世界坐标不变。"""
        bx, by = self.screen_to_world(sx, sy)
        self.zoom = clamp(self.zoom * factor, config.MIN_ZOOM, config.MAX_ZOOM)
        ax, ay = self.screen_to_world(sx, sy)
        self.x += bx - ax
        self.y += by - ay

    def pan_screen(self, dx, dy):
        """按屏幕像素平移视口。"""
        self.x -= dx / self.zoom
        self.y -= dy / self.zoom
