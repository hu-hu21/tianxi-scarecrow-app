# 稻草人驱鸟器控制协议（API v1）

三个客户端（Windows / Android / iOS）共用同一套 HTTP 接口，固件版本 `1.1.0` 起支持；`1.1.1` 修复了内置网页状态不显示的问题；`1.2.0` 起设备热点常开（AP+STA），`192.168.4.1` 始终可访问。

## 1. 网络模型

设备默认工作在 AP 模式：

```
手机 / 电脑  ──Wi-Fi──▶  Scarecrow-XXXX（密码 scarecrow）
                              │
                              └─ HTTP  http://192.168.4.1/
                                   也可用 http://scarecrow.local/
```

- 设备已配置路由器 STA 时，IP 由路由器分配，页面 `/api/status` 的 `ip` 字段会给出当前地址。
- 所有接口都是明文 HTTP，仅用于局域网，**不要映射到公网**。
- 端口固定 80，响应 `Content-Type: application/json`。

## 2. 状态

### GET /api/status

```json
{
  "api": 1,
  "fw": "1.2.0",
  "state": "IDLE",
  "vbat": 12.35,
  "night": 0,
  "quiet": 0,
  "pulses": 42,
  "lowBat": 0,
  "test": 0,
  "track": 3,
  "servo": 90,
  "volDay": 26,
  "volNight": 16,
  "sens": 3,
  "cool": 60,
  "tracks": 8,
  "qStart": 22,
  "qEnd": 6,
  "qEnable": 0,
  "activeMin": 8000,
  "activeMax": 18000,
  "trigger": 2500,
  "ldr": 800,
  "uptime": 3725,
  "mode": "AP",
  "ssid": "Scarecrow",
  "rssi": 0,
  "ip": "192.168.4.1"
}
```

| 字段 | 类型 | 含义 |
|---|---|---|
| `api` | int | 协议版本，当前 1 |
| `fw` | string | 固件版本 |
| `state` | string | `IDLE` / `ACTIVE` / `COOLDOWN` |
| `vbat` | float | 电池电压（V） |
| `night` | 0/1 | 光敏判夜 |
| `quiet` | 0/1 | 当前是否处于静音时段 |
| `pulses` | int | 雷达累计脉冲 |
| `lowBat` | 0/1 | 低电禁驱状态 |
| `test` | int | 分项测试：0 无，1 声音，2 灯光，3 云台 |
| `track` | int | 当前/最近播放音轨 |
| `servo` | int | 舵机角度 |
| `uptime` | int | 运行秒数 |
| `mode` | string | `AP` / `STA` |
| `rssi` | int | STA 模式信号强度，AP 模式为 0 |
| `ip` | string | 当前访问地址 |

`volDay` / `volNight` / `sens` / `cool` / `tracks` / `qStart` / `qEnd` / `qEnable` / `activeMin` / `activeMax` / `trigger` / `ldr` 与配置接口同名字段一致。

## 3. 配置

### GET /api/config

返回可写参数，结构如下：

```json
{
  "volDay": 26, "volNight": 16, "sens": 3, "cool": 60, "tracks": 8,
  "qStart": 22, "qEnd": 6, "qEnable": 0,
  "activeMin": 8000, "activeMax": 18000, "trigger": 2500, "ldr": 800
}
```

### POST /api/config

请求体为 `application/x-www-form-urlencoded`，只提交需要修改的字段即可：

```
volDay=20&volNight=12&sens=4&cool=90&tracks=8&activeMin=8000&activeMax=20000&qStart=22&qEnd=6&qEnable=1&ldr=800&trigger=2500
```

| 字段 | 范围 | 说明 |
|---|---|---|
| `volDay` / `volNight` | 0–30 | DFPlayer 音量 |
| `sens` | 1–8 | 触发所需脉冲数 |
| `cool` | 5–3600 | 冷却秒数 |
| `tracks` | 1–99 | TF 卡音轨数量 |
| `activeMin` / `activeMax` | 2000–120000 | 单次驱赶时长（ms），max 会自动 ≥ min+1000 |
| `qStart` / `qEnd` | 0–23 | 静音时段（需 NTP 对时） |
| `qEnable` | 0/1 | 是否启用静音时段 |
| `ldr` | 0–4095 | 夜间判定 ADC 阈值 |
| `trigger` | 500–10000 | 雷达计数窗口（ms） |

返回更新后的 `/api/status` 完整 JSON。所有值都会写入 NVS，掉电保留。

## 4. 分项测试

### GET/POST /api/test?what=all

| `what` | 动作 |
|---|---|
| `all`（缺省） | 立即执行一次完整驱赶 |
| `sound` | 播放随机音轨 5 s |
| `light` | 红蓝交替闪 4 s |
| `servo` | 30–150° 往返扫摆 4 s |
| `stop` | 停止声音/灯光/舵机，回到待机 |

响应：`{"ok":1}`。分项测试期间 `status.test` 为 1/2/3。

## 5. 维护

| 接口 | 方法 | 说明 |
|---|---|---|
| `/api/reset` | POST | 恢复出厂参数（不重启） |
| `/api/reboot` | POST | 重启设备，先返回 `{"ok":1}` 再断开 |
| `/save` | POST | 旧版表单接口，等同 `/api/config` |
| `/test` | GET | 旧版立即试驱 |
| `/reset` | GET | 旧版恢复默认 |

## 6. 示例

```bash
curl http://192.168.4.1/api/status
curl http://192.168.4.1/api/config
curl -X POST http://192.168.4.1/api/config \
     -d "volDay=20&cool=90&qEnable=1"
curl -X POST "http://192.168.4.1/api/test?what=light"
curl -X POST http://192.168.4.1/api/reboot
```

## 7. 兼容性约定

- 客户端应先检查 `api` 字段，不等于 1 时提示升级。
- 新增字段只增不改；未知字段忽略。
- 所有请求建议 2.5–3 s 超时，失败按“离线”处理并继续轮询。
- 设备单线程处理 HTTP，轮询间隔建议 ≥ 2 s，避免影响雷达与驱赶逻辑。

---

# 扩展能力（v2.0 草案）

以下接口对应「病虫害识别 / 防护服检测 / 驱鸟策略 / 小车路线 / 天气与水阀」五项扩展。
设备端固件未实现时返回 `404`，客户端应按「本机不支持」提示，不影响基础功能。

通用约定：

- 所有响应仍为 JSON，成功 `{"code":0,...}`，失败 `{"code":<非0>,"msg":"..."}`。
- 视觉推理建议由局域网内的 AI 服务承担（如 PC 上的 Python 服务），设备只做转发或直接由客户端调用。
- 客户端可在设置里单独填写「AI 服务地址」，留空则用设备地址。

## 8. 视觉识别（YOLOv8 实时）

推理由局域网内的 YOLOv8 服务完成（`tools/yolo_service.py`，默认端口 8000），客户端负责取摄像头画面、按约 0.8 s 的间隔送帧并绘制检测框。该服务也支持直接读取摄像头并输出已画框的 MJPEG 标注流。

### GET /api/vision/capabilities

```json
{
  "code": 0,
  "engine": "yolov8",
  "imgsz": 640,
  "device": "cpu",
  "models": {
    "pest": {"weights": "...\\models\\pest.pt", "exists": true, "loaded": true, "model": "pest.pt", "conf": 0.35},
    "ppe":  {"weights": "...\\models\\ppe.pt",  "exists": false, "loaded": false, "model": "", "conf": 0.35}
  }
}
```

### POST /api/vision/detect?kind=pest

`Content-Type: multipart/form-data`，字段名 `image`，JPEG/PNG，长边建议 ≤ 1280 px。

```json
{
  "code": 0,
  "kind": "pest",
  "model": "pest.pt",
  "fallback": false,
  "cost_ms": 38,
  "image_w": 640,
  "image_h": 480,
  "detections": [
    {"label": "稻瘟病", "label_en": "rice_blast", "confidence": 0.87, "box": [120, 88, 260, 240]},
    {"label": "稻飞虱", "label_en": "planthopper", "confidence": 0.72, "box": [300, 150, 360, 210]}
  ]
}
```

`box` 为 `[x1,y1,x2,y2]` 像素坐标。`fallback=true` 表示配置的权重缺失、服务退回到 `yolov8n.pt`（COCO 通用类别）。

### POST /api/vision/detect?kind=ppe

```json
{
  "code": 0,
  "kind": "ppe",
  "model": "ppe.pt",
  "cost_ms": 42,
  "image_w": 1280,
  "image_h": 720,
  "person_count": 3,
  "alarm": true,
  "detections": [
    {"label": "未戴安全帽", "label_en": "no_helmet", "confidence": 0.91, "box": [300, 80, 420, 200]},
    {"label": "反光衣", "label_en": "vest", "confidence": 0.88, "box": [300, 200, 430, 520]}
  ]
}
```

`label_en` 取值：`helmet` / `no_helmet` / `vest` / `no_vest` / `person`。
出现 `no_helmet` 或 `no_vest` 且置信度 ≥ 0.5 时置 `alarm=true`。

### GET /api/vision/stream?kind=ppe&src=<camera>

返回 `multipart/x-mixed-replace` MJPEG，服务端已逐帧完成 YOLOv8 推理并绘制检测框。`src` 可省略，使用服务启动参数 `--source`（USB 编号或 MJPEG/RTSP 地址）。客户端直接把「摄像头地址」填成该 URL，即可看到全帧率标注画面。

### 摄像头接口（设备端可选）

摄像头挂在设备上时，建议固件提供：

- `GET /api/camera/stream`：MJPEG，`Content-Type: multipart/x-mixed-replace`
- `GET /api/camera/snapshot`：单张 `image/jpeg`

客户端两种都兼容：Content-Type 为 `image/*` 时按快照轮询，否则按 MJPEG 解析。ESP32-CAM 常见地址为 `http://<设备IP>:81/stream`。


## 9. 小车路线

### GET /api/robot/state

```json
{
  "code": 0, "mode": "idle", "waypoint": 0, "total": 6,
  "x": 0.0, "y": 0.0, "heading": 90.0,
  "speed": 0.0, "battery": 86, "error": ""
}
```

`mode`：`idle` / `running` / `paused` / `returning` / `fault`。

### GET /api/robot/route

```json
{"code":0,"loop":false,"waypoints":[
  {"x":1.5,"y":2.0,"action":"none","wait_s":0},
  {"x":4.0,"y":2.0,"action":"spray","wait_s":8},
  {"x":4.0,"y":5.5,"action":"photo","wait_s":3}
]}
```

### POST /api/robot/route

请求体同 `GET` 的响应（去掉 `code`）。整条覆盖，最多 64 个点。

### POST /api/robot/control

```json
{"action":"start"}
```

`action`：`start` / `pause` / `resume` / `stop` / `home`。

## 10. 天气与水阀

### GET /api/weather

设备侧缓存，10 分钟刷新一次；没有联网时 `stale=true`。

```json
{"code":0,"temp":26.4,"humidity":58,"rain":0.0,"desc":"多云",
 "wind":2.1,"stale":false,"updated":1763000000}
```

### GET /api/valve

```json
{"code":0,"open":false,"auto":true,"mode":"idle","flow":0.0,
 "reason":"湿度 58% 高于阈值 40%","last_open":1762990000}
```

### POST /api/valve

```json
{"open":true,"duration_s":30}
```

`duration_s>0` 时到时自动关闭。

### POST /api/valve/auto

```json
{"enabled":true,"temp_min":5,"temp_max":35,"humidity_below":40,"respect_rain":true}
```

自动规则：`humidity < humidity_below` 且 `temp_min ≤ temp ≤ temp_max` 且（`respect_rain` 时 `rain == 0`）→ 开阀，否则关闭。

## 11. 驱鸟策略

沿用 `POST /api/config`，新增表单字段：

| 字段 | 取值 | 说明 |
|---|---|---|
| `strategy` | `radar` / `vision` / `both` | 触发源，默认 `radar` |
| `visionCool` | 30–3600 | 视觉触发后的冷却秒数 |

`GET /api/status` 增加 `strategy` 字段；旧固件无此字段时客户端按 `radar` 处理。

## 12. 客户端降级策略

| 情况 | 客户端表现 |
|---|---|
| `404` / 连接失败 | 卡片置灰，标注「设备固件不支持」 |
| 视觉服务未配置 | 「识别」按钮提示先填写 AI 服务地址 |
| 天气接口失败 | 显示「天气获取失败」，水阀仍可手动控制 |
| 无 GPS / 里程计 | 路线仍可编辑下发，`state` 只显示模式与序号 |

## 13. 仿真设备

`tools/demo_server.py` 实现了本文全部接口（含摄像头 MJPEG、视觉、小车、水阀），
默认监听 `0.0.0.0:1819`，可直接部署到公网服务器供客户端联调。
视觉结果是按画面内容模拟生成的，不是真实推理。

```bash
python3 tools/demo_server.py --port 1819 --advertise 47.94.214.62:1819
```

部署、安全组和 systemd 配置见 [仿真服务器部署.md](仿真服务器部署.md)。

## 14. 服务端转发与客户端通道

Windows 11 服务端 `ScarecrowServer.exe` 监听端口（默认 1819），把客户端的
`/api/*` 与 MJPEG 请求转发到绑定的设备，并维护每个客户端的独立通道。

- 客户端在请求头带 `X-Client-Id`（启动时生成的随机字符串）
- 客户端可用 `X-Device-Address` 指定设备；服务端首次解析后把该地址固定到通道
- 没有 `X-Client-Id` 时按来源 IP 建立通道，兼容旧客户端
- 监控接口：`GET /server/health`、`GET /server/channels`
- 通道之间互不共享设备绑定，一个客户端切换设备不会影响其他客户端

请求示例：

```http
GET /api/status HTTP/1.1
Host: 127.0.0.1:1819
X-Client-Id: 9f2c4a7b6d1e4c8f
X-Device-Address: 192.168.1.66:80
```
