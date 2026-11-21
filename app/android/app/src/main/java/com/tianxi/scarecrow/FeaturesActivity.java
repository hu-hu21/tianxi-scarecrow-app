package com.tianxi.scarecrow;

import android.app.Activity;
import android.content.ContentResolver;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.res.ColorStateList;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.graphics.drawable.RippleDrawable;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Spinner;
import android.widget.Switch;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * 扩展功能：病虫害识别 / 防护服检测 / 驱鸟策略 / 小车路线 / 天气与水阀。
 * 视觉推理委托给局域网 AI 服务，天气数据来自 Open-Meteo（免密钥）。
 */
public class FeaturesActivity extends Activity {

    private static final int BG = 0xFF0B1220;
    private static final int CARD = 0xFF16233A;
    private static final int CARD2 = 0xFF223753;
    private static final int INPUT = 0xFF0F1B2E;
    private static final int TEXT = 0xFFE5EDF7;
    private static final int MUTED = 0xFF93A4BC;
    private static final int ACCENT = 0xFF0EA5E9;
    private static final int GREEN = 0xFF34D399;
    private static final int RED = 0xFFDC2626;
    private static final int AMBER = 0xFFF59E0B;
    private static final int LINE = 0xFF2A3B57;

    private static final int REQ_PEST = 1001;
    private static final int REQ_PPE = 1002;

    private DeviceApi api;
    private SharedPreferences prefs;
    private EditText addrView;

    private final Handler ui = new Handler(Looper.getMainLooper());
    private final AtomicBoolean alive = new AtomicBoolean(false);
    private final Map<String, VisionSlot> slots = new HashMap<String, VisionSlot>();

    private TextView robotState;
    private EditText routeView;
    private TextView weatherView;
    private TextView valveView;
    private Switch autoSwitch;
    private EditText latView, lonView, humidityView, tminView, tmaxView;

    // ---------------------------------------------------------------- 结构

    static class Det {
        String label;
        double conf;
        float[] box;
    }

    static class VisionSlot {
        final String kind;
        Uri uri;
        ImageView view;
        BoxOverlay overlay;
        TextView result;
        EditText camera;
        Button liveBtn;
        volatile boolean live;
        volatile byte[] frame;
        volatile HttpURLConnection conn;
        Thread reader, detector;
        int iw, ih;

        VisionSlot(String kind) {
            this.kind = kind;
        }
    }

    static class BoxOverlay extends View {
        private final List<Det> dets = new ArrayList<Det>();
        private int imgW, imgH;
        private boolean alarm;
        private final Paint boxPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final Paint textPaint = new Paint(Paint.ANTI_ALIAS_FLAG);

        BoxOverlay(android.content.Context c) {
            super(c);
            boxPaint.setStyle(Paint.Style.STROKE);
            boxPaint.setStrokeWidth(4f);
            textPaint.setTextSize(26f);
            textPaint.setTypeface(Typeface.DEFAULT_BOLD);
        }

        void setData(List<Det> list, int w, int h, boolean isAlarm) {
            dets.clear();
            if (list != null) dets.addAll(list);
            imgW = w;
            imgH = h;
            alarm = isAlarm;
            invalidate();
        }

        void clear() {
            dets.clear();
            imgW = 0;
            imgH = 0;
            invalidate();
        }

        @Override
        protected void onDraw(Canvas canvas) {
            super.onDraw(canvas);
            if (imgW <= 0 || imgH <= 0 || dets.isEmpty()) return;
            float s = Math.min((float) getWidth() / imgW, (float) getHeight() / imgH);
            float ox = (getWidth() - imgW * s) / 2f;
            float oy = (getHeight() - imgH * s) / 2f;
            for (Det d : dets) {
                int color = alarm ? RED : GREEN;
                boxPaint.setColor(color);
                textPaint.setColor(color);
                float l = ox + d.box[0] * s;
                float t = oy + d.box[1] * s;
                float r = ox + d.box[2] * s;
                float b = oy + d.box[3] * s;
                canvas.drawRect(l, t, r, b, boxPaint);
                String label = d.label == null ? "" : d.label;
                if (d.conf > 0) label = label + " " + Math.round(d.conf * 100) + "%";
                canvas.drawText(label, l + 6, Math.max(t - 8, 26), textPaint);
            }
        }
    }

    // ---------------------------------------------------------------- 生命周期

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setStatusBarColor(BG);
        getWindow().setNavigationBarColor(BG);

        prefs = getSharedPreferences("scarecrow", MODE_PRIVATE);
        String ip = getIntent().getStringExtra("ip");
        if (ip == null || ip.trim().length() == 0) {
            ip = prefs.getString("ip", "192.168.4.1");
        }
        api = new DeviceApi(ip);

        setContentView(buildUi(ip));
        alive.set(true);
        ui.post(robotPoll);
    }

    @Override
    protected void onResume() {
        super.onResume();
        alive.set(true);
        ui.removeCallbacks(robotPoll);
        ui.postDelayed(robotPoll, 1200);
    }

    @Override
    protected void onPause() {
        super.onPause();
        alive.set(false);
        ui.removeCallbacks(robotPoll);
        for (VisionSlot s : slots.values()) {
            if (s.live) stopLive(s, null);
        }
    }

    private final Runnable robotPoll = new Runnable() {
        @Override
        public void run() {
            if (!alive.get()) return;
            pollRobot();
            ui.postDelayed(this, 2500);
        }
    };

    // ---------------------------------------------------------------- 控件工具

    private int dp(float v) {
        return (int) (v * getResources().getDisplayMetrics().density + 0.5f);
    }

    private TextView tv(String text, float sp, int color, boolean bold) {
        TextView t = new TextView(this);
        t.setText(text);
        t.setTextSize(sp);
        t.setTextColor(color);
        t.setIncludeFontPadding(false);
        if (bold) t.setTypeface(Typeface.DEFAULT_BOLD);
        return t;
    }

    private LinearLayout vbox() {
        LinearLayout l = new LinearLayout(this);
        l.setOrientation(LinearLayout.VERTICAL);
        return l;
    }

    private LinearLayout hbox() {
        LinearLayout l = new LinearLayout(this);
        l.setOrientation(LinearLayout.HORIZONTAL);
        l.setGravity(Gravity.CENTER_VERTICAL);
        return l;
    }

    private GradientDrawable shape(int color, float radius) {
        GradientDrawable g = new GradientDrawable();
        g.setColor(color);
        g.setCornerRadius(dp(radius));
        return g;
    }

    private LinearLayout card(String title) {
        LinearLayout c = vbox();
        c.setBackground(shape(CARD, 14));
        c.setPadding(dp(16), dp(14), dp(16), dp(14));
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        p.topMargin = dp(12);
        c.setLayoutParams(p);
        if (title != null) {
            TextView t = tv(title, 15f, TEXT, true);
            t.setPadding(0, 0, 0, dp(6));
            c.addView(t);
        }
        return c;
    }

    private Button button(String text, int color) {
        Button b = new Button(this);
        b.setText(text);
        b.setTextSize(14f);
        b.setTextColor(Color.WHITE);
        b.setAllCaps(false);
        b.setTypeface(Typeface.DEFAULT_BOLD);
        b.setPadding(0, 0, 0, 0);
        b.setMinHeight(0);
        b.setMinimumHeight(0);
        b.setStateListAnimator(null);
        GradientDrawable bg = shape(color, 10);
        b.setBackground(new RippleDrawable(ColorStateList.valueOf(0x33FFFFFF), bg, null));
        b.setLayoutParams(new LinearLayout.LayoutParams(0, dp(44), 1f));
        return b;
    }

    private Button wideButton(String text, int color) {
        Button b = button(text, color);
        b.setLayoutParams(new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(44)));
        return b;
    }

    private LinearLayout buttonRow(Button left, Button right) {
        LinearLayout row = hbox();
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0, dp(44), 1f);
        lp.leftMargin = dp(4);
        lp.rightMargin = dp(4);
        left.setLayoutParams(lp);
        row.addView(left);
        row.addView(right);
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        p.topMargin = dp(8);
        row.setLayoutParams(p);
        return row;
    }

    private EditText input(String value, String hint, int inputType) {
        EditText e = new EditText(this);
        e.setText(value == null ? "" : value);
        e.setTextSize(14f);
        e.setTextColor(TEXT);
        e.setHintTextColor(MUTED);
        e.setHint(hint == null ? "" : hint);
        e.setSingleLine(true);
        e.setInputType(inputType);
        e.setBackground(shape(INPUT, 8));
        e.setPadding(dp(10), dp(8), dp(10), dp(8));
        return e;
    }

    private TextView caption(String text) {
        TextView t = tv(text, 12.5f, MUTED, false);
        t.setLineSpacing(dp(2), 1f);
        return t;
    }

    // ---------------------------------------------------------------- 界面

    private View buildUi(String ip) {
        ScrollView scroll = new ScrollView(this);
        scroll.setBackgroundColor(BG);
        scroll.setFillViewport(true);

        LinearLayout root = vbox();
        root.setPadding(dp(16), dp(14), dp(16), dp(28));
        scroll.addView(root);

        root.addView(tv("扩展功能", 26f, TEXT, true));
        TextView sub = tv("视觉识别 · 驱鸟策略 · 小车路线 · 天气与水阀", 12f, MUTED, false);
        sub.setPadding(0, dp(4), 0, 0);
        root.addView(sub);

        // 服务地址
        LinearLayout conn = card(null);
        LinearLayout row = hbox();
        TextView l = tv("服务地址", 13f, MUTED, false);
        l.setLayoutParams(new LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        row.addView(l);
        conn.addView(row);

        LinearLayout addrRow = hbox();
        addrView = input(api.base.replace("http://", ""), "192.168.4.1",
                android.text.InputType.TYPE_CLASS_TEXT);
        addrView.setLayoutParams(new LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        addrRow.addView(addrView);

        Button apply = button("应用", ACCENT);
        apply.setLayoutParams(new LinearLayout.LayoutParams(dp(78), dp(42)));
        addrRow.addView(apply);

        LinearLayout.LayoutParams addrLp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        addrLp.topMargin = dp(8);
        conn.addView(addrRow, addrLp);
        root.addView(conn);

        apply.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                String s = addrView.getText().toString().trim();
                if (s.length() == 0) s = "192.168.4.1";
                prefs.edit().putString("ip", s).apply();
                api = new DeviceApi(s);
                addrView.setText(api.base.replace("http://", ""));
                toast("已切换到 " + api.base);
            }
        });

        addVisionCard(root, "pest", "病虫害识别",
                "接入摄像头实时画面，由局域网 YOLOv8 服务识别虫害与病斑并标注位置。");
        addVisionCard(root, "ppe", "人员防护服检测",
                "接入摄像头实时画面，由 YOLOv8 检测安全帽与防护服，未穿戴时报警。");
        addStrategyCard(root);
        addRobotCard(root);
        addWeatherCard(root);
        return scroll;
    }

    // ---------------------------------------------------------------- 视觉

    private void addVisionCard(LinearLayout root, final String kind,
                               String title, String desc) {
        LinearLayout c = card(title);
        c.addView(caption(desc));

        final VisionSlot slot = new VisionSlot(kind);
        slots.put(kind, slot);

        FrameLayout frame = new FrameLayout(this);
        frame.setBackground(shape(INPUT, 10));
        LinearLayout.LayoutParams fp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(190));
        fp.topMargin = dp(10);
        c.addView(frame, fp);

        slot.view = new ImageView(this);
        slot.view.setScaleType(ImageView.ScaleType.FIT_CENTER);
        frame.addView(slot.view, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));

        slot.overlay = new BoxOverlay(this);
        frame.addView(slot.overlay, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));

        slot.camera = input(api.base + "/api/camera/stream",
                "http://192.168.4.1/api/camera/stream",
                android.text.InputType.TYPE_CLASS_TEXT);
        LinearLayout.LayoutParams clp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        clp.topMargin = dp(8);
        c.addView(slot.camera, clp);

        slot.liveBtn = button("开始实时", ACCENT);
        Button stopBtn = button("停止", CARD2);
        c.addView(buttonRow(slot.liveBtn, stopBtn));

        Button pick = wideButton("单张图片", CARD2);
        LinearLayout.LayoutParams pkLp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(44));
        pkLp.topMargin = dp(8);
        c.addView(pick, pkLp);

        slot.result = caption("尚未识别");
        slot.result.setPadding(0, dp(8), 0, 0);
        c.addView(slot.result);
        root.addView(c);

        slot.liveBtn.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                if (slot.live) {
                    stopLive(slot, "实时识别已停止");
                } else {
                    startLive(slot);
                }
            }
        });

        stopBtn.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                stopLive(slot, "实时识别已停止");
            }
        });

        pick.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                stopLive(slot, null);
                Intent it = new Intent(Intent.ACTION_GET_CONTENT);
                it.setType("image/*");
                it.addCategory(Intent.CATEGORY_OPENABLE);
                try {
                    startActivityForResult(Intent.createChooser(it, "选择图片"),
                            "pest".equals(kind) ? REQ_PEST : REQ_PPE);
                } catch (Exception e) {
                    toast("没有可用的图片选择器");
                }
            }
        });
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (resultCode != RESULT_OK || data == null || data.getData() == null) return;
        final VisionSlot slot = requestCode == REQ_PEST ? slots.get("pest")
                : requestCode == REQ_PPE ? slots.get("ppe") : null;
        if (slot == null) return;

        final Uri uri = data.getData();
        slot.uri = uri;
        slot.result.setText("正在加载图片…");
        new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    final Bitmap bmp = decode(uri);
                    runOnUiThread(new Runnable() {
                        @Override
                        public void run() {
                            slot.view.setImageBitmap(bmp);
                            slot.overlay.clear();
                            slot.iw = bmp.getWidth();
                            slot.ih = bmp.getHeight();
                            slot.result.setText(String.format(Locale.US,
                                    "已选择 %d × %d 像素，正在识别…",
                                    bmp.getWidth(), bmp.getHeight()));
                            recognize(slot, slot.kind);
                        }
                    });
                } catch (final Exception e) {
                    runOnUiThread(new Runnable() {
                        @Override
                        public void run() {
                            slot.uri = null;
                            slot.result.setText("图片读取失败：" + errMsg(e));
                        }
                    });
                }
            }
        }).start();
    }

    private Bitmap decode(Uri uri) throws IOException {
        ContentResolver cr = getContentResolver();
        BitmapFactory.Options probe = new BitmapFactory.Options();
        probe.inJustDecodeBounds = true;
        InputStream is = cr.openInputStream(uri);
        if (is == null) throw new IOException("无法打开图片");
        try {
            BitmapFactory.decodeStream(is, null, probe);
        } finally {
            is.close();
        }
        if (probe.outWidth <= 0 || probe.outHeight <= 0) {
            throw new IOException("不是有效的图片");
        }
        int sample = 1;
        while (probe.outWidth / (sample * 2) >= 1600
                || probe.outHeight / (sample * 2) >= 1600) {
            sample *= 2;
        }
        BitmapFactory.Options opt = new BitmapFactory.Options();
        opt.inSampleSize = sample;
        is = cr.openInputStream(uri);
        if (is == null) throw new IOException("无法打开图片");
        try {
            Bitmap bmp = BitmapFactory.decodeStream(is, null, opt);
            if (bmp == null) throw new IOException("图片解码失败");
            return bmp;
        } finally {
            is.close();
        }
    }

    private void recognize(final VisionSlot slot, final String kind) {
        if (slot.uri == null) {
            toast("请先选择一张图片");
            return;
        }
        final DeviceApi call = api;
        slot.result.setText("识别中，请稍候…");

        new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    byte[] data = readAll(slot.uri);
                    if (data.length > 12 * 1024 * 1024) {
                        throw new IOException("图片超过 12MB，请换一张");
                    }
                    final String res = call.postFile(
                            "/api/vision/detect?kind=" + kind,
                            "image", "image.jpg", data, 30000);
                    final JSONObject d = new JSONObject(res);
                    runOnUiThread(new Runnable() {
                        @Override
                        public void run() {
                            applyVision(slot, d, kind);
                        }
                    });
                } catch (final Exception e) {
                    runOnUiThread(new Runnable() {
                        @Override
                        public void run() {
                            slot.overlay.clear();
                            slot.result.setText("识别失败：" + errMsg(e));
                            slot.result.setTextColor(RED);
                        }
                    });
                }
            }
        }).start();
    }

    private byte[] readAll(Uri uri) throws IOException {
        InputStream is = getContentResolver().openInputStream(uri);
        if (is == null) throw new IOException("无法打开图片");
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        byte[] buf = new byte[8192];
        int n;
        try {
            while ((n = is.read(buf)) > 0) bos.write(buf, 0, n);
        } finally {
            is.close();
        }
        return bos.toByteArray();
    }

    private void applyVision(VisionSlot slot, JSONObject d, String kind) {
        boolean alarm = d.optBoolean("alarm", false);
        int iw = d.optInt("image_w", 0);
        int ih = d.optInt("image_h", 0);

        List<Det> dets = new ArrayList<Det>();
        JSONArray arr = d.optJSONArray("detections");
        if (arr != null) {
            for (int i = 0; i < arr.length(); i++) {
                JSONObject o = arr.optJSONObject(i);
                if (o == null) continue;
                Det det = new Det();
                det.label = o.optString("label", o.optString("label_en", "目标"));
                det.conf = o.optDouble("confidence", 0);
                JSONArray box = o.optJSONArray("box");
                det.box = new float[4];
                if (box != null && box.length() >= 4) {
                    for (int k = 0; k < 4; k++) {
                        det.box[k] = (float) box.optDouble(k, 0);
                    }
                }
                dets.add(det);
            }
        }
        if (iw <= 0) iw = d.optInt("width", 0);
        if (ih <= 0) ih = d.optInt("height", 0);
        if (iw <= 0) iw = slot.iw;
        if (ih <= 0) ih = slot.ih;
        if (iw <= 0 && slot.view.getDrawable() instanceof android.graphics.drawable.BitmapDrawable) {
            Bitmap b = ((android.graphics.drawable.BitmapDrawable) slot.view.getDrawable()).getBitmap();
            iw = b.getWidth();
            ih = b.getHeight();
        }

        slot.overlay.setData(dets, iw, ih, alarm);

        long cost = d.optLong("cost_ms", 0);
        StringBuilder sb = new StringBuilder();
        if ("ppe".equals(kind)) {
            sb.append("人员数量：").append(d.optInt("person_count", 0))
                    .append("  ·  报警：").append(alarm ? "是" : "否");
        } else {
            sb.append("识别到 ").append(dets.size()).append(" 个目标");
        }
        if (cost > 0) sb.append("  ·  ").append(cost).append(" ms");
        sb.append('\n');
        if (dets.isEmpty()) {
            sb.append("未发现需要处理的目标");
        } else {
            for (int i = 0; i < dets.size(); i++) {
                Det det = dets.get(i);
                if (i > 0) sb.append('\n');
                sb.append("· ").append(det.label);
                if (det.conf > 0) {
                    sb.append(String.format(Locale.US, "  %.0f%%", det.conf * 100));
                }
            }
        }
        slot.result.setText(sb.toString());
        slot.result.setTextColor(alarm ? RED : TEXT);
    }

    // ---------------------------------------------------------------- 驱鸟策略

    private void addStrategyCard(LinearLayout root) {
        LinearLayout c = card("驱鸟策略");
        c.addView(caption("雷达检测到移动后先做视觉确认，可减少误触发。"));

        LinearLayout row = hbox();
        TextView l = tv("触发方式", 13f, MUTED, false);
        l.setLayoutParams(new LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        row.addView(l);

        final Spinner sp = new Spinner(this);
        ArrayAdapter<String> ad = new ArrayAdapter<String>(this,
                android.R.layout.simple_spinner_item,
                new String[] { "雷达触发", "视觉触发", "雷达 + 视觉" });
        ad.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        sp.setAdapter(ad);
        sp.setLayoutParams(new LinearLayout.LayoutParams(dp(150),
                ViewGroup.LayoutParams.WRAP_CONTENT));
        row.addView(sp);
        LinearLayout.LayoutParams rlp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        rlp.topMargin = dp(6);
        c.addView(row, rlp);

        LinearLayout coolRow = hbox();
        TextView cl = tv("视觉冷却(秒)", 13f, MUTED, false);
        coolRow.addView(cl);
        final EditText cool = input("120", "120", android.text.InputType.TYPE_CLASS_NUMBER);
        LinearLayout.LayoutParams clp = new LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
        clp.leftMargin = dp(12);
        coolRow.addView(cool, clp);
        LinearLayout.LayoutParams coolLp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        coolLp.topMargin = dp(6);
        c.addView(coolRow, coolLp);

        final TextView out = caption("尚未读取");
        out.setPadding(0, dp(8), 0, 0);
        c.addView(out);

        Button applyBtn = button("应用策略", ACCENT);
        Button testBtn = button("立即驱赶", CARD2);
        c.addView(buttonRow(applyBtn, testBtn));

        Button readBtn = wideButton("读取当前状态", CARD2);
        LinearLayout.LayoutParams rbLp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(44));
        rbLp.topMargin = dp(8);
        c.addView(readBtn, rbLp);
        root.addView(c);

        applyBtn.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                String[] map = new String[] { "radar", "vision", "both" };
                int idx = sp.getSelectedItemPosition();
                if (idx < 0 || idx > 2) idx = 0;
                int sec = parseInt(cool.getText().toString(), 120);
                if (sec < 30) sec = 30;
                if (sec > 3600) sec = 3600;
                final DeviceApi call = api;
                final String body = "strategy=" + map[idx] + "&visionCool=" + sec;
                new Thread(new Runnable() {
                    @Override
                    public void run() {
                        try {
                            final String res = call.post("/api/config", body);
                            postText(out, "策略已应用：" + res, GREEN);
                        } catch (Exception e) {
                            postText(out, "应用失败：" + errMsg(e), RED);
                        }
                    }
                }).start();
            }
        });

        testBtn.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                final DeviceApi call = api;
                new Thread(new Runnable() {
                    @Override
                    public void run() {
                        try {
                            call.post("/api/test?what=all", "");
                            postText(out, "已触发一次驱赶", GREEN);
                        } catch (Exception e) {
                            postText(out, "触发失败：" + errMsg(e), RED);
                        }
                    }
                }).start();
            }
        });

        readBtn.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                final DeviceApi call = api;
                new Thread(new Runnable() {
                    @Override
                    public void run() {
                        try {
                            JSONObject d = new JSONObject(call.get("/api/status"));
                            String s = "状态 " + d.optString("state", "-")
                                    + " · 模式 " + d.optString("mode", "-")
                                    + " · 策略 " + d.optString("strategy", "-");
                            postText(out, s, TEXT);
                        } catch (Exception e) {
                            postText(out, "读取失败：" + errMsg(e), RED);
                        }
                    }
                }).start();
            }
        });
    }

    // ---------------------------------------------------------------- 小车路线

    private void addRobotCard(LinearLayout root) {
        LinearLayout c = card("小车固定路线");
        c.addView(caption("每行一个航点：x,y,动作,停留秒数。动作可选 none / spray / water / photo / wait，最多 64 个点。"));

        robotState = caption("小车状态：--");
        robotState.setTextColor(TEXT);
        LinearLayout.LayoutParams slp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        slp.topMargin = dp(8);
        c.addView(robotState, slp);

        routeView = new EditText(this);
        routeView.setText("0,0,none,0\n5,0,spray,3\n5,5,photo,0\n0,5,wait,2");
        routeView.setTextSize(13f);
        routeView.setTextColor(TEXT);
        routeView.setTypeface(Typeface.MONOSPACE);
        routeView.setBackground(shape(INPUT, 8));
        routeView.setPadding(dp(10), dp(8), dp(10), dp(8));
        routeView.setGravity(Gravity.TOP | Gravity.START);
        routeView.setMinLines(4);
        routeView.setInputType(android.text.InputType.TYPE_CLASS_TEXT
                | android.text.InputType.TYPE_TEXT_FLAG_MULTI_LINE);
        LinearLayout.LayoutParams rlp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(118));
        rlp.topMargin = dp(8);
        c.addView(routeView, rlp);

        Button upload = wideButton("下发路线", ACCENT);
        LinearLayout.LayoutParams ulp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(44));
        ulp.topMargin = dp(8);
        c.addView(upload, ulp);

        Button start = button("启动", GREEN);
        Button pause = button("暂停", AMBER);
        c.addView(buttonRow(start, pause));

        Button stop = button("停止", RED);
        Button home = button("回原点", CARD2);
        c.addView(buttonRow(stop, home));
        root.addView(c);

        upload.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                final String json;
                try {
                    json = buildRoute(routeView.getText().toString());
                } catch (Exception e) {
                    toast("路线格式错误：" + e.getMessage());
                    return;
                }
                new Thread(new Runnable() {
                    @Override
                    public void run() {
                        try {
                            api.postJson("/api/robot/route", json);
                            toast("路线已下发");
                        } catch (Exception e) {
                            toast("下发失败：" + errMsg(e));
                        }
                    }
                }).start();
            }
        });

        start.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                robotControl("start");
            }
        });
        pause.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                robotControl("pause");
            }
        });
        stop.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                robotControl("stop");
            }
        });
        home.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                robotControl("home");
            }
        });
    }

    private String buildRoute(String text) throws Exception {
        JSONArray wp = new JSONArray();
        String[] lines = text.split("\n");
        for (String line : lines) {
            line = line.trim();
            if (line.length() == 0 || line.startsWith("#")) continue;
            String[] p = line.split("[,，\\s]+");
            if (p.length < 2) throw new Exception("每行至少要有 x,y");
            JSONObject o = new JSONObject();
            o.put("x", Double.parseDouble(p[0]));
            o.put("y", Double.parseDouble(p[1]));
            o.put("action", p.length > 2 && p[2].length() > 0 ? p[2] : "none");
            o.put("wait_s", p.length > 3 ? Double.parseDouble(p[3]) : 0);
            wp.put(o);
        }
        if (wp.length() == 0) throw new Exception("至少需要一个航点");
        if (wp.length() > 64) throw new Exception("航点最多 64 个");
        JSONObject route = new JSONObject();
        route.put("loop", false);
        route.put("waypoints", wp);
        return route.toString();
    }

    private void robotControl(final String action) {
        new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    api.postJson("/api/robot/control", "{\"action\":\"" + action + "\"}");
                    toast("指令已发送：" + action);
                } catch (Exception e) {
                    toast("指令失败：" + errMsg(e));
                }
            }
        }).start();
    }

    private void pollRobot() {
        if (robotState == null) return;
        final DeviceApi call = api;
        new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    final JSONObject d = new JSONObject(call.get("/api/robot/state"));
                    runOnUiThread(new Runnable() {
                        @Override
                        public void run() {
                            robotState.setText(String.format(Locale.US,
                                    "模式 %s · 航点 %d/%d · 坐标 (%.1f, %.1f) · 电量 %d%%",
                                    d.optString("mode", "-"), d.optInt("waypoint", 0),
                                    d.optInt("total", 0), d.optDouble("x", 0),
                                    d.optDouble("y", 0), d.optInt("battery", 0)));
                            robotState.setTextColor(TEXT);
                        }
                    });
                } catch (final Exception e) {
                    runOnUiThread(new Runnable() {
                        @Override
                        public void run() {
                            robotState.setText("小车未连接或固件不支持该接口");
                            robotState.setTextColor(MUTED);
                        }
                    });
                }
            }
        }).start();
    }

    // ---------------------------------------------------------------- 天气与水阀

    private void addWeatherCard(LinearLayout root) {
        LinearLayout c = card("天气预报与水阀");
        c.addView(caption("按经纬度读取实时天气，结合温湿度判断是否需要灌溉。"));

        LinearLayout coordRow = hbox();
        latView = input("30.28", "纬度", android.text.InputType.TYPE_CLASS_NUMBER
                | android.text.InputType.TYPE_NUMBER_FLAG_DECIMAL);
        lonView = input("120.15", "经度", android.text.InputType.TYPE_CLASS_NUMBER
                | android.text.InputType.TYPE_NUMBER_FLAG_DECIMAL);
        LinearLayout.LayoutParams c1 = new LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
        LinearLayout.LayoutParams c2 = new LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
        c2.leftMargin = dp(8);
        coordRow.addView(latView, c1);
        coordRow.addView(lonView, c2);
        LinearLayout.LayoutParams crLp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        crLp.topMargin = dp(8);
        c.addView(coordRow, crLp);

        weatherView = caption("尚未获取天气");
        weatherView.setTextColor(TEXT);
        LinearLayout.LayoutParams wlp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        wlp.topMargin = dp(8);
        c.addView(weatherView, wlp);

        Button refresh = wideButton("刷新天气", ACCENT);
        LinearLayout.LayoutParams rlp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(44));
        rlp.topMargin = dp(8);
        c.addView(refresh, rlp);

        LinearLayout autoRow = hbox();
        TextView at = tv("自动灌溉规则", 13f, MUTED, false);
        at.setLayoutParams(new LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        autoRow.addView(at);
        autoSwitch = new Switch(this);
        autoSwitch.setThumbTintList(ColorStateList.valueOf(ACCENT));
        autoSwitch.setTrackTintList(ColorStateList.valueOf(LINE));
        autoRow.addView(autoSwitch);
        LinearLayout.LayoutParams arLp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        arLp.topMargin = dp(10);
        c.addView(autoRow, arLp);

        LinearLayout hRow = hbox();
        TextView hl = tv("湿度低于", 13f, MUTED, false);
        hl.setLayoutParams(new LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        hRow.addView(hl);
        humidityView = input("40", "40", android.text.InputType.TYPE_CLASS_NUMBER);
        humidityView.setLayoutParams(new LinearLayout.LayoutParams(dp(70),
                ViewGroup.LayoutParams.WRAP_CONTENT));
        hRow.addView(humidityView);
        hRow.addView(tv(" %", 13f, MUTED, false));
        c.addView(hRow);

        LinearLayout tRow = hbox();
        TextView tl = tv("温度区间", 13f, MUTED, false);
        tl.setLayoutParams(new LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        tRow.addView(tl);
        tminView = input("5", "最低", android.text.InputType.TYPE_CLASS_NUMBER);
        tminView.setLayoutParams(new LinearLayout.LayoutParams(dp(64),
                ViewGroup.LayoutParams.WRAP_CONTENT));
        tRow.addView(tminView);
        TextView dash = tv(" ~ ", 13f, MUTED, false);
        dash.setPadding(dp(6), 0, dp(6), 0);
        tRow.addView(dash);
        tmaxView = input("35", "最高", android.text.InputType.TYPE_CLASS_NUMBER);
        tmaxView.setLayoutParams(new LinearLayout.LayoutParams(dp(64),
                ViewGroup.LayoutParams.WRAP_CONTENT));
        tRow.addView(tmaxView);
        tRow.addView(tv(" ℃", 13f, MUTED, false));
        c.addView(tRow);

        Button ruleBtn = wideButton("应用自动规则", CARD2);
        LinearLayout.LayoutParams ruleLp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(44));
        ruleLp.topMargin = dp(8);
        c.addView(ruleBtn, ruleLp);

        Button openBtn = button("开阀 30 秒", GREEN);
        Button closeBtn = button("关闭水阀", CARD2);
        c.addView(buttonRow(openBtn, closeBtn));

        Button readValve = wideButton("读取阀门状态", CARD2);
        LinearLayout.LayoutParams rvLp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(44));
        rvLp.topMargin = dp(8);
        c.addView(readValve, rvLp);

        valveView = caption("--");
        valveView.setPadding(0, dp(8), 0, 0);
        c.addView(valveView);
        root.addView(c);

        refresh.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                refreshWeather();
            }
        });

        ruleBtn.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                final DeviceApi call = api;
                final String body = "{\"enabled\":" + (autoSwitch.isChecked() ? "true" : "false")
                        + ",\"temp_min\":" + parseInt(tminView.getText().toString(), 5)
                        + ",\"temp_max\":" + parseInt(tmaxView.getText().toString(), 35)
                        + ",\"humidity_below\":" + parseInt(humidityView.getText().toString(), 40)
                        + ",\"respect_rain\":true}";
                new Thread(new Runnable() {
                    @Override
                    public void run() {
                        try {
                            call.postJson("/api/valve/auto", body);
                            postText(valveView, "自动规则已下发", GREEN);
                        } catch (Exception e) {
                            postText(valveView, "下发失败：" + errMsg(e), RED);
                        }
                    }
                }).start();
            }
        });

        openBtn.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                valveCommand("{\"open\":true,\"duration_s\":30}", "已开阀 30 秒");
            }
        });
        closeBtn.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                valveCommand("{\"open\":false,\"duration_s\":0}", "已关闭水阀");
            }
        });
        readValve.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                final DeviceApi call = api;
                new Thread(new Runnable() {
                    @Override
                    public void run() {
                        try {
                            JSONObject d = new JSONObject(call.get("/api/valve"));
                            String s = "阀门 " + (d.optBoolean("open", false) ? "开启" : "关闭")
                                    + " · 自动 " + (d.optBoolean("auto", false) ? "开" : "关")
                                    + " · 模式 " + d.optString("mode", "-")
                                    + " · 流量 " + d.optDouble("flow", 0)
                                    + "\n原因：" + d.optString("reason", "-");
                            postText(valveView, s, TEXT);
                        } catch (Exception e) {
                            postText(valveView, "读取失败：" + errMsg(e), RED);
                        }
                    }
                }).start();
            }
        });
    }

    private void refreshWeather() {
        final double lat = parseDouble(latView.getText().toString(), 30.28);
        final double lon = parseDouble(lonView.getText().toString(), 120.15);
        weatherView.setText("正在获取天气…");
        weatherView.setTextColor(MUTED);

        new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    String url = String.format(Locale.US,
                            "https://api.open-meteo.com/v1/forecast?latitude=%.4f&longitude=%.4f"
                                    + "&current=temperature_2m,relative_humidity_2m,"
                                    + "precipitation,weather_code&timezone=Asia%%2FShanghai",
                            lat, lon);
                    String body = httpGet(url, 15000);
                    final JSONObject cur = new JSONObject(body).optJSONObject("current");
                    if (cur == null) throw new IOException("天气数据为空");
                    final double temp = cur.optDouble("temperature_2m", 0);
                    final int hum = cur.optInt("relative_humidity_2m", 0);
                    final double rain = cur.optDouble("precipitation", 0);
                    final int code = cur.optInt("weather_code", 0);
                    runOnUiThread(new Runnable() {
                        @Override
                        public void run() {
                            weatherView.setText(String.format(Locale.US,
                                    "气温 %.1f ℃ · 湿度 %d%% · 降水 %.1f mm\n天气：%s",
                                    temp, hum, rain, weatherName(code)));
                            weatherView.setTextColor(TEXT);
                            valveView.setText(advice(temp, hum, rain));
                            valveView.setTextColor(TEXT);
                        }
                    });
                } catch (final Exception e) {
                    runOnUiThread(new Runnable() {
                        @Override
                        public void run() {
                            weatherView.setText("天气获取失败：" + errMsg(e));
                            weatherView.setTextColor(RED);
                        }
                    });
                }
            }
        }).start();
    }

    private String httpGet(String url, int timeoutMs) throws IOException {
        HttpURLConnection c = (HttpURLConnection) new URL(url).openConnection();
        c.setRequestMethod("GET");
        c.setConnectTimeout(8000);
        c.setReadTimeout(timeoutMs);
        c.setUseCaches(false);
        c.setRequestProperty("Accept", "application/json");
        try {
            int code = c.getResponseCode();
            if (code >= 400) throw new IOException("HTTP " + code);
            InputStream is = c.getInputStream();
            try {
                ByteArrayOutputStream bos = new ByteArrayOutputStream();
                byte[] buf = new byte[4096];
                int n;
                while ((n = is.read(buf)) > 0) bos.write(buf, 0, n);
                return new String(bos.toByteArray(), "UTF-8");
            } finally {
                is.close();
            }
        } finally {
            c.disconnect();
        }
    }

    private String advice(double temp, int hum, double rain) {
        if (rain > 0.2) {
            return "正在降水（" + String.format(Locale.US, "%.1f", rain)
                    + " mm），土壤已有水分，建议关闭水阀。";
        }
        if (hum >= 75) {
            return "空气湿度 " + hum + "%，蒸发量小，暂不需要灌溉。";
        }
        if (temp < 5) {
            return "气温 " + String.format(Locale.US, "%.1f", temp)
                    + " ℃ 偏低，建议暂停灌溉，防止冻害。";
        }
        if (hum < 40) {
            return "湿度仅 " + hum + "%，建议开启水阀灌溉 10～15 分钟。";
        }
        return "湿度 " + hum + "%，温湿度适中，可维持当前灌溉计划。";
    }

    private static String weatherName(int code) {
        if (code == 0) return "晴";
        if (code == 1) return "多云";
        if (code == 2) return "局部多云";
        if (code == 3) return "阴";
        if (code == 45 || code == 48) return "雾";
        if (code >= 51 && code <= 57) return "毛毛雨";
        if (code >= 61 && code <= 67) return "雨";
        if (code >= 71 && code <= 77) return "雪";
        if (code >= 80 && code <= 82) return "阵雨";
        if (code == 85 || code == 86) return "阵雪";
        if (code >= 95) return "雷暴";
        return "未知";
    }

    private void valveCommand(final String json, final String okText) {
        final DeviceApi call = api;
        new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    call.postJson("/api/valve", json);
                    postText(valveView, okText, GREEN);
                } catch (Exception e) {
                    postText(valveView, "操作失败：" + errMsg(e), RED);
                }
            }
        }).start();
    }

    // ---------------------------------------------------------------- 实时摄像头

    private void startLive(final VisionSlot slot) {
        stopLive(slot, null);
        String url = slot.camera.getText().toString().trim();
        if (url.length() == 0) {
            toast("请先填写摄像头地址");
            return;
        }
        slot.live = true;
        slot.liveBtn.setText("停止实时");
        slot.result.setText("正在连接摄像头…");
        slot.result.setTextColor(MUTED);

        slot.reader = new Thread(new Runnable() {
            @Override
            public void run() {
                readLoop(slot, url);
            }
        });
        slot.reader.start();

        slot.detector = new Thread(new Runnable() {
            @Override
            public void run() {
                detectLoop(slot);
            }
        });
        slot.detector.start();
    }

    private void stopLive(VisionSlot slot, String message) {
        slot.live = false;
        try {
            if (slot.conn != null) slot.conn.disconnect();
        } catch (Exception ignored) {
        }
        slot.conn = null;
        if (slot.liveBtn != null) slot.liveBtn.setText("开始实时");
        if (message != null && slot.result != null) {
            slot.result.setText(message);
            slot.result.setTextColor(MUTED);
        }
        slot.reader = null;
        slot.detector = null;
    }

    private void readLoop(final VisionSlot slot, String url) {
        try {
            HttpURLConnection probe = connect(url);
            slot.conn = probe;
            String ct = probe.getContentType();
            InputStream is = probe.getInputStream();
            boolean mjpeg = ct == null
                    || !ct.toLowerCase(Locale.US).startsWith("image/");
            if (mjpeg) {
                try {
                    JpegReader reader = new JpegReader(is);
                    byte[] f;
                    while (slot.live && (f = reader.next()) != null) {
                        onFrame(slot, f);
                    }
                } finally {
                    is.close();
                    probe.disconnect();
                }
                return;
            }

            byte[] data = readStream(is);
            is.close();
            probe.disconnect();
            onFrame(slot, data);

            while (slot.live) {
                Thread.sleep(250);
                HttpURLConnection c = connect(url);
                slot.conn = c;
                try {
                    InputStream s = c.getInputStream();
                    try {
                        data = readStream(s);
                    } finally {
                        s.close();
                    }
                    onFrame(slot, data);
                } finally {
                    c.disconnect();
                }
            }
        } catch (final Exception e) {
            if (slot.live) {
                slot.live = false;
                runOnUiThread(new Runnable() {
                    @Override
                    public void run() {
                        slot.liveBtn.setText("开始实时");
                        slot.result.setText("摄像头连接失败：" + errMsg(e));
                        slot.result.setTextColor(RED);
                    }
                });
            }
        }
    }

    private HttpURLConnection connect(String url) throws IOException {
        HttpURLConnection c = (HttpURLConnection) new URL(url).openConnection();
        c.setConnectTimeout(5000);
        c.setReadTimeout(20000);
        c.setUseCaches(false);
        c.setRequestProperty("Connection", "close");
        int code = c.getResponseCode();
        if (code >= 400) throw new IOException("HTTP " + code);
        return c;
    }

    private byte[] readStream(InputStream is) throws IOException {
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        byte[] buf = new byte[8192];
        int n;
        while ((n = is.read(buf)) > 0) bos.write(buf, 0, n);
        return bos.toByteArray();
    }

    private void onFrame(final VisionSlot slot, final byte[] jpeg) {
        if (!slot.live || jpeg == null || jpeg.length < 100) return;
        final Bitmap bmp = BitmapFactory.decodeByteArray(jpeg, 0, jpeg.length);
        if (bmp == null) return;
        slot.frame = jpeg;
        final int w = bmp.getWidth();
        final int h = bmp.getHeight();
        runOnUiThread(new Runnable() {
            @Override
            public void run() {
                if (!slot.live) {
                    bmp.recycle();
                    return;
                }
                slot.view.setImageBitmap(bmp);
                slot.iw = w;
                slot.ih = h;
            }
        });
    }

    private void detectLoop(VisionSlot slot) {
        final DeviceApi call = api;
        while (slot.live) {
            byte[] f = slot.frame;
            if (f != null) {
                try {
                    final String res = call.postFile(
                            "/api/vision/detect?kind=" + slot.kind,
                            "image", "frame.jpg", f, 15000);
                    final JSONObject d = new JSONObject(res);
                    runOnUiThread(new Runnable() {
                        @Override
                        public void run() {
                            if (slot.live) applyVision(slot, d, slot.kind);
                        }
                    });
                } catch (final Exception e) {
                    slot.live = false;
                    try {
                        if (slot.conn != null) slot.conn.disconnect();
                    } catch (Exception ignored) {
                    }
                    runOnUiThread(new Runnable() {
                        @Override
                        public void run() {
                            slot.liveBtn.setText("开始实时");
                            slot.result.setText("识别失败：" + errMsg(e));
                            slot.result.setTextColor(RED);
                        }
                    });
                    break;
                }
            }
            try {
                Thread.sleep(800);
            } catch (InterruptedException ie) {
                break;
            }
        }
    }

    static class JpegReader {
        private final InputStream in;
        private final byte[] buf = new byte[16384];
        private final ByteArrayOutputStream frame = new ByteArrayOutputStream(262144);
        private int pos, len, push = -1;
        private boolean inside;

        JpegReader(InputStream in) {
            this.in = in;
        }

        private int nextByte() throws IOException {
            if (push >= 0) {
                int v = push;
                push = -1;
                return v;
            }
            if (pos >= len) {
                len = in.read(buf);
                pos = 0;
                if (len <= 0) return -1;
            }
            return buf[pos++] & 0xFF;
        }

        byte[] next() throws IOException {
            while (true) {
                int b = nextByte();
                if (b < 0) return null;
                if (!inside) {
                    if (b != 0xFF) continue;
                    int b2 = nextByte();
                    if (b2 < 0) return null;
                    if (b2 == 0xD8) {
                        inside = true;
                        frame.reset();
                        frame.write(0xFF);
                        frame.write(0xD8);
                    } else {
                        push = b2;
                    }
                    continue;
                }
                frame.write(b);
                if (b != 0xFF) continue;
                int b2 = nextByte();
                if (b2 < 0) return null;
                if (b2 == 0xD9) {
                    inside = false;
                    frame.write(0xD9);
                    if (frame.size() > 16 * 1024 * 1024) {
                        frame.reset();
                        continue;
                    }
                    return frame.toByteArray();
                }
                push = b2;
            }
        }
    }

    // ---------------------------------------------------------------- 工具

    private void postText(final TextView view, final String text, final int color) {
        runOnUiThread(new Runnable() {
            @Override
            public void run() {
                view.setText(text);
                view.setTextColor(color);
            }
        });
    }

    private void toast(final String msg) {
        runOnUiThread(new Runnable() {
            @Override
            public void run() {
                Toast.makeText(FeaturesActivity.this, msg, Toast.LENGTH_SHORT).show();
            }
        });
    }

    private String errMsg(Exception e) {
        String m = e.getMessage();
        if (m == null) m = e.getClass().getSimpleName();
        if (m.contains("404")) return "固件不支持该接口（404）";
        if (m.length() > 60) m = m.substring(0, 60);
        return m;
    }

    private static int parseInt(String s, int def) {
        try {
            return Integer.parseInt(s.trim());
        } catch (Exception e) {
            return def;
        }
    }

    private static double parseDouble(String s, double def) {
        try {
            return Double.parseDouble(s.trim());
        } catch (Exception e) {
            return def;
        }
    }
}
