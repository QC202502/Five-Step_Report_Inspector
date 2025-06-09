#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库修复脚本
用于解决"研报ID XXX 没有找到分析结果"的问题，并同步新旧系统的数据
"""

import sqlite3
import json
import logging
import os
import sys
from datetime import datetime

# 设置日志
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)  # 确保日志输出到控制台
    ]
)
logger = logging.getLogger(__name__)

# 数据库文件名
DB_FILE = 'research_reports.db'

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def repair_analysis_data():
    """修复分析数据"""
    print("开始修复数据库数据...")  # 直接打印到控制台
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        logger.info("开始修复数据库数据...")
        
        # 1. 获取所有研报ID
        cursor.execute('SELECT id FROM reports ORDER BY id')
        report_ids = [row[0] for row in cursor.fetchall()]
        print(f"数据库中共有 {len(report_ids)} 条研报记录")  # 直接打印到控制台
        logger.info(f"数据库中共有 {len(report_ids)} 条研报记录")
        
        # 2. 检查每个研报的分析数据是否完整
        fixed_count = 0
        created_placeholder = 0
        
        for report_id in report_ids:
            # 检查新系统中是否有分析数据
            cursor.execute('SELECT id FROM report_analysis WHERE report_id = ?', (report_id,))
            new_analysis = cursor.fetchone()
            
            # 检查旧系统中是否有分析数据
            cursor.execute('SELECT id FROM analysis_results WHERE report_id = ?', (report_id,))
            old_analysis = cursor.fetchone()
            
            # 检查旧系统中是否有完整分析
            cursor.execute('SELECT report_id FROM report_full_analysis WHERE report_id = ?', (report_id,))
            old_full_analysis = cursor.fetchone()
            
            # 1. 如果新系统有数据但旧系统没有，同步到旧系统
            if new_analysis and not old_analysis:
                sync_new_to_old(conn, report_id)
                fixed_count += 1
                print(f"研报ID {report_id} 从新系统同步到旧系统")  # 直接打印到控制台
                logger.info(f"研报ID {report_id} 从新系统同步到旧系统")
                
            # 2. 如果旧系统有数据但新系统没有，同步到新系统
            elif old_analysis and not new_analysis:
                sync_old_to_new(conn, report_id)
                fixed_count += 1
                print(f"研报ID {report_id} 从旧系统同步到新系统")  # 直接打印到控制台
                logger.info(f"研报ID {report_id} 从旧系统同步到新系统")
                
            # 3. 如果两个系统都没有数据，创建占位分析记录
            elif not new_analysis and not old_analysis:
                create_placeholder_analysis(conn, report_id)
                created_placeholder += 1
                print(f"研报ID {report_id} 创建了占位分析记录")  # 直接打印到控制台
                logger.info(f"研报ID {report_id} 创建了占位分析记录")
        
        conn.commit()
        print(f"成功修复 {fixed_count} 条研报的分析数据")  # 直接打印到控制台
        print(f"为 {created_placeholder} 条研报创建了占位分析记录")  # 直接打印到控制台
        logger.info(f"成功修复 {fixed_count} 条研报的分析数据")
        logger.info(f"为 {created_placeholder} 条研报创建了占位分析记录")
        
        # 3. 添加索引优化数据库性能
        add_indexes(conn)
        
        return fixed_count, created_placeholder
        
    except Exception as e:
        conn.rollback()
        print(f"修复过程中出错: {str(e)}")  # 直接打印到控制台
        logger.error(f"修复过程中出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return 0, 0
    finally:
        conn.close()
        print("修复操作完成")  # 直接打印到控制台
        logger.info("修复操作完成")

def sync_new_to_old(conn, report_id):
    """将新系统的分析数据同步到旧系统"""
    cursor = conn.cursor()
    
    # 1. 获取新系统中的分析数据
    cursor.execute('''
    SELECT ra.id, ra.analyzer_type, ra.completeness_score, ra.evaluation, 
           ra.one_line_summary, ra.full_analysis
    FROM report_analysis ra WHERE ra.report_id = ?
    ''', (report_id,))
    
    analysis = cursor.fetchone()
    if not analysis:
        return False
    
    analysis_id, analyzer_type, completeness_score, evaluation, one_line_summary, full_analysis = analysis
    
    # 2. 获取步骤分析数据
    cursor.execute('''
    SELECT step_name, found, description, step_score, framework_summary
    FROM step_analysis WHERE analysis_id = ?
    ''', (analysis_id,))
    
    steps = cursor.fetchall()
    
    # 3. 更新research_reports表中的completeness_score和analysis_method
    cursor.execute('''
    UPDATE reports 
    SET completeness_score = ?, analysis_method = ?
    WHERE id = ?
    ''', (completeness_score, analyzer_type, report_id))
    
    # 4. 删除旧系统中可能存在的不完整数据
    cursor.execute('DELETE FROM analysis_results WHERE report_id = ?', (report_id,))
    cursor.execute('DELETE FROM report_full_analysis WHERE report_id = ?', (report_id,))
    
    # 5. 同步每个步骤分析到旧系统
    for step_name, found, description, step_score, framework_summary in steps:
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
    
    # 6. 同步完整分析文本
    cursor.execute('''
    INSERT INTO report_full_analysis (
        report_id, full_analysis_text, one_line_summary
    ) VALUES (?, ?, ?)
    ''', (report_id, full_analysis, one_line_summary))
    
    return True

def sync_old_to_new(conn, report_id):
    """将旧系统的分析数据同步到新系统"""
    cursor = conn.cursor()
    
    # 1. 获取旧系统中的分析数据
    cursor.execute('''
    SELECT step_name, found, description, framework_summary, step_score
    FROM analysis_results WHERE report_id = ?
    ''', (report_id,))
    
    steps = cursor.fetchall()
    if not steps:
        return False
    
    # 2. 获取完整分析文本
    cursor.execute('''
    SELECT full_analysis_text, one_line_summary
    FROM report_full_analysis WHERE report_id = ?
    ''', (report_id,))
    
    full_analysis_row = cursor.fetchone()
    full_analysis = full_analysis_row[0] if full_analysis_row else ""
    one_line_summary = full_analysis_row[1] if full_analysis_row else ""
    
    # 3. 获取研报评分
    cursor.execute('SELECT completeness_score, analysis_method FROM reports WHERE id = ?', (report_id,))
    report_row = cursor.fetchone()
    completeness_score = report_row[0] if report_row and report_row[0] else 0
    analyzer_type = report_row[1] if report_row and report_row[1] else 'claude'
    
    # 4. 构建评价
    if completeness_score >= 80:
        evaluation = "该研报质量很高，五步法应用完善"
    elif completeness_score >= 60:
        evaluation = "该研报质量较好，五步法应用基本完善"
    elif completeness_score >= 40:
        evaluation = "该研报质量一般，五步法应用有所欠缺"
    else:
        evaluation = "该研报质量较差，五步法应用不足"
    
    # 5. 插入到新系统的report_analysis表
    cursor.execute('''
    INSERT INTO report_analysis 
    (report_id, analyzer_type, completeness_score, evaluation, one_line_summary, full_analysis)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (report_id, analyzer_type, completeness_score, evaluation, one_line_summary, full_analysis))
    
    analysis_id = cursor.lastrowid
    
    # 6. 插入各步骤分析结果到step_analysis表
    for step_name, found, description, framework_summary, step_score in steps:
        cursor.execute('''
        INSERT INTO step_analysis
        (analysis_id, step_name, found, description, step_score, framework_summary)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (analysis_id, step_name, 1 if found == 1 else 0, description, step_score, framework_summary))
    
    return True

def create_placeholder_analysis(conn, report_id):
    """为没有分析数据的研报创建占位分析记录"""
    cursor = conn.cursor()
    
    # 1. 获取研报基本信息
    cursor.execute('SELECT title, industry FROM reports WHERE id = ?', (report_id,))
    report_row = cursor.fetchone()
    if not report_row:
        return False
    
    title, industry = report_row
    
    # 2. 创建默认评价和分数
    completeness_score = 0
    evaluation = "暂无分析数据，请点击分析按钮进行分析"
    one_line_summary = f"《{title}》暂无分析结果"
    full_analysis = f"研报《{title}》尚未进行分析，请使用分析功能获取详细分析结果。"
    analyzer_type = 'placeholder'
    
    # 3. 插入到新系统的report_analysis表
    cursor.execute('''
    INSERT INTO report_analysis 
    (report_id, analyzer_type, completeness_score, evaluation, one_line_summary, full_analysis)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (report_id, analyzer_type, completeness_score, evaluation, one_line_summary, full_analysis))
    
    analysis_id = cursor.lastrowid
    
    # 4. 为五步法各步骤创建占位记录
    steps = ["信息", "逻辑", "超预期", "催化剂", "结论"]
    for step in steps:
        description = f"暂无{step}分析"
        cursor.execute('''
        INSERT INTO step_analysis
        (analysis_id, step_name, found, description, step_score, framework_summary)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (analysis_id, step, 0, description, 0, ""))
    
    # 5. 同步到旧系统的analysis_results表
    keywords_json = json.dumps([], ensure_ascii=False)
    evidence_json = json.dumps([], ensure_ascii=False)
    
    for step in steps:
        description = f"暂无{step}分析"
        cursor.execute('''
        INSERT INTO analysis_results (
            report_id, step_name, found, keywords, evidence, 
            description, framework_summary, step_score
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            report_id, step, 0, 
            keywords_json, evidence_json, description, 
            "", 0
        ))
    
    # 6. 同步到旧系统的report_full_analysis表
    cursor.execute('''
    INSERT INTO report_full_analysis (
        report_id, full_analysis_text, one_line_summary
    ) VALUES (?, ?, ?)
    ''', (report_id, full_analysis, one_line_summary))
    
    # 7. 更新reports表中的字段
    cursor.execute('''
    UPDATE reports 
    SET completeness_score = ?, analysis_method = ?
    WHERE id = ?
    ''', (completeness_score, analyzer_type, report_id))
    
    return True

def add_indexes(conn):
    """为常用查询添加索引，提高性能"""
    cursor = conn.cursor()
    
    try:
        print("添加数据库索引...")  # 直接打印到控制台
        # 为reports表添加索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_reports_industry ON reports(industry)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_reports_org ON reports(org)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_reports_date ON reports(date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_reports_rating ON reports(rating)')
        
        # 为report_analysis表添加索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_report_analysis_analyzer ON report_analysis(analyzer_type)')
        
        # 为step_analysis表添加索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_step_analysis_step_name ON step_analysis(step_name)')
        
        # 为analysis_results表添加索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_analysis_results_step_name ON analysis_results(step_name)')
        
        print("成功添加数据库索引")  # 直接打印到控制台
        logger.info("成功添加数据库索引")
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"添加索引时出错: {str(e)}")  # 直接打印到控制台
        logger.error(f"添加索引时出错: {str(e)}")
        return False

def optimize_database():
    """优化数据库，清理碎片，提高性能"""
    conn = get_db_connection()
    try:
        print("开始优化数据库...")  # 直接打印到控制台
        logger.info("开始优化数据库...")
        
        # 执行VACUUM命令优化数据库
        conn.execute("VACUUM")
        
        # 执行ANALYZE命令更新统计信息
        conn.execute("ANALYZE")
        
        print("数据库优化完成")  # 直接打印到控制台
        logger.info("数据库优化完成")
        return True
    except Exception as e:
        print(f"优化数据库时出错: {str(e)}")  # 直接打印到控制台
        logger.error(f"优化数据库时出错: {str(e)}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("=" * 50)  # 直接打印到控制台
    print("开始数据库修复脚本")  # 直接打印到控制台
    print("=" * 50)  # 直接打印到控制台
    
    # 创建备份
    try:
        import shutil
        backup_name = f"research_reports_backup_{datetime.now().strftime('%Y%m%d%H%M%S')}.db"
        shutil.copy2(DB_FILE, backup_name)
        print(f"已创建数据库备份: {backup_name}")  # 直接打印到控制台
        logger.info(f"已创建数据库备份: {backup_name}")
    except Exception as e:
        print(f"创建备份时出错: {str(e)}")  # 直接打印到控制台
        logger.warning(f"创建备份时出错: {str(e)}")
        choice = input("未能创建备份，是否继续修复操作？(y/n): ")
        if choice.lower() != 'y':
            print("用户取消了修复操作")  # 直接打印到控制台
            logger.info("用户取消了修复操作")
            exit(0)
    
    # 执行修复
    fixed_count, placeholder_count = repair_analysis_data()
    print(f"成功修复 {fixed_count} 条研报数据，创建了 {placeholder_count} 条占位分析记录")  # 直接打印到控制台
    logger.info(f"成功修复 {fixed_count} 条研报数据，创建了 {placeholder_count} 条占位分析记录")
    
    # 优化数据库
    optimize_database()
    
    print("=" * 50)  # 直接打印到控制台
    print("数据库修复和优化操作已完成")  # 直接打印到控制台
    print("=" * 50)  # 直接打印到控制台
    logger.info("数据库修复和优化操作已完成") 