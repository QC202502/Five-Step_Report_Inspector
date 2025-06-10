#!/bin/bash

# 设置颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}准备提交五步法研报分析器 v0.7.0 更新...${NC}"

# 添加所有更改的文件
git add .

# 提交更改
git commit -m "feat: 实现用户系统 v0.7.0

- 添加用户注册和登录功能
- 创建用户数据表结构
- 开发用户资料页面
- 实现会话管理和基本安全措施
- 添加用户权限管理功能
- 将推荐系统与用户系统集成"

# 推送到远程仓库
echo -e "${GREEN}正在推送更改到远程仓库...${NC}"
git push origin main

echo -e "${GREEN}完成! v0.7.0 已成功提交并推送。${NC}" 