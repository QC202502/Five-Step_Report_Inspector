# -*- coding: utf-8 -*-
import requests
from bs4 import BeautifulSoup
import json # 导入json库
import time
import os
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import sys
try:
    from chromedriver_py import binary_path  # 导入chromedriver-py提供的二进制路径
    print(f"ChromeDriver binary path: {binary_path}")
    chrome_driver_available = True
except ImportError:
    print("chromedriver_py未安装，请运行: python -m pip install chromedriver-py")
    chrome_driver_available = False

# 导入DeepSeek分析器
try:
    from deepseek_analyzer import DeepSeekAnalyzer
    deepseek_analyzer = DeepSeekAnalyzer()
    deepseek_available = True
    print("DeepSeek分析器初始化成功")
except ImportError:
    print("未找到DeepSeek分析器模块，将无法进行分析")
    deepseek_available = False
except Exception as e:
    print(f"初始化DeepSeek分析器时出错: {str(e)}")
    deepseek_available = False

def get_report_detail(url):
    """
    获取研报详情内容
    """
    print(f"正在获取研报详情: {url}")
    
    try:
        # 首先尝试使用requests获取研报详情页
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://data.eastmoney.com/'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # 设置正确的编码
        if response.encoding == 'ISO-8859-1':
            response.encoding = response.apparent_encoding
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 尝试提取研报内容
        content = ""
        
        # 优先查找 ctx-content 类，这是东方财富网研报内容的主要容器
        ctx_content = soup.find('div', class_='ctx-content')
        if ctx_content:
            # 提取所有段落文本
            paragraphs = ctx_content.find_all('p')
            if paragraphs:
                content = '\n'.join([p.get_text(strip=True) for p in paragraphs])
                print("成功从ctx-content提取研报内容")
        
        # 如果上述方法失败，尝试其他可能的内容容器
        if not content:
            # 检查特定的zw_industry页面结构
            content_div = soup.find('div', class_='report-content')
            if content_div:
                # 移除不需要的元素
                [s.extract() for s in content_div.select('style, script')]
                content = content_div.get_text(strip=True)
                print("成功从report-content提取研报内容")
            else:
                # 尝试查找研报正文内容 (可能的其他标记)
                content_div = soup.find('div', class_='newsContent')
                if content_div:
                    content = content_div.get_text(strip=True)
                    print("成功从newsContent提取研报内容")
                else:
                    # 尝试其他可能的内容容器
                    content_div = soup.find('div', id='ContentBody')
                    if content_div:
                        content = content_div.get_text(strip=True)
                        print("成功从ContentBody提取研报内容")
                    else:
                        # 尝试zw-content类
                        zw_content = soup.find('div', class_='zw-content')
                        if zw_content:
                            # 查找其中的内容部分
                            ctx_box = zw_content.find('div', class_='ctx-box')
                            if ctx_box:
                                paragraphs = ctx_box.find_all('p')
                                if paragraphs:
                                    content = '\n'.join([p.get_text(strip=True) for p in paragraphs])
                                    print("成功从zw-content/ctx-box提取研报内容")
            
        if content:  # 如果通过requests获取到了任何内容
            print(f"成功通过requests获取研报内容，长度: {len(content)} 字符")
            # 记录完整内容长度，同时显示部分预览用于调试
            preview = content[:100].replace('\n', ' ') if len(content) > 100 else content.replace('\n', ' ')
            print(f"内容预览: {preview}...")
            return content # 直接返回，不再检查长度是否大于500
        else:
            # 只有当requests完全没有获取到内容时，才打印这条信息并尝试Selenium
            print(f"使用requests未能获取到研报内容，尝试使用Selenium方法...")
        
        # 如果requests未能获取到内容，尝试使用Selenium获取完整内容
        if chrome_driver_available:
            try:
                print("使用Selenium获取研报详情...")
                
                # 设置Chrome选项
                chrome_options = Options()
                chrome_options.add_argument("--headless")  # 无头模式
                chrome_options.add_argument("--disable-gpu")
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                
                # 创建Service对象
                service = Service(executable_path=binary_path)
                
                # 初始化Chrome浏览器
                driver = webdriver.Chrome(service=service, options=chrome_options)
                
                try:
                    # 访问URL
                    driver.get(url)
                    
                    # 等待页面加载
                    time.sleep(5)  # 等待JavaScript加载
                    
                    # 获取页面源码
                    page_source = driver.page_source
                    
                    # 使用BeautifulSoup解析
                    soup = BeautifulSoup(page_source, 'html.parser')
                    
                    # 保存页面源码以便调试
                    with open("report_detail_selenium.html", "w", encoding="utf-8") as f:
                        f.write(page_source)
                    print("已保存研报详情页源码到 report_detail_selenium.html 文件")
                    
                    # 尝试提取研报内容 - 使用更多针对性的选择器
                    content = ""
                    
                    # 优先查找 ctx-content 类，这是东方财富网研报内容的主要容器
                    ctx_content = soup.find('div', class_='ctx-content')
                    if ctx_content:
                        # 提取所有段落文本
                        paragraphs = ctx_content.find_all('p')
                        if paragraphs:
                            content = '\n'.join([p.get_text(strip=True) for p in paragraphs])
                            print("成功从ctx-content提取研报内容")
                            
                    # 如果未找到ctx-content，尝试其他容器
                    if not content:
                        # 尝试获取zw-content下的内容
                        zw_content = soup.find('div', class_='zw-content')
                        if zw_content:
                            # 查找其中的内容部分
                            ctx_box = zw_content.find('div', class_='ctx-box')
                            if ctx_box:
                                paragraphs = ctx_box.find_all('p')
                                if paragraphs:
                                    content = '\n'.join([p.get_text(strip=True) for p in paragraphs])
                                    print("成功从zw-content/ctx-box提取研报内容")
                            
                        # 如果还是没有找到，尝试更多可能的容器
                        if not content:
                            # 尝试研报正文内容的其他可能位置
                            content_div = soup.find('div', class_='report-content')
                            if content_div:
                                [s.extract() for s in content_div.select('style, script')]
                                content = content_div.get_text(strip=True)
                                print("成功从report-content提取研报内容")
                            else:
                                content_div = soup.find('div', class_='newsContent')
                                if content_div:
                                    content = content_div.get_text(strip=True)
                                    print("成功从newsContent提取研报内容")
                                else:
                                    content_div = soup.find('div', id='ContentBody')
                                    if content_div:
                                        content = content_div.get_text(strip=True)
                                        print("成功从ContentBody提取研报内容")
                                    else:
                                        # 尝试提取class="content"的内容
                                        content_divs = soup.find_all('div', class_='content')
                                        if content_divs:
                                            for div in content_divs:
                                                # 检查是否包含有意义的文本内容
                                                text = div.get_text(strip=True)
                                                if len(text) > 500:  # 有意义的内容通常较长
                                                    content = text
                                                    print("成功从content类提取研报内容")
                                                    break
                    
                    # 如果上述所有方法都失败，尝试清理的方式提取body内容
                    if not content or len(content) < 500:
                        body = soup.find('body')
                        if body:
                            # 去除脚本、样式、导航、页眉、页脚等
                            for tag in body.select('script, style, header, footer, nav, .header, .footer, .nav, .menu, .sidebar, .ad'):
                                tag.extract()
                            
                            # 尝试仅提取正文区域
                            main_content = body.find('div', class_=['main', 'main-content', 'content-main', 'article', 'article-content'])
                            if main_content:
                                content = main_content.get_text(strip=True)
                                print("成功从主内容区域提取研报内容")
                            else:
                                # 如果没有明确的主内容区域，提取所有段落
                                paragraphs = body.find_all('p')
                                if paragraphs and len(paragraphs) > 5:  # 有意义的内容通常有多个段落
                                    content = '\n'.join([p.get_text(strip=True) for p in paragraphs])
                                    print("成功从所有段落提取研报内容")
                                else:
                                    # 最后的方法：提取清理后的body内容
                                    content = body.get_text(strip=True)
                                    # 移除多余空格
                                    content = re.sub(r'\s+', ' ', content).strip()
                                    print("成功提取清理后的页面文本")
                    
                    if content:
                        print(f"使用Selenium成功获取研报内容，长度: {len(content)} 字符")
                        preview = content[:100].replace('\n', ' ') if len(content) > 100 else content.replace('\n', ' ')
                        print(f"内容预览: {preview}...")
                    else:
                        print("使用Selenium未能找到研报内容")
                    
                except Exception as e:
                    print(f"Selenium获取研报详情时出错: {e}")
                    import traceback
                    traceback.print_exc()
                finally:
                    # 关闭浏览器
                    driver.quit()
                
                # 如果Selenium方法获取到内容，则返回，否则返回原来的内容
                if content:
                    return content
            except Exception as e:
                print(f"使用Selenium获取研报详情时出错: {e}")
                import traceback
                traceback.print_exc()
                
        # 如果都失败了，返回之前获取的内容（即使可能不完整）
        print("返回通过requests获取的研报内容")
        return content
    except Exception as e:
        print(f"获取研报详情时出错: {e}")
        return ""

def get_page_with_requests(url):
    """
    使用requests库获取页面内容的备选方法
    """
    print(f"正在使用requests库获取页面: {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Referer': 'https://data.eastmoney.com/'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()  # 如果状态码不是200，抛出异常
        
        # 设置正确的编码
        if response.encoding == 'ISO-8859-1':
            response.encoding = response.apparent_encoding
        
        page_source = response.text
        print(f"获取到页面内容，长度: {len(page_source)} 字符")
        
        # 保存页面源码以便调试
        with open("page_source_requests.html", "w", encoding="utf-8") as f:
            f.write(page_source)
        print("已保存页面源码到 page_source_requests.html 文件")
        
        return page_source
    except Exception as e:
        print(f"使用requests获取页面时出错: {e}")
        import traceback
        traceback.print_exc()
        return None

def parse_reports_from_page(page_source):
    """
    从页面内容解析研究报告，增强解析能力以适应网站结构变化
    """
    print("正在解析页面内容...")
    
    soup = BeautifulSoup(page_source, 'html.parser')
    
    # 尝试直接查找表格行
    print("尝试查找研报列表...")
    
    reports_list = []
    
    # 检查是否是新版东方财富网页面结构
    is_new_structure = False
    if "研报列表" in page_source or "行业研报" in page_source:
        print("检测到新版东方财富网页面结构")
        is_new_structure = True
    
    # 如果是新版结构，尝试查找表格行
    if is_new_structure:
        # 查找表格行
        rows = soup.find_all('tr')
        print(f"找到 {len(rows)} 个表格行")
        
        for row in rows:
            try:
                # 查找研报标题和链接
                title_cell = row.find('a', href=lambda href: href and ('zw_industry.jshtml' in href or 'zw_stock.jshtml' in href))
                if not title_cell:
                    continue
                
                title = title_cell.get_text(strip=True)
                href = title_cell.get('href')
                
                if href.startswith('//'):
                    full_link = f"https:{href}"
                elif href.startswith('/'):
                    full_link = f"https://data.eastmoney.com{href}"
                else:
                    full_link = href
                
                # 获取行所有单元格
                cells = row.find_all('td')
                
                # 打印调试信息
                print(f"研报标题: {title}")
                print(f"研报链接: {full_link}")
                print(f"单元格数量: {len(cells)}")
                
                # 提取行业信息 - 行业通常在第一列或特定列
                industry = "未知行业"
                rating = ""
                org = ""
                date = ""
                
                # 查找行业列
                industry_cell = None
                
                # 检查是否有行业列标题
                headers = soup.find_all('th')
                industry_col_index = -1
                for i, header in enumerate(headers):
                    header_text = header.get_text(strip=True)
                    if "行业" in header_text:
                        industry_col_index = i
                        print(f"找到行业列索引: {industry_col_index}")
                        break
                
                # 如果找到行业列索引，尝试从对应单元格获取行业信息
                if industry_col_index >= 0 and industry_col_index < len(cells):
                    industry_cell = cells[industry_col_index]
                    industry_text = industry_cell.get_text(strip=True)
                    # 检查是否是数字（如15、14等）
                    if industry_text and not industry_text.isdigit():
                        industry = industry_text
                    else:
                        # 如果是数字，尝试查找行业图标或其他指示
                        industry_icon = industry_cell.find('i', class_=lambda c: c and 'icon' in c.lower())
                        if industry_icon and industry_icon.get('title'):
                            industry = industry_icon.get('title')
                        elif industry_cell.find('img') and industry_cell.find('img').get('alt'):
                            industry = industry_cell.find('img').get('alt')
                
                # 如果仍未找到行业，尝试从所有单元格中查找
                if industry == "未知行业":
                    for i, cell in enumerate(cells):
                        cell_text = cell.get_text(strip=True)
                        # 常见行业名称
                        common_industries = ["食品饮料", "医药", "金融", "科技", "消费", "通信", "电子", "计算机", "汽车", "房地产", "能源", "化工"]
                        for ind in common_industries:
                            if ind in cell_text:
                                industry = ind
                                break
                        if industry != "未知行业":
                            break
                
                # 查找评级、机构和日期
                for i, cell in enumerate(cells):
                    cell_text = cell.get_text(strip=True)
                    
                    # 评级通常包含特定关键词
                    if cell_text in ["买入", "增持", "中性", "减持", "卖出", "强烈推荐", "推荐", "谨慎推荐", "持有", "回避"]:
                        rating = cell_text
                    
                    # 机构通常包含"证券"等关键词
                    if "证券" in cell_text or "研究" in cell_text or "资本" in cell_text:
                        org = cell_text
                    
                    # 日期通常是YYYY-MM-DD格式
                    if re.match(r'\d{4}-\d{2}-\d{2}', cell_text) or re.match(r'\d{4}/\d{2}/\d{2}', cell_text):
                        date = cell_text
                
                # 如果仍然没有找到行业，尝试从标题中提取
                if industry == "未知行业" and title:
                    # 常见行业关键词
                    industry_keywords = ["医药", "科技", "金融", "消费", "房地产", "能源", "通信", "汽车", "食品", "电子", "互联网", "计算机", "传媒"]
                    for keyword in industry_keywords:
                        if keyword in title:
                            industry = keyword
                            break
                
                # 构建报告摘要
                abstract = f"行业: {industry}, 评级: {rating}, 机构: {org}, 日期: {date}"
                
                reports_list.append({
                    "title": title,
                    "link": full_link,
                    "abstract": abstract,
                    "industry": industry,
                    "rating": rating,
                    "org": org,
                    "date": date
                })
                print(f"解析到研报: {title}, 行业: {industry}")
            except Exception as e:
                print(f"解析行时出错: {e}")
                continue
    
    # 如果没有找到研报或不是新版结构，尝试旧版解析方法
    if not reports_list:
        # 方法1: 查找所有研报链接，格式为 /report/zw_industry.jshtml?infocode=XX
        report_links = soup.find_all('a', href=lambda href: href and ('zw_industry.jshtml' in href or 'zw_stock.jshtml' in href))
        print(f"找到 {len(report_links)} 个研报链接")
        
        if report_links:
            for link in report_links:
                try:
                    # 获取研报标题
                    title = link.get_text(strip=True)
                    if not title:
                        continue
                    
                    # 获取研报链接
                    href = link.get('href')
                    if href.startswith('//'):
                        full_link = f"https:{href}"
                    elif href.startswith('/'):
                        full_link = f"https://data.eastmoney.com{href}"
                    else:
                        full_link = href
                    
                    # 查找所在行或父元素
                    row = link.find_parent('tr')
                    if not row:
                        # 如果找不到tr父元素，尝试查找其他包含元素
                        row = link.find_parent('div', class_=lambda c: c and ('item' in c.lower() or 'row' in c.lower()))
                    
                    # 初始化变量
                    industry = "未知行业"
                    rating = ""
                    org = ""
                    date = ""
                    
                    if row:
                        # 尝试从行中提取信息
                        # 查找所有文本节点
                        all_texts = [text for text in row.stripped_strings]
                        
                        # 打印调试信息
                        print(f"行内文本: {all_texts}")
                        
                        # 尝试根据位置或特征提取信息
                        if len(all_texts) >= 3:
                            # 根据常见格式，尝试提取行业、评级、机构、日期
                            for text in all_texts:
                                # 尝试识别行业
                                if len(text) < 10 and not text.isdigit() and (not industry or industry == "未知行业"):
                                    industry = text
                                
                                # 尝试识别评级
                                if text in ["买入", "增持", "中性", "减持", "卖出", "强烈推荐", "推荐", "谨慎推荐", "持有", "回避"]:
                                    rating = text
                                
                                # 尝试识别日期 (YYYY-MM-DD格式)
                                if re.match(r'\d{4}-\d{2}-\d{2}', text) or re.match(r'\d{4}/\d{2}/\d{2}', text):
                                    date = text
                                
                                # 尝试识别机构 (通常包含"证券"、"研究"等字样)
                                if "证券" in text or "研究" in text or "资本" in text or "投资" in text:
                                    org = text
                    
                    # 如果没有找到行业信息，尝试从标题中提取
                    if industry == "未知行业" and title:
                        # 常见行业关键词
                        industry_keywords = ["医药", "科技", "金融", "消费", "房地产", "能源", "通信", "汽车", "食品", "电子", "互联网", "计算机", "传媒"]
                        for keyword in industry_keywords:
                            if keyword in title:
                                industry = keyword
                                break
                    
                    # 构建报告摘要
                    abstract = f"行业: {industry}, 评级: {rating}, 机构: {org}, 日期: {date}"
                    
                    reports_list.append({
                        "title": title,
                        "link": full_link,
                        "abstract": abstract,
                        "industry": industry,
                        "rating": rating,
                        "org": org,
                        "date": date
                    })
                    print(f"解析到研报: {title}, 行业: {industry}")
                except Exception as e:
                    print(f"解析研报链接时出错: {e}")
                    continue
    
    # 如果未找到任何研报，使用更广泛的搜索方法
    if not reports_list:
        print("未找到任何研报，使用更广泛的搜索方法...")
        
        # 方法2: 查找所有可能的研报链接
        all_links = soup.find_all('a')
        for link in all_links:
            try:
                href = link.get('href', '')
                title = link.get_text(strip=True)
                
                # 如果链接包含特定关键词且有标题文本
                if (('report' in href or 'research' in href or 'pdf' in href) and title and len(title) > 5):
                    if href.startswith('//'):
                        full_link = f"https:{href}"
                    elif href.startswith('/'):
                        full_link = f"https://data.eastmoney.com{href}"
                    else:
                        full_link = href
                    
                    # 尝试从标题中提取行业信息
                    industry = "未能确定行业"
                    industry_keywords = ["医药", "科技", "金融", "消费", "房地产", "能源", "通信", "汽车", "食品", "电子", "互联网", "计算机", "传媒"]
                    for keyword in industry_keywords:
                        if keyword in title:
                            industry = keyword
                            break
                    
                    reports_list.append({
                        "title": title,
                        "link": full_link,
                        "abstract": f"行业: {industry}",
                        "industry": industry,
                        "rating": "",
                        "org": "",
                        "date": ""
                    })
                    print(f"广泛搜索解析到研报: {title}, 行业: {industry}")
            except Exception as e:
                print(f"广泛搜索解析链接时出错: {e}")
    
    print(f"共解析出 {len(reports_list)} 条研报数据")
    return reports_list

def scrape_research_reports(url):
    """
    使用 Selenium 爬取东方财富网的研究报告摘要。
    如果Selenium方法失败，将使用requests备选方法。
    """
    print(f"正在使用 Selenium 爬取页面：{url}")

    driver = None # 初始化 driver 为 None
    try:
        if not chrome_driver_available:
            print("ChromeDriver不可用，将使用requests备选方法")
            page_source = get_page_with_requests(url)
            if page_source:
                return parse_reports_from_page(page_source)
            return []
        
        # 设置Chrome选项，改进浏览器配置以提高稳定性
        chrome_options = Options()
        chrome_options.add_argument("--window-size=1920,1080")  # 设置固定窗口大小
        chrome_options.add_argument("--disable-extensions")  # 禁用扩展
        chrome_options.add_argument("--disable-gpu")  # 禁用GPU加速
        chrome_options.add_argument("--no-sandbox")  # 禁用沙箱模式
        chrome_options.add_argument("--disable-dev-shm-usage")  # 禁用/dev/shm使用
        chrome_options.add_argument("--disable-infobars")  # 禁用信息栏
        chrome_options.add_argument("--disable-notifications")  # 禁用通知
        chrome_options.add_argument("--disable-popup-blocking")  # 禁用弹出窗口阻止
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36")  # 设置用户代理
        
        # 使用无头模式，减少资源消耗和提高稳定性
        chrome_options.add_argument("--headless=new")  # 使用新的无头模式
        
        print("正在初始化Chrome浏览器...")
        
        # 创建Service对象，使用chromedriver-py提供的ChromeDriver路径
        service = Service(executable_path=binary_path)
        
        # 初始化 Chrome 浏览器驱动，使用service对象
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        print("Chrome浏览器已初始化，正在访问URL...")
        
        # 设置页面加载超时，增加超时时间
        driver.set_page_load_timeout(60)  # 增加到60秒
        
        # 访问URL
        try:
            driver.get(url)
            print(f"已访问URL: {url}")
            
            # 增加等待时间，确保页面完全加载
            print("等待页面加载(10秒)...")
            time.sleep(10)  # 增加到10秒
            
            # 尝试滚动页面以加载更多内容
            print("滚动页面以加载更多内容...")
            try:
                # 滚动到页面底部
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)  # 等待内容加载
                
                # 再滚动回页面中部
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
                time.sleep(2)  # 等待内容加载
            except Exception as e:
                print(f"滚动页面时出错: {e}")
            
            # 获取页面渲染后的源代码
            page_source = driver.page_source
            print(f"已获取页面源代码，长度: {len(page_source)} 字符")
            
            # 保存页面源码以便调试
            with open("page_source_selenium.html", "w", encoding="utf-8") as f:
                f.write(page_source)
            print("已保存页面源码到 page_source_selenium.html 文件")
            
            # 尝试解析页面
            reports = parse_reports_from_page(page_source)
            
            # 如果没有找到研报，尝试使用备选URL
            if not reports:
                print("未从主页面找到研报，尝试备选URL...")
                backup_urls = [
                    "https://data.eastmoney.com/report/industry.jshtml",  # 行业研报
                    "https://data.eastmoney.com/report/stock.jshtml"      # 个股研报
                ]
                
                for backup_url in backup_urls:
                    print(f"尝试访问备选URL: {backup_url}")
                    try:
                        driver.get(backup_url)
                        print(f"已访问备选URL: {backup_url}")
                        
                        # 等待页面加载
                        print("等待备选页面加载(10秒)...")
                        time.sleep(10)
                        
                        # 获取页面源码
                        backup_page_source = driver.page_source
                        
                        # 保存备选页面源码
                        with open(f"page_source_backup_{backup_url.split('/')[-1]}", "w", encoding="utf-8") as f:
                            f.write(backup_page_source)
                        
                        # 解析备选页面
                        backup_reports = parse_reports_from_page(backup_page_source)
                        
                        if backup_reports:
                            print(f"从备选URL找到 {len(backup_reports)} 条研报")
                            reports.extend(backup_reports)
                            break
                    except Exception as e:
                        print(f"访问备选URL时出错: {e}")
            
            return reports
            
        except Exception as e:
            print(f"Selenium访问URL时出错: {e}")
            print("将尝试使用requests备选方法...")
            
            # 尝试备选方法
            return try_alternative_methods(url)

    except Exception as e:
        print(f"爬取过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        
        # 尝试备选方法
        return try_alternative_methods(url)
    finally:
        if driver:
            print("关闭浏览器...")
            try:
                driver.quit() # 确保关闭浏览器
            except Exception as e:
                print(f"关闭浏览器时遇到错误: {e}")
    return []

def try_alternative_methods(url):
    """尝试多种备选方法获取研报数据"""
    print("尝试多种备选方法获取研报数据...")
    
    # 方法1: 使用requests直接获取页面
    print("方法1: 使用requests直接获取页面...")
    page_source = get_page_with_requests(url)
    if page_source:
        reports = parse_reports_from_page(page_source)
        if reports:
            print(f"方法1成功: 获取到 {len(reports)} 条研报")
            return reports
    
    # 方法2: 尝试备选URL
    print("方法2: 尝试备选URL...")
    backup_urls = [
        "https://data.eastmoney.com/report/industry.jshtml",  # 行业研报
        "https://data.eastmoney.com/report/stock.jshtml"      # 个股研报
    ]
    
    for backup_url in backup_urls:
        print(f"尝试备选URL: {backup_url}")
        backup_page_source = get_page_with_requests(backup_url)
        if backup_page_source:
            backup_reports = parse_reports_from_page(backup_page_source)
            if backup_reports:
                print(f"从备选URL找到 {len(backup_reports)} 条研报")
                return backup_reports
    
    # 方法3: 尝试API接口
    print("方法3: 尝试API接口...")
    try:
        # 东方财富研报API
        api_url = "https://reportapi.eastmoney.com/report/list"
        params = {
            "cb": "datatable",
            "industryCode": "*",
            "pageSize": "50",
            "industry": "*",
            "rating": "*",
            "ratingChange": "*",
            "beginTime": "2023-01-01",
            "endTime": time.strftime("%Y-%m-%d"),
            "pageNo": "1",
            "fields": "",
            "_": str(int(time.time() * 1000))
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
            'Referer': 'https://data.eastmoney.com/report/',
            'Accept': '*/*'
        }
        
        response = requests.get(api_url, params=params, headers=headers, timeout=30)
        
        if response.status_code == 200:
            # 提取JSON数据
            text = response.text
            if text.startswith("datatable("):
                json_str = text[text.find("(")+1:text.rfind(")")]
                try:
                    data = json.loads(json_str)
                    if "data" in data and len(data["data"]) > 0:
                        reports_list = []
                        for item in data["data"]:
                            report = {
                                "title": item.get("title", ""),
                                "link": f"https://data.eastmoney.com/report/zw_industry.jshtml?infocode={item.get('infoCode', '')}",
                                "abstract": f"行业: {item.get('industryName', '未知行业')}, 评级: {item.get('rating', '')}, 机构: {item.get('orgSName', '')}, 日期: {item.get('publishDate', '')}",
                                "industry": item.get("industryName", "未知行业"),
                                "rating": item.get("rating", ""),
                                "org": item.get("orgSName", ""),
                                "date": item.get("publishDate", "")
                            }
                            reports_list.append(report)
                        
                        print(f"从API接口获取到 {len(reports_list)} 条研报")
                        return reports_list
                except Exception as e:
                    print(f"解析API数据时出错: {e}")
    except Exception as e:
        print(f"访问API接口时出错: {e}")
    
    print("所有备选方法都失败，返回空列表")
    return []

def analyze_with_five_steps(summary, content="", industry=None):
    """
    使用DeepSeek API对报告摘要和内容进行分析。
    
    黄燕铭五步分析法:
    1. 信息：收集和整理相关信息，包括公司公告、行业数据、政策变化等
    2. 逻辑：基于信息进行分析推理，形成对市场或个股的基本判断
    3. 超预期：寻找市场共识之外的信息点，发现被低估或高估的因素
    4. 催化剂：找出能够促使价格变动的关键事件或因素
    5. 结论：给出明确的投资建议，包括评级、目标价等
    
    Parameters:
    -----------
    summary : str
        报告摘要
    content : str, optional
        报告内容
    industry : str, optional
        行业分类
        
    Returns:
    --------
    dict
        分析结果字典
    """
    # 使用DeepSeek进行分析
    if deepseek_available:
        try:
            print("使用DeepSeek API进行分析...")
            # 提取标题
            title = summary.split('\n')[0] if '\n' in summary else summary[:100]
            # 使用DeepSeek分析器进行分析
            result = deepseek_analyzer.analyze_with_five_steps(title, content, industry)
            print("DeepSeek分析完成")
            return result["analysis"]
        except Exception as e:
            print(f"DeepSeek分析失败: {str(e)}")
            # 如果分析失败，返回空结果
            return {
                "信息": {"found": False, "keywords": [], "evidence": [], "step_score": 0},
                "逻辑": {"found": False, "keywords": [], "evidence": [], "step_score": 0},
                "超预期": {"found": False, "keywords": [], "evidence": [], "step_score": 0},
                "催化剂": {"found": False, "keywords": [], "evidence": [], "step_score": 0},
                "结论": {"found": False, "keywords": [], "evidence": [], "step_score": 0},
                "summary": {
                    "completeness_score": 0,
                    "steps_found": 0,
                    "evaluation": "分析失败，无法评估"
                }
            }
    else:
        print("DeepSeek分析器不可用，无法进行分析")
        return {
            "信息": {"found": False, "keywords": [], "evidence": [], "step_score": 0},
            "逻辑": {"found": False, "keywords": [], "evidence": [], "step_score": 0},
            "超预期": {"found": False, "keywords": [], "evidence": [], "step_score": 0},
            "催化剂": {"found": False, "keywords": [], "evidence": [], "step_score": 0},
            "结论": {"found": False, "keywords": [], "evidence": [], "step_score": 0},
            "summary": {
                "completeness_score": 0,
                "steps_found": 0,
                "evaluation": "分析器不可用，无法评估"
            }
        }

def get_evaluation_text(score):
    """根据完整度分数生成评价文本"""
    if score >= 90:
        return "研报非常完整地应用了五步分析法，包含了全面的分析要素"
    elif score >= 80:
        return "研报较好地应用了五步分析法，大部分分析要素齐全"
    elif score >= 60:
        return "研报部分应用了五步分析法，关键分析要素有所欠缺"
    elif score >= 40:
        return "研报仅包含少量五步分析法要素，分析不够全面"
    else:
        return "研报几乎未应用五步分析法，分析要素严重不足"

def save_results(data, filename="research_reports.json"):
    """
    将爬取和分析结果保存到 JSON 文件。
    """
    # 确保每个报告都包含 full_analysis 字段
    for report in data:
        if 'analysis' in report and not 'full_analysis' in report:
            # 如果没有完整分析文本，添加一个标记
            report['full_analysis'] = report.get('full_analysis', '未获取到完整分析文本')
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"结果已保存到 {filename}")

# 主程序入口
if __name__ == "__main__":
    print(f"Python版本: {sys.version}")
    print(f"Selenium版本: {webdriver.__version__}")
    print(f"Requests版本: {requests.__version__}")
    
    # 东方财富网行业研报页面 URL
    report_url = "https://data.eastmoney.com/report/hyyb.html"

    # 爬取研究报告列表
    reports_data = scrape_research_reports(report_url)
    print(f"爬取到 {len(reports_data)} 条研报数据")

    # 对每份报告进行五步分析
    analyzed_reports = []
    
    # 处理所有爬取到的研报数据
    print(f"将处理全部 {len(reports_data)} 条研报数据")
    
    for i, report in enumerate(reports_data):
        print(f"\n处理第 {i+1}/{len(reports_data)} 条研报: {report.get('title', 'N/A')}")
        
        # 对于每份报告，尝试获取详细内容并分析
        try:
            # 获取研报详情
            content = get_report_detail(report['link'])
            
            # 使用五步法分析
            analysis = analyze_with_five_steps(
                report['abstract'], 
                content,
                industry=report['industry']
            )
            
            # 将分析结果添加到报告数据中
            report['analysis'] = analysis
            report['full_content'] = content
            
            analyzed_reports.append(report)
            print(f"完成第 {i+1} 份研报的分析")
            
        except Exception as e:
            print(f"处理研报时出错: {e}")
            continue

    # 保存结果
    save_results(analyzed_reports)

    print("\n分析完成！请查看 research_reports.json 文件获取详细结果。")
    print("使用DeepSeek增强五步法分析已完成。") 