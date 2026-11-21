#include "dfplayer.h"
#include "../include/config.h"

void DfPlayer::begin() {
  serial_.begin(9600, SERIAL_8N1, PIN_DF_RX, PIN_DF_TX);
  delay(600);          // 模块上电需要稳定时间
  reset();
  delay(900);
  setDevice(2);        // TF 卡
  setEq(0);
  setVolume(cfg.volumeDay);
}

void DfPlayer::cmd(uint8_t command, uint16_t param) {
  uint8_t frame[10];
  frame[0] = 0x7E;
  frame[1] = 0xFF;
  frame[2] = 0x06;
  frame[3] = command;
  frame[4] = 0x00;             // 不需要模块回传
  frame[5] = (uint8_t)(param >> 8);
  frame[6] = (uint8_t)(param & 0xFF);

  uint16_t sum = 0;
  for (uint8_t i = 1; i <= 6; i++) sum += frame[i];
  sum = (uint16_t)(0 - sum);
  frame[7] = (uint8_t)(sum >> 8);
  frame[8] = (uint8_t)(sum & 0xFF);
  frame[9] = 0xEF;

  serial_.write(frame, sizeof(frame));
  serial_.flush();
}

void DfPlayer::setVolume(uint8_t vol) {
  if (vol > 30) vol = 30;
  cmd(0x06, vol);
}

void DfPlayer::playTrack(uint16_t track) {
  cmd(0x03, track);
}

void DfPlayer::stop() {
  cmd(0x16, 0);
}

void DfPlayer::setEq(uint8_t eq) {
  cmd(0x07, eq);
}

void DfPlayer::setDevice(uint8_t dev) {
  cmd(0x09, dev);
}

void DfPlayer::reset() {
  cmd(0x0C, 0);
}
