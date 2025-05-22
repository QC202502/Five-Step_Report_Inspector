# 五步法研报检查器 (Five-Step Report Inspector)

一个基于Flask的web应用，用于爬取和分析金融研究报告，并使用黄燕铭五步分析法对研报质量进行评估。

## 项目介绍

本项目基于黄燕铭的五步分析方法，通过网络爬虫从东方财富网获取最新的研究报告，并对其内容进行结构化分析。系统会检查研报中是否包含五步分析法的各个要素：信息收集、逻辑推理、超预期发现、催化剂识别和结论建议，并给出综合评分。

## 核心功能

- 实时爬取东方财富网的最新研究报告
- 使用五步分析法评估研报质量
- 可视化展示研报分析结果
- 支持Claude人工智能增强分析
- 提供详细的研报内容和分析详情

## 技术栈

- **后端**: Python, Flask
- **前端**: HTML, CSS, JavaScript, Bootstrap
- **数据分析**: Beautiful Soup, Claude API
- **网页爬虫**: Selenium, Requests
- **数据可视化**: Chart.js

## 安装与使用

1. 克隆仓库
   ```
   git clone https://github.com/yourusername/Five-Step_Report_Inspector.git
   cd Five-Step_Report_Inspector
   ```

2. 安装依赖
   ```
   pip install -r requirements.txt
   ```

3. 运行应用
   ```
   python app.py
   ```

4. 访问 `http://127.0.0.1:5001` 即可使用

## 主要页面

- **首页**: 显示已爬取的研报列表
- **研报详情**: 展示具体研报的五步分析结果
- **统计分析**: 展示所有研报的五步法应用情况统计

## 五步分析法简介

1. **信息**: 收集和整理相关信息，包括公司公告、行业数据、政策变化等
2. **逻辑**: 基于信息进行分析推理，形成对市场或个股的基本判断
3. **超预期**: 寻找市场共识之外的信息点，发现被低估或高估的因素
4. **催化剂**: 找出能够促使价格变动的关键事件或因素
5. **结论**: 给出明确的投资建议，包括评级、目标价等

## 项目结构

```
Five-Step_Report_Inspector/
├── app.py                # Flask应用主程序
├── main.py               # 爬虫和分析核心逻辑
├── claude_analyzer.py    # Claude AI分析模块
├── requirements.txt      # 项目依赖
├── static/               # 静态资源
│   ├── css/              # CSS样式文件
│   ├── js/               # JavaScript脚本
│   └── img/              # 图片资源
└── templates/            # HTML模板
    ├── index.html        # 首页模板
    ├── report_detail.html # 研报详情页模板
    └── stats.html        # 统计分析页模板
```

## 注意事项

- 本项目仅作为学习和研究使用，请勿用于商业目的
- 爬取网站内容时请遵守相关网站的使用条款和robots.txt规定
- Claude分析功能需要配置相应的API密钥才能使用 