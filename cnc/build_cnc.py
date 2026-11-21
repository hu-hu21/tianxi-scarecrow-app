# -*- coding: utf-8 -*-
"""生成稻草人驱鸟装置 v1 的 CNC 零件 DXF、PDF 与装配图。"""
import os, csv
import ezdxf
from ezdxf import units
from ezdxf.enums import TextEntityAlignment
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon, FancyArrowPatch
import matplotlib.font_manager as fm

OUT = r"C:\Users\Yang\Tianxi\scarecrow-bird-v1\cnc"
os.makedirs(OUT, exist_ok=True)

FONT_PATH = r"C:\Windows\Fonts\msyh.ttc"
CN = fm.FontProperties(fname=FONT_PATH) if os.path.exists(FONT_PATH) else None

# ---------------------------------------------------------------- helpers
def new_doc():
    doc = ezdxf.new("R2010", setup=True)
    doc.units = units.MM
    doc.header["$INSUNITS"] = 4
    for name, color in [("OUTLINE", 7), ("HOLES", 4), ("BEND", 2), ("NOTES", 3)]:
        if name not in doc.layers:
            doc.layers.add(name, color=color)
    if "BEND" in doc.linetypes:
        doc.layers.get("BEND").dxf.linetype = "DASHED"
    return doc


def add_title(doc, code, name, material, thickness, qty):
    msp = doc.modelspace()
    msp.add_text(code, height=7, dxfattribs={"layer": "NOTES"}).set_placement((0, -14), align=TextEntityAlignment.LEFT)
    msp.add_text(name, height=4, dxfattribs={"layer": "NOTES"}).set_placement((0, -22), align=TextEntityAlignment.LEFT)
    msp.add_text(f"MATERIAL: {material}  THK: {thickness}mm  QTY: {qty}",
                 height=3, dxfattribs={"layer": "NOTES"}).set_placement((0, -28), align=TextEntityAlignment.LEFT)
    msp.add_text("TOLERANCE: +/-0.1mm  DEBURR ALL EDGES  UNITS: mm",
                 height=3, dxfattribs={"layer": "NOTES"}).set_placement((0, -34), align=TextEntityAlignment.LEFT)


def rounded_rect(msp, x, y, w, h, r=8, layer="OUTLINE"):
    # 逆时针绘制，四个 90° 圆角用 bulge=tan(22.5°)=0.4142 表示
    b = 0.41421356
    pts = [
        (x + r, y, 0.0),
        (x + w - r, y, b),
        (x + w, y + r, 0.0),
        (x + w, y + h - r, b),
        (x + w - r, y + h, 0.0),
        (x + r, y + h, b),
        (x, y + h - r, 0.0),
        (x, y + r, b),
    ]
    msp.add_lwpolyline(pts, format="xyb", close=True, dxfattribs={"layer": layer})


def hole(msp, x, y, d, layer="HOLES"):
    msp.add_circle((x, y), d / 2.0, dxfattribs={"layer": layer})


def slot(msp, x, y, w, h, layer="HOLES"):
    msp.add_lwpolyline(
        [(x, y), (x + w, y), (x + w, y + h), (x, y + h)],
        close=True, dxfattribs={"layer": layer}
    )


def bend(msp, x1, y1, x2, y2):
    msp.add_line((x1, y1), (x2, y2), dxfattribs={"layer": "BEND"})


def save(doc, name):
    path = os.path.join(OUT, name)
    doc.saveas(path)
    return path


# ---------------------------------------------------------------- P01 地插
def make_stake():
    doc = new_doc(); msp = doc.modelspace()
    w, h, tip = 60, 520, 80
    msp.add_lwpolyline([(0, 0), (w, 0), (w, h), (w / 2, h + tip), (0, h)],
                       close=True, dxfattribs={"layer": "OUTLINE"})
    for y in (400, 440, 480):
        hole(msp, w / 2, y, 6.6)
    # 加强筋折弯线
    bend(msp, 12, 90, 12, h - 10)
    bend(msp, w - 12, 90, w - 12, h - 10)
    add_title(doc, "P01", "GROUND STAKE", "Q235 STEEL", 3, 1)
    return save(doc, "P01_ground_stake_3mm_steel.dxf")


# ---------------------------------------------------------------- P02 抱箍
def make_clamp():
    doc = new_doc(); msp = doc.modelspace()
    w, h = 80, 45
    rounded_rect(msp, 0, 0, w, h, r=5)
    for x in (12, w - 12):
        for y in (12, h - 12):
            hole(msp, x, y, 5.5)
    # 中间 30.5mm 方管避让
    slot(msp, (w - 30.5) / 2, (h - 30.5) / 2, 30.5, 30.5)
    add_title(doc, "P02", "MAST CLAMP PLATE", "6061-T6 ALU", 3, 2)
    return save(doc, "P02_mast_clamp_3mm_alu.dxf")


# ---------------------------------------------------------------- P03 云台支架
def make_head():
    doc = new_doc(); msp = doc.modelspace()
    w, h = 200, 140
    rounded_rect(msp, 0, 0, w, h, r=12)
    # SG90 舵机本体窗口
    slot(msp, 48, 63, 24, 13)
    # 舵机安装孔（M2，间距 27.5mm）
    hole(msp, 46.25, 88, 2.2)
    hole(msp, 73.75, 88, 2.2)
    # 雷达窗口 30x30
    slot(msp, 135, 85, 30, 30)
    # 喇叭/线束过孔
    hole(msp, 35, 110, 10)
    hole(msp, 175, 30, 10)
    # 灯带固定孔
    for x in (120, 140, 160):
        hole(msp, x, 45, 4.2)
    # 与舵机臂连接孔
    for x in (90, 110):
        hole(msp, x, 20, 4.2)
    add_title(doc, "P03", "HEAD / SERVO BRACKET", "6061-T6 ALU", 3, 1)
    return save(doc, "P03_head_bracket_3mm_alu.dxf")


# ---------------------------------------------------------------- P04 太阳能板支架
def make_solar():
    doc = new_doc(); msp = doc.modelspace()
    w, h = 240, 180
    rounded_rect(msp, 0, 0, w, h, r=8)
    # 组件安装孔 200x150
    for x in (20, 220):
        for y in (15, 165):
            hole(msp, x, y, 6.6)
    # 抱箍安装孔
    for x in (95, 145):
        for y in (60, 120):
            hole(msp, x, y, 6.6)
    # 折弯线
    bend(msp, 0, 60, w, 60)
    bend(msp, 0, 120, w, 120)
    add_title(doc, "P04", "SOLAR PANEL BRACKET (FLAT PATTERN)", "5052-H32 ALU", 2, 1)
    return save(doc, "P04_solar_bracket_2mm_alu.dxf")


# ---------------------------------------------------------------- P05 电控托盘
def make_tray():
    doc = new_doc(); msp = doc.modelspace()
    w, h = 140, 100
    rounded_rect(msp, 0, 0, w, h, r=8)
    # PCB 120x80 安装孔
    for x in (10, 130):
        for y in (10, 90):
            hole(msp, x, y, 3.4)
    # 线缆过孔
    slot(msp, 55, 2, 30, 10)
    slot(msp, 2, 40, 10, 20)
    # 盒体安装孔
    for x in (5, 135):
        for y in (5, 95):
            hole(msp, x, y, 3.4)
    add_title(doc, "P05", "CONTROLLER TRAY", "5052-H32 ALU", 2, 1)
    return save(doc, "P05_controller_tray_2mm_alu.dxf")


# ---------------------------------------------------------------- PDF export
def export_pdf(dxf_path):
    from ezdxf.addons.drawing import matplotlib as mpl_backend
    doc = ezdxf.readfile(dxf_path)
    pdf = dxf_path.replace(".dxf", ".pdf")
    png = dxf_path.replace(".dxf", ".png")
    try:
        mpl_backend.qsave(doc.modelspace(), pdf, bg="#FFFFFF", fg="#111111", dpi=300)
        mpl_backend.qsave(doc.modelspace(), png, bg="#FFFFFF", fg="#111111", dpi=200)
    except Exception as exc:
        print("PDF export failed:", dxf_path, exc)
    return pdf


# ---------------------------------------------------------------- 装配图
def assembly_pdf():
    fig, ax = plt.subplots(figsize=(9, 12))
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_xlim(-160, 360)
    ax.set_ylim(-60, 2050)

    # 地面
    ax.plot([-150, 350], [0, 0], color="#8a6d3b", lw=2)
    ax.add_patch(Rectangle((-150, -25), 500, 25, color="#e8dcc8", zorder=0))

    # 地插
    ax.add_patch(Polygon([(-30, 0), (30, 0), (30, 120), (0, 165), (-30, 120)],
                         closed=True, fill=False, lw=1.6, color="#333"))
    # 立柱
    ax.add_patch(Rectangle((-15, 150), 30, 1200, fill=False, lw=1.6, color="#333"))

    # 云台支架
    ax.add_patch(Rectangle((-100, 1330), 200, 140, fill=False, lw=1.6, color="#1a5c8a"))
    # 喇叭
    ax.add_patch(Circle((0, 1400), 40, fill=False, lw=1.4, color="#1a5c8a"))
    ax.add_patch(Circle((0, 1400), 12, fill=False, lw=1.2, color="#1a5c8a"))
    # 灯带
    ax.add_patch(Rectangle((-90, 1350), 180, 12, color="#b45309", alpha=.35))
    # 雷达窗口
    ax.add_patch(Rectangle((35, 1440), 30, 30, fill=False, lw=1.2, color="#177245"))

    # 太阳能板（正视投影：240 宽，30° 倾角对应 120 高）
    ax.add_patch(Rectangle((-120, 1470), 240, 120, fill=False, lw=1.6, color="#1a5c8a"))
    for x in range(-100, 121, 40):
        ax.plot([x, x + 40], [1470, 1590], color="#1a5c8a", lw=.5, alpha=.6)
    ax.plot([0, 0], [1470, 1450], color="#555", lw=1.4)   # 支架立柱
    ax.plot([-20, 20], [1450, 1450], color="#555", lw=1.4)

    # 电控盒
    ax.add_patch(Rectangle((32, 900), 90, 140, fill=False, lw=1.6, color="#1a5c8a"))
    ax.text(77, 970, "CTRL", fontproperties=CN, ha="center", va="center", fontsize=9, color="#1a5c8a")

    # 标注
    def note(xy, xytext, text):
        ax.annotate(text, xy=xy, xytext=xytext, fontproperties=CN, fontsize=9,
                    arrowprops=dict(arrowstyle="-", lw=.8, color="#555"),
                    bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#bbb", lw=.6))

    note((40, 1600), (-165, 1750), "P04 太阳能板支架 2mm 铝\n240×180，折弯 60/120")
    note((60, 1400), (175, 1320), "P03 云台支架 3mm 铝\n200×140，SG90 舵机")
    note((0, 800), (-155, 780), "30×30×2 铝方管\n长 1200mm")
    note((0, 70), (-150, 240), "P01 地插 3mm 钢\n入土 ≥350mm")
    note((77, 970), (185, 1050), "P05 电控托盘 2mm 铝\nIP65 盒 150×100×60")
    note((0, 150), (150, 300), "P02 抱箍板 3mm 铝 ×2\nM5×25 螺栓 ×4")

    # 尺寸
    ax.annotate("", xy=(-140, 0), xytext=(-140, 1350),
                arrowprops=dict(arrowstyle="<->", lw=1, color="#333"))
    ax.text(-155, 675, "1350", fontproperties=CN, rotation=90, va="center", ha="right", fontsize=9)

    ax.set_title("稻草人驱鸟装置 v1  装配示意图（单位：mm）", fontproperties=CN, fontsize=15, pad=18)
    ax.text(0, -55, "注：示意图非比例严格，孔位与外形以 DXF 为准。", fontproperties=CN, fontsize=8.5, color="#666")

    pdf = os.path.join(OUT, "assembly_drawing.pdf")
    png = os.path.join(OUT, "assembly_drawing.png")
    fig.savefig(pdf, bbox_inches="tight", dpi=300)
    fig.savefig(png, bbox_inches="tight", dpi=160)
    plt.close(fig)
    return pdf


# ---------------------------------------------------------------- BOM / notes
def bom():
    rows = [
        ["P01", "地插", "Q235 钢", "3mm", 1, "激光切割 + 折弯", "热镀锌或喷塑"],
        ["P02", "立柱抱箍板", "6061-T6 铝", "3mm", 2, "激光切割", "阳极氧化"],
        ["P03", "云台支架", "6061-T6 铝", "3mm", 1, "激光切割 / CNC 铣", "阳极氧化"],
        ["P04", "太阳能板支架", "5052-H32 铝", "2mm", 1, "激光切割 + 折弯", "阳极氧化"],
        ["P05", "电控托盘", "5052-H32 铝", "2mm", 1, "激光切割 + 折弯", "阳极氧化"],
        ["M01", "立柱", "6061 铝方管 30×30×2", "-", 1, "锯切 1200mm", "阳极氧化"],
        ["F01", "M5×25 不锈钢螺栓 + 螺母 + 垫片", "304", "-", 4, "标准件", "-"],
        ["F02", "M3×10 不锈钢螺钉", "304", "-", 12, "标准件", "-"],
        ["F03", "M2×6 不锈钢螺钉", "304", "-", 4, "标准件", "-"],
        ["F04", "M6×80 地插螺栓", "304", "-", 3, "标准件", "-"],
        ["S01", "防水盒 150×100×60", "ABS", "-", 1, "成品", "IP65"],
        ["S02", "3W 喇叭", "-", "-", 1, "成品", "防水型"],
        ["S03", "太阳能板 6V/10W", "-", "-", 1, "成品", "配支架"],
    ]
    path = os.path.join(OUT, "cnc_bom.csv")
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["编号", "名称", "材料/规格", "厚度", "数量", "工艺", "表面处理"])
        w.writerows(rows)
    return path


def notes():
    text = """# CNC 加工与装配说明

## 1. 工艺选择
- 铝板：优先激光切割（光纤激光），也可 CNC 铣。切割面粗糙度 Ra3.2，去毛刺、倒 C0.5。
- 钢板：激光切割 + 折弯，热镀锌或户外喷塑，膜厚 ≥ 60μm。
- 折弯半径：等于板厚（3mm 板 R3，2mm 板 R2），折弯线见 DXF 的 BEND 图层。
- 一般公差：±0.1mm；孔位公差 ±0.05mm；角度公差 ±0.5°。

## 2. 零件清单
见 `cnc_bom.csv`。其中 P02 抱箍板需要 2 件，前后夹住 30×30 方管。

## 3. 装配顺序
1. 地插入土 ≥350mm，保证 P01 上端 3 个 Ø6.6 孔露出地面。
2. 方管插入地插上端，用 M6 螺栓穿过 P01 与方管（方管对应位置钻 Ø6.5 通孔）。
3. P02 两片抱箍板夹住方管，M5×25 螺栓对角预紧，再逐步加力。
4. P03 云台支架固定在抱箍前端，SG90 舵机从背面装入 24×13 窗口，M2×6 固定。
5. P05 电控托盘装入 IP65 防水盒，PCB 用 M3 铜柱固定。
6. P04 太阳能板支架按 60/120 折弯线折成 Z 形，固定在方管顶部，面板朝南倾斜约 30°。
7. 喇叭朝下或加防雨罩，线缆全部走防水接头。

## 4. 表面与防护
- 铝件阳极氧化（本色或黑色），膜厚 10-15μm。
- 钢件热镀锌后再喷塑，切口与孔位必须补漆。
- 所有紧固件用 304 不锈钢，螺纹处涂防咬合剂。
- PCB 与电池仓内加放干燥剂，壳体接缝处加 2mm 橡胶垫。

## 5. 检查项
- [ ] 所有孔位与 DXF 一致，孔径通规通过。
- [ ] 折弯方向正确，支架能贴合方管无翘曲。
- [ ] 舵机窗口不干涉舵机本体，舵机臂全行程无碰撞。
- [ ] 太阳能板支架在 10 级风下不松动（建议加安全绳）。
- [ ] 整机重心在地插中心线 ±20mm 内。

## 6. 文件说明
- `P01`~`P05`：零件 DXF，1:1，单位 mm，可直接导入激光切割机。
- `P01`~`P05` PDF：用于打印复核。
- `assembly_drawing.pdf`：装配示意图。
- `cnc_bom.csv`：材料与标准件清单。
"""
    path = os.path.join(OUT, "CNC加工说明.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


if __name__ == "__main__":
    dxfs = [make_stake(), make_clamp(), make_head(), make_solar(), make_tray()]
    for d in dxfs:
        print("DXF", d, "OK")
        print("PDF", export_pdf(d))
    print("ASM", assembly_pdf())
    print("BOM", bom())
    print("NOTES", notes())
