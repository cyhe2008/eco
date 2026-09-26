"""所有可调参数集中于此，便于后续进化实验复现与调参。"""

# ---- 世界 ----
WORLD_SIZE = 600         # 世界边长（世界单位），正方形（与视觉 25 匹配，便于单位可见）
GRID_SIZE = 20           # 网格线间距（世界单位）

# ---- 视图 ----
INITIAL_FRACTION = 0.5   # 初始：地图占电脑全屏的 50%（取屏幕短边）
MIN_ZOOM = 0.08          # 最小缩放（像素 / 世界单位）
MAX_ZOOM = 8             # 最大缩放
ZOOM_STEP = 1.25         # 每格滚轮 / 按钮的缩放倍率

# ---- 植物 ----
PLANT_INITIAL_COUNT = 160
PLANT_INITIAL_ENERGY = 1.0
PLANT_MAX_ENERGY = 5.0       # 成熟阈值：达到后停止生长并繁殖
PLANT_GROWTH_RATE = 0.08     # 能量 / 秒
PLANT_BASE_RADIUS = 5        # 能量 0 时的叶片半径（世界单位，仅外观）
PLANT_MAX_RADIUS = 24        # 成熟时的叶片半径（世界单位，仅外观）
PLANT_OFFSPRING_MIN = 1      # 成熟时生成后代数量下限
PLANT_OFFSPRING_MAX = 3      # 成熟时生成后代数量上限
PLANT_OFFSPRING_ENERGY = 0.0 # 后代初始能量
PLANT_SPREAD_RADIUS = 46     # 后代散布半径（世界单位）
PLANT_SPRITE_VARIANTS = 6    # 预生成的俯视贴图种类数
PLANT_MAX_COUNT = 1200       # 植株总数软上限（防止失控）
PLANT_SEED_RATE = 5.0        # "种子雨"：每秒随机萌发的新植株数（防止植物被吃绝）
PLANT_COLLISION_RADIUS = 4   # 物理碰撞半径（茎/中心，较小，不计叶片）
PLANT_GRID_CELL = 8          # 空间网格单元尺寸（需整除 WORLD_SIZE）

# ---- 植物动画 ----
SWAY_AMPLITUDE_DEG = 4       # 摆动幅度（度）
SWAY_FREQUENCY = 0.6         # 摆动频率（Hz）
SWAY_FRAMES = 8              # 每个摆动周期预渲染帧数

# ---- 死亡淡出 ----
PLANT_FADE_DURATION = 1.2    # 植物被吃后的淡出时长（秒）
PREY_FADE_DURATION = 1.0     # 猎物死亡淡出时长（秒）

# ---- 猎物（食草者） ----
PREY_INITIAL_COUNT = 20
PREY_INITIAL_ENERGY = 5.0
PREY_SPLIT_THRESHOLD = 10.0     # 能量达到该值触发分裂
PREY_SPLIT_CD = 5.0             # 分裂冷却（秒）；CD 期间能量可超过阈值
PREY_MAX_COUNT = 250            # 猎物数量软上限（限制过度放牧）
PREY_METABOLISM = 0.04          # 能量消耗 / 秒（饥饿死亡 → 自然选择）
PREY_BODY_RADIUS = 5            # 身体视觉半径（世界单位）
PREY_EAT_REACH = 7              # 口器判定中心到身体中心的前伸距离
PREY_EAT_RADIUS = 4             # 口器判定半径
PREY_MAX_LINEAR_SPEED = 8.0     # 线速度上限（世界单位 / 秒）
PREY_MAX_ANGULAR_SPEED = 180    # 角速度上限（度 / 秒）
MOVE_SUBSTEP_DIST = 2.0         # 移动子步最大距离（避免高速大步穿越食物）
PREY_TRAIL_LENGTH = 18          # 尾迹点数
PREY_COLOR = (70, 160, 255)     # 身体蓝色
PREY_GLOW_COLOR = (60, 140, 255)  # 荧光辉光

# ---- 捕食者（肉食者） ----
PREDATOR_INITIAL_COUNT = 6
PREDATOR_INITIAL_ENERGY = 8.0
PREDATOR_SPLIT_THRESHOLD = 12.0    # 能量达到该值触发分裂（首餐后可繁殖，此后约两餐一次）
PREDATOR_SPLIT_CD = 5.0            # 分裂冷却（秒）
PREDATOR_MAX_COUNT = 45            # 数量软上限（同类相食会自限，此处为硬上限）
PREDATOR_METABOLISM = 0.09         # 能量消耗 / 秒（猎物稀少时快速饿死 → 猎物得以反弹）
PREDATOR_BODY_RADIUS = 6           # 身体视觉半径
PREDATOR_EAT_REACH = 8             # 口器判定中心前伸距离
PREDATOR_EAT_RADIUS = 1            # 口器判定半径（较小：咬合更精确）
PREDATOR_MAX_LINEAR_SPEED = 9.0    # 略快于猎物（8）：直线追逐占优
PREDATOR_MAX_ANGULAR_SPEED = 150   # 略慢于猎物（180）：猎物可急转甩脱
PREDATOR_TRAIL_LENGTH = 18
PREDATOR_COLOR = (235, 80, 70)         # 身体红色
PREDATOR_GLOW_COLOR = (255, 120, 95)   # 荧光辉光
PREDATOR_FADE_DURATION = 1.0           # 死亡淡出时长（秒）

# ---- 视觉 ----
VISION_RAYS = 12
VISION_FOV_DEG = 270          # 猎物视野角
VISION_RANGE = 50.0
PREDATOR_VISION_RANGE = 90.0  # 捕食者视距更远（猎手感官），可从猎物感知范围外接近
PREDATOR_VISION_FOV_DEG = 180 # 捕食者视野角更窄（"望远镜"式感官，追丢更易发生）
VISION_PLANT_COLOR = (0.15, 0.85, 0.25)   # 归一化 RGB（射线命中颜色）
VISION_PREY_COLOR = (0.25, 0.55, 1.0)
VISION_PREDATOR_COLOR = (1.0, 0.2, 0.15)  # 捕食者（红色，猎物可据此逃跑）
VISION_EMPTY_COLOR = (0.0, 0.0, 0.0)
VISION_FALLOFF = 0.5           # 距离衰减强度（0.5 = 最远距离仍保留一半亮度，利于远距离感知）
VISION_GRID_CELL = 32          # 视觉空间网格单元尺寸（较粗，加速射线查询）
VISION_SIZE_REFERENCE = 15.0   # 视觉"体型通道"的归一化基准（世界单位，超过即饱和为 1）

# ---- 神经网络 ----
BRAIN_HIDDEN1 = 24             # 隐层1神经元数
BRAIN_HIDDEN2 = 12             # 隐层2神经元数
BRAIN_TICK = 0.12              # 决策间隔（模拟秒）：网络感知+输出的频率下限（高倍速下行为更连贯）
MEMORY_HALF_LIFE = 1.2         # 目标记忆半衰期（秒）：猎物记红/捕食者记蓝，反应更持久

# ---- 可进化形态性状（基因组尾部的 4 个基因，随变异遗传；上限已放开） ----
TRAIT_VISION_RANGE = (0.5, 30.0)    # 视距倍率（30 仅为数值安全线，可继续调大）
TRAIT_SIZE_RANGE = (0.5, 30.0)      # 体型倍率（捕食者须体型更大才能吃下猎物）
TRAIT_CD_RANGE = (1.0, 120.0)       # 繁殖冷却（秒）
TRAIT_SPEED_RANGE = (0.5, 30.0)     # 速度倍率
# 性状代价（自我限制，防止数值无界膨胀）：
#   代谢 × (0.5+0.5×速度) × (0.5+0.5×体型) × (0.9+0.1×视距)
#   繁殖成本 × (0.5+0.5×速度) × (0.5+0.5×体型)

# ---- 捕食规则 ----
PREDATOR_CANNIBALISM = True       # 允许捕食者吃掉比自己体型小的同类（是否捕食由大脑行为决定）
PREDATOR_PREY_SIZE_RULE = True    # 捕食者体型必须大于猎物才能成功捕食

# ---- 捕食者冲刺能力：付出双倍代谢，获得一段时间 1.5 倍速度，有冷却 ----
PREDATOR_BURST_SPEED_MULT = 1.5          # 冲刺速度倍率
PREDATOR_BURST_METABOLISM_MULT = 2.0     # 冲刺期间代谢倍率（代价）
PREDATOR_BURST_DURATION = 2.0            # 冲刺持续时间（秒）
PREDATOR_BURST_CD = 4.0                  # 冲刺冷却（秒）
PREDATOR_BURST_THRESHOLD = 0.5           # 网络第三输出（冲刺倾向）的激活阈值

# ---- 植物密度反馈：植物越少，能量积累越快 ----
PLANT_SCARCITY_BONUS = 2.0        # 植物数量为 0 时的额外生长倍率
PLANT_SCARCITY_REFERENCE = 300    # 植物数量达到该值时无增益（线性插值）

# ---- 灭绝救援（安全网：灭绝后一段时间自动重新引入少量个体，保证演示可持续） ----
PREY_REINTRODUCE_DELAY = 15.0      # 猎物灭绝后等待（秒）
PREY_REINTRODUCE_COUNT = 6         # 重新引入数量
PREDATOR_REINTRODUCE_DELAY = 30.0  # 捕食者灭绝后等待（秒）
PREDATOR_REINTRODUCE_COUNT = 3     # 重新引入数量

# ---- 备份 ----
BACKUP_PATH = "eco_backup.pkl"      # 手动备份文件（F5 保存 / F9 载入）
AUTOSAVE_PATH = "eco_autosave.pkl"  # 自动备份文件
AUTOSAVE_INTERVAL = 60.0            # 自动备份间隔（真实秒，0 = 关闭）
SETTINGS_FILE = "eco_settings.json" # 开局设置持久化文件（下次运行自动沿用）

# ---- 种群曲线 ----
CHART_SAMPLE_INTERVAL = 1.0         # 采样间隔（模拟秒）
CHART_MAX_SAMPLES = 600             # 保留的最大样本数（600 秒）
CHART_WINDOW = 120.0                # 曲线显示的时间窗口（模拟秒）

# ---- 遗传算法 ----
GA_MUTATION_RATE = 0.05        # 每个基因发生变异的概率
GA_MUTATION_MAGNITUDE = 0.05   # 变异幅度：每次变化为当前值的增加或缩小 0–5%（相对值）

# ---- 稳态选择（挑选真正能觅食、能繁殖的个体） ----
SELECTION_GRACE = 15.0            # 幼体保护期（秒）：此年龄内不被适应度淘汰替换
FITNESS_OFFSPRING_WEIGHT = 10.0   # 每个后代折算的适应度能量（约等于分裂阈值，繁殖次数进入评价指标）
REPRODUCTION_COST = 1.5           # 繁殖基础能量成本：实际成本 × (0.5+0.5×速度) × (0.5+0.5×体型)

# ---- 模拟 ----
MAX_FRAME_DT = 0.1           # 单帧最大真实时间（秒），防止卡顿跳变

# ---- 速度控制 ----
SPEED_LEVELS = [0.5, 1, 2, 4, 8, 16, 32, 64]  # 模拟速度倍率（0.5 慢动作 … 64 倍速）
DEFAULT_SPEED_INDEX = 1                       # 默认 1×

# ---- 颜色（RGB） ----
OUTSIDE_BACKGROUND = (24, 26, 30)    # 世界之外的底色（深灰，衬托地图）
WORLD_BACKGROUND = (59, 63, 70)      # 世界内的灰色平面
GRID_LINE = (82, 87, 94)             # 网格线
BOUNDARY_LINE = (120, 126, 136)      # 基本域边界（虚线示意"一张地图"的范围）
COLLISION_COLOR = (111, 207, 151)    # 碰撞体积圈
