import os.path
import sys

def main():
    # 使用 for 循环
    squares = []
    for x in range(5):
        squares.append(x ** 2)

    # 等效的列表推导式（更简洁）
    squares = [x ** 2 for x in range(10)]
    print(squares)

    for x in squares:
        if x == 9:
            continue
        print(x)

    list = []

    for x in range(10):
        if x < 5:
            list.append(x)
        elif x > 7:
            list.append(x + 2)
        else:
            list.append(x + 1)
    print(list)


    if not os.path.exists("skip"):
        os.makedirs("skip")


    list2 = [1,2,3,4,5,6]
    it = iter(list2)
    for x in it:
        print(x)

    # while True:
    #     try:
    #         print (next(it))
    #     except StopIteration:
    #         sys.exit()

    # def Foo(x):
    #     if (x == 1):
    #         return 1
    #     else:
    #         return x + Foo(x - 1)

    # print(Foo(4))

    print("############")

    # a , b = 0 , 1
    # while b < 1000:
    #     print(b , end=" ")
    #     a , b = b , a + b

    print(dir(os))
    os.direntry("skip")

if __name__ == "__main__":
    main()