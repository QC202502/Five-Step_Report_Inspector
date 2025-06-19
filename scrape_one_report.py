#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 导入需要的模块
from main import scrape_research_reports, get_report_detail, analyze_with_five_steps
import database as db
import json
import time
import logging
import os
from dotenv import load_dotenv

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()
api_key = os.environ.get("DEEPSEEK_API_KEY")
logger.info(f"使用的API密钥: {api_key[:8]}..." if api_key else "未找到API密钥!")

def scrape_and_analyze_one():
    """爬取并分析单篇研报，保存到数据库"""
    try:
        # 东方财富网行业研报页面 URL
        url = "https://data.eastmoney.com/report/hyyb.html"
        logger.info(f"开始爬取研报列表，URL: {url}")
        
        # 爬取研报列表
        reports_data = scrape_research_reports(url)
        
        if not reports_data:
            logger.error("未爬取到研报数据，请检查网站结构是否已更新")
            # 如果无法爬取，创建一个示例研报用于测试
            reports_data = [{
                "title": "测试研报：A股市场走势分析",
                "link": "https://example.com/report/1",
                "abstract": "本报告分析了近期A股市场表现，发现市场呈现结构性机会。",
                "industry": "金融证券",
                "rating": "买入",
                "org": "样例证券",
                "date": "2025-06-16"
            }]
            logger.info("创建了一个示例研报用于测试")
            
        logger.info(f"获取到 {len(reports_data)} 条研报数据，将只处理第一条")
        
        # 只处理第一条研报
        report = reports_data[0]
        logger.info(f"处理研报: {report.get('title', 'N/A')}")
        
        # 获取研报详情
        content = None
        if "link" in report and report["link"].startswith("http"):
            content = get_report_detail(report['link'])
        
        # 如果无法获取内容，使用示例内容
        if not content or len(content) < 100:
            logger.warning("未能获取到有效研报内容，使用示例内容")
            content = f"""
            {report.get('title', '测试研报标题')}
            
            摘要：{report.get('abstract', '这是一份测试研报摘要，用于测试分析功能。')}
            
            一、市场回顾与展望
            近期市场波动较大，主要受到宏观经济数据和政策预期的影响。我们认为，当前市场处于底部区域，具有较好的配置价值。
            
            二、投资逻辑
            1. 政策面：近期多项政策出台，对市场形成支撑
            2. 基本面：企业盈利预期改善，部分行业景气度上升
            3. 估值：当前市场估值处于历史低位，具有吸引力
            
            三、超预期因素
            1. 流动性持续宽松超预期
            2. 外部环境改善超预期
            
            四、催化剂分析
            1. 短期催化剂：政策持续加码
            2. 中期催化剂：经济数据改善
            
            五、投资建议
            我们建议投资者积极布局，关注以下方向：
            1. 科技创新领域
            2. 消费升级方向
            3. 低估值蓝筹
            
            风险提示：政策不及预期，经济复苏不及预期
            """
            logger.info("生成了示例研报内容用于测试")
        
        # 使用DeepSeek五步法分析
        logger.info("开始使用DeepSeek分析研报")
        industry = report.get('industry', '未知行业')
        analysis = analyze_with_five_steps(
            report.get("abstract", ""),
            content,
            industry=industry
        )
        
        # 保存分析结果
        analyzed_report = {
            "title": report.get("title", "N/A"),
            "link": report.get("link", "N/A"),
            "abstract": report.get("abstract", "N/A"),
            "content_preview": content[:500] if content else "未获取到内容",
            "full_content": content,  # 存储完整内容
            "industry": industry,
            "rating": report.get("rating", "N/A"),
            "org": report.get("org", "N/A"),
            "date": report.get("date", "N/A"),
            "analysis": analysis,
            "analysis_method": "DeepSeek分析器"
        }
        
        # 将分析结果保存到数据库
        logger.info("保存研报到数据库")
        db_saved_count = db.save_reports_to_db([analyzed_report])
        
        # 同时保存到JSON文件（方便查看）
        with open('single_report.json', 'w', encoding='utf-8') as f:
            json.dump(analyzed_report, f, ensure_ascii=False, indent=4)
        
        logger.info(f"成功分析研报并保存到数据库，ID: {db_saved_count}")
        logger.info("分析结果已保存到 single_report.json 文件中")
        
        return True
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"处理过程中发生错误: {str(e)}\n{error_details}")
        return False

if __name__ == "__main__":
    scrape_and_analyze_one() 