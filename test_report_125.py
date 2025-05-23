#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
from deepseek_analyzer import DeepSeekAnalyzer

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

def main():
    # 获取ID为125的研报
    report = get_report_by_id(125)
    
    if not report:
        print("未找到ID为125的研报")
        return
    
    print(f"开始分析研报: {report['title']}")
    print(f"行业: {report['industry']}")
    print(f"内容长度: {len(report['content'])}")
    
    # 初始化分析器并分析研报
    analyzer = DeepSeekAnalyzer()
    analysis_result = analyzer.analyze_with_five_steps(report['title'], report['content'], report['industry'])
    
    # 打印分析结果
    print("\n===== 分析结果 =====")
    print(f"完整度评分: {analysis_result['analysis']['summary']['completeness_score']}")
    print(f"总体评价: {analysis_result['analysis']['summary']['evaluation']}")
    
    print("\n各步骤分析:")
    steps = ["信息", "逻辑", "超预期", "催化剂", "结论"]
    for step in steps:
        print(f"\n--- {step} ---")
        print(f"描述: {analysis_result['analysis'][step]['description']}")
        print(f"评分: {analysis_result['analysis'][step]['step_score']}")
    
    # 打印一句话总结（如果存在）
    if 'one_line_summary' in analysis_result['analysis']['summary']:
        print("\n一句话总结:")
        print(analysis_result['analysis']['summary']['one_line_summary'])
    
    # 打印完整分析文本
    print("\n===== 完整分析文本 =====")
    print(analysis_result['full_analysis'])

if __name__ == "__main__":
    main() 