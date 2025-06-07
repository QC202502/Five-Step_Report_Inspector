#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import time
import dotenv
from main import scrape_research_reports, get_report_detail
from deepseek_analyzer import DeepSeekAnalyzer
from analysis_db import AnalysisDatabase
import json

def main():
    """
    爬取5条研报，使用DeepSeek分析器分析，并将结果存入数据库
    """
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
            print(f"从.env文件中获取到API密钥，长度: {len(api_key)}")
            os.environ["DEEPSEEK_API_KEY"] = api_key
        else:
            print("警告: 无法找到DeepSeek API密钥，请确保.env文件中包含DEEPSEEK_API_KEY")
            return
    
    print("开始批量爬取研报并使用DeepSeek分析...")
    
    # 东方财富网行业研报页面 URL
    report_url = "https://data.eastmoney.com/report/hyyb.html"
    
    # 爬取研究报告列表
    reports_data = scrape_research_reports(report_url)
    print(f"爬取到 {len(reports_data)} 条研报数据")
    
    if not reports_data:
        print("未爬取到任何研报，请检查网络连接或网站结构是否变化")
        return
    
    # 初始化分析器和数据库
    analyzer = DeepSeekAnalyzer()
    analysis_db = AnalysisDatabase()
    
    # 处理前5条研报（或者所有研报，如果不足5条）
    num_reports = min(5, len(reports_data))
    processed_reports = 0
    
    for i in range(num_reports):
        report = reports_data[i]
        print(f"\n处理第 {i+1}/{num_reports} 条研报: {report.get('title', 'N/A')}")
        print(f"行业: {report.get('industry', 'N/A')}")
        print(f"链接: {report.get('link', 'N/A')}")
        
        try:
            # 获取研报详情
            max_retries = 3
            content = None
            
            for retry in range(max_retries):
                try:
                    content = get_report_detail(report['link'])
                    if content and len(content) > 200:
                        break
                    print(f"研报内容过短或为空，重试 ({retry+1}/{max_retries})...")
                    time.sleep(2)
                except Exception as e:
                    print(f"获取研报详情出错: {str(e)}")
                    if retry < max_retries - 1:
                        print(f"重试 ({retry+1}/{max_retries})...")
                        time.sleep(3)
            
            if not content or len(content) < 200:
                print(f"无法获取有效研报内容，跳过此研报")
                continue
                
            print(f"成功获取研报内容，长度: {len(content)} 字符")
            print(f"内容预览: {content[:100]}...")
            
            # 使用DeepSeek分析器进行五步法分析
            print("\n开始调用DeepSeek API进行分析...")
            analysis_result = analyzer.analyze_with_five_steps(report['title'], content, report['industry'])
            
            print("\n分析完成，结果摘要:")
            if 'summary' in analysis_result:
                summary = analysis_result['summary']
                print(f"完整度分数: {summary.get('completeness_score', 0)}")
                print(f"评价: {summary.get('evaluation', '未提供评价')}")
                if 'one_line_summary' in summary:
                    print(f"一句话总结: {summary.get('one_line_summary', '未提供总结')}")
            
            # 将研报保存到数据库，获取报告ID
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
            analysis_id = analysis_db.save_analysis_result(report_id, analysis_result, analyzer_type='deepseek')
            print(f"分析结果已保存到数据库，分析ID: {analysis_id}")
            
            # 为每个研报保存一个独立的JSON文件
            json_filename = f'analysis_report_{i+1}.json'
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(analysis_result, f, ensure_ascii=False, indent=4)
            print(f"分析结果已保存到 {json_filename} 文件")
            
            processed_reports += 1
            
            # 处理完一个研报后短暂等待，避免过快请求
            if i < num_reports - 1:
                print("等待2秒后处理下一个研报...")
                time.sleep(2)
                
        except Exception as e:
            print(f"处理研报时出错: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print(f"\n总共成功处理了 {processed_reports}/{num_reports} 条研报")
    
    # 启动网站应用以展示结果
    print("\n所有研报已分析完成并存入数据库，您可以通过运行以下命令启动网站查看结果:")
    print("python app.py")

if __name__ == "__main__":
    main() 