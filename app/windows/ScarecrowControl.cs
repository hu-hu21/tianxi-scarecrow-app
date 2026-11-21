using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Globalization;
using System.IO;
using System.Net;
using System.Text;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows.Forms;

namespace ScarecrowControl
{
    static class Program
    {
        [STAThread]
        static void Main(string[] args)
        {
            // 供构建脚本验证 exe 可运行，不弹窗
            if (args.Length > 0 && args[0] == "--selftest")
            {
                try
                {
                    var ser = new JavaScriptSerializer();
                    var d = ser.Deserialize<Dictionary<string, object>>("{\"state\":\"IDLE\",\"vbat\":12.34}");
                    if (Presets.All.Length != 6) Environment.Exit(1);
                    foreach (Preset p in Presets.All)
                    {
                        if (p.VolDay < 0 || p.VolDay > 30 || p.VolNight < 0 || p.VolNight > 30) Environment.Exit(1);
                        if (p.Sens < 1 || p.Sens > 8 || p.Cool < 5 || p.Cool > 3600) Environment.Exit(1);
                        if (p.ActiveMin < 2 || p.ActiveMax > 120 || p.ActiveMax <= p.ActiveMin) Environment.Exit(1);
                    }
                    string outFile = Path.Combine(Path.GetTempPath(), "scarecrow_selftest.txt");
                    File.WriteAllText(outFile,
                        "ok state=" + Convert.ToString(d["state"]) +
                        " vbat=" + Convert.ToString(d["vbat"]) +
                        " presets=" + Presets.All.Length, Encoding.UTF8);
                    Environment.Exit(0);
                }
                catch
                {
                    Environment.Exit(1);
                }
            }

            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);

            // 构建脚本用：直接构造扩展功能窗口，验证控件创建不抛异常
            if (args.Length > 0 && args[0] == "--features-selftest")
            {
                try
                {
                    using (FeaturesForm f = new FeaturesForm("192.168.4.1"))
                    {
                        if (f.Controls.Count < 1) Environment.Exit(1);
                        File.WriteAllText(Path.Combine(Path.GetTempPath(), "scarecrow_features.txt"),
                            "ok controls=" + f.Controls.Count, Encoding.UTF8);
                    }
                    Environment.Exit(0);
                }
                catch (Exception ex)
                {
                    File.WriteAllText(Path.Combine(Path.GetTempPath(), "scarecrow_features.txt"),
                        "fail " + ex.GetType().Name + ": " + ex.Message, Encoding.UTF8);
                    Environment.Exit(1);
                }
            }

            if (args.Length > 0 && args[0] == "--features")
            {
                int page = 0;
                if (args.Length > 2) int.TryParse(args[2], out page);
                Application.Run(new FeaturesForm(args.Length > 1 ? args[1] : "192.168.4.1", page));
                return;
            }

            Application.Run(new MainForm());
        }
    }

    static class Theme
    {
        public static readonly Color Bg = Color.FromArgb(11, 18, 32);
        public static readonly Color Card = Color.FromArgb(22, 35, 58);
        public static readonly Color CardEdge = Color.FromArgb(40, 62, 94);
        public static readonly Color Input = Color.FromArgb(15, 27, 46);
        public static readonly Color Text = Color.FromArgb(229, 237, 247);
        public static readonly Color Muted = Color.FromArgb(147, 164, 188);
        public static readonly Color Accent = Color.FromArgb(14, 165, 233);
        public static readonly Color Green = Color.FromArgb(52, 211, 153);
        public static readonly Color Red = Color.FromArgb(220, 38, 38);
        public static readonly Color Amber = Color.FromArgb(245, 158, 11);
    }

    class CardPanel : Panel
    {
        public CardPanel()
        {
            SetStyle(ControlStyles.AllPaintingInWmPaint |
                     ControlStyles.UserPaint |
                     ControlStyles.OptimizedDoubleBuffer, true);
            BackColor = Theme.Card;
        }

        protected override void OnPaintBackground(PaintEventArgs e)
        {
            // 交给 OnPaint 处理圆角
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            Graphics g = e.Graphics;
            g.SmoothingMode = SmoothingMode.AntiAlias;
            g.Clear(Parent != null ? Parent.BackColor : Theme.Bg);

            Rectangle r = new Rectangle(0, 0, Width - 1, Height - 1);
            using (GraphicsPath path = Ui.RoundRect(r, 12))
            using (SolidBrush b = new SolidBrush(BackColor))
            using (Pen pen = new Pen(Theme.CardEdge))
            {
                g.FillPath(b, path);
                g.DrawPath(pen, path);
            }
        }
    }

    class UiButton : Button
    {
        private Color _normal;
        private Color _hover;

        public UiButton(string text, Color back)
        {
            Text = text;
            _normal = back;
            _hover = ControlPaint.Light(back, 0.18f);
            BackColor = back;
            ForeColor = Color.White;
            FlatStyle = FlatStyle.Flat;
            FlatAppearance.BorderSize = 0;
            Font = new Font("Microsoft YaHei UI", 9.5f, FontStyle.Regular);
            Cursor = Cursors.Hand;
            UseVisualStyleBackColor = false;
            TabStop = false;
        }

        protected override void OnMouseEnter(EventArgs e)
        {
            BackColor = _hover;
            base.OnMouseEnter(e);
        }

        protected override void OnMouseLeave(EventArgs e)
        {
            BackColor = _normal;
            base.OnMouseLeave(e);
        }
    }

    static class Ui
    {
        public static GraphicsPath RoundRect(Rectangle r, int radius)
        {
            GraphicsPath p = new GraphicsPath();
            int d = radius * 2;
            p.AddArc(r.X, r.Y, d, d, 180, 90);
            p.AddArc(r.Right - d, r.Y, d, d, 270, 90);
            p.AddArc(r.Right - d, r.Bottom - d, d, d, 0, 90);
            p.AddArc(r.X, r.Bottom - d, d, d, 90, 90);
            p.CloseFigure();
            return p;
        }

        public static Label Lbl(string text, int x, int y, int w, int h,
                                  float size, bool bold, Color color)
        {
            Label l = new Label();
            l.Text = text;
            l.AutoSize = false;
            l.Location = new Point(x, y);
            l.Size = new Size(w, h);
            l.ForeColor = color;
            l.BackColor = Color.Transparent;
            l.Font = new Font("Microsoft YaHei UI", size,
                              bold ? FontStyle.Bold : FontStyle.Regular);
            l.TextAlign = ContentAlignment.MiddleLeft;
            return l;
        }
    }

    static class Http
    {
        public static string Get(string url, int timeoutMs)
        {
            HttpWebRequest req = (HttpWebRequest)WebRequest.Create(url);
            req.Method = "GET";
            req.Proxy = null;
            req.KeepAlive = false;
            req.Timeout = timeoutMs;
            req.ReadWriteTimeout = timeoutMs;
            using (HttpWebResponse resp = (HttpWebResponse)req.GetResponse())
            using (StreamReader sr = new StreamReader(resp.GetResponseStream(), Encoding.UTF8))
            {
                return sr.ReadToEnd();
            }
        }

        public static string Post(string url, string body, int timeoutMs)
        {
            byte[] data = Encoding.UTF8.GetBytes(body ?? "");
            HttpWebRequest req = (HttpWebRequest)WebRequest.Create(url);
            req.Method = "POST";
            req.Proxy = null;
            req.KeepAlive = false;
            req.Timeout = timeoutMs;
            req.ReadWriteTimeout = timeoutMs;
            req.ContentType = "application/x-www-form-urlencoded; charset=utf-8";
            req.ContentLength = data.Length;
            using (Stream s = req.GetRequestStream())
            {
                s.Write(data, 0, data.Length);
            }
            using (HttpWebResponse resp = (HttpWebResponse)req.GetResponse())
            using (StreamReader sr = new StreamReader(resp.GetResponseStream(), Encoding.UTF8))
            {
                return sr.ReadToEnd();
            }
        }

        /// <summary>multipart/form-data 单文件上传，用于视觉识别接口。</summary>
        public static string PostFile(string url, string field, string fileName, byte[] data, int timeoutMs)
        {
            string boundary = "----tianxi" + DateTime.Now.Ticks.ToString("x");
            byte[] head = Encoding.UTF8.GetBytes(
                "--" + boundary + "\r\n" +
                "Content-Disposition: form-data; name=\"" + field + "\"; filename=\"" + fileName + "\"\r\n" +
                "Content-Type: application/octet-stream\r\n\r\n");
            byte[] tail = Encoding.UTF8.GetBytes("\r\n--" + boundary + "--\r\n");

            HttpWebRequest req = (HttpWebRequest)WebRequest.Create(url);
            req.Method = "POST";
            req.Proxy = null;
            req.KeepAlive = false;
            req.Timeout = timeoutMs;
            req.ReadWriteTimeout = timeoutMs;
            req.ContentType = "multipart/form-data; boundary=" + boundary;
            req.ContentLength = head.Length + data.Length + tail.Length;
            using (Stream s = req.GetRequestStream())
            {
                s.Write(head, 0, head.Length);
                s.Write(data, 0, data.Length);
                s.Write(tail, 0, tail.Length);
            }
            using (HttpWebResponse resp = (HttpWebResponse)req.GetResponse())
            using (StreamReader sr = new StreamReader(resp.GetResponseStream(), Encoding.UTF8))
            {
                return sr.ReadToEnd();
            }
        }
    }

    class DarkMenuRenderer : ToolStripProfessionalRenderer
    {
        public DarkMenuRenderer()
        {
            RoundedEdges = false;
        }

        protected override void OnRenderToolStripBackground(ToolStripRenderEventArgs e)
        {
            using (SolidBrush b = new SolidBrush(Theme.Card))
            {
                e.Graphics.FillRectangle(b, e.AffectedBounds);
            }
        }

        protected override void OnRenderMenuItemBackground(ToolStripItemRenderEventArgs e)
        {
            Rectangle r = new Rectangle(0, 0, e.Item.Width, e.Item.Height);
            using (SolidBrush b = new SolidBrush(e.Item.Selected ? Theme.Accent : Theme.Card))
            {
                e.Graphics.FillRectangle(b, r);
            }
        }

        protected override void OnRenderItemText(ToolStripItemTextRenderEventArgs e)
        {
            e.TextColor = e.Item.Selected ? Color.White : Theme.Text;
            base.OnRenderItemText(e);
        }

        protected override void OnRenderToolStripBorder(ToolStripRenderEventArgs e)
        {
            using (Pen p = new Pen(Theme.CardEdge))
            {
                e.Graphics.DrawRectangle(p, 0, 0, e.ToolStrip.Width - 1, e.ToolStrip.Height - 1);
            }
        }
    }

    class Preset
    {
        public string Name;
        public string Hint;
        public int VolDay, VolNight, Sens, Cool, Tracks;
        public int ActiveMin, ActiveMax, QStart, QEnd, Ldr, Trigger;
        public bool QEnable;

        public Preset(string name, string hint, int volDay, int volNight, int sens,
                      int cool, int activeMin, int activeMax, int qStart, int qEnd,
                      int ldr, int trigger, bool qEnable)
        {
            Name = name;
            Hint = hint;
            VolDay = volDay;
            VolNight = volNight;
            Sens = sens;
            Cool = cool;
            Tracks = 8;
            ActiveMin = activeMin;
            ActiveMax = activeMax;
            QStart = qStart;
            QEnd = qEnd;
            Ldr = ldr;
            Trigger = trigger;
            QEnable = qEnable;
        }

        public override string ToString()
        {
            return Name;
        }
    }

    static class Presets
    {
        // 六套现场调好的参数，顺序与下拉框一致
        public static readonly Preset[] All = new Preset[]
        {
            new Preset("标准农田（推荐）", "中等灵敏度、60 秒冷却，适合 2–5 亩大田日常使用",
                       26, 16, 3, 60, 8, 18, 22, 6, 800, 2500, true),
            new Preset("果园 / 大范围", "高灵敏度、短冷却，覆盖 10–30 m，适合果园和开阔地",
                       28, 18, 5, 45, 10, 20, 22, 6, 800, 2200, true),
            new Preset("菜地 / 小范围", "低灵敏度、长冷却，减少误触发和耗电，适合小地块",
                       22, 12, 2, 90, 6, 12, 21, 6, 850, 3000, true),
            new Preset("庭院 / 低扰民", "低音量、短驱赶，降低对邻里的影响，适合房前屋后",
                       18, 10, 2, 120, 5, 10, 21, 7, 900, 3500, true),
            new Preset("夜间低噪", "夜间音量压到 8，保留必要惊吓，适合居民区过夜",
                       24, 8, 3, 90, 6, 12, 23, 5, 700, 2800, true),
            new Preset("强干扰 / 高频", "高音量、30 秒冷却、关闭静音，适合鸟群已适应时短期加强",
                       30, 22, 6, 30, 10, 22, 22, 6, 800, 1800, false),
        };
    }

    class MainForm : Form
    {
        private TextBox _ip;
        private Label _pill;
        private Label _state, _vbat, _light, _quiet, _pulses, _uptime, _fw, _mode;
        private NumericUpDown _volDay, _volNight, _sens, _cool, _tracks;
        private NumericUpDown _activeMin, _activeMax, _qStart, _qEnd, _ldr, _trigger;
        private CheckBox _qEnable;
        private Button _preset;
        private ContextMenuStrip _presetMenu;
        private int _presetIndex;
        private Label _presetHint;
        private TextBox _logBox;
        private Timer _timer;

        private bool _busy;
        private bool _online;
        private bool _configLoaded;
        private string _lastIp = "";
        private string _lastError = "";

        private readonly JavaScriptSerializer _json = new JavaScriptSerializer();

        public MainForm()
        {
            Text = "稻草人驱鸟控制器 - Windows 控制台";
            ClientSize = new Size(1000, 720);
            FormBorderStyle = FormBorderStyle.FixedSingle;
            MaximizeBox = false;
            StartPosition = FormStartPosition.CenterScreen;
            BackColor = Theme.Bg;
            ForeColor = Theme.Text;
            Font = new Font("Microsoft YaHei UI", 9.5f);
            AutoScaleMode = AutoScaleMode.None;

            BuildHeader();
            BuildStatusCard();
            BuildActionCard();
            BuildConfigCard();
            BuildLogCard();

            LoadSettings();
            ApplyDpiScale();

            _timer = new Timer();
            _timer.Interval = 2000;
            _timer.Tick += delegate { PollTick(); };
            _timer.Start();

            Shown += delegate
            {
                if (_ip.Text.Trim().Length > 0)
                {
                    PollTick();
                }
            };
        }

        private void BuildHeader()
        {
            Controls.Add(Ui.Lbl("稻草人驱鸟控制器", 20, 12, 380, 34, 18f, true, Theme.Text));
            Controls.Add(Ui.Lbl("Windows 控制台  ·  Wi-Fi 局域网直连", 22, 46, 360, 22, 9f, false, Theme.Muted));

            Controls.Add(Ui.Lbl("设备地址", 604, 20, 66, 26, 9f, false, Theme.Muted));

            _ip = new TextBox();
            _ip.Text = "192.168.4.1";
            _ip.Location = new Point(672, 19);
            _ip.Size = new Size(150, 28);
            _ip.BackColor = Theme.Input;
            _ip.ForeColor = Theme.Text;
            _ip.BorderStyle = BorderStyle.FixedSingle;
            _ip.Font = new Font("Consolas", 10.5f);
            Controls.Add(_ip);

            UiButton connect = new UiButton("连接", Theme.Accent);
            connect.Location = new Point(830, 17);
            connect.Size = new Size(72, 32);
            connect.Click += delegate { ConnectNow(); };
            Controls.Add(connect);

            UiButton auto = new UiButton("自动查找", Theme.CardEdge);
            auto.Location = new Point(910, 17);
            auto.Size = new Size(74, 32);
            auto.Click += delegate { AutoDetect(); };
            Controls.Add(auto);

            UiButton about = new UiButton("关于", Theme.CardEdge);
            about.Location = new Point(506, 18);
            about.Size = new Size(72, 30);
            about.Font = new Font("Microsoft YaHei UI", 9f);
            about.Click += delegate { ShowAbout(); };
            Controls.Add(about);

            UiButton ext = new UiButton("扩展功能", Theme.Accent);
            ext.Location = new Point(420, 18);
            ext.Size = new Size(78, 30);
            ext.Font = new Font("Microsoft YaHei UI", 9f);
            ext.Click += delegate
            {
                using (FeaturesForm f = new FeaturesForm(_ip.Text))
                {
                    f.ShowDialog(this);
                }
            };
            Controls.Add(ext);

            _pill = Ui.Lbl("● 未连接", 606, 54, 378, 22, 9f, false, Theme.Muted);
            Controls.Add(_pill);
        }

        private void ShowAbout()
        {
            Form dlg = new Form();
            dlg.Text = "关于";
            dlg.ClientSize = new Size(560, 380);
            dlg.FormBorderStyle = FormBorderStyle.FixedDialog;
            dlg.MaximizeBox = false;
            dlg.MinimizeBox = false;
            dlg.ShowInTaskbar = false;
            dlg.StartPosition = FormStartPosition.CenterParent;
            dlg.BackColor = Theme.Bg;
            dlg.ForeColor = Theme.Text;
            dlg.Font = new Font("Microsoft YaHei UI", 9.5f);
            dlg.AutoScaleMode = AutoScaleMode.None;

            dlg.Controls.Add(Ui.Lbl("关于 稻草人驱鸟控制器", 24, 18, 500, 34, 17f, true, Theme.Text));
            dlg.Controls.Add(Ui.Lbl("Windows 控制台  ·  独立原创作品", 26, 54, 500, 22, 9f, false, Theme.Muted));

            dlg.Controls.Add(Ui.Lbl("Copyright (C) 2026 【胡宇宸/tj248511fg51/y9000p】",
                                    26, 94, 508, 26, 10.5f, true, Theme.Text));

            Label terms = Ui.Lbl(
                "本程序为独立原创作品，版权归作者所有。\n" +
                "严禁未经许可反编译、逆向工程、破解、修改源码、非法复制及传播。\n" +
                "对于本软件相关规则、使用说明，最终解释权归作者本人。",
                26, 128, 508, 120, 9.5f, false, Theme.Muted);
            terms.TextAlign = ContentAlignment.TopLeft;
            dlg.Controls.Add(terms);

            UiButton close = new UiButton("关闭", Theme.Accent);
            close.Location = new Point(408, 316);
            close.Size = new Size(126, 38);
            close.Click += delegate { dlg.Close(); };
            dlg.Controls.Add(close);
            dlg.AcceptButton = close;

            dlg.ShowDialog(this);
        }

        private CardPanel NewCard(int x, int y, int w, int h, string title)
        {
            CardPanel card = new CardPanel();
            card.Location = new Point(x, y);
            card.Size = new Size(w, h);
            Controls.Add(card);
            card.Controls.Add(Ui.Lbl(title, 16, 10, w - 32, 26, 11f, true, Theme.Text));
            return card;
        }

        private void BuildStatusCard()
        {
            CardPanel card = NewCard(16, 92, 470, 230, "设备状态");

            int[] ys = new int[] { 48, 92, 136, 180 };

            card.Controls.Add(Ui.Lbl("运行状态", 18, ys[0], 74, 24, 9f, false, Theme.Muted));
            _state = Ui.Lbl("--", 96, ys[0], 120, 24, 10f, true, Theme.Text);
            card.Controls.Add(_state);

            card.Controls.Add(Ui.Lbl("电池电压", 242, ys[0], 74, 24, 9f, false, Theme.Muted));
            _vbat = Ui.Lbl("--", 320, ys[0], 120, 24, 10f, true, Theme.Text);
            card.Controls.Add(_vbat);

            card.Controls.Add(Ui.Lbl("光照环境", 18, ys[1], 74, 24, 9f, false, Theme.Muted));
            _light = Ui.Lbl("--", 96, ys[1], 120, 24, 10f, true, Theme.Text);
            card.Controls.Add(_light);

            card.Controls.Add(Ui.Lbl("静音时段", 242, ys[1], 74, 24, 9f, false, Theme.Muted));
            _quiet = Ui.Lbl("--", 320, ys[1], 120, 24, 10f, true, Theme.Text);
            card.Controls.Add(_quiet);

            card.Controls.Add(Ui.Lbl("雷达脉冲", 18, ys[2], 74, 24, 9f, false, Theme.Muted));
            _pulses = Ui.Lbl("--", 96, ys[2], 120, 24, 10f, true, Theme.Text);
            card.Controls.Add(_pulses);

            card.Controls.Add(Ui.Lbl("在线时长", 242, ys[2], 74, 24, 9f, false, Theme.Muted));
            _uptime = Ui.Lbl("--", 320, ys[2], 120, 24, 10f, true, Theme.Text);
            card.Controls.Add(_uptime);

            card.Controls.Add(Ui.Lbl("固件版本", 18, ys[3], 74, 24, 9f, false, Theme.Muted));
            _fw = Ui.Lbl("--", 96, ys[3], 120, 24, 10f, true, Theme.Text);
            card.Controls.Add(_fw);

            card.Controls.Add(Ui.Lbl("网络模式", 242, ys[3], 74, 24, 9f, false, Theme.Muted));
            _mode = Ui.Lbl("--", 320, ys[3], 120, 24, 10f, true, Theme.Text);
            card.Controls.Add(_mode);
        }

        private void BuildActionCard()
        {
            CardPanel card = NewCard(16, 334, 470, 238, "快捷操作");

            AddActionButton(card, "立即试驱", 18, 44, 210, Theme.Accent, "all");
            AddActionButton(card, "声音测试", 240, 44, 210, Theme.CardEdge, "sound");
            AddActionButton(card, "灯光测试", 18, 94, 210, Theme.CardEdge, "light");
            AddActionButton(card, "云台测试", 240, 94, 210, Theme.CardEdge, "servo");
            AddActionButton(card, "停止输出", 18, 144, 210, Theme.Red, "stop");

            UiButton web = new UiButton("打开网页控制台", Theme.CardEdge);
            web.Location = new Point(240, 144);
            web.Size = new Size(210, 40);
            web.Click += delegate { OpenWeb(); };
            card.Controls.Add(web);

            UiButton reset = new UiButton("恢复设备默认值", Theme.CardEdge);
            reset.Location = new Point(18, 194);
            reset.Size = new Size(210, 36);
            reset.Click += delegate { ResetDevice(); };
            card.Controls.Add(reset);

            UiButton reboot = new UiButton("重启设备", Theme.CardEdge);
            reboot.Location = new Point(240, 194);
            reboot.Size = new Size(210, 36);
            reboot.Click += delegate { RebootDevice(); };
            card.Controls.Add(reboot);
        }

        private void AddActionButton(CardPanel card, string text, int x, int y, int w,
                                     Color color, string what)
        {
            UiButton b = new UiButton(text, color);
            b.Location = new Point(x, y);
            b.Size = new Size(w, 40);
            b.Click += delegate { TestAction(what); };
            card.Controls.Add(b);
        }

        private NumericUpDown AddNum(CardPanel card, string label, int y,
                                     decimal min, decimal max, decimal step, decimal val)
        {
            card.Controls.Add(Ui.Lbl(label, 18, y, 220, 26, 9f, false, Theme.Muted));
            NumericUpDown n = new NumericUpDown();
            n.Location = new Point(250, y);
            n.Size = new Size(200, 26);
            n.Minimum = min;
            n.Maximum = max;
            n.Increment = step;
            n.Value = val;
            n.BackColor = Theme.Input;
            n.ForeColor = Theme.Text;
            n.BorderStyle = BorderStyle.FixedSingle;
            n.Font = new Font("Consolas", 10.5f);
            n.TextAlign = HorizontalAlignment.Right;
            card.Controls.Add(n);
            return n;
        }

        private void BuildConfigCard()
        {
            CardPanel card = NewCard(502, 92, 482, 500, "参数配置");

            card.Controls.Add(Ui.Lbl("推荐场景", 18, 38, 74, 26, 9f, false, Theme.Muted));

            _preset = new UiButton(Presets.All[0].Name + "  ▾", Theme.Input);
            _preset.Location = new Point(96, 38);
            _preset.Size = new Size(250, 26);
            _preset.TextAlign = ContentAlignment.MiddleLeft;
            _preset.Padding = new Padding(8, 0, 0, 0);
            _preset.Font = new Font("Microsoft YaHei UI", 9f);
            _preset.Click += delegate
            {
                _presetMenu.Show(_preset, new Point(0, _preset.Height));
            };
            card.Controls.Add(_preset);

            _presetMenu = new ContextMenuStrip();
            _presetMenu.Renderer = new DarkMenuRenderer();
            _presetMenu.BackColor = Theme.Card;
            _presetMenu.ForeColor = Theme.Text;
            _presetMenu.Font = new Font("Microsoft YaHei UI", 9f);
            _presetMenu.ShowImageMargin = false;
            _presetMenu.ShowCheckMargin = false;
            _presetMenu.Padding = new Padding(0, 4, 0, 4);
            for (int i = 0; i < Presets.All.Length; i++)
            {
                int idx = i;
                ToolStripMenuItem item = new ToolStripMenuItem(Presets.All[i].Name);
                item.BackColor = Theme.Card;
                item.ForeColor = Theme.Text;
                item.Padding = new Padding(10, 4, 14, 4);
                item.Click += delegate { SelectPreset(idx); };
                _presetMenu.Items.Add(item);
            }

            UiButton usePreset = new UiButton("一键套用", Theme.Green);
            usePreset.Location = new Point(354, 36);
            usePreset.Size = new Size(110, 30);
            usePreset.Font = new Font("Microsoft YaHei UI", 8.5f);
            usePreset.Click += delegate { ApplyPreset(); };
            card.Controls.Add(usePreset);

            _presetHint = Ui.Lbl("", 18, 66, 446, 20, 8f, false, Theme.Muted);
            card.Controls.Add(_presetHint);
            UpdatePresetHint();

            int y = 92;
            int step = 29;
            _volDay = AddNum(card, "白天音量 (0-30)", y, 0, 30, 1, 26); y += step;
            _volNight = AddNum(card, "夜间音量 (0-30)", y, 0, 30, 1, 16); y += step;
            _sens = AddNum(card, "雷达灵敏度 (1-8)", y, 1, 8, 1, 3); y += step;
            _cool = AddNum(card, "冷却时间 (秒)", y, 5, 3600, 5, 60); y += step;
            _tracks = AddNum(card, "音轨数量", y, 1, 99, 1, 8); y += step;
            _activeMin = AddNum(card, "驱赶最短 (秒)", y, 2, 120, 1, 8); y += step;
            _activeMax = AddNum(card, "驱赶最长 (秒)", y, 2, 120, 1, 18); y += step;
            _qStart = AddNum(card, "静音开始 (时)", y, 0, 23, 1, 22); y += step;
            _qEnd = AddNum(card, "静音结束 (时)", y, 0, 23, 1, 6); y += step;
            _ldr = AddNum(card, "夜间阈值 (ADC)", y, 0, 4095, 50, 800); y += step;
            _trigger = AddNum(card, "触发窗口 (ms)", y, 500, 10000, 100, 2500);

            _qEnable = new CheckBox();
            _qEnable.Text = "启用静音时段（需设备已对时）";
            _qEnable.Location = new Point(250, 414);
            _qEnable.Size = new Size(220, 24);
            _qEnable.ForeColor = Theme.Text;
            _qEnable.BackColor = Color.Transparent;
            _qEnable.Font = new Font("Microsoft YaHei UI", 9f);
            card.Controls.Add(_qEnable);

            UiButton save = new UiButton("保存配置", Theme.Accent);
            save.Location = new Point(18, 446);
            save.Size = new Size(120, 36);
            save.Click += delegate { SaveConfig(); };
            card.Controls.Add(save);

            UiButton read = new UiButton("读取", Theme.CardEdge);
            read.Location = new Point(146, 446);
            read.Size = new Size(90, 36);
            read.Click += async delegate { await LoadConfig(true); };
            card.Controls.Add(read);

            UiButton def = new UiButton("恢复默认", Theme.CardEdge);
            def.Location = new Point(244, 446);
            def.Size = new Size(120, 36);
            def.Click += delegate { ResetDevice(); };
            card.Controls.Add(def);
        }

        private void SelectPreset(int index)
        {
            if (index < 0 || index >= Presets.All.Length) return;
            _presetIndex = index;
            _preset.Text = Presets.All[index].Name + "  ▾";
            UpdatePresetHint();
        }

        private void UpdatePresetHint()
        {
            if (_presetHint == null) return;
            _presetHint.Text = Presets.All[_presetIndex].Hint;
        }

        private async void ApplyPreset()
        {
            Preset p = Presets.All[_presetIndex];

            _volDay.Value = p.VolDay;
            _volNight.Value = p.VolNight;
            _sens.Value = p.Sens;
            _cool.Value = p.Cool;
            _tracks.Value = p.Tracks;
            _activeMin.Value = p.ActiveMin;
            _activeMax.Value = p.ActiveMax;
            _qStart.Value = p.QStart;
            _qEnd.Value = p.QEnd;
            _ldr.Value = p.Ldr;
            _trigger.Value = p.Trigger;
            _qEnable.Checked = p.QEnable;

            Log("已套用推荐场景：" + p.Name);
            if (!_online)
            {
                Log("设备未连接，参数已填入；连接后点“保存配置”即可下发。");
                return;
            }

            try
            {
                string json = await Task.Run(() => Http.Post(Url("/api/config"), ConfigBody(), 3000));
                ApplyStatus(Parse(json));
                Log("推荐参数已保存到设备");
            }
            catch (Exception ex)
            {
                Log("保存推荐参数失败：" + ex.Message);
            }
        }

        private void BuildLogCard()
        {
            CardPanel card = NewCard(16, 604, 968, 100, "运行日志");

            _logBox = new TextBox();
            _logBox.Location = new Point(16, 40);
            _logBox.Size = new Size(936, 48);
            _logBox.Multiline = true;
            _logBox.ReadOnly = true;
            _logBox.ScrollBars = ScrollBars.Vertical;
            _logBox.BackColor = Theme.Input;
            _logBox.ForeColor = Theme.Muted;
            _logBox.BorderStyle = BorderStyle.None;
            _logBox.Font = new Font("Consolas", 9f);
            card.Controls.Add(_logBox);
        }

        private void ApplyDpiScale()
        {
            float scale;
            using (Graphics g = CreateGraphics())
            {
                scale = g.DpiX / 96f;
            }
            // 保证整窗不超出屏幕可用区域
            float maxScale = Math.Min(
                (Screen.PrimaryScreen.WorkingArea.Width - 40) / 1000f,
                (Screen.PrimaryScreen.WorkingArea.Height - 80) / 720f);
            if (maxScale < 0.7f) maxScale = 0.7f;
            if (scale > maxScale) scale = maxScale;

            if (scale < 0.95f || scale > 1.05f)
            {
                Scale(new SizeF(scale, scale));
                ClientSize = new Size((int)(1000 * scale), (int)(720 * scale));
            }
        }

        // ---------------- 配置持久化 ----------------

        private static string SettingsPath
        {
            get
            {
                string dir = Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
                    "ScarecrowControl");
                Directory.CreateDirectory(dir);
                return Path.Combine(dir, "settings.ini");
            }
        }

        private void LoadSettings()
        {
            try
            {
                if (File.Exists(SettingsPath))
                {
                    string[] lines = File.ReadAllLines(SettingsPath, Encoding.UTF8);
                    foreach (string line in lines)
                    {
                        int eq = line.IndexOf('=');
                        if (eq > 0 && line.Substring(0, eq).Trim() == "ip")
                        {
                            _ip.Text = line.Substring(eq + 1).Trim();
                        }
                    }
                }
            }
            catch
            {
            }
        }

        private void SaveSettings()
        {
            try
            {
                File.WriteAllText(SettingsPath, "ip=" + _ip.Text.Trim(), Encoding.UTF8);
            }
            catch
            {
            }
        }

        // ---------------- 网络 ----------------

        private string Ip
        {
            get { return _ip.Text.Trim(); }
        }

        private string Url(string path)
        {
            string ip = Ip;
            if (ip.StartsWith("http://", StringComparison.OrdinalIgnoreCase))
            {
                return ip.TrimEnd('/') + path;
            }
            return "http://" + ip + path;
        }

        private void Log(string text)
        {
            string line = DateTime.Now.ToString("HH:mm:ss  ") + text + "\r\n";
            _logBox.AppendText(line);
            if (_logBox.TextLength > 12000)
            {
                _logBox.Text = _logBox.Text.Substring(_logBox.TextLength - 6000);
            }
            _logBox.SelectionStart = _logBox.TextLength;
            _logBox.ScrollToCaret();
        }

        private void SetOnline(bool online, string message)
        {
            bool changed = _online != online;
            _online = online;

            if (online)
            {
                _pill.Text = "● 已连接  " + Ip;
                _pill.ForeColor = Theme.Green;
            }
            else
            {
                _pill.Text = "● 未连接" + (message.Length > 0 ? "  " + message : "");
                _pill.ForeColor = Theme.Red;
            }

            if (changed)
            {
                Log(online ? "已连接到设备 " + Ip : "连接中断：" + message);
            }
        }

        private async void ConnectNow()
        {
            _lastIp = Ip;
            _configLoaded = false;
            SaveSettings();
            Log("正在连接 " + Ip + " …");
            await RefreshStatus();
            if (_online)
            {
                await LoadConfig(false);
            }
        }

        private async void PollTick()
        {
            if (_busy) return;
            if (Ip.Length == 0) return;
            _busy = true;
            try
            {
                await RefreshStatus();
            }
            finally
            {
                _busy = false;
            }
        }

        private async Task RefreshStatus()
        {
            string ip = Ip;
            if (ip.Length == 0) return;

            try
            {
                string json = await Task.Run(() => Http.Get(Url("/api/status"), 2500));
                Dictionary<string, object> d = Parse(json);
                ApplyStatus(d);
                SetOnline(true, "");

                if (!_configLoaded && _lastIp != ip)
                {
                    _lastIp = ip;
                    ApplyConfig(d);
                    _configLoaded = true;
                }
            }
            catch (Exception ex)
            {
                string msg = ex.Message;
                if (msg.Length > 60) msg = msg.Substring(0, 60);
                if (_online || _lastError != msg)
                {
                    _lastError = msg;
                    SetOnline(false, msg);
                }
            }
        }

        private Dictionary<string, object> Parse(string json)
        {
            return _json.Deserialize<Dictionary<string, object>>(json);
        }

        private static double Num(Dictionary<string, object> d, string key, double def)
        {
            object v;
            if (!d.TryGetValue(key, out v) || v == null) return def;
            try
            {
                return Convert.ToDouble(v, CultureInfo.InvariantCulture);
            }
            catch
            {
                return def;
            }
        }

        private static string Str(Dictionary<string, object> d, string key, string def)
        {
            object v;
            if (!d.TryGetValue(key, out v) || v == null) return def;
            return Convert.ToString(v, CultureInfo.InvariantCulture);
        }

        private void ApplyStatus(Dictionary<string, object> d)
        {
            string state = Str(d, "state", "--");
            _state.Text = state == "ACTIVE" ? "驱赶中" : (state == "COOLDOWN" ? "冷却中" : "待机");
            _state.ForeColor = state == "ACTIVE" ? Theme.Amber : Theme.Text;

            double vbat = Num(d, "vbat", 0);
            _vbat.Text = vbat.ToString("0.00", CultureInfo.InvariantCulture) + " V";
            _vbat.ForeColor = vbat < 11.0 && vbat > 0.1 ? Theme.Red : Theme.Green;

            _light.Text = Num(d, "night", 0) > 0 ? "夜间" : "白天";
            _quiet.Text = Num(d, "quiet", 0) > 0 ? "生效中" : "未生效";
            _quiet.ForeColor = Num(d, "quiet", 0) > 0 ? Theme.Amber : Theme.Text;

            _pulses.Text = Num(d, "pulses", 0).ToString("0", CultureInfo.InvariantCulture);
            _uptime.Text = FormatUptime(Num(d, "uptime", 0));
            _fw.Text = "v" + Str(d, "fw", "--");
            _mode.Text = Str(d, "mode", "--") + (Num(d, "rssi", 0) != 0
                ? "  " + Num(d, "rssi", 0).ToString("0", CultureInfo.InvariantCulture) + " dBm"
                : "");
        }

        private static string FormatUptime(double sec)
        {
            int s = (int)sec;
            int h = s / 3600;
            int m = (s % 3600) / 60;
            return h > 0 ? h + " 小时 " + m + " 分" : m + " 分钟";
        }

        private void ApplyConfig(Dictionary<string, object> d)
        {
            _volDay.Value = Clamp(Num(d, "volDay", 26), 0, 30);
            _volNight.Value = Clamp(Num(d, "volNight", 16), 0, 30);
            _sens.Value = Clamp(Num(d, "sens", 3), 1, 8);
            _cool.Value = Clamp(Num(d, "cool", 60), 5, 3600);
            _tracks.Value = Clamp(Num(d, "tracks", 8), 1, 99);
            _activeMin.Value = Clamp(Num(d, "activeMin", 8000) / 1000.0, 2, 120);
            _activeMax.Value = Clamp(Num(d, "activeMax", 18000) / 1000.0, 2, 120);
            _qStart.Value = Clamp(Num(d, "qStart", 22), 0, 23);
            _qEnd.Value = Clamp(Num(d, "qEnd", 6), 0, 23);
            _ldr.Value = Clamp(Num(d, "ldr", 800), 0, 4095);
            _trigger.Value = Clamp(Num(d, "trigger", 2500), 500, 10000);
            _qEnable.Checked = Num(d, "qEnable", 0) > 0;
        }

        private static decimal Clamp(double v, int min, int max)
        {
            if (v < min) return min;
            if (v > max) return max;
            return (decimal)v;
        }

        private async Task LoadConfig(bool log)
        {
            try
            {
                string json = await Task.Run(() => Http.Get(Url("/api/config"), 2500));
                ApplyConfig(Parse(json));
                if (log) Log("已读取设备配置");
            }
            catch (Exception ex)
            {
                if (log) Log("读取配置失败：" + ex.Message);
            }
        }

        private string ConfigBody()
        {
            StringBuilder sb = new StringBuilder();
            sb.Append("volDay=").Append((int)_volDay.Value);
            sb.Append("&volNight=").Append((int)_volNight.Value);
            sb.Append("&sens=").Append((int)_sens.Value);
            sb.Append("&cool=").Append((int)_cool.Value);
            sb.Append("&tracks=").Append((int)_tracks.Value);
            sb.Append("&activeMin=").Append((int)_activeMin.Value * 1000);
            sb.Append("&activeMax=").Append((int)_activeMax.Value * 1000);
            sb.Append("&qStart=").Append((int)_qStart.Value);
            sb.Append("&qEnd=").Append((int)_qEnd.Value);
            sb.Append("&ldr=").Append((int)_ldr.Value);
            sb.Append("&trigger=").Append((int)_trigger.Value);
            sb.Append("&qEnable=").Append(_qEnable.Checked ? "1" : "0");
            return sb.ToString();
        }

        private async void SaveConfig()
        {
            try
            {
                string body = ConfigBody();
                string json = await Task.Run(() => Http.Post(Url("/api/config"), body, 3000));
                ApplyStatus(Parse(json));
                Log("配置已保存到设备");
            }
            catch (Exception ex)
            {
                Log("保存失败：" + ex.Message);
            }
        }

        private async void TestAction(string what)
        {
            string name = what == "all" ? "立即试驱"
                        : what == "sound" ? "声音测试"
                        : what == "light" ? "灯光测试"
                        : what == "servo" ? "云台测试" : "停止输出";
            try
            {
                await Task.Run(() => Http.Post(Url("/api/test?what=" + what), "", 3000));
                Log("已发送：" + name);
                await RefreshStatus();
            }
            catch (Exception ex)
            {
                Log(name + "失败：" + ex.Message);
            }
        }

        private async void ResetDevice()
        {
            if (MessageBox.Show("将把设备参数恢复为出厂默认值，是否继续？", "确认",
                                MessageBoxButtons.YesNo, MessageBoxIcon.Question) != DialogResult.Yes)
            {
                return;
            }
            try
            {
                await Task.Run(() => Http.Post(Url("/api/reset"), "", 3000));
                Log("设备参数已恢复默认");
                await LoadConfig(true);
            }
            catch (Exception ex)
            {
                Log("恢复默认失败：" + ex.Message);
            }
        }

        private async void RebootDevice()
        {
            if (MessageBox.Show("确定重启设备？重启期间会断开约 5 秒。", "确认",
                                MessageBoxButtons.YesNo, MessageBoxIcon.Question) != DialogResult.Yes)
            {
                return;
            }
            try
            {
                await Task.Run(() => Http.Post(Url("/api/reboot"), "", 3000));
                Log("设备正在重启…");
                SetOnline(false, "重启中");
            }
            catch (Exception ex)
            {
                Log("重启指令发送失败：" + ex.Message);
            }
        }

        private void OpenWeb()
        {
            try
            {
                Process.Start(new ProcessStartInfo(Url("/")) { UseShellExecute = true });
                Log("已在浏览器打开 " + Url("/"));
            }
            catch (Exception ex)
            {
                Log("打开浏览器失败：" + ex.Message);
            }
        }

        private async void AutoDetect()
        {
            Log("正在查找设备…");
            string found = null;

            await Task.Run(delegate
            {
                try
                {
                    IPAddress[] addrs = Dns.GetHostAddresses("scarecrow.local");
                    if (addrs.Length > 0)
                    {
                        found = addrs[0].ToString();
                        return;
                    }
                }
                catch
                {
                }

                try
                {
                    Http.Get("http://192.168.4.1/api/status", 1500);
                    found = "192.168.4.1";
                }
                catch
                {
                }
            });

            if (found != null)
            {
                _ip.Text = found;
                SaveSettings();
                Log("已发现设备：" + found);
                await RefreshStatus();
                await LoadConfig(false);
            }
            else
            {
                Log("未发现设备。请先连接 Scarecrow-XXXX 热点（默认密码见设备标签），或手动输入 IP。");
            }
        }
    }
}
