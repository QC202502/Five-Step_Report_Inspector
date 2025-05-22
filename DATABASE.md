# 数据库设计与使用说明

## 概述

五步法研报检查器使用SQLite作为数据库引擎，通过`database.py`提供数据库操作接口。数据库设计简洁而高效，用于存储研报信息和分析结果，避免重复爬取，提高应用性能。

## 数据库结构

数据库包含两个主要表：

### 1. 研报表(reports)

存储研报的基本信息和元数据。

| 字段名 | 类型 | 说明 |
|-------|------|-----|
| id | INTEGER | 主键，自增 |
| title | TEXT | 研报标题，非空 |
| link | TEXT | 研报链接，唯一，非空 |
| abstract | TEXT | 研报摘要 |
| content_preview | TEXT | 内容预览 |
| full_content | TEXT | 完整内容 |
| industry | TEXT | 行业分类 |
| rating | TEXT | 评级 |
| org | TEXT | 发布机构 |
| date | TEXT | 发布日期 |
| analysis_method | TEXT | 分析方法 |
| completeness_score | INTEGER | 完整度分数 |
| created_at | TEXT | 创建时间 |
| updated_at | TEXT | 更新时间 |

### 2. 分析结果表(analysis_results)

存储每份研报的五步法分析结果。

| 字段名 | 类型 | 说明 |
|-------|------|-----|
| id | INTEGER | 主键，自增 |
| report_id | INTEGER | 关联研报ID，外键 |
| step_name | TEXT | 步骤名称（信息、逻辑、超预期、催化剂、结论） |
| found | INTEGER | 是否找到此步骤(0/1) |
| keywords | TEXT | JSON格式的匹配关键词列表 |
| evidence | TEXT | JSON格式的证据文本列表 |
| description | TEXT | 步骤说明 |

## 主要功能接口

`database.py`提供以下主要功能：

### 初始化与设置

- `init_db()`: 初始化数据库，创建表结构
- `get_db_connection()`: 获取数据库连接

### 数据操作

- `save_report_to_db(report_data)`: 保存单条研报及分析结果
- `save_reports_to_db(reports)`: 批量保存研报列表
- `get_reports_from_db(limit=100, offset=0)`: 获取研报列表
- `get_report_by_id(report_id)`: 通过ID获取单条研报
- `get_reports_by_industry(industry, limit=100)`: 按行业获取研报
- `search_reports(keyword, limit=100)`: 搜索研报
- `count_reports()`: 获取研报总数

### 导入导出

- `import_from_json(json_file='research_reports.json')`: 从JSON文件导入数据
- `export_to_json(json_file='exported_reports.json')`: 导出数据到JSON文件

## 使用示例

1. **初始化数据库**:
   ```python
   import database as db
   db.init_db()
   ```

2. **导入现有数据**:
   ```python
   db.import_from_json('research_reports.json')
   ```

3. **获取研报列表**:
   ```python
   reports = db.get_reports_from_db(limit=20)
   ```

4. **按行业筛选**:
   ```python
   tech_reports = db.get_reports_by_industry('科技行业')
   ```

5. **搜索研报**:
   ```python
   search_results = db.search_reports('人工智能')
   ```

## 性能注意事项

- 数据库使用`link`字段作为唯一键，确保不会重复保存相同研报
- 每次应用启动时会自动初始化数据库，并从JSON文件导入数据（如果数据库为空）
- 爬取新数据时，会同时保存到数据库和JSON文件（为了兼容性）

## 故障排除

如果遇到数据库问题：

1. 检查`research_reports.db`文件是否存在和有效
2. 尝试删除数据库文件并重新启动应用，将自动重建
3. 检查`research_reports.json`文件是否有效，作为备用数据源

## 未来改进计划

- 添加数据库迁移功能
- 实现更复杂的查询功能
- 添加数据库备份和恢复机制 