"""
Media Download GUI（Telegram / X）。

布局：顶栏 → 配置 → 链接/队列 → 操作/进度 → 日志/历史 → 状态栏。
下载逻辑在 tgdl，本文件只做 UI 与后台线程调度。
"""

from __future__ import annotations

import asyncio
import os
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from tg_download import (
    CONFIG_PATH,
    VERSION,
    DownloadControl,
    HAS_CRYPTG,
    acquire_instance_lock,
    app_dir,
    clear_history,
    disk_free_gb,
    link_kind,
    load_config,
    load_history,
    release_instance_lock,
    run,
    save_config,
)

ROOT = app_dir()

STATUS_CN = {
    "pending": "等待",
    "running": "下载中",
    "ok": "完成",
    "skip": "跳过",
    "fail": "失败",
    "cancelled": "取消",
}

STATUS_FG = {
    "pending": "#5B6B7C",
    "running": "#0369A1",
    "ok": "#15803D",
    "skip": "#5B6B7C",
    "fail": "#B91C1C",
    "cancelled": "#B45309",
}

# 配色：冷灰底 + 青绿强调（避开默认紫/奶油风）
C = {
    "bg": "#EEF1F4",
    "card": "#FFFFFF",
    "line": "#D8DEE6",
    "text": "#1A2332",
    "muted": "#5B6B7C",
    "accent": "#0D9488",
    "accent_hi": "#0F766E",
    "danger": "#B91C1C",
    "danger_hi": "#991B1B",
    "header": "#0F172A",
    "input_bg": "#F8FAFC",
    "ok": "#15803D",
    "fail": "#B91C1C",
    "run": "#0369A1",
}


def apply_theme(root: tk.Tk) -> ttk.Style:
    root.configure(bg=C["bg"])
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    font_ui = ("Segoe UI", 10)
    font_title = ("Segoe UI Semibold", 16)
    font_sub = ("Segoe UI", 9)
    font_btn = ("Segoe UI Semibold", 10)

    style.configure(".", background=C["bg"], foreground=C["text"], font=font_ui)
    style.configure("TFrame", background=C["bg"])
    style.configure("Card.TFrame", background=C["card"])
    style.configure("Header.TFrame", background=C["header"])
    style.configure("Status.TFrame", background=C["card"])

    style.configure("TLabel", background=C["bg"], foreground=C["text"], font=font_ui)
    style.configure("Card.TLabel", background=C["card"], foreground=C["text"])
    style.configure("Muted.TLabel", background=C["bg"], foreground=C["muted"], font=font_sub)
    style.configure("CardMuted.TLabel", background=C["card"], foreground=C["muted"], font=font_sub)
    style.configure(
        "HeaderTitle.TLabel",
        background=C["header"],
        foreground="#F8FAFC",
        font=font_title,
    )
    style.configure(
        "HeaderSub.TLabel",
        background=C["header"],
        foreground="#94A3B8",
        font=font_sub,
    )
    style.configure(
        "Section.TLabel",
        background=C["card"],
        foreground=C["accent_hi"],
        font=("Segoe UI Semibold", 10),
    )

    style.configure(
        "Card.TLabelframe",
        background=C["card"],
        foreground=C["text"],
        bordercolor=C["line"],
        relief="solid",
        borderwidth=1,
    )
    style.configure(
        "Card.TLabelframe.Label",
        background=C["card"],
        foreground=C["accent_hi"],
        font=("Segoe UI Semibold", 10),
    )

    style.configure(
        "TEntry",
        fieldbackground=C["input_bg"],
        foreground=C["text"],
        bordercolor=C["line"],
        lightcolor=C["accent"],
        darkcolor=C["line"],
        insertcolor=C["text"],
        padding=4,
    )
    style.configure(
        "TCombobox",
        fieldbackground=C["input_bg"],
        foreground=C["text"],
        bordercolor=C["line"],
        padding=3,
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", C["input_bg"])],
        selectbackground=[("readonly", C["accent"])],
    )

    style.configure("TCheckbutton", background=C["card"], foreground=C["text"], font=font_ui)
    style.map("TCheckbutton", background=[("active", C["card"])])

    style.configure(
        "TButton",
        background=C["card"],
        foreground=C["text"],
        bordercolor=C["line"],
        focusthickness=1,
        focuscolor=C["accent"],
        padding=(12, 6),
        font=font_ui,
    )
    style.map(
        "TButton",
        background=[("active", "#F1F5F9"), ("disabled", "#E2E8F0")],
        foreground=[("disabled", "#94A3B8")],
    )

    style.configure(
        "Accent.TButton",
        background=C["accent"],
        foreground="#FFFFFF",
        bordercolor=C["accent_hi"],
        padding=(16, 7),
        font=font_btn,
    )
    style.map(
        "Accent.TButton",
        background=[("active", C["accent_hi"]), ("disabled", "#99F6E4")],
        foreground=[("disabled", "#F0FDFA")],
    )

    style.configure(
        "Danger.TButton",
        background=C["danger"],
        foreground="#FFFFFF",
        bordercolor=C["danger_hi"],
        padding=(14, 7),
        font=font_btn,
    )
    style.map(
        "Danger.TButton",
        background=[("active", C["danger_hi"]), ("disabled", "#FECACA")],
    )

    style.configure(
        "Ghost.TButton",
        background=C["card"],
        foreground=C["muted"],
        bordercolor=C["line"],
        padding=(10, 5),
        font=font_sub,
    )

    style.configure(
        "Horizontal.TProgressbar",
        troughcolor="#E2E8F0",
        background=C["accent"],
        bordercolor=C["line"],
        lightcolor=C["accent"],
        darkcolor=C["accent_hi"],
        thickness=14,
    )

    style.configure("TPanedwindow", background=C["bg"])
    style.configure("Sash", sashthickness=4)

    return style


def _style_text(widget: tk.Text, *, log_tags: bool = False) -> None:
    widget.configure(
        bg=C["input_bg"],
        fg=C["text"],
        insertbackground=C["text"],
        selectbackground=C["accent"],
        selectforeground="#FFFFFF",
        relief="flat",
        borderwidth=0,
        highlightthickness=1,
        highlightbackground=C["line"],
        highlightcolor=C["accent"],
        font=("Cascadia Mono", 10) if _font_exists("Cascadia Mono") else ("Consolas", 10),
        padx=8,
        pady=8,
    )
    if log_tags:
        widget.tag_configure("ok", foreground=C["ok"])
        widget.tag_configure("fail", foreground=C["fail"])
        widget.tag_configure("run", foreground=C["run"])
        widget.tag_configure("skip", foreground=C["muted"])
        widget.tag_configure("cancel", foreground="#B45309")
        widget.tag_configure("sep", foreground=C["accent_hi"])


def _log_line_tag(line: str) -> str | None:
    s = line.lstrip()
    if s.startswith("----"):
        return "sep"
    if s.startswith("OK") or s.startswith("X 完成") or s.startswith("完成:"):
        return "ok"
    if s.startswith("FAIL") or s.startswith("异常:"):
        return "fail"
    if s.startswith("SKIP") or s.startswith("OK(skip)"):
        return "skip"
    if s.startswith("CANCEL") or s.startswith("正在停止"):
        return "cancel"
    if s.startswith("开始") or s.startswith("fxtwitter") or s.startswith("直链") or s.startswith("断点"):
        return "run"
    return None



def _style_listbox(widget: tk.Listbox) -> None:
    widget.configure(
        bg=C["input_bg"],
        fg=C["text"],
        selectbackground=C["accent"],
        selectforeground="#FFFFFF",
        activestyle="none",
        relief="flat",
        borderwidth=0,
        highlightthickness=1,
        highlightbackground=C["line"],
        highlightcolor=C["accent"],
        font=("Segoe UI", 9),
    )


def _font_exists(name: str) -> bool:
    try:
        import tkinter.font as tkfont

        return name in tkfont.families()
    except Exception:
        return False


class PromptBridge:
    def __init__(self, root: tk.Tk):
        self.root = root
        self._event = threading.Event()
        self._value = ""
        self._title = ""
        self._prompt = ""

    def ask(self, title: str, prompt: str, default: str = "") -> str:
        self._title = title
        self._prompt = prompt
        self._value = default
        self._event.clear()
        self.root.after(0, self._show_dialog)
        self._event.wait(timeout=600)
        return (self._value or "").strip()

    def _show_dialog(self) -> None:
        win = tk.Toplevel(self.root)
        win.title(self._title)
        win.configure(bg=C["card"])
        win.transient(self.root)
        win.grab_set()
        win.geometry("400x160")
        ttk.Label(win, text=self._prompt, wraplength=360, style="Card.TLabel").pack(
            padx=16, pady=(16, 8), anchor="w"
        )
        var = tk.StringVar(value=self._value)
        entry = ttk.Entry(win, textvariable=var, width=42)
        entry.pack(padx=16, pady=6, fill="x")
        entry.focus_set()

        def ok(_event=None):
            self._value = var.get()
            win.destroy()
            self._event.set()

        def cancel():
            self._value = ""
            win.destroy()
            self._event.set()

        btns = ttk.Frame(win, style="Card.TFrame")
        btns.pack(pady=12)
        ttk.Button(btns, text="确定", style="Accent.TButton", command=ok).pack(side="left", padx=6)
        ttk.Button(btns, text="取消", command=cancel).pack(side="left", padx=6)
        win.bind("<Return>", ok)
        win.protocol("WM_DELETE_WINDOW", cancel)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"Media Download  v{VERSION}")
        self.geometry("1000x740")
        self.minsize(860, 620)

        self.cfg_path = CONFIG_PATH
        self.busy = False
        self.control: DownloadControl | None = None
        self.bridge = PromptBridge(self)
        self._hist_all: list[dict] = []
        self._hist_entries: list[dict] = []
        self._queue_urls: list[str] = []
        self._queue_status: dict[str, str] = {}
        self._queue_index = (0, 0)

        self.api_id = tk.StringVar()
        self.api_hash = tk.StringVar()
        self.phone = tk.StringVar()
        self.download_dir = tk.StringVar()
        self.proxy_enabled = tk.BooleanVar(value=True)
        self.proxy_type = tk.StringVar(value="socks5")
        self.proxy_addr = tk.StringVar(value="127.0.0.1")
        self.proxy_port = tk.StringVar(value="7892")
        self.skip_existing = tk.BooleanVar(value=True)
        self.download_group = tk.BooleanVar(value=True)
        self.hist_filter = tk.StringVar(value="全部")
        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress_text = tk.StringVar(value="就绪")
        self.account_text = tk.StringVar(value="未登录")
        self.status_bar = tk.StringVar(value="")
        self._tg_expanded = tk.BooleanVar(value=False)

        apply_theme(self)
        self._build()
        self._load_ui_from_config()
        self._refresh_status_bar()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind_all("<Control-Return>", lambda _e: self._start())
        self.after(15000, self._tick_status)

    def _card(self, parent, title: str) -> ttk.LabelFrame:
        box = ttk.LabelFrame(parent, text=f"  {title}  ", style="Card.TLabelframe")
        return box

    def _build(self) -> None:
        # —— 顶栏 ——
        header = ttk.Frame(self, style="Header.TFrame")
        header.pack(fill="x")
        head_inner = ttk.Frame(header, style="Header.TFrame")
        head_inner.pack(fill="x", padx=20, pady=14)
        ttk.Label(head_inner, text="Media Download", style="HeaderTitle.TLabel").pack(side="left")
        ttk.Label(
            head_inner,
            text="  Telegram / X 视频下载",
            style="HeaderSub.TLabel",
        ).pack(side="left", padx=(8, 0), pady=(4, 0))
        ttk.Label(head_inner, textvariable=self.account_text, style="HeaderSub.TLabel").pack(
            side="right", pady=(4, 0)
        )

        main = ttk.Frame(self)
        main.pack(fill="both", expand=True, padx=14, pady=12)

        # —— 配置 ——
        cfg_f = self._card(main, "连接配置")
        cfg_f.pack(fill="x", pady=(0, 10))
        cfg_in = ttk.Frame(cfg_f, style="Card.TFrame")
        cfg_in.pack(fill="x", padx=12, pady=10)

        # Telegram 凭证（可折叠；纯 X 不用看）
        tg_bar = ttk.Frame(cfg_in, style="Card.TFrame")
        tg_bar.pack(fill="x", pady=(0, 4))
        self._tg_toggle_btn = ttk.Button(
            tg_bar,
            text="▸  Telegram 登录（下 t.me 时需要）",
            style="Ghost.TButton",
            command=self._toggle_tg_panel,
        )
        self._tg_toggle_btn.pack(side="left")
        self._tg_panel = ttk.Frame(cfg_in, style="Card.TFrame")
        # 默认折叠，不 pack

        r1 = ttk.Frame(self._tg_panel, style="Card.TFrame")
        r1.pack(fill="x", pady=3)
        ttk.Label(r1, text="api_id", width=10, style="CardMuted.TLabel").pack(side="left")
        ttk.Entry(r1, textvariable=self.api_id, width=14).pack(side="left", padx=(0, 16))
        ttk.Label(r1, text="api_hash", style="CardMuted.TLabel").pack(side="left")
        ttk.Entry(r1, textvariable=self.api_hash, show="•").pack(
            side="left", padx=8, fill="x", expand=True
        )

        r2 = ttk.Frame(self._tg_panel, style="Card.TFrame")
        r2.pack(fill="x", pady=3)
        ttk.Label(r2, text="手机号", width=10, style="CardMuted.TLabel").pack(side="left")
        ttk.Entry(r2, textvariable=self.phone, width=18).pack(side="left", padx=(0, 16))

        r_dir = ttk.Frame(cfg_in, style="Card.TFrame")
        r_dir.pack(fill="x", pady=3)
        ttk.Label(r_dir, text="下载目录", width=10, style="CardMuted.TLabel").pack(side="left")
        ttk.Entry(r_dir, textvariable=self.download_dir).pack(
            side="left", padx=8, fill="x", expand=True
        )
        ttk.Button(r_dir, text="浏览", style="Ghost.TButton", command=self._browse_dir).pack(
            side="left"
        )

        r3 = ttk.Frame(cfg_in, style="Card.TFrame")
        r3.pack(fill="x", pady=(6, 0))
        ttk.Checkbutton(r3, text="代理", variable=self.proxy_enabled).pack(side="left")
        ttk.Combobox(
            r3,
            textvariable=self.proxy_type,
            values=("socks5", "socks4", "http"),
            width=8,
            state="readonly",
        ).pack(side="left", padx=(8, 4))
        ttk.Entry(r3, textvariable=self.proxy_addr, width=12).pack(side="left", padx=2)
        ttk.Label(r3, text=":", style="Card.TLabel").pack(side="left")
        ttk.Entry(r3, textvariable=self.proxy_port, width=6).pack(side="left", padx=2)
        ttk.Checkbutton(r3, text="跳过已下载", variable=self.skip_existing).pack(
            side="left", padx=(16, 0)
        )
        ttk.Checkbutton(r3, text="下载媒体组", variable=self.download_group).pack(
            side="left", padx=(12, 0)
        )

        # —— 链接 / 队列 ——
        mid = ttk.Panedwindow(main, orient="horizontal")
        mid.pack(fill="both", expand=True, pady=(0, 10))

        url_f = self._card(mid, "链接（t.me / x.com，每行一条）")
        queue_f = self._card(mid, "下载队列")
        mid.add(url_f, weight=3)
        mid.add(queue_f, weight=2)

        url_toolbar = ttk.Frame(url_f, style="Card.TFrame")
        url_toolbar.pack(fill="x", padx=10, pady=(8, 0))
        ttk.Label(
            url_toolbar,
            text="Ctrl+Enter 开始",
            style="CardMuted.TLabel",
        ).pack(side="left")
        ttk.Button(
            url_toolbar, text="粘贴", style="Ghost.TButton", command=self._paste_urls
        ).pack(side="right")
        ttk.Button(
            url_toolbar, text="清空", style="Ghost.TButton", command=self._clear_urls
        ).pack(side="right", padx=(0, 6))

        self.url_text = tk.Text(url_f, height=6, wrap="none")
        _style_text(self.url_text)
        self.url_text.pack(fill="both", expand=True, padx=10, pady=10)

        self.queue_list = tk.Listbox(queue_f, height=5)
        _style_listbox(self.queue_list)
        self.queue_list.pack(fill="both", expand=True, padx=10, pady=(10, 4))
        qops = ttk.Frame(queue_f, style="Card.TFrame")
        qops.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Button(qops, text="重试选中", style="Ghost.TButton", command=self._retry_selected_fail).pack(
            side="left"
        )
        ttk.Button(qops, text="重试全部失败", style="Ghost.TButton", command=self._retry_all_fail).pack(
            side="left", padx=6
        )

        # —— 操作条 ——
        ops = ttk.Frame(main)
        ops.pack(fill="x", pady=(0, 8))
        self.btn_start = ttk.Button(ops, text="▶  开始下载", style="Accent.TButton", command=self._start)
        self.btn_start.pack(side="left")
        self.btn_stop = ttk.Button(
            ops, text="■  停止", style="Danger.TButton", command=self._stop, state="disabled"
        )
        self.btn_stop.pack(side="left", padx=8)
        self.btn_save = ttk.Button(ops, text="保存配置", command=self._save_config)
        self.btn_save.pack(side="left", padx=(4, 0))
        ttk.Button(ops, text="打开目录", style="Ghost.TButton", command=self._open_dir).pack(
            side="left", padx=8
        )
        ttk.Button(ops, text="导出日志", style="Ghost.TButton", command=self._export_log).pack(side="left")

        # —— 进度 ——
        prog_f = self._card(main, "下载进度")
        prog_f.pack(fill="x", pady=(0, 10))
        prog_inner = ttk.Frame(prog_f, style="Card.TFrame")
        prog_inner.pack(fill="x", padx=12, pady=10)
        ttk.Progressbar(prog_inner, variable=self.progress_var, maximum=100).pack(fill="x")
        ttk.Label(prog_inner, textvariable=self.progress_text, style="CardMuted.TLabel").pack(
            anchor="w", pady=(6, 0)
        )

        # —— 日志 / 历史 ——
        bottom = ttk.Panedwindow(main, orient="horizontal")
        bottom.pack(fill="both", expand=True)

        log_f = self._card(bottom, "运行日志")
        hist_f = self._card(bottom, "下载历史")
        bottom.add(log_f, weight=3)
        bottom.add(hist_f, weight=2)

        self.log_text = tk.Text(log_f, height=12, wrap="word", state="disabled")
        _style_text(self.log_text, log_tags=True)
        self.log_text.pack(fill="both", expand=True, padx=10, pady=10)

        htop = ttk.Frame(hist_f, style="Card.TFrame")
        htop.pack(fill="x", padx=10, pady=(10, 4))
        ttk.Label(htop, text="筛选", style="CardMuted.TLabel").pack(side="left")
        cb = ttk.Combobox(
            htop,
            textvariable=self.hist_filter,
            values=("全部", "完成", "失败", "跳过"),
            width=8,
            state="readonly",
        )
        cb.pack(side="left", padx=6)
        cb.bind("<<ComboboxSelected>>", lambda _e: self._apply_hist_filter())
        ttk.Button(htop, text="刷新", style="Ghost.TButton", command=self._refresh_history).pack(
            side="left", padx=2
        )
        ttk.Button(htop, text="清失败", style="Ghost.TButton", command=self._clear_fail_history).pack(
            side="left", padx=2
        )
        ttk.Button(htop, text="清空", style="Ghost.TButton", command=self._clear_history).pack(
            side="left", padx=2
        )

        self.hist_list = tk.Listbox(hist_f, height=10)
        _style_listbox(self.hist_list)
        self.hist_list.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.hist_list.bind("<Double-Button-1>", self._open_history_item)
        self.hist_list.bind("<Button-3>", self._history_context)

        # —— 底栏 ——
        foot = tk.Frame(self, bg=C["card"], highlightbackground=C["line"], highlightthickness=1)
        foot.pack(fill="x", side="bottom")
        ttk.Label(foot, textvariable=self.status_bar, style="CardMuted.TLabel").pack(
            anchor="w", padx=14, pady=6
        )

    def _download_path(self) -> Path:
        d = Path(self.download_dir.get() or "downloads")
        return d if d.is_absolute() else ROOT / d

    def _toggle_tg_panel(self) -> None:
        if self._tg_expanded.get():
            self._tg_panel.pack_forget()
            self._tg_expanded.set(False)
            self._tg_toggle_btn.configure(text="▸  Telegram 登录（下 t.me 时需要）")
            return
        # 插在 Telegram 标题行之后、下载目录之前
        self._tg_panel.pack(fill="x", after=self._tg_toggle_btn.master)
        self._tg_expanded.set(True)
        self._tg_toggle_btn.configure(text="▾  Telegram 登录（下 t.me 时需要）")

    def _ensure_tg_panel(self, open_: bool = True) -> None:
        if open_ == self._tg_expanded.get():
            return
        self._toggle_tg_panel()

    def _paste_urls(self) -> None:
        try:
            text = self.clipboard_get()
        except tk.TclError:
            return
        text = (text or "").strip()
        if not text:
            return
        cur = self.url_text.get("1.0", "end").strip()
        if cur:
            self.url_text.insert("end", "\n" + text + "\n")
        else:
            self.url_text.insert("1.0", text + "\n")

    def _clear_urls(self) -> None:
        self.url_text.delete("1.0", "end")

    def _refresh_status_bar(self) -> None:
        crypt = "cryptg ON" if HAS_CRYPTG else "cryptg OFF"
        try:
            free = disk_free_gb(self._download_path())
            disk = f"磁盘 {free:.1f} GB"
        except Exception:
            disk = "磁盘 ?"
        self.status_bar.set(f"v{VERSION}    ·    {crypt}    ·    {disk}")

    def _tick_status(self) -> None:
        self._refresh_status_bar()
        self.after(15000, self._tick_status)

    def _load_ui_from_config(self) -> None:
        try:
            cfg = load_config(self.cfg_path)
        except Exception as e:
            self._log(f"加载配置失败: {e}")
            return
        self.api_id.set(str(cfg.get("api_id", "")))
        self.api_hash.set(str(cfg.get("api_hash", "")))
        self.phone.set(str(cfg.get("phone") or ""))
        self.download_dir.set(str(cfg.get("download_dir") or "downloads"))
        proxy = cfg.get("proxy") or {}
        self.proxy_enabled.set(bool(proxy.get("enabled")))
        self.proxy_type.set(str(proxy.get("type") or "socks5"))
        self.proxy_addr.set(str(proxy.get("addr") or "127.0.0.1"))
        self.proxy_port.set(str(proxy.get("port") or 1080))
        opts = cfg.get("options") or {}
        self.skip_existing.set(bool(opts.get("skip_existing", True)))
        self.download_group.set(bool(opts.get("download_group", True)))
        acc = cfg.get("account") or {}
        if acc.get("user_id"):
            self.account_text.set(f"账号 {acc.get('user_id')}  @{acc.get('username') or '-'}")
            self._ensure_tg_panel(True)
        else:
            self.account_text.set("未登录")
        self._refresh_history()
        hist = load_history()
        urls = [h.get("url") for h in hist if h.get("url")]
        if urls and not self.url_text.get("1.0", "end").strip():
            self.url_text.insert("1.0", urls[-1] + "\n")
        self._refresh_status_bar()

    def _collect_config(self, *, require_tg: bool = False) -> dict:
        try:
            cfg = load_config(self.cfg_path)
        except Exception:
            cfg = {"session": "tg_download", "account": {}, "last_run": {}}
        aid = self.api_id.get().strip()
        ahash = self.api_hash.get().strip()
        if require_tg:
            if not aid or not ahash or ahash.startswith("your_"):
                raise ValueError("下载 Telegram 链接需要填写 api_id / api_hash")
            cfg["api_id"] = int(aid)
            cfg["api_hash"] = ahash
        else:
            if aid:
                cfg["api_id"] = int(aid)
            if ahash:
                cfg["api_hash"] = ahash
        cfg["phone"] = self.phone.get().strip()
        cfg["download_dir"] = self.download_dir.get().strip() or "downloads"
        cfg["proxy"] = {
            "enabled": bool(self.proxy_enabled.get()),
            "type": self.proxy_type.get().strip() or "socks5",
            "addr": self.proxy_addr.get().strip() or "127.0.0.1",
            "port": int(self.proxy_port.get().strip() or 1080),
            "username": (cfg.get("proxy") or {}).get("username"),
            "password": (cfg.get("proxy") or {}).get("password"),
        }
        opts = dict(cfg.get("options") or {})
        opts["skip_existing"] = bool(self.skip_existing.get())
        opts["download_group"] = bool(self.download_group.get())
        opts.setdefault("connection_retries", 5)
        opts.setdefault("timeout", 30)
        opts.setdefault("max_retries", 3)
        opts.setdefault("request_size_kb", 512)
        cfg["options"] = opts
        return cfg

    def _save_config(self) -> None:
        try:
            cfg = self._collect_config()
            save_config(cfg, self.cfg_path)
            self._log("配置已保存")
            self._refresh_status_bar()
            messagebox.showinfo("保存", "config.json 已更新")
        except Exception as e:
            messagebox.showerror("保存失败", str(e))

    def _browse_dir(self) -> None:
        path = filedialog.askdirectory(initialdir=str(self._download_path()))
        if path:
            self.download_dir.set(path)
            self._refresh_status_bar()

    def _open_dir(self) -> None:
        d = self._download_path()
        d.mkdir(parents=True, exist_ok=True)
        os.startfile(str(d))

    def _urls(self) -> list[str]:
        raw = self.url_text.get("1.0", "end").splitlines()
        seen, out = set(), []
        for line in raw:
            u = line.strip()
            if not u or u.startswith("#") or u in seen:
                continue
            seen.add(u)
            out.append(u)
        return out

    def _init_queue(self, urls: list[str]) -> None:
        self._queue_urls = list(urls)
        self._queue_status = {u: "pending" for u in urls}

        def upd():
            self.queue_list.delete(0, "end")
            for u in urls:
                self.queue_list.insert("end", f"[{STATUS_CN['pending']}]  {u}")
                self.queue_list.itemconfig("end", fg=STATUS_FG["pending"])

        self.after(0, upd)

    def _set_queue_status(self, url: str, status: str, idx: int = 0, total: int = 0) -> None:
        self._queue_status[url] = status
        if idx and total:
            self._queue_index = (idx, total)
        label = STATUS_CN.get(status, status)
        color = STATUS_FG.get(status, C["text"])

        def upd():
            for i, u in enumerate(self._queue_urls):
                if u == url:
                    self.queue_list.delete(i)
                    self.queue_list.insert(i, f"[{label}]  {u}")
                    self.queue_list.itemconfig(i, fg=color)
                    self.queue_list.see(i)
                    break
            if idx and total:
                self.progress_text.set(f"队列 {idx}/{total}  ·  {label}")

        self.after(0, upd)

    def _failed_urls(self) -> list[str]:
        return [u for u, s in self._queue_status.items() if s == "fail"]

    def _retry_all_fail(self) -> None:
        fails = self._failed_urls()
        if not fails:
            seen: set[str] = set()
            for h in load_history():
                u = h.get("url")
                if h.get("status") == "fail" and u and u not in seen:
                    seen.add(u)
                    fails.append(u)
        if not fails:
            messagebox.showinfo("重试", "没有失败项")
            return
        self.url_text.delete("1.0", "end")
        self.url_text.insert("1.0", "\n".join(fails) + "\n")
        self._start()

    def _retry_selected_fail(self) -> None:
        sel = self.queue_list.curselection()
        if not sel:
            messagebox.showinfo("重试", "请先在队列里选中一条失败项")
            return
        i = sel[0]
        url = self._queue_urls[i]
        if self._queue_status.get(url) != "fail":
            messagebox.showinfo("重试", "选中项不是失败状态")
            return
        self.url_text.delete("1.0", "end")
        self.url_text.insert("1.0", url + "\n")
        self._start()

    def _log(self, msg: str) -> None:
        def append():
            self.log_text.configure(state="normal")
            line = msg.rstrip() + "\n"
            tag = _log_line_tag(line)
            if tag:
                self.log_text.insert("end", line, tag)
            else:
                self.log_text.insert("end", line)
            self.log_text.see("end")
            self.log_text.configure(state="disabled")

        self.after(0, append)

    def _export_log(self) -> None:
        text = self.log_text.get("1.0", "end").strip()
        if not text:
            messagebox.showinfo("导出", "日志为空")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text", "*.txt"), ("All", "*.*")],
            initialfile=f"tg_download_log_{datetime.now():%Y%m%d_%H%M%S}.txt",
            initialdir=str(ROOT),
        )
        if not path:
            return
        Path(path).write_text(text + "\n", encoding="utf-8")
        self._log(f"日志已导出: {path}")

    def _clear_history(self) -> None:
        if not messagebox.askyesno("清空历史", "确定清空全部 history.jsonl？"):
            return
        n = clear_history()
        self._refresh_history()
        self._log(f"历史已清空 ({n} 条)")

    def _clear_fail_history(self) -> None:
        n = clear_history(status="fail")
        self._refresh_history()
        self._log(f"已清除失败记录 {n} 条")

    @staticmethod
    def _fmt_eta(sec: float | None) -> str:
        if sec is None or sec < 0 or sec == float("inf"):
            return "-"
        sec = int(sec)
        if sec < 60:
            return f"{sec}s"
        if sec < 3600:
            return f"{sec // 60}m{sec % 60:02d}s"
        return f"{sec // 3600}h{(sec % 3600) // 60:02d}m"

    def _set_progress(self, current: int, total: int, speed: float = 0.0, eta=None) -> None:
        pct = 0.0 if total <= 0 else current * 100 / total
        mb_c = current / (1024 * 1024)
        mb_t = total / (1024 * 1024)
        spd = f"{speed / 1024 / 1024:.2f} MB/s" if speed and speed > 0 else "- MB/s"
        qi, qt = self._queue_index
        prefix = f"{qi}/{qt}  ·  " if qt else ""
        text = f"{prefix}{pct:5.1f}%   {mb_c:.1f}/{mb_t:.1f} MB   {spd}   ETA {self._fmt_eta(eta)}"

        def upd():
            self.progress_var.set(pct)
            self.progress_text.set(text)

        self.after(0, upd)

    def _refresh_history(self, _cfg=None) -> None:
        self._hist_all = list(reversed(load_history()))[:200]
        self._apply_hist_filter()

    def _apply_hist_filter(self) -> None:
        mapping = {"全部": None, "完成": "ok", "失败": "fail", "跳过": "skip"}
        want = mapping.get(self.hist_filter.get(), None)
        items = self._hist_all if want is None else [h for h in self._hist_all if h.get("status") == want]
        self._hist_entries = items

        def upd():
            self.hist_list.delete(0, "end")
            for h in items:
                st_key = h.get("status", "")
                st = STATUS_CN.get(st_key, st_key or "?")
                url = h.get("url") or ""
                self.hist_list.insert("end", f"[{st}]  {url}")
                self.hist_list.itemconfig("end", fg=STATUS_FG.get(st_key, C["text"]))

        self.after(0, upd)

    def _open_history_item(self, _event=None) -> None:
        sel = self.hist_list.curselection()
        if not sel:
            return
        entry = self._hist_entries[sel[0]]
        path = entry.get("file")
        if path and Path(path).is_file():
            os.startfile(path)
        elif entry.get("url"):
            self.url_text.delete("1.0", "end")
            self.url_text.insert("1.0", entry["url"] + "\n")

    def _history_context(self, event) -> None:
        idx = self.hist_list.nearest(event.y)
        if idx < 0 or idx >= len(self._hist_entries):
            return
        self.hist_list.selection_clear(0, "end")
        self.hist_list.selection_set(idx)
        entry = self._hist_entries[idx]
        menu = tk.Menu(
            self,
            tearoff=0,
            bg=C["card"],
            fg=C["text"],
            activebackground=C["accent"],
            activeforeground="#FFFFFF",
            relief="flat",
            borderwidth=1,
        )
        menu.add_command(label="打开文件", command=lambda: self._hist_open_file(entry))
        menu.add_command(label="打开所在目录", command=lambda: self._hist_open_folder(entry))
        menu.add_command(label="填入链接框", command=lambda: self._hist_fill_url(entry))
        menu.add_command(label="重试此链接", command=lambda: self._hist_retry(entry))
        menu.tk_popup(event.x_root, event.y_root)

    def _hist_open_file(self, entry: dict) -> None:
        path = entry.get("file")
        if path and Path(path).is_file():
            os.startfile(path)
        else:
            messagebox.showinfo("提示", "无本地文件")

    def _hist_open_folder(self, entry: dict) -> None:
        path = entry.get("file")
        if path and Path(path).exists():
            os.startfile(str(Path(path).parent))
        else:
            self._open_dir()

    def _hist_fill_url(self, entry: dict) -> None:
        if entry.get("url"):
            self.url_text.delete("1.0", "end")
            self.url_text.insert("1.0", entry["url"] + "\n")

    def _hist_retry(self, entry: dict) -> None:
        if not entry.get("url"):
            return
        self._hist_fill_url(entry)
        self._start()

    def _set_busy(self, busy: bool) -> None:
        self.busy = busy

        def upd():
            self.btn_start.configure(state="disabled" if busy else "normal")
            self.btn_save.configure(state="disabled" if busy else "normal")
            self.btn_stop.configure(state="normal" if busy else "disabled")

        self.after(0, upd)

    def _stop(self) -> None:
        if self.control:
            self.control.cancel()
            self._log("正在停止…（保留 .part 以便续传）")
            self.progress_text.set("停止中...")

    def _precheck_disk(self) -> bool:
        try:
            free = disk_free_gb(self._download_path())
        except Exception as e:
            messagebox.showerror("磁盘", str(e))
            return False
        if free < 0.5:
            return messagebox.askyesno(
                "磁盘空间不足",
                f"下载目录仅剩 {free:.2f} GB，可能不够。仍要继续？",
            )
        return True

    def _start(self) -> None:
        if self.busy:
            return
        urls = self._urls()
        if not urls:
            messagebox.showwarning("提示", "请至少填一条 t.me 或 x.com 链接")
            return
        bad = [u for u in urls if link_kind(u) == "unknown"]
        if bad:
            messagebox.showwarning(
                "链接无效",
                "仅支持 Telegram / X(Twitter) 链接，例如：\n"
                "https://t.me/c/…/…\n"
                "https://x.com/user/status/…\n\n"
                f"无效: {bad[0]}",
            )
            return
        if not self._precheck_disk():
            return
        need_tg = any(link_kind(u) == "tg" for u in urls)
        if need_tg:
            self._ensure_tg_panel(True)
        try:
            cfg = self._collect_config(require_tg=need_tg)
            save_config(cfg, self.cfg_path)
        except Exception as e:
            messagebox.showerror("配置错误", str(e))
            return

        self.control = DownloadControl()
        self._queue_index = (0, len(urls))
        self._init_queue(urls)
        self._set_busy(True)
        self.progress_var.set(0)
        self.progress_text.set(f"连接中…  0/{len(urls)}")
        self._log("---- 开始下载 ----")
        self._refresh_status_bar()

        def worker():
            phone_default = (cfg.get("phone") or "").strip()

            def phone_cb():
                val = self.bridge.ask("登录", "请输入手机号（含国家码，如 +86138...）", phone_default)
                if val:
                    cfg["phone"] = val
                    save_config(cfg, self.cfg_path)
                    self.after(0, lambda: self.phone.set(val))
                return val

            def code_cb():
                return self.bridge.ask("验证码", "请输入 Telegram 验证码")

            def password_cb():
                return self.bridge.ask("两步验证", "请输入两步验证密码")

            def on_progress(cur, total, speed=0.0, eta=None):
                self._set_progress(cur, total, speed, eta)

            def on_status(url, status, idx=0, total=0):
                self._set_queue_status(url, status, idx, total)

            summary = {"code": 1}
            try:
                code = asyncio.run(
                    run(
                        urls,
                        self.cfg_path,
                        cfg=cfg,
                        progress_callback=on_progress,
                        log=self._log,
                        phone_callback=phone_cb if not phone_default else phone_default,
                        code_callback=code_cb,
                        password_callback=password_cb,
                        control=self.control,
                        status_callback=on_status,
                    )
                )
                summary["code"] = code
                self._log(f"退出码: {code}")
            except Exception as e:
                self._log(f"异常: {e}")
                self.after(0, lambda: messagebox.showerror("下载失败", str(e)))
            finally:
                self.control = None
                self._set_busy(False)
                self.after(0, self._load_ui_from_config)
                self.after(0, lambda: self.progress_text.set("完成"))
                self.after(0, lambda: self._done_notify(summary["code"], urls))

        threading.Thread(target=worker, daemon=True).start()

    def _done_notify(self, code: int, urls: list[str]) -> None:
        fails = self._failed_urls()
        ok_n = sum(1 for s in self._queue_status.values() if s in ("ok", "skip"))
        title = "下载完成" if code == 0 else "下载结束（有失败）"
        msg = f"队列 {len(urls)} 条\n成功/跳过: {ok_n}\n失败: {len(fails)}"
        if fails:
            msg += "\n\n可用「重试全部失败」重新下载。"
        try:
            self.deiconify()
            self.lift()
            self.attributes("-topmost", True)
            self.after(200, lambda: self.attributes("-topmost", False))
        except Exception:
            pass
        messagebox.showinfo(title, msg)

    def _on_close(self) -> None:
        if self.busy and self.control:
            if not messagebox.askyesno("退出", "正在下载，确定停止并退出？"):
                return
            self.control.cancel()
        release_instance_lock()
        self.destroy()


def main() -> None:
    if not acquire_instance_lock():
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("已在运行", f"Media Download v{VERSION} 已在运行")
        root.destroy()
        raise SystemExit(2)
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
