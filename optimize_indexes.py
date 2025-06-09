#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库索引优化脚本
为常用查询添加索引，提高数据库查询性能
"""

import sqlite3
import logging
import sys
import time

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 数据库文件
DB_FILE = 'research_reports.db'

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def get_existing_indexes():
    """获取已存在的索引"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row['name'] for row in cursor.fetchall()]
        return indexes
    except Exception as e:
        logger.error(f"获取索引列表时出错: {str(e)}")
        return []
    finally:
        conn.close()

def create_indexes():
    """创建必要的索引"""
    conn = get_db_connection()
    try:
        logger.info("开始创建索引...")
        cursor = conn.cursor()
        
        # 获取现有索引
        existing_indexes = get_existing_indexes()
        
        # 定义需要创建的索引
        indexes = [
            # reports表索引
            {
                "name": "idx_reports_industry",
                "sql": "CREATE INDEX IF NOT EXISTS idx_reports_industry ON reports(industry)"
            },
            {
                "name": "idx_reports_org",
                "sql": "CREATE INDEX IF NOT EXISTS idx_reports_org ON reports(org)"
            },
            {
                "name": "idx_reports_date",
                "sql": "CREATE INDEX IF NOT EXISTS idx_reports_date ON reports(date)"
            },
            {
                "name": "idx_reports_rating",
                "sql": "CREATE INDEX IF NOT EXISTS idx_reports_rating ON reports(rating)"
            },
            {
                "name": "idx_reports_stock_code",
                "sql": "CREATE INDEX IF NOT EXISTS idx_reports_stock_code ON reports(stock_code)"
            },
            # report_analysis表索引
            {
                "name": "idx_report_analysis_report_id",
                "sql": "CREATE INDEX IF NOT EXISTS idx_report_analysis_report_id ON report_analysis(report_id)"
            },
            {
                "name": "idx_report_analysis_analyzer_type",
                "sql": "CREATE INDEX IF NOT EXISTS idx_report_analysis_analyzer_type ON report_analysis(analyzer_type)"
            },
            {
                "name": "idx_report_analysis_completeness_score",
                "sql": "CREATE INDEX IF NOT EXISTS idx_report_analysis_completeness_score ON report_analysis(completeness_score)"
            },
            # step_analysis表索引
            {
                "name": "idx_step_analysis_analysis_id",
                "sql": "CREATE INDEX IF NOT EXISTS idx_step_analysis_analysis_id ON step_analysis(analysis_id)"
            },
            {
                "name": "idx_step_analysis_step_name",
                "sql": "CREATE INDEX IF NOT EXISTS idx_step_analysis_step_name ON step_analysis(step_name)"
            },
            {
                "name": "idx_step_analysis_found",
                "sql": "CREATE INDEX IF NOT EXISTS idx_step_analysis_found ON step_analysis(found)"
            },
            # improvement_suggestions表索引
            {
                "name": "idx_improvement_suggestions_analysis_id",
                "sql": "CREATE INDEX IF NOT EXISTS idx_improvement_suggestions_analysis_id ON improvement_suggestions(analysis_id)"
            },
            # analysis_results表索引
            {
                "name": "idx_analysis_results_report_id",
                "sql": "CREATE INDEX IF NOT EXISTS idx_analysis_results_report_id ON analysis_results(report_id)"
            },
            {
                "name": "idx_analysis_results_step_name",
                "sql": "CREATE INDEX IF NOT EXISTS idx_analysis_results_step_name ON analysis_results(step_name)"
            },
            # report_full_analysis表索引
            {
                "name": "idx_report_full_analysis_report_id",
                "sql": "CREATE INDEX IF NOT EXISTS idx_report_full_analysis_report_id ON report_full_analysis(report_id)"
            }
        ]
        
        # 创建索引
        created_count = 0
        skipped_count = 0
        
        for index in indexes:
            if index["name"] in existing_indexes:
                logger.info(f"索引 {index['name']} 已存在，跳过")
                skipped_count += 1
                continue
            
            try:
                start_time = time.time()
                cursor.execute(index["sql"])
                duration = time.time() - start_time
                logger.info(f"创建索引 {index['name']} 成功，耗时 {duration:.2f} 秒")
                created_count += 1
            except Exception as e:
                logger.error(f"创建索引 {index['name']} 时出错: {str(e)}")
                
        conn.commit()
        logger.info(f"索引创建完成，共创建 {created_count} 个新索引，跳过 {skipped_count} 个已存在的索引")
        
        # 更新数据库统计信息
        cursor.execute("ANALYZE")
        logger.info("已更新数据库统计信息")
        
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"创建索引时出错: {str(e)}")
        return False
    finally:
        conn.close()

def check_index_usage():
    """检查索引使用情况"""
    conn = get_db_connection()
    try:
        logger.info("检查索引使用情况...")
        cursor = conn.cursor()
        
        # 定义常用查询
        test_queries = [
            {
                "name": "按行业查询",
                "sql": "EXPLAIN QUERY PLAN SELECT * FROM reports WHERE industry = '互联网'",
                "expected_index": "idx_reports_industry"
            },
            {
                "name": "按机构查询",
                "sql": "EXPLAIN QUERY PLAN SELECT * FROM reports WHERE org = '国信证券'",
                "expected_index": "idx_reports_org"
            },
            {
                "name": "按评级查询",
                "sql": "EXPLAIN QUERY PLAN SELECT * FROM reports WHERE rating = '买入'",
                "expected_index": "idx_reports_rating"
            },
            {
                "name": "获取研报分析",
                "sql": "EXPLAIN QUERY PLAN SELECT * FROM report_analysis WHERE report_id = 1 AND analyzer_type = 'claude'",
                "expected_index": "idx_report_analysis_report_id"
            },
            {
                "name": "获取步骤分析",
                "sql": "EXPLAIN QUERY PLAN SELECT * FROM step_analysis WHERE analysis_id = 1 AND step_name = '信息'",
                "expected_index": "idx_step_analysis_analysis_id"
            }
        ]
        
        # 执行测试查询
        for query in test_queries:
            cursor.execute(query["sql"])
            explain_result = cursor.fetchall()
            
            logger.info(f"查询: {query['name']}")
            logger.info(f"执行计划:")
            
            using_index = any(query["expected_index"] in str(row) for row in explain_result)
            for row in explain_result:
                logger.info(f"  {dict(row)}")
            
            if using_index:
                logger.info(f"✓ 正在使用索引 {query['expected_index']}")
            else:
                logger.info(f"✗ 未使用预期索引 {query['expected_index']}")
            
            logger.info("-" * 50)
        
        return True
    except Exception as e:
        logger.error(f"检查索引使用情况时出错: {str(e)}")
        return False
    finally:
        conn.close()

def run_optimization():
    """运行索引优化"""
    logger.info("=" * 50)
    logger.info("开始数据库索引优化")
    logger.info("=" * 50)
    
    success = create_indexes()
    
    if success:
        check_index_usage()
    
    logger.info("=" * 50)
    logger.info("数据库索引优化完成")
    logger.info("=" * 50)
    
    return success

if __name__ == "__main__":
    success = run_optimization()
    sys.exit(0 if success else 1) 