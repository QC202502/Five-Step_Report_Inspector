#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
导入研报数据到数据库
从research_reports.json中读取研报数据，然后导入到数据库中
"""

import json
import os
import sys
import sqlite3
from datetime import datetime
import database as db  # 导入数据库模块
from analysis_db import AnalysisDatabase  # 导入分析数据库模块

def main():
    print("开始导入研报数据到数据库...")
    
    # 检查JSON文件是否存在
    json_file = 'research_reports.json'
    if not os.path.exists(json_file):
        print(f"错误: 未找到 {json_file}")
        sys.exit(1)
    
    # 读取JSON文件
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            reports = json.load(f)
            
        print(f"从 {json_file} 加载了 {len(reports)} 条研报数据")
    except Exception as e:
        print(f"读取JSON文件时出错: {e}")
        sys.exit(1)
    
    # 导入到research_reports.db
    try:
        # 初始化数据库
        db.init_db()
        import_count = db.import_from_json(json_file)
        print(f"成功导入 {import_count} 条研报到 research_reports.db")
    except Exception as e:
        print(f"导入到research_reports.db时出错: {e}")
    
    # 导入到分析数据库
    try:
        # 初始化分析数据库
        analysis_db = AnalysisDatabase()
        
        # 获取数据库中的研报ID和链接映射
        conn = sqlite3.connect('research_reports.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, link FROM reports")
        report_links = {row['link']: row['id'] for row in cursor.fetchall()}
        conn.close()
        
        # 导入分析结果
        analysis_count = 0
        for report in reports:
            if 'link' in report and report['link'] in report_links:
                report_id = report_links[report['link']]
                if 'analysis' in report and isinstance(report['analysis'], dict):
                    # 构建完整的分析结果
                    analysis_result = {
                        'analysis': report['analysis'],
                        'full_analysis': report.get('full_analysis', '')
                    }
                    
                    # 保存到分析数据库
                    try:
                        analysis_db.save_analysis_result(report_id, analysis_result)
                        analysis_count += 1
                    except Exception as e:
                        print(f"保存分析结果时出错(ID: {report_id}): {e}")
        
        print(f"成功导入 {analysis_count} 条分析结果到分析数据库")
    except Exception as e:
        print(f"导入到分析数据库时出错: {e}")
    
    print("导入完成")

if __name__ == "__main__":
    main() 