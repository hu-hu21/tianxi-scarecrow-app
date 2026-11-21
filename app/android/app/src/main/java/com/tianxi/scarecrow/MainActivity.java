package com.tianxi.scarecrow;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.DialogInterface;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.res.ColorStateList;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.graphics.drawable.RippleDrawable;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.SeekBar;
import android.widget.Spinner;
import android.widget.ArrayAdapter;
import android.widget.Switch;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONArray;
import org.json.JSONObject;

import java.net.InetAddress;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.atomic.AtomicBoolean;

public class MainActivity extends Activity {

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

    private TextView pill;
    private TextView stateValue, vbatValue, lightValue, quietValue;
    private TextView pulsesValue, uptimeValue, fwValue, modeValue;
    private TextView logView;
    private Switch quietSwitch;

    private ScrollView scroll;
    private LinearLayout controlGroup, statusGroup, settingsGroup, aboutGroup;
    private LinearLayout navBar;
    private final java.util.List<Button> navButtons = new java.util.ArrayList<Button>();
    private EditText serverView;
    private EditText deviceView;
    private Spinner deviceSpinner;
    private TextView deviceHint;
    private final java.util.List<String> deviceLabels = new java.util.ArrayList<String>();
    private final java.util.List<String> deviceRefs = new java.util.ArrayList<String>();
    private boolean fillingDevices = false;
    private String loginUser = "";
    private int currentTab = 0;
    private String serverAddr = "192.168.4.1";
    private String deviceAddr = "";

    private final Map<String, Slider> sliders = new LinkedHashMap<String, Slider>();
    private DeviceApi api;
    private SharedPreferences prefs;

    private final Handler ui = new Handler(Looper.getMainLooper());
    private final AtomicBoolean busy = new AtomicBoolean(false);
    private boolean configLoaded = false;
    private boolean online = false;
    private boolean polling = false;

    private static class Slider {
        final String key;
        final SeekBar bar;
        final TextView value;
        final int min;
        final int step;
        final int scale;

        Slider(String key, SeekBar bar, TextView value, int min, int step, int scale) {
            this.key = key;
            this.bar = bar;
            this.value = value;
            this.min = min;
            this.step = step;
            this.scale = scale;
        }

        int get() {
            return min + bar.getProgress() * step;
        }

        int sent() {
            return get() * scale;
        }

        void set(int v) {
            int p = (v - min) / step;
            if (p < 0) p = 0;
            if (p > bar.getMax()) p = bar.getMax();
            bar.setProgress(p);
            value.setText(String.valueOf(get()));
        }

        void refreshLabel() {
            value.setText(String.valueOf(get()));
        }
    }

    // ---------------- 生命周期 ----------------

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setStatusBarColor(BG);
        getWindow().setNavigationBarColor(BG);

        prefs = getSharedPreferences("scarecrow", MODE_PRIVATE);
        String token = prefs.getString("token", "");
        if (token == null || token.length() == 0) {
            startActivity(new Intent(this, LoginActivity.class));
            finish();
            return;
        }
        DeviceApi.TOKEN = token;
        loginUser = prefs.getString("user", "");
        String savedIp = prefs.getString("server", prefs.getString("ip", "192.168.4.1"));
        serverAddr = savedIp;
        deviceAddr = prefs.getString("device", "");
        api = new DeviceApi(serverAddr, deviceAddr);

        setContentView(buildUi(savedIp));
        startPolling();
        refresh(true);
        loadDevices();
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        if (intent != null) selectTab(intent.getIntExtra("tab", 0));
    }

    @Override
    protected void onResume() {
        super.onResume();
        startPolling();
    }

    @Override
    protected void onPause() {
        super.onPause();
        stopPolling();
    }

    private void startPolling() {
        if (polling) return;
        polling = true;
        ui.postDelayed(pollTask, 1200);
    }

    private void stopPolling() {
        polling = false;
        ui.removeCallbacks(pollTask);
    }

    private final Runnable pollTask = new Runnable() {
        @Override
        public void run() {
            if (!polling) return;
            refresh(false);
            ui.postDelayed(this, 2500);
        }
    };

    // ---------------- UI 构建 ----------------

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
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(
                0, dp(44), 1f);
        p.leftMargin = dp(4);
        p.rightMargin = dp(4);
        b.setLayoutParams(p);
        return b;
    }

    private LinearLayout buttonRow(Button left, Button right) {
        LinearLayout row = hbox();
        row.addView(left);
        row.addView(right);
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        p.topMargin = dp(8);
        row.setLayoutParams(p);
        return row;
    }

    private LinearLayout usageCard(String feature) {
        LinearLayout c = card(feature + "功能使用说明");
        TextView body = tv(UsageText.get(feature), 12f, MUTED, false);
        body.setLineSpacing(dp(3), 1f);
        c.addView(body);
        return c;
    }

    private EditText field(String hint, String value, int type) {
        EditText e = new EditText(this);
        e.setText(value == null ? "" : value);
        e.setTextSize(15f);
        e.setTextColor(TEXT);
        e.setHintTextColor(MUTED);
        e.setHint(hint);
        e.setSingleLine(true);
        e.setInputType(type);
        e.setBackground(shape(INPUT, 8));
        e.setPadding(dp(12), dp(8), dp(12), dp(8));
        return e;
    }

    private LinearLayout buildServerCard(String savedIp) {
        LinearLayout c = card("服务器 / 设备绑定");

        LinearLayout acct = hbox();
        TextView who = tv("账号：" + (loginUser.length() == 0 ? "未登录" : loginUser),
                13f, MUTED, true);
        who.setLayoutParams(new LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        acct.addView(who);
        Button out = button("退出登录", CARD2);
        out.setTextSize(12f);
        out.setLayoutParams(new LinearLayout.LayoutParams(dp(96), dp(34)));
        out.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                LoginActivity.logoutFrom(MainActivity.this);
            }
        });
        acct.addView(out);
        c.addView(acct);

        c.addView(tv("硬件数据经服务器转发，服务器地址与设备地址均可手动填写绑定",
                12f, MUTED, false));

        LinearLayout statusRow = hbox();
        pill = tv("● 未连接", 13f, MUTED, true);
        pill.setLayoutParams(new LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        statusRow.addView(pill);
        Button find = button("查找设备", CARD2);
        find.setLayoutParams(new LinearLayout.LayoutParams(dp(104), dp(38)));
        find.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                findDevice();
            }
        });
        statusRow.addView(find);
        LinearLayout.LayoutParams statusLp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        statusLp.topMargin = dp(10);
        c.addView(statusRow, statusLp);

        TextView serverLabel = tv("服务器地址", 12f, MUTED, false);
        LinearLayout.LayoutParams labelLp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        labelLp.topMargin = dp(10);
        c.addView(serverLabel, labelLp);

        serverView = field("例如 47.94.214.62:1819", savedIp, InputType.TYPE_CLASS_TEXT);
        c.addView(serverView, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        TextView deviceLabel = tv("设备地址（服务器所在局域网内，可留空）", 12f, MUTED, false);
        LinearLayout.LayoutParams label2Lp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        label2Lp.topMargin = dp(8);
        c.addView(deviceLabel, label2Lp);

        deviceView = field("例如 192.168.1.66:8080", deviceAddr, InputType.TYPE_CLASS_TEXT);
        c.addView(deviceView, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        Button bind = button("保存并绑定", ACCENT);
        bind.setLayoutParams(new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(44)));
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(44));
        lp.topMargin = dp(10);
        c.addView(bind, lp);

        bind.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                String addr = serverView.getText().toString().trim();
                if (addr.length() == 0) addr = "192.168.4.1";
                String dev = deviceView.getText().toString().trim();
                serverAddr = addr;
                deviceAddr = dev;
                serverView.setText(addr);
                deviceView.setText(dev);
                prefs.edit()
                        .putString("server", addr)
                        .putString("device", dev)
                        .putString("ip", addr)
                        .apply();
                api = new DeviceApi(addr, dev);
                configLoaded = false;
                log(dev.length() == 0
                        ? "已绑定服务器 " + addr + "（自动选择设备）"
                        : "已绑定服务器 " + addr + " / 设备 " + dev);
                refresh(true);
            }
        });

        TextView deviceTitle = tv("我的设备（来自服务端）", 12f, MUTED, false);
        LinearLayout.LayoutParams deviceTitleLp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        deviceTitleLp.topMargin = dp(14);
        deviceTitle.setLayoutParams(deviceTitleLp);
        c.addView(deviceTitle);

        LinearLayout deviceRow = hbox();
        deviceSpinner = new Spinner(this);
        deviceSpinner.setBackground(shape(INPUT, 8));
        final ArrayAdapter<String> adapter = new ArrayAdapter<String>(this,
                android.R.layout.simple_spinner_dropdown_item, deviceLabels);
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        deviceSpinner.setAdapter(adapter);
        deviceSpinner.setLayoutParams(new LinearLayout.LayoutParams(0, dp(42), 1f));
        deviceSpinner.setOnItemSelectedListener(new android.widget.AdapterView.OnItemSelectedListener() {
            @Override
            public void onItemSelected(android.widget.AdapterView<?> parent, View view,
                                       int position, long id) {
                if (fillingDevices || position < 0 || position >= deviceRefs.size()) return;
                String ref = deviceRefs.get(position);
                if (ref.length() == 0 || ref.equals(deviceAddr)) return;
                deviceAddr = ref;
                if (deviceView != null) deviceView.setText(ref);
                prefs.edit().putString("device", ref).apply();
                api = new DeviceApi(serverAddr, deviceAddr);
                configLoaded = false;
                if (deviceHint != null) {
                    deviceHint.setText("当前设备：" + deviceLabels.get(position));
                }
                log("切换设备 → " + deviceLabels.get(position));
                refresh(true);
            }

            @Override
            public void onNothingSelected(android.widget.AdapterView<?> parent) {
            }
        });
        deviceRow.addView(deviceSpinner);
        Button refreshDevices = button("刷新", CARD2);
        refreshDevices.setTextSize(12f);
        refreshDevices.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                loadDevices();
            }
        });
        LinearLayout.LayoutParams rdLp = new LinearLayout.LayoutParams(dp(72), dp(36));
        rdLp.leftMargin = dp(8);
        deviceRow.addView(refreshDevices, rdLp);
        LinearLayout.LayoutParams deviceRowLp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        deviceRowLp.topMargin = dp(6);
        c.addView(deviceRow, deviceRowLp);

        deviceHint = tv("登录后自动读取当前账号名下的设备。", 11.5f, MUTED, false);
        LinearLayout.LayoutParams hintLp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        hintLp.topMargin = dp(6);
        deviceHint.setLayoutParams(hintLp);
        c.addView(deviceHint);

        Button addDevice = button("添加我的硬件", ACCENT);
        addDevice.setTextSize(13f);
        LinearLayout.LayoutParams addLp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(42));
        addLp.topMargin = dp(8);
        addDevice.setLayoutParams(addLp);
        addDevice.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                addMyDeviceDialog();
            }
        });
        c.addView(addDevice);

        return c;
    }

    /** 异步读取当前账号名下的设备列表。 */
    private void loadDevices() {
        if (deviceHint != null) deviceHint.setText("正在读取我的设备…");
        final DeviceApi call = new DeviceApi(serverAddr, "");
        new Thread(new Runnable() {
            @Override
            public void run() {
                String error = null;
                final java.util.List<String> labels = new java.util.ArrayList<String>();
                final java.util.List<String> refs = new java.util.ArrayList<String>();
                try {
                    JSONObject result = new JSONObject(call.get("/account/devices"));
                    JSONArray arr = result.optJSONArray("devices");
                    if (arr != null) {
                        for (int i = 0; i < arr.length(); i++) {
                            JSONObject d = arr.getJSONObject(i);
                            String name = d.optString("name", "");
                            String ref = d.optString("ref", "");
                            boolean custom = d.optBoolean("custom", false);
                            labels.add(name + (custom ? "  [客户硬件]" : ""));
                            refs.add(ref);
                        }
                    }
                } catch (Exception e) {
                    error = e.getMessage();
                }

                final String fError = error;
                ui.post(new Runnable() {
                    @Override
                    public void run() {
                        if (deviceSpinner == null) return;
                        fillingDevices = true;
                        deviceLabels.clear();
                        deviceRefs.clear();
                        deviceLabels.addAll(labels);
                        deviceRefs.addAll(refs);
                        if (deviceSpinner.getAdapter() instanceof ArrayAdapter) {
                            ((ArrayAdapter<?>) deviceSpinner.getAdapter()).notifyDataSetChanged();
                        }
                        int index = 0;
                        for (int i = 0; i < refs.size(); i++) {
                            if (refs.get(i).equals(deviceAddr)) {
                                index = i;
                                break;
                            }
                        }
                        if (!refs.isEmpty()) {
                            deviceSpinner.setSelection(index);
                            if (deviceHint != null) {
                                deviceHint.setText("共 " + refs.size() + " 台设备，选择后立即切换。");
                            }
                            if (deviceAddr.length() == 0) {
                                deviceAddr = refs.get(index);
                                if (deviceView != null) deviceView.setText(deviceAddr);
                                prefs.edit().putString("device", deviceAddr).apply();
                                api = new DeviceApi(serverAddr, deviceAddr);
                            }
                        } else if (deviceHint != null) {
                            deviceHint.setText(fError == null
                                    ? "当前账号还没有设备，点击【添加我的硬件】。"
                                    : "读取设备失败：" + fError);
                        }
                        fillingDevices = false;
                    }
                });
            }
        }).start();
    }

    /** 添加自己的硬件：标准设备填地址；客户自定义硬件可只填名称，密钥由服务端生成。 */
    private void addMyDeviceDialog() {
        LinearLayout box = vbox();
        box.setPadding(dp(20), dp(8), dp(20), dp(4));

        box.addView(tv("设备名称", 12f, MUTED, false));
        final EditText name = field("例如 一号田东侧", "", InputType.TYPE_CLASS_TEXT);
        box.addView(name);

        box.addView(tv("设备地址（标准硬件填写，例如 192.168.1.66:80）", 12f, MUTED, false));
        final EditText address = field("可留空（客户自定义硬件）", "", InputType.TYPE_CLASS_TEXT);
        box.addView(address);

        box.addView(tv("设备密钥（客户自定义硬件填写，留空自动生成）", 12f, MUTED, false));
        final EditText key = field("可留空", "", InputType.TYPE_CLASS_TEXT);
        box.addView(key);

        final CheckBox custom = new CheckBox(this);
        custom.setText("客户自定义硬件：数据由硬件主动上报到服务端");
        custom.setTextSize(12.5f);
        custom.setTextColor(TEXT);
        custom.setPadding(0, dp(6), 0, 0);
        box.addView(custom);

        new AlertDialog.Builder(this)
                .setTitle("添加我的硬件")
                .setView(box)
                .setNegativeButton("取消", null)
                .setPositiveButton("添加", new DialogInterface.OnClickListener() {
                    @Override
                    public void onClick(DialogInterface dialog, int which) {
                        submitDevice(name, address, key, custom);
                    }
                })
                .show();
    }

    private void submitDevice(final EditText name, final EditText address,
                              final EditText key, final CheckBox custom) {
        final String n = name.getText().toString().trim();
        final String a = address.getText().toString().trim();
        final String k = key.getText().toString().trim();
        final boolean isCustom = custom.isChecked() || a.length() == 0;
        final DeviceApi call = new DeviceApi(serverAddr, "");
        new Thread(new Runnable() {
            @Override
            public void run() {
                String error = null;
                String shownKey = k;
                String shownName = n.length() == 0 ? (a.length() == 0 ? "我的硬件" : a) : n;
                try {
                    JSONObject body = new JSONObject();
                    body.put("name", shownName);
                    body.put("address", a);
                    body.put("key", k);
                    body.put("custom", isCustom ? "1" : "0");
                    JSONObject result = new JSONObject(call.postJson("/account/devices", body.toString()));
                    if (result.optInt("code", 1) != 0) {
                        error = result.optString("msg", "添加失败");
                    } else {
                        JSONObject d = result.optJSONObject("device");
                        if (d != null) shownKey = d.optString("key", k);
                    }
                } catch (Exception e) {
                    error = e.getMessage();
                }
                final String fError = error;
                final String fKey = shownKey;
                final String fName = shownName;
                ui.post(new Runnable() {
                    @Override
                    public void run() {
                        if (fError != null) {
                            Toast.makeText(MainActivity.this,
                                    "添加失败：" + fError, Toast.LENGTH_LONG).show();
                            return;
                        }
                        Toast.makeText(MainActivity.this,
                                isCustom ? "已添加 " + fName + "，设备密钥：" + fKey
                                        : "已添加 " + fName, Toast.LENGTH_LONG).show();
                        log("添加我的硬件 " + fName);
                        loadDevices();
                    }
                });
            }
        }).start();
    }

    private LinearLayout buildBottomNav() {
        navBar = hbox();
        navBar.setBackgroundColor(CARD);
        navBar.setPadding(dp(4), dp(6), dp(4), dp(6));

        String[] names = { "设备控制", "设备状态", "硬件设置", "扩展功能", "设置" };
        for (int i = 0; i < names.length; i++) {
            Button b = button(names[i], i == 0 ? ACCENT : CARD2);
            b.setTextSize(10.5f);
            b.setLayoutParams(new LinearLayout.LayoutParams(0, dp(46), 1f));
            final int idx = i;
            b.setOnClickListener(new View.OnClickListener() {
                @Override
                public void onClick(View v) {
                    if (idx == 3) openFeatures();
                    else selectTab(idx);
                }
            });
            navBar.addView(b);
            navButtons.add(b);
        }
        return navBar;
    }

    private void openFeatures() {
        Intent it = new Intent(MainActivity.this, FeaturesActivity.class);
        it.putExtra("ip", api.base.replace("http://", "").replace("https://", ""));
        it.putExtra("device", deviceAddr);
        startActivity(it);
    }

    private void selectTab(int tab) {
        currentTab = tab;
        if (controlGroup == null) return;
        controlGroup.setVisibility(tab == 0 ? View.VISIBLE : View.GONE);
        statusGroup.setVisibility(tab == 1 ? View.VISIBLE : View.GONE);
        settingsGroup.setVisibility(tab == 2 ? View.VISIBLE : View.GONE);
        aboutGroup.setVisibility(tab == 4 ? View.VISIBLE : View.GONE);
        for (int i = 0; i < navButtons.size(); i++) {
            navButtons.get(i).setBackground(shape(i == tab ? ACCENT : CARD2, 10));
        }
        if (scroll != null) scroll.scrollTo(0, 0);
    }

    private View buildUi(String savedIp) {
        LinearLayout outer = vbox();
        outer.setBackgroundColor(BG);

        scroll = new ScrollView(this);
        scroll.setBackgroundColor(BG);
        scroll.setFillViewport(true);
        outer.addView(scroll, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));

        LinearLayout root = vbox();
        root.setPadding(dp(16), dp(14), dp(16), dp(24));
        scroll.addView(root);

        TextView title = tv("稻草人驱鸟", 26f, TEXT, true);
        root.addView(title);
        TextView sub = tv("Android 控制台  ·  v3.21.5  ·  经服务器转发", 12f, MUTED, false);
        sub.setPadding(0, dp(4), 0, 0);
        root.addView(sub);

        controlGroup = vbox();
        statusGroup = vbox();
        statusGroup.setVisibility(View.GONE);
        settingsGroup = vbox();
        settingsGroup.setVisibility(View.GONE);
        aboutGroup = vbox();
        aboutGroup.setVisibility(View.GONE);
        root.addView(controlGroup);
        root.addView(statusGroup);
        root.addView(settingsGroup);
        root.addView(aboutGroup);

        // 快捷操作
        LinearLayout actions = card("快捷操作");
        Button testAll = button("立即试驱", ACCENT);
        Button testSound = button("声音测试", CARD2);
        actions.addView(buttonRow(testAll, testSound));

        Button testLight = button("灯光测试", CARD2);
        Button testServo = button("云台测试", CARD2);
        actions.addView(buttonRow(testLight, testServo));

        Button stop = button("停止输出", RED);
        Button web = button("网页控制台", CARD2);
        actions.addView(buttonRow(stop, web));
        controlGroup.addView(actions);

        // 设备状态
        LinearLayout status = card("设备状态");
        stateValue = addStatusRow(status, "运行状态");
        vbatValue = addStatusRow(status, "电池电压");
        lightValue = addStatusRow(status, "光照环境");
        quietValue = addStatusRow(status, "静音时段");
        pulsesValue = addStatusRow(status, "雷达脉冲");
        uptimeValue = addStatusRow(status, "在线时长");
        fwValue = addStatusRow(status, "固件版本");
        modeValue = addStatusRow(status, "网络模式");
        statusGroup.addView(status);
        statusGroup.addView(usageCard("设备状态"));

        // 服务器连接（硬件数据经服务器转发）
        settingsGroup.addView(buildServerCard(savedIp));

        // 参数配置
        LinearLayout config = card("参数配置");

        addSection(config, "声音与识别");
        addSlider(config, "volDay", "白天音量", 0, 30, 1, 1, 26);
        addSlider(config, "volNight", "夜间音量", 0, 30, 1, 1, 16);
        addSlider(config, "sens", "雷达灵敏度", 1, 8, 1, 1, 3);
        addSlider(config, "tracks", "音轨数量", 1, 30, 1, 1, 8);

        addSection(config, "驱赶节奏");
        addSlider(config, "cool", "冷却时间(秒)", 5, 600, 5, 1, 60);
        addSlider(config, "activeMin", "最短驱赶(秒)", 2, 120, 1, 1000, 8);
        addSlider(config, "activeMax", "最长驱赶(秒)", 2, 120, 1, 1000, 18);
        addSlider(config, "trigger", "触发窗口(ms)", 500, 10000, 100, 1, 2500);

        addSection(config, "静音与光感");
        addSlider(config, "qStart", "静音开始(时)", 0, 23, 1, 1, 22);
        addSlider(config, "qEnd", "静音结束(时)", 0, 23, 1, 1, 6);
        addSlider(config, "ldr", "夜间阈值", 0, 4000, 50, 1, 800);

        LinearLayout quietRow = hbox();
        TextView quietLabel = tv("启用静音时段", 13f, MUTED, false);
        quietLabel.setLayoutParams(new LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        quietRow.addView(quietLabel);
        quietSwitch = new Switch(this);
        quietSwitch.setThumbTintList(ColorStateList.valueOf(ACCENT));
        quietSwitch.setTrackTintList(ColorStateList.valueOf(LINE));
        quietRow.addView(quietSwitch);
        LinearLayout.LayoutParams qLp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        qLp.topMargin = dp(6);
        config.addView(quietRow, qLp);

        Button save = button("保存配置", ACCENT);
        save.setLayoutParams(new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(46)));
        LinearLayout.LayoutParams saveLp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(46));
        saveLp.topMargin = dp(14);
        config.addView(save, saveLp);

        LinearLayout extra = hbox();
        Button read = smallButton("读取配置");
        Button reset = smallButton("恢复默认");
        Button reboot = smallButton("重启设备");
        extra.addView(read);
        extra.addView(reset);
        extra.addView(reboot);
        LinearLayout.LayoutParams exLp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        exLp.topMargin = dp(8);
        config.addView(extra, exLp);
        settingsGroup.addView(config);
        settingsGroup.addView(usageCard("硬件设置"));

        // 设备控制使用说明
        controlGroup.addView(usageCard("设备控制"));

        // 设置：运行日志
        LinearLayout logCard = card("运行日志");
        logView = tv("", 11f, MUTED, false);
        logView.setTypeface(Typeface.MONOSPACE);
        logView.setLineSpacing(dp(2), 1f);
        logCard.addView(logView);
        aboutGroup.addView(logCard);

        // 开发警示
        LinearLayout about = card("开发警示");
        TextView version = tv("版本 3.21.5", 13f, ACCENT, true);
        about.addView(version);
        TextView copyright = tv("Copyright (C) 2026 【胡宇宸/tj248511fg51/y9000p】",
                12f, TEXT, true);
        LinearLayout.LayoutParams cpLp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        cpLp.topMargin = dp(6);
        about.addView(copyright, cpLp);

        TextView terms = tv(
                "本程序为独立原创作品，版权归作者所有。\n"
                        + "严禁未经许可反编译、逆向工程、破解、修改源码、非法复制及传播。\n"
                        + "对于本软件相关规则、使用说明，最终解释权归作者本人。",
                11.5f, MUTED, false);
        terms.setLineSpacing(dp(3), 1f);
        LinearLayout.LayoutParams termsLp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        termsLp.topMargin = dp(6);
        about.addView(terms, termsLp);
        aboutGroup.addView(about);
        aboutGroup.addView(usageCard("设置"));

        // 事件
        testAll.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                testAction("all", "立即试驱");
            }
        });
        testSound.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                testAction("sound", "声音测试");
            }
        });
        testLight.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                testAction("light", "灯光测试");
            }
        });
        testServo.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                testAction("servo", "云台测试");
            }
        });
        stop.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                testAction("stop", "停止输出");
            }
        });
        web.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                try {
                    startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(api.base + "/")));
                } catch (Exception e) {
                    log("打开浏览器失败");
                }
            }
        });
        save.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                saveConfig();
            }
        });
        read.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                loadConfig(true);
            }
        });
        reset.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                confirm("恢复设备默认值？", new Runnable() {
                    @Override
                    public void run() {
                        postAsync("/api/reset", "", "已恢复默认", true);
                    }
                });
            }
        });
        reboot.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                confirm("重启设备？约 5 秒后重新连接。", new Runnable() {
                    @Override
                    public void run() {
                        postAsync("/api/reboot", "", "设备正在重启", true);
                    }
                });
            }
        });

        outer.addView(buildBottomNav(), new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        selectTab(getIntent().getIntExtra("tab", 0));
        return outer;
    }

    private Button smallButton(String text) {
        Button b = button(text, CARD2);
        b.setTextSize(12f);
        b.setLayoutParams(new LinearLayout.LayoutParams(0, dp(38), 1f));
        return b;
    }

    private void addSection(LinearLayout parent, String title) {
        TextView t = tv(title, 11f, ACCENT, true);
        t.setPadding(0, dp(12), 0, dp(2));
        parent.addView(t);
    }

    private TextView addStatusRow(LinearLayout parent, String label) {
        LinearLayout row = hbox();
        TextView l = tv(label, 13f, MUTED, false);
        l.setLayoutParams(new LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        row.addView(l);

        TextView v = tv("--", 14f, TEXT, true);
        v.setGravity(Gravity.END);
        row.addView(v);

        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        p.topMargin = dp(7);
        parent.addView(row, p);
        return v;
    }

    private void addSlider(LinearLayout parent, String key, String label,
                           int min, int max, int step, int scale, int initial) {
        LinearLayout row = hbox();

        TextView name = tv(label, 12.5f, MUTED, false);
        name.setLayoutParams(new LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        row.addView(name);

        SeekBar bar = new SeekBar(this);
        bar.setMax((max - min) / step);
        bar.setProgressTintList(ColorStateList.valueOf(ACCENT));
        bar.setThumbTintList(ColorStateList.valueOf(ACCENT));
        bar.setProgressBackgroundTintList(ColorStateList.valueOf(LINE));
        row.addView(bar, new LinearLayout.LayoutParams(dp(112), dp(34)));

        TextView value = tv("", 12.5f, TEXT, true);
        value.setGravity(Gravity.END);
        row.addView(value, new LinearLayout.LayoutParams(dp(46),
                ViewGroup.LayoutParams.WRAP_CONTENT));

        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        p.topMargin = dp(2);
        parent.addView(row, p);

        final Slider s = new Slider(key, bar, value, min, step, scale);
        sliders.put(key, s);
        s.set(initial);

        bar.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener() {
            @Override
            public void onProgressChanged(SeekBar seekBar, int progress, boolean fromUser) {
                s.refreshLabel();
            }

            @Override
            public void onStartTrackingTouch(SeekBar seekBar) {
            }

            @Override
            public void onStopTrackingTouch(SeekBar seekBar) {
            }
        });
    }

    // ---------------- 网络 ----------------

    private void log(String msg) {
        String time = new SimpleDateFormat("HH:mm:ss", Locale.US).format(new Date());
        String line = time + "  " + msg + "\n";
        String old = logView.getText().toString();
        String merged = old + line;
        String[] lines = merged.split("\n");
        if (lines.length > 6) {
            StringBuilder sb = new StringBuilder();
            for (int i = lines.length - 5; i < lines.length; i++) {
                sb.append(lines[i]).append('\n');
            }
            merged = sb.toString();
        }
        logView.setText(merged);
    }

    private void setOnline(boolean ok, String msg) {
        boolean changed = online != ok;
        online = ok;
        if (ok) {
            pill.setText("● 已连接  " + api.base.replace("http://", ""));
            pill.setTextColor(GREEN);
        } else {
            pill.setText("● 未连接" + (msg == null || msg.length() == 0 ? "" : "  " + msg));
            pill.setTextColor(RED);
        }
        if (changed) {
            log(ok ? "已连接设备" : "连接中断" + (msg == null ? "" : "：" + msg));
        }
    }

    private void refresh(final boolean forceConfig) {
        if (busy.getAndSet(true)) return;
        final DeviceApi call = api;
        new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    final JSONObject status = new JSONObject(call.get("/api/status"));
                    runOnUiThread(new Runnable() {
                        @Override
                        public void run() {
                            applyStatus(status);
                            setOnline(true, null);
                        }
                    });
                    if (forceConfig || !configLoaded) {
                        final JSONObject cfg = new JSONObject(call.get("/api/config"));
                        runOnUiThread(new Runnable() {
                            @Override
                            public void run() {
                                applyConfig(cfg);
                                configLoaded = true;
                            }
                        });
                    }
                    busy.set(false);
                } catch (final Exception e) {
                    busy.set(false);
                    runOnUiThread(new Runnable() {
                        @Override
                        public void run() {
                            String m = e.getMessage();
                            if (m != null && m.contains("401")) {
                                LoginActivity.logoutFrom(MainActivity.this);
                                return;
                            }
                            setOnline(false, shortMsg(e));
                        }
                    });
                }
            }
        }).start();
    }

    private String shortMsg(Exception e) {
        String m = e.getMessage();
        if (m == null) m = e.getClass().getSimpleName();
        if (m.length() > 34) m = m.substring(0, 34);
        return m;
    }

    private void applyStatus(JSONObject d) {
        String state = d.optString("state", "--");
        int test = d.optInt("test", 0);
        String show;
        int color = TEXT;
        if (test == 1) {
            show = "声音测试中";
            color = AMBER;
        } else if (test == 2) {
            show = "灯光测试中";
            color = AMBER;
        } else if (test == 3) {
            show = "云台测试中";
            color = AMBER;
        } else if ("ACTIVE".equals(state)) {
            show = "驱赶中";
            color = AMBER;
        } else if ("COOLDOWN".equals(state)) {
            show = "冷却中";
        } else {
            show = "待机";
        }
        stateValue.setText(show);
        stateValue.setTextColor(color);

        double vbat = d.optDouble("vbat", 0);
        vbatValue.setText(String.format(Locale.US, "%.2f V", vbat));
        vbatValue.setTextColor(vbat > 0.5 && vbat < 11.0 ? RED : GREEN);

        lightValue.setText(d.optInt("night", 0) == 1 ? "夜间" : "白天");
        boolean quiet = d.optInt("quiet", 0) == 1;
        quietValue.setText(quiet ? "生效中" : "未生效");
        quietValue.setTextColor(quiet ? AMBER : TEXT);

        pulsesValue.setText(String.valueOf(d.optLong("pulses", 0)));
        uptimeValue.setText(uptime(d.optLong("uptime", 0)));
        fwValue.setText("v" + d.optString("fw", "--"));
        String mode = d.optString("mode", "--");
        int rssi = d.optInt("rssi", 0);
        modeValue.setText(rssi != 0 ? mode + "  " + rssi + " dBm" : mode);
    }

    private String uptime(long sec) {
        long h = sec / 3600;
        long m = (sec % 3600) / 60;
        return h > 0 ? h + " 小时 " + m + " 分" : m + " 分钟";
    }

    private void applyConfig(JSONObject d) {
        setSlider("volDay", d.optInt("volDay", 26));
        setSlider("volNight", d.optInt("volNight", 16));
        setSlider("sens", d.optInt("sens", 3));
        setSlider("tracks", d.optInt("tracks", 8));
        setSlider("cool", d.optInt("cool", 60));
        setSlider("activeMin", d.optInt("activeMin", 8000) / 1000);
        setSlider("activeMax", d.optInt("activeMax", 18000) / 1000);
        setSlider("trigger", d.optInt("trigger", 2500));
        setSlider("qStart", d.optInt("qStart", 22));
        setSlider("qEnd", d.optInt("qEnd", 6));
        setSlider("ldr", d.optInt("ldr", 800));
        quietSwitch.setChecked(d.optInt("qEnable", 0) == 1);
    }

    private void setSlider(String key, int value) {
        Slider s = sliders.get(key);
        if (s != null) s.set(value);
    }

    private void loadConfig(final boolean logIt) {
        final DeviceApi call = api;
        new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    final JSONObject cfg = new JSONObject(call.get("/api/config"));
                    runOnUiThread(new Runnable() {
                        @Override
                        public void run() {
                            applyConfig(cfg);
                            configLoaded = true;
                            if (logIt) log("已读取设备配置");
                        }
                    });
                } catch (final Exception e) {
                    runOnUiThread(new Runnable() {
                        @Override
                        public void run() {
                            if (logIt) log("读取失败：" + shortMsg(e));
                        }
                    });
                }
            }
        }).start();
    }

    private void saveConfig() {
        StringBuilder b = new StringBuilder();
        for (Slider s : sliders.values()) {
            if (b.length() > 0) b.append('&');
            b.append(s.key).append('=').append(s.sent());
        }
        b.append("&qEnable=").append(quietSwitch.isChecked() ? 1 : 0);
        postAsync("/api/config", b.toString(), "配置已保存", false);
    }

    private void testAction(String what, String name) {
        postAsync("/api/test?what=" + what, "", name, false);
    }

    private void postAsync(final String path, final String body,
                           final String okText, final boolean reloadConfig) {
        final DeviceApi call = api;
        new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    final String res = call.post(path, body);
                    runOnUiThread(new Runnable() {
                        @Override
                        public void run() {
                            log(okText);
                            try {
                                applyStatus(new JSONObject(res));
                            } catch (Exception ignored) {
                            }
                            if (reloadConfig) loadConfig(false);
                        }
                    });
                } catch (final Exception e) {
                    runOnUiThread(new Runnable() {
                        @Override
                        public void run() {
                            log(okText + "失败：" + shortMsg(e));
                            Toast.makeText(MainActivity.this,
                                    "操作失败：" + shortMsg(e), Toast.LENGTH_SHORT).show();
                        }
                    });
                }
            }
        }).start();
    }

    private void findDevice() {
        log("正在查找设备…");
        final String ip = api.base.replace("http://", "");
        new Thread(new Runnable() {
            @Override
            public void run() {
                String found = null;
                try {
                    InetAddress[] addrs = InetAddress.getAllByName("scarecrow.local");
                    if (addrs.length > 0) found = addrs[0].getHostAddress();
                } catch (Exception ignored) {
                }
                if (found == null) {
                    try {
                        new DeviceApi("192.168.4.1", deviceAddr).get("/api/status");
                        found = "192.168.4.1";
                    } catch (Exception ignored) {
                    }
                }
                final String result = found;
                runOnUiThread(new Runnable() {
                    @Override
                    public void run() {
                        if (result == null) {
                            log("未发现设备，请先连接 Scarecrow-XXXX 热点");
                            Toast.makeText(MainActivity.this,
                                    "未发现设备，请先连接设备热点", Toast.LENGTH_LONG).show();
                            return;
                        }
                        serverView.setText(result);
                        serverAddr = result;
                        prefs.edit().putString("server", result)
                                .putString("ip", result).apply();
                        api = new DeviceApi(result, deviceAddr);
                        configLoaded = false;
                        log("已发现 " + result);
                        refresh(true);
                    }
                });
            }
        }).start();
    }

    private void confirm(String title, final Runnable action) {
        new AlertDialog.Builder(this)
                .setTitle(title)
                .setNegativeButton("取消", null)
                .setPositiveButton("确定", new DialogInterface.OnClickListener() {
                    @Override
                    public void onClick(DialogInterface dialog, int which) {
                        action.run();
                    }
                })
                .show();
    }
}
