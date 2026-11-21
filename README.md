# 稻草人驱鸟控制系统 · 源码

Windows 11 服务端、Windows 桌面客户端、Android 手机客户端，以及 ESP32 固件、
YOLOv8 识别服务和结构 / PCB 设计脚本。

- 版本：**v3.21.5**
- 开发者：**胡宇宸**
- 开发日期：**2026-11-21**
- 适用：Windows 11 / Android 7.0 以上

> **本仓库只提供源码，不提供 APK / exe 成品，也没有 Release 安装包。**
> 需要运行请按下面的步骤自行编译。

## 功能

### 客户端（Windows / Android）

- 固定底部导航：**设备控制 / 设备状态 / 硬件设置 / 扩展功能 / 设置**
- 设备控制：立即试驱、声音测试、灯光测试、云台测试、停止输出、网页控制台、
  恢复默认、重启设备
- 设备状态：运行状态、电池电压、光照环境、静音时段、雷达脉冲、在线时长、
  固件版本、网络模式，每 2.5 秒自动刷新
- 硬件设置：服务器地址、设备地址、保存并连接、自动查找
- 扩展功能：
  - 病虫害识别 / 人员防护服检测（摄像头画面 + YOLOv8 检测框）
  - 驱鸟策略（雷达 / 视觉 / 雷达 + 视觉）
  - 小车固定路线规划与运行控制
  - 天气查询 + 自动 / 手动水阀控制
- 设置：运行日志、版本信息、开发者警示与使用条款
- 每个功能页都带「功能使用说明」

### Windows 11 服务端

- 监听端口（默认 1819），按设备地址转发 `/api/*` 与 MJPEG 流
- 设备列表、设为当前、健康检查、请求统计
- **每个客户端独立转发通道**：按 `X-Client-Id` 区分，首次解析后固定设备，
  多端同时在线互不影响；没有该请求头时按来源 IP 区分
- 监控接口：`GET /server/health`、`GET /server/channels`

### 识别服务

- `tools/yolo_service.py`：YOLOv8 病虫害与 PPE 检测 HTTP 服务
- `models/pest.pt`、`models/ppe.pt` 需自行训练后放入 `models/` 目录
- 详见 [docs/YOLOv8识别.md](docs/YOLOv8识别.md)

## 目录

```
app/
├─ windows-server/          Windows 11 服务端（C# WinForms，单文件编译）
│  ├─ ScarecrowServer.cs    监听、转发、设备绑定、独立客户端通道
│  └─ build.bat             csc 编译脚本
├─ windows/                 Windows 客户端（C# WinForms）
│  ├─ ScarecrowControl.cs   主界面、五个导航页、连接与状态
│  ├─ Features.cs           扩展功能页面
│  └─ build.bat
└─ android/                 Android 客户端（Java，无第三方依赖）
   ├─ app/src/main/         Java 源码、资源、清单
   ├─ app/build.gradle      模块配置
   ├─ build_apk.bat         离线打包脚本（aapt2 → javac → d8 → 签名）
   └─ gradle/               Gradle Wrapper

firmware/                   ESP32 固件（PlatformIO）
pcb/                        PCB 生成脚本、网表、BOM、Gerber
cnc/                        CNC 零件生成脚本与图纸
tools/
├─ yolo_service.py          YOLOv8 识别服务
├─ demo_server.py           仿真设备（全部 /api/* 接口）
├─ mock_device.py           最小设备模拟器
├─ make_usage_video.py      生成使用说明视频
└─ fetch_models.py          下载基础权重
docs/
├─ APP控制协议.md            客户端 / 服务端 / 设备 HTTP 接口
├─ YOLOv8识别.md             模型、接口与风险分级
├─ 仿真服务器部署.md          公网部署、客户端连接与通道说明
├─ 接线与调试.md             硬件接线与调试
└─ video/                   使用说明视频截图
```

## 编译 Windows 服务端

需要 Windows 自带的 .NET Framework 4.x（`csc.exe`），不需要 Visual Studio 或 NuGet。

```bat
cd app\windows-server
build.bat
```

产物为 `app\windows-server\dist\ScarecrowServer.exe`。`dist` 目录已在 `.gitignore` 中忽略。

## 编译 Windows 客户端

```bat
cd app\windows
build.bat
```

产物为 `app\windows\dist\ScarecrowControl.exe`。

## 编译 Android 客户端

### 方式一：离线脚本（不依赖 Gradle）

前置条件：

- Android SDK，包含 `build-tools;35.0.0` 和 `platforms;android-34`
- Android Studio 自带的 JDK（默认路径 `C:\Program Files\Android\Android Studio\jbr`）

```bat
cd app\android
build_apk.bat
```

脚本会依次执行 aapt2、javac、d8、zipalign、apksigner，产物在
`app\android\dist\ScarecrowControl.apk`。

### 方式二：Android Studio

在 `app\android` 下新建 `local.properties`：

```properties
sdk.dir=C\:\\Users\\<你的用户名>\\AppData\\Local\\Android\\Sdk
```

然后用 Android Studio 打开 `app\android` 目录同步并编译。工程配置：
compileSdk 34、minSdk 24、targetSdk 34、无第三方依赖。

仓库不包含签名文件；离线脚本会用 `keytool` 在本机生成一个标准调试证书
（口令 `android`），仅适合自用测试。正式发布请替换为你自己的签名。

## 使用流程

1. 在 Windows 11 上启动 `ScarecrowServer.exe`，添加设备地址并【设为当前】，
   确认端口后【启动服务】。
2. 客户端进入【硬件设置】，填写服务器地址（运行服务端的电脑 IP:端口），
   设备地址可留空；点击【保存并连接】。
3. 【设备控制】做一次声音 / 灯光 / 云台测试。
4. 【设备状态】查看电压、光照、雷达脉冲、固件版本等实时数据。
5. 需要识别时，启动 YOLOv8 服务并放入 `models/pest.pt`、`models/ppe.pt`。

多客户端同时使用时，服务端会为每个客户端建立独立通道；在
`GET /server/channels` 可以看到通道绑定的设备与请求统计。

## 识别服务

```bash
pip install -r tools/requirements-yolo.txt
python tools/yolo_service.py --port 8000
```

默认接口：

- `POST /detect/pest`：病虫害识别
- `POST /detect/ppe`：防护服 / 安全帽检测
- `GET /health`：服务状态与模型加载情况

接口细节见 [docs/YOLOv8识别.md](docs/YOLOv8识别.md)。

## 仿真设备

没有硬件时可用 `tools/demo_server.py` 模拟全部接口：

```bash
python3 tools/demo_server.py --port 1819 --advertise 127.0.0.1:1819
```

部署、防火墙、systemd 与客户端连接见
[docs/仿真服务器部署.md](docs/仿真服务器部署.md)。

接口细节见 [docs/APP控制协议.md](docs/APP控制协议.md)。

## 使用与授权

本仓库源码供在线浏览和评估使用。未经版权所有者书面许可，不得复制、修改、
再分发、用于商业用途或用于制作衍生软件。详见 [LICENSE](LICENSE)。

---

版权所有 © 2026 胡宇宸，保留所有权利。
