using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Drawing;
using System.Globalization;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using System.Windows.Forms;

namespace ScarecrowServer
{
    static class Program
    {
        [STAThread]
        static void Main(string[] args)
        {
            bool headless = args != null && args.Length > 0
                && string.Equals(args[0], "--headless", StringComparison.OrdinalIgnoreCase);

            if (headless)
            {
                int port = 0;
                if (args.Length > 1) int.TryParse(args[1], out port);
                ServerForm form = new ServerForm();
                if (!form.StartHeadless(port))
                {
                    Environment.Exit(1);
                }
                Console.WriteLine("ScarecrowServer v3.21.5 headless, developer 胡宇宸, 2026-11-21");
                Console.WriteLine("按下 Ctrl+C 或关闭窗口结束服务。");
                while (true) System.Threading.Thread.Sleep(1000);
            }

            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new ServerForm());
        }
    }

    static class Theme
    {
        public static readonly Color Bg = Color.FromArgb(11, 18, 32);
        public static readonly Color Card = Color.FromArgb(22, 35, 58);
        public static readonly Color CardEdge = Color.FromArgb(40, 62, 94);
        public static readonly Color Card2 = Color.FromArgb(34, 55, 83);
        public static readonly Color Input = Color.FromArgb(15, 27, 46);
        public static readonly Color Text = Color.FromArgb(229, 237, 247);
        public static readonly Color Muted = Color.FromArgb(147, 164, 188);
        public static readonly Color Accent = Color.FromArgb(14, 165, 233);
        public static readonly Color Green = Color.FromArgb(52, 211, 153);
        public static readonly Color Red = Color.FromArgb(220, 38, 38);
        public static readonly Color Amber = Color.FromArgb(245, 158, 11);
        public static readonly Color Line = Color.FromArgb(42, 59, 87);

        public static readonly Font H1 = new Font("Microsoft YaHei UI", 20f, FontStyle.Bold);
        public static readonly Font H2 = new Font("Microsoft YaHei UI", 12.5f, FontStyle.Bold);
        public static readonly Font Body = new Font("Microsoft YaHei UI", 9.5f);
        public static readonly Font Small = new Font("Microsoft YaHei UI", 8.5f);
    }

    class CardPanel : Panel
    {
        public CardPanel()
        {
            DoubleBuffered = true;
            BackColor = Theme.Card;
            Padding = new Padding(18, 14, 18, 14);
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            base.OnPaint(e);
            using (Pen p = new Pen(Theme.CardEdge))
            {
                e.Graphics.DrawRectangle(p, 0, 0, Width - 1, Height - 1);
            }
        }
    }

    class UiButton : Button
    {
        private Color _bg;

        public UiButton(string text, Color bg)
        {
            Text = text;
            _bg = bg;
            FlatStyle = FlatStyle.Flat;
            FlatAppearance.BorderSize = 0;
            BackColor = bg;
            ForeColor = Color.White;
            Font = new Font("Microsoft YaHei UI", 9.5f, FontStyle.Bold);
            Cursor = Cursors.Hand;
            UseVisualStyleBackColor = false;
        }

        public void SetColor(Color c)
        {
            _bg = c;
            BackColor = c;
        }

        protected override void OnMouseEnter(EventArgs e)
        {
            base.OnMouseEnter(e);
            BackColor = ControlPaint.Light(_bg, 0.15f);
        }

        protected override void OnMouseLeave(EventArgs e)
        {
            base.OnMouseLeave(e);
            BackColor = _bg;
        }
    }

    class Device
    {
        public string Name = "";
        public string Address = "";
        public bool Current;

        public override string ToString()
        {
            return (Current ? "★ " : "   ") + Name + "   " + Address;
        }
    }

    static class Store
    {
        public static string FilePath =
            Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "server.cfg");

        public static string Load()
        {
            if (!File.Exists(FilePath)) return null;
            try { return File.ReadAllText(FilePath, Encoding.UTF8); }
            catch { return null; }
        }

        public static void Save(string text)
        {
            try { File.WriteAllText(FilePath, text, new UTF8Encoding(false)); }
            catch { }
        }
    }

    /// <summary>一个客户端独占的转发通道：设备地址、请求量与最近活动互不影响。</summary>
    class ClientChannel
    {
        public string Key;
        public string DeviceAddress = "";
        public long Requests;
        public long Bytes;
        public DateTime LastSeen = DateTime.Now;
        public string LastError = "";
    }

    /// <summary>
    /// 极简 TCP 代理：每个客户端一条独立转发通道，按 X-Device-Address 或通道首次绑定的设备转发，
    /// 并把设备响应原样回写到客户端（MJPEG 流同样适用）。
    /// </summary>
    class ProxyServer
    {
        private TcpListener _listener;
        private Thread _accept;
        private volatile bool _running;
        private readonly ConcurrentDictionary<string, ClientChannel> _channels =
            new ConcurrentDictionary<string, ClientChannel>();

        public int Port;
        public int Requests;
        public string LastError = "";
        public Action<string> Log;
        public Func<string, Device> ResolveDevice;
        public Func<string> ActiveAddress;

        public bool Running { get { return _running; } }

        public int ChannelCount { get { return _channels.Count; } }

        public List<ClientChannel> SnapshotChannels()
        {
            List<ClientChannel> list = new List<ClientChannel>(_channels.Values);
            list.Sort(delegate(ClientChannel a, ClientChannel b)
            {
                return b.LastSeen.CompareTo(a.LastSeen);
            });
            return list;
        }

        private ClientChannel GetChannel(string clientId, IPEndPoint remote)
        {
            string key = clientId;
            if (string.IsNullOrEmpty(key))
                key = remote == null ? "unknown" : "ip:" + remote.Address;
            if (key.Length > 80) key = key.Substring(0, 80);

            ClientChannel channel = _channels.GetOrAdd(key, delegate(string k)
            {
                ClientChannel ch = new ClientChannel();
                ch.Key = k;
                return ch;
            });
            channel.LastSeen = DateTime.Now;
            return channel;
        }

        public void Start(int port)
        {
            if (_running) return;
            Port = port;
            _listener = new TcpListener(IPAddress.Any, port);
            _listener.Start();
            _running = true;
            _accept = new Thread(AcceptLoop);
            _accept.IsBackground = true;
            _accept.Start();
        }

        public void Stop()
        {
            _running = false;
            try { if (_listener != null) _listener.Stop(); } catch { }
            _listener = null;
        }

        private void AcceptLoop()
        {
            while (_running)
            {
                TcpClient client = null;
                try
                {
                    client = _listener.AcceptTcpClient();
                }
                catch
                {
                    if (!_running) break;
                    Thread.Sleep(60);
                    continue;
                }
                ThreadPool.QueueUserWorkItem(delegate { Handle(client); });
            }
        }

        private void Handle(TcpClient client)
        {
            using (client)
            {
                try
                {
                    client.NoDelay = true;
                    NetworkStream cs = client.GetStream();
                    cs.ReadTimeout = 15000;

                    string method, path, version;
                    Dictionary<string, string> headers;
                    byte[] body;
                    if (!ReadRequest(cs, out method, out path, out version, out headers, out body))
                        return;

                    string pathOnly = path;
                    int q = pathOnly.IndexOf('?');
                    if (q >= 0) pathOnly = pathOnly.Substring(0, q);

                    string clientId;
                    headers.TryGetValue("x-client-id", out clientId);
                    IPEndPoint remote = null;
                    try { remote = client.Client.RemoteEndPoint as IPEndPoint; }
                    catch { }

                    if (method == "GET" && (pathOnly == "/" || pathOnly == "/index.html"))
                    {
                        WriteHtml(cs, Dashboard());
                        return;
                    }
                    if (method == "GET" && pathOnly == "/server/health")
                    {
                        string json = "{\"ok\":true,\"version\":\"3.21.5\",\"port\":" + Port
                            + ",\"requests\":" + Requests
                            + ",\"channels\":" + ChannelCount
                            + ",\"active\":\"" + JsonEscape(ActiveAddress == null ? "" : (ActiveAddress() ?? "")) + "\"}";
                        WriteText(cs, "200 OK", "application/json; charset=utf-8", json);
                        return;
                    }
                    if (method == "GET" && pathOnly == "/server/channels")
                    {
                        StringBuilder cj = new StringBuilder();
                        cj.Append("{\"code\":0,\"count\":").Append(ChannelCount).Append(",\"channels\":[");
                        List<ClientChannel> snapshot = SnapshotChannels();
                        for (int i = 0; i < snapshot.Count; i++)
                        {
                            ClientChannel ch = snapshot[i];
                            if (i > 0) cj.Append(',');
                            cj.Append("{\"id\":\"").Append(JsonEscape(ch.Key)).Append("\"")
                              .Append(",\"device\":\"").Append(JsonEscape(ch.DeviceAddress)).Append("\"")
                              .Append(",\"requests\":").Append(ch.Requests)
                              .Append(",\"bytes\":").Append(ch.Bytes)
                              .Append(",\"last_seen\":\"").Append(ch.LastSeen.ToString("yyyy-MM-dd HH:mm:ss")).Append("\"}");
                        }
                        cj.Append("]}");
                        WriteText(cs, "200 OK", "application/json; charset=utf-8", cj.ToString());
                        return;
                    }

                    ClientChannel channel = GetChannel(clientId, remote);

                    string wanted = null;
                    string hv;
                    if (headers.TryGetValue("x-device-address", out hv)) wanted = hv;

                    string address = null;
                    if (!string.IsNullOrEmpty(wanted))
                    {
                        if (ResolveDevice != null)
                        {
                            Device d = ResolveDevice(wanted);
                            if (d != null) address = d.Address;
                        }
                        if (string.IsNullOrEmpty(address)) address = wanted;
                        channel.DeviceAddress = address;
                    }
                    else if (!string.IsNullOrEmpty(channel.DeviceAddress))
                    {
                        // 通道已绑定设备：后续请求固定走该设备，不受其他客户端或全局“当前设备”影响。
                        address = channel.DeviceAddress;
                    }
                    if (string.IsNullOrEmpty(address) && ActiveAddress != null)
                    {
                        address = ActiveAddress();
                        channel.DeviceAddress = address;
                    }

                    string host;
                    int port;
                    if (!ParseAddress(address, out host, out port))
                    {
                        WriteText(cs, "400 Bad Request", "text/plain; charset=utf-8",
                            "未绑定设备。请在服务端【设备绑定】中添加设备，或在 App 中填写设备地址。");
                        return;
                    }

                    Interlocked.Increment(ref Requests);
                    Interlocked.Increment(ref channel.Requests);

                    using (TcpClient device = new TcpClient())
                    {
                        device.NoDelay = true;
                        if (!Connect(device, host, port, 5000))
                        {
                            channel.LastError = "设备连接失败 " + host + ":" + port;
                            WriteText(cs, "502 Bad Gateway", "text/plain; charset=utf-8",
                                "连接设备失败：" + host + ":" + port);
                            if (Log != null) Log("设备连接失败 " + host + ":" + port);
                            return;
                        }

                        NetworkStream ds = device.GetStream();
                        ds.ReadTimeout = Timeout.Infinite;
                        ds.WriteTimeout = 15000;

                        StringBuilder sb = new StringBuilder();
                        sb.Append(method).Append(' ').Append(path).Append(' ').Append(version).Append("\r\n");
                        foreach (KeyValuePair<string, string> kv in headers)
                        {
                            string k = kv.Key;
                            if (k == "host" || k == "connection" || k == "keep-alive" ||
                                k == "proxy-connection" || k == "x-device-address" ||
                                k == "x-client-id" ||
                                k == "upgrade" || k == "te" || k == "trailer")
                                continue;
                            sb.Append(kv.Key).Append(": ").Append(kv.Value).Append("\r\n");
                        }
                        sb.Append("Host: ").Append(host).Append(':').Append(port).Append("\r\n");
                        sb.Append("Connection: close\r\n\r\n");

                        byte[] outHead = Encoding.UTF8.GetBytes(sb.ToString());
                        ds.Write(outHead, 0, outHead.Length);
                        if (body != null && body.Length > 0) ds.Write(body, 0, body.Length);
                        ds.Flush();

                        cs.WriteTimeout = Timeout.Infinite;
                        byte[] buf = new byte[32768];
                        while (true)
                        {
                            int n;
                            try { n = ds.Read(buf, 0, buf.Length); }
                            catch { break; }
                            if (n <= 0) break;
                            Interlocked.Add(ref channel.Bytes, n);
                            cs.Write(buf, 0, n);
                            cs.Flush();
                        }
                    }
                }
                catch (Exception ex)
                {
                    LastError = ex.Message;
                    if (Log != null) Log("代理异常：" + ex.Message);
                }
            }
        }

        private static bool Connect(TcpClient c, string host, int port, int timeoutMs)
        {
            try
            {
                IAsyncResult ar = c.BeginConnect(host, port, null, null);
                if (!ar.AsyncWaitHandle.WaitOne(timeoutMs))
                {
                    try { c.Close(); } catch { }
                    return false;
                }
                c.EndConnect(ar);
                return true;
            }
            catch
            {
                return false;
            }
        }

        private static bool ParseAddress(string address, out string host, out int port)
        {
            host = null;
            port = 80;
            if (address == null) return false;
            string s = address.Trim();
            if (s.Length == 0) return false;
            if (s.StartsWith("http://", StringComparison.OrdinalIgnoreCase))
                s = s.Substring(7);
            if (s.StartsWith("https://", StringComparison.OrdinalIgnoreCase))
                s = s.Substring(8);
            int slash = s.IndexOf('/');
            if (slash >= 0) s = s.Substring(0, slash);
            int colon = s.LastIndexOf(':');
            if (colon > 0)
            {
                int p;
                if (int.TryParse(s.Substring(colon + 1), out p) && p > 0 && p < 65536)
                {
                    port = p;
                    s = s.Substring(0, colon);
                }
            }
            host = s.Trim();
            return host.Length > 0;
        }

        private static bool ReadRequest(NetworkStream s, out string method, out string path,
            out string version, out Dictionary<string, string> headers, out byte[] body)
        {
            method = ""; path = ""; version = "HTTP/1.1";
            headers = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            body = new byte[0];

            MemoryStream ms = new MemoryStream();
            int state = 0;
            byte[] one = new byte[1];
            while (ms.Length < 131072)
            {
                int n = s.Read(one, 0, 1);
                if (n <= 0) return false;
                ms.WriteByte(one[0]);
                if (one[0] == 13)
                {
                    if (state == 0 || state == 2) state++;
                }
                else if (one[0] == 10)
                {
                    if (state == 1) state = 2;
                    else if (state == 3) { state = 4; break; }
                    else state = 0;
                }
                else state = 0;
            }

            string text = Encoding.UTF8.GetString(ms.ToArray());
            string[] lines = text.Split(new string[] { "\r\n" }, StringSplitOptions.None);
            if (lines.Length == 0) return false;

            string[] first = lines[0].Split(' ');
            if (first.Length >= 2)
            {
                method = first[0].ToUpperInvariant();
                path = first[1];
                if (first.Length >= 3) version = first[2];
            }
            else return false;

            for (int i = 1; i < lines.Length; i++)
            {
                string line = lines[i];
                if (line.Length == 0) continue;
                int c = line.IndexOf(':');
                if (c <= 0) continue;
                headers[line.Substring(0, c).Trim()] = line.Substring(c + 1).Trim();
            }

            int len = 0;
            string cl;
            if (headers.TryGetValue("content-length", out cl))
                int.TryParse(cl, out len);
            if (len > 0 && len <= 32 * 1024 * 1024)
            {
                body = new byte[len];
                int got = 0;
                while (got < len)
                {
                    int n = s.Read(body, got, len - got);
                    if (n <= 0) break;
                    got += n;
                }
                if (got < len) Array.Resize(ref body, got);
            }
            return true;
        }

        private static void WriteText(NetworkStream s, string status, string contentType, string text)
        {
            byte[] data = Encoding.UTF8.GetBytes(text ?? "");
            StringBuilder sb = new StringBuilder();
            sb.Append("HTTP/1.1 ").Append(status).Append("\r\n");
            sb.Append("Content-Type: ").Append(contentType).Append("\r\n");
            sb.Append("Content-Length: ").Append(data.Length).Append("\r\n");
            sb.Append("Cache-Control: no-store\r\n");
            sb.Append("Connection: close\r\n\r\n");
            byte[] head = Encoding.UTF8.GetBytes(sb.ToString());
            try
            {
                s.Write(head, 0, head.Length);
                s.Write(data, 0, data.Length);
                s.Flush();
            }
            catch { }
        }

        private static void WriteHtml(NetworkStream s, string html)
        {
            WriteText(s, "200 OK", "text/html; charset=utf-8", html);
        }

        private string Dashboard()
        {
            StringBuilder sb = new StringBuilder();
            sb.Append("<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">");
            sb.Append("<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">");
            sb.Append("<title>稻草人驱鸟控制器 · 转发服务</title><style>");
            sb.Append("body{margin:0;background:#0b1220;color:#e5edf7;font-family:'Microsoft YaHei UI',sans-serif}");
            sb.Append(".wrap{max-width:820px;margin:0 auto;padding:28px 20px}");
            sb.Append("h1{font-size:24px;margin:0 0 6px}p.sub{color:#93a4bc;margin:0 0 20px}");
            sb.Append(".card{background:#16233a;border:1px solid #283e5e;border-radius:14px;padding:18px;margin-bottom:14px}");
            sb.Append(".row{display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px dashed #2a3b57}");
            sb.Append(".row:last-child{border-bottom:0}.k{color:#93a4bc}.v{font-weight:bold}");
            sb.Append(".on{color:#34d399}.off{color:#f59e0b}.mono{font-family:Consolas,monospace}");
            sb.Append("</style></head><body><div class=\"wrap\">");
            sb.Append("<h1>稻草人驱鸟控制器 · 转发服务</h1>");
            sb.Append("<p class=\"sub\">Windows 11 转发节点  ·  v3.21.5  ·  开发者 胡宇宸  ·  2026-11-21</p>");

            sb.Append("<div class=\"card\"><div class=\"row\"><span class=\"k\">运行状态</span><span class=\"v ");
            sb.Append(_running ? "on\">运行中" : "off\">已停止");
            sb.Append("</span></div>");
            sb.Append("<div class=\"row\"><span class=\"k\">监听端口</span><span class=\"v mono\">");
            sb.Append(Port).Append("</span></div>");
            sb.Append("<div class=\"row\"><span class=\"k\">已转发请求</span><span class=\"v\">");
            sb.Append(Requests).Append("</span></div>");
            sb.Append("<div class=\"row\"><span class=\"k\">独立转发通道</span><span class=\"v\">");
            sb.Append(ChannelCount).Append("</span></div>");
            sb.Append("<div class=\"row\"><span class=\"k\">当前设备</span><span class=\"v mono\">");
            string active = ActiveAddress == null ? "" : (ActiveAddress() ?? "");
            sb.Append(Html(active.Length == 0 ? "未绑定" : active));
            sb.Append("</span></div></div>");

            sb.Append("<div class=\"card\"><div class=\"row\"><span class=\"k\" style=\"font-weight:bold;color:#e5edf7\">设备名称</span>");
            sb.Append("<span class=\"k\" style=\"font-weight:bold\">设备地址</span></div>");
            List<Device> list = DeviceList;
            if (list != null && list.Count > 0)
            {
                foreach (Device d in list)
                {
                    sb.Append("<div class=\"row\"><span class=\"v\">");
                    sb.Append(d.Current ? "★ " : "");
                    sb.Append(Html(d.Name));
                    sb.Append("</span><span class=\"v mono\">").Append(Html(d.Address)).Append("</span></div>");
                }
            }
            else
            {
                sb.Append("<div class=\"row\"><span class=\"k\">暂无绑定设备</span></div>");
            }
            sb.Append("</div>");
            sb.Append("<div class=\"card\"><div class=\"row\"><span class=\"k\" style=\"font-weight:bold;color:#e5edf7\">客户端通道</span>");
            sb.Append("<span class=\"k\" style=\"font-weight:bold\">转发设备 / 请求数</span></div>");
            List<ClientChannel> channels = SnapshotChannels();
            if (channels.Count > 0)
            {
                foreach (ClientChannel ch in channels)
                {
                    string id = ch.Key.Length > 18 ? ch.Key.Substring(0, 18) + "…" : ch.Key;
                    sb.Append("<div class=\"row\"><span class=\"v mono\">").Append(Html(id)).Append("</span>");
                    sb.Append("<span class=\"v mono\">").Append(Html(ch.DeviceAddress.Length == 0 ? "--" : ch.DeviceAddress));
                    sb.Append(" · ").Append(ch.Requests).Append("</span></div>");
                }
            }
            else
            {
                sb.Append("<div class=\"row\"><span class=\"k\">暂无客户端接入</span></div>");
            }
            sb.Append("</div>");
            sb.Append("<div class=\"card\"><div class=\"row\"><span class=\"k\">设备 API</span>");
            sb.Append("<span class=\"v mono\">http://本机IP:");
            sb.Append(Port).Append("/api/status</span></div>");
            sb.Append("<div class=\"row\"><span class=\"k\">健康检查</span>");
            sb.Append("<span class=\"v mono\">/server/health</span></div></div>");
            sb.Append("</div></body></html>");
            return sb.ToString();
        }

        public List<Device> DeviceList;

        private static string Html(string s)
        {
            if (s == null) return "";
            return s.Replace("&", "&amp;").Replace("<", "&lt;").Replace(">", "&gt;")
                .Replace("\"", "&quot;");
        }

        private static string JsonEscape(string s)
        {
            if (s == null) return "";
            return s.Replace("\\", "\\\\").Replace("\"", "\\\"");
        }
    }

    class ServerForm : Form
    {
        private const string AppVersion = "3.21.5";

        private readonly List<Device> _devices = new List<Device>();
        private readonly ProxyServer _proxy = new ProxyServer();

        private Panel _pageService, _pageBind, _pageAbout;
        private Panel _navBar;
        private readonly List<UiButton> _nav = new List<UiButton>();

        private TextBox _port;
        private UiButton _toggle;
        private Label _statusLabel;
        private Label _activeLabel;
        private Label _requestLabel;
        private TextBox _log;

        private ListBox _deviceList;
        private TextBox _name;
        private TextBox _address;
        private Label _bindHint;

        private System.Windows.Forms.Timer _uiTimer;

        public ServerForm()
        {
            Text = "稻草人驱鸟控制器 · 转发服务 v" + AppVersion + " - Windows 11";
            StartPosition = FormStartPosition.CenterScreen;
            ClientSize = new Size(1000, 800);
            FormBorderStyle = FormBorderStyle.FixedSingle;
            MaximizeBox = false;
            MinimumSize = new Size(900, 720);
            BackColor = Theme.Bg;
            ForeColor = Theme.Text;
            Font = Theme.Body;
            DoubleBuffered = true;
            AutoScaleMode = AutoScaleMode.None;

            _proxy.Log = Log;
            _proxy.ResolveDevice = FindDevice;
            _proxy.ActiveAddress = delegate { return ActiveDeviceAddress(); };
            _proxy.DeviceList = _devices;

            LoadConfig();

            BuildHeader();
            BuildBottomNav();
            BuildServicePage();
            BuildBindPage();
            BuildAboutPage();
            ApplyDpiScale();
            RefreshDeviceList();

            _uiTimer = new System.Windows.Forms.Timer();
            _uiTimer.Interval = 800;
            _uiTimer.Tick += delegate { TickUi(); };
            _uiTimer.Start();

            FormClosing += delegate
            {
                _uiTimer.Stop();
                _proxy.Stop();
                SaveConfig();
            };

            Log("服务端已就绪，版本 " + AppVersion + "，开发者 胡宇宸，2026-11-21");
        }

        /// <summary>无界面模式：按配置绑定并启动转发，用于服务器常驻运行。</summary>
        public bool StartHeadless(int portOverride)
        {
            int port = portOverride > 0 ? portOverride : (_proxy.Port > 0 ? _proxy.Port : 1819);
            _proxy.Log = delegate(string m)
            {
                Console.WriteLine(DateTime.Now.ToString("HH:mm:ss") + "  " + m);
            };
            try
            {
                _proxy.Start(port);
            }
            catch (Exception ex)
            {
                Console.WriteLine("启动失败：" + ex.Message);
                return false;
            }
            Console.WriteLine("监听 0.0.0.0:" + port);
            string active = ActiveDeviceAddress();
            Console.WriteLine("当前设备：" + (active.Length == 0 ? "(未绑定)" : active));
            return true;
        }

        private void ApplyDpiScale()
        {
            // 固定 1000×800 逻辑布局，交给系统 DPI 缩放，避免控件尺寸与窗体尺寸不一致。
            if (_navBar != null) _navBar.BringToFront();
            _pageService.BringToFront();
            _pageBind.BringToFront();
            _pageAbout.BringToFront();
            if (_navBar != null) _navBar.BringToFront();
            ShowPage(0);
        }

        // ---------------------------------------------------------- 配置

        private void LoadConfig()
        {
            string text = Store.Load();
            int port = 1819;
            if (!string.IsNullOrEmpty(text))
            {
                string[] lines = text.Split('\n');
                foreach (string raw in lines)
                {
                    string line = raw.Trim();
                    if (line.Length == 0) continue;
                    int eq = line.IndexOf('=');
                    if (eq <= 0) continue;
                    string key = line.Substring(0, eq).Trim();
                    string val = line.Substring(eq + 1).Trim();
                    if (key == "port")
                    {
                        int p;
                        if (int.TryParse(val, out p) && p > 0 && p < 65536) port = p;
                    }
                    else if (key == "device")
                    {
                        string[] parts = val.Split('|');
                        if (parts.Length >= 2)
                        {
                            Device d = new Device();
                            d.Name = parts[0].Trim();
                            d.Address = parts[1].Trim();
                            d.Current = parts.Length >= 3 && parts[2].Trim() == "1";
                            if (d.Name.Length == 0) d.Name = d.Address;
                            if (d.Address.Length > 0) _devices.Add(d);
                        }
                    }
                }
            }

            if (_devices.Count == 0)
            {
                Device d = new Device();
                d.Name = "默认设备";
                d.Address = "192.168.4.1:80";
                d.Current = true;
                _devices.Add(d);
            }
            else if (ActiveDeviceAddress().Length == 0)
            {
                _devices[0].Current = true;
            }

            _proxy.Port = port;
        }

        private void SaveConfig()
        {
            StringBuilder sb = new StringBuilder();
            int port;
            if (_port != null && int.TryParse(_port.Text.Trim(), out port)) { }
            else port = _proxy.Port > 0 ? _proxy.Port : 1819;
            sb.Append("port=").Append(port).Append('\n');
            foreach (Device d in _devices)
            {
                sb.Append("device=").Append(d.Name).Append('|').Append(d.Address)
                    .Append('|').Append(d.Current ? "1" : "0").Append('\n');
            }
            Store.Save(sb.ToString());
        }

        private string ActiveDeviceAddress()
        {
            foreach (Device d in _devices)
                if (d.Current) return d.Address;
            return "";
        }

        private Device FindDevice(string key)
        {
            if (string.IsNullOrEmpty(key)) return null;
            string k = key.Trim();
            foreach (Device d in _devices)
            {
                if (string.Equals(d.Name, k, StringComparison.OrdinalIgnoreCase)) return d;
                if (string.Equals(d.Address, k, StringComparison.OrdinalIgnoreCase)) return d;
            }
            return null;
        }

        // ---------------------------------------------------------- 界面

        private void BuildHeader()
        {
            Label title = new Label();
            title.Text = "稻草人驱鸟控制器 · 转发服务";
            title.Font = Theme.H1;
            title.ForeColor = Theme.Text;
            title.AutoSize = true;
            title.Location = new Point(20, 14);
            Controls.Add(title);

            Label sub = new Label();
            sub.Text = "Windows 11 转发节点  ·  v" + AppVersion + "  ·  硬件数据经本机转发到手机";
            sub.Font = Theme.Small;
            sub.ForeColor = Theme.Muted;
            sub.AutoSize = true;
            sub.Location = new Point(22, 52);
            Controls.Add(sub);
        }

        private void BuildBottomNav()
        {
            Panel bar = new Panel();
            _navBar = bar;
            bar.Dock = DockStyle.Bottom;
            bar.Height = 64;
            bar.BackColor = Theme.Card;
            bar.Paint += delegate(object s, PaintEventArgs e)
            {
                using (Pen p = new Pen(Theme.CardEdge))
                    e.Graphics.DrawLine(p, 0, 0, bar.Width, 0);
            };

            string[] names = { "服务控制", "设备绑定", "开发警示" };
            for (int i = 0; i < names.Length; i++)
            {
                int idx = i;
                UiButton b = new UiButton(names[i], i == 0 ? Theme.Accent : Theme.Card2);
                b.Size = new Size(156, 44);
                b.Location = new Point(16 + i * 168, 10);
                b.Click += delegate { ShowPage(idx); };
                bar.Controls.Add(b);
                _nav.Add(b);
            }

            Label hint = new Label();
            hint.Text = "设备侧数据 → 本机转发 → 手机 App";
            hint.Font = Theme.Small;
            hint.ForeColor = Theme.Muted;
            hint.AutoSize = true;
            hint.Location = new Point(620, 24);
            bar.Controls.Add(hint);

            Controls.Add(bar);
        }

        private void ShowPage(int index)
        {
            _pageService.Visible = index == 0;
            _pageBind.Visible = index == 1;
            _pageAbout.Visible = index == 2;
            for (int i = 0; i < _nav.Count; i++)
                _nav[i].SetColor(i == index ? Theme.Accent : Theme.Card2);
        }

        private CardPanel NewCard(Panel host, int y, int h, string title)
        {
            CardPanel card = new CardPanel();
            card.Location = new Point(16, y);
            card.Size = new Size(968, h);
            host.Controls.Add(card);

            if (title != null)
            {
                Label t = new Label();
                t.Text = title;
                t.Font = Theme.H2;
                t.ForeColor = Theme.Text;
                t.AutoSize = true;
                t.Location = new Point(18, 12);
                card.Controls.Add(t);
            }
            return card;
        }

        private static Label TextLabel(string text, Font font, Color color, Point at)
        {
            Label l = new Label();
            l.Text = text;
            l.Font = font;
            l.ForeColor = color;
            l.AutoSize = true;
            l.Location = at;
            l.BackColor = Color.Transparent;
            return l;
        }

        private static TextBox Input(string value, Point at, int width)
        {
            TextBox t = new TextBox();
            t.Text = value;
            t.Font = new Font("Microsoft YaHei UI", 10f);
            t.BackColor = Theme.Input;
            t.ForeColor = Theme.Text;
            t.BorderStyle = BorderStyle.FixedSingle;
            t.Location = at;
            t.Width = width;
            return t;
        }

        private void BuildServicePage()
        {
            _pageService = new Panel();
            _pageService.Location = new Point(0, 84);
            _pageService.Size = new Size(1000, 652);
            _pageService.BackColor = Theme.Bg;
            _pageService.AutoScroll = true;
            Controls.Add(_pageService);

            CardPanel listen = NewCard(_pageService, 12, 170, "监听设置");
            listen.Controls.Add(TextLabel("监听端口", Theme.Body, Theme.Muted, new Point(18, 52)));
            _port = Input(_proxy.Port > 0 ? _proxy.Port.ToString() : "1819", new Point(18, 76), 140);
            listen.Controls.Add(_port);

            _toggle = new UiButton("启动服务", Theme.Green);
            _toggle.Size = new Size(140, 44);
            _toggle.Location = new Point(178, 72);
            _toggle.Click += delegate { ToggleServer(); };
            listen.Controls.Add(_toggle);

            _statusLabel = TextLabel("● 已停止", Theme.Body, Theme.Red, new Point(340, 82));
            listen.Controls.Add(_statusLabel);

            listen.Controls.Add(TextLabel(
                "手机 App 填写本机 IP 与该端口即可访问；设备需与本机在同一可达网络。",
                Theme.Small, Theme.Muted, new Point(18, 128)));

            CardPanel info = NewCard(_pageService, 194, 130, "当前转发");
            _activeLabel = TextLabel("当前设备：--", Theme.Body, Theme.Text, new Point(18, 52));
            info.Controls.Add(_activeLabel);
            _requestLabel = TextLabel("已转发请求：0", Theme.Body, Theme.Muted, new Point(18, 80));
            info.Controls.Add(_requestLabel);
            info.Controls.Add(TextLabel(
                "每个客户端按 X-Client-Id（缺省用客户端 IP）建立独立通道，首次绑定的设备互不影响。",
                Theme.Small, Theme.Muted, new Point(18, 104)));

            CardPanel logCard = NewCard(_pageService, 336, 210, "运行日志");
            _log = new TextBox();
            _log.Multiline = true;
            _log.ReadOnly = true;
            _log.ScrollBars = ScrollBars.Vertical;
            _log.BackColor = Theme.Input;
            _log.ForeColor = Theme.Muted;
            _log.BorderStyle = BorderStyle.None;
            _log.Font = new Font("Consolas", 9f);
            _log.Location = new Point(18, 42);
            _log.Size = new Size(930, 154);
            logCard.Controls.Add(_log);

            CardPanel usage = NewCard(_pageService, 558, 150, "服务控制功能使用说明");
            usage.Controls.Add(TextLabel(
                "1. 在【设备绑定】中添加设备名称与地址，例如 192.168.1.66:8080，并设为当前设备。\r\n"
                + "2. 在【监听设置】填写端口（默认 1819），点击【启动服务】。\r\n"
                + "3. 手机 App 打开【硬件设置】，服务器填写本机 IP:端口，设备填写目标设备地址，保存并绑定。\r\n"
                + "4. 若手机无法访问，请在 Windows 防火墙中放行该端口，或改用管理员身份运行。",
                Theme.Small, Theme.Muted, new Point(18, 46)));
        }

        private void BuildBindPage()
        {
            _pageBind = new Panel();
            _pageBind.Location = new Point(0, 84);
            _pageBind.Size = new Size(1000, 652);
            _pageBind.BackColor = Theme.Bg;
            _pageBind.AutoScroll = true;
            _pageBind.Visible = false;
            Controls.Add(_pageBind);

            CardPanel card = NewCard(_pageBind, 12, 360, "设备绑定");
            card.Controls.Add(TextLabel(
                "手动添加设备，列表中带 ★ 的为当前转发设备。App 也可在绑定页直接填写设备地址。",
                Theme.Small, Theme.Muted, new Point(18, 42)));

            _deviceList = new ListBox();
            _deviceList.Font = new Font("Microsoft YaHei UI", 10f);
            _deviceList.BackColor = Theme.Input;
            _deviceList.ForeColor = Theme.Text;
            _deviceList.BorderStyle = BorderStyle.None;
            _deviceList.Location = new Point(18, 70);
            _deviceList.Size = new Size(560, 200);
            _deviceList.IntegralHeight = false;
            card.Controls.Add(_deviceList);

            card.Controls.Add(TextLabel("名称", Theme.Body, Theme.Muted, new Point(600, 70)));
            _name = Input("", new Point(600, 92), 340);
            card.Controls.Add(_name);

            card.Controls.Add(TextLabel("设备地址（IP:端口）", Theme.Body, Theme.Muted, new Point(600, 130)));
            _address = Input("", new Point(600, 152), 340);
            card.Controls.Add(_address);

            UiButton add = new UiButton("添加 / 更新", Theme.Accent);
            add.Size = new Size(164, 42);
            add.Location = new Point(600, 192);
            add.Click += delegate { AddDevice(); };
            card.Controls.Add(add);

            UiButton setCurrent = new UiButton("设为当前", Theme.Green);
            setCurrent.Size = new Size(164, 42);
            setCurrent.Location = new Point(776, 192);
            setCurrent.Click += delegate { SetCurrentDevice(); };
            card.Controls.Add(setCurrent);

            UiButton remove = new UiButton("删除选中", Theme.Red);
            remove.Size = new Size(164, 42);
            remove.Location = new Point(600, 244);
            remove.Click += delegate { RemoveDevice(); };
            card.Controls.Add(remove);

            _bindHint = TextLabel("", Theme.Small, Theme.Amber, new Point(18, 286));
            card.Controls.Add(_bindHint);

            _deviceList.SelectedIndexChanged += delegate
            {
                int i = _deviceList.SelectedIndex;
                if (i >= 0 && i < _devices.Count)
                {
                    _name.Text = _devices[i].Name;
                    _address.Text = _devices[i].Address;
                }
            };

            CardPanel usage = NewCard(_pageBind, 386, 140, "设备绑定功能使用说明");
            usage.Controls.Add(TextLabel(
                "1. 名称可自定义（例如 1 号田东侧）；地址格式为 IP:端口，端口省略时默认 80。\r\n"
                + "2. 点击【添加 / 更新】保存；选中列表项后可【设为当前】或【删除选中】。\r\n"
                + "3. 绑定结果保存在程序目录 server.cfg，重启后自动恢复。",
                Theme.Small, Theme.Muted, new Point(18, 44)));
        }

        private void BuildAboutPage()
        {
            _pageAbout = new Panel();
            _pageAbout.Location = new Point(0, 84);
            _pageAbout.Size = new Size(1000, 652);
            _pageAbout.BackColor = Theme.Bg;
            _pageAbout.AutoScroll = true;
            _pageAbout.Visible = false;
            Controls.Add(_pageAbout);

            CardPanel card = NewCard(_pageAbout, 12, 330, "开发警示");
            card.Controls.Add(TextLabel("版本 " + AppVersion, Theme.H2, Theme.Accent, new Point(18, 50)));
            card.Controls.Add(TextLabel("Copyright (C) 2026 【胡宇宸/tj248511fg51/y9000p】",
                Theme.Body, Theme.Text, new Point(18, 84)));
            card.Controls.Add(TextLabel("开发日期：2026-11-21    开发者：胡宇宸",
                Theme.Body, Theme.Muted, new Point(18, 112)));
            card.Controls.Add(TextLabel(
                "本程序为独立原创作品，版权归作者所有。\r\n"
                + "严禁未经许可反编译、逆向工程、破解、修改源码、非法复制及传播。\r\n"
                + "对于本软件相关规则、使用说明，最终解释权归作者本人。",
                Theme.Body, Theme.Muted, new Point(18, 146)));
        }

        // ---------------------------------------------------------- 交互

        private void ToggleServer()
        {
            if (_proxy.Running)
            {
                _proxy.Stop();
                Log("服务已停止");
                UpdateServerUi();
                return;
            }

            int port;
            if (!int.TryParse(_port.Text.Trim(), out port) || port <= 0 || port >= 65536)
            {
                MessageBox.Show(this, "端口需为 1 - 65535 之间的整数。", "端口无效",
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }

            try
            {
                _proxy.Start(port);
            }
            catch (Exception ex)
            {
                Log("启动失败：" + ex.Message);
                MessageBox.Show(this,
                    "端口 " + port + " 启动失败：" + ex.Message + "\r\n\r\n"
                    + "请确认端口未被占用，并在 Windows 防火墙中放行该端口。",
                    "启动失败", MessageBoxButtons.OK, MessageBoxIcon.Error);
                UpdateServerUi();
                return;
            }

            _port.Text = port.ToString();
            SaveConfig();
            Log("服务已启动，监听 0.0.0.0:" + port);
            UpdateServerUi();
        }

        private void UpdateServerUi()
        {
            bool on = _proxy.Running;
            _toggle.Text = on ? "停止服务" : "启动服务";
            _toggle.SetColor(on ? Theme.Red : Theme.Green);
            _statusLabel.Text = on ? "● 运行中  0.0.0.0:" + _proxy.Port : "● 已停止";
            _statusLabel.ForeColor = on ? Theme.Green : Theme.Red;
            _requestLabel.Text = "已转发请求：" + _proxy.Requests + "  ·  独立通道：" + _proxy.ChannelCount;
            string active = ActiveDeviceAddress();
            _activeLabel.Text = "当前设备：" + (active.Length == 0 ? "--" : active);
        }

        private void TickUi()
        {
            UpdateServerUi();
        }

        private void AddDevice()
        {
            string name = _name.Text.Trim();
            string address = _address.Text.Trim();
            if (address.Length == 0)
            {
                _bindHint.Text = "请填写设备地址，例如 192.168.1.66:8080";
                _bindHint.ForeColor = Theme.Red;
                return;
            }
            if (name.Length == 0) name = address;

            Device found = null;
            foreach (Device d in _devices)
            {
                if (string.Equals(d.Address, address, StringComparison.OrdinalIgnoreCase))
                {
                    found = d;
                    break;
                }
            }
            if (found == null)
            {
                found = new Device();
                found.Address = address;
                _devices.Add(found);
            }
            found.Name = name;
            if (ActiveDeviceAddress().Length == 0) found.Current = true;

            _name.Text = "";
            _address.Text = "";
            _bindHint.Text = "已保存：" + name + "  " + address;
            _bindHint.ForeColor = Theme.Green;
            RefreshDeviceList();
            SaveConfig();
            Log("绑定设备 " + name + " → " + address);
        }

        private void SetCurrentDevice()
        {
            int i = _deviceList.SelectedIndex;
            if (i < 0 || i >= _devices.Count)
            {
                _bindHint.Text = "请先在列表中选择一个设备";
                _bindHint.ForeColor = Theme.Red;
                return;
            }
            foreach (Device d in _devices) d.Current = false;
            _devices[i].Current = true;
            _bindHint.Text = "当前设备已切换为 " + _devices[i].Name;
            _bindHint.ForeColor = Theme.Green;
            RefreshDeviceList();
            SaveConfig();
            Log("当前设备切换为 " + _devices[i].Name + " (" + _devices[i].Address + ")");
        }

        private void RemoveDevice()
        {
            int i = _deviceList.SelectedIndex;
            if (i < 0 || i >= _devices.Count)
            {
                _bindHint.Text = "请先在列表中选择一个设备";
                _bindHint.ForeColor = Theme.Red;
                return;
            }
            Device d = _devices[i];
            DialogResult r = MessageBox.Show(this,
                "确定删除设备 \"" + d.Name + "\"？", "删除确认",
                MessageBoxButtons.YesNo, MessageBoxIcon.Warning);
            if (r != DialogResult.Yes) return;

            _devices.RemoveAt(i);
            if (d.Current && _devices.Count > 0) _devices[0].Current = true;
            _bindHint.Text = "已删除 " + d.Name;
            _bindHint.ForeColor = Theme.Amber;
            RefreshDeviceList();
            SaveConfig();
            Log("删除设备 " + d.Name);
        }

        private void RefreshDeviceList()
        {
            _deviceList.Items.Clear();
            foreach (Device d in _devices) _deviceList.Items.Add(d.ToString());
            UpdateServerUi();
        }

        private void Log(string message)
        {
            if (_log == null) return;
            if (_log.InvokeRequired)
            {
                try { _log.BeginInvoke(new Action<string>(Log), message); }
                catch { }
                return;
            }
            string line = DateTime.Now.ToString("HH:mm:ss", CultureInfo.InvariantCulture) + "  " + message;
            string old = _log.Text;
            string merged = old.Length == 0 ? line : old + "\r\n" + line;
            string[] lines = merged.Split(new string[] { "\r\n" }, StringSplitOptions.None);
            if (lines.Length > 200)
                merged = string.Join("\r\n", lines, lines.Length - 200, 200);
            _log.Text = merged;
            _log.SelectionStart = _log.TextLength;
            _log.ScrollToCaret();
        }
    }
}
