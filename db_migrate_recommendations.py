#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import os
import sys
from datetime import datetime

def migrate_database():
    """添加推荐系统所需的表结构"""
    print("开始数据库迁移 - 添加推荐系统相关表...")
    
    conn = sqlite3.connect('research_reports.db')
    cursor = conn.cursor()
    
    try:
        # 创建阅读记录表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS read_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER DEFAULT 1,
            report_id INTEGER NOT NULL,
            read_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            read_status TEXT DEFAULT 'read',
            FOREIGN KEY (report_id) REFERENCES reports(id),
            UNIQUE(user_id, report_id)
        )
        ''')
        print("创建阅读记录表成功")
        
        # 创建推荐配置表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS recommendation_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER DEFAULT 1,
            weight_score INTEGER DEFAULT 40,
            weight_time INTEGER DEFAULT 30,
            weight_industry INTEGER DEFAULT 30,
            preferred_industries TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        print("创建推荐配置表成功")
        
        # 检查是否已存在默认配置
        cursor.execute('SELECT COUNT(*) FROM recommendation_settings WHERE user_id = 1')
        if cursor.fetchone()[0] == 0:
            # 添加默认配置
            cursor.execute('''
            INSERT INTO recommendation_settings 
            (user_id, weight_score, weight_time, weight_industry, preferred_industries)
            VALUES (1, 40, 30, 30, '')
            ''')
            print("添加默认推荐配置成功")
        else:
            print("默认推荐配置已存在，跳过添加")
        
        # 提交更改
        conn.commit()
        print("数据库迁移成功完成")
        
    except Exception as e:
        conn.rollback()
        print(f"数据库迁移失败: {str(e)}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database() 