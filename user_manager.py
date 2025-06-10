#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import hashlib
import secrets
import json
import re
import time
from datetime import datetime, timedelta
from functools import wraps
from flask import session, redirect, url_for, flash, request, g

class UserManager:
    """用户管理模块，处理用户认证、注册和资料管理"""
    
    def __init__(self, db_path='research_reports.db'):
        """初始化用户管理器"""
        self.db_path = db_path
        
    def get_db_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def register_user(self, username, email, password, confirm_password):
        """注册新用户"""
        # 验证输入
        if not username or not email or not password:
            return False, "用户名、邮箱和密码不能为空"
            
        if password != confirm_password:
            return False, "两次输入的密码不匹配"
            
        # 验证邮箱格式
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            return False, "邮箱格式不正确"
            
        # 验证用户名长度
        if len(username) < 3 or len(username) > 20:
            return False, "用户名长度必须在3-20个字符之间"
            
        # 验证密码强度
        if len(password) < 6:
            return False, "密码长度不能少于6个字符"
            
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 检查用户名是否已存在
            cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
            if cursor.fetchone():
                return False, "用户名已被使用"
                
            # 检查邮箱是否已存在
            cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
            if cursor.fetchone():
                return False, "邮箱已被注册"
                
            # 生成随机盐值
            salt = secrets.token_hex(16)
            # 创建密码哈希
            password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
            
            # 添加用户
            cursor.execute('''
            INSERT INTO users 
            (username, email, password_hash, salt, created_at, is_active)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, 1)
            ''', (username, email, password_hash, salt))
            
            # 获取新创建的用户ID
            user_id = cursor.lastrowid
            
            # 添加用户资料
            cursor.execute('''
            INSERT INTO user_profiles
            (user_id, display_name)
            VALUES (?, ?)
            ''', (user_id, username))
            
            # 提交事务
            conn.commit()
            return True, "注册成功"
            
        except Exception as e:
            conn.rollback()
            return False, f"注册失败: {str(e)}"
        finally:
            conn.close()
    
    def login(self, username, password, remember=False):
        """用户登录"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 查询用户
            cursor.execute('''
            SELECT id, username, password_hash, salt, is_active, is_admin
            FROM users WHERE username = ?
            ''', (username,))
            
            user = cursor.fetchone()
            
            if not user:
                return False, "用户名或密码错误"
                
            if not user['is_active']:
                return False, "账户已被禁用，请联系管理员"
                
            # 验证密码
            password_hash = hashlib.sha256((password + user['salt']).encode()).hexdigest()
            
            if password_hash != user['password_hash']:
                return False, "用户名或密码错误"
                
            # 生成会话令牌
            session_token = secrets.token_hex(32)
            
            # 设置过期时间（默认1天，记住我则30天）
            expires_at = datetime.now() + timedelta(days=30 if remember else 1)
            
            # 保存会话信息
            cursor.execute('''
            INSERT INTO sessions
            (user_id, session_token, expires_at, ip_address, user_agent, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
            ''', (
                user['id'],
                session_token,
                expires_at.strftime('%Y-%m-%d %H:%M:%S'),
                request.remote_addr,
                request.user_agent.string if request.user_agent else 'Unknown'
            ))
            
            # 更新最后登录时间
            cursor.execute('''
            UPDATE users SET last_login = CURRENT_TIMESTAMP
            WHERE id = ?
            ''', (user['id'],))
            
            # 提交事务
            conn.commit()
            
            # 返回用户信息和会话令牌
            user_info = {
                'id': user['id'],
                'username': user['username'],
                'is_admin': bool(user['is_admin']),
                'session_token': session_token
            }
            
            return True, user_info
            
        except Exception as e:
            conn.rollback()
            return False, f"登录失败: {str(e)}"
        finally:
            conn.close()
    
    def logout(self, session_token):
        """用户登出，使会话失效"""
        if not session_token:
            return True
            
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 将会话标记为非活动
            cursor.execute('''
            UPDATE sessions SET is_active = 0
            WHERE session_token = ?
            ''', (session_token,))
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def verify_session(self, session_token):
        """验证会话是否有效"""
        if not session_token:
            return False, None
            
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 查询会话
            cursor.execute('''
            SELECT s.id, s.user_id, s.expires_at, s.is_active,
                   u.username, u.is_admin, u.is_active AS user_active
            FROM sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.session_token = ?
            ''', (session_token,))
            
            session_data = cursor.fetchone()
            
            if not session_data:
                return False, None
                
            # 检查会话是否有效
            if not session_data['is_active'] or not session_data['user_active']:
                return False, None
                
            # 检查是否过期
            expires_at = datetime.strptime(session_data['expires_at'], '%Y-%m-%d %H:%M:%S')
            if expires_at < datetime.now():
                # 使会话失效
                cursor.execute('UPDATE sessions SET is_active = 0 WHERE id = ?', (session_data['id'],))
                conn.commit()
                return False, None
                
            # 返回用户信息
            user_info = {
                'id': session_data['user_id'],
                'username': session_data['username'],
                'is_admin': bool(session_data['is_admin'])
            }
            
            return True, user_info
            
        except Exception as e:
            print(f"验证会话失败: {str(e)}")
            return False, None
        finally:
            conn.close()
    
    def get_user_profile(self, user_id):
        """获取用户资料"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 查询用户基本信息
            cursor.execute('''
            SELECT u.id, u.username, u.email, u.created_at, u.last_login, u.is_admin,
                   p.display_name, p.bio, p.avatar_url, p.preferred_industries, p.notification_settings
            FROM users u
            LEFT JOIN user_profiles p ON u.id = p.user_id
            WHERE u.id = ?
            ''', (user_id,))
            
            user_data = cursor.fetchone()
            
            if not user_data:
                return None
                
            # 处理JSON字段
            notification_settings = json.loads(user_data['notification_settings']) if user_data['notification_settings'] else {}
            preferred_industries = user_data['preferred_industries'].split(',') if user_data['preferred_industries'] else []
            
            # 构建用户资料
            profile = {
                'id': user_data['id'],
                'username': user_data['username'],
                'email': user_data['email'],
                'display_name': user_data['display_name'] or user_data['username'],
                'bio': user_data['bio'] or '',
                'avatar_url': user_data['avatar_url'] or '',
                'preferred_industries': preferred_industries,
                'notification_settings': notification_settings,
                'created_at': user_data['created_at'],
                'last_login': user_data['last_login'],
                'is_admin': bool(user_data['is_admin'])
            }
            
            return profile
            
        except Exception as e:
            print(f"获取用户资料失败: {str(e)}")
            return None
        finally:
            conn.close()
    
    def update_profile(self, user_id, profile_data):
        """更新用户资料"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 更新用户基本信息
            if 'email' in profile_data:
                # 验证邮箱格式
                if not re.match(r"[^@]+@[^@]+\.[^@]+", profile_data['email']):
                    return False, "邮箱格式不正确"
                    
                # 检查邮箱是否已被其他用户使用
                cursor.execute('SELECT id FROM users WHERE email = ? AND id != ?', 
                              (profile_data['email'], user_id))
                if cursor.fetchone():
                    return False, "邮箱已被其他用户注册"
                    
                # 更新邮箱
                cursor.execute('UPDATE users SET email = ? WHERE id = ?', 
                              (profile_data['email'], user_id))
            
            # 更新密码
            if 'new_password' in profile_data and profile_data['new_password']:
                # 验证当前密码
                if 'current_password' not in profile_data or not profile_data['current_password']:
                    return False, "请输入当前密码"
                    
                # 获取当前密码哈希和盐值
                cursor.execute('SELECT password_hash, salt FROM users WHERE id = ?', (user_id,))
                user_data = cursor.fetchone()
                
                if not user_data:
                    return False, "用户不存在"
                    
                # 验证当前密码
                current_hash = hashlib.sha256((profile_data['current_password'] + user_data['salt']).encode()).hexdigest()
                if current_hash != user_data['password_hash']:
                    return False, "当前密码不正确"
                    
                # 验证新密码强度
                if len(profile_data['new_password']) < 6:
                    return False, "新密码长度不能少于6个字符"
                    
                # 生成新的盐值和密码哈希
                salt = secrets.token_hex(16)
                password_hash = hashlib.sha256((profile_data['new_password'] + salt).encode()).hexdigest()
                
                # 更新密码
                cursor.execute('UPDATE users SET password_hash = ?, salt = ? WHERE id = ?', 
                              (password_hash, salt, user_id))
            
            # 更新用户资料
            update_fields = []
            params = []
            
            if 'display_name' in profile_data:
                update_fields.append('display_name = ?')
                params.append(profile_data['display_name'])
                
            if 'bio' in profile_data:
                update_fields.append('bio = ?')
                params.append(profile_data['bio'])
                
            if 'avatar_url' in profile_data:
                update_fields.append('avatar_url = ?')
                params.append(profile_data['avatar_url'])
                
            if 'preferred_industries' in profile_data:
                industries = ','.join(profile_data['preferred_industries']) if isinstance(profile_data['preferred_industries'], list) else profile_data['preferred_industries']
                update_fields.append('preferred_industries = ?')
                params.append(industries)
                
            if 'notification_settings' in profile_data:
                settings = json.dumps(profile_data['notification_settings']) if isinstance(profile_data['notification_settings'], dict) else profile_data['notification_settings']
                update_fields.append('notification_settings = ?')
                params.append(settings)
            
            if update_fields:
                update_fields.append('updated_at = CURRENT_TIMESTAMP')
                
                query = f'''
                UPDATE user_profiles 
                SET {', '.join(update_fields)}
                WHERE user_id = ?
                '''
                
                params.append(user_id)
                cursor.execute(query, params)
            
            # 提交事务
            conn.commit()
            return True, "资料更新成功"
            
        except Exception as e:
            conn.rollback()
            return False, f"更新资料失败: {str(e)}"
        finally:
            conn.close()
    
    def list_users(self, page=1, per_page=20):
        """列出用户（管理员功能）"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 计算总用户数
            cursor.execute('SELECT COUNT(*) FROM users')
            total_users = cursor.fetchone()[0]
            
            # 分页查询用户列表
            offset = (page - 1) * per_page
            cursor.execute('''
            SELECT u.id, u.username, u.email, u.created_at, u.last_login, 
                   u.is_active, u.is_admin, p.display_name
            FROM users u
            LEFT JOIN user_profiles p ON u.id = p.user_id
            ORDER BY u.created_at DESC
            LIMIT ? OFFSET ?
            ''', (per_page, offset))
            
            users = []
            for row in cursor.fetchall():
                users.append({
                    'id': row['id'],
                    'username': row['username'],
                    'email': row['email'],
                    'display_name': row['display_name'] or row['username'],
                    'created_at': row['created_at'],
                    'last_login': row['last_login'],
                    'is_active': bool(row['is_active']),
                    'is_admin': bool(row['is_admin'])
                })
            
            return {
                'users': users,
                'total': total_users,
                'page': page,
                'per_page': per_page,
                'total_pages': (total_users + per_page - 1) // per_page
            }
            
        except Exception as e:
            print(f"获取用户列表失败: {str(e)}")
            return {'users': [], 'total': 0, 'page': page, 'per_page': per_page, 'total_pages': 0}
        finally:
            conn.close()
    
    def change_user_status(self, user_id, is_active):
        """更改用户状态（激活/禁用）"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 更新用户状态
            cursor.execute('UPDATE users SET is_active = ? WHERE id = ?', (1 if is_active else 0, user_id))
            
            # 如果禁用用户，同时使其所有会话失效
            if not is_active:
                cursor.execute('UPDATE sessions SET is_active = 0 WHERE user_id = ?', (user_id,))
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"更改用户状态失败: {str(e)}")
            return False
        finally:
            conn.close()

# 装饰器：要求用户登录
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('请先登录', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# 装饰器：要求管理员权限
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('请先登录', 'warning')
            return redirect(url_for('login', next=request.url))
        if not session['user'].get('is_admin', False):
            flash('需要管理员权限', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function 