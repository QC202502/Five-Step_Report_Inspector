#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复数据库引用脚本
用于更新代码中对旧表的引用，使其使用新表结构
"""

import os
import re
import sys
from typing import Dict, List, Any, Optional

class AnalysisAdapter:
    """
    适配器类，用于将旧的数据库访问函数适配到新的表结构
    这个类将替代原有的函数，但保持相同的接口，使得系统其他部分不需要修改
    """
    
    def __init__(self, db_path: str = 'research_reports.db'):
        """初始化数据库连接"""
        self.db_path = db_path
        
        # 导入AnalysisDatabase类
        from analysis_db import AnalysisDatabase
        self.db = AnalysisDatabase(db_path)
    
    def get_analysis_results_for_report(self, report_id: int) -> Dict:
        """
        获取研报的分析结果（适配旧接口）
        
        参数:
        report_id (int): 研报ID
        
        返回:
        dict: 分析结果字典
        """
        # 从新表中获取分析结果
        analysis = self.db.get_analysis_by_report_id(report_id)
        if not analysis:
            return {}
        
        # 将新格式转换为旧格式
        result = {}
        for step_name, step_data in analysis['steps'].items():
            result[step_name] = {
                'found': step_data['found'],
                'description': step_data['description'],
                'step_score': step_data['step_score'],
                'keywords': [],  # 旧格式需要这些字段，但新格式可能没有
                'evidence': [],
                'framework_summary': step_data.get('framework_summary', '')
            }
        
        return result
    
    def get_full_analysis_for_report(self, report_id: int) -> Dict:
        """
        获取研报的完整分析文本（适配旧接口）
        
        参数:
        report_id (int): 研报ID
        
        返回:
        dict: 包含完整分析文本和一句话总结的字典
        """
        # 从新表中获取分析结果
        analysis = self.db.get_analysis_by_report_id(report_id)
        if not analysis:
            return None
        
        # 将新格式转换为旧格式
        return {
            'full_analysis_text': analysis['full_analysis'],
            'one_line_summary': analysis['one_line_summary']
        }

def update_database_module():
    """更新database.py文件，替换对旧表的引用"""
    adapter_code = """
# 适配器函数，使用新表结构替代旧表
def get_analysis_results_for_report(report_id):
    \"\"\"
    获取研报的五步法分析结果（适配旧接口）
    
    参数:
    report_id (int): 研报ID
    
    返回:
    dict: 分析结果字典
    \"\"\"
    from analysis_db import AnalysisDatabase
    db = AnalysisDatabase()
    analysis = db.get_analysis_by_report_id(report_id)
    if not analysis:
        return {}
    
    # 将新格式转换为旧格式
    result = {}
    for step_name, step_data in analysis['steps'].items():
        result[step_name] = {
            'found': step_data['found'],
            'description': step_data['description'],
            'step_score': step_data['step_score'],
            'keywords': [],  # 旧格式需要这些字段，但新格式可能没有
            'evidence': [],
            'framework_summary': step_data.get('framework_summary', '')
        }
    
    return result

def get_full_analysis_for_report(report_id):
    \"\"\"
    获取研报的完整分析文本（适配旧接口）
    
    参数:
    report_id (int): 研报ID
    
    返回:
    dict: 包含完整分析文本和一句话总结的字典
    \"\"\"
    from analysis_db import AnalysisDatabase
    db = AnalysisDatabase()
    analysis = db.get_analysis_by_report_id(report_id)
    if not analysis:
        return None
    
    # 将新格式转换为旧格式
    return {
        'full_analysis_text': analysis['full_analysis'],
        'one_line_summary': analysis['one_line_summary']
    }
"""
    
    # 读取database.py文件
    try:
        with open('database.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找并替换旧的函数定义
        pattern_analysis_results = r'def get_analysis_results_for_report\(.*?return.*?\n\s*\n'
        pattern_full_analysis = r'def get_full_analysis_for_report\(.*?return.*?\n\s*\n'
        
        # 使用正则表达式替换函数定义
        import re
        content = re.sub(pattern_analysis_results, '', content, flags=re.DOTALL)
        content = re.sub(pattern_full_analysis, '', content, flags=re.DOTALL)
        
        # 在文件末尾添加新的适配器函数
        content += adapter_code
        
        # 写回文件
        with open('database.py', 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("已更新 database.py 文件")
        return True
    except Exception as e:
        print(f"更新 database.py 文件时出错: {e}")
        return False

def main():
    """主函数"""
    print("=== 数据库引用修复工具 ===")
    print("此工具将更新代码中对旧表的引用，使其使用新表结构")
    
    confirm = input("是否继续？(y/n): ")
    if confirm.lower() != 'y':
        print("操作已取消")
        return
    
    # 备份文件
    try:
        import shutil
        shutil.copy2('database.py', 'database.py.bak')
        print("已备份 database.py 文件")
    except Exception as e:
        print(f"备份文件时出错: {e}")
        confirm = input("是否继续而不备份？(y/n): ")
        if confirm.lower() != 'y':
            print("操作已取消")
            return
    
    # 更新数据库模块
    if update_database_module():
        print("代码引用已成功修复")
        print("现在您可以安全地删除旧表了")
    else:
        print("修复代码引用失败")
        print("您可以使用备份文件 database.py.bak 恢复代码")

if __name__ == "__main__":
    main() 