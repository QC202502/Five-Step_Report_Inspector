# -*- coding: utf-8 -*-
from flask import Flask, render_template, jsonify, request
import json
import os
import sys
import socket
from main import scrape_research_reports, analyze_with_five_steps, get_report_detail, get_evaluation_text
import database as db  # 导入数据库模块

# 版本常量
VERSION = "0.2.1"

app = Flask(__name__)

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
    reports = load_reports()
    return render_template('index.html', reports=reports)

# 研报详情页面
@app.route('/report/<int:report_id>')
def report_detail(report_id):
    reports = load_reports()
    if 0 <= report_id < len(reports):
        report = reports[report_id]
        
        # 获取五步法分析统计
        steps_stats = {}
        for step in ["信息", "逻辑", "超预期", "催化剂", "结论"]:
            steps_stats[step] = {
                "found": report["analysis"][step]["found"],
                "keywords": report["analysis"][step]["keywords"],
                "evidence": report["analysis"][step]["evidence"],
                "description": report["analysis"][step]["description"]
            }
            
        # 预处理雷达图数据
        steps_order = ["信息", "逻辑", "超预期", "催化剂", "结论"]
        radar_data = [100 if steps_stats[step]["found"] else 0 for step in steps_order]
        
        # 确定进度条样式
        score = report["analysis"]["summary"]["completeness_score"]
        if score >= 80:
            progress_class = "bg-success"
        elif score >= 60:
            progress_class = "bg-info"
        elif score >= 40:
            progress_class = "bg-warning"
        else:
            progress_class = "bg-danger"
        
        return render_template(
            'report_detail.html', 
            report=report, 
            steps_stats=steps_stats,
            steps_order=steps_order,
            radar_data=radar_data,
            progress_class=progress_class,
            score=score
        )
    return "报告不存在", 404

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
        # 从东方财富网爬取最新研报
        report_url = "https://data.eastmoney.com/report/hyyb.html"
        print(f"开始爬取研报数据: {report_url}")
        reports_data = scrape_research_reports(report_url)
        print(f"成功爬取到 {len(reports_data)} 条研报数据")
        
        if not reports_data:
            return jsonify({
                "success": False,
                "message": "未能爬取到有效的研报数据，请检查爬取逻辑或网站结构是否变更"
            }), 500
        
        # 处理所有爬取到的研报
        print(f"将处理全部 {len(reports_data)} 条研报")
        
        # 分析研报
        analyzed_reports = []
        for i, report in enumerate(reports_data):
            try:
                print(f"\n处理第 {i+1}/{len(reports_data)} 条研报: {report.get('title', 'N/A')}")
                
                # 获取研报详情内容
                content = get_report_detail(report.get("link", ""))
                
                # 获取行业信息
                industry = report.get("industry", "N/A")
                
                # 进行五步分析，使用Claude
                analysis = analyze_with_five_steps(
                    report.get("abstract", ""),
                    content,
                    industry=industry
                )
                
                analyzed_reports.append({
                    "title": report.get("title", "N/A"),
                    "link": report.get("link", "N/A"),
                    "abstract": report.get("abstract", "N/A"),
                    "content_preview": content[:200] + "..." if content else "未获取到内容",
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
def stats():
    reports = load_reports()
    
    # 计算五步法各步骤出现的频率
    steps_stats = {}
    for step in ["信息", "逻辑", "超预期", "催化剂", "结论"]:
        count = sum(1 for r in reports if r["analysis"][step]["found"])
        steps_stats[step] = {
            "count": count,
            "percentage": round(count / len(reports) * 100 if reports else 0, 1)
        }
    
    # 计算五步法完整度分数分布
    score_distribution = {
        "excellent": sum(1 for r in reports if r["analysis"]["summary"]["completeness_score"] >= 80),
        "good": sum(1 for r in reports if 60 <= r["analysis"]["summary"]["completeness_score"] < 80),
        "average": sum(1 for r in reports if 40 <= r["analysis"]["summary"]["completeness_score"] < 60),
        "poor": sum(1 for r in reports if r["analysis"]["summary"]["completeness_score"] < 40)
    }
    
    # 按行业统计
    industry_stats = {}
    for report in reports:
        industry = report.get("industry", "未知")
        if industry not in industry_stats:
            industry_stats[industry] = []
        industry_stats[industry].append(report["analysis"]["summary"]["completeness_score"])
    
    # 计算每个行业的平均分
    for industry in industry_stats:
        scores = industry_stats[industry]
        industry_stats[industry] = {
            "count": len(scores),
            "avg_score": round(sum(scores) / len(scores), 1)
        }
    
    return render_template(
        'stats.html', 
        steps_stats=steps_stats, 
        score_distribution=score_distribution,
        industry_stats=industry_stats,
        total_reports=len(reports)
    )

# 搜索研报
@app.route('/search')
def search():
    keyword = request.args.get('q', '')
    if not keyword:
        return redirect('/')
        
    reports = db.search_reports(keyword)
    return render_template('search_results.html', 
                           reports=reports, 
                           keyword=keyword, 
                           count=len(reports))

# 按行业筛选研报
@app.route('/industry/<industry>')
def industry_reports(industry):
    reports = db.get_reports_by_industry(industry)
    return render_template('industry.html', 
                           reports=reports, 
                           industry=industry, 
                           count=len(reports))

# 初始化应用
def init_app():
    # 初始化数据库
    db.init_db()
    
    # 如果存在JSON文件且数据库为空，导入数据
    if os.path.exists('research_reports.json') and db.count_reports() == 0:
        print("初始化数据库并导入现有数据...")
        db.import_from_json()

if __name__ == '__main__':
    # 初始化应用
    init_app()
    
    # 查找可用端口
    port = find_available_port()
    print(f"启动Flask应用，使用端口: {port}")
    app.run(debug=True, port=port) 