#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sqlite3
import json
from deepseek_analyzer import DeepSeekAnalyzer
from analysis_db import AnalysisDatabase

def main():
    """
    从数据库获取已有研报，使用DeepSeek分析器分析，并将结果存入数据库
    """
    # 设置 DeepSeek API 密钥
    # 注意：这里使用的是示例密钥，请替换为您自己的 DeepSeek API 密钥
    os.environ["DEEPSEEK_API_KEY"] = "YOUR_DEEPSEEK_API_KEY_HERE"  # 替换为您的实际 API 密钥
    
    print("开始测试使用DeepSeek分析已有研报...")
    
    # 连接数据库
    conn = sqlite3.connect('research_reports.db')
    cursor = conn.cursor()
    
    # 获取一条已有研报 (使用ID 172)
    report_id = 172
    cursor.execute('''
    SELECT id, title, full_content, industry FROM reports WHERE id = ?
    ''', (report_id,))
    
    report = cursor.fetchone()
    if not report:
        print(f"未找到ID为 {report_id} 的研报，请检查数据库")
        return
    
    report_id, title, content, industry = report
    
    print(f"已获取研报: {title}")
    print(f"行业: {industry}")
    print(f"内容长度: {len(content) if content else 0} 字符")
    
    try:
        # 使用DeepSeek分析器进行五步法分析
        analyzer = DeepSeekAnalyzer()
        analysis_result = analyzer.analyze_with_five_steps(title, content, industry)
        
        print("\n分析完成，结果摘要:")
        if 'analysis' in analysis_result and 'summary' in analysis_result['analysis']:
            summary = analysis_result['analysis']['summary']
            print(f"完整度分数: {summary.get('completeness_score', 0)}")
            print(f"评价: {summary.get('evaluation', '未提供评价')}")
            print(f"一句话总结: {summary.get('one_line_summary', '未提供总结')}")
        
        # 保存分析结果
        analysis_db = AnalysisDatabase()
        analysis_id = analysis_db.save_analysis_result(report_id, analysis_result, analyzer_type='deepseek')
        
        print(f"分析结果已保存到数据库，分析ID: {analysis_id}")
        
        # 保存为JSON文件以便查看
        with open('latest_analysis.json', 'w', encoding='utf-8') as f:
            json.dump(analysis_result, f, ensure_ascii=False, indent=4)
        print("分析结果已保存到 latest_analysis.json 文件")
        
    except Exception as e:
        print(f"分析研报时出错: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    main() 