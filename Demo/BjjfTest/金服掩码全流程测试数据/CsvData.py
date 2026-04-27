import pandas as pd
import requests
import json
from typing import Dict, List


def read_csv_and_request(file_path: str, api_url: str):
    """
    读取CSV文件并发送请求
    """
    try:
        # 读取CSV文件
        df = pd.read_csv(file_path)
        print(f"成功读取文件，共{len(df)}行数据")
        print("字段名:", df.columns.tolist())

        # 转换为字典列表
        records = df.to_dict('records')

        # 发送请求
        for i, record in enumerate(records, 1):
            try:
                response = requests.post(
                    api_url,
                    json=record,  # 使用JSON格式发送
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                )

                print(f"\n记录 {i}/{len(records)}:")
                print(f"  请求数据: {record}")
                print(f"  状态码: {response.status_code}")
                print(f"  响应: {response.text[:200]}...")

                # 处理响应
                if response.status_code == 200:
                    print("  ✅ 请求成功")
                else:
                    print(f"  ❌ 请求失败: {response.status_code}")

            except Exception as e:
                print(f"  ⚠️ 发送记录 {i} 时出错: {str(e)}")

    except Exception as e:
        print(f"读取文件失败: {str(e)}")

# 使用示例
if __name__ == '__main__':
    read_csv_and_request(r'C:\\Users\\useradmin\\Desktop\\81336865-cc29-44fb-b8b0-06030d83c7de.csv', '')