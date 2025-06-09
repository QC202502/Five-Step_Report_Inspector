#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理脚本
用于删除旧的日志文件和数据库备份，释放磁盘空间
"""

import os
import sys
import logging
import time
from datetime import datetime, timedelta
import glob
import shutil

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 配置
BACKUP_DIR = 'database_backups'
LOG_DIR = '.'
KEEP_BACKUPS = 5  # 保留的备份数量
LOG_MAX_AGE_DAYS = 30  # 日志文件保留的天数

def cleanup_database_backups():
    """清理旧的数据库备份，只保留最近的几个"""
    if not os.path.exists(BACKUP_DIR):
        logger.info(f"备份目录 {BACKUP_DIR} 不存在，跳过清理")
        return
    
    try:
        # 获取所有数据库备份文件
        backup_files = glob.glob(os.path.join(BACKUP_DIR, 'research_reports_*.db'))
        
        # 按修改时间排序
        backup_files.sort(key=os.path.getmtime)
        
        # 计算需要删除的文件
        files_to_delete = backup_files[:-KEEP_BACKUPS] if len(backup_files) > KEEP_BACKUPS else []
        
        # 删除旧备份
        for file_path in files_to_delete:
            os.remove(file_path)
            logger.info(f"已删除旧备份: {file_path}")
        
        logger.info(f"清理完成，共删除 {len(files_to_delete)} 个旧备份文件，保留 {min(len(backup_files), KEEP_BACKUPS)} 个最新备份")
    
    except Exception as e:
        logger.error(f"清理数据库备份时出错: {str(e)}")

def cleanup_log_files():
    """清理旧的日志文件，保留最近一个月的"""
    try:
        # 获取当前时间
        now = datetime.now()
        cutoff_date = now - timedelta(days=LOG_MAX_AGE_DAYS)
        cutoff_timestamp = cutoff_date.timestamp()
        
        # 获取所有日志文件
        log_files = [f for f in glob.glob(os.path.join(LOG_DIR, '*.log')) if os.path.isfile(f)]
        
        # 计算需要删除的文件
        files_to_delete = []
        for file_path in log_files:
            file_mod_time = os.path.getmtime(file_path)
            if file_mod_time < cutoff_timestamp:
                files_to_delete.append(file_path)
        
        # 删除旧日志
        for file_path in files_to_delete:
            os.remove(file_path)
            logger.info(f"已删除旧日志: {file_path}")
        
        logger.info(f"清理完成，共删除 {len(files_to_delete)} 个旧日志文件")
    
    except Exception as e:
        logger.error(f"清理日志文件时出错: {str(e)}")

def cleanup_temp_files():
    """清理临时文件"""
    try:
        # 获取当前时间
        now = datetime.now()
        cutoff_date = now - timedelta(days=7)  # 一周前的临时文件
        cutoff_timestamp = cutoff_date.timestamp()
        
        # 定义要清理的临时文件模式
        temp_patterns = [
            '*.tmp',
            'temp_*',
            '*.bak',
            '__pycache__/*',
            '*.pyc'
        ]
        
        total_deleted = 0
        
        # 遍历每个模式
        for pattern in temp_patterns:
            files = glob.glob(pattern, recursive=True)
            for file_path in files:
                if os.path.isfile(file_path) and os.path.getmtime(file_path) < cutoff_timestamp:
                    os.remove(file_path)
                    total_deleted += 1
                    logger.debug(f"已删除临时文件: {file_path}")
        
        # 清理__pycache__目录
        for root, dirs, files in os.walk('.', topdown=False):
            for name in dirs:
                if name == '__pycache__':
                    pycache_dir = os.path.join(root, name)
                    try:
                        shutil.rmtree(pycache_dir)
                        logger.debug(f"已删除 __pycache__ 目录: {pycache_dir}")
                        total_deleted += 1
                    except:
                        pass
        
        logger.info(f"清理完成，共删除 {total_deleted} 个临时文件和目录")
    
    except Exception as e:
        logger.error(f"清理临时文件时出错: {str(e)}")

def run_cleanup():
    """运行所有清理任务"""
    logger.info("=" * 50)
    logger.info("开始清理任务")
    logger.info("=" * 50)
    
    cleanup_database_backups()
    cleanup_log_files()
    cleanup_temp_files()
    
    logger.info("=" * 50)
    logger.info("清理任务完成")
    logger.info("=" * 50)

if __name__ == "__main__":
    run_cleanup() 