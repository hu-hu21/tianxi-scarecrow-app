using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Text;
using System.Threading;
using System.Web.Script.Serialization;
using System.Windows.Forms;

namespace ScarecrowControl
{
    /// <summary>登录 / 注册窗口。账号保存在 Windows 服务端的 accounts.cfg。</summary>
    class LoginForm : Form
    {
        private readonly TextBox _server;
        private readonly TextBox _user;
        private readonly TextBox _pass;
        private readonly TextBox _confirm;
        private readonly TextBox _display;
        private readonly Label _confirmLabel;
        private readonly Label _displayLabel;
        private readonly UiButton _submit;
        private readonly UiButton _switch;
        private readonly Label _status;
        private readonly Label _tip;

        private bool _registerMode;

        public string ServerAddress { get; private set; }
        public string SessionToken { get; private set; }
        public string LoginUser { get; private set; }
        public string DisplayName { get; private set; }

        public LoginForm()
        {
            Text = "登录 · 稻草人驱鸟控制器 v3.21.5";
            ClientSize = new Size(470, 566);
            FormBorderStyle = FormBorderStyle.FixedSingle;
            MaximizeBox = false;
            MinimizeBox = false;
            StartPosition = FormStartPosition.CenterScreen;
            BackColor = Theme.Bg;
            ForeColor = Theme.Text;
            Font = new Font("Microsoft YaHei UI", 9.5f);
            AutoScaleMode = AutoScaleMode.None;
            DoubleBuffered = true;

            Controls.Add(Ui.Lbl("稻草人驱鸟控制器", 36, 28, 380, 40, 21f, true, Theme.Text));
            Controls.Add(Ui.Lbl("登录后经统一服务端访问你的硬件  ·  v3.21.5", 38, 70, 400, 22, 9f, false, Theme.Muted));
            Controls.Add(Ui.Lbl("开发者 胡宇宸  ·  2026-11-21", 38, 96, 400, 20, 8.5f, false, Theme.Muted));

            Controls.Add(Ui.Lbl("服务器地址", 38, 134, 200, 22, 9f, false, Theme.Muted));
            _server = Input(38, 158, 394);
            Controls.Add(_server);

            Controls.Add(Ui.Lbl("用户名", 38, 202, 200, 22, 9f, false, Theme.Muted));
            _user = Input(38, 226, 394);
            Controls.Add(_user);

            Controls.Add(Ui.Lbl("密码", 38, 270, 200, 22, 9f, false, Theme.Muted));
            _pass = Input(38, 294, 394);
            _pass.UseSystemPasswordChar = true;
            Controls.Add(_pass);

            _confirmLabel = Ui.Lbl("确认密码", 38, 338, 200, 22, 9f, false, Theme.Muted);
            Controls.Add(_confirmLabel);
            _confirm = Input(38, 362, 394);
            _confirm.UseSystemPasswordChar = true;
            Controls.Add(_confirm);

            _displayLabel = Ui.Lbl("显示名称（可选）", 38, 406, 250, 22, 9f, false, Theme.Muted);
            Controls.Add(_displayLabel);
            _display = Input(38, 430, 394);
            Controls.Add(_display);

            _tip = Ui.Lbl("首次使用请点击右侧【立即注册】创建账号。\r\n登录后可在【硬件设置】添加自己的硬件，数据统一经服务端转发。",
                38, 348, 394, 46, 8.5f, false, Theme.Muted);
            Controls.Add(_tip);

            _submit = new UiButton("登 录", Theme.Accent);
            _submit.Location = new Point(38, 474);
            _submit.Size = new Size(226, 42);
            _submit.Click += delegate { Submit(); };
            Controls.Add(_submit);

            _switch = new UiButton("没有账号？立即注册", Theme.Card);
            _switch.Location = new Point(272, 474);
            _switch.Size = new Size(160, 42);
            _switch.Font = new Font("Microsoft YaHei UI", 8.5f);
            _switch.Click += delegate { SetMode(!_registerMode); };
            Controls.Add(_switch);

            _status = Ui.Lbl("", 38, 528, 394, 24, 9f, false, Theme.Red);
            Controls.Add(_status);

            AcceptButton = _submit;
            LoadLogin();
            SetMode(false);
        }

        private TextBox Input(int x, int y, int w)
        {
            TextBox t = new TextBox();
            t.Location = new Point(x, y);
            t.Size = new Size(w, 28);
            t.BackColor = Theme.Input;
            t.ForeColor = Theme.Text;
            t.BorderStyle = BorderStyle.FixedSingle;
            t.Font = new Font("Microsoft YaHei UI", 10.5f);
            return t;
        }

        private static string LoginFile
        {
            get { return Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "login.ini"); }
        }

        private void LoadLogin()
        {
            try
            {
                string server = "127.0.0.1:18080";
                string user = "";
                if (File.Exists(LoginFile))
                {
                    foreach (string raw in File.ReadAllLines(LoginFile, Encoding.UTF8))
                    {
                        int eq = raw.IndexOf('=');
                        if (eq <= 0) continue;
                        string k = raw.Substring(0, eq).Trim();
                        string v = raw.Substring(eq + 1).Trim();
                        if (k == "server" && v.Length > 0) server = v;
                        if (k == "user") user = v;
                    }
                }
                _server.Text = server;
                _user.Text = user;
                _pass.Text = "";
            }
            catch { _server.Text = "127.0.0.1:18080"; }
        }

        private void SaveLogin()
        {
            try
            {
                File.WriteAllText(LoginFile,
                    "server=" + _server.Text.Trim() + "\nuser=" + _user.Text.Trim() + "\n",
                    new UTF8Encoding(false));
            }
            catch { }
        }

        private void SetMode(bool register)
        {
            _registerMode = register;
            _confirmLabel.Visible = register;
            _confirm.Visible = register;
            _displayLabel.Visible = register;
            _display.Visible = register;
            _tip.Visible = !register;
            _submit.Text = register ? "注 册" : "登 录";
            _switch.Text = register ? "已有账号？返回登录" : "没有账号？立即注册";
            _status.Text = "";
            if (register)
            {
                ClientSize = new Size(470, 566);
                Height = 605;
            }
            else
            {
                _confirm.Text = "";
                _display.Text = "";
                ClientSize = new Size(470, 566);
                Height = 605;
            }
        }

        private void Submit()
        {
            string server = _server.Text.Trim();
            string user = _user.Text.Trim();
            string pass = _pass.Text;
            if (server.Length == 0)
            {
                ShowStatus("请填写服务器地址，例如 192.168.1.20:1819");
                return;
            }
            if (user.Length < 3)
            {
                ShowStatus("用户名至少 3 位");
                return;
            }
            if (pass.Length < 6)
            {
                ShowStatus("密码至少 6 位");
                return;
            }
            if (_registerMode && pass != _confirm.Text)
            {
                ShowStatus("两次输入的密码不一致");
                return;
            }

            string url = Normalize(server);
            string path = _registerMode ? "/account/register" : "/account/login";
            Dictionary<string, object> body = new Dictionary<string, object>();
            body["username"] = user;
            body["password"] = pass;
            if (_registerMode) body["display"] = _display.Text.Trim();

            _submit.Enabled = false;
            _switch.Enabled = false;
            ShowStatus(_registerMode ? "正在注册…" : "正在登录…", Theme.Muted);
            string json = new JavaScriptSerializer().Serialize(body);

            ThreadPool.QueueUserWorkItem(delegate
            {
                string error = null;
                string token = null;
                string display = null;
                try
                {
                    Http.Token = "";
                    string text = Http.Post(url + path, json, 8000);
                    Dictionary<string, object> d =
                        new JavaScriptSerializer().Deserialize<Dictionary<string, object>>(text);
                    int code = d.ContainsKey("code") ? Convert.ToInt32(d["code"]) : 1;
                    if (code != 0)
                    {
                        error = d.ContainsKey("msg") ? Convert.ToString(d["msg"]) : "请求失败";
                    }
                    else
                    {
                        token = Convert.ToString(d["token"]);
                        display = d.ContainsKey("display") ? Convert.ToString(d["display"]) : user;
                    }
                }
                catch (Exception ex)
                {
                    error = "连接服务端失败：" + ex.Message;
                }

                BeginInvoke(new Action(delegate
                {
                    _submit.Enabled = true;
                    _switch.Enabled = true;
                    if (error != null)
                    {
                        ShowStatus(error);
                        return;
                    }
                    ServerAddress = server;
                    SessionToken = token;
                    LoginUser = user;
                    DisplayName = display;
                    SaveLogin();
                    DialogResult = DialogResult.OK;
                    Close();
                }));
            });
        }

        private void ShowStatus(string text)
        {
            ShowStatus(text, Theme.Red);
        }

        private void ShowStatus(string text, Color color)
        {
            _status.Text = text;
            _status.ForeColor = color;
        }

        public static string Normalize(string server)
        {
            string s = (server ?? "").Trim();
            if (s.Length == 0) s = "127.0.0.1:18080";
            if (!s.StartsWith("http://", StringComparison.OrdinalIgnoreCase) &&
                !s.StartsWith("https://", StringComparison.OrdinalIgnoreCase))
                s = "http://" + s;
            while (s.EndsWith("/")) s = s.Substring(0, s.Length - 1);
            return s;
        }
    }

    /// <summary>添加自己的硬件：标准设备填地址；客户自定义硬件可只填名称，密钥由服务端生成。</summary>
    class DeviceDialog : Form
    {
        private readonly TextBox _name;
        private readonly TextBox _address;
        private readonly TextBox _key;
        private readonly CheckBox _custom;
        private readonly Label _status;

        public string DeviceName { get; private set; }
        public string DeviceAddress { get; private set; }
        public string DeviceKey { get; private set; }
        public bool Custom { get; private set; }
        public string DeviceRef { get; private set; }
        public string ServerKey { get; private set; }

        public DeviceDialog()
        {
            Text = "添加我的硬件";
            ClientSize = new Size(440, 380);
            FormBorderStyle = FormBorderStyle.FixedDialog;
            MaximizeBox = false;
            MinimizeBox = false;
            StartPosition = FormStartPosition.CenterParent;
            BackColor = Theme.Bg;
            ForeColor = Theme.Text;
            Font = new Font("Microsoft YaHei UI", 9.5f);
            AutoScaleMode = AutoScaleMode.None;

            Controls.Add(Ui.Lbl("添加我的硬件", 28, 20, 360, 32, 16f, true, Theme.Text));
            Controls.Add(Ui.Lbl("设备会登记到当前登录账号，其他账号不可见。", 30, 54, 380, 22, 8.5f, false, Theme.Muted));

            Controls.Add(Ui.Lbl("设备名称", 30, 88, 200, 22, 9f, false, Theme.Muted));
            _name = Box(30, 110, 378);
            Controls.Add(_name);

            Controls.Add(Ui.Lbl("设备地址（标准硬件填写，例如 192.168.1.66:80）", 30, 150, 380, 22, 9f, false, Theme.Muted));
            _address = Box(30, 172, 378);
            Controls.Add(_address);

            Controls.Add(Ui.Lbl("设备密钥（客户自定义硬件填写，留空自动生成）", 30, 212, 380, 22, 9f, false, Theme.Muted));
            _key = Box(30, 234, 378);
            Controls.Add(_key);

            _custom = new CheckBox();
            _custom.Text = "客户自定义硬件：数据由硬件主动上报到服务端";
            _custom.Location = new Point(30, 274);
            _custom.Size = new Size(380, 24);
            _custom.ForeColor = Theme.Text;
            _custom.BackColor = Color.Transparent;
            Controls.Add(_custom);

            UiButton ok = new UiButton("添加", Theme.Accent);
            ok.Location = new Point(30, 310);
            ok.Size = new Size(180, 40);
            ok.Click += delegate { Submit(); };
            Controls.Add(ok);

            UiButton cancel = new UiButton("取消", Theme.Card);
            cancel.Location = new Point(228, 310);
            cancel.Size = new Size(180, 40);
            cancel.DialogResult = DialogResult.Cancel;
            Controls.Add(cancel);

            _status = Ui.Lbl("", 30, 354, 380, 20, 8.5f, false, Theme.Red);
            Controls.Add(_status);
            AcceptButton = ok;
        }

        private TextBox Box(int x, int y, int w)
        {
            TextBox t = new TextBox();
            t.Location = new Point(x, y);
            t.Size = new Size(w, 28);
            t.BackColor = Theme.Input;
            t.ForeColor = Theme.Text;
            t.BorderStyle = BorderStyle.FixedSingle;
            t.Font = new Font("Microsoft YaHei UI", 10f);
            return t;
        }

        private void Submit()
        {
            string name = _name.Text.Trim();
            string address = _address.Text.Trim();
            bool custom = _custom.Checked || address.Length == 0;
            if (address.Length == 0 && !custom)
            {
                _status.Text = "请填写设备地址，或勾选客户自定义硬件";
                return;
            }

            Dictionary<string, object> body = new Dictionary<string, object>();
            body["name"] = name.Length == 0 ? (address.Length == 0 ? "我的硬件" : address) : name;
            body["address"] = address;
            body["key"] = _key.Text.Trim();
            body["custom"] = custom ? "1" : "0";
            string json = new JavaScriptSerializer().Serialize(body);

            try
            {
                string text = Http.Post(LoginForm.Normalize(ServerAddress()) + "/account/devices", json, 8000);
                Dictionary<string, object> d =
                    new JavaScriptSerializer().Deserialize<Dictionary<string, object>>(text);
                int code = Convert.ToInt32(d["code"]);
                if (code != 0)
                {
                    _status.Text = d.ContainsKey("msg") ? Convert.ToString(d["msg"]) : "添加失败";
                    return;
                }
                Dictionary<string, object> dev = (Dictionary<string, object>)d["device"];
                DeviceName = Convert.ToString(dev["name"]);
                DeviceAddress = Convert.ToString(dev["address"]);
                DeviceKey = Convert.ToString(dev["key"]);
                DeviceRef = Convert.ToString(dev["ref"]);
                Custom = Convert.ToBoolean(dev["custom"]);
                ServerKey = DeviceKey;
                DialogResult = DialogResult.OK;
                Close();
            }
            catch (Exception ex)
            {
                _status.Text = "添加失败：" + ex.Message;
            }
        }

        public Func<string> ServerAddress;
    }
}
