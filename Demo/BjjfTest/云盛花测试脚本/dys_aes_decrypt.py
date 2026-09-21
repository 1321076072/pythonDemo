#!/usr/bin/env python3
"""德云晟短信 API 请求体解密。

对齐 Java: AesUtils.decrypt + isPro()==true
  AES/CBC/PKCS5Padding, 密钥 Base64 解码为 16 字节, IV 取请求头 X-IV。

用法:
  python dys_aes_decrypt.py CIPHER IV [CIPHER IV ...]
  python dys_aes_decrypt.py --log dump.txt
  python dys_aes_decrypt.py --xlsx export.xlsx [--out result.txt]
  type dump.txt | python dys_aes_decrypt.py --log
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import sys
from pathlib import Path

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

# YshConstant.DYS_XD_SMS_AES_KEY_PRO / DYS_XD_SMS_AES_KEY
AES_KEY_PRO = "iN7lSJCmKZncN0ibYPuMeA=="
AES_KEY_TEST = "6E5a7B4mGku9l46wcLlMLw=="

# 日志指纹：长 Base64 密文 + 请求字节数组 + X-IV。避免把 X-Sign 当成密文。
LOG_RE = re.compile(
    r"(?P<cipher>[A-Za-z0-9+/]{40,}={0,2}).*?"
    r"\[(?:\d{1,3},\s*){8,}\d{1,3}\]"
    r".*?X-IV=(?P<iv>[A-Za-z0-9+/=]+)",
    re.S,
)


def decrypt(cipher_b64: str, iv_b64: str, key_b64: str = AES_KEY_PRO) -> str:
    key = base64.b64decode(key_b64)
    iv = base64.b64decode(iv_b64)
    ct = base64.b64decode(cipher_b64)
    pt = unpad(AES.new(key, AES.MODE_CBC, iv).decrypt(ct), AES.block_size)
    return pt.decode("utf-8")


def pretty(plaintext: str) -> str:
    try:
        return json.dumps(json.loads(plaintext), ensure_ascii=False, indent=2)
    except json.JSONDecodeError:
        return plaintext


def parse_log(text: str) -> list[tuple[str, str]]:
    return [(m["cipher"], m["iv"]) for m in LOG_RE.finditer(text)]


def format_item(i: int, total: int, cipher: str, iv: str, key: str, ts: str = "", raw: str = "") -> tuple[str, bool]:
    """拼一条：原文（日志/密文）+ 解密结果。返回 (文本, 是否成功)。"""
    head = f"===== [{i}/{total}] =====" if not ts else f"===== [{i}/{total}] time={ts} ====="
    origin = raw.strip() if raw else f"cipher={cipher}\niv={iv}"
    try:
        plain = pretty(decrypt(cipher, iv, key))
        ok = True
    except Exception as e:
        plain = f"解密失败: {e}"
        ok = False
    text = "\n".join([head, "[原文]", origin, "[明文]", plain, ""])
    return text, ok


def parse_lines(text: str) -> list[tuple[str, str]]:
    jobs = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = re.split(r"[\s|,]+", line)
        if len(parts) == 2:
            jobs.append((parts[0], parts[1]))
    return jobs


def load_xlsx_jobs(xlsx_path: str) -> list[tuple[str, str, str]]:
    """
    读 ES 导出 xlsx，列: @timestamp | content。
    返回 [(timestamp, cipher, iv, content), ...]，按时间升序。
    """
    from openpyxl import load_workbook

    # 不用 read_only：ES 导出常把 dimension 写成单列，会丢掉 content
    wb = load_workbook(xlsx_path, data_only=True)
    ws = wb.active
    rows = ws.iter_rows(values_only=True)
    header = next(rows, None)
    if not header:
        wb.close()
        return []

    # 兼容列名：@timestamp / logTime / time ；content / 消息
    names = [str(h).strip().lower() if h is not None else "" for h in header]
    ts_i = next((i for i, n in enumerate(names) if "timestamp" in n or "time" in n or n in ("时间",)), None)
    content_i = next((i for i, n in enumerate(names) if n in ("content", "消息", "日志", "message") or "content" in n), None)
    if ts_i is None or content_i is None or ts_i == content_i:
        ts_i, content_i = 0, 1

    jobs: list[tuple[str, str, str, str]] = []
    for row in rows:
        if not row or len(row) <= max(ts_i, content_i):
            continue
        ts = "" if row[ts_i] is None else str(row[ts_i]).strip()
        content = "" if row[content_i] is None else str(row[content_i])
        if not content:
            continue
        for cipher, iv in parse_log(content):
            jobs.append((ts, cipher, iv, content))
    wb.close()
    jobs.sort(key=lambda x: x[0])
    return jobs


def load_jobs(args: argparse.Namespace) -> list[tuple[str, str]]:
    if args.log is not None:
        text = sys.stdin.read() if args.log == "-" else Path(args.log).read_text(encoding="utf-8")
        return parse_log(text) or parse_lines(text)
    if len(args.pairs) % 2:
        raise SystemExit("参数必须成对: CIPHER IV [CIPHER IV ...]")
    return list(zip(args.pairs[::2], args.pairs[1::2]))


def run_xlsx(xlsx: str, key: str, out_path: str | None, preview: int = 5) -> int:
    jobs = load_xlsx_jobs(xlsx)
    if not jobs:
        print("xlsx 中未解析到任何 CIPHER/IV", file=sys.stderr)
        return 1

    lines: list[str] = [
        f"# dys_aes_decrypt xlsx={xlsx}",
        f"# total={len(jobs)} sorted_by=@timestamp",
        "",
    ]
    failed = 0
    for i, (ts, cipher, iv, content) in enumerate(jobs, 1):
        text, ok = format_item(i, len(jobs), cipher, iv, key, ts=ts, raw=content)
        if not ok:
            failed += 1
        lines.append(text)
        if not out_path or i <= preview:
            print(text)

    summary = f"# done total={len(jobs)} ok={len(jobs) - failed} fail={failed}"
    if out_path:
        Path(out_path).write_text("\n".join(lines), encoding="utf-8", newline="\n")
        print(f"\n# written: {out_path}")
        if len(jobs) > preview:
            print(f"# console preview first {preview} only; full result in --out")
    print(summary, flush=True)
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="德云晟 AES 请求体解密（默认正式环境密钥）")
    parser.add_argument("pairs", nargs="*", help="CIPHER IV 成对传入，可多组")
    parser.add_argument("--log", nargs="?", const="-", help="解析日志文件；省略路径则读 stdin")
    parser.add_argument("--xlsx", help="ES 导出 xlsx（含 @timestamp + content）")
    parser.add_argument("--out", help="解密结果输出文件（建议配合 --xlsx）")
    parser.add_argument("--test", action="store_true", help="使用测试环境 AES 密钥")
    args = parser.parse_args()

    key = AES_KEY_TEST if args.test else AES_KEY_PRO

    if args.xlsx:
        return run_xlsx(args.xlsx, key, args.out)

    if not args.pairs and args.log is None:
        parser.print_help()
        return 2

    jobs = load_jobs(args)
    if not jobs:
        print("未解析到任何 CIPHER/IV", file=sys.stderr)
        return 1

    failed = 0
    for i, (cipher, iv) in enumerate(jobs, 1):
        text, ok = format_item(i, len(jobs), cipher, iv, key)
        if not ok:
            failed += 1
        print(text)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
