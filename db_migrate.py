#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本
将旧系统数据迁移到新系统，并移除冗余表
"""

import sqlite3
import logging
import sys
import os
from datetime import datetime
import shutil

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)  # 确保日志输出到控制台
    ]
)
logger = logging.getLogger(__name__)

# 数据库文件
DB_FILE = 'research_reports.db'

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def create_backup():
    """创建数据库备份"""
    try:
        backup_dir = 'database_backups'
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
            
        backup_name = f"{backup_dir}/research_reports_before_migration_{datetime.now().strftime('%Y%m%d%H%M%S')}.db"
        shutil.copy2(DB_FILE, backup_name)
        logger.info(f"已创建数据库备份: {backup_name}")
        return True
    except Exception as e:
        logger.error(f"创建备份时出错: {str(e)}")
        return False

def migrate_data():
    """将旧系统数据迁移到新系统"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # 1. 先检查是否有未迁移的数据
        logger.info("检查是否有未迁移的数据...")
        
        # 检查analysis_results表中是否有report_analysis表中没有的数据
        cursor.execute('''
        SELECT DISTINCT ar.report_id 
        FROM analysis_results ar
        LEFT JOIN report_analysis ra ON ar.report_id = ra.report_id
        WHERE ra.id IS NULL
        ''')
        
        missing_reports = cursor.fetchall()
        missing_count = len(missing_reports)
        
        if missing_count > 0:
            logger.info(f"发现 {missing_count} 条需要迁移的报告")
            
            # 2. 迁移每条缺失的数据
            migrated_count = 0
            
            for report in missing_reports:
                report_id = report['report_id']
                
                # 获取旧系统中的分析数据
                cursor.execute('''
                SELECT step_name, found, description, framework_summary, step_score, improvement_suggestions
                FROM analysis_results 
                WHERE report_id = ?
                ''', (report_id,))
                
                steps = cursor.fetchall()
                
                # 获取完整分析文本
                cursor.execute('''
                SELECT full_analysis_text, one_line_summary
                FROM report_full_analysis 
                WHERE report_id = ?
                ''', (report_id,))
                
                full_analysis_row = cursor.fetchone()
                
                if not full_analysis_row:
                    logger.warning(f"研报ID {report_id} 在report_full_analysis表中没有数据，跳过")
                    continue
                
                full_analysis = full_analysis_row['full_analysis_text']
                one_line_summary = full_analysis_row['one_line_summary']
                
                # 获取研报基本信息
                cursor.execute('''
                SELECT completeness_score, analysis_method 
                FROM reports 
                WHERE id = ?
                ''', (report_id,))
                
                report_row = cursor.fetchone()
                
                if not report_row:
                    logger.warning(f"研报ID {report_id} 在reports表中没有数据，跳过")
                    continue
                
                completeness_score = report_row['completeness_score'] or 0
                analyzer_type = report_row['analysis_method'] or 'claude'
                
                # 计算评价
                if completeness_score >= 80:
                    evaluation = "该研报质量很高，五步法应用完善"
                elif completeness_score >= 60:
                    evaluation = "该研报质量较好，五步法应用基本完善"
                elif completeness_score >= 40:
                    evaluation = "该研报质量一般，五步法应用有所欠缺"
                else:
                    evaluation = "该研报质量较差，五步法应用不足"
                
                # 插入到新系统的report_analysis表
                cursor.execute('''
                INSERT INTO report_analysis 
                (report_id, analyzer_type, completeness_score, evaluation, one_line_summary, full_analysis)
                VALUES (?, ?, ?, ?, ?, ?)
                ''', (report_id, analyzer_type, completeness_score, evaluation, one_line_summary, full_analysis))
                
                analysis_id = cursor.lastrowid
                
                # 插入步骤分析
                for step in steps:
                    cursor.execute('''
                    INSERT INTO step_analysis
                    (analysis_id, step_name, found, description, step_score, framework_summary)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        analysis_id, 
                        step['step_name'],
                        1 if step['found'] == 1 else 0,
                        step['description'] or '',
                        step['step_score'] or 0,
                        step['framework_summary'] or ''
                    ))
                    
                    # 如果有改进建议，提取并插入
                    if step['improvement_suggestions']:
                        # 尝试提取改进建议（简单处理，实际可能需要更复杂的解析）
                        suggestions = step['improvement_suggestions'].split('\n')
                        for suggestion in suggestions:
                            if suggestion.strip():
                                cursor.execute('''
                                INSERT INTO improvement_suggestions
                                (analysis_id, point, suggestion)
                                VALUES (?, ?, ?)
                                ''', (
                                    analysis_id,
                                    f"改进{step['step_name']}步骤",
                                    suggestion.strip()
                                ))
                
                migrated_count += 1
                logger.info(f"已迁移研报ID {report_id} 的数据")
            
            logger.info(f"共迁移了 {migrated_count} 条研报的分析数据")
        else:
            logger.info("没有发现需要迁移的数据")
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"迁移数据时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()

def remove_old_tables():
    """删除旧系统表"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # 1. 确认数据已完全迁移
        cursor.execute('''
        SELECT COUNT(*) FROM analysis_results
        ''')
        old_count = cursor.fetchone()[0]
        
        cursor.execute('''
        SELECT COUNT(*) FROM report_analysis
        ''')
        new_count = cursor.fetchone()[0]
        
        if old_count > new_count:
            logger.warning(f"旧系统中还有未迁移的数据: 旧系统={old_count}, 新系统={new_count}")
            choice = input("确认是否仍然要删除旧系统表? (y/n): ")
            if choice.lower() != 'y':
                logger.info("用户取消了删除操作")
                return False
        
        # 2. 删除旧系统表
        logger.info("开始删除旧系统表...")
        
        # 备份表结构以防需要恢复
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='analysis_results'")
        analysis_results_sql = cursor.fetchone()['sql']
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='report_full_analysis'")
        report_full_analysis_sql = cursor.fetchone()['sql']
        
        with open('old_tables_schema.sql', 'w') as f:
            f.write(f"{analysis_results_sql};\n\n")
            f.write(f"{report_full_analysis_sql};\n\n")
        
        logger.info("已保存旧表结构到 old_tables_schema.sql")
        
        # 删除旧系统表
        cursor.execute("DROP TABLE IF EXISTS analysis_results")
        cursor.execute("DROP TABLE IF EXISTS report_full_analysis")
        
        logger.info("旧系统表已删除")
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"删除旧系统表时出错: {str(e)}")
        return False
    finally:
        conn.close()

def optimize_database():
    """优化数据库"""
    conn = get_db_connection()
    try:
        logger.info("开始优化数据库...")
        
        # 执行VACUUM命令优化数据库
        conn.execute("VACUUM")
        
        # 执行ANALYZE命令更新统计信息
        conn.execute("ANALYZE")
        
        logger.info("数据库优化完成")
        return True
    except Exception as e:
        logger.error(f"优化数据库时出错: {str(e)}")
        return False
    finally:
        conn.close()

def remove_unused_indexes():
    """删除不再需要的索引"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # 获取与旧表相关的索引
        cursor.execute('''
        SELECT name FROM sqlite_master 
        WHERE type='index' AND 
        (name LIKE 'idx_analysis_results%' OR name LIKE 'idx_report_full_analysis%')
        ''')
        
        indexes = cursor.fetchall()
        
        if indexes:
            logger.info(f"发现 {len(indexes)} 个与旧表相关的索引需要删除")
            
            for index in indexes:
                index_name = index['name']
                cursor.execute(f"DROP INDEX IF EXISTS {index_name}")
                logger.info(f"已删除索引: {index_name}")
        else:
            logger.info("没有发现需要删除的索引")
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"删除索引时出错: {str(e)}")
        return False
    finally:
        conn.close()

def run_migration():
    """运行迁移流程"""
    logger.info("=" * 50)
    logger.info("开始数据库迁移")
    logger.info("=" * 50)
    
    # 1. 创建备份
    if not create_backup():
        logger.error("创建备份失败，中止迁移")
        return False
    
    # 2. 迁移数据
    if not migrate_data():
        logger.error("数据迁移失败，中止迁移")
        return False
    
    # 3. 删除旧系统表
    if not remove_old_tables():
        logger.warning("删除旧系统表失败，继续进行其他优化")
    
    # 4. 删除不再需要的索引
    if not remove_unused_indexes():
        logger.warning("删除不再需要的索引失败，继续进行其他优化")
    
    # 5. 优化数据库
    optimize_database()
    
    logger.info("=" * 50)
    logger.info("数据库迁移完成")
    logger.info("=" * 50)
    
    return True

if __name__ == "__main__":
    run_migration() 