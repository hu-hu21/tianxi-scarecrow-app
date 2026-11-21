package com.tianxi.scarecrow;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.Charset;
import java.util.UUID;

/** 与 ESP32 固件的 JSON / 表单接口通信，无第三方依赖。 */
public class DeviceApi {

    private static final Charset UTF8 = Charset.forName("UTF-8");
    /** 每一个 App 进程一个客户端标识，服务器据此分配独立转发通道。 */
    private static final String CLIENT_ID =
            UUID.randomUUID().toString().replace("-", "");
    /** 登录后由 LoginActivity 写入，随每个请求发送。 */
    public static String TOKEN = "";

    public final String base;
    public final String device;

    public DeviceApi(String input) {
        this(input, null);
    }

    public DeviceApi(String input, String deviceAddress) {
        String s = input == null ? "" : input.trim();
        String d = deviceAddress == null ? "" : deviceAddress.trim();
        if (s.length() == 0) s = d.length() == 0 ? "192.168.4.1" : d;
        if (!s.startsWith("http://") && !s.startsWith("https://")) {
            s = "http://" + s;
        }
        while (s.endsWith("/")) {
            s = s.substring(0, s.length() - 1);
        }
        base = s;
        device = d;
    }

    private void applyDevice(HttpURLConnection c) {
        c.setRequestProperty("X-Client-Id", CLIENT_ID);
        if (TOKEN != null && TOKEN.length() > 0) {
            c.setRequestProperty("X-Auth-Token", TOKEN);
        }
        if (device.length() > 0) {
            c.setRequestProperty("X-Device-Address", device);
        }
    }

    public String get(String path) throws IOException {
        HttpURLConnection c = open(path, "GET");
        try {
            return read(c);
        } finally {
            c.disconnect();
        }
    }

    public String post(String path, String body) throws IOException {
        HttpURLConnection c = open(path, "POST");
        try {
            byte[] data = (body == null ? "" : body).getBytes(UTF8);
            c.setRequestProperty("Content-Type",
                    "application/x-www-form-urlencoded; charset=utf-8");
            c.setDoOutput(true);
            c.setFixedLengthStreamingMode(data.length);
            OutputStream os = c.getOutputStream();
            try {
                os.write(data);
                os.flush();
            } finally {
                os.close();
            }
            return read(c);
        } finally {
            c.disconnect();
        }
    }

    /** 发送 JSON 请求体（视觉/小车/水阀接口使用）。 */
    public String postJson(String path, String json) throws IOException {
        HttpURLConnection c = open(path, "POST", 6000);
        try {
            byte[] data = (json == null ? "{}" : json).getBytes(UTF8);
            c.setRequestProperty("Content-Type", "application/json; charset=utf-8");
            c.setDoOutput(true);
            c.setFixedLengthStreamingMode(data.length);
            OutputStream os = c.getOutputStream();
            try {
                os.write(data);
                os.flush();
            } finally {
                os.close();
            }
            return read(c);
        } finally {
            c.disconnect();
        }
    }

    /** multipart 上传单张图片（视觉识别接口使用）。 */
    public String postFile(String path, String field, String filename,
                           byte[] data, int timeoutMs) throws IOException {
        String boundary = "----tianxi" + Long.toHexString(System.currentTimeMillis());
        String head = "--" + boundary + "\r\n"
                + "Content-Disposition: form-data; name=\"" + field + "\"; filename=\""
                + filename + "\"\r\n"
                + "Content-Type: application/octet-stream\r\n\r\n";
        String tail = "\r\n--" + boundary + "--\r\n";

        ByteArrayOutputStream bos = new ByteArrayOutputStream(
                head.length() + data.length + tail.length() + 16);
        bos.write(head.getBytes(UTF8));
        bos.write(data);
        bos.write(tail.getBytes(UTF8));
        byte[] body = bos.toByteArray();

        HttpURLConnection c = (HttpURLConnection) new URL(base + path).openConnection();
        c.setRequestMethod("POST");
        c.setConnectTimeout(4000);
        c.setReadTimeout(timeoutMs);
        c.setUseCaches(false);
        c.setDoOutput(true);
        c.setFixedLengthStreamingMode(body.length);
        c.setRequestProperty("Content-Type", "multipart/form-data; boundary=" + boundary);
        c.setRequestProperty("Accept", "application/json");
        c.setRequestProperty("Connection", "close");
        applyDevice(c);
        try {
            OutputStream os = c.getOutputStream();
            try {
                os.write(body);
                os.flush();
            } finally {
                os.close();
            }
            return read(c);
        } finally {
            c.disconnect();
        }
    }

    private HttpURLConnection open(String path, String method) throws IOException {
        return open(path, method, 2600);
    }

    private HttpURLConnection open(String path, String method, int timeoutMs) throws IOException {
        HttpURLConnection c = (HttpURLConnection) new URL(base + path).openConnection();
        c.setRequestMethod(method);
        c.setConnectTimeout(2600);
        c.setReadTimeout(timeoutMs);
        c.setUseCaches(false);
        c.setRequestProperty("Accept", "application/json");
        c.setRequestProperty("Connection", "close");
        applyDevice(c);
        return c;
    }

    private String read(HttpURLConnection c) throws IOException {
        int code = c.getResponseCode();
        InputStream is = code >= 400 ? c.getErrorStream() : c.getInputStream();
        if (is == null) {
            throw new IOException("HTTP " + code);
        }
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        byte[] buf = new byte[4096];
        int n;
        try {
            while ((n = is.read(buf)) > 0) {
                bos.write(buf, 0, n);
            }
        } finally {
            is.close();
        }
        String body = new String(bos.toByteArray(), UTF8);
        if (code >= 400) {
            throw new IOException("HTTP " + code);
        }
        return body;
    }
}
