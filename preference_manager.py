#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import json
import os
from datetime import datetime

class PreferenceManager:
    """用户偏好设置管理类"""
    
    def __init__(self, db_path='research_reports.db'):
        """初始化偏好设置管理器"""
        self.db_path = db_path
        
    def get_db_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_user_preferences(self, user_id, preference_type=None):
        """
        获取用户偏好设置
        
        参数:
            user_id (int): 用户ID
            preference_type (str, optional): 偏好设置类型，如 'recommendation', 'reading', 'privacy'
                                           如果为None，则返回所有类型的偏好设置
        
        返回:
            dict: 用户偏好设置
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            if preference_type:
                # 获取特定类型的偏好设置
                cursor.execute('''
                SELECT preference_data FROM user_preferences 
                WHERE user_id = ? AND preference_type = ?
                ''', (user_id, preference_type))
                
                result = cursor.fetchone()
                if result:
                    return json.loads(result['preference_data'])
                else:
                    # 返回默认设置
                    return self._get_default_preferences(preference_type)
            else:
                # 获取所有类型的偏好设置
                cursor.execute('''
                SELECT preference_type, preference_data FROM user_preferences 
                WHERE user_id = ?
                ''', (user_id,))
                
                results = cursor.fetchall()
                preferences = {}
                
                for row in results:
                    preferences[row['preference_type']] = json.loads(row['preference_data'])
                
                # 补充缺失的默认设置
                for pref_type in ['recommendation', 'reading', 'privacy']:
                    if pref_type not in preferences:
                        preferences[pref_type] = self._get_default_preferences(pref_type)
                
                return preferences
                
        except Exception as e:
            print(f"获取用户偏好设置失败: {str(e)}")
            # 返回默认设置
            if preference_type:
                return self._get_default_preferences(preference_type)
            else:
                return {
                    'recommendation': self._get_default_preferences('recommendation'),
                    'reading': self._get_default_preferences('reading'),
                    'privacy': self._get_default_preferences('privacy')
                }
        finally:
            conn.close()
    
    def update_user_preferences(self, user_id, preference_type, preferences):
        """
        更新用户偏好设置
        
        参数:
            user_id (int): 用户ID
            preference_type (str): 偏好设置类型，如 'recommendation', 'reading', 'privacy'
            preferences (dict): 偏好设置数据
            
        返回:
            tuple: (成功标志, 消息)
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 将偏好设置转换为JSON字符串
            preference_data = json.dumps(preferences)
            
            # 尝试更新现有记录
            cursor.execute('''
            UPDATE user_preferences 
            SET preference_data = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ? AND preference_type = ?
            ''', (preference_data, user_id, preference_type))
            
            # 如果没有更新任何记录，则插入新记录
            if cursor.rowcount == 0:
                cursor.execute('''
                INSERT INTO user_preferences (user_id, preference_type, preference_data)
                VALUES (?, ?, ?)
                ''', (user_id, preference_type, preference_data))
            
            conn.commit()
            return True, "偏好设置更新成功"
            
        except Exception as e:
            conn.rollback()
            print(f"更新用户偏好设置失败: {str(e)}")
            return False, f"更新偏好设置失败: {str(e)}"
        finally:
            conn.close()
    
    def get_notification_settings(self, user_id):
        """
        获取用户通知设置
        
        参数:
            user_id (int): 用户ID
            
        返回:
            dict: 通知设置
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            SELECT notification_settings FROM user_profiles 
            WHERE user_id = ?
            ''', (user_id,))
            
            result = cursor.fetchone()
            if result and result['notification_settings']:
                return json.loads(result['notification_settings'])
            else:
                return self._get_default_notification_settings()
                
        except Exception as e:
            print(f"获取用户通知设置失败: {str(e)}")
            return self._get_default_notification_settings()
        finally:
            conn.close()
    
    def update_notification_settings(self, user_id, settings):
        """
        更新用户通知设置
        
        参数:
            user_id (int): 用户ID
            settings (dict): 通知设置
            
        返回:
            tuple: (成功标志, 消息)
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 将设置转换为JSON字符串
            settings_data = json.dumps(settings)
            
            cursor.execute('''
            UPDATE user_profiles 
            SET notification_settings = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
            ''', (settings_data, user_id))
            
            if cursor.rowcount == 0:
                return False, "未找到用户资料"
            
            conn.commit()
            return True, "通知设置更新成功"
            
        except Exception as e:
            conn.rollback()
            print(f"更新用户通知设置失败: {str(e)}")
            return False, f"更新通知设置失败: {str(e)}"
        finally:
            conn.close()
    
    def record_reading_history(self, user_id, report_id, duration=0, is_completed=True):
        """
        记录用户阅读历史，并计算阅读完成度
        """
        privacy_settings = self.get_user_preferences(user_id, 'privacy')
        if not privacy_settings.get('collect_reading_history', True):
            return True

        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 获取报告总字数
            cursor.execute("SELECT LENGTH(full_content) FROM reports WHERE id = ?", (report_id,))
            content_length_row = cursor.fetchone()
            content_length = content_length_row[0] if content_length_row and content_length_row[0] is not None else 0

            # 计算阅读完成度
            completion_rate = 0.0
            if content_length > 0:
                # 假设平均阅读速度为 5字/秒 (300字/分钟)
                estimated_read_time = content_length / 5
                if estimated_read_time > 0:
                    completion_rate = min(1.0, duration / estimated_read_time) # 完成度最高为100%

            # 检查是否已有记录
            cursor.execute('''
            SELECT id, read_duration, is_completed FROM reading_history 
            WHERE user_id = ? AND report_id = ?
            ''', (user_id, report_id))
            existing = cursor.fetchone()
            
            if existing:
                # 更新现有记录
                new_duration = duration
                new_completed = 1 if is_completed else existing['is_completed']
                
                cursor.execute('''
                UPDATE reading_history 
                SET read_at = CURRENT_TIMESTAMP, 
                    read_duration = ?, 
                    is_completed = ?,
                    completion_rate = ?
                WHERE id = ?
                ''', (new_duration, new_completed, completion_rate, existing['id']))
            else:
                # 插入新记录
                cursor.execute('''
                INSERT INTO reading_history (user_id, report_id, read_duration, is_completed, completion_rate)
                VALUES (?, ?, ?, ?, ?)
                ''', (user_id, report_id, duration, 1 if is_completed else 0, completion_rate))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"记录阅读历史时出错: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def get_reading_history(self, user_id, limit=20, offset=0, sort_by='recent', filter_by='all'):
        """
        获取用户阅读历史
        
        参数:
            user_id (int): 用户ID
            limit (int): 返回记录数量限制
            offset (int): 分页偏移量
            sort_by (str): 排序方式，可选值：recent（最近阅读）、oldest（最早阅读）、industry（按行业）
            filter_by (str): 筛选方式，可选值：all（全部）、completed（已完成）、incomplete（未完成）
            
        返回:
            list: 阅读历史记录列表
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 构建基本查询
            query = '''
            SELECT h.id, h.report_id, h.read_at, h.read_duration, h.is_completed,
                   r.title, r.date as publish_date, r.org as author, r.industry
            FROM reading_history h
            JOIN reports r ON h.report_id = r.id
            WHERE h.user_id = ?
            '''
            
            params = [user_id]
            
            # 添加筛选条件
            if filter_by == 'completed':
                query += ' AND h.is_completed = 1'
            elif filter_by == 'incomplete':
                query += ' AND h.is_completed = 0'
            
            # 添加排序条件
            if sort_by == 'oldest':
                query += ' ORDER BY h.read_at ASC'
            elif sort_by == 'industry':
                query += ' ORDER BY r.industry ASC, h.read_at DESC'
            else:  # 默认按最近阅读排序
                query += ' ORDER BY h.read_at DESC'
            
            # 添加分页
            query += ' LIMIT ? OFFSET ?'
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            
            results = cursor.fetchall()
            history = []
            
            for row in results:
                # 将UTC时间转换为北京时间
                read_at = row['read_at']
                if read_at:
                    try:
                        # 解析时间字符串
                        from datetime import datetime, timedelta
                        dt = datetime.strptime(read_at, '%Y-%m-%d %H:%M:%S')
                        # 添加8小时得到北京时间
                        beijing_time = dt + timedelta(hours=8)
                        read_at = beijing_time.strftime('%Y-%m-%d %H:%M:%S')
                    except Exception as e:
                        print(f"时间转换错误: {str(e)}")
                
                history.append({
                    'id': row['id'],
                    'report_id': row['report_id'],
                    'read_at': read_at,
                    'read_duration': row['read_duration'],
                    'is_completed': bool(row['is_completed']),
                    'title': row['title'],
                    'author': row['author'],
                    'publish_date': row['publish_date'],
                    'industry': row['industry']
                })
            
            return history
                
        except Exception as e:
            print(f"获取阅读历史失败: {str(e)}")
            return []
        finally:
            conn.close()
            
    def get_reading_history_count(self, user_id, filter_by='all'):
        """
        获取用户阅读历史记录总数
        
        参数:
            user_id (int): 用户ID
            filter_by (str): 筛选方式，可选值：all（全部）、completed（已完成）、incomplete（未完成）
            
        返回:
            int: 记录总数
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 构建基本查询
            query = '''
            SELECT COUNT(*) as count
            FROM reading_history h
            WHERE h.user_id = ?
            '''
            
            params = [user_id]
            
            # 添加筛选条件
            if filter_by == 'completed':
                query += ' AND h.is_completed = 1'
            elif filter_by == 'incomplete':
                query += ' AND h.is_completed = 0'
            
            cursor.execute(query, params)
            result = cursor.fetchone()
            
            return result['count'] if result else 0
                
        except Exception as e:
            print(f"获取阅读历史记录数失败: {str(e)}")
            return 0
        finally:
            conn.close()
    
    def clear_reading_history(self, user_id):
        """
        清除用户阅读历史
        
        参数:
            user_id (int): 用户ID
            
        返回:
            tuple: (成功标志, 消息)
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM reading_history WHERE user_id = ?', (user_id,))
            conn.commit()
            return True, f"已清除 {cursor.rowcount} 条阅读历史记录"
            
        except Exception as e:
            conn.rollback()
            print(f"清除阅读历史失败: {str(e)}")
            return False, f"清除阅读历史失败: {str(e)}"
        finally:
            conn.close()
    
    def record_search_history(self, user_id, query, result_count=0):
        """
        记录用户搜索历史
        
        参数:
            user_id (int): 用户ID
            query (str): 搜索查询
            result_count (int): 搜索结果数量
            
        返回:
            bool: 成功标志
        """
        # 首先检查用户的隐私设置是否允许收集搜索历史
        privacy_settings = self.get_user_preferences(user_id, 'privacy')
        if not privacy_settings.get('collect_search_history', True):
            return True  # 如果用户设置不允许收集，则直接返回成功
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            INSERT INTO search_history (user_id, search_query, result_count)
            VALUES (?, ?, ?)
            ''', (user_id, query, result_count))
            
            conn.commit()
            return True
            
        except Exception as e:
            conn.rollback()
            print(f"记录搜索历史失败: {str(e)}")
            return False
        finally:
            conn.close()
    
    def get_search_history(self, user_id, limit=20, offset=0):
        """
        获取用户搜索历史
        
        参数:
            user_id (int): 用户ID
            limit (int): 返回记录数量限制
            offset (int): 分页偏移量
            
        返回:
            list: 搜索历史记录列表
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            SELECT id, search_query, search_at, result_count
            FROM search_history
            WHERE user_id = ?
            ORDER BY search_at DESC
            LIMIT ? OFFSET ?
            ''', (user_id, limit, offset))
            
            results = cursor.fetchall()
            history = []
            
            for row in results:
                history.append({
                    'id': row['id'],
                    'query': row['search_query'],
                    'timestamp': row['search_at'],
                    'result_count': row['result_count']
                })
            
            return history
                
        except Exception as e:
            print(f"获取搜索历史失败: {str(e)}")
            return []
        finally:
            conn.close()
    
    def clear_search_history(self, user_id):
        """
        清除用户搜索历史
        
        参数:
            user_id (int): 用户ID
            
        返回:
            tuple: (成功标志, 消息)
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM search_history WHERE user_id = ?', (user_id,))
            conn.commit()
            return True, f"已清除 {cursor.rowcount} 条搜索历史记录"
            
        except Exception as e:
            conn.rollback()
            print(f"清除搜索历史失败: {str(e)}")
            return False, f"清除搜索历史失败: {str(e)}"
        finally:
            conn.close()
    
    def export_user_data(self, user_id):
        """
        导出用户的所有相关数据
        
        参数:
            user_id (int): 用户ID
            
        返回:
            dict: 用户数据
        """
        data = {
            'preferences': self.get_user_preferences(user_id),
            'notification_settings': self.get_notification_settings(user_id),
            'reading_history': self.get_reading_history(user_id, limit=1000),
            'search_history': self.get_search_history(user_id, limit=1000),
            'export_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return data
    
    def _get_default_preferences(self, preference_type):
        """
        获取默认偏好设置
        
        参数:
            preference_type (str): 偏好设置类型
            
        返回:
            dict: 默认设置
        """
        if preference_type == 'recommendation':
            return {
                'weight_score': 40,
                'weight_time': 30,
                'weight_industry': 30,
                'preferred_industries': [],
                'show_recommendations': True,
                'show_recommendation_modal': True,
                'auto_mark_read': True,
                'focused_industries': [],
                'preferred_report_types': [],
                'followed_organizations': []
            }
        elif preference_type == 'reading':
            return {
                'default_view': 'card',
                'reports_per_page': 20,
                'default_sort': 'date',
                'sort_desc': True,
                'auto_expand_summary': True,
                'auto_expand_analysis': False
            }
        elif preference_type == 'privacy':
            return {
                'collect_reading_history': True,
                'collect_search_history': True,
                'show_profile': True,
                'show_reading_history': False
            }
        else:
            return {}
    
    def _get_default_notification_settings(self):
        """
        获取默认通知设置
        
        返回:
            dict: 默认通知设置
        """
        return {
            'email': True,
            'site': True,
            'new_reports': True,
            'industry_reports': True,
            'high_quality': True
        }

    def get_reading_habit_stats(self, user_id):
        """
        获取用户的阅读习惯统计数据，用于生成报告。
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        stats = {
            'top_industries': [],
            'top_organizations': [],
            'total_reports_read': 0,
            'total_reading_duration': 0,
            'average_completion_rate': 0.0
        }

        try:
            # 1. 最常阅读的行业 (Top 5)
            cursor.execute('''
                SELECT r.industry, COUNT(h.id) as read_count
                FROM reading_history h
                JOIN reports r ON h.report_id = r.id
                WHERE h.user_id = ? AND r.industry IS NOT NULL AND r.industry != ''
                GROUP BY r.industry
                ORDER BY read_count DESC
                LIMIT 5
            ''', (user_id,))
            stats['top_industries'] = [{'industry': row[0], 'count': row[1]} for row in cursor.fetchall()]

            # 2. 最常阅读的机构 (Top 5)
            cursor.execute('''
                SELECT r.org, COUNT(h.id) as read_count
                FROM reading_history h
                JOIN reports r ON h.report_id = r.id
                WHERE h.user_id = ? AND r.org IS NOT NULL AND r.org != ''
                GROUP BY r.org
                ORDER BY read_count DESC
                LIMIT 5
            ''', (user_id,))
            stats['top_organizations'] = [{'organization': row[0], 'count': row[1]} for row in cursor.fetchall()]

            # 3, 4, 5. 总数、总时长、平均完成度
            cursor.execute('''
                SELECT 
                    COUNT(id),
                    SUM(read_duration),
                    AVG(completion_rate)
                FROM reading_history
                WHERE user_id = ?
            ''', (user_id,))
            result = cursor.fetchone()
            if result:
                stats['total_reports_read'] = result[0] or 0
                stats['total_reading_duration'] = result[1] or 0
                stats['average_completion_rate'] = round(result[2] or 0.0, 2)

        except Exception as e:
            print(f"获取阅读习惯统计时出错: {e}")
        finally:
            conn.close()
            
        return stats 