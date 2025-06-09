#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
初始化演示数据
直接添加一些基本的研报和分析结果到数据库中
"""

import sqlite3
import json
import datetime

def add_demo_report():
    """添加一条示例研报到数据库"""
    conn = sqlite3.connect('research_reports.db')
    cursor = conn.cursor()
    
    try:
        # 检查报告是否已存在
        cursor.execute("SELECT id FROM reports WHERE title = '示例研报：五步法分析演示'")
        existing = cursor.fetchone()
        
        if existing:
            print(f"示例研报已存在，ID: {existing[0]}")
            report_id = existing[0]
        else:
            # 添加示例研报
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            cursor.execute('''
            INSERT INTO reports (
                title, link, abstract, content_preview, full_content, 
                industry, rating, org, date, completeness_score,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                '示例研报：五步法分析演示',                  # 标题
                'https://example.com/demo-report',         # 链接
                '这是一份用于演示五步法分析的示例研报',       # 摘要
                '这是一份用于演示五步法分析的示例研报内容预览...', # 内容预览
                '这是一份用于演示五步法分析的示例研报完整内容。本研报展示了五步法分析方法的应用。', # 完整内容
                '科技',                                   # 行业
                '买入',                                   # 评级
                '演示机构',                                # 机构
                '2025-06-01',                             # 日期
                80,                                        # 完整性评分
                now,                                       # 创建时间
                now                                        # 更新时间
            ))
            
            report_id = cursor.lastrowid
            print(f"成功添加示例研报，ID: {report_id}")
        
        # 添加分析结果
        cursor.execute("SELECT id FROM analysis_results WHERE report_id = ? AND step_name = '信息'", (report_id,))
        if not cursor.fetchone():
            # 添加五步法分析结果
            steps = ['信息', '逻辑', '超预期', '催化剂', '结论']
            step_scores = [80, 75, 70, 85, 90]
            
            for i, step in enumerate(steps):
                keywords_json = json.dumps(['关键词1', '关键词2', '关键词3'], ensure_ascii=False)
                evidence_json = json.dumps(['证据1', '证据2', '证据3'], ensure_ascii=False)
                
                cursor.execute('''
                INSERT INTO analysis_results (
                    report_id, step_name, found, keywords, evidence, description,
                    framework_summary, improvement_suggestions, step_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    report_id,
                    step,
                    1,  # found
                    keywords_json,
                    evidence_json,
                    f'这是{step}步骤的分析描述',
                    f'这是{step}步骤的框架摘要',
                    f'这是{step}步骤的改进建议' if step == '结论' else '',
                    step_scores[i]
                ))
            
            print(f"成功为示例研报添加了五步法分析结果")
        else:
            print(f"示例研报已有分析结果，无需再次添加")
        
        # 添加完整分析
        cursor.execute("SELECT report_id FROM report_full_analysis WHERE report_id = ?", (report_id,))
        if not cursor.fetchone():
            cursor.execute('''
            INSERT INTO report_full_analysis (
                report_id, full_analysis_text, one_line_summary
            ) VALUES (?, ?, ?)
            ''', (
                report_id,
                "这是完整的五步法分析文本，包含详细的分析过程和结论。",
                "一句话总结：这是一份高质量的研报，五步法分析完整。"
            ))
            
            print(f"成功为示例研报添加了完整分析文本")
        else:
            print(f"示例研报已有完整分析文本，无需再次添加")
        
        # 添加到新的分析表中
        cursor.execute("SELECT id FROM report_analysis WHERE report_id = ?", (report_id,))
        if not cursor.fetchone():
            cursor.execute('''
            INSERT INTO report_analysis (
                report_id, analyzer_type, completeness_score, evaluation, 
                one_line_summary, full_analysis
            ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                report_id,
                'deepseek',
                80,
                '该研报对五步法的应用较为完善，涵盖了大部分分析要素',
                '一句话总结：这是一份高质量的研报，五步法分析完整。',
                '这是完整的五步法分析文本，包含详细的分析过程和结论。'
            ))
            
            analysis_id = cursor.lastrowid
            
            # 添加步骤分析
            steps = ['信息', '逻辑', '超预期', '催化剂', '结论']
            step_scores = [80, 75, 70, 85, 90]
            
            for i, step in enumerate(steps):
                cursor.execute('''
                INSERT INTO step_analysis (
                    analysis_id, step_name, found, description, step_score, framework_summary
                ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    analysis_id,
                    step,
                    1,  # found
                    f'这是{step}步骤的分析描述',
                    step_scores[i],
                    f'这是{step}步骤的框架摘要'
                ))
            
            print(f"成功为示例研报添加了新格式的分析结果")
        else:
            print(f"示例研报已有新格式的分析结果，无需再次添加")
        
        conn.commit()
        print("演示数据初始化完成")
        
    except Exception as e:
        conn.rollback()
        print(f"添加演示数据时出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    add_demo_report() 