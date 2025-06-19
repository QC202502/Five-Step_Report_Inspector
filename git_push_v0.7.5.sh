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
    git commit -m "v0.7.5: 修复评级和日期标签页跳转问题"
    
    echo "推送到远程仓库"
    git push origin main || {
        echo "HTTPS推送失败，尝试SSH方式..."
        git remote set-url origin git@github.com:QC202502/Five-Step_Report_Inspector.git
        git push origin main
    }
    
    echo "创建标签 v0.7.5"
    git tag -a v0.7.5 -m "版本0.7.5: 修复评级和日期标签页跳转问题"
    
    echo "推送标签到远程仓库"
    git push origin v0.7.5 || {
        echo "标签推送失败，请稍后手动执行: git push origin v0.7.5"
    }
    
    echo "完成! 版本v0.7.5已成功推送"
else
    echo "没有需要提交的更改，仅推送已提交的内容"
    
    echo "推送到远程仓库"
    git push origin main || {
        echo "HTTPS推送失败，尝试SSH方式..."
        git remote set-url origin git@github.com:QC202502/Five-Step_Report_Inspector.git
        git push origin main
    }
    
    echo "创建标签 v0.7.5"
    git tag -a v0.7.5 -m "版本0.7.5: 修复评级和日期标签页跳转问题"
    
    echo "推送标签到远程仓库"
    git push origin v0.7.5 || {
        echo "标签推送失败，请稍后手动执行: git push origin v0.7.5"
    }
    
    echo "完成! 版本v0.7.5已成功推送"
fi 