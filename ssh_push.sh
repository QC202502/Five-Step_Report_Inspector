#!/bin/bash

echo "===== 五步法研报检查器 Git推送脚本 ====="
echo "1. 添加SSH密钥到SSH代理"
echo "请在提示时输入您的SSH密钥密码"
ssh-add ~/.ssh/id_ed25519

echo "2. 测试SSH连接到GitHub"
ssh -T git@github.com

echo "3. 确认远程仓库配置"
git remote -v

echo "4. 推送到远程仓库"
git push origin main

echo "5. 完成"
echo "请检查GitHub上的仓库是否已更新" 