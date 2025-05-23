#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库清理脚本
用于删除旧版的analysis_results和report_full_analysis表
"""

import sqlite3
import os
import sys

# 数据库文件路径
DB_FILE = 'research_reports.db'

def get_db_connection():
    """获取数据库连接"""
    if not os.path.exists(DB_FILE):
        print(f"错误：数据库文件 {DB_FILE} 不存在")
        sys.exit(1)
    
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def backup_database():
    """备份数据库"""
    import shutil
    backup_file = f"{DB_FILE}.bak"
    try:
        shutil.copy2(DB_FILE, backup_file)
        print(f"数据库已备份到: {backup_file}")
        return True
    except Exception as e:
        print(f"备份数据库时出错: {e}")
        return False

def drop_old_tables():
    """删除旧版表"""
    conn = get_db_connection()
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
    print("此工具将删除旧版的analysis_results和report_full_analysis表")
    print("警告：此操作不可逆，建议先备份数据库")
    
    confirm = input("是否继续？(y/n): ")
    if confirm.lower() != 'y':
        print("操作已取消")
        return
    
    # 备份数据库
    if not backup_database():
        print("备份失败，操作已取消")
        return
    
    # 删除旧表
    if drop_old_tables():
        print("旧表已成功删除")
    else:
        print("删除旧表失败")
        print(f"您可以使用备份文件 {DB_FILE}.bak 恢复数据库")

if __name__ == "__main__":
    main() 