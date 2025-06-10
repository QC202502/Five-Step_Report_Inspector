#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
from datetime import datetime, timedelta
import json
import math

class RecommendationEngine:
    """研报推荐引擎"""
    
    def __init__(self, db_path='research_reports.db'):
        """初始化推荐引擎"""
        self.db_path = db_path
    
    def get_user_settings(self, user_id=1):
        """获取用户的推荐设置"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT weight_score, weight_time, weight_industry, preferred_industries
        FROM recommendation_settings
        WHERE user_id = ?
        ''', (user_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'weight_score': result[0],
                'weight_time': result[1],
                'weight_industry': result[2],
                'preferred_industries': result[3].split(',') if result[3] else []
            }
        else:
            # 返回默认设置
            return {
                'weight_score': 40,
                'weight_time': 30,
                'weight_industry': 30,
                'preferred_industries': []
            }
    
    def calculate_time_score(self, date_str):
        """计算时间新鲜度分数，越新的研报分数越高"""
        try:
            if not date_str:
                return 50  # 默认中等分数
                
            # 尝试解析日期
            date_formats = ["%Y-%m-%d", "%Y/%m/%d", "%Y年%m月%d日", "%Y.%m.%d"]
            report_date = None
            
            for fmt in date_formats:
                try:
                    report_date = datetime.strptime(date_str, fmt)
                    break
                except ValueError:
                    continue
            
            if not report_date:
                return 50
            
            # 计算与当前日期的差距
            days_diff = (datetime.now() - report_date).days
            
            # 一周内的研报得分最高
            if days_diff <= 7:
                return 100 - (days_diff * 5)  # 最新的接近100分
            elif days_diff <= 30:
                return 70 - ((days_diff - 7) * 1.5)  # 一个月内递减
            else:
                return max(10, 40 - ((days_diff - 30) * 0.5))  # 更早的研报分数较低
        except Exception:
            return 50  # 出错时返回默认分数
    
    def calculate_industry_score(self, report_industry, preferred_industries):
        """计算行业匹配分数"""
        if not preferred_industries or not report_industry:
            return 50  # 没有偏好设置时返回中等分数
        
        # 检查是否在偏好行业列表中
        if report_industry in preferred_industries:
            return 100
        
        # 部分匹配检查
        for industry in preferred_industries:
            if industry in report_industry or report_industry in industry:
                return 75
        
        return 30  # 不匹配偏好行业
    
    def get_recommendations(self, user_id=1, limit=5):
        """获取推荐研报列表，考虑用户阅读历史"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='recommendation_settings'")
        if not cursor.fetchone():
            # 如果表不存在，返回空列表
            conn.close()
            print("警告: recommendation_settings表不存在，请先运行数据库迁移脚本")
            return []
            
        # 获取用户设置
        settings = self.get_user_settings(user_id)
        
        # 检查用户偏好设置表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_preferences'")
        user_preferences_exists = cursor.fetchone() is not None
        
        # 检查阅读历史表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reading_history'")
        reading_history_exists = cursor.fetchone() is not None
        
        # 检查旧的read_records表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='read_records'")
        read_records_exists = cursor.fetchone() is not None
        
        # 获取用户阅读历史中的行业偏好
        industry_preferences = settings['preferred_industries']
        
        # 如果存在阅读历史表，分析用户的阅读偏好
        if reading_history_exists:
            # 获取用户最近阅读的行业分布
            cursor.execute('''
            SELECT r.industry, COUNT(*) as count
            FROM reading_history h
            JOIN reports r ON h.report_id = r.id
            WHERE h.user_id = ? AND r.industry IS NOT NULL AND r.industry != ''
            GROUP BY r.industry
            ORDER BY count DESC
            LIMIT 5
            ''', (user_id,))
            
            read_industries = cursor.fetchall()
            
            # 将用户经常阅读的行业添加到偏好中
            for row in read_industries:
                industry = row['industry']
                if industry and industry not in industry_preferences:
                    industry_preferences.append(industry)
        
        # 构建SQL查询
        # 优先获取未读研报
        if reading_history_exists:
            query = '''
            SELECT r.id, r.title, r.industry, r.date, r.org, r.rating, r.abstract, 
                   r.content_preview, a.completeness_score
            FROM reports r
            LEFT JOIN report_analysis a ON r.id = a.report_id AND a.analyzer_type = 'deepseek'
            LEFT JOIN reading_history h ON r.id = h.report_id AND h.user_id = ?
            WHERE h.id IS NULL  -- 未读研报
            '''
            params = (user_id,)
        elif read_records_exists:
            # 兼容旧版的read_records表
            query = '''
            SELECT r.id, r.title, r.industry, r.date, r.org, r.rating, r.abstract, 
                   r.content_preview, a.completeness_score
            FROM reports r
            LEFT JOIN report_analysis a ON r.id = a.report_id AND a.analyzer_type = 'deepseek'
            LEFT JOIN read_records rr ON r.id = rr.report_id AND rr.user_id = ?
            WHERE rr.id IS NULL  -- 未读研报
            '''
            params = (user_id,)
        else:
            # 如果没有阅读历史表，获取所有研报
            query = '''
            SELECT r.id, r.title, r.industry, r.date, r.org, r.rating, r.abstract, 
                   r.content_preview, a.completeness_score
            FROM reports r
            LEFT JOIN report_analysis a ON r.id = a.report_id AND a.analyzer_type = 'deepseek'
            '''
            params = ()
            print("警告: 阅读历史表不存在，将显示所有研报")
        
        cursor.execute(query, params)
        
        reports = []
        for row in cursor.fetchall():
            report = dict(row)
            
            # 计算五步法评分分数 (0-100)
            analysis_score = report['completeness_score'] if report['completeness_score'] else 50
            
            # 计算时间新鲜度分数 (0-100)
            time_score = self.calculate_time_score(report['date'])
            
            # 计算行业匹配分数 (0-100)
            industry_score = self.calculate_industry_score(
                report['industry'], 
                industry_preferences
            )
            
            # 计算阅读历史相关性分数
            history_score = 50  # 默认中等分数
            
            # 如果存在阅读历史，分析相关性
            if reading_history_exists:
                # 获取用户阅读过的相似研报数量
                if report['industry']:
                    cursor.execute('''
                    SELECT COUNT(*) as count
                    FROM reading_history h
                    JOIN reports r ON h.report_id = r.id
                    WHERE h.user_id = ? AND r.industry = ?
                    ''', (user_id, report['industry']))
                    
                    similar_count = cursor.fetchone()['count']
                    
                    # 根据相似研报阅读量调整分数
                    if similar_count > 10:
                        history_score = 100  # 用户非常喜欢这个行业
                    elif similar_count > 5:
                        history_score = 85  # 用户比较喜欢这个行业
                    elif similar_count > 2:
                        history_score = 70  # 用户有一定兴趣
                    elif similar_count > 0:
                        history_score = 60  # 用户略有兴趣
            
            # 计算总推荐分数，加入历史相关性因素
            recommendation_score = (
                (analysis_score * settings['weight_score'] / 100) +
                (time_score * settings['weight_time'] / 100) +
                (industry_score * settings['weight_industry'] / 100) +
                (history_score * 0.2)  # 历史相关性额外加权20%
            )
            
            report['recommendation_score'] = round(recommendation_score, 2)
            reports.append(report)
        
        conn.close()
        
        # 按推荐分数排序
        reports.sort(key=lambda x: x['recommendation_score'], reverse=True)
        
        # 返回前N条推荐
        return reports[:limit]
    
    def mark_as_read(self, report_id, user_id=1, status='read'):
        """标记研报为已读，同时更新阅读历史"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 检查旧的read_records表是否存在
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='read_records'")
            if not cursor.fetchone():
                # 如果表不存在，创建表
                cursor.execute('''
                CREATE TABLE read_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER DEFAULT 1,
                    report_id INTEGER NOT NULL,
                    read_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    read_status TEXT DEFAULT 'read',
                    FOREIGN KEY (report_id) REFERENCES reports(id),
                    UNIQUE(user_id, report_id)
                )
                ''')
                print("已创建read_records表")
            
            # 更新旧的read_records表
            cursor.execute('''
            INSERT OR REPLACE INTO read_records (user_id, report_id, read_status, read_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (user_id, report_id, status))
            
            # 检查新的reading_history表是否存在
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reading_history'")
            if cursor.fetchone():
                # 检查用户的隐私设置是否允许收集阅读历史
                collect_history = True
                
                # 检查user_preferences表是否存在
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_preferences'")
                if cursor.fetchone():
                    # 获取用户隐私设置
                    cursor.execute('''
                    SELECT preference_data FROM user_preferences 
                    WHERE user_id = ? AND preference_type = 'privacy'
                    ''', (user_id,))
                    
                    privacy_data = cursor.fetchone()
                    if privacy_data:
                        try:
                            import json
                            privacy_settings = json.loads(privacy_data[0])
                            collect_history = privacy_settings.get('collect_reading_history', True)
                        except:
                            pass
                
                # 如果用户允许收集阅读历史，则更新reading_history表
                if collect_history:
                    # 检查是否已有记录
                    cursor.execute('''
                    SELECT id, read_duration, is_completed FROM reading_history 
                    WHERE user_id = ? AND report_id = ?
                    ''', (user_id, report_id))
                    
                    existing = cursor.fetchone()
                    
                    if existing:
                        # 更新现有记录
                        is_completed = 1 if status == 'read' else 0
                        
                        # 更新阅读时间、完成状态和阅读时长（如果当前时长为0）
                        if existing[1] == 0:  # 如果当前阅读时长为0
                            read_duration = 180  # 设置默认阅读时长为3分钟
                        else:
                            read_duration = existing[1]  # 保持原有阅读时长
                            
                        cursor.execute('''
                        UPDATE reading_history 
                        SET read_at = CURRENT_TIMESTAMP, 
                            is_completed = ?,
                            read_duration = ?
                        WHERE id = ?
                        ''', (is_completed, read_duration, existing[0]))
                    else:
                        # 插入新记录
                        is_completed = 1 if status == 'read' else 0
                        
                        cursor.execute('''
                        INSERT INTO reading_history (user_id, report_id, read_duration, is_completed)
                        VALUES (?, ?, ?, ?)
                        ''', (user_id, report_id, 0, is_completed))
            
            conn.commit()
            success = True
        except Exception as e:
            conn.rollback()
            print(f"标记已读状态失败: {str(e)}")
            success = False
        finally:
            conn.close()
            
        return success
    
    def update_user_preferences(self, user_id=1, **preferences):
        """更新用户偏好设置"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 检查表是否存在
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='recommendation_settings'")
            if not cursor.fetchone():
                # 如果表不存在，创建表
                cursor.execute('''
                CREATE TABLE recommendation_settings (
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
                # 添加默认设置
                cursor.execute('''
                INSERT INTO recommendation_settings 
                (user_id, weight_score, weight_time, weight_industry, preferred_industries)
                VALUES (1, 40, 30, 30, '')
                ''')
                print("已创建recommendation_settings表并添加默认设置")
            
            # 构建更新语句
            update_fields = []
            params = []
            
            if 'weight_score' in preferences:
                update_fields.append('weight_score = ?')
                params.append(preferences['weight_score'])
                
            if 'weight_time' in preferences:
                update_fields.append('weight_time = ?')
                params.append(preferences['weight_time'])
                
            if 'weight_industry' in preferences:
                update_fields.append('weight_industry = ?')
                params.append(preferences['weight_industry'])
                
            if 'preferred_industries' in preferences:
                industries = ','.join(preferences['preferred_industries'])
                update_fields.append('preferred_industries = ?')
                params.append(industries)
            
            if update_fields:
                update_fields.append('updated_at = CURRENT_TIMESTAMP')
                
                query = f'''
                UPDATE recommendation_settings 
                SET {', '.join(update_fields)}
                WHERE user_id = ?
                '''
                
                params.append(user_id)
                cursor.execute(query, params)
                
                conn.commit()
                success = True
            else:
                success = False
                
        except Exception as e:
            conn.rollback()
            print(f"更新用户偏好失败: {str(e)}")
            success = False
        finally:
            conn.close()
            
        return success
    
    def check_is_read(self, report_id, user_id=1):
        """检查研报是否已读，同时检查新旧两个表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        is_read = False
        
        # 检查新的reading_history表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reading_history'")
        if cursor.fetchone():
            cursor.execute('''
            SELECT id FROM reading_history 
            WHERE user_id = ? AND report_id = ?
            ''', (user_id, report_id))
            
            if cursor.fetchone():
                is_read = True
        
        # 如果新表中没有找到记录，检查旧的read_records表
        if not is_read:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='read_records'")
            if cursor.fetchone():
                cursor.execute('''
                SELECT id FROM read_records 
                WHERE user_id = ? AND report_id = ?
                ''', (user_id, report_id))
                
                if cursor.fetchone():
                    is_read = True
        
        conn.close()
        return is_read