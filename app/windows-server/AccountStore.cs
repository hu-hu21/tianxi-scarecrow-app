using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Web.Script.Serialization;

namespace ScarecrowServer
{
    /// <summary>注册用户。密码只保存 PBKDF2 派生值，设备字段保存用户当前选择的设备。</summary>
    class Account
    {
        public string User = "";
        public string Salt = "";
        public string Hash = "";
        public string Display = "";
        public string Device = "";
        public DateTime Created = DateTime.Now;
    }

    class TokenInfo
    {
        public string User = "";
        public DateTime Expires = DateTime.Now;
    }

    /// <summary>
    /// 账号与设备归属。服务端同时承担多客户接入：每个用户可添加自己的硬件，
    /// 自定义硬件通过设备密钥向服务端上报数据，客户端只登录服务端即可读取。
    /// </summary>
    static class AccountStore
    {
        public static readonly object Gate = new object();
        public static string FilePath =
            Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "accounts.cfg");

        private static readonly List<Account> _accounts = new List<Account>();
        private static readonly ConcurrentDictionary<string, TokenInfo> _tokens =
            new ConcurrentDictionary<string, TokenInfo>(StringComparer.Ordinal);

        private static List<Device> _devices = new List<Device>();
        private static Action _saveDevices;
        private static readonly JavaScriptSerializer Json = new JavaScriptSerializer();

        public static int Count
        {
            get { lock (Gate) return _accounts.Count; }
        }

        public static void Init(List<Device> devices, Action saveDevices)
        {
            _devices = devices;
            _saveDevices = saveDevices;
            Load();
        }

        // ------------------------------------------------------------ 持久化

        private static void Load()
        {
            lock (Gate)
            {
                _accounts.Clear();
                if (!File.Exists(FilePath)) return;
                try
                {
                    foreach (string raw in File.ReadAllLines(FilePath, Encoding.UTF8))
                    {
                        string line = raw.Trim();
                        if (line.Length == 0 || line.StartsWith("#")) continue;
                        string[] p = line.Split('|');
                        if (p.Length < 3) continue;
                        Account a = new Account();
                        a.User = p[0].Trim();
                        a.Salt = p[1].Trim();
                        a.Hash = p[2].Trim();
                        a.Display = p.Length > 3 ? Decode(p[3]) : a.User;
                        a.Device = p.Length > 4 ? Decode(p[4]) : "";
                        long ticks;
                        if (p.Length > 5 && long.TryParse(p[5], out ticks))
                            a.Created = new DateTime(ticks);
                        if (a.User.Length > 0) _accounts.Add(a);
                    }
                }
                catch { }
            }
        }

        private static void SaveLocked()
        {
            try
            {
                StringBuilder sb = new StringBuilder();
                sb.Append("# 稻草人驱鸟控制器账号文件：user|salt|hash|display|device|created\n");
                foreach (Account a in _accounts)
                {
                    sb.Append(a.User).Append('|').Append(a.Salt).Append('|').Append(a.Hash)
                      .Append('|').Append(Encode(a.Display)).Append('|').Append(Encode(a.Device))
                      .Append('|').Append(a.Created.Ticks.ToString(CultureInfo.InvariantCulture))
                      .Append('\n');
                }
                File.WriteAllText(FilePath, sb.ToString(), new UTF8Encoding(false));
            }
            catch { }
        }

        private static string Encode(string s)
        {
            return Convert.ToBase64String(Encoding.UTF8.GetBytes(s ?? ""));
        }

        private static string Decode(string s)
        {
            try { return Encoding.UTF8.GetString(Convert.FromBase64String(s)); }
            catch { return s ?? ""; }
        }

        // ------------------------------------------------------------ 密码与令牌

        private static string NewSalt()
        {
            byte[] b = new byte[16];
            using (RandomNumberGenerator rng = RandomNumberGenerator.Create()) rng.GetBytes(b);
            return Convert.ToBase64String(b);
        }

        private static string HashPassword(string password, string salt64)
        {
            byte[] salt = Convert.FromBase64String(salt64);
            using (Rfc2898DeriveBytes pb = new Rfc2898DeriveBytes(password ?? "", salt, 12000))
            {
                return Convert.ToBase64String(pb.GetBytes(32));
            }
        }

        private static bool SameHash(string a, string b)
        {
            if (a == null || b == null || a.Length != b.Length) return false;
            int diff = 0;
            for (int i = 0; i < a.Length; i++) diff |= a[i] ^ b[i];
            return diff == 0;
        }

        private static string NewTokenLocked(Account a)
        {
            string token = Guid.NewGuid().ToString("N") + Guid.NewGuid().ToString("N");
            _tokens[token] = new TokenInfo { User = a.User, Expires = DateTime.Now.AddDays(7) };
            return token;
        }

        // ------------------------------------------------------------ 注册登录

        public static string Register(string user, string password, string display, out string error)
        {
            error = null;
            user = (user ?? "").Trim();
            password = password ?? "";
            display = (display ?? "").Trim();
            if (user.Length < 3 || user.Length > 32)
            {
                error = "用户名长度需为 3-32 位";
                return null;
            }
            if (user.IndexOf('|') >= 0 || user.IndexOf(' ') >= 0)
            {
                error = "用户名不能包含空格或竖线";
                return null;
            }
            if (password.Length < 6 || password.Length > 64)
            {
                error = "密码长度需为 6-64 位";
                return null;
            }

            lock (Gate)
            {
                if (FindLocked(user) != null)
                {
                    error = "用户名已存在，请直接登录";
                    return null;
                }
                Account a = new Account();
                a.User = user;
                a.Display = display.Length == 0 ? user : display;
                a.Salt = NewSalt();
                a.Hash = HashPassword(password, a.Salt);
                a.Created = DateTime.Now;
                _accounts.Add(a);
                SaveLocked();
                return NewTokenLocked(a);
            }
        }

        public static string Login(string user, string password, out Account account, out string error)
        {
            account = null;
            error = null;
            lock (Gate)
            {
                Account a = FindLocked((user ?? "").Trim());
                if (a == null || !SameHash(a.Hash, HashPassword(password ?? "", a.Salt)))
                {
                    error = "用户名或密码错误";
                    return null;
                }
                account = a;
                return NewTokenLocked(a);
            }
        }

        public static Account Auth(string token)
        {
            if (string.IsNullOrEmpty(token)) return null;
            TokenInfo ti;
            if (!_tokens.TryGetValue(token, out ti)) return null;
            if (ti.Expires < DateTime.Now)
            {
                TokenInfo removed;
                _tokens.TryRemove(token, out removed);
                return null;
            }
            lock (Gate) return FindLocked(ti.User);
        }

        public static void Logout(string token)
        {
            if (string.IsNullOrEmpty(token)) return;
            TokenInfo removed;
            _tokens.TryRemove(token, out removed);
        }

        private static Account FindLocked(string user)
        {
            foreach (Account a in _accounts)
                if (string.Equals(a.User, user, StringComparison.OrdinalIgnoreCase)) return a;
            return null;
        }

        public static Account AccountOf(string user)
        {
            lock (Gate) return FindLocked(user);
        }

        // ------------------------------------------------------------ 设备

        public static List<Device> DevicesFor(string user)
        {
            List<Device> list = new List<Device>();
            lock (Gate)
            {
                foreach (Device d in _devices)
                {
                    if (d.Owner.Length == 0 || string.Equals(d.Owner, user, StringComparison.OrdinalIgnoreCase))
                        list.Add(d);
                }
            }
            return list;
        }

        public static Device FindDevice(string reference)
        {
            if (string.IsNullOrEmpty(reference)) return null;
            string r = reference.Trim();
            lock (Gate)
            {
                foreach (Device d in _devices)
                {
                    if (string.Equals(d.Ref, r, StringComparison.OrdinalIgnoreCase)) return d;
                    if (string.Equals(d.Address, r, StringComparison.OrdinalIgnoreCase)) return d;
                    if (string.Equals(d.Name, r, StringComparison.OrdinalIgnoreCase)) return d;
                    if (d.Key.Length > 0 && string.Equals(d.Key, r, StringComparison.OrdinalIgnoreCase)) return d;
                }
            }
            return null;
        }

        public static Device FindByKey(string key)
        {
            if (string.IsNullOrEmpty(key)) return null;
            lock (Gate)
            {
                foreach (Device d in _devices)
                    if (d.Key.Length > 0 && string.Equals(d.Key, key, StringComparison.OrdinalIgnoreCase))
                        return d;
            }
            return null;
        }

        public static string AddDevice(string user, string name, string address, string key,
            bool custom, out Device created, out string error)
        {
            created = null;
            error = null;
            name = (name ?? "").Trim();
            address = (address ?? "").Trim();
            key = (key ?? "").Trim();
            if (address.Length == 0 && !custom)
            {
                error = "标准硬件需填写设备地址，例如 192.168.1.66:80";
                return null;
            }
            if (custom && key.Length == 0) key = Guid.NewGuid().ToString("N").Substring(0, 16);
            if (key.Length > 0 && key.Length < 6)
            {
                error = "设备密钥至少 6 位";
                return null;
            }

            lock (Gate)
            {
                Device found = null;
                foreach (Device d in _devices)
                {
                    bool sameAddr = address.Length > 0 &&
                        string.Equals(d.Address, address, StringComparison.OrdinalIgnoreCase);
                    bool sameKey = key.Length > 0 &&
                        string.Equals(d.Key, key, StringComparison.OrdinalIgnoreCase);
                    if (sameAddr || sameKey) { found = d; break; }
                }
                if (found != null && found.Owner.Length > 0 &&
                    !string.Equals(found.Owner, user, StringComparison.OrdinalIgnoreCase))
                {
                    error = "该设备已被其他账号绑定";
                    return null;
                }
                if (found == null)
                {
                    found = new Device();
                    _devices.Add(found);
                }
                found.Name = name.Length == 0
                    ? (address.Length > 0 ? address : "我的硬件")
                    : name;
                found.Address = address;
                found.Key = key;
                found.Custom = custom || address.Length == 0;
                found.Owner = user;
                found.LastSeen = DateTime.Now;

                Account a = FindLocked(user);
                if (a != null && a.Device.Length == 0)
                {
                    a.Device = found.Ref;
                    SaveLocked();
                }
                if (_saveDevices != null) _saveDevices();
                created = found;
                return found.Ref;
            }
        }

        public static bool SelectDevice(string user, string reference, out string error)
        {
            error = null;
            lock (Gate)
            {
                Device d = null;
                foreach (Device x in _devices)
                {
                    if (string.Equals(x.Ref, reference, StringComparison.OrdinalIgnoreCase) ||
                        string.Equals(x.Address, reference, StringComparison.OrdinalIgnoreCase) ||
                        string.Equals(x.Name, reference, StringComparison.OrdinalIgnoreCase))
                    {
                        d = x;
                        break;
                    }
                }
                if (d == null)
                {
                    error = "设备不存在";
                    return false;
                }
                if (d.Owner.Length > 0 &&
                    !string.Equals(d.Owner, user, StringComparison.OrdinalIgnoreCase))
                {
                    error = "该设备属于其他账号";
                    return false;
                }
                Account a = FindLocked(user);
                if (a != null)
                {
                    a.Device = d.Ref;
                    SaveLocked();
                }
                return true;
            }
        }

        public static bool CanUse(Account account, Device device)
        {
            if (device == null) return false;
            if (account == null) return false;
            return device.Owner.Length == 0 ||
                string.Equals(device.Owner, account.User, StringComparison.OrdinalIgnoreCase);
        }

        public static string SerializeDevice(Device d)
        {
            Dictionary<string, object> o = new Dictionary<string, object>();
            o["name"] = d.Name;
            o["ref"] = d.Ref;
            o["address"] = d.Address;
            o["key"] = d.Key;
            o["custom"] = d.Custom;
            o["owner"] = d.Owner;
            o["current"] = d.Current;
            o["online"] = d.Online;
            o["reports"] = d.Reports;
            o["last_seen"] = d.LastSeen.ToString("yyyy-MM-dd HH:mm:ss");
            return Json.Serialize(o);
        }
    }
}
