#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import sys
from datetime import datetime

def check_existing_reports(search_term=None, limit=20):
    """
    检查并显示数据库中已有的研报
    
    参数:
    search_term (str): 可选的搜索关键词，用于过滤研报标题
    limit (int): 显示的最大记录数
    """
    try:
        # 连接数据库
        conn = sqlite3.connect('research_reports.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 构建查询
        query = "SELECT id, title, industry, org, date, link FROM reports"
        params = []
        
        if search_term:
            query += " WHERE title LIKE ? OR industry LIKE ? OR org LIKE ?"
            search_pattern = f"%{search_term}%"
            params = [search_pattern, search_pattern, search_pattern]
        
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        
        # 执行查询
        cursor.execute(query, params)
        reports = cursor.fetchall()
        
        # 获取总记录数
        cursor.execute("SELECT COUNT(*) FROM reports")
        total_count = cursor.fetchone()[0]
        
        # 显示结果
        print(f"\n===== 数据库中的研报记录 ({total_count} 条总记录) =====\n")
        
        if not reports:
            print("没有找到匹配的研报记录")
            return
        
        # 使用固定宽度的格式字符串
        format_str = "{:<6} {:<40} {:<12} {:<12} {:<10}"
        
        # 打印表头
        print(format_str.format("ID", "标题", "行业", "机构", "日期"))
        print("-" * 80)
        
        # 打印研报记录
        for report in reports:
            # 处理每个字段，确保不会过长
            id_str = str(report['id'])
            
            title = report['title'] if report['title'] else ""
            if len(title) > 37:
                title = title[:37] + "..."
            
            industry = report['industry'] if report['industry'] else ""
            if len(industry) > 9:
                industry = industry[:9] + "..."
            
            org = report['org'] if report['org'] else ""
            if len(org) > 9:
                org = org[:9] + "..."
            
            date = report['date'] if report['date'] else ""
            if len(date) > 10:
                date = date[:10]
            
            # 使用格式字符串打印一行
            print(format_str.format(id_str, title, industry, org, date))
        
        print("\n使用方法:")
        print("  python check_existing_reports.py [搜索关键词] [显示数量]")
        print("  例如: python check_existing_reports.py 科技 50")
        
    except Exception as e:
        print(f"检查研报记录时出错: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    # 解析命令行参数
    search_term = None
    limit = 20
    
    if len(sys.argv) > 1:
        search_term = sys.argv[1]
    
    if len(sys.argv) > 2:
        try:
            limit = int(sys.argv[2])
        except ValueError:
            print(f"警告: 显示数量参数 '{sys.argv[2]}' 不是有效的整数，使用默认值 20")
    
    check_existing_reports(search_term, limit) 