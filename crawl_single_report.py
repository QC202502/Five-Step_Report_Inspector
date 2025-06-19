# -*- coding: utf-8 -*-
import os
import json
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import database as db
from deepseek_analyzer import DeepSeekAnalyzer

def scrape_research_reports():
    """
    爬取东方财富网研报列表
    """
    print("开始爬取东方财富网研报列表...")
    url = "https://data.eastmoney.com/report/industry.jshtml"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Referer': 'https://data.eastmoney.com/'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # 设置正确的编码
        if response.encoding == 'ISO-8859-1':
            response.encoding = response.apparent_encoding
        
        # 使用BeautifulSoup解析HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 查找研报列表表格
        table = soup.find('table', class_='tabgg')
        if not table:
            print("未找到研报列表表格")
            return []
        
        # 提取所有行（跳过表头）
        rows = table.find_all('tr')[1:]
        
        reports = []
        for row in rows:
            cells = row.find_all('td')
            
            if len(cells) >= 8:  # 确保有足够的单元格
                # 获取标题和链接
                title_cell = cells[0]
                title_link = title_cell.find('a')
                
                if title_link:
                    title = title_link.get_text(strip=True)
                    link = title_link.get('href')
                    
                    if not link.startswith('http'):
                        link = f"https://data.eastmoney.com{link}"
                    
                    # 获取行业、评级和机构
                    industry = cells[1].get_text(strip=True)
                    rating = cells[2].get_text(strip=True)
                    org = cells[3].get_text(strip=True)
                    
                    # 获取日期
                    date = cells[4].get_text(strip=True)
                    
                    # 创建研报数据结构
                    report = {
                        'title': title,
                        'link': link,
                        'industry': industry,
                        'rating': rating,
                        'org': org,
                        'date': date
                    }
                    
                    reports.append(report)
                    
        print(f"成功爬取 {len(reports)} 条研报数据")
        
        # 只返回第一条研报用于演示
        return reports[:1] if reports else []
        
    except Exception as e:
        print(f"爬取研报时出错: {e}")
        return []

def get_report_detail(url):
    """
    获取研报详细内容
    """
    print(f"正在获取研报详情: {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Referer': 'https://data.eastmoney.com/'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # 设置正确的编码
        if response.encoding == 'ISO-8859-1':
            response.encoding = response.apparent_encoding
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 获取报告摘要
        abstract = ""
        abstract_div = soup.find('div', class_='summary')
        if abstract_div:
            abstract = abstract_div.get_text(strip=True)
        
        # 获取报告全文
        content = ""
        
        # 优先查找 ctx-content 类，这是东方财富网研报内容的主要容器
        ctx_content = soup.find('div', class_='ctx-content')
        if ctx_content:
            paragraphs = ctx_content.find_all('p')
            if paragraphs:
                content = '\n'.join([p.get_text(strip=True) for p in paragraphs])
        
        # 如果没有找到内容，尝试其他可能的内容容器
        if not content:
            content_div = soup.find('div', class_='report-content')
            if content_div:
                content = content_div.get_text(strip=True)
            else:
                content_div = soup.find('div', class_='newsContent')
                if content_div:
                    content = content_div.get_text(strip=True)
                else:
                    content_div = soup.find('div', id='ContentBody')
                    if content_div:
                        content = content_div.get_text(strip=True)
        
        # 保存完整的网页内容以便调试
        with open("report_content_debug.html", "w", encoding="utf-8") as f:
            f.write(str(soup))
        
        print(f"获取到研报内容，长度: {len(content)} 字符")
        
        return {
            'abstract': abstract,
            'content': content
        }
        
    except Exception as e:
        print(f"获取研报详情时出错: {e}")
        return {'abstract': "", 'content': ""}

def analyze_with_deepseek(title, content, industry):
    """
    使用DeepSeek分析研报
    """
    print(f"开始使用DeepSeek分析研报: {title}")
    
    try:
        analyzer = DeepSeekAnalyzer()
        analysis_result = analyzer.analyze_with_five_steps(title, content, industry)
        
        print("分析完成")
        return analysis_result
    except Exception as e:
        print(f"分析研报时出错: {e}")
        return None

def save_results_to_json(data, filename="crawled_report.json"):
    """
    保存结果到JSON文件
    """
    try:
        # 确保格式化输出并使用UTF-8编码
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"已保存结果到文件: {filename}")
    except Exception as e:
        print(f"保存结果到文件时出错: {e}")

def main():
    """
    主函数
    """
    print("=" * 50)
    print("开始爬取并分析单个研报")
    print("=" * 50)
    
    # 1. 爬取研报列表
    reports = scrape_research_reports()
    
    if not reports:
        print("未获取到研报数据，程序结束")
        return
    
    # 获取第一条研报
    report = reports[0]
    print(f"选择第一条研报进行分析: {report['title']}")
    
    # 2. 获取研报详情
    detail = get_report_detail(report['link'])
    
    # 将详情添加到研报数据中
    report['abstract'] = detail['abstract']
    report['content_preview'] = detail['content'][:500] + "..." if len(detail['content']) > 500 else detail['content']
    report['full_content'] = detail['content']
    
    # 3. 进行五步法分析
    analysis_result = analyze_with_deepseek(report['title'], detail['content'], report['industry'])
    
    if analysis_result:
        # 将分析结果添加到研报数据中
        report['analysis'] = analysis_result
        report['analysis_method'] = 'DeepSeek五步法'
        
        # 4. 保存到数据库
        report_id = db.save_report_to_db(report)
        
        if report_id > 0:
            print(f"成功保存研报到数据库，ID: {report_id}")
        else:
            print("保存到数据库失败")
        
        # 5. 保存到JSON文件
        save_results_to_json(report)
    else:
        print("分析失败，无法获取分析结果")
    
    print("=" * 50)
    print("程序执行完毕")
    print("=" * 50)

if __name__ == "__main__":
    main() 