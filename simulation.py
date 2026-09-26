"""场景管理：植物 + 猎物 + 捕食者（视觉 / 神经网络 / 进食 / 繁殖）+ 碰撞与空间网格。

- 视觉统一：射线命中"最近物体"（植物绿 / 猎物蓝 / 捕食者红），叶片遮挡视线，
  猎物可藏身植物之间；猎物与捕食者视野角/视距不同。
- 繁殖（分裂）采用**稳态选择**：种群满员时用子代替换适应度最低的成年个体；
  适应度 = 一生累计进食能量 / 年龄（觅食速率），真正能觅食的个体得以留存。
- 灭绝救援使用**本次运行中最优基因组**（而非初始本能），保住进化成果。
- 视觉射线 numpy 向量化；视觉用粗网格，碰撞用细网格；变步长。
"""
import math
import pickle
import random

import numpy as np

import config
from brain import Brain, instinct_genome
from plant import Plant
from prey import Prey
from predator import Predator
from world import wrap, wrap_delta, torus_distance

# 体型性状上限对应的最大半径（视觉候选查询用）
PREY_RADIUS_MAX = config.PREY_BODY_RADIUS * config.TRAIT_SIZE_RANGE[1]
PREDATOR_RADIUS_MAX = config.PREDATOR_BODY_RADIUS * config.TRAIT_SIZE_RANGE[1]


class Simulation:
    def __init__(self):
        self.plants = []
        self.prey = []
        self.predators = []
        self.plant_grid = {}            # 碰撞用（细）
        self.plant_vision_grid = {}     # 视觉用（粗）
        self.prey_vision_grid = {}      # 视觉用（粗）
        self.predator_vision_grid = {}  # 视觉用（粗）
        self.collision_cell = config.PLANT_GRID_CELL
        self.vision_cell = config.VISION_GRID_CELL
        self.nc_collision = max(1, math.ceil(config.WORLD_SIZE / self.collision_cell))
        self.nc_vision = max(1, math.ceil(config.WORLD_SIZE / self.vision_cell))
        self._prey_offsets_np = np.asarray(self._make_ray_offsets(config.VISION_FOV_DEG))
        self._pred_offsets_np = np.asarray(self._make_ray_offsets(config.PREDATOR_VISION_FOV_DEG))
        self._seed_timer = 0.0
        self._prey_gone_timer = 0.0
        self._pred_gone_timer = 0.0
        self.splits_prey = 0
        self.splits_predator = 0
        self.time = 0.0
        # 种群历史（供左侧种群曲线）
        self.history = []            # [(t, plants, prey, predators)]
        self._history_timer = 0.0
        # 本次运行中最优基因组（灭绝救援时保留进化成果）
        self.best_prey_genome = None
        self.best_predator_genome = None
        self.best_prey_fitness = -1.0
        self.best_predator_fitness = -1.0

    def seed(self):
        S = config.WORLD_SIZE
        for i in range(config.PLANT_INITIAL_COUNT):
            self.plants.append(Plant(random.uniform(0, S), random.uniform(0, S),
                                     config.PLANT_INITIAL_ENERGY, i))
        for _ in range(config.PREY_INITIAL_COUNT):
            self.prey.append(Prey(random.uniform(0, S), random.uniform(0, S),
                                  genome=Brain(instinct_genome("prey")).mutated().genome))
        for _ in range(config.PREDATOR_INITIAL_COUNT):
            self.predators.append(Predator(random.uniform(0, S), random.uniform(0, S),
                                           genome=Brain(instinct_genome("predator")).mutated().genome))
        self._rebuild_plant_grid()
        self._rebuild_plant_vision_grid()
        self._rebuild_prey_vision_grid()
        self._rebuild_predator_vision_grid()
        self.relax(iterations=6)

    # ---- 空间网格 ----
    def _cell_of(self, x, y, cell, nc):
        return (int(x // cell) % nc, int(y // cell) % nc)

    def _build_grid(self, items, cell, nc):
        grid = {}
        for it in items:
            key = self._cell_of(it.x, it.y, cell, nc)
            grid.setdefault(key, []).append(it)
        return grid

    def _rebuild_plant_grid(self):
        self.plant_grid = self._build_grid(self.plants, self.collision_cell, self.nc_collision)

    def _rebuild_plant_vision_grid(self):
        self.plant_vision_grid = self._build_grid(
            [p for p in self.plants if not p.dying], self.vision_cell, self.nc_vision)

    def _rebuild_prey_vision_grid(self):
        self.prey_vision_grid = self._build_grid(
            [q for q in self.prey if not q.dying], self.vision_cell, self.nc_vision)

    def _rebuild_predator_vision_grid(self):
        self.predator_vision_grid = self._build_grid(
            [r for r in self.predators if not r.dying], self.vision_cell, self.nc_vision)

    def _candidates(self, grid, x, y, radius, cell, nc):
        ci, cj = self._cell_of(x, y, cell, nc)
        r_cells = int(math.ceil(radius / cell)) + 1
        out = []
        for i in range(ci - r_cells, ci + r_cells + 1):
            for j in range(cj - r_cells, cj + r_cells + 1):
                key = (i % nc, j % nc)
                out.extend(grid.get(key, ()))
        return out

    # ---- 植物互挤 ----
    def relax(self, iterations=3):
        for _ in range(iterations):
            moved = False
            for p in self.plants:
                for q in self._neighbors(p):
                    if q.id < p.id:
                        continue
                    if self._separate(p, q):
                        moved = True
            if not moved:
                break
            self._wrap_plants()
            self._rebuild_plant_grid()

    def _neighbors(self, p):
        ci, cj = self._cell_of(p.x, p.y, self.collision_cell, self.nc_collision)
        for i in range(ci - 1, ci + 2):
            for j in range(cj - 1, cj + 2):
                key = (i % self.nc_collision, j % self.nc_collision)
                for q in self.plant_grid.get(key, ()):
                    if q is not p:
                        yield q

    def _separate(self, p, q):
        dx = wrap_delta(q.x - p.x)
        dy = wrap_delta(q.y - p.y)
        d = math.hypot(dx, dy)
        min_d = p.collision_radius + q.collision_radius
        if d >= min_d:
            return False
        push = (min_d - d) / 2.0
        if d > 1e-9:
            ux, uy = dx / d, dy / d
        else:
            a = random.uniform(0, math.tau)
            ux, uy = math.cos(a), math.sin(a)
        p.x -= ux * push
        p.y -= uy * push
        q.x += ux * push
        q.y += uy * push
        return True

    def _wrap_plants(self):
        for p in self.plants:
            p.x = wrap(p.x)
            p.y = wrap(p.y)

    # ---- 视觉（猎物与捕食者通用） ----
    def _make_ray_offsets(self, fov_deg):
        n = config.VISION_RAYS
        fov = math.radians(fov_deg)
        if n <= 1:
            return [0.0]
        return [-fov / 2 + fov * i / (n - 1) for i in range(n)]

    @staticmethod
    def _raycast(ca, sa, cx, cy, cr):
        """返回 (最近命中距离 (R,), 命中对象下标 (R,))，未命中距离为 inf。"""
        if not cx:
            return np.full(len(ca), np.inf), np.zeros(len(ca), dtype=int)
        cx = np.asarray(cx)
        cy = np.asarray(cy)
        cr = np.asarray(cr)
        tca = cx[None, :] * ca[:, None] + cy[None, :] * sa[:, None]
        d2 = (cx[None, :] ** 2 + cy[None, :] ** 2) - tca * tca
        r2 = cr[None, :] ** 2
        hit = (tca >= 0.0) & (d2 <= r2)
        t = np.where(hit, tca - np.sqrt(np.maximum(r2 - d2, 0.0)), np.inf)
        return t.min(axis=1), t.argmin(axis=1)

    def _sense_agent(self, agent):
        """对任意智能体做射线采样：返回最近物体（植物/猎物/捕食者）的颜色与体型。"""
        R = agent.vision_range
        plant_cands = self._candidates(self.plant_vision_grid, agent.x, agent.y,
                                       R + config.PLANT_MAX_RADIUS, self.vision_cell, self.nc_vision)
        prey_cands = self._candidates(self.prey_vision_grid, agent.x, agent.y,
                                      R + PREY_RADIUS_MAX, self.vision_cell, self.nc_vision)
        pred_cands = self._candidates(self.predator_vision_grid, agent.x, agent.y,
                                      R + PREDATOR_RADIUS_MAX, self.vision_cell, self.nc_vision)

        def local(items, radius_get, R0):
            xs, ys, rs = [], [], []
            for it in items:
                if it.dying or it is agent:
                    continue
                lx = wrap_delta(it.x - agent.x)
                ly = wrap_delta(it.y - agent.y)
                rr = R0 + radius_get(it)
                if lx * lx + ly * ly <= rr * rr:
                    xs.append(lx)
                    ys.append(ly)
                    rs.append(radius_get(it))
            return xs, ys, rs

        plx, ply, plr = local(plant_cands, lambda p: p.radius, R)
        qlx, qly, qlr = local(prey_cands, lambda q: q.body_radius, R)
        rlx, rly, rlr = local(pred_cands, lambda r: r.body_radius, R)

        if isinstance(agent, Prey):
            offsets = self._prey_offsets_np
        else:
            offsets = self._pred_offsets_np
        angles = agent.heading + offsets
        ca = np.cos(angles)
        sa = np.sin(angles)
        plant_t, plant_i = self._raycast(ca, sa, plx, ply, plr)
        prey_t, prey_i = self._raycast(ca, sa, qlx, qly, qlr)
        pred_t, pred_i = self._raycast(ca, sa, rlx, rly, rlr)

        n = len(offsets)
        hits = []
        vision = []
        ch = agent.memory_channel
        mem = 0.0
        mem_rel = 0.0
        for i in range(n):
            # 最近者优先（并列时：植物 > 猎物 > 捕食者）；附带体型信息
            t, raw, rad = R + 1.0, config.VISION_EMPTY_COLOR, 0.0
            if plant_t[i] < t:
                t, raw, rad = float(plant_t[i]), config.VISION_PLANT_COLOR, plr[plant_i[i]]
            if prey_t[i] < t:
                t, raw, rad = float(prey_t[i]), config.VISION_PREY_COLOR, qlr[prey_i[i]]
            if pred_t[i] < t:
                t, raw, rad = float(pred_t[i]), config.VISION_PREDATOR_COLOR, rlr[pred_i[i]]
            hits.append((t, raw))
            if t >= R:
                vision.extend(config.VISION_EMPTY_COLOR)
                vision.append(0.0)                      # 体型通道：无命中为 0
            else:
                k = max(0.0, 1.0 - config.VISION_FALLOFF * (t / R))
                vision.extend((raw[0] * k, raw[1] * k, raw[2] * k))
                vision.append(min(1.0, rad / config.VISION_SIZE_REFERENCE))   # 体型通道
                if raw[ch] * k > mem:
                    mem = raw[ch] * k
                    mem_rel = float(offsets[i])

        if mem > agent.memory:
            agent.memory = mem
            agent.mem_dir = mem_rel
        agent.mem_dir = (agent.mem_dir + math.pi) % (2 * math.pi) - math.pi
        vision.append(min(1.0, agent.memory))
        vision.append(math.sin(agent.mem_dir))
        vision.append(math.cos(agent.mem_dir))
        # 自身状态输入（能量 / 当前速度 / 自身体型），让网络能按内部状态调节行为
        if isinstance(agent, Prey):
            thr = config.PREY_SPLIT_THRESHOLD
        else:
            thr = config.PREDATOR_SPLIT_THRESHOLD
        vision.append(min(1.0, max(0.0, agent.energy / max(thr, 1e-9))))
        vision.append(min(1.0, max(0.0, agent.v / max(agent.max_speed, 1e-9))))
        vision.append(min(1.0, agent.body_radius / config.VISION_SIZE_REFERENCE))
        # 递归记忆：上一决策的隐层2状态反馈
        vision.extend(float(x) for x in agent.brain.last_h2)

        agent.vision_hits = hits
        agent.vision_rays = list(angles)
        agent.vision = vision
        return vision

    # ---- 进食 ----
    def _eat_plant(self, prey):
        mx = wrap(prey.x + math.cos(prey.heading) * config.PREY_EAT_REACH)
        my = wrap(prey.y + math.sin(prey.heading) * config.PREY_EAT_REACH)
        reach = config.PLANT_COLLISION_RADIUS + config.PREY_EAT_RADIUS
        best = None
        best_d = float("inf")
        for p in self._candidates(self.plant_grid, mx, my,
                                  reach + self.collision_cell, self.collision_cell, self.nc_collision):
            if p.dying:
                continue
            d = torus_distance(mx, my, p.x, p.y)
            if d <= reach and d < best_d:
                best = p
                best_d = d
        if best is not None:
            prey.energy += best.energy
            prey.food_eaten += best.energy
            best.start_dying()

    def _eat_prey(self, predator):
        """捕食：吃口器触及的、体型小于自己的猎物；允许吃比自己小的同类（是否捕食由大脑行为决定）。"""
        mx = wrap(predator.x + math.cos(predator.heading) * config.PREDATOR_EAT_REACH)
        my = wrap(predator.y + math.sin(predator.heading) * config.PREDATOR_EAT_REACH)
        my_radius = predator.body_radius
        best = None
        best_d = float("inf")

        # 猎物（需体型更小才能吞下）
        if config.PREDATOR_PREY_SIZE_RULE:
            for q in self._candidates(self.prey_vision_grid, mx, my,
                                      config.PREDATOR_EAT_RADIUS + PREY_RADIUS_MAX,
                                      self.vision_cell, self.nc_vision):
                if q.dying or q.body_radius >= my_radius:
                    continue
                d = torus_distance(mx, my, q.x, q.y)
                reach = config.PREDATOR_EAT_RADIUS + q.body_radius
                if d <= reach and d < best_d:
                    best = q
                    best_d = d
        else:
            for q in self._candidates(self.prey_vision_grid, mx, my,
                                      config.PREDATOR_EAT_RADIUS + PREY_RADIUS_MAX,
                                      self.vision_cell, self.nc_vision):
                if q.dying:
                    continue
                d = torus_distance(mx, my, q.x, q.y)
                reach = config.PREDATOR_EAT_RADIUS + q.body_radius
                if d <= reach and d < best_d:
                    best = q
                    best_d = d

        # 同类相食：吃比自己体型小的捕食者
        if config.PREDATOR_CANNIBALISM:
            for r in self._candidates(self.predator_vision_grid, mx, my,
                                      config.PREDATOR_EAT_RADIUS + PREDATOR_RADIUS_MAX,
                                      self.vision_cell, self.nc_vision):
                if r is predator or r.dying or r.body_radius >= my_radius:
                    continue
                d = torus_distance(mx, my, r.x, r.y)
                reach = config.PREDATOR_EAT_RADIUS + r.body_radius
                if d <= reach and d < best_d:
                    best = r
                    best_d = d

        if best is not None:
            predator.energy += best.energy
            predator.food_eaten += best.energy
            best.start_dying()

    # ---- 适应度与稳态选择 ----
    @staticmethod
    def _fitness(a):
        """适应度 = (一生累计进食能量 + 繁殖次数折算能量) / 年龄。"""
        return (a.food_eaten + config.FITNESS_OFFSPRING_WEIGHT * a.offspring) / max(a.age, 1.0)

    def _consider_best(self, kind, a):
        f = self._fitness(a)
        if kind == "prey":
            if f > self.best_prey_fitness:
                self.best_prey_fitness = f
                self.best_prey_genome = list(a.brain.genome)
        else:
            if f > self.best_predator_fitness:
                self.best_predator_fitness = f
                self.best_predator_genome = list(a.brain.genome)

    def _add_with_selection(self, lst, child, max_count, grace):
        """稳态选择：未满员直接加入；满员则替换适应度最低的成年个体。"""
        if len(lst) < max_count:
            lst.append(child)
            return
        worst_i = None
        worst_f = None
        for i, a in enumerate(lst):
            if a.dying or a.age < grace:
                continue
            f = self._fitness(a)
            if worst_f is None or f < worst_f:
                worst_f = f
                worst_i = i
        if worst_i is not None:
            lst[worst_i] = child

    # ---- 繁殖（分裂） ----
    @staticmethod
    def _reproduction_cost(a):
        """繁殖成本：体型越大、速度越快，繁殖一次消耗的能量越多。"""
        s = a.brain.traits["speed"]
        z = a.brain.traits["size"]
        return config.REPRODUCTION_COST * (0.5 + 0.5 * s) * (0.5 + 0.5 * z)

    def _split_prey(self, prey):
        prey.energy = max(0.5, prey.energy - self._reproduction_cost(prey))   # 先支付繁殖成本
        half = prey.energy / 2.0
        prey.energy = half
        prey.split_cd = prey.split_cd_duration
        prey.offspring += 1
        self.splits_prey += 1
        self._consider_best("prey", prey)
        # 新单位与亲代出生在同一位置（不随机散布，避免"歪打正着"被吃或吃到食物）；
        # 仅保留极小朝向差，避免两个个体永久重叠同步运动
        child = Prey(prey.x, prey.y, half, genome=prey.brain.mutated().genome)
        child.heading = prey.heading + random.uniform(-0.3, 0.3)
        child.split_cd = child.split_cd_duration
        return child

    def _split_predator(self, pred):
        pred.energy = max(0.5, pred.energy - self._reproduction_cost(pred))   # 先支付繁殖成本
        half = pred.energy / 2.0
        pred.energy = half
        pred.split_cd = pred.split_cd_duration
        pred.offspring += 1
        self.splits_predator += 1
        self._consider_best("predator", pred)
        # 新单位与亲代出生在同一位置（不随机散布，避免"歪打正着"被吃或吃到食物）；
        # 仅保留极小朝向差，避免两个个体永久重叠同步运动
        child = Predator(pred.x, pred.y, half, genome=pred.brain.mutated().genome)
        child.heading = pred.heading + random.uniform(-0.3, 0.3)
        child.split_cd = child.split_cd_duration
        return child

    # ---- 智能体更新 ----
    def _move_and_eat(self, agent, dt, eat_fn):
        n_sub = max(1, int(math.ceil(agent.v * dt / config.MOVE_SUBSTEP_DIST)))
        sub_dt = dt / n_sub
        for _ in range(n_sub):
            agent.heading += math.radians(agent.w_deg) * sub_dt
            agent.heading %= math.tau
            agent.x += math.cos(agent.heading) * agent.v * sub_dt
            agent.y += math.sin(agent.heading) * agent.v * sub_dt
            agent.x = wrap(agent.x)
            agent.y = wrap(agent.y)
            eat_fn(agent)

    def _update_prey(self, prey, dt):
        prey.age += dt
        remaining = dt
        while remaining > 1e-9:
            tick = min(remaining, config.BRAIN_TICK)
            remaining -= tick
            prey.memory *= math.exp(-tick / config.MEMORY_HALF_LIFE)
            vision = self._sense_agent(prey)
            v_norm, w_norm, _ = prey.brain.forward(vision)
            prey.v = v_norm * prey.max_speed
            prey.w_deg = w_norm * config.PREY_MAX_ANGULAR_SPEED

            self._move_and_eat(prey, tick, self._eat_plant)

            prey.energy -= prey.metabolism * tick
            if prey.energy <= 0.0:
                prey.start_dying()
                return None
            if prey.energy >= config.PREY_SPLIT_THRESHOLD and prey.split_cd <= 0.0:
                return self._split_prey(prey)
            if prey.split_cd > 0.0:
                prey.split_cd = max(0.0, prey.split_cd - tick)

        prey.trail.append((prey.x, prey.y))
        if len(prey.trail) > config.PREY_TRAIL_LENGTH:
            prey.trail.pop(0)
        return None

    def _update_predator(self, pred, dt):
        pred.age += dt
        remaining = dt
        while remaining > 1e-9:
            tick = min(remaining, config.BRAIN_TICK)
            remaining -= tick
            pred.memory *= math.exp(-tick / config.MEMORY_HALF_LIFE)
            # 冲刺状态机：计时 + 冷却
            pred.burst_cd = max(0.0, pred.burst_cd - tick)
            if pred.bursting:
                pred.burst_timer -= tick
                if pred.burst_timer <= 0.0:
                    pred.bursting = False
                    pred.burst_cd = config.PREDATOR_BURST_CD
            vision = self._sense_agent(pred)
            v_norm, w_norm, sprint_p = pred.brain.forward(vision)
            if (not pred.bursting and pred.burst_cd <= 0.0
                    and sprint_p > config.PREDATOR_BURST_THRESHOLD):
                # 激活冲刺：双倍速度 + 双倍代谢
                pred.bursting = True
                pred.burst_timer = config.PREDATOR_BURST_DURATION
            if pred.bursting:
                speed_mult = config.PREDATOR_BURST_SPEED_MULT
                metab_mult = config.PREDATOR_BURST_METABOLISM_MULT
            else:
                speed_mult = 1.0
                metab_mult = 1.0
            pred.v = v_norm * pred.max_speed * speed_mult
            pred.w_deg = w_norm * config.PREDATOR_MAX_ANGULAR_SPEED

            self._move_and_eat(pred, tick, self._eat_prey)

            pred.energy -= pred.metabolism * metab_mult * tick
            if pred.energy <= 0.0:
                pred.start_dying()
                return None
            if pred.energy >= config.PREDATOR_SPLIT_THRESHOLD and pred.split_cd <= 0.0:
                return self._split_predator(pred)
            if pred.split_cd > 0.0:
                pred.split_cd = max(0.0, pred.split_cd - tick)

        pred.trail.append((pred.x, pred.y))
        if len(pred.trail) > config.PREDATOR_TRAIL_LENGTH:
            pred.trail.pop(0)
        return None

    # ---- 主步进 ----
    def step(self, dt):
        self.time += dt

        # 种群采样（供左侧曲线）
        self._history_timer += dt
        if self._history_timer >= config.CHART_SAMPLE_INTERVAL:
            self._history_timer -= config.CHART_SAMPLE_INTERVAL
            self.history.append((self.time, len(self.plants), len(self.prey), len(self.predators)))
            if len(self.history) > config.CHART_MAX_SAMPLES:
                self.history.pop(0)

        # 种子雨：随机萌发新植株（防止植物被吃绝）
        if config.PLANT_SEED_RATE > 0:
            self._seed_timer += dt
            interval = 1.0 / config.PLANT_SEED_RATE
            while self._seed_timer >= interval and len(self.plants) < config.PLANT_MAX_COUNT:
                self._seed_timer -= interval
                self.plants.append(Plant(
                    random.uniform(0, config.WORLD_SIZE),
                    random.uniform(0, config.WORLD_SIZE),
                    config.PLANT_OFFSPRING_ENERGY,
                    random.randint(0, config.PLANT_SPRITE_VARIANTS - 1)))

        # 植物：生长 + 淡出（密度反馈：植物越少，能量积累越快）
        if config.PLANT_SCARCITY_REFERENCE > 0:
            n_plants = len(self.plants)
            scarcity = max(0.0, 1.0 - n_plants / config.PLANT_SCARCITY_REFERENCE)
            growth_mult = 1.0 + config.PLANT_SCARCITY_BONUS * scarcity
        else:
            growth_mult = 1.0
        newborns = []
        for p in self.plants:
            if not p.dying:
                newborns.extend(p.update(dt, growth_mult))
            else:
                p.fade_timer -= dt

        added = 0
        for k in newborns:
            if len(self.plants) + added >= config.PLANT_MAX_COUNT:
                break
            k.x = wrap(k.x)
            k.y = wrap(k.y)
            self.plants.append(k)
            added += 1

        self.plants = [p for p in self.plants if not (p.dying and p.fade_timer <= 0.0)]

        self._rebuild_plant_grid()
        if added:
            self.relax(iterations=3)
        self._rebuild_plant_vision_grid()
        self._rebuild_prey_vision_grid()
        self._rebuild_predator_vision_grid()

        # 猎物
        new_prey = []
        for q in self.prey:
            if q.dying:
                q.fade_timer -= dt
            else:
                child = self._update_prey(q, dt)
                if child is not None:
                    new_prey.append(child)
        for c in new_prey:
            self._add_with_selection(self.prey, c, config.PREY_MAX_COUNT,
                                     config.SELECTION_GRACE)
        for q in self.prey:
            if q.dying and q.fade_timer <= 0.0:
                self._consider_best("prey", q)
        self.prey = [q for q in self.prey if not (q.dying and q.fade_timer <= 0.0)]

        # 捕食者
        new_preds = []
        for r in self.predators:
            if r.dying:
                r.fade_timer -= dt
            else:
                child = self._update_predator(r, dt)
                if child is not None:
                    new_preds.append(child)
        for c in new_preds:
            self._add_with_selection(self.predators, c, config.PREDATOR_MAX_COUNT,
                                     config.SELECTION_GRACE)
        for r in self.predators:
            if r.dying and r.fade_timer <= 0.0:
                self._consider_best("predator", r)
        self.predators = [r for r in self.predators if not (r.dying and r.fade_timer <= 0.0)]
        self._rebuild_predator_vision_grid()

        # 灭绝救援：用本次运行的最优基因组（而非初始本能）重新引入
        S = config.WORLD_SIZE
        if not self.prey:
            self._prey_gone_timer += dt
            if self._prey_gone_timer >= config.PREY_REINTRODUCE_DELAY:
                self._prey_gone_timer = 0.0
                base = (self.best_prey_genome if self.best_prey_genome is not None
                        else instinct_genome("prey"))
                for _ in range(config.PREY_REINTRODUCE_COUNT):
                    self.prey.append(Prey(random.uniform(0, S), random.uniform(0, S),
                                          genome=Brain(base).mutated().genome))
                self._rebuild_prey_vision_grid()
        else:
            self._prey_gone_timer = 0.0

        if not self.predators:
            self._pred_gone_timer += dt
            if self._pred_gone_timer >= config.PREDATOR_REINTRODUCE_DELAY:
                self._pred_gone_timer = 0.0
                base = (self.best_predator_genome if self.best_predator_genome is not None
                        else instinct_genome("predator"))
                for _ in range(config.PREDATOR_REINTRODUCE_COUNT):
                    self.predators.append(Predator(random.uniform(0, S), random.uniform(0, S),
                                                   genome=Brain(base).mutated().genome))
                self._rebuild_predator_vision_grid()
        else:
            self._pred_gone_timer = 0.0

    # ---- 备份：保存 / 载入完整状态（含基因组与最优记录） ----
    @staticmethod
    def _agent_dict(a):
        return {"x": a.x, "y": a.y, "heading": a.heading, "energy": a.energy,
                "genome": list(a.brain.genome), "split_cd": a.split_cd,
                "dying": a.dying, "fade_timer": a.fade_timer, "memory": a.memory,
                "mem_dir": a.mem_dir, "food_eaten": a.food_eaten, "age": a.age,
                "offspring": a.offspring,
                "bursting": getattr(a, "bursting", False),
                "burst_timer": getattr(a, "burst_timer", 0.0),
                "burst_cd": getattr(a, "burst_cd", 0.0)}

    @staticmethod
    def _agent_fields(data):
        """兼容新（字典）旧（元组）两种存档格式。"""
        if isinstance(data, dict):
            return (data.get("x", 0.0), data.get("y", 0.0), data.get("heading", 0.0),
                    data.get("energy", 1.0), data.get("genome", None),
                    data.get("split_cd", 0.0), data.get("dying", False),
                    data.get("fade_timer", 0.0), data.get("memory", 0.0),
                    data.get("mem_dir", 0.0), data.get("food_eaten", 0.0),
                    data.get("age", 0.0), data.get("offspring", 0),
                    data.get("bursting", False), data.get("burst_timer", 0.0),
                    data.get("burst_cd", 0.0))
        row = list(data) + [0.0] * 16
        return tuple(row[:16])

    @staticmethod
    def _config_snapshot():
        """当前 config 模块的所有可序列化参数（供"继续上次进度"恢复）。"""
        return {k: v for k, v in vars(config).items()
                if k.isupper() and not k.startswith("_")
                and isinstance(v, (int, float, bool, str, tuple, list))}

    def save(self, path):
        data = {
            "plants": [(p.x, p.y, p.energy, p.variant, p.rotation, p.mature, p.reproduced,
                        p.sway_phase, p.dying, p.fade_timer) for p in self.plants],
            "prey": [self._agent_dict(q) for q in self.prey],
            "predators": [self._agent_dict(r) for r in self.predators],
            "timers": (self._seed_timer, self._prey_gone_timer, self._pred_gone_timer, self.time),
            "counters": (self.splits_prey, self.splits_predator),
            "ids": (Plant._next_id, Prey._next_id, Predator._next_id),
            "best": (self.best_prey_genome, self.best_prey_fitness,
                     self.best_predator_genome, self.best_predator_fitness),
            "history": self.history,
            "config": self._config_snapshot(),
        }
        with open(path, "wb") as f:
            pickle.dump(data, f)

    @classmethod
    def load(cls, path):
        with open(path, "rb") as f:
            data = pickle.load(f)
        sim = cls()
        sim.plants = []
        for (x, y, e, v, rot, mature, repro, sway, dying, fade) in data["plants"]:
            p = Plant(x, y, e, v)
            p.rotation = rot
            p.mature = mature
            p.reproduced = repro
            p.sway_phase = sway
            p.dying = dying
            p.fade_timer = fade
            sim.plants.append(p)
        sim.prey = []
        for item in data["prey"]:
            x, y, h, e, g, cd, dying, fade, mem, mdir, food, age, off, _, _, _ = cls._agent_fields(item)
            q = Prey(x, y, e, genome=g, heading=h)
            q.split_cd = cd
            q.dying = dying
            q.fade_timer = fade
            q.memory = mem
            q.mem_dir = mdir
            q.food_eaten = food
            q.age = age
            q.offspring = off
            sim.prey.append(q)
        sim.predators = []
        for item in data["predators"]:
            x, y, h, e, g, cd, dying, fade, mem, mdir, food, age, off, bursting, btimer, bcd = cls._agent_fields(item)
            r = Predator(x, y, e, genome=g, heading=h)
            r.split_cd = cd
            r.dying = dying
            r.fade_timer = fade
            r.memory = mem
            r.mem_dir = mdir
            r.food_eaten = food
            r.age = age
            r.offspring = off
            r.bursting = bursting
            r.burst_timer = btimer
            r.burst_cd = bcd
            sim.predators.append(r)
        sim._seed_timer, sim._prey_gone_timer, sim._pred_gone_timer = data["timers"][:3]
        sim.time = data["timers"][3] if len(data["timers"]) > 3 else 0.0
        sim.splits_prey, sim.splits_predator = data["counters"]
        Plant._next_id, Prey._next_id, Predator._next_id = data["ids"]
        if data.get("best"):
            (sim.best_prey_genome, sim.best_prey_fitness,
             sim.best_predator_genome, sim.best_predator_fitness) = data["best"]
        sim.history = [tuple(h) for h in data.get("history", [])]
        sim._rebuild_plant_grid()
        sim._rebuild_plant_vision_grid()
        sim._rebuild_prey_vision_grid()
        sim._rebuild_predator_vision_grid()
        return sim
