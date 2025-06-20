# Git推送指南

## v0.5.0版本更新内容

本次更新（v0.5.0）主要包含以下内容：
- 移除Claude分析器和关键词分析功能，仅使用DeepSeek API
- 更新README.md以反映分析器变更
- [在此添加主要更新内容]
- [在此添加主要更新内容]
- [在此添加主要更新内容]

## 已完成的操作

以下操作已经完成：
1. 更新VERSION文件为0.5.0
2. 更新CHANGELOG.md，添加v0.5.0版本的更新记录
3. 创建database_update_v0.5.0.md，详细记录数据库更新内容
4. 创建数据库备份（database_backups/v0.5.0/research_reports_v0.5.0_20250609.db）
5. 提交所有更改到本地Git仓库

## 如何推送到远程仓库

由于推送到远程仓库需要输入SSH密钥密码，我们已经创建了一个脚本来帮助您完成这一步骤：

```bash
# 在终端中执行以下命令
./git_push_v0.5.0.sh
```

执行脚本后，系统会显示当前Git状态，并询问是否继续推送。按Enter键继续，或按Ctrl+C取消。

如果您需要手动推送，可以使用以下命令：

```bash
git push origin main
```

## 确认更新成功

推送完成后，您可以通过以下方式确认更新是否成功：

1. 检查远程仓库是否显示最新提交
2. 验证VERSION文件是否已更新为0.5.0
3. 确认CHANGELOG.md中是否包含v0.5.0的更新记录
4. 确认database_update_v0.5.0.md文件是否已添加到仓库中
