# 五步法研报检查器

基于黄燕铭投资五步法的研报自动化分析系统，使用Claude和DeepSeek大语言模型对研究报告进行深度语义分析。

![版本](https://img.shields.io/badge/版本-0.3.0-blue.svg)
![Python版本](https://img.shields.io/badge/Python-3.8%2B-brightgreen.svg)
![Flask版本](https://img.shields.io/badge/Flask-2.0%2B-red.svg)

## 项目简介

本项目是一个自动化分析金融研究报告的Web应用系统，采用黄燕铭的"五步法"分析框架，结合Claude和DeepSeek大语言模型进行深度语义分析，帮助投资者和分析师评估研究报告的质量和完整性。

### 黄燕铭五步法简介

五步法分析框架包括以下步骤：

1. **信息** - 收集和整理相关信息，包括公司公告、行业数据、政策变化等
2. **逻辑** - 基于信息进行分析推理，形成对市场或个股的基本判断
3. **超预期** - 寻找市场共识之外的信息点，发现被低估或高估的因素
4. **催化剂** - 找出能够促使价格变动的关键事件或因素
5. **结论** - 给出明确的投资建议，包括评级、目标价等

## 功能特点

- **智能分析**: 利用Claude和DeepSeek大语言模型进行研报内容的深度语义分析
- **多模型支持**: 支持Claude和DeepSeek两种大语言模型进行分析
- **数据爬取**: 自动从东方财富网等金融网站爬取最新研究报告
- **五步法评估**: 对研报应用黄燕铭五步法进行结构化评估
- **数据可视化**: 提供研报质量分布、行业分布等多维度的数据可视化
- **数据持久化**: 使用SQLite数据库存储研报数据和分析结果
- **全文搜索**: 支持对研报的标题、内容、行业等字段进行关键词搜索
- **多维度筛选**: 支持按行业、机构等维度进行研报筛选
- **可视化评分**: 使用雷达图、进度条等方式直观展示评分结果
- **响应式设计**: 适配各种屏幕尺寸，提供良好的移动端体验

## 技术栈

- **后端框架**: Flask
- **数据库**: SQLite
- **前端框架**: Bootstrap 5
- **图表库**: Chart.js
- **图标库**: Font Awesome
- **AI模型**: Anthropic Claude, DeepSeek
- **网络爬虫**: Requests, BeautifulSoup4

## 安装指南

### 先决条件

- Python 3.8+ 
- pip 包管理器

### 安装步骤

1. 克隆仓库:
```bash
git clone https://github.com/yourusername/five-step-report-inspector.git
cd five-step-report-inspector
```

2. 创建虚拟环境:
```bash
python -m venv venv
source venv/bin/activate  # 在Windows上: venv\Scripts\activate
```

3. 安装依赖:
```bash
pip install -r requirements.txt
```

4. 设置API密钥:
```bash
# 在Unix/Linux/Mac OS上
export CLAUDE_API_KEY=your_claude_api_key_here
export DEEPSEEK_API_KEY=your_deepseek_api_key_here

# 在Windows上
set CLAUDE_API_KEY=your_claude_api_key_here
set DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

5. 初始化数据库:
```bash
python init_db.py
```

## 使用方法

1. 启动应用:
```bash
python app.py
```

2. 在浏览器中访问:
```
http://127.0.0.1:5002
```

3. 点击"实时爬取"按钮获取最新研报数据

4. 浏览研报列表或使用搜索功能查找特定研报

5. 点击研报"详情"按钮查看五步法分析结果

## 版本历史

有关详细的版本历史和变更记录，请查看 [CHANGELOG.md](CHANGELOG.md) 文件。

## 项目结构

```
五步法研报检查器/
├── app.py                 # Flask应用主入口
├── main.py                # 爬虫和分析逻辑
├── database.py            # 数据库操作
├── claude_analyzer.py     # Claude API集成
├── deepseek_analyzer.py   # DeepSeek API集成
├── templates/             # HTML模板
│   ├── base.html          # 基础模板
│   ├── index.html         # 首页模板
│   ├── report_detail.html # 研报详情页模板
│   └── ...                # 其他模板
├── static/                # 静态资源
│   ├── css/               # CSS样式表
│   ├── js/                # JavaScript文件
│   └── img/               # 图像资源
├── research_reports.db    # SQLite数据库
├── research_reports.json  # 研报数据JSON备份
├── requirements.txt       # 项目依赖
└── README.md              # 项目说明
```

## 开发计划

- [x] 添加DeepSeek模型支持，扩展分析能力
- [ ] 添加更多数据源，扩展研报来源
- [ ] 实现自定义分析框架，不仅限于五步法
- [ ] 添加用户系统，支持个性化配置
- [ ] 实现研报比较功能，对比不同研报的分析结果
- [ ] 添加导出功能，支持将分析结果导出为PDF或Excel

## 贡献指南

欢迎贡献代码、报告问题或提出新功能建议。请遵循以下步骤:

1. Fork项目仓库
2. 创建您的特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交您的更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 打开Pull Request

## 许可证

本项目采用MIT许可证 - 详情请参见 [LICENSE](LICENSE) 文件。 