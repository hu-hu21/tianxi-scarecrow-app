#include "radar.h"
#include "../include/config.h"

volatile uint32_t RadarDetector::pulseCount_ = 0;
volatile uint32_t RadarDetector::lastIsrMs_ = 0;

void IRAM_ATTR RadarDetector::isr() {
  uint32_t now = millis();
  // 80ms 内的重复边沿视为同一次动作
  if (now - lastIsrMs_ >= 80) {
    lastIsrMs_ = now;
    pulseCount_++;
  }
}

void RadarDetector::begin() {
  pinMode(PIN_RADAR_OUT, INPUT);
  attachInterrupt(digitalPinToInterrupt(PIN_RADAR_OUT), isr, FALLING);
  // 雷达 UART 用于改参数，默认 9600
  Serial2.begin(9600, SERIAL_8N1, PIN_RADAR_RX, PIN_RADAR_TX);
  clear();
}

void RadarDetector::clear() {
  noInterrupts();
  hits_ = 0;
  windowStart_ = millis();
  lastSeen_ = pulseCount_;
  interrupts();
}

bool RadarDetector::update() {
  uint32_t now = millis();
  uint32_t count = pulseCount_;

  if (count != lastSeen_) {
    lastSeen_ = count;
    if (now - windowStart_ > windowMs_) {
      windowStart_ = now;
      hits_ = 0;
    }
    if (hits_ < 255) hits_++;
  } else if (hits_ > 0 && (now - windowStart_ > windowMs_)) {
    hits_ = 0;              // 窗口内脉冲不足，清零重新计数
  }

  if (hits_ >= sensitivity_) {
    hits_ = 0;
    windowStart_ = now;
    return true;
  }
  return false;
}
