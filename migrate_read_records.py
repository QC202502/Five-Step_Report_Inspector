#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
迁移脚本：将旧版read_records表的记录迁移到新版reading_history表中
"""

import sqlite3
import datetime

def migrate_read_records():
    """迁移旧版已读记录到新版阅读历史表"""
    print("开始迁移旧版已读记录到新版阅读历史表...")
    
    # 连接数据库
    conn = sqlite3.connect('research_reports.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 检查旧表是否存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='read_records'")
    if not cursor.fetchone():
        print("旧版read_records表不存在，无需迁移")
        conn.close()
        return
    
    # 检查新表是否存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reading_history'")
    if not cursor.fetchone():
        print("新版reading_history表不存在，请先运行数据库迁移脚本")
        conn.close()
        return
    
    # 获取所有旧记录
    cursor.execute('''
    SELECT user_id, report_id, read_at, read_status
    FROM read_records
    ''')
    
    old_records = cursor.fetchall()
    print(f"找到 {len(old_records)} 条旧版已读记录")
    
    # 计数器
    migrated_count = 0
    skipped_count = 0
    
    # 开始迁移
    for record in old_records:
        user_id = record['user_id']
        report_id = record['report_id']
        read_at = record['read_at']
        read_status = record['read_status']
        
        # 检查新表中是否已有该记录
        cursor.execute('''
        SELECT id FROM reading_history
        WHERE user_id = ? AND report_id = ?
        ''', (user_id, report_id))
        
        if cursor.fetchone():
            # 记录已存在，跳过
            skipped_count += 1
            continue
        
        # 设置阅读时长和完成状态
        read_duration = 180  # 默认3分钟
        is_completed = 1 if read_status == 'read' else 0
        
        # 插入新记录
        try:
            cursor.execute('''
            INSERT INTO reading_history (user_id, report_id, read_at, read_duration, is_completed)
            VALUES (?, ?, ?, ?, ?)
            ''', (user_id, report_id, read_at, read_duration, is_completed))
            migrated_count += 1
        except sqlite3.IntegrityError:
            # 可能由于唯一约束冲突
            skipped_count += 1
    
    # 提交事务
    conn.commit()
    conn.close()
    
    print(f"迁移完成: {migrated_count} 条记录已迁移, {skipped_count} 条记录已跳过")

if __name__ == "__main__":
    migrate_read_records() 