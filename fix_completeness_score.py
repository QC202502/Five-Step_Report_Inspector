#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复数据库中所有研报的completeness_score字段
确保它们有有效的整数值，避免NoneType与int比较错误
"""

import sqlite3
import json

def fix_completeness_scores():
    """修复所有研报的完整性评分"""
    conn = sqlite3.connect('research_reports.db')
    cursor = conn.cursor()
    
    try:
        print("开始修复研报完整性评分...")
        
        # 获取所有研报ID
        cursor.execute('SELECT id, title, completeness_score FROM reports')
        reports = cursor.fetchall()
        print(f"数据库中共有 {len(reports)} 条研报记录")
        
        fixed_count = 0
        for report_id, title, score in reports:
            # 检查分数是否为None或非整数
            if score is None or not isinstance(score, int):
                print(f"研报ID {report_id} 的评分为 {score}，需要修复")
                
                # 计算新的评分
                # 从analysis_results表获取各步骤的评分
                cursor.execute('''
                SELECT step_score FROM analysis_results 
                WHERE report_id = ? AND step_score IS NOT NULL
                ''', (report_id,))
                step_scores = [row[0] for row in cursor.fetchall()]
                
                # 如果有step_score，则计算平均值，否则默认设为50
                if step_scores:
                    # 确保每个分数都是有效的整数
                    valid_scores = []
                    for s in step_scores:
                        try:
                            if s is not None:
                                valid_scores.append(int(s))
                        except (ValueError, TypeError):
                            pass
                    
                    new_score = int(sum(valid_scores) / len(valid_scores)) if valid_scores else 50
                else:
                    new_score = 50  # 默认中等评分
                
                # 更新研报的评分
                cursor.execute('''
                UPDATE reports SET completeness_score = ? WHERE id = ?
                ''', (new_score, report_id))
                
                print(f"已将研报 '{title}' (ID: {report_id}) 的评分从 {score} 修复为 {new_score}")
                fixed_count += 1
        
        conn.commit()
        print(f"完成修复！共更新了 {fixed_count} 条研报的完整性评分")
        
        # 修复report_analysis表中的评分
        cursor.execute('SELECT id, report_id, completeness_score FROM report_analysis')
        analyses = cursor.fetchall()
        print(f"数据库中共有 {len(analyses)} 条分析记录")
        
        fixed_analysis_count = 0
        for analysis_id, report_id, score in analyses:
            # 检查分数是否为None或非整数
            if score is None or not isinstance(score, int):
                print(f"分析记录ID {analysis_id} 的评分为 {score}，需要修复")
                
                # 从reports表获取修复后的评分
                cursor.execute('SELECT completeness_score FROM reports WHERE id = ?', (report_id,))
                report_score = cursor.fetchone()
                
                if report_score and report_score[0]:
                    new_score = report_score[0]
                else:
                    new_score = 50  # 默认中等评分
                
                # 更新分析记录的评分
                cursor.execute('''
                UPDATE report_analysis SET completeness_score = ? WHERE id = ?
                ''', (new_score, analysis_id))
                
                print(f"已将分析记录ID {analysis_id} (报告ID: {report_id}) 的评分从 {score} 修复为 {new_score}")
                fixed_analysis_count += 1
        
        conn.commit()
        print(f"完成修复！共更新了 {fixed_analysis_count} 条分析记录的完整性评分")
        
        # 修复step_analysis表中的评分
        cursor.execute('''
        SELECT id, analysis_id, step_name, step_score 
        FROM step_analysis
        ''')
        steps = cursor.fetchall()
        print(f"数据库中共有 {len(steps)} 条步骤分析记录")
        
        fixed_step_count = 0
        for step_id, analysis_id, step_name, score in steps:
            # 检查分数是否为None或非整数
            if score is None or not isinstance(score, int):
                print(f"步骤分析ID {step_id} ({step_name}) 的评分为 {score}，需要修复")
                
                # 默认设置为60分（及格）
                new_score = 60
                
                # 更新步骤分析的评分
                cursor.execute('''
                UPDATE step_analysis SET step_score = ? WHERE id = ?
                ''', (new_score, step_id))
                
                print(f"已将步骤分析ID {step_id} ({step_name}) 的评分从 {score} 修复为 {new_score}")
                fixed_step_count += 1
        
        conn.commit()
        print(f"完成修复！共更新了 {fixed_step_count} 条步骤分析的评分")
        
    except Exception as e:
        conn.rollback()
        print(f"修复过程中出错: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()
        print("修复操作完成")

if __name__ == "__main__":
    fix_completeness_scores() 