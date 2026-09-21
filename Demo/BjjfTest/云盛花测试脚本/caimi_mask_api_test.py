# -*- coding: utf-8 -*-
"""
财米(CAIMI) 掩码全流程：撞库 + 进件
支持单发 / 并发。加密：AES/ECB/PKCS7 + Base64（key=iCtJKfUdx5iUr2v1）。

外层请求体: { "channel": "<渠道码>", "content": "<密文>" }
路径: /app/openapi/mask/check|push/CAIMI

用法:
  python caimi_mask_api_test.py              # 单发撞库+进件
  python caimi_mask_api_test.py -e 1 --no-push
  python caimi_mask_api_test.py -n 10 -w 5
"""

from __future__ import annotations

import argparse
import base64
import json
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import requests

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad
except ImportError:
    print("缺少依赖: pip install pycryptodome", file=sys.stderr)
    raise SystemExit(1)

AES_KEY = "iCtJKfUdx5iUr2v1"
TYPE = "CAIMI"
CHECK_PATH = f"/app/openapi/mask/check/{TYPE}"
PUSH_PATH = f"/app/openapi/mask/push/{TYPE}"

# env -> (base_url, channel)
ENV = {
    1: ("https://yshds.hzbxhd.com/prod-api", "aGL1X0QVfhxJ7peUPktUuhyMGhad4Yv1LRBOVZOQUU"),
    2: ("https://yshwcf.hzbxhd.com/prod-api", "BQnoLXEDNVHcXINHqWoYu37aqhMV2mytV33cqoUGmD"),
    3: ("https://yshwcf.hzbxhd.com/prod-api", "GpkRnE0lDXvLsfD9x7gDt8YORqALdAOuikcyDm45qU"),
    4: ("https://yshwcf.hzbxhd.com/prod-api", "PAFju5UC1Gw9j5KW2bHwiHlYTcfOiocYL51S3DciJF"),
}

_print_lock = threading.Lock()
_thread_local = threading.local()


def log(msg: str) -> None:
    with _print_lock:
        print(msg, flush=True)


def http() -> requests.Session:
    sess = getattr(_thread_local, "session", None)
    if sess is None:
        sess = requests.Session()
        sess.headers.update({
            "Content-Type": "application/json;charset=UTF-8",
            "Accept": "application/json",
        })
        _thread_local.session = sess
    return sess


def aes_encrypt(plain: str, key: str = AES_KEY) -> str:
    cipher = AES.new(key.encode("utf-8"), AES.MODE_ECB)
    raw = cipher.encrypt(pad(plain.encode("utf-8"), AES.block_size))
    return base64.b64encode(raw).decode("utf-8")


def aes_decrypt(cipher_b64: str, key: str = AES_KEY) -> str:
    cipher = AES.new(key.encode("utf-8"), AES.MODE_ECB)
    raw = cipher.decrypt(base64.b64decode(cipher_b64))
    return unpad(raw, AES.block_size).decode("utf-8")


def random_phone() -> str:
    return "138" + f"{random.randint(10000000, 99999999)}"


def build_check_plain(mobile8: str, city: str = "杭州", city_id: int = 330100) -> dict[str, Any]:
    return {
        "mobile": mobile8,
        "age": 30,
        "city_id": city_id,
        "city": city.replace("市", ""),
        "gender": 1,
        "quota": 2,
        "occupation": 1,
        "house": 1,
        "car": 1,
        "social_security": 2,
        "reserved_funds": 2,
        "life_insurance": 1,
        "zm_score": 4,
        "overdue": 1,
        "ip": "127.0.0.1",
        "device_type": 1,
    }


def build_push_plain(
    mobile11: str,
    name: str,
    order_num: str,
    city: str = "杭州",
    city_id: int = 330100,
) -> dict[str, Any]:
    body = build_check_plain(mobile11[:8], city=city, city_id=city_id)
    body["mobile"] = mobile11
    body["name"] = name
    body["order_num"] = order_num
    return body


def encrypt_body(channel: str, plain: dict[str, Any], key: str = AES_KEY) -> dict[str, str]:
    plain_json = json.dumps(plain, ensure_ascii=False, separators=(",", ":"))
    return {"channel": channel, "content": aes_encrypt(plain_json, key)}


def extract_order_num(check_resp: dict) -> str | None:
    """从撞库响应取出 order_num。"""
    data = check_resp.get("data")
    if isinstance(data, list) and data:
        return data[0].get("order_num")
    if isinstance(data, dict):
        return data.get("order_num")
    return None


class CaiMiMask:
    def __init__(
        self,
        phone: str,
        city: str = "杭州",
        city_id: int = 330100,
        env: int = 1,
        name: str = "张三",
        key: str = AES_KEY,
        base_url: str | None = None,
        channel: str | None = None,
    ):
        self.phone = phone
        self.city = city
        self.city_id = city_id
        self.name = name
        self.key = key
        domain, ch = ENV[env]
        self.domain = (base_url or domain).rstrip("/")
        self.channel = channel or ch

    def check(self) -> dict:
        plain = build_check_plain(self.phone[:8], city=self.city, city_id=self.city_id)
        body = encrypt_body(self.channel, plain, self.key)
        log(f"[撞库请求] url={self.domain + CHECK_PATH} channel={self.channel} 明文={json.dumps(plain, ensure_ascii=False)}")
        resp = http().post(self.domain + CHECK_PATH, json=body, timeout=30)
        return resp.json()

    def push(self, order_num: str) -> dict:
        # 进件明文 order_num = 撞库返回值
        plain = build_push_plain(self.phone, self.name, order_num, city=self.city, city_id=self.city_id)
        assert plain["order_num"] == order_num
        body = encrypt_body(self.channel, plain, self.key)
        log(f"[进件请求] url={self.domain + PUSH_PATH} channel={self.channel} order_num={order_num} 明文={json.dumps(plain, ensure_ascii=False)}")
        resp = http().post(self.domain + PUSH_PATH, json=body, timeout=30)
        return resp.json()

    def run(self, do_push: bool = True) -> dict:
        result = {"phone": self.phone, "ok": False}
        try:
            check_resp = self.check()
            result["check"] = check_resp
            log(f"[撞库] 手机明文={self.phone} 响应={json.dumps(check_resp, ensure_ascii=False)}")
            if check_resp.get("code") != 200:
                result["msg"] = check_resp.get("msg")
                return result

            if not do_push:
                result["ok"] = True
                result["msg"] = check_resp.get("msg")
                return result

            order_num = extract_order_num(check_resp)
            if not order_num:
                result["msg"] = "撞库响应缺少 order_num"
                log(f"[异常] phone={self.phone} err={result['msg']}")
                return result

            log(f"[填充] 撞库 order_num={order_num} -> 进件 order_num")
            result["order_num"] = order_num
            push_resp = self.push(order_num)
            result["push"] = push_resp
            result["ok"] = push_resp.get("code") == 200
            result["msg"] = push_resp.get("msg")
            log(f"[进件] 手机明文={self.phone} order_num={order_num} 响应={json.dumps(push_resp, ensure_ascii=False)}")
        except Exception as e:
            result["msg"] = str(e)
            log(f"[异常] phone={self.phone} err={e}")
        return result


def run_one(
    task_id: int,
    env: int,
    city: str,
    city_id: int,
    do_push: bool,
    phone: str | None = None,
    name: str = "张三",
) -> dict:
    client = CaiMiMask(
        phone or random_phone(),
        city=city,
        city_id=city_id,
        env=env,
        name=name,
    )
    result = client.run(do_push=do_push)
    result["task_id"] = task_id
    return result


def run_concurrent(
    total: int = 1,
    workers: int = 1,
    env: int = 1,
    city: str = "杭州",
    city_id: int = 330100,
    do_push: bool = True,
    phone: str | None = None,
    name: str = "张三",
) -> list[dict]:
    workers = max(1, min(workers, total))
    mode = "并发" if total > 1 else "单发"
    domain, channel = ENV[env]
    log(f"{mode}启动: total={total} workers={workers} env={env} url={domain} channel={channel} push={do_push}")
    t0 = time.perf_counter()
    results = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(
                run_one,
                i,
                env,
                city,
                city_id,
                do_push,
                phone if total == 1 else None,
                name,
            )
            for i in range(total)
        ]
        for fut in as_completed(futures):
            results.append(fut.result())
    ok = sum(1 for r in results if r.get("ok"))
    log(f"完成: ok={ok}/{total} 耗时={time.perf_counter() - t0:.2f}s")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="财米 CAIMI 掩码撞库+进件（单发/并发）")
    parser.add_argument("-n", "--total", type=int, default=1, help="总请求条数，默认单发")
    parser.add_argument("-w", "--workers", type=int, default=1, help="并发线程数")
    parser.add_argument("-e", "--env", type=int, default=1, choices=list(ENV.keys()), help="1=test 2=uat 3=dev 4=prod")
    parser.add_argument("--city", default="杭州")
    parser.add_argument("--city-id", type=int, default=330100)
    parser.add_argument("--phone", default="", help="指定手机号；空则随机；并发时每条随机")
    parser.add_argument("--name", default="张三", help="进件姓名")
    parser.add_argument("--no-push", action="store_true", help="仅撞库，不进件")
    args = parser.parse_args()
    run_concurrent(
        total=args.total,
        workers=args.workers,
        env=args.env,
        city=args.city,
        city_id=args.city_id,
        do_push=not args.no_push,
        phone=args.phone or None,
        name=args.name,
    )
