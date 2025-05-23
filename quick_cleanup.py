#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速数据库清理脚本
无需用户交互，直接执行清理操作
"""

import os
import sys
import sqlite3
import shutil
from datetime import datetime

# 数据库文件路径
DB_FILE = 'research_reports.db'

def backup_files():
    """备份数据库和关键代码文件"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    backup_dir = f"backup_{timestamp}"
    
    try:
        # 创建备份目录
        os.makedirs(backup_dir, exist_ok=True)
        
        # 备份数据库
        if os.path.exists(DB_FILE):
            shutil.copy2(DB_FILE, os.path.join(backup_dir, DB_FILE))
            print(f"已备份数据库到: {os.path.join(backup_dir, DB_FILE)}")
        
        # 备份关键代码文件
        for file in ['database.py', 'app.py', 'analysis_db.py']:
            if os.path.exists(file):
                shutil.copy2(file, os.path.join(backup_dir, file))
                print(f"已备份 {file} 到: {os.path.join(backup_dir, file)}")
        
        print(f"所有文件已备份到目录: {backup_dir}")
        return True
    except Exception as e:
        print(f"备份文件时出错: {e}")
        return False

def update_database_module():
    """更新database.py文件，替换对旧表的引用"""
    adapter_code = """
# 适配器函数，使用新表结构替代旧表
def get_analysis_results_for_report(report_id):
    \"\"\"
    获取研报的五步法分析结果（适配旧接口）
    
    参数:
    report_id (int): 研报ID
    
    返回:
    dict: 分析结果字典
    \"\"\"
    from analysis_db import AnalysisDatabase
    db = AnalysisDatabase()
    analysis = db.get_analysis_by_report_id(report_id)
    if not analysis:
        return {}
    
    # 将新格式转换为旧格式
    result = {}
    for step_name, step_data in analysis['steps'].items():
        result[step_name] = {
            'found': step_data['found'],
            'description': step_data['description'],
            'step_score': step_data['step_score'],
            'keywords': [],  # 旧格式需要这些字段，但新格式可能没有
            'evidence': [],
            'framework_summary': step_data.get('framework_summary', '')
        }
    
    return result

def get_full_analysis_for_report(report_id):
    \"\"\"
    获取研报的完整分析文本（适配旧接口）
    
    参数:
    report_id (int): 研报ID
    
    返回:
    dict: 包含完整分析文本和一句话总结的字典
    \"\"\"
    from analysis_db import AnalysisDatabase
    db = AnalysisDatabase()
    analysis = db.get_analysis_by_report_id(report_id)
    if not analysis:
        return None
    
    # 将新格式转换为旧格式
    return {
        'full_analysis_text': analysis['full_analysis'],
        'one_line_summary': analysis['one_line_summary']
    }
"""
    
    # 读取database.py文件
    try:
        with open('database.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找并替换旧的函数定义
        import re
        pattern_analysis_results = r'def get_analysis_results_for_report\(.*?return.*?\n\s*\n'
        pattern_full_analysis = r'def get_full_analysis_for_report\(.*?return.*?\n\s*\n'
        
        # 使用正则表达式替换函数定义
        content = re.sub(pattern_analysis_results, '', content, flags=re.DOTALL)
        content = re.sub(pattern_full_analysis, '', content, flags=re.DOTALL)
        
        # 在文件末尾添加新的适配器函数
        content += adapter_code
        
        # 写回文件
        with open('database.py', 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("已更新 database.py 文件")
        return True
    except Exception as e:
        print(f"更新 database.py 文件时出错: {e}")
        return False

def drop_old_tables():
    """删除旧版表"""
    conn = sqlite3.connect(DB_FILE)
    try:
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='analysis_results'")
        if cursor.fetchone():
            # 删除analysis_results表
            cursor.execute("DROP TABLE analysis_results")
            print("已删除旧版表: analysis_results")
        else:
            print("表 analysis_results 不存在，无需删除")
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='report_full_analysis'")
        if cursor.fetchone():
            # 删除report_full_analysis表
            cursor.execute("DROP TABLE report_full_analysis")
            print("已删除旧版表: report_full_analysis")
        else:
            print("表 report_full_analysis 不存在，无需删除")
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"删除表时出错: {e}")
        return False
    finally:
        conn.close()

def main():
    """主函数"""
    print("=== 快速数据库清理工具 ===")
    
    # 步骤1：备份文件
    print("\n步骤1：备份文件")
    backup_files()
    
    # 步骤2：更新代码引用
    print("\n步骤2：更新代码引用")
    update_database_module()
    
    # 步骤3：删除旧表
    print("\n步骤3：删除旧表")
    drop_old_tables()
    
    print("\n数据库清理完成！")
    print("系统现在使用新的表结构，旧表已被删除")

if __name__ == "__main__":
    main() 