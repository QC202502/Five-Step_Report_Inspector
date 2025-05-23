#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库结构更新脚本
用于更新现有数据库以支持完整的研报分析内容存储
"""

import sqlite3
import json
import os
import re
import time
from datetime import datetime

# 数据库文件名
DB_FILE = 'research_reports.db'
JSON_FILE = 'research_reports.json'

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def update_database_schema():
    """更新数据库架构，添加新表和字段"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # 检查 analysis_results 表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='analysis_results'")
        if cursor.fetchone() is None:
            print("analysis_results 表不存在，请先运行 init_db() 初始化数据库")
            return False
        
        # 添加新字段到 analysis_results 表
        try:
            cursor.execute('ALTER TABLE analysis_results ADD COLUMN framework_summary TEXT;')
            print("成功添加 framework_summary 字段")
        except sqlite3.OperationalError:
            print("framework_summary 字段可能已存在")
        
        try:
            cursor.execute('ALTER TABLE analysis_results ADD COLUMN improvement_suggestions TEXT;')
            print("成功添加 improvement_suggestions 字段")
        except sqlite3.OperationalError:
            print("improvement_suggestions 字段可能已存在")
        
        try:
            cursor.execute('ALTER TABLE analysis_results ADD COLUMN step_score INTEGER;')
            print("成功添加 step_score 字段")
        except sqlite3.OperationalError:
            print("step_score 字段可能已存在")
        
        # 创建 report_full_analysis 表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS report_full_analysis (
            report_id INTEGER PRIMARY KEY,
            full_analysis_text TEXT,
            one_line_summary TEXT,
            FOREIGN KEY (report_id) REFERENCES reports (id)
        );
        ''')
        print("成功创建或确认 report_full_analysis 表")
        
        conn.commit()
        print("数据库架构更新成功")
        return True
    except Exception as e:
        print(f"更新数据库架构时出错: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def extract_analysis_components(full_analysis):
    """从完整分析文本中提取各个组成部分"""
    result = {
        "framework_summaries": {},
        "improvement_suggestions": "",
        "one_line_summary": ""
    }
    
    if not full_analysis:
        return result
    
    try:
        # 提取框架梳理部分
        framework_section_match = re.search(r'## 五步框架梳理(.*?)##', full_analysis, re.DOTALL)
        if framework_section_match:
            framework_section = framework_section_match.group(1)
            steps_mapping = {
                'Information': '信息',
                'Logic': '逻辑',
                'Beyond-Consensus': '超预期',
                'Catalyst': '催化剂',
                'Conclusion': '结论'
            }
            
            for eng_name, cn_name in steps_mapping.items():
                pattern = r'\| ' + re.escape(eng_name) + r' \|(.*?)\|'
                match = re.search(pattern, framework_section, re.DOTALL)
                if match:
                    result["framework_summaries"][cn_name] = match.group(1).strip()
        
        # 提取可操作补强思路部分
        suggestions_match = re.search(r'## 可操作补强思路(.*?)##', full_analysis, re.DOTALL)
        if suggestions_match:
            result["improvement_suggestions"] = suggestions_match.group(1).strip()
        
        # 提取一句话总结
        summary_match = re.search(r'## 一句话总结(.*?)##', full_analysis, re.DOTALL)
        if summary_match:
            result["one_line_summary"] = summary_match.group(1).strip()
        
    except Exception as e:
        print(f"从完整分析中提取组件时出错: {e}")
    
    return result

def update_from_json():
    """从 JSON 文件中更新数据库的分析内容"""
    if not os.path.exists(JSON_FILE):
        print(f"文件 {JSON_FILE} 不存在")
        return False
    
    try:
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            reports = json.load(f)
        
        if not reports:
            print("JSON 文件中没有找到研报数据")
            return False
        
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            updated_count = 0
            
            for report in reports:
                # 查找报告在数据库中的 ID
                try:
                    cursor.execute('SELECT id FROM reports WHERE link = ?', (report.get('link', ''),))
                    result = cursor.fetchone()
                    if not result:
                        print(f"未找到链接为 {report.get('link')} 的报告")
                        continue
                    
                    report_id = result['id']
                    
                    # 获取完整分析文本
                    full_analysis = report.get('full_analysis', '')
                    
                    # 如果没有完整分析文本，尝试从 analysis 中的 full_analysis 字段获取
                    if not full_analysis and 'analysis' in report:
                        full_analysis = report.get('analysis', {}).get('full_analysis', '')
                    
                    # 从完整分析文本中提取各个组件
                    components = extract_analysis_components(full_analysis)
                    
                    # 更新 report_full_analysis 表
                    one_line_summary = components["one_line_summary"]
                    if not one_line_summary and 'analysis' in report:
                        one_line_summary = report.get('analysis', {}).get('summary', {}).get('one_line_summary', '')
                    
                    cursor.execute('''
                    INSERT OR REPLACE INTO report_full_analysis (report_id, full_analysis_text, one_line_summary)
                    VALUES (?, ?, ?)
                    ''', (report_id, full_analysis, one_line_summary))
                    
                    # 更新 analysis_results 表中的各个步骤
                    for step in ['信息', '逻辑', '超预期', '催化剂', '结论']:
                        if step in components["framework_summaries"]:
                            framework_summary = components["framework_summaries"][step]
                            # 更新框架摘要
                            cursor.execute('''
                            UPDATE analysis_results 
                            SET framework_summary = ? 
                            WHERE report_id = ? AND step_name = ?
                            ''', (framework_summary, report_id, step))
                        
                        # 如果是结论步骤，还要更新改进建议
                        if step == '结论' and components["improvement_suggestions"]:
                            cursor.execute('''
                            UPDATE analysis_results 
                            SET improvement_suggestions = ? 
                            WHERE report_id = ? AND step_name = ?
                            ''', (components["improvement_suggestions"], report_id, step))
                        
                        # 更新步骤评分
                        if 'analysis' in report and step in report['analysis']:
                            step_score = report['analysis'][step].get('step_score', 0)
                            # 确保 step_score 不为 None
                            if step_score is not None and step_score > 0:
                                cursor.execute('''
                                UPDATE analysis_results 
                                SET step_score = ? 
                                WHERE report_id = ? AND step_name = ?
                                ''', (step_score, report_id, step))
                    
                    updated_count += 1
                except Exception as e:
                    print(f"更新报告 {report.get('title', 'unknown')} 时出错: {e}")
                    continue
            
            conn.commit()
            print(f"成功从 JSON 更新了 {updated_count} 条研报的分析内容")
            return True
        except Exception as e:
            print(f"从 JSON 更新数据库时出错: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    except Exception as e:
        print(f"读取 JSON 文件时出错: {e}")
        return False

if __name__ == "__main__":
    print("开始更新数据库架构...")
    if update_database_schema():
        print("\n开始从 JSON 文件更新分析内容...")
        update_from_json()
    print("\n数据库更新完成!") 