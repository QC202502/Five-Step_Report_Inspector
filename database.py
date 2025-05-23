# -*- coding: utf-8 -*-
import sqlite3
import json
import os
import time
from datetime import datetime
import re

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
            full_content TEXT, -- SQLite的TEXT类型没有长度限制，可以存储大量文本
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
            keywords TEXT, -- 可以存储JSON格式的关键词列表
            evidence TEXT, -- 可以存储JSON格式的证据列表
            description TEXT, -- 详细描述，支持长文本
            framework_summary TEXT, -- 五步框架梳理中的核心内容提炼
            improvement_suggestions TEXT, -- 可操作补强思路
            step_score INTEGER, -- 该步骤的分数
            FOREIGN KEY (report_id) REFERENCES reports (id),
            UNIQUE (report_id, step_name)
        )
        ''')
        
        # 创建报告完整分析表，用于存储完整的Claude分析文本
        conn.execute('''
        CREATE TABLE IF NOT EXISTS report_full_analysis (
            report_id INTEGER PRIMARY KEY,
            full_analysis_text TEXT, -- 完整的Claude分析文本
            one_line_summary TEXT, -- 一句话总结
            FOREIGN KEY (report_id) REFERENCES reports (id)
        )
        ''')
        
        # 尝试添加新列（如果表已存在）
        try:
            # 为已存在的analysis_results表添加新字段
            conn.execute('ALTER TABLE analysis_results ADD COLUMN framework_summary TEXT;')
            conn.execute('ALTER TABLE analysis_results ADD COLUMN improvement_suggestions TEXT;')
            conn.execute('ALTER TABLE analysis_results ADD COLUMN step_score INTEGER;')
            print("成功为analysis_results表添加新字段")
        except Exception as e:
            # 如果列已存在，sqlite会抛出错误
            print(f"添加新列时出现信息（可能列已存在）: {e}")
        
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
        
        # 保存完整分析文本和一句话总结
        full_analysis = report_data.get('full_analysis', '')
        one_line_summary = report_data.get('analysis', {}).get('summary', {}).get('one_line_summary', '')
        
        if full_analysis or one_line_summary:
            cursor.execute('''
            INSERT OR REPLACE INTO report_full_analysis (
                report_id, full_analysis_text, one_line_summary
            ) VALUES (?, ?, ?)
            ''', (
                report_id,
                full_analysis,
                one_line_summary
            ))
        
        # 插入分析结果
        analysis = report_data.get('analysis', {})
        
        # 从Claude结果中提取五步框架梳理和可操作补强思路
        framework_summaries = {}  # 用于存储各步骤的框架摘要
        improvement_suggestions = ""  # 用于存储改进建议
        
        # 尝试从full_analysis中提取框架摘要
        if full_analysis:
            try:
                # 提取框架梳理部分
                framework_section_match = re.search(r'## 五步框架梳理(.*?)##', full_analysis, re.DOTALL)
                if framework_section_match:
                    framework_section = framework_section_match.group(1)
                    steps_mapping = {
                        'Information': '信息',
                        'Logic': '逻辑',
                        'Beyond-Consensus': '超预期',
                        'Catalyst': '催化剂',
                        'Conclusion': '结论'
                    }
                    
                    for eng_name, cn_name in steps_mapping.items():
                        pattern = r'\| ' + re.escape(eng_name) + r' \|(.*?)\|'
                        match = re.search(pattern, framework_section, re.DOTALL)
                        if match:
                            framework_summaries[cn_name] = match.group(1).strip()
                
                # 提取可操作补强思路部分
                suggestions_match = re.search(r'## 可操作补强思路(.*?)##', full_analysis, re.DOTALL)
                if suggestions_match:
                    improvement_suggestions = suggestions_match.group(1).strip()
            except Exception as e:
                print(f"从full_analysis提取框架摘要和改进建议时出错: {e}")
        
        for step in ['信息', '逻辑', '超预期', '催化剂', '结论']:
            if step in analysis:
                step_data = analysis[step]
                keywords_json = json.dumps(step_data.get('keywords', []), ensure_ascii=False)
                evidence_json = json.dumps(step_data.get('evidence', []), ensure_ascii=False)
                
                conn.execute('''
                INSERT OR REPLACE INTO analysis_results (
                    report_id, step_name, found, keywords, evidence, description,
                    framework_summary, improvement_suggestions, step_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    report_id,
                    step,
                    1 if step_data.get('found', False) else 0,
                    keywords_json,
                    evidence_json,
                    step_data.get('description', ''),
                    framework_summaries.get(step, ''),  # 添加框架摘要
                    improvement_suggestions if step == '结论' else '',  # 只在结论步骤保存改进建议
                    step_data.get('step_score', 0)  # 添加步骤评分
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
            report_id = row['id']
            
            # 获取研报的分析结果
            analysis_rows = cursor.execute('''
            SELECT * FROM analysis_results
            WHERE report_id = ?
            ''', (report_id,)).fetchall()
            
            analysis = {}
            for ar in analysis_rows:
                step_name = ar['step_name']
                analysis[step_name] = {
                    'found': bool(ar['found']),
                    'keywords': json.loads(ar['keywords']),
                    'evidence': json.loads(ar['evidence']),
                    'description': ar['description'],
                    'step_score': ar['step_score'] if 'step_score' in ar else 0  # 获取步骤评分
                }
                
                # 获取框架摘要和改进建议（如果存在）
                if 'framework_summary' in ar and ar['framework_summary']:
                    analysis[step_name]['framework_summary'] = ar['framework_summary']
                
                if 'improvement_suggestions' in ar and ar['improvement_suggestions'] and step_name == '结论':
                    analysis['improvement_suggestions'] = ar['improvement_suggestions']
            
            # 获取完整分析文本和一句话总结
            full_analysis_row = cursor.execute('''
            SELECT * FROM report_full_analysis
            WHERE report_id = ?
            ''', (report_id,)).fetchone()
            
            # 添加摘要数据
            analysis['summary'] = {
                'completeness_score': report['completeness_score'],
                'steps_found': sum(1 for step in analysis.values() if isinstance(step, dict) and step.get('found', False)),
                'evaluation': get_evaluation_text(report['completeness_score'])
            }
            
            # 添加一句话总结和完整分析文本（如果存在）
            if full_analysis_row:
                if 'one_line_summary' in full_analysis_row and full_analysis_row['one_line_summary']:
                    analysis['summary']['one_line_summary'] = full_analysis_row['one_line_summary']
                
                if 'full_analysis_text' in full_analysis_row and full_analysis_row['full_analysis_text']:
                    report['full_analysis'] = full_analysis_row['full_analysis_text']
            
            # 不再删除id字段，保留它供app.py使用
            # del report['id']  
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
        db_id = report['id']
        
        # 获取研报的分析结果
        analysis_rows = cursor.execute('SELECT * FROM analysis_results WHERE report_id = ?', (report_id,)).fetchall()
        
        analysis = {}
        for ar in analysis_rows:
            step_name = ar['step_name']
            analysis[step_name] = {
                'found': bool(ar['found']),
                'keywords': json.loads(ar['keywords']),
                'evidence': json.loads(ar['evidence']),
                'description': ar['description'],
                'step_score': ar['step_score'] if 'step_score' in ar else 0  # 获取步骤评分
            }
            
            # 获取框架摘要和改进建议（如果存在）
            if 'framework_summary' in ar and ar['framework_summary']:
                analysis[step_name]['framework_summary'] = ar['framework_summary']
            
            if 'improvement_suggestions' in ar and ar['improvement_suggestions'] and step_name == '结论':
                analysis['improvement_suggestions'] = ar['improvement_suggestions']
        
        # 获取完整分析文本和一句话总结
        full_analysis_row = cursor.execute('''
        SELECT * FROM report_full_analysis
        WHERE report_id = ?
        ''', (report_id,)).fetchone()
        
        # 添加摘要数据
        analysis['summary'] = {
            'completeness_score': report['completeness_score'],
            'steps_found': sum(1 for step in analysis.values() if isinstance(step, dict) and step.get('found', False)),
            'evaluation': get_evaluation_text(report['completeness_score'])
        }
        
        # 添加一句话总结和完整分析文本（如果存在）
        if full_analysis_row:
            if 'one_line_summary' in full_analysis_row and full_analysis_row['one_line_summary']:
                analysis['summary']['one_line_summary'] = full_analysis_row['one_line_summary']
            
            if 'full_analysis_text' in full_analysis_row and full_analysis_row['full_analysis_text']:
                report['full_analysis'] = full_analysis_row['full_analysis_text']
        
        # 移除数据库ID，并添加分析结果
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
            report_id = row['id']
            
            # 获取研报的分析结果
            analysis_rows = cursor.execute('''
            SELECT * FROM analysis_results
            WHERE report_id = ?
            ''', (report_id,)).fetchall()
            
            analysis = {}
            for ar in analysis_rows:
                step_name = ar['step_name']
                analysis[step_name] = {
                    'found': bool(ar['found']),
                    'keywords': json.loads(ar['keywords']),
                    'evidence': json.loads(ar['evidence']),
                    'description': ar['description'],
                    'step_score': ar['step_score'] if 'step_score' in ar else 0  # 获取步骤评分
                }
                
                # 获取框架摘要和改进建议（如果存在）
                if 'framework_summary' in ar and ar['framework_summary']:
                    analysis[step_name]['framework_summary'] = ar['framework_summary']
                
                if 'improvement_suggestions' in ar and ar['improvement_suggestions'] and step_name == '结论':
                    analysis['improvement_suggestions'] = ar['improvement_suggestions']
            
            # 获取完整分析文本和一句话总结
            full_analysis_row = cursor.execute('''
            SELECT * FROM report_full_analysis
            WHERE report_id = ?
            ''', (report_id,)).fetchone()
            
            # 添加摘要数据
            analysis['summary'] = {
                'completeness_score': report['completeness_score'],
                'steps_found': sum(1 for step in analysis.values() if isinstance(step, dict) and step.get('found', False)),
                'evaluation': get_evaluation_text(report['completeness_score'])
            }
            
            # 添加一句话总结和完整分析文本（如果存在）
            if full_analysis_row:
                if 'one_line_summary' in full_analysis_row and full_analysis_row['one_line_summary']:
                    analysis['summary']['one_line_summary'] = full_analysis_row['one_line_summary']
                
                if 'full_analysis_text' in full_analysis_row and full_analysis_row['full_analysis_text']:
                    report['full_analysis'] = full_analysis_row['full_analysis_text']
            
            # 不再删除id字段，保留它供app.py使用
            # del report['id']
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
            report_id = row['id']
            
            # 获取研报的分析结果
            analysis_rows = cursor.execute('''
            SELECT * FROM analysis_results
            WHERE report_id = ?
            ''', (report_id,)).fetchall()
            
            analysis = {}
            for ar in analysis_rows:
                step_name = ar['step_name']
                analysis[step_name] = {
                    'found': bool(ar['found']),
                    'keywords': json.loads(ar['keywords']),
                    'evidence': json.loads(ar['evidence']),
                    'description': ar['description'],
                    'step_score': ar['step_score'] if 'step_score' in ar else 0  # 获取步骤评分
                }
                
                # 获取框架摘要和改进建议（如果存在）
                if 'framework_summary' in ar and ar['framework_summary']:
                    analysis[step_name]['framework_summary'] = ar['framework_summary']
                
                if 'improvement_suggestions' in ar and ar['improvement_suggestions'] and step_name == '结论':
                    analysis['improvement_suggestions'] = ar['improvement_suggestions']
            
            # 获取完整分析文本和一句话总结
            full_analysis_row = cursor.execute('''
            SELECT * FROM report_full_analysis
            WHERE report_id = ?
            ''', (report_id,)).fetchone()
            
            # 添加摘要数据
            analysis['summary'] = {
                'completeness_score': report['completeness_score'],
                'steps_found': sum(1 for step in analysis.values() if isinstance(step, dict) and step.get('found', False)),
                'evaluation': get_evaluation_text(report['completeness_score'])
            }
            
            # 添加一句话总结和完整分析文本（如果存在）
            if full_analysis_row:
                if 'one_line_summary' in full_analysis_row and full_analysis_row['one_line_summary']:
                    analysis['summary']['one_line_summary'] = full_analysis_row['one_line_summary']
                
                if 'full_analysis_text' in full_analysis_row and full_analysis_row['full_analysis_text']:
                    report['full_analysis'] = full_analysis_row['full_analysis_text']
            
            # 不再删除id字段，保留它供app.py使用
            # del report['id']
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
        # 修改连接以使用标准字典
        conn = sqlite3.connect(DB_FILE)
        # 使用自定义的 row factory 函数，将 Row 对象转换为 dict
        conn.row_factory = lambda cursor, row: {col[0]: row[idx] for idx, col in enumerate(cursor.description)}
        
        cursor = conn.cursor()
        
        # 获取研报基本数据
        reports = []
        rows = cursor.execute('''
        SELECT * FROM reports
        ORDER BY id DESC
        LIMIT 1000
        ''').fetchall()
        
        for row in rows:
            report = row  # 已经是字典了
            report_id = row['id']
            
            # 获取研报的分析结果
            analysis_rows = cursor.execute('''
            SELECT * FROM analysis_results
            WHERE report_id = ?
            ''', (report_id,)).fetchall()
            
            analysis = {}
            for ar in analysis_rows:
                step_name = ar['step_name']
                analysis[step_name] = {
                    'found': bool(ar['found']),
                    'keywords': json.loads(ar['keywords']) if ar['keywords'] else [],
                    'evidence': json.loads(ar['evidence']) if ar['evidence'] else [],
                    'description': ar['description'] if ar['description'] else '',
                    'step_score': ar['step_score'] if 'step_score' in ar else 0  # 获取步骤评分
                }
                
                # 获取框架摘要和改进建议（如果存在）
                if 'framework_summary' in ar and ar['framework_summary']:
                    analysis[step_name]['framework_summary'] = ar['framework_summary']
                
                if 'improvement_suggestions' in ar and ar['improvement_suggestions'] and step_name == '结论':
                    analysis['improvement_suggestions'] = ar['improvement_suggestions']
            
            # 获取完整分析文本和一句话总结
            full_analysis_row = cursor.execute('''
            SELECT * FROM report_full_analysis
            WHERE report_id = ?
            ''', (report_id,)).fetchone()
            
            # 添加摘要数据
            analysis['summary'] = {
                'completeness_score': report['completeness_score'],
                'steps_found': sum(1 for step in analysis.values() if isinstance(step, dict) and step.get('found', False)),
                'evaluation': get_evaluation_text(report['completeness_score'])
            }
            
            # 添加一句话总结和完整分析文本（如果存在）
            if full_analysis_row:
                if 'one_line_summary' in full_analysis_row and full_analysis_row['one_line_summary']:
                    analysis['summary']['one_line_summary'] = full_analysis_row['one_line_summary']
                
                if 'full_analysis_text' in full_analysis_row and full_analysis_row['full_analysis_text']:
                    report['full_analysis'] = full_analysis_row['full_analysis_text']
            
            # 移除数据库ID，并添加分析结果
            del report['id']
            report['analysis'] = analysis
            reports.append(report)
        
        if not reports:
            print("数据库中没有研报数据可导出")
            return False
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(reports, f, ensure_ascii=False, indent=4)
            
        print(f"成功导出 {len(reports)} 条研报数据到 {json_file}")
        return True
    except Exception as e:
        print(f"导出研报数据到JSON时出错: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if conn:
            conn.close()

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

# 添加从app.py中需要的两个函数

    except Exception as e:
        print(f"获取报告分析结果时出错: {e}")
        return []
    finally:
        conn.close()

    except Exception as e:
        print(f"获取报告完整分析时出错: {e}")
        return {
            "full_analysis_text": "",
            "one_line_summary": ""
        }
    finally:
        conn.close()

# 初始化数据库
if __name__ == "__main__":
    init_db()
    
    # 如果存在JSON文件，导入到数据库
    if os.path.exists('research_reports.json'):
        import_from_json() 
# 适配器函数，使用新表结构替代旧表
    # 将新格式转换为旧格式
    result = {}
    for step_name, step_data in analysis['steps'].items():
        result[step_name] = {
            'found': step_data['found'],
            'description': step_data['description'],
            'step_score': step_data['step_score'],
            'keywords': [],  # 旧格式需要这些字段，但新格式可能没有
            'evidence': [],
            'framework_summary': step_data.get('framework_summary', '')
        }
    
    return result

    # 将新格式转换为旧格式
    return {
        'full_analysis_text': analysis['full_analysis'],
        'one_line_summary': analysis['one_line_summary']
    }

# 适配器函数，使用新表结构替代旧表
def get_analysis_results_for_report(report_id):
    """
    获取研报的五步法分析结果（适配旧接口）
    
    参数:
    report_id (int): 研报ID
    
    返回:
    dict: 分析结果字典
    """
    from analysis_db import AnalysisDatabase
    db = AnalysisDatabase()
    analysis = db.get_analysis_by_report_id(report_id)
    if not analysis:
        return {}
    
    # 将新格式转换为旧格式
    result = {}
    for step_name, step_data in analysis['steps'].items():
        result[step_name] = {
            'found': step_data['found'],
            'description': step_data['description'],
            'step_score': step_data['step_score'],
            'keywords': [],  # 旧格式需要这些字段，但新格式可能没有
            'evidence': [],
            'framework_summary': step_data.get('framework_summary', '')
        }
    
    return result

def get_full_analysis_for_report(report_id):
    """
    获取研报的完整分析文本（适配旧接口）
    
    参数:
    report_id (int): 研报ID
    
    返回:
    dict: 包含完整分析文本和一句话总结的字典
    """
    from analysis_db import AnalysisDatabase
    db = AnalysisDatabase()
    analysis = db.get_analysis_by_report_id(report_id)
    if not analysis:
        return None
    
    # 将新格式转换为旧格式
    return {
        'full_analysis_text': analysis['full_analysis'],
        'one_line_summary': analysis['one_line_summary']
    }
