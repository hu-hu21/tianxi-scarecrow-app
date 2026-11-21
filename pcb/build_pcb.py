# -*- coding: utf-8 -*-
"""
稻草人驱鸟控制器 v1 PCB 生成器
- 120 x 80 mm, 2 层, 1.6mm FR4
- 顶层信号, 底层 GND 平面
- 输出: Gerber / Excellon / BOM / 网表 / 原理框图 / 布局图 / DRC 报告
"""
import os, math, heapq, csv, json
from collections import defaultdict
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon, FancyArrowPatch
import matplotlib.font_manager as fm

OUT = r"C:\Users\Yang\Tianxi\scarecrow-bird-v1\pcb"
GERBER = os.path.join(OUT, "gerber")
os.makedirs(GERBER, exist_ok=True)

FONT_PATH = r"C:\Windows\Fonts\msyh.ttc"
CN = fm.FontProperties(fname=FONT_PATH) if os.path.exists(FONT_PATH) else None

BOARD_W, BOARD_H = 120.0, 80.0
GRID = 0.5
NX, NY = int(BOARD_W / GRID), int(BOARD_H / GRID)   # 240 x 160
TRACE_SIG = 0.30
TRACE_PWR = 0.40
CLEARANCE = 0.15
PAD_MARGIN = 0.40


# ------------------------------------------------------------------ data
class Pad:
    def __init__(self, ref, num, x, y, w, h, drill=0.0, shape="rect", net="NC"):
        self.ref, self.num = ref, str(num)
        self.x, self.y, self.w, self.h = x, y, w, h
        self.drill, self.shape, self.net = drill, shape, net
        self.smd = drill <= 0

    def key(self):
        return (self.ref, self.num)


class Comp:
    def __init__(self, ref, value, x, y):
        self.ref, self.value, self.x, self.y = ref, value, x, y
        self.pads = []

    def add(self, pads):
        self.pads.extend(pads)


def rot_pt(dx, dy, rot):
    a = math.radians(rot)
    return dx * math.cos(a) - dy * math.sin(a), dx * math.sin(a) + dy * math.cos(a)


def place(ref, value, x, y, local, rot=0):
    c = Comp(ref, value, x, y)
    for (num, dx, dy, w, h, drill, shape, net) in local:
        if rot in (90, 270):
            w, h = h, w
        px, py = rot_pt(dx, dy, rot)
        c.add([Pad(ref, num, x + px, y + py, w, h, drill, shape, net)])
    return c


# ---------------- footprints (local coordinates) ----------------
def fp_header_1xn(n, nets, vertical=True, pitch=2.54, d=1.7, drill=1.0, start=1):
    out = []
    for i in range(n):
        dx, dy = (0, i * pitch) if vertical else (i * pitch, 0)
        out.append((start + i, dx, dy, d, d, drill, "circle", nets[i]))
    return out


def fp_header_2xn(n, nets_left, nets_right, pitch=2.54, d=1.7, drill=1.0):
    out = []
    for i in range(n):
        out.append((1 + i, 0, -i * pitch, d, d, drill, "circle", nets_left[i]))
        out.append((1 + n + i, pitch, -i * pitch, d, d, drill, "circle", nets_right[i]))
    return out


def fp_0805(net1, net2, horizontal=True):
    if horizontal:
        return [(1, -0.95, 0, 1.0, 1.3, 0, "rect", net1), (2, 0.95, 0, 1.0, 1.3, 0, "rect", net2)]
    return [(1, 0, 0.95, 1.3, 1.0, 0, "rect", net1), (2, 0, -0.95, 1.3, 1.0, 0, "rect", net2)]


def fp_1206(net1, net2):
    return [(1, -1.5, 0, 1.2, 1.8, 0, "rect", net1), (2, 1.5, 0, 1.2, 1.8, 0, "rect", net2)]


def fp_radial(net1, net2, pitch=2.5, d=1.8, drill=0.9):
    return [(1, -pitch / 2, 0, d, d, drill, "circle", net1),
            (2, pitch / 2, 0, d, d, drill, "circle", net2)]


def fp_sma(net1, net2):
    return [(1, -2.0, 0, 1.8, 2.2, 0, "rect", net1), (2, 2.0, 0, 1.8, 2.2, 0, "rect", net2)]


def fp_smb(net1, net2):
    return [(1, -2.2, 0, 2.0, 2.4, 0, "rect", net1), (2, 2.2, 0, 2.0, 2.4, 0, "rect", net2)]


def fp_sot23(gate, source, drain):
    return [(1, -0.95, 0.95, 1.0, 0.6, 0, "rect", gate),
            (2, -0.95, -0.95, 1.0, 0.6, 0, "rect", source),
            (3, 0.95, 0, 1.0, 0.6, 0, "rect", drain)]


def fp_tact(net_a, net_b):
    return [(1, -3.25, 2.25, 1.8, 1.8, 1.0, "circle", net_a),
            (2, -3.25, -2.25, 1.8, 1.8, 1.0, "circle", net_a),
            (3, 3.25, 2.25, 1.8, 1.8, 1.0, "circle", net_b),
            (4, 3.25, -2.25, 1.8, 1.8, 1.0, "circle", net_b)]


def fp_terminal(net1, net2, pitch=5.08, d=2.2, drill=1.3):
    return [(1, 0, 0, d, d, drill, "circle", net1), (2, pitch, 0, d, d, drill, "circle", net2)]


# ------------------------------------------------------------------ placement
comps = []

# 电源链（顶部）
comps.append(place("J5", "12V IN 2P", 6, 72, fp_terminal("12V_IN", "GND")))
comps.append(place("F1", "2A fuse 1206", 16, 74, fp_1206("12V_IN", "12V_FUSED")))
comps.append(place("D1", "SS34 SMA", 22, 74, fp_sma("12V_FUSED", "12V_RAIL")))
comps.append(place("D2", "SMBJ18A SMB", 28, 74, fp_smb("12V_RAIL", "GND")))
comps.append(place("C1", "220uF/25V", 34, 74, fp_radial("12V_RAIL", "GND")))
comps.append(place("U2", "MP1584 module", 40, 74, fp_header_1xn(4, ["12V_RAIL", "GND", "5V", "GND"], vertical=False, start=1)))
comps.append(place("C2", "100nF 0805", 52, 74, fp_0805("5V", "GND")))
comps.append(place("C5", "470uF/10V", 57, 74, fp_radial("5V", "GND")))
comps.append(place("R1", "100k", 32, 47.5, fp_0805("12V_RAIL", "VBAT_SENSE", horizontal=False)))
comps.append(place("R2", "22k", 32, 44.5, fp_0805("VBAT_SENSE", "GND", horizontal=False)))
comps.append(place("LED1", "green", 71, 74, fp_0805("3V3", "LED1_K")))
comps.append(place("R11", "1k", 75, 74, fp_0805("LED1_K", "GND")))
comps.append(place("J6", "SPK 2P", 88, 74, fp_terminal("SPK+", "SPK-")))

# ESP32 2x15
left = ["NC", "LDR_SENSE", "VBAT_SENSE", "RADAR_OUT", "NC", "LED_R_CTRL", "LED_B_CTRL",
        "NC", "DF_RX", "DF_TX", "NC", "NC", "SERVO", "GND", "5V"]
right = ["3V3", "GND", "BTN_TEST", "STATUS_LED", "BTN_MODE", "RADAR_TX", "RADAR_RX",
         "NC", "NC", "NC", "I2C_SDA", "NC", "NC", "I2C_SCL", "NC"]
comps.append(place("J1", "ESP32 DevKit 30P", 18, 50,
                   fp_header_2xn(15, left, right)))

# 右侧接口
comps.append(place("J2", "RADAR 5P", 108, 10,
                   fp_header_1xn(5, ["5V", "GND", "RADAR_TX", "RADAR_RX", "RADAR_OUT"])))
comps.append(place("J3", "DFPLAYER 6P", 108, 23.5,
                   fp_header_1xn(6, ["5V", "DF_RX_MOD", "DF_RX", "SPK+", "SPK-", "GND"])))
comps.append(place("J4", "SERVO 3P", 108, 38,
                   fp_header_1xn(3, ["5V", "GND", "SERVO"])))
comps.append(place("J8", "I2C 4P", 108, 47,
                   fp_header_1xn(4, ["3V3", "GND", "I2C_SDA", "I2C_SCL"])))
comps.append(place("J9", "LDR 2P", 108, 58,
                   fp_header_1xn(2, ["3V3", "LDR_SENSE"])))
comps.append(place("J7", "LED 3P", 108, 64,
                   fp_header_1xn(3, ["12V_RAIL", "LED_R_D", "LED_B_D"])))

# LED 驱动
comps.append(place("Q1", "AO3400A", 98, 66, fp_sot23("Q1_G", "GND", "LED_R_D")))
comps.append(place("Q2", "AO3400A", 98, 60, fp_sot23("Q2_G", "GND", "LED_B_D")))
comps.append(place("R3", "100R", 93, 68, fp_0805("LED_R_CTRL", "Q1_G")))
comps.append(place("R4", "10k", 95, 64.5, fp_0805("Q1_G", "GND", horizontal=False)))
comps.append(place("R5", "100R", 93, 62, fp_0805("LED_B_CTRL", "Q2_G")))
comps.append(place("R6", "10k", 95, 58.5, fp_0805("Q2_G", "GND", horizontal=False)))
comps.append(place("R7", "1k", 100, 33, fp_0805("DF_TX", "DF_RX_MOD")))

# 传感器与按键
comps.append(place("R8", "10k", 102, 57.5, fp_0805("LDR_SENSE", "GND", horizontal=False)))
comps.append(place("R9", "4.7k", 102, 50, fp_0805("3V3", "I2C_SDA", horizontal=False)))
comps.append(place("R10", "4.7k", 102, 54, fp_0805("3V3", "I2C_SCL", horizontal=False)))
comps.append(place("R12", "1k", 78, 66, fp_0805("STATUS_LED", "LED2_A")))
comps.append(place("LED2", "blue", 82, 66, fp_0805("LED2_A", "GND")))
comps.append(place("SW1", "MODE 6mm", 50, 66, fp_tact("BTN_MODE", "GND")))
comps.append(place("SW2", "TEST 6mm", 62, 66, fp_tact("BTN_TEST", "GND")))

all_pads = [p for c in comps for p in c.pads]
pad_by_key = {p.key(): p for p in all_pads}

nets = defaultdict(list)
for p in all_pads:
    if p.net not in ("NC", "GND"):
        nets[p.net].append(p)

# ------------------------------------------------------------------ GND vias for SMD pads
vias = []          # (x, y)
gnd_stubs = []     # (x1,y1,x2,y2)

def free_for_via(x, y, ignore=None):
    if x < 1.2 or x > BOARD_W - 1.2 or y < 1.2 or y > BOARD_H - 1.2:
        return False
    for p in all_pads:
        if p is ignore:
            continue
        if abs(x - p.x) < (p.w / 2 + 0.9) and abs(y - p.y) < (p.h / 2 + 0.9):
            return False
    for vx, vy in vias:
        if abs(x - vx) < 1.2 and abs(y - vy) < 1.2:
            return False
    return True

for p in all_pads:
    if p.net == "GND" and p.smd:
        candidates = [(0, 1.8), (0, -1.8), (1.8, 0), (-1.8, 0),
                      (1.8, 1.8), (-1.8, 1.8), (1.8, -1.8), (-1.8, -1.8),
                      (0, 2.6), (0, -2.6), (2.6, 0), (-2.6, 0)]
        for dx, dy in candidates:
            vx, vy = round((p.x + dx) / 0.5) * 0.5, round((p.y + dy) / 0.5) * 0.5
            if free_for_via(vx, vy, p):
                vias.append((vx, vy))
                gnd_stubs.append((p.x, p.y, vx, vy))
                break

# ------------------------------------------------------------------ router (2 layers)
# layer 0 = top, 1 = bottom
# blocked : pad/footprint keep-out
# hard    : existing copper (traces, vias, GND stubs)
# owner   : cells around a pad belong to that pad's net; only that net may enter
blocked = [set(), set()]
hard = [set(), set()]
hard_core = [set(), set()]
owner = [dict(), dict()]
signal_vias = []

def mark_rect(cx, cy, w, h, margin, layers=(0, 1)):
    x0, x1 = cx - w / 2 - margin, cx + w / 2 + margin
    y0, y1 = cy - h / 2 - margin, cy + h / 2 + margin
    gx0, gx1 = int(math.floor(x0 / GRID)), int(math.ceil(x1 / GRID))
    gy0, gy1 = int(math.floor(y0 / GRID)), int(math.ceil(y1 / GRID))
    for gx in range(gx0, gx1 + 1):
        for gy in range(gy0, gy1 + 1):
            if x0 <= gx * GRID <= x1 and y0 <= gy * GRID <= y1:
                for l in layers:
                    blocked[l].add((gx, gy))

def pad_layers(pad):
    return (0, 1) if pad.drill > 0 else (0,)

for p in all_pads:
    # 通孔焊盘两层都占；SMD 只占顶层
    mark_rect(p.x, p.y, p.w, p.h, PAD_MARGIN, pad_layers(p))
    if p.net not in ("NC", ""):
        x0, x1 = p.x - p.w / 2 - PAD_MARGIN, p.x + p.w / 2 + PAD_MARGIN
        y0, y1 = p.y - p.h / 2 - PAD_MARGIN, p.y + p.h / 2 + PAD_MARGIN
        for gx in range(int(math.floor(x0 / GRID)), int(math.ceil(x1 / GRID)) + 1):
            for gy in range(int(math.floor(y0 / GRID)), int(math.ceil(y1 / GRID)) + 1):
                if x0 <= gx * GRID <= x1 and y0 <= gy * GRID <= y1:
                    for l in pad_layers(p):
                        owner[l][(gx, gy)] = p.net

def snap(v):
    return int(round(v / GRID))

# pre-reserve short escape corridors so dense headers cannot be sealed off
ESCAPE_STEPS = 12
for p in all_pads:
    if p.net in ("NC", "") or p.drill <= 0:
        continue
    if p.x <= 19.2:
        dirs = [(-1, 0)]
    elif p.x <= 23.0:
        dirs = [(1, 0)]
    elif p.x >= 104.0:
        dirs = [(-1, 0)]
    else:
        def score(d):
            s = 0
            for k in range(1, ESCAPE_STEPS + 1):
                c = (snap(p.x) + d[0] * k, snap(p.y) + d[1] * k)
                if c in blocked[0] or c in hard[0]:
                    s -= 1
            return s
        dirs = [max([(0, 1), (0, -1), (1, 0), (-1, 0)], key=score)]
    for d in dirs:
        for k in range(1, ESCAPE_STEPS + 1):
            c = (snap(p.x) + d[0] * k, snap(p.y) + d[1] * k)
            if c[0] < 1 or c[0] > NX - 1 or c[1] < 1 or c[1] > NY - 1:
                break
            ok = True
            for l in pad_layers(p):
                o = owner[l].get(c)
                if o is not None and o != p.net:
                    ok = False
                elif o is None and c in blocked[l]:
                    ok = False
            if not ok:
                break
            for l in pad_layers(p):
                owner[l][c] = p.net
                blocked[l].add(c)

for (vx, vy) in vias:
    mark_rect(vx, vy, 0.6, 0.6, PAD_MARGIN, (0, 1))
    for l in (0, 1):
        hard[l].add((int(round(vx / GRID)), int(round(vy / GRID))))

for (x1, y1, x2, y2) in gnd_stubs:
    steps = int(max(abs(x2 - x1), abs(y2 - y1)) / (GRID / 2)) + 1
    for i in range(steps + 1):
        t = i / max(steps, 1)
        cx, cy = x1 + (x2 - x1) * t, y1 + (y2 - y1) * t
        for gx in range(int(math.floor((cx - 0.65) / GRID)), int(math.ceil((cx + 0.65) / GRID)) + 1):
            for gy in range(int(math.floor((cy - 0.65) / GRID)), int(math.ceil((cy + 0.65) / GRID)) + 1):
                if abs(cx - gx * GRID) <= 0.65 and abs(cy - gy * GRID) <= 0.65:
                    hard[0].add((gx, gy))

for l in (0, 1):
    for gx in range(NX + 1):
        for gy in range(NY + 1):
            if gx < 1 or gx > NX - 1 or gy < 1 or gy > NY - 1:
                blocked[l].add((gx, gy))

def astar_2l(start, goal, net, goal_layers, relaxed=False):
    sx, sy = start
    gx0, gy0 = goal
    openq = [(0.0, 0, (sx, sy, 0), None)]
    came = {}
    gscore = {(sx, sy, 0): 0.0}
    counter = 1
    dirs = [(1, 0, 10), (-1, 0, 10), (0, 1, 10), (0, -1, 10),
            (1, 1, 14), (1, -1, 14), (-1, 1, 14), (-1, -1, 14)]
    expansions = 0

    copper = hard_core if relaxed else hard

    def enterable(cell, l):
        if cell in copper[l]:
            return False
        if owner[l].get(cell) == net:
            return True
        return cell not in blocked[l]

    while openq:
        f, _, cur, parent = heapq.heappop(openq)
        if cur in came:
            continue
        came[cur] = parent
        cx, cy, cl = cur
        if (cx, cy) == goal and cl in goal_layers:
            path = [cur]
            while came[path[-1]] is not None:
                path.append(came[path[-1]])
            return list(reversed(path))
        expansions += 1
        if expansions > 500000:
            return None

        for dx, dy, cost in dirs:
            nx, ny = cx + dx, cy + dy
            if nx < 0 or ny < 0 or nx > NX or ny > NY:
                continue
            if not enterable((nx, ny), cl):
                continue
            if dx and dy:
                # 禁止斜穿：两个拐角格都必须可通行
                if not enterable((cx + dx, cy), cl) or not enterable((cx, cy + dy), cl):
                    continue
            nstate = (nx, ny, cl)
            g = gscore[cur] + cost
            if nstate in gscore and gscore[nstate] <= g:
                continue
            gscore[nstate] = g
            h = 10 * max(abs(nx - gx0), abs(ny - gy0)) + 4 * min(abs(nx - gx0), abs(ny - gy0))
            heapq.heappush(openq, (g + h, counter, nstate, cur))
            counter += 1

        # via to the other layer
        ol = 1 - cl
        if enterable((cx, cy), ol):
            nstate = (cx, cy, ol)
            g = gscore[cur] + 25
            if nstate not in gscore or gscore[nstate] > g:
                gscore[nstate] = g
                h = 10 * max(abs(cx - gx0), abs(cy - gy0)) + 4 * min(abs(cx - gx0), abs(cy - gy0))
                heapq.heappush(openq, (g + h, counter, nstate, cur))
                counter += 1
    return None

def simplify(path):
    if len(path) <= 2:
        return path
    out = [path[0]]
    for i in range(1, len(path) - 1):
        x0, y0 = out[-1][:2]
        x1, y1 = path[i][:2]
        x2, y2 = path[i + 1][:2]
        if (x1 - x0, y1 - y0) != (x2 - x1, y2 - y1):
            out.append(path[i])
    out.append(path[-1])
    return out

def mst_edges(pads):
    pts = [(p.x, p.y, p) for p in pads]
    if len(pts) < 2:
        return [], 0
    in_tree = [0]
    rest = list(range(1, len(pts)))
    edges = []
    total = 0
    while rest:
        best = None
        for i in in_tree:
            for j in rest:
                d = abs(pts[i][0] - pts[j][0]) + abs(pts[i][1] - pts[j][1])
                if best is None or d < best[0]:
                    best = (d, i, j)
        total += best[0]
        edges.append((pts[best[1]][2], pts[best[2]][2]))
        in_tree.append(best[2])
        rest.remove(best[2])
    return edges, total

def route_net(net, pads, width):
    edges, _ = mst_edges(pads)
    segs = []
    fails = []
    for p1, p2 in edges:
        goal_layers = (0,) if p2.smd else (0, 1)
        path = astar_2l((snap(p1.x), snap(p1.y)), (snap(p2.x), snap(p2.y)), net, goal_layers)
        if not path:
            path = astar_2l((snap(p1.x), snap(p1.y)), (snap(p2.x), snap(p2.y)), net, goal_layers, relaxed=True)
        if not path:
            fails.append((p1.key(), p2.key()))
            continue
        full_path = path
        path = simplify(path)
        # split into same-layer runs and record vias
        run = [path[0]]
        for prev, cur in zip(path[:-1], path[1:]):
            if prev[2] != cur[2]:
                if len(run) >= 2:
                    for a, b in zip(run[:-1], run[1:]):
                        segs.append((run[0][2], a[0] * GRID, a[1] * GRID, b[0] * GRID, b[1] * GRID))
                signal_vias.append((cur[0] * GRID, cur[1] * GRID))
                hard[0].add((cur[0], cur[1]))
                hard[1].add((cur[0], cur[1]))
                run = [cur]
            else:
                run.append(cur)
        if len(run) >= 2:
            for a, b in zip(run[:-1], run[1:]):
                segs.append((run[0][2], a[0] * GRID, a[1] * GRID, b[0] * GRID, b[1] * GRID))
        # mark copper: self + orthogonal neighbours keep 0.5mm centre spacing
        for (cx, cy, cl) in full_path:
            if owner[cl].get((cx, cy)) != net:
                hard[cl].add((cx, cy))
                hard_core[cl].add((cx, cy))
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                c = (cx + dx, cy + dy)
                if owner[cl].get(c) != net:
                    hard[cl].add(c)
    return segs, fails

power_nets = {"12V_IN", "12V_FUSED", "12V_RAIL", "5V", "3V3"}
routes = {}
failures = []

def net_len(n):
    return mst_edges(nets[n])[1]

net_order = sorted(nets.keys(), key=lambda n: (n not in power_nets, -net_len(n)))

BASE_BLOCKED = [set(blocked[0]), set(blocked[1])]

def run_routing(order):
    for l in (0, 1):
        blocked[l] = set(BASE_BLOCKED[l])
        hard[l] = set()
        hard_core[l] = set()
    signal_vias.clear()
    routes.clear()
    failures.clear()
    for n in order:
        segs, fails = route_net(n, nets[n], TRACE_PWR if n in power_nets else TRACE_SIG)
        routes[n] = segs
        for f in fails:
            failures.append((n, f[0], f[1]))
    return list(failures)

for attempt in range(8):
    bad = run_routing(net_order)
    if not bad:
        break
    stuck = bad[0][0]
    print("reroute with priority:", stuck, "(attempt %d)" % (attempt + 1))
    net_order = [stuck] + [n for n in net_order if n != stuck]

# ------------------------------------------------------------------ Gerber writer
def fmt(v):
    return str(int(round(v * 1000000)))

class ApSet:
    def __init__(self):
        self.map = {}
        self.items = []
        self.next = 10
    def get(self, shape, *params):
        k = (shape,) + params
        if k not in self.map:
            self.map[k] = "D%d" % self.next
            self.items.append((self.map[k], shape, params))
            self.next += 1
        return self.map[k]

def write_gerber(path, lines, flashes, regions=None, clear_flashes=None,
                 clear_regions=None, clear_lines=None, title=""):
    aps = ApSet()
    # pre-register apertures
    for (x1, y1, x2, y2, w) in lines:
        aps.get("C", w)
    for (x, y, shape, w, h) in flashes:
        if shape == "C":
            aps.get("C", w)
        else:
            aps.get("R", w, h)
    if clear_flashes:
        for item in clear_flashes:
            if len(item) == 3:
                aps.get("C", item[2])
            else:
                _, _, shape, w, h = item
                aps.get("C", w) if shape == "C" else aps.get("R", w, h)
    if clear_lines:
        for (x1, y1, x2, y2, w) in clear_lines:
            aps.get("C", w)

    out = []
    out.append("G04 %s*" % title)
    out.append("%FSLAX46Y46*%")
    out.append("%MOMM*%")
    for code, shape, params in aps.items:
        if shape == "C":
            out.append("%%ADD%s%s,%.6f*%%" % (code[1:], shape, params[0]))
        else:
            out.append("%%ADD%s%s,%.6fX%.6f*%%" % (code[1:], shape, params[0], params[1]))
    out.append("%LPD*%")

    if regions:
        for pts in regions:
            out.append("G36*")
            out.append("X%sY%sD02*" % (fmt(pts[0][0]), fmt(pts[0][1])))
            for (x, y) in pts[1:]:
                out.append("X%sY%sD01*" % (fmt(x), fmt(y)))
            out.append("X%sY%sD01*" % (fmt(pts[0][0]), fmt(pts[0][1])))
            out.append("G37*")

    if clear_regions or clear_flashes or clear_lines:
        out.append("%LPC*%")
        for pts in (clear_regions or []):
            out.append("G36*")
            out.append("X%sY%sD02*" % (fmt(pts[0][0]), fmt(pts[0][1])))
            for (x, y) in pts[1:]:
                out.append("X%sY%sD01*" % (fmt(x), fmt(y)))
            out.append("X%sY%sD01*" % (fmt(pts[0][0]), fmt(pts[0][1])))
            out.append("G37*")
        for item in (clear_flashes or []):
            if len(item) == 3:
                x, y, d = item
                code = aps.get("C", d)
            else:
                x, y, shape, w, h = item
                code = aps.get("C", w) if shape == "C" else aps.get("R", w, h)
            out.append(code + "*")
            out.append("X%sY%sD03*" % (fmt(x), fmt(y)))
        for (x1, y1, x2, y2, w) in (clear_lines or []):
            code = aps.get("C", w)
            out.append(code + "*")
            out.append("X%sY%sD02*" % (fmt(x1), fmt(y1)))
            out.append("X%sY%sD01*" % (fmt(x2), fmt(y2)))
        out.append("%LPD*%")

    for (x1, y1, x2, y2, w) in lines:
        code = aps.get("C", w)
        out.append(code + "*")
        out.append("X%sY%sD02*" % (fmt(x1), fmt(y1)))
        out.append("X%sY%sD01*" % (fmt(x2), fmt(y2)))

    for (x, y, shape, w, h) in flashes:
        code = aps.get("C", w) if shape == "C" else aps.get("R", w, h)
        out.append(code + "*")
        out.append("X%sY%sD03*" % (fmt(x), fmt(y)))

    out.append("M02*")
    with open(path, "w", encoding="ascii") as f:
        f.write("\n".join(out) + "\n")

# top / bottom copper
top_lines = []
bottom_lines = []
for n, segs in routes.items():
    w = TRACE_PWR if n in power_nets else TRACE_SIG
    for (lay, x1, y1, x2, y2) in segs:
        (top_lines if lay == 0 else bottom_lines).append((x1, y1, x2, y2, w))
for (x1, y1, x2, y2) in gnd_stubs:
    top_lines.append((x1, y1, x2, y2, TRACE_PWR))

top_flashes = []
mask_flashes = []
for p in all_pads:
    if p.shape == "circle":
        top_flashes.append((p.x, p.y, "C", p.w, p.w))
    else:
        top_flashes.append((p.x, p.y, "R", p.w, p.h))
    mask_flashes.append((p.x, p.y, "C" if p.shape == "circle" else "R", p.w + 0.1, p.h + 0.1))
for (vx, vy) in vias:
    top_flashes.append((vx, vy, "C", 0.6, 0.6))
for (vx, vy) in signal_vias:
    top_flashes.append((vx, vy, "C", 0.6, 0.6))

# bottom plane: full board minus non-GND THT pads / bottom traces / signal vias
plane = [(0.3, 0.3), (BOARD_W - 0.3, 0.3), (BOARD_W - 0.3, BOARD_H - 0.3), (0.3, BOARD_H - 0.3)]
clear = []
for p in all_pads:
    if p.drill <= 0:
        continue
    if p.net == "GND":
        continue
    if p.shape == "circle":
        clear.append((p.x, p.y, "C", p.w + 0.6, p.w + 0.6))
    else:
        clear.append((p.x, p.y, "R", p.w + 0.6, p.h + 0.6))
for (vx, vy) in signal_vias:
    clear.append((vx, vy, "C", 1.2, 1.2))

clear_lines = []
for (x1, y1, x2, y2, w) in bottom_lines:
    clear_lines.append((x1, y1, x2, y2, w + 0.6))

bottom_flashes = []
for p in all_pads:
    if p.drill <= 0:
        continue
    if p.shape == "circle":
        bottom_flashes.append((p.x, p.y, "C", p.w, p.w))
    else:
        bottom_flashes.append((p.x, p.y, "R", p.w, p.h))
for (vx, vy) in signal_vias:
    bottom_flashes.append((vx, vy, "C", 0.6, 0.6))

edge_lines = [
    (0, 0, BOARD_W, 0, 0.15), (BOARD_W, 0, BOARD_W, BOARD_H, 0.15),
    (BOARD_W, BOARD_H, 0, BOARD_H, 0.15), (0, BOARD_H, 0, 0, 0.15)
]

write_gerber(os.path.join(GERBER, "scarecrow-F_Cu.gbr"), top_lines, top_flashes, title="F.Cu")
write_gerber(os.path.join(GERBER, "scarecrow-B_Cu.gbr"), bottom_lines, bottom_flashes,
             regions=[plane], clear_flashes=clear, clear_lines=clear_lines,
             title="B.Cu / GND plane")
write_gerber(os.path.join(GERBER, "scarecrow-F_Mask.gbr"), [], mask_flashes, title="F.Mask")
write_gerber(os.path.join(GERBER, "scarecrow-Edge_Cuts.gbr"), edge_lines, [], title="Edge.Cuts")

# silkscreen (outlines + refs). Text font 5x7.
FONT5 = {
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "C": ["01110", "10001", "10000", "10000", "10000", "10001", "01110"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    "G": ["01110", "10001", "10000", "10111", "10001", "10001", "01111"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
    "J": ["00111", "00010", "00010", "00010", "00010", "10010", "01100"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "Q": ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
    "W": ["10001", "10001", "10001", "10101", "10101", "11011", "10001"],
    "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
    "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    "Z": ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
    "3": ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
    "6": ["00110", "01000", "10000", "11110", "10001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00010", "01100"],
    "-": ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
    "+": ["00000", "00100", "00100", "11111", "00100", "00100", "00000"],
    ".": ["00000", "00000", "00000", "00000", "00000", "00110", "00110"],
    "/": ["00001", "00010", "00010", "00100", "01000", "01000", "10000"],
    " ": ["00000"] * 7,
}

def text_lines(x, y, s, h=1.2):
    out = []
    cw = h * 5 / 7.0
    cx = x
    for ch in s.upper():
        rows = FONT5.get(ch, FONT5[" "])
        for r, row in enumerate(rows):
            col = 0
            while col < len(row):
                if row[col] == "1":
                    start = col
                    while col < len(row) and row[col] == "1":
                        col += 1
                    out.append((cx + start * cw / 5, y + (6 - r) * h / 7,
                                cx + (col - 1) * cw / 5, y + (6 - r) * h / 7, 0.12))
                else:
                    col += 1
        cx += cw * 1.25
    return out

silk = []
for c in comps:
    xs = [p.x for p in c.pads]; ys = [p.y for p in c.pads]
    x0, x1 = min(xs) - 1.2, max(xs) + 1.2
    y0, y1 = min(ys) - 1.2, max(ys) + 1.2
    silk += [(x0, y0, x1, y0, 0.15), (x1, y0, x1, y1, 0.15),
             (x1, y1, x0, y1, 0.15), (x0, y1, x0, y0, 0.15)]
    silk += text_lines(x0, y1 + 0.4, c.ref, 1.0)

# connector labels
labels = [
    ("12V", 5, 69), ("5V", 40, 70.8), ("RADAR", 108, 22.0),
    ("DFPLAYER", 108, 38.0), ("SERVO", 108, 45.0), ("I2C", 108, 56.2),
    ("LDR", 108, 62.8), ("LED", 108, 71.5), ("SPK", 88, 71.2),
    ("MODE", 46, 61.5), ("TEST", 58, 61.5), ("USB", 18, 12.0),
]
for s, x, y in labels:
    silk += text_lines(x, y, s, 1.0)
silk += text_lines(3, 3, "SCARECROW V1", 1.4)

write_gerber(os.path.join(GERBER, "scarecrow-F_Silkscreen.gbr"), silk, [], title="F.Silkscreen")

# drill
drills = defaultdict(list)
for p in all_pads:
    if p.drill > 0:
        drills[p.drill].append((p.x, p.y))
for (vx, vy) in vias:
    drills[0.3].append((vx, vy))
for (vx, vy) in signal_vias:
    drills[0.3].append((vx, vy))

def write_drill(path):
    tools = sorted(drills.keys())
    lines = ["M48", ";SCARECROW V1", "METRIC,TZ"]
    for i, d in enumerate(tools, 1):
        lines.append("T%dC%.3f" % (i, d))
    lines += ["%", "G90"]
    for i, d in enumerate(tools, 1):
        lines.append("T%d" % i)
        for (x, y) in drills[d]:
            lines.append("X%.3fY%.3f" % (x, y))
    lines += ["M30"]
    with open(path, "w", encoding="ascii") as f:
        f.write("\n".join(lines) + "\n")

write_drill(os.path.join(GERBER, "scarecrow.drl"))

# ------------------------------------------------------------------ BOM / netlist
bom_rows = []
for c in comps:
    bom_rows.append([c.ref, c.value, len(c.pads), "PLACE"])
with open(os.path.join(OUT, "pcb_bom.csv"), "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["位号", "规格", "焊点数", "备注"])
    w.writerows(bom_rows)
    w.writerow([])
    w.writerow(["J1", "2x15P 2.54 母排针", 30, "ESP32 DevKit 30Pin"])
    w.writerow(["J2", "1x5P 2.54", 5, "WT41 雷达（含 OUT）"])
    w.writerow(["J3", "1x6P 2.54", 6, "DFPlayer Mini"])
    w.writerow(["J4", "1x3P 2.54", 3, "SG90 舵机"])
    w.writerow(["J5/J6", "2P 5.08 螺钉端子", 2, "12V 输入 / 喇叭"])
    w.writerow(["J7", "1x3P 2.54", 3, "12V 红/蓝灯带"])
    w.writerow(["J8", "1x4P 2.54", 4, "I2C 扩展"])
    w.writerow(["J9", "1x2P 2.54", 2, "光敏电阻"])

with open(os.path.join(OUT, "netlist.csv"), "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["网络", "位号", "引脚", "X(mm)", "Y(mm)"])
    for p in all_pads:
        if p.net != "NC":
            w.writerow([p.net, p.ref, p.num, "%.2f" % p.x, "%.2f" % p.y])

# ------------------------------------------------------------------ geometry checks
def _pt_seg(p, a, b):
    ax, ay = a; bx, by = b
    dx, dy = bx - ax, by - ay
    l2 = dx * dx + dy * dy
    if l2 == 0:
        return math.hypot(p[0] - ax, p[1] - ay)
    t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / l2))
    return math.hypot(p[0] - (ax + t * dx), p[1] - (ay + t * dy))

def _orient(p, q, r):
    return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

def seg_seg_dist(a1, a2, b1, b2):
    o1, o2 = _orient(a1, a2, b1), _orient(a1, a2, b2)
    o3, o4 = _orient(b1, b2, a1), _orient(b1, b2, a2)
    if ((o1 > 0) != (o2 > 0)) and ((o3 > 0) != (o4 > 0)):
        return 0.0
    return min(_pt_seg(a1, b1, b2), _pt_seg(a2, b1, b2),
              _pt_seg(b1, a1, a2), _pt_seg(b2, a1, a2))

seg_net = []
for n, segs in routes.items():
    w = TRACE_PWR if n in power_nets else TRACE_SIG
    for (lay, x1, y1, x2, y2) in segs:
        seg_net.append((n, lay, w, (x1, y1), (x2, y2)))
for (x1, y1, x2, y2) in gnd_stubs:
    seg_net.append(("GND", 0, TRACE_PWR, (x1, y1), (x2, y2)))

shorts = []
for i in range(len(seg_net)):
    n1, l1, w1, a1, b1 = seg_net[i]
    bb1 = (min(a1[0], b1[0]), min(a1[1], b1[1]), max(a1[0], b1[0]), max(a1[1], b1[1]))
    need = (w1 + 0.4) / 2 + CLEARANCE + 0.5
    for j in range(i + 1, len(seg_net)):
        n2, l2, w2, a2, b2 = seg_net[j]
        if l1 != l2 or n1 == n2:
            continue
        bb2 = (min(a2[0], b2[0]), min(a2[1], b2[1]), max(a2[0], b2[0]), max(a2[1], b2[1]))
        if bb1[0] - need > bb2[2] or bb2[0] - need > bb1[2] or \
           bb1[1] - need > bb2[3] or bb2[1] - need > bb1[3]:
            continue
        d = seg_seg_dist(a1, b1, a2, b2)
        if d < (w1 + w2) / 2 + CLEARANCE - 0.02:
            shorts.append((n1, n2, round(d, 3), a1, b1, a2, b2))

single_pad_nets = [n for n, ps in nets.items() if len(ps) < 2]

# ------------------------------------------------------------------ DRC report
report = []
report.append("# PCB 设计检查报告（脚本级）\n")
report.append("- 板框：%.1f × %.1f mm，2 层，1.6mm FR4，1oz 铜" % (BOARD_W, BOARD_H))
report.append("- 最小走线：信号 %.2f mm，电源 %.2f mm" % (TRACE_SIG, TRACE_PWR))
report.append("- 设计间距：%.2f mm（网格 0.5mm 近似）" % CLEARANCE)
report.append("- 过孔：0.6/0.3 mm，GND 过孔 + 信号换层过孔")
report.append("- 焊盘：THT 1.7/1.0 mm，端子 2.2/1.3 mm\n")
report.append("## 布线结果\n")
report.append("| 网络 | 线段数 | 状态 |")
report.append("|---|---|---|")
for n in net_order:
    report.append("| %s | %d | %s |" % (n, len(routes[n]), "OK" if not any(f[0] == n for f in failures) else "FAIL"))
report.append("")
report.append("- 顶/底层走线：%d / %d 段" % (len(top_lines), len(bottom_lines)))
report.append("- GND 过孔 %d 个，信号过孔 %d 个" % (len(vias), len(signal_vias)))
report.append("")
if failures:
    report.append("## 未完成连接\n")
    for f in failures:
        report.append("- %s: %s → %s" % f)
else:
    report.append("## 未完成连接\n\n无。所有信号网络均由 MST 边连接成功。\n")
report.append("## 同层间距检查\n")
report.append("- 比较线段总数：%d" % len(seg_net))
report.append("- 同层异网间距违规：%d 处" % len(shorts))
for s in shorts[:20]:
    report.append("  - %s ↔ %s，间距 %.3f mm，段 %s-%s / %s-%s" % s)
report.append("- 单焊盘网络：%s\n" % (", ".join(single_pad_nets) if single_pad_nets else "无"))
report.append("## 必须人工复核的项\n")
report.append("1. 本板由脚本生成，未在 KiCad/Altium 中运行官方 DRC；打样前请导入 EDA 复核间距、焊盘与丝印。")
report.append("2. 电源路径按 1A 设计；如喇叭长时间满功率，请把 5V 走线加宽到 0.8mm 或开窗加锡。")
report.append("3. J3 已按 DFPlayer Mini 实物引脚排列：VCC / RX / TX / SPK1 / SPK2 / GND；RX 串 1k（R7）接 GPIO27，TX 接 GPIO26。")
report.append("4. 底层为整板 GND 平面：非 GND 通孔按焊盘外形 +0.6mm 避让，底层走线两侧留 0.3mm 隔离槽，信号过孔 +0.6mm 避让；SMD 地焊盘通过 0.3mm 过孔下地。")
report.append("5. 12V 输入建议外加自恢复保险丝与 TVS；本板已留 F1/D2 位置。")
with open(os.path.join(OUT, "DRC报告.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(report) + "\n")

# ------------------------------------------------------------------ layout PDF/PNG
fig, ax = plt.subplots(figsize=(11, 7.6))
ax.set_aspect("equal")
ax.set_xlim(-8, BOARD_W + 8)
ax.set_ylim(-8, BOARD_H + 8)
ax.axis("off")
ax.add_patch(Rectangle((0, 0), BOARD_W, BOARD_H, fill=False, lw=1.8, ec="#111"))
ax.add_patch(Rectangle((0.4, 0.4), BOARD_W - 0.8, BOARD_H - 0.8, fill=False, lw=.5, ec="#888", ls="--"))

for (x1, y1, x2, y2) in gnd_stubs:
    ax.plot([x1, x2], [y1, y2], color="#c0392b", lw=1.2, solid_capstyle="round")
for n, segs in routes.items():
    w = 2.2 if n in power_nets else 1.4
    for (lay, x1, y1, x2, y2) in segs:
        color = "#c0392b" if lay == 0 else "#1f6feb"
        ax.plot([x1, x2], [y1, y2], color=color, lw=w, solid_capstyle="round",
                alpha=.85 if lay == 0 else .55)

for p in all_pads:
    if p.shape == "circle":
        ax.add_patch(Circle((p.x, p.y), p.w / 2, fc="#d4a017", ec="#7a5c00", lw=.5, zorder=3))
    else:
        ax.add_patch(Rectangle((p.x - p.w / 2, p.y - p.h / 2), p.w, p.h,
                               fc="#d4a017", ec="#7a5c00", lw=.5, zorder=3))
for (vx, vy) in vias:
    ax.add_patch(Circle((vx, vy), 0.3, fc="#2e8b57", ec="#14532d", lw=.4, zorder=4))
for (vx, vy) in signal_vias:
    ax.add_patch(Circle((vx, vy), 0.3, fc="#e67e22", ec="#8a4b08", lw=.4, zorder=4))

for c in comps:
    xs = [p.x for p in c.pads]; ys = [p.y for p in c.pads]
    ax.text(min(xs), max(ys) + 1.0, c.ref, fontproperties=CN, fontsize=7, color="#333", zorder=5)

ax.annotate("", xy=(0, -4), xytext=(BOARD_W, -4), arrowprops=dict(arrowstyle="<->", lw=.8))
ax.text(BOARD_W / 2, -6.5, "120 mm", fontproperties=CN, ha="center", fontsize=8)
ax.annotate("", xy=(-4, 0), xytext=(-4, BOARD_H), arrowprops=dict(arrowstyle="<->", lw=.8))
ax.text(-6.5, BOARD_H / 2, "80 mm", fontproperties=CN, rotation=90, va="center", ha="right", fontsize=8)

ax.set_title("稻草人驱鸟控制器 v1  PCB 布局（顶层/底层）", fontproperties=CN, fontsize=15, pad=14)
ax.text(0, BOARD_H + 4.5, "红=顶层走线　蓝=底层走线　金=焊盘　绿=GND 过孔　橙=信号过孔　底层为 GND 平面",
        fontproperties=CN, fontsize=8.5, color="#555")
pdf = os.path.join(OUT, "pcb_layout.pdf")
png = os.path.join(OUT, "pcb_layout.png")
fig.savefig(pdf, bbox_inches="tight", dpi=300)
fig.savefig(png, bbox_inches="tight", dpi=160)
plt.close(fig)

# ------------------------------------------------------------------ schematic PDF
from matplotlib.backends.backend_pdf import PdfPages

def box(ax, x, y, w, h, title, sub=""):
    ax.add_patch(Rectangle((x, y), w, h, fill=True, fc="#f7fbff", ec="#1a5c8a", lw=1.2))
    ax.text(x + w / 2, y + h - 3, title, fontproperties=CN, ha="center", va="top", fontsize=9, weight="bold")
    if sub:
        ax.text(x + w / 2, y + h / 2 - 1, sub, fontproperties=CN, ha="center", va="center", fontsize=7.5, color="#555")

def arrow(ax, p1, p2, text="", color="#333"):
    ax.annotate("", xy=p2, xytext=p1, arrowprops=dict(arrowstyle="-|>", lw=1.0, color=color))
    if text:
        ax.text((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2 + 1.5, text,
                fontproperties=CN, fontsize=7, ha="center", color="#333")

sch = os.path.join(OUT, "schematic.pdf")
with PdfPages(sch) as pdf:
    fig, ax = plt.subplots(figsize=(11.7, 8.3))
    ax.set_xlim(0, 160); ax.set_ylim(0, 110); ax.axis("off")

    ax.text(4, 104, "稻草人驱鸟控制器 v1  系统原理框图", fontproperties=CN, fontsize=16, weight="bold")
    ax.text(4, 99, "ESP32 + WT41 微波雷达 + DFPlayer + 声光执行", fontproperties=CN, fontsize=9, color="#555")

    box(ax, 4, 62, 24, 26, "12V 输入", "J5 / 太阳能控制器\n或 12V 电池")
    box(ax, 34, 62, 24, 26, "保护", "F1 2A\nD1 SS34 防反接\nD2 SMBJ18A")
    box(ax, 64, 62, 26, 26, "DC-DC", "MP1584 模块\n12V → 5V / 3A")
    box(ax, 96, 62, 22, 26, "5V 负载", "雷达 / DFPlayer\n舵机 / 喇叭")
    box(ax, 124, 62, 30, 26, "3.3V", "ESP32 DevKit\n3V3 输出")

    arrow(ax, (28, 75), (34, 75), "12V")
    arrow(ax, (58, 75), (64, 75), "12V")
    arrow(ax, (90, 75), (96, 75), "5V")
    arrow(ax, (118, 75), (124, 75), "5V→3V3")

    box(ax, 34, 24, 34, 26, "ESP32 DevKit", "GPIO34 雷达\nGPIO16/17 雷达串口\nGPIO26/27 DFPlayer\nGPIO13 舵机")
    box(ax, 4, 18, 24, 20, "WT41 雷达", "1-30m / 90°\nUART 5V")
    box(ax, 76, 36, 26, 22, "DFPlayer Mini", "TF 卡音源\n3W 功放")
    box(ax, 76, 10, 26, 18, "喇叭", "8Ω 3W\n防水")
    box(ax, 108, 36, 20, 22, "舵机", "SG90 / MG90\n云台扫描")
    box(ax, 108, 10, 20, 18, "红蓝灯带", "12V / MOS 低边")
    box(ax, 132, 36, 22, 22, "传感/按键", "光敏 / 电池采样\nMODE / TEST")
    box(ax, 132, 10, 22, 18, "配置接口", "WiFi AP\nOTA / 串口 CLI")

    arrow(ax, (24, 30), (34, 34), "OUT")
    arrow(ax, (68, 40), (76, 44), "UART")
    arrow(ax, (89, 36), (89, 28), "SPK")
    arrow(ax, (68, 34), (108, 44), "PWM")
    arrow(ax, (68, 30), (108, 18), "GPIO32/33")
    arrow(ax, (68, 26), (132, 42), "ADC/按键")
    arrow(ax, (68, 22), (132, 16), "WiFi/OTA")

    ax.text(4, 4, "注：本图为系统级框图，器件级连接以 netlist.csv 与 PCB 布局为准。",
            fontproperties=CN, fontsize=8, color="#666")
    pdf.savefig(fig, bbox_inches="tight"); plt.close(fig)

    # page 2 connector table
    fig, ax = plt.subplots(figsize=(11.7, 8.3)); ax.axis("off")
    ax.text(4, 108, "连接器引脚定义", fontproperties=CN, fontsize=16, weight="bold")
    rows = [["J1", "ESP32 DevKit 30Pin（USB 朝板下）", ""]]
    pinmap = {
        "J1": [("1 EN", "16 3V3"), ("2 GPIO36 / LDR", "17 GND"), ("3 GPIO39 / VBAT", "18 GPIO15 / TEST"),
               ("4 GPIO34 / RADAR", "19 GPIO2 / LED"), ("5 GPIO35", "20 GPIO4 / MODE"),
               ("6 GPIO32 / LED_R", "21 GPIO16 / RADAR_TX"), ("7 GPIO33 / LED_B", "22 GPIO17 / RADAR_RX"),
               ("8 GPIO25", "23 GPIO5"), ("9 GPIO26 / DF_RX", "24 GPIO18"), ("10 GPIO27 / DF_TX", "25 GPIO19"),
               ("11 GPIO14", "26 GPIO21 / SDA"), ("12 GPIO12", "27 GPIO3 / RX0"), ("13 GPIO13 / SERVO", "28 GPIO1 / TX0"),
               ("14 GND", "29 GPIO22 / SCL"), ("15 VIN 5V", "30 GPIO23")],
        "J2": [("1 5V", ""), ("2 GND", ""), ("3 RADAR_TX → GPIO16", ""), ("4 RADAR_RX ← GPIO17", ""),
               ("5 RADAR_OUT → GPIO34", "")],
        "J3": [("1 VCC 5V", ""), ("2 RX ← GPIO27 经 1k", ""), ("3 TX → GPIO26", ""),
               ("4 SPK1", ""), ("5 SPK2", ""), ("6 GND", "")],
        "J4": [("1 5V", ""), ("2 GND", ""), ("3 SERVO ← GPIO13", "")],
        "J5": [("1 12V+", ""), ("2 GND", "")],
        "J6": [("1 SPK+", ""), ("2 SPK-", "")],
        "J7": [("1 12V+", ""), ("2 红灯带 -", ""), ("3 蓝灯带 -", "")],
        "J8": [("1 3V3", ""), ("2 GND", ""), ("3 SDA / GPIO21", ""), ("4 SCL / GPIO22", "")],
        "J9": [("1 3V3", ""), ("2 LDR 分压点 → GPIO36", "")],
    }
    y = 100
    for ref, title in [("J1", "J1  ESP32 DevKit 30Pin"), ("J2", "J2  WT41 雷达"),
                       ("J3", "J3  DFPlayer Mini"), ("J4", "J4  舵机"),
                       ("J5", "J5  12V 输入"), ("J6", "J6  喇叭"),
                       ("J7", "J7  红蓝灯带"), ("J8", "J8  I2C 扩展"), ("J9", "J9  光敏电阻")]:
        ax.text(6, y, title, fontproperties=CN, fontsize=10, weight="bold")
        y -= 5
        for a, b in pinmap[ref]:
            ax.text(10, y, a, fontproperties=CN, fontsize=8)
            if b:
                ax.text(60, y, b, fontproperties=CN, fontsize=8)
            y -= 4.2
        y -= 3
    pdf.savefig(fig, bbox_inches="tight"); plt.close(fig)

print("PCB done.")
print("nets:", len(net_order), "pads:", len(all_pads), "vias:", len(vias))
print("failures:", failures)
