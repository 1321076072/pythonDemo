"""config.json + history.jsonl。历史与配置分离，避免大 JSON 反复整文件重写。"""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

from tgdl.paths import CONFIG_PATH, HISTORY_MAX, HISTORY_PATH


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def atomic_write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    data = json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
    with tmp.open("w", encoding="utf-8", newline="\n") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def load_config(path: Path = CONFIG_PATH) -> dict:
    if not path.exists():
        example = path.with_name("config.example.json")
        raise FileNotFoundError(
            f"缺少 {path.name}。复制 {example.name} 为 {path.name}，填入 api_id / api_hash。"
        )
    with path.open(encoding="utf-8") as f:
        cfg = json.load(f)
    # api_id/api_hash 仅在跑 TG 链接时由 runner 强校验；纯 X 下载可空着
    cfg.setdefault("phone", "")
    cfg.setdefault("session", "tg_download")
    cfg.setdefault("download_dir", "downloads")
    cfg.setdefault("proxy", {"enabled": False})
    cfg.setdefault(
        "options",
        {
            "skip_existing": True,
            "connection_retries": 5,
            "timeout": 30,
            "max_retries": 3,
            "download_group": True,
            "request_size_kb": 512,
        },
    )
    opts = cfg["options"]
    opts.setdefault("max_retries", 3)
    opts.setdefault("download_group", True)
    opts.setdefault("request_size_kb", 512)
    cfg.setdefault("account", {})
    cfg.setdefault("last_run", {})

    # 旧版把 history 嵌在 config：迁出一次
    old_hist = cfg.pop("history", None)
    if old_hist:
        for entry in old_hist:
            append_history(entry)
        atomic_write_json(path, cfg)
    return cfg


def save_config(cfg: dict, path: Path = CONFIG_PATH) -> None:
    out = {k: v for k, v in cfg.items() if k != "history"}
    atomic_write_json(path, out)


def load_history(limit: int = HISTORY_MAX) -> list[dict]:
    if not HISTORY_PATH.exists():
        return []
    rows: list[dict] = []
    with HISTORY_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows[-limit:]


def append_history(entry: dict) -> None:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY_PATH.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    rows = load_history(limit=HISTORY_MAX * 2)
    if len(rows) > HISTORY_MAX:
        tmp = HISTORY_PATH.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8", newline="\n") as f:
            for r in rows[-HISTORY_MAX:]:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        os.replace(tmp, HISTORY_PATH)


def clear_history(status: str | None = None) -> int:
    """清空历史。status=fail 等则只删该状态。返回删除条数。"""
    rows = load_history(limit=10_000)
    if status is None:
        n = len(rows)
        HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        HISTORY_PATH.write_text("", encoding="utf-8")
        return n
    keep = [r for r in rows if r.get("status") != status]
    removed = len(rows) - len(keep)
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY_PATH.open("w", encoding="utf-8", newline="\n") as f:
        for r in keep[-HISTORY_MAX:]:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return removed


def history_ok(url: str, msg_id: int | None = None) -> dict | None:
    for item in reversed(load_history()):
        if item.get("status") != "ok" or not item.get("file"):
            continue
        if msg_id is not None and item.get("msg_id") == msg_id:
            return item
        if item.get("url") == url:
            return item
    return None


def disk_free_gb(path: Path) -> float:
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return shutil.disk_usage(path).free / (1024**3)


def ensure_disk_space(dir_path: Path, need: int | None, margin: int = 64 * 1024 * 1024) -> None:
    if not need or need <= 0:
        return
    dir_path.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(dir_path).free
    if free < need + margin:
        raise RuntimeError(
            f"磁盘空间不足: 需要约 {need/1024/1024:.0f}MB，剩余 {free/1024/1024:.0f}MB"
        )


def record_result(
    cfg: dict,
    *,
    url: str,
    chat,
    msg_id: int,
    path: Path | None,
    size: int | None,
    status: str,
    error: str | None = None,
    note: str | None = None,
) -> None:
    entry = {
        "url": url,
        "chat": chat,
        "msg_id": msg_id,
        "file": str(path.resolve()) if path else None,
        "size": size,
        "status": status,
        "time": now_iso(),
    }
    if error:
        entry["error"] = error
    if note:
        entry["note"] = note
    append_history(entry)
    cfg["last_run"] = {
        "at": now_iso(),
        "current_url": url,
        "chat": chat,
        "msg_id": msg_id,
        "status": status,
        "file": entry["file"],
        "size": size,
        "error": error,
    }
