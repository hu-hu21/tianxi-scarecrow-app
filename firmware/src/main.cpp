#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <ArduinoOTA.h>
#include <ESPmDNS.h>
#include <Preferences.h>
#include <esp_sleep.h>
#include <time.h>

#include "../include/config.h"
#include "dfplayer.h"
#include "radar.h"
#include "outputs.h"

// ---------------- 全局对象 ----------------
DfPlayer      player;
RadarDetector radar;
Outputs       outputs;
WebServer     server(80);
Preferences   prefs;

ScarecrowConfig cfg;

enum RunState : uint8_t { ST_IDLE = 0, ST_ACTIVE = 1, ST_COOLDOWN = 2 };
static RunState state = ST_IDLE;

static uint32_t stateUntil   = 0;
static uint32_t nextStrobe   = 0;
static uint32_t nextServo    = 0;
static uint32_t nextBattery  = 0;
static uint32_t lastBlink    = 0;
static bool     blinkOn      = false;
static bool     wifiOnline   = false;
static uint32_t bootMs       = 0;

static int8_t   servoDir     = 1;
static uint8_t  servoAngle   = 90;
static uint16_t activeTrack  = 1;
static bool     lowBattery   = false;

// 分项测试：1=声音 2=灯光 3=舵机，到时自动停止
static uint8_t  testMode     = 0;
static uint32_t testUntil    = 0;
static uint32_t testNext     = 0;
static bool     testRed      = true;

static String cliLine;

// ---------------- 配置 ----------------
void configReset() {
  memset(&cfg, 0, sizeof(cfg));
  cfg.version           = CFG_VERSION;
  cfg.volumeDay         = 26;
  cfg.volumeNight       = 16;
  cfg.sensitivity       = 3;
  cfg.triggerWindowMs   = 2500;
  cfg.cooldownSec       = 60;
  cfg.activeMinMs       = 8000;
  cfg.activeMaxMs       = 18000;
  cfg.trackCount        = 8;
  cfg.quietStartHour    = 22;
  cfg.quietEndHour      = 6;
  cfg.nightReduceVolume = 1;
  cfg.quietHoursEnable  = 0;
  cfg.ldrNightThreshold = 800;
  cfg.wifiSsid[0]       = '\0';
  cfg.wifiPass[0]       = '\0';
}

void configLoad() {
  prefs.begin(CFG_NAMESPACE, true);
  size_t n = prefs.getBytes("cfg", &cfg, sizeof(cfg));
  prefs.end();

  if (n != sizeof(cfg) || cfg.version != CFG_VERSION) {
    configReset();
    configSave();
  }
}

void configSave() {
  prefs.begin(CFG_NAMESPACE, false);
  prefs.putBytes("cfg", &cfg, sizeof(cfg));
  prefs.end();
}

// ---------------- 辅助 ----------------
static const char* stateName() {
  switch (state) {
    case ST_ACTIVE:   return "ACTIVE";
    case ST_COOLDOWN: return "COOLDOWN";
    default:          return "IDLE";
  }
}

static bool timeReady() {
  return time(nullptr) > 1700000000;
}

static bool isQuietHour() {
  if (!cfg.quietHoursEnable || !timeReady()) return false;
  if (cfg.quietStartHour == cfg.quietEndHour) return false;

  time_t now = time(nullptr);
  struct tm tmNow;
  localtime_r(&now, &tmNow);
  uint8_t h = (uint8_t)tmNow.tm_hour;

  if (cfg.quietStartHour < cfg.quietEndHour) {
    return h >= cfg.quietStartHour && h < cfg.quietEndHour;
  }
  return h >= cfg.quietStartHour || h < cfg.quietEndHour;
}

// ---------------- 驱赶流程 ----------------
static void stopDeterrent() {
  player.stop();
  outputs.leds(0, 0);
  outputs.servoCenter();
  testMode = 0;
  state = ST_IDLE;
}

static void startDeterrent(bool manual) {
  if (state == ST_ACTIVE) return;
  testMode = 0;

  if (!manual) {
    if (lowBattery || !outputs.batteryOk()) return;
    if (millis() < stateUntil) return;          // 冷却期
  }

  uint32_t now = millis();
  uint32_t duration = random(cfg.activeMinMs, (long)cfg.activeMaxMs + 1);

  uint8_t vol = cfg.volumeDay;
  if (cfg.nightReduceVolume && outputs.isNight()) vol = cfg.volumeNight;
  if (isQuietHour() && vol > 8) vol = 8;

  player.setVolume(vol);
  activeTrack = (uint16_t)random(1, (long)cfg.trackCount + 1);
  player.playTrack(activeTrack);

  servoAngle = (uint8_t)random(30, 151);
  servoDir = (random(0, 2) == 0) ? -1 : 1;

  state       = ST_ACTIVE;
  stateUntil  = now + duration;
  nextStrobe  = now;
  nextServo   = now;

  Serial.printf("[DETER] trigger=%s track=%u dur=%lums vol=%u\n",
                manual ? "manual" : "radar", activeTrack,
                (unsigned long)duration, vol);
}

// ---------------- 电池 ----------------
static void checkBattery() {
  if (millis() < nextBattery) return;
  nextBattery = millis() + 5000;

  float v = outputs.batteryVoltage();
  lowBattery = (v < VBAT_LOW_CUTOFF);

  if (v < VBAT_SLEEP_CUTOFF) {
    Serial.printf("[POWER] %.2fV, sleep 30min\n", v);
    stopDeterrent();
    esp_sleep_enable_timer_wakeup(30ULL * 60ULL * 1000000ULL);
    esp_deep_sleep_start();
  }
}

// ---------------- Web ----------------
static String jsonEsc(const String &in) {
  String out;
  out.reserve(in.length() + 8);
  for (size_t i = 0; i < in.length(); i++) {
    char c = in[i];
    if (c == '"' || c == '\\') {
      out += '\\';
      out += c;
    } else if ((uint8_t)c < 0x20) {
      out += ' ';
    } else {
      out += c;
    }
  }
  return out;
}

static String statusJson() {
  float vbat = outputs.batteryVoltage();
  if (!(vbat >= 0.0f && vbat <= 30.0f)) vbat = 0.0f;  // 过滤 nan / inf

  String s = "{";
  s += "\"api\":";      s += API_VERSION; s += ",";
  s += "\"fw\":\"";     s += jsonEsc(FW_VERSION); s += "\",";
  s += "\"state\":\"";  s += jsonEsc(stateName()); s += "\",";
  s += "\"vbat\":";     s += String(vbat, 2); s += ",";
  s += "\"night\":";    s += outputs.isNight() ? 1 : 0; s += ",";
  s += "\"quiet\":";    s += isQuietHour() ? 1 : 0; s += ",";
  s += "\"pulses\":";   s += radar.totalPulses(); s += ",";
  s += "\"lowBat\":";   s += lowBattery ? 1 : 0; s += ",";
  s += "\"test\":";     s += testMode; s += ",";
  s += "\"track\":";    s += activeTrack; s += ",";
  s += "\"servo\":";    s += servoAngle; s += ",";
  s += "\"volDay\":";   s += cfg.volumeDay; s += ",";
  s += "\"volNight\":"; s += cfg.volumeNight; s += ",";
  s += "\"sens\":";     s += cfg.sensitivity; s += ",";
  s += "\"cool\":";     s += cfg.cooldownSec; s += ",";
  s += "\"tracks\":";   s += cfg.trackCount; s += ",";
  s += "\"qStart\":";   s += cfg.quietStartHour; s += ",";
  s += "\"qEnd\":";     s += cfg.quietEndHour; s += ",";
  s += "\"qEnable\":";  s += cfg.quietHoursEnable; s += ",";
  s += "\"activeMin\":"; s += cfg.activeMinMs; s += ",";
  s += "\"activeMax\":"; s += cfg.activeMaxMs; s += ",";
  s += "\"trigger\":";  s += cfg.triggerWindowMs; s += ",";
  s += "\"ldr\":";      s += cfg.ldrNightThreshold; s += ",";
  s += "\"uptime\":";   s += (uint32_t)((millis() - bootMs) / 1000UL); s += ",";
  s += "\"mode\":\"";   s += (WiFi.status() == WL_CONNECTED ? "AP+STA" : "AP"); s += "\",";
  s += "\"ssid\":\"";   s += jsonEsc(WiFi.status() == WL_CONNECTED ? WiFi.SSID() : String("Scarecrow")); s += "\",";
  s += "\"rssi\":";     s += (WiFi.status() == WL_CONNECTED ? WiFi.RSSI() : 0); s += ",";
  s += "\"ip\":\"";     s += jsonEsc(WiFi.status() == WL_CONNECTED ? WiFi.localIP().toString() : WiFi.softAPIP().toString()); s += "\",";
  s += "\"apIp\":\"";   s += jsonEsc(WiFi.softAPIP().toString()); s += "\",";
  s += "\"staIp\":\"";  s += (WiFi.status() == WL_CONNECTED ? jsonEsc(WiFi.localIP().toString()) : String("")); s += "\"";
  s += "}";
  return s;
}

static String configJson() {
  String s = "{";
  s += "\"volDay\":";   s += cfg.volumeDay; s += ",";
  s += "\"volNight\":"; s += cfg.volumeNight; s += ",";
  s += "\"sens\":";     s += cfg.sensitivity; s += ",";
  s += "\"cool\":";     s += cfg.cooldownSec; s += ",";
  s += "\"tracks\":";   s += cfg.trackCount; s += ",";
  s += "\"qStart\":";   s += cfg.quietStartHour; s += ",";
  s += "\"qEnd\":";     s += cfg.quietEndHour; s += ",";
  s += "\"qEnable\":";  s += cfg.quietHoursEnable; s += ",";
  s += "\"activeMin\":"; s += cfg.activeMinMs; s += ",";
  s += "\"activeMax\":"; s += cfg.activeMaxMs; s += ",";
  s += "\"trigger\":";  s += cfg.triggerWindowMs; s += ",";
  s += "\"ldr\":";      s += cfg.ldrNightThreshold;
  s += "}";
  return s;
}

static const char INDEX_HTML[] PROGMEM = R"HTML(
<!doctype html><html lang="zh-CN"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>稻草人驱鸟控制器</title>
<style>
body{font-family:system-ui,-apple-system,"Microsoft YaHei",sans-serif;margin:0;background:#f4f6f8;color:#1f2a37}
.wrap{max-width:620px;margin:0 auto;padding:18px}
h1{font-size:20px;margin:6px 0 14px}
.card{background:#fff;border-radius:10px;padding:16px;margin-bottom:14px;box-shadow:0 1px 4px rgba(0,0,0,.08)}
.row{display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #eef1f4;font-size:14px}
.row:last-child{border:0}
label{display:flex;justify-content:space-between;align-items:center;margin:10px 0;font-size:14px}
input[type=number]{width:90px;padding:6px;border:1px solid #cfd6de;border-radius:6px}
input[type=text],input[type=password]{width:220px;padding:6px;border:1px solid #cfd6de;border-radius:6px}
button{background:#1a5c8a;color:#fff;border:0;border-radius:8px;padding:10px 16px;font-size:15px;margin-top:8px}
button.gray{background:#5a636e}
.ok{color:#177245;font-weight:600}.warn{color:#b45309;font-weight:600}
</style></head><body><div class="wrap">
<h1>稻草人驱鸟控制器</h1>
<div style="font-size:13px;color:#5a636e;margin:-6px 0 10px">设备热点 192.168.4.1 始终可用；连上路由器后也可用局域网地址访问。</div>
<div class="card" id="st">读取中…</div>
<form class="card" id="f">
<label>白天音量 (0-30)<input type="number" name="volDay" min="0" max="30"></label>
<label>夜间音量 (0-30)<input type="number" name="volNight" min="0" max="30"></label>
<label>灵敏度 (1-8 次脉冲)<input type="number" name="sens" min="1" max="8"></label>
<label>冷却时间 (秒)<input type="number" name="cool" min="5" max="3600"></label>
<label>音轨数量<input type="number" name="tracks" min="1" max="99"></label>
<label>静音开始 (0-23)<input type="number" name="qStart" min="0" max="23"></label>
<label>静音结束 (0-23)<input type="number" name="qEnd" min="0" max="23"></label>
<label>启用静音时段<input type="checkbox" id="qEnableBox"></label>
<div id="msg" style="font-size:13px;color:#177245;min-height:18px"></div>
<button type="submit">保存配置</button>
<button type="button" class="gray" onclick="fetch('/test')">立即试驱</button>
</form>
<script>
function esc(v){
  return String(v==null?'':v).replace(/[&<>"]/g,function(c){
    return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];
  });
}
function showError(msg){
  document.getElementById('st').innerHTML=
    '<div class="row"><span>连接状态</span><b class="warn">读取失败</b></div>'+
    '<div class="row"><span>原因</span><span>'+esc(msg)+'</span></div>'+
    '<div class="row"><span>当前地址</span><span>'+esc(location.href)+'</span></div>'+
    '<div class="row"><span>排查</span><span>连 Scarecrow-XXXX 热点，用 http://192.168.4.1/ 打开</span></div>';
}
async function load(){
  try{
    const r=await fetch('/api/status',{cache:'no-store'});
    if(!r.ok) throw new Error('HTTP '+r.status);
    const txt=await r.text();
    let s;
    try{ s=JSON.parse(txt); }
    catch(e){ throw new Error('返回数据异常：'+txt.slice(0,80)); }
    document.getElementById('st').innerHTML=
      '<div class="row"><span>状态</span><b>'+esc(s.state)+'</b></div>'+
      '<div class="row"><span>电池</span><b class="'+(Number(s.vbat)<11?'warn':'ok')+'">'+Number(s.vbat).toFixed(2)+' V</b></div>'+
      '<div class="row"><span>光照</span><span>'+(s.night?'夜间':'白天')+'</span></div>'+
      '<div class="row"><span>静音时段</span><span>'+(s.quiet?'生效中':'未生效')+'</span></div>'+
      '<div class="row"><span>雷达脉冲累计</span><span>'+esc(s.pulses)+'</span></div>'+
      '<div class="row"><span>热点地址</span><span>'+esc(s.apIp||'192.168.4.1')+'</span></div>'+
      '<div class="row"><span>局域网地址</span><span>'+esc(s.staIp||'未连接')+'</span></div>';
    const f=document.getElementById('f');
    f.volDay.value=s.volDay; f.volNight.value=s.volNight; f.sens.value=s.sens;
    f.cool.value=s.cool; f.tracks.value=s.tracks; f.qStart.value=s.qStart; f.qEnd.value=s.qEnd;
    document.getElementById('qEnableBox').checked=!!s.qEnable;
  }catch(e){
    showError(e && e.message ? e.message : e);
  }
}
document.getElementById('f').onsubmit=async e=>{
  e.preventDefault();
  const msg=document.getElementById('msg');
  const fd=new FormData(e.target);
  fd.set('qEnable',document.getElementById('qEnableBox').checked?'1':'0');
  try{
    const r=await fetch('/save',{method:'POST',body:new URLSearchParams(fd)});
    if(!r.ok) throw new Error('HTTP '+r.status);
    msg.style.color='#177245'; msg.textContent='配置已保存';
    load();
  }catch(err){
    msg.style.color='#b45309'; msg.textContent='保存失败：'+err.message;
  }
};
load(); setInterval(load,3000);
</script></div></body></html>
)HTML";

static void handleRoot() {
  server.sendHeader("Cache-Control", "no-store, no-cache, must-revalidate");
  server.send_P(200, "text/html; charset=utf-8", INDEX_HTML);
}

static void sendJson(const String &body) {
  server.sendHeader("Cache-Control", "no-store");
  server.send(200, "application/json", body);
}

static void handleStatus() {
  sendJson(statusJson());
}

static void applyConfigFromRequest() {
  if (server.hasArg("volDay"))   cfg.volumeDay  = constrain(server.arg("volDay").toInt(), 0, 30);
  if (server.hasArg("volNight")) cfg.volumeNight = constrain(server.arg("volNight").toInt(), 0, 30);
  if (server.hasArg("sens"))     cfg.sensitivity = constrain(server.arg("sens").toInt(), 1, 8);
  if (server.hasArg("cool"))     cfg.cooldownSec = constrain(server.arg("cool").toInt(), 5, 3600);
  if (server.hasArg("tracks"))   cfg.trackCount  = constrain(server.arg("tracks").toInt(), 1, 99);
  if (server.hasArg("qStart"))   cfg.quietStartHour = constrain(server.arg("qStart").toInt(), 0, 23);
  if (server.hasArg("qEnd"))     cfg.quietEndHour   = constrain(server.arg("qEnd").toInt(), 0, 23);
  if (server.hasArg("qEnable"))  cfg.quietHoursEnable = server.arg("qEnable").toInt() ? 1 : 0;

  if (server.hasArg("activeMin")) {
    cfg.activeMinMs = constrain(server.arg("activeMin").toInt(), 2000L, 120000L);
  }
  if (server.hasArg("activeMax")) {
    cfg.activeMaxMs = constrain(server.arg("activeMax").toInt(), 2000L, 120000L);
  }
  if (cfg.activeMaxMs < cfg.activeMinMs + 1000) {
    cfg.activeMaxMs = cfg.activeMinMs + 1000;
  }
  if (server.hasArg("trigger")) {
    cfg.triggerWindowMs = constrain(server.arg("trigger").toInt(), 500L, 10000L);
  }
  if (server.hasArg("ldr")) {
    cfg.ldrNightThreshold = constrain(server.arg("ldr").toInt(), 0L, 4095L);
  }

  configSave();
  radar.setSensitivity(cfg.sensitivity);
  radar.setWindow(cfg.triggerWindowMs);
}

static void handleSave() {
  applyConfigFromRequest();
  server.sendHeader("Location", "/");
  server.send(303);
}

static void handleConfigGet() {
  sendJson(configJson());
}

static void handleConfigPost() {
  applyConfigFromRequest();
  sendJson(statusJson());
}

// 分项测试：sound / light / servo / stop / all
static void beginTestOutput(uint8_t mode, uint32_t ms) {
  testMode  = mode;
  testUntil = millis() + ms;
  testNext  = 0;
  testRed   = true;
}

static void handleTestAction() {
  String what = server.arg("what");
  if (what.length() == 0) what = "all";

  if (what == "sound") {
    stopDeterrent();
    player.setVolume(cfg.volumeDay);
    activeTrack = (uint16_t)random(1, (long)cfg.trackCount + 1);
    player.playTrack(activeTrack);
    beginTestOutput(1, 5000);
  } else if (what == "light") {
    stopDeterrent();
    beginTestOutput(2, 4000);
  } else if (what == "servo") {
    stopDeterrent();
    beginTestOutput(3, 4000);
  } else if (what == "stop") {
    stopDeterrent();
  } else {
    startDeterrent(true);
  }

  server.send(200, "application/json", "{\"ok\":1}");
}

static void handleTest() {
  startDeterrent(true);
  server.send(200, "text/plain", "ok");
}

static void handleReset() {
  configReset();
  configSave();
  server.send(200, "text/plain", "reset, reboot to apply wifi");
}

static void handleApiReset() {
  configReset();
  configSave();
  radar.setSensitivity(cfg.sensitivity);
  radar.setWindow(cfg.triggerWindowMs);
  server.send(200, "application/json", "{\"ok\":1}");
}

static void handleReboot() {
  server.send(200, "application/json", "{\"ok\":1,\"reboot\":1}");
  delay(150);
  ESP.restart();
}

static void webBegin() {
  // AP + STA 共存：热点常开，192.168.4.1 永远可访问；
  // 配了路由器凭据时同时连路由器，连不上也不影响本地网页。
  WiFi.mode(WIFI_AP_STA);
  WiFi.setSleep(false);
  WiFi.setAutoReconnect(true);

  String ap = "Scarecrow-" + String((uint32_t)(ESP.getEfuseMac() & 0xFFFF), HEX);
  IPAddress apIp(192, 168, 4, 1);
  IPAddress apMask(255, 255, 255, 0);
  WiFi.softAPConfig(apIp, apIp, apMask);
  bool apOk = WiFi.softAP(ap.c_str(), "scarecrow");
  Serial.printf("[WIFI] AP %s  http://%s/  %s\n",
                ap.c_str(), WiFi.softAPIP().toString().c_str(),
                apOk ? "ok" : "FAILED");

  if (strlen(cfg.wifiSsid) > 0) {
    WiFi.begin(cfg.wifiSsid, cfg.wifiPass);
    uint32_t t0 = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - t0 < 8000) {
      delay(200);
      Serial.print('.');
    }
  }

  if (WiFi.status() == WL_CONNECTED) {
    wifiOnline = true;
    Serial.printf("\n[WIFI] STA %s  http://%s/\n",
                  WiFi.SSID().c_str(), WiFi.localIP().toString().c_str());
    configTime(8 * 3600, 0, "ntp.aliyun.com", "ntp.tencent.com", "pool.ntp.org");
  } else {
    wifiOnline = false;
    Serial.println("\n[WIFI] STA 未连接，热点保持可用");
  }

  server.on("/", handleRoot);
  server.on("/api/status", handleStatus);
  server.on("/api/config", HTTP_GET, handleConfigGet);
  server.on("/api/config", HTTP_POST, handleConfigPost);
  server.on("/api/test", HTTP_GET, handleTestAction);
  server.on("/api/test", HTTP_POST, handleTestAction);
  server.on("/api/reboot", HTTP_POST, handleReboot);
  server.on("/api/reset", HTTP_POST, handleApiReset);
  server.on("/save", HTTP_POST, handleSave);
  server.on("/test", handleTest);
  server.on("/reset", handleReset);
  server.begin();

  if (MDNS.begin("scarecrow")) {
    MDNS.addService("http", "tcp", 80);
    Serial.println("[MDNS] http://scarecrow.local/");
  }

  ArduinoOTA.setHostname("scarecrow");
  ArduinoOTA.begin();
}

// STA 断线重连后同步状态；AP 一直保持，不影响网页访问
static void checkWifi() {
  static uint32_t nextCheck = 0;
  static bool started = false;
  static bool lastState = false;
  if (millis() < nextCheck) return;
  nextCheck = millis() + 5000;

  bool now = (WiFi.status() == WL_CONNECTED);
  if (!started) {
    started = true;
    lastState = now;
    return;
  }
  if (now == lastState) return;
  lastState = now;

  if (now) {
    wifiOnline = true;
    Serial.printf("[WIFI] STA %s  http://%s/\n",
                  WiFi.SSID().c_str(), WiFi.localIP().toString().c_str());
    configTime(8 * 3600, 0, "ntp.aliyun.com", "ntp.tencent.com", "pool.ntp.org");
  } else {
    wifiOnline = false;
    Serial.println("[WIFI] STA 断开，热点仍可用");
  }
}

// ---------------- 串口 CLI ----------------
static void printStatus() {
  Serial.printf("state=%s vbat=%.2f night=%d quiet=%d pulses=%lu\n",
                stateName(), outputs.batteryVoltage(), outputs.isNight(),
                isQuietHour(), (unsigned long)radar.totalPulses());
  Serial.printf("volDay=%u volNight=%u sens=%u cool=%us tracks=%u quiet=%u-%u(%u)\n",
                cfg.volumeDay, cfg.volumeNight, cfg.sensitivity, cfg.cooldownSec,
                cfg.trackCount, cfg.quietStartHour, cfg.quietEndHour, cfg.quietHoursEnable);
}

static void runCli(String line) {
  line.trim();
  if (line.length() == 0) return;

  if (line == "status") {
    printStatus();
  } else if (line == "test") {
    startDeterrent(true);
  } else if (line == "save") {
    configSave();
    Serial.println("saved");
  } else if (line == "reset") {
    configReset();
    configSave();
    Serial.println("reset");
  } else if (line.startsWith("vol ")) {
    cfg.volumeDay = constrain(line.substring(4).toInt(), 0, 30);
    player.setVolume(cfg.volumeDay);
    Serial.printf("volDay=%u\n", cfg.volumeDay);
  } else if (line.startsWith("cool ")) {
    cfg.cooldownSec = constrain(line.substring(5).toInt(), 5, 3600);
    Serial.printf("cooldown=%us\n", cfg.cooldownSec);
  } else if (line.startsWith("quiet ")) {
    cfg.quietHoursEnable = line.substring(6).toInt() ? 1 : 0;
    Serial.printf("quietHours=%u\n", cfg.quietHoursEnable);
  } else {
    Serial.println("commands: status | test | save | reset | vol N | cool N | quiet 0/1");
  }
}

static void handleSerial() {
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\r') continue;
    if (c == '\n') {
      runCli(cliLine);
      cliLine = "";
    } else if (cliLine.length() < 120) {
      cliLine += c;
    }
  }
}

// ---------------- 按钮 ----------------
static void handleButtons() {
  static bool modeWasDown = false;
  static uint32_t modeDownAt = 0;
  static bool testWasDown = false;

  bool modeDown = (digitalRead(PIN_BTN_MODE) == LOW);
  bool testDown = (digitalRead(PIN_BTN_TEST) == LOW);

  if (modeDown && !modeWasDown) {
    modeDownAt = millis();
  }
  if (!modeDown && modeWasDown) {
    uint32_t held = millis() - modeDownAt;
    if (held > 3000) {
      configReset();
      configSave();
      Serial.println("[BTN] config reset, restarting");
      delay(200);
      ESP.restart();
    } else if (held > 40) {
      startDeterrent(true);
    }
  }
  modeWasDown = modeDown;

  if (testDown && !testWasDown) {
    startDeterrent(true);
  }
  testWasDown = testDown;
}

// ---------------- 初始化 ----------------
void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.println("\n=== Scarecrow Bird Deterrent v1 ===");

  randomSeed(esp_random());

  configLoad();

  radar.setSensitivity(cfg.sensitivity);
  radar.setWindow(cfg.triggerWindowMs);

  outputs.begin();
  radar.begin();
  player.begin();

  pinMode(PIN_BTN_MODE, INPUT_PULLUP);
  pinMode(PIN_BTN_TEST, INPUT_PULLUP);

  webBegin();

  bootMs = millis();
  Serial.printf("[READY] state=%s vbat=%.2f\n", stateName(), outputs.batteryVoltage());
}

void loop() {
  uint32_t now = millis();

  server.handleClient();
  ArduinoOTA.handle();
  handleSerial();
  handleButtons();
  checkBattery();
  checkWifi();

  // 雷达计数：冷却期也持续收集，但不触发
  bool detected = radar.update();
  if (detected && state == ST_IDLE) {
    startDeterrent(false);
  }

  if (state == ST_ACTIVE) {
    if (now >= nextStrobe) {
      bool red = (random(0, 2) == 0);
      uint8_t level = (uint8_t)random(140, 256);
      if (isQuietHour()) {
        outputs.leds(0, 0);
      } else {
        outputs.leds(red ? level : 0, red ? 0 : level);
      }
      nextStrobe = now + random(120, 380);
    }

    if (now >= nextServo) {
      int16_t next = (int16_t)servoAngle + servoDir * 3;
      if (next >= 150) { next = 150; servoDir = -1; }
      if (next <= 30)  { next = 30;  servoDir = 1; }
      servoAngle = (uint8_t)next;
      outputs.servo(servoAngle);
      nextServo = now + 40;
    }

    if (now >= stateUntil) {
      Serial.printf("[DETER] done, cooldown %us\n", cfg.cooldownSec);
      player.stop();
      outputs.leds(0, 0);
      outputs.servoCenter();
      state = ST_COOLDOWN;
      stateUntil = now + (uint32_t)cfg.cooldownSec * 1000UL;
    }
  } else if (state == ST_COOLDOWN) {
    if (now >= stateUntil) {
      state = ST_IDLE;
      Serial.println("[STATE] idle");
    }
  }

  // 分项测试动画（声音测试只播一次，到时停止）
  if (testMode) {
    if (now >= testUntil) {
      player.stop();
      outputs.leds(0, 0);
      outputs.servoCenter();
      testMode = 0;
    } else if (testMode == 2 && now >= testNext) {
      testRed = !testRed;
      outputs.leds(testRed ? 220 : 0, testRed ? 0 : 220);
      testNext = now + 150;
    } else if (testMode == 3 && now >= testNext) {
      static int8_t  tDir   = 1;
      static uint8_t tAngle = 90;
      int16_t next = (int16_t)tAngle + tDir * 4;
      if (next >= 150) { next = 150; tDir = -1; }
      if (next <= 30)  { next = 30;  tDir = 1; }
      tAngle = (uint8_t)next;
      outputs.servo(tAngle);
      testNext = now + 25;
    }
  }

  // 状态灯：运行常亮，低电快闪，空闲慢闪
  if (state == ST_ACTIVE) {
    outputs.statusLed(true);
  } else if (lowBattery) {
    if (now - lastBlink > 150) {
      lastBlink = now;
      blinkOn = !blinkOn;
      outputs.statusLed(blinkOn);
    }
  } else {
    if (now - lastBlink > 1000) {
      lastBlink = now;
      blinkOn = !blinkOn;
      outputs.statusLed(blinkOn);
    }
  }

  delay(5);
}
