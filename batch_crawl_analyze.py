#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import time
import dotenv
import sqlite3
from main import scrape_research_reports, get_report_detail
from deepseek_analyzer import DeepSeekAnalyzer
from analysis_db import AnalysisDatabase
import json

def main():
    """
    爬取10条研报，使用DeepSeek分析器分析，并将结果存入数据库
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
    
    # 连接数据库，用于检查研报是否已存在
    conn = sqlite3.connect('research_reports.db')
    cursor = conn.cursor()
    
    # 获取数据库中已存在的研报链接
    cursor.execute('SELECT link FROM reports')
    existing_links = {row[0] for row in cursor.fetchall()}
    print(f"数据库中已有 {len(existing_links)} 条研报记录")
    
    # 过滤掉已经存在的研报
    new_reports = [report for report in reports_data if report['link'] not in existing_links]
    print(f"发现 {len(new_reports)} 条新研报")
    
    # 处理前10条新研报（或者所有新研报，如果不足10条）
    num_reports = min(10, len(new_reports))
    processed_reports = 0
    
    if num_reports == 0:
        print("没有新的研报需要处理")
        conn.close()
        return
    
    for i, report in enumerate(new_reports[:num_reports]):
        print(f"\n处理第 {i+1}/{len(new_reports[:num_reports])} 条新研报: {report.get('title', 'N/A')}")
        print(f"行业: {report.get('industry', 'N/A')}")
        print(f"链接: {report.get('link', 'N/A')}")
        
        try:
            # 获取研报详情
            content = get_report_detail(report['link'])
            
            if not content or len(content.strip()) < 100:
                print(f"警告: 获取到的研报内容过短或为空，可能无法进行有效分析")
                content = f"[内容获取失败] {report.get('title', '')} - {report.get('abstract', '')}"
            
            print(f"成功获取研报内容，长度: {len(content)} 字符")
            preview = content[:100].replace('\n', ' ') if len(content) > 100 else content.replace('\n', ' ')
            print(f"内容预览: {preview}...")
            
            # 使用DeepSeek进行五步法分析
            print("\n开始调用DeepSeek API进行分析...")
            try:
                analysis_result = analyzer.analyze_with_five_steps(
                    report['title'], 
                    content,
                    industry=report['industry']
                )
                
                # 检查分析结果是否有效
                if not analysis_result or not isinstance(analysis_result, dict):
                    print("警告: DeepSeek分析返回了无效结果，使用默认分析")
                    analysis_result = {
                        "analysis": {
                            "信息": {"found": True, "keywords": ["数据"], "evidence": ["由于分析错误，使用默认结果"], "step_score": 60, "description": "包含基本信息"},
                            "逻辑": {"found": True, "keywords": ["分析"], "evidence": ["由于分析错误，使用默认结果"], "step_score": 60, "description": "包含基本逻辑"},
                            "超预期": {"found": False, "keywords": [], "evidence": [], "step_score": 0, "description": "未找到明显超预期"},
                            "催化剂": {"found": False, "keywords": [], "evidence": [], "step_score": 0, "description": "未找到明显催化剂"},
                            "结论": {"found": True, "keywords": ["建议"], "evidence": ["由于分析错误，使用默认结果"], "step_score": 60, "description": "包含基本结论"},
                            "summary": {
                                "completeness_score": 60,
                                "steps_found": 3,
                                "evaluation": "研报部分应用了五步分析法，关键分析要素有所欠缺",
                                "one_line_summary": "由于分析错误，使用默认结果"
                            }
                        },
                        "full_analysis": "由于分析错误，使用默认结果"
                    }
                
                # 确保结构正确
                if "analysis" not in analysis_result:
                    print("警告: 分析结果结构不正确，重新组织结构")
                    # 保存原始分析结果
                    original_analysis = analysis_result
                    
                    # 创建新的结构化结果
                    analysis_result = {
                        "analysis": {},
                        "full_analysis": original_analysis.get("full_analysis", "无法获取完整分析")
                    }
                    
                    # 复制五步法分析结果
                    for step in ["信息", "逻辑", "超预期", "催化剂", "结论"]:
                        if step in original_analysis:
                            analysis_result["analysis"][step] = original_analysis[step]
                        else:
                            analysis_result["analysis"][step] = {
                                "found": False, 
                                "keywords": [], 
                                "evidence": [], 
                                "step_score": 0,
                                "description": f"未找到{step}相关内容"
                            }
                
                # 确保analysis包含summary字段
                if "summary" not in analysis_result["analysis"]:
                    print("警告: 分析结果中没有summary字段，添加默认summary")
                    # 计算找到的步骤数量
                    steps_found = sum(1 for step in ["信息", "逻辑", "超预期", "催化剂", "结论"] 
                                    if step in analysis_result["analysis"] and analysis_result["analysis"][step].get("found", False))
                    
                    # 计算完整度分数
                    completeness_score = int((steps_found / 5) * 100)
                    
                    # 生成评价文本
                    if completeness_score >= 90:
                        evaluation = "研报非常完整地应用了五步分析法，包含了全面的分析要素"
                    elif completeness_score >= 80:
                        evaluation = "研报较好地应用了五步分析法，大部分分析要素齐全"
                    elif completeness_score >= 60:
                        evaluation = "研报部分应用了五步分析法，关键分析要素有所欠缺"
                    elif completeness_score >= 40:
                        evaluation = "研报仅包含少量五步分析法要素，分析不够全面"
                    else:
                        evaluation = "研报几乎未应用五步分析法，分析要素严重不足"
                    
                    analysis_result["analysis"]["summary"] = {
                        "completeness_score": completeness_score,
                        "steps_found": steps_found,
                        "evaluation": evaluation,
                        "one_line_summary": "自动生成的分析总结"
                    }
                
                # 确保每个步骤都有step_score字段
                for step in ["信息", "逻辑", "超预期", "催化剂", "结论"]:
                    if step in analysis_result["analysis"] and "step_score" not in analysis_result["analysis"][step]:
                        found = analysis_result["analysis"][step].get("found", False)
                        analysis_result["analysis"][step]["step_score"] = 60 if found else 0
            except Exception as e:
                print(f"DeepSeek分析过程中出错: {str(e)}")
                print("使用默认分析结果...")
                analysis_result = {
                    "analysis": {
                        "信息": {"found": True, "keywords": ["数据"], "evidence": ["由于分析错误，使用默认结果"], "step_score": 60, "description": "包含基本信息"},
                        "逻辑": {"found": True, "keywords": ["分析"], "evidence": ["由于分析错误，使用默认结果"], "step_score": 60, "description": "包含基本逻辑"},
                        "超预期": {"found": False, "keywords": [], "evidence": [], "step_score": 0, "description": "未找到明显超预期"},
                        "催化剂": {"found": False, "keywords": [], "evidence": [], "step_score": 0, "description": "未找到明显催化剂"},
                        "结论": {"found": True, "keywords": ["建议"], "evidence": ["由于分析错误，使用默认结果"], "step_score": 60, "description": "包含基本结论"},
                        "summary": {
                            "completeness_score": 60,
                            "steps_found": 3,
                            "evaluation": "研报部分应用了五步分析法，关键分析要素有所欠缺",
                            "one_line_summary": "由于分析错误，使用默认结果"
                        }
                    },
                    "full_analysis": "由于分析错误，使用默认结果"
                }
            
            print("\n分析完成，结果摘要:")
            
            # 保存研报到数据库
            try:
                # 将研报保存到数据库
                report_id = analysis_db.insert_report(
                    report['title'],
                    report['link'],
                    report.get('industry', '未知行业'),
                    report.get('rating', ''),
                    report.get('org', ''),
                    report.get('date', ''),
                    content
                )
                print(f"研报已保存到数据库，新ID: {report_id}")
                
                # 保存分析结果到数据库
                try:
                    analysis_id = analysis_db.insert_analysis(report_id, 'deepseek', json.dumps(analysis_result, ensure_ascii=False))
                    print(f"分析结果已保存到数据库，分析ID: {analysis_id}")
                except Exception as e:
                    print(f"保存到数据库时出错: {str(e)}")
                
                # 保存分析结果到JSON文件
                analysis_file = f"analysis_report_{i+1}.json"
                with open(analysis_file, 'w', encoding='utf-8') as f:
                    json.dump(analysis_result, f, ensure_ascii=False, indent=4)
                print(f"分析结果已保存到 {analysis_file} 文件")
                
                # 更新成功处理的报告计数
                processed_reports += 1
            except Exception as db_error:
                print(f"保存到数据库时出错: {str(db_error)}")
        except Exception as e:
            print(f"处理研报时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            print("跳过此研报，继续处理下一个...")
        
        # 添加间隔，避免API请求过于频繁
        if i < len(new_reports[:num_reports]) - 1:
            print("等待2秒后处理下一个研报...")
            time.sleep(2)
    
    # 关闭数据库连接
    conn.close()
    
    print(f"\n总共成功处理了 {processed_reports}/{num_reports} 条新研报")
    
    # 启动网站应用以展示结果
    print("\n所有研报已分析完成并存入数据库，您可以通过运行以下命令启动网站查看结果:")
    print("python app.py")

if __name__ == "__main__":
    main() 