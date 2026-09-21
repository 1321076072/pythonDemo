import base64
import hashlib
from urllib.parse import quote


from Crypto.Cipher import DES3, AES, DES
from Crypto.Util.Padding import unpad
from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA
from Crypto import Random
import hashlib


class EncryptUtil:


    @classmethod
    def aes_encrypt(cls, key, content, encrypt_mode, iv='', paddingMode="NoPadding"):
        key, content, iv = cls._change_type(key, content, iv, padding=paddingMode, mode="AES")

        # if mode == "encrypt":
        if encrypt_mode == "ECB":
            aes = AES.new(key, AES.MODE_ECB)
        elif encrypt_mode == "CBC":
            aes = AES.new(key, AES.MODE_CBC, iv=iv)
        else:
            aes = None
            print("不支持的加密模式")

        en_text = aes.encrypt(content)
        ciphertext_base64 = base64.b64encode(en_text)
        return ciphertext_base64.decode("utf-8")

    @classmethod
    def aes_decrypt(cls, key, ciphertext, encrypt_mode, iv='', paddingMode="NoPadding"):
        key, content, iv = cls._change_type(key, ciphertext, iv, padding=paddingMode, mode="AES")

        # if mode == "encrypt":
        if encrypt_mode == "ECB":
            aes = AES.new(key, AES.MODE_ECB)
        elif encrypt_mode == "CBC":
            aes = AES.new(key, AES.MODE_CBC, iv=iv)
        else:
            aes = None
            print("不支持的解密模式")

        # 假设密文经过 Base64 编码
        ciphertext = base64.b64decode(ciphertext)
        # 解密并去除填充
        decrypted_data = unpad(aes.decrypt(ciphertext), AES.block_size)
        
        return decrypted_data.decode('utf-8')
    
    
    @classmethod
    def des_encrypt(cls, key, content, encrypt_mode, iv='', paddingMode="NoPadding"):
        key, content, iv = cls._change_type(key[:8], content, iv, padding=paddingMode, mode="DES")

        if encrypt_mode == "ECB":
            des = DES.new(key, DES.MODE_ECB)
        elif encrypt_mode == "CBC":
            des = DES.new(key, DES.MODE_CBC, iv=iv)
        else:
            print("不支持的加密模式")

        en_text = des.encrypt(content)

        ciphertext_base64 = base64.b64encode(en_text)

        return ciphertext_base64.decode("utf-8")

    @classmethod
    def tripledes_encrypt(cls, key, content, encrypt_mode, iv='', paddingMode="NoPadding"):
        key, content, iv = cls._change_type(key, content, iv, padding=paddingMode, mode="3DES")

        if encrypt_mode == "ECB":
            des3 = DES3.new(key, DES3.MODE_ECB)
        elif encrypt_mode == "CBC":
            des3 = DES3.new(key, DES3.MODE_CBC, iv=iv)
        else:
            print("不支持的加密模式")

        en_text = des3.encrypt(content)

        ciphertext_base64 = base64.b64encode(en_text)

        return ciphertext_base64.decode("utf-8")

    @classmethod
    def md5_encrypt(cls, string):
        md5_util = hashlib.md5()
        md5_util.update(string.encode("utf-8"))
        md5_encrypt_result = md5_util.hexdigest().lower()

        return md5_encrypt_result
    
    @classmethod
    def URL_encoding(cls, string):
        string_URLe = quote(string, encoding='utf-8')

        return string_URLe

    # 填充方式
    @classmethod
    def __PKCS5_7Padding(cls, content, mode):
        if mode == "AES":
            needSize = 16 - len(content) % 16
            if needSize == 0:
                needSize = 16
            return content + needSize.to_bytes(1, 'little') * needSize
        elif mode == "DES" or "3DES":
            needSize = 8 - len(content) % 8
            if needSize == 0:
                needSize = 8
            return content + needSize.to_bytes(1, 'little') * needSize

    # 填充方式
    @classmethod
    def __ZeroPadding(cls, content, mode):
        if mode == "AES":
            content += b'\x00'
            while len(content) % 16 != 0:
                content += b'\x00'
            return content
        elif mode == "DES" or "3DES":
            content += b'\x00'
            while len(content) % 8 != 0:
                content += b'\x00'
            return content

    # 填充方式
    @classmethod
    def __ZeroPadding_key(cls, content, mode):
        if mode == "AES":
            content += b'\x00'
            while len(content) % 16 != 0:
                content += b'\x00'
            return content
        elif mode == "DES":
            content += b'\x00'
            while len(content) % 8 != 0:
                content += b'\x00'
            return content
        elif mode == "3DES":
            content += b'\x00'
            while len(content) % 24 != 0:
                content += b'\x00'
            return content

    # 传参预处理
    @classmethod
    def _change_type(cls, key, content, iv, padding, mode):

        # 将字符类型密钥、明文、偏移量转化为字节类型
        key_byte = key.encode('utf-8')
        content_byte = content.encode('utf-8')
        iv_byte = iv.encode("utf-8")

        # 校验密钥是否符合加密协议长度

        if mode == "AES":
            if len(key_byte) % 16 != 0:
                key_byte = cls.__ZeroPadding_key(key_byte, mode=mode)
        elif mode == "DES":
            if len(key_byte) % 8 != 0:
                print(key_byte)
                key_byte = cls.__ZeroPadding_key(key_byte, mode=mode)
        elif mode == "3DES":
            if len(key_byte) % 24 != 0:
                if len(key_byte) < 8:
                    raise TypeError("3DES的密钥长度要为24位！！！")
                else:
                    key_byte = cls.__ZeroPadding_key(key_byte, mode=mode)

        # 根据加密协议对明文进行填充
        if padding == "NoPadding":
            if len(content_byte) % 16 == 0:
                return content_byte
            else:
                content_byte = cls.__ZeroPadding(content_byte, mode=mode)
        elif padding == "ZeroPadding":
            content_byte = cls.__ZeroPadding(content_byte, mode=mode)
        elif padding == "PKCS5Padding" or padding == "PKCS7Padding":
            content_byte = cls.__PKCS5_7Padding(content_byte, mode=mode)
        else:
            print("不支持Padding")

        return key_byte[:24], content_byte, iv_byte
    
    
    @classmethod
    def rsaEncrypt(cls, content, public_key):
        rsa_key = RSA.importKey(public_key)
        cipher = PKCS1_v1_5.new(rsa_key)
        encrypted_message = base64.b64encode(cipher.encrypt(content.encode('utf-8')))
        return encrypted_message.decode('utf-8')
    
    @classmethod
    def rsaDecrypt(cls, content, private_key):
        rsa_key = RSA.importKey(private_key)
        cipher = PKCS1_v1_5.new(rsa_key)
        decrypted_message = cipher.decrypt(base64.b64decode(content), Random.new().read)
        return decrypted_message.decode('utf-8')
    
    @classmethod
    def _SHA256(cls,content):

        # 使用SHA-256算法创建哈希对象，并进行加密
        data_sha = hashlib.sha256(content.encode('utf-8')).hexdigest()

        
        return data_sha
    
    @classmethod
    def _Sign(cls,signDict:dict):
        # 按 key 升序排序并拼接
        sorted_items = sorted(signDict.items())  # 按 key 排序
        result = '&'.join([f"{key}={value}" for key, value in sorted_items])

        return result
    @classmethod
    def SignAndSHA256(cls,signDict:dict):
        return cls._SHA256(cls._Sign(signDict))
        


if __name__ == "__main__":
    #key = "gsdfeygasfw"
    #iv = "2%8iTpSi"
    
    key = "p4aw3lWlI6nXRDD0"
    iv = "2%8iTpSi"
    
    text = {
        "businessLicense": 1,
        "insurance": 1,
        "profession": 10,
        "loanUse": 5,
        "education": 2,
        "salaryType": 1,
        "city": 640500,
        "social": 0,
        "sex": "男",
        "zhima": 5,
        "loanAmt": 10,
        "userName": "测试",
        "house": 2,
        "incomeMonth": 3,
        "loanTerm": 5,
        "maskPhone": "18211199",
        "overdue": 0,
        "province": "宁夏回族自治区",
        "car": 1,
        "fund": 0,
        "requestId": "maskcode445049983853376",
        "cityAllName": "中卫市",
        "age": 29
    }
    text = str(text)
    
    detext = "/ZwykSq7qlHJK3GFUODjp22lrz6M/lTocWJ8EC9k+MwWoTc9RFoDy66HVhR0pFDGjHxT6y8jAaeXmkYkfwQ2CA=="
    dekey = "wVNuDLPfBVXMxuKx"
    
    
    
    #print("aes_ECB_pkcs5:",EncryptUtil.aes_decrypt(dekey, detext, "ECB", "", "PKCS5Padding"))
    
    # collisionlibrary = {"sex": 1,"age": 33,"phone": "83925d97b2e4a09c5e5d26ff35a9c3b0", "actualName": "撞库优化","city": "深圳","cityCode": 4403,"socialSecurity": 1,"providentFund": 1,
    # "carProduction": 2,"estate": 2,"personalInsurance": 1,"sesame": 5,"professionalIdentity": 1,"overdued": False,"creditCard": True,"microLoan": False,"education": 1,"monthlyIncome": 1,"monthlyIncomeType": 1,"formOfPayroll": 1,"currentWorkingAge": 1,"creditInformation": 1}
    #
    #
    # print(EncryptUtil.md5_encrypt("123456"))
    # print("aes_sha1prng:",EncryptUtil.AES_sha1prng(json.dumps(collisionlibrary),key))
    #
    #
    #
    #print("aes_ECB_pkcs5:",EncryptUtil.aes_encrypt(key, text, "ECB", "", "PKCS5Padding"))
    # print("aes_ECB_zero:",EncryptUtil.aes_encrypt("123", "123", "ECB", "", "ZeroPadding"))
    #print("aes_CBC_pkcs5:",EncryptUtil.aes_encrypt(key, text, "CBC", iv, "PKCS5Padding"))
    # # print("aes_CBC_zero:",EncryptUtil.aes_encrypt("123", "123", "CBC", "", "ZeroPadding"))
    # print("aes_CBC_pkcs5_iv:",EncryptUtil.aes_encrypt("123", "123", "CBC", "1234567812345678", "PKCS5Padding"))
    # print("aes_CBC_zero_iv:",EncryptUtil.aes_encrypt("123", "123", "CBC", "1234567812345678", "ZeroPadding"))
    #
    #
    #print("des_ECB_pkcs5:",EncryptUtil.des_encrypt("3OJ19716zuw8U99XI6349HNw", text, "ECB", "", "PKCS5Padding"))
    # print("des_ECB_zero:",EncryptUtil.des_encrypt("123", "123", "ECB", "", "ZeroPadding"))
    # print("des_CBC_pkcs5_iv:",EncryptUtil.des_encrypt(key, text, "CBC", iv, "PKCS5Padding"))
    # print("des_CBC_zero_iv:",EncryptUtil.des_encrypt("123", "123", "CBC", "12345678", "ZeroPadding"))
    #

    # print("3des_ECB_pkcs5:", EncryptUtil.tripledes_encrypt("OOO12345678901234567890", "123", "ECB", "", "PKCS5Padding"))
    # print("3des_ECB_zero:", EncryptUtil.tripledes_encrypt("OOO12345678901234567890", "123", "ECB", "", "ZeroPadding"))
    # print("3des_CBC_pkcs5_iv:", EncryptUtil.tripledes_encrypt(key, text, "CBC", iv, "PKCS5Padding"))
    # print("3des_CBC_zero_iv:", EncryptUtil.tripledes_encrypt("32e326b5053bc97b895f2c14c228af82", "123", "CBC", "01234567", "PKCS5Padding"))
    
    
    thirdPublicKey = "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC4En0Zh+17Kb02YI06wZvadlulp+llGQCZUDmlzAfC++0/ZAwmhtVbjxeMTs3v+FE7DSTlAV+QANBl2bJwbvpBH9sjIl17f7Hu8vseWhIeUzTRzv2gv4R52aSM4Lmb6WpxEFgeApVkVRzun0sYalIwjC2QVIn8pksr7vq4RgomZwIDAQAB"
    
    privatekey = "MIICdQIBADANBgkqhkiG9w0BAQEFAASCAl8wggJbAgEAAoGBAL7v24XGW9gPuJj8mKPHkDdJSNMKIChB0yM2Rs8BDTGYwoeIAvD9wTN2sCIB0xOM6qhlJz4jYe1tmZi8Eb6TSygLKLUmfxrV7NVeoj/VT/Vnm+9fpEpD/RQ8hCDKEN7vX18Q56mf7iWNFjGk0k6BK65VFwutiyW6hY4f+89NLxX9AgMBAAECgYArAmeeFiT5Ie1wlLGjbuAW/AyJ8UV2HAG99Et19KQusFzdX69d7qMW/xzExElyJXN0VDjHP/wemeoX5AFRPueWLMYPaLvGoHTki6E0Mov3EgX87gb9RkVap5jp7zRRY/v7xlYrs+lSv/xuFFlIfO6OTz5NCyofbmR1ANjmlu+78QJBAPiyXeRHBEaK2nKpijVHmC7NE6NyzMTmElyQaQ6ZzmzvROgLu3Jo5M9i4QRddC/enGEiLIVCbBWS6e91cBZ5fxkCQQDEi0TAHzbsaNI9JDr1IcjMaC6DZLysutKWCuBaIg5c1eqw610Hvf/RmK17+Q557kmUFWYduqNaFm97+DfeiD6FAkAZadiwYBVuw/eoqeyGn0dM2QX9uNh18nDD5rnllRAED7tB3xkLiu5+xsLpuEcMMTpXrq9P+saiub2QC7clhMrZAkBTxHe82pDyGYrhfDuUlp2aYRzR63FuvQFb6a7NO46biqDIXsf7sMMDdesa13+QADtj3erz6MQOdVl2oMhPFApxAkAs6/ioqQOC7KE4FBluWbjV1qZhammZmPtNFX8dJq9P0seD0AbEBG3rbnNwYgt0kmFiMhuQCoHNhI7hfs3LYfTY"
    publickey = "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC+79uFxlvYD7iY/Jijx5A3SUjTCiAoQdMjNkbPAQ0xmMKHiALw/cEzdrAiAdMTjOqoZSc+I2HtbZmYvBG+k0soCyi1Jn8a1ezVXqI/1U/1Z5vvX6RKQ/0UPIQgyhDe719fEOepn+4ljRYxpNJOgSuuVRcLrYsluoWOH/vPTS8V/QIDAQAB"
    
    pubilckeytemp = """-----BEGIN PUBLIC KEY-----
                        {Key}
                        -----END PUBLIC KEY-----"""
    privatekeytemp = """-----BEGIN RSA PRIVATE KEY-----
                        {Key}
                        -----END RSA PRIVATE KEY-----
                """
    
    content = "b81281e4813a174a"
    
    #print("rsaEncrypt:", EncryptUtil.rsaEncrypt(content,pubilckeytemp.format(Key=thirdPublicKey)))
    
    testdict = {
        "channelCode": "yunshenghua",
        "key": "dVXLIYeGhmJcUA4gBy0rWxyX0dVznU9jdmOjOt3/HflOLymHqu+nNtjCGNB1GjrJK9a+7BbFhEMy2A+qsBmhQk4U6NtyAZ/zUmV+xH/4U4LrQeAyGdPiUqvt0VwVvnKWxVtDiC4I7OxiiddQ6yjBk963aOrnsvChux4UFcFlq5M=",
        "payload": "Wa7GN94Fl2LPDi6zrMmsHVcLn/uM2q5giseMN3JNYzcBkFIDlbBrD9o/jajRnxymTeLSq1GZA7BN28NFS1vI0ti98OvOUjO6d8Sd2/Lh6ubPtlTcfw6FS24pEpkv/anp",
        }
    
    encryptcontent = EncryptUtil.rsaEncrypt(EncryptUtil.SignAndSHA256(testdict),pubilckeytemp.format(Key=publickey))
    #print(encryptcontent)
    
    #print(EncryptUtil.rsaDecrypt(encryptcontent,privatekeytemp.format(Key=privatekey)))
    
    print(EncryptUtil.rsaDecrypt("HgFYijbMvxQ5oH59W1Wg2G/tY/MbIWTDmBLJipKLPpJUnYg3hY32U1r8sRINTCwHoTgNjZ146PEhDwOYlMZYq9L1F/LHM7GdLtQkQIvsvY27+R4x92BdIu8tyABddw2I5ae0+2eJ7Q0lGnrVxvYA1dAHfoj1h3Z2fOeR5BAx4cU=",privatekeytemp.format(Key=privatekey)))
    