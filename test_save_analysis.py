#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
from deepseek_analyzer import DeepSeekAnalyzer
from analysis_db import AnalysisDatabase

def get_report_by_id(report_id):
    """从数据库获取指定ID的研报信息"""
    conn = sqlite3.connect('research_reports.db')
    cursor = conn.cursor()
    cursor.execute('SELECT title, full_content, industry FROM reports WHERE id = ?', (report_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            'title': result[0],
            'content': result[1],
            'industry': result[2]
        }
    return None

def analyze_and_save_report(report_id):
    """分析研报并将结果保存到数据库"""
    # 1. 获取研报内容
    report = get_report_by_id(report_id)
    if not report:
        print(f"未找到ID为{report_id}的研报")
        return
    
    print(f"开始分析研报: {report['title']}")
    print(f"行业: {report['industry']}")
    print(f"内容长度: {len(report['content'])}")
    
    # 2. 使用DeepSeek分析器进行分析
    analyzer = DeepSeekAnalyzer()
    analysis_result = analyzer.analyze_with_five_steps(report['title'], report['content'], report['industry'])
    
    # 3. 将分析结果保存到数据库
    db = AnalysisDatabase()
    analysis_id = db.save_analysis_result(report_id, analysis_result, analyzer_type='deepseek')
    
    print(f"分析结果已保存到数据库，分析ID: {analysis_id}")
    
    # 4. 从数据库读取并验证分析结果
    saved_result = db.get_analysis_by_report_id(report_id, analyzer_type='deepseek')
    if saved_result:
        print("\n===== 从数据库读取的分析结果 =====")
        print(f"完整度评分: {saved_result['completeness_score']}")
        print(f"总体评价: {saved_result['evaluation']}")
        print(f"一句话总结: {saved_result['one_line_summary']}")
        
        print("\n各步骤分析:")
        for step_name, step_data in saved_result['steps'].items():
            print(f"\n--- {step_name} ---")
            print(f"描述: {step_data['description']}")
            print(f"评分: {step_data['step_score']}")
        
        print("\n改进建议:")
        for suggestion in saved_result['improvement_suggestions']:
            print(f"- {suggestion['point']}: {suggestion['suggestion']}")
    else:
        print("无法从数据库读取分析结果")

if __name__ == "__main__":
    # 分析ID为125的研报
    analyze_and_save_report(125) 