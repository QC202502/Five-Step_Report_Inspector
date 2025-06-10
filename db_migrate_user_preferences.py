#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import json
import os
import sys

def migrate():
    """
    执行数据库迁移，添加用户偏好设置相关的表和字段
    """
    print("开始执行用户偏好设置数据库迁移...")
    
    # 连接数据库
    db_path = 'research_reports.db'
    if not os.path.exists(db_path):
        print(f"错误：数据库文件 {db_path} 不存在")
        sys.exit(1)
        
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # 检查 user_profiles 表是否已存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_profiles'")
        if not cursor.fetchone():
            print("错误：user_profiles 表不存在，请先运行 db_migrate_users.py")
            sys.exit(1)
        
        # 检查 user_preferences 表是否已存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_preferences'")
        if cursor.fetchone():
            print("user_preferences 表已存在，跳过创建")
        else:
            # 创建用户偏好设置表
            cursor.execute('''
            CREATE TABLE user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                preference_type TEXT NOT NULL,
                preference_data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE (user_id, preference_type)
            )
            ''')
            print("创建 user_preferences 表成功")
        
        # 检查 reading_history 表是否已存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reading_history'")
        if cursor.fetchone():
            print("reading_history 表已存在，跳过创建")
        else:
            # 创建阅读历史表
            cursor.execute('''
            CREATE TABLE reading_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                report_id INTEGER NOT NULL,
                read_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                read_duration INTEGER DEFAULT 0,
                is_completed BOOLEAN DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (report_id) REFERENCES reports(id),
                UNIQUE (user_id, report_id)
            )
            ''')
            print("创建 reading_history 表成功")
        
        # 检查 search_history 表是否已存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='search_history'")
        if cursor.fetchone():
            print("search_history 表已存在，跳过创建")
        else:
            # 创建搜索历史表
            cursor.execute('''
            CREATE TABLE search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                search_query TEXT NOT NULL,
                search_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                result_count INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            ''')
            print("创建 search_history 表成功")
        
        # 检查 user_profiles 表中是否已有 notification_settings 字段
        cursor.execute("PRAGMA table_info(user_profiles)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'notification_settings' not in columns:
            cursor.execute('''
            ALTER TABLE user_profiles ADD COLUMN notification_settings TEXT DEFAULT '{}'
            ''')
            print("在 user_profiles 表中添加 notification_settings 字段成功")
        
        # 为每个用户添加默认的偏好设置
        cursor.execute("SELECT id FROM users WHERE is_active = 1")
        users = cursor.fetchall()
        
        # 默认推荐设置
        default_recommendation = {
            'weight_score': 40,
            'weight_time': 30,
            'weight_industry': 30,
            'preferred_industries': [],
            'show_recommendations': True,
            'show_recommendation_modal': True,
            'auto_mark_read': True
        }
        
        # 默认阅读偏好
        default_reading = {
            'default_view': 'card',
            'reports_per_page': 20,
            'default_sort': 'date',
            'sort_desc': True,
            'auto_expand_summary': True,
            'auto_expand_analysis': False
        }
        
        # 默认隐私设置
        default_privacy = {
            'collect_reading_history': True,
            'collect_search_history': True,
            'show_profile': True,
            'show_reading_history': False
        }
        
        # 默认通知设置
        default_notification = {
            'email': True,
            'site': True,
            'new_reports': True,
            'industry_reports': True,
            'high_quality': True
        }
        
        for user in users:
            user_id = user['id']
            
            # 添加默认推荐设置
            cursor.execute('''
            INSERT OR IGNORE INTO user_preferences (user_id, preference_type, preference_data)
            VALUES (?, ?, ?)
            ''', (user_id, 'recommendation', json.dumps(default_recommendation)))
            
            # 添加默认阅读偏好
            cursor.execute('''
            INSERT OR IGNORE INTO user_preferences (user_id, preference_type, preference_data)
            VALUES (?, ?, ?)
            ''', (user_id, 'reading', json.dumps(default_reading)))
            
            # 添加默认隐私设置
            cursor.execute('''
            INSERT OR IGNORE INTO user_preferences (user_id, preference_type, preference_data)
            VALUES (?, ?, ?)
            ''', (user_id, 'privacy', json.dumps(default_privacy)))
            
            # 更新用户资料中的通知设置
            cursor.execute('''
            UPDATE user_profiles 
            SET notification_settings = ? 
            WHERE user_id = ? AND (notification_settings IS NULL OR notification_settings = '{}')
            ''', (json.dumps(default_notification), user_id))
        
        # 提交事务
        conn.commit()
        print(f"为 {len(users)} 个用户添加默认偏好设置成功")
        
        print("用户偏好设置数据库迁移完成")
        
    except Exception as e:
        conn.rollback()
        print(f"迁移失败: {str(e)}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    migrate() 