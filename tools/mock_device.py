"""本地模拟稻草人设备，用于验证桌面客户端而无需真实硬件。"""
import json
import re
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

STATE = {
    "api": 1, "fw": "1.1.0", "state": "ACTIVE", "vbat": 12.35,
    "night": 1, "quiet": 0, "pulses": 42, "lowBat": 0, "test": 0,
    "track": 3, "servo": 96, "volDay": 26, "volNight": 16, "sens": 3,
    "cool": 60, "tracks": 8, "qStart": 22, "qEnd": 6, "qEnable": 0,
    "activeMin": 8000, "activeMax": 18000, "trigger": 2500, "ldr": 800,
    "uptime": 3725, "mode": "AP", "ssid": "Scarecrow", "rssi": 0,
    "ip": "192.168.4.1",
}

CONFIG_KEYS = ["volDay", "volNight", "sens", "cool", "tracks",
               "qStart", "qEnd", "qEnable", "activeMin", "activeMax",
               "trigger", "ldr"]


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, code, body, ctype="application/json"):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/api/status":
            self._send(200, json.dumps(STATE))
        elif path == "/api/config":
            self._send(200, json.dumps({k: STATE[k] for k in CONFIG_KEYS}))
        elif path == "/api/test":
            STATE["state"] = "ACTIVE"
            self._send(200, '{"ok":1}')
        elif path == "/":
            self._send(200, "<h1>Scarecrow mock</h1>", "text/html")
        else:
            self._send(404, '{"err":"not found"}')

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        form = urllib.parse.parse_qs(body)
        if path == "/api/config":
            for k, v in form.items():
                if k in CONFIG_KEYS:
                    STATE[k] = int(v[0])
            self._send(200, json.dumps(STATE))
        elif path == "/api/test":
            STATE["state"] = "ACTIVE"
            self._send(200, '{"ok":1}')
        elif path == "/api/reset":
            self._send(200, '{"ok":1}')
        elif path == "/api/reboot":
            self._send(200, '{"ok":1,"reboot":1}')
        else:
            self._send(404, '{"err":"not found"}')


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", 18080), Handler).serve_forever()
