#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
下载 YOLOv8 识别所需的权重文件到 tools/models/。

用法：
    python tools/fetch_models.py                 # 下载 yolov8n + 公开安全帽模型
    python tools/fetch_models.py --ppe-url URL   # 指定自己的防护服权重
    python tools/fetch_models.py --skip-ppe      # 只下载 yolov8n
    python tools/fetch_models.py --check         # 只检查现有权重

说明：
    - 病虫害模型没有通用公开权重，需要用自己的田间照片训练，
      训练后把 best.pt 放到 tools/models/pest.pt（见 docs/YOLOv8识别.md）。
    - 安全帽/防护服模型也建议用现场照片微调，公开权重只作演示。
"""

import argparse
import os
import shutil
import sys
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")

YOLOV8N_URL = "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n.pt"
# 公开的安全帽检测权重（Hugging Face，作者 keremberke）。如链接失效请用 --ppe-url 指定。
PPE_URL = ("https://huggingface.co/keremberke/yolov8n-hard-hat-detection/"
           "resolve/main/best.pt")


def download(url, target, name):
    if os.path.exists(target) and os.path.getsize(target) > 1024 * 1024:
        print("已存在，跳过：%s" % target)
        return True
    print("正在下载 %s ..." % name)
    print("  %s" % url)
    try:
        tmp = target + ".part"
        with urllib.request.urlopen(url, timeout=60) as resp:
            with open(tmp, "wb") as out:
                shutil.copyfileobj(resp, out)
        os.replace(tmp, target)
        print("完成：%s（%.1f MB）" % (target, os.path.getsize(target) / 1048576.0))
        return True
    except Exception as exc:
        print("下载失败：%s" % exc)
        print("请手动下载后放到：%s" % target)
        return False


def check():
    print("模型目录：%s" % MODELS_DIR)
    for name in ("yolov8n.pt", "ppe.pt", "pest.pt"):
        path = os.path.join(MODELS_DIR, name)
        if os.path.exists(path):
            print("  [OK]   %-12s %.1f MB" % (name, os.path.getsize(path) / 1048576.0))
        else:
            print("  [缺失] %-12s" % name)
    print("\n缺少 pest.pt 时病虫害接口会返回 503，需要自行训练后放入。")
    print("缺少 ppe.pt 时会退回 yolov8n.pt，只能识别人员，无法判断穿戴。")


def main():
    parser = argparse.ArgumentParser(description="下载 YOLOv8 权重（稻草人驱鸟器）")
    parser.add_argument("--ppe-url", default=PPE_URL, help="防护服/安全帽权重下载地址")
    parser.add_argument("--skip-ppe", action="store_true", help="跳过防护服权重")
    parser.add_argument("--check", action="store_true", help="只检查现有权重")
    args = parser.parse_args()

    if args.check:
        check()
        return

    os.makedirs(MODELS_DIR, exist_ok=True)

    ok = download(YOLOV8N_URL, os.path.join(MODELS_DIR, "yolov8n.pt"), "YOLOv8n 基础权重")

    if not args.skip_ppe:
        ok = download(args.ppe_url, os.path.join(MODELS_DIR, "ppe.pt"),
                      "安全帽/防护服权重") and ok

    print()
    check()
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
