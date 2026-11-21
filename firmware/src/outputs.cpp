#include "outputs.h"
#include "../include/config.h"

#if ESP_ARDUINO_VERSION_MAJOR >= 3
  #define PWM_ATTACH(pin, ch, freq, res) ledcAttach((pin), (freq), (res))
  #define PWM_WRITE(pin, ch, duty)       ledcWrite((pin), (duty))
#else
  #define PWM_ATTACH(pin, ch, freq, res) do { ledcSetup((ch), (freq), (res)); ledcAttachPin((pin), (ch)); } while (0)
  #define PWM_WRITE(pin, ch, duty)       ledcWrite((ch), (duty))
#endif

void Outputs::begin() {
  pinMode(PIN_STATUS_LED, OUTPUT);
  digitalWrite(PIN_STATUS_LED, LOW);

  pinMode(PIN_LED_RED, OUTPUT);
  pinMode(PIN_LED_BLUE, OUTPUT);
  pinMode(PIN_SERVO, OUTPUT);

  PWM_ATTACH(PIN_LED_RED,  0, 20000, 8);
  PWM_ATTACH(PIN_LED_BLUE, 1, 20000, 8);
  PWM_ATTACH(PIN_SERVO,    2, 50, 16);

  leds(0, 0);
  servoCenter();

  analogSetPinAttenuation(PIN_LDR,  ADC_11db);
  analogSetPinAttenuation(PIN_VBAT, ADC_11db);
  pinMode(PIN_LDR, INPUT);
  pinMode(PIN_VBAT, INPUT);

  vbatFiltered_ = batteryVoltage();
}

void Outputs::pwmWrite(uint8_t pin, uint8_t channel, uint32_t duty) {
  PWM_WRITE(pin, channel, duty);
}

void Outputs::leds(uint8_t red, uint8_t blue) {
  pwmWrite(PIN_LED_RED,  0, red);
  pwmWrite(PIN_LED_BLUE, 1, blue);
}

void Outputs::servo(uint8_t degrees) {
  if (degrees > 180) degrees = 180;
  // 500-2500us / 20ms，16bit 占空比
  float pulseUs = 500.0f + (float)degrees * (2000.0f / 180.0f);
  uint32_t duty = (uint32_t)(pulseUs / 20000.0f * 65535.0f);
  pwmWrite(PIN_SERVO, 2, duty);
}

void Outputs::servoCenter() {
  servo(90);
}

uint16_t Outputs::readAverage(uint8_t pin, uint8_t samples) {
  uint32_t sum = 0;
  for (uint8_t i = 0; i < samples; i++) {
    sum += analogRead(pin);
    delayMicroseconds(200);
  }
  return (uint16_t)(sum / samples);
}

bool Outputs::isNight() {
  uint16_t v = readAverage(PIN_LDR, 8);
  return v < cfg.ldrNightThreshold;
}

float Outputs::batteryVoltage() {
  uint32_t mv = 0;
  for (uint8_t i = 0; i < 16; i++) {
    mv += analogReadMilliVolts(PIN_VBAT);
    delayMicroseconds(200);
  }
  mv /= 16;

  float ratio = (VBAT_R_TOP_KOHM + VBAT_R_BOT_KOHM) / VBAT_R_BOT_KOHM;
  float v = (float)mv * ratio / 1000.0f;
  vbatFiltered_ = vbatFiltered_ * 0.8f + v * 0.2f;
  return vbatFiltered_;
}

bool Outputs::batteryOk() {
  return batteryVoltage() >= VBAT_LOW_CUTOFF;
}

void Outputs::statusLed(bool on) {
  digitalWrite(PIN_STATUS_LED, on ? HIGH : LOW);
}
