#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
项目清理脚本
用于清理项目中的临时文件、日志文件和其他不需要的文件
"""

import os
import shutil
import datetime
import glob
import argparse

def create_backup_dir():
    """创建备份目录"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    backup_dir = f"cleanup_tmp_{timestamp}"
    
    # 创建备份目录结构
    subdirs = ["backups", "tests", "html", "json", "scripts", "logs", "templates"]
    os.makedirs(backup_dir, exist_ok=True)
    for subdir in subdirs:
        os.makedirs(os.path.join(backup_dir, subdir), exist_ok=True)
    
    print(f"创建备份目录: {backup_dir}")
    return backup_dir

def move_files(patterns, target_dir):
    """移动匹配模式的文件到指定目录"""
    moved = 0
    for pattern in patterns:
        files = glob.glob(pattern)
        for file in files:
            if os.path.isfile(file):
                try:
                    shutil.move(file, os.path.join(target_dir, os.path.basename(file)))
                    print(f"已移动: {file} -> {target_dir}")
                    moved += 1
                except Exception as e:
                    print(f"移动 {file} 失败: {str(e)}")
    return moved

def cleanup_project(backup_dir, dry_run=False):
    """清理项目文件"""
    # 定义要清理的文件模式
    patterns = {
        "backups": ["backup_*", "research_reports_backup_*.db"],
        "html": ["page_source_*.html", "report_detail_*.html", "wangye.html"],
        "json": ["analysis_report_*.json", "latest_analysis.json", "latest_report.json", 
                "research_reports.json", "test_analysis_result.json"],
        "logs": ["*.log", "scheduler.log", "db_maintenance.log", "deepseek_disable.log"],
        "templates": ["templates/*_backup.html", "templates/*_orig.html", "templates/temp_*.html"]
    }
    
    total_moved = 0
    
    # 如果是dry run模式，只打印要移动的文件，不实际移动
    if dry_run:
        print("== 干运行模式 - 只显示将被移动的文件 ==")
        for category, category_patterns in patterns.items():
            print(f"\n要移动到 {os.path.join(backup_dir, category)} 的文件:")
            for pattern in category_patterns:
                files = glob.glob(pattern)
                for file in files:
                    if os.path.isfile(file):
                        print(f"  {file}")
                        total_moved += 1
    else:
        # 实际移动文件
        for category, category_patterns in patterns.items():
            target_dir = os.path.join(backup_dir, category)
            moved = move_files(category_patterns, target_dir)
            total_moved += moved
            print(f"移动了 {moved} 个文件到 {target_dir}")
    
    print(f"\n总计: {'将移动' if dry_run else '已移动'} {total_moved} 个文件")
    return total_moved

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="项目清理脚本")
    parser.add_argument("--dry-run", action="store_true", help="只显示要移动的文件，不实际移动")
    args = parser.parse_args()
    
    print("=== 开始清理项目 ===")
    
    # 创建备份目录
    backup_dir = create_backup_dir()
    
    # 清理项目
    cleanup_project(backup_dir, args.dry_run)
    
    print("\n=== 清理完成 ===")
    if not args.dry_run:
        print(f"所有移动的文件都在 {backup_dir} 目录中")
    print("如果需要恢复任何文件，可以从备份目录中复制回来")

if __name__ == "__main__":
    main() 