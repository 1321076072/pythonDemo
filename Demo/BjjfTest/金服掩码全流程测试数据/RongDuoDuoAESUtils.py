import base64
import logging
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes


class RongDuoDuoAESUtils:
    # 数据推送URL（保留原Java类的常量）
    URL = "http://120.78.237.96:8081/Admin/UserIncomeApi/addUserAes"

    # 加解密密钥
    KEY = "dxjf18129979469s"

    # 偏移量，AES 128位数据块对应偏移量为16位
    VIPARA = "dxjf18129979469s"

    # 编码方式
    CODE_TYPE = "UTF-8"

    # 块大小
    BLOCK_SIZE = AES.block_size

    @staticmethod
    def encrypt(content: str, key: str = None) -> str:
        """
        AES 加密操作

        Args:
            content: 待加密内容
            key: 加密密钥，默认为类中定义的KEY

        Returns:
            Base64编码的加密数据
        """
        if content is None or content == "":
            return content

        try:
            # 使用默认密钥或传入的密钥
            use_key = key if key is not None else RongDuoDuoAESUtils.KEY
            use_iv = RongDuoDuoAESUtils.VIPARA.encode(RongDuoDuoAESUtils.CODE_TYPE)

            # 将密钥和IV转换为合适的长度
            key_bytes = use_key.encode(RongDuoDuoAESUtils.CODE_TYPE)

            # 确保密钥长度为16、24或32字节
            if len(key_bytes) > 32:
                key_bytes = key_bytes[:32]
            elif len(key_bytes) < 16:
                key_bytes = key_bytes.ljust(16, b'\0')
            elif len(key_bytes) not in [16, 24, 32]:
                # 补齐到最近的16的倍数
                target_len = ((len(key_bytes) + 15) // 16) * 16
                if target_len > 32:
                    target_len = 32
                key_bytes = key_bytes.ljust(target_len, b'\0')

            # 确保IV长度为16字节
            if len(use_iv) > 16:
                iv_bytes = use_iv[:16]
            elif len(use_iv) < 16:
                iv_bytes = use_iv.ljust(16, b'\0')
            else:
                iv_bytes = use_iv

            # 创建Cipher对象
            cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)

            # 加密数据
            content_bytes = content.encode(RongDuoDuoAESUtils.CODE_TYPE)
            padded_content = pad(content_bytes, RongDuoDuoAESUtils.BLOCK_SIZE)
            encrypted_bytes = cipher.encrypt(padded_content)

            # 返回Base64编码结果
            return base64.b64encode(encrypted_bytes).decode(RongDuoDuoAESUtils.CODE_TYPE)

        except Exception as ex:
            logging.getLogger(__name__).error(f"AES加密失败: {ex}")
            return None

    @staticmethod
    def decrypt(content: str, key: str = None) -> str:
        """
        AES 解密操作

        Args:
            content: 待解密内容（Base64编码）
            key: 解密密钥，默认为类中定义的KEY

        Returns:
            解密后的字符串
        """
        if content is None or content == "":
            return content

        try:
            # 使用默认密钥或传入的密钥
            use_key = key if key is not None else RongDuoDuoAESUtils.KEY
            use_iv = RongDuoDuoAESUtils.VIPARA.encode(RongDuoDuoAESUtils.CODE_TYPE)

            # 将密钥和IV转换为合适的长度
            key_bytes = use_key.encode(RongDuoDuoAESUtils.CODE_TYPE)

            # 确保密钥长度为16、24或32字节
            if len(key_bytes) > 32:
                key_bytes = key_bytes[:32]
            elif len(key_bytes) < 16:
                key_bytes = key_bytes.ljust(16, b'\0')
            elif len(key_bytes) not in [16, 24, 32]:
                # 补齐到最近的16的倍数
                target_len = ((len(key_bytes) + 15) // 16) * 16
                if target_len > 32:
                    target_len = 32
                key_bytes = key_bytes.ljust(target_len, b'\0')

            # 确保IV长度为16字节
            if len(use_iv) > 16:
                iv_bytes = use_iv[:16]
            elif len(use_iv) < 16:
                iv_bytes = use_iv.ljust(16, b'\0')
            else:
                iv_bytes = use_iv

            # 解码Base64
            encrypted_bytes = base64.b64decode(content)

            # 创建Cipher对象并解密
            cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
            decrypted_bytes = cipher.decrypt(encrypted_bytes)

            # 去除填充
            unpadded_bytes = unpad(decrypted_bytes, RongDuoDuoAESUtils.BLOCK_SIZE)

            # 返回解码后的字符串
            return unpadded_bytes.decode(RongDuoDuoAESUtils.CODE_TYPE)

        except Exception as ex:
            logging.getLogger(__name__).error(f"AES解密失败: {ex}")
            return None

    @staticmethod
    def encrypt_with_iv(content: str, key: str, iv: str) -> str:
        """
        AES 加密操作（使用指定的IV）

        Args:
            content: 待加密内容
            key: 加密密钥
            iv: 偏移量

        Returns:
            Base64编码的加密数据
        """
        if content is None or content == "":
            return content

        try:
            # 将密钥和IV转换为字节
            key_bytes = key.encode(RongDuoDuoAESUtils.CODE_TYPE)
            iv_bytes = iv.encode(RongDuoDuoAESUtils.CODE_TYPE)

            # 确保密钥长度为16、24或32字节
            if len(key_bytes) > 32:
                key_bytes = key_bytes[:32]
            elif len(key_bytes) < 16:
                key_bytes = key_bytes.ljust(16, b'\0')
            elif len(key_bytes) not in [16, 24, 32]:
                # 补齐到最近的16的倍数
                target_len = ((len(key_bytes) + 15) // 16) * 16
                if target_len > 32:
                    target_len = 32
                key_bytes = key_bytes.ljust(target_len, b'\0')

            # 确保IV长度为16字节
            if len(iv_bytes) > 16:
                iv_bytes = iv_bytes[:16]
            elif len(iv_bytes) < 16:
                iv_bytes = iv_bytes.ljust(16, b'\0')

            # 创建Cipher对象
            cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)

            # 加密数据
            content_bytes = content.encode(RongDuoDuoAESUtils.CODE_TYPE)
            padded_content = pad(content_bytes, RongDuoDuoAESUtils.BLOCK_SIZE)
            encrypted_bytes = cipher.encrypt(padded_content)

            # 返回Base64编码结果
            return base64.b64encode(encrypted_bytes).decode(RongDuoDuoAESUtils.CODE_TYPE)

        except Exception as ex:
            logging.getLogger(__name__).error(f"AES加密失败: {ex}")
            return None

    @staticmethod
    def get_secret_key(key: str):
        """
        生成加密密钥（与原Java方法兼容）

        注意：这个方法是原Java类的遗留方法，在Python版本中实际不使用
        因为Python的Crypto库直接使用原始密钥
        """
        try:
            # 在Python中，我们直接使用原始密钥
            key_bytes = key.encode(RongDuoDuoAESUtils.CODE_TYPE)

            # 确保密钥长度为16、24或32字节
            if len(key_bytes) > 32:
                key_bytes = key_bytes[:32]
            elif len(key_bytes) < 16:
                key_bytes = key_bytes.ljust(16, b'\0')
            elif len(key_bytes) not in [16, 24, 32]:
                # 补齐到最近的16的倍数
                target_len = ((len(key_bytes) + 15) // 16) * 16
                if target_len > 32:
                    target_len = 32
                key_bytes = key_bytes.ljust(target_len, b'\0')

            return key_bytes
        except Exception as ex:
            logging.getLogger(__name__).error(f"生成密钥失败: {ex}")
            return None


# 使用示例
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO)

    # 测试数据
    original_text = "Hello, RongDuoDuo!"

    # 加密
    encrypted = RongDuoDuoAESUtils.encrypt(original_text)
    print(f"加密前: {original_text}")
    print(f"加密后: {encrypted}")

    # 解密
    decrypted = RongDuoDuoAESUtils.decrypt(encrypted)
    print(f"解密后: {decrypted}")

    # 使用自定义密钥和IV
    custom_key = "mycustomkey123456"
    custom_iv = "mycustomiv1234567"
    encrypted_custom = RongDuoDuoAESUtils.encrypt_with_iv(original_text, custom_key, custom_iv)
    print(f"使用自定义密钥加密后: {encrypted_custom}")