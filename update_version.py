#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
版本更新脚本
用于自动更新项目中所有与版本相关的文件
"""

import os
import re
import sys
import datetime
import argparse
from pathlib import Path

def read_current_version():
    """读取当前版本号"""
    try:
        with open('VERSION', 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        print("错误: 未找到VERSION文件")
        return "0.0.0"

def update_version_file(new_version):
    """更新VERSION文件"""
    with open('VERSION', 'w') as f:
        f.write(new_version)
    print(f"✅ 已更新VERSION文件到 {new_version}")

def update_app_py(new_version):
    """更新app.py中的版本号"""
    file_path = 'app.py'
    if not os.path.exists(file_path):
        print(f"⚠️ 警告: 未找到{file_path}文件")
        return False
        
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 使用正则表达式替换版本号
    updated_content = re.sub(r'VERSION\s*=\s*"[0-9.]+"\s*', f'VERSION = "{new_version}"\n', content)
    
    if content == updated_content:
        print(f"⚠️ 警告: 无法在{file_path}中找到版本号定义")
        return False
        
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(updated_content)
        
    print(f"✅ 已更新{file_path}中的版本号到 {new_version}")
    return True

def update_readme(new_version):
    """更新README.md中的版本号和相关内容"""
    file_path = 'README.md'
    if not os.path.exists(file_path):
        print(f"⚠️ 警告: 未找到{file_path}文件")
        return False
        
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 使用正则表达式替换版本号
    updated_content = re.sub(r'版本-[0-9.]+', f'版本-{new_version}', content)
    
    # 从版本号判断是否为v0.5.0及以上版本（移除Claude分析器的版本）
    version_parts = [int(x) for x in new_version.split('.')]
    major, minor = version_parts[0], version_parts[1]
    
    # 如果是0.5.0及以上版本，确保README中只提到DeepSeek分析器
    if major == 0 and minor >= 5:
        # 更新分析引擎描述
        updated_content = re.sub(
            r'- \*\*多种分析引擎\*\*：支持 Claude 和 DeepSeek API 进行高质量语义分析',
            r'- **分析引擎**：使用 DeepSeek API 进行高质量语义分析',
            updated_content
        )
        
        # 更新项目结构，移除Claude分析器
        updated_content = re.sub(
            r'- `claude_analyzer.py`：Claude 分析器\n- `deepseek_analyzer.py`：DeepSeek 分析器',
            r'- `deepseek_analyzer.py`：DeepSeek 分析器',
            updated_content
        )
    
    if content == updated_content:
        print(f"⚠️ 警告: 无法在{file_path}中找到需要更新的内容")
        return False
        
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(updated_content)
        
    print(f"✅ 已更新{file_path}中的版本号和相关内容到 {new_version}")
    return True

def update_changelog(new_version, changes):
    """更新CHANGELOG.md，添加新版本的更新记录"""
    file_path = 'CHANGELOG.md'
    if not os.path.exists(file_path):
        print(f"⚠️ 警告: 未找到{file_path}文件")
        return False
    
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    
    # 准备新版本的更新记录
    new_version_entry = f"""
## v{new_version} ({today})

### 新增功能
{changes.get('features', '- 无')}

### 改进
{changes.get('improvements', '- 无')}

### 修复
{changes.get('fixes', '- 无')}

"""
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.readlines()
    
    # 在第一个版本记录之前插入新版本
    insert_index = 0
    for i, line in enumerate(content):
        if line.startswith('## v'):
            insert_index = i
            break
    
    content.insert(insert_index, new_version_entry)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(content)
        
    print(f"✅ 已更新{file_path}，添加了v{new_version}的更新记录")
    return True

def create_database_update_file(new_version):
    """创建新版本的数据库更新记录文件"""
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    file_path = f'database_update_v{new_version}.md'
    
    if os.path.exists(file_path):
        print(f"⚠️ 警告: {file_path}已存在，跳过创建")
        return False
    
    template = f"""# 数据库更新记录 v{new_version}

## 更新日期：{today}

## 主要更新内容

### 1. 数据库内容更新
- 添加新的研报数据
- 更新研报分析结果
- 优化数据库结构

### 2. 新增研报详情

| ID | 标题 | 行业 | 完整度分数 | 分析器 | 评价 |
|----|------|------|------------|--------|------|
|    |      |      |            |        |      |

### 3. 分析结果示例

- **信息**: 
- **逻辑**: 
- **超预期**: 
- **催化剂**: 
- **结论**: 

### 4. 改进建议示例

- 

## 数据库统计信息

- 当前研报总数：
- 本次新增研报数：
- 使用的分析器：
- 平均完整度分数：

## 技术细节

- 
"""
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(template)
        
    print(f"✅ 已创建{file_path}文件模板")
    return True

def create_git_push_script(new_version):
    """创建新版本的Git推送脚本"""
    file_path = f'git_push_v{new_version}.sh'
    
    if os.path.exists(file_path):
        print(f"⚠️ 警告: {file_path}已存在，跳过创建")
        return False
    
    script_content = f"""#!/bin/bash

echo "===== 五步法研报检查器 v{new_version} Git推送脚本 ====="
echo "当前Git状态:"
git status

echo -e "\\n是否继续推送? 按Enter继续，Ctrl+C取消"
read -p ""

echo "推送到远程仓库..."
git push origin main

echo "完成! 请检查GitHub上的仓库是否已更新"
"""
    
    with open(file_path, 'w') as f:
        f.write(script_content)
    
    # 设置执行权限
    os.chmod(file_path, 0o755)
    
    print(f"✅ 已创建{file_path}并设置执行权限")
    return True

def update_git_push_readme(new_version, old_version):
    """更新或创建Git推送指南"""
    file_path = 'GIT_PUSH_README.md'
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    
    # 检查版本号，为0.5.0及以上版本添加特殊说明
    version_parts = [int(x) for x in new_version.split('.')]
    major, minor = version_parts[0], version_parts[1]
    
    # 准备版本特定的更新内容
    version_specific_content = ""
    if major == 0 and minor >= 5:
        version_specific_content = "- 移除Claude分析器和关键词分析功能，仅使用DeepSeek API\n- 更新README.md以反映分析器变更\n"
    
    template = f"""# Git推送指南

## v{new_version}版本更新内容

本次更新（v{new_version}）主要包含以下内容：
{version_specific_content}- [在此添加主要更新内容]
- [在此添加主要更新内容]
- [在此添加主要更新内容]

## 已完成的操作

以下操作已经完成：
1. 更新VERSION文件为{new_version}
2. 更新CHANGELOG.md，添加v{new_version}版本的更新记录
3. 创建database_update_v{new_version}.md，详细记录数据库更新内容
4. 创建数据库备份（database_backups/v{new_version}/research_reports_v{new_version}_{today.replace('-', '')}.db）
5. 提交所有更改到本地Git仓库

## 如何推送到远程仓库

由于推送到远程仓库需要输入SSH密钥密码，我们已经创建了一个脚本来帮助您完成这一步骤：

```bash
# 在终端中执行以下命令
./git_push_v{new_version}.sh
```

执行脚本后，系统会显示当前Git状态，并询问是否继续推送。按Enter键继续，或按Ctrl+C取消。

如果您需要手动推送，可以使用以下命令：

```bash
git push origin main
```

## 确认更新成功

推送完成后，您可以通过以下方式确认更新是否成功：

1. 检查远程仓库是否显示最新提交
2. 验证VERSION文件是否已更新为{new_version}
3. 确认CHANGELOG.md中是否包含v{new_version}的更新记录
4. 确认database_update_v{new_version}.md文件是否已添加到仓库中
"""
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(template)
        
    print(f"✅ 已更新{file_path}，添加了v{new_version}的推送指南")
    return True

def create_backup_dir(new_version):
    """创建数据库备份目录"""
    today = datetime.datetime.now().strftime('%Y%m%d')
    backup_dir = f"database_backups/v{new_version}"
    
    os.makedirs(backup_dir, exist_ok=True)
    
    print(f"✅ 已创建数据库备份目录: {backup_dir}")
    return backup_dir

def main():
    parser = argparse.ArgumentParser(description="更新项目版本号")
    parser.add_argument('new_version', help='新版本号，例如: 0.4.2')
    parser.add_argument('--features', help='新版本的新增功能，多个条目用分号分隔')
    parser.add_argument('--improvements', help='新版本的改进，多个条目用分号分隔')
    parser.add_argument('--fixes', help='新版本的修复，多个条目用分号分隔')
    args = parser.parse_args()
    
    # 读取当前版本
    current_version = read_current_version()
    print(f"当前版本: {current_version}")
    print(f"新版本: {args.new_version}")
    
    # 确认是否继续
    confirm = input("是否继续更新版本? (y/n): ")
    if confirm.lower() != 'y':
        print("已取消版本更新")
        return
    
    # 处理更新日志内容
    changes = {}
    if args.features:
        changes['features'] = '\n'.join([f"- {item.strip()}" for item in args.features.split(';')])
    if args.improvements:
        changes['improvements'] = '\n'.join([f"- {item.strip()}" for item in args.improvements.split(';')])
    if args.fixes:
        changes['fixes'] = '\n'.join([f"- {item.strip()}" for item in args.fixes.split(';')])
    
    # 更新所有相关文件
    update_version_file(args.new_version)
    update_app_py(args.new_version)
    update_readme(args.new_version)
    update_changelog(args.new_version, changes)
    create_database_update_file(args.new_version)
    create_git_push_script(args.new_version)
    update_git_push_readme(args.new_version, current_version)
    backup_dir = create_backup_dir(args.new_version)
    
    print("\n✅ 版本更新完成!")
    print(f"当前版本: {args.new_version}")
    print(f"数据库备份目录: {backup_dir}")
    
    # 显示版本特定的信息
    version_parts = [int(x) for x in args.new_version.split('.')]
    major, minor = version_parts[0], version_parts[1]
    if major == 0 and minor >= 5:
        print("\n注意: 从v0.5.0开始，项目已移除Claude分析器和关键词分析功能，仅使用DeepSeek API")
        print("README.md已自动更新以反映这些变化")
    
    print("\n接下来的步骤:")
    print("1. 更新database_update_v{}.md文件，填写实际的数据库更新内容".format(args.new_version))
    print("2. 创建数据库备份")
    print("3. 使用git add和git commit提交所有更改")
    print("4. 使用./git_push_v{}.sh推送到远程仓库".format(args.new_version))

if __name__ == "__main__":
    main() 