#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爬取并分析5篇研报，使用DeepSeek API，结果存入数据库
"""

import os
import sys
import time
import dotenv
from main import scrape_research_reports, get_report_detail
from deepseek_analyzer import DeepSeekAnalyzer
from analysis_db import AnalysisDatabase
import json

def main():
    """爬取并分析5篇研报，结果存入数据库"""
    # 加载环境变量
    print("加载环境变量...")
    dotenv.load_dotenv()
    
    # 确保DeepSeek API密钥已设置
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        with open('.env', 'r') as f:
            for line in f:
                if line.startswith('DEEPSEEK_API_KEY='):
                    api_key = line.strip().split('=', 1)[1]
                    break
        if api_key:
            print(f"从.env文件中获取到API密钥: {api_key[:8]}...")
            os.environ["DEEPSEEK_API_KEY"] = api_key
        else:
            print("错误: 无法找到DeepSeek API密钥，请在.env文件中设置DEEPSEEK_API_KEY")
            return
    
    print("开始爬取5篇研报并使用DeepSeek API进行分析")
    
    # 东方财富网行业研报页面 URL
    report_url = "https://data.eastmoney.com/report/hyyb.html"
    
    # 爬取研究报告列表
    print(f"从 {report_url} 爬取研报列表...")
    reports_data = scrape_research_reports(report_url)
    
    if not reports_data or len(reports_data) == 0:
        print("错误: 未爬取到研报数据，请检查网络连接或网站结构")
        return
        
    print(f"成功爬取到 {len(reports_data)} 条研报数据")
    
    # 初始化DeepSeek分析器和数据库
    print("初始化DeepSeek分析器...")
    analyzer = DeepSeekAnalyzer()
    analysis_db = AnalysisDatabase()
    
    # 只处理5篇研报
    reports_to_process = min(5, len(reports_data))
    processed_reports = []
    
    print(f"开始处理前 {reports_to_process} 篇研报...")
    for i in range(reports_to_process):
        report = reports_data[i]
        print(f"\n[{i+1}/{reports_to_process}] 处理研报: {report.get('title', 'N/A')}")
        
        # 获取研报详情
        try:
            print(f"获取研报详情，链接: {report.get('link', 'N/A')}")
            content = get_report_detail(report['link'])
            
            if not content or len(content) < 100:
                print(f"警告: 研报内容过短或为空，跳过此研报")
                continue
                
            print(f"成功获取研报内容，长度: {len(content)} 字符")
            print(f"内容预览: {content[:100]}...")
            
            # 使用DeepSeek API进行分析
            print(f"使用DeepSeek API分析研报...")
            analysis_result = analyzer.analyze_with_five_steps(
                report.get('title', ''),
                content,
                industry=report.get('industry', '未知行业')
            )
            
            # 保存研报到数据库
            import sqlite3
            conn = sqlite3.connect('research_reports.db')
            cursor = conn.cursor()
            
            # 检查研报是否已存在
            cursor.execute('SELECT id FROM reports WHERE link = ?', (report['link'],))
            existing_report = cursor.fetchone()
            
            if existing_report:
                report_id = existing_report[0]
                print(f"研报已存在于数据库，ID: {report_id}")
            else:
                # 插入新研报
                cursor.execute('''
                INSERT INTO reports (title, link, abstract, content_preview, full_content, industry, rating, org, date, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
                ''', (
                    report.get('title', ''),
                    report.get('link', ''),
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
            
            # 保存分析结果到数据库
            analysis_id = analysis_db.save_analysis_result(report_id, analysis_result, analyzer_type='deepseek')
            print(f"分析结果已保存到数据库，分析ID: {analysis_id}")
            
            # 显示分析摘要
            if 'summary' in analysis_result:
                summary = analysis_result['summary']
                print("\n===== 分析摘要 =====")
                print(f"完整度评分: {summary.get('completeness_score', 0)}")
                print(f"总体评价: {summary.get('evaluation', '未提供评价')}")
                if 'one_line_summary' in summary:
                    print(f"一句话总结: {summary.get('one_line_summary', '未提供总结')}")
            
            processed_reports.append({
                'id': report_id,
                'title': report.get('title', ''),
                'industry': report.get('industry', ''),
                'analysis_id': analysis_id
            })
            
            # 处理完一个研报后稍微等待，避免请求过快
            if i < reports_to_process - 1:
                print("等待3秒后处理下一篇研报...")
                time.sleep(3)
                
        except Exception as e:
            print(f"处理研报时出错: {str(e)}")
            import traceback
            traceback.print_exc()
    
    # 打印处理结果
    print(f"\n成功处理了 {len(processed_reports)} 篇研报:")
    for i, report in enumerate(processed_reports):
        print(f"{i+1}. {report['title']} (ID: {report['id']}, 行业: {report['industry']})")
    
    # 提示如何查看结果
    print("\n所有研报已分析完成并存入数据库。")
    print("您可以通过以下方式查看结果:")
    print("1. 启动网站应用: python app.py")
    print("2. 访问网站: http://127.0.0.1:5002")
    print("3. 在网站上查看研报列表和详细分析结果")

if __name__ == "__main__":
    main() 