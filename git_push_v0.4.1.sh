#!/bin/bash

# 显示当前Git状态
echo "当前Git状态："
git status

# 确认是否继续
echo "====================================="
echo "以上是当前Git状态，请确认是否继续推送？"
echo "按Enter键继续，Ctrl+C取消"
read -p ""

# 推送到远程仓库
echo "正在推送到远程仓库..."
git push origin main

echo "====================================="
echo "推送完成，当前Git状态："
git status 