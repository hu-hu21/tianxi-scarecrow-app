#pragma once
#include <Arduino.h>

/*
 * 硬件版本：v1（ESP32 DevKit 30Pin + WT41 雷达 + DFPlayer Mini）
 * 所有引脚均为 ESP32 DevKit V1 30Pin 的丝印编号。
 */

// ---------- 输入 ----------
#define PIN_RADAR_OUT     34   // WT41 OUT，下降沿触发
#define PIN_LDR           36   // 光敏分压节点（VP）
#define PIN_VBAT          39   // 电池分压节点（VN）
#define PIN_BTN_MODE       4   // 短按试驱，长按 3s 恢复默认
#define PIN_BTN_TEST      15   // 短按立即驱赶

// ---------- 输出 ----------
#define PIN_LED_RED       32   // 12V 红灯带，低边 MOS
#define PIN_LED_BLUE      33   // 12V 蓝灯带，低边 MOS
#define PIN_SERVO         13   // 云台舵机
#define PIN_STATUS_LED     2   // 板载状态灯

// ---------- 串口 ----------
#define PIN_RADAR_RX      16   // ESP32 RX2 <- WT41 TX
#define PIN_RADAR_TX      17   // ESP32 TX2 -> WT41 RX
#define PIN_DF_RX         26   // ESP32 RX1 <- DFPlayer TX
#define PIN_DF_TX         27   // ESP32 TX1 -> DFPlayer RX（串 1k）

// ---------- I2C 扩展 ----------
#define PIN_I2C_SDA       21
#define PIN_I2C_SCL       22

// ---------- 电气参数 ----------
#define VBAT_R_TOP_KOHM   100.0f
#define VBAT_R_BOT_KOHM    22.0f
#define VBAT_LOW_CUTOFF    11.0f   // 低于此值禁止驱赶
#define VBAT_SLEEP_CUTOFF  10.5f   // 低于此值进入 30min 深睡
#define VBAT_MAX           15.5f

#define CFG_VERSION        3
#define CFG_NAMESPACE      "scarecrow"

// 对外 API 版本，客户端通过 /api/status 的 api 字段校验
#define FW_VERSION         "1.2.0"
#define API_VERSION        1

struct ScarecrowConfig {
  uint8_t  version;
  uint8_t  volumeDay;          // 0-30
  uint8_t  volumeNight;        // 0-30
  uint8_t  sensitivity;        // 触发所需脉冲数 1-8
  uint16_t triggerWindowMs;    // 计数窗口
  uint16_t cooldownSec;        // 驱赶后的冷却
  uint16_t activeMinMs;        // 单次驱赶最短
  uint16_t activeMaxMs;        // 单次驱赶最长
  uint8_t  trackCount;         // SD 卡内音轨数量
  uint8_t  quietStartHour;     // 静音时段开始
  uint8_t  quietEndHour;       // 静音时段结束
  uint8_t  nightReduceVolume;  // 1=夜间降音量
  uint8_t  quietHoursEnable;   // 1=启用静音时段（需 NTP 对时）
  uint16_t ldrNightThreshold;  // ADC 低于此值判为夜间
  char     wifiSsid[33];
  char     wifiPass[65];
};

extern ScarecrowConfig cfg;

void configLoad();
void configSave();
void configReset();
