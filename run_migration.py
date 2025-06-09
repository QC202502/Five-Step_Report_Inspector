#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移运行脚本
"""

import logging
import sys
import os
from db_migrate import run_migration

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("开始执行数据库迁移...")
    
    if not os.path.exists('db_migrate.py'):
        logger.error("db_migrate.py文件不存在，请先创建迁移脚本")
        sys.exit(1)
    
    try:
        success = run_migration()
        
        if success:
            logger.info("数据库迁移成功完成")
            sys.exit(0)
        else:
            logger.error("数据库迁移过程中出现错误")
            sys.exit(1)
    except Exception as e:
        logger.error(f"执行迁移脚本时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 