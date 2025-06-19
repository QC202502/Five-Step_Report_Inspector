#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
修复app.py中的缩进错误
"""

import re

def fix_app_py():
    print("Fixing indentation in app.py...")
    
    # Read app.py
    with open("app.py", "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    # Create a new list for fixed lines
    fixed_lines = []
    
    # Variables to track state
    in_report_notes = False
    in_get_method = False
    in_post_method = False
    in_generate_script = False
    
    # Process each line
    for i, line in enumerate(lines):
        # Check for function definitions
        if '@app.route(\'/api/report/<int:report_id>/notes\'' in line:
            in_report_notes = True
            fixed_lines.append(line)
            continue
            
        if in_report_notes and 'def report_notes' in line:
            fixed_lines.append(line)
            continue
            
        if in_report_notes and 'if request.method == \'GET\'' in line:
            in_get_method = True
            fixed_lines.append(line)
            continue
            
        if in_report_notes and 'elif request.method == \'POST\'' in line:
            in_get_method = False
            in_post_method = True
            fixed_lines.append(line)
            continue
            
        # Fix indentation in report_notes GET section
        if in_report_notes and in_get_method:
            if '# 获取笔记' in line and not line.strip().startswith('# 获取笔记'):
                fixed_lines.append('        # 获取笔记\n')
                continue
                
            if 'try:' in line and not line.strip().startswith('try:'):
                fixed_lines.append('        try:\n')
                continue
                
            if 'user_id = session[\'user\'][\'id\']' in line and not line.startswith('            '):
                fixed_lines.append('            user_id = session[\'user\'][\'id\']\n')
                continue
                
            if '# 从数据库获取笔记' in line and not line.startswith('            '):
                fixed_lines.append('            # 从数据库获取笔记\n')
                continue
                
            if 'conn = get_db_connection()' in line and not line.startswith('            '):
                fixed_lines.append('            conn = get_db_connection()\n')
                continue
                
            if 'cursor = conn.cursor()' in line and not line.startswith('            '):
                fixed_lines.append('            cursor = conn.cursor()\n')
                continue
        
        # Fix indentation in report_notes POST section
        if in_report_notes and in_post_method:
            if 'try:' in line and not line.strip().startswith('try:'):
                fixed_lines.append('        try:\n')
                continue
                
            if 'user_id = session[\'user\'][\'id\']' in line and not line.startswith('            '):
                fixed_lines.append('            user_id = session[\'user\'][\'id\']\n')
                continue
                
            if '# 检查内容长度' in line and not line.startswith('            '):
                fixed_lines.append('            # 检查内容长度\n')
                continue
                
            if 'conn = get_db_connection()' in line and not line.startswith('            '):
                fixed_lines.append('            conn = get_db_connection()\n')
                continue
                
            if 'cursor = conn.cursor()' in line and not line.startswith('            '):
                fixed_lines.append('            cursor = conn.cursor()\n')
                continue
                
        # Reset state when we hit a new route
        if in_report_notes and '@app.route' in line and '/api/report/<int:report_id>/notes' not in line:
            in_report_notes = False
            in_get_method = False
            in_post_method = False
            
        # Fix generate_video_script function
        if '@app.route(\'/generate_video_script/<int:report_id>\')' in line:
            in_generate_script = True
            fixed_lines.append(line)
            continue
            
        if in_generate_script and 'cursor = conn.cursor()' in line and not line.startswith('        '):
            fixed_lines.append('        cursor = conn.cursor()\n')
            continue
            
        if in_generate_script and 'conn.close()' in line and not line.startswith('        '):
            fixed_lines.append('        conn.close()\n')
            continue
            
        # Reset state when we hit a new route
        if in_generate_script and '@app.route' in line and '/generate_video_script' not in line:
            in_generate_script = False
            
        # Add the line unchanged for all other cases
            fixed_lines.append(line)
    
    # Write back the fixed file
    with open("app.py", "w", encoding="utf-8") as f:
        f.writelines(fixed_lines)
    
    print("Indentation fixed in app.py")

if __name__ == "__main__":
    fix_app_py() 