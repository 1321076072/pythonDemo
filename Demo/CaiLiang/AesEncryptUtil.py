import jnius_config
jnius_config.set_classpath('./',r"E:\javaSite\hutool-core-5.8.16.jar",r"E:\javaSite\commons-codec-1.9.jar",r"E:\javaSite\hutool-crypto-5.8.16.jar",r'E:\OLD2\TestJar\AesSha1prng.jar',r'E:\OLD2\TestJar\SecureUtils.jar',r'E:\OLD2\TestJar\fastjson-1.2.83.jar',
                           r'E:\OLD2\TestJar\YocOpenLoanEncryptUtils.jar',r'E:\OLD2\TestJar\RSATestDemo.jar',r"E:\OLD2\TestJar\YshAesUtil.jar")
import jnius
import random
import json

from encryptutil import EncryptUtil
md5 = EncryptUtil.md5_encrypt


def aessha1():
    java = jnius.autoclass("AesSha1prng").encrypt
    return java

def aescbc():
    java = jnius.autoclass("SecureUtils$AesUtil").encryptCbc
    return java

def aesDecodecbc():
    java = jnius.autoclass("SecureUtils$AesUtil").decrypt
    return java

def aesebc():
    java = jnius.autoclass("SecureUtils$AesUtil").encrypt
    return java

def rasAesEbc():
    java = jnius.autoclass("YocOpenLoanEncryptUtils").channelEncryptedData
    return java

def QDRas():
    java = jnius.autoclass("RSATestDemo").dataEncrypt
    return java

def YshAesUtil():
    java = jnius.autoclass("YshAesUtil")
    return java

if __name__ == "__main__":
    # String text, String key
    #print(aessha1()("382a739acc6d7b0b9cde57e223d9fb0f","gsdfeygasfw"))

    # String text, String key, String iv
    #print(aescbc()(str({"a":"b"}),"66fa4d17fc49e0f2","66fa4d17fc49e0f2"))
    text = "Y3JnpwU13iJNBBX5BS6jPnUyc4+uTp/NXiDkEtWNbVEzwG6rIxJfORwmp8KfGqlTvd/Q0lkYS/7YhKSoWa2Pvr5q8fubEc8i1H/mJ016ZLASLbcRe3wdRreGd4qxuGJrfe0HjMhgZMB+8WYfsuWMu03z1MKyrM4kOCQxaqzjev4Q4glnEBwO7SGosBr414XPxBSJ7GK8wxOzFtL58CeMdnxRbJ6Ya+yol+Bc+go6l8KTAQr5R7GFdX99LXz/PCAxIQ7QS57qVQU72k+0xSeCLB6/lXaRRzT0hMDtFsl/couUWwkPJ7kEtIeKduoaGpgcVlEsNXdp36uZMmiHLhKE5rHNiccHdr3cpnv1XXYv7K4k9TDGImNRf20tBN7jjlSRD65QKMn4KJBneAjtXyXWri8Nvu06pS2oOspX0+wFWAcqxbrnxCumWN2Pm4Ce+TVxn3BAeKdOBuM2AYttez1NJLnjPZkQPKVa3YNBovL7Fy+O2gnvQza8Falwtq0EfOH6+33RH/ZkAYeGa/ghC2D3BIWiwhFh/44Lw+2lMVcHGONIaVtaEzuJCig0iryHEYBylwr4OsPNF+5tL/wHtD/Fr3Ragg2FWkAnOKDgF7yv+VuewHMlwM8eKh8I+rNNBhrUe6vxAZXIN3FwEaoRJRy0wNVsXWB8ccd17GXYuxZyHT8S7iyVhUyhAqANFNn9zBkt2imAtXwDapGzkpXc1+Jvfk4Rs+bG0e/Iw2WkTd60ZNGy2c9octWnxXNSOIa4plEqkibuadsK1qID27crWmIz8lEwgWQxY2QNIpGC7mIPqniMNvht+xLx1l7JVj5Mg4Cq"
    print(aesDecodecbc()(text,"dxjf18129979469s","dxjf18129979469s"))
    
    
    # String text, String key, String iv
    #print(aesebc()(str({"a":"b"}),"]+atg}`Ff*bcH[99M#-G%rI,s-n;nMR="))
    """
    key = "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA74GY9YeVmIGdatiOA8zjLyX8JHPizuBiEXenGWhWn9FHJdrE/f5sNOALOslPLud/6Zc6ryd0UvThp3PMm5Pit7YAAcOBHCp61LtFGAlvz+RGurrbQoEzO8MfaujEyr93jtM8yBVS6VevrSTnP0zA1EUpVcFjNCzZnzQQa4LlApqV0mV8N/bUDYBaF3wUL7tYTAAXG+P2XIhaXASkIErRviVaLNZV3Wg5PmmkV//epap2ziXNbC6/OeWQG4rQVG8iTBmNCwnijLp2gdy6uECk6kXIM2PwMiQ/quNtnaB6kJR6LXfAcXUb3wuPhJN64SZ69wNnfPH/z66QvlUhNepT9QIDAQAB"
    
    keytest = "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC+79uFxlvYD7iY/Jijx5A3SUjTCiAoQdMjNkbPAQ0xmMKHiALw/cEzdrAiAdMTjOqoZSc+I2HtbZmYvBG+k0soCyi1Jn8a1ezVXqI/1U/1Z5vvX6RKQ/0UPIQgyhDe719fEOepn+4ljRYxpNJOgSuuVRcLrYsluoWOH/vPTS8V/QIDAQAB"
    phone = "154" + ''.join(random.choices('0123456789', k=8))
    #phone = "15811866375"
    print(phone,'\n')
    body = {
        "phoneMd5": md5(phone)
        }
    
    
    content = json.dumps(body)
    
    #javautil = rasAesEbc()
    #print("****")
    #print(javautil(content,key))
    #print("---------------")
    
    
    qdutil = QDRas()
    
    print("****")
    print(qdutil("IuOPUiymIGMnZ0ZlsQYvzcRauOvYYRAya5gBBPVO5a",content,keytest))
    print("---------------")
   

    """
    
    #javautil = YshAesUtil().encryptText
    #print(javautil("test","7169bc746c4003df4da4d51b1d43c5ab","ijhuhyghuhygyhuh"))
    
    
    
   


    
    
    
   
