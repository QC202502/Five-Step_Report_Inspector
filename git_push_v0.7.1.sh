#!/bin/bash

# 确保脚本在错误时退出
set -e

# 显示当前目录
echo "当前目录: $(pwd)"

# 检查是否有未提交的更改
if [ -n "$(git status --porcelain)" ]; then
    echo "添加所有更改到git"
    git add .
    
    echo "提交更改"
    git commit -m "v0.7.1: 添加用户偏好设置系统"
    
    echo "推送到远程仓库"
    git push origin main
    
    echo "创建标签 v0.7.1"
    git tag -a v0.7.1 -m "版本0.7.1: 添加用户偏好设置系统"
    
    echo "推送标签到远程仓库"
    git push origin v0.7.1
    
    echo "完成! 版本v0.7.1已成功推送"
else
    echo "没有需要提交的更改"
fi 