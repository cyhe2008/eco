# -*- coding: utf-8 -*-
"""截图脚本：用程序自身渲染器生成 README 配图。"""
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame

pygame.init()
pygame.display.set_mode((1280, 800))
os.makedirs("images", exist_ok=True)

W, H = 1280, 800

# 1) 启动参数设置屏
import settings as S
sc = S.SettingsScreen()
sc.screen = pygame.display.set_mode((W, H), pygame.RESIZABLE)
sc.w, sc.h = W, H
sc._draw()
pygame.image.save(sc.screen, "images/settings.png")
print("settings.png")

# 2) 模拟主界面（含 HUD、按钮、种群曲线）
import main
app = main.App()
app.screen = pygame.display.set_mode((W, H), pygame.RESIZABLE)
app.camera.resize(W, H)
app.camera.fit(ref_side=H)
for _ in range(900):            # 推进 90 模拟秒，让世界热闹起来
    app.sim.step(0.1)
app.show_chart = True
app.renderer.render(app.screen, app.sim.plants, app.sim.prey, app.sim.predators)
app.draw_hud()
pygame.image.save(app.screen, "images/world.png")
print("world.png")

# 3) 视野显示（放大 + 双物种视野锥与射线）
app.show_chart = False
app.show_vision = True
app.camera.zoom = 3.5
app.camera.x = app.camera.y = 300
app.renderer.show_vision = True
app.renderer.render(app.screen, app.sim.plants, app.sim.prey, app.sim.predators)
app.draw_hud()
pygame.image.save(app.screen, "images/vision.png")
print("vision.png")

# 4) 神经网络存档查看器
app.show_vision = False
app.renderer.show_vision = False
app.camera.fit(ref_side=H)
app._save_best_brains()
app.toggle_brains()
app.renderer.render(app.screen, app.sim.plants, app.sim.prey, app.sim.predators)
app.draw_hud()
app._draw_brain_viewer()
pygame.image.save(app.screen, "images/brains.png")
print("brains.png")

# 5) 操作说明面板
app.show_brains = False
app.show_help = True
app.renderer.render(app.screen, app.sim.plants, app.sim.prey, app.sim.predators)
app.draw_hud()
pygame.image.save(app.screen, "images/help.png")
print("help.png")

print("ALL SCREENSHOTS SAVED")
