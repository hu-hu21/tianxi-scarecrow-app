#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import math
import random
import socket
import sys
import threading
import time
import urllib.parse
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

VERSION = "1.0.0"
DEFAULT_PORT = 1819


CAM_W, CAM_H = 192, 144

LUMA_Q = [
    16, 11, 10, 16, 24, 40, 51, 61,
    12, 12, 14, 19, 26, 58, 60, 55,
    14, 13, 16, 24, 40, 57, 69, 56,
    14, 17, 22, 29, 51, 87, 80, 62,
    18, 22, 37, 56, 68, 109, 103, 77,
    24, 35, 55, 64, 81, 104, 113, 92,
    49, 64, 78, 87, 103, 121, 120, 101,
    72, 92, 95, 98, 112, 100, 103, 99,
]

CHROMA_Q = [
    17, 18, 24, 47, 99, 99, 99, 99,
    18, 21, 26, 66, 99, 99, 99, 99,
    24, 26, 56, 99, 99, 99, 99, 99,
    47, 66, 99, 99, 99, 99, 99, 99,
    99, 99, 99, 99, 99, 99, 99, 99,
    99, 99, 99, 99, 99, 99, 99, 99,
    99, 99, 99, 99, 99, 99, 99, 99,
    99, 99, 99, 99, 99, 99, 99, 99,
]

ZIGZAG = [
    0, 1, 8, 16, 9, 2, 3, 10,
    17, 24, 32, 25, 18, 11, 4, 5,
    12, 19, 26, 33, 40, 48, 41, 34,
    27, 20, 13, 6, 7, 14, 21, 28,
    35, 42, 49, 56, 57, 50, 43, 36,
    29, 22, 15, 23, 30, 37, 44, 51,
    58, 59, 52, 45, 38, 31, 39, 46,
    53, 60, 61, 54, 47, 55, 62, 63,
]

DC_LUMA_BITS = [0, 1, 5, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0]
DC_CHROMA_BITS = [0, 3, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0]
AC_LUMA_BITS = [0, 2, 1, 3, 3, 2, 4, 3, 5, 5, 4, 4, 0, 0, 1, 0x7D]
AC_CHROMA_BITS = [0, 2, 1, 2, 4, 4, 3, 4, 7, 5, 4, 4, 0, 1, 2, 0x77]

AC_LUMA_VALS = [
    0x01, 0x02, 0x03, 0x00, 0x04, 0x11, 0x05, 0x12, 0x21, 0x31, 0x41, 0x06,
    0x13, 0x51, 0x61, 0x07, 0x22, 0x71, 0x14, 0x32, 0x81, 0x91, 0xA1, 0x08,
    0x23, 0x42, 0xB1, 0xC1, 0x15, 0x52, 0xD1, 0xF0, 0x24, 0x33, 0x62, 0x72,
    0x82, 0x09, 0x0A, 0x16, 0x17, 0x18, 0x19, 0x1A, 0x25, 0x26, 0x27, 0x28,
    0x29, 0x2A, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3A, 0x43, 0x44, 0x45,
    0x46, 0x47, 0x48, 0x49, 0x4A, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59,
    0x5A, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69, 0x6A, 0x73, 0x74, 0x75,
    0x76, 0x77, 0x78, 0x79, 0x7A, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89,
    0x8A, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98, 0x99, 0x9A, 0xA2, 0xA3,
    0xA4, 0xA5, 0xA6, 0xA7, 0xA8, 0xA9, 0xAA, 0xB2, 0xB3, 0xB4, 0xB5, 0xB6,
    0xB7, 0xB8, 0xB9, 0xBA, 0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7, 0xC8, 0xC9,
    0xCA, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9, 0xDA, 0xE1, 0xE2,
    0xE3, 0xE4, 0xE5, 0xE6, 0xE7, 0xE8, 0xE9, 0xEA, 0xF1, 0xF2, 0xF3, 0xF4,
    0xF5, 0xF6, 0xF7, 0xF8, 0xF9, 0xFA,
]

AC_CHROMA_VALS = [
    0x00, 0x01, 0x02, 0x03, 0x11, 0x04, 0x05, 0x21, 0x31, 0x06, 0x12, 0x41,
    0x51, 0x07, 0x61, 0x71, 0x13, 0x22, 0x32, 0x81, 0x08, 0x14, 0x42, 0x91,
    0xA1, 0xB1, 0xC1, 0x09, 0x23, 0x33, 0x52, 0xF0, 0x15, 0x62, 0x72, 0xD1,
    0x0A, 0x16, 0x24, 0x34, 0xE1, 0x25, 0xF1, 0x17, 0x18, 0x19, 0x1A, 0x26,
    0x27, 0x28, 0x29, 0x2A, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3A, 0x43, 0x44,
    0x45, 0x46, 0x47, 0x48, 0x49, 0x4A, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58,
    0x59, 0x5A, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69, 0x6A, 0x73, 0x74,
    0x75, 0x76, 0x77, 0x78, 0x79, 0x7A, 0x82, 0x83, 0x84, 0x85, 0x86, 0x87,
    0x88, 0x89, 0x8A, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98, 0x99, 0x9A,
    0xA2, 0xA3, 0xA4, 0xA5, 0xA6, 0xA7, 0xA8, 0xA9, 0xAA, 0xB2, 0xB3, 0xB4,
    0xB5, 0xB6, 0xB7, 0xB8, 0xB9, 0xBA, 0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7,
    0xC8, 0xC9, 0xCA, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9, 0xDA,
    0xE2, 0xE3, 0xE4, 0xE5, 0xE6, 0xE7, 0xE8, 0xE9, 0xEA, 0xF2, 0xF3, 0xF4,
    0xF5, 0xF6, 0xF7, 0xF8, 0xF9, 0xFA,
]

COS = [[0.5 * (1.0 / math.sqrt(2.0) if u == 0 else 1.0) *
        math.cos((2 * x + 1) * u * math.pi / 16.0) for x in range(8)]
       for u in range(8)]


def _huff_table(bits, vals):
    table = {}
    code = 0
    k = 0
    for length in range(1, 17):
        for _ in range(bits[length - 1]):
            table[vals[k]] = (code, length)
            code += 1
            k += 1
        code <<= 1
    return table


T_DC_Y = _huff_table(DC_LUMA_BITS, list(range(12)))
T_DC_C = _huff_table(DC_CHROMA_BITS, list(range(12)))
T_AC_Y = _huff_table(AC_LUMA_BITS, AC_LUMA_VALS)
T_AC_C = _huff_table(AC_CHROMA_BITS, AC_CHROMA_VALS)


class BitWriter(object):
    __slots__ = ("out", "buf", "n")

    def __init__(self):
        self.out = bytearray()
        self.buf = 0
        self.n = 0

    def write(self, value, length):
        if length <= 0:
            return
        self.buf = (self.buf << length) | (value & ((1 << length) - 1))
        self.n += length
        while self.n >= 8:
            self.n -= 8
            b = (self.buf >> self.n) & 0xFF
            self.out.append(b)
            if b == 0xFF:
                self.out.append(0)
        self.buf &= (1 << self.n) - 1 if self.n else 0

    def flush(self):
        if self.n:
            self.write(0, 8 - self.n)


def _category(value):
    a = -value if value < 0 else value
    n = 0
    while a:
        n += 1
        a >>= 1
    return n


def _emit_block(bw, blk, quant, dc_tab, ac_tab, prev_dc):
    tmp = [0.0] * 64
    for y in range(8):
        o = y * 8
        r0, r1, r2, r3, r4, r5, r6, r7 = blk[o:o + 8]
        for u in range(8):
            m = COS[u]
            tmp[u * 8 + y] = (m[0] * r0 + m[1] * r1 + m[2] * r2 + m[3] * r3 +
                              m[4] * r4 + m[5] * r5 + m[6] * r6 + m[7] * r7)

    qz = [0] * 64
    for u in range(8):
        o = u * 8
        c0, c1, c2, c3, c4, c5, c6, c7 = tmp[o:o + 8]
        for v in range(8):
            m = COS[v]
            val = (m[0] * c0 + m[1] * c1 + m[2] * c2 + m[3] * c3 +
                   m[4] * c4 + m[5] * c5 + m[6] * c6 + m[7] * c7)
            qz[v * 8 + u] = int(round(val / quant[v * 8 + u]))

    dc = qz[0]
    diff = dc - prev_dc
    size = _category(diff)
    if size > 11:
        size = 11
    code, length = dc_tab[size]
    bw.write(code, length)
    if size:
        bw.write(diff if diff >= 0 else diff - 1, size)

    run = 0
    for i in range(1, 64):
        val = qz[ZIGZAG[i]]
        if val == 0:
            run += 1
            continue
        if val > 1023:
            val = 1023
        elif val < -1023:
            val = -1023
        while run > 15:
            code, length = ac_tab[0xF0]
            bw.write(code, length)
            run -= 16
        size = _category(val)
        code, length = ac_tab[(run << 4) | size]
        bw.write(code, length)
        bw.write(val if val >= 0 else val - 1, size)
        run = 0
    if run:
        code, length = ac_tab[0x00]
        bw.write(code, length)
    return dc


def encode_jpeg(width, height, rgb, quality=58):
    """把 RGB 字节流编码成 JPEG（4:2:0 基线）。宽高必须是 16 的倍数。"""
    if width % 16 or height % 16:
        raise ValueError("width/height must be multiples of 16")
    if len(rgb) != width * height * 3:
        raise ValueError("rgb buffer size mismatch")

    scale = 5000 // quality if quality < 50 else 200 - 2 * quality
    ql = [max(1, min(255, (v * scale + 50) // 100)) for v in LUMA_Q]
    qc = [max(1, min(255, (v * scale + 50) // 100)) for v in CHROMA_Q]

    out = bytearray()
    out += b"\xff\xd8"
    out += b"\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    out += b"\xff\xdb\x00\x43\x00" + bytes(ql[z] for z in ZIGZAG)
    out += b"\xff\xdb\x00\x43\x01" + bytes(qc[z] for z in ZIGZAG)
    out += b"\xff\xc0\x00\x11\x08"
    out += bytes([(height >> 8) & 0xFF, height & 0xFF, (width >> 8) & 0xFF, width & 0xFF])
    out += b"\x03\x01\x22\x00\x02\x11\x01\x03\x11\x01"

    for cls, tid, bits, vals in (
        (0, 0, DC_LUMA_BITS, list(range(12))),
        (0, 1, DC_CHROMA_BITS, list(range(12))),
        (1, 0, AC_LUMA_BITS, AC_LUMA_VALS),
        (1, 1, AC_CHROMA_BITS, AC_CHROMA_VALS),
    ):
        seg = bytes([(cls << 4) | tid]) + bytes(bits) + bytes(vals)
        total = len(seg) + 2
        out += b"\xff\xc4" + bytes([(total >> 8) & 0xFF, total & 0xFF]) + seg

    out += b"\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00"

    bw = BitWriter()
    prev = [0, 0, 0]

    for my in range(0, height, 16):
        for mx in range(0, width, 16):
            for by in range(2):
                for bx in range(2):
                    blk = [0.0] * 64
                    for y in range(8):
                        row = ((my + by * 8 + y) * width + mx + bx * 8) * 3
                        for x in range(8):
                            i = row + x * 3
                            blk[y * 8 + x] = (0.299 * rgb[i] + 0.587 * rgb[i + 1] +
                                              0.114 * rgb[i + 2] - 128.0)
                    prev[0] = _emit_block(bw, blk, ql, T_DC_Y, T_AC_Y, prev[0])

            for comp in (1, 2):
                blk = [0.0] * 64
                for y in range(8):
                    row = ((my + y * 2) * width + mx) * 3
                    for x in range(8):
                        i = row + x * 6
                        r, g, b = rgb[i], rgb[i + 1], rgb[i + 2]
                        if comp == 1:
                            blk[y * 8 + x] = -0.168736 * r - 0.331264 * g + 0.5 * b
                        else:
                            blk[y * 8 + x] = 0.5 * r - 0.418688 * g - 0.081312 * b
                prev[comp] = _emit_block(bw, blk, qc, T_DC_C, T_AC_C, prev[comp])

    bw.flush()
    out += bw.out
    out += b"\xff\xd9"
    return bytes(out)




class Canvas(object):
    __slots__ = ("w", "h", "buf")

    def __init__(self, w, h, bg=(0, 0, 0)):
        self.w = w
        self.h = h
        self.buf = bytearray(bytes(bg) * (w * h))

    def px(self, x, y, rgb):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.buf[i] = rgb[0]
            self.buf[i + 1] = rgb[1]
            self.buf[i + 2] = rgb[2]

    def hline(self, x0, x1, y, rgb):
        if y < 0 or y >= self.h:
            return
        if x0 > x1:
            x0, x1 = x1, x0
        x0 = max(0, x0)
        x1 = min(self.w - 1, x1)
        if x1 < x0:
            return
        i = (y * self.w + x0) * 3
        self.buf[i:i + (x1 - x0 + 1) * 3] = bytes(rgb) * (x1 - x0 + 1)

    def rect(self, x0, y0, x1, y1, rgb):
        if x0 > x1:
            x0, x1 = x1, x0
        if y0 > y1:
            y0, y1 = y1, y0
        for y in range(max(0, y0), min(self.h - 1, y1) + 1):
            self.hline(x0, x1, y, rgb)

    def frame(self, x0, y0, x1, y1, rgb):
        self.hline(x0, x1, y0, rgb)
        self.hline(x0, x1, y1, rgb)
        for y in range(y0, y1 + 1):
            self.px(x0, y, rgb)
            self.px(x1, y, rgb)

    def vgrad(self, y0, y1, c0, c1):
        span = max(1, y1 - y0 - 1)
        for y in range(max(0, y0), min(self.h, y1)):
            k = (y - y0) / float(span)
            rgb = (int(c0[0] + (c1[0] - c0[0]) * k),
                   int(c0[1] + (c1[1] - c0[1]) * k),
                   int(c0[2] + (c1[2] - c0[2]) * k))
            self.hline(0, self.w - 1, y, rgb)

    def circle(self, cx, cy, r, rgb):
        for y in range(cy - r, cy + r + 1):
            dy = y - cy
            if abs(dy) > r:
                continue
            half = int((r * r - dy * dy) ** 0.5)
            self.hline(cx - half, cx + half, y, rgb)

    def ellipse(self, cx, cy, rx, ry, rgb):
        for y in range(cy - ry, cy + ry + 1):
            dy = (y - cy) / float(ry)
            if abs(dy) > 1:
                continue
            half = int(rx * (1.0 - dy * dy) ** 0.5)
            self.hline(cx - half, cx + half, y, rgb)

    def line(self, x0, y0, x1, y1, rgb):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.px(x0, y0, rgb)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy


def render_scene(t):
    """按时间 t（秒）绘制一帧农田画面，返回 (Canvas, 目标框信息)。"""
    W, H = CAM_W, CAM_H
    c = Canvas(W, H, (24, 32, 48))

    c.vgrad(0, 94, (30, 42, 66), (128, 142, 148))
    c.circle(int(W * 0.78), 22, 8, (236, 225, 186))
    c.circle(int(W * 0.78), 22, 5, (248, 240, 208))

    # 云
    drift = int(t * 4)
    for base, y, rx, ry in ((26, 30, 20, 3), (84, 46, 14, 3), (132, 20, 11, 2)):
        x = (base + drift) % (W + 40) - 20
        c.ellipse(x, y, rx, ry, (150, 165, 178))
        c.ellipse(x - rx // 2, y + 2, rx // 2, ry, (150, 165, 178))

    # 地面与垄沟
    c.vgrad(90, H, (62, 84, 48), (34, 48, 28))
    for i in range(6):
        yy = 96 + i * 9
        for x in range(0, W, 2):
            y = yy + int(1.6 * math.sin(x / 14.0 + i * 1.3))
            c.px(x, y, (48, 68, 38))

    # 作物
    for x in range(6, W, 9):
        top = 90 + (x * 7) % 9
        c.line(x, top, x, top + 5, (44, 92, 44))
        c.line(x, top + 2, x - 3, top + 5, (54, 104, 50))
        c.line(x, top + 2, x + 3, top + 5, (54, 104, 50))

    # 病叶与病斑
    leaves = ((36, 104), (70, 111), (106, 99))
    spots = []
    for idx, (lx, ly) in enumerate(leaves):
        c.ellipse(lx, ly, 9, 4, (52, 96, 46))
        c.ellipse(lx - 3, ly - 2, 4, 3, (66, 116, 54))
        sx = lx + idx * 2 - 2
        sy = ly + (idx % 2) * 2 - 1
        c.circle(sx, sy, 2, (120, 88, 42))
        c.circle(sx, sy, 1, (168, 132, 60))
        spots.append((sx, sy))

    # 作业人员：每 12 秒切换一次防护状态
    phase = int(t // 12) % 4
    helmet = phase != 1
    vest = phase != 2
    wx = 44 + int((t * 9) % 108)
    base = 128
    c.ellipse(wx, base + 1, 9, 2, (28, 40, 26))
    c.rect(wx - 4, base - 14, wx - 1, base, (36, 42, 58))
    c.rect(wx + 1, base - 14, wx + 4, base, (36, 42, 58))
    body = (206, 112, 40) if vest else (58, 76, 112)
    c.rect(wx - 7, base - 31, wx + 7, base - 14, body)
    if vest:
        c.rect(wx - 7, base - 28, wx + 7, base - 26, (214, 220, 224))
        c.rect(wx - 7, base - 21, wx + 7, base - 19, (214, 220, 224))
    c.line(wx - 7, base - 29, wx - 10, base - 20, body)
    c.line(wx + 7, base - 29, wx + 10, base - 20, body)
    c.circle(wx, base - 36, 4, (208, 168, 132))
    if helmet:
        c.circle(wx, base - 38, 5, (228, 188, 44))
        c.circle(wx, base - 36, 4, (208, 168, 132))
    else:
        c.ellipse(wx, base - 39, 4, 2, (44, 38, 34))

    # 飞鸟
    bx = int((t * 16) % (W + 40)) - 20
    by = 36 + int(7 * math.sin(t * 0.8))
    flap = int(3 * math.sin(t * 9))
    c.line(bx - 6, by + 2, bx, by - flap, (38, 40, 44))
    c.line(bx, by - flap, bx + 6, by + 2, (38, 40, 44))

    # 仿监控画面的边角标记
    c.frame(0, 0, W - 1, H - 1, (70, 84, 96))
    for x0, y0 in ((6, 6), (W - 12, 6), (6, H - 12), (W - 12, H - 12)):
        c.frame(x0, y0, x0 + 5, y0 + 5, (120, 140, 150))

    labels = (("稻瘟病", "rice_blast"), ("叶斑病", "leaf_spot"), ("稻飞虱", "planthopper"))
    pest = []
    for i, (sx, sy) in enumerate(spots):
        conf = round(0.62 + 0.3 * abs(math.sin(t * 0.17 + i * 1.1)), 2)
        pest.append({
            "label": labels[i][0], "label_en": labels[i][1], "confidence": conf,
            "box": [sx - 5, sy - 5, sx + 5, sy + 5],
        })

    ppe = {
        "person": [wx - 9, base - 41, wx + 9, base + 1],
        "helmet": [wx - 6, base - 44, wx + 6, base - 33] if helmet else None,
        "vest": [wx - 7, base - 31, wx + 7, base - 14] if vest else None,
        "alarm": (not helmet) or (not vest),
    }
    return c, {"pest": pest, "ppe": ppe}


def _draw_box(canvas, box, rgb, label_bar=True):
    x1, y1, x2, y2 = [int(v) for v in box]
    canvas.frame(x1, y1, x2, y2, rgb)
    if label_bar:
        canvas.rect(x1, max(0, y1 - 3), x1 + 12, max(0, y1 - 1), rgb)


# ============================================================ 摄像头

class Camera(object):
    def __init__(self):
        self.lock = threading.Lock()
        self.gen_lock = threading.Lock()
        self.rgb = None
        self.jpeg = b""
        self.objects = {"pest": [], "ppe": {}}
        self.stamp = 0.0
        self.started = time.time()
        self.viewers = 0
        self.last_use = 0.0
        self.ann = {}
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def _loop(self):
        while True:
            now = time.time()
            busy = self.viewers > 0 or (now - self.last_use) < 3.0
            if busy and now - self.stamp >= 0.30:
                self.make()
            time.sleep(0.05)

    def make(self):
        if not self.gen_lock.acquire(False):
            return
        try:
            now = time.time()
            canvas, objects = render_scene(now - self.started)
            jpeg = encode_jpeg(CAM_W, CAM_H, canvas.buf, 58)
            with self.lock:
                self.rgb = canvas.buf
                self.jpeg = jpeg
                self.objects = objects
                self.stamp = now
        finally:
            self.gen_lock.release()

    def snapshot(self):
        self.last_use = time.time()
        with self.lock:
            fresh = bool(self.jpeg) and time.time() - self.stamp < 0.8
        if not fresh:
            self.make()
        with self.lock:
            return self.jpeg

    def frame(self):
        self.last_use = time.time()
        with self.lock:
            return self.jpeg

    def data(self):
        self.last_use = time.time()
        with self.lock:
            return self.rgb, self.objects

    def annotated(self, kind):
        rgb, objects = self.data()
        if not rgb:
            return b""
        with self.gen_lock:
            canvas = Canvas(CAM_W, CAM_H)
            canvas.buf = bytearray(rgb)
            if kind == "pest":
                for det in objects.get("pest", []):
                    _draw_box(canvas, det["box"], (80, 220, 120))
            else:
                ppe = objects.get("ppe") or {}
                color = (255, 88, 88) if ppe.get("alarm") else (80, 220, 120)
                if ppe.get("person"):
                    _draw_box(canvas, ppe["person"], color)
                if ppe.get("helmet"):
                    _draw_box(canvas, ppe["helmet"], (90, 200, 255))
                if ppe.get("vest"):
                    _draw_box(canvas, ppe["vest"], (255, 190, 80))
            return encode_jpeg(CAM_W, CAM_H, canvas.buf, 58)

    def annotated_cached(self, kind):
        now = time.time()
        with self.lock:
            item = self.ann.get(kind)
        if item and now - item[0] < 1.0:
            return item[1]
        data = self.annotated(kind)
        with self.lock:
            self.ann[kind] = (now, data)
        return data


# ============================================================ 设备状态

DEFAULT_CONFIG = {
    "volDay": 26, "volNight": 16, "sens": 3, "cool": 30, "tracks": 8,
    "qStart": 22, "qEnd": 6, "qEnable": 0,
    "activeMin": 8000, "activeMax": 18000, "trigger": 2500, "ldr": 800,
    "strategy": "radar", "visionCool": 120,
}

LIMITS = {
    "volDay": (0, 30), "volNight": (0, 30), "sens": (1, 8), "cool": (5, 3600),
    "tracks": (1, 99), "qStart": (0, 23), "qEnd": (0, 23), "qEnable": (0, 1),
    "activeMin": (2000, 120000), "activeMax": (2000, 120000),
    "trigger": (500, 10000), "ldr": (0, 4095), "visionCool": (30, 3600),
}


class Device(object):
    def __init__(self):
        self.lock = threading.RLock()
        self.start = time.time()
        self.config = dict(DEFAULT_CONFIG)
        self.state = "IDLE"
        self.active_until = 0.0
        self.cool_until = 0.0
        self.test = 0
        self.test_until = 0.0
        self.track = 3
        self.pulses = 0
        self.vbat = 12.42
        self.lowbat = 0
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def _loop(self):
        while True:
            time.sleep(0.5)
            try:
                self.tick()
            except Exception:
                traceback.print_exc()

    def _hour(self):
        lt = time.localtime()
        return lt.tm_hour + lt.tm_min / 60.0

    def quiet(self):
        if not self.config["qEnable"]:
            return 0
        hour = int(self._hour())
        a, b = self.config["qStart"], self.config["qEnd"]
        if a == b:
            return 0
        inside = (a <= hour < b) if a < b else (hour >= a or hour < b)
        return 1 if inside else 0

    def servo(self, now=None):
        now = now or time.time()
        if self.state == "ACTIVE" or self.test == 3:
            return 90 + int(45 * math.sin(now * 1.1))
        return 90

    def tick(self):
        now = time.time()
        with self.lock:
            if self.test and now >= self.test_until:
                self.test = 0
            if self.state == "ACTIVE" and now >= self.active_until:
                if self.test:
                    self.state = "IDLE"
                else:
                    self.state = "COOLDOWN"
                    self.cool_until = now + self.config["cool"]
            elif self.state == "COOLDOWN" and now >= self.cool_until:
                self.state = "IDLE"

            # 雷达事件（脉冲数仅用于展示）
            if random.random() < 0.55:
                self.pulses += 1
            if self.state == "IDLE" and not self.test:
                chance = 0.015 + 0.012 * self.config["sens"]
                if random.random() < chance:
                    self._drive()
            if self.state == "ACTIVE":
                self.vbat -= 0.003
            else:
                self.vbat += 0.0015
            self.vbat = max(11.2, min(12.9, self.vbat))
            self.lowbat = 1 if self.vbat < 11.65 else 0

    def _drive(self):
        now = time.time()
        self.state = "ACTIVE"
        self.active_until = now + self.config["activeMin"] / 1000.0
        self.track = random.randint(1, max(1, self.config["tracks"]))

    def start_test(self, what):
        now = time.time()
        with self.lock:
            if what == "sound":
                self.test, self.test_until = 1, now + 5
                self.state, self.active_until = "ACTIVE", now + 5
                self.track = random.randint(1, max(1, self.config["tracks"]))
            elif what == "light":
                self.test, self.test_until = 2, now + 4
                self.state, self.active_until = "ACTIVE", now + 4
            elif what == "servo":
                self.test, self.test_until = 3, now + 4
                self.state, self.active_until = "ACTIVE", now + 4
            elif what == "stop":
                self.test = 0
                self.state = "IDLE"
            else:
                self.test = 0
                self._drive()
                self.active_until = now + 5
        return True

    def update_config(self, form):
        with self.lock:
            for key, value in form.items():
                if key == "strategy":
                    if value in ("radar", "vision", "both"):
                        self.config["strategy"] = value
                    continue
                if key not in LIMITS:
                    continue
                try:
                    num = int(float(value))
                except (TypeError, ValueError):
                    continue
                lo, hi = LIMITS[key]
                self.config[key] = max(lo, min(hi, num))
            if self.config["activeMax"] < self.config["activeMin"] + 1000:
                self.config["activeMax"] = self.config["activeMin"] + 1000
        return dict(self.config)

    def reset(self):
        with self.lock:
            self.config = dict(DEFAULT_CONFIG)
            self.state = "IDLE"
            self.test = 0
            self.track = 3
        return True

    def reboot(self):
        with self.lock:
            self.start = time.time()
            self.state = "IDLE"
            self.test = 0
            self.pulses = 0
        return True

    def status(self, ip):
        now = time.time()
        with self.lock:
            hour = self._hour()
            data = {
                "api": 1, "fw": "1.2.0", "state": self.state,
                "vbat": round(self.vbat, 2),
                "night": 1 if (hour < 6 or hour >= 18) else 0,
                "quiet": self.quiet(),
                "pulses": self.pulses,
                "lowBat": self.lowbat,
                "test": self.test,
                "track": self.track,
                "servo": self.servo(now),
                "uptime": int(now - self.start),
                "mode": "STA", "ssid": "Scarecrow-SIM", "rssi": -52,
                "ip": ip,
            }
            for key, value in self.config.items():
                data[key] = value
            return data


# ============================================================ 小车

DEFAULT_ROUTE = {
    "loop": False,
    "waypoints": [
        {"x": 1.5, "y": 2.0, "action": "none", "wait_s": 0},
        {"x": 4.0, "y": 2.0, "action": "spray", "wait_s": 8},
        {"x": 4.0, "y": 5.5, "action": "photo", "wait_s": 3},
        {"x": 1.5, "y": 5.5, "action": "water", "wait_s": 5},
        {"x": 1.5, "y": 3.8, "action": "none", "wait_s": 0},
        {"x": 0.0, "y": 0.0, "action": "none", "wait_s": 0},
    ],
}


class Robot(object):
    def __init__(self):
        self.lock = threading.RLock()
        self.route = json.loads(json.dumps(DEFAULT_ROUTE))
        self.mode = "idle"
        self.x = 0.0
        self.y = 0.0
        self.heading = 90.0
        self.speed = 0.0
        self.battery = 86.0
        self.wp = 0
        self.hold_until = 0.0
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def _loop(self):
        while True:
            time.sleep(0.2)
            try:
                with self.lock:
                    now = time.time()
                    if self.mode == "running":
                        self._step(now, 0.2)
                    elif self.mode == "returning":
                        if self._move_to(0.0, 0.0, 0.2):
                            self.mode = "idle"
                            self.wp = 0
                    if self.mode in ("running", "returning"):
                        self.battery = max(5.0, self.battery - 0.012)
                    elif self.battery < 100:
                        self.battery = min(100.0, self.battery + 0.02)
            except Exception:
                traceback.print_exc()

    def _move_to(self, tx, ty, dt):
        dx = tx - self.x
        dy = ty - self.y
        dist = math.hypot(dx, dy)
        step = 0.45 * dt
        if dist <= max(step, 0.02):
            self.x, self.y = tx, ty
            self.speed = 0.0
            return True
        self.x += dx / dist * step
        self.y += dy / dist * step
        self.speed = 0.45
        self.heading = round((math.degrees(math.atan2(dy, dx)) + 360) % 360, 1)
        return False

    def _step(self, now, dt):
        route = self.route.get("waypoints") or []
        if not route:
            self.mode = "idle"
            self.speed = 0.0
            return
        if self.hold_until:
            if now < self.hold_until:
                self.speed = 0.0
                return
            self.hold_until = 0.0
            self.wp += 1
        if self.wp >= len(route):
            if self.route.get("loop"):
                self.wp = 0
            else:
                self.mode = "returning"
                return
        point = route[self.wp]
        if self._move_to(float(point.get("x", 0)), float(point.get("y", 0)), dt):
            wait = float(point.get("wait_s", 0) or 0)
            if wait > 0:
                self.hold_until = now + min(wait, 600)
            else:
                self.wp += 1
                if self.wp >= len(route) and not self.route.get("loop"):
                    self.mode = "returning"

    def set_route(self, data):
        if not isinstance(data, dict):
            raise ValueError("请求体必须是 JSON 对象")
        points = data.get("waypoints")
        if not isinstance(points, list) or not points:
            raise ValueError("waypoints 不能为空")
        if len(points) > 64:
            raise ValueError("航点最多 64 个")
        clean = []
        for point in points:
            clean.append({
                "x": float(point.get("x", 0)),
                "y": float(point.get("y", 0)),
                "action": str(point.get("action", "none"))[:16],
                "wait_s": max(0.0, min(600.0, float(point.get("wait_s", 0) or 0))),
            })
        with self.lock:
            self.route = {"loop": bool(data.get("loop", False)), "waypoints": clean}
            self.mode = "idle"
            self.wp = 0
            self.hold_until = 0.0
        return len(clean)

    def control(self, action):
        with self.lock:
            points = self.route.get("waypoints") or []
            if action == "start":
                if not points:
                    return {"code": 1, "msg": "路线为空"}
                self.mode = "running"
                self.wp = 0
                self.hold_until = 0.0
            elif action == "pause":
                if self.mode == "running":
                    self.mode = "paused"
                    self.speed = 0.0
            elif action == "resume":
                if self.mode == "paused":
                    self.mode = "running"
            elif action == "stop":
                self.mode = "idle"
                self.speed = 0.0
                self.wp = 0
                self.hold_until = 0.0
            elif action == "home":
                self.mode = "returning"
            else:
                return {"code": 1, "msg": "未知动作"}
            return {"code": 0, "action": action, "mode": self.mode}

    def state(self):
        with self.lock:
            total = len(self.route.get("waypoints") or [])
            if self.mode == "running":
                current = min(self.wp + 1, total)
            elif self.mode == "returning":
                current = total
            else:
                current = 0
            return {
                "code": 0, "mode": self.mode, "waypoint": current, "total": total,
                "x": round(self.x, 2), "y": round(self.y, 2),
                "heading": round(self.heading, 1), "speed": round(self.speed, 2),
                "battery": int(round(self.battery)), "error": "",
            }


# ============================================================ 天气与水阀

class Weather(object):
    def __init__(self):
        self.lock = threading.Lock()
        self.temp = 26.0
        self.humidity = 58
        self.rain = 0.0
        self.wind = 2.1
        self.updated = time.time()
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def _loop(self):
        while True:
            time.sleep(5)
            try:
                self.tick()
            except Exception:
                traceback.print_exc()

    def tick(self):
        now = time.time()
        lt = time.localtime()
        hour = lt.tm_hour + lt.tm_min / 60.0
        temp = 24.0 + 6.0 * math.sin((hour - 9.0) / 24.0 * 2 * math.pi)
        hum = 62.0 - 1.9 * (temp - 20.0) + 5.0 * math.sin(now / 900.0)
        rain = 1.2 if int(now // 300) % 12 == 7 else 0.0
        with self.lock:
            self.temp = round(temp, 1)
            self.humidity = int(max(22, min(96, hum)))
            self.rain = rain
            self.wind = round(1.5 + 1.2 * abs(math.sin(now / 420.0)), 1)
            self.updated = now

    def snapshot(self):
        with self.lock:
            desc = "小雨" if self.rain > 0 else ("晴热" if self.temp > 30 else "多云")
            return {
                "code": 0, "temp": self.temp, "humidity": self.humidity,
                "rain": self.rain, "desc": desc, "wind": self.wind,
                "stale": False, "updated": int(self.updated),
            }


class Valve(object):
    def __init__(self, weather):
        self.weather = weather
        self.lock = threading.Lock()
        self.auto = True
        self.temp_min = 5.0
        self.temp_max = 38.0
        self.humidity_below = 60
        self.respect_rain = True
        self.open = False
        self.reason = "初始关闭"
        self.flow = 0.0
        self.last_open = 0
        self.manual_until = 0.0
        self.hold_closed_until = 0.0
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def _loop(self):
        while True:
            time.sleep(1.0)
            try:
                self.tick()
            except Exception:
                traceback.print_exc()

    def _set(self, opened, reason, now=None):
        self.open = opened
        self.reason = reason
        self.flow = 1.2 if opened else 0.0
        if opened:
            self.last_open = int(now or time.time())

    def tick(self):
        now = time.time()
        w = self.weather.snapshot()
        with self.lock:
            if self.open and w["rain"] > 0 and self.respect_rain:
                self._set(False, "检测到降雨（%.1f mm），安全关阀" % w["rain"], now)
                return
            if self.manual_until:
                if now < self.manual_until:
                    return
                self.manual_until = 0.0
                if self.open:
                    self._set(False, "定时结束，自动关阀", now)
                if self.hold_closed_until:
                    self.hold_closed_until = 0.0
            if self.hold_closed_until and now < self.hold_closed_until:
                return
            if not self.auto:
                return

            if w["humidity"] >= self.humidity_below:
                want, why = False, "湿度 %d%% 高于阈值 %d%%" % (w["humidity"], self.humidity_below)
            elif not (self.temp_min <= w["temp"] <= self.temp_max):
                want, why = False, "温度 %.1f℃ 超出区间 %.0f~%.0f℃" % (
                    w["temp"], self.temp_min, self.temp_max)
            elif self.respect_rain and w["rain"] > 0:
                want, why = False, "正在降雨（%.1f mm），暂不灌溉" % w["rain"]
            else:
                want, why = True, "湿度 %d%% 低于阈值 %d%%，自动开阀" % (
                    w["humidity"], self.humidity_below)

            if want and not self.open:
                self._set(True, why, now)
            elif not want and self.open:
                self._set(False, why, now)
            elif not self.open:
                self.reason = why

    def manual(self, opened, duration):
        now = time.time()
        with self.lock:
            if opened:
                self.manual_until = now + max(0, duration)
                self._set(True, "手动开阀 %d 秒" % duration if duration > 0 else "手动开阀", now)
            else:
                self.manual_until = 0.0
                self.hold_closed_until = now + 60
                self._set(False, "手动关阀（60 秒内不自动开启）", now)
            return self.snapshot_locked(now)

    def configure(self, body):
        with self.lock:
            if "enabled" in body:
                self.auto = bool(body["enabled"])
                # 重新下发自动规则后立即生效，取消手动保持
                self.manual_until = 0.0
                self.hold_closed_until = 0.0
            if "temp_min" in body:
                self.temp_min = float(body["temp_min"])
            if "temp_max" in body:
                self.temp_max = float(body["temp_max"])
            if "humidity_below" in body:
                self.humidity_below = int(body["humidity_below"])
            if "respect_rain" in body:
                self.respect_rain = bool(body["respect_rain"])
            return self.snapshot_locked(time.time())

    def snapshot_locked(self, now):
        return {
            "code": 0, "open": self.open, "auto": self.auto,
            "mode": "manual" if self.manual_until > now else ("auto" if self.auto else "idle"),
            "flow": self.flow, "reason": self.reason,
            "last_open": self.last_open,
            "temp_min": self.temp_min, "temp_max": self.temp_max,
            "humidity_below": self.humidity_below, "respect_rain": self.respect_rain,
        }

    def snapshot(self):
        with self.lock:
            return self.snapshot_locked(time.time())


# ============================================================ 全局对象

camera = Camera()
device = Device()
robot = Robot()
weather = Weather()
valve = Valve(weather)

VERBOSE = False
ADVERTISE = ""


def guess_ip():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except Exception:
        return "127.0.0.1"


def request_host(handler):
    if ADVERTISE:
        return ADVERTISE
    host = handler.headers.get("Host")
    if host:
        return host
    return "%s:%d" % (guess_ip(), handler.server.server_port)


# ============================================================ 视觉结果

def jpeg_size(data):
    if not data or data[:2] != b"\xff\xd8":
        return None
    i = 2
    while i + 9 < len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        seglen = (data[i + 2] << 8) | data[i + 3]
        if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                      0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            h = (data[i + 5] << 8) | data[i + 6]
            w = (data[i + 7] << 8) | data[i + 8]
            return w, h
        i += 2 + seglen
    return None


def png_size(data):
    if len(data) > 24 and data[:8] == b"\x89PNG\r\n\x1a\n" and data[12:16] == b"IHDR":
        w = (data[16] << 24) | (data[17] << 16) | (data[18] << 8) | data[19]
        h = (data[20] << 24) | (data[21] << 16) | (data[22] << 8) | data[23]
        return w, h
    return None


def image_size(data):
    return jpeg_size(data) or png_size(data)


def extract_image(content_type, body):
    ctype = (content_type or "").lower()
    if "multipart/form-data" in ctype:
        marker = "boundary="
        pos = ctype.find(marker)
        if pos < 0:
            return b""
        boundary = content_type.strip()[pos + len(marker):].strip().strip('"')
        sep = ("--" + boundary).encode("utf-8")
        for part in body.split(sep):
            head_end = part.find(b"\r\n\r\n")
            if head_end < 0:
                continue
            head = part[:head_end].lower()
            if b'name="image"' in head or b"name=image" in head:
                return part[head_end + 4:].rstrip(b"\r\n")
        return b""
    if ctype.startswith("image/"):
        return body
    # 部分客户端不带 Content-Type，直接按原始图片处理
    if body[:2] == b"\xff\xd8" or body[:8] == b"\x89PNG\r\n\x1a\n":
        return body
    return b""


def vision_result(kind, width, height):
    _, objects = camera.data()
    sx = width / float(CAM_W)
    sy = height / float(CAM_H)

    def scale(box):
        return [int(box[0] * sx), int(box[1] * sy), int(box[2] * sx), int(box[3] * sy)]

    if kind == "pest":
        dets = []
        for det in objects.get("pest", []):
            dets.append({
                "label": det["label"], "label_en": det["label_en"],
                "confidence": det["confidence"], "box": scale(det["box"]),
            })
        return {
            "code": 0, "kind": "pest", "model": "sim-yolov8n-pest.pt",
            "fallback": False, "simulated": True,
            "cost_ms": random.randint(18, 46),
            "image_w": width, "image_h": height, "detections": dets,
        }

    ppe = objects.get("ppe") or {}
    dets = []
    person = ppe.get("person")
    if person:
        dets.append({"label": "人员", "label_en": "person",
                     "confidence": 0.93, "box": scale(person)})
        if ppe.get("helmet"):
            dets.append({"label": "安全帽", "label_en": "helmet",
                         "confidence": 0.90, "box": scale(ppe["helmet"])})
        else:
            x1, y1, x2, y2 = scale(person)
            dets.append({"label": "未戴安全帽", "label_en": "no_helmet",
                         "confidence": 0.88,
                         "box": [x1 + 2, y1 + 1, x2 - 2, y1 + max(8, (y2 - y1) // 5)]})
        if ppe.get("vest"):
            dets.append({"label": "反光衣", "label_en": "vest",
                         "confidence": 0.89, "box": scale(ppe["vest"])})
        else:
            x1, y1, x2, y2 = scale(person)
            dets.append({"label": "未穿反光衣", "label_en": "no_vest",
                         "confidence": 0.86,
                         "box": [x1 + 2, y1 + (y2 - y1) // 2, x2 - 2, y2 - 2]})
    return {
        "code": 0, "kind": "ppe", "model": "sim-yolov8n-ppe.pt",
        "fallback": False, "simulated": True,
        "cost_ms": random.randint(20, 52),
        "image_w": width, "image_h": height,
        "person_count": 1 if person else 0,
        "alarm": bool(ppe.get("alarm")),
        "detections": dets,
    }


# ============================================================ 页面

DASHBOARD = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>稻草人仿真设备</title>
<style>
  * { box-sizing: border-box; }
  body { margin:0; background:#0b1220; color:#e6edf6;
         font-family:"Microsoft YaHei UI","PingFang SC",system-ui,sans-serif; }
  header { padding:18px 24px; border-bottom:1px solid #1e2b42;
           display:flex; align-items:center; gap:12px; flex-wrap:wrap; }
  h1 { font-size:20px; margin:0; font-weight:600; letter-spacing:.5px; }
  .tag { font-size:12px; padding:3px 9px; border-radius:10px;
         background:#16233a; color:#8fa6c4; border:1px solid #22314b; }
  .dot { width:9px; height:9px; border-radius:50%; background:#3b4a63; display:inline-block; }
  .dot.on { background:#35d07f; box-shadow:0 0 8px #35d07f; }
  .dot.off { background:#e05252; }
  main { max-width:1100px; margin:0 auto; padding:20px 24px 48px; }
  .grid { display:grid; grid-template-columns: 420px 1fr; gap:18px; }
  @media (max-width: 880px) { .grid { grid-template-columns:1fr; } }
  .card { background:#111c2f; border:1px solid #1e2b42; border-radius:12px; padding:16px; }
  .card h2 { font-size:14px; margin:0 0 12px; color:#9db2cf; font-weight:600; }
  .cam { width:100%; border-radius:8px; background:#0a0f1a; display:block;
         image-rendering:auto; }
  .kv { display:grid; grid-template-columns: 96px 1fr; gap:8px 10px; font-size:13px; }
  .kv span:nth-child(odd) { color:#7f94b3; }
  .big { font-size:22px; font-weight:600; color:#7fe0b0; }
  .addr { font-family:Consolas,monospace; font-size:15px; color:#7fb4ff;
          background:#0c1626; border:1px solid #22314b; border-radius:8px;
          padding:9px 12px; display:inline-block; }
  .row { display:flex; gap:10px; flex-wrap:wrap; margin-top:12px; }
  button { background:#1d3a63; color:#dbe9ff; border:1px solid #2b4f80;
           border-radius:8px; padding:9px 14px; font-size:13px; cursor:pointer; }
  button:hover { background:#234776; }
  button.g { background:#154a35; border-color:#1f6b4b; }
  button.r { background:#4a1c1c; border-color:#6e2a2a; }
  .muted { color:#7f94b3; font-size:12px; line-height:1.7; }
  table { width:100%; border-collapse:collapse; font-size:12.5px; }
  td { padding:6px 4px; border-bottom:1px solid #172338; color:#b9c9dd; }
  td:first-child { font-family:Consolas,monospace; color:#7fb4ff; white-space:nowrap; }
  code { font-family:Consolas,monospace; color:#7fb4ff; }
</style></head>
<body>
<header>
  <h1>稻草人仿真设备</h1>
  <span class="tag">v__VERSION__</span>
  <span class="tag">固件 1.2.0（模拟）</span>
  <span class="tag">端口 __PORT__</span>
  <span class="dot" id="online"></span>
</header>
<main>
  <div class="card" style="margin-bottom:18px">
    <h2>客户端填写这个地址</h2>
    <div class="addr">__NOSCHEME__</div>
    <div class="muted" style="margin-top:10px">
      Windows 主界面右上角地址框、Android 首屏地址框填上面的值即可；
      「扩展功能」里的摄像头与 AI 服务地址默认跟随设备地址。
      完整地址：<code>__URL__</code>
    </div>
  </div>

  <div class="grid">
    <div class="card">
      <h2>实时画面（仿真生成）</h2>
      <img class="cam" id="cam" src="/api/camera/stream" alt="camera">
      <div class="muted" style="margin-top:8px">
        画面由服务器逐帧绘制并编码为 JPEG，不是真实摄像头；
        识别结果为模拟数据，用于联调界面与流程。
      </div>
    </div>

    <div>
      <div class="card" style="margin-bottom:18px">
        <h2>设备状态</h2>
        <div class="kv">
          <span>运行状态</span><span class="big" id="state">-</span>
          <span>电池电压</span><span id="vbat">-</span>
          <span>雷达脉冲</span><span id="pulses">-</span>
          <span>触发策略</span><span id="strategy">-</span>
          <span>运行时长</span><span id="uptime">-</span>
          <span>水阀</span><span id="valve">-</span>
          <span>小车</span><span id="robot">-</span>
        </div>
        <div class="row">
          <button class="g" onclick="act('/api/test?what=all','')">立即驱赶</button>
          <button onclick="act('/api/robot/control','{\"action\":\"start\"}')">开始巡逻</button>
          <button onclick="act('/api/valve','{\"open\":true,\"duration_s\":30}')">开阀 30 秒</button>
          <button class="r" onclick="act('/api/valve','{\"open\":false,\"duration_s\":0}')">关闭水阀</button>
        </div>
      </div>

      <div class="card">
        <h2>接口</h2>
        <table>
          <tr><td>GET /api/status</td><td>设备状态</td></tr>
          <tr><td>GET /api/config</td><td>读取参数</td></tr>
          <tr><td>POST /api/config</td><td>保存参数（form）</td></tr>
          <tr><td>GET /api/camera/stream</td><td>MJPEG 实时画面</td></tr>
          <tr><td>GET /api/camera/snapshot</td><td>单张 JPEG</td></tr>
          <tr><td>POST /api/vision/detect?kind=pest|ppe</td><td>视觉识别（模拟）</td></tr>
          <tr><td>GET /api/vision/stream?kind=</td><td>带框标注流</td></tr>
          <tr><td>GET/POST /api/robot/route</td><td>路线读写</td></tr>
          <tr><td>POST /api/robot/control</td><td>启动 / 暂停 / 停止 / 回原点</td></tr>
          <tr><td>GET/POST /api/valve</td><td>水阀状态与控制</td></tr>
          <tr><td>POST /api/valve/auto</td><td>自动灌溉规则</td></tr>
        </table>
      </div>
    </div>
  </div>
</main>
<script>
function fmt(s){ s=Math.max(0,s|0); var h=(s/3600)|0, m=((s%3600)/60)|0, x=s%60;
  return (h?h+' 小时 ':'') + m + ' 分 ' + x + ' 秒'; }
async function act(url, body){
  try{
    await fetch(url, {method:'POST', body: body,
      headers: body ? {'Content-Type':'application/json'} : {}});
    poll();
  }catch(e){ alert('请求失败：'+e); }
}
async function poll(){
  try{
    const s = await (await fetch('/api/status')).json();
    document.getElementById('state').textContent = s.state;
    document.getElementById('vbat').textContent = Number(s.vbat).toFixed(2) + ' V';
    document.getElementById('pulses').textContent = s.pulses;
    document.getElementById('strategy').textContent = s.strategy;
    document.getElementById('uptime').textContent = fmt(s.uptime);
    const v = await (await fetch('/api/valve')).json();
    document.getElementById('valve').textContent = (v.open?'开阀':'关阀') + ' · ' + v.reason;
    const r = await (await fetch('/api/robot/state')).json();
    document.getElementById('robot').textContent =
      r.mode + ' · 航点 ' + r.waypoint + '/' + r.total +
      ' · (' + Number(r.x).toFixed(1) + ', ' + Number(r.y).toFixed(1) + ')';
    document.getElementById('online').className = 'dot on';
  }catch(e){
    document.getElementById('online').className = 'dot off';
  }
}
setInterval(poll, 2000); poll();
</script>
</body></html>
"""


def dashboard_html(handler):
    host = request_host(handler)
    return (DASHBOARD
            .replace("__VERSION__", VERSION)
            .replace("__PORT__", str(handler.server.server_port))
            .replace("__NOSCHEME__", host)
            .replace("__URL__", "http://" + host + "/"))


# ============================================================ HTTP

class Server(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class Handler(BaseHTTPRequestHandler):
    server_version = "ScarecrowSim/" + VERSION
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        if VERBOSE:
            sys.stderr.write("[%s] %s\n" % (time.strftime("%H:%M:%S"), fmt % args))

    # ---------- 响应 ----------

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, obj, code=200):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self._cors()
        self.end_headers()
        if self.command != "HEAD":
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass

    def _html(self, text):
        data = text.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self._cors()
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _jpeg(self, data):
        if not data:
            self._json({"code": 503, "msg": "画面尚未就绪"}, 503)
            return
        self.send_response(200)
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self._cors()
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _mjpeg(self, getter, interval):
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Connection", "close")
        self._cors()
        self.end_headers()
        self.close_connection = True
        try:
            while True:
                data = getter()
                if data:
                    head = ("--frame\r\nContent-Type: image/jpeg\r\nContent-Length: %d\r\n\r\n"
                            % len(data)).encode("ascii")
                    self.wfile.write(head)
                    self.wfile.write(data)
                    self.wfile.write(b"\r\n")
                    self.wfile.flush()
                time.sleep(interval)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass

    def _read_body(self, limit=20 * 1024 * 1024):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except (TypeError, ValueError):
            length = 0
        if length <= 0:
            return b""
        if length > limit:
            self._json({"code": 413, "msg": "请求体过大"}, 413)
            return None
        data = b""
        while len(data) < length:
            chunk = self.rfile.read(min(65536, length - len(data)))
            if not chunk:
                break
            data += chunk
        return data

    # ---------- GET ----------

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)
        try:
            if path == "/":
                self._html(dashboard_html(self))
            elif path in ("/healthz", "/api/ping"):
                self._json({"ok": 1, "version": VERSION,
                            "uptime": int(time.time() - device.start)})
            elif path == "/api/status":
                self._json(device.status(request_host(self)))
            elif path == "/api/config":
                cfg = dict(device.config)
                self._json(cfg)
            elif path == "/api/vision/capabilities":
                self._json({
                    "code": 0, "engine": "yolov8", "simulated": True,
                    "imgsz": 640, "device": "sim",
                    "models": {
                        "pest": {"weights": "sim/pest.pt", "exists": True,
                                 "loaded": True, "model": "sim-yolov8n-pest.pt", "conf": 0.35},
                        "ppe": {"weights": "sim/ppe.pt", "exists": True,
                                "loaded": True, "model": "sim-yolov8n-ppe.pt", "conf": 0.35},
                    },
                })
            elif path == "/api/camera/snapshot":
                self._jpeg(camera.snapshot())
            elif path == "/api/camera/stream":
                camera.viewers += 1
                try:
                    self._mjpeg(camera.frame, 0.42)
                finally:
                    camera.viewers -= 1
            elif path == "/api/vision/stream":
                kind = (query.get("kind", ["ppe"])[0] or "ppe")
                if kind not in ("pest", "ppe"):
                    self._json({"code": 400, "msg": "kind 必须是 pest 或 ppe"}, 400)
                    return
                camera.viewers += 1
                try:
                    self._mjpeg(lambda: camera.annotated_cached(kind), 1.0)
                finally:
                    camera.viewers -= 1
            elif path == "/api/robot/state":
                self._json(robot.state())
            elif path == "/api/robot/route":
                with robot.lock:
                    route = {
                        "code": 0,
                        "loop": bool(robot.route.get("loop", False)),
                        "waypoints": [dict(p) for p in robot.route.get("waypoints", [])],
                    }
                self._json(route)
            elif path == "/api/weather":
                self._json(weather.snapshot())
            elif path == "/api/valve":
                self._json(valve.snapshot())
            elif path == "/api/test":
                device.start_test((query.get("what", ["all"])[0] or "all").lower())
                self._json({"ok": 1})
            elif path == "/test":
                device.start_test("all")
                self._json({"ok": 1})
            elif path == "/reset":
                device.reset()
                self._json({"ok": 1})
            elif path == "/api/device/info":
                self._json({"code": 0, "name": "Scarecrow-SIM", "fw": "1.2.0",
                            "api": 1, "host": request_host(self)})
            else:
                self._json({"code": 404, "msg": "接口不存在"}, 404)
        except Exception as exc:
            traceback.print_exc()
            try:
                self._json({"code": 500, "msg": str(exc)}, 500)
            except Exception:
                pass

    # ---------- POST ----------

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)
        body = self._read_body()
        if body is None:
            return
        ctype = (self.headers.get("Content-Type") or "").lower()

        try:
            if path in ("/api/config", "/save"):
                form = {}
                for key, values in urllib.parse.parse_qs(
                        body.decode("utf-8", "replace")).items():
                    if values:
                        form[key] = values[0]
                device.update_config(form)
                self._json(device.status(request_host(self)))
            elif path == "/api/test":
                what = (query.get("what", ["all"])[0] or "all").lower()
                device.start_test(what)
                self._json({"ok": 1})
            elif path == "/api/reset":
                device.reset()
                self._json({"ok": 1})
            elif path == "/api/reboot":
                device.reboot()
                self._json({"ok": 1, "reboot": 1})
            elif path == "/api/robot/route":
                try:
                    data = json.loads(body.decode("utf-8") or "{}")
                    total = robot.set_route(data)
                    self._json({"code": 0, "total": total})
                except (ValueError, TypeError, json.JSONDecodeError) as exc:
                    self._json({"code": 1, "msg": str(exc)}, 400)
            elif path == "/api/robot/control":
                try:
                    data = json.loads(body.decode("utf-8") or "{}")
                except json.JSONDecodeError:
                    data = {}
                action = str(data.get("action", ""))
                result = robot.control(action)
                self._json(result, 200 if result.get("code") == 0 else 400)
            elif path == "/api/valve":
                try:
                    data = json.loads(body.decode("utf-8") or "{}")
                except json.JSONDecodeError:
                    data = {}
                result = valve.manual(bool(data.get("open", False)),
                                      int(data.get("duration_s", 0) or 0))
                self._json(result)
            elif path == "/api/valve/auto":
                try:
                    data = json.loads(body.decode("utf-8") or "{}")
                except json.JSONDecodeError:
                    data = {}
                self._json(valve.configure(data))
            elif path == "/api/vision/detect":
                kind = (query.get("kind", ["pest"])[0] or "pest").lower()
                if kind not in ("pest", "ppe"):
                    self._json({"code": 400, "msg": "kind 必须是 pest 或 ppe"}, 400)
                    return
                image = extract_image(ctype, body)
                if not image:
                    self._json({"code": 400, "msg": "没有收到图片字段 image"}, 400)
                    return
                size = image_size(image) or (CAM_W, CAM_H)
                self._json(vision_result(kind, size[0], size[1]))
            else:
                self._json({"code": 404, "msg": "接口不存在"}, 404)
        except Exception as exc:
            traceback.print_exc()
            try:
                self._json({"code": 500, "msg": str(exc)}, 500)
            except Exception:
                pass

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_HEAD(self):
        self.do_GET()


# ============================================================ 启动

def main():
    global VERBOSE, ADVERTISE

    parser = argparse.ArgumentParser(description="稻草人驱鸟控制器 · 公网仿真设备")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址，默认 0.0.0.0")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="监听端口，默认 1819")
    parser.add_argument("--advertise", default="",
                        help="对外展示的地址，如 47.94.214.62:1819；留空则按请求 Host 自动识别")
    parser.add_argument("--verbose", action="store_true", help="打印访问日志")
    parser.add_argument("--render", default="", help="只渲染一张画面到指定 jpg 后退出")
    args = parser.parse_args()

    VERBOSE = args.verbose
    ADVERTISE = args.advertise.strip()

    if args.render:
        started = time.time()
        canvas, _ = render_scene(0.0)
        data = encode_jpeg(CAM_W, CAM_H, canvas.buf, 66)
        with open(args.render, "wb") as fp:
            fp.write(data)
        print("已生成 %s  %dx%d  %.1f KB  %.0f ms" % (
            args.render, CAM_W, CAM_H, len(data) / 1024.0,
            (time.time() - started) * 1000))
        return

    server = Server((args.host, args.port), Handler)
    shown = ADVERTISE or ("%s:%d" % (guess_ip(), args.port))
    print("稻草人仿真设备 v%s" % VERSION)
    print("监听      http://%s:%d" % (args.host, args.port))
    print("访问面板  http://%s/" % shown)
    print("客户端填  %s" % shown)
    print("公网部署时请确认安全组 / 防火墙已放开 TCP %d" % args.port)
    sys.stdout.flush()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
