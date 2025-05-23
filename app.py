# -*- coding: utf-8 -*-
from flask import Flask, render_template, jsonify, request, redirect, url_for, abort, flash
import json
import os
import sys
import socket
from main import scrape_research_reports, analyze_with_five_steps, get_report_detail, get_evaluation_text
import database as db  # 导入数据库模块
import datetime
import sqlite3
import requests
import logging
from database import get_db_connection, get_reports_from_db, get_analysis_results_for_report, get_full_analysis_for_report
import threading
from analysis_db import AnalysisDatabase

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 版本常量
VERSION = "0.4.0"

# 数据库路径
DATABASE_PATH = 'research_reports.db'

app = Flask(__name__)

# 全局变量，存储爬取状态
scraping_status = {"is_scraping": False, "message": ""}

# 检查端口是否可用
def is_port_available(port):
    """检查指定端口是否可用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('127.0.0.1', port))
            return True
        except OSError:
            return False

# 找到一个可用的端口
def find_available_port(start_port=5001, max_attempts=10):
    """从指定端口开始查找可用端口"""
    port = start_port
    for _ in range(max_attempts):
        if is_port_available(port):
            return port
        port += 1
    # 如果找不到可用端口，返回一个较高的端口，希望它是可用的
    return 8080

# 加载研报数据
def load_reports():
    """
    从数据库加载研报数据
    如果数据库中没有数据，尝试从JSON文件导入
    """
    # 获取数据库中的报告数量
    report_count = db.count_reports()
    
    # 如果数据库中没有数据，尝试从JSON导入
    if report_count == 0 and os.path.exists('research_reports.json'):
        print("数据库中没有数据，尝试从JSON文件导入...")
        imported_count = db.import_from_json()
        print(f"成功导入 {imported_count} 条研报数据到数据库")
    
    # 从数据库获取研报列表
    return db.get_reports_from_db()

# 首页路由 - 展示研报列表
@app.route('/')
def index():
    """首页，展示研报列表"""
    reports = load_reports_from_db()
    return render_template('index.html', reports=reports)

# 研报详情页面
@app.route('/report/<int:report_id>')
def report_detail(report_id):
    """显示研报详情页面"""
    # 从数据库获取研报
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT * FROM reports WHERE id = ?
    ''', (report_id,))
    
    report = cursor.fetchone()
    conn.close()
    
    if not report:
        abort(404)
    
    # 将行对象转换为字典
    report_dict = dict(report)
    
    # 获取分析结果
    analysis_db = AnalysisDatabase()
    claude_analysis = analysis_db.get_analysis_by_report_id(report_id, analyzer_type='claude')
    deepseek_analysis = analysis_db.get_analysis_by_report_id(report_id, analyzer_type='deepseek')
    
    return render_template(
        'report_detail.html', 
        report=report_dict,
        claude_analysis=claude_analysis,
        deepseek_analysis=deepseek_analysis
    )

# API端点 - 获取所有研报数据
@app.route('/api/reports')
def api_reports():
    reports = load_reports()
    return jsonify(reports)

# API端点 - 获取特定研报数据
@app.route('/api/report/<int:report_id>')
def api_report(report_id):
    reports = load_reports()
    if 0 <= report_id < len(reports):
        return jsonify(reports[report_id])
    return jsonify({"error": "报告不存在"}), 404

# 实时爬取新研报
@app.route('/scrape', methods=['GET'])
def scrape():
    try:
        # 使用selenium爬取
        # 东方财富网行业研报页面 URL
        url = "https://data.eastmoney.com/report/hyyb.html"
        print(f"开始爬取研报列表，URL: {url}")
        
        from main import scrape_research_reports, get_report_detail, analyze_with_five_steps
        
        # 爬取研报列表
        reports_data = scrape_research_reports(url)
        
        if not reports_data:
            return jsonify({
                "success": False,
                "message": "未爬取到研报数据，请检查网站结构是否已更新"
            }), 500
            
        print(f"爬取到 {len(reports_data)} 条研报数据")
        
        # 对每份报告进行五步分析
        analyzed_reports = []
        
        # 处理所有爬取到的研报数据
        print(f"将处理全部 {len(reports_data)} 条研报数据")
        
        for i, report in enumerate(reports_data):
            try:
                print(f"\n处理第 {i+1}/{len(reports_data)} 条研报: {report.get('title', 'N/A')}")
                
                # 获取研报详情
                content = get_report_detail(report['link'])
                industry = report.get('industry', '未知行业')
                
                # 使用五步法分析
                analysis = analyze_with_five_steps(
                    report.get("abstract", ""),
                    content,
                    industry=industry
                )
                
                analyzed_reports.append({
                    "title": report.get("title", "N/A"),
                    "link": report.get("link", "N/A"),
                    "abstract": report.get("abstract", "N/A"),
                    "content_preview": content if content else "未获取到内容",
                    "full_content": content,  # 存储完整内容
                    "industry": industry,
                    "rating": report.get("rating", "N/A"),
                    "org": report.get("org", "N/A"),
                    "date": report.get("date", "N/A"),
                    "analysis": analysis,
                    "analysis_method": "Claude增强"
                })
                
                print(f"完成第 {i+1}/{len(reports_data)} 条研报的分析")
            except Exception as e:
                print(f"处理研报 {report.get('title', 'N/A')} 时出错: {str(e)}")
                # 继续处理下一条研报
        
        if not analyzed_reports:
            return jsonify({
                "success": False,
                "message": "未能成功分析任何研报，请检查分析逻辑"
            }), 500
        
        # 将分析结果保存到数据库
        db_saved_count = db.save_reports_to_db(analyzed_reports)
        
        # 同时保存到JSON文件（为了兼容性）
        with open('research_reports.json', 'w', encoding='utf-8') as f:
            json.dump(analyzed_reports, f, ensure_ascii=False, indent=4)
        
        print(f"成功分析了 {len(analyzed_reports)} 条研报，已保存 {db_saved_count} 条到数据库")
        
        return jsonify({
            "success": True,
            "message": f"成功爬取并分析了 {len(analyzed_reports)} 条研报数据，其中 {db_saved_count} 条保存到数据库",
            "count": len(analyzed_reports)
        })
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"爬取过程中发生错误: {str(e)}\n{error_details}")
        
        return jsonify({
            "success": False,
            "message": f"爬取过程中发生错误: {str(e)}"
        }), 500

# 统计页面 - 分析五步法应用情况
@app.route('/stats')
def stats_page():
    """统计分析页面"""
    reports = load_reports_from_db()
    
    if not reports:
        return render_template('stats.html', 
                              reports=[], 
                              industry_names=[],
                              industry_counts_list=[],
                              industry_counts={},
                              org_counts={},
                              industries=[],
                              organizations=[],
                              avg_score=0,
                              step_avg_scores=[0, 0, 0, 0, 0],
                              industry_avg_scores={},
                              org_avg_scores={},
                              rating_labels=[],
                              rating_counts=[])
    
    # 计算行业统计
    industry_counts = {}
    industry_avg_scores = {}
    for report in reports:
        industry = report.get("industry", "未知行业")
        if industry not in industry_counts:
            industry_counts[industry] = 0
            industry_avg_scores[industry] = []
        
        industry_counts[industry] += 1
        industry_avg_scores[industry].append(report["analysis"]["summary"]["completeness_score"])
    
    # 计算行业平均分
    for industry in industry_avg_scores:
        scores = industry_avg_scores[industry]
        industry_avg_scores[industry] = sum(scores) / len(scores) if scores else 0
    
    # 计算机构统计
    org_counts = {}
    org_avg_scores = {}
    for report in reports:
        org = report.get("org", "未知机构")
        if org not in org_counts:
            org_counts[org] = 0
            org_avg_scores[org] = []
        
        org_counts[org] += 1
        org_avg_scores[org].append(report["analysis"]["summary"]["completeness_score"])
    
    # 计算机构平均分
    for org in org_avg_scores:
        scores = org_avg_scores[org]
        org_avg_scores[org] = sum(scores) / len(scores) if scores else 0
    
    # 计算评级分布
    rating_counts_dict = {}
    for report in reports:
        rating = report.get("rating", "未知评级")
        # 标准化评级
        if rating in ["买入", "强烈推荐"]:
            rating = "买入/强烈推荐"
        elif rating in ["增持", "推荐"]:
            rating = "增持/推荐"
        elif rating in ["中性", "持有"]:
            rating = "中性/持有"
        elif rating in ["减持", "卖出"]:
            rating = "减持/卖出"
        else:
            rating = "其他"
            
        if rating not in rating_counts_dict:
            rating_counts_dict[rating] = 0
        
        rating_counts_dict[rating] += 1
    
    # 转换为列表
    rating_labels = list(rating_counts_dict.keys())
    rating_counts = list(rating_counts_dict.values())
    
    # 计算各步骤平均分
    step_scores = {"信息": [], "逻辑": [], "超预期": [], "催化剂": [], "结论": []}
    for report in reports:
        # 检查steps是列表还是字典，适配不同数据结构
        if "steps" in report["analysis"]:
            steps = report["analysis"]["steps"]
            # 如果是列表形式（旧版本）
            if isinstance(steps, list):
                for step in steps:
                    step_name = step.get("step_name", "")
                    step_score = step.get("step_score", 0)
                    
                    if "信息" in step_name:
                        step_scores["信息"].append(step_score)
                    elif "逻辑" in step_name:
                        step_scores["逻辑"].append(step_score)
                    elif "超预期" in step_name:
                        step_scores["超预期"].append(step_score)
                    elif "催化剂" in step_name:
                        step_scores["催化剂"].append(step_score)
                    elif "结论" in step_name:
                        step_scores["结论"].append(step_score)
            else:
                # 如果是字典形式（新版本）
                for step_key, step_data in steps.items():
                    step_score = step_data.get("step_score", 0)
                    if step_score == 0 and isinstance(step_data, dict):
                        step_score = float(step_data.get("step_score", 0))
                        
                    if "信息" in step_key:
                        step_scores["信息"].append(step_score)
                    elif "逻辑" in step_key:
                        step_scores["逻辑"].append(step_score)
                    elif "超预期" in step_key:
                        step_scores["超预期"].append(step_score)
                    elif "催化剂" in step_key:
                        step_scores["催化剂"].append(step_score)
                    elif "结论" in step_key:
                        step_scores["结论"].append(step_score)
    
    # 计算平均分
    step_avg_scores = []
    for step in ["信息", "逻辑", "超预期", "催化剂", "结论"]:
        scores = step_scores[step]
        avg = sum(scores) / len(scores) if scores else 0
        step_avg_scores.append(avg)
    
    # 计算总平均分
    all_scores = [report["analysis"]["summary"]["completeness_score"] for report in reports]
    avg_score = sum(all_scores) / len(all_scores) if all_scores else 0
    
    # 按研报数量降序排列
    industry_names = sorted(industry_counts.keys(), key=lambda x: industry_counts[x], reverse=True)
    industry_counts_list = [industry_counts[industry] for industry in industry_names]
    
    return render_template(
        'stats.html',
        reports=reports,
        industries=list(industry_counts.keys()),
        organizations=list(org_counts.keys()),
        industry_names=industry_names,
        industry_counts_list=industry_counts_list,
        industry_counts=industry_counts,
        org_counts=org_counts,
        avg_score=avg_score,
        step_avg_scores=step_avg_scores,
        industry_avg_scores=industry_avg_scores,
        org_avg_scores=org_avg_scores,
        rating_labels=rating_labels,
        rating_counts=rating_counts
    )

# 搜索研报
@app.route('/search')
def search_reports():
    """搜索研报"""
    query = request.args.get('q', '').strip()
    reports = load_reports_from_db()
    
    if not query:
        return redirect('/')
    
    # 简单关键词匹配
    filtered_reports = []
    for report in reports:
        if (query.lower() in report.get("title", "").lower() or 
            query.lower() in report.get("content", "").lower() or
            query.lower() in report.get("industry", "").lower() or
            query.lower() in report.get("org", "").lower()):
            filtered_reports.append(report)
    
    return render_template(
        'filtered_reports.html',
        reports=filtered_reports,
        filter_type="搜索",
        filter_value=query
    )

# 按行业筛选研报
@app.route('/industry/<industry>')
def industry_reports(industry):
    """按行业过滤研报"""
    reports = load_reports_from_db()
    filtered_reports = [report for report in reports if report.get("industry") == industry]
    
    return render_template(
        'filtered_reports.html',
        reports=filtered_reports,
        filter_type="行业",
        filter_value=industry
    )

@app.route('/organization/<org>')
def organization_reports(org):
    """按发布机构过滤研报"""
    reports = load_reports_from_db()
    filtered_reports = [report for report in reports if report.get("org") == org]
    
    return render_template(
        'filtered_reports.html',
        reports=filtered_reports,
        filter_type="机构",
        filter_value=org
    )

def background_scrape():
    """后台爬取研报的函数"""
    global scraping_status
    scraping_status["is_scraping"] = True
    scraping_status["message"] = "正在爬取研报数据..."
    
    try:
        # 调用爬虫主函数
        scrape_research_reports()
        scraping_status["message"] = f"爬取完成，时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    except Exception as e:
        scraping_status["message"] = f"爬取失败: {str(e)}"
    finally:
        scraping_status["is_scraping"] = False

@app.route('/scrape')
def scrape_endpoint():
    """触发爬虫的接口"""
    global scraping_status
    
    # 检查是否已经在爬取
    if scraping_status["is_scraping"]:
        return jsonify({"success": False, "message": "已经有一个爬取任务在进行中"})
    
    # 启动后台线程进行爬取
    threading.Thread(target=background_scrape).start()
    
    return jsonify({"success": True, "message": "爬取任务已启动"})

@app.route('/scrape-status')
def scrape_status():
    """获取爬取状态的接口"""
    global scraping_status
    return jsonify(scraping_status)

@app.route('/about')
def about():
    """关于页面"""
    return render_template('about.html', version=VERSION)

@app.route('/api/version')
def api_version():
    """获取应用版本信息的API"""
    return jsonify({
        "version": VERSION,
        "timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

@app.errorhandler(404)
def page_not_found(e):
    """404页面"""
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    """500页面"""
    return render_template('500.html'), 500

# 初始化应用
def init_app():
    # 初始化数据库
    db.init_db()
    
    # 如果存在JSON文件且数据库为空，导入数据
    if os.path.exists('research_reports.json') and db.count_reports() == 0:
        print("初始化数据库并导入现有数据...")
        db.import_from_json()

def load_reports_from_json():
    """从JSON文件加载研报数据"""
    try:
        json_path = os.path.join(os.path.dirname(__file__), 'research_reports.json')
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except Exception as e:
        logger.error(f"加载JSON文件出错: {e}")
        return []

def load_reports_from_db():
    """从数据库加载研报数据并构建完整的结构"""
    try:
        # 获取所有研报
        reports = get_reports_from_db()
        
        # 对每个研报添加分析结果
        for report in reports:
            report_id = report["id"]
            
            # 获取五步法分析结果
            steps = get_analysis_results_for_report(report_id)
            
            # 获取完整分析文本
            full_analysis = get_full_analysis_for_report(report_id)
            
            # 已经在analysis字段中的数据，不需要重新构建
            if "analysis" not in report:
                # 构建分析结构
                analysis = {}
                
                # 检查steps是否为字典类型
                if isinstance(steps, dict):
                    analysis["steps"] = steps
                else:
                    # 将步骤结果转换为预期结构
                    formatted_steps = {}
                    step_list = []
                    
                    for step in steps:
                        step_name = step.get("step_name", "")
                        formatted_steps[step_name] = step
                        step_list.append(step)
                    
                    # 同时保留步骤字典和步骤列表
                    analysis["steps"] = step_list
                
                # 计算完整性分数
                completeness_score = calculate_completeness_score(steps)
                
                # 构建摘要信息
                analysis["summary"] = {
                    "completeness_score": completeness_score,
                    "completeness_description": get_completeness_description(steps),
                    "improvement_suggestions": get_improvement_suggestions(steps),
                    "one_line_summary": full_analysis.get("one_line_summary", "") if full_analysis else ""
                }
                
                # 添加到报告
                report["analysis"] = analysis
            
            # 确保报告有内容字段
            report["content"] = report.get("full_content", report.get("content_preview", ""))
            
        return reports
    except Exception as e:
        logger.error(f"从数据库加载研报数据出错: {e}")
        return []

def calculate_completeness_score(steps):
    """根据五步法各步骤的分数计算总得分"""
    if not steps:
        return 0
    
    # 处理不同的步骤数据结构
    total_score = 0
    count = 0
        
    if isinstance(steps, list):
        # 列表形式
        total_score = sum(step.get("step_score", 0) for step in steps)
        count = len(steps)
    elif isinstance(steps, dict):
        # 字典形式
        for step_key, step_data in steps.items():
            if isinstance(step_data, dict):
                step_score = step_data.get("step_score", 0)
                total_score += step_score
                count += 1
    
    return int(total_score / count) if count else 0

def get_completeness_description(steps):
    """根据五步法分析结果提供完整性评估描述"""
    if not steps:
        return "无法评估研报完整性，缺少分析数据。"
        
    score = calculate_completeness_score(steps)
    
    if score >= 80:
        return "该研报对五步法的应用非常完善，几乎涵盖了所有分析要素，分析深入全面，投资建议有充分依据。"
    elif score >= 60:
        return "该研报对五步法的应用较为完善，涵盖了大部分分析要素，分析较为深入，投资建议有一定依据。"
    elif score >= 40:
        return "该研报对五步法的应用一般，部分分析要素有所欠缺，分析深度不足，投资建议缺乏充分依据。"
    else:
        return "该研报对五步法的应用不足，多数分析要素缺失，分析浅显，投资建议依据不足。"

def get_improvement_suggestions(steps):
    """根据五步法分析结果提供改进建议"""
    if not steps:
        return "无法提供改进建议，缺少分析数据。"
    
    missing_steps = []
    
    # 处理不同的步骤数据结构
    if isinstance(steps, list):
        # 列表形式
        for step in steps:
            if step.get("step_score", 0) < 60:
                step_name = step.get("step_name", "")
                missing_steps.append(step_name)
    elif isinstance(steps, dict):
        # 字典形式
        for step_name, step_data in steps.items():
            if isinstance(step_data, dict) and step_data.get("step_score", 0) < 60:
                missing_steps.append(step_name)
    
    if not missing_steps:
        return "研报结构完整，建议保持当前分析质量。"
    
    suggestions = "建议加强以下方面的分析："
    for step in missing_steps:
        if "信息" in step:
            suggestions += " 1) 收集更丰富的基础信息和数据；"
        elif "逻辑" in step:
            suggestions += " 2) 加强分析推理的逻辑性和连贯性；"
        elif "超预期" in step:
            suggestions += " 3) 深入挖掘市场共识之外的观点和信息；"
        elif "催化剂" in step:
            suggestions += " 4) 明确指出能够促使股价变动的关键因素；"
        elif "结论" in step:
            suggestions += " 5) 给出更明确的投资建议和目标价。"
    
    return suggestions

@app.route('/analyze/<int:report_id>')
def analyze_report(report_id):
    """分析研报"""
    analyzer_type = request.args.get('analyzer', 'claude')
    
    # 从数据库获取研报
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT title, full_content, industry FROM reports WHERE id = ?
    ''', (report_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        flash('未找到研报', 'error')
        return redirect(url_for('index'))
    
    title, content, industry = result
    
    try:
        if analyzer_type == 'claude':
            # 使用Claude分析器
            from claude_analyzer import ClaudeAnalyzer
            analyzer = ClaudeAnalyzer()
            analysis_result = analyzer.analyze_with_five_steps(title, content, industry)
        else:
            # 使用DeepSeek分析器
            from deepseek_analyzer import DeepSeekAnalyzer
            analyzer = DeepSeekAnalyzer()
            analysis_result = analyzer.analyze_with_five_steps(title, content, industry)
        
        # 保存分析结果到数据库
        analysis_db = AnalysisDatabase()
        analysis_db.save_analysis_result(report_id, analysis_result, analyzer_type=analyzer_type)
        
        flash(f'使用{analyzer_type}分析完成', 'success')
    except Exception as e:
        flash(f'分析失败: {str(e)}', 'error')
    
    return redirect(url_for('report_detail', report_id=report_id))

if __name__ == '__main__':
    # 初始化应用
    init_app()
    
    # 查找可用端口
    port = find_available_port()
    print(f"启动Flask应用，使用端口: {port}")
    app.run(debug=True, port=port) 