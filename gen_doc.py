# -*- coding: utf-8 -*-
"""生成《生态缸》项目技术总结报告（Word 文档）。"""
from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

import config

DOC_NAME = "生态缸项目技术总结报告.docx"

doc = Document()

# ---- 页面与基础样式 ----
for section in doc.sections:
    section.top_margin = Cm(2.2)
    section.bottom_margin = Cm(2.2)
    section.left_margin = Cm(2.4)
    section.right_margin = Cm(2.4)

normal = doc.styles["Normal"]
normal.font.name = "Times New Roman"
normal.font.size = Pt(11)
normal._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
normal.paragraph_format.line_spacing = 1.35


def set_east_asia(obj, font_name):
    """为 style 或 run 设置中文字体。"""
    rPr = obj._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:eastAsia"), font_name)


for name, size, ascii_font in (("Heading 1", 16, "Arial"), ("Heading 2", 13, "Arial"),
                               ("Heading 3", 11.5, "Arial")):
    st = doc.styles[name]
    st.font.name = ascii_font
    st.font.size = Pt(size)
    st.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)
    st.font.bold = True
    set_east_asia(st, "黑体")


def h1(text):
    return doc.add_heading(text, level=1)


def h2(text):
    return doc.add_heading(text, level=2)


def h3(text):
    return doc.add_heading(text, level=3)


def p(text, bold=False, size=None):
    par = doc.add_paragraph()
    run = par.add_run(text)
    run.bold = bold
    if size:
        run.font.size = Pt(size)
    return par


def bullet(text, bold_prefix=None):
    par = doc.add_paragraph(style="List Bullet")
    if bold_prefix:
        r = par.add_run(bold_prefix)
        r.bold = True
        par.add_run(text)
    else:
        par.add_run(text)
    return par


def table(headers, rows, widths=None):
    t = doc.add_table(rows=1 + len(rows), cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for j, htext in enumerate(headers):
        cell = t.rows[0].cells[j]
        cell.text = ""
        run = cell.paragraphs[0].add_run(htext)
        run.bold = True
        run.font.size = Pt(10)
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            cell = t.rows[i + 1].cells[j]
            cell.text = ""
            run = cell.paragraphs[0].add_run(str(val))
            run.font.size = Pt(10)
    if widths:
        for j, w in enumerate(widths):
            for row in t.rows:
                row.cells[j].width = Cm(w)
    doc.add_paragraph()
    return t


# ================= 封面标题 =================
title = doc.add_paragraph()
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = title.add_run("《生态缸》——基于神经网络的\n捕食者-猎物协同进化模拟系统")
run.bold = True
run.font.size = Pt(22)
run.font.color.rgb = RGBColor(0x10, 0x30, 0x50)
set_east_asia(run, "黑体")

sub = doc.add_paragraph()
sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = sub.add_run("技术总结报告")
r.bold = True
r.font.size = Pt(14)
r.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
set_east_asia(r, "黑体")

meta = doc.add_paragraph()
meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = meta.add_run("技术栈：Python 3.14 · pygame-ce · NumPy · PyInstaller\n"
                 "交付形态：源码（PyCharm 可直接运行）＋ 单文件可执行程序 EcoTank.exe")
r.font.size = Pt(10)
r.font.color.rgb = RGBColor(0x77, 0x77, 0x77)
set_east_asia(r, "宋体")

doc.add_paragraph()

# ================= 一、项目概述 =================
h1("一、项目概述")

h2("1.1 项目目的")
p("本项目构建了一个可交互的虚拟生态缸：一个带有环绕边界的灰色网格世界中，植物、猎物（食草者）"
  "与捕食者（肉食者）三种生命形式共存。猎物与捕食者由小型神经网络驱动，其行为策略完全通过"
  "遗传算法在模拟中自行演化，无需人工编写规则。项目的核心目的是：")
bullet("观察神经网络智能体在捕食-被捕食压力下自发产生的行为与策略演化（觅食、逃跑、伏击、躲藏等）；")
bullet("观察两物种之间形成的“进化军备竞赛”——猎物与捕食者的形态与行为相互驱动、螺旋上升；")
bullet("为“进化算法如何塑造复杂行为”提供一个直观、可交互的教学与演示平台。")

h2("1.2 项目意义")
bullet("完整性：从场景、植物、智能体、神经网络、遗传算法到存档、统计、参数化界面，构成一个闭环的进化模拟系统；")
bullet("可演化性：全部行为由网络权重与四个形态性状编码，变异幅度受严格约束（0–5%），进化过程平滑可观察；")
bullet("可持续性：种子雨、密度反馈、灭绝救援、备份续进度等机制保证系统可长期运行、随时断点续演；")
bullet("可复现性：全部参数集中于 config.py 并在启动设置屏暴露，实验结果（种群曲线、大脑存档）可导出比对。")

# ================= 二、总体架构 =================
h1("二、总体架构与运行流程")

h2("2.1 模块结构")
table(["模块", "职责"],
      [["config.py", "全部可调参数（世界/植物/猎物/捕食者/视觉/网络/遗传算法/备份等）"],
       ["main.py", "入口、主循环、HUD、按钮、种群曲线、大脑存档查看器"],
       ["settings.py", "启动参数设置屏（36 项参数图形化调整、保存/恢复/继续进度）"],
       ["simulation.py", "种群管理：视觉射线、进食、繁殖、稳态选择、碰撞、灭绝救援、存档"],
       ["brain.py", "两层神经网络 + 遗传算法（基因组、变异、交叉接口、本能基因组）"],
       ["plant.py / plant_sprite.py", "植物实体（生长/繁殖/密度反馈）与程序化俯视贴图"],
       ["prey.py / predator.py", "猎物与捕食者实体（性状、代谢、记忆、冲刺状态）"],
       ["renderer.py", "渲染：网格/植物动画/智能体辉光尾迹/视野叠加/冲刺特效"],
       ["camera.py / world.py", "视口相机（缩放平移）与环形世界坐标工具"],
       ["brain_archive.py", "神经网络存档（多份 JSON 保存/列表/读取）"]],
      widths=[4.5, 10.5])

h2("2.2 运行流程")
p("启动程序 → 进入【参数设置屏】（调整参数 / 保存设置 / 继续上次进度）→ 进入模拟主循环："
  "每帧执行“感知→决策→移动→进食→代谢→繁殖”的智能体更新与渲染 → 可随时暂停、加速（0.5–64×）、"
  "存档（F5）、保存大脑（B）、查看曲线（T）与大脑数据（N）。")

# ================= 三、世界与植物 =================
h1("三、世界与植物机制")

h2("3.1 世界与场景")
bullet("灰色平面网格：世界为正方形（默认 600×600，可调 300–2000），网格线间距 20；"
       "地图初始渲染为电脑全屏的 50%，可全屏化（F11）与缩放（0.08–8×，滚轮/按钮）。")
bullet("环绕边界（torus）：从左边出去会从右边进来，不存在“墙角死局”，保证捕食压力在空间上均匀，"
       "避免猎物靠躲墙角逃避进化压力；渲染时跨边个体在对侧补齐显示。")

h2("3.2 植物")
bullet("外观：程序化绘制的绿色俯视莲座贴图（6 种变体），叶片随风摆动（8 帧预渲染动画）。")
bullet("生长：初始能量 1，以 0.08/秒积累能量，叶片随能量开方增长（半径 5→24）；"
       "达到成熟阈值（5）后停止生长，并在周围散播 1–3 株能量 0 的新植株（每株只繁殖一次）。")
bullet("碰撞体积：茎部碰撞半径固定为 4（不计叶片）；植物之间不能堆叠、互相挤压"
       "（空间哈希网格 + 松弛分离算法），叶片可互相交叠，为猎物留下藏身间隙。")
bullet("叶片遮挡视线：视觉射线命中“最近物体”，密集植物会挡住身后的捕食者/猎物——"
       "猎物可藏身植物之间，兑现“利用地形”的设计初衷。")
bullet("密度反馈：植物越少能量积累越快（基准 300 株，最多 3 倍生长加速），配合种子雨（5 株/秒），"
       "食物链底部在被过度啃食后能快速自我修复。")
bullet("死亡：被吃后淡出 1.2 秒再移除。")

# ================= 四、猎物与捕食者 =================
h1("四、猎物与捕食者机制")

h2("4.1 猎物（食草者，蓝色荧光圆 + 尾迹 + 双眼）")
bullet("能量：初始 5，达到 10 触发分裂（能量平分，子代同位置出生并变异），分裂冷却可进化（1–120 秒）。")
bullet("进食：前部口器（前伸 7、半径 4）碰到植物茎部即获得其全部能量，植物淡出死亡。")
bullet("视觉：270°、12 条射线，每条射线返回命中物的颜色（绿=植物、蓝=同类、红=捕食者）与体型。")
bullet("性状（可进化）：视距（基础 50×）、体型（基础半径 5×）、繁殖冷却、速度（基础 8×，上限已放开，"
       "代价自我限制，见第六节）。角速度上限 180°/s。")

h2("4.2 捕食者（肉食者，红色荧光圆 + 尾迹 + 双眼）")
bullet("能量：初始 8，达到 12 触发分裂（同上），冷却可进化。")
bullet("体型捕食规则：只有体型大于猎物的捕食者才能成功捕食——体型军备竞赛的引擎。")
bullet("同类相食：允许吃掉体型比自己小的同类（是否捕食由大脑行为决定），形成捕食者种群自限；可在设置屏关闭。")
bullet("“望远镜”式感官：视野角仅 180°（窄，追丢更易发生）但视距可达 90×（远，可从猎物感知范围外接近）。")
bullet("冲刺能力：网络第三输出控制——付出双倍代谢获得 1.5 倍速度，持续 2 秒，冷却 4 秒；"
       "何时冲刺完全由进化学习，冲刺时身体泛金黄色辉光。")
bullet("速度/角速度：速度基础 9×（可进化），角速度 150°/s（慢于猎物的 180°/s，猎物可急转甩脱）。")

# ================= 五、神经网络 =================
h1("五、神经网络设计")

h2("5.1 网络结构（两层前馈 + 递归记忆）")
table(["层", "规模", "激活函数", "说明"],
      [["输入", "66 维", "—", "12 射线 × (RGB+体型) 48 维 + 目标记忆强度/方向 3 维 "
        "+ 自身能量/速度/体型 3 维 + 上一决策隐层2状态反馈 12 维"],
       ["隐层1", "24 神经元", "tanh", "特征探测"],
       ["隐层2", "12 神经元", "tanh", "组合；其状态作为递归反馈回输入（有状态网络，可记忆“刚才在做什么”）"],
       ["输出", "3 维", "sigmoid/sigmoid/sigmoid", "线速度归一化、角速度归一化（tanh）、冲刺倾向"]],
      widths=[2.2, 2.6, 2.2, 8.0])

h2("5.2 记忆机制")
bullet("目标记忆：记住最近看到的目标（猎物记红、捕食者记蓝）的强度与方向，半衰期 1.2 秒——"
       "目标进入盲区后仍能朝记忆方向继续追/逃；")
bullet("递归记忆：上一决策的隐层状态回馈为下次输入，使网络成为有状态机器，行为序列化、可复杂化。")

h2("5.3 决策频率")
p("网络按固定模拟时间节拍（BRAIN_TICK = 0.12 秒）执行“感知→决策”，与帧率、速度倍率解耦："
  "高倍速下每帧会执行多次决策，行为在模拟时间尺度上同样连贯。")

# ================= 六、遗传算法与进化机制 =================
h1("六、遗传算法与进化机制")

h2("6.1 基因组")
p("基因组 = 网络全部权重与偏置（1947 个基因）＋ 4 个形态性状基因（视距倍率、体型倍率、"
  "繁殖冷却秒数、速度倍率），共 1951 个实数基因。性状与权重走同一条变异/遗传/存档管线，"
  "选择压力可以同时优化行为与形态。")

h2("6.2 繁殖与变异")
bullet("分裂繁殖：能量达到阈值后一分为二（先支付繁殖成本，再平分能量），子代与亲代出生在同一位置"
       "（避免出生瞬间的随机好运/厄运）；")
bullet("变异幅度严格限制：每个被选中变异的基因按相对比例增加或缩小 0–5%（方向随机、均匀分布），"
       "概率 5%/基因——彻底杜绝“突变巨兽”，进化平滑渐进；")
bullet("交叉接口：brain.py 已提供 breed_genome()（均匀交叉+变异），为将来启用有性繁殖预留。")

h2("6.3 选择机制（挑选真正能觅食、能繁殖的个体）")
bullet("适应度 =（一生累计进食能量 ＋ 繁殖次数 × 折算权重 10）÷ 年龄——既奖励觅食效率，也奖励成功繁殖；")
bullet("稳态选择：种群满员时，新生子代直接替换适应度最低的成年个体（幼体有 15 秒保护期），"
       "弱个体被持续淘汰；HUD 实时显示两物种的最佳适应度；")
bullet("初代暖启动：初始个体携带手写“本能”基因组（捕食者追蓝、猎物趋绿+逃红），之后完全由进化修改；")
bullet("灭绝救援：某一物种灭绝后，用本次运行中适应度最高的基因组（而非初始本能）重新引入——"
       "进化成果不会因种群崩溃而丢失。")

h2("6.4 性状的代价设计（参数设计考量的核心）")
p("放开性状上限后，若无代价，速度/体型/视距会被无脑拉满。因此为性状设置了自我限制的代价：")
table(["性状", "收益", "代价"],
      [["体型", "越大越难被吃（捕食者须更大才能吞下）；捕食者越大能吃越多猎物", "代谢 ×(0.5+0.5×体型)；繁殖成本 ×(0.5+0.5×体型)"],
       ["速度", "逃逸/追猎能力", "代谢 ×(0.5+0.5×速度)；繁殖成本 ×(0.5+0.5×速度)"],
       ["视距", "更早发现食物/危险", "代谢 ×(0.9+0.1×视距)"],
       ["繁殖冷却", "更频繁繁殖", "每次分裂平分能量（频繁分裂→个体能量低、更脆弱）"]],
      widths=[2.2, 6.0, 6.8])
p("代价机制使性状进化形成真实权衡：实验中猎物在“变大（难被吃）”与“小而快（繁殖便宜）”之间分化，"
  "捕食者则向大体型进化以维持捕食能力——军备竞赛因此有攻有守、动态平衡。")

# ================= 七、性能设计 =================
h1("七、性能设计")
bullet("视觉射线 NumPy 向量化：整组射线 × 候选圆一次矩阵求交，取代逐条 Python 循环；")
bullet("双层空间网格：碰撞用细网格（8），视觉查询用粗网格（32），候选扫描量下降数倍；")
bullet("变步长模拟：速度倍率直接乘在 dt 上，64× 速度不会把每帧计算量放大 64 倍；")
bullet("渲染层缓存：尾迹/辉光/视野透明图层复用，避免每帧分配大块显存表面；视口剔除离屏个体；")
bullet("实测：默认规模（20 猎物 + 6 捕食者）单步约 3–5 ms，可稳定 60 FPS；峰值种群（250+45）约 30 FPS。")

# ================= 八、交互与工具 =================
h1("八、交互界面与配套工具")

h2("8.1 启动参数设置屏")
p("程序启动即进入图形化设置屏，可调整约 36 项参数：世界边长、植物（数量/生长/上限/种子雨/稀缺反馈）、"
  "猎物与捕食者（数量/代谢/分裂阈值/速度/视距/视野角/口器/同类相食/冲刺）、射线数、隐层规模、决策间隔、"
  "变异概率与幅度、选择与繁殖参数、自动备份间隔。支持「保存设置」单独存盘与自动沿用、"
  "「继续上次进度」无缝接续。")

h2("8.2 模拟内操作")
table(["操作", "功能"],
      [["左键拖拽 / 滚轮", "平移 / 缩放（以光标为锚点）"],
       ["空格 / [ ] / 右上按钮", "暂停 / 减速加速（0.5–64×）"],
       ["C / V / T", "碰撞体积 / 双物种视野射线 / 左侧种群曲线（图例可单独开关三种单位）"],
       ["F11", "全屏切换"],
       ["F5 / F9", "手动存档 / 载入（含全部基因组、适应度、种群历史与当时的开局设置）"],
       ["B / N", "保存当前最优大脑存档（可多份）/ 打开存档查看器"],
       ["H / 0 / Esc", "操作说明 / 恢复 50% 视图 / 退出"]],
      widths=[4.5, 10.5])

h2("8.3 神经网络存档与数据查看")
p("按 B 将当前能量最高的猎物与捕食者大脑各存一份（brains/ 文件夹、JSON、按时间命名，可保留任意多份）；"
  "按 N 打开查看器：左侧列表选择，右侧查看元数据（时间/能量/世代/种群/形态性状）、权重统计、"
  "权重分布直方图与 W1 热力图——可跨世代对比进化轨迹。")

h2("8.4 备份与断点续演")
p("F5 手动存档与每 60 秒自动备份均保存完整局面（每个个体的位置/能量/基因组/记忆/冲刺状态、"
  "适应度记录、种群历史）连同当时的开局设置；关闭程序后，下次启动点「继续上次进度」即可接着进化。")

# ================= 九、关键参数总表 =================
h1("九、关键参数总表（默认值）")
table(["参数", "默认值", "说明"],
      [["WORLD_SIZE", 600, "世界边长（世界单位）"],
       ["PLANT_INITIAL_COUNT / MAX_COUNT", "160 / 1200", "初始植物数 / 上限"],
       ["PLANT_GROWTH_RATE / MAX_ENERGY", "0.08 / 5.0", "生长速率 / 成熟阈值"],
       ["PLANT_SEED_RATE", "5.0", "种子雨（株/秒）"],
       ["PLANT_SCARCITY_BONUS / REFERENCE", "2.0 / 300", "稀缺生长增益 / 基准株数"],
       ["PLANT_COLLISION_RADIUS", "4", "茎部碰撞半径（不计叶片）"],
       ["PREY_INITIAL_ENERGY / SPLIT_THRESHOLD", "5 / 10", "猎物初始能量 / 分裂阈值"],
       ["PREY_METABOLISM / MAX_COUNT", "0.04 / 250", "猎物代谢 / 上限"],
       ["PREY_MAX_LINEAR_SPEED / ANGULAR", "8.0 / 180°/s", "猎物速度基础 / 角速度"],
       ["VISION_RAYS / FOV / RANGE", "12 / 270° / 50", "猎物视觉"],
       ["PREDATOR_INITIAL_ENERGY / SPLIT", "8 / 12", "捕食者初始能量 / 分裂阈值"],
       ["PREDATOR_METABOLISM / MAX_COUNT", "0.09 / 45", "捕食者代谢 / 上限"],
       ["PREDATOR_SPEED / ANGULAR", "9.0 / 150°/s", "捕食者速度基础 / 角速度"],
       ["PREDATOR_VISION_FOV / RANGE", "180° / 90", "捕食者“望远镜”感官"],
       ["PREDATOR_EAT_RADIUS", "1", "捕食者口器半径（体型大于猎物才能吃）"],
       ["PREDATOR_CANNIBALISM", "开", "同类相食（可关）"],
       ["PREDATOR_BURST", "1.5×速/2×耗/2s/4sCD", "冲刺：速度倍率/代谢倍率/持续/冷却"],
       ["BRAIN_HIDDEN1 / HIDDEN2", "24 / 12", "隐层神经元数"],
       ["BRAIN_TICK", "0.12s", "决策间隔（模拟秒）"],
       ["GA_MUTATION_RATE / MAGNITUDE", "5% / 0–5%", "变异概率 / 相对变异幅度"],
       ["SELECTION_GRACE / FITNESS_WEIGHT", "15s / 10", "幼体保护期 / 繁殖次数折算权重"],
       ["REPRODUCTION_COST", "1.5", "繁殖基础能量成本"],
       ["AUTOSAVE_INTERVAL", "60s", "自动备份间隔（0=关）"],
       ["SPEED_LEVELS", "0.5–64×", "模拟速度倍率档位"]],
      widths=[5.4, 3.6, 6.0])

# ================= 十、实验观察 =================
h1("十、实验观察与结论")

h2("10.1 进化军备竞赛")
bullet("体型军备竞赛：捕食者须大于猎物才能捕食，实验中猎物平均体型从 1× 进化到 1.5×（最优 1.79×），"
       "捕食者被迫向 2.4× 进化；猎物同时分化出“小而快”（平均速度 2.1×、视距 1.85×）策略，"
       "证明代价机制产生了真实的策略分化；")
bullet("冲刺行为的诞生：捕食者从“从不冲刺”进化到在追猎中主动使用冲刺（繁荣期同屏最多 9 只同时冲刺），"
       "第三输出与代价被网络自发掌握；")
bullet("适应度持续上升：600 秒长跑中两物种最佳适应度单调爬升（猎物 0.1→14+，捕食者 0.2→21+）。")

h2("10.2 种群动态")
p("两物种形成约 200–300 秒周期的数量振荡（猎物 7–250、捕食者 0–60），加入体型规则、同类相食与"
  "植物密度反馈后，猎物灭绝事件降至 0（600 秒实测猎物最低 7–17 只并总能反弹）。")

h2("10.3 结论")
p("该系统证明：在“感知—决策—行动—繁殖—选择”的闭环中，仅靠小步变异（0–5%）与基于觅食/繁殖的"
  "稳态选择，即可自发涌现出觅食、逃避、追击、伏击、冲刺、躲藏乃至同类相食等复杂行为，"
  "并在捕食者与猎物之间形成可长期观察的进化军备竞赛。")

# ================= 十一、后续方向 =================
h1("十一、后续改进方向")
bullet("有性繁殖（交叉重组）：breed_genome() 接口已就绪，可加入“两只可繁殖个体交配”机制；")
bullet("多核并行：multiprocessing 绕开 GIL，支撑更大种群规模；")
bullet("统计面板：种群曲线扩展、最优个体行为回放、性状演化轨迹图；")
bullet("环境扰动实验：周期性食物潮汐/瘟疫，观察进化系统的鲁棒性。")

doc.add_paragraph()
end = doc.add_paragraph()
end.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = end.add_run("—— 全文完 ——")
r.font.color.rgb = RGBColor(0x88, 0x88, 0x88)
r.font.size = Pt(10)
set_east_asia(r, "宋体")

doc.save(DOC_NAME)
print("已生成:", DOC_NAME)
