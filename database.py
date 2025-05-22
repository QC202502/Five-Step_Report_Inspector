# -*- coding: utf-8 -*-
import sqlite3
import json
import os
import time
from datetime import datetime

# 数据库文件名
DB_FILE = 'research_reports.db'

def get_db_connection():
    """
    获取数据库连接
    """
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # 使结果以字典形式返回
    return conn

def init_db():
    """
    初始化数据库表结构
    """
    conn = get_db_connection()
    try:
        # 创建研报表
        conn.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            link TEXT UNIQUE NOT NULL,
            abstract TEXT,
            content_preview TEXT,
            full_content TEXT,
            industry TEXT,
            rating TEXT,
            org TEXT,
            date TEXT,
            analysis_method TEXT,
            completeness_score INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        ''')
        
        # 创建分析结果表
        conn.execute('''
        CREATE TABLE IF NOT EXISTS analysis_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER NOT NULL,
            step_name TEXT NOT NULL,
            found INTEGER NOT NULL,
            keywords TEXT,
            evidence TEXT,
            description TEXT,
            FOREIGN KEY (report_id) REFERENCES reports (id),
            UNIQUE (report_id, step_name)
        )
        ''')
        
        conn.commit()
        print("数据库初始化成功")
    except Exception as e:
        print(f"初始化数据库出错: {e}")
    finally:
        conn.close()

def save_report_to_db(report_data):
    """
    保存单条研报及其分析结果到数据库
    
    参数:
    report_data (dict): 包含研报信息和分析结果的字典
    
    返回:
    int: 插入的研报ID，如果失败则返回-1
    """
    conn = get_db_connection()
    try:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 提取分析摘要
        completeness_score = report_data.get('analysis', {}).get('summary', {}).get('completeness_score', 0)
        
        # 插入研报数据
        cursor = conn.cursor()
        cursor.execute('''
        INSERT OR REPLACE INTO reports (
            title, link, abstract, content_preview, full_content, 
            industry, rating, org, date, analysis_method, 
            completeness_score, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            report_data.get('title', 'N/A'),
            report_data.get('link', 'N/A'),
            report_data.get('abstract', ''),
            report_data.get('content_preview', ''),
            report_data.get('full_content', ''),
            report_data.get('industry', '未知'),
            report_data.get('rating', ''),
            report_data.get('org', ''),
            report_data.get('date', ''),
            report_data.get('analysis_method', ''),
            completeness_score,
            now,
            now
        ))
        
        # 获取插入的研报ID
        report_id = cursor.lastrowid
        
        # 插入分析结果
        analysis = report_data.get('analysis', {})
        for step in ['信息', '逻辑', '超预期', '催化剂', '结论']:
            if step in analysis:
                step_data = analysis[step]
                keywords_json = json.dumps(step_data.get('keywords', []), ensure_ascii=False)
                evidence_json = json.dumps(step_data.get('evidence', []), ensure_ascii=False)
                
                conn.execute('''
                INSERT OR REPLACE INTO analysis_results (
                    report_id, step_name, found, keywords, evidence, description
                ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    report_id,
                    step,
                    1 if step_data.get('found', False) else 0,
                    keywords_json,
                    evidence_json,
                    step_data.get('description', '')
                ))
        
        conn.commit()
        print(f"成功保存研报到数据库: {report_data.get('title')}")
        return report_id
    except Exception as e:
        conn.rollback()
        print(f"保存研报到数据库时出错: {e}")
        return -1
    finally:
        conn.close()

def save_reports_to_db(reports):
    """
    批量保存研报列表到数据库
    
    参数:
    reports (list): 研报数据列表
    
    返回:
    int: 成功保存的研报数量
    """
    success_count = 0
    for report in reports:
        if save_report_to_db(report) > 0:
            success_count += 1
    return success_count

def get_reports_from_db(limit=100, offset=0):
    """
    从数据库获取研报列表
    
    参数:
    limit (int): 结果限制数量
    offset (int): 结果偏移量
    
    返回:
    list: 研报数据列表
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # 获取研报基本数据
        reports = []
        rows = cursor.execute('''
        SELECT * FROM reports
        ORDER BY id DESC
        LIMIT ? OFFSET ?
        ''', (limit, offset)).fetchall()
        
        for row in rows:
            report = dict(row)
            
            # 获取研报的分析结果
            analysis_rows = cursor.execute('''
            SELECT * FROM analysis_results
            WHERE report_id = ?
            ''', (row['id'],)).fetchall()
            
            analysis = {}
            for ar in analysis_rows:
                step_name = ar['step_name']
                analysis[step_name] = {
                    'found': bool(ar['found']),
                    'keywords': json.loads(ar['keywords']),
                    'evidence': json.loads(ar['evidence']),
                    'description': ar['description']
                }
            
            # 添加摘要数据
            analysis['summary'] = {
                'completeness_score': report['completeness_score'],
                'steps_found': sum(1 for step in analysis.values() if step.get('found', False)),
                'evaluation': get_evaluation_text(report['completeness_score'])
            }
            
            # 移除数据库ID，并添加分析结果
            del report['id']
            report['analysis'] = analysis
            reports.append(report)
            
        return reports
    except Exception as e:
        print(f"从数据库获取研报列表时出错: {e}")
        return []
    finally:
        conn.close()

def get_report_by_id(report_id):
    """
    通过ID从数据库获取单条研报
    
    参数:
    report_id (int): 研报ID
    
    返回:
    dict: 研报数据，若不存在则返回None
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # 获取研报基本数据
        row = cursor.execute('SELECT * FROM reports WHERE id = ?', (report_id,)).fetchone()
        if not row:
            return None
            
        report = dict(row)
        
        # 获取研报的分析结果
        analysis_rows = cursor.execute('SELECT * FROM analysis_results WHERE report_id = ?', (report_id,)).fetchall()
        
        analysis = {}
        for ar in analysis_rows:
            step_name = ar['step_name']
            analysis[step_name] = {
                'found': bool(ar['found']),
                'keywords': json.loads(ar['keywords']),
                'evidence': json.loads(ar['evidence']),
                'description': ar['description']
            }
        
        # 添加摘要数据
        analysis['summary'] = {
            'completeness_score': report['completeness_score'],
            'steps_found': sum(1 for step in analysis.values() if step.get('found', False)),
            'evaluation': get_evaluation_text(report['completeness_score'])
        }
        
        # 移除数据库ID，并添加分析结果
        db_id = report['id']
        del report['id']
        report['analysis'] = analysis
        report['db_id'] = db_id  # 保留数据库ID作为单独字段
        
        return report
    except Exception as e:
        print(f"从数据库获取研报时出错: {e}")
        return None
    finally:
        conn.close()

def get_reports_by_industry(industry, limit=100):
    """
    通过行业分类获取研报列表
    
    参数:
    industry (str): 行业名称
    limit (int): 结果限制数量
    
    返回:
    list: 研报数据列表
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # 获取研报基本数据
        rows = cursor.execute('''
        SELECT * FROM reports
        WHERE industry = ?
        ORDER BY id DESC
        LIMIT ?
        ''', (industry, limit)).fetchall()
        
        reports = []
        for row in rows:
            report = dict(row)
            
            # 获取研报的分析结果
            analysis_rows = cursor.execute('''
            SELECT * FROM analysis_results
            WHERE report_id = ?
            ''', (row['id'],)).fetchall()
            
            analysis = {}
            for ar in analysis_rows:
                step_name = ar['step_name']
                analysis[step_name] = {
                    'found': bool(ar['found']),
                    'keywords': json.loads(ar['keywords']),
                    'evidence': json.loads(ar['evidence']),
                    'description': ar['description']
                }
            
            # 添加摘要数据
            analysis['summary'] = {
                'completeness_score': report['completeness_score'],
                'steps_found': sum(1 for step in analysis.values() if step.get('found', False)),
                'evaluation': get_evaluation_text(report['completeness_score'])
            }
            
            # 移除数据库ID，并添加分析结果
            del report['id']
            report['analysis'] = analysis
            reports.append(report)
            
        return reports
    except Exception as e:
        print(f"获取行业研报列表时出错: {e}")
        return []
    finally:
        conn.close()

def search_reports(keyword, limit=100):
    """
    搜索研报
    
    参数:
    keyword (str): 搜索关键词
    limit (int): 结果限制数量
    
    返回:
    list: 搜索结果列表
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # 构建搜索模式
        search_pattern = f"%{keyword}%"
        
        # 搜索研报
        rows = cursor.execute('''
        SELECT * FROM reports
        WHERE title LIKE ? OR abstract LIKE ? OR industry LIKE ? OR full_content LIKE ?
        ORDER BY id DESC
        LIMIT ?
        ''', (search_pattern, search_pattern, search_pattern, search_pattern, limit)).fetchall()
        
        reports = []
        for row in rows:
            report = dict(row)
            
            # 获取研报的分析结果
            analysis_rows = cursor.execute('''
            SELECT * FROM analysis_results
            WHERE report_id = ?
            ''', (row['id'],)).fetchall()
            
            analysis = {}
            for ar in analysis_rows:
                step_name = ar['step_name']
                analysis[step_name] = {
                    'found': bool(ar['found']),
                    'keywords': json.loads(ar['keywords']),
                    'evidence': json.loads(ar['evidence']),
                    'description': ar['description']
                }
            
            # 添加摘要数据
            analysis['summary'] = {
                'completeness_score': report['completeness_score'],
                'steps_found': sum(1 for step in analysis.values() if step.get('found', False)),
                'evaluation': get_evaluation_text(report['completeness_score'])
            }
            
            # 移除数据库ID，并添加分析结果
            del report['id']
            report['analysis'] = analysis
            reports.append(report)
            
        return reports
    except Exception as e:
        print(f"搜索研报时出错: {e}")
        return []
    finally:
        conn.close()

def count_reports():
    """
    获取数据库中研报总数
    
    返回:
    int: 研报总数
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        result = cursor.execute('SELECT COUNT(*) as count FROM reports').fetchone()
        return result['count']
    except Exception as e:
        print(f"获取研报总数时出错: {e}")
        return 0
    finally:
        conn.close()

def import_from_json(json_file='research_reports.json'):
    """
    从JSON文件导入研报数据到数据库
    
    参数:
    json_file (str): JSON文件路径
    
    返回:
    int: 成功导入的研报数量
    """
    if not os.path.exists(json_file):
        print(f"文件 {json_file} 不存在")
        return 0
        
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            reports = json.load(f)
            
        if not reports:
            print("JSON文件中没有找到研报数据")
            return 0
            
        # 初始化数据库（如果尚未初始化）
        init_db()
        
        # 保存研报到数据库
        success_count = save_reports_to_db(reports)
        print(f"成功从JSON导入了 {success_count} 条研报到数据库")
        return success_count
    except Exception as e:
        print(f"从JSON导入数据时出错: {e}")
        return 0

def export_to_json(json_file='exported_reports.json'):
    """
    导出数据库中的研报数据到JSON文件
    
    参数:
    json_file (str): 导出的JSON文件路径
    
    返回:
    bool: 是否成功导出
    """
    try:
        reports = get_reports_from_db(limit=1000)  # 获取最多1000条数据
        if not reports:
            print("数据库中没有研报数据可导出")
            return False
            
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(reports, f, ensure_ascii=False, indent=4)
            
        print(f"成功导出 {len(reports)} 条研报数据到 {json_file}")
        return True
    except Exception as e:
        print(f"导出研报数据到JSON时出错: {e}")
        return False

# 辅助函数，与main.py中相同
def get_evaluation_text(score):
    """根据完整度分数生成评价文本"""
    if score >= 90:
        return "研报非常完整地应用了五步分析法，包含了全面的分析要素"
    elif score >= 80:
        return "研报较好地应用了五步分析法，大部分分析要素齐全"
    elif score >= 60:
        return "研报部分应用了五步分析法，关键分析要素有所欠缺"
    elif score >= 40:
        return "研报仅包含少量五步分析法要素，分析不够全面"
    else:
        return "研报几乎未应用五步分析法，分析要素严重不足"

# 初始化数据库
if __name__ == "__main__":
    init_db()
    
    # 如果存在JSON文件，导入到数据库
    if os.path.exists('research_reports.json'):
        import_from_json() 