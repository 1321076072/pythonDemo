"""
SecureUtils Python 实现
加解密工具类
@author: LiYu (ported to Python)
@createTime: 2024年05月20日 11:04:00
"""

import base64
import hashlib
import json
import random
import re
import string
from urllib.parse import quote, unquote

from Crypto.Cipher import DES3, AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes


class Md5Util:
    """MD5 加密工具类"""

    @staticmethod
    def is_md5(s: str) -> bool:
        """判断是否为md5加密"""
        return bool(re.match(r'^[a-f0-9]{32}$', s))

    @staticmethod
    def md5_to_upper_case(s: str) -> str:
        """MD5加密并转大写"""
        if not s:
            return None
        if Md5Util.is_md5(s):
            return s
        return hashlib.md5(s.encode('utf-8')).hexdigest().upper()

    @staticmethod
    def md5_to_lower_case(s: str) -> str:
        """MD5加密并转小写"""
        if not s:
            return None
        if Md5Util.is_md5(s):
            return s
        return hashlib.md5(s.encode('utf-8')).hexdigest().lower()

    @staticmethod
    def md5(s: str) -> str:
        """MD5加密"""
        if not s:
            return None
        if Md5Util.is_md5(s):
            return s
        return hashlib.md5(s.encode('utf-8')).hexdigest()


class DesUtil:
    """DES 加密工具类 (实际使用DESede/Triple DES)"""

    # 加密key
    KEY = "_@Ks`Y*9jLb.hvho}C;GwDpw"
    # 偏移量
    IV = "2%8iTpSi"

    @staticmethod
    def _create_cipher(iv: str, mode: int):
        """创建加密对象"""
        key_bytes = DesUtil.KEY.encode('utf-8')
        iv_bytes = iv.encode('utf-8')

        if mode == 1:  # ENCRYPT_MODE
            cipher = DES3.new(key_bytes, DES3.MODE_CBC, iv_bytes)
        else:  # DECRYPT_MODE
            cipher = DES3.new(key_bytes, DES3.MODE_CBC, iv_bytes)
        return cipher

    @staticmethod
    def encrypt(data: str, iv: str = None) -> str:
        """加密"""
        if iv is None:
            iv = DesUtil.IV

        try:
            cipher = DesUtil._create_cipher(iv, 1)  # ENCRYPT_MODE
            data_bytes = data.encode('utf-8')
            padded_data = pad(data_bytes, DES3.block_size)
            encrypted_bytes = cipher.encrypt(padded_data)
            encoded = base64.b64encode(encrypted_bytes).decode('utf-8')
            return quote(encoded, safe='')
        except Exception as e:
            print(f"加密失败: {e}")
            return None

    @staticmethod
    def decrypt(data: str, iv: str = None) -> str:
        """解密"""
        if iv is None:
            iv = DesUtil.IV

        try:
            cipher = DesUtil._create_cipher(iv, 0)  # DECRYPT_MODE
            decoded_data = unquote(data)
            encrypted_bytes = base64.b64decode(decoded_data)
            decrypted_bytes = cipher.decrypt(encrypted_bytes)
            unpadded_bytes = unpad(decrypted_bytes, DES3.block_size)
            return unpadded_bytes.decode('utf-8')
        except Exception as e:
            print(f"解密失败: {e}")
            return None


class AesUtil:
    """AES 加解密工具类"""

    # 加密模式
    AES_ECB = "AES/ECB/PKCS5Padding"
    AES_CBC = "AES/CBC/PKCS5Padding"
    AES_CFB = "AES/CFB/PKCS5Padding"

    # AES 中的 IV 必须是 16 字节（128位）长
    IV_LENGTH = 16

    @staticmethod
    def is_empty(obj) -> bool:
        """空校验"""
        return obj is None or obj == ""

    @staticmethod
    def get_bytes(s: str) -> bytes:
        """String 转 byte"""
        if AesUtil.is_empty(s):
            return None
        try:
            return s.encode('utf-8')
        except Exception as e:
            raise RuntimeError(e)

    @staticmethod
    def get_iv() -> str:
        """初始化向量（IV），它是一个随机生成的字节数组，用于增加加密和解密的安全性"""
        chars = string.ascii_letters + string.digits
        return ''.join(random.choice(chars) for _ in range(AesUtil.IV_LENGTH))

    @staticmethod
    def _get_secret_key_spec(key: str) -> bytes:
        """获取 AES 密钥"""
        key_bytes = AesUtil.get_bytes(key)
        if key_bytes is None:
            raise ValueError("Key cannot be None")
        return key_bytes

    @staticmethod
    def encrypt(text: str, key: str, mode: str = None, iv: str = None) -> str:
        """
        加密
        :param text: 需要加密的文本内容
        :param key: 加密的密钥 key
        :param mode: 加密模式 (ECB/CBC/CFB)
        :param iv: 初始化向量 (CBC/CFB模式需要)
        """
        if AesUtil.is_empty(text) or AesUtil.is_empty(key):
            return None

        try:
            key_bytes = AesUtil._get_secret_key_spec(key)

            if mode is None or mode == AesUtil.AES_ECB:
                cipher = AES.new(key_bytes, AES.MODE_ECB)
            elif mode == AesUtil.AES_CBC:
                if iv is None:
                    iv = AesUtil.get_iv()
                cipher = AES.new(key_bytes, AES.MODE_CBC, iv.encode('utf-8'))
            elif mode == AesUtil.AES_CFB:
                if iv is None:
                    iv = AesUtil.get_iv()
                cipher = AES.new(key_bytes, AES.MODE_CFB, iv.encode('utf-8'))
            else:
                raise ValueError(f"Unsupported mode: {mode}")

            text_bytes = AesUtil.get_bytes(text)
            encrypted_bytes = cipher.encrypt(pad(text_bytes, AES.block_size))
            return base64.b64encode(encrypted_bytes).decode('utf-8')
        except Exception as e:
            raise RuntimeError(e)

    @staticmethod
    def decrypt(text: str, key: str, mode: str = None, iv: str = None) -> str:
        """
        解密
        :param text: 需要解密的文本内容
        :param key: 解密的密钥 key
        :param mode: 加密模式 (ECB/CBC/CFB)
        :param iv: 初始化向量 (CBC/CFB模式需要)
        """
        if AesUtil.is_empty(text) or AesUtil.is_empty(key):
            return None

        try:
            key_bytes = AesUtil._get_secret_key_spec(key)
            text_bytes = base64.b64decode(text)

            if mode is None or mode == AesUtil.AES_ECB:
                cipher = AES.new(key_bytes, AES.MODE_ECB)
            elif mode == AesUtil.AES_CBC:
                if iv is None:
                    raise ValueError("IV is required for CBC mode")
                cipher = AES.new(key_bytes, AES.MODE_CBC, iv.encode('utf-8'))
            elif mode == AesUtil.AES_CFB:
                if iv is None:
                    raise ValueError("IV is required for CFB mode")
                cipher = AES.new(key_bytes, AES.MODE_CFB, iv.encode('utf-8'))
            else:
                raise ValueError(f"Unsupported mode: {mode}")

            decrypted_bytes = cipher.decrypt(text_bytes)
            return unpad(decrypted_bytes, AES.block_size).decode('utf-8')
        except Exception as e:
            raise RuntimeError(e)

    """
    通用掩码加密
    5aa3130110a308f7   小安明文掩码流程
    b81281e4813a174a   通用掩码流程加密 - COMMON_MASK_ACCREDIT
    66fa4d17fc49e0f2   MD5信贷流程加密 - XIAO_AN_FEN_QI
    0b0d02cc8758a94a   MD5采量转掩码  - BA_JIE_JIN_FU
    """
    @staticmethod
    def encrypt_cbc(text: str, key: str, iv: str) -> str:
        """加密 - 模式 CBC"""
        return AesUtil.encrypt(text, key, AesUtil.AES_CBC, iv)

    @staticmethod
    def decrypt_cbc(text: str, key: str, iv: str) -> str:
        """解密 - 模式 CBC"""
        return AesUtil.decrypt(text, key, AesUtil.AES_CBC, iv)

    @staticmethod
    def _encrypt_byte(content: str, password: str) -> bytes:
        """加密字节数组 (使用SHA1PRNG生成密钥)"""
        # 使用密码生成密钥 (模拟 Java 的 SHA1PRNG)
        key_material = password.encode('utf-8')
        # Java 的 SecureRandom SHA1PRNG 实现
        seed_hash = hashlib.sha1(key_material).digest()
        # 取前16字节作为AES-128密钥
        aes_key = seed_hash[:16]

        cipher = AES.new(aes_key, AES.MODE_ECB)
        content_bytes = content.encode('utf-8')
        return cipher.encrypt(pad(content_bytes, AES.block_size))

    @staticmethod
    def _decrypt_byte(content: bytes, password: str) -> bytes:
        """解密字节数组 (使用SHA1PRNG生成密钥)"""
        # 使用密码生成密钥 (模拟 Java 的 SHA1PRNG)
        key_material = password.encode('utf-8')
        # Java 的 SecureRandom SHA1PRNG 实现
        seed_hash = hashlib.sha1(key_material).digest()
        # 取前16字节作为AES-128密钥
        aes_key = seed_hash[:16]

        cipher = AES.new(aes_key, AES.MODE_ECB)
        decrypted = cipher.decrypt(content)
        return unpad(decrypted, AES.block_size)

    @staticmethod
    def aes_encode(content: str, password: str) -> str:
        """加密 (使用SHA1PRNG生成密钥的方式)"""
        try:
            encrypt_result = AesUtil._encrypt_byte(content, password)
            return base64.b64encode(encrypt_result).decode('utf-8')
        except Exception as e:
            print(f"加密出现问题: {e}")
            raise Exception("加密出现问题")

    @staticmethod
    def aes_decode(content: str, password: str) -> str:
        """解密 (使用SHA1PRNG生成密钥的方式)"""
        try:
            content_bytes = base64.b64decode(content)
            decrypt_result = AesUtil._decrypt_byte(content_bytes, password)
            return decrypt_result.decode('utf-8')
        except Exception as e:
            print(f"解密出现问题: {e}")
            return content

    @staticmethod
    def generate_ddfq_key(keyword: str) -> str:
        """根据产品唯一编号生成16字节的密钥"""
        if not keyword:
            return keyword
        key = hashlib.md5(keyword.encode('utf-8')).hexdigest()
        if key:
            # 截取中间16位
            key = key[8:24]
        return key

    @staticmethod
    def generate_key(credit_api_type_name: str) -> str:
        """根据产品唯一编号生成16字节的密钥"""
        if "V2" in credit_api_type_name:
            credit_api_type_name = credit_api_type_name.replace("_V2", "")

        key = Md5Util.md5(credit_api_type_name)
        if key:
            # 截取中间16位
            key = key[8:24]
        return key


class Base64Util:
    """Base64 加解密工具类"""

    @staticmethod
    def encode(input_str: str) -> str:
        """编码字符串为Base64"""
        return base64.b64encode(input_str.encode('utf-8')).decode('utf-8')

    @staticmethod
    def decode(input_str: str) -> str:
        """从Base64编码解码为字符串"""
        decoded_bytes = base64.b64decode(input_str)
        return decoded_bytes.decode('utf-8')

    @staticmethod
    def encode_bytes(input_bytes: bytes) -> str:
        """编码字节数组为Base64字符串"""
        return base64.b64encode(input_bytes).decode('utf-8')

    @staticmethod
    def decode_to_byte_array(input_str: str) -> bytes:
        """解码Base64字符串为字节数组"""
        return base64.b64decode(input_str)

    @staticmethod
    def is_base64(s: str) -> bool:
        """判断是否为Base64编码"""
        base64_pattern = r'^([A-Za-z0-9+/]{4})*([A-Za-z0-9+/]{4}|[A-Za-z0-9+/]{3}=|[A-Za-z0-9+/]{2}==)$'
        return bool(re.match(base64_pattern, s))


if __name__ == "__main__":
    # 测试代码
    print("Testing Md5Util:")
    print(Md5Util.md5_to_upper_case("test"))
    print(Md5Util.md5_to_lower_case("test"))
    print(Md5Util.is_md5("098f6bcd4621d373cade4e832627b4f6"))

    print("\nTesting DesUtil:")
    test_data = {"url": "https://www.baidu.com", "shortUrlType": 1, "shortUrlName": "测试"}
    encrypted = DesUtil.encrypt(json.dumps(test_data))
    print(f"Encrypted: {encrypted}")
    decrypted = DesUtil.decrypt(encrypted)
    print(f"Decrypted: {decrypted}")
    print(f"Phone encrypted: {DesUtil.encrypt('18973023565')}")

    print("\nTesting AesUtil:")
    data = '{"accumulationFund":3,"age":20,"city":"杭州"}'
    encrypted_cbc = AesUtil.encrypt_cbc(data, "b81281e4813a174a", "feawjofjaofaewoj")
    print(f"CBC Encrypted: {encrypted_cbc}")
    decrypted_cbc = AesUtil.decrypt_cbc(encrypted_cbc, "b81281e4813a174a", "feawjofjaofaewoj")
    print(f"CBC Decrypted: {decrypted_cbc}")

    print("\nTesting Key Generation:")
    print(f"XIAO_AN_FEN_QI key: {AesUtil.generate_ddfq_key('XIAO_AN_FEN_QI')}")
    print(f"BA_JIE_JIN_FU key: {AesUtil.generate_ddfq_key('BA_JIE_JIN_FU')}")

    print("\nTesting Base64Util:")
    encoded = Base64Util.encode("Hello World")
    print(f"Base64 encoded: {encoded}")
    decoded = Base64Util.decode(encoded)
    print(f"Base64 decoded: {decoded}")
    print(f"Is base64: {Base64Util.is_base64(encoded)}")