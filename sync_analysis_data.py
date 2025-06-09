#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
同步分析数据
将新系统(report_analysis和step_analysis)中的分析结果同步到旧系统(analysis_results)中
确保评分和分析结果一致
"""

import sqlite3
import json

def sync_analysis_data():
    """同步分析数据"""
    conn = sqlite3.connect('research_reports.db')
    cursor = conn.cursor()
    
    try:
        print("开始同步分析数据...")
        
        # 1. 获取所有report_analysis记录
        cursor.execute('''
        SELECT ra.id, ra.report_id, ra.analyzer_type, ra.completeness_score, 
               ra.evaluation, ra.one_line_summary, ra.full_analysis
        FROM report_analysis ra
        ''')
        analyses = cursor.fetchall()
        print(f"找到 {len(analyses)} 条report_analysis记录")
        
        # 2. 获取所有step_analysis记录
        cursor.execute('''
        SELECT sa.analysis_id, sa.step_name, sa.found, sa.description, 
               sa.step_score, sa.framework_summary
        FROM step_analysis sa
        ''')
        steps = cursor.fetchall()
        print(f"找到 {len(steps)} 条step_analysis记录")
        
        # 3. 组织数据，按analysis_id分组
        steps_by_analysis = {}
        for analysis_id, step_name, found, description, step_score, framework_summary in steps:
            if analysis_id not in steps_by_analysis:
                steps_by_analysis[analysis_id] = []
            steps_by_analysis[analysis_id].append({
                'step_name': step_name,
                'found': found,
                'description': description,
                'step_score': step_score,
                'framework_summary': framework_summary
            })
        
        # 4. 更新reports表中的completeness_score
        updated_reports = 0
        for analysis_id, report_id, analyzer_type, completeness_score, evaluation, one_line_summary, full_analysis in analyses:
            # 更新reports表中的评分
            cursor.execute('''
            UPDATE reports 
            SET completeness_score = ?, 
                analysis_method = ?
            WHERE id = ?
            ''', (completeness_score, analyzer_type, report_id))
            
            # 检查report_id是否在steps_by_analysis中
            if analysis_id in steps_by_analysis:
                # 5. 删除旧的analysis_results记录
                cursor.execute('DELETE FROM analysis_results WHERE report_id = ?', (report_id,))
                
                # 6. 插入新的analysis_results记录
                for step in steps_by_analysis[analysis_id]:
                    step_name = step['step_name']
                    found = step['found']
                    description = step['description']
                    step_score = step['step_score']
                    framework_summary = step['framework_summary']
                    
                    # 创建空的JSON数组字符串
                    keywords_json = json.dumps([], ensure_ascii=False)
                    evidence_json = json.dumps([], ensure_ascii=False)
                    
                    cursor.execute('''
                    INSERT INTO analysis_results (
                        report_id, step_name, found, keywords, evidence, 
                        description, framework_summary, step_score
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        report_id, step_name, 1 if found else 0, 
                        keywords_json, evidence_json, description, 
                        framework_summary, step_score
                    ))
                
                # 7. 更新或插入report_full_analysis记录
                cursor.execute('SELECT report_id FROM report_full_analysis WHERE report_id = ?', (report_id,))
                if cursor.fetchone():
                    cursor.execute('''
                    UPDATE report_full_analysis 
                    SET full_analysis_text = ?, one_line_summary = ?
                    WHERE report_id = ?
                    ''', (full_analysis, one_line_summary, report_id))
                else:
                    cursor.execute('''
                    INSERT INTO report_full_analysis (
                        report_id, full_analysis_text, one_line_summary
                    ) VALUES (?, ?, ?)
                    ''', (report_id, full_analysis, one_line_summary))
                
                updated_reports += 1
                print(f"已同步研报ID {report_id} 的分析数据")
        
        conn.commit()
        print(f"成功同步了 {updated_reports} 条研报的分析数据")
        
    except Exception as e:
        conn.rollback()
        print(f"同步过程中出错: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()
        print("同步操作完成")

if __name__ == "__main__":
    sync_analysis_data() 