#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成《稻草人驱鸟控制器 v3.21.5 使用说明》MP4 视频。

依赖：Pillow、imageio-ffmpeg（自带 ffmpeg）
    pip install pillow imageio-ffmpeg

用法：
    python tools/make_usage_video.py
输出：
    dist/稻草人驱鸟控制器_v3.21.5_使用说明.mp4
"""

import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(BASE_DIR, "dist")

W, H = 1920, 1080
FPS = 30
BG = (11, 18, 32)
CARD = (22, 35, 58)
EDGE = (40, 62, 94)
TEXT = (229, 237, 247)
MUTED = (147, 164, 188)
ACCENT = (14, 165, 233)
GREEN = (52, 211, 153)
RED = (220, 38, 38)
AMBER = (245, 158, 11)

REG = "C:/Windows/Fonts/msyh.ttc"
BOLD = "C:/Windows/Fonts/msyhbd.ttc"


def font(size, bold=False):
    return ImageFont.truetype(BOLD if bold else REG, size)


def text_w(draw, text, f):
    box = draw.textbbox((0, 0), text, font=f)
    return box[2] - box[0]


def wrap(draw, text, f, max_width):
    lines = []
    for raw in text.split("\n"):
        if raw == "":
            lines.append("")
            continue
        line = ""
        for ch in raw:
            if text_w(draw, line + ch, f) <= max_width:
                line += ch
            else:
                lines.append(line)
                line = ch
        lines.append(line)
    return lines


def rounded(draw, box, radius, fill, outline=None, width=2):
    draw.rounded_rectangle(box, radius=radius, fill=fill,
                           outline=outline, width=width)


def slide_base(index, total):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    # 顶部品牌
    d.text((80, 46), "稻草人驱鸟控制器", font=font(30, True), fill=ACCENT)
    d.text((W - 80 - text_w(d, "v3.21.5", font(26)), 50), "v3.21.5",
           font=font(26, True), fill=TEXT)
    # 底部进度
    bar_x, bar_y, bar_w = 80, H - 54, W - 160
    rounded(d, (bar_x, bar_y, bar_x + bar_w, bar_y + 6), 3, (35, 51, 78), None, 0)
    progress = int(bar_w * (index + 1) / float(total))
    rounded(d, (bar_x, bar_y, bar_x + progress, bar_y + 6), 3, ACCENT, None, 0)
    d.text((80, H - 34), "开发者：胡宇宸   ·   开发日期：2026-11-21",
           font=font(20), fill=(100, 116, 138))
    d.text((W - 80 - text_w(d, "%d / %d" % (index + 1, total), font(20)), H - 34),
           "%d / %d" % (index + 1, total), font=font(20), fill=(100, 116, 138))
    return img


def title(img, text, sub=None):
    d = ImageDraw.Draw(img)
    d.text((80, 116), text, font=font(62, True), fill=TEXT)
    y = 200
    if sub:
        d.text((80, y), sub, font=font(30), fill=MUTED)
        y += 54
    d.line((80, y + 10, W - 80, y + 10), fill=EDGE, width=2)
    return y + 34


def bullets(img, items, x, y, width, size=32, gap=18):
    d = ImageDraw.Draw(img)
    f = font(size)
    fb = font(size, True)
    for item in items:
        color = TEXT
        prefix = "•  "
        if item.startswith("!"):
            item = item[1:]
            color = AMBER
        elif item.startswith("+"):
            item = item[1:]
            color = GREEN
        lines = wrap(d, item, f, width - 40)
        d.text((x, y), prefix, font=fb, fill=ACCENT)
        for i, line in enumerate(lines):
            d.text((x + 36, y + i * int(size * 1.45)), line, font=f, fill=color)
        y += len(lines) * int(size * 1.45) + gap
    return y


def image_card(img, path, box, caption=None):
    d = ImageDraw.Draw(img)
    x1, y1, x2, y2 = box
    rounded(d, box, 16, CARD, EDGE)
    pad = 14
    inner = (x1 + pad, y1 + pad, x2 - pad, y2 - pad - (40 if caption else 0))
    if not os.path.exists(path):
        d.text(((x1 + x2) // 2 - 60, (y1 + y2) // 2),
               "界面示意", font=font(28), fill=MUTED)
        return
    pic = Image.open(path).convert("RGB")
    iw, ih = pic.size
    avail_w = inner[2] - inner[0]
    avail_h = inner[3] - inner[1]
    scale = min(avail_w / float(iw), avail_h / float(ih))
    nw, nh = max(1, int(iw * scale)), max(1, int(ih * scale))
    pic = pic.resize((nw, nh), Image.LANCZOS)
    px = inner[0] + (avail_w - nw) // 2
    py = inner[1] + (avail_h - nh) // 2
    img.paste(pic, (px, py))
    d.rectangle((px - 1, py - 1, px + nw, py + nh), outline=EDGE, width=2)
    if caption:
        d.text((x1 + pad, y2 - 38), caption, font=font(22), fill=MUTED)


def slide_cover(total):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 14, H), fill=ACCENT)
    d.text((130, 220), "稻草人驱鸟控制器", font=font(96, True), fill=TEXT)
    d.text((134, 344), "使用说明  ·  Windows 11 服务端 + 手机 App", font=font(40), fill=ACCENT)
    d.line((134, 420, 900, 420), fill=EDGE, width=3)

    lines = [
        ("版本", "v3.21.5"),
        ("开发者", "胡宇宸"),
        ("开发日期", "2026-11-21"),
        ("适用", "Windows 11 / Android 7.0 以上"),
    ]
    y = 480
    for k, v in lines:
        d.text((134, y), k, font=font(28), fill=MUTED)
        d.text((330, y - 4), v, font=font(34, True), fill=TEXT)
        y += 68

    # 右侧示意：手机 + 服务器 + 设备
    def node(cx, cy, r, label, color):
        d.rounded_rectangle((cx - r, cy - r * 0.62, cx + r, cy + r * 0.62),
                            radius=22, fill=CARD, outline=color, width=4)
        tw = text_w(d, label, font(30, True))
        d.text((cx - tw // 2, cy - 20), label, font=font(30, True), fill=TEXT)

    node(1470, 380, 170, "手机 App", ACCENT)
    node(1470, 610, 170, "Windows 服务", GREEN)
    node(1470, 840, 170, "驱鸟设备", AMBER)
    d.line((1470, 500, 1470, 556), fill=MUTED, width=3)
    d.line((1470, 700, 1470, 756), fill=MUTED, width=3)
    d.text((1530, 512), "HTTP", font=font(22), fill=MUTED)
    d.text((1530, 712), "局域网", font=font(22), fill=MUTED)

    d.text((130, H - 120), "所有数据经 Windows 服务端转发，服务器与设备均可手动绑定",
           font=font(26), fill=MUTED)
    return img


def slide_arch(total):
    img = slide_base(1, total)
    y = title(img, "系统组成", "手机不直连设备，统一经 Windows 11 服务端转发")
    d = ImageDraw.Draw(img)
    boxes = [
        (120, y + 30, 620, y + 300, "① 手机 / 电脑客户端", ACCENT,
         ["设备控制、硬件设置", "扩展功能、参数配置"]),
        (710, y + 30, 1210, y + 300, "② Windows 11 服务端", GREEN,
         ["监听端口（默认 1819）", "每个客户端独立转发通道"]),
        (1300, y + 30, 1800, y + 300, "③ 驱鸟设备", AMBER,
         ["ESP32 控制板", "摄像头 / 雷达 / 小车 / 水阀"]),
    ]
    for x1, y1, x2, y2, name, color, items in boxes:
        rounded(d, (x1, y1, x2, y2), 20, CARD, color, 3)
        d.text((x1 + 26, y1 + 24), name, font=font(34, True), fill=color)
        yy = y1 + 86
        for it in items:
            d.text((x1 + 26, yy), "· " + it, font=font(26), fill=TEXT)
            yy += 42
    # 箭头
    for (x1, x2) in ((620, 710), (1210, 1300)):
        cy = y + 165
        d.line((x1 + 10, cy, x2 - 14, cy), fill=MUTED, width=4)
        d.polygon([(x2 - 14, cy - 9), (x2 - 2, cy), (x2 - 14, cy + 9)], fill=MUTED)

    rounded(d, (120, y + 350, 1800, y + 560), 20, CARD, EDGE)
    d.text((150, y + 372), "YOLOv8 识别服务（可选）", font=font(32, True), fill=ACCENT)
    d.text((150, y + 424), "运行在同一台 Windows 电脑：python tools/yolo_service.py --port 8000",
           font=font(26), fill=TEXT)
    d.text((150, y + 470), "· 病虫害识别：models/pest.pt", font=font(26), fill=TEXT)
    d.text((150, y + 512), "· 防护服 / 安全帽：models/ppe.pt，自动判断穿戴合规",
           font=font(26), fill=TEXT)
    return img


def slide_server(total, shot):
    img = slide_base(2, total)
    y = title(img, "第一步：配置 Windows 服务端", "ScarecrowServer.exe")
    bullets(img, [
        "打开【设备绑定】，填写设备名称与地址，例如 192.168.1.66:8080",
        "点击【添加 / 更新】，选中后【设为当前】",
        "在【监听设置】确认端口（默认 1819），点击【启动服务】",
        "每个客户端按 X-Client-Id 建立独立通道，互不影响",
        "!手机无法访问时：在 Windows 防火墙放行该端口",
    ], 80, y + 10, 830, 30)
    image_card(img, shot, (960, y - 6, 1840, y + 610), "服务端主界面")
    return img


def slide_bind(total, shot):
    img = slide_base(3, total)
    y = title(img, "第二步：手机绑定服务器与设备", "App 内可分别填写，保存后立即生效")
    bullets(img, [
        "服务器地址：运行服务端的电脑 IP:端口，例如 192.168.1.20:1819",
        "设备地址：服务端所在网络中设备的 IP:端口，例如 192.168.1.66:80",
        "设备地址可留空，由服务端使用【当前设备】",
        "+底部导航栏固定显示：设备控制 / 设备状态 / 硬件设置 / 扩展功能 / 设置",
        "网络变化后回到本页重新保存即可",
    ], 80, y + 10, 830, 30)
    image_card(img, shot, (960, y - 6, 1840, y + 610), "手机端硬件设置")
    return img


def slide_control(total, shot):
    img = slide_base(4, total)
    y = title(img, "设备控制", "所有快捷操作集中在首页")
    bullets(img, [
        "立即试驱：触发一次完整驱赶流程",
        "声音测试 / 灯光测试 / 云台测试：分别验证对应部件",
        "停止输出：立即停止驱赶与测试",
        "网页控制台：用浏览器打开设备自带页面",
        "恢复默认 / 重启设备：危险操作，执行前二次确认",
        "实时运行数据已独立到【设备状态】页查看",
    ], 80, y + 10, 830, 30)
    image_card(img, shot, (960, y - 6, 1840, y + 610), "手机端设备控制")
    return img


def slide_status(total, shot):
    img = slide_base(5, total)
    y = title(img, "设备状态", "每 2.5 秒自动刷新，数据经服务端转发")
    bullets(img, [
        "运行状态：待机 / 驱赶中 / 冷却中 / 静音中",
        "电池电压与光照环境：判断电量与白天 / 夜间",
        "静音时段：当前是否处于免打扰区间",
        "雷达脉冲、在线时长、固件版本、网络模式：用于巡检与排障",
        "!全部显示 - 时，先到【硬件设置】检查服务器与设备绑定",
    ], 80, y + 10, 830, 30)
    image_card(img, shot, (960, y - 6, 1840, y + 610), "手机端设备状态")
    return img


def slide_windows(total, shot):
    img = slide_base(6, total)
    y = title(img, "Windows 11 客户端", "与手机端同一套功能，连接设置集中在【硬件设置】")
    bullets(img, [
        "顶部显示连接状态，例如 已连接 127.0.0.1:18080",
        "底部导航：设备控制 / 设备状态 / 硬件设置 / 扩展功能 / 设置",
        "【硬件设置】填写服务器与设备地址，保存并连接，也可自动查找",
        "运行日志与开发者警示统一放在【设置】页",
        "两端同时在线时，服务端为每个客户端分配独立转发通道",
    ], 80, y + 10, 830, 30)
    image_card(img, shot, (960, y - 6, 1840, y + 610), "Windows 11 客户端")
    return img


def slide_pest(total, shot):
    img = slide_base(7, total)
    y = title(img, "病虫害识别（YOLOv8）", "模型放在 models/pest.pt，结果按风险分级")
    bullets(img, [
        "识别服务：python tools/yolo_service.py --port 8000",
        "支持单张田间照片与摄像头实时画面",
        "输出：目标数量、位置、置信度、病斑面积占比",
        "风险等级：轻微（<0.5%）/ 中等（<2%）/ 严重（≥2%）",
        "!没有 pest.pt 时接口返回 503，需先用本地照片训练",
    ], 80, y + 10, 830, 30)
    image_card(img, shot, (960, y - 6, 1840, y + 610), "手机端病虫害识别")
    return img


def slide_ppe(total, shot):
    img = slide_base(8, total)
    y = title(img, "防护服穿戴检测与识别", "人员框 + 安全帽 / 防护服框自动关联")
    bullets(img, [
        "模型类别：person / helmet / vest / no_helmet / no_vest",
        "逐人判断：是否戴安全帽、是否穿防护服",
        "+输出合规人数、不合规人数、缺失项数量",
        "!未穿戴时红色报警并标注具体缺少的物品",
        "仅有 yolov8n 权重时只能识别人，不能判断穿戴",
    ], 80, y + 10, 830, 30)
    image_card(img, shot, (960, y - 6, 1840, y + 610), "手机端防护服检测")
    return img


def slide_extra(total, shot):
    img = slide_base(9, total)
    y = title(img, "扩展功能", "驱鸟策略 / 小车路线 / 天气与水阀")
    bullets(img, [
        "驱鸟策略：雷达、视觉、雷达+视觉三种触发方式，视觉冷却 30-3600 秒",
        "小车路线：每行一个航点 x,y,动作,停留秒数，最多 64 个点",
        "天气预报：输入经纬度读取实时天气，结合温湿度提示灌溉",
        "水阀控制：手动开阀 30 秒 / 关闭 / 读取状态，支持自动规则",
    ], 80, y + 10, 830, 30)
    image_card(img, shot, (960, y - 6, 1840, y + 610), "手机端扩展功能")
    return img


def slide_faq(total):
    img = slide_base(10, total)
    y = title(img, "常见问题", "按顺序排查，多数问题可在 1 分钟内定位")
    rows = [
        ("手机提示未连接", "确认手机与服务端在同一网络，防火墙已放行端口，服务端显示运行中"),
        ("能连服务器但读不到设备", "检查设备地址是否正确；在服务端列表里把目标设备设为当前"),
        ("识别接口返回 503", "模型文件不存在或缺少 ultralytics，先执行 pip install -r tools/requirements-yolo.txt"),
        ("防护服检测不报警", "只有 yolov8n 权重时无法判断穿戴，请放入含 helmet/vest 类别的 ppe.pt"),
        ("服务端启动失败", "端口被占用或被系统拒绝，换端口或以管理员身份运行"),
    ]
    d = ImageDraw.Draw(img)
    yy = y + 20
    for q, a in rows:
        rounded(d, (80, yy, 1840, yy + 118), 16, CARD, EDGE)
        d.text((110, yy + 20), "Q  " + q, font=font(28, True), fill=AMBER)
        lines = wrap(d, a, font(25), 1650)
        for i, line in enumerate(lines[:2]):
            d.text((110, yy + 62 + i * 34), line, font=font(25), fill=TEXT)
        yy += 138
    return img


def slide_end(total):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 14, H), fill=GREEN)
    d.text((130, 300), "开始使用", font=font(88, True), fill=TEXT)
    d.text((134, 420), "1. 启动 ScarecrowServer.exe，绑定设备并启动服务", font=font(34), fill=MUTED)
    d.text((134, 486), "2. 手机 App 绑定服务器与设备", font=font(34), fill=MUTED)
    d.text((134, 552), "3. 进入设备控制，先做声音/灯光测试", font=font(34), fill=MUTED)
    d.text((134, 618), "4. 需要识别时再启动 YOLOv8 服务并放入模型", font=font(34), fill=MUTED)
    d.line((134, 720, 1200, 720), fill=EDGE, width=3)
    d.text((134, 760), "稻草人驱鸟控制器  v3.21.5", font=font(40, True), fill=ACCENT)
    d.text((134, 822), "开发者：胡宇宸     开发日期：2026-11-21", font=font(30), fill=TEXT)
    d.text((134, 900), "内容由AI大模型生成，请仔细甄别", font=font(24), fill=(100, 116, 138))
    return img


def find_shot(name):
    candidates = [
        os.path.join(BASE_DIR, "docs", "video", name),
        os.path.join(BASE_DIR, "app", "android", name),
        os.path.join(BASE_DIR, "app", "windows-server", name),
        os.path.join(BASE_DIR, "app", "windows", name),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return os.path.join(BASE_DIR, "docs", "video", name)


def build_slides():
    shots = {
        "server": find_shot("screen_service.png"),
        "settings": find_shot("shot_settings.png"),
        "control": find_shot("shot_control.png"),
        "status": find_shot("shot_status.png"),
        "windows": find_shot("win_client.png"),
        "pest": find_shot("shot_pest.png"),
        "ppe": find_shot("shot_ppe.png"),
        "extra": find_shot("shot_features.png"),
    }
    total = 12
    return [
        slide_cover(total),
        slide_arch(total),
        slide_server(total, shots["server"]),
        slide_bind(total, shots["settings"]),
        slide_control(total, shots["control"]),
        slide_status(total, shots["status"]),
        slide_windows(total, shots["windows"]),
        slide_pest(total, shots["pest"]),
        slide_ppe(total, shots["ppe"]),
        slide_extra(total, shots["extra"]),
        slide_faq(total),
        slide_end(total),
    ]


def main():
    try:
        import imageio_ffmpeg
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        ffmpeg = "ffmpeg"

    slides = build_slides()
    hold = 4.4
    fade = 0.5
    hold_frames = int(hold * FPS)
    fade_frames = int(fade * FPS)

    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, "稻草人驱鸟控制器_v3.21.5_使用说明.mp4")

    cmd = [
        ffmpeg, "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", "%dx%d" % (W, H), "-r", str(FPS), "-i", "-",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        out,
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    black = Image.new("RGB", (W, H), BG)
    prev = black
    try:
        for idx, shot in enumerate(slides):
            # 淡入
            for i in range(fade_frames):
                alpha = (i + 1) / float(fade_frames)
                frame = Image.blend(prev, shot, alpha)
                proc.stdin.write(frame.tobytes())
            # 停留
            for _ in range(hold_frames - fade_frames * 2):
                proc.stdin.write(shot.tobytes())
            # 淡出（最后一页淡到黑）
            following = slides[idx + 1] if idx + 1 < len(slides) else black
            for i in range(fade_frames):
                alpha = (i + 1) / float(fade_frames)
                frame = Image.blend(shot, following, alpha)
                proc.stdin.write(frame.tobytes())
            prev = following
        proc.stdin.close()
        proc.wait(timeout=180)
    except BrokenPipeError:
        pass
    finally:
        if proc.poll() is None:
            proc.terminate()

    if proc.returncode not in (0, None):
        print("视频编码失败，返回码：%s" % proc.returncode)
        sys.exit(1)

    size = os.path.getsize(out) / 1048576.0
    print("已生成：%s" % out)
    print("大小：%.1f MB，时长约 %.0f 秒" % (size, len(slides) * hold))


if __name__ == "__main__":
    main()
