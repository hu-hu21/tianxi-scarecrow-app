package com.tianxi.scarecrow;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.Typeface;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.view.ViewGroup;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;

/** 启动页：展示应用图标与版本，短暂停留后进入主界面。 */
public class SplashActivity extends Activity {

    private static final int BG = 0xFF0B1220;
    private static final int TEXT = 0xFFE5EDF7;
    private static final int MUTED = 0xFF93A4BC;
    private static final int ACCENT = 0xFF0EA5E9;

    private final Handler ui = new Handler(Looper.getMainLooper());
    private boolean entered = false;

    private final Runnable enter = new Runnable() {
        @Override
        public void run() {
            if (entered) return;
            entered = true;
            String token = getSharedPreferences("scarecrow", MODE_PRIVATE)
                    .getString("token", "");
            Class<?> next = token != null && token.length() > 0
                    ? MainActivity.class : LoginActivity.class;
            startActivity(new Intent(SplashActivity.this, next));
            overridePendingTransition(android.R.anim.fade_in, android.R.anim.fade_out);
            finish();
        }
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setStatusBarColor(BG);
        getWindow().setNavigationBarColor(BG);

        int dp = (int) (getResources().getDisplayMetrics().density + 0.5f);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(BG);
        root.setGravity(Gravity.CENTER);
        root.setPadding(dp * 32, 0, dp * 32, dp * 40);

        ImageView icon = new ImageView(this);
        int iconId = getResources().getIdentifier(
                "ic_launcher", "mipmap", getPackageName());
        if (iconId != 0) icon.setImageResource(iconId);
        LinearLayout.LayoutParams iconLp = new LinearLayout.LayoutParams(
                dp * 112, dp * 112);
        root.addView(icon, iconLp);

        TextView title = new TextView(this);
        title.setText("稻草人驱鸟控制器");
        title.setTextSize(24f);
        title.setTextColor(TEXT);
        title.setTypeface(Typeface.DEFAULT_BOLD);
        title.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams titleLp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        titleLp.topMargin = dp * 22;
        root.addView(title, titleLp);

        TextView version = new TextView(this);
        version.setText("v3.21.5");
        version.setTextSize(14f);
        version.setTextColor(ACCENT);
        version.setTypeface(Typeface.DEFAULT_BOLD);
        version.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams verLp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        verLp.topMargin = dp * 8;
        root.addView(version, verLp);

        ProgressBar bar = new ProgressBar(this);
        bar.setIndeterminateTintList(
                android.content.res.ColorStateList.valueOf(ACCENT));
        LinearLayout.LayoutParams barLp = new LinearLayout.LayoutParams(
                dp * 40, dp * 40);
        barLp.topMargin = dp * 28;
        root.addView(bar, barLp);

        TextView tip = new TextView(this);
        tip.setText("正在加载设备配置…");
        tip.setTextSize(12f);
        tip.setTextColor(MUTED);
        tip.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams tipLp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        tipLp.topMargin = dp * 12;
        root.addView(tip, tipLp);

        TextView copyright = new TextView(this);
        copyright.setText("开发者：胡宇宸  ·  2026-11-21");
        copyright.setTextSize(11f);
        copyright.setTextColor(Color.parseColor("#5B6B84"));
        copyright.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams cpLp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        cpLp.topMargin = dp * 40;
        root.addView(copyright, cpLp);

        setContentView(root);
        ui.postDelayed(enter, 1500);
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        ui.removeCallbacks(enter);
    }
}
