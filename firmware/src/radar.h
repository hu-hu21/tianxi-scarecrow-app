#pragma once
#include <Arduino.h>

/*
 * WT41 这类微波雷达模块的 OUT 脚会输出一段电平脉冲。
 * 这里用中断计数 + 时间窗过滤，避免树叶、雨滴、单次抖动造成误触发。
 */
class RadarDetector {
public:
  void begin();
  bool update();                 // 达到设定脉冲数时返回 true（只返回一次）
  void clear();
  void setSensitivity(uint8_t n) { sensitivity_ = constrain(n, 1, 8); }
  void setWindow(uint16_t ms)    { windowMs_ = ms; }
  uint32_t totalPulses() const   { return pulseCount_; }

private:
  static void IRAM_ATTR isr();
  static volatile uint32_t pulseCount_;
  static volatile uint32_t lastIsrMs_;

  uint32_t lastSeen_ = 0;
  uint32_t windowStart_ = 0;
  uint8_t  hits_ = 0;
  uint8_t  sensitivity_ = 3;
  uint16_t windowMs_ = 2500;
};
