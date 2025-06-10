#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
from datetime import datetime, timedelta
import json
import math
from preference_manager import PreferenceManager # 引入新的偏好管理器

class RecommendationEngine:
    """研报推荐引擎"""
    
    def __init__(self, db_path='research_reports.db'):
        """初始化推荐引擎"""
        self.db_path = db_path
        self.preference_manager = PreferenceManager(db_path) # 实例化偏好管理器
    
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

    def _calculate_preference_score(self, report, preferences):
        """计算基于用户偏好的额外分数"""
        score = 0
        
        # 1. 专注行业匹配
        if report.get('industry') and preferences.get('focused_industries'):
            if report['industry'] in preferences['focused_industries']:
                score += 50  # 命中专注行业，给予高加分

        # 2. 关注机构匹配
        if report.get('org') and preferences.get('followed_organizations'):
            if report['org'] in preferences['followed_organizations']:
                score += 30 # 命中关注机构，给予中等加分
        
        # 3. 报告类型匹配 (未来可扩展)
        # report_type = self._infer_report_type(report.get('title'))
        # if report_type and preferences.get('preferred_report_types'):
        #     if report_type in preferences['preferred_report_types']:
        #         score += 20
                
        return score

    def get_recommendations(self, user_id=1, limit=5):
        """获取推荐研报列表，考虑用户偏好和阅读历史"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 1. 获取用户的所有推荐偏好设置
        try:
            settings = self.preference_manager.get_user_preferences(user_id, 'recommendation')
        except Exception as e:
            print(f"获取用户偏好失败: {e}, 将使用默认设置。")
            settings = self.preference_manager._get_default_preferences('recommendation')

        # 2. 获取该用户已读的报告ID列表
        read_report_ids = set()
        try:
            history = self.preference_manager.get_reading_history(user_id, limit=500) # 获取最近500条
            read_report_ids = {item['report_id'] for item in history}
        except Exception as e:
            print(f"获取阅读历史失败: {e}")

        # 3. 从数据库获取所有报告（或近期报告）
        # 为了性能，可以只取最近几个月的报告进行推荐
        two_months_ago = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')
        cursor.execute('''
        SELECT r.id, r.title, r.industry, r.date, r.org, r.rating, a.completeness_score
        FROM reports r
        LEFT JOIN report_analysis a ON r.id = a.report_id AND a.analyzer_type = 'deepseek'
        WHERE r.date >= ? 
        ''', (two_months_ago,))
        
        all_reports = cursor.fetchall()
        conn.close()

        # 4. 计算每个报告的分数
        scored_reports = []
        for report_row in all_reports:
            report = dict(report_row)
            
            # 如果报告已读，则跳过
            if report['id'] in read_report_ids:
                continue

            # 计算基础分数
            analysis_score = report['completeness_score'] if report['completeness_score'] is not None else 50
            time_score = self.calculate_time_score(report['date'])
            
            # 使用权重计算基础分
            base_score = (
                (analysis_score * settings.get('weight_score', 40) / 100) +
                (time_score * settings.get('weight_time', 30) / 100)
            )
            
            # 计算偏好分数
            preference_score = self._calculate_preference_score(report, settings)
            
            # 总分 = 基础分 + 偏好分
            total_score = base_score + preference_score
            
            report['recommendation_score'] = round(total_score, 2)
            scored_reports.append(report)
        
        # 5. 按最终分数排序
        scored_reports.sort(key=lambda x: x['recommendation_score'], reverse=True)
        
        return scored_reports[:limit]
    
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