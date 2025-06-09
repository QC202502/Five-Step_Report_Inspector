# 五步法研报分析器

[![版本](https://img.shields.io/badge/版本-0.6.0-blue.svg?t=1701156201)](https://github.com/QC202502/Five-Step_Report_Inspector)
[![许可证](https://img.shields.io/badge/许可证-MIT-green.svg)](LICENSE)

基于黄燕铭五步法的研报分析工具，支持自动爬取、分析和评估研究报告的质量。

## 功能特点

- **研报爬取**：自动从东方财富网爬取最新行业研究报告
- **五步法分析**：使用黄燕铭五步法（信息、逻辑、超预期、催化剂、结论）分析研报质量
- **分析引擎**：使用 DeepSeek API 进行高质量语义分析
- **视频脚本生成**：基于五步法分析结果生成投资顾问口播文案
- **数据可视化**：直观展示研报分析结果和行业统计数据
- **数据库存储**：将研报和分析结果保存到 SQLite 数据库中，方便查询和管理

## 安装方法

### 环境要求

- Python 3.8+
- Chrome 浏览器（用于爬虫）

### 安装步骤

1. 克隆仓库

```bash
git clone https://github.com/yourusername/Five-Step_Report_Inspector.git
cd Five-Step_Report_Inspector
```

2. 安装依赖

```bash
pip install -r requirements.txt
```

3. 配置 API 密钥（可选，用于高级分析）

```bash
# 设置 DeepSeek API 密钥
export DEEPSEEK_API_KEY="your_deepseek_api_key"
```

## 使用说明

### 启动应用

```bash
python app.py
```

应用将在 http://127.0.0.1:5001 启动（或自动选择可用端口）。

### 爬取和分析研报

1. 访问首页，点击"爬取最新研报"按钮
2. 等待爬取和分析完成
3. 查看研报列表和分析结果

### 使用 DeepSeek 分析器

如果您想单独测试 DeepSeek 分析器，可以运行：

```bash
python test_crawl_and_analyze.py
```

请确保已设置 `DEEPSEEK_API_KEY` 环境变量。

## 项目结构

- `app.py`：主应用程序入口
- `main.py`：爬虫和分析核心功能
- `database.py`：数据库操作模块
- `analysis_db.py`：分析结果数据库操作
- `deepseek_analyzer.py`：DeepSeek 分析器
- `templates/`：前端模板文件
- `static/`：静态资源文件

## 更新日志

详见 [CHANGELOG.md](CHANGELOG.md)

## 许可证

MIT License 