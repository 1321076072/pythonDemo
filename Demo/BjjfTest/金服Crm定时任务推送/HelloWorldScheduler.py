import time
from datetime import datetime
import signal
import schedule
import sys
import pymysql
import pymysql.cursors


class HelloWorldScheduler:
    """使用schedule库的Hello World调度器"""

    def __init__(self):
        self.running = True
        self.count = 0

        # 设置信号处理
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def print_hello(self):
        """打印Hello World"""
        self.count += 1
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{current_time}] 第{self.count}次: Hello World!")

    def signal_handler(self, signum, frame):
        """处理退出信号"""
        print(f"\n收到退出信号，正在停止...")
        self.running = False

    def run_every_seconds(self, interval=5):
        """每N秒执行一次"""
        schedule.every(interval).seconds.do(self.print_hello)
        self.run_scheduler()

    def run_every_minutes(self, interval=1):
        """每N分钟执行一次"""
        schedule.every(interval).minutes.do(self.print_hello)
        self.run_scheduler()

    def run_at_specific_time(self, time_str="10:30"):
        """每天特定时间执行"""
        schedule.every().day.at(time_str).do(self.print_hello)
        self.run_scheduler()

    def run_scheduler(self):
        """运行调度器"""
        print(f"=== Hello World定时程序启动 ===")
        print(f"按 Ctrl+C 停止程序")
        print("=" * 30)

        # 立即执行一次
        self.print_hello()

        while self.running:
            schedule.run_pending()
            time.sleep(1)

        print(f"=== 程序已停止，共执行 {self.count} 次 ===")

    def connect_mysql_pymysql(self):
        """使用pymysql连接MySQL"""
        try:
            connection = pymysql.connect(
                host='192.168.3.10',
                port=3306,
                user='41193',
                password='root',
                database='SgQHvsy9M7LWKBCz',
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            print("✅ 成功连接到MySQL数据库")
            return connection
        except pymysql.MySQLError as e:
            print(f"❌ 连接MySQL失败: {e}")
            return None

if __name__ == "__main__":
    scheduler = HelloWorldScheduler()

    # 选择一种定时方式
    # scheduler.run_every_seconds(interval=3)  # 每3秒执行
    # scheduler.run_every_minutes(interval=1)  # 每1分钟执行
    # scheduler.run_at_specific_time("10:30")  # 每天10:30执行
    scheduler.connect_mysql_pymysql()