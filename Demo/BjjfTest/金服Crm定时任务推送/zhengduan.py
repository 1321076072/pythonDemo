import socket
import subprocess
import sys
import pymysql

import os


def diagnose_mysql_connection(host='192.168.3.10', port=3306,
                              username='root', password=''):
    """
    诊断MySQL连接问题
    """
    print("=" * 60)
    print("MySQL连接诊断工具")
    print("=" * 60)

    print(f"目标服务器: {host}:{port}")
    print(f"用户名: {username}")

    # 1. 检查网络连通性
    print("\n1. 检查网络连通性...")
    if check_ping(host):
        print(f"  ✅ 可以ping通 {host}")
    else:
        print(f"  ❌ 无法ping通 {host}")
        print("  建议: 检查网络连接或IP地址是否正确")

    # 2. 检查端口是否开放
    print("\n2. 检查MySQL端口(3306)是否开放...")
    if check_port(host, port):
        print(f"  ✅ 端口 {port} 已开放")
    else:
        print(f"  ❌ 端口 {port} 未开放或被阻止")
        print("  建议: 检查MySQL服务是否启动，防火墙是否允许")

    # 3. 检查本地MySQL服务
    print("\n3. 检查本地MySQL服务状态...")
    if is_localhost(host):
        check_local_mysql_service()

    # 4. 尝试使用不同驱动连接
    print("\n4. 尝试使用不同MySQL驱动连接...")
    test_drivers(host, port, username, password)

    # 5. 生成解决方案
    print("\n" + "=" * 60)
    print("解决方案建议")
    print("=" * 60)
    generate_solutions(host)


def check_ping(host):
    """检查是否能ping通主机"""
    param = '-n' if sys.platform.lower().startswith('win') else '-c'
    command = ['ping', param, '1', host]

    try:
        result = subprocess.run(command,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                                timeout=5)
        return result.returncode == 0
    except:
        return False


def check_port(host, port):
    """检查端口是否开放"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False


def is_localhost(host):
    """检查是否是本地主机"""
    return host in ['127.0.0.1', 'localhost', '::1'] or host.startswith('192.168')


def check_local_mysql_service():
    """检查本地MySQL服务状态"""
    if sys.platform.startswith('win'):
        # Windows
        try:
            result = subprocess.run(
                ['sc', 'query', 'MySQL'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if 'RUNNING' in result.stdout:
                print("  ✅ MySQL服务正在运行")
            else:
                print("  ❌ MySQL服务未运行")
                print("    启动命令: net start MySQL")
        except:
            print("  ⚠️  无法检查MySQL服务状态")
    else:
        # Linux/Mac
        try:
            result = subprocess.run(
                ['systemctl', 'status', 'mysql'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if 'active (running)' in result.stdout.lower():
                print("  ✅ MySQL服务正在运行")
            else:
                print("  ❌ MySQL服务未运行")
                print("    启动命令: sudo systemctl start mysql")
        except:
            # 尝试service命令
            try:
                result = subprocess.run(
                    ['service', 'mysql', 'status'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if 'active (running)' in result.stdout.lower():
                    print("  ✅ MySQL服务正在运行")
                else:
                    print("  ❌ MySQL服务未运行")
            except:
                print("  ⚠️  无法检查MySQL服务状态")


def test_drivers(host, port, username, password):
    """测试不同的MySQL驱动"""
    drivers = [
        ("mysql-connector-python", mysql.connector.connect),
        ("pymysql", pymysql.connect)
    ]

    for driver_name, connect_func in drivers:
        print(f"  测试 {driver_name}...")
        try:
            if driver_name == "mysql-connector-python":
                connection = connect_func(
                    host=host,
                    port=port,
                    user=username,
                    password=password,
                    connection_timeout=5
                )
            else:  # pymysql
                connection = connect_func(
                    host=host,
                    port=port,
                    user=username,
                    password=password,
                    connect_timeout=5
                )

            if connection:
                print(f"    ✅ 使用 {driver_name} 连接成功")
                cursor = connection.cursor()
                cursor.execute("SELECT version()")
                version = cursor.fetchone()
                print(f"    MySQL版本: {version[0]}")
                connection.close()
                return True

        except Exception as e:
            print(f"    ❌ {driver_name} 连接失败: {e}")

    return False


def generate_solutions(host):
    """根据诊断结果生成解决方案"""
    print("根据您的问题，请按以下步骤排查:")
    print("\n1. 检查MySQL服务是否启动:")
    if sys.platform.startswith('win'):
        print("   - 按 Win+R，输入 services.msc")
        print("   - 找到 MySQL 服务，确保状态为'正在运行'")
        print("   - 或运行命令: net start MySQL")
    else:
        print("   - 运行命令: sudo systemctl start mysql")
        print("   - 或: sudo service mysql start")

    print("\n2. 检查防火墙设置:")
    print("   - 确保端口 3306 在防火墙中是开放的")
    if sys.platform.startswith('win'):
        print(
            "   - 运行: netsh advfirewall firewall add rule name=\"MySQL\" dir=in action=allow protocol=TCP localport=3306")
    else:
        print("   - 运行: sudo ufw allow 3306")

    print("\n3. 检查MySQL配置:")
    print("   - 编辑 my.cnf 或 my.ini 文件")
    print("   - 确保 bind-address 不是 127.0.0.1")
    print("   - 改为: bind-address = 0.0.0.0 或 bind-address = 192.168.3.10")

    print("\n4. 创建远程访问用户:")
    print("   登录MySQL后执行:")
    print("   CREATE USER 'username'@'%' IDENTIFIED BY 'password';")
    print("   GRANT ALL PRIVILEGES ON *.* TO 'username'@'%';")
    print("   FLUSH PRIVILEGES;")

    print("\n5. 如果上述都无效，尝试:")
    print(f"   - 检查IP地址是否正确: {host}")
    print("   - 检查网络是否在同一子网")
    print("   - 联系网络管理员")


# 运行诊断
if __name__ == "__main__":
    # 从命令行参数获取配置，或使用默认值
    import argparse

    parser = argparse.ArgumentParser(description='MySQL连接诊断工具')
    parser.add_argument('--host', default='192.168.3.10', help='MySQL服务器地址')
    parser.add_argument('--port', type=int, default=3306, help='MySQL端口')
    parser.add_argument('--user', default='root', help='MySQL用户名')
    parser.add_argument('--password', default='', help='MySQL密码')

    args = parser.parse_args()

    diagnose_mysql_connection(
        host=args.host,
        port=args.port,
        username=args.user,
        password=args.password
    )