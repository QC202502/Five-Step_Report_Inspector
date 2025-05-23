#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库清理主脚本
协调整个数据库清理过程，包括修复代码引用和删除旧表
"""

import os
import sys
import time
import sqlite3
import shutil
from datetime import datetime

# 导入其他脚本
try:
    from fix_db_references import update_database_module
except ImportError:
    print("错误：找不到 fix_db_references.py 文件")
    sys.exit(1)

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
    print("=== 数据库清理工具 ===")
    print("此工具将执行以下操作：")
    print("1. 备份数据库和关键代码文件")
    print("2. 更新代码中对旧表的引用")
    print("3. 删除旧版的analysis_results和report_full_analysis表")
    print("\n警告：此操作不可逆！")
    
    confirm = input("是否继续？(y/n): ")
    if confirm.lower() != 'y':
        print("操作已取消")
        return
    
    # 步骤1：备份文件
    print("\n步骤1：备份文件")
    if not backup_files():
        print("备份失败，操作已取消")
        return
    
    # 步骤2：更新代码引用
    print("\n步骤2：更新代码引用")
    if update_database_module():
        print("代码引用已成功更新")
    else:
        print("更新代码引用失败，操作已取消")
        return
    
    # 步骤3：删除旧表
    print("\n步骤3：删除旧表")
    if drop_old_tables():
        print("旧表已成功删除")
    else:
        print("删除旧表失败")
        return
    
    print("\n数据库清理完成！")
    print("系统现在使用新的表结构，旧表已被删除")

if __name__ == "__main__":
    main() 