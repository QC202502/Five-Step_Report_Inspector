#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import json
import re
from typing import Dict, List, Any, Optional, Tuple

class AnalysisDatabase:
    """处理研报分析结果的数据库操作"""
    
    def __init__(self, db_path: str = 'research_reports.db'):
        """初始化数据库连接"""
        self.db_path = db_path
        self._ensure_tables_exist()
    
    def _ensure_tables_exist(self):
        """确保所有必要的表都存在"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建研报分析结果表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS report_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER NOT NULL,
            analyzer_type TEXT NOT NULL,
            completeness_score INTEGER NOT NULL,
            evaluation TEXT NOT NULL,
            one_line_summary TEXT,
            full_analysis TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE
        )
        ''')
        
        # 创建五步法各步骤分析结果表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS step_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            analysis_id INTEGER NOT NULL,
            step_name TEXT NOT NULL,
            found BOOLEAN NOT NULL,
            description TEXT,
            step_score INTEGER NOT NULL,
            framework_summary TEXT,
            FOREIGN KEY (analysis_id) REFERENCES report_analysis(id) ON DELETE CASCADE
        )
        ''')
        
        # 创建改进建议表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS improvement_suggestions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            analysis_id INTEGER NOT NULL,
            point TEXT NOT NULL,
            suggestion TEXT NOT NULL,
            FOREIGN KEY (analysis_id) REFERENCES report_analysis(id) ON DELETE CASCADE
        )
        ''')
        
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
            # 1. 插入主分析记录
            completeness_score = analysis_result['analysis']['summary']['completeness_score']
            evaluation = analysis_result['analysis']['summary']['evaluation']
            one_line_summary = analysis_result['analysis']['summary'].get('one_line_summary', '')
            full_analysis = analysis_result['full_analysis']
            
            cursor.execute('''
            INSERT INTO report_analysis 
            (report_id, analyzer_type, completeness_score, evaluation, one_line_summary, full_analysis)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (report_id, analyzer_type, completeness_score, evaluation, one_line_summary, full_analysis))
            
            analysis_id = cursor.lastrowid
            
            # 2. 插入各步骤分析结果
            steps = ["信息", "逻辑", "超预期", "催化剂", "结论"]
            for step in steps:
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
            
            # 3. 解析并插入改进建议
            self._parse_and_save_suggestions(cursor, analysis_id, analysis_result)
            
            conn.commit()
            return analysis_id
            
        except Exception as e:
            conn.rollback()
            print(f"保存分析结果时出错: {str(e)}")
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
                    if point and suggestion:
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
                        if point and suggestion:
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
            print(f"获取分析结果时出错: {str(e)}")
            return None
        finally:
            conn.close()

# 测试代码
if __name__ == "__main__":
    db = AnalysisDatabase()
    print("分析数据库初始化完成") 