#pragma once
#include <Arduino.h>

/*
 * DFPlayer Mini 最小组件。只实现本项目用到的命令，避免额外依赖。
 * 接线：ESP32 GPIO27(TX) --1k-- DFPlayer RX；GPIO26(RX) <- DFPlayer TX
 */
class DfPlayer {
public:
  void begin();
  void setVolume(uint8_t vol);      // 0-30
  void playTrack(uint16_t track);   // TF 卡 / 目录下的第 N 首
  void stop();
  void setEq(uint8_t eq);           // 0 普通 1 流行 2 摇滚 3 爵士 4 古典 5 贝斯
  void setDevice(uint8_t dev);      // 1=U 盘 2=TF 卡
  void reset();

private:
  HardwareSerial serial_{1};
  void cmd(uint8_t command, uint16_t param);
};
