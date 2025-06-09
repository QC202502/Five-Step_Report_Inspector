#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import json
import re
from typing import Dict, List, Any, Optional, Tuple
import logging
import datetime

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AnalysisDatabase:
    """处理研报分析结果的数据库操作"""
    
    def __init__(self, db_path: str = 'research_reports.db'):
        """初始化数据库连接"""
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='report_video_scripts'")
        video_scripts_exists = cursor.fetchone() is not None
        
        # 创建存储分析结果的表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS report_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER NOT NULL,
            analyzer_type TEXT NOT NULL,
            completeness_score INTEGER DEFAULT 0,
            evaluation TEXT,
            one_line_summary TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(report_id, analyzer_type)
        )
        ''')
        
        # 创建存储每个步骤分析结果的表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS analysis_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER NOT NULL,
            analyzer_type TEXT NOT NULL,
            step_name TEXT NOT NULL,
            found BOOLEAN DEFAULT 0,
            keywords TEXT,
            evidence TEXT,
            description TEXT,
            framework_summary TEXT,
            improvement_suggestions TEXT,
            step_score INTEGER DEFAULT 0,
            UNIQUE(report_id, analyzer_type, step_name)
        )
        ''')
        
        # 创建存储完整分析文本的表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS report_full_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER NOT NULL,
            analyzer_type TEXT NOT NULL,
            full_text TEXT,
            UNIQUE(report_id, analyzer_type)
        )
        ''')
        
        # 仅当表不存在时创建视频文案表
        if not video_scripts_exists:
            try:
                cursor.execute('''
                CREATE TABLE report_video_scripts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_id INTEGER NOT NULL,
                    script_text TEXT,
                    created_at TEXT NOT NULL,
                    UNIQUE(report_id)
                )
                ''')
                print("成功创建视频文案表")
            except sqlite3.OperationalError as e:
                # 表可能已存在
                print(f"创建视频文案表时出现信息（可能表已存在）: {str(e)}")
        
        conn.commit()
        conn.close()
    
    def save_analysis_result(self, report_id: int, analysis_result: Dict[str, Any], analyzer_type: str = 'deepseek') -> int:
        """
        将分析结果保存到数据库
        
        Parameters:
        -----------
        report_id : int
            研报ID
        analysis_result : Dict[str, Any]
            分析结果字典
        analyzer_type : str
            分析器类型，默认为'deepseek'
            
        Returns:
        --------
        int
            新插入的分析记录ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 1. 检查是否已存在相同类型的分析，如果存在则更新
            cursor.execute('''
            SELECT id FROM report_analysis 
            WHERE report_id = ? AND analyzer_type = ?
            ''', (report_id, analyzer_type))
            
            existing_analysis = cursor.fetchone()
            
            # 2. 准备分析数据
            completeness_score = analysis_result['analysis']['summary']['completeness_score']
            evaluation = analysis_result['analysis']['summary']['evaluation']
            one_line_summary = analysis_result['analysis']['summary'].get('one_line_summary', '')
            full_analysis = analysis_result['full_analysis']
            
            if existing_analysis:
                # 更新现有分析
                analysis_id = existing_analysis[0]
                cursor.execute('''
                UPDATE report_analysis 
                SET completeness_score = ?, evaluation = ?, one_line_summary = ?, full_analysis = ?,
                    created_at = CURRENT_TIMESTAMP
                WHERE id = ?
                ''', (completeness_score, evaluation, one_line_summary, full_analysis, analysis_id))
                
                # 删除旧的步骤分析和改进建议
                cursor.execute('DELETE FROM step_analysis WHERE analysis_id = ?', (analysis_id,))
                cursor.execute('DELETE FROM improvement_suggestions WHERE analysis_id = ?', (analysis_id,))
                
                logger.info(f"更新研报ID {report_id} 的 {analyzer_type} 分析")
            else:
                # 插入新分析
                cursor.execute('''
                INSERT INTO report_analysis 
                (report_id, analyzer_type, completeness_score, evaluation, one_line_summary, full_analysis)
                VALUES (?, ?, ?, ?, ?, ?)
                ''', (report_id, analyzer_type, completeness_score, evaluation, one_line_summary, full_analysis))
                
                analysis_id = cursor.lastrowid
                logger.info(f"为研报ID {report_id} 创建新的 {analyzer_type} 分析")
            
            # 3. 插入各步骤分析结果
            steps = ["信息", "逻辑", "超预期", "催化剂", "结论"]
            for step in steps:
                if step in analysis_result['analysis']:
                    step_data = analysis_result['analysis'][step]
                    found = step_data.get('found', False)
                    description = step_data.get('description', '')
                    step_score = step_data.get('step_score', 0)
                    framework_summary = step_data.get('framework_summary', '')
                    
                    cursor.execute('''
                    INSERT INTO step_analysis
                    (analysis_id, step_name, found, description, step_score, framework_summary)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ''', (analysis_id, step, found, description, step_score, framework_summary))
            
            # 4. 解析并插入改进建议
            self._parse_and_save_suggestions(cursor, analysis_id, analysis_result)
            
            # 5. 更新reports表中的completeness_score和analysis_method字段
            cursor.execute('''
            UPDATE reports
            SET completeness_score = ?, analysis_method = ?
            WHERE id = ?
            ''', (completeness_score, analyzer_type, report_id))
            
            conn.commit()
            return analysis_id
            
        except Exception as e:
            conn.rollback()
            logger.error(f"保存分析结果时出错: {str(e)}")
            raise
        finally:
            conn.close()
    
    def _parse_and_save_suggestions(self, cursor, analysis_id: int, analysis_result: Dict[str, Any]):
        """解析并保存改进建议"""
        # 检查是否有改进建议部分
        if 'improvement_suggestions' in analysis_result['analysis']:
            suggestions_text = analysis_result['analysis']['improvement_suggestions']
            
            # 尝试从文本中提取改进建议
            suggestions = self._extract_suggestions_from_text(suggestions_text)
            
            # 如果无法提取，尝试从完整分析文本中提取
            if not suggestions and 'full_analysis' in analysis_result:
                full_text = analysis_result['full_analysis']
                suggestions_section = re.search(r'## 可操作补强思路(.*?)##', full_text, re.DOTALL)
                if suggestions_section:
                    suggestions_text = suggestions_section.group(1).strip()
                    suggestions = self._extract_suggestions_from_text(suggestions_text)
            
            # 保存提取到的建议
            for point, suggestion in suggestions:
                cursor.execute('''
                INSERT INTO improvement_suggestions (analysis_id, point, suggestion)
                VALUES (?, ?, ?)
                ''', (analysis_id, point, suggestion))
    
    def _extract_suggestions_from_text(self, text: str) -> List[Tuple[str, str]]:
        """从文本中提取改进建议"""
        suggestions = []
        
        # 尝试解析表格格式
        table_rows = re.findall(r'\|(.*?)\|(.*?)\|', text)
        if table_rows:
            for row in table_rows:
                if len(row) >= 2 and not ('待完善点' in row[0] and '建议' in row[1]):
                    point = row[0].strip()
                    suggestion = row[1].strip()
                    
                    # 处理<br>标签，确保它们正确显示
                    suggestion = suggestion.replace('<br>', '<br />')
                    
                    # 验证提取的建议是否有效
                    if (point and suggestion and 
                        point != '-------' and suggestion != '----' and
                        len(point) > 1 and len(suggestion) > 1):
                        suggestions.append((point, suggestion))
        
        # 如果没有找到表格格式，尝试解析其他格式
        if not suggestions:
            # 尝试解析列表格式
            list_items = re.findall(r'- (.*?)[:：](.*?)(?:\n|$)', text)
            if list_items:
                for item in list_items:
                    if len(item) >= 2:
                        point = item[0].strip()
                        suggestion = item[1].strip()
                        
                        # 处理<br>标签，确保它们正确显示
                        suggestion = suggestion.replace('<br>', '<br />')
                        
                        # 验证提取的建议是否有效
                        if (point and suggestion and 
                            point != '-------' and suggestion != '----' and
                            len(point) > 1 and len(suggestion) > 1):
                            suggestions.append((point, suggestion))
        
        return suggestions
    
    def get_analysis_by_report_id(self, report_id: int, analyzer_type: str = None) -> Optional[Dict[str, Any]]:
        """
        根据研报ID获取分析结果
        
        Parameters:
        -----------
        report_id : int
            研报ID
        analyzer_type : str, optional
            分析器类型，如果不指定则返回最新的分析结果
            
        Returns:
        --------
        Dict[str, Any] or None
            分析结果字典，如果没有找到则返回None
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            # 构建查询
            query = '''
            SELECT * FROM report_analysis 
            WHERE report_id = ?
            '''
            params = [report_id]
            
            if analyzer_type:
                query += ' AND analyzer_type = ?'
                params.append(analyzer_type)
            
            query += ' ORDER BY created_at DESC LIMIT 1'
            
            # 执行查询
            cursor.execute(query, params)
            analysis_row = cursor.fetchone()
            
            if not analysis_row:
                # 如果没有找到分析结果，先检查是否有任何类型的分析结果
                if analyzer_type:
                    cursor.execute('''
                    SELECT * FROM report_analysis 
                    WHERE report_id = ?
                    ORDER BY created_at DESC LIMIT 1
                    ''', [report_id])
                    any_analysis = cursor.fetchone()
                    
                    if any_analysis:
                        # 找到其他类型的分析结果，使用它替代
                        logger.info(f"研报ID {report_id} 没有找到 {analyzer_type} 分析结果，使用其他类型的分析结果替代")
                        analysis_row = any_analysis
                    else:
                        return None
                else:
                    return None
            
            # 将行转换为字典
            analysis = dict(analysis_row)
            analysis_id = analysis['id']
            
            # 获取步骤分析
            cursor.execute('''
            SELECT * FROM step_analysis
            WHERE analysis_id = ?
            ''', (analysis_id,))
            
            steps = {}
            for step_row in cursor.fetchall():
                step_dict = dict(step_row)
                step_name = step_dict['step_name']
                steps[step_name] = {
                    'found': bool(step_dict['found']),
                    'description': step_dict['description'],
                    'step_score': step_dict['step_score'],
                    'framework_summary': step_dict['framework_summary']
                }
            
            # 获取改进建议
            cursor.execute('''
            SELECT point, suggestion FROM improvement_suggestions
            WHERE analysis_id = ?
            ''', (analysis_id,))
            
            suggestions = []
            for suggestion_row in cursor.fetchall():
                suggestions.append({
                    'point': suggestion_row['point'],
                    'suggestion': suggestion_row['suggestion']
                })
            
            # 构建完整的结果字典
            result = {
                'id': analysis['id'],
                'report_id': analysis['report_id'],
                'analyzer_type': analysis['analyzer_type'],
                'completeness_score': analysis['completeness_score'],
                'evaluation': analysis['evaluation'],
                'one_line_summary': analysis['one_line_summary'],
                'full_analysis': analysis['full_analysis'],
                'created_at': analysis['created_at'],
                'steps': steps,
                'improvement_suggestions': suggestions
            }
            
            return result
            
        except Exception as e:
            logger.error(f"获取分析结果时出错: {str(e)}")
            return None
        finally:
            conn.close()
    
    def delete_analysis(self, analysis_id: int) -> bool:
        """
        删除指定的分析记录
        
        Parameters:
        -----------
        analysis_id : int
            分析记录ID
            
        Returns:
        --------
        bool
            删除是否成功
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            
            # 删除步骤分析
            cursor.execute('DELETE FROM step_analysis WHERE analysis_id = ?', (analysis_id,))
            
            # 删除改进建议
            cursor.execute('DELETE FROM improvement_suggestions WHERE analysis_id = ?', (analysis_id,))
            
            # 删除主分析记录
            cursor.execute('DELETE FROM report_analysis WHERE id = ?', (analysis_id,))
            
            conn.commit()
            logger.info(f"已删除分析ID {analysis_id}")
            return True
        except Exception as e:
            conn.rollback()
            logger.error(f"删除分析记录时出错: {str(e)}")
            return False
        finally:
            conn.close()
    
    def get_all_analyses_for_report(self, report_id: int) -> List[Dict[str, Any]]:
        """
        获取研报的所有分析结果
        
        Parameters:
        -----------
        report_id : int
            研报ID
            
        Returns:
        --------
        List[Dict[str, Any]]
            分析结果列表
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            # 获取所有分析记录
            cursor.execute('''
            SELECT id, analyzer_type, completeness_score, created_at
            FROM report_analysis
            WHERE report_id = ?
            ORDER BY created_at DESC
            ''', (report_id,))
            
            analyses = []
            for row in cursor.fetchall():
                analyses.append(dict(row))
            
            return analyses
        except Exception as e:
            logger.error(f"获取研报所有分析时出错: {str(e)}")
            return []
        finally:
            conn.close()

    def insert_report(self, title, link, industry, rating, org, date, content):
        """
        将研报信息插入到数据库中
        
        Parameters:
        -----------
        title : str
            研报标题
        link : str
            研报链接
        industry : str
            行业分类
        rating : str
            评级
        org : str
            发布机构
        date : str
            发布日期
        content : str
            研报内容
            
        Returns:
        --------
        int
            新插入的研报ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 插入研报信息
            cursor.execute('''
            INSERT INTO reports (title, link, industry, rating, org, date, full_content, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            ''', (title, link, industry, rating, org, date, content))
            
            report_id = cursor.lastrowid
            conn.commit()
            logger.info(f"插入新研报，ID: {report_id}, 标题: {title}")
            return report_id
            
        except Exception as e:
            conn.rollback()
            logger.error(f"插入研报时出错: {str(e)}")
            raise
        finally:
            conn.close()
    
    def insert_analysis(self, report_id, analyzer_type, analysis_json):
        """
        将分析结果插入到数据库中
        
        Parameters:
        -----------
        report_id : int
            研报ID
        analyzer_type : str
            分析器类型
        analysis_json : str
            JSON格式的分析结果
            
        Returns:
        --------
        int
            新插入的分析ID
        """
        try:
            # 解析JSON
            analysis_data = json.loads(analysis_json)
            
            # 调用现有的save_analysis_result方法
            analysis_id = self.save_analysis_result(report_id, analysis_data, analyzer_type)
            
            logger.info(f"插入新分析，ID: {analysis_id}, 研报ID: {report_id}")
            return analysis_id
            
        except json.JSONDecodeError:
            logger.error("无法解析JSON格式的分析结果")
            raise
        except Exception as e:
            logger.error(f"插入分析结果时出错: {str(e)}")
            raise

    def save_video_script(self, report_id: int, script_text: str) -> int:
        """
        保存研报的视频文案
        
        Parameters:
        -----------
        report_id : int
            研报ID
        script_text : str
            生成的视频文案
            
        Returns:
        --------
        int
            新插入或更新的记录ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 检查是否已存在
            cursor.execute('''
            SELECT id FROM report_video_scripts 
            WHERE report_id = ?
            ''', (report_id,))
            
            existing_script = cursor.fetchone()
            
            if existing_script:
                # 更新现有记录
                cursor.execute('''
                UPDATE report_video_scripts
                SET script_text = ?, created_at = ?
                WHERE report_id = ?
                ''', (script_text, now, report_id))
                script_id = existing_script[0]
            else:
                # 插入新记录
                cursor.execute('''
                INSERT INTO report_video_scripts (report_id, script_text, created_at)
                VALUES (?, ?, ?)
                ''', (report_id, script_text, now))
                script_id = cursor.lastrowid
            
            conn.commit()
            return script_id
            
        except Exception as e:
            print(f"保存视频文案时出错: {str(e)}")
            conn.rollback()
            return 0
        finally:
            conn.close()
    
    def get_video_script(self, report_id: int) -> str:
        """
        获取研报的视频文案
        
        Parameters:
        -----------
        report_id : int
            研报ID
            
        Returns:
        --------
        str
            视频文案文本，如果不存在则返回空字符串
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            SELECT script_text FROM report_video_scripts 
            WHERE report_id = ?
            ''', (report_id,))
            
            result = cursor.fetchone()
            
            if result:
                return result[0]
            return ""
            
        except Exception as e:
            print(f"获取视频文案时出错: {str(e)}")
            return ""
        finally:
            conn.close()

# 测试代码
if __name__ == "__main__":
    db = AnalysisDatabase()
    logger.info("分析数据库初始化完成") 