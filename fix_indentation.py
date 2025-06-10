#!/usr/bin/env python3
import re

# 读取原始文件
with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 查找并修复缩进问题
fixed_lines = []
in_analyze_report = False
for i, line in enumerate(lines):
    if 'def analyze_report(report_id):' in line:
        in_analyze_report = True
        fixed_lines.append(line)
    elif in_analyze_report and 'try:' in line and line.strip() != 'try:':
        # 修复try行的缩进
        fixed_lines.append('    try:\n')
    elif in_analyze_report and ('# 使用DeepSeek分析器' in line or 
                              'from deepseek_analyzer' in line or 
                              'analyzer = DeepSeekAnalyzer()' in line or
                              'analysis_result = analyzer.analyze_with_five_steps' in line or
                              '# 保存分析结果到数据库' in line or
                              'analysis_db = AnalysisDatabase()' in line or
                              'analysis_db.save_analysis_result' in line or
                              'flash(\'使用DeepSeek分析完成\'' in line):
        # 修复try块内的代码缩进
        fixed_lines.append('        ' + line.lstrip())
    elif in_analyze_report and 'except Exception as e:' in line:
        # 修复except行的缩进
        fixed_lines.append('    except Exception as e:\n')
        in_analyze_report = False  # 结束analyze_report函数的特殊处理
    elif not in_analyze_report or 'flash(f\'分析失败:' not in line:
        # 其他行直接添加
        fixed_lines.append(line)
    else:
        # 修复except块内的代码缩进
        fixed_lines.append('        ' + line.lstrip())

# 保存修复后的文件
with open('app.py', 'w', encoding='utf-8') as f:
    f.writelines(fixed_lines)

print("app.py中的缩进问题已修复")
