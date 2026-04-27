import random
from MaskFull import MaskFull


def single_test():
    """单次测试示例"""
    print("=" * 60)
    print("单次测试")
    print("=" * 60)

    # 生成随机手机号
    phone = '154' + str(random.randint(10000000, 99999999))

    # 创建测试实例
    mask_full = MaskFull(phone, '杭州', '3301')

    # 初始化环境 (1:测试 2:UAT 3:开发 4:生产)
    mask_full.InitializationRequest(2)

    # 随机生成枚举值
    mask_full.randomize_enum_values()

    # 打印参数中文释义
    mask_full.print_params_description()

    # 执行测试
    mask_full.startTest()
    print()


def batch_test(count=5):
    """批量测试示例"""
    print("=" * 60)
    print(f"批量测试 - 共{count}条数据")
    print("=" * 60)

    cities = [
        ('杭州', '3301'),
        ('上海', '3100'),
        ('北京', '1100'),
        ('广州', '4401'),
        ('深圳', '4403'),
        ('成都', '5101'),
        ('武汉', '4201'),
        ('南京', '3201'),
    ]

    for i in range(count):
        print(f"\n第 {i + 1} 条测试数据:")
        print("-" * 60)

        # 随机选择城市
        city, city_code = random.choice(cities)

        # 生成随机手机号
        phone = '1' + str(random.randint(300000000, 999999999))

        # 创建测试实例
        mask_full = MaskFull(phone, city, city_code)

        # 初始化环境
        mask_full.InitializationRequest(2)

        # 随机生成枚举值
        mask_full.randomize_enum_values()

        # 打印参数
        mask_full.print_params_description()

        # 执行测试
        mask_full.startTest()


def fixed_data_test():
    """固定数据测试示例"""
    print("=" * 60)
    print("固定数据测试")
    print("=" * 60)

    # 使用固定的测试数据
    mask_full = MaskFull('13800138000', '上海', '3100')

    # 初始化环境
    mask_full.InitializationRequest(1)

    # 设置固定参数
    mask_full.params.update({
        'sex': 1,  # 男
        'age': 30,
        'socialSecurity': 3,  # 缴纳6个月以上
        'accumulationFund': 3,  # 缴纳6个月以上
        'carProduction': 2,  # 有车产
        'estate': 2,  # 有房产按揭
        'professionalIdentity': 1,  # 上班族
        'highestEducation': 5,  # 本科
        'monthlyIncome': 15000.00,
        'loanPurpose': 1,  # 个人日常消费
    })

    # 打印参数
    mask_full.print_params_description()

    # 执行测试
    mask_full.startTest()


if __name__ == '__main__':
    # 选择测试模式

    # 模式1: 单次测试
    single_test()

    # 模式2: 批量测试（取消注释使用）
    # batch_test(10)

    # 模式3: 固定数据测试（取消注释使用）
    # fixed_data_test()
