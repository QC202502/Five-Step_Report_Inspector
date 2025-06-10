#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import os
import sys
from datetime import datetime
import hashlib
import secrets

def migrate_database():
    """添加用户系统所需的表结构"""
    print("开始数据库迁移 - 添加用户系统相关表...")
    
    conn = sqlite3.connect('research_reports.db')
    cursor = conn.cursor()
    
    try:
        # 创建用户表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            is_admin BOOLEAN DEFAULT 0
        )
        ''')
        print("创建用户表成功")
        
        # 创建用户资料表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            display_name TEXT,
            bio TEXT,
            avatar_url TEXT,
            preferred_industries TEXT DEFAULT '',
            notification_settings TEXT DEFAULT '{"email": true, "site": true}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        ''')
        print("创建用户资料表成功")
        
        # 创建会话表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            session_token TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            ip_address TEXT,
            user_agent TEXT,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        ''')
        print("创建会话表成功")
        
        # 创建管理员账户（如果不存在）
        cursor.execute('SELECT COUNT(*) FROM users WHERE username = "admin"')
        if cursor.fetchone()[0] == 0:
            # 生成随机盐值
            salt = secrets.token_hex(16)
            # 创建密码哈希（默认密码：admin123）
            password = "admin123"
            password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
            
            # 添加管理员账户
            cursor.execute('''
            INSERT INTO users 
            (username, email, password_hash, salt, created_at, is_active, is_admin)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, 1, 1)
            ''', ("admin", "admin@example.com", password_hash, salt))
            
            # 获取新创建的用户ID
            user_id = cursor.lastrowid
            
            # 添加用户资料
            cursor.execute('''
            INSERT INTO user_profiles
            (user_id, display_name, bio, avatar_url)
            VALUES (?, ?, ?, ?)
            ''', (user_id, "系统管理员", "五步法研报分析器系统管理员", ""))
            
            print("创建管理员账户成功 (用户名: admin, 密码: admin123)")
        else:
            print("管理员账户已存在，跳过创建")
        
        # 更新recommendation_settings表，添加user_id外键关联
        cursor.execute('''
        PRAGMA foreign_keys = OFF;
        ''')
        
        # 检查recommendation_settings表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='recommendation_settings'")
        if cursor.fetchone():
            # 创建临时表
            cursor.execute('''
            CREATE TABLE recommendation_settings_temp (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                weight_score INTEGER DEFAULT 40,
                weight_time INTEGER DEFAULT 30,
                weight_industry INTEGER DEFAULT 30,
                preferred_industries TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            ''')
            
            # 复制数据
            cursor.execute('''
            INSERT INTO recommendation_settings_temp
            (id, user_id, weight_score, weight_time, weight_industry, preferred_industries, created_at, updated_at)
            SELECT id, user_id, weight_score, weight_time, weight_industry, preferred_industries, created_at, updated_at
            FROM recommendation_settings
            ''')
            
            # 删除旧表
            cursor.execute('DROP TABLE recommendation_settings')
            
            # 重命名新表
            cursor.execute('ALTER TABLE recommendation_settings_temp RENAME TO recommendation_settings')
            
            print("更新recommendation_settings表成功，添加了外键约束")
        
        # 更新read_records表，添加user_id外键关联
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='read_records'")
        if cursor.fetchone():
            # 创建临时表
            cursor.execute('''
            CREATE TABLE read_records_temp (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                report_id INTEGER NOT NULL,
                read_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                read_status TEXT DEFAULT 'read',
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (report_id) REFERENCES reports(id),
                UNIQUE(user_id, report_id)
            )
            ''')
            
            # 复制数据
            cursor.execute('''
            INSERT INTO read_records_temp
            (id, user_id, report_id, read_at, read_status)
            SELECT id, user_id, report_id, read_at, read_status
            FROM read_records
            ''')
            
            # 删除旧表
            cursor.execute('DROP TABLE read_records')
            
            # 重命名新表
            cursor.execute('ALTER TABLE read_records_temp RENAME TO read_records')
            
            print("更新read_records表成功，添加了外键约束")
        
        cursor.execute('''
        PRAGMA foreign_keys = ON;
        ''')
        
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