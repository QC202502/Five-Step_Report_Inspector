#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本：爬取一篇研报并使用DeepSeek进行五步法分析
"""

import os
import sys
import json
import time
import dotenv  # 导入dotenv库用于加载环境变量
from main import get_report_detail, scrape_research_reports
from deepseek_analyzer import DeepSeekAnalyzer  # 直接导入DeepSeek分析器

def test_single_report():
    """爬取一篇研报并进行分析"""
    print("开始测试研报爬取和DeepSeek分析...")
    
    # 加载.env文件中的环境变量
    print("加载.env文件中的环境变量...")
    dotenv.load_dotenv()
    
    # 手动设置DeepSeek API密钥
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
            print("警告: 无法从.env文件中获取API密钥")
    
    # 东方财富网行业研报页面 URL
    url = "https://data.eastmoney.com/report/hyyb.html"
    print(f"从 {url} 爬取研报列表...")
    
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # 爬取研报列表
            reports_data = scrape_research_reports(url)
            
            if not reports_data or len(reports_data) == 0:
                print("未获取到研报数据，请检查网站是否更新或网络连接")
                retry_count += 1
                print(f"重试 ({retry_count}/{max_retries})...")
                time.sleep(2)  # 等待2秒后重试
                continue
                
            print(f"成功爬取到 {len(reports_data)} 条研报数据")
            
            # 选择其中一条研报进行分析（第5条，避免热门研报可能被限制访问）
            report_index = min(4, len(reports_data) - 1)  # 确保索引有效
            report = reports_data[report_index]
            print(f"\n选择研报: {report.get('title', 'N/A')}")
            
            # 获取研报详情
            print(f"获取研报详情，链接: {report.get('link', 'N/A')}")
            
            # 添加重试逻辑
            content_retry = 0
            while content_retry < max_retries:
                try:
                    content = get_report_detail(report['link'])
                    if content and len(content) > 200:  # 确保内容有效
                        break
                    print(f"研报内容过短，可能未正确获取，重试 ({content_retry+1}/{max_retries})...")
                    content_retry += 1
                    time.sleep(2)
                except Exception as e:
                    print(f"获取研报详情时出错: {str(e)}")
                    content_retry += 1
                    if content_retry < max_retries:
                        print(f"重试获取研报内容 ({content_retry}/{max_retries})...")
                        time.sleep(3)  # 等待时间延长
            
            if not content or len(content) < 200:
                print("多次尝试后仍未能获取有效研报内容，尝试其他研报...")
                retry_count += 1
                continue
                
            print(f"成功获取研报内容，长度: {len(content)} 字符")
            print(f"内容预览: {content[:200]}...")
            
            # 确认环境变量已设置
            print(f"当前DeepSeek API密钥: {os.environ.get('DEEPSEEK_API_KEY', '未设置')[:8]}...")
            
            # 直接使用DeepSeek分析器
            print("\n开始使用DeepSeek进行五步法分析...")
            analyzer = DeepSeekAnalyzer()
            industry = report.get('industry', '未知行业')
            
            # 直接调用分析器的方法
            analysis_result = analyzer.analyze_with_five_steps(
                report.get("title", ""),
                content,
                industry=industry
            )
            
            # 保存分析结果到文件
            with open('test_analysis_result.json', 'w', encoding='utf-8') as f:
                json.dump(analysis_result, f, ensure_ascii=False, indent=4)
                
            print("\n分析完成，结果已保存到 test_analysis_result.json")
            
            # 显示分析摘要
            if 'summary' in analysis_result:
                summary = analysis_result['summary']
                print("\n===== 分析摘要 =====")
                print(f"完整度评分: {summary.get('completeness_score', 0)}")
                print(f"总体评价: {summary.get('evaluation', '无评价')}")
                if 'one_line_summary' in summary:
                    print(f"一句话总结: {summary.get('one_line_summary', '无总结')}")
                    
            return True
            
        except Exception as e:
            print(f"测试过程中出错: {str(e)}")
            import traceback
            traceback.print_exc()
            retry_count += 1
            if retry_count < max_retries:
                print(f"\n进行第 {retry_count+1} 次重试...")
                time.sleep(3)  # 等待3秒后重试
    
    print(f"达到最大重试次数 ({max_retries})，测试失败")
    return False

if __name__ == "__main__":
    success = test_single_report()
    sys.exit(0 if success else 1) 