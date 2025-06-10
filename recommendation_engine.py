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
        """获取推荐研报列表"""
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
        
        # 检查read_records表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='read_records'")
        read_records_exists = cursor.fetchone() is not None
        
        # 构建SQL查询
        if read_records_exists:
            # 获取所有未读研报
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
            # 如果read_records表不存在，获取所有研报
            query = '''
            SELECT r.id, r.title, r.industry, r.date, r.org, r.rating, r.abstract, 
                   r.content_preview, a.completeness_score
            FROM reports r
            LEFT JOIN report_analysis a ON r.id = a.report_id AND a.analyzer_type = 'deepseek'
            '''
            params = ()
            print("警告: read_records表不存在，将显示所有研报")
        
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
                settings['preferred_industries']
            )
            
            # 计算总推荐分数
            recommendation_score = (
                (analysis_score * settings['weight_score'] / 100) +
                (time_score * settings['weight_time'] / 100) +
                (industry_score * settings['weight_industry'] / 100)
            )
            
            report['recommendation_score'] = round(recommendation_score, 2)
            reports.append(report)
        
        conn.close()
        
        # 按推荐分数排序
        reports.sort(key=lambda x: x['recommendation_score'], reverse=True)
        
        # 返回前N条推荐
        return reports[:limit]
    
    def mark_as_read(self, report_id, user_id=1, status='read'):
        """标记研报为已读"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 检查表是否存在
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
            
            cursor.execute('''
            INSERT OR REPLACE INTO read_records (user_id, report_id, read_status, read_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (user_id, report_id, status))
            
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
        """检查研报是否已读"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='read_records'")
        if not cursor.fetchone():
            conn.close()
            return False
            
        cursor.execute('''
        SELECT id FROM read_records 
        WHERE user_id = ? AND report_id = ?
        ''', (user_id, report_id))
        
        result = cursor.fetchone()
        conn.close()
        
        return result is not None 