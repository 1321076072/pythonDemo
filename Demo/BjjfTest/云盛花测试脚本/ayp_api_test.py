#!/usr/bin/env python3
"""AnyiPick 半流程联调脚本。

默认打测试明文接口：POST {base}/ayp/test/req/{route}
进件正式报文：     POST {base}/ayp/req/apply   （AES-CBC + SHA256withRSA）

用法：
  python ayp_api_test.py --all
  python ayp_api_test.py --route checkUser
  python ayp_api_test.py --route apply --secure
  python ayp_api_test.py --base http://127.0.0.1:9308 --route jumpUrl --order-no YOUR_ORDER

环境变量可覆盖脚本内默认密钥（与配置中心 ayp_channel_config 对齐）：
  AYP_AES_KEY        AES Key，Base64
  AYP_AES_IV         AES IV，Base64，解码后 16 字节
  AYP_RSA_PRIVATE    平台 RSA 私钥 PEM 路径，或 PKCS8 Base64
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROUTES = ("checkUser", "apply", "jumpUrl", "queryCredit", "queryOrder", "getContract")

PHONE = "13800138000"
ID_CARD = "110101199001011234"

# 联调密钥（AES-128）；环境变量优先。RSA 私钥不入库，走 env 或同目录 pem。
AES_KEY = "aeT22JTuxIiFD5ajRbGGZg=="
AES_IV = "mjBnCt8tVa/43iuFgfY6cA=="
RSA_PRIVATE = ""
RSA_PEM_FILE = Path(__file__).with_name("ayp_rsa_private.pem")


def md5_hex(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def id_card_md5(id_card: str) -> str:
    # 文档：身份证末位 x 先转大写 X 再 MD5
    if id_card and id_card[-1] in ("x", "X"):
        id_card = id_card[:-1] + "X"
    return md5_hex(id_card)


def sample(route: str, order_no: str) -> dict:
    if route == "checkUser":
        return {"phoneMd5": md5_hex(PHONE), "idCardMd5": id_card_md5(ID_CARD)}
    if route == "apply":
        return {
            "orderNo": order_no,
            "phone": PHONE,
            "name": "张三",
            "idCard": ID_CARD,
            "idCardFrontImgUrl": "https://example.com/id_front.jpg",
            "idCardBackImgUrl": "https://example.com/id_back.jpg",
            "faceImgUrl": "https://example.com/face.jpg",
            "nation": "汉族",
            "idCardAddress": "北京市东城区测试路1号",
            "issuedBy": "北京市公安局东城分局",
            "validPeriod": "2010.01.01-2030.01.01",
            "gender": 1,
            "education": 4,
            "marriage": 2,
            "city": "成都市",
            "liveAddress": "四川省成都市高新区测试小区1栋101室",
            "liveSituationType": 3,
            "occupation": "1",
            "companyName": "测试科技有限公司",
            "companyAddress": "四川省成都市高新区天府大道1号",
            "monthlyIncome": 12000,
            "loanPurpose": 1,
            "zhimaScore": 700,
            "housingFund": 1,
            "socialSecurity": 1,
            "carAsset": 3,
            "applyIpAddr": "127.0.0.1",
            "clientType": 1,
            "relations": [
                {"name": "李四", "phone": "13900139000", "relation": 1},
                {"name": "王五", "phone": "13700137000", "relation": 3},
            ],
        }
    if route == "getContract":
        return {"scene": 1, "orderNo": order_no}
    return {"orderNo": order_no}


def load_private_key(raw: str):
    from Crypto.PublicKey import RSA

    text = raw.strip()
    path = Path(text)
    if path.is_file():
        text = path.read_text(encoding="utf-8")
    if "BEGIN" in text:
        return RSA.import_key(text)
    return RSA.import_key(base64.b64decode(text))


def encrypt_apply(plain: dict, aes_key_b64: str, aes_iv_b64: str, rsa_private: str) -> dict:
    from Crypto.Cipher import AES
    from Crypto.Hash import SHA256
    from Crypto.Signature import pkcs1_15
    from Crypto.Util.Padding import pad

    def aes_bytes(v: str) -> bytes:
        try:
            decoded = base64.b64decode(v)
            if len(decoded) in (16, 24, 32):
                return decoded
        except Exception:
            pass
        return v.encode("utf-8")

    raw = json.dumps(plain, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    key = aes_bytes(aes_key_b64)
    iv = aes_bytes(aes_iv_b64)
    if len(iv) != 16:
        raise SystemExit(f"AES IV 解码后必须 16 字节，当前 {len(iv)}")
    cipher = AES.new(key, AES.MODE_CBC, iv)
    data = base64.b64encode(cipher.encrypt(pad(raw, AES.block_size))).decode("ascii")
    ts = str(int(time.time() * 1000))
    digest = SHA256.new((data + ts).encode("utf-8"))
    sign = base64.b64encode(pkcs1_15.new(load_private_key(rsa_private)).sign(digest)).decode("ascii")
    return {"data": data, "timestamp": ts, "sign": sign}


def post(url: str, body: dict) -> tuple[int, str]:
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except Exception as e:
        return 0, str(e)


def pretty(text: str) -> str:
    try:
        return json.dumps(json.loads(text), ensure_ascii=False, indent=2)
    except Exception:
        return text


def resolve_secrets() -> tuple[str, str, str]:
    """env > 脚本常量 > 同目录 ayp_rsa_private.pem"""
    key = os.environ.get("AYP_AES_KEY") or AES_KEY
    iv = os.environ.get("AYP_AES_IV") or AES_IV
    pem = os.environ.get("AYP_RSA_PRIVATE") or RSA_PRIVATE
    if not pem and RSA_PEM_FILE.is_file():
        pem = str(RSA_PEM_FILE)
    return key, iv, pem


def run_one(base: str, route: str, order_no: str, secure: bool) -> None:
    body = sample(route, order_no)
    if secure:
        if route != "apply":
            raise SystemExit("--secure 只用于 apply")
        key, iv, pem = resolve_secrets()
        if not key or not iv or not pem:
            raise SystemExit(
                "缺少 RSA 私钥：设置 AYP_RSA_PRIVATE，或把 PEM 放到脚本同目录 ayp_rsa_private.pem"
            )
        body = encrypt_apply(body, key, iv, pem)
        url = f"{base.rstrip('/')}/ayj/req/apply"
    else:
        url = f"{base.rstrip('/')}/ayj/test/req/{route}"

    print("=" * 72)
    print(f"POST {url}")
    print("request:")
    print(json.dumps(body, ensure_ascii=False, indent=2))
    status, text = post(url, body)
    print(f"http {status}")
    print("response:")
    print(pretty(text))


def main() -> int:
    parser = argparse.ArgumentParser(description="AnyiPick 半流程联调")
    parser.add_argument("--base", default=os.environ.get("AYP_BASE_URL", "https://yshds.hzbxhd.com/prod-api/app"))
    parser.add_argument("--route", choices=ROUTES)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--secure", action="store_true", help="apply 走正式安全报文 /ayp/req/apply")
    parser.add_argument("--order-no", default=f"AYP{int(time.time())}")
    args = parser.parse_args()

    routes = ROUTES if args.all else ((args.route,) if args.route else None)
    if not routes:
        parser.print_help()
        print("\n示例：python ayp_api_test.py --all")
        return 2

    print(f"phoneMd5={md5_hex(PHONE)}")
    print(f"idCardMd5={id_card_md5(ID_CARD)}")
    print(f"orderNo={args.order_no}")
    for route in routes:
        run_one(args.base, route, args.order_no, args.secure and route == "apply")
    return 0


if __name__ == "__main__":
    sys.exit(main())
