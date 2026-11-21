using System;
using System.Collections;
using System.Collections.Generic;
using System.Drawing;
using System.Globalization;
using System.IO;
using System.Net;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows.Forms;

namespace ScarecrowControl
{
    /// <summary>
    /// 扩展功能窗口：病虫害识别、防护服检测、驱鸟策略、小车路线、天气与水阀。
    /// 接口定义见 docs/APP控制协议.md 第 8-12 节。
    /// </summary>
    class FeaturesForm : Form
    {
        private readonly string _ip;
        private readonly JavaScriptSerializer _json = new JavaScriptSerializer();

        private readonly List<Button> _nav = new List<Button>();
        private readonly List<Panel> _pages = new List<Panel>();
        private Panel _host;
        private int _current = -1;

        private VisionPanel _pest;
        private VisionPanel _ppe;
        private StrategyPanel _strategy;
        private RobotPanel _robot;
        private WeatherPanel _weather;
        private System.Windows.Forms.Timer _timer;

        public int NavigateTo = -1;

        public FeaturesForm(string ip) : this(ip, 0) { }

        public FeaturesForm(string ip, int startPage)
        {
            _ip = (ip ?? "").Trim();
            if (_ip.Length == 0) _ip = "192.168.4.1";

            Text = "稻草人驱鸟控制器 - 扩展功能";
            ClientSize = new Size(1000, 850);
            FormBorderStyle = FormBorderStyle.FixedSingle;
            MaximizeBox = false;
            StartPosition = FormStartPosition.CenterParent;
            BackColor = Theme.Bg;
            ForeColor = Theme.Text;
            Font = new Font("Microsoft YaHei UI", 9.5f);
            AutoScaleMode = AutoScaleMode.None;

            try { ServicePointManager.SecurityProtocol |= SecurityProtocolType.Tls12; }
            catch { }

            Controls.Add(Ui.Lbl("扩展功能", 20, 10, 320, 34, 17f, true, Theme.Text));
            Controls.Add(Ui.Lbl("AI 视觉  ·  小车路线  ·  天气与水阀", 22, 44, 420, 22, 9f, false, Theme.Muted));

            UiButton close = new UiButton("关闭", Theme.CardEdge);
            close.Location = new Point(890, 14);
            close.Size = new Size(80, 32);
            close.Click += delegate { Close(); };
            Controls.Add(close);

            BuildNav();
            BuildPages();
            BuildBottomNav();
            Switch(startPage < 0 || startPage >= _pages.Count ? 0 : startPage);

            _timer = new System.Windows.Forms.Timer();
            _timer.Interval = 2000;
            _timer.Tick += delegate
            {
                if (_robot != null && Visible) _robot.Poll();
            };
            _timer.Start();
        }

        private void BuildNav()
        {
            string[] names = { "病虫害识别", "防护服检测", "驱鸟策略", "小车路线", "天气与水阀" };
            for (int i = 0; i < names.Length; i++)
            {
                UiButton b = new UiButton(names[i], Theme.Card);
                b.Location = new Point(16, 84 + i * 46);
                b.Size = new Size(150, 38);
                b.TextAlign = ContentAlignment.MiddleLeft;
                b.Padding = new Padding(12, 0, 0, 0);
                b.Font = new Font("Microsoft YaHei UI", 9.5f);
                int idx = i;
                b.Click += delegate { Switch(idx); };
                Controls.Add(b);
                _nav.Add(b);
            }
        }

        private void BuildPages()
        {
            _host = new Panel();
            _host.Location = new Point(180, 84);
            _host.Size = new Size(800, 700);
            _host.BackColor = Theme.Bg;
            Controls.Add(_host);

            _pest = new VisionPanel("pest", "病虫害识别",
                "接入摄像头实时画面，由局域网 YOLOv8 服务持续识别病害/虫害并标注位置。", _ip);
            _ppe = new VisionPanel("ppe", "防护服检测",
                "识别人员是否佩戴安全帽、穿戴反光衣，出现违规时给出报警标记。", _ip);
            _strategy = new StrategyPanel(_ip);
            _robot = new RobotPanel(_ip);
            _weather = new WeatherPanel(_ip);

            Panel[] pages = { _pest, _ppe, _strategy, _robot, _weather };
            foreach (Panel p in pages)
            {
                p.Dock = DockStyle.Fill;
                p.BackColor = Theme.Bg;
                p.Visible = false;
                _host.Controls.Add(p);
                _pages.Add(p);
            }
        }

        private void BuildBottomNav()
        {
            Panel bar = new Panel();
            bar.Dock = DockStyle.Bottom;
            bar.Height = 64;
            bar.BackColor = Theme.Card;
            Controls.Add(bar);

            Panel line = new Panel();
            line.Dock = DockStyle.Top;
            line.Height = 1;
            line.BackColor = Theme.CardEdge;
            bar.Controls.Add(line);

            string[] names = { "设备控制", "设备状态", "硬件设置", "扩展功能", "设置" };
            for (int i = 0; i < names.Length; i++)
            {
                UiButton b = new UiButton(names[i], i == 3 ? Theme.Accent : Theme.Card);
                b.Location = new Point(16 + i * 190, 10);
                b.Size = new Size(174, 44);
                b.Font = new Font("Microsoft YaHei UI", 10.5f);
                int idx = i;
                b.Click += delegate
                {
                    if (idx == 3) return;
                    NavigateTo = idx;
                    Close();
                };
                bar.Controls.Add(b);
            }
        }

        public static void AddUsage(Panel parent, int y, string feature, int height)
        {
            CardPanel card = new CardPanel();
            card.Location = new Point(16, y);
            card.Size = new Size(764, height);
            parent.Controls.Add(card);

            card.Controls.Add(Ui.Lbl(feature + "功能使用说明", 16, 10, 720, 26, 11f, true, Theme.Accent));
            Label body = Ui.Lbl(UsageText.Get(feature), 16, 40, 730, height - 50, 9.5f, false, Theme.Muted);
            body.TextAlign = ContentAlignment.TopLeft;
            card.Controls.Add(body);
        }

        private void Switch(int index)
        {
            if (index == _current) return;
            _current = index;
            for (int i = 0; i < _pages.Count; i++)
            {
                _pages[i].Visible = i == index;
                _nav[i].BackColor = i == index ? Theme.Accent : Theme.Card;
            }
        }

        protected override void OnFormClosed(FormClosedEventArgs e)
        {
            if (_timer != null) _timer.Stop();
            base.OnFormClosed(e);
        }

        public static string Api(string ip)
        {
            string s = (ip ?? "").Trim();
            if (s.Length == 0) s = "192.168.4.1";
            if (!s.StartsWith("http://") && !s.StartsWith("https://")) s = "http://" + s;
            while (s.EndsWith("/")) s = s.Substring(0, s.Length - 1);
            return s;
        }
    }

    // ---------------------------------------------------------------- 视觉

    class DetBox
    {
        public string Label;
        public double Conf;
        public int X1, Y1, X2, Y2;
    }

    /// <summary>
    /// 读取摄像头画面：MJPEG（multipart/x-mixed-replace）逐帧推送；
    /// 若地址返回 image/jpeg，则按快照定时抓取。
    /// </summary>
    class CameraStream
    {
        public event Action<byte[], Bitmap> FrameReady;
        public event Action<string> Failed;

        private readonly string _url;
        private Thread _thread;
        private volatile bool _running;
        private HttpWebResponse _resp;
        private Stream _stream;

        public CameraStream(string url)
        {
            _url = url;
        }

        public void Start()
        {
            Stop();
            _running = true;
            _thread = new Thread(Loop);
            _thread.IsBackground = true;
            _thread.Start();
        }

        public void Stop()
        {
            _running = false;
            try { if (_stream != null) _stream.Close(); } catch { }
            try { if (_resp != null) _resp.Close(); } catch { }
            _stream = null;
            _resp = null;
            Thread t = _thread;
            if (t != null)
            {
                try { t.Join(800); } catch { }
            }
            _thread = null;
        }

        private void Loop()
        {
            try
            {
                _resp = (HttpWebResponse)Request().GetResponse();
                string ct = _resp.ContentType ?? "";
                _stream = _resp.GetResponseStream();
                if (ct.StartsWith("image/", StringComparison.OrdinalIgnoreCase))
                {
                    SnapshotLoop();
                }
                else
                {
                    JpegSplitReader reader = new JpegSplitReader(_stream);
                    byte[] frame;
                    while (_running && (frame = reader.Next()) != null)
                    {
                        if (!Emit(frame)) break;
                    }
                }
            }
            catch (Exception ex)
            {
                if (_running) Fail(ex.Message);
            }
            finally
            {
                _running = false;
                try { if (_stream != null) _stream.Close(); } catch { }
                try { if (_resp != null) _resp.Close(); } catch { }
            }
        }

        private void SnapshotLoop()
        {
            while (_running)
            {
                try
                {
                    using (MemoryStream ms = new MemoryStream())
                    {
                        _stream.CopyTo(ms);
                        if (ms.Length > 100) Emit(ms.ToArray());
                    }
                }
                catch (Exception ex)
                {
                    if (_running) Fail(ex.Message);
                    break;
                }
                for (int i = 0; i < 5 && _running; i++) Thread.Sleep(80);
                if (!_running) break;
                try
                {
                    _stream.Close();
                    _resp.Close();
                    _resp = (HttpWebResponse)Request().GetResponse();
                    _stream = _resp.GetResponseStream();
                }
                catch (Exception ex)
                {
                    if (_running) Fail(ex.Message);
                    break;
                }
            }
        }

        private HttpWebRequest Request()
        {
            HttpWebRequest req = (HttpWebRequest)WebRequest.Create(_url);
            req.Proxy = null;
            req.Timeout = 8000;
            req.ReadWriteTimeout = 20000;
            req.KeepAlive = false;
            req.UserAgent = "ScarecrowControl/1.0";
            req.Headers["X-Client-Id"] = Http.ClientId;
            return req;
        }

        private bool Emit(byte[] jpeg)
        {
            Bitmap bmp;
            try
            {
                using (MemoryStream ms = new MemoryStream(jpeg)) bmp = new Bitmap(ms);
            }
            catch
            {
                return true;
            }
            Action<byte[], Bitmap> h = FrameReady;
            if (h == null)
            {
                bmp.Dispose();
                return false;
            }
            try
            {
                h(jpeg, bmp);
                return true;
            }
            catch
            {
                bmp.Dispose();
                return false;
            }
        }

        private void Fail(string message)
        {
            Action<string> h = Failed;
            if (h != null)
            {
                try { h(message); } catch { }
            }
        }
    }

    /// <summary>在字节流中按 JPEG 的 SOI/EOI 标记切出完整帧。</summary>
    class JpegSplitReader
    {
        private readonly ByteFeed _feed;
        private readonly MemoryStream _frame = new MemoryStream(262144);
        private bool _in;

        public JpegSplitReader(Stream stream)
        {
            _feed = new ByteFeed(stream, 32768);
        }

        public byte[] Next()
        {
            while (true)
            {
                int b = _feed.Next();
                if (b < 0) return null;

                if (!_in)
                {
                    if (b != 0xFF) continue;
                    int b2 = _feed.Next();
                    if (b2 < 0) return null;
                    if (b2 == 0xD8)
                    {
                        _in = true;
                        _frame.SetLength(0);
                        _frame.WriteByte(0xFF);
                        _frame.WriteByte(0xD8);
                    }
                    else
                    {
                        _feed.Push(b2);
                    }
                    continue;
                }

                _frame.WriteByte((byte)b);
                if (b != 0xFF) continue;

                int next = _feed.Next();
                if (next < 0) return null;
                if (next == 0xD9)
                {
                    _in = false;
                    _frame.WriteByte(0xD9);
                    if (_frame.Length > 16 * 1024 * 1024)
                    {
                        _frame.SetLength(0);
                        continue;
                    }
                    return _frame.ToArray();
                }
                _feed.Push(next);
            }
        }
    }

    class ByteFeed
    {
        private readonly Stream _stream;
        private readonly byte[] _buffer;
        private int _pos, _len, _push = -1;

        public ByteFeed(Stream stream, int size)
        {
            _stream = stream;
            _buffer = new byte[size];
        }

        public int Next()
        {
            if (_push >= 0)
            {
                int v = _push;
                _push = -1;
                return v;
            }
            if (_pos >= _len)
            {
                _len = _stream.Read(_buffer, 0, _buffer.Length);
                _pos = 0;
                if (_len <= 0) return -1;
            }
            return _buffer[_pos++] & 0xFF;
        }

        public void Push(int b)
        {
            _push = b;
        }
    }

    class VisionPanel : Panel
    {
        private readonly string _kind;
        private readonly string _ip;
        private readonly PictureBox _pic;
        private readonly TextBox _camera;
        private readonly TextBox _service;
        private readonly Label _result;
        private readonly Label _status;
        private readonly Button _run;
        private readonly Button _liveBtn;
        private readonly System.Windows.Forms.Timer _tick;
        private readonly JavaScriptSerializer _json = new JavaScriptSerializer();

        private CameraStream _cam;
        private byte[] _frame;
        private bool _live;
        private bool _busy;
        private string _path;
        private int _iw, _ih;
        private List<DetBox> _boxes = new List<DetBox>();
        private bool _alarm;

        public VisionPanel(string kind, string title, string desc, string ip)
        {
            _kind = kind;
            _ip = ip;
            BackColor = Theme.Bg;

            Controls.Add(Ui.Lbl(title, 16, 8, 400, 28, 12f, true, Theme.Text));
            Controls.Add(Ui.Lbl(desc, 16, 40, 760, 22, 9f, false, Theme.Muted));

            CardPanel frame = new CardPanel();
            frame.Location = new Point(16, 76);
            frame.Size = new Size(400, 320);
            Controls.Add(frame);

            _pic = new PictureBox();
            _pic.Location = new Point(10, 10);
            _pic.Size = new Size(380, 300);
            _pic.BackColor = Theme.Input;
            _pic.SizeMode = PictureBoxSizeMode.Zoom;
            _pic.Paint += PicPaint;
            frame.Controls.Add(_pic);

            Controls.Add(Ui.Lbl("摄像头地址", 432, 74, 120, 22, 9f, false, Theme.Muted));
            _camera = new TextBox();
            _camera.Text = FeaturesForm.Api(ip) + "/api/camera/stream";
            _camera.Location = new Point(432, 98);
            _camera.Size = new Size(352, 28);
            _camera.BackColor = Theme.Input;
            _camera.ForeColor = Theme.Text;
            _camera.BorderStyle = BorderStyle.FixedSingle;
            _camera.Font = new Font("Consolas", 9.5f);
            Controls.Add(_camera);

            _liveBtn = new UiButton("开始实时", Theme.Accent);
            _liveBtn.Location = new Point(432, 134);
            _liveBtn.Size = new Size(120, 36);
            _liveBtn.Click += delegate { ToggleLive(); };
            Controls.Add(_liveBtn);

            UiButton stopLive = new UiButton("停止", Theme.CardEdge);
            stopLive.Location = new Point(560, 134);
            stopLive.Size = new Size(80, 36);
            stopLive.Click += delegate { StopLive("实时识别已停止"); };
            Controls.Add(stopLive);

            UiButton pick = new UiButton("单张图片", Theme.CardEdge);
            pick.Location = new Point(648, 134);
            pick.Size = new Size(136, 36);
            pick.Click += delegate { PickFile(); };
            Controls.Add(pick);

            Controls.Add(Ui.Lbl("AI 服务地址", 432, 178, 120, 22, 9f, false, Theme.Muted));
            _service = new TextBox();
            _service.Text = FeaturesForm.Api(ip);
            _service.Location = new Point(432, 202);
            _service.Size = new Size(352, 28);
            _service.BackColor = Theme.Input;
            _service.ForeColor = Theme.Text;
            _service.BorderStyle = BorderStyle.FixedSingle;
            _service.Font = new Font("Consolas", 10f);
            Controls.Add(_service);

            _run = new UiButton("识别当前画面", Theme.CardEdge);
            _run.Location = new Point(432, 240);
            _run.Size = new Size(160, 34);
            _run.Click += delegate { RunDetect(); };
            Controls.Add(_run);

            CardPanel box = new CardPanel();
            box.Location = new Point(432, 286);
            box.Size = new Size(352, 228);
            Controls.Add(box);

            _result = Ui.Lbl("", 12, 10, 328, 208, 9f, false, Theme.Text);
            _result.TextAlign = ContentAlignment.TopLeft;
            box.Controls.Add(_result);

            _status = Ui.Lbl("等待操作", 16, 528, 760, 24, 9f, false, Theme.Muted);
            Controls.Add(_status);

            FeaturesForm.AddUsage(this, 560, title, 172);

            _tick = new System.Windows.Forms.Timer();
            _tick.Interval = 800;
            _tick.Tick += delegate { DetectTick(); };
        }

        private void PickFile()
        {
            StopLive("已切换到单张图片");
            using (OpenFileDialog dlg = new OpenFileDialog())
            {
                dlg.Filter = "图片|*.jpg;*.jpeg;*.png;*.bmp|所有文件|*.*";
                if (dlg.ShowDialog(this) != DialogResult.OK) return;
                try
                {
                    using (Image img = Image.FromFile(dlg.FileName))
                    {
                        _iw = img.Width;
                        _ih = img.Height;
                    }
                    _path = dlg.FileName;
                    _frame = null;
                    Image old = _pic.Image;
                    _pic.Image = Image.FromFile(dlg.FileName);
                    if (old != null) old.Dispose();
                    _boxes.Clear();
                    _alarm = false;
                    _pic.Invalidate();
                    _result.Text = "";
                    _status.Text = "已选择：" + Path.GetFileName(dlg.FileName) + "  " + _iw + "×" + _ih;
                    _status.ForeColor = Theme.Muted;
                    RunDetect();
                }
                catch (Exception ex)
                {
                    _status.Text = "图片读取失败：" + ex.Message;
                    _status.ForeColor = Theme.Red;
                }
            }
        }

        private void ToggleLive()
        {
            if (_live) StopLive("实时识别已停止");
            else StartLive();
        }

        private void StartLive()
        {
            string url = _camera.Text.Trim();
            if (url.Length == 0)
            {
                _status.Text = "请先填写摄像头地址";
                _status.ForeColor = Theme.Amber;
                return;
            }
            StopLive(null);
            _live = true;
            _frame = null;
            _liveBtn.Text = "停止实时";
            _status.Text = "正在连接摄像头…（MJPEG 流，或 image/jpeg 快照地址）";
            _status.ForeColor = Theme.Muted;
            _cam = new CameraStream(url);
            _cam.FrameReady += OnFrame;
            _cam.Failed += OnCamFailed;
            _cam.Start();
            _tick.Start();
        }

        private void StopLive(string message)
        {
            _live = false;
            if (_tick != null) _tick.Stop();
            if (_cam != null)
            {
                _cam.FrameReady -= OnFrame;
                _cam.Failed -= OnCamFailed;
                _cam.Stop();
                _cam = null;
            }
            if (_liveBtn != null) _liveBtn.Text = "开始实时";
            if (message != null)
            {
                _status.Text = message;
                _status.ForeColor = Theme.Muted;
            }
        }

        private void OnFrame(byte[] jpeg, Bitmap bmp)
        {
            if (!_live)
            {
                bmp.Dispose();
                return;
            }
            _frame = jpeg;
            int w = bmp.Width, h = bmp.Height;
            try
            {
                BeginInvoke(new Action(delegate
                {
                    if (!_live)
                    {
                        bmp.Dispose();
                        return;
                    }
                    Image old = _pic.Image;
                    _pic.Image = bmp;
                    _iw = w;
                    _ih = h;
                    if (old != null && old != bmp) old.Dispose();
                    _pic.Invalidate();
                }));
            }
            catch
            {
                bmp.Dispose();
            }
        }

        private void OnCamFailed(string message)
        {
            try
            {
                BeginInvoke(new Action(delegate
                {
                    if (!_live) return;
                    StopLive("摄像头连接失败：" + message);
                    _status.ForeColor = Theme.Red;
                }));
            }
            catch { }
        }

        private void DetectTick()
        {
            if (!_live || _busy) return;
            byte[] frame = _frame;
            if (frame == null) return;
            string service = _service.Text.Trim();
            if (service.Length == 0) return;

            string url = FeaturesForm.Api(service) + "/api/vision/detect?kind=" + _kind;
            _busy = true;
            Task.Run(delegate { return Http.PostFile(url, "image", "frame.jpg", frame, 8000); })
                .ContinueWith(delegate(Task<string> t)
                {
                    try
                    {
                        BeginInvoke(new Action(delegate
                        {
                            _busy = false;
                            if (!_live) return;
                            if (t.IsFaulted)
                            {
                                Exception ex = t.Exception != null && t.Exception.InnerException != null
                                    ? t.Exception.InnerException : t.Exception;
                                WebException wex = ex as WebException;
                                HttpWebResponse r = wex != null ? wex.Response as HttpWebResponse : null;
                                if (r != null && (int)r.StatusCode == 404)
                                {
                                    StopLive("设备固件不支持视觉接口（404）");
                                    _status.ForeColor = Theme.Red;
                                }
                                else
                                {
                                    _status.Text = "识别失败：" + (ex == null ? "未知错误" : ex.Message);
                                    _status.ForeColor = Theme.Red;
                                }
                            }
                            else
                            {
                                ShowResult(t.Result);
                            }
                        }));
                    }
                    catch
                    {
                        _busy = false;
                    }
                });
        }

        private async void RunDetect()
        {
            byte[] data = _frame;
            if (data == null && _path != null)
            {
                try { data = File.ReadAllBytes(_path); }
                catch (Exception ex)
                {
                    _status.Text = "图片读取失败：" + ex.Message;
                    _status.ForeColor = Theme.Red;
                    return;
                }
            }
            if (data == null)
            {
                _status.Text = "请先开启实时画面或选择图片";
                _status.ForeColor = Theme.Amber;
                return;
            }
            string service = _service.Text.Trim();
            if (service.Length == 0)
            {
                _status.Text = "请先填写 AI 服务地址";
                _status.ForeColor = Theme.Amber;
                return;
            }
            string url = FeaturesForm.Api(service) + "/api/vision/detect?kind=" + _kind;
            _run.Enabled = false;
            _status.Text = "正在识别…";
            _status.ForeColor = Theme.Muted;
            try
            {
                string body = await Task.Run(delegate
                {
                    return Http.PostFile(url, "image", "image.jpg", data, 30000);
                });
                ShowResult(body);
            }
            catch (WebException wex)
            {
                HttpWebResponse r = wex.Response as HttpWebResponse;
                if (r != null && (int)r.StatusCode == 404)
                {
                    _status.Text = "设备固件不支持视觉接口（404）";
                }
                else
                {
                    _status.Text = "识别失败：" + wex.Message;
                }
                _status.ForeColor = Theme.Red;
            }
            catch (Exception ex)
            {
                _status.Text = "识别失败：" + ex.Message;
                _status.ForeColor = Theme.Red;
            }
            finally
            {
                _run.Enabled = true;
            }
        }

        private void ShowResult(string body)
        {
            Dictionary<string, object> root;
            try { root = _json.Deserialize<Dictionary<string, object>>(body); }
            catch { _status.Text = "返回不是合法 JSON"; _status.ForeColor = Theme.Red; return; }

            object v;
            if (root.TryGetValue("image_w", out v)) _iw = ToInt(v, _iw);
            if (root.TryGetValue("image_h", out v)) _ih = ToInt(v, _ih);

            _boxes.Clear();
            _alarm = false;
            if (root.TryGetValue("alarm", out v)) _alarm = ToBool(v);

            StringBuilder sb = new StringBuilder();
            // JavaScriptSerializer 把 JSON 数组解成 object[]，这里按 IList 兼容处理
            IList list = null;
            if (root.TryGetValue("detections", out v)) list = v as IList;
            int n = 0;
            if (list != null)
            {
                foreach (object o in list)
                {
                    Dictionary<string, object> d = o as Dictionary<string, object>;
                    if (d == null) continue;
                    DetBox b = new DetBox();
                    b.Label = Str(d, "label");
                    b.Conf = Num(d, "confidence", 0);
                    IList bx = null;
                    if (d.ContainsKey("box")) bx = d["box"] as IList;
                    if (bx != null && bx.Count >= 4)
                    {
                        b.X1 = ToInt(bx[0], 0); b.Y1 = ToInt(bx[1], 0);
                        b.X2 = ToInt(bx[2], 0); b.Y2 = ToInt(bx[3], 0);
                    }
                    _boxes.Add(b);
                    n++;
                    sb.AppendLine(string.Format("{0}. {1}   置信度 {2:P0}", n, b.Label, b.Conf));
                    if (b.X2 > b.X1 && b.Y2 > b.Y1)
                    {
                        sb.AppendLine(string.Format("    位置 [{0},{1}] - [{2},{3}]", b.X1, b.Y1, b.X2, b.Y2));
                    }
                }
            }
            if (n == 0) sb.AppendLine("未检测到目标");

            if (_kind == "ppe")
            {
                object pc;
                int persons = root.TryGetValue("person_count", out pc) ? ToInt(pc, 0) : 0;
                StringBuilder head = new StringBuilder();
                head.AppendFormat("人员 {0} 人 · {1}\r\n", persons,
                    _alarm ? "发现违规，需整改" : "未发现违规");

                object wv;
                if (root.TryGetValue("wearing", out wv))
                {
                    Dictionary<string, object> wearing = wv as Dictionary<string, object>;
                    if (wearing != null)
                    {
                        int ok = wearing.ContainsKey("compliant") ? ToInt(wearing["compliant"], 0) : 0;
                        int bad = wearing.ContainsKey("violations") ? ToInt(wearing["violations"], 0) : 0;
                        int mh = wearing.ContainsKey("missing_helmet") ? ToInt(wearing["missing_helmet"], 0) : 0;
                        int mv = wearing.ContainsKey("missing_vest") ? ToInt(wearing["missing_vest"], 0) : 0;
                        head.AppendFormat("穿戴合规 {0} 人 · 不合规 {1} 人", ok, bad);
                        if (mh > 0) head.AppendFormat(" · 缺安全帽 {0}", mh);
                        if (mv > 0) head.AppendFormat(" · 缺防护服 {0}", mv);
                        head.AppendLine();
                    }
                }
                object sm;
                if (root.TryGetValue("summary", out sm) && sm != null)
                    head.AppendLine(sm.ToString());
                object ready;
                if (root.TryGetValue("ppe_ready", out ready) && !ToBool(ready))
                    head.AppendLine("提示：当前权重不含穿戴类别，请放入 models/ppe.pt 后重启识别服务。");
                sb.Insert(0, head.ToString() + "\r\n");
            }
            else if (_kind == "pest")
            {
                object sm;
                if (root.TryGetValue("summary", out sm) && sm != null)
                    sb.Insert(0, sm.ToString() + "\r\n\r\n");
            }
            _result.Text = sb.ToString();
            _pic.Invalidate();

            _status.Text = string.Format("识别完成，共 {0} 个目标，耗时 {1} ms",
                n, Str(root, "cost_ms"));
            _status.ForeColor = _alarm ? Theme.Red : Theme.Green;
        }

        private void PicPaint(object sender, PaintEventArgs e)
        {
            if (_boxes.Count == 0 || _pic.Image == null) return;
            float scale = Math.Min(_pic.ClientSize.Width / (float)Math.Max(1, _iw),
                                   _pic.ClientSize.Height / (float)Math.Max(1, _ih));
            float ox = (_pic.ClientSize.Width - _iw * scale) / 2f;
            float oy = (_pic.ClientSize.Height - _ih * scale) / 2f;

            using (Pen pen = new Pen(_alarm ? Theme.Red : Theme.Green, 2f))
            using (SolidBrush bg = new SolidBrush(Color.FromArgb(190, 11, 18, 32)))
            using (SolidBrush fg = new SolidBrush(Theme.Text))
            {
                foreach (DetBox b in _boxes)
                {
                    if (b.X2 <= b.X1 || b.Y2 <= b.Y1) continue;
                    RectangleF r = new RectangleF(ox + b.X1 * scale, oy + b.Y1 * scale,
                                                  (b.X2 - b.X1) * scale, (b.Y2 - b.Y1) * scale);
                    e.Graphics.DrawRectangle(pen, r.X, r.Y, r.Width, r.Height);
                    string text = b.Label + " " + b.Conf.ToString("P0");
                    SizeF sz = e.Graphics.MeasureString(text, Font);
                    e.Graphics.FillRectangle(bg, r.X, Math.Max(0, r.Y - sz.Height), sz.Width, sz.Height);
                    e.Graphics.DrawString(text, Font, fg, r.X, Math.Max(0, r.Y - sz.Height));
                }
            }
        }

        // JSON 取值小工具
        static string Str(Dictionary<string, object> d, string k)
        {
            object v;
            return d.TryGetValue(k, out v) && v != null ? Convert.ToString(v) : "";
        }

        static double Num(Dictionary<string, object> d, string k, double def)
        {
            object v;
            if (!d.TryGetValue(k, out v) || v == null) return def;
            try { return Convert.ToDouble(v, CultureInfo.InvariantCulture); }
            catch { return def; }
        }

        static int ToInt(object v, int def)
        {
            try { return Convert.ToInt32(v, CultureInfo.InvariantCulture); }
            catch { return def; }
        }

        static bool ToBool(object v)
        {
            if (v == null) return false;
            if (v is bool) return (bool)v;
            try { return Convert.ToInt32(v) != 0; } catch { return false; }
        }
    }

    // ---------------------------------------------------------------- 驱鸟策略

    class StrategyPanel : Panel
    {
        private readonly string _ip;
        private readonly ComboBox _mode;
        private readonly NumericUpDown _visionCool;
        private readonly Label _status;
        private readonly JavaScriptSerializer _json = new JavaScriptSerializer();

        public StrategyPanel(string ip)
        {
            _ip = ip;
            BackColor = Theme.Bg;

            Controls.Add(Ui.Lbl("驱鸟策略", 16, 8, 400, 28, 12f, true, Theme.Text));
            Controls.Add(Ui.Lbl("选择触发源：雷达稳定省电，视觉精准，两者结合可降低误触发。",
                16, 40, 760, 22, 9f, false, Theme.Muted));

            CardPanel card = new CardPanel();
            card.Location = new Point(16, 76);
            card.Size = new Size(764, 250);
            Controls.Add(card);

            card.Controls.Add(Ui.Lbl("触发源", 20, 20, 100, 26, 9f, false, Theme.Muted));
            _mode = new ComboBox();
            _mode.DropDownStyle = ComboBoxStyle.DropDownList;
            _mode.Items.AddRange(new object[] { "雷达触发", "视觉触发", "雷达 + 视觉" });
            _mode.SelectedIndex = 0;
            _mode.Location = new Point(130, 18);
            _mode.Size = new Size(200, 26);
            _mode.BackColor = Theme.Input;
            _mode.ForeColor = Theme.Text;
            card.Controls.Add(_mode);

            card.Controls.Add(Ui.Lbl("视觉冷却（秒）", 20, 66, 148, 26, 9f, false, Theme.Muted));
            _visionCool = new NumericUpDown();
            _visionCool.Minimum = 30;
            _visionCool.Maximum = 3600;
            _visionCool.Value = 120;
            _visionCool.Location = new Point(170, 64);
            _visionCool.Size = new Size(110, 26);
            _visionCool.BackColor = Theme.Input;
            _visionCool.ForeColor = Theme.Text;
            _visionCool.BorderStyle = BorderStyle.FixedSingle;
            card.Controls.Add(_visionCool);

            UiButton apply = new UiButton("应用策略", Theme.Accent);
            apply.Location = new Point(130, 110);
            apply.Size = new Size(140, 38);
            apply.Click += delegate { Apply(); };
            card.Controls.Add(apply);

            UiButton fire = new UiButton("立即驱赶", Theme.CardEdge);
            fire.Location = new Point(286, 110);
            fire.Size = new Size(140, 38);
            fire.Click += delegate { Fire(); };
            card.Controls.Add(fire);

            UiButton refresh = new UiButton("读取当前状态", Theme.CardEdge);
            refresh.Location = new Point(442, 110);
            refresh.Size = new Size(150, 38);
            refresh.Click += delegate { LoadState(); };
            card.Controls.Add(refresh);

            _status = Ui.Lbl("未读取状态", 20, 196, 720, 24, 9f, false, Theme.Muted);
            card.Controls.Add(_status);

            FeaturesForm.AddUsage(this, 340, "驱鸟策略", 130);
        }

        private void Apply()
        {
            string[] values = { "radar", "vision", "both" };
            string body = "strategy=" + values[Math.Max(0, _mode.SelectedIndex)] +
                          "&visionCool=" + ((int)_visionCool.Value);
            try
            {
                string resp = Http.Post(FeaturesForm.Api(_ip) + "/api/config", body, 4000);
                _status.Text = "已下发：" + resp;
                _status.ForeColor = Theme.Green;
            }
            catch (WebException wex)
            {
                HttpWebResponse r = wex.Response as HttpWebResponse;
                _status.Text = r != null && (int)r.StatusCode == 404
                    ? "固件不支持策略配置（404），请升级固件"
                    : "下发失败：" + wex.Message;
                _status.ForeColor = Theme.Red;
            }
            catch (Exception ex)
            {
                _status.Text = "下发失败：" + ex.Message;
                _status.ForeColor = Theme.Red;
            }
        }

        private void Fire()
        {
            try
            {
                Http.Post(FeaturesForm.Api(_ip) + "/api/test?what=all", "", 4000);
                _status.Text = "已触发一次声光驱赶";
                _status.ForeColor = Theme.Green;
            }
            catch (Exception ex)
            {
                _status.Text = "触发失败：" + ex.Message;
                _status.ForeColor = Theme.Red;
            }
        }

        private void LoadState()
        {
            try
            {
                string body = Http.Get(FeaturesForm.Api(_ip) + "/api/status", 3000);
                Dictionary<string, object> d = _json.Deserialize<Dictionary<string, object>>(body);
                object v;
                string state = d.TryGetValue("state", out v) ? Convert.ToString(v) : "?";
                string strategy = d.TryGetValue("strategy", out v) ? Convert.ToString(v) : "radar";
                string mode = d.TryGetValue("mode", out v) ? Convert.ToString(v) : "AP";
                _status.Text = string.Format("运行状态 {0} · 网络 {1} · 当前策略 {2}", state, mode, strategy);
                _status.ForeColor = Theme.Green;

                if (strategy == "vision") _mode.SelectedIndex = 1;
                else if (strategy == "both") _mode.SelectedIndex = 2;
                else _mode.SelectedIndex = 0;
            }
            catch (Exception ex)
            {
                _status.Text = "读取失败：" + ex.Message;
                _status.ForeColor = Theme.Red;
            }
        }
    }

    // ---------------------------------------------------------------- 小车路线

    class RobotPanel : Panel
    {
        private readonly string _ip;
        private readonly DataGridView _grid;
        private readonly Label _state;
        private readonly JavaScriptSerializer _json = new JavaScriptSerializer();

        public RobotPanel(string ip)
        {
            _ip = ip;
            BackColor = Theme.Bg;

            Controls.Add(Ui.Lbl("小车固定路线", 16, 8, 400, 28, 12f, true, Theme.Text));
            Controls.Add(Ui.Lbl("按顺序记录航点，可给每个点附带动作（喷施/拍照/停留）。",
                16, 40, 760, 22, 9f, false, Theme.Muted));

            _grid = new DataGridView();
            _grid.Location = new Point(16, 76);
            _grid.Size = new Size(500, 420);
            _grid.BackgroundColor = Theme.Input;
            _grid.GridColor = Theme.CardEdge;
            _grid.BorderStyle = BorderStyle.None;
            _grid.RowHeadersVisible = false;
            _grid.AllowUserToAddRows = false;
            _grid.AllowUserToResizeRows = false;
            _grid.AutoSizeColumnsMode = DataGridViewAutoSizeColumnsMode.Fill;
            _grid.EnableHeadersVisualStyles = false;
            _grid.ColumnHeadersDefaultCellStyle.BackColor = Theme.Card;
            _grid.ColumnHeadersDefaultCellStyle.ForeColor = Theme.Text;
            _grid.DefaultCellStyle.BackColor = Theme.Input;
            _grid.DefaultCellStyle.ForeColor = Theme.Text;
            _grid.DefaultCellStyle.SelectionBackColor = Theme.CardEdge;
            _grid.DefaultCellStyle.SelectionForeColor = Theme.Text;
            _grid.Columns.Add("no", "#");
            _grid.Columns.Add("x", "X (m)");
            _grid.Columns.Add("y", "Y (m)");
            DataGridViewComboBoxColumn act = new DataGridViewComboBoxColumn();
            act.Name = "action";
            act.HeaderText = "动作";
            act.Items.AddRange(new object[] { "none", "spray", "water", "photo", "wait" });
            act.FlatStyle = FlatStyle.Flat;
            _grid.Columns.Add(act);
            _grid.Columns.Add("wait", "停留 (s)");
            _grid.Columns["no"].ReadOnly = true;
            Controls.Add(_grid);

            int bx = 536;
            AddBtn("添加点", bx, 76, delegate { AddRow(); }, Theme.Accent);
            AddBtn("删除点", bx, 122, delegate { DelRow(); }, Theme.CardEdge);
            AddBtn("上移", bx, 168, delegate { MoveRow(-1); }, Theme.CardEdge);
            AddBtn("下移", bx, 214, delegate { MoveRow(1); }, Theme.CardEdge);
            AddBtn("下发路线", bx, 278, delegate { Upload(); }, Theme.Accent);
            AddBtn("启动", bx, 324, delegate { Control("start"); }, Theme.Green);
            AddBtn("暂停", bx, 370, delegate { Control("pause"); }, Theme.CardEdge);
            AddBtn("停止", bx, 416, delegate { Control("stop"); }, Theme.Red);
            AddBtn("回原点", bx, 462, delegate { Control("home"); }, Theme.CardEdge);

            _state = Ui.Lbl("未连接", 16, 510, 764, 24, 9f, false, Theme.Muted);
            Controls.Add(_state);

            Controls.Add(Ui.Lbl("说明：X/Y 为相对起点的米数；动作执行完才前往下一点。", 16, 540, 764, 22,
                9f, false, Theme.Muted));

            FeaturesForm.AddUsage(this, 570, "小车固定路线", 124);

            AddRow();
        }

        private void AddBtn(string text, int x, int y, EventHandler h, Color color)
        {
            UiButton b = new UiButton(text, color);
            b.Location = new Point(x, y);
            b.Size = new Size(120, 38);
            b.Click += h;
            Controls.Add(b);
        }

        private void AddRow()
        {
            int i = _grid.Rows.Add();
            _grid.Rows[i].Cells[0].Value = (i + 1).ToString();
            _grid.Rows[i].Cells[1].Value = "0";
            _grid.Rows[i].Cells[2].Value = "0";
            _grid.Rows[i].Cells[3].Value = "none";
            _grid.Rows[i].Cells[4].Value = "0";
        }

        private void DelRow()
        {
            if (_grid.CurrentRow != null) _grid.Rows.Remove(_grid.CurrentRow);
            Renumber();
        }

        private void MoveRow(int delta)
        {
            if (_grid.CurrentRow == null) return;
            int i = _grid.CurrentRow.Index;
            int j = i + delta;
            if (j < 0 || j >= _grid.Rows.Count) return;
            DataGridViewRow row = _grid.Rows[i];
            _grid.Rows.RemoveAt(i);
            _grid.Rows.Insert(j, row);
            _grid.CurrentCell = _grid.Rows[j].Cells[1];
            Renumber();
        }

        private void Renumber()
        {
            for (int i = 0; i < _grid.Rows.Count; i++) _grid.Rows[i].Cells[0].Value = (i + 1).ToString();
        }

        private string BuildJson()
        {
            StringBuilder sb = new StringBuilder();
            sb.Append("{\"loop\":false,\"waypoints\":[");
            for (int i = 0; i < _grid.Rows.Count; i++)
            {
                DataGridViewRow r = _grid.Rows[i];
                if (i > 0) sb.Append(',');
                sb.AppendFormat(CultureInfo.InvariantCulture,
                    "{{\"x\":{0},\"y\":{1},\"action\":\"{2}\",\"wait_s\":{3}}}",
                    D(r.Cells[1].Value), D(r.Cells[2].Value),
                    Convert.ToString(r.Cells[3].Value ?? "none"), (int)D(r.Cells[4].Value));
            }
            sb.Append("]}");
            return sb.ToString();
        }

        static double D(object v)
        {
            double d;
            if (v == null) return 0;
            double.TryParse(Convert.ToString(v), NumberStyles.Float, CultureInfo.InvariantCulture, out d);
            return d;
        }

        private void Upload()
        {
            try
            {
                string resp = Http.Post(FeaturesForm.Api(_ip) + "/api/robot/route", BuildJson(), 6000);
                _state.Text = "路线已下发：" + resp;
                _state.ForeColor = Theme.Green;
            }
            catch (Exception ex)
            {
                _state.Text = "下发失败：" + Describe(ex);
                _state.ForeColor = Theme.Red;
            }
        }

        private void Control(string action)
        {
            try
            {
                string resp = Http.Post(FeaturesForm.Api(_ip) + "/api/robot/control",
                    "{\"action\":\"" + action + "\"}", 4000);
                _state.Text = "指令 " + action + " 已发送：" + resp;
                _state.ForeColor = Theme.Green;
            }
            catch (Exception ex)
            {
                _state.Text = "指令失败：" + Describe(ex);
                _state.ForeColor = Theme.Red;
            }
        }

        public void Poll()
        {
            try
            {
                string body = Http.Get(FeaturesForm.Api(_ip) + "/api/robot/state", 2500);
                Dictionary<string, object> d = _json.Deserialize<Dictionary<string, object>>(body);
                _state.Text = string.Format("模式 {0} · 航点 {1}/{2} · 坐标 ({3:0.0}, {4:0.0}) · 电量 {5}%",
                    Get(d, "mode"), Get(d, "waypoint"), Get(d, "total"),
                    GetNum(d, "x"), GetNum(d, "y"), Get(d, "battery"));
                _state.ForeColor = Theme.Green;
            }
            catch
            {
                _state.Text = "小车未连接或固件不支持该接口";
                _state.ForeColor = Theme.Muted;
            }
        }

        static string Get(Dictionary<string, object> d, string k)
        {
            object v;
            return d.TryGetValue(k, out v) && v != null ? Convert.ToString(v) : "-";
        }

        static double GetNum(Dictionary<string, object> d, string k)
        {
            object v;
            if (!d.TryGetValue(k, out v) || v == null) return 0;
            try { return Convert.ToDouble(v, CultureInfo.InvariantCulture); } catch { return 0; }
        }

        static string Describe(Exception ex)
        {
            WebException wex = ex as WebException;
            if (wex != null)
            {
                HttpWebResponse r = wex.Response as HttpWebResponse;
                if (r != null && (int)r.StatusCode == 404) return "固件不支持（404）";
            }
            return ex.Message;
        }
    }

    // ---------------------------------------------------------------- 天气与水阀

    class WeatherPanel : Panel
    {
        private readonly string _ip;
        private readonly TextBox _lat;
        private readonly TextBox _lon;
        private readonly Label _now;
        private readonly Label _advice;
        private readonly Label _valve;
        private readonly CheckBox _auto;
        private readonly NumericUpDown _humidity;
        private readonly NumericUpDown _tmin, _tmax;
        private readonly JavaScriptSerializer _json = new JavaScriptSerializer();

        private double _temp = double.NaN;
        private double _hum = double.NaN;
        private double _rain = double.NaN;

        public WeatherPanel(string ip)
        {
            _ip = ip;
            BackColor = Theme.Bg;

            Controls.Add(Ui.Lbl("天气与水阀", 16, 8, 400, 28, 12f, true, Theme.Text));
            Controls.Add(Ui.Lbl("读取实时天气，按温湿度与降雨判断是否需要灌溉；也可手动开关水阀。",
                16, 40, 760, 22, 9f, false, Theme.Muted));

            CardPanel w = new CardPanel();
            w.Location = new Point(16, 76);
            w.Size = new Size(764, 210);
            Controls.Add(w);

            w.Controls.Add(Ui.Lbl("纬度", 20, 18, 60, 24, 9f, false, Theme.Muted));
            _lat = Input("30.28", 80, 16, 120);
            w.Controls.Add(_lat);

            w.Controls.Add(Ui.Lbl("经度", 216, 18, 60, 24, 9f, false, Theme.Muted));
            _lon = Input("120.15", 276, 16, 120);
            w.Controls.Add(_lon);

            UiButton get = new UiButton("刷新天气", Theme.Accent);
            get.Location = new Point(420, 15);
            get.Size = new Size(130, 34);
            get.Click += delegate { LoadWeather(); };
            w.Controls.Add(get);

            _now = Ui.Lbl("尚未获取", 20, 62, 720, 26, 10f, false, Theme.Text);
            w.Controls.Add(_now);

            _advice = Ui.Lbl("", 20, 96, 720, 26, 9.5f, false, Theme.Muted);
            w.Controls.Add(_advice);

            w.Controls.Add(Ui.Lbl("自动规则：湿度低于阈值、温度在区间内且无降雨时开阀",
                20, 132, 720, 22, 9f, false, Theme.Muted));

            _auto = new CheckBox();
            _auto.Text = "启用";
            _auto.Location = new Point(20, 164);
            _auto.Size = new Size(64, 26);
            _auto.ForeColor = Theme.Text;
            w.Controls.Add(_auto);

            w.Controls.Add(Ui.Lbl("湿度 <", 92, 166, 56, 22, 9f, false, Theme.Muted));
            _humidity = Num(40, 148, 164, 80, 0, 100);
            w.Controls.Add(_humidity);
            w.Controls.Add(Ui.Lbl("%", 232, 166, 20, 22, 9f, false, Theme.Muted));
            w.Controls.Add(Ui.Lbl("温度", 256, 166, 44, 22, 9f, false, Theme.Muted));
            _tmin = Num(5, 300, 164, 70, -20, 60);
            w.Controls.Add(_tmin);
            w.Controls.Add(Ui.Lbl("~", 376, 166, 20, 22, 9f, false, Theme.Muted));
            _tmax = Num(35, 396, 164, 70, -20, 60);
            w.Controls.Add(_tmax);
            w.Controls.Add(Ui.Lbl("℃", 470, 166, 30, 22, 9f, false, Theme.Muted));

            UiButton apply = new UiButton("应用规则", Theme.CardEdge);
            apply.Location = new Point(516, 160);
            apply.Size = new Size(120, 34);
            apply.Click += delegate { ApplyRule(); };
            w.Controls.Add(apply);

            CardPanel v = new CardPanel();
            v.Location = new Point(16, 302);
            v.Size = new Size(764, 200);
            Controls.Add(v);

            v.Controls.Add(Ui.Lbl("水阀控制", 20, 14, 200, 26, 11f, true, Theme.Text));
            _valve = Ui.Lbl("未读取阀门状态", 20, 48, 720, 26, 9.5f, false, Theme.Muted);
            v.Controls.Add(_valve);

            UiButton open = new UiButton("开阀 30 秒", Theme.Green);
            open.Location = new Point(20, 88);
            open.Size = new Size(140, 40);
            open.Click += delegate { Valve(true, 30); };
            v.Controls.Add(open);

            UiButton close = new UiButton("关闭水阀", Theme.Red);
            close.Location = new Point(176, 88);
            close.Size = new Size(140, 40);
            close.Click += delegate { Valve(false, 0); };
            v.Controls.Add(close);

            UiButton read = new UiButton("读取阀门状态", Theme.CardEdge);
            read.Location = new Point(332, 88);
            read.Size = new Size(150, 40);
            read.Click += delegate { LoadValve(); };
            v.Controls.Add(read);

            v.Controls.Add(Ui.Lbl("安全联锁：降雨、超时（默认 300 秒）、断线时自动关阀。",
                20, 148, 720, 24, 9f, false, Theme.Muted));

            FeaturesForm.AddUsage(this, 516, "天气预报与水阀", 156);
        }

        private TextBox Input(string text, int x, int y, int w)
        {
            TextBox t = new TextBox();
            t.Text = text;
            t.Location = new Point(x, y);
            t.Size = new Size(w, 26);
            t.BackColor = Theme.Input;
            t.ForeColor = Theme.Text;
            t.BorderStyle = BorderStyle.FixedSingle;
            t.Font = new Font("Consolas", 10f);
            return t;
        }

        private NumericUpDown Num(decimal value, int x, int y, int w, int min, int max)
        {
            NumericUpDown n = new NumericUpDown();
            n.Minimum = min;
            n.Maximum = max;
            n.Value = value;
            n.Location = new Point(x, y);
            n.Size = new Size(w, 26);
            n.BackColor = Theme.Input;
            n.ForeColor = Theme.Text;
            n.BorderStyle = BorderStyle.FixedSingle;
            return n;
        }

        private async void LoadWeather()
        {
            double lat, lon;
            if (!double.TryParse(_lat.Text, NumberStyles.Float, CultureInfo.InvariantCulture, out lat) ||
                !double.TryParse(_lon.Text, NumberStyles.Float, CultureInfo.InvariantCulture, out lon))
            {
                _now.Text = "经纬度格式不正确";
                _now.ForeColor = Theme.Red;
                return;
            }
            _now.Text = "正在获取天气…";
            _now.ForeColor = Theme.Muted;
            string url = string.Format(CultureInfo.InvariantCulture,
                "https://api.open-meteo.com/v1/forecast?latitude={0}&longitude={1}" +
                "&current=temperature_2m,relative_humidity_2m,precipitation,weather_code" +
                "&timezone=Asia%2FShanghai", lat, lon);
            try
            {
                string body = await Task.Run(delegate { return Http.Get(url, 15000); });
                Dictionary<string, object> root = _json.Deserialize<Dictionary<string, object>>(body);
                object curObj;
                Dictionary<string, object> cur = root.TryGetValue("current", out curObj)
                    ? curObj as Dictionary<string, object> : null;
                if (cur == null) throw new Exception("返回缺少 current 字段");

                _temp = NumOf(cur, "temperature_2m");
                _hum = NumOf(cur, "relative_humidity_2m");
                _rain = NumOf(cur, "precipitation");
                int code = (int)NumOf(cur, "weather_code");

                _now.Text = string.Format("气温 {0:0.0} ℃   相对湿度 {1:0}%   降水 {2:0.0} mm   天气 {3}",
                    _temp, _hum, _rain, Wmo(code));
                _now.ForeColor = Theme.Text;
                Judge();
            }
            catch (Exception ex)
            {
                _now.Text = "天气获取失败：" + ex.Message;
                _now.ForeColor = Theme.Red;
            }
        }

        private void Judge()
        {
            if (double.IsNaN(_hum)) return;
            bool suggest;
            string why;
            if (_rain > 0)
            {
                suggest = false;
                why = "正在降雨，不需要灌溉";
            }
            else if (_hum < (double)_humidity.Value)
            {
                suggest = true;
                why = string.Format("湿度 {0:0}% 低于阈值 {1}%，建议开阀", _hum, _humidity.Value);
            }
            else
            {
                suggest = false;
                why = string.Format("湿度 {0:0}% 高于阈值 {1}%，暂不需要灌溉", _hum, _humidity.Value);
            }
            if (_temp < (double)_tmin.Value) { suggest = false; why = "气温过低，避免灌溉"; }
            if (_temp > (double)_tmax.Value) { suggest = false; why = "气温过高，建议避开正午灌溉"; }

            _advice.Text = "建议：" + why;
            _advice.ForeColor = suggest ? Theme.Amber : Theme.Muted;
        }

        private void ApplyRule()
        {
            string body = string.Format(CultureInfo.InvariantCulture,
                "{{\"enabled\":{0},\"temp_min\":{1},\"temp_max\":{2},\"humidity_below\":{3},\"respect_rain\":true}}",
                _auto.Checked ? "true" : "false", _tmin.Value, _tmax.Value, _humidity.Value);
            try
            {
                string resp = Http.Post(FeaturesForm.Api(_ip) + "/api/valve/auto", body, 4000);
                _valve.Text = "规则已下发：" + resp;
                _valve.ForeColor = Theme.Green;
            }
            catch (Exception ex)
            {
                _valve.Text = "下发失败：" + Describe(ex);
                _valve.ForeColor = Theme.Red;
            }
        }

        private void Valve(bool open, int seconds)
        {
            string body = string.Format(CultureInfo.InvariantCulture,
                "{{\"open\":{0},\"duration_s\":{1}}}", open ? "true" : "false", seconds);
            try
            {
                string resp = Http.Post(FeaturesForm.Api(_ip) + "/api/valve", body, 4000);
                _valve.Text = (open ? "已开阀" : "已关阀") + "：" + resp;
                _valve.ForeColor = Theme.Green;
            }
            catch (Exception ex)
            {
                _valve.Text = "控制失败：" + Describe(ex);
                _valve.ForeColor = Theme.Red;
            }
        }

        private void LoadValve()
        {
            try
            {
                string body = Http.Get(FeaturesForm.Api(_ip) + "/api/valve", 3000);
                Dictionary<string, object> d = _json.Deserialize<Dictionary<string, object>>(body);
                object v;
                bool open = d.TryGetValue("open", out v) && Convert.ToBoolean(v);
                string reason = d.TryGetValue("reason", out v) ? Convert.ToString(v) : "";
                _valve.Text = string.Format("当前{0}　{1}", open ? "开阀" : "关阀", reason);
                _valve.ForeColor = open ? Theme.Green : Theme.Muted;
            }
            catch (Exception ex)
            {
                _valve.Text = "读取失败：" + Describe(ex);
                _valve.ForeColor = Theme.Red;
            }
        }

        static double NumOf(Dictionary<string, object> d, string k)
        {
            object v;
            if (!d.TryGetValue(k, out v) || v == null) return 0;
            try { return Convert.ToDouble(v, CultureInfo.InvariantCulture); } catch { return 0; }
        }

        static string Describe(Exception ex)
        {
            WebException wex = ex as WebException;
            if (wex != null)
            {
                HttpWebResponse r = wex.Response as HttpWebResponse;
                if (r != null && (int)r.StatusCode == 404) return "固件不支持（404）";
            }
            return ex.Message;
        }

        static string Wmo(int code)
        {
            if (code == 0) return "晴";
            if (code <= 3) return "多云";
            if (code <= 48) return "雾";
            if (code <= 57) return "毛毛雨";
            if (code <= 67) return "雨";
            if (code <= 77) return "雪";
            if (code <= 82) return "阵雨";
            if (code <= 86) return "阵雪";
            return "雷雨";
        }
    }
}
