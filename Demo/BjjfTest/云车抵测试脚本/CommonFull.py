"""
云车抵撞库 + 进件 — 对齐 YshAesUtil
AES/CBC/PKCS5Padding，密文 Hex，密钥 = MD5(channelSignature[5:15])
支持并发：每条任务独立 session，撞库成功后再进件。
除 city 外，业务字段按采量文档枚举随机，且撞库/进件共用。
"""

import argparse
import hashlib
import json
import random
import string
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

CHANNEL_SIGNATURE = "20260513143429540933"
BASE = "https://yshlyycd.hzbxhd.com/prod-api"
CHECK_URL = f"{BASE}/app/api/channel/check"
PUSH_URL = f"{BASE}/app/api/channel/push"

# 仅城市固定；buyCarType 文档未列枚举，保持 1
FIXED = {
    "city": "杭州市",
    "buyCarType": 1,
}

# 枚举释义，便于结果汇总阅读
ENUM_LABEL = {
    "mortgageStatus": {1: "抵押中", 2: "未抵押"},
    "vehicleAge": {1: "3年内", 2: "3-5年", 3: "6-12年", 4: "12年以上"},
    "vehicleMileage": {1: "2万内", 2: "2~5万", 3: "6-10万", 4: "10万以上"},
    "sex": {0: "女", 1: "男"},
    "buyCarType": {1: "购车类型1"},
}

_SURNAMES = "赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜"
_GIVEN = "一二三四五六七八九十甲乙丙丁戊己庚辛壬癸子丑寅卯辰巳午未申酉戌亥"

_print_lock = threading.Lock()
_thread_local = threading.local()


class YshAesUtil:
    IV_SIZE = 16

    @staticmethod
    def encrypt_text(text: str, aes_key: str, aes_iv: str) -> str:
        cipher = AES.new(aes_key.encode("ascii"), AES.MODE_CBC, aes_iv.encode("ascii"))
        return cipher.encrypt(pad(text.encode("utf-8"), AES.block_size)).hex()

    @staticmethod
    def decrypt_text(encrypted_hex: str, aes_key: str, aes_iv: str) -> str:
        cipher = AES.new(aes_key.encode("ascii"), AES.MODE_CBC, aes_iv.encode("ascii"))
        return unpad(cipher.decrypt(bytes.fromhex(encrypted_hex)), AES.block_size).decode("utf-8")

    @staticmethod
    def get_iv() -> str:
        return "".join(random.choices(string.ascii_letters + string.digits, k=YshAesUtil.IV_SIZE))

    @staticmethod
    def get_aes_key(channel_signature: str) -> str:
        return hashlib.md5(channel_signature[5:15].encode("utf-8")).hexdigest()


def log(msg: str) -> None:
    with _print_lock:
        print(msg, flush=True)


def http() -> requests.Session:
    sess = getattr(_thread_local, "session", None)
    if sess is None:
        sess = requests.Session()
        _thread_local.session = sess
    return sess


def random_phone() -> str:
    prefix = random.choice(
        ("130", "131", "132", "135", "136", "137", "138", "139",
         "150", "151", "152", "158", "159", "186", "188")
    )
    return prefix + f"{random.randint(0, 99999999):08d}"


def random_partner_id() -> str:
    return f"pytest{datetime.now():%Y%m%d}{uuid.uuid4().hex[:6]}"


def random_car_plate() -> str:
    province = random.choice("京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼")
    letter = random.choice(string.ascii_uppercase)
    return f"{province}{letter}{random.randint(0, 99999):05d}"


def random_name() -> str:
    return random.choice(_SURNAMES) + "".join(random.choices(_GIVEN, k=random.choice((1, 2))))


def random_id_card(age: int, sex: int) -> str:
    """按年龄/性别生成合法校验位身份证。"""
    area = random.choice(("110101", "310101", "330102", "440103", "510104"))
    birth = datetime.now() - timedelta(days=age * 365 + random.randint(0, 364))
    birth_s = birth.strftime("%Y%m%d")
    seq = random.randint(0, 499) * 2 + (sex & 1)  # 奇男偶女
    body = f"{area}{birth_s}{seq:03d}"
    weights = (7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2)
    check_map = "10X98765432"
    total = sum(int(b) * w for b, w in zip(body, weights))
    return body + check_map[total % 11]


def new_session() -> dict:
    """
    一次流程共用字段（撞库/进件一致）。
    枚举对齐采量文档；city 不随机。
    """
    sex = random.choice([0, 1])          # 0女 1男
    age = random.randint(22, 60)
    return {
        "partnerId": random_partner_id(),
        "phone": random_phone(),
        "carPlateNo": random_car_plate(),
        "name": random_name(),
        # 1抵押中 2未抵押
        "mortgageStatus": random.choice([1, 2]),
        # 1:3年内 2:3-5年 3:6-12年 4:12年以上
        "vehicleAge": random.choice([1, 2, 3, 4]),
        # 1:2万内 2:2~5万 3:6-10万 4:10万以上（文档末项缺编号，按序取4）
        "vehicleMileage": random.choice([1, 2, 3, 4]),
        # 单位：万元
        "vehicleValuation": round(random.uniform(3.0, 50.0), 1),
        "idCard": random_id_card(age, sex),
        "sex": sex,
        "age": age,
    }


def annotate_params(session: dict) -> dict:
    """原始值 + 枚举中文释义，便于打印/汇总。"""
    payload = {**FIXED, **session}
    labeled = {}
    for k, v in payload.items():
        if k in ENUM_LABEL:
            labeled[k] = {"value": v, "label": ENUM_LABEL[k].get(v, str(v))}
        else:
            labeled[k] = v
    return labeled


def format_params(session: dict) -> str:
    """单行可读的随机参数摘要。"""
    p = annotate_params(session)
    parts = []
    for k, v in p.items():
        if isinstance(v, dict) and "value" in v:
            parts.append(f"{k}={v['value']}({v['label']})")
        else:
            parts.append(f"{k}={v}")
    return " | ".join(parts)


def print_params_block(task_id: int, session: dict) -> None:
    """每次请求前完整打印参数块。"""
    lines = [f"[#{task_id}] ===== 随机参数 ====="]
    for k, v in annotate_params(session).items():
        if isinstance(v, dict) and "value" in v:
            lines.append(f"  {k}: {v['value']} ({v['label']})")
        else:
            lines.append(f"  {k}: {v}")
    lines.append(f"[#{task_id}] ==================")
    log("\n".join(lines))


def print_results_summary(results: list[dict]) -> None:
    """全部任务结束后汇总随机参数与结果。"""
    lines = ["", "========== 结果汇总 =========="]
    for r in sorted(results, key=lambda x: x.get("task_id", 0)):
        tid = r.get("task_id")
        ok = "成功" if r.get("ok") else "失败"
        push_data = (r.get("push") or {}).get("data")
        lines.append(f"[#{tid}] {ok} | msg={r.get('msg')} | data={push_data}")
        lines.append(f"  参数: {format_params(r.get('session') or {})}")
    lines.append("==============================")
    log("\n".join(lines))


def encrypt_body(payload: dict, channel_signature: str) -> dict:
    key = YshAesUtil.get_aes_key(channel_signature)
    iv = YshAesUtil.get_iv()
    data = YshAesUtil.encrypt_text(json.dumps(payload, ensure_ascii=False), key, iv)
    return {"iv": iv, "data": data, "channelSignature": channel_signature}


def post(url: str, body: dict) -> dict:
    resp = http().post(url, json=body, timeout=30)
    log(f"响应: {resp.text}")
    return resp.json()


def extract_serial_no(resp: dict) -> str | None:
    data = resp.get("data")
    if isinstance(data, list) and data:
        return data[0].get("serialNo")
    if isinstance(data, dict):
        return data.get("serialNo")
    return None


def check(session: dict, channel_signature: str = CHANNEL_SIGNATURE) -> dict:
    body = encrypt_body({**FIXED, **session}, channel_signature)
    log(f"[撞库] phone={session['phone']} partnerId={session['partnerId']}")
    return post(CHECK_URL, body)


def push(session: dict, channel_signature: str = CHANNEL_SIGNATURE, serial_no: str | None = None) -> dict:
    body = encrypt_body({**FIXED, **session}, channel_signature)
    if serial_no:
        body["serialNo"] = serial_no
    log(f"[进件] phone={session['phone']} partnerId={session['partnerId']}")
    return post(PUSH_URL, body)


def run_one(task_id: int = 0) -> dict:
    session = new_session()
    params = annotate_params(session)
    result = {
        "task_id": task_id,
        "session": session,
        "params": params,
        "params_text": format_params(session),
        "ok": False,
    }
    print_params_block(task_id, session)

    try:
        check_resp = check(session)
        result["check"] = check_resp
        if check_resp.get("code") != 200:
            result["msg"] = f"撞库失败: {check_resp.get('msg')}"
            log(f"[#{task_id}] {result['msg']} | {result['params_text']}")
            return result

        push_resp = push(session, serial_no=extract_serial_no(check_resp))
        result["push"] = push_resp
        result["ok"] = push_resp.get("code") == 200
        result["msg"] = push_resp.get("msg")
        result["order_no"] = push_resp.get("data")
        log(
            f"[#{task_id}] 进件 code={push_resp.get('code')} msg={push_resp.get('msg')} "
            f"data={push_resp.get('data')} | {result['params_text']}"
        )
    except Exception as e:
        result["msg"] = str(e)
        log(f"[#{task_id}] 异常: {e} | {result['params_text']}")
    return result


def run_concurrent(total: int = 5, workers: int = 5) -> list[dict]:
    workers = max(1, min(workers, total))
    log(f"并发启动: total={total} workers={workers}")
    t0 = time.perf_counter()
    results = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(run_one, i): i for i in range(total)}
        for fut in as_completed(futures):
            results.append(fut.result())
    ok = sum(1 for r in results if r.get("ok"))
    log(f"完成: ok={ok}/{total} 耗时={time.perf_counter() - t0:.2f}s")
    print_results_summary(results)
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="云车抵撞库+进件（支持并发）")
    parser.add_argument("-n", "--total", type=int, default=1, help="总请求条数")
    parser.add_argument("-w", "--workers", type=int, default=1, help="并发线程数")
    args = parser.parse_args()
    run_concurrent(args.total, args.workers)
