#pragma once
#include <Arduino.h>

class Outputs {
public:
  void begin();

  void leds(uint8_t red, uint8_t blue);   // 0-255，低边 MOS
  void servo(uint8_t degrees);            // 0-180
  void servoCenter();

  bool  isNight();                        // 光敏判定
  float batteryVoltage();                 // 已按分压比换算
  bool  batteryOk();

  void statusLed(bool on);

private:
  void pwmWrite(uint8_t pin, uint8_t channel, uint32_t duty);
  uint16_t readAverage(uint8_t pin, uint8_t samples);
  float vbatFiltered_ = 12.0f;
};
