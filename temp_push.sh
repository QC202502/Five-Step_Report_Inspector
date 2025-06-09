#!/bin/bash

echo "===== 五步法研报检查器临时推送脚本 ====="

echo "1. 确认当前Git状态"
git status

echo -e "\n2. 尝试推送到远程仓库"
# 使用-v参数显示详细输出
git push -v origin main

echo -e "\n3. 如果上述推送失败，请手动执行以下命令之一："
echo "   a) 使用HTTPS方式推送（需要输入用户名和密码）："
echo "      ./https_push.sh"
echo "   b) 使用SSH方式推送（需要输入SSH密钥密码）："
echo "      ./ssh_push.sh"

echo -e "\n4. 完成"
echo "   请检查GitHub上的仓库是否已更新" 