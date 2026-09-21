import time

from encryptutil import EncryptUtil
md5 = EncryptUtil.md5_encrypt

from inputpackage.FullMarkInput import FullMarkInput


from threading import Thread
import time
import datetime
import random

"""
通用掩码全流程采量:FullMarkInput
"""


def InputAction(inputobj,argcS,argname,argcity,argdomain,argidcard,argphone=None,argmode=None,argchild_cs=""):
    temp = inputobj(channelSignature=argcS,name=argname,city=argcity,domain=argdomain,idcard=argidcard,phone=argphone,mode=argmode)
    #result = temp._check()
    #print(result)
    #input()
    #result = temp._push()
    #print(result)
    #result = temp.action()
    #print("{}:{}\n".format(inputobj.__name__,result))
    return temp

if __name__ == "__main__":

    
    testChannelSignature = "ruf3Qixk5V7ngs70iJnam00zZ9Muj4xUMbouwxzIJV"
    testDomain = r"bjjfapi.zbjjf.com"

    
    testCity = "克拉玛依"
    

    testName = "陈林"
    tsetIdcard = "350321350302123"
    

    n = 0

    phone = "158" + ''.join(random.choices('0123456789', k=8))
    #phone = "15473999765"
    a = InputAction(FullMarkInput,argcS=testChannelSignature,argcity=testCity,argname=testName,argdomain=testDomain,argidcard=tsetIdcard,argphone=phone,argmode=False)
    
    print(phone)
    print(md5(phone))
    print(a._check())
    input()
    pushresult = a._push()
    print(pushresult)
