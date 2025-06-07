#!/bin/bash

echo "===== 五步法研报检查器 HTTPS推送脚本 ====="

echo "1. 将远程仓库URL更改为HTTPS格式"
git remote set-url origin https://github.com/QC202502/Five-Step_Report_Inspector.git

echo "2. 确认远程仓库配置"
git remote -v

echo "3. 推送到远程仓库"
echo "请在提示时输入您的GitHub用户名和密码（或个人访问令牌）"
git push origin main

echo "4. 完成"
echo "请检查GitHub上的仓库是否已更新"

echo "5. 恢复SSH配置（如果需要）"
echo "如果您想恢复SSH配置，请运行以下命令："
echo "git remote set-url origin git@github.com:QC202502/Five-Step_Report_Inspector.git" 