# YOLOv8 实时识别部署说明

Windows / Android 客户端本身不内置模型，视觉推理由同一局域网内的 YOLOv8 服务完成。客户端负责取摄像头画面、按约 0.8 秒送一帧、把返回的检测框叠加在实时画面上。

```
摄像头（设备 ESP32-CAM / USB 摄像头 / RTSP）
        │  MJPEG 或快照
        ├──────────────► Windows exe / Android apk   实时预览 + 画框
        │                        │ 每 0.8 s 上传一帧
        ▼                        ▼
   YOLOv8 服务（PC / 边缘盒子）POST /api/vision/detect
```

如果希望全帧率标注，也可以让 YOLOv8 服务直接读摄像头，输出已经画好框的 MJPEG：
`http://<服务IP>:8000/api/vision/stream?kind=ppe&src=<摄像头地址>`，客户端把这个地址填进「摄像头地址」即可。

## 1. 安装

建议 Python 3.10–3.12（PyTorch 对 3.13+ 的支持有限；本机是 3.14，需另装 3.11 虚拟环境）。

```bat
py -3.11 -m venv .venv-yolo
.venv-yolo\Scripts\activate
pip install -r tools\requirements-yolo.txt
```

`ultralytics` 会自动安装 PyTorch。CPU 版即可跑通，有 NVIDIA 显卡时用 CUDA 版 PyTorch 更快。

## 2. 模型

本项目的识别引擎固定为 **YOLOv8（ultralytics）**，默认基础权重 `yolov8n.pt`，可替换为 `yolov8s/m/l/x` 自己训练的 `.pt`。

一键下载基础权重与公开安全帽权重：

```bat
python tools\fetch_models.py            # yolov8n + 公开 ppe.pt（演示用）
python tools\fetch_models.py --check    # 检查 models 目录
```

COCO 预训练权重（`yolov8n.pt`）**只有 person 等通用类别，没有病虫害、安全帽、防护服**。要识别这些目标，需要用自己的数据训练：

1. 采集现场图片（建议每类 ≥ 500 张，覆盖不同光照、角度、距离）。
2. 用 labelImg / Roboflow 标注，导出 YOLO 格式。
3. 写 `data.yaml`：

```yaml
path: datasets/ppe
train: images/train
val: images/val
names:
  0: person
  1: helmet
  2: no_helmet
  3: vest
  4: no_vest
```

4. 训练：

```bat
yolo detect train model=yolov8n.pt data=datasets/ppe/data.yaml epochs=100 imgsz=640 batch=16
```

5. 把 `runs/detect/train/weights/best.pt` 复制到：

- `tools/models/ppe.pt`（防护服）
- `tools/models/pest.pt`（病虫害，类别换成蚜虫、叶斑病等）

类别名与中文显示的对应关系在 `tools/yolo_models.json` 的 `labels` 里维护；`alarm_classes` 里的类别置信度 ≥ 0.5 时会触发报警。

> 没有 ppe.pt 时服务会自动退回 `yolov8n.pt`，此时只能统计人数，不能判断安全帽/反光衣。没有 pest.pt 时病虫害接口返回 503，并提示缺少模型。

## 3. 启动服务

```bat
python tools\yolo_service.py --port 8000
```

有摄像头时可直接让服务读流（用于标注流模式）：

```bat
python tools\yolo_service.py --port 8000 --source "http://192.168.4.1:81/stream"
```

常用参数：

| 参数 | 说明 |
|---|---|
| `--port` | 监听端口，默认 8000 |
| `--config` | 模型配置，默认 `tools/yolo_models.json` |
| `--imgsz` | 推理尺寸，默认 640 |
| `--device` | `cpu` 或 `cuda:0` |
| `--source` | 摄像头源：USB 编号 `0`，或 MJPEG/RTSP 地址 |
| `--verbose` | 打印每条请求日志 |

启动后会打印本机局域网地址，例如 `http://192.168.1.20:8000`。

## 4. 客户端配置

1. 「摄像头地址」填设备画面：`http://192.168.4.1/api/camera/stream`；ESP32-CAM 常用 `http://192.168.4.1:81/stream`。
2. 「AI 服务地址」填运行 YOLOv8 的电脑：`http://192.168.1.20:8000`。
3. 点「开始实时」，客户端会持续显示画面，并按 0.8 秒间隔把最新帧送去检测，框随结果刷新。
4. 「单张图片」仍可用于离线核对。

在手机浏览器里打开 `http://192.168.1.20:8000/api/vision/capabilities` 可确认模型是否就绪。

## 5. 性能参考

| 硬件 | 模型 | 单帧耗时 | 建议 |
|---|---|---|---|
| 普通笔记本 CPU | yolov8n 640 | 60–150 ms | 0.8 s 间隔足够 |
| NVIDIA 入门显卡 | yolov8n 640 | 8–20 ms | 可提到 0.3 s 或直接用标注流 |
| 树莓派 4 | yolov8n 640 | 300–600 ms | 降低到 imgsz=416，间隔 1.5 s |

客户端默认 0.8 秒送一帧，既能看到接近实时的框，又不会把服务压满。标注流模式由服务端逐帧推理，帧率取决于硬件。

## 6. 故障排查

| 现象 | 原因 | 处理 |
|---|---|---|
| 返回 503「缺少 ultralytics」 | 依赖未装 | `pip install -r tools/requirements-yolo.txt` |
| 返回 503「模型文件不存在」 | 未放 pest.pt | 按第 2 节训练并复制权重 |
| 摄像头连接失败 | 地址不对或设备未开流 | 浏览器直接打开该地址验证 |
| 框位置偏移 | 客户端画面与送检帧尺寸不一致 | 服务返回的 `image_w/image_h` 会用于缩放，通常无需处理；确认摄像头分辨率未在中途切换 |
| 报警不触发 | 类别名不是 `no_helmet/no_vest` | 检查模型类别名，并同步 `alarm_classes` |

## 7. 穿戴判定与风险分级（v3.21.5）

### 7.1 防护服 / 安全帽穿戴判定

`kind=ppe` 的返回新增：

```json
{
  "person_count": 2,
  "ppe_ready": true,
  "wearing": {
    "total": 2,
    "compliant": 1,
    "violations": 1,
    "missing_helmet": 0,
    "missing_vest": 1
  },
  "persons": [
    {"box": [120, 80, 260, 420], "helmet": true, "vest": false,
     "compliant": false, "missing": ["防护服"], "status": "缺少防护服"}
  ],
  "alarm": true,
  "summary": "人员 2 人，1 人穿戴不合规"
}
```

判定规则：

1. 先取所有 `person / worker / farmer` 人员框。
2. 安全帽、防护服检测框的**中心点落在人员框内**（允许 8% 外扩）即视为该人员已穿戴。
3. 出现 `no_helmet / no_hardhat / no_vest` 等负类时，对应人员直接判为未穿戴。
4. 模型本身包含正类类别、但某人员没有匹配到对应框时，按 `assume_missing_when_absent`（默认 true）判为缺失。
5. 报警条件：任一人员缺失必需项，或画面中出现负类检测框。
6. `ppe_ready=false` 表示当前权重（通常是 yolov8n）没有穿戴类别，只统计人数，不判断穿戴。

类别名可在 `tools/yolo_models.json` 的 `person_classes / helmet_classes / vest_classes / helmet_missing_classes / vest_missing_classes` 中调整，常见别名（hardhat、safety_vest、reflective_vest 等）已内置。

### 7.2 病虫害风险分级

`kind=pest` 的返回新增：

```json
{
  "pest_count": 3,
  "pest_ratio": 0.0184,
  "severity": "moderate",
  "summary": "识别到 3 处，风险等级：中等"
}
```

`pest_ratio` = 所有检测框面积之和 ÷ 画面面积；阈值在 `tools/yolo_models.json` 的 `severity.low / severity.high` 中配置（默认 0.5% 与 2%）。`severity=high` 时接口同时把 `alarm` 置为 true，客户端红色显示。

### 7.3 类别建议

| 用途 | 必需类别 |
|---|---|
| 病虫害 | 蚜虫、叶蝉、飞虱、叶斑病、稻瘟病、锈病、白粉病、健康叶片（可只保留当地常见类别） |
| 防护服 | person、helmet、vest、no_helmet、no_vest（负类可选，有则判定更准） |

> 公开权重只用于联调演示。病虫害需要按当地作物与病害重新采集、标注、训练，否则准确率不可信。
