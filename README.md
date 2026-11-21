# 稻草人驱鸟控制系统 · 客户端源码

Windows 桌面端与 Android 手机端的控制软件源码。两端共用设备固件 `1.2.0` 的 `/api/*` HTTP 接口，界面与功能保持一致。

> **本仓库只提供源码，不提供 APK / exe 成品，也没有 Release 安装包。**
> 需要运行请按下面的步骤自行编译。

## 功能

- 设备连接与状态轮询（2 秒刷新）：电压、信号、雷达脉冲、工作状态
- 参数配置：白天/夜间音量、灵敏度、冷却时间、触发阈值、光控、驱鸟策略等
- 分项测试、恢复默认、重启设备、打开网页控制台
- 6 套现场推荐场景一键套用（农田、果园、菜地、庭院、夜间低噪、强干扰）
- 扩展功能：
  - 病虫害识别 / 人员防护服检测（摄像头实时画面 + YOLOv8 服务回传检测框）
  - 驱鸟策略（雷达 / 视觉 / 两者结合）
  - 小车固定路线规划与运行控制
  - 天气查询 + 自动/手动水阀控制

## 目录

```
app/
├─ windows/                 Windows WinForms 客户端（C#，单文件编译）
│  ├─ ScarecrowControl.cs   主界面、状态、参数、连接
│  ├─ Features.cs           5 个扩展功能页面
│  ├─ build.bat             csc 编译脚本
│  └─ app.manifest / app.ico
└─ android/                 Android 客户端（Java，无第三方依赖）
   ├─ app/src/main/         Java 源码、资源、清单
   ├─ app/build.gradle      模块配置
   ├─ build_apk.bat         离线打包脚本（aapt2 → javac → d8 → 签名）
   └─ gradle/               Gradle Wrapper
docs/
└─ APP控制协议.md           客户端与设备之间的 HTTP 接口定义
```

## 编译 Windows 端

需要 Windows 自带的 .NET Framework 4.x（`csc.exe`），不需要 Visual Studio 或 NuGet。

```bat
cd app\windows
build.bat
```

产物为 `app\windows\dist\ScarecrowControl.exe`。`dist` 目录已在 `.gitignore` 中忽略。

## 编译 Android 端

### 方式一：离线脚本（不依赖 Gradle）

前置条件：

- Android SDK，包含 `build-tools;35.0.0` 和 `platforms;android-34`
- Android Studio 自带的 JDK（默认路径 `C:\Program Files\Android\Android Studio\jbr`）

```bat
cd app\android
build_apk.bat
```

脚本会依次执行 aapt2、javac、d8、zipalign、apksigner，产物在 `app\android\dist\ScarecrowControl.apk`。

### 方式二：Android Studio

在 `app\android` 下新建 `local.properties`：

```properties
sdk.dir=C\:\\Users\\<你的用户名>\\AppData\\Local\\Android\\Sdk
```

然后用 Android Studio 打开 `app\android` 目录同步并编译。工程配置：compileSdk 34、minSdk 24、targetSdk 34、无第三方依赖。

仓库不包含签名文件；离线脚本会用 `keytool` 在本机生成一个标准调试证书（口令 `android`），仅适合自用测试。正式发布请替换为你自己的签名。

## 连接设备

1. 手机或电脑连接设备热点 `Scarecrow-XXXX`（默认密码见设备标签）。
2. 默认设备地址为 `192.168.4.1`，界面里也可以手动修改。
3. 如果设备已接入路由器，请填写设备 `/api/status` 返回的局域网 IP。

接口细节见 [docs/APP控制协议.md](docs/APP控制协议.md)。

## 使用与授权

本仓库源码供在线浏览和评估使用。未经版权所有者书面许可，不得复制、修改、再分发、用于商业用途或用于制作衍生软件。详见 [LICENSE](LICENSE)。

---

版权所有 © 2026 hu-hu21，保留所有权利。
