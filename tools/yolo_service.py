#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YOLOv8 实时识别服务（Windows / Android 客户端共用）

安装依赖：
    pip install -r tools/requirements-yolo.txt

启动：
    python tools/yolo_service.py --port 8000
    python tools/yolo_service.py --source "http://192.168.4.1:81/stream" --port 8000

接口：
    GET  /health
    GET  /api/vision/capabilities
    POST /api/vision/detect?kind=pest|ppe     multipart/form-data，字段名 image
    GET  /api/vision/stream?kind=ppe&src=...  MJPEG 标注流（服务器端绘制检测框）

模型配置见 tools/yolo_models.json。
注意：COCO 预训练权重不包含病虫害 / 安全帽类别，需要换成自己训练的 .pt。
"""

import argparse
import json
import os
import socket
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DEFAULT_CONFIG = {
    "pest": {
        "weights": "models/pest.pt",
        "conf": 0.35,
        "labels": {},
        "alarm_classes": [],
        "severity": {"low": 0.005, "high": 0.02},
    },
    "ppe": {
        "weights": "models/ppe.pt",
        "conf": 0.35,
        "required": ["helmet", "vest"],
        "person_classes": ["person", "worker", "farmer"],
        "helmet_classes": ["helmet", "hardhat", "hard_hat", "safety_helmet"],
        "vest_classes": ["vest", "safety_vest", "reflective_vest", "hi_vis", "hivis"],
        "helmet_missing_classes": ["no_helmet", "no_hardhat", "without_helmet", "bare_head"],
        "vest_missing_classes": ["no_vest", "no_safety_vest", "without_vest"],
        "labels": {
            "helmet": "安全帽",
            "hardhat": "安全帽",
            "safety_helmet": "安全帽",
            "no_helmet": "未戴安全帽",
            "no_hardhat": "未戴安全帽",
            "vest": "防护服",
            "safety_vest": "防护服",
            "reflective_vest": "防护服",
            "no_vest": "未穿防护服",
            "person": "人员",
            "worker": "作业人员",
            "farmer": "作业人员",
        },
        "alarm_classes": ["no_helmet", "no_vest", "no_hardhat", "without_helmet"],
        "assume_missing_when_absent": True,
    },
}

_cv = None
_np = None


def ensure_cv():
    """延迟导入 OpenCV / numpy，未安装时接口仍可返回明确错误。"""
    global _cv, _np
    if _cv is None:
        import cv2
        import numpy

        _cv, _np = cv2, numpy
    return _cv, _np


def normalize(name):
    return str(name).strip().lower().replace("-", "_").replace(" ", "_")


class ModelBox:
    def __init__(self, kind, cfg, imgsz, device):
        self.kind = kind
        self.weights = cfg.get("weights", "models/%s.pt" % kind)
        self.conf = float(cfg.get("conf", 0.35))
        self.labels = cfg.get("labels") or {}
        self.alarm_classes = set(normalize(x) for x in cfg.get("alarm_classes") or [])
        self.required = [normalize(x) for x in cfg.get("required") or []]
        self.person_classes = set(normalize(x) for x in
                                  cfg.get("person_classes") or ["person"])
        self.helmet_classes = set(normalize(x) for x in
                                  cfg.get("helmet_classes") or ["helmet", "hardhat"])
        self.vest_classes = set(normalize(x) for x in
                                cfg.get("vest_classes") or ["vest", "safety_vest"])
        self.helmet_missing = set(normalize(x) for x in
                                  cfg.get("helmet_missing_classes") or
                                  ["no_helmet", "no_hardhat", "without_helmet"])
        self.vest_missing = set(normalize(x) for x in
                                cfg.get("vest_missing_classes") or
                                ["no_vest", "without_vest"])
        self.assume_missing = bool(cfg.get("assume_missing_when_absent", True))
        sev = cfg.get("severity") or {}
        self.sev_low = float(sev.get("low", 0.005))
        self.sev_high = float(sev.get("high", 0.02))
        self.imgsz = imgsz
        self.device = device
        self.ppe_ready = False
        self.class_names = set()

        self.model = None
        self.lock = threading.Lock()
        self.loaded_name = ""
        self.fallback = False
        self.error = None

    def resolve_path(self):
        path = self.weights
        if not os.path.isabs(path):
            path = os.path.join(BASE_DIR, path)
        return path

    def load(self):
        if self.model is not None:
            return self.model
        with self.lock:
            if self.model is not None:
                return self.model
            try:
                from ultralytics import YOLO
            except ImportError as exc:
                self.error = (
                    "缺少 ultralytics，请先执行 pip install -r tools/requirements-yolo.txt"
                    "（%s）" % exc
                )
                raise RuntimeError(self.error)

            path = self.resolve_path()
            if not os.path.exists(path):
                if self.kind == "ppe":
                    path = "yolov8n.pt"
                    self.fallback = True
                else:
                    self.error = "模型文件不存在：%s" % path
                    raise FileNotFoundError(self.error)

            try:
                self.model = YOLO(path)
                self.loaded_name = os.path.basename(path)
                self.error = None
                names = getattr(self.model, "names", None) or {}
                if not isinstance(names, dict):
                    names = dict(enumerate(names))
                self.class_names = set(normalize(v) for v in names.values())
                # COCO 的 person 权重没有安全帽/防护服类别，不能判断穿戴情况。
                self.ppe_ready = bool(
                    (self.class_names & self.helmet_classes)
                    or (self.class_names & self.vest_classes)
                    or (self.class_names & self.helmet_missing)
                    or (self.class_names & self.vest_missing)
                )
            except Exception as exc:
                self.error = "加载模型失败：%s" % exc
                raise
            return self.model

    def describe(self):
        path = self.resolve_path()
        info = {
            "weights": path,
            "exists": os.path.exists(path),
            "loaded": self.model is not None,
            "model": self.loaded_name,
            "conf": self.conf,
            "required": self.required,
            "classes": sorted(self.class_names),
        }
        if self.kind == "ppe":
            info["ppe_ready"] = self.ppe_ready
        if not info["exists"] and self.kind == "ppe":
            info["fallback"] = "yolov8n.pt（仅能识别 person，需自训练安全帽/防护服权重）"
        if self.error:
            info["error"] = self.error
        return info

    def predict(self, image):
        """image: numpy BGR 图。返回协议 JSON。"""
        model = self.load()
        started = time.time()
        with self.lock:
            results = model.predict(
                image,
                imgsz=self.imgsz,
                conf=self.conf,
                iou=0.45,
                device=self.device,
                verbose=False,
            )
        cost_ms = int((time.time() - started) * 1000)

        result = results[0]
        names = result.names
        if not isinstance(names, dict):
            names = dict(enumerate(names))

        detections = []
        alarm = False

        for box in result.boxes:
            cls_id = int(box.cls.item())
            name_en = str(names.get(cls_id, cls_id))
            key = normalize(name_en)
            score = float(box.conf.item())
            if box.xyxy.shape[0] == 0:
                continue
            x1, y1, x2, y2 = [float(v) for v in box.xyxy[0].tolist()]

            label = self.labels.get(name_en) or self.labels.get(key) or name_en
            detections.append(
                {
                    "label": label,
                    "label_en": name_en,
                    "key": key,
                    "confidence": round(score, 4),
                    "box": [int(x1), int(y1), int(x2), int(y2)],
                }
            )
            if key in self.alarm_classes and score >= 0.5:
                alarm = True

        height, width = image.shape[:2]
        payload = {
            "code": 0,
            "kind": self.kind,
            "model": self.loaded_name,
            "fallback": self.fallback,
            "cost_ms": cost_ms,
            "image_w": int(width),
            "image_h": int(height),
            "detections": detections,
        }

        if self.kind == "ppe":
            payload.update(self.analyze_ppe(detections, width, height))
            payload["alarm"] = bool(payload["alarm"] or alarm)
        elif self.kind == "pest":
            payload.update(self.analyze_pest(detections, width, height))
            payload["alarm"] = alarm or payload.get("severity") == "high"
        else:
            payload["alarm"] = alarm

        payload["summary"] = self.summary(payload)
        return payload

    # ------------------------------------------------------------ 穿戴 / 病虫害分析

    @staticmethod
    def _center(box):
        return ((box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0)

    @staticmethod
    def _inside(point, box, margin=0.08):
        x, y = point
        w = max(1.0, box[2] - box[0])
        h = max(1.0, box[3] - box[1])
        return (box[0] - w * margin <= x <= box[2] + w * margin
                and box[1] - h * margin <= y <= box[3] + h * margin)

    def _belongs(self, item, person_box):
        return self._inside(self._center(item["box"]), person_box)

    def analyze_ppe(self, detections, width, height):
        """把安全帽 / 防护服检测结果关联到每个人，输出穿戴合规情况。"""
        persons = [d for d in detections if d["key"] in self.person_classes]
        helmets = [d for d in detections if d["key"] in self.helmet_classes]
        vests = [d for d in detections if d["key"] in self.vest_classes]
        no_helmets = [d for d in detections if d["key"] in self.helmet_missing]
        no_vests = [d for d in detections if d["key"] in self.vest_missing]

        know_helmet = self.ppe_ready and bool(self.helmet_classes & self.class_names)
        know_vest = self.ppe_ready and bool(self.vest_classes & self.class_names)
        # 配置了 required，但权重里既没有正类也没有负类，则无法判断。
        judge_helmet = "helmet" in self.required and (
            know_helmet or bool(self.helmet_missing & self.class_names))
        judge_vest = "vest" in self.required and (
            know_vest or bool(self.vest_missing & self.class_names))

        wearing = []
        violations = 0
        missing_helmet = 0
        missing_vest = 0

        for person in persons:
            pbox = person["box"]
            has_helmet = any(self._belongs(h, pbox) for h in helmets)
            has_vest = any(self._belongs(v, pbox) for v in vests)
            bad_helmet = any(self._belongs(n, pbox) for n in no_helmets)
            bad_vest = any(self._belongs(n, pbox) for n in no_vests)

            if bad_helmet:
                has_helmet = False
            if bad_vest:
                has_vest = False

            missing = []
            if judge_helmet and not has_helmet and (self.assume_missing or bad_helmet):
                missing.append("安全帽")
                missing_helmet += 1
            if judge_vest and not has_vest and (self.assume_missing or bad_vest):
                missing.append("防护服")
                missing_vest += 1

            compliant = len(missing) == 0
            if not compliant:
                violations += 1
            wearing.append(
                {
                    "box": pbox,
                    "helmet": (has_helmet if judge_helmet else None),
                    "vest": (has_vest if judge_vest else None),
                    "compliant": compliant,
                    "missing": missing,
                    "status": "穿戴合规" if compliant else "缺少" + "、".join(missing),
                }
            )

        # 没有人员框时，单独的"未戴安全帽/未穿防护服"检测同样报警。
        if not persons and (no_helmets or no_vests):
            violations = 1
            missing_helmet = 1 if no_helmets else 0
            missing_vest = 1 if no_vests else 0

        return {
            "person_count": len(persons),
            "ppe_ready": self.ppe_ready,
            "judge_helmet": judge_helmet,
            "judge_vest": judge_vest,
            "wearing": {
                "total": len(persons),
                "compliant": max(0, len(persons) - violations),
                "violations": violations,
                "missing_helmet": missing_helmet,
                "missing_vest": missing_vest,
            },
            "persons": wearing,
            "alarm": violations > 0 or bool(no_helmets) or bool(no_vests),
        }

    def analyze_pest(self, detections, width, height):
        area = 0.0
        for det in detections:
            x1, y1, x2, y2 = det["box"]
            area += max(0.0, (x2 - x1)) * max(0.0, (y2 - y1))
        ratio = area / float(max(1, width * height))

        low = self.sev_low
        high = self.sev_high
        if not detections:
            severity = "none"
        elif ratio < low:
            severity = "low"
        elif ratio < high:
            severity = "moderate"
        else:
            severity = "high"

        return {
            "pest_count": len(detections),
            "pest_ratio": round(ratio, 4),
            "severity": severity,
        }

    def summary(self, payload):
        if self.kind == "ppe":
            wearing = payload.get("wearing") or {}
            total = wearing.get("total", 0)
            bad = wearing.get("violations", 0)
            if not payload.get("ppe_ready"):
                return "识别到 %d 人（当前权重未包含穿戴类别，无法判断穿戴）" % total
            if total == 0 and bad:
                return "检测到未规范穿戴"
            if bad == 0:
                return "人员 %d 人，穿戴全部合规" % total
            return "人员 %d 人，%d 人穿戴不合规" % (total, bad)
        if self.kind == "pest":
            count = payload.get("pest_count", 0)
            names = {"none": "未见明显病虫害", "low": "轻微", "moderate": "中等",
                     "high": "严重"}
            return "识别到 %d 处，风险等级：%s" % (
                count, names.get(payload.get("severity"), "未知"))
        return ""

    def detect_bytes(self, data):
        cv, np = ensure_cv()
        array = np.frombuffer(data, dtype=np.uint8)
        image = cv.imdecode(array, cv.IMREAD_COLOR)
        if image is None:
            raise ValueError("无法解码图片，请确认是 JPEG/PNG")
        return self.predict(image)


class Service:
    def __init__(self, config_path, imgsz, device, source):
        self.imgsz = imgsz
        self.device = device
        self.source = source
        self.models = {}

        data = DEFAULT_CONFIG
        if config_path and os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)

        for kind, cfg in data.items():
            self.models[kind] = ModelBox(kind, cfg, imgsz, device)

    def get(self, kind):
        box = self.models.get(kind)
        if box is None:
            raise KeyError(kind)
        return box

    def capabilities(self):
        return {
            "code": 0,
            "engine": "yolov8",
            "imgsz": self.imgsz,
            "device": self.device,
            "source": self.source,
            "models": {kind: box.describe() for kind, box in self.models.items()},
        }


def extract_image(content_type, body):
    """支持 multipart/form-data（字段 image）和直接提交 image/jpeg。"""
    content_type = content_type or ""
    lowered = content_type.lower()
    if lowered.startswith("image/"):
        return body
    if "multipart/form-data" not in lowered:
        return None

    boundary = None
    for part in content_type.split(";"):
        part = part.strip()
        if part.lower().startswith("boundary="):
            boundary = part.split("=", 1)[1].strip().strip('"')
            break
    if not boundary:
        return None

    separator = b"--" + boundary.encode("ascii", "ignore")
    for chunk in body.split(separator):
        if b"\r\n\r\n" not in chunk:
            continue
        head, data = chunk.split(b"\r\n\r\n", 1)
        if b'name="image"' not in head:
            continue
        if data.endswith(b"\r\n"):
            data = data[:-2]
        return data
    return None


def draw_boxes(cv, frame, result):
    alarm = bool(result.get("alarm"))
    green = (60, 190, 120)
    red = (40, 40, 220)
    amber = (60, 170, 240)
    person_status = {}
    for person in result.get("persons") or []:
        person_status[tuple(person.get("box") or [])] = person

    for det in result.get("detections", []):
        x1, y1, x2, y2 = det.get("box", [0, 0, 0, 0])
        color = red if alarm else green
        text = "%s %.0f%%" % (det.get("label_en", ""), det.get("confidence", 0) * 100)
        status = person_status.get(tuple(det.get("box") or []))
        if status is not None:
            color = green if status.get("compliant") else red
            text = status.get("status", text)
        cv.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        ty = max(18, y1 - 6)
        cv.putText(frame, text, (x1 + 2, ty), cv.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

    label = "ALARM" if alarm else "YOLOv8"
    color = red if alarm else green
    cv.putText(frame, label, (10, 24), cv.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    summary = result.get("summary")
    if summary:
        cv.putText(frame, summary.encode("ascii", "ignore").decode("ascii") or "detecting",
                   (10, 48), cv.FONT_HERSHEY_SIMPLEX, 0.5, amber, 1)


VERBOSE = False


class Handler(BaseHTTPRequestHandler):
    server_version = "ScarecrowYOLO/1.0"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        if VERBOSE:
            sys.stderr.write("[%s] %s\n" % (time.strftime("%H:%M:%S"), fmt % args))

    def send_json(self, code, obj):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        path = parsed.path

        if path == "/health":
            self.send_json(200, {"ok": True, "engine": "yolov8"})
            return

        if path == "/api/vision/capabilities":
            self.send_json(200, self.server.service.capabilities())
            return

        if path == "/api/vision/stream":
            self.handle_stream(query)
            return

        self.send_json(404, {"code": 404, "error": "not found"})

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        if parsed.path != "/api/vision/detect":
            self.send_json(404, {"code": 404, "error": "not found"})
            return

        kind = (query.get("kind") or ["pest"])[0]
        try:
            box = self.server.service.get(kind)
        except KeyError:
            self.send_json(400, {"code": 400, "error": "未知类别：%s" % kind})
            return

        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            self.send_json(400, {"code": 400, "error": "请求体为空"})
            return
        if length > 20 * 1024 * 1024:
            self.send_json(413, {"code": 413, "error": "图片超过 20MB"})
            return

        body = self.rfile.read(length)
        image = extract_image(self.headers.get("Content-Type"), body)
        if not image:
            self.send_json(400, {"code": 400, "error": "未找到 image 字段"})
            return

        try:
            result = box.detect_bytes(image)
            self.send_json(200, result)
        except FileNotFoundError as exc:
            self.send_json(503, {"code": 503, "error": str(exc)})
        except RuntimeError as exc:
            self.send_json(503, {"code": 503, "error": str(exc)})
        except ImportError as exc:
            self.send_json(503, {
                "code": 503,
                "error": "缺少依赖：%s，请执行 pip install -r tools/requirements-yolo.txt" % exc,
            })
        except ValueError as exc:
            self.send_json(400, {"code": 400, "error": str(exc)})
        except Exception as exc:  # 推理异常不应打断服务
            self.send_json(500, {"code": 500, "error": "%s: %s" % (type(exc).__name__, exc)})

    def handle_stream(self, query):
        kind = (query.get("kind") or ["ppe"])[0]
        try:
            box = self.server.service.get(kind)
        except KeyError:
            self.send_json(400, {"code": 400, "error": "未知类别：%s" % kind})
            return

        source = (query.get("src") or [self.server.service.source or ""])[0]
        if not source:
            self.send_json(400, {"code": 400, "error": "请用 --source 配置摄像头，或传 src= 参数"})
            return

        try:
            cv, _ = ensure_cv()
        except ImportError as exc:
            self.send_json(503, {
                "code": 503,
                "error": "缺少依赖：%s，请执行 pip install -r tools/requirements-yolo.txt" % exc,
            })
            return
        try:
            box.load()
        except Exception as exc:
            self.send_json(503, {"code": 503, "error": str(exc)})
            return

        capture_source = int(source) if source.isdigit() else source
        capture = cv.VideoCapture(capture_source)
        if source.isdigit() and hasattr(cv, "CAP_PROP_BUFFERSIZE"):
            capture.set(cv.CAP_PROP_BUFFERSIZE, 1)
        if not capture.isOpened():
            self.send_json(502, {"code": 502, "error": "无法打开摄像头源：%s" % source})
            return

        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()

        try:
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                try:
                    result = box.predict(frame)
                    draw_boxes(cv, frame, result)
                except Exception as exc:
                    cv.putText(frame, "infer error", (10, 24),
                               cv.FONT_HERSHEY_SIMPLEX, 0.7, (40, 40, 220), 2)
                    if VERBOSE:
                        sys.stderr.write("stream infer error: %s\n" % exc)
                ok, jpeg = cv.imencode(".jpg", frame, [int(cv.IMWRITE_JPEG_QUALITY), 80])
                if not ok:
                    continue
                data = jpeg.tobytes()
                self.wfile.write(b"--frame\r\n")
                self.wfile.write(b"Content-Type: image/jpeg\r\n")
                self.wfile.write(("Content-Length: %d\r\n\r\n" % len(data)).encode("ascii"))
                self.wfile.write(data)
                self.wfile.write(b"\r\n")
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            pass
        finally:
            capture.release()


def local_ips():
    ips = []
    try:
        host = socket.gethostname()
        for item in socket.getaddrinfo(host, None, socket.AF_INET):
            ip = item[4][0]
            if ip not in ips and not ip.startswith("127."):
                ips.append(ip)
    except Exception:
        pass
    return ips


def main():
    parser = argparse.ArgumentParser(description="YOLOv8 实时识别服务（稻草人驱鸟器）")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--config", default=os.path.join(BASE_DIR, "yolo_models.json"))
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", default="cpu", help="cpu 或 cuda:0")
    parser.add_argument("--source", default="",
                        help="摄像头源：USB 编号 0，或 MJPEG/RTSP 地址")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    global VERBOSE
    VERBOSE = args.verbose

    service = Service(args.config, args.imgsz, args.device, args.source)
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.service = service
    server.daemon_threads = True

    print("YOLOv8 识别服务已启动")
    print("  监听:      http://%s:%d" % (args.host, args.port))
    for ip in local_ips():
        print("  局域网:    http://%s:%d" % (ip, args.port))
    print("  检测接口:  POST /api/vision/detect?kind=pest|ppe")
    print("  标注流:    GET  /api/vision/stream?kind=ppe&src=<摄像头地址>")
    print("  模型配置:  %s" % args.config)
    print("  摄像头源:  %s" % (args.source or "未配置（检测接口仍可用）"))
    print("按 Ctrl+C 停止。")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n正在停止…")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
