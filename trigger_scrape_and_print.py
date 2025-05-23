#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
from app import app # 假设 app.py 在同一目录下或者 PYTHONPATH 中

def run_scrape():
    print("开始通过 API 触发爬虫...")
    with app.test_client() as client:
        try:
            response = client.get('/scrape')
            response.raise_for_status() # 如果状态码不是 2xx，则抛出异常
            
            print("\n爬虫 API 调用成功。")
            try:
                # 尝试解析JSON响应
                result_data = response.get_json()
                print("API 返回结果:")
                print(json.dumps(result_data, indent=4, ensure_ascii=False))
            except Exception as e:
                # 如果不是JSON，打印原始数据
                print(f"API 返回的不是有效的JSON，原始数据: {response.data.decode(errors='ignore')}")
                print(f"解析JSON时出错: {e}")

        except Exception as e:
            print(f"调用 /scrape API 时出错: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"API 错误响应: {e.response.data.decode(errors='ignore')}")

if __name__ == "__main__":
    run_scrape() 