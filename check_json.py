#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os

def check_json_file(file_path='research_reports.json'):
    """检查JSON文件中的研报内容长度"""
    if not os.path.exists(file_path):
        print(f"文件 {file_path} 不存在")
        return
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"JSON文件中包含 {len(data)} 条研报数据")
        
        if data and len(data) > 0:
            first_report = data[0]
            print(f"\n第一份研报信息:")
            print(f"标题: {first_report.get('title', 'N/A')}")
            print(f"行业: {first_report.get('industry', 'N/A')}")
            
            content_preview = first_report.get('content_preview', '')
            full_content = first_report.get('full_content', '')
            
            print(f"内容预览长度: {len(content_preview)} 字符")
            print(f"完整内容长度: {len(full_content)} 字符")
            
            if content_preview:
                print(f"\n内容预览前200字符: {content_preview[:200]}...")
            else:
                print("\n内容预览为空")
            
            if full_content:
                print(f"\n完整内容前200字符: {full_content[:200]}...")
            else:
                print("\n完整内容为空")
    
    except Exception as e:
        print(f"检查JSON文件时出错: {e}")

if __name__ == "__main__":
    check_json_file() 