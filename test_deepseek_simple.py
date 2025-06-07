#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
简单测试脚本：测试OpenAI SDK调用DeepSeek API
"""

from openai import OpenAI

def main():
    print("开始简单测试 OpenAI SDK 调用 DeepSeek API...")
    
    # 创建OpenAI客户端
    client = OpenAI(
        api_key="YOUR_DEEPSEEK_API_KEY",  # 替换为您的DeepSeek API Key
        base_url="https://api.deepseek.com"
    )
    
    try:
        # 发送简单的英文请求
        print("发送英文请求...")
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a helpful assistant"},
                {"role": "user", "content": "Hello, how are you?"}
            ],
            stream=False
        )
        
        print("英文响应:")
        print(response.choices[0].message.content)
        print("\n")
        
        # 尝试发送中文请求
        print("发送中文请求...")
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a helpful assistant"},
                {"role": "user", "content": "你好，请用中文回答：今天天气怎么样？"}
            ],
            stream=False
        )
        
        print("中文响应:")
        print(response.choices[0].message.content)
        
        print("\n测试成功完成！")
        return True
        
    except Exception as e:
        print(f"测试过程中出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    main() 