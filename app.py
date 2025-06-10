# -*- coding: utf-8 -*-
from flask import Flask, render_template, jsonify, request, redirect, url_for, abort, flash, Markup, session
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
from database import get_db_connection, get_reports_from_db
import threading
from analysis_db import AnalysisDatabase
from recommendation_engine import RecommendationEngine
from user_manager import UserManager, login_required, admin_required

# 创建Flask应用
app = Flask(__name__)
app.secret_key = 'five_step_report_inspector_secret_key'  # 设置密钥
app.permanent_session_lifetime = datetime.timedelta(days=30)  # 会话有效期

# 创建分析数据库实例
analysis_db = AnalysisDatabase()

# 创建用户管理器实例
user_manager = UserManager()

# 创建偏好设置管理器实例
from preference_manager import PreferenceManager
preference_manager = PreferenceManager()

# 添加nl2br过滤器，用于在HTML中显示换行
@app.template_filter('nl2br')
def nl2br(value):
    """将换行符转换为HTML的<br>标签"""
    if not value:
        return ""
    return Markup(value.replace('\n', '<br>'))

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 版本常量
VERSION = "0.7.2"
# 数据库路径
DATABASE_PATH = 'research_reports.db'

# 全局变量，存储爬取状态
scraping_status = {"is_scraping": False, "message": ""}

# 用户认证相关路由
@app.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录页面"""
    # 如果用户已登录，重定向到首页
    if 'user' in session:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember') == 'on'
        
        if not username or not password:
            flash('请输入用户名和密码', 'danger')
            return render_template('login.html')
            
        success, result = user_manager.login(username, password, remember)
        
        if success:
            # 设置会话
            session['user'] = {
                'id': result['id'],
                'username': result['username'],
                'is_admin': result['is_admin']
            }
            session['session_token'] = result['session_token']
            
            if remember:
                session.permanent = True
                
            next_url = request.args.get('next') or url_for('index')
            flash(f'欢迎回来, {result["username"]}!', 'success')
            return redirect(next_url)
        else:
            flash(result, 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """用户登出"""
    if 'session_token' in session:
        user_manager.logout(session['session_token'])
    
    # 清除会话
    session.pop('user', None)
    session.pop('session_token', None)
    flash('您已成功登出', 'success')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    """用户注册页面"""
    # 如果用户已登录，重定向到首页
    if 'user' in session:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        success, message = user_manager.register_user(
            username, email, password, confirm_password
        )
        
        if success:
            flash('注册成功，请登录', 'success')
            return redirect(url_for('login'))
        else:
            flash(message, 'danger')
    
    return render_template('register.html')

@app.route('/profile')
@login_required
def profile():
    """用户资料页面"""
    user_id = session['user']['id']
    user_profile = user_manager.get_user_profile(user_id)
    
    if not user_profile:
        flash('获取用户资料失败', 'danger')
        return redirect(url_for('index'))
        
    return render_template('profile.html', profile=user_profile)

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """编辑用户资料"""
    user_id = session['user']['id']
    
    if request.method == 'POST':
        profile_data = {
            'display_name': request.form.get('display_name'),
            'email': request.form.get('email'),
            'bio': request.form.get('bio')
        }
        
        # 处理密码更新
        if request.form.get('new_password'):
            profile_data.update({
                'current_password': request.form.get('current_password'),
                'new_password': request.form.get('new_password')
            })
        
        # 处理偏好行业
        if 'preferred_industries' in request.form:
            profile_data['preferred_industries'] = request.form.get('preferred_industries').split(',')
        
        success, message = user_manager.update_profile(user_id, profile_data)
        
        if success:
            flash('资料更新成功', 'success')
            return redirect(url_for('profile'))
        else:
            flash(message, 'danger')
    
    # 获取当前资料
    user_profile = user_manager.get_user_profile(user_id)
    
    if not user_profile:
        flash('获取用户资料失败', 'danger')
        return redirect(url_for('index'))
        
    # 获取所有可用行业
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT industry FROM reports WHERE industry IS NOT NULL AND industry != ""')
    all_industries = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    return render_template('edit_profile.html', profile=user_profile, all_industries=all_industries)

# 管理员路由
@app.route('/admin/users')
@admin_required
def admin_users():
    """用户管理页面（管理员）"""
    page = request.args.get('page', 1, type=int)
    result = user_manager.list_users(page=page)
    
    return render_template('admin_users.html', users=result)

@app.route('/admin/user/<int:user_id>/toggle_status', methods=['POST'])
@admin_required
def toggle_user_status(user_id):
    """切换用户状态（激活/禁用）"""
    is_active = request.form.get('is_active') == 'true'
    success = user_manager.change_user_status(user_id, is_active)
    
    if success:
        status = "激活" if is_active else "禁用"
        flash(f'用户已{status}', 'success')
    else:
        flash('操作失败', 'danger')
        
    return redirect(url_for('admin_users'))

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

# 初始化推荐引擎
recommendation_engine = RecommendationEngine()

# 首页路由 - 展示研报列表
@app.route('/')
def index():
    """首页"""
    # 获取当前用户ID
    user_id = session.get('user', {}).get('id', 1)
    
    # 获取推荐研报
    recommendations = recommendation_engine.get_recommendations(user_id=user_id, limit=5)
    
    # 为每个推荐研报添加已读状态
    for report in recommendations:
        report['is_read'] = recommendation_engine.check_is_read(report['id'], user_id=user_id)
    
    # 获取所有研报
    reports = load_reports_from_db()
    
    # 获取顶部推荐（用于弹窗）
    top_recommendation = recommendations[0] if recommendations else None
    
    return render_template('index.html', 
                          reports=reports, 
                          recommendations=recommendations,
                          top_recommendation=top_recommendation)

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
    
    # 获取当前用户ID
    user_id = session.get('user', {}).get('id', 1)
    
    # 检查研报是否已读
    report_dict['is_read'] = recommendation_engine.check_is_read(report_id, user_id=user_id)
    
    # 如果用户已登录，自动将研报标记为已读
    if 'user' in session:
        # 检查用户偏好设置中是否启用了自动标记已读
        auto_mark_read = True  # 默认启用
        user_preferences = preference_manager.get_user_preferences(user_id, 'recommendation')
        if user_preferences:
            auto_mark_read = user_preferences.get('auto_mark_read', True)
            
        # 如果启用了自动标记已读，且研报尚未标记为已读
        if auto_mark_read:
            if not report_dict['is_read']:
                # 首次阅读，标记为已读
                recommendation_engine.mark_as_read(report_id, user_id=user_id)
            # 注意：不再在这里设置默认阅读时长，改为由前端JS实际记录阅读时长
    
    # 获取分析结果
    analysis_db = AnalysisDatabase()
    deepseek_analysis = analysis_db.get_analysis_by_report_id(report_id, analyzer_type='deepseek')
    
    # 如果没有分析结果，创建默认占位结果以避免前端错误
    if not deepseek_analysis:
        # 记录缺少分析结果的情况，但不在页面上显示错误
        logger.info(f"研报ID {report_id} 没有找到分析结果，将使用占位数据")
        
        # 创建默认的分析结果结构
        default_analysis = {
            'id': None,
            'report_id': report_id,
            'analyzer_type': 'placeholder',
            'completeness_score': 0,
            'evaluation': f"该研报《{report_dict.get('title', '未知标题')}》尚未分析，请点击分析按钮进行分析。",
            'one_line_summary': '暂无分析结果',
            'full_analysis': '尚未对该研报进行分析，请点击页面上的分析按钮开始分析。',
            'created_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'steps': {
                '信息': {'found': False, 'description': '暂无分析', 'step_score': 0, 'framework_summary': ''},
                '逻辑': {'found': False, 'description': '暂无分析', 'step_score': 0, 'framework_summary': ''},
                '超预期': {'found': False, 'description': '暂无分析', 'step_score': 0, 'framework_summary': ''},
                '催化剂': {'found': False, 'description': '暂无分析', 'step_score': 0, 'framework_summary': ''},
                '结论': {'found': False, 'description': '暂无分析', 'step_score': 0, 'framework_summary': ''}
            },
            'improvement_suggestions': []
        }
        
        # 设置分析结果
        deepseek_analysis = default_analysis
    
    return render_template(
        'report_detail.html', 
        report=report_dict,
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
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT * FROM reports ORDER BY id DESC
        ''')
        
        reports = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        # 初始化分析数据库
        analysis_db = AnalysisDatabase()
        
        # 对每个研报添加分析结果
        for report in reports:
            report_id = report["id"]
            
            # 获取分析结果
            analysis = analysis_db.get_analysis_by_report_id(report_id)
            
            if analysis:
                # 构建分析结构
                report["analysis"] = {
                    "steps": analysis.get("steps", {}),
                    "summary": {
                        "completeness_score": analysis.get("completeness_score", 0),
                        "completeness_description": get_completeness_description(analysis.get("completeness_score", 0)),
                        "improvement_suggestions": "建议请参考详细分析页面",
                        "one_line_summary": analysis.get("one_line_summary", "")
                    }
                }
            else:
                # 创建默认分析结构
                report["analysis"] = {
                    "steps": {
                        "信息": {"found": False, "step_score": 0},
                        "逻辑": {"found": False, "step_score": 0},
                        "超预期": {"found": False, "step_score": 0},
                        "催化剂": {"found": False, "step_score": 0},
                        "结论": {"found": False, "step_score": 0}
                    },
                    "summary": {
                        "completeness_score": 0,
                        "completeness_description": "尚未分析",
                        "improvement_suggestions": "尚未分析",
                        "one_line_summary": "尚未分析"
                    }
                }
            
            # 确保报告有内容字段
            report["content"] = report.get("full_content", report.get("content_preview", ""))
            
        return reports
    except Exception as e:
        logger.error(f"从数据库加载研报数据出错: {e}")
        return []

def get_completeness_description(score):
    """根据完整性分数提供评估描述"""
    if score is None:
        score = 0
    elif not isinstance(score, (int, float)):
        try:
            score = int(score)
        except (ValueError, TypeError):
            score = 0
    
    if score >= 80:
        return "该研报对五步法的应用非常完善，几乎涵盖了所有分析要素，分析深入全面，投资建议有充分依据。"
    elif score >= 60:
        return "该研报对五步法的应用较为完善，涵盖了大部分分析要素，分析较为深入，投资建议有一定依据。"
    elif score >= 40:
        return "该研报对五步法的应用一般，部分分析要素有所欠缺，分析深度不足，投资建议缺乏充分依据。"
    else:
        return "该研报对五步法的应用不足，多数分析要素缺失，分析浅显，投资建议依据不足。"

@app.route('/analyze/<int:report_id>')
def analyze_report(report_id):
    """分析研报"""
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
        # 使用DeepSeek分析器
        from deepseek_analyzer import DeepSeekAnalyzer
        analyzer = DeepSeekAnalyzer()
        analysis_result = analyzer.analyze_with_five_steps(title, content, industry)
        
        # 保存分析结果到数据库
        analysis_db = AnalysisDatabase()
        analysis_db.save_analysis_result(report_id, analysis_result, analyzer_type='deepseek')
        
        flash('使用DeepSeek分析完成', 'success')
    except Exception as e:
        flash(f'分析失败: {str(e)}', 'error')
    
    return redirect(url_for('report_detail', report_id=report_id))

@app.route('/generate_video_script/<int:report_id>')
def generate_video_script(report_id):
    """生成研报的视频文案"""
    logger.info(f"开始为研报ID {report_id} 生成视频文案")
    
    # 从数据库获取研报信息
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT * FROM reports WHERE id = ?
    ''', (report_id,))
    
    report = cursor.fetchone()
    conn.close()
    
    if not report:
        logger.error(f"未找到研报ID {report_id}")
        flash('未找到研报', 'error')
        return redirect(url_for('index'))
    
    # 转换为字典
    report_info = dict(report)
    logger.info(f"获取到研报信息: {report_info['title']}")
    
    # 获取分析结果
    analysis_db = AnalysisDatabase()
    analysis_result = analysis_db.get_analysis_by_report_id(report_id, analyzer_type='deepseek')
    
    if not analysis_result:
        logger.warning(f"研报ID {report_id} 尚未进行分析")
        flash('请先进行研报分析', 'warning')
        return redirect(url_for('report_detail', report_id=report_id))
    
    try:
        # 使用DeepSeek生成视频文案
        from deepseek_analyzer import DeepSeekAnalyzer
        analyzer = DeepSeekAnalyzer()
        logger.info("调用DeepSeek生成视频文案")
        video_script = analyzer.generate_video_script(report_info, analysis_result)
        
        if video_script and video_script != "无法生成视频文案: API密钥未配置":
            # 保存视频文案到数据库
            logger.info("成功生成视频文案，正在保存到数据库")
            script_id = analysis_db.save_video_script(report_id, video_script)
            if script_id:
                logger.info(f"视频文案已保存，ID: {script_id}")
                flash('视频文案生成完成', 'success')
            else:
                logger.error("保存视频文案到数据库失败")
                flash('视频文案生成成功，但保存失败', 'warning')
        else:
            logger.error(f"视频文案生成失败: {video_script}")
            flash('视频文案生成失败: API密钥未配置或生成内容为空', 'error')
    except Exception as e:
        logger.exception(f"生成视频文案时出错: {str(e)}")
        flash(f'生成视频文案失败: {str(e)}', 'error')
    
    return redirect(url_for('report_detail', report_id=report_id))

@app.route('/get_video_script/<int:report_id>')
def get_video_script(report_id):
    """获取研报的视频文案"""
    try:
        # 从数据库中获取视频文案
        video_script = analysis_db.get_video_script(report_id)
        
        if not video_script:
            return jsonify({"success": False, "message": "未找到视频文案"})
        
        logger.info(f"成功获取视频文案，长度: {len(video_script)}")
        return jsonify({"success": True, "message": "获取成功", "script": video_script})
    except Exception as e:
        logger.error(f"获取视频文案时出错: {str(e)}")
        return jsonify({"success": False, "message": f"获取视频文案时出错: {str(e)}"})

@app.route('/video_scripts')
def video_scripts_page():
    """显示所有视频脚本页面"""
    try:
        # 从数据库获取所有视频脚本
        scripts = analysis_db.get_all_video_scripts()
        
        # 渲染视频脚本页面
        return render_template('video_scripts.html', scripts=scripts)
    except Exception as e:
        logger.error(f"加载视频脚本页面时出错: {str(e)}")
        return render_template('error.html', error=str(e))

@app.route('/api/video_scripts')
def get_all_video_scripts():
    """API端点：获取所有视频脚本"""
    try:
        scripts = analysis_db.get_all_video_scripts()
        return jsonify({"success": True, "scripts": scripts})
    except Exception as e:
        logger.error(f"获取所有视频脚本时出错: {str(e)}")
        return jsonify({"success": False, "message": str(e)})

@app.route('/mark_read/<int:report_id>')
@login_required
def mark_read(report_id):
    """标记研报为已读"""
    user_id = session['user']['id']
    success = recommendation_engine.mark_as_read(report_id, user_id=user_id)
    if success:
        flash('已标记为已读', 'success')
    else:
        flash('标记失败', 'error')
    return redirect(url_for('report_detail', report_id=report_id))

@app.route('/mark_not_interested/<int:report_id>')
@login_required
def mark_not_interested(report_id):
    """标记为不感兴趣"""
    user_id = session['user']['id']
    success = recommendation_engine.mark_as_read(report_id, user_id=user_id, status='not_interested')
    if success:
        flash('已标记为不感兴趣', 'success')
    else:
        flash('标记失败', 'error')
    return redirect(url_for('index'))

@app.route('/recommendation_settings')
@login_required
def recommendation_settings():
    """
    旧的推荐设置页面，现在重定向到新的用户偏好设置页面。
    """
    flash('推荐设置已移动到新的 "用户偏好设置" 页面。', 'info')
    return redirect(url_for('user_preferences', tab='recommendation'))

@app.route('/user/preferences', methods=['GET', 'POST'])
@login_required
def user_preferences():
    """用户偏好设置页面"""
    user_id = session['user']['id']
    
    if request.method == 'POST':
        form_type = request.form.get('form_type')
        
        if form_type == 'recommendation':
            # 处理推荐设置
            preferences = {
                'weight_score': int(request.form.get('weight_score', 40)),
                'weight_time': int(request.form.get('weight_time', 30)),
                'weight_industry': int(request.form.get('weight_industry', 30)),
                'focused_industries': request.form.getlist('focused_industries'),
                'preferred_report_types': request.form.getlist('preferred_report_types'),
                'followed_organizations': request.form.getlist('followed_organizations'),
                'show_recommendations': request.form.get('show_recommendations') == 'on',
                'show_recommendation_modal': request.form.get('show_recommendation_modal') == 'on',
                'auto_mark_read': request.form.get('auto_mark_read') == 'on'
            }
            
            success, message = preference_manager.update_user_preferences(user_id, 'recommendation', preferences)
            
        elif form_type == 'notification':
            # 处理通知设置
            settings = {
                'email': request.form.get('email_notifications') == 'on',
                'site': request.form.get('site_notifications') == 'on',
                'new_reports': request.form.get('notify_new_reports') == 'on',
                'industry_reports': request.form.get('notify_industry_reports') == 'on',
                'high_quality': request.form.get('notify_high_quality') == 'on'
            }
            
            success, message = preference_manager.update_notification_settings(user_id, settings)
            
        elif form_type == 'reading':
            # 处理阅读偏好
            preferences = {
                'default_view': request.form.get('default_view', 'card'),
                'reports_per_page': int(request.form.get('reports_per_page', 20)),
                'default_sort': request.form.get('default_sort', 'date'),
                'sort_desc': request.form.get('sort_desc') == 'on',
                'auto_expand_summary': request.form.get('auto_expand_summary') == 'on',
                'auto_expand_analysis': request.form.get('auto_expand_analysis') == 'on'
            }
            
            success, message = preference_manager.update_user_preferences(user_id, 'reading', preferences)
            
        elif form_type == 'privacy':
            # 处理隐私设置
            preferences = {
                'collect_reading_history': request.form.get('collect_reading_history') == 'on',
                'collect_search_history': request.form.get('collect_search_history') == 'on',
                'show_profile': request.form.get('show_profile') == 'on',
                'show_reading_history': request.form.get('show_reading_history') == 'on'
            }
            
            success, message = preference_manager.update_user_preferences(user_id, 'privacy', preferences)
            
        else:
            success = False
            message = "未知的设置类型"
        
        if success:
            flash(message, 'success')
        else:
            flash(message, 'danger')
        
        # 重定向到当前页面，但添加标签页参数
        return redirect(url_for('user_preferences', tab=form_type))
    
    # 获取用户的所有偏好设置
    settings = preference_manager.get_user_preferences(user_id, 'recommendation')
    reading_preferences = preference_manager.get_user_preferences(user_id, 'reading')
    privacy_settings = preference_manager.get_user_preferences(user_id, 'privacy')
    notification_settings = preference_manager.get_notification_settings(user_id)
    
    # 获取用户偏好
    user_preferences = {
        'show_recommendations': settings.get('show_recommendations', True),
        'show_recommendation_modal': settings.get('show_recommendation_modal', True),
        'auto_mark_read': settings.get('auto_mark_read', True)
    }
    
    # 获取所有可用行业和机构
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT industry FROM reports WHERE industry IS NOT NULL AND industry != "" ORDER BY industry')
    all_industries = [row[0] for row in cursor.fetchall()]
    cursor.execute('SELECT DISTINCT org FROM reports WHERE org IS NOT NULL AND org != "" ORDER BY org')
    all_organizations = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    return render_template('preferences.html', 
                          settings=settings,
                          reading_preferences=reading_preferences,
                          privacy_settings=privacy_settings,
                          notification_settings=notification_settings,
                          user_preferences=user_preferences,
                          all_industries=all_industries,
                          all_organizations=all_organizations)

@app.route('/user/reading_history')
@login_required
def reading_history():
    """用户阅读历史页面"""
    user_id = session['user']['id']
    
    # 获取分页参数
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # 获取排序和筛选参数
    sort = request.args.get('sort', 'recent')
    filter_type = request.args.get('filter', 'all')
    
    # 计算偏移量
    offset = (page - 1) * per_page
    
    # 构建查询参数
    params = {'user_id': user_id, 'limit': per_page, 'offset': offset}
    
    # 获取阅读历史
    history = preference_manager.get_reading_history(
        user_id=user_id,
        limit=per_page,
        offset=offset,
        sort_by=sort,
        filter_by=filter_type
    )
    
    # 获取总记录数
    total_records = preference_manager.get_reading_history_count(user_id, filter_by=filter_type)
    
    # 计算总页数
    total_pages = (total_records + per_page - 1) // per_page
    
    return render_template('reading_history.html',
                          history=history,
                          page=page,
                          total_pages=total_pages,
                          sort=sort,
                          filter=filter_type)

@app.route('/user/clear_reading_history', methods=['POST'])
@login_required
def clear_reading_history():
    """清除用户阅读历史"""
    user_id = session['user']['id']
    success, message = preference_manager.clear_reading_history(user_id)
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    # 检查请求来源
    referer = request.referrer
    if referer and 'reading_history' in referer:
        return redirect(url_for('reading_history'))
    else:
        return redirect(url_for('user_preferences', tab='data-settings'))

@app.route('/user/clear_search_history', methods=['POST'])
@login_required
def clear_search_history():
    """清除用户搜索历史"""
    user_id = session['user']['id']
    success, message = preference_manager.clear_search_history(user_id)
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
        
    return redirect(url_for('user_preferences', tab='data-settings'))

@app.route('/user/export_data')
@login_required
def export_user_data():
    """导出用户数据"""
    user_id = session['user']['id']
    data = preference_manager.export_user_data(user_id)
    
    # 将数据转换为JSON并作为下载文件返回
    from flask import Response
    
    username = session['user']['username']
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    filename = f"{username}_data_export_{timestamp}.json"
    
    return Response(
        json.dumps(data, ensure_ascii=False, indent=2),
        mimetype='application/json',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )

@app.route('/my_data')
@login_required
def my_data():
    """显示用户的个人阅读数据报告页面"""
    user_id = session['user']['id']
    
    # 获取阅读习惯统计数据
    stats = preference_manager.get_reading_habit_stats(user_id)
    
    return render_template('my_data.html', stats=stats)

@app.route('/user/export_reading_history')
@login_required
def export_reading_history():
    """导出用户阅读历史，支持CSV和JSON格式"""
    user_id = session['user']['id']
    format_type = request.args.get('format', 'csv')  # 默认为CSV格式
    
    # 获取用户名和时间戳
    username = session['user']['username']
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    
    # 获取阅读历史
    history = preference_manager.get_reading_history(
        user_id=user_id,
        limit=1000,  # 设置一个较大的限制
        offset=0,
        sort_by='recent'
    )
    
    if not history:
        flash('没有阅读历史记录可导出', 'info')
        return redirect(url_for('reading_history'))
    
    from flask import Response
    import io
    import csv
    
    if format_type == 'csv':
        # 准备CSV数据
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 写入CSV头部
        writer.writerow(['报告标题', '行业', '阅读时间', '阅读时长(秒)', '状态', '报告ID'])
        
        # 写入数据行
        for item in history:
            status = '已完成' if item['is_completed'] else '未完成'
            writer.writerow([
                item['title'],
                item['industry'],
                item['read_at'],
                item['read_duration'],
                status,
                item['report_id']
            ])
        
        # 创建响应
        output.seek(0)
        filename = f"{username}_reading_history_{timestamp}.csv"
        return Response(
            output.getvalue(),
            mimetype='text/csv; charset=utf-8',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )
    else:
        # JSON格式
        filename = f"{username}_reading_history_{timestamp}.json"
        return Response(
            json.dumps(history, ensure_ascii=False, indent=2),
            mimetype='application/json',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )

@app.route('/user/delete_account', methods=['POST'])
@login_required
def delete_account():
    """删除用户账户"""
    user_id = session['user']['id']
    password = request.form.get('password')
    confirm_delete = request.form.get('confirm_delete') == 'on'
    
    if not confirm_delete:
        flash('请确认您要删除账户', 'danger')
        return redirect(url_for('user_preferences', tab='data-settings'))
    
    # 验证密码
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT password_hash, salt FROM users WHERE id = ?', (user_id,))
    user_data = cursor.fetchone()
    conn.close()
    
    if not user_data:
        flash('用户不存在', 'danger')
        return redirect(url_for('user_preferences', tab='data-settings'))
    
    import hashlib
    password_hash = hashlib.sha256((password + user_data['salt']).encode()).hexdigest()
    
    if password_hash != user_data['password_hash']:
        flash('密码不正确', 'danger')
        return redirect(url_for('user_preferences', tab='data-settings'))
    
    # 删除用户数据
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 开始事务
        cursor.execute('BEGIN TRANSACTION')
        
        # 删除用户相关数据
        cursor.execute('DELETE FROM reading_history WHERE user_id = ?', (user_id,))
        cursor.execute('DELETE FROM search_history WHERE user_id = ?', (user_id,))
        cursor.execute('DELETE FROM user_preferences WHERE user_id = ?', (user_id,))
        cursor.execute('DELETE FROM sessions WHERE user_id = ?', (user_id,))
        cursor.execute('DELETE FROM user_profiles WHERE user_id = ?', (user_id,))
        cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
        
        # 提交事务
        cursor.execute('COMMIT')
        
        # 清除会话
        session.pop('user', None)
        session.pop('session_token', None)
        
        flash('您的账户已成功删除', 'success')
        return redirect(url_for('index'))
        
    except Exception as e:
        cursor.execute('ROLLBACK')
        flash(f'删除账户失败: {str(e)}', 'danger')
        return redirect(url_for('user_preferences', tab='data-settings'))
    finally:
        conn.close()

@app.route('/update_reading_duration/<int:report_id>', methods=['POST'])
@login_required
def update_reading_duration(report_id):
    """更新研报阅读时长"""
    user_id = session['user']['id']
    
    # 从请求中获取阅读时长和完成状态
    data = request.json
    duration = data.get('duration', 0)
    is_completed = data.get('is_completed', False)
    
    print(f"接收到阅读时长更新请求: 用户={user_id}, 报告={report_id}, 时长={duration}秒, 完成={is_completed}")
    
    # 使用preference_manager更新阅读记录
    success = preference_manager.record_reading_history(
        user_id=user_id,
        report_id=report_id,
        duration=duration,
        is_completed=is_completed
    )
    
    if success:
        return jsonify({"success": True, "duration": duration})
    else:
        return jsonify({"success": False, "message": "Failed to update reading duration"}), 500

if __name__ == '__main__':
    # 初始化应用
    init_app()
    
    # 查找可用端口
    port = find_available_port()
    print(f"启动Flask应用，使用端口: {port}")
    app.run(debug=True, port=port) 