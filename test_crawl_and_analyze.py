#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
from main import scrape_research_reports, get_report_detail
from deepseek_analyzer import DeepSeekAnalyzer
from analysis_db import AnalysisDatabase
import json

def main():
    """
    爬取一条研报，使用DeepSeek分析器分析，并将结果存入数据库
    """
    # 设置 DeepSeek API 密钥
    os.environ["DEEPSEEK_API_KEY"] = "YOUR_DEEPSEEK_API_KEY"
    
    print("开始测试爬取研报并使用DeepSeek分析...")
    
    # 东方财富网行业研报页面 URL
    report_url = "https://data.eastmoney.com/report/hyyb.html"
    
    # 爬取研究报告列表
    reports_data = scrape_research_reports(report_url)
    print(f"爬取到 {len(reports_data)} 条研报数据")
    
    if not reports_data:
        print("未爬取到任何研报，请检查网络连接或网站结构是否变化")
        return
    
    # 只处理第一条研报
    report = reports_data[0]
    print(f"\n处理研报: {report.get('title', 'N/A')}")
    print(f"行业: {report.get('industry', 'N/A')}")
    print(f"链接: {report.get('link', 'N/A')}")
    
    try:
        # 获取研报详情
        content = get_report_detail(report['link'])
        if not content:
            print("未能获取研报内容，请检查链接是否有效")
            return
            
        print(f"成功获取研报内容，长度: {len(content)} 字符")
        print(f"内容预览: {content[:200]}...")
        
        # 使用DeepSeek分析器进行五步法分析
        print("\n开始调用DeepSeek API进行分析...")
        analyzer = DeepSeekAnalyzer()
        analysis_result = analyzer.analyze_with_five_steps(report['title'], content, report['industry'])
        
        print("\n分析完成，结果摘要:")
        if 'analysis' in analysis_result and 'summary' in analysis_result['analysis']:
            summary = analysis_result['analysis']['summary']
            print(f"完整度分数: {summary.get('completeness_score', 0)}")
            print(f"评价: {summary.get('evaluation', '未提供评价')}")
            print(f"一句话总结: {summary.get('one_line_summary', '未提供总结')}")
        
        # 将分析结果保存到数据库
        # 首先将研报保存到数据库，获取报告ID
        import sqlite3
        conn = sqlite3.connect('research_reports.db')
        cursor = conn.cursor()
        
        # 检查研报是否已存在
        cursor.execute('SELECT id FROM reports WHERE link = ?', (report['link'],))
        existing_report = cursor.fetchone()
        
        if existing_report:
            report_id = existing_report[0]
            print(f"研报已存在于数据库中，ID: {report_id}")
        else:
            # 插入新研报
            cursor.execute('''
            INSERT INTO reports (title, link, abstract, content_preview, full_content, industry, rating, org, date, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            ''', (
                report['title'],
                report['link'],
                report.get('abstract', ''),
                content[:500] if content else '',  # 预览
                content,  # 完整内容
                report.get('industry', '未知行业'),
                report.get('rating', ''),
                report.get('org', ''),
                report.get('date', '')
            ))
            conn.commit()
            report_id = cursor.lastrowid
            print(f"研报已保存到数据库，新ID: {report_id}")
        
        conn.close()
        
        # 保存分析结果
        analysis_db = AnalysisDatabase()
        analysis_id = analysis_db.save_analysis_result(report_id, analysis_result, analyzer_type='deepseek')
        
        print(f"分析结果已保存到数据库，分析ID: {analysis_id}")
        
        # 保存为JSON文件以便查看
        with open('latest_analysis.json', 'w', encoding='utf-8') as f:
            json.dump(analysis_result, f, ensure_ascii=False, indent=4)
        print("分析结果已保存到 latest_analysis.json 文件")
        
    except Exception as e:
        print(f"处理研报时出错: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 