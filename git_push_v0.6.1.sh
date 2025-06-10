#!/bin/bash

# 设置版本号
VERSION="0.6.1"

# 显示当前工作目录
echo "当前工作目录: $(pwd)"

# 显示Git状态
echo "Git状态:"
git status

# 添加所有更改的文件
echo "添加所有更改的文件..."
git add .

# 提交更改
echo "提交更改..."
git commit -m "v$VERSION: 添加研报推荐功能，实现已读/未读状态管理"

# 推送到远程仓库
echo "推送到远程仓库..."
git push origin master

echo "完成! v$VERSION 已成功提交和推送。" 