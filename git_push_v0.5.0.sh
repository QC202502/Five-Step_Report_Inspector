#!/bin/bash

echo "===== 五步法研报检查器 v0.5.0 Git推送脚本 ====="
echo "当前Git状态:"
git status

echo -e "\n是否继续推送? 按Enter继续，Ctrl+C取消"
read -p ""

echo "推送到远程仓库..."
git push origin main

echo "完成! 请检查GitHub上的仓库是否已更新"
