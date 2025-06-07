#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库维护脚本
定期执行以确保数据库性能和数据一致性
"""

import sqlite3
import os
import sys
import logging
import time
from datetime import datetime

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('db_maintenance.log'),
        logging.StreamHandler(sys.stdout)
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

def check_database_integrity():
    """检查数据库完整性"""
    conn = get_db_connection()
    try:
        logger.info("开始检查数据库完整性...")
        cursor = conn.cursor()
        
        # 执行完整性检查
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()
        integrity_status = result[0]
        
        if integrity_status == "ok":
            logger.info("数据库完整性检查通过")
            return True
        else:
            logger.error(f"数据库完整性检查失败: {integrity_status}")
            return False
            
    except Exception as e:
        logger.error(f"检查数据库完整性时出错: {str(e)}")
        return False
    finally:
        conn.close()

def check_data_consistency():
    """检查数据一致性"""
    conn = get_db_connection()
    try:
        logger.info("开始检查数据一致性...")
        cursor = conn.cursor()
        issues = []
        
        # 检查研报表中是否有缺失分析的记录
        cursor.execute('''
        SELECT r.id, r.title FROM reports r
        LEFT JOIN report_analysis ra ON r.id = ra.report_id
        WHERE ra.id IS NULL
        ''')
        missing_analysis = cursor.fetchall()
        if missing_analysis:
            issues.append(f"发现 {len(missing_analysis)} 条研报缺少分析数据")
            for report in missing_analysis[:5]:  # 只记录前5条
                issues.append(f"  研报ID {report['id']}: {report['title']}")
            
            if len(missing_analysis) > 5:
                issues.append(f"  以及其他 {len(missing_analysis) - 5} 条...")
        
        # 检查分析表中是否有孤立记录
        cursor.execute('''
        SELECT ra.id, ra.report_id FROM report_analysis ra
        LEFT JOIN reports r ON ra.report_id = r.id
        WHERE r.id IS NULL
        ''')
        orphaned_analysis = cursor.fetchall()
        if orphaned_analysis:
            issues.append(f"发现 {len(orphaned_analysis)} 条孤立的分析记录")
            for analysis in orphaned_analysis:
                issues.append(f"  分析ID {analysis['id']} 关联到不存在的研报ID {analysis['report_id']}")
        
        # 检查步骤分析表中是否有孤立记录
        cursor.execute('''
        SELECT sa.id, sa.analysis_id FROM step_analysis sa
        LEFT JOIN report_analysis ra ON sa.analysis_id = ra.id
        WHERE ra.id IS NULL
        ''')
        orphaned_steps = cursor.fetchall()
        if orphaned_steps:
            issues.append(f"发现 {len(orphaned_steps)} 条孤立的步骤分析记录")
        
        # 检查改进建议表中是否有孤立记录
        cursor.execute('''
        SELECT imp.id, imp.analysis_id FROM improvement_suggestions imp
        LEFT JOIN report_analysis ra ON imp.analysis_id = ra.id
        WHERE ra.id IS NULL
        ''')
        orphaned_suggestions = cursor.fetchall()
        if orphaned_suggestions:
            issues.append(f"发现 {len(orphaned_suggestions)} 条孤立的改进建议记录")
        
        # 记录检查结果
        if issues:
            logger.warning("数据一致性检查发现以下问题:")
            for issue in issues:
                logger.warning(issue)
            return False, issues
        else:
            logger.info("数据一致性检查通过，未发现问题")
            return True, []
            
    except Exception as e:
        logger.error(f"检查数据一致性时出错: {str(e)}")
        return False, [f"检查出错: {str(e)}"]
    finally:
        conn.close()

def optimize_database():
    """优化数据库性能"""
    conn = get_db_connection()
    try:
        logger.info("开始优化数据库...")
        
        # 记录优化前的数据库大小
        db_size_before = os.path.getsize(DB_FILE)
        logger.info(f"优化前数据库大小: {db_size_before/1024/1024:.2f} MB")
        
        # 执行VACUUM命令整理数据库
        start_time = time.time()
        conn.execute("VACUUM")
        vacuum_time = time.time() - start_time
        logger.info(f"VACUUM操作完成，耗时: {vacuum_time:.2f} 秒")
        
        # 执行ANALYZE命令更新统计信息
        start_time = time.time()
        conn.execute("ANALYZE")
        analyze_time = time.time() - start_time
        logger.info(f"ANALYZE操作完成，耗时: {analyze_time:.2f} 秒")
        
        # 记录优化后的数据库大小
        db_size_after = os.path.getsize(DB_FILE)
        size_diff = db_size_before - db_size_after
        logger.info(f"优化后数据库大小: {db_size_after/1024/1024:.2f} MB")
        logger.info(f"减少了: {size_diff/1024/1024:.2f} MB ({size_diff/db_size_before*100:.2f}%)")
        
        return True
    except Exception as e:
        logger.error(f"优化数据库时出错: {str(e)}")
        return False
    finally:
        conn.close()

def backup_database():
    """备份数据库"""
    try:
        import shutil
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        backup_dir = 'database_backups'
        
        # 确保备份目录存在
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        backup_file = os.path.join(backup_dir, f'research_reports_{timestamp}.db')
        shutil.copy2(DB_FILE, backup_file)
        
        # 清理旧备份，只保留最近5个
        backup_files = sorted([os.path.join(backup_dir, f) for f in os.listdir(backup_dir) 
                              if f.startswith('research_reports_') and f.endswith('.db')])
        
        if len(backup_files) > 5:
            for old_file in backup_files[:-5]:
                os.remove(old_file)
                logger.info(f"已删除旧备份: {old_file}")
        
        logger.info(f"数据库已备份为: {backup_file}")
        return True
    except Exception as e:
        logger.error(f"备份数据库时出错: {str(e)}")
        return False

def create_maintenance_log(is_integrity_ok, consistency_result, is_optimize_ok, is_backup_ok):
    """创建维护日志记录"""
    conn = get_db_connection()
    try:
        # 检查是否存在维护日志表
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS maintenance_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            integrity_check TEXT,
            consistency_check TEXT,
            optimization TEXT,
            backup TEXT,
            issues TEXT
        )
        ''')
        
        # 准备日志数据
        integrity_status = "通过" if is_integrity_ok else "失败"
        is_consistency_ok, consistency_issues = consistency_result
        consistency_status = "通过" if is_consistency_ok else "失败"
        optimization_status = "成功" if is_optimize_ok else "失败"
        backup_status = "成功" if is_backup_ok else "失败"
        
        # 记录详细问题
        issues_text = ""
        if not is_integrity_ok:
            issues_text += "数据库完整性检查失败\n"
        if not is_consistency_ok:
            issues_text += "数据一致性问题:\n" + "\n".join(consistency_issues) + "\n"
        if not is_optimize_ok:
            issues_text += "数据库优化失败\n"
        if not is_backup_ok:
            issues_text += "数据库备份失败\n"
        
        # 插入日志记录
        cursor.execute('''
        INSERT INTO maintenance_logs 
        (integrity_check, consistency_check, optimization, backup, issues)
        VALUES (?, ?, ?, ?, ?)
        ''', (integrity_status, consistency_status, optimization_status, backup_status, issues_text))
        
        conn.commit()
        logger.info("维护日志已记录到数据库")
        return True
    except Exception as e:
        logger.error(f"创建维护日志时出错: {str(e)}")
        return False
    finally:
        conn.close()

def run_maintenance():
    """运行所有维护任务"""
    logger.info("=" * 50)
    logger.info("开始数据库维护任务")
    logger.info("=" * 50)
    
    # 运行各维护任务
    is_integrity_ok = check_database_integrity()
    consistency_result = check_data_consistency()
    is_backup_ok = backup_database()
    is_optimize_ok = optimize_database()
    
    # 创建维护日志
    create_maintenance_log(is_integrity_ok, consistency_result, is_optimize_ok, is_backup_ok)
    
    logger.info("=" * 50)
    logger.info("数据库维护任务完成")
    logger.info("=" * 50)
    
    # 返回总体状态
    is_consistency_ok = consistency_result[0]
    return is_integrity_ok and is_consistency_ok and is_optimize_ok and is_backup_ok

if __name__ == "__main__":
    success = run_maintenance()
    sys.exit(0 if success else 1) 