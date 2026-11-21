package com.tianxi.scarecrow;

import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import org.json.JSONObject;

/** 登录 / 注册页：账号由统一服务端 accounts.cfg 管理。 */
public class LoginActivity extends Activity {

    private static final int BG = 0xFF0B1220;
    private static final int CARD = 0xFF16233A;
    private static final int CARD2 = 0xFF223753;
    private static final int INPUT = 0xFF0F1B2E;
    private static final int TEXT = 0xFFE5EDF7;
    private static final int MUTED = 0xFF93A4BC;
    private static final int ACCENT = 0xFF0EA5E9;
    private static final int RED = 0xFFDC2626;

    private EditText serverView;
    private EditText userView;
    private EditText passView;
    private EditText confirmView;
    private EditText displayView;
    private TextView confirmLabel;
    private TextView displayLabel;
    private TextView tip;
    private TextView status;
    private Button submit;
    private Button switchBtn;

    private SharedPreferences prefs;
    private final Handler ui = new Handler(Looper.getMainLooper());
    private boolean registerMode = false;
    private boolean working = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setStatusBarColor(BG);
        getWindow().setNavigationBarColor(BG);

        prefs = getSharedPreferences("scarecrow", MODE_PRIVATE);
        setContentView(buildUi());
        loadSaved();
    }

    private int dp(float v) {
        return (int) (v * getResources().getDisplayMetrics().density + 0.5f);
    }

    private GradientDrawable shape(int color, float radius) {
        GradientDrawable g = new GradientDrawable();
        g.setColor(color);
        g.setCornerRadius(dp(radius));
        return g;
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

    private EditText field(String hint, int type) {
        EditText e = new EditText(this);
        e.setHint(hint);
        e.setTextSize(15f);
        e.setTextColor(TEXT);
        e.setHintTextColor(MUTED);
        e.setSingleLine(true);
        e.setInputType(type);
        e.setBackground(shape(INPUT, 8));
        e.setPadding(dp(12), dp(9), dp(12), dp(9));
        return e;
    }

    private Button button(String text, int color) {
        Button b = new Button(this);
        b.setText(text);
        b.setTextSize(15f);
        b.setTextColor(Color.WHITE);
        b.setAllCaps(false);
        b.setTypeface(Typeface.DEFAULT_BOLD);
        b.setPadding(0, 0, 0, 0);
        b.setMinHeight(0);
        b.setMinimumHeight(0);
        b.setStateListAnimator(null);
        b.setBackground(shape(color, 10));
        return b;
    }

    private TextView label(String text) {
        TextView t = tv(text, 12f, MUTED, false);
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        p.topMargin = dp(12);
        t.setLayoutParams(p);
        return t;
    }

    private View buildUi() {
        ScrollView scroll = new ScrollView(this);
        scroll.setBackgroundColor(BG);
        scroll.setFillViewport(true);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(24), dp(36), dp(24), dp(28));
        scroll.addView(root);

        root.addView(tv("稻草人驱鸟控制器", 26f, TEXT, true));
        TextView sub = tv("登录后经统一服务端访问你的硬件  ·  v3.21.5", 12.5f, MUTED, false);
        LinearLayout.LayoutParams subLp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        subLp.topMargin = dp(6);
        sub.setLayoutParams(subLp);
        root.addView(sub);
        TextView dev = tv("开发者 胡宇宸  ·  2026-11-21", 11.5f, MUTED, false);
        LinearLayout.LayoutParams devLp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        devLp.topMargin = dp(4);
        dev.setLayoutParams(devLp);
        root.addView(dev);

        root.addView(label("服务器地址"));
        serverView = field("例如 192.168.1.20:1819", InputType.TYPE_CLASS_TEXT);
        root.addView(serverView);

        root.addView(label("用户名"));
        userView = field("至少 3 位", InputType.TYPE_CLASS_TEXT);
        root.addView(userView);

        root.addView(label("密码"));
        passView = field("至少 6 位", InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
        root.addView(passView);

        confirmLabel = label("确认密码");
        root.addView(confirmLabel);
        confirmView = field("再次输入密码", InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
        root.addView(confirmView);

        displayLabel = label("显示名称（可选）");
        root.addView(displayLabel);
        displayView = field("例如 一号田", InputType.TYPE_CLASS_TEXT);
        root.addView(displayView);

        tip = tv("首次使用请点击【立即注册】创建账号。\r\n登录后可在【硬件设置】添加自己的硬件，数据统一经服务端转发。",
                12f, MUTED, false);
        tip.setLineSpacing(dp(3), 1f);
        LinearLayout.LayoutParams tipLp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        tipLp.topMargin = dp(14);
        tip.setLayoutParams(tipLp);
        root.addView(tip);

        submit = button("登 录", ACCENT);
        LinearLayout.LayoutParams submitLp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(48));
        submitLp.topMargin = dp(22);
        submit.setLayoutParams(submitLp);
        submit.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                submit();
            }
        });
        root.addView(submit);

        switchBtn = button("没有账号？立即注册", CARD2);
        LinearLayout.LayoutParams switchLp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(44));
        switchLp.topMargin = dp(12);
        switchBtn.setLayoutParams(switchLp);
        switchBtn.setTextSize(13f);
        switchBtn.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                setMode(!registerMode);
            }
        });
        root.addView(switchBtn);

        status = tv("", 12.5f, RED, false);
        status.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams statusLp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        statusLp.topMargin = dp(12);
        status.setLayoutParams(statusLp);
        root.addView(status);

        setMode(false);
        return scroll;
    }

    private void loadSaved() {
        String server = prefs.getString("server", "192.168.4.1");
        String user = prefs.getString("user", "");
        serverView.setText(server);
        userView.setText(user);
    }

    private void setMode(boolean register) {
        registerMode = register;
        confirmLabel.setVisibility(register ? View.VISIBLE : View.GONE);
        confirmView.setVisibility(register ? View.VISIBLE : View.GONE);
        displayLabel.setVisibility(register ? View.VISIBLE : View.GONE);
        displayView.setVisibility(register ? View.VISIBLE : View.GONE);
        tip.setVisibility(register ? View.GONE : View.VISIBLE);
        submit.setText(register ? "注 册" : "登 录");
        switchBtn.setText(register ? "已有账号？返回登录" : "没有账号？立即注册");
        status.setText("");
    }

    private void showStatus(String text) {
        status.setText(text);
    }

    private void setWorking(boolean value) {
        working = value;
        submit.setEnabled(!value);
        switchBtn.setEnabled(!value);
    }

    private void submit() {
        if (working) return;
        final String server = serverView.getText().toString().trim();
        final String user = userView.getText().toString().trim();
        final String pass = passView.getText().toString();
        if (server.length() == 0) {
            showStatus("请填写服务器地址，例如 192.168.1.20:1819");
            return;
        }
        if (user.length() < 3) {
            showStatus("用户名至少 3 位");
            return;
        }
        if (pass.length() < 6) {
            showStatus("密码至少 6 位");
            return;
        }
        if (registerMode && !pass.equals(confirmView.getText().toString())) {
            showStatus("两次输入的密码不一致");
            return;
        }

        final String path = registerMode ? "/account/register" : "/account/login";
        final String display = displayView.getText().toString().trim();
        setWorking(true);
        showStatus(registerMode ? "正在注册…" : "正在登录…");

        new Thread(new Runnable() {
            @Override
            public void run() {
                String error = null;
                String token = null;
                String shown = user;
                try {
                    DeviceApi.TOKEN = "";
                    DeviceApi call = new DeviceApi(server);
                    JSONObject body = new JSONObject();
                    body.put("username", user);
                    body.put("password", pass);
                    if (registerMode) body.put("display", display);
                    JSONObject result = new JSONObject(call.postJson(path, body.toString()));
                    int code = result.optInt("code", 1);
                    if (code != 0) {
                        error = result.optString("msg", "请求失败");
                    } else {
                        token = result.optString("token", "");
                        shown = result.optString("display", user);
                    }
                } catch (Exception e) {
                    error = "连接服务端失败：" + e.getMessage();
                }

                final String fError = error;
                final String fToken = token;
                final String fShown = shown;
                ui.post(new Runnable() {
                    @Override
                    public void run() {
                        setWorking(false);
                        if (fError != null) {
                            showStatus(fError);
                            return;
                        }
                        DeviceApi.TOKEN = fToken;
                        prefs.edit()
                                .putString("server", server)
                                .putString("ip", server)
                                .putString("user", user)
                                .putString("display", fShown)
                                .putString("token", fToken)
                                .apply();
                        startActivity(new Intent(LoginActivity.this, MainActivity.class));
                        finish();
                    }
                });
            }
        }).start();
    }

    /** 清除登录状态并回到登录页。 */
    static void logoutFrom(Activity activity) {
        DeviceApi.TOKEN = "";
        activity.getSharedPreferences("scarecrow", MODE_PRIVATE)
                .edit().remove("token").remove("user").remove("display").apply();
        Intent intent = new Intent(activity, LoginActivity.class);
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TASK);
        activity.startActivity(intent);
        activity.finish();
    }
}
