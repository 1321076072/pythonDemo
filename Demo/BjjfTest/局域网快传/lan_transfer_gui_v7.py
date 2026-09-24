#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
局域网直连传输工具 - GUI 版 v7.0
功能：v6全部 + 拖拽发送 + 系统通知 + 设备自动发现 + 深色主题 + 差异同步 + 速度曲线
依赖：pip install cryptography pystray pillow matplotlib plyer tkinterdnd2 qrcode
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import re
import socket
import threading
import os
import sys
import subprocess
import struct
import json
import zipfile
import time
import select
import hashlib
import base64
import ctypes
from datetime import datetime

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    DND_FILES = None
    TkinterDnD = None
    HAS_DND = False

# cryptography 延迟加载，避免拖慢启动
_crypto = None

def _load_crypto():
    global _crypto
    if _crypto is None:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.primitives import padding, hashes
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        _crypto = {
            "Cipher": Cipher, "algorithms": algorithms, "modes": modes,
            "padding": padding, "hashes": hashes, "default_backend": default_backend,
            "PBKDF2HMAC": PBKDF2HMAC,
        }
    return _crypto
# ==================== 配置 ====================
ROLE_RECEIVER_IP = "192.168.99.1"
ROLE_SENDER_IP   = "192.168.99.2"
DEFAULT_PORT     = 5000
CHUNK_SIZE       = 256 * 1024  # 局域网用大块，64K 会白白增加系统调用次数
MAGIC_HEADER     = b"LANT2024"
DISCOVER_MAGIC   = b"LANT_DISCOVER_v8"
DISCOVER_PORT    = DEFAULT_PORT + 100  # 固定发现口，与传输端口解耦
DISCOVER_QUERY   = 0
DISCOVER_HERE    = 1
DISCOVER_BEACON  = 3.0   # 秒：周期宣告
DISCOVER_TTL     = 12.0  # 秒：对端失联过期
SKIP_OFFSET      = (1 << 64) - 1  # 接收端：内容未变化，跳过正文
HISTORY_FILE     = os.path.join(os.path.expanduser("~"), ".lan_transfer_history.json")

# ==================== 全局进度 ====================
global_progress = {
    "active": False, "filename": "", "pct": 0.0, "speed": 0.0,
    "sent": 0, "total": 0, "direction": "", "start_time": 0,
    "speed_history": [],  # 速度曲线数据
}

# ==================== 主题系统 ====================
THEMES = {
    "light": {
        "bg": "#f3f3f3", "fg": "#1a1a1a", "accent": "#0078d4",
        "panel": "#ffffff", "border": "#d0d0d0", "success": "#107c10",
        "warning": "#ff8c00", "error": "#d13438", "muted": "#666666",
        "log_bg": "#ffffff", "log_fg": "#1a1a1a",
        "hover": "#e8f2fc", "select": "#cce4f7", "on_accent": "#ffffff",
    },
    "dark": {
        "bg": "#1e1e2e", "fg": "#cdd6f4", "accent": "#89b4fa",
        "panel": "#313244", "border": "#45475a", "success": "#a6e3a1",
        "warning": "#f9e2af", "error": "#f38ba8", "muted": "#a6adc8",
        "log_bg": "#11111b", "log_fg": "#cdd6f4",
        "hover": "#45475a", "select": "#585b70", "on_accent": "#1e1e2e",
    },
}
current_theme = "light"

def _paint_native(widget, t):
    """tk 原生控件不吃 ttk.Style，单独上色。"""
    for child in widget.winfo_children():
        cls = child.winfo_class()
        try:
            if cls == "Listbox":
                child.configure(
                    bg=t["panel"], fg=t["fg"],
                    selectbackground=t["accent"], selectforeground=t["on_accent"],
                    highlightbackground=t["border"], highlightcolor=t["accent"],
                    highlightthickness=1, relief="flat", bd=0,
                    activestyle="none",
                )
            elif cls == "Text":
                child.configure(
                    bg=t["log_bg"], fg=t["log_fg"], insertbackground=t["accent"],
                    selectbackground=t["select"], selectforeground=t["fg"],
                    relief="flat", highlightthickness=1,
                    highlightbackground=t["border"], highlightcolor=t["accent"],
                    padx=6, pady=4,
                )
        except tk.TclError:
            pass
        _paint_native(child, t)

def apply_theme(root, theme_name):
    global current_theme
    current_theme = theme_name
    t = THEMES[theme_name]
    root.configure(bg=t["bg"])
    style = ttk.Style()
    style.theme_use("clam")
    font_ui = ("Microsoft YaHei UI", 9)
    style.configure(".", background=t["bg"], foreground=t["fg"], font=font_ui)
    style.configure("TFrame", background=t["bg"])
    style.configure("TLabel", background=t["bg"], foreground=t["fg"])
    style.configure("Muted.TLabel", background=t["bg"], foreground=t["muted"])
    style.configure("Title.TLabel", font=("Microsoft YaHei UI", 15, "bold"), background=t["bg"], foreground=t["accent"])
    style.configure(
        "TButton", background=t["panel"], foreground=t["fg"],
        bordercolor=t["border"], lightcolor=t["panel"], darkcolor=t["panel"],
        padding=(10, 4), focusthickness=0, focuscolor=t["panel"],
    )
    style.map(
        "TButton",
        background=[("pressed", t["select"]), ("active", t["hover"]), ("disabled", t["bg"])],
        foreground=[("disabled", t["muted"])],
        bordercolor=[("active", t["accent"])],
    )
    style.configure("Accent.TButton", background=t["accent"], foreground=t["on_accent"], bordercolor=t["accent"], padding=(12, 4))
    style.map(
        "Accent.TButton",
        background=[("pressed", t["select"]), ("active", t["hover"])],
        foreground=[("pressed", t["fg"]), ("active", t["fg"])],
    )
    for name in ("TCheckbutton", "TRadiobutton"):
        style.configure(name, background=t["bg"], foreground=t["fg"])
        style.map(name, background=[("active", t["bg"])], foreground=[("disabled", t["muted"])])
    style.configure("TLabelframe", background=t["bg"], bordercolor=t["border"], relief="solid", borderwidth=1)
    style.configure("TLabelframe.Label", background=t["bg"], foreground=t["accent"], font=("Microsoft YaHei UI", 9, "bold"))
    style.configure("TEntry", fieldbackground=t["panel"], foreground=t["fg"], bordercolor=t["border"], insertcolor=t["fg"], padding=3)
    style.map("TEntry", fieldbackground=[("disabled", t["bg"])], foreground=[("disabled", t["muted"])])
    style.configure("TCombobox", fieldbackground=t["panel"], foreground=t["fg"], bordercolor=t["border"], arrowcolor=t["fg"], padding=3)
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", t["panel"]), ("disabled", t["bg"])],
        foreground=[("readonly", t["fg"]), ("disabled", t["muted"])],
        selectbackground=[("readonly", t["panel"])],
        selectforeground=[("readonly", t["fg"])],
    )
    style.configure("Vertical.TScrollbar", background=t["panel"], troughcolor=t["bg"], bordercolor=t["bg"], arrowcolor=t["muted"])
    style.map("Vertical.TScrollbar", background=[("active", t["hover"])])
    root.option_add("*TCombobox*Listbox.background", t["panel"])
    root.option_add("*TCombobox*Listbox.foreground", t["fg"])
    root.option_add("*TCombobox*Listbox.selectBackground", t["accent"])
    root.option_add("*TCombobox*Listbox.selectForeground", t["on_accent"])
    _paint_native(root, t)
    return t

# ==================== 系统通知 ====================
def send_notification(title, message, icon_type="info"):
    """跨平台系统通知"""
    try:
        if sys.platform == "win32":
            # 任务栏闪烁
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            ctypes.windll.user32.FlashWindow(hwnd, True)
            # 系统托盘通知
            try:
                from win10toast import ToastNotifier
                toaster = ToastNotifier()
                toaster.show_toast(title, message, duration=5, threaded=True)
            except ImportError:
                # fallback: messagebox
                pass
        else:
            # Linux/macOS: notify-send
            subprocess.run(["notify-send", title, message], capture_output=True)
    except Exception:
        pass

# ==================== 网络工具 ====================
def _decode_console(raw: bytes) -> str:
    """PowerShell 重定向 stdout 是 UTF-16；控制台中文则是 GBK。"""
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16")
    if b"\x00" in raw[:80]:
        return raw.decode("utf-16-le", errors="replace")
    for enc in ("utf-8", "gbk"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")

_iface_cache = {"ts": 0.0, "list": None}

def get_ethernet_interfaces(force=False):
    now = time.time()
    if not force and _iface_cache["list"] is not None and now - _iface_cache["ts"] < 30:
        return list(_iface_cache["list"])
    interfaces = []
    if sys.platform == "win32":
        try:
            raw = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command",
                 "Get-NetAdapter | Where-Object Status -eq 'Up' | Select-Object -ExpandProperty Name"],
                timeout=8,
            )
            out = _decode_console(raw)
            interfaces = [ln.strip() for ln in out.splitlines() if ln.strip()]
        except Exception:
            interfaces = []
    else:
        try:
            out = subprocess.check_output("ip link show", shell=True, text=True)
            for line in out.split("\n"):
                if ": " in line and "state UP" in line:
                    iface = line.split(":")[1].split("@")[0].strip()
                    if iface != "lo":
                        interfaces.append(iface)
        except Exception:
            interfaces = []
    interfaces = interfaces or (["以太网"] if sys.platform == "win32" else ["eth0"])
    _iface_cache["ts"] = now
    _iface_cache["list"] = interfaces
    return list(interfaces)
def set_static_ip(iface, ip):
    if sys.platform == "win32":
        cmd = f'netsh interface ip set address name="{iface}" static {ip} 255.255.255.0'
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return r.returncode == 0
    r1 = subprocess.run(f"sudo ip addr flush dev {iface}", shell=True, capture_output=True)
    r2 = subprocess.run(f"sudo ip addr add {ip}/24 dev {iface}", shell=True, capture_output=True)
    return r1.returncode == 0 and r2.returncode == 0

def set_dhcp(iface):
    if sys.platform == "win32":
        r = subprocess.run(f'netsh interface ip set address name="{iface}" dhcp', shell=True, capture_output=True, text=True)
        return r.returncode == 0
    r = subprocess.run(f"sudo dhclient {iface}", shell=True, capture_output=True)
    return r.returncode == 0

_local_ips_cache = (0.0, frozenset())

def local_ips():
    """本机 IPv4 集合；短缓存，避免发现循环里反复建 socket。"""
    global _local_ips_cache
    now = time.time()
    ts, cached = _local_ips_cache
    if now - ts < 2.0 and cached:
        return set(cached)
    ips = {"127.0.0.1"}
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.add(info[4][0])
    except OSError:
        pass
    ip = get_local_ip()
    if ip and ip != "未知":
        ips.add(ip)
    _local_ips_cache = (now, frozenset(ips))
    return ips

def broadcast_targets():
    """255.255.255.255 + 各本机 /24 定向广播（多网卡场景更稳）。"""
    addrs = {"255.255.255.255"}
    for ip in local_ips():
        if ip.startswith("127."):
            continue
        parts = ip.split(".")
        if len(parts) == 4 and all(p.isdigit() for p in parts):
            addrs.add(".".join(parts[:3] + ["255"]))
    return addrs

def safe_basename(name):
    name = (name or "unknown").replace("\\", "/").split("/")[-1].strip()
    if name in ("", ".", ".."):
        return "unknown"
    return name

def safe_join(base, name):
    path = os.path.abspath(os.path.join(base, safe_basename(name)))
    base_abs = os.path.abspath(base)
    if os.path.commonpath([base_abs, path]) != base_abs:
        raise ValueError(f"非法文件名: {name}")
    return path

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "未知"

def share_base_url(ip, port):
    """HTTP 共享根链接：手机扫码后浏览器直接打开目录。"""
    return f"http://{ip}:{port}/"

def make_qr_image(url, box_size=8):
    """返回 PIL Image；缺 qrcode/Pillow 时返回 None。"""
    try:
        import qrcode
        from PIL import Image  # noqa: F401 — make_image 需要 Pillow
    except ImportError:
        return None
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    try:
        return qr.make_image(fill_color="black", back_color="white").convert("RGB")
    except ImportError:
        return None

def show_share_qr_window(parent, url, on_close=None):
    """弹窗显示二维码 + 可复制链接。扫码即打开下载页。"""
    win = tk.Toplevel(parent)
    win.title("扫码获取共享链接")
    win.attributes("-topmost", True)
    win.resizable(False, False)

    ttk.Label(win, text="手机扫描二维码，自动打开共享目录", style="Title.TLabel").pack(padx=16, pady=(12, 4))

    photo = None
    img = make_qr_image(url)
    if img is not None:
        from PIL import ImageTk
        photo = ImageTk.PhotoImage(img)
        lbl = ttk.Label(win, image=photo)
        lbl.image = photo  # 防 GC
        lbl.pack(padx=16, pady=4)
    else:
        ttk.Label(
            win, text="未安装 qrcode/Pillow，仅显示链接\npip install qrcode pillow",
            style="Muted.TLabel", justify="center",
        ).pack(padx=16, pady=8)

    url_var = tk.StringVar(value=url)
    entry = ttk.Entry(win, textvariable=url_var, width=42, justify="center")
    entry.pack(padx=16, pady=4, fill="x")
    entry.select_range(0, "end")

    btn_row = ttk.Frame(win)
    btn_row.pack(pady=(4, 12))

    def copy_url():
        win.clipboard_clear()
        win.clipboard_append(url)
        win.update_idletasks()

    ttk.Button(btn_row, text="复制链接", style="Accent.TButton", command=copy_url).pack(side="left", padx=4)
    ttk.Button(btn_row, text="关闭", command=win.destroy).pack(side="left", padx=4)

    def _on_destroy(_event=None):
        if on_close:
            on_close()

    win.bind("<Destroy>", lambda e: _on_destroy() if e.widget is win else None)
    win.update_idletasks()
    # 相对主窗口居中
    try:
        px = parent.winfo_rootx() + (parent.winfo_width() - win.winfo_reqwidth()) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - win.winfo_reqheight()) // 2
        win.geometry(f"+{max(0, px)}+{max(0, py)}")
    except tk.TclError:
        pass
    return win

# ==================== 设备自动发现 ====================
def _discover_pack(kind, tcp_port, name):
    name_b = (name or "").encode("utf-8")[:200]
    return DISCOVER_MAGIC + bytes([kind & 0xFF]) + struct.pack(">H", int(tcp_port) & 0xFFFF) + name_b

def _discover_unpack(data):
    hdr = len(DISCOVER_MAGIC)
    if not data.startswith(DISCOVER_MAGIC) or len(data) < hdr + 3:
        return None
    kind = data[hdr]
    tcp_port = struct.unpack(">H", data[hdr + 1:hdr + 3])[0]
    name = data[hdr + 3:].decode("utf-8", "ignore").strip()
    return kind, tcp_port, name

class DeviceDiscovery:
    """
    固定 UDP 口 DISCOVER_PORT 上做周期宣告 + 点名查询。
    报文自带对方 TCP 传输端口，发送/接收端口不一致也能连上。
    """
    def __init__(self, tcp_port=DEFAULT_PORT, callback=None):
        self.tcp_port = tcp_port
        self.hostname = socket.gethostname()
        self.callback = callback  # callback(ip, name, tcp_port, is_new)
        self.running = False
        self.sock = None
        self.thread = None
        self.discovered = {}  # ip -> {ip, name, port, last_seen}
        self.lock = threading.Lock()
        self._next_beacon = 0.0

    def start(self):
        if self.running:
            return
        self.running = True
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.bind(("0.0.0.0", DISCOVER_PORT))
        sock.settimeout(0.5)
        self.sock = sock
        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()
        self.probe()

    def stop(self):
        self.running = False
        sock = self.sock
        self.sock = None
        if sock:
            try:
                sock.close()
            except OSError:
                pass

    def ensure(self, tcp_port=None):
        if tcp_port is not None:
            self.tcp_port = int(tcp_port)
        if self.running and self.sock:
            return
        self.stop()
        self.start()

    def set_tcp_port(self, tcp_port):
        self.tcp_port = int(tcp_port)

    def _sendto_all(self, payload):
        sock = self.sock
        if not sock:
            return
        for dest in broadcast_targets():
            try:
                sock.sendto(payload, (dest, DISCOVER_PORT))
            except OSError:
                pass

    def _announce(self):
        self._sendto_all(_discover_pack(DISCOVER_HERE, self.tcp_port, self.hostname))

    def _query(self):
        self._sendto_all(_discover_pack(DISCOVER_QUERY, self.tcp_port, self.hostname))

    def probe(self):
        """主动点名：发 QUERY + HERE，立刻露脸并拉对端。"""
        self._announce()
        self._query()

    def _remember(self, ip, name, tcp_port):
        now = time.time()
        with self.lock:
            old = self.discovered.get(ip)
            is_new = old is None
            item = {
                "ip": ip,
                "name": name or (old["name"] if old else ip),
                "port": int(tcp_port) or (old["port"] if old else DEFAULT_PORT),
                "last_seen": now,
            }
            changed = is_new or old["name"] != item["name"] or old["port"] != item["port"]
            self.discovered[ip] = item
        if self.callback and (is_new or changed):
            self.callback(item["ip"], item["name"], item["port"], is_new)
        return is_new

    def _prune(self):
        cutoff = time.time() - DISCOVER_TTL
        with self.lock:
            dead = [ip for ip, v in self.discovered.items() if v["last_seen"] < cutoff]
            for ip in dead:
                del self.discovered[ip]
        return dead

    def _listen_loop(self):
        while self.running:
            now = time.time()
            if now >= self._next_beacon:
                self._announce()
                self._prune()
                self._next_beacon = now + DISCOVER_BEACON
            sock = self.sock
            if not sock:
                break
            try:
                data, addr = sock.recvfrom(1024)
            except socket.timeout:
                continue
            except OSError:
                break
            parsed = _discover_unpack(data)
            if not parsed or addr[0] in local_ips():
                continue
            kind, tcp_port, name = parsed
            if kind == DISCOVER_HERE:
                self._remember(addr[0], name or addr[0], tcp_port)
            elif kind == DISCOVER_QUERY:
                # 被点名：单播回 HERE，并顺便记住对方
                self._remember(addr[0], name or addr[0], tcp_port)
                try:
                    sock.sendto(
                        _discover_pack(DISCOVER_HERE, self.tcp_port, self.hostname),
                        addr,
                    )
                except OSError:
                    pass

    def snapshot(self):
        """当前仍在 TTL 内的对端列表。"""
        self._prune()
        with self.lock:
            return [
                {"ip": v["ip"], "name": v["name"], "port": v["port"]}
                for v in sorted(self.discovered.values(), key=lambda x: x["ip"])
            ]

    def discover_once(self, wait=1.2):
        started = time.time()
        self.probe()
        time.sleep(wait)
        with self.lock:
            return [
                {"ip": v["ip"], "name": v["name"], "port": v["port"]}
                for v in sorted(self.discovered.values(), key=lambda x: x["ip"])
                if v["last_seen"] >= started - 0.5
            ]

# ==================== AES 加密 ====================
class AESCipher:
    def __init__(self, password, salt=None):
        c = _load_crypto()
        self.salt = salt if salt is not None else os.urandom(16)
        kdf = c["PBKDF2HMAC"](
            algorithm=c["hashes"].SHA256(), length=32, salt=self.salt,
            iterations=100000, backend=c["default_backend"](),
        )
        self.key = kdf.derive(password.encode("utf-8"))

    def encrypt(self, data):
        c = _load_crypto()
        iv = os.urandom(16)
        cipher = c["Cipher"](c["algorithms"].AES(self.key), c["modes"].CBC(iv), backend=c["default_backend"]())
        encryptor = cipher.encryptor()
        padder = c["padding"].PKCS7(128).padder()
        padded = padder.update(data) + padder.finalize()
        ct = encryptor.update(padded) + encryptor.finalize()
        return iv + ct

    def decrypt(self, data):
        c = _load_crypto()
        iv = data[:16]
        ct = data[16:]
        cipher = c["Cipher"](c["algorithms"].AES(self.key), c["modes"].CBC(iv), backend=c["default_backend"]())
        decryptor = cipher.decryptor()
        padded = decryptor.update(ct) + decryptor.finalize()
        unpadder = c["padding"].PKCS7(128).unpadder()
        return unpadder.update(padded) + unpadder.finalize()

    def encrypt_stream(self, in_file, out_file, chunk_size=CHUNK_SIZE, progress_callback=None):
        c = _load_crypto()
        iv = os.urandom(16)
        out_file.write(iv)
        cipher = c["Cipher"](c["algorithms"].AES(self.key), c["modes"].CBC(iv), backend=c["default_backend"]())
        encryptor = cipher.encryptor()
        padder = c["padding"].PKCS7(128).padder()
        total = os.path.getsize(in_file.name)
        done = 0
        while True:
            chunk = in_file.read(chunk_size)
            if not chunk:
                break
            padded = padder.update(chunk)
            if padded:
                ct = encryptor.update(padded)
                out_file.write(ct)
            done += len(chunk)
            if progress_callback:
                progress_callback(done, total)
        padded = padder.finalize()
        if padded:
            ct = encryptor.update(padded)
            out_file.write(ct)
        ct = encryptor.finalize()
        if ct:
            out_file.write(ct)

    def decrypt_stream(self, in_file, out_file, chunk_size=CHUNK_SIZE, progress_callback=None):
        c = _load_crypto()
        iv = in_file.read(16)
        cipher = c["Cipher"](c["algorithms"].AES(self.key), c["modes"].CBC(iv), backend=c["default_backend"]())
        decryptor = cipher.decryptor()
        unpadder = c["padding"].PKCS7(128).unpadder()
        total = os.path.getsize(in_file.name)
        done = 16
        while True:
            chunk = in_file.read(chunk_size)
            if not chunk:
                break
            padded = decryptor.update(chunk)
            if padded:
                try:
                    data = unpadder.update(padded)
                    if data:
                        out_file.write(data)
                except ValueError:
                    pass
            done += len(chunk)
            if progress_callback:
                progress_callback(done, total)
        try:
            padded = decryptor.finalize()
            if padded:
                data = unpadder.update(padded)
                if data:
                    out_file.write(data)
            data = unpadder.finalize()
            if data:
                out_file.write(data)
        except Exception:
            pass

# ==================== 协议 ====================
def recv_exact(sock, n):
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            return None
        buf.extend(chunk)
    return bytes(buf)

def send_protocol_header(sock, ptype, meta_dict):
    meta_json = json.dumps(meta_dict, ensure_ascii=False).encode("utf-8")
    header = MAGIC_HEADER + ptype.encode("ascii") + struct.pack(">I", len(meta_json)) + meta_json
    sock.sendall(header)

def recv_protocol_header(sock):
    magic = recv_exact(sock, len(MAGIC_HEADER))
    if not magic or magic != MAGIC_HEADER:
        return None, None
    ptype = recv_exact(sock, 1)
    len_b = recv_exact(sock, 4)
    if not ptype or not len_b:
        return None, None
    json_len = struct.unpack(">I", len_b)[0]
    if json_len > 8 * 1024 * 1024:
        return None, None
    meta_b = recv_exact(sock, json_len)
    if not meta_b:
        return None, None
    return ptype.decode("ascii"), json.loads(meta_b.decode("utf-8"))

# ==================== 限速器 ====================
class RateLimiter:
    def __init__(self, max_mbps=0):
        self.max_mbps = max_mbps
        self.bucket_bytes = max_mbps * 1024 * 1024 if max_mbps > 0 else 0
        self.tokens = self.bucket_bytes
        self.last_refill = time.time()
        self.lock = threading.Lock()

    def update_limit(self, max_mbps):
        with self.lock:
            self.max_mbps = max_mbps
            if max_mbps > 0:
                self.bucket_bytes = max_mbps * 1024 * 1024
                self.tokens = min(self.tokens, self.bucket_bytes) if self.tokens > 0 else self.bucket_bytes
            else:
                self.bucket_bytes = 0
                self.tokens = 0

    def consume(self, bytes_count):
        if self.max_mbps <= 0 or bytes_count <= 0:
            return
        rate = self.max_mbps * 1024 * 1024
        while True:
            with self.lock:
                now = time.time()
                elapsed = now - self.last_refill
                if elapsed > 0:
                    self.tokens = min(self.bucket_bytes, self.tokens + elapsed * rate)
                    self.last_refill = now
                if self.tokens >= bytes_count:
                    self.tokens -= bytes_count
                    return
                wait = (bytes_count - self.tokens) / rate
            time.sleep(min(max(wait, 0.0), 0.05))

# ==================== 哈希计算 ====================
def calc_hash(filepath, algo="md5", progress_callback=None):
    h = hashlib.md5() if algo == "md5" else hashlib.sha256()
    total = os.path.getsize(filepath)
    done = 0
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            h.update(chunk)
            done += len(chunk)
            if progress_callback and total > 0:
                progress_callback(done, total)
    return h.hexdigest()

# ==================== 文件差异同步 ====================
def compute_file_signature(filepath):
    """计算文件签名：大小 + mtime + 快速哈希（前64KB + 后64KB）"""
    stat = os.stat(filepath)
    size = stat.st_size
    mtime = stat.st_mtime

    # 快速哈希：头尾各64KB
    h = hashlib.md5()
    with open(filepath, "rb") as f:
        head = f.read(65536)
        h.update(head)
        if size > 131072:
            f.seek(-65536, 2)
            tail = f.read(65536)
            h.update(tail)

    return {
        "size": size,
        "mtime": mtime,
        "quick_hash": h.hexdigest(),
    }

def files_are_same(local_path, remote_sig):
    """比对本地文件和远程签名，判断是否需要传输"""
    if not remote_sig or not os.path.isfile(local_path):
        return False
    local_sig = compute_file_signature(local_path)
    return local_sig["size"] == remote_sig.get("size") and local_sig["quick_hash"] == remote_sig.get("quick_hash")

def compute_tree_signature(folder):
    """目录签名：每个文件的相对路径 + 大小 + 头尾哈希。"""
    h = hashlib.md5()
    total = 0
    for root, dirs, files in os.walk(folder):
        dirs.sort()
        files.sort()
        for name in files:
            fp = os.path.join(root, name)
            rel = os.path.relpath(fp, folder).replace("\\", "/")
            sig = compute_file_signature(fp)
            total += sig["size"]
            h.update(f"{rel}:{sig['size']}:{sig['quick_hash']}\n".encode())
    return {"size": total, "quick_hash": h.hexdigest(), "tree": True}

def content_same(path, remote_sig):
    if not remote_sig:
        return False
    if remote_sig.get("tree"):
        return os.path.isdir(path) and compute_tree_signature(path)["quick_hash"] == remote_sig.get("quick_hash")
    return files_are_same(path, remote_sig)

def report_progress(log_callback, prefix, name, done, total, last_log, last_done):
    now = time.time()
    if total <= 0 or now - last_log < 0.5:
        return last_log, last_done
    speed = (done - last_done) / (now - last_log) / 1024 / 1024
    pct = done / total * 100
    global_progress["pct"] = pct
    global_progress["speed"] = speed
    global_progress["sent"] = done
    global_progress["speed_history"].append(speed)
    if len(global_progress["speed_history"]) > 300:
        del global_progress["speed_history"][:-300]
    log_callback(
        f"{prefix} {name}: {done/1024/1024:.1f}/{total/1024/1024:.1f} MB ({pct:.0f}%) {speed:.1f} MB/s",
        raw=True,
    )
    return now, done

def recv_payload(conn, path, offset, total, stop_event, rate_limiter, log_callback, label):
    received = offset
    last_log, last_done = time.time(), received
    mode = "r+b" if offset and os.path.exists(path) else "wb"
    with open(path, mode) as f:
        if offset:
            f.seek(offset)
            f.truncate()
        while received < total:
            if stop_event.is_set():
                return received, False
            ready, _, _ = select.select([conn], [], [], 0.5)
            if not ready:
                continue
            data = conn.recv(min(CHUNK_SIZE, total - received))
            if not data:
                return received, False
            f.write(data)
            received += len(data)
            rate_limiter.consume(len(data))
            last_log, last_done = report_progress(
                log_callback, "📥", label, received, total, last_log, last_done
            )
    return received, True

# ==================== 历史记录 ====================
class TransferHistory:
    def __init__(self):
        self.records = []
        self._loaded = False

    def _ensure_loaded(self):
        if self._loaded:
            return
        self._loaded = True
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    self.records = json.load(f)
            except Exception:
                self.records = []

    def load(self):
        self._loaded = False
        self._ensure_loaded()

    def save(self):
        self._ensure_loaded()
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.records, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def add(self, direction, filename, size, status, verify_result="", speed="", encrypted=False):
        self._ensure_loaded()
        record = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "direction": direction, "filename": filename, "size": size,
            "status": status, "verify": verify_result, "speed": speed, "encrypted": encrypted
        }
        self.records.insert(0, record)
        if len(self.records) > 500:
            self.records = self.records[:500]
        self.save()

    def get_all(self):
        self._ensure_loaded()
        return self.records

    def clear(self):
        self._loaded = True
        self.records = []
        self.save()

# ==================== 悬浮进度球 ====================
class FloatingProgressBall:
    def __init__(self):
        self.root = None
        self.canvas = None
        self.running = False
        self.thread = None

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._create_window, daemon=True)
        self.thread.start()

    def _create_window(self):
        self.root = tk.Tk()
        self.root.title("传输进度")
        self.root.geometry("160x160+20+20")
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.85)
        self.root.overrideredirect(True)
        self.root.configure(bg="black")
        self.root.bind("<Button-1>", self._on_press)
        self.root.bind("<B1-Motion>", self._on_drag)
        self.canvas = tk.Canvas(self.root, width=160, height=160, bg="black", highlightthickness=0)
        self.canvas.pack()
        close_btn = tk.Label(self.root, text="×", fg="white", bg="black", font=("Arial", 14, "bold"), cursor="hand2")
        close_btn.place(x=140, y=2, width=18, height=18)
        close_btn.bind("<Button-1>", lambda e: self.hide())
        self._update_loop()

    def _on_press(self, event):
        self.root.x = event.x
        self.root.y = event.y

    def _on_drag(self, event):
        x = self.root.winfo_x() + (event.x - self.root.x)
        y = self.root.winfo_y() + (event.y - self.root.y)
        self.root.geometry(f"+{x}+{y}")

    def _update_loop(self):
        if not self.running or not self.root:
            return
        self._draw()
        self.root.after(500, self._update_loop)

    def _draw(self):
        self.canvas.delete("all")
        gp = global_progress
        if not gp["active"]:
            self.canvas.create_oval(30, 30, 130, 130, outline="#444", width=2, fill="#1a1a2e")
            self.canvas.create_text(80, 75, text="空闲", fill="#888", font=("Arial", 11))
            return
        pct = gp["pct"]
        speed = gp["speed"]
        filename = gp["filename"]
        direction = gp["direction"]
        self.canvas.create_oval(10, 10, 150, 150, outline="#333", width=2, fill="#0f0f23")
        if pct > 0:
            import math
            angle = pct / 100.0 * 360
            extent = min(angle, 359.9)
            self.canvas.create_arc(10, 10, 150, 150, start=90, extent=-extent, fill="#00d4aa", outline="")
        self.canvas.create_text(80, 60, text=f"{pct:.0f}%", fill="white", font=("Arial", 18, "bold"))
        speed_str = f"{speed:.1f} MB/s" if speed < 1000 else f"{speed/1024:.1f} GB/s"
        self.canvas.create_text(80, 85, text=speed_str, fill="#00d4aa", font=("Arial", 9))
        disp_name = filename if len(filename) <= 12 else filename[:10] + ".."
        self.canvas.create_text(80, 105, text=disp_name, fill="#aaa", font=("Arial", 8))
        icon = "↑" if direction == "send" else "↓" if direction == "recv" else ""
        self.canvas.create_text(80, 125, text=icon, fill="#ff6b6b", font=("Arial", 14, "bold"))

    def hide(self):
        if self.root:
            self.root.destroy()
            self.root = None
        self.running = False

    def show(self):
        if not self.running:
            self.start()

# ==================== 速度曲线窗口 ====================
class SpeedChartWindow:
    def __init__(self):
        self.root = None
        self.running = False
        self.fig = None
        self.ax = None
        self.line = None
        self.canvas = None

    def show(self):
        if self.running and self.root:
            self.root.lift()
            return
        self.running = True
        threading.Thread(target=self._create_window, daemon=True).start()

    def _create_window(self):
        try:
            import matplotlib
            matplotlib.use("TkAgg")
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            from matplotlib.figure import Figure

            self.root = tk.Toplevel()
            self.root.title("实时速度曲线")
            self.root.geometry("500x300")
            self.root.attributes("-topmost", True)

            self.fig = Figure(figsize=(5, 3), dpi=100)
            self.ax = self.fig.add_subplot(111)
            self.ax.set_xlabel("时间 (s)")
            self.ax.set_ylabel("速度 (MB/s)")
            self.ax.set_ylim(0, 100)
            self.ax.grid(True, alpha=0.3)
            self.line, = self.ax.plot([], [], 'g-', linewidth=2)

            self.canvas = FigureCanvasTkAgg(self.fig, self.root)
            self.canvas.get_tk_widget().pack(fill="both", expand=True)

            self._update_loop()
            self.root.mainloop()
        except ImportError:
            pass

    def _update_loop(self):
        if not self.running or not self.root:
            return
        try:
            import matplotlib
            matplotlib.use("TkAgg")
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

            speeds = global_progress.get("speed_history", [])
            if len(speeds) > 200:
                speeds = speeds[-200:]
            if len(speeds) > 1:
                self.ax.clear()
                self.ax.set_xlabel("采样点")
                self.ax.set_ylabel("速度 (MB/s)")
                self.ax.set_ylim(0, max(speeds) * 1.2 + 1)
                self.ax.plot(range(len(speeds)), speeds, 'g-', linewidth=1.5)
                self.ax.fill_between(range(len(speeds)), speeds, alpha=0.3, color='green')
                self.ax.grid(True, alpha=0.3)
                self.canvas.draw()
        except Exception:
            pass
        if self.root:
            self.root.after(1000, self._update_loop)

    def hide(self):
        if self.root:
            self.root.destroy()
            self.root = None
        self.running = False

# ==================== GUI ====================
class LanTransferGUI:
    def __init__(self, root):
        self.root = root
        root.title("局域网直连传输工具 v7.0")
        root.geometry("900x820")
        root.resizable(False, False)

        self.history = TransferHistory()
        self.floating_ball = FloatingProgressBall()
        self.speed_chart = SpeedChartWindow()
        self.discovery = DeviceDiscovery(callback=self.on_device_discovered)

        # ---- 标题 ----
        frm_title = ttk.Frame(root)
        frm_title.pack(pady=4)
        ttk.Label(frm_title, text="🖧 局域网直连传输工具 v7.0", style="Title.TLabel").pack()
        ttk.Label(frm_title, text="拖拽 · 通知 · 自动发现 · 深色主题 · 差异同步 · 速度曲线", style="Muted.TLabel").pack()

        # ---- 网卡 ----
        frm_iface = ttk.LabelFrame(root, text=" 网卡 ", padding=4)
        frm_iface.pack(fill="x", padx=15, pady=1)
        row = ttk.Frame(frm_iface)
        row.pack(fill="x")
        ttk.Label(row, text="网卡:").pack(side="left")
        self.iface_var = tk.StringVar(value="")
        # PowerShell 枚举网卡仅在点「刷新 / 设IP / DHCP」时执行
        self.iface_combo = ttk.Combobox(row, textvariable=self.iface_var, values=[], width=16, state="readonly")
        self.iface_combo.pack(side="left", padx=3)
        ttk.Button(row, text="刷新", command=self.refresh_iface).pack(side="left", padx=2)
        self.ip_label = ttk.Label(frm_iface, text="IP: ...", foreground="blue")
        self.ip_label.pack(anchor="w", pady=1)
        self._ifaces_ready = False

        # 多网卡绑定
        multi_row = ttk.Frame(frm_iface)
        multi_row.pack(fill="x", pady=1)
        self.multi_nic_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(multi_row, text="🔗 多网卡绑定", variable=self.multi_nic_var, command=self.on_multi_nic_toggle).pack(side="left")
        ttk.Label(multi_row, text="副网卡:").pack(side="left", padx=4)
        self.secondary_iface_var = tk.StringVar()
        self.secondary_combo = ttk.Combobox(multi_row, textvariable=self.secondary_iface_var, values=[], width=14, state="disabled")
        self.secondary_combo.pack(side="left", padx=2)
        ttk.Label(multi_row, text="副IP:").pack(side="left", padx=2)
        self.secondary_ip_var = tk.StringVar(value="192.168.100.2")
        self.secondary_ip_entry = ttk.Entry(multi_row, textvariable=self.secondary_ip_var, width=12, state="disabled")
        self.secondary_ip_entry.pack(side="left", padx=2)
        ttk.Button(multi_row, text="设副IP", command=self.apply_secondary_ip, state="disabled").pack(side="left", padx=3)
        self.secondary_ip_btn = multi_row.winfo_children()[-1]

        # ---- 角色 ----
        frm_role = ttk.LabelFrame(root, text=" 角色 ", padding=4)
        frm_role.pack(fill="x", padx=15, pady=1)
        role_row = ttk.Frame(frm_role)
        role_row.pack(fill="x")
        ttk.Label(role_row, text="角色:").pack(side="left")
        self.role_var = tk.StringVar(value="receiver")
        ttk.Radiobutton(role_row, text="📥 接收方", variable=self.role_var, value="receiver", command=self.on_role_change).pack(side="left", padx=3)
        ttk.Radiobutton(role_row, text="📤 发送方", variable=self.role_var, value="sender", command=self.on_role_change).pack(side="left", padx=3)
        ttk.Button(role_row, text="⚙ 设IP", command=self.apply_ip).pack(side="right")
        ttk.Button(role_row, text="🔮 悬浮球", command=self.toggle_floating_ball).pack(side="right", padx=5)
        ttk.Button(role_row, text="📊 速度曲线", command=self.speed_chart.show).pack(side="right", padx=5)

        # ---- 传输设置 ----
        frm_xfer = ttk.LabelFrame(root, text=" 传输设置 ", padding=4)
        frm_xfer.pack(fill="x", padx=15, pady=1)

        r1 = ttk.Frame(frm_xfer)
        r1.pack(fill="x", pady=1)
        ttk.Label(r1, text="端口:").pack(side="left")
        self.port_var = tk.StringVar(value=str(DEFAULT_PORT))
        ttk.Entry(r1, textvariable=self.port_var, width=7).pack(side="left", padx=2)
        self.port_var.trace_add("write", lambda *_: self._sync_discover_port())
        ttk.Label(r1, text="限速:").pack(side="left", padx=(8,2))
        self.speed_var = tk.StringVar(value="0")
        self.speed_combo = ttk.Combobox(r1, textvariable=self.speed_var, width=7, state="readonly",
                                        values=["0", "10", "25", "50", "100", "200", "500", "1000"])
        self.speed_combo.pack(side="left")
        ttk.Label(r1, text="MB/s").pack(side="left", padx=1)
        self.resume_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(r1, text="🔄断点续传", variable=self.resume_var).pack(side="left", padx=8)

        # 差异同步
        self.sync_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r1, text="🔄 差异同步", variable=self.sync_var).pack(side="left", padx=8)

        # 设备发现
        ttk.Button(r1, text="📡 发现设备", command=self.discover_devices).pack(side="right", padx=3)
        self.discovered_devices = {}
        self.device_combo = ttk.Combobox(r1, width=18, state="readonly")
        self.device_combo.pack(side="right", padx=2)
        self.device_combo.bind("<<ComboboxSelected>>", self.on_device_selected)
        self._device_labels = []  # 与 combo values 对齐的 peer 列表

        r2 = ttk.Frame(frm_xfer)
        r2.pack(fill="x", pady=1)
        self.verify_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(r2, text="🔍 校验", variable=self.verify_var, command=self.on_verify_toggle).pack(side="left")
        ttk.Label(r2, text="算法:").pack(side="left", padx=2)
        self.verify_algo = tk.StringVar(value="md5")
        self.algo_md5 = ttk.Radiobutton(r2, text="MD5", variable=self.verify_algo, value="md5")
        self.algo_md5.pack(side="left", padx=2)
        self.algo_sha = ttk.Radiobutton(r2, text="SHA256", variable=self.verify_algo, value="sha256")
        self.algo_sha.pack(side="left", padx=2)
        self.encrypt_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r2, text="🔐 AES加密", variable=self.encrypt_var, command=self.on_encrypt_toggle).pack(side="left", padx=10)
        ttk.Label(r2, text="密码:").pack(side="left", padx=2)
        self.password_var = tk.StringVar(value="lan2024")
        self.password_entry = ttk.Entry(r2, textvariable=self.password_var, width=12, show="*")
        self.password_entry.pack(side="left", padx=2)

        r3 = ttk.Frame(frm_xfer)
        r3.pack(fill="x", pady=1)
        ttk.Label(r3, text="完成后:").pack(side="left")
        self.post_action_var = tk.StringVar(value="无")
        for text in ["无", "关机", "休眠", "睡眠"]:
            ttk.Radiobutton(r3, text=text, variable=self.post_action_var, value=text).pack(side="left", padx=4)

        r4 = ttk.Frame(frm_xfer)
        r4.pack(fill="x", pady=1)
        ttk.Label(r4, text="发送源:").pack(side="left")
        self.source_var = tk.StringVar()
        self.source_entry = ttk.Entry(r4, textvariable=self.source_var, width=33)
        self.source_entry.pack(side="left", padx=2, fill="x", expand=True)
        ttk.Button(r4, text="文件", command=self.add_file_to_queue).pack(side="right", padx=1)
        ttk.Button(r4, text="文件夹", command=self.add_dir_to_queue).pack(side="right", padx=1)

        r5 = ttk.Frame(frm_xfer)
        r5.pack(fill="x", pady=1)
        ttk.Label(r5, text="队列(可拖入):").pack(side="left")
        self.queue_listbox = tk.Listbox(r5, height=3, font=("Consolas", 8))
        self.queue_listbox.pack(side="left", padx=2, fill="x", expand=True)
        ttk.Button(r5, text="移除", command=self.remove_from_queue).pack(side="right", padx=1)
        ttk.Button(r5, text="清空", command=self.clear_queue).pack(side="right", padx=1)

        # 拖拽发送（tkinterdnd2）；启用提示在日志框创建后输出
        self._dnd_enabled = False
        if HAS_DND and DND_FILES is not None:
            for widget in (self.queue_listbox, root):
                widget.drop_target_register(DND_FILES)
                widget.dnd_bind("<<Drop>>", self.on_drop)
            self._dnd_enabled = True

        r6 = ttk.Frame(frm_xfer)
        r6.pack(fill="x", pady=1)
        ttk.Label(r6, text="保存至:").pack(side="left")
        self.save_var = tk.StringVar(value=os.path.expanduser("~"))
        ttk.Entry(r6, textvariable=self.save_var, width=18).pack(side="left", padx=2)
        ttk.Button(r6, text="浏览", command=self.browse_save).pack(side="left", padx=1)
        ttk.Label(r6, text="目标IP:").pack(side="left", padx=(8,2))
        self.target_var = tk.StringVar(value="192.168.99.1")
        ttk.Entry(r6, textvariable=self.target_var, width=12).pack(side="left", padx=1)
        ttk.Button(r6, text="Ping", command=self.ping_test).pack(side="left", padx=2)

        # ---- 按钮 ----
        frm_btn = ttk.Frame(root)
        frm_btn.pack(pady=4)
        ttk.Button(frm_btn, text="🚀 开始传输", style="Accent.TButton", command=self.start_transfer).pack(side="left", padx=3)
        ttk.Button(frm_btn, text="⏹ 停止", command=self.stop_transfer).pack(side="left", padx=3)
        ttk.Button(frm_btn, text="🌐 HTTP共享", command=self.start_http).pack(side="left", padx=3)
        ttk.Button(frm_btn, text="📱 二维码", command=self.show_share_qr).pack(side="left", padx=3)
        ttk.Button(frm_btn, text="📋 历史记录", command=lambda: show_history_window(self.history)).pack(side="left", padx=3)
        self.theme_btn = ttk.Button(frm_btn, text="🌙 深色主题", command=self.toggle_theme)
        self.theme_btn.pack(side="left", padx=3)
        ttk.Button(frm_btn, text="🔄 DHCP", command=self.restore_dhcp).pack(side="left", padx=3)
        ttk.Button(frm_btn, text="❌ 退出", command=root.quit).pack(side="left", padx=3)

        # ---- 日志 ----
        frm_log = ttk.LabelFrame(root, text=" 日志 ", padding=3)
        frm_log.pack(fill="both", expand=True, padx=15, pady=1)
        self.log = scrolledtext.ScrolledText(frm_log, height=10, font=("Consolas", 9))
        self.log.pack(fill="both", expand=True)

        # 限速器
        self.rate_limiter = RateLimiter(0)
        self.speed_combo.bind("<<ComboboxSelected>>", self.on_speed_change)
        self.stop_event = threading.Event()
        self.transfer_thread = None
        self.http_server = None
        self.qr_win = None
        self.share_url = ""

        self.on_role_change()
        self.on_encrypt_toggle()

        if getattr(self, "_dnd_enabled", False):
            self.log_write("✅ 拖拽发送已启用：把文件/文件夹拖到窗口或队列即可\n")
        else:
            self.log_write("⚠️ 未安装 tkinterdnd2，拖拽不可用：pip install tkinterdnd2\n")

        self.theme = apply_theme(self.root, current_theme)
        # 重依赖 / PowerShell / UDP 发现全部推到首帧之后
        self.root.after(50, self._post_startup)

    # ---- 方法 ----
    def _post_startup(self):
        """启动后只做轻量初始化：本机 IP（socket）+ UDP 发现，不启动 PowerShell。"""
        def worker():
            try:
                ip = get_local_ip()
                self.root.after(0, lambda: self.ip_label.config(text=f"IP: {ip}"))
            except Exception:
                pass
            try:
                port = int(self.port_var.get())
                self.discovery.ensure(port)
            except Exception as e:
                self.root.after(0, lambda: self.log_write(f"⚠️ 设备发现未启动: {e}\n"))
        threading.Thread(target=worker, daemon=True).start()
        self.root.after(1500, self._poll_discovered)

    def _sync_discover_port(self):
        try:
            self.discovery.set_tcp_port(int(self.port_var.get()))
        except ValueError:
            pass

    def _poll_discovered(self):
        """周期同步发现列表到 combo（对端自动上线/掉线）。"""
        try:
            if not self.root.winfo_exists():
                return
            devices = self.discovery.snapshot()
            sig = tuple((d["ip"], d["name"], d.get("port")) for d in devices)
            if sig != getattr(self, "_device_sig", None):
                self._device_sig = sig
                self._refresh_device_combo(devices, log=False, notify=False)
            self.root.after(2000, self._poll_discovered)
        except tk.TclError:
            pass

    def _apply_iface_list(self, interfaces, ip=None):
        self.iface_combo["values"] = interfaces
        self.secondary_combo["values"] = interfaces
        self._ifaces_ready = bool(interfaces)
        if interfaces:
            self.iface_combo.current(0)
        if ip is not None:
            self.ip_label.config(text=f"IP: {ip}")

    def _load_ifaces_async(self, on_done=None, force=True):
        """按需启动 PowerShell 枚举网卡。"""
        def worker():
            try:
                interfaces = get_ethernet_interfaces(force=force)
                ip = get_local_ip()
            except Exception as e:
                self.root.after(0, lambda: self.log_write(f"⚠️ 网卡枚举失败: {e}\n"))
                return
            def done():
                self._apply_iface_list(interfaces, ip)
                if on_done:
                    on_done()
            self.root.after(0, done)
        self.log_write("🔎 正在枚举网卡（PowerShell）...\n")
        threading.Thread(target=worker, daemon=True).start()

    def _ensure_iface_selected(self, then):
        iface = self.iface_var.get().strip()
        if self._ifaces_ready and iface:
            then(iface)
            return
        def after_load():
            name = self.iface_var.get().strip()
            if not name:
                messagebox.showerror("错误", "未找到可用网卡")
                return
            then(name)
        self._load_ifaces_async(on_done=after_load, force=True)

    def log_write(self, text, raw=False):
        def _do():
            try:
                if not self.log.winfo_exists():
                    return
            except tk.TclError:
                return
            if raw:
                text_clean = text.replace("\r", "")
                end = self.log.index("end-1c")
                line_start = self.log.index("end-1c linestart")
                last = self.log.get(line_start, end)
                if last.startswith("📥 ") or last.startswith("📤 "):
                    self.log.delete(line_start, end)
                self.log.insert(tk.END, text_clean)
            else:
                self.log.insert(tk.END, text)
            self.log.see(tk.END)
        if threading.current_thread() is threading.main_thread():
            _do()
        else:
            self.root.after(0, _do)

    def refresh_iface(self):
        self._load_ifaces_async(force=True)

    def on_role_change(self):
        role = self.role_var.get()
        if role == "receiver":
            self.target_var.set("")
            return
        if self._device_labels:
            self._apply_peer(self._device_labels[0])
            self.device_combo.current(0)
        else:
            self.target_var.set("192.168.99.1")

    def on_verify_toggle(self):
        state = "normal" if self.verify_var.get() else "disabled"
        self.algo_md5.config(state=state)
        self.algo_sha.config(state=state)

    def on_encrypt_toggle(self):
        state = "normal" if self.encrypt_var.get() else "disabled"
        self.password_entry.config(state=state)

    def on_multi_nic_toggle(self):
        state = "normal" if self.multi_nic_var.get() else "disabled"
        self.secondary_combo.config(state=state)
        self.secondary_ip_entry.config(state=state)
        self.secondary_ip_btn.config(state=state)

    def bind_ip(self):
        if not self.multi_nic_var.get():
            return None
        ip = self.secondary_ip_var.get().strip()
        return ip or None

    def toggle_theme(self):
        global current_theme
        new_theme = "dark" if current_theme == "light" else "light"
        self.theme = apply_theme(self.root, new_theme)
        self.theme_btn.config(text="☀ 浅色主题" if new_theme == "dark" else "🌙 深色主题")
        self.log_write(f"🎨 切换至{'深色' if new_theme == 'dark' else '浅色'}主题\n")

    def toggle_floating_ball(self):
        if self.floating_ball.running:
            self.floating_ball.hide()
        else:
            self.floating_ball.show()

    def on_drop(self, event):
        """处理拖拽文件/文件夹到队列。"""
        raw = (event.data or "").strip()
        if not raw:
            return
        # Windows tkinterdnd2: 含空格路径被 {} 包裹，如 {C:\a b.txt} C:\c.txt
        paths = [m[0] or m[1] for m in re.findall(r"\{([^}]+)\}|(\S+)", raw)]
        added = 0
        for f in paths:
            f = f.strip().strip('"').replace("/", os.sep)
            if os.path.isfile(f):
                self.queue_listbox.insert(tk.END, f"FILE:{f}")
                added += 1
            elif os.path.isdir(f):
                self.queue_listbox.insert(tk.END, f"DIR:{f}")
                added += 1
        if added:
            self.source_var.set(f"队列: {self.queue_listbox.size()} 项")
            self.log_write(f"📁 拖拽添加 {added} 项\n")
        else:
            self.log_write(f"⚠️ 拖拽路径无效: {raw}\n")

    def discover_devices(self):
        """发现局域网设备"""
        self.log_write("📡 正在搜索设备...\n")
        try:
            port = int(self.port_var.get())
        except ValueError:
            self.log_write("❌ 端口无效\n")
            return
        def worker():
            try:
                self.discovery.ensure(port)
                devices = self.discovery.discover_once()
            except Exception as e:
                self.root.after(0, lambda: self.log_write(f"❌ 发现失败: {e}\n"))
                return
            self.root.after(0, lambda: self._update_device_list(devices))
        threading.Thread(target=worker, daemon=True).start()

    def _device_label(self, d):
        return f"{d['name']} ({d['ip']}:{d.get('port', DEFAULT_PORT)})"

    def _refresh_device_combo(self, devices, log=False, notify=False, select_first=False):
        self.discovered_devices = {d["ip"]: d for d in devices}
        self._device_sig = tuple((d["ip"], d["name"], d.get("port")) for d in devices)
        labels = [self._device_label(d) for d in devices]
        prev = self.device_combo.get()
        self._device_labels = devices
        self.device_combo["values"] = labels
        if not devices:
            self.device_combo.set("")
            if log:
                self.log_write("❌ 未发现设备\n")
            return
        if select_first or prev not in labels:
            self.device_combo.current(0)
            self._apply_peer(devices[0])
        else:
            self.device_combo.set(prev)
        if log:
            self.log_write(f"✅ 发现 {len(devices)} 个设备\n")
            for d in devices:
                self.log_write(f"   {d['name']} - {d['ip']}:{d.get('port', DEFAULT_PORT)}\n")
        if notify:
            send_notification("设备发现", f"发现 {len(devices)} 个设备")

    def _apply_peer(self, peer):
        if self.role_var.get() != "sender":
            return
        self.target_var.set(peer["ip"])
        port = peer.get("port")
        if port:
            self.port_var.set(str(port))
            self.discovery.set_tcp_port(port)

    def _update_device_list(self, devices):
        self._refresh_device_combo(devices, log=True, notify=True, select_first=True)

    def on_device_selected(self, _event=None):
        idx = self.device_combo.current()
        if idx < 0 or idx >= len(self._device_labels):
            return
        self._apply_peer(self._device_labels[idx])
        peer = self._device_labels[idx]
        self.log_write(f"🔗 已选对端: {peer['name']} ({peer['ip']}:{peer.get('port', DEFAULT_PORT)})\n")

    def on_device_discovered(self, ip, name, port, is_new):
        self.discovered_devices[ip] = {"ip": ip, "name": name, "port": port}
        if is_new:
            self.root.after(0, lambda: self.log_write(
                f"📡 发现设备: {name} ({ip}:{port})\n"
            ))
            self.root.after(0, lambda: self._refresh_device_combo(
                self.discovery.snapshot(), log=False, notify=False
            ))

    def add_file_to_queue(self):
        f = filedialog.askopenfilename(title="选择文件")
        if f:
            self.queue_listbox.insert(tk.END, f"FILE:{f}")
            self.source_var.set(f"队列: {self.queue_listbox.size()} 项")

    def add_dir_to_queue(self):
        d = filedialog.askdirectory(title="选择文件夹")
        if d:
            self.queue_listbox.insert(tk.END, f"DIR:{d}")
            self.source_var.set(f"队列: {self.queue_listbox.size()} 项")

    def clear_queue(self):
        self.queue_listbox.delete(0, tk.END)
        self.source_var.set("")

    def remove_from_queue(self):
        sel = self.queue_listbox.curselection()
        for i in reversed(sel):
            self.queue_listbox.delete(i)
        self.source_var.set(f"队列: {self.queue_listbox.size()} 项" if self.queue_listbox.size() > 0 else "")

    def browse_save(self):
        d = filedialog.askdirectory(title="选择保存目录")
        if d:
            self.save_var.set(d)

    def on_speed_change(self, event=None):
        try:
            mbps = float(self.speed_var.get())
        except ValueError:
            mbps = 0
        self.rate_limiter.update_limit(mbps)
        self.log_write(f"🚦 限速: {mbps} MB/s\n")

    def ping_test(self):
        target = self.target_var.get()
        def worker():
            try:
                if sys.platform == "win32":
                    out = subprocess.check_output(f"ping -n 3 {target}", shell=True, text=True, timeout=10)
                else:
                    out = subprocess.check_output(f"ping -c 3 {target}", shell=True, text=True, timeout=10)
                self.log_write(f"✅ Ping {target} 成功\n")
            except Exception as e:
                self.log_write(f"❌ Ping 失败: {e}\n")
        threading.Thread(target=worker, daemon=True).start()

    def apply_ip(self):
        def do_set(iface):
            ip = ROLE_RECEIVER_IP if self.role_var.get() == "receiver" else ROLE_SENDER_IP
            if not set_static_ip(iface, ip):
                messagebox.showerror("错误", f"设置 IP 失败: {iface} → {ip}")
                return
            self.ip_label.config(text=f"IP: {ip}")
            self.log_write(f"✅ IP → {ip} ({iface})\n")
        self._ensure_iface_selected(do_set)

    def apply_secondary_ip(self):
        def do_set(_primary_ignored=None):
            iface = self.secondary_iface_var.get().strip()
            ip = self.secondary_ip_var.get().strip()
            if not iface or not ip:
                messagebox.showerror("错误", "请先刷新并选择副网卡，填写副IP")
                return
            if not set_static_ip(iface, ip):
                self.log_write(f"❌ 副IP 设置失败: {ip} ({iface})\n")
                return
            self.log_write(f"✅ 副IP → {ip} ({iface})\n")

        if self._ifaces_ready and self.secondary_iface_var.get().strip():
            do_set()
        else:
            self._load_ifaces_async(on_done=do_set, force=True)

    def _busy(self):
        return (self.transfer_thread and self.transfer_thread.is_alive()) or self.http_server is not None

    def stop_transfer(self):
        self.stop_event.set()
        server = self.http_server
        self.http_server = None
        if server:
            threading.Thread(target=server.shutdown, daemon=True).start()
        self._close_qr_win()
        self.share_url = ""
        self.log_write("⏹ 正在停止...\n")

    def _current_share_ip(self):
        """优先用界面显示的本机 IP（直连场景常被手动设成 192.168.99.x）。"""
        text = self.ip_label.cget("text")
        if text.startswith("IP:"):
            ip = text[3:].strip()
            if ip and ip not in (".", "...", "未知"):
                return ip
        return get_local_ip()

    def _close_qr_win(self):
        win = self.qr_win
        self.qr_win = None
        if win is not None:
            try:
                win.destroy()
            except tk.TclError:
                pass

    def _open_qr_win(self, url):
        self._close_qr_win()
        self.share_url = url
        self.qr_win = show_share_qr_window(
            self.root, url, on_close=lambda: setattr(self, "qr_win", None),
        )

    def show_share_qr(self):
        """已在 HTTP 共享时重新弹出二维码；否则提示先开共享。"""
        if self.share_url and self.http_server is not None:
            self._open_qr_win(self.share_url)
            return
        if self.http_server is None:
            messagebox.showinfo("提示", "请先点击「HTTP共享」选择目录，启动后会自动弹出二维码")
            return
        try:
            port = int(self.port_var.get())
        except ValueError:
            messagebox.showerror("错误", "端口无效")
            return
        url = share_base_url(self._current_share_ip(), port)
        self._open_qr_win(url)

    def start_transfer(self):
        if self._busy():
            messagebox.showerror("错误", "已有传输或 HTTP 共享在运行，请先停止")
            return
        try:
            port = int(self.port_var.get())
        except ValueError:
            messagebox.showerror("错误", "端口无效")
            return
        self.discovery.ensure(port)
        self.discovery.probe()
        role = self.role_var.get()
        self.stop_event.clear()
        global_progress["speed_history"] = []
        bind_ip = self.bind_ip()

        if role == "receiver":
            save_dir = self.save_var.get()
            if not save_dir or not os.path.isdir(save_dir):
                messagebox.showerror("错误", "请选择保存目录")
                return
            if self.encrypt_var.get() and not self.password_var.get():
                messagebox.showerror("错误", "加密传输需要设置密码")
                return
            self.log_write(f"📥 接收模式启动 (端口 {port}" + (f", 绑定 {bind_ip}" if bind_ip else "") + ")\n")
            global_progress["active"] = True
            self.transfer_thread = start_receiver(
                port, save_dir, self.log_write, self.resume_var,
                self.rate_limiter, self.verify_var, self.verify_algo,
                self.post_action_var, self.encrypt_var, self.password_var,
                self.history, bind_ip, self.stop_event,
            )
        else:
            items = []
            for i in range(self.queue_listbox.size()):
                entry = self.queue_listbox.get(i)
                if entry.startswith("FILE:"):
                    items.append(entry[5:])
                elif entry.startswith("DIR:"):
                    items.append(entry[4:])
            if not items:
                single = self.source_var.get()
                if single and os.path.exists(single) and not single.startswith("队列"):
                    items.append(single)
                else:
                    messagebox.showerror("错误", "队列为空")
                    return
            target_ip = self.target_var.get().strip()
            if not target_ip:
                messagebox.showerror("错误", "请输入目标IP")
                return
            if self.encrypt_var.get() and not self.password_var.get():
                messagebox.showerror("错误", "加密传输需要设置密码")
                return
            self.log_write(f"📤 发送模式启动 → {target_ip}:{port}" + (f" via {bind_ip}" if bind_ip else "") + "\n")
            self.log_write(f"   队列: {len(items)} 项\n")
            global_progress["active"] = True
            self.transfer_thread = start_sender_queue(
                target_ip, port, items, self.log_write, self.resume_var,
                self.rate_limiter, self.verify_var, self.verify_algo,
                self.encrypt_var, self.password_var, self.history,
                bind_ip, self.sync_var.get(), self.stop_event,
            )

    def start_http(self):
        if self._busy():
            messagebox.showerror("错误", "已有传输或 HTTP 共享在运行，请先停止")
            return
        try:
            port = int(self.port_var.get())
        except ValueError:
            messagebox.showerror("错误", "端口无效")
            return
        d = filedialog.askdirectory(title="选择共享目录")
        if not d:
            return
        self.stop_event.clear()
        ip = self._current_share_ip()
        url = share_base_url(ip, port)
        self.log_write(f"🌐 HTTP 共享启动\n")
        self.log_write(f"   链接: {url}\n")
        self.log_write(f"   目录: {d}\n")
        self.transfer_thread = start_http_server(port, d, self.log_write, self, self.stop_event)
        self._open_qr_win(url)

    def restore_dhcp(self):
        def do_restore(iface):
            if not set_dhcp(iface):
                messagebox.showerror("错误", f"恢复 DHCP 失败: {iface}")
                return
            self.ip_label.config(text=f"IP: {get_local_ip()}")
            self.log_write("✅ DHCP 已恢复\n")
        self._ensure_iface_selected(do_restore)

# ==================== 接收端 ====================
def _extract_zip(zip_path, dest_dir):
    dest_abs = os.path.abspath(dest_dir)
    os.makedirs(dest_abs, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.infolist():
            target = os.path.abspath(os.path.join(dest_abs, member.filename))
            if os.path.commonpath([dest_abs, target]) != dest_abs:
                raise ValueError(f"压缩包路径非法: {member.filename}")
            zf.extract(member, dest_abs)


def start_receiver(port, save_dir, log_callback, resume_var, rate_limiter, verify_var, verify_algo,
                   post_action_var, encrypt_var, password_var, history, bind_ip, stop_event):
    def worker():
        srv = None
        total_completed = total_failed = total_skipped = 0
        try:
            srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind((bind_ip or "0.0.0.0", port))
            srv.listen(5)
            srv.settimeout(1.0)
            log_callback(f"🟢 接收端监听 {bind_ip or '0.0.0.0'}:{port}，点「停止」结束\n")
            
            while not stop_event.is_set(): 
                try:
                    conn, addr = srv.accept()
                except socket.timeout:
                    continue
                try:
                    ok, skipped = _handle_incoming(
                        conn, addr, save_dir, log_callback, resume_var, rate_limiter,
                        verify_var, verify_algo, encrypt_var, password_var, history, stop_event,
                    )
                    if skipped:
                        total_skipped += 1
                    elif ok:
                        total_completed += 1
                    else:
                        total_failed += 1
                except Exception as e:
                    total_failed += 1
                    log_callback(f"❌ 处理失败: {e}\n")
                finally:
                    try:
                        conn.close()
                    except OSError:
                        pass

            log_callback(f"\n📊 接收统计: 成功 {total_completed}, 跳过 {total_skipped}, 失败 {total_failed}\n")
            if total_completed > 0:
                send_notification("传输完成", f"接收 {total_completed} 个，跳过 {total_skipped}，失败 {total_failed}")
            action = post_action_var.get()
            if action != "无" and total_completed > 0:
                log_callback(f"⏳ 执行完成后动作: {action}\n")
                time.sleep(3)
                do_post_action(action)
        except Exception as e:
            log_callback(f"❌ 接收端错误: {e}\n")
        finally:
            global_progress["active"] = False
            if srv:
                try:
                    srv.close()
                except OSError:
                    pass

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return t


def _handle_incoming(conn, addr, save_dir, log_callback, resume_var, rate_limiter,
                     verify_var, verify_algo, encrypt_var, password_var, history, stop_event):
    log_callback(f"\n{'━'*50}\n")
    log_callback(f"✅ 连接: {addr[0]}:{addr[1]}\n")
    ptype, meta = recv_protocol_header(conn)
    if not ptype:
        log_callback("❌ 协议头无效\n")
        return False, False

    filename = safe_basename(meta.get("name", "unknown"))
    logical = safe_basename(meta.get("logical") or filename)
    total_size = int(meta.get("size") or 0)
    sender_hash = meta.get("hash") or ""
    is_dir = ptype == "D"
    is_encrypted = bool(meta.get("encrypted"))
    sig = meta.get("sig")
    save_path = safe_join(save_dir, filename)
    compare_path = safe_join(save_dir, logical if sig and sig.get("tree") else filename)
    log_callback(f"📋 {'文件夹' if is_dir else '文件'}: {filename} ({total_size/1024/1024:.1f} MB)\n")

    if sig and content_same(compare_path, sig):
        conn.sendall(struct.pack(">Q", SKIP_OFFSET))
        log_callback(f"⏭ 未变化，跳过: {logical}\n")
        history.add("接收", logical, total_size, "跳过")
        return True, True

    actual_offset = 0
    if resume_var.get() and not is_encrypted and os.path.isfile(save_path):
        existing = os.path.getsize(save_path)
        if existing == total_size and total_size > 0:
            algo = verify_algo.get() if verify_var.get() else (meta.get("hash_algo") or "md5")
            if sender_hash and calc_hash(save_path, algo).lower() == sender_hash.lower():
                conn.sendall(struct.pack(">Q", total_size))
                log_callback(f"⏭ 本地已完整且校验通过: {filename}\n")
                history.add("接收", filename, total_size, "跳过", verify_result="通过")
                return True, True
        elif 0 < existing < total_size:
            actual_offset = existing

    conn.sendall(struct.pack(">Q", actual_offset))
    global_progress["filename"] = filename
    global_progress["total"] = total_size
    global_progress["direction"] = "recv"
    global_progress["start_time"] = time.time()

    wire_path = save_path + ".enc" if is_encrypted else save_path
    wire_offset = 0 if is_encrypted else actual_offset
    received, ok = recv_payload(
        conn, wire_path, wire_offset, total_size, stop_event, rate_limiter, log_callback, filename,
    )
    if not ok or received < total_size:
        log_callback(f"\n❌ 接收中断: {filename} ({received}/{total_size})\n")
        history.add("接收", filename, total_size, "失败", encrypted=is_encrypted)
        return False, False

    if is_encrypted:
        salt_b64 = meta.get("salt") or ""
        if not salt_b64 or not password_var.get():
            log_callback("❌ 缺少解密盐或密码\n")
            return False, False
        cipher = AESCipher(password_var.get(), base64.b64decode(salt_b64))
        with open(wire_path, "rb") as ef, open(save_path, "wb") as df:
            cipher.decrypt_stream(ef, df)
        os.remove(wire_path)

    log_callback(f"\n✅ 接收完成: {filename}\n")
    verify_pass = True
    verify_text = ""
    if verify_var.get() and sender_hash:
        local_hash = calc_hash(save_path, verify_algo.get())
        if local_hash.lower() == sender_hash.lower():
            verify_text = "通过"
            log_callback("✅ 校验通过\n")
        else:
            verify_text = "失败"
            verify_pass = False
            log_callback("❌ 校验失败\n")

    if is_dir and verify_pass:
        _extract_zip(save_path, safe_join(save_dir, logical))
        os.remove(save_path)
        log_callback(f"📦 已解压到: {logical}\n")

    if verify_pass:
        history.add("接收", logical, total_size, "成功", verify_result=verify_text, encrypted=is_encrypted)
        return True, False
    history.add("接收", logical, total_size, "失败", verify_result=verify_text, encrypted=is_encrypted)
    return False, False


# ==================== 发送端 ====================
def _cleanup(paths):
    for p in paths:
        try:
            if p and os.path.isfile(p):
                os.remove(p)
        except OSError:
            pass


def start_sender_queue(target_ip, port, queue_items, log_callback, resume_var, rate_limiter, verify_var,
                       verify_algo, encrypt_var, password_var, history, bind_ip, sync_enabled, stop_event):
    def worker():
        completed = failed = skipped = 0
        total_items = len(queue_items)
        total_start = time.time()
        try:
            for item_path in queue_items:
                if stop_event.is_set():
                    log_callback("⏹ 发送已停止\n")
                    break
                temps = []
                sock = None
                try:
                    if not os.path.exists(item_path):
                        log_callback(f"❌ 不存在，计为失败: {item_path}\n")
                        failed += 1
                        continue

                    is_dir = os.path.isdir(item_path)
                    log_callback(f"\n{'━'*50}\n")
                    log_callback(f"📤 队列: {completed + skipped + failed + 1}/{total_items}\n")
                    sig = None
                    if is_dir:
                        folder_name = os.path.basename(item_path)
                        if sync_enabled:
                            log_callback("🔄 计算目录签名...\n")
                            sig = compute_tree_signature(item_path)
                        zip_path = os.path.join(os.path.dirname(item_path), folder_name + ".zip")
                        if os.path.exists(zip_path):
                            os.remove(zip_path)
                        # 局域网带宽远大于 CPU：STORE 只打包不压缩。
                        # DEFLATE 对已压缩内容（jpg/pdf/docx）几乎不降体积，却拖慢打包。
                        log_callback(f"📦 打包文件夹（STORE）: {folder_name}\n")
                        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_STORED) as zf:
                            for root, dirs, files in os.walk(item_path):
                                dirs.sort()
                                for file in files:
                                    fp = os.path.join(root, file)
                                    zf.write(fp, os.path.relpath(fp, item_path))
                        temps.append(zip_path)
                        send_path, send_name, logical, ptype = zip_path, folder_name + ".zip", folder_name, "D"
                    else:
                        if sync_enabled:
                            sig = compute_file_signature(item_path)
                        send_path = item_path
                        send_name = logical = os.path.basename(item_path)
                        ptype = "F"

                    file_hash = ""
                    if verify_var.get():
                        file_hash = calc_hash(send_path, verify_algo.get())
                        log_callback(f"   {verify_algo.get()}: {file_hash[:16]}...\n")

                    payload = send_path
                    salt_b64 = ""
                    is_encrypted = bool(encrypt_var.get())
                    if is_encrypted:
                        cipher = AESCipher(password_var.get())
                        enc_path = send_path + ".enc"
                        with open(send_path, "rb") as sf, open(enc_path, "wb") as ef:
                            cipher.encrypt_stream(sf, ef)
                        temps.append(enc_path)
                        payload = enc_path
                        salt_b64 = base64.b64encode(cipher.salt).decode("ascii")

                    file_size = os.path.getsize(payload)
                    log_callback(f"📋 名称: {send_name} ({file_size/1024/1024:.1f} MB)\n")
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    try:
                        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1024 * 1024)
                    except OSError:
                        pass
                    sock.settimeout(30)
                    if bind_ip:
                        sock.bind((bind_ip, 0))
                    sock.connect((target_ip, port))
                    sock.settimeout(None)
                    send_protocol_header(sock, ptype, {
                        "name": send_name, "logical": logical, "size": file_size,
                        "hash": file_hash, "hash_algo": verify_algo.get(),
                        "encrypted": is_encrypted, "sig": sig, "salt": salt_b64,
                    })
                    resp = recv_exact(sock, 8)
                    if not resp:
                        log_callback("❌ 对端未返回偏移\n")
                        failed += 1
                        continue
                    resume_offset = struct.unpack(">Q", resp)[0]
                    if resume_offset == SKIP_OFFSET or resume_offset >= file_size:
                        log_callback(f"⏭ 对端已有相同内容，跳过: {logical}\n")
                        skipped += 1
                        history.add("发送", logical, file_size, "跳过", encrypted=is_encrypted)
                        continue
                    if is_encrypted:
                        resume_offset = 0

                    sent = resume_offset
                    last_log, last_sent = time.time(), sent
                    global_progress["filename"] = send_name
                    global_progress["total"] = file_size
                    global_progress["direction"] = "send"
                    global_progress["start_time"] = time.time()
                    with open(payload, "rb") as f:
                        f.seek(resume_offset)
                        while True:
                            if stop_event.is_set():
                                raise InterruptedError("已停止")
                            chunk = f.read(CHUNK_SIZE)
                            if not chunk:
                                break
                            sock.sendall(chunk)
                            sent += len(chunk)
                            rate_limiter.consume(len(chunk))
                            last_log, last_sent = report_progress(
                                log_callback, "📤", send_name, sent, file_size, last_log, last_sent,
                            )
                    elapsed = time.time() - global_progress["start_time"]
                    avg = file_size / elapsed / 1024 / 1024 if elapsed > 0 else 0
                    log_callback(f"\n✅ 完成: {send_name} (平均 {avg:.1f} MB/s)\n")
                    completed += 1
                    history.add("发送", send_name, file_size, "成功", speed=f"{avg:.1f} MB/s", encrypted=is_encrypted)
                except Exception as e:
                    log_callback(f"\n❌ 发送失败: {e}\n")
                    failed += 1
                finally:
                    if sock:
                        try:
                            sock.close()
                        except OSError:
                            pass
                    _cleanup(temps)
        finally:
            global_progress["active"] = False
            elapsed = time.time() - total_start
            log_callback(f"\n{'='*50}\n")
            log_callback(f"📊 发送统计: 成功 {completed}/{total_items}, 跳过 {skipped}, 失败 {failed}\n")
            log_callback(f"⏱ 总耗时: {elapsed:.0f}s\n")
            if completed or skipped:
                send_notification("传输完成", f"成功 {completed}，跳过 {skipped}，失败 {failed}，耗时 {elapsed:.0f}s")

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return t


# ==================== 完成后动作 ====================
def do_post_action(action):
    try:
        if sys.platform == "win32":
            if action == "关机":
                subprocess.run("shutdown /s /t 30", shell=True)
            elif action == "休眠":
                subprocess.run("shutdown /h", shell=True)
            elif action == "睡眠":
                subprocess.run("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)
        else:
            if action == "关机":
                subprocess.run("sudo shutdown -h now", shell=True)
            elif action == "休眠":
                subprocess.run("sudo systemctl hibernate", shell=True)
            elif action == "睡眠":
                subprocess.run("sudo systemctl suspend", shell=True)
    except Exception:
        pass


# ==================== HTTP 共享 ====================
def start_http_server(port, share_dir, log_callback, app, stop_event):
    def worker():
        import http.server
        server = None
        try:
            handler = lambda *args, **kwargs: http.server.SimpleHTTPRequestHandler(
                *args, directory=share_dir, **kwargs
            )
            server = http.server.HTTPServer(("0.0.0.0", port), handler)
            app.http_server = server
            log_callback(f"🌐 HTTP 共享端口 {port}，目录 {share_dir}。扫码或打开链接即可下载。点「停止」结束\n")
            server.serve_forever()
        except Exception as e:
            log_callback(f"❌ HTTP 错误: {e}\n")
        finally:
            app.http_server = None
            if server:
                try:
                    server.server_close()
                except Exception:
                    pass
            log_callback("⏹ HTTP 共享已停止\n")

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return t

# ==================== 历史记录窗口 ====================
def show_history_window(history):
    hist_win = tk.Toplevel()
    hist_win.title("传输历史记录")
    hist_win.geometry("750x450")
    columns = ("时间", "方向", "文件名", "大小", "状态", "校验", "加密", "速度")
    tree = ttk.Treeview(hist_win, columns=columns, show="headings", height=20)
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=80 if col != "文件名" else 200)
    tree.pack(fill="both", expand=True, padx=5, pady=5)

    for r in history.get_all():
        size_str = f"{r.get('size',0)/1024/1024:.1f} MB" if r.get('size',0) > 0 else "-"
        tree.insert("", "end", values=(
            r.get("time", ""), r.get("direction", ""), r.get("filename", ""),
            size_str, r.get("status", ""), r.get("verify", ""),
            "是" if r.get("encrypted") else "否", r.get("speed", "")
        ))

# ==================== 单实例 ====================
_INSTANCE_MUTEX_NAME = "Local\\LanTransferGUI_v7_SingleInstance"
_INSTANCE_MUTEX = None  # 进程存活期间持有，防止被 GC 释放

def _activate_existing_window(title="局域网直连传输工具 v7.0"):
    """把已运行的主窗口拉到前台。"""
    if sys.platform != "win32":
        return False
    user32 = ctypes.windll.user32
    hwnd = user32.FindWindowW(None, title)
    if not hwnd:
        return False
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    user32.SetForegroundWindow(hwnd)
    return True

def acquire_single_instance():
    """
    成功拿到锁返回 True；已有实例则激活旧窗口并返回 False。
    Windows：命名 Mutex（exe 连点也不会起第二个）。
    其它：本机 TCP 端口占位。
    """
    global _INSTANCE_MUTEX
    if sys.platform == "win32":
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.CreateMutexW(None, False, _INSTANCE_MUTEX_NAME)
        if not handle:
            return True  # 拿不到句柄就放行，别把自己锁死
        ERROR_ALREADY_EXISTS = 183
        if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
            kernel32.CloseHandle(handle)
            _activate_existing_window()
            return False
        _INSTANCE_MUTEX = handle
        return True

    # 非 Windows：绑定固定环回口当锁
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
        sock.bind(("127.0.0.1", DISCOVER_PORT + 1))
        _INSTANCE_MUTEX = sock  # 持有至进程退出
        return True
    except OSError:
        return False

# ==================== 主入口 ====================
if __name__ == "__main__":
    if not acquire_single_instance():
        # 已激活旧窗口；激活失败时再弹提示
        if sys.platform == "win32" and not ctypes.windll.user32.FindWindowW(
            None, "局域网直连传输工具 v7.0"
        ):
            ctypes.windll.user32.MessageBoxW(
                0, "局域网直连传输工具已在运行。", "提示", 0x40
            )
        sys.exit(0)
    if HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
        print("警告: 未安装 tkinterdnd2，拖拽发送不可用。请执行: pip install tkinterdnd2", flush=True)
    app = LanTransferGUI(root)
    root.mainloop()